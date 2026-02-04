"""
Orchestration components for agent execution.
Splits complex Agent.run() logic into manageable, testable components.
"""
import re
import json
import asyncio
import itertools
from typing import Dict, List, Optional, Any, Tuple, Callable, Awaitable
from datetime import datetime

# Constants
POLL_TIMEOUT_SECONDS = 0.1  # Quick poll timeout for checking task results
END_SESSION_TOOL = 'end_session'  # Tool name for ending agent session


def _truncate_preview(text: str, max_len: int = 200) -> str:
    """Truncate text for preview logging."""
    return text[:max_len] + "..." if len(text) > max_len else text


class ToolCallHandler:
    """Handles extraction, categorization, and execution of tool calls."""

    @staticmethod
    def extract_all_tool_calls(text: str) -> List[Dict[str, Any]]:
        """
        Extract all tool calls from text.

        Args:
            text: Text that may contain multiple tool calls

        Returns:
            List of dictionaries with tool_name, parameters, and call_mode
        """
        pattern = r'<tool_call>\s*<tool_name>(.*?)</tool_name>(?:\s*<call_mode>(.*?)</call_mode>)?\s*<parameters>(.*?)</parameters>\s*</tool_call>'
        matches = re.finditer(pattern, text, re.DOTALL)

        tool_calls = []
        for match in matches:
            tool_name = match.group(1).strip()
            call_mode = match.group(2).strip() if match.group(2) else 'synchronous'
            parameters_str = match.group(3).strip()

            try:
                parameters = json.loads(parameters_str)
                tool_calls.append({
                    'tool_name': tool_name,
                    'call_mode': call_mode,
                    'parameters': parameters
                })
            except json.JSONDecodeError as e:
                # Include parse error so agent can be notified
                tool_calls.append({
                    'tool_name': tool_name,
                    'call_mode': call_mode,
                    'parameters': {},
                    'parse_error': f"Invalid JSON in parameters: {str(e)}"
                })

        return tool_calls

    @staticmethod
    def categorize_tool_calls(tool_calls: List[Dict[str, Any]]) -> Tuple[Optional[Dict], List[Dict], List[Dict]]:
        """
        Categorize tool calls into end_session, synchronous, and asynchronous.

        Args:
            tool_calls: List of tool call dictionaries

        Returns:
            Tuple of (end_session_call, sync_tool_calls, async_tool_calls)
        """
        end_session_call = None
        sync_tool_calls = []
        async_tool_calls = []

        for tool_call in tool_calls:
            if tool_call['tool_name'] == END_SESSION_TOOL:
                end_session_call = tool_call
            elif tool_call.get('call_mode', 'synchronous') == 'synchronous':
                sync_tool_calls.append(tool_call)
            else:
                async_tool_calls.append(tool_call)

        return end_session_call, sync_tool_calls, async_tool_calls

    @staticmethod
    def extract_text_before_end_session(response: str) -> str:
        """
        Extract text before end_session tool call.

        Args:
            response: LLM response containing end_session

        Returns:
            Text before the end_session tool call
        """
        tool_call_pattern = rf'<tool_call>\s*<tool_name>{END_SESSION_TOOL}</tool_name>.*?</tool_call>'
        text_before = re.sub(tool_call_pattern, '', response, flags=re.DOTALL).strip()
        return text_before


class TaskManager:
    """Manages asynchronous task execution and tracking."""

    def __init__(self):
        """Initialize task manager."""
        self.pending_tasks: Dict[str, asyncio.Task] = {}
        self.pending_tasks_info: Dict[str, Dict[str, Any]] = {}
        self.completed_results: asyncio.Queue = asyncio.Queue()
        self._task_counter = itertools.count(1)  # Thread-safe counter
        self.tasks_lock = asyncio.Lock()
        # Track launched vs processed to detect unprocessed results
        self._launched_count = 0
        self._processed_count = 0

    def generate_task_id(self, tool_name: str) -> str:
        """
        Generate unique task ID.

        Args:
            tool_name: Name of the tool

        Returns:
            Unique task ID
        """
        return f"{tool_name}_{next(self._task_counter)}"

    async def launch_task(
        self,
        task_id: str,
        tool_name: str,
        parameters: Dict[str, Any],
        execute_func: Callable[[str, Dict[str, Any], str], Awaitable[str]]
    ) -> None:
        """
        Launch an asynchronous task.

        Args:
            task_id: Unique task identifier
            tool_name: Name of the tool to execute
            parameters: Parameters for the tool
            execute_func: Async function to execute the tool (tool_name, params, call_mode) -> result
        """
        async def _task_wrapper():
            try:
                result = await execute_func(tool_name, parameters, call_mode='asynchronous')
                await self.completed_results.put((task_id, result))
            except Exception as e:
                error_msg = f"Error in task {task_id}: {str(e)}"
                await self.completed_results.put((task_id, error_msg))
            finally:
                # Ensure task is removed from pending even if queue put fails
                async with self.tasks_lock:
                    self.pending_tasks.pop(task_id, None)
                    self.pending_tasks_info.pop(task_id, None)

        task = asyncio.create_task(_task_wrapper())
        async with self.tasks_lock:
            self.pending_tasks[task_id] = task
            self.pending_tasks_info[task_id] = {
                "tool_name": tool_name,
                "parameters": parameters,
                "launched_at": datetime.now().isoformat()
            }
            self._launched_count += 1

    async def wait_for_result(self, timeout: Optional[float] = None) -> Optional[Tuple[str, str]]:
        """
        Wait for a task result.

        Args:
            timeout: Timeout in seconds (None for no timeout)

        Returns:
            Tuple of (task_id, result) or None if timeout
        """
        try:
            return await asyncio.wait_for(
                self.completed_results.get(),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            return None

    async def remove_task(self, task_id: str) -> None:
        """
        Remove task from pending lists.

        Args:
            task_id: Task identifier to remove
        """
        async with self.tasks_lock:
            if task_id in self.pending_tasks:
                del self.pending_tasks[task_id]
            if task_id in self.pending_tasks_info:
                del self.pending_tasks_info[task_id]

    async def has_pending_tasks(self) -> bool:
        """
        Check if there are pending tasks.

        Returns:
            True if there are pending tasks
        """
        async with self.tasks_lock:
            return len(self.pending_tasks) > 0

    async def has_outstanding_tasks(self) -> bool:
        """
        Check if there are outstanding tasks (running OR results not yet processed).

        This is the correct check for end_session - it ensures all launched tasks
        have had their results processed, not just that they've finished running.

        Returns:
            True if there are tasks that haven't been fully processed
        """
        async with self.tasks_lock:
            # Outstanding = launched but not yet processed
            return self._launched_count > self._processed_count

    async def mark_task_processed(self) -> None:
        """
        Mark a task result as processed.

        Call this after retrieving and processing a result from the queue.
        """
        async with self.tasks_lock:
            self._processed_count += 1

    async def get_outstanding_count(self) -> int:
        """
        Get the number of outstanding tasks (launched - processed).

        Returns:
            Number of tasks that haven't been fully processed
        """
        async with self.tasks_lock:
            return self._launched_count - self._processed_count

    async def get_pending_count(self) -> int:
        """
        Get number of pending tasks.

        Returns:
            Number of pending tasks
        """
        async with self.tasks_lock:
            return len(self.pending_tasks)

    async def get_pending_task_ids(self) -> List[str]:
        """
        Get list of pending task IDs.

        Returns:
            List of task IDs
        """
        async with self.tasks_lock:
            return list(self.pending_tasks.keys())

    async def get_remaining_tasks(self) -> List[asyncio.Task]:
        """
        Get list of remaining tasks.

        Returns:
            List of asyncio tasks
        """
        async with self.tasks_lock:
            return list(self.pending_tasks.values())

    async def build_pending_tasks_message(self, prompts) -> Optional[str]:
        """
        Build message about pending tasks for agent context.

        Args:
            prompts: Prompt loader instance

        Returns:
            Message string or None if no pending tasks
        """
        async with self.tasks_lock:
            if not self.pending_tasks_info:
                return None

            msg = prompts.get_runtime_message('pending_tasks_header', pending_count=len(self.pending_tasks_info))

            for task_id, info in self.pending_tasks_info.items():
                tool_name = info["tool_name"]
                parameters = info["parameters"]
                launched_at = info["launched_at"]

                msg += prompts.get_runtime_message(
                    'pending_task_item',
                    task_id=task_id,
                    tool_name=tool_name,
                    parameters=json.dumps(parameters, ensure_ascii=False),
                    launched_at=launched_at
                )

            msg += prompts.get_runtime_message('pending_tasks_reminder')
            return msg


class ConversationManager:
    """Manages conversation history and message formatting."""

    def __init__(self, messages: List[Dict[str, str]], prompts):
        """
        Initialize conversation manager.

        Args:
            messages: Reference to agent's messages list
            prompts: Prompt loader instance
        """
        self.messages = messages
        self.prompts = prompts

    def add_user_message(self, content: str) -> None:
        """Add user message to conversation."""
        self.messages.append({
            "role": "user",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, content: str) -> None:
        """Add assistant message to conversation."""
        self.messages.append({
            "role": "assistant",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_system_message(self, content: str) -> None:
        """Add system message to conversation."""
        self.messages.append({
            "role": "system",
            "content": content,
            "timestamp": datetime.now().isoformat()
        })

    def add_tool_result(self, tool_name: str, result: str) -> None:
        """Add tool result as user message."""
        self.add_user_message(
            self.prompts.get_runtime_message('tool_result', tool_name=tool_name, result=result)
        )

    def add_task_completed(self, task_id: str, result: str) -> None:
        """Add task completion as user message."""
        self.add_user_message(
            self.prompts.get_runtime_message('task_completed', task_id=task_id, result=result)
        )

    def add_tasks_launched_notification(self, task_ids: List[str]) -> None:
        """Add notification about launched tasks."""
        task_list = self.prompts.format_task_list(task_ids)
        notification_msg = self.prompts.get_runtime_message(
            'tasks_launched_notification',
            task_count=len(task_ids),
            task_list=task_list
        )
        self.add_system_message(notification_msg)

    def add_end_session_warning(self, pending_count: int, task_list: str) -> None:
        """Add warning about ending session with pending tasks."""
        warning_msg = self.prompts.get_runtime_message(
            'end_session_with_pending_tasks_error',
            pending_count=pending_count,
            task_list=task_list
        )
        self.add_system_message(warning_msg)

    def add_no_tool_call_warning(self) -> None:
        """Add warning about missing tool call."""
        reminder_msg = self.prompts.get_runtime_message('no_tool_call_warning')
        self.add_system_message(reminder_msg)

    def remove_last_message(self) -> None:
        """Remove last message from conversation."""
        if self.messages:
            self.messages.pop()


class AgentOrchestrator:
    """
    Orchestrates agent execution by coordinating tool calls, tasks, and conversation.
    Simplifies the main Agent.run() loop by delegating to specialized handlers.
    """

    def __init__(self, agent):
        """
        Initialize orchestrator.

        Args:
            agent: Agent instance to orchestrate
        """
        self.agent = agent
        self.tool_handler = ToolCallHandler()
        self.task_manager = TaskManager()
        self.conversation = ConversationManager(agent.messages, agent.prompts)

    async def handle_iteration(
        self,
        iterations: int,
        max_iterations: int
    ) -> Tuple[str, bool, bool]:
        """
        Handle a single iteration of the agent loop.

        Args:
            iterations: Current iteration number
            max_iterations: Maximum iterations allowed

        Returns:
            Tuple of (response, should_continue, session_ended)
        """
        # Log iteration
        self.agent._log(
            self.agent.prompts.get_log_message('iteration_separator', iteration=iterations, max_iterations=max_iterations)
        )

        # Update state
        self.agent.db.update_agent_state(self.agent.agent_id, 'generating')

        # Inject pending tasks info
        pending_tasks_msg = await self.task_manager.build_pending_tasks_message(self.agent.prompts)
        if pending_tasks_msg:
            self.conversation.add_system_message(pending_tasks_msg)

        try:
            # Call LLM
            response = await self.agent._call_llm()
        finally:
            # Remove pending tasks message (ensure cleanup even on error)
            if pending_tasks_msg:
                self.conversation.remove_last_message()

        # Extract tool calls
        tool_calls = self.tool_handler.extract_all_tool_calls(response)

        if not tool_calls:
            # No tool call - warn and continue
            self.agent._log(self.agent.prompts.get_log_message('warning_no_tool_call'), "WARNING")
            self.conversation.add_no_tool_call_warning()
            return response, True, False

        # Process tool calls
        return await self._process_tool_calls(response, tool_calls)

    async def _process_tool_calls(
        self,
        response: str,
        tool_calls: List[Dict[str, Any]]
    ) -> Tuple[str, bool, bool]:
        """
        Process extracted tool calls.

        Args:
            response: LLM response
            tool_calls: List of tool calls

        Returns:
            Tuple of (final_response, should_continue, session_ended)
        """
        self.agent._log(
            self.agent.prompts.get_log_message('tool_calls_detected', count=len(tool_calls))
        )

        # Handle parse errors - notify agent about malformed tool calls
        valid_tool_calls = []
        for tool_call in tool_calls:
            if 'parse_error' in tool_call:
                self.conversation.add_user_message(
                    f"Error parsing tool call for '{tool_call['tool_name']}': {tool_call['parse_error']}"
                )
            else:
                valid_tool_calls.append(tool_call)

        # Categorize valid tool calls
        end_session_call, sync_calls, async_calls = self.tool_handler.categorize_tool_calls(valid_tool_calls)

        # Add assistant message
        self.conversation.add_assistant_message(response)

        # Execute sync calls
        if sync_calls:
            await self._execute_sync_calls(sync_calls)

        # Launch async calls
        launched_task_ids = []
        if async_calls:
            launched_task_ids = await self._launch_async_calls(async_calls)

        # Handle end_session
        if end_session_call:
            return await self._handle_end_session(end_session_call, response, launched_task_ids)

        # Notify about launched tasks
        if launched_task_ids:
            self.conversation.add_tasks_launched_notification(launched_task_ids)

        # Determine if should continue
        should_continue = self._should_continue_generating(sync_calls, async_calls)

        # Update state
        if should_continue:
            self.agent.db.update_agent_state(self.agent.agent_id, 'generating')
        else:
            self.agent.db.update_agent_state(self.agent.agent_id, 'waiting')

        return response, should_continue, False

    async def _execute_sync_calls(self, sync_calls: List[Dict[str, Any]]) -> None:
        """Execute synchronous tool calls in order."""
        self.agent._log(
            self.agent.prompts.get_log_message('executing_sync_tools', count=len(sync_calls))
        )

        for tool_call in sync_calls:
            self.agent._log(
                self.agent.prompts.get_log_message(
                    'executing_sync_tool',
                    tool_name=tool_call['tool_name'],
                    parameters=tool_call['parameters']
                )
            )

            result = await self.agent._execute_tool(
                tool_call['tool_name'],
                tool_call['parameters'],
                call_mode='synchronous'
            )

            result_preview = _truncate_preview(result)
            self.agent._log(
                self.agent.prompts.get_log_message('tool_result_log', result=result_preview)
            )

            self.conversation.add_tool_result(tool_call['tool_name'], result)

    async def _launch_async_calls(self, async_calls: List[Dict[str, Any]]) -> List[str]:
        """Launch asynchronous tool calls."""
        self.agent._log(
            self.agent.prompts.get_log_message('launching_async_tools', count=len(async_calls))
        )

        task_ids = []
        for tool_call in async_calls:
            self.agent._log(
                self.agent.prompts.get_log_message(
                    'launching_async_tool',
                    tool_name=tool_call['tool_name'],
                    parameters=tool_call['parameters']
                )
            )

            task_id = self.task_manager.generate_task_id(tool_call['tool_name'])
            await self.task_manager.launch_task(
                task_id,
                tool_call['tool_name'],
                tool_call['parameters'],
                self.agent._execute_tool
            )
            task_ids.append(task_id)

            self.agent._log(
                self.agent.prompts.get_log_message('task_launched', task_id=task_id)
            )

        return task_ids

    async def _handle_end_session(
        self,
        end_session_call: Dict[str, Any],
        response: str,
        launched_task_ids: List[str]
    ) -> Tuple[str, bool, bool]:
        """
        Handle end_session tool call.

        Returns:
            Tuple of (final_response, should_continue, session_ended)
        """
        # Check for outstanding tasks (running OR completed but not yet processed)
        # This is critical - we must wait for ALL task results to be processed,
        # not just for tasks to finish running. Tasks remove themselves from
        # pending_tasks when they complete, but their results may still be in the queue.
        has_outstanding = await self.task_manager.has_outstanding_tasks()

        if has_outstanding:
            outstanding_count = await self.task_manager.get_outstanding_count()
            # Get IDs of tasks still running (subset of outstanding)
            pending_ids = await self.task_manager.get_pending_task_ids()
            if pending_ids:
                pending_list = ', '.join(pending_ids)
            else:
                # Tasks completed but results not processed yet
                pending_list = f"({outstanding_count} task result(s) awaiting processing)"

            self.agent._log(
                self.agent.prompts.get_log_message('warning_end_session_with_pending', count=outstanding_count),
                "WARNING"
            )
            self.agent._log(
                self.agent.prompts.get_log_message('warning_pending_tasks_list', task_list=pending_list),
                "WARNING"
            )

            self.conversation.add_end_session_warning(outstanding_count, pending_list)
            self.agent.db.update_agent_state(self.agent.agent_id, 'waiting')

            return response, False, False

        # Safe to end session
        self.agent._log(self.agent.prompts.get_log_message('end_session_called'))

        # Extract final response
        text_before = self.tool_handler.extract_text_before_end_session(response)
        final_response = text_before if text_before else response

        # Execute end_session
        result = await self.agent._execute_tool(END_SESSION_TOOL, end_session_call['parameters'])
        self.agent._log(f"  {result}")

        # Check for final_message parameter
        final_message_param = end_session_call['parameters'].get('final_message', '')
        if final_message_param:
            final_response = final_message_param

        response_preview = _truncate_preview(final_response, max_len=100)
        self.agent._log(
            self.agent.prompts.get_log_message('final_response_log', response=response_preview)
        )

        return final_response, False, True

    def _should_continue_generating(self, sync_calls: List, async_calls: List) -> bool:
        """
        Determine if agent should continue generating.

        Args:
            sync_calls: List of synchronous calls executed
            async_calls: List of asynchronous calls launched

        Returns:
            True if agent should generate next response
        """
        if sync_calls and not async_calls:
            # Only sync calls - results in conversation, can continue
            return True
        elif async_calls:
            # Async calls launched - wait for results
            return False
        else:
            # No calls executed (shouldn't happen)
            return False

    async def wait_for_task_result(self, has_pending: bool, should_continue: bool) -> Optional[Tuple[str, str]]:
        """
        Wait for a task result if needed.

        Behavior:
        - If has_pending=True: Block indefinitely waiting for next result
        - If has_outstanding (results in queue): Return immediately from queue
        - If has_pending=False and should_continue=False: Quick poll (POLL_TIMEOUT_SECONDS)
        - If has_pending=False and should_continue=True: Return immediately (no waiting)

        Args:
            has_pending: Whether there are pending tasks (still running)
            should_continue: Whether agent wants to continue generating

        Returns:
            Tuple of (task_id, result) or None
        """
        # First check if there are results waiting in the queue
        # This handles the case where tasks completed faster than we could process
        if not self.task_manager.completed_results.empty():
            try:
                return self.task_manager.completed_results.get_nowait()
            except asyncio.QueueEmpty:
                pass  # Race condition, continue with normal flow

        if has_pending:
            # Block until a pending task completes
            return await self.task_manager.wait_for_result(timeout=None)
        elif not should_continue:
            # Quick poll to check if any results arrived
            return await self.task_manager.wait_for_result(timeout=POLL_TIMEOUT_SECONDS)
        else:
            # Continue generating, don't wait
            return None

    async def process_task_result(
        self,
        task_id: str,
        result: str,
        session_ended: bool
    ) -> bool:
        """
        Process a completed task result.

        Args:
            task_id: Task identifier
            result: Task result
            session_ended: Whether session has ended

        Returns:
            True if agent should continue generating
        """
        self.agent._log(
            self.agent.prompts.get_log_message('task_completed_log', task_id=task_id)
        )

        result_preview = result[:200] + "..." if len(result) > 200 else result
        self.agent._log(
            self.agent.prompts.get_log_message('task_result_log', result=result_preview)
        )

        # Add to conversation if session not ended
        if not session_ended:
            self.conversation.add_task_completed(task_id, result)

        # Remove from pending and mark as processed
        await self.task_manager.remove_task(task_id)
        await self.task_manager.mark_task_processed()

        # Continue if session not ended
        return not session_ended

    async def wait_for_remaining_tasks(self) -> None:
        """Wait for all remaining tasks to complete and drain any leftover results."""
        remaining = await self.task_manager.get_remaining_tasks()

        if remaining:
            self.agent._log(
                self.agent.prompts.get_log_message('waiting_for_remaining_tasks', count=len(remaining))
            )
            results = await asyncio.gather(*remaining, return_exceptions=True)

            # Log any exceptions that occurred
            for result in results:
                if isinstance(result, Exception):
                    self.agent._log(f"Task failed with exception: {result}", "ERROR")

        # Drain any remaining results from the queue (safety measure)
        # This handles edge cases where results were queued but not processed
        drained_count = 0
        while not self.task_manager.completed_results.empty():
            try:
                task_id, result = self.task_manager.completed_results.get_nowait()
                await self.task_manager.mark_task_processed()
                drained_count += 1
                self.agent._log(
                    f"Drained unprocessed result for task {task_id}: {_truncate_preview(result, 100)}"
                )
            except asyncio.QueueEmpty:
                break

        if drained_count > 0:
            self.agent._log(
                f"WARNING: {drained_count} task result(s) were not processed before session ended",
                "WARNING"
            )

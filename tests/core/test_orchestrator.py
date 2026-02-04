"""Tests for orchestrator module."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from multi_agent.core.orchestrator import (
    ToolCallHandler,
    TaskManager,
    ConversationManager,
    AgentOrchestrator,
    END_SESSION_TOOL,
    _truncate_preview
)


class TestTruncatePreview:
    """Test cases for _truncate_preview helper function."""

    def test_truncate_preview_short_text(self):
        """Test that short text is not truncated."""
        text = "Short text"
        assert _truncate_preview(text) == "Short text"

    def test_truncate_preview_long_text_default(self):
        """Test truncation with default max_len (200)."""
        text = "x" * 250
        result = _truncate_preview(text)
        assert len(result) == 203  # 200 + "..."
        assert result.endswith("...")

    def test_truncate_preview_long_text_custom_len(self):
        """Test truncation with custom max_len."""
        text = "x" * 150
        result = _truncate_preview(text, max_len=100)
        assert len(result) == 103  # 100 + "..."
        assert result.endswith("...")

    def test_truncate_preview_exact_length(self):
        """Test text at exact max_len is not truncated."""
        text = "x" * 200
        result = _truncate_preview(text)
        assert result == text  # No truncation


class TestToolCallHandler:
    """Test cases for ToolCallHandler class."""

    def test_extract_all_tool_calls_single(self):
        """Test extracting a single tool call."""
        text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>{"operation": "add", "a": 5, "b": 3}</parameters>
</tool_call>
'''
        handler = ToolCallHandler()
        result = handler.extract_all_tool_calls(text)

        assert len(result) == 1
        assert result[0]['tool_name'] == 'calculator'
        assert result[0]['parameters'] == {"operation": "add", "a": 5, "b": 3}
        assert result[0]['call_mode'] == 'synchronous'

    def test_extract_all_tool_calls_multiple(self):
        """Test extracting multiple tool calls."""
        text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>{"operation": "add"}</parameters>
</tool_call>

<tool_call>
<tool_name>text_analyzer</tool_name>
<call_mode>asynchronous</call_mode>
<parameters>{"text": "hello"}</parameters>
</tool_call>
'''
        handler = ToolCallHandler()
        results = handler.extract_all_tool_calls(text)

        assert len(results) == 2
        assert results[0]['tool_name'] == 'calculator'
        assert results[0]['call_mode'] == 'synchronous'
        assert results[1]['tool_name'] == 'text_analyzer'
        assert results[1]['call_mode'] == 'asynchronous'

    def test_extract_all_tool_calls_invalid_json(self):
        """Test that invalid JSON returns parse_error instead of being skipped."""
        text = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>{invalid json}</parameters>
</tool_call>

<tool_call>
<tool_name>text_analyzer</tool_name>
<parameters>{"valid": "json"}</parameters>
</tool_call>
'''
        handler = ToolCallHandler()
        results = handler.extract_all_tool_calls(text)

        # Both tool calls should be returned
        assert len(results) == 2

        # First one has parse_error
        assert results[0]['tool_name'] == 'calculator'
        assert 'parse_error' in results[0]
        assert 'Invalid JSON' in results[0]['parse_error']
        assert results[0]['parameters'] == {}

        # Second one is valid
        assert results[1]['tool_name'] == 'text_analyzer'
        assert 'parse_error' not in results[1]
        assert results[1]['parameters'] == {"valid": "json"}

    def test_categorize_tool_calls(self):
        """Test categorizing tool calls by type."""
        tool_calls = [
            {'tool_name': 'calculator', 'call_mode': 'synchronous', 'parameters': {}},
            {'tool_name': 'text_analyzer', 'call_mode': 'asynchronous', 'parameters': {}},
            {'tool_name': 'end_session', 'call_mode': 'synchronous', 'parameters': {}},
            {'tool_name': 'another_tool', 'call_mode': 'synchronous', 'parameters': {}},
        ]

        handler = ToolCallHandler()
        end_session, sync_calls, async_calls = handler.categorize_tool_calls(tool_calls)

        assert end_session is not None
        assert end_session['tool_name'] == 'end_session'
        assert len(sync_calls) == 2
        assert len(async_calls) == 1

    def test_extract_text_before_end_session(self):
        """Test extracting text before end_session call."""
        response = '''Here is the result.

<tool_call>
<tool_name>end_session</tool_name>
<parameters>{}</parameters>
</tool_call>
'''
        handler = ToolCallHandler()
        text = handler.extract_text_before_end_session(response)

        assert "Here is the result." in text
        assert "<tool_call>" not in text


@pytest.mark.asyncio
class TestTaskManager:
    """Test cases for TaskManager class."""

    async def test_generate_task_id(self):
        """Test generating unique task IDs."""
        manager = TaskManager()

        task_id1 = manager.generate_task_id("calculator")
        task_id2 = manager.generate_task_id("calculator")

        assert task_id1 == "calculator_1"
        assert task_id2 == "calculator_2"

    async def test_launch_task(self):
        """Test launching an async task."""
        manager = TaskManager()

        async def mock_execute(tool_name, params, call_mode):
            await asyncio.sleep(0.01)
            return "Result"

        task_id = manager.generate_task_id("test_tool")
        await manager.launch_task(task_id, "test_tool", {"param": "value"}, mock_execute)

        assert task_id in manager.pending_tasks
        assert task_id in manager.pending_tasks_info

        # Wait for task completion
        result = await manager.wait_for_result(timeout=1.0)
        assert result is not None
        assert result[0] == task_id
        assert result[1] == "Result"

    async def test_has_pending_tasks(self):
        """Test checking for pending tasks."""
        manager = TaskManager()

        assert not await manager.has_pending_tasks()

        async def mock_execute(tool_name, params, call_mode):
            await asyncio.sleep(0.1)
            return "Result"

        task_id = manager.generate_task_id("test_tool")
        await manager.launch_task(task_id, "test_tool", {}, mock_execute)

        assert await manager.has_pending_tasks()

        # Wait for completion
        await manager.wait_for_result(timeout=1.0)
        await manager.remove_task(task_id)

        assert not await manager.has_pending_tasks()

    async def test_get_pending_count(self):
        """Test getting pending task count."""
        manager = TaskManager()

        assert await manager.get_pending_count() == 0

        async def mock_execute(tool_name, params, call_mode):
            await asyncio.sleep(0.5)
            return "Result"

        task_id1 = manager.generate_task_id("tool1")
        task_id2 = manager.generate_task_id("tool2")

        await manager.launch_task(task_id1, "tool1", {}, mock_execute)
        await manager.launch_task(task_id2, "tool2", {}, mock_execute)

        assert await manager.get_pending_count() == 2

        # Cleanup
        await manager.wait_for_result(timeout=1.0)
        await manager.wait_for_result(timeout=1.0)

    async def test_wait_for_result_timeout(self):
        """Test waiting for result with timeout."""
        manager = TaskManager()

        result = await manager.wait_for_result(timeout=0.01)
        assert result is None

    async def test_remove_task(self):
        """Test removing task from pending lists."""
        manager = TaskManager()

        async def mock_execute(tool_name, params, call_mode):
            await asyncio.sleep(0.01)
            return "Result"

        task_id = manager.generate_task_id("test_tool")
        await manager.launch_task(task_id, "test_tool", {}, mock_execute)

        assert task_id in manager.pending_tasks
        await manager.remove_task(task_id)
        assert task_id not in manager.pending_tasks

    async def test_launch_task_cleanup_on_error(self):
        """Test that task is removed from pending even when execute_func raises."""
        manager = TaskManager()

        async def failing_execute(tool_name, params, call_mode):
            raise ValueError("Simulated error")

        task_id = manager.generate_task_id("failing_tool")
        await manager.launch_task(task_id, "failing_tool", {}, failing_execute)

        # Task should be in pending initially
        assert task_id in manager.pending_tasks

        # Wait for the task to complete (with error)
        result = await manager.wait_for_result(timeout=1.0)
        assert result is not None
        assert result[0] == task_id
        assert "Error in task" in result[1]

        # Give the finally block time to execute
        await asyncio.sleep(0.01)

        # Task should be cleaned up automatically by finally block
        assert task_id not in manager.pending_tasks
        assert task_id not in manager.pending_tasks_info


class TestConversationManager:
    """Test cases for ConversationManager class."""

    def test_add_user_message(self):
        """Test adding user message."""
        messages = []
        prompts = Mock()
        manager = ConversationManager(messages, prompts)

        manager.add_user_message("Hello")

        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'Hello'

    def test_add_assistant_message(self):
        """Test adding assistant message."""
        messages = []
        prompts = Mock()
        manager = ConversationManager(messages, prompts)

        manager.add_assistant_message("Hi there")

        assert len(messages) == 1
        assert messages[0]['role'] == 'assistant'
        assert messages[0]['content'] == 'Hi there'

    def test_add_system_message(self):
        """Test adding system message."""
        messages = []
        prompts = Mock()
        manager = ConversationManager(messages, prompts)

        manager.add_system_message("System notification")

        assert len(messages) == 1
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == 'System notification'

    def test_add_tool_result(self):
        """Test adding tool result."""
        messages = []
        prompts = Mock()
        prompts.get_runtime_message.return_value = "Tool result: Success"

        manager = ConversationManager(messages, prompts)
        manager.add_tool_result("calculator", "42")

        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        prompts.get_runtime_message.assert_called_once_with(
            'tool_result',
            tool_name='calculator',
            result='42'
        )

    def test_add_task_completed(self):
        """Test adding task completion message."""
        messages = []
        prompts = Mock()
        prompts.get_runtime_message.return_value = "Task completed: calculator_1"

        manager = ConversationManager(messages, prompts)
        manager.add_task_completed("calculator_1", "Result")

        assert len(messages) == 1
        prompts.get_runtime_message.assert_called_once_with(
            'task_completed',
            task_id='calculator_1',
            result='Result'
        )

    def test_remove_last_message(self):
        """Test removing last message."""
        messages = [
            {'role': 'user', 'content': 'Hello'},
            {'role': 'assistant', 'content': 'Hi'}
        ]
        prompts = Mock()
        manager = ConversationManager(messages, prompts)

        manager.remove_last_message()

        assert len(messages) == 1
        assert messages[0]['role'] == 'user'


@pytest.mark.asyncio
class TestAgentOrchestrator:
    """Test cases for AgentOrchestrator class."""

    @pytest.fixture
    def mock_agent(self):
        """Create a mock agent."""
        agent = Mock()
        agent.messages = []
        agent.prompts = Mock()
        agent.db = Mock()
        agent.agent_id = "test-agent-id"
        agent._log = Mock()
        agent._call_llm = AsyncMock(return_value="Response")
        agent._execute_tool = AsyncMock(return_value="Tool result")

        # Setup prompt returns
        agent.prompts.get_log_message.return_value = "Log message"
        agent.prompts.get_runtime_message.return_value = "Runtime message"
        agent.prompts.format_task_list.return_value = "task1, task2"

        return agent

    async def test_orchestrator_initialization(self, mock_agent):
        """Test orchestrator initialization."""
        orchestrator = AgentOrchestrator(mock_agent)

        assert orchestrator.agent == mock_agent
        assert isinstance(orchestrator.tool_handler, ToolCallHandler)
        assert isinstance(orchestrator.task_manager, TaskManager)
        assert isinstance(orchestrator.conversation, ConversationManager)

    async def test_handle_iteration_no_tool_calls(self, mock_agent):
        """Test handling iteration with no tool calls."""
        mock_agent._call_llm.return_value = "Just a response without tool calls"

        orchestrator = AgentOrchestrator(mock_agent)
        response, should_continue, session_ended = await orchestrator.handle_iteration(1, 10)

        assert response == "Just a response without tool calls"
        assert should_continue is True
        assert session_ended is False
        mock_agent.db.update_agent_state.assert_called()

    async def test_handle_iteration_with_sync_tool_call(self, mock_agent):
        """Test handling iteration with synchronous tool call."""
        mock_agent._call_llm.return_value = '''
<tool_call>
<tool_name>calculator</tool_name>
<parameters>{"operation": "add"}</parameters>
</tool_call>
'''
        mock_agent._execute_tool.return_value = "42"

        orchestrator = AgentOrchestrator(mock_agent)
        response, should_continue, session_ended = await orchestrator.handle_iteration(1, 10)

        assert should_continue is True
        assert session_ended is False
        mock_agent._execute_tool.assert_called_once()

    async def test_handle_iteration_with_end_session(self, mock_agent):
        """Test handling iteration with end_session call."""
        mock_agent._call_llm.return_value = '''Final result.
<tool_call>
<tool_name>end_session</tool_name>
<parameters>{"final_message": "Done"}</parameters>
</tool_call>
'''
        mock_agent._execute_tool.return_value = "Session ended"

        orchestrator = AgentOrchestrator(mock_agent)
        response, should_continue, session_ended = await orchestrator.handle_iteration(1, 10)

        assert session_ended is True
        assert should_continue is False
        assert "Final result" in response or response == "Done"

    async def test_should_continue_generating_sync_only(self, mock_agent):
        """Test continue logic with only sync calls."""
        orchestrator = AgentOrchestrator(mock_agent)

        sync_calls = [{'tool_name': 'calculator'}]
        async_calls = []

        should_continue = orchestrator._should_continue_generating(sync_calls, async_calls)
        assert should_continue is True

    async def test_should_continue_generating_with_async(self, mock_agent):
        """Test continue logic with async calls."""
        orchestrator = AgentOrchestrator(mock_agent)

        sync_calls = []
        async_calls = [{'tool_name': 'long_task'}]

        should_continue = orchestrator._should_continue_generating(sync_calls, async_calls)
        assert should_continue is False

    async def test_process_task_result(self, mock_agent):
        """Test processing task result."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Launch a task first
        async def mock_execute(tool_name, params, call_mode):
            return "Result"

        task_id = orchestrator.task_manager.generate_task_id("test_tool")
        await orchestrator.task_manager.launch_task(
            task_id,
            "test_tool",
            {},
            mock_execute
        )

        # Wait for result
        await asyncio.sleep(0.01)

        # Process result
        should_continue = await orchestrator.process_task_result(
            task_id,
            "Result",
            session_ended=False
        )

        assert should_continue is True
        mock_agent._log.assert_called()

    async def test_launch_async_calls(self, mock_agent):
        """Test launching async calls."""
        orchestrator = AgentOrchestrator(mock_agent)

        async_calls = [
            {'tool_name': 'tool1', 'parameters': {'p1': 'v1'}},
            {'tool_name': 'tool2', 'parameters': {'p2': 'v2'}},
        ]

        task_ids = await orchestrator._launch_async_calls(async_calls)

        assert len(task_ids) == 2
        assert task_ids[0].startswith('tool1_')
        assert task_ids[1].startswith('tool2_')
        assert await orchestrator.task_manager.get_pending_count() == 2

    async def test_handle_end_session_with_pending_tasks(self, mock_agent):
        """Test that end_session is blocked when there are pending tasks."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Launch a pending task
        async def slow_task(tool_name, params, call_mode):
            await asyncio.sleep(1.0)
            return "Result"

        task_id = orchestrator.task_manager.generate_task_id("slow_tool")
        await orchestrator.task_manager.launch_task(task_id, "slow_tool", {}, slow_task)

        # Try to end session
        end_session_call = {'tool_name': 'end_session', 'parameters': {}}
        response, should_continue, session_ended = await orchestrator._handle_end_session(
            end_session_call,
            "Response text",
            []
        )

        assert session_ended is False
        assert should_continue is False
        mock_agent._log.assert_called()

    async def test_process_tool_calls_notifies_parse_errors(self, mock_agent):
        """Test that parse errors are sent to the agent as user messages."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Tool calls with one having a parse error
        tool_calls = [
            {'tool_name': 'calculator', 'call_mode': 'synchronous', 'parameters': {},
             'parse_error': 'Invalid JSON in parameters: Expecting value'},
            {'tool_name': 'valid_tool', 'call_mode': 'synchronous', 'parameters': {'x': 1}},
        ]

        await orchestrator._process_tool_calls("Response", tool_calls)

        # Check that a message was added for the parse error
        messages = mock_agent.messages
        parse_error_messages = [m for m in messages if 'parse_error' in m.get('content', '').lower()
                                or 'Invalid JSON' in m.get('content', '')]
        assert len(parse_error_messages) >= 1
        assert 'calculator' in parse_error_messages[0]['content']

    async def test_wait_for_task_result_scenarios(self, mock_agent):
        """Test wait_for_task_result covers all three branches explicitly."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Scenario 1: has_pending=True - should block (we use a short timeout to test)
        # Launch a quick task
        async def quick_task(tool_name, params, call_mode):
            await asyncio.sleep(0.01)
            return "Done"

        task_id = orchestrator.task_manager.generate_task_id("test")
        await orchestrator.task_manager.launch_task(task_id, "test", {}, quick_task)

        # has_pending=True should wait and return result
        result = await orchestrator.wait_for_task_result(has_pending=True, should_continue=False)
        assert result is not None
        assert result[0] == task_id

        # Scenario 2: has_pending=False, should_continue=False - quick poll
        result = await orchestrator.wait_for_task_result(has_pending=False, should_continue=False)
        # Should return None (no pending tasks)
        assert result is None

        # Scenario 3: has_pending=False, should_continue=True - return immediately
        result = await orchestrator.wait_for_task_result(has_pending=False, should_continue=True)
        assert result is None

    async def test_wait_for_remaining_tasks_logs_exceptions(self, mock_agent):
        """Test that wait_for_remaining_tasks logs exceptions from asyncio.gather."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Create a task that raises directly (simulating a task that fails after being gathered)
        # We need to add a raw task to pending_tasks that will raise when awaited
        async def raw_failing_task():
            raise ValueError("Direct task failure!")

        task = asyncio.create_task(raw_failing_task())
        async with orchestrator.task_manager.tasks_lock:
            orchestrator.task_manager.pending_tasks["failing_1"] = task

        # Wait for remaining tasks - this should catch and log the exception
        await orchestrator.wait_for_remaining_tasks()

        # Check that _log was called with the error
        log_calls = [str(call) for call in mock_agent._log.call_args_list]
        error_logged = any("Task failed with exception" in str(call) or "ValueError" in str(call)
                          for call in log_calls)
        assert error_logged, f"Expected error to be logged, got: {log_calls}"

    async def test_handle_iteration_cleans_up_on_llm_error(self, mock_agent):
        """Test that pending tasks message is removed even when LLM call raises."""
        orchestrator = AgentOrchestrator(mock_agent)

        # Setup: add a pending task so we get a pending_tasks_msg
        async def slow_task(tool_name, params, call_mode):
            await asyncio.sleep(10)
            return "Done"

        task_id = orchestrator.task_manager.generate_task_id("slow")
        await orchestrator.task_manager.launch_task(task_id, "slow", {}, slow_task)

        # Make LLM call raise an exception
        mock_agent._call_llm = AsyncMock(side_effect=Exception("LLM failed!"))

        # Record initial message count
        initial_msg_count = len(mock_agent.messages)

        # Call handle_iteration - it should raise but clean up
        with pytest.raises(Exception, match="LLM failed!"):
            await orchestrator.handle_iteration(1, 10)

        # Messages should be back to initial count (pending msg was added then removed)
        assert len(mock_agent.messages) == initial_msg_count

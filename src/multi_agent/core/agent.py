"""
Agent system for multi-agent framework.
Handles agent loading, execution, and LLM interaction.
"""
import asyncio
import json
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

from .config import Config
from .database import get_database
from .prompts import get_prompt_loader
from .orchestrator import AgentOrchestrator
from .llm_client import LLMClient, OpenAILLMClient
from ..tools.loader import ToolLoader
from ..tools.base import BaseTool



class AgentConfig:
    """Configuration for an agent loaded from its directory."""

    def __init__(self, name: str, agent_dir: Path):
        """
        Initialize agent configuration.

        Args:
            name: Name of the agent
            agent_dir: Path to agent's directory
        """
        self.name = name
        self.agent_dir = agent_dir

        # Load agent files
        self.description = self._load_file("description.txt")
        self.system_prompt = self._load_file("system_prompt.txt")
        self.tools = self._load_tools_list("tools.txt")

    def _load_file(self, filename: str) -> str:
        """Load content from a file in agent directory."""
        file_path = self.agent_dir / filename
        if file_path.exists():
            return file_path.read_text(encoding='utf-8').strip()
        return ""

    def _load_tools_list(self, filename: str) -> List[str]:
        """Load list of tool names from file."""
        file_path = self.agent_dir / filename
        if file_path.exists():
            content = file_path.read_text(encoding='utf-8').strip()
            # Each line is a tool name
            return [line.strip() for line in content.split('\n') if line.strip()]
        return []


class Agent:
    """Core agent class that executes tasks using LLM."""

    def __init__(
        self,
        config: AgentConfig,
        tool_loader: ToolLoader,
        agent_loader: 'AgentLoader',
        llm_client: Optional[LLMClient] = None,
        parent_agent_id: Optional[str] = None,
        parent_agent_name: str = "root",
        call_mode: str = "synchronous",
        project_dir: str = "default",
        prompt_loader=None
    ):
        """
        Initialize agent.

        Args:
            config: Agent configuration
            tool_loader: Tool loader instance
            agent_loader: Agent loader instance (for calling sub-agents)
            llm_client: LLM client instance (defaults to OpenAILLMClient)
            parent_agent_id: ID of parent agent (None if root)
            parent_agent_name: Name of parent agent
            call_mode: Execution mode ('synchronous' or 'asynchronous')
            project_dir: Project directory for this execution
            prompt_loader: Prompt loader instance (defaults to global instance)
        """
        self.config = config
        self.tool_loader = tool_loader
        self.agent_loader = agent_loader
        self.parent_agent_id = parent_agent_id
        self.parent_agent_name = parent_agent_name
        self.call_mode = call_mode
        self.project_dir = project_dir

        # Get prompt loader instance (use provided or fallback to global)
        self.prompts = prompt_loader if prompt_loader is not None else get_prompt_loader()

        # Initialize LLM client (with dependency injection support)
        if llm_client is None:
            Config.validate()
            self.llm_client = OpenAILLMClient()
        else:
            self.llm_client = llm_client

        # Track execution in database
        self.db = get_database()
        self.agent_id = self.db.create_agent_execution(
            agent_name=config.name,
            parent_agent_id=parent_agent_id,
            parent_agent_name=parent_agent_name,
            call_mode=call_mode,
            project_dir=project_dir
        )

        # Conversation history
        self.messages: List[Dict[str, str]] = []
        self._initialize_system_prompt()

        # Setup logging
        self.logs_dir = Path("logs")
        self.logs_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y_%m_%d_%H_%M_%S")
        self.log_file = self.logs_dir / f"{timestamp}_{config.name}_{self.agent_id}.log"
        # Save log file path to database
        self.db.update_log_file(self.agent_id, str(self.log_file))

        self.interaction_log = {
            "agent_id": self.agent_id,
            "agent_name": config.name,
            "parent_agent_id": parent_agent_id,
            "parent_agent_name": parent_agent_name,
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "final_response": None,
            "total_iterations": None,
            "session_ended_explicitly": None,
            "model": Config.OPENAI_MODEL,
            # interactions will be populated from self.messages at save time
            "interactions": []
        }

    def _log(self, message: str, level: str = "INFO"):
        """
        Log a message to stdout.

        Args:
            message: Message to log
            level: Log level (INFO, WARNING, ERROR, etc.)
        """
        print(message, flush=True)

    def _initialize_system_prompt(self):
        """Initialize the system prompt for this agent."""
        system_message = self.config.system_prompt

        # Add available tools information
        if self.config.tools:
            # Add header
            system_message += self.prompts.get_system_prompt('available_tools_header')

            for tool_name in self.config.tools:
                # Check if it's a regular tool
                if tool_name in self.tool_loader.get_all_tools():
                    tool = self.tool_loader.get_tool(tool_name)
                    func_def = tool.to_function_definition()
                    params = func_def['function']['parameters']

                    # Add tool description
                    system_message += self.prompts.get_system_prompt(
                        'tool_description_template',
                        tool_name=tool_name,
                        description=tool.description
                    )

                    # Add parameters
                    if params['properties']:
                        for param_name, param_info in params['properties'].items():
                            required = " (required)" if param_name in params.get('required', []) else " (optional)"
                            system_message += self.prompts.get_system_prompt(
                                'tool_parameter_line',
                                param_name=param_name,
                                param_type=param_info['type'],
                                required=required,
                                param_description=param_info.get('description', 'No description')
                            )
                    else:
                        system_message += self.prompts.get_system_prompt('tool_no_parameters')
                    system_message += "\n"

                # Check if it's another agent
                elif self.agent_loader.has_agent(tool_name):
                    agent_config = self.agent_loader.get_agent_config(tool_name)
                    system_message += self.prompts.get_system_prompt(
                        'agent_description_template',
                        tool_name=tool_name,
                        description=agent_config.description
                    )

            # Add tool calling format and rules
            system_message += self.prompts.get_system_prompt('tool_calling_format')
            system_message += self.prompts.get_system_prompt('execution_modes')
            system_message += self.prompts.get_system_prompt('tool_call_examples')
            system_message += self.prompts.get_system_prompt('critical_rules')
            system_message += self.prompts.get_system_prompt('task_management')
            system_message += self.prompts.get_system_prompt('end_session_rules')

        self.messages.append({
            "role": "system",
            "content": system_message,
            "timestamp": datetime.now().isoformat()
        })

    async def run(self, user_message: str, max_iterations: int = 50) -> str:
        """
        Run the agent with a user message (refactored with orchestrator).

        Args:
            user_message: Initial message from user
            max_iterations: Maximum number of LLM calls to prevent infinite loops

        Returns:
            Final response from agent
        """
        # Initialize orchestrator
        orchestrator = AgentOrchestrator(self)

        # Add user message
        orchestrator.conversation.add_user_message(user_message)

        iterations = 0
        final_response = ""
        llm_should_continue = True
        session_ended = False

        try:
            self._log(self.prompts.get_log_message('agent_start_separator'))
            self._log(self.prompts.get_log_message('agent_start', agent_name=self.config.name, agent_id=self.agent_id))
            self._log(self.prompts.get_log_message('user_message', user_message=user_message))
            self._log(self.prompts.get_log_message('agent_start_separator'))

            while iterations < max_iterations and not session_ended:
                # Generate response if needed
                if llm_should_continue:
                    iterations += 1
                    response, llm_should_continue, session_ended = await orchestrator.handle_iteration(
                        iterations,
                        max_iterations
                    )
                    final_response = response

                # Wait for task results
                has_pending = await orchestrator.task_manager.has_pending_tasks()
                task_result = await orchestrator.wait_for_task_result(has_pending, llm_should_continue)

                if task_result:
                    task_id, result = task_result
                    llm_should_continue = await orchestrator.process_task_result(
                        task_id,
                        result,
                        session_ended
                    )
                elif not has_pending and not llm_should_continue:
                    # No pending tasks and LLM doesn't want to continue
                    if not session_ended:
                        self._log(self.prompts.get_log_message('timeout_waiting'))
                        llm_should_continue = True
                    else:
                        break

            # Wait for remaining tasks
            await orchestrator.wait_for_remaining_tasks()

            if not session_ended and iterations >= max_iterations:
                self._log(self.prompts.get_log_message('warning_max_iterations'), "WARNING")

            self._log(self.prompts.get_log_message('agent_completed_separator'))
            self._log(self.prompts.get_log_message('agent_completed', iterations=iterations))
            self._log(self.prompts.get_log_message('session_ended_status', status=session_ended))
            self._log(self.prompts.get_log_message('agent_completed_separator'))

            return final_response

        finally:
            # Mark agent as completed in database
            self.db.complete_agent_execution(self.agent_id)

            # Save final log
            self.interaction_log["completed_at"] = datetime.now().isoformat()
            self.interaction_log["final_response"] = final_response
            self.interaction_log["total_iterations"] = iterations
            self.interaction_log["session_ended_explicitly"] = session_ended
            self._log(self.prompts.get_log_message('log_file_saved', log_file=self.log_file))
            self._save_log_file()

    async def _call_llm(self) -> str:
        """Call the LLM and get response via streaming (async version)."""
        self._log(self.prompts.get_log_message('agent_generating', agent_name=self.config.name))

        try:
            def _on_stream_update(partial_content: str):
                """Save partial streamed content to log for live monitoring."""
                self._save_log_file(streaming_content=partial_content)

            # Use injected LLM client
            response_content, response_model = await self.llm_client.generate_stream(
                messages=self.messages,
                model=Config.OPENAI_MODEL,
                temperature=0.7,
                on_stream_update=_on_stream_update
            )

            if not response_content:
                self._log(self.prompts.get_log_message('warning_empty_response'), "WARNING")

            # Save log incrementally for live monitoring
            # interactions will be populated from self.messages at save time
            self._save_log_file()

            return response_content

        except Exception as e:
            error_msg = self.prompts.get_error_message('llm_call_error', error_details=str(e))
            self._log(self.prompts.get_log_message('error_llm_call', error_message=error_msg), "ERROR")
            import traceback
            traceback.print_exc()

            # Save log incrementally even on error
            self._save_log_file()

            return error_msg

    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """
        Extract tool call from text if present.

        Args:
            text: Text that may contain a tool call

        Returns:
            Dictionary with tool_name and parameters, or None
        """
        # Look for complete tool call with opening and closing tags
        # Make <tool_call> wrapper optional to support models that don't use it
        pattern = r'(?:<tool_call>\s*)?<tool_name>(.*?)</tool_name>\s*<parameters>(.*?)</parameters>(?:\s*</tool_call>)?'
        match = re.search(pattern, text, re.DOTALL)

        if match:
            tool_name = match.group(1).strip()
            parameters_str = match.group(2).strip()

            try:
                parameters = json.loads(parameters_str)
                return {
                    'tool_name': tool_name,
                    'parameters': parameters
                }
            except json.JSONDecodeError:
                return None

        return None


    def _clean_result(self, result: str) -> str:
        """
        Clean result by removing <think> tags and other noise.

        Args:
            result: Raw result string

        Returns:
            Cleaned result string
        """
        # Remove <think>...</think> blocks
        cleaned = re.sub(r'<think>.*?</think>', '', result, flags=re.DOTALL)
        # Remove extra whitespace
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned)
        return cleaned.strip()

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], call_mode: str = 'synchronous', track_in_db: bool = True) -> str:
        """
        Execute a tool or sub-agent (async version).

        Args:
            tool_name: Name of tool or agent to execute
            parameters: Parameters for the tool/agent
            call_mode: Execution mode ('synchronous' or 'asynchronous')
            track_in_db: Whether to track this execution in database (default: True)

        Returns:
            Result of execution as string
        """
        # Validate that tool is authorized for this agent
        # Built-in tools like 'end_session' are always allowed
        built_in_tools = ['end_session']
        if tool_name not in built_in_tools and tool_name not in self.config.tools:
            authorized_tools_str = ', '.join(self.config.tools) if self.config.tools else 'none'
            error_msg = self.prompts.get_error_message(
                'tool_not_authorized',
                tool_name=tool_name,
                agent_name=self.config.name,
                authorized_tools=authorized_tools_str,
                tools_file=f"{self.config.agent_dir}/tools.txt"
            )
            self._log(self.prompts.get_log_message('security_violation', error_message=error_msg), "ERROR")
            return error_msg

        # Create tool execution record in database
        tool_execution_id = None
        if track_in_db:
            tool_execution_id = self.db.create_tool_execution(
                agent_id=self.agent_id,
                tool_name=tool_name,
                parameters=parameters,
                call_mode=call_mode
            )
            # Update agent state to executing_tool
            self.db.update_agent_state(self.agent_id, 'executing_tool')

        try:
            # Check if it's a regular tool
            if tool_name in self.tool_loader.get_all_tools():
                tool = self.tool_loader.get_tool(tool_name)
                # Run tool in thread pool (tools are sync)
                result = await asyncio.to_thread(tool.execute, **parameters)

                # Mark tool as completed in database
                if track_in_db and tool_execution_id:
                    self.db.complete_tool_execution(tool_execution_id, result)

                return result

            # Check if it's a sub-agent
            elif self.agent_loader.has_agent(tool_name):
                # Create and run sub-agent
                sub_agent = self.agent_loader.create_agent(
                    tool_name,
                    parent_agent_id=self.agent_id,
                    parent_agent_name=self.config.name,
                    call_mode=call_mode
                )

                # Extract 'query' or 'message' parameter
                user_message = parameters.get('query') or parameters.get('message', '')
                if not user_message:
                    # If no standard parameter, convert all parameters to a message
                    user_message = json.dumps(parameters)

                # Run sub-agent asynchronously
                result = await sub_agent.run(user_message)

                # Clean the result from think tags and extra whitespace
                cleaned_result = self._clean_result(result)

                # Mark tool (sub-agent) as completed in database
                if track_in_db and tool_execution_id:
                    self.db.complete_tool_execution(tool_execution_id, cleaned_result)

                return cleaned_result

            else:
                error_msg = self.prompts.get_error_message('tool_not_found', tool_name=tool_name)
                if track_in_db and tool_execution_id:
                    self.db.complete_tool_execution(tool_execution_id, error_msg)
                return error_msg

        except Exception as e:
            error_msg = self.prompts.get_error_message('tool_execution_error', tool_name=tool_name, error_details=str(e))
            if track_in_db and tool_execution_id:
                self.db.complete_tool_execution(tool_execution_id, error_msg)
            return error_msg


    def _save_log_file(self, streaming_content: str = None):
        """
        Save interaction log to file.

        Args:
            streaming_content: If provided, appends a temporary assistant message
                with this partial content and a "streaming": true flag, so the
                web frontend can display in-progress LLM output.
        """
        try:
            # Populate interactions from current messages
            # This is a flat array of all messages in conversation order
            self.interaction_log["interactions"] = self.messages.copy()

            if streaming_content is not None:
                self.interaction_log["interactions"].append({
                    "role": "assistant",
                    "content": streaming_content,
                    "timestamp": datetime.now().isoformat(),
                    "streaming": True
                })

            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.interaction_log, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Failed to save log file: {e}")


class AgentLoader:
    """Loads agents from the user/agents directory."""

    def __init__(
        self,
        agents_dir: str = "user/agents",
        tool_loader: ToolLoader = None,
        llm_client: Optional[LLMClient] = None,
        prompt_loader=None,
        project_dir: str = "default"
    ):
        """
        Initialize agent loader.

        Args:
            agents_dir: Directory containing agent subdirectories (default: user/agents)
            tool_loader: Tool loader instance
            llm_client: LLM client instance (defaults to OpenAILLMClient)
            prompt_loader: Prompt loader instance
            project_dir: Project directory for agent executions
        """
        self.agents_dir = Path(agents_dir)
        self.tool_loader = tool_loader or ToolLoader()
        self.llm_client = llm_client
        self.prompt_loader = prompt_loader
        self.project_dir = project_dir
        self._agent_configs: Dict[str, AgentConfig] = {}
        self._load_agent_configs()

    def _load_agent_configs(self):
        """Load all agent configurations from user/agents directory."""
        if not self.agents_dir.exists():
            return

        for agent_dir in self.agents_dir.iterdir():
            if agent_dir.is_dir() and not agent_dir.name.startswith("_"):
                agent_name = agent_dir.name
                try:
                    config = AgentConfig(agent_name, agent_dir)
                    self._agent_configs[agent_name] = config
                except Exception as e:
                    print(f"Error loading agent config from {agent_dir}: {e}")

    def has_agent(self, name: str) -> bool:
        """Check if agent exists."""
        return name in self._agent_configs

    def get_agent_config(self, name: str) -> AgentConfig:
        """Get agent configuration by name."""
        return self._agent_configs[name]

    def create_agent(
        self,
        name: str,
        parent_agent_id: Optional[str] = None,
        parent_agent_name: str = "root",
        call_mode: str = "synchronous"
    ) -> Agent:
        """
        Create an agent instance.

        Args:
            name: Name of the agent
            parent_agent_id: ID of parent agent
            parent_agent_name: Name of parent agent
            call_mode: Execution mode ('synchronous' or 'asynchronous')

        Returns:
            Agent instance

        Raises:
            KeyError: If agent not found
        """
        config = self._agent_configs[name]
        return Agent(
            config=config,
            tool_loader=self.tool_loader,
            agent_loader=self,
            llm_client=self.llm_client,
            parent_agent_id=parent_agent_id,
            parent_agent_name=parent_agent_name,
            call_mode=call_mode,
            project_dir=self.project_dir,
            prompt_loader=self.prompt_loader
        )

    def get_available_agents(self) -> List[str]:
        """Get list of available agent names."""
        return list(self._agent_configs.keys())

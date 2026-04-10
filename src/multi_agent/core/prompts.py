"""
Prompt management system for multi-agent framework.
Loads and manages prompts from YAML configuration files with fallback support.
"""
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging


class PromptLoader:
    """
    Loads and manages prompts from YAML configuration files.

    Provides fallback to hardcoded defaults when prompts are missing or malformed.
    Supports variable substitution in prompt templates.
    """

    # Hardcoded fallback prompts (minimal defaults)
    FALLBACK_PROMPTS = {
        'system_prompts': {
            'available_tools_header': '\n\n## Available Tools\n\nYou have access to the following tools:\n\n',
            'tool_description_template': '### {tool_name}\n{description}\n\nParameters:\n',
            'tool_no_parameters': '  No parameters\n',
            'tool_parameter_line': '  - {param_name} ({param_type}){required}: {param_description}\n',
            'agent_description_template': '### {tool_name} (Agent)\n{description}\n\nParameters:\n  - message (string) (required): Message or query to send to the agent\n\n',
            'tool_calling_format': '\n## Tool Calling Format\n\nIMPORTANT: You MUST use the EXACT XML format shown below. Do NOT use any other format.\nDo NOT use formats like <|tool_call>call:name{...}<tool_call|> or similar — they will be IGNORED.\nThe ONLY format the system can parse is this:\n\n<tool_call>\n<tool_name>name_of_tool</tool_name>\n<parameters>\n{"param1": "value1"}\n</parameters>\n</tool_call>\n\nOptional tags inside <tool_call>:\n- <call_mode>synchronous|asynchronous</call_mode> (defaults to synchronous)\n- <wait_for_all_finished>true|false</wait_for_all_finished> (defaults to false)\n- <include_call_params_in_response /> or <include_call_params_in_response>true</include_call_params_in_response> — when present, the result message you receive will include the parameters you passed. Use this when you make several calls to the SAME tool in one response and need to match results to calls.\n\n',
            'execution_modes': '## Execution Modes\n\n**synchronous**: Tool executes immediately\n**asynchronous**: Tool runs in background\n**wait_for_all_finished**: If set to true for any asynchronous call in a response, the system will wait for ALL outstanding tasks to complete before giving you control again. Results will be delivered as a single batch.\n**include_call_params_in_response**: Optional flag that echoes your input parameters back in the tool result message, so you can tell several calls to the same tool apart. Only use it when needed — it adds tokens to the result.\n\n',
            'tool_call_examples': 'EXAMPLES:\n\n<tool_call>\n<tool_name>calculator</tool_name>\n<parameters>\n{"operation": "add", "a": 5, "b": 3}\n</parameters>\n</tool_call>\n\n<tool_call>\n<tool_name>question_answerer</tool_name>\n<call_mode>asynchronous</call_mode>\n<wait_for_all_finished>true</wait_for_all_finished>\n<parameters>\n{"message": "What is the capital of France?"}\n</parameters>\n</tool_call>\n\nExample — two calls to the same tool with include_call_params_in_response so results are unambiguous:\n\n<tool_call>\n<tool_name>calculator</tool_name>\n<include_call_params_in_response />\n<parameters>\n{"operation": "add", "a": 2, "b": 5}\n</parameters>\n</tool_call>\n<tool_call>\n<tool_name>calculator</tool_name>\n<include_call_params_in_response />\n<parameters>\n{"operation": "add", "a": 4, "b": 2}\n</parameters>\n</tool_call>\n\n',
            'critical_rules': 'CRITICAL RULES:\n- NEVER use <|tool_call>call:name{...}<tool_call|> format — it DOES NOT WORK\n- ALWAYS wrap every tool call in <tool_call>...</tool_call> tags\n- ALWAYS use <tool_name>...</tool_name> for the tool name\n- ALWAYS use <parameters>...</parameters> with a valid JSON object (double quotes)\n- <call_mode> is optional (defaults to synchronous)\n- <wait_for_all_finished> is optional (defaults to false)\n- <include_call_params_in_response> is optional — only add it when you need the system to echo your parameters back alongside the result (e.g. to disambiguate several calls to the same tool). Accepts self-closing form <include_call_params_in_response /> or <include_call_params_in_response>true</include_call_params_in_response>.\n\n',
            'task_management': '## Task Management\n\nEach tool call gets a unique TASK ID. Do not create duplicate tasks.\n\n',
            'end_session_rules': '## CRITICAL: When to Call end_session\n\nYOU MUST NOT call end_session if there are pending tasks!\n\n'
        },
        'runtime_messages': {
            'pending_tasks_header': '=== CURRENTLY PENDING TASKS ===\n\nYou have {pending_count} task(s) running:\n\n',
            'pending_task_item': 'Task ID: {task_id}\n  Tool/Agent: {tool_name}\n  Parameters: {parameters}\n  Launched at: {launched_at}\n\n',
            'pending_tasks_reminder': 'REMINDER: Do not create duplicate tasks.\n================================\n',
            'tasks_launched_notification': 'SYSTEM NOTIFICATION: {task_count} task(s) launched:\n{task_list}\n\nDO NOT create duplicate tasks.\n',
            'wait_for_async_acknowledged': 'Acknowledged: Waiting for all async tasks to complete as requested. All results will be delivered at once.\n',
            'wait_for_async_no_tasks': 'Note: wait_for_all_finished was requested, but there are no outstanding async tasks.\n',
            'all_tasks_completed_batch_header': 'All {task_count} async task(s) have completed. Results:\n\n',
            'all_tasks_completed_batch_item': "--- Task '{task_id}' result ---\n{result}\n\n",
            'all_tasks_completed_batch_item_with_input': "--- Task '{task_id}' ({tool_name} called with parameters {parameters}) result ---\n{result}\n\n",
            'task_completed': "Task '{task_id}' completed:\n{result}",
            'task_completed_with_input': "Task '{task_id}' ({tool_name} called with parameters {parameters}) completed:\n{result}",
            'tool_result': "Tool '{tool_name}' result:\n{result}",
            'tool_result_with_input': "Tool '{tool_name}' called with parameters {parameters} returned:\n{result}",
            'no_tool_call_warning': 'SYSTEM ERROR: No valid tool call detected! Do NOT use <|tool_call>call:name{...}<tool_call|> format — it does not work.\n\nYou MUST use this EXACT format:\n<tool_call>\n<tool_name>end_session</tool_name>\n<parameters>\n{"final_message": "Your response"}\n</parameters>\n</tool_call>\n',
            'end_session_with_pending_tasks_error': 'Error: You called end_session with {pending_count} pending tasks!\n\nPending: {task_list}\n\nend_session call IGNORED.\n'
        },
        'log_messages': {
            'agent_start_separator': '=' * 80,
            'agent_start': 'Starting agent: {agent_name} (ID: {agent_id})',
            'user_message': 'User message: {user_message}',
            'iteration_separator': '--- Iteration {iteration}/{max_iterations} ---',
            'agent_generating': '[Agent: {agent_name}] Generating response...',
            'tool_calls_detected': '[{count} Tool Call(s) Detected]',
            'executing_sync_tools': '[Executing {count} synchronous tool call(s)...]',
            'executing_sync_tool': '  Executing (sync): {tool_name} with {parameters}',
            'tool_result_log': '  Result: {result}',
            'launching_async_tools': '[Launching {count} asynchronous tool call(s)...]',
            'launching_async_tool': '  Launching (async): {tool_name} with {parameters}',
            'task_launched': '[Task {task_id} launched asynchronously]',
            'task_completed_log': '[Task Completed: {task_id}]',
            'task_result_log': '  Result: {result}',
            'end_session_called': '[END_SESSION called - agent will terminate after pending tasks complete]',
            'final_response_log': '[Final response to return: {response}]',
            'waiting_for_remaining_tasks': '[Waiting for {count} remaining task(s) to complete...]',
            'agent_completed_separator': '=' * 80,
            'agent_completed': 'Agent completed after {iterations} iteration(s)',
            'session_ended_status': 'Session ended explicitly: {status}',
            'log_file_saved': '[Log saved to: {log_file}]',
            'warning_end_session_with_pending': '[WARNING] Agent attempted to call end_session with {count} pending tasks!',
            'warning_pending_tasks_list': '[WARNING] Pending tasks: {task_list}',
            'warning_no_tool_call': '[WARNING: No tool call detected. Agent should call end_session when done.]',
            'warning_max_iterations': '[WARNING: Max iterations reached without end_session call]',
            'warning_empty_response': '[WARNING: Empty response from LLM]',
            'error_llm_call': '[ERROR] {error_message}',
            'security_violation': '[SECURITY VIOLATION] {error_message}',
            'timeout_waiting': '[Timeout waiting for tasks - continuing]'
        },
        'error_messages': {
            'tool_not_authorized': "SECURITY ERROR: Tool/agent '{tool_name}' is not authorized for agent '{agent_name}'. Authorized tools: {authorized_tools}. To use this tool, add it to the file: {tools_file}",
            'tool_not_found': "Error: Tool or agent '{tool_name}' not found",
            'tool_execution_error': "Error executing tool/agent '{tool_name}': {error_details}",
            'llm_call_error': "Error calling LLM: {error_details}",
            'agent_failed_to_finish': "This agent failed to finish its job. You either have to run a new one or ignore this situation."
        }
    }

    def __init__(self, prompts_file: Optional[str] = None, prompts_dir: str = "user/prompts"):
        """
        Initialize PromptLoader.

        Args:
            prompts_file: Name of YAML file to load (default: "default.yaml")
            prompts_dir: Directory containing prompt files (default: "user/prompts")
        """
        self.prompts_dir = Path(prompts_dir)
        self.prompts_file = prompts_file or "default.yaml"
        self.prompts: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)

        # Load prompts from YAML file
        self._load_prompts()

    def _load_prompts(self):
        """Load prompts from YAML file with error handling."""
        yaml_path = self.prompts_dir / self.prompts_file

        if not yaml_path.exists():
            self.logger.warning(f"Prompts file not found: {yaml_path}. Using fallback prompts.")
            self.prompts = self.FALLBACK_PROMPTS.copy()
            return

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                loaded_prompts = yaml.safe_load(f)

            if not loaded_prompts:
                self.logger.warning(f"Empty prompts file: {yaml_path}. Using fallback prompts.")
                self.prompts = self.FALLBACK_PROMPTS.copy()
                return

            # Merge loaded prompts with fallback (fallback as base, loaded overrides)
            self.prompts = self._deep_merge(self.FALLBACK_PROMPTS.copy(), loaded_prompts)
            self.logger.info(f"Successfully loaded prompts from: {yaml_path}")

        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML file {yaml_path}: {e}. Using fallback prompts.")
            self.prompts = self.FALLBACK_PROMPTS.copy()
        except Exception as e:
            self.logger.error(f"Unexpected error loading prompts from {yaml_path}: {e}. Using fallback prompts.")
            self.prompts = self.FALLBACK_PROMPTS.copy()

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """
        Deep merge two dictionaries (override takes precedence).

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def get_prompt(self, category: str, key: str, **kwargs) -> str:
        """
        Get a prompt by category and key with variable substitution.

        Args:
            category: Prompt category (e.g., 'system_prompts', 'runtime_messages')
            key: Prompt key within category
            **kwargs: Variables to substitute in the prompt template

        Returns:
            Formatted prompt string, or fallback if not found
        """
        try:
            # Navigate to the prompt
            prompt_template = self.prompts.get(category, {}).get(key, None)

            # If not found, try fallback
            if prompt_template is None:
                fallback = self.FALLBACK_PROMPTS.get(category, {}).get(key, '')
                if not fallback:
                    self.logger.warning(f"Prompt not found: {category}.{key}. Using empty string.")
                    return ''
                self.logger.debug(f"Using fallback for: {category}.{key}")
                prompt_template = fallback

            # Handle variable substitution
            if kwargs:
                try:
                    # Format the prompt with provided variables
                    return prompt_template.format(**kwargs)
                except KeyError as e:
                    self.logger.warning(f"Missing variable {e} in prompt {category}.{key}. Returning unformatted.")
                    return prompt_template
                except Exception as e:
                    self.logger.error(f"Error formatting prompt {category}.{key}: {e}")
                    return prompt_template

            return prompt_template

        except Exception as e:
            self.logger.error(f"Error getting prompt {category}.{key}: {e}")
            return ''

    def get_system_prompt(self, key: str, **kwargs) -> str:
        """
        Convenience method to get system prompts.

        Args:
            key: Prompt key
            **kwargs: Variables to substitute

        Returns:
            Formatted prompt string
        """
        return self.get_prompt('system_prompts', key, **kwargs)

    def get_runtime_message(self, key: str, **kwargs) -> str:
        """
        Convenience method to get runtime messages.

        Args:
            key: Message key
            **kwargs: Variables to substitute

        Returns:
            Formatted message string
        """
        return self.get_prompt('runtime_messages', key, **kwargs)

    def get_log_message(self, key: str, **kwargs) -> str:
        """
        Convenience method to get log messages.

        Args:
            key: Message key
            **kwargs: Variables to substitute

        Returns:
            Formatted log message string
        """
        return self.get_prompt('log_messages', key, **kwargs)

    def get_error_message(self, key: str, **kwargs) -> str:
        """
        Convenience method to get error messages.

        Args:
            key: Message key
            **kwargs: Variables to substitute

        Returns:
            Formatted error message string
        """
        return self.get_prompt('error_messages', key, **kwargs)

    def format_task_list(self, task_ids: list) -> str:
        """
        Format a list of task IDs for display.

        Args:
            task_ids: List of task ID strings

        Returns:
            Formatted task list string
        """
        return "\n".join([f"  - {tid}" for tid in task_ids])

    def reload(self):
        """Reload prompts from file (useful for runtime updates)."""
        self._load_prompts()
        self.logger.info("Prompts reloaded")


# Global prompt loader instance (will be initialized by config)
_prompt_loader: Optional[PromptLoader] = None


def get_prompt_loader(prompts_file: Optional[str] = None) -> PromptLoader:
    """
    Get or create the global PromptLoader instance.

    Args:
        prompts_file: Optional prompts file name (only used on first call)

    Returns:
        PromptLoader instance
    """
    global _prompt_loader

    if _prompt_loader is None:
        _prompt_loader = PromptLoader(prompts_file=prompts_file)

    return _prompt_loader


def set_prompt_loader(prompts_file: Optional[str] = None, prompts_dir: str = "user/prompts"):
    """
    Set/reset the global PromptLoader instance.

    Args:
        prompts_file: Prompts file name to use
        prompts_dir: Directory containing prompt files
    """
    global _prompt_loader
    _prompt_loader = PromptLoader(prompts_file=prompts_file, prompts_dir=prompts_dir)

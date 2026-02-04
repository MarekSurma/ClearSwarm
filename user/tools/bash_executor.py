"""
Bash command executor tool for running shell commands.
"""
import subprocess
from multi_agent.tools.base import BaseTool


class BashExecutorTool(BaseTool):
    """Tool for executing bash commands."""

    @property
    def name(self) -> str:
        return "bash_executor"

    @property
    def description(self) -> str:
        return "Executes bash commands and returns the output or error"

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "string",
                    "description": "The bash command to execute (e.g., 'mkdir -p mydir', 'touch file.txt')"
                }
            },
            "required": ["command"]
        }

    def execute(self, command: str) -> str:
        """
        Execute a bash command.

        Args:
            command: The bash command to run

        Returns:
            Command output or error message
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                output = result.stdout.strip()
                if output:
                    return f"Command executed successfully:\n{output}"
                else:
                    return f"Command executed successfully (no output)"
            else:
                return f"Command failed with exit code {result.returncode}:\n{result.stderr.strip()}"

        except subprocess.TimeoutExpired:
            return "Error: Command timed out (30 second limit)"
        except Exception as e:
            return f"Error executing command: {str(e)}"

"""
Base classes for tools in the multi-agent system.
"""
import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseTool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of the tool."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Return description of what the tool does."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """
        Execute the tool with given arguments.

        Args:
            **kwargs: Tool-specific arguments

        Returns:
            Result of tool execution as string
        """
        pass

    def get_parameters_schema(self) -> Dict[str, Any]:
        """
        Override this method to provide custom parameter descriptions.

        Returns:
            Dictionary with parameter descriptions or None to use auto-generated
        """
        return None

    def to_function_definition(self) -> dict:
        """
        Convert tool to OpenAI function definition format.

        Returns:
            Dictionary representing the function for OpenAI API
        """
        # Check if tool provides custom parameter schema
        custom_schema = self.get_parameters_schema()

        if custom_schema:
            return {
                "type": "function",
                "function": {
                    "name": self.name,
                    "description": self.description,
                    "parameters": custom_schema
                }
            }

        # Auto-generate from execute method signature
        sig = inspect.signature(self.execute)
        parameters = {
            "type": "object",
            "properties": {},
            "required": []
        }

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_type = "string"  # Default type
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"

            parameters["properties"][param_name] = {
                "type": param_type,
                "description": f"Parameter {param_name}"
            }

            if param.default == inspect.Parameter.empty:
                parameters["required"].append(param_name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters
            }
        }

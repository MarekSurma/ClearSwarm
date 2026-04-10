"""
Calculator tool for basic arithmetic operations.
"""
from multi_agent.tools.base import BaseTool


class CalculatorTool(BaseTool):
    """Tool for performing basic arithmetic calculations."""

    @property
    def name(self) -> str:
        return "calculator"

    @property
    def description(self) -> str:
        return (
            "Performs basic arithmetic operations. Use exact operation names: "
            "'add', 'subtract', 'multiply', 'divide'. "
            "MANDATORY: You MUST call this tool with the <include_call_params_in_response /> "
            "flag. Results are short numbers and it is easy to lose track of "
            "which result belongs to which call when you issue several "
            "calculations in one response. Echoing the input parameters back "
            "alongside the result removes that ambiguity at a negligible "
            "token cost. "
            "Example usage:\n"
            "<tool_call>\n"
            "  <tool_name>calculator</tool_name>\n"
            "  <include_call_params_in_response />\n"
            "  <parameters>\n"
            "    {\"operation\": \"add\", \"a\": 10, \"b\": 5}\n"
            "  </parameters>\n"
            "</tool_call>"
        )

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "description": "Operation to perform. Must be one of: 'add', 'subtract', 'multiply', 'divide'",
                    "enum": ["add", "subtract", "multiply", "divide"]
                },
                "a": {
                    "type": "number",
                    "description": "First number"
                },
                "b": {
                    "type": "number",
                    "description": "Second number"
                }
            },
            "required": ["operation", "a", "b"]
        }

    def execute(self, operation: str, a: float, b: float) -> str:
        """
        Execute arithmetic operation.

        Args:
            operation: One of 'add', 'subtract', 'multiply', 'divide'
            a: First number
            b: Second number

        Returns:
            Result of the operation
        """
        a = float(a)
        b = float(b)

        if operation == "add":
            result = a + b
        elif operation == "subtract":
            result = a - b
        elif operation == "multiply":
            result = a * b
        elif operation == "divide":
            if b == 0:
                return "Error: Division by zero"
            result = a / b
        else:
            return f"Error: Unknown operation '{operation}'"

        return f"Result: {result}"

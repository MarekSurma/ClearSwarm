"""
Text analyzer tool for analyzing text properties.
"""
from multi_agent.tools.base import BaseTool


class TextAnalyzerTool(BaseTool):
    """Tool for analyzing text (word count, character count, etc.)."""

    @property
    def name(self) -> str:
        return "text_analyzer"

    @property
    def description(self) -> str:
        return "Analyzes text and returns statistics (word count, character count, line count)"

    def get_parameters_schema(self):
        """Provide detailed parameter descriptions."""
        return {
            "type": "object",
            "properties": {
                "text": {
                    "type": "string",
                    "description": "The text to analyze"
                }
            },
            "required": ["text"]
        }

    def execute(self, text: str) -> str:
        """
        Analyze text and return statistics.

        Args:
            text: Text to analyze

        Returns:
            Statistics about the text
        """
        lines = text.split('\n')
        words = text.split()
        chars = len(text)
        chars_no_spaces = len(text.replace(' ', '').replace('\n', ''))

        result = f"Text Analysis:\n"
        result += f"- Characters (with spaces): {chars}\n"
        result += f"- Characters (without spaces): {chars_no_spaces}\n"
        result += f"- Words: {len(words)}\n"
        result += f"- Lines: {len(lines)}\n"

        return result

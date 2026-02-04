"""
End session tool - signals that the agent has completed its work.
"""
from multi_agent.tools.base import BaseTool


class EndSession(BaseTool):
    """Tool that signals the agent wants to end the session."""

    @property
    def name(self) -> str:
        return "end_session"

    @property
    def description(self) -> str:
        return (
            "Call this tool when you have completed your task and are ready to end the session. "
            "You should call this ONLY when:\n"
            "- You have fully answered the user's request\n"
            "- All necessary sub-tasks are complete\n"
            "- You have provided your final response to the user\n"
            "- You have no more work to do"
        )

    def execute(self, final_message: str = "") -> str:
        """
        Execute the end session action.

        Args:
            final_message: Optional final message to the user before ending

        Returns:
            Confirmation that session is ending
        """
        if final_message:
            return f"SESSION_END: {final_message}"
        return "SESSION_END"

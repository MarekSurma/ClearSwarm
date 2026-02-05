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
            "Call this tool when you have completed your task and are ready to end the session. Whole end message HAS TO go to the final_message field.\n"
            "You MUST not return anything outside of the end_session tool call. Whole message has to go into the final_message section."
            "You should call this ONLY when:\n"
            "- You know how to answer the user's request\n"
            "- All necessary sub-tasks are complete\n"
            "- You have no more work to do\n"
            "- you place your HWOLE answer in the final_message parameter"
        )

    def execute(self, final_message: str = "") -> str:
        """
        Execute the end session action.

        Args:
            final_message: Mandatory final message to the user before ending

        Returns:
            Confirmation that session is ending
        """
        if final_message:
            return f"SESSION_END: {final_message}"
        return "SESSION_END"

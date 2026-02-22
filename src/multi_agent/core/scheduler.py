"""
Scheduler service for cyclic agent execution.
Runs as a background task and triggers agents based on schedules.
"""
import asyncio
import logging
from typing import Optional
from datetime import datetime

from .database import get_database

logger = logging.getLogger(__name__)


class SchedulerService:
    """Background service that monitors and triggers scheduled agent runs."""

    def __init__(self):
        """Initialize the scheduler service."""
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._check_interval = 30  # Check every 30 seconds

    async def start(self) -> None:
        """Start the scheduler service."""
        if self._running:
            logger.warning("Scheduler service is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._run_loop())
        logger.info("Scheduler service started")

    async def stop(self) -> None:
        """Stop the scheduler service."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("Scheduler service stopped")

    async def _run_loop(self) -> None:
        """Main loop that periodically checks for due schedules."""
        logger.info("Scheduler loop started")

        while self._running:
            try:
                await self._check_and_run_due_schedules()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Wait before next check
            try:
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break

        logger.info("Scheduler loop stopped")

    async def _check_and_run_due_schedules(self) -> None:
        """Check for due schedules and trigger agent runs."""
        db = get_database()
        due_schedules = db.get_due_schedules()

        if not due_schedules:
            return

        logger.info(f"Found {len(due_schedules)} due schedule(s)")

        for schedule in due_schedules:
            try:
                await self._trigger_agent_run(schedule)
                # Mark as run after successful trigger
                db.mark_schedule_run(schedule['schedule_id'])
                logger.info(
                    f"Triggered schedule '{schedule['name']}' "
                    f"(agent: {schedule['agent_name']})"
                )
            except Exception as e:
                logger.error(
                    f"Failed to trigger schedule '{schedule['name']}': {e}",
                    exc_info=True
                )
                # Still mark as run to avoid getting stuck
                db.mark_schedule_run(schedule['schedule_id'])

    async def _trigger_agent_run(self, schedule: dict) -> None:
        """
        Trigger an agent run for a schedule.

        Args:
            schedule: Schedule dictionary with agent_name, message, project_dir
        """
        # Import here to avoid circular imports
        from ..web_interface.api.agents import get_loaders, _track_task, _untrack_task

        tool_loader, agent_loader, prompt_loader = get_loaders(schedule['project_dir'])

        # Create agent instance
        agent = agent_loader.create_agent(schedule['agent_name'])
        if not agent:
            raise ValueError(f"Agent '{schedule['agent_name']}' not found")

        # Create task and track it
        task = asyncio.create_task(agent.run(schedule['message']))
        task_id = f"schedule_{schedule['schedule_id']}_{datetime.now().timestamp()}"

        # Track task so it appears in execution monitor
        await _track_task(task_id, task)

        # Set up cleanup when task completes
        def cleanup_callback(t):
            asyncio.create_task(_untrack_task(task_id))

        task.add_done_callback(cleanup_callback)


# Global scheduler instance
_scheduler_instance: Optional[SchedulerService] = None


def get_scheduler() -> SchedulerService:
    """Get or create the global scheduler instance."""
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = SchedulerService()
    return _scheduler_instance

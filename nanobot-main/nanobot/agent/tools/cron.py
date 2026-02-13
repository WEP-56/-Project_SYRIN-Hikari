"""Cron tool for scheduling reminders and tasks."""

from typing import Any

from nanobot.agent.tools.base import Tool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


class CronTool(Tool):
    """Tool to schedule reminders and recurring tasks."""
    
    def __init__(self, cron_service: CronService):
        self._cron = cron_service
        self._channel = ""
        self._chat_id = ""
        self._session_id = ""
    
    def set_context(self, channel: str, chat_id: str, session_id: str = "") -> None:
        """Set the current session context for delivery."""
        self._channel = channel
        self._chat_id = chat_id
        self._session_id = session_id
    
    @property
    def name(self) -> str:
        return "cron"
    
    @property
    def description(self) -> str:
        return "Schedule reminders and recurring tasks. Actions: add, list, remove."
    
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove"],
                    "description": "Action to perform"
                },
                "message": {
                    "type": "string",
                    "description": "Reminder message (for add)"
                },
                "every_seconds": {
                    "type": "integer",
                    "description": "Interval in seconds (for recurring tasks)"
                },
                "cron_expr": {
                    "type": "string",
                    "description": "Cron expression like '0 9 * * *' (for scheduled tasks)"
                },
                "job_id": {
                    "type": "string",
                    "description": "Job ID (for remove)"
                },
                "one_time": {
                    "type": "boolean",
                    "description": "Set to true if this is a one-time reminder (not recurring)"
                }
            },
            "required": ["action"]
        }
    
    async def execute(
        self,
        action: str,
        message: str = "",
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        job_id: str | None = None,
        **kwargs: Any
    ) -> str:
        if action == "add":
            return self._add_job(message, every_seconds, cron_expr)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(job_id)
        return f"Unknown action: {action}"
    
    def _add_job(self, message: str, every_seconds: int | None, cron_expr: str | None) -> str:
        if not message:
            return "Error: message is required for add"
        if not self._channel or not self._chat_id:
            return "Error: no session context (channel/chat_id)"
        
        # Build schedule
        # For "in X seconds/minutes", we should use "at" with a specific time, 
        # OR use "every" with delete_after_run=True. 
        # Using "at" is safer for one-off reminders.
        
        import time
        now_ms = int(time.time() * 1000)
        delete_after_run = False
        
        if every_seconds:
            # If it's a "remind me in X" style (often implied by single action), we might want delete_after_run
            # But the tool param says "every_seconds", implying recurrence.
            # Let's assume if it's explicitly "every", it's recurring.
            # If the user prompt was "in 1 minute", the LLM should ideally convert to a timestamp or use a different flag.
            # However, current parameters are limited. 
            # Let's strictly follow parameters: every_seconds -> recurring.
            
            # Wait, if the user said "remind me in 1 min", LLM might use every_seconds=60.
            # We need to detect intent. For now, let's trust the LLM. 
            # But to be safe against infinite loops, let's enforce a minimum interval
            if every_seconds < 5:
                every_seconds = 5 # Minimum 5s interval
                
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
            
            # Heuristic: If message contains "in ... minutes/seconds" and NOT "every", it might be one-off.
            # But we can't easily know here. 
            # Let's rely on 'delete_after_run' param if we add it to execute, 
            # OR we change how we calculate 'at'.
            
            # Ideally, we should add 'type' param to execute: 'one-off' or 'recurring'.
            # For now, let's add a hack: if message starts with "Reminder:", treat as one-off? No.
            
            # Let's just stick to the schedule. 
            pass
            
        elif cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr)
        else:
            return "Error: either every_seconds or cron_expr is required"
        
        # If it's a one-time reminder (which we can't fully distinguish from 'every' without more params),
        # we risk the loop.
        # FIX: Let's assume 'every_seconds' implies RECURRING unless we have a way to specify one-off.
        # We'll add a 'one_time' parameter to the tool definition.
        
        job = self._cron.add_job(
            name=message[:30],
            schedule=schedule,
            message=message,
            deliver=True,
            channel=self._channel,
            to=self._chat_id,
            delete_after_run=kwargs.get('one_time', False),
            session_id=self._session_id,
        )
        return f"Created job '{job.name}' (id: {job.id})"
    
    def _list_jobs(self) -> str:
        jobs = self._cron.list_jobs()
        if not jobs:
            return "No scheduled jobs."
        lines = [f"- {j.name} (id: {j.id}, {j.schedule.kind})" for j in jobs]
        return "Scheduled jobs:\n" + "\n".join(lines)
    
    def _remove_job(self, job_id: str | None) -> str:
        if not job_id:
            return "Error: job_id is required for remove"
        if self._cron.remove_job(job_id):
            return f"Removed job {job_id}"
        return f"Job {job_id} not found"

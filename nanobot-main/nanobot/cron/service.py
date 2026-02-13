"""Cron service for scheduling agent tasks using SQLite storage."""

import asyncio
import json
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Coroutine, List, Optional

from loguru import logger

from nanobot.cron.types import CronJob, CronJobState, CronPayload, CronSchedule
from nanobot.storage.db import Database
from nanobot.storage.models import CronJobModel
from nanobot.session.manager import SessionManager


def _now_ms() -> int:
    return int(time.time() * 1000)


def _compute_next_run(schedule: CronSchedule, now_ms: int) -> int | None:
    """Compute next run time in ms."""
    if schedule.kind == "at":
        return schedule.at_ms if schedule.at_ms and schedule.at_ms > now_ms else None
    
    if schedule.kind == "every":
        if not schedule.every_ms or schedule.every_ms <= 0:
            return None
        # Next interval from now
        return now_ms + schedule.every_ms
    
    if schedule.kind == "cron" and schedule.expr:
        try:
            from croniter import croniter
            cron = croniter(schedule.expr, time.time())
            next_time = cron.get_next()
            return int(next_time * 1000)
        except Exception:
            return None
    
    return None


class CronService:
    """Service for managing and executing scheduled jobs."""
    
    def __init__(
        self,
        db: Database,
        session_manager: SessionManager,
        on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None = None
    ):
        self.db = db
        self.session_manager = session_manager
        self.on_job = on_job
        self._timer_task: asyncio.Task | None = None
        self._running = False
        self._retry_timers: dict[str, asyncio.TimerHandle] = {} # For busy retry
    
    def _model_to_job(self, model: CronJobModel) -> CronJob:
        """Convert DB model to CronJob type."""
        # Parse schedule
        sched_dict = model.schedule
        schedule = CronSchedule(
            kind=sched_dict.get("kind", "every"),
            at_ms=sched_dict.get("at_ms"),
            every_ms=sched_dict.get("every_ms"),
            expr=sched_dict.get("expr"),
            tz=sched_dict.get("tz"),
        )
        
        # Parse payload
        pay_dict = model.payload
        payload = CronPayload(
            kind=pay_dict.get("kind", "agent_turn"),
            message=pay_dict.get("message", ""),
            deliver=pay_dict.get("deliver", False),
            channel=pay_dict.get("channel"),
            to=pay_dict.get("to"),
        )
        
        return CronJob(
            id=model.id,
            name=model.name,
            enabled=model.enabled,
            session_id=model.session_id,
            schedule=schedule,
            payload=payload,
            state=CronJobState(
                next_run_at_ms=model.next_run_at,
                # We don't store last_run/error in main table for now or we do?
                # The model has basic fields. We might need to extend model or store state in meta.
                # For now, let's just use what we have.
            ),
            created_at_ms=model.created_at,
            updated_at_ms=model.updated_at,
            # delete_after_run needs to be stored! 
            # Currently CronJobModel doesn't have delete_after_run column.
            # We can put it in payload or schedule or add a column.
            # Let's put it in payload for now as a workaround or assume False.
            delete_after_run=pay_dict.get("delete_after_run", False)
        )

    def _job_to_model(self, job: CronJob) -> CronJobModel:
        """Convert CronJob type to DB model."""
        schedule_dict = {
            "kind": job.schedule.kind,
            "at_ms": job.schedule.at_ms,
            "every_ms": job.schedule.every_ms,
            "expr": job.schedule.expr,
            "tz": job.schedule.tz,
        }
        
        payload_dict = {
            "kind": job.payload.kind,
            "message": job.payload.message,
            "deliver": job.payload.deliver,
            "channel": job.payload.channel,
            "to": job.payload.to,
            "delete_after_run": job.delete_after_run # Store here
        }
        
        return CronJobModel(
            id=job.id,
            session_id=job.session_id or "", # Must have session_id
            name=job.name,
            schedule_json=json.dumps(schedule_dict),
            payload_json=json.dumps(payload_dict),
            next_run_at=job.state.next_run_at_ms,
            enabled=job.enabled,
            created_at=job.created_at_ms,
            updated_at=job.updated_at_ms
        )

    async def start(self) -> None:
        """Start the cron service."""
        self._running = True
        
        # Check for missed jobs (system resume)
        self._handle_missed_jobs()
        
        self._arm_timer()
        logger.info("Cron service started")

    def stop(self) -> None:
        """Stop the cron service."""
        self._running = False
        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

    def _handle_missed_jobs(self) -> None:
        """Check for jobs that should have run but didn't (e.g. system sleep)."""
        now = _now_ms()
        # Get all enabled jobs with next_run_at < now
        due_jobs = self.db.get_due_jobs(now)
        
        for model in due_jobs:
            job = self._model_to_job(model)
            logger.warning(f"Cron: Missed job '{job.name}' (due {job.state.next_run_at_ms}, now {now})")
            
            # Logic for missed jobs:
            # 1. If it's a one-off ("at"), it's missed. Maybe notify user?
            # 2. If it's recurring ("every"/"cron"), we might want to run it NOW or skip to next.
            # For safety, let's run it now (it will be caught by _on_timer anyway if we don't change next_run).
            # But _on_timer handles execution.
            pass

    def _get_next_wake_ms(self) -> int | None:
        """Get the earliest next run time across all jobs."""
        # We can query DB for min(next_run_at) where enabled=1
        # But for now, let's fetch all active jobs.
        # Optimization: Add DB method get_next_run_time()
        # For now, listing is okay for small number of jobs.
        jobs = self.db.list_jobs()
        times = [j.next_run_at for j in jobs if j.enabled and j.next_run_at]
        return min(times) if times else None
    
    def _arm_timer(self) -> None:
        """Schedule the next timer tick."""
        if self._timer_task:
            self._timer_task.cancel()
        
        next_wake = self._get_next_wake_ms()
        if not next_wake or not self._running:
            return
        
        delay_ms = max(0, next_wake - _now_ms())
        delay_s = delay_ms / 1000
        
        async def tick():
            await asyncio.sleep(delay_s)
            if self._running:
                await self._on_timer()
        
        self._timer_task = asyncio.create_task(tick())
    
    async def _on_timer(self) -> None:
        """Handle timer tick - run due jobs."""
        if not self._running:
            return
            
        now = _now_ms()
        due_models = self.db.get_due_jobs(now)
        
        for model in due_models:
            job = self._model_to_job(model)
            await self._execute_job(job)
        
        self._arm_timer()

    async def _execute_job(self, job: CronJob) -> None:
        """Execute a single job."""
        # 1. Session Binding Check
        if not job.session_id:
            logger.error(f"Cron: Job '{job.name}' has no session_id. Disabling.")
            job.enabled = False
            self.db.update_job(self._job_to_model(job))
            return

        session = self.session_manager.get_by_id(job.session_id)
        if not session:
            logger.warning(f"Cron: Session {job.session_id} not found for job '{job.name}'. Disabling.")
            job.enabled = False
            self.db.update_job(self._job_to_model(job))
            return

        # 2. Busy Guard Check
        if getattr(session, "is_processing", False):
            logger.info(f"Cron: Session {job.session_id} is busy. Rescheduling job '{job.name}' in 5s.")
            # Reschedule logic: Don't change next_run_at in DB (so it stays due), 
            # but wait 5s before retrying this specific job loop?
            # Or better: push next_run_at by 5s.
            job.state.next_run_at_ms = _now_ms() + 5000
            self.db.update_job(self._job_to_model(job))
            return

        # 3. Execution
        start_ms = _now_ms()
        logger.info(f"Cron: executing job '{job.name}' ({job.id})")
        
        try:
            if self.on_job:
                await self.on_job(job)
            logger.info(f"Cron: job '{job.name}' completed")
            
        except Exception as e:
            logger.error(f"Cron: job '{job.name}' failed: {e}")
        
        # 4. Update State (Next Run)
        job.updated_at_ms = _now_ms()
        
        if job.delete_after_run:
             logger.info(f"Cron: Deleting job '{job.name}' after run")
             self.db.delete_job(job.id)
             return
             
        if job.schedule.kind == "at":
            # Native one-shot -> Disable
            job.enabled = False
            job.state.next_run_at_ms = None
        else:
            # Compute next run
            next_run = _compute_next_run(job.schedule, _now_ms())
            
            # Safety check: Minimum 1s delay
            if next_run and next_run <= _now_ms():
                 next_run = _now_ms() + 1000 
                 
            job.state.next_run_at_ms = next_run
            
        self.db.update_job(self._job_to_model(job))

    # ========== Public API ==========
    
    def list_jobs(self, include_disabled: bool = False) -> list[CronJob]:
        """List all jobs."""
        models = self.db.list_jobs()
        jobs = [self._model_to_job(m) for m in models]
        if not include_disabled:
            jobs = [j for j in jobs if j.enabled]
        return sorted(jobs, key=lambda j: j.state.next_run_at_ms or float('inf'))
    
    def add_job(
        self,
        name: str,
        schedule: CronSchedule,
        message: str,
        deliver: bool = False,
        channel: str | None = None,
        to: str | None = None,
        delete_after_run: bool = False,
        session_id: str | None = None,
    ) -> CronJob:
        """Add a new job."""
        if not session_id:
            raise ValueError("session_id is required for cron jobs")

        now = _now_ms()
        
        job = CronJob(
            id=str(uuid.uuid4())[:8],
            name=name,
            enabled=True,
            session_id=session_id,
            schedule=schedule,
            payload=CronPayload(
                kind="agent_turn",
                message=message,
                deliver=deliver,
                channel=channel,
                to=to,
            ),
            state=CronJobState(next_run_at_ms=_compute_next_run(schedule, now)),
            created_at_ms=now,
            updated_at_ms=now,
            delete_after_run=delete_after_run,
        )
        
        model = self._job_to_model(job)
        self.db.create_job(model)
        self._arm_timer()
        
        logger.info(f"Cron: added job '{name}' (session: {session_id})")
        return job
    
    def remove_job(self, job_id: str) -> bool:
        """Remove a job."""
        res = self.db.delete_job(job_id)
        self._arm_timer()
        return res

    def enable_job(self, job_id: str, enabled: bool = True) -> CronJob | None:
        """Enable or disable a job."""
        model = self.db.get_job(job_id)
        if not model:
            return None
        
        model.enabled = enabled
        self.db.update_job(model)
        self._arm_timer()
        return self._model_to_job(model)

    async def run_job(self, job_id: str, force: bool = False) -> bool:
        """Manually run a job."""
        model = self.db.get_job(job_id)
        if not model:
            return False
            
        if not model.enabled and not force:
            return False
            
        job = self._model_to_job(model)
        await self._execute_job(job)
        return True

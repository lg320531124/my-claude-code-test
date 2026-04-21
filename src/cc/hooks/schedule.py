"""Schedule Hook - Async scheduled task management."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import uuid


class ScheduleType(Enum):
    """Schedule types."""
    CRON = "cron"
    INTERVAL = "interval"
    ONCE = "once"
    DELAY = "delay"


@dataclass
class ScheduledJob:
    """Scheduled job."""
    id: str
    name: str
    schedule_type: ScheduleType
    schedule: str  # Cron expression or interval seconds
    handler: Callable
    next_run: Optional[datetime] = None
    last_run: Optional[datetime] = None
    run_count: int = 0
    error_count: int = 0
    last_error: Optional[Exception] = None
    enabled: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)
    task: Optional[asyncio.Task] = None

    @property
    def is_active(self) -> bool:
        """Check if job is active."""
        return self.enabled and self.next_run is not None


class ScheduleHook:
    """Async scheduled task management hook."""

    def __init__(self):
        self._jobs: Dict[str, ScheduledJob] = {}
        self._scheduler_task: Optional[asyncio.Task] = None
        self._running: bool = False
        self._subscribers: List[Callable] = []

    async def start(self) -> None:
        """Start scheduler."""
        self._running = True
        if self._scheduler_task is None:
            self._scheduler_task = asyncio.create_task(
                self._run_scheduler()
            )

    async def stop(self) -> None:
        """Stop scheduler."""
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
            self._scheduler_task = None

    async def _run_scheduler(self) -> None:
        """Run scheduler loop."""
        while self._running:
            now = datetime.now()

            # Check each job
            for job in self._jobs.values():
                if not job.enabled or not job.next_run:
                    continue

                if now >= job.next_run:
                    # Execute job
                    asyncio.create_task(self._execute_job(job.id))

            # Sleep briefly
            await asyncio.sleep(0.5)

    async def _execute_job(self, job_id: str) -> None:
        """Execute scheduled job.

        Args:
            job_id: Job ID
        """
        job = self._jobs.get(job_id)
        if not job:
            return

        job.last_run = datetime.now()
        job.run_count += 1

        try:
            if asyncio.iscoroutinefunction(job.handler):
                await job.handler()
            else:
                job.handler()

        except Exception as e:
            job.error_count += 1
            job.last_error = e

        # Calculate next run
        job.next_run = self._calculate_next_run(job)

        # Notify subscribers
        await self._notify_subscribers(job)

    def _calculate_next_run(self, job: ScheduledJob) -> Optional[datetime]:
        """Calculate next run time.

        Args:
            job: Scheduled job

        Returns:
            Next run datetime
        """
        if job.schedule_type == ScheduleType.CRON:
            return self._parse_cron(job.schedule)

        elif job.schedule_type == ScheduleType.INTERVAL:
            seconds = float(job.schedule)
            return datetime.now() + timedelta(seconds=seconds)

        elif job.schedule_type == ScheduleType.ONCE:
            return None  # One-time, no next run

        elif job.schedule_type == ScheduleType.DELAY:
            seconds = float(job.schedule)
            return datetime.now() + timedelta(seconds=seconds)

        return None

    def _parse_cron(self, expression: str) -> Optional[datetime]:
        """Parse cron expression.

        Args:
            expression: Cron expression (minute hour day month weekday)

        Returns:
            Next run datetime
        """
        # Simple cron parsing
        parts = expression.split()
        if len(parts) != 5:
            return None

        minute, hour, day, month, weekday = parts
        now = datetime.now()

        # Find next matching time
        # Start from next minute
        next_time = now.replace(second=0, microsecond=0) + timedelta(minutes=1)

        # Simple implementation - check each minute up to 1 year
        for _ in range(525600):  # Minutes in a year
            if self._matches_cron(next_time, minute, hour, day, month, weekday):
                return next_time
            next_time += timedelta(minutes=1)

        return None

    def _matches_cron(
        self,
        dt: datetime,
        minute: str,
        hour: str,
        day: str,
        month: str,
        weekday: str,
    ) -> bool:
        """Check if datetime matches cron expression.

        Args:
            dt: Datetime to check
            minute: Minute field
            hour: Hour field
            day: Day field
            month: Month field
            weekday: Weekday field

        Returns:
            True if matches
        """
        def matches_field(value: int, field: str) -> bool:
            if field == "*":
                return True
            if field.isdigit():
                return value == int(field)
            if "," in field:
                return str(value) in field.split(",")
            return False

        return (
            matches_field(dt.minute, minute) and
            matches_field(dt.hour, hour) and
            matches_field(dt.day, day) and
            matches_field(dt.month, month) and
            matches_field(dt.weekday(), weekday)
        )

    async def schedule(
        self,
        handler: Callable,
        schedule: str,
        name: str = None,
        schedule_type: ScheduleType = ScheduleType.CRON,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Schedule a job.

        Args:
            handler: Handler function
            schedule: Schedule expression
            name: Job name
            schedule_type: Schedule type
            metadata: Additional metadata

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            schedule_type=schedule_type,
            schedule=schedule,
            handler=handler,
            metadata=metadata or {},
        )

        # Calculate initial next run
        job.next_run = self._calculate_next_run(job)

        self._jobs[job_id] = job

        return job_id

    async def schedule_interval(
        self,
        handler: Callable,
        seconds: float,
        name: str = None,
    ) -> str:
        """Schedule interval job.

        Args:
            handler: Handler function
            seconds: Interval in seconds
            name: Job name

        Returns:
            Job ID
        """
        return await self.schedule(
            handler=handler,
            schedule=str(seconds),
            name=name,
            schedule_type=ScheduleType.INTERVAL,
        )

    async def schedule_cron(
        self,
        handler: Callable,
        cron_expression: str,
        name: str = None,
    ) -> str:
        """Schedule cron job.

        Args:
            handler: Handler function
            cron_expression: Cron expression
            name: Job name

        Returns:
            Job ID
        """
        return await self.schedule(
            handler=handler,
            schedule=cron_expression,
            name=name,
            schedule_type=ScheduleType.CRON,
        )

    async def schedule_once(
        self,
        handler: Callable,
        delay_seconds: float = 0,
        name: str = None,
    ) -> str:
        """Schedule one-time job.

        Args:
            handler: Handler function
            delay_seconds: Delay before execution
            name: Job name

        Returns:
            Job ID
        """
        job_id = str(uuid.uuid4())

        job = ScheduledJob(
            id=job_id,
            name=name or job_id,
            schedule_type=ScheduleType.ONCE,
            schedule=str(delay_seconds),
            handler=handler,
            next_run=datetime.now() + timedelta(seconds=delay_seconds),
        )

        self._jobs[job_id] = job

        return job_id

    def cancel(self, job_id: str) -> bool:
        """Cancel job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled
        """
        if job_id in self._jobs:
            job = self._jobs.pop(job_id)
            if job.task:
                job.task.cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all jobs.

        Returns:
            Number of cancelled jobs
        """
        count = len(self._jobs)
        for job_id in list(self._jobs.keys()):
            self.cancel(job_id)
        return count

    def pause(self, job_id: str) -> bool:
        """Pause job.

        Args:
            job_id: Job ID

        Returns:
            True if paused
        """
        job = self._jobs.get(job_id)
        if job:
            job.enabled = False
            return True
        return False

    def resume(self, job_id: str) -> bool:
        """Resume job.

        Args:
            job_id: Job ID

        Returns:
            True if resumed
        """
        job = self._jobs.get(job_id)
        if job:
            job.enabled = True
            job.next_run = self._calculate_next_run(job)
            return True
        return False

    def get_job(self, job_id: str) -> Optional[ScheduledJob]:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            ScheduledJob or None
        """
        return self._jobs.get(job_id)

    def get_jobs(self, enabled_only: bool = False) -> List[ScheduledJob]:
        """Get all jobs.

        Args:
            enabled_only: Only enabled jobs

        Returns:
            List of jobs
        """
        jobs = list(self._jobs.values())

        if enabled_only:
            jobs = [j for j in jobs if j.enabled]

        return jobs

    def get_active_jobs(self) -> List[ScheduledJob]:
        """Get active jobs.

        Returns:
            List of active jobs
        """
        return [j for j in self._jobs.values() if j.is_active]

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to job updates.

        Args:
            callback: Callback function
        """
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable) -> bool:
        """Unsubscribe from updates.

        Args:
            callback: Callback to remove

        Returns:
            True if removed
        """
        if callback in self._subscribers:
            self._subscribers.remove(callback)
            return True
        return False

    async def _notify_subscribers(self, job: ScheduledJob) -> None:
        """Notify subscribers of job update."""
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(job)
                else:
                    subscriber(job)
            except Exception:
                pass


# Global schedule hook
_schedule_hook: Optional[ScheduleHook] = None


def get_schedule_hook() -> ScheduleHook:
    """Get global schedule hook."""
    global _schedule_hook
    if _schedule_hook is None:
        _schedule_hook = ScheduleHook()
    return _schedule_hook


async def use_schedule() -> Dict[str, Any]:
    """Schedule hook for hooks module.

    Returns schedule functions.
    """
    hook = get_schedule_hook()

    return {
        "start": hook.start,
        "stop": hook.stop,
        "schedule": hook.schedule,
        "schedule_interval": hook.schedule_interval,
        "schedule_cron": hook.schedule_cron,
        "schedule_once": hook.schedule_once,
        "cancel": hook.cancel,
        "cancel_all": hook.cancel_all,
        "pause": hook.pause,
        "resume": hook.resume,
        "get_job": hook.get_job,
        "get_jobs": hook.get_jobs,
        "get_active_jobs": hook.get_active_jobs,
        "subscribe": hook.subscribe,
        "unsubscribe": hook.unsubscribe,
    }


__all__ = [
    "ScheduleType",
    "ScheduledJob",
    "ScheduleHook",
    "get_schedule_hook",
    "use_schedule",
]
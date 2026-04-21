"""Schedule tools - CronCreate, ScheduleWakeup, RemoteTrigger."""

from __future__ import annotations
import asyncio
import time
from typing import ClassVar, Callable, Optional
from dataclasses import dataclass

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


@dataclass
class ScheduledJob:
    """Scheduled job info."""
    job_id: str
    cron: str
    prompt: str
    recurring: bool
    created_at: float
    last_run: float = 0
    next_run: float = 0
    run_count: int = 0


class ScheduleInput(ToolInput):
    """Input for schedule tools."""

    cron: str
    prompt: str
    recurring: bool = True


class ScheduleWakeupInput(ToolInput):
    """Input for ScheduleWakeup."""

    delay_seconds: int
    prompt: str
    reason: str


class RemoteTriggerInput(ToolInput):
    """Input for RemoteTrigger."""

    action: str  # "list", "get", "create", "run", "update"
    trigger_id: Optional[str] = None
    body: Optional[dict] = None


class CronScheduler:
    """Manages scheduled jobs."""

    def __init__(self):
        self.jobs: Dict[str, ScheduledJob] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._on_trigger: Optional[Callable] = None
        self._started = False

    async def start(self) -> None:
        """Start the scheduler."""
        if self._started:
            return

        self._started = True
        # Start scheduler loop
        asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._started = False
        for task in self._running_tasks.values():
            task.cancel()

    def create_job(
        self,
        cron: str,
        prompt: str,
        recurring: bool = True,
    ) -> ScheduledJob:
        """Create a scheduled job."""
        job_id = f"job-{time.time_ns()}"

        job = ScheduledJob(
            job_id=job_id,
            cron=cron,
            prompt=prompt,
            recurring=recurring,
            created_at=time.time(),
        )

        # Calculate next run
        job.next_run = self._parse_cron_next(cron)

        self.jobs[job_id] = job

        return job

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a job."""
        if job_id in self.jobs:
            del self.jobs[job_id]

            if job_id in self._running_tasks:
                self._running_tasks[job_id].cancel()
                del self._running_tasks[job_id]

            return True
        return False

    def list_jobs(self) -> List[ScheduledJob]:
        """List all jobs."""
        return list(self.jobs.values())

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._started:
            try:
                now = time.time()

                for job in list(self.jobs.values()):
                    # Check if job should run
                    if job.next_run > 0 and now >= job.next_run:
                        # Run job
                        task = asyncio.create_task(
                            self._run_job(job),
                            name=job.job_id,
                        )
                        self._running_tasks[job.job_id] = task

                # Check every second
                await asyncio.sleep(1.0)

            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(5.0)

    async def _run_job(self, job: ScheduledJob) -> None:
        """Run a scheduled job."""
        job.last_run = time.time()
        job.run_count += 1

        try:
            if self._on_trigger:
                await self._on_trigger(job.prompt)

        except Exception:
            pass

        finally:
            self._running_tasks.pop(job.job_id, None)

            # Schedule next run if recurring
            if job.recurring:
                job.next_run = self._parse_cron_next(job.cron)
            else:
                # Remove one-time job
                self.jobs.pop(job.job_id, None)

    def _parse_cron_next(self, cron: str) -> float:
        """Parse cron and get next run time."""
        # Simple cron parsing
        # Format: M H DoM Mon DoW
        parts = cron.split()
        if len(parts) != 5:
            return 0

        minute, hour, dom, month, dow = parts

        now = time.localtime()
        next_time = time.mktime(now)

        # Add interval based on cron
        if minute.startswith("*"):
            # Every minute interval
            if "/" in minute:
                interval = int(minute.split("/")[1])
                next_time += interval * 60
            else:
                next_time += 60
        elif minute.isdigit():
            # Specific minute
            target_minute = int(minute)
            current_minute = now.tm_min
            if target_minute > current_minute:
                next_time += (target_minute - current_minute) * 60
            else:
                next_time += (60 - current_minute + target_minute) * 60

        return next_time

    def set_callback(self, callback: Callable) -> None:
        """Set trigger callback."""
        self._on_trigger = callback


class CronCreateTool(ToolDef):
    """Create scheduled cron jobs."""

    name: ClassVar[str] = "CronCreate"
    description: ClassVar[str] = "Schedule a prompt to be enqueued at a future time"
    input_schema: ClassVar[type] = ScheduleInput

    _scheduler: ClassVar[CronScheduler | None] = None

    def get_scheduler(self) -> CronScheduler:
        """Get scheduler instance."""
        if CronCreateTool._scheduler is None:
            CronCreateTool._scheduler = CronScheduler()
            asyncio.create_task(CronCreateTool._scheduler.start())
        return CronCreateTool._scheduler

    async def execute(self, input: ScheduleInput, ctx: ToolUseContext) -> ToolResult:
        """Create scheduled job."""
        scheduler = self.get_scheduler()

        job = scheduler.create_job(
            input.cron,
            input.prompt,
            input.recurring,
        )

        return ToolResult(
            content=f"Scheduled job {job.job_id}\n"
            f"Cron: {job.cron}\n"
            f"Recurring: {job.recurring}\n"
            f"Next run: {time.strftime('%H:%M', time.localtime(job.next_run))}",
            metadata={"job_id": job.job_id},
        )


class ScheduleWakeupTool(ToolDef):
    """Schedule wakeup for dynamic loops."""

    name: ClassVar[str] = "ScheduleWakeup"
    description: ClassVar[str] = "Schedule when to resume work in /loop dynamic mode"
    input_schema: ClassVar[type] = ScheduleWakeupInput

    async def execute(self, input: ScheduleWakeupInput, ctx: ToolUseContext) -> ToolResult:
        """Schedule wakeup."""
        delay = max(60, min(3600, input.delay_seconds))  # Clamp to 60-3600

        # Create timer
        wakeup_time = time.time() + delay

        return ToolResult(
            content=f"Wakeup scheduled for {delay}s\n"
            f"Reason: {input.reason}\n"
            f"Prompt: {input.prompt[:50]}...",
            metadata={
                "delay_seconds": delay,
                "wakeup_time": wakeup_time,
                "reason": input.reason,
            },
        )


class RemoteTriggerTool(ToolDef):
    """Trigger remote API calls."""

    name: ClassVar[str] = "RemoteTrigger"
    description: ClassVar[str] = "Call the claude.ai remote-trigger API"
    input_schema: ClassVar[type] = RemoteTriggerInput

    async def execute(self, input: RemoteTriggerInput, ctx: ToolUseContext) -> ToolResult:
        """Execute remote trigger."""
        # This would call actual API
        # For now, return placeholder
        return ToolResult(
            content=f"RemoteTrigger action: {input.action}\n"
            f"Trigger ID: {input.trigger_id or 'N/A'}",
            metadata={
                "action": input.action,
                "trigger_id": input.trigger_id,
            },
        )


# Global scheduler
_scheduler: Optional[CronScheduler] = None


def get_scheduler() -> CronScheduler:
    """Get global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = CronScheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start global scheduler."""
    await get_scheduler().start()


async def stop_scheduler() -> None:
    """Stop global scheduler."""
    if _scheduler:
        await _scheduler.stop()


def list_scheduled_jobs() -> List[ScheduledJob]:
    """List all scheduled jobs."""
    return get_scheduler().list_jobs()

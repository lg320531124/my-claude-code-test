"""Task Scheduler - Background task execution.

Provides async task scheduling and execution:
- Queue-based task execution
- Concurrent task limits
- Task prioritization
- Retry handling
- Progress tracking
"""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from . import TaskStatus, TaskManager, get_task_manager


class ScheduleType(Enum):
    """Schedule types."""
    IMMEDIATE = "immediate"
    DELAYED = "delayed"
    RECURRING = "recurring"
    DEPENDENT = "dependent"


@dataclass
class ScheduledTask:
    """Scheduled task definition."""
    task_id: str
    schedule_type: ScheduleType
    scheduled_at: datetime
    execute_at: Optional[datetime] = None
    interval_seconds: Optional[int] = None
    repeat_count: int = 0  # 0 = infinite
    executed_count: int = 0


class TaskScheduler:
    """Async task scheduler."""

    def __init__(self, manager: TaskManager = None):
        self.manager = manager or get_task_manager()
        self._scheduled: Dict[str, ScheduledTask] = {}
        self._queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        self._running: Dict[str, asyncio.Task] = {}
        self._max_concurrent: int = 5
        self._is_running: bool = False
        self._scheduler_task: Optional[asyncio.Task] = None

    async def schedule_immediate(self, task_id: str) -> bool:
        """Schedule task for immediate execution."""
        task = await self.manager.get(task_id)
        if not task:
            return False

        scheduled = ScheduledTask(
            task_id=task_id,
            schedule_type=ScheduleType.IMMEDIATE,
            scheduled_at=datetime.now(),
            execute_at=datetime.now(),
        )

        self._scheduled[task_id] = scheduled

        # Add to priority queue
        priority = task.priority.value
        await self._queue.put((priority, task_id))

        return True

    async def schedule_delayed(
        self,
        task_id: str,
        delay_seconds: int,
    ) -> bool:
        """Schedule task for delayed execution."""
        task = await self.manager.get(task_id)
        if not task:
            return False

        execute_at = datetime.now() + asyncio.timedelta(seconds=delay_seconds)

        scheduled = ScheduledTask(
            task_id=task_id,
            schedule_type=ScheduleType.DELAYED,
            scheduled_at=datetime.now(),
            execute_at=execute_at,
        )

        self._scheduled[task_id] = scheduled

        # Add to priority queue with delay priority
        priority = task.priority.value + delay_seconds
        await self._queue.put((priority, task_id))

        return True

    async def schedule_recurring(
        self,
        task_id: str,
        interval_seconds: int,
        repeat_count: int = 0,  # 0 = infinite
    ) -> bool:
        """Schedule recurring task."""
        task = await self.manager.get(task_id)
        if not task:
            return False

        scheduled = ScheduledTask(
            task_id=task_id,
            schedule_type=ScheduleType.RECURRING,
            scheduled_at=datetime.now(),
            execute_at=datetime.now(),
            interval_seconds=interval_seconds,
            repeat_count=repeat_count,
        )

        self._scheduled[task_id] = scheduled

        priority = task.priority.value
        await self._queue.put((priority, task_id))

        return True

    async def schedule_dependent(
        self,
        task_id: str,
        depends_on: List[str],
    ) -> bool:
        """Schedule task that depends on other tasks."""
        task = await self.manager.get(task_id)
        if not task:
            return False

        # Set dependencies in manager
        await self.manager.set_dependencies(task_id, blocked_by=depends_on)

        scheduled = ScheduledTask(
            task_id=task_id,
            schedule_type=ScheduleType.DEPENDENT,
            scheduled_at=datetime.now(),
        )

        self._scheduled[task_id] = scheduled

        return True

    async def unschedule(self, task_id: str) -> bool:
        """Remove scheduled task."""
        if task_id not in self._scheduled:
            return False

        self._scheduled.pop(task_id)

        # Cancel running task if any
        if task_id in self._running:
            self._running[task_id].cancel()
            self._running.pop(task_id)

        return True

    async def start(self) -> None:
        """Start scheduler loop."""
        if self._is_running:
            return

        self._is_running = True
        self._scheduler_task = asyncio.create_task(self._scheduler_loop())

    async def stop(self) -> None:
        """Stop scheduler."""
        self._is_running = False

        if self._scheduler_task:
            self._scheduler_task.cancel()
            self._scheduler_task = None

        # Cancel all running tasks
        for task_id, async_task in self._running.items():
            async_task.cancel()

        self._running.clear()

    async def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        while self._is_running:
            try:
                # Get next task from queue
                priority, task_id = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=1.0
                )

                # Check if we can run more tasks
                while len(self._running) >= self._max_concurrent:
                    await asyncio.sleep(0.1)

                # Get task
                task = await self.manager.get(task_id)
                if not task:
                    continue

                # Check if scheduled
                scheduled = self._scheduled.get(task_id)
                if not scheduled:
                    continue

                # Check delay
                if scheduled.execute_at:
                    wait_time = (scheduled.execute_at - datetime.now()).total_seconds()
                    if wait_time > 0:
                        # Re-queue with updated priority
                        await asyncio.sleep(wait_time)

                # Check dependencies
                if scheduled.schedule_type == ScheduleType.DEPENDENT:
                    all_complete = True
                    for dep_id in task.blocked_by:
                        dep_task = await self.manager.get(dep_id)
                        if dep_task and dep_task.status != TaskStatus.COMPLETED:
                            all_complete = False
                            break

                    if not all_complete:
                        # Re-queue to wait
                        await self._queue.put((priority + 100, task_id))
                        await asyncio.sleep(1.0)
                        continue

                # Start task execution
                async_task = asyncio.create_task(self._execute_task(task_id))
                self._running[task_id] = async_task

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(1.0)

    async def _execute_task(self, task_id: str) -> None:
        """Execute a task."""
        task = await self.manager.get(task_id)
        if not task:
            return

        scheduled = self._scheduled.get(task_id)

        try:
            # Start task
            await self.manager.start(task_id)

            # Execute handler if exists
            if task.handler:
                if asyncio.iscoroutinefunction(task.handler):
                    await task.handler(task)
                else:
                    task.handler(task)

            # Complete task
            await self.manager.complete(task_id)

            # Handle recurring
            if scheduled and scheduled.schedule_type == ScheduleType.RECURRING:
                scheduled.executed_count += 1

                if scheduled.repeat_count == 0 or scheduled.executed_count < scheduled.repeat_count:
                    # Schedule next run
                    next_execute_at = datetime.now() + asyncio.timedelta(
                        seconds=scheduled.interval_seconds
                    )
                    scheduled.execute_at = next_execute_at

                    # Re-queue
                    priority = task.priority.value + scheduled.executed_count * 10
                    await self._queue.put((priority, task_id))

        except asyncio.CancelledError:
            await self.manager.cancel(task_id)

        except Exception as e:
            await self.manager.fail(task_id, str(e))

            # Retry if allowed
            await self.manager.retry(task_id)

            # Re-queue for retry
            if task.retry_count < task.max_retries:
                await self._queue.put((task.priority.value + 50, task_id))

        finally:
            self._running.pop(task_id, None)

    async def get_status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        return {
            "is_running": self._is_running,
            "scheduled_count": len(self._scheduled),
            "running_count": len(self._running),
            "queue_size": self._queue.qsize(),
            "max_concurrent": self._max_concurrent,
        }

    async def get_running_tasks(self) -> List[str]:
        """Get running task IDs."""
        return list(self._running.keys())

    async def get_scheduled_tasks(self) -> List[ScheduledTask]:
        """Get scheduled tasks."""
        return list(self._scheduled.values())


# Global scheduler
_scheduler: Optional[TaskScheduler] = None


def get_scheduler() -> TaskScheduler:
    """Get global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = TaskScheduler()
    return _scheduler


async def schedule_task(task_id: str, delay: int = 0) -> bool:
    """Schedule task for execution."""
    scheduler = get_scheduler()

    if delay > 0:
        return await scheduler.schedule_delayed(task_id, delay)
    else:
        return await scheduler.schedule_immediate(task_id)


async def start_scheduler() -> None:
    """Start scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop scheduler."""
    scheduler = get_scheduler()
    await scheduler.stop()


__all__ = [
    "ScheduleType",
    "ScheduledTask",
    "TaskScheduler",
    "get_scheduler",
    "schedule_task",
    "start_scheduler",
    "stop_scheduler",
]
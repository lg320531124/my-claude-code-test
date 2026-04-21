"""Background Task Utils - Async background task management."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskState(Enum):
    """Background task state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackgroundTask:
    """Background task."""
    id: str
    name: str
    state: TaskState = TaskState.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Any = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


class BackgroundTaskManager:
    """Manage background tasks."""

    def __init__(self):
        self._tasks: Dict[str, BackgroundTask] = field(default_factory=dict)
        self._running_tasks: Dict[str, asyncio.Task] = field(default_factory=dict)
        self._callbacks: Dict[str, List[Callable]] = {}

    async def start_task(
        self,
        task_id: str,
        name: str,
        coro: Awaitable,
        metadata: Dict[str, Any] = None,
    ) -> BackgroundTask:
        """Start a background task."""
        task = BackgroundTask(
            id=task_id,
            name=name,
            state=TaskState.PENDING,
            metadata=metadata or {},
        )

        self._tasks[task_id] = task

        # Create async task
        async def run_with_tracking():
            task.state = TaskState.RUNNING
            task.started_at = datetime.now()

            try:
                result = await coro
                task.state = TaskState.COMPLETED
                task.result = result
                task.completed_at = datetime.now()
                await self._notify_callbacks(task_id, "completed", result)
                return result

            except asyncio.CancelledError:
                task.state = TaskState.CANCELLED
                task.completed_at = datetime.now()
                await self._notify_callbacks(task_id, "cancelled", None)
                raise

            except Exception as e:
                task.state = TaskState.FAILED
                task.error = str(e)
                task.completed_at = datetime.now()
                await self._notify_callbacks(task_id, "failed", str(e))
                raise

        self._running_tasks[task_id] = asyncio.create_task(run_with_tracking())

        return task

    async def cancel_task(self, task_id: str) -> bool:
        """Cancel a running task."""
        if task_id not in self._running_tasks:
            return False

        task = self._running_tasks[task_id]
        task.cancel()

        try:
            await task
        except asyncio.CancelledError:
            pass

        return True

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> List[BackgroundTask]:
        """Get all tasks."""
        return list(self._tasks.values())

    def get_running_tasks(self) -> List[BackgroundTask]:
        """Get running tasks."""
        return [
            t for t in self._tasks.values()
            if t.state == TaskState.RUNNING
        ]

    async def wait_for_task(
        self,
        task_id: str,
        timeout: float = None,
    ) -> Optional[Any]:
        """Wait for task to complete."""
        if task_id not in self._running_tasks:
            return self._tasks.get(task_id).result

        try:
            if timeout:
                await asyncio.wait_for(
                    self._running_tasks[task_id],
                    timeout=timeout,
                )
            else:
                await self._running_tasks[task_id]

            return self._tasks[task_id].result

        except asyncio.TimeoutError:
            return None

    def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress."""
        if task_id in self._tasks:
            self._tasks[task_id].progress = progress

    def on_task_event(
        self,
        task_id: str,
        event: str,
        callback: Callable,
    ) -> None:
        """Register callback for task event."""
        key = f"{task_id}:{event}"
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    async def _notify_callbacks(
        self,
        task_id: str,
        event: str,
        data: Any,
    ) -> None:
        """Notify callbacks."""
        key = f"{task_id}:{event}"
        callbacks = self._callbacks.get(key, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(task_id, event, data)
                else:
                    callback(task_id, event, data)
            except Exception:
                pass

    async def cleanup_completed(self) -> int:
        """Clean up completed tasks."""
        to_remove = [
            tid for tid, task in self._tasks.items()
            if task.state in [TaskState.COMPLETED, TaskState.FAILED, TaskState.CANCELLED]
        ]

        for tid in to_remove:
            self._tasks.pop(tid, None)
            self._running_tasks.pop(tid, None)

        return len(to_remove)


class TaskQueue:
    """Queue for background tasks."""

    def __init__(self, max_concurrent: int = 5):
        self.max_concurrent = max_concurrent
        self._queue: asyncio.Queue = asyncio.Queue()
        self._manager = BackgroundTaskManager()
        self._running_count: int = 0
        self._worker_task: Optional[asyncio.Task] = None

    async def enqueue(
        self,
        name: str,
        coro: Awaitable,
        priority: int = 0,
    ) -> str:
        """Enqueue a task."""
        import uuid
        task_id = uuid.uuid4().hex[:8]

        await self._queue.put({
            "id": task_id,
            "name": name,
            "coro": coro,
            "priority": priority,
        })

        return task_id

    async def start_workers(self) -> None:
        """Start worker loop."""
        if self._worker_task:
            return

        self._worker_task = asyncio.create_task(self._worker_loop())

    async def stop_workers(self) -> None:
        """Stop workers."""
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
            self._worker_task = None

    async def _worker_loop(self) -> None:
        """Worker loop."""
        while True:
            if self._running_count >= self.max_concurrent:
                await asyncio.sleep(0.1)
                continue

            try:
                item = await asyncio.wait_for(
                    self._queue.get(),
                    timeout=0.5,
                )

                self._running_count += 1

                await self._manager.start_task(
                    item["id"],
                    item["name"],
                    self._run_with_cleanup(item["coro"]),
                )

            except asyncio.TimeoutError:
                continue

    async def _run_with_cleanup(self, coro: Awaitable) -> Any:
        """Run coroutine and decrement count."""
        try:
            result = await coro
            return result
        finally:
            self._running_count -= 1

    async def get_stats(self) -> Dict[str, int]:
        """Get queue stats."""
        return {
            "queue_size": self._queue.qsize(),
            "running": self._running_count,
            "max_concurrent": self.max_concurrent,
        }


# Global manager
_manager: Optional[BackgroundTaskManager] = None


def get_background_manager() -> BackgroundTaskManager:
    """Get global background manager."""
    global _manager
    if _manager is None:
        _manager = BackgroundTaskManager()
    return _manager


async def run_in_background(
    name: str,
    coro: Awaitable,
    task_id: str = None,
) -> str:
    """Run task in background."""
    import uuid
    manager = get_background_manager()

    if task_id is None:
        task_id = uuid.uuid4().hex[:8]

    await manager.start_task(task_id, name, coro)
    return task_id


__all__ = [
    "TaskState",
    "BackgroundTask",
    "BackgroundTaskManager",
    "TaskQueue",
    "get_background_manager",
    "run_in_background",
]
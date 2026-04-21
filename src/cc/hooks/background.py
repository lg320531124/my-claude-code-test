"""Background Hook - Async background task management."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Callable, List, Awaitable, Coroutine
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import uuid


class TaskState(Enum):
    """Background task states."""
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
    coro: Optional[Coroutine] = None
    task: Optional[asyncio.Task] = None
    result: Any = None
    error: Optional[Exception] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    on_complete: Optional[Callable] = None
    on_error: Optional[Callable] = None
    on_cancel: Optional[Callable] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    @property
    def is_done(self) -> bool:
        """Check if task is done."""
        return self.state in {
            TaskState.COMPLETED,
            TaskState.FAILED,
            TaskState.CANCELLED,
        }


class BackgroundHook:
    """Async background task management hook."""

    def __init__(self):
        self._tasks: Dict[str, BackgroundTask] = {}
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._executor_task: Optional[asyncio.Task] = None
        self._max_concurrent: int = 10
        self._running_count: int = 0
        self._subscribers: List[Callable] = []

    async def start_executor(self) -> None:
        """Start task executor."""
        if self._executor_task is None:
            self._executor_task = asyncio.create_task(
                self._execute_tasks()
            )

    async def stop_executor(self) -> None:
        """Stop task executor."""
        if self._executor_task:
            self._executor_task.cancel()
            try:
                await self._executor_task
            except asyncio.CancelledError:
                pass
            self._executor_task = None

    async def _execute_tasks(self) -> None:
        """Execute queued tasks."""
        while True:
            task_id = await self._task_queue.get()
            task = self._tasks.get(task_id)

            if task and task.coro:
                # Wait for slot
                while self._running_count >= self._max_concurrent:
                    await asyncio.sleep(0.1)

                self._running_count += 1
                task.state = TaskState.RUNNING
                task.started_at = datetime.now()
                task.task = asyncio.create_task(task.coro)

                # Handle completion
                async def handle_completion():
                    try:
                        task.result = await task.task
                        task.state = TaskState.COMPLETED
                        task.completed_at = datetime.now()

                        if task.on_complete:
                            if asyncio.iscoroutinefunction(task.on_complete):
                                await task.on_complete(task.result, task)
                            else:
                                task.on_complete(task.result, task)

                    except asyncio.CancelledError:
                        task.state = TaskState.CANCELLED
                        task.completed_at = datetime.now()

                        if task.on_cancel:
                            if asyncio.iscoroutinefunction(task.on_cancel):
                                await task.on_cancel(task)
                            else:
                                task.on_cancel(task)

                    except Exception as e:
                        task.state = TaskState.FAILED
                        task.error = e
                        task.completed_at = datetime.now()

                        if task.on_error:
                            if asyncio.iscoroutinefunction(task.on_error):
                                await task.on_error(e, task)
                            else:
                                task.on_error(e, task)

                    finally:
                        self._running_count -= 1
                        await self._notify_subscribers(task)

                asyncio.create_task(handle_completion())

    async def _notify_subscribers(self, task: BackgroundTask) -> None:
        """Notify subscribers of task update."""
        for subscriber in self._subscribers:
            try:
                if asyncio.iscoroutinefunction(subscriber):
                    await subscriber(task)
                else:
                    subscriber(task)
            except Exception:
                pass

    async def submit(
        self,
        coro: Coroutine,
        name: str = None,
        on_complete: Callable = None,
        on_error: Callable = None,
        on_cancel: Callable = None,
        metadata: Dict[str, Any] = None,
    ) -> str:
        """Submit background task.

        Args:
            coro: Coroutine to execute
            name: Task name
            on_complete: Completion callback
            on_error: Error callback
            on_cancel: Cancel callback
            metadata: Additional metadata

        Returns:
            Task ID
        """
        task_id = str(uuid.uuid4())

        task = BackgroundTask(
            id=task_id,
            name=name or task_id,
            coro=coro,
            on_complete=on_complete,
            on_error=on_error,
            on_cancel=on_cancel,
            metadata=metadata or {},
        )

        self._tasks[task_id] = task
        await self._task_queue.put(task_id)

        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel task.

        Args:
            task_id: Task ID

        Returns:
            True if cancelled
        """
        task = self._tasks.get(task_id)
        if task and task.task and not task.is_done:
            task.task.cancel()
            return True
        return False

    def cancel_all(self) -> int:
        """Cancel all running tasks.

        Returns:
            Number of cancelled tasks
        """
        count = 0
        for task_id in list(self._tasks.keys()):
            if self.cancel(task_id):
                count += 1
        return count

    def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """Get task by ID.

        Args:
            task_id: Task ID

        Returns:
            BackgroundTask or None
        """
        return self._tasks.get(task_id)

    def get_tasks(self, state: TaskState = None) -> List[BackgroundTask]:
        """Get all tasks.

        Args:
            state: Optional state filter

        Returns:
            List of tasks
        """
        tasks = list(self._tasks.values())

        if state:
            tasks = [t for t in tasks if t.state == state]

        return tasks

    def get_running_tasks(self) -> List[BackgroundTask]:
        """Get running tasks.

        Returns:
            List of running tasks
        """
        return self.get_tasks(TaskState.RUNNING)

    def get_pending_tasks(self) -> List[BackgroundTask]:
        """Get pending tasks.

        Returns:
            List of pending tasks
        """
        return self.get_tasks(TaskState.PENDING)

    def get_completed_tasks(self) -> List[BackgroundTask]:
        """Get completed tasks.

        Returns:
            List of completed tasks
        """
        return self.get_tasks(TaskState.COMPLETED)

    def get_failed_tasks(self) -> List[BackgroundTask]:
        """Get failed tasks.

        Returns:
            List of failed tasks
        """
        return self.get_tasks(TaskState.FAILED)

    def update_progress(self, task_id: str, progress: float) -> None:
        """Update task progress.

        Args:
            task_id: Task ID
            progress: Progress (0.0 to 1.0)
        """
        task = self._tasks.get(task_id)
        if task:
            task.progress = progress

    def subscribe(self, callback: Callable) -> None:
        """Subscribe to task updates.

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

    async def wait_for(self, task_id: str, timeout: float = None) -> Any:
        """Wait for task completion.

        Args:
            task_id: Task ID
            timeout: Timeout in seconds

        Returns:
            Task result

        Raises:
            TimeoutError if timeout
            Exception if task failed
        """
        task = self._tasks.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if task.is_done:
            if task.state == TaskState.FAILED:
                raise task.error
            return task.result

        if task.task:
            try:
                return await asyncio.wait_for(task.task, timeout)
            except asyncio.TimeoutError:
                raise TimeoutError(f"Task {task_id} timed out")

        # Wait for task to be processed
        while not task.is_done:
            await asyncio.sleep(0.1)
            if timeout:
                timeout -= 0.1
                if timeout <= 0:
                    raise TimeoutError(f"Task {task_id} timed out")

        if task.state == TaskState.FAILED:
            raise task.error
        return task.result

    async def wait_all(self, timeout: float = None) -> Dict[str, Any]:
        """Wait for all tasks.

        Args:
            timeout: Timeout per task

        Returns:
            Dict of task_id -> result
        """
        results = {}
        for task_id in list(self._tasks.keys()):
            try:
                results[task_id] = await self.wait_for(task_id, timeout)
            except Exception:
                pass
        return results

    def cleanup(self) -> int:
        """Remove completed tasks.

        Returns:
            Number of removed tasks
        """
        to_remove = [
            id for id, task in self._tasks.items()
            if task.is_done
        ]
        for id in to_remove:
            del self._tasks[id]
        return len(to_remove)


# Global background hook
_background_hook: Optional[BackgroundHook] = None


def get_background_hook() -> BackgroundHook:
    """Get global background hook."""
    global _background_hook
    if _background_hook is None:
        _background_hook = BackgroundHook()
    return _background_hook


async def use_background() -> Dict[str, Any]:
    """Background hook for hooks module.

    Returns background task functions.
    """
    hook = get_background_hook()

    return {
        "submit": hook.submit,
        "cancel": hook.cancel,
        "cancel_all": hook.cancel_all,
        "get_task": hook.get_task,
        "get_tasks": hook.get_tasks,
        "get_running_tasks": hook.get_running_tasks,
        "get_pending_tasks": hook.get_pending_tasks,
        "get_completed_tasks": hook.get_completed_tasks,
        "get_failed_tasks": hook.get_failed_tasks,
        "update_progress": hook.update_progress,
        "subscribe": hook.subscribe,
        "unsubscribe": hook.unsubscribe,
        "wait_for": hook.wait_for,
        "wait_all": hook.wait_all,
        "cleanup": hook.cleanup,
    }


__all__ = [
    "TaskState",
    "BackgroundTask",
    "BackgroundHook",
    "get_background_hook",
    "use_background",
]
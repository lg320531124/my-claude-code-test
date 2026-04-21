"""Tasks Module - Complete task management system.

Provides task management with:
- Task creation, update, deletion
- Task dependencies (blocks/blockedBy)
- Task scheduling and prioritization
- Task history and tracking
- Async task execution
- Task persistence
"""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    DELETED = "deleted"


class TaskPriority(Enum):
    """Task priority."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass
class Task:
    """Task definition."""
    id: str
    subject: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    owner: Optional[str] = None
    active_form: str = ""
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Dependencies
    blocks: List[str] = field(default_factory=list)  # Tasks blocked by this task
    blocked_by: List[str] = field(default_factory=list)  # Tasks that block this task

    # Execution
    handler: Optional[Callable] = None
    retry_count: int = 0
    max_retries: int = 3
    error: Optional[str] = None

    # Progress tracking
    progress: float = 0.0
    subtasks: List[str] = field(default_factory=list)
    parent_task: Optional[str] = None

    def is_ready(self) -> bool:
        """Check if task is ready to start."""
        if self.status != TaskStatus.PENDING:
            return False
        for blocking_task_id in self.blocked_by:
            # Would check against task manager
            pass
        return True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "subject": self.subject,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "owner": self.owner,
            "activeForm": self.active_form,
            "createdAt": self.created_at.isoformat(),
            "updatedAt": self.updated_at.isoformat(),
            "startedAt": self.started_at.isoformat() if self.started_at else None,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "blocks": self.blocks,
            "blockedBy": self.blocked_by,
            "progress": self.progress,
            "subtasks": self.subtasks,
            "parentTask": self.parent_task,
            "error": self.error,
        }


@dataclass
class TaskEvent:
    """Task event for history."""
    task_id: str
    event_type: str
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """Central task manager."""

    def __init__(self, persistence_path: Path = None):
        self._tasks: Dict[str, Task] = {}
        self._counter: int = 0
        self._history: List[TaskEvent] = []
        self._listeners: List[Callable] = []
        self._persistence_path = persistence_path
        self._lock = asyncio.Lock()

        # Task execution queue
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running_tasks: Set[str] = set()
        self._max_concurrent: int = 5

    async def create(
        self,
        subject: str,
        description: str,
        active_form: str = None,
        priority: TaskPriority = TaskPriority.MEDIUM,
        owner: str = None,
        metadata: Dict[str, Any] = None,
    ) -> Task:
        """Create a new task."""
        async with self._lock:
            self._counter += 1
            task_id = str(self._counter)

            task = Task(
                id=task_id,
                subject=subject,
                description=description,
                active_form=active_form or subject,
                priority=priority,
                owner=owner,
                metadata=metadata or {},
            )

            self._tasks[task_id] = task

            # Record event
            self._record_event(task_id, "created", {"subject": subject})

            # Notify listeners
            await self._notify("created", task)

            # Save
            await self._save()

            return task

    async def get(self, task_id: str) -> Optional[Task]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    async def update(
        self,
        task_id: str,
        status: TaskStatus = None,
        subject: str = None,
        description: str = None,
        owner: str = None,
        priority: TaskPriority = None,
        progress: float = None,
        metadata: Dict[str, Any] = None,
    ) -> Optional[Task]:
        """Update task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            old_status = task.status

            if status is not None:
                task.status = status
                if status == TaskStatus.IN_PROGRESS and task.started_at is None:
                    task.started_at = datetime.now()
                elif status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED):
                    task.completed_at = datetime.now()

            if subject is not None:
                task.subject = subject
            if description is not None:
                task.description = description
            if owner is not None:
                task.owner = owner
            if priority is not None:
                task.priority = priority
            if progress is not None:
                task.progress = progress
            if metadata is not None:
                task.metadata.update(metadata)

            task.updated_at = datetime.now()

            # Record event
            self._record_event(task_id, "updated", {
                "old_status": old_status.value,
                "new_status": task.status.value,
            })

            # Notify listeners
            await self._notify("updated", task)

            # Check blocked tasks
            if old_status != task.status and task.status == TaskStatus.COMPLETED:
                await self._check_blocked_tasks(task_id)

            # Save
            await self._save()

            return task

    async def delete(self, task_id: str) -> bool:
        """Delete task."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False

            task.status = TaskStatus.DELETED
            self._tasks.pop(task_id)

            # Record event
            self._record_event(task_id, "deleted", {"subject": task.subject})

            # Notify listeners
            await self._notify("deleted", task)

            # Save
            await self._save()

            return True

    async def set_dependencies(
        self,
        task_id: str,
        blocks: List[str] = None,
        blocked_by: List[str] = None,
    ) -> Optional[Task]:
        """Set task dependencies."""
        async with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return None

            if blocks is not None:
                task.blocks = blocks
                # Update blocked tasks' blockedBy
                for blocked_id in blocks:
                    blocked_task = self._tasks.get(blocked_id)
                    if blocked_task and task_id not in blocked_task.blocked_by:
                        blocked_task.blocked_by.append(task_id)

            if blocked_by is not None:
                task.blocked_by = blocked_by
                # Update blocking tasks' blocks
                for blocking_id in blocked_by:
                    blocking_task = self._tasks.get(blocking_id)
                    if blocking_task and task_id not in blocking_task.blocks:
                        blocking_task.blocks.append(task_id)

            task.updated_at = datetime.now()

            # Record event
            self._record_event(task_id, "dependencies_set", {
                "blocks": task.blocks,
                "blockedBy": task.blocked_by,
            })

            # Save
            await self._save()

            return task

    async def add_block(self, task_id: str, blocks_task_id: str) -> bool:
        """Add a task that this task blocks."""
        return await self.set_dependencies(task_id, blocks=[blocks_task_id] + self._tasks[task_id].blocks)

    async def add_blocked_by(self, task_id: str, blocked_by_task_id: str) -> bool:
        """Add a task that blocks this task."""
        return await self.set_dependencies(task_id, blocked_by=[blocked_by_task_id] + self._tasks[task_id].blocked_by)

    async def start(self, task_id: str) -> Optional[Task]:
        """Start task."""
        return await self.update(task_id, status=TaskStatus.IN_PROGRESS)

    async def complete(self, task_id: str) -> Optional[Task]:
        """Complete task."""
        return await self.update(task_id, status=TaskStatus.COMPLETED)

    async def fail(self, task_id: str, error: str = None) -> Optional[Task]:
        """Mark task as failed."""
        task = await self.get(task_id)
        if task:
            task.error = error
            return await self.update(task_id, status=TaskStatus.FAILED)
        return None

    async def cancel(self, task_id: str) -> Optional[Task]:
        """Cancel task."""
        return await self.update(task_id, status=TaskStatus.CANCELLED)

    async def retry(self, task_id: str) -> Optional[Task]:
        """Retry failed task."""
        task = await self.get(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return None

        if task.retry_count >= task.max_retries:
            return None

        task.retry_count += 1
        return await self.update(task_id, status=TaskStatus.PENDING)

    async def list(
        self,
        status: TaskStatus = None,
        owner: str = None,
        priority: TaskPriority = None,
    ) -> List[Task]:
        """List tasks with filters."""
        tasks = []

        for task in self._tasks.values():
            if task.status == TaskStatus.DELETED:
                continue
            if status and task.status != status:
                continue
            if owner and task.owner != owner:
                continue
            if priority and task.priority != priority:
                continue
            tasks.append(task)

        # Sort by priority then by ID
        tasks.sort(key=lambda t: (t.priority.value, int(t.id)))
        return tasks

    async def list_pending(self) -> List[Task]:
        """List pending tasks."""
        return await self.list(status=TaskStatus.PENDING)

    async def list_ready(self) -> List[Task]:
        """List tasks ready to start."""
        pending = await self.list_pending()
        ready = []

        for task in pending:
            all_blocked_complete = True
            for blocking_id in task.blocked_by:
                blocking_task = self._tasks.get(blocking_id)
                if blocking_task and blocking_task.status != TaskStatus.COMPLETED:
                    all_blocked_complete = False
                    break
            if all_blocked_complete:
                ready.append(task)

        return ready

    async def list_in_progress(self) -> List[Task]:
        """List in-progress tasks."""
        return await self.list(status=TaskStatus.IN_PROGRESS)

    async def claim(self, task_id: str, owner: str) -> Optional[Task]:
        """Claim task for owner."""
        return await self.update(task_id, owner=owner)

    async def get_next_ready(self) -> Optional[Task]:
        """Get next ready task."""
        ready_tasks = await self.list_ready()
        if ready_tasks:
            return ready_tasks[0]
        return None

    async def get_stats(self) -> Dict[str, Any]:
        """Get task statistics."""
        stats = {
            "total": len(self._tasks),
            "pending": 0,
            "in_progress": 0,
            "completed": 0,
            "failed": 0,
            "cancelled": 0,
            "blocked": 0,
        }

        for task in self._tasks.values():
            if task.status == TaskStatus.DELETED:
                continue
            stats[task.status.value] += 1

            # Check if blocked
            if task.status == TaskStatus.PENDING:
                for blocking_id in task.blocked_by:
                    blocking_task = self._tasks.get(blocking_id)
                    if blocking_task and blocking_task.status != TaskStatus.COMPLETED:
                        stats["blocked"] += 1
                        break

        return stats

    async def get_history(self, task_id: str = None) -> List[TaskEvent]:
        """Get task history."""
        if task_id:
            return [e for e in self._history if e.task_id == task_id]
        return self._history

    async def subscribe(self, listener: Callable) -> Callable:
        """Subscribe to task events."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    async def execute_ready_tasks(self) -> None:
        """Execute ready tasks with handlers."""
        ready_tasks = await self.list_ready()

        for task in ready_tasks:
            if task.handler and task.status == TaskStatus.PENDING:
                await self.start(task.id)

                try:
                    if asyncio.iscoroutinefunction(task.handler):
                        await task.handler(task)
                    else:
                        task.handler(task)

                    await self.complete(task.id)

                except Exception as e:
                    await self.fail(task.id, str(e))

    def _record_event(self, task_id: str, event_type: str, data: Dict[str, Any] = None) -> None:
        """Record task event."""
        event = TaskEvent(
            task_id=task_id,
            event_type=event_type,
            timestamp=datetime.now(),
            data=data or {},
        )
        self._history.append(event)

    async def _notify(self, event_type: str, task: Task) -> None:
        """Notify listeners."""
        for listener in self._listeners:
            if asyncio.iscoroutinefunction(listener):
                await listener(event_type, task)
            else:
                listener(event_type, task)

    async def _check_blocked_tasks(self, completed_task_id: str) -> None:
        """Check tasks blocked by completed task."""
        task = self._tasks.get(completed_task_id)
        if not task:
            return

        for blocked_id in task.blocks:
            blocked_task = self._tasks.get(blocked_id)
            if blocked_task and blocked_task.status == TaskStatus.PENDING:
                # Check if all blockers are complete
                all_complete = True
                for blocking_id in blocked_task.blocked_by:
                    blocking_task = self._tasks.get(blocking_id)
                    if blocking_task and blocking_task.status != TaskStatus.COMPLETED:
                        all_complete = False
                        break

                if all_complete:
                    self._record_event(blocked_id, "unblocked", {"by": completed_task_id})

    async def _save(self) -> None:
        """Save tasks to file."""
        if not self._persistence_path:
            return

        import aiofiles

        data = {
            "tasks": {k: v.to_dict() for k, v in self._tasks.items()},
            "counter": self._counter,
            "history": [
                {
                    "taskId": e.task_id,
                    "eventType": e.event_type,
                    "timestamp": e.timestamp.isoformat(),
                    "data": e.data,
                }
                for e in self._history
            ],
        }

        async with aiofiles.open(self._persistence_path, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def _load(self) -> None:
        """Load tasks from file."""
        if not self._persistence_path or not self._persistence_path.exists():
            return

        import aiofiles

        async with aiofiles.open(self._persistence_path, "r") as f:
            content = await f.read()

        data = json.loads(content)

        self._counter = data.get("counter", 0)

        for task_id, task_data in data.get("tasks", {}).items():
            task = Task(
                id=task_id,
                subject=task_data["subject"],
                description=task_data["description"],
                status=TaskStatus(task_data.get("status", "pending")),
                priority=TaskPriority(task_data.get("priority", 2)),
                owner=task_data.get("owner"),
                active_form=task_data.get("activeForm", ""),
                created_at=datetime.fromisoformat(task_data["createdAt"]),
                updated_at=datetime.fromisoformat(task_data["updatedAt"]),
                started_at=datetime.fromisoformat(task_data["startedAt"]) if task_data.get("startedAt") else None,
                completed_at=datetime.fromisoformat(task_data["completedAt"]) if task_data.get("completedAt") else None,
                metadata=task_data.get("metadata", {}),
                blocks=task_data.get("blocks", []),
                blocked_by=task_data.get("blockedBy", []),
                progress=task_data.get("progress", 0.0),
                subtasks=task_data.get("subtasks", []),
                parent_task=task_data.get("parentTask"),
                error=task_data.get("error"),
            )
            self._tasks[task_id] = task

        for event_data in data.get("history", []):
            event = TaskEvent(
                task_id=event_data["taskId"],
                event_type=event_data["eventType"],
                timestamp=datetime.fromisoformat(event_data["timestamp"]),
                data=event_data.get("data", {}),
            )
            self._history.append(event)


# Global task manager
_task_manager: Optional[TaskManager] = None


def get_task_manager() -> TaskManager:
    """Get global task manager."""
    global _task_manager
    if _task_manager is None:
        persistence_path = Path.home() / ".claude" / "tasks.json"
        _task_manager = TaskManager(persistence_path)
    return _task_manager


def create_task_manager(persistence_path: Path = None) -> TaskManager:
    """Create new task manager."""
    return TaskManager(persistence_path)


# Import scheduler submodule
from .scheduler import (
    ScheduleType,
    ScheduledTask,
    TaskScheduler,
    get_scheduler,
    schedule_task,
    start_scheduler,
    stop_scheduler,
)


__all__ = [
    # Core
    "TaskStatus",
    "TaskPriority",
    "Task",
    "TaskEvent",
    "TaskManager",
    "get_task_manager",
    "create_task_manager",
    # Scheduler
    "ScheduleType",
    "ScheduledTask",
    "TaskScheduler",
    "get_scheduler",
    "schedule_task",
    "start_scheduler",
    "stop_scheduler",
]
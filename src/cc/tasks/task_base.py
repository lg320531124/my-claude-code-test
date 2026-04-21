"""Task Module - Task execution management.

Provides task types, status management, ID generation, and
task context for background task execution.
"""

from __future__ import annotations

import secrets
import time
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, List
from enum import Enum
from pathlib import Path


class TaskType(Enum):
    """Task type enumeration."""
    LOCAL_BASH = "local_bash"
    LOCAL_AGENT = "local_agent"
    REMOTE_AGENT = "remote_agent"
    IN_PROCESS_TEAMMATE = "in_process_teammate"
    LOCAL_WORKFLOW = "local_workflow"
    MONITOR_MCP = "monitor_mcp"
    DREAM = "dream"


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    KILLED = "killed"


def is_terminal_task_status(status: TaskStatus) -> bool:
    """Check if task status is terminal (no further transitions)."""
    return status in (TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.KILLED)


# Task ID prefixes
TASK_ID_PREFIXES: Dict[str, str] = {
    "local_bash": "b",
    "local_agent": "a",
    "remote_agent": "r",
    "in_process_teammate": "t",
    "local_workflow": "w",
    "monitor_mcp": "m",
    "dream": "d",
}

# Case-insensitive-safe alphabet for task IDs
TASK_ID_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyz"


def get_task_id_prefix(task_type: TaskType) -> str:
    """Get task ID prefix for task type."""
    return TASK_ID_PREFIXES.get(task_type.value, "x")


def generate_task_id(task_type: TaskType) -> str:
    """Generate unique task ID with type prefix."""
    prefix = get_task_id_prefix(task_type)
    # Generate 8 random characters from alphabet
    random_chars = "".join(
        TASK_ID_ALPHABET[secrets.randbelow(len(TASK_ID_ALPHABET))]
        for _ in range(8)
    )
    return prefix + random_chars


def get_task_output_path(task_id: str) -> Path:
    """Get output file path for task."""
    # Output stored in task-specific file
    output_dir = Path.home() / ".claude" / "task_outputs"
    return output_dir / f"{task_id}.jsonl"


@dataclass
class TaskHandle:
    """Handle for tracking a task."""
    task_id: str
    cleanup: Optional[Callable] = None


@dataclass
class TaskStateBase:
    """Base state for all tasks."""
    id: str
    type: TaskType
    status: TaskStatus = TaskStatus.PENDING
    description: str = ""
    tool_use_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    total_paused_ms: Optional[float] = None
    output_file: str = ""
    output_offset: int = 0
    notified: bool = False

    def __post_init__(self):
        if not self.output_file:
            self.output_file = str(get_task_output_path(self.id))


@dataclass
class LocalShellSpawnInput:
    """Input for local shell task spawn."""
    command: str
    description: str
    timeout: Optional[float] = None
    tool_use_id: Optional[str] = None
    agent_id: Optional[str] = None
    kind: Optional[str] = None  # 'bash' or 'monitor'


@dataclass
class TaskContext:
    """Context for task execution."""
    abort_controller: Optional[Any] = None
    get_app_state: Optional[Callable] = None
    set_app_state: Optional[Callable] = None


class Task:
    """Base class for tasks."""

    name: str
    type: TaskType

    async def kill(self, task_id: str, set_app_state: Callable) -> None:
        """Kill the task."""
        raise NotImplementedError


def create_task_state_base(
    task_type: TaskType,
    description: str,
    tool_use_id: Optional[str] = None,
) -> TaskStateBase:
    """Create base task state."""
    task_id = generate_task_id(task_type)
    return TaskStateBase(
        id=task_id,
        type=task_type,
        description=description,
        tool_use_id=tool_use_id,
    )


@dataclass
class TaskRegistry:
    """Registry for managing tasks."""

    _tasks: Dict[str, TaskStateBase] = field(default_factory=dict)

    def add(self, task: TaskStateBase) -> None:
        """Add task to registry."""
        self._tasks[task.id] = task

    def remove(self, task_id: str) -> Optional[TaskStateBase]:
        """Remove task from registry."""
        return self._tasks.pop(task_id, None)

    def get(self, task_id: str) -> Optional[TaskStateBase]:
        """Get task by ID."""
        return self._tasks.get(task_id)

    def list_all(self) -> List[TaskStateBase]:
        """List all tasks."""
        return list(self._tasks.values())

    def list_by_status(self, status: TaskStatus) -> List[TaskStateBase]:
        """List tasks by status."""
        return [t for t in self._tasks.values() if t.status == status]

    def list_running(self) -> List[TaskStateBase]:
        """List running tasks."""
        return self.list_by_status(TaskStatus.RUNNING)

    def list_terminal(self) -> List[TaskStateBase]:
        """List terminal tasks (completed, failed, killed)."""
        return [
            t for t in self._tasks.values()
            if is_terminal_task_status(t.status)
        ]

    def clear_terminal(self) -> int:
        """Clear all terminal tasks."""
        terminal_ids = [t.id for t in self.list_terminal()]
        for task_id in terminal_ids:
            self._tasks.pop(task_id, None)
        return len(terminal_ids)


# Global task registry
_task_registry = None


def get_task_registry() -> TaskRegistry:
    """Get global task registry."""
    global _task_registry
    if _task_registry is None:
        _task_registry = TaskRegistry()
    return _task_registry


def reset_task_registry() -> None:
    """Reset task registry (for tests)."""
    global _task_registry
    _task_registry = None


__all__ = [
    "TaskType",
    "TaskStatus",
    "is_terminal_task_status",
    "TASK_ID_PREFIXES",
    "TASK_ID_ALPHABET",
    "get_task_id_prefix",
    "generate_task_id",
    "get_task_output_path",
    "TaskHandle",
    "TaskStateBase",
    "LocalShellSpawnInput",
    "TaskContext",
    "Task",
    "create_task_state_base",
    "TaskRegistry",
    "get_task_registry",
    "reset_task_registry",
]
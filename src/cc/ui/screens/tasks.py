"""Tasks Screen - Task list display."""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Task status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class TaskItem:
    """Task item."""
    id: str
    title: str
    description: str = ""
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    created_at: datetime = None
    updated_at: datetime = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TasksScreenConfig:
    """Tasks screen configuration."""
    show_progress: bool = True
    show_priority: bool = True
    show_timestamps: bool = False
    group_by_status: bool = True
    max_tasks: int = 50


class TasksScreen:
    """Screen to display task list."""
    
    def __init__(self, config: TasksScreenConfig = None):
        self.config = config or TasksScreenConfig()
        self._tasks: List[TaskItem] = []
    
    def add_task(self, task: TaskItem) -> None:
        """Add task."""
        self._tasks.append(task)
    
    def update_task(self, task_id: str, status: TaskStatus, progress: float = None) -> None:
        """Update task."""
        for task in self._tasks:
            if task.id == task_id:
                task.status = status
                task.updated_at = datetime.now()
                if progress is not None:
                    task.progress = progress
    
    def get_task(self, task_id: str) -> Optional[TaskItem]:
        """Get task by ID."""
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None
    
    def get_by_status(self, status: TaskStatus) -> List[TaskItem]:
        """Get tasks by status."""
        return [t for t in self._tasks if t.status == status]
    
    def render(self) -> str:
        """Render tasks screen."""
        lines = ["# Tasks", ""]
        
        if self.config.group_by_status:
            # Group by status
            for status in [TaskStatus.IN_PROGRESS, TaskStatus.PENDING, TaskStatus.COMPLETED, TaskStatus.FAILED]:
                tasks = self.get_by_status(status)
                if tasks:
                    lines.append(f"## {status.value.replace('_', ' ').title()} ({len(tasks)})")
                    lines.append("")
                    
                    for task in tasks:
                        lines.append(self._render_task(task))
                    
                    lines.append("")
        else:
            # Flat list
            for task in self._tasks:
                lines.append(self._render_task(task))
        
        return "\n".join(lines)
    
    def _render_task(self, task: TaskItem) -> str:
        """Render single task."""
        status_icon = self._get_status_icon(task.status)
        priority_icon = self._get_priority_icon(task.priority) if self.config.show_priority else ""
        
        parts = [f"{status_icon} {task.title}"]
        
        if priority_icon:
            parts.append(priority_icon)
        
        if self.config.show_progress and task.progress > 0:
            parts.append(f"[{task.progress:.0f}%]")
        
        return " ".join(parts)
    
    def _get_status_icon(self, status: TaskStatus) -> str:
        """Get status icon."""
        icons = {
            TaskStatus.PENDING: "⏳",
            TaskStatus.IN_PROGRESS: "🔄",
            TaskStatus.COMPLETED: "✓",
            TaskStatus.FAILED: "✗",
            TaskStatus.CANCELLED: "⊘",
        }
        return icons.get(status, "•")
    
    def _get_priority_icon(self, priority: TaskPriority) -> str:
        """Get priority icon."""
        icons = {
            TaskPriority.LOW: "",
            TaskPriority.MEDIUM: "⚡",
            TaskPriority.HIGH: "🔥",
            TaskPriority.CRITICAL: "🚨",
        }
        return icons.get(priority, "")
    
    def get_stats(self) -> Dict[str, int]:
        """Get task statistics."""
        return {
            "total": len(self._tasks),
            "pending": len(self.get_by_status(TaskStatus.PENDING)),
            "in_progress": len(self.get_by_status(TaskStatus.IN_PROGRESS)),
            "completed": len(self.get_by_status(TaskStatus.COMPLETED)),
            "failed": len(self.get_by_status(TaskStatus.FAILED)),
        }
    
    def clear_completed(self) -> int:
        """Clear completed tasks."""
        completed = self.get_by_status(TaskStatus.COMPLETED)
        count = len(completed)
        self._tasks = [t for t in self._tasks if t.status != TaskStatus.COMPLETED]
        return count


__all__ = [
    "TaskStatus",
    "TaskPriority",
    "TaskItem",
    "TasksScreenConfig",
    "TasksScreen",
]

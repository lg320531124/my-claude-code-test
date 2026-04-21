"""Progress Tracker - Track progress of tasks and operations."""

from __future__ import annotations
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class ProgressState(Enum):
    """Progress state."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


@dataclass
class ProgressStep:
    """A progress step."""
    name: str
    description: str = ""
    state: ProgressState = ProgressState.PENDING
    progress: float = 0.0  # 0-100
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def duration(self) -> Optional[float]:
        """Get duration in seconds."""
        if self.start_time is None:
            return None
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def is_complete(self) -> bool:
        """Check if step is complete."""
        return self.state in (
            ProgressState.COMPLETED,
            ProgressState.FAILED,
            ProgressState.CANCELLED,
        )


@dataclass
class ProgressConfig:
    """Progress tracker configuration."""
    name: str = "Task"
    total_steps: int = 0
    auto_estimate: bool = True
    persist: bool = False
    history_file: str = ".progress.json"
    notify_thresholds: List[float] = field(default_factory=lambda: [25.0, 50.0, 75.0, 100.0])


@dataclass
class ProgressResult:
    """Progress result."""
    name: str
    state: ProgressState
    total_progress: float
    steps_completed: int
    steps_total: int
    duration: Optional[float]
    error: Optional[str] = None


class ProgressTracker:
    """Track progress of multi-step operations."""

    def __init__(self, config: Optional[ProgressConfig] = None):
        self.config = config or ProgressConfig()
        self._steps: List[ProgressStep] = []
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._current_step: int = 0
        self._callbacks: List[Callable[[ProgressResult], None]] = []
        self._state: ProgressState = ProgressState.PENDING
        self._error: Optional[str] = None
        self._notified_thresholds: set = set()

    def start(self) -> None:
        """Start progress tracking."""
        self._state = ProgressState.RUNNING
        self._start_time = time.time()

    def add_step(
        self,
        name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProgressStep:
        """Add a step."""
        step = ProgressStep(
            name=name,
            description=description,
            metadata=metadata or {},
        )
        self._steps.append(step)
        return step

    def begin_step(self, index: Optional[int] = None) -> ProgressStep:
        """Begin a step."""
        if index is not None:
            self._current_step = index

        if self._current_step >= len(self._steps):
            raise ValueError("No more steps available")

        step = self._steps[self._current_step]
        step.state = ProgressState.RUNNING
        step.start_time = time.time()
        self._notify_progress()
        return step

    def update_step(
        self,
        progress: float,
        index: Optional[int] = None,
    ) -> None:
        """Update step progress."""
        idx = index if index is not None else self._current_step
        if idx < len(self._steps):
            self._steps[idx].progress = progress
            self._notify_progress()

    def complete_step(
        self,
        index: Optional[int] = None,
        error: Optional[str] = None,
    ) -> ProgressStep:
        """Complete a step."""
        idx = index if index is not None else self._current_step
        if idx >= len(self._steps):
            raise ValueError("Step index out of range")

        step = self._steps[idx]
        step.end_time = time.time()

        if error:
            step.state = ProgressState.FAILED
            step.error = error
        else:
            step.state = ProgressState.COMPLETED
            step.progress = 100.0

        self._notify_progress()

        if idx == self._current_step:
            self._current_step += 1

        return step

    def fail(self, error: str) -> None:
        """Fail the entire progress."""
        self._state = ProgressState.FAILED
        self._error = error
        self._end_time = time.time()
        self._notify_progress()

    def complete(self) -> None:
        """Complete the entire progress."""
        self._state = ProgressState.COMPLETED
        self._end_time = time.time()
        self._notify_progress()

    def cancel(self) -> None:
        """Cancel progress."""
        self._state = ProgressState.CANCELLED
        self._end_time = time.time()
        self._notify_progress()

    def pause(self) -> None:
        """Pause progress."""
        self._state = ProgressState.PAUSED

    def resume(self) -> None:
        """Resume progress."""
        self._state = ProgressState.RUNNING

    def get_progress(self) -> float:
        """Get overall progress (0-100)."""
        if not self._steps:
            return 0.0

        total = sum(step.progress for step in self._steps)
        return total / len(self._steps)

    def get_result(self) -> ProgressResult:
        """Get progress result."""
        steps_completed = sum(1 for s in self._steps if s.is_complete())

        duration = None
        if self._start_time is not None:
            if self._end_time is not None:
                duration = self._end_time - self._start_time
            else:
                duration = time.time() - self._start_time

        return ProgressResult(
            name=self.config.name,
            state=self._state,
            total_progress=self.get_progress(),
            steps_completed=steps_completed,
            steps_total=len(self._steps),
            duration=duration,
            error=self._error,
        )

    def get_steps(self) -> List[ProgressStep]:
        """Get all steps."""
        return self._steps.copy()

    def get_current_step(self) -> Optional[ProgressStep]:
        """Get current step."""
        if self._current_step < len(self._steps):
            return self._steps[self._current_step]
        return None

    def add_callback(self, callback: Callable[[ProgressResult], None]) -> None:
        """Add progress callback."""
        self._callbacks.append(callback)

    def remove_callback(self, callback: Callable[[ProgressResult], None]) -> None:
        """Remove progress callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def _notify_progress(self) -> None:
        """Notify callbacks of progress update."""
        result = self.get_result()

        # Check thresholds
        progress = result.total_progress
        for threshold in self.config.notify_thresholds:
            if progress >= threshold and threshold not in self._notified_thresholds:
                self._notified_thresholds.add(threshold)
                for callback in self._callbacks:
                    callback(result)

        # Always notify on state changes
        if result.state != ProgressState.RUNNING:
            for callback in self._callbacks:
                callback(result)

    def format_progress(self) -> str:
        """Format progress as string."""
        result = self.get_result()
        progress_pct = f"{result.total_progress:.1f}%"
        steps_info = f"{result.steps_completed}/{result.steps_total}"

        duration_str = ""
        if result.duration is not None:
            duration_str = f" ({result.duration:.1f}s)"

        state_str = result.state.value

        return f"[{state_str}] {self.config.name}: {progress_pct} [{steps_info}]{duration_str}"

    def format_steps(self) -> str:
        """Format steps as list."""
        lines = []
        for i, step in enumerate(self._steps):
            status = step.state.value
            progress = f"{step.progress:.0f}%"
            duration = ""
            if step.duration() is not None:
                duration = f" ({step.duration():.1f}s)"

            lines.append(f"{i+1}. {step.name}: [{status}] {progress}{duration}")

        return "\n".join(lines)

    def estimate_remaining(self) -> Optional[float]:
        """Estimate remaining time."""
        completed_steps = [s for s in self._steps if s.is_complete()]
        if len(completed_steps) < 2:
            return None

        # Calculate average duration per step
        durations = [s.duration() for s in completed_steps if s.duration() is not None]
        if not durations:
            return None

        avg_duration = sum(durations) / len(durations)
        remaining_steps = len(self._steps) - len(completed_steps)

        return avg_duration * remaining_steps


def create_tracker(name: str, total_steps: int = 0) -> ProgressTracker:
    """Create a progress tracker."""
    config = ProgressConfig(name=name, total_steps=total_steps)
    return ProgressTracker(config)


def track_steps(
    steps: List[str],
    callback: Optional[Callable[[ProgressResult], None]] = None,
) -> ProgressTracker:
    """Track a list of steps."""
    tracker = create_tracker("Task", total_steps=len(steps))

    for step_name in steps:
        tracker.add_step(step_name)

    if callback:
        tracker.add_callback(callback)

    return tracker


__all__ = [
    "ProgressState",
    "ProgressStep",
    "ProgressConfig",
    "ProgressResult",
    "ProgressTracker",
    "create_tracker",
    "track_steps",
]
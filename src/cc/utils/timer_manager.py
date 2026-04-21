"""Timer Manager - Timer utilities for tracking durations and timeouts."""

from __future__ import annotations
import asyncio
import time
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class TimerState(Enum):
    """Timer state."""
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    EXPIRED = "expired"


@dataclass
class TimerInfo:
    """Timer information."""
    name: str
    state: TimerState = TimerState.STOPPED
    duration: float = 0.0  # Target duration in seconds
    elapsed: float = 0.0  # Elapsed time
    remaining: float = 0.0  # Remaining time
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    pause_time: Optional[float] = None
    callbacks: List[Callable] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def progress(self) -> float:
        """Get progress percentage."""
        if self.duration <= 0:
            return 100.0
        return min(100.0, (self.elapsed / self.duration) * 100)


@dataclass
class TimerConfig:
    """Timer manager configuration."""
    default_timeout: float = 30.0
    auto_cleanup: bool = True
    max_timers: int = 100
    persist: bool = False


class TimerManager:
    """Manage timers with async support."""

    def __init__(self, config: Optional[TimerConfig] = None):
        self.config = config or TimerConfig()
        self._timers: Dict[str, TimerInfo] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._callbacks: Dict[str, List[Callable]] = {}

    def create_timer(
        self,
        name: str,
        duration: float,
        callbacks: Optional[List[Callable]] = None,
        **metadata,
    ) -> TimerInfo:
        """Create a new timer."""
        if len(self._timers) >= self.config.max_timers:
            # Cleanup expired timers if auto_cleanup
            if self.config.auto_cleanup:
                self._cleanup_expired()
            else:
                raise ValueError("Maximum timers reached")

        timer = TimerInfo(
            name=name,
            duration=duration,
            callbacks=callbacks or [],
            metadata=metadata,
        )
        self._timers[name] = timer
        self._callbacks[name] = callbacks or []
        return timer

    def start_timer(self, name: str) -> bool:
        """Start a timer."""
        if name not in self._timers:
            return False

        timer = self._timers[name]
        if timer.state == TimerState.RUNNING:
            return False

        timer.state = TimerState.RUNNING
        timer.start_time = time.time()
        timer.elapsed = 0.0
        timer.remaining = timer.duration

        # Start async task
        if timer.duration > 0:
            self._tasks[name] = asyncio.create_task(
                self._timer_loop(name)
            )

        return True

    def stop_timer(self, name: str) -> TimerInfo:
        """Stop a timer."""
        if name not in self._timers:
            raise ValueError(f"Timer '{name}' not found")

        timer = self._timers[name]
        self._cancel_task(name)

        timer.state = TimerState.STOPPED
        timer.end_time = time.time()
        timer.elapsed = timer.duration - timer.remaining

        return timer

    def pause_timer(self, name: str) -> bool:
        """Pause a timer."""
        if name not in self._timers:
            return False

        timer = self._timers[name]
        if timer.state != TimerState.RUNNING:
            return False

        timer.state = TimerState.PAUSED
        timer.pause_time = time.time()
        timer.elapsed = timer.pause_time - timer.start_time
        timer.remaining = timer.duration - timer.elapsed

        self._cancel_task(name)
        return True

    def resume_timer(self, name: str) -> bool:
        """Resume a paused timer."""
        if name not in self._timers:
            return False

        timer = self._timers[name]
        if timer.state != TimerState.PAUSED:
            return False

        timer.state = TimerState.RUNNING
        # Adjust start time to account for paused duration
        pause_duration = time.time() - timer.pause_time
        timer.start_time += pause_duration
        timer.pause_time = None

        # Restart async task
        if timer.remaining > 0:
            self._tasks[name] = asyncio.create_task(
                self._timer_loop(name)
            )

        return True

    def reset_timer(self, name: str) -> TimerInfo:
        """Reset a timer."""
        if name not in self._timers:
            raise ValueError(f"Timer '{name}' not found")

        timer = self._timers[name]
        self._cancel_task(name)

        timer.state = TimerState.STOPPED
        timer.elapsed = 0.0
        timer.remaining = timer.duration
        timer.start_time = None
        timer.end_time = None
        timer.pause_time = None

        return timer

    async def _timer_loop(self, name: str) -> None:
        """Timer loop task."""
        timer = self._timers[name]
        interval = min(0.1, timer.duration / 100)

        while timer.state == TimerState.RUNNING:
            # Update elapsed and remaining
            if timer.start_time:
                timer.elapsed = time.time() - timer.start_time
                timer.remaining = max(0, timer.duration - timer.elapsed)

            # Check if expired
            if timer.remaining <= 0:
                timer.state = TimerState.EXPIRED
                timer.end_time = time.time()
                self._notify_callbacks(name, "expired")
                break

            # Check progress thresholds
            progress = timer.progress
            thresholds = [25.0, 50.0, 75.0, 90.0]
            for threshold in thresholds:
                if abs(progress - threshold) < 1.0:
                    self._notify_callbacks(name, f"progress_{int(threshold)}")

            await asyncio.sleep(interval)

        # Timer completed
        if timer.state == TimerState.EXPIRED:
            self._notify_callbacks(name, "completed")

    def _cancel_task(self, name: str) -> None:
        """Cancel timer task."""
        if name in self._tasks:
            self._tasks[name].cancel()
            del self._tasks[name]

    def _notify_callbacks(self, name: str, event: str) -> None:
        """Notify callbacks."""
        callbacks = self._callbacks.get(name, [])
        for callback in callbacks:
            timer = self._timers.get(name)
            if timer:
                callback(timer, event)

    def _cleanup_expired(self) -> None:
        """Cleanup expired timers."""
        expired = [
            name for name, timer in self._timers.items()
            if timer.state in (TimerState.EXPIRED, TimerState.COMPLETED)
        ]
        for name in expired:
            self.delete_timer(name)

    def delete_timer(self, name: str) -> None:
        """Delete a timer."""
        self._cancel_task(name)
        if name in self._timers:
            del self._timers[name]
        if name in self._callbacks:
            del self._callbacks[name]

    def get_timer(self, name: str) -> Optional[TimerInfo]:
        """Get timer info."""
        return self._timers.get(name)

    def get_all_timers(self) -> Dict[str, TimerInfo]:
        """Get all timers."""
        return self._timers.copy()

    def get_running_timers(self) -> List[TimerInfo]:
        """Get running timers."""
        return [
            timer for timer in self._timers.values()
            if timer.state == TimerState.RUNNING
        ]

    def get_elapsed(self, name: str) -> float:
        """Get elapsed time for timer."""
        timer = self._timers.get(name)
        if timer:
            if timer.state == TimerState.RUNNING and timer.start_time:
                return time.time() - timer.start_time
            return timer.elapsed
        return 0.0

    def get_remaining(self, name: str) -> float:
        """Get remaining time for timer."""
        timer = self._timers.get(name)
        if timer:
            if timer.state == TimerState.RUNNING and timer.start_time:
                return max(0, timer.duration - (time.time() - timer.start_time))
            return timer.remaining
        return 0.0

    def is_expired(self, name: str) -> bool:
        """Check if timer is expired."""
        timer = self._timers.get(name)
        return timer is not None and timer.state == TimerState.EXPIRED

    def is_running(self, name: str) -> bool:
        """Check if timer is running."""
        timer = self._timers.get(name)
        return timer is not None and timer.state == TimerState.RUNNING

    async def wait_for_timer(self, name: str) -> TimerInfo:
        """Wait for timer to complete."""
        while True:
            timer = self._timers.get(name)
            if not timer:
                raise ValueError(f"Timer '{name}' not found")

            if timer.state in (TimerState.EXPIRED, TimerState.COMPLETED, TimerState.STOPPED):
                return timer

            await asyncio.sleep(0.1)


class Stopwatch:
    """Simple stopwatch for timing operations."""

    def __init__(self, name: str = "default"):
        self.name = name
        self._start_time: Optional[float] = None
        self._stop_time: Optional[float] = None
        self._elapsed: float = 0.0
        self._lap_times: List[float] = []

    def start(self) -> None:
        """Start stopwatch."""
        self._start_time = time.time()
        self._stop_time = None

    def stop(self) -> float:
        """Stop stopwatch and return elapsed."""
        self._stop_time = time.time()
        if self._start_time:
            self._elapsed += self._stop_time - self._start_time
        return self._elapsed

    def reset(self) -> None:
        """Reset stopwatch."""
        self._start_time = None
        self._stop_time = None
        self._elapsed = 0.0
        self._lap_times = []

    def lap(self) -> float:
        """Record lap time."""
        lap_time = time.time()
        if self._start_time:
            elapsed = lap_time - self._start_time
            self._lap_times.append(elapsed)
            return elapsed
        return 0.0

    def get_elapsed(self) -> float:
        """Get elapsed time."""
        if self._start_time and not self._stop_time:
            return self._elapsed + (time.time() - self._start_time)
        return self._elapsed

    def get_laps(self) -> List[float]:
        """Get lap times."""
        return self._lap_times.copy()


class Countdown:
    """Simple countdown timer."""

    def __init__(self, duration: float):
        self.duration = duration
        self._start_time: Optional[float] = None
        self._remaining: float = duration
        self._running = False

    def start(self) -> None:
        """Start countdown."""
        self._start_time = time.time()
        self._running = True

    def stop(self) -> float:
        """Stop countdown."""
        self._running = False
        return self.get_remaining()

    def reset(self) -> None:
        """Reset countdown."""
        self._start_time = None
        self._remaining = self.duration
        self._running = False

    def get_remaining(self) -> float:
        """Get remaining time."""
        if self._running and self._start_time:
            elapsed = time.time() - self._start_time
            self._remaining = max(0, self.duration - elapsed)
        return self._remaining

    def is_expired(self) -> bool:
        """Check if countdown expired."""
        return self.get_remaining() <= 0


def create_timer_manager(max_timers: int = 100) -> TimerManager:
    """Create timer manager."""
    config = TimerConfig(max_timers=max_timers)
    return TimerManager(config)


def create_stopwatch(name: str = "default") -> Stopwatch:
    """Create stopwatch."""
    return Stopwatch(name)


def create_countdown(duration: float) -> Countdown:
    """Create countdown."""
    return Countdown(duration)


__all__ = [
    "TimerState",
    "TimerInfo",
    "TimerConfig",
    "TimerManager",
    "Stopwatch",
    "Countdown",
    "create_timer_manager",
    "create_stopwatch",
    "create_countdown",
]
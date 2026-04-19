"""Timer Tool - Timing and benchmarking."""

from __future__ import annotations
import time
import asyncio
from typing import ClassVar, Optional, Callable, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class TimerInput(ToolInput):
    """Input for TimerTool."""
    action: str = Field(description="Action: start, stop, measure, benchmark, countdown")
    name: Optional[str] = Field(default=None, description="Timer name")
    duration: Optional[float] = Field(default=None, description="Duration in seconds")
    iterations: int = Field(default=1, description="Number of iterations for benchmark")


class TimerResult(BaseModel):
    """Timer result."""
    name: str
    elapsed_seconds: float
    elapsed_ms: float
    start_time: Optional[float] = None
    end_time: Optional[float] = None


class TimerTool(ToolDef):
    """Timing and benchmarking operations."""

    name: ClassVar[str] = "Timer"
    description: ClassVar[str] = "Time operations and benchmarks"
    input_schema: ClassVar[type] = TimerInput

    # Active timers
    _timers: dict = {}

    async def execute(self, input: TimerInput, ctx: ToolUseContext) -> ToolResult:
        """Execute timer operation."""
        action = input.action

        if action == "start":
            return self._start_timer(input.name)
        elif action == "stop":
            return self._stop_timer(input.name)
        elif action == "measure":
            return await self._measure(ctx)
        elif action == "benchmark":
            return ToolResult(
                content="Benchmark requires passing a callable to measure",
                is_error=True,
            )
        elif action == "countdown":
            return await self._countdown(input.duration)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _start_timer(self, name: Optional[str]) -> ToolResult:
        """Start a named timer."""
        timer_name = name or "default"
        start_time = time.time()
        self._timers[timer_name] = start_time

        return ToolResult(
            content=f"Timer '{timer_name}' started",
            metadata={"name": timer_name, "start_time": start_time},
        )

    def _stop_timer(self, name: Optional[str]) -> ToolResult:
        """Stop a named timer."""
        timer_name = name or "default"

        if timer_name not in self._timers:
            return ToolResult(
                content=f"Timer '{timer_name}' not found",
                is_error=True,
            )

        start_time = self._timers[timer_name]
        end_time = time.time()
        elapsed = end_time - start_time

        result = TimerResult(
            name=timer_name,
            elapsed_seconds=elapsed,
            elapsed_ms=elapsed * 1000,
            start_time=start_time,
            end_time=end_time,
        )

        del self._timers[timer_name]

        return ToolResult(
            content=f"Timer '{timer_name}': {elapsed:.3f}s ({elapsed * 1000:.1f}ms)",
            metadata=result.model_dump(),
        )

    async def _measure(self, ctx: ToolUseContext) -> ToolResult:
        """Measure current session time."""
        elapsed = time.time()
        return ToolResult(
            content=f"Current time: {elapsed:.3f}s since epoch",
            metadata={"timestamp": elapsed},
        )

    async def _countdown(self, duration: Optional[float]) -> ToolResult:
        """Run countdown."""
        if duration is None:
            return ToolResult(content="Duration required", is_error=True)

        if duration <= 0:
            return ToolResult(content="Duration must be positive", is_error=True)

        # Simple countdown (no UI updates)
        await asyncio.sleep(duration)

        return ToolResult(
            content=f"Countdown complete: {duration}s",
            metadata={"duration": duration},
        )

    @classmethod
    async def benchmark(cls, func: Callable, iterations: int = 10) -> ToolResult:
        """Benchmark a function."""
        times = []

        for _ in range(iterations):
            start = time.time()
            if asyncio.iscoroutinefunction(func):
                await func()
            else:
                func()
            elapsed = time.time() - start
            times.append(elapsed)

        total = sum(times)
        avg = total / iterations
        min_time = min(times)
        max_time = max(times)

        result = f"Benchmark Results ({iterations} iterations):\n"
        result += f"  Total: {total:.3f}s\n"
        result += f"  Average: {avg:.3f}s ({avg * 1000:.1f}ms)\n"
        result += f"  Min: {min_time:.3f}s\n"
        result += f"  Max: {max_time:.3f}s\n"

        return ToolResult(
            content=result,
            metadata={
                "iterations": iterations,
                "total": total,
                "average": avg,
                "min": min_time,
                "max": max_time,
                "times": times,
            },
        )


__all__ = ["TimerTool", "TimerInput", "TimerResult"]
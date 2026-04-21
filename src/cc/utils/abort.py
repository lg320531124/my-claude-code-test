"""Abort Controller - Abort signal management."""

from __future__ import annotations
import asyncio
from typing import Callable, List, Optional
from dataclasses import dataclass, field


@dataclass
class AbortSignal:
    """Abort signal."""
    aborted: bool = False
    reason: str = ""
    _listeners: List[Callable] = field(default_factory=list)

    def add_listener(self, listener: Callable) -> None:
        """Add abort listener."""
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """Remove abort listener."""
        self._listeners.remove(listener)

    def abort(self, reason: str = "") -> None:
        """Abort."""
        if self.aborted:
            return

        self.aborted = True
        self.reason = reason

        for listener in self._listeners:
            try:
                listener(reason)
            except Exception:
                pass

        self._listeners.clear()


class AbortController:
    """Abort controller."""

    def __init__(self):
        self.signal = AbortSignal()

    def abort(self, reason: str = "") -> None:
        """Abort."""
        self.signal.abort(reason)


async def with_abort(signal: AbortSignal, coro) -> Optional[Any]:
    """Run coroutine with abort signal."""
    if signal.aborted:
        return None

    task = asyncio.create_task(coro)

    # Check abort periodically
    while not task.done():
        if signal.aborted:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                return None
        await asyncio.sleep(0.1)

    return task.result()


def create_abort_controller() -> AbortController:
    """Create abort controller."""
    return AbortController()


__all__ = [
    "AbortSignal",
    "AbortController",
    "with_abort",
    "create_abort_controller",
]
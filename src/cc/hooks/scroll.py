"""Hook Scroll - Async virtual scrolling."""

from __future__ import annotations
import asyncio
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum


class ScrollDirection(Enum):
    """Scroll direction."""
    UP = "up"
    DOWN = "down"
    LEFT = "left"
    RIGHT = "right"


@dataclass
class ScrollPosition:
    """Scroll position."""
    vertical: int = 0
    horizontal: int = 0
    max_vertical: int = 0
    max_horizontal: int = 0


@dataclass
class ScrollConfig:
    """Scroll configuration."""
    item_height: int = 1
    visible_items: int = 20
    overscan: int = 5
    scroll_step: int = 1
    page_size: int = 20
    smooth_scroll: bool = True


@dataclass
class ViewportRange:
    """Visible range in viewport."""
    start: int
    end: int
    total: int


class VirtualScroller:
    """Virtual scroll manager."""

    def __init__(self, config: Optional[ScrollConfig] = None):
        self.config = config or ScrollConfig()
        self._position = ScrollPosition()
        self._total_items: int = 0
        self._item_heights: Dict[int, int] = {}
        self._scroll_callbacks: List[Callable] = []
        self._scroll_animation: Optional[asyncio.Task] = None

    def set_total_items(self, total: int) -> None:
        """Set total items."""
        self._total_items = total
        self._position.max_vertical = max(0, total - self.config.visible_items)

    def get_visible_range(self) -> ViewportRange:
        """Get visible range."""
        start = self._position.vertical
        end = min(start + self.config.visible_items + self.config.overscan, self._total_items)
        return ViewportRange(start=start, end=end, total=self._total_items)

    async def scroll(self, direction: ScrollDirection, amount: int = None) -> None:
        """Scroll in direction."""
        if amount is None:
            amount = self.config.scroll_step

        if direction == ScrollDirection.UP:
            new_pos = self._position.vertical - amount
        elif direction == ScrollDirection.DOWN:
            new_pos = self._position.vertical + amount
        elif direction == ScrollDirection.LEFT:
            new_pos = self._position.horizontal - amount
        elif direction == ScrollDirection.RIGHT:
            new_pos = self._position.horizontal + amount
        else:
            return

        if direction in [ScrollDirection.UP, ScrollDirection.DOWN]:
            self._position.vertical = max(0, min(self._position.max_vertical, new_pos))
        else:
            self._position.horizontal = max(0, min(self._position.max_horizontal, new_pos))

        await self._notify_scroll()

    async def scroll_to(self, index: int) -> None:
        """Scroll to specific index."""
        self._position.vertical = max(0, min(self._position.max_vertical, index))
        await self._notify_scroll()

    async def scroll_page(self, direction: ScrollDirection) -> None:
        """Scroll by page."""
        amount = self.config.page_size
        await self.scroll(direction, amount)

    async def scroll_to_end(self) -> None:
        """Scroll to end."""
        self._position.vertical = self._position.max_vertical
        await self._notify_scroll()

    async def scroll_to_start(self) -> None:
        """Scroll to start."""
        self._position.vertical = 0
        await self._notify_scroll()

    async def smooth_scroll_to(self, target: int) -> None:
        """Smooth scroll animation."""
        if self._scroll_animation:
            self._scroll_animation.cancel()

        start = self._position.vertical
        distance = target - start

        if distance == 0:
            return

        async def animate():
            steps = 20
            step_size = distance / steps

            for i in range(steps):
                if not self.config.smooth_scroll:
                    break

                current = start + step_size * (i + 1)
                self._position.vertical = int(current)
                await self._notify_scroll()
                await asyncio.sleep(0.02)

            self._position.vertical = target
            await self._notify_scroll()

        self._scroll_animation = asyncio.create_task(animate())

    def get_position(self) -> ScrollPosition:
        """Get current position."""
        return self._position

    def is_at_start(self) -> bool:
        """Check if at start."""
        return self._position.vertical == 0

    def is_at_end(self) -> bool:
        """Check if at end."""
        return self._position.vertical >= self._position.max_vertical

    def set_item_height(self, index: int, height: int) -> None:
        """Set item height for variable height items."""
        self._item_heights[index] = height

    def get_scroll_percentage(self) -> float:
        """Get scroll percentage."""
        if self._position.max_vertical == 0:
            return 0.0
        return self._position.vertical / self._position.max_vertical

    def on_scroll(self, callback: Callable) -> None:
        """Register scroll callback."""
        self._scroll_callbacks.append(callback)

    async def _notify_scroll(self) -> None:
        """Notify scroll callbacks."""
        for callback in self._scroll_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(self._position, self.get_visible_range())
                else:
                    callback(self._position, self.get_visible_range())
            except Exception:
                pass


class ScrollHooks:
    """Hooks for scroll events."""

    def __init__(self, scroller: VirtualScroller):
        self._scroller = scroller

    async def pre_scroll(self, direction: ScrollDirection, amount: int) -> bool:
        """Hook before scroll."""
        # Check if scroll is valid
        if direction == ScrollDirection.UP and self._scroller.is_at_start():
            return False
        if direction == ScrollDirection.DOWN and self._scroller.is_at_end():
            return False
        return True

    async def post_scroll(self, position: ScrollPosition) -> None:
        """Hook after scroll."""
        # Update UI or trigger other actions
        pass

    async def on_key_scroll(self, key: str) -> Optional[ScrollDirection]:
        """Handle key-based scroll."""
        if key == "up" or key == "k":
            return ScrollDirection.UP
        elif key == "down" or key == "j":
            return ScrollDirection.DOWN
        elif key == "page_up":
            return ScrollDirection.UP  # Will use page_size
        elif key == "page_down":
            return ScrollDirection.DOWN
        elif key == "home" or key == "g":
            await self._scroller.scroll_to_start()
        elif key == "end" or key == "G":
            await self._scroller.scroll_to_end()
        return None


# Global scroller
_scroller: Optional[VirtualScroller] = None


def get_virtual_scroller(config: ScrollConfig = None) -> VirtualScroller:
    """Get global virtual scroller."""
    global _scroller
    if _scroller is None:
        _scroller = VirtualScroller(config)
    return _scroller


__all__ = [
    "ScrollDirection",
    "ScrollPosition",
    "ScrollConfig",
    "ViewportRange",
    "VirtualScroller",
    "ScrollHooks",
    "get_virtual_scroller",
]
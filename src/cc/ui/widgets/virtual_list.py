"""Virtual List Widget - Virtual scrolling for large lists."""

from __future__ import annotations
from typing import Any, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class ScrollDirection(Enum):
    """Scroll direction."""
    UP = "up"
    DOWN = "down"
    TOP = "top"
    BOTTOM = "bottom"


@dataclass
class VirtualListConfig:
    """Virtual list configuration."""
    item_height: int = 1
    visible_count: int = 20
    overscan: int = 5  # Extra items to render for smooth scrolling
    show_scrollbar: bool = True
    scrollbar_width: int = 1


@dataclass
class VirtualListState:
    """Virtual list state."""
    start_index: int = 0
    end_index: int = 20
    total_items: int = 0
    scroll_position: float = 0.0  # 0-100


class VirtualListWidget:
    """Widget for virtual scrolling large lists."""
    
    def __init__(self, config: VirtualListConfig = None):
        self.config = config or VirtualListConfig()
        self._items: List[Any] = []
        self._state = VirtualListState()
        self._render_item: Optional[Callable[[Any, int], str]] = None
    
    def set_items(self, items: List[Any]) -> None:
        """Set list items."""
        self._items = items
        self._state.total_items = len(items)
        self._state.end_index = min(self.config.visible_count, len(items))
    
    def set_renderer(self, renderer: Callable[[Any, int], str]) -> None:
        """Set item renderer function."""
        self._render_item = renderer
    
    def scroll(self, direction: ScrollDirection, amount: int = 1) -> None:
        """Scroll list."""
        if direction == ScrollDirection.UP:
            self._state.start_index = max(0, self._state.start_index - amount)
        
        elif direction == ScrollDirection.DOWN:
            max_start = max(0, len(self._items) - self.config.visible_count)
            self._state.start_index = min(max_start, self._state.start_index + amount)
        
        elif direction == ScrollDirection.TOP:
            self._state.start_index = 0
        
        elif direction == ScrollDirection.BOTTOM:
            max_start = max(0, len(self._items) - self.config.visible_count)
            self._state.start_index = max_start
        
        self._update_state()
    
    def scroll_to_index(self, index: int) -> None:
        """Scroll to specific index."""
        if index < 0:
            index = 0
        elif index >= len(self._items):
            index = len(self._items) - 1
        
        # Center the item
        half = self.config.visible_count // 2
        self._state.start_index = max(0, index - half)
        self._update_state()
    
    def _update_state(self) -> None:
        """Update internal state."""
        self._state.end_index = min(
            self._state.start_index + self.config.visible_count + self.config.overscan,
            len(self._items)
        )
        
        if len(self._items) > 0:
            self._state.scroll_position = (self._state.start_index / len(self._items)) * 100
    
    def get_visible_items(self) -> List[Any]:
        """Get currently visible items."""
        return self._items[self._state.start_index:self._state.end_index]
    
    def render(self) -> str:
        """Render visible portion."""
        visible = self.get_visible_items()
        lines = []
        
        # Render items
        for i, item in enumerate(visible):
            actual_index = self._state.start_index + i
            
            if self._render_item:
                lines.append(self._render_item(item, actual_index))
            else:
                lines.append(str(item))
        
        # Add scrollbar if enabled
        if self.config.show_scrollbar and len(self._items) > self.config.visible_count:
            scrollbar = self._render_scrollbar()
            lines = [line + scrollbar[i] if i < len(scrollbar) else line for i, line in enumerate(lines)]
        
        return "\n".join(lines)
    
    def _render_scrollbar(self) -> List[str]:
        """Render scrollbar."""
        height = self.config.visible_count
        position = self._state.scroll_position
        
        # Calculate thumb position
        thumb_height = max(1, int(height * (self.config.visible_count / len(self._items))))
        thumb_pos = int((position / 100) * (height - thumb_height))
        
        scrollbar = []
        for i in range(height):
            if thumb_pos <= i < thumb_pos + thumb_height:
                scrollbar.append("█")
            else:
                scrollbar.append("│")
        
        return scrollbar
    
    def get_state(self) -> VirtualListState:
        """Get current state."""
        return self._state
    
    def get_total(self) -> int:
        """Get total item count."""
        return len(self._items)
    
    def is_empty(self) -> bool:
        """Check if list is empty."""
        return len(self._items) == 0


# Global virtual list factory
def create_virtual_list(
    items: List[Any] = None,
    visible_count: int = 20,
    renderer: Callable = None,
) -> VirtualListWidget:
    """Create virtual list widget."""
    config = VirtualListConfig(visible_count=visible_count)
    widget = VirtualListWidget(config)
    
    if items:
        widget.set_items(items)
    
    if renderer:
        widget.set_renderer(renderer)
    
    return widget


__all__ = [
    "ScrollDirection",
    "VirtualListConfig",
    "VirtualListState",
    "VirtualListWidget",
    "create_virtual_list",
]

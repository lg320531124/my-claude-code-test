"""Hook Input - Async input handling hooks."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class InputEventType(Enum):
    """Input event types."""
    KEY_PRESS = "key_press"
    KEY_RELEASE = "key_release"
    TEXT_INPUT = "text_input"
    PASTE = "paste"
    COMMAND = "command"
    COMPLETION_REQUEST = "completion_request"


@dataclass
class InputEvent:
    """Input event."""
    type: InputEventType
    data: str = ""
    key: str = ""
    modifiers: List[str] = field(default_factory=list)
    position: int = 0
    timestamp: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InputState:
    """Current input state."""
    text: str = ""
    cursor_position: int = 0
    selection_start: Optional[int] = None
    selection_end: Optional[int] = None
    history: List[str] = field(default_factory=list)
    history_index: int = 0
    completions: List[str] = field(default_factory=list)
    completion_index: int = 0


class InputHandler:
    """Async input handler."""

    def __init__(self):
        self._state = InputState()
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._key_handlers: Dict[str, Callable] = {}
        self._input_handlers: List[Callable] = []
        self._running: bool = False

    async def start(self) -> None:
        """Start input handler."""
        self._running = True
        asyncio.create_task(self._process_events())

    async def stop(self) -> None:
        """Stop input handler."""
        self._running = False

    async def handle_event(self, event: InputEvent) -> None:
        """Handle input event."""
        await self._event_queue.put(event)

    async def _process_events(self) -> None:
        """Process event queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(
                    self._event_queue.get(),
                    timeout=0.5,
                )
                await self._dispatch_event(event)
            except asyncio.TimeoutError:
                continue

    async def _dispatch_event(self, event: InputEvent) -> None:
        """Dispatch event to handlers."""
        if event.type == InputEventType.KEY_PRESS:
            handler = self._key_handlers.get(event.key)
            if handler:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)

        elif event.type == InputEventType.TEXT_INPUT:
            for handler in self._input_handlers:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(event)
                    else:
                        handler(event)
                except Exception:
                    pass

    def register_key_handler(self, key: str, handler: Callable) -> None:
        """Register key handler."""
        self._key_handlers[key] = handler

    def register_input_handler(self, handler: Callable) -> None:
        """Register input handler."""
        self._input_handlers.append(handler)

    def get_state(self) -> InputState:
        """Get current state."""
        return self._state

    def update_text(self, text: str, position: int = None) -> None:
        """Update input text."""
        self._state.text = text
        if position is not None:
            self._state.cursor_position = position
        else:
            self._state.cursor_position = len(text)

    def insert_text(self, text: str) -> None:
        """Insert text at cursor."""
        pos = self._state.cursor_position
        current = self._state.text

        new_text = current[:pos] + text + current[pos:]
        self._state.text = new_text
        self._state.cursor_position = pos + len(text)

    def delete_text(self, length: int = 1, forward: bool = False) -> None:
        """Delete text at cursor."""
        pos = self._state.cursor_position
        current = self._state.text

        if forward:
            new_text = current[:pos] + current[pos + length:]
        else:
            new_text = current[:pos - length] + current[pos:]
            pos -= length

        self._state.text = new_text
        self._state.cursor_position = pos

    def move_cursor(self, offset: int) -> None:
        """Move cursor."""
        new_pos = self._state.cursor_position + offset
        self._state.cursor_position = max(0, min(len(self._state.text), new_pos))

    def set_selection(self, start: int, end: int) -> None:
        """Set selection."""
        self._state.selection_start = start
        self._state.selection_end = end

    def clear_selection(self) -> None:
        """Clear selection."""
        self._state.selection_start = None
        self._state.selection_end = None

    def get_selection_text(self) -> Optional[str]:
        """Get selected text."""
        if self._state.selection_start and self._state.selection_end:
            return self._state.text[self._state.selection_start:self._state.selection_end]
        return None

    def add_history(self, text: str) -> None:
        """Add to history."""
        if text and text != self._state.history[-1] if self._state.history else True:
            self._state.history.append(text)
            self._state.history_index = len(self._state.history)

    def history_up(self) -> Optional[str]:
        """Go up in history."""
        if self._state.history_index > 0:
            self._state.history_index -= 1
            return self._state.history[self._state.history_index]
        return None

    def history_down(self) -> Optional[str]:
        """Go down in history."""
        if self._state.history_index < len(self._state.history) - 1:
            self._state.history_index += 1
            return self._state.history[self._state.history_index]
        return None

    def set_completions(self, completions: List[str]) -> None:
        """Set completions."""
        self._state.completions = completions
        self._state.completion_index = 0

    def next_completion(self) -> Optional[str]:
        """Get next completion."""
        if self._state.completions:
            self._state.completion_index = (self._state.completion_index + 1) % len(self._state.completions)
            return self._state.completions[self._state.completion_index]
        return None

    def prev_completion(self) -> Optional[str]:
        """Get previous completion."""
        if self._state.completions:
            self._state.completion_index = (self._state.completion_index - 1) % len(self._state.completions)
            return self._state.completions[self._state.completion_index]
        return None


class TextInputHooks:
    """Hooks for text input."""

    def __init__(self, handler: InputHandler):
        self._handler = handler

    async def pre_input(self, event: InputEvent) -> InputEvent:
        """Hook before input."""
        # Validate input
        if event.type == InputEventType.TEXT_INPUT:
            # Filter unwanted characters
            event.data = self._filter_input(event.data)

        return event

    async def post_input(self, event: InputEvent) -> InputEvent:
        """Hook after input."""
        # Update state
        if event.type == InputEventType.TEXT_INPUT:
            self._handler.insert_text(event.data)

        return event

    def _filter_input(self, text: str) -> str:
        """Filter input text."""
        # Remove control characters except newline
        filtered = "".join(
            c for c in text
            if c.isprintable() or c == "\n"
        )
        return filtered


# Global handler
_handler: Optional[InputHandler] = None


def get_input_handler() -> InputHandler:
    """Get global input handler."""
    global _handler
    if _handler is None:
        _handler = InputHandler()
    return _handler


__all__ = [
    "InputEventType",
    "InputEvent",
    "InputState",
    "InputHandler",
    "TextInputHooks",
    "get_input_handler",
]
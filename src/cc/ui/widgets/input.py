"""Input Widget - Terminal input handling."""

from __future__ import annotations
import asyncio
from typing import Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class InputMode(Enum):
    """Input modes."""
    SINGLE_LINE = "single_line"
    MULTI_LINE = "multi_line"
    PASSWORD = "password"
    SEARCH = "search"
    COMMAND = "command"


@dataclass
class InputConfig:
    """Input configuration."""
    mode: InputMode = InputMode.SINGLE_LINE
    placeholder: str = ""
    default: str = ""
    max_length: int = 10000
    multiline_marker: str = "..."
    history_enabled: bool = True
    completion_enabled: bool = True
    echo: bool = True  # For password mode


@dataclass
class InputState:
    """Input state."""
    text: str = ""
    cursor_pos: int = 0
    history: List[str] = field(default_factory=list)
    history_index: int = -1
    completions: List[str] = field(default_factory=list)
    completion_index: int = -1
    started_at: Optional[datetime] = None


class InputWidget:
    """Terminal input widget."""

    def __init__(self, config: InputConfig = None):
        self._config = config or InputConfig()
        self._state = InputState()
        self._state.text = self._config.default
        self._state.cursor_pos = len(self._config.default)
        self._submit_callback: Optional[Callable] = None
        _change_callback: Optional[Callable] = None

    async def read(self) -> str:
        """Read input from terminal.

        Returns:
            Input text
        """
        self._state.started_at = datetime.now()

        # Show placeholder if empty
        if not self._state.text and self._config.placeholder:
            self._render(self._config.placeholder)

        # Read input loop
        while True:
            # Get key press
            key = await self._read_key()

            if key == "enter":
                if self._config.mode == InputMode.MULTI_LINE:
                    # Check for submit marker
                    if self._state.text.endswith("\n"):
                        return self._state.text.rstrip("\n")
                    self._state.text += "\n"
                    self._state.cursor_pos = len(self._state.text)
                else:
                    return self._state.text

            elif key == "escape":
                return ""

            elif key == "backspace":
                self._delete_before_cursor()

            elif key == "delete":
                self._delete_at_cursor()

            elif key == "arrow_up":
                if self._config.history_enabled:
                    self._history_prev()
                elif self._config.mode == InputMode.MULTI_LINE:
                    self._cursor_up()

            elif key == "arrow_down":
                if self._config.history_enabled:
                    self._history_next()
                elif self._config.mode == InputMode.MULTI_LINE:
                    self._cursor_down()

            elif key == "arrow_left":
                self._cursor_left()

            elif key == "arrow_right":
                self._cursor_right()

            elif key == "home":
                self._state.cursor_pos = 0

            elif key == "end":
                self._state.cursor_pos = len(self._state.text)

            elif key == "tab":
                if self._config.completion_enabled:
                    await self._complete()

            elif key == "ctrl_c":
                raise KeyboardInterrupt()

            elif key == "ctrl_d":
                if not self._state.text:
                    raise EOFError()

            elif key == "ctrl_u":
                self._state.text = self._state.text[self._state.cursor_pos:]
                self._state.cursor_pos = 0

            elif key == "ctrl_k":
                self._state.text = self._state.text[:self._state.cursor_pos]

            elif key == "ctrl_w":
                self._delete_word_before_cursor()

            elif len(key) == 1 and key.isprintable():
                self._insert_char(key)

            self._render()

    async def _read_key(self) -> str:
        """Read single key from terminal.

        Returns:
            Key string
        """
        # This would integrate with actual terminal input
        # For now, placeholder implementation
        await asyncio.sleep(0.01)
        return ""

    def _insert_char(self, char: str) -> None:
        """Insert character at cursor."""
        if len(self._state.text) < self._config.max_length:
            self._state.text = (
                self._state.text[:self._state.cursor_pos] +
                char +
                self._state.text[self._state.cursor_pos:]
            )
            self._state.cursor_pos += 1

    def _delete_before_cursor(self) -> None:
        """Delete character before cursor."""
        if self._state.cursor_pos > 0:
            self._state.text = (
                self._state.text[:self._state.cursor_pos - 1] +
                self._state.text[self._state.cursor_pos:]
            )
            self._state.cursor_pos -= 1

    def _delete_at_cursor(self) -> None:
        """Delete character at cursor."""
        if self._state.cursor_pos < len(self._state.text):
            self._state.text = (
                self._state.text[:self._state.cursor_pos] +
                self._state.text[self._state.cursor_pos + 1:]
            )

    def _delete_word_before_cursor(self) -> None:
        """Delete word before cursor."""
        text_before = self._state.text[:self._state.cursor_pos]
        words = text_before.split()
        if words:
            new_text_before = " ".join(words[:-1])
            if new_text_before:
                new_text_before += " "
            self._state.text = new_text_before + self._state.text[self._state.cursor_pos:]
            self._state.cursor_pos = len(new_text_before)

    def _cursor_left(self) -> None:
        """Move cursor left."""
        if self._state.cursor_pos > 0:
            self._state.cursor_pos -= 1

    def _cursor_right(self) -> None:
        """Move cursor right."""
        if self._state.cursor_pos < len(self._state.text):
            self._state.cursor_pos += 1

    def _cursor_up(self) -> None:
        """Move cursor up (multiline)."""
        # Find previous line
        text_before = self._state.text[:self._state.cursor_pos]
        lines = text_before.split("\n")
        if len(lines) > 1:
            prev_line_len = len(lines[-2])
            current_line_pos = len(lines[-1])
            self._state.cursor_pos = len(text_before) - current_line_pos - 1 + min(prev_line_len, current_line_pos)

    def _cursor_down(self) -> None:
        """Move cursor down (multiline)."""
        # Find next line
        text_after = self._state.text[self._state.cursor_pos:]
        if "\n" in text_after:
            next_line_end = text_after.find("\n")
            next_line = text_after[:next_line_end]
            current_line_before = self._state.text[:self._state.cursor_pos]
            current_line_start = current_line_before.rfind("\n") + 1 if "\n" in current_line_before else 0
            current_line_pos = self._state.cursor_pos - current_line_start
            self._state.cursor_pos += next_line_end + 1 + min(current_line_pos, len(next_line))

    def _history_prev(self) -> None:
        """Go to previous history item."""
        if self._state.history and self._state.history_index < len(self._state.history) - 1:
            self._state.history_index += 1
            self._state.text = self._state.history[-(self._state.history_index + 1)]
            self._state.cursor_pos = len(self._state.text)

    def _history_next(self) -> None:
        """Go to next history item."""
        if self._state.history_index > 0:
            self._state.history_index -= 1
            self._state.text = self._state.history[-(self._state.history_index + 1)]
            self._state.cursor_pos = len(self._state.text)
        elif self._state.history_index == 0:
            self._state.history_index = -1
            self._state.text = self._config.default
            self._state.cursor_pos = len(self._config.default)

    async def _complete(self) -> None:
        """Trigger completion."""
        # Placeholder - would integrate with completion system
        pass

    def _render(self, placeholder: str = None) -> None:
        """Render input."""
        text = placeholder if placeholder else self._state.text

        if self._config.mode == InputMode.PASSWORD:
            text = "*" * len(text)

        # Show cursor position
        display = text[:self._state.cursor_pos] + "█" + text[self._state.cursor_pos:]

        # Placeholder implementation - would use terminal rendering
        pass

    def add_to_history(self, text: str) -> None:
        """Add to history."""
        if self._config.history_enabled and text:
            self._state.history.append(text)
            # Limit history size
            if len(self._state.history) > 1000:
                self._state.history = self._state.history[-1000:]

    def set_completions(self, completions: List[str]) -> None:
        """Set completions."""
        self._state.completions = completions

    def set_submit_callback(self, callback: Callable) -> None:
        """Set submit callback."""
        self._submit_callback = callback

    def clear(self) -> None:
        """Clear input."""
        self._state.text = self._config.default
        self._state.cursor_pos = len(self._config.default)
        self._state.completions = []
        self._state.completion_index = -1

    @property
    def text(self) -> str:
        """Get current text."""
        return self._state.text

    @property
    def cursor_position(self) -> int:
        """Get cursor position."""
        return self._state.cursor_pos


# Global input
_main_input: Optional[InputWidget] = None


def get_input(config: InputConfig = None) -> InputWidget:
    """Get main input widget."""
    global _main_input
    if _main_input is None:
        _main_input = InputWidget(config)
    return _main_input


__all__ = [
    "InputMode",
    "InputConfig",
    "InputState",
    "InputWidget",
    "get_input",
]

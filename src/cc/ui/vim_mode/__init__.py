"""Vim Modes - Vim editing modes implementation."""

from __future__ import annotations
import asyncio
from typing import Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class VimMode(Enum):
    """Vim modes."""
    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    VISUAL_LINE = "visual_line"
    VISUAL_BLOCK = "visual_block"
    COMMAND = "command"
    REPLACE = "replace"


@dataclass
class VimState:
    """Vim state."""
    mode: VimMode = VimMode.NORMAL
    cursor_line: int = 0
    cursor_col: int = 0
    visual_start_line: int = 0
    visual_start_col: int = 0
    last_search: str = ""
    last_search_direction: str = "/"  # "/" or "?"
    register: str = ""  # Yanked text
    count: int = 0  # Pending count prefix
    pending_operator: Optional[str] = None
    pending_motion: Optional[str] = None
    marks: Dict[str, tuple] = field(default_factory=dict)
    last_line: int = 0


@dataclass
class VimCommand:
    """Vim command result."""
    action: str
    text: str = ""
    position: tuple = (0, 0)
    mode_change: Optional[VimMode] = None
    count: int = 1


class VimModeHandler:
    """Handle vim mode transitions."""

    def __init__(self):
        self._state = VimState()
        self._mode_handlers: Dict[VimMode, Callable] = {}
        self._transition_hooks: List[Callable] = []

    def get_state(self) -> VimState:
        """Get current state."""
        return self._state

    def set_mode(self, mode: VimMode) -> None:
        """Set vim mode."""
        old_mode = self._state.mode
        self._state.mode = mode

        # Reset pending state
        self._state.count = 0
        self._state.pending_operator = None
        self._state.pending_motion = None

        # Notify hooks
        for hook in self._transition_hooks:
            try:
                hook(old_mode, mode)
            except Exception:
                pass

    def on_mode_transition(self, hook: Callable) -> None:
        """Register mode transition hook."""
        self._transition_hooks.append(hook)

    async def handle_key(self, key: str) -> Optional[VimCommand]:
        """Handle key in current mode."""
        handler = self._mode_handlers.get(self._state.mode)

        if handler:
            if asyncio.iscoroutinefunction(handler):
                return await handler(key, self._state)
            else:
                return handler(key, self._state)

        return None

    def register_mode_handler(self, mode: VimMode, handler: Callable) -> None:
        """Register handler for mode."""
        self._mode_handlers[mode] = handler


class NormalMode:
    """Normal mode handler."""

    OPERATORS = {"d", "y", "c", ">", "<", "gu", "gU"}
    MOTIONS = {"h", "j", "k", "l", "w", "b", "e", "W", "B", "E", "0", "$", "gg", "G"}

    def handle(self, key: str, state: VimState) -> Optional[VimCommand]:
        """Handle key in normal mode."""
        # Count prefix
        if key.isdigit() and (state.count > 0 or key != "0"):
            state.count = state.count * 10 + int(key)
            return None

        # Mode switches
        if key == "i":
            return VimCommand(action="insert", mode_change=VimMode.INSERT)

        if key == "a":
            return VimCommand(
                action="insert_after",
                position=(state.cursor_line, state.cursor_col + 1),
                mode_change=VimMode.INSERT,
            )

        if key == "I":
            return VimCommand(action="insert_line_start", mode_change=VimMode.INSERT)

        if key == "A":
            return VimCommand(action="insert_line_end", mode_change=VimMode.INSERT)

        if key == "o":
            return VimCommand(action="open_below", mode_change=VimMode.INSERT)

        if key == "O":
            return VimCommand(action="open_above", mode_change=VimMode.INSERT)

        if key == "v":
            state.visual_start_line = state.cursor_line
            state.visual_start_col = state.cursor_col
            return VimCommand(action="visual", mode_change=VimMode.VISUAL)

        if key == "V":
            state.visual_start_line = state.cursor_line
            return VimCommand(action="visual_line", mode_change=VimMode.VISUAL_LINE)

        if key == ":":
            return VimCommand(action="command", mode_change=VimMode.COMMAND)

        if key == "R":
            return VimCommand(action="replace", mode_change=VimMode.REPLACE)

        # Operators
        if key in self.OPERATORS:
            state.pending_operator = key
            return None

        # Motions
        if key in self.MOTIONS or (key.startswith("g") and len(key) >= 2):
            count = state.count or 1

            if state.pending_operator:
                # Operator + motion combo
                result = VimCommand(
                    action=f"{state.pending_operator}_{key}",
                    count=count,
                )
                state.pending_operator = None
                state.count = 0
                return result

            # Simple motion
            return VimCommand(action=f"move_{key}", count=count)

        # Special commands
        if key == "x":
            return VimCommand(action="delete_char", count=state.count or 1)

        if key == "X":
            return VimCommand(action="delete_char_before", count=state.count or 1)

        if key == "r":
            state.pending_operator = "r"
            return None

        if key == "p":
            return VimCommand(action="paste", count=state.count or 1)

        if key == "P":
            return VimCommand(action="paste_before", count=state.count or 1)

        if key == "u":
            return VimCommand(action="undo")

        if key == "J":
            return VimCommand(action="join_lines", count=state.count or 1)

        if key == "/":
            return VimCommand(action="search_forward")

        if key == "?":
            return VimCommand(action="search_backward")

        if key == "n":
            return VimCommand(action="search_next")

        if key == "N":
            return VimCommand(action="search_prev")

        # Reset count on unrecognized key
        state.count = 0
        return None


class InsertMode:
    """Insert mode handler."""

    def handle(self, key: str, state: VimState) -> Optional[VimCommand]:
        """Handle key in insert mode."""
        if key == "escape":
            return VimCommand(action="exit_insert", mode_change=VimMode.NORMAL)

        if key == "backspace":
            return VimCommand(action="backspace")

        if key == "enter":
            return VimCommand(action="newline")

        if key == "tab":
            return VimCommand(action="tab")

        # Regular character insertion
        return VimCommand(action="insert_char", text=key)


class VisualMode:
    """Visual mode handler."""

    def handle(self, key: str, state: VimState) -> Optional[VimCommand]:
        """Handle key in visual mode."""
        if key == "escape":
            return VimCommand(action="exit_visual", mode_change=VimMode.NORMAL)

        # Motions extend selection
        if key in {"h", "j", "k", "l", "w", "b", "e", "$", "0"}:
            return VimCommand(action=f"extend_{key}")

        # Operators act on selection
        if key == "d":
            return VimCommand(action="delete_selection", mode_change=VimMode.NORMAL)

        if key == "y":
            return VimCommand(action="yank_selection", mode_change=VimMode.NORMAL)

        if key == "c":
            return VimCommand(action="change_selection", mode_change=VimMode.INSERT)

        return None


class CommandMode:
    """Command mode handler (ex commands)."""

    EX_COMMANDS = {
        "w": "write",
        "q": "quit",
        "wq": "write_quit",
        "x": "write_quit",
        "d": "delete_lines",
        "s": "substitute",
        "g": "global",
        "v": "vglobal",
        "m": "move",
        "co": "copy",
        "set": "set_option",
    }

    def handle(self, key: str, state: VimState) -> Optional[VimCommand]:
        """Handle key in command mode."""
        if key == "escape":
            return VimCommand(action="exit_command", mode_change=VimMode.NORMAL)

        if key == "enter":
            # Parse and execute command
            return VimCommand(action="execute_command")

        # Build command string
        return VimCommand(action="command_char", text=key)


# Global handler
_handler: Optional[VimModeHandler] = None


def get_vim_handler() -> VimModeHandler:
    """Get global vim handler."""
    global _handler
    if _handler is None:
        _handler = VimModeHandler()
        _handler.register_mode_handler(VimMode.NORMAL, NormalMode().handle)
        _handler.register_mode_handler(VimMode.INSERT, InsertMode().handle)
        _handler.register_mode_handler(VimMode.VISUAL, VisualMode().handle)
        _handler.register_mode_handler(VimMode.COMMAND, CommandMode().handle)
    return _handler


__all__ = [
    "VimMode",
    "VimState",
    "VimCommand",
    "VimModeHandler",
    "NormalMode",
    "InsertMode",
    "VisualMode",
    "CommandMode",
    "get_vim_handler",
]
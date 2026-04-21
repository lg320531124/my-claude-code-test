"""Vim Module - Vim-like editing mode implementation.

Provides vim motions, operators, text objects, and state management
for text editing in terminal interfaces.
"""

from __future__ import annotations
from enum import Enum
from typing import Optional, Tuple, List, Callable, Dict, Any
from dataclasses import dataclass


class VimMode(Enum):
    """Vim editing modes."""
    NORMAL = "normal"
    INSERT = "insert"
    VISUAL = "visual"
    VISUAL_LINE = "visual_line"
    VISUAL_BLOCK = "visual_block"
    COMMAND = "command"
    REPLACE = "replace"


class VimState:
    """Vim state machine."""

    def __init__(self):
        self.mode: VimMode = VimMode.NORMAL
        self.pending_operator: Optional[str] = None
        self.pending_count: int = 0
        self.pending_motion: Optional[str] = None
        self.register: str = ""  # Default register
        self.last_search: str = ""
        self.last_search_direction: int = 1  # 1 forward, -1 backward
        self.cursor_pos: Tuple[int, int] = (0, 0)  # (line, col)
        self.visual_start: Optional[Tuple[int, int]] = None
        self.visual_end: Optional[Tuple[int, int]] = None

    def is_operator_pending(self) -> bool:
        """Check if operator is pending."""
        return self.pending_operator is not None

    def is_motion_pending(self) -> bool:
        """Check if motion is pending after operator."""
        return self.is_operator_pending() and self.pending_motion is not None

    def reset_pending(self) -> None:
        """Reset pending state."""
        self.pending_operator = None
        self.pending_count = 0
        self.pending_motion = None

    def get_count(self, default: int = 1) -> int:
        """Get pending count or default."""
        return self.pending_count if self.pending_count > 0 else default

    def transition_to(self, mode: VimMode) -> None:
        """Transition to new mode."""
        if mode == VimMode.VISUAL or mode == VimMode.VISUAL_LINE or mode == VimMode.VISUAL_BLOCK:
            self.visual_start = self.cursor_pos
            self.visual_end = self.cursor_pos
        elif self.mode in (VimMode.VISUAL, VimMode.VISUAL_LINE, VimMode.VISUAL_BLOCK):
            if mode in (VimMode.NORMAL, VimMode.INSERT):
                self.visual_start = None
                self.visual_end = None

        self.mode = mode
        self.reset_pending()


@dataclass
class MotionResult:
    """Result of a vim motion."""
    start: Tuple[int, int]
    end: Tuple[int, int]
    linewise: bool = False
    exclusive: bool = False  # End position excluded


@dataclass
class OperatorResult:
    """Result of a vim operator."""
    text: str
    register: str
    cursor_pos: Tuple[int, int]


# Import submodules
from .motions import VimMotions, MOTION_REGISTRY
from .operators import VimOperators, OperatorContext, OPERATOR_REGISTRY
from .text_objects import VimTextObjects, TEXT_OBJECT_REGISTRY
from .transitions import VimTransitions, TransitionResult


__all__ = [
    # Core
    "VimMode",
    "VimState",
    "MotionResult",
    "OperatorResult",
    # Submodules
    "VimMotions",
    "MOTION_REGISTRY",
    "VimOperators",
    "OperatorContext",
    "OPERATOR_REGISTRY",
    "VimTextObjects",
    "TEXT_OBJECT_REGISTRY",
    "VimTransitions",
    "TransitionResult",
]
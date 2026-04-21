"""Vim Motions - Vim motion commands."""

from __future__ import annotations
from typing import Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum


class MotionType(Enum):
    """Motion types."""
    CHAR = "char"
    WORD = "word"
    LINE = "line"
    SCREEN = "screen"
    FILE = "file"
    SEARCH = "search"
    MARK = "mark"


@dataclass
class MotionResult:
    """Motion result."""
    line: int
    col: int
    motion_type: MotionType
    linewise: bool = False


class VimMotions:
    """Vim motion implementations."""

    def __init__(self):
        self._motions: Dict[str, Callable] = {}
        self._load_motions()

    def _load_motions(self) -> None:
        """Load motion handlers."""
        self._motions = {
            # Character motions
            "h": self._motion_h,
            "l": self._motion_l,
            "j": self._motion_j,
            "k": self._motion_k,

            # Word motions
            "w": self._motion_w,
            "W": self._motion_W,
            "b": self._motion_b,
            "B": self._motion_B,
            "e": self._motion_e,
            "E": self._motion_E,

            # Line motions
            "0": self._motion_0,
            "$": self._motion_dollar,
            "^": self._motion_caret,
            "_": self._motion_underline,

            # File motions
            "gg": self._motion_gg,
            "G": self._motion_G,

            # Percent motion
            "%": self._motion_percent,

            # Search motions
            "f": self._motion_f,
            "F": self._motion_F,
            "t": self._motion_t,
            "T": self._motion_T,

            # Mark motions
            "'": self._motion_mark,
            "`": self._motion_mark_exact,
        }

    def execute(self, motion: str, state: Dict[str, Any], count: int = 1) -> MotionResult:
        """Execute motion."""
        handler = self._motions.get(motion)

        if handler:
            return handler(state, count)

        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.CHAR,
        )

    def _motion_h(self, state: Dict, count: int) -> MotionResult:
        """Move left."""
        col = state.get("col", 0) - count
        col = max(0, col)
        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.CHAR,
        )

    def _motion_l(self, state: Dict, count: int) -> MotionResult:
        """Move right."""
        line_text = state.get("line_text", "")
        max_col = len(line_text) - 1 if line_text else 0
        col = state.get("col", 0) + count
        col = min(max_col, col)
        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.CHAR,
        )

    def _motion_j(self, state: Dict, count: int) -> MotionResult:
        """Move down."""
        total_lines = state.get("total_lines", 1)
        line = state.get("line", 0) + count
        line = min(total_lines - 1, line)
        return MotionResult(
            line=line,
            col=state.get("col", 0),
            motion_type=MotionType.LINE,
            linewise=True,
        )

    def _motion_k(self, state: Dict, count: int) -> MotionResult:
        """Move up."""
        line = state.get("line", 0) - count
        line = max(0, line)
        return MotionResult(
            line=line,
            col=state.get("col", 0),
            motion_type=MotionType.LINE,
            linewise=True,
        )

    def _motion_w(self, state: Dict, count: int) -> MotionResult:
        """Move to next word start."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0)

        for _ in range(count):
            # Skip current word
            while col < len(line_text) and line_text[col].isalnum():
                col += 1

            # Skip punctuation/whitespace
            while col < len(line_text) and not line_text[col].isalnum():
                col += 1

        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.WORD,
        )

    def _motion_W(self, state: Dict, count: int) -> MotionResult:
        """Move to next WORD start (whitespace delimited)."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0)

        for _ in range(count):
            # Skip non-whitespace
            while col < len(line_text) and not line_text[col].isspace():
                col += 1

            # Skip whitespace
            while col < len(line_text) and line_text[col].isspace():
                col += 1

        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.WORD,
        )

    def _motion_b(self, state: Dict, count: int) -> MotionResult:
        """Move to previous word start."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0)

        for _ in range(count):
            # Move back past whitespace/punctuation
            while col > 0 and not line_text[col - 1].isalnum():
                col -= 1

            # Move back through word
            while col > 0 and line_text[col - 1].isalnum():
                col -= 1

        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.WORD,
        )

    def _motion_B(self, state: Dict, count: int) -> MotionResult:
        """Move to previous WORD start."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0)

        for _ in range(count):
            # Move back through whitespace
            while col > 0 and line_text[col - 1].isspace():
                col -= 1

            # Move back through WORD
            while col > 0 and not line_text[col - 1].isspace():
                col -= 1

        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.WORD,
        )

    def _motion_e(self, state: Dict, count: int) -> MotionResult:
        """Move to word end."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0) + 1

        for _ in range(count):
            # Skip whitespace/punctuation
            while col < len(line_text) and not line_text[col].isalnum():
                col += 1

            # Move through word
            while col < len(line_text) - 1 and line_text[col + 1].isalnum():
                col += 1

        return MotionResult(
            line=state.get("line", 0),
            col=min(col, len(line_text) - 1),
            motion_type=MotionType.WORD,
        )

    def _motion_E(self, state: Dict, count: int) -> MotionResult:
        """Move to WORD end."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0) + 1

        for _ in range(count):
            # Skip whitespace
            while col < len(line_text) and line_text[col].isspace():
                col += 1

            # Move through WORD
            while col < len(line_text) - 1 and not line_text[col + 1].isspace():
                col += 1

        return MotionResult(
            line=state.get("line", 0),
            col=min(col, len(line_text) - 1),
            motion_type=MotionType.WORD,
        )

    def _motion_0(self, state: Dict, count: int) -> MotionResult:
        """Move to line start."""
        return MotionResult(
            line=state.get("line", 0),
            col=0,
            motion_type=MotionType.LINE,
        )

    def _motion_dollar(self, state: Dict, count: int) -> MotionResult:
        """Move to line end."""
        line_text = state.get("line_text", "")
        return MotionResult(
            line=state.get("line", 0),
            col=max(0, len(line_text) - 1),
            motion_type=MotionType.LINE,
        )

    def _motion_caret(self, state: Dict, count: int) -> MotionResult:
        """Move to first non-blank character."""
        line_text = state.get("line_text", "")
        col = 0
        while col < len(line_text) and line_text[col].isspace():
            col += 1
        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.LINE,
        )

    def _motion_underline(self, state: Dict, count: int) -> MotionResult:
        """Move to first non-blank character N lines down."""
        line_text = state.get("line_text", "")
        col = 0
        while col < len(line_text) and line_text[col].isspace():
            col += 1
        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.LINE,
        )

    def _motion_gg(self, state: Dict, count: int) -> MotionResult:
        """Move to file start or specific line."""
        if count > 1:
            line = count - 1
        else:
            line = 0

        return MotionResult(
            line=line,
            col=0,
            motion_type=MotionType.FILE,
            linewise=True,
        )

    def _motion_G(self, state: Dict, count: int) -> MotionResult:
        """Move to file end or specific line."""
        total_lines = state.get("total_lines", 1)

        if count > 1:
            line = count - 1
        else:
            line = total_lines - 1

        return MotionResult(
            line=line,
            col=0,
            motion_type=MotionType.FILE,
            linewise=True,
        )

    def _motion_percent(self, state: Dict, count: int) -> MotionResult:
        """Move to matching bracket."""
        line_text = state.get("line_text", "")
        col = state.get("col", 0)

        brackets = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{"}

        if col < len(line_text) and line_text[col] in brackets:
            # Find matching bracket
            target = brackets[line_text[col]]
            balance = 1

            # Search forward or backward
            if line_text[col] in "([{":
                search_col = col + 1
                direction = 1
            else:
                search_col = col - 1
                direction = -1

            while 0 <= search_col < len(line_text) and balance > 0:
                if line_text[search_col] == line_text[col]:
                    balance += 1
                elif line_text[search_col] == target:
                    balance -= 1
                search_col += direction

            return MotionResult(
                line=state.get("line", 0),
                col=search_col - direction,
                motion_type=MotionType.CHAR,
            )

        return MotionResult(
            line=state.get("line", 0),
            col=col,
            motion_type=MotionType.CHAR,
        )

    def _motion_f(self, state: Dict, count: int) -> MotionResult:
        """Find character forward."""
        # Needs character input
        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.SEARCH,
        )

    def _motion_F(self, state: Dict, count: int) -> MotionResult:
        """Find character backward."""
        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.SEARCH,
        )

    def _motion_t(self, state: Dict, count: int) -> MotionResult:
        """To character forward."""
        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.SEARCH,
        )

    def _motion_T(self, state: Dict, count: int) -> MotionResult:
        """To character backward."""
        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.SEARCH,
        )

    def _motion_mark(self, state: Dict, count: int) -> MotionResult:
        """Jump to mark line."""
        return MotionResult(
            line=state.get("line", 0),
            col=0,
            motion_type=MotionType.MARK,
            linewise=True,
        )

    def _motion_mark_exact(self, state: Dict, count: int) -> MotionResult:
        """Jump to mark exact position."""
        return MotionResult(
            line=state.get("line", 0),
            col=state.get("col", 0),
            motion_type=MotionType.MARK,
        )


__all__ = [
    "MotionType",
    "MotionResult",
    "VimMotions",
]
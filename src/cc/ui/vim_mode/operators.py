"""Vim Operators - Vim operator commands."""

from __future__ import annotations
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


@dataclass
class OperatorResult:
    """Operator result."""
    text: str = ""
    deleted: str = ""
    yanked: str = ""
    position: tuple = (0, 0)
    mode_change: str = ""


class VimOperators:
    """Vim operator implementations."""

    def __init__(self):
        self._operators: Dict[str, Callable] = {}
        self._registers: Dict[str, str] = {}
        self._load_operators()

    def _load_operators(self) -> None:
        """Load operator handlers."""
        self._operators = {
            "d": self._operator_delete,
            "y": self._operator_yank,
            "c": self._operator_change,
            "p": self._operator_put,
            "P": self._operator_put_before,
            "r": self._operator_replace,
            "R": self._operator_replace_mode,
            "x": self._operator_delete_char,
            "X": self._operator_delete_char_before,
            "J": self._operator_join,
            ">": self._operator_shift_right,
            "<": self._operator_shift_left,
            "gu": self._operator_lower,
            "gU": self._operator_upper,
        }

    def execute(
        self,
        operator: str,
        text: str,
        range: tuple,
        count: int = 1,
    ) -> OperatorResult:
        """Execute operator on text range."""
        handler = self._operators.get(operator)

        if handler:
            return handler(text, range, count)

        return OperatorResult(text=text)

    def _operator_delete(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Delete operator."""
        start, end = range

        deleted = text[start:end]
        remaining = text[:start] + text[end:]

        # Store in register
        self._registers[""] = deleted

        return OperatorResult(
            text=remaining,
            deleted=deleted,
            yanked=deleted,
            position=(start, 0),
            mode_change="normal",
        )

    def _operator_yank(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Yank operator."""
        start, end = range
        yanked = text[start:end]

        # Store in register
        self._registers[""] = yanked

        return OperatorResult(
            text=text,
            yanked=yanked,
            position=(start, 0),
        )

    def _operator_change(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Change operator."""
        start, end = range

        deleted = text[start:end]
        remaining = text[:start] + text[end:]

        # Store deleted in register
        self._registers[""] = deleted

        return OperatorResult(
            text=remaining,
            deleted=deleted,
            yanked=deleted,
            position=(start, 0),
            mode_change="insert",
        )

    def _operator_put(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Put operator (paste after)."""
        start, _ = range
        register = self._registers.get("", "")

        if register:
            repeated = register * count
            new_text = text[:start + 1] + repeated + text[start + 1:]
            return OperatorResult(
                text=new_text,
                position=(start + len(repeated), 0),
            )

        return OperatorResult(text=text)

    def _operator_put_before(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Put before operator."""
        start, _ = range
        register = self._registers.get("", "")

        if register:
            repeated = register * count
            new_text = text[:start] + repeated + text[start:]
            return OperatorResult(
                text=new_text,
                position=(start + len(repeated), 0),
            )

        return OperatorResult(text=text)

    def _operator_replace(
        self,
        text: str,
        range: tuple,
        count: int,
        char: str = None,
    ) -> OperatorResult:
        """Replace character operator."""
        start, _ = range

        if char:
            new_text = text[:start] + char + text[start + 1:]
            return OperatorResult(
                text=new_text,
                position=(start, 0),
            )

        return OperatorResult(text=text)

    def _operator_replace_mode(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Enter replace mode."""
        return OperatorResult(
            text=text,
            mode_change="replace",
        )

    def _operator_delete_char(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Delete character under cursor."""
        start, _ = range

        deleted = text[start:start + count]
        remaining = text[:start] + text[start + count:]

        self._registers[""] = deleted

        return OperatorResult(
            text=remaining,
            deleted=deleted,
            position=(start, 0),
        )

    def _operator_delete_char_before(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Delete character before cursor."""
        start, _ = range

        delete_start = max(0, start - count)
        deleted = text[delete_start:start]
        remaining = text[:delete_start] + text[start:]

        self._registers[""] = deleted

        return OperatorResult(
            text=remaining,
            deleted=deleted,
            position=(delete_start, 0),
        )

    def _operator_join(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Join lines operator."""
        start, _ = range

        lines = text.split("\n")
        if start < len(lines) - 1:
            # Join current and next line
            joined = lines[start] + " " + lines[start + 1].lstrip()
            new_lines = lines[:start] + [joined] + lines[start + 2:]
            new_text = "\n".join(new_lines)

            return OperatorResult(
                text=new_text,
                position=(start, len(lines[start])),
            )

        return OperatorResult(text=text)

    def _operator_shift_right(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Shift right (indent) operator."""
        start, end = range
        indent = "    "  # 4 spaces

        lines = text.split("\n")

        for i in range(start, min(end, len(lines))):
            lines[i] = indent + lines[i]

        new_text = "\n".join(lines)

        return OperatorResult(
            text=new_text,
            position=(start, 0),
        )

    def _operator_shift_left(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Shift left (unindent) operator."""
        start, end = range

        lines = text.split("\n")

        for i in range(start, min(end, len(lines))):
            if lines[i].startswith("    "):
                lines[i] = lines[i][4:]
            elif lines[i].startswith("\t"):
                lines[i] = lines[i][1:]

        new_text = "\n".join(lines)

        return OperatorResult(
            text=new_text,
            position=(start, 0),
        )

    def _operator_lower(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Make lowercase operator."""
        start, end = range

        new_text = text[:start] + text[start:end].lower() + text[end:]

        return OperatorResult(
            text=new_text,
            position=(start, 0),
        )

    def _operator_upper(
        self,
        text: str,
        range: tuple,
        count: int,
    ) -> OperatorResult:
        """Make uppercase operator."""
        start, end = range

        new_text = text[:start] + text[start:end].upper() + text[end:]

        return OperatorResult(
            text=new_text,
            position=(start, 0),
        )

    def get_register(self, name: str = "") -> str:
        """Get register content."""
        return self._registers.get(name, "")

    def set_register(self, name: str, content: str) -> None:
        """Set register content."""
        self._registers[name] = content


__all__ = [
    "OperatorResult",
    "VimOperators",
]
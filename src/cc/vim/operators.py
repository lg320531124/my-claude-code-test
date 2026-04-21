"""Vim Operators - Edit operators in vim mode.

Implements vim operators: d (delete), y (yank), c (change), p (put), etc.
"""

from __future__ import annotations
from typing import List, Dict, Callable
from dataclasses import dataclass
from . import VimState, VimMode, MotionResult, OperatorResult


@dataclass
class OperatorContext:
    """Context for operator execution."""
    lines: List[str]
    motion_result: MotionResult
    count: int
    register: str


class VimOperators:
    """Vim operator commands."""

    def __init__(self, state: VimState):
        self.state = state
        self.registers: Dict[str, str] = {}
        self.register_types: Dict[str, str] = {}  # 'linewise' or 'charwise'

    def execute_delete(self, ctx: OperatorContext) -> OperatorResult:
        """Delete operator (d)."""
        start_line, start_col = ctx.motion_result.start
        end_line, end_col = ctx.motion_result.end

        if ctx.motion_result.linewise:
            # Linewise delete
            text_lines = ctx.lines[start_line:end_line + 1]
            text = '\n'.join(text_lines)
            self.registers[ctx.register] = text
            self.register_types[ctx.register] = 'linewise'

            # Delete lines
            new_lines = ctx.lines[:start_line] + ctx.lines[end_line + 1:]

            # Cursor to start of deleted region or line above
            new_cursor_line = start_line
            if new_cursor_line >= len(new_lines):
                new_cursor_line = len(new_lines) - 1
            new_cursor_line = max(0, new_cursor_line)

            return OperatorResult(
                text=text,
                register=ctx.register,
                cursor_pos=(new_cursor_line, 0),
            )

        else:
            # Characterwise delete
            if start_line == end_line:
                # Single line
                text = ctx.lines[start_line][start_col:end_col + (0 if ctx.motion_result.exclusive else 1)]
                new_line = ctx.lines[start_line][:start_col] + ctx.lines[start_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]
                new_lines = ctx.lines.copy()
                new_lines[start_line] = new_line
            else:
                # Multi-line characterwise
                first_part = ctx.lines[start_line][:start_col]
                last_part = ctx.lines[end_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]

                text_parts = []
                text_parts.append(ctx.lines[start_line][start_col:])
                for l in range(start_line + 1, end_line):
                    text_parts.append(ctx.lines[l])
                text_parts.append(ctx.lines[end_line][:end_col + (0 if ctx.motion_result.exclusive else 1)])
                text = '\n'.join(text_parts)

                new_lines = ctx.lines[:start_line] + [first_part + last_part] + ctx.lines[end_line + 1:]

            self.registers[ctx.register] = text
            self.register_types[ctx.register] = 'charwise'

            return OperatorResult(
                text=text,
                register=ctx.register,
                cursor_pos=(start_line, start_col),
            )

    def execute_yank(self, ctx: OperatorContext) -> OperatorResult:
        """Yank operator (y)."""
        start_line, start_col = ctx.motion_result.start
        end_line, end_col = ctx.motion_result.end

        if ctx.motion_result.linewise:
            # Linewise yank
            text_lines = ctx.lines[start_line:end_line + 1]
            text = '\n'.join(text_lines)
            self.registers[ctx.register] = text
            self.register_types[ctx.register] = 'linewise'

            # Cursor doesn't move
            return OperatorResult(
                text=text,
                register=ctx.register,
                cursor_pos=(start_line, 0),
            )

        else:
            # Characterwise yank
            if start_line == end_line:
                text = ctx.lines[start_line][start_col:end_col + (0 if ctx.motion_result.exclusive else 1)]
            else:
                text_parts = []
                text_parts.append(ctx.lines[start_line][start_col:])
                for l in range(start_line + 1, end_line):
                    text_parts.append(ctx.lines[l])
                text_parts.append(ctx.lines[end_line][:end_col + (0 if ctx.motion_result.exclusive else 1)])
                text = '\n'.join(text_parts)

            self.registers[ctx.register] = text
            self.register_types[ctx.register] = 'charwise'

            # Cursor moves to start of yanked region
            return OperatorResult(
                text=text,
                register=ctx.register,
                cursor_pos=(start_line, start_col),
            )

    def execute_change(self, ctx: OperatorContext) -> OperatorResult:
        """Change operator (c)."""
        # First delete
        delete_result = self.execute_delete(ctx)

        # Then enter insert mode
        self.state.transition_to(VimMode.INSERT)

        return delete_result

    def execute_put_after(self, ctx: OperatorContext) -> OperatorResult:
        """Put after cursor (p)."""
        register = ctx.register
        text = self.registers.get(register, '')

        if not text:
            return OperatorResult(text='', register=register, cursor_pos=self.state.cursor_pos)

        line, col = self.state.cursor_pos

        if self.register_types.get(register) == 'linewise':
            # Put lines after current line
            new_lines = ctx.lines[:line + 1] + text.split('\n') + ctx.lines[line + 1:]
            new_cursor_line = line + 1
            return OperatorResult(
                text=text,
                register=register,
                cursor_pos=(new_cursor_line, 0),
            )

        else:
            # Put text after cursor
            new_line = ctx.lines[line][:col + 1] + text + ctx.lines[line][col + 1:]
            new_lines = ctx.lines.copy()
            new_lines[line] = new_line
            new_cursor_col = col + len(text)
            return OperatorResult(
                text=text,
                register=register,
                cursor_pos=(line, new_cursor_col),
            )

    def execute_put_before(self, ctx: OperatorContext) -> OperatorResult:
        """Put before cursor (P)."""
        register = ctx.register
        text = self.registers.get(register, '')

        if not text:
            return OperatorResult(text='', register=register, cursor_pos=self.state.cursor_pos)

        line, col = self.state.cursor_pos

        if self.register_types.get(register) == 'linewise':
            # Put lines before current line
            new_lines = ctx.lines[:line] + text.split('\n') + ctx.lines[line:]
            new_cursor_line = line
            return OperatorResult(
                text=text,
                register=register,
                cursor_pos=(new_cursor_line, 0),
            )

        else:
            # Put text before cursor
            new_line = ctx.lines[line][:col] + text + ctx.lines[line][col:]
            new_lines = ctx.lines.copy()
            new_lines[line] = new_line
            new_cursor_col = col + len(text) - 1
            return OperatorResult(
                text=text,
                register=register,
                cursor_pos=(line, new_cursor_col),
            )

    def execute_replace(self, ctx: OperatorContext, char: str) -> OperatorResult:
        """Replace character (r)."""
        line, col = self.state.cursor_pos

        if line >= len(ctx.lines) or col >= len(ctx.lines[line]):
            return OperatorResult(text='', register='', cursor_pos=(line, col))

        old_char = ctx.lines[line][col]
        new_line = ctx.lines[line][:col] + char + ctx.lines[line][col + 1:]
        new_lines = ctx.lines.copy()
        new_lines[line] = new_line

        return OperatorResult(
            text=old_char,
            register='',
            cursor_pos=(line, col),  # Stay at position
        )

    def execute_replace_mode(self, ctx: OperatorContext) -> OperatorResult:
        """Enter replace mode (R)."""
        self.state.transition_to(VimMode.REPLACE)
        return OperatorResult(text='', register='', cursor_pos=self.state.cursor_pos)

    def execute_x(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Delete character under cursor (x)."""
        line, col = self.state.cursor_pos

        if line >= len(ctx.lines):
            return OperatorResult(text='', register='', cursor_pos=(line, col))

        max_col = len(ctx.lines[line])
        end_col = min(col + count, max_col)

        text = ctx.lines[line][col:end_col]
        new_line = ctx.lines[line][:col] + ctx.lines[line][end_col:]
        new_lines = ctx.lines.copy()
        new_lines[line] = new_line

        self.registers[self.state.register] = text
        self.register_types[self.state.register] = 'charwise'

        new_cursor_col = col
        if new_cursor_col >= len(new_line) and len(new_line) > 0:
            new_cursor_col = len(new_line) - 1

        return OperatorResult(
            text=text,
            register=self.state.register,
            cursor_pos=(line, new_cursor_col),
        )

    def execute_X(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Delete character before cursor (X)."""
        line, col = self.state.cursor_pos

        if line >= len(ctx.lines) or col == 0:
            return OperatorResult(text='', register='', cursor_pos=(line, col))

        start_col = max(0, col - count)
        text = ctx.lines[line][start_col:col]
        new_line = ctx.lines[line][:start_col] + ctx.lines[line][col:]
        new_lines = ctx.lines.copy()
        new_lines[line] = new_line

        self.registers[self.state.register] = text
        self.register_types[self.state.register] = 'charwise'

        return OperatorResult(
            text=text,
            register=self.state.register,
            cursor_pos=(line, start_col),
        )

    def execute_J(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Join lines (J)."""
        line, col = self.state.cursor_pos

        if line >= len(ctx.lines) - 1:
            return OperatorResult(text='', register='', cursor_pos=(line, col))

        # Join current line with next
        current_line = ctx.lines[line]
        next_line = ctx.lines[line + 1]

        # Strip trailing whitespace from current, leading from next
        current_line = current_line.rstrip()
        next_line = next_line.lstrip()

        # Add space between unless current line ends with space or is empty
        join_col = len(current_line)
        if current_line and not current_line.endswith(' '):
            new_line = current_line + ' ' + next_line
            join_col += 1  # Space position
        else:
            new_line = current_line + next_line

        new_lines = ctx.lines[:line] + [new_line] + ctx.lines[line + 2:]

        return OperatorResult(
            text='\n',
            register='',
            cursor_pos=(line, join_col),
        )

    def execute_gJ(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Join lines without space (gJ)."""
        line, col = self.state.cursor_pos

        if line >= len(ctx.lines) - 1:
            return OperatorResult(text='', register='', cursor_pos=(line, col))

        current_line = ctx.lines[line].rstrip()
        next_line = ctx.lines[line + 1].lstrip()

        join_col = len(current_line)
        new_line = current_line + next_line

        new_lines = ctx.lines[:line] + [new_line] + ctx.lines[line + 2:]

        return OperatorResult(
            text='\n',
            register='',
            cursor_pos=(line, join_col),
        )

    def execute_greater(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Indent lines (>)."""
        start_line, _ = ctx.motion_result.start
        end_line, _ = ctx.motion_result.end

        indent = '    ' * count  # 4 spaces per indent level

        new_lines = ctx.lines.copy()
        for l in range(start_line, end_line + 1):
            if l < len(new_lines):
                new_lines[l] = indent + new_lines[l]

        return OperatorResult(
            text='',
            register='',
            cursor_pos=(start_line, 0),
        )

    def execute_less(self, ctx: OperatorContext, count: int = 1) -> OperatorResult:
        """Unindent lines (<)."""
        start_line, _ = ctx.motion_result.start
        end_line, _ = ctx.motion_result.end

        remove_spaces = 4 * count

        new_lines = ctx.lines.copy()
        for l in range(start_line, end_line + 1):
            if l < len(new_lines):
                # Remove leading spaces/tabs
                line_text = new_lines[l]
                removed = 0
                while removed < remove_spaces and line_text and (line_text[0] == ' ' or line_text[0] == '\t'):
                    line_text = line_text[1:]
                    removed += 1
                new_lines[l] = line_text

        return OperatorResult(
            text='',
            register='',
            cursor_pos=(start_line, 0),
        )

    def execute_gu(self, ctx: OperatorContext) -> OperatorResult:
        """Lowercase (gu)."""
        start_line, start_col = ctx.motion_result.start
        end_line, end_col = ctx.motion_result.end

        new_lines = ctx.lines.copy()

        if start_line == end_line:
            text = ctx.lines[start_line][start_col:end_col + (1 if not ctx.motion_result.exclusive else 0)]
            new_lines[start_line] = ctx.lines[start_line][:start_col] + text.lower() + ctx.lines[start_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]
        else:
            # Lowercase first line from start_col
            new_lines[start_line] = ctx.lines[start_line][:start_col] + ctx.lines[start_line][start_col:].lower()
            # Lowercase middle lines
            for l in range(start_line + 1, end_line):
                new_lines[l] = ctx.lines[l].lower()
            # Lowercase last line to end_col
            new_lines[end_line] = ctx.lines[end_line][:end_col + (1 if not ctx.motion_result.exclusive else 0)].lower() + ctx.lines[end_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]

        return OperatorResult(
            text='',
            register='',
            cursor_pos=(start_line, start_col),
        )

    def execute_gU(self, ctx: OperatorContext) -> OperatorResult:
        """Uppercase (gU)."""
        start_line, start_col = ctx.motion_result.start
        end_line, end_col = ctx.motion_result.end

        new_lines = ctx.lines.copy()

        if start_line == end_line:
            text = ctx.lines[start_line][start_col:end_col + (1 if not ctx.motion_result.exclusive else 0)]
            new_lines[start_line] = ctx.lines[start_line][:start_col] + text.upper() + ctx.lines[start_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]
        else:
            # Uppercase first line from start_col
            new_lines[start_line] = ctx.lines[start_line][:start_col] + ctx.lines[start_line][start_col:].upper()
            # Uppercase middle lines
            for l in range(start_line + 1, end_line):
                new_lines[l] = ctx.lines[l].upper()
            # Uppercase last line to end_col
            new_lines[end_line] = ctx.lines[end_line][:end_col + (1 if not ctx.motion_result.exclusive else 0)].upper() + ctx.lines[end_line][end_col + (1 if not ctx.motion_result.exclusive else 0):]

        return OperatorResult(
            text='',
            register='',
            cursor_pos=(start_line, start_col),
        )


# Operator registry
OPERATOR_REGISTRY: Dict[str, Callable] = {
    'd': VimOperators.execute_delete,
    'y': VimOperators.execute_yank,
    'c': VimOperators.execute_change,
    'p': VimOperators.execute_put_after,
    'P': VimOperators.execute_put_before,
    'r': VimOperators.execute_replace,  # Needs char param
    'R': VimOperators.execute_replace_mode,
    'x': VimOperators.execute_x,  # Needs count param
    'X': VimOperators.execute_X,  # Needs count param
    'J': VimOperators.execute_J,
    'gJ': VimOperators.execute_gJ,
    '>': VimOperators.execute_greater,
    '<': VimOperators.execute_less,
    'gu': VimOperators.execute_gu,
    'gU': VimOperators.execute_gU,
}


__all__ = [
    "VimOperators",
    "OperatorContext",
    "OPERATOR_REGISTRY",
]
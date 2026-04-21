"""Vim Transitions - State transitions between vim modes.

Handles transitions between NORMAL, INSERT, VISUAL, COMMAND, REPLACE modes.
"""

from __future__ import annotations
from typing import Dict, Callable, Tuple, Optional, List
from dataclasses import dataclass
from . import VimState, VimMode, VimMotions, VimOperators, VimTextObjects, MotionResult


@dataclass
class TransitionResult:
    """Result of a mode transition."""
    new_mode: VimMode
    cursor_pos: Tuple[int, int]
    message: Optional[str] = None
    action: Optional[str] = None  # 'insert', 'delete', 'yank', etc.


class VimTransitions:
    """Vim mode transitions."""

    def __init__(self, state: VimState):
        self.state = state
        self.motions = VimMotions(state)
        self.operators = VimOperators(state)
        self.text_objects = VimTextObjects()

        # Mode-specific key handlers
        self.normal_handlers: Dict[str, Callable] = {}
        self.insert_handlers: Dict[str, Callable] = {}
        self.visual_handlers: Dict[str, Callable] = {}
        self.command_handlers: Dict[str, Callable] = {}
        self.replace_handlers: Dict[str, Callable] = {}

        self._setup_handlers()

    def _setup_handlers(self) -> None:
        """Setup mode-specific key handlers."""
        # Normal mode transitions
        self.normal_handlers['i'] = self._transition_insert
        self.normal_handlers['I'] = self._transition_insert_line_start
        self.normal_handlers['a'] = self._transition_insert_after
        self.normal_handlers['A'] = self._transition_insert_line_end
        self.normal_handlers['o'] = self._transition_insert_new_line_below
        self.normal_handlers['O'] = self._transition_insert_new_line_above
        self.normal_handlers['v'] = self._transition_visual
        self.normal_handlers['V'] = self._transition_visual_line
        self.normal_handlers['ctrl_v'] = self._transition_visual_block
        self.normal_handlers[':'] = self._transition_command
        self.normal_handlers['R'] = self._transition_replace

        # Back to normal from other modes
        self.insert_handlers['escape'] = self._back_to_normal
        self.visual_handlers['escape'] = self._back_to_normal
        self.command_handlers['escape'] = self._back_to_normal
        self.replace_handlers['escape'] = self._back_to_normal

        # Visual mode operations
        self.visual_handlers['o'] = self._visual_move_other_end

        # Command mode actions
        self.command_handlers['enter'] = self._execute_command
        self.command_handlers['backspace'] = self._command_backspace

    # Normal mode transitions
    def _transition_insert(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode at cursor (i)."""
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=self.state.cursor_pos,
            action='insert',
        )

    def _transition_insert_line_start(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode at line start (I)."""
        line, _ = self.state.cursor_pos
        # Move to first non-blank character
        col = 0
        if line < len(lines):
            while col < len(lines[line]) and lines[line][col].isspace():
                col += 1
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=(line, col),
            action='insert',
        )

    def _transition_insert_after(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode after cursor (a)."""
        line, col = self.state.cursor_pos
        if line < len(lines) and col < len(lines[line]):
            col += 1
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=(line, col),
            action='insert',
        )

    def _transition_insert_line_end(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode at line end (A)."""
        line, col = self.state.cursor_pos
        if line < len(lines):
            col = len(lines[line])
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=(line, col),
            action='insert',
        )

    def _transition_insert_new_line_below(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode on new line below (o)."""
        line, _ = self.state.cursor_pos
        new_line = line + 1
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=(new_line, 0),
            action='insert_newline_below',
        )

    def _transition_insert_new_line_above(self, lines: List[str]) -> TransitionResult:
        """Enter insert mode on new line above (O)."""
        line, _ = self.state.cursor_pos
        return TransitionResult(
            new_mode=VimMode.INSERT,
            cursor_pos=(line, 0),
            action='insert_newline_above',
        )

    def _transition_visual(self, lines: List[str]) -> TransitionResult:
        """Enter visual character mode (v)."""
        return TransitionResult(
            new_mode=VimMode.VISUAL,
            cursor_pos=self.state.cursor_pos,
            message='-- VISUAL --',
        )

    def _transition_visual_line(self, lines: List[str]) -> TransitionResult:
        """Enter visual line mode (V)."""
        return TransitionResult(
            new_mode=VimMode.VISUAL_LINE,
            cursor_pos=self.state.cursor_pos,
            message='-- VISUAL LINE --',
        )

    def _transition_visual_block(self, lines: List[str]) -> TransitionResult:
        """Enter visual block mode (Ctrl-V)."""
        return TransitionResult(
            new_mode=VimMode.VISUAL_BLOCK,
            cursor_pos=self.state.cursor_pos,
            message='-- VISUAL BLOCK --',
        )

    def _transition_command(self, lines: List[str]) -> TransitionResult:
        """Enter command mode (:)."""
        return TransitionResult(
            new_mode=VimMode.COMMAND,
            cursor_pos=self.state.cursor_pos,
            message=':',
            action='command_input',
        )

    def _transition_replace(self, lines: List[str]) -> TransitionResult:
        """Enter replace mode (R)."""
        return TransitionResult(
            new_mode=VimMode.REPLACE,
            cursor_pos=self.state.cursor_pos,
            message='-- REPLACE --',
            action='replace',
        )

    # Back to normal
    def _back_to_normal(self, lines: List[str]) -> TransitionResult:
        """Exit to normal mode (Escape)."""
        if self.state.mode == VimMode.INSERT:
            # Move cursor back one position
            line, col = self.state.cursor_pos
            if col > 0:
                col -= 1
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=(line, col),
            )

        elif self.state.mode in (VimMode.VISUAL, VimMode.VISUAL_LINE, VimMode.VISUAL_BLOCK):
            # Clear visual selection
            self.state.visual_start = None
            self.state.visual_end = None
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
            )

        elif self.state.mode == VimMode.COMMAND:
            # Cancel command
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
            )

        elif self.state.mode == VimMode.REPLACE:
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
            )

        return TransitionResult(
            new_mode=VimMode.NORMAL,
            cursor_pos=self.state.cursor_pos,
        )

    # Visual mode operations
    def _visual_move_other_end(self, lines: List[str]) -> TransitionResult:
        """Move to other end of visual selection (o)."""
        if self.state.visual_start and self.state.visual_end:
            # Swap start and end
            if self.state.cursor_pos == self.state.visual_start:
                new_pos = self.state.visual_end
                self.state.visual_start, self.state.visual_end = self.state.visual_end, self.state.visual_start
            else:
                new_pos = self.state.visual_start
                self.state.visual_start, self.state.visual_end = self.state.visual_start, self.state.visual_start

            return TransitionResult(
                new_mode=self.state.mode,
                cursor_pos=new_pos,
            )

        return TransitionResult(
            new_mode=self.state.mode,
            cursor_pos=self.state.cursor_pos,
        )

    # Command mode
    def _execute_command(self, command: str, lines: List[str]) -> TransitionResult:
        """Execute command (:command)."""
        command = command.strip()

        if not command:
            return self._back_to_normal(lines)

        # Built-in commands
        if command == 'q':
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='quit',
            )

        elif command == 'q!':
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='quit_force',
            )

        elif command == 'w':
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='save',
            )

        elif command == 'wq' or command == 'x':
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='save_quit',
            )

        elif command.startswith('e '):
            # Edit file
            filename = command[2:].strip()
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=(0, 0),
                action='edit_file',
                message=filename,
            )

        elif command.isdigit():
            # Go to line number
            line_num = int(command) - 1
            line_num = max(0, min(line_num, len(lines) - 1))
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=(line_num, 0),
            )

        elif command == '$':
            # Go to last line
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=(len(lines) - 1, 0),
            )

        elif command.startswith('/'):
            # Search
            pattern = command[1:]
            result = self.motions.motion_slash(lines, pattern)
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=result.end,
            )

        elif command.startswith('?'):
            # Search backward
            pattern = command[1:]
            result = self.motions.motion_question(lines, pattern)
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=result.end,
            )

        elif command.startswith('s/'):
            # Substitute
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='substitute',
                message=command,
            )

        elif command == 'noh':
            # No highlight
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='no_highlight',
            )

        elif command.startswith('!'):
            # Shell command
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                action='shell',
                message=command[1:],
            )

        else:
            return TransitionResult(
                new_mode=VimMode.NORMAL,
                cursor_pos=self.state.cursor_pos,
                message=f"Unknown command: {command}",
            )

    def _command_backspace(self, command_buffer: str, lines: List[str]) -> TransitionResult:
        """Handle backspace in command mode."""
        if not command_buffer:
            return self._back_to_normal(lines)

        new_buffer = command_buffer[:-1]
        return TransitionResult(
            new_mode=VimMode.COMMAND,
            cursor_pos=self.state.cursor_pos,
            message=':' + new_buffer,
        )

    # Process key input
    def process_key(self, key: str, lines: List[str], command_buffer: str = '') -> TransitionResult:
        """Process a key input in current mode."""
        mode = self.state.mode

        if mode == VimMode.NORMAL:
            handler = self.normal_handlers.get(key)
            if handler:
                return handler(lines)

            # Check for motion
            if key in self.motions.MOTION_REGISTRY:
                motion_func = self.motions.MOTION_REGISTRY[key]
                result = motion_func(self.motions, lines, self.state.get_count())
                return TransitionResult(
                    new_mode=VimMode.NORMAL,
                    cursor_pos=result.end,
                )

            # Check for operator
            if key in self.operators.OPERATOR_REGISTRY:
                self.state.pending_operator = key
                return TransitionResult(
                    new_mode=VimMode.NORMAL,
                    cursor_pos=self.state.cursor_pos,
                )

            # Count
            if key.isdigit() and key != '0':
                self.state.pending_count = self.state.pending_count * 10 + int(key)
                return TransitionResult(
                    new_mode=VimMode.NORMAL,
                    cursor_pos=self.state.cursor_pos,
                )

        elif mode == VimMode.INSERT:
            # Insert character
            return TransitionResult(
                new_mode=VimMode.INSERT,
                cursor_pos=self.state.cursor_pos,
                action='insert_char',
                message=key,
            )

        elif mode == VimMode.VISUAL:
            handler = self.visual_handlers.get(key)
            if handler:
                return handler(lines)

            # Motion in visual mode
            if key in self.motions.MOTION_REGISTRY:
                motion_func = self.motions.MOTION_REGISTRY[key]
                result = motion_func(self.motions, lines, self.state.get_count())
                self.state.visual_end = result.end
                return TransitionResult(
                    new_mode=VimMode.VISUAL,
                    cursor_pos=result.end,
                )

            # Operator in visual mode - operates on selection
            if key in self.operators.OPERATOR_REGISTRY:
                # Create motion result from visual selection
                visual_result = MotionResult(
                    start=self.state.visual_start or self.state.cursor_pos,
                    end=self.state.visual_end or self.state.cursor_pos,
                    linewise=(self.state.mode == VimMode.VISUAL_LINE),
                )

                operator_func = self.operators.OPERATOR_REGISTRY[key]
                # Execute operator
                return TransitionResult(
                    new_mode=VimMode.NORMAL,
                    cursor_pos=self.state.cursor_pos,
                    action=key,
                )

        elif mode == VimMode.COMMAND:
            handler = self.command_handlers.get(key)
            if handler:
                if key == 'enter':
                    return self._execute_command(command_buffer, lines)
                elif key == 'backspace':
                    return self._command_backspace(command_buffer, lines)
                elif key == 'escape':
                    return handler(lines)

            # Add character to command buffer
            return TransitionResult(
                new_mode=VimMode.COMMAND,
                cursor_pos=self.state.cursor_pos,
                message=':' + command_buffer + key,
            )

        elif mode == VimMode.REPLACE:
            handler = self.replace_handlers.get(key)
            if handler:
                return handler(lines)

            # Replace character
            return TransitionResult(
                new_mode=VimMode.REPLACE,
                cursor_pos=self.state.cursor_pos,
                action='replace_char',
                message=key,
            )

        return TransitionResult(
            new_mode=mode,
            cursor_pos=self.state.cursor_pos,
        )


__all__ = [
    "VimTransitions",
    "TransitionResult",
]
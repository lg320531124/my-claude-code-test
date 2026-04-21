"""Vim Motions - Movement commands in vim mode.

Implements vim motion commands: h, j, k, l, w, b, e, 0, $, gg, G, etc.
"""

from __future__ import annotations
import re
from typing import List, Dict, Callable, Optional
from . import VimState, MotionResult


class VimMotions:
    """Vim motion commands."""

    def __init__(self, state: VimState):
        self.state = state

    # Character motions
    def motion_h(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move left (h)."""
        line, col = self.state.cursor_pos
        new_col = max(0, col - count)
        return MotionResult(
            start=(line, col),
            end=(line, new_col),
            exclusive=True,
        )

    def motion_l(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move right (l)."""
        line, col = self.state.cursor_pos
        max_col = len(lines[line]) if line < len(lines) else 0
        new_col = min(max_col, col + count)
        return MotionResult(
            start=(line, col),
            end=(line, new_col),
            exclusive=True,
        )

    def motion_j(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move down (j)."""
        line, col = self.state.cursor_pos
        new_line = min(len(lines) - 1, line + count)
        # Clamp column to new line length
        max_col = len(lines[new_line]) if new_line < len(lines) else 0
        new_col = min(col, max_col)
        return MotionResult(
            start=(line, col),
            end=(new_line, new_col),
            linewise=True,
        )

    def motion_k(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move up (k)."""
        line, col = self.state.cursor_pos
        new_line = max(0, line - count)
        # Clamp column to new line length
        max_col = len(lines[new_line]) if new_line < len(lines) else 0
        new_col = min(col, max_col)
        return MotionResult(
            start=(line, col),
            end=(new_line, new_col),
            linewise=True,
        )

    # Word motions
    def motion_w(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to next word start (w)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            # Skip current word
            while line < len(lines) and col < len(lines[line]):
                char = lines[line][col]
                if char.isspace():
                    break
                col += 1

            # Skip whitespace
            while line < len(lines):
                while col < len(lines[line]) and lines[line][col].isspace():
                    col += 1
                if col < len(lines[line]):
                    break
                line += 1
                col = 0

        if line >= len(lines):
            line = len(lines) - 1
            col = len(lines[line]) if line >= 0 else 0

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_b(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to previous word start (b)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            # If at start of word, go to previous word
            if col == 0:
                if line > 0:
                    line -= 1
                    col = len(lines[line]) if line < len(lines) else 0

            # Skip whitespace backwards
            while line >= 0:
                while col > 0 and lines[line][col - 1].isspace():
                    col -= 1
                if col > 0:
                    break
                if line > 0:
                    line -= 1
                    col = len(lines[line]) if line < len(lines) else 0
                else:
                    break

            # Move to start of word
            while col > 0 and not lines[line][col - 1].isspace():
                col -= 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_e(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to word end (e)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            # Move one position forward first (if not at end)
            if line < len(lines) and col < len(lines[line]):
                col += 1

            # Skip whitespace
            while line < len(lines):
                while col < len(lines[line]) and lines[line][col].isspace():
                    col += 1
                if col < len(lines[line]):
                    break
                line += 1
                col = 0

            # Move to end of word
            while line < len(lines) and col < len(lines[line]) - 1:
                if lines[line][col + 1].isspace():
                    break
                col += 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=False,  # e is inclusive
        )

    def motion_W(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to next WORD start (W - space-delimited)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            # Skip to next space
            while line < len(lines) and col < len(lines[line]):
                if lines[line][col].isspace():
                    break
                col += 1

            # Skip whitespace
            while line < len(lines):
                while col < len(lines[line]) and lines[line][col].isspace():
                    col += 1
                if col < len(lines[line]):
                    break
                line += 1
                col = 0

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_B(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to previous WORD start (B - space-delimited)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            # Move backwards past space
            if col == 0 and line > 0:
                line -= 1
                col = len(lines[line])

            # Skip whitespace backwards
            while col > 0 and lines[line][col - 1].isspace():
                col -= 1

            # Move to start of WORD
            while col > 0 and not lines[line][col - 1].isspace():
                col -= 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_E(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to WORD end (E - space-delimited)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            if col < len(lines[line]):
                col += 1

            # Skip whitespace
            while col < len(lines[line]) and lines[line][col].isspace():
                col += 1

            # Move to end of WORD
            while col < len(lines[line]) - 1 and not lines[line][col + 1].isspace():
                col += 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=False,
        )

    # Line motions
    def motion_0(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to line start (0)."""
        line, col = self.state.cursor_pos
        return MotionResult(
            start=(line, col),
            end=(line, 0),
            exclusive=True,
        )

    def motion_dollar(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to line end ($)."""
        line, col = self.state.cursor_pos
        max_col = len(lines[line]) if line < len(lines) else 0
        new_col = max(0, max_col - 1)  # $ lands on last char, not after
        return MotionResult(
            start=(line, col),
            end=(line, new_col),
            exclusive=False,
        )

    def motion_gg(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to first line (gg) or specific line."""
        target_line = count - 1 if count > 1 else 0
        target_line = min(target_line, len(lines) - 1)
        return MotionResult(
            start=self.state.cursor_pos,
            end=(target_line, 0),
            linewise=True,
        )

    def motion_G(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to last line (G) or specific line."""
        if count > 1:
            target_line = min(count - 1, len(lines) - 1)
        else:
            target_line = len(lines) - 1
        return MotionResult(
            start=self.state.cursor_pos,
            end=(target_line, 0),
            linewise=True,
        )

    def motion_percent(self, lines: List[str], count: int = 1) -> MotionResult:
        """Move to matching bracket (%)."""
        line, col = self.state.cursor_pos
        if line >= len(lines) or col >= len(lines[line]):
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        char = lines[line][col]
        matching = {
            '(':')', ')':'(',
            '[':']', ']':'[',
            '{':'}', '}':'{',
        }

        if char not in matching:
            # Search forward for bracket
            for c in range(col, len(lines[line])):
                if lines[line][c] in matching:
                    col = c
                    char = lines[line][c]
                    break
            else:
                return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        # Find matching bracket
        target = matching[char]
        depth = 1
        direction = 1 if char in '([{ ' else -1
        curr_line, curr_col = line, col

        while depth > 0:
            curr_col += direction
            if curr_col < 0:
                curr_line -= 1
                if curr_line < 0:
                    break
                curr_col = len(lines[curr_line]) - 1
            elif curr_col >= len(lines[curr_line]):
                curr_line += 1
                if curr_line >= len(lines):
                    break
                curr_col = 0

            if curr_line < len(lines) and curr_col < len(lines[curr_line]):
                c = lines[curr_line][curr_col]
                if c == char:
                    depth += 1
                elif c == target:
                    depth -= 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(curr_line, curr_col),
            exclusive=False,
        )

    # Search motions
    def motion_f(self, lines: List[str], char: str, count: int = 1) -> MotionResult:
        """Find character forward on line (f)."""
        line, col = self.state.cursor_pos
        if line >= len(lines):
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        for _ in range(count):
            for c in range(col + 1, len(lines[line])):
                if lines[line][c] == char:
                    col = c
                    break
            else:
                break  # Not found

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=False,  # f is inclusive
        )

    def motion_F(self, lines: List[str], char: str, count: int = 1) -> MotionResult:
        """Find character backward on line (F)."""
        line, col = self.state.cursor_pos

        for _ in range(count):
            for c in range(col - 1, -1, -1):
                if lines[line][c] == char:
                    col = c
                    break
            else:
                break  # Not found

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=False,
        )

    def motion_t(self, lines: List[str], char: str, count: int = 1) -> MotionResult:
        """Till character forward on line (t)."""
        result = self.motion_f(lines, char, count)
        if result.end[1] > result.start[1]:
            # Move back one position
            return MotionResult(
                start=result.start,
                end=(result.end[0], result.end[1] - 1),
                exclusive=True,
            )
        return result

    def motion_T(self, lines: List[str], char: str, count: int = 1) -> MotionResult:
        """Till character backward on line (T)."""
        result = self.motion_F(lines, char, count)
        if result.end[1] < result.start[1]:
            # Move forward one position
            return MotionResult(
                start=result.start,
                end=(result.end[0], result.end[1] + 1),
                exclusive=True,
            )
        return result

    def motion_slash(self, lines: List[str], pattern: str, count: int = 1) -> MotionResult:
        """Search forward (/)."""
        import re
        line, col = self.state.cursor_pos

        for _ in range(count):
            found = False
            # Search from current position forward
            for l in range(line, len(lines)):
                start_col = col + 1 if l == line else 0
                match = re.search(pattern, lines[l][start_col:])
                if match:
                    line = l
                    col = start_col + match.start()
                    found = True
                    break
            if not found:
                # Wrap around
                for l in range(0, line + 1):
                    start_col = 0 if l < line else 0
                    end_col = col if l == line else len(lines[l])
                    match = re.search(pattern, lines[l][start_col:end_col])
                    if match:
                        line = l
                        col = start_col + match.start()
                        break

        self.state.last_search = pattern
        self.state.last_search_direction = 1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_n(self, lines: List[str], count: int = 1) -> MotionResult:
        """Repeat last search (n)."""
        if not self.state.last_search:
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        if self.state.last_search_direction == 1:
            return self.motion_slash(lines, self.state.last_search, count)
        else:
            return self.motion_question(lines, self.state.last_search, count)

    def motion_question(self, lines: List[str], pattern: str, count: int = 1) -> MotionResult:
        """Search backward (?)."""
        import re
        line, col = self.state.cursor_pos

        for _ in range(count):
            found = False
            # Search from current position backward
            for l in range(line, -1, -1):
                start_col = 0
                end_col = col if l == line else len(lines[l])
                # Find all matches and take last one
                matches = list(re.finditer(pattern, lines[l][start_col:end_col]))
                if matches:
                    line = l
                    col = start_col + matches[-1].start()
                    found = True
                    break
            if not found:
                # Wrap around
                for l in range(len(lines) - 1, line):
                    matches = list(re.finditer(pattern, lines[l]))
                    if matches:
                        line = l
                        col = matches[-1].start()
                        break

        self.state.last_search = pattern
        self.state.last_search_direction = -1

        return MotionResult(
            start=self.state.cursor_pos,
            end=(line, col),
            exclusive=True,
        )

    def motion_N(self, lines: List[str], count: int = 1) -> MotionResult:
        """Repeat last search in opposite direction (N)."""
        if not self.state.last_search:
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        # Flip direction
        if self.state.last_search_direction == 1:
            return self.motion_question(lines, self.state.last_search, count)
        else:
            return self.motion_slash(lines, self.state.last_search, count)

    # Special motions
    def motion_star(self, lines: List[str], count: int = 1) -> MotionResult:
        """Search for word under cursor forward (*)."""
        line, col = self.state.cursor_pos
        if line >= len(lines) or col >= len(lines[line]):
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        # Extract word at cursor
        word_start = col
        while word_start > 0 and not lines[line][word_start - 1].isspace():
            word_start -= 1
        word_end = col
        while word_end < len(lines[line]) and not lines[line][word_end].isspace():
            word_end += 1

        word = lines[line][word_start:word_end]
        pattern = r'\b' + re.escape(word) + r'\b'

        return self.motion_slash(lines, pattern, count)

    def motion_hash(self, lines: List[str], count: int = 1) -> MotionResult:
        """Search for word under cursor backward (#)."""
        line, col = self.state.cursor_pos
        if line >= len(lines) or col >= len(lines[line]):
            return MotionResult(start=self.state.cursor_pos, end=self.state.cursor_pos)

        # Extract word at cursor
        word_start = col
        while word_start > 0 and not lines[line][word_start - 1].isspace():
            word_start -= 1
        word_end = col
        while word_end < len(lines[line]) and not lines[line][word_end].isspace():
            word_end += 1

        word = lines[line][word_start:word_end]
        import re
        pattern = r'\b' + re.escape(word) + r'\b'

        return self.motion_question(lines, pattern, count)


# Motion registry
MOTION_REGISTRY: Dict[str, Callable] = {
    'h': VimMotions.motion_h,
    'j': VimMotions.motion_j,
    'k': VimMotions.motion_k,
    'l': VimMotions.motion_l,
    'w': VimMotions.motion_w,
    'b': VimMotions.motion_b,
    'e': VimMotions.motion_e,
    'W': VimMotions.motion_W,
    'B': VimMotions.motion_B,
    'E': VimMotions.motion_E,
    '0': VimMotions.motion_0,
    '$': VimMotions.motion_dollar,
    'gg': VimMotions.motion_gg,
    'G': VimMotions.motion_G,
    '%': VimMotions.motion_percent,
    'n': VimMotions.motion_n,
    'N': VimMotions.motion_N,
    '*': VimMotions.motion_star,
    '#': VimMotions.motion_hash,
}


__all__ = [
    "VimMotions",
    "MOTION_REGISTRY",
]
"""Vim Text Objects - Text object selections in vim mode.

Implements vim text objects: aw, iw, ap, ip, a(, i(, a[, i[, a{, i{, at, it, etc.
"""

from __future__ import annotations
import re
from typing import List, Tuple
from . import MotionResult


class VimTextObjects:
    """Vim text object selections."""

    # Word boundaries
    WORD_BOUNDARIES = {' ', '\t', '\n', '(', ')', '[', ']', '{', '}', '<', '>', '"', "'", '`', ',', '.', ';', ':', '!', '?', '/', '\\', '|', '@', '#', '$', '%', '^', '&', '*', '+', '-', '=', '~'}

    def __init__(self):
        pass

    def get_word_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get word text object (aw/iw)."""
        line, col = cursor_pos
        if line >= len(lines) or col >= len(lines[line]):
            return MotionResult(start=cursor_pos, end=cursor_pos)

        text = lines[line]

        # Find word boundaries
        # If cursor on whitespace, move to next word
        if col < len(text) and text[col].isspace():
            while col < len(text) and text[col].isspace():
                col += 1
            if col >= len(text):
                return MotionResult(start=cursor_pos, end=cursor_pos)

        # Find word start
        word_start = col
        while word_start > 0 and not self._is_word_boundary(text[word_start - 1]):
            word_start -= 1

        # Find word end
        word_end = col
        while word_end < len(text) and not self._is_word_boundary(text[word_end]):
            word_end += 1

        if around:
            # Include surrounding whitespace
            # Before
            start = word_start
            while start > 0 and text[start - 1].isspace():
                start -= 1

            # After
            end = word_end
            while end < len(text) and text[end].isspace():
                end += 1

            return MotionResult(
                start=(line, start),
                end=(line, end - 1),  # Exclusive for selection
                exclusive=False,
                linewise=False,
            )

        else:
            # Just the word
            return MotionResult(
                start=(line, word_start),
                end=(line, word_end - 1),
                exclusive=False,
                linewise=False,
            )

    def get_WORD_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get WORD text object (aW/iW - space delimited)."""
        line, col = cursor_pos
        if line >= len(lines) or col >= len(lines[line]):
            return MotionResult(start=cursor_pos, end=cursor_pos)

        text = lines[line]

        # If on whitespace, move to next WORD
        if col < len(text) and text[col].isspace():
            while col < len(text) and text[col].isspace():
                col += 1
            if col >= len(text):
                return MotionResult(start=cursor_pos, end=cursor_pos)

        # Find WORD start (only space delimiter)
        word_start = col
        while word_start > 0 and not text[word_start - 1].isspace():
            word_start -= 1

        # Find WORD end
        word_end = col
        while word_end < len(text) and not text[word_end].isspace():
            word_end += 1

        if around:
            # Include surrounding whitespace
            start = word_start
            while start > 0 and text[start - 1].isspace():
                start -= 1

            end = word_end
            while end < len(text) and text[end].isspace():
                end += 1

            return MotionResult(
                start=(line, start),
                end=(line, end - 1),
                exclusive=False,
            )

        else:
            return MotionResult(
                start=(line, word_start),
                end=(line, word_end - 1),
                exclusive=False,
            )

    def get_paragraph_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get paragraph text object (ap/ip)."""
        line, col = cursor_pos

        # Find paragraph boundaries (blank lines)
        # Paragraph is defined as non-blank lines separated by blank lines

        # If on blank line, find next non-blank paragraph
        if line < len(lines) and not lines[line].strip():
            # Move down to find paragraph start
            while line < len(lines) and not lines[line].strip():
                line += 1
            if line >= len(lines):
                return MotionResult(start=cursor_pos, end=cursor_pos)

        # Find paragraph start
        para_start = line
        while para_start > 0 and lines[para_start - 1].strip():
            para_start -= 1

        # Find paragraph end
        para_end = line
        while para_end < len(lines) - 1 and lines[para_end + 1].strip():
            para_end += 1

        if around:
            # Include trailing blank line
            end = para_end + 1
            if end < len(lines) and not lines[end].strip():
                end += 1

            # Include leading blank line if exists
            start = para_start
            if start > 0 and not lines[start - 1].strip():
                start -= 1

            return MotionResult(
                start=(start, 0),
                end=(end, 0),
                linewise=True,
            )

        else:
            return MotionResult(
                start=(para_start, 0),
                end=(para_end, len(lines[para_end]) if para_end < len(lines) else 0),
                linewise=True,
            )

    def get_sentence_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get sentence text object (as/is)."""
        line, col = cursor_pos

        # Sentence ends with .!? followed by space, tab, or newline
        # This is a simplified implementation

        # Find current sentence
        all_text = '\n'.join(lines)

        # Convert cursor position to text position
        text_pos = sum(len(lines[l]) + 1 for l in range(line)) + col

        # Find sentence boundaries
        # Sentence start: after .!? + space/tab/newline, or start of text
        sentence_end_chars = {'.', '!', '?'}

        # Find sentence start
        start = text_pos
        while start > 0:
            if all_text[start - 1] in sentence_end_chars:
                if start < len(all_text) and all_text[start] in ' \t\n':
                    break
            start -= 1

        # Adjust for whitespace
        while start < len(all_text) and all_text[start] in ' \t\n':
            start += 1

        # Find sentence end
        end = text_pos
        while end < len(all_text):
            if all_text[end] in sentence_end_chars:
                if end + 1 < len(all_text) and all_text[end + 1] in ' \t\n':
                    end += 1
                    break
            end += 1

        # Convert back to line/col
        start_line, start_col = self._text_pos_to_line_col(lines, start)
        end_line, end_col = self._text_pos_to_line_col(lines, end)

        return MotionResult(
            start=(start_line, start_col),
            end=(end_line, end_col),
            linewise=False,
            exclusive=False,
        )

    def get_block_object(self, lines: List[str], cursor_pos: Tuple[int, int], open_char: str, close_char: str, around: bool = False) -> MotionResult:
        """Get block text object (a(, i(, a{, i{, a[, i[, a<, i<)."""
        line, col = cursor_pos

        matching = {
            '(':'(', ')':'(',
            '{':'{', '}':'{',
            '[':'[', ']':'[',
            '<':'<', '>':'<',
        }

        # Find opening character
        # If on the character itself
        if line < len(lines) and col < len(lines[line]):
            char = lines[line][col]
            if char == open_char or char == matching.get(open_char, open_char):
                # Already on it
                pass
            else:
                # Search forward
                found = False
                for c in range(col + 1, len(lines[line])):
                    if lines[line][c] == open_char:
                        col = c
                        found = True
                        break
                if not found:
                    # Search backward
                    for c in range(col - 1, -1, -1):
                        if lines[line][c] == open_char:
                            col = c
                            break

        # Find matching closing character
        close_char_match = {'(':')', '{':'}', '[':']', '<':'>'}.get(open_char, close_char)

        depth = 0
        start_line, start_col = line, col
        curr_line, curr_col = line, col + 1

        while curr_line < len(lines):
            while curr_col < len(lines[curr_line]):
                c = lines[curr_line][curr_col]
                if c == open_char:
                    depth += 1
                elif c == close_char_match:
                    if depth == 0:
                        # Found matching close
                        if around:
                            return MotionResult(
                                start=(start_line, start_col),
                                end=(curr_line, curr_col),
                                linewise=False,
                            )
                        else:
                            # Inside block
                            inner_start_col = start_col + 1
                            inner_end_col = curr_col - 1

                            if curr_line == start_line:
                                return MotionResult(
                                    start=(start_line, inner_start_col),
                                    end=(curr_line, inner_end_col),
                                    linewise=False,
                                )
                            else:
                                return MotionResult(
                                    start=(start_line, inner_start_col),
                                    end=(curr_line, inner_end_col),
                                    linewise=False,
                                )
                    depth -= 1
                curr_col += 1
            curr_line += 1
            curr_col = 0

        return MotionResult(start=cursor_pos, end=cursor_pos)

    def get_quote_object(self, lines: List[str], cursor_pos: Tuple[int, int], quote_char: str, around: bool = False) -> MotionResult:
        """Get quote text object (a", i", a', i', a`, i`)."""
        line, col = cursor_pos
        if line >= len(lines):
            return MotionResult(start=cursor_pos, end=cursor_pos)

        text = lines[line]

        # Find quote start
        # If cursor is on quote, use it
        if col < len(text) and text[col] == quote_char:
            start_col = col
        else:
            # Find preceding quote
            start_col = -1
            for c in range(col - 1, -1, -1):
                if text[c] == quote_char:
                    # Check if escaped
                    if c > 0 and text[c - 1] == '\\':
                        continue
                    start_col = c
                    break

            if start_col == -1:
                # Find following quote
                for c in range(col, len(text)):
                    if text[c] == quote_char:
                        start_col = c
                        break

        if start_col == -1 or start_col >= len(text):
            return MotionResult(start=cursor_pos, end=cursor_pos)

        # Find quote end
        end_col = -1
        for c in range(start_col + 1, len(text)):
            if text[c] == quote_char:
                # Check if escaped
                if c > 0 and text[c - 1] == '\\':
                    continue
                end_col = c
                break

        if end_col == -1:
            return MotionResult(start=cursor_pos, end=cursor_pos)

        if around:
            return MotionResult(
                start=(line, start_col),
                end=(line, end_col),
                linewise=False,
            )
        else:
            return MotionResult(
                start=(line, start_col + 1),
                end=(line, end_col - 1),
                linewise=False,
            )

    def get_tag_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get HTML/XML tag text object (at/it)."""
        line, col = cursor_pos

        # Find opening tag
        tag_pattern = re.compile(r'<(\w+)[^>]*>')
        close_pattern = re.compile(r'</(\w+)>')

        # Search backward for opening tag
        all_text = '\n'.join(lines)
        text_pos = sum(len(lines[l]) + 1 for l in range(line)) + col

        # Find nearest opening tag before cursor
        best_match = None
        best_start = -1
        for match in tag_pattern.finditer(all_text[:text_pos + 1]):
            if match.start() > best_start:
                best_start = match.start()
                best_match = match.group(1)

        if not best_match:
            # Search forward
            for match in tag_pattern.finditer(all_text[text_pos:]):
                best_match = match.group(1)
                best_start = text_pos + match.start()
                break

        if not best_match:
            return MotionResult(start=cursor_pos, end=cursor_pos)

        # Find closing tag
        depth = 0
        pos = best_start
        while pos < len(all_text):
            open_match = tag_pattern.match(all_text[pos:])
            if open_match and open_match.group(1) == best_match:
                depth += 1
                pos += open_match.end()

            close_match = close_pattern.match(all_text[pos:])
            if close_match and close_match.group(1) == best_match:
                depth -= 1
                if depth == 0:
                    end_pos = pos + close_match.end()
                    break
                pos += close_match.end()
            else:
                pos += 1

        start_line, start_col = self._text_pos_to_line_col(lines, best_start)
        end_line, end_col = self._text_pos_to_line_col(lines, end_pos)

        if around:
            return MotionResult(
                start=(start_line, start_col),
                end=(end_line, end_col - 1),
                linewise=False,
            )
        else:
            # Find content start (after opening tag)
            open_end = best_start + len(tag_pattern.match(all_text[best_start:]).group(0))
            content_start_line, content_start_col = self._text_pos_to_line_col(lines, open_end)

            # Find content end (before closing tag)
            close_start = end_pos - len(close_pattern.match(all_text[end_pos - len(f'</{best_match}>'):]).group(0))
            content_end_line, content_end_col = self._text_pos_to_line_col(lines, close_start)

            return MotionResult(
                start=(content_start_line, content_start_col),
                end=(content_end_line, content_end_col - 1),
                linewise=False,
            )

    def get_line_object(self, lines: List[str], cursor_pos: Tuple[int, int], around: bool = False) -> MotionResult:
        """Get line text object (al/il)."""
        line, col = cursor_pos
        if line >= len(lines):
            return MotionResult(start=cursor_pos, end=cursor_pos)

        # For both around and inner, select the whole line
        # 'around' includes newline behavior differently in visual mode

        start_col = 0
        end_col = len(lines[line])

        return MotionResult(
            start=(line, start_col),
            end=(line, end_col - 1),
            linewise=True,
        )

    def _is_word_boundary(self, char: str) -> bool:
        """Check if character is a word boundary."""
        return char.isspace() or char in self.WORD_BOUNDARIES

    def _text_pos_to_line_col(self, lines: List[str], pos: int) -> Tuple[int, int]:
        """Convert text position to line/col."""
        line = 0
        curr_pos = 0
        while line < len(lines):
            line_len = len(lines[line]) + 1  # +1 for newline
            if curr_pos + line_len > pos:
                return (line, pos - curr_pos)
            curr_pos += line_len
            line += 1
        return (len(lines) - 1, len(lines[-1]) if lines else 0)


# Text object registry
TEXT_OBJECT_REGISTRY = {
    'aw': ('word', True),
    'iw': ('word', False),
    'aW': ('WORD', True),
    'iW': ('WORD', False),
    'ap': ('paragraph', True),
    'ip': ('paragraph', False),
    'as': ('sentence', True),
    'is': ('sentence', False),
    'a(': ('block', True, '('),
    'i(': ('block', False, '('),
    'a)': ('block', True, '('),
    'i)': ('block', False, '('),
    'ab': ('block', True, '('),
    'ib': ('block', False, '('),
    'a{': ('block', True, '{'),
    'i{': ('block', False, '{'),
    'a}': ('block', True, '{'),
    'i}': ('block', False, '{'),
    'aB': ('block', True, '{'),
    'iB': ('block', False, '{'),
    'a[': ('block', True, '['),
    'i[': ('block', False, '['),
    'a]': ('block', True, '['),
    'i]': ('block', False, '['),
    'a<': ('block', True, '<'),
    'i<': ('block', False, '<'),
    'a>': ('block', True, '<'),
    'i>': ('block', False, '<'),
    'a"': ('quote', True, '"'),
    'i"': ('quote', False, '"'),
    "a'": ('quote', True, "'"),
    "i'": ('quote', False, "'"),
    'a`': ('quote', True, '`'),
    'i`': ('quote', False, '`'),
    'at': ('tag', True),
    'it': ('tag', False),
    'al': ('line', True),
    'il': ('line', False),
}


__all__ = [
    "VimTextObjects",
    "TEXT_OBJECT_REGISTRY",
]
"""Vim Text Objects - Vim text object commands."""

from __future__ import annotations
import re
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
from enum import Enum


class TextObjectKind(Enum):
    """Text object kinds."""
    WORD = "word"
    WORD_UPPER = "WORD"  # Whitespace delimited
    LINE = "line"
    PARAGRAPH = "paragraph"
    SENTENCE = "sentence"
    BLOCK = "block"  # Parentheses, brackets, braces
    QUOTE = "quote"  # Single, double quotes
    TAG = "tag"  # HTML/XML tags
    FUNCTION = "function"
    CLASS = "class"
    ARGUMENT = "argument"


@dataclass
class TextObject:
    """Text object range."""
    kind: TextObjectKind
    start: int
    end: int
    linewise: bool = False
    content: str = ""


class VimTextObjects:
    """Vim text object implementations."""

    def __init__(self):
        self._objects: Dict[str, Callable] = {}
        self._load_objects()

    def _load_objects(self) -> None:
        """Load text object handlers."""
        self._objects = {
            # Word objects
            "aw": self._object_word,
            "iw": self._object_inner_word,
            "aW": self._object_WORD,
            "iW": self._object_inner_WORD,

            # Paragraph objects
            "ap": self._object_paragraph,
            "ip": self._object_inner_paragraph,

            # Block objects
            "a(": self._object_block_paren,
            "i(": self._object_inner_paren,
            "a)": self._object_block_paren,
            "i)": self._object_inner_paren,
            "a[": self._object_block_bracket,
            "i[": self._object_inner_bracket,
            "a]": self._object_block_bracket,
            "i]": self._object_inner_bracket,
            "a{": self._object_block_brace,
            "i{": self._object_inner_brace,
            "a}": self._object_block_brace,
            "i}": self._object_inner_brace,
            "ab": self._object_block_paren,  # alias
            "ib": self._object_inner_paren,
            "aB": self._object_block_brace,  # alias
            "iB": self._object_inner_brace,

            # Quote objects
            "a'": self._object_quote_single,
            "i'": self._object_inner_quote_single,
            "a\"": self._object_quote_double,
            "i\"": self._object_inner_quote_double,
            "a`": self._object_quote_backtick,
            "i`": self._object_inner_quote_backtick,

            # Tag objects
            "at": self._object_tag,
            "it": self._object_inner_tag,

            # Sentence objects
            "as": self._object_sentence,
            "is": self._object_inner_sentence,
        }

    def get_object(
        self,
        object_key: str,
        text: str,
        position: int,
    ) -> Optional[TextObject]:
        """Get text object at position."""
        handler = self._objects.get(object_key)

        if handler:
            return handler(text, position)

        return None

    def _object_word(self, text: str, position: int) -> Optional[TextObject]:
        """A word (includes surrounding whitespace)."""
        start, end = self._find_word_bounds(text, position)

        # Include trailing whitespace
        while end < len(text) and text[end].isspace():
            end += 1

        return TextObject(
            kind=TextObjectKind.WORD,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_inner_word(self, text: str, position: int) -> Optional[TextObject]:
        """Inner word (no whitespace)."""
        start, end = self._find_word_bounds(text, position)

        return TextObject(
            kind=TextObjectKind.WORD,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_WORD(self, text: str, position: int) -> Optional[TextObject]:
        """A WORD (whitespace delimited, includes whitespace)."""
        start, end = self._find_WORD_bounds(text, position)

        # Include trailing whitespace
        while end < len(text) and text[end].isspace():
            end += 1

        return TextObject(
            kind=TextObjectKind.WORD_UPPER,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_inner_WORD(self, text: str, position: int) -> Optional[TextObject]:
        """Inner WORD."""
        start, end = self._find_WORD_bounds(text, position)

        return TextObject(
            kind=TextObjectKind.WORD_UPPER,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _find_word_bounds(self, text: str, position: int) -> Tuple[int, int]:
        """Find word boundaries."""
        # Word is alphanumeric sequence
        start = position
        while start > 0 and text[start - 1].isalnum():
            start -= 1

        end = position
        while end < len(text) and text[end].isalnum():
            end += 1

        return start, end

    def _find_WORD_bounds(self, text: str, position: int) -> Tuple[int, int]:
        """Find WORD boundaries (whitespace delimited)."""
        start = position
        while start > 0 and not text[start - 1].isspace():
            start -= 1

        end = position
        while end < len(text) and not text[end].isspace():
            end += 1

        return start, end

    def _object_paragraph(self, text: str, position: int) -> Optional[TextObject]:
        """A paragraph."""
        lines = text.split("\n")

        # Find current line
        current_line = 0
        char_count = 0
        for i, line in enumerate(lines):
            if char_count + len(line) >= position:
                current_line = i
                break
            char_count += len(line) + 1

        # Find paragraph start
        start_line = current_line
        while start_line > 0 and lines[start_line - 1]:
            start_line -= 1

        # Find paragraph end
        end_line = current_line
        while end_line < len(lines) - 1 and lines[end_line + 1]:
            end_line += 1

        # Include blank line after
        if end_line < len(lines) - 1:
            end_line += 1

        start = sum(len(lines[i]) + 1 for i in range(start_line))
        end = sum(len(lines[i]) + 1 for i in range(end_line + 1))

        return TextObject(
            kind=TextObjectKind.PARAGRAPH,
            start=start,
            end=end,
            linewise=True,
            content=text[start:end],
        )

    def _object_inner_paragraph(self, text: str, position: int) -> Optional[TextObject]:
        """Inner paragraph (no blank lines)."""
        lines = text.split("\n")

        # Find current line
        current_line = 0
        char_count = 0
        for i, line in enumerate(lines):
            if char_count + len(line) >= position:
                current_line = i
                break
            char_count += len(line) + 1

        # Find paragraph bounds
        start_line = current_line
        while start_line > 0 and lines[start_line - 1]:
            start_line -= 1

        end_line = current_line
        while end_line < len(lines) - 1 and lines[end_line + 1]:
            end_line += 1

        start = sum(len(lines[i]) + 1 for i in range(start_line))
        end = sum(len(lines[i]) + 1 for i in range(end_line + 1))

        return TextObject(
            kind=TextObjectKind.PARAGRAPH,
            start=start,
            end=end,
            linewise=True,
            content=text[start:end],
        )

    def _object_block_paren(self, text: str, position: int) -> Optional[TextObject]:
        """Parentheses block."""
        return self._find_block(text, position, "(", ")")

    def _object_inner_paren(self, text: str, position: int) -> Optional[TextObject]:
        """Inner parentheses."""
        obj = self._find_block(text, position, "(", ")")
        if obj:
            obj.start += 1  # Skip opening paren
            obj.end -= 1    # Skip closing paren
        return obj

    def _object_block_bracket(self, text: str, position: int) -> Optional[TextObject]:
        """Bracket block."""
        return self._find_block(text, position, "[", "]")

    def _object_inner_bracket(self, text: str, position: int) -> Optional[TextObject]:
        """Inner bracket."""
        obj = self._find_block(text, position, "[", "]")
        if obj:
            obj.start += 1
            obj.end -= 1
        return obj

    def _object_block_brace(self, text: str, position: int) -> Optional[TextObject]:
        """Brace block."""
        return self._find_block(text, position, "{", "}")

    def _object_inner_brace(self, text: str, position: int) -> Optional[TextObject]:
        """Inner brace."""
        obj = self._find_block(text, position, "{", "}")
        if obj:
            obj.start += 1
            obj.end -= 1
        return obj

    def _find_block(
        self,
        text: str,
        position: int,
        open_char: str,
        close_char: str,
    ) -> Optional[TextObject]:
        """Find matching block."""
        # Find opening
        balance = 0
        start = position

        # Search backward for opening
        while start >= 0:
            if text[start] == close_char:
                balance += 1
            elif text[start] == open_char:
                balance -= 1
                if balance <= 0:
                    break
            start -= 1

        if start < 0 or text[start] != open_char:
            return None

        # Find closing
        balance = 1
        end = start + 1

        while end < len(text) and balance > 0:
            if text[end] == open_char:
                balance += 1
            elif text[end] == close_char:
                balance -= 1
            end += 1

        if balance != 0:
            return None

        return TextObject(
            kind=TextObjectKind.BLOCK,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_quote_single(self, text: str, position: int) -> Optional[TextObject]:
        """Single quote string."""
        return self._find_quote(text, position, "'")

    def _object_inner_quote_single(self, text: str, position: int) -> Optional[TextObject]:
        """Inner single quote."""
        obj = self._find_quote(text, position, "'")
        if obj:
            obj.start += 1
            obj.end -= 1
        return obj

    def _object_quote_double(self, text: str, position: int) -> Optional[TextObject]:
        """Double quote string."""
        return self._find_quote(text, position, '"')

    def _object_inner_quote_double(self, text: str, position: int) -> Optional[TextObject]:
        """Inner double quote."""
        obj = self._find_quote(text, position, '"')
        if obj:
            obj.start += 1
            obj.end -= 1
        return obj

    def _object_quote_backtick(self, text: str, position: int) -> Optional[TextObject]:
        """Backtick string."""
        return self._find_quote(text, position, "`")

    def _object_inner_quote_backtick(self, text: str, position: int) -> Optional[TextObject]:
        """Inner backtick."""
        obj = self._find_quote(text, position, "`")
        if obj:
            obj.start += 1
            obj.end -= 1
        return obj

    def _find_quote(self, text: str, position: int, quote_char: str) -> Optional[TextObject]:
        """Find quote boundaries."""
        # Find opening quote
        start = position
        while start >= 0:
            if text[start] == quote_char:
                # Check if escaped
                if start > 0 and text[start - 1] == "\\":
                    start -= 1
                    continue
                break
            start -= 1

        if start < 0:
            return None

        # Find closing quote
        end = start + 1
        while end < len(text):
            if text[end] == quote_char:
                if end > 0 and text[end - 1] == "\\":
                    end += 1
                    continue
                break
            end += 1

        if end >= len(text):
            return None

        return TextObject(
            kind=TextObjectKind.QUOTE,
            start=start,
            end=end + 1,
            content=text[start:end + 1],
        )

    def _object_tag(self, text: str, position: int) -> Optional[TextObject]:
        """HTML/XML tag block."""
        # Find opening tag
        tag_pattern = r"<(\w+)[^>]*>"
        match = None

        for m in re.finditer(tag_pattern, text):
            if m.end() <= position or m.start() > position:
                continue
            match = m
            break

        # Search backward if not found
        if not match:
            pos = position
            while pos >= 0:
                m = re.match(tag_pattern, text[pos:])
                if m:
                    match = re.finditer(tag_pattern, text)
                    for m in match:
                        if m.start() == pos:
                            match = m
                            break
                    break
                pos -= 1

        if not match:
            return None

        tag_name = match.group(1)
        start = match.start()

        # Find closing tag
        close_pattern = f"</{tag_name}>"
        end_match = re.search(close_pattern, text[start + match.end():])

        if not end_match:
            return None

        end = start + match.end() + end_match.end()

        return TextObject(
            kind=TextObjectKind.TAG,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_inner_tag(self, text: str, position: int) -> Optional[TextObject]:
        """Inner HTML/XML tag."""
        obj = self._object_tag(text, position)

        if obj:
            # Find actual inner content
            inner_start = obj.start
            while inner_start < obj.end and text[inner_start] != ">":
                inner_start += 1
            inner_start += 1

            inner_end = obj.end
            while inner_end > inner_start and not text[inner_end - 1:].startswith("</"):
                inner_end -= 1

            obj.start = inner_start
            obj.end = inner_end

        return obj

    def _object_sentence(self, text: str, position: int) -> Optional[TextObject]:
        """Sentence."""
        # Find sentence boundaries
        start = position
        while start > 0:
            if text[start - 1] in ".!?":
                break
            start -= 1

        end = position
        while end < len(text):
            if text[end] in ".!?":
                end += 1
                # Include trailing whitespace
                while end < len(text) and text[end].isspace():
                    end += 1
                break
            end += 1

        return TextObject(
            kind=TextObjectKind.SENTENCE,
            start=start,
            end=end,
            content=text[start:end],
        )

    def _object_inner_sentence(self, text: str, position: int) -> Optional[TextObject]:
        """Inner sentence."""
        obj = self._object_sentence(text, position)

        if obj:
            # Trim trailing punctuation/whitespace
            while obj.end > obj.start and text[obj.end - 1] in ".!? \n":
                obj.end -= 1

        return obj


__all__ = [
    "TextObjectKind",
    "TextObject",
    "VimTextObjects",
]
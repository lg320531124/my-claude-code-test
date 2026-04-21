"""Text Formatter - Text formatting and manipulation utilities."""

from __future__ import annotations
import re
import textwrap
from typing import Optional, List
from dataclasses import dataclass
from enum import Enum


class TextFormat(Enum):
    """Text format types."""
    PLAIN = "plain"
    MARKDOWN = "markdown"
    HTML = "html"
    CODE = "code"
    JSON = "json"


class TextAlign(Enum):
    """Text alignment options."""
    LEFT = "left"
    CENTER = "center"
    RIGHT = "right"


@dataclass
class FormatConfig:
    """Format configuration."""
    max_width: int = 80
    indent: int = 0
    wrap: bool = True
    preserve_newlines: bool = True
    strip_whitespace: bool = True
    format: TextFormat = TextFormat.PLAIN
    alignment: TextAlign = TextAlign.LEFT


@dataclass
class FormattedText:
    """Formatted text result."""
    text: str
    original: str
    format: TextFormat
    lines: int = 0
    width: int = 0
    truncated: bool = False


class TextFormatter:
    """Format and manipulate text."""

    def __init__(self, config: Optional[FormatConfig] = None):
        self.config = config or FormatConfig()

    def format(self, text: str, format_type: Optional[TextFormat] = None) -> FormattedText:
        """Format text."""
        use_format = format_type or self.config.format

        # Strip whitespace if configured
        if self.config.strip_whitespace:
            text = text.strip()

        # Apply indent
        if self.config.indent > 0:
            indent_str = " " * self.config.indent
            text = "\n".join(indent_str + line for line in text.split("\n"))

        # Wrap text if configured
        if self.config.wrap and self.config.max_width > 0:
            text = self._wrap_text(text)

        # Format specific handling
        if use_format == TextFormat.MARKDOWN:
            text = self._format_markdown(text)
        elif use_format == TextFormat.HTML:
            text = self._format_html(text)
        elif use_format == TextFormat.CODE:
            text = self._format_code(text)
        elif use_format == TextFormat.JSON:
            text = self._format_json_text(text)

        # Apply alignment
        text = self._apply_alignment(text)

        # Count metrics
        lines = text.count("\n") + 1
        width = max(len(line) for line in text.split("\n"))
        truncated = len(text) < len(text)

        return FormattedText(
            text=text,
            original=text,
            format=use_format,
            lines=lines,
            width=width,
            truncated=truncated,
        )

    def _wrap_text(self, text: str) -> str:
        """Wrap text to max width."""
        if self.config.preserve_newlines:
            lines = text.split("\n")
            wrapped = []
            for line in lines:
                if len(line) > self.config.max_width:
                    wrapped.append(textwrap.fill(line, width=self.config.max_width))
                else:
                    wrapped.append(line)
            return "\n".join(wrapped)
        else:
            return textwrap.fill(text, width=self.config.max_width)

    def _apply_alignment(self, text: str) -> str:
        """Apply text alignment."""
        if self.config.alignment == TextAlign.LEFT:
            return text

        lines = text.split("\n")
        aligned = []

        for line in lines:
            if self.config.alignment == TextAlign.CENTER:
                padding = (self.config.max_width - len(line)) // 2
                aligned.append(" " * padding + line)
            elif self.config.alignment == TextAlign.RIGHT:
                padding = self.config.max_width - len(line)
                aligned.append(" " * padding + line)

        return "\n".join(aligned)

    def _format_markdown(self, text: str) -> str:
        """Format markdown text."""
        # Preserve markdown structure
        return text

    def _format_html(self, text: str) -> str:
        """Format HTML text."""
        # Basic HTML escaping
        text = text.replace("&", "&amp;")
        text = text.replace("<", "&lt;")
        text = text.replace(">", "&gt;")
        return text

    def _format_code(self, text: str) -> str:
        """Format code text."""
        # Add line numbers
        lines = text.split("\n")
        numbered = []
        for i, line in enumerate(lines, 1):
            numbered.append(f"{i:4d} | {line}")
        return "\n".join(numbered)

    def _format_json_text(self, text: str) -> str:
        """Format JSON-like text."""
        return text

    def truncate(self, text: str, max_length: int, suffix: str = "...") -> FormattedText:
        """Truncate text."""
        truncated = False
        if len(text) > max_length:
            text = text[:max_length - len(suffix)] + suffix
            truncated = True

        lines = text.count("\n") + 1
        width = max(len(line) for line in text.split("\n"))

        return FormattedText(
            text=text,
            original=text,
            format=self.config.format,
            lines=lines,
            width=width,
            truncated=truncated,
        )

    def indent(self, text: str, level: int = 1, indent_char: str = "  ") -> str:
        """Indent text by level."""
        indent_str = indent_char * level
        return "\n".join(indent_str + line for line in text.split("\n"))

    def dedent(self, text: str) -> str:
        """Remove common indentation."""
        return textwrap.dedent(text)

    def center(self, text: str, width: int = 80, fill_char: str = " ") -> str:
        """Center text."""
        lines = text.split("\n")
        centered = []
        for line in lines:
            centered.append(line.center(width, fill_char))
        return "\n".join(centered)

    def justify(self, text: str, width: int = 80) -> str:
        """Justify text."""
        lines = text.split("\n")
        justified = []
        for line in lines:
            if len(line) < width:
                justified.append(line.ljust(width))
            else:
                justified.append(line)
        return "\n".join(justified)

    def strip_lines(self, text: str) -> str:
        """Strip each line."""
        return "\n".join(line.strip() for line in text.split("\n"))

    def normalize_spaces(self, text: str) -> str:
        """Normalize multiple spaces to single."""
        return re.sub(r" +", " ", text)

    def normalize_newlines(self, text: str) -> str:
        """Normalize newlines."""
        # Replace multiple newlines with double
        text = re.sub(r"\n{3,}", "\n\n", text)
        # Strip trailing whitespace from lines
        return "\n".join(line.rstrip() for line in text.split("\n"))

    def remove_empty_lines(self, text: str) -> str:
        """Remove empty lines."""
        return "\n".join(line for line in text.split("\n") if line.strip())

    def compact(self, text: str) -> str:
        """Compact text - remove extra whitespace."""
        text = self.normalize_spaces(text)
        text = self.normalize_newlines(text)
        text = self.strip_lines(text)
        return text

    def title(self, text: str, underline: str = "=", width: int = 80) -> str:
        """Create title with underline."""
        text = text.strip()
        if width > len(text):
            underline_line = underline * min(len(text), width)
        else:
            underline_line = underline * width
        return f"{text}\n{underline_line}"

    def heading(self, text: str, level: int = 1) -> str:
        """Create markdown heading."""
        prefix = "#" * level
        return f"{prefix} {text}"

    def bullet_list(self, items: List[str], bullet: str = "-") -> str:
        """Format bullet list."""
        return "\n".join(f"{bullet} {item}" for item in items)

    def numbered_list(self, items: List[str], start: int = 1) -> str:
        """Format numbered list."""
        return "\n".join(f"{i}. {item}" for i, item in enumerate(items, start))

    def table(
        self,
        headers: List[str],
        rows: List[List[str]],
        align: Optional[List[TextAlign]] = None,
    ) -> str:
        """Format table."""
        # Calculate column widths
        widths = [len(h) for h in headers]
        for row in rows:
            for i, cell in enumerate(row):
                if i < len(widths):
                    widths[i] = max(widths[i], len(cell))

        # Build separator
        sep = "+" + "+".join("-" * (w + 2) for w in widths) + "+"

        # Build header
        header_cells = []
        for i, h in enumerate(headers):
            align_type = align[i] if align and i < len(align) else TextAlign.LEFT
            if align_type == TextAlign.CENTER:
                header_cells.append(h.center(widths[i]))
            elif align_type == TextAlign.RIGHT:
                header_cells.append(h.rjust(widths[i]))
            else:
                header_cells.append(h.ljust(widths[i]))
        header_line = "| " + " | ".join(header_cells) + " |"

        # Build rows
        row_lines = []
        for row in rows:
            row_cells = []
            for i, cell in enumerate(row[:len(headers)]):
                align_type = align[i] if align and i < len(align) else TextAlign.LEFT
                if align_type == TextAlign.CENTER:
                    row_cells.append(cell.center(widths[i]))
                elif align_type == TextAlign.RIGHT:
                    row_cells.append(cell.rjust(widths[i]))
                else:
                    row_cells.append(cell.ljust(widths[i]))
            row_lines.append("| " + " | ".join(row_cells) + " |")

        # Combine
        lines = [sep, header_line, sep]
        for row_line in row_lines:
            lines.append(row_line)
        lines.append(sep)

        return "\n".join(lines)

    def highlight(
        self,
        text: str,
        pattern: str,
        before: str = "**",
        after: str = "**",
    ) -> str:
        """Highlight pattern in text."""
        return re.sub(pattern, f"{before}\\g<0>{after}", text)

    def wrap_paragraphs(self, text: str, width: int = 80) -> str:
        """Wrap paragraphs."""
        paragraphs = text.split("\n\n")
        wrapped = []
        for para in paragraphs:
            wrapped.append(textwrap.fill(para.strip(), width=width))
        return "\n\n".join(wrapped)


def format_text(text: str, config: Optional[FormatConfig] = None) -> FormattedText:
    """Format text with default configuration."""
    formatter = TextFormatter(config)
    return formatter.format(text)


def truncate_text(text: str, max_length: int = 80, suffix: str = "...") -> str:
    """Truncate text to max length."""
    formatter = TextFormatter()
    result = formatter.truncate(text, max_length, suffix)
    return result.text


def indent_text(text: str, level: int = 1) -> str:
    """Indent text."""
    formatter = TextFormatter()
    return formatter.indent(text, level)


def compact_text(text: str) -> str:
    """Compact text."""
    formatter = TextFormatter()
    return formatter.compact(text)


def create_table(headers: List[str], rows: List[List[str]]) -> str:
    """Create simple table."""
    formatter = TextFormatter()
    return formatter.table(headers, rows)


__all__ = [
    "TextFormat",
    "TextAlign",
    "FormatConfig",
    "FormattedText",
    "TextFormatter",
    "format_text",
    "truncate_text",
    "indent_text",
    "compact_text",
    "create_table",
]
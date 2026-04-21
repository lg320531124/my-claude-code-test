"""Output Handler - Handle tool output formatting and display."""

from __future__ import annotations
import re
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from .log import get_logger

logger = get_logger(__name__)


class OutputType(Enum):
    """Output types."""
    TEXT = "text"
    CODE = "code"
    JSON = "json"
    TABLE = "table"
    LIST = "list"
    ERROR = "error"
    SUCCESS = "success"
    WARNING = "warning"
    INFO = "info"
    FILE = "file"
    DIFF = "diff"
    MARKDOWN = "markdown"


@dataclass
class OutputConfig:
    """Output configuration."""
    max_length: int = 10000
    truncate_message: str = "... [truncated]"
    indent_json: bool = True
    show_line_numbers: bool = True
    highlight_syntax: bool = True
    wrap_lines: bool = False
    max_wrap_width: int = 80


@dataclass
class FormattedOutput:
    """Formatted output result."""
    type: OutputType
    content: str
    raw: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    truncated: bool = False
    lines: int = 0


class OutputHandler:
    """Handle and format tool output."""

    def __init__(self, config: Optional[OutputConfig] = None):
        self.config = config or OutputConfig()

    def format(self, output: Any, type_hint: Optional[OutputType] = None) -> FormattedOutput:
        """Format output based on type."""
        # Auto-detect type if not provided
        if type_hint is None:
            type_hint = self._detect_type(output)

        # Format based on type
        formatter = self._get_formatter(type_hint)
        formatted_content = formatter(output)

        # Handle truncation
        truncated = False
        if len(formatted_content) > self.config.max_length:
            formatted_content = formatted_content[:self.config.max_length] + self.config.truncate_message
            truncated = True

        # Count lines
        lines = formatted_content.count("\n") + 1

        return FormattedOutput(
            type=type_hint,
            content=formatted_content,
            raw=output,
            truncated=truncated,
            lines=lines,
        )

    def _detect_type(self, output: Any) -> OutputType:
        """Detect output type."""
        if output is None:
            return OutputType.TEXT

        if isinstance(output, dict) or isinstance(output, list):
            return OutputType.JSON

        if isinstance(output, str):
            # Check for code patterns
            if self._looks_like_code(output):
                return OutputType.CODE

            # Check for diff patterns
            if output.startswith("---") or output.startswith("+++") or re.match(r"^@@", output):
                return OutputType.DIFF

            # Check for table patterns
            if "|" in output and re.match(r"^\|.+\|$", output.split("\n")[0]):
                return OutputType.TABLE

            # Check for list patterns
            if output.startswith("- ") or output.startswith("* ") or re.match(r"^\d+\.", output.split("\n")[0]):
                return OutputType.LIST

            # Check for markdown
            if output.startswith("#") or re.search(r"\[.+]\(.+\)", output):
                return OutputType.MARKDOWN

            # Check for error/success patterns
            if "error" in output.lower() or "failed" in output.lower():
                return OutputType.ERROR
            if "success" in output.lower() or "completed" in output.lower():
                return OutputType.SUCCESS
            if "warning" in output.lower():
                return OutputType.WARNING

        return OutputType.TEXT

    def _looks_like_code(self, text: str) -> bool:
        """Check if text looks like code."""
        code_patterns = [
            r"def\s+\w+",
            r"class\s+\w+",
            r"function\s+\w+",
            r"import\s+",
            r"from\s+\w+\s+import",
            r"const\s+\w+",
            r"let\s+\w+",
            r"var\s+\w+",
            r"return\s+",
            r"{\s*\n",
            r";\s*$",
        ]

        for pattern in code_patterns:
            if re.search(pattern, text):
                return True

        return False

    def _get_formatter(self, type: OutputType):
        """Get formatter for type."""
        formatters = {
            OutputType.TEXT: self._format_text,
            OutputType.CODE: self._format_code,
            OutputType.JSON: self._format_json,
            OutputType.TABLE: self._format_table,
            OutputType.LIST: self._format_list,
            OutputType.ERROR: self._format_error,
            OutputType.SUCCESS: self._format_success,
            OutputType.WARNING: self._format_warning,
            OutputType.INFO: self._format_info,
            OutputType.FILE: self._format_file,
            OutputType.DIFF: self._format_diff,
            OutputType.MARKDOWN: self._format_markdown,
        }
        return formatters.get(type, self._format_text)

    def _format_text(self, output: Any) -> str:
        """Format plain text."""
        if isinstance(output, str):
            return output
        return str(output)

    def _format_code(self, output: str) -> str:
        """Format code with line numbers."""
        if self.config.show_line_numbers:
            lines = output.split("\n")
            numbered = []
            for i, line in enumerate(lines, 1):
                numbered.append(f"{i:4d} | {line}")
            return "\n".join(numbered)
        return output

    def _format_json(self, output: Any) -> str:
        """Format JSON output."""
        indent = 2 if self.config.indent_json else None
        return json.dumps(output, indent=indent, ensure_ascii=False)

    def _format_table(self, output: str) -> str:
        """Format table output."""
        # Preserve table formatting
        return output

    def _format_list(self, output: str) -> str:
        """Format list output."""
        # Preserve list formatting
        return output

    def _format_error(self, output: str) -> str:
        """Format error output."""
        return f"[ERROR] {output}"

    def _format_success(self, output: str) -> str:
        """Format success output."""
        return f"[SUCCESS] {output}"

    def _format_warning(self, output: str) -> str:
        """Format warning output."""
        return f"[WARNING] {output}"

    def _format_info(self, output: str) -> str:
        """Format info output."""
        return f"[INFO] {output}"

    def _format_file(self, output: Any) -> str:
        """Format file output."""
        if isinstance(output, Path):
            return str(output)
        if isinstance(output, str):
            return f"File: {output}"
        return str(output)

    def _format_diff(self, output: str) -> str:
        """Format diff output."""
        # Add syntax highlighting markers
        lines = output.split("\n")
        formatted = []
        for line in lines:
            if line.startswith("+"):
                formatted.append(f"+ {line[1:]}")
            elif line.startswith("-"):
                formatted.append(f"- {line[1:]}")
            else:
                formatted.append(line)
        return "\n".join(formatted)

    def _format_markdown(self, output: str) -> str:
        """Format markdown output."""
        # Preserve markdown formatting
        return output

    def format_table_from_dict(self, data: Dict[str, Any], headers: Optional[List[str]] = None) -> str:
        """Format dictionary as table."""
        if headers is None:
            headers = list(data.keys())

        # Calculate widths
        widths = [len(h) for h in headers]
        for key, value in data.items():
            if key in headers:
                idx = headers.index(key)
                widths[idx] = max(widths[idx], len(str(value)))

        # Build table
        lines = []

        # Header
        header_line = "| " + " | ".join(h.ljust(widths[i]) for i, h in enumerate(headers)) + " |"
        lines.append(header_line)

        # Separator
        sep_line = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
        lines.append(sep_line)

        # Data
        data_line = "| " + " | ".join(str(data.get(h, "")).ljust(widths[i]) for i, h in enumerate(headers)) + " |"
        lines.append(data_line)

        return "\n".join(lines)

    def format_list_from_items(self, items: List[Any], bullet: str = "-") -> str:
        """Format list of items."""
        lines = []
        for item in items:
            lines.append(f"{bullet} {item}")
        return "\n".join(lines)

    def wrap_text(self, text: str, width: Optional[int] = None) -> str:
        """Wrap text to specified width."""
        if not self.config.wrap_lines:
            return text

        use_width = width or self.config.max_wrap_width

        words = text.split()
        lines = []
        current_line = []
        current_length = 0

        for word in words:
            if current_length + len(word) + 1 > use_width:
                if current_line:
                    lines.append(" ".join(current_line))
                current_line = [word]
                current_length = len(word)
            else:
                current_line.append(word)
                current_length += len(word) + 1

        if current_line:
            lines.append(" ".join(current_line))

        return "\n".join(lines)


def format_output(output: Any, config: Optional[OutputConfig] = None) -> FormattedOutput:
    """Format output with default configuration."""
    handler = OutputHandler(config)
    return handler.format(output)


def format_json(data: Any, indent: bool = True) -> str:
    """Format JSON data."""
    return json.dumps(data, indent=2 if indent else None, ensure_ascii=False)


def format_error(message: str) -> str:
    """Format error message."""
    return f"[ERROR] {message}"


def format_success(message: str) -> str:
    """Format success message."""
    return f"[SUCCESS] {message}"


__all__ = [
    "OutputType",
    "OutputConfig",
    "FormattedOutput",
    "OutputHandler",
    "format_output",
    "format_json",
    "format_error",
    "format_success",
]
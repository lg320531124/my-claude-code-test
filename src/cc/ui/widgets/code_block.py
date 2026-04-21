"""Code Block Widget - Code display and highlighting."""

from __future__ import annotations
import asyncio
import re
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class Language(Enum):
    """Supported languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    GO = "go"
    RUST = "rust"
    JAVA = "java"
    C = "c"
    CPP = "cpp"
    HTML = "html"
    CSS = "css"
    JSON = "json"
    YAML = "yaml"
    MARKDOWN = "markdown"
    SQL = "sql"
    SHELL = "shell"
    UNKNOWN = "unknown"


@dataclass
class CodeBlockConfig:
    """Code block configuration."""
    language: Language = Language.UNKNOWN
    show_line_numbers: bool = True
    highlight_lines: List[int] = field(default_factory=list)
    max_height: int = 50
    wrap_long_lines: bool = False
    theme: str = "dark"
    copy_button: bool = True


@dataclass
class HighlightedLine:
    """Highlighted line."""
    number: int
    content: str
    tokens: List[Dict[str, str]] = field(default_factory=list)  # [{text, color}]
    is_highlighted: bool = False


class CodeBlock:
    """Code block widget with syntax highlighting."""

    def __init__(self, config: CodeBlockConfig = None):
        self._config = config or CodeBlockConfig()
        self._code: str = ""
        self._lines: List[HighlightedLine] = []
        self._language: Language = Language.UNKNOWN
        self._copy_callback: Optional[Callable] = None

    def set_code(self, code: str, language: Language = None) -> None:
        """Set code content.

        Args:
            code: Code string
            language: Language type
        """
        self._code = code
        self._language = language or self._detect_language(code)
        self._config.language = self._language
        self._highlight()

    def _detect_language(self, code: str) -> Language:
        """Detect language from code.

        Args:
            code: Code string

        Returns:
            Detected Language
        """
        # Heuristic detection
        if code.startswith("#!") or "def " in code or "import " in code:
            return Language.PYTHON
        elif "function" in code or "const " in code or "let " in code:
            if ": " in code and "interface" in code:
                return Language.TYPESCRIPT
            return Language.JAVASCRIPT
        elif "package " in code and "func " in code:
            return Language.GO
        elif "fn " in code or "let mut" in code:
            return Language.RUST
        elif "public class" in code or "private void" in code:
            return Language.JAVA
        elif "#include" in code:
            if "class" in code:
                return Language.CPP
            return Language.C
        elif "<!DOCTYPE" in code or "<html" in code:
            return Language.HTML
        elif "{" in code and ":" in code and '"' in code:
            return Language.JSON
        elif "---" in code or "apiVersion:" in code:
            return Language.YAML
        elif "SELECT" in code.upper() or "FROM" in code.upper():
            return Language.SQL
        elif "$ " in code or "#!/bin/bash" in code:
            return Language.SHELL

        return Language.UNKNOWN

    def _highlight(self) -> None:
        """Apply syntax highlighting."""
        lines = self._code.splitlines()

        for i, line in enumerate(lines):
            tokens = self._highlight_line(line, self._language)
            highlighted = i + 1 in self._config.highlight_lines

            self._lines.append(HighlightedLine(
                number=i + 1,
                content=line,
                tokens=tokens,
                is_highlighted=highlighted,
            ))

    def _highlight_line(self, line: str, language: Language) -> List[Dict[str, str]]:
        """Highlight single line.

        Args:
            line: Line content
            language: Language type

        Returns:
            List of tokens with colors
        """
        tokens = []

        # Simple token-based highlighting
        patterns = self._get_patterns(language)

        pos = 0
        while pos < len(line):
            matched = False

            for pattern, color in patterns:
                match = re.match(pattern, line[pos:])
                if match:
                    matched_text = match.group()
                    tokens.append({
                        "text": matched_text,
                        "color": color,
                    })
                    pos += len(matched_text)
                    matched = True
                    break

            if not matched:
                tokens.append({
                    "text": line[pos],
                    "color": "default",
                })
                pos += 1

        return tokens

    def _get_patterns(self, language: Language) -> List[tuple]:
        """Get highlighting patterns for language.

        Args:
            language: Language type

        Returns:
            List of (pattern, color) tuples
        """
        patterns = []

        # Common patterns
        patterns.extend([
            (r'"[^"]*"', "green"),  # String
            (r"'[^']*'", "green"),  # String
            (r'\b\d+\b', "yellow"),  # Number
            (r'#.*$', "dim"),  # Comment
            (r'//.*$', "dim"),  # Comment
        ])

        # Language-specific patterns
        if language == Language.PYTHON:
            patterns.extend([
                (r'\b(def|class|import|from|return|if|else|for|while|try|except|with|as|lambda|yield)\b', "cyan"),
                (r'\b(True|False|None)\b', "magenta"),
                (r'\b(self)\b', "dim"),
            ])

        elif language in {Language.JAVASCRIPT, Language.TYPESCRIPT}:
            patterns.extend([
                (r'\b(function|const|let|var|return|if|else|for|while|class|extends|import|export|from|async|await)\b', "cyan"),
                (r'\b(true|false|null|undefined)\b', "magenta"),
            ])

        elif language == Language.GO:
            patterns.extend([
                (r'\b(func|package|import|var|const|type|struct|interface|return|if|else|for|range|go|chan)\b', "cyan"),
            ])

        elif language == Language.RUST:
            patterns.extend([
                (r'\b(fn|let|mut|pub|struct|enum|impl|trait|mod|use|return|if|else|for|while|match|async|await)\b', "cyan"),
            ])

        elif language == Language.SHELL:
            patterns.extend([
                (r'\$\{[^}]+\}', "magenta"),  # Variable
                (r'\$\w+', "magenta"),  # Variable
                (r'\b(if|then|else|fi|for|do|done|while|case|esac|function)\b', "cyan"),
            ])

        return patterns

    def render(self) -> str:
        """Render code block.

        Returns:
            Rendered string
        """
        output = []

        # Language header
        if self._language != Language.UNKNOWN:
            output.append(f"[{self._language.value}]")

        # Code lines
        visible_lines = self._lines[:self._config.max_height]

        for line in visible_lines:
            # Line number
            if self._config.show_line_numbers:
                line_num = f"{line.number:4d} | "
            else:
                line_num = ""

            # Build colored line
            colored_line = ""
            for token in line.tokens:
                text = token["text"]
                color = token["color"]
                colored_line += f"[{color}]{text}[/]"

            # Highlighted marker
            marker = ">>> " if line.is_highlighted else ""

            output.append(f"{marker}{line_num}{colored_line}")

        # Truncated indicator
        if len(self._lines) > self._config.max_height:
            output.append(f"... ({len(self._lines) - self._config.max_height} more lines)")

        return "\n".join(output)

    async def copy(self) -> None:
        """Copy code to clipboard."""
        if self._copy_callback:
            try:
                await self._copy_callback(self._code)
            except Exception:
                pass

    def set_highlight_lines(self, lines: List[int]) -> None:
        """Set highlighted lines.

        Args:
            lines: Line numbers to highlight
        """
        self._config.highlight_lines = lines
        self._highlight()

    def set_copy_callback(self, callback: Callable) -> None:
        """Set copy callback."""
        self._copy_callback = callback

    def get_line(self, number: int) -> Optional[HighlightedLine]:
        """Get specific line.

        Args:
            number: Line number

        Returns:
            HighlightedLine or None
        """
        if 1 <= number <= len(self._lines):
            return self._lines[number - 1]
        return None

    @property
    def line_count(self) -> int:
        """Get line count."""
        return len(self._lines)

    @property
    def code(self) -> str:
        """Get raw code."""
        return self._code


__all__ = [
    "Language",
    "CodeBlockConfig",
    "HighlightedLine",
    "CodeBlock",
]

"""Output Styles Module - Response formatting styles.

Provides multiple output formatting styles:
- concise: Minimal output
- explanatory: Detailed explanations
- technical: Technical documentation
- friendly: User-friendly tone
- formal: Professional format
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass


class OutputStyle(Enum):
    """Output style types."""
    CONCISE = "concise"
    EXPLANATORY = "explanatory"
    TECHNICAL = "technical"
    FRIENDLY = "friendly"
    FORMAL = "formal"
    MINIMAL = "minimal"
    VERBOSE = "verbose"


@dataclass
class StyleConfig:
    """Style configuration."""
    style: OutputStyle = OutputStyle.EXPLANATORY
    max_length: int = 500
    include_code_blocks: bool = True
    include_headers: bool = True
    include_bullet_points: bool = True
    include_progress: bool = True
    emoji_usage: bool = False
    technical_terms: bool = True


class OutputFormatter:
    """Format output according to style."""

    def __init__(self, config: StyleConfig = None):
        self.config = config or StyleConfig()
        self._style_handlers: Dict[OutputStyle, Callable] = {
            OutputStyle.CONCISE: self._format_concise,
            OutputStyle.EXPLANATORY: self._format_explanatory,
            OutputStyle.TECHNICAL: self._format_technical,
            OutputStyle.FRIENDLY: self._format_friendly,
            OutputStyle.FORMAL: self._format_formal,
            OutputStyle.MINIMAL: self._format_minimal,
            OutputStyle.VERBOSE: self._format_verbose,
        }

    def format(self, content: str, style: OutputStyle = None) -> str:
        """Format content with style."""
        target_style = style or self.config.style
        handler = self._style_handlers.get(target_style, self._format_default)
        return handler(content)

    def _format_concise(self, content: str) -> str:
        """Concise format - brief summaries."""
        # Remove extra whitespace
        lines = content.strip().split('\n')
        # Keep only essential info
        result = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('```'):
                # Condense
                if len(line) > 100:
                    line = line[:100] + '...'
                result.append(line)
        return '\n'.join(result[:3])

    def _format_explanatory(self, content: str) -> str:
        """Explanatory format - detailed with context."""
        lines = content.strip().split('\n')
        result = []
        for i, line in enumerate(lines):
            line = line.strip()
            if line:
                if self.config.include_headers and i == 0:
                    result.append(f"## {line}")
                else:
                    result.append(line)
        return '\n'.join(result)

    def _format_technical(self, content: str) -> str:
        """Technical format - structured documentation."""
        return f"```\n{content}\n```"

    def _format_friendly(self, content: str) -> str:
        """Friendly format - conversational tone."""
        # Add greeting
        lines = content.strip().split('\n')
        result = ["Here's what I found:", ""]
        for line in lines:
            if line.strip():
                result.append(f"• {line.strip()}")
        result.append("")
        result.append("Hope this helps!")
        return '\n'.join(result)

    def _format_formal(self, content: str) -> str:
        """Formal format - professional documentation."""
        lines = content.strip().split('\n')
        result = ["RESPONSE:", ""]
        for i, line in enumerate(lines):
            if line.strip():
                result.append(f"{i+1}. {line.strip()}")
        result.append("")
        result.append("---")
        return '\n'.join(result)

    def _format_minimal(self, content: str) -> str:
        """Minimal format - raw output."""
        return content.strip()

    def _format_verbose(self, content: str) -> str:
        """Verbose format - maximum detail."""
        return f"=== Detailed Output ===\n\n{content}\n\n=== End of Output ==="

    def _format_default(self, content: str) -> str:
        """Default format."""
        return content.strip()

    def format_code_block(self, code: str, language: str = "") -> str:
        """Format code block."""
        if not self.config.include_code_blocks:
            return code
        return f"```{language}\n{code}\n```"

    def format_list(self, items: List[str], ordered: bool = False) -> str:
        """Format list items."""
        if not self.config.include_bullet_points:
            return '\n'.join(items)

        result = []
        for i, item in enumerate(items):
            if ordered:
                result.append(f"{i+1}. {item}")
            else:
                result.append(f"• {item}")
        return '\n'.join(result)

    def format_header(self, text: str, level: int = 2) -> str:
        """Format header."""
        if not self.config.include_headers:
            return text
        return f"{'#' * level} {text}"

    def format_progress(self, current: int, total: int, message: str = "") -> str:
        """Format progress indicator."""
        if not self.config.include_progress:
            return ""
        percent = (current / total) * 100 if total > 0 else 0
        return f"[{current}/{total}] {percent:.0f}% - {message}"


# Style presets
STYLE_PRESETS: Dict[str, StyleConfig] = {
    "concise": StyleConfig(
        style=OutputStyle.CONCISE,
        max_length=200,
        include_headers=False,
        include_progress=False,
    ),
    "default": StyleConfig(
        style=OutputStyle.EXPLANATORY,
        include_headers=True,
        include_bullet_points=True,
    ),
    "technical": StyleConfig(
        style=OutputStyle.TECHNICAL,
        include_code_blocks=True,
        technical_terms=True,
    ),
    "friendly": StyleConfig(
        style=OutputStyle.FRIENDLY,
        emoji_usage=True,
        include_headers=False,
    ),
    "minimal": StyleConfig(
        style=OutputStyle.MINIMAL,
        include_headers=False,
        include_bullet_points=False,
        include_progress=False,
    ),
}


def get_formatter(style: str = "default") -> OutputFormatter:
    """Get formatter for style preset."""
    config = STYLE_PRESETS.get(style, StyleConfig())
    return OutputFormatter(config)


def format_output(content: str, style: str = "default") -> str:
    """Quick format output."""
    formatter = get_formatter(style)
    return formatter.format(content)


__all__ = [
    "OutputStyle",
    "StyleConfig",
    "OutputFormatter",
    "STYLE_PRESETS",
    "get_formatter",
    "format_output",
]
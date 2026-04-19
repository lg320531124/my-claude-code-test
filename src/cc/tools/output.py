"""Output Tool - Format and render output."""

from __future__ import annotations
import json
from typing import Any, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult, ToolUseContext


class OutputInput(BaseModel):
    """Input for OutputTool."""
    content: Any = Field(description="Content to format")
    format: str = Field(default="text", description="Output format: text, json, yaml, table, markdown")
    style: Optional[str] = Field(default=None, description="Style options")
    title: Optional[str] = Field(default=None, description="Optional title")


class OutputTool(ToolDef):
    """Tool for formatting output."""

    name = "Output"
    description = "Format and render output in various formats"
    input_schema = OutputInput

    async def execute(self, input: OutputInput, ctx: Optional[ToolUseContext] = None) -> ToolResult:
        """Execute output formatting."""
        content = input.content
        format_type = input.format

        if format_type == "text":
            return self._format_text(content, input.title)
        elif format_type == "json":
            return self._format_json(content)
        elif format_type == "yaml":
            return self._format_yaml(content)
        elif format_type == "table":
            return self._format_table(content, input.title)
        elif format_type == "markdown":
            return self._format_markdown(content, input.title, input.style)
        else:
            return ToolResult(
                content=f"Unknown format: {format_type}",
                is_error=True
            )

    def _format_text(self, content: Any, title: Optional[str] = None) -> ToolResult:
        """Format as plain text."""
        lines = []

        if title:
            lines.append(f"=== {title} ===")
            lines.append("")

        if isinstance(content, str):
            lines.append(content)
        elif isinstance(content, (dict, list)):
            lines.append(json.dumps(content, indent=2))
        else:
            lines.append(str(content))

        return ToolResult(
            content="\n".join(lines),
            metadata={"format": "text"}
        )

    def _format_json(self, content: Any) -> ToolResult:
        """Format as JSON."""
        try:
            output = json.dumps(content, indent=2, ensure_ascii=False)
            return ToolResult(
                content=output,
                metadata={"format": "json"}
            )
        except Exception as e:
            return ToolResult(
                content=f"JSON formatting error: {str(e)}",
                is_error=True
            )

    def _format_yaml(self, content: Any) -> ToolResult:
        """Format as YAML (simplified)."""
        # Simple YAML-like formatting without full YAML support
        lines = []

        if isinstance(content, dict):
            for key, value in content.items():
                if isinstance(value, dict):
                    lines.append(f"{key}:")
                    for k, v in value.items():
                        lines.append(f"  {k}: {self._yaml_value(v)}")
                elif isinstance(value, list):
                    lines.append(f"{key}:")
                    for item in value:
                        lines.append(f"  - {self._yaml_value(item)}")
                else:
                    lines.append(f"{key}: {self._yaml_value(value)}")
        elif isinstance(content, list):
            for item in content:
                lines.append(f"- {self._yaml_value(item)}")
        else:
            lines.append(self._yaml_value(content))

        return ToolResult(
            content="\n".join(lines),
            metadata={"format": "yaml"}
        )

    def _yaml_value(self, value: Any) -> str:
        """Format YAML value."""
        if isinstance(value, str):
            if value.startswith('"') or value.startswith("'"):
                return value
            return f'"{value}"'
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif value is None:
            return "null"
        else:
            return str(value)

    def _format_table(self, content: Any, title: Optional[str] = None) -> ToolResult:
        """Format as table."""
        lines = []

        if title:
            lines.append(f"=== {title} ===")
            lines.append("")

        if isinstance(content, list) and content:
            if isinstance(content[0], dict):
                # Dict list table
                headers = list(content[0].keys())
                lines.append(" | ".join(headers))
                lines.append("-" * len(" | ".join(headers)))

                for row in content:
                    values = [str(row.get(h, "")) for h in headers]
                    lines.append(" | ".join(values))
            else:
                # Simple list table
                lines.append("Value")
                lines.append("-" * 10)
                for item in content:
                    lines.append(str(item))
        elif isinstance(content, dict):
            # Dict table
            lines.append("Key | Value")
            lines.append("-" * 20)
            for key, value in content.items():
                lines.append(f"{key} | {value}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"format": "table"}
        )

    def _format_markdown(self, content: Any, title: Optional[str] = None, style: Optional[str] = None) -> ToolResult:
        """Format as Markdown."""
        lines = []

        if title:
            level = int(style or "1") if style and style.isdigit() else 1
            lines.append(f"{'#' * level} {title}")
            lines.append("")

        if isinstance(content, str):
            lines.append(content)
        elif isinstance(content, list):
            if style == "bullets":
                for item in content:
                    lines.append(f"- {item}")
            elif style == "numbers":
                for i, item in enumerate(content, 1):
                    lines.append(f"{i}. {item}")
            else:
                lines.append(json.dumps(content, indent=2))
        elif isinstance(content, dict):
            lines.append("```json")
            lines.append(json.dumps(content, indent=2))
            lines.append("```")
        else:
            lines.append(str(content))

        return ToolResult(
            content="\n".join(lines),
            metadata={"format": "markdown", "style": style}
        )


__all__ = ["OutputTool", "OutputInput"]
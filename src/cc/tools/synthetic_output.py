"""Synthetic Output Tool - Generate synthetic responses."""

from __future__ import annotations
import json
import time
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult, ToolUseContext


class SyntheticInput(BaseModel):
    """Input for SyntheticOutputTool."""
    type: str = Field(description="Output type: text, code, json, markdown, error")
    content: Optional[str] = Field(default=None, description="Base content to synthesize")
    template: Optional[str] = Field(default=None, description="Template to use")
    params: Optional[Dict[str, Any]] = Field(default=None, description="Parameters for synthesis")


class SyntheticOutputTool(ToolDef):
    """Tool for generating synthetic outputs."""

    name = "SyntheticOutput"
    description = "Generate synthetic outputs for testing and demonstrations"
    input_schema = SyntheticInput

    _templates: Dict[str, str] = {
        "code_python": "def {name}():\n    {body}\n    return {result}",
        "code_typescript": "function {name}(): {type} {\n  {body}\n  return {result};\n}",
        "json_response": '{"status": "{status}", "data": {data}, "message": "{message}"}',
        "markdown_header": "# {title}\n\n{content}",
        "error_generic": "Error: {error_type} - {message}",
        "success_message": "Success: {action} completed in {duration}",
    }

    async def execute(self, input: SyntheticInput, ctx: Optional[ToolUseContext] = None) -> ToolResult:
        """Execute synthetic output generation."""
        output_type = input.type

        if output_type == "text":
            return self._generate_text(input)
        elif output_type == "code":
            return self._generate_code(input)
        elif output_type == "json":
            return self._generate_json(input)
        elif output_type == "markdown":
            return self._generate_markdown(input)
        elif output_type == "error":
            return self._generate_error(input)
        else:
            return ToolResult(
                content=f"Unknown output type: {output_type}",
                is_error=True
            )

    def _generate_text(self, input: SyntheticInput) -> ToolResult:
        """Generate synthetic text."""
        content = input.content or "Sample synthetic text output"
        params = input.params or {}

        # Apply transformations
        if params.get("uppercase"):
            content = content.upper()
        if params.get("lowercase"):
            content = content.lower()
        if params.get("prefix"):
            content = f"{params['prefix']} {content}"
        if params.get("suffix"):
            content = f"{content} {params['suffix']}"

        return ToolResult(
            content=content,
            metadata={"type": "text", "params": params}
        )

    def _generate_code(self, input: SyntheticInput) -> ToolResult:
        """Generate synthetic code."""
        params = input.params or {}
        language = params.get("language", "python")
        template_key = f"code_{language}"

        template = self._templates.get(template_key, self._templates["code_python"])

        code = template.format(
            name=params.get("name", "example_function"),
            body=params.get("body", "# implementation"),
            result=params.get("result", "None"),
            type=params.get("return_type", "any"),
        )

        return ToolResult(
            content=code,
            metadata={"type": "code", "language": language}
        )

    def _generate_json(self, input: SyntheticInput) -> ToolResult:
        """Generate synthetic JSON."""
        params = input.params or {}
        template = self._templates.get("json_response", '{"status": "ok"}')

        # Create JSON structure
        data = {
            "status": params.get("status", "success"),
            "timestamp": time.time(),
            "data": params.get("data", {}),
            "message": params.get("message", "Synthetic JSON response"),
        }

        if input.content:
            data["content"] = input.content

        return ToolResult(
            content=json.dumps(data, indent=2),
            metadata={"type": "json"}
        )

    def _generate_markdown(self, input: SyntheticInput) -> ToolResult:
        """Generate synthetic markdown."""
        params = input.params or {}
        template = self._templates.get("markdown_header", "# Title\n\nContent")

        markdown = template.format(
            title=params.get("title", "Example"),
            content=input.content or params.get("content", "Example content"),
        )

        # Add sections if specified
        sections = params.get("sections", [])
        for section in sections:
            markdown += f"\n\n## {section['title']}\n{section['content']}"

        return ToolResult(
            content=markdown,
            metadata={"type": "markdown"}
        )

    def _generate_error(self, input: SyntheticInput) -> ToolResult:
        """Generate synthetic error."""
        params = input.params or {}
        template = self._templates.get("error_generic", "Error occurred")

        error_msg = template.format(
            error_type=params.get("error_type", "GenericError"),
            message=params.get("message", input.content or "An error occurred"),
        )

        return ToolResult(
            content=error_msg,
            is_error=True,
            metadata={"type": "error", "error_type": params.get("error_type")}
        )


__all__ = ["SyntheticOutputTool", "SyntheticInput"]
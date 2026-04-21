"""Template Tool - Template processing."""

from __future__ import annotations
from pathlib import Path
from typing import ClassVar, Dict, Optional, Any
from pydantic import Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class TemplateInput(ToolInput):
    """Input for TemplateTool."""
    action: str = Field(description="Action: render, save, load, list")
    template: Optional[str] = Field(default=None, description="Template content or path")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Variables for template")
    name: Optional[str] = Field(default=None, description="Template name for save/load")
    output_path: Optional[str] = Field(default=None, description="Output file path")


class TemplateTool(ToolDef):
    """Template processing."""

    name: ClassVar[str] = "Template"
    description: ClassVar[str] = "Process and render templates"
    input_schema: ClassVar[type] = TemplateInput

    # Stored templates
    _templates: Dict[str, str] = {}

    async def execute(self, input: TemplateInput, ctx: ToolUseContext) -> ToolResult:
        """Execute template operation."""
        action = input.action

        if action == "render":
            return self._render_template(input.template, input.variables)
        elif action == "save":
            return self._save_template(input.name, input.template)
        elif action == "load":
            return self._load_template(input.name)
        elif action == "list":
            return self._list_templates()
        elif action == "apply":
            return self._apply_to_file(input.template, input.variables, input.output_path, ctx)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _render_template(self, template: Optional[str], variables: Optional[Dict[str, Any]]) -> ToolResult:
        """Render template with variables."""
        if not template:
            return ToolResult(content="Template required", is_error=True)

        variables = variables or {}
        result = template

        # Simple variable substitution: {{var}}
        import re
        pattern = r'\{\{(\w+)\}\}'

        def replace(match):
            key = match.group(1)
            return str(variables.get(key, match.group(0)))

        result = re.sub(pattern, replace, result)

        # Also support ${var} style
        pattern = r'\$\{(\w+)\}'
        result = re.sub(pattern, replace, result)

        return ToolResult(
            content=result,
            metadata={"template": template, "variables": variables},
        )

    def _save_template(self, name: Optional[str], template: Optional[str]) -> ToolResult:
        """Save template."""
        if not name or not template:
            return ToolResult(content="Name and template required", is_error=True)

        self._templates[name] = template

        return ToolResult(
            content=f"Template '{name}' saved",
            metadata={"name": name, "length": len(template)},
        )

    def _load_template(self, name: Optional[str]) -> ToolResult:
        """Load template."""
        if not name:
            return ToolResult(content="Name required", is_error=True)

        if name not in self._templates:
            return ToolResult(content=f"Template '{name}' not found", is_error=True)

        return ToolResult(
            content=self._templates[name],
            metadata={"name": name},
        )

    def _list_templates(self) -> ToolResult:
        """List saved templates."""
        if not self._templates:
            return ToolResult(content="No templates saved")

        lines = []
        for name, template in self._templates.items():
            preview = template[:50] + "..." if len(template) > 50 else template
            lines.append(f"{name}: {preview}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"templates": list(self._templates.keys())},
        )

    def _apply_to_file(
        self,
        template: Optional[str],
        variables: Optional[Dict[str, Any]],
        output_path: Optional[str],
        ctx: ToolUseContext,
    ) -> ToolResult:
        """Apply template to file."""
        if not template or not output_path:
            return ToolResult(content="Template and output_path required", is_error=True)

        # Render template
        rendered = self._render_template(template, variables)
        if rendered.is_error:
            return rendered

        # Write to file
        path = Path(output_path)
        if not path.is_absolute():
            path = Path(ctx.cwd) / path

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(rendered.content)

        return ToolResult(
            content=f"Template applied to {path}",
            metadata={"path": str(path)},
        )


__all__ = ["TemplateTool", "TemplateInput"]
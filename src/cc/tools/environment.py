"""Environment Tool - Environment variable management."""

from __future__ import annotations
import os
from typing import ClassVar, Optional
from pydantic import Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class EnvironmentInput(ToolInput):
    """Input for EnvironmentTool."""
    action: str = Field(description="Action: get, set, list, unset, export")
    key: Optional[str] = Field(default=None, description="Environment variable key")
    value: Optional[str] = Field(default=None, description="Environment variable value")
    filter: Optional[str] = Field(default=None, description="Filter pattern")


class EnvironmentTool(ToolDef):
    """Manage environment variables."""

    name: ClassVar[str] = "Environment"
    description: ClassVar[str] = "Get, set, and manage environment variables"
    input_schema: ClassVar[type] = EnvironmentInput

    async def execute(self, input: EnvironmentInput, ctx: ToolUseContext) -> ToolResult:
        """Execute environment operation."""
        action = input.action

        if action == "get":
            return self._get_env(input.key)
        elif action == "set":
            return self._set_env(input.key, input.value)
        elif action == "list":
            return self._list_env(input.filter)
        elif action == "unset":
            return self._unset_env(input.key)
        elif action == "export":
            return self._export_env()
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _get_env(self, key: Optional[str]) -> ToolResult:
        """Get environment variable."""
        if not key:
            return ToolResult(
                content="Key required for get action",
                is_error=True,
            )

        value = os.environ.get(key)
        if value is None:
            return ToolResult(
                content=f"Environment variable not found: {key}",
                is_error=True,
            )

        return ToolResult(
            content=f"{key}={value}",
            metadata={"key": key, "value": value},
        )

    def _set_env(self, key: Optional[str], value: Optional[str]) -> ToolResult:
        """Set environment variable."""
        if not key or not value:
            return ToolResult(
                content="Key and value required for set action",
                is_error=True,
            )

        os.environ[key] = value
        return ToolResult(
            content=f"Set {key}={value}",
            metadata={"key": key, "value": value},
        )

    def _list_env(self, filter: Optional[str]) -> ToolResult:
        """List environment variables."""
        env_vars = dict(os.environ)

        if filter:
            env_vars = {
                k: v for k, v in env_vars.items()
                if filter.lower() in k.lower()
            }

        lines = []
        for key, value in sorted(env_vars.items()):
            # Mask sensitive values
            if any(s in key.upper() for s in ["KEY", "SECRET", "TOKEN", "PASSWORD", "API"]):
                value = "***" + value[-4:] if len(value) > 4 else "***"
            lines.append(f"{key}={value}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(env_vars)},
        )

    def _unset_env(self, key: Optional[str]) -> ToolResult:
        """Unset environment variable."""
        if not key:
            return ToolResult(
                content="Key required for unset action",
                is_error=True,
            )

        if key not in os.environ:
            return ToolResult(
                content=f"Environment variable not found: {key}",
                is_error=True,
            )

        del os.environ[key]
        return ToolResult(content=f"Unset {key}")

    def _export_env(self) -> ToolResult:
        """Export all environment variables."""
        import json
        env_vars = dict(os.environ)

        # Mask sensitive values
        for key in env_vars:
            if any(s in key.upper() for s in ["KEY", "SECRET", "TOKEN", "PASSWORD", "API"]):
                env_vars[key] = "***MASKED***"

        return ToolResult(
            content=json.dumps(env_vars, indent=2),
            metadata={"count": len(env_vars)},
        )


__all__ = ["EnvironmentTool", "EnvironmentInput"]
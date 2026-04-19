"""Config Tool - Manage configuration settings."""

from __future__ import annotations
import json
import os
from pathlib import Path
from typing import Any, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult, ToolUseContext


class ConfigInput(BaseModel):
    """Input for ConfigTool."""
    action: str = Field(description="Action: get, set, list, delete, reset")
    key: Optional[str] = Field(default=None, description="Configuration key")
    value: Optional[Any] = Field(default=None, description="Configuration value")
    scope: str = Field(default="project", description="Scope: project, user, global")


class ConfigTool(ToolDef):
    """Tool for managing configuration."""

    name = "Config"
    description = "Manage Claude Code configuration settings"
    input_schema = ConfigInput

    def __init__(self):
        self._config_paths = {
            "project": Path.cwd() / ".claude" / "settings.json",
            "user": Path.home() / ".claude" / "settings.json",
            "global": Path.home() / ".claude" / "settings.global.json",
        }

    async def execute(self, input: ConfigInput, ctx: Optional[ToolUseContext] = None) -> ToolResult:
        """Execute config operation."""
        action = input.action
        scope = input.scope
        config_path = self._config_paths.get(scope, self._config_paths["project"])

        if action == "get":
            return self._get_config(config_path, input.key)
        elif action == "set":
            return self._set_config(config_path, input.key, input.value)
        elif action == "list":
            return self._list_config(config_path)
        elif action == "delete":
            return self._delete_config(config_path, input.key)
        elif action == "reset":
            return self._reset_config(config_path)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True
            )

    def _get_config(self, path: Path, key: Optional[str]) -> ToolResult:
        """Get configuration value."""
        if not path.exists():
            return ToolResult(content="Configuration file not found")

        data = json.loads(path.read_text())

        if key is None:
            return ToolResult(content=json.dumps(data, indent=2))

        # Navigate nested keys
        keys = key.split(".")
        value = data
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return ToolResult(
                    content=f"Key not found: {key}",
                    is_error=True
                )

        return ToolResult(
            content=json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value),
            metadata={"key": key, "scope": str(path)}
        )

    def _set_config(self, path: Path, key: Optional[str], value: Optional[Any]) -> ToolResult:
        """Set configuration value."""
        if key is None or value is None:
            return ToolResult(
                content="Key and value required for set action",
                is_error=True
            )

        # Load or create config
        if path.exists():
            data = json.loads(path.read_text())
        else:
            data = {}

        # Navigate to nested location
        keys = key.split(".")
        target = data
        for k in keys[:-1]:
            if k not in target:
                target[k] = {}
            target = target[k]

        target[keys[-1]] = value

        # Save
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2))

        return ToolResult(
            content=f"Set {key} = {json.dumps(value)}",
            metadata={"key": key, "scope": str(path)}
        )

    def _list_config(self, path: Path) -> ToolResult:
        """List all configuration."""
        if not path.exists():
            return ToolResult(content="Configuration file not found")

        data = json.loads(path.read_text())
        lines = []
        for key, value in self._flatten_dict(data).items():
            lines.append(f"{key}: {json.dumps(value)}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"total_keys": len(lines)}
        )

    def _delete_config(self, path: Path, key: Optional[str]) -> ToolResult:
        """Delete configuration key."""
        if key is None:
            return ToolResult(
                content="Key required for delete action",
                is_error=True
            )

        if not path.exists():
            return ToolResult(
                content="Configuration file not found",
                is_error=True
            )

        data = json.loads(path.read_text())
        keys = key.split(".")
        target = data

        for k in keys[:-1]:
            if k not in target:
                return ToolResult(
                    content=f"Key not found: {key}",
                    is_error=True
                )
            target = target[k]

        if keys[-1] not in target:
            return ToolResult(
                content=f"Key not found: {key}",
                is_error=True
            )

        del target[keys[-1]]
        path.write_text(json.dumps(data, indent=2))

        return ToolResult(content=f"Deleted {key}")

    def _reset_config(self, path: Path) -> ToolResult:
        """Reset configuration to defaults."""
        defaults = {
            "api": {"model": "claude-opus-4-7"},
            "ui": {"theme": "dark"},
            "permissions": {"allow": [], "deny": []},
        }

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(defaults, indent=2))

        return ToolResult(
            content="Configuration reset to defaults",
            metadata={"scope": str(path)}
        )

    def _flatten_dict(self, d: dict, prefix: str = "") -> dict:
        """Flatten nested dictionary."""
        result = {}
        for key, value in d.items():
            full_key = f"{prefix}{key}" if prefix else key
            if isinstance(value, dict):
                result.update(self._flatten_dict(value, f"{full_key}."))
            else:
                result[full_key] = value
        return result


__all__ = ["ConfigTool", "ConfigInput"]
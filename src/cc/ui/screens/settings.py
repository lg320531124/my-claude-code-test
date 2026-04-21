"""Settings Screen - Settings management screen."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum


class SettingCategory(Enum):
    """Setting categories."""
    API = "api"
    UI = "ui"
    PERMISSIONS = "permissions"
    MCP = "mcp"
    HOOKS = "hooks"
    MEMORY = "memory"
    OUTPUT = "output"


@dataclass
class SettingItem:
    """Setting item."""
    key: str
    value: Any
    type: str  # "string", "number", "boolean", "choice"
    category: SettingCategory
    description: str = ""
    choices: List[str] = field(default_factory=list)
    default: Any = None
    editable: bool = True


class SettingsScreen:
    """Settings management screen."""

    def __init__(self):
        self._settings: Dict[str, SettingItem] = {}
        self._categories: Dict[SettingCategory, List[SettingItem]] = {}
        self._current_category: SettingCategory = SettingCategory.API
        self._change_callback: Optional[Callable] = None
        self._load_default_settings()

    def _load_default_settings(self) -> None:
        """Load default settings."""
        defaults = [
            # API settings
            SettingItem(
                key="api.model",
                value="claude-sonnet-4-6",
                type="choice",
                category=SettingCategory.API,
                description="Default model for API calls",
                choices=["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
            ),
            SettingItem(
                key="api.max_tokens",
                value=4096,
                type="number",
                category=SettingCategory.API,
                description="Maximum tokens per response",
                default=4096,
            ),
            SettingItem(
                key="api.timeout",
                value=120,
                type="number",
                category=SettingCategory.API,
                description="API request timeout in seconds",
                default=120,
            ),

            # UI settings
            SettingItem(
                key="ui.theme",
                value="dark",
                type="choice",
                category=SettingCategory.UI,
                description="UI theme",
                choices=["dark", "light", "monochrome", "ansi"],
            ),
            SettingItem(
                key="ui.vim_mode",
                value=False,
                type="boolean",
                category=SettingCategory.UI,
                description="Enable vim editing mode",
                default=False,
            ),
            SettingItem(
                key="ui.show_tokens",
                value=True,
                type="boolean",
                category=SettingCategory.UI,
                description="Show token usage in status line",
                default=True,
            ),

            # Permissions
            SettingItem(
                key="permissions.mode",
                value="ask",
                type="choice",
                category=SettingCategory.PERMISSIONS,
                description="Permission mode",
                choices=["ask", "auto_approve", "strict"],
            ),
            SettingItem(
                key="permissions.auto_approve_readonly",
                value=True,
                type="boolean",
                category=SettingCategory.PERMISSIONS,
                description="Auto-approve read-only commands",
                default=True,
            ),

            # MCP
            SettingItem(
                key="mcp.enabled",
                value=True,
                type="boolean",
                category=SettingCategory.MCP,
                description="Enable MCP server integration",
                default=True,
            ),
            SettingItem(
                key="mcp.auto_approve",
                value=False,
                type="boolean",
                category=SettingCategory.MCP,
                description="Auto-approve MCP tool calls",
                default=False,
            ),

            # Hooks
            SettingItem(
                key="hooks.enabled",
                value=True,
                type="boolean",
                category=SettingCategory.HOOKS,
                description="Enable hooks system",
                default=True,
            ),

            # Memory
            SettingItem(
                key="memory.enabled",
                value=True,
                type="boolean",
                category=SettingCategory.MEMORY,
                description="Enable session memory",
                default=True,
            ),
            SettingItem(
                key="memory.max_entries",
                value=100,
                type="number",
                category=SettingCategory.MEMORY,
                description="Maximum memory entries",
                default=100,
            ),

            # Output
            SettingItem(
                key="output.style",
                value="explanatory",
                type="choice",
                category=SettingCategory.OUTPUT,
                description="Output style",
                choices=["explanatory", "concise", "technical"],
            ),
            SettingItem(
                key="output.show_thinking",
                value=False,
                type="boolean",
                category=SettingCategory.OUTPUT,
                description="Show extended thinking",
                default=False,
            ),
        ]

        for item in defaults:
            self._settings[item.key] = item

            if item.category not in self._categories:
                self._categories[item.category] = []
            self._categories[item.category].append(item)

    def get_categories(self) -> List[SettingCategory]:
        """Get all categories."""
        return list(self._categories.keys())

    def get_settings(self, category: SettingCategory = None) -> List[SettingItem]:
        """Get settings.

        Args:
            category: Optional category filter

        Returns:
            List of SettingItem
        """
        if category:
            return self._categories.get(category, [])
        return list(self._settings.values())

    def get_setting(self, key: str) -> Optional[SettingItem]:
        """Get specific setting.

        Args:
            key: Setting key

        Returns:
            SettingItem or None
        """
        return self._settings.get(key)

    def get_value(self, key: str) -> Any:
        """Get setting value.

        Args:
            key: Setting key

        Returns:
            Setting value
        """
        item = self._settings.get(key)
        return item.value if item else None

    async def set_value(self, key: str, value: Any) -> bool:
        """Set setting value.

        Args:
            key: Setting key
            value: New value

        Returns:
            True if set
        """
        item = self._settings.get(key)
        if not item or not item.editable:
            return False

        # Validate value
        if item.type == "boolean":
            if isinstance(value, str):
                value = value.lower() in ("true", "yes", "1", "on")
            else:
                value = bool(value)

        elif item.type == "number":
            try:
                value = float(value) if "." in str(value) else int(value)
            except ValueError:
                return False

        elif item.type == "choice":
            if value not in item.choices:
                return False

        item.value = value

        # Notify callback
        if self._change_callback:
            try:
                if asyncio.iscoroutinefunction(self._change_callback):
                    await self._change_callback(key, value)
                else:
                    self._change_callback(key, value)
            except Exception:
                pass

        return True

    def set_category(self, category: SettingCategory) -> None:
        """Set current category."""
        self._current_category = category

    def get_current_category(self) -> SettingCategory:
        """Get current category."""
        return self._current_category

    def set_change_callback(self, callback: Callable) -> None:
        """Set change callback."""
        self._change_callback = callback

    def reset(self, key: str) -> bool:
        """Reset setting to default.

        Args:
            key: Setting key

        Returns:
            True if reset
        """
        item = self._settings.get(key)
        if item and item.default is not None:
            item.value = item.default
            return True
        return False

    def reset_all(self) -> None:
        """Reset all settings to defaults."""
        for item in self._settings.values():
            if item.default is not None:
                item.value = item.default

    def export(self) -> Dict[str, Any]:
        """Export settings to dict."""
        return {key: item.value for key, item in self._settings.items()}

    def import_settings(self, data: Dict[str, Any]) -> int:
        """Import settings from dict.

        Args:
            data: Settings dict

        Returns:
            Number of settings imported
        """
        count = 0
        for key, value in data.items():
            if key in self._settings:
                item = self._settings[key]
                item.value = value
                count += 1
        return count


__all__ = [
    "SettingCategory",
    "SettingItem",
    "SettingsScreen",
]

"""User Preferences Service - Manage user preferences."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class PreferenceCategory(Enum):
    """Preference categories."""
    UI = "ui"
    BEHAVIOR = "behavior"
    OUTPUT = "output"
    TOOLS = "tools"
    MODEL = "model"
    NETWORK = "network"
    STORAGE = "storage"


@dataclass
class Preference:
    """User preference."""
    key: str
    value: Any
    category: PreferenceCategory
    description: str = ""
    editable: bool = True
    default: Any = None


@dataclass
class PreferencesConfig:
    """Preferences configuration."""
    storage_path: Optional[Path] = None
    auto_save: bool = True
    sync_enabled: bool = False
    defaults: Dict[str, Any] = field(default_factory=dict)


class UserPreferences:
    """User preferences manager."""

    # Default preferences
    DEFAULTS: Dict[str, Preference] = {
        "theme": Preference(
            key="theme",
            value="default",
            category=PreferenceCategory.UI,
            description="UI theme",
        ),
        "model": Preference(
            key="model",
            value="claude-sonnet-4-6",
            category=PreferenceCategory.MODEL,
            description="Default model",
        ),
        "vim_mode": Preference(
            key="vim_mode",
            value=False,
            category=PreferenceCategory.BEHAVIOR,
            description="Enable vim keybindings",
        ),
        "auto_compact": Preference(
            key="auto_compact",
            value=True,
            category=PreferenceCategory.BEHAVIOR,
            description="Auto compact context",
        ),
        "show_token_count": Preference(
            key="show_token_count",
            value=True,
            category=PreferenceCategory.UI,
            description="Show token count in status",
        ),
        "show_thinking": Preference(
            key="show_thinking",
            value=False,
            category=PreferenceCategory.OUTPUT,
            description="Show extended thinking",
        ),
        "output_format": Preference(
            key="output_format",
            value="markdown",
            category=PreferenceCategory.OUTPUT,
            description="Output format",
        ),
        "tool_permission_mode": Preference(
            key="tool_permission_mode",
            value="ask",
            category=PreferenceCategory.TOOLS,
            description="Tool permission mode",
        ),
        "bash_sandbox": Preference(
            key="bash_sandbox",
            value=True,
            category=PreferenceCategory.TOOLS,
            description="Enable bash sandbox",
        ),
        "max_concurrent_tools": Preference(
            key="max_concurrent_tools",
            value=5,
            category=PreferenceCategory.TOOLS,
            description="Max concurrent tool calls",
        ),
    }

    def __init__(self, config: Optional[PreferencesConfig] = None):
        self.config = config or PreferencesConfig()
        self._preferences: Dict[str, Any] = {}
        self._callbacks: Dict[str, List[callable]] = {}

        # Load defaults
        self._load_defaults()

        # Load saved preferences
        if self.config.storage_path:
            self._load_from_file()

    def _load_defaults(self) -> None:
        """Load default preferences."""
        for key, pref in self.DEFAULTS.items():
            self._preferences[key] = pref.value

    def _load_from_file(self) -> None:
        """Load preferences from file."""
        if not self.config.storage_path:
            return

        path = self.config.storage_path

        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._preferences.update(data)
                logger.info(f"Loaded preferences from {path}")
            except Exception as e:
                logger.error(f"Failed to load preferences: {e}")

    async def save(self) -> None:
        """Save preferences to file."""
        if not self.config.storage_path:
            return

        path = self.config.storage_path

        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self._preferences, indent=2))
            logger.info(f"Saved preferences to {path}")
        except Exception as e:
            logger.error(f"Failed to save preferences: {e}")

    async def get(self, key: str) -> Any:
        """Get preference value."""
        return self._preferences.get(key)

    async def set(
        self,
        key: str,
        value: Any
    ) -> bool:
        """Set preference value."""
        if key not in self.DEFAULTS:
            # Unknown preference
            self._preferences[key] = value
        else:
            pref = self.DEFAULTS[key]
            if not pref.editable:
                logger.warning(f"Preference {key} is not editable")
                return False

            self._preferences[key] = value

        # Notify callbacks
        await self._notify_change(key, value)

        # Auto save
        if self.config.auto_save:
            await self.save()

        return True

    async def _notify_change(
        self,
        key: str,
        value: Any
    ) -> None:
        """Notify preference change."""
        callbacks = self._callbacks.get(key, [])

        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(key, value)
                else:
                    callback(key, value)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def get_all(self) -> Dict[str, Any]:
        """Get all preferences."""
        return self._preferences.copy()

    async def get_by_category(
        self,
        category: PreferenceCategory
    ) -> Dict[str, Any]:
        """Get preferences by category."""
        return {
            key: value
            for key, value in self._preferences.items()
            if key in self.DEFAULTS and self.DEFAULTS[key].category == category
        }

    async def reset(self, key: str) -> bool:
        """Reset preference to default."""
        if key not in self.DEFAULTS:
            return False

        default_value = self.DEFAULTS[key].default or self.DEFAULTS[key].value
        await self.set(key, default_value)
        return True

    async def reset_all(self) -> None:
        """Reset all preferences to defaults."""
        for key, pref in self.DEFAULTS.items():
            self._preferences[key] = pref.default or pref.value

        if self.config.auto_save:
            await self.save()

    def register_callback(
        self,
        key: str,
        callback: callable
    ) -> None:
        """Register preference change callback."""
        if key not in self._callbacks:
            self._callbacks[key] = []

        self._callbacks[key].append(callback)

    async def get_preference_info(
        self,
        key: str
    ) -> Optional[Preference]:
        """Get preference metadata."""
        return self.DEFAULTS.get(key)

    async def list_preferences(self) -> List[Preference]:
        """List all preferences."""
        return list(self.DEFAULTS.values())

    async def export(self) -> str:
        """Export preferences as JSON."""
        return json.dumps(self._preferences, indent=2)

    async def import_prefs(
        self,
        data: str
    ) -> int:
        """Import preferences from JSON."""
        try:
            prefs = json.loads(data)
            count = 0

            for key, value in prefs.items():
                if await self.set(key, value):
                    count += 1

            return count
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return 0


__all__ = [
    "PreferenceCategory",
    "Preference",
    "PreferencesConfig",
    "UserPreferences",
]
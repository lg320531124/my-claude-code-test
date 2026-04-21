"""Config Manager - Manage application configuration."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class ConfigSource(Enum):
    """Configuration sources."""
    DEFAULT = "default"
    FILE = "file"
    ENV = "env"
    CLI = "cli"
    USER = "user"
    PROJECT = "project"


class ConfigPriority(Enum):
    """Configuration priority."""
    LOWEST = 0
    LOW = 25
    NORMAL = 50
    HIGH = 75
    HIGHEST = 100


@dataclass
class ConfigEntry:
    """Configuration entry."""
    key: str
    value: Any
    source: ConfigSource
    priority: ConfigPriority
    timestamp: datetime
    description: str = ""
    editable: bool = True
    validators: List[callable] = field(default_factory=list)


@dataclass
class ConfigManagerConfig:
    """Config manager configuration."""
    config_path: Optional[Path] = None
    env_prefix: str = "CC_"
    auto_reload: bool = False
    reload_interval: float = 5.0
    validate_on_load: bool = True
    max_entries: int = 500


class ConfigManager:
    """Manage application configuration."""

    # Default configuration
    DEFAULTS: Dict[str, Any] = {
        "model": "claude-sonnet-4-6",
        "theme": "default",
        "vim_mode": False,
        "output_format": "markdown",
        "show_tokens": True,
        "show_thinking": False,
        "auto_compact": True,
        "max_history": 100,
        "max_tokens": 200000,
        "timeout": 120.0,
        "retry_limit": 3,
        "sandbox_enabled": True,
        "permission_mode": "ask",
    }

    def __init__(self, config: Optional[ConfigManagerConfig] = None):
        self.config = config or ConfigManagerConfig()
        self._entries: Dict[str, ConfigEntry] = {}
        self._watchers: Dict[str, List[callable]] = {}
        self._last_reload: float = 0.0

        # Load defaults
        self._load_defaults()

        # Load from file
        if self.config.config_path:
            self._load_from_file()

        # Load from environment
        self._load_from_env()

    def _load_defaults(self) -> None:
        """Load default configuration."""
        import time

        for key, value in self.DEFAULTS.items():
            entry = ConfigEntry(
                key=key,
                value=value,
                source=ConfigSource.DEFAULT,
                priority=ConfigPriority.LOWEST,
                timestamp=datetime.now(),
            )

            self._entries[key] = entry

    def _load_from_file(self) -> None:
        """Load configuration from file."""
        if not self.config.config_path:
            return

        path = self.config.config_path

        if not path.exists():
            return

        try:
            data = json.loads(path.read_text())

            for key, value in data.items():
                entry = ConfigEntry(
                    key=key,
                    value=value,
                    source=ConfigSource.FILE,
                    priority=ConfigPriority.NORMAL,
                    timestamp=datetime.now(),
                )

                self._entries[key] = entry

            logger.info(f"Loaded config from {path}")
        except Exception as e:
            logger.error(f"Failed to load config: {e}")

    def _load_from_env(self) -> None:
        """Load configuration from environment."""
        import os

        for key, value in os.environ.items():
            if key.startswith(self.config.env_prefix):
                config_key = key[len(self.config.env_prefix):].lower()

                entry = ConfigEntry(
                    key=config_key,
                    value=value,
                    source=ConfigSource.ENV,
                    priority=ConfigPriority.HIGH,
                    timestamp=datetime.now(),
                )

                self._entries[config_key] = entry

    async def get(
        self,
        key: str,
        default: Any = None
    ) -> Any:
        """Get configuration value."""
        if key not in self._entries:
            return default

        return self._entries[key].value

    async def set(
        self,
        key: str,
        value: Any,
        source: ConfigSource = ConfigSource.USER,
        priority: ConfigPriority = ConfigPriority.NORMAL
    ) -> bool:
        """Set configuration value."""
        # Check if can override
        if key in self._entries:
            existing = self._entries[key]
            if existing.priority.value > priority.value and existing.source != ConfigSource.DEFAULT:
                return False

        old_value = await self.get(key)

        entry = ConfigEntry(
            key=key,
            value=value,
            source=source,
            priority=priority,
            timestamp=datetime.now(),
        )

        self._entries[key] = entry

        # Notify watchers
        await self._notify_watchers(key, old_value, value)

        # Save if file source
        if source == ConfigSource.USER and self.config.config_path:
            await self._save_to_file()

        return True

    async def _save_to_file(self) -> None:
        """Save configuration to file."""
        if not self.config.config_path:
            return

        path = self.config.config_path

        try:
            # Filter file-persistent entries
            data = {
                key: entry.value
                for key, entry in self._entries.items()
                if entry.source in [ConfigSource.FILE, ConfigSource.USER, ConfigSource.DEFAULT]
            }

            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=2))
            logger.info(f"Saved config to {path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    async def _notify_watchers(
        self,
        key: str,
        old_value: Any,
        new_value: Any
    ) -> None:
        """Notify watchers."""
        watchers = self._watchers.get(key, [])

        for watcher in watchers:
            try:
                if asyncio.iscoroutinefunction(watcher):
                    await watcher(key, old_value, new_value)
                else:
                    watcher(key, old_value, new_value)
            except Exception as e:
                logger.error(f"Watcher error: {e}")

    async def delete(
        self,
        key: str
    ) -> bool:
        """Delete configuration entry."""
        if key not in self._entries:
            return False

        old_value = self._entries[key].value
        del self._entries[key]

        # Notify watchers
        await self._notify_watchers(key, old_value, None)

        return True

    async def get_all(self) -> Dict[str, Any]:
        """Get all configuration."""
        return {
            key: entry.value
            for key, entry in self._entries.items()
        }

    async def get_by_source(
        self,
        source: ConfigSource
    ) -> Dict[str, Any]:
        """Get configuration by source."""
        return {
            key: entry.value
            for key, entry in self._entries.items()
            if entry.source == source
        }

    async def reset(
        self,
        key: str
    ) -> bool:
        """Reset to default."""
        if key not in self.DEFAULTS:
            return False

        # Force override for reset
        old_value = await self.get(key)

        entry = ConfigEntry(
            key=key,
            value=self.DEFAULTS[key],
            source=ConfigSource.DEFAULT,
            priority=ConfigPriority.LOWEST,
            timestamp=datetime.now(),
        )

        self._entries[key] = entry

        # Notify watchers
        await self._notify_watchers(key, old_value, self.DEFAULTS[key])

        return True

    async def reset_all(self) -> None:
        """Reset all to defaults."""
        for key in self.DEFAULTS:
            await self.reset(key)

    async def watch(
        self,
        key: str,
        callback: callable
    ) -> None:
        """Watch configuration key."""
        if key not in self._watchers:
            self._watchers[key] = []

        self._watchers[key].append(callback)

    async def unwatch(
        self,
        key: str,
        callback: callable
    ) -> bool:
        """Unwatch configuration key."""
        if key not in self._watchers:
            return False

        try:
            self._watchers[key].remove(callback)
            return True
        except ValueError:
            return False

    async def validate(
        self,
        key: str,
        value: Any
    ) -> bool:
        """Validate configuration value."""
        if key not in self._entries:
            return True

        entry = self._entries[key]

        for validator in entry.validators:
            try:
                if not validator(value):
                    return False
            except Exception:
                return False

        return True

    async def add_validator(
        self,
        key: str,
        validator: callable
    ) -> bool:
        """Add validator."""
        if key not in self._entries:
            return False

        self._entries[key].validators.append(validator)
        return True

    async def reload(self) -> int:
        """Reload configuration."""
        self._load_from_file()
        self._load_from_env()

        self._last_reload = asyncio.get_event_loop().time()
        return len(self._entries)

    async def export(self) -> str:
        """Export configuration."""
        return json.dumps(await self.get_all(), indent=2)

    async def import_config(
        self,
        data: str
    ) -> int:
        """Import configuration."""
        try:
            parsed = json.loads(data)

            count = 0

            for key, value in parsed.items():
                if await self.set(key, value):
                    count += 1

            return count
        except Exception as e:
            logger.error(f"Import error: {e}")
            return 0

    async def get_stats(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        by_source: Dict[str, int] = {}

        for entry in self._entries.values():
            key = entry.source.value
            by_source[key] = by_source.get(key, 0) + 1

        return {
            "total_entries": len(self._entries),
            "by_source": by_source,
            "config_path": str(self.config.config_path) if self.config.config_path else None,
        }


__all__ = [
    "ConfigSource",
    "ConfigPriority",
    "ConfigEntry",
    "ConfigManagerConfig",
    "ConfigManager",
]
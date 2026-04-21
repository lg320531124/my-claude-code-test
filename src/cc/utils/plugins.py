"""Plugins - Plugin loading and management."""

from __future__ import annotations
import importlib
import json
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ..utils.log import get_logger

logger = get_logger(__name__)


class PluginStatus(Enum):
    """Plugin status."""
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"
    PENDING = "pending"


class PluginType(Enum):
    """Plugin types."""
    TOOL = "tool"
    SERVICE = "service"
    COMMAND = "command"
    HOOK = "hook"
    UI = "ui"


@dataclass
class PluginInfo:
    """Plugin information."""
    name: str
    version: str
    type: PluginType
    path: Path
    status: PluginStatus = PluginStatus.PENDING
    dependencies: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PluginConfig:
    """Plugin configuration."""
    enabled: bool = True
    priority: int = 0
    settings: Dict[str, Any] = field(default_factory=dict)


class PluginManager:
    """Manage plugin loading and lifecycle."""

    def __init__(self, plugin_dir: Optional[Path] = None):
        self.plugin_dir = plugin_dir or Path.home() / ".claude" / "plugins"
        self._plugins: Dict[str, PluginInfo] = {}
        self._configs: Dict[str, PluginConfig] = {}
        self._hooks: Dict[str, List[Callable]] = {}

    async def discover(self) -> List[PluginInfo]:
        """Discover available plugins."""
        discovered = []

        if not self.plugin_dir.exists():
            return discovered

        for plugin_path in self.plugin_dir.iterdir():
            if plugin_path.is_dir():
                manifest = plugin_path / "manifest.json"

                if manifest.exists():
                    try:
                        data = json.loads(manifest.read_text())

                        info = PluginInfo(
                            name=data.get("name", plugin_path.name),
                            version=data.get("version", "0.0.0"),
                            type=PluginType(data.get("type", "tool")),
                            path=plugin_path,
                            dependencies=data.get("dependencies", []),
                            capabilities=data.get("capabilities", []),
                            metadata=data,
                        )

                        self._plugins[info.name] = info
                        discovered.append(info)

                    except Exception as e:
                        logger.error(f"Failed to parse manifest: {e}")

        return discovered

    async def load(self, name: str) -> bool:
        """Load plugin."""
        info = self._plugins.get(name)
        if not info:
            return False

        try:
            # Import plugin module
            module_path = info.path / "main.py"

            if module_path.exists():
                spec = importlib.util.spec_from_file_location(
                    f"plugin_{name}",
                    module_path
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                # Initialize plugin
                if hasattr(module, "initialize"):
                    await module.initialize(self._configs.get(name, PluginConfig()))

                info.status = PluginStatus.LOADED
                logger.info(f"Loaded plugin: {name}")
                return True

        except Exception as e:
            info.status = PluginStatus.ERROR
            logger.error(f"Failed to load plugin {name}: {e}")
            return False

        return False

    async def enable(self, name: str) -> bool:
        """Enable plugin."""
        info = self._plugins.get(name)
        if not info:
            return False

        if info.status != PluginStatus.LOADED:
            # Try to load first
            if not await self.load(name):
                return False

        info.status = PluginStatus.ENABLED
        self._configs[name] = PluginConfig(enabled=True)

        # Register hooks
        self._register_hooks(name)

        logger.info(f"Enabled plugin: {name}")
        return True

    async def disable(self, name: str) -> bool:
        """Disable plugin."""
        info = self._plugins.get(name)
        if not info:
            return False

        info.status = PluginStatus.DISABLED
        self._configs[name] = PluginConfig(enabled=False)

        # Unregister hooks
        self._unregister_hooks(name)

        logger.info(f"Disabled plugin: {name}")
        return True

    async def unload(self, name: str) -> bool:
        """Unload plugin."""
        info = self._plugins.get(name)
        if not info:
            return False

        # Disable first
        await self.disable(name)

        info.status = PluginStatus.PENDING
        logger.info(f"Unloaded plugin: {name}")
        return True

    def _register_hooks(self, name: str) -> None:
        """Register plugin hooks."""
        # Would register actual hooks in production
        self._hooks[name] = []

    def _unregister_hooks(self, name: str) -> None:
        """Unregister plugin hooks."""
        if name in self._hooks:
            del self._hooks[name]

    async def get_plugin(self, name: str) -> Optional[PluginInfo]:
        """Get plugin info."""
        return self._plugins.get(name)

    async def list_plugins(
        self,
        status: Optional[PluginStatus] = None
    ) -> List[PluginInfo]:
        """List plugins."""
        plugins = list(self._plugins.values())

        if status:
            plugins = [p for p in plugins if p.status == status]

        return plugins

    async def reload(self, name: str) -> bool:
        """Reload plugin."""
        await self.unload(name)
        return await self.load(name)

    async def load_all(self) -> Dict[str, bool]:
        """Load all discovered plugins."""
        results = {}

        for name in self._plugins:
            results[name] = await self.load(name)

        return results

    async def enable_all(self) -> Dict[str, bool]:
        """Enable all loaded plugins."""
        results = {}

        for name, info in self._plugins.items():
            if info.status == PluginStatus.LOADED:
                results[name] = await self.enable(name)

        return results

    def get_config(self, name: str) -> Optional[PluginConfig]:
        """Get plugin config."""
        return self._configs.get(name)

    def set_config(self, name: str, config: PluginConfig) -> None:
        """Set plugin config."""
        self._configs[name] = config

    async def install(
        self,
        source: str,
        name: Optional[str] = None
    ) -> Optional[PluginInfo]:
        """Install plugin from source."""
        # Simulate installation
        plugin_path = self.plugin_dir / (name or Path(source).name)

        plugin_path.mkdir(parents=True, exist_ok=True)

        info = PluginInfo(
            name=name or Path(source).name,
            version="1.0.0",
            type=PluginType.TOOL,
            path=plugin_path,
            status=PluginStatus.PENDING,
        )

        self._plugins[info.name] = info
        logger.info(f"Installed plugin: {info.name}")
        return info

    async def uninstall(self, name: str) -> bool:
        """Uninstall plugin."""
        info = self._plugins.get(name)
        if not info:
            return False

        await self.unload(name)

        # Remove directory
        if info.path.exists():
            import shutil
            shutil.rmtree(info.path)

        del self._plugins[name]
        if name in self._configs:
            del self._configs[name]

        logger.info(f"Uninstalled plugin: {name}")
        return True


__all__ = [
    "PluginStatus",
    "PluginType",
    "PluginInfo",
    "PluginConfig",
    "PluginManager",
]
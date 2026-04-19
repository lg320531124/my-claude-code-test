"""Plugin System - Load and manage plugins."""

from __future__ import annotations
import asyncio
import json
import importlib
import time
from pathlib import Path
from typing import ClassVar, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class PluginState(Enum):
    """Plugin state."""
    UNLOADED = "unloaded"
    LOADING = "loading"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Plugin metadata."""
    name: str
    version: str = "1.0"
    author: str = ""
    description: str = ""
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    priority: int = 0


@dataclass
class PluginInfo:
    """Complete plugin info."""
    metadata: PluginMetadata
    path: Path
    state: PluginState = PluginState.UNLOADED
    loaded_at: Optional[float] = None
    error: Optional[str] = None


class PluginBase:
    """Base class for plugins."""

    metadata: ClassVar[PluginMetadata]

    def __init__(self):
        self._hooks: Dict[str, List[Callable]] = {}

    async def on_load(self) -> None:
        """Called when plugin is loaded."""
        pass

    async def on_unload(self) -> None:
        """Called when plugin is unloaded."""
        pass

    def register_hook(self, event: str, callback: Callable) -> None:
        """Register event hook."""
        if event not in self._hooks:
            self._hooks[event] = []
        self._hooks[event].append(callback)

    def unregister_hook(self, event: str, callback: Callable) -> None:
        """Unregister event hook."""
        if event in self._hooks:
            self._hooks[event] = [
                c for c in self._hooks[event] if c != callback
            ]

    def get_hooks(self, event: str) -> List[Callable]:
        """Get hooks for event."""
        return self._hooks.get(event, [])

    def add_tool(self, tool: Any) -> None:
        """Add tool to system."""
        # This would integrate with tool system
        pass

    def add_command(self, name: str, handler: Callable) -> None:
        """Add command to system."""
        # This would integrate with command system
        pass


class PluginLoader:
    """Load and validate plugins."""

    def __init__(self, plugin_dirs: Optional[List[Path]] = None):
        self.plugin_dirs = plugin_dirs or [
            Path.cwd() / ".claude" / "plugins",
            Path.home() / ".claude" / "plugins",
        ]
        self.plugins: Dict[str, PluginInfo] = {}
        self._instances: Dict[str, PluginBase] = {}
        self._errors: List[dict] = []

    async def discover(self) -> Dict[str, PluginInfo]:
        """Discover available plugins."""
        for plugin_dir in self.plugin_dirs:
            if not plugin_dir.exists():
                continue

            for plugin_path in plugin_dir.iterdir():
                if plugin_path.is_dir():
                    await self._discover_plugin(plugin_path)
                elif plugin_path.suffix == ".py":
                    await self._discover_single_file(plugin_path)

        return self.plugins

    async def _discover_plugin(self, path: Path) -> None:
        """Discover plugin from directory."""
        # Check for plugin.json
        config_file = path / "plugin.json"
        if not config_file.exists():
            return

        try:
            loop = asyncio.get_event_loop()
            content = await loop.run_in_executor(None, config_file.read_text)
            data = json.loads(content)

            metadata = PluginMetadata(
                name=data.get("name", path.name),
                version=data.get("version", "1.0"),
                author=data.get("author", ""),
                description=data.get("description", ""),
                requires=data.get("requires", []),
                provides=data.get("provides", []),
                priority=data.get("priority", 0),
            )

            self.plugins[metadata.name] = PluginInfo(
                metadata=metadata,
                path=path,
            )

        except Exception as e:
            self._errors.append({"path": str(path), "error": str(e)})

    async def _discover_single_file(self, path: Path) -> None:
        """Discover single-file plugin."""
        # Use filename as plugin name
        name = path.stem

        self.plugins[name] = PluginInfo(
            metadata=PluginMetadata(name=name),
            path=path,
        )

    async def load(self, name: str) -> PluginBase | None:
        """Load a specific plugin."""
        info = self.plugins.get(name)
        if not info:
            return None

        if info.state == PluginState.ACTIVE:
            return self._instances.get(name)

        info.state = PluginState.LOADING

        try:
            # Import module
            module_name = f"plugin_{name}"

            if info.path.is_dir():
                # Load from directory
                init_file = info.path / "__init__.py"
                if init_file.exists():
                    spec = importlib.util.spec_from_file_location(
                        module_name,
                        init_file,
                    )
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                else:
                    raise ImportError("No __init__.py")
            else:
                # Load single file
                spec = importlib.util.spec_from_file_location(
                    module_name,
                    info.path,
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

            # Find plugin class
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and issubclass(attr, PluginBase):
                    plugin_class = attr
                    break

            if plugin_class is None:
                raise ImportError("No PluginBase subclass found")

            # Instantiate
            instance = plugin_class()
            await instance.on_load()

            info.state = PluginState.ACTIVE
            info.loaded_at = time.time()
            self._instances[name] = instance

            return instance

        except Exception as e:
            info.state = PluginState.ERROR
            info.error = str(e)
            self._errors.append({"name": name, "error": str(e)})
            return None

    async def unload(self, name: str) -> bool:
        """Unload a plugin."""
        info = self.plugins.get(name)
        if not info:
            return False

        instance = self._instances.get(name)
        if instance:
            await instance.on_unload()
            del self._instances[name]

        info.state = PluginState.UNLOADED
        info.loaded_at = None

        return True

    async def load_all(self) -> Dict[str, PluginBase]:
        """Load all discovered plugins."""
        loaded = {}

        # Sort by priority
        sorted_plugins = sorted(
            self.plugins.items(),
            key=lambda x: x[1].metadata.priority,
        )

        for name, info in sorted_plugins:
            if info.state != PluginState.DISABLED:
                instance = await self.load(name)
                if instance:
                    loaded[name] = instance

        return loaded

    async def unload_all(self) -> None:
        """Unload all plugins."""
        for name in list(self._instances.keys()):
            await self.unload(name)

    def get_plugin(self, name: str) -> PluginBase | None:
        """Get loaded plugin instance."""
        return self._instances.get(name)

    def get_errors(self) -> List[dict]:
        """Get load errors."""
        return self._errors

    def disable(self, name: str) -> None:
        """Disable a plugin."""
        info = self.plugins.get(name)
        if info:
            info.state = PluginState.DISABLED

    def enable(self, name: str) -> None:
        """Enable a plugin."""
        info = self.plugins.get(name)
        if info and info.state == PluginState.DISABLED:
            info.state = PluginState.UNLOADED


class PluginManager:
    """Manage plugin lifecycle."""

    def __init__(self):
        self.loader = PluginLoader()
        self._event_hooks: Dict[str, List[Callable]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize plugin system."""
        if self._initialized:
            return

        await self.loader.discover()
        await self.loader.load_all()

        # Collect hooks from all plugins
        for name, instance in self.loader._instances.items():
            for event, hooks in instance._hooks.items():
                if event not in self._event_hooks:
                    self._event_hooks[event] = []
                self._event_hooks[event].extend(hooks)

        self._initialized = True

    async def shutdown(self) -> None:
        """Shutdown plugin system."""
        await self.loader.unload_all()
        self._event_hooks = {}
        self._initialized = False

    async def trigger_event(self, event: str, *args, **kwargs) -> List[Any]:
        """Trigger event to all registered hooks."""
        results = []
        hooks = self._event_hooks.get(event, [])

        for hook in hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(*args, **kwargs)
                else:
                    result = hook(*args, **kwargs)
                results.append(result)
            except Exception:
                pass

        return results

    def register_global_hook(self, event: str, callback: Callable) -> None:
        """Register global hook."""
        if event not in self._event_hooks:
            self._event_hooks[event] = []
        self._event_hooks[event].append(callback)

    def list_plugins(self) -> List[dict]:
        """List all plugins."""
        return [
            {
                "name": info.metadata.name,
                "version": info.metadata.version,
                "state": info.state.value,
                "description": info.metadata.description,
            }
            for info in self.loader.plugins.values()
        ]

    async def reload(self) -> None:
        """Reload all plugins."""
        await self.shutdown()
        await self.initialize()


# Events
PLUGIN_EVENTS = [
    "pre_tool_execute",
    "post_tool_execute",
    "pre_query",
    "post_query",
    "on_message",
    "on_error",
    "on_session_start",
    "on_session_end",
]

# Global manager
_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    """Get global plugin manager."""
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


async def initialize_plugins() -> None:
    """Initialize plugin system."""
    await get_plugin_manager().initialize()


async def trigger_plugin_event(event: str, *args, **kwargs) -> List[Any]:
    """Trigger plugin event."""
    return await get_plugin_manager().trigger_event(event, *args, **kwargs)

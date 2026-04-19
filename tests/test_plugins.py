"""Tests for Plugin System."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import json

from cc.services.plugins.plugin_system import (
    PluginState,
    PluginMetadata,
    PluginInfo,
    PluginBase,
    PluginLoader,
    PluginManager,
    get_plugin_manager,
    initialize_plugins,
    trigger_plugin_event,
    PLUGIN_EVENTS,
)


class TestPluginMetadata:
    """Test PluginMetadata dataclass."""

    def test_create_metadata(self):
        """Test creating plugin metadata."""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            author="Test Author",
            description="Test plugin",
        )
        assert metadata.name == "test_plugin"
        assert metadata.version == "1.0.0"
        assert metadata.author == "Test Author"
        assert metadata.description == "Test plugin"
        assert metadata.requires == []
        assert metadata.provides == []
        assert metadata.priority == 0

    def test_metadata_defaults(self):
        """Test metadata default values."""
        metadata = PluginMetadata(name="minimal")
        assert metadata.version == "1.0"
        assert metadata.author == ""
        assert metadata.description == ""


class TestPluginInfo:
    """Test PluginInfo dataclass."""

    def test_create_info(self):
        """Test creating plugin info."""
        metadata = PluginMetadata(name="test")
        path = Path("/tmp/test_plugin")
        info = PluginInfo(metadata=metadata, path=path)
        assert info.metadata.name == "test"
        assert info.path == path
        assert info.state == PluginState.UNLOADED
        assert info.loaded_at is None
        assert info.error is None


class TestPluginBase:
    """Test PluginBase class."""

    def test_plugin_base_creation(self):
        """Test creating a plugin instance."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

        plugin = TestPlugin()
        assert plugin._hooks == {}

    def test_register_hook(self):
        """Test registering hooks."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

        plugin = TestPlugin()
        callback = MagicMock()
        plugin.register_hook("pre_query", callback)
        assert "pre_query" in plugin._hooks
        assert callback in plugin._hooks["pre_query"]

    def test_unregister_hook(self):
        """Test unregistering hooks."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

        plugin = TestPlugin()
        callback1 = MagicMock()
        callback2 = MagicMock()
        plugin.register_hook("pre_query", callback1)
        plugin.register_hook("pre_query", callback2)
        plugin.unregister_hook("pre_query", callback1)
        assert callback1 not in plugin._hooks["pre_query"]
        assert callback2 in plugin._hooks["pre_query"]

    def test_get_hooks(self):
        """Test getting hooks."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

        plugin = TestPlugin()
        callback = MagicMock()
        plugin.register_hook("pre_query", callback)
        hooks = plugin.get_hooks("pre_query")
        assert hooks == [callback]
        assert plugin.get_hooks("nonexistent") == []

    @pytest.mark.asyncio
    async def test_on_load(self):
        """Test on_load lifecycle."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

            async def on_load(self):
                self.loaded = True

        plugin = TestPlugin()
        await plugin.on_load()
        assert plugin.loaded is True

    @pytest.mark.asyncio
    async def test_on_unload(self):
        """Test on_unload lifecycle."""
        class TestPlugin(PluginBase):
            metadata = PluginMetadata(name="test_plugin")

            async def on_unload(self):
                self.unloaded = True

        plugin = TestPlugin()
        await plugin.on_unload()
        assert plugin.unloaded is True


class TestPluginLoader:
    """Test PluginLoader class."""

    def test_init_default_dirs(self):
        """Test default plugin directories."""
        loader = PluginLoader()
        assert len(loader.plugin_dirs) == 2
        assert loader.plugins == {}
        assert loader._instances == {}

    def test_init_custom_dirs(self):
        """Test custom plugin directories."""
        custom_dirs = [Path("/custom/plugins")]
        loader = PluginLoader(plugin_dirs=custom_dirs)
        assert loader.plugin_dirs == custom_dirs

    @pytest.mark.asyncio
    async def test_discover_empty(self):
        """Test discovering with no plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            plugins = await loader.discover()
            assert plugins == {}

    @pytest.mark.asyncio
    async def test_discover_single_file(self):
        """Test discovering single file plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "test_plugin.py"
            plugin_path.write_text(
                """
from cc.services.plugins.plugin_system import PluginBase, PluginMetadata

class MyPlugin(PluginBase):
    metadata = PluginMetadata(name="my_plugin")
"""
            )

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            plugins = await loader.discover()
            assert "test_plugin" in plugins
            assert plugins["test_plugin"].metadata.name == "test_plugin"

    @pytest.mark.asyncio
    async def test_discover_directory_plugin(self):
        """Test discovering directory plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_dir = Path(tmpdir) / "dir_plugin"
            plugin_dir.mkdir()
            config_file = plugin_dir / "plugin.json"
            config_file.write_text(
                json.dumps(
                    {
                        "name": "directory_plugin",
                        "version": "2.0.0",
                        "author": "Test",
                        "description": "A directory plugin",
                    }
                )
            )

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            plugins = await loader.discover()
            assert "directory_plugin" in plugins
            assert plugins["directory_plugin"].metadata.version == "2.0.0"

    @pytest.mark.asyncio
    async def test_load_single_file(self):
        """Test loading single file plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "loadable.py"
            plugin_path.write_text(
                """
from cc.services.plugins.plugin_system import PluginBase, PluginMetadata

class LoadablePlugin(PluginBase):
    metadata = PluginMetadata(name="loadable_plugin")

    async def on_load(self):
        self.initialized = True
"""
            )

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            await loader.discover()
            instance = await loader.load("loadable")

            assert instance is not None
            assert instance.initialized is True
            info = loader.plugins["loadable"]
            assert info.state == PluginState.ACTIVE

    @pytest.mark.asyncio
    async def test_load_error(self):
        """Test loading plugin with error."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "broken.py"
            plugin_path.write_text("invalid python syntax here!")

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            await loader.discover()
            instance = await loader.load("broken")

            assert instance is None
            assert loader.plugins["broken"].state == PluginState.ERROR
            assert len(loader._errors) > 0

    @pytest.mark.asyncio
    async def test_unload(self):
        """Test unloading plugin."""
        with tempfile.TemporaryDirectory() as tmpdir:
            plugin_path = Path(tmpdir) / "unloadable.py"
            plugin_path.write_text(
                """
from cc.services.plugins.plugin_system import PluginBase, PluginMetadata

class UnloadablePlugin(PluginBase):
    metadata = PluginMetadata(name="unloadable_plugin")

    async def on_unload(self):
        self.cleaned_up = True
"""
            )

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            await loader.discover()
            await loader.load("unloadable")
            result = await loader.unload("unloadable")

            assert result is True
            assert loader.plugins["unloadable"].state == PluginState.UNLOADED
            assert "unloadable" not in loader._instances

    @pytest.mark.asyncio
    async def test_load_all(self):
        """Test loading all plugins."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create two plugins
            for name in ["plugin_a", "plugin_b"]:
                path = Path(tmpdir) / f"{name}.py"
                path.write_text(
                    f"""
from cc.services.plugins.plugin_system import PluginBase, PluginMetadata

class {name.capitalize()}Plugin(PluginBase):
    metadata = PluginMetadata(name="{name}")
"""
                )

            loader = PluginLoader(plugin_dirs=[Path(tmpdir)])
            await loader.discover()
            loaded = await loader.load_all()

            assert len(loaded) == 2
            assert all(
                loader.plugins[name].state == PluginState.ACTIVE for name in loaded
            )

    def test_disable_enable(self):
        """Test disable and enable."""
        loader = PluginLoader()
        info = PluginInfo(
            metadata=PluginMetadata(name="test"),
            path=Path("/tmp/test"),
        )
        loader.plugins["test"] = info

        loader.disable("test")
        assert loader.plugins["test"].state == PluginState.DISABLED

        loader.enable("test")
        assert loader.plugins["test"].state == PluginState.UNLOADED


class TestPluginManager:
    """Test PluginManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = PluginManager()
        assert manager.loader is not None
        assert manager._event_hooks == {}
        assert manager._initialized is False

    @pytest.mark.asyncio
    async def test_initialize_shutdown(self):
        """Test initialize and shutdown."""
        manager = PluginManager()
        await manager.initialize()
        assert manager._initialized is True

        await manager.shutdown()
        assert manager._initialized is False
        assert manager._event_hooks == {}

    @pytest.mark.asyncio
    async def test_trigger_event(self):
        """Test triggering events."""
        manager = PluginManager()
        callback = AsyncMock(return_value="result")
        manager.register_global_hook("test_event", callback)

        results = await manager.trigger_event("test_event", "arg1", kwarg="kw")
        assert results == ["result"]
        callback.assert_called_once_with("arg1", kwarg="kw")

    def test_register_global_hook(self):
        """Test registering global hook."""
        manager = PluginManager()
        callback = MagicMock()
        manager.register_global_hook("event1", callback)
        manager.register_global_hook("event1", lambda: None)

        assert len(manager._event_hooks["event1"]) == 2

    def test_list_plugins(self):
        """Test listing plugins."""
        manager = PluginManager()
        manager.loader.plugins["test"] = PluginInfo(
            metadata=PluginMetadata(name="test", version="1.0"),
            path=Path("/tmp/test"),
            state=PluginState.ACTIVE,
        )

        plugins = manager.list_plugins()
        assert len(plugins) == 1
        assert plugins[0]["name"] == "test"
        assert plugins[0]["version"] == "1.0"
        assert plugins[0]["state"] == "active"

    @pytest.mark.asyncio
    async def test_reload(self):
        """Test reload."""
        manager = PluginManager()
        await manager.initialize()
        first_init = manager._initialized

        await manager.reload()
        assert manager._initialized is True


class TestGlobals:
    """Test global functions."""

    def test_get_plugin_manager(self):
        """Test getting global manager."""
        manager1 = get_plugin_manager()
        manager2 = get_plugin_manager()
        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_initialize_plugins(self):
        """Test global initialize."""
        await initialize_plugins()
        manager = get_plugin_manager()
        # Note: This affects global state

    @pytest.mark.asyncio
    async def test_trigger_plugin_event(self):
        """Test global trigger."""
        manager = get_plugin_manager()
        manager.register_global_hook("test", AsyncMock(return_value="ok"))
        results = await trigger_plugin_event("test")
        assert results == ["ok"]


class TestPluginEvents:
    """Test plugin events constant."""

    def test_events_list(self):
        """Test events are defined."""
        assert "pre_tool_execute" in PLUGIN_EVENTS
        assert "post_tool_execute" in PLUGIN_EVENTS
        assert "pre_query" in PLUGIN_EVENTS
        assert "post_query" in PLUGIN_EVENTS
        assert "on_message" in PLUGIN_EVENTS
        assert "on_error" in PLUGIN_EVENTS
        assert "on_session_start" in PLUGIN_EVENTS
        assert "on_session_end" in PLUGIN_EVENTS
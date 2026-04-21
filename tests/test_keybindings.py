"""Tests for keybinding manager."""

import pytest
from src.cc.services.keybindings import (
    KeybindingManager,
    KeybindingConfig,
    KeybindingMode,
    KeybindingAction,
    Keybinding,
)


@pytest.mark.asyncio
async def test_keybinding_manager_init():
    """Test manager initialization."""
    manager = KeybindingManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_get_binding():
    """Test getting binding."""
    manager = KeybindingManager()

    binding = await manager.get_binding("ctrl+c")
    assert binding is not None
    assert binding.action == KeybindingAction.QUIT


@pytest.mark.asyncio
async def test_register_binding():
    """Test registering binding."""
    manager = KeybindingManager()

    binding = Keybinding(
        key="ctrl+shift+t",
        action=KeybindingAction.CUSTOM,
        command="test",
    )

    result = await manager.register_binding(binding)
    assert result is True


@pytest.mark.asyncio
async def test_unregister_binding():
    """Test unregistering binding."""
    manager = KeybindingManager()

    binding = Keybinding(
        key="ctrl+shift+x",
        action=KeybindingAction.CUSTOM,
    )

    await manager.register_binding(binding)
    result = await manager.unregister_binding("ctrl+shift+x")

    assert result is True


@pytest.mark.asyncio
async def test_handle_key():
    """Test handling key."""
    manager = KeybindingManager()

    action = await manager.handle_key("ctrl+c")
    assert action == KeybindingAction.QUIT


@pytest.mark.asyncio
async def test_handle_unknown_key():
    """Test handling unknown key."""
    manager = KeybindingManager()

    action = await manager.handle_key("unknown_key")
    assert action is None


@pytest.mark.asyncio
async def test_get_all_bindings():
    """Test getting all bindings."""
    manager = KeybindingManager()

    bindings = await manager.get_all_bindings()
    assert len(bindings) > 0


@pytest.mark.asyncio
async def test_set_mode():
    """Test setting mode."""
    manager = KeybindingManager()

    await manager.set_mode(KeybindingMode.VIM)

    binding = await manager.get_binding("h")
    assert binding is not None


@pytest.mark.asyncio
async def test_enable_disable_binding():
    """Test enabling/disabling binding."""
    manager = KeybindingManager()

    await manager.disable_binding("ctrl+c")
    action = await manager.handle_key("ctrl+c")
    assert action is None

    await manager.enable_binding("ctrl+c")
    action = await manager.handle_key("ctrl+c")
    assert action == KeybindingAction.QUIT


@pytest.mark.asyncio
async def test_export_import_bindings():
    """Test export/import."""
    manager = KeybindingManager()

    exported = await manager.export_bindings()
    assert "mode" in exported
    assert "bindings" in exported


@pytest.mark.asyncio
async def test_register_callback():
    """Test registering callback."""
    manager = KeybindingManager()

    callbacks = []

    def callback(b):
        callbacks.append(b)

    manager.register_callback(KeybindingAction.QUIT, callback)

    await manager.handle_key("ctrl+c")

    assert len(callbacks) == 1


@pytest.mark.asyncio
async def test_keybinding_mode_enum():
    """Test keybinding mode enum."""
    assert KeybindingMode.NORMAL.value == "normal"
    assert KeybindingMode.VIM.value == "vim"


@pytest.mark.asyncio
async def test_keybinding_action_enum():
    """Test keybinding action enum."""
    assert KeybindingAction.QUIT.value == "quit"
    assert KeybindingAction.SAVE.value == "save"


@pytest.mark.asyncio
async def test_keybinding():
    """Test keybinding dataclass."""
    binding = Keybinding(
        key="test_key",
        action=KeybindingAction.CUSTOM,
        description="Test binding",
    )

    assert binding.key == "test_key"
    assert binding.enabled is True


@pytest.mark.asyncio
async def test_keybinding_config():
    """Test keybinding config."""
    config = KeybindingConfig(
        mode=KeybindingMode.VIM,
        allow_custom=False,
    )

    assert config.mode == KeybindingMode.VIM
    assert config.allow_custom is False
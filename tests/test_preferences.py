"""Tests for user preferences."""

import pytest
from pathlib import Path
from src.cc.services.preferences import (
    UserPreferences,
    PreferencesConfig,
    Preference,
    PreferenceCategory,
)


@pytest.mark.asyncio
async def test_preferences_init():
    """Test preferences initialization."""
    prefs = UserPreferences()
    assert prefs._preferences is not None


@pytest.mark.asyncio
async def test_get_preference():
    """Test getting preference."""
    prefs = UserPreferences()

    value = await prefs.get("theme")
    assert value is not None


@pytest.mark.asyncio
async def test_set_preference():
    """Test setting preference."""
    prefs = UserPreferences()

    result = await prefs.set("theme", "dark")
    assert result is True

    value = await prefs.get("theme")
    assert value == "dark"


@pytest.mark.asyncio
async def test_get_all():
    """Test getting all preferences."""
    prefs = UserPreferences()

    all_prefs = await prefs.get_all()
    assert len(all_prefs) > 0


@pytest.mark.asyncio
async def test_get_by_category():
    """Test getting by category."""
    prefs = UserPreferences()

    ui_prefs = await prefs.get_by_category(PreferenceCategory.UI)
    assert len(ui_prefs) > 0


@pytest.mark.asyncio
async def test_reset_preference():
    """Test resetting preference."""
    prefs = UserPreferences()

    await prefs.set("theme", "custom")
    await prefs.reset("theme")

    value = await prefs.get("theme")
    assert value == "default"


@pytest.mark.asyncio
async def test_reset_all():
    """Test resetting all preferences."""
    prefs = UserPreferences()

    await prefs.set("theme", "custom")
    await prefs.set("model", "custom-model")

    await prefs.reset_all()

    theme = await prefs.get("theme")
    assert theme == "default"


@pytest.mark.asyncio
async def test_list_preferences():
    """Test listing preferences."""
    prefs = UserPreferences()

    prefs_list = await prefs.list_preferences()
    assert len(prefs_list) > 0


@pytest.mark.asyncio
async def test_preference_info():
    """Test getting preference info."""
    prefs = UserPreferences()

    info = await prefs.get_preference_info("theme")
    assert info is not None
    assert info.key == "theme"


@pytest.mark.asyncio
async def test_export_import():
    """Test export and import."""
    prefs = UserPreferences()

    await prefs.set("theme", "exported")

    exported = await prefs.export()
    assert "theme" in exported

    # Import
    prefs2 = UserPreferences()
    count = await prefs2.import_prefs(exported)
    assert count > 0


@pytest.mark.asyncio
async def test_callback():
    """Test preference change callback."""
    prefs = UserPreferences()

    changes = []

    def callback(key, value):
        changes.append((key, value))

    prefs.register_callback("theme", callback)

    await prefs.set("theme", "callback-test")

    assert len(changes) == 1
    assert changes[0] == ("theme", "callback-test")


@pytest.mark.asyncio
async def test_preference_category():
    """Test preference category enum."""
    assert PreferenceCategory.UI.value == "ui"
    assert PreferenceCategory.BEHAVIOR.value == "behavior"
    assert PreferenceCategory.MODEL.value == "model"


@pytest.mark.asyncio
async def test_preference():
    """Test preference dataclass."""
    pref = Preference(
        key="test_key",
        value="test_value",
        category=PreferenceCategory.UI,
        description="Test preference",
    )

    assert pref.key == "test_key"
    assert pref.editable is True


@pytest.mark.asyncio
async def test_preferences_config():
    """Test preferences config."""
    config = PreferencesConfig(
        auto_save=False,
        sync_enabled=True,
    )

    assert config.auto_save is False
    assert config.sync_enabled is True
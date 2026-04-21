"""Tests for styling service."""

import pytest
from src.cc.services.styling import (
    StylingService,
    StyleConfig,
    ThemeType,
    ThemeColors,
    ColorRole,
)


@pytest.mark.asyncio
async def test_styling_service_init():
    """Test styling service initialization."""
    service = StylingService()
    assert service.config is not None


@pytest.mark.asyncio
async def test_get_theme():
    """Test getting theme."""
    service = StylingService()

    theme = await service.get_theme()
    assert theme is not None
    assert theme.primary is not None


@pytest.mark.asyncio
async def test_set_theme():
    """Test setting theme."""
    service = StylingService()

    result = await service.set_theme(ThemeType.DARK)
    assert result is True

    theme = await service.get_theme()
    assert theme.background == "#0D0D0D"


@pytest.mark.asyncio
async def test_get_color():
    """Test getting color."""
    service = StylingService()

    color = await service.get_color(ColorRole.PRIMARY)
    assert color is not None


@pytest.mark.asyncio
async def test_register_custom_theme():
    """Test registering custom theme."""
    service = StylingService()

    custom_colors = ThemeColors(
        primary="#FF0000",
        background="#000000",
        text="#FFFFFF",
    )

    await service.register_custom_theme("custom_red", custom_colors)

    result = await service.use_custom_theme("custom_red")
    assert result is True


@pytest.mark.asyncio
async def test_get_all_themes():
    """Test getting all themes."""
    service = StylingService()

    themes = await service.get_all_themes()
    assert len(themes) > 0


@pytest.mark.asyncio
async def test_get_css_vars():
    """Test getting CSS variables."""
    service = StylingService()

    vars = await service.get_css_vars()
    assert "--color-primary" in vars
    assert "--font-size" in vars


@pytest.mark.asyncio
async def test_set_style_property():
    """Test setting style property."""
    service = StylingService()

    result = await service.set_style_property("font_size", 14)
    assert result is True
    assert service.config.font_size == 14


@pytest.mark.asyncio
async def test_export_import_theme():
    """Test export and import theme."""
    service = StylingService()

    exported = await service.export_theme()
    assert "colors" in exported
    assert "config" in exported


@pytest.mark.asyncio
async def test_theme_type_enum():
    """Test theme type enum."""
    assert ThemeType.DEFAULT.value == "default"
    assert ThemeType.DARK.value == "dark"
    assert ThemeType.LIGHT.value == "light"


@pytest.mark.asyncio
async def test_color_role_enum():
    """Test color role enum."""
    assert ColorRole.PRIMARY.value == "primary"
    assert ColorRole.SECONDARY.value == "secondary"
    assert ColorRole.ERROR.value == "error"


@pytest.mark.asyncio
async def test_theme_colors():
    """Test theme colors."""
    colors = ThemeColors(
        primary="#123456",
        background="#000000",
        text="#FFFFFF",
    )

    assert colors.primary == "#123456"
    assert colors.background == "#000000"


@pytest.mark.asyncio
async def test_style_config():
    """Test style config."""
    config = StyleConfig(
        theme=ThemeType.DARK,
        font_size=16,
        animation_enabled=False,
    )

    assert config.theme == ThemeType.DARK
    assert config.font_size == 16
    assert config.animation_enabled is False
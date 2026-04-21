"""Styling Service - UI styling and themes."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class ThemeType(Enum):
    """Theme types."""
    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    HIGH_CONTRAST = "high_contrast"
    MONOCHROME = "monochrome"
    CUSTOM = "custom"


class ColorRole(Enum):
    """Color roles."""
    PRIMARY = "primary"
    SECONDARY = "secondary"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    INFO = "info"
    BACKGROUND = "background"
    TEXT = "text"
    ACCENT = "accent"


@dataclass
class ColorScheme:
    """Color scheme definition."""
    name: str
    colors: Dict[ColorRole, str] = field(default_factory=dict)


@dataclass
class ThemeColors:
    """Theme color values."""
    primary: str = "#4A90D9"
    secondary: str = "#6B7280"
    success: str = "#10B981"
    warning: str = "#F59E0B"
    error: str = "#EF4444"
    info: str = "#3B82F6"
    background: str = "#1A1A2E"
    text: str = "#E5E5E5"
    accent: str = "#9B59B6"


@dataclass
class StyleConfig:
    """Style configuration."""
    theme: ThemeType = ThemeType.DEFAULT
    font_size: int = 12
    line_height: float = 1.5
    spacing: int = 4
    border_radius: int = 4
    animation_enabled: bool = True


# Predefined themes
THEMES: Dict[ThemeType, ThemeColors] = {
    ThemeType.DEFAULT: ThemeColors(
        primary="#4A90D9",
        background="#1E1E1E",
        text="#E5E5E5",
    ),
    ThemeType.DARK: ThemeColors(
        primary="#569CD6",
        background="#0D0D0D",
        text="#D4D4D4",
        success="#4EC9B0",
        error="#F14C4C",
    ),
    ThemeType.LIGHT: ThemeColors(
        primary="#0066CC",
        background="#FFFFFF",
        text="#333333",
        success="#22863A",
        error="#CB2431",
    ),
    ThemeType.HIGH_CONTRAST: ThemeColors(
        primary="#FFFF00",
        background="#000000",
        text="#FFFFFF",
        success="#00FF00",
        error="#FF0000",
    ),
    ThemeType.MONOCHROME: ThemeColors(
        primary="#888888",
        background="#222222",
        text="#AAAAAA",
    ),
}


class StylingService:
    """Service for UI styling."""

    def __init__(self, config: Optional[StyleConfig] = None):
        self.config = config or StyleConfig()
        self._custom_themes: Dict[str, ThemeColors] = {}
        self._current_theme: ThemeColors = THEMES.get(
            config.theme if config else ThemeType.DEFAULT,
            THEMES[ThemeType.DEFAULT]
        )

    async def get_theme(self) -> ThemeColors:
        """Get current theme."""
        return self._current_theme

    async def set_theme(
        self,
        theme_type: ThemeType
    ) -> bool:
        """Set theme by type."""
        if theme_type == ThemeType.CUSTOM:
            return False

        if theme_type in THEMES:
            self._current_theme = THEMES[theme_type]
            self.config.theme = theme_type
            logger.info(f"Theme set to {theme_type.value}")
            return True

        return False

    async def get_color(
        self,
        role: ColorRole
    ) -> str:
        """Get color by role."""
        role_map = {
            ColorRole.PRIMARY: self._current_theme.primary,
            ColorRole.SECONDARY: self._current_theme.secondary,
            ColorRole.SUCCESS: self._current_theme.success,
            ColorRole.WARNING: self._current_theme.warning,
            ColorRole.ERROR: self._current_theme.error,
            ColorRole.INFO: self._current_theme.info,
            ColorRole.BACKGROUND: self._current_theme.background,
            ColorRole.TEXT: self._current_theme.text,
            ColorRole.ACCENT: self._current_theme.accent,
        }

        return role_map.get(role, "#000000")

    async def register_custom_theme(
        self,
        name: str,
        colors: ThemeColors
    ) -> None:
        """Register custom theme."""
        self._custom_themes[name] = colors
        logger.info(f"Custom theme registered: {name}")

    async def use_custom_theme(
        self,
        name: str
    ) -> bool:
        """Use custom theme."""
        if name in self._custom_themes:
            self._current_theme = self._custom_themes[name]
            self.config.theme = ThemeType.CUSTOM
            return True

        return False

    async def get_all_themes(self) -> Dict[str, ThemeColors]:
        """Get all available themes."""
        result = {}

        for theme_type, colors in THEMES.items():
            result[theme_type.value] = colors

        for name, colors in self._custom_themes.items():
            result[f"custom:{name}"] = colors

        return result

    async def get_style_config(self) -> StyleConfig:
        """Get style configuration."""
        return self.config

    async def set_style_property(
        self,
        property: str,
        value: Any
    ) -> bool:
        """Set style property."""
        if property == "font_size":
            self.config.font_size = int(value)
        elif property == "line_height":
            self.config.line_height = float(value)
        elif property == "spacing":
            self.config.spacing = int(value)
        elif property == "border_radius":
            self.config.border_radius = int(value)
        elif property == "animation_enabled":
            self.config.animation_enabled = bool(value)
        else:
            return False

        return True

    async def get_css_vars(self) -> Dict[str, str]:
        """Get CSS variables for theme."""
        return {
            "--color-primary": self._current_theme.primary,
            "--color-secondary": self._current_theme.secondary,
            "--color-success": self._current_theme.success,
            "--color-warning": self._current_theme.warning,
            "--color-error": self._current_theme.error,
            "--color-info": self._current_theme.info,
            "--color-background": self._current_theme.background,
            "--color-text": self._current_theme.text,
            "--color-accent": self._current_theme.accent,
            "--font-size": f"{self.config.font_size}px",
            "--line-height": str(self.config.line_height),
            "--spacing": f"{self.config.spacing}px",
            "--border-radius": f"{self.config.border_radius}px",
        }

    async def export_theme(self) -> Dict[str, Any]:
        """Export current theme."""
        return {
            "theme_type": self.config.theme.value,
            "colors": {
                "primary": self._current_theme.primary,
                "secondary": self._current_theme.secondary,
                "success": self._current_theme.success,
                "warning": self._current_theme.warning,
                "error": self._current_theme.error,
                "info": self._current_theme.info,
                "background": self._current_theme.background,
                "text": self._current_theme.text,
                "accent": self._current_theme.accent,
            },
            "config": {
                "font_size": self.config.font_size,
                "line_height": self.config.line_height,
                "spacing": self.config.spacing,
                "border_radius": self.config.border_radius,
                "animation_enabled": self.config.animation_enabled,
            },
        }

    async def import_theme(
        self,
        data: Dict[str, Any]
    ) -> bool:
        """Import theme configuration."""
        try:
            if "colors" in data:
                self._current_theme = ThemeColors(**data["colors"])

            if "config" in data:
                for key, value in data["config"].items():
                    await self.set_style_property(key, value)

            return True
        except Exception as e:
            logger.error(f"Import failed: {e}")
            return False


__all__ = [
    "ThemeType",
    "ColorRole",
    "ColorScheme",
    "ThemeColors",
    "StyleConfig",
    "StylingService",
    "THEMES",
]
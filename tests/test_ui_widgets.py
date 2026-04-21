"""Tests for UI Widgets - Theme system, Vim mode, etc."""

import pytest
from unittest.mock import MagicMock, patch

from cc.ui.widgets import (
    ThemeType,
    ThemeManager,
)


class TestThemeType:
    """Test ThemeType enum."""

    def test_all_themes(self):
        """Test all theme types exist."""
        themes = [
            ThemeType.DARK,
            ThemeType.LIGHT,
            ThemeType.MONO,
            ThemeType.GRUVBOX,
            ThemeType.NORD,
            ThemeType.DRACULA,
            ThemeType.SOLARIZED,
        ]
        for theme in themes:
            assert isinstance(theme.value, str)


class TestThemeManager:
    """Test ThemeManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = ThemeManager()
        assert manager._current_theme == "dark"

    def test_get_theme_css(self):
        """Test getting theme CSS."""
        manager = ThemeManager()
        css = manager.get_theme_css("dark")
        assert "$surface:" in css

        css_light = manager.get_theme_css("light")
        assert "$surface:" in css_light

    def test_get_invalid_theme(self):
        """Test getting invalid theme returns dark."""
        manager = ThemeManager()
        css = manager.get_theme_css("nonexistent")
        assert "$surface:" in css  # Falls back to dark

    def test_set_theme(self):
        """Test setting theme."""
        manager = ThemeManager()
        manager.set_theme("nord")
        assert manager.get_current_theme() == "nord"

    def test_get_all_themes(self):
        """Test getting all theme names."""
        manager = ThemeManager()
        themes = manager.get_all_themes()
        assert "dark" in themes
        assert "light" in themes
        assert len(themes) >= 7


class TestSessionManager:
    """Test SessionManager (imported from ui dependency)."""

    def test_init(self):
        """Test manager initialization."""
        from cc.core.session import SessionManager
        manager = SessionManager()
        assert manager.sessions_dir is not None

    def test_create_session(self):
        """Test creating session."""
        from cc.core.session import SessionManager
        manager = SessionManager()
        session = manager.create_session()
        assert session.session_id is not None
        assert session.messages == []

    def test_list_sessions(self):
        """Test listing sessions."""
        from cc.core.session import SessionManager
        manager = SessionManager()
        sessions = manager.list_sessions()
        assert isinstance(sessions, list)

    def test_get_current_session(self):
        """Test getting current session."""
        from cc.core.session import SessionManager
        manager = SessionManager()
        session = manager.create_session()
        assert manager.get_current_session() == session
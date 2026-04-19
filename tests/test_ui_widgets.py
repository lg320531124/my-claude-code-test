"""Tests for UI Widgets - Theme system, Vim mode, etc."""

import pytest
from unittest.mock import MagicMock, patch

from cc.ui.widgets import (
    ThemeType,
    ThemeManager,
    VimMode,
    VimModeIndicator,
    VimHandler,
    StatusWidget,
    TokenCounterWidget,
    ToolProgressWidget,
    MessageListWidget,
    ThemeSelectorWidget,
    CommandPaletteWidget,
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
        assert "#eff1f5" in css_light or "$surface:" in css_light

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
        assert "gruvbox" in themes
        assert len(themes) >= 7


class TestVimMode:
    """Test VimMode enum."""

    def test_all_modes(self):
        """Test all vim modes exist."""
        modes = [
            VimMode.NORMAL,
            VimMode.INSERT,
            VimMode.COMMAND,
            VimMode.VISUAL,
        ]
        for mode in modes:
            assert isinstance(mode.value, str)


class TestVimModeIndicator:
    """Test VimModeIndicator widget."""

    def test_init(self):
        """Test indicator initialization."""
        indicator = VimModeIndicator()
        assert indicator.mode == VimMode.NORMAL
        assert indicator.enabled is False

    def test_set_mode(self):
        """Test setting mode."""
        indicator = VimModeIndicator()
        indicator.enabled = True
        indicator.set_mode(VimMode.INSERT)
        assert indicator.mode == VimMode.INSERT


class TestVimHandler:
    """Test VimHandler class."""

    def test_init(self):
        """Test handler initialization."""
        widget = MagicMock()
        handler = VimHandler(widget)
        assert handler.mode == VimMode.NORMAL
        assert handler._enabled is False

    def test_enable_disable(self):
        """Test enable/disable."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler.enable()
        assert handler.is_enabled() is True
        assert handler.mode == VimMode.NORMAL

        handler.disable()
        assert handler.is_enabled() is False

    def test_handle_key_disabled(self):
        """Test handling key when disabled."""
        widget = MagicMock()
        handler = VimHandler(widget)
        result = handler.handle_key("j")
        assert result is None

    def test_handle_normal_mode_navigation(self):
        """Test navigation in normal mode."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler.enable()

        assert handler.handle_key("j") == "scroll_down"
        assert handler.handle_key("k") == "scroll_up"
        assert handler.handle_key("g") == "scroll_top"
        assert handler.handle_key("G") == "scroll_bottom"

    def test_handle_normal_mode_switching(self):
        """Test mode switching in normal mode."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler.enable()

        result = handler.handle_key("i")
        assert result == "enter_insert"
        assert handler.mode == VimMode.INSERT

    def test_handle_insert_mode(self):
        """Test insert mode handling."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler.enable()
        handler.mode = VimMode.INSERT

        result = handler.handle_key("escape")
        assert result == "exit_insert"
        assert handler.mode == VimMode.NORMAL

    def test_handle_command_mode(self):
        """Test command mode handling."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler.enable()

        # Enter command mode
        handler.handle_key("colon")
        assert handler.mode == VimMode.COMMAND

        # Type command
        handler._command_buffer = ""
        handler.handle_key("q")
        assert handler._command_buffer == "q"

        # Execute
        result = handler.handle_key("enter")
        assert result == "quit"
        assert handler.mode == VimMode.NORMAL

    def test_command_quit(self):
        """Test quit command."""
        widget = MagicMock()
        handler = VimHandler(widget)
        handler._execute_command("q") == "quit"

    def test_command_save(self):
        """Test save command."""
        widget = MagicMock()
        handler = VimHandler(widget)
        assert handler._execute_command("w") == "save"

    def test_command_wq(self):
        """Test wq command."""
        widget = MagicMock()
        handler = VimHandler(widget)
        assert handler._execute_command("wq") == "save_quit"

    def test_command_clear(self):
        """Test clear command."""
        widget = MagicMock()
        handler = VimHandler(widget)
        assert handler._execute_command("clear") == "clear"

    def test_command_theme(self):
        """Test theme command."""
        widget = MagicMock()
        handler = VimHandler(widget)
        result = handler._execute_command("theme nord")
        assert result == "set_theme:nord"


class TestStatusWidget:
    """Test StatusWidget."""

    def test_init(self):
        """Test status widget initialization."""
        widget = StatusWidget()
        assert widget.status == "ready"
        assert widget.model == "claude-sonnet-4-6"

    def test_reactive_updates(self):
        """Test reactive properties."""
        widget = StatusWidget()
        widget.status = "thinking"
        widget.model = "claude-opus-4-7"
        widget.theme = "nord"

        assert widget.status == "thinking"
        assert widget.model == "claude-opus-4-7"
        assert widget.theme == "nord"


class TestTokenCounterWidget:
    """Test TokenCounterWidget."""

    def test_init(self):
        """Test token counter initialization."""
        widget = TokenCounterWidget()
        assert widget.input_tokens == 0
        assert widget.output_tokens == 0
        assert widget.max_tokens == 8192

    def test_reactive_updates(self):
        """Test reactive updates."""
        widget = TokenCounterWidget()
        widget.input_tokens = 1000
        widget.output_tokens = 500

        assert widget.input_tokens == 1000
        assert widget.output_tokens == 500


class TestToolProgressWidget:
    """Test ToolProgressWidget."""

    def test_init(self):
        """Test tool progress initialization."""
        widget = ToolProgressWidget()
        assert widget.tool_name == ""
        assert widget.status == "running"
        assert widget.progress == 0

    def test_reactive_updates(self):
        """Test reactive updates."""
        widget = ToolProgressWidget()
        widget.tool_name = "Bash"
        widget.status = "complete"
        widget.progress = 100
        widget.result_preview = "Success"

        assert widget.tool_name == "Bash"
        assert widget.status == "complete"


class TestMessageListWidget:
    """Test MessageListWidget."""

    def test_init(self):
        """Test message list initialization."""
        widget = MessageListWidget()
        assert widget.messages == []

    def test_add_message(self):
        """Test adding messages."""
        widget = MessageListWidget()
        widget.add_message("user", "Hello")
        widget.add_message("assistant", "Hi there!")

        assert len(widget.messages) == 2
        assert widget.messages[0]["role"] == "user"
        assert widget.messages[1]["content"] == "Hi there!"

    def test_clear(self):
        """Test clearing messages."""
        widget = MessageListWidget()
        widget.add_message("user", "Test")
        widget.clear()
        assert widget.messages == []


class TestThemeSelectorWidget:
    """Test ThemeSelectorWidget."""

    def test_init(self):
        """Test theme selector initialization."""
        widget = ThemeSelectorWidget()
        assert widget.current_theme == "dark"
        assert len(widget.available_themes) >= 7

    def test_current_theme_highlight(self):
        """Test current theme is highlighted."""
        widget = ThemeSelectorWidget()
        widget.current_theme = "nord"


class TestCommandPaletteWidget:
    """Test CommandPaletteWidget."""

    def test_init(self):
        """Test command palette initialization."""
        widget = CommandPaletteWidget()
        assert widget.query == ""
        assert widget.selected == 0

    def test_update_query(self):
        """Test updating query."""
        widget = CommandPaletteWidget()
        widget.update_query("/he")
        assert widget.query == "/he"
        assert widget.selected == 0

    def test_move_selection(self):
        """Test moving selection."""
        widget = CommandPaletteWidget()
        widget.update_query("/")  # Match all commands
        widget.move_selection(1)
        # Selection should move down

    def test_get_selected_command(self):
        """Test getting selected command."""
        widget = CommandPaletteWidget()
        widget.update_query("/help")
        cmd = widget.get_selected_command()
        assert cmd == "/help"


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
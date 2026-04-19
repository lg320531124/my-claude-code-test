"""UI module - Terminal User Interface."""

from __future__ import annotations
from .app import (
    ClaudeCodeApp,
    MainScreen,
    MessageWidget,
    InputWidget,
    UserInput,
    ToolProgress,
    StreamingUpdate,
    VimModeChanged,
    ThemeChanged,
    run_tui,
)
from .screens import (
    HelpScreen,
    SessionsScreen,
    PluginsScreen,
    HooksScreen,
    SettingsScreen,
    StatsScreen,
    MessageHistoryScreen,
    DoctorScreen,
    ConfigScreen,
)
from .widgets import (
    ThemeType,
    ThemeManager,
    VimMode,
    VimModeIndicator,
    VimHandler,
    StatusWidget,
    TokenCounterWidget,
    ToolProgressWidget,
    MessageListWidget,
    CodeBlockWidget,
    MarkdownWidget,
    HistoryBrowserWidget,
    StatsTableWidget,
    ThemeSelectorWidget,
    CommandPaletteWidget,
)

__all__ = [
    # App
    "ClaudeCodeApp",
    "MainScreen",
    "MessageWidget",
    "InputWidget",
    "run_tui",
    # Messages
    "UserInput",
    "ToolProgress",
    "StreamingUpdate",
    "VimModeChanged",
    "ThemeChanged",
    # Screens
    "HelpScreen",
    "SessionsScreen",
    "PluginsScreen",
    "HooksScreen",
    "SettingsScreen",
    "StatsScreen",
    "MessageHistoryScreen",
    "DoctorScreen",
    "ConfigScreen",
    # Widgets
    "ThemeType",
    "ThemeManager",
    "VimMode",
    "VimModeIndicator",
    "VimHandler",
    "StatusWidget",
    "TokenCounterWidget",
    "ToolProgressWidget",
    "MessageListWidget",
    "CodeBlockWidget",
    "MarkdownWidget",
    "HistoryBrowserWidget",
    "StatsTableWidget",
    "ThemeSelectorWidget",
    "CommandPaletteWidget",
]

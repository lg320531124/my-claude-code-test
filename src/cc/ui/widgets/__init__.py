"""Enhanced UI widgets."""

from __future__ import annotations
from enum import Enum
from typing import Optional, ClassVar, Dict, List

# Try to import textual-dependent widgets
try:
    from textual.widget import Widget
    from textual.containers import Horizontal, Vertical, VerticalScroll
    from textual.widgets import Static, Button, Label, Input, ProgressBar, DataTable
    from textual.reactive import reactive
    from textual.message import Message
    from rich.text import Text
    from rich.syntax import Syntax
    from rich.markdown import Markdown
    from rich.table import Table
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False
    Widget = None
    Horizontal = None
    Vertical = None
    VerticalScroll = None
    Static = None
    Button = None
    Label = None
    Input = None
    ProgressBar = None
    DataTable = None
    Text = None
    Syntax = None
    Markdown = None
    Table = None


class ThemeType(Enum):
    """Available themes."""
    DARK = "dark"
    LIGHT = "light"
    MONO = "mono"
    GRUVBOX = "gruvbox"
    NORD = "nord"
    DRACULA = "dracula"
    SOLARIZED = "solarized"


class ThemeManager:
    """Manage UI themes."""

    THEMES: ClassVar[Dict[str, str]] = {
        "dark": "$surface: #1e1e2e;",
        "light": "$surface: #eff1f5;",
        "mono": "$surface: #ffffff;",
        "gruvbox": "$surface: #282828;",
        "nord": "$surface: #2e3440;",
        "dracula": "$surface: #282a36;",
        "solarized": "$surface: #002b36;",
    }

    def __init__(self):
        self._current_theme = "dark"

    def get_theme_css(self, theme_name: str) -> str:
        """Get CSS for a theme."""
        return self.THEMES.get(theme_name, self.THEMES["dark"])

    def set_theme(self, theme_name: str) -> None:
        """Set current theme."""
        if theme_name in self.THEMES:
            self._current_theme = theme_name

    def get_current_theme(self) -> str:
        """Get current theme name."""
        return self._current_theme

    def get_all_themes(self) -> List[str]:
        """Get all available theme names."""
        return list(self.THEMES.keys())


# Basic widgets (no textual dependency)
from .token_bar import (
    TokenBarStyle,
    TokenUsage,
    TokenBarConfig,
    TokenBarWidget,
    get_token_bar,
    update_token_usage,
)
from .tool_progress import (
    ToolProgressState,
    ToolProgressInfo,
    ToolProgressConfig,
    ToolProgressWidget,
    get_tool_progress,
)
from .permission_bar import (
    PermissionBarStyle,
    PermissionPrompt,
    PermissionBarConfig,
    PermissionBarWidget,
    get_permission_bar,
)
from .virtual_list import (
    ScrollDirection,
    VirtualListConfig,
    VirtualListState,
    VirtualListWidget,
    create_virtual_list,
)
from .message_list import (
    MessageRole,
    MessageItem,
    MessageListConfig,
    MessageListWidget,
)
from .message_row import (
    MessageStatus,
    MessageRowConfig,
    MessageRowData,
    MessageRowWidget,
)
from .token_warning import (
    WarningLevel,
    TokenWarningConfig,
    TokenWarningWidget,
)

__all__ = [
    # Theme
    "ThemeType",
    "ThemeManager",
    "_TEXTUAL_AVAILABLE",
    # Basic widgets
    "TokenBarStyle",
    "TokenUsage",
    "TokenBarConfig",
    "TokenBarWidget",
    "get_token_bar",
    "update_token_usage",
    "ToolProgressState",
    "ToolProgressInfo",
    "ToolProgressConfig",
    "ToolProgressWidget",
    "get_tool_progress",
    "PermissionBarStyle",
    "PermissionPrompt",
    "PermissionBarConfig",
    "PermissionBarWidget",
    "get_permission_bar",
    "ScrollDirection",
    "VirtualListConfig",
    "VirtualListState",
    "VirtualListWidget",
    "create_virtual_list",
    # Message list
    "MessageRole",
    "MessageItem",
    "MessageListConfig",
    "MessageListWidget",
    # Message row
    "MessageStatus",
    "MessageRowConfig",
    "MessageRowData",
    "MessageRowWidget",
    # Token warning
    "WarningLevel",
    "TokenWarningConfig",
    "TokenWarningWidget",
]

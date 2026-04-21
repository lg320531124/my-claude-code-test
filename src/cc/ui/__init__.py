"""UI module - Terminal User Interface."""

from __future__ import annotations

# Try to import textual-dependent modules
try:
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
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False
    ClaudeCodeApp = None
    MainScreen = None
    MessageWidget = None
    InputWidget = None
    UserInput = None
    ToolProgress = None
    StreamingUpdate = None
    VimModeChanged = None
    ThemeChanged = None
    run_tui = None

# Import ThemeManager from widgets (no textual dependency)
from .widgets import ThemeManager, ThemeType

# Screens (optional)
try:
    from .screens import (
        HelpScreen,
        SessionsScreen,
        PluginsScreen,
        HooksScreen,
    )
except ImportError:
    HelpScreen = None
    SessionsScreen = None
    PluginsScreen = None
    HooksScreen = None

# Dialogs (optional)
try:
    from .dialogs import (
        PermissionDialog,
        MCPServerDialog,
        ModelPickerDialog,
        ThemePickerDialog,
        HelpDialog,
        FeedbackDialog,
        UpdateDialog,
        ErrorDialog,
        ConfirmDialog,
    )
except ImportError:
    PermissionDialog = None
    MCPServerDialog = None
    ModelPickerDialog = None
    ThemePickerDialog = None
    HelpDialog = None
    FeedbackDialog = None
    UpdateDialog = None
    ErrorDialog = None
    ConfirmDialog = None

# Widgets (basic - no textual dependency)
from .widgets.token_bar import (
    TokenBarStyle,
    TokenUsage,
    TokenBarConfig,
    TokenBarWidget,
    get_token_bar,
    update_token_usage,
)
from .widgets.tool_progress import (
    ToolProgressState,
    ToolProgressInfo,
    ToolProgressConfig,
    ToolProgressWidget,
    get_tool_progress,
)
from .widgets.permission_bar import (
    PermissionBarStyle,
    PermissionPrompt,
    PermissionBarConfig,
    PermissionBarWidget,
    get_permission_bar,
)
from .widgets.virtual_list import (
    ScrollDirection,
    VirtualListConfig,
    VirtualListState,
    VirtualListWidget,
    create_virtual_list,
)

__all__ = [
    # App (optional)
    "ClaudeCodeApp",
    "MainScreen",
    "MessageWidget",
    "InputWidget",
    "UserInput",
    "ToolProgress",
    "StreamingUpdate",
    "VimModeChanged",
    "ThemeChanged",
    "run_tui",
    "_TEXTUAL_AVAILABLE",
    # Theme
    "ThemeManager",
    "ThemeType",
    # Screens (optional)
    "HelpScreen",
    "SessionsScreen",
    "PluginsScreen",
    "HooksScreen",
    # Dialogs (optional)
    "PermissionDialog",
    "MCPServerDialog",
    "ModelPickerDialog",
    "ThemePickerDialog",
    "HelpDialog",
    "FeedbackDialog",
    "UpdateDialog",
    "ErrorDialog",
    "ConfirmDialog",
    # Basic widgets (no textual)
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
]

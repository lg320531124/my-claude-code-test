"""UI Dialogs - Modal dialogs for user interaction."""

from __future__ import annotations

# Try to import textual-dependent dialogs
try:
    from .permission import PermissionDialog, PermissionLevel, PermissionResult
    from .mcp_server import MCPServerDialog, MCPServerApproval
    from .model import ModelPickerDialog, ModelInfo
    from .theme import ThemePickerDialog, ThemeInfo
    from .help import HelpDialog, HelpSection
    from .feedback import FeedbackDialog, FeedbackType
    from .update import UpdateDialog, UpdateInfo
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False
    PermissionDialog = None
    PermissionLevel = None
    PermissionResult = None
    MCPServerDialog = None
    MCPServerApproval = None
    ModelPickerDialog = None
    ModelInfo = None
    ThemePickerDialog = None
    ThemeInfo = None
    HelpDialog = None
    HelpSection = None
    FeedbackDialog = None
    FeedbackType = None
    UpdateDialog = None
    UpdateInfo = None

# Basic dialogs (no textual dependency)
from .error import ErrorDialog, ErrorInfo, ErrorType, get_error_display
from .confirm import ConfirmDialog, ConfirmAction, ConfirmResult, confirm

__all__ = [
    # Textual dialogs (optional)
    "PermissionDialog",
    "PermissionLevel",
    "PermissionResult",
    "MCPServerDialog",
    "MCPServerApproval",
    "ModelPickerDialog",
    "ModelInfo",
    "ThemePickerDialog",
    "ThemeInfo",
    "HelpDialog",
    "HelpSection",
    "FeedbackDialog",
    "FeedbackType",
    "UpdateDialog",
    "UpdateInfo",
    "_TEXTUAL_AVAILABLE",
    # Basic dialogs (no textual)
    "ErrorDialog",
    "ErrorInfo",
    "ErrorType",
    "get_error_display",
    "ConfirmDialog",
    "ConfirmAction",
    "ConfirmResult",
    "confirm",
]

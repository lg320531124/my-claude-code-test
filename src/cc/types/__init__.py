"""Core types for Claude Code Python."""

from __future__ import annotations
from .message import (
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    TextBlock,
    ContentBlock,
    ProgressMessage,
    AttachmentMessage,
    SystemMessage,
    create_user_message,
)
from .tool import (
    Tool,
    ToolDef,
    Tools,
    ToolResult,
    ToolInput,
    ToolUseContext,
    ToolProgress,
    ToolProgressData,
    ValidationResult,
    build_tool,
    tool_matches_name,
    find_tool_by_name,
)
from .permission import (
    PermissionResult,
    PermissionDecision,
    PermissionMode,
    PermissionRule,
    PermissionConfig,
    ToolPermissionContext,
    get_empty_tool_permission_context,
)

__all__ = [
    # Messages
    "Message",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "ToolResultBlock",
    "ToolUseBlock",
    "TextBlock",
    "ContentBlock",
    "ProgressMessage",
    "AttachmentMessage",
    "SystemMessage",
    "create_user_message",
    # Tools
    "Tool",
    "ToolDef",
    "Tools",
    "ToolResult",
    "ToolInput",
    "ToolUseContext",
    "ToolProgress",
    "ToolProgressData",
    "ValidationResult",
    "build_tool",
    "tool_matches_name",
    "find_tool_by_name",
    # Permissions
    "PermissionResult",
    "PermissionDecision",
    "PermissionMode",
    "PermissionRule",
    "PermissionConfig",
    "ToolPermissionContext",
    "get_empty_tool_permission_context",
]
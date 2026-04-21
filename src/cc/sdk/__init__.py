"""SDK Module - Claude Code Agent SDK types and functions.

Provides public SDK API for building custom tools and sessions.
"""

from __future__ import annotations

from .core_types import (
    SDKMessage,
    SDKUserMessage,
    SDKResultMessage,
    SDKAssistantMessage,
    SDKSystemMessage,
    SDKSessionInfo,
    SDKContentBlock,
    SDKTextBlock,
    SDKToolUseBlock,
    SDKToolResultBlock,
    MessageRole,
)

from .control_types import (
    SDKControlRequest,
    SDKControlResponse,
    SDKControlCancelRequest,
    SDKControlPermissionRequest,
    SDKControlInterruptRequest,
)

from .runtime_types import (
    SDKSession,
    SDKSessionOptions,
    Query,
    Options,
    ListSessionsOptions,
    GetSessionInfoOptions,
    SessionMutationOptions,
    ForkSessionOptions,
    ForkSessionResult,
    AbortError,
)

__all__ = [
    # Core types
    "SDKMessage",
    "SDKUserMessage",
    "SDKResultMessage",
    "SDKAssistantMessage",
    "SDKSystemMessage",
    "SDKSessionInfo",
    "SDKContentBlock",
    "SDKTextBlock",
    "SDKToolUseBlock",
    "SDKToolResultBlock",
    "MessageRole",
    # Control types
    "SDKControlRequest",
    "SDKControlResponse",
    "SDKControlCancelRequest",
    "SDKControlPermissionRequest",
    "SDKControlInterruptRequest",
    # Runtime types
    "SDKSession",
    "SDKSessionOptions",
    "Query",
    "Options",
    "ListSessionsOptions",
    "GetSessionInfoOptions",
    "SessionMutationOptions",
    "ForkSessionOptions",
    "ForkSessionResult",
    "AbortError",
]
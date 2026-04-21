"""Remote Module - WebSocket sessions for CCR communication.

Provides WebSocket client and session management for remote Claude Code sessions.
"""

from __future__ import annotations

from .websocket import (
    SessionsWebSocket,
    SessionsWebSocketCallbacks,
    WebSocketState,
)
from .manager import (
    RemoteSessionManager,
    RemoteSessionConfig,
    RemoteSessionCallbacks,
    RemotePermissionResponse,
    create_remote_session_config,
)

__all__ = [
    # WebSocket
    "SessionsWebSocket",
    "SessionsWebSocketCallbacks",
    "WebSocketState",
    # Manager
    "RemoteSessionManager",
    "RemoteSessionConfig",
    "RemoteSessionCallbacks",
    "RemotePermissionResponse",
    "create_remote_session_config",
]
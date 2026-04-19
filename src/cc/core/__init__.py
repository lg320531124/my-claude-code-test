"""Core module."""

from __future__ import annotations

# Engine (optional - requires anthropic SDK)
try:
    from .engine import QueryEngine, QueryStats, MessageHistory, ToolExecutor
    _ENGINE_AVAILABLE = True
except ImportError:
    _ENGINE_AVAILABLE = False
    QueryEngine = None
    QueryStats = None
    MessageHistory = None
    ToolExecutor = None

from .session import Session, SessionManager

# REPL (optional)
try:
    from .repl import REPL, run_repl, StreamingDisplay
    _REPL_AVAILABLE = True
except ImportError:
    _REPL_AVAILABLE = False
    REPL = None
    run_repl = None
    StreamingDisplay = None

# Recovery
try:
    from .recovery import (
        SessionPersistence,
        SessionRecovery,
        SessionHistory,
        SessionData,
        SessionMetadata,
        get_persistence,
        save_current_session,
        list_saved_sessions,
        load_session,
    )
    _RECOVERY_AVAILABLE = True
except ImportError:
    _RECOVERY_AVAILABLE = False
    SessionPersistence = None
    SessionRecovery = None
    SessionHistory = None
    SessionData = None
    SessionMetadata = None
    get_persistence = None
    save_current_session = None
    list_saved_sessions = None
    load_session = None

__all__ = [
    # Engine (optional)
    "QueryEngine",
    "QueryStats",
    "MessageHistory",
    "ToolExecutor",
    # Session
    "Session",
    "SessionManager",
    # REPL (optional)
    "REPL",
    "run_repl",
    "StreamingDisplay",
    # Recovery (optional)
    "SessionPersistence",
    "SessionRecovery",
    "SessionHistory",
    "SessionData",
    "SessionMetadata",
    "get_persistence",
    "save_current_session",
    "list_saved_sessions",
    "load_session",
]
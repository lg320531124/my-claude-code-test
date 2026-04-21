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

# Streaming
from .streaming import (
    SSEEventType,
    SSEEvent,
    StreamState,
    SSEParser,
    stream_api_response,
    collect_stream_text,
    collect_stream_tool_calls,
    StreamBuffer,
    ToolCallBuffer,
)

# Compression
from .compression import (
    CompressionStrategy,
    CompressionConfig,
    CompressionResult,
    MessageCompressor,
    compress_messages,
    should_compress,
    estimate_compression_savings,
)

# Executor
from .executor import (
    ExecutorMode,
    ExecutionPlan,
    PlanResult,
    CoreExecutor,
    get_core_executor,
    execute_tools,
)

# Rate Limiter
from .rate_limiter import (
    LimitType,
    RateLimit,
    LimitState,
    RateLimitConfig,
    RateLimiter,
)

# Error Recovery
from .error_recovery import (
    ErrorType,
    RecoveryStrategy,
    ErrorInfo,
    RecoveryConfig,
    RecoveryState,
    ErrorRecovery,
)

# Request Queue
from .request_queue import (
    QueuePriority,
    QueueStatus,
    QueuedRequest,
    QueueConfig,
    QueueStats,
    RequestQueue,
)

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
    # Streaming
    "SSEEventType",
    "SSEEvent",
    "StreamState",
    "SSEParser",
    "stream_api_response",
    "collect_stream_text",
    "collect_stream_tool_calls",
    "StreamBuffer",
    "ToolCallBuffer",
    # Compression
    "CompressionStrategy",
    "CompressionConfig",
    "CompressionResult",
    "MessageCompressor",
    "compress_messages",
    "should_compress",
    "estimate_compression_savings",
    # Executor
    "ExecutorMode",
    "ExecutionPlan",
    "PlanResult",
    "CoreExecutor",
    "get_core_executor",
    "execute_tools",
    # Rate Limiter
    "LimitType",
    "RateLimit",
    "LimitState",
    "RateLimitConfig",
    "RateLimiter",
    # Error Recovery
    "ErrorType",
    "RecoveryStrategy",
    "ErrorInfo",
    "RecoveryConfig",
    "RecoveryState",
    "ErrorRecovery",
    # Request Queue
    "QueuePriority",
    "QueueStatus",
    "QueuedRequest",
    "QueueConfig",
    "QueueStats",
    "RequestQueue",
]
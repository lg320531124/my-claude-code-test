"""Utilities module."""

from __future__ import annotations
from .config import Config
from .shell import run_command
from .file import get_file_info
from .log import get_logger
from .performance import (
    AsyncCache,
    cached,
    ParallelExecutor,
    RateLimiter,
    TokenOptimizer,
    PerformanceTracker,
    timed,
    get_cache,
    get_executor,
    get_tracker,
)
from .error_handling import (
    ErrorSeverity,
    ErrorCategory,
    ErrorInfo,
    ErrorHandler,
    error_handler,
    RecoveryManager,
    get_error_handler,
    get_recovery_manager,
)

__all__ = [
    # Config
    "Config",
    # Shell
    "run_command",
    # File
    "get_file_info",
    # Log
    "get_logger",
    # Performance
    "AsyncCache",
    "cached",
    "ParallelExecutor",
    "RateLimiter",
    "TokenOptimizer",
    "PerformanceTracker",
    "timed",
    "get_cache",
    "get_executor",
    "get_tracker",
    # Error handling
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorInfo",
    "ErrorHandler",
    "error_handler",
    "RecoveryManager",
    "get_error_handler",
    "get_recovery_manager",
]

"""Error Handling - Unified error handling, recovery, and logging."""

from __future__ import annotations
import asyncio
import traceback
import time
from dataclasses import dataclass, field
from enum import Enum
from functools import wraps
from pathlib import Path
from typing import Callable, TypeVar, Optional, List, Dict, Any
import logging


T = TypeVar("T")


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(Enum):
    """Error categories."""
    API = "api"
    TOOL = "tool"
    PERMISSION = "permission"
    NETWORK = "network"
    FILE = "file"
    MCP = "mcp"
    INTERNAL = "internal"
    USER = "user"


@dataclass
class ErrorInfo:
    """Detailed error information."""
    message: str
    category: ErrorCategory
    severity: ErrorSeverity
    timestamp: float
    exception_type: str
    stack_trace: Optional[str] = None
    context: dict = field(default_factory=dict)
    recovery_suggestion: Optional[str] = None
    retry_count: int = 0
    resolved: bool = False


class ErrorHandler:
    """Unified error handling."""

    def __init__(self, log_file: Optional[Path] = None):
        self.errors: List[...] = []
        self._handlers: Dict[ErrorCategory, Callable] = {}
        self._recovery_handlers: Dict[ErrorCategory, Callable] = {}
        self._log_file = log_file
        self._logger = self._setup_logger()

        # Default handlers
        self._setup_default_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Set up logging."""
        logger = logging.getLogger("claude-code")
        logger.setLevel(logging.DEBUG)

        # Console handler
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s"
        )
        console.setFormatter(formatter)
        logger.addHandler(console)

        # File handler if specified
        if self._log_file:
            file_handler = logging.FileHandler(self._log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

        return logger

    def _setup_default_handlers(self) -> None:
        """Set up default error handlers."""
        self._handlers[ErrorCategory.API] = self._handle_api_error
        self._handlers[ErrorCategory.TOOL] = self._handle_tool_error
        self._handlers[ErrorCategory.NETWORK] = self._handle_network_error
        self._handlers[ErrorCategory.FILE] = self._handle_file_error

    def handle(
        self,
        exception: Exception,
        category: ErrorCategory,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[dict] = None,
    ) -> ErrorInfo:
        """Handle an error."""
        error_info = ErrorInfo(
            message=str(exception),
            category=category,
            severity=severity,
            timestamp=time.time(),
            exception_type=type(exception).__name__,
            stack_trace=traceback.format_exc(),
            context=context or {},
        )

        self.errors.append(error_info)

        # Log
        self._log_error(error_info)

        # Call specific handler
        handler = self._handlers.get(category)
        if handler:
            handler(error_info)

        # Try recovery
        recovery = self._recovery_handlers.get(category)
        if recovery:
            try:
                recovery(error_info)
                error_info.resolved = True
            except Exception:
                pass

        return error_info

    def _log_error(self, error: ErrorInfo) -> None:
        """Log error."""
        level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL,
        }.get(error.severity, logging.ERROR)

        self._logger.log(level, f"[{error.category.value}] {error.message}")

    def _handle_api_error(self, error: ErrorInfo) -> None:
        """Handle API errors."""
        error.recovery_suggestion = "Check API key, base URL, and network connectivity"

        if "rate_limit" in error.message.lower():
            error.recovery_suggestion = "Wait and retry with exponential backoff"
        elif "timeout" in error.message.lower():
            error.recovery_suggestion = "Increase timeout or check network"
        elif "invalid_key" in error.message.lower():
            error.recovery_suggestion = "Verify ANTHROPIC_API_KEY is correct"

    def _handle_tool_error(self, error: ErrorInfo) -> None:
        """Handle tool errors."""
        error.recovery_suggestion = "Check tool inputs and permissions"

        tool_name = error.context.get("tool_name", "")
        if tool_name:
            error.recovery_suggestion = f"Check {tool_name} execution parameters"

    def _handle_network_error(self, error: ErrorInfo) -> None:
        """Handle network errors."""
        error.recovery_suggestion = "Check network connectivity and retry"

    def _handle_file_error(self, error: ErrorInfo) -> None:
        """Handle file errors."""
        if "not found" in error.message.lower():
            error.recovery_suggestion = "Check file path exists"
        elif "permission" in error.message.lower():
            error.recovery_suggestion = "Check file permissions"
        elif "too large" in error.message.lower():
            error.recovery_suggestion = "File may exceed limits, use chunked reading"

    def set_handler(self, category: ErrorCategory, handler: Callable) -> None:
        """Set custom handler for category."""
        self._handlers[category] = handler

    def set_recovery(self, category: ErrorCategory, handler: Callable) -> None:
        """Set recovery handler."""
        self._recovery_handlers[category] = handler

    def get_errors(
        self,
        category: Optional[ErrorCategory] = None,
        severity: Optional[ErrorSeverity] = None,
        unresolved_only: bool = False,
    ) -> List[ErrorInfo]:
        """Get filtered errors."""
        filtered = self.errors

        if category:
            filtered = [e for e in filtered if e.category == category]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]
        if unresolved_only:
            filtered = [e for e in filtered if not e.resolved]

        return filtered

    def get_stats(self) -> dict:
        """Get error statistics."""
        by_category = {}
        by_severity = {}

        for error in self.errors:
            cat = error.category.value
            sev = error.severity.value

            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_errors": len(self.errors),
            "resolved": sum(1 for e in self.errors if e.resolved),
            "by_category": by_category,
            "by_severity": by_severity,
        }

    def clear_resolved(self) -> int:
        """Clear resolved errors."""
        count = sum(1 for e in self.errors if e.resolved)
        self.errors = [e for e in self.errors if not e.resolved]
        return count


def error_handler(
    category: ErrorCategory,
    severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    retry_count: int = 0,
    retry_delay: float = 1.0,
):
    """Decorator for error handling."""
    handler = ErrorHandler()

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            last_error = None

            while attempts <= retry_count:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    attempts += 1

                    if attempts <= retry_count:
                        await asyncio.sleep(retry_delay * attempts)
                    else:
                        error_info = handler.handle(
                            e,
                            category,
                            severity,
                            context={
                                "function": func.__name__,
                                "args": str(args)[:100],
                                "retry_count": attempts,
                            },
                        )
                        raise

            raise last_error

        return wrapper

    return decorator


class RecoveryManager:
    """Manage error recovery strategies."""

    def __init__(self):
        self._strategies: Dict[str, Callable] = field(default_factory=dict)
        self._recovery_history: List[...] = field(default_factory=list)

    def register_strategy(self, name: str, strategy: Callable) -> None:
        """Register recovery strategy."""
        self._strategies[name] = strategy

    async def attempt_recovery(
        self,
        error: ErrorInfo,
        strategy_name: Optional[str] = None,
    ) -> bool:
        """Attempt recovery."""
        # Find strategy
        if strategy_name:
            strategy = self._strategies.get(strategy_name)
        else:
            # Auto-select based on category
            strategy = self._get_auto_strategy(error)

        if not strategy:
            return False

        # Attempt
        try:
            await strategy(error)
            error.resolved = True

            self._recovery_history.append({
                "timestamp": time.time(),
                "error_category": error.category.value,
                "strategy": strategy_name or "auto",
                "success": True,
            })

            return True
        except Exception as e:
            self._recovery_history.append({
                "timestamp": time.time(),
                "error_category": error.category.value,
                "strategy": strategy_name or "auto",
                "success": False,
                "error": str(e),
            })
            return False

    def _get_auto_strategy(self, error: ErrorInfo) -> Callable | None:
        """Get automatic recovery strategy."""
        if error.category == ErrorCategory.API:
            return self._strategies.get("retry_with_backoff")
        elif error.category == ErrorCategory.NETWORK:
            return self._strategies.get("reconnect")
        elif error.category == ErrorCategory.FILE:
            return self._strategies.get("check_permissions")

        return None

    def get_history(self) -> List[dict]:
        """Get recovery history."""
        return self._recovery_history


# Default recovery strategies
async def retry_with_backoff(error: ErrorInfo, max_attempts: int = 3) -> None:
    """Retry with exponential backoff."""
    for attempt in range(max_attempts):
        delay = 2 ** attempt
        await asyncio.sleep(delay)


async def reconnect(error: ErrorInfo) -> None:
    """Reconnect strategy."""
    # Would reconnect to API/MCP
    await asyncio.sleep(1)


async def check_permissions(error: ErrorInfo) -> None:
    """Check permissions strategy."""
    # Would verify permissions
    pass


# Global instances
_error_handler: Optional[ErrorHandler] = None
_recovery_manager: Optional[RecoveryManager] = None


def get_error_handler() -> ErrorHandler:
    """Get global error handler."""
    global _error_handler
    if _error_handler is None:
        log_file = Path.home() / ".claude" / "logs" / "errors.log"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        _error_handler = ErrorHandler(log_file)

        # Register default strategies
        recovery = get_recovery_manager()
        recovery.register_strategy("retry_with_backoff", retry_with_backoff)
        recovery.register_strategy("reconnect", reconnect)
        recovery.register_strategy("check_permissions", check_permissions)

        _error_handler.set_recovery(ErrorCategory.API, lambda e: retry_with_backoff(e))
        _error_handler.set_recovery(ErrorCategory.NETWORK, lambda e: reconnect(e))

    return _error_handler


def get_recovery_manager() -> RecoveryManager:
    """Get global recovery manager."""
    global _recovery_manager
    if _recovery_manager is None:
        _recovery_manager = RecoveryManager()
    return _recovery_manager


__all__ = [
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorInfo",
    "ErrorHandler",
    "error_handler",
    "RecoveryManager",
    "get_error_handler",
    "get_recovery_manager",
]

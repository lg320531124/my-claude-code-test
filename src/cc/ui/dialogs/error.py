"""Error Dialog - Display error messages."""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional, List
from enum import Enum


class ErrorType(Enum):
    """Error types."""
    API_ERROR = "api_error"
    TOOL_ERROR = "tool_error"
    PERMISSION_ERROR = "permission_error"
    NETWORK_ERROR = "network_error"
    FILE_ERROR = "file_error"
    SYNTAX_ERROR = "syntax_error"
    RUNTIME_ERROR = "runtime_error"
    UNKNOWN = "unknown"


@dataclass
class ErrorInfo:
    """Error information."""
    type: ErrorType = ErrorType.UNKNOWN
    message: str = ""
    details: Optional[str] = None
    stack_trace: Optional[str] = None
    suggestion: Optional[str] = None
    recoverable: bool = False
    timestamp: Optional[float] = None
    context: dict = field(default_factory=dict)


@dataclass
class ErrorDialog:
    """Error dialog for displaying errors."""
    
    title: str = "Error"
    errors: List[ErrorInfo] = field(default_factory=list)
    show_details: bool = False
    can_retry: bool = False
    can_dismiss: bool = True
    
    def add_error(self, error: ErrorInfo) -> None:
        """Add error to dialog."""
        self.errors.append(error)
    
    def clear(self) -> None:
        """Clear all errors."""
        self.errors.clear()
    
    def get_summary(self) -> str:
        """Get error summary."""
        if not self.errors:
            return "No errors"
        
        type_counts = {}
        for error in self.errors:
            type_counts[error.type.value] = type_counts.get(error.type.value, 0) + 1
        
        summary_parts = []
        for type_name, count in type_counts.items():
            summary_parts.append(f"{count} {type_name}")
        
        return ", ".join(summary_parts)
    
    def get_most_recent(self) -> Optional[ErrorInfo]:
        """Get most recent error."""
        if not self.errors:
            return None
        return self.errors[-1]
    
    def get_recoverable_errors(self) -> List[ErrorInfo]:
        """Get recoverable errors."""
        return [e for e in self.errors if e.recoverable]


class ErrorDisplay:
    """Error display manager."""
    
    def __init__(self):
        self._dialog = ErrorDialog()
        self._history: List[ErrorInfo] = []
        self._max_history = 100
    
    def show_error(
        self,
        message: str,
        type: ErrorType = ErrorType.UNKNOWN,
        details: Optional[str] = None,
        suggestion: Optional[str] = None,
        recoverable: bool = False,
    ) -> ErrorInfo:
        """Show error message."""
        import time
        
        error = ErrorInfo(
            type=type,
            message=message,
            details=details,
            suggestion=suggestion,
            recoverable=recoverable,
            timestamp=time.time(),
        )
        
        self._dialog.add_error(error)
        self._history.append(error)
        
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]
        
        return error
    
    def dismiss(self) -> None:
        """Dismiss current errors."""
        self._dialog.clear()
    
    def get_history(self, limit: int = 10) -> List[ErrorInfo]:
        """Get error history."""
        return self._history[-limit:]
    
    def get_dialog(self) -> ErrorDialog:
        """Get current dialog."""
        return self._dialog


# Global error display
_error_display: Optional[ErrorDisplay] = None


def get_error_display() -> ErrorDisplay:
    """Get global error display."""
    global _error_display
    if _error_display is None:
        _error_display = ErrorDisplay()
    return _error_display


def show_error(message: str, type: ErrorType = ErrorType.UNKNOWN) -> ErrorInfo:
    """Show error message."""
    return get_error_display().show_error(message, type)


__all__ = [
    "ErrorType",
    "ErrorInfo",
    "ErrorDialog",
    "ErrorDisplay",
    "get_error_display",
    "show_error",
]

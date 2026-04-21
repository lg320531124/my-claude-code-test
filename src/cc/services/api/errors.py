"""API Errors - Error classification and handling."""

from __future__ import annotations
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum


class ErrorType(Enum):
    """API error types."""
    AUTHENTICATION = "authentication"
    PERMISSION = "permission"
    RATE_LIMIT = "rate_limit"
    INVALID_REQUEST = "invalid_request"
    NOT_FOUND = "not_found"
    SERVER_ERROR = "server_error"
    OVERLOAD = "overload"
    TIMEOUT = "timeout"
    NETWORK = "network"
    CONTENT_FILTER = "content_filter"
    CONTEXT_LENGTH = "context_length"
    MODEL_NOT_FOUND = "model_not_found"
    STREAMING_ERROR = "streaming_error"
    UNKNOWN = "unknown"


@dataclass
class APIError:
    """Structured API error."""
    type: ErrorType
    message: str
    code: Optional[str] = None
    status_code: Optional[int] = None
    request_id: Optional[str] = None
    retry_after: Optional[int] = None
    details: Optional[Dict[str, Any]] = None

    def is_retryable(self) -> bool:
        """Check if error is retryable."""
        retryable_types = [
            ErrorType.RATE_LIMIT,
            ErrorType.SERVER_ERROR,
            ErrorType.OVERLOAD,
            ErrorType.TIMEOUT,
            ErrorType.NETWORK,
            ErrorType.STREAMING_ERROR,
        ]
        return self.type in retryable_types

    def should_prompt_user(self) -> bool:
        """Check if error should prompt user."""
        prompt_types = [
            ErrorType.AUTHENTICATION,
            ErrorType.PERMISSION,
            ErrorType.CONTENT_FILTER,
            ErrorType.CONTEXT_LENGTH,
        ]
        return self.type in prompt_types

    def to_display_message(self) -> str:
        """Convert to user-friendly message."""
        messages = {
            ErrorType.AUTHENTICATION: "Authentication failed. Please check your API key.",
            ErrorType.PERMISSION: "Permission denied. Check your account permissions.",
            ErrorType.RATE_LIMIT: f"Rate limit exceeded. Please wait {self.retry_after or 60} seconds.",
            ErrorType.INVALID_REQUEST: "Invalid request. Please check your input.",
            ErrorType.NOT_FOUND: "Resource not found.",
            ErrorType.SERVER_ERROR: "Server error. Retrying...",
            ErrorType.OVERLOAD: "API is overloaded. Retrying...",
            ErrorType.TIMEOUT: "Request timed out. Retrying...",
            ErrorType.NETWORK: "Network error. Please check your connection.",
            ErrorType.CONTENT_FILTER: "Content filtered by safety guidelines.",
            ErrorType.CONTEXT_LENGTH: "Context too long. Please reduce input size.",
            ErrorType.MODEL_NOT_FOUND: "Model not available.",
            ErrorType.STREAMING_ERROR: "Streaming interrupted. Retrying...",
            ErrorType.UNKNOWN: f"Unknown error: {self.message}",
        }
        return messages.get(self.type, self.message)


class ErrorClassifier:
    """Classify API errors."""

    def classify(self, error: Exception) -> APIError:
        """Classify an exception into APIError."""
        error_str = str(error)
        error_lower = error_str.lower()

        # Check for specific error types

        if "authentication" in error_lower or "invalid api key" in error_lower or "401" in error_str:
            return APIError(
                type=ErrorType.AUTHENTICATION,
                message=error_str,
                status_code=401,
            )

        if "permission" in error_lower or "403" in error_str:
            return APIError(
                type=ErrorType.PERMISSION,
                message=error_str,
                status_code=403,
            )

        if "rate limit" in error_lower or "429" in error_str:
            # Try to extract retry_after
            retry_after = self._extract_retry_after(error_str)
            return APIError(
                type=ErrorType.RATE_LIMIT,
                message=error_str,
                status_code=429,
                retry_after=retry_after,
            )

        if "invalid" in error_lower or "400" in error_str:
            return APIError(
                type=ErrorType.INVALID_REQUEST,
                message=error_str,
                status_code=400,
            )

        if "not found" in error_lower or "404" in error_str:
            return APIError(
                type=ErrorType.NOT_FOUND,
                message=error_str,
                status_code=404,
            )

        if "500" in error_str or "502" in error_str or "503" in error_str:
            return APIError(
                type=ErrorType.SERVER_ERROR,
                message=error_str,
                status_code=int(error_str.split()[0]) if error_str.split()[0].isdigit() else 500,
            )

        if "overload" in error_lower:
            return APIError(
                type=ErrorType.OVERLOAD,
                message=error_str,
            )

        if "timeout" in error_lower:
            return APIError(
                type=ErrorType.TIMEOUT,
                message=error_str,
            )

        if "connection" in error_lower or "network" in error_lower:
            return APIError(
                type=ErrorType.NETWORK,
                message=error_str,
            )

        if "content filter" in error_lower or "safety" in error_lower:
            return APIError(
                type=ErrorType.CONTENT_FILTER,
                message=error_str,
            )

        if "context length" in error_lower or "too long" in error_lower or "max_tokens" in error_lower:
            return APIError(
                type=ErrorType.CONTEXT_LENGTH,
                message=error_str,
            )

        if "model" in error_lower and ("not found" in error_lower or "unavailable" in error_lower):
            return APIError(
                type=ErrorType.MODEL_NOT_FOUND,
                message=error_str,
            )

        if "stream" in error_lower:
            return APIError(
                type=ErrorType.STREAMING_ERROR,
                message=error_str,
            )

        return APIError(
            type=ErrorType.UNKNOWN,
            message=error_str,
        )

    def _extract_retry_after(self, error_str: str) -> Optional[int]:
        """Extract retry-after value from error."""
        import re

        # Look for "retry after X seconds" or similar
        patterns = [
            r"retry after (\d+)",
            r"wait (\d+) seconds",
            r"retry-after.*?(\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, error_str.lower())
            if match:
                return int(match.group(1))

        return None


class ErrorHandler:
    """Handle API errors."""

    def __init__(self):
        self._classifier = ErrorClassifier()
        self._error_history: list = []

    def handle(self, error: Exception) -> APIError:
        """Handle an error."""
        classified = self._classifier.classify(error)
        self._error_history.append(classified)
        return classified

    def get_error_history(self) -> list:
        """Get error history."""
        return self._error_history.copy()

    def clear_history(self) -> None:
        """Clear error history."""
        self._error_history.clear()

    def get_retry_recommendation(self, error: APIError) -> Optional[int]:
        """Get recommended retry delay."""
        if not error.is_retryable():
            return None

        if error.retry_after:
            return error.retry_after

        # Default recommendations by type
        recommendations = {
            ErrorType.RATE_LIMIT: 60,
            ErrorType.SERVER_ERROR: 5,
            ErrorType.OVERLOAD: 30,
            ErrorType.TIMEOUT: 10,
            ErrorType.NETWORK: 5,
            ErrorType.STREAMING_ERROR: 3,
        }

        return recommendations.get(error.type, 10)


def classify_error(error: Exception) -> APIError:
    """Classify an error."""
    return ErrorClassifier().classify(error)


__all__ = [
    "ErrorType",
    "APIError",
    "ErrorClassifier",
    "ErrorHandler",
    "classify_error",
]
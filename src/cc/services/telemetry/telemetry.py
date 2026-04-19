"""Telemetry Service - Usage telemetry."""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from datetime import datetime


class TelemetryConfig(BaseModel):
    """Telemetry configuration."""
    enabled: bool = Field(default=True, description="Enable telemetry")
    endpoint: Optional[str] = Field(default=None, description="Telemetry endpoint")
    batch_size: int = Field(default=100, description="Batch size for sending")
    flush_interval: int = Field(default=60, description="Flush interval in seconds")


class TelemetryEvent(BaseModel):
    """Telemetry event."""
    event_type: str
    timestamp: float
    session_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class TelemetryService:
    """Usage telemetry service."""

    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self._events: List[TelemetryEvent] = []
        self._session_id: Optional[str] = None
        self._start_time: float = 0

    def start_session(self, session_id: str) -> None:
        """Start a new session."""
        self._session_id = session_id
        self._start_time = time.time()
        self.track("session_start", {"session_id": session_id})

    def end_session(self) -> None:
        """End current session."""
        if self._session_id:
            duration = time.time() - self._start_time
            self.track("session_end", {
                "session_id": self._session_id,
                "duration_seconds": duration,
            })
            self.flush()
            self._session_id = None

    def track(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Track an event."""
        if not self.config.enabled:
            return

        event = TelemetryEvent(
            event_type=event_type,
            timestamp=time.time(),
            session_id=self._session_id,
            data=data or {},
        )
        self._events.append(event)

        # Auto-flush if batch size reached
        if len(self._events) >= self.config.batch_size:
            self.flush()

    def track_tool_use(self, tool_name: str, success: bool, duration_ms: float) -> None:
        """Track tool usage."""
        self.track("tool_use", {
            "tool": tool_name,
            "success": success,
            "duration_ms": duration_ms,
        })

    def track_api_call(self, model: str, input_tokens: int, output_tokens: int) -> None:
        """Track API call."""
        self.track("api_call", {
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
        })

    def track_command(self, command: str) -> None:
        """Track slash command."""
        self.track("command", {"command": command})

    def track_error(self, error_type: str, error_message: str) -> None:
        """Track error."""
        self.track("error", {
            "type": error_type,
            "message": error_message[:100],  # Truncate long messages
        })

    def flush(self) -> None:
        """Flush events."""
        if not self._events:
            return

        # In production, would send to endpoint
        # For now, save to local file
        if self.config.endpoint:
            # Would POST to endpoint
            pass
        else:
            # Local storage
            storage_path = Path.home() / ".claude" / "telemetry"
            storage_path.mkdir(parents=True, exist_ok=True)

            date_str = datetime.now().strftime("%Y-%m-%d")
            file_path = storage_path / f"events_{date_str}.jsonl"

            with open(file_path, "a") as f:
                for event in self._events:
                    f.write(event.model_dump_json() + "\n")

        self._events.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get telemetry stats."""
        return {
            "enabled": self.config.enabled,
            "events_pending": len(self._events),
            "session_id": self._session_id,
            "session_duration": time.time() - self._start_time if self._start_time else 0,
        }


# Singleton
_telemetry_service: Optional[TelemetryService] = None


def get_telemetry_service(config: Optional[TelemetryConfig] = None) -> TelemetryService:
    """Get telemetry service singleton."""
    global _telemetry_service
    if _telemetry_service is None:
        _telemetry_service = TelemetryService(config)
    return _telemetry_service


def track_event(event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
    """Convenience tracking function."""
    get_telemetry_service().track(event_type, data)


__all__ = [
    "TelemetryConfig",
    "TelemetryEvent",
    "TelemetryService",
    "get_telemetry_service",
    "track_event",
]
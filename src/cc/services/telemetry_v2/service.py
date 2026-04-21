"""Telemetry Service - Collect and send telemetry."""

from __future__ import annotations
import asyncio
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import platform
import sys

from ...utils.log import get_logger

logger = get_logger(__name__)


class TelemetryEvent(Enum):
    """Telemetry event types."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    TOOL_CALL = "tool_call"
    API_CALL = "api_call"
    ERROR = "error"
    COMMAND = "command"
    UI_ACTION = "ui_action"
    PERFORMANCE = "performance"


@dataclass
class TelemetryConfig:
    """Telemetry configuration."""
    enabled: bool = True
    endpoint: Optional[str] = None
    batch_size: int = 10
    flush_interval: float = 60.0
    include_system_info: bool = True
    anonymize: bool = True


@dataclass
class TelemetryEventRecord:
    """Telemetry event record."""
    event_type: TelemetryEvent
    timestamp: datetime
    data: Dict[str, Any] = field(default_factory=dict)
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SystemInfo:
    """System information."""
    platform: str
    python_version: str
    os_name: str
    os_version: str
    arch: str


class TelemetryService:
    """Telemetry collection service."""

    def __init__(self, config: Optional[TelemetryConfig] = None):
        self.config = config or TelemetryConfig()
        self._events: List[TelemetryEventRecord] = []
        self._session_id: Optional[str] = None
        self._system_info: Optional[SystemInfo] = None

        if self.config.include_system_info:
            self._collect_system_info()

    def _collect_system_info(self) -> None:
        """Collect system information."""
        self._system_info = SystemInfo(
            platform=platform.system(),
            python_version=sys.version,
            os_name=platform.platform(),
            os_version=platform.version(),
            arch=platform.machine(),
        )

    async def start_session(
        self,
        session_id: str
    ) -> None:
        """Start telemetry session."""
        self._session_id = session_id

        await self.record_event(
            TelemetryEvent.SESSION_START,
            {"session_id": session_id}
        )

    async def end_session(self) -> None:
        """End telemetry session."""
        await self.record_event(
            TelemetryEvent.SESSION_END,
            {"session_id": self._session_id}
        )

        # Flush remaining events
        await self.flush()

    async def record_event(
        self,
        event_type: TelemetryEvent,
        data: Optional[Dict[str, Any]] = None
    ) -> TelemetryEventRecord:
        """Record telemetry event."""
        if not self.config.enabled:
            return TelemetryEventRecord(
                event_type=event_type,
                timestamp=datetime.now(),
            )

        # Anonymize if needed
        if self.config.anonymize:
            data = self._anonymize_data(data or {})

        event = TelemetryEventRecord(
            event_type=event_type,
            timestamp=datetime.now(),
            data=data,
            session_id=self._session_id,
        )

        self._events.append(event)

        # Check flush conditions
        if len(self._events) >= self.config.batch_size:
            await self.flush()

        return event

    def _anonymize_data(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Anonymize sensitive data."""
        # Remove sensitive keys
        sensitive_keys = [
            "password", "token", "key", "secret",
            "api_key", "auth", "credential",
        ]

        result = {}

        for key, value in data.items():
            if any(s in key.lower() for s in sensitive_keys):
                result[key] = "[REDACTED]"
            elif isinstance(value, str) and len(value) > 100:
                # Truncate long strings
                result[key] = value[:100] + "..."
            elif isinstance(value, dict):
                result[key] = self._anonymize_data(value)
            else:
                result[key] = value

        return result

    async def record_tool_call(
        self,
        tool_name: str,
        success: bool,
        duration: float
    ) -> None:
        """Record tool call event."""
        await self.record_event(
            TelemetryEvent.TOOL_CALL,
            {
                "tool": tool_name,
                "success": success,
                "duration_ms": duration * 1000,
            }
        )

    async def record_api_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration: float
    ) -> None:
        """Record API call event."""
        await self.record_event(
            TelemetryEvent.API_CALL,
            {
                "model": model,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "duration_ms": duration * 1000,
            }
        )

    async def record_error(
        self,
        error_type: str,
        message: str
    ) -> None:
        """Record error event."""
        await self.record_event(
            TelemetryEvent.ERROR,
            {
                "error_type": error_type,
                "message": message[:200],
            }
        )

    async def record_command(
        self,
        command: str
    ) -> None:
        """Record command execution."""
        await self.record_event(
            TelemetryEvent.COMMAND,
            {"command": command}
        )

    async def flush(self) -> int:
        """Flush events to endpoint."""
        if not self._events:
            return 0

        if not self.config.endpoint:
            # Just clear if no endpoint
            count = len(self._events)
            self._events.clear()
            return count

        # Send to endpoint
        batch = self._events[:self.config.batch_size]
        self._events = self._events[self.config.batch_size:]

        try:
            # In real implementation, would send HTTP request
            logger.debug(f"Flushed {len(batch)} telemetry events")
        except Exception as e:
            logger.error(f"Telemetry flush failed: {e}")
            # Re-add events
            self._events.extend(batch)

        return len(batch)

    async def get_events(
        self,
        limit: int = 100
    ) -> List[TelemetryEventRecord]:
        """Get recorded events."""
        return self._events[-limit:]

    async def export_events(self) -> str:
        """Export events as JSON."""
        events_data = [
            {
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "data": e.data,
                "session_id": e.session_id,
            }
            for e in self._events
        ]

        export_data = {
            "system_info": {
                "platform": self._system_info.platform if self._system_info else None,
                "python_version": self._system_info.python_version if self._system_info else None,
            },
            "events": events_data,
        }

        return json.dumps(export_data, indent=2)

    async def clear(self) -> int:
        """Clear all events."""
        count = len(self._events)
        self._events.clear()
        return count

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable telemetry."""
        self.config.enabled = enabled

    def is_enabled(self) -> bool:
        """Check if telemetry is enabled."""
        return self.config.enabled


__all__ = [
    "TelemetryEvent",
    "TelemetryConfig",
    "TelemetryEventRecord",
    "SystemInfo",
    "TelemetryService",
]
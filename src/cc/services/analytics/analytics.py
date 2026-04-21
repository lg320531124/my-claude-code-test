"""Analytics Service - Event tracking and reporting."""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Callable, Any, Callable, Optional
from dataclasses import dataclass, field
from enum import Enum


class EventType(Enum):
    """Event types for tracking."""
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    QUERY = "query"
    TOOL_CALL = "tool_call"
    ERROR = "error"
    PERMISSION_PROMPT = "permission_prompt"
    COMPACT = "compact"
    MCP_CONNECT = "mcp_connect"
    MCP_DISCONNECT = "mcp_disconnect"
    CACHE_HIT = "cache_hit"
    CACHE_MISS = "cache_miss"
    TOKEN_USAGE = "token_usage"
    COST_UPDATE = "cost_update"


@dataclass
class AnalyticsEvent:
    """Single analytics event."""
    event_type: str
    timestamp: float
    data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    session_id: Optional[str] = None
    user_id: Optional[str] = None


class EventSink:
    """Sink for collecting events."""

    def __init__(self, max_events: int = 10000):
        self.events: List[AnalyticsEvent] = []
        self.max_events = max_events
        self._flush_callbacks: List[Callable] = []

    def add(self, event: AnalyticsEvent) -> None:
        """Add event to sink."""
        self.events.append(event)

        # Trim if needed
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]

    def flush(self) -> List[AnalyticsEvent]:
        """Flush all events."""
        events = self.events.copy()
        self.events.clear()

        for callback in self._flush_callbacks:
            callback(events)

        return events

    def add_flush_callback(self, callback: Callable) -> None:
        """Add flush callback."""
        self._flush_callbacks.append(callback)

    def get_events_by_type(self, event_type: str) -> List[AnalyticsEvent]:
        """Get events by type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_stats(self) -> dict:
        """Get sink statistics."""
        by_type: Dict[str, int] = {}
        for event in self.events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        return {
            "total_events": len(self.events),
            "by_type": by_type,
            "max_events": self.max_events,
        }


class AnalyticsConfig:
    """Analytics configuration."""

    def __init__(
        self,
        enabled: bool = True,
        flush_interval: float = 60.0,
        log_file: Optional[Path] = None,
        remote_endpoint: Optional[str] = None,
    ):
        self.enabled = enabled
        self.flush_interval = flush_interval
        self.log_file = log_file
        self.remote_endpoint = remote_endpoint


class AnalyticsService:
    """Service for tracking analytics events."""

    def __init__(self, config: Optional[AnalyticsConfig] = None):
        self.config = config or AnalyticsConfig()
        self.sink = EventSink()
        self._flush_task: asyncio.Task | None = None
        self._running = False
        self._session_id: Optional[str] = None
        self._user_id: Optional[str] = None

    def start(self) -> None:
        """Start analytics service."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._flush_loop())

        # Record session start
        self.track(EventType.SESSION_START)

    def stop(self) -> None:
        """Stop analytics service."""
        self._running = False

        # Record session end
        self.track(EventType.SESSION_END)

        # Final flush
        self.sink.flush()

        if self._flush_task:
            self._flush_task.cancel()

    async def _flush_loop(self) -> None:
        """Periodic flush loop."""
        while self._running:
            await asyncio.sleep(self.config.flush_interval)
            self._do_flush()

    def _do_flush(self) -> None:
        """Perform flush."""
        if not self.config.enabled:
            return

        events = self.sink.flush()

        if self.config.log_file and events:
            self._write_to_file(events)

        if self.config.remote_endpoint and events:
            # Would send to remote endpoint
            pass

    def _write_to_file(self, events: List[AnalyticsEvent]) -> None:
        """Write events to log file."""
        if not self.config.log_file:
            return

        self.config.log_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config.log_file, "a") as f:
            for event in events:
                data = {
                    "event_type": event.event_type,
                    "timestamp": event.timestamp,
                    "data": event.data,
                    "metadata": event.metadata,
                    "session_id": event.session_id,
                }
                f.write(json.dumps(data) + "\n")

    def track(
        self,
        event_type: EventType | str,
        data: Optional[dict] = None,
        metadata: Optional[dict] = None,
    ) -> None:
        """Track an event."""
        if not self.config.enabled:
            return

        event = AnalyticsEvent(
            event_type=event_type.value if isinstance(event_type, EventType) else event_type,
            timestamp=time.time(),
            data=data or {},
            metadata=metadata or {},
            session_id=self._session_id,
            user_id=self._user_id,
        )

        self.sink.add(event)

    def set_session_id(self, session_id: str) -> None:
        """Set current session ID."""
        self._session_id = session_id

    def set_user_id(self, user_id: str) -> None:
        """Set user ID."""
        self._user_id = user_id

    def get_events(self) -> List[AnalyticsEvent]:
        """Get all events."""
        return self.sink.events.copy()

    def get_events_by_type(self, event_type: str) -> List[AnalyticsEvent]:
        """Get events by type."""
        return self.sink.get_events_by_type(event_type)

    def get_summary(self) -> dict:
        """Get analytics summary."""
        events = self.sink.events

        # Count by type
        by_type: Dict[str, int] = {}
        for event in events:
            by_type[event.event_type] = by_type.get(event.event_type, 0) + 1

        # Calculate timing stats
        if events:
            first_event = min(e.timestamp for e in events)
            last_event = max(e.timestamp for e in events)
            duration = last_event - first_event
        else:
            duration = 0

        return {
            "total_events": len(events),
            "by_type": by_type,
            "session_duration_seconds": duration,
            "session_id": self._session_id,
        }


class FirstPartyEventLogger:
    """Logger for first-party events."""

    def __init__(self, service: AnalyticsService):
        self.service = service

    def log_query(self, model: str, tokens_in: int, tokens_out: int) -> None:
        """Log query event."""
        self.service.track(
            EventType.QUERY,
            data={
                "model": model,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
            },
        )

    def log_tool_call(self, tool_name: str, success: bool, duration_ms: float) -> None:
        """Log tool call."""
        self.service.track(
            EventType.TOOL_CALL,
            data={
                "tool_name": tool_name,
                "success": success,
                "duration_ms": duration_ms,
            },
        )

    def log_error(self, error_type: str, message: str) -> None:
        """Log error."""
        self.service.track(
            EventType.ERROR,
            data={
                "error_type": error_type,
                "message": message,
            },
        )

    def log_permission_prompt(self, tool_name: str, decision: str) -> None:
        """Log permission prompt."""
        self.service.track(
            EventType.PERMISSION_PROMPT,
            data={
                "tool_name": tool_name,
                "decision": decision,
            },
        )

    def log_compact(self, messages_before: int, messages_after: int, tokens_saved: int) -> None:
        """Log compact event."""
        self.service.track(
            EventType.COMPACT,
            data={
                "messages_before": messages_before,
                "messages_after": messages_after,
                "tokens_saved": tokens_saved,
            },
        )

    def log_token_usage(self, total_in: int, total_out: int) -> None:
        """Log token usage."""
        self.service.track(
            EventType.TOKEN_USAGE,
            data={
                "total_in": total_in,
                "total_out": total_out,
            },
        )


class GrowthBookIntegration:
    """Integration with GrowthBook feature flags."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._features: Dict[str, Any] = {}
        self._last_refresh: float = 0

    def refresh_features(self) -> None:
        """Refresh feature flags."""
        # Would call GrowthBook API
        pass

    def is_feature_enabled(self, feature_key: str) -> bool:
        """Check if feature is enabled."""
        feature = self._features.get(feature_key)
        if feature:
            return feature.get("enabled", False)
        return False

    def get_feature_value(self, feature_key: str, default: Any = None) -> Any:
        """Get feature value."""
        feature = self._features.get(feature_key)
        if feature:
            return feature.get("value", default)
        return default


# Global service
_analytics_service: Optional[AnalyticsService] = None


def get_analytics_service() -> AnalyticsService:
    """Get global analytics service."""
    global _analytics_service
    if _analytics_service is None:
        log_file = Path.home() / ".claude" / "logs" / "analytics.jsonl"
        _analytics_service = AnalyticsService(AnalyticsConfig(log_file=log_file))
    return _analytics_service


def start_analytics() -> None:
    """Start global analytics."""
    service = get_analytics_service()
    service.start()


def stop_analytics() -> None:
    """Stop global analytics."""
    service = get_analytics_service()
    service.stop()


def track_event(event_type: EventType | str, data: Optional[dict] = None) -> None:
    """Track event globally."""
    service = get_analytics_service()
    service.track(event_type, data)


__all__ = [
    "EventType",
    "AnalyticsEvent",
    "EventSink",
    "AnalyticsConfig",
    "AnalyticsService",
    "FirstPartyEventLogger",
    "GrowthBookIntegration",
    "get_analytics_service",
    "start_analytics",
    "stop_analytics",
    "track_event",
]

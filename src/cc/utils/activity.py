"""Activity Manager - Track user/system activity."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ActivityType(Enum):
    """Activity types."""
    USER_INPUT = "user_input"
    TOOL_CALL = "tool_call"
    API_REQUEST = "api_request"
    FILE_OPERATION = "file_operation"
    COMMAND = "command"
    SESSION = "session"
    ERROR = "error"


@dataclass
class ActivityEvent:
    """Activity event."""
    type: ActivityType
    timestamp: datetime
    details: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0
    success: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActivityStats:
    """Activity statistics."""
    total_events: int = 0
    events_by_type: Dict[str, int] = field(default_factory=dict)
    success_rate: float = 0.0
    avg_duration: float = 0.0
    last_activity: Optional[datetime] = None


class ActivityManager:
    """Manage activity tracking."""
    
    def __init__(self, max_events: int = 1000):
        self._max_events = max_events
        self._events: List[ActivityEvent] = []
        self._current_session: Optional[str] = None
        self._session_start: Optional[datetime] = None
    
    def record(self, event: ActivityEvent) -> None:
        """Record activity event."""
        self._events.append(event)
        
        # Trim if over limit
        if len(self._events) > self._max_events:
            self._events = self._events[-self._max_events:]
    
    def record_event(
        self,
        type: ActivityType,
        details: Dict[str, Any] = None,
        duration: float = 0.0,
        success: bool = True,
    ) -> ActivityEvent:
        """Record event with convenience method."""
        event = ActivityEvent(
            type=type,
            timestamp=datetime.now(),
            details=details or {},
            duration=duration,
            success=success,
        )
        self.record(event)
        return event
    
    def start_session(self, session_id: str) -> None:
        """Start session."""
        self._current_session = session_id
        self._session_start = datetime.now()
        
        self.record_event(
            ActivityType.SESSION,
            {"session_id": session_id, "action": "start"},
        )
    
    def end_session(self) -> Optional[float]:
        """End session."""
        if not self._current_session:
            return None
        
        duration = 0.0
        if self._session_start:
            duration = (datetime.now() - self._session_start).total_seconds()
        
        self.record_event(
            ActivityType.SESSION,
            {"session_id": self._current_session, "action": "end", "duration": duration},
            duration=duration,
        )
        
        self._current_session = None
        self._session_start = None
        
        return duration
    
    def get_stats(self) -> ActivityStats:
        """Get activity statistics."""
        if not self._events:
            return ActivityStats()
        
        events_by_type: Dict[str, int] = {}
        total_duration = 0.0
        success_count = 0
        
        for event in self._events:
            type_name = event.type.value
            events_by_type[type_name] = events_by_type.get(type_name, 0) + 1
            
            if event.success:
                success_count += 1
            
            total_duration += event.duration
        
        return ActivityStats(
            total_events=len(self._events),
            events_by_type=events_by_type,
            success_rate=success_count / len(self._events),
            avg_duration=total_duration / len(self._events),
            last_activity=self._events[-1].timestamp if self._events else None,
        )
    
    def get_events(self, type: ActivityType = None, limit: int = 50) -> List[ActivityEvent]:
        """Get events."""
        events = self._events
        
        if type:
            events = [e for e in events if e.type == type]
        
        return events[-limit:]
    
    def get_recent(self, minutes: int = 5) -> List[ActivityEvent]:
        """Get recent events."""
        cutoff = datetime.now()
        from datetime import timedelta
        cutoff = cutoff - timedelta(minutes=minutes)
        
        return [e for e in self._events if e.timestamp >= cutoff]
    
    def clear(self) -> None:
        """Clear all events."""
        self._events.clear()


__all__ = [
    "ActivityType",
    "ActivityEvent",
    "ActivityStats",
    "ActivityManager",
]

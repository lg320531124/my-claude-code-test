"""Agent Summary Service - Summarize agent activities."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class SummaryType(Enum):
    """Summary types."""
    SESSION = "session"
    TASK = "task"
    CONVERSATION = "conversation"
    PERFORMANCE = "performance"


class TimeRange(Enum):
    """Time ranges."""
    HOUR = "hour"
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class SummaryConfig:
    """Summary configuration."""
    include_tools: bool = True
    include_errors: bool = True
    include_metrics: bool = True
    max_items: int = 100
    detail_level: str = "medium"


@dataclass
class AgentSummary:
    """Agent summary."""
    type: SummaryType
    start_time: datetime
    end_time: datetime
    total_requests: int = 0
    total_tools: int = 0
    total_errors: int = 0
    avg_response_time: float = 0.0
    top_tools: List[str] = field(default_factory=list)
    error_types: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SessionSummary:
    """Session summary."""
    session_id: str
    duration: float
    message_count: int
    tool_count: int
    error_count: int
    topics: List[str] = field(default_factory=list)
    actions: List[str] = field(default_factory=list)


class AgentSummaryService:
    """Service for summarizing agent activities."""

    def __init__(self, config: Optional[SummaryConfig] = None):
        self.config = config or SummaryConfig()
        self._summaries: Dict[str, AgentSummary] = {}
        self._session_summaries: Dict[str, SessionSummary] = {}
        self._activity_log: List[Dict[str, Any]] = []

    async def generate_summary(
        self,
        summary_type: SummaryType,
        time_range: TimeRange,
        session_id: Optional[str] = None
    ) -> AgentSummary:
        """Generate summary for given type and time range."""
        # Calculate time bounds
        end_time = datetime.now()
        start_time = self._get_start_time(time_range, end_time)

        # Filter activity log
        activities = self._filter_activities(start_time, end_time)

        # Calculate metrics
        total_requests = len(activities)
        total_tools = sum(1 for a in activities if a.get("type") == "tool")
        total_errors = sum(1 for a in activities if a.get("type") == "error")

        # Calculate response times
        response_times = [
            a.get("duration", 0)
            for a in activities
            if a.get("duration")
        ]
        avg_response_time = (
            sum(response_times) / len(response_times)
            if response_times else 0.0
        )

        # Get top tools
        tool_counts: Dict[str, int] = {}
        for a in activities:
            if a.get("type") == "tool":
                tool_name = a.get("name", "unknown")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        top_tools = sorted(
            tool_counts.keys(),
            key=lambda x: tool_counts[x],
            reverse=True
        )[:10]

        # Get error types
        error_counts: Dict[str, int] = {}
        for a in activities:
            if a.get("type") == "error":
                error_type = a.get("error_type", "unknown")
                error_counts[error_type] = error_counts.get(error_type, 0) + 1

        error_types = sorted(
            error_counts.keys(),
            key=lambda x: error_counts[x],
            reverse=True
        )[:5]

        # Generate highlights
        highlights = self._generate_highlights(activities)

        # Create summary
        summary = AgentSummary(
            type=summary_type,
            start_time=start_time,
            end_time=end_time,
            total_requests=total_requests,
            total_tools=total_tools,
            total_errors=total_errors,
            avg_response_time=avg_response_time,
            top_tools=top_tools,
            error_types=error_types,
            highlights=highlights,
        )

        # Store summary
        summary_key = f"{summary_type.value}_{time_range.value}"
        self._summaries[summary_key] = summary

        logger.info(f"Generated summary: {summary_type.value}")
        return summary

    async def generate_session_summary(
        self,
        session_id: str
    ) -> SessionSummary:
        """Generate summary for a specific session."""
        # Get session activities
        session_activities = [
            a for a in self._activity_log
            if a.get("session_id") == session_id
        ]

        if not session_activities:
            return SessionSummary(
                session_id=session_id,
                duration=0,
                message_count=0,
                tool_count=0,
                error_count=0,
            )

        # Calculate duration
        first_time = min(a.get("timestamp", datetime.now()) for a in session_activities)
        last_time = max(a.get("timestamp", datetime.now()) for a in session_activities)
        duration = (last_time - first_time).total_seconds()

        # Count items
        message_count = sum(1 for a in session_activities if a.get("type") == "message")
        tool_count = sum(1 for a in session_activities if a.get("type") == "tool")
        error_count = sum(1 for a in session_activities if a.get("type") == "error")

        # Extract topics and actions
        topics = self._extract_topics(session_activities)
        actions = self._extract_actions(session_activities)

        summary = SessionSummary(
            session_id=session_id,
            duration=duration,
            message_count=message_count,
            tool_count=tool_count,
            error_count=error_count,
            topics=topics,
            actions=actions,
        )

        self._session_summaries[session_id] = summary
        return summary

    async def log_activity(
        self,
        activity_type: str,
        data: Dict[str, Any],
        session_id: Optional[str] = None
    ) -> None:
        """Log an activity for summary generation."""
        activity = {
            "type": activity_type,
            "timestamp": datetime.now(),
            "session_id": session_id,
            **data,
        }

        self._activity_log.append(activity)

        # Trim log if too large
        if len(self._activity_log) > self.config.max_items:
            self._activity_log = self._activity_log[-self.config.max_items:]

    def _get_start_time(
        self,
        time_range: TimeRange,
        end_time: datetime
    ) -> datetime:
        """Calculate start time based on time range."""
        from datetime import timedelta

        deltas = {
            TimeRange.HOUR: timedelta(hours=1),
            TimeRange.DAY: timedelta(days=1),
            TimeRange.WEEK: timedelta(weeks=1),
            TimeRange.MONTH: timedelta(days=30),
        }

        return end_time - deltas.get(time_range, timedelta(days=1))

    def _filter_activities(
        self,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict[str, Any]]:
        """Filter activities by time range."""
        return [
            a for a in self._activity_log
            if start_time <= a.get("timestamp", datetime.min) <= end_time
        ]

    def _generate_highlights(
        self,
        activities: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate highlights from activities."""
        highlights = []

        # Most used tool
        tool_counts: Dict[str, int] = {}
        for a in activities:
            if a.get("type") == "tool":
                tool_name = a.get("name", "unknown")
                tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

        if tool_counts:
            top_tool = max(tool_counts.keys(), key=lambda x: tool_counts[x])
            count = tool_counts[top_tool]
            highlights.append(f"Most used tool: {top_tool} ({count} times)")

        # Longest request
        durations = [
            (a.get("duration", 0), a)
            for a in activities
            if a.get("duration")
        ]
        if durations:
            longest = max(durations, key=lambda x: x[0])
            highlights.append(f"Longest request: {longest[0]:.2f}s")

        # Error rate
        total = len(activities)
        errors = sum(1 for a in activities if a.get("type") == "error")
        if total > 0 and errors > 0:
            error_rate = errors / total * 100
            highlights.append(f"Error rate: {error_rate:.1f}%")

        return highlights[:5]

    def _extract_topics(
        self,
        activities: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract topics from activities."""
        topics = []

        for a in activities:
            if a.get("type") == "message":
                content = a.get("content", "")
                if content:
                    # Simple topic extraction
                    words = content.split()
                    if len(words) >= 3:
                        topics.append(words[0])

        return topics[:10]

    def _extract_actions(
        self,
        activities: List[Dict[str, Any]]
    ) -> List[str]:
        """Extract actions from activities."""
        actions = []

        for a in activities:
            if a.get("type") == "tool":
                tool_name = a.get("name", "unknown")
                action = f"Used {tool_name}"
                if a.get("result"):
                    action += f" - {a.get('result')}"
                actions.append(action)

        return actions[:20]

    async def get_summary(
        self,
        summary_type: SummaryType,
        time_range: TimeRange
    ) -> Optional[AgentSummary]:
        """Get cached summary."""
        summary_key = f"{summary_type.value}_{time_range.value}"
        return self._summaries.get(summary_key)

    async def get_session_summary(
        self,
        session_id: str
    ) -> Optional[SessionSummary]:
        """Get cached session summary."""
        return self._session_summaries.get(session_id)

    async def clear_summaries(self) -> int:
        """Clear all summaries."""
        count = len(self._summaries) + len(self._session_summaries)
        self._summaries.clear()
        self._session_summaries.clear()
        return count

    async def clear_activity_log(self) -> int:
        """Clear activity log."""
        count = len(self._activity_log)
        self._activity_log.clear()
        return count


__all__ = [
    "SummaryType",
    "TimeRange",
    "SummaryConfig",
    "AgentSummary",
    "SessionSummary",
    "AgentSummaryService",
]
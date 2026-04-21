"""Agent Summary - Summarize agent activities."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class AgentRole(Enum):
    """Agent roles."""
    ORCHESTRATOR = "orchestrator"
    EXECUTOR = "executor"
    ANALYZER = "analyzer"
    REVIEWER = "reviewer"
    PLANNER = "planner"
    DEBUGGER = "debugger"


@dataclass
class AgentActivity:
    """Agent activity record."""
    agent_id: str
    role: AgentRole
    action: str
    timestamp: datetime
    duration: float = 0.0
    success: bool = True
    result_summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentSummaryConfig:
    """Summary configuration."""
    max_activities: int = 100
    include_details: bool = True
    group_by_role: bool = True
    time_window: Optional[float] = None  # Seconds


@dataclass
class AgentSummary:
    """Agent activity summary."""
    total_activities: int
    successful: int
    failed: int
    total_duration: float
    by_role: Dict[str, int] = field(default_factory=dict)
    recent_activities: List[AgentActivity] = field(default_factory=list)
    key_findings: List[str] = field(default_factory=list)


class AgentSummarizer:
    """Summarize agent activities."""

    def __init__(self, config: Optional[AgentSummaryConfig] = None):
        self.config = config or AgentSummaryConfig()
        self._activities: List[AgentActivity] = []

    async def record(
        self,
        agent_id: str,
        role: AgentRole,
        action: str,
        success: bool = True,
        duration: float = 0.0,
        result_summary: Optional[str] = None
    ) -> AgentActivity:
        """Record agent activity."""
        activity = AgentActivity(
            agent_id=agent_id,
            role=role,
            action=action,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            result_summary=result_summary,
        )

        self._activities.append(activity)

        # Trim if over limit
        if len(self._activities) > self.config.max_activities:
            self._activities = self._activities[-self.config.max_activities:]

        return activity

    async def summarize(
        self,
        agent_id: Optional[str] = None,
        role: Optional[AgentRole] = None
    ) -> AgentSummary:
        """Generate summary."""
        # Filter activities
        activities = self._activities

        if agent_id:
            activities = [a for a in activities if a.agent_id == agent_id]

        if role:
            activities = [a for a in activities if a.role == role]

        # Time window
        if self.config.time_window:
            cutoff = datetime.now() - datetime.timedelta(seconds=self.config.time_window)
            activities = [a for a in activities if a.timestamp >= cutoff]

        # Calculate metrics
        total = len(activities)
        successful = sum(1 for a in activities if a.success)
        failed = total - successful
        total_duration = sum(a.duration for a in activities)

        # Group by role
        by_role: Dict[str, int] = {}
        for a in activities:
            key = a.role.value
            by_role[key] = by_role.get(key, 0) + 1

        # Recent activities
        recent = activities[-10:] if self.config.include_details else []

        # Key findings
        findings = self._extract_findings(activities)

        return AgentSummary(
            total_activities=total,
            successful=successful,
            failed=failed,
            total_duration=total_duration,
            by_role=by_role,
            recent_activities=recent,
            key_findings=findings,
        )

    def _extract_findings(
        self,
        activities: List[AgentActivity]
    ) -> List[str]:
        """Extract key findings."""
        findings = []

        # Success rate
        if activities:
            success_rate = sum(1 for a in activities if a.success) / len(activities)
            findings.append(f"Success rate: {success_rate:.1%}")

        # Most active role
        role_counts: Dict[AgentRole, int] = {}
        for a in activities:
            role_counts[a.role] = role_counts.get(a.role, 0) + 1

        if role_counts:
            most_active = max(role_counts, key=role_counts.get)
            findings.append(f"Most active role: {most_active.value}")

        # Average duration
        durations = [a.duration for a in activities if a.duration > 0]
        if durations:
            avg_duration = sum(durations) / len(durations)
            findings.append(f"Average duration: {avg_duration:.2f}s")

        return findings

    async def get_activities(
        self,
        limit: int = 50
    ) -> List[AgentActivity]:
        """Get recent activities."""
        return self._activities[-limit:]

    async def clear(self) -> int:
        """Clear activities."""
        count = len(self._activities)
        self._activities.clear()
        return count

    async def export(
        self,
        format: str = "json"
    ) -> str:
        """Export summary."""
        summary = await self.summarize()

        if format == "json":
            import json

            data = {
                "total_activities": summary.total_activities,
                "successful": summary.successful,
                "failed": summary.failed,
                "total_duration": summary.total_duration,
                "by_role": summary.by_role,
                "key_findings": summary.key_findings,
            }

            return json.dumps(data, indent=2)

        # Text format
        lines = [
            f"Total activities: {summary.total_activities}",
            f"Successful: {summary.successful}",
            f"Failed: {summary.failed}",
            f"Total duration: {summary.total_duration:.2f}s",
            "",
            "By role:",
        ]

        for role, count in summary.by_role.items():
            lines.append(f"  {role}: {count}")

        lines.append("")
        lines.append("Key findings:")

        for finding in summary.key_findings:
            lines.append(f"  - {finding}")

        return "\n".join(lines)

    async def get_agent_stats(
        self,
        agent_id: str
    ) -> Dict[str, Any]:
        """Get stats for specific agent."""
        activities = [a for a in self._activities if a.agent_id == agent_id]

        if not activities:
            return {"error": f"No activities for agent {agent_id}"}

        return {
            "agent_id": agent_id,
            "total": len(activities),
            "success_rate": sum(1 for a in activities if a.success) / len(activities),
            "total_duration": sum(a.duration for a in activities),
            "roles": list(set(a.role.value for a in activities)),
        }


__all__ = [
    "AgentRole",
    "AgentActivity",
    "AgentSummaryConfig",
    "AgentSummary",
    "AgentSummarizer",
]
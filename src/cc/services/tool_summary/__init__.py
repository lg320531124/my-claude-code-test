"""Tool Summary - Summarize tool usage."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
from collections import defaultdict

from ...utils.log import get_logger

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Tool categories."""
    FILE = "file"
    SEARCH = "search"
    CODE = "code"
    WEB = "web"
    SYSTEM = "system"
    AGENT = "agent"
    MCP = "mcp"
    OTHER = "other"


@dataclass
class ToolUsage:
    """Tool usage record."""
    tool_name: str
    category: ToolCategory
    timestamp: datetime
    duration: float = 0.0
    success: bool = True
    error: Optional[str] = None
    input_size: int = 0
    output_size: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolSummaryConfig:
    """Summary configuration."""
    max_records: int = 1000
    include_errors: bool = True
    group_by_category: bool = True
    track_sizes: bool = True


@dataclass
class ToolSummary:
    """Tool usage summary."""
    total_calls: int
    successful: int
    failed: int
    total_duration: float
    by_tool: Dict[str, int]
    by_category: Dict[str, int]
    errors: List[str]
    most_used: List[str]
    slowest: List[str]


class ToolSummarizer:
    """Summarize tool usage."""

    # Tool category mapping
    TOOL_CATEGORIES: Dict[str, ToolCategory] = {
        "read": ToolCategory.FILE,
        "write": ToolCategory.FILE,
        "edit": ToolCategory.FILE,
        "glob": ToolCategory.SEARCH,
        "grep": ToolCategory.SEARCH,
        "web_fetch": ToolCategory.WEB,
        "web_search": ToolCategory.WEB,
        "bash": ToolCategory.SYSTEM,
        "agent": ToolCategory.AGENT,
        "mcp": ToolCategory.MCP,
        "lsp": ToolCategory.CODE,
    }

    def __init__(self, config: Optional[ToolSummaryConfig] = None):
        self.config = config or ToolSummaryConfig()
        self._usage: List[ToolUsage] = []

    def _get_category(self, tool_name: str) -> ToolCategory:
        """Get tool category."""
        # Check mapping
        for key, category in self.TOOL_CATEGORIES.items():
            if key in tool_name.lower():
                return category

        return ToolCategory.OTHER

    async def record(
        self,
        tool_name: str,
        success: bool = True,
        duration: float = 0.0,
        error: Optional[str] = None,
        input_size: int = 0,
        output_size: int = 0
    ) -> ToolUsage:
        """Record tool usage."""
        category = self._get_category(tool_name)

        usage = ToolUsage(
            tool_name=tool_name,
            category=category,
            timestamp=datetime.now(),
            duration=duration,
            success=success,
            error=error,
            input_size=input_size if self.config.track_sizes else 0,
            output_size=output_size if self.config.track_sizes else 0,
        )

        self._usage.append(usage)

        # Trim if over limit
        if len(self._usage) > self.config.max_records:
            self._usage = self._usage[-self.config.max_records:]

        return usage

    async def summarize(
        self,
        tool_name: Optional[str] = None,
        category: Optional[ToolCategory] = None
    ) -> ToolSummary:
        """Generate summary."""
        # Filter
        usage = self._usage

        if tool_name:
            usage = [u for u in usage if u.tool_name == tool_name]

        if category:
            usage = [u for u in usage if u.category == category]

        # Calculate metrics
        total = len(usage)
        successful = sum(1 for u in usage if u.success)
        failed = total - successful
        total_duration = sum(u.duration for u in usage)

        # By tool
        by_tool: Dict[str, int] = defaultdict(int)
        for u in usage:
            by_tool[u.tool_name] += 1

        # By category
        by_category: Dict[str, int] = defaultdict(int)
        for u in usage:
            by_category[u.category.value] += 1

        # Errors
        errors = [u.error for u in usage if u.error] if self.config.include_errors else []

        # Most used
        most_used = sorted(by_tool.keys(), key=lambda t: by_tool[t], reverse=True)[:5]

        # Slowest
        tool_durations: Dict[str, float] = defaultdict(float)
        tool_counts: Dict[str, int] = defaultdict(int)

        for u in usage:
            tool_durations[u.tool_name] += u.duration
            tool_counts[u.tool_name] += 1

        avg_durations = {
            t: tool_durations[t] / tool_counts[t]
            for t in tool_counts
        }

        slowest = sorted(avg_durations.keys(), key=lambda t: avg_durations[t], reverse=True)[:5]

        return ToolSummary(
            total_calls=total,
            successful=successful,
            failed=failed,
            total_duration=total_duration,
            by_tool=dict(by_tool),
            by_category=dict(by_category),
            errors=errors[:10],
            most_used=most_used,
            slowest=slowest,
        )

    async def get_usage_history(
        self,
        limit: int = 100
    ) -> List[ToolUsage]:
        """Get usage history."""
        return self._usage[-limit:]

    async def clear(self) -> int:
        """Clear usage."""
        count = len(self._usage)
        self._usage.clear()
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
                "total_calls": summary.total_calls,
                "successful": summary.successful,
                "failed": summary.failed,
                "total_duration": summary.total_duration,
                "by_tool": summary.by_tool,
                "by_category": summary.by_category,
            }

            return json.dumps(data, indent=2)

        # Text format
        lines = [
            f"Total calls: {summary.total_calls}",
            f"Successful: {summary.successful}",
            f"Failed: {summary.failed}",
            f"Total duration: {summary.total_duration:.2f}s",
            "",
            "Most used tools:",
        ]

        for tool in summary.most_used:
            count = summary.by_tool.get(tool, 0)
            lines.append(f"  {tool}: {count}")

        lines.append("")
        lines.append("By category:")

        for cat, count in summary.by_category.items():
            lines.append(f"  {cat}: {count}")

        return "\n".join(lines)

    async def get_tool_stats(
        self,
        tool_name: str
    ) -> Dict[str, Any]:
        """Get stats for specific tool."""
        usage = [u for u in self._usage if u.tool_name == tool_name]

        if not usage:
            return {"error": f"No usage for tool {tool_name}"}

        return {
            "tool_name": tool_name,
            "total_calls": len(usage),
            "success_rate": sum(1 for u in usage if u.success) / len(usage),
            "avg_duration": sum(u.duration for u in usage) / len(usage),
            "total_input_size": sum(u.input_size for u in usage),
            "total_output_size": sum(u.output_size for u in usage),
            "category": usage[0].category.value,
        }


__all__ = [
    "ToolCategory",
    "ToolUsage",
    "ToolSummaryConfig",
    "ToolSummary",
    "ToolSummarizer",
]
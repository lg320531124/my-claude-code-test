"""Tool Summary Service - Summarize tool usage."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum
from datetime import datetime

from ...utils.log import get_logger

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Tool categories."""
    FILE = "file"
    BASH = "bash"
    WEB = "web"
    SEARCH = "search"
    MCP = "mcp"
    AGENT = "agent"
    OTHER = "other"


@dataclass
class ToolUsageStats:
    """Tool usage statistics."""
    tool_name: str
    category: ToolCategory
    total_calls: int = 0
    success_count: int = 0
    failure_count: int = 0
    avg_duration: float = 0.0
    total_tokens_used: int = 0
    last_used: Optional[datetime] = None


@dataclass
class ToolSummaryConfig:
    """Tool summary configuration."""
    track_tokens: bool = True
    track_duration: bool = True
    track_errors: bool = True
    max_history: int = 1000


@dataclass
class CategorySummary:
    """Summary for a tool category."""
    category: ToolCategory
    tools: List[str]
    total_calls: int
    success_rate: float
    avg_duration: float


class ToolSummaryService:
    """Service for summarizing tool usage."""

    def __init__(self, config: Optional[ToolSummaryConfig] = None):
        self.config = config or ToolSummaryConfig()
        self._usage_stats: Dict[str, ToolUsageStats] = {}
        self._call_history: List[Dict[str, Any]] = []

    def _get_category(self, tool_name: str) -> ToolCategory:
        """Get tool category from name."""
        if tool_name in ["read", "write", "edit", "glob", "grep", "list_files"]:
            return ToolCategory.FILE
        elif tool_name in ["bash", "process", "environment"]:
            return ToolCategory.BASH
        elif tool_name in ["web_fetch", "web_search"]:
            return ToolCategory.WEB
        elif tool_name in ["search", "tool_search"]:
            return ToolCategory.SEARCH
        elif tool_name.startswith("mcp_"):
            return ToolCategory.MCP
        elif tool_name in ["agent", "task_output", "task_stop"]:
            return ToolCategory.AGENT
        else:
            return ToolCategory.OTHER

    async def record_call(
        self,
        tool_name: str,
        success: bool,
        duration: Optional[float] = None,
        tokens_used: Optional[int] = None,
        error: Optional[str] = None
    ) -> None:
        """Record a tool call."""
        # Get or create stats
        if tool_name not in self._usage_stats:
            self._usage_stats[tool_name] = ToolUsageStats(
                tool_name=tool_name,
                category=self._get_category(tool_name),
            )

        stats = self._usage_stats[tool_name]

        # Update stats
        stats.total_calls += 1
        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1

        if duration is not None and self.config.track_duration:
            # Calculate average duration
            if stats.avg_duration > 0:
                stats.avg_duration = (
                    (stats.avg_duration * (stats.total_calls - 1) + duration)
                    / stats.total_calls
                )
            else:
                stats.avg_duration = duration

        if tokens_used is not None and self.config.track_tokens:
            stats.total_tokens_used += tokens_used

        stats.last_used = datetime.now()

        # Add to history
        call_record = {
            "tool": tool_name,
            "success": success,
            "duration": duration,
            "tokens": tokens_used,
            "error": error,
            "timestamp": datetime.now(),
        }
        self._call_history.append(call_record)

        # Trim history
        if len(self._call_history) > self.config.max_history:
            self._call_history = self._call_history[-self.config.max_history:]

    async def get_tool_stats(
        self,
        tool_name: str
    ) -> Optional[ToolUsageStats]:
        """Get stats for a specific tool."""
        return self._usage_stats.get(tool_name)

    async def get_all_stats(self) -> Dict[str, ToolUsageStats]:
        """Get all tool stats."""
        return self._usage_stats.copy()

    async def get_category_summary(
        self,
        category: ToolCategory
    ) -> CategorySummary:
        """Get summary for a category."""
        # Get tools in category
        tools = [
            name for name, stats in self._usage_stats.items()
            if stats.category == category
        ]

        if not tools:
            return CategorySummary(
                category=category,
                tools=[],
                total_calls=0,
                success_rate=0.0,
                avg_duration=0.0,
            )

        # Calculate totals
        total_calls = sum(self._usage_stats[t].total_calls for t in tools)
        total_success = sum(self._usage_stats[t].success_count for t in tools)
        total_duration = sum(self._usage_stats[t].avg_duration for t in tools)

        success_rate = total_success / total_calls if total_calls > 0 else 0.0
        avg_duration = total_duration / len(tools)

        return CategorySummary(
            category=category,
            tools=tools,
            total_calls=total_calls,
            success_rate=success_rate,
            avg_duration=avg_duration,
        )

    async def get_top_tools(
        self,
        limit: int = 10,
        by_calls: bool = True
    ) -> List[str]:
        """Get top tools by usage."""
        if by_calls:
            sorted_tools = sorted(
                self._usage_stats.keys(),
                key=lambda x: self._usage_stats[x].total_calls,
                reverse=True
            )
        else:
            sorted_tools = sorted(
                self._usage_stats.keys(),
                key=lambda x: self._usage_stats[x].success_count,
                reverse=True
            )

        return sorted_tools[:limit]

    async def get_error_tools(
        self,
        limit: int = 10
    ) -> List[str]:
        """Get tools with most errors."""
        sorted_tools = sorted(
            self._usage_stats.keys(),
            key=lambda x: self._usage_stats[x].failure_count,
            reverse=True
        )

        return [t for t in sorted_tools if self._usage_stats[t].failure_count > 0][:limit]

    async def get_summary_report(self) -> Dict[str, Any]:
        """Get comprehensive summary report."""
        # Category summaries
        category_summaries = {}
        for category in ToolCategory:
            category_summaries[category.value] = await self.get_category_summary(category)

        # Top tools
        top_tools = await self.get_top_tools()

        # Error tools
        error_tools = await self.get_error_tools()

        # Totals
        total_calls = sum(s.total_calls for s in self._usage_stats.values())
        total_success = sum(s.success_count for s in self._usage_stats.values())
        total_failures = sum(s.failure_count for s in self._usage_stats.values())
        total_tokens = sum(s.total_tokens_used for s in self._usage_stats.values())

        return {
            "total_calls": total_calls,
            "total_success": total_success,
            "total_failures": total_failures,
            "success_rate": total_success / total_calls if total_calls > 0 else 0.0,
            "total_tokens": total_tokens,
            "unique_tools": len(self._usage_stats),
            "top_tools": top_tools,
            "error_tools": error_tools,
            "categories": category_summaries,
        }

    async def clear_stats(self) -> int:
        """Clear all stats."""
        count = len(self._usage_stats)
        self._usage_stats.clear()
        return count

    async def clear_history(self) -> int:
        """Clear call history."""
        count = len(self._call_history)
        self._call_history.clear()
        return count


__all__ = [
    "ToolCategory",
    "ToolUsageStats",
    "ToolSummaryConfig",
    "CategorySummary",
    "ToolSummaryService",
]
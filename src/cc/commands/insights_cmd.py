"""Insights Command - Show insights/analytics."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class InsightData:
    """Insight data."""
    category: str
    title: str
    description: str
    value: Any
    trend: str = "stable"  # up, down, stable


async def run_insights() -> Dict[str, Any]:
    """Generate insights."""
    insights = []
    
    # Usage patterns
    usage_insight = await _analyze_usage()
    if usage_insight:
        insights.append(usage_insight)
    
    # Tool patterns
    tool_insight = await _analyze_tools()
    if tool_insight:
        insights.append(tool_insight)
    
    # Cost patterns
    cost_insight = await _analyze_costs()
    if cost_insight:
        insights.append(cost_insight)
    
    return {
        "success": True,
        "insights": [
            {
                "category": i.category,
                "title": i.title,
                "description": i.description,
                "value": i.value,
                "trend": i.trend,
            }
            for i in insights
        ],
    }


async def _analyze_usage() -> InsightData:
    """Analyze usage patterns."""
    stats_path = Path.home() / ".claude-code-py" / "stats.json"
    
    if not stats_path.exists():
        return None
    
    try:
        data = json.loads(stats_path.read_text())
        sessions = data.get("total_sessions", 0)
        
        if sessions > 100:
            return InsightData(
                category="usage",
                title="High Usage",
                description="You've been using Claude Code frequently",
                value=sessions,
                trend="up",
            )
        else:
            return InsightData(
                category="usage",
                title="Moderate Usage",
                description="Normal usage pattern",
                value=sessions,
                trend="stable",
            )
    except:
        return None


async def _analyze_tools() -> InsightData:
    """Analyze tool usage patterns."""
    stats_path = Path.home() / ".claude-code-py" / "stats.json"
    
    if not stats_path.exists():
        return None
    
    try:
        data = json.loads(stats_path.read_text())
        tools = data.get("most_used_tools", [])
        
        if tools:
            return InsightData(
                category="tools",
                title="Most Used Tools",
                description=f"Top tool: {tools[0]}",
                value=tools[:5],
                trend="stable",
            )
    except:
        pass
    
    return None


async def _analyze_costs() -> InsightData:
    """Analyze cost patterns."""
    stats_path = Path.home() / ".claude-code-py" / "stats.json"
    
    if not stats_path.exists():
        return None
    
    try:
        data = json.loads(stats_path.read_text())
        cost = data.get("total_cost", 0.0)
        
        return InsightData(
            category="cost",
            title="Total Cost",
            description="Cumulative API cost",
            value=f"${cost:.2f}",
            trend="up" if cost > 10 else "stable",
        )
    except:
        return None


class InsightsCommand:
    """Insights command implementation."""
    
    name = "insights"
    description = "Show usage insights"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute insights command."""
        return await run_insights()


__all__ = [
    "InsightData",
    "run_insights",
    "InsightsCommand",
]

"""Stats Command - Show usage statistics."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class UsageStats:
    """Usage statistics."""
    total_sessions: int = 0
    total_messages: int = 0
    total_tool_calls: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    avg_session_length: float = 0.0
    most_used_tools: List[str] = field(default_factory=list)


async def run_stats() -> Dict[str, Any]:
    """Show usage statistics."""
    stats = UsageStats()
    
    # Load stats from file if exists
    stats_path = Path.home() / ".claude-code-py" / "stats.json"
    
    if stats_path.exists():
        try:
            data = json.loads(stats_path.read_text())
            stats.total_sessions = data.get("total_sessions", 0)
            stats.total_messages = data.get("total_messages", 0)
            stats.total_tool_calls = data.get("total_tool_calls", 0)
            stats.total_tokens = data.get("total_tokens", 0)
            stats.total_cost = data.get("total_cost", 0.0)
            stats.most_used_tools = data.get("most_used_tools", [])
        except:
            pass
    
    # Calculate averages
    if stats.total_sessions > 0:
        stats.avg_session_length = stats.total_messages / stats.total_sessions
    
    return {
        "success": True,
        "stats": {
            "sessions": stats.total_sessions,
            "messages": stats.total_messages,
            "tool_calls": stats.total_tool_calls,
            "tokens": stats.total_tokens,
            "cost": f"${stats.total_cost:.2f}",
            "avg_session_length": stats.avg_session_length,
            "most_used_tools": stats.most_used_tools,
        },
    }


async def get_recent_stats(days: int = 7) -> Dict[str, Any]:
    """Get recent usage stats."""
    stats_path = Path.home() / ".claude-code-py" / "usage_history.json"
    
    if not stats_path.exists():
        return {"success": True, "recent": {}}
    
    try:
        data = json.loads(stats_path.read_text())
        
        cutoff = datetime.now() - timedelta(days=days)
        recent = {}
        
        for date_str, usage in data.items():
            try:
                date = datetime.fromisoformat(date_str)
                if date >= cutoff:
                    recent[date_str] = usage
            except:
                pass
        
        return {"success": True, "recent": recent}
    except:
        return {"success": True, "recent": {}}


class StatsCommand:
    """Stats command implementation."""
    
    name = "stats"
    description = "Show usage statistics"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute stats command."""
        days = args.get("days", 7)
        
        if days:
            return await get_recent_stats(days)
        else:
            return await run_stats()


__all__ = [
    "UsageStats",
    "run_stats",
    "get_recent_stats",
    "StatsCommand",
]

"""Stats Screen - Usage statistics display."""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class StatsCategory(Enum):
    """Stats categories."""
    USAGE = "usage"
    COST = "cost"
    PERFORMANCE = "performance"
    TOOLS = "tools"


@dataclass
class StatsItem:
    """Stats item."""
    label: str
    value: Any
    unit: str = ""
    trend: str = "stable"  # up, down, stable
    category: StatsCategory = StatsCategory.USAGE


@dataclass
class StatsSection:
    """Stats section."""
    title: str
    items: List[StatsItem] = field(default_factory=list)


@dataclass
class StatsScreenConfig:
    """Stats screen configuration."""
    show_history: bool = True
    show_trends: bool = True
    history_days: int = 7
    refresh_interval: int = 60


class StatsScreen:
    """Screen to display usage statistics."""
    
    def __init__(self, config: StatsScreenConfig = None):
        self.config = config or StatsScreenConfig()
        self._sections: List[StatsSection] = []
        self._data: Dict[str, Any] = {}
    
    def load_stats(self) -> None:
        """Load statistics."""
        import json
        from pathlib import Path
        
        stats_path = Path.home() / ".claude-code-py" / "stats.json"
        
        if stats_path.exists():
            try:
                self._data = json.loads(stats_path.read_text())
            except:
                self._data = {}
        
        self._build_sections()
    
    def _build_sections(self) -> None:
        """Build stats sections."""
        self._sections = []
        
        # Usage section
        usage_section = StatsSection(
            title="Usage",
            items=[
                StatsItem(
                    label="Total Sessions",
                    value=self._data.get("total_sessions", 0),
                    category=StatsCategory.USAGE,
                ),
                StatsItem(
                    label="Total Messages",
                    value=self._data.get("total_messages", 0),
                    category=StatsCategory.USAGE,
                ),
                StatsItem(
                    label="Avg Session Length",
                    value=self._data.get("avg_session_length", 0),
                    unit="messages",
                    category=StatsCategory.USAGE,
                ),
            ],
        )
        self._sections.append(usage_section)
        
        # Cost section
        cost_section = StatsSection(
            title="Cost",
            items=[
                StatsItem(
                    label="Total Cost",
                    value=self._data.get("total_cost", 0),
                    unit="USD",
                    category=StatsCategory.COST,
                ),
                StatsItem(
                    label="Avg Cost per Session",
                    value=self._data.get("avg_session_cost", 0),
                    unit="USD",
                    category=StatsCategory.COST,
                ),
            ],
        )
        self._sections.append(cost_section)
        
        # Tools section
        tools = self._data.get("most_used_tools", [])
        tools_section = StatsSection(
            title="Tools",
            items=[
                StatsItem(
                    label="Tool Calls",
                    value=self._data.get("total_tool_calls", 0),
                    category=StatsCategory.TOOLS,
                ),
                StatsItem(
                    label="Top Tool",
                    value=tools[0] if tools else "None",
                    category=StatsCategory.TOOLS,
                ),
            ],
        )
        self._sections.append(tools_section)
    
    def render(self) -> str:
        """Render stats screen."""
        lines = ["# Statistics", ""]
        
        for section in self._sections:
            lines.append(f"## {section.title}")
            lines.append("")
            
            for item in section.items:
                value_str = f"{item.value} {item.unit}" if item.unit else str(item.value)
                trend_icon = self._get_trend_icon(item.trend)
                lines.append(f"- {item.label}: {value_str} {trend_icon}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    def _get_trend_icon(self, trend: str) -> str:
        """Get trend icon."""
        icons = {
            "up": "📈",
            "down": "📉",
            "stable": "➡️",
        }
        return icons.get(trend, "")
    
    def get_sections(self) -> List[StatsSection]:
        """Get all sections."""
        return self._sections
    
    def get_item(self, label: str) -> Optional[StatsItem]:
        """Get specific stats item."""
        for section in self._sections:
            for item in section.items:
                if item.label == label:
                    return item
        return None


__all__ = [
    "StatsCategory",
    "StatsItem",
    "StatsSection",
    "StatsScreenConfig",
    "StatsScreen",
]

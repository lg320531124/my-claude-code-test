"""UI Screens - Terminal screen components."""

from __future__ import annotations

# Try to import textual-dependent screens
try:
    from .onboarding import OnboardingScreen, OnboardingStep
    from .mcp import MCPScreen, MCPServerInfo
    from .search import SearchScreen, SearchConfig
    _TEXTUAL_AVAILABLE = True
except ImportError:
    _TEXTUAL_AVAILABLE = False
    OnboardingScreen = None
    OnboardingStep = None
    MCPScreen = None
    MCPServerInfo = None
    SearchScreen = None
    SearchConfig = None

# Basic screens (no textual dependency)
from .settings import (
    SettingCategory,
    SettingItem,
    SettingsScreen,
)
from .history import (
    HistoryFilter,
    HistoryEntry,
    HistoryScreen,
)
from .stats import (
    StatsCategory,
    StatsItem,
    StatsSection,
    StatsScreen,
)
from .tasks import (
    TaskStatus,
    TaskPriority,
    TaskItem,
    TasksScreen,
)

__all__ = [
    # Textual screens (optional)
    "OnboardingScreen",
    "OnboardingStep",
    "MCPScreen",
    "MCPServerInfo",
    "SearchScreen",
    "SearchConfig",
    "_TEXTUAL_AVAILABLE",
    # Basic screens
    "SettingCategory",
    "SettingItem",
    "SettingsScreen",
    "HistoryFilter",
    "HistoryEntry",
    "HistoryScreen",
    "StatsCategory",
    "StatsItem",
    "StatsSection",
    "StatsScreen",
    "TaskStatus",
    "TaskPriority",
    "TaskItem",
    "TasksScreen",
]

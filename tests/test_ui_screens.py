"""Tests for UI screens."""

import pytest
from src.cc.ui.screens.stats import StatsScreen, StatsScreenConfig, StatsCategory
from src.cc.ui.screens.tasks import TasksScreen, TasksScreenConfig, TaskStatus
from src.cc.ui.screens.settings import SettingsScreen, SettingCategory
from src.cc.ui.screens.history import HistoryScreen, HistoryFilter


def test_stats_screen_config():
    """Test stats screen config."""
    config = StatsScreenConfig()
    assert config is not None


def test_stats_category():
    """Test stats category enum."""
    assert StatsCategory.USAGE.value == "usage"
    assert StatsCategory.TOOLS.value == "tools"


def test_tasks_screen_config():
    """Test tasks screen config."""
    config = TasksScreenConfig()
    assert config is not None


def test_task_status():
    """Test task status enum."""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.COMPLETED.value == "completed"


def test_setting_category():
    """Test setting category enum."""
    assert SettingCategory.API.value == "api"
    assert SettingCategory.UI.value == "ui"


def test_history_filter():
    """Test history filter."""
    filter = HistoryFilter()
    assert filter is not None
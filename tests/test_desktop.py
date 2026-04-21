"""Test Desktop command."""

import pytest
from click.testing import CliRunner
from src.cc.commands.desktop import desktop_group


def test_desktop_group():
    """Test Desktop command group."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["--help"])
    assert result.exit_code == 0


def test_desktop_status():
    """Test desktop status command."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["status"])
    assert result.exit_code == 0


def test_desktop_open():
    """Test desktop open command."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["open", "https://example.com"])
    assert result.exit_code == 0


def test_desktop_notifications():
    """Test notifications command."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["notifications", "--enable"])
    assert result.exit_code == 0


def test_desktop_settings():
    """Test desktop settings command."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["settings"])
    assert result.exit_code == 0


def test_desktop_logs():
    """Test logs command."""
    runner = CliRunner()
    result = runner.invoke(desktop_group, ["logs"])
    assert result.exit_code == 0
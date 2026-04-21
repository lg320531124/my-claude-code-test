"""Test Terminal command."""

import pytest
from click.testing import CliRunner
from src.cc.commands.terminal import terminal_group


def test_terminal_group():
    """Test Terminal command group."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["--help"])
    assert result.exit_code == 0


def test_terminal_info():
    """Test terminal info command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["info"])
    assert result.exit_code == 0


def test_terminal_size():
    """Test terminal size command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["size"])
    assert result.exit_code == 0


def test_terminal_clear():
    """Test terminal clear command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["clear"])
    assert result.exit_code == 0


def test_terminal_title():
    """Test terminal title command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["title", "Test Title"])
    assert result.exit_code == 0


def test_terminal_bell():
    """Test terminal bell command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["bell"])
    assert result.exit_code == 0


def test_terminal_env():
    """Test terminal env command."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["env"])
    assert result.exit_code == 0


def test_terminal_env_name():
    """Test terminal env with specific name."""
    runner = CliRunner()
    result = runner.invoke(terminal_group, ["env", "HOME"])
    assert result.exit_code == 0
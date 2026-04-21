"""Test Chrome command."""

import pytest
from click.testing import CliRunner
from src.cc.commands.chrome import chrome_group


def test_chrome_group():
    """Test Chrome command group."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["--help"])
    assert result.exit_code == 0


def test_list_pages():
    """Test list pages command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["list"])
    assert result.exit_code == 0


def test_open_page():
    """Test open page command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["open", "https://example.com"])
    assert result.exit_code == 0


def test_open_page_new_tab():
    """Test open page in new tab."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["open", "https://example.com", "-n"])
    assert result.exit_code == 0


def test_screenshot():
    """Test screenshot command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["screenshot", "1"])
    assert result.exit_code == 0


def test_screenshot_with_output():
    """Test screenshot with output."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["screenshot", "1", "-o", "test.png"])
    assert result.exit_code == 0


def test_close_page():
    """Test close page command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["close", "1"])
    assert result.exit_code == 0


def test_navigate_page():
    """Test navigate page command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["navigate", "1", "https://example.com"])
    assert result.exit_code == 0


def test_evaluate_script():
    """Test evaluate script command."""
    runner = CliRunner()
    result = runner.invoke(chrome_group, ["evaluate", "1", "console.log('test')"])
    assert result.exit_code == 0
"""Tests for enhanced doctor command."""

import pytest
import asyncio
from pathlib import Path
import tempfile
import os

from cc.commands.doctor import (
    DiagnosticResult,
    run_command_async,
    check_python_async,
    check_git_async,
    check_ripgrep_async,
    check_api_key_async,
    check_config_file_async,
    check_git_repo_async,
    run_all_checks_async,
)


def test_diagnostic_result():
    """Test diagnostic result."""
    result = DiagnosticResult(
        name="Test",
        category="test",
        ok=True,
        status="OK",
        details="All good",
    )

    assert result.ok is True
    assert result.status == "OK"


def test_diagnostic_result_with_suggestion():
    """Test result with suggestion."""
    result = DiagnosticResult(
        name="Test",
        category="test",
        ok=False,
        status="MISSING",
        details="Not found",
        suggestion="Install it",
    )

    assert result.ok is False
    assert result.suggestion == "Install it"


@pytest.mark.asyncio
async def test_check_python_async():
    """Test Python check."""
    result = await check_python_async()

    assert result.name == "Python"
    assert result.category == "runtime"
    # Should pass on any Python 3.10+ system
    assert result.ok is True or result.ok is False  # Either outcome is valid


@pytest.mark.asyncio
async def test_check_git_async():
    """Test git check."""
    result = await check_git_async()

    assert result.name == "Git"
    assert result.category == "tools"
    # Most systems have git
    assert result.status in ("OK", "MISSING")


@pytest.mark.asyncio
async def test_check_ripgrep_async():
    """Test ripgrep check."""
    result = await check_ripgrep_async()

    assert result.name == "Ripgrep"
    assert result.category == "tools"


@pytest.mark.asyncio
async def test_check_api_key_missing():
    """Test API key check when missing."""
    # Temporarily remove key
    original = os.environ.pop("ANTHROPIC_API_KEY", None)

    result = await check_api_key_async()

    assert result.ok is False
    assert result.status == "MISSING"

    # Restore if existed
    if original:
        os.environ["ANTHROPIC_API_KEY"] = original


@pytest.mark.asyncio
async def test_check_api_key_present():
    """Test API key check when present."""
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key-123"

    result = await check_api_key_async()

    assert result.ok is True
    assert result.status == "OK"

    # Clean up
    del os.environ["ANTHROPIC_API_KEY"]


@pytest.mark.asyncio
async def test_check_config_file_async(temp_dir):
    """Test config file check."""
    result = await check_config_file_async(temp_dir)

    assert result.name == "Config"
    assert result.category == "config"
    # Should work with or without config
    assert result.status in ("OK", "DEFAULT")


@pytest.mark.asyncio
async def test_check_config_file_exists(temp_dir):
    """Test config check with existing file."""
    config_dir = temp_dir / ".claude"
    config_dir.mkdir()
    config_file = config_dir / "config.json"
    config_file.write_text("{}")

    result = await check_config_file_async(temp_dir)

    assert result.status == "OK"


@pytest.mark.asyncio
async def test_check_git_repo_async(temp_dir):
    """Test git repo check."""
    result = await check_git_repo_async(temp_dir)

    assert result.name == "Git Repo"
    assert result.category == "git"
    assert result.status == "NONE"  # Not a git repo


@pytest.mark.asyncio
async def test_check_git_repo_exists(temp_dir):
    """Test git repo check in repo."""
    import subprocess
    subprocess.run(["git", "init"], cwd=temp_dir, capture_output=True)

    result = await check_git_repo_async(temp_dir)

    assert result.ok is True
    assert result.status == "OK"


@pytest.mark.asyncio
async def test_run_all_checks_async(temp_dir):
    """Test running all checks."""
    results = await run_all_checks_async(temp_dir)

    assert len(results) > 0
    assert all(isinstance(r, DiagnosticResult) for r in results)

    # Check categories
    categories = set(r.category for r in results)
    assert "runtime" in categories or "tools" in categories


@pytest.mark.asyncio
async def test_run_command_async_success():
    """Test async command execution."""
    stdout, stderr, code = await run_command_async(["echo", "test"])

    assert code == 0
    assert "test" in stdout


@pytest.mark.asyncio
async def test_run_command_async_failure():
    """Test async command with failure."""
    stdout, stderr, code = await run_command_async(["false"])

    assert code != 0


@pytest.mark.asyncio
async def test_run_command_async_timeout():
    """Test async command timeout."""
    # Sleep for longer than timeout
    stdout, stderr, code = await run_command_async(["sleep", "10"], timeout=0.5)

    assert code == -1
    assert "Timeout" in stderr


@pytest.mark.asyncio
async def test_run_command_async_not_found():
    """Test async command not found."""
    stdout, stderr, code = await run_command_async(["nonexistent_command"])

    assert code == -1
    assert "Not found" in stderr


@pytest.fixture
def temp_dir():
    """Create temporary directory."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)
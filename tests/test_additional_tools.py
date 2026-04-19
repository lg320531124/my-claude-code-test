"""Tests for additional tools."""

from __future__ import annotations
import pytest
import tempfile
from pathlib import Path

from cc.tools.environment import EnvironmentTool, EnvironmentInput
from cc.tools.checksum import ChecksumTool, ChecksumInput
from cc.tools.timer import TimerTool, TimerInput
from cc.tools.json_tool import JSONTool, JSONInput
from cc.tools.regex import RegexTool, RegexInput
from cc.tools.url import URLTool, URLInput
from cc.types.tool import ToolUseContext


@pytest.fixture
def ctx():
    """Create ToolUseContext."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield ToolUseContext(cwd=tmpdir, session_id="test")


# Environment Tool Tests
@pytest.fixture
def env_tool():
    return EnvironmentTool()


@pytest.mark.asyncio
async def test_env_list(env_tool, ctx):
    """Test environment list."""
    input = EnvironmentInput(action="list")
    result = await env_tool.execute(input, ctx)
    assert not result.is_error


@pytest.mark.asyncio
async def test_env_get(env_tool, ctx):
    """Test environment get."""
    import os
    os.environ["TEST_VAR"] = "test_value"
    input = EnvironmentInput(action="get", key="TEST_VAR")
    result = await env_tool.execute(input, ctx)
    assert not result.is_error
    assert "test_value" in result.content


# Checksum Tool Tests
@pytest.fixture
def checksum_tool():
    return ChecksumTool()


@pytest.fixture
def test_file(ctx):
    path = Path(ctx.cwd) / "test.txt"
    path.write_text("test content")
    return path


@pytest.mark.asyncio
async def test_checksum_sha256(checksum_tool, ctx, test_file):
    """Test SHA256 checksum."""
    input = ChecksumInput(file_path=str(test_file), algorithm="sha256")
    result = await checksum_tool.execute(input, ctx)
    assert not result.is_error
    assert "sha256:" in result.content.lower()


@pytest.mark.asyncio
async def test_checksum_md5(checksum_tool, ctx, test_file):
    """Test MD5 checksum."""
    input = ChecksumInput(file_path=str(test_file), algorithm="md5")
    result = await checksum_tool.execute(input, ctx)
    assert not result.is_error


# Timer Tool Tests
@pytest.fixture
def timer_tool():
    return TimerTool()


@pytest.mark.asyncio
async def test_timer_start_stop(timer_tool, ctx):
    """Test timer start and stop."""
    start_input = TimerInput(action="start", name="test_timer")
    start_result = await timer_tool.execute(start_input, ctx)
    assert not start_result.is_error

    stop_input = TimerInput(action="stop", name="test_timer")
    stop_result = await timer_tool.execute(stop_input, ctx)
    assert not stop_result.is_error


# JSON Tool Tests
@pytest.fixture
def json_tool():
    return JSONTool()


@pytest.mark.asyncio
async def test_json_parse(json_tool, ctx):
    """Test JSON parse."""
    input = JSONInput(action="parse", data='{"key": "value"}')
    result = await json_tool.execute(input, ctx)
    assert not result.is_error


@pytest.mark.asyncio
async def test_json_format(json_tool, ctx):
    """Test JSON format."""
    input = JSONInput(action="format", data='{"key":"value"}')
    result = await json_tool.execute(input, ctx)
    assert not result.is_error


@pytest.mark.asyncio
async def test_json_validate(json_tool, ctx):
    """Test JSON validate."""
    input = JSONInput(action="validate", data='{"key": "value"}')
    result = await json_tool.execute(input, ctx)
    assert not result.is_error
    assert "valid" in result.content.lower()


@pytest.mark.asyncio
async def test_json_invalid(json_tool, ctx):
    """Test invalid JSON."""
    input = JSONInput(action="validate", data='{invalid json}')
    result = await json_tool.execute(input, ctx)
    assert result.is_error


# Regex Tool Tests
@pytest.fixture
def regex_tool():
    return RegexTool()


@pytest.mark.asyncio
async def test_regex_search(regex_tool, ctx):
    """Test regex search."""
    input = RegexInput(action="search", pattern="test", text="this is a test string")
    result = await regex_tool.execute(input, ctx)
    assert not result.is_error
    assert "test" in result.content


@pytest.mark.asyncio
async def test_regex_findall(regex_tool, ctx):
    """Test regex findall."""
    input = RegexInput(
        action="findall",
        pattern="\\d+",
        text="123 456 789"
    )
    result = await regex_tool.execute(input, ctx)
    assert not result.is_error


@pytest.mark.asyncio
async def test_regex_replace(regex_tool, ctx):
    """Test regex replace."""
    input = RegexInput(
        action="replace",
        pattern="test",
        text="test value",
        replacement="new",
        flags=["g"]
    )
    result = await regex_tool.execute(input, ctx)
    assert "new" in result.content


# URL Tool Tests
@pytest.fixture
def url_tool():
    return URLTool()


@pytest.mark.asyncio
async def test_url_parse(url_tool, ctx):
    """Test URL parse."""
    input = URLInput(action="parse", url="https://example.com/path?query=value")
    result = await url_tool.execute(input, ctx)
    assert not result.is_error
    assert "example.com" in result.content


@pytest.mark.asyncio
async def test_url_validate(url_tool, ctx):
    """Test URL validate."""
    input = URLInput(action="validate", url="https://example.com")
    result = await url_tool.execute(input, ctx)
    assert not result.is_error
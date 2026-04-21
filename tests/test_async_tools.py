"""Test async tools."""

from __future__ import annotations
import asyncio
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from cc.utils.async_io import read_file_async, write_file_async, exists_async
from cc.utils.async_process import run_command_async
from cc.utils.async_http import AsyncHTTPClient


class TestAsyncIO:
    """Test async file operations."""

    @pytest.mark.asyncio
    async def test_write_and_read(self, tmp_path):
        """Test write and read."""
        test_file = tmp_path / "test.txt"
        content = "Hello, asyncio!"

        await write_file_async(str(test_file), content)
        result = await read_file_async(str(test_file))

        assert result == content

    @pytest.mark.asyncio
    async def test_exists(self, tmp_path):
        """Test file existence check."""
        test_file = tmp_path / "exists.txt"

        assert await exists_async(str(test_file)) is False

        await write_file_async(str(test_file), "test")
        assert await exists_async(str(test_file)) is True


class TestAsyncProcess:
    """Test async process execution."""

    @pytest.mark.asyncio
    async def test_simple_command(self):
        """Test simple command."""
        result = await run_command_async("echo hello")

        assert result.returncode == 0
        assert "hello" in result.stdout

    @pytest.mark.asyncio
    async def test_command_with_error(self):
        """Test command with error."""
        result = await run_command_async("ls /nonexistent")

        assert result.returncode != 0
        assert len(result.stderr) > 0

    @pytest.mark.asyncio
    async def test_parallel_commands(self):
        """Test parallel execution."""
        commands = ["echo one", "echo two", "echo three"]
        results = await asyncio.gather(
            *[run_command_async(cmd) for cmd in commands]
        )

        assert all(r.returncode == 0 for r in results)
        assert "one" in results[0].stdout
        assert "two" in results[1].stdout
        assert "three" in results[2].stdout


class TestBashSandbox:
    """Test bash sandbox."""

    @pytest.mark.asyncio
    async def test_safe_command(self):
        """Test safe command detection."""
        from cc.utils.bash.sandbox import get_sandbox

        sandbox = get_sandbox()
        result = sandbox.check_command("ls -la")

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_dangerous_command(self):
        """Test dangerous command detection."""
        from cc.utils.bash.sandbox import get_sandbox

        sandbox = get_sandbox()
        result = sandbox.check_command("rm -rf /")

        assert result.allowed is False
        assert result.risk_level == "critical"


class TestHooks:
    """Test hooks system."""

    def test_permission_checker(self):
        """Test permission checker."""
        from cc.tools.shared.permissions import get_permission_checker

        checker = get_permission_checker()
        checker.add_allow_rule("Read(*)")

        assert "Read(*)" in checker.get_rules()["allow"]

    def test_tool_validator(self):
        """Test tool validator."""
        from cc.tools.shared.validation import get_validator

        validator = get_validator()
        assert validator.validate_path("/tmp/test") == (True, "", "/tmp/test")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

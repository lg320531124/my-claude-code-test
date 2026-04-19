"""Tests for MCP Health Check and Auto-restart."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import tempfile
import json

from cc.mcp.health import (
    ServerHealthStatus,
    HealthCheckResult,
    ServerHealthConfig,
    MCPHealthMonitor,
    MCPAutoRecovery,
    MCPServerRegistry,
    get_health_monitor,
    start_health_monitoring,
    stop_health_monitoring,
)


class TestServerHealthStatus:
    """Test ServerHealthStatus enum."""

    def test_all_statuses(self):
        """Test all health statuses exist."""
        statuses = [
            ServerHealthStatus.HEALTHY,
            ServerHealthStatus.UNHEALTHY,
            ServerHealthStatus.RECONNECTING,
            ServerHealthStatus.STOPPED,
        ]
        for status in statuses:
            assert isinstance(status.value, str)


class TestHealthCheckResult:
    """Test HealthCheckResult dataclass."""

    def test_create_result(self):
        """Test creating health check result."""
        result = HealthCheckResult(
            server_name="test_server",
            status=ServerHealthStatus.HEALTHY,
            last_check=100.0,
        )
        assert result.server_name == "test_server"
        assert result.status == ServerHealthStatus.HEALTHY
        assert result.last_check == 100.0
        assert result.consecutive_failures == 0

    def test_result_with_failures(self):
        """Test result with failures."""
        result = HealthCheckResult(
            server_name="bad_server",
            status=ServerHealthStatus.UNHEALTHY,
            last_check=100.0,
            consecutive_failures=3,
            last_error="Connection lost",
            reconnect_attempts=2,
        )
        assert result.status == ServerHealthStatus.UNHEALTHY
        assert result.consecutive_failures == 3
        assert result.last_error == "Connection lost"


class TestServerHealthConfig:
    """Test ServerHealthConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = ServerHealthConfig()
        assert config.check_interval_seconds == 30.0
        assert config.max_failures == 3
        assert config.reconnect_delay_seconds == 5.0
        assert config.max_reconnect_attempts == 5
        assert config.auto_restart is True

    def test_custom_config(self):
        """Test custom configuration."""
        config = ServerHealthConfig(
            check_interval_seconds=60.0,
            max_failures=5,
            auto_restart=False,
        )
        assert config.check_interval_seconds == 60.0
        assert config.max_failures == 5
        assert config.auto_restart is False


class TestMCPHealthMonitor:
    """Test MCPHealthMonitor class."""

    def test_init(self):
        """Test monitor initialization."""
        monitor = MCPHealthMonitor()
        assert monitor.health_status == {}
        assert monitor._running is False

    def test_init_with_config(self):
        """Test monitor with custom config."""
        config = ServerHealthConfig(check_interval_seconds=15.0)
        monitor = MCPHealthMonitor(config)
        assert monitor.config.check_interval_seconds == 15.0

    @pytest.mark.asyncio
    async def test_start_stop(self):
        """Test start and stop monitoring."""
        monitor = MCPHealthMonitor()
        await monitor.start()
        assert monitor._running is True
        assert monitor._monitor_task is not None

        await monitor.stop()
        assert monitor._running is False
        assert monitor._monitor_task is None

    def test_register_connection_time(self):
        """Test registering connection time."""
        monitor = MCPHealthMonitor()
        monitor.register_connection_time("test_server")
        assert "test_server" in monitor._connection_times

    def test_get_health_summary(self):
        """Test getting health summary."""
        monitor = MCPHealthMonitor()
        monitor.health_status["server1"] = HealthCheckResult(
            server_name="server1",
            status=ServerHealthStatus.HEALTHY,
            last_check=100.0,
            uptime_seconds=3600.0,
        )
        monitor.health_status["server2"] = HealthCheckResult(
            server_name="server2",
            status=ServerHealthStatus.UNHEALTHY,
            last_check=100.0,
            consecutive_failures=2,
        )

        summary = monitor.get_health_summary()
        assert "server1" in summary
        assert summary["server1"]["status"] == "healthy"
        assert "server2" in summary
        assert summary["server2"]["status"] == "unhealthy"

    def test_get_healthy_servers(self):
        """Test getting healthy servers."""
        monitor = MCPHealthMonitor()
        monitor.health_status["healthy1"] = HealthCheckResult(
            server_name="healthy1",
            status=ServerHealthStatus.HEALTHY,
            last_check=100.0,
        )
        monitor.health_status["unhealthy1"] = HealthCheckResult(
            server_name="unhealthy1",
            status=ServerHealthStatus.UNHEALTHY,
            last_check=100.0,
        )

        healthy = monitor.get_healthy_servers()
        assert healthy == ["healthy1"]

    def test_get_unhealthy_servers(self):
        """Test getting unhealthy servers."""
        monitor = MCPHealthMonitor()
        monitor.health_status["healthy1"] = HealthCheckResult(
            server_name="healthy1",
            status=ServerHealthStatus.HEALTHY,
            last_check=100.0,
        )
        monitor.health_status["reconnecting1"] = HealthCheckResult(
            server_name="reconnecting1",
            status=ServerHealthStatus.RECONNECTING,
            last_check=100.0,
        )

        unhealthy = monitor.get_unhealthy_servers()
        assert "reconnecting1" in unhealthy

    def test_set_callbacks(self):
        """Test setting callbacks."""
        monitor = MCPHealthMonitor()
        monitor.set_callbacks(
            on_health_change=lambda n, r: None,
            on_reconnect=lambda n, s: None,
            on_failure=lambda n, r: None,
        )
        assert monitor._on_health_change is not None
        assert monitor._on_reconnect is not None
        assert monitor._on_failure is not None

    @pytest.mark.asyncio
    async def test_check_server_health_connected(self):
        """Test checking health of connected server."""
        monitor = MCPHealthMonitor()

        # Mock connection
        conn = MagicMock()
        conn.connected = True
        conn._send_request = AsyncMock(return_value={"result": {}})

        result = await monitor._check_server_health("test", conn)
        assert result.status == ServerHealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_check_server_health_disconnected(self):
        """Test checking health of disconnected server."""
        monitor = MCPHealthMonitor()

        conn = MagicMock()
        conn.connected = False

        result = await monitor._check_server_health("test", conn)
        assert result.status == ServerHealthStatus.UNHEALTHY


class TestMCPAutoRecovery:
    """Test MCPAutoRecovery class."""

    def test_init(self):
        """Test recovery initialization."""
        monitor = MCPHealthMonitor()
        recovery = MCPAutoRecovery(monitor)
        assert recovery.health_monitor == monitor
        assert recovery._recovery_history == []

    def test_record_event(self):
        """Test recording events."""
        monitor = MCPHealthMonitor()
        recovery = MCPAutoRecovery(monitor)

        recovery._record_event("test_type", "test_server", {"key": "value"})
        assert len(recovery._recovery_history) == 1
        event = recovery._recovery_history[0]
        assert event["type"] == "test_type"
        assert event["server"] == "test_server"

    def test_max_history(self):
        """Test history size limit."""
        monitor = MCPHealthMonitor()
        recovery = MCPAutoRecovery(monitor)
        recovery._max_history = 10

        # Add more than limit
        for i in range(20):
            recovery._record_event("type", f"server_{i}", {})

        assert len(recovery._recovery_history) == 10

    def test_get_recovery_history(self):
        """Test getting history."""
        monitor = MCPHealthMonitor()
        recovery = MCPAutoRecovery(monitor)

        recovery._record_event("type1", "server1", {})
        recovery._record_event("type2", "server2", {})
        recovery._record_event("type3", "server1", {})

        history = recovery.get_recovery_history("server1")
        assert len(history) == 2

        all_history = recovery.get_recovery_history()
        assert len(all_history) == 3

    def test_get_stats(self):
        """Test getting stats."""
        monitor = MCPHealthMonitor()
        recovery = MCPAutoRecovery(monitor)

        recovery._record_event("reconnect", "s1", {"success": True})
        recovery._record_event("reconnect", "s2", {"success": False})
        recovery._record_event("failure", "s3", {})

        stats = recovery.get_stats()
        assert stats["total_events"] == 3
        assert stats["reconnect_attempts"] == 2
        assert stats["successful_reconnects"] == 1
        assert stats["permanent_failures"] == 1


class TestMCPServerRegistry:
    """Test MCPServerRegistry class."""

    def test_init(self):
        """Test registry initialization."""
        registry = MCPServerRegistry()
        assert registry.server_configs == {}

    def test_with_config_file(self):
        """Test registry with config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {
                    "server1": {"command": "node", "args": ["server.js"]},
                }
            }))

            registry = MCPServerRegistry(config_path)
            assert "server1" in registry.server_configs

    def test_get_server_config(self):
        """Test getting server config."""
        registry = MCPServerRegistry()
        registry.server_configs["test"] = {"command": "test_cmd"}

        config = registry.get_server_config("test")
        assert config == {"command": "test_cmd"}

        assert registry.get_server_config("nonexistent") is None

    def test_list_servers(self):
        """Test listing servers."""
        registry = MCPServerRegistry()
        registry.server_configs["s1"] = {}
        registry.server_configs["s2"] = {}

        servers = registry.list_servers()
        assert servers == ["s1", "s2"]

    def test_add_server(self):
        """Test adding server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            registry = MCPServerRegistry(config_path)

            registry.add_server("new_server", {"command": "new_cmd"})
            assert "new_server" in registry.server_configs

            # Check file was saved
            saved_config = json.loads(config_path.read_text())
            assert "new_server" in saved_config["mcpServers"]

    def test_remove_server(self):
        """Test removing server."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "mcp.json"
            config_path.write_text(json.dumps({
                "mcpServers": {"server1": {"command": "cmd"}}
            }))

            registry = MCPServerRegistry(config_path)
            result = registry.remove_server("server1")
            assert result is True
            assert "server1" not in registry.server_configs

    def test_update_server(self):
        """Test updating server."""
        registry = MCPServerRegistry()
        registry.server_configs["test"] = {"command": "old"}

        registry.update_server("test", {"command": "new"})
        assert registry.server_configs["test"]["command"] == "new"


class TestGlobals:
    """Test global functions."""

    def test_get_health_monitor(self):
        """Test getting global monitor."""
        monitor1 = get_health_monitor()
        monitor2 = get_health_monitor()
        assert monitor1 is monitor2

    @pytest.mark.asyncio
    async def test_start_stop_monitoring(self):
        """Test global start/stop functions."""
        await start_health_monitoring()
        monitor = get_health_monitor()
        assert monitor._running is True

        await stop_health_monitoring()
        assert monitor._running is False
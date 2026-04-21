"""MCP Health Check and Auto-restart - Monitor connections and recover."""

from __future__ import annotations
import asyncio
import time
from pathlib import Path
from typing import Dict, List, Callable, Optional
from dataclasses import dataclass
from enum import Enum

from .client import MCPConnection, get_mcp_manager


class ServerHealthStatus(Enum):
    """Server health status."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    RECONNECTING = "reconnecting"
    STOPPED = "stopped"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    server_name: str
    status: ServerHealthStatus
    last_check: float
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    uptime_seconds: float = 0.0
    reconnect_attempts: int = 0


@dataclass
class ServerHealthConfig:
    """Configuration for health monitoring."""
    check_interval_seconds: float = 30.0
    max_failures: int = 3
    reconnect_delay_seconds: float = 5.0
    max_reconnect_attempts: int = 5
    auto_restart: bool = True
    graceful_shutdown_timeout: float = 10.0


class MCPHealthMonitor:
    """Monitor MCP server health and auto-restart."""

    def __init__(self, config: Optional[ServerHealthConfig] = None):
        self.config = config or ServerHealthConfig()
        self.health_status: Dict[str, HealthCheckResult] = {}
        self._monitor_task: asyncio.Task | None = None
        self._running = False
        self._on_health_change: Optional[Callable] = None
        self._on_reconnect: Optional[Callable] = None
        self._on_failure: Optional[Callable] = None

        # Track connection times
        self._connection_times: Dict[str, float] = {}

    async def start(self) -> None:
        """Start health monitoring."""
        if self._running:
            return

        self._running = True
        self._monitor_task = asyncio.create_task(self._monitor_loop())

    async def stop(self) -> None:
        """Stop health monitoring."""
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None

    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_all_servers()
                await asyncio.sleep(self.config.check_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception:
                # Log error but continue monitoring
                await asyncio.sleep(self.config.check_interval_seconds)

    async def _check_all_servers(self) -> None:
        """Check health of all servers."""
        manager = get_mcp_manager()

        for name, conn in manager.connections.items():
            result = await self._check_server_health(name, conn)
            self.health_status[name] = result

            # Handle unhealthy servers
            if result.status == ServerHealthStatus.UNHEALTHY:
                await self._handle_unhealthy(name, conn, result)

            # Notify of status changes
            if self._on_health_change:
                self._on_health_change(name, result)

    async def _check_server_health(
        self,
        name: str,
        conn: MCPConnection,
    ) -> HealthCheckResult:
        """Check health of a single server."""
        now = time.time()
        prev_result = self.health_status.get(name)

        if not conn.connected:
            # Server is disconnected
            failures = (prev_result.consecutive_failures + 1) if prev_result else 1
            return HealthCheckResult(
                server_name=name,
                status=ServerHealthStatus.UNHEALTHY,
                last_check=now,
                consecutive_failures=failures,
                last_error="Connection lost",
                reconnect_attempts=(prev_result.reconnect_attempts if prev_result else 0),
            )

        # Try to ping server
        try:
            # Send a minimal request to check if server responds
            response = await conn._send_request("ping", {})

            if response and "result" in response:
                # Server is healthy
                uptime = now - self._connection_times.get(name, now)
                return HealthCheckResult(
                    server_name=name,
                    status=ServerHealthStatus.HEALTHY,
                    last_check=now,
                    consecutive_failures=0,
                    uptime_seconds=uptime,
                )
            else:
                failures = (prev_result.consecutive_failures + 1) if prev_result else 1
                return HealthCheckResult(
                    server_name=name,
                    status=ServerHealthStatus.UNHEALTHY,
                    last_check=now,
                    consecutive_failures=failures,
                    last_error="Ping failed",
                )

        except Exception as e:
            failures = (prev_result.consecutive_failures + 1) if prev_result else 1
            return HealthCheckResult(
                server_name=name,
                status=ServerHealthStatus.UNHEALTHY,
                last_check=now,
                consecutive_failures=failures,
                last_error=str(e),
            )

    async def _handle_unhealthy(
        self,
        name: str,
        conn: MCPConnection,
        result: HealthCheckResult,
    ) -> None:
        """Handle unhealthy server."""
        # Check if we should attempt reconnect
        if result.consecutive_failures < self.config.max_failures:
            return

        if result.reconnect_attempts >= self.config.max_reconnect_attempts:
            # Max attempts reached, mark as stopped
            result.status = ServerHealthStatus.STOPPED
            result.last_error = "Max reconnect attempts reached"
            if self._on_failure:
                self._on_failure(name, result)
            return

        if not self.config.auto_restart:
            return

        # Attempt reconnect
        result.status = ServerHealthStatus.RECONNECTING
        result.reconnect_attempts += 1

        # Wait before reconnect
        await asyncio.sleep(self.config.reconnect_delay_seconds)

        # Try to reconnect
        try:
            await conn.disconnect()
            success = await conn.connect()

            if success:
                # Reset status
                result.status = ServerHealthStatus.HEALTHY
                result.consecutive_failures = 0
                result.reconnect_attempts = 0
                result.last_error = None
                self._connection_times[name] = time.time()

                if self._on_reconnect:
                    self._on_reconnect(name, success)
            else:
                result.last_error = "Reconnect failed"

        except Exception as e:
            result.last_error = f"Reconnect error: {e}"

    def register_connection_time(self, name: str) -> None:
        """Record when a connection was established."""
        self._connection_times[name] = time.time()

    def get_health_summary(self) -> dict:
        """Get health summary for all servers."""
        return {
            name: {
                "status": result.status.value,
                "uptime": result.uptime_seconds,
                "failures": result.consecutive_failures,
                "reconnects": result.reconnect_attempts,
                "last_error": result.last_error,
            }
            for name, result in self.health_status.items()
        }

    def set_callbacks(
        self,
        on_health_change: Optional[Callable] = None,
        on_reconnect: Optional[Callable] = None,
        on_failure: Optional[Callable] = None,
    ) -> None:
        """Set event callbacks."""
        self._on_health_change = on_health_change
        self._on_reconnect = on_reconnect
        self._on_failure = on_failure

    def get_healthy_servers(self) -> List[str]:
        """Get list of healthy servers."""
        return [
            name for name, result in self.health_status.items()
            if result.status == ServerHealthStatus.HEALTHY
        ]

    def get_unhealthy_servers(self) -> List[str]:
        """Get list of unhealthy servers."""
        return [
            name for name, result in self.health_status.items()
            if result.status in (
                ServerHealthStatus.UNHEALTHY,
                ServerHealthStatus.RECONNECTING,
            )
        ]


class MCPAutoRecovery:
    """Automatic recovery for MCP connections."""

    def __init__(self, health_monitor: MCPHealthMonitor):
        self.health_monitor = health_monitor
        self._recovery_history: List[dict] = []
        self._max_history: int = 100

        # Set up health monitor callbacks
        self.health_monitor.set_callbacks(
            on_health_change=self._on_health_change,
            on_reconnect=self._on_reconnect,
            on_failure=self._on_failure,
        )

    def _on_health_change(self, name: str, result: HealthCheckResult) -> None:
        """Handle health status change."""
        self._record_event("health_change", name, {
            "status": result.status.value,
            "failures": result.consecutive_failures,
        })

    def _on_reconnect(self, name: str, success: bool) -> None:
        """Handle reconnect event."""
        self._record_event("reconnect", name, {"success": success})

    def _on_failure(self, name: str, result: HealthCheckResult) -> None:
        """Handle failure event."""
        self._record_event("failure", name, {
            "error": result.last_error,
            "attempts": result.reconnect_attempts,
        })

    def _record_event(self, event_type: str, server_name: str, data: dict) -> None:
        """Record recovery event."""
        event = {
            "timestamp": time.time(),
            "type": event_type,
            "server": server_name,
            "data": data,
        }
        self._recovery_history.append(event)

        # Trim history
        if len(self._recovery_history) > self._max_history:
            self._recovery_history = self._recovery_history[-self._max_history:]

    def get_recovery_history(self, server_name: Optional[str] = None) -> List[dict]:
        """Get recovery history."""
        if server_name:
            return [
                e for e in self._recovery_history
                if e["server"] == server_name
            ]
        return self._recovery_history

    def get_stats(self) -> dict:
        """Get recovery statistics."""
        reconnects = [e for e in self._recovery_history if e["type"] == "reconnect"]
        failures = [e for e in self._recovery_history if e["type"] == "failure"]

        return {
            "total_events": len(self._recovery_history),
            "reconnect_attempts": len(reconnects),
            "successful_reconnects": sum(
                1 for e in reconnects if e["data"].get("success", False)
            ),
            "permanent_failures": len(failures),
        }


class MCPServerRegistry:
    """Registry for tracking server configurations."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path.cwd() / ".claude" / "mcp.json"
        self.server_configs: Dict[str, dict] = {}
        self._load_config()

    def _load_config(self) -> None:
        """Load server configurations."""
        import json

        if not self.config_path.exists():
            return

        try:
            with open(self.config_path) as f:
                config = json.load(f)
            self.server_configs = config.get("mcpServers", {})
        except Exception:
            self.server_configs = {}

    def get_server_config(self, name: str) -> dict | None:
        """Get configuration for a server."""
        return self.server_configs.get(name)

    def list_servers(self) -> List[str]:
        """List all configured servers."""
        return list(self.server_configs.keys())

    def add_server(self, name: str, config: dict) -> None:
        """Add a server configuration."""
        self.server_configs[name] = config
        self._save_config()

    def remove_server(self, name: str) -> bool:
        """Remove a server configuration."""
        if name in self.server_configs:
            del self.server_configs[name]
            self._save_config()
            return True
        return False

    def update_server(self, name: str, config: dict) -> None:
        """Update server configuration."""
        self.server_configs[name] = config
        self._save_config()

    def _save_config(self) -> None:
        """Save configuration to file."""
        import json

        config = {"mcpServers": self.server_configs}

        # Ensure directory exists
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w") as f:
            json.dump(config, f, indent=2)


# Global health monitor
_health_monitor: Optional[MCPHealthMonitor] = None


def get_health_monitor() -> MCPHealthMonitor:
    """Get global health monitor."""
    global _health_monitor
    if _health_monitor is None:
        _health_monitor = MCPHealthMonitor()
    return _health_monitor


async def start_health_monitoring() -> None:
    """Start health monitoring."""
    monitor = get_health_monitor()
    await monitor.start()


async def stop_health_monitoring() -> None:
    """Stop health monitoring."""
    monitor = get_health_monitor()
    await monitor.stop()


__all__ = [
    "ServerHealthStatus",
    "HealthCheckResult",
    "ServerHealthConfig",
    "MCPHealthMonitor",
    "MCPAutoRecovery",
    "MCPServerRegistry",
    "get_health_monitor",
    "start_health_monitoring",
    "stop_health_monitoring",
]

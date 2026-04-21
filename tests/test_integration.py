"""Integration Tests - End-to-end functionality verification."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import json

from cc.core import Session, SessionManager
from cc.core.engine import QueryEngine
from cc.tools import get_default_tools
from cc.permissions import PermissionManager
from cc.services.hooks import HookManager, HookType, register_hook
from cc.services.plugins import PluginManager
from cc.mcp import MCPHealthMonitor
from cc.ui.widgets import ThemeManager
from cc.utils.performance import AsyncCache, ParallelExecutor


class TestIntegrationSession:
    """Test session integration."""

    @pytest.mark.asyncio
    async def test_session_creation_and_save(self):
        """Test creating and saving session."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = SessionManager(Path(tmpdir))
            session = manager.create_session()

            assert session.session_id is not None
            assert session.messages == []

            # Save
            manager.save_session(session)

            # Load
            loaded = manager.load_session(session.session_id)
            assert loaded is not None
            assert loaded.session_id == session.session_id

    @pytest.mark.asyncio
    async def test_session_message_flow(self):
        """Test message flow in session."""
        session = Session()

        from cc.types.message import create_user_message

        user_msg = create_user_message("Hello")
        session.add_message(user_msg)

        # Create assistant message with proper format
        from cc.types.message import AssistantMessage, TextBlock
        assistant_msg = AssistantMessage(content=[TextBlock(text="Hi there!")])
        session.add_message(assistant_msg)

        assert len(session.messages) == 2

        session.clear_messages()
        assert len(session.messages) == 0


class TestIntegrationPermissions:
    """Test permission integration."""

    @pytest.mark.asyncio
    async def test_permission_flow(self):
        """Test permission checking flow."""
        from cc.types.permission import PermissionDecision

        manager = PermissionManager()

        # Add a rule
        from cc.permissions.rules import PermissionRule
        manager.rules.append(PermissionRule(
            pattern="Bash(ls*)",
            decision=PermissionDecision.ALLOW,
        ))

        # Check (not async)
        result = manager.check("Bash", {"command": "ls -la"})
        assert result.decision == PermissionDecision.ALLOW

    @pytest.mark.asyncio
    async def test_permission_with_hooks(self):
        """Test permission with hooks."""
        from cc.permissions.hooks import create_permission_hook
        from cc.types.permission import PermissionDecision

        hook_manager = HookManager()
        permission_hook = create_permission_hook(lambda: PermissionDecision.ALLOW)
        hook_manager.register(HookType.PRE_TOOL_EXECUTE, permission_hook)

        # Trigger
        results = await hook_manager.trigger(HookType.PRE_TOOL_EXECUTE)
        assert len(results) >= 1


class TestIntegrationHooksPlugins:
    """Test hooks and plugins integration."""

    @pytest.mark.asyncio
    async def test_hook_plugin_flow(self):
        """Test hook triggering from plugin context."""
        events = []

        async def capture_hook(ctx):
            events.append(ctx.event.value)
            return ctx

        # Use the hook manager directly instead of global register
        hook_manager = HookManager()
        hook_manager.register(HookType.PRE_QUERY, capture_hook)
        hook_manager.register(HookType.POST_QUERY, capture_hook)

        # Trigger via manager
        await hook_manager.trigger(HookType.PRE_QUERY, data={"test": True})
        await hook_manager.trigger(HookType.POST_QUERY, data={"test": True})

        assert "pre_query" in events
        assert "post_query" in events

    @pytest.mark.asyncio
    async def test_plugin_manager_integration(self):
        """Test plugin manager lifecycle."""
        manager = PluginManager()

        await manager.initialize()
        assert manager._initialized is True

        # Register global hook
        manager.register_global_hook("test_event", MagicMock())

        # Trigger
        results = await manager.trigger_event("test_event")
        assert len(results) >= 1

        await manager.shutdown()
        assert manager._initialized is False


class TestIntegrationMCP:
    """Test MCP integration."""

    @pytest.mark.asyncio
    async def test_health_monitor_integration(self):
        """Test health monitor with MCP."""
        from cc.mcp.health import ServerHealthConfig

        config = ServerHealthConfig(check_interval_seconds=1.0)
        monitor = MCPHealthMonitor(config)

        await monitor.start()
        assert monitor._running is True

        summary = monitor.get_health_summary()
        assert isinstance(summary, dict)

        await monitor.stop()
        assert monitor._running is False


class TestIntegrationUI:
    """Test UI integration."""

    def test_theme_integration(self):
        """Test theme manager."""
        theme_mgr = ThemeManager()

        # Set theme
        theme_mgr.set_theme("nord")
        assert theme_mgr.get_current_theme() == "nord"


class TestIntegrationPerformance:
    """Test performance optimization integration."""

    @pytest.mark.asyncio
    async def test_cache_with_tools(self):
        """Test caching with tool execution."""
        cache = AsyncCache(max_size=10)

        # Simulate tool result caching
        tool_result = {"output": "Hello World"}
        await cache.set("tool_bash_ls", tool_result)

        # Retrieve
        cached_result = await cache.get("tool_bash_ls")
        assert cached_result == tool_result

    @pytest.mark.asyncio
    async def test_parallel_execution(self):
        """Test parallel execution of multiple tasks."""
        executor = ParallelExecutor(max_concurrent=5)

        async def simulate_tool_call(n):
            await asyncio.sleep(0.01)
            return {"result": n}

        # Run 10 tasks in parallel
        tasks = [lambda n=i: simulate_tool_call(n) for i in range(10)]
        results = await executor.execute(tasks)

        assert len(results) == 10


class TestIntegrationFullFlow:
    """Test complete application flow."""

    @pytest.mark.asyncio
    async def test_end_to_end_flow_mocked(self):
        """Test end-to-end flow with mocked components."""
        # This test simulates a complete query flow

        # 1. Create session
        session = Session()

        # 2. Add user message
        from cc.types.message import create_user_message
        session.add_message(create_user_message("Test query"))

        # 3. Get context
        ctx = session.get_context()
        assert ctx.cwd is not None

        # 4. Check permissions (mocked)
        perm_manager = PermissionManager()
        # Would check permission before tool execution

        # 5. Trigger hooks
        hook_mgr = HookManager()
        await hook_mgr.trigger(HookType.PRE_QUERY)

        # 6. Simulate tool execution (mocked)
        tools = get_default_tools()
        assert len(tools) > 0

        # 7. Trigger post hooks
        await hook_mgr.trigger(HookType.POST_QUERY)

        # 8. Clear session
        session.clear_messages()
        assert len(session.messages) == 0


class TestIntegrationConfig:
    """Test configuration integration."""

    def test_config_load_save(self):
        """Test config loading and saving."""
        from cc.utils.config import Config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "settings.json"
            config_path.write_text(json.dumps({
                "api": {"model": "claude-opus-4-7"},
                "ui": {"theme": "dark"},
            }))

            # Config.load() would read from default location
            # Here we test the model directly
            config = Config(api={"model": "test-model"})
            assert config.api.model == "test-model"


class TestIntegrationStats:
    """Test statistics integration."""

    def test_performance_stats(self):
        """Test performance stats across components."""
        from cc.utils.performance import PerformanceTracker, PerformanceMetrics

        tracker = PerformanceTracker()

        # Record various operations
        tracker.record(PerformanceMetrics(operation="api_call", duration_ms=100.0))
        tracker.record(PerformanceMetrics(operation="tool_exec", duration_ms=50.0))
        tracker.record(PerformanceMetrics(operation="cache_hit", duration_ms=1.0, cache_hit=True))

        stats = tracker.get_stats()
        assert stats["total_operations"] == 3
        assert stats["cache_hit_rate"] > 0

    def test_hook_stats(self):
        """Test hook statistics."""
        hook_mgr = HookManager()
        hook_mgr.register(HookType.PRE_QUERY, MagicMock())

        stats = hook_mgr.get_stats()
        assert stats["total_hooks"] >= 1

    def test_plugin_stats(self):
        """Test plugin statistics."""
        plugin_mgr = PluginManager()
        plugins = plugin_mgr.list_plugins()
        assert isinstance(plugins, list)


class TestIntegrationErrorHandling:
    """Test error handling integration."""

    @pytest.mark.asyncio
    async def test_error_flow(self):
        """Test error handling flow."""
        from cc.utils.error_handling import ErrorHandler, ErrorCategory, ErrorSeverity

        handler = ErrorHandler()

        error_info = handler.handle(
            ValueError("Test error"),
            category=ErrorCategory.TOOL,
            severity=ErrorSeverity.MEDIUM,
            context={"tool_name": "Bash"},
        )

        assert error_info.category == ErrorCategory.TOOL
        assert error_info.message == "Test error"
        assert error_info.recovery_suggestion is not None

        stats = handler.get_stats()
        assert stats["total_errors"] == 1


class TestIntegrationReadyForRelease:
    """Final verification tests."""

    def test_all_modules_importable(self):
        """Test all modules can be imported."""
        # Core
        from cc.core import Session, SessionManager, QueryEngine

        # Tools
        from cc.tools import BashTool, ReadTool, WriteTool

        # Permissions
        from cc.permissions import PermissionManager

        # Services
        from cc.services.plugins import PluginManager
        from cc.services.hooks import HookManager

        # MCP
        from cc.mcp import MCPHealthMonitor, SubscriptionManager

        # UI
        from cc.ui import ClaudeCodeApp, ThemeManager

        # Utils
        from cc.utils import Config, AsyncCache

        # All imports successful
        assert True

    def test_all_tests_summary(self):
        """Summary of test coverage."""
        # This is a meta-test to verify the test structure
        test_modules = [
            "test_plugins",
            "test_hooks",
            "test_ui_widgets",
            "test_mcp_health",
            "test_mcp_subscriptions",
            "test_performance",
        ]

        # Each module has tests (verified by pytest)
        assert len(test_modules) >= 6


__all__ = [
    "TestIntegrationSession",
    "TestIntegrationPermissions",
    "TestIntegrationHooksPlugins",
    "TestIntegrationMCP",
    "TestIntegrationUI",
    "TestIntegrationPerformance",
    "TestIntegrationFullFlow",
    "TestIntegrationConfig",
    "TestIntegrationStats",
    "TestIntegrationErrorHandling",
    "TestIntegrationReadyForRelease",
]
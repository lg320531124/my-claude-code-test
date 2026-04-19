"""Tests for Hooks System."""

import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
import tempfile

from cc.services.hooks.hooks_system import (
    HookType,
    HookContext,
    HookResult,
    Hook,
    HookRegistry,
    HookManager,
    get_hook_manager,
    register_hook,
    trigger_hook,
    create_logging_hook,
    create_timing_hook,
    create_validation_hook,
)


class TestHookType:
    """Test HookType enum."""

    def test_all_types(self):
        """Test all hook types exist."""
        types = [
            HookType.PRE_TOOL_EXECUTE,
            HookType.POST_TOOL_EXECUTE,
            HookType.PRE_QUERY,
            HookType.POST_QUERY,
            HookType.ON_MESSAGE,
            HookType.ON_TEXT_STREAM,
            HookType.ON_SESSION_START,
            HookType.ON_SESSION_END,
            HookType.ON_SESSION_SAVE,
            HookType.ON_ERROR,
            HookType.ON_RETRY,
            HookType.ON_FILE_READ,
            HookType.ON_FILE_WRITE,
            HookType.ON_FILE_EDIT,
            HookType.PRE_COMMIT,
            HookType.POST_COMMIT,
            HookType.ON_CONFIG_CHANGE,
            HookType.USER_PROMPT_SUBMIT,
        ]
        for t in types:
            assert isinstance(t.value, str)

    def test_from_string(self):
        """Test creating from string."""
        hook_type = HookType("pre_query")
        assert hook_type == HookType.PRE_QUERY


class TestHookContext:
    """Test HookContext dataclass."""

    def test_create_context(self):
        """Test creating hook context."""
        ctx = HookContext(
            event=HookType.PRE_QUERY,
            session_id="test-session",
            cwd=Path("/tmp"),
            data={"key": "value"},
            metadata={"meta": "data"},
        )
        assert ctx.event == HookType.PRE_QUERY
        assert ctx.session_id == "test-session"
        assert ctx.cwd == Path("/tmp")
        assert ctx.data == {"key": "value"}
        assert ctx.metadata == {"meta": "data"}

    def test_context_defaults(self):
        """Test context default values."""
        ctx = HookContext(event=HookType.ON_MESSAGE)
        assert ctx.timestamp > 0
        assert ctx.session_id is None
        assert ctx.cwd is None
        assert ctx.data == {}
        assert ctx.metadata == {}

    def test_timestamp_auto(self):
        """Test timestamp is auto-generated."""
        import time

        before = time.time()
        ctx = HookContext(event=HookType.PRE_QUERY)
        after = time.time()
        assert before <= ctx.timestamp <= after


class TestHookResult:
    """Test HookResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = HookResult(success=True)
        assert result.success is True
        assert result.modified is False
        assert result.data is None
        assert result.error is None
        assert result.block is False

    def test_modified_result(self):
        """Test modified result."""
        result = HookResult(success=True, modified=True, data={"modified": "data"})
        assert result.success is True
        assert result.modified is True
        assert result.data == {"modified": "data"}

    def test_error_result(self):
        """Test error result."""
        result = HookResult(success=False, error="Something failed")
        assert result.success is False
        assert result.error == "Something failed"

    def test_block_result(self):
        """Test blocking result."""
        result = HookResult(success=True, block=True)
        assert result.block is True


class TestHook:
    """Test Hook class."""

    def test_create_hook(self):
        """Test creating a hook."""
        callback = MagicMock()
        hook = Hook(
            event=HookType.PRE_QUERY,
            callback=callback,
            priority=10,
            name="test_hook",
            blocking=True,
        )
        assert hook.event == HookType.PRE_QUERY
        assert hook.callback == callback
        assert hook.priority == 10
        assert hook.name == "test_hook"
        assert hook.blocking is True
        assert hook.enabled is True
        assert hook.call_count == 0

    def test_default_name(self):
        """Test default hook name."""
        callback = MagicMock()
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        assert hook.name.startswith("hook_")

    def test_enable_disable(self):
        """Test enable/disable."""
        callback = MagicMock()
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)

        hook.disable()
        assert hook.enabled is False

        hook.enable()
        assert hook.enabled is True

    @pytest.mark.asyncio
    async def test_execute_sync_callback(self):
        """Test executing sync callback."""
        callback = MagicMock(return_value=HookResult(success=True))
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert hook.call_count == 1
        assert hook.last_call is not None
        callback.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_execute_async_callback(self):
        """Test executing async callback."""
        callback = AsyncMock(return_value=HookResult(success=True, modified=True))
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert result.modified is True
        callback.assert_called_once_with(ctx)

    @pytest.mark.asyncio
    async def test_execute_returns_dict(self):
        """Test callback returning dict."""
        callback = MagicMock(return_value={"key": "value"})
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert result.modified is True
        assert result.data == {"key": "value"}

    @pytest.mark.asyncio
    async def test_execute_returns_none(self):
        """Test callback returning None."""
        callback = MagicMock(return_value=None)
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert result.modified is False

    @pytest.mark.asyncio
    async def test_execute_returns_false(self):
        """Test callback returning False (blocking)."""
        callback = MagicMock(return_value=False)
        hook = Hook(event=HookType.PRE_QUERY, callback=callback, blocking=True)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert result.block is True

    @pytest.mark.asyncio
    async def test_execute_disabled(self):
        """Test executing disabled hook."""
        callback = MagicMock()
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        hook.disable()
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is True
        assert hook.call_count == 0
        callback.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_error(self):
        """Test callback raising error."""
        callback = MagicMock(side_effect=ValueError("Test error"))
        hook = Hook(event=HookType.PRE_QUERY, callback=callback)
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook.execute(ctx)
        assert result.success is False
        assert result.error == "Test error"


class TestHookRegistry:
    """Test HookRegistry class."""

    def test_init(self):
        """Test registry initialization."""
        registry = HookRegistry()
        assert registry.hooks == {}
        assert registry._global_hooks == []

    def test_register(self):
        """Test registering a hook."""
        registry = HookRegistry()
        callback = MagicMock()
        hook = registry.register(
            HookType.PRE_QUERY,
            callback,
            priority=5,
            name="test",
        )
        assert hook.event == HookType.PRE_QUERY
        assert HookType.PRE_QUERY in registry.hooks
        assert hook in registry.hooks[HookType.PRE_QUERY]

    def test_register_priority_sort(self):
        """Test hooks sorted by priority."""
        registry = HookRegistry()
        hook1 = registry.register(HookType.PRE_QUERY, MagicMock(), priority=10)
        hook2 = registry.register(HookType.PRE_QUERY, MagicMock(), priority=5)
        hook3 = registry.register(HookType.PRE_QUERY, MagicMock(), priority=15)

        hooks = registry.get_hooks(HookType.PRE_QUERY)
        assert hooks[0] == hook2  # priority 5
        assert hooks[1] == hook1  # priority 10
        assert hooks[2] == hook3  # priority 15

    def test_register_global(self):
        """Test registering global hook."""
        registry = HookRegistry()
        callback = MagicMock()
        hook = registry.register_global(callback, priority=10)
        assert hook.event is None
        assert hook in registry._global_hooks

    def test_unregister(self):
        """Test unregistering hook."""
        registry = HookRegistry()
        hook = registry.register(HookType.PRE_QUERY, MagicMock())
        result = registry.unregister(hook)
        assert result is True
        assert hook not in registry.hooks.get(HookType.PRE_QUERY, [])

    def test_unregister_not_found(self):
        """Test unregistering non-existent hook."""
        registry = HookRegistry()
        hook = Hook(HookType.PRE_QUERY, MagicMock())
        result = registry.unregister(hook)
        assert result is False

    def test_unregister_by_name(self):
        """Test unregistering by name."""
        registry = HookRegistry()
        registry.register(HookType.PRE_QUERY, MagicMock(), name="hook1")
        registry.register(HookType.PRE_QUERY, MagicMock(), name="hook1")
        registry.register(HookType.POST_QUERY, MagicMock(), name="hook1")

        removed = registry.unregister_by_name("hook1")
        assert removed == 3

    def test_get_hooks_with_global(self):
        """Test getting hooks including global."""
        registry = HookRegistry()
        local = registry.register(HookType.PRE_QUERY, MagicMock(), priority=10)
        global_hook = registry.register_global(MagicMock(), priority=5)

        hooks = registry.get_hooks(HookType.PRE_QUERY)
        assert global_hook in hooks
        assert local in hooks
        # Global should be first due to priority
        assert hooks[0] == global_hook

    @pytest.mark.asyncio
    async def test_trigger(self):
        """Test triggering hooks."""
        registry = HookRegistry()
        results = []

        async def hook1(ctx):
            results.append("hook1")
            return HookResult(success=True)

        async def hook2(ctx):
            results.append("hook2")
            return HookResult(success=True)

        registry.register(HookType.PRE_QUERY, hook1)
        registry.register(HookType.PRE_QUERY, hook2)

        ctx = HookContext(event=HookType.PRE_QUERY)
        hook_results = await registry.trigger(HookType.PRE_QUERY, ctx)

        assert results == ["hook1", "hook2"]
        assert len(hook_results) == 2

    @pytest.mark.asyncio
    async def test_trigger_blocking(self):
        """Test blocking hook stops execution."""
        registry = HookRegistry()
        results = []

        async def hook1(ctx):
            results.append("hook1")
            return HookResult(success=True, block=True)

        async def hook2(ctx):
            results.append("hook2")
            return HookResult(success=True)

        registry.register(HookType.PRE_QUERY, hook1, blocking=True)
        registry.register(HookType.PRE_QUERY, hook2)

        ctx = HookContext(event=HookType.PRE_QUERY)
        await registry.trigger(HookType.PRE_QUERY, ctx)

        # hook2 should not be called due to blocking
        assert results == ["hook1"]

    def test_clear_event(self):
        """Test clearing hooks for specific event."""
        registry = HookRegistry()
        registry.register(HookType.PRE_QUERY, MagicMock())
        registry.register(HookType.POST_QUERY, MagicMock())

        count = registry.clear(HookType.PRE_QUERY)
        assert count == 1
        assert registry.hooks.get(HookType.PRE_QUERY, []) == []
        assert HookType.POST_QUERY in registry.hooks

    def test_clear_all(self):
        """Test clearing all hooks."""
        registry = HookRegistry()
        registry.register(HookType.PRE_QUERY, MagicMock())
        registry.register(HookType.POST_QUERY, MagicMock())
        registry.register_global(MagicMock())

        count = registry.clear()
        assert count == 3
        assert registry.hooks == {}
        assert registry._global_hooks == []

    def test_get_stats(self):
        """Test getting statistics."""
        registry = HookRegistry()
        hook1 = registry.register(HookType.PRE_QUERY, MagicMock())
        hook2 = registry.register(HookType.POST_QUERY, MagicMock())
        hook1.call_count = 5
        hook2.call_count = 3

        stats = registry.get_stats()
        assert stats["total_hooks"] == 2
        assert stats["events"]["pre_query"]["count"] == 1
        assert stats["events"]["pre_query"]["total_calls"] == 5
        assert stats["events"]["post_query"]["total_calls"] == 3


class TestHookManager:
    """Test HookManager class."""

    def test_init(self):
        """Test manager initialization."""
        manager = HookManager()
        assert manager.registry is not None
        assert manager._enabled is True

    def test_register_string_event(self):
        """Test registering with string event."""
        manager = HookManager()
        callback = MagicMock()
        hook = manager.register("pre_query", callback)
        assert hook.event == HookType.PRE_QUERY

    def test_enable_disable(self):
        """Test enable/disable."""
        manager = HookManager()
        manager.disable()
        assert manager._enabled is False
        manager.enable()
        assert manager._enabled is True

    @pytest.mark.asyncio
    async def test_trigger_disabled(self):
        """Test trigger when disabled returns empty."""
        manager = HookManager()
        manager.register(HookType.PRE_QUERY, MagicMock())
        manager.disable()

        results = await manager.trigger(HookType.PRE_QUERY)
        assert results == []

    @pytest.mark.asyncio
    async def test_trigger_with_data(self):
        """Test triggering with data."""
        manager = HookManager()
        callback = AsyncMock(return_value=HookResult(success=True))
        manager.register(HookType.PRE_QUERY, callback)

        results = await manager.trigger(
            HookType.PRE_QUERY,
            data={"key": "value"},
            session_id="test",
        )
        assert len(results) == 1
        assert results[0].success is True
        callback.assert_called_once()
        ctx = callback.call_args[0][0]
        assert ctx.data == {"key": "value"}

    def test_unregister(self):
        """Test unregistering."""
        manager = HookManager()
        hook = manager.register(HookType.PRE_QUERY, MagicMock())
        result = manager.unregister(hook)
        assert result is True

    def test_get_stats(self):
        """Test getting stats."""
        manager = HookManager()
        manager.register(HookType.PRE_QUERY, MagicMock())
        stats = manager.get_stats()
        assert "total_hooks" in stats

    def test_clear_all(self):
        """Test clearing all."""
        manager = HookManager()
        manager.register(HookType.PRE_QUERY, MagicMock())
        count = manager.clear_all()
        assert count == 1


class TestUtilityHooks:
    """Test utility hook factories."""

    @pytest.mark.asyncio
    async def test_logging_hook(self):
        """Test logging hook."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "log.json"
            hook = create_logging_hook(log_file)
            ctx = HookContext(
                event=HookType.PRE_QUERY,
                data={"test": "data"},
            )

            result = await hook(ctx)
            assert result.success is True

            import json

            content = json.loads(log_file.read_text())
            assert content["event"] == "pre_query"
            assert content["data"] == {"test": "data"}

    @pytest.mark.asyncio
    async def test_logging_hook_no_file(self):
        """Test logging hook without file."""
        hook = create_logging_hook()
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook(ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_timing_hook(self):
        """Test timing hook."""
        hook = create_timing_hook()
        ctx1 = HookContext(event=HookType.PRE_QUERY)
        ctx2 = HookContext(event=HookType.PRE_QUERY)

        result1 = await hook(ctx1)
        result2 = await hook(ctx2)

        # Check that timings are tracked (hook returns success)
        assert result1.success is True
        assert result2.success is True

    @pytest.mark.asyncio
    async def test_validation_hook_pass(self):
        """Test validation hook passes."""
        rule = MagicMock(return_value=True)
        hook = create_validation_hook([rule])
        ctx = HookContext(event=HookType.PRE_QUERY, data={"valid": True})

        result = await hook(ctx)
        assert result.success is True
        assert result.block is False

    @pytest.mark.asyncio
    async def test_validation_hook_fail(self):
        """Test validation hook fails."""
        rule = MagicMock(return_value=False)
        hook = create_validation_hook([rule])
        ctx = HookContext(event=HookType.PRE_QUERY, data={"valid": False})

        result = await hook(ctx)
        assert result.success is False
        assert result.block is True
        assert result.error == "Validation failed"

    @pytest.mark.asyncio
    async def test_validation_hook_async_rule(self):
        """Test validation hook with async rule."""
        async def async_rule(data):
            return data.get("allowed", False)

        hook = create_validation_hook([async_rule])
        ctx = HookContext(event=HookType.PRE_QUERY, data={"allowed": True})

        result = await hook(ctx)
        assert result.success is True

    @pytest.mark.asyncio
    async def test_validation_hook_exception(self):
        """Test validation hook with exception."""
        rule = MagicMock(side_effect=ValueError("Rule error"))
        hook = create_validation_hook([rule])
        ctx = HookContext(event=HookType.PRE_QUERY)

        result = await hook(ctx)
        assert result.success is False
        assert result.block is True
        assert result.error == "Rule error"


class TestGlobals:
    """Test global functions."""

    def test_get_hook_manager(self):
        """Test getting global manager."""
        manager1 = get_hook_manager()
        manager2 = get_hook_manager()
        assert manager1 is manager2

    def test_register_hook_global(self):
        """Test global register_hook."""
        hook = register_hook("pre_query", MagicMock())
        assert hook.event == HookType.PRE_QUERY

    @pytest.mark.asyncio
    async def test_trigger_hook_global(self):
        """Test global trigger_hook."""
        callback = AsyncMock(return_value=HookResult(success=True))
        register_hook("post_query", callback)
        results = await trigger_hook("post_query", data={"test": True})
        assert len(results) >= 1
        # Note: This affects global state, so results may include other hooks
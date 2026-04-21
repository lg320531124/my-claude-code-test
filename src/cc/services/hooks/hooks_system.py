"""Hooks System - Event hooks for extensibility."""

from __future__ import annotations
import asyncio
import time
from typing import Callable, Optional
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class HookType(Enum):
    """Hook event types."""
    # Tool hooks
    PRE_TOOL_EXECUTE = "pre_tool_execute"
    POST_TOOL_EXECUTE = "post_tool_execute"

    # Query hooks
    PRE_QUERY = "pre_query"
    POST_QUERY = "post_query"

    # Message hooks
    ON_MESSAGE = "on_message"
    ON_TEXT_STREAM = "on_text_stream"

    # Session hooks
    ON_SESSION_START = "on_session_start"
    ON_SESSION_END = "on_session_end"
    ON_SESSION_SAVE = "on_session_save"

    # Error hooks
    ON_ERROR = "on_error"
    ON_RETRY = "on_retry"

    # File hooks
    ON_FILE_READ = "on_file_read"
    ON_FILE_WRITE = "on_file_write"
    ON_FILE_EDIT = "on_file_edit"

    # Git hooks
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"

    # Config hooks
    ON_CONFIG_CHANGE = "on_config_change"

    # User hooks
    USER_PROMPT_SUBMIT = "user_prompt_submit"


@dataclass
class HookContext:
    """Context passed to hooks."""
    event: HookType
    timestamp: float = field(default_factory=time.time)
    session_id: Optional[str] = None
    cwd: Optional[Path] = None
    data: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)


@dataclass
class HookResult:
    """Result from hook execution."""
    success: bool
    modified: bool = False  # Did hook modify data?
    data: Optional[dict] = None
    error: Optional[str] = None
    block: bool = False  # Should block the original action?


class Hook:
    """Single hook definition."""

    def __init__(
        self,
        event: HookType,
        callback: Callable,
        priority: int = 0,
        name: Optional[str] = None,
        blocking: bool = False,
    ):
        self.event = event
        self.callback = callback
        self.priority = priority
        self.name = name or f"hook_{id(callback)}"
        self.blocking = blocking
        self.enabled = True
        self.call_count = 0
        self.last_call: Optional[float] = None
        self.last_result: Optional[HookResult] = None

    async def execute(self, ctx: HookContext) -> HookResult:
        """Execute hook."""
        if not self.enabled:
            return HookResult(success=True)

        self.call_count += 1
        self.last_call = time.time()

        try:
            if asyncio.iscoroutinefunction(self.callback):
                result = await self.callback(ctx)
            else:
                result = self.callback(ctx)

            # Handle result
            if isinstance(result, HookResult):
                self.last_result = result
                return result
            elif isinstance(result, dict):
                self.last_result = HookResult(
                    success=True,
                    modified=True,
                    data=result,
                )
                return self.last_result
            elif result is None:
                self.last_result = HookResult(success=True)
                return self.last_result
            elif result is False:
                self.last_result = HookResult(
                    success=True,
                    block=True,
                )
                return self.last_result
            else:
                self.last_result = HookResult(success=True)
                return self.last_result

        except Exception as e:
            self.last_result = HookResult(
                success=False,
                error=str(e),
            )
            return self.last_result

    def disable(self) -> None:
        """Disable hook."""
        self.enabled = False

    def enable(self) -> None:
        """Enable hook."""
        self.enabled = True


class HookRegistry:
    """Registry for all hooks."""

    def __init__(self):
        self.hooks: Dict[HookType, List[Hook]] = {}
        self._global_hooks: List[Hook] = []  # Hooks for all events

    def register(
        self,
        event: HookType,
        callback: Callable,
        priority: int = 0,
        name: Optional[str] = None,
        blocking: bool = False,
    ) -> Hook:
        """Register a hook."""
        hook = Hook(
            event=event,
            callback=callback,
            priority=priority,
            name=name,
            blocking=blocking,
        )

        if event not in self.hooks:
            self.hooks[event] = []
        self.hooks[event].append(hook)

        # Sort by priority
        self.hooks[event].sort(key=lambda h: h.priority)

        return hook

    def register_global(
        self,
        callback: Callable,
        priority: int = 0,
        name: Optional[str] = None,
    ) -> Hook:
        """Register hook for all events."""
        hook = Hook(
            event=None,  # Global
            callback=callback,
            priority=priority,
            name=name,
        )
        self._global_hooks.append(hook)
        self._global_hooks.sort(key=lambda h: h.priority)
        return hook

    def unregister(self, hook: Hook) -> bool:
        """Unregister a hook."""
        if hook.event and hook.event in self.hooks:
            try:
                self.hooks[hook.event].remove(hook)
                return True
            except ValueError:
                pass

        try:
            self._global_hooks.remove(hook)
            return True
        except ValueError:
            pass

        return False

    def unregister_by_name(self, name: str) -> int:
        """Unregister hooks by name."""
        removed = 0

        for event in self.hooks:
            hooks_to_remove = [h for h in self.hooks[event] if h.name == name]
            for h in hooks_to_remove:
                self.hooks[event].remove(h)
                removed += 1

        global_to_remove = [h for h in self._global_hooks if h.name == name]
        for h in global_to_remove:
            self._global_hooks.remove(h)
            removed += 1

        return removed

    def get_hooks(self, event: HookType) -> List[Hook]:
        """Get hooks for event."""
        event_hooks = self.hooks.get(event, [])
        global_hooks = self._global_hooks
        combined = event_hooks + global_hooks
        return sorted(combined, key=lambda h: h.priority)

    async def trigger(self, event: HookType, ctx: HookContext) -> List[HookResult]:
        """Trigger all hooks for event."""
        hooks = self.get_hooks(event)
        results = []

        for hook in hooks:
            result = await hook.execute(ctx)
            results.append(result)

            # Blocking hook stops execution
            if result.block and hook.blocking:
                break

        return results

    def clear(self, event: Optional[HookType] = None) -> int:
        """Clear hooks."""
        if event:
            count = len(self.hooks.get(event, []))
            self.hooks[event] = []
            return count

        total = sum(len(h) for h in self.hooks.values())
        total += len(self._global_hooks)
        self.hooks = {}
        self._global_hooks = []
        return total

    def get_stats(self) -> dict:
        """Get hook statistics."""
        stats = {
            "total_hooks": sum(len(h) for h in self.hooks.values()) + len(self._global_hooks),
            "events": {},
        }

        for event, hooks in self.hooks.items():
            stats["events"][event.value] = {
                "count": len(hooks),
                "total_calls": sum(h.call_count for h in hooks),
            }

        return stats


class HookManager:
    """Manages hook system."""

    def __init__(self):
        self.registry = HookRegistry()
        self._enabled = True

    def register(
        self,
        event: str | HookType,
        callback: Callable,
        **kwargs,
    ) -> Hook:
        """Register hook."""
        if isinstance(event, str):
            event = HookType(event)

        return self.registry.register(event, callback, **kwargs)

    async def trigger(
        self,
        event: str | HookType,
        data: Optional[dict] = None,
        **kwargs,
    ) -> List[HookResult]:
        """Trigger event."""
        if not self._enabled:
            return []

        if isinstance(event, str):
            event = HookType(event)

        ctx = HookContext(
            event=event,
            data=data or {},
            metadata=kwargs,
        )

        return await self.registry.trigger(event, ctx)

    def enable(self) -> None:
        """Enable hook system."""
        self._enabled = True

    def disable(self) -> None:
        """Disable hook system."""
        self._enabled = False

    def unregister(self, hook: Hook) -> bool:
        """Unregister hook."""
        return self.registry.unregister(hook)

    def get_stats(self) -> dict:
        """Get statistics."""
        return self.registry.get_stats()

    def clear_all(self) -> int:
        """Clear all hooks."""
        return self.registry.clear()


# Common hooks
def create_logging_hook(log_file: Optional[Path] = None) -> Callable:
    """Create a logging hook."""
    async def log_hook(ctx: HookContext) -> HookResult:
        import json

        entry = {
            "event": ctx.event.value,
            "timestamp": ctx.timestamp,
            "data": ctx.data,
        }

        if log_file:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None,
                lambda: log_file.write_text(json.dumps(entry) + "\n"),
            )

        return HookResult(success=True)

    return log_hook


def create_timing_hook() -> Callable:
    """Create a timing hook."""
    timings: Dict[str, List[float]] = {}

    async def time_hook(ctx: HookContext) -> HookResult:
        key = ctx.event.value
        if key not in timings:
            timings[key] = []

        timings[key].append(ctx.timestamp)
        return HookResult(success=True)

    return time_hook


def create_validation_hook(rules: List[Callable]) -> Callable:
    """Create a validation hook."""
    async def validate_hook(ctx: HookContext) -> HookResult:
        for rule in rules:
            try:
                if asyncio.iscoroutinefunction(rule):
                    valid = await rule(ctx.data)
                else:
                    valid = rule(ctx.data)

                if not valid:
                    return HookResult(
                        success=False,
                        block=True,
                        error="Validation failed",
                    )
            except Exception as e:
                return HookResult(
                    success=False,
                    block=True,
                    error=str(e),
                )

        return HookResult(success=True)

    return validate_hook


# Global manager
_hook_manager: Optional[HookManager] = None


def get_hook_manager() -> HookManager:
    """Get global hook manager."""
    global _hook_manager
    if _hook_manager is None:
        _hook_manager = HookManager()
    return _hook_manager


def register_hook(event: str, callback: Callable, **kwargs) -> Hook:
    """Register hook globally."""
    return get_hook_manager().register(event, callback, **kwargs)


async def trigger_hook(event: str, data: Optional[dict] = None, **kwargs) -> List[HookResult]:
    """Trigger hook globally."""
    return await get_hook_manager().trigger(event, data, **kwargs)

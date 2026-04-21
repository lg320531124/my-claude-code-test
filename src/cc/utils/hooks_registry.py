"""Hooks Registration - Hook system utilities."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class HookType(Enum):
    """Hook types."""
    PRE_TOOL_USE = "pre_tool_use"
    POST_TOOL_USE = "post_tool_use"
    PRE_QUERY = "pre_query"
    POST_QUERY = "post_query"
    PRE_COMMIT = "pre_commit"
    POST_COMMIT = "post_commit"
    SESSION_START = "session_start"
    SESSION_END = "session_end"
    ERROR = "error"
    MESSAGE_ADD = "message_add"


@dataclass
class HookConfig:
    """Hook configuration."""
    name: str
    type: HookType
    handler: Callable
    enabled: bool = True
    priority: int = 0
    timeout_ms: int = 30000


class HookRegistry:
    """Hook registry."""

    def __init__(self):
        self._hooks: Dict[HookType, List[HookConfig]] = {}

    def register(
        self,
        hook_type: HookType,
        name: str,
        handler: Callable,
        priority: int = 0,
        timeout_ms: int = 30000,
    ) -> HookConfig:
        """Register hook."""
        config = HookConfig(
            name=name,
            type=hook_type,
            handler=handler,
            priority=priority,
            timeout_ms=timeout_ms,
        )

        if hook_type not in self._hooks:
            self._hooks[hook_type] = []

        self._hooks[hook_type].append(config)
        self._hooks[hook_type].sort(key=lambda h: h.priority, reverse=True)

        return config

    def unregister(self, hook_type: HookType, name: str) -> bool:
        """Unregister hook."""
        if hook_type not in self._hooks:
            return False

        hooks = [h for h in self._hooks[hook_type] if h.name != name]
        self._hooks[hook_type] = hooks
        return True

    async def execute(self, hook_type: HookType, context: Dict[str, Any]) -> List[Any]:
        """Execute hooks."""
        results = []

        hooks = self._hooks.get(hook_type, [])
        for hook in hooks:
            if not hook.enabled:
                continue

            try:
                if asyncio.iscoroutinefunction(hook.handler):
                    result = await asyncio.wait_for(
                        hook.handler(context),
                        timeout=hook.timeout_ms / 1000,
                    )
                else:
                    result = hook.handler(context)
                results.append(result)
            except asyncio.TimeoutError:
                results.append(None)
            except Exception as e:
                results.append({"error": str(e)})

        return results

    def get_hooks(self, hook_type: HookType = None) -> List[HookConfig]:
        """Get hooks."""
        if hook_type:
            return self._hooks.get(hook_type, [])
        return [h for hooks in self._hooks.values() for h in hooks]

    def enable_hook(self, name: str) -> bool:
        """Enable hook."""
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.name == name:
                    hook.enabled = True
                    return True
        return False

    def disable_hook(self, name: str) -> bool:
        """Disable hook."""
        for hooks in self._hooks.values():
            for hook in hooks:
                if hook.name == name:
                    hook.enabled = False
                    return True
        return False


# Global registry
_registry: Optional[HookRegistry] = None


def get_hook_registry() -> HookRegistry:
    """Get global registry."""
    if _registry is None:
        _registry = HookRegistry()
    return _registry


async def register_hook(
    hook_type: HookType,
    name: str,
    handler: Callable,
) -> HookConfig:
    """Register hook."""
    return get_hook_registry().register(hook_type, name, handler)


async def execute_hooks(hook_type: HookType, context: Dict[str, Any]) -> List[Any]:
    """Execute hooks."""
    return await get_hook_registry().execute(hook_type, context)


__all__ = [
    "HookType",
    "HookConfig",
    "HookRegistry",
    "get_hook_registry",
    "register_hook",
    "execute_hooks",
]
"""Tool Permission Hook - Async permission checking."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass

from ..services.hooks import Hook, HookType, HookContext, HookResult, get_hook_manager
from ..tools.shared.permissions import check_tool_permission, check_bash_permission


@dataclass
class PermissionState:
    """Permission check state."""
    tool_name: str
    allowed: bool
    reason: str = ""
    pattern: str = ""


class ToolPermissionHook:
    """Hook for checking tool permissions."""

    def __init__(self):
        self._manager = get_hook_manager()
        self._cache: Dict[str, PermissionState] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}

    async def check_permission(self, tool_name: str, tool_input: Dict) -> PermissionState:
        """Check if tool can be used."""
        # Check cache
        cache_key = f"{tool_name}:{hash(str(tool_input))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check permission
        allowed = await check_tool_permission(tool_name)

        state = PermissionState(
            tool_name=tool_name,
            allowed=allowed,
            reason="auto-allowed" if allowed else "requires approval",
        )

        self._cache[cache_key] = state
        return state

    async def check_bash_permission(self, command: str) -> PermissionState:
        """Check bash command permission."""
        allowed = await check_bash_permission(command)

        state = PermissionState(
            tool_name="Bash",
            allowed=allowed,
            reason="auto-allowed" if allowed else "requires approval",
            pattern=command.split()[0] if command.split() else "",
        )

        return state

    async def request_permission(
        self,
        tool_name: str,
        tool_input: Dict,
        timeout: float = 30.0
    ) -> PermissionState:
        """Request permission from user."""
        request_id = f"{tool_name}_{asyncio.get_event_loop().time()}"

        future = asyncio.get_event_loop().create_future()
        self._pending_requests[request_id] = future

        # Would show UI dialog
        # ...

        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            return PermissionState(
                tool_name=tool_name,
                allowed=False,
                reason="timeout",
            )
        finally:
            self._pending_requests.pop(request_id, None)

    def grant_permission(self, request_id: str, pattern: str = None) -> None:
        """Grant pending permission request."""
        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            state = PermissionState(
                tool_name=request_id.split("_")[0],
                allowed=True,
                pattern=pattern or "",
            )
            future.set_result(state)

    def deny_permission(self, request_id: str) -> None:
        """Deny pending permission request."""
        if request_id in self._pending_requests:
            future = self._pending_requests[request_id]
            state = PermissionState(
                tool_name=request_id.split("_")[0],
                allowed=False,
                reason="denied",
            )
            future.set_result(state)

    def clear_cache(self) -> None:
        """Clear permission cache."""
        self._cache.clear()


async def use_tool_permission(tool_name: str) -> bool:
    """Hook to check tool permission.

    Usage:
        allowed = await use_tool_permission("Bash")
        if allowed:
            # Execute tool
    """
    hook = ToolPermissionHook()
    state = await hook.check_permission(tool_name, {})
    return state.allowed


async def use_bash_permission(command: str) -> bool:
    """Hook to check bash permission.

    Usage:
        allowed = await use_bash_permission("ls -la")
        if allowed:
            # Execute command
    """
    hook = ToolPermissionHook()
    state = await hook.check_bash_permission(command)
    return state.allowed


def register_permission_hook() -> None:
    """Register permission check hook."""
    manager = get_hook_manager()

    async def permission_handler(context: HookContext) -> HookResult:
        tool_name = context.data.get("tool_name")
        tool_input = context.data.get("tool_input", {})

        hook = ToolPermissionHook()
        state = await hook.check_permission(tool_name, tool_input)

        return HookResult(
            success=state.allowed,
            data={"permission": state},
            error=state.reason if not state.allowed else None,
        )

    manager.register(
        hook_type=HookType.PRE_TOOL_USE,
        name="tool_permission_check",
        handler=permission_handler,
        priority=100,  # High priority
    )


__all__ = [
    "PermissionState",
    "ToolPermissionHook",
    "use_tool_permission",
    "use_bash_permission",
    "register_permission_hook",
]
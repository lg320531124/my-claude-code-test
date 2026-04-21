"""Hook Permissions - Async tool permission checks."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable, Set
from dataclasses import dataclass, field
from enum import Enum


class PermissionAction(Enum):
    """Permission actions."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass
class PermissionRule:
    """Permission rule."""
    pattern: str
    action: PermissionAction
    priority: int = 0
    expires_at: Optional[float] = None
    created_at: float = 0.0
    match_count: int = 0


@dataclass
class PermissionContext:
    """Permission check context."""
    tool_name: str
    tool_input: Dict[str, Any]
    user_message: str = ""
    session_id: str = ""
    cwd: str = ""
    risk_level: str = "medium"
    metadata: Dict[str, Any] = field(default_factory=dict)


class PermissionChecker:
    """Async permission checker."""

    def __init__(self):
        self._rules: List[PermissionRule] = []
        self._cache: Dict[str, PermissionAction] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._callbacks: List[Callable] = []

    def add_rule(self, rule: PermissionRule) -> None:
        """Add permission rule."""
        self._rules.append(rule)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        self._cache.clear()

    def remove_rule(self, pattern: str) -> bool:
        """Remove rule by pattern."""
        self._rules = [r for r in self._rules if r.pattern != pattern]
        self._cache.clear()
        return True

    async def check_permission(
        self,
        context: PermissionContext,
    ) -> PermissionAction:
        """Check permission for tool call."""
        # Build cache key
        cache_key = f"{context.tool_name}:{context.risk_level}"

        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check rules
        for rule in self._rules:
            if self._matches_rule(rule, context):
                rule.match_count += 1

                # Check expiration
                if rule.expires_at and asyncio.get_event_loop().time() > rule.expires_at:
                    continue

                self._cache[cache_key] = rule.action
                return rule.action

        # Default to ask
        return PermissionAction.ASK

    def _matches_rule(self, rule: PermissionRule, context: PermissionContext) -> bool:
        """Check if rule matches context."""
        pattern = rule.pattern

        # Exact match
        if pattern == context.tool_name:
            return True

        # Pattern match (e.g., "Bash(rm *)")
        if "(" in pattern:
            tool_part, input_part = pattern.split("(", 1)
            input_part = input_part.rstrip(")")

            if tool_part != context.tool_name:
                return False

            # Check input pattern
            import fnmatch
            tool_input_str = str(context.tool_input)

            if input_part.endswith("*"):
                prefix = input_part[:-1]
                return tool_input_str.startswith(prefix)
            else:
                return fnmatch.fnmatch(tool_input_str, input_part)

        # Wildcard match
        if pattern.endswith("*"):
            return context.tool_name.startswith(pattern[:-1])

        return False

    async def request_permission(
        self,
        context: PermissionContext,
    ) -> PermissionAction:
        """Request permission from user."""
        # First check rules
        action = await self.check_permission(context)

        if action != PermissionAction.ASK:
            return action

        # Need to ask user - notify callbacks
        request_id = f"{context.session_id}:{context.tool_name}"

        future = asyncio.Future()
        self._pending_requests[request_id] = future

        # Notify callbacks
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(context, request_id)
                else:
                    callback(context, request_id)
            except Exception:
                pass

        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=300.0)
            return result
        except asyncio.TimeoutError:
            return PermissionAction.DENY
        finally:
            self._pending_requests.pop(request_id, None)

    def respond_permission(self, request_id: str, action: PermissionAction) -> None:
        """Respond to permission request."""
        future = self._pending_requests.get(request_id)
        if future and not future.done():
            future.set_result(action)

    def on_permission_request(self, callback: Callable) -> None:
        """Register callback for permission requests."""
        self._callbacks.append(callback)

    def get_rules(self) -> List[PermissionRule]:
        """Get all rules."""
        return self._rules.copy()

    def clear_cache(self) -> None:
        """Clear permission cache."""
        self._cache.clear()


class PermissionHooks:
    """Hooks for permission system."""

    def __init__(self, checker: PermissionChecker):
        self._checker = checker

    async def pre_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hook before tool use."""
        perm_context = PermissionContext(
            tool_name=context.get("tool_name", ""),
            tool_input=context.get("tool_input", {}),
            session_id=context.get("session_id", ""),
            cwd=context.get("cwd", ""),
            metadata=context,
        )

        # Determine risk level
        tool_name = context.get("tool_name", "")
        if tool_name == "Bash":
            cmd = str(context.get("tool_input", {}).get("command", ""))
            if any(d in cmd for d in ["rm", "sudo", "chmod", ">"]):
                perm_context.risk_level = "high"
            elif any(w in cmd for w in ["write", "save", "delete"]):
                perm_context.risk_level = "medium"
            else:
                perm_context.risk_level = "low"

        elif tool_name in ["Write", "Edit"]:
            perm_context.risk_level = "medium"

        elif tool_name in ["Read", "Glob", "Grep"]:
            perm_context.risk_level = "low"

        action = await self._checker.request_permission(perm_context)

        context["permission_action"] = action.value
        context["permission_context"] = perm_context

        return context

    async def post_tool_use(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Hook after tool use."""
        # Record permission usage
        action = context.get("permission_action", "ask")

        # Analytics
        context["permission_used"] = action

        return context


# Global checker
_checker: Optional[PermissionChecker] = None


def get_permission_checker() -> PermissionChecker:
    """Get global permission checker."""
    global _checker
    if _checker is None:
        _checker = PermissionChecker()
    return _checker


async def check_tool_permission(
    tool_name: str,
    tool_input: Dict[str, Any],
    **kwargs,
) -> PermissionAction:
    """Check permission for tool."""
    checker = get_permission_checker()
    context = PermissionContext(
        tool_name=tool_name,
        tool_input=tool_input,
        **kwargs,
    )
    return await checker.check_permission(context)


__all__ = [
    "PermissionAction",
    "PermissionRule",
    "PermissionContext",
    "PermissionChecker",
    "PermissionHooks",
    "get_permission_checker",
    "check_tool_permission",
]
"""Permission hooks - Tool call interception."""

from __future__ import annotations
from typing import Callable

from ..types.permission import PermissionResult
from ..types.tool import ToolUseContext
from .manager import PermissionManager
from .prompts import PermissionPrompter


class PermissionHook:
    """Hook for intercepting tool calls."""

    def __init__(
        self,
        manager: PermissionManager,
        prompter: PermissionPrompter,
    ):
        self.manager = manager
        self.prompter = prompter

    async def check(
        self,
        tool_name: str,
        tool_input: dict,
        ctx: ToolUseContext,
    ) -> PermissionResult:
        """Check permission for tool call."""
        # First check rules
        rule_result = self.manager.check(tool_name, tool_input)

        if rule_result.is_allowed:
            return rule_result

        if rule_result.is_denied:
            return rule_result

        # Needs prompting
        decision = await self.prompter.prompt(
            tool_name,
            tool_input,
            rule_result.reason,
        )

        return PermissionResult(
            decision=decision.value,
            reason=rule_result.reason,
        )


def create_permission_hook(
    auto_approve: bool = False,
) -> PermissionHook:
    """Create a permission hook."""
    manager = PermissionManager()
    prompter = PermissionPrompter(auto_approve=auto_approve)
    return PermissionHook(manager, prompter)


# Decorator for permission checking
def require_permission(tool_name: str):
    """Decorator to require permission for a function."""
    def decorator(func: Callable) -> Callable:
        async def wrapper(*args, **kwargs):
            # Extract context
            ctx = kwargs.get("ctx") or args[-1] if args else None
            if not ctx:
                raise ValueError("No context provided")

            # Check permission
            hook = create_permission_hook()
            result = await hook.check(tool_name, kwargs, ctx)

            if result.is_denied:
                raise PermissionError(f"Permission denied: {result.reason}")

            return await func(*args, **kwargs)

        return wrapper
    return decorator

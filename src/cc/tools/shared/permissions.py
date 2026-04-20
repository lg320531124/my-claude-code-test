"""Shared tool permissions.

Common permission checking logic for tools.
"""

from __future__ import annotations
import asyncio
import re
from typing import Dict, Any, Optional, Callable

from ..types.permission import PermissionResult, PermissionDecision


def match_wildcard_pattern(pattern: str, value: str) -> bool:
    """Match wildcard pattern against value."""
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    if pattern.startswith("*"):
        return value.endswith(pattern[1:])
    return pattern == value


def check_file_permission(
    file_path: str,
    deny_patterns: list[str],
    ask_patterns: list[str],
    allow_patterns: list[str],
) -> PermissionResult:
    """Check file permission based on patterns."""
    # Check deny first
    for pattern in deny_patterns:
        if match_wildcard_pattern(pattern, file_path):
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"File matches deny pattern: {pattern}",
                rule=pattern,
            )

    # Check ask
    for pattern in ask_patterns:
        if match_wildcard_pattern(pattern, file_path):
            return PermissionResult(
                decision=PermissionDecision.ASK,
                reason=f"File matches ask pattern: {pattern}",
                rule=pattern,
            )

    # Check allow
    for pattern in allow_patterns:
        if match_wildcard_pattern(pattern, file_path):
            return PermissionResult(
                decision=PermissionDecision.ALLOW,
                reason=f"File matches allow pattern: {pattern}",
                rule=pattern,
            )

    # Default: ask
    return PermissionResult(
        decision=PermissionDecision.ASK,
        reason="No explicit permission rule matched",
    )


def check_bash_permission(
    command: str,
    deny_patterns: list[str],
    ask_patterns: list[str],
    allow_patterns: list[str],
) -> PermissionResult:
    """Check bash command permission."""
    # Extract base command
    base_cmd = command.strip().split()[0] if command.strip() else ""

    # Check deny first
    for pattern in deny_patterns:
        if pattern.endswith("*"):
            # Prefix match
            if command.startswith(pattern[:-1]):
                return PermissionResult(
                    decision=PermissionDecision.DENY,
                    reason=f"Command matches deny pattern: {pattern}",
                    rule=pattern,
                )
        elif match_wildcard_pattern(pattern, base_cmd):
            return PermissionResult(
                decision=PermissionDecision.DENY,
                reason=f"Command matches deny pattern: {pattern}",
                rule=pattern,
            )

    # Check ask
    for pattern in ask_patterns:
        if pattern.endswith("*"):
            if command.startswith(pattern[:-1]):
                return PermissionResult(
                    decision=PermissionDecision.ASK,
                    reason=f"Command matches ask pattern: {pattern}",
                    rule=pattern,
                )
        elif match_wildcard_pattern(pattern, base_cmd):
            return PermissionResult(
                decision=PermissionDecision.ASK,
                reason=f"Command matches ask pattern: {pattern}",
                rule=pattern,
            )

    # Check allow
    for pattern in allow_patterns:
        if pattern.endswith("*"):
            if command.startswith(pattern[:-1]):
                return PermissionResult(
                    decision=PermissionDecision.ALLOW,
                    rule=pattern,
                )
        elif match_wildcard_pattern(pattern, base_cmd):
            return PermissionResult(
                decision=PermissionDecision.ALLOW,
                rule=pattern,
            )

    # Default: ask for non-readonly commands
    readonly_commands = ["ls", "cat", "pwd", "echo", "git status", "git log", "git diff"]
    if any(command.startswith(cmd) for cmd in readonly_commands):
        return PermissionResult(decision=PermissionDecision.ALLOW)

    return PermissionResult(
        decision=PermissionDecision.ASK,
        reason="Non-readonly command requires confirmation",
    )


async def async_check_permission(
    check_fn: Callable,
    *args,
) -> PermissionResult:
    """Run permission check in thread pool."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: check_fn(*args))


__all__ = [
    "match_wildcard_pattern",
    "check_file_permission",
    "check_bash_permission",
    "async_check_permission",
]
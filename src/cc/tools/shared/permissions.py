"""Tool Permissions - Permission checking for tools."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable, Awaitable
from dataclasses import dataclass, field
from enum import Enum


class PermissionLevel(Enum):
    """Permission levels."""
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


@dataclass
class PermissionResult:
    """Permission check result."""
    allowed: bool
    level: PermissionLevel
    reason: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)


class PermissionChecker:
    """Async permission checker for tools."""

    def __init__(self):
        self._allow_rules: List[str] = []
        self._ask_rules: List[str] = []
        self._deny_rules: List[str] = []
        self._hooks: List[Callable] = []
        self._cache: Dict[str, PermissionResult] = {}

    def add_allow_rule(self, pattern: str) -> None:
        """Add allow rule pattern."""
        self._allow_rules.append(pattern)
        self._cache.clear()

    def add_ask_rule(self, pattern: str) -> None:
        """Add ask rule pattern."""
        self._ask_rules.append(pattern)
        self._cache.clear()

    def add_deny_rule(self, pattern: str) -> None:
        """Add deny rule pattern."""
        self._deny_rules.append(pattern)
        self._cache.clear()

    async def check_permission(self, tool_name: str, args: Dict[str, Any]) -> PermissionResult:
        """Check if tool is allowed."""
        cache_key = f"{tool_name}:{hash(str(args))}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        for hook in self._hooks:
            try:
                if asyncio.iscoroutinefunction(hook):
                    result = await hook(tool_name, args)
                else:
                    result = hook(tool_name, args)
                if result:
                    return result
            except Exception:
                pass

        if self._matches_rules(tool_name, args, self._deny_rules):
            result = PermissionResult(allowed=False, level=PermissionLevel.DENY, reason="Blocked by deny rule")
            self._cache[cache_key] = result
            return result

        if self._matches_rules(tool_name, args, self._allow_rules):
            result = PermissionResult(allowed=True, level=PermissionLevel.ALLOW)
            self._cache[cache_key] = result
            return result

        if self._matches_rules(tool_name, args, self._ask_rules):
            result = PermissionResult(allowed=False, level=PermissionLevel.ASK, reason="Requires permission")
            self._cache[cache_key] = result
            return result

        result = PermissionResult(allowed=False, level=PermissionLevel.ASK, reason="No matching rule")
        self._cache[cache_key] = result
        return result

    def _matches_rules(self, tool_name: str, args: Dict, rules: List[str]) -> bool:
        for rule in rules:
            if self._match_pattern(rule, tool_name, args):
                return True
        return False

    def _match_pattern(self, pattern: str, tool_name: str, args: Dict) -> bool:
        if "(" in pattern and pattern.endswith(")"):
            parts = pattern.split("(")
            pattern_tool = parts[0]
            pattern_args = parts[1].rstrip(")")
            if pattern_tool != tool_name:
                return False
            if pattern_args == "*":
                return True
            if tool_name == "Bash":
                command = args.get("command", "")
                cmd_token = self._extract_command_token(command)
                if pattern_args.endswith("*"):
                    return cmd_token.startswith(pattern_args[:-1])
                return cmd_token == pattern_args
            return False
        else:
            if pattern.endswith("*"):
                return tool_name.startswith(pattern[:-1])
            return pattern == tool_name

    def _extract_command_token(self, command: str) -> str:
        tokens = command.split()
        i = 0
        while i < len(tokens):
            token = tokens[i]
            if token in {"sudo", "timeout", "env", "time"}:
                i += 1
            elif token.startswith("-") or "=" in token:
                i += 1
            else:
                return token
        return ""

    def load_rules(self, allow: List[str], ask: List[str], deny: List[str]) -> None:
        self._allow_rules = allow.copy()
        self._ask_rules = ask.copy()
        self._deny_rules = deny.copy()
        self._cache.clear()

    def get_rules(self) -> Dict[str, List[str]]:
        return {"allow": self._allow_rules.copy(), "ask": self._ask_rules.copy(), "deny": self._deny_rules.copy()}


_permission_checker: Optional[PermissionChecker] = None

def get_permission_checker() -> PermissionChecker:
    global _permission_checker
    if _permission_checker is None:
        _permission_checker = PermissionChecker()
    return _permission_checker

async def check_tool_permission(tool_name: str, args: Dict[str, Any]) -> bool:
    checker = get_permission_checker()
    result = await checker.check_permission(tool_name, args)
    return result.allowed

__all__ = ["PermissionLevel", "PermissionResult", "PermissionChecker", "get_permission_checker", "check_tool_permission"]

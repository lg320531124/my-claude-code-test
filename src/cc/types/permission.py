"""Permission types for Claude Code Python."""

from enum import Enum
from typing import Literal

from pydantic import BaseModel


class PermissionDecision(str, Enum):
    """Permission decision types."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionMode(str, Enum):
    """Permission mode for the session."""

    DEFAULT = "default"
    PLAN = "plan"
    BYPASS = "bypassPermissions"
    AUTO = "auto"


class PermissionResult(BaseModel):
    """Result of permission check."""

    decision: Literal["allow", "deny", "ask"]
    reason: str | None = None
    rule: str | None = None  # Which rule triggered this decision

    @property
    def is_allowed(self) -> bool:
        return self.decision == "allow"

    @property
    def is_denied(self) -> bool:
        return self.decision == "deny"

    @property
    def needs_confirmation(self) -> bool:
        return self.decision == "ask"


class PermissionRule(BaseModel):
    """A single permission rule."""

    pattern: str  # e.g., "Bash(ls *)", "Read", "Bash(rm *)"
    decision: PermissionDecision
    priority: int = 0  # Higher priority rules are checked first

    def matches(self, tool_name: str, tool_input: dict) -> bool:
        """Check if this rule matches the tool call."""
        # Parse pattern: "ToolName" or "ToolName(subpattern)"
        if "(" in self.pattern:
            base, subpattern = self.pattern.split("(")
            subpattern = subpattern.rstrip(")")
            if tool_name != base:
                return False
            # Check subpattern against input
            return self._matches_subpattern(subpattern, tool_input)
        else:
            # Simple tool name match
            return tool_name == self.pattern or self.pattern == "*"

    def _matches_subpattern(self, subpattern: str, input: dict) -> bool:
        """Match subpattern against tool input."""
        if subpattern == "*":
            return True
        # For Bash tool, match against command
        if "command" in input:
            cmd = input["command"]
            # Handle wildcards
            if subpattern.endswith("*"):
                return cmd.startswith(subpattern[:-1])
            return cmd == subpattern
        return False


class PermissionConfig(BaseModel):
    """Permission configuration."""

    allow: list[str] = []
    deny: list[str] = []
    ask: list[str] = []

    def to_rules(self) -> list[PermissionRule]:
        """Convert config to sorted rules."""
        rules: list[PermissionRule] = []
        for pattern in self.deny:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.DENY, priority=100))
        for pattern in self.ask:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.ASK, priority=50))
        for pattern in self.allow:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.ALLOW, priority=0))
        # Sort by priority (highest first)
        return sorted(rules, key=lambda r: -r.priority)
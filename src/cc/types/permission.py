"""Permission types for Claude Code Python.

Ported from TypeScript types/permissions.ts patterns:
- PermissionResult with behavior and updated_input
- PermissionMode enum
- Permission rules by source
- ToolPermissionContext
"""

from __future__ import annotations
import time

from enum import Enum
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field



class PermissionDecision(str, Enum):
    """Permission decision types (matching TypeScript behavior)."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionMode(str, Enum):
    """Permission mode for the session (matching TypeScript PermissionMode)."""

    DEFAULT = "default"
    PLAN = "plan"
    BYPASS = "bypassPermissions"
    AUTO = "auto"


@dataclass
class PermissionResult:
    """Result of permission check (matching TypeScript PermissionResult).

    Key fields:
    - behavior: 'allow', 'deny', or 'ask'
    - updated_input: optionally modified input (e.g., sandboxed path)
    - reason: explanation for the decision
    - rule: which rule triggered this decision
    """

    decision: PermissionDecision
    updated_input: Optional[Dict[str, Any]] = None
    reason: Optional[str] = None
    rule: Optional[str] = None  # Which rule triggered this decision

    def __post_init__(self):
        # Allow string decision to be converted to PermissionDecision
        if isinstance(self.decision, str):
            self.decision = PermissionDecision(self.decision)

    @property
    def behavior(self) -> str:
        """Alias for decision (matching TypeScript behavior)."""
        return self.decision.value

    @property
    def is_allowed(self) -> bool:
        return self.decision == PermissionDecision.ALLOW

    @property
    def is_denied(self) -> bool:
        return self.decision == PermissionDecision.DENY

    @property
    def needs_confirmation(self) -> bool:
        return self.decision == PermissionDecision.ASK


@dataclass
class PermissionRule:
    """A single permission rule (matching TypeScript patterns)."""

    pattern: str  # e.g., "Bash(ls *)", "Read", "Bash(rm *)"
    decision: PermissionDecision
    priority: int = 0  # Higher priority rules are checked first
    source: Optional[str] = None  # Where this rule came from (settings, project, etc.)

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
        # For file tools, match against file_path
        if "file_path" in input:
            path = input["file_path"]
            if subpattern.endswith("*"):
                return path.startswith(subpattern[:-1])
            return path == subpattern
        return False


@dataclass
class ToolPermissionRulesBySource:
    """Permission rules organized by source (matching TypeScript ToolPermissionRulesBySource)."""

    settings: Optional[Dict[str, List[str]]] = None  # From ~/.claude/settings.json
    project: Optional[Dict[str, List[str]]] = None  # From .claude/settings.json
    local: Optional[Dict[str, List[str]]] = None  # From .claude/settings.local.json
    policy: Optional[Dict[str, List[str]]] = None  # From managed policy

    def get_rules(self, source: str, decision_type: str) -> List[PermissionRule]:
        """Get rules for a specific source and decision type."""
        source_data = getattr(self, source, None)
        if source_data is None:
            return []
        patterns = source_data.get(decision_type, [])
        decision = PermissionDecision(decision_type.upper())
        return [PermissionRule(pattern=p, decision=decision, source=source) for p in patterns]


@dataclass
class AdditionalWorkingDirectory:
    """Additional working directory with trust status."""

    path: str
    is_trusted: bool = False
    added_at: Optional[float] = None


@dataclass
class ToolPermissionContext:
    """Tool permission context (matching TypeScript ToolPermissionContext).

    Contains:
    - Current permission mode
    - Additional working directories
    - Rules by source (alwaysAllow, alwaysDeny, alwaysAsk)
    - Feature flags for bypass/auto modes
    - Pre-plan mode state for restoration
    """

    mode: PermissionMode = PermissionMode.DEFAULT
    additional_working_directories: Dict[str, AdditionalWorkingDirectory] = field(default_factory=dict)
    always_allow_rules: Dict[str, List[str]] = field(default_factory=dict)
    always_deny_rules: Dict[str, List[str]] = field(default_factory=dict)
    always_ask_rules: Dict[str, List[str]] = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    is_auto_mode_available: bool = False
    stripped_dangerous_rules: Optional[Dict[str, List[str]]] = None
    should_avoid_permission_prompts: bool = False
    await_automated_checks_before_dialog: bool = False
    pre_plan_mode: Optional[PermissionMode] = None


def get_empty_tool_permission_context() -> ToolPermissionContext:
    """Get empty permission context (matching TypeScript getEmptyToolPermissionContext)."""
    return ToolPermissionContext(
        mode=PermissionMode.DEFAULT,
        additional_working_directories={},
        always_allow_rules={},
        always_deny_rules={},
        always_ask_rules={},
        is_bypass_permissions_mode_available=False,
    )


@dataclass
class PermissionConfig:
    """Permission configuration (matching TypeScript settings format)."""

    allow: List[str] = field(default_factory=list)
    deny: List[str] = field(default_factory=list)
    ask: List[str] = field(default_factory=list)

    def to_rules(self) -> List[PermissionRule]:
        """Convert config to sorted rules."""
        rules: List[PermissionRule] = []
        for pattern in self.deny:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.DENY, priority=100))
        for pattern in self.ask:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.ASK, priority=50))
        for pattern in self.allow:
            rules.append(PermissionRule(pattern=pattern, decision=PermissionDecision.ALLOW, priority=0))
        # Sort by priority (highest first)
        return sorted(rules, key=lambda r: -r.priority)


@dataclass
class DenialTrackingState:
    """Tracks permission denials for fallback logic (matching TypeScript DenialTrackingState)."""

    count: int = 0
    last_denial_time: Optional[float] = None
    denied_tools: Set[str] = field(default_factory=set)

    def record_denial(self, tool_name: str) -> None:
        """Record a denial."""
        self.count += 1
        self.last_denial_time = time.time() if 'time' in globals() else 0.0
        self.denied_tools.add(tool_name)


__all__ = [
    "PermissionDecision",
    "PermissionMode",
    "PermissionResult",
    "PermissionRule",
    "PermissionConfig",
    "ToolPermissionContext",
    "ToolPermissionRulesBySource",
    "AdditionalWorkingDirectory",
    "DenialTrackingState",
    "get_empty_tool_permission_context",
]
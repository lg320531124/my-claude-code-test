"""Permission manager."""

from __future__ import annotations
from ..types.permission import PermissionConfig, PermissionResult, PermissionDecision


class PermissionManager:
    """Manages tool execution permissions."""

    def __init__(self, config: Optional[PermissionConfig] = None):
        self.config = config or PermissionConfig()
        self.rules = self.config.to_rules()

    def check(self, tool_name: str, tool_input: dict) -> PermissionResult:
        """Check permission for a tool call."""
        for rule in self.rules:
            if rule.matches(tool_name, tool_input):
                return PermissionResult(
                    decision=rule.decision.value,
                    reason=f"Matched rule: {rule.pattern}",
                    rule=rule.pattern,
                )

        # Default: ask for confirmation
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="No matching rule",
        )

    def add_rule(self, pattern: str, decision: PermissionDecision) -> None:
        """Add a permission rule."""
        if decision == PermissionDecision.ALLOW:
            self.config.allow.append(pattern)
        elif decision == PermissionDecision.DENY:
            self.config.deny.append(pattern)
        elif decision == PermissionDecision.ASK:
            self.config.ask.append(pattern)

        self.rules = self.config.to_rules()

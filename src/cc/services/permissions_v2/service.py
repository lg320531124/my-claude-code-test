"""Permission Manager - Manage permissions."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class PermissionMode(Enum):
    """Permission modes."""
    ASK = "ask"
    AUTO_ALLOW = "auto_allow"
    AUTO_DENY = "auto_deny"
    SESSION = "session"


class PermissionDecision(Enum):
    """Permission decisions."""
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"
    SESSION_ALLOW = "session_allow"


@dataclass
class PermissionRule:
    """Permission rule."""
    pattern: str
    decision: PermissionDecision
    tool_type: Optional[str] = None
    description: str = ""
    created_at: float = 0.0


@dataclass
class PermissionRequest:
    """Permission request."""
    tool_name: str
    action: str
    context: Dict[str, Any] = field(default_factory=dict)
    risky: bool = False
    auto_allowed: bool = False


@dataclass
class PermissionConfig:
    """Permission configuration."""
    mode: PermissionMode = PermissionMode.ASK
    default_decision: PermissionDecision = PermissionDecision.ASK
    max_session_rules: int = 50
    persist_rules: bool = True


class PermissionManager:
    """Manage permissions."""

    # Auto-allowed patterns
    AUTO_ALLOWED_PATTERNS: List[str] = [
        "Bash(ls*)",
        "Bash(cat*)",
        "Bash(pwd)",
        "Bash(git status*)",
        "Bash(git log*)",
        "Bash(git diff*)",
        "Bash(git branch*)",
        "Read(*)",
        "Glob(*)",
        "Grep(*)",
    ]

    def __init__(self, config: Optional[PermissionConfig] = None):
        self.config = config or PermissionConfig()
        self._rules: List[PermissionRule] = []
        self._session_rules: Dict[str, PermissionDecision] = {}
        self._pending_requests: Dict[str, PermissionRequest] = {}
        self._callbacks: List[callable] = []

    async def check_permission(
        self,
        request: PermissionRequest
    ) -> PermissionDecision:
        """Check if action is permitted."""
        # Check auto-allowed
        if self._is_auto_allowed(request):
            request.auto_allowed = True
            return PermissionDecision.ALLOW

        pattern = f"{request.tool_name}({request.action})"

        # Check session rules first (use pattern matching)
        for session_pattern, decision in self._session_rules.items():
            if self._pattern_matches(pattern, session_pattern):
                return decision

        # Check persistent rules
        for rule in self._rules:
            if self._matches_pattern(request, rule):
                return rule.decision

        # Apply default mode
        return self._get_default_decision(request)

    def _is_auto_allowed(
        self,
        request: PermissionRequest
    ) -> bool:
        """Check if request is auto-allowed."""
        pattern = f"{request.tool_name}({request.action})"

        for auto_pattern in self.AUTO_ALLOWED_PATTERNS:
            if self._pattern_matches(pattern, auto_pattern):
                return True

        return False

    def _pattern_matches(
        self,
        pattern: str,
        rule_pattern: str
    ) -> bool:
        """Check if pattern matches rule.

        Supported formats:
        - Tool(*) - matches any action for that tool
        - Tool(prefix*) - matches actions starting with prefix
        - Tool(action) - exact match
        - prefix* - prefix match
        """
        # Check for Tool(...) format
        if "(" in rule_pattern and rule_pattern.endswith(")"):
            # Extract tool and action pattern
            tool_part, action_part = rule_pattern.split("(", 1)
            action_pattern = action_part[:-1]  # Remove trailing )

            # Pattern must match tool
            if not pattern.startswith(tool_part + "("):
                return False

            # Extract action from pattern
            pattern_parts = pattern.split("(", 1)
            pattern_action = pattern_parts[1].rstrip(")")

            # Check action match
            if action_pattern == "*":
                return True  # Match any action
            elif action_pattern.endswith("*"):
                action_prefix = action_pattern[:-1]
                return pattern_action.startswith(action_prefix)
            else:
                return pattern_action == action_pattern

        # Handle simple prefix* format
        if rule_pattern.endswith("*"):
            prefix = rule_pattern[:-1]
            return pattern.startswith(prefix)

        # Exact match
        return pattern == rule_pattern

    def _matches_pattern(
        self,
        request: PermissionRequest,
        rule: PermissionRule
    ) -> bool:
        """Check if request matches rule."""
        # Tool type check
        if rule.tool_type and request.tool_name != rule.tool_type:
            return False

        pattern = f"{request.tool_name}({request.action})"
        return self._pattern_matches(pattern, rule.pattern)

    def _get_default_decision(
        self,
        request: PermissionRequest
    ) -> PermissionDecision:
        """Get default decision based on mode."""
        if self.config.mode == PermissionMode.AUTO_ALLOW:
            return PermissionDecision.ALLOW
        elif self.config.mode == PermissionMode.AUTO_DENY:
            return PermissionDecision.DENY
        else:
            return PermissionDecision.ASK

    async def add_rule(
        self,
        pattern: str,
        decision: PermissionDecision,
        tool_type: Optional[str] = None,
        description: str = ""
    ) -> PermissionRule:
        """Add permission rule."""
        rule = PermissionRule(
            pattern=pattern,
            decision=decision,
            tool_type=tool_type,
            description=description,
            created_at=asyncio.get_event_loop().time(),
        )

        self._rules.append(rule)

        logger.info(f"Added rule: {pattern} -> {decision.value}")
        return rule

    async def add_session_rule(
        self,
        pattern: str,
        decision: PermissionDecision
    ) -> bool:
        """Add session-specific rule."""
        if len(self._session_rules) >= self.config.max_session_rules:
            return False

        self._session_rules[pattern] = decision
        return True

    async def request_permission(
        self,
        request: PermissionRequest
    ) -> str:
        """Request permission from user."""
        request_id = f"{request.tool_name}_{asyncio.get_event_loop().time()}"
        self._pending_requests[request_id] = request

        # Call callbacks to prompt user
        await self._call_callbacks(request)

        return request_id

    async def respond_to_request(
        self,
        request_id: str,
        decision: PermissionDecision
    ) -> bool:
        """Respond to pending request."""
        if request_id not in self._pending_requests:
            return False

        request = self._pending_requests[request_id]

        # Add session rule if requested
        if decision == PermissionDecision.SESSION_ALLOW:
            pattern = f"{request.tool_name}({request.action})"
            await self.add_session_rule(pattern, PermissionDecision.ALLOW)

        del self._pending_requests[request_id]
        return True

    async def _call_callbacks(
        self,
        request: PermissionRequest
    ) -> None:
        """Call registered callbacks."""
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(request)
                else:
                    callback(request)
            except Exception as e:
                logger.error(f"Callback error: {e}")

    async def get_rules(self) -> List[PermissionRule]:
        """Get all rules."""
        return self._rules.copy()

    async def get_session_rules(self) -> Dict[str, PermissionDecision]:
        """Get session rules."""
        return self._session_rules.copy()

    async def clear_session_rules(self) -> int:
        """Clear session rules."""
        count = len(self._session_rules)
        self._session_rules.clear()
        return count

    async def remove_rule(
        self,
        pattern: str
    ) -> bool:
        """Remove rule by pattern."""
        for i, rule in enumerate(self._rules):
            if rule.pattern == pattern:
                self._rules.pop(i)
                return True

        return False

    def register_callback(
        self,
        callback: callable
    ) -> None:
        """Register permission request callback."""
        self._callbacks.append(callback)

    async def set_mode(
        self,
        mode: PermissionMode
    ) -> None:
        """Set permission mode."""
        self.config.mode = mode
        logger.info(f"Permission mode set to {mode.value}")

    async def is_allowed(
        self,
        tool_name: str,
        action: str
    ) -> bool:
        """Check if action is allowed."""
        request = PermissionRequest(
            tool_name=tool_name,
            action=action,
        )

        decision = await self.check_permission(request)
        return decision in [PermissionDecision.ALLOW, PermissionDecision.SESSION_ALLOW]


__all__ = [
    "PermissionMode",
    "PermissionDecision",
    "PermissionRule",
    "PermissionRequest",
    "PermissionConfig",
    "PermissionManager",
]
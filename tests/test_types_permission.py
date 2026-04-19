"""Tests for permission types."""

from __future__ import annotations
import pytest

from cc.types.permission import (
    PermissionDecision,
    PermissionMode,
    PermissionResult,
    PermissionRule,
    PermissionConfig,
)


def test_permission_decision_values():
    """Test PermissionDecision enum values."""
    assert PermissionDecision.ALLOW.value == "allow"
    assert PermissionDecision.DENY.value == "deny"
    assert PermissionDecision.ASK.value == "ask"


def test_permission_mode_values():
    """Test PermissionMode enum values."""
    assert PermissionMode.DEFAULT.value == "default"
    assert PermissionMode.PLAN.value == "plan"
    assert PermissionMode.BYPASS.value == "bypassPermissions"
    assert PermissionMode.AUTO.value == "auto"


def test_permission_rule_creation():
    """Test PermissionRule creation."""
    rule = PermissionRule(pattern="Bash(ls *)", decision=PermissionDecision.ALLOW)
    assert rule.pattern == "Bash(ls *)"
    assert rule.decision == PermissionDecision.ALLOW


def test_permission_rule_matches_simple():
    """Test PermissionRule simple matching."""
    rule = PermissionRule(pattern="Bash", decision=PermissionDecision.ALLOW)
    assert rule.matches("Bash", {})
    assert not rule.matches("Read", {})


def test_permission_rule_matches_wildcard():
    """Test PermissionRule wildcard matching."""
    rule = PermissionRule(pattern="*", decision=PermissionDecision.ALLOW)
    assert rule.matches("Bash", {})
    assert rule.matches("Read", {})
    assert rule.matches("Write", {})


def test_permission_rule_matches_with_subpattern():
    """Test PermissionRule with subpattern."""
    rule = PermissionRule(pattern="Bash(ls *)", decision=PermissionDecision.ALLOW)
    assert rule.matches("Bash", {"command": "ls -la"})
    assert not rule.matches("Bash", {"command": "rm file"})


def test_permission_config():
    """Test PermissionConfig creation."""
    config = PermissionConfig(
        allow=["Bash", "Read"],
        deny=["Bash(rm *)"],
        ask=["Write"],
    )
    assert config.allow == ["Bash", "Read"]
    assert config.deny == ["Bash(rm *)"]
    assert config.ask == ["Write"]


def test_permission_config_to_rules():
    """Test PermissionConfig.to_rules."""
    config = PermissionConfig(
        deny=["Bash(rm *)"],
        ask=["Write"],
        allow=["Bash", "Read"],
    )
    rules = config.to_rules()
    assert len(rules) == 4  # 1 deny + 1 ask + 2 allow

    # Check order (deny first, then ask, then allow)
    assert rules[0].decision == PermissionDecision.DENY
    assert rules[1].decision == PermissionDecision.ASK
    assert rules[2].decision == PermissionDecision.ALLOW


def test_permission_result_properties():
    """Test PermissionResult properties."""
    allow_result = PermissionResult(decision="allow")
    deny_result = PermissionResult(decision="deny")
    ask_result = PermissionResult(decision="ask")

    assert allow_result.is_allowed
    assert not allow_result.is_denied
    assert not allow_result.needs_confirmation

    assert not deny_result.is_allowed
    assert deny_result.is_denied
    assert not deny_result.needs_confirmation

    assert not ask_result.is_allowed
    assert not ask_result.is_denied
    assert ask_result.needs_confirmation
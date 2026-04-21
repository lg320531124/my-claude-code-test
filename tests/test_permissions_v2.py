"""Tests for permission manager."""

import pytest
from src.cc.services.permissions_v2 import (
    PermissionManager,
    PermissionConfig,
    PermissionMode,
    PermissionDecision,
    PermissionRule,
    PermissionRequest,
)


@pytest.mark.asyncio
async def test_permission_manager_init():
    """Test permission manager initialization."""
    manager = PermissionManager()
    assert manager.config is not None


@pytest.mark.asyncio
async def test_check_permission_auto_allowed():
    """Test auto-allowed permission."""
    manager = PermissionManager()

    request = PermissionRequest(
        tool_name="Read",
        action="file.py",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.ALLOW
    assert request.auto_allowed is True


@pytest.mark.asyncio
async def test_check_permission_ask():
    """Test permission asking."""
    manager = PermissionManager()

    request = PermissionRequest(
        tool_name="Bash",
        action="rm file",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.ASK


@pytest.mark.asyncio
async def test_add_rule():
    """Test adding rule."""
    manager = PermissionManager()

    rule = await manager.add_rule(
        "Bash(ls*)",
        PermissionDecision.ALLOW,
        description="Allow ls"
    )

    assert rule.pattern == "Bash(ls*)"
    assert len(await manager.get_rules()) == 1


@pytest.mark.asyncio
async def test_rule_applied():
    """Test rule being applied."""
    manager = PermissionManager()

    await manager.add_rule(
        "Bash(custom*)",
        PermissionDecision.DENY
    )

    request = PermissionRequest(
        tool_name="Bash",
        action="custom action",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.DENY


@pytest.mark.asyncio
async def test_session_rule():
    """Test session rule."""
    manager = PermissionManager()

    await manager.add_session_rule(
        "Bash(test*)",
        PermissionDecision.ALLOW
    )

    request = PermissionRequest(
        tool_name="Bash",
        action="test",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.ALLOW


@pytest.mark.asyncio
async def test_clear_session_rules():
    """Test clearing session rules."""
    manager = PermissionManager()

    await manager.add_session_rule("Test*", PermissionDecision.ALLOW)
    count = await manager.clear_session_rules()

    assert count == 1


@pytest.mark.asyncio
async def test_remove_rule():
    """Test removing rule."""
    manager = PermissionManager()

    await manager.add_rule("Test*", PermissionDecision.ALLOW)
    result = await manager.remove_rule("Test*")

    assert result is True
    assert len(await manager.get_rules()) == 0


@pytest.mark.asyncio
async def test_set_mode():
    """Test setting mode."""
    manager = PermissionManager()

    await manager.set_mode(PermissionMode.AUTO_ALLOW)
    assert manager.config.mode == PermissionMode.AUTO_ALLOW


@pytest.mark.asyncio
async def test_auto_allow_mode():
    """Test auto allow mode."""
    config = PermissionConfig(mode=PermissionMode.AUTO_ALLOW)
    manager = PermissionManager(config)

    request = PermissionRequest(
        tool_name="CustomTool",
        action="unknown",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.ALLOW


@pytest.mark.asyncio
async def test_auto_deny_mode():
    """Test auto deny mode."""
    config = PermissionConfig(mode=PermissionMode.AUTO_DENY)
    manager = PermissionManager(config)

    request = PermissionRequest(
        tool_name="CustomTool",
        action="unknown",
    )

    decision = await manager.check_permission(request)
    assert decision == PermissionDecision.DENY


@pytest.mark.asyncio
async def test_is_allowed():
    """Test is_allowed method."""
    manager = PermissionManager()

    result = await manager.is_allowed("Read", "file.py")
    assert result is True


@pytest.mark.asyncio
async def test_permission_mode_enum():
    """Test permission mode enum."""
    assert PermissionMode.ASK.value == "ask"
    assert PermissionMode.AUTO_ALLOW.value == "auto_allow"


@pytest.mark.asyncio
async def test_permission_decision_enum():
    """Test permission decision enum."""
    assert PermissionDecision.ALLOW.value == "allow"
    assert PermissionDecision.DENY.value == "deny"


@pytest.mark.asyncio
async def test_permission_request():
    """Test permission request."""
    request = PermissionRequest(
        tool_name="Bash",
        action="ls",
        risky=True,
    )

    assert request.tool_name == "Bash"
    assert request.risky is True


@pytest.mark.asyncio
async def test_register_callback():
    """Test registering callback."""
    manager = PermissionManager()

    callbacks = []

    def callback(r):
        callbacks.append(r)

    manager.register_callback(callback)

    request = PermissionRequest(tool_name="Test", action="test")
    await manager.request_permission(request)

    assert len(callbacks) == 1
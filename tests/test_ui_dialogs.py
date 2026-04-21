"""Tests for UI dialogs (non-textual parts)."""

import pytest

# Test enums and dataclasses that don't depend on textual
from src.cc.ui.dialogs.confirm import ConfirmAction, ConfirmResult
from src.cc.ui.dialogs.error import ErrorType, ErrorInfo
from src.cc.ui.dialogs.help_dialog import HelpCategory, HelpDialogConfig


def test_confirm_action():
    """Test confirm action enum."""
    assert ConfirmAction.YES.value == "yes"
    assert ConfirmAction.NO.value == "no"


def test_confirm_result():
    """Test confirm result."""
    result = ConfirmResult(action=ConfirmAction.YES)
    assert result.action == ConfirmAction.YES


def test_error_type():
    """Test error type enum."""
    assert ErrorType.API_ERROR.value == "api_error"
    assert ErrorType.TOOL_ERROR.value == "tool_error"


def test_error_info():
    """Test error info."""
    info = ErrorInfo(type=ErrorType.API_ERROR, message="API error")
    assert info.type == ErrorType.API_ERROR
    assert info.message == "API error"


def test_help_category():
    """Test help category enum."""
    assert HelpCategory.COMMANDS.value == "commands"
    assert HelpCategory.TOOLS.value == "tools"


def test_help_dialog_config():
    """Test help dialog config."""
    config = HelpDialogConfig()
    assert config is not None
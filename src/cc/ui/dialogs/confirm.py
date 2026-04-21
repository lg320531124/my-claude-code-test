"""Confirm Dialog - Confirmation dialogs."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Any
from enum import Enum


class ConfirmAction(Enum):
    """Confirm action types."""
    YES = "yes"
    NO = "no"
    CANCEL = "cancel"
    OK = "ok"
    CONTINUE = "continue"
    ABORT = "abort"


@dataclass
class ConfirmResult:
    """Result of confirmation."""
    action: ConfirmAction
    confirmed: bool = False
    data: Any = None


@dataclass
class ConfirmDialog:
    """Confirmation dialog."""
    
    title: str = "Confirm"
    message: str = ""
    detail: Optional[str] = None
    default_action: ConfirmAction = ConfirmAction.NO
    actions: list = None  # List of ConfirmAction
    
    def __post_init__(self):
        if self.actions is None:
            self.actions = [ConfirmAction.YES, ConfirmAction.NO]
    
    def get_buttons(self) -> list:
        """Get button labels."""
        return [a.value.upper() for a in self.actions]
    
    def is_confirmed(self, action: ConfirmAction) -> bool:
        """Check if action is confirmation."""
        return action in [ConfirmAction.YES, ConfirmAction.OK, ConfirmAction.CONTINUE]


class ConfirmManager:
    """Manager for confirmation dialogs."""
    
    def __init__(self):
        self._pending: dict = {}
        self._callbacks: dict = {}
    
    async def ask(
        self,
        message: str,
        title: str = "Confirm",
        detail: Optional[str] = None,
        default: ConfirmAction = ConfirmAction.NO,
    ) -> ConfirmResult:
        """Ask for confirmation (async)."""
        # In real implementation, would render dialog and wait for input
        # For now, return default action
        return ConfirmResult(
            action=default,
            confirmed=self._is_confirmed(default),
        )
    
    def ask_sync(
        self,
        message: str,
        title: str = "Confirm",
        default: ConfirmAction = ConfirmAction.NO,
    ) -> ConfirmResult:
        """Ask for confirmation (sync)."""
        return ConfirmResult(
            action=default,
            confirmed=self._is_confirmed(default),
        )
    
    def _is_confirmed(self, action: ConfirmAction) -> bool:
        """Check if action is confirmation."""
        return action in [ConfirmAction.YES, ConfirmAction.OK, ConfirmAction.CONTINUE]


# Global confirm manager
_confirm_manager: Optional[ConfirmManager] = None


def get_confirm_manager() -> ConfirmManager:
    """Get global confirm manager."""
    global _confirm_manager
    if _confirm_manager is None:
        _confirm_manager = ConfirmManager()
    return _confirm_manager


def confirm(message: str, title: str = "Confirm") -> bool:
    """Simple confirmation."""
    result = get_confirm_manager().ask_sync(message, title)
    return result.confirmed


__all__ = [
    "ConfirmAction",
    "ConfirmResult",
    "ConfirmDialog",
    "ConfirmManager",
    "get_confirm_manager",
    "confirm",
]

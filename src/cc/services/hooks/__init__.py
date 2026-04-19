"""Hooks package."""

from __future__ import annotations
from .hooks_system import (
    Hook,
    HookType,
    HookContext,
    HookResult,
    HookRegistry,
    HookManager,
    get_hook_manager,
    register_hook,
    trigger_hook,
    create_logging_hook,
    create_timing_hook,
    create_validation_hook,
)

__all__ = [
    "Hook",
    "HookType",
    "HookContext",
    "HookResult",
    "HookRegistry",
    "HookManager",
    "get_hook_manager",
    "register_hook",
    "trigger_hook",
    "create_logging_hook",
    "create_timing_hook",
    "create_validation_hook",
]

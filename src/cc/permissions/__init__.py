"""Permissions module."""

from __future__ import annotations
from .manager import PermissionManager
from .rules import get_default_rules, matches_pattern
from .prompts import PermissionPrompter, EnhancedPermissionPrompter, show_saved_permissions, clear_permissions
from .hooks import PermissionHook, create_permission_hook
from .persistence import PermissionPersistence, SessionMemory

# Alias for compatibility
show_permission_rules = show_saved_permissions

__all__ = [
    "PermissionManager",
    "get_default_rules",
    "matches_pattern",
    "PermissionPrompter",
    "EnhancedPermissionPrompter",
    "show_permission_rules",
    "show_saved_permissions",
    "clear_permissions",
    "PermissionHook",
    "create_permission_hook",
    "PermissionPersistence",
    "SessionMemory",
]

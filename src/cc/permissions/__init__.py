"""Permissions module."""

from .manager import PermissionManager
from .rules import get_default_rules, matches_pattern
from .prompts import PermissionPrompter, show_permission_rules
from .hooks import PermissionHook, create_permission_hook

__all__ = [
    "PermissionManager",
    "get_default_rules",
    "matches_pattern",
    "PermissionPrompter",
    "show_permission_rules",
    "PermissionHook",
    "create_permission_hook",
]
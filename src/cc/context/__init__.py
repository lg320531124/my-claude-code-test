"""Context module."""

from .collector import ContextCollector
from .git import get_git_context, get_git_diff, get_staged_files
from .system import SYSTEM_PROMPT, build_system_prompt
from .prompts import get_system_prompt, build_dynamic_prompt, PLANNING_PROMPT

__all__ = [
    "ContextCollector",
    "get_git_context",
    "get_git_diff",
    "get_staged_files",
    "SYSTEM_PROMPT",
    "build_system_prompt",
    "get_system_prompt",
    "build_dynamic_prompt",
    "PLANNING_PROMPT",
]
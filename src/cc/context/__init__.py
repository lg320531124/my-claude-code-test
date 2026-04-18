"""Context module - Context collection and system prompts."""

from .collector import ContextCollector
from .git import get_git_context, get_git_diff, get_staged_files
from .system import SYSTEM_PROMPT, build_system_prompt

__all__ = [
    "ContextCollector",
    "get_git_context",
    "get_git_diff",
    "get_staged_files",
    "SYSTEM_PROMPT",
    "build_system_prompt",
]
"""Context module."""

from __future__ import annotations
from .collector import ContextCollector
from .git import get_git_context, get_git_diff, get_staged_files
from .system import SYSTEM_PROMPT, build_system_prompt
from .prompts import get_system_prompt, build_dynamic_prompt, PLANNING_PROMPT
from .watcher import (
    FileWatcher,
    FileEvent,
    FileEventType,
    ContextUpdater,
    ProjectStructure,
    get_file_watcher,
    start_file_watching,
    stop_file_watching,
)
from .full_context import (
    AsyncContextCollector,
    EnvironmentInfo,
    GitInfo,
    ProjectInfo,
    ContextInfo,
    build_system_prompt_from_context,
    get_full_context,
    get_context_sync,
)

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
    # Watcher
    "FileWatcher",
    "FileEvent",
    "FileEventType",
    "ContextUpdater",
    "ProjectStructure",
    "get_file_watcher",
    "start_file_watching",
    "stop_file_watching",
    # Full Context
    "AsyncContextCollector",
    "EnvironmentInfo",
    "GitInfo",
    "ProjectInfo",
    "ContextInfo",
    "build_system_prompt_from_context",
    "get_full_context",
    "get_context_sync",
]

"""Bootstrap Module - Session state and initialization.

Provides global state management for Claude Code sessions.
"""

from __future__ import annotations

from .state import (
    SessionId,
    get_session_id,
    regenerate_session_id,
    get_parent_session_id,
    switch_session,
    get_session_project_dir,
    get_original_cwd,
    get_project_root,
    set_original_cwd,
    set_project_root,
    get_cwd_state,
    set_cwd_state,
    get_total_cost_usd,
    set_total_cost_usd,
    get_total_api_duration,
    get_total_duration,
    add_to_total_cost_state,
    get_is_interactive,
    set_is_interactive,
    get_is_non_interactive_session,
    get_client_type,
    set_client_type,
    get_session_source,
    set_session_source,
    get_start_time,
    reset_state_for_tests,
    SessionState,
    get_state,
)
from .setup import (
    SetupConfig,
    WorktreeSession,
    setup,
    check_python_version,
    is_bare_mode,
    is_env_truthy,
    create_worktree_for_session,
    generate_tmux_session_name,
    create_tmux_session_for_worktree,
    init_session_memory,
    init_background_jobs,
    prefetch_api_key,
    check_for_release_notes,
    get_global_config,
    get_current_project_config,
    log_event,
)

__all__ = [
    # Session ID
    "SessionId",
    "get_session_id",
    "regenerate_session_id",
    "get_parent_session_id",
    "switch_session",
    "get_session_project_dir",
    # CWD
    "get_original_cwd",
    "get_project_root",
    "set_original_cwd",
    "set_project_root",
    "get_cwd_state",
    "set_cwd_state",
    # Cost/Duration
    "get_total_cost_usd",
    "set_total_cost_usd",
    "get_total_api_duration",
    "get_total_duration",
    "add_to_total_cost_state",
    # Interactive
    "get_is_interactive",
    "set_is_interactive",
    "get_is_non_interactive_session",
    # Client
    "get_client_type",
    "set_client_type",
    # Session
    "get_session_source",
    "set_session_source",
    "get_start_time",
    # Testing
    "reset_state_for_tests",
    # State class
    "SessionState",
    "get_state",
    # Setup
    "SetupConfig",
    "WorktreeSession",
    "setup",
    "check_python_version",
    "is_bare_mode",
    "is_env_truthy",
    "create_worktree_for_session",
    "generate_tmux_session_name",
    "create_tmux_session_for_worktree",
    "init_session_memory",
    "init_background_jobs",
    "prefetch_api_key",
    "check_for_release_notes",
    "get_global_config",
    "get_current_project_config",
    "log_event",
]
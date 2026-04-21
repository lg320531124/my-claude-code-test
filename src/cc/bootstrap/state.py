"""Session State Management - Global state for Claude Code sessions.

Provides singleton state management with getter/setter accessors.
"""

from __future__ import annotations

import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Set, List, Callable


# Type alias for session IDs
SessionId = str


@dataclass
class ModelUsage:
    """Model usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    web_search_requests: int = 0


@dataclass
class SessionCronTask:
    """Session-only cron task (not persisted to disk)."""
    id: str
    cron: str
    prompt: str
    created_at: float
    recurring: bool = False
    agent_id: Optional[str] = None


@dataclass
class InvokedSkillInfo:
    """Info about an invoked skill."""
    skill_name: str
    skill_path: str
    content: str
    invoked_at: float
    agent_id: Optional[str] = None


@dataclass
class SlowOperation:
    """Slow operation tracking."""
    operation: str
    duration_ms: float
    timestamp: float


@dataclass
class TeleportedSessionInfo:
    """Teleported session tracking."""
    is_teleported: bool
    has_logged_first_message: bool
    session_id: Optional[str]


@dataclass
class SessionState:
    """Global session state.

    DO NOT ADD MORE STATE HERE - BE JUDICIOUS WITH GLOBAL STATE.
    """

    # CWD and project
    original_cwd: str = ""
    project_root: str = ""
    cwd: str = ""

    # Cost and duration
    total_cost_usd: float = 0.0
    total_api_duration: float = 0.0
    total_api_duration_without_retries: float = 0.0
    total_tool_duration: float = 0.0
    start_time: float = field(default_factory=time.time)
    last_interaction_time: float = field(default_factory=time.time)

    # Lines changed
    total_lines_added: int = 0
    total_lines_removed: int = 0

    # Model
    model_usage: Dict[str, ModelUsage] = field(default_factory=dict)
    has_unknown_model_cost: bool = False

    # Session
    session_id: SessionId = field(default_factory=lambda: str(uuid.uuid4()))
    parent_session_id: Optional[SessionId] = None
    session_project_dir: Optional[str] = None

    # Interactive
    is_interactive: bool = False
    kairos_active: bool = False
    strict_tool_result_pairing: bool = False
    sdk_agent_progress_summaries_enabled: bool = False
    user_msg_opt_in: bool = False

    # Client
    client_type: str = "cli"
    session_source: Optional[str] = None
    question_preview_format: Optional[str] = None

    # Tokens and auth
    session_ingress_token: Optional[str] = None
    oauth_token_from_fd: Optional[str] = None
    api_key_from_fd: Optional[str] = None

    # Settings
    flag_settings_path: Optional[str] = None
    flag_settings_inline: Optional[Dict[str, Any]] = None
    allowed_setting_sources: List[str] = field(
        default_factory=lambda: [
            "userSettings",
            "projectSettings",
            "localSettings",
            "flagSettings",
            "policySettings",
        ]
    )

    # Chrome
    chrome_flag_override: Optional[bool] = None
    use_cowork_plugins: bool = False

    # Permissions
    session_bypass_permissions_mode: bool = False
    session_trust_accepted: bool = False
    session_persistence_disabled: bool = False

    # Scheduled tasks
    scheduled_tasks_enabled: bool = False
    session_cron_tasks: List[SessionCronTask] = field(default_factory=list)

    # Teams
    session_created_teams: Set[str] = field(default_factory=set)

    # Plan mode
    has_exited_plan_mode: bool = False
    needs_plan_mode_exit_attachment: bool = False
    needs_auto_mode_exit_attachment: bool = False

    # LSP
    lsp_recommendation_shown_this_session: bool = False

    # SDK
    init_json_schema: Optional[Dict[str, Any]] = None
    registered_hooks: Optional[Dict[str, List[Any]]] = None
    sdk_betas: Optional[List[str]] = None
    main_thread_agent_type: Optional[str] = None

    # Remote
    is_remote_mode: bool = False
    direct_connect_server_url: Optional[str] = None

    # Caches
    plan_slug_cache: Dict[str, str] = field(default_factory=dict)
    system_prompt_section_cache: Dict[str, Optional[str]] = field(default_factory=dict)
    invoked_skills: Dict[str, InvokedSkillInfo] = field(default_factory=dict)

    # Errors
    in_memory_error_log: List[Dict[str, str]] = field(default_factory=list)

    # Slow operations
    slow_operations: List[SlowOperation] = field(default_factory=list)

    # Teleported session
    teleported_session_info: Optional[TeleportedSessionInfo] = None

    # Plugins
    inline_plugins: List[str] = field(default_factory=list)

    # Channels
    allowed_channels: List[Any] = field(default_factory=list)
    has_dev_channels: bool = False

    # Claude.md
    cached_claude_md_content: Optional[str] = None
    additional_directories_for_claude_md: List[str] = field(default_factory=list)

    # Prompt cache
    prompt_cache_1h_allowlist: Optional[List[str]] = None
    prompt_cache_1h_eligible: Optional[bool] = None

    # Beta header latches
    afk_mode_header_latched: Optional[bool] = None
    fast_mode_header_latched: Optional[bool] = None
    cache_editing_header_latched: Optional[bool] = None
    thinking_clear_latched: Optional[bool] = None

    # Prompt tracking
    prompt_id: Optional[str] = None
    last_main_request_id: Optional[str] = None
    last_api_completion_timestamp: Optional[float] = None
    pending_post_compaction: bool = False

    # Last emitted date
    last_emitted_date: Optional[str] = None

    # Turn duration tracking
    turn_hook_duration_ms: float = 0.0
    turn_tool_duration_ms: float = 0.0
    turn_classifier_duration_ms: float = 0.0
    turn_tool_count: int = 0
    turn_hook_count: int = 0
    turn_classifier_count: int = 0


# Global state singleton
_STATE: Optional[SessionState] = None

# Session switch callbacks
_session_switch_callbacks: List[Callable[[SessionId], None]] = []


def _get_initial_state() -> SessionState:
    """Get initial state with resolved cwd."""
    cwd = os.getcwd()
    return SessionState(
        original_cwd=cwd,
        project_root=cwd,
        cwd=cwd,
    )


def get_state() -> SessionState:
    """Get the global session state."""
    global _STATE
    if _STATE is None:
        _STATE = _get_initial_state()
    return _STATE


def reset_state_for_tests() -> None:
    """Reset state for tests only."""
    global _STATE
    if os.environ.get("NODE_ENV") != "test" and os.environ.get("PYTEST_CURRENT_TEST") is None:
        raise RuntimeError("reset_state_for_tests can only be called in tests")
    _STATE = _get_initial_state()
    _session_switch_callbacks.clear()


# Session ID functions
def get_session_id() -> SessionId:
    """Get current session ID."""
    return get_state().session_id


def regenerate_session_id(options: Optional[Dict[str, Any]] = None) -> SessionId:
    """Regenerate session ID."""
    state = get_state()
    if options and options.get("setCurrentAsParent"):
        state.parent_session_id = state.session_id
    # Clear plan slug cache entry
    state.plan_slug_cache.pop(state.session_id, None)
    state.session_id = str(uuid.uuid4())
    state.session_project_dir = None
    return state.session_id


def get_parent_session_id() -> Optional[SessionId]:
    """Get parent session ID."""
    return get_state().parent_session_id


def switch_session(session_id: SessionId, project_dir: Optional[str] = None) -> None:
    """Switch to a different session."""
    state = get_state()
    state.plan_slug_cache.pop(state.session_id, None)
    state.session_id = session_id
    state.session_project_dir = project_dir
    for callback in _session_switch_callbacks:
        callback(session_id)


def on_session_switch(callback: Callable[[SessionId], None]) -> None:
    """Register callback for session switches."""
    _session_switch_callbacks.append(callback)


def get_session_project_dir() -> Optional[str]:
    """Get session project directory."""
    return get_state().session_project_dir


# CWD functions
def get_original_cwd() -> str:
    """Get original working directory."""
    return get_state().original_cwd


def get_project_root() -> str:
    """Get stable project root directory."""
    return get_state().project_root


def set_original_cwd(cwd: str) -> None:
    """Set original working directory."""
    get_state().original_cwd = cwd


def set_project_root(cwd: str) -> None:
    """Set project root (only for --worktree startup)."""
    get_state().project_root = cwd


def get_cwd_state() -> str:
    """Get current working directory state."""
    return get_state().cwd


def set_cwd_state(cwd: str) -> None:
    """Set current working directory state."""
    get_state().cwd = cwd


# Cost/Duration functions
def get_total_cost_usd() -> float:
    """Get total cost in USD."""
    return get_state().total_cost_usd


def set_total_cost_usd(cost: float) -> None:
    """Set total cost."""
    get_state().total_cost_usd = cost


def get_total_api_duration() -> float:
    """Get total API duration."""
    return get_state().total_api_duration


def get_total_api_duration_without_retries() -> float:
    """Get total API duration without retries."""
    return get_state().total_api_duration_without_retries


def get_total_duration() -> float:
    """Get total session duration."""
    return time.time() - get_state().start_time


def add_to_total_cost_state(
    cost: float,
    model_usage: ModelUsage,
    model: str,
) -> None:
    """Add to total cost state."""
    state = get_state()
    state.model_usage[model] = model_usage
    state.total_cost_usd += cost


def add_to_total_duration_state(
    duration: float,
    duration_without_retries: float,
) -> None:
    """Add to total duration state."""
    state = get_state()
    state.total_api_duration += duration
    state.total_api_duration_without_retries += duration_without_retries


def get_start_time() -> float:
    """Get session start time."""
    return get_state().start_time


# Interactive functions
def get_is_interactive() -> bool:
    """Get if session is interactive."""
    return get_state().is_interactive


def set_is_interactive(value: bool) -> None:
    """Set interactive mode."""
    get_state().is_interactive = value


def get_is_non_interactive_session() -> bool:
    """Get if session is non-interactive."""
    return not get_state().is_interactive


# Client functions
def get_client_type() -> str:
    """Get client type."""
    return get_state().client_type


def set_client_type(client_type: str) -> None:
    """Set client type."""
    get_state().client_type = client_type


# Session source
def get_session_source() -> Optional[str]:
    """Get session source."""
    return get_state().session_source


def set_session_source(source: str) -> None:
    """Set session source."""
    get_state().session_source = source


# Lines changed
def get_total_lines_added() -> int:
    """Get total lines added."""
    return get_state().total_lines_added


def get_total_lines_removed() -> int:
    """Get total lines removed."""
    return get_state().total_lines_removed


def add_to_total_lines_changed(added: int, removed: int) -> None:
    """Add to total lines changed."""
    state = get_state()
    state.total_lines_added += added
    state.total_lines_removed += removed


# Tool duration
def get_total_tool_duration() -> float:
    """Get total tool duration."""
    return get_state().total_tool_duration


def add_to_tool_duration(duration: float) -> None:
    """Add to tool duration."""
    state = get_state()
    state.total_tool_duration += duration
    state.turn_tool_duration_ms += duration
    state.turn_tool_count += 1


# Interaction time
def get_last_interaction_time() -> float:
    """Get last interaction time."""
    return get_state().last_interaction_time


def update_last_interaction_time(immediate: bool = False) -> None:
    """Update last interaction time."""
    get_state().last_interaction_time = time.time()


# Direct connect
def get_direct_connect_server_url() -> Optional[str]:
    """Get direct connect server URL."""
    return get_state().direct_connect_server_url


def set_direct_connect_server_url(url: str) -> None:
    """Set direct connect server URL."""
    get_state().direct_connect_server_url = url


# Remote mode
def get_is_remote_mode() -> bool:
    """Get if remote mode."""
    return get_state().is_remote_mode


def set_is_remote_mode(value: bool) -> None:
    """Set remote mode."""
    get_state().is_remote_mode = value


# Cron tasks
def get_session_cron_tasks() -> List[SessionCronTask]:
    """Get session cron tasks."""
    return get_state().session_cron_tasks


def add_session_cron_task(task: SessionCronTask) -> None:
    """Add session cron task."""
    get_state().session_cron_tasks.append(task)


def remove_session_cron_tasks(ids: List[str]) -> int:
    """Remove session cron tasks by IDs."""
    if not ids:
        return 0
    state = get_state()
    id_set = set(ids)
    remaining = [t for t in state.session_cron_tasks if t.id not in id_set]
    removed = len(state.session_cron_tasks) - len(remaining)
    if removed > 0:
        state.session_cron_tasks = remaining
    return removed


# Scheduled tasks enabled
def get_scheduled_tasks_enabled() -> bool:
    """Get scheduled tasks enabled."""
    return get_state().scheduled_tasks_enabled


def set_scheduled_tasks_enabled(enabled: bool) -> None:
    """Set scheduled tasks enabled."""
    get_state().scheduled_tasks_enabled = enabled


# Bypass permissions
def get_session_bypass_permissions_mode() -> bool:
    """Get session bypass permissions mode."""
    return get_state().session_bypass_permissions_mode


def set_session_bypass_permissions_mode(enabled: bool) -> None:
    """Set session bypass permission mode."""
    get_state().session_bypass_permissions_mode = enabled


__all__ = [
    "SessionId",
    "ModelUsage",
    "SessionCronTask",
    "InvokedSkillInfo",
    "SlowOperation",
    "TeleportedSessionInfo",
    "SessionState",
    "get_state",
    "reset_state_for_tests",
    "get_session_id",
    "regenerate_session_id",
    "get_parent_session_id",
    "switch_session",
    "on_session_switch",
    "get_session_project_dir",
    "get_original_cwd",
    "get_project_root",
    "set_original_cwd",
    "set_project_root",
    "get_cwd_state",
    "set_cwd_state",
    "get_total_cost_usd",
    "set_total_cost_usd",
    "get_total_api_duration",
    "get_total_api_duration_without_retries",
    "get_total_duration",
    "add_to_total_cost_state",
    "add_to_total_duration_state",
    "get_start_time",
    "get_is_interactive",
    "set_is_interactive",
    "get_is_non_interactive_session",
    "get_client_type",
    "set_client_type",
    "get_session_source",
    "set_session_source",
    "get_total_lines_added",
    "get_total_lines_removed",
    "add_to_total_lines_changed",
    "get_total_tool_duration",
    "add_to_tool_duration",
    "get_last_interaction_time",
    "update_last_interaction_time",
    "get_direct_connect_server_url",
    "set_direct_connect_server_url",
    "get_is_remote_mode",
    "set_is_remote_mode",
    "get_session_cron_tasks",
    "add_session_cron_task",
    "remove_session_cron_tasks",
    "get_scheduled_tasks_enabled",
    "set_scheduled_tasks_enabled",
    "get_session_bypass_permissions_mode",
    "set_session_bypass_permissions_mode",
]
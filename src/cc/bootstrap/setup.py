"""Setup Module - Session initialization and configuration.

Handles session startup, worktree creation, permission checks,
background job initialization, and exit event logging.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any

from ..bootstrap.state import (
    get_project_root,
    get_session_id,
    set_original_cwd,
    set_project_root,
    switch_session,
    get_is_interactive,
)


@dataclass
class SetupConfig:
    """Configuration for setup."""
    cwd: str
    permission_mode: str = "default"
    allow_dangerously_skip_permissions: bool = False
    worktree_enabled: bool = False
    worktree_name: Optional[str] = None
    tmux_enabled: bool = False
    custom_session_id: Optional[str] = None
    worktree_pr_number: Optional[int] = None
    messaging_socket_path: Optional[str] = None


@dataclass
class WorktreeSession:
    """Worktree session info."""
    worktree_path: str
    branch_name: str
    session_id: str


def check_python_version() -> None:
    """Check Python version is 3.8+."""
    if sys.version_info < (3, 8):
        print("Error: Claude Code requires Python version 3.8 or higher.")
        sys.exit(1)


def is_bare_mode() -> bool:
    """Check if running in bare mode."""
    return os.environ.get("CLAUDE_CODE_BARE_MODE") == "1"


def is_env_truthy(key: str) -> bool:
    """Check if environment variable is truthy."""
    val = os.environ.get(key, "")
    return val.lower() in ("1", "true", "yes", "on")


async def check_terminal_backup() -> Optional[str]:
    """Check and restore terminal backup if interrupted."""
    # Placeholder - would implement iTerm2 and Terminal.app backup restoration
    return None


async def create_worktree_for_session(
    session_id: str,
    slug: str,
    tmux_session_name: Optional[str] = None,
    pr_info: Optional[Dict[str, int]] = None,
) -> WorktreeSession:
    """Create worktree for session."""
    # Placeholder - would implement git worktree creation
    worktree_path = Path.cwd() / ".worktrees" / slug
    worktree_path.mkdir(parents=True, exist_ok=True)
    return WorktreeSession(
        worktree_path=str(worktree_path),
        branch_name=f"cc-{slug}",
        session_id=session_id,
    )


def generate_tmux_session_name(repo_root: str, branch_name: str) -> str:
    """Generate tmux session name."""
    repo_name = Path(repo_root).name
    return f"cc-{repo_name}-{branch_name}"


async def create_tmux_session_for_worktree(
    session_name: str,
    worktree_path: str,
) -> Dict[str, Any]:
    """Create tmux session for worktree."""
    # Placeholder - would implement tmux session creation
    return {"created": False, "error": "tmux not available"}


def init_session_memory() -> None:
    """Initialize session memory hooks."""
    # Placeholder - registers session memory hooks
    pass


def init_background_jobs() -> None:
    """Initialize background jobs."""
    init_session_memory()


async def prefetch_api_key() -> None:
    """Prefetch API key from helper if safe."""
    # Placeholder - would implement API key prefetch
    pass


async def check_for_release_notes(last_seen: Optional[str]) -> Dict[str, Any]:
    """Check for release notes."""
    # Placeholder - would check for new release notes
    return {"has_release_notes": False}


def get_global_config() -> Dict[str, Any]:
    """Get global configuration."""
    config_path = Path.home() / ".claude" / "config.json"
    if config_path.exists():
        import json
        with open(config_path) as f:
            return json.load(f)
    return {}


def get_current_project_config() -> Dict[str, Any]:
    """Get current project configuration."""
    project_root = get_project_root()
    config_path = Path(project_root) / ".claude" / "config.json"
    if config_path.exists():
        import json
        with open(config_path) as f:
            return json.load(f)
    return {}


def log_event(event_name: str, metadata: Dict[str, Any]) -> None:
    """Log analytics event."""
    # Placeholder - would implement analytics logging
    pass


def capture_hooks_config_snapshot() -> None:
    """Capture hooks configuration snapshot."""
    # Placeholder - would capture hooks config
    pass


def initialize_file_changed_watcher(cwd: str) -> None:
    """Initialize file changed watcher."""
    # Placeholder - would initialize watcher
    pass


def update_hooks_config_snapshot() -> None:
    """Update hooks configuration snapshot."""
    # Placeholder - would update snapshot
    pass


def clear_memory_file_caches() -> None:
    """Clear memory file caches."""
    # Placeholder - would clear caches
    pass


async def setup(config: SetupConfig) -> None:
    """Main setup function for session initialization."""
    # Check Python version
    check_python_version()

    # Set custom session ID if provided
    if config.custom_session_id:
        switch_session(config.custom_session_id)

    cwd = config.cwd

    # Terminal backup restoration - interactive only
    if get_is_interactive():
        await check_terminal_backup()

    # Set working directory
    os.chdir(cwd)

    # Capture hooks configuration
    capture_hooks_config_snapshot()

    # Initialize file changed watcher
    initialize_file_changed_watcher(cwd)

    # Handle worktree creation
    if config.worktree_enabled:
        slug = (
            f"pr-{config.worktree_pr_number}"
            if config.worktree_pr_number
            else (config.worktree_name or "default")
        )

        tmux_session_name = None
        if config.tmux_enabled:
            tmux_session_name = generate_tmux_session_name(cwd, slug)

        try:
            worktree_session = await create_worktree_for_session(
                get_session_id(),
                slug,
                tmux_session_name,
                {"prNumber": config.worktree_pr_number} if config.worktree_pr_number else None,
            )
        except Exception as e:
            print(f"Error creating worktree: {e}")
            sys.exit(1)

        log_event("tengu_worktree_created", {"tmux_enabled": config.tmux_enabled})

        # Create tmux session if enabled
        if config.tmux_enabled and tmux_session_name:
            tmux_result = await create_tmux_session_for_worktree(
                tmux_session_name,
                worktree_session.worktree_path,
            )
            if tmux_result.get("created"):
                print(f"Created tmux session: {tmux_session_name}")
                print(f"To attach: tmux attach -t {tmux_session_name}")

        # Update working directory to worktree
        os.chdir(worktree_session.worktree_path)
        set_original_cwd(worktree_session.worktree_path)
        set_project_root(worktree_session.worktree_path)
        clear_memory_file_caches()
        update_hooks_config_snapshot()

    # Background jobs
    if not is_bare_mode():
        init_background_jobs()

    # Prefetch API key
    await prefetch_api_key()

    # Check for release notes
    if not is_bare_mode():
        global_config = get_global_config()
        await check_for_release_notes(global_config.get("lastReleaseNotesSeen"))

    # Permission bypass checks
    if config.permission_mode == "bypassPermissions" or config.allow_dangerously_skip_permissions:
        # Check if running as root
        if os.name != "nt" and os.getuid() == 0:
            if not is_env_truthy("IS_SANDBOX") and not is_env_truthy("CLAUDE_CODE_BUBBLEWRAP"):
                print("--dangerously-skip-permissions cannot be used with root/sudo")
                sys.exit(1)

    # Log session start
    log_event("tengu_started", {})

    # Log exit event from last session
    project_config = get_current_project_config()
    if "lastCost" in project_config and "lastDuration" in project_config:
        log_event("tengu_exit", {
            "last_session_cost": project_config.get("lastCost"),
            "last_session_api_duration": project_config.get("lastAPIDuration"),
            "last_session_tool_duration": project_config.get("lastToolDuration"),
            "last_session_duration": project_config.get("lastDuration"),
            "last_session_lines_added": project_config.get("lastLinesAdded"),
            "last_session_lines_removed": project_config.get("lastLinesRemoved"),
            "last_session_total_input_tokens": project_config.get("lastTotalInputTokens"),
            "last_session_total_output_tokens": project_config.get("lastTotalOutputTokens"),
            "last_session_id": project_config.get("lastSessionId"),
        })


__all__ = [
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
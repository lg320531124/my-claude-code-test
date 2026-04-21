"""Git context collection."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
import subprocess
from pathlib import Path


def get_git_context(cwd: Path) -> dict:
    """Get git repository context."""
    info = {
        "in_repo": False,
        "branch": None,
        "status": None,
        "remote": None,
        "recent_commits": [],
    }

    try:
        # Check if in git repo
        result = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return info

        info["in_repo"] = True

        # Branch
        info["branch"] = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()

        # Status (short)
        info["status"] = subprocess.run(
            ["git", "status", "--short"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()

        # Remote
        info["remote"] = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()

        # Recent commits
        commits = subprocess.run(
            ["git", "log", "-5", "--oneline"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        ).stdout.strip()
        if commits:
            info["recent_commits"] = commits.split("\n")

    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    return info


def get_git_diff(cwd: Path, staged: bool = True) -> str:
    """Get git diff."""
    try:
        if staged:
            result = subprocess.run(
                ["git", "diff", "--cached"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            result = subprocess.run(
                ["git", "diff"],
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=10,
            )
        return result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def get_staged_files(cwd: Path) -> List[str]:
    """Get list of staged files."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

"""Context collector - gathers environment context."""

from __future__ import annotations
import subprocess
from pathlib import Path


class ContextCollector:
    """Collects context for LLM queries."""

    def __init__(self, cwd: Path):
        self.cwd = cwd

    def collect(self) -> dict:
        """Collect all context."""
        return {
            "cwd": str(self.cwd),
            "git": self._collect_git_context(),
            "files": self._collect_file_context(),
        }

    def _collect_git_context(self) -> dict:
        """Collect git context."""
        try:
            # Check if in git repo
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                return {"in_repo": False}

            # Get branch
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
            ).stdout.strip()

            # Get status
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=self.cwd,
                capture_output=True,
                text=True,
            ).stdout.strip()

            return {
                "in_repo": True,
                "branch": branch,
                "status": status,
            }
        except Exception:
            return {"in_repo": False}

    def _collect_file_context(self) -> dict:
        """Collect file system context."""
        files = list(self.cwd.glob("*"))
        return {
            "count": len(files),
            "has_pyproject": (self.cwd / "pyproject.toml").exists(),
            "has_package_json": (self.cwd / "package.json").exists(),
            "has_git": (self.cwd / ".git").exists(),
        }

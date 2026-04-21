"""Git Utilities - Git operations."""

from __future__ import annotations
import asyncio
import os
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class GitStatus(Enum):
    """Git status types."""
    CLEAN = "clean"
    MODIFIED = "modified"
    STAGED = "staged"
    UNTRACKED = "untracked"
    CONFLICT = "conflict"


@dataclass
class GitBranch:
    """Git branch info."""
    name: str
    is_current: bool = False
    is_remote: bool = False
    upstream: Optional[str] = None
    ahead: int = 0
    behind: int = 0


@dataclass
class GitInfo:
    """Git repository information."""
    root: Optional[Path] = None
    branch: Optional[str] = None
    status: GitStatus = GitStatus.CLEAN
    staged_files: List[str] = field(default_factory=list)
    modified_files: List[str] = field(default_factory=list)
    untracked_files: List[str] = field(default_factory=list)
    branches: List[GitBranch] = field(default_factory=list)


class GitManager:
    """Manage Git operations."""
    
    def __init__(self, cwd: Optional[Path] = None):
        self.cwd = cwd or Path.cwd()
    
    async def is_git_repo(self) -> bool:
        """Check if current directory is a git repo."""
        git_dir = self.cwd / ".git"
        return git_dir.exists()
    
    async def get_root(self) -> Optional[Path]:
        """Get git root directory."""
        if not await self.is_git_repo():
            return None
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--show-toplevel",
                stdout=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return Path(stdout.decode().strip())
        except:
            pass
        
        return None
    
    async def get_branch(self) -> Optional[str]:
        """Get current branch name."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "branch", "--show-current",
                stdout=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, _ = await proc.communicate()
            if proc.returncode == 0:
                return stdout.decode().strip()
        except:
            pass
        
        return None
    
    async def get_status(self) -> GitInfo:
        """Get git status."""
        info = GitInfo(root=await self.get_root(), branch=await self.get_branch())
        
        if not info.root:
            return info
        
        # Get status output
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "status", "--porcelain",
                stdout=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode == 0:
                for line in stdout.decode().splitlines():
                    status = line[:2]
                    file = line[3:]
                    
                    if status.startswith("M"):
                        info.modified_files.append(file)
                    elif status.startswith("A"):
                        info.staged_files.append(file)
                    elif status == "??":
                        info.untracked_files.append(file)
            
            # Determine overall status
            if info.staged_files:
                info.status = GitStatus.STAGED
            elif info.modified_files:
                info.status = GitStatus.MODIFIED
            elif info.untracked_files:
                info.status = GitStatus.UNTRACKED
            else:
                info.status = GitStatus.CLEAN
        
        except:
            pass
        
        return info
    
    async def get_branches(self) -> List[GitBranch]:
        """Get all branches."""
        branches = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "branch", "-vv",
                stdout=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, _ = await proc.communicate()
            
            current_branch = await self.get_branch()
            
            if proc.returncode == 0:
                for line in stdout.decode().splitlines():
                    is_current = line.startswith("*")
                    name = line.split()[0] if is_current else line.split()[0]
                    
                    branches.append(GitBranch(
                        name=name,
                        is_current=name == current_branch,
                    ))
        except:
            pass
        
        return branches
    
    async def get_log(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent commits."""
        commits = []
        
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "log", f"-{limit}", "--oneline",
                stdout=asyncio.subprocess.PIPE,
                cwd=str(self.cwd),
            )
            stdout, _ = await proc.communicate()
            
            if proc.returncode == 0:
                for line in stdout.decode().splitlines():
                    parts = line.split(" ", 1)
                    if len(parts) == 2:
                        commits.append({
                            "hash": parts[0],
                            "message": parts[1],
                        })
        except:
            pass
        
        return commits


# Global git manager
_git_manager: Optional[GitManager] = None


def get_git_manager(cwd: Optional[Path] = None) -> GitManager:
    """Get global git manager."""
    global _git_manager
    if _git_manager is None or cwd:
        _git_manager = GitManager(cwd)
    return _git_manager


__all__ = [
    "GitStatus",
    "GitBranch",
    "GitInfo",
    "GitManager",
    "get_git_manager",
]

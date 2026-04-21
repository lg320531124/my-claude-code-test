"""Branch Command - Manage git branches."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass
from enum import Enum

from ..utils.git import GitManager


class BranchAction(Enum):
    """Branch actions."""
    LIST = "list"
    CREATE = "create"
    DELETE = "delete"
    SWITCH = "switch"
    MERGE = "merge"


@dataclass
class BranchOptions:
    """Branch command options."""
    action: BranchAction = BranchAction.LIST
    name: Optional[str] = None
    base: Optional[str] = None  # Base branch for create
    force: bool = False
    remote: bool = False


async def run_branch(options: BranchOptions, cwd: Optional[Path] = None) -> Dict[str, Any]:
    """Run branch command."""
    git = GitManager(cwd or Path.cwd())
    
    if options.action == BranchAction.LIST:
        return await _list_branches(git)
    elif options.action == BranchAction.CREATE:
        return await _create_branch(git, options)
    elif options.action == BranchAction.DELETE:
        return await _delete_branch(git, options)
    elif options.action == BranchAction.SWITCH:
        return await _switch_branch(git, options)
    elif options.action == BranchAction.MERGE:
        return await _merge_branch(git, options)
    
    return {"success": False, "error": f"Unknown action: {options.action}"}


async def _list_branches(git: GitManager) -> Dict[str, Any]:
    """List branches."""
    branches = await git.get_branches()
    current = await git.get_branch()
    
    return {
        "success": True,
        "branches": [
            {
                "name": b.name,
                "current": b.is_current,
                "remote": b.is_remote,
            }
            for b in branches
        ],
        "current": current,
    }


async def _create_branch(git: GitManager, options: BranchOptions) -> Dict[str, Any]:
    """Create new branch."""
    if not options.name:
        return {"success": False, "error": "Branch name required"}
    
    base = options.base or "main"
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "checkout", "-b", options.name, base,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(git.cwd),
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return {"success": True, "branch": options.name, "base": base}
        else:
            return {"success": False, "error": stderr.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _delete_branch(git: GitManager, options: BranchOptions) -> Dict[str, Any]:
    """Delete branch."""
    if not options.name:
        return {"success": False, "error": "Branch name required"}
    
    flag = "-D" if options.force else "-d"
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "branch", flag, options.name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(git.cwd),
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return {"success": True, "deleted": options.name}
        else:
            return {"success": False, "error": stderr.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _switch_branch(git: GitManager, options: BranchOptions) -> Dict[str, Any]:
    """Switch to branch."""
    if not options.name:
        return {"success": False, "error": "Branch name required"}
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "checkout", options.name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(git.cwd),
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return {"success": True, "switched_to": options.name}
        else:
            return {"success": False, "error": stderr.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _merge_branch(git: GitManager, options: BranchOptions) -> Dict[str, Any]:
    """Merge branch."""
    if not options.name:
        return {"success": False, "error": "Branch name required"}
    
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "merge", options.name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(git.cwd),
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode == 0:
            return {"success": True, "merged": options.name}
        else:
            return {"success": False, "error": stderr.decode()}
    except Exception as e:
        return {"success": False, "error": str(e)}


class BranchCommand:
    """Branch command implementation."""
    
    name = "branch"
    description = "Manage git branches"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute branch command."""
        options = BranchOptions(
            action=BranchAction(args.get("action", "list")),
            name=args.get("name"),
            base=args.get("base"),
            force=args.get("force", False),
            remote=args.get("remote", False),
        )
        
        cwd = Path(args.get("cwd", Path.cwd()))
        return await run_branch(options, cwd)


__all__ = [
    "BranchAction",
    "BranchOptions",
    "run_branch",
    "BranchCommand",
]

"""Diff Command - Show file diffs."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..types.permission import PermissionDecision


class DiffMode(Enum):
    """Diff display modes."""
    UNIFIED = "unified"
    SIDEBYSIDE = "sidebyside"
    COLOR = "color"


@dataclass
class DiffOptions:
    """Diff command options."""
    files: List[str] = field(default_factory=list)
    mode: DiffMode = DiffMode.UNIFIED
    color: bool = True
    context: int = 3  # Lines of context


async def run_diff(options: DiffOptions) -> Dict[str, Any]:
    """Run diff command."""
    results = []
    
    for file_pair in options.files:
        if ":" in file_pair:
            file1, file2 = file_pair.split(":", 1)
        else:
            file1 = file_pair
            file2 = None
        
        file1_path = Path(file1)
        
        if file2:
            file2_path = Path(file2)
        else:
            # Compare with previous version (git)
            file2_path = None
        
        if not file1_path.exists():
            results.append({
                "file": file1,
                "error": "File not found",
            })
            continue
        
        # Get diff
        if file2_path:
            diff = await _diff_files(file1_path, file2_path, options)
        else:
            diff = await _git_diff(file1_path, options)
        
        results.append({
            "file": file1,
            "diff": diff,
        })
    
    return {
        "results": results,
        "mode": options.mode.value,
    }


async def _diff_files(file1: Path, file2: Path, options: DiffOptions) -> str:
    """Diff two files."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "diff",
            "-u",  # unified format
            f"-U{options.context}",  # context lines
            str(file1),
            str(file2),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        
        if stdout:
            return stdout.decode()
        return "Files are identical"
    except Exception as e:
        return f"Error: {e}"


async def _git_diff(file: Path, options: DiffOptions) -> str:
    """Get git diff for file."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "git",
            "diff",
            "-U{}".format(options.context),
            str(file),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(file.parent),
        )
        stdout, stderr = await proc.communicate()
        
        if stdout:
            return stdout.decode()
        return "No changes"
    except Exception as e:
        return f"Error: {e}"


def format_diff(diff: str, color: bool = True) -> str:
    """Format diff output with colors."""
    if not color:
        return diff
    
    lines = diff.split("\n")
    formatted = []
    
    for line in lines:
        if line.startswith("+"):
            formatted.append(f"\033[32m{line}\033[0m")  # Green for additions
        elif line.startswith("-"):
            formatted.append(f"\033[31m{line}\033[0m")  # Red for deletions
        elif line.startswith("@@"):
            formatted.append(f"\033[36m{line}\033[0m")  # Cyan for headers
        else:
            formatted.append(line)
    
    return "\n".join(formatted)


class DiffCommand:
    """Diff command implementation."""
    
    name = "diff"
    description = "Show file differences"
    
    def __init__(self):
        self.permission_level = PermissionDecision.ALLOW
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute diff command."""
        options = DiffOptions(
            files=args.get("files", []),
            mode=DiffMode(args.get("mode", "unified")),
            color=args.get("color", True),
            context=args.get("context", 3),
        )
        
        return await run_diff(options)


__all__ = [
    "DiffMode",
    "DiffOptions",
    "run_diff",
    "format_diff",
    "DiffCommand",
]

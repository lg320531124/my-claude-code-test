"""Enhanced Commit command with asyncio and smart message generation."""

from __future__ import annotations
import asyncio
import re
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table


@dataclass
class GitChange:
    """Represents a git change."""
    status: str
    file: str
    additions: int = 0
    deletions: int = 0


async def run_async_command(cmd: List[str], cwd: Path) -> tuple[str, str, int]:
    """Run command asynchronously."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    return stdout.decode(), stderr.decode(), proc.returncode


async def get_changes(cwd: Path) -> List[GitChange]:
    """Get all changes asynchronously."""
    stdout, _, _ = await run_async_command(
        ["git", "status", "--short", "--porcelain"],
        cwd,
    )

    changes = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue

        status = line[:2].strip()
        file = line[3:]

        # Get diff stats
        if status in ("M", "A"):
            diff_stdout, _, _ = await run_async_command(
                ["git", "diff", "--numstat", file],
                cwd,
            )
            if diff_stdout.strip():
                parts = diff_stdout.strip().split()
                additions = int(parts[0]) if parts[0] != "-" else 0
                deletions = int(parts[1]) if parts[1] != "-" else 0
                changes.append(GitChange(status, file, additions, deletions))
            else:
                changes.append(GitChange(status, file))
        else:
            changes.append(GitChange(status, file))

    return changes


async def analyze_diff(cwd: Path) -> dict:
    """Analyze diff for commit message suggestions."""
    stdout, _, _ = await run_async_command(
        ["git", "diff", "--stat"],
        cwd,
    )

    # Parse stats
    stats = {
        "files_changed": 0,
        "insertions": 0,
        "deletions": 0,
    }

    if stdout.strip():
        lines = stdout.strip().split("\n")
        last_line = lines[-1] if lines else ""
        match = re.search(r"(\d+) files changed", last_line)
        if match:
            stats["files_changed"] = int(match.group(1))
        match = re.search(r"(\d+) insertions", last_line)
        if match:
            stats["insertions"] = int(match.group(1))
        match = re.search(r"(\d+) deletions", last_line)
        if match:
            stats["deletions"] = int(match.group(1))

    return stats


def suggest_commit_type(changes: List[GitChange], diff: dict) -> str:
    """Suggest conventional commit type."""
    # Analyze file patterns
    file_patterns = [c.file.lower() for c in changes]

    # Check for test changes
    if any("test" in f for f in file_patterns):
        return "test"

    # Check for docs
    if any(f.endswith(".md") or "doc" in f for f in file_patterns):
        return "docs"

    # Check for config/build
    if any(f in ["pyproject.toml", "setup.py", "package.json", "Makefile"] for f in file_patterns):
        return "chore"

    # Check for style
    if any(".css" in f or ".scss" in f for f in file_patterns):
        return "style"

    # Check for refactor (many deletions)
    if diff["deletions"] > diff["insertions"] * 2:
        return "refactor"

    # Default to feat or fix based on new/modified
    if any(c.status == "A" for c in changes):
        return "feat"
    else:
        return "fix"


def generate_commit_message(changes: List[GitChange], diff: dict) -> str:
    """Generate smart commit message."""
    type = suggest_commit_type(changes, diff)

    # Analyze changes to find common pattern
    files = [c.file for c in changes]

    # Find common prefix
    if len(files) > 1:
        prefixes = [f.split("/")[:-1] for f in files]
        common_prefix = []
        for parts in zip(*prefixes):
            if len(set(parts)) == 1:
                common_prefix.append(parts[0])
            else:
                break

        scope = "/".join(common_prefix[:2]) if common_prefix else ""
    else:
        # Single file - use file name as scope
        scope = files[0].split("/")[-1].replace(".py", "").replace(".js", "")

    # Generate description
    if type == "feat":
        desc = "add"
    elif type == "fix":
        desc = "fix"
    elif type == "refactor":
        desc = "refactor"
    elif type == "test":
        desc = "add tests for"
    elif type == "docs":
        desc = "update docs for"
    else:
        desc = "update"

    if scope:
        message = f"{type}({scope}): {desc} {scope}"
    else:
        message = f"{type}: {desc}"

    return message


async def run_commit_async(console: Console, cwd: Path, message: Optional[str] = None, auto: bool = False) -> bool:
    """Create a git commit with async operations."""
    # Get changes
    changes = await get_changes(cwd)

    if not changes:
        console.print("[yellow]No changes to commit[/yellow]")
        return False

    # Show changes
    table = Table(title="Changes")
    table.add_column("Status", style="cyan")
    table.add_column("File")
    table.add_column("Additions", style="green")
    table.add_column("Deletions", style="red")

    for change in changes:
        status_colors = {
            "M": "yellow",
            "A": "green",
            "D": "red",
            "?": "blue",
        }
        color = status_colors.get(change.status, "white")
        table.add_row(
            f"[{color}]{change.status}[/]",
            change.file,
            str(change.additions) if change.additions else "",
            str(change.deletions) if change.deletions else "",
        )

    console.print(table)

    # Analyze diff
    diff = await analyze_diff(cwd)
    console.print(f"\n[dim]{diff['files_changed']} files, +{diff['insertions']}, -{diff['deletions']}[/dim]")

    # Generate or get message
    if not message:
        suggested = generate_commit_message(changes, diff)
        console.print(f"\n[dim]Suggested: {suggested}[/dim]")

        if auto:
            message = suggested
        else:
            message = Prompt.ask("[bold]Commit message[/bold]", default=suggested)

    if not message.strip():
        console.print("[red]Empty commit message[/red]")
        return False

    # Stage changes
    await run_async_command(["git", "add", "-A"], cwd)

    # Create commit
    stdout, stderr, code = await run_async_command(
        ["git", "commit", "-m", message],
        cwd,
    )

    if code == 0:
        console.print(f"[green]✓ Committed: {message}[/green]")

        # Show commit info
        stdout, _, _ = await run_async_command(
            ["git", "log", "-1", "--stat"],
            cwd,
        )
        console.print(f"\n[dim]{stdout[:200]}[/dim]")
        return True
    else:
        console.print(f"[red]Commit failed: {stderr}[/red]")
        return False


def run_commit(console: Console, cwd: Path, message: Optional[str] = None) -> None:
    """Sync wrapper for async commit."""
    asyncio.run(run_commit_async(console, cwd, message))


async def get_commit_history(cwd: Path, limit: int = 10) -> List[dict]:
    """Get commit history."""
    stdout, _, _ = await run_async_command(
        ["git", "log", f"-{limit}", "--oneline", "--format=%h|%s|%an|%ar"],
        cwd,
    )

    commits = []
    for line in stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        if len(parts) >= 4:
            commits.append({
                "hash": parts[0],
                "message": parts[1],
                "author": parts[2],
                "date": parts[3],
            })

    return commits


async def amend_commit(console: Console, cwd: Path, message: str) -> bool:
    """Amend last commit."""
    stdout, stderr, code = await run_async_command(
        ["git", "commit", "--amend", "-m", message],
        cwd,
    )

    if code == 0:
        console.print("[green]✓ Amended commit[/green]")
        return True
    else:
        console.print(f"[red]Amend failed: {stderr}[/red]")
        return False

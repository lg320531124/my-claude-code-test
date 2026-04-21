"""Files Command - File management operations."""

from __future__ import annotations
from pathlib import Path
from typing import Optional, List
from rich.console import Console
from rich.table import Table

from ..utils.async_io import (
    exists_async,
    stat_async,
)
from ..utils.async_process import run_command_async


async def run_files(console: Console, cwd: Path, action: str, args: List[str]) -> None:
    """Run files command."""
    if action == "list":
        await list_files(console, cwd, args[0] if args else None)
    elif action == "tree":
        await tree_files(console, cwd, args[0] if args else cwd)
    elif action == "find":
        await find_files(console, cwd, args[0] if args else "")
    elif action == "info":
        await file_info(console, cwd, args[0] if args else None)
    elif action == "clean":
        await clean_files(console, cwd, args[0] if args else "tmp")
    else:
        show_files_help(console)


async def list_files(console: Console, cwd: Path, pattern: Optional[str]) -> None:
    """List files with pattern."""
    # Run async glob command
    result = await run_command_async(
        f"find . -name '{pattern or '*'}' -type f | head -50",
        cwd=cwd,
    )

    table = Table(title="Files")
    table.add_column("File", style="cyan")
    table.add_column("Size", style="green")

    for line in result.stdout.split("\n"):
        if line.strip():
            file_path = Path(line.strip())
            if await exists_async(cwd / file_path):
                stat = await stat_async(cwd / file_path)
                size = stat.st_size
                size_str = f"{size}" if size < 1024 else f"{size // 1024}KB"
                table.add_row(str(file_path), size_str)

    console.print(table)


async def tree_files(console: Console, cwd: Path, directory: Path) -> None:
    """Show file tree."""
    result = await run_command_async(
        f"tree -L 3 '{directory}' 2>/dev/null || find '{directory}' -type d | head -20",
        cwd=cwd,
    )

    console.print("[bold]File Tree:[/bold]")
    console.print(result.stdout)


async def find_files(console: Console, cwd: Path, query: str) -> None:
    """Find files by content."""
    if not query:
        console.print("[red]Please provide a search query[/red]")
        return

    result = await run_command_async(
        f"grep -r '{query}' --include='*.py' --include='*.ts' --include='*.js' -l | head -20",
        cwd=cwd,
    )

    if result.stdout.strip():
        console.print("[bold]Files containing query:[/bold]")
        for line in result.stdout.split("\n"):
            if line.strip():
                console.print(f"  [cyan]{line.strip()}[/]")
    else:
        console.print("[dim]No files found[/]")


async def file_info(console: Console, cwd: Path, file_path: Optional[str]) -> None:
    """Show file info."""
    if not file_path:
        console.print("[red]Please provide a file path[/red]")
        return

    path = cwd / file_path
    if not await exists_async(path):
        console.print(f"[red]File not found: {file_path}[/red]")
        return

    stat = await stat_async(path)

    console.print(f"[bold cyan]File: {file_path}[/]")
    console.print(f"  Size: {stat.st_size} bytes")
    console.print(f"  Modified: {stat.st_mtime}")
    console.print(f"  Permissions: {stat.st_mode}")

    # Show line count for text files
    result = await run_command_async(f"wc -l '{file_path}'", cwd=cwd)
    if result.stdout.strip():
        lines = result.stdout.strip().split()[0]
        console.print(f"  Lines: {lines}")


async def clean_files(console: Console, cwd: Path, pattern: str) -> None:
    """Clean temporary files."""
    console.print(f"[yellow]Finding files matching: {pattern}[/]")

    # List first, don't delete automatically
    result = await run_command_async(
        f"find . -name '{pattern}' -type f",
        cwd=cwd,
    )

    files = [f.strip() for f in result.stdout.split("\n") if f.strip()]

    if not files:
        console.print("[dim]No files found[/]")
        return

    console.print(f"[bold]Found {len(files)} files[/]")
    for f in files[:10]:
        console.print(f"  [cyan]{f}[/]")

    console.print("[dim]Use 'rm' command to delete[/]")


def show_files_help(console: Console) -> None:
    """Show files command help."""
    table = Table(title="Files Commands")
    table.add_column("Command", style="cyan")
    table.add_column("Description")

    commands = [
        ("files list [pattern]", "List files matching pattern"),
        ("files tree [dir]", "Show directory tree"),
        ("files find [query]", "Find files by content"),
        ("files info [file]", "Show file info"),
        ("files clean [pattern]", "Find temp files"),
    ]

    for cmd, desc in commands:
        table.add_row(cmd, desc)

    console.print(table)


__all__ = ["run_files"]
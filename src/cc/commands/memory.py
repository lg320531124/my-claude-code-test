"""Memory command - Persistent memory management."""

from __future__ import annotations
import json
from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table


MEMORY_DIR = Path.home() / ".claude-code-py" / "memory"


def run_memory(console: Console, action: str = "list", name: Optional[str] = None) -> None:
    """Manage persistent memories."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    if action == "list":
        list_memories(console)
    elif action == "show" and name:
        show_memory(console, name)
    elif action == "delete" and name:
        delete_memory(console, name)
    elif action == "clear":
        clear_memories(console)
    else:
        console.print("[red]Unknown action or missing name[/red]")


def list_memories(console: Console) -> None:
    """List all memories."""
    memories = list(MEMORY_DIR.glob("*.md"))

    if not memories:
        console.print("[yellow]No memories stored[/yellow]")
        return

    table = Table(title="Memories")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Modified")

    for mem in sorted(memories):
        name = mem.stem
        modified = datetime.fromtimestamp(mem.stat().st_mtime).strftime("%Y-%m-%d")
        # Try to detect type from content
        content = mem.read_text()
        mem_type = detect_memory_type(content)
        table.add_row(name, mem_type, modified)

    console.print(table)


def show_memory(console: Console, name: str) -> None:
    """Show a specific memory."""
    path = MEMORY_DIR / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Memory not found: {name}[/red]")
        return

    console.print(f"[bold]{name}[/bold]")
    console.print(path.read_text())


def delete_memory(console: Console, name: str) -> None:
    """Delete a memory."""
    path = MEMORY_DIR / f"{name}.md"
    if not path.exists():
        console.print(f"[red]Memory not found: {name}[/red]")
        return

    path.unlink()
    console.print(f"[green]Deleted: {name}[/green]")


def clear_memories(console: Console) -> None:
    """Clear all memories."""
    count = 0
    for mem in MEMORY_DIR.glob("*.md"):
        mem.unlink()
        count += 1
    console.print(f"[green]Cleared {count} memories[/green]")


def detect_memory_type(content: str) -> str:
    """Detect memory type from content."""
    if "---" in content[:50]:
        # Has YAML frontmatter
        if "type:" in content[:200]:
            for line in content[:200].split("\n"):
                if line.startswith("type:"):
                    return line.split(":", 1)[1].strip()
    return "general"


def save_memory(name: str, content: str, memory_type: str = "general") -> Path:
    """Save a memory."""
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)
    path = MEMORY_DIR / f"{name}.md"

    # Add frontmatter
    frontmatter = f"""---
name: {name}
type: {memory_type}
created: {datetime.now().isoformat()}
---

{content}"""

    path.write_text(frontmatter)
    return path

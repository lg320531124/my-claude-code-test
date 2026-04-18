"""Skills command - Skill management."""

import json
from pathlib import Path

from rich.console import Console
from rich.table import Table


SKILLS_DIR = Path.home() / ".claude-code-py" / "skills"


def run_skills(console: Console, action: str = "list", name: str | None = None) -> None:
    """Manage skills."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)

    if action == "list":
        list_skills(console)
    elif action == "show" and name:
        show_skill(console, name)
    elif action == "run" and name:
        console.print(f"[yellow]Skill execution coming soon: {name}[/yellow]")
    else:
        console.print("[red]Unknown action or missing name[/red]")


def list_skills(console: Console) -> None:
    """List available skills."""
    # Check built-in skills
    builtin_skills = get_builtin_skills()

    # Check custom skills
    custom_skills = []
    for skill_file in SKILLS_DIR.glob("*.md"):
        custom_skills.append(skill_file.stem)

    if not builtin_skills and not custom_skills:
        console.print("[yellow]No skills available[/yellow]")
        return

    table = Table(title="Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Type")
    table.add_column("Description")

    for name, desc in builtin_skills.items():
        table.add_row(name, "builtin", desc[:50])

    for name in custom_skills:
        table.add_row(name, "custom", "[dim]user-defined[/]")

    console.print(table)


def show_skill(console: Console, name: str) -> None:
    """Show skill details."""
    # Check custom first
    custom_path = SKILLS_DIR / f"{name}.md"
    if custom_path.exists():
        console.print(f"[bold]{name}[/bold] (custom)")
        console.print(custom_path.read_text())
        return

    # Check builtin
    builtin = get_builtin_skills()
    if name in builtin:
        console.print(f"[bold]{name}[/bold] (builtin)")
        console.print(builtin[name])
        return

    console.print(f"[red]Skill not found: {name}[/red]")


def get_builtin_skills() -> dict:
    """Get built-in skills."""
    return {
        "tdd": "Test-Driven Development workflow",
        "debug": "Systematic debugging process",
        "review": "Code review checklist",
        "plan": "Planning and design workflow",
        "security-review": "Security vulnerability check",
    }


def create_skill(name: str, content: str) -> Path:
    """Create a custom skill."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{name}.md"
    path.write_text(content)
    return path
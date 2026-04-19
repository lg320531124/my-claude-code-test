"""Init command - Initialize project."""

from __future__ import annotations
import json
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt


def run_init(console: Console, cwd: Path) -> None:
    """Initialize project configuration."""
    console.print("[bold]Initializing Claude Code Python[/bold]")

    # Create .claude-code-py directory
    config_dir = cwd / ".claude-code-py"
    config_dir.mkdir(exist_ok=True)

    # Create settings
    settings = {
        "permissions": {
            "allow": ["Read", "Glob", "Grep"],
            "deny": [],
            "ask": ["Bash(rm *)", "Write"],
        },
        "context": {
            "include": ["src/", "lib/", "app/"],
            "exclude": ["node_modules/", ".git/", "__pycache__/"],
        },
    }

    settings_file = config_dir / "settings.json"
    if settings_file.exists():
        console.print("[yellow]Settings file exists[/yellow]")
        overwrite = Prompt.ask("Overwrite?", choices=["y", "n"], default="n")
        if overwrite == "n":
            console.print("[dim]Keeping existing settings[/dim]")
        else:
            settings_file.write_text(json.dumps(settings, indent=2))
            console.print("[green]✓ Settings created[/green]")
    else:
        settings_file.write_text(json.dumps(settings, indent=2))
        console.print("[green]✓ Settings created[/green]")

    # Create AGENTS.md (optional)
    agents_file = cwd / "AGENTS.md"
    if not agents_file.exists():
        create_agents = Prompt.ask("Create AGENTS.md?", choices=["y", "n"], default="y")
        if create_agents == "y":
            agents_content = """# Agents Configuration

This file describes custom agents for this project.

## Available Agents

- planner: Planning agent for complex features
- reviewer: Code review agent
- security: Security analysis agent

## Usage

Use `/agents` command to see available agents.
"""
            agents_file.write_text(agents_content)
            console.print("[green]✓ AGENTS.md created[/green]")

    # Create .gitignore additions
    gitignore = cwd / ".gitignore"
    additions = [
        "# Claude Code Python",
        ".claude-code-py/",
    ]

    if gitignore.exists():
        content = gitignore.read_text()
        if ".claude-code-py/" not in content:
            gitignore.write_text(content + "\n" + "\n".join(additions) + "\n")
            console.print("[green]✓ Added to .gitignore[/green]")
    else:
        gitignore.write_text("\n".join(additions) + "\n")
        console.print("[green]✓ .gitignore created[/green]")

    console.print("\n[bold]Initialization complete![/bold]")
    console.print("[dim]Run 'cc' to start[/dim]")


def get_project_config(cwd: Path) -> dict | None:
    """Get project-level configuration."""
    config_file = cwd / ".claude-code-py" / "settings.json"
    if config_file.exists():
        try:
            return json.loads(config_file.read_text())
        except json.JSONDecodeError:
            pass
    return None

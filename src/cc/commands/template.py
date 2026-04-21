"""Template Command - Template management."""

from __future__ import annotations
from typing import Optional
from rich.console import Console
from rich.table import Table

from ..services.template.template import get_template_service


def run_template(console: Console, action: str = "list", name: Optional[str] = None, category: Optional[str] = None) -> None:
    """Run template command."""
    service = get_template_service()

    if action == "list":
        list_templates(console, service, category)
    elif action == "show":
        show_template(console, service, name)
    elif action == "categories":
        list_categories(console, service)
    elif action == "create":
        create_template(console, service, name)
    else:
        console.print(f"[red]Unknown action: {action}[/red]")


def list_templates(console: Console, service, category: Optional[str]) -> None:
    """List templates."""
    templates = service.list_templates(category)

    if not templates:
        console.print("[dim]No templates found[/dim]")
        return

    table = Table(title="Templates")
    table.add_column("Name", style="cyan")
    table.add_column("Category")
    table.add_column("Description")

    for t in templates:
        desc = t.description or ""[:40]
        table.add_row(t.name, t.category, desc)

    console.print(table)


def show_template(console: Console, service, name: Optional[str]) -> None:
    """Show template details."""
    if not name:
        console.print("[red]Template name required[/red]")
        return

    template = service.get_template(name)
    if not template:
        console.print(f"[red]Template '{name}' not found[/red]")
        return

    console.print(f"\n[bold]Template: {template.name}[/bold]")
    console.print(f"Category: {template.category}")
    console.print(f"Description: {template.description or 'None'}")
    console.print(f"Variables: {', '.join(template.variables) or 'None'}")
    console.print(f"Extension: {template.file_extension or 'None'}")

    console.print("\n[bold]Content:[/bold]")
    console.print(template.content)


def list_categories(console: Console, service) -> None:
    """List template categories."""
    categories = service.get_categories()

    table = Table(title="Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Templates")

    for cat in categories:
        templates = service.list_templates(cat)
        table.add_row(cat, str(len(templates)))

    console.print(table)


def create_template(console: Console, service, name: Optional[str]) -> None:
    """Create custom template."""
    if not name:
        console.print("[red]Template name required[/red]")
        return

    from ..services.template.template import Template

    # Prompt for template content
    console.print("[dim]Enter template content (use {{var}} for variables):[/dim]")
    console.print("[dim]Press Enter twice to finish[/dim]")

    lines = []
    empty_count = 0
    while True:
        try:
            line = input()
            if not line:
                empty_count += 1
                if empty_count >= 2:
                    break
            else:
                empty_count = 0
            lines.append(line)
        except EOFError:
            break

    content = "\n".join(lines[:-2])  # Remove trailing empty lines

    if not content.strip():
        console.print("[red]No content provided[/red]")
        return

    # Extract variables
    import re
    variables = re.findall(r'\{\{(\w+)\}\}', content)

    template = Template(
        name=name,
        category="custom",
        content=content,
        variables=variables,
    )

    service.add_template(template)
    console.print(f"[green]Template '{name}' created[/green]")


__all__ = ["run_template"]
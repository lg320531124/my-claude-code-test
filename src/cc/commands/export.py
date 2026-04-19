"""Export Command - Export session data."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from rich.console import Console

from ..core.session import Session


def run_export(console: Console, session: Session, format: str = "json", output: Optional[str] = None) -> None:
    """Run export command."""
    # Get export data
    data = session.to_dict()

    # Format output
    if format == "json":
        content = json.dumps(data, indent=2)
    elif format == "markdown":
        content = export_as_markdown(session)
    elif format == "text":
        content = export_as_text(session)
    else:
        console.print(f"[red]Unknown format: {format}[/red]")
        return

    # Write to file or stdout
    if output:
        output_path = Path(output)
        output_path.write_text(content)
        console.print(f"[green]Exported to {output_path}[/green]")
    else:
        console.print(content)


def export_as_markdown(session: Session) -> str:
    """Export session as markdown."""
    lines = []
    lines.append(f"# Session Export")
    lines.append(f"\n**Session ID:** {session.session_id}")
    lines.append(f"**Working Directory:** {session.cwd}")
    lines.append(f"\n## Messages\n")

    for i, msg in enumerate(session.messages, 1):
        role = msg.role.capitalize()
        lines.append(f"### {role} Message {i}\n")

        for block in msg.content:
            if hasattr(block, "text"):
                lines.append(block.text)
            elif hasattr(block, "content"):
                lines.append(block.content)

        lines.append("\n")

    return "\n".join(lines)


def export_as_text(session: Session) -> str:
    """Export session as plain text."""
    lines = []
    lines.append(f"Session: {session.session_id}")
    lines.append(f"Directory: {session.cwd}")
    lines.append("")

    for msg in session.messages:
        lines.append(f"[{msg.role}]")
        for block in msg.content:
            if hasattr(block, "text"):
                lines.append(block.text)
            elif hasattr(block, "content"):
                lines.append(f"  {block.content[:100]}...")
        lines.append("")

    return "\n".join(lines)


__all__ = ["run_export"]
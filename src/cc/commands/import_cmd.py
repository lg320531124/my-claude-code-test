"""Import Command - Import session data."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Optional
from rich.console import Console

from ..core.session import Session


def run_import(console: Console, session: Session, path: str, merge: bool = False) -> None:
    """Run import command."""
    import_path = Path(path)

    if not import_path.exists():
        console.print(f"[red]File not found: {path}[/red]")
        return

    content = import_path.read_text()

    # Detect format
    if import_path.suffix == ".json":
        data = json.loads(content)
    elif import_path.suffix in [".md", ".markdown"]:
        data = parse_markdown_session(content)
    else:
        data = parse_text_session(content)

    if not data:
        console.print("[red]Could not parse session data[/red]")
        return

    # Import into session
    if merge:
        # Merge with existing session
        for msg in data.get("messages", []):
            session.messages.append(msg)
        console.print(f"[green]Imported and merged {len(data.get('messages', []))} messages[/green]")
    else:
        # Replace session
        session.messages = data.get("messages", [])
        session.metadata.update(data.get("metadata", {}))
        console.print(f"[green]Imported session: {len(session.messages)} messages[/green]")


def parse_markdown_session(content: str) -> Optional[dict]:
    """Parse markdown session format."""
    messages = []

    # Simple parsing - look for role markers
    lines = content.splitlines()
    current_role = None
    current_text = []

    for line in lines:
        if line.startswith("### User"):
            if current_role and current_text:
                messages.append({
                    "role": current_role,
                    "content": [{"type": "text", "text": "\n".join(current_text)}],
                })
            current_role = "user"
            current_text = []
        elif line.startswith("### Assistant"):
            if current_role and current_text:
                messages.append({
                    "role": current_role,
                    "content": [{"type": "text", "text": "\n".join(current_text)}],
                })
            current_role = "assistant"
            current_text = []
        elif current_role:
            current_text.append(line)

    # Add last message
    if current_role and current_text:
        messages.append({
            "role": current_role,
            "content": [{"type": "text", "text": "\n".join(current_text)}],
        })

    return {"messages": messages}


def parse_text_session(content: str) -> Optional[dict]:
    """Parse text session format."""
    messages = []

    lines = content.splitlines()
    current_role = None
    current_text = []

    for line in lines:
        if line.startswith("[user]"):
            if current_role and current_text:
                messages.append({
                    "role": current_role,
                    "content": [{"type": "text", "text": "\n".join(current_text)}],
                })
            current_role = "user"
            current_text = []
        elif line.startswith("[assistant]"):
            if current_role and current_text:
                messages.append({
                    "role": current_role,
                    "content": [{"type": "text", "text": "\n".join(current_text)}],
                })
            current_role = "assistant"
            current_text = []
        elif current_role:
            if not line.startswith("[") and line.strip():
                current_text.append(line)

    if current_role and current_text:
        messages.append({
            "role": current_role,
            "content": [{"type": "text", "text": "\n".join(current_text)}],
        })

    return {"messages": messages}


__all__ = ["run_import"]
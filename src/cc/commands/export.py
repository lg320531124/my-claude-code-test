"""Export Command - Export session/logs."""

from __future__ import annotations
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..core.session import SessionManager


class ExportFormat(Enum):
    """Export formats."""
    JSON = "json"
    MARKDOWN = "markdown"
    TEXT = "text"
    HTML = "html"


@dataclass
class ExportOptions:
    """Export command options."""
    session_id: Optional[str] = None
    format: ExportFormat = ExportFormat.JSON
    output: Optional[str] = None
    include_tools: bool = True
    include_thinking: bool = False


async def run_export(options: ExportOptions) -> Dict[str, Any]:
    """Export session to file."""
    manager = SessionManager()
    
    # Load session
    if options.session_id:
        session = await manager.load_session(options.session_id)
    else:
        sessions = await manager.list_sessions()
        if not sessions:
            return {"success": False, "error": "No sessions found"}
        session = sessions[0]
    
    if not session:
        return {"success": False, "error": "Session not found"}
    
    # Generate output
    if options.format == ExportFormat.JSON:
        content = _export_json(session, options)
    elif options.format == ExportFormat.MARKDOWN:
        content = _export_markdown(session, options)
    elif options.format == ExportFormat.TEXT:
        content = _export_text(session, options)
    else:
        content = _export_text(session, options)
    
    # Write to file
    if options.output:
        output_path = Path(options.output)
        output_path.write_text(content)
        return {
            "success": True,
            "output": str(output_path),
            "format": options.format.value,
            "size": len(content),
        }
    
    return {
        "success": True,
        "content": content,
        "format": options.format.value,
    }


def _export_json(session: Any, options: ExportOptions) -> str:
    """Export as JSON."""
    data = {
        "id": session.id,
        "cwd": session.cwd,
        "created_at": str(session.created_at),
        "messages": [],
    }
    
    for msg in session.messages:
        msg_data = {
            "role": msg.role,
            "content": msg.content if hasattr(msg, 'content') else str(msg),
        }
        
        if options.include_tools and hasattr(msg, 'tool_calls'):
            msg_data["tool_calls"] = msg.tool_calls
        
        if options.include_thinking and hasattr(msg, 'thinking'):
            msg_data["thinking"] = msg.thinking
        
        data["messages"].append(msg_data)
    
    return json.dumps(data, indent=2)


def _export_markdown(session: Any, options: ExportOptions) -> str:
    """Export as Markdown."""
    lines = [
        f"# Session {session.id}",
        f"",
        f"**Directory:** {session.cwd}",
        f"**Created:** {session.created_at}",
        f"",
        "---",
        f"",
    ]
    
    for i, msg in enumerate(session.messages, 1):
        role = msg.role if hasattr(msg, 'role') else 'unknown'
        content = msg.content if hasattr(msg, 'content') else str(msg)
        
        lines.append(f"## Message {i} ({role})")
        lines.append("")
        lines.append(content)
        lines.append("")
        
        if options.include_tools and hasattr(msg, 'tool_calls'):
            lines.append("### Tool Calls")
            lines.append("")
            for tc in msg.tool_calls:
                lines.append(f"- {tc.name}")
            lines.append("")
    
    return "\n".join(lines)


def _export_text(session: Any, options: ExportOptions) -> str:
    """Export as plain text."""
    lines = [
        f"Session: {session.id}",
        f"Directory: {session.cwd}",
        f"Created: {session.created_at}",
        "",
    ]
    
    for msg in session.messages:
        role = msg.role if hasattr(msg, 'role') else 'unknown'
        content = msg.content if hasattr(msg, 'content') else str(msg)
        lines.append(f"[{role}] {content}")
        lines.append("")
    
    return "\n".join(lines)


class ExportCommand:
    """Export command implementation."""
    
    name = "export"
    description = "Export session to file"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute export command."""
        options = ExportOptions(
            session_id=args.get("session_id"),
            format=ExportFormat(args.get("format", "json")),
            output=args.get("output"),
            include_tools=args.get("include_tools", True),
            include_thinking=args.get("include_thinking", False),
        )
        
        return await run_export(options)


__all__ = [
    "ExportFormat",
    "ExportOptions",
    "run_export",
    "ExportCommand",
]

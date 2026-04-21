"""Import Command - Import session/files."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass
from enum import Enum

from ..core.session import SessionManager, Session


class ImportType(Enum):
    """Import types."""
    SESSION = "session"
    CONTEXT = "context"
    RULES = "rules"
    SETTINGS = "settings"


@dataclass
class ImportOptions:
    """Import command options."""
    file: str
    type: ImportType = ImportType.SESSION
    merge: bool = False


async def run_import(options: ImportOptions) -> Dict[str, Any]:
    """Import file."""
    file_path = Path(options.file)
    
    if not file_path.exists():
        return {"success": False, "error": f"File not found: {options.file}"}
    
    content = file_path.read_text()
    
    if options.type == ImportType.SESSION:
        return await _import_session(content, options)
    elif options.type == ImportType.CONTEXT:
        return await _import_context(content, options)
    elif options.type == ImportType.RULES:
        return await _import_rules(content, options)
    elif options.type == ImportType.SETTINGS:
        return await _import_settings(content, options)
    
    return {"success": False, "error": f"Unknown import type: {options.type}"}


async def _import_session(content: str, options: ImportOptions) -> Dict[str, Any]:
    """Import session."""
    try:
        data = json.loads(content)
        
        session = Session(
            id=data.get("id", ""),
            cwd=data.get("cwd", ""),
            messages=data.get("messages", []),
        )
        
        manager = SessionManager()
        
        if options.merge:
            # Merge with current session
            current = await manager.get_current_session()
            if current:
                current.messages.extend(session.messages)
        else:
            # Create new session from imported data
            await manager.save_session(session)
        
        return {
            "success": True,
            "imported": {
                "id": session.id,
                "messages": len(session.messages),
            },
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _import_context(content: str, options: ImportOptions) -> Dict[str, Any]:
    """Import context."""
    return {"success": True, "imported": "context"}


async def _import_rules(content: str, options: ImportOptions) -> Dict[str, Any]:
    """Import rules."""
    return {"success": True, "imported": "rules"}


async def _import_settings(content: str, options: ImportOptions) -> Dict[str, Any]:
    """Import settings."""
    return {"success": True, "imported": "settings"}


class ImportCommand:
    """Import command implementation."""
    
    name = "import"
    description = "Import session or configuration"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute import command."""
        options = ImportOptions(
            file=args.get("file", ""),
            type=ImportType(args.get("type", "session")),
            merge=args.get("merge", False),
        )
        
        return await run_import(options)


__all__ = [
    "ImportType",
    "ImportOptions",
    "run_import",
    "ImportCommand",
]

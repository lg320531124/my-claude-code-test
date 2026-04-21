"""Resume Command - Resume previous session."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime

from ..core.session import SessionManager, Session


@dataclass
class ResumeOptions:
    """Resume command options."""
    session_id: Optional[str] = None
    latest: bool = True
    branch: Optional[str] = None


async def run_resume(options: ResumeOptions) -> Dict[str, Any]:
    """Resume a previous session."""
    manager = SessionManager()
    
    # Find session
    if options.session_id:
        session = await manager.load_session(options.session_id)
    elif options.latest:
        sessions = await manager.list_sessions()
        if sessions:
            session = sessions[0]  # Most recent
        else:
            return {
                "success": False,
                "error": "No sessions found",
            }
    else:
        return {
            "success": False,
            "error": "Specify session_id or use --latest",
        }
    
    if not session:
        return {
            "success": False,
            "error": f"Session {options.session_id} not found",
        }
    
    # Resume context
    context = {
        "session_id": session.id,
        "messages": len(session.messages),
        "cwd": session.cwd,
        "created_at": session.created_at,
    }
    
    # Optionally checkout branch
    if options.branch:
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "checkout", options.branch,
                cwd=session.cwd,
            )
            await proc.communicate()
        except:
            pass
    
    return {
        "success": True,
        "session": context,
        "resumed": True,
    }


async def list_sessions(limit: int = 10) -> List[Dict[str, Any]]:
    """List recent sessions."""
    manager = SessionManager()
    sessions = await manager.list_sessions()
    
    result = []
    for session in sessions[:limit]:
        result.append({
            "id": session.id,
            "cwd": session.cwd,
            "created_at": session.created_at.isoformat() if hasattr(session.created_at, 'isoformat') else str(session.created_at),
            "messages": len(session.messages),
        })
    
    return result


class ResumeCommand:
    """Resume command implementation."""
    
    name = "resume"
    description = "Resume previous session"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute resume command."""
        options = ResumeOptions(
            session_id=args.get("session_id"),
            latest=args.get("latest", True),
            branch=args.get("branch"),
        )
        
        return await run_resume(options)


__all__ = [
    "ResumeOptions",
    "run_resume",
    "list_sessions",
    "ResumeCommand",
]

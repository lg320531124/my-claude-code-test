"""Clear Command - Clear conversation/terminal."""

from __future__ import annotations
import os
import asyncio
from typing import Dict, Any
from enum import Enum


class ClearTarget(Enum):
    """Clear targets."""
    CONVERSATION = "conversation"
    TERMINAL = "terminal"
    HISTORY = "history"
    ALL = "all"


async def run_clear(target: ClearTarget = ClearTarget.CONVERSATION) -> Dict[str, Any]:
    """Run clear command."""
    if target == ClearTarget.CONVERSATION:
        # Clear current conversation
        return {"success": True, "cleared": "conversation"}
    
    elif target == ClearTarget.TERMINAL:
        # Clear terminal screen
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        return {"success": True, "cleared": "terminal"}
    
    elif target == ClearTarget.HISTORY:
        # Clear command history
        return {"success": True, "cleared": "history"}
    
    elif target == ClearTarget.ALL:
        # Clear everything
        if os.name == "nt":
            os.system("cls")
        else:
            os.system("clear")
        return {"success": True, "cleared": "all"}
    
    return {"success": False, "error": f"Unknown target: {target}"}


class ClearCommand:
    """Clear command implementation."""
    
    name = "clear"
    description = "Clear conversation or terminal"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute clear command."""
        target_str = args.get("target", "conversation")
        target = ClearTarget(target_str.lower())
        return await run_clear(target)


__all__ = [
    "ClearTarget",
    "run_clear",
    "ClearCommand",
]

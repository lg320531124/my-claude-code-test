"""PowerShell Tool - Execute PowerShell commands (Windows)."""

from __future__ import annotations
import platform
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


@dataclass
class PowerShellInput(ToolInput):
    """PowerShell input schema."""
    command: str = ""
    timeout: int = 60000


class PowerShellTool(ToolDef):
    """Tool to execute PowerShell commands on Windows."""
    
    name = "PowerShell"
    input_schema = PowerShellInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Execute PowerShell command."""
        command = args.get("command", "")
        
        if not command:
            return ToolResult(data="Error: command is required")
        
        if platform.system() != "Windows":
            return ToolResult(data=f"PowerShell only available on Windows. Current: {platform.system()}")
        
        # Mock implementation for now
        return ToolResult(data=f"PowerShell: {command} (simulated)")


# Tool registration
_powershell_tool: Optional[PowerShellTool] = None


def get_powershell_tool() -> PowerShellTool:
    """Get global PowerShell tool."""
    global _powershell_tool
    if _powershell_tool is None:
        _powershell_tool = PowerShellTool()
    return _powershell_tool


__all__ = [
    "PowerShellInput",
    "PowerShellTool",
    "get_powershell_tool",
]

"""PowerShell Tool - Windows PowerShell command execution."""

from __future__ import annotations
import asyncio
import subprocess
import shutil
from typing import Optional, Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult


class PowerShellInput(BaseModel):
    """Input for PowerShellTool."""
    command: str = Field(description="PowerShell command to execute")
    timeout: int = Field(default=30000, description="Timeout in milliseconds")


class PowerShellTool(ToolDef):
    """Tool for executing PowerShell commands."""

    name = "PowerShell"
    description = "Execute PowerShell commands on Windows systems"
    input_schema = PowerShellInput

    def __init__(self):
        self._powershell_path = self._find_powershell()

    def _find_powershell(self) -> Optional[str]:
        """Find PowerShell executable."""
        # Try PowerShell Core first (pwsh)
        pwsh = shutil.which("pwsh")
        if pwsh:
            return pwsh

        # Try Windows PowerShell (powershell)
        powershell = shutil.which("powershell")
        if powershell:
            return powershell

        return None

    async def execute(self, input: PowerShellInput, ctx: Any = None) -> ToolResult:
        """Execute PowerShell command."""
        if not self._powershell_path:
            return ToolResult(
                content="PowerShell not available on this system",
                is_error=True,
                metadata={"platform": "non-windows"}
            )

        command = input.command
        timeout = input.timeout

        # Build PowerShell arguments
        args = [
            self._powershell_path,
            "-NoProfile",
            "-NonInteractive",
            "-Command",
            command,
        ]

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout / 1000
            )

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ToolResult(
                    content=f"PowerShell error:\n{error}\n{output}",
                    is_error=True,
                    metadata={
                        "returncode": proc.returncode,
                        "command": command,
                    }
                )

            return ToolResult(
                content=output,
                metadata={
                    "command": command,
                    "returncode": proc.returncode,
                }
            )

        except asyncio.TimeoutError:
            return ToolResult(
                content=f"PowerShell command timed out after {timeout}ms",
                is_error=True,
                metadata={"timeout": timeout, "command": command}
            )
        except Exception as e:
            return ToolResult(
                content=f"PowerShell execution error: {str(e)}",
                is_error=True,
                metadata={"error": str(e), "command": command}
            )


__all__ = ["PowerShellTool", "PowerShellInput"]

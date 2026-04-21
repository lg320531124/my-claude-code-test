"""PowerShell Tool - Windows PowerShell execution."""

from __future__ import annotations
import asyncio
import platform
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class PowerShellInput(ToolInput):
    """Input for PowerShell."""
    command: str
    timeout: int = 30000


class PowerShellTool(ToolDef):
    """Execute PowerShell command (Windows only)."""

    name: ClassVar[str] = "PowerShell"
    description: ClassVar[str] = "Execute PowerShell command on Windows"
    input_schema: ClassVar[type] = PowerShellInput

    async def execute(self, input: PowerShellInput, ctx: ToolUseContext) -> ToolResult:
        """Execute PowerShell command."""
        if platform.system() != "Windows":
            return ToolResult(
                content="PowerShell tool only available on Windows",
                is_error=True
            )

        try:
            proc = await asyncio.create_subprocess_exec(
                "powershell",
                "-Command",
                input.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=input.timeout / 1000
            )

            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ToolResult(
                    content=f"Error: {error}\nOutput: {output}",
                    is_error=True
                )

            return ToolResult(content=output, metadata={"exit_code": proc.returncode})

        except asyncio.TimeoutError:
            proc.kill()
            return ToolResult(content="Command timed out", is_error=True)


class ToolSearchInput(ToolInput):
    """Input for ToolSearch."""
    query: str
    category: str = ""


class ToolSearchTool(ToolDef):
    """Search available tools."""

    name: ClassVar[str] = "ToolSearch"
    description: ClassVar[str] = "Search for available tools by name or category"
    input_schema: ClassVar[type] = ToolSearchInput

    async def execute(self, input: ToolSearchInput, ctx: ToolUseContext) -> ToolResult:
        """Search tools."""
        from . import ALL_TOOLS

        results = []
        for tool_name, tool_class in ALL_TOOLS.items():
            if input.query.lower() in tool_name.lower():
                results.append(f"- {tool_name}: {tool_class.description}")
            elif input.category and hasattr(tool_class, 'category') and tool_class.category == input.category:
                results.append(f"- {tool_name}: {tool_class.description}")

        if not results:
            return ToolResult(content=f"No tools found matching: {input.query}")

        return ToolResult(content="\n".join(results))


class TeamInput(ToolInput):
    """Input for Team tools."""
    team_name: str = ""
    member_email: str = ""


class TeamCreateTool(ToolDef):
    """Create team."""

    name: ClassVar[str] = "TeamCreate"
    description: ClassVar[str] = "Create a new team"
    input_schema: ClassVar[type] = TeamInput

    async def execute(self, input: TeamInput, ctx: ToolUseContext) -> ToolResult:
        """Create team."""
        from ..memdir import get_memdir_service

        service = get_memdir_service()
        team = await service.create_team(input.team_name)

        return ToolResult(
            content=f"Team created: {team.name} (ID: {team.id})",
            metadata={"team_id": team.id}
        )


class TeamDeleteTool(ToolDef):
    """Delete team."""

    name: ClassVar[str] = "TeamDelete"
    description: ClassVar[str] = "Delete a team"
    input_schema: ClassVar[type] = TeamInput

    async def execute(self, input: TeamInput, ctx: ToolUseContext) -> ToolResult:
        """Delete team."""
        from ..memdir import get_memdir_service

        service = get_memdir_service()
        # Would implement deletion logic
        return ToolResult(content=f"Team deletion requires admin privileges")


__all__ = [
    "PowerShellTool",
    "ToolSearchTool",
    "TeamCreateTool",
    "TeamDeleteTool",
]
"""BashTool - Shell command execution."""

import asyncio
import subprocess
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


class BashInput(ToolInput):
    """Input for BashTool."""

    command: str
    timeout_ms: int | None = None
    description: str | None = None


class BashTool(ToolDef):
    """Execute shell commands."""

    name: ClassVar[str] = "Bash"
    description: ClassVar[str] = "Execute shell commands with safety checks"
    input_schema: ClassVar[type[ToolInput]] = BashInput

    async def execute(self, input: BashInput, ctx: ToolUseContext) -> ToolResult:
        """Execute the bash command."""
        timeout = (input.timeout_ms or ctx.timeout_ms) / 1000

        try:
            # Run command in subprocess
            proc = await asyncio.create_subprocess_shell(
                input.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=ctx.cwd,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=timeout,
            )

            # Build result
            output = stdout.decode("utf-8", errors="replace")
            error = stderr.decode("utf-8", errors="replace")

            if proc.returncode != 0:
                return ToolResult(
                    content=f"Command failed with exit code {proc.returncode}\nstdout: {output}\nstderr: {error}",
                    is_error=True,
                    metadata={"exit_code": proc.returncode},
                )

            return ToolResult(
                content=output or "Command executed successfully (no output)",
                metadata={"exit_code": 0},
            )

        except asyncio.TimeoutError:
            return ToolResult(
                content=f"Command timed out after {timeout}s",
                is_error=True,
            )
        except Exception as e:
            return ToolResult(
                content=f"Error executing command: {e}",
                is_error=True,
            )

    def check_permission(self, input: BashInput, ctx: ToolUseContext) -> PermissionResult:
        """Check if command is allowed."""
        cmd = input.command.strip()

        # Dangerous commands always need confirmation
        dangerous = ["rm", "rmdir", "sudo", "chmod", "chown", "mv", "cp"]
        for prefix in dangerous:
            if cmd.startswith(prefix):
                return PermissionResult(
                    decision=PermissionDecision.ASK.value,
                    reason=f"Command '{prefix}' may be destructive",
                )

        # Default to allow for read-only commands
        return PermissionResult(decision=PermissionDecision.ALLOW.value)
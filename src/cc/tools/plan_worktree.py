"""Plan and Worktree tools."""

import json
from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from ..types.permission import PermissionResult, PermissionDecision


class EnterPlanModeInput(ToolInput):
    """Input for EnterPlanMode."""

    pass


class ExitPlanModeInput(ToolInput):
    """Input for ExitPlanMode."""

    allowedPrompts: list[dict] | None = None


class EnterWorktreeInput(ToolInput):
    """Input for EnterWorktree."""

    name: str | None = None
    path: str | None = None


class ExitWorktreeInput(ToolInput):
    """Input for ExitWorktree."""

    action: str = "keep"  # or "remove"
    discard_changes: bool = False


PLAN_FILE = Path.home() / ".claude-code-py" / "plans" / "current_plan.md"


class EnterPlanModeTool(ToolDef):
    """Enter planning mode."""

    name: ClassVar[str] = "EnterPlanMode"
    description: ClassVar[str] = "Enter planning mode to design implementation before executing"
    input_schema: ClassVar[type[ToolInput]] = EnterPlanModeInput

    async def execute(self, input: EnterPlanModeInput, ctx: ToolUseContext) -> ToolResult:
        """Enter plan mode."""
        # Create plan directory
        plan_dir = PLAN_FILE.parent
        plan_dir.mkdir(parents=True, exist_ok=True)

        # Create empty plan file
        PLAN_FILE.write_text("# Implementation Plan\n\n## Context\n\nDescribe the change...\n\n## Plan\n\n1. Step 1\n2. Step 2\n")

        return ToolResult(
            content="Entered planning mode. Plan file created at ~/.claude-code-py/plans/current_plan.md\n\nEdit the plan file, then use ExitPlanMode to proceed.",
            metadata={"plan_file": str(PLAN_FILE)},
        )


class ExitPlanModeTool(ToolDef):
    """Exit planning mode."""

    name: ClassVar[str] = "ExitPlanMode"
    description: ClassVar[str] = "Exit planning mode and proceed with implementation"
    input_schema: ClassVar[type[ToolInput]] = ExitPlanModeInput

    async def execute(self, input: ExitPlanModeInput, ctx: ToolUseContext) -> ToolResult:
        """Exit plan mode."""
        if not PLAN_FILE.exists():
            return ToolResult(
                content="No plan file found. Use EnterPlanMode first.",
                is_error=True,
            )

        plan_content = PLAN_FILE.read_text()

        return ToolResult(
            content=f"Plan approved. Proceeding with implementation.\n\nPlan:\n{plan_content[:500]}...",
            metadata={"plan_file": str(PLAN_FILE)},
        )

    def check_permission(self, input: ExitPlanModeInput, ctx: ToolUseContext) -> PermissionResult:
        """Check permission - always ask for plan approval."""
        return PermissionResult(
            decision=PermissionDecision.ASK.value,
            reason="Plan approval required",
        )


class EnterWorktreeTool(ToolDef):
    """Enter git worktree."""

    name: ClassVar[str] = "EnterWorktree"
    description: ClassVar[str] = "Create and enter a git worktree for isolated work"
    input_schema: ClassVar[type[ToolInput]] = EnterWorktreeInput

    async def execute(self, input: EnterWorktreeInput, ctx: ToolUseContext) -> ToolResult:
        """Enter worktree."""
        import subprocess

        name = input.name or "isolated-work"
        worktree_path = Path(ctx.cwd).parent / f".worktrees/{name}"

        try:
            # Create worktree
            subprocess.run(
                ["git", "worktree", "add", str(worktree_path)],
                cwd=ctx.cwd,
                capture_output=True,
                check=True,
            )

            return ToolResult(
                content=f"Created worktree at {worktree_path}. Working directory changed.",
                metadata={"worktree_path": str(worktree_path)},
            )
        except subprocess.CalledProcessError as e:
            return ToolResult(
                content=f"Failed to create worktree: {e.stderr}",
                is_error=True,
            )


class ExitWorktreeTool(ToolDef):
    """Exit git worktree."""

    name: ClassVar[str] = "ExitWorktree"
    description: ClassVar[str] = "Exit and optionally remove git worktree"
    input_schema: ClassVar[type[ToolInput]] = ExitWorktreeInput

    async def execute(self, input: ExitWorktreeInput, ctx: ToolUseContext) -> ToolResult:
        """Exit worktree."""
        import subprocess

        if input.action == "remove":
            try:
                subprocess.run(
                    ["git", "worktree", "remove", ctx.cwd],
                    capture_output=True,
                    check=True,
                )
                return ToolResult(
                    content=f"Removed worktree at {ctx.cwd}",
                )
            except subprocess.CalledProcessError as e:
                if not input.discard_changes:
                    return ToolResult(
                        content=f"Worktree has changes. Use discard_changes=true to force remove.\n{e.stderr}",
                        is_error=True,
                    )
                subprocess.run(
                    ["git", "worktree", "remove", "--force", ctx.cwd],
                    capture_output=True,
                    check=True,
                )
                return ToolResult(
                    content=f"Force removed worktree at {ctx.cwd}",
                )

        return ToolResult(
            content=f"Keeping worktree at {ctx.cwd}. Return to main directory manually.",
        )
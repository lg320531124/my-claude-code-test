"""REPL Tool - Interactive REPL control."""

from __future__ import annotations
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class REPLInput(ToolInput):
    """Input for REPL tool."""
    command: str = ""
    code: str = ""
    language: str = "python"


class REPLTool(ToolDef):
    """Execute code in REPL."""

    name: ClassVar[str] = "REPL"
    description: ClassVar[str] = "Execute code in interactive REPL"
    input_schema: ClassVar[type] = REPLInput

    async def execute(self, input: REPLInput, ctx: ToolUseContext) -> ToolResult:
        """Execute REPL command."""
        from ..core.repl import get_repl

        repl = get_repl()

        if input.command:
            # Execute REPL command
            result = await repl.execute_command(input.command)
            return ToolResult(content=result)

        if input.code:
            # Execute code
            result = await repl.execute_code(input.code, input.language)
            return ToolResult(content=str(result), metadata={"language": input.language})

        return ToolResult(content="No command or code provided")


class SendMessageInput(ToolInput):
    """Input for SendMessage."""
    to_agent: str
    message: str


class SendMessageTool(ToolDef):
    """Send message to sub-agent."""

    name: ClassVar[str] = "SendMessage"
    description: ClassVar[str] = "Send message to running sub-agent"
    input_schema: ClassVar[type] = SendMessageInput

    async def execute(self, input: SendMessageInput, ctx: ToolUseContext) -> ToolResult:
        """Send message."""
        from ..bridge import get_bridge_manager

        bridge = get_bridge_manager()

        # Send through bridge
        success = await bridge.send_message(input.to_agent, input.message)

        if success:
            return ToolResult(content=f"Message sent to {input.to_agent}")
        else:
            return ToolResult(content=f"Failed to send message to {input.to_agent}", is_error=True)


class SyntheticOutputInput(ToolInput):
    """Input for SyntheticOutput."""
    pattern: str
    count: int = 1


class SyntheticOutputTool(ToolDef):
    """Generate synthetic output."""

    name: ClassVar[str] = "SyntheticOutput"
    description: ClassVar[str] = "Generate synthetic test output"
    input_schema: ClassVar[type] = SyntheticOutputInput

    async def execute(self, input: SyntheticOutputInput, ctx: ToolUseContext) -> ToolResult:
        """Generate synthetic output."""
        outputs = {
            "file_list": ["src/main.py", "src/utils.py", "tests/test_main.py"],
            "git_status": ["M src/main.py", "A tests/test_new.py"],
            "error": ["Error: File not found", "Traceback..."],
            "success": ["Operation completed", "All tests passed"],
        }

        pattern_outputs = outputs.get(input.pattern, ["Generated output"])
        result = pattern_outputs[:input.count]

        return ToolResult(content="\n".join(result), metadata={"pattern": input.pattern})


__all__ = ["REPLTool", "SendMessageTool", "SyntheticOutputTool"]
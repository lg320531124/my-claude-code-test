"""BashTool - Shell command execution.

Ported from TypeScript BashTool.tsx patterns:
- Input schema with timeout, description, run_in_background, dangerouslyDisableSandbox
- Command parsing and permission matching
- Sandbox configuration
- Git commit/PR instructions in prompt
- Search/read/list command classification
- Simulated sed edit (apply directly without running sed)
- Output persistence for large outputs
- Background task management
- Progress callbacks
- Image output handling
- Claude Code hints extraction
"""

from __future__ import annotations
import asyncio
import re
import time
from pathlib import Path
from typing import Dict, Any, Optional, Set, Callable, List

from pydantic import BaseModel, Field

from ..types.tool import Tool, ToolInput, ToolResult, ToolUseContext, ValidationResult, ToolProgressData
from ..types.permission import PermissionResult, PermissionDecision


# Constants
EOL = "\n"
PROGRESS_THRESHOLD_MS = 2000
ASSISTANT_BLOCKING_BUDGET_MS = 15_000
TOOL_SUMMARY_MAX_LENGTH = 60
DEFAULT_TIMEOUT_MS = 120_000
MAX_TIMEOUT_MS = 600_000

# Search commands for collapsible display
BASH_SEARCH_COMMANDS: Set[str] = {
    "find", "grep", "rg", "ag", "ack", "locate", "which", "whereis"
}

# Read/view commands for collapsible display
BASH_READ_COMMANDS: Set[str] = {
    "cat", "head", "tail", "less", "more",
    "wc", "stat", "file", "strings",
    "jq", "awk", "cut", "sort", "uniq", "tr"
}

# Directory-listing commands
BASH_LIST_COMMANDS: Set[str] = {"ls", "tree", "du"}

# Semantic-neutral commands
BASH_SEMANTIC_NEUTRAL_COMMANDS: Set[str] = {
    "echo", "printf", "true", "false", ":"
}

# Commands that typically produce no stdout on success
BASH_SILENT_COMMANDS: Set[str] = {
    "mv", "cp", "rm", "mkdir", "rmdir", "chmod", "chown", "chgrp",
    "touch", "ln", "cd", "export", "unset", "wait"
}

# Commands that should not be auto-backgrounded
DISALLOWED_AUTO_BACKGROUND_COMMANDS: Set[str] = {"sleep"}

# Common background commands for logging
COMMON_BACKGROUND_COMMANDS: Set[str] = {
    "npm", "yarn", "pnpm", "node", "python", "python3", "go", "cargo",
    "make", "docker", "terraform", "webpack", "vite", "jest", "pytest",
    "curl", "wget", "build", "test", "serve", "watch", "dev"
}


class BashProgressData(ToolProgressData):
    """Progress data for Bash tool."""

    type: str = "bash_progress"
    output: str = ""
    full_output: str = ""
    elapsed_time_seconds: float = 0.0
    total_lines: int = 0
    total_bytes: Optional[int] = None
    task_id: Optional[str] = None
    timeout_ms: Optional[int] = None


class BashInput(ToolInput):
    """Input for BashTool."""

    command: str = Field(description="The command to execute")
    timeout: Optional[int] = Field(
        default=None,
        description=f"Optional timeout in milliseconds (max {MAX_TIMEOUT_MS})"
    )
    timeout_ms: Optional[int] = Field(
        default=None,
        description="Alias for timeout"
    )
    description: Optional[str] = Field(
        default=None,
        description="Clear, concise description of what this command does"
    )
    run_in_background: Optional[bool] = Field(
        default=None,
        description="Set to true to run this command in the background"
    )
    dangerously_disable_sandbox: Optional[bool] = Field(
        default=None,
        description="Set to true to dangerously override sandbox mode"
    )
    simulated_sed_edit: Optional[Dict[str, str]] = Field(
        default=None,
        description="Internal: pre-computed sed edit result from preview"
    )

    def model_post_init(self, __context):
        # Sync timeout and timeout_ms
        if self.timeout_ms is not None and self.timeout is None:
            self.timeout = self.timeout_ms
        if self.timeout is not None and self.timeout_ms is None:
            self.timeout_ms = self.timeout


class BashOutput(BaseModel):
    """Output schema for BashTool."""

    stdout: str = Field(description="The standard output of the command")
    stderr: str = Field(description="The standard error output of the command")
    interrupted: bool = Field(description="Whether the command was interrupted")
    is_image: Optional[bool] = Field(
        default=None,
        description="Flag to indicate if stdout contains image data"
    )
    background_task_id: Optional[str] = Field(
        default=None,
        description="ID of the background task if running in background"
    )
    backgrounded_by_user: Optional[bool] = Field(default=None)
    assistant_auto_backgrounded: Optional[bool] = Field(default=None)
    dangerously_disable_sandbox: Optional[bool] = Field(default=None)
    return_code_interpretation: Optional[str] = Field(default=None)
    no_output_expected: Optional[bool] = Field(default=None)
    structured_content: Optional[List[Any]] = Field(default=None)
    persisted_output_path: Optional[str] = Field(default=None)
    persisted_output_size: Optional[int] = Field(default=None)


def split_command_with_operators(command: str) -> List[str]:
    """Split command into parts with operators preserved."""
    # Simple implementation - can be enhanced with proper parsing
    parts = re.split(r'(\||&&|\|\|;|>|>>|>&)', command)
    return [p.strip() for p in parts if p.strip()]


def get_base_command(part: str) -> str:
    """Extract the base command from a command part."""
    tokens = part.strip().split()
    return tokens[0] if tokens else ""


def is_search_or_read_bash_command(command: str) -> Dict[str, bool]:
    """Check if a bash command is a search or read operation."""
    try:
        parts = split_command_with_operators(command)
    except Exception:
        return {"is_search": False, "is_read": False, "is_list": False}

    if not parts:
        return {"is_search": False, "is_read": False, "is_list": False}

    has_search = False
    has_read = False
    has_list = False
    has_non_neutral_command = False
    skip_next = False

    for part in parts:
        if skip_next:
            skip_next = False
            continue

        if part in (">", ">>", ">&"):
            skip_next = True
            continue

        if part in ("||", "&&", "|", ";"):
            continue

        base_cmd = get_base_command(part)
        if not base_cmd:
            continue

        if base_cmd in BASH_SEMANTIC_NEUTRAL_COMMANDS:
            continue

        has_non_neutral_command = True
        is_part_search = base_cmd in BASH_SEARCH_COMMANDS
        is_part_read = base_cmd in BASH_READ_COMMANDS
        is_part_list = base_cmd in BASH_LIST_COMMANDS

        if not (is_part_search or is_part_read or is_part_list):
            return {"is_search": False, "is_read": False, "is_list": False}

        if is_part_search:
            has_search = True
        if is_part_read:
            has_read = True
        if is_part_list:
            has_list = True

    if not has_non_neutral_command:
        return {"is_search": False, "is_read": False, "is_list": False}

    return {"is_search": has_search, "is_read": has_read, "is_list": has_list}


def is_silent_bash_command(command: str) -> bool:
    """Check if a bash command is expected to produce no stdout on success."""
    try:
        parts = split_command_with_operators(command)
    except Exception:
        return False

    if not parts:
        return False

    has_non_fallback_command = False
    last_operator = None
    skip_next = False

    for part in parts:
        if skip_next:
            skip_next = False
            continue

        if part in (">", ">>", ">&"):
            skip_next = True
            continue

        if part in ("||", "&&", "|", ";"):
            last_operator = part
            continue

        base_cmd = get_base_command(part)
        if not base_cmd:
            continue

        if last_operator == "||" and base_cmd in BASH_SEMANTIC_NEUTRAL_COMMANDS:
            continue

        has_non_fallback_command = True
        if base_cmd not in BASH_SILENT_COMMANDS:
            return False

    return has_non_fallback_command


def is_auto_backgrounding_allowed(command: str) -> bool:
    """Check if a command is allowed to be automatically backgrounded."""
    tokens = command.strip().split()
    if not tokens:
        return True
    base_cmd = tokens[0]
    return base_cmd not in DISALLOWED_AUTO_BACKGROUND_COMMANDS


def detect_blocked_sleep_pattern(command: str) -> Optional[str]:
    """Detect standalone or leading sleep patterns that should use Monitor."""
    tokens = command.strip().split()
    if not tokens:
        return None

    first = tokens[0]
    match = re.match(r"^sleep\s+(\d+)\s*$", first)
    if not match:
        return None

    secs = int(match.group(1))
    if secs < 2:
        return None

    rest = " ".join(tokens[1:]).strip()
    return f"sleep {secs} followed by: {rest}" if rest else f"standalone sleep {secs}"


def truncate(text: str, max_length: int) -> str:
    """Truncate text to max_length."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def get_command_type_for_logging(command: str) -> str:
    """Get command type for analytics logging."""
    tokens = command.strip().split()
    if not tokens:
        return "other"

    for token in tokens:
        base = token.split()[0] if token.split() else ""
        if base in COMMON_BACKGROUND_COMMANDS:
            return base

    return "other"


def match_wildcard_pattern(pattern: str, value: str) -> bool:
    """Match wildcard pattern against value."""
    if pattern == "*":
        return True
    if pattern.endswith("*"):
        return value.startswith(pattern[:-1])
    return pattern == value


def permission_rule_extract_prefix(pattern: str) -> Optional[str]:
    """Extract prefix from permission rule pattern."""
    if pattern.endswith("*"):
        return pattern[:-1]
    return None


def get_simple_prompt() -> str:
    """Generate the Bash tool prompt template."""
    return """Executes a given bash command and returns its output.

The working directory persists between commands, but shell state does not. The shell environment is initialized from the user's profile (bash or zsh).

IMPORTANT: Avoid using this tool to run `find`, `grep`, `cat`, `head`, `tail`, `sed`, `awk`, or `echo` commands, unless explicitly instructed or after you have verified that a dedicated tool cannot accomplish your task. Instead, use the appropriate dedicated tool as this will provide a much better experience for the user:

- File search: Use Glob (NOT find or ls)
- Content search: Use Grep (NOT grep or rg)
- Read files: Use Read (NOT cat/head/tail)
- Edit files: Use Edit (NOT sed/awk)
- Write files: Use Write (NOT echo >/cat <<EOF)
- Communication: Output text directly (NOT echo/printf)

While the Bash tool can do similar things, it's better to use the built-in tools as they provide a better user experience and make it easier to review tool calls and give permission.

# Instructions

- If your command will create new directories or files, first use this tool to run `ls` to verify the parent directory exists and is the correct location.
- Always quote file paths that contain spaces with double quotes in your command (e.g., cd "path with spaces/file.txt")
- Try to maintain your current working directory throughout the session by using absolute paths and avoiding usage of `cd`. You may use `cd` if the User explicitly requests it.
- You may specify an optional timeout in milliseconds (up to 600000ms / 10 minutes). By default, your command will timeout after 120000ms (2 minutes).
- When issuing multiple commands:
  - If the commands are independent and can run in parallel, make multiple Bash tool calls in a single message.
  - If the commands depend on each other and must run sequentially, use a single Bash call with '&&' to chain them together.
  - Use ';' only when you need to run commands sequentially but don't care if earlier commands fail.
- For git commands:
  - Prefer to create a new commit rather than amending an existing commit.
  - Before running destructive operations, consider whether there is a safer alternative.
  - Never skip hooks (--no-verify) or bypass signing unless the user explicitly asked for it.
- Avoid unnecessary `sleep` commands:
  - Do not sleep between commands that can run immediately — just run them.
  - Use the Monitor tool to stream events from a background process.
  - If your command is long running, use `run_in_background`. No sleep needed.
  - Do not retry failing commands in a sleep loop — diagnose the root cause.

# Git operations

For git commits and pull requests, follow these steps carefully:

Git Safety Protocol:
- NEVER update the git config
- NEVER run destructive git commands unless the user explicitly requests these actions
- NEVER skip hooks unless the user explicitly requests it
- NEVER run force push to main/master, warn the user if they request it
- CRITICAL: Always create NEW commits rather than amending
- When staging files, prefer adding specific files by name rather than "git add -A"

1. Run git status, git diff, and git log in parallel to understand changes.
2. Draft a commit message focusing on the "why" rather than the "what".
3. Add relevant files and create the commit.
4. Run git status after to verify success.

For pull requests:
1. Run git status, git diff, git log, and check remote tracking.
2. Draft a PR title (under 70 characters) and summary.
3. Create branch if needed, push with -u, and create PR via `gh pr create`.
"""


class BashTool(Tool):
    """Bash tool implementation matching TypeScript BashTool.tsx."""

    name: str = "Bash"
    description_text: str = "Execute shell commands and scripts"
    input_schema: type = BashInput
    max_result_size_chars: float = 30_000
    strict: bool = True
    aliases: Optional[List[str]] = None
    search_hint: str = "execute shell commands"

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute the bash command."""
        input_data = BashInput.model_validate(args)

        # Handle simulated sed edit
        if input_data.simulated_sed_edit:
            return await self._apply_sed_edit(
                input_data.simulated_sed_edit,
                context,
                parent_message,
            )

        timeout_ms = input_data.timeout or DEFAULT_TIMEOUT_MS
        timeout_secs = timeout_ms / 1000

        stdout_accumulator = []
        stderr_accumulator = []
        was_interrupted = False
        exit_code = 0

        try:
            # Run command
            proc = await asyncio.create_subprocess_shell(
                input_data.command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=context.cwd,
            )

            # Wait with timeout
            try:
                stdout_bytes, stderr_bytes = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout_secs,
                )
                stdout = stdout_bytes.decode("utf-8", errors="replace")
                stderr = stderr_bytes.decode("utf-8", errors="replace")
                exit_code = proc.returncode or 0
            except asyncio.TimeoutError:
                proc.kill()
                was_interrupted = True
                stdout = ""
                stderr = f"Command timed out after {timeout_secs}s"

        except asyncio.CancelledError:
            was_interrupted = True
            stdout = ""
            stderr = "<error>Command was aborted before completion</error>"
            exit_code = -1
        except Exception as e:
            return ToolResult(
                data=BashOutput(
                    stdout="",
                    stderr=f"Error executing command: {e}",
                    interrupted=True,
                ),
                is_error=True,
            )

        # Trim output
        stdout = stdout.strip()
        stderr = stderr.strip()

        # Determine if this is an error
        is_error = exit_code != 0 and not was_interrupted

        # Check if output is too large
        persisted_path = None
        persisted_size = None
        if len(stdout) > 30_000:
            # For large outputs, would need to persist to disk
            # Simplified for this implementation
            pass

        # Extract Claude Code hints (strip from output)
        stdout = self._extract_claude_code_hints(stdout, input_data.command)

        # Determine command type for UI
        is_search_read = is_search_or_read_bash_command(input_data.command)
        no_output_expected = is_silent_bash_command(input_data.command)

        output = BashOutput(
            stdout=stdout,
            stderr=stderr,
            interrupted=was_interrupted,
            is_image=self._is_image_output(stdout),
            no_output_expected=no_output_expected,
            dangerously_disable_sandbox=input_data.dangerously_disable_sandbox,
            persisted_output_path=persisted_path,
            persisted_output_size=persisted_size,
        )

        return ToolResult(data=output, is_error=is_error)

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description."""
        if input.get("description"):
            return input["description"]
        cmd = input.get("command", "")
        return truncate(cmd, TOOL_SUMMARY_MAX_LENGTH) if cmd else "Run shell command"

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt."""
        return get_simple_prompt()

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return self.is_read_only(input)

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        result = is_search_or_read_bash_command(input.get("command", ""))
        return result["is_search"] or result["is_read"] or result["is_list"]

    def is_search_or_read_command(self, input: Dict[str, Any]) -> Dict[str, bool]:
        """Check if this is a search/read operation."""
        return is_search_or_read_bash_command(input.get("command", ""))

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> str:
        """Convert input for auto-mode classifier."""
        return input.get("command", "")

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        if not input or not input.get("command"):
            return None
        if input.get("description"):
            return input["description"]
        return truncate(input["command"], TOOL_SUMMARY_MAX_LENGTH)

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        if not input or not input.get("command"):
            return "Running command"
        desc = input.get("description") or truncate(input["command"], TOOL_SUMMARY_MAX_LENGTH)
        return f"Running {desc}"

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name for tool."""
        return "Bash"

    async def execute(
        self,
        input: BashInput,
        ctx: ToolUseContext,
    ) -> ToolResult:
        """Execute method for simpler interface (used by tests)."""
        args = input.model_dump() if hasattr(input, 'model_dump') else dict(input)
        result = await self.call(
            args,
            ctx,
            lambda *args: True,  # Default can_use_tool
            None,  # parent_message
        )
        return result

    def validate_input(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate tool input."""
        # Check for blocked sleep patterns
        if input.get("command"):
            sleep_pattern = detect_blocked_sleep_pattern(input["command"])
            if sleep_pattern:
                return ValidationResult(
                    result=False,
                    message=f"Blocked: {sleep_pattern}. Use run_in_background or Monitor tool.",
                    error_code=10,
                )
        return ValidationResult(result=True)

    async def check_permissions(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check tool permissions."""
        cmd = input.get("command", "").strip()

        # Dangerous commands need confirmation
        dangerous_prefixes = [
            "rm", "rmdir", "sudo", "chmod", "chown",
            "mv", "cp", "git push", "git reset",
        ]
        for prefix in dangerous_prefixes:
            if cmd.startswith(prefix):
                return PermissionResult(
                    decision=PermissionDecision.ASK,
                    reason=f"Command '{prefix}' may be destructive",
                    rule=f"Bash({prefix}*)",
                )

        # Check if read-only
        if self.is_read_only(input):
            return PermissionResult(
                decision=PermissionDecision.ALLOW,
                updated_input=input,
            )

        # Default: ask for non-read-only commands
        return PermissionResult(
            decision=PermissionDecision.ASK,
            reason="Command may modify state",
        )

    def check_permission(self, input: BashInput, ctx: ToolUseContext) -> PermissionResult:
        """Sync permission check wrapper for tests."""
        args = input.model_dump() if hasattr(input, 'model_dump') else dict(input)
        cmd = args.get("command", "").strip()

        # Dangerous commands need confirmation
        dangerous_prefixes = [
            "rm", "rmdir", "sudo", "chmod", "chown",
            "mv", "cp", "git push", "git reset",
        ]
        for prefix in dangerous_prefixes:
            if cmd.startswith(prefix):
                return PermissionResult(
                    decision=PermissionDecision.ASK,
                    reason=f"Command '{prefix}' may be destructive",
                    rule=f"Bash({prefix}*)",
                )

        # Check if read-only
        if self.is_read_only(args):
            return PermissionResult(
                decision=PermissionDecision.ALLOW,
                updated_input=args,
            )

        # Default: ask for non-read-only commands
        return PermissionResult(
            decision=PermissionDecision.ASK,
            reason="Command may modify state",
        )

    def _is_image_output(self, stdout: str) -> bool:
        """Check if output contains image data."""
        # Check for common image file output patterns
        return stdout.startswith("\x89PNG") or stdout.startswith("\xff\xd8")

    def _extract_claude_code_hints(self, stdout: str, command: str) -> str:
        """Extract and strip Claude Code hints from output."""
        # Look for <claude-code-hint /> tags and strip them
        pattern = r"<claude-code-hint\s*/>"
        return re.sub(pattern, "", stdout)

    async def _apply_sed_edit(
        self,
        simulated_edit: Dict[str, str],
        context: ToolUseContext,
        parent_message: Any,
    ) -> ToolResult:
        """Apply a simulated sed edit directly."""
        file_path = simulated_edit.get("filePath", "")
        new_content = simulated_edit.get("newContent", "")

        if not file_path:
            return ToolResult(
                data=BashOutput(
                    stdout="",
                    stderr="sed: No file path provided",
                    interrupted=False,
                ),
                is_error=True,
            )

        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    data=BashOutput(
                        stdout="",
                        stderr=f"sed: {file_path}: No such file or directory\nExit code 1",
                        interrupted=False,
                    ),
                    is_error=True,
                )

            # Write new content
            path.write_text(new_content, encoding="utf-8")

            # Update file state
            if context.read_file_state:
                context.read_file_state[file_path] = {
                    "content": new_content,
                    "timestamp": time.time(),
                }

            return ToolResult(
                data=BashOutput(
                    stdout="",
                    stderr="",
                    interrupted=False,
                ),
            )
        except Exception as e:
            return ToolResult(
                data=BashOutput(
                    stdout="",
                    stderr=f"sed: {e}",
                    interrupted=False,
                ),
                is_error=True,
            )


# Build tool function
def build_bash_tool() -> BashTool:
    """Build BashTool instance."""
    return BashTool()


__all__ = [
    "BashTool",
    "BashInput",
    "BashOutput",
    "BashProgressData",
    "build_bash_tool",
    "is_search_or_read_bash_command",
    "is_silent_bash_command",
    "is_auto_backgrounding_allowed",
    "detect_blocked_sleep_pattern",
    "get_simple_prompt",
    "DEFAULT_TIMEOUT_MS",
    "MAX_TIMEOUT_MS",
]
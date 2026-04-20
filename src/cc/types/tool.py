"""Tool types for Claude Code Python.

Ported from TypeScript Tool.ts patterns:
- Tool interface with full method set
- ToolDef for building tools with defaults
- Progress tracking
- Permission matching
- Validation
- Full asyncio support for all async operations
"""

from __future__ import annotations
import asyncio
from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional, Dict, List, Callable, Union, Awaitable, AsyncIterator
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from .message import ToolResultBlock, ProgressMessage
from .permission import PermissionResult, PermissionDecision, ToolPermissionContext


class ToolInput(BaseModel):
    """Base class for tool input schemas."""

    pass


@dataclass
class ToolResult:
    """Tool execution result (matching TypeScript ToolResult)."""

    data: Any
    new_messages: Optional[List[Any]] = None
    context_modifier: Optional[Callable] = None
    mcp_meta: Optional[Dict[str, Any]] = None  # MCP metadata

    def to_block(self, tool_use_id: str) -> ToolResultBlock:
        """Convert to ToolResultBlock for API."""
        content = self.data if isinstance(self.data, str) else str(self.data)
        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=content,
            is_error=False,
        )


@dataclass
class ValidationResult:
    """Validation result for tool input."""

    result: bool
    message: Optional[str] = None
    error_code: Optional[int] = None


@dataclass
class ToolProgressData:
    """Base class for tool progress data."""

    type: str = "tool_progress"


@dataclass
class ToolProgress:
    """Tool progress tracking."""

    tool_use_id: str
    data: ToolProgressData


@dataclass
class ToolUseContext:
    """Context passed to tool execution (matching TypeScript ToolUseContext).

    Contains:
    - Options (commands, tools, model, etc.)
    - Abort controller
    - State management
    - File cache
    - Permission context
    - Session tracking
    """

    # Options
    commands: List[Any] = field(default_factory=list)
    debug: bool = False
    main_loop_model: str = "claude-sonnet-4-6"
    tools: List[Any] = field(default_factory=list)
    verbose: bool = False
    thinking_config: Optional[Dict[str, Any]] = None
    mcp_clients: List[Any] = field(default_factory=list)
    mcp_resources: Dict[str, List[Any]] = field(default_factory=dict)
    is_non_interactive_session: bool = False
    agent_definitions: Optional[Dict[str, Any]] = None
    max_budget_usd: Optional[float] = None
    custom_system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None

    # Abort handling
    abort_controller: Optional[Any] = None

    # State
    get_app_state: Optional[Callable] = None
    set_app_state: Optional[Callable] = None

    # File state
    read_file_state: Dict[str, Any] = field(default_factory=dict)

    # Permissions
    permission_mode: str = "default"

    # Session
    cwd: str = ""
    session_id: str = ""
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None

    # Additional context
    git_branch: Optional[str] = None
    git_status: Optional[str] = None

    # Progress callbacks
    set_tool_jsx: Optional[Callable] = None
    add_notification: Optional[Callable] = None
    append_system_message: Optional[Callable] = None
    send_os_notification: Optional[Callable] = None

    # Tracking
    nested_memory_attachment_triggers: Optional[set] = None
    loaded_nested_memory_paths: Optional[set] = None
    dynamic_skill_dir_triggers: Optional[set] = None
    discovered_skill_names: Optional[set] = None
    user_modified: bool = False
    set_in_progress_tool_use_ids: Optional[Callable] = None
    set_has_interruptible_tool_in_progress: Optional[Callable] = None
    set_response_length: Optional[Callable] = None
    push_api_metrics_entry: Optional[Callable] = None
    set_stream_mode: Optional[Callable] = None
    on_compact_progress: Optional[Callable] = None
    set_sdk_status: Optional[Callable] = None
    open_message_selector: Optional[Callable] = None

    # File history
    update_file_history_state: Optional[Callable] = None
    update_attribution_state: Optional[Callable] = None
    set_conversation_id: Optional[Callable] = None

    # Messages
    messages: List[Any] = field(default_factory=list)

    # Limits
    file_reading_limits: Optional[Dict[str, int]] = None
    glob_limits: Optional[Dict[str, int]] = None

    # Tool decisions
    tool_decisions: Optional[Dict[str, Any]] = None

    # Query tracking
    query_tracking: Optional[Dict[str, Any]] = None

    # Prompt callback
    request_prompt: Optional[Callable] = None

    # Tool use ID
    tool_use_id: Optional[str] = None

    # Content replacement state
    content_replacement_state: Optional[Dict[str, Any]] = None

    # System prompt
    rendered_system_prompt: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class Tool(ABC):
    """Tool interface matching TypeScript Tool.ts.

    Key patterns:
    - call() for execution
    - description() for prompt generation
    - validateInput() for input validation
    - checkPermissions() for permission checks
    - isConcurrencySafe() for parallel execution
    - isReadOnly() for read-only operations
    - isDestructive() for destructive operations
    - prompt() for tool schema generation
    - Various render methods for UI
    """

    # Required attributes
    name: str
    input_schema: Any  # ZodType in TS, BaseModel in Python
    max_result_size_chars: float = 10000

    # Optional attributes
    aliases: Optional[List[str]] = None
    search_hint: Optional[str] = None
    input_json_schema: Optional[Dict[str, Any]] = None
    output_schema: Optional[Any] = None
    should_defer: bool = False
    always_load: bool = False
    mcp_info: Optional[Dict[str, str]] = None
    strict: bool = False
    is_mcp: bool = False
    is_lsp: bool = False

    @abstractmethod
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute the tool."""
        pass

    @abstractmethod
    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate tool description for prompt."""
        pass

    def inputs_equivalent(self, a: Dict[str, Any], b: Dict[str, Any]) -> bool:
        """Check if two inputs are equivalent."""
        return a == b

    def is_enabled(self) -> bool:
        """Check if tool is enabled."""
        return True

    def is_concurrency_safe(self, input: Dict[str, Any]) -> bool:
        """Check if tool is safe for concurrent execution."""
        return False

    def is_read_only(self, input: Dict[str, Any]) -> bool:
        """Check if tool is read-only."""
        return False

    def is_destructive(self, input: Dict[str, Any]) -> bool:
        """Check if tool performs destructive operations."""
        return False

    def interrupt_behavior(self) -> str:
        """What happens on user interrupt: 'cancel' or 'block'."""
        return "block"

    def is_search_or_read_command(self, input: Dict[str, Any]) -> Dict[str, bool]:
        """Check if this is a search/read operation for UI."""
        return {"is_search": False, "is_read": False, "is_list": False}

    def is_open_world(self, input: Dict[str, Any]) -> bool:
        """Check if tool accesses external world."""
        return False

    def requires_user_interaction(self) -> bool:
        """Check if tool requires user interaction."""
        return False

    def get_path(self, input: Dict[str, Any]) -> Optional[str]:
        """Get file path from input (for file tools)."""
        return None

    async def prepare_permission_matcher(
        self,
        input: Dict[str, Any],
    ) -> Callable:
        """Prepare permission pattern matcher."""
        return lambda pattern: pattern == self.name

    async def prompt(
        self,
        options: Dict[str, Any],
    ) -> str:
        """Generate tool prompt for system message."""
        schema = self.get_api_schema()
        desc = schema.get("description", "")
        return f"- {self.name}: {desc}"

    async def get_api_schema_async(self) -> Dict[str, Any]:
        """Generate Anthropic API-compatible tool schema (async)."""
        # Schema generation in thread pool for complex schemas
        if hasattr(self.input_schema, 'model_json_schema'):
            loop = asyncio.get_event_loop()
            schema = await loop.run_in_executor(None, self.input_schema.model_json_schema)
        else:
            schema = self.input_json_schema or {"type": "object", "properties": {}}

        return {
            "name": self.name,
            "description": getattr(self, 'description_text', self.name),
            "input_schema": schema,
        }

    async def run_sync_in_executor(
        self,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Run a synchronous function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def user_facing_name(self, input: Optional[Dict[str, Any]]) -> str:
        """Get user-facing name for tool."""
        return self.name

    def user_facing_name_background_color(
        self,
        input: Optional[Dict[str, Any]],
    ) -> Optional[str]:
        """Get background color for tool name display."""
        return None

    def is_transparent_wrapper(self) -> bool:
        """Check if this is a transparent wrapper tool."""
        return False

    def get_tool_use_summary(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get short summary for compact view."""
        return None

    def get_activity_description(self, input: Optional[Dict[str, Any]]) -> Optional[str]:
        """Get activity description for spinner."""
        return None

    def to_auto_classifier_input(self, input: Dict[str, Any]) -> Any:
        """Convert input for auto-mode classifier."""
        return ""

    def map_tool_result_to_tool_result_block_param(
        self,
        content: Any,
        tool_use_id: str,
    ) -> ToolResultBlock:
        """Map result to API block."""
        return ToolResultBlock(
            tool_use_id=tool_use_id,
            content=str(content),
        )

    async def validate_input(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> ValidationResult:
        """Validate tool input (async version)."""
        # Run Pydantic validation in thread pool for large inputs
        if len(str(input)) > 10000:
            loop = asyncio.get_event_loop()
            try:
                validated = await loop.run_in_executor(
                    None,
                    lambda: self.input_schema.model_validate(input) if hasattr(self.input_schema, 'model_validate') else input
                )
                return ValidationResult(result=True)
            except Exception as e:
                return ValidationResult(result=False, message=str(e), error_code=400)
        else:
            try:
                validated = self.input_schema.model_validate(input) if hasattr(self.input_schema, 'model_validate') else input
                return ValidationResult(result=True)
            except Exception as e:
                return ValidationResult(result=False, message=str(e), error_code=400)

    async def check_permissions(
        self,
        input: Dict[str, Any],
        context: ToolUseContext,
    ) -> PermissionResult:
        """Check tool permissions."""
        # Default: defer to general permission system
        return PermissionResult(decision=PermissionDecision.ALLOW, updated_input=input)

    def backfill_observable_input(self, input: Dict[str, Any]) -> None:
        """Backfill input with legacy/derived fields."""
        pass

    def get_api_schema(self) -> Dict[str, Any]:
        """Generate Anthropic API-compatible tool schema."""
        if self.input_json_schema:
            schema = self.input_json_schema
        elif hasattr(self.input_schema, 'model_json_schema'):
            schema = self.input_schema.model_json_schema()
        else:
            schema = {"type": "object", "properties": {}}

        return {
            "name": self.name,
            "description": getattr(self, 'description_text', self.name),
            "input_schema": schema,
        }

    def is_result_truncated(self, output: Any) -> bool:
        """Check if result is truncated."""
        return False

    def extract_search_text(self, output: Any) -> str:
        """Extract searchable text from result."""
        return str(output) if output else ""


class Tools:
    """Collection of tools (matching TypeScript Tools type)."""

    def __init__(self, tools: List[Tool]):
        self._tools = tools

    def __iter__(self):
        return iter(self._tools)

    def __len__(self):
        return len(self._tools)

    def __getitem__(self, index):
        return self._tools[index]


# Tool defaults (matching TypeScript TOOL_DEFAULTS)
TOOL_DEFAULTS = {
    "is_enabled": lambda: True,
    "is_concurrency_safe": lambda input=None: False,
    "is_read_only": lambda input=None: False,
    "is_destructive": lambda input=None: False,
    "check_permissions": lambda input=None, ctx=None: PermissionResult(decision=PermissionDecision.ALLOW, updated_input=input),
    "to_auto_classifier_input": lambda input=None: "",
    "user_facing_name": lambda input=None: "",
}


class ToolDef:
    """Tool definition for building tools with defaults.

    Usage:
        class MyTool(ToolDef):
            name = "my_tool"
            input_schema = MyInputSchema

            async def call(self, args, ctx, can_use_tool, parent_message):
                return ToolResult(data="result")

    This fills in safe defaults for optional methods.
    """

    # Required to be defined in subclass
    name: str
    input_schema: Any

    def __init__(self):
        # Apply defaults
        if not hasattr(self, 'is_enabled'):
            self.is_enabled = TOOL_DEFAULTS["is_enabled"]
        if not hasattr(self, 'is_concurrency_safe'):
            self.is_concurrency_safe = TOOL_DEFAULTS["is_concurrency_safe"]
        if not hasattr(self, 'is_read_only'):
            self.is_read_only = TOOL_DEFAULTS["is_read_only"]
        if not hasattr(self, 'is_destructive'):
            self.is_destructive = TOOL_DEFAULTS["is_destructive"]
        if not hasattr(self, 'check_permissions'):
            self.check_permissions = TOOL_DEFAULTS["check_permissions"]
        if not hasattr(self, 'to_auto_classifier_input'):
            self.to_auto_classifier_input = TOOL_DEFAULTS["to_auto_classifier_input"]
        if not hasattr(self, 'user_facing_name'):
            self.user_facing_name = lambda input=None: self.name

    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Any,
        on_progress: Optional[Callable] = None,
    ) -> ToolResult:
        """Execute the tool (must be implemented)."""
        raise NotImplementedError

    async def description(
        self,
        input: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Generate description."""
        return getattr(self, 'description_text', self.name)


def build_tool(defn: ToolDef) -> Tool:
    """Build a complete Tool from a ToolDef with defaults."""
    # Create a Tool that wraps the ToolDef
    class BuiltTool(Tool):
        def __init__(self, defn):
            self._defn = defn
            self.name = defn.name
            self.input_schema = defn.input_schema
            self.max_result_size_chars = getattr(defn, 'max_result_size_chars', 10000)
            self.aliases = getattr(defn, 'aliases', None)
            self.search_hint = getattr(defn, 'search_hint', None)
            self.should_defer = getattr(defn, 'should_defer', False)
            self.always_load = getattr(defn, 'always_load', False)
            self.mcp_info = getattr(defn, 'mcp_info', None)
            self.is_mcp = getattr(defn, 'is_mcp', False)
            self.is_lsp = getattr(defn, 'is_lsp', False)

            # Copy description text
            self.description_text = getattr(defn, 'description_text', defn.name)

        async def call(self, args, context, can_use_tool, parent_message, on_progress=None):
            return await self._defn.call(args, context, can_use_tool, parent_message, on_progress)

        async def description(self, input, options):
            return await self._defn.description(input, options)

        def is_enabled(self):
            return self._defn.is_enabled()

        def is_concurrency_safe(self, input):
            return self._defn.is_concurrency_safe(input)

        def is_read_only(self, input):
            return self._defn.is_read_only(input)

        def is_destructive(self, input):
            return self._defn.is_destructive(input)

        def check_permissions(self, input, context):
            return self._defn.check_permissions(input, context)

        def to_auto_classifier_input(self, input):
            return self._defn.to_auto_classifier_input(input)

        def user_facing_name(self, input):
            return self._defn.user_facing_name(input)

    return BuiltTool(defn)


def tool_matches_name(tool: Union[Tool, Dict], name: str) -> bool:
    """Check if tool name matches (supports aliases)."""
    tool_name = tool.name if hasattr(tool, 'name') else tool.get('name', '')
    aliases = tool.aliases if hasattr(tool, 'aliases') else tool.get('aliases', [])

    if tool_name == name:
        return True
    if aliases and name in aliases:
        return True
    return False


def find_tool_by_name(tools: List[Tool], name: str) -> Optional[Tool]:
    """Find tool by name or alias."""
    for tool in tools:
        if tool_matches_name(tool, name):
            return tool
    return None


__all__ = [
    "Tool",
    "ToolDef",
    "Tools",
    "ToolInput",
    "ToolResult",
    "ToolUseContext",
    "ToolProgress",
    "ToolProgressData",
    "ValidationResult",
    "build_tool",
    "tool_matches_name",
    "find_tool_by_name",
    "TOOL_DEFAULTS",
    # Async helpers
    "execute_tools_parallel",
    "execute_tool_with_timeout",
]


# Async execution helpers
async def execute_tools_parallel(
    tools: List[Tool],
    inputs: List[Dict[str, Any]],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    on_progress: Optional[Callable] = None,
) -> List[ToolResult]:
    """Execute multiple tools in parallel using asyncio.gather.

    Args:
        tools: List of tools to execute
        inputs: List of inputs for each tool
        context: Tool context
        can_use_tool: Permission check callback
        parent_message: Parent message
        on_progress: Progress callback

    Returns:
        List of ToolResults
    """
    tasks = [
        tool.call(input, context, can_use_tool, parent_message, on_progress)
        for tool, input in zip(tools, inputs)
    ]
    return await asyncio.gather(*tasks)


async def execute_tool_with_timeout(
    tool: Tool,
    input: Dict[str, Any],
    context: ToolUseContext,
    can_use_tool: Callable,
    parent_message: Any,
    timeout: float = 30.0,
    on_progress: Optional[Callable] = None,
) -> ToolResult:
    """Execute a tool with timeout.

    Args:
        tool: Tool to execute
        input: Tool input
        context: Tool context
        can_use_tool: Permission check callback
        parent_message: Parent message
        timeout: Timeout in seconds
        on_progress: Progress callback

    Returns:
        ToolResult or error result if timed out
    """
    try:
        return await asyncio.wait_for(
            tool.call(input, context, can_use_tool, parent_message, on_progress),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return ToolResult(
            data=f"Tool {tool.name} timed out after {timeout} seconds",
            is_error=True,
        )
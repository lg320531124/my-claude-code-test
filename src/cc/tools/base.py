"""Tool Base - Core tool infrastructure for Claude Code.

Provides Tool types, ToolResult, ToolUseContext, and tool registry
for implementing command-line tools.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Callable, Generic, TypeVar
from abc import ABC, abstractmethod


InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")
ProgressT = TypeVar("ProgressT")


class ValidationResult:
    """Validation result for tool inputs."""

    def __init__(self, result: bool, message: str = "", error_code: int = 0):
        self.result = result
        self.message = message
        self.error_code = error_code

    @classmethod
    def valid(cls) -> ValidationResult:
        return cls(result=True)

    @classmethod
    def invalid(cls, message: str, error_code: int = 1) -> ValidationResult:
        return cls(result=False, message=message, error_code=error_code)


@dataclass
class ToolProgress:
    """Progress data for tool execution."""
    tool_use_id: str
    data: Dict[str, Any]


@dataclass
class ToolResult(Generic[OutputT]):
    """Result from tool execution."""
    data: OutputT
    new_messages: Optional[List[Dict[str, Any]]] = None
    context_modifier: Optional[Callable] = None
    mcp_meta: Optional[Dict[str, Any]] = None


@dataclass
class ToolPermissionContext:
    """Permission context for tool execution."""
    mode: str = "default"
    additional_working_directories: Dict[str, Any] = field(default_factory=dict)
    always_allow_rules: Dict[str, Any] = field(default_factory=dict)
    always_deny_rules: Dict[str, Any] = field(default_factory=dict)
    always_ask_rules: Dict[str, Any] = field(default_factory=dict)
    is_bypass_permissions_mode_available: bool = False
    is_auto_mode_available: bool = False
    stripped_dangerous_rules: Optional[Dict[str, Any]] = None
    should_avoid_permission_prompts: bool = False
    await_automated_checks_before_dialog: bool = False
    pre_plan_mode: Optional[str] = None


def get_empty_tool_permission_context() -> ToolPermissionContext:
    """Get empty permission context."""
    return ToolPermissionContext()


@dataclass
class ToolOptions:
    """Options for tool execution context."""
    commands: List[Any] = field(default_factory=list)
    debug: bool = False
    main_loop_model: str = ""
    tools: List[Tool] = field(default_factory=list)
    verbose: bool = False
    thinking_config: Optional[Dict[str, Any]] = None
    mcp_clients: List[Any] = field(default_factory=list)
    mcp_resources: Dict[str, List[Any]] = field(default_factory=dict)
    is_non_interactive_session: bool = False
    agent_definitions: Optional[Dict[str, Any]] = None
    max_budget_usd: Optional[float] = None
    custom_system_prompt: Optional[str] = None
    append_system_prompt: Optional[str] = None
    query_source: Optional[str] = None
    refresh_tools: Optional[Callable] = None


@dataclass
class ToolUseContext:
    """Context for tool use execution."""
    options: ToolOptions = field(default_factory=ToolOptions)
    abort_controller: Optional[asyncio.Future] = None
    read_file_state: Dict[str, Any] = field(default_factory=dict)
    messages: List[Dict[str, Any]] = field(default_factory=list)
    file_reading_limits: Optional[Dict[str, int]] = None
    glob_limits: Optional[Dict[str, int]] = None
    tool_decisions: Optional[Dict[str, Dict[str, Any]]] = None
    query_tracking: Optional[Dict[str, Any]] = None
    tool_use_id: Optional[str] = None
    user_modified: bool = False
    agent_id: Optional[str] = None
    agent_type: Optional[str] = None

    def get_app_state(self) -> Dict[str, Any]:
        """Get application state."""
        return {}

    def set_app_state(self, updater: Callable) -> None:
        """Set application state."""
        pass

    def add_notification(self, notification: Dict[str, Any]) -> None:
        """Add notification."""
        pass

    def append_system_message(self, message: Dict[str, Any]) -> None:
        """Append system message."""
        pass


@dataclass
class InputSchema:
    """Input schema for tool validation."""
    type: str = "object"
    properties: Dict[str, Any] = field(default_factory=dict)
    required: List[str] = field(default_factory=list)

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema format."""
        return {
            "type": self.type,
            "properties": self.properties,
            "required": self.required,
        }

    def validate(self, input_data: Dict[str, Any]) -> ValidationResult:
        """Validate input against schema."""
        # Check required fields
        for field_name in self.required:
            if field_name not in input_data:
                return ValidationResult.invalid(
                    f"Missing required field: {field_name}",
                    error_code=1,
                )

        # Check field types (basic validation)
        for field_name, field_spec in self.properties.items():
            if field_name in input_data:
                expected_type = field_spec.get("type")
                value = input_data[field_name]

                if expected_type == "string" and not isinstance(value, str):
                    return ValidationResult.invalid(
                        f"Field {field_name} must be a string",
                        error_code=2,
                    )
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    return ValidationResult.invalid(
                        f"Field {field_name} must be a number",
                        error_code=2,
                    )
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return ValidationResult.invalid(
                        f"Field {field_name} must be a boolean",
                        error_code=2,
                    )
                elif expected_type == "array" and not isinstance(value, list):
                    return ValidationResult.invalid(
                        f"Field {field_name} must be an array",
                        error_code=2,
                    )

        return ValidationResult.valid()


class Tool(ABC, Generic[InputT, OutputT]):
    """Abstract base class for tools."""

    name: str
    aliases: List[str] = field(default_factory=list)
    search_hint: Optional[str] = None
    input_schema: InputSchema

    @abstractmethod
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Callable,
        parent_message: Dict[str, Any],
        on_progress: Optional[Callable] = None,
    ) -> ToolResult[OutputT]:
        """Execute the tool."""
        pass

    @abstractmethod
    async def description(
        self,
        input_data: Dict[str, Any],
        options: Dict[str, Any],
    ) -> str:
        """Get tool description."""
        pass

    def matches_name(self, name: str) -> bool:
        """Check if tool matches given name."""
        return self.name == name or name in self.aliases

    def get_json_schema(self) -> Dict[str, Any]:
        """Get input schema in JSON format."""
        return self.input_schema.to_json_schema()

    def validate_input(self, input_data: Dict[str, Any]) -> ValidationResult:
        """Validate input against schema."""
        return self.input_schema.validate(input_data)


def tool_matches_name(tool: Tool, name: str) -> bool:
    """Check if tool matches the given name."""
    return tool.name == name or (tool.aliases and name in tool.aliases)


def find_tool_by_name(tools: List[Tool], name: str) -> Optional[Tool]:
    """Find a tool by name or alias."""
    for tool in tools:
        if tool_matches_name(tool, name):
            return tool
    return None


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        for alias in tool.aliases:
            self._tools[alias] = tool

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name."""
        if name in self._tools:
            tool = self._tools[name]
            del self._tools[name]
            for alias in tool.aliases:
                self._tools.pop(alias, None)
            return True
        return False

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self._tools.get(name)

    def list_all(self) -> List[Tool]:
        """List all registered tools."""
        return list(set(self._tools.values()))

    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()


# Global tool registry
_tool_registry = ToolRegistry()


def get_tool_registry() -> ToolRegistry:
    """Get global tool registry."""
    return _tool_registry


__all__ = [
    "ValidationResult",
    "ToolProgress",
    "ToolResult",
    "ToolPermissionContext",
    "get_empty_tool_permission_context",
    "ToolOptions",
    "ToolUseContext",
    "InputSchema",
    "Tool",
    "tool_matches_name",
    "find_tool_by_name",
    "ToolRegistry",
    "get_tool_registry",
]
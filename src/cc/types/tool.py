"""Tool types for Claude Code Python."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar

from pydantic import BaseModel

from .message import ToolResultBlock
from .permission import PermissionResult


class ToolInput(BaseModel):
    """Base class for tool input schemas."""

    pass


class ToolResult(BaseModel):
    """Tool execution result."""

    content: str
    is_error: bool = False
    metadata: dict[str, Any] = {}

    def to_block(self, tool_use_id: str) -> ToolResultBlock:
        """Convert to ToolResultBlock for API."""
        return ToolResultBlock(tool_use_id=tool_use_id, content=self.content, is_error=self.is_error)


class ToolUseContext(BaseModel):
    """Context passed to tool execution."""

    cwd: str
    session_id: str
    user_type: str = "external"
    permission_mode: str = "default"
    model: str = "claude-sonnet-4-6"

    # Additional context
    git_branch: str | None = None
    git_status: str | None = None
    file_cache: dict[str, str] = {}

    # Tool-specific settings
    sandbox_enabled: bool = False
    timeout_ms: int = 120000

    class Config:
        arbitrary_types_allowed = True


class ToolDef(ABC):
    """Abstract base class for tool definitions."""

    name: ClassVar[str]
    description: ClassVar[str]
    input_schema: ClassVar[type[ToolInput]]

    @abstractmethod
    async def execute(self, input: ToolInput, ctx: ToolUseContext) -> ToolResult:
        """Execute the tool with given input and context."""
        pass

    def validate_input(self, input_dict: dict[str, Any]) -> ToolInput:
        """Validate and parse input."""
        return self.input_schema.model_validate(input_dict)

    def get_api_schema(self) -> dict[str, Any]:
        """Generate Anthropic API-compatible tool schema."""
        schema = self.input_schema.model_json_schema()
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": schema,
        }

    def check_permission(self, input: ToolInput, ctx: ToolUseContext) -> PermissionResult:
        """Check if tool execution is permitted."""
        # Default: allowed, can be overridden by specific tools
        return PermissionResult(decision="allow")


class ValidationResult(BaseModel):
    """Validation result for tool input."""

    valid: bool
    error_message: str | None = None


def tool_matches_name(tool: ToolDef, name: str) -> bool:
    """Check if tool name matches (supports fuzzy matching)."""
    # Exact match
    if tool.name == name:
        return True
    # Lowercase match
    if tool.name.lower() == name.lower():
        return True
    return False
"""Tool Search - Search for available tools."""

from __future__ import annotations
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


@dataclass
class ToolSearchInput(ToolInput):
    """Tool search input schema."""
    query: str = ""
    limit: int = 10


class ToolSearchTool(ToolDef):
    """Tool to search for available tools."""
    
    name = "ToolSearch"
    input_schema = ToolSearchInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Search for tools."""
        query = args.get("query", "").lower()
        limit = args.get("limit", 10)
        
        # List known tools
        known_tools = [
            "Bash", "Read", "Write", "Edit", "Glob", "Grep",
            "WebFetch", "WebSearch", "Agent", "TaskOutput", "TaskStop",
            "PowerShell", "SyntheticOutput", "AskUserQuestion", "Skill",
        ]
        
        # Filter by query
        if query:
            matching = [t for t in known_tools if query in t.lower()]
        else:
            matching = known_tools
        
        matching = matching[:limit]
        
        return ToolResult(data="Matching tools:\n" + "\n".join(f"- {t}" for t in matching))


# Tool registration
_tool_search: Optional[ToolSearchTool] = None


def get_tool_search() -> ToolSearchTool:
    """Get global tool search."""
    global _tool_search
    if _tool_search is None:
        _tool_search = ToolSearchTool()
    return _tool_search


__all__ = [
    "ToolSearchInput",
    "ToolSearchTool",
    "get_tool_search",
]

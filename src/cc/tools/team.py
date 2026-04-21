"""Team Tool - Team management operations."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


@dataclass
class TeamInput(ToolInput):
    """Team input schema."""
    action: str = "list"  # list, create, delete, invite
    team_id: Optional[str] = None
    name: Optional[str] = None
    members: List[str] = []


class TeamTool(ToolDef):
    """Tool for team management."""
    
    name = "Team"
    input_schema = TeamInput
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Execute team operation."""
        action = args.get("action", "list")
        
        if action == "list":
            # List teams (simulated)
            teams = [
                {"id": "team_1", "name": "Development", "members": 5},
                {"id": "team_2", "name": "QA", "members": 3},
            ]
            return ToolResult(data=f"Teams:\n{self._format_teams(teams)}")
        
        elif action == "create":
            name = args.get("name", "New Team")
            return ToolResult(data=f"Created team: {name}")
        
        elif action == "delete":
            team_id = args.get("team_id", "")
            return ToolResult(data=f"Deleted team: {team_id}")
        
        elif action == "invite":
            team_id = args.get("team_id", "")
            members = args.get("members", [])
            return ToolResult(data=f"Invited {len(members)} to team {team_id}")
        
        return ToolResult(data="Unknown action")
    
    def _format_teams(self, teams: List[Dict]) -> str:
        """Format teams list."""
        lines = []
        for t in teams:
            lines.append(f"- {t['name']} ({t['id']}): {t['members']} members")
        return "\n".join(lines)


# Tool registration
_team_tool: Optional[TeamTool] = None


def get_team_tool() -> TeamTool:
    """Get global team tool."""
    global _team_tool
    if _team_tool is None:
        _team_tool = TeamTool()
    return _team_tool


__all__ = [
    "TeamInput",
    "TeamTool",
    "get_team_tool",
]

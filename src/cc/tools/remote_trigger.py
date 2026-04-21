"""Remote Trigger Tool - Trigger remote workflows."""

from __future__ import annotations
import json
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult, ToolUseContext


class RemoteTriggerInput(BaseModel):
    """Input for RemoteTriggerTool."""
    action: str = Field(description="Action: list, get, create, update, run")
    trigger_id: Optional[str] = Field(default=None, description="Trigger ID")
    body: Optional[Dict[str, Any]] = Field(default=None, description="Request body for create/update/run")
    endpoint: Optional[str] = Field(default=None, description="Custom endpoint URL")


class RemoteTriggerTool(ToolDef):
    """Tool for triggering remote workflows."""

    name = "RemoteTrigger"
    description = "Trigger remote Claude Code workflows and triggers"
    input_schema = RemoteTriggerInput

    # Simulated trigger registry
    _triggers: Dict[str, Dict[str, Any]] = {
        "build_check": {
            "id": "build_check",
            "name": "Build Verification",
            "description": "Trigger build verification workflow",
            "enabled": True,
        },
        "deploy_preview": {
            "id": "deploy_preview",
            "name": "Deploy Preview",
            "description": "Trigger preview deployment",
            "enabled": True,
        },
        "test_suite": {
            "id": "test_suite",
            "name": "Test Suite",
            "description": "Trigger full test suite",
            "enabled": True,
        },
    }

    async def execute(self, input: RemoteTriggerInput, ctx: Optional[ToolUseContext] = None) -> ToolResult:
        """Execute remote trigger operation."""
        action = input.action

        if action == "list":
            return self._list_triggers()
        elif action == "get":
            return self._get_trigger(input.trigger_id)
        elif action == "create":
            return self._create_trigger(input.body or {})
        elif action == "update":
            return self._update_trigger(input.trigger_id, input.body or {})
        elif action == "run":
            return self._run_trigger(input.trigger_id, input.body)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True
            )

    def _list_triggers(self) -> ToolResult:
        """List available triggers."""
        triggers = list(self._triggers.values())
        lines = ["Available Triggers:"]
        for t in triggers:
            status = "✓" if t.get("enabled") else "✗"
            lines.append(f"  [{status}] {t['id']}: {t['name']}")

        return ToolResult(
            content="\n".join(lines),
            metadata={"count": len(triggers)}
        )

    def _get_trigger(self, trigger_id: Optional[str]) -> ToolResult:
        """Get trigger details."""
        if not trigger_id:
            return ToolResult(
                content="trigger_id required for get action",
                is_error=True
            )

        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return ToolResult(
                content=f"Trigger not found: {trigger_id}",
                is_error=True
            )

        return ToolResult(
            content=json.dumps(trigger, indent=2),
            metadata={"trigger_id": trigger_id}
        )

    def _create_trigger(self, body: Dict[str, Any]) -> ToolResult:
        """Create new trigger."""
        trigger_id = body.get("id", f"trigger_{len(self._triggers) + 1}")
        trigger = {
            "id": trigger_id,
            "name": body.get("name", trigger_id),
            "description": body.get("description", ""),
            "enabled": body.get("enabled", True),
            "created_at": "now",
        }

        self._triggers[trigger_id] = trigger

        return ToolResult(
            content=f"Trigger created: {trigger_id}",
            metadata={"trigger": trigger}
        )

    def _update_trigger(self, trigger_id: Optional[str], body: Dict[str, Any]) -> ToolResult:
        """Update trigger."""
        if not trigger_id:
            return ToolResult(
                content="trigger_id required for update action",
                is_error=True
            )

        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return ToolResult(
                content=f"Trigger not found: {trigger_id}",
                is_error=True
            )

        for key, value in body.items():
            trigger[key] = value

        return ToolResult(
            content=f"Trigger updated: {trigger_id}",
            metadata={"trigger": trigger}
        )

    def _run_trigger(self, trigger_id: Optional[str], body: Optional[Dict[str, Any]]) -> ToolResult:
        """Run trigger."""
        if not trigger_id:
            return ToolResult(
                content="trigger_id required for run action",
                is_error=True
            )

        trigger = self._triggers.get(trigger_id)
        if not trigger:
            return ToolResult(
                content=f"Trigger not found: {trigger_id}",
                is_error=True
            )

        if not trigger.get("enabled"):
            return ToolResult(
                content=f"Trigger disabled: {trigger_id}",
                is_error=True
            )

        # Simulate trigger execution
        result = {
            "trigger_id": trigger_id,
            "status": "completed",
            "message": f"Trigger '{trigger['name']}' executed successfully",
            "params": body or {},
            "timestamp": "now",
        }

        return ToolResult(
            content=f"Trigger executed: {trigger_id}\n{json.dumps(result, indent=2)}",
            metadata={"result": result}
        )


__all__ = ["RemoteTriggerTool", "RemoteTriggerInput"]
"""Wizard Tool - Step-by-step wizard operations."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


class WizardState(Enum):
    """Wizard states."""
    START = "start"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    CANCELLED = "cancelled"


@dataclass
class WizardStep:
    """Wizard step."""
    id: str
    title: str
    description: str
    fields: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class WizardInput(ToolInput):
    """Wizard input schema."""
    wizard_type: str = "init"
    step: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)


class WizardTool(ToolDef):
    """Tool for wizard operations."""
    
    name = "Wizard"
    input_schema = WizardInput
    
    def __init__(self):
        self._wizards: Dict[str, Dict[str, Any]] = {}
        self._current_wizard: Optional[str] = None
        self._current_step: int = 0
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Execute wizard operation."""
        wizard_type = args.get("wizard_type", "init")
        step = args.get("step")
        data = args.get("data", {})
        
        if wizard_type == "init":
            return await self._start_init_wizard()
        
        elif wizard_type == "setup":
            return await self._start_setup_wizard()
        
        elif step:
            return await self._process_step(wizard_type, step, data)
        
        return ToolResult(data="Unknown wizard type")
    
    async def _start_init_wizard(self) -> ToolResult:
        """Start init wizard."""
        steps = [
            WizardStep(id="1", title="Project Name", description="Enter project name", fields=["name"]),
            WizardStep(id="2", title="Description", description="Project description", fields=["description"]),
            WizardStep(id="3", title="Language", description="Primary language", fields=["language"]),
        ]
        
        self._wizards["init"] = {"steps": steps, "data": {}, "state": WizardState.START}
        self._current_wizard = "init"
        
        return ToolResult(data=self._format_wizard_start("Init Wizard", steps))
    
    async def _start_setup_wizard(self) -> ToolResult:
        """Start setup wizard."""
        steps = [
            WizardStep(id="1", title="API Key", description="Anthropic API key", fields=["api_key"]),
            WizardStep(id="2", title="Default Model", description="Default model selection", fields=["model"]),
        ]
        
        self._wizards["setup"] = {"steps": steps, "data": {}, "state": WizardState.START}
        self._current_wizard = "setup"
        
        return ToolResult(data=self._format_wizard_start("Setup Wizard", steps))
    
    async def _process_step(self, wizard_type: str, step_id: str, data: Dict) -> ToolResult:
        """Process wizard step."""
        wizard = self._wizards.get(wizard_type)
        
        if not wizard:
            return ToolResult(data="Wizard not found")
        
        # Store data
        wizard["data"].update(data)
        
        # Find current step
        steps = wizard["steps"]
        step_idx = next(
            (i for i, s in enumerate(steps) if s.id == step_id),
            -1
        )
        
        if step_idx < 0:
            return ToolResult(data="Invalid step")
        
        # Check if complete
        if step_idx >= len(steps) - 1:
            wizard["state"] = WizardState.COMPLETE
            return ToolResult(data=f"Wizard complete!\nData: {wizard['data']}")
        
        # Return next step
        next_step = steps[step_idx + 1]
        return ToolResult(data=f"Step: {next_step.title}\n{next_step.description}")
    
    def _format_wizard_start(self, name: str, steps: List[WizardStep]) -> str:
        """Format wizard start message."""
        lines = [f"## {name}", "", "Steps:"]
        for i, s in enumerate(steps, 1):
            lines.append(f"{i}. {s.title}: {s.description}")
        return "\n".join(lines)
    
    def get_wizard(self, wizard_type: str) -> Optional[Dict]:
        """Get wizard data."""
        return self._wizards.get(wizard_type)
    
    def cancel(self, wizard_type: str) -> bool:
        """Cancel wizard."""
        if wizard_type in self._wizards:
            self._wizards[wizard_type]["state"] = WizardState.CANCELLED
            return True
        return False


__all__ = [
    "WizardState",
    "WizardStep",
    "WizardInput",
    "WizardTool",
]

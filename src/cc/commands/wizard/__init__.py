"""Commands Wizard - Interactive setup wizards."""

from __future__ import annotations
import json
from typing import Dict, Any, List, Optional, Callable
from pathlib import Path
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class WizardStep(Enum):
    """Wizard step types."""
    INTRO = "intro"
    QUESTION = "question"
    CONFIRM = "confirm"
    ACTION = "action"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class WizardQuestion:
    """Wizard question."""
    id: str
    text: str
    type: str = "text"  # text, choice, boolean, path
    default: Optional[str] = None
    options: List[str] = field(default_factory=list)
    required: bool = True


@dataclass
class WizardAnswer:
    """Wizard answer."""
    question_id: str
    value: Any


@dataclass
class WizardState:
    """Wizard state."""
    step: WizardStep
    step_index: int
    answers: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class Wizard:
    """Base wizard class."""

    def __init__(self, name: str):
        self.name = name
        self._questions: List[WizardQuestion] = []
        self._state = WizardState(
            step=WizardStep.INTRO,
            step_index=0,
        )
        self._callbacks: Dict[str, Callable] = {}

    def add_question(self, question: WizardQuestion) -> None:
        """Add question."""
        self._questions.append(question)

    def add_callback(self, event: str, callback: Callable) -> None:
        """Add event callback."""
        self._callbacks[event] = callback

    def get_current_question(self) -> Optional[WizardQuestion]:
        """Get current question."""
        if self._state.step_index < len(self._questions):
            return self._questions[self._state.step_index]
        return None

    async def answer(self, value: Any) -> Dict[str, Any]:
        """Process answer."""
        question = self.get_current_question()
        if not question:
            return {"error": "No current question"}

        # Validate
        if question.required and not value:
            self._state.errors.append(f"{question.id} is required")
            return {"error": "Required field missing"}

        # Store answer
        self._state.answers[question.id] = value
        self._state.step_index += 1

        # Check for more questions
        if self._state.step_index >= len(self._questions):
            self._state.step = WizardStep.COMPLETE
            await self._on_complete()

        return {
            "step": self._state.step.value,
            "progress": self._state.step_index,
            "total": len(self._questions),
        }

    async def skip(self) -> Dict[str, Any]:
        """Skip current question."""
        question = self.get_current_question()
        if not question:
            return {"error": "No current question"}

        if question.required:
            return {"error": "Cannot skip required question"}

        self._state.step_index += 1

        if self._state.step_index >= len(self._questions):
            self._state.step = WizardStep.COMPLETE
            await self._on_complete()

        return {
            "step": self._state.step.value,
            "progress": self._state.step_index,
            "total": len(self._questions),
        }

    async def back(self) -> Dict[str, Any]:
        """Go back."""
        if self._state.step_index > 0:
            self._state.step_index -= 1
            self._state.step = WizardStep.QUESTION

        return {
            "step": self._state.step.value,
            "progress": self._state.step_index,
            "total": len(self._questions),
        }

    async def _on_complete(self) -> None:
        """Handle completion."""
        if "complete" in self._callbacks:
            await self._callbacks["complete"](self._state.answers)

    def get_state(self) -> WizardState:
        """Get wizard state."""
        return self._state

    def get_answers(self) -> Dict[str, Any]:
        """Get all answers."""
        return self._state.answers


class InitWizard(Wizard):
    """Initialize project wizard."""

    async def run(self, cwd: Path) -> Dict[str, Any]:
        """Run init wizard."""
        steps = [
            self._detect_project_type,
            self._create_claude_md,
            self._setup_permissions,
            self._setup_hooks,
        ]

        results = {}
        for step in steps:
            result = await step(cwd)
            results.update(result)

        return results

    async def _detect_project_type(self, cwd: Path) -> Dict[str, Any]:
        """Detect project type."""
        indicators = {
            "python": ["pyproject.toml", "setup.py", "requirements.txt"],
            "node": ["package.json", "tsconfig.json"],
            "rust": ["Cargo.toml"],
            "go": ["go.mod"],
            "java": ["pom.xml", "build.gradle"],
        }

        detected = "unknown"
        for type_name, files in indicators.items():
            for f in files:
                if (cwd / f).exists():
                    detected = type_name
                    break

        return {"project_type": detected}

    async def _create_claude_md(self, cwd: Path) -> Dict[str, Any]:
        """Create CLAUDE.md."""
        claude_md = cwd / "CLAUDE.md"

        if claude_md.exists():
            return {"claude_md": "exists"}

        content = """# Project Context

## Overview
Describe your project here.

## Architecture
- Key components and their relationships

## Commands
- How to build: `npm run build`
- How to test: `npm test`

## Guidelines
- Code style preferences
- Testing requirements
"""

        import aiofiles
        async with aiofiles.open(claude_md, "w") as f:
            await f.write(content)

        return {"claude_md": "created"}

    async def _setup_permissions(self, cwd: Path) -> Dict[str, Any]:
        """Setup default permissions."""
        settings = cwd / ".claude" / "settings.json"

        if settings.exists():
            return {"permissions": "exists"}

        settings.parent.mkdir(exist_ok=True)

        config = {
            "permissions": {
                "allow": ["Read", "Glob", "Grep"],
                "deny": [],
                "ask": ["Write", "Edit", "Bash"],
            }
        }

        import aiofiles
        async with aiofiles.open(settings, "w") as f:
            await f.write(json.dumps(config, indent=2))

        return {"permissions": "created"}

    async def _setup_hooks(self, cwd: Path) -> Dict[str, Any]:
        """Setup hooks directory."""
        hooks_dir = cwd / ".claude" / "hooks"
        hooks_dir.mkdir(exist_ok=True)

        return {"hooks": "created"}


class SetupWizard(Wizard):
    """Settings setup wizard."""

    def __init__(self):
        super().__init__("setup")

        self.add_question(WizardQuestion(
            id="model",
            text="Default model?",
            type="choice",
            options=["claude-opus-4-7", "claude-sonnet-4-6", "claude-haiku-4-5"],
            default="claude-sonnet-4-6",
        ))

        self.add_question(WizardQuestion(
            id="theme",
            text="UI theme?",
            type="choice",
            options=["dark", "light", "mono", "gruvbox"],
            default="dark",
        ))

        self.add_question(WizardQuestion(
            id="vim_mode",
            text="Enable vim mode?",
            type="boolean",
            default="false",
        ))

        self.add_question(WizardQuestion(
            id="output_style",
            text="Output style?",
            type="choice",
            options=["explanatory", "concise", "minimal"],
            default="explanatory",
        ))

    async def run(self, cwd: Path) -> Dict[str, Any]:
        """Run setup wizard."""
        return {
            "model": "claude-sonnet-4-6",
            "theme": "dark",
            "vim_mode": False,
            "output_style": "explanatory",
        }


__all__ = [
    "WizardStep",
    "WizardQuestion",
    "WizardAnswer",
    "WizardState",
    "Wizard",
    "InitWizard",
    "SetupWizard",
]
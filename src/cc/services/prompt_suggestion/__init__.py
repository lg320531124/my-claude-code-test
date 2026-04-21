"""Prompt Suggestion - Suggest prompts to user."""

from __future__ import annotations
import random
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from ...utils.log import get_logger

logger = get_logger(__name__)


class SuggestionType(Enum):
    """Suggestion types."""
    TASK = "task"
    QUESTION = "question"
    COMMAND = "command"
    CONTEXT = "context"
    LEARNING = "learning"
    FOLLOW_UP = "follow_up"


class SuggestionPriority(Enum):
    """Suggestion priority."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class PromptSuggestion:
    """Prompt suggestion."""
    text: str
    type: SuggestionType
    priority: SuggestionPriority
    context: str = ""
    confidence: float = 0.8
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuggestionConfig:
    """Suggestion configuration."""
    max_suggestions: int = 10
    min_confidence: float = 0.5
    include_context: bool = True
    diversity_factor: float = 0.3
    history_weight: float = 0.2


@dataclass
class ContextInfo:
    """Context information."""
    recent_files: List[str] = field(default_factory=list)
    recent_commands: List[str] = field(default_factory=list)
    current_project: str = ""
    recent_topics: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


class PromptSuggester:
    """Suggest prompts to user."""

    def __init__(self, config: Optional[SuggestionConfig] = None):
        self.config = config or SuggestionConfig()
        self._templates: Dict[SuggestionType, List[str]] = self._load_templates()
        self._history: List[str] = []
        self._context: Optional[ContextInfo] = None

    def _load_templates(self) -> Dict[SuggestionType, List[str]]:
        """Load suggestion templates."""
        return {
            SuggestionType.TASK: [
                "Analyze the code in {file}",
                "Review the changes in {project}",
                "Fix the error in {file}",
                "Implement {feature}",
                "Optimize {component}",
            ],
            SuggestionType.QUESTION: [
                "What does {function} do?",
                "How is {module} structured?",
                "Why was {change} made?",
                "Where is {symbol} defined?",
            ],
            SuggestionType.COMMAND: [
                "/commit",
                "/review",
                "/doctor",
                "/compact",
                "/init",
            ],
            SuggestionType.CONTEXT: [
                "Explain the architecture of {project}",
                "Describe the flow of {process}",
                "Summarize recent changes",
            ],
            SuggestionType.LEARNING: [
                "Teach me about {topic}",
                "Explain {concept}",
                "Show best practices for {area}",
            ],
            SuggestionType.FOLLOW_UP: [
                "Continue the previous task",
                "Review the last change",
                "Test the implementation",
            ],
        }

    async def suggest(
        self,
        context: Optional[ContextInfo] = None,
        limit: Optional[int] = None
    ) -> List[PromptSuggestion]:
        """Generate suggestions."""
        self._context = context or ContextInfo()

        suggestions = []

        # Task suggestions
        task_suggestions = await self._suggest_tasks()
        suggestions.extend(task_suggestions)

        # Question suggestions
        question_suggestions = await self._suggest_questions()
        suggestions.extend(question_suggestions)

        # Command suggestions
        command_suggestions = await self._suggest_commands()
        suggestions.extend(command_suggestions)

        # Context suggestions
        context_suggestions = await self._suggest_context()
        suggestions.extend(context_suggestions)

        # Follow-up suggestions
        follow_up_suggestions = await self._suggest_follow_up()
        suggestions.extend(follow_up_suggestions)

        # Filter by confidence
        suggestions = [
            s for s in suggestions
            if s.confidence >= self.config.min_confidence
        ]

        # Add diversity
        suggestions = self._add_diversity(suggestions)

        # Sort by priority
        priority_order = {
            SuggestionPriority.HIGH: 0,
            SuggestionPriority.MEDIUM: 1,
            SuggestionPriority.LOW: 2,
        }
        suggestions.sort(key=lambda s: priority_order.get(s.priority, 1))

        # Limit
        use_limit = limit or self.config.max_suggestions
        suggestions = suggestions[:use_limit]

        return suggestions

    async def _suggest_tasks(self) -> List[PromptSuggestion]:
        """Suggest tasks."""
        suggestions = []

        # Based on recent files
        for file in self._context.recent_files[:3]:
            template = random.choice(self._templates[SuggestionType.TASK])
            text = template.replace("{file}", file)

            suggestions.append(PromptSuggestion(
                text=text,
                type=SuggestionType.TASK,
                priority=SuggestionPriority.HIGH,
                confidence=0.85,
                context=f"Recent file: {file}",
            ))

        # Based on errors
        for error in self._context.errors[:2]:
            suggestions.append(PromptSuggestion(
                text=f"Fix error: {error[:50]}",
                type=SuggestionType.TASK,
                priority=SuggestionPriority.HIGH,
                confidence=0.9,
                context="Error detected",
            ))

        return suggestions

    async def _suggest_questions(self) -> List[PromptSuggestion]:
        """Suggest questions."""
        suggestions = []

        if self._context.recent_topics:
            topic = self._context.recent_topics[0]
            template = random.choice(self._templates[SuggestionType.QUESTION])
            text = template.replace("{topic}", topic)

            suggestions.append(PromptSuggestion(
                text=text,
                type=SuggestionType.QUESTION,
                priority=SuggestionPriority.MEDIUM,
                confidence=0.7,
                context=f"Topic: {topic}",
            ))

        return suggestions

    async def _suggest_commands(self) -> List[PromptSuggestion]:
        """Suggest commands."""
        suggestions = []

        # Popular commands
        popular_commands = self._templates[SuggestionType.COMMAND][:3]

        for cmd in popular_commands:
            suggestions.append(PromptSuggestion(
                text=cmd,
                type=SuggestionType.COMMAND,
                priority=SuggestionPriority.MEDIUM,
                confidence=0.75,
                context="Available command",
            ))

        return suggestions

    async def _suggest_context(self) -> List[PromptSuggestion]:
        """Suggest context."""
        suggestions = []

        if self._context.current_project:
            template = random.choice(self._templates[SuggestionType.CONTEXT])
            text = template.replace("{project}", self._context.current_project)

            suggestions.append(PromptSuggestion(
                text=text,
                type=SuggestionType.CONTEXT,
                priority=SuggestionPriority.LOW,
                confidence=0.6,
                context=f"Project: {self._context.current_project}",
            ))

        return suggestions

    async def _suggest_follow_up(self) -> List[PromptSuggestion]:
        """Suggest follow-up."""
        suggestions = []

        if self._history:
            last_prompt = self._history[-1]

            suggestions.append(PromptSuggestion(
                text="Continue the previous task",
                type=SuggestionType.FOLLOW_UP,
                priority=SuggestionPriority.HIGH,
                confidence=0.8,
                context=f"Last: {last_prompt[:50]}",
            ))

        return suggestions

    def _add_diversity(
        self,
        suggestions: List[PromptSuggestion]
    ) -> List[PromptSuggestion]:
        """Add diversity to suggestions."""
        if not suggestions:
            return suggestions

        # Group by type
        by_type: Dict[SuggestionType, List[PromptSuggestion]] = {}

        for s in suggestions:
            if s.type not in by_type:
                by_type[s.type] = []
            by_type[s.type].append(s)

        # Select from each type
        diverse = []

        for type, type_suggestions in by_type.items():
            # Take top suggestion from each type
            if type_suggestions:
                diverse.append(type_suggestions[0])

        # Fill remaining
        remaining = [s for s in suggestions if s not in diverse]
        diverse.extend(remaining)

        return diverse

    async def add_to_history(self, prompt: str) -> None:
        """Add to history."""
        self._history.append(prompt)

        # Trim history
        if len(self._history) > 100:
            self._history = self._history[-100:]

    async def get_history(self) -> List[str]:
        """Get history."""
        return self._history

    async def update_context(
        self,
        files: Optional[List[str]] = None,
        commands: Optional[List[str]] = None,
        project: Optional[str] = None,
        topics: Optional[List[str]] = None,
        errors: Optional[List[str]] = None
    ) -> None:
        """Update context."""
        # Create context if not exists
        if self._context is None:
            self._context = ContextInfo()

        if files:
            self._context.recent_files = files
        if commands:
            self._context.recent_commands = commands
        if project:
            self._context.current_project = project
        if topics:
            self._context.recent_topics = topics
        if errors:
            self._context.errors = errors

    async def suggest_next_action(
        self,
        last_result: Dict[str, Any]
    ) -> Optional[PromptSuggestion]:
        """Suggest next action based on last result."""
        if last_result.get("error"):
            return PromptSuggestion(
                text="Fix the error and retry",
                type=SuggestionType.FOLLOW_UP,
                priority=SuggestionPriority.HIGH,
                confidence=0.9,
            )

        if last_result.get("success"):
            return PromptSuggestion(
                text="Review the changes made",
                type=SuggestionType.FOLLOW_UP,
                priority=SuggestionPriority.MEDIUM,
                confidence=0.8,
            )

        return None

    async def suggest_for_file(
        self,
        file_path: Path
    ) -> List[PromptSuggestion]:
        """Suggest for specific file."""
        suggestions = []

        file_name = file_path.name

        suggestions.append(PromptSuggestion(
            text=f"Review {file_name}",
            type=SuggestionType.TASK,
            priority=SuggestionPriority.HIGH,
            confidence=0.85,
            context=f"File: {file_path}",
        ))

        suggestions.append(PromptSuggestion(
            text=f"Explain {file_name}",
            type=SuggestionType.QUESTION,
            priority=SuggestionPriority.MEDIUM,
            confidence=0.75,
            context=f"File: {file_path}",
        ))

        return suggestions


__all__ = [
    "SuggestionType",
    "SuggestionPriority",
    "PromptSuggestion",
    "SuggestionConfig",
    "ContextInfo",
    "PromptSuggester",
]
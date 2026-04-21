"""Prompt Suggestions - Async prompt suggestion service."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class SuggestionType(Enum):
    """Suggestion types."""
    CONTEXT = "context"
    FIX = "fix"
    EXPLAIN = "explain"
    GENERATE = "generate"
    TEST = "test"
    REFACTOR = "refactor"
    DOCUMENT = "document"


@dataclass
class PromptSuggestion:
    """Prompt suggestion."""
    id: str
    type: SuggestionType
    text: str
    context: str
    priority: int = 0
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SuggestionContext:
    """Context for suggestions."""
    cwd: str = ""
    recent_files: List[str] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    git_status: str = ""
    language: str = ""
    task_type: str = ""


class PromptSuggestionService:
    """Async prompt suggestion service."""

    def __init__(self):
        self._templates: Dict[SuggestionType, List[str]] = {}
        self._context_patterns: Dict[str, SuggestionType] = {}
        self._history: List[str] = []
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default suggestion templates."""
        self._templates = {
            SuggestionType.FIX: [
                "Fix the error in {file}: {error}",
                "Debug why {error} is occurring",
                "Resolve the {language} error: {error}",
            ],
            SuggestionType.EXPLAIN: [
                "Explain how {file} works",
                "What does the {function} function do?",
                "Explain the code at line {line} in {file}",
            ],
            SuggestionType.GENERATE: [
                "Generate a {type} for {context}",
                "Create {thing} based on {pattern}",
                "Write {type} code for {feature}",
            ],
            SuggestionType.TEST: [
                "Write tests for {file}",
                "Add test coverage for {function}",
                "Generate unit tests for {module}",
            ],
            SuggestionType.REFACTOR: [
                "Refactor {file} to improve {aspect}",
                "Simplify the code in {function}",
                "Optimize {module} for better performance",
            ],
            SuggestionType.DOCUMENT: [
                "Add documentation to {file}",
                "Generate docstrings for {function}",
                "Write README for {project}",
            ],
            SuggestionType.CONTEXT: [
                "What is the current state of {project}?",
                "Show me recent changes in {branch}",
                "Explain the architecture of {module}",
            ],
        }

        self._context_patterns = {
            "error": SuggestionType.FIX,
            "bug": SuggestionType.FIX,
            "fail": SuggestionType.FIX,
            "explain": SuggestionType.EXPLAIN,
            "what": SuggestionType.EXPLAIN,
            "how": SuggestionType.EXPLAIN,
            "create": SuggestionType.GENERATE,
            "generate": SuggestionType.GENERATE,
            "write": SuggestionType.GENERATE,
            "test": SuggestionType.TEST,
            "refactor": SuggestionType.REFACTOR,
            "optimize": SuggestionType.REFACTOR,
            "document": SuggestionType.DOCUMENT,
        }

    async def get_suggestions(
        self,
        context: SuggestionContext,
        user_input: str = "",
        limit: int = 5,
    ) -> List[PromptSuggestion]:
        """Get prompt suggestions."""
        suggestions = []

        # Analyze context
        suggested_types = await self._analyze_context(context, user_input)

        for suggestion_type in suggested_types:
            templates = self._templates.get(suggestion_type, [])

            for template in templates[:2]:  # Top 2 templates per type
                text = self._fill_template(template, context)

                suggestion = PromptSuggestion(
                    id=hashlib.md5(text.encode()).hexdigest()[:8] if hashlib else str(len(suggestions)),
                    type=suggestion_type,
                    text=text,
                    context=str(context),
                    priority=suggested_types.index(suggestion_type),
                    confidence=0.8,
                )

                suggestions.append(suggestion)

        # Sort by priority
        suggestions.sort(key=lambda s: s.priority)

        return suggestions[:limit]

    async def _analyze_context(
        self,
        context: SuggestionContext,
        user_input: str,
    ) -> List[SuggestionType]:
        """Analyze context to determine suggestion types."""
        types = []

        # Check for errors
        if context.recent_errors:
            types.append(SuggestionType.FIX)

        # Check recent files
        if context.recent_files:
            types.append(SuggestionType.EXPLAIN)
            types.append(SuggestionType.TEST)

        # Check git status
        if context.git_status and "modified" in context.git_status:
            types.append(SuggestionType.REFACTOR)
            types.append(SuggestionType.DOCUMENT)

        # Check user input patterns
        input_lower = user_input.lower()

        for pattern, suggestion_type in self._context_patterns.items():
            if pattern in input_lower:
                if suggestion_type not in types:
                    types.insert(0, suggestion_type)

        # Default suggestions
        if not types:
            types = [
                SuggestionType.CONTEXT,
                SuggestionType.EXPLAIN,
                SuggestionType.TEST,
            ]

        return types

    def _fill_template(
        self,
        template: str,
        context: SuggestionContext,
    ) -> str:
        """Fill template with context."""
        # Replace placeholders
        result = template

        result = result.replace("{cwd}", context.cwd)
        result = result.replace("{file}", context.recent_files[0] if context.recent_files else "file")
        result = result.replace("{error}", context.recent_errors[0] if context.recent_errors else "error")
        result = result.replace("{language}", context.language or "code")
        result = result.replace("{project}", Path(context.cwd).name if context.cwd else "project")

        return result

    async def learn_from_usage(self, prompt: str, was_useful: bool) -> None:
        """Learn from user's prompt usage."""
        self._history.append(prompt)

        # Would adjust confidence based on usage patterns
        pass

    async def get_quick_suggestions(self) -> List[str]:
        """Get quick suggestion prompts."""
        return [
            "Fix the current error",
            "Explain this code",
            "Write tests",
            "Refactor this",
            "Add documentation",
            "What changed recently?",
        ]


import hashlib


# Global service
_service: Optional[PromptSuggestionService] = None


def get_suggestion_service() -> PromptSuggestionService:
    """Get global suggestion service."""
    global _service
    if _service is None:
        _service = PromptSuggestionService()
    return _service


__all__ = [
    "SuggestionType",
    "PromptSuggestion",
    "SuggestionContext",
    "PromptSuggestionService",
    "get_suggestion_service",
]
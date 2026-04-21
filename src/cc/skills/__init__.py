"""Skills Module - Built-in skill definitions.

Provides skill registration, discovery, and execution:
- Skill registry
- Skill loading
- Skill execution
- Skill documentation
"""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, field
from enum import Enum


class SkillType(Enum):
    """Skill types."""
    COMMAND = "command"
    AGENT = "agent"
    WORKFLOW = "workflow"
    TEMPLATE = "template"
    PLUGIN = "plugin"


@dataclass
class Skill:
    """Skill definition."""
    name: str
    description: str
    skill_type: SkillType
    handler: Optional[Callable] = None
    args_schema: Dict[str, Any] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    category: str = "general"
    version: str = "1.0"
    enabled: bool = True
    requires: List[str] = field(default_factory=list)  # Required tools/services
    priority: int = 0


@dataclass
class SkillContext:
    """Skill execution context."""
    args: Dict[str, Any] = field(default_factory=dict)
    session_id: str = ""
    cwd: Path = field(default_factory=Path.cwd)
    config: Dict[str, Any] = field(default_factory=dict)
    tools: List[str] = field(default_factory=list)


class SkillRegistry:
    """Skill registry and manager."""

    def __init__(self):
        self._skills: Dict[str, Skill] = {}
        self._categories: Dict[str, List[str]] = {}
        self._aliases: Dict[str, str] = {}
        self._listeners: List[Callable] = []

    def register(self, skill: Skill) -> None:
        """Register skill."""
        self._skills[skill.name] = skill

        # Add to category
        if skill.category not in self._categories:
            self._categories[skill.category] = []
        self._categories[skill.category].append(skill.name)

        # Notify listeners
        for listener in self._listeners:
            listener("registered", skill)

    def unregister(self, name: str) -> bool:
        """Unregister skill."""
        if name not in self._skills:
            return False

        skill = self._skills.pop(name)
        self._categories[skill.category].remove(name)

        # Remove aliases
        aliases_to_remove = [k for k, v in self._aliases.items() if v == name]
        for alias in aliases_to_remove:
            self._aliases.pop(alias)

        for listener in self._listeners:
            listener("unregistered", skill)

        return True

    def add_alias(self, alias: str, skill_name: str) -> None:
        """Add skill alias."""
        if skill_name in self._skills:
            self._aliases[alias] = skill_name

    def get(self, name: str) -> Optional[Skill]:
        """Get skill by name or alias."""
        # Check alias
        if name in self._aliases:
            name = self._aliases[name]
        return self._skills.get(name)

    def list(self, category: str = None, enabled_only: bool = True) -> List[Skill]:
        """List skills."""
        skills = []
        for skill in self._skills.values():
            if enabled_only and not skill.enabled:
                continue
            if category and skill.category != category:
                continue
            skills.append(skill)
        return sorted(skills, key=lambda s: s.priority)

    def list_categories(self) -> List[str]:
        """List categories."""
        return list(self._categories.keys())

    def search(self, query: str) -> List[Skill]:
        """Search skills."""
        query_lower = query.lower()
        results = []
        for skill in self._skills.values():
            if query_lower in skill.name.lower() or query_lower in skill.description.lower():
                results.append(skill)
        return results

    async def execute(self, name: str, context: SkillContext) -> Any:
        """Execute skill."""
        skill = self.get(name)
        if not skill:
            raise ValueError(f"Skill not found: {name}")

        if not skill.enabled:
            raise ValueError(f"Skill disabled: {name}")

        if skill.handler:
            if asyncio.iscoroutinefunction(skill.handler):
                return await skill.handler(context)
            else:
                return skill.handler(context)

        raise ValueError(f"Skill has no handler: {name}")

    def subscribe(self, listener: Callable) -> Callable:
        """Subscribe to skill events."""
        self._listeners.append(listener)
        return lambda: self._listeners.remove(listener)

    def to_dict(self) -> Dict[str, Any]:
        """Export registry."""
        return {
            "skills": {k: {
                "name": v.name,
                "description": v.description,
                "type": v.skill_type.value,
                "category": v.category,
                "version": v.version,
                "enabled": v.enabled,
                "examples": v.examples,
            } for k, v in self._skills.items()},
            "categories": self._categories,
            "aliases": self._aliases,
        }


# Built-in skills
BUILTIN_SKILLS = [
    Skill(
        name="fewer-permission-prompts",
        description="Analyze transcript and suggest permission allowlist entries",
        skill_type=SkillType.WORKFLOW,
        category="permissions",
        examples=["fewer-permission-prompts"],
    ),
    Skill(
        name="brainstorming",
        description="Structured brainstorming for complex features",
        skill_type=SkillType.WORKFLOW,
        category="planning",
        examples=["brainstorming", "brainstorming feature X"],
    ),
    Skill(
        name="tdd",
        description="Test-driven development workflow",
        skill_type=SkillType.WORKFLOW,
        category="development",
        examples=["tdd", "tdd for authentication"],
    ),
    Skill(
        name="frontend-design",
        description="Frontend component design patterns",
        skill_type=SkillType.WORKFLOW,
        category="frontend",
        examples=["frontend-design", "frontend-design login form"],
    ),
    Skill(
        name="debugging",
        description="Systematic debugging workflow",
        skill_type=SkillType.WORKFLOW,
        category="debugging",
        examples=["debugging", "debugging connection error"],
    ),
    Skill(
        name="security-review",
        description="Security vulnerability review",
        skill_type=SkillType.WORKFLOW,
        category="security",
        examples=["security-review", "security-review auth module"],
    ),
    Skill(
        name="mcp-builder",
        description="Build MCP servers",
        skill_type=SkillType.WORKFLOW,
        category="mcp",
        examples=["mcp-builder", "mcp-builder slack integration"],
    ),
    Skill(
        name="git-workflow",
        description="Git workflow and commit patterns",
        skill_type=SkillType.WORKFLOW,
        category="git",
        examples=["git-workflow", "git-workflow pr creation"],
    ),
    Skill(
        name="code-review",
        description="Code review checklist and process",
        skill_type=SkillType.WORKFLOW,
        category="review",
        examples=["code-review", "code-review PR #123"],
    ),
    Skill(
        name="refactoring",
        description="Refactoring patterns and strategies",
        skill_type=SkillType.WORKFLOW,
        category="refactor",
        examples=["refactoring", "refactoring api layer"],
    ),
]


# Global registry
_registry: Optional[SkillRegistry] = None


def get_skill_registry() -> SkillRegistry:
    """Get global registry."""
    global _registry
    if _registry is None:
        _registry = SkillRegistry()
        # Register built-in skills
        for skill in BUILTIN_SKILLS:
            _registry.register(skill)
    return _registry


async def execute_skill(name: str, args: Dict[str, Any] = None) -> Any:
    """Execute skill."""
    registry = get_skill_registry()
    context = SkillContext(args=args or {})
    return await registry.execute(name, context)


def list_skills() -> List[Skill]:
    """List all skills."""
    return get_skill_registry().list()


__all__ = [
    "SkillType",
    "Skill",
    "SkillContext",
    "SkillRegistry",
    "BUILTIN_SKILLS",
    "get_skill_registry",
    "execute_skill",
    "list_skills",
]
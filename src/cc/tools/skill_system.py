"""Skill System - Load, validate, and execute skills."""

from __future__ import annotations
import asyncio
import json
import time
from pathlib import Path
from typing import ClassVar, Any, Callable, Optional, List, Dict
from dataclasses import dataclass, field
from pydantic import BaseModel, ValidationError, Field


@dataclass
class SkillMetadata:
    """Skill metadata."""
    name: str
    description: str
    version: str = "1.0"
    author: str = ""
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)  # Required tools/features
    created_at: float = field(default_factory=time.time)


@dataclass
class SkillDefinition:
    """Complete skill definition."""
    metadata: SkillMetadata
    prompt: str
    examples: List[str] = field(default_factory=list)
    usage_notes: str = ""
    is_active: bool = True


class SkillValidationError(Exception):
    """Skill validation error."""
    pass


class SkillSchema(BaseModel):
    """Schema for skill validation."""
    name: str = Field(min_length=1)
    description: str = ""  # Description can be empty
    prompt: str = Field(min_length=1)
    version: str = "1.0"
    author: str = ""
    tags: List[str] = []
    requires: List[str] = []
    examples: List[str] = []
    usage_notes: str = ""


class SkillLoader:
    """Load and validate skills."""

    def __init__(self, skill_dirs: Optional[List[Path]] = None):
        self.skill_dirs = skill_dirs or [
            Path.cwd() / "skills",
            Path.home() / ".claude" / "skills",
            Path(__file__).parent.parent.parent / "skills",  # Built-in
        ]
        self.skills: Dict[str, SkillDefinition] = {}
        self._validation_errors: List[dict] = []

    async def load_all(self) -> Dict[str, SkillDefinition]:
        """Load all skills from directories."""
        for skill_dir in self.skill_dirs:
            if skill_dir.exists():
                await self._load_from_dir(skill_dir)

        return self.skills

    async def _load_from_dir(self, dir: Path) -> None:
        """Load skills from directory."""
        loop = asyncio.get_event_loop()

        for skill_file in dir.glob("*.md"):
            try:
                content = await loop.run_in_executor(None, skill_file.read_text)
                skill = self._parse_skill_file(skill_file, content)

                if skill:
                    self.skills[skill.metadata.name] = skill

            except Exception as e:
                self._validation_errors.append({
                    "file": str(skill_file),
                    "error": str(e),
                })

    def _parse_skill_file(self, path: Path, content: str) -> SkillDefinition | None:
        """Parse skill from markdown file."""
        # Strip leading whitespace
        content = content.strip()

        # Extract frontmatter
        if not content.startswith("---"):
            # No frontmatter - simple prompt file
            name = path.stem
            return SkillDefinition(
                metadata=SkillMetadata(name=name, description=content[:100]),
                prompt=content,
            )

        # Parse frontmatter
        parts = content.split("---")
        if len(parts) < 3:
            return None

        # parts[0] is empty, parts[1] is frontmatter, parts[2] is prompt (plus any remaining)
        frontmatter = parts[1].strip()
        prompt = "---".join(parts[2:]).strip()

        # Parse YAML-like frontmatter
        metadata_dict = self._parse_frontmatter(frontmatter)

        # Add prompt to metadata_dict for schema validation
        metadata_dict["prompt"] = prompt

        try:
            # Validate with schema
            schema = SkillSchema(**metadata_dict)

            metadata = SkillMetadata(
                name=schema.name,
                description=schema.description,
                version=schema.version,
                author=schema.author,
                tags=schema.tags,
                requires=schema.requires,
            )

            return SkillDefinition(
                metadata=metadata,
                prompt=schema.prompt.strip(),
                examples=schema.examples,
                usage_notes=schema.usage_notes,
            )

        except ValidationError as e:
            self._validation_errors.append({
                "file": str(path),
                "error": str(e),
            })
            return None

    def _parse_frontmatter(self, text: str) -> dict:
        """Parse YAML-like frontmatter."""
        result = {}

        for line in text.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()

                # Handle lists
                if value.startswith("[") and value.endswith("]"):
                    items = value[1:-1].split(",")
                    result[key] = [i.strip().strip('"').strip("'") for i in items if i.strip()]
                else:
                    # Remove quotes
                    value = value.strip('"').strip("'")
                    result[key] = value

        return result

    def get_skill(self, name: str) -> SkillDefinition | None:
        """Get skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[SkillMetadata]:
        """List all loaded skills."""
        return [s.metadata for s in self.skills.values()]

    def search_skills(self, query: str) -> List[SkillDefinition]:
        """Search skills."""
        results = []
        query_lower = query.lower()

        for skill in self.skills.values():
            if query_lower in skill.metadata.name.lower():
                results.append(skill)
            elif query_lower in skill.metadata.description.lower():
                results.append(skill)
            elif any(query_lower in tag.lower() for tag in skill.metadata.tags):
                results.append(skill)

        return results

    def get_errors(self) -> List[dict]:
        """Get validation errors."""
        return self._validation_errors


class SkillExecutor:
    """Execute skills."""

    def __init__(self, loader: Optional[SkillLoader] = None):
        self.loader = loader or SkillLoader()
        self._on_execute: Optional[Callable] = None
        self._execution_history: List[dict] = []

    async def execute(
        self,
        skill_name: str,
        context: dict,
        args: Optional[str] = None,
    ) -> str:
        """Execute a skill."""
        skill = self.loader.get_skill(skill_name)

        # Record execution attempt (even if skill not found)
        execution = {
            "skill": skill_name,
            "timestamp": time.time(),
            "args": args,
            "success": skill is not None,
        }
        self._execution_history.append(execution)

        if not skill:
            return f"Skill not found: {skill_name}"

        # Build prompt
        prompt = skill.prompt
        if args:
            prompt += f"\n\nArguments: {args}"

        # Add context
        prompt += f"\n\nContext:\n{json.dumps(context, indent=2)}"

        if self._on_execute:
            self._on_execute(skill_name, prompt)

        return prompt

    def get_history(self) -> List[dict]:
        """Get execution history."""
        return self._execution_history

    def set_callback(self, callback: Callable) -> None:
        """Set execution callback."""
        self._on_execute = callback


class SkillManager:
    """Manage skills system."""

    def __init__(self):
        self.loader = SkillLoader()
        self.executor = SkillExecutor(self.loader)
        self._loaded = False

    async def initialize(self) -> None:
        """Initialize skill system."""
        if self._loaded:
            return

        await self.loader.load_all()
        self._loaded = True

    async def execute_skill(self, name: str, context: dict, args: str = "") -> str:
        """Execute skill."""
        await self.initialize()
        return await self.executor.execute(name, context, args)

    def list_skills(self) -> List[dict]:
        """List skills."""
        skills = self.loader.list_skills()
        return [
            {
                "name": s.name,
                "description": s.description,
                "tags": s.tags,
            }
            for s in skills
        ]

    def get_skill_info(self, name: str) -> dict | None:
        """Get skill info."""
        skill = self.loader.get_skill(name)
        if skill:
            return {
                "name": skill.metadata.name,
                "description": skill.metadata.description,
                "prompt_preview": skill.prompt[:200],
                "examples": skill.examples,
                "usage_notes": skill.usage_notes,
            }
        return None

    def create_skill_template(self, name: str) -> str:
        """Create skill template."""
        return f'''---
name: {name}
description: Description of the skill
version: "1.0"
author: ""
tags: []
requires: []
examples: []
usage_notes: ""
---

# {name}

Your skill prompt here. This will be sent to Claude when the skill is invoked.

## Usage

Describe how to use this skill.

## Examples

Provide examples if needed.
'''

    async def reload(self) -> None:
        """Reload skills."""
        # Preserve skill_dirs from previous loader
        skill_dirs = self.loader.skill_dirs if hasattr(self.loader, 'skill_dirs') else None
        self.loader = SkillLoader(skill_dirs)
        await self.loader.load_all()
        self.executor = SkillExecutor(self.loader)


class SkillTool:
    """Skill tool for use in engine."""

    def __init__(self, manager: Optional[SkillManager] = None):
        self.manager = manager or SkillManager()

    async def execute(self, skill_name: str, context: dict, args: str = "") -> str:
        """Execute skill."""
        return await self.manager.execute_skill(skill_name, context, args)

    def get_schema(self) -> dict:
        """Get tool schema."""
        return {
            "name": "Skill",
            "description": "Execute a skill",
            "input_schema": {
                "type": "object",
                "properties": {
                    "skill_name": {"type": "string"},
                    "args": {"type": "string"},
                },
                "required": ["skill_name"],
            },
        }


# Global skill manager
_skill_manager: Optional[SkillManager] = None


def get_skill_manager() -> SkillManager:
    """Get global skill manager."""
    global _skill_manager
    if _skill_manager is None:
        _skill_manager = SkillManager()
    return _skill_manager


async def initialize_skills() -> None:
    """Initialize skills."""
    await get_skill_manager().initialize()


def list_available_skills() -> List[dict]:
    """List available skills."""
    return get_skill_manager().list_skills()

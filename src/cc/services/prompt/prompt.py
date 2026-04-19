"""Prompt Service - System prompt management."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class PromptTemplate(BaseModel):
    """Prompt template."""
    name: str
    content: str
    variables: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    category: str = "general"


class PromptConfig(BaseModel):
    """Prompt configuration."""
    templates_dir: Optional[str] = None
    default_system_prompt: str = "You are a helpful AI assistant."
    max_prompt_tokens: int = 10000


class PromptService:
    """Manage system prompts and templates."""

    def __init__(self, config: Optional[PromptConfig] = None):
        self.config = config or PromptConfig()
        self._templates: Dict[str, PromptTemplate] = {}
        self._load_default_templates()

        if self.config.templates_dir:
            self._load_templates_from_dir(Path(self.config.templates_dir))

    def _load_default_templates(self) -> None:
        """Load built-in templates."""
        defaults = [
            PromptTemplate(
                name="default",
                content=self.config.default_system_prompt,
                description="Default system prompt",
            ),
            PromptTemplate(
                name="code_review",
                content="You are a code reviewer. Analyze the provided code for:\n"
                "- Quality and readability\n"
                "- Potential bugs or errors\n"
                "- Security vulnerabilities\n"
                "- Performance issues\n"
                "- Best practices adherence\n\n"
                "Provide constructive feedback with specific recommendations.",
                variables=["language", "context"],
                description="Code review prompt",
                category="development",
            ),
            PromptTemplate(
                name="commit",
                content="Generate a git commit message for the changes described below.\n"
                "Follow conventional commits format: <type>: <description>\n\n"
                "Types: feat, fix, refactor, docs, test, chore, perf, ci\n\n"
                "Rules:\n"
                "- Keep the title under 72 characters\n"
                "- Use imperative mood in the title\n"
                "- Include body if changes are complex\n"
                "- Do not mention files that were only reformatted\n"
                "- Focus on the WHY, not the WHAT",
                variables=["changes", "files"],
                description="Commit message generator",
                category="git",
            ),
            PromptTemplate(
                name="debug",
                content="You are a debugging assistant. Help diagnose and fix the issue.\n\n"
                "Approach:\n"
                "1. Analyze the error/behavior\n"
                "2. Identify potential causes\n"
                "3. Suggest debugging steps\n"
                "4. Provide fix recommendations\n\n"
                "Be specific and actionable in your suggestions.",
                variables=["error", "context", "language"],
                description="Debugging prompt",
                category="development",
            ),
            PromptTemplate(
                name="refactor",
                content="You are a refactoring assistant. Improve the code structure.\n\n"
                "Focus on:\n"
                "- Reducing complexity\n"
                "- Improving readability\n"
                "- Eliminating duplication\n"
                "- Applying design patterns where appropriate\n"
                "- Maintaining existing behavior\n\n"
                "Provide step-by-step refactoring suggestions.",
                variables=["code", "goal"],
                description="Refactoring prompt",
                category="development",
            ),
            PromptTemplate(
                name="explain",
                content="Explain the following code or concept in clear, simple terms.\n\n"
                "Target audience: developers with intermediate experience.\n\n"
                "Include:\n"
                "- High-level overview\n"
                "- Key components and their roles\n"
                "- How different parts interact\n"
                "- Important patterns or idioms used\n\n"
                "Use analogies when helpful.",
                variables=["topic", "level"],
                description="Explanation prompt",
                category="learning",
            ),
            PromptTemplate(
                name="tdd",
                content="You are a test-driven development guide.\n\n"
                "Process:\n"
                "1. RED: Write a failing test that describes expected behavior\n"
                "2. GREEN: Write minimal code to make the test pass\n"
                "3. REFACTOR: Improve code while keeping tests passing\n\n"
                "Provide tests first, then implementation. Focus on testable behavior.",
                variables=["feature", "language"],
                description="TDD prompt",
                category="testing",
            ),
            PromptTemplate(
                name="security",
                content="Perform a security review of the provided code.\n\n"
                "Check for:\n"
                "- OWASP Top 10 vulnerabilities\n"
                "- Input validation issues\n"
                "- Authentication/authorization flaws\n"
                "- Injection vulnerabilities (SQL, XSS, command, etc.)\n"
                "- Insecure data handling\n"
                "- Cryptographic weaknesses\n"
                "- Information disclosure\n\n"
                "Rate severity: CRITICAL, HIGH, MEDIUM, LOW\n"
                "Provide specific remediation steps.",
                variables=["code", "context"],
                description="Security review prompt",
                category="security",
            ),
            PromptTemplate(
                name="architect",
                content="You are a software architect. Analyze and design system architecture.\n\n"
                "Consider:\n"
                "- Scalability requirements\n"
                "- Performance constraints\n"
                "- Maintainability and extensibility\n"
                "- Technology choices and tradeoffs\n"
                "- Integration patterns\n"
                "- Deployment considerations\n\n"
                "Provide architectural recommendations with rationale.",
                variables=["requirements", "constraints"],
                description="Architecture prompt",
                category="design",
            ),
        ]

        for template in defaults:
            self._templates[template.name] = template

    def _load_templates_from_dir(self, dir_path: Path) -> None:
        """Load templates from directory."""
        if not dir_path.exists():
            return

        for file in dir_path.glob("*.md"):
            name = file.stem
            content = file.read_text()

            # Extract variables from content if marked
            variables = []
            if "{{" in content:
                import re
                variables = re.findall(r"\{\{(\w+)\}\}", content)

            self._templates[name] = PromptTemplate(
                name=name,
                content=content,
                variables=variables,
                category="custom",
            )

    def get_prompt(self, name: str, variables: Optional[Dict[str, Any]] = None) -> str:
        """Get prompt with variables substituted."""
        template = self._templates.get(name)
        if not template:
            return self.config.default_system_prompt

        content = template.content

        if variables:
            for key, value in variables.items():
                content = content.replace(f"{{{{{key}}}}}", str(value))

        return content

    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get template by name."""
        return self._templates.get(name)

    def list_templates(self) -> List[PromptTemplate]:
        """List all templates."""
        return list(self._templates.values())

    def add_template(self, template: PromptTemplate) -> None:
        """Add a new template."""
        self._templates[template.name] = template

        if self.config.templates_dir:
            # Save to disk
            dir_path = Path(self.config.templates_dir)
            dir_path.mkdir(parents=True, exist_ok=True)
            file_path = dir_path / f"{template.name}.md"
            file_path.write_text(template.content)

    def build_system_prompt(
        self,
        context: Optional[Dict[str, Any]] = None,
        role: str = "default",
    ) -> str:
        """Build complete system prompt."""
        base = self.get_prompt(role)

        if context:
            # Add context information
            context_parts = []

            if "cwd" in context:
                context_parts.append(f"Working directory: {context['cwd']}")

            if "git_branch" in context:
                context_parts.append(f"Git branch: {context['git_branch']}")

            if "git_status" in context:
                context_parts.append(f"Git status: {context['git_status']}")

            if "files" in context:
                context_parts.append(f"Available files: {len(context['files'])} files in workspace")

            if context_parts:
                base += "\n\n" + "\n".join(context_parts)

        return base


# Singleton
_prompt_service: Optional[PromptService] = None


def get_prompt_service(config: Optional[PromptConfig] = None) -> PromptService:
    """Get prompt service singleton."""
    global _prompt_service
    if _prompt_service is None:
        _prompt_service = PromptService(config)
    return _prompt_service


def get_prompt(name: str, variables: Optional[Dict[str, Any]] = None) -> str:
    """Convenience prompt getter."""
    return get_prompt_service().get_prompt(name, variables)


__all__ = [
    "PromptTemplate",
    "PromptConfig",
    "PromptService",
    "get_prompt_service",
    "get_prompt",
]
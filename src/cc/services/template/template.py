"""Template Service - Document and code templates."""

from __future__ import annotations
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class Template(BaseModel):
    """Template definition."""
    name: str
    category: str
    description: Optional[str] = None
    content: str
    variables: List[str] = Field(default_factory=list)
    file_extension: Optional[str] = None


TEMPLATE_LIBRARY = {
    # Python templates
    "python_script": Template(
        name="python_script",
        category="python",
        description="Basic Python script template",
        content='#!/usr/bin/env python3\n"""{{description}}"""\n\nfrom __future__ import annotations\n\ndef main():\n    {{body}}\n\nif __name__ == "__main__":\n    main()\n',
        variables=["description", "body"],
        file_extension=".py",
    ),
    "python_class": Template(
        name="python_class",
        category="python",
        description="Python class template",
        content='"""{{description}}"""\n\nfrom __future__ import annotations\nfrom pydantic import BaseModel\n\nclass {{name}}(BaseModel):\n    """{{class_description}}"""\n    {{fields}}\n',
        variables=["description", "name", "class_description", "fields"],
        file_extension=".py",
    ),
    "python_test": Template(
        name="python_test",
        category="python",
        description="Python test template",
        content='"""Tests for {{module}}"""\n\nimport pytest\nfrom {{module}} import {{target}}\n\ndef test_{{target}}_basic():\n    """Test basic functionality."""\n    # TODO: Implement test\n    pass\n',
        variables=["module", "target"],
        file_extension="_test.py",
    ),

    # TypeScript templates
    "typescript_module": Template(
        name="typescript_module",
        category="typescript",
        description="TypeScript module template",
        content='/** {{description}} */\n\nexport interface {{interface_name}} {\n  {{fields}}\n}\n\nexport class {{class_name}} {\n  constructor(data: {{interface_name}}) {\n    // TODO: Implement\n  }\n}\n',
        variables=["description", "interface_name", "class_name", "fields"],
        file_extension=".ts",
    ),

    # Config templates
    "pyproject": Template(
        name="pyproject",
        category="config",
        description="pyproject.toml template",
        content='[project]\nname = "{{name}}"\nversion = "{{version}}"\ndescription = "{{description}}"\nauthors = [{name = "{{author}}"}]\nrequires-python = ">=3.9"\ndependencies = [{{deps}}]\n\n[build-system]\nrequires = ["hatchling"]\nbuild-backend = "hatchling.build"\n',
        variables=["name", "version", "description", "author", "deps"],
        file_extension=".toml",
    ),
    "gitignore": Template(
        name="gitignore",
        category="config",
        description="Python .gitignore template",
        content="# Byte-compiled / optimized / DLL files\n__pycache__/\n*.py[cod]\n\n# Virtual environments\nvenv/\n.env/\n\n# IDE\n.vscode/\n.idea/\n\n# Distribution\ndist/\n*.egg-info/\n\n# Testing\n.pytest_cache/\n.coverage\n\n# Secrets\n.env\n*.pem\n*.key\n",
        variables=[],
        file_extension=".gitignore",
    ),

    # Documentation templates
    "readme": Template(
        name="readme",
        category="docs",
        description="README template",
        content='# {{name}}\n\n{{description}}\n\n## Installation\n\n```bash\npip install {{name}}\n```\n\n## Usage\n\n```python\n{{usage_example}}\n```\n\n## License\n\n{{license}}\n',
        variables=["name", "description", "usage_example", "license"],
        file_extension=".md",
    ),
    "changelog": Template(
        name="changelog",
        category="docs",
        description="CHANGELOG template",
        content='# Changelog\n\nAll notable changes to this project will be documented in this file.\n\n## [Unreleased]\n\n### Added\n- TODO\n\n## [{{version}}] - {{date}}\n\n### Added\n- Initial release\n',
        variables=["version", "date"],
        file_extension=".md",
    ),

    # Web templates
    "html_page": Template(
        name="html_page",
        category="web",
        description="Basic HTML page template",
        content='<!DOCTYPE html>\n<html lang="en">\n<head>\n    <meta charset="UTF-8">\n    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n    <title>{{title}}</title>\n</head>\n<body>\n    {{content}}\n</body>\n</html>\n',
        variables=["title", "content"],
        file_extension=".html",
    ),
}


class TemplateService:
    """Template management service."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or Path.home() / ".claude" / "templates"
        self._templates: Dict[str, Template] = dict(TEMPLATE_LIBRARY)
        self._load_custom_templates()

    def _load_custom_templates(self) -> None:
        """Load custom templates from directory."""
        if not self.templates_dir.exists():
            return

        for file in self.templates_dir.glob("*.template"):
            try:
                content = file.read_text()
                name = file.stem
                # Parse variables from content
                import re
                variables = re.findall(r'\{\{(\w+)\}\}', content)

                self._templates[name] = Template(
                    name=name,
                    category="custom",
                    content=content,
                    variables=variables,
                )
            except Exception:
                pass

    def get_template(self, name: str) -> Optional[Template]:
        """Get template by name."""
        return self._templates.get(name)

    def render(self, name: str, variables: Dict[str, Any]) -> str:
        """Render template with variables."""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")

        result = template.content
        for key, value in variables.items():
            result = result.replace(f"{{{{{key}}}}}", str(value))

        return result

    def save_as_file(self, name: str, variables: Dict[str, Any], output_path: Path) -> None:
        """Render template and save to file."""
        template = self.get_template(name)
        if not template:
            raise ValueError(f"Template not found: {name}")

        content = self.render(name, variables)

        # Determine extension
        ext = template.file_extension or ""
        if not output_path.suffix and ext:
            output_path = output_path.with_suffix(ext)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content)

    def list_templates(self, category: Optional[str] = None) -> List[Template]:
        """List available templates."""
        templates = list(self._templates.values())
        if category:
            templates = [t for t in templates if t.category == category]
        return templates

    def add_template(self, template: Template) -> None:
        """Add custom template."""
        self._templates[template.name] = template

        # Save to file
        if self.templates_dir:
            self.templates_dir.mkdir(parents=True, exist_ok=True)
            file_path = self.templates_dir / f"{template.name}.template"
            file_path.write_text(template.content)

    def get_categories(self) -> List[str]:
        """Get available categories."""
        categories = set(t.category for t in self._templates.values())
        return sorted(categories)


# Singleton
_template_service: Optional[TemplateService] = None


def get_template_service() -> TemplateService:
    """Get template service singleton."""
    global _template_service
    if _template_service is None:
        _template_service = TemplateService()
    return _template_service


def render_template(name: str, variables: Dict[str, Any]) -> str:
    """Convenience render function."""
    return get_template_service().render(name, variables)


__all__ = [
    "Template",
    "TEMPLATE_LIBRARY",
    "TemplateService",
    "get_template_service",
    "render_template",
]
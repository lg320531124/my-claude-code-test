"""Magic Docs Service - Document processing and magic document generation."""

from __future__ import annotations
import json
import time
from pathlib import Path
from typing import Any, Optional
from dataclasses import dataclass, field
from enum import Enum


class DocFormat(Enum):
    """Document formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    JSON = "json"
    YAML = "yaml"
    TEXT = "text"


@dataclass
class DocSection:
    """Document section."""
    title: str
    content: str
    level: int = 1
    subsections: List["DocSection"] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class MagicDoc:
    """Magic document."""
    title: str
    sections: List[DocSection] = field(default_factory=list)
    format: DocFormat = DocFormat.MARKDOWN
    created_at: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)
    auto_generated: bool = True


class MagicDocsService:
    """Service for processing and generating documents."""

    def __init__(self):
        self._templates: Dict[str, str] = {}
        self._docs: Dict[str, MagicDoc] = {}
        self._load_templates()

    def _load_templates(self) -> None:
        """Load built-in templates."""
        self._templates = {
            "api_doc": self._api_doc_template(),
            "changelog": self._changelog_template(),
            "readme": self._readme_template(),
            "design_doc": self._design_doc_template(),
            "test_report": self._test_report_template(),
        }

    def _api_doc_template(self) -> str:
        """API documentation template."""
        return """
# {title}

## Overview
{overview}

## Endpoints

### {endpoint_name}
- **Method**: {method}
- **Path**: {path}
- **Description**: {description}

#### Parameters
{parameters}

#### Response
{response}

## Examples
{examples}
"""

    def _changelog_template(self) -> str:
        """Changelog template."""
        return """
# Changelog

All notable changes to this project will be documented in this file.

## [{version}] - {date}

### Added
{added}

### Changed
{changed}

### Fixed
{fixed}

### Removed
{removed}
"""

    def _readme_template(self) -> str:
        """README template."""
        return """
# {title}

{description}

## Installation
{installation}

## Usage
{usage}

## Configuration
{configuration}

## API Reference
{api_reference}

## Contributing
{contributing}

## License
{license}
"""

    def _design_doc_template(self) -> str:
        """Design document template."""
        return """
# Design Document: {title}

## Problem Statement
{problem}

## Proposed Solution
{solution}

## Architecture
{architecture}

## Implementation Plan
{implementation}

## Risks and Mitigations
{risks}

## Timeline
{timeline}
"""

    def _test_report_template(self) -> str:
        """Test report template."""
        return """
# Test Report

## Summary
- **Total Tests**: {total_tests}
- **Passed**: {passed}
- **Failed**: {failed}
- **Skipped**: {skipped}

## Details
{details}

## Coverage
{coverage}
"""

    def create_doc(
        self,
        title: str,
        template_name: Optional[str] = None,
        sections: Optional[List[DocSection]] = None,
        format: DocFormat = DocFormat.MARKDOWN,
        **kwargs,
    ) -> MagicDoc:
        """Create a magic document."""
        doc = MagicDoc(
            title=title,
            format=format,
            metadata=kwargs,
        )

        if template_name and template_name in self._templates:
            # Use template
            template = self._templates[template_name]
            content = template.format(title=title, **kwargs)
            doc.sections.append(DocSection(
                title=title,
                content=content,
                level=1,
            ))
        elif sections:
            doc.sections = sections

        doc_id = f"doc_{len(self._docs)}_{int(time.time())}"
        self._docs[doc_id] = doc

        return doc

    def generate_from_code(self, code: str, language: str) -> MagicDoc:
        """Generate documentation from code."""
        # Extract function/class definitions
        sections = []

        # Simple parsing for demonstration
        lines = code.split("\n")
        current_section = None
        current_content = []

        for line in lines:
            # Look for function/class definitions
            if language == "python":
                if line.startswith("def ") or line.startswith("class "):
                    if current_section:
                        current_section.content = "\n".join(current_content)
                        sections.append(current_section)
                    name = line.split("(")[0].replace("def ", "").replace("class ", "")
                    current_section = DocSection(
                        title=name,
                        content="",
                        level=2 if line.startswith("def ") else 1,
                    )
                    current_content = [line]
                elif current_section:
                    current_content.append(line)

        if current_section:
            current_section.content = "\n".join(current_content)
            sections.append(current_section)

        return self.create_doc(
            title="Code Documentation",
            sections=sections,
            metadata={"language": language},
        )

    def generate_from_json(self, data: dict, title: str = "JSON Documentation") -> MagicDoc:
        """Generate documentation from JSON structure."""
        sections = []

        for key, value in data.items():
            content = json.dumps(value, indent=2) if isinstance(value, (dict, list)) else str(value)
            sections.append(DocSection(
                title=key,
                content=content,
                level=2,
            ))

        return self.create_doc(title=title, sections=sections)

    def render(self, doc: MagicDoc, format: Optional[DocFormat] = None) -> str:
        """Render document to string."""
        use_format = format or doc.format

        if use_format == DocFormat.MARKDOWN:
            return self._render_markdown(doc)
        elif use_format == DocFormat.HTML:
            return self._render_html(doc)
        elif use_format == DocFormat.JSON:
            return self._render_json(doc)
        elif use_format == DocFormat.TEXT:
            return self._render_text(doc)
        else:
            return self._render_markdown(doc)

    def _render_markdown(self, doc: MagicDoc) -> str:
        """Render as Markdown."""
        lines = []

        for section in doc.sections:
            prefix = "#" * section.level
            lines.append(f"{prefix} {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")

            for sub in section.subsections:
                sub_prefix = "#" * sub.level
                lines.append(f"{sub_prefix} {sub.title}")
                lines.append("")
                lines.append(sub.content)
                lines.append("")

        return "\n".join(lines)

    def _render_html(self, doc: MagicDoc) -> str:
        """Render as HTML."""
        lines = ["<!DOCTYPE html>", "<html>", "<body>"]

        for section in doc.sections:
            tag = f"h{section.level}"
            lines.append(f"<{tag}>{section.title}</{tag}>")
            lines.append(f"<p>{section.content}</p>")

        lines.extend(["</body>", "</html>"])
        return "\n".join(lines)

    def _render_json(self, doc: MagicDoc) -> str:
        """Render as JSON."""
        data = {
            "title": doc.title,
            "format": doc.format.value,
            "created_at": doc.created_at,
            "sections": [
                {
                    "title": s.title,
                    "content": s.content,
                    "level": s.level,
                }
                for s in doc.sections
            ],
        }
        return json.dumps(data, indent=2)

    def _render_text(self, doc: MagicDoc) -> str:
        """Render as plain text."""
        lines = []

        for section in doc.sections:
            lines.append(section.title)
            lines.append("-" * len(section.title))
            lines.append(section.content)
            lines.append("")

        return "\n".join(lines)

    def save_doc(self, doc: MagicDoc, path: Path) -> bool:
        """Save document to file."""
        try:
            content = self.render(doc)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content)
            return True
        except Exception:
            return False

    def load_doc(self, path: Path) -> MagicDoc | None:
        """Load document from file."""
        if not path.exists():
            return None

        try:
            content = path.read_text()
            # Simple markdown parsing
            sections = []
            lines = content.split("\n")

            current_title = ""
            current_content = []
            current_level = 1

            for line in lines:
                if line.startswith("#"):
                    if current_title:
                        sections.append(DocSection(
                            title=current_title,
                            content="\n".join(current_content),
                            level=current_level,
                        ))
                    level = len(line) - len(line.lstrip("#"))
                    current_title = line.lstrip("#").strip()
                    current_level = level
                    current_content = []
                else:
                    current_content.append(line)

            if current_title:
                sections.append(DocSection(
                    title=current_title,
                    content="\n".join(current_content),
                    level=current_level,
                ))

            return MagicDoc(
                title=path.stem,
                sections=sections,
                format=DocFormat.MARKDOWN,
                auto_generated=False,
            )
        except Exception:
            return None

    def get_templates(self) -> List[str]:
        """Get available template names."""
        return list(self._templates.keys())

    def get_docs(self) -> List[str]:
        """Get document IDs."""
        return list(self._docs.keys())


__all__ = [
    "DocFormat",
    "DocSection",
    "MagicDoc",
    "MagicDocsService",
]

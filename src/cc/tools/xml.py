"""XML Tool - XML processing."""

from __future__ import annotations
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import ClassVar, Optional, List
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class XMLInput(ToolInput):
    """Input for XMLTool."""
    action: str = Field(description="Action: parse, format, validate, extract, xpath")
    data: Optional[str] = Field(default=None, description="XML data or file path")
    tag: Optional[str] = Field(default=None, description="Tag to extract")
    xpath: Optional[str] = Field(default=None, description="XPath expression")


class XMLTool(ToolDef):
    """XML processing."""

    name: ClassVar[str] = "XML"
    description: ClassVar[str] = "Parse and manipulate XML"
    input_schema: ClassVar[type] = XMLInput

    async def execute(self, input: XMLInput, ctx: ToolUseContext) -> ToolResult:
        """Execute XML operation."""
        action = input.action

        # Get data
        data = input.data
        if data:
            path = Path(data)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path
            if path.exists():
                data = path.read_text()

        if not data:
            return ToolResult(content="XML data required", is_error=True)

        if action == "parse":
            return self._parse_xml(data)
        elif action == "format":
            return self._format_xml(data)
        elif action == "validate":
            return self._validate_xml(data)
        elif action == "extract":
            return self._extract_tag(data, input.tag)
        elif action == "xpath":
            return self._xpath(data, input.xpath)
        else:
            return ToolResult(content=f"Unknown action: {action}", is_error=True)

    def _parse_xml(self, data: str) -> ToolResult:
        """Parse XML."""
        try:
            root = ET.fromstring(data)
            return ToolResult(
                content=f"XML parsed: root tag '{root.tag}'",
                metadata={"root_tag": root.tag, "children": len(root)},
            )
        except ET.ParseError as e:
            return ToolResult(content=f"XML parse error: {e}", is_error=True)

    def _format_xml(self, data: str) -> ToolResult:
        """Format XML."""
        try:
            root = ET.fromstring(data)
            # Pretty print
            ET.indent(root, space="  ")
            formatted = ET.tostring(root, encoding="unicode")
            return ToolResult(content=formatted)
        except ET.ParseError as e:
            return ToolResult(content=f"XML parse error: {e}", is_error=True)

    def _validate_xml(self, data: str) -> ToolResult:
        """Validate XML."""
        try:
            root = ET.fromstring(data)

            # Count elements
            elements = list(root.iter())

            return ToolResult(
                content=f"XML is valid\nRoot: {root.tag}\nElements: {len(elements)}",
                metadata={"valid": True, "root": root.tag, "element_count": len(elements)},
            )
        except ET.ParseError as e:
            return ToolResult(
                content=f"XML validation failed: {e}",
                is_error=True,
                metadata={"valid": False},
            )

    def _extract_tag(self, data: str, tag: Optional[str]) -> ToolResult:
        """Extract tag content."""
        if not tag:
            return ToolResult(content="Tag required", is_error=True)

        try:
            root = ET.fromstring(data)
            elements = root.findall(f".//{tag}")

            if not elements:
                return ToolResult(content=f"Tag '{tag}' not found", is_error=True)

            results = []
            for elem in elements:
                text = elem.text or ""
                attribs = dict(elem.attrib)
                results.append({
                    "tag": elem.tag,
                    "text": text.strip(),
                    "attribs": attribs,
                })

            lines = []
            for r in results:
                lines.append(f"<{r['tag']}>")
                if r['text']:
                    lines.append(f"  {r['text']}")
                if r['attribs']:
                    for k, v in r['attribs'].items():
                        lines.append(f"  @{k}={v}")

            return ToolResult(
                content="\n".join(lines),
                metadata={"tag": tag, "count": len(results), "results": results},
            )
        except ET.ParseError as e:
            return ToolResult(content=f"XML parse error: {e}", is_error=True)

    def _xpath(self, data: str, xpath: Optional[str]) -> ToolResult:
        """XPath query."""
        if not xpath:
            return ToolResult(content="XPath required", is_error=True)

        try:
            root = ET.fromstring(data)
            elements = root.findall(xpath)

            if not elements:
                return ToolResult(content=f"No matches for: {xpath}")

            lines = []
            for elem in elements:
                text = elem.text.strip() if elem.text else ""
                lines.append(f"<{elem.tag}> {text}")

            return ToolResult(
                content="\n".join(lines),
                metadata={"xpath": xpath, "count": len(elements)},
            )
        except ET.ParseError as e:
            return ToolResult(content=f"XML parse error: {e}", is_error=True)


__all__ = ["XMLTool", "XMLInput"]
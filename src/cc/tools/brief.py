"""Brief Tool - Generate brief summaries."""

from __future__ import annotations
from typing import Any
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolResult


class BriefInput(BaseModel):
    """Input for BriefTool."""
    content: str = Field(description="Content to summarize")
    max_length: int = Field(default=200, description="Maximum summary length")
    style: str = Field(default="concise", description="Summary style: concise, detailed, bullet")


class BriefTool(ToolDef):
    """Tool for generating brief summaries."""

    name = "Brief"
    description = "Generate a brief summary of content"
    input_schema = BriefInput

    async def execute(self, input: BriefInput, ctx: Any = None) -> ToolResult:
        """Execute brief generation."""
        content = input.content
        max_length = input.max_length
        style = input.style

        # Simple summarization logic
        if style == "bullet":
            lines = content.split("\n")
            bullets = [f"- {line.strip()}" for line in lines[:10] if line.strip()]
            summary = "\n".join(bullets[:5])
        elif style == "detailed":
            # Extract key sentences
            sentences = content.replace("\n", " ").split(". ")
            key_sentences = sentences[:3]
            summary = ". ".join(key_sentences) + "."
        else:
            # Concise - first few significant words
            words = content.split()
            significant = [w for w in words[:50] if len(w) > 3]
            summary = " ".join(significant[:max_length // 10])

        if len(summary) > max_length:
            summary = summary[:max_length - 3] + "..."

        return ToolResult(
            content=summary,
            metadata={
                "original_length": len(content),
                "summary_length": len(summary),
                "style": style,
            }
        )


__all__ = ["BriefTool", "BriefInput"]

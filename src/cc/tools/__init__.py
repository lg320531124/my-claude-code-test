"""Tool system."""

from .bash import BashTool
from .read import ReadTool
from .write import WriteTool
from .glob import GlobTool
from .grep import GrepTool

__all__ = [
    "BashTool",
    "ReadTool",
    "WriteTool",
    "GlobTool",
    "GrepTool",
    "get_default_tools",
]


def get_default_tools() -> list:
    """Get default tool set for a session."""
    return [
        BashTool(),
        ReadTool(),
        WriteTool(),
        GlobTool(),
        GrepTool(),
    ]
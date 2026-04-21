"""REPL Tool - Interactive REPL operations."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from ..types.tool import ToolDef, ToolResult, ToolInput, ToolUseContext


class REPLMode(Enum):
    """REPL modes."""
    INTERACTIVE = "interactive"
    SCRIPT = "script"
    EVAL = "eval"


@dataclass
class REPLInput(ToolInput):
    """REPL input schema."""
    code: str = ""
    mode: str = "eval"
    language: str = "python"
    timeout: int = 30


class REPLTool(ToolDef):
    """Tool for REPL operations."""
    
    name = "REPL"
    input_schema = REPLInput
    
    # Store REPL state
    _variables: Dict[str, Any] = {}
    _history: List[str] = []
    
    def __init__(self):
        self._variables = {}
        self._history = []
    
    async def call(
        self,
        args: Dict[str, Any],
        context: ToolUseContext,
        can_use_tool: Any = None,
        parent_message: Any = None,
        on_progress: Optional[Any] = None,
    ) -> ToolResult:
        """Execute REPL code."""
        code = args.get("code", "")
        mode = args.get("mode", "eval")
        language = args.get("language", "python")
        
        if not code:
            return ToolResult(data="No code provided")
        
        # Store in history
        self._history.append(code)
        
        if language == "python":
            return await self._execute_python(code, mode)
        
        return ToolResult(data=f"Unsupported language: {language}")
    
    async def _execute_python(self, code: str, mode: str) -> ToolResult:
        """Execute Python code."""
        try:
            if mode == "eval":
                # Evaluate expression
                result = eval(code, {"__builtins__": __builtins__}, self._variables)
                return ToolResult(data=str(result))
            
            elif mode == "script":
                # Execute as script
                exec(code, {"__builtins__": __builtins__}, self._variables)
                return ToolResult(data="Script executed")
            
            elif mode == "interactive":
                # Interactive mode with output capture
                local_vars = dict(self._variables)
                exec(code, {"__builtins__": __builtins__}, local_vars)
                
                # Update variables
                for key, value in local_vars.items():
                    if not key.startswith("_"):
                        self._variables[key] = value
                
                return ToolResult(data=f"Defined: {list(local_vars.keys())}")
        
        except Exception as e:
            return ToolResult(data=f"Error: {e}")
    
    def get_variables(self) -> Dict[str, Any]:
        """Get REPL variables."""
        return dict(self._variables)
    
    def get_history(self) -> List[str]:
        """Get REPL history."""
        return self._history[-20:]
    
    def clear(self) -> None:
        """Clear REPL state."""
        self._variables.clear()
        self._history.clear()


# Tool registration
_repl_tool: Optional[REPLTool] = None


def get_repl_tool() -> REPLTool:
    """Get global REPL tool."""
    global _repl_tool
    if _repl_tool is None:
        _repl_tool = REPLTool()
    return _repl_tool


__all__ = [
    "REPLMode",
    "REPLInput",
    "REPLTool",
    "get_repl_tool",
]

"""Code Tool - Code analysis and generation."""

from __future__ import annotations
import ast
import re
from pathlib import Path
from typing import ClassVar, Dict, List, Optional
from pydantic import BaseModel, Field

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class CodeInput(ToolInput):
    """Input for CodeTool."""
    action: str = Field(description="Action: analyze, outline, symbols, format, lint, count")
    file_path: Optional[str] = Field(default=None, description="File path")
    code: Optional[str] = Field(default=None, description="Code content")
    language: str = Field(default="python", description="Programming language")


class CodeAnalysis(BaseModel):
    """Code analysis result."""
    symbols: List[str] = []
    imports: List[str] = []
    classes: List[str] = []
    functions: List[str] = []
    lines: int = 0
    complexity: int = 0


class CodeTool(ToolDef):
    """Code analysis and operations."""

    name: ClassVar[str] = "Code"
    description: ClassVar[str] = "Analyze and process code files"
    input_schema: ClassVar[type] = CodeInput

    async def execute(self, input: CodeInput, ctx: ToolUseContext) -> ToolResult:
        """Execute code operation."""
        action = input.action

        # Get code content
        code = input.code
        if input.file_path:
            path = Path(input.file_path)
            if not path.is_absolute():
                path = Path(ctx.cwd) / path

            if path.exists():
                code = path.read_text()
                # Detect language from file extension
                ext = path.suffix.lower()
                lang_map = {
                    ".py": "python",
                    ".js": "javascript",
                    ".ts": "typescript",
                    ".go": "go",
                    ".rs": "rust",
                    ".java": "java",
                    ".c": "c",
                    ".cpp": "cpp",
                }
                input.language = lang_map.get(ext, input.language)

        if not code:
            return ToolResult(
                content="No code provided",
                is_error=True,
            )

        if action == "analyze":
            return self._analyze_code(code, input.language)
        elif action == "outline":
            return self._outline_code(code, input.language)
        elif action == "symbols":
            return self._extract_symbols(code, input.language)
        elif action == "format":
            return self._format_code(code, input.language)
        elif action == "lint":
            return self._lint_code(code, input.language)
        elif action == "count":
            return self._count_code(code)
        else:
            return ToolResult(
                content=f"Unknown action: {action}",
                is_error=True,
            )

    def _analyze_code(self, code: str, language: str) -> ToolResult:
        """Analyze code structure."""
        if language != "python":
            return ToolResult(
                content=f"Analysis only supported for Python. Language: {language}",
                is_error=True,
            )

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return ToolResult(
                content=f"Syntax error: {e}",
                is_error=True,
            )

        analysis = CodeAnalysis()

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                analysis.functions.append(node.name)
                analysis.symbols.append(f"function:{node.name}")
            elif isinstance(node, ast.ClassDef):
                analysis.classes.append(node.name)
                analysis.symbols.append(f"class:{node.name}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    analysis.imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    analysis.imports.append(f"{module}.{alias.name}")

        analysis.lines = len(code.splitlines())

        # Simple complexity estimate
        analysis.complexity = len([n for n in ast.walk(tree)
                                  if isinstance(n, (ast.If, ast.While, ast.For, ast.ExceptHandler))])

        result = "Analysis:\n"
        result += f"  Lines: {analysis.lines}\n"
        result += f"  Classes: {len(analysis.classes)}\n"
        result += f"  Functions: {len(analysis.functions)}\n"
        result += f"  Imports: {len(analysis.imports)}\n"
        result += f"  Complexity: {analysis.complexity}\n"

        if analysis.classes:
            result += "\nClasses:\n  - " + "\n  - ".join(analysis.classes) + "\n"
        if analysis.functions:
            result += "\nFunctions:\n  - " + "\n  - ".join(analysis.functions) + "\n"

        return ToolResult(content=result, metadata=analysis.model_dump())

    def _outline_code(self, code: str, language: str) -> ToolResult:
        """Generate code outline."""
        if language != "python":
            # Generic outline for other languages
            lines = []
            for line in code.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#") and not stripped.startswith("//"):
                    # Check for function/class patterns
                    if any(p in stripped.lower() for p in ["function", "class", "def", "public", "private"]):
                        lines.append(stripped[:100])
            return ToolResult(content="\n".join(lines[:50]))

        try:
            tree = ast.parse(code)
        except SyntaxError:
            return ToolResult(content="Cannot parse code for outline", is_error=True)

        outline = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                args = [a.arg for a in node.args.args]
                outline.append(f"def {node.name}({', '.join(args)})")
                # Add method signatures
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.Return):
                        outline.append("    returns: ...")

            elif isinstance(node, ast.ClassDef):
                outline.append(f"class {node.name}:")
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, ast.FunctionDef):
                        args = [a.arg for a in child.args.args]
                        outline.append(f"    def {child.name}({', '.join(args)})")

        return ToolResult(content="\n".join(outline))

    def _extract_symbols(self, code: str, language: str) -> ToolResult:
        """Extract symbols from code."""
        if language == "python":
            try:
                tree = ast.parse(code)
            except SyntaxError:
                return ToolResult(content="Cannot parse code", is_error=True)

            symbols = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Name):
                    symbols.append(node.id)
                elif isinstance(node, ast.Attribute):
                    symbols.append(node.attr)

            # Count occurrences
            symbol_counts: Dict[str, int] = {}
            for s in symbols:
                symbol_counts[s] = symbol_counts.get(s, 0) + 1

            # Sort by count
            sorted_symbols = sorted(symbol_counts.items(), key=lambda x: -x[1])
            lines = [f"{s}: {c}" for s, c in sorted_symbols[:50]]

            return ToolResult(content="\n".join(lines), metadata={"symbols": sorted_symbols})

        else:
            # Generic regex for other languages
            # Match word-like patterns
            symbols = re.findall(r'\b[A-Za-z_][A-Za-z0-9_]*\b', code)
            symbol_counts = {}
            for s in symbols:
                if len(s) > 2:  # Skip short symbols
                    symbol_counts[s] = symbol_counts.get(s, 0) + 1

            sorted_symbols = sorted(symbol_counts.items(), key=lambda x: -x[1])
            lines = [f"{s}: {c}" for s, c in sorted_symbols[:50]]

            return ToolResult(content="\n".join(lines), metadata={"symbols": sorted_symbols})

    def _format_code(self, code: str, language: str) -> ToolResult:
        """Format code (basic formatting)."""
        lines = code.splitlines()

        # Remove trailing whitespace
        lines = [line.rstrip() for line in lines]

        # Ensure proper line endings
        formatted = "\n".join(lines)

        return ToolResult(
            content=formatted,
            metadata={"original_lines": len(code.splitlines()), "formatted_lines": len(lines)},
        )

    def _lint_code(self, code: str, language: str) -> ToolResult:
        """Basic linting."""
        issues = []

        lines = code.splitlines()

        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 100:
                issues.append(f"Line {i}: Line too long ({len(line)} chars)")

            # Check trailing whitespace
            if line.rstrip() != line and line.strip():
                issues.append(f"Line {i}: Trailing whitespace")

            # Check for tabs in Python
            if language == "python" and "\t" in line:
                issues.append(f"Line {i}: Tab character (use spaces)")

        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                issues.append(f"Syntax error at line {e.lineno}: {e.msg}")

        if not issues:
            return ToolResult(content="No lint issues found")

        return ToolResult(content="\n".join(issues), metadata={"issues": issues})

    def _count_code(self, code: str) -> ToolResult:
        """Count code statistics."""
        lines = code.splitlines()

        stats = {
            "total_lines": len(lines),
            "code_lines": len([l for l in lines if l.strip() and not l.strip().startswith("#")]),
            "comment_lines": len([l for l in lines if l.strip().startswith("#")]),
            "empty_lines": len([l for l in lines if not l.strip()]),
            "characters": len(code),
            "words": len(code.split()),
        }

        result = "Code Statistics:\n"
        result += f"  Total lines: {stats['total_lines']}\n"
        result += f"  Code lines: {stats['code_lines']}\n"
        result += f"  Comment lines: {stats['comment_lines']}\n"
        result += f"  Empty lines: {stats['empty_lines']}\n"
        result += f"  Characters: {stats['characters']}\n"

        return ToolResult(content=result, metadata=stats)


__all__ = ["CodeTool", "CodeInput", "CodeAnalysis"]
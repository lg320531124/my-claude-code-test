"""SkillTool - Execute skills."""

import json
from pathlib import Path
from typing import ClassVar

from ..types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext


class SkillInput(ToolInput):
    """Input for SkillTool."""

    skill: str
    args: str | None = None


class SkillTool(ToolDef):
    """Execute skills."""

    name: ClassVar[str] = "Skill"
    description: ClassVar[str] = "Execute a skill with optional arguments"
    input_schema: ClassVar[type[ToolInput]] = SkillInput

    SKILLS_DIR = Path.home() / ".claude-code-py" / "skills"

    async def execute(self, input: SkillInput, ctx: ToolUseContext) -> ToolResult:
        """Execute the skill."""
        skill_name = input.skill
        args = input.args

        # Find skill file
        skill_path = self.SKILLS_DIR / f"{skill_name}.md"

        # Check built-in skills
        builtin = self._get_builtin_skills()
        if skill_name in builtin:
            skill_content = builtin[skill_name]
            source = "builtin"
        elif skill_path.exists():
            skill_content = skill_path.read_text()
            source = "custom"
        else:
            return ToolResult(
                content=f"Skill not found: {skill_name}",
                is_error=True,
            )

        # Parse skill content
        parsed = self._parse_skill(skill_content)

        # Execute skill logic (simplified - return skill instructions)
        # In a full implementation, this would execute the skill's defined workflow
        result = self._format_skill_result(parsed, args, source)

        return ToolResult(
            content=result,
            metadata={"skill": skill_name, "source": source},
        )

    def _get_builtin_skills(self) -> dict:
        """Get built-in skills."""
        return {
            "tdd": """---
name: tdd
description: Test-Driven Development workflow
---

# TDD Workflow

1. **Write test first** (RED)
   - Define expected behavior
   - Write failing test

2. **Implement minimum code** (GREEN)
   - Make test pass
   - Keep code minimal

3. **Refactor** (IMPROVE)
   - Clean up code
   - Keep tests passing

## Guidelines
- 80%+ test coverage
- One test per behavior
- Fast tests (< 5s)
""",
            "debug": """---
name: debug
description: Systematic debugging workflow
---

# Debug Workflow

1. **Reproduce** - Confirm the bug exists
2. **Isolate** - Find minimal reproduction
3. **Investigate** - Trace the cause
4. **Fix** - Make targeted change
5. **Verify** - Confirm fix works
6. **Prevent** - Add test for regression

## Tools
- Use Bash for logs/errors
- Use Grep for code search
- Use Read for source inspection
""",
            "review": """---
name: review
description: Code review checklist
---

# Code Review Checklist

## Quality
- [ ] Code is readable
- [ ] Naming is clear
- [ ] No dead code
- [ ] No code duplication

## Security
- [ ] No hardcoded secrets
- [ ] Input validation
- [ ] No SQL injection
- [ ] No XSS vulnerabilities

## Performance
- [ ] No unnecessary loops
- [ ] Efficient data structures
- [ ] No memory leaks

## Testing
- [ ] Tests cover edge cases
- [ ] Tests are meaningful
- [ ] Mocks are appropriate
""",
            "security-review": """---
name: security-review
description: Security vulnerability check
---

# Security Review Checklist

## OWASP Top 10
1. Injection (SQL, Command, XSS)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities
5. Broken Access Control
6. Security Misconfiguration
7. XSS
8. Insecure Deserialization
9. Using Components with Vulnerabilities
10. Insufficient Logging

## Checks
- [ ] Input validation
- [ ] Output encoding
- [ ] Authentication secure
- [ ] Authorization checked
- [ ] Secrets not in code
- [ ] HTTPS enforced
- [ ] Error handling safe
""",
        }

    def _parse_skill(self, content: str) -> dict:
        """Parse skill content."""
        # Parse frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                import yaml
                try:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                    return {
                        "name": frontmatter.get("name", "unknown"),
                        "description": frontmatter.get("description", ""),
                        "content": body,
                    }
                except Exception:
                    pass

        return {
            "name": "unknown",
            "description": "",
            "content": content,
        }

    def _format_skill_result(self, parsed: dict, args: str | None, source: str) -> str:
        """Format skill result."""
        result = f"# Skill: {parsed['name']}\n"
        result += f"Source: {source}\n"
        if args:
            result += f"Arguments: {args}\n"
        result += f"\n{parsed['content']}\n"
        result += "\n## Instructions\n"
        result += "Follow the steps above. Use available tools as needed.\n"
        return result
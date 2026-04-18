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
            "refactor": """---
name: refactor
description: Safe refactoring workflow
---

# Refactoring Workflow

## Before Starting
1. Ensure tests exist and pass
2. Read and understand current code
3. Identify what needs to change

## During Refactoring
1. Make one small change at a time
2. Run tests after each change
3. Keep the same interface

## Common Refactorings
- Extract function
- Rename variables
- Remove duplication
- Simplify conditionals
- Replace magic numbers

## Guidelines
- Don't change behavior
- Keep backward compatibility
- Update comments if needed

## After Completion
1. All tests pass
2. Code is cleaner
3. No new complexity
""",
            "deploy": """---
name: deploy
description: Deployment checklist
---

# Deployment Checklist

## Pre-Deploy
- [ ] All tests passing
- [ ] No lint errors
- [ ] No type errors
- [ ] Version bumped
- [ ] CHANGELOG updated
- [ ] Environment vars documented

## Code Quality
- [ ] No debug logs
- [ ] No hardcoded values
- [ ] Secrets in env vars
- [ ] Error handling complete

## Infrastructure
- [ ] Database migrations ready
- [ ] Backups in place
- [ ] Monitoring configured
- [ ] Rollback plan documented

## Post-Deploy
- [ ] Health checks pass
- [ ] Logs streaming
- [ ] Metrics collecting
- [ ] Smoke tests run

## Rollback Steps
1. Identify issue
2. Stop new traffic
3. Restore previous version
4. Verify rollback success
""",
            "perf": """---
name: perf
description: Performance optimization workflow
---

# Performance Optimization

## 1. Measure First
- Profile before optimizing
- Identify actual bottleneck
- Document current performance

## 2. Analyze
- Check algorithm complexity
- Review database queries
- Look for N+1 problems
- Check memory patterns

## 3. Optimize
- Cache frequently used data
- Batch operations
- Use async for I/O
- Reduce allocations

## 4. Verify
- Measure after change
- Compare with baseline
- Document improvement

## Common Patterns
- Loop unrolling (careful)
- Lazy loading
- Connection pooling
- Index optimization

## Anti-Patterns
- Premature optimization
- Optimizing without measuring
- Micro-optimizations
- Ignoring readability
""",
            "cleanup": """---
name: cleanup
description: Code cleanup workflow
---

# Cleanup Workflow

## Dead Code
- Find unused functions
- Remove unreachable code
- Delete obsolete files
- Clean imports

## Duplication
- Find repeated code
- Extract common functions
- Use inheritance/composition

## Naming
- Rename unclear variables
- Fix misleading names
- Use consistent style

## Structure
- Fix indentation
- Remove extra whitespace
- Organize imports
- Update comments

## Tools
- Use Grep to find patterns
- Use Glob to find files
- Use Edit for small changes
""",
            "init-project": """---
name: init-project
description: Initialize new project
---

# Project Initialization

## Structure
```
project/
├── src/
├── tests/
├── docs/
├── README.md
├── pyproject.toml
├── .gitignore
```

## Files to Create
1. README.md - Project description
2. pyproject.toml/package.json - Dependencies
3. .gitignore - Ignore patterns
4. src/__init__.py or main file
5. tests/__init__.py

## Git Setup
1. git init
2. git add .
3. git commit -m "Initial commit"

## Dependencies
- Add core dependencies
- Add dev dependencies (lint, test)
- Pin versions for production
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
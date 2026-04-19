# Development Guide

## Architecture Overview

### Directory Structure

```
src/cc/
├── main.py          # CLI entry point
├── core/
│   ├── engine.py    # Query engine - LLM API calls
│   ├── session.py   # Session management
│   └── repl.py      # REPL mode
├── tools/
│   ├── base.py      # Tool base class
│   ├── bash.py      # Shell execution
│   ├── read.py      # File reading
│   ├── write.py     # File writing
│   ├── edit.py      # File editing
│   ├── glob.py      # File pattern search
│   ├── grep.py      # Content search
│   └── web*.py      # Web tools
├── commands/
│   ├── commit.py    # Git commit
│   ├── doctor.py    # Diagnostics
│   └── *.py         # Other commands
├── permissions/
│   ├── manager.py   # Permission manager
│   ├── rules.py     # Rule definitions
│   └── prompts.py   # User prompts
├── context/
│   └── collector.py # Context collection
├── ui/
│   ├── app.py       # Textual app
│   ├── screens/     # UI screens
│   └── widgets/     # UI components
├── mcp/
│   ├── client.py    # MCP client
│   ├── server.py    # Server management
│   ├── health.py    # Health monitoring
│   └── subscriptions.py # Resource subscriptions
├── services/
│   ├── api/         # API clients
│   ├── plugins/     # Plugin system
│   └── hooks/       # Hooks system
├── utils/
│   ├── config.py    # Configuration
│   ├── shell.py     # Shell helpers
│   └── log.py       # Logging
└── types/
    ├── message.py   # Message types
    ├── tool.py      # Tool types
    └── permission.py # Permission types
```

---

## Key Components

### Query Engine

The `QueryEngine` orchestrates LLM interactions:

1. Build messages from context
2. Send request to API
3. Process streaming response
4. Handle tool calls
5. Execute tools and return results
6. Continue until completion

```python
# src/cc/core/engine.py
class QueryEngine:
    async def query(self, text, ctx):
        # Build request
        messages = self._build_messages(text)
        tools = self._build_tool_schema()

        # Stream response
        async for chunk in self.api.stream(messages, tools):
            if chunk.type == "text":
                yield chunk.text
            elif chunk.type == "tool_use":
                result = await self._execute_tool(chunk)
                yield result
```

### Tool System

Tools follow a unified interface:

```python
# src/cc/tools/base.py
class ToolDef:
    name: str
    description: str

    async def execute(self, input, ctx) -> ToolResult:
        raise NotImplementedError

    def get_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {...}
        }
```

### Permission System

Permissions are checked before tool execution:

```python
# src/cc/permissions/manager.py
class PermissionManager:
    async def check(self, tool_name, tool_input) -> PermissionDecision:
        # Check rules
        for rule in self.rules:
            if matches_pattern(tool_name, rule.pattern):
                return rule.decision

        # Prompt user
        return await self.prompter.prompt(tool_name, tool_input)
```

### Plugin System

Plugins extend functionality:

```python
# src/cc/services/plugins/plugin_system.py
class PluginBase:
    metadata: ClassVar[PluginMetadata]

    async def on_load(self):
        # Register hooks, tools, commands
        pass

    async def on_unload(self):
        # Cleanup
        pass
```

### Hooks System

Hooks intercept events:

```python
# src/cc/services/hooks/hooks_system.py
class HookRegistry:
    async def trigger(self, event, ctx) -> list[HookResult]:
        for hook in self.get_hooks(event):
            result = await hook.execute(ctx)
            if result.block:
                break
```

---

## Adding New Features

### Adding a Tool

1. Create tool file in `src/cc/tools/`:

```python
# src/cc/tools/my_tool.py
from .base import ToolDef, ToolInput, ToolResult, ToolUseContext

class MyTool(ToolDef):
    name = "my_tool"
    description = "My custom tool"

    async def execute(self, input, ctx: ToolUseContext) -> ToolResult:
        # Implementation
        return ToolResult(content="Success")
```

2. Register in `src/cc/tools/__init__.py`:

```python
from .my_tool import MyTool

DEFAULT_TOOLS = [
    BashTool(),
    ReadTool(),
    MyTool(),  # Add here
]
```

3. Add tests in `tests/test_my_tool.py`.

### Adding a Command

1. Create command file in `src/cc/commands/`:

```python
# src/cc/commands/my_cmd.py
import click
from rich.console import Console

@click.command("my-cmd")
@click.argument("arg", required=False)
def my_command(arg: str | None):
    """My custom command."""
    console = Console()
    console.print(f"Running my-cmd with {arg}")
```

2. Register in `src/cc/commands/__init__.py`.

### Adding a Plugin Hook

```python
from cc.services.hooks import register_hook, HookType, HookContext, HookResult

async def my_hook(ctx: HookContext) -> HookResult:
    # Process event
    print(f"Event: {ctx.event.value}")
    return HookResult(success=True)

register_hook(HookType.PRE_QUERY, my_hook, priority=10)
```

### Adding an MCP Server

1. Create `mcp.json`:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "python",
      "args": ["my_mcp_server.py"]
    }
  }
}
```

2. Server will auto-connect on startup.

---

## Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run specific module
uv run pytest tests/test_tools.py

# With coverage
uv run pytest --cov=cc tests/
```

### Writing Tests

```python
# tests/test_my_feature.py
import pytest
from cc.tools.my_tool import MyTool

class TestMyTool:
    def test_init(self):
        tool = MyTool()
        assert tool.name == "my_tool"

    @pytest.mark.asyncio
    async def test_execute(self):
        tool = MyTool()
        result = await tool.execute({}, ctx)
        assert result.success
```

---

## Code Style

### Guidelines

1. Use asyncio throughout for async operations
2. Use dataclasses for structured data
3. Use Pydantic for validation
4. Follow PEP 8 naming
5. Document with docstrings

### Example

```python
"""Module description."""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class MyData:
    """Data structure."""
    name: str
    value: int = 0
    tags: list[str] = field(default_factory=list)


class MyClass:
    """Class description."""

    def __init__(self, config: dict):
        self.config = config

    async def process(self) -> MyData:
        """Process data."""
        await asyncio.sleep(1)
        return MyData(name="result")
```

---

## Contribution Process

1. Fork repository
2. Create feature branch
3. Make changes
4. Add tests
5. Run linting: `uv run ruff check src/`
6. Run tests: `uv run pytest tests/`
7. Submit PR

---

## Performance Considerations

### Async Operations

- Use `asyncio.gather` for parallel execution
- Cache results where appropriate
- Use streaming for large responses

### Token Management

- Compact context when large
- Use appropriate model (Haiku for simple tasks)
- Cache system prompts

### Memory

- Clear caches periodically
- Use lazy loading for large data
- Profile memory usage

---

## Debugging

### Logs

```python
from cc.utils.log import get_logger

logger = get_logger()
logger.info("Processing...")
logger.error("Failed: %s", error)
```

### Diagnostics

```bash
# Run diagnostics
cc /doctor

# Check specific
cc /stats
```

---

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Run full test suite
4. Build package: `uv build`
5. Publish: `uv publish`

---

## Resources

- [API Reference](./api-reference.md)
- [User Guide](./user-guide.md)
- [Textual Documentation](https://textual.textualize.io/)
- [Anthropic API Docs](https://docs.anthropic.com/)
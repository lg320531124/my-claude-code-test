# Claude Code Python API Reference

## Core Modules

### cc.core.engine - Query Engine

```python
from cc.core import QueryEngine, QueryStats

engine = QueryEngine(
    model="claude-opus-4-7",
    tools=[...],
    base_url="https://api.anthropic.com",
)

# Query with streaming
async for chunk in engine.query("Hello", context):
    if isinstance(chunk, str):
        print(chunk)  # Text response
    elif isinstance(chunk, dict):
        if chunk.get("type") == "complete":
            stats = chunk["stats"]
```

### cc.core.session - Session Management

```python
from cc.core import Session, SessionManager

# Create session
session = Session(cwd=Path.cwd())

# Add message
session.add_message(create_user_message("Hello"))

# Save/Load
session.save_transcript(Path("session.json"))
session.load_transcript(Path("session.json"))

# Session history
manager = SessionManager()
sessions = manager.list_sessions()
session = manager.load_session(session_id)
```

---

## Tools

### cc.tools.base - Tool Base

```python
from cc.tools.base import ToolDef, ToolInput, ToolResult

class MyTool(ToolDef):
    name = "my_tool"
    description = "My custom tool"

    async def execute(self, input: ToolInput, ctx: ToolContext) -> ToolResult:
        return ToolResult(content="Success")
```

### cc.tools.bash - Bash Execution

```python
from cc.tools import BashTool

tool = BashTool()
result = await tool.execute({"command": "ls -la"}, ctx)
print(result.content)
```

### cc.tools.read/write/edit - File Operations

```python
from cc.tools import FileReadTool, FileWriteTool, FileEditTool

# Read file
read_tool = FileReadTool()
result = await read_tool.execute({"file_path": "/path/to/file"}, ctx)

# Write file
write_tool = FileWriteTool()
result = await write_tool.execute({
    "file_path": "/path/to/new",
    "content": "Hello World",
}, ctx)

# Edit file
edit_tool = FileEditTool()
result = await edit_tool.execute({
    "file_path": "/path/to/file",
    "old_string": "old",
    "new_string": "new",
}, ctx)
```

---

## Permissions

### cc.permissions.manager - Permission System

```python
from cc.permissions import PermissionManager, PermissionDecision

manager = PermissionManager()

# Check permission
decision = await manager.check("Bash", {"command": "ls"})
if decision == PermissionDecision.ALLOW:
    # Execute
    pass
elif decision == PermissionDecision.ASK:
    # Prompt user
    pass
```

### cc.permissions.rules - Permission Rules

```python
from cc.permissions import get_default_rules, matches_pattern

rules = get_default_rules()
for rule in rules:
    if matches_pattern("Bash(ls*)", rule.pattern):
        print(rule.decision)
```

---

## Services

### cc.services.plugins - Plugin System

```python
from cc.services.plugins import (
    PluginBase,
    PluginMetadata,
    PluginManager,
    get_plugin_manager,
)

class MyPlugin(PluginBase):
    metadata = PluginMetadata(
        name="my_plugin",
        version="1.0",
    )

    async def on_load(self):
        self.register_hook("pre_query", self.my_hook)

    async def my_hook(self, ctx):
        print("Query starting")

# Initialize
manager = get_plugin_manager()
await manager.initialize()
await manager.trigger_event("pre_query")
```

### cc.services.hooks - Hooks System

```python
from cc.services.hooks import (
    HookType,
    HookContext,
    HookResult,
    HookManager,
    register_hook,
)

# Register hook
async def my_hook(ctx: HookContext) -> HookResult:
    print(f"Event: {ctx.event}")
    return HookResult(success=True)

register_hook(HookType.PRE_QUERY, my_hook)

# Trigger
await trigger_hook("pre_query", data={"key": "value"})
```

### cc.services.api - API Clients

```python
from cc.services.api import EnhancedAPIClient, create_client

client = create_client(
    model="claude-opus-4-7",
    api_key="...",
)

# Streaming request
async for event in client.stream(messages, tools):
    if event.type == "text":
        print(event.text)
    elif event.type == "tool_use":
        print(event.tool_name)
```

---

## MCP Integration

### cc.mcp - Model Context Protocol

```python
from cc.mcp import (
    MCPManager,
    MCPHealthMonitor,
    SubscriptionManager,
    get_mcp_manager,
)

# Initialize
manager = get_mcp_manager()
await manager.load_config()
await manager.connect_all()

# List tools
tools = manager.get_all_tools()

# Call tool
result = await manager.call_tool("server", "tool_name", {"arg": "value"})

# Health monitoring
monitor = MCPHealthMonitor()
await monitor.start()
health = monitor.get_health_summary()

# Subscriptions
sub_manager = SubscriptionManager()
await sub_manager.start()
sub_id = sub_manager.subscribe("resource://uri", callback)
```

---

## UI Components

### cc.ui - Terminal UI

```python
from cc.ui import (
    ClaudeCodeApp,
    ThemeManager,
    VimMode,
    run_tui,
)

# Run TUI
run_tui()

# Or create app with config
app = ClaudeCodeApp(config=my_config)
app.run()

# Theme management
theme_mgr = ThemeManager()
theme_mgr.set_theme("nord")
css = theme_mgr.get_theme_css("dark")

# Vim mode
from cc.ui.widgets import VimHandler, VimModeIndicator
handler = VimHandler(widget)
handler.enable()
```

---

## Commands

### cc.commands - CLI Commands

```python
# Available commands
# /help - Show help
# /commit - Git commit
# /review - Code review
# /compact - Compact context
# /doctor - Diagnostics
# /mcp - MCP management
# /memory - Memory management
# /sessions - Session history
# /stats - Usage statistics
# /theme - Theme settings
# /vim - Toggle Vim mode
```

---

## Types

### cc.types - Type Definitions

```python
from cc.types.message import Message, create_user_message, create_assistant_message
from cc.types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from cc.types.permission import PermissionDecision, PermissionRule, PermissionResult

# Create messages
user_msg = create_user_message("Hello")
assistant_msg = create_assistant_message("Hi there!")
```

---

## Context Collection

### cc.context - Context System

```python
from cc.context import AsyncContextCollector

collector = AsyncContextCollector()
info = await collector.collect_all()

print(info.environment)  # Python version, platform, cwd
print(info.git)         # Branch, status, commits
print(info.project)     # Package info, dependencies
```

---

## Configuration

### cc.utils.config - Configuration Management

```python
from cc.utils.config import Config, save_config

config = Config.load()
print(config.api.model)
print(config.api.base_url)

# Modify
config.api.model = "claude-sonnet-4-6"
save_config(config)
```
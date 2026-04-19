# API Reference

## Core Engine

### QueryEngine

```python
from cc.core.engine import QueryEngine

engine = QueryEngine(
    model="claude-sonnet-4-6",
    tools=[],             # Tool definitions
    system_prompt=None,   # Custom system prompt
    max_tokens=8192,      # Max output tokens
    max_turns=20,         # Max conversation turns
    base_url=None,        # Custom API URL
)
```

#### Methods

```python
# Set callbacks for streaming
engine.set_callbacks(
    on_text=lambda text: print(text),
    on_tool_start=lambda name: print(f"Tool: {name}"),
    on_tool_result=lambda result: print(result),
)

# Execute query
async for chunk in engine.query(prompt, context):
    if isinstance(chunk, str):
        # Text chunk
    elif isinstance(chunk, dict):
        # Event dict (tool_results, complete, etc.)

# Get context summary
summary = engine.get_context_summary()
# Returns: {history: {...}, tools: {...}, stats: {...}}
```

### MessageHistory

```python
from cc.core.engine import MessageHistory

history = MessageHistory(
    max_messages=100,
    max_tokens=100_000,
    compression_threshold=0.8,
)

# Add message
history.add(message)

# Get token usage
usage = history.get_token_usage()
# Returns: {estimated_tokens, message_count, max_tokens, usage_percent}

# Convert to API format
api_messages = history.to_api_format()

# Clear history
history.clear()
```

### ToolExecutor

```python
from cc.core.engine import ToolExecutor

executor = ToolExecutor(
    tools=[tool1, tool2],
    permission_prompter=None,
    max_parallel=5,
)

# Get tool
tool = executor.get_tool("Bash")

# Get schemas
schemas = executor.get_schemas()

# Execute single tool
result = await executor.execute_single(tool_call, context)

# Execute parallel
results = await executor.execute_parallel(tool_calls, context)

# Get stats
stats = executor.get_stats()
```

### QueryStats

```python
from cc.core.engine import QueryStats

stats = QueryStats()
stats.input_tokens = 1000
stats.output_tokens = 500

# Get dict
data = stats.to_dict()

# Estimate cost
cost = stats.estimate_cost("claude-sonnet-4-6")
```

## Message Types

### Creating Messages

```python
from cc.types.message import (
    create_user_message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
)

# Simple user message
msg = create_user_message("Hello")

# With content blocks
msg = UserMessage(
    role="user",
    content=[TextBlock(text="Hello")]
)
```

### Content Blocks

```python
from cc.types.message import (
    TextBlock,
    ToolUseBlock,
    ToolResultBlock,
)

# Text block
text = TextBlock(text="Some text")

# Tool use block
tool_use = ToolUseBlock(
    id="tool_123",
    name="Bash",
    input={"command": "ls"},
)

# Tool result block
result = ToolResultBlock(
    tool_use_id="tool_123",
    content="file1.txt\nfile2.txt",
    is_error=False,
)
```

## Tool Definitions

### Base Tool Class

```python
from cc.types.tool import ToolDef, ToolInput, ToolResult, ToolUseContext
from cc.types.permission import PermissionResult, PermissionDecision

class MyTool(ToolDef):
    name = "MyTool"
    description = "My custom tool"

    class MyInput(ToolInput):
        value: str

    input_schema = MyInput

    async def execute(self, input: MyInput, ctx: ToolUseContext) -> ToolResult:
        return ToolResult(content=f"Result: {input.value}")

    def check_permission(self, input: MyInput, ctx: ToolUseContext) -> PermissionResult:
        return PermissionResult(decision=PermissionDecision.ALLOW.value)

    def get_api_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema.model_json_schema(),
        }
```

### Tool Result

```python
from cc.types.tool import ToolResult

# Success result
result = ToolResult(
    content="Success",
    is_error=False,
    metadata={"key": "value"},
)

# Error result
error = ToolResult(
    content="Error message",
    is_error=True,
)

# Convert to block
block = result.to_block("tool_123")
```

## Permission System

### Permission Manager

```python
from cc.permissions import PermissionManager
from cc.types.permission import PermissionConfig, PermissionDecision

config = PermissionConfig(
    allow=["Read", "Glob"],
    deny=["Bash(rm -rf *)"],
    ask=["Write", "Edit"],
)

manager = PermissionManager(config)

# Check permission
result = manager.check("Bash", {"command": "ls -la"})
# Returns: PermissionResult(decision, reason, rule)

# Add rule
manager.add_rule("Bash(ls *)", PermissionDecision.ALLOW)
```

### Permission Prompter

```python
from cc.permissions import EnhancedPermissionPrompter

prompter = EnhancedPermissionPrompter(
    auto_approve=False,
    project_dir=Path.cwd(),
    save_decisions=True,
)

# Prompt for decision
decision = await prompter.prompt("Bash", {"command": "ls"})
# Returns: PermissionDecision.ALLOW, DENY, or ASK
```

### Permission Persistence

```python
from cc.permissions import PermissionPersistence

persistence = PermissionPersistence(Path.cwd())

# Save decision
persistence.save_decision("Bash(ls *)", PermissionDecision.ALLOW, expires_days=30)

# Get decision
decision = persistence.get_decision("Bash(ls *)")

# List decisions
decisions = persistence.list_decisions()

# Clear expired
persistence.clear_expired()
```

## Configuration

### Loading Config

```python
from cc.utils.config import Config

# Load from file or defaults
config = Config.load()

# Load from specific file
config = Config.load_from_file(Path(".claude/config.json"))
```

### Config Structure

```python
config = Config(
    api=APIConfig(
        provider="anthropic",
        model="claude-sonnet-4-6",
        base_url=None,
        max_tokens=8192,
    ),
    permissions=PermissionConfig(
        allow=["Read", "Glob"],
        deny=["Bash(rm -rf *)"],
        ask=["Write", "Edit"],
    ),
    ui=UIConfig(
        theme="dark",
        output_style="explanatory",
        vim_mode=False,
    ),
)

# Save
config.save()
config.save_to_file(Path("config.json"))
```

## Session Management

### Session

```python
from cc.core.session import Session

session = Session(cwd=Path.cwd())

# Add message
session.add_message(message)

# Get context
ctx = session.get_context()

# Clear messages
session.clear_messages()

# Get messages
messages = session.messages
```

## API Client

### Direct API Usage

```python
from cc.services.api import APIClient, get_client

# Get client
client = get_client(model="claude-sonnet-4-6")

# Create message
async for event in client.create_message(
    messages=[{"role": "user", "content": "Hello"}],
    tools=[],
    system="You are helpful",
    max_tokens=1000,
    stream=True,
):
    # Handle streaming events
    pass

# Get usage stats
stats = client.get_usage_stats()
```

## Context Collection

### Git Context

```python
from cc.context import get_git_context

git_info = get_git_context(Path.cwd())
# Returns: {branch, status, recent_commits, etc.}
```

### System Prompt

```python
from cc.context import get_system_prompt

prompt = get_system_prompt(
    scenario="developer",
    cwd=Path.cwd(),
    git_info=git_info,
)
```

## REPL

### Running REPL

```python
from cc.core.repl import REPL, run_repl

config = Config.load()
session = Session()

repl = REPL(config, session)
repl.run()

# Or with initial prompt
run_repl(config, session, initial_prompt="Hello")
```

## TUI

### Running TUI

```python
from cc.ui.app import ClaudeCodeApp, run_tui

# Run app
run_tui()

# Or with config
app = ClaudeCodeApp(config=config, session=session)
app.run()
```
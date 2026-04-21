# API Reference

## Async IO Utilities

### Async File Operations

```python
from cc.utils.async_io import (
    read_file_async,
    write_file_async,
    exists_async,
    stat_async,
    mkdir_async,
)

# Async file read
content = await read_file_async("/path/to/file")

# Async file write
await write_file_async("/path/to/file", "content")

# Check file existence
if await exists_async("/path/to/file"):
    stat = await stat_async("/path/to/file")
    print(f"Size: {stat.st_size}")
```

### Async Process Execution

```python
from cc.utils.async_process import (
    run_command_async,
    run_command_streaming,
    run_commands_parallel,
    ProcessResult,
)

# Single command
result = await run_command_async("ls -la")
print(result.stdout)

# Streaming output
async for line in run_command_streaming("tail -f log.txt"):
    print(line)

# Parallel execution
results = await run_commands_parallel([
    "git status",
    "npm test",
    "python -m pytest",
])
```

### Async HTTP Client

```python
from cc.utils.async_http import AsyncHTTPClient, fetch_sse_stream

# HTTP client
client = AsyncHTTPClient(timeout=30.0)
await client.connect()

response = await client.get("https://api.example.com/data")
data = response.json()

# SSE streaming
async for chunk in fetch_sse_stream(url, headers):
    yield chunk
```

## Token Estimation

```python
from cc.services.token_estimation import (
    estimate_tokens,
    estimate_message_tokens,
    TokenCounter,
    TokenBudgetManager,
)

# Estimate tokens
tokens = await estimate_tokens("Hello world")

# Message token estimation
usage = await estimate_message_tokens(message)

# Token counter with cache
counter = TokenCounter()
tokens = await counter.count("large content")

# Budget manager
manager = TokenBudgetManager()
if manager.can_add_input(5000):
    manager.add_usage(usage)
```

## MCP Client

```python
from cc.services.mcp import MCPClient, MCPServerConfig

config = MCPServerConfig(
    name="my-server",
    command="node",
    args=["server.js"],
    timeout=30.0,
)

client = MCPClient(config)
await client.connect()

# Discover tools
tools = client.get_tools()

# Call tool
result = await client.call_tool("my_tool", {"arg": "value"})
```

## LSP Client

```python
from cc.services.lsp import LSPClient, LSPServerConfig

config = LSPServerConfig(
    language="python",
    command="pyright",
    args=["--stdio"],
)

client = LSPClient(config, root_path="/project")
await client.connect()

# Get completions
completions = await client.get_completions("file.py", line=10, character=5)

# Get hover info
hover = await client.get_hover("file.py", line=10, character=5)
```

## Streaming Utilities

```python
from cc.core.streaming import SSEParser, StreamBuffer, ToolCallBuffer

# SSE parser
parser = SSEParser()
event = parser.parse_event(raw_event)

# Stream buffer
buffer = StreamBuffer()
buffer.add_text("Hello")
buffer.subscribe(lambda text: print(text))

# Tool call buffer
tool_buffer = ToolCallBuffer()
tool_buffer.start_tool("tool_1", "Bash")
tool_buffer.add_partial("tool_1", '{"command": ')
result = tool_buffer.complete_tool("tool_1")
```

## Compression

```python
from cc.core.compression import compress_messages, CompressionStrategy

messages = [{"role": "user", "content": "text"} for _ in range(100)]

compressed = await compress_messages(
    messages,
    strategy=CompressionStrategy.SUMMARY,
    target_tokens=50000,
)
```

## Hooks

```python
from cc.hooks import (
    use_tool_permission,
    use_keybindings,
    KeyMode,
)

# Permission hook
allowed = await use_tool_permission("Bash")

# Keybindings hook
kb = await use_keybindings({
    "ctrl+p": lambda: print("Previous"),
    "ctrl+n": lambda: print("Next"),
})
kb.set_mode(KeyMode.NORMAL)
```

## Model Selection

```python
from cc.utils.model import ModelSelector, AVAILABLE_MODELS

selector = ModelSelector(default_model="claude-sonnet-4-6")

# Select for task
model = selector.select_for_task("architecture")

# Get model info
info = AVAILABLE_MODELS["claude-sonnet-4-6"]
print(f"Price: ${info.input_price}/M input, ${info.output_price}/M output")
```

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
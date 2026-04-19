# MCP Integration Guide

## Overview

MCP (Model Context Protocol) allows Claude Code to connect to external tools and resources through standardized protocol.

## Configuration

Create `.claude/mcp.json` in your project:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "mcp-server-filesystem",
      "args": ["--root", "/path/to/project"],
      "env": {}
    },
    "github": {
      "command": "mcp-server-github",
      "args": [],
      "env": {
        "GITHUB_TOKEN": "${GITHUB_TOKEN}"
      }
    }
  }
}
```

## Using MCP in Python

### Initialize MCP

```python
from cc.mcp import initialize_mcp, get_mcp_manager

# Initialize all configured servers
await initialize_mcp()

# Get manager
manager = get_mcp_manager()
```

### List Available Tools

```python
from cc.mcp import discover_mcp_tools

tools = await discover_mcp_tools()
for tool in tools:
    print(f"{tool['name']}: {tool['description']}")
```

### Call MCP Tool

```python
from cc.mcp import call_mcp_tool

result = await call_mcp_tool(
    server_name="filesystem",
    tool_name="read_file",
    arguments={"path": "/path/to/file.txt"},
)
```

### Read MCP Resource

```python
from cc.mcp import read_mcp_resource

content = await read_mcp_resource(
    server_name="filesystem",
    uri="file:///path/to/file.txt",
)
```

## MCP Manager API

```python
from cc.mcp import MCPManager

manager = MCPManager()

# Load configuration
await manager.load_config()

# Connect all servers
results = await manager.connect_all()

# Get connected servers
servers = manager.get_connected_servers()

# Get all tools
tools = manager.get_all_tools()

# Server info
info = manager.get_server_info("filesystem")

# Disconnect all
await manager.disconnect_all()
```

## Resource Management

```python
from cc.mcp import get_resource_manager, MCPResourceCache

manager = get_resource_manager()

# Read resource with caching
resource = await manager.read("file:///path/file.txt")

# Get text content
text = resource.to_text()

# Get JSON content
json_data = resource.to_json()

# Cache stats
stats = manager.get_cache_stats()
```

## Resource Subscriptions

```python
from cc.mcp import MCPSubscription

def on_update(uri, content):
    print(f"Updated: {uri}")

sub = manager.subscribe("file:///path/file.txt", on_update)

# Later...
manager.unsubscribe(sub)
```

## Creating MCP Server

### Basic Server

```python
from cc.mcp import MCPServerProcess

server = MCPServerProcess(
    name="my-server",
    command="python",
    args=["-m", "my_mcp_server"],
)

await server.start()

# Send message
response = await server.send_message({
    "method": "tools/list",
})

await server.stop()
```

## Available MCP Servers

### File System

```json
{
  "filesystem": {
    "command": "mcp-server-filesystem",
    "args": ["--root", "/project"]
  }
}
```

Tools:
- `read_file` - Read file contents
- `write_file` - Write file contents
- `list_directory` - List directory contents
- `search_files` - Search for files

### GitHub

```json
{
  "github": {
    "command": "mcp-server-github",
    "env": {"GITHUB_TOKEN": "${GITHUB_TOKEN}"}
  }
}
```

Tools:
- `get_issue` - Get issue details
- `create_issue` - Create new issue
- `list_pull_requests` - List PRs
- `create_pull_request` - Create PR

### Slack

```json
{
  "slack": {
    "command": "mcp-server-slack",
    "env": {"SLACK_BOT_TOKEN": "${SLACK_TOKEN}"}
  }
}
```

Tools:
- `send_message` - Send Slack message
- `read_channel` - Read channel messages
- `list_channels` - List available channels

## Troubleshooting

### Check MCP Status

```python
from cc.mcp import show_mcp_status
show_mcp_status()
```

### Server Not Connecting

1. Check command exists
2. Check arguments are correct
3. Verify environment variables

### Tool Not Available

1. Check server is connected
2. Verify tool name matches server
3. Check input schema validation

## Environment Variables

| Variable | Purpose |
|----------|---------|
| GITHUB_TOKEN | GitHub API access |
| SLACK_BOT_TOKEN | Slack API access |
| ANTHROPIC_API_KEY | For MCP server auth |
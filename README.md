# Claude Code Python

Python implementation of Claude Code CLI - an AI-powered coding assistant for terminal.

## Features

- 🛠️ **Tool System**: File operations, shell commands, web fetch, and more
- 🤖 **Query Engine**: LLM API integration with tool-call loop
- ⌨️ **Command System**: Slash commands for common workflows
- 🔐 **Permission System**: Fine-grained control over tool execution
- 🖥️ **Terminal UI**: Rich TUI with Textual framework
- 🔌 **MCP Support**: Model Context Protocol integration
- 🔄 **Multi-API**: Support Anthropic and compatible APIs (智谱, etc.)

## Installation

```bash
# Using pip
pip install claude-code-py

# Using uv
uv install claude-code-py
```

## Usage

```bash
# Start interactive session
cc

# Run with a prompt
cc "fix the bug in src/main.py"

# Use slash commands
cc /commit
cc /review
cc /doctor
```

## Configuration

Configuration is stored in `~/.claude-code-py/config.json`:

```json
{
  "api": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-6"
  },
  "permissions": {
    "allow": ["Bash(ls *)", "Read"],
    "deny": ["Bash(rm *)"],
    "ask": ["Bash(npm *)"]
  }
}
```

## Environment Variables

- `ANTHROPIC_API_KEY`: Anthropic API key
- `ANTHROPIC_BASE_URL`: Custom API endpoint (for compatible APIs)
- `ANTHROPIC_MODEL`: Model override

## Development

```bash
# Install dev dependencies
uv sync --extra dev

# Run tests
uv run pytest

# Type check
uv run mypy src/cc
```

## License

MIT
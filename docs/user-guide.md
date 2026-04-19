# Claude Code Python - User Guide

## Quick Start

### Installation

```bash
# Clone repository
git clone https://github.com/lg320531124/my-claude-code-test
cd my-claude-code-test

# Install with uv
uv sync

# Or with pip
pip install -e .
```

### Basic Usage

```bash
# Run CLI
cc

# With options
cc --model claude-opus-4-7
cc --help
```

---

## Configuration

### Configuration File

Create `.claude/settings.json` in your project:

```json
{
  "api": {
    "model": "claude-opus-4-7",
    "base_url": "https://api.anthropic.com"
  },
  "permissions": {
    "mode": "ask",
    "allow": ["Bash(ls*)", "Read(*)"]
  },
  "ui": {
    "theme": "dark"
  }
}
```

### Environment Variables

```bash
# API Key
export ANTHROPIC_API_KEY=your_key_here

# Custom Base URL (for compatible APIs)
export ANTHROPIC_BASE_URL=https://api.example.com
```

---

## Slash Commands

### Available Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands and keybindings |
| `/clear` | Clear current session |
| `/commit` | Create git commit with message |
| `/review` | Review code changes |
| `/compact` | Compress conversation context |
| `/doctor` | Run environment diagnostics |
| `/mcp` | MCP server management |
| `/memory` | Persistent memory management |
| `/sessions` | Browse session history |
| `/stats` | Show usage statistics |
| `/theme` | Change UI theme |
| `/vim` | Toggle Vim mode |
| `/exit` | Exit application |

### Usage Examples

```
/help           # Show help
/commit         # Generate commit message
/doctor         # Check environment
/theme nord     # Set nord theme
```

---

## Keybindings

### Global

| Key | Action |
|-----|--------|
| `Ctrl+C` | Quit |
| `Ctrl+L` | Clear session |
| `Ctrl+D` | Run diagnostics |
| `Ctrl+H` | Show help |
| `Ctrl+T` | Toggle theme |
| `Ctrl+S` | Show stats |
| `Ctrl+P` | Session history |
| `Ctrl+O` | Settings |
| `Ctrl+/` | Command palette |
| `Ctrl+V` | Toggle Vim mode |
| `Escape` | Cancel/Exit |

### Vim Mode (when enabled)

| Key | Action |
|-----|--------|
| `j` | Scroll down |
| `k` | Scroll up |
| `g` | Go to top |
| `G` | Go to bottom |
| `i` | Enter insert mode |
| `Esc` | Exit insert mode |
| `:` | Command mode |

#### Vim Command Mode

| Command | Action |
|---------|--------|
| `:q` | Quit |
| `:w` | Save session |
| `:wq` | Save and quit |
| `:clear` | Clear |
| `:theme X` | Set theme |

---

## Themes

### Available Themes

- `dark` - Default dark theme (Catppuccin-like)
- `light` - Light theme (Catppuccin Latte)
- `mono` - Monochrome theme
- `gruvbox` - Gruvbox dark
- `nord` - Nord theme
- `dracula` - Dracula theme
- `solarized` - Solarized dark

### Setting Theme

```
# Via command
/theme nord

# Via Vim command
:theme nord

# Via config
# In .claude/settings.json:
{"ui": {"theme": "nord"}}
```

---

## MCP (Model Context Protocol)

### Configuration

Create `.claude/mcp.json`:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

### MCP Commands

```
/mcp list       # List MCP servers
/mcp connect X  # Connect to server X
/mcp disconnect X # Disconnect server X
/mcp reload     # Reload all servers
/mcp call X Y args # Call tool Y on server X
```

### Health Monitoring

MCP servers are automatically monitored:
- Connection status checked every 30 seconds
- Auto-reconnect on failure (max 5 attempts)
- Health status displayed in UI

---

## Permissions

### Permission Modes

- `ask` - Prompt for each action (default)
- `auto` - Auto-approve all actions (dangerous!)

### Permission Rules

Add rules in `.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(ls*)",
      "Bash(git status*)",
      "Read(*)",
      "Write(src/*)"
    ],
    "deny": [
      "Bash(rm*)",
      "Bash(sudo*)"
    ]
  }
}
```

### Permission Response Options

When prompted:
- `y` - Allow once
- `Y` - Always allow (save)
- `n` - Deny once
- `N` - Always deny (save)
- `s` - Allow for session only
- `i` - Show more info

---

## Sessions

### Session Management

Sessions are automatically saved in `~/.claude/sessions/`.

```
/sessions       # Browse session history
/sessions load X # Load session X
/sessions delete X # Delete session X
/sessions export X # Export session to file
```

### Session Persistence

Sessions include:
- Conversation history
- Working directory
- Tool execution results
- Timestamps

---

## Memory System

### Persistent Memory

Memory is stored in `~/.claude/projects/<project>/memory/`.

```
/memory show    # Show saved memories
/memory add X   # Add memory
/memory clear   # Clear memories
```

### Memory Types

- `user` - User preferences and profile
- `project` - Project-specific context
- `feedback` - Learned behaviors
- `reference` - External resource references

---

## Usage Statistics

### View Statistics

```
/stats          # Show current session stats
```

Statistics include:
- Input/output tokens
- Tool call count
- Response time
- Model used

### Cost Estimation

Costs are calculated based on:
- Model pricing (Claude Opus/Sonnet/Haiku)
- Token usage
- Tool overhead

---

## Troubleshooting

### Run Diagnostics

```
/doctor         # Check environment
```

Checks:
- Python version
- Git availability
- API key presence
- MCP configuration
- Dependencies

### Common Issues

1. **API Key Missing**
   ```
   export ANTHROPIC_API_KEY=your_key
   ```

2. **Connection Failed**
   - Check base URL
   - Verify API key
   - Check network

3. **MCP Server Not Starting**
   - Check `mcp.json` config
   - Verify command path
   - Check server logs

4. **Permission Loop**
   - Add rule to allow common operations
   - Use `Y` to save decisions

---

## Tips

1. **Efficient Workflow**
   - Use Vim mode for navigation
   - Set preferred theme
   - Add frequently used commands to permissions

2. **Context Management**
   - Use `/compact` when context grows
   - Clear session for fresh start

3. **MCP Usage**
   - Start essential MCP servers in config
   - Monitor health status
   - Use subscriptions for real-time updates

4. **Customization**
   - Create custom plugins
   - Register hooks for events
   - Modify theme CSS
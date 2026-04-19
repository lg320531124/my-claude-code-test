# Claude Code Python - Quick Start Guide

## Installation

```bash
# Clone repository
git clone https://github.com/lg320531124/my-claude-code-test.git
cd my-claude-code-test

# Install with uv (recommended)
uv pip install -e .

# Or with pip
pip install -e .
```

## Initial Setup

### 1. Set API Key

```bash
# For Anthropic Claude
export ANTHROPIC_API_KEY=your-api-key

# For compatible APIs (智谱, DeepSeek, etc.)
export ANTHROPIC_API_KEY=your-key
export ANTHROPIC_BASE_URL=https://api.deepseek.com
```

### 2. Initialize Project

```bash
# Initialize configuration
cc init

# Or with options
cc init --template full --force
```

## Basic Usage

### REPL Mode

```bash
# Start REPL
cc

# Ask a single question
cc ask "How do I read a file in Python?"

# Launch TUI mode
cc --tui
```

### Commands in REPL

```
/help      - Show available commands
/clear     - Clear session history
/model     - Show current model
/stats     - Show session statistics
/doctor    - Run diagnostics
/config    - Show configuration
/exit      - Exit REPL
```

## Configuration

### View Config

```bash
cc config --list
```

### Set Config

```bash
cc config model claude-sonnet-4-6
cc config base_url https://api.deepseek.com
cc config theme dark
```

### Permission Rules

```bash
# Add allow rule
cc permission "Bash(ls *)" --allow

# Add deny rule
cc permission "Bash(rm -rf *)" --deny

# List all rules
cc permission --list
```

## Using Different Models

```bash
# Claude models
cc --model claude-sonnet-4-6
cc --model claude-opus-4-5
cc --model claude-haiku-4-5

# Compatible models (智谱 GLM)
cc --model glm-4-plus --base-url https://coding.dashscope.aliyuncs.com/apps/anthropic

# DeepSeek
cc --model deepseek-chat --base-url https://api.deepseek.com
```

## TUI Mode

```bash
# Launch TUI
cc --tui

# TUI shortcuts
Ctrl+C - Quit
Ctrl+L - Clear
Ctrl+D - Doctor
Ctrl+H - Help
Ctrl+T - Toggle theme
Ctrl+S - Stats
```

## Available Tools

| Tool | Description |
|------|-------------|
| Read | Read file contents |
| Write | Write to file |
| Edit | Edit file (find/replace) |
| Glob | Find files by pattern |
| Grep | Search in files |
| Bash | Execute shell commands |
| WebFetch | Fetch web content |
| WebSearch | Web search |
| TaskCreate | Create task |
| TaskList | List tasks |

## Built-in Skills

| Skill | Purpose |
|-------|---------|
| tdd | Test-driven development |
| debug | Debugging assistance |
| review | Code review |
| security-review | Security analysis |
| refactor | Refactoring guidance |
| deploy | Deployment help |
| perf | Performance optimization |
| cleanup | Code cleanup |
| init-project | Project initialization |

## Environment Variables

| Variable | Purpose |
|----------|---------|
| ANTHROPIC_API_KEY | API key |
| ANTHROPIC_BASE_URL | Custom API URL |
| CC_MODEL | Default model |
| CC_THEME | UI theme |

## Project Structure

```
my-claude-code-test/
├── src/cc/
│   ├── core/          # Engine, session, REPL
│   ├── tools/         # Tool implementations
│   ├── commands/      # Slash commands
│   ├── permissions/   # Permission system
│   ├── ui/            # TUI components
│   ├── services/      # API clients
│   ├── utils/         # Utilities
│   └── types/         # Type definitions
├── tests/             # Test files
├── config/            # Configuration examples
└── docs/              # Documentation
```

## Troubleshooting

### Run Diagnostics

```bash
cc doctor
```

### Common Issues

1. **API Key Not Set**
   ```
   export ANTHROPIC_API_KEY=your-key
   ```

2. **Model Not Found**
   - Check model name matches provider
   - Ensure base_url is correct

3. **Permission Denied**
   - Check permission rules
   - Use `/config` to view current rules

## More Information

- [API Documentation](./API.md)
- [Configuration Guide](./CONFIGURATION.md)
- [Tool Reference](./TOOLS.md)
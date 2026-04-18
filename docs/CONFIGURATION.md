# Claude Code Python - Configuration Guide

## Environment Variables

```bash
# API Configuration
ANTHROPIC_API_KEY=your-api-key
ANTHROPIC_BASE_URL=https://api.anthropic.com  # Optional: Custom API endpoint
ANTHROPIC_MODEL=claude-sonnet-4-6              # Optional: Model override

# For compatible APIs (智谱/DeepSeek/etc.)
# 智谱 Coding Plan
ANTHROPIC_BASE_URL=https://coding.dashscope.aliyuncs.com/apps/anthropic
ANTHROPIC_MODEL=glm-5
ANTHROPIC_API_KEY=your-dashscope-key

# DeepSeek
ANTHROPIC_BASE_URL=https://api.deepseek.com
ANTHROPIC_MODEL=deepseek-chat
ANTHROPIC_API_KEY=your-deepseek-key

# Moonshot
ANTHROPIC_BASE_URL=https://api.moonshot.cn/v1
ANTHROPIC_MODEL=moonshot-v1-8k
ANTHROPIC_API_KEY=your-moonshot-key
```

## Configuration File

Location: `~/.claude-code-py/config.json`

```json
{
  "api": {
    "provider": "anthropic",
    "model": "claude-sonnet-4-6",
    "base_url": null,
    "max_tokens": 8192
  },
  "permissions": {
    "allow": [
      "Read",
      "Glob",
      "Grep",
      "Bash(ls *)",
      "Bash(git status *)"
    ],
    "deny": [
      "Bash(rm -rf *)"
    ],
    "ask": [
      "Write",
      "Edit",
      "Bash(npm *)",
      "Bash(pip *)",
      "Bash(rm *)"
    ]
  },
  "ui": {
    "theme": "dark",
    "output_style": "explanatory",
    "vim_mode": false
  }
}
```

## MCP Configuration

Location: `~/.claude-code-py/mcp.json`

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
        "GITHUB_TOKEN": "your-token"
      }
    },
    "postgres": {
      "command": "mcp-server-postgres",
      "args": ["postgresql://user:pass@localhost/db"],
      "env": {}
    }
  }
}
```

## Project Configuration

Location: `.claude-code-py/settings.json` (in project root)

```json
{
  "permissions": {
    "allow": ["Bash(npm run *)"],
    "deny": [],
    "ask": ["Bash(npm publish)"]
  },
  "context": {
    "include": ["src/", "lib/", "docs/"],
    "exclude": ["node_modules/", "dist/", ".git/"]
  }
}
```

## Skills Directory

Location: `~/.claude-code-py/skills/`

Create custom skills as `.md` files with frontmatter:

```markdown
---
name: my-custom-skill
description: My custom workflow
---

# My Custom Skill

1. Step 1
2. Step 2
3. Step 3
```

## Memory Directory

Location: `~/.claude-code-py/memory/`

Persistent memories stored as `.md` files.

## Sessions Directory

Location: `~/.claude-code-py/sessions/`

Auto-saved session transcripts.

## Permission Rules

| Decision | Meaning |
|----------|---------|
| `allow` | Always permitted |
| `deny` | Always blocked |
| `ask` | Prompt user each time |

Pattern syntax:
- `Read` - Allow all Read operations
- `Bash(ls *)` - Allow `ls` with any arguments
- `Bash(rm *)` - Ask for `rm` commands
- `Write` - Ask for all Write operations
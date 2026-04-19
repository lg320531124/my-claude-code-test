# Session Recovery Guide

## Overview

Sessions are automatically saved and can be restored after crashes or for continuing work.

## Automatic Saving

Sessions are auto-saved every 60 seconds:

```python
from cc.core.recovery import SessionRecovery, get_persistence

recovery = SessionRecovery(get_persistence())
recovery.start_auto_save(session, engine, config)

# Stop when done
recovery.stop_auto_save()
```

## Manual Save

```python
from cc.core.recovery import save_current_session

path = await save_current_session(session, engine, config)
print(f"Session saved to: {path}")
```

## List Saved Sessions

```python
from cc.core.recovery import list_saved_sessions

sessions = list_saved_sessions()
for s in sessions:
    print(f"{s['session_id']}: {s['message_count']} messages")
```

## Load Session

```python
from cc.core.recovery import load_session, SessionData

data = load_session("session-123")
if data:
    print(f"Loaded: {data.metadata.message_count} messages")
```

## Restore Session

```python
from cc.core.recovery import SessionRecovery

recovery = SessionRecovery()
data = load_session("session-123")

session = recovery.restore_session(data)
```

## Session Persistence API

```python
from cc.core.recovery import SessionPersistence

persistence = SessionPersistence(
    storage_dir=Path(".claude/sessions"),
    max_sessions=50,
)

# Save
path = persistence.save(session, stats, config)

# Load
data = persistence.load(path)
data = persistence.load_latest()
data = persistence.load_by_id("session-id")

# List
sessions = persistence.list_sessions()

# Delete
persistence.delete(path)
persistence.delete_by_id("session-id")
```

## Session Metadata

```python
from cc.core.recovery import SessionMetadata

metadata = SessionMetadata(
    session_id="unique-id",
    cwd="/project/path",
    created_at=time.time(),
    updated_at=time.time(),
    message_count=10,
    token_count=5000,
    model="claude-sonnet-4-6",
    title="First message preview...",
)
```

## Session History

```python
from cc.core.recovery import SessionHistory

history = SessionHistory()

# Get recent
recent = history.get_recent(limit=10)

# Search
results = history.search("keyword")

# Get summary
summary = history.get_session_summary("session-id")

# Export
history.export_session("session-id", Path("export.json"))
```

## Recovery After Crash

```python
from cc.core.recovery import SessionRecovery

recovery = SessionRecovery()

# Check for recovery session
data = recovery.check_recovery()

if data:
    print("Found recovery session!")
    session = recovery.restore_session(data)

    # Clear recovery marker
    recovery.clear_recovery()
```

## CLI Commands

```bash
# List sessions
cc sessions list

# Load session
cc sessions load session-123

# Delete session
cc sessions delete session-123

# Export session
cc sessions export session-123 output.json
```

## Session File Format

```json
{
  "metadata": {
    "session_id": "session-123",
    "cwd": "/project/path",
    "created_at": 1234567890,
    "updated_at": 1234567890,
    "message_count": 10,
    "token_count": 5000,
    "model": "claude-sonnet-4-6",
    "title": "Preview..."
  },
  "messages": [
    {"role": "user", "content": [{"type": "text", "text": "Hello"}]},
    {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]}
  ],
  "stats": {
    "total_tokens": 5000,
    "tool_calls": 3
  },
  "config": {
    "model": "claude-sonnet-4-6"
  }
}
```

## Best Practices

1. **Enable auto-save** for long sessions
2. **Name sessions** with descriptive titles
3. **Clean up** old sessions periodically
4. **Export important sessions** for backup
5. **Check recovery** after crashes
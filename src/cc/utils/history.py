"""History Management - Prompt history storage and retrieval.

Provides history entry management, pasted content handling, and
JSONL-based history file operations for command history.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Dict, List, AsyncGenerator, Set, Any

MAX_HISTORY_ITEMS = 100
MAX_PASTED_CONTENT_LENGTH = 1024


@dataclass
class PastedContent:
    """Pasted content entry."""
    id: int
    type: str  # 'text' or 'image'
    content: Optional[str] = None
    media_type: Optional[str] = None
    filename: Optional[str] = None


@dataclass
class StoredPastedContent:
    """Stored paste content - inline or hash reference."""
    id: int
    type: str  # 'text' or 'image'
    content: Optional[str] = None  # Inline for small pastes
    content_hash: Optional[str] = None  # Hash reference for large pastes
    media_type: Optional[str] = None
    filename: Optional[str] = None


@dataclass
class HistoryEntry:
    """History entry with display text and pasted contents."""
    display: str
    pasted_contents: Dict[int, PastedContent] = field(default_factory=dict)


@dataclass
class LogEntry:
    """Internal log entry format."""
    display: str
    pasted_contents: Dict[int, StoredPastedContent] = field(default_factory=dict)
    timestamp: float = 0.0
    project: str = ""
    session_id: Optional[str] = None


@dataclass
class TimestampedHistoryEntry:
    """Timestamped history entry for ctrl+r picker."""
    display: str
    timestamp: float
    resolve: Any  # Callable returning HistoryEntry


def get_pasted_text_ref_num_lines(text: str) -> int:
    """Get number of lines in pasted text reference."""
    return len(re.findall(r'\r\n|\r|\n', text))


def format_pasted_text_ref(id: int, num_lines: int) -> str:
    """Format pasted text reference."""
    if num_lines == 0:
        return f"[Pasted text #{id}]"
    return f"[Pasted text #{id} +{num_lines} lines]"


def format_image_ref(id: int) -> str:
    """Format image reference."""
    return f"[Image #{id}]"


def parse_references(input_text: str) -> List[Dict[str, Any]]:
    """Parse references from input text."""
    pattern = r'\[(Pasted text|Image|\.\.\.Truncated text) #(\d+)(?: \+\d+ lines)?(\.)*\]'
    matches = list(re.finditer(pattern, input_text))
    result = []
    for match in matches:
        id_val = int(match.group(2) or '0')
        if id_val > 0:
            result.append({
                'id': id_val,
                'match': match.group(0),
                'index': match.start(),
            })
    return result


def expand_pasted_text_refs(
    input_text: str,
    pasted_contents: Dict[int, PastedContent],
) -> str:
    """Replace pasted text placeholders with actual content."""
    refs = parse_references(input_text)
    expanded = input_text
    # Process in reverse order to keep offsets valid
    for ref in reversed(refs):
        content = pasted_contents.get(ref['id'])
        if content is None or content.type != 'text':
            continue
        expanded = (
            expanded[:ref['index']] +
            content.content +
            expanded[ref['index'] + len(ref['match']):]
        )
    return expanded


# Module state
_pending_entries: List[LogEntry] = []
_is_writing: bool = False
_current_flush_future: Optional[asyncio.Future] = None
_cleanup_registered: bool = False
_last_added_entry: Optional[LogEntry] = None
_skipped_timestamps: Set[float] = set()


def _get_config_home_dir() -> Path:
    """Get Claude config home directory."""
    # Default to ~/.claude
    return Path.home() / '.claude'


def _get_history_path() -> Path:
    """Get history file path."""
    return _get_config_home_dir() / 'history.jsonl'


async def _read_lines_reverse(filepath: Path) -> AsyncGenerator[str, None]:
    """Read file lines in reverse order."""
    if not filepath.exists():
        return

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in reversed(lines):
                yield line.strip()
    except FileNotFoundError:
        return


async def _log_entry_to_history_entry(entry: LogEntry) -> HistoryEntry:
    """Convert LogEntry to HistoryEntry."""
    pasted_contents: Dict[int, PastedContent] = {}

    for id_val, stored in entry.pasted_contents.items():
        if stored.content:
            pasted_contents[id_val] = PastedContent(
                id=stored.id,
                type=stored.type,
                content=stored.content,
                media_type=stored.media_type,
                filename=stored.filename,
            )
        elif stored.content_hash:
            # For now, we don't have paste store, use placeholder
            pasted_contents[id_val] = PastedContent(
                id=stored.id,
                type=stored.type,
                content="[Large paste - not retrieved]",
                media_type=stored.media_type,
                filename=stored.filename,
            )

    return HistoryEntry(
        display=entry.display,
        pasted_contents=pasted_contents,
    )


async def _make_log_entry_reader() -> AsyncGenerator[LogEntry, None]:
    """Create async generator for log entries."""
    from ..bootstrap.state import get_session_id
    current_session = get_session_id()

    # Start with pending entries
    for entry in reversed(_pending_entries):
        yield entry

    # Read from history file
    history_path = _get_history_path()

    try:
        for line in await _read_lines_reverse(history_path):
            try:
                data = json.loads(line)
                entry = LogEntry(
                    display=data.get('display', ''),
                    pasted_contents={
                        int(k): StoredPastedContent(**v)
                        for k, v in data.get('pastedContents', {}).items()
                    },
                    timestamp=data.get('timestamp', 0),
                    project=data.get('project', ''),
                    session_id=data.get('sessionId'),
                )
                # Skip entries that were removed
                if (
                    entry.session_id == current_session and
                    entry.timestamp in _skipped_timestamps
                ):
                    continue
                yield entry
            except (json.JSONDecodeError, KeyError):
                continue
    except FileNotFoundError:
        return


async def make_history_reader() -> AsyncGenerator[HistoryEntry, None]:
    """Create async generator for history entries."""
    for entry in _make_log_entry_reader():
        yield await _log_entry_to_history_entry(entry)


async def get_timestamped_history() -> AsyncGenerator[TimestampedHistoryEntry, None]:
    """Get timestamped history entries for current project."""
    from ..bootstrap.state import get_project_root
    current_project = get_project_root()
    seen: Set[str] = set()

    async for entry in _make_log_entry_reader():
        if not entry or not isinstance(entry.project, str):
            continue
        if entry.project != current_project:
            continue
        if entry.display in seen:
            continue
        seen.add(entry.display)

        yield TimestampedHistoryEntry(
            display=entry.display,
            timestamp=entry.timestamp,
            resolve=lambda: _log_entry_to_history_entry(entry),
        )

        if len(seen) >= MAX_HISTORY_ITEMS:
            return


async def get_history() -> AsyncGenerator[HistoryEntry, None]:
    """Get history entries for current project."""
    from ..bootstrap.state import get_project_root, get_session_id
    current_project = get_project_root()
    current_session = get_session_id()
    other_session_entries: List[LogEntry] = []
    yielded = 0

    async for entry in _make_log_entry_reader():
        if not entry or not isinstance(entry.project, str):
            continue
        if entry.project != current_project:
            continue

        if entry.session_id == current_session:
            yield await _log_entry_to_history_entry(entry)
            yielded += 1
        else:
            other_session_entries.append(entry)

        if yielded + len(other_session_entries) >= MAX_HISTORY_ITEMS:
            break

    for entry in other_session_entries:
        if yielded >= MAX_HISTORY_ITEMS:
            return
        yield await _log_entry_to_history_entry(entry)
        yielded += 1


async def _immediate_flush_history() -> None:
    """Flush pending entries to disk."""
    if not _pending_entries:
        return

    history_path = _get_history_path()

    try:
        # Ensure directory exists
        history_path.parent.mkdir(parents=True, exist_ok=True)

        # Ensure file exists
        if not history_path.exists():
            history_path.touch()
            os.chmod(history_path, 0o600)

        # Write entries
        json_lines = [json.dumps({
            'display': e.display,
            'pastedContents': {
                str(k): {
                    'id': v.id,
                    'type': v.type,
                    'content': v.content,
                    'contentHash': v.content_hash,
                    'mediaType': v.media_type,
                    'filename': v.filename,
                }
                for k, v in e.pasted_contents.items()
            },
            'timestamp': e.timestamp,
            'project': e.project,
            'sessionId': e.session_id,
        }) + '\n' for e in _pending_entries]

        _pending_entries.clear()

        with open(history_path, 'a', encoding='utf-8') as f:
            f.writelines(json_lines)

    except Exception:
        # Not critical - log and continue
        pass


async def _flush_prompt_history(retries: int) -> None:
    """Flush prompt history with retries."""
    if _is_writing or not _pending_entries:
        return

    if retries > 5:
        return

    _is_writing = True

    try:
        await _immediate_flush_history()
    finally:
        _is_writing = False

        if _pending_entries:
            await asyncio.sleep(0.5)
            await _flush_prompt_history(retries + 1)


async def _add_to_prompt_history(command: HistoryEntry | str) -> None:
    """Add entry to prompt history."""
    from ..bootstrap.state import get_project_root, get_session_id

    if isinstance(command, str):
        entry = HistoryEntry(display=command, pasted_contents={})
    else:
        entry = command

    stored_pasted_contents: Dict[int, StoredPastedContent] = {}
    if entry.pasted_contents:
        for id_val, content in entry.pasted_contents.items():
            if content.type == 'image':
                continue

            if content.content and len(content.content) <= MAX_PASTED_CONTENT_LENGTH:
                stored_pasted_contents[id_val] = StoredPastedContent(
                    id=content.id,
                    type=content.type,
                    content=content.content,
                    media_type=content.media_type,
                    filename=content.filename,
                )
            elif content.content:
                # Large content - compute hash and store reference
                import hashlib
                hash_val = hashlib.sha256(content.content.encode()).hexdigest()[:16]
                stored_pasted_contents[id_val] = StoredPastedContent(
                    id=content.id,
                    type=content.type,
                    content_hash=hash_val,
                    media_type=content.media_type,
                    filename=content.filename,
                )

    log_entry = LogEntry(
        display=entry.display,
        pasted_contents=stored_pasted_contents,
        timestamp=time.time(),
        project=get_project_root(),
        session_id=get_session_id(),
    )

    _pending_entries.append(log_entry)
    _last_added_entry = log_entry

    await _flush_prompt_history(0)


def add_to_history(command: HistoryEntry | str) -> None:
    """Add command to history."""
    if os.environ.get('CLAUDE_CODE_SKIP_PROMPT_HISTORY'):
        return

    # Fire-and-forget async call
    try:
        asyncio.get_event_loop().create_task(_add_to_prompt_history(command))
    except RuntimeError:
        # No event loop running - schedule for later
        pass


def clear_pending_history_entries() -> None:
    """Clear pending history entries."""
    global _pending_entries, _last_added_entry
    _pending_entries.clear()
    _last_added_entry = None
    _skipped_timestamps.clear()


def remove_last_from_history() -> None:
    """Remove last added history entry."""
    global _last_added_entry
    if not _last_added_entry:
        return
    entry = _last_added_entry
    _last_added_entry = None

    try:
        idx = _pending_entries.index(entry)
        _pending_entries.pop(idx)
    except ValueError:
        _skipped_timestamps.add(entry.timestamp)


__all__ = [
    "PastedContent",
    "StoredPastedContent",
    "HistoryEntry",
    "LogEntry",
    "TimestampedHistoryEntry",
    "MAX_HISTORY_ITEMS",
    "MAX_PASTED_CONTENT_LENGTH",
    "get_pasted_text_ref_num_lines",
    "format_pasted_text_ref",
    "format_image_ref",
    "parse_references",
    "expand_pasted_text_refs",
    "make_history_reader",
    "get_timestamped_history",
    "get_history",
    "add_to_history",
    "clear_pending_history_entries",
    "remove_last_from_history",
]
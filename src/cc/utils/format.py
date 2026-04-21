"""Format Utilities - Display formatting helpers.

Pure display formatters for file sizes, durations, numbers,
relative time, and log metadata.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Optional, Dict, Any, List


def format_file_size(size_in_bytes: int) -> str:
    """Format byte count to human-readable string (KB, MB, GB)."""
    kb = size_in_bytes / 1024
    if kb < 1:
        return f"{size_in_bytes} bytes"
    if kb < 1024:
        return f"{kb:.1f}".rstrip("0").rstrip(".") + "KB"
    mb = kb / 1024
    if mb < 1024:
        return f"{mb:.1f}".rstrip("0").rstrip(".") + "MB"
    gb = mb / 1024
    return f"{gb:.1f}".rstrip("0").rstrip(".") + "GB"


def format_seconds_short(ms: float) -> str:
    """Format milliseconds as seconds with 1 decimal place."""
    return f"{ms / 1000:.1f}s"


def format_duration(
    ms: float,
    hide_trailing_zeros: bool = False,
    most_significant_only: bool = False,
) -> str:
    """Format duration in human-readable form."""
    if ms < 60000:
        if ms == 0:
            return "0s"
        if ms < 1:
            return f"{ms / 1000:.1f}s"
        return f"{int(ms / 1000)}s"

    days = int(ms // 86400000)
    hours = int((ms % 86400000) // 3600000)
    minutes = int((ms % 3600000) // 60000)
    seconds = round((ms % 60000) / 60000)

    # Handle rounding carry-over
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        hours += 1
    if hours == 24:
        hours = 0
        days += 1

    if most_significant_only:
        if days > 0:
            return f"{days}d"
        if hours > 0:
            return f"{hours}h"
        if minutes > 0:
            return f"{minutes}m"
        return f"{seconds}s"

    if days > 0:
        if hide_trailing_zeros and hours == 0 and minutes == 0:
            return f"{days}d"
        if hide_trailing_zeros and minutes == 0:
            return f"{days}d {hours}h"
        return f"{days}d {hours}h {minutes}m"

    if hours > 0:
        if hide_trailing_zeros and minutes == 0 and seconds == 0:
            return f"{hours}h"
        if hide_trailing_zeros and seconds == 0:
            return f"{hours}h {minutes}m"
        return f"{hours}h {minutes}m {seconds}s"

    if minutes > 0:
        if hide_trailing_zeros and seconds == 0:
            return f"{minutes}m"
        return f"{minutes}m {seconds}s"

    return f"{seconds}s"


def format_number(number: int) -> str:
    """Format number with K/M suffixes."""
    if number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.1f}b"
    if number >= 1_000_000:
        return f"{number / 1_000_000:.1f}m"
    if number >= 1_000:
        return f"{number / 1_000:.1f}k"
    return str(number)


def format_tokens(count: int) -> str:
    """Format token count."""
    return format_number(count).replace(".0", "")


def format_relative_time(
    date: datetime,
    now: Optional[datetime] = None,
    style: str = "narrow",
) -> str:
    """Format relative time from date."""
    if now is None:
        now = datetime.now()

    diff_in_ms = (date - now).total_seconds() * 1000
    diff_in_seconds = int(diff_in_ms / 1000)

    intervals = [
        ("year", 31536000, "y"),
        ("month", 2592000, "mo"),
        ("week", 604800, "w"),
        ("day", 86400, "d"),
        ("hour", 3600, "h"),
        ("minute", 60, "m"),
        ("second", 1, "s"),
    ]

    for unit, interval_seconds, short_unit in intervals:
        if abs(diff_in_seconds) >= interval_seconds:
            value = int(diff_in_seconds / interval_seconds)
            if style == "narrow":
                if diff_in_seconds < 0:
                    return f"{abs(value)}{short_unit} ago"
                return f"in {value}{short_unit}"
            # For other styles, use long format
            return f"{abs(value)} {unit}{'s' if abs(value) != 1 else ''} ago"

    return "0s ago"


def format_relative_time_ago(
    date: datetime,
    now: Optional[datetime] = None,
    style: str = "narrow",
) -> str:
    """Format relative time ago."""
    if now is None:
        now = datetime.now()

    if date > now:
        return format_relative_time(date, now, style)

    return format_relative_time(date, now, style)


def format_log_metadata(
    log: Dict[str, Any],
    now: Optional[datetime] = None,
) -> str:
    """Format log metadata for display."""
    modified = log.get("modified")
    if isinstance(modified, (int, float)):
        modified = datetime.fromtimestamp(modified)

    parts: List[str] = []

    if modified:
        parts.append(format_relative_time_ago(modified, now, style="short"))

    if log.get("gitBranch"):
        parts.append(log["gitBranch"])

    if log.get("fileSize"):
        parts.append(format_file_size(log["fileSize"]))
    elif log.get("messageCount"):
        parts.append(f"{log['messageCount']} messages")

    if log.get("tag"):
        parts.append(f"#{log['tag']}")

    if log.get("agentSetting"):
        parts.append(f"@{log['agentSetting']}")

    if log.get("prNumber"):
        pr_repo = log.get("prRepository")
        if pr_repo:
            parts.append(f"{pr_repo}#{log['prNumber']}")
        else:
            parts.append(f"#{log['prNumber']}")

    return " · ".join(parts)


def format_reset_time(
    timestamp_seconds: Optional[float],
    show_timezone: bool = False,
    show_time: bool = True,
) -> Optional[str]:
    """Format reset timestamp."""
    if not timestamp_seconds:
        return None

    date = datetime.fromtimestamp(timestamp_seconds)
    now = datetime.now()

    hours_until_reset = (date - now).total_seconds() / 3600

    if hours_until_reset > 24:
        # Show date and time for resets more than a day away
        if date.year != now.year:
            date_str = date.strftime("%b %d, %Y")
        else:
            date_str = date.strftime("%b %d")

        if show_time:
            time_str = date.strftime("%I:%M%p").lower().lstrip("0")
            result = f"{date_str} {time_str}"
        else:
            result = date_str

        if show_timezone:
            result += f" ({time.tzname[0]})"
        return result

    # For resets within 24 hours, show just the time
    time_str = date.strftime("%I:%M%p").lower().lstrip("0")
    if show_timezone:
        time_str += f" ({time.tzname[0]})"
    return time_str


def format_reset_text(
    resets_at: str,
    show_timezone: bool = False,
    show_time: bool = True,
) -> str:
    """Format reset text from ISO datetime string."""
    try:
        dt = datetime.fromisoformat(resets_at.replace("Z", "+00:00"))
        result = format_reset_time(dt.timestamp(), show_timezone, show_time)
        return result or ""
    except (ValueError, TypeError):
        return ""


def truncate(text: str, max_length: int = 50) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def truncate_path_middle(path: str, max_length: int = 50) -> str:
    """Truncate path keeping middle."""
    if len(path) <= max_length:
        return path

    # Keep first and last parts
    first_len = max_length // 2 - 1
    last_len = max_length // 2 - 2
    return path[:first_len] + "..." + path[-last_len:]


def truncate_to_width(text: str, width: int) -> str:
    """Truncate text to display width."""
    return truncate(text, width)


def wrap_text(text: str, width: int = 80) -> str:
    """Wrap text to specified width."""
    lines: List[str] = []
    current_line = ""

    for word in text.split():
        if len(current_line) + len(word) + 1 <= width:
            current_line += " " + word if current_line else word
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return "\n".join(lines)


__all__ = [
    "format_file_size",
    "format_seconds_short",
    "format_duration",
    "format_number",
    "format_tokens",
    "format_relative_time",
    "format_relative_time_ago",
    "format_log_metadata",
    "format_reset_time",
    "format_reset_text",
    "truncate",
    "truncate_path_middle",
    "truncate_to_width",
    "wrap_text",
]
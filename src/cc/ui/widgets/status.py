"""Status Line Widget - Terminal status line."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class StatusConfig:
    """Status line configuration."""
    show_model: bool = True
    show_tokens: bool = True
    show_cost: bool = False
    show_time: bool = True
    show_context: bool = True
    show_git: bool = True
    show_mode: bool = True
    color: str = "dim"
    separator: str = " | "


@dataclass
class StatusData:
    """Status line data."""
    model: str = ""
    tokens_used: int = 0
    tokens_max: int = 200000
    cost: float = 0.0
    elapsed_time: float = 0.0
    context_files: int = 0
    git_branch: str = ""
    git_status: str = ""
    mode: str = "normal"
    cwd: str = ""
    message: str = ""
    progress: float = 0.0


class StatusLine:
    """Terminal status line widget."""

    def __init__(self, config: StatusConfig = None):
        self._config = config or StatusConfig()
        self._data = StatusData()
        self._update_callback: Optional[Callable] = None
        self._timer_task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._running = False

    def start(self) -> None:
        """Start status line timer."""
        if self._running:
            return

        self._running = True
        self._started_at = datetime.now()
        self._timer_task = asyncio.create_task(self._update_timer())

    async def _update_timer(self) -> None:
        """Update elapsed time."""
        while self._running:
            self._data.elapsed_time = (
                datetime.now() - self._started_at
            ).total_seconds()
            self._render()
            await asyncio.sleep(1.0)

    def stop(self) -> float:
        """Stop status line.

        Returns:
            Total elapsed time
        """
        self._running = False

        if self._timer_task:
            self._timer_task.cancel()
            self._timer_task = None

        elapsed = self._data.elapsed_time
        self._started_at = None
        return elapsed

    def update(self, data: Dict[str, Any]) -> None:
        """Update status data.

        Args:
            data: Status data to update
        """
        for key, value in data.items():
            if hasattr(self._data, key):
                setattr(self._data, key, value)

        self._render()

    def set_model(self, model: str) -> None:
        """Set model name."""
        self._data.model = model
        self._render()

    def set_tokens(self, used: int, max: int = None) -> None:
        """Set token usage."""
        self._data.tokens_used = used
        if max:
            self._data.tokens_max = max
        self._render()

    def set_cost(self, cost: float) -> None:
        """Set cost."""
        self._data.cost = cost
        self._render()

    def set_context(self, files: int) -> None:
        """Set context files count."""
        self._data.context_files = files
        self._render()

    def set_git(self, branch: str, status: str = "") -> None:
        """Set git info."""
        self._data.git_branch = branch
        self._data.git_status = status
        self._render()

    def set_mode(self, mode: str) -> None:
        """Set editing mode."""
        self._data.mode = mode
        self._render()

    def set_cwd(self, cwd: str) -> None:
        """Set working directory."""
        self._data.cwd = cwd
        self._render()

    def set_message(self, message: str) -> None:
        """Set status message."""
        self._data.message = message
        self._render()

    def set_progress(self, progress: float) -> None:
        """Set progress."""
        self._data.progress = progress
        self._render()

    def _render(self) -> None:
        """Render status line."""
        parts = []

        # Model
        if self._config.show_model and self._data.model:
            parts.append(f"model: {self._data.model}")

        # Tokens
        if self._config.show_tokens:
            tokens_pct = self._data.tokens_used / self._data.tokens_max * 100
            token_color = "green" if tokens_pct < 50 else "yellow" if tokens_pct < 80 else "red"
            parts.append(f"tokens: {self._data.tokens_used}/{self._data.tokens_max} [{token_color}]")

        # Cost
        if self._config.show_cost and self._data.cost > 0:
            parts.append(f"cost: ${self._data.cost:.4f}")

        # Time
        if self._config.show_time and self._data.elapsed_time > 0:
            parts.append(f"time: {self._data.elapsed_time:.1f}s")

        # Context
        if self._config.show_context and self._data.context_files > 0:
            parts.append(f"context: {self._data.context_files} files")

        # Git
        if self._config.show_git and self._data.git_branch:
            git_str = f"git: {self._data.git_branch}"
            if self._data.git_status:
                git_str += f" [{self._data.git_status}]"
            parts.append(git_str)

        # Mode
        if self._config.show_mode and self._data.mode:
            parts.append(f"mode: {self._data.mode}")

        # Working directory
        if self._data.cwd:
            cwd_display = Path(self._data.cwd).name
            parts.append(f"cwd: {cwd_display}")

        # Message
        if self._data.message:
            parts.append(self._data.message)

        # Progress
        if self._data.progress > 0:
            progress_pct = self._data.progress * 100
            parts.append(f"progress: {progress_pct:.0f}%")

        # Build output
        output = self._config.separator.join(parts)

        # Call callback
        if self._update_callback:
            try:
                self._update_callback(output)
            except Exception:
                pass

    def set_update_callback(self, callback: Callable) -> None:
        """Set update callback."""
        self._update_callback = callback

    def get_status(self) -> StatusData:
        """Get current status data."""
        return self._data


class StatusManager:
    """Manage multiple status lines."""

    def __init__(self):
        self._status_lines: Dict[str, StatusLine] = {}
        self._outputs: Dict[str, str] = {}

    def create(self, name: str, config: StatusConfig = None) -> StatusLine:
        """Create status line.

        Args:
            name: Status line name
            config: Optional config

        Returns:
            StatusLine
        """
        status = StatusLine(config)
        status.set_update_callback(lambda output: self._update_output(name, output))
        self._status_lines[name] = status
        return status

    def _update_output(self, name: str, output: str) -> None:
        """Update output."""
        self._outputs[name] = output

    def start_all(self) -> None:
        """Start all status lines."""
        for status in self._status_lines.values():
            status.start()

    def stop_all(self) -> Dict[str, float]:
        """Stop all status lines."""
        elapsed = {}
        for name, status in self._status_lines.items():
            elapsed[name] = status.stop()
        return elapsed

    def get(self, name: str) -> Optional[StatusLine]:
        """Get status line."""
        return self._status_lines.get(name)

    def get_output(self) -> str:
        """Get combined output."""
        return "\n".join(self._outputs.values())


# Global status line
_main_status: Optional[StatusLine] = None


def get_status_line(config: StatusConfig = None) -> StatusLine:
    """Get main status line."""
    global _main_status
    if _main_status is None:
        _main_status = StatusLine(config)
    return _main_status


__all__ = [
    "StatusConfig",
    "StatusData",
    "StatusLine",
    "StatusManager",
    "get_status_line",
]

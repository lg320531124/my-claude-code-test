"""Spinner Widget - Loading animation widget."""

from __future__ import annotations
import asyncio
from typing import Any, Dict, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime


class SpinnerStyle(Enum):
    """Spinner animation styles."""
    DOTS = "dots"
    LINE = "line"
    CIRCLE = "circle"
    ARROWS = "arrows"
    BOUNCE = "bounce"
    PULSE = "pulse"
    BRAILLE = "braille"


# Animation frames
SPINNER_FRAMES: Dict[SpinnerStyle, List[str]] = {
    SpinnerStyle.DOTS: ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
    SpinnerStyle.LINE: ["-", "=", "≡", "≣", "=", "-"],
    SpinnerStyle.CIRCLE: ["◜", "◠", "◝", "◞", "◡", "◟"],
    SpinnerStyle.ARROWS: ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
    SpinnerStyle.BOUNCE: ["⠁", "⠂", "⠄", "⡀", "⢀", "⠄", "⠂", "⠁"],
    SpinnerStyle.PULSE: ["∎", "∎∎", "∎∎∎", "∎∎∎∎"],
    SpinnerStyle.BRAILLE: ["⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"],
}


@dataclass
class SpinnerConfig:
    """Spinner configuration."""
    style: SpinnerStyle = SpinnerStyle.DOTS
    text: str = "Loading..."
    color: str = "cyan"
    interval: float = 0.08
    show_elapsed: bool = True
    show_progress: bool = False
    progress: float = 0.0


class SpinnerWidget:
    """Async spinner animation widget."""

    def __init__(self, config: SpinnerConfig = None):
        self._config = config or SpinnerConfig()
        self._frames = SPINNER_FRAMES.get(self._config.style, SPINNER_FRAMES[SpinnerStyle.DOTS])
        self._frame_index = 0
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._started_at: Optional[datetime] = None
        self._update_callback: Optional[Callable] = None

    def start(self, text: str = None) -> None:
        """Start spinner animation.

        Args:
            text: Optional text to display
        """
        if self._running:
            return

        self._running = True
        self._started_at = datetime.now()

        if text:
            self._config.text = text

        self._task = asyncio.create_task(self._animate())

    async def _animate(self) -> None:
        """Animate spinner frames."""
        while self._running:
            frame = self._frames[self._frame_index]
            self._frame_index = (self._frame_index + 1) % len(self._frames)

            # Build output
            output = self._build_output(frame)

            # Call update callback
            if self._update_callback:
                try:
                    if asyncio.iscoroutinefunction(self._update_callback):
                        await self._update_callback(output)
                    else:
                        self._update_callback(output)
                except Exception:
                    pass

            await asyncio.sleep(self._config.interval)

    def _build_output(self, frame: str) -> str:
        """Build output string.

        Args:
            frame: Current animation frame

        Returns:
            Output string
        """
        parts = [frame]

        if self._config.text:
            parts.append(self._config.text)

        if self._config.show_elapsed and self._started_at:
            elapsed = (datetime.now() - self._started_at).total_seconds()
            parts.append(f"[{elapsed:.1f}s]")

        if self._config.show_progress:
            progress_pct = self._config.progress * 100
            parts.append(f"[{progress_pct:.0f}%]")

        return " ".join(parts)

    def stop(self) -> str:
        """Stop spinner animation.

        Returns:
            Final elapsed time string
        """
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                asyncio.get_event_loop().run_until_complete(self._task)
            except asyncio.CancelledError:
                pass
            self._task = None

        elapsed = ""
        if self._started_at:
            elapsed = f"{(datetime.now() - self._started_at).total_seconds():.1f}s"

        self._started_at = None
        return elapsed

    def update_text(self, text: str) -> None:
        """Update spinner text.

        Args:
            text: New text
        """
        self._config.text = text

    def update_progress(self, progress: float) -> None:
        """Update progress value.

        Args:
            progress: Progress (0.0 to 1.0)
        """
        self._config.progress = progress
        self._config.show_progress = True

    def set_style(self, style: SpinnerStyle) -> None:
        """Set animation style.

        Args:
            style: New style
        """
        self._config.style = style
        self._frames = SPINNER_FRAMES.get(style, SPINNER_FRAMES[SpinnerStyle.DOTS])
        self._frame_index = 0

    def set_update_callback(self, callback: Callable) -> None:
        """Set update callback.

        Args:
            callback: Callback function for output updates
        """
        self._update_callback = callback

    @property
    def is_running(self) -> bool:
        """Check if spinner is running."""
        return self._running

    @property
    def elapsed(self) -> float:
        """Get elapsed time."""
        if self._started_at:
            return (datetime.now() - self._started_at).total_seconds()
        return 0.0


class MultiSpinner:
    """Multiple concurrent spinners."""

    def __init__(self):
        self._spinners: Dict[str, SpinnerWidget] = {}
        self._outputs: Dict[str, str] = {}

    def add(self, name: str, config: SpinnerConfig = None) -> SpinnerWidget:
        """Add spinner.

        Args:
            name: Spinner name
            config: Optional config

        Returns:
            SpinnerWidget
        """
        spinner = SpinnerWidget(config)
        spinner.set_update_callback(lambda output: self._update_output(name, output))
        self._spinners[name] = spinner
        return spinner

    def _update_output(self, name: str, output: str) -> None:
        """Update output for spinner.

        Args:
            name: Spinner name
            output: Output string
        """
        self._outputs[name] = output

    def start_all(self) -> None:
        """Start all spinners."""
        for spinner in self._spinners.values():
            spinner.start()

    def stop_all(self) -> Dict[str, str]:
        """Stop all spinners.

        Returns:
            Dict of elapsed times
        """
        elapsed = {}
        for name, spinner in self._spinners.items():
            elapsed[name] = spinner.stop()
        return elapsed

    def start(self, name: str, text: str = None) -> None:
        """Start specific spinner.

        Args:
            name: Spinner name
            text: Optional text
        """
        if name in self._spinners:
            self._spinners[name].start(text)

    def stop(self, name: str) -> str:
        """Stop specific spinner.

        Args:
            name: Spinner name

        Returns:
            Elapsed time
        """
        if name in self._spinners:
            return self._spinners[name].stop()
        return ""

    def get_output(self) -> str:
        """Get combined output.

        Returns:
            Combined output string
        """
        return "\n".join(self._outputs.values())


# Global spinner for CLI
_main_spinner: Optional[SpinnerWidget] = None


def get_spinner(config: SpinnerConfig = None) -> SpinnerWidget:
    """Get main spinner."""
    global _main_spinner
    if _main_spinner is None:
        _main_spinner = SpinnerWidget(config)
    return _main_spinner


def start_spinner(text: str = "Loading...") -> None:
    """Start main spinner."""
    get_spinner().start(text)


def stop_spinner() -> str:
    """Stop main spinner."""
    return get_spinner().stop()


__all__ = [
    "SpinnerStyle",
    "SPINNER_FRAMES",
    "SpinnerConfig",
    "SpinnerWidget",
    "MultiSpinner",
    "get_spinner",
    "start_spinner",
    "stop_spinner",
]

"""Onboarding Screen - New user introduction."""

from __future__ import annotations
from textual.widget import Widget
from textual.widgets import Static, Button, ProgressBar
from textual.reactive import reactive
from textual.message import Message
from textual.screen import Screen
from textual.binding import Binding
from textual.containers import Container, VerticalScroll, Horizontal
from rich.text import Text


class OnboardingScreen(Screen):
    """New user onboarding flow."""

    CSS = """
    OnboardingScreen {
        layout: vertical;
        align: center middle;
    }

    OnboardingScreen > Container {
        width: 80;
        height: 30;
        background: $surface;
        padding: 3;
    }

    .step-content {
        height: 1fr;
    }

    .navigation {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("escape", "skip", "Skip"),
        Binding("enter", "next", "Next"),
    ]

    current_step: reactive[int] = reactive(0)
    total_steps: reactive[int] = reactive(6)
    completed: reactive[bool] = reactive(False)
    user_name: reactive[str] = reactive("")
    selected_model: reactive[str] = reactive("claude-sonnet-4-6")
    selected_theme: reactive[str] = reactive("dark")
    vim_mode_enabled: reactive[bool] = reactive(False)

    class Completed(Message):
        """Onboarding completed."""
        config: dict

        def __init__(self, config: dict):
            self.config = config
            super().__init__()

    class Skipped(Message):
        """Onboarding skipped."""

    def compose(self):
        """Compose screen."""
        yield Container(
            Static("[bold cyan]Welcome to Claude Code[/]", classes="title"),
            ProgressBar(total=self.total_steps, progress=self.current_step),
            VerticalScroll(
                Static("", id="step-content"),
                classes="step-content"
            ),
            Horizontal(
                Button("← Back", id="back", variant="default"),
                Button("Next →", id="next", variant="primary"),
                classes="navigation"
            )
        )

    def on_mount(self) -> None:
        """Show first step."""
        self._show_step()

    def _show_step(self) -> None:
        """Show current step content."""
        content = self.query_one("#step-content", Static)

        steps = [
            self._step_welcome,
            self._step_introduction,
            self._step_setup_name,
            self._step_select_model,
            self._step_select_theme,
            self._step_vim_mode,
            self._step_complete,
        ]

        if self.current_step < len(steps):
            content.update(steps[self.current_step]())

    def _step_welcome(self) -> str:
        """Welcome step."""
        return """
[bold cyan]Welcome to Claude Code CLI[/bold cyan]

Claude Code is your AI-powered coding assistant.

[bold]What it can do:[/bold]
  • Read, write, and edit files
  • Execute bash commands safely
  • Search and analyze codebases
  • Run tests and fix bugs
  • Create commits and pull requests
  • And much more!

[dim]Press Enter to continue[/]
"""

    def _step_introduction(self) -> str:
        """Introduction step."""
        return """
[bold cyan]How Claude Code Works[/bold cyan]

[bold]1. Ask[/bold] - Type your request naturally
[bold]2. Tools[/bold] - Claude uses tools to help you
[bold]3. Iterate[/bold] - Work together until done

[bold]Key Features:[/bold]
  • [cyan]Tools[/] - File operations, bash, search
  • [cyan]Agents[/] - Specialized sub-agents for complex tasks
  • [cyan]Sessions[/] - Persistent conversation history
  • [cyan]MCP[/] - Connect external tools via MCP

[dim]Press Enter to continue[/]
"""

    def _step_setup_name(self) -> str:
        """Setup name step."""
        return """
[bold cyan]Personalize Your Experience[/bold cyan]

[bold]Your Name[/bold]
This helps Claude personalize responses.

[dim]Enter your name below (optional):[/]
"""

    def _step_select_model(self) -> str:
        """Model selection step."""
        return """
[bold cyan]Choose Your Model[/bold cyan]

[bold]Available Models:[/bold]

  [purple]Opus 4.7[/] - Maximum reasoning, complex tasks
  [cyan]Sonnet 4.6[/] - Best for coding, recommended
  [green]Haiku 4.5[/] - Fast, economical, good for simple tasks

[bold]Recommendation:[/bold]
[cyan]Claude Sonnet 4.6[/] is recommended for most coding tasks.

[dim]Press Enter to use recommended, or type to change[/]
"""

    def _step_select_theme(self) -> str:
        """Theme selection step."""
        return """
[bold cyan]Select Theme[/bold cyan]

Available themes:
  [cyan]dark[/] - Catppuccin Dark (default)
  [cyan]light[/] - Catppuccin Light
  [cyan]mono[/] - Monochrome
  [cyan]gruvbox[/] - Gruvbox Dark
  [cyan]nord[/] - Nord
  [cyan]dracula[/] - Dracula
  [cyan]solarized[/] - Solarized Dark

[bold]Current: [cyan]dark[/][/bold]

[dim]Press Enter to keep current, or type theme name[/]
"""

    def _step_vim_mode(self) -> str:
        """Vim mode step."""
        return """
[bold cyan]Enable Vim Mode?[/bold cyan]

Vim mode provides:
  • j/k for navigation
  • i for insert mode
  • : for command mode
  • Standard Vim commands

[bold]Current: [dim]disabled[/][/bold]

[dim]Press Enter to skip, or 'y' to enable[/]
"""

    def _step_complete(self) -> str:
        """Complete step."""
        return """
[bold green]Setup Complete![/bold green]

[bold]Your Configuration:[/bold]
  • Model: [cyan]{self.selected_model}[/cyan]
  • Theme: [cyan]{self.selected_theme}[/cyan]
  • Vim Mode: [cyan]{self.vim_mode_enabled}[/cyan]

[bold]Next Steps:[/bold]
  • Try asking: "What files are in this project?"
  • Use /help for commands
  • Use /doctor to check setup

[bold green]Press Enter to start using Claude Code[/bold green]
"""

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle navigation."""
        if event.button.id == "next":
            self._next_step()
        elif event.button.id == "back":
            self._prev_step()

    def _next_step(self) -> None:
        """Go to next step."""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
            self._show_step()
        else:
            # Complete onboarding
            config = {
                "user_name": self.user_name,
                "model": self.selected_model,
                "theme": self.selected_theme,
                "vim_mode": self.vim_mode_enabled,
            }
            self.post_message(self.Completed(config))
            self.app.pop_screen()

    def _prev_step(self) -> None:
        """Go to previous step."""
        if self.current_step > 0:
            self.current_step -= 1
            self._show_step()

    def action_skip(self) -> None:
        """Skip onboarding."""
        self.post_message(self.Skipped())
        self.app.pop_screen()

    def action_next(self) -> None:
        """Next action."""
        self._next_step()


class OnboardingCompleteWidget(Widget):
    """Widget showing onboarding status."""

    DEFAULT_CSS = """
    OnboardingCompleteWidget {
        width: 20;
        height: 1;
    }
    """

    completed: reactive[bool] = reactive(False)

    def render(self) -> Text:
        """Render status."""
        if self.completed:
            return Text("[green]✓ Onboarding complete[/]")
        return Text("[dim]Setup needed[/]")


__all__ = [
    "OnboardingScreen",
    "OnboardingCompleteWidget",
]
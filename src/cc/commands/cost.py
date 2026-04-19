"""Cost command - Usage tracking."""

from __future__ import annotations
from rich.console import Console
from rich.table import Table


def run_cost(console: Console) -> None:
    """Show usage cost."""
    from ..core.session import Session

    # This would normally track actual API usage
    # Placeholder for demonstration

    table = Table(title="Usage Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value")

    # Placeholder values
    table.add_row("Input Tokens", "12,450")
    table.add_row("Output Tokens", "3,890")
    table.add_row("Total Tokens", "16,340")
    table.add_row("API Calls", "5")
    table.add_row("Tool Calls", "8")
    table.add_row("Estimated Cost", "$0.25")

    console.print(table)

    console.print("\n[dim]Note: Usage tracking requires API logging[/dim]")
    console.print("[dim]Install tracking: Set LOG_API_USAGE=true[/dim]")


class CostTracker:
    """Track API usage costs."""

    def __init__(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.api_calls = 0
        self.tool_calls = 0

    def record_usage(self, input_tokens: int, output_tokens: int) -> None:
        """Record API usage."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.api_calls += 1

    def record_tool_call(self) -> None:
        """Record tool call."""
        self.tool_calls += 1

    def estimate_cost(self, model: str = "claude-sonnet-4-6") -> float:
        """Estimate cost in USD."""
        # Claude pricing (approximate)
        prices = {
            "claude-opus-4-5": {"input": 15.0, "output": 75.0},  # per million tokens
            "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
            "claude-haiku-4-5": {"input": 0.25, "output": 1.25},
            "glm-5": {"input": 0.5, "output": 2.0},  # 智谱 approximate
        }

        price = prices.get(model, {"input": 3.0, "output": 15.0})

        input_cost = (self.input_tokens / 1_000_000) * price["input"]
        output_cost = (self.output_tokens / 1_000_000) * price["output"]

        return input_cost + output_cost

    def get_summary(self) -> dict:
        """Get usage summary."""
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.input_tokens + self.output_tokens,
            "api_calls": self.api_calls,
            "tool_calls": self.tool_calls,
        }


# Global tracker
_cost_tracker = CostTracker()


def get_tracker() -> CostTracker:
    """Get global cost tracker."""
    return _cost_tracker

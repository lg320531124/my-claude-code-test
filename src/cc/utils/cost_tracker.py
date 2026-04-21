"""Cost Tracker - Cost and usage tracking for sessions.

Handles cost accumulation, model usage tracking, session cost
storage and restoration, and cost formatting.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Dict, Any
from pathlib import Path
import json

from ..bootstrap.state import (
    get_session_id,
    get_total_duration,
    get_state,
)


@dataclass
class ModelUsage:
    """Model usage statistics."""
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    web_search_requests: int = 0
    cost_usd: float = 0.0
    context_window: int = 0
    max_output_tokens: int = 0


@dataclass
class StoredCostState:
    """Stored cost state for session restoration."""
    total_cost_usd: float = 0.0
    total_api_duration: float = 0.0
    total_api_duration_without_retries: float = 0.0
    total_tool_duration: float = 0.0
    total_lines_added: int = 0
    total_lines_removed: int = 0
    last_duration: Optional[float] = None
    model_usage: Optional[Dict[str, ModelUsage]] = None


def _get_project_config_path() -> Path:
    """Get project config path."""
    from ..bootstrap.state import get_project_root
    return Path(get_project_root()) / ".claude" / "config.json"


def get_current_project_config() -> Dict[str, Any]:
    """Get current project configuration."""
    config_path = _get_project_config_path()
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def save_current_project_config(data: Dict[str, Any]) -> None:
    """Save current project configuration."""
    config_path = _get_project_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(data, f)


def get_stored_session_costs(session_id: str) -> Optional[StoredCostState]:
    """Get stored cost state from project config for a specific session."""
    project_config = get_current_project_config()

    if project_config.get("lastSessionId") != session_id:
        return None

    model_usage = None
    if project_config.get("lastModelUsage"):
        model_usage = {
            model: ModelUsage(
                input_tokens=usage.get("inputTokens", 0),
                output_tokens=usage.get("outputTokens", 0),
                cache_read_input_tokens=usage.get("cacheReadInputTokens", 0),
                cache_creation_input_tokens=usage.get("cacheCreationInputTokens", 0),
                web_search_requests=usage.get("webSearchRequests", 0),
                cost_usd=usage.get("costUSD", 0.0),
                context_window=usage.get("contextWindow", 0),
                max_output_tokens=usage.get("maxOutputTokens", 0),
            )
            for model, usage in project_config["lastModelUsage"].items()
        }

    return StoredCostState(
        total_cost_usd=project_config.get("lastCost", 0),
        total_api_duration=project_config.get("lastAPIDuration", 0),
        total_api_duration_without_retries=project_config.get("lastAPIDurationWithoutRetries", 0),
        total_tool_duration=project_config.get("lastToolDuration", 0),
        total_lines_added=project_config.get("lastLinesAdded", 0),
        total_lines_removed=project_config.get("lastLinesRemoved", 0),
        last_duration=project_config.get("lastDuration"),
        model_usage=model_usage,
    )


def restore_cost_state_for_session(session_id: str) -> bool:
    """Restore cost state from project config when resuming a session."""
    data = get_stored_session_costs(session_id)
    if not data:
        return False

    state = get_state()
    state.total_cost_usd = data.total_cost_usd
    state.total_api_duration = data.total_api_duration
    state.total_api_duration_without_retries = data.total_api_duration_without_retries
    state.total_tool_duration = data.total_tool_duration
    state.total_lines_added = data.total_lines_added
    state.total_lines_removed = data.total_lines_removed

    return True


def save_current_session_costs(fps_metrics: Optional[Dict[str, float]] = None) -> None:
    """Save the current session's costs to project config."""
    state = get_state()

    model_usage_data = {
        model: {
            "inputTokens": usage.input_tokens,
            "outputTokens": usage.output_tokens,
            "cacheReadInputTokens": usage.cache_read_input_tokens,
            "cacheCreationInputTokens": usage.cache_creation_input_tokens,
            "webSearchRequests": usage.web_search_requests,
            "costUSD": usage.cost_usd,
        }
        for model, usage in state.model_usage.items()
    }

    project_config = get_current_project_config()
    project_config.update({
        "lastCost": state.total_cost_usd,
        "lastAPIDuration": state.total_api_duration,
        "lastAPIDurationWithoutRetries": state.total_api_duration_without_retries,
        "lastToolDuration": state.total_tool_duration,
        "lastDuration": get_total_duration(),
        "lastLinesAdded": state.total_lines_added,
        "lastLinesRemoved": state.total_lines_removed,
        "lastTotalInputTokens": sum(u.input_tokens for u in state.model_usage.values()),
        "lastTotalOutputTokens": sum(u.output_tokens for u in state.model_usage.values()),
        "lastTotalCacheCreationInputTokens": sum(u.cache_creation_input_tokens for u in state.model_usage.values()),
        "lastTotalCacheReadInputTokens": sum(u.cache_read_input_tokens for u in state.model_usage.values()),
        "lastTotalWebSearchRequests": sum(u.web_search_requests for u in state.model_usage.values()),
        "lastFpsAverage": fps_metrics.get("averageFps") if fps_metrics else None,
        "lastFpsLow1Pct": fps_metrics.get("low1PctFps") if fps_metrics else None,
        "lastModelUsage": model_usage_data,
        "lastSessionId": get_session_id(),
    })

    save_current_project_config(project_config)


def format_cost(cost: float, max_decimal_places: int = 4) -> str:
    """Format cost in USD."""
    if cost > 0.5:
        return f"${round_value(cost, 100):.2f}"
    return f"${cost:.{max_decimal_places}f}"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable form."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}m {secs:.0f}s"


def format_number(num: int) -> str:
    """Format number with K/M suffixes."""
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def round_value(number: float, precision: int) -> float:
    """Round number to precision."""
    return math.round(number * precision) / precision


def get_model_usage() -> Dict[str, ModelUsage]:
    """Get model usage map."""
    return get_state().model_usage


def get_usage_for_model(model: str) -> Optional[ModelUsage]:
    """Get usage for specific model."""
    return get_state().model_usage.get(model)


def format_model_usage() -> str:
    """Format model usage for display."""
    model_usage_map = get_model_usage()
    if not model_usage_map:
        return "Usage:                 0 input, 0 output, 0 cache read, 0 cache write"

    result = "Usage by model:"
    for model, usage in model_usage_map.items():
        usage_string = (
            f"  {format_number(usage.input_tokens)} input, "
            f"{format_number(usage.output_tokens)} output, "
            f"{format_number(usage.cache_read_input_tokens)} cache read, "
            f"{format_number(usage.cache_creation_input_tokens)} cache write"
        )
        if usage.web_search_requests > 0:
            usage_string += f", {format_number(usage.web_search_requests)} web search"
        usage_string += f" ({format_cost(usage.cost_usd)})"

        result += f"\n{model + ':':>21}{usage_string}"

    return result


def format_total_cost() -> str:
    """Format total cost for display."""
    state = get_state()
    cost_display = format_cost(state.total_cost_usd)

    if state.has_unknown_model_cost:
        cost_display += " (costs may be inaccurate due to usage of unknown models)"

    model_usage_display = format_model_usage()

    lines_word = "line" if state.total_lines_added == 1 else "lines"

    return (
        f"Total cost:            {cost_display}\n"
        f"Total duration (API):  {format_duration(state.total_api_duration)}\n"
        f"Total duration (wall): {format_duration(get_total_duration())}\n"
        f"Total code changes:    {state.total_lines_added} {lines_word} added, "
        f"{state.total_lines_removed} {'line' if state.total_lines_removed == 1 else 'lines'} removed\n"
        f"{model_usage_display}"
    )


def add_to_total_session_cost(
    cost: float,
    usage: Dict[str, Any],
    model: str,
) -> float:
    """Add to total session cost and usage."""
    state = get_state()

    model_usage = state.model_usage.get(model, ModelUsage())
    model_usage.input_tokens += usage.get("input_tokens", 0)
    model_usage.output_tokens += usage.get("output_tokens", 0)
    model_usage.cache_read_input_tokens += usage.get("cache_read_input_tokens", 0)
    model_usage.cache_creation_input_tokens += usage.get("cache_creation_input_tokens", 0)
    model_usage.web_search_requests += usage.get("web_search_requests", 0)
    model_usage.cost_usd += cost

    state.model_usage[model] = model_usage
    state.total_cost_usd += cost

    return cost


def reset_cost_state() -> None:
    """Reset cost state."""
    state = get_state()
    state.total_cost_usd = 0.0
    state.total_api_duration = 0.0
    state.total_api_duration_without_retries = 0.0
    state.total_tool_duration = 0.0
    state.total_lines_added = 0
    state.total_lines_removed = 0
    state.model_usage.clear()
    state.has_unknown_model_cost = False


def has_unknown_model_cost() -> bool:
    """Check if unknown model cost exists."""
    return get_state().has_unknown_model_cost


def set_has_unknown_model_cost(value: bool) -> None:
    """Set unknown model cost flag."""
    get_state().has_unknown_model_cost = value


__all__ = [
    "ModelUsage",
    "StoredCostState",
    "get_stored_session_costs",
    "restore_cost_state_for_session",
    "save_current_session_costs",
    "format_cost",
    "format_duration",
    "format_number",
    "format_model_usage",
    "format_total_cost",
    "add_to_total_session_cost",
    "reset_cost_state",
    "has_unknown_model_cost",
    "set_has_unknown_model_cost",
    "get_model_usage",
    "get_usage_for_model",
    "get_current_project_config",
    "save_current_project_config",
]
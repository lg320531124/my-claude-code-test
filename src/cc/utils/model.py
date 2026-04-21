"""Model Selection Utilities - Model selection and configuration."""

from __future__ import annotations
from typing import Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from ..services.token_estimation import TokenBudget


class ModelFamily(Enum):
    """Claude model families."""
    OPUS = "opus"
    SONNET = "sonnet"
    HAIKU = "haiku"


class APIProvider(Enum):
    """API providers."""
    DIRECT = "direct"  # Anthropic direct
    BEDROCK = "bedrock"  # AWS Bedrock
    VERTEX = "vertex"  # Google Vertex
    FOUNDRY = "foundry"  # Internal
    COMPAT = "compat"  # Compatible endpoint


@dataclass
class ModelInfo:
    """Model information."""
    id: str
    display_name: str
    family: ModelFamily
    max_tokens: int
    max_output_tokens: int
    input_price: float  # per 1M tokens
    output_price: float  # per 1M tokens
    features: List[str]
    supports_thinking: bool = True
    supports_vision: bool = True


AVAILABLE_MODELS: Dict[str, ModelInfo] = {
    "claude-opus-4-7": ModelInfo(
        id="claude-opus-4-7",
        display_name="Claude Opus 4.7",
        family=ModelFamily.OPUS,
        max_tokens=200000,
        max_output_tokens=16384,
        input_price=15.0,
        output_price=75.0,
        features=["vision", "extended_thinking", "tools", "code"],
        supports_thinking=True,
        supports_vision=True,
    ),
    "claude-sonnet-4-6": ModelInfo(
        id="claude-sonnet-4-6",
        display_name="Claude Sonnet 4.6",
        family=ModelFamily.SONNET,
        max_tokens=200000,
        max_output_tokens=16384,
        input_price=3.0,
        output_price=15.0,
        features=["vision", "extended_thinking", "tools", "code"],
        supports_thinking=True,
        supports_vision=True,
    ),
    "claude-haiku-4-5-20251001": ModelInfo(
        id="claude-haiku-4-5-20251001",
        display_name="Claude Haiku 4.5",
        family=ModelFamily.HAIKU,
        max_tokens=200000,
        max_output_tokens=8192,
        input_price=0.80,
        output_price=4.0,
        features=["vision", "tools", "code"],
        supports_thinking=False,
        supports_vision=True,
    ),
}


class ModelSelector:
    """Select appropriate model for task."""

    def __init__(self, default_model: str = "claude-sonnet-4-6"):
        self.default_model = default_model
        self._current_model = default_model

    def get_model(self) -> ModelInfo:
        """Get current model info."""
        return AVAILABLE_MODELS.get(self._current_model)

    def set_model(self, model_id: str) -> bool:
        """Set model by ID."""
        if model_id in AVAILABLE_MODELS:
            self._current_model = model_id
            return True
        return False

    def select_for_task(self, task_type: str, budget: TokenBudget = None) -> str:
        """Select best model for task."""
        # Complex tasks → Opus
        complex_tasks = ["architecture", "planning", "research", "analysis"]
        if task_type in complex_tasks:
            return "claude-opus-4-7"

        # Development tasks → Sonnet
        dev_tasks = ["coding", "debugging", "refactoring", "review"]
        if task_type in dev_tasks:
            return "claude-sonnet-4-6"

        # Simple tasks → Haiku
        simple_tasks = ["formatting", "quick_edit", "documentation"]
        if task_type in simple_tasks:
            return "claude-haiku-4-5-20251001"

        # Budget constraints
        if budget:
            if budget.max_total_tokens < 50000:
                return "claude-haiku-4-5-20251001"

        return self.default_model

    def get_model_for_agent(self, agent_type: str) -> str:
        """Get model for specific agent."""
        # Heavy reasoning agents → Opus
        if agent_type in ["planner", "architect", "reviewer"]:
            return "claude-opus-4-7"

        # Development agents → Sonnet
        if agent_type in ["coder", "debugger", "tdd-guide"]:
            return "claude-sonnet-4-6"

        # Lightweight agents → Haiku
        if agent_type in ["explorer", "validator", "helper"]:
            return "claude-haiku-4-5-20251001"

        return self.default_model

    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate cost for current model."""
        model = self.get_model()
        if not model:
            return 0

        input_cost = (input_tokens / 1_000_000) * model.input_price
        output_cost = (output_tokens / 1_000_000) * model.output_price

        return input_cost + output_cost


def get_provider_config(provider: APIProvider) -> Dict[str, Any]:
    """Get configuration for provider."""
    configs = {
        APIProvider.DIRECT: {
            "base_url": "https://api.anthropic.com",
            "auth_type": "x-api-key",
        },
        APIProvider.BEDROCK: {
            "base_url": "bedrock-runtime",
            "auth_type": "aws",
        },
        APIProvider.VERTEX: {
            "base_url": "vertex-ai.googleapis.com",
            "auth_type": "oauth",
        },
        APIProvider.COMPAT: {
            "base_url": "",  # User configured
            "auth_type": "bearer",
        },
    }

    return configs.get(provider, configs[APIProvider.DIRECT])


def validate_model_id(model_id: str) -> bool:
    """Validate model ID."""
    return model_id in AVAILABLE_MODELS


def get_model_families() -> List[ModelFamily]:
    """Get all model families."""
    return list(ModelFamily)


__all__ = [
    "ModelFamily",
    "APIProvider",
    "ModelInfo",
    "AVAILABLE_MODELS",
    "ModelSelector",
    "get_provider_config",
    "validate_model_id",
    "get_model_families",
]
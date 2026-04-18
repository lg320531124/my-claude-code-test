"""Tests for configuration."""

import pytest
from pathlib import Path
import tempfile

from cc.utils.config import Config, APIConfig
from cc.types.permission import PermissionConfig


def test_default_config():
    """Test default configuration."""
    config = Config()
    assert config.api.model == "claude-sonnet-4-6"
    assert config.api.provider == "anthropic"
    assert config.ui.theme == "dark"


def test_config_save_load():
    """Test save and load configuration."""
    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "config.json"

        config = Config(
            api=APIConfig(model="claude-opus-4-5"),
        )
        config.save(path)

        loaded = Config.load(path)
        assert loaded.api.model == "claude-opus-4-5"


def test_permission_config():
    """Test permission configuration."""
    perm = PermissionConfig(
        allow=["Read", "Bash(ls *)"],
        deny=["Bash(rm *)"],
        ask=["Write"],
    )

    rules = perm.to_rules()
    assert len(rules) == 3

    # Deny rules have highest priority
    deny_rules = [r for r in rules if r.decision.value == "deny"]
    assert len(deny_rules) == 1
    assert deny_rules[0].pattern == "Bash(rm *)"


def test_env_overrides():
    """Test environment variable overrides."""
    import os

    config = Config()

    # Mock env vars
    original_model = os.environ.get("ANTHROPIC_MODEL")
    original_base = os.environ.get("ANTHROPIC_BASE_URL")

    os.environ["ANTHROPIC_MODEL"] = "claude-haiku-4-5"
    os.environ["ANTHROPIC_BASE_URL"] = "https://custom.api.com"

    overrides = config.get_env_overrides()
    assert overrides.get("model") == "claude-haiku-4-5"
    assert overrides.get("base_url") == "https://custom.api.com"

    # Restore
    if original_model:
        os.environ["ANTHROPIC_MODEL"] = original_model
    else:
        os.environ.pop("ANTHROPIC_MODEL", None)

    if original_base:
        os.environ["ANTHROPIC_BASE_URL"] = original_base
    else:
        os.environ.pop("ANTHROPIC_BASE_URL", None)
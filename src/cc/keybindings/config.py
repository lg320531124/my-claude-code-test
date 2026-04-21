"""Keybindings Configuration - Load and save keybindings configuration.

Supports JSON and YAML configuration files for custom keybindings.
"""

from __future__ import annotations
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from . import KeyBinding, KeySequence, KeyMode, Platform, KeybindingsManager


@dataclass
class KeybindingConfig:
    """Keybinding configuration file format."""
    bindings: List[Dict[str, Any]]
    sequences: List[Dict[str, Any]]
    groups: List[str]  # Groups to disable


async def load_keybindings(path: Path) -> KeybindingConfig:
    """Load keybindings from config file."""
    # Async file read
    import aiofiles

    async with aiofiles.open(path, "r") as f:
        content = await f.read()

    if path.suffix == ".json":
        data = json.loads(content)
    elif path.suffix in (".yaml", ".yml"):
        import yaml
        data = yaml.safe_load(content)
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")

    return KeybindingConfig(
        bindings=data.get("bindings", []),
        sequences=data.get("sequences", []),
        groups=data.get("disabled_groups", []),
    )


async def save_keybindings(path: Path, manager: KeybindingsManager) -> None:
    """Save keybindings to config file."""
    import aiofiles

    bindings_data = []
    for key, bindings in manager.get_bindings().items():
        for binding in bindings:
            bindings_data.append({
                "key": binding.key,
                "mode": binding.mode.value,
                "description": binding.description,
                "repeatable": binding.repeatable,
                "group": binding.group,
                "enabled": binding.enabled,
            })

    sequences_data = []
    for seq_id, sequence in manager.get_sequences().items():
        sequences_data.append({
            "keys": sequence.keys,
            "mode": sequence.mode.value,
            "description": sequence.description,
            "timeout_ms": sequence.timeout_ms,
        })

    data = {
        "bindings": bindings_data,
        "sequences": sequences_data,
        "disabled_groups": [g for g, bindings in manager._groups.items() if not any(b.enabled for b in bindings)],
    }

    async with aiofiles.open(path, "w") as f:
        if path.suffix == ".json":
            await f.write(json.dumps(data, indent=2))
        elif path.suffix in (".yaml", ".yml"):
            import yaml
            await f.write(yaml.dump(data))
        else:
            await f.write(json.dumps(data, indent=2))


def apply_config(manager: KeybindingsManager, config: KeybindingConfig) -> None:
    """Apply configuration to manager."""
    # Disable groups
    for group in config.groups:
        manager.unbind_group(group)

    # Apply bindings
    for binding_data in config.bindings:
        mode = KeyMode(binding_data.get("mode", "normal"))
        platform_str = binding_data.get("platform")
        platform = Platform(platform_str) if platform_str else None

        manager.bind(
            key=binding_data["key"],
            handler=lambda ctx: None,  # Placeholder, real handler from context
            mode=mode,
            description=binding_data.get("description", ""),
            repeatable=binding_data.get("repeatable", False),
            platform=platform,
            priority=binding_data.get("priority", 0),
            group=binding_data.get("group", ""),
        )

    # Apply sequences
    for sequence_data in config.sequences:
        mode = KeyMode(sequence_data.get("mode", "normal"))

        manager.bind_sequence(
            keys=sequence_data["keys"],
            handler=lambda ctx: None,  # Placeholder
            mode=mode,
            timeout_ms=sequence_data.get("timeout_ms", 500),
            description=sequence_data.get("description", ""),
        )


# Default config paths
DEFAULT_CONFIG_PATHS = [
    Path(".claude/keybindings.json"),
    Path(".claude/keybindings.yaml"),
    Path("~/.claude/keybindings.json"),
    Path("~/.claude/keybindings.yaml"),
]


async def find_config() -> Optional[Path]:
    """Find keybindings config file."""
    for path in DEFAULT_CONFIG_PATHS:
        expanded = path.expanduser()
        if expanded.exists():
            return expanded

    return None


async def load_user_keybindings(manager: KeybindingsManager) -> None:
    """Load user keybindings from config."""
    config_path = await find_config()

    if config_path:
        config = await load_keybindings(config_path)
        apply_config(manager, config)


# Example config format
EXAMPLE_CONFIG = """
{
  "bindings": [
    {
      "key": "ctrl+shift+f",
      "mode": "normal",
      "description": "Find in files"
    },
    {
      "key": "ctrl+shift+g",
      "mode": "normal",
      "description": "Go to file"
    }
  ],
  "sequences": [
    {
      "keys": ["ctrl+k", "ctrl+s"],
      "mode": "normal",
      "description": "Save all"
    }
  ],
  "disabled_groups": []
}
"""


__all__ = [
    "KeybindingConfig",
    "load_keybindings",
    "save_keybindings",
    "apply_config",
    "find_config",
    "load_user_keybindings",
    "DEFAULT_CONFIG_PATHS",
    "EXAMPLE_CONFIG",
]
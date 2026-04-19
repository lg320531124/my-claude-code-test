"""Plugins package."""

from __future__ import annotations
from .plugin_system import (
    PluginBase,
    PluginLoader,
    PluginManager,
    PluginMetadata,
    PluginInfo,
    PluginState,
    get_plugin_manager,
    initialize_plugins,
    trigger_plugin_event,
    PLUGIN_EVENTS,
)

__all__ = [
    "PluginBase",
    "PluginLoader",
    "PluginManager",
    "PluginMetadata",
    "PluginInfo",
    "PluginState",
    "get_plugin_manager",
    "initialize_plugins",
    "trigger_plugin_event",
    "PLUGIN_EVENTS",
]

"""
Claude Code Python - AI-powered coding assistant for terminal.
"""
from __future__ import annotations

__version__ = "0.1.0"

# Module imports
from .bridge import (
    BridgeStatus,
    BridgeMessageType,
    BridgeMessage,
    BridgeConfig,
    BridgeAPI,
    BridgeMessaging,
    BridgeMain,
)

from .vim import (
    VimMode,
    VimState,
    VimMotions,
    VimOperators,
    VimTextObjects,
    VimTransitions,
)

from .keybindings import (
    KeyMode,
    KeyBinding,
    KeySequence,
    KeybindingsManager,
    KeyParser,
    get_keybindings_manager,
)

from .state import (
    AppState,
    Store,
    ActionType,
    Action,
    Selectors,
    use_state,
    use_selector,
    use_dispatch,
)

from .tasks import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskManager,
    TaskScheduler,
    get_task_manager,
)

from .skills import (
    Skill,
    SkillType,
    SkillRegistry,
    get_skill_registry,
)

from .output_styles import (
    OutputStyle,
    OutputFormatter,
    StyleConfig,
)

from .migrations import (
    Migration,
    MigrationStatus,
    MigrationManager,
    get_migration_manager,
)

from .buddy import (
    VisualizationType,
    VisualizationGraph,
    BuddyVisualizer,
    get_visualizer,
)

from .memdir import (
    MemoryType,
    MemoryEntry,
    Team,
    MemDirService,
    get_memdir_service,
)


__all__ = [
    # Bridge
    "BridgeStatus",
    "BridgeMessageType",
    "BridgeMessage",
    "BridgeConfig",
    "BridgeAPI",
    "BridgeMessaging",
    "BridgeMain",
    # Vim
    "VimMode",
    "VimState",
    "VimMotions",
    "VimOperators",
    "VimTextObjects",
    "VimTransitions",
    # Keybindings
    "KeyMode",
    "KeyBinding",
    "KeySequence",
    "KeybindingsManager",
    "KeyParser",
    "get_keybindings_manager",
    # State
    "AppState",
    "Store",
    "ActionType",
    "Action",
    "Selectors",
    "use_state",
    "use_selector",
    "use_dispatch",
    # Tasks
    "Task",
    "TaskStatus",
    "TaskPriority",
    "TaskManager",
    "TaskScheduler",
    "get_task_manager",
    # Skills
    "Skill",
    "SkillType",
    "SkillRegistry",
    "get_skill_registry",
    # Output Styles
    "OutputStyle",
    "OutputFormatter",
    "StyleConfig",
    # Migrations
    "Migration",
    "MigrationStatus",
    "MigrationManager",
    "get_migration_manager",
    # Buddy
    "VisualizationType",
    "VisualizationGraph",
    "BuddyVisualizer",
    "get_visualizer",
    # MemDir
    "MemoryType",
    "MemoryEntry",
    "Team",
    "MemDirService",
    "get_memdir_service",
]

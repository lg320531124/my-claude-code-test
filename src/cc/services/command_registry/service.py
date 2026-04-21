"""Command Registry - Manage CLI commands."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from enum import Enum

from ...utils.log import get_logger

logger = get_logger(__name__)


class CommandCategory(Enum):
    """Command categories."""
    CORE = "core"
    GIT = "git"
    MCP = "mcp"
    MEMORY = "memory"
    TOOLS = "tools"
    SETTINGS = "settings"
    DEV = "dev"
    ADMIN = "admin"


@dataclass
class CommandMeta:
    """Command metadata."""
    name: str
    description: str = ""
    category: CommandCategory = CommandCategory.CORE
    aliases: List[str] = field(default_factory=list)
    args: List[str] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    hidden: bool = False
    deprecated: bool = False


@dataclass
class RegisteredCommand:
    """Registered command."""
    meta: CommandMeta
    handler: Callable
    subcommands: Dict[str, RegisteredCommand] = field(default_factory=dict)


@dataclass
class RegistryConfig:
    """Registry configuration."""
    allow_overrides: bool = False
    case_sensitive: bool = False
    max_commands: int = 200


class CommandRegistry:
    """Registry for CLI commands."""

    def __init__(self, config: Optional[RegistryConfig] = None):
        self.config = config or RegistryConfig()
        self._commands: Dict[str, RegisteredCommand] = {}
        self._aliases: Dict[str, str] = {}

    async def register(
        self,
        name: str,
        handler: Callable,
        meta: Optional[CommandMeta] = None
    ) -> bool:
        """Register command."""
        # Normalize name
        key = self._normalize_key(name)

        # Check existing
        if key in self._commands and not self.config.allow_overrides:
            logger.warning(f"Command already registered: {name}")
            return False

        # Check limit
        if len(self._commands) >= self.config.max_commands:
            logger.warning("Command limit reached")
            return False

        # Create metadata
        use_meta = meta or CommandMeta(name=name)

        # Register command
        command = RegisteredCommand(
            meta=use_meta,
            handler=handler,
        )

        self._commands[key] = command

        # Register aliases
        for alias in use_meta.aliases:
            self._aliases[self._normalize_key(alias)] = key

        logger.info(f"Registered command: {name}")
        return True

    def _normalize_key(self, key: str) -> str:
        """Normalize command key."""
        if not self.config.case_sensitive:
            return key.lower()
        return key

    async def unregister(
        self,
        name: str
    ) -> bool:
        """Unregister command."""
        key = self._normalize_key(name)

        if key not in self._commands:
            return False

        # Remove aliases
        for alias, target in self._aliases.items():
            if target == key:
                del self._aliases[alias]

        del self._commands[key]
        return True

    async def get(
        self,
        name: str
    ) -> Optional[RegisteredCommand]:
        """Get command by name."""
        key = self._normalize_key(name)

        # Check direct
        if key in self._commands:
            return self._commands[key]

        # Check alias
        if key in self._aliases:
            target = self._aliases[key]
            return self._commands.get(target)

        return None

    async def execute(
        self,
        name: str,
        args: Optional[List[str]] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> Any:
        """Execute command."""
        command = await self.get(name)

        if not command:
            raise ValueError(f"Command not found: {name}")

        if command.meta.deprecated:
            logger.warning(f"Command {name} is deprecated")

        # Check for subcommand
        if args and len(args) > 0:
            subcommand_key = self._normalize_key(args[0])
            if subcommand_key in command.subcommands:
                subcommand = command.subcommands[subcommand_key]
                return await self._execute_handler(
                    subcommand.handler,
                    args[1:],
                    context
                )

        return await self._execute_handler(
            command.handler,
            args or [],
            context
        )

    async def _execute_handler(
        self,
        handler: Callable,
        args: List[str],
        context: Optional[Dict[str, Any]]
    ) -> Any:
        """Execute handler."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(args, context)
        else:
            return handler(args, context)

    async def register_subcommand(
        self,
        parent: str,
        name: str,
        handler: Callable,
        meta: Optional[CommandMeta] = None
    ) -> bool:
        """Register subcommand."""
        parent_cmd = await self.get(parent)

        if not parent_cmd:
            return False

        key = self._normalize_key(name)
        use_meta = meta or CommandMeta(name=name)

        subcommand = RegisteredCommand(
            meta=use_meta,
            handler=handler,
        )

        parent_cmd.subcommands[key] = subcommand
        return True

    async def list_commands(
        self,
        category: Optional[CommandCategory] = None,
        include_hidden: bool = False
    ) -> List[CommandMeta]:
        """List commands."""
        commands = []

        for cmd in self._commands.values():
            # Filter hidden
            if cmd.meta.hidden and not include_hidden:
                continue

            # Filter deprecated
            if cmd.meta.deprecated:
                continue

            # Filter category
            if category and cmd.meta.category != category:
                continue

            commands.append(cmd.meta)

        return commands

    async def get_help(
        self,
        name: str
    ) -> Optional[str]:
        """Get help for command."""
        command = await self.get(name)

        if not command:
            return None

        lines = [
            f"Command: {command.meta.name}",
            f"Description: {command.meta.description}",
        ]

        if command.meta.aliases:
            lines.append(f"Aliases: {', '.join(command.meta.aliases)}")

        if command.meta.args:
            lines.append(f"Arguments: {', '.join(command.meta.args)}")

        if command.meta.examples:
            lines.append("Examples:")
            for ex in command.meta.examples:
                lines.append(f"  {ex}")

        if command.subcommands:
            lines.append("Subcommands:")
            for name, sub in command.subcommands.items():
                lines.append(f"  {name}: {sub.meta.description}")

        return "\n".join(lines)

    async def search(
        self,
        query: str
    ) -> List[CommandMeta]:
        """Search commands."""
        query_lower = query.lower()
        results = []

        for cmd in self._commands.values():
            # Match name
            if query_lower in cmd.meta.name.lower():
                results.append(cmd.meta)
                continue

            # Match description
            if query_lower in cmd.meta.description.lower():
                results.append(cmd.meta)
                continue

            # Match aliases
            for alias in cmd.meta.aliases:
                if query_lower in alias.lower():
                    results.append(cmd.meta)
                    break

        return results

    async def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        by_category: Dict[str, int] = {}

        for cmd in self._commands.values():
            key = cmd.meta.category.value
            by_category[key] = by_category.get(key, 0) + 1

        return {
            "total_commands": len(self._commands),
            "total_aliases": len(self._aliases),
            "by_category": by_category,
        }


__all__ = [
    "CommandCategory",
    "CommandMeta",
    "RegisteredCommand",
    "RegistryConfig",
    "CommandRegistry",
]
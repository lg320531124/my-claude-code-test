"""Commands module - All available CLI commands."""

from __future__ import annotations

# New commands with proper exports
from .branch import BranchCommand, BranchAction, BranchOptions, run_branch
from .diff import DiffCommand, DiffMode, DiffOptions, run_diff
from .resume import ResumeCommand, ResumeOptions, run_resume
from .export import ExportCommand, ExportFormat, ExportOptions, run_export
from .import_cmd import ImportCommand, ImportType, ImportOptions, run_import
from .clear_cmd import ClearCommand, ClearTarget, run_clear
from .stats_cmd import StatsCommand, UsageStats, run_stats
from .feedback_cmd import FeedbackCommand, FeedbackType, run_feedback
from .insights_cmd import InsightsCommand, InsightData, run_insights
from .help_cmd import HelpCommand, HelpSection, run_help

# Sandbox and Teleport commands
from .sandbox_cmd import SandboxCommand, SandboxStatus, SandboxInfo
from .teleport_cmd import TeleportCommand, TeleportStatus, TeleportEndpoint

# Wizard commands
from .wizard import (
    WizardStep, WizardQuestion, WizardAnswer, WizardState,
    Wizard, InitWizard, SetupWizard,
)

# Existing commands (check each)
try:
    from .commit import CommitCommand
except ImportError:
    CommitCommand = None

try:
    from .doctor import DoctorCommand
except ImportError:
    DoctorCommand = None

try:
    from .cost import CostCommand
except ImportError:
    CostCommand = None

try:
    from .review import ReviewCommand
except ImportError:
    ReviewCommand = None

__all__ = [
    # New commands
    "BranchCommand", "BranchAction", "BranchOptions", "run_branch",
    "DiffCommand", "DiffMode", "DiffOptions", "run_diff",
    "ResumeCommand", "ResumeOptions", "run_resume",
    "ExportCommand", "ExportFormat", "ExportOptions", "run_export",
    "ImportCommand", "ImportType", "ImportOptions", "run_import",
    "ClearCommand", "ClearTarget", "run_clear",
    "StatsCommand", "UsageStats", "run_stats",
    "FeedbackCommand", "FeedbackType", "run_feedback",
    "InsightsCommand", "InsightData", "run_insights",
    "HelpCommand", "HelpSection", "run_help",
    # Sandbox/Teleport
    "SandboxCommand", "SandboxStatus", "SandboxInfo",
    "TeleportCommand", "TeleportStatus", "TeleportEndpoint",
    # Wizard
    "WizardStep", "WizardQuestion", "WizardAnswer", "WizardState",
    "Wizard", "InitWizard", "SetupWizard",
    # Existing commands (optional)
    "CommitCommand",
    "DoctorCommand",
    "CostCommand",
    "ReviewCommand",
]

"""Utils package - All utility functions."""

from __future__ import annotations
from .config import Config
from .shell import ShellDetector, ShellInfo, ShellType, get_shell_detector
from .file import get_file_info
from .log import get_logger
from .performance import (
    AsyncCache,
    cached,
    ParallelExecutor,
    RateLimiter,
    TokenOptimizer,
    PerformanceTracker,
    timed,
    get_cache,
    get_executor,
    get_tracker,
)
from .error_handling import (
    ErrorSeverity,
    ErrorCategory,
    ErrorInfo,
    ErrorHandler,
    error_handler,
    RecoveryManager,
    get_error_handler,
    get_recovery_manager,
)

# Async utilities
from .async_io import (
    read_file_async,
    write_file_async,
    exists_async,
    stat_async,
    mkdir_async,
)
from .async_process import (
    ProcessResult,
    AsyncProcess,
    run_command_async,
    run_command_streaming,
    run_commands_parallel,
)
from .async_http import (
    HTTPResponse,
    AsyncHTTPClient,
    fetch_url,
    fetch_json,
    fetch_sse_stream,
)

# Claude.md
from .claude_md import (
    ClaudeMDSection,
    ClaudeMDContent,
    parse_claude_md,
    parse_claude_md_content,
    find_claude_md_files,
    load_claude_md_context,
    extract_instructions,
)

# Messages
from .messages import (
    MessageRole,
    ContentBlock,
    Message,
    create_user_message,
    create_assistant_message,
    create_tool_result_message,
    estimate_message_tokens,
    format_messages_for_api,
    extract_text_from_messages,
    get_tool_calls_from_message,
    stream_message_updates,
)

# System prompt
from .system_prompt import (
    SystemPromptBuilder,
    build_system_prompt,
    get_default_tools_description,
)

# Thinking
from .thinking import (
    ThinkingBudgetMode,
    ThinkingConfig,
    ThinkingBlock,
    ThinkingManager,
    parse_thinking_from_response,
    format_thinking_for_api,
    should_use_thinking,
    get_thinking_budget_for_task,
)

# Model
from .model import (
    ModelFamily,
    APIProvider,
    ModelInfo,
    AVAILABLE_MODELS,
    ModelSelector,
    get_provider_config,
    validate_model_id,
    get_model_families,
)
from .swarm import (
    SwarmState,
    AgentRole,
    SwarmAgent,
    SwarmConfig,
    SwarmResult,
    SwarmCoordinator,
)
from .circular_buffer import (
    BufferStats,
    CircularBuffer,
)
from .activity import (
    ActivityType,
    ActivityEvent,
    ActivityStats,
    ActivityManager,
)
from .analyze_context import (
    ContextType,
    ContextPriority,
    ContextItem,
    ContextAnalysis,
    ContextAnalyzer,
)
from .query_context import (
    QueryType,
    QueryResultType,
    Query,
    QueryResult,
    QueryContext,
)
from .plugins import (
    PluginStatus,
    PluginType,
    PluginInfo,
    PluginConfig,
    PluginManager,
)
from .process_input import (
    InputType,
    InputStatus,
    InputConfig,
    ProcessedInput,
    InputProcessor,
)
from .voice import (
    VoiceFormat,
    VoiceQuality,
    VoiceConfig,
    VoiceSegment,
    VoiceTranscription,
    VoiceProcessor,
    VoiceDetector,
    SpeakerIdentifier,
    TranscriptionFormatter,
)

__all__ = [
    # Config
    "Config",
    # Shell
    "run_command",
    # File
    "get_file_info",
    # Log
    "get_logger",
    # Performance
    "AsyncCache",
    "cached",
    "ParallelExecutor",
    "RateLimiter",
    "TokenOptimizer",
    "PerformanceTracker",
    "timed",
    "get_cache",
    "get_executor",
    "get_tracker",
    # Error handling
    "ErrorSeverity",
    "ErrorCategory",
    "ErrorInfo",
    "ErrorHandler",
    "error_handler",
    "RecoveryManager",
    "get_error_handler",
    "get_recovery_manager",
    # Async IO
    "read_file_async",
    "write_file_async",
    "exists_async",
    "stat_async",
    "mkdir_async",
    # Async Process
    "ProcessResult",
    "AsyncProcess",
    "run_command_async",
    "run_command_streaming",
    "run_commands_parallel",
    # Async HTTP
    "HTTPResponse",
    "AsyncHTTPClient",
    "fetch_url",
    "fetch_json",
    "fetch_sse_stream",
    # Claude.md
    "ClaudeMDSection",
    "ClaudeMDContent",
    "parse_claude_md",
    "parse_claude_md_content",
    "find_claude_md_files",
    "load_claude_md_context",
    "extract_instructions",
    # Messages
    "MessageRole",
    "ContentBlock",
    "Message",
    "create_user_message",
    "create_assistant_message",
    "create_tool_result_message",
    "estimate_message_tokens",
    "format_messages_for_api",
    "extract_text_from_messages",
    "get_tool_calls_from_message",
    "stream_message_updates",
    # System prompt
    "SystemPromptBuilder",
    "build_system_prompt",
    "get_default_tools_description",
    # Thinking
    "ThinkingBudgetMode",
    "ThinkingConfig",
    "ThinkingBlock",
    "ThinkingManager",
    "parse_thinking_from_response",
    "format_thinking_for_api",
    "should_use_thinking",
    "get_thinking_budget_for_task",
    # Model
    "ModelFamily",
    "APIProvider",
    "ModelInfo",
    "AVAILABLE_MODELS",
    "ModelSelector",
    "get_provider_config",
    "validate_model_id",
    "get_model_families",
    # Swarm
    "SwarmState",
    "AgentRole",
    "SwarmAgent",
    "SwarmConfig",
    "SwarmResult",
    "SwarmCoordinator",
    # Circular buffer
    "BufferStats",
    "CircularBuffer",
    # Activity
    "ActivityType",
    "ActivityEvent",
    "ActivityStats",
    "ActivityManager",
    # Analyze context
    "ContextType",
    "ContextPriority",
    "ContextItem",
    "ContextAnalysis",
    "ContextAnalyzer",
    # Query context
    "QueryType",
    "QueryResultType",
    "Query",
    "QueryResult",
    "QueryContext",
    # Plugins
    "PluginStatus",
    "PluginType",
    "PluginInfo",
    "PluginConfig",
    "PluginManager",
    # Process input
    "InputType",
    "InputStatus",
    "InputConfig",
    "ProcessedInput",
    "InputProcessor",
    # Voice
    "VoiceFormat",
    "VoiceQuality",
    "VoiceConfig",
    "VoiceSegment",
    "VoiceTranscription",
    "VoiceProcessor",
    "VoiceDetector",
    "SpeakerIdentifier",
    "TranscriptionFormatter",
]
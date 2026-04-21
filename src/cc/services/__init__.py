"""Services module."""

from __future__ import annotations

# API clients (optional - requires anthropic SDK)
try:
    from .api.client import APIClient, CompatClient, RetryConfig, get_client
    from .api.enhanced_client import (
        EnhancedAPIClient,
        APIError,
        APIErrorType,
        StreamEvent,
        StreamingBuffer,
        ToolCallBuffer,
        create_client,
    )
    _API_AVAILABLE = True
except ImportError:
    _API_AVAILABLE = False
    APIClient = None
    CompatClient = None
    RetryConfig = None
    get_client = None
    EnhancedAPIClient = None
    APIError = None
    APIErrorType = None
    StreamEvent = None
    StreamingBuffer = None
    ToolCallBuffer = None
    create_client = None

# Plugins
from .plugins import (
    PluginBase,
    PluginLoader,
    PluginManager,
    PluginMetadata,
    PluginInfo,
    PluginState,
    get_plugin_manager,
    initialize_plugins,
    trigger_plugin_event,
)

# Hooks
from .hooks import (
    Hook,
    HookType,
    HookContext,
    HookResult,
    HookRegistry,
    HookManager,
    get_hook_manager,
    register_hook,
    trigger_hook,
)

# Compact
from .compact.compact import (
    CompactStrategy,
    CompactConfig,
    CompactResult,
    MessageGroup,
    CompactService,
    AutoCompactHook,
    get_compact_service,
)

# Analytics
from .analytics.analytics import (
    EventType,
    AnalyticsEvent,
    EventSink,
    AnalyticsConfig,
    AnalyticsService,
    FirstPartyEventLogger,
    GrowthBookIntegration,
    get_analytics_service,
    start_analytics,
    stop_analytics,
    track_event,
)

# Memory
from .memory.session_memory import (
    MemoryType,
    MemoryEntry,
    MemorySearchResult,
    MemoryStore,
    MemoryExtractor,
    SessionMemory,
    get_memory_store,
    remember,
    recall,
)

# Notifier
from .notifier.notifier import (
    NotificationLevel,
    Notification,
    NotifierService,
    get_notifier,
    notify,
)

# OAuth
from .oauth.oauth import (
    OAuthProvider,
    OAuthToken,
    OAuthState,
    OAuthService,
)

# Magic Docs
from .magic_docs.magic_docs import (
    DocFormat,
    DocSection,
    MagicDoc,
    MagicDocsService,
)

# Auto Dream
from .auto_dream.auto_dream import (
    DreamType,
    Dream,
    DreamContext,
    AutoDreamService,
)

# File Watcher
from .file_watcher.file_watcher import (
    WatchEventType,
    WatchEvent,
    WatchConfig,
    FileWatcherService,
)

# Cache
from .cache.cache import (
    CacheEntry,
    CacheConfig,
    CacheService,
    get_cache_service,
    cache_get,
    cache_set,
)

# Prompt
from .prompt.prompt import (
    PromptTemplate,
    PromptConfig,
    PromptService,
    get_prompt_service,
    get_prompt,
)

# Storage
from .storage.storage import (
    StorageConfig,
    StorageService,
    get_storage_service,
)

# Telemetry
from .telemetry.telemetry import (
    TelemetryConfig,
    TelemetryEvent,
    TelemetryService,
    get_telemetry_service,
    track_event,
)

# Security
from .security.security import (
    SecurityConfig,
    SecurityCheck,
    SecurityService,
    SECRET_PATTERNS,
    get_security_service,
    check_input,
    sanitize_output,
)

# Validation
from .validation.validation import (
    ValidationRule,
    ValidationResult,
    ValidationService,
    get_validation_service,
    validate,
)

# Template (document templates)
from .template.template import (
    Template,
    TEMPLATE_LIBRARY,
    TemplateService,
    get_template_service,
    render_template,
)

# Rate Limiter
from .rate_limiter.rate_limiter import (
    RateLimitConfig,
    RateLimitResult,
    RateLimiterService,
    get_rate_limiter,
    check_rate,
)

# MCP (Model Context Protocol)
from .mcp import (
    MCPClient,
    MCPServerConfig,
    MCPTool,
    MCPResource,
    MCPManager,
    load_mcp_servers,
)

# LSP (Language Server Protocol)
from .lsp import (
    LSPClient,
    LSPServerConfig,
    LSPDiagnostic,
    LSPCompletion,
    LSPHover,
    LSPManager,
)

# Voice (Speech-to-Text / Text-to-Speech)
from .voice import (
    VoiceService,
    VoiceConfig,
    VoiceStreamProcessor,
    TranscriptionResult,
    SpeechConfig,
)

# Token Estimation
from .token_estimation import (
    TokenUsage,
    TokenBudget,
    estimate_tokens,
    estimate_message_tokens,
    estimate_messages_tokens,
    TokenCounter,
    TokenBudgetManager,
    detect_content_type,
)

# Settings Sync
from .settings import (
    SettingsSnapshot,
    SyncResult,
    SettingsSync,
)

# Team Sync
from .team import (
    SyncStatus,
    TeamMemory,
    SyncBatch,
    TeamMemorySync,
)

__all__ = [
    # API (optional)
    "APIClient",
    "CompatClient",
    "RetryConfig",
    "get_client",
    "EnhancedAPIClient",
    "APIError",
    "APIErrorType",
    "StreamEvent",
    "StreamingBuffer",
    "ToolCallBuffer",
    "create_client",
    # Plugins
    "PluginBase",
    "PluginLoader",
    "PluginManager",
    "PluginMetadata",
    "PluginInfo",
    "PluginState",
    "get_plugin_manager",
    "initialize_plugins",
    "trigger_plugin_event",
    # Hooks
    "Hook",
    "HookType",
    "HookContext",
    "HookResult",
    "HookRegistry",
    "HookManager",
    "get_hook_manager",
    "register_hook",
    "trigger_hook",
    # Compact
    "CompactStrategy",
    "CompactConfig",
    "CompactResult",
    "MessageGroup",
    "CompactService",
    "AutoCompactHook",
    "get_compact_service",
    # Analytics
    "EventType",
    "AnalyticsEvent",
    "EventSink",
    "AnalyticsConfig",
    "AnalyticsService",
    "FirstPartyEventLogger",
    "GrowthBookIntegration",
    "get_analytics_service",
    "start_analytics",
    "stop_analytics",
    "track_event",
    # Memory
    "MemoryType",
    "MemoryEntry",
    "MemorySearchResult",
    "MemoryStore",
    "MemoryExtractor",
    "SessionMemory",
    "get_memory_store",
    "remember",
    "recall",
    # Notifier
    "NotificationLevel",
    "Notification",
    "NotifierService",
    "get_notifier",
    "notify",
    # OAuth
    "OAuthProvider",
    "OAuthToken",
    "OAuthState",
    "OAuthService",
    # Magic Docs
    "DocFormat",
    "DocSection",
    "MagicDoc",
    "MagicDocsService",
    # Auto Dream
    "DreamType",
    "Dream",
    "DreamContext",
    "AutoDreamService",
    # File Watcher
    "WatchEventType",
    "WatchEvent",
    "WatchConfig",
    "FileWatcherService",
    # Cache
    "CacheEntry",
    "CacheConfig",
    "CacheService",
    "get_cache_service",
    "cache_get",
    "cache_set",
    # Prompt
    "PromptTemplate",
    "PromptConfig",
    "PromptService",
    "get_prompt_service",
    "get_prompt",
    # Storage
    "StorageConfig",
    "StorageService",
    "get_storage_service",
    # Telemetry
    "TelemetryConfig",
    "TelemetryEvent",
    "TelemetryService",
    "get_telemetry_service",
    "track_event",
    # Security
    "SecurityConfig",
    "SecurityCheck",
    "SecurityService",
    "SECRET_PATTERNS",
    "get_security_service",
    "check_input",
    "sanitize_output",
    # Validation
    "ValidationRule",
    "ValidationResult",
    "ValidationService",
    "get_validation_service",
    "validate",
    # Template
    "Template",
    "TEMPLATE_LIBRARY",
    "TemplateService",
    "get_template_service",
    "render_template",
    # Rate Limiter
    "RateLimitConfig",
    "RateLimitResult",
    "RateLimiterService",
    "get_rate_limiter",
    "check_rate",
    # MCP
    "MCPClient",
    "MCPServerConfig",
    "MCPTool",
    "MCPResource",
    "MCPManager",
    "load_mcp_servers",
    # LSP
    "LSPClient",
    "LSPServerConfig",
    "LSPDiagnostic",
    "LSPCompletion",
    "LSPHover",
    "LSPManager",
    # Voice
    "VoiceService",
    "VoiceConfig",
    "VoiceStreamProcessor",
    "TranscriptionResult",
    "SpeechConfig",
    # Token Estimation
    "TokenUsage",
    "TokenBudget",
    "estimate_tokens",
    "estimate_message_tokens",
    "estimate_messages_tokens",
    "TokenCounter",
    "TokenBudgetManager",
    "detect_content_type",
    # Settings Sync
    "SettingsSnapshot",
    "SyncResult",
    "SettingsSync",
    # Team Sync
    "SyncStatus",
    "TeamMemory",
    "SyncBatch",
    "TeamMemorySync",
]
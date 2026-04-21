"""Product Constants - URLs and environment detection.

Provides product URLs and helpers for remote session environments.
"""

from __future__ import annotations
from typing import Optional

# Product URL
PRODUCT_URL = "https://claude.com/claude-code"

# Claude Code Remote session URLs
CLAUDE_AI_BASE_URL = "https://claude.ai"
CLAUDE_AI_STAGING_BASE_URL = "https://claude-ai.staging.ant.dev"
CLAUDE_AI_LOCAL_BASE_URL = "http://localhost:4000"


def is_remote_session_staging(
    session_id: Optional[str] = None,
    ingress_url: Optional[str] = None,
) -> bool:
    """Check if we're in a staging environment for remote sessions.

    Checks session ID format and ingress URL.

    Args:
        session_id: Optional session ID to check
        ingress_url: Optional ingress URL to check

    Returns:
        True if staging environment detected
    """
    if session_id and "_staging_" in session_id:
        return True
    if ingress_url and "staging" in ingress_url:
        return True
    return False


def is_remote_session_local(
    session_id: Optional[str] = None,
    ingress_url: Optional[str] = None,
) -> bool:
    """Check if we're in a local-dev environment for remote sessions.

    Checks session ID format (e.g. `session_local_...`) and ingress URL.

    Args:
        session_id: Optional session ID to check
        ingress_url: Optional ingress URL to check

    Returns:
        True if local environment detected
    """
    if session_id and "_local_" in session_id:
        return True
    if ingress_url and "localhost" in ingress_url:
        return True
    return False


def get_claude_ai_base_url(
    session_id: Optional[str] = None,
    ingress_url: Optional[str] = None,
) -> str:
    """Get the base URL for Claude AI based on environment.

    Args:
        session_id: Optional session ID to determine environment
        ingress_url: Optional ingress URL to determine environment

    Returns:
        Appropriate base URL for the environment
    """
    if is_remote_session_local(session_id, ingress_url):
        return CLAUDE_AI_LOCAL_BASE_URL
    if is_remote_session_staging(session_id, ingress_url):
        return CLAUDE_AI_STAGING_BASE_URL
    return CLAUDE_AI_BASE_URL


def to_compat_session_id(session_id: str) -> str:
    """Convert session ID to compat format.

    Translates cse_ -> session_ prefix for frontend compatibility.
    No-op for IDs already in session_* form.

    Args:
        session_id: Original session ID

    Returns:
        Compat session ID with session_ prefix
    """
    if session_id.startswith("cse_"):
        return "session_" + session_id[4:]
    return session_id


def get_remote_session_url(
    session_id: str,
    ingress_url: Optional[str] = None,
) -> str:
    """Get the full session URL for a remote session.

    Args:
        session_id: Session ID
        ingress_url: Optional ingress URL to determine environment

    Returns:
        Full URL to the session
    """
    compat_id = to_compat_session_id(session_id)
    base_url = get_claude_ai_base_url(compat_id, ingress_url)
    return f"{base_url}/code/{compat_id}"


__all__ = [
    "PRODUCT_URL",
    "CLAUDE_AI_BASE_URL",
    "CLAUDE_AI_STAGING_BASE_URL",
    "CLAUDE_AI_LOCAL_BASE_URL",
    "is_remote_session_staging",
    "is_remote_session_local",
    "get_claude_ai_base_url",
    "to_compat_session_id",
    "get_remote_session_url",
]
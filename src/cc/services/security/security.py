"""Security Service - Security utilities."""

from __future__ import annotations
import hashlib
import secrets
import re
from pathlib import Path
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field


class SecurityConfig(BaseModel):
    """Security configuration."""
    sanitize_html: bool = Field(default=True, description="Sanitize HTML input")
    check_secrets: bool = Field(default=True, description="Check for secrets in output")
    max_input_length: int = Field(default=100000, description="Maximum input length")


class SecurityCheck(BaseModel):
    """Security check result."""
    safe: bool
    issues: List[str] = Field(default_factory=list)
    severity: str = "none"  # none, low, medium, high, critical


SECRET_PATTERNS = [
    # AWS
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
    (r'aws_secret_access_key\s*=\s*[\'"][^\'"]+[\'"]', 'AWS Secret Key'),
    # API Keys
    (r'api_key\s*=\s*[\'"][^\'"]+[\'"]', 'API Key'),
    (r'apikey\s*[\'":]\s*[\'"][^\'"]+[\'"]', 'API Key'),
    # Tokens
    (r'Bearer\s+[A-Za-z0-9\-._~+/]+=*', 'Bearer Token'),
    (r'token\s*=\s*[\'"][^\'"]+[\'"]', 'Token'),
    (r'access_token\s*[\'":]\s*[\'"][^\'"]+[\'"]', 'Access Token'),
    (r'refresh_token\s*[\'":]\s*[\'"][^\'"]+[\'"]', 'Refresh Token'),
    # Passwords
    (r'password\s*=\s*[\'"][^\'"]+[\'"]', 'Password'),
    (r'passwd\s*=\s*[\'"][^\'"]+[\'"]', 'Password'),
    # SSH Keys
    (r'ssh-rsa\s+[A-Za-z0-9+/=]+', 'SSH Key'),
    # Private Keys
    (r'private_key\s*[\'":]\s*[\'"][^\'"]+[\'"]', 'Private Key'),
    (r'-----BEGIN\s+(RSA|PRIVATE)\s+KEY-----', 'Private Key'),
    # URLs with secrets
    (r'https://[^@]+@[^\s]+', 'URL with credentials'),
]


class SecurityService:
    """Security utilities service."""

    def __init__(self, config: Optional[SecurityConfig] = None):
        self.config = config or SecurityConfig()

    def check_input(self, input: str) -> SecurityCheck:
        """Check input for security issues."""
        issues = []

        # Length check
        if len(input) > self.config.max_input_length:
            issues.append(f"Input too long: {len(input)} > {self.config.max_input_length}")

        # Secret patterns check
        if self.config.check_secrets:
            for pattern, name in SECRET_PATTERNS:
                if re.search(pattern, input, re.IGNORECASE):
                    issues.append(f"Potential secret found: {name}")

        severity = self._determine_severity(issues)

        return SecurityCheck(
            safe=len(issues) == 0,
            issues=issues,
            severity=severity,
        )

    def sanitize_output(self, output: str) -> str:
        """Sanitize output for display."""
        result = output

        # Mask secrets
        for pattern, name in SECRET_PATTERNS:
            matches = re.findall(pattern, result, re.IGNORECASE)
            for match in matches:
                if len(match) > 8:
                    masked = match[:4] + "***" + match[-4:]
                    result = result.replace(match, masked)

        return result

    def sanitize_html(self, html: str) -> str:
        """Sanitize HTML input."""
        if not self.config.sanitize_html:
            return html

        # Remove script tags
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove style tags
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # Remove event handlers
        html = re.sub(r'\s+on\w+="[^"]*"', '', html, flags=re.IGNORECASE)
        html = re.sub(r'\s+on\w+=[\'"][^\'"]*[\'"]', '', html, flags=re.IGNORECASE)

        return html

    def generate_token(self, length: int = 32) -> str:
        """Generate secure random token."""
        return secrets.token_hex(length)

    def hash_password(self, password: str) -> str:
        """Hash password securely."""
        salt = secrets.token_hex(16)
        hash_value = hashlib.sha256((password + salt).encode()).hexdigest()
        return f"{salt}:{hash_value}"

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify password against stored hash."""
        try:
            salt, hash_value = stored_hash.split(":")
            computed = hashlib.sha256((password + salt).encode()).hexdigest()
            return computed == hash_value
        except Exception:
            return False

    def _determine_severity(self, issues: List[str]) -> str:
        """Determine severity from issues."""
        if not issues:
            return "none"

        critical_keywords = ["ssh key", "private key", "aws"]
        high_keywords = ["api key", "token", "bearer", "password"]

        for issue in issues:
            issue_lower = issue.lower()
            if any(k in issue_lower for k in critical_keywords):
                return "critical"
            if any(k in issue_lower for k in high_keywords):
                return "high"

        return "medium"


# Singleton
_security_service: Optional[SecurityService] = None


def get_security_service(config: Optional[SecurityConfig] = None) -> SecurityService:
    """Get security service singleton."""
    global _security_service
    if _security_service is None:
        _security_service = SecurityService(config)
    return _security_service


def check_input(input: str) -> SecurityCheck:
    """Convenience check function."""
    return get_security_service().check_input(input)


def sanitize_output(output: str) -> str:
    """Convenience sanitize function."""
    return get_security_service().sanitize_output(output)


__all__ = [
    "SecurityConfig",
    "SecurityCheck",
    "SecurityService",
    "SECRET_PATTERNS",
    "get_security_service",
    "check_input",
    "sanitize_output",
]
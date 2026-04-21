"""Advisor Service - Provide advice and recommendations."""

from __future__ import annotations
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class AdviceType(Enum):
    """Types of advice."""
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"
    SECURITY = "security"
    CODE_QUALITY = "code_quality"
    BEST_PRACTICES = "best_practices"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    REFACTORING = "refactoring"


@dataclass
class AdviceItem:
    """Single advice item."""
    type: AdviceType
    title: str
    description: str
    severity: str = "info"  # info, warning, critical
    actionable: bool = True
    suggestions: List[str] = field(default_factory=list)
    references: List[str] = field(default_factory=list)
    confidence: float = 0.8


@dataclass
class AdviceResult:
    """Advice analysis result."""
    items: List[AdviceItem]
    summary: str
    overall_score: float
    needs_attention: bool


class AdvisorService:
    """Service for providing development advice."""

    def __init__(self):
        self._advice_templates: Dict[AdviceType, List[Dict]] = {}
        self._load_default_templates()

    def _load_default_templates(self) -> None:
        """Load default advice templates."""
        self._advice_templates = {
            AdviceType.ARCHITECTURE: [
                {
                    "pattern": "large_file",
                    "condition": lambda ctx: ctx.get("file_lines", 0) > 500,
                    "title": "Large file detected",
                    "description": "Consider splitting into smaller modules",
                    "severity": "warning",
                    "suggestions": [
                        "Extract related functionality into separate modules",
                        "Use composition over inheritance",
                        "Apply single responsibility principle",
                    ],
                },
                {
                    "pattern": "deep_nesting",
                    "condition": lambda ctx: ctx.get("max_nesting", 0) > 4,
                    "title": "Deep nesting detected",
                    "description": "Code has excessive nesting levels",
                    "severity": "warning",
                    "suggestions": [
                        "Extract nested logic into separate functions",
                        "Use early returns to reduce nesting",
                        "Apply guard clauses",
                    ],
                },
            ],
            AdviceType.PERFORMANCE: [
                {
                    "pattern": "n_squared",
                    "condition": lambda ctx: ctx.get("loop_complexity", "") == "n_squared",
                    "title": "O(n²) algorithm detected",
                    "description": "Consider optimizing for better performance",
                    "severity": "warning",
                    "suggestions": [
                        "Use hash maps for lookups",
                        "Pre-sort data for efficient access",
                        "Consider caching frequently accessed data",
                    ],
                },
                {
                    "pattern": "large_allocation",
                    "condition": lambda ctx: ctx.get("allocation_size", 0) > 10000000,
                    "title": "Large memory allocation",
                    "description": "May cause performance issues",
                    "severity": "info",
                    "suggestions": [
                        "Use streaming/chunking for large data",
                        "Consider lazy loading",
                        "Implement pagination",
                    ],
                },
            ],
            AdviceType.SECURITY: [
                {
                    "pattern": "sql_injection",
                    "condition": lambda ctx: "raw_sql" in ctx.get("patterns", []),
                    "title": "Potential SQL injection",
                    "description": "Use parameterized queries",
                    "severity": "critical",
                    "suggestions": [
                        "Use parameterized queries or prepared statements",
                        "Validate and sanitize user input",
                        "Use ORM instead of raw SQL",
                    ],
                },
                {
                    "pattern": "hardcoded_secret",
                    "condition": lambda ctx: "hardcoded_password" in ctx.get("patterns", []),
                    "title": "Hardcoded secret detected",
                    "description": "Secrets should be stored securely",
                    "severity": "critical",
                    "suggestions": [
                        "Use environment variables",
                        "Use secure secret management",
                        "Never commit secrets to repository",
                    ],
                },
            ],
            AdviceType.CODE_QUALITY: [
                {
                    "pattern": "duplicate_code",
                    "condition": lambda ctx: ctx.get("duplication_ratio", 0) > 0.1,
                    "title": "Code duplication detected",
                    "description": "Consider extracting common functionality",
                    "severity": "warning",
                    "suggestions": [
                        "Extract common logic into utility functions",
                        "Use inheritance or composition",
                        "Apply DRY principle",
                    ],
                },
                {
                    "pattern": "long_function",
                    "condition": lambda ctx: ctx.get("function_lines", 0) > 50,
                    "title": "Long function detected",
                    "description": "Consider breaking into smaller functions",
                    "severity": "info",
                    "suggestions": [
                        "Split into smaller, focused functions",
                        "Use helper functions for sub-tasks",
                        "Apply single responsibility principle",
                    ],
                },
            ],
            AdviceType.TESTING: [
                {
                    "pattern": "low_coverage",
                    "condition": lambda ctx: ctx.get("test_coverage", 100) < 80,
                    "title": "Low test coverage",
                    "description": "Increase test coverage for reliability",
                    "severity": "warning",
                    "suggestions": [
                        "Add unit tests for core functionality",
                        "Add integration tests for critical paths",
                        "Use TDD approach for new features",
                    ],
                },
                {
                    "pattern": "missing_edge_cases",
                    "condition": lambda ctx: "edge_case_tests" not in ctx.get("test_types", []),
                    "title": "Missing edge case tests",
                    "description": "Add tests for edge cases",
                    "severity": "info",
                    "suggestions": [
                        "Test empty inputs",
                        "Test boundary conditions",
                        "Test error conditions",
                    ],
                },
            ],
        }

    async def analyze(
        self,
        context: Dict[str, Any],
        advice_types: List[AdviceType] = None,
    ) -> AdviceResult:
        """Analyze context and provide advice."""
        items = []

        if advice_types is None:
            advice_types = list(AdviceType)

        for advice_type in advice_types:
            templates = self._advice_templates.get(advice_type, [])

            for template in templates:
                try:
                    if template["condition"](context):
                        item = AdviceItem(
                            type=advice_type,
                            title=template["title"],
                            description=template["description"],
                            severity=template["severity"],
                            actionable=True,
                            suggestions=template.get("suggestions", []),
                            references=template.get("references", []),
                        )
                        items.append(item)
                except Exception:
                    pass

        # Calculate overall score
        if items:
            critical_count = sum(1 for i in items if i.severity == "critical")
            warning_count = sum(1 for i in items if i.severity == "warning")

            score = 100 - (critical_count * 30 + warning_count * 10)
            score = max(0, min(100, score))
        else:
            score = 100

        # Generate summary
        summary = self._generate_summary(items, score)

        return AdviceResult(
            items=items,
            summary=summary,
            overall_score=score,
            needs_attention=len(items) > 0,
        )

    def _generate_summary(self, items: List[AdviceItem], score: float) -> str:
        """Generate summary from items."""
        if not items:
            return "No issues detected. Code quality is good."

        critical = [i for i in items if i.severity == "critical"]
        warnings = [i for i in items if i.severity == "warning"]

        parts = []

        if critical:
            parts.append(f"{len(critical)} critical issues require immediate attention")

        if warnings:
            parts.append(f"{len(warnings)} warnings should be addressed")

        if len(items) - len(critical) - len(warnings) > 0:
            parts.append(f"{len(items) - len(critical) - len(warnings)} suggestions for improvement")

        return ". ".join(parts) + f". Overall score: {score:.0f}/100"

    async def get_quick_advice(
        self,
        query: str,
        context: Dict[str, Any] = None,
    ) -> List[str]:
        """Get quick advice for a query."""
        # Placeholder - would use AI to generate advice
        return [
            "Consider the maintainability of your solution",
            "Ensure proper error handling",
            "Add appropriate tests",
            "Document your decisions",
        ]

    def add_custom_template(
        self,
        advice_type: AdviceType,
        template: Dict[str, Any],
    ) -> None:
        """Add custom advice template."""
        if advice_type not in self._advice_templates:
            self._advice_templates[advice_type] = []
        self._advice_templates[advice_type].append(template)


# Global advisor
_advisor: Optional[AdvisorService] = None


def get_advisor() -> AdvisorService:
    """Get global advisor service."""
    global _advisor
    if _advisor is None:
        _advisor = AdvisorService()
    return _advisor


async def analyze_code(context: Dict[str, Any]) -> AdviceResult:
    """Analyze code and get advice."""
    return await get_advisor().analyze(context)


__all__ = [
    "AdviceType",
    "AdviceItem",
    "AdviceResult",
    "AdvisorService",
    "get_advisor",
    "analyze_code",
]
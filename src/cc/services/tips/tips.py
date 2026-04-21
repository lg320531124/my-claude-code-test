"""Tips - Helpful tips and suggestions."""

from __future__ import annotations
import random
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum


class TipCategory(Enum):
    """Tip categories."""
    PRODUCTIVITY = "productivity"
    CODING = "coding"
    GIT = "git"
    DEBUGGING = "debugging"
    SHORTCUTS = "shortcuts"
    BEST_PRACTICES = "best_practices"
    FEATURES = "features"


@dataclass
class Tip:
    """Tip data."""
    id: str
    category: TipCategory
    title: str
    content: str
    example: Optional[str] = None
    tags: List[str] = field(default_factory=list)


# Built-in tips
BUILTIN_TIPS = [
    Tip(
        id="tip_001",
        category=TipCategory.PRODUCTIVITY,
        title="Use /compact to save context",
        content="When your conversation gets long, use /compact to summarize and free up context space.",
        tags=["context", "memory"],
    ),
    Tip(
        id="tip_002",
        category=TipCategory.CODING,
        title="Specify file paths clearly",
        content="When asking to read or modify files, provide exact paths to avoid confusion.",
        example="src/components/Button.tsx",
        tags=["files", "paths"],
    ),
    Tip(
        id="tip_003",
        category=TipCategory.GIT,
        title="Review before committing",
        content="Use /review to get a code review before committing changes.",
        tags=["git", "review"],
    ),
    Tip(
        id="tip_004",
        category=TipCategory.SHORTCUTS,
        title="Use keyboard shortcuts",
        content="Press Ctrl+K to clear input, Ctrl+L to clear screen.",
        tags=["keyboard", "shortcuts"],
    ),
    Tip(
        id="tip_005",
        category=TipCategory.DEBUGGING,
        title="Describe errors precisely",
        content="When debugging, include exact error messages and stack traces.",
        tags=["debugging", "errors"],
    ),
    Tip(
        id="tip_006",
        category=TipCategory.BEST_PRACTICES,
        title="Write tests first",
        content="Consider writing tests before implementing features for better design.",
        tags=["testing", "tdd"],
    ),
    Tip(
        id="tip_007",
        category=TipCategory.FEATURES,
        title="Use /doctor for diagnosis",
        content="Run /doctor to check your environment setup and identify issues.",
        tags=["doctor", "setup"],
    ),
    Tip(
        id="tip_008",
        category=TipCategory.PRODUCTIVITY,
        title="Use /cost to track spending",
        content="Monitor your API usage with /cost to stay within budget.",
        tags=["cost", "usage"],
    ),
]


class TipsService:
    """Service for tips management."""
    
    def __init__(self):
        self._tips: Dict[str, Tip] = {t.id: t for t in BUILTIN_TIPS}
        self._custom_tips: Dict[str, Tip] = {}
        self._seen: set = set()
    
    def get_tip(self, tip_id: str) -> Optional[Tip]:
        """Get specific tip."""
        return self._tips.get(tip_id) or self._custom_tips.get(tip_id)
    
    def get_random_tip(self, category: TipCategory = None) -> Optional[Tip]:
        """Get random tip."""
        tips = list(self._tips.values())
        
        if category:
            tips = [t for t in tips if t.category == category]
        
        if not tips:
            return None
        
        # Prefer unseen tips
        unseen = [t for t in tips if t.id not in self._seen]
        
        if unseen:
            tip = random.choice(unseen)
        else:
            tip = random.choice(tips)
        
        self._seen.add(tip.id)
        return tip
    
    def get_by_category(self, category: TipCategory) -> List[Tip]:
        """Get tips by category."""
        return [t for t in self._tips.values() if t.category == category]
    
    def get_all(self) -> List[Tip]:
        """Get all tips."""
        return list(self._tips.values()) + list(self._custom_tips.values())
    
    def add_tip(self, tip: Tip) -> None:
        """Add custom tip."""
        self._custom_tips[tip.id] = tip
    
    def search(self, query: str) -> List[Tip]:
        """Search tips."""
        query = query.lower()
        results = []
        
        for tip in self.get_all():
            if query in tip.title.lower() or query in tip.content.lower():
                results.append(tip)
            elif query in tip.tags:
                results.append(tip)
        
        return results
    
    def clear_seen(self) -> None:
        """Clear seen tips."""
        self._seen.clear()


# Global service
_tips_service: Optional[TipsService] = None


def get_tips_service() -> TipsService:
    """Get global tips service."""
    global _tips_service
    if _tips_service is None:
        _tips_service = TipsService()
    return _tips_service


def get_random_tip(category: TipCategory = None) -> Optional[Tip]:
    """Get random tip."""
    return get_tips_service().get_random_tip(category)


__all__ = [
    "TipCategory",
    "Tip",
    "BUILTIN_TIPS",
    "TipsService",
    "get_tips_service",
    "get_random_tip",
]

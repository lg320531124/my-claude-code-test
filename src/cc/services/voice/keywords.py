"""Voice Keywords - Keyword extraction from voice transcripts."""

from __future__ import annotations
import re
from typing import List, Dict, Set
from dataclasses import dataclass, field
from enum import Enum


class KeywordType(Enum):
    """Types of keywords."""
    COMMAND = "command"
    ACTION = "action"
    ENTITY = "entity"
    MODIFIER = "modifier"
    TIME = "time"
    NUMBER = "number"
    BOOLEAN = "boolean"


@dataclass
class KeywordMatch:
    """Matched keyword."""
    keyword: str
    type: KeywordType
    position: int
    confidence: float = 1.0
    context: str = ""
    metadata: Dict = field(default_factory=dict)


@dataclass
class ExtractionResult:
    """Keyword extraction result."""
    keywords: List[KeywordMatch]
    entities: Dict[str, List[str]]
    intents: List[str]
    confidence: float


# Predefined keyword sets
COMMAND_KEYWORDS = {
    "read", "write", "edit", "delete", "create", "open", "close",
    "run", "execute", "start", "stop", "pause", "resume",
    "search", "find", "grep", "glob", "list", "show", "display",
    "commit", "push", "pull", "merge", "branch", "checkout",
    "build", "test", "lint", "format", "check", "verify",
}

ACTION_KEYWORDS = {
    "fix", "solve", "implement", "add", "remove", "update",
    "refactor", "optimize", "simplify", "improve", "enhance",
    "debug", "analyze", "review", "explain", "document",
    "generate", "create", "delete", "move", "copy", "rename",
}

MODIFIER_KEYWORDS = {
    "all", "some", "only", "first", "last", "next", "previous",
    "current", "new", "old", "latest", "earliest",
    "recursive", "force", "safe", "quick", "full", "partial",
}

BOOLEAN_KEYWORDS = {
    "yes", "no", "true", "false", "on", "off", "enable", "disable",
    "confirm", "cancel", "approve", "reject", "accept", "deny",
}

TIME_KEYWORDS = {
    "now", "today", "tomorrow", "yesterday", "later", "soon",
    "morning", "afternoon", "evening", "night",
    "week", "month", "year", "hour", "minute", "second",
}


class KeywordExtractor:
    """Extract keywords from voice transcripts."""

    def __init__(self):
        self._custom_keywords: Dict[KeywordType, Set[str]] = {
            KeywordType.COMMAND: set(),
            KeywordType.ACTION: set(),
            KeywordType.MODIFIER: set(),
        }
        self._stop_words: Set[str] = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "could", "should", "may", "might", "must", "shall",
            "i", "you", "we", "they", "he", "she", "it", "this", "that",
            "in", "on", "at", "by", "for", "with", "about", "to", "from",
        }

    def extract(self, text: str) -> ExtractionResult:
        """Extract keywords from text."""
        keywords = []
        entities = {}
        intents = []

        # Normalize text
        text_lower = text.lower()
        words = re.findall(r"\b\w+\b", text_lower)

        # Extract keywords by type
        for i, word in enumerate(words):
            if word in self._stop_words:
                continue

            keyword_type = None

            if word in COMMAND_KEYWORDS or word in self._custom_keywords[KeywordType.COMMAND]:
                keyword_type = KeywordType.COMMAND
            elif word in ACTION_KEYWORDS or word in self._custom_keywords[KeywordType.ACTION]:
                keyword_type = KeywordType.ACTION
            elif word in MODIFIER_KEYWORDS or word in self._custom_keywords[KeywordType.MODIFIER]:
                keyword_type = KeywordType.MODIFIER
            elif word in BOOLEAN_KEYWORDS:
                keyword_type = KeywordType.BOOLEAN
            elif word in TIME_KEYWORDS:
                keyword_type = KeywordType.TIME
            elif self._is_number(word):
                keyword_type = KeywordType.NUMBER

            if keyword_type:
                keywords.append(KeywordMatch(
                    keyword=word,
                    type=keyword_type,
                    position=i,
                    context=self._get_context(words, i),
                ))

        # Extract entities (files, paths, URLs)
        entities = self._extract_entities(text)

        # Determine intents
        intents = self._determine_intents(keywords)

        # Calculate overall confidence
        confidence = self._calculate_confidence(keywords, intents)

        return ExtractionResult(
            keywords=keywords,
            entities=entities,
            intents=intents,
            confidence=confidence,
        )

    def _is_number(self, word: str) -> bool:
        """Check if word is a number."""
        try:
            float(word)
            return True
        except ValueError:
            return False

    def _get_context(self, words: List[str], position: int, window: int = 3) -> str:
        """Get context around position."""
        start = max(0, position - window)
        end = min(len(words), position + window + 1)
        return " ".join(words[start:end])

    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract entities from text."""
        entities = {}

        # File paths
        file_pattern = r"[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+"
        files = re.findall(file_pattern, text)
        if files:
            entities["files"] = files

        # URLs
        url_pattern = r"https?://[^\s]+"
        urls = re.findall(url_pattern, text)
        if urls:
            entities["urls"] = urls

        # Package names
        package_pattern = r"@[\w\-]+/[\w\-]+|[\w\-]+-[\w\-]+"
        packages = re.findall(package_pattern, text)
        if packages:
            entities["packages"] = packages

        # Code references
        code_pattern = r"`[^`]+`|'[^']+'"
        code_refs = re.findall(code_pattern, text)
        if code_refs:
            entities["code"] = [ref.strip("`'") for ref in code_refs]

        return entities

    def _determine_intents(self, keywords: List[KeywordMatch]) -> List[str]:
        """Determine intents from keywords."""
        intents = []

        keyword_set = {k.keyword for k in keywords}

        # File operations
        if {"read", "file"} & keyword_set:
            intents.append("file_read")
        if {"write", "create", "file"} & keyword_set:
            intents.append("file_write")
        if {"edit", "modify"} & keyword_set:
            intents.append("file_edit")

        # Git operations
        if {"commit"} & keyword_set:
            intents.append("git_commit")
        if {"push"} & keyword_set:
            intents.append("git_push")
        if {"branch"} & keyword_set:
            intents.append("git_branch")

        # Build/test
        if {"run", "test"} & keyword_set:
            intents.append("run_tests")
        if {"build"} & keyword_set:
            intents.append("build")

        # Search
        if {"search", "find", "grep"} & keyword_set:
            intents.append("search")

        return intents

    def _calculate_confidence(
        self,
        keywords: List[KeywordMatch],
        intents: List[str],
    ) -> float:
        """Calculate extraction confidence."""
        if not keywords:
            return 0.0

        # Base confidence from keyword count
        keyword_conf = min(1.0, len(keywords) / 5.0)

        # Intent confidence
        intent_conf = 0.8 if intents else 0.4

        return (keyword_conf + intent_conf) / 2

    def add_custom_keyword(self, keyword: str, type: KeywordType) -> None:
        """Add custom keyword."""
        self._custom_keywords[type].add(keyword.lower())

    def remove_custom_keyword(self, keyword: str, type: KeywordType) -> None:
        """Remove custom keyword."""
        self._custom_keywords[type].discard(keyword.lower())


class VoiceCommandParser:
    """Parse voice commands."""

    def __init__(self):
        self._extractor = KeywordExtractor()

    def parse(self, transcript: str) -> Dict:
        """Parse transcript into command."""
        result = self._extractor.extract(transcript)

        # Determine primary command
        command_keywords = [k for k in result.keywords if k.type == KeywordType.COMMAND]
        action_keywords = [k for k in result.keywords if k.type == KeywordType.ACTION]

        primary_action = None
        if action_keywords:
            primary_action = action_keywords[0].keyword
        elif command_keywords:
            primary_action = command_keywords[0].keyword

        # Get modifiers
        modifiers = [k.keyword for k in result.keywords if k.type == KeywordType.MODIFIER]

        # Get targets
        targets = []
        if "files" in result.entities:
            targets.extend(result.entities["files"])
        if "urls" in result.entities:
            targets.extend(result.entities["urls"])

        return {
            "action": primary_action,
            "modifiers": modifiers,
            "targets": targets,
            "entities": result.entities,
            "intents": result.intents,
            "confidence": result.confidence,
            "raw_keywords": [k.keyword for k in result.keywords],
        }


__all__ = [
    "KeywordType",
    "KeywordMatch",
    "ExtractionResult",
    "KeywordExtractor",
    "VoiceCommandParser",
]
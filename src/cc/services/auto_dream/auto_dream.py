"""Auto Dream Service - Automatic dream/plan generation."""

from __future__ import annotations
from typing import List, Dict, Optional, Any, Callable
import json
import time
from dataclasses import dataclass, field
from enum import Enum


class DreamType(Enum):
    """Dream types."""
    PLAN = "plan"
    IDEA = "idea"
    SOLUTION = "solution"
    ALTERNATIVE = "alternative"
    IMPROVEMENT = "improvement"


@dataclass
class Dream:
    """Generated dream/idea."""
    id: str
    type: DreamType
    title: str
    content: str
    reasoning: str = ""
    created_at: float = field(default_factory=time.time)
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)


@dataclass
class DreamContext:
    """Context for dream generation."""
    problem: str
    constraints: List[str] = field(default_factory=list)
    preferences: List[str] = field(default_factory=list)
    existing_solutions: List[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


class AutoDreamService:
    """Service for automatic dream/plan generation."""

    def __init__(self):
        self._dreams: Dict[str, Dream] = {}
        self._patterns: Dict[str, List[str]] = {
            "problem_analysis": [
                "What is the core problem?",
                "What are the symptoms?",
                "What are the root causes?",
                "What constraints exist?",
            ],
            "solution_generation": [
                "What are possible solutions?",
                "What are trade-offs?",
                "What is the recommended approach?",
                "What are implementation steps?",
            ],
            "improvement_analysis": [
                "What can be improved?",
                "What are bottlenecks?",
                "What optimizations are possible?",
                "What alternative approaches exist?",
            ],
        }

    def dream(
        self,
        context: DreamContext,
        type: DreamType = DreamType.SOLUTION,
        count: int = 3,
    ) -> List[Dream]:
        """Generate dreams based on context."""
        dreams = []

        for i in range(count):
            dream_id = f"dream_{len(self._dreams)}_{int(time.time())}_{i}"

            content = self._generate_content(context, type)

            dream = Dream(
                id=dream_id,
                type=type,
                title=self._generate_title(context, type, i),
                content=content,
                reasoning=self._generate_reasoning(context, type),
                confidence=self._calculate_confidence(context, content),
                metadata={
                    "context_problem": context.problem,
                    "generated_at": time.time(),
                },
            )

            self._dreams[dream_id] = dream
            dreams.append(dream)

        return dreams

    def _generate_title(self, context: DreamContext, type: DreamType, index: int) -> str:
        """Generate dream title."""
        base_titles = {
            DreamType.PLAN: ["Implementation Plan", "Action Plan", "Roadmap"],
            DreamType.IDEA: ["New Idea", "Creative Concept", "Innovation"],
            DreamType.SOLUTION: ["Proposed Solution", "Recommended Approach", "Alternative Solution"],
            DreamType.ALTERNATIVE: ["Alternative Approach", "Different Perspective", "Other Option"],
            DreamType.IMPROVEMENT: ["Improvement Proposal", "Optimization Plan", "Enhancement"],
        }

        titles = base_titles.get(type, ["Dream"])
        return titles[index % len(titles)]

    def _generate_content(self, context: DreamContext, type: DreamType) -> str:
        """Generate dream content."""
        patterns = self._patterns.get(
            "problem_analysis" if type == DreamType.PLAN else
            "solution_generation" if type == DreamType.SOLUTION else
            "improvement_analysis",
            []
        )

        sections = []
        sections.append(f"Problem: {context.problem}")

        if context.constraints:
            sections.append("Constraints:\n- " + "\n- ".join(context.constraints))

        if context.preferences:
            sections.append("Preferences:\n- " + "\n- ".join(context.preferences))

        # Generate steps based on type
        if type == DreamType.SOLUTION:
            sections.append("Recommended Steps:")
            steps = self._generate_steps(context)
            sections.append("\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)))

        elif type == DreamType.PLAN:
            sections.append("Plan Phases:")
            phases = self._generate_phases(context)
            sections.append("\n".join(f"## {p}" for p in phases))

        elif type == DreamType.IMPROVEMENT:
            sections.append("Improvement Areas:")
            areas = self._generate_improvements(context)
            sections.append("\n".join(f"- {a}" for a in areas))

        return "\n\n".join(sections)

    def _generate_steps(self, context: DreamContext) -> List[str]:
        """Generate solution steps."""
        return [
            "Analyze the current state",
            "Identify key changes needed",
            "Design implementation approach",
            "Execute changes incrementally",
            "Validate results",
            "Iterate if needed",
        ]

    def _generate_phases(self, context: DreamContext) -> List[str]:
        """Generate plan phases."""
        return [
            "Discovery - Understand requirements",
            "Design - Create architecture",
            "Implementation - Build solution",
            "Testing - Verify correctness",
            "Deployment - Release to production",
            "Monitoring - Track performance",
        ]

    def _generate_improvements(self, context: DreamContext) -> List[str]:
        """Generate improvement areas."""
        return [
            "Performance optimization",
            "Code quality improvements",
            "Architecture refinements",
            "Feature enhancements",
            "Documentation updates",
        ]

    def _generate_reasoning(self, context: DreamContext, type: DreamType) -> str:
        """Generate reasoning for the dream."""
        reasoning = [
            f"Based on problem: '{context.problem}'",
            f"Dream type: {type.value}",
        ]

        if context.constraints:
            reasoning.append(f"Considering constraints: {len(context.constraints)}")

        if context.existing_solutions:
            reasoning.append(f"Evaluating against existing solutions: {len(context.existing_solutions)}")

        return ". ".join(reasoning)

    def _calculate_confidence(self, context: DreamContext, content: str) -> float:
        """Calculate confidence score."""
        # Simple heuristic
        score = 0.5

        if context.constraints:
            score += 0.1

        if context.preferences:
            score += 0.1

        if context.existing_solutions:
            score += 0.15

        # Cap at 0.95
        return min(score, 0.95)

    def get_dream(self, dream_id: str) -> Dream | None:
        """Get dream by ID."""
        return self._dreams.get(dream_id)

    def get_dreams_by_type(self, type: DreamType) -> List[Dream]:
        """Get dreams by type."""
        return [d for d in self._dreams.values() if d.type == type]

    def get_top_dreams(self, limit: int = 10) -> List[Dream]:
        """Get top dreams by confidence."""
        sorted_dreams = sorted(
            self._dreams.values(),
            key=lambda d: d.confidence,
            reverse=True,
        )
        return sorted_dreams[:limit]

    def delete_dream(self, dream_id: str) -> bool:
        """Delete a dream."""
        if dream_id in self._dreams:
            del self._dreams[dream_id]
            return True
        return False

    def export_dreams(self) -> str:
        """Export dreams as JSON."""
        data = {
            "dreams": [
                {
                    "id": d.id,
                    "type": d.type.value,
                    "title": d.title,
                    "content": d.content,
                    "reasoning": d.reasoning,
                    "confidence": d.confidence,
                    "created_at": d.created_at,
                }
                for d in self._dreams.values()
            ]
        }
        return json.dumps(data, indent=2)

    def get_stats(self) -> dict:
        """Get dream statistics."""
        by_type: Dict[str, int] = {}
        for dream in self._dreams.values():
            by_type[dream.type.value] = by_type.get(dream.type.value, 0) + 1

        avg_confidence = (
            sum(d.confidence for d in self._dreams.values()) / len(self._dreams)
            if self._dreams else 0
        )

        return {
            "total_dreams": len(self._dreams),
            "by_type": by_type,
            "avg_confidence": avg_confidence,
        }


__all__ = [
    "DreamType",
    "Dream",
    "DreamContext",
    "AutoDreamService",
]

"""Feedback Command - Submit feedback."""

from __future__ import annotations
import json
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class FeedbackType(Enum):
    """Feedback types."""
    BUG = "bug"
    FEATURE = "feature"
    IMPROVEMENT = "improvement"
    GENERAL = "general"


@dataclass
class FeedbackData:
    """Feedback data."""
    type: FeedbackType
    message: str
    context: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: str = ""


async def run_feedback(data: FeedbackData) -> Dict[str, Any]:
    """Submit feedback."""
    data.timestamp = datetime.now().isoformat()
    
    # Store locally
    feedback_path = Path.home() / ".claude-code-py" / "feedback.json"
    feedback_path.parent.mkdir(parents=True, exist_ok=True)
    
    feedbacks = []
    if feedback_path.exists():
        try:
            feedbacks = json.loads(feedback_path.read_text())
        except:
            pass
    
    feedbacks.append({
        "type": data.type.value,
        "message": data.message,
        "context": data.context,
        "session_id": data.session_id,
        "timestamp": data.timestamp,
    })
    
    feedback_path.write_text(json.dumps(feedbacks, indent=2))
    
    # In real implementation, would submit to API
    return {
        "success": True,
        "feedback_id": f"fb_{len(feedbacks)}",
        "stored": str(feedback_path),
    }


async def list_feedback(limit: int = 10) -> List[Dict[str, Any]]:
    """List submitted feedback."""
    feedback_path = Path.home() / ".claude-code-py" / "feedback.json"
    
    if not feedback_path.exists():
        return []
    
    try:
        feedbacks = json.loads(feedback_path.read_text())
        return feedbacks[-limit:]
    except:
        return []


class FeedbackCommand:
    """Feedback command implementation."""
    
    name = "feedback"
    description = "Submit feedback"
    
    async def execute(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Execute feedback command."""
        data = FeedbackData(
            type=FeedbackType(args.get("type", "general")),
            message=args.get("message", ""),
            context=args.get("context"),
            session_id=args.get("session_id"),
        )
        
        if not data.message:
            return {"success": False, "error": "Message required"}
        
        return await run_feedback(data)


__all__ = [
    "FeedbackType",
    "FeedbackData",
    "run_feedback",
    "list_feedback",
    "FeedbackCommand",
]

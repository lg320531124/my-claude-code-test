"""Teleport Utilities - Teleport functionality."""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class TeleportLocation:
    """Teleport location."""
    name: str
    path: str
    description: str = ""
    last_visited: datetime = None
    visit_count: int = 0
    tags: List[str] = field(default_factory=list)


@dataclass
class TeleportHistory:
    """Teleport history entry."""
    from_location: str
    to_location: str
    timestamp: datetime


class TeleportManager:
    """Manage teleport locations."""
    
    def __init__(self):
        self._locations: Dict[str, TeleportLocation] = {}
        self._history: List[TeleportHistory] = []
        self._current: Optional[str] = None
    
    def add_location(self, location: TeleportLocation) -> None:
        """Add teleport location."""
        self._locations[location.name] = location
    
    def remove_location(self, name: str) -> bool:
        """Remove location."""
        if name in self._locations:
            del self._locations[name]
            return True
        return False
    
    def teleport(self, name: str) -> Optional[Path]:
        """Teleport to location."""
        location = self._locations.get(name)
        
        if not location:
            return None
        
        # Record history
        if self._current:
            self._history.append(TeleportHistory(
                from_location=self._current,
                to_location=name,
                timestamp=datetime.now(),
            ))
        
        # Update location stats
        location.last_visited = datetime.now()
        location.visit_count += 1
        
        self._current = name
        
        return Path(location.path)
    
    def get_location(self, name: str) -> Optional[TeleportLocation]:
        """Get location."""
        return self._locations.get(name)
    
    def list_locations(self) -> List[TeleportLocation]:
        """List all locations."""
        return list(self._locations.values())
    
    def search(self, query: str) -> List[TeleportLocation]:
        """Search locations."""
        query = query.lower()
        results = []
        
        for loc in self._locations.values():
            if query in loc.name.lower():
                results.append(loc)
            elif query in loc.path.lower():
                results.append(loc)
            elif query in loc.description.lower():
                results.append(loc)
        
        return results
    
    def get_frequent(self, limit: int = 5) -> List[TeleportLocation]:
        """Get most visited locations."""
        sorted_locs = sorted(
            self._locations.values(),
            key=lambda x: x.visit_count,
            reverse=True
        )
        return sorted_locs[:limit]
    
    def get_recent(self, limit: int = 5) -> List[TeleportLocation]:
        """Get recently visited."""
        recent = [
            loc for loc in self._locations.values()
            if loc.last_visited
        ]
        sorted_locs = sorted(
            recent,
            key=lambda x: x.last_visited,
            reverse=True
        )
        return sorted_locs[:limit]
    
    def get_history(self, limit: int = 10) -> List[TeleportHistory]:
        """Get teleport history."""
        return self._history[-limit:]
    
    def go_back(self) -> Optional[str]:
        """Go back to previous location."""
        if len(self._history) < 1:
            return None
        
        last = self._history[-1]
        self.teleport(last.from_location)
        return last.from_location
    
    def export(self) -> Dict[str, Any]:
        """Export locations."""
        return {
            name: {
                "path": loc.path,
                "description": loc.description,
                "tags": loc.tags,
            }
            for name, loc in self._locations.items()
        }
    
    def import_locations(self, data: Dict[str, Any]) -> int:
        """Import locations."""
        count = 0
        
        for name, info in data.items():
            self.add_location(TeleportLocation(
                name=name,
                path=info.get("path", ""),
                description=info.get("description", ""),
                tags=info.get("tags", []),
            ))
            count += 1
        
        return count


__all__ = [
    "TeleportLocation",
    "TeleportHistory",
    "TeleportManager",
]

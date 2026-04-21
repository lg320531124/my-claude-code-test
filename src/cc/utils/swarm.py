"""Swarm Utilities - Multi-agent coordination."""

from __future__ import annotations
import asyncio
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class SwarmState(Enum):
    """Swarm states."""
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETE = "complete"
    FAILED = "failed"


class AgentRole(Enum):
    """Agent roles in swarm."""
    LEADER = "leader"
    WORKER = "worker"
    REVIEWER = "reviewer"
    COORDINATOR = "coordinator"


@dataclass
class SwarmAgent:
    """Swarm agent."""
    id: str
    role: AgentRole
    task: str = ""
    status: str = "idle"
    result: Any = None
    started_at: datetime = None
    completed_at: datetime = None


@dataclass
class SwarmConfig:
    """Swarm configuration."""
    max_agents: int = 5
    timeout: float = 300.0
    parallel: bool = True
    retry_count: int = 3
    coordination_interval: float = 10.0


@dataclass
class SwarmResult:
    """Swarm execution result."""
    swarm_id: str
    state: SwarmState
    agents: List[SwarmAgent] = field(default_factory=list)
    total_time: float = 0.0
    success_count: int = 0
    failure_count: int = 0


class SwarmCoordinator:
    """Coordinate swarm of agents."""
    
    def __init__(self, config: SwarmConfig = None):
        self.config = config or SwarmConfig()
        self._swarms: Dict[str, SwarmResult] = {}
        self._agents: Dict[str, SwarmAgent] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
    
    def create_swarm(self, task: str, roles: List[AgentRole] = None) -> str:
        """Create new swarm."""
        import uuid
        swarm_id = str(uuid.uuid4())[:8]
        
        roles = roles or [AgentRole.LEADER, AgentRole.WORKER, AgentRole.WORKER]
        
        agents = []
        for i, role in enumerate(roles):
            agent = SwarmAgent(
                id=f"{swarm_id}_agent_{i}",
                role=role,
            )
            agents.append(agent)
            self._agents[agent.id] = agent
        
        self._swarms[swarm_id] = SwarmResult(
            swarm_id=swarm_id,
            state=SwarmState.IDLE,
            agents=agents,
        )
        
        return swarm_id
    
    async def run_swarm(self, swarm_id: str) -> SwarmResult:
        """Run swarm."""
        swarm = self._swarms.get(swarm_id)
        if not swarm:
            raise ValueError(f"Swarm {swarm_id} not found")
        
        swarm.state = SwarmState.RUNNING
        
        # Assign task to leader
        leader = next((a for a in swarm.agents if a.role == AgentRole.LEADER), None)
        if leader:
            leader.task = "Coordinate and distribute work"
            leader.status = "running"
            leader.started_at = datetime.now()
        
        # Distribute work to workers
        workers = [a for a in swarm.agents if a.role == AgentRole.WORKER]
        for worker in workers:
            worker.task = "Execute subtask"
            worker.status = "running"
            worker.started_at = datetime.now()
        
        # Simulate execution
        await asyncio.sleep(0.5)
        
        # Mark complete
        for agent in swarm.agents:
            agent.status = "complete"
            agent.completed_at = datetime.now()
        
        swarm.state = SwarmState.COMPLETE
        swarm.success_count = len(swarm.agents)
        
        return swarm
    
    def get_swarm(self, swarm_id: str) -> Optional[SwarmResult]:
        """Get swarm."""
        return self._swarms.get(swarm_id)
    
    def get_agent(self, agent_id: str) -> Optional[SwarmAgent]:
        """Get agent."""
        return self._agents.get(agent_id)
    
    def cancel_swarm(self, swarm_id: str) -> bool:
        """Cancel swarm."""
        swarm = self._swarms.get(swarm_id)
        if swarm:
            swarm.state = SwarmState.FAILED
            for agent in swarm.agents:
                agent.status = "cancelled"
            return True
        return False
    
    def list_swarms(self) -> List[str]:
        """List swarm IDs."""
        return list(self._swarms.keys())


__all__ = [
    "SwarmState",
    "AgentRole",
    "SwarmAgent",
    "SwarmConfig",
    "SwarmResult",
    "SwarmCoordinator",
]

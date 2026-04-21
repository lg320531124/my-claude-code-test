"""SSH Utilities - SSH connection handling."""

from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum


class SSHAuthType(Enum):
    """SSH authentication types."""
    PASSWORD = "password"
    KEY = "key"
    AGENT = "agent"
    NONE = "none"


@dataclass
class SSHConfig:
    """SSH configuration."""
    host: str
    port: int = 22
    user: str = ""
    auth_type: SSHAuthType = SSHAuthType.KEY
    key_path: Optional[str] = None
    password: Optional[str] = None
    timeout: int = 30
    options: Dict[str, str] = field(default_factory=dict)


@dataclass
class SSHConnection:
    """SSH connection info."""
    host: str
    connected: bool = False
    session: Any = None


class SSHManager:
    """Manage SSH connections."""
    
    def __init__(self):
        self._connections: Dict[str, SSHConnection] = {}
        self._config_path: Path = Path.home() / ".ssh" / "config"
    
    def load_config(self) -> Dict[str, SSHConfig]:
        """Load SSH config file."""
        configs = {}
        
        if not self._config_path.exists():
            return configs
        
        try:
            content = self._config_path.read_text()
            current_host = None
            current_config = {}
            
            for line in content.splitlines():
                line = line.strip()
                
                if not line or line.startswith("#"):
                    continue
                
                if line.lower().startswith("host "):
                    if current_host:
                        configs[current_host] = SSHConfig(
                            host=current_host,
                            **current_config
                        )
                    current_host = line.split()[1]
                    current_config = {}
                
                elif current_host:
                    parts = line.split()
                    if len(parts) >= 2:
                        key = parts[0].lower()
                        value = parts[1]
                        
                        if key == "hostname":
                            current_config["host"] = value
                        elif key == "port":
                            current_config["port"] = int(value)
                        elif key == "user":
                            current_config["user"] = value
                        elif key == "identityfile":
                            current_config["key_path"] = value
            
            if current_host:
                configs[current_host] = SSHConfig(
                    host=current_host,
                    **current_config
                )
        except:
            pass
        
        return configs
    
    async def connect(self, config: SSHConfig) -> SSHConnection:
        """Connect to SSH host."""
        connection = SSHConnection(host=config.host)
        
        # Simulate connection (would use asyncssh in real implementation)
        await asyncio.sleep(0.1)
        
        connection.connected = True
        self._connections[config.host] = connection
        
        return connection
    
    async def disconnect(self, host: str) -> bool:
        """Disconnect from host."""
        if host in self._connections:
            self._connections[host].connected = False
            del self._connections[host]
            return True
        return False
    
    async def execute(self, host: str, command: str) -> tuple[str, str]:
        """Execute command on SSH host."""
        if host not in self._connections:
            return "", "Not connected"
        
        # Simulate execution
        await asyncio.sleep(0.1)
        return f"Executed on {host}: {command}", ""
    
    def get_connection(self, host: str) -> Optional[SSHConnection]:
        """Get connection."""
        return self._connections.get(host)
    
    def list_connections(self) -> List[str]:
        """List active connections."""
        return [h for h, c in self._connections.items() if c.connected]


__all__ = [
    "SSHAuthType",
    "SSHConfig",
    "SSHConnection",
    "SSHManager",
]

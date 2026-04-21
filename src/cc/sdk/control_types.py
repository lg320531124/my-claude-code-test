"""Control Types - SDK control protocol types.

Types for control requests and responses in the SDK protocol.
"""

from __future__ import annotations
from typing import Any, Optional, Dict, Union
from dataclasses import dataclass, field


@dataclass
class SDKControlPermissionRequest:
    """Permission request from CCR.

    subtype: 'can_use_tool'
    """
    subtype: str = "can_use_tool"
    tool_name: str = ""
    tool_use_id: Optional[str] = None
    input: Dict[str, Any] = field(default_factory=dict)
    context: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        result = {
            "subtype": self.subtype,
            "tool_name": self.tool_name,
            "input": self.input,
        }
        if self.tool_use_id:
            result["tool_use_id"] = self.tool_use_id
        if self.context:
            result["context"] = self.context
        return result


@dataclass
class SDKControlInterruptRequest:
    """Interrupt request from CCR.

    subtype: 'interrupt'
    """
    subtype: str = "interrupt"


SDKControlRequestInner = Union[SDKControlPermissionRequest, SDKControlInterruptRequest]


@dataclass
class SDKControlRequest:
    """Control request wrapper."""
    type: str = "control_request"
    request_id: str = ""
    request: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "request_id": self.request_id,
            "request": self.request,
        }


@dataclass
class SDKControlResponse:
    """Control response wrapper."""
    type: str = "control_response"
    response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "response": self.response,
        }


@dataclass
class SDKControlCancelRequest:
    """Control cancel request.

    Server cancelling a pending permission request.
    """
    type: str = "control_cancel_request"
    request_id: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "type": self.type,
            "request_id": self.request_id,
        }
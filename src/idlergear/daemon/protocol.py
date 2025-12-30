"""JSON-RPC 2.0 protocol implementation for daemon communication."""

from dataclasses import dataclass, field
from typing import Any
import json


@dataclass
class Request:
    """JSON-RPC 2.0 request."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)
    id: int | str | None = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        msg = {
            "jsonrpc": "2.0",
            "method": self.method,
        }
        if self.params:
            msg["params"] = self.params
        if self.id is not None:
            msg["id"] = self.id
        return json.dumps(msg)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Request":
        """Parse from dictionary."""
        return cls(
            method=data["method"],
            params=data.get("params", {}),
            id=data.get("id"),
        )


@dataclass
class Response:
    """JSON-RPC 2.0 response."""

    id: int | str | None
    result: Any = None
    error: dict[str, Any] | None = None

    def to_json(self) -> str:
        """Serialize to JSON string."""
        msg: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": self.id,
        }
        if self.error is not None:
            msg["error"] = self.error
        else:
            msg["result"] = self.result
        return json.dumps(msg)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Response":
        """Parse from dictionary."""
        return cls(
            id=data.get("id"),
            result=data.get("result"),
            error=data.get("error"),
        )

    @classmethod
    def success(cls, id: int | str | None, result: Any = None) -> "Response":
        """Create a success response."""
        return cls(id=id, result=result)

    @classmethod
    def error_response(
        cls,
        id: int | str | None,
        code: int,
        message: str,
        data: Any = None,
    ) -> "Response":
        """Create an error response."""
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return cls(id=id, error=error)


@dataclass
class Notification:
    """JSON-RPC 2.0 notification (request without id)."""

    method: str
    params: dict[str, Any] = field(default_factory=dict)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        msg = {
            "jsonrpc": "2.0",
            "method": self.method,
        }
        if self.params:
            msg["params"] = self.params
        return json.dumps(msg)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Notification":
        """Parse from dictionary."""
        return cls(
            method=data["method"],
            params=data.get("params", {}),
        )


# Standard JSON-RPC 2.0 error codes
class ErrorCode:
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # Custom error codes (application-specific, -32000 to -32099)
    NOT_INITIALIZED = -32000
    LOCK_CONFLICT = -32001
    FILE_NOT_FOUND = -32002


def parse_message(data: str) -> Request | Response | Notification:
    """Parse a JSON-RPC message from string."""
    try:
        msg = json.loads(data)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON: {e}")

    if "jsonrpc" not in msg or msg["jsonrpc"] != "2.0":
        raise ValueError("Invalid JSON-RPC version")

    # Response has result or error
    if "result" in msg or "error" in msg:
        return Response.from_dict(msg)

    # Request/Notification has method
    if "method" in msg:
        if "id" in msg:
            return Request.from_dict(msg)
        return Notification.from_dict(msg)

    raise ValueError("Invalid JSON-RPC message")

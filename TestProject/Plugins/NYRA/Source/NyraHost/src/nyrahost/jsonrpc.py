"""JSON-RPC 2.0 envelope parsing + builders.

See docs/JSONRPC.md for the canonical wire format. Implements D-09
(JSON-RPC envelope) + D-11 (error.data.remediation contract).

Returns a tagged union (via isinstance checks) of RequestEnvelope,
NotificationEnvelope, ResponseEnvelope, ErrorEnvelope. Malformed frames
raise ProtocolError (callers typically log + close the WS with 4401 or
respond with an error envelope).
"""
from __future__ import annotations
import json
from dataclasses import dataclass
from typing import Any, Union


@dataclass(frozen=True)
class RequestEnvelope:
    id: int | str
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class NotificationEnvelope:
    method: str
    params: dict[str, Any]


@dataclass(frozen=True)
class ResponseEnvelope:
    id: int | str
    result: dict[str, Any]


@dataclass(frozen=True)
class ErrorEnvelope:
    id: int | str | None
    code: int
    message: str
    remediation: str | None


Envelope = Union[
    RequestEnvelope, NotificationEnvelope, ResponseEnvelope, ErrorEnvelope
]


class ProtocolError(Exception):
    """Raised when an incoming frame is not valid JSON-RPC 2.0."""

    def __init__(self, message: str, *, recv_id: int | str | None = None):
        super().__init__(message)
        self.recv_id = recv_id


def parse_envelope(frame: str) -> Envelope:
    try:
        obj = json.loads(frame)
    except json.JSONDecodeError as e:
        raise ProtocolError(f"invalid_json: {e}") from e
    if not isinstance(obj, dict):
        raise ProtocolError("envelope_not_object")
    if obj.get("jsonrpc") != "2.0":
        raise ProtocolError("missing_or_wrong_jsonrpc_version")

    if "method" in obj:
        method = obj["method"]
        params = obj.get("params", {}) or {}
        if not isinstance(method, str):
            raise ProtocolError("method_not_string")
        if not isinstance(params, dict):
            raise ProtocolError("params_not_object")
        # WR-08: per JSON-RPC 2.0 §4 — id MUST be String, Number, or NULL
        # if included; absence means notification. Some buggy clients
        # send `"id": null` to indicate "I don't care about a response"
        # which is semantically a notification. Treat both the absent and
        # null cases as notifications so handlers don't reply to a void
        # id (the spec also forbids using NULL except as the response id
        # for an error where the request id couldn't be parsed).
        if "id" in obj and obj["id"] is not None:
            rid = obj["id"]
            if not isinstance(rid, (int, str)):
                raise ProtocolError("id_not_string_or_number")
            return RequestEnvelope(id=rid, method=method, params=params)
        return NotificationEnvelope(method=method, params=params)

    if "result" in obj:
        if "id" not in obj:
            raise ProtocolError("response_missing_id")
        return ResponseEnvelope(id=obj["id"], result=obj["result"])

    if "error" in obj:
        e = obj["error"]
        return ErrorEnvelope(
            id=obj.get("id"),
            code=int(e.get("code", 0)),
            message=str(e.get("message", "")),
            remediation=(e.get("data") or {}).get("remediation"),
        )
    raise ProtocolError("envelope_has_neither_method_nor_result_nor_error")


def build_response(id_: int | str, result: dict[str, Any]) -> str:
    return json.dumps(
        {"jsonrpc": "2.0", "id": id_, "result": result},
        separators=(",", ":"),
    )


def build_error(
    id_: int | str | None,
    *,
    code: int,
    message: str,
    remediation: str,
) -> str:
    envelope: dict[str, Any] = {
        "jsonrpc": "2.0",
        "id": id_,
        "error": {
            "code": code,
            "message": message,
            "data": {"remediation": remediation},
        },
    }
    return json.dumps(envelope, separators=(",", ":"))


def build_notification(method: str, params: dict[str, Any]) -> str:
    return json.dumps(
        {"jsonrpc": "2.0", "method": method, "params": params},
        separators=(",", ":"),
    )

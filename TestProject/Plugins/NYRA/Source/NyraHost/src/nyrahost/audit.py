"""nyrahost.audit — Phase 13-D append-only audit log.

Tier 2 privacy moat. Aura is SaaS — every prompt, tool call, and
permission decision flows through their backend. Studios under NDA
or working on unreleased IP can't audit what left their machine.

NYRA writes a per-project ``Saved/NYRA/audit.jsonl`` JSONL stream with
every event so the user (or their security review) can grep what
happened. Each line is a complete JSON object — append-only, no edits,
no cross-line state, so a single line corruption never breaks the
parser.

Event categories:
  * prompt_in   — user typed a prompt
  * tool_call   — an MCP tool was invoked (planned or executed)
  * permission  — NyraPermissionGate decision (approve / reject)
  * outbound    — external HTTP made (Meshy / ComfyUI / Claude CLI)
  * model_pin   — per-conversation model pin changed
  * mode_change — operating mode or backend mode changed

Threat mitigations:
  * T-13-01: write-only file. open with 'a' mode every event; never
    re-read what's there. A malicious edit between events can corrupt
    history but cannot affect future writes.
  * T-13-02: secrets are never logged. Token / api_key fields are
    redacted via a closed-set name match BEFORE serialisation.
  * T-13-03: line size cap (32 KB) so a giant pasted prompt can't
    blow log-rotation budgets.
"""
from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.audit")

AUDIT_FILENAME: Final[str] = "audit.jsonl"
MAX_LINE_BYTES: Final[int] = 32 * 1024

# Closed set of field names that may carry secrets — redacted on the
# fly before serialisation. Matches the ClaudeBackend env-scrub list
# from D-02.
SECRET_FIELDS: Final[frozenset[str]] = frozenset({
    "token",
    "auth_token",
    "api_key",
    "MESHY_API_KEY",
    "ANTHROPIC_API_KEY",
    "ANTHROPIC_AUTH_TOKEN",
    "Authorization",
    "password",
    "secret",
})


def _audit_path(project_dir: Path) -> Path:
    return Path(project_dir) / "Saved" / "NYRA" / AUDIT_FILENAME


def _redact(d: dict) -> dict:
    """Recursively replace any value whose key matches SECRET_FIELDS
    with the string ``"<redacted>"``. Returns a new dict — never
    mutates the input."""
    out: dict = {}
    for k, v in d.items():
        if k in SECRET_FIELDS:
            out[k] = "<redacted>"
        elif isinstance(v, dict):
            out[k] = _redact(v)
        elif isinstance(v, list):
            out[k] = [_redact(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


@dataclass
class AuditLog:
    """Per-project append-only JSONL audit log."""

    project_dir: Path

    def __post_init__(self) -> None:
        self.path = _audit_path(self.project_dir)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _write(self, kind: str, payload: dict) -> dict:
        record = {
            "ts": time.time(),
            "id": str(uuid.uuid4())[:8],
            "kind": kind,
            **_redact(payload),
        }
        line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        if len(line.encode("utf-8")) > MAX_LINE_BYTES:
            # Trim the body but keep the envelope so an oversize prompt
            # is still represented as an event.
            record["_truncated"] = True
            for key in ("content", "prompt", "body", "stdout", "stderr"):
                if key in record and isinstance(record[key], str):
                    record[key] = record[key][:1024] + "...<truncated>"
            line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
        # T-13-01: open append for every event; no fsync needed for
        # logging (kernel page cache + monitor-mode sync is enough).
        with self.path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        return record

    # --- typed event entries ---

    def prompt_in(self, *, conversation_id: str, prompt: str,
                  model: str | None = None) -> dict:
        return self._write("prompt_in", {
            "conversation_id": conversation_id,
            "prompt": prompt,
            "model": model,
        })

    def tool_call(self, *, name: str, args: dict, decided: str = "queued",
                  conversation_id: str | None = None) -> dict:
        return self._write("tool_call", {
            "tool": name,
            "args": args,
            "decided": decided,
            "conversation_id": conversation_id,
        })

    def permission(self, *, plan_id: str, decision: str,
                   reason: str | None = None) -> dict:
        return self._write("permission", {
            "plan_id": plan_id,
            "decision": decision,
            "reason": reason,
        })

    def outbound(self, *, target: str, method: str = "POST",
                 status: int | None = None, bytes_sent: int | None = None,
                 bytes_received: int | None = None) -> dict:
        return self._write("outbound", {
            "target": target,
            "method": method,
            "status": status,
            "bytes_sent": bytes_sent,
            "bytes_received": bytes_received,
        })

    def model_pin(self, *, conversation_id: str,
                  model: str | None) -> dict:
        return self._write("model_pin", {
            "conversation_id": conversation_id,
            "model": model,
        })

    def mode_change(self, *, axis: str, new_value: str) -> dict:
        return self._write("mode_change", {
            "axis": axis,
            "new_value": new_value,
        })

    def read_all(self) -> Iterable[dict]:
        """Yield every record. Skip lines that fail to parse so a
        partial flush during a crash doesn't break diagnostics."""
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError:
                    continue


__all__ = [
    "AuditLog",
    "AUDIT_FILENAME",
    "MAX_LINE_BYTES",
    "SECRET_FIELDS",
]

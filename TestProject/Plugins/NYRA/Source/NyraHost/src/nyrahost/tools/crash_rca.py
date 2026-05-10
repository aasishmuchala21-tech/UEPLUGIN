"""nyrahost.tools.crash_rca — Phase 14-E Crash RCA Agent (Tier 2 moat).

Reads UE crash dumps under ``<ProjectDir>/Saved/Crashes/`` and
extracts:
  * the assertion / exception message
  * the top N callstack frames
  * a stable signature hash for de-duplication

Aura's per-event SaaS pricing makes per-crash LLM calls expensive
even when nothing is wrong. NYRA does the parse + signature work
locally (zero token cost) and only sends the SUMMARY to the agent
when the user explicitly asks for an explanation.
"""
from __future__ import annotations

import hashlib
import json
import re
import string
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.crash_rca")

ERR_BAD_INPUT: Final[int] = -32602
ERR_RCA_FAILED: Final[int] = -32059

CRASHES_DIRNAME: Final[str] = "Crashes"
DEFAULT_FRAMES: Final[int] = 12
MAX_FRAMES: Final[int] = 100

# UE crash log conventions (verified against UE 5.4–5.6 sample dumps):
#   * Assertion failure header: "Assertion failed: <expr> [...] [Line: N]"
#   * Generic exception header: "Unhandled Exception: <type> ... 0x<addr>"
#   * Callstack lines: "0x<hex> <module>.<dll>!<symbol>+<offset> [path:line]"
ASSERT_RE: Final[re.Pattern[str]] = re.compile(
    r"Assertion failed:\s*(?P<expr>.+?)(?:\s*\[File:.*?\])?\s*\[Line:\s*(?P<line>\d+)\]",
    re.IGNORECASE,
)
EXCEPTION_RE: Final[re.Pattern[str]] = re.compile(
    r"Unhandled Exception:\s*(?P<type>[A-Z0-9_-]+)",
)
FRAME_RE: Final[re.Pattern[str]] = re.compile(
    r"0x[0-9a-f]+\s+(?P<module>[\w.+-]+)!(?P<symbol>[^\s\[]+)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class CrashSignature:
    crash_kind: str             # "assertion" | "exception" | "unknown"
    summary: str                # one-line human description
    top_frames: tuple[str, ...] # module!symbol pairs in callstack order
    signature_hash: str         # sha256 of (kind + first 8 frame symbols)
    source_log: str             # path of the .log we parsed

    def to_dict(self) -> dict:
        return {
            "crash_kind": self.crash_kind,
            "summary": self.summary,
            "top_frames": list(self.top_frames),
            "signature_hash": self.signature_hash,
            "source_log": self.source_log,
        }


def parse_crash_log(text: str, *, source: str = "<inline>",
                    max_frames: int = DEFAULT_FRAMES) -> CrashSignature:
    """Parse a UE crash log body into a CrashSignature."""
    if not isinstance(text, str):
        text = str(text)
    if not (1 <= max_frames <= MAX_FRAMES):
        raise ValueError(f"max_frames {max_frames} out of range 1..{MAX_FRAMES}")

    # Kind + summary
    kind = "unknown"
    summary = ""
    am = ASSERT_RE.search(text)
    em = EXCEPTION_RE.search(text)
    if am:
        kind = "assertion"
        summary = f"Assertion failed: {am.group('expr').strip()} [Line {am.group('line')}]"
    elif em:
        kind = "exception"
        summary = f"Unhandled Exception: {em.group('type')}"

    # Callstack frames
    frames: list[str] = []
    for fm in FRAME_RE.finditer(text):
        frames.append(f"{fm.group('module')}!{fm.group('symbol')}")
        if len(frames) >= max_frames:
            break

    # Stable signature for de-duplication: kind + first 8 frame symbols
    sig_input = kind + "|" + "|".join(frames[:8])
    sig_hash = hashlib.sha256(sig_input.encode("utf-8")).hexdigest()[:16]

    if not summary and frames:
        summary = f"Crash in {frames[0]}"
    if not summary:
        summary = "Crash with no recognised header"

    return CrashSignature(
        crash_kind=kind,
        summary=summary,
        top_frames=tuple(frames),
        signature_hash=sig_hash,
        source_log=source,
    )


def discover_crash_logs(project_dir: Path) -> list[Path]:
    """Walk ``<ProjectDir>/Saved/Crashes/<crash-id>/UEMinidump.log``
    or ``*.log`` and return all matches."""
    crashes_root = Path(project_dir) / "Saved" / CRASHES_DIRNAME
    if not crashes_root.exists():
        return []
    return sorted(crashes_root.rglob("*.log"))


def rca_report(project_dir: Path, *, max_frames: int = DEFAULT_FRAMES) -> dict:
    """Walk the project's crash dir + return one CrashSignature per .log."""
    out: list[dict] = []
    for log_path in discover_crash_logs(project_dir):
        try:
            text = log_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            out.append({"source_log": str(log_path), "error": str(exc)})
            continue
        sig = parse_crash_log(text, source=str(log_path), max_frames=max_frames)
        out.append(sig.to_dict())
    # Aggregate by signature_hash so dupes are visible.
    by_hash: dict[str, dict] = {}
    for entry in out:
        h = entry.get("signature_hash")
        if h is None:
            continue
        if h not in by_hash:
            by_hash[h] = {**entry, "occurrences": 1}
        else:
            by_hash[h]["occurrences"] += 1
    return {
        "project_dir": str(project_dir),
        "total_logs": len(out),
        "unique_signatures": len(by_hash),
        "signatures": list(by_hash.values()),
        "raw": out,
    }


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class CrashRCAHandlers:
    def __init__(self, *, project_dir: Path) -> None:
        self._project_dir = Path(project_dir)

    async def on_run(self, params: dict, session=None, ws=None) -> dict:
        try:
            max_frames = int(params.get("max_frames", DEFAULT_FRAMES))
        except (TypeError, ValueError):
            return _err(ERR_BAD_INPUT, "max_frames_must_be_int")
        try:
            return rca_report(self._project_dir, max_frames=max_frames)
        except (OSError, ValueError) as exc:
            return _err(ERR_RCA_FAILED, "rca_failed", str(exc))


__all__ = [
    "CrashRCAHandlers",
    "CrashSignature",
    "parse_crash_log",
    "discover_crash_logs",
    "rca_report",
    "DEFAULT_FRAMES",
    "MAX_FRAMES",
]

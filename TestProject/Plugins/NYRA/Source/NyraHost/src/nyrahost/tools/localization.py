"""nyrahost.tools.localization — Phase 15-B LOCTEXT extractor (Tier 2).

UE5 localisation pipeline:
  * Strings declared with ``LOCTEXT("KeyName", "English source")``
    or ``NSLOCTEXT("Namespace", "KeyName", "English source")``
  * Per-namespace defined with ``#define LOCTEXT_NAMESPACE "Name"``
    ... ``#undef LOCTEXT_NAMESPACE``

Aura's per-event SaaS pricing makes whole-project string extraction
expensive; NYRA does the regex pass locally (zero token cost) and
emits CSV / JSON / .po-ready output the user can ship to a
translation team OR an LLM for first-pass translation.
"""
from __future__ import annotations

import csv
import io
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final, Iterable, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.localization")

ERR_BAD_INPUT: Final[int] = -32602
ERR_LOC_FAILED: Final[int] = -32065

# UE5 LOCTEXT regex variants. Captures key + source string.
# Handles single-line declarations only — multiline LOCTEXT is rare
# and the agent flags any files it skipped for human review.
LOCTEXT_RE: Final[re.Pattern[str]] = re.compile(
    r'LOCTEXT\(\s*"(?P<key>[^"]*)"\s*,\s*"(?P<source>(?:[^"\\]|\\.)*)"\s*\)',
)
NSLOCTEXT_RE: Final[re.Pattern[str]] = re.compile(
    r'NSLOCTEXT\(\s*"(?P<ns>[^"]*)"\s*,\s*"(?P<key>[^"]*)"\s*,\s*"(?P<source>(?:[^"\\]|\\.)*)"\s*\)',
)
NAMESPACE_DEFINE_RE: Final[re.Pattern[str]] = re.compile(
    r'#define\s+LOCTEXT_NAMESPACE\s+"(?P<ns>[^"]+)"',
)
NAMESPACE_UNDEF_RE: Final[re.Pattern[str]] = re.compile(
    r'#undef\s+LOCTEXT_NAMESPACE',
)


@dataclass(frozen=True)
class LocEntry:
    namespace: str
    key: str
    source: str
    source_file: str
    line: int

    def to_dict(self) -> dict:
        return {
            "namespace": self.namespace,
            "key": self.key,
            "source": self.source,
            "source_file": self.source_file,
            "line": self.line,
        }


def extract_from_text(text: str, *, source_file: str = "<inline>") -> list[LocEntry]:
    """Return every LOCTEXT / NSLOCTEXT entry in source order."""
    out: list[LocEntry] = []
    current_ns = ""
    for line_no, line in enumerate(text.splitlines(), start=1):
        # Namespace bookkeeping
        m_def = NAMESPACE_DEFINE_RE.search(line)
        if m_def:
            current_ns = m_def.group("ns")
        m_undef = NAMESPACE_UNDEF_RE.search(line)
        if m_undef:
            current_ns = ""

        # NSLOCTEXT first (more specific match)
        for m in NSLOCTEXT_RE.finditer(line):
            out.append(LocEntry(
                namespace=m.group("ns"),
                key=m.group("key"),
                source=m.group("source"),
                source_file=source_file,
                line=line_no,
            ))
        # LOCTEXT (uses the current_ns from the file context)
        for m in LOCTEXT_RE.finditer(line):
            out.append(LocEntry(
                namespace=current_ns,
                key=m.group("key"),
                source=m.group("source"),
                source_file=source_file,
                line=line_no,
            ))
    return out


def scan_source_tree(root: Path) -> list[LocEntry]:
    """Walk root, return every extracted LocEntry across .cpp / .h."""
    out: list[LocEntry] = []
    for ext in ("*.cpp", "*.h", "*.hpp", "*.inl"):
        for p in sorted(root.rglob(ext)):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            out.extend(extract_from_text(text, source_file=str(p)))
    return out


def to_csv(entries: Iterable[LocEntry]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["namespace", "key", "source", "source_file", "line"])
    for e in entries:
        w.writerow([e.namespace, e.key, e.source, e.source_file, e.line])
    return buf.getvalue()


def to_json(entries: Iterable[LocEntry]) -> str:
    return json.dumps([e.to_dict() for e in entries], indent=2)


def to_po_skeleton(entries: Iterable[LocEntry], *, lang: str = "fr") -> str:
    """Emit a .po skeleton for one target language; msgstr is left blank
    for translators (or an LLM first-pass) to fill in."""
    lines = [
        'msgid ""',
        'msgstr ""',
        f'"Language: {lang}\\n"',
        '"Content-Type: text/plain; charset=UTF-8\\n"',
        "",
    ]
    seen: set[tuple[str, str]] = set()
    for e in entries:
        if (e.namespace, e.key) in seen:
            continue
        seen.add((e.namespace, e.key))
        lines.append(f"#: {e.source_file}:{e.line}")
        lines.append(f'msgctxt "{e.namespace}/{e.key}"')
        lines.append(f'msgid "{e.source.replace(chr(34), chr(92) + chr(34))}"')
        lines.append('msgstr ""')
        lines.append("")
    return "\n".join(lines)


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


class LocalizationHandlers:
    def __init__(self, *, plugin_source_dir: Path) -> None:
        self._src = Path(plugin_source_dir)

    async def on_scan(self, params: dict, session=None, ws=None) -> dict:
        module = params.get("module")
        if module is not None and not isinstance(module, str):
            return _err(ERR_BAD_INPUT, "bad_type", "module must be str or null")
        root = self._src / module if module else self._src
        if not root.exists():
            return _err(ERR_BAD_INPUT, "module_not_found", str(root))
        try:
            entries = scan_source_tree(root)
        except OSError as exc:
            return _err(ERR_LOC_FAILED, "scan_failed", str(exc))
        return {
            "count": len(entries),
            "entries": [e.to_dict() for e in entries],
            "scanned_root": str(root),
        }

    async def on_emit(self, params: dict, session=None, ws=None) -> dict:
        fmt = params.get("format", "csv")
        if fmt not in {"csv", "json", "po"}:
            return _err(
                ERR_BAD_INPUT, "bad_format",
                f"format must be csv|json|po; got {fmt!r}",
            )
        # Reuse on_scan to get the entries
        scan_resp = await self.on_scan(
            {"module": params.get("module")}, session, ws,
        )
        if "error" in scan_resp:
            return scan_resp
        entries = [
            LocEntry(
                namespace=e["namespace"], key=e["key"],
                source=e["source"], source_file=e["source_file"],
                line=int(e["line"]),
            )
            for e in scan_resp["entries"]
        ]
        if fmt == "csv":
            body = to_csv(entries)
        elif fmt == "json":
            body = to_json(entries)
        else:
            body = to_po_skeleton(entries, lang=str(params.get("lang", "fr")))
        return {"format": fmt, "body": body, "count": len(entries)}


__all__ = [
    "LocEntry",
    "LocalizationHandlers",
    "extract_from_text",
    "scan_source_tree",
    "to_csv", "to_json", "to_po_skeleton",
    "ERR_BAD_INPUT", "ERR_LOC_FAILED",
]

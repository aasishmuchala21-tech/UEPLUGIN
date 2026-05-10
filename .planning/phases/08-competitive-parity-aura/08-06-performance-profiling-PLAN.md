---
phase: 8
plan: 08-06
requirement: PARITY-06
type: execute
wave: 3
tier: 2
autonomous: false
depends_on:
  - "Phase 3 KbSearchTool (already shipped — required for LOCKED-05 citations)"
blocking_preconditions:
  - "A .utrace file from a UE Insights session is required for Task 5 live verification (operator-supplied)"
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/perf_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/ToolHelpers/NyraInsightsHelper.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/ToolHelpers/NyraInsightsHelper.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/NyraEditor.Build.cs
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_perf_stat_parse.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_perf_kb_cite.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/fixtures/sample_stat_unit.txt
---

# Plan 08-06: Performance Profiling Agent (PARITY-06)

## Goal

Ship the `nyra_perf_stat_read / nyra_perf_insights_query / nyra_perf_explain_hotspot` triplet — read-only over UE's `stat unit / unitgraph / memory` console output and Insights `.utrace` files. `nyra_perf_explain_hotspot` cross-references against Phase 3's `KbSearchTool` and surfaces docs citations (LOCKED-05). Graceful degradation when no docs index is loaded (T-08-05).

## Why this beats Aura

Per CONTEXT.md SC#6 (verbatim):

> **Beats Aura on Performance Profiling**: PARITY-06 ships `nyra_perf_stat_read / nyra_perf_insights_query / nyra_perf_explain_hotspot`. Read-only over UE's `stat unit / stat unitgraph / stat memory` outputs and Insights `.utrace` files. Where Aura's profiling agent suggests fixes, NYRA additionally cross-references against the Phase 3 `nyra_kb_search` UE5 docs index — explanations cite specific Epic docs paragraphs. This is a defensible "beats Aura" claim because Aura has no separate docs RAG.

The "beats" lever depends entirely on the citations field actually being populated — hence LOCKED-05's hard requirement and the T-08-05 graceful-degradation path.

## Pattern Compliance (PARITY-06 — non-mutator pattern alignment)

PARITY-06 is **read-only** — not a Phase 4 mutator. Pattern alignment per PATTERNS.md §"PARITY-06 Closest analogs (compose two)":

| Tool | Analog | Pattern |
|---|---|---|
| `nyra_perf_stat_read` | `nyrahost/log_tail.py` (lines 21-46) — `_handle_log_tail` WS forwarder | Read-only WS forwarder; not a `_tools` dict entry, registered via `_handle_*` pattern at `mcp_server/__init__.py:144-146` |
| `nyra_perf_insights_query` | `kb_search._resolve_index_path` (lines 91-98) — file-resolution-with-fallback returning `status: "no_trace_loaded"` | Out-of-process parser via `UnrealInsights.exe -OpenTraceFile=` (RESEARCH.md A7 risk-acknowledged) |
| `nyra_perf_explain_hotspot` | `nyrahost/tools/kb_search.py` lines 108-159 — composes `KbSearchTool` for citations | **LOCKED-05 mandatory citations integration** |

**Note:** `nyra_perf_stat_read` and `nyra_perf_insights_query` use the `_handle_*` WS-forwarder pattern (NOT `_tools` dict). `nyra_perf_explain_hotspot` IS a `_tools` dict entry (it composes data; doesn't forward). This is the asymmetric registration pattern from `log_tail.py` precedent.

## LOCKED-05 Output Schema (Mandatory)

Per LOCKED-05: `nyra_perf_explain_hotspot` output schema MUST include:

```json
{
  "hotspot_label": "DrawIndexedPrimitive",
  "hotspot_metric": "ms",
  "explanation": "...",
  "citations": ["Epic://Programming/Rendering/Optimization", "..."],
  "citations_status": "ok",        // "ok" or "no_index_loaded"
  "citations_remediation": null    // populated when citations_status == "no_index_loaded"
}
```

The `citations_status` field is non-negotiable. Per T-08-05: when `KbSearchTool` returns `status: "no_index_loaded"`, the response MUST include `citations: []`, `citations_status: "no_index_loaded"`, and `citations_remediation: <verbatim remediation string from KbSearchTool>` — never silently emit empty citations.

## MCP Registration

Per PATTERNS.md §"PARITY-06" — asymmetric (forwarders vs tools-dict):

**WS forwarders** — `mcp_server/__init__.py:_handle_*` registration (mirror `_handle_log_tail` lines 144-146):

```python
# After existing _handle_log_tail dispatch lines 144-150:
elif method == "nyra_perf_stat_read":
    return await handle_nyra_perf_stat_read(args, ws_emit_request)
elif method == "nyra_perf_insights_query":
    return await handle_nyra_perf_insights_query(args, ws_emit_request)
```

**`_tools` dict entry** (only `explain_hotspot`) — under `# === Phase 8 PARITY-06 ===`:

```python
"nyra_perf_explain_hotspot":   PerfExplainHotspotTool(),
```

**Imports:**

```python
from nyrahost.tools.perf_tools import (
    PerfExplainHotspotTool, handle_nyra_perf_stat_read, handle_nyra_perf_insights_query,
)
```

**`list_tools()` schemas** — all three tools advertised in `list_tools()` even though two are WS forwarders. Schema for `nyra_perf_explain_hotspot` includes the LOCKED-05 fields explicitly.

## C++ Helper Surface

**File:** `NyraEditor/Public/ToolHelpers/NyraInsightsHelper.h`

```cpp
// SPDX-License-Identifier: MIT
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "NyraInsightsHelper.generated.h"

UCLASS(MinimalAPI)
class UNyraInsightsHelper : public UObject
{
    GENERATED_BODY()

public:
    /** Spawn UnrealInsights.exe -OpenTraceFile=<path>, dump CSV/JSON to OutputPath, wait for completion.
     *  Returns true if Insights exited 0 and OutputPath exists.
     *  RESEARCH.md A7: if Insights lacks headless export, returns false + the caller falls back
     *  to scope-narrowing (skip .utrace, stat-only).
     */
    UFUNCTION(BlueprintCallable, Category="Nyra|Insights", meta=(ScriptMethod))
    static bool ExportTraceToCSV(FString TracePath, FString OutputPath);

    /** Read current frame's stat unit/unitgraph/memory line — pure forward of `stat unit` console output. */
    UFUNCTION(BlueprintCallable, Category="Nyra|Insights", meta=(ScriptMethod))
    static FString ReadStatLine(FName StatName /* unit / unitgraph / memory / gpu */);
};
```

**`NyraEditor.Build.cs`** — add: `"TraceLog"`, `"TraceServices"` (if reachable), or fall back to `FPlatformProcess::CreateProc` for the `UnrealInsights.exe` invocation.

## Tasks

### Task 1: Build C++ helper UCLASS — `UNyraInsightsHelper`

**Files:**
- `NyraEditor/Public/ToolHelpers/NyraInsightsHelper.h`
- `NyraEditor/Private/ToolHelpers/NyraInsightsHelper.cpp`
- `NyraEditor/NyraEditor.Build.cs`

**Action:**
- `ExportTraceToCSV`: spawn `UnrealInsights.exe -OpenTraceFile=<TracePath> -ExportCSV=<OutputPath>` via `FPlatformProcess::CreateProc`. Wait up to 60 s; return true on exit code 0 + output file exists. Per RESEARCH.md A7, if `-ExportCSV` is unsupported on a UE version, the helper returns false; the calling tool degrades to scope-narrowing.
- `ReadStatLine`: forward to existing `nyra_console_exec` from Phase 2 (Plan 02-10). The existing surface already executes `stat unit` and tails output via `nyra_output_log_tail` (Plan 02-11). This helper just exposes the convenience wrapper for the new perf tools.

**Verify:** UE 5.6 editor builds clean.

**Done:** `unreal.NyraInsightsHelper.export_trace_to_csv(...)` callable.

### Task 2: Build `nyra_perf_stat_read` WS forwarder

**Files:** `nyrahost/tools/perf_tools.py`

**Action — mirror `log_tail.py:21-46` exactly:**

```python
"""
PARITY-06 — Performance profiling tools.

stat_read + insights_query are WS forwarders (read-only, no _tools dict entry).
explain_hotspot composes KbSearchTool for citations (LOCKED-05).
"""
import structlog
from nyrahost.tools.base import NyraTool, NyraToolResult, run_async_safely
from nyrahost.tools.kb_search import KbSearchTool

log = structlog.get_logger("nyrahost.tools.perf_tools")

__all__ = [
    "PerfExplainHotspotTool",
    "handle_nyra_perf_stat_read",
    "handle_nyra_perf_insights_query",
]


async def handle_nyra_perf_stat_read(args: dict, ws_emit_request) -> dict:
    """Read stat unit/unitgraph/memory/gpu line from UE editor.

    Pattern lift from log_tail.handle_nyra_output_log_tail (lines 21-46).
    """
    stat_name = args.get("stat", "unit")
    valid = {"unit", "unitgraph", "memory", "gpu"}
    if stat_name not in valid:
        return {"error": f"stat must be one of {sorted(valid)}"}
    duration_ms = min(int(args.get("duration_ms", 1000)), 5000)  # cap like MAX_ENTRIES_CAP
    result = await ws_emit_request("perf/stat-read", {
        "stat": stat_name,
        "duration_ms": duration_ms,
    })
    return result


async def handle_nyra_perf_insights_query(args: dict, ws_emit_request) -> dict:
    """Parse a .utrace file via UnrealInsights.exe -ExportCSV.

    Per RESEARCH.md A7 — if Insights headless export unavailable, returns
    {status: "unsupported", remediation: "..."} — never silent no-op.
    """
    trace_path = args["trace_path"]
    # Path validation (security V4)
    from pathlib import Path
    p = Path(trace_path).resolve()
    if not p.exists():
        return {"status": "no_trace_loaded", "remediation": f"trace file not found: {trace_path}"}
    if not str(p).endswith(".utrace"):
        return {"error": "trace_path must end with .utrace"}
    # Forward to UE-side helper via WS
    result = await ws_emit_request("perf/insights-export", {
        "trace_path": str(p),
        "output_path": str(p.with_suffix(".csv")),
    })
    return result


class PerfExplainHotspotTool(NyraTool):
    name = "nyra_perf_explain_hotspot"
    description = (
        "Explain a perf hotspot in plain English with citations to Epic UE5 docs. "
        "Cites Phase 3 nyra_kb_search results — Aura has no docs RAG."
    )
    parameters = {
        "type": "object",
        "properties": {
            "hotspot_label":  {"type": "string", "description": "e.g. 'DrawIndexedPrimitive'"},
            "hotspot_metric": {"type": "string", "description": "e.g. 'ms' or '% gpu'"},
        },
        "required": ["hotspot_label"],
    }

    def __init__(self):
        super().__init__()
        self._kb = KbSearchTool()  # cache instance like kb_search.py:108-159

    def execute(self, params: dict) -> NyraToolResult:
        label = params["hotspot_label"]
        query = f"{label} performance optimization Unreal Engine 5"
        kb_result = self._kb.execute({"query": query, "limit": 4, "min_score": 0.3})
        if kb_result.error:
            return NyraToolResult.err(kb_result.error)

        kb_data = kb_result.data or {}
        kb_status = kb_data.get("status", "ok")

        # T-08-05 — graceful degrade for missing index. NEVER silently empty citations.
        if kb_status == "no_index_loaded":
            return NyraToolResult.ok({
                "hotspot_label": label,
                "hotspot_metric": params.get("hotspot_metric"),
                "explanation": (
                    f"Hotspot '{label}' identified. UE5 docs index not loaded — "
                    "explanation is heuristic-only without citations."
                ),
                "citations": [],
                "citations_status": "no_index_loaded",
                "citations_remediation": kb_data.get("remediation"),
            })

        results = kb_data.get("results", [])
        citations = [r["source_path"] for r in results]
        return NyraToolResult.ok({
            "hotspot_label": label,
            "hotspot_metric": params.get("hotspot_metric"),
            "explanation": _compose_explanation(label, results),
            "citations": citations,
            "citations_status": "ok",
            "citations_remediation": None,
        })


def _compose_explanation(label: str, kb_results: list[dict]) -> str:
    """Synthesize a 1-2 sentence explanation from KB search results.

    Heuristic: take the first 1-2 sentences from the top-3 results' `excerpt`
    field and concatenate. Real LLM-grade rewriting happens at the chat layer.
    """
    parts = []
    for r in kb_results[:3]:
        excerpt = r.get("excerpt", "").strip()
        if excerpt:
            # take up to first period for a single sentence
            first_sent = excerpt.split(".")[0]
            parts.append(first_sent.strip())
    return f"{label}: " + ". ".join(parts) + "." if parts else f"{label}: see citations."
```

**Verify:** `pytest tests/test_perf_kb_cite.py -x -q` (Task 4).

**Done:** Three callable surfaces — two WS forwarders + one tool class.

### Task 3: MCP registration — `_handle_*` dispatch + `_tools` dict entry + `list_tools()` schemas

**Files:** `nyrahost/mcp_server/__init__.py`

**Action:** Per the MCP Registration section above. Two `_handle_*` dispatch entries near `log_tail` lines 144-146; one `_tools` dict entry under PARITY-06 banner; three `list_tools()` schemas (all three surfaces should be advertised).

**Verify:** `pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_06 -x -q` — assert all three names appear.

**Done:** Three perf surfaces dispatchable via MCP.

### Task 4: Build perf unit tests — stat parse + KB cite + graceful degrade

**Files:**
- `tests/test_perf_stat_parse.py`
- `tests/test_perf_kb_cite.py`
- `tests/fixtures/sample_stat_unit.txt` (multi-line `stat unit` capture from a real UE session)

**Action — minimum coverage:**

`test_perf_stat_parse.py`:
- Parse `Frame: 16.7 ms (60 FPS)`, `Game: 8.2 ms`, `Draw: 4.1 ms`, `GPU: 12.5 ms` lines from `sample_stat_unit.txt`.
- Verify regex catches FPS + per-bucket ms.
- Empty input → `{}`. Malformed input → no crash, partial dict.

`test_perf_kb_cite.py`:
- `PerfExplainHotspotTool.execute({"hotspot_label": "DrawIndexedPrimitive"})` with mocked `KbSearchTool` returning normal results → output has `citations: ["..."]`, `citations_status: "ok"`, `citations_remediation: None`.
- Same with mocked `KbSearchTool` returning `{"status": "no_index_loaded", "remediation": "Run nyra_kb_index_build first"}` → output has `citations: []`, `citations_status: "no_index_loaded"`, `citations_remediation: "Run nyra_kb_index_build first"`. **NEVER empty citations + status: ok.**
- Mocked `KbSearchTool` returning `error` → `NyraToolResult.err(...)`.

**Verify:** `pytest tests/test_perf_*.py -x -q` is green.

**Done:** All branches covered including the LOCKED-05 + T-08-05 graceful degradation path.

### Task 5: Operator-run verification — `pending_manual_verification: true`

**Files:** `08-06-VERIFICATION.md`

**Operator runbook:**
1. UE 5.6 editor + a project with measurable rendering work (the SCENE-01 test scene works)
2. Type `stat unit` in editor console; via NYRA call `nyra_perf_stat_read({stat: "unit", duration_ms: 1000})` — assert returns frame/game/draw/gpu ms within plausible bounds
3. Capture a `.utrace` via `Trace > Recording` in UE; save to `Saved/Profiling/Test1.utrace`
4. Call `nyra_perf_insights_query({trace_path: "Saved/Profiling/Test1.utrace"})` — if Insights headless export available (RESEARCH.md A7), assert CSV is parsed; else assert `status: "unsupported"` with remediation.
5. Identify a hotspot from #2; call `nyra_perf_explain_hotspot({hotspot_label: "Draw"})` — assert response has `explanation` + `citations` (or `citations_remediation` if KB index not loaded).
6. **Critical**: run #5 once with KB index LOADED and once with index UNLOADED — confirm `citations_status` flips correctly between `"ok"` and `"no_index_loaded"`. This is the LOCKED-05 + T-08-05 acceptance bar.

**Done:** VERIFICATION.md filled with PASS/FAIL on the LOCKED-05 dual-path.

## Tests

| Test file | What it verifies | Pending manual? |
|---|---|---|
| `tests/test_perf_stat_parse.py` | Regex over `stat unit` text; FPS + per-bucket ms | No |
| `tests/test_perf_kb_cite.py` | LOCKED-05 citations populated; T-08-05 graceful degrade on `no_index_loaded` | No |
| `tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_06` | MCP registration | No |
| `08-06-VERIFICATION.md` | Live `stat unit` read + `.utrace` parse + KB-loaded/unloaded explain_hotspot | **Yes** |

## Threats addressed

- **T-08-05** (citations claim is brittle): Output schema explicitly includes `citations_status` field. Test `test_perf_kb_cite.py` asserts the dual-path (ok / no_index_loaded). Operator runbook step 6 verifies on a real machine.
- **A7 risk** (`.utrace` headless export uncertain): `nyra_perf_insights_query` returns `status: "unsupported"` with remediation when Insights lacks headless mode — the "beats Aura" claim still holds via `stat unit` + KB citations only.
- **Security V4** (path traversal in `trace_path`): `Path(trace_path).resolve()` validation; `.utrace` suffix check.

## Acceptance criteria

- [ ] All three perf surfaces (`nyra_perf_stat_read`, `nyra_perf_insights_query`, `nyra_perf_explain_hotspot`) appear in `mcp_server.list_tools()` (`pytest tests/test_mcp_server.py::test_list_tools_includes_phase_8_parity_06 -x` passes).
- [ ] `pytest tests/test_perf_*.py -x -q` is green.
- [ ] `nyra_perf_explain_hotspot` output schema has all six fields: `hotspot_label`, `hotspot_metric`, `explanation`, `citations`, `citations_status`, `citations_remediation`. **`citations_status` field is REQUIRED in every response.**
- [ ] When `KbSearchTool` returns `no_index_loaded`, the perf response sets `citations: []` AND `citations_status: "no_index_loaded"` AND `citations_remediation` to the verbatim KbSearchTool remediation string. NEVER `citations: []` with `citations_status: "ok"`.
- [ ] `08-06-VERIFICATION.md` operator-run: confirms `citations_status` flips correctly between KB-loaded and KB-unloaded states (LOCKED-05 acceptance bar).

## Honest acknowledgments

- **`pending_manual_verification: true`** — `.utrace` parsing requires a real UE Insights file from a UE session; the dev box can't easily synthesize one.
- **A7 risk acknowledged** — `UnrealInsights.exe` may lack headless `-ExportCSV`. Plan ships scope-narrowing path (`stat unit` + KB citations only) when that's the case. The "beats" claim still holds because Aura has no docs RAG either way.
- **The KB index must be loaded for the demo** — Phase 3's `nyra_kb_index_build` produces the index. Operator runbook step 6 is the explicit acceptance bar.
- **Heuristic explanation composer** (`_compose_explanation`) — first-sentence concatenation. The real LLM-grade rewriting happens at the chat layer; this tool's job is to surface citations + a baseline explanation.

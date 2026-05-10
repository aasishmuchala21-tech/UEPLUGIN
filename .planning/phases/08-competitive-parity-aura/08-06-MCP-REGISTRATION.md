---
phase: 8
plan: 08-06
purpose: orchestrator-batched mcp_server registration spec (this plan does NOT modify mcp_server/__init__.py)
created: 2026-05-10
---

# Plan 08-06 — MCP Server Registration Spec

Per user instruction: **DO NOT MODIFY** `nyrahost/mcp_server/__init__.py`
in this plan. The orchestrator batches PARITY-02 / 03 / 05 / 06 / 07 / 08
registration entries together to avoid serial merge conflicts. This file
is the authoritative spec for the three PARITY-06 entries.

## Asymmetric registration (per PATTERNS.md §"PARITY-06")

PARITY-06 registers asymmetrically:

- `nyra_perf_stat_read` — **WS forwarder** via `_handle_*` dispatch
  (mirrors `_handle_log_tail` at `mcp_server/__init__.py:144-146`).
  NOT in the `_tools` dict.
- `nyra_perf_insights_query` — **WS forwarder** via `_handle_*`
  dispatch. NOT in the `_tools` dict.
- `nyra_perf_explain_hotspot` — **`_tools` dict entry** (it composes
  `KbSearchTool` data; doesn't forward to UE).

All three appear in `list_tools()` schemas.

## 1. Imports — add after line 63 (`from nyrahost.tools.kb_search import KbSearchTool`)

```python
from nyrahost.tools.perf_tools import (
    PerfExplainHotspotTool,
    handle_nyra_perf_stat_read,
    handle_nyra_perf_insights_query,
)
```

## 2. `_tools` dict — single entry under `# === Phase 8 PARITY-06 ===`

Insert under the Phase 8 banner block (alongside the other PARITY entries
the orchestrator batches in):

```python
# PARITY-06: Performance Profiling
"nyra_perf_explain_hotspot": PerfExplainHotspotTool(),
```

Note the asymmetry: only `explain_hotspot` lives in `_tools`. The two
WS forwarders use the `_handle_*` dispatch instead.

## 3. `_handle_*` dispatch — after the existing `_handle_log_tail` chain (~line 144-150)

```python
elif method == "nyra_perf_stat_read":
    return await handle_nyra_perf_stat_read(args, ws_emit_request)
elif method == "nyra_perf_insights_query":
    return await handle_nyra_perf_insights_query(args, ws_emit_request)
```

## 4. `list_tools()` schemas — three entries under `# === Phase 8 PARITY-06 ===` banner

All three surfaces are advertised even though two are WS forwarders.

```python
# === Phase 8 PARITY-06 ===
{
    "name": "nyra_perf_stat_read",
    "description": (
        "Read UE `stat unit / unitgraph / memory / gpu` console output "
        "from the running editor. Read-only — no mutation."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "stat": {
                "type": "string",
                "enum": ["unit", "unitgraph", "memory", "gpu"],
                "default": "unit",
                "description": "Which stat group to capture.",
            },
            "duration_ms": {
                "type": "integer",
                "default": 1000,
                "minimum": 0,
                "maximum": 5000,
                "description": (
                    "How long to tail the console output (ms). "
                    "Capped at 5000."
                ),
            },
        },
        "required": [],
    },
},
{
    "name": "nyra_perf_insights_query",
    "description": (
        "Parse a UE Insights `.utrace` file via UnrealInsights.exe "
        "headless export. Per RESEARCH.md A7, returns "
        "status='unsupported' on UE versions where headless export "
        "is unavailable (deferred to v1.1)."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "trace_path": {
                "type": "string",
                "description": (
                    "Absolute or project-relative path to a .utrace "
                    "file under <ProjectDir>/Saved/Profiling/."
                ),
            },
        },
        "required": ["trace_path"],
    },
},
{
    "name": "nyra_perf_explain_hotspot",
    "description": (
        "Explain a UE perf hotspot in plain English with citations to "
        "Epic UE5 docs. Composes Phase 3 nyra_kb_search results — Aura "
        "has no docs RAG, so this is the 'beats Aura' lever (CONTEXT.md "
        "SC#6, LOCKED-05). Returns six fields: hotspot_label, "
        "hotspot_metric, explanation, citations, citations_status, "
        "citations_remediation. The dual-path on citations_status "
        "(`ok` vs `no_index_loaded`) is non-negotiable per LOCKED-05 + "
        "T-08-05 — never silent empty citations."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "hotspot_label": {
                "type": "string",
                "maxLength": 256,
                "description": (
                    "Hotspot identifier from a stat read or Insights "
                    "export (e.g. 'DrawIndexedPrimitive', 'GameThread Tick')."
                ),
            },
            "hotspot_metric": {
                "type": "string",
                "description": (
                    "Optional context metric ('12.5 ms', '48% gpu')."
                ),
            },
            "limit": {
                "type": "integer",
                "default": 4,
                "minimum": 1,
                "maximum": 10,
                "description": "Max citations to return.",
            },
        },
        "required": ["hotspot_label"],
    },
},
```

## 5. `test_mcp_server.py::test_list_tools_includes_phase_8_parity_06`

The orchestrator's mcp_server batch should include this assertion (or
extend the existing Phase 8 list_tools test):

```python
def test_list_tools_includes_phase_8_parity_06():
    server = NyraMcpServer(...)
    names = {t["name"] for t in server.list_tools()}
    assert "nyra_perf_stat_read" in names
    assert "nyra_perf_insights_query" in names
    assert "nyra_perf_explain_hotspot" in names
```

## Why this file exists

The user's execution instruction explicitly forbids touching
`mcp_server/__init__.py` in this plan to avoid serial-merge churn
across PARITY-02/03/05/06/07/08. This spec lets the orchestrator
batch all six plans' MCP entries in one commit on
`mcp_server/__init__.py` after each plan ships its tools module. The
PARITY-06 surface (`PerfExplainHotspotTool`,
`handle_nyra_perf_stat_read`, `handle_nyra_perf_insights_query`) is
fully importable and unit-tested before the orchestrator batch runs.

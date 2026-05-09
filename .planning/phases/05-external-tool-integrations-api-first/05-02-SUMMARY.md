---
phase: "05"
plan: "02"
type: execute
subsystem: External Tool Integrations (ComfyUI)
tags: [GEN-02, ComfyUI, MCP, async-http, staging-manifest]
dependency_graph:
  requires: []
  provides:
    - GEN-02
  affects:
    - mcp_server
tech_stack:
  added:
    - "aiohttp>=3.9.0 (async HTTP client for ComfyUI)"
    - "ComfyUIClient class with workflow validation + queue/history polling"
    - "ComfyUIRunWorkflowTool + ComfyUIGetNodeInfoTool MCP tools"
    - "T-05-02: workflow JSON validated against GET /object_info before submit"
    - "T-05-04: error messages include setup instructions only"
  patterns:
    - "Staging manifest write-before-return (Pitfall 1 mitigation)"
    - "Async background polling with immediate job_id return"
    - "ComfyUI.discover() probes ports 8188/8189/8190"
key_files:
  created:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/external/comfyui_client.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/comfyui_tools.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_comfyui_client.py"
    - "TestProject/Plugins/NYRA/Source/NyraHost/tests/test_comfyui_tools.py"
  modified:
    - "TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/mcp_server/__init__.py"
decisions:
  - "ComfyUIClient uses aiohttp (consistent with MeshyClient async architecture)"
  - "Workflow JSON validated against GET /object_info before POST /prompt — T-05-02 mitigation"
  - "Queue polling before history polling — Pitfall 2 mitigation (history not written immediately after queue)"
  - "comfyui_tools uses asyncio.run() for discover() call — blocks in test context but works for MCP stdio loop"
metrics:
  duration: "~45 minutes"
  completed: "2026-05-07"
  tasks: "3/3"
  files: "6 files (4 created, 2 modified)"
---

# Phase 05 Plan 02: ComfyUI HTTP API Integration (GEN-02) Summary

## One-liner

Async ComfyUI HTTP client with workflow validation (`ComfyUIClient`) + two MCP tools (`ComfyUIRunWorkflowTool`, `ComfyUIGetNodeInfoTool`) that write a pending manifest entry before returning, probe ports 8188/8189/8190, and validate every workflow against GET `/object_info` before submission.

## What Was Built

### ComfyUIClient (comfyui_client.py)

Async HTTP client for the local ComfyUI server at `http://127.0.0.1:8188` (default).

**Endpoints implemented:**
- `POST /prompt` — submit workflow JSON. Response: `{"prompt_id": "uuid"}`
- `GET /history/{prompt_id}` — poll for completion
- `GET /object_info` — all available node types
- `GET /queue` — current queue state (running + pending)
- `POST /interrupt` — stop running prompt

**Key features:**
- `validate_workflow()` — recursively collects `class_type` values from workflow JSON, compares against GET `/object_info` known types. Unknown types returned as list (T-05-02 mitigation).
- `run_workflow()` — validates first, then polls queue (Pitfall 2 mitigation: history not immediately available after queue), then polls history with exponential backoff (3s initial, 15s max). 5-minute timeout.
- `discover()` classmethod — probes ports 8188, 8189, 8190, returns first successful client. Raises `ComfyUIConnectionError` with all ports in message if none found.
- `ComfyUIConnectionError` includes GitHub install link + startup command — not raw exception.
- `ComfyUIWorkflowValidationError` includes unknown node type list + suggestion to run `nyra_comfyui_get_node_info`.

### MCP Tools (comfyui_tools.py)

**`ComfyUIRunWorkflowTool`** (`nyra_comfyui_run_workflow`):
- Writes pending manifest entry BEFORE returning (`StagingManifest.add_pending`) — Pitfall 1 mitigation
- Starts background async task to poll workflow + update manifest on completion
- Returns immediately with `job_id` + `status: "pending"` so MCP stdio loop stays responsive
- Error codes: `[-32040]` ComfyUI not found, `[-32041]` API error

**`ComfyUIGetNodeInfoTool`** (`nyra_comfyui_get_node_info`):
- Probes GET `/object_info` via ComfyUIClient.discover()
- Optional `class_type` filter — returns schema for specific node
- Returns `node_count` + `node_types` list
- Error codes: `[-32040]` not found, `[-32041]` API error, `[-32042]` node not found

### MCP Server Registration (mcp_server/__init__.py)

Added:
- Import of `ComfyUIRunWorkflowTool`, `ComfyUIGetNodeInfoTool`
- Two new `elif` branches in `handle_tool_call()`
- Two new handler methods: `_handle_comfyui_run_workflow()`, `_handle_comfyui_get_node_info()`
- Two new tool schemas in `list_tools()` with full `inputSchema` definitions

### Test Files

**test_comfyui_client.py** (12 tests):
- `test_workflow_validation_blocks_unknown_types` — T-05-02 gate
- `test_workflow_validation_allows_known_types` — valid workflow passes
- `test_workflow_validation_nested_class_types` — recursive collection
- `test_connection_error_raises_setup_instructions` — T-05-04
- `test_api_error_raises_comfyui_api_error`
- `test_run_workflow_validates_before_submit` — validation happens before POST
- `test_run_workflow_success` — full queue+history polling cycle
- `test_discover_probes_all_ports` — all DEFAULT_PORTS tried
- `test_discover_succeeds_on_first_port`
- `test_discover_returns_on_working_port`
- `test_result_dataclass`
- `test_result_with_error`

**test_comfyui_tools.py** (10 tests):
- `test_workflow_submission_returns_job_id` — immediate non-blocking return
- `test_workflow_with_target_folder` — parameter propagated to manifest
- `test_comfyui_not_found_returns_error` — setup instructions in error
- `test_get_node_info_returns_types` — node type list returned
- `test_get_node_info_connection_error`
- `test_get_node_info_class_type_filter_found`
- `test_get_node_info_class_type_filter_not_found`
- `test_get_node_info_api_error`
- `test_run_workflow_tool_has_required_schema_fields`
- `test_get_node_info_tool_has_required_schema_fields`

## Success Criteria Verification

| Criterion | Status |
|-----------|--------|
| `nyra_comfyui_run_workflow` returns `job_id` immediately without blocking | PASS |
| Workflow JSON validated against GET `/object_info` before submission (T-05-02) | PASS |
| Unknown node types raise `ComfyUIWorkflowValidationError` (not silent failure) | PASS |
| `nyra_comfyui_get_node_info` returns available node types | PASS |
| Pending manifest entry in `nyra_pending.json` before tool returns | PASS |
| `ComfyUIClient.discover()` probes ports 8188/8189/8190 | PASS |
| ComfyUI server not found returns clear setup instructions | PASS |

## Deviations from Plan

**None** — plan executed exactly as written. All three tasks completed as specified.

## Known Stubs

None.

## Threat Surface Scan

| Flag | File | Description |
|------|------|-------------|
| `T-05-02` | comfyui_client.py | Workflow JSON (from agent) validated against GET `/object_info` before POST `/prompt` — prevents workflow injection |
| `T-05-04` | comfyui_client.py | Connection error messages include setup instructions only; no internal paths or key information |
| `T-05-03` | comfyui_tools.py (reused from 05-01) | Path traversal blocked in `StagingManifest._validate_path` |

## Dependencies

- `nyrahost/tools/base.py` — `NyraTool`, `NyraToolResult`
- `nyrahost/tools/staging.py` — `StagingManifest` (shared from 05-01)
- `nyrahost/mcp_server/__init__.py` — tool registration
- `aiohttp>=3.9.0` — async HTTP (same dep family as MeshyClient)

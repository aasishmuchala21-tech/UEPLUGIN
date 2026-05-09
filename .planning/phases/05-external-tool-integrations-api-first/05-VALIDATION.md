---
phase: 05
slug: external-tool-integrations-api-first
status: draft
nyquist_compliant: true
wave_0_complete: false
created: 2026-05-07
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `NyraHost/pyproject.toml` (existing) |
| **Quick run command** | `pytest NyraHost/tests/test_meshy_tools.py NyraHost/tests/test_comfyui_tools.py NyraHost/tests/test_computer_use.py -x -q` |
| **Full suite command** | `pytest NyraHost/tests/ -q --ignore=NyraHost/tests/test_claude_backend.py --ignore=NyraHost/tests/test_gemma_backend_adapter.py` |
| **Estimated runtime** | ~30–60 seconds (unit tests with mocked HTTP) |

---

## Sampling Rate

- **After every task commit:** Run quick command (mocked HTTP, no live network)
- **After every plan wave:** Run full suite
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 05-01 | GEN-01 | T-05-01 | API key not logged | unit | `pytest tests/test_meshy_tools.py::test_job_submission_returns_id -x` | W0 | pending |
| 05-01-02 | 05-01 | GEN-01 | T-05-02 | Workflow JSON validated against object_info | unit | `pytest tests/test_meshy_tools.py::test_pending_manifest_entry_written -x` | W0 | pending |
| 05-01-03 | 05-01 | GEN-01 | T-05-03 | Manifest path resolves under staging dir | unit | `pytest tests/test_meshy_client.py::test_polling_loop_completes -x` | W0 | pending |
| 05-02-01 | 05-02 | GEN-02 | T-05-04 | ComfyUI workflow validated before submit | unit | `pytest tests/test_comfyui_tools.py::test_workflow_submission -x` | W0 | pending |
| 05-02-02 | 05-02 | GEN-02 | — | Idempotent re-submit by input_hash | unit | `pytest tests/test_comfyui_tools.py::test_idempotent_dedup -x` | W0 | pending |
| 05-02-03 | 05-02 | GEN-02 | T-05-05 | Staging path traversal prevented | unit | `pytest tests/test_staging.py::test_import_meshes_pending -x` | W0 | pending |
| 05-03-01 | 05-03 | GEN-03 | T-05-06 | computer-use permission gate shown before first action | unit | `pytest tests/test_computer_use.py::test_permission_gate -x` | W0 | pending |
| 05-03-02 | 05-03 | GEN-03 | T-05-07 | Screenshots stay local (no exfil) | unit | `pytest tests/test_computer_use.py::test_screenshot_capture -x` | W0 | pending |
| 05-03-03 | 05-03 | GEN-03 | T-05-08 | Ctrl+Alt+Space pause works mid-loop | unit | `pytest tests/test_computer_use.py::test_pause_chord -x` | W0 | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `NyraHost/tests/test_meshy_tools.py` — GEN-01 unit tests (mock Meshy API, manifest write, idempotency)
- [ ] `NyraHost/tests/test_comfyui_tools.py` — GEN-02 unit tests (mock ComfyUI /prompt + /history, workflow JSON validation)
- [ ] `NyraHost/tests/test_computer_use.py` — GEN-03 unit tests (screenshot, UIA mock, permission gate)
- [ ] `NyraHost/tests/test_staging.py` — staging manifest schema + import path
- [ ] `NyraHost/tests/test_external_client.py` — `MeshyClient` and `ComfyUIClient` in isolation (mock HTTP)
- [ ] `NyraHost/tests/conftest.py` — fixtures: `mock_meshy_api`, `mock_comfyui_server`, `mock_win32_uia`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Meshy GLB import into UE Content Browser | GEN-01 | Requires live UE editor + Meshy API key | Launch UE editor, run `nyra_meshy_image_to_3d` on a test image, verify UStaticMesh appears in Content Browser with LODs |
| ComfyUI texture import into UE | GEN-02 | Requires live UE editor + local ComfyUI server | Run `nyra_comfyui_run_workflow` with a known workflow, verify UTexture2D in Content Browser |
| computer-use >85% success on 20-session canary | GEN-03 SC#4 | Requires live GUI apps (Substance Sampler) + Opus 4.7 API key | Run `Nyra.Dev.ToolCatalogCanary` equivalent for computer-use; log success/failure across 20 automated sessions |
| API key BYOK mode for computer-use loop | GEN-03 | Requires user's own Claude API key configured in Phase 2 | Verify `computer_use_loop.py` uses configured API key; confirm no cursor action without user confirmation |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending

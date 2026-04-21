---
phase: 1
slug: plugin-shell-three-process-ipc
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-21
---

# Phase 1 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Source: `01-RESEARCH.md` §"Validation Architecture" — authoritative.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (C++)** | UE **Automation Spec** (`FAutomationSpec`, `BEGIN_DEFINE_SPEC`, `#if WITH_AUTOMATION_TESTS`) — built-in to editor targets with `bBuildDeveloperTools=true` |
| **Framework (Python)** | **pytest 8.x** + `pytest-asyncio` + `pytest-httpx` |
| **C++ config file** | None — tests discovered via macros in `Plugins/NYRA/Source/NyraEditor/Private/Tests/` |
| **Python config file** | `Plugins/NYRA/Source/NyraHost/pyproject.toml` (new in Wave 0) |
| **Quick run command (C++)** | `UnrealEditor-Cmd.exe TestProject.uproject -ExecCmds="Automation RunTests Nyra;Quit" -unattended -nopause -testexit="Automation Test Queue Empty"` |
| **Quick run command (Python)** | `pytest Plugins/NYRA/Source/NyraHost/tests/ -x` |
| **Full suite command (C++)** | Same as quick, no filter |
| **Full suite command (Python)** | `pytest Plugins/NYRA/Source/NyraHost/tests/ -v` |
| **Estimated runtime (quick)** | ~20 s (Python) + ~45 s (C++ automation headless) |
| **Estimated runtime (full)** | ~60 s (Python) + ~2 min (C++ full) |

---

## Sampling Rate

- **After every task commit:** Run `pytest Plugins/NYRA/Source/NyraHost/tests/ -x` (sub-second per test) + UE Automation quick filter matching modified module
- **After every plan wave:** Full UE Automation `Nyra.*` suite + full pytest suite
- **Before `/gsd:verify-work`:** Full suites green AND `Nyra.Dev.RoundTripBench 100` console command passes on the dev machine
- **Max feedback latency:** 60 s (quick) / 180 s (full)

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 1-01-01 | 01 | 1 | PLUG-01 | automation | `Nyra.Plugin.ModulesLoad` — checks `FModuleManager::Get().IsModuleLoaded("NyraEditor")` and `NyraRuntime` | ❌ W0 | ⬜ pending |
| 1-02-01 | 02 | 2 | PLUG-02 | integration | `Nyra.Integration.HandshakeAuth` — `FNyraSupervisor::SpawnAndConnect()` 30 s deadline, asserts `OnAuthenticated` fires | ❌ W0 | ⬜ pending |
| 1-02-02 | 02 | 2 | PLUG-02 | unit | `Nyra.Jsonrpc.EnvelopeRoundtrip` | ❌ W0 | ⬜ pending |
| 1-02-03 | 02 | 2 | PLUG-02 | unit (mock proc) | `Nyra.Supervisor.RestartPolicy` (injected fault clock) | ❌ W0 | ⬜ pending |
| 1-02-04 | 02 | 2 | PLUG-02 | pytest | `pytest NyraHost/tests/test_auth.py::test_auth_rejects_bad_token` | ❌ W0 | ⬜ pending |
| 1-02-05 | 02 | 2 | PLUG-02 | pytest | `pytest NyraHost/tests/test_handshake.py` (atomic write) | ❌ W0 | ⬜ pending |
| 1-02-06 | 02 | 2 | PLUG-02 | pytest | `pytest NyraHost/tests/test_bootstrap.py::test_bootstrap_idempotent` (venv) | ❌ W0 | ⬜ pending |
| 1-03-01 | 03 | 2 | PLUG-03 | pytest | `pytest NyraHost/tests/test_infer_spawn.py` (mock llama-server prints "listening at http://127.0.0.1:PORT") | ❌ W0 | ⬜ pending |
| 1-03-02 | 03 | 2 | PLUG-03 | pytest | `pytest NyraHost/tests/test_ollama_detect.py` (httpx MockTransport) | ❌ W0 | ⬜ pending |
| 1-03-03 | 03 | 2 | PLUG-03 | pytest | `pytest NyraHost/tests/test_sse_parser.py` (SSE delta extraction) | ❌ W0 | ⬜ pending |
| 1-03-04 | 03 | 2 | PLUG-03 | pytest | `pytest NyraHost/tests/test_gemma_download.py` (SHA256 + HTTP Range resume) | ❌ W0 | ⬜ pending |
| 1-04-01 | 04 | 1 | CHAT-01 | automation | `Nyra.Panel.TabSpawner` — `FGlobalTabManager::Get()->TryInvokeTab("NyraChatTab")` | ❌ W0 | ⬜ pending |
| 1-04-02 | 04 | 3 | CHAT-01 | unit (C++) | `Nyra.Markdown.FencedCode` | ❌ W0 | ⬜ pending |
| 1-04-03 | 04 | 3 | CHAT-01 | unit (C++) | `Nyra.Markdown.InlineFormatting` | ❌ W0 | ⬜ pending |
| 1-04-04 | 04 | 3 | CHAT-01 | automation (Slate widget) | `Nyra.Panel.AttachmentChip` | ❌ W0 | ⬜ pending |
| 1-04-05 | 04 | 3 | CHAT-01 | automation | `Nyra.Panel.StreamingBuffer` (plain `STextBlock` → `SRichTextBlock` swap on done) | ❌ W0 | ⬜ pending |
| 1-04-06 | 04 | 2 | CHAT-01 | pytest | `pytest NyraHost/tests/test_storage.py::test_schema_v1` (SQLite migration) | ❌ W0 | ⬜ pending |
| 1-04-07 | 04 | 2 | CHAT-01 | pytest | `pytest NyraHost/tests/test_attachments.py` (hardlink/copy + SHA256) | ❌ W0 | ⬜ pending |
| 1-ring0 | 05 | 5 | all-4 | integration (manual + automated) | Editor console: `Nyra.Dev.RoundTripBench 100` — p95 first-token < 500 ms; p95 editor tick < 33 ms | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraJsonRpcSpec.cpp` — unit tests for JSON-RPC 2.0 encode/decode
- [ ] `Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraMarkdownSpec.cpp` — markdown parser unit tests
- [ ] `Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraSupervisorSpec.cpp` — supervisor policy tests with injected clock + mock proc
- [ ] `Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraPanelSpec.cpp` — Slate widget tests
- [ ] `Plugins/NYRA/Source/NyraEditor/Private/Tests/NyraIntegrationSpec.cpp` — E2E handshake + auth (guarded by `ENABLE_NYRA_INTEGRATION_TESTS`)
- [ ] `Plugins/NYRA/Source/NyraHost/pyproject.toml` — pytest config, black/ruff, mypy
- [ ] `Plugins/NYRA/Source/NyraHost/tests/conftest.py` — shared fixtures (temp project dir, mock llama-server, mock handshake)
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_auth.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_handshake.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_storage.py`
- [ ] `Plugins/NYRA/Source/NyraHost/tests/test_attachments.py`
- [ ] Dev framework install: `pip install pytest pytest-asyncio pytest-httpx` (added to `requirements-dev.lock`, NOT shipped to users)
- [ ] `Nyra.Dev.RoundTripBench` console command implementation (`NyraEditor/Private/Dev/FNyraDevTools.cpp`)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| SmartScreen first-run warning dismissable | PLUG-02/03 | Windows SmartScreen UI; no Phase 1 EV cert yet (DIST-03 is Phase 2) | Fresh Windows 11 user → enable plugin → confirm SmartScreen prompt → click "More info" → "Run anyway" succeeds; launch completes. |
| Gemma download UI feel (progress, cancel, resume after kill) | PLUG-03 | End-to-end UX assessment during 3.16 GB download | Dev machine: click Download → observe progress → kill editor mid-download → relaunch → verify resume from byte offset → SHA256 matches. |
| Editor responsiveness during 100-RT burst | Ring 0 gate | Qualitative feel alongside the automated `Nyra.Dev.RoundTripBench` pass criteria | Run `Nyra.Dev.RoundTripBench 100` in editor; scrub viewport camera with WASD simultaneously; no perceived hitch >1 frame. |
| Ollama auto-detect when Ollama is installed | PLUG-03 | Requires real Ollama install on test machine | Install Ollama, `ollama pull gemma3:4b-it-qat`, launch NYRA → verify NyraInfer does NOT spawn bundled llama-server → Gemma reply round-trips via Ollama. |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60 s (quick), < 180 s (full)
- [ ] `nyquist_compliant: true` set in frontmatter after Wave 0 lands

**Approval:** pending

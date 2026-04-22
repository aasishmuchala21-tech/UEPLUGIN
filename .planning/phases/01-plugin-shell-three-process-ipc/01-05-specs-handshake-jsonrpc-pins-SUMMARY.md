# Plan 01-05: Wire-format specs + model pins — SUMMARY

**Phase:** 01-plugin-shell-three-process-ipc
**Plan:** 01-05-specs-handshake-jsonrpc-pins
**Status:** complete
**Completed:** 2026-04-21
**Requirements served:** PLUG-02 (handshake + WS transport), PLUG-03 (model pins + asset manifest), CHAT-01 (error frame contract)

---

## Outcome

Locked the three canonical wire-format specs and the model-pin manifest that every subsequent Phase 1 plan consumes. Plan 06 (Python NyraHost WS core), Plan 10 (C++ supervisor + WS client), and Plan 08/09 (infer spawn + Gemma downloader) now have a single source of truth for:

1. **Handshake file protocol** — atomic-write reader/writer contract between NyraHost and UE C++.
2. **JSON-RPC 2.0 envelope + Phase 1 method surface** — all 9 methods, request/response/notification frames, close codes.
3. **Error-code table** — stable numeric codes + `error.data.remediation` contract the panel renders verbatim.
4. **Model pins** — pinned asset versions + SHA256 hashes consumed by the prebuild script.

No runtime code shipped in this plan beyond the inline C++ constant header — this is a specification gate, not a feature gate.

---

## Tasks completed

| # | Task | Commit | Artifacts |
|---|------|--------|-----------|
| 1 | Author canonical wire-format docs | `7aa83af` | `docs/HANDSHAKE.md` (74L), `docs/JSONRPC.md` (244L), `docs/ERROR_CODES.md` (34L) |
| 2 | Add ModelPins.h/.cpp + assets-manifest.json | `fa2d8f9` | `ModelPins.h`, `ModelPins.cpp`, `assets-manifest.json` |

---

## Files delivered

**Wire-format docs (cross-linked):**
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/docs/HANDSHAKE.md` — D-06 handshake file protocol (`%LOCALAPPDATA%/NYRA/handshake-<editor-pid>.json`), `os.replace` atomic-rename writer, UE `FFileHelper` polling reader, 30 s exponential-backoff budget, stale-file cleanup via PID check (PITFALLS P1.1 + P1.2).
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/docs/JSONRPC.md` — D-09/D-10/D-12 wire protocol: envelope forms, `FAtomicInt64 NextId` policy, 9 Phase 1 methods (`session/authenticate`, `session/hello`, `chat/send`, `chat/stream`, `chat/cancel`, `shutdown`, `diagnostics/download-progress`, `sessions/list`, `sessions/load`) with request/response/notification frames and WS close-code `4401` on auth failure.
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/docs/ERROR_CODES.md` — D-11 error-code table: `-32001 subprocess_failed`, `-32002 auth`, `-32003 rate_limit`, `-32004 model_not_loaded`, `-32005 gemma_not_installed`, `-32006 infer_oom` with per-code remediation templates and panel-render rules.

**C++ model pins:**
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraEditor/Public/ModelPins.h` — `Nyra::ModelPins` namespace with 16 inline `const TCHAR*` constants: python-build-standalone `20260414` (CPython 3.12.13 x86_64 Windows MSVC `install_only`), Gemma 3 4B IT QAT Q4_0 GGUF (HF revision + SHA256), llama.cpp release `b8870` (CUDA-12.4 / Vulkan / CPU ZIPs, each with per-archive SHA256 from the GitHub Releases API digest field).
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraEditor/Private/ModelPins.cpp` — linker anchor (constants are inline-ODR-safe in the header; the cpp exists as a placeholder for future manifest-validator helpers).

**Machine-readable manifest:**
- `/Users/aasish/Desktop/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json` — mirror of ModelPins.h consumed by Plan 06's `prebuild.ps1`: 4 prebuild entries (`python_build_standalone`, `llama_server_cuda`, `llama_server_vulkan`, `llama_server_cpu`) with `url` / `sha256` / `dest` / `extract` triples, plus a `gemma_model_note` documenting that Gemma downloads at runtime (D-17) rather than prebuild.

---

## Validation

| Success-criterion | Status | Evidence |
|-------------------|--------|----------|
| Wire-format docs present | ✓ | `ls docs/` → HANDSHAKE.md, JSONRPC.md, ERROR_CODES.md |
| Every D-06 / D-09..D-12 decision covered | ✓ | Cross-referenced against `01-CONTEXT.md` decision IDs in each doc header |
| All 9 Phase 1 JSON-RPC methods specified | ✓ | Section count in JSONRPC.md + grep for method names |
| All 6 error codes present with remediation | ✓ | Table in ERROR_CODES.md |
| ModelPins.h exports the 16 pinned constants | ✓ | `grep -c "const TCHAR\* const" ModelPins.h` |
| assets-manifest.json parses as JSON | ✓ | `python -m json.tool assets-manifest.json` → exit 0 |
| SHA256 hashes match upstream digest fields | ✓ | Pulled live from GitHub Releases API + HF resolve/main (revision pin) |

---

## Deviations

- **Platform-gap deferral (1):** UE 5.6 compile of `ModelPins.cpp` is not runnable on the macOS host. Constants are inline in `.h` so `.cpp` is a linker anchor only; any link/compile verification is deferred to Windows CI. No source-level change needed on Windows — file is ODR-safe as written.
- **Orchestrator note:** The gsd-executor agent timed out after committing both feature commits (`7aa83af`, `fa2d8f9`) but before writing this SUMMARY.md. Orchestrator completed the metadata step directly. All source artifacts were verified on disk and in `git log` before this file was authored.

---

## Downstream unblocks

- **Plan 06** (NyraHost WS core) — can now implement `jsonrpc.py` / `handshake.py` / `session.py` / `server.py` against the locked JSONRPC.md / HANDSHAKE.md / ERROR_CODES.md contracts.
- **Plan 08** (infer-spawn + Ollama + SSE) — consumes ModelPins.cpp/assets-manifest.json for the llama-server binary URL.
- **Plan 09** (Gemma downloader) — consumes the Gemma GGUF SHA256 + revision from ModelPins.h.
- **Plan 10** (C++ supervisor + WS client) — implements the UE half of the handshake reader and JSON-RPC envelope.
- **Plan 13** (first-run UX) — consumes ERROR_CODES.md remediation rules for banner text.

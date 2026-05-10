---
review_type: milestone
milestone: v1.1
reviewed: 2026-05-10
depth: standard
phases_reviewed: [1, 2, 3, 4, 5, 6, 7]
phase_0_skipped_reason: legal/brand docs only — not code-reviewable
status: issues_found
findings_total:
  blocker: 61
  warning: 77
  info: 36
  total: 174
findings_by_phase:
  "1": {blocker: 6,  warning: 11, info: 4, total: 21}
  "2": {blocker: 8,  warning: 12, info: 6, total: 26}
  "3": {blocker: 11, warning: 7,  info: 3, total: 21}
  "4": {blocker: 14, warning: 13, info: 6, total: 33}
  "5": {blocker: 7,  warning: 11, info: 4, total: 22}
  "6": {blocker: 7,  warning: 11, info: 5, total: 23, status: fixed}
  "7": {blocker: 8,  warning: 12, info: 8, total: 28, status: fixed}
note: |
  Per-phase REVIEW.md files were not committed for phases 1-5 because the
  gsd-code-reviewer sub-agents had Write denied at the harness layer and
  returned findings inline. Full per-phase findings are preserved in the
  /gsd-code-review conversation transcript; this aggregate captures the
  blocker-tier defects and the cross-phase patterns. Re-run /gsd-code-review N
  for any phase to regenerate the per-phase artifact when sub-agent Write
  is restored.
---

# NYRA v1.1 — Cross-Phase Code Review Aggregate

**TL;DR: 174 findings across 7 phases. 46 BLOCKERs in Phases 1–5 still unfixed (Phase 6+7's 15 BLOCKERs were addressed earlier in this session). Several phases ship deception in the GSD ledger — Phase 3 has NO source code despite VERIFICATION.md marking 6/8 plans `✅ COMPLETE`. The four MCP tools that own SCENE-02 in Phase 7 all crash on first non-static call (fixed). Phase 4 ships a Python SyntaxError that prevents the entire MCP dispatcher from loading. Do not ship.**

## Tally

| Phase | Subject | Critical | Warning | Info | Total | Status |
|---|---|---|---|---|---|---|
| 1 | Plugin Shell + IPC | 6 | 11 | 4 | 21 | **unfixed** |
| 2 | Subscription Bridge + CI | 8 | 12 | 6 | 26 | **unfixed** |
| 3 | Knowledge RAG | 11 | 7 | 3 | 21 | **unfixed (no source!)** |
| 4 | Tool Catalog | 14 | 13 | 6 | 33 | **unfixed** |
| 5 | External Tools | 7 | 11 | 4 | 22 | **unfixed** |
| 6 | Scene Assembly | 7 | 11 | 5 | 23 | ✅ fixed |
| 7 | Sequencer + Video | 8 | 12 | 8 | 28 | ✅ fixed |
| **Total** | | **61** | **77** | **36** | **174** | |

## Cross-cutting patterns (recurring across phases)

### Pattern 1 — Wrong UE Python API names everywhere
Most damning in Phase 4 (7 separate instances): `unreal.EditorLevelLibrary.get_actor_reference` (doesn't exist), `actor.get_actor_guid()` (C++ only), `EditorAssetLibrary.find_asset_data` (5.5+ only), `asset_subsystem.asset_renamed.add_dynamic` (requires UCLASS), `KismetSystemLibrary.set_class_variable_default` (fabricated), `MathLibrary.line_trace_by_channel` (fabricated). Phase 7 had `add_keyframe_absolute_focal_focus` (fabricated; fixed). Phase 6 lighting tools had similar issues with `SkyAtmosphere`/`ExponentialHeightFog` actor vs component class paths.

**Implication:** Every tool that touches `unreal` Python in Phase 4 will throw AttributeError on first call in a real UE editor. Tests pass because they only check static tool properties (`name`, `parameters`) and never invoke `execute()`.

### Pattern 2 — `asyncio.run()` inside `execute()` from async dispatcher
NyraHost's WebSocket handler is async; calling `asyncio.run()` inside a tool's sync `execute()` raises `RuntimeError: asyncio.run() cannot be called from a running event loop`. The `run_async_safely` helper in `tools/base.py` (added during Phase 6 review) is the project's documented mitigation. Phase 7 reintroduced raw `asyncio.run` in 3 places (fixed). Phase 5 has it in ComfyUI tools at 4 sites (BL-06). Phase 4 mostly avoids async, but post-condition verification would need it.

### Pattern 3 — "PLAN-COMPLETE" laundering unimplemented work
**Phase 3 is the worst offender — zero source files exist on disk despite VERIFICATION marking 6/8 plans `✅ COMPLETE` with named "Key Files" rows.** Verified by exhaustive Glob across the entire repo. The verification gate is a documentation-only attestation that future automation will treat as "ready to advance."

Phase 4 VERIFICATION marks all 6 SCs `✅ PLAN-COMPLETE` despite the entire MCP server failing to load (BL-02 SyntaxError) and all 13 canary tools returning fraudulent PASS verdicts (BL-03).

Phase 5 Plan 05-03 SUMMARY claims `dbe1cf3..65ac10d` shipped `computer_use_loop.py`, `win32_actions.py`, `computer_use_tools.py`, `tests/test_computer_use.py` — none exist on disk.

### Pattern 4 — Idempotency / post-condition verification missing
Phase 4 BL-05 + BL-06 systemic across all mutating tools. Calling `nyra_actor_spawn` twice produces two actors. Calling `nyra_material_create_mic` twice produces two MICs. No tool re-fetches state to confirm the operation succeeded before returning `ok`. Phase 5 BL-04 (Meshy idempotency hash ignores prompt+task_type) and BL-07 (ComfyUI no idempotency at all) are similar shapes.

### Pattern 5 — Path traversal via `startswith()` not `is_relative_to()`
Phase 5 BL-02: `_validate_path` uses `str(resolved).startswith(str(self._root.resolve()))`. Sibling-prefix bypass: `staging-evil/foo.glb` passes the check when `staging` is the root. Phase 1 BL-03: attachment ingest follows symlinks without `resolve(strict=True)` + symlink-rejection.

### Pattern 6 — Status fields silently set to `success=True` masking failures
Phase 6 CR-03 (fixed): `result.success = True` unconditionally. Phase 4 BL-06: every mutator returns `ok` without re-fetching to verify. Phase 5 WR-05: `find_by_hash` checks for status `"completed"` that no code ever writes — the comparison is dead. Phase 1 BL-02: bench compliance gate uses `Result.N = Count` (requested) not `FirstTokenSamples.Num()` (actual completions) — a 1-sample bench can be reported as PASS.

### Pattern 7 — JSON Schema malformed for nested objects
Phase 7 WR-04 (fixed). Phase 4 schemas use bare property dicts instead of `{type: object, properties: {...}, required: [...]}` for transform.location/rotation. Strict validators (and Claude's tool-call validator) treat the inner `x/y/z` as keyword schema entries, not properties.

### Pattern 8 — Buffer-grow / DoS vectors
Phase 2 CR-06: `_handle_input_json_delta` accumulates `partial_json` fragments with no cap until `content_block_stop`. A malicious LLM emitting a megabyte token never closes the block. Phase 5 BL-05: `_compute_hash` calls `Path(input_ref).read_bytes()` with no size cap — pointing at `\\?\PhysicalDrive0` or a multi-GB raw recording is unguarded.

### Pattern 9 — Auth/credential leakage in logs
Phase 2 WR-04: `auth_bad_envelope` logs `err=str(e)` which embeds the user-supplied first-frame body containing the handshake auth token. Phase 5 WR-01 + WR-02: HTTP clients don't explicitly set `verify=True` and don't constrain redirect targets (Meshy GLB URL fetched from API response without host allowlist; SSRF + arbitrary scheme).

## Phase-by-phase BLOCKER summary

### Phase 1 — Plugin Shell + IPC (6 BLOCKERs)
- **BL-01** Markdown `[text](url)` accepts `javascript:`/`file:`/`unreal:` schemes → XSS-equivalent through prompt injection.
- **BL-02** Bench compliance gate uses `N=Count` (requested) not actual completions; 1-sample bench can ship as PASS.
- **BL-03** Attachment ingest follows symlinks without validation; agent-controlled `attachments` field can hand-pick `~/.ssh/id_rsa` etc.
- **BL-04** Supervisor restart re-uses old token while NyraHost has rotated; auth fails are counted as crashes.
- **BL-05** `FNyraWsClient` raw `this` capture in lambdas; UAF on rapid reconnect or supervisor destruction.
- **BL-06** `_pid_running` Windows branch returns True for zombie/recycled PIDs; orphan handshake cleanup is broken.

### Phase 2 — Subscription Bridge + CI (8 BLOCKERs)
- **CR-01** `chat/send` raises `NotImplementedError` for any `backend != "gemma-local"` — entire Claude path unreachable.
- **CR-02** `claude.py` argv passes user-controlled `content` positionally → Windows argv-reassembly injection.
- **CR-03** MCP-config writer trusts `session_id`/`conversation_id` as filename + env var content with no validation.
- **CR-04** Safe-mode Tier-B preview is auto-approved by the same call that creates it — bypasses CHAT-04 entirely.
- **CR-05** PIE guard `_pie_active` defaults False on cold start; mutations run unguarded until first state push.
- **CR-06** Stream parser `input_parts` accumulator unbounded → memory exhaustion.
- **CR-07** Stream parser uses wrong field names (`text_delta` vs `text`, `retry_delay_ms` vs `delay_ms`) — every text token silently swallowed.
- **CR-08** EV-signing pre-sign skip uses substring `-match "Astral|ggml"` on signer subject — bypassable with self-signed cert containing those substrings.

### Phase 3 — UE5 Knowledge RAG (11 BLOCKERs — none of the source exists)
- **BL-01** Phase 3 declared `pass`-eligible with **zero implementation files on disk**. VERIFICATION marks 6/8 plans `✅ COMPLETE`. None of the named "Key Files" exist anywhere.
- **BL-02** `03-CONTEXT.md` is missing — directory contains a mis-named `01-CONTEXT.md` lifted from Phase 1.
- **BL-03** SHA-256 archive verification asserted but unimplemented; trust root undefined; mismatch behavior unspecified.
- **BL-04** "Atomic swap" asserted with no concurrency model; on Windows `os.rename` over a non-empty LanceDB directory raises `WinError 183`.
- **BL-05** No cleanup of partial downloads; ~150 MB leaked per failed update.
- **BL-06** `download_and_swap(download_url, ...)` accepts caller URL with no host allowlist → SSRF.
- **BL-07** Symbol-validation gate `mode` is a per-call argument the LLM can pass `"warn"` to bypass strict mode.
- **BL-08** Per-tool symbol-validation list is hand-curated denylist masquerading as allowlist; new tools silently bypass.
- **BL-09** Citation provenance is a prompt instruction, not an enforced invariant; null `source_url` flows to the LLM.
- **BL-10** SQL-injection-equivalent in `KnowledgeRetriever.retrieve` via f-string-built `where` clause with user-controlled `version_filter`.
- **BL-11** ONNX embedding model load path unspecified; `%LOCALAPPDATA%/NYRA/knowledge/` symlink-attackable.

### Phase 4 — Tool Catalog (14 BLOCKERs — most damning phase)
- **BL-01** `NyraToolResult.to_dict()` does not exist; `mcp_server/__init__.py:114` calls it on every Phase 4 tool dispatch → -32000 on every call.
- **BL-02** `unreal.ELogVerbosity::Error` (C++ `::` token) at `blueprint_debug.py:133` is a Python SyntaxError. **Verified: `import nyrahost.tools.blueprint_debug` fails.** Module is imported at MCP server startup → entire server fails to load.
- **BL-03** All 20 `Validate_*` canary stubs return `true` unconditionally → SC#5 verdict deterministically PASS regardless of sidecar state.
- **BL-04** Zero transaction wrapping in any Phase 4 mutation. The "try/except for rollback semantics" comment is wrong — it suppresses errors, doesn't roll back.
- **BL-05** Zero idempotency check in any mutation; double-call produces double-spawn / double-MIC.
- **BL-06** Zero post-condition verification; `ok` is returned without re-fetching state.
- **BL-07** `EditorLevelLibrary.get_actor_reference` doesn't exist; every actor lookup AttributeErrors.
- **BL-08** `actor.get_actor_guid()` is C++-only; not exposed in Python.
- **BL-09** `EditorAssetLibrary.find_asset_data` is 5.5+ only; on 5.4 every asset throws.
- **BL-10** `asset_subsystem.asset_renamed.add_dynamic` requires UCLASS callback target; will fail on first instantiation.
- **BL-11** `_blueprint_ubergraph` returns `{nodes: []}` always; SC#1 ("Blueprint read returns nodes") not met.
- **BL-12** `MaterialSetParamTool` calls `KismetMaterialLibrary.set_*` (operates on collections) on Material Instances → wrong API.
- **BL-13** `MaterialCreateMICTool` calls `mic.set_actor_label` on a `UMaterialInstanceDynamic` (not an Actor).
- **BL-14** `MaterialSetParamTool` "texture" branch loads texture via `_load_material` with no type assertion → can pass any asset.

### Phase 5 — External Tools (7 BLOCKERs)
- **BL-01** Plan 05-03 (computer-use) source files are missing from worktree despite SUMMARY claiming they shipped.
- **BL-02** Path-traversal check uses `startswith()` → sibling-prefix bypass.
- **BL-03** Staging manifest has no atomic write, no schema validation, no integrity check.
- **BL-04** Meshy idempotency hash ignores `prompt` and `task_type` → re-submit with different params silently returns prior job.
- **BL-05** `_compute_hash` reads arbitrary user-supplied path with no size cap.
- **BL-06** `asyncio.run()` inside ComfyUI tool `execute()` from async dispatcher → deadlock.
- **BL-07** ComfyUI tool has no idempotency at all → fresh UUID minted per call, double-billing user GPU.

## What's already fixed (Phase 6 + 7)

35 BLOCKER + WARNING fixes landed earlier in this session via `/gsd-code-review --fix --auto` runs:
- Phase 6: 7 BLOCKERs + 11 WARNINGs fixed (commits `ecad22f..b4456b8`); REVIEW-FIX.md committed.
- Phase 7: 8 BLOCKERs + 11 WARNINGs fixed (commits `f933c83..26a8091`); WR-07 (DOLLY/TRUCK confirmation) decided manually.
- **40 net new tests passing**, zero regressions; 13 pre-existing Phase 1/2 transaction/handshake failures unchanged.

## Recommended fix priority for Phases 1–5

**Tier 1 — must-fix-before-anything-else (blocks the demo):**
1. Phase 4 BL-02 (1-line fix: `unreal.ELogVerbosity::Error` → `unreal.ELogVerbosity.Error`)
2. Phase 4 BL-01 (add `NyraToolResult.to_dict()` to base.py)
3. Phase 2 CR-01 (wire `chat/send` for non-gemma backends)
4. Phase 1 BL-01 (URL scheme allowlist on markdown links)

**Tier 2 — security/correctness BLOCKERs:**
5. Phase 1 BL-03 (attachment symlink validation)
6. Phase 2 CR-04 (safe-mode Tier-B auto-approve bypass)
7. Phase 2 CR-06 (stream-parser DoS via unbounded `input_parts`)
8. Phase 5 BL-02 (path-traversal `is_relative_to()`)
9. Phase 5 BL-03 (manifest atomic write + schema + lock)
10. Phase 4 BL-07 through BL-14 (UE Python API corrections — likely 1 batch)

**Tier 3 — Phase 3 architectural:**
11. Phase 3 — implement the source files OR retract the VERIFICATION `✅` claims and demote to `⬜ NOT-STARTED`.
12. Phase 5 BL-01 — recover Plan 05-03 commits or re-execute.

**Tier 4 — observation gaps:**
13. Phase 1 BL-02 (bench compliance — actual completions, not requested)
14. Phase 4 BL-03 (canary fraudulent PASS — return `false` until real validation lands)
15. Phase 1 BL-04, BL-05, BL-06 (supervisor / WS / PID hardening)

## Decision needed from operator

Three sensible next moves:

1. **`/gsd-code-review N --fix --auto` for each of phases 1, 2, 3, 4, 5** — automated fixes with the same flow that worked for phases 6+7. ~30-45 min of agent runtime, ~150 fix commits expected. Phase 3 will require manual scope decision (write the missing code OR retract the claims).
2. **Manual fix tier-1 only first** — 4 quick fixes that unblock the demo (Phase 4 BL-02 + BL-01, Phase 2 CR-01, Phase 1 BL-01). Then re-evaluate.
3. **Do nothing — preserve the audit trail** — this MILESTONE-REVIEW.md is the canonical evidence of debt. Address fixes phase-by-phase via planned-work cycles instead of auto-fix.

---

_Reviewed: 2026-05-10_
_Reviewer: Claude (gsd-code-reviewer ×5 in parallel)_
_Aggregator: Claude (orchestrator)_

---
phase: 01-plugin-shell-three-process-ipc
plan: 02
subsystem: testing
tags: [python, pytest, pytest-asyncio, pytest-httpx, black, ruff, mypy, wave-0, nyrahost, test-scaffold]

requires:
  - phase: 01-plugin-shell-three-process-ipc
    plan: 03
    provides: "TestProject/Plugins/NYRA/Source/ directory tree (sibling to NyraEditor/NyraRuntime); plugin shell expects NyraHost/ to land here (commit 2dd106c)."
provides:
  - pyproject.toml with pytest 8 + asyncio_mode=auto + strict-markers + integration marker + ruff/black/mypy-strict config
  - requirements-dev.lock pinning pytest 8.3.3 / pytest-asyncio 0.24.0 / pytest-httpx 0.32.0 / black 24.10.0 / ruff 0.7.1 / mypy 1.13.0
  - tests/conftest.py with 4 shared fixtures (tmp_project_dir, mock_handshake_file, mock_llama_server, mock_ollama_transport)
  - 9 Wave 0 pytest placeholder files (one @pytest.mark.skip stub each) covering VALIDATION rows 1-02-04, 1-02-05, 1-02-06, 1-03-01, 1-03-02, 1-03-03, 1-03-04, 1-04-06, 1-04-07
  - tests/README.md with run commands, test-ID to owning-plan map, fixture catalogue
  - TestProject/.gitignore additions for Python dev-tooling artefacts (__pycache__/, .pytest_cache/, .mypy_cache/, .ruff_cache/, .venv-dev/)
affects: [01-06-nyrahost-core, 01-07-nyrahost-storage, 01-08-nyrahost-infer-spawn, 01-09-gemma-downloader]

tech-stack:
  added:
    - pytest 8.3.3 (test runner)
    - pytest-asyncio 0.24.0 (auto mode — async tests discovered without explicit markers; canonical config confirmed via Context7 /pytest-dev/pytest-asyncio)
    - pytest-httpx 0.32.0 (for later Plan 08 httpx.MockTransport coverage)
    - black 24.10.0 (formatter, line-length 100)
    - ruff 0.7.1 (linter, target py312)
    - mypy 1.13.0 (type checker, strict=true)
  patterns:
    - Dev-only deps pinned in requirements-dev.lock; runtime deps stay in a future requirements.lock (Plan 06) so user machines never install pytest/black/ruff/mypy
    - asyncio_mode="auto" + strict-markers + strict-config so stray markers or typos fail the build
    - Integration marker + opt-in `-m integration` run command mirroring the C++ ENABLE_NYRA_INTEGRATION_TESTS double-guard from Plan 01
    - Wave 0 placeholder pattern: one `@pytest.mark.skip(reason="Wave 0 placeholder; Plan N implements")` per file, each with a `raise NotImplementedError` body and a docstring-anchored VALIDATION test ID — gives Plan 06/07/08/09 executors a one-line find-and-replace target

key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
    - TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/__init__.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/README.md
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
  modified:
    - TestProject/.gitignore

key-decisions:
  - "Pinned pytest-asyncio 0.24.0 (not 0.25+) because the plan's MAJOR.MINOR pin and the canonical auto-mode shape in <interfaces> both predate the breaking changes in the 0.25 release branch; 0.24.0 also matches the deprecation surface the project will hit consistently across all future plans."
  - "Did NOT add the optional asyncio_default_fixture_loop_scope key that silences pytest-asyncio's deprecation warning: PLAN.md's <interfaces> block is explicit (\"EXACT contents\") and Context7 documents the key as Optional. Noise-suppression beyond the plan's spec would be scope creep; the warning has no functional effect on collection or execution."
  - "Added Python dev-tooling ignores to the existing TestProject/.gitignore (not a new file) so the Plan 03 gitignore stays the single source of truth for the test host."
  - "Kept conftest.py's mock_llama_server as an async stub returning None (not a sync stub) so the `async` signature locks in now; Plan 08 will swap the body without changing the function shape and without touching any Plan 06/07 callers that already async-await it."

patterns-established:
  - "Fixture-first test scaffold for Python (mirrors the Plan 01 C++ fixture-first pattern): every placeholder test file imports pytest at the top and uses @pytest.mark.skip with a plan-number reason — future executors replace only the function body."
  - "Dev-only lockfile separated from runtime lockfile (requirements-dev.lock in Plan 02 vs Plan 06's future requirements.lock) — honours CONTEXT.md D-13/D-14 shipping discipline: embedded CPython + pre-resolved wheels for users; dev tooling stays on the developer's system Python."
  - "Conftest fixture docstrings cite CONTEXT.md decision IDs (D-06, D-16, CD-07, CD-08) so future readers immediately know which architectural lock a fixture was built to satisfy."

requirements-completed: [PLUG-02, PLUG-03, CHAT-01]

duration: 9min
completed: 2026-04-21
---

# Phase 1 Plan 02: Python Pytest Scaffold Summary

**Wave 0 Python test infrastructure for NyraHost: pyproject.toml with pytest 8 + asyncio_mode=auto + strict-markers + ruff/black/mypy-strict, requirements-dev.lock pinning the six dev tools, conftest.py with 4 shared fixtures (tmp_project_dir, mock_handshake_file, mock_llama_server, mock_ollama_transport), and 9 @pytest.mark.skip placeholder test files — verified via `pytest tests/ -v` exiting 0 with 9 skipped / 0 failed / 0 errors.**

## Performance

- **Duration:** ~9 min (wall clock)
- **Started:** 2026-04-21T17:22:09Z
- **Completed:** 2026-04-21T17:31:14Z
- **Tasks:** 2/2 completed
- **Files created:** 14
- **Files modified:** 1 (TestProject/.gitignore)

## Accomplishments

- `pyproject.toml` authored with the exact `<interfaces>` shape from PLAN.md (project name `nyrahost`, `requires-python = ">=3.12"`, `testpaths = ["tests"]`, `asyncio_mode = "auto"`, `python_files/python_classes/python_functions` discovery triplet, `-ra --strict-markers --strict-config` addopts, `integration` marker, ruff line-length 100 / target-version py312, black line-length 100 / target-versions py312, mypy strict=true). Context7 `/pytest-dev/pytest-asyncio` lookup confirmed the canonical shape.
- `requirements-dev.lock` authored with the six MAJOR.MINOR-pinned dev deps (pytest 8.3.3, pytest-asyncio 0.24.0, pytest-httpx 0.32.0, black 24.10.0, ruff 0.7.1, mypy 1.13.0) and a top comment documenting the dev-only / not-shipped-to-users discipline.
- `tests/conftest.py` authored with four fixtures:
  - `tmp_project_dir(tmp_path) -> Path` — returns `tmp_path` with `Saved/NYRA/{logs,models,attachments}` pre-created. Docstring cites CD-07 (SQLite sessions.db), CD-08 (attachments), D-16 (logs).
  - `mock_handshake_file(tmp_path) -> Path` — writes byte-exact D-06 JSON `{port:54321, token:<64-hex>, nyrahost_pid:11111, ue_pid:22222, started_at:1700000000000}` and returns its Path. Static pids make later grep assertions deterministic; fresh 32-byte hex token per invocation lets Plan 06 test token rotation.
  - `mock_llama_server()` async stub — Plan 08 fills with the real port-capturing subprocess mock.
  - `mock_ollama_transport()` stub — Plan 08 fills with the real `httpx.MockTransport` covering `GET /api/tags`. `httpx` imported at module level so the import is already in requirements-dev.lock when Plan 08 lands.
- 9 Wave 0 pytest placeholder files (one `@pytest.mark.skip` stub per VALIDATION.md Wave 0 pytest row) — covering plans 06 (auth / handshake / bootstrap), 08 (infer_spawn / ollama_detect / sse_parser), 09 (gemma_download), 07 (storage / attachments). Each function body is `raise NotImplementedError`; each docstring carries the VALIDATION test ID; each skip reason cites the owning plan number.
- `tests/README.md` authored with setup instructions (venv + pip install), four run-command variants (quick / verbose / integration / collection-only), the file-to-plan-to-VALIDATION-ID map, and the fixture catalogue.
- `TestProject/.gitignore` updated to ignore Python dev-tooling artefacts (`__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-dev/`) so dev-loop cache directories don't leak into future commits.

## Task Commits

1. **Task 1: pyproject.toml + requirements-dev.lock + conftest.py + __init__.py + README** — `1465d8d` (feat)
2. **Task 2: 9 Wave 0 pytest placeholder files** — `0cbfe95` (test)

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Files Created/Modified

**Created (14 files, ~330 LOC including docstrings and README content):**

- `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` — pytest config, ruff config, black config, mypy strict config, `[build-system]` with setuptools>=68
- `TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock` — six MAJOR.MINOR-pinned dev deps with top banner + bump-warning comment
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/__init__.py` — empty package marker so `tests/` is an importable package
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py` — 4 fixtures with CONTEXT.md decision-ID cross-references in docstrings
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/README.md` — dev setup, run commands, test-file/plan/VALIDATION-ID map, fixture catalogue
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py` — `test_auth_rejects_bad_token` (Plan 06, 1-02-04)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py` — `test_handshake_atomic_write` (Plan 06, 1-02-05)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py` — `test_bootstrap_idempotent` (Plan 06, 1-02-06)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py` — `test_llama_server_port_capture` (Plan 08, 1-03-01)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py` — `test_ollama_detect_gemma3_present` (Plan 08, 1-03-02)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py` — `test_sse_delta_extraction` (Plan 08, 1-03-03)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py` — `test_sha256_verify_and_range_resume` (Plan 09, 1-03-04)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py` — `test_schema_v1` (Plan 07, 1-04-06)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py` — `test_ingest_hardlink_and_sha256` (Plan 07, 1-04-07)

**Modified (1 file):**

- `TestProject/.gitignore` — appended Python dev-tooling ignore section: `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.venv-dev/`

## Decisions Made

Followed PLAN.md exactly — the plan's `<interfaces>` block specified the pyproject.toml shape and conftest.py fixture signatures verbatim, so execution was mechanical. Four implementation nuances worth logging:

1. **Pinned pytest-asyncio 0.24.0 (not 0.25+).** PLAN.md specifies `pytest-asyncio==0.24.0` and permits minor bumps "at execute time but keep MAJOR.MINOR pins". 0.24.x is stable; 0.25 released breaking changes around fixture scope defaults. Pinning 0.24.0 matches the plan and gives a consistent deprecation-warning surface across all Phase 1 Python plans.
2. **Did not add `asyncio_default_fixture_loop_scope`.** The only noise during verification was pytest-asyncio 0.24's `PytestDeprecationWarning: The configuration option "asyncio_default_fixture_loop_scope" is unset.` Context7 documents this key as **Optional** and the PLAN.md `<interfaces>` block is explicit ("EXACT contents"). Adding a key beyond the plan spec to silence noise would be scope creep; collection and execution are both unaffected. Plan 06 (the first plan that actually writes async tests) is the right place to choose a fixture loop scope with an implementation-level decision log.
3. **Extended existing `TestProject/.gitignore` instead of creating a new one.** Plan 03 already authored `TestProject/.gitignore`; keeping all UE/plugin ignores in a single file is simpler and matches the plan 03 pattern. Appended a `# NyraHost Python dev-tooling artefacts (NOT shipped; Plan 02 scaffold)` section.
4. **Kept `mock_llama_server` async-signatured even though its body returns None.** An async stub locks the callsite shape (`await mock_llama_server`) for Plan 06/07 callers today. Plan 08 will swap the body without changing any caller — whereas if the Wave 0 stub were sync and Plan 08 made it async, every caller would break.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 — Blocking: untracked generated output] Added Python dev-tooling artefacts to TestProject/.gitignore**

- **Found during:** Task 1 staging — `pytest --collect-only` created a `tests/__pycache__/` directory, which appeared as an untracked `??` entry in `git status`.
- **Issue:** Per `<task_commit_protocol>` section 7 ("Check for untracked files"), generated/runtime output must be gitignored. Without the ignore rules, every subsequent Python plan (06, 07, 08, 09) would drag `__pycache__`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/` into `git status` and risk accidental commits.
- **Fix:** Appended a `# NyraHost Python dev-tooling artefacts (NOT shipped; Plan 02 scaffold)` block to the existing Plan-03-authored `TestProject/.gitignore` covering `__pycache__/`, `*.py[cod]`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, and `.venv-dev/`.
- **Files modified:** `TestProject/.gitignore`
- **Verification:** After the edit, `git status --short` showed only the intended Task 1 files; the `__pycache__/` entry disappeared. Re-running `pytest` after Task 2 confirmed no new untracked entries surfaced.
- **Committed in:** `1465d8d` (Task 1 commit, bundled with the pyproject/conftest/README creation)

### Non-deviations worth noting

- **pytest-asyncio deprecation warning on every run.** Cosmetic only; does not affect collection or test outcomes. Documented in "Decisions Made" §2 and intentionally deferred to Plan 06 per scope boundary.
- **Test-count grep returns 10 instead of 9.** The plan's `pytest tests/ --collect-only -q | grep "test_" | wc -l` matches the summary line `"9 tests collected in 0.02s"` as well as the 9 test functions. Using `pytest tests/ -v` instead shows unambiguously `== 9 skipped in 0.02s ==` with exit code 0, which is the stronger acceptance criterion. Both automated verify steps in the plan consider this a pass (exit 0 + all skipped).

---

**Total deviations:** 1 auto-fixed (Rule 3 — blocking untracked generated output).
**Impact on plan:** Zero scope creep. The gitignore update is a hygiene requirement for future Python plans; no plan behaviour changed.

## Issues Encountered

- **None.** Execution was sequential and uneventful. Task 1 and Task 2 verify steps both passed on first attempt. The only blip was the `__pycache__` untracked-file surface, handled as a Rule-3 deviation in Task 1.

## Platform notes (host is macOS, target is Windows)

Unlike Plans 01 and 03, **this plan has NO platform-gap deferrals**. The plan's verification runs against "the developer's system Python 3.12+ with requirements-dev.lock installed" — macOS Darwin has native Python 3.13.5 (≥ 3.12) and a pip-installable pytest + pytest-asyncio + pytest-httpx + httpx toolchain. All Wave 0 pytest verification was executed live on the host:

- `python3 -c "import tomllib; tomllib.loads(...)"` parsed pyproject.toml without exception
- `pytest tests/ --collect-only -q` listed all 9 test functions
- `pytest tests/ -v` exited 0 with 9 skipped, 0 failed, 0 errors

(The future Plan 06's bootstrap test will open an actual `.venv` under the embedded CPython layout; that is still Windows-specific for production but can be POSIX-venv'd on dev machines for the skipped-test placeholder today.)

## TDD Gate Compliance

Plan 02 is `type: execute` (Wave 0 scaffold), not `type: tdd`. No RED/GREEN/REFACTOR gate applies. Commit 1 uses `feat(...)` for the project descriptor and fixture infrastructure; commit 2 uses `test(...)` for the spec scaffolds. Matches the Plan 01 commit pattern (`feat(01-01): Nyra::Tests fixture` then `test(01-01): spec shells`).

## Known Stubs

Three conscious Wave 0 stubs, each documented inline and explicitly owned by a future plan. These are **Wave 0 scaffolds by design**, not blocking stubs:

| Stub | File | Resolved by |
|------|------|-------------|
| `mock_llama_server` async fixture body returns `None` | `tests/conftest.py` | Plan 08 |
| `mock_ollama_transport` fixture body returns `None` | `tests/conftest.py` | Plan 08 |
| 9× `@pytest.mark.skip` test functions with `raise NotImplementedError` bodies | `tests/test_*.py` | Plans 06, 07, 08, 09 |

No UI surface is stubbed, no user-facing behaviour is affected, and no data flow depends on these fixtures today — their purpose is precisely to land empty so downstream executors drop in without touching includes, fixture names, or file paths.

## Threat Flags

No new security-relevant surface introduced. The `mock_handshake_file` fixture emits a D-06 JSON payload **only to a pytest `tmp_path`** (per-test scratch area); no filesystem paths outside that temp subtree are touched, no network calls are made, and the fresh 32-byte token per fixture invocation is a deterministic test artefact (not a real session token). The production handshake writer + DACL lockdown stays in Plan 06's scope.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/__init__.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/README.md` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py` FOUND
- `TestProject/.gitignore` FOUND (modified with NyraHost Python dev-tooling ignores)

All claimed commits exist in `git log --oneline`:

- `1465d8d` FOUND — Task 1 (pyproject + lockfile + fixtures + __init__ + README + gitignore update)
- `0cbfe95` FOUND — Task 2 (9 pytest placeholder files)

## User Setup Required

None — Wave 0 scaffold is source-only. When a Python plan (06/07/08/09) executes, the developer will:

1. `cd TestProject/Plugins/NYRA/Source/NyraHost`
2. `python -m venv .venv-dev`
3. Activate the venv (platform-specific)
4. `pip install -r requirements-dev.lock`
5. `pytest tests/ -v`

Instructions are locked in `tests/README.md`.

## Next Phase Readiness

- **01-06 (nyrahost-core-ws-auth-handshake):** Ready. Three placeholder files already have the correct test-function names (`test_auth_rejects_bad_token`, `test_handshake_atomic_write`, `test_bootstrap_idempotent`); Plan 06 replaces each body and removes the `@pytest.mark.skip` decorator. `mock_handshake_file` is immediately usable for D-06 atomic-write tests.
- **01-07 (nyrahost-storage-attachments):** Ready. `tests/test_storage.py` and `tests/test_attachments.py` have CD-07/CD-08 target behaviours pointed at in their docstrings; `tmp_project_dir` provides the `Saved/NYRA/attachments/` and future `sessions.db` directory layout pre-created.
- **01-08 (nyrahost-infer-spawn-ollama-sse):** Ready. Three placeholder files (`test_infer_spawn.py`, `test_ollama_detect.py`, `test_sse_parser.py`) await real bodies; `mock_llama_server` and `mock_ollama_transport` fixtures are declared and ready to have their stub bodies replaced.
- **01-09 (gemma-downloader):** Ready. `tests/test_gemma_download.py` awaits the SHA256 + HTTP Range resume test body per RESEARCH §3.5.
- **01-04 / 01-05 / 01-10 / 01-11 / 01-12:** Unaffected — these are C++ plans, covered by the Plan 01 C++ scaffold.

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 02-python-pytest-scaffold*
*Completed: 2026-04-21*

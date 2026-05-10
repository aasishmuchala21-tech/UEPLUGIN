# Phase 8 deferred items

Pre-existing test failures discovered during 08-01 execution but
caused by code outside 08-01's scope. Documented here so they don't
silently regress and so a later plan picks them up.

## Discovered 2026-05-10 during 08-01 execution

### tests/test_claude_mcp_config.py::TestWriteMcpConfig::test_command_points_to_bundled_python

- **Failure mode:** AssertionError comparing
  `D:\Nyra\Binaries\Win64\NyraHost\python\python.exe` (actual)
  to `D:/Nyra/Binaries/Win64/NyraHost/python/python.exe` (expected).
- **Root cause:** Windows path-separator round-trip. The mcp config
  writer emits backslashes (Windows-native); the test asserts
  forward-slashes.
- **Out of scope for 08-01:** test predates this plan. Touches
  `claude_mcp_config.py` which has nothing to do with the document
  attachment pipeline.
- **Fix:** Either normalize paths to forward-slashes in the writer
  (matches typical JSON convention) or update the test assertion to
  use `Path` comparison. Pick at next Phase 02-04 follow-up.

### tests/test_transaction.py — 10 failures (PIE / transaction lifecycle)

- **Failure mode:** Multiple AssertionErrors in transaction PIE-guard
  / rollback / super-transaction tests.
- **Root cause:** Need to inspect; may be the `unreal` mock not
  matching current production state.
- **Out of scope for 08-01:** transaction module is Phase 4 mutator
  infrastructure. PARITY-01 doesn't touch it.
- **Fix:** Triage at next Phase 4 maintenance pass. Run on a clean
  tree (without 08-01 changes) reproduces all 10 failures, confirming
  they're pre-existing.

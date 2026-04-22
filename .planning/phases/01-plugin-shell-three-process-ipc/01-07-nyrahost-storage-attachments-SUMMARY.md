---
phase: 01-plugin-shell-three-process-ipc
plan: 07
subsystem: nyrahost-storage
tags: [python, sqlite, wal, content-addressed, hardlink, attachments, pytest, tdd, wave-2]

requires:
  - phase: 01-plugin-shell-three-process-ipc
    plan: 02
    provides: "tests/conftest.py fixture tmp_project_dir (pre-creates Saved/NYRA/{logs,models,attachments}/); pyproject.toml pytest config; requirements-dev.lock pytest 8.3.3 + pytest-asyncio 0.24.0 + pytest-httpx 0.32.0. Wave 0 @pytest.mark.skip stubs test_storage.py + test_attachments.py upgraded in place."
  - phase: 01-plugin-shell-three-process-ipc
    plan: 06
    provides: "nyrahost Python package layout (src/nyrahost/__init__.py __version__='0.1.0', src-layout via pyproject [tool.setuptools.packages.find] where=[\"src\"], pip install -e . editable surface so `from nyrahost.X import ...` resolves during pytest). NyraServer.register_request / register_notification extension points await Plan 10's sessions/list + sessions/load method mounts."
provides:
  - "nyrahost.storage module: Storage class + Conversation/Message frozen dataclasses + SCHEMA_V1 DDL string + CURRENT_SCHEMA_VERSION=1 + db_path_for_project helper. SQLite WAL + foreign_keys=ON + synchronous=NORMAL + PRAGMA user_version migration. CRUD surface: create_conversation / get_conversation / list_conversations / append_message (updates parent updated_at) / list_messages / link_attachment / close."
  - "nyrahost.attachments module: ingest_attachment(src_path, *, project_saved) -> AttachmentRef + AttachmentKind Literal + ALLOWED_EXTENSIONS dict (image/video/text matching CD-04) + _sha256_of_file 1 MB chunk helper + _classify extension validator. Hard-link via os.link with shutil.copy2 fallback on OSError (cross-device / FAT32 / network mount)."
  - "9 real pytest tests upgrading Plan 02's 2 Wave 0 stubs: 4 test_storage tests (schema_v1, schema_v1_idempotent, cascade, role_check) + 5 test_attachments tests (hardlink_sha256, dedup, unsupported_kind, hardlink_falls_back_to_copy, accepted_extensions_coverage). Full pytest suite now 17 passed / 4 skipped (remaining 4 skipped stubs owned by Plans 08/09)."
affects: [01-08-nyrahost-infer-spawn, 01-10-cpp-supervisor, 01-12-chat-panel-streaming-integration, 01-12b-history-drawer]

tech-stack:
  added:
    - "sqlite3 (Python stdlib) — no new pip dep; schema v1 lives as executescript on the stdlib module, connection params detect_types=PARSE_DECLTYPES + isolation_level='DEFERRED'."
    - "hashlib (Python stdlib) — streaming SHA256 in 1 MB chunks for content-addressed attachment ingestion."
    - "shutil (Python stdlib) — copy2 fallback when os.link raises OSError on cross-device / FAT32 / network mount."
  patterns:
    - "TDD RED→GREEN commit pattern inherited verbatim from Plan 06: `test(01-07): upgrade test_X.py from Wave 0 skip to real X tests` followed by `feat(01-07): add nyrahost.X ...`. Each Wave 0 @pytest.mark.skip stub is upgraded in its own RED commit; implementation lands in the follow-on GREEN commit. 2 RED + 2 GREEN = 4 atomic commits for this plan (matches both tasks carrying tdd=\"true\")."
    - "Schema DDL in a single SCHEMA_V1 string constant (not split across executemany calls) — keeps the schema grep-able for audit tools and lets the UE C++ side (Phase 2 when SQLiteCore links) mirror the exact shape verbatim. Comment block 'PRAGMA journal_mode=WAL' is load-bearing for Plan 07's grep-based acceptance criteria."
    - "PRAGMA re-assertion discipline: _migrate re-applies foreign_keys=ON + synchronous=NORMAL on every new Storage() connection (WAL is persistent in the DB file; FK + synchronous are per-connection). Any future code that opens sessions.db MUST either go through the Storage wrapper or re-assert both PRAGMAs — skipping the re-assertion silently disables CASCADE deletes on that connection."
    - "Content-addressed file storage with sharded 2-char sha256 prefix: <project_saved>/NYRA/attachments/<sha[:2]>/<sha>.<ext>. Dedup is free, per-directory file counts stay bounded (256 max shards × many files). The `path` column in attachments table stores the absolute post-ingest path, NOT the user's original src path — the src disappears after ingest, replaced by the content-addressed copy/hardlink."
    - "os.link-first-with-copy2-fallback pattern: attempt hard-link (O(1) metadata op on NTFS/APFS/ext4), catch OSError as the signal that the filesystem or mount geometry can't hardlink, then fall back to full byte copy. This pattern locks for any future NyraHost file-ingest surface (Plan 09 Gemma downloader writes into Saved/NYRA/models/ but does NOT content-address — that's intentional, models are already SHA-verified by the downloader manifest)."

key-files:
  created:
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py
  modified:
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py

key-decisions:
  - "Re-asserted foreign_keys=ON + synchronous=NORMAL on every new Storage() connection inside _migrate (not just at first-open). SQLite persists WAL mode in the DB file header but leaves foreign_keys and synchronous as per-connection runtime state — silent FK-off on a reconnect would disable CASCADE deletes and corrupt the message-parent relationship. Test_schema_v1_idempotent exercises the reconnect path implicitly (second Storage(db_path) call)."
  - "Used detect_types=sqlite3.PARSE_DECLTYPES on the Connection even though schema v1 doesn't exercise adapter types yet. Future conversation-title search (Plan 12b history drawer) will add a BLOB tsvector column for FTS; keeping PARSE_DECLTYPES on from day one means we don't need a schema-v2 migration just to change the connection flag. Zero cost today, one future migration saved."
  - "AttachmentRef.path is absolute (str(dest.resolve())) NOT a project-relative string. Rationale: the UE C++ side opens the file via FFileHelper::LoadFileToString / FMediaTexture / etc., and those expect absolute paths when the working directory is the editor's binary dir. Making the path resolution the responsibility of ingest_attachment (not every caller) eliminates a class of bugs where Plan 12's chat panel code would otherwise have to composite project_dir + relative_path in three different places."
  - "link_attachment stores the AttachmentRef path AS-IS in the attachments table (no normalization to project-relative). Matches the above: readers pull path straight from SQLite and hand to UE. If a user moves the project directory (rare for UE projects because .uproject hard-codes absolute paths in many places), the attachment paths will need a one-time fixup — Plan 12b will add that to the history drawer 'repair' action if users hit it in practice."
  - "Kept SCHEMA_V1 as a single triple-quoted string passed to executescript (not split into CREATE TABLE calls or a migrations/ directory). Schema v2 adds will prepend a `if version < 2: conn.executescript(SCHEMA_V1_TO_V2)` branch; each version gets its own constant. Simpler than a migrations framework for the 3-table v1 surface and mirrors how the UE C++ side will read the shape in Phase 2."
  - "Set AttachmentKind Literal in BOTH storage.py and attachments.py (duplicated 3-line type alias) rather than importing one from the other. Rationale: storage.py currently has no dependency on attachments.py (and vice versa), and introducing one just to share a Literal would create an import cycle risk when Plan 10 adds sessions/load handlers that touch both modules. The duplication is a 3-word enum; if it drifts, the CHECK constraint and the classifier raise ValueError at different layers catching the bug fast."

patterns-established:
  - "Plan-06 TDD RED→GREEN commit pattern confirmed applies to pure-Python storage plans as well as server plans. Future Phase 1 Python plans (08 infer spawn + Ollama detect + SSE parser, 09 gemma downloader) can inherit this exactly: upgrade Wave 0 @pytest.mark.skip stub in a `test(NN-NN): ...` commit that fails with ImportError at collection, then land implementation module in `feat(NN-NN): ...`."
  - "Schema migration floor: _migrate checks PRAGMA user_version, runs schema-v1 script if version==0, RuntimeError if version is neither 0 nor CURRENT_SCHEMA_VERSION. Future schema v2 bumps add `elif version == 1: conn.executescript(SCHEMA_V1_TO_V2); conn.execute('PRAGMA user_version=2')` — never re-run SCHEMA_V1 on an existing v1 DB. Prevents silent downgrade if a new plugin version meets an old DB."
  - "Per-fixture isolation: tests use tmp_project_dir (fresh tmp_path per test from Plan 02's conftest) so no test leaks state into another. WAL + SQLite on tmpfs on the test runner is fine (sqlite3 opens auxiliary -wal and -shm files automatically; tmp_path cleanup removes them). No fixture-scope loop key needed in pyproject.toml — Plan 06's deferral continues to hold."

requirements-completed: [CHAT-01]

duration: ~15min
completed: 2026-04-22
---

# Phase 1 Plan 07: NyraHost Storage + Attachments Summary

**Per-project SQLite persistence live: `Storage(Path)` opens/creates `<ProjectDir>/Saved/NYRA/sessions.db` at schema v1 (conversations / messages / attachments with FK-cascade + messages(conv_id, created_at) index + CHECK role IN ('user','assistant','system','tool')) in WAL + foreign_keys=ON + synchronous=NORMAL; `ingest_attachment(src, project_saved=...)` hashes the source in 1 MB chunks, hard-links (or shutil.copy2 fallback on OSError) into `Saved/NYRA/attachments/<sha[:2]>/<sha>.<ext>`, and returns an `AttachmentRef` with the absolute post-ingest path. 9 pytest tests upgraded from Wave 0 stubs; full suite 17 passed / 4 skipped on macOS Darwin Python 3.13.5 with Plan 06's 8 tests still green.**

## Performance

- **Duration:** ~15 min active executor time (git commit spread ~4h 14min wall-clock — includes initial context load + manual RED verify pauses; active Edit/Write/Bash time was ~15 min)
- **Started:** 2026-04-22T06:03:19Z (first RED work commit at 06:12:44Z)
- **Completed:** 2026-04-22T10:26:36Z (Task 2 GREEN commit)
- **Tasks:** 2/2 completed
- **Commits:** 4 (2 TDD RED + 2 GREEN)
- **Files created:** 2 (storage.py, attachments.py — both under src/nyrahost/)
- **Files modified:** 2 (test_storage.py + test_attachments.py — upgraded from Wave 0 skips to real test bodies)
- **Tests:** 9 new passing (4 storage + 5 attachments); Plan 06's 8 tests preserved green; 4 Wave 0 stubs remain owned by Plans 08/09 (test_infer_spawn, test_ollama_detect, test_sse_parser, test_gemma_download)

## Accomplishments

### Task 1 — storage.py + test_storage.py (commits 5cb4c8f RED + f6c29b5 GREEN)

- `src/nyrahost/storage.py` authored with schema v1 DDL string constant (`SCHEMA_V1`) containing PRAGMA journal_mode=WAL / synchronous=NORMAL / foreign_keys=ON + 3 CREATE TABLE IF NOT EXISTS statements + 1 CREATE INDEX IF NOT EXISTS on `messages(conversation_id, created_at)`.
- `CURRENT_SCHEMA_VERSION = 1` exported; `_migrate` reads PRAGMA user_version, runs SCHEMA_V1 executescript on version 0, raises RuntimeError on any other unexpected version (prevents silent downgrade across plugin updates).
- `Storage` class with full CRUD: `create_conversation(*, title)` → uuid4 id + ms timestamp + INSERT + commit; `get_conversation(id)` / `list_conversations(*, limit=50)` ORDER BY updated_at DESC; `append_message(*, conversation_id, role, content, usage_json=None, error_json=None)` INSERT + UPDATE conversations.updated_at + commit (so conversation list ordering reflects latest activity); `list_messages(conversation_id)` ORDER BY created_at ASC; `link_attachment(*, message_id, kind, path, size_bytes, sha256)` for Plan 12's attachment-send path; `close()` releases the connection.
- `Conversation` + `Message` frozen dataclasses with field names matching SQLite column names (enables `Conversation(**dict(row))` round-trip from sqlite3.Row).
- `db_path_for_project(project_dir)` returns the canonical CD-07 Path `<ProjectDir>/Saved/NYRA/sessions.db`; parent directory auto-created on Storage() init.
- `tests/test_storage.py` upgraded from 1 @pytest.mark.skip stub to 4 real tests: `test_schema_v1` (PRAGMA assertions + tables + index), `test_schema_v1_idempotent` (double bootstrap is a no-op), `test_insert_conversation_and_message_and_cascade` (FK ON DELETE CASCADE + ordering), `test_message_role_check` (CHECK constraint rejects invalid role with sqlite3.IntegrityError). All 4 green on first GREEN run.

### Task 2 — attachments.py + test_attachments.py (commits 89e1c49 RED + 861aa35 GREEN)

- `src/nyrahost/attachments.py` authored with `ALLOWED_EXTENSIONS: dict[AttachmentKind, frozenset[str]]` mapping CD-04's three allowed kinds (image: png/jpg/jpeg/webp; video: mp4/mov; text: md/txt). `AttachmentKind = Literal["image","video","text"]` type alias.
- `@dataclass(frozen=True) AttachmentRef` with fields sha256 / path (absolute) / size_bytes / kind / original_filename.
- `_sha256_of_file(path, chunk=1 MB)` streams the file through hashlib.sha256(), reads in 1 MB chunks (sweet spot: Python per-chunk overhead amortised while working-set stays out of L2-cache territory — important for multi-hundred-MB video fixtures).
- `_classify(ext_lower)` loops over ALLOWED_EXTENSIONS; on miss raises ValueError with a sorted list of every allow-listed extension in the message so the UE-side error remediation can surface it verbatim.
- `ingest_attachment(src_path, *, project_saved) -> AttachmentRef`: validates src is a file, classifies extension, computes sha256, creates `<project_saved>/NYRA/attachments/<sha[:2]>/` on demand, attempts `os.link(src_path, dest)` (O(1) hardlink on NTFS/APFS/ext4), falls back to `shutil.copy2(src_path, dest)` on OSError (cross-device, FAT32, network mount, CI runner without hardlink perms). Returns absolute-path AttachmentRef.
- `tests/test_attachments.py` upgraded from 1 @pytest.mark.skip stub to 5 real tests: `test_ingest_hardlink_and_sha256` (11 KB text payload, sha256 matches hashlib, dest path shape), `test_ingest_dedup` (two different filenames with same bytes yield identical path + only one physical file), `test_ingest_unsupported_kind` (`.exe` raises ValueError mentioning ext or 'Unsupported'), `test_ingest_hardlink_falls_back_to_copy` (patches `nyrahost.attachments.os.link` to raise OSError("cross-device"), verifies copy2 path produces matching sha256), `test_accepted_extensions_coverage` (every kind has >=1 ext; no overlapping extensions between kinds). All 5 green on first GREEN run.

## Task Commits

| # | Task | Type | Commit | Message |
|---|------|------|--------|---------|
| 1 | Task 1 RED | test | `5cb4c8f` | upgrade test_storage.py from Wave 0 skip to real schema tests |
| 1 | Task 1 GREEN | feat | `f6c29b5` | add nyrahost.storage with schema v1 + CRUD |
| 2 | Task 2 RED | test | `89e1c49` | upgrade test_attachments.py from Wave 0 skip to real tests |
| 2 | Task 2 GREEN | feat | `861aa35` | add nyrahost.attachments content-addressed ingestion |

_Plan metadata commit (SUMMARY + STATE + ROADMAP) follows this summary._

## Files Created/Modified

- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` — CREATED (242 lines): Storage class + Conversation/Message dataclasses + SCHEMA_V1 DDL + CURRENT_SCHEMA_VERSION + db_path_for_project helper.
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` — CREATED (145 lines): ingest_attachment + AttachmentRef + ALLOWED_EXTENSIONS + _sha256_of_file + _classify.
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py` — MODIFIED (was 11-line Wave 0 skip stub, now 93 lines of 4 real pytest test functions).
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py` — MODIFIED (was 11-line Wave 0 skip stub, now 83 lines of 5 real pytest test functions).

## Decisions Made

1. **`AttachmentRef.path` is absolute (`str(dest.resolve())`), not project-relative.** UE C++ readers expect absolute paths (FFileHelper::LoadFileToString from editor working directory). Keeping this inside ingest_attachment instead of pushing to every caller eliminates a class of "who resolves the path?" bugs downstream in Plan 12 chat panel code.

2. **Re-assert `PRAGMA foreign_keys=ON` + `PRAGMA synchronous=NORMAL` on every new `Storage()` connection.** WAL persists in the DB file header (set once at bootstrap), but FK + synchronous are per-connection runtime state. Silent FK-off on a reconnect would disable CASCADE delete → corrupt the message/conversation relationship without any error surface. test_schema_v1_idempotent exercises the reconnect path implicitly.

3. **Enabled `detect_types=sqlite3.PARSE_DECLTYPES` at day one, even though v1 uses no custom types.** Plan 12b's FTS columns (future tsvector BLOB) need this flag; enabling it now avoids a schema v2 migration later just to flip the Connection flag. Zero cost today, one future migration saved.

4. **Schema DDL as a single `SCHEMA_V1` string constant via `executescript`, not split migrations.** Three tables + one index is simpler to read as a single block than a migrations/ directory; future v2 bumps add a parallel `SCHEMA_V1_TO_V2` constant and branch on user_version. Also keeps the shape grep-able for the UE C++ audit tools in Phase 2.

5. **`AttachmentKind` Literal duplicated (3 lines) in both storage.py and attachments.py rather than imported from one into the other.** Avoids an import cycle risk when Plan 10 mounts sessions/load handlers that reach into both modules. The duplication is 3 words; drift would be caught by either the CHECK constraint or the _classify ValueError.

6. **`os.link` with `shutil.copy2` fallback, not vice versa.** Hardlink is O(1) metadata on NTFS/APFS/ext4 (the common case); copy2 is the escape hatch for cross-device, FAT32, network mount, CI runner without hardlink perms. Matches CD-08's "hard-linked (or copied)" wording — the planner called the bias correctly.

## Deviations from Plan

None — plan executed exactly as written.

Both tasks landed at GREEN on first implementation run. The storage.py and attachments.py contents match the PLAN.md `<action>` blocks verbatim (same class shape, same dataclass fields, same function signatures, same DDL string). The test bodies match the PLAN.md spec verbatim. No Rule 1/2/3 auto-fixes needed. No Rule 4 architectural escalation needed. No out-of-scope discoveries queued to `deferred-items.md`.

Zero PLAN.md-mandated supersets either: neither `storage.py` nor `attachments.py` existed before this plan (both `create mode 100644` in the GREEN commits), so no prior-plan symbols to preserve. The test files DID exist as Wave 0 @pytest.mark.skip stubs from Plan 02, and they were upgraded in place per the plan's Task 1 acceptance criterion "test_storage.py contains `def test_schema_v1(tmp_project_dir: Path)` (NOT skipped)" — the upgrade is the explicit plan contract, not a deviation.

## Issues Encountered

None. Every step ran sequentially on first attempt:

- RED commits landed with the expected ModuleNotFoundError at collection (pytest cannot import nyrahost.storage / nyrahost.attachments because neither module exists yet).
- GREEN commits landed with the expected 4 (storage) and 5 (attachments) test passes on first run.
- Plan 06's 8 baseline tests (3 auth + 3 handshake + 2 bootstrap) remained green through every GREEN step.
- Full suite final state: 17 passed / 4 skipped / 0 failed / 0 errors in ~9 seconds on macOS Darwin Python 3.13.5 via the .venv-dev installed editable (pip install -e .) package.

## Platform notes (host is macOS, target is Windows)

All Plan 07 code is pure Python stdlib (sqlite3 + hashlib + os + shutil + pathlib + dataclasses + typing) + zero runtime deps beyond what Plan 06 already shipped. Every test runs LIVE on the macOS Darwin host against production code — same wire path a Windows-hosted NyraHost will take.

Zero platform-gap deferrals this plan:

- `os.link` / `shutil.copy2` both work on macOS APFS (HFS+ behind the scenes) and Windows NTFS. The cross-device fallback is exercised via the `patch("nyrahost.attachments.os.link", side_effect=OSError("cross-device"))` test — no need to spin up a second volume.
- SQLite WAL mode works on every major host OS; WAL files (`-wal`, `-shm`) live next to the main DB file and are cleaned up on normal connection close.
- UTF-8 path handling (`str(dest.resolve())`) is transparent across OS boundaries — sqlite3 stores the path bytes as a TEXT column and Python 3 encodes / decodes via fs_encoding.

Windows-specific caveat worth noting for downstream plans: `os.link` on Windows requires SeCreateSymbolicLinkPrivilege and/or the target filesystem being NTFS (not FAT32 / exFAT on USB drives). The `shutil.copy2` fallback handles both. Plan 12b may want to surface a user-facing diagnostic if `link` falls back to copy (via a `diagnostics/attachment-ingest-fallback` notification) because on sufficiently large corpora the copy-not-link difference is ~100 GB of real storage.

## TDD Gate Compliance

Plan 07 is `type: execute` with both tasks carrying `tdd="true"`. Gate compliance:

| Task | RED commit | GREEN commit | REFACTOR | Gate status |
|------|------------|--------------|----------|-------------|
| 1    | `5cb4c8f` test(01-07): test_storage.py RED    | `f6c29b5` feat(01-07): storage.py GREEN     | n/a | PASS |
| 2    | `89e1c49` test(01-07): test_attachments.py RED | `861aa35` feat(01-07): attachments.py GREEN | n/a | PASS |

Each RED commit contained ONLY the test file change (upgrade of the Wave 0 stub to the full test body). `pytest tests/test_storage.py` / `pytest tests/test_attachments.py` on the RED commit both produced the expected `ModuleNotFoundError: No module named 'nyrahost.storage'` / `'nyrahost.attachments'` at collection — no test passed unexpectedly during RED. Each GREEN commit contained ONLY the implementation module under `src/nyrahost/`. All 4 tests in test_storage.py and all 5 tests in test_attachments.py passed on the first GREEN run. REFACTOR commits not needed — GREEN implementations were clean first pass.

## Known Stubs

None in Plan 07's own surface. Plan 02's remaining 4 Wave 0 stubs (test_infer_spawn, test_ollama_detect, test_sse_parser, test_gemma_download) remain `@pytest.mark.skip` — they are stubs by design, owned by downstream plans 08 and 09. This matches Plan 06's "Known Stubs" treatment exactly.

## Threat Flags

No new network-exposed surface in Plan 07. Security-adjacent observations:

- SQLite DB file lives under `<ProjectDir>/Saved/NYRA/` which inherits the UE project directory's POSIX / NTFS permissions — it is NOT world-readable on a user's own machine under a per-user Saved tree. No DACL work needed on the DB file (handshake.py's Windows owner-only DACL is still the one Phase 1 surface that needs it, and that landed in Plan 06).
- Attachments are copied / hard-linked into the same `Saved/NYRA/attachments/` subtree; same permissions posture.
- No secrets written to the DB in Plan 07's CRUD surface. Phase 2 will carry tokens / credentials in the Claude CLI subprocess env; those never touch sessions.db.
- Path handling: `ingest_attachment` uses `Path.is_file()` gate + `src_path.suffix.lower()` classification — no shell invocation, no subprocess, no tar extraction, no symbolic-link evaluation that could escape the attachments dir. A path-traversal attempt would have to go through the .extension allow-list first, which only accepts image/video/text literal suffixes.

No threat flags to raise for downstream scrutiny.

## Self-Check: PASSED

All claimed files exist on disk:

- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/attachments.py` FOUND
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py` FOUND (upgraded from Wave 0 stub — 93 lines vs prior 11)
- `TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py` FOUND (upgraded from Wave 0 stub — 83 lines vs prior 11)

All claimed commits exist in `git log --oneline`:

- `5cb4c8f` FOUND — Task 1 RED (test_storage.py upgrade)
- `f6c29b5` FOUND — Task 1 GREEN (storage.py + schema v1 + CRUD)
- `89e1c49` FOUND — Task 2 RED (test_attachments.py upgrade)
- `861aa35` FOUND — Task 2 GREEN (attachments.py content-addressed ingestion)

All 9 new Plan 07 pytest tests plus Plan 06's 8 baseline tests run green LIVE on macOS Darwin Python 3.13.5: `17 passed, 4 skipped, 3 deprecation warnings, 0 failed, 0 errors` on the final `pytest tests/ -v` run.

## Next Phase Readiness

- **01-08 (nyrahost-infer-spawn-ollama-sse):** Ready. NyraServer.register_request can mount `chat/send` handler; Plan 08 will author the Ollama HTTP client + llama-server subprocess spawn + SSE parser, and append messages via `Storage.append_message` when a chat round-trip completes. Storage WAL mode means Plan 08's write path does NOT conflict with a future read path from Plan 12's history drawer.
- **01-09 (gemma-downloader):** Ready. Gemma downloader writes to `<ProjectDir>/Saved/NYRA/models/` (distinct from attachments/), does NOT go through ingest_attachment. Plan 09 has its own SHA256+Range resume path per the assets-manifest.json pinned hashes.
- **01-10 (cpp-supervisor + ws/jsonrpc UE client):** Ready for `sessions/list` + `sessions/load` method handlers. Handler body: `storage.list_conversations(limit=50)` → build JSON-RPC response via Plan 06's `build_response`. Storage is the ONLY writer; the handler is a read (no commit). `sessions/load` calls `storage.list_messages(conversation_id)`.
- **01-12 (chat-panel-streaming-integration):** Ready. Attachment send flow is: panel drops a file → UE code sends chat/send with `attachments: [{kind, path}]` → Plan 08 server receives and calls `ingest_attachment(Path(params.path), project_saved=<ProjectDir>/Saved)` → records via `storage.link_attachment`. `AttachmentRef.path` being absolute means Plan 12's chat panel can render attachment thumbnails via direct FFileHelper load without path re-composition.
- **01-12b (history-drawer):** Ready. History drawer is a pure reader: queries `storage.list_conversations(limit=50)` on tab open, `storage.list_messages(conversation.id)` on conversation select. No writes from the drawer. Storage v1 schema already covers the drawer's display columns (title, updated_at, message count derivable via COUNT(*)).

---

*Phase: 01-plugin-shell-three-process-ipc*
*Plan: 07-nyrahost-storage-attachments*
*Completed: 2026-04-22*

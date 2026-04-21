---
phase: 01-plugin-shell-three-process-ipc
plan: 02
type: execute
wave: 0
depends_on: []
autonomous: true
requirements: [PLUG-02, PLUG-03, CHAT-01]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
  - TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/README.md
objective: >
  Create the Python pytest scaffold for NyraHost: pyproject.toml with pytest +
  black + ruff + mypy config, requirements-dev.lock with pinned dev deps,
  conftest.py with shared fixtures (temp project dir, mock llama-server, mock
  handshake), and 10 empty test_*.py files (one per VALIDATION.md Wave 0 pytest
  row) that each contain a single placeholder `@pytest.mark.skip` test so
  `pytest -v` exits 0 and lists every future test target. Addresses
  RESEARCH §"Validation Architecture" (Wave 0 Gaps, Python rows).
must_haves:
  truths:
    - "Running `pytest tests/ -v` from NyraHost/ exits 0 (all skipped)"
    - "Running `pytest tests/ --collect-only -q` lists at least 10 placeholder test functions"
    - pyproject.toml declares pytest as the test runner and sets `asyncio_mode = "auto"`
    - requirements-dev.lock pins pytest, pytest-asyncio, pytest-httpx, black, ruff, mypy with exact versions
    - conftest.py provides a `tmp_project_dir` fixture that returns a unique Path under pytest's `tmp_path_factory`
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
      provides: "Python project descriptor with pytest + lint config"
      contains: "asyncio_mode"
    - path: TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock
      provides: "Pinned dev dependencies — never shipped to users"
      contains: "pytest=="
    - path: TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
      provides: "Shared fixtures: tmp_project_dir, mock_llama_server, mock_handshake_file, mock_ollama_transport"
      exports: ["tmp_project_dir", "mock_llama_server", "mock_handshake_file"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
      provides: "Auth rejection test shell (Plan 06 fills)"
      contains: "def test_auth_rejects_bad_token"
  key_links:
    - from: "pyproject.toml [tool.pytest.ini_options]"
      to: "tests/ directory"
      via: "testpaths setting"
      pattern: "testpaths = \\[\"tests\"\\]"
---

<objective>
Create Wave 0 Python test infrastructure so every task in Waves 2-5 that
touches NyraHost can add real tests and cite the test ID from VALIDATION.md.
Per CONTEXT.md D-13/D-14, NyraHost ships embedded CPython + a pre-resolved
wheel cache — but dev-time tests run against the developer's system Python
with requirements-dev.lock installed (NOT shipped to users).

Per RESEARCH §"Validation Architecture":
- Framework: pytest 8.x + pytest-asyncio + pytest-httpx
- Quick run: `pytest NyraHost/tests/ -x`
- Full run: `pytest NyraHost/tests/ -v`
- Sampling target: sub-second per test after populated.

Purpose: Later plans (06, 07, 08, 09, 10, 12) expect these exact files and
fixture names; this plan creates all of them empty so dependency order is
clean.

Output: 10 empty test_*.py files each with one skipped placeholder test, 1
conftest.py with 4 fixtures, pyproject.toml, requirements-dev.lock, README.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md
</context>

<interfaces>
pyproject.toml canonical pytest-asyncio shape (verify with Context7 at execute
time if unsure; cite `mcp:context7` query `pytest-asyncio auto mode pyproject`):

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "nyrahost"
version = "0.1.0"
requires-python = ">=3.12"

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-ra --strict-markers --strict-config"
markers = [
    "integration: end-to-end tests that spawn real subprocesses (default: skip in CI quick)",
]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.black]
line-length = 100
target-version = ["py312"]

[tool.mypy]
python_version = "3.12"
strict = true
```

conftest.py canonical shape with 4 fixtures:

```python
import pytest
from pathlib import Path
import json
import secrets
import httpx

@pytest.fixture
def tmp_project_dir(tmp_path: Path) -> Path:
    # Mirrors <ProjectDir>/Saved/NYRA/ layout expected by storage + attachments.
    saved = tmp_path / "Saved" / "NYRA"
    (saved / "logs").mkdir(parents=True)
    (saved / "models").mkdir()
    (saved / "attachments").mkdir()
    return tmp_path

@pytest.fixture
def mock_handshake_file(tmp_path: Path) -> Path:
    payload = {
        "port": 54321,
        "token": secrets.token_hex(32),
        "nyrahost_pid": 11111,
        "ue_pid": 22222,
        "started_at": 1700000000000,
    }
    f = tmp_path / "handshake-22222.json"
    f.write_text(json.dumps(payload))
    return f

@pytest.fixture
async def mock_llama_server():
    # Returns an object with .port, .url, stop() that simulates llama-server
    # printing "server listening at http://127.0.0.1:PORT". Plan 08 wires real behaviour.
    ...

@pytest.fixture
def mock_ollama_transport():
    # Returns httpx.MockTransport that answers GET /api/tags with a canned
    # {"models":[{"name":"gemma3:4b-it-qat",...}]} body. Plan 08 wires real.
    ...
```
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: pyproject.toml + requirements-dev.lock + conftest.py + __init__.py + README</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
    TestProject/Plugins/NYRA/Source/NyraHost/requirements-dev.lock
    TestProject/Plugins/NYRA/Source/NyraHost/tests/__init__.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/README.md
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-13 through D-16 (embedded Python, deps list, logging)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.4 (venv + wheels), §"Validation Architecture"
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md (pytest test IDs)
  </read_first>
  <action>
    Create `pyproject.toml` with EXACT contents from the `<interfaces>` block
    above (project name `nyrahost`, python >= 3.12, pytest testpaths=["tests"],
    asyncio_mode="auto", strict markers, integration marker, ruff line-length=100,
    black target py312, mypy strict=true).

    Create `requirements-dev.lock` pinning these exact versions (resolve any
    minor version differences at execute time but keep MAJOR.MINOR pins):
    ```
    pytest==8.3.3
    pytest-asyncio==0.24.0
    pytest-httpx==0.32.0
    black==24.10.0
    ruff==0.7.1
    mypy==1.13.0
    ```
    Comment at top: `# Dev-only — NOT included in Binaries/Win64/NyraHost/wheels/ (runtime deps live in requirements.lock in Plan 06).`

    Create `tests/__init__.py` as empty file (marks the directory as a package).

    Create `tests/conftest.py` with the 4 fixtures from `<interfaces>`.
    `mock_llama_server` and `mock_ollama_transport` bodies are stubs that
    return None now — Plan 08 fills real implementations. Keep the signatures
    exact: `tmp_project_dir(tmp_path)`, `mock_handshake_file(tmp_path)`,
    `mock_llama_server()` (async fixture placeholder), `mock_ollama_transport()`.

    Add imports at top of conftest.py: `import pytest`, `from pathlib import Path`,
    `import json`, `import secrets`, `import httpx`.

    Create `tests/README.md`:
    ```markdown
    # NyraHost tests

    Runs against the developer's system Python 3.12 with
    `requirements-dev.lock` installed — NOT the bundled runtime python.

    ## Setup (dev machine, once)

    ```
    cd TestProject/Plugins/NYRA/Source/NyraHost
    python -m venv .venv-dev
    .venv-dev\Scripts\activate
    pip install -r requirements-dev.lock
    ```

    ## Run

    Quick (fail fast):
    ```
    pytest tests/ -x
    ```

    Full verbose:
    ```
    pytest tests/ -v
    ```

    Integration (spawns real subprocesses; slower):
    ```
    pytest tests/ -v -m integration
    ```

    ## Test files -> Plan mapping

    | File | Plan | Test ID per VALIDATION |
    |------|------|------------------------|
    | test_auth.py | 06 | 1-02-04 |
    | test_handshake.py | 06 | 1-02-05 |
    | test_bootstrap.py | 06 | 1-02-06 |
    | test_infer_spawn.py | 08 | 1-03-01 |
    | test_ollama_detect.py | 08 | 1-03-02 |
    | test_sse_parser.py | 08 | 1-03-03 |
    | test_gemma_download.py | 09 | 1-03-04 |
    | test_storage.py | 07 | 1-04-06 |
    | test_attachments.py | 07 | 1-04-07 |
    ```
  </action>
  <verify>
    <automated>
      - Change dir to TestProject/Plugins/NYRA/Source/NyraHost and run `python -c "import tomllib; tomllib.loads(open('pyproject.toml','rb').read().decode())"` (parses without exception)
      - `grep -c "asyncio_mode" pyproject.toml` equals 1 and value is `"auto"`
      - `grep -c "pytest==" requirements-dev.lock` equals 1
      - `grep -c "def tmp_project_dir" tests/conftest.py` equals 1
      - `grep -c "def mock_handshake_file" tests/conftest.py` equals 1
    </automated>
  </verify>
  <acceptance_criteria>
    - File pyproject.toml contains literal text `asyncio_mode = "auto"`
    - File pyproject.toml contains literal text `testpaths = ["tests"]`
    - File pyproject.toml contains literal text `strict = true` (mypy section)
    - File pyproject.toml contains literal text `"integration: end-to-end tests that spawn real subprocesses (default: skip in CI quick)"`
    - File requirements-dev.lock contains literal text `pytest==`
    - File requirements-dev.lock contains literal text `pytest-asyncio==`
    - File requirements-dev.lock contains literal text `pytest-httpx==`
    - File requirements-dev.lock contains literal text `black==`
    - File requirements-dev.lock contains literal text `ruff==`
    - File requirements-dev.lock contains literal text `mypy==`
    - File tests/__init__.py exists (can be empty)
    - File tests/conftest.py contains literal text `def tmp_project_dir(tmp_path: Path) -> Path:`
    - File tests/conftest.py contains literal text `def mock_handshake_file(tmp_path: Path) -> Path:`
    - File tests/conftest.py contains literal text `"port": 54321`
    - File tests/conftest.py contains literal text `import httpx`
    - File tests/README.md contains literal text `1-02-04` (VALIDATION ID mapping)
  </acceptance_criteria>
  <done>pyproject + lockfile + fixtures file on disk; `pytest --collect-only -q` from NyraHost/ returns 0 collected (no test files yet, but no errors).</done>
</task>

<task type="auto">
  <name>Task 2: Create 9 empty test_*.py placeholder files</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_download.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_storage.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_attachments.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-VALIDATION.md Per-Task Verification Map rows 1-02-04, 1-02-05, 1-02-06, 1-03-01, 1-03-02, 1-03-03, 1-03-04, 1-04-06, 1-04-07
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py (just created)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.3 (infer spawn), §3.5 (SSE parser, Ollama detect, Gemma download), §3.7 (storage, attachments)
  </read_first>
  <action>
    Create each of the 9 test_*.py files with this exact template, substituting
    the test-function name per the required VALIDATION test ID:

    ```python
    """Placeholder — Plan {FILLER_PLAN} fills in real tests.
    VALIDATION test ID: {TEST_ID}
    """
    import pytest


    @pytest.mark.skip(reason="Wave 0 placeholder; Plan {FILLER_PLAN} implements")
    def {TEST_NAME}() -> None:
        # Target behaviour described in RESEARCH.md §{RESEARCH_SECTION}
        raise NotImplementedError
    ```

    Exact substitutions (FILLER_PLAN / TEST_ID / TEST_NAME / RESEARCH_SECTION):

    | File | FILLER_PLAN | TEST_ID | TEST_NAME | RESEARCH_SECTION |
    |------|-------------|---------|-----------|------------------|
    | test_auth.py | 06 | 1-02-04 | `test_auth_rejects_bad_token` | "§3.4 embedded Python; D-07 auth" |
    | test_handshake.py | 06 | 1-02-05 | `test_handshake_atomic_write` | "§3.10 P1.1 atomic rename" |
    | test_bootstrap.py | 06 | 1-02-06 | `test_bootstrap_idempotent` | "§3.4 venv rebuild marker" |
    | test_infer_spawn.py | 08 | 1-03-01 | `test_llama_server_port_capture` | "§3.3 B, §3.5 llama-server flags" |
    | test_ollama_detect.py | 08 | 1-03-02 | `test_ollama_detect_gemma3_present` | "§3.5 Ollama detect" |
    | test_sse_parser.py | 08 | 1-03-03 | `test_sse_delta_extraction` | "§3.5 SSE streaming" |
    | test_gemma_download.py | 09 | 1-03-04 | `test_sha256_verify_and_range_resume` | "§3.5 Gemma download URL + HTTP Range" |
    | test_storage.py | 07 | 1-04-06 | `test_schema_v1` | "§3.7 SQLite schema bootstrap" |
    | test_attachments.py | 07 | 1-04-07 | `test_ingest_hardlink_and_sha256` | "§3.7 attachment content-addressing" |

    Each file has exactly ONE `@pytest.mark.skip`-decorated function whose
    name matches the TEST_NAME column. The function body is
    `raise NotImplementedError`. No fixture usage needed at this stage — the
    signature takes no arguments.
  </action>
  <verify>
    <automated>
      From TestProject/Plugins/NYRA/Source/NyraHost/:
      - `pytest tests/ --collect-only -q | grep "test_" | wc -l` equals 9
      - `pytest tests/ -v` exits 0 with 9 skipped and 0 failed
    </automated>
  </verify>
  <acceptance_criteria>
    - File tests/test_auth.py contains literal text `def test_auth_rejects_bad_token(` and `@pytest.mark.skip`
    - File tests/test_handshake.py contains literal text `def test_handshake_atomic_write(` and `@pytest.mark.skip`
    - File tests/test_bootstrap.py contains literal text `def test_bootstrap_idempotent(` and `@pytest.mark.skip`
    - File tests/test_infer_spawn.py contains literal text `def test_llama_server_port_capture(` and `@pytest.mark.skip`
    - File tests/test_ollama_detect.py contains literal text `def test_ollama_detect_gemma3_present(` and `@pytest.mark.skip`
    - File tests/test_sse_parser.py contains literal text `def test_sse_delta_extraction(` and `@pytest.mark.skip`
    - File tests/test_gemma_download.py contains literal text `def test_sha256_verify_and_range_resume(` and `@pytest.mark.skip`
    - File tests/test_storage.py contains literal text `def test_schema_v1(` and `@pytest.mark.skip`
    - File tests/test_attachments.py contains literal text `def test_ingest_hardlink_and_sha256(` and `@pytest.mark.skip`
    - Each file references its FILLER_PLAN number in the docstring or skip reason
    - `pytest tests/ -v` from the NyraHost/ dir exits 0 (9 skipped)
  </acceptance_criteria>
  <done>All 9 test stubs exist; `pytest tests/ -v` shows 9 skipped, 0 failed, 0 errors. Later plans replace each body.</done>
</task>

</tasks>

<verification>
From TestProject/Plugins/NYRA/Source/NyraHost/ (system Python 3.12 with
requirements-dev.lock installed):
```
pytest tests/ -v
```
Must exit 0 with exactly 9 tests, all skipped.
</verification>

<success_criteria>
- pyproject.toml, requirements-dev.lock, conftest.py, 9 test_*.py, README.md all on disk
- `pytest tests/ -v` from NyraHost/ exits 0, reports 9 skipped
- Every VALIDATION.md Wave 0 pytest file exists and is discoverable
- Dev deps (pytest, pytest-asyncio, pytest-httpx, black, ruff, mypy) pinned in requirements-dev.lock
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-02-SUMMARY.md`
listing the 12 files created, the fixture names, and the test-ID -> plan
mapping table from README.md.
</output>

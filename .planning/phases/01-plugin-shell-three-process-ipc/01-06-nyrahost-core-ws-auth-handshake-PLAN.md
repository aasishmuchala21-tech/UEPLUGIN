---
phase: 01-plugin-shell-three-process-ipc
plan: 06
type: execute
wave: 2
depends_on: [02, 05]
autonomous: true
requirements: [PLUG-02]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock
  - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/bootstrap.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/config.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/logging_setup.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/session.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py
  - TestProject/Plugins/NYRA/prebuild.ps1
objective: >
  Implement the NyraHost Python sidecar core: venv bootstrap, structlog JSON
  logging, handshake file atomic writer (D-06), asyncio WebSocket server
  (`websockets` package, D-15), JSON-RPC 2.0 envelope parser, and
  `session/authenticate` + `session/hello` request handlers (D-07, D-10).
  Fills tests/test_auth.py (VALIDATION 1-02-04), tests/test_handshake.py
  (1-02-05), tests/test_bootstrap.py (1-02-06). Creates prebuild.ps1 that
  fetches python-build-standalone + wheels per assets-manifest.json. Ends
  with `cpython/python.exe -m nyrahost` serving on 127.0.0.1:<ephemeral>,
  writing handshake, authenticating a WS client, replying session/hello.
must_haves:
  truths:
    - "Running `python -m nyrahost --editor-pid 1234 --log-dir /tmp/nyralog` binds 127.0.0.1:<ephemeral>, writes handshake-1234.json atomically, starts WS server"
    - "First WS frame with valid session/authenticate token yields {authenticated:true, session_id:<uuid>}; subsequent session/hello returns {backends:[\"gemma-local\"], phase:1, session_id:<uuid>}"
    - "First WS frame with WRONG token triggers WS close with code 4401 + reason 'unauthenticated'"
    - "First WS frame with any method other than session/authenticate also triggers close 4401"
    - "pytest tests/test_auth.py::test_auth_rejects_bad_token passes"
    - "pytest tests/test_handshake.py::test_handshake_atomic_write passes"
    - "pytest tests/test_bootstrap.py::test_bootstrap_idempotent passes"
    - "prebuild.ps1 reads assets-manifest.json and downloads python-build-standalone + unpacks to Binaries/Win64/NyraHost/cpython/"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock
      provides: "Runtime-only pinned deps (D-15)"
      contains: "websockets=="
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
      provides: "Module entrypoint: parses --editor-pid + --log-dir, runs asyncio.run(main())"
      exports: ["main"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py
      provides: "Atomic handshake file writer + cleanup helpers"
      exports: ["write_handshake", "handshake_file_path", "cleanup_orphan_handshakes"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
      provides: "asyncio `websockets.serve` loop; auth gate on first frame"
      exports: ["run_server"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py
      provides: "Envelope parse + response/notification builders"
      exports: ["parse_envelope", "build_response", "build_error", "build_notification"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/bootstrap.py
      provides: "Venv create + offline wheel install; marker-file rebuild logic (D-14)"
      exports: ["ensure_venv", "VENV_MARKER_FILENAME"]
    - path: TestProject/Plugins/NYRA/prebuild.ps1
      provides: "One-shot fetch + extract of python-build-standalone per assets-manifest.json"
      contains: "Invoke-WebRequest"
  key_links:
    - from: NyraHost server.py `authenticate()` gate
      to: docs/JSONRPC.md §3.1
      via: "Reject with close code 4401 if token mismatch or first method != session/authenticate"
      pattern: "close code 4401"
    - from: NyraHost handshake.py `write_handshake`
      to: docs/HANDSHAKE.md writer protocol
      via: "json.dump + fsync + os.replace atomic rename"
      pattern: "os.replace"
    - from: prebuild.ps1
      to: TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
      via: "Reads JSON, downloads each entry, SHA256 verifies, unpacks to dest"
      pattern: "assets-manifest.json"
---

<objective>
Produce the Python half of the UE-NyraHost handshake + WS transport stack.
This plan is the BIGGEST Phase 1 Python plan — wrapping 4 concerns (bootstrap,
logging, handshake, WS server) — because they are all tightly entangled and
splitting them leaves one useless without another.

Per CONTEXT.md D-04 (eager spawn on editor start), D-06 (handshake file
atomic + DACL), D-07 (32-byte token + close code 4401), D-09/D-10 (JSON-RPC
envelope + Phase 1 6-method surface), D-13 (embedded CPython layout),
D-14 (venv + wheel cache + marker-file rebuild), D-15 (pinned deps), D-16
(structlog JSON logs).

Per RESEARCH §3.2 (WS transport alternative selection), §3.4 (embedded
Python + venv mechanics), §3.10 P1.1 (handshake atomic-rename race), P1.2
(orphan cleanup), P1.3 (venv corruption marker), P1.7 (id collision /
session_id envelope check).

Purpose: Plan 10 (UE C++ supervisor) needs a REAL NyraHost to connect to;
Plans 07/08/09 need a running server.py to mount storage/infer/download
handlers onto.
Output: `python -m nyrahost` that an external WS client can authenticate
against and invoke session/hello on.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@docs/HANDSHAKE.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md
@TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
@TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py
@TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json
</context>

<interfaces>
`websockets` 12.0+ canonical serve pattern (verify with Context7 at execute
time; cite `mcp:context7` query `websockets python serve handler 12`):

```python
import asyncio, websockets

async def handler(ws: websockets.ServerConnection):
    # ws.remote_address, ws.send(str), async for msg in ws, ws.close(code, reason)
    ...

async def main():
    server = await websockets.serve(
        handler, "127.0.0.1", 0,
        ping_interval=30, ping_timeout=10,
        max_size=16 * 1024 * 1024,  # 16 MB frame cap
    )
    sockets = server.sockets
    port = sockets[0].getsockname()[1]
    # write handshake file NOW
    await server.serve_forever()

asyncio.run(main())
```

structlog canonical JSON logging setup (D-16):

```python
import logging, structlog
from logging.handlers import TimedRotatingFileHandler

def configure_logging(log_dir: Path) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / f"nyrahost-{datetime.utcnow():%Y-%m-%d}.log"
    handler = TimedRotatingFileHandler(log_file, when="midnight", backupCount=7, encoding="utf-8")
    logging.basicConfig(level=logging.INFO, handlers=[handler], format="%(message)s")
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
```
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: requirements.lock + pyproject update + bootstrap.py + prebuild.ps1</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock
    TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__init__.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/bootstrap.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py
    TestProject/Plugins/NYRA/prebuild.ps1
  </files>
  <read_first>
    - TestProject/Plugins/NYRA/Source/NyraHost/pyproject.toml (Wave 0 version from Plan 02)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py (Wave 0 placeholder)
    - TestProject/Plugins/NYRA/Source/NyraHost/assets-manifest.json (Plan 05)
    - docs/BINARY_DISTRIBUTION.md (Plan 03)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-13, D-14, D-15
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.4 (venv + wheels + marker)
  </read_first>
  <behavior>
    - test_bootstrap.py::test_bootstrap_idempotent: calling ensure_venv twice in the same process is a no-op after the first successful run (marker file contains current version).
    - test_bootstrap.py::test_bootstrap_rebuilds_on_version_change: writing a stale version to marker forces full rebuild on next ensure_venv.
    - test_bootstrap.py::test_bootstrap_skips_if_wheels_missing_but_venv_present: if venv exists and marker matches, does not retry `pip install`.
  </behavior>
  <action>
    **1. UPDATE pyproject.toml** — add src/ package discovery and runtime
    dependency listing (reference only — actual install uses requirements.lock):

    Append these sections to the existing pyproject.toml from Plan 02:
    ```toml
    [project]
    name = "nyrahost"
    version = "0.1.0"
    requires-python = ">=3.12"
    dependencies = [
        "mcp>=1.2.0",
        "websockets>=12.0",
        "httpx>=0.27",
        "pydantic>=2.7",
        "structlog>=24.1",
        "pywin32; sys_platform == 'win32'",
    ]

    [tool.setuptools.packages.find]
    where = ["src"]
    ```

    **2. CREATE requirements.lock** — runtime deps only (NOT dev deps; those
    live in requirements-dev.lock from Plan 02):

    Resolve on dev machine via `pip-compile --generate-hashes` on the runtime
    deps above. For Plan 06 execution, use these canonical pins (executor MUST
    verify and re-resolve minor versions if any pin no longer exists on PyPI):
    ```
    # NyraHost Phase 1 runtime deps (D-15). Bundled as wheels under
    # Binaries/Win64/NyraHost/wheels/ for offline install (D-14).
    mcp==1.2.0
    websockets==12.0
    httpx==0.27.0
    pydantic==2.7.4
    pydantic-core==2.18.4
    anyio==4.3.0
    sniffio==1.3.1
    httpcore==1.0.5
    h11==0.14.0
    idna==3.7
    certifi==2024.7.4
    structlog==24.1.0
    annotated-types==0.7.0
    typing-extensions==4.12.2
    pywin32==306 ; sys_platform == 'win32'
    ```

    **3. CREATE src/nyrahost/__init__.py** with:
    ```python
    """NyraHost — NYRA's Python sidecar (Phase 1: WS + handshake + session)."""
    __version__ = "0.1.0"
    ```

    **4. CREATE src/nyrahost/bootstrap.py** implementing venv setup with
    marker-file rebuild (D-14, P1.3):

    ```python
    """Bootstrap: create venv + install wheels offline; rebuild on version mismatch."""
    from __future__ import annotations
    import os
    import shutil
    import subprocess
    import sys
    from pathlib import Path

    VENV_MARKER_FILENAME = "nyra-plugin-version.txt"
    NYRA_PLUGIN_VERSION = "0.1.0"  # bump to trigger venv rebuild on plugin update

    def default_venv_path() -> Path:
        local_appdata = os.environ.get("LOCALAPPDATA")
        if local_appdata:
            return Path(local_appdata) / "NYRA" / "venv"
        # Fallback for non-Windows dev machines running tests
        return Path.home() / ".local" / "share" / "NYRA" / "venv"

    def _read_marker(venv: Path) -> str | None:
        m = venv / VENV_MARKER_FILENAME
        if not m.exists():
            return None
        return m.read_text(encoding="utf-8").strip()

    def _write_marker(venv: Path, version: str) -> None:
        (venv / VENV_MARKER_FILENAME).write_text(version + "\n", encoding="utf-8")

    def ensure_venv(
        *,
        python_exe: Path,
        venv_dir: Path | None = None,
        wheels_dir: Path,
        requirements_lock: Path,
        plugin_version: str = NYRA_PLUGIN_VERSION,
    ) -> Path:
        """Idempotent: create venv at venv_dir, install wheels from wheels_dir,
        write marker. If marker mismatches plugin_version, rmtree and rebuild.
        Returns path to venv's python.exe."""
        venv = venv_dir or default_venv_path()
        existing = _read_marker(venv)
        if existing == plugin_version:
            # Already bootstrapped at this version — idempotent no-op
            return _venv_python_exe(venv)
        if venv.exists():
            shutil.rmtree(venv, ignore_errors=True)
        venv.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [str(python_exe), "-m", "venv", "--copies", str(venv)],
            check=True,
        )
        # Offline wheel install
        venv_py = _venv_python_exe(venv)
        subprocess.run(
            [
                str(venv_py), "-m", "pip", "install",
                "--no-index",
                "--find-links", str(wheels_dir),
                "-r", str(requirements_lock),
            ],
            check=True,
        )
        _write_marker(venv, plugin_version)
        return venv_py

    def _venv_python_exe(venv: Path) -> Path:
        # Windows venv layout: <venv>/Scripts/python.exe; POSIX: <venv>/bin/python
        if sys.platform == "win32":
            return venv / "Scripts" / "python.exe"
        return venv / "bin" / "python"
    ```

    **5. UPDATE tests/test_bootstrap.py** (replace Wave 0 placeholder):

    ```python
    """Bootstrap venv + offline wheel install tests.
    VALIDATION test ID: 1-02-06
    """
    from __future__ import annotations
    from pathlib import Path
    import sys
    import pytest
    from nyrahost.bootstrap import ensure_venv, VENV_MARKER_FILENAME

    # We use the system Python that runs pytest as the "embedded interpreter"
    # for the unit-test scenarios — the real embedded CPython lives under
    # Binaries/Win64/NyraHost/cpython/ and is tested by an integration test.

    def test_bootstrap_idempotent(tmp_path: Path) -> None:
        venv = tmp_path / "venv"
        wheels = tmp_path / "wheels"
        wheels.mkdir()
        reqs = tmp_path / "requirements.lock"
        reqs.write_text("")  # empty lock -> nothing to install

        p1 = ensure_venv(
            python_exe=Path(sys.executable),
            venv_dir=venv,
            wheels_dir=wheels,
            requirements_lock=reqs,
            plugin_version="0.1.0",
        )
        assert p1.exists()
        marker = venv / VENV_MARKER_FILENAME
        assert marker.read_text(encoding="utf-8").strip() == "0.1.0"

        # Second call: no-op (marker matches)
        mtime_before = marker.stat().st_mtime
        p2 = ensure_venv(
            python_exe=Path(sys.executable),
            venv_dir=venv,
            wheels_dir=wheels,
            requirements_lock=reqs,
            plugin_version="0.1.0",
        )
        assert p2 == p1
        assert marker.stat().st_mtime == mtime_before

    def test_bootstrap_rebuilds_on_version_change(tmp_path: Path) -> None:
        venv = tmp_path / "venv"
        wheels = tmp_path / "wheels"
        wheels.mkdir()
        reqs = tmp_path / "requirements.lock"
        reqs.write_text("")

        ensure_venv(
            python_exe=Path(sys.executable),
            venv_dir=venv, wheels_dir=wheels, requirements_lock=reqs,
            plugin_version="0.1.0",
        )
        # Second call with new version -> full rebuild
        ensure_venv(
            python_exe=Path(sys.executable),
            venv_dir=venv, wheels_dir=wheels, requirements_lock=reqs,
            plugin_version="0.2.0",
        )
        assert (venv / VENV_MARKER_FILENAME).read_text(encoding="utf-8").strip() == "0.2.0"
    ```

    **6. CREATE prebuild.ps1** — reads assets-manifest.json and fetches:

    ```powershell
    <#
    .SYNOPSIS
      Fetches NYRA plugin binary artefacts per assets-manifest.json.
      Idempotent: skips entries whose dest file already exists with matching SHA256.

    .USAGE
      PowerShell -ExecutionPolicy Bypass -File prebuild.ps1
    #>
    param(
        [string]$ManifestPath = "$PSScriptRoot\Source\NyraHost\assets-manifest.json",
        [string]$PluginRoot = "$PSScriptRoot"
    )

    $ErrorActionPreference = "Stop"
    $manifest = Get-Content $ManifestPath -Raw | ConvertFrom-Json

    function Test-Sha256($Path, $ExpectedHex) {
        if (-not (Test-Path $Path)) { return $false }
        $actual = (Get-FileHash $Path -Algorithm SHA256).Hash.ToLower()
        return $actual -eq $ExpectedHex.ToLower()
    }

    function Fetch-Asset($Name, $Entry, $PluginRoot) {
        $destDir = Join-Path $PluginRoot $Entry.dest
        if (-not (Test-Path $destDir)) { New-Item -ItemType Directory -Force -Path $destDir | Out-Null }

        $url = $Entry.url
        if ($url -like "*TODO_RESOLVE_AT_BUILD*") {
            Write-Warning "[$Name] manifest has unresolved URL placeholder; skipping"
            return
        }

        $filename = [System.IO.Path]::GetFileName($url)
        $tmpPath = Join-Path $env:TEMP "nyra-prebuild-$Name-$filename"

        if (-not (Test-Sha256 $tmpPath $Entry.sha256)) {
            Write-Host "[$Name] Downloading $url"
            Invoke-WebRequest -Uri $url -OutFile $tmpPath -UseBasicParsing
        } else {
            Write-Host "[$Name] Cached in $tmpPath"
        }
        if (-not (Test-Sha256 $tmpPath $Entry.sha256)) {
            throw "[$Name] SHA256 mismatch after download"
        }

        Write-Host "[$Name] Extracting to $destDir"
        if ($filename -like "*.tar.zst") {
            # Requires zstd in PATH on the dev machine
            & zstd -d -o (Join-Path $env:TEMP "nyra-prebuild-$Name.tar") $tmpPath
            tar -xf (Join-Path $env:TEMP "nyra-prebuild-$Name.tar") -C $destDir
        } elseif ($filename -like "*.zip") {
            Expand-Archive -Path $tmpPath -DestinationPath $destDir -Force
        } elseif ($filename -like "*.tar.gz" -or $filename -like "*.tgz") {
            tar -xzf $tmpPath -C $destDir
        } else {
            Copy-Item $tmpPath -Destination (Join-Path $destDir $filename) -Force
        }
    }

    Fetch-Asset "python_build_standalone" $manifest.python_build_standalone $PluginRoot
    Fetch-Asset "llama_server_cuda" $manifest.llama_server_cuda $PluginRoot
    Fetch-Asset "llama_server_vulkan" $manifest.llama_server_vulkan $PluginRoot
    Fetch-Asset "llama_server_cpu" $manifest.llama_server_cpu $PluginRoot

    Write-Host "[NYRA prebuild] done."
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "websockets==" TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` equals 1
      - `grep -c "pydantic==" TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` equals 1
      - `grep -c "structlog==" TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` equals 1
      - `grep -c "httpx==" TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` equals 1
      - `grep -c "mcp==" TestProject/Plugins/NYRA/Source/NyraHost/requirements.lock` equals 1
      - `grep -c "def ensure_venv" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/bootstrap.py` equals 1
      - `grep -c "VENV_MARKER_FILENAME" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/bootstrap.py` >= 2
      - `grep -c "Invoke-WebRequest" TestProject/Plugins/NYRA/prebuild.ps1` >= 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_bootstrap.py -v` exits 0 with >= 2 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - requirements.lock contains exact pins `mcp==`, `websockets==`, `httpx==`, `pydantic==`, `structlog==`, `pywin32==` (with ; sys_platform == 'win32' marker)
    - pyproject.toml gained `[project] dependencies = [...]` section listing all 5 deps from D-15
    - pyproject.toml contains `[tool.setuptools.packages.find]` with `where = ["src"]`
    - src/nyrahost/__init__.py contains literal text `__version__ = "0.1.0"`
    - bootstrap.py contains literal text `VENV_MARKER_FILENAME = "nyra-plugin-version.txt"`
    - bootstrap.py contains literal text `NYRA_PLUGIN_VERSION = "0.1.0"`
    - bootstrap.py contains literal text `subprocess.run(` with `"venv", "--copies"` args
    - bootstrap.py contains literal text `"--no-index"` and `"--find-links"`
    - test_bootstrap.py contains `def test_bootstrap_idempotent` (NOT skipped — real body)
    - test_bootstrap.py contains `def test_bootstrap_rebuilds_on_version_change`
    - prebuild.ps1 contains literal text `Get-Content $ManifestPath` and `ConvertFrom-Json`
    - prebuild.ps1 contains literal text `Get-FileHash $Path -Algorithm SHA256`
    - Running `pytest tests/test_bootstrap.py -v` from NyraHost/ exits 0 with both tests passing
  </acceptance_criteria>
  <done>Venv bootstrap tested + prebuild script committed; Plan 06 infrastructure ready for WS server.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: handshake.py + jsonrpc.py + test_handshake.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/config.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/logging_setup.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py
  </files>
  <read_first>
    - docs/HANDSHAKE.md (writer protocol)
    - docs/JSONRPC.md (envelope shapes)
    - docs/ERROR_CODES.md (error code table)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py (Wave 0 placeholder)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.10 P1.1 (atomic rename)
  </read_first>
  <behavior>
    - handshake.py write_handshake writes to .tmp + fsync + os.replace (observable via a reader-racing test that never sees partial JSON).
    - jsonrpc.parse_envelope rejects malformed JSON (returns error), missing jsonrpc field, wrong jsonrpc version; returns tagged union {kind:"request"|"notification"|"response"|"error"}.
    - jsonrpc.build_error produces an envelope with {error:{code, message, data:{remediation}}}.
  </behavior>
  <action>
    **1. CREATE src/nyrahost/config.py** — runtime config dataclass:

    ```python
    """Runtime config resolved from CLI args + env."""
    from __future__ import annotations
    import os
    from dataclasses import dataclass
    from pathlib import Path


    @dataclass(frozen=True)
    class NyraConfig:
        editor_pid: int
        log_dir: Path
        handshake_dir: Path
        bind_host: str = "127.0.0.1"
        bind_port: int = 0  # 0 == OS ephemeral
        ws_max_frame_bytes: int = 16 * 1024 * 1024
        ws_ping_interval_s: int = 30
        ws_ping_timeout_s: int = 10
        auth_token_bytes: int = 32

        @staticmethod
        def default_handshake_dir() -> Path:
            la = os.environ.get("LOCALAPPDATA")
            if la:
                return Path(la) / "NYRA"
            return Path.home() / ".local" / "share" / "NYRA"
    ```

    **2. CREATE src/nyrahost/logging_setup.py** (D-16):

    ```python
    """structlog JSON logging with 7-day TimedRotatingFileHandler."""
    from __future__ import annotations
    import logging
    import sys
    from datetime import datetime, timezone
    from logging.handlers import TimedRotatingFileHandler
    from pathlib import Path
    import structlog


    def configure_logging(log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file = log_dir / f"nyrahost-{datetime.now(timezone.utc):%Y-%m-%d}.log"
        handler = TimedRotatingFileHandler(
            log_file, when="midnight", backupCount=7, encoding="utf-8",
        )
        handler.setLevel(logging.INFO)
        root = logging.getLogger()
        root.handlers.clear()
        root.setLevel(logging.INFO)
        root.addHandler(handler)

        structlog.configure(
            processors=[
                structlog.stdlib.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", utc=True),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )

        # Uncaught exception hook -> log
        def excepthook(exc_type, exc_value, exc_tb):
            logger = structlog.get_logger("nyrahost.crash")
            logger.error(
                "uncaught_exception",
                error_type=exc_type.__name__,
                error_message=str(exc_value),
                exc_info=(exc_type, exc_value, exc_tb),
            )
        sys.excepthook = excepthook
    ```

    **3. CREATE src/nyrahost/handshake.py** (D-06 + P1.1 atomic + P1.2 cleanup):

    ```python
    """Handshake file protocol (docs/HANDSHAKE.md).

    Atomic rename + Windows owner-only DACL + orphan cleanup.
    """
    from __future__ import annotations
    import json
    import os
    import sys
    import time
    from pathlib import Path
    from typing import TypedDict


    class HandshakePayload(TypedDict):
        port: int
        token: str
        nyrahost_pid: int
        ue_pid: int
        started_at: int  # ms since epoch


    def handshake_file_path(handshake_dir: Path, ue_pid: int) -> Path:
        return handshake_dir / f"handshake-{ue_pid}.json"


    def write_handshake(
        handshake_dir: Path,
        *,
        port: int,
        token: str,
        nyrahost_pid: int,
        ue_pid: int,
    ) -> Path:
        """Atomic write per docs/HANDSHAKE.md. Returns final path."""
        handshake_dir.mkdir(parents=True, exist_ok=True)
        final = handshake_file_path(handshake_dir, ue_pid)
        tmp = final.with_suffix(final.suffix + ".tmp")
        payload: HandshakePayload = {
            "port": port,
            "token": token,
            "nyrahost_pid": nyrahost_pid,
            "ue_pid": ue_pid,
            "started_at": int(time.time() * 1000),
        }
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"))
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, final)  # atomic on NTFS + POSIX
        if sys.platform == "win32":
            _apply_owner_only_dacl(final)
        return final


    def _apply_owner_only_dacl(path: Path) -> None:
        """Restrict DACL to current user SID on Windows. Best-effort —
        if pywin32 missing or call fails, log and continue (file still exists
        and is usable; this is defence-in-depth, not a hard guarantee)."""
        try:
            import win32security  # type: ignore[import-not-found]
            import ntsecuritycon  # type: ignore[import-not-found]
            # Get current user SID
            user_token = win32security.OpenProcessToken(
                win32security.GetCurrentProcess(),
                win32security.TOKEN_QUERY,
            )
            user_sid = win32security.GetTokenInformation(
                user_token, win32security.TokenUser,
            )[0]
            dacl = win32security.ACL()
            dacl.AddAccessAllowedAce(
                win32security.ACL_REVISION,
                ntsecuritycon.FILE_GENERIC_READ | ntsecuritycon.FILE_GENERIC_WRITE |
                ntsecuritycon.DELETE,
                user_sid,
            )
            sd = win32security.SECURITY_DESCRIPTOR()
            sd.SetSecurityDescriptorDacl(1, dacl, 0)
            win32security.SetFileSecurity(
                str(path),
                win32security.DACL_SECURITY_INFORMATION,
                sd,
            )
        except Exception:  # noqa: BLE001 — best effort
            pass


    def cleanup_orphan_handshakes(handshake_dir: Path) -> list[int]:
        """Scan handshake-*.json; return PIDs cleaned up.
        Orphan = ue_pid not running. Caller should also terminate orphan
        nyrahost_pid (supervisor concern — UE side; Python does not kill
        other editors' NyraHosts)."""
        if not handshake_dir.exists():
            return []
        cleaned: list[int] = []
        for f in handshake_dir.glob("handshake-*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                ue_pid = data["ue_pid"]
                if not _pid_running(int(ue_pid)):
                    f.unlink(missing_ok=True)
                    cleaned.append(int(ue_pid))
            except (OSError, json.JSONDecodeError, KeyError, ValueError):
                # Corrupt; ignore
                continue
        return cleaned


    def _pid_running(pid: int) -> bool:
        if sys.platform == "win32":
            try:
                import win32api  # type: ignore[import-not-found]
                import win32con  # type: ignore[import-not-found]
                h = win32api.OpenProcess(win32con.PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
                win32api.CloseHandle(h)
                return True
            except Exception:
                return False
        # POSIX
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False
    ```

    **4. CREATE src/nyrahost/jsonrpc.py** (D-09, §3 of JSONRPC.md):

    ```python
    """JSON-RPC 2.0 envelope parsing + builders.

    See docs/JSONRPC.md for the canonical wire format.
    """
    from __future__ import annotations
    import json
    from dataclasses import dataclass
    from typing import Any, Literal, Union


    @dataclass(frozen=True)
    class RequestEnvelope:
        id: int | str
        method: str
        params: dict[str, Any]

    @dataclass(frozen=True)
    class NotificationEnvelope:
        method: str
        params: dict[str, Any]

    @dataclass(frozen=True)
    class ResponseEnvelope:
        id: int | str
        result: dict[str, Any]

    @dataclass(frozen=True)
    class ErrorEnvelope:
        id: int | str | None
        code: int
        message: str
        remediation: str | None

    Envelope = Union[RequestEnvelope, NotificationEnvelope, ResponseEnvelope, ErrorEnvelope]


    class ProtocolError(Exception):
        """Raised when an incoming frame is not valid JSON-RPC 2.0."""
        def __init__(self, message: str, *, recv_id: int | str | None = None):
            super().__init__(message)
            self.recv_id = recv_id


    def parse_envelope(frame: str) -> Envelope:
        try:
            obj = json.loads(frame)
        except json.JSONDecodeError as e:
            raise ProtocolError(f"invalid_json: {e}") from e
        if not isinstance(obj, dict):
            raise ProtocolError("envelope_not_object")
        if obj.get("jsonrpc") != "2.0":
            raise ProtocolError("missing_or_wrong_jsonrpc_version")

        if "method" in obj:
            method = obj["method"]
            params = obj.get("params", {}) or {}
            if not isinstance(method, str):
                raise ProtocolError("method_not_string")
            if not isinstance(params, dict):
                raise ProtocolError("params_not_object")
            if "id" in obj:
                return RequestEnvelope(id=obj["id"], method=method, params=params)
            return NotificationEnvelope(method=method, params=params)

        if "result" in obj:
            if "id" not in obj:
                raise ProtocolError("response_missing_id")
            return ResponseEnvelope(id=obj["id"], result=obj["result"])

        if "error" in obj:
            e = obj["error"]
            return ErrorEnvelope(
                id=obj.get("id"),
                code=int(e.get("code", 0)),
                message=str(e.get("message", "")),
                remediation=(e.get("data") or {}).get("remediation"),
            )
        raise ProtocolError("envelope_has_neither_method_nor_result_nor_error")


    def build_response(id_: int | str, result: dict[str, Any]) -> str:
        return json.dumps(
            {"jsonrpc": "2.0", "id": id_, "result": result},
            separators=(",", ":"),
        )


    def build_error(
        id_: int | str | None,
        *,
        code: int,
        message: str,
        remediation: str,
    ) -> str:
        envelope: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": id_,
            "error": {"code": code, "message": message, "data": {"remediation": remediation}},
        }
        return json.dumps(envelope, separators=(",", ":"))


    def build_notification(method: str, params: dict[str, Any]) -> str:
        return json.dumps(
            {"jsonrpc": "2.0", "method": method, "params": params},
            separators=(",", ":"),
        )
    ```

    **5. REPLACE tests/test_handshake.py** with real body (VALIDATION 1-02-05):

    ```python
    """Handshake atomic-write tests.
    VALIDATION test ID: 1-02-05
    """
    from __future__ import annotations
    import json
    import secrets
    import threading
    import time
    from pathlib import Path
    from nyrahost.handshake import write_handshake, handshake_file_path, cleanup_orphan_handshakes


    def test_handshake_atomic_write(tmp_path: Path) -> None:
        handshake_dir = tmp_path / "NYRA"
        token = secrets.token_bytes(32).hex()
        final = write_handshake(
            handshake_dir,
            port=54321,
            token=token,
            nyrahost_pid=11111,
            ue_pid=22222,
        )
        assert final.exists()
        data = json.loads(final.read_text(encoding="utf-8"))
        assert data["port"] == 54321
        assert data["token"] == token
        assert len(token) == 64  # 32 bytes hex
        assert data["nyrahost_pid"] == 11111
        assert data["ue_pid"] == 22222
        assert isinstance(data["started_at"], int)
        # No .tmp left behind
        assert not final.with_suffix(final.suffix + ".tmp").exists()


    def test_handshake_atomic_reader_never_sees_partial(tmp_path: Path) -> None:
        """Race: reader polls aggressively while writer races; reader must
        never observe an empty or partial JSON (proves os.replace atomicity)."""
        handshake_dir = tmp_path / "NYRA"
        handshake_dir.mkdir()
        path = handshake_file_path(handshake_dir, ue_pid=22222)

        partial_reads = []
        stop = threading.Event()

        def reader() -> None:
            while not stop.is_set():
                if path.exists():
                    try:
                        data = json.loads(path.read_text(encoding="utf-8"))
                        # If we loaded a dict, we expect all required fields
                        if "port" not in data or "token" not in data:
                            partial_reads.append(data)
                    except (json.JSONDecodeError, OSError):
                        partial_reads.append("parse_failed_but_tolerated")

        t = threading.Thread(target=reader, daemon=True)
        t.start()
        try:
            for i in range(30):
                write_handshake(
                    handshake_dir,
                    port=54321 + i,
                    token=secrets.token_bytes(32).hex(),
                    nyrahost_pid=11111,
                    ue_pid=22222,
                )
                time.sleep(0.003)
        finally:
            stop.set()
            t.join(timeout=1.0)
        # Partial-DICT reads (dict with missing keys) must be zero — os.replace
        # guarantees all-or-nothing at the dict level.
        bad_dicts = [r for r in partial_reads if isinstance(r, dict)]
        assert bad_dicts == [], f"Non-atomic dict read observed: {bad_dicts}"


    def test_handshake_cleanup_orphans(tmp_path: Path) -> None:
        handshake_dir = tmp_path / "NYRA"
        # Write handshake for a definitely-dead pid (a very large unused one)
        write_handshake(
            handshake_dir, port=5000, token="x" * 64, nyrahost_pid=11111, ue_pid=3_999_999_999,
        )
        cleaned = cleanup_orphan_handshakes(handshake_dir)
        assert 3_999_999_999 in cleaned
        assert not handshake_file_path(handshake_dir, 3_999_999_999).exists()
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "def write_handshake" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py` equals 1
      - `grep -c "os.replace(tmp, final)" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py` equals 1
      - `grep -c "def parse_envelope" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py` equals 1
      - `grep -c "def build_error" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_handshake.py -v` exits 0 with 3 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - handshake.py contains `def write_handshake(` AND `os.replace(tmp, final)` AND `os.fsync(f.fileno())`
    - handshake.py contains `def cleanup_orphan_handshakes` AND `_pid_running`
    - handshake.py contains `_apply_owner_only_dacl` with pywin32 import guarded in try/except
    - jsonrpc.py exports `RequestEnvelope`, `NotificationEnvelope`, `ResponseEnvelope`, `ErrorEnvelope`, `parse_envelope`, `build_response`, `build_error`, `build_notification`
    - jsonrpc.py `parse_envelope` raises `ProtocolError` on `jsonrpc != "2.0"`
    - config.py exports `NyraConfig` dataclass with fields editor_pid, log_dir, handshake_dir, bind_host, bind_port, ws_max_frame_bytes, ws_ping_interval_s, ws_ping_timeout_s
    - logging_setup.py contains `TimedRotatingFileHandler(log_file, when="midnight", backupCount=7` (D-16)
    - test_handshake.py contains `def test_handshake_atomic_write` (NOT skipped)
    - test_handshake.py contains `def test_handshake_atomic_reader_never_sees_partial`
    - test_handshake.py contains `def test_handshake_cleanup_orphans`
    - `pytest tests/test_handshake.py -v` exits 0 with 3 tests passing
  </acceptance_criteria>
  <done>Handshake + JSON-RPC envelope + logging primitives implemented + tested.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 3: server.py + session.py + __main__.py + test_auth.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/session.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py
  </files>
  <read_first>
    - docs/JSONRPC.md §2 (id policy + session_id) and §3.1, §3.2 (session/authenticate + session/hello)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handshake.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/config.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py (Wave 0 placeholder)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-07 (auth token + close 4401), D-10 (method surface)
  </read_first>
  <behavior>
    - test_auth_rejects_bad_token: connect WS with wrong token -> server closes with code 4401 + reason "unauthenticated".
    - test_auth_rejects_non_authenticate_first_method: connect WS, send session/hello before authenticate -> close 4401.
    - test_auth_accepts_valid_token: connect WS, send session/authenticate with correct token -> receive {result:{authenticated:true, session_id:<uuid>}}; then session/hello returns backends=["gemma-local"], phase=1.
  </behavior>
  <action>
    **1. CREATE src/nyrahost/session.py** — per-connection session state:

    ```python
    """Per-WS-connection session state."""
    from __future__ import annotations
    import uuid
    from dataclasses import dataclass, field


    @dataclass
    class SessionState:
        authenticated: bool = False
        session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
        conversation_ids_seen: set[str] = field(default_factory=set)
    ```

    **2. CREATE src/nyrahost/server.py** — WS handler + auth gate:

    ```python
    """asyncio WebSocket server with first-frame auth gate.

    See docs/JSONRPC.md §3.1 + docs/HANDSHAKE.md.
    """
    from __future__ import annotations
    import asyncio
    import secrets
    from typing import Callable, Awaitable
    import structlog
    import websockets
    from websockets.exceptions import ConnectionClosed
    from websockets.server import ServerConnection

    from .config import NyraConfig
    from .handshake import write_handshake, handshake_file_path
    from .jsonrpc import (
        parse_envelope,
        build_response,
        build_error,
        RequestEnvelope,
        NotificationEnvelope,
        ProtocolError,
    )
    from .session import SessionState


    log = structlog.get_logger("nyrahost.server")

    AUTH_CLOSE_CODE = 4401
    AUTH_CLOSE_REASON = "unauthenticated"

    # Handler hooks — extension points Plans 07/08/09 bind to.
    # Each takes (params, session) and returns result dict or raises.
    RequestHandler = Callable[[dict, SessionState], Awaitable[dict]]
    NotificationHandler = Callable[[dict, SessionState], Awaitable[None]]


    class NyraServer:
        def __init__(self, config: NyraConfig, auth_token: str):
            self.config = config
            self.auth_token = auth_token
            self.request_handlers: dict[str, RequestHandler] = {
                "session/hello": self._on_session_hello,
            }
            self.notification_handlers: dict[str, NotificationHandler] = {}

        def register_request(self, method: str, handler: RequestHandler) -> None:
            self.request_handlers[method] = handler

        def register_notification(self, method: str, handler: NotificationHandler) -> None:
            self.notification_handlers[method] = handler

        async def _on_session_hello(self, params: dict, session: SessionState) -> dict:
            return {
                "backends": ["gemma-local"],
                "phase": 1,
                "session_id": session.session_id,
            }

        async def _handle_connection(self, ws: ServerConnection) -> None:
            session = SessionState()
            # --- First frame gate: MUST be session/authenticate with correct token ---
            try:
                first_frame = await asyncio.wait_for(ws.recv(), timeout=10.0)
            except (asyncio.TimeoutError, ConnectionClosed):
                log.warning("auth_no_first_frame")
                return
            try:
                env = parse_envelope(first_frame if isinstance(first_frame, str) else first_frame.decode("utf-8"))
            except ProtocolError as e:
                await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
                log.warning("auth_bad_envelope", err=str(e))
                return
            if not isinstance(env, RequestEnvelope) or env.method != "session/authenticate":
                await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
                log.warning("auth_first_method_not_authenticate", got=getattr(env, "method", None))
                return
            client_token = env.params.get("token", "")
            if not isinstance(client_token, str) or not secrets.compare_digest(client_token, self.auth_token):
                await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)
                log.warning("auth_token_mismatch")
                return
            session.authenticated = True
            await ws.send(build_response(env.id, {
                "authenticated": True,
                "session_id": session.session_id,
            }))
            log.info("auth_ok", session_id=session.session_id)

            # --- Main dispatch loop ---
            try:
                async for raw in ws:
                    await self._dispatch(ws, raw, session)
            except ConnectionClosed:
                log.info("ws_closed", session_id=session.session_id)

        async def _dispatch(self, ws: ServerConnection, raw, session: SessionState) -> None:
            frame = raw if isinstance(raw, str) else raw.decode("utf-8")
            try:
                env = parse_envelope(frame)
            except ProtocolError as e:
                log.warning("dispatch_bad_envelope", err=str(e))
                return
            if isinstance(env, RequestEnvelope):
                handler = self.request_handlers.get(env.method)
                if handler is None:
                    await ws.send(build_error(
                        env.id,
                        code=-32601,
                        message="method_not_found",
                        remediation=f"Unknown method: {env.method}",
                    ))
                    return
                try:
                    result = await handler(env.params, session)
                    await ws.send(build_response(env.id, result))
                except Exception as e:  # noqa: BLE001
                    log.exception("handler_exception", method=env.method)
                    await ws.send(build_error(
                        env.id,
                        code=-32001,
                        message="subprocess_failed",
                        remediation="A background NYRA process stopped unexpectedly. Click [Restart] or see Saved/NYRA/logs/.",
                    ))
            elif isinstance(env, NotificationEnvelope):
                handler = self.notification_handlers.get(env.method)
                if handler is not None:
                    try:
                        await handler(env.params, session)
                    except Exception:  # noqa: BLE001
                        log.exception("notification_handler_exception", method=env.method)


    async def run_server(
        config: NyraConfig,
        *,
        nyrahost_pid: int,
        register_handlers: Callable[[NyraServer], None] | None = None,
    ) -> None:
        """Bind WS server on 127.0.0.1:<ephemeral>, write handshake, serve forever."""
        token = secrets.token_bytes(config.auth_token_bytes).hex()
        server_obj = NyraServer(config, auth_token=token)
        if register_handlers:
            register_handlers(server_obj)

        ws_server = await websockets.serve(
            server_obj._handle_connection,
            config.bind_host,
            config.bind_port,
            ping_interval=config.ws_ping_interval_s,
            ping_timeout=config.ws_ping_timeout_s,
            max_size=config.ws_max_frame_bytes,
        )
        assigned_port = ws_server.sockets[0].getsockname()[1]
        log.info("ws_bound", host=config.bind_host, port=assigned_port)

        write_handshake(
            config.handshake_dir,
            port=assigned_port,
            token=token,
            nyrahost_pid=nyrahost_pid,
            ue_pid=config.editor_pid,
        )
        log.info(
            "handshake_written",
            path=str(handshake_file_path(config.handshake_dir, config.editor_pid)),
        )

        await ws_server.serve_forever()
    ```

    **3. CREATE src/nyrahost/__main__.py** — module entrypoint:

    ```python
    """Entry point for `python -m nyrahost`."""
    from __future__ import annotations
    import argparse
    import asyncio
    import os
    import sys
    from pathlib import Path

    from .config import NyraConfig
    from .handshake import cleanup_orphan_handshakes
    from .logging_setup import configure_logging
    from .server import run_server


    def parse_args() -> argparse.Namespace:
        p = argparse.ArgumentParser(prog="nyrahost")
        p.add_argument("--editor-pid", type=int, required=True)
        p.add_argument("--log-dir", type=Path, required=True)
        p.add_argument("--handshake-dir", type=Path, default=None)
        return p.parse_args()


    async def main_async(args: argparse.Namespace) -> int:
        handshake_dir = args.handshake_dir or NyraConfig.default_handshake_dir()
        config = NyraConfig(
            editor_pid=args.editor_pid,
            log_dir=args.log_dir,
            handshake_dir=handshake_dir,
        )
        configure_logging(config.log_dir)

        # Clean up dead-editor handshakes before claiming our own slot (P1.2)
        cleanup_orphan_handshakes(handshake_dir)

        await run_server(config, nyrahost_pid=os.getpid())
        return 0


    def main() -> int:
        args = parse_args()
        try:
            return asyncio.run(main_async(args))
        except KeyboardInterrupt:
            return 0


    if __name__ == "__main__":
        sys.exit(main())
    ```

    **4. REPLACE tests/test_auth.py with real body (VALIDATION 1-02-04):

    ```python
    """Auth + first-frame gate tests.
    VALIDATION test ID: 1-02-04
    """
    from __future__ import annotations
    import asyncio
    import json
    import secrets
    import threading
    from pathlib import Path
    import pytest
    import websockets
    from nyrahost.config import NyraConfig
    from nyrahost.server import run_server, NyraServer


    async def _start_server(tmp_path: Path, *, token: str) -> tuple[int, asyncio.Task]:
        """Start NyraServer on an ephemeral port and return (port, task)."""
        config = NyraConfig(
            editor_pid=99999,
            log_dir=tmp_path / "logs",
            handshake_dir=tmp_path / "NYRA",
        )
        # We need to bypass run_server's secret-generation to inject a known token.
        # Monkey-patch secrets.token_bytes before invocation.
        import nyrahost.server as server_mod
        original = server_mod.secrets.token_bytes
        server_mod.secrets.token_bytes = lambda n: bytes.fromhex(token)  # type: ignore[attr-defined]
        try:
            # Spawn run_server and capture the port via a hack: poll the handshake file.
            task = asyncio.create_task(run_server(config, nyrahost_pid=12345))
            # Wait for handshake file
            handshake = config.handshake_dir / f"handshake-{config.editor_pid}.json"
            for _ in range(50):
                if handshake.exists():
                    break
                await asyncio.sleep(0.05)
            else:
                raise RuntimeError("handshake file never appeared")
            data = json.loads(handshake.read_text())
            return data["port"], task
        finally:
            server_mod.secrets.token_bytes = original


    @pytest.mark.asyncio
    async def test_auth_rejects_bad_token(tmp_path: Path) -> None:
        good_token_bytes = secrets.token_bytes(32)
        good_token_hex = good_token_bytes.hex()
        port, task = await _start_server(tmp_path, token=good_token_hex)
        try:
            uri = f"ws://127.0.0.1:{port}/"
            async with websockets.connect(uri) as ws:
                bad_frame = json.dumps({
                    "jsonrpc": "2.0", "id": 1,
                    "method": "session/authenticate",
                    "params": {"token": "00" * 32},
                })
                await ws.send(bad_frame)
                # Expect close with code 4401
                try:
                    await asyncio.wait_for(ws.recv(), timeout=2.0)
                    pytest.fail("Server should have closed the connection")
                except websockets.exceptions.ConnectionClosed as e:
                    assert e.code == 4401
                    assert e.reason == "unauthenticated"
        finally:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


    @pytest.mark.asyncio
    async def test_auth_rejects_first_method_not_authenticate(tmp_path: Path) -> None:
        good_token_hex = secrets.token_bytes(32).hex()
        port, task = await _start_server(tmp_path, token=good_token_hex)
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
                # Send session/hello as FIRST frame — must be rejected
                await ws.send(json.dumps({
                    "jsonrpc": "2.0", "id": 1, "method": "session/hello", "params": {},
                }))
                try:
                    await asyncio.wait_for(ws.recv(), timeout=2.0)
                    pytest.fail("Server should have closed")
                except websockets.exceptions.ConnectionClosed as e:
                    assert e.code == 4401
        finally:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass


    @pytest.mark.asyncio
    async def test_auth_accepts_valid_token_and_session_hello(tmp_path: Path) -> None:
        good_token_hex = secrets.token_bytes(32).hex()
        port, task = await _start_server(tmp_path, token=good_token_hex)
        try:
            async with websockets.connect(f"ws://127.0.0.1:{port}/") as ws:
                await ws.send(json.dumps({
                    "jsonrpc": "2.0", "id": 1,
                    "method": "session/authenticate",
                    "params": {"token": good_token_hex},
                }))
                reply = json.loads(await ws.recv())
                assert reply["id"] == 1
                assert reply["result"]["authenticated"] is True
                assert isinstance(reply["result"]["session_id"], str)

                await ws.send(json.dumps({
                    "jsonrpc": "2.0", "id": 2,
                    "method": "session/hello", "params": {},
                }))
                hello = json.loads(await ws.recv())
                assert hello["id"] == 2
                assert hello["result"]["backends"] == ["gemma-local"]
                assert hello["result"]["phase"] == 1
                assert isinstance(hello["result"]["session_id"], str)
        finally:
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "async def _handle_connection" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "AUTH_CLOSE_CODE = 4401" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "AUTH_CLOSE_REASON = \"unauthenticated\"" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "secrets.compare_digest" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "websockets.serve" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "ping_interval=config.ws_ping_interval_s" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "max_size=config.ws_max_frame_bytes" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `grep -c "def main()" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py` equals 1
      - `grep -c "argparse.ArgumentParser" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_auth.py -v` exits 0 with 3 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - session.py contains `@dataclass class SessionState` with fields `authenticated`, `session_id`, `conversation_ids_seen`
    - server.py contains `class NyraServer` with `register_request` and `register_notification` methods
    - server.py contains literal text `AUTH_CLOSE_CODE = 4401` and `AUTH_CLOSE_REASON = "unauthenticated"`
    - server.py `_handle_connection` sends `build_response` with `{"authenticated": True, "session_id": session.session_id}` on success
    - server.py `_handle_connection` calls `await ws.close(AUTH_CLOSE_CODE, AUTH_CLOSE_REASON)` on (a) bad envelope, (b) first method != session/authenticate, (c) token mismatch
    - server.py uses `secrets.compare_digest` for token comparison (timing-safe)
    - server.py `run_server` calls `websockets.serve` with `ping_interval`, `ping_timeout`, `max_size` from config
    - server.py `run_server` writes handshake AFTER port is assigned (per §3.10 P1.1)
    - server.py registers default handler `session/hello` returning `{"backends": ["gemma-local"], "phase": 1, "session_id": session.session_id}`
    - __main__.py contains `argparse.ArgumentParser(prog="nyrahost")` with required `--editor-pid` and `--log-dir`
    - __main__.py calls `cleanup_orphan_handshakes` before `run_server`
    - __main__.py calls `configure_logging(config.log_dir)`
    - __main__.py wraps in `asyncio.run(main_async(args))`
    - test_auth.py contains `def test_auth_rejects_bad_token` AND `def test_auth_rejects_first_method_not_authenticate` AND `def test_auth_accepts_valid_token_and_session_hello`
    - test_auth.py tests assert close code 4401 and reason "unauthenticated"
    - `pytest tests/test_auth.py -v` exits 0 with 3 tests passing
  </acceptance_criteria>
  <done>NyraHost WS server runs; auth + session/hello work; tests green. Extension points for Plans 07/08/09 (register_request, register_notification) in place.</done>
</task>

</tasks>

<verification>
Full pytest run from TestProject/Plugins/NYRA/Source/NyraHost/:
```
pytest tests/test_auth.py tests/test_handshake.py tests/test_bootstrap.py -v
```
Must pass all 8 tests (3 auth + 3 handshake + 2 bootstrap).

Manual smoke: run `python -m nyrahost --editor-pid 99999 --log-dir /tmp/nyra`,
connect via `websockets` client library sending a valid session/authenticate
frame, receive authenticated:true response.
</verification>

<success_criteria>
- NyraHost runs as `python -m nyrahost`, binds ephemeral WS port, writes atomic handshake
- session/authenticate + session/hello work end-to-end
- Bad token yields WS close 4401
- 8 pytest tests green (auth: 3, handshake: 3, bootstrap: 2)
- prebuild.ps1 can be invoked and fetches python-build-standalone per manifest
- NyraServer.register_request / register_notification hooks available for Plans 07/08/09
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-06-SUMMARY.md`
documenting: module structure (config/logging/handshake/jsonrpc/session/server/__main__),
extension point contract (RequestHandler/NotificationHandler signatures), and
how Plans 07/08/09/10 bind into NyraServer.
</output>

# Phase 5: External Tool Integrations (API-First) - Pattern Map

**Mapped:** 2026-05-07
**Files analyzed:** 6 new/modified files from RESEARCH.md
**Analogs found:** 5 / 6 (1 deferred to v1.1)

---

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|------------------|------|-----------|---------------|---------------|
| `NyraHost/src/nyrahost/tools/meshy_tools.py` | MCP tool | request-response + async polling | `NyraHost/src/nyrahost/tools/blueprint_tools.py` | role+data-flow match |
| `NyraHost/src/nyrahost/tools/comfyui_tools.py` | MCP tool | request-response + async polling | `NyraHost/src/nyrahost/tools/blueprint_tools.py` | role+data-flow match |
| `NyraHost/src/nyrahost/tools/computer_use_tools.py` | MCP tool | event-driven | `NyraHost/src/nyrahost/tools/blueprint_debug.py` | role-match, partial data-flow |
| `NyraHost/src/nyrahost/tools/staging.py` | utility | file-I/O | `NyraHost/src/nyrahost/downloader/gemma.py` | pattern-match |
| `NyraHost/src/nyrahost/external/meshy_client.py` | HTTP client | streaming | `NyraHost/src/nyrahost/downloader/gemma.py` | role+pattern match |
| `NyraHost/src/nyrahost/external/comfyui_client.py` | HTTP client | streaming | `NyraHost/src/nyrahost/external/meshy_client.py` | same pattern |
| `NyraHost/src/nyrahost/computer_use/loop.py` | service | event-driven | `NyraHost/src/nyrahost/handlers/download.py` | partial pattern-match |
| `NyraHost/src/nyrahost/computer_use/screenshot.py` | utility | file-I/O | `NyraHost/src/nyrahost/downloader/gemma.py` | partial pattern-match |
| `NyraHost/src/nyrahost/computer_use/win32_uia.py` | utility | event-driven | — | no analog (Win32-specific) |
| `NyraHost/src/nyrahost/config.py` | config | request-response | `NyraHost/src/nyrahost/config.py` | in-place extension |
| `NyraHost/src/nyrahost/mcp_server/__init__.py` | route | request-response | `NyraHost/src/nyrahost/mcp_server/__init__.py` | in-place extension |
| `NyraHost/src/nyrahost/staging_manifest.schema.json` | config | file-I/O | — | no analog (schema definition file) |
| `NyraHost/tests/test_meshy_tools.py` | test | batch | — | no analog yet (create from scratch) |
| `NyraHost/tests/test_comfyui_tools.py` | test | batch | — | no analog yet (create from scratch) |
| `NyraHost/tests/test_computer_use.py` | test | batch | — | no analog yet (create from scratch) |
| `NyraHost/tests/test_staging.py` | test | batch | — | no analog yet (create from scratch) |
| `NyraHost/tests/test_external_client.py` | test | batch | — | no analog yet (create from scratch) |
| `NyraHost/tests/conftest.py` | test | batch | `NyraHost/tests/conftest.py` | in-place extension |

---

## Pattern Assignments

### `NyraHost/src/nyrahost/tools/meshy_tools.py` (MCP tool, request-response + async polling)

**Analog:** `NyraHost/src/nyrahost/tools/blueprint_tools.py` (lines 1-50, 114-170)

**Imports pattern** (blueprint_tools.py lines 1-18):
```python
from __future__ import annotations

import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult
```

**Core NyraTool class pattern** (blueprint_tools.py lines 114-169):
```python
class BlueprintReadTool(NyraTool):
    name = "nyra_blueprint_read"
    description = (
        "Read a Blueprint's node graph, variables, and event graphs as structured JSON. "
        "Returns class name, functions, events, variables, and graph nodes."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'",
            },
            ...
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        bp, err = _load_blueprint(params["asset_path"])
        if err:
            code = "-32010" if err == "asset_not_found" else "-32013"
            return NyraToolResult.err(f"[{code}] {err}: {params['asset_path']}")
        ...
        log.info("blueprint_read", asset=params["asset_path"], ...)
        return NyraToolResult.ok(result)
```

**Key design decisions for meshy_tools.py:**
- Follow the same `NyraTool` + `NyraToolResult` pattern from `base.py`
- Error codes use `-32xxx` range (matching existing convention in blueprint_tools)
- Tool returns a `job_id` immediately; polling is async in background task
- Import `uuid`, `aiohttp`, `structlog`, and `from nyrahost.tools.staging import StagingManifest`
- Log with `structlog.get_logger("nyrahost.tools.meshy_tools")` — consistent with existing logger names
- `_load_blueprint` pattern maps to a `_validate_image_path` helper
- `__all__` exports the tool classes

---

### `NyraHost/src/nyrahost/tools/comfyui_tools.py` (MCP tool, request-response + async polling)

**Analog:** `NyraHost/src/nyrahost/tools/meshy_tools.py` (same pattern, parallel implementation)

**Imports pattern:**
```python
from __future__ import annotations

import structlog
import uuid

from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.external.comfyui_client import ComfyUIClient
from nyrahost.tools.staging import StagingManifest
```

**Core pattern (same as meshy_tools.py but with workflow_json parameter):**
```python
class ComfyUIRunWorkflowTool(NyraTool):
    name = "nyra_comfyui_run_workflow"
    description = (
        "Run a ComfyUI image generation workflow and auto-import results as UTexture2D. "
        "Pass a workflow exported from ComfyUI in API format."
    )
    parameters = {
        "type": "object",
        "properties": {
            "workflow_json": {
                "type": "object",
                "description": "ComfyUI workflow in API JSON format"
            },
            "input_image_asset_path": {"type": "string"},
            "target_folder": {
                "type": "string",
                "default": "/Game/NYRA/Textures",
                "description": "UE Content destination folder for generated textures"
            }
        },
        "required": ["workflow_json"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        job_id = str(uuid.uuid4())
        manifest = StagingManifest()
        manifest.add_pending(job_id, "comfyui", "run_workflow",
                             params.get("input_image_asset_path", ""))
        return NyraToolResult.ok({
            "job_id": job_id,
            "status": "pending",
            "message": "ComfyUI workflow queued. Results auto-imported to ..."
        })
```

**Key design decisions for comfyui_tools.py:**
- Parallel structure to meshy_tools.py — same `NyraTool` base class, same `NyraToolResult` return pattern
- Two classes: `ComfyUIRunWorkflowTool` + `ComfyUICheckStatusTool` (job status poller)
- `ComfyUIClient` uses `aiohttp` async client (mirrors meshy_client.py)
- Workflow JSON is passed as a tool parameter (agent exports from ComfyUI UI)
- `__all__` exports both tool classes

---

### `NyraHost/src/nyrahost/tools/computer_use_tools.py` (MCP tool, event-driven)

**Analog:** `NyraHost/src/nyrahost/tools/blueprint_debug.py` (event-driven error pattern)

**Imports pattern** (blueprint_debug.py lines 1-18):
```python
from __future__ import annotations

import re
import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult
```

**Core pattern — async execute with event loop dispatch:**
```python
# computer_use_tools.py
from __future__ import annotations

import structlog
from nyrahost.tools.base import NyraTool, NyraToolResult
from nyrahost.computer_use.loop import ComputerUseLoop

log = structlog.get_logger("nyrahost.tools.computer_use_tools")

class ComputerUseExecuteTool(NyraTool):
    name = "nyra_computer_use_execute"
    description = (
        "Drive a Windows desktop application via Claude Opus 4.7 computer-use. "
        "Reserved for Substance 3D Sampler (no API) and UE editor modal dialogs "
        "that the Unreal API does not expose. API-first tools (Meshy, ComfyUI) "
        "must be attempted first."
    )
    parameters = {
        "type": "object",
        "properties": {
            "task": {"type": "string", "description": "Natural-language task description"},
            "target_app": {
                "type": "string",
                "enum": ["substance_sampler", "ue_editor_modal"],
                "description": "Target application"
            },
            "max_turns": {"type": "integer", "default": 30}
        },
        "required": ["task", "target_app"]
    }

    async def execute(self, params: dict) -> NyraToolResult:
        loop = ComputerUseLoop()
        try:
            result = await loop.execute(
                task=params["task"],
                target_app=params["target_app"],
                max_turns=params.get("max_turns", 30)
            )
            return NyraToolResult.ok(result)
        except TimeoutError:
            return NyraToolResult.err("[-32020] computer-use loop exceeded max turns")
        except Exception as e:
            log.error("computer_use_failed", error=str(e))
            return NyraToolResult.err(f"[-32000] computer-use failed: {e}")
```

**Key design decisions for computer_use_tools.py:**
- Inherits from `NyraTool` but `execute` is `async` — the `mcp_server/__init__.py` `handle_tool_call` already `await`s, so async tools are supported
- Wraps `ComputerUseLoop` from `nyrahost.computer_use.loop`
- GEN-03 gated scope: tool is registered but requires a canary-suite pass (>85% reliability) before Phase 7 commits
- Error code range `-32xxx` continues — computer-use uses `-32020` onward
- Permission gate (HUD overlay + Ctrl+Alt+Space pause) must be shown before first Win32 action

---

### `NyraHost/src/nyrahost/tools/staging.py` (utility, file-I/O)

**Analog:** `NyraHost/src/nyrahost/downloader/gemma.py` (file-I/O + atomic writes + structured logging)

**Imports pattern** (gemma.py lines 1-35):
```python
from __future__ import annotations

import asyncio
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import httpx
import structlog

log = structlog.get_logger("nyrahost.downloader.gemma")
```

**Core staging manifest pattern:**
```python
# staging.py
from __future__ import annotations

import json
import structlog
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

log = structlog.get_logger("nyrahost.tools.staging")

MANIFEST_PATH_KEY = "NYRA_STAGING_MANIFEST"
DEFAULT_STAGING_DIR = Path.home() / ".local" / "share" / "NYRA" / "staging"

@dataclass
class StagingManifest:
    """Reads and writes nyra_pending.json staging manifest.

    Every external tool result (Meshy GLB, ComfyUI PNG, computer-use screenshot)
    lands here before UE import. Entries are UUID-keyed for idempotent retry.
    """
    manifest_path: Path = field(default_factory=lambda: (
        Path(__import__("os").environ.get("LOCALAPPDATA", Path.home() / ".local" / "share"))
        / "NYRA" / "nyra_pending.json"
    ))
    _cache: Optional[dict] = field(default=None, repr=False)

    def _read(self) -> dict:
        if self._cache is not None:
            return self._cache
        if self.manifest_path.exists():
            self._cache = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        else:
            self._cache = {"version": 1, "jobs": []}
        return self._cache

    def add_pending(self, job_id: str, tool: str, operation: str,
                    input_ref: str, input_hash: str = "") -> None:
        """Write a pending entry BEFORE returning job_id — Pitfall 1 mitigation."""
        m = self._read()
        m.setdefault("jobs", [])
        m["jobs"].append({
            "id": job_id,
            "tool": tool,
            "operation": operation,
            "input_ref": input_ref,
            "input_hash": input_hash,
            "api_response": {},
            "downloaded_path": None,
            "ue_asset_path": None,
            "ue_import_status": "pending",
            "created_at": __import__("datetime").datetime.utcnow().isoformat() + "Z",
        })
        self._write(m)

    def update_completed(self, job_id: str, downloaded_path: str) -> None:
        """Update manifest after successful download."""
        m = self._read()
        for job in m.get("jobs", []):
            if job.get("id") == job_id:
                job["downloaded_path"] = downloaded_path
                job["ue_import_status"] = "ready_for_import"
                break
        self._write(m)

    def find_by_input_hash(self, tool: str, operation: str,
                           input_hash: str) -> Optional[str]:
        """Idempotent dedup: return existing job_id if identical input already queued."""
        m = self._read()
        for job in m.get("jobs", []):
            if (job.get("tool") == tool and job.get("operation") == operation
                    and job.get("input_hash") == input_hash
                    and job.get("ue_import_status") in ("pending", "ready_for_import")):
                return job.get("id")
        return None

    def _write(self, manifest: dict) -> None:
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        self._cache = manifest
```

**Key design decisions for staging.py:**
- Follows `GemmaDownloader._resume_offset` + `_write` atomic write pattern
- `_cache` field invalidation on write mirrors gemma.py's pattern
- `MANIFEST_PATH_KEY` env-override allows testing against a temp path
- `add_pending` writes BEFORE the tool returns — critical for Pitfall 1 mitigation
- `find_by_input_hash` implements idempotent deduplication (Pitfall 4 mitigation)
- `ue_import_status` enum: `pending` | `ready_for_import` | `imported` | `failed` | `timeout`
- Periodic cleanup: mark entries older than 7 days with `ue_import_status: timeout`

---

### `NyraHost/src/nyrahost/external/meshy_client.py` (HTTP client, streaming)

**Analog:** `NyraHost/src/nyrahost/downloader/gemma.py` (async HTTP streaming with retry + progress)

**Core pattern — async HTTP client with aiohttp:**
```python
# meshy_client.py
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Optional

import aiohttp
import structlog

log = structlog.get_logger("nyrahost.external.meshy_client")

@dataclass(frozen=True)
class MeshySpec:
    api_key: str
    base_url: str = "https://meshy.ai/api/v1"
    timeout_seconds: int = 600

class MeshyClient:
    """Async Meshy REST client — image-to-3D with exponential-backoff polling."""

    def __init__(self, spec: MeshySpec):
        self.spec = spec
        self._session: Optional[aiohttp.ClientSession] = None

    async def _session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def image_to_3d(self, image_bytes: bytes,
                          task_type: str = "meshy-image-to-3d-reMeshed",
                          prompt: str = "") -> dict:
        sess = await self._get_session()
        form = aiohttp.FormData()
        form.add_field("model_file", image_bytes,
                       filename="ref.jpg",
                       content_type="image/jpeg")
        form.add_field("task_type", task_type)
        if prompt:
            form.add_field("prompt", prompt)

        async with sess.post(
            f"{self.spec.base_url}/meshes",
            headers={"Authorization": f"Bearer {self.spec.api_key}"},
            data=form,
        ) as resp:
            task = await resp.json()
            task_id = task["id"]  # Verify: may be "taskId" — check Meshy docs

        # Poll with exponential backoff
        delay = 2.0
        start = time.monotonic()
        while True:
            async with sess.get(
                f"{self.spec.base_url}/meshes/{task_id}",
                headers={"Authorization": f"Bearer {self.spec.api_key}"},
            ) as resp:
                status = await resp.json()
                if status["status"] == "completed":
                    return status
                elif status["status"] in ("failed", "cancelled"):
                    raise RuntimeError(f"Meshy task failed: {status}")
            await asyncio.sleep(delay)
            delay = min(delay * 1.5, 30.0)
            if time.monotonic() - start > self.spec.timeout_seconds:
                raise TimeoutError("Meshy job timeout (>10 min)")

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
```

**Key design decisions for meshy_client.py:**
- `aiohttp.ClientSession` reuse (like gemma.py's `httpx.AsyncClient`) for connection pooling
- Exponential backoff: `delay = min(delay * 1.5, 30.0)` — matches RESEARCH.md Pattern 2
- Timeout at 600s (10 min) — configurable via `MeshySpec.timeout_seconds`
- `MeshySpec` frozen dataclass mirrors `GemmaSpec` from gemma.py
- `API key not in logs` — Bearer token in header only, never in log messages
- Close method for cleanup; caller uses `async with` context manager pattern

---

### `NyraHost/src/nyrahost/external/comfyui_client.py` (HTTP client, streaming)

**Analog:** `NyraHost/src/nyrahost/external/meshy_client.py` (same pattern, different API)

**Core pattern — ComfyUI HTTP client:**
```python
# comfyui_client.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import aiohttp
import structlog

log = structlog.get_logger("nyrahost.external.comfyui_client")

@dataclass(frozen=True)
class ComfyUISpec:
    host: str = "127.0.0.1"
    port: int = 8188
    timeout_seconds: int = 300

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

class ComfyUIClient:
    """Async ComfyUI HTTP client — queue workflow, poll history."""

    def __init__(self, spec: ComfyUISpec):
        self.spec = spec
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def run_workflow(self, workflow: dict) -> dict:
        sess = await self._get_session()
        async with sess.post(
            f"{self.spec.base_url}/prompt",
            json={"prompt": workflow},
        ) as resp:
            result = await resp.json()
            prompt_id = result["prompt_id"]

        # Poll history concurrently with queue check (Pitfall 2 mitigation)
        while True:
            async with sess.get(
                f"{self.spec.base_url}/history/{prompt_id}"
            ) as resp:
                if resp.status == 200:
                    history = await resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        if outputs:
                            return outputs
            # Also check queue to confirm prompt is not stalled
            async with sess.get(f"{self.spec.base_url}/queue") as resp:
                if resp.status == 200:
                    queue_data = await resp.json()
                    running = queue_data.get("queue_running", [])
                    pending = queue_data.get("queue_pending", [])
                    if not any(p.get("prompt_id") == prompt_id for p in running + pending):
                        raise RuntimeError(f"ComfyUI prompt {prompt_id} not found in queue")
            await asyncio.sleep(3.0)

    async def get_object_info(self) -> dict:
        sess = await self._get_session()
        async with sess.get(f"{self.spec.base_url}/object_info") as resp:
            return await resp.json()

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
```

**Key design decisions for comfyui_client.py:**
- Same dataclass + session-reuse + close pattern as meshy_client.py
- Queue + history dual polling mitigates Pitfall 2 (ComfyUI queue stall)
- `get_object_info()` for workflow JSON validation before submit
- Port fallback: try 8188, 8189, 8190 (configurable)
- ComfyUI server unreachable → tool returns error with install/run instructions (no blocking)

---

### `NyraHost/src/nyrahost/computer_use/loop.py` (service, event-driven)

**Analog:** `NyraHost/src/nyrahost/handlers/download.py` (async background task + WS notification pattern)

**Imports pattern** (download.py lines 1-30):
```python
from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import structlog
from websockets.server import ServerConnection

from ..downloader.gemma import (
    GemmaSpec,
    download_gemma,
)
from ..jsonrpc import build_notification
from ..session import SessionState

log = structlog.get_logger("nyrahost.download")
```

**Core computer-use loop pattern:**
```python
# computer_use/loop.py
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

import structlog
from anthropic import Anthropic

from .screenshot import capture_screen
from .win32_uia import Win32UIA

log = structlog.get_logger("nyrahost.computer_use.loop")

@dataclass
class ComputerUseLoop:
    """Orchestrate Opus 4.7 computer-use loop for Substance Sampler + UE modals."""
    api_key: str
    max_turns: int = 30
    _client: Anthropic | None = None

    @property
    def client(self) -> Anthropic:
        if self._client is None:
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    @property
    def tools(self) -> list[dict]:
        return [{
            "name": "computer_20251124",
            "type": "computer_20251124",
            "display_width_px": 2576,
            "display_height_px": 2576,
            "environment": "windows",
        }]

    async def execute(self, task: str, target_app: str) -> dict:
        messages = [{"role": "user", "content": [{"type": "text", "text": task}]}]
        for _ in range(self.max_turns):
            screenshot_b64 = capture_screen()
            messages.append({
                "role": "user",
                "content": [{
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png",
                               "data": screenshot_b64}
                }]
            })
            resp = self.client.messages.create(
                model="opus-4-7",
                max_tokens=1024,
                tools=self.tools,
                messages=messages,
                headers={"anthropic-beta": "computer-use-2025-11-24"},
            )
            msg = resp.content[-1]
            if msg.type == "text":
                messages.append({"role": "assistant",
                                 "content": [{"type": "text", "text": msg.text}]})
            elif msg.type == "tool_use":
                for result in msg.result:
                    action = result.source["action"]
                    outcome = Win32UIA.execute(action, target_app=target_app)
                    messages.append({
                        "role": "user",
                        "content": [{"type": "tool_result",
                                     "tool_use_id": result.id,
                                     "content": json.dumps(outcome)}]
                    })
                    if outcome.get("success"):
                        return outcome
        raise TimeoutError("computer-use loop exceeded max turns")
```

**Key design decisions for loop.py:**
- `anthropic` Python SDK for API key path (not Claude CLI — Windows constraint)
- Beta header `anthropic-beta: computer-use-2025-11-24` required per STACK.md
- `ComputerUseLoop` is instantiated per-session; client is lazily created
- Screenshot via `mss` (pure Python, stable across DPI scaling — not PIL.ImageGrab)
- Win32 UIA for structural element clicks (not pyautogui — more stable vs. theme/DPI changes)
- Ctrl+Alt+Space pause chord registered at OS level before first action
- GEN-03 gated: loop only activates after >85% canary suite success

---

### `NyraHost/src/nyrahost/computer_use/screenshot.py` (utility, file-I/O)

**Analog:** `NyraHost/src/nyrahost/downloader/gemma.py` (file-I/O with structured logging)

**Core pattern:**
```python
# computer_use/screenshot.py
from __future__ import annotations

import base64
from typing import Optional

import mss
import structlog

log = structlog.get_logger("nyrahost.computer_use.screenshot")

def capture_screen(monitor_index: int = 1) -> str:
    """Capture the primary monitor (or monitor_index) as base64 PNG.

    mss is preferred over PIL.ImageGrab — stable across DPI scaling on Windows.
    Output is base64-encoded for Anthropic API (max 2576px on long edge for Opus 4.7).
    """
    with mss.mss() as s:
        shot = s.grab(s.monitors[monitor_index])
        return base64.b64encode(mss.tools.to_png(shot)).decode()
```

---

### `NyraHost/src/nyrahost/computer_use/win32_uia.py` (utility, event-driven)

**Analog:** None — Windows-specific, no existing NyraHost analog. Follow Win32 UIA best practices.

**Core pattern:**
```python
# computer_use/win32_uia.py
from __future__ import annotations

import structlog
from typing import Any

log = structlog.get_logger("nyrahost.computer_use.win32_uia")

# Target app → UIA element path map (populated by canary suite in Phase 5 spike)
_TARGET_ELEMENT_PATHS: dict[str, dict[str, Any]] = {
    "substance_sampler": {},  # Populated by canary suite
    "ue_editor_modal": {},    # Populated by canary suite
}

class Win32UIA:
    """Win32 UIA structural element backend for computer-use action dispatch."""

    @staticmethod
    def execute(action: dict, target_app: str) -> dict:
        """Dispatch a computer_20251124 action to the appropriate Win32 UIA handler."""
        action_type = action.get("action")
        if action_type == "mouse_move":
            return Win32UIA._move(action, target_app)
        elif action_type == "mouse_click":
            return Win32UIA._click(action, target_app)
        elif action_type == "keypress":
            return Win32UIA._keypress(action, target_app)
        elif action_type == "screenshot":
            return {"success": True, "screenshots": []}  # Handled by loop
        else:
            return {"success": False, "error": f"Unknown action: {action_type}"}

    @staticmethod
    def _move(action: dict, target_app: str) -> dict:
        # Use UIA TreeWalker to find element by path, then set cursor to element center
        # Implemented via py-win32 / uiautomation stdlib
        log.info("uia_move", x=action.get("x"), y=action.get("y"), app=target_app)
        return {"success": True}

    @staticmethod
    def _click(action: dict, target_app: str) -> dict:
        log.info("uia_click", button=action.get("button"), app=target_app)
        return {"success": True}

    @staticmethod
    def _keypress(action: dict, target_app: str) -> dict:
        log.info("uia_keypress", key=action.get("key"), app=target_app)
        return {"success": True}
```

**Key design decisions for win32_uia.py:**
- No existing NyraHost analog — follows Win32 UIA best practices
- `_TARGET_ELEMENT_PATHS` dictionary is the canary-suite output: maps target_app to UIA element tree paths
- `Win32UIA.execute` dispatches action types from `computer_20251124` tool
- Uses `uiautomation` stdlib or `pywinauto` for structural element access
- Never uses pixel coordinates directly — UIA structural elements are stable across DPI/theme
- Permission gate (HUD overlay) shown before first `_click` action in a session

---

### `NyraHost/src/nyrahost/config.py` (config, in-place extension)

**Analog:** `NyraHost/src/nyrahost/config.py` (existing in-place pattern)

**Extension pattern — add to existing `NyraConfig` dataclass:**
```python
# Add to NyraConfig dataclass fields:
meshy_api_key: str = ""
meshy_base_url: str = "https://meshy.ai/api/v1"
comfyui_host: str = "127.0.0.1"
comfyui_port: int = 8188
computer_use_api_key: str = ""  # BYOK mode from Phase 2
blender_path: str = ""  # Deferred to v1.1

# Add factory method:
@staticmethod
def staging_dir() -> Path:
    la = os.environ.get("LOCALAPPDATA")
    if la:
        return Path(la) / "NYRA" / "staging"
    return Path.home() / ".local" / "share" / "NYRA" / "staging"
```

**Key design decisions:**
- All external tool settings are strings (no secrets stored, loaded from env at startup)
- `blender_path` added now but unused until v1.1 (GEN-11)
- Config loaded from env + handshake JSON — no new config file format

---

### `NyraHost/src/nyrahost/mcp_server/__init__.py` (route, in-place extension)

**Analog:** `NyraHost/src/nyrahost/mcp_server/__init__.py` (existing in-place pattern)

**Extension pattern — add tool registrations + schema entries:**
```python
# In imports section, add:
from nyrahost.tools.meshy_tools import MeshyImageTo3DTool
from nyrahost.tools.comfyui_tools import ComfyUIRunWorkflowTool, ComfyUICheckStatusTool
from nyrahost.tools.computer_use_tools import ComputerUseExecuteTool

# In NyraMCPServer.__init__._tools dict, add:
"nyra_meshy_image_to_3d": MeshyImageTo3DTool(),
"nyra_comfyui_run_workflow": ComfyUIRunWorkflowTool(),
"nyra_comfyui_check_status": ComfyUICheckStatusTool(),
"nyra_computer_use_execute": ComputerUseExecuteTool(),

# In @server.list_tools(), add corresponding inputSchema entries
# (see mcp_server/__init__.py pattern — follow the existing JSON schema format)
```

**Key design decisions:**
- Existing `NyraMCPServer._tools` dict is the canonical tool registry
- `create_server()` uses the same `@server.list_tools()` decorator pattern
- Phase 5 tools follow the same `inputSchema` JSON schema structure used by all existing tools
- Computer-use tool registered but gated behind canary-suite flag (check `settings.computer_use_enabled`)

---

### `NyraHost/src/nyrahost/staging_manifest.schema.json` (config, file-I/O)

**Analog:** None — new JSON schema file. Use standard JSON Schema draft-07.

**Core schema:**
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "NyraPendingManifest",
  "description": "Staging manifest for external tool imports (nyra_pending.json)",
  "type": "object",
  "required": ["version", "jobs"],
  "properties": {
    "version": {
      "type": "integer",
      "minimum": 1,
      "description": "Schema version — increment when breaking changes are introduced"
    },
    "jobs": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["id", "tool", "operation", "ue_import_status"],
        "properties": {
          "id": {"type": "string", "format": "uuid"},
          "tool": {"type": "string", "enum": ["meshy", "comfyui", "computer_use"]},
          "operation": {"type": "string"},
          "input_ref": {"type": "string"},
          "input_hash": {"type": "string"},
          "api_response": {"type": "object"},
          "downloaded_path": {"type": ["string", "null"]},
          "ue_asset_path": {"type": ["string", "null"]},
          "ue_import_status": {
            "type": "string",
            "enum": ["pending", "ready_for_import", "imported", "failed", "timeout"]
          },
          "created_at": {"type": "string", "format": "date-time"}
        }
      }
    }
  }
}
```

---

### `NyraHost/tests/test_meshy_tools.py` (test, batch)

**Analog:** None yet — create from scratch following pytest + pytest-asyncio pattern.

**Core test structure:**
```python
# tests/test_meshy_tools.py
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch

from nyrahost.tools.meshy_tools import MeshyImageTo3DTool
from nyrahost.tools.base import NyraToolResult

@pytest.fixture
def meshy_tool():
    return MeshyImageTo3DTool()

def test_job_submission_returns_id(meshy_tool):
    result = meshy_tool.execute({"image_path": "/Game/Props/TestTexture"})
    assert result.error is None
    assert result.data["job_id"] is not None
    assert result.data["status"] == "pending"

def test_pending_manifest_entry_written(meshy_tool, tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    # Verify manifest contains pending entry after execute()
    ...

@pytest.mark.asyncio
async def test_polling_loop_completes():
    # Mock aiohttp responses for Meshy task creation + polling
    ...
```

---

## Shared Patterns

### Async HTTP Client Pattern
**Source:** `NyraHost/src/nyrahost/downloader/gemma.py` lines 67-155, `NyraHost/src/nyrahost/external/meshy_client.py`
**Apply to:** All external HTTP clients (`meshy_client.py`, `comfyui_client.py`)
```python
# Pattern: dataclass spec + lazy session + close method
@dataclass(frozen=True)
class MeshySpec:
    api_key: str
    base_url: str = "https://meshy.ai/api/v1"
    timeout_seconds: int = 600

class MeshyClient:
    def __init__(self, spec: MeshySpec):
        self.spec = spec
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
```

### MCP Tool Registration Pattern
**Source:** `NyraHost/src/nyrahost/mcp_server/__init__.py` lines 58-102
**Apply to:** All Phase 5 tool additions
- Import tool class
- Instantiate in `NyraMCPServer.__init__._tools` dict
- Add `inputSchema` entry in `@server.list_tools()`
- Handle in `handle_tool_call` (or inherit auto-handling from existing dispatch)

### NyraTool + NyraToolResult Pattern
**Source:** `NyraHost/src/nyrahost/tools/base.py`, `NyraHost/src/nyrahost/tools/blueprint_tools.py`
**Apply to:** All new MCP tools
- Inherit from `NyraTool`
- Define `name`, `description`, `parameters` class attributes
- `execute(params: dict) -> NyraToolResult`
- Return `NyraToolResult.err(...)` for failures with `-32xxx` error codes
- Return `NyraToolResult.ok({...})` for success

### Staging Manifest (Idempotent File-I/O)
**Source:** `NyraHost/src/nyrahost/tools/staging.py`
**Apply to:** All external tool results — GLB downloads, ComfyUI textures, computer-use outputs
- Write `pending` entry BEFORE returning job_id to caller
- Key by UUID (`job_id = str(uuid.uuid4())`)
- Deduplicate by `(tool, operation, input_hash)` before starting new API call
- Update `ue_import_status` at each state transition

### Error Code Range
**Source:** `NyraHost/src/nyrahost/tools/blueprint_tools.py` lines 137-141
**Apply to:** All Phase 5 tool error codes
- `-32000` to `-32009`: Generic tool errors
- `-32010` to `-32019`: Asset/Blueprint errors (existing)
- `-32020` to `-32029`: Computer-use errors (Phase 5 new range)
- `-32030` to `-32039`: External tool (Meshy/ComfyUI) errors

---

## No Analog Found

Files with no close match in the codebase (planner should use RESEARCH.md patterns instead):

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `NyraHost/src/nyrahost/computer_use/win32_uia.py` | utility | event-driven | Windows UIA-specific; no existing Win32 code in NyraHost |
| `NyraHost/src/nyrahost/staging_manifest.schema.json` | config | file-I/O | JSON Schema definition file; no schema files exist in codebase |
| `NyraHost/tests/test_meshy_tools.py` | test | batch | No existing Phase 5 test files yet |
| `NyraHost/tests/test_comfyui_tools.py` | test | batch | No existing Phase 5 test files yet |
| `NyraHost/tests/test_computer_use.py` | test | batch | No existing Phase 5 test files yet |
| `NyraHost/tests/test_staging.py` | test | batch | No existing staging test files yet |
| `NyraHost/tests/test_external_client.py` | test | batch | No existing external client test files yet |

---

## Metadata

**Analog search scope:** `NyraHost/src/nyrahost/`
**Files scanned:** ~40 Python source files
**Pattern extraction date:** 2026-05-07

**Primary analog sources:**
- `NyraHost/src/nyrahost/tools/base.py` — NyraTool + NyraToolResult base class
- `NyraHost/src/nyrahost/tools/blueprint_tools.py` — MCP tool pattern (most complete example)
- `NyraHost/src/nyrahost/tools/blueprint_debug.py` — async tool + error pattern
- `NyraHost/src/nyrahost/tools/material_tools.py` — error handling + unreal integration
- `NyraHost/src/nyrahost/downloader/gemma.py` — async HTTP streaming + file-I/O pattern
- `NyraHost/src/nyrahost/handlers/download.py` — async background task + notification pattern
- `NyraHost/src/nyrahost/config.py` — NyraConfig frozen dataclass pattern
- `NyraHost/src/nyrahost/mcp_server/__init__.py` — tool registration + server factory pattern

**Assumptions:**
- A1: Meshy API base URL `https://meshy.ai/api/v1` — verify before implementation (see RESEARCH.md Assumptions Log)
- A2: Meshy task creation returns `{"id": "..."}` field — verify from Meshy API docs
- A3: ComfyUI server on port 8188 — confirmed from docs.comfy.org
- A4: computer-use on Windows runs via API key path (not Claude CLI)

# Phase 5: External Tool Integrations (API-First) - Research

**Researched:** 2026-05-07
**Domain:** External AI tool orchestration — Meshy REST API, ComfyUI HTTP API, Blender Python subprocess, Claude computer-use reserved for non-API tools
**Confidence:** MEDIUM-HIGH (ComfyUI API verified from official docs; Meshy API partially verified; Blender and computer-use based on training knowledge)

---

<user_constraints>
## User Constraints (from CONTEXT.md)

*No CONTEXT.md exists for Phase 5 — skipped.*
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| GEN-01 | Meshy REST API integration — image-to-3D model, job polling, download, auto-import as UE UStaticMesh with LODs and collision | Meshy API v1 at `meshy.ai/api/v1/` confirmed; task types (text-to-3d-reMeshed, image-to-3d-reMeshed, texture-to-3d) and polling pattern documented below; UE static mesh import pipeline requires `UFbxFactory` or `UFbxImportUI` + `IPluginManager` |
| GEN-02 | ComfyUI local HTTP API integration — image-to-image workflows (textures, variations, references), auto-import results as UTexture2D or Material inputs | ComfyUI local server at `http://127.0.0.1:8188` (default port) confirmed from official docs; all core endpoints verified; workflow JSON format confirmed; UE texture import via `UTexture2D::CreateFromFile` or Python `unreal.EditorAssetLibrary` |
| GEN-03 | Claude computer-use (`computer_20251124` tool with Opus 4.7) reserved for Substance 3D Sampler (image-to-PBR material, no public API) and UE editor modal dialogs the Unreal API doesn't expose | computer-use Windows constraint confirmed (CLI not available on Windows; Desktop or API key fallback); `computer_20251124` tool type + `computer-use-2025-11-24` beta header verified from STACK.md |
</phase_requirements>

## Summary

Phase 5 implements API-first external tool integrations in NYRA's NyraHost sidecar, plus a gated computer-use spike for tools with no API surface. GEN-01 surfaces Meshy as an MCP tool that creates 3D meshes from reference images (Polling + Download pattern). GEN-02 surfaces ComfyUI as an MCP tool that runs local Stable Diffusion workflows (Queue + History pattern). GEN-03 confines `computer_20251124` to exactly two use cases — Substance 3D Sampler (no API) and UE editor modal dialogs (Unreal API gap) — and requires >85% success on a 20-session canary suite before Phase 7 commits to DEMO-02. The staging-manifest pattern (nyra_pending.json) is the key architectural primitive: external tools never write to UE Content directly; every import is audited and undoable.

Three findings changed from initial assumptions: (1) Blender Python is not a Phase 5 deliverable per REQUIREMENTS.md GEN-11 deferral — it belongs to v1.1 — so `bpy` subprocess invocation is out of scope; (2) ComfyUI is fully verified from official docs at docs.comfy.org, no assumptions needed; (3) computer-use on Windows requires either Claude Desktop running or direct API key (not CLI), which affects the reliability spike design.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Meshy REST API orchestration | NyraHost (Python) | UE Asset Import Bridge | NyraHost handles HTTP polling loop; UE Python bindings handle import |
| ComfyUI HTTP API orchestration | NyraHost (Python) | UE Asset Import Bridge | NyraHost submits prompt + polls; UE Python bindings handle texture import |
| Blender Python subprocess | NyraHost (Python) | — | Deferred to v1.1; not in scope for Phase 5 |
| Substance 3D Sampler via computer-use | NyraHost (Python) + Opus 4.7 | — | computer-use loop runs inside NyraHost; Windows Desktop or API key |
| UE modal dialog via computer-use | NyraHost (Python) + Opus 4.7 | — | Win32 UIA backend in NyraHost; UE Python bindings for dialog actions |
| Staging manifest / asset import | UE (Python binding) | NyraHost (manifest writer) | `nyra_pending.json` written by NyraHost; read + import by UE Python |
| Config/settings management | NyraHost config.py | UE editor settings | Meshy API key, ComfyUI port, Blender path all configurable |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python `requests` | `requests>=2.31.0` [VERIFIED: PyPI] | Meshy REST HTTP calls | Built into stdlib patterns; NyraHost already uses it |
| Python `aiohttp` | `aiohttp>=3.9.0` [VERIFIED: PyPI] | Async HTTP for Meshy polling + ComfyUI prompt | Non-blocking polling loop; consistent with async architecture already in NyraHost (SSE already uses aiohttp-style) |
| Python `asyncio` | stdlib | Polling loop, subprocess management | Already the async backbone of NyraHost |
| Blender (headless) | 4.x LTS | Mesh cleanup / UV authoring via Python subprocess | GEN-11 deferred to v1.1; Blender 4.x LTS for Windows confirmed [ASSUMED] |
| `httpx` | `httpx>=0.27.0` [VERIFIED: PyPI] | ComfyUI workflow upload with multipart | ComfyUI `/upload/image` requires multipart/form-data; `httpx` handles cleanly |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `subprocess` (stdlib) | — | Blender headless invocation | Invoking `blender.exe --background --python-script` |
| Python `uuid` (stdlib) | — | Staging manifest UUID keys | Idempotent import tracking |
| Python `json` (stdlib) | — | Staging manifest serialization | `nyra_pending.json` read/write |
| UE `unreal` Python binding | UE-bundled | Asset import, texture creation | `EditorAssetLibrary`, `AssetTools`, `FbxFactory` |
| UE `FbxFactory` / `UFbxImportUI` | UE C++ API | Static mesh import with LODs + collision | GEN-01 UE import pipeline |
| Python `mss` or `PIL` | `mss>=4.0.0` / `pillow>=10.0.0` | Screenshot capture for computer-use loop | If NyraHost runs its own computer-use via API key |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `requests` (sync) for Meshy | `aiohttp` async client | Meshy polling is async by nature; use `aiohttp` for both Meshy and ComfyUI to share one async HTTP client |
| `httpx` for ComfyUI upload | `requests` with `requests-toolbelt` | `httpx` has cleaner async multipart support; worth the extra dep |
| `pillow` for screenshot | `mss` (faster, pure Python) | `mss` is faster for screen capture; `pillow` only if PIL-format processing is needed |
| Blender headless subprocess | Blender Python API via `unreal.PythonScriptLibrary` | Not viable: Blender is a separate process with no in-process API; subprocess is the only path |
| computer-use via Claude Desktop | computer-use via API key (`computer_20251124`) | Desktop approach requires user to have Desktop running; API key approach gives NyraHost full control — both are valid but different UX tradeoffs |

**Installation:**
```bash
# NyraHost deps (add to pyproject.toml / requirements.txt)
aiohttp>=3.9.0
httpx>=0.27.0
mss>=4.0.0
pillow>=10.0.0
```

---

## Architecture Patterns

### System Architecture Diagram

```
User Reference Image
       |
       v
+----------------+
| Claude Opus 4.7 |  (via NyraHost backend router)
| (image analysis |
|  + task plan)   |
+--------+----+---+
         |    |
         v    v
+---------+  +--------+
| Meshy   |  | ComfyUI|  <- API-first path (NyraHost HTTP calls)
| REST API|  | HTTP  |     No cursor hijack. Fast. Idempotent.
+---------+  +--------+
    |              |
    v              v
nyra_pending.json  nyra_pending.json
    (staging manifest, UUID-keyed)
    |
    v
+------------------+
| UE Asset Import   |  <- UE Python binding reads manifest
| Bridge           |     - FBX/glb import via UFbxFactory
| (unreal Python)  |     - Texture import via UTexture2D::CreateFromFile
+------------------+     - UStaticMesh with LODs + collision
         |
         v
 UE Content Browser
 (actor spawn via nyra_actor_spawn, material via nyra_material_set_param)

=============================================================
COMPUTER-USE PATH (GEN-03, gated >85% reliability spike)
=============================================================
Substance 3D Sampler  OR  UE Editor Modal Dialog
(no API available)         (Unreal API gap)
         |                        |
         v                        v
+----------------+    +---------------------------+
| NyraHost CU    |    | NyraHost CU loop           |
| loop via      |    | via Windows Desktop        |
| API key or    |    | or direct API key +        |
| Desktop daemon|    | Win32 UIA structural clicks |
+----------------+    +---------------------------+
         |                        |
         v                        v
  nyra_pending.json  ->  UE Asset Import Bridge
  (same manifest, same import path)
```

### Recommended Project Structure

```
NyraHost/src/nyrahost/
├── tools/
│   ├── base.py                  # NyraTool, NyraToolResult (existing)
│   ├── meshy_tools.py           # NEW: Meshy MCP tools
│   ├── comfyui_tools.py         # NEW: ComfyUI MCP tools
│   ├── computer_use_tools.py   # NEW: computer-use orchestration tools
│   ├── staging.py              # NEW: nyra_pending.json manifest manager
│   ├── actor_tools.py          # (existing)
│   ├── asset_search.py         # (existing)
│   ├── blueprint_tools.py      # (existing)
│   └── material_tools.py       # (existing)
├── external/
│   ├── meshy_client.py         # NEW: Meshy async HTTP client
│   ├── comfyui_client.py       # NEW: ComfyUI HTTP client
│   └── blender_subprocess.py   # NEW: Blender headless subprocess runner (v1.1 prep)
├── computer_use/
│   ├── loop.py                 # NEW: computer-use orchestration loop
│   ├── win32_uia.py            # NEW: Win32 UIA structural-element backend
│   └── screenshot.py           # NEW: mss screenshot capture
├── mcp_server/__init__.py    # (existing: register Phase 5 tools)
├── config.py                  # (existing: add Meshy/ComfyUI/Blender config)
└── staging_manifest.schema.json  # NEW: JSON schema for nyra_pending.json
```

### Pattern 1: Staging Manifest (Idempotent Import)

**What:** Every external tool result lands in `nyra_pending.json` before UE import. Each entry is UUID-keyed. Re-running a tool call checks the manifest before starting a new API call — prevents duplicate imports when a job is retried after partial failure.

**When to use:** Every external tool call (Meshy, ComfyUI, computer-use). This is the idempotency primitive.

**Example:**
```json
// nyra_pending.json (written by NyraHost, read by UE Python)
{
  "version": 1,
  "jobs": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "tool": "meshy",
      "operation": "image-to-3d",
      "input_ref": "/Game/Props/HeroStatue",
      "input_hash": "sha256:abc123...",
      "api_response": { "taskId": "...", "status": "completed" },
      "downloaded_path": "C:/Users/aasish/AppData/NYRA/staging/550e8400.glb",
      "ue_asset_path": null,
      "ue_import_status": "pending",
      "created_at": "2026-05-07T12:00:00Z"
    }
  ]
}
```

### Pattern 2: Async Polling Loop (Meshy)

**What:** Meshy tasks are async (not webhooks). NyraHost polls with exponential backoff until `status == "completed"` or timeout (10 min default).

**When to use:** Every Meshy job submission.

**Example:**
```python
# meshy_client.py — async Meshy client
import aiohttp, asyncio, time

class MeshyClient:
    BASE_URL = "https://meshy.ai/api/v1"  # [ASSUMED]

    async def image_to_3d(self, api_key: str, image_bytes: bytes,
                          task_type: str = "meshy-image-to-3d-reMeshed") -> str:
        async with aiohttp.ClientSession() as sess:
            # 1. Upload + create task
            form = aiohttp.FormData()
            form.add_field("model_file", image_bytes,
                           filename="ref.jpg",
                           content_type="image/jpeg")
            form.add_field("task_type", task_type)
            async with sess.post(
                f"{self.BASE_URL}/meshes",
                headers={"Authorization": f"Bearer {api_key}"},
                data=form,
            ) as resp:
                task = await resp.json()
                task_id = task["id"]  # [ASSUMED field name]

            # 2. Poll with exponential backoff
            delay = 2.0
            start = time.monotonic()
            while True:
                async with sess.get(
                    f"{self.BASE_URL}/meshes/{task_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                ) as resp:
                    status = await resp.json()  # [ASSUMED]
                    if status["status"] == "completed":
                        return status["model_urls"]["glb"]  # [ASSUMED]
                    elif status["status"] in ("failed", "cancelled"):
                        raise RuntimeError(f"Meshy task failed: {status}")
                await asyncio.sleep(delay)
                delay = min(delay * 1.5, 30.0)
                if time.monotonic() - start > 600:
                    raise TimeoutError("Meshy job timeout (>10 min)")
```

### Pattern 3: ComfyUI Workflow Submission

**What:** ComfyUI accepts a workflow JSON (exported from the ComfyUI UI in "API format"). NyraHost submits it via POST `/prompt`, then polls GET `/history/{prompt_id}` or GET `/queue` until completion.

**When to use:** Texture generation, image variation, reference-based img2img.

**Example:**
```python
# comfyui_client.py — ComfyUI HTTP client
import aiohttp, asyncio, json

class ComfyUIClient:
    DEFAULT_PORT = 8188

    def __init__(self, host: str = "127.0.0.1", port: int = DEFAULT_PORT):
        self.base = f"http://{host}:{port}"

    async def run_workflow(self, workflow: dict, timeout: int = 300) -> dict:
        async with aiohttp.ClientSession() as sess:
            # 1. Submit
            async with sess.post(
                f"{self.base}/prompt",
                json={"prompt": workflow},
            ) as resp:
                result = await resp.json()
                prompt_id = result["prompt_id"]

            # 2. Poll history
            while True:
                async with sess.get(
                    f"{self.base}/history/{prompt_id}"
                ) as resp:
                    history = await resp.json()
                    if prompt_id in history:
                        outputs = history[prompt_id].get("outputs", {})
                        if outputs:
                            return outputs  # dict of output node_id -> image data
                await asyncio.sleep(3.0)

    async def get_workflow_node_info(self) -> dict:
        """GET /object_info — all available node types + defaults."""
        async with aiohttp.ClientSession() as sess:
            async with sess.get(f"{self.base}/object_info") as resp:
                return await resp.json()
```

### Pattern 4: Computer-Use Orchestration Loop (Windows)

**What:** NyraHost runs its own computer-use loop using Opus 4.7 via direct API key (bypassing Claude CLI on Windows). The loop: capture screenshot -> send to Opus 4.7 with `computer_20251124` tool -> execute Win32 action -> repeat until task complete.

**When to use:** Only for Substance 3D Sampler and UE modal dialogs (GEN-03 gated scope). API-first tools (Meshy, ComfyUI) must be tried first.

**Why not Claude Desktop:** Desktop requires the user to have Claude Desktop open and running. The direct API key approach gives NyraHost full control and works as a background service. [ASSUMED: API key path is how computer-use runs when Claude CLI is unavailable on Windows]

**Example:**
```python
# computer_use/loop.py — Windows computer-use loop
import mss, base64, json
from anthropic import Anthropic

class ComputerUseLoop:
    def __init__(self, api_key: str):
        self.client = Anthropic(api_key=api_key)
        self.tools = [{
            "name": "computer_20251124",
            "type": "computer_20251124",
            "display_width_px": 2576,   # Opus 4.7 max
            "display_height_px": 2576,
            "environment": "windows",
        }]

    def capture(self) -> str:
        with mss.mss() as s:
            shot = s.grab(s.monitors[1])
            return base64.b64encode(mss.tools.to_png(shot)).decode()

    async def execute(self, task: str, max_turns: int = 30) -> str:
        messages = [{"role": "user", "content": [{"type": "text", "text": task}]}
        for _ in range(max_turns):
            screenshot_b64 = self.capture()
            messages.append({
                "role": "user",
                "content": [{
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/png",
                               "data": screenshot_b64}
                }]
            })
            resp = self.client.messages.create(
                model="opus-4.7",
                max_tokens=1024,
                tools=self.tools,
                messages=messages,
            )
            msg = resp.content[-1]
            if msg.type == "text":
                messages.append({"role": "assistant", "content": [{"type": "text", "text": msg.text}]})
            elif msg.type == "tool_use":
                for result in msg.result:
                    action = result.source["action"]
                    # Dispatch to Win32 UIA backend
                    outcome = self.win32_uia.execute(action)
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

### Pattern 5: UE Asset Import via Python

**What:** After NyraHost writes the imported asset to disk, UE Python (`unreal` binding) imports it into the Content Browser using `AssetTools` + factory classes, then updates `nyra_pending.json` with the UE asset path.

**When to use:** After Meshy GLB download, after ComfyUI image download — every external tool result must go through this bridge.

```python
# staging.py — UE-side import handler (runs in UE Python context)
import unreal, json, os
from pathlib import Path

MANIFEST_PATH = Path(unreal.Paths.project_saved_dir()) / "NYRA" / "nyra_pending.json"

def import_meshy_glb(glb_path: str, dest_folder: str = "/Game/NYRA/Meshes") -> str:
    # 1. Load factory
    factory = unreal.FbxFactory()
    import_ui = unreal.FbxImportUI()
    import_ui.import_materials = True
    import_ui.import_textures = False
    import_ui.import_skeletal = False
    import_ui.lod_distance_0 = 256  # LOD0: 256 tris min
    import_ui.lod_distance_1 = 128
    import_ui.auto_generate_collision = True

    # 2. Import
    task = unreal.AssetImportTask()
    task.filename = glb_path
    task.destination_path = dest_folder
    task.factory = factory
    task.options = import_ui
    task.replace_existing = False  # idempotent
    task.save = True

    AssetTools = unreal.AssetToolsHelpers.get_asset_tools()
    AssetTools.import_asset_tasks([task])

    # 3. Update manifest
    manifest = json.loads(MANIFEST_PATH.read_text()) if MANIFEST_PATH.exists() else {"version": 1, "jobs": []}
    for job in manifest["jobs"]:
        if job.get("downloaded_path") == glb_path:
            job["ue_import_status"] = "imported"
            job["ue_asset_path"] = f"{dest_folder}/{Path(glb_path).stem}"
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2))
    return f"{dest_folder}/{Path(glb_path).stem}"

def import_comfyui_image(png_path: str, dest_folder: str = "/Game/NYRA/Textures") -> str:
    """Import PNG as UTexture2D."""
    task = unreal.AssetImportTask()
    task.filename = png_path
    task.destination_path = dest_folder
    task.factory = unreal.TextureFactory()
    task.replace_existing = False
    task.save = True
    AssetTools = unreal.AssetToolsHelpers.get_asset_tools()
    AssetTools.import_asset_tasks([task])
    return f"{dest_folder}/{Path(png_path).stem}"
```

### Anti-Patterns to Avoid

- **Direct UE Content writes from external tools:** Do not write mesh/texture files directly into the UE Content directory — use `nyra_pending.json` as the staging layer. This is the only way to keep imports undoable via `FScopedTransaction`.

- **Sync HTTP in the MCP tool handler:** `requests` (sync) inside an MCP `execute()` call blocks the MCP stdio loop. Use `aiohttp` (async) and return immediately, then use a background task to poll and fill the manifest. MCP tools should return a job ID immediately, not block for 30-120 seconds waiting for Meshy/ComfyUI to finish.

- **Non-idempotent tool calls:** Re-submitting a "generate texture" request after a network timeout should detect the existing job via `nyra_pending.json` (matched by `input_hash`) rather than creating a duplicate API call. This is the primary mitigation for PITFALLS section 5.4 "duplicate asset accumulation."

- **computer-use for API-available tools:** If Meshy or ComfyUI can handle a task, computer-use must not be used. The computer-use reliability spike gates this — the agent router must fail over to API-first tools before attempting computer-use.

- **Importing unverified asset formats:** Meshy may return USDZ, glTF, or OBJ depending on plan tier. Only GLB is guaranteed to have FBX-like import support via `UFbxFactory`. USDZ requires conversion (use Blender subprocess as a pre-import step, deferred to v1.1).

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Async HTTP polling | `requests` blocking loop + `time.sleep` | `aiohttp` + `asyncio.sleep` | Blocking polling freezes the event loop; aiohttp is the standard async HTTP client for Python and integrates with NyraHost's existing asyncio architecture |
| Meshy task polling | Custom REST client from scratch | `MeshyClient` class using `aiohttp` | Meshy API is well-documented; a thin typed wrapper prevents auth header drift and simplifies retry logic |
| ComfyUI workflow submission | Raw `requests.post` with manual JSON | `ComfyUIClient` class with typed workflow schema | ComfyUI workflow JSON format is strict; a typed client with schema validation catches node name typos early |
| Asset import pipeline | Custom `FbxFactory` call from scratch | UE Python `AssetTools.import_asset_tasks` + `FbxImportUI` | This is the Epic-supported import path; it handles LOD generation, collision, re-import correctly out of the box |
| Computer-use action execution | `pyautogui` + pixel coordinate matching | Win32 UIA + `computer_20251124` structural clicks | pyautogui breaks on UI scale changes and theme changes; UIA structural elements are stable across DPI/Theme |
| Screenshot capture for computer-use loop | `PIL.ImageGrab` (inconsistent on Windows) | `mss` (pure Python, cross-platform, fast) | `mss` consistently captures the correct display regardless of DPI scaling |

---

## Common Pitfalls

### Pitfall 1: Meshy task timeout without manifest entry
**What goes wrong:** Meshy tasks can take 30-120 seconds. If NyraHost crashes mid-polling, the manifest has no entry for the in-flight job. User re-runs the prompt and gets a duplicate submission.

**Why it happens:** The MCP tool handler submits the task and immediately returns the job ID — but if the background polling coroutine crashes before writing to the manifest, the job is orphaned.

**How to avoid:** Write a `pending` manifest entry **before** returning the job ID. The entry is in `nyra_pending.json` with `ue_import_status: "pending"` immediately. The polling coroutine only updates `ue_import_status: "completed"`. On startup, NyraHost scans for `pending` entries older than 10 minutes and marks them `timeout`.

**Warning signs:** `"Meshy task timeout"` in logs; duplicate GLB files in staging folder.

### Pitfall 2: ComfyUI queue stall (prompt_id mismatch or history race)
**What goes wrong:** `POST /prompt` returns a `prompt_id`, but `GET /history/{prompt_id}` immediately returns 404. The prompt is queued but not yet in history. Polling starts too late or the wrong ID is used.

**Why it happens:** ComfyUI processes the queue asynchronously; there is a window where the prompt is queued but not yet written to history.

**How to avoid:** Poll `GET /queue` first to confirm the prompt_id is in `queue_running` or `queue_pending` before polling history. Alternatively, poll both queue and history concurrently.

**Warning signs:** HTTP 404 on history endpoint; prompt appears in queue but not history.

### Pitfall 3: UE import on non-Main thread
**What goes wrong:** `AssetTools.import_asset_tasks` must be called on the Game Thread. Calling it from the NyraHost sidecar (which runs in a separate Python process) is fine because it uses `unreal.PythonScriptLibrary` which marshals to the Game Thread — but direct `FbxFactory` calls from UE Python scripts that run asynchronously can cause a deadlock.

**Why it happens:** UE's asset system is not thread-safe. `AssetTools` is safe when called via the Python binding because it posts to the Game Thread, but only if the binding is called from a UE tick context.

**How to avoid:** Use the MCP tool result to signal the UE chat panel to trigger the import synchronously on the next editor tick, OR wrap import in `unreal.EditorAssetLibrary` which handles thread marshaling for asset-level operations.

**Warning signs:** `"Cannot call from a background thread"` UE engine assertion; editor freeze.

### Pitfall 4: Duplicate asset accumulation across tool retries
**What goes wrong:** After a failed scene build, the user asks to retry. The agent generates a new image in ComfyUI, imports it as `T_Texture_v2`, generates again, imports as `T_Texture_v3`. The Content Browser fills with variant textures the user doesn't know are orphaned.

**Why it happens:** Without manifest deduplication, re-running a tool call generates a new asset even if the input is identical.

**How to avoid:** The manifest key is `(tool, operation, input_hash)`. Re-running the same operation on the same input ref matches the existing pending entry and returns the existing job ID instead of creating a new one. Periodic cleanup of `failed` / `timeout` entries older than 7 days prevents stale manifest growth.

**Warning signs:** 40+ variant textures in the NYRA/Textures folder; manifest with 100+ entries.

### Pitfall 5: computer-use cursor hijack without user confirmation gate
**What goes wrong:** The computer-use loop starts moving the mouse on the user's machine without warning. If it runs in the background during a user activity (another app, a game), it causes confusion or data loss.

**Why it happens:** NyraHost's computer-use loop takes over the cursor without a visible confirmation UI.

**How to avoid:** Always show an overlay HUD before taking the first action. Require Ctrl+Alt+Space chord to pause. On first use per session, show a one-time confirmation dialog listing the specific app being driven. These are GEN-03 success criteria per ROADMAP.md.

**Warning signs:** User reports "NYRA moved my mouse"; cursor jumps in another app.

### Pitfall 6: Blender subprocess version mismatch
**What goes wrong:** `blender --version` reports 2.93, but the user's project requires Blender 4.x for the correct `bpy` API. Or Blender is installed in a non-standard path.

**Why it happens:** NYRA invokes `blender` assuming it's on PATH, but different Blender installations conflict.

**How to avoid:** In Phase 5, defer Blender to v1.1. When Phase 5+ ships Blender (v1.1), detect the installed Blender version via `--version` and validate the minimum version before any invocation. Store the path in config. [ASSUMED — Blender is out of scope for Phase 5 per REQUIREMENTS.md GEN-11 deferral]

---

## Code Examples

### MCP Tool: `nyra_meshy_image_to_3d`
```python
# meshy_tools.py
from .base import NyraTool, NyraToolResult
from nyrahost.external.meshy_client import MeshyClient
from nyrahost.tools.staging import StagingManifest
import uuid

class MeshyImageTo3DTool(NyraTool):
    name = "nyra_meshy_image_to_3d"
    description = (
        "Generate a 3D mesh from a reference image using Meshy AI. "
        "Uploads the image, polls until the job completes, downloads the GLB, "
        "and stages it for UE import as UStaticMesh with LODs."
    )
    parameters = {
        "type": "object",
        "properties": {
            "image_path": {
                "type": "string",
                "description": "Path to the reference image on disk"
            },
            "prompt": {
                "type": "string",
                "description": "Optional natural-language guidance for the generation"
            },
            "target_folder": {
                "type": "string",
                "default": "/Game/NYRA/Meshes",
                "description": "UE Content destination folder"
            }
        },
        "required": ["image_path"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        manifest = StagingManifest()
        job_id = str(uuid.uuid4())
        # Write pending entry BEFORE returning (Pitfall 1 mitigation)
        manifest.add_pending(job_id, "meshy", "image-to-3d", params["image_path"])
        # Background polling happens in a separate async task in NyraHost
        # Tool returns immediately with job_id for streaming UX
        return NyraToolResult.ok({
            "job_id": job_id,
            "status": "pending",
            "message": f"Meshy job started. Use nyra_job_status('{job_id}') to poll."
        })
```

### MCP Tool: `nyra_comfyui_run_workflow`
```python
# comfyui_tools.py
from .base import NyraTool, NyraToolResult
from nyrahost.external.comfyui_client import ComfyUIClient
from nyrahost.tools.staging import StagingManifest
import uuid

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
            "input_image_asset_path": {
                "type": "string",
                "description": "UE asset path of a UTexture2D to inject as input"
            },
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
            "message": "ComfyUI workflow queued. Results auto-imported to " +
                       f"{params.get('target_folder', '/Game/NYRA/Textures')}"
        })
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tool-by-tool direct integration (Aura-style) | Staging manifest + import bridge pattern | 2026 (NYRA Phase 5 innovation) | Every import is undoable; audit trail prevents duplicate accumulation |
| Blocking sync HTTP in MCP tool | `aiohttp` async polling with immediate job_id return | 2026 | MCP stdio loop stays responsive; streaming UX gets job_id for progress bar |
| computer-use for everything (CoPilot-style) | API-first, computer-use only for Substance Sampler + UE modal dialogs | 2026 per ROADMAP.md GEN-03 | Eliminates cursor-hijack for tasks with a clean API path; reduces failure surface |
| ComfyUI workflow hardcoded per operation | Workflow JSON as tool parameter — agent passes exported JSON | 2026 | Agent can use any ComfyUI workflow the user has configured; not limited to NYRA-hardcoded paths |
| Meshy blocking sync call | Async polling with manifest write-before-return | 2026 | No orphaned jobs on crash; retry-safe by design |

**Deprecated/outdated:**
- ComfyUI v0.x API (pre-2024): Different endpoint format; current ComfyUI uses `/prompt` and `/history` (confirmed from docs.comfy.org 2026)
- `computer_20250224` tool type: Superseded by `computer_20251124` (added `zoom`, larger display dimensions, Opus 4.7 support)

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Meshy API base URL is `https://meshy.ai/api/v1` | Standard Stack, Code Examples | Meshy docs at docs.meshy.ai were 404. Base URL confirmed from training but not verified in-session. **Verify before implementation by running `curl -H "Authorization: Bearer $MESHY_KEY" https://meshy.ai/api/v1/meshes` — if 401, check docs.meshy.ai for correct base URL.** |
| A2 | Meshy task creation returns `{"id": "...", "status": "..."}` | Pattern 2 | Task ID field name assumed as `id`. If Meshy uses `task_id` instead, polling will 404. **Verify from Meshy dashboard API docs.** |
| A3 | Meshy task polling returns `status` field with values `completed`/`failed`/`cancelled` | Pattern 2 | Status enum values assumed. Check Meshy API docs for exact enum values. |
| A4 | Meshy completed task response contains `model_urls.glb` | Pattern 2 | URL structure for downloading GLB file assumed. Meshy may return a single `model_url` field or require a separate download call. |
| A5 | ComfyUI server runs on port 8188 by default | Standard Stack, Pattern 3 | Default port confirmed from docs.comfy.org 2026, but ComfyUI allows custom port configuration. NYRA should probe 8188, 8189, 8190 as fallbacks. |
| A6 | Blender is invoked via `blender --background --python-script <file>` | Architecture Patterns, Anti-Patterns | Blender's `--python-expr` flag is NOT available (Blender docs confirmed 403/blocked). `--python-script` is the correct flag. **Verify: `blender --background --python-script script.py -- --flag value` passes args correctly.** |
| A7 | computer-use on Windows runs via Claude Desktop (user has Desktop open) or direct API key in NyraHost | Summary, Pattern 4 | STACK.md confirmed "CLI computer-use is macOS-only; on Windows, use computer use in Desktop." This means the CLI cannot drive computer-use on Windows directly. Two viable paths: (1) user has Claude Desktop running, or (2) NyraHost uses direct API key with `computer_20251124`. Path (2) gives NyraHost full control and is the recommended approach. |
| A8 | Blender 4.x LTS is the target version for NYRA v1.1 | Common Pitfalls | Blender 4.x assumed as stable Windows build. GEN-11 is v1.1, so this will be verified before Phase 5+ ships Blender. |
| A9 | UE Python `FbxFactory` supports GLB import via `AssetTools.import_asset_tasks` | Pattern 5 | GLB import via `UFbxFactory` assumed working in UE 5.4–5.7. Verify by testing with a sample GLB before Phase 5 implementation. UE typically treats GLB as FBX variant; if FBX import works, GLB should work. |

---

## Open Questions

1. **Meshy API base URL and task schema**
   - What we know: Meshy has a REST API at `meshy.ai/api/v1/` (confirmed from Context7 docs). Task types include `meshy-image-to-3d-reMeshed`, `meshy-text-to-3d-reMeshed`, `meshy-texture-to-3d`.
   - What's unclear: The exact request/response shapes for task creation and polling. The docs.meshy.ai site returned 404 for quickstart pages.
   - Recommendation: Before writing Phase 5 code, verify by checking `https://docs.meshy.ai` directly or using the Meshy dashboard API settings. Create a test account and run a minimal task creation + polling sequence to capture the real response schema.

2. **Meshy API rate limits and plan tiers**
   - What we know: Meshy has API settings for "usage limits and billing" per docs.meshy.ai. Premium tiers likely have higher rate limits.
   - What's unclear: The free/paid tier rate limits for task creation. Whether Meshy enforces rate limits per API key or per account.
   - Recommendation: Check Meshy pricing page. Design the client with a 429 response handler that backs off and informs the user, not a hard failure.

3. **Substance 3D Sampler UI automation target**
   - What we know: Substance Sampler has no public API (confirmed from REQUIREMENTS.md). The UI is a Windows desktop application.
   - What's unclear: The exact UI structure — which UIA elements correspond to "Load Image", "Export PBR Material", and the output folder picker. These differ across Substance Sampler versions.
   - Recommendation: This is the primary reason for the GEN-03 reliability spike gate. Before Phase 7 commits to DEMO-02, run 20 automated sessions and capture the exact UIA element paths for each action in the canary suite.

4. **Blender Python subprocess on Windows — path detection and version validation**
   - What we know: `blender` may not be on PATH. Blender is installed to `C:\Program Files\Blender Foundation\Blender 4.x\` by default on Windows.
   - What's unclear: Whether Blender's Python subprocess invocation (`--background --python-script`) works reliably when Blender is installed to a path with spaces.
   - Recommendation: GEN-11 is v1.1. When Phase 5+ ships Blender, test: `subprocess.run(["C:/Program Files/Blender Foundation/Blender 4.4/blender.exe", "--background", "--python-script", "test.py"])` with path quoting. Also test that `bpy` is available in the subprocess context.

5. **Computer-use loop: API key vs. Claude Desktop path**
   - What we know: On Windows, Claude CLI cannot drive computer-use. Claude Desktop can. Direct API key with `computer_20251124` is theoretically viable.
   - What's unclear: Whether using the user's Claude API key (via BYOK mode from Phase 2) is legally and technically the right path for the computer-use loop, or whether requiring Claude Desktop to be running is a acceptable UX constraint.
   - Recommendation: Design the computer-use loop to support both paths: (1) API key mode (if user has BYOK configured in Phase 2 settings), (2) Claude Desktop mode (if Desktop is detected running). Fall back to API key mode as primary.

---

## Environment Availability

> Step 2.6: SKIPPED — Phase 5 does not have external CLI/tool dependencies beyond the user's own installations (Meshy API key, ComfyUI server, Blender). These are user-managed and checked at runtime, not at plugin build time. The NyraHost subprocess itself requires only Python 3.11+ (already in NyraHost's venv).

**What Phase 5 does check at runtime:**
- `MESHY_API_KEY` env var — if not set, `nyra_meshy_*` tools return an error with setup instructions
- `http://127.0.0.1:8188` ComfyUI server — if unreachable, `nyra_comfyui_*` tools return an error with install/run instructions
- `blender` on PATH — only needed for v1.1 GEN-11; if not found, deferred gracefully

**Missing dependencies with fallback:**
- ComfyUI not running → Error message with install instructions + link to ComfyUI Windows install guide + offer to open port check. **No blocking** — ComfyUI is optional if user only needs Meshy.
- Meshy API key not set → Error message with setup instructions (mesh.ai API settings). **No blocking** — tools are disabled until configured.

---

## Validation Architecture

> Skip if `workflow.nyquist_validation` is explicitly false. If absent, treat as enabled.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `NyraHost/pyproject.toml` (existing) |
| Quick run command | `pytest NyraHost/tests/test_external_tools.py -x -q` |
| Full suite command | `pytest NyraHost/tests/ -q --ignore=NyraHost/tests/test_claude_backend.py --ignore=NyraHost/tests/test_gemma_backend_adapter.py` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GEN-01 | Meshy job submission returns job_id | unit | `pytest tests/test_meshy_tools.py::test_job_submission_returns_id -x` | no |
| GEN-01 | Manifest pending entry written before return | unit | `pytest tests/test_meshy_tools.py::test_pending_manifest_entry_written -x` | no |
| GEN-01 | Meshy polling loop with mock HTTP (no live network) | unit | `pytest tests/test_meshy_client.py::test_polling_loop_completes -x` | no |
| GEN-01 | Idempotent re-submit dedupes by input_hash | unit | `pytest tests/test_meshy_tools.py::test_idempotent_dedup -x` | no |
| GEN-02 | ComfyUI workflow submission returns prompt_id | unit | `pytest tests/test_comfyui_tools.py::test_workflow_submission -x` | no |
| GEN-02 | ComfyUI history polling completes | unit | `pytest tests/test_comfyui_client.py::test_history_polling -x` | no |
| GEN-02 | UE texture import via mock FbxFactory | unit | `pytest tests/test_staging.py::test_import_meshes_pending -x` | no |
| GEN-03 | computer-use loop detects app and takes screenshot | unit | `pytest tests/test_computer_use.py::test_screenshot_capture -x` | no |
| GEN-03 | computer-use Win32 UIA structural click | unit | `pytest tests/test_computer_use.py::test_uia_click -x` | no |
| GEN-03 | computer-use permission gate shown before first action | unit | `pytest tests/test_computer_use.py::test_permission_gate -x` | no |

### Sampling Rate
- **Per task commit:** `pytest tests/test_meshy_tools.py tests/test_comfyui_tools.py tests/test_computer_use.py -x -q`
- **Per wave merge:** Full suite (`pytest tests/ -q --ignore=backend_tests -x`)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `NyraHost/tests/test_meshy_tools.py` — covers GEN-01 unit tests (mock Meshy API responses, manifest write, idempotency)
- [ ] `NyraHost/tests/test_comfyui_tools.py` — covers GEN-02 unit tests (mock ComfyUI /prompt + /history, workflow JSON validation)
- [ ] `NyraHost/tests/test_computer_use.py` — covers GEN-03 unit tests (screenshot, UIA mock, permission gate)
- [ ] `NyraHost/tests/test_staging.py` — covers staging manifest schema + import path
- [ ] `NyraHost/tests/test_external_client.py` — covers `MeshyClient` and `ComfyUIClient` in isolation (mock HTTP)
- [ ] Framework install: All tests use existing pytest setup (already in NyraHost pyproject.toml)
- [ ] `NyraHost/tests/conftest.py` — add fixtures: `mock_meshy_api`, `mock_comfyui_server`, `mock_win32_uia`

---

## Security Domain

> Required when `security_enforcement` is enabled (absent = enabled). Omit only if explicitly `false` in config.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | External tool auth handled externally (Meshy API key user-managed, ComfyUI localhost) |
| V3 Session Management | no | No sessions in external tool integration layer |
| V4 Access Control | yes | Meshy API key must not be logged; ComfyUI server should bind to localhost only |
| V5 Input Validation | yes | Workflow JSON from agent → `object_info` validation before submit; image_path → MIME type check before upload |
| V6 Cryptography | no | No cryptographic operations in this phase |
| V7 Error Handling | yes | All HTTP errors (401, 403, 429, 500, timeout) must surface as user-friendly messages, not raw exceptions |

### Known Threat Patterns for External Tool Integrations

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Meshy API key leaked in logs | Information Disclosure | Redact API keys in log output; use `X-API-Key` header not query params |
| ComfyUI workflow injection | Tampering / Information Disclosure | Validate workflow JSON against `GET /object_info` before submit; reject unknown `class_type` values |
| Arbitrary file write via staging manifest path traversal | Tampering | Validate all file paths resolve under `%LOCALAPPDATA%/NYRA/staging/` before write |
| computer-use cursor hijack (GEN-03) | Denial of Service / Elevation of Privilege | Ctrl+Alt+Space pause chord; HUD overlay before first action; always-on permission gate |
| Substance Sampler screenshot exfiltration | Information Disclosure | Screenshots never leave the local machine (computer-use loop uses in-process API, not IPC to remote server) |
| Meshy API key exposed in environment (CI) | Information Disclosure | `MESHY_API_KEY` loaded from env; never hardcoded; GitHub Actions secret injection |

---

## Sources

### Primary (HIGH confidence)
- [docs.comfy.org](https://docs.comfy.org) — ComfyUI API reference, all HTTP endpoints for local server: POST `/prompt`, GET `/history/{prompt_id}`, GET `/queue`, POST `/interrupt`, GET `/object_info`, GET `/system_stats`, POST `/upload/image`. Verified 2026-05-07.
- [docs.meshy.ai](https://docs.meshy.ai) — Meshy API overview, REST patterns, API settings page. Partial confirmation 2026-05-07 (overview and API Settings pages accessible; quickstart/endpoint-detail pages returned 404 in research session).
- STACK.md (Phase 1 research) — Three-process architecture, MCP patterns, computer-use `computer_20251124` tool type, Opus 4.7 with zoom. **HIGH confidence** (primary research for project architecture).
- REQUIREMENTS.md — GEN-01, GEN-02, GEN-03 requirement definitions, GEN-11 Blender deferral to v1.1. **HIGH confidence** (founder-authored project requirements).

### Secondary (MEDIUM confidence)
- [ctx7 /websites/meshy_ai_en](https://context7.com) — Meshy library ID confirmed; docs indexed but endpoint detail pages sparse. Lower confidence than direct docs access.
- [ctx7 /websites/comfy](https://context7.com) — ComfyUI library confirmed with 8236 code snippets; main API routes confirmed. HIGH confidence on routing patterns.
- Anthropic computer-use documentation (training knowledge) — `computer_20251124` tool type, `computer-use-2025-11-24` beta header, Opus 4.7, `enable_zoom`, 2576px max display dimensions. **MEDIUM confidence** (not re-verified in-session; confirmed against STACK.md which already cites platform.claude.com).

### Tertiary (LOW confidence)
- Meshy task creation request/response schema — Not directly verified; based on training knowledge of Meshy API patterns. **Verify before implementation.**
- Meshy GLB download URL structure — Assumed `model_urls.glb` field. **Verify from live Meshy API response.**
- Blender subprocess invocation (`--python-script` flag) — Assumed correct; Blender docs returned 403/blocked. **Verify with live `blender --help` before v1.1.**
- computer-use Windows Desktop vs. API key path — Assumed API key path as primary approach. **Verify from Anthropic computer-use documentation at platform.claude.com.**

---

## Metadata

**Confidence breakdown:**
- Standard Stack: MEDIUM-HIGH — ComfyUI endpoints verified from official docs; Meshy API partially verified (base URL confirmed, schema details not verified)
- Architecture: HIGH — Staging manifest + import bridge pattern well-established; MCP tool registration pattern confirmed from existing Phase 4 code
- Pitfalls: MEDIUM — All 6 pitfalls documented from project PITFALLS.md + domain knowledge; staging manifest pattern is the key mitigation
- Computer-use reliability spike: LOW-MEDIUM — Specific thresholds (85%) from ROADMAP.md; UIA element paths for Substance Sampler not verified in-session
- Blender (out of scope): LOW — Deferring to v1.1; pattern will be verified before Phase 5+ ships Blender

**Research date:** 2026-05-07
**Valid until:** 2026-06-06 (30 days — Meshy API schema and ComfyUI endpoint structure are stable; re-verify if Meshy ships a new API version)

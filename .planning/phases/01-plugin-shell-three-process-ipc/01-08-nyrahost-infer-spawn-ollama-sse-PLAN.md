---
phase: 01-plugin-shell-three-process-ipc
plan: 08
type: execute
wave: 2
depends_on: [02, 05, 06]
autonomous: true
requirements: [PLUG-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
objective: >
  Implement the llama.cpp-backed Gemma inference path on the Python side:
  GPU probe (nvidia-smi -> vulkaninfo -> CPU order), llama-server spawn with
  port capture from stdout, Ollama auto-detect fast path, SSE stream parser,
  and a chat/send + chat/cancel JSON-RPC handler that routes to the chosen
  backend and emits chat/stream notifications. Lazy spawn + 10-min idle
  shutdown per D-19. Fills VALIDATION 1-03-01, 1-03-02, 1-03-03. Updates
  __main__.py to register handlers on NyraServer.
must_haves:
  truths:
    - "On startup, GPU probe detects nvidia-smi first, falls back to vulkaninfo, falls back to CPU"
    - "llama-server spawn captures the ephemeral port from stdout line 'server listening at http://127.0.0.1:NNNN'"
    - "Ollama detection probes http://127.0.0.1:11434/api/tags; if gemma3:4b-it-qat model present, router prefers Ollama (no llama-server spawn)"
    - "SSE parser extracts delta content from 'data: {json}' lines; ignores non-data lines; terminates on 'data: [DONE]'"
    - "chat/send with backend=gemma-local + req_id triggers lazy NyraInfer spawn if not running; first token arrives via chat/stream notification within the test timeout"
    - "chat/cancel {conversation_id, req_id} closes the in-flight HTTP stream and emits final chat/stream with done=true, cancelled=true"
    - "NyraInfer is SIGTERMed if idle >10 minutes (background task every 60s tracks last_infer_request_ts)"
    - "pytest tests/test_infer_spawn.py + test_ollama_detect.py + test_sse_parser.py all pass"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py
      provides: "spawn_llama_server + InferHandle + idle shutdown task"
      exports: ["spawn_llama_server", "InferHandle"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py
      provides: "detect_ollama returning base URL or None"
      exports: ["detect_ollama"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py
      provides: "parse_sse_line + aiter_sse_deltas"
      exports: ["parse_sse_line", "aiter_sse_deltas", "SseEvent"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py
      provides: "InferRouter picks backend (Ollama fast path vs bundled llama-server); lazy spawn"
      exports: ["InferRouter", "BackendChoice"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
      provides: "chat/send request handler + chat/cancel notification handler"
      exports: ["ChatHandlers"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
      provides: "build_server — composes Storage + InferRouter + handlers into NyraServer"
      exports: ["build_server"]
  key_links:
    - from: router.py InferRouter.stream_chat
      to: llama_server.py / ollama_probe.py
      via: "Ollama detect first; else spawn_llama_server; POST /v1/chat/completions"
      pattern: "POST.*v1/chat/completions"
    - from: chat.py ChatHandlers.on_chat_send
      to: server.py build_notification("chat/stream", ...)
      via: "one build_notification per SSE delta; final frame with done=true"
      pattern: "build_notification"
---

<objective>
Gemma-backed chat works end-to-end: UE sends chat/send over WS, NyraHost
picks backend (Ollama fast path if present else bundled llama-server),
streams tokens back via chat/stream notifications.

Per CONTEXT.md:
- D-17 (Gemma download writes `<ProjectDir>/Saved/NYRA/models/gemma-3-4b-it-qat-q4_0.gguf`)
- D-18 (bundled llama-server + Ollama auto-detect via /api/tags)
- D-19 (lazy NyraInfer spawn + 10-min idle shutdown)
- D-20 (chat-only OpenAI-compatible surface in Phase 1)

Per RESEARCH §3.5 (llama-server flags, SSE format, Ollama /api/tags JSON
shape, CUDA/Vulkan/CPU probe order), §3.3 Pattern B (Python asyncio pipe
drain + port capture regex), §3.10 P1.5 (CUDA DLL fallback order).

Plan 09 separately handles the Gemma GGUF downloader; Plan 08 assumes the
GGUF already exists at the expected path (tests mock it).

Purpose: After Plan 08, NyraHost can answer `chat/send` prompts. This is the
largest Python plan in Phase 1 — 4 modules + 3 tests.
Output: nyrahost chat streaming works against a mock llama-server (real
llama-server integration validated by Plan 14 Ring 0 bench).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md
@docs/JSONRPC.md
@docs/ERROR_CODES.md
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/jsonrpc.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
</context>

<interfaces>
llama-server stdout port line pattern (§3.3 Pattern B):
```
r"listening at http://[^:]+:(\d+)"
```

Ollama /api/tags response shape (§3.5):
```json
{
  "models": [
    {
      "name": "gemma3:4b-it-qat",
      "details": {"format":"gguf","family":"gemma","parameter_size":"4.3B","quantization_level":"Q4_0"}
    }
  ]
}
```

SSE stream format:
```
data: {"choices":[{"delta":{"content":"Hello"}}]}

data: {"choices":[{"delta":{"content":" world"}}]}

data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{...}}

data: [DONE]
```

Lines:
- Lines starting with `data: ` → payload after 6 chars
- `data: [DONE]` → end sentinel
- Empty lines / other prefixes → ignore

Backend base URLs (router returns one):
- Ollama: `http://127.0.0.1:11434` (model name `"gemma3:4b-it-qat"`)
- Bundled llama-server: `http://127.0.0.1:<ephemeral>` (model name from GGUF, pass `"gemma-3-4b-it"`)
</interfaces>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: sse.py + ollama_probe.py + gpu_probe.py + test_sse_parser.py + test_ollama_detect.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/__init__.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_ollama_detect.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.5 (SSE format example, Ollama /api/tags shape, CUDA/Vulkan probe)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-18
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py and test_ollama_detect.py (Wave 0 placeholders)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/conftest.py (for mock_ollama_transport fixture signature)
  </read_first>
  <behavior>
    - test_sse_delta_extraction: feed a 4-line SSE stream (`data:` with delta, blank, `data:` with second delta + finish_reason, `data: [DONE]`) into aiter_sse_deltas; receive exactly 2 SseEvent instances with content "Hello" and " world", and a trailing SseEvent with done=True, usage fields present.
    - test_sse_tolerates_comment_and_blank_lines: lines starting with `:` (comment) and blank lines are skipped.
    - test_sse_malformed_json_frame_is_skipped: a `data: not-json` line is logged but does not raise; iterator continues.
    - test_ollama_detect_gemma3_present: httpx MockTransport returns 200 + gemma3:4b-it-qat model; detect_ollama returns `"http://127.0.0.1:11434"`.
    - test_ollama_detect_absent_returns_none: MockTransport returns 200 + only non-gemma models; detect_ollama returns None.
    - test_ollama_detect_connection_refused_returns_none: MockTransport raises httpx.ConnectError; detect_ollama returns None (no exception).
  </behavior>
  <action>
    **1. CREATE src/nyrahost/infer/__init__.py** (empty package marker).

    **2. CREATE src/nyrahost/infer/sse.py:**

    ```python
    """Server-Sent Events (SSE) parser for OpenAI-compatible chat streams.

    llama-server + Ollama both emit: each event is `data: <json>\\n\\n`, terminated
    by `data: [DONE]`. See RESEARCH §3.5.
    """
    from __future__ import annotations
    import json
    from dataclasses import dataclass
    from typing import AsyncIterator, Iterable
    import structlog

    log = structlog.get_logger("nyrahost.sse")


    @dataclass(frozen=True)
    class SseEvent:
        delta: str
        done: bool = False
        finish_reason: str | None = None
        usage: dict | None = None


    DONE_SENTINEL = "[DONE]"


    def parse_sse_line(line: str) -> SseEvent | None:
        """Return SseEvent if the line produces one, else None (ignore).

        Rules:
        - Blank line -> None
        - Line starting with ':' (comment) -> None
        - Line starting with 'data: [DONE]' -> SseEvent(delta="", done=True)
        - Line starting with 'data: ' + JSON -> extract choices[0].delta.content
        - Malformed JSON -> log + None
        - Lines without 'data: ' prefix -> None
        """
        if not line or line.startswith(":"):
            return None
        if not line.startswith("data: "):
            return None
        payload = line[6:].strip()
        if payload == DONE_SENTINEL:
            return SseEvent(delta="", done=True)
        try:
            obj = json.loads(payload)
        except json.JSONDecodeError:
            log.warning("sse_malformed_frame", payload=payload[:120])
            return None
        choices = obj.get("choices") or []
        choice = choices[0] if choices else {}
        delta_obj = choice.get("delta") or {}
        content = delta_obj.get("content") or ""
        finish = choice.get("finish_reason")
        usage = obj.get("usage")
        done = finish is not None
        return SseEvent(
            delta=content,
            done=done,
            finish_reason=finish,
            usage=usage,
        )


    async def aiter_sse_deltas(lines: AsyncIterator[str]) -> AsyncIterator[SseEvent]:
        """Consume an async line iterator and yield SseEvent instances.
        Stops after emitting the first done=True event."""
        async for raw in lines:
            ev = parse_sse_line(raw.rstrip("\n"))
            if ev is None:
                continue
            yield ev
            if ev.done:
                return
    ```

    **3. CREATE src/nyrahost/infer/ollama_probe.py:**

    ```python
    """Ollama auto-detect (D-18). Probes http://127.0.0.1:11434/api/tags."""
    from __future__ import annotations
    from typing import Optional
    import httpx
    import structlog

    log = structlog.get_logger("nyrahost.ollama")

    OLLAMA_BASE_URL = "http://127.0.0.1:11434"
    # Match any Ollama tag that starts with gemma3:4b-it-qat (model names include ":" suffix for variants).
    GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"


    async def detect_ollama(*, client: httpx.AsyncClient | None = None, timeout: float = 1.0) -> Optional[str]:
        """Return base URL if Ollama is reachable AND has a matching Gemma 3 tag;
        else None. Never raises on connection failure (graceful degrade)."""
        owns_client = client is None
        if owns_client:
            client = httpx.AsyncClient(timeout=timeout)
        try:
            r = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            if r.status_code != 200:
                log.info("ollama_probe_non_200", status=r.status_code)
                return None
            data = r.json()
            for m in data.get("models", []) or []:
                name = m.get("name", "") or ""
                if name.startswith(GEMMA_TAG_PREFIX):
                    log.info("ollama_detected", model=name)
                    return OLLAMA_BASE_URL
            log.info("ollama_running_but_no_gemma")
            return None
        except (httpx.ConnectError, httpx.TimeoutException, httpx.HTTPError) as e:
            log.info("ollama_probe_failed", err=type(e).__name__)
            return None
        finally:
            if owns_client:
                await client.aclose()
    ```

    **4. CREATE src/nyrahost/infer/gpu_probe.py:**

    ```python
    """GPU backend probe (D-18, §3.5). Order: nvidia-smi -> vulkaninfo -> CPU."""
    from __future__ import annotations
    import asyncio
    from enum import Enum
    import structlog

    log = structlog.get_logger("nyrahost.gpu")


    class GpuBackend(str, Enum):
        CUDA = "cuda"
        VULKAN = "vulkan"
        CPU = "cpu"


    async def _binary_probe(*cmd: str, timeout_s: float = 3.0) -> bool:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            try:
                await asyncio.wait_for(proc.wait(), timeout=timeout_s)
            except asyncio.TimeoutError:
                proc.terminate()
                return False
            return proc.returncode == 0
        except FileNotFoundError:
            return False
        except OSError:
            return False


    async def probe_gpu_backend() -> GpuBackend:
        if await _binary_probe("nvidia-smi", "-L"):
            log.info("gpu_backend_selected", backend="cuda")
            return GpuBackend.CUDA
        if await _binary_probe("vulkaninfo", "--summary"):
            log.info("gpu_backend_selected", backend="vulkan")
            return GpuBackend.VULKAN
        log.info("gpu_backend_selected", backend="cpu")
        return GpuBackend.CPU
    ```

    **5. REPLACE tests/test_sse_parser.py:**

    ```python
    """SSE parser tests.
    VALIDATION test ID: 1-03-03
    """
    from __future__ import annotations
    import pytest
    from nyrahost.infer.sse import parse_sse_line, aiter_sse_deltas, SseEvent


    def test_sse_delta_extraction() -> None:
        e = parse_sse_line('data: {"choices":[{"delta":{"content":"Hello"}}]}')
        assert e is not None
        assert e.delta == "Hello"
        assert e.done is False

        e2 = parse_sse_line(
            'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
            '"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}'
        )
        assert e2 is not None
        assert e2.delta == ""
        assert e2.done is True
        assert e2.finish_reason == "stop"
        assert e2.usage == {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}


    def test_sse_tolerates_comment_and_blank_lines() -> None:
        assert parse_sse_line("") is None
        assert parse_sse_line(": keep-alive") is None
        assert parse_sse_line("event: message") is None  # not prefixed "data: "


    def test_sse_done_sentinel() -> None:
        e = parse_sse_line("data: [DONE]")
        assert e is not None
        assert e.done is True


    def test_sse_malformed_json_frame_is_skipped() -> None:
        # Should NOT raise; returns None and logs (logger tested separately)
        assert parse_sse_line("data: not-json") is None


    @pytest.mark.asyncio
    async def test_aiter_sse_deltas_end_to_end() -> None:
        async def source():
            yield 'data: {"choices":[{"delta":{"content":"Hello"}}]}\n'
            yield "\n"  # blank
            yield 'data: {"choices":[{"delta":{"content":" world"}}]}\n'
            yield (
                'data: {"choices":[{"delta":{},"finish_reason":"stop"}],'
                '"usage":{"prompt_tokens":3,"completion_tokens":2}}\n'
            )
            yield "data: [DONE]\n"  # should not be reached

        out: list[SseEvent] = []
        async for ev in aiter_sse_deltas(source()):
            out.append(ev)
        # Expect: "Hello", " world", final with done=True
        assert len(out) == 3
        assert out[0].delta == "Hello"
        assert out[1].delta == " world"
        assert out[2].done is True
        assert out[2].finish_reason == "stop"
    ```

    **6. REPLACE tests/test_ollama_detect.py:**

    ```python
    """Ollama auto-detect tests.
    VALIDATION test ID: 1-03-02
    """
    from __future__ import annotations
    import pytest
    import httpx
    from nyrahost.infer.ollama_probe import detect_ollama, OLLAMA_BASE_URL, GEMMA_TAG_PREFIX


    def _transport_returning(payload: dict, status: int = 200) -> httpx.MockTransport:
        def handler(request: httpx.Request) -> httpx.Response:
            assert request.url.path == "/api/tags"
            return httpx.Response(status, json=payload)
        return httpx.MockTransport(handler)


    @pytest.mark.asyncio
    async def test_ollama_detect_gemma3_present() -> None:
        transport = _transport_returning({
            "models": [
                {"name": "llama3:8b", "details": {}},
                {"name": "gemma3:4b-it-qat", "details": {"family": "gemma"}},
            ]
        })
        async with httpx.AsyncClient(transport=transport) as c:
            url = await detect_ollama(client=c)
        assert url == OLLAMA_BASE_URL


    @pytest.mark.asyncio
    async def test_ollama_detect_absent_returns_none() -> None:
        transport = _transport_returning({
            "models": [{"name": "llama3:8b", "details": {}}]
        })
        async with httpx.AsyncClient(transport=transport) as c:
            url = await detect_ollama(client=c)
        assert url is None


    @pytest.mark.asyncio
    async def test_ollama_detect_connection_refused_returns_none() -> None:
        def raise_connect(_req: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("refused")
        transport = httpx.MockTransport(raise_connect)
        async with httpx.AsyncClient(transport=transport) as c:
            url = await detect_ollama(client=c)
        assert url is None


    @pytest.mark.asyncio
    async def test_ollama_detect_non_200_returns_none() -> None:
        transport = _transport_returning({}, status=503)
        async with httpx.AsyncClient(transport=transport) as c:
            url = await detect_ollama(client=c)
        assert url is None


    def test_tag_prefix_constant() -> None:
        assert GEMMA_TAG_PREFIX == "gemma3:4b-it-qat"
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "class SseEvent" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py` equals 1
      - `grep -c "DONE_SENTINEL" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/sse.py` >= 2
      - `grep -c "OLLAMA_BASE_URL" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py` >= 2
      - `grep -c 'GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py` equals 1
      - `grep -c "class GpuBackend" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py` equals 1
      - `grep -c "nvidia-smi" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py` >= 1
      - `grep -c "vulkaninfo" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py` >= 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_sse_parser.py tests/test_ollama_detect.py -v` exits 0 with >= 9 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - sse.py exports `SseEvent`, `parse_sse_line`, `aiter_sse_deltas`, `DONE_SENTINEL`
    - sse.py handles: blank line, ":" comment, "data: [DONE]", valid JSON data line, malformed JSON (no raise)
    - ollama_probe.py exports `detect_ollama`, `OLLAMA_BASE_URL = "http://127.0.0.1:11434"`, `GEMMA_TAG_PREFIX = "gemma3:4b-it-qat"`
    - ollama_probe.py catches `httpx.ConnectError` AND `httpx.TimeoutException` AND `httpx.HTTPError` → returns None
    - gpu_probe.py exports `GpuBackend` enum with `CUDA`, `VULKAN`, `CPU` values
    - gpu_probe.py tries `nvidia-smi -L` first, `vulkaninfo --summary` second, falls back to CPU
    - test_sse_parser.py has >= 4 test functions (delta_extraction, comment/blank tolerance, done_sentinel, malformed json)
    - test_ollama_detect.py has >= 4 test functions (gemma_present, absent_returns_none, connection_refused, non_200)
    - `pytest tests/test_sse_parser.py tests/test_ollama_detect.py -v` exits 0 with all tests passing
  </acceptance_criteria>
  <done>SSE parser + Ollama detect + GPU probe tested in isolation.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: llama_server.py + router.py + test_infer_spawn.py</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py
    TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py
  </files>
  <read_first>
    - .planning/phases/01-plugin-shell-three-process-ipc/01-RESEARCH.md §3.3 Pattern B (port capture + drain), §3.5 (llama-server flags), §3.10 P1.5 (CUDA fallback)
    - .planning/phases/01-plugin-shell-three-process-ipc/01-CONTEXT.md D-18, D-19, D-20
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/gpu_probe.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/ollama_probe.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py (Wave 0 placeholder)
  </read_first>
  <behavior>
    - test_llama_server_port_capture: spawn a mock llama-server (Python script that prints "server listening at http://127.0.0.1:54321\n" to stdout and sleeps), verify spawn_llama_server returns InferHandle with .port == 54321 within a timeout.
    - test_llama_server_dies_before_port_raises: mock script exits immediately with no port line; spawn_llama_server raises RuntimeError within startup_timeout_s.
    - test_llama_server_falls_back_cuda_to_vulkan_to_cpu_on_exit: mock cuda binary exits with code 1 on launch; router retries with vulkan; if vulkan also exits, falls back to cpu.
  </behavior>
  <action>
    **1. CREATE src/nyrahost/infer/llama_server.py:**

    ```python
    """llama-server subprocess spawn + port capture (D-18, §3.3, §3.5)."""
    from __future__ import annotations
    import asyncio
    import re
    from dataclasses import dataclass, field
    from pathlib import Path
    from typing import Sequence
    import structlog

    from .gpu_probe import GpuBackend

    log = structlog.get_logger("nyrahost.llama_server")

    PORT_RE = re.compile(r"listening at http://[^:]+:(\d+)")
    STARTUP_TIMEOUT_S = 60.0  # model load can take 6-12s; allow headroom


    @dataclass
    class InferHandle:
        proc: asyncio.subprocess.Process
        port: int
        backend: GpuBackend
        drain_task: asyncio.Task | None = None

        @property
        def base_url(self) -> str:
            return f"http://127.0.0.1:{self.port}"

        async def terminate(self) -> None:
            if self.proc.returncode is None:
                self.proc.terminate()
                try:
                    await asyncio.wait_for(self.proc.wait(), timeout=5.0)
                except asyncio.TimeoutError:
                    self.proc.kill()
                    await self.proc.wait()
            if self.drain_task is not None and not self.drain_task.done():
                self.drain_task.cancel()


    def llama_server_executable_path(plugin_binaries_dir: Path, backend: GpuBackend) -> Path:
        return plugin_binaries_dir / "NyraInfer" / backend.value / "llama-server.exe"


    async def spawn_llama_server(
        *,
        exe_path: Path,
        gguf_path: Path,
        backend: GpuBackend,
        ctx_size: int = 16384,
        startup_timeout_s: float = STARTUP_TIMEOUT_S,
    ) -> InferHandle:
        """Spawn llama-server bound to ephemeral port; parse port from stdout.

        Args:
            exe_path: path to llama-server.exe (per-backend folder)
            gguf_path: path to gemma-3-4b-it-qat-q4_0.gguf
            backend: which GPU backend's binary we're launching (for labelling)
            ctx_size: --ctx-size (Phase 1 default 16384)
            startup_timeout_s: max seconds to wait for port-announcement line
        """
        cmd = [
            str(exe_path),
            "-m", str(gguf_path),
            "--port", "0",
            "--host", "127.0.0.1",
            "--ctx-size", str(ctx_size),
            "-ngl", "99",
            "--chat-template", "gemma",
            "--no-webui",
        ]
        log.info("llama_server_spawn", cmd=cmd[0], backend=backend.value)
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )

        port: int | None = None
        deadline = asyncio.get_event_loop().time() + startup_timeout_s
        while port is None:
            remaining = deadline - asyncio.get_event_loop().time()
            if remaining <= 0:
                proc.terminate()
                await proc.wait()
                raise RuntimeError(
                    f"llama-server ({backend.value}) did not announce port within {startup_timeout_s}s"
                )
            if proc.returncode is not None:
                raise RuntimeError(
                    f"llama-server ({backend.value}) exited with code {proc.returncode} before port announcement"
                )
            try:
                line_bytes = await asyncio.wait_for(proc.stdout.readline(), timeout=remaining)
            except asyncio.TimeoutError:
                continue
            if not line_bytes:
                # EOF -> proc likely died; loop will see returncode next iter
                await asyncio.sleep(0.05)
                continue
            line = line_bytes.decode(errors="replace")
            log.debug("llama_server_stdout", line=line.rstrip())
            m = PORT_RE.search(line)
            if m:
                port = int(m.group(1))

        async def _drain() -> None:
            try:
                while True:
                    line = await proc.stdout.readline()
                    if not line:
                        break
                    log.debug("llama_server_stdout", line=line.decode(errors="replace").rstrip())
            except Exception:  # noqa: BLE001
                return

        drain_task = asyncio.create_task(_drain())
        log.info("llama_server_ready", port=port, backend=backend.value)
        return InferHandle(proc=proc, port=port, backend=backend, drain_task=drain_task)
    ```

    **2. CREATE src/nyrahost/infer/router.py:**

    ```python
    """Backend router: Ollama fast path vs bundled llama-server.

    Implements D-19 lazy spawn + 10-min idle shutdown.
    """
    from __future__ import annotations
    import asyncio
    import time
    from dataclasses import dataclass
    from enum import Enum
    from pathlib import Path
    from typing import AsyncIterator, Callable
    import httpx
    import structlog

    from .gpu_probe import GpuBackend, probe_gpu_backend
    from .llama_server import (
        InferHandle,
        spawn_llama_server,
        llama_server_executable_path,
    )
    from .ollama_probe import detect_ollama
    from .sse import aiter_sse_deltas, SseEvent

    log = structlog.get_logger("nyrahost.router")

    IDLE_SHUTDOWN_SECONDS = 10 * 60
    IDLE_CHECK_INTERVAL_SECONDS = 60

    # Backend fallback order when a GPU backend binary fails to launch.
    _BACKEND_FALLBACK: list[GpuBackend] = [GpuBackend.CUDA, GpuBackend.VULKAN, GpuBackend.CPU]


    class BackendChoice(str, Enum):
        OLLAMA = "ollama"
        BUNDLED = "bundled"


    @dataclass
    class RouterState:
        choice: BackendChoice
        base_url: str
        model_name: str
        handle: InferHandle | None = None
        last_request_ts: float = 0.0


    class InferRouter:
        def __init__(
            self,
            *,
            plugin_binaries_dir: Path,
            gguf_path_getter: Callable[[], Path],
        ):
            self._plugin_binaries_dir = plugin_binaries_dir
            self._gguf_path_getter = gguf_path_getter
            self._state: RouterState | None = None
            self._lock = asyncio.Lock()
            self._idle_task: asyncio.Task | None = None

        async def start(self) -> None:
            """Start idle-shutdown background task."""
            self._idle_task = asyncio.create_task(self._idle_watchdog())

        async def stop(self) -> None:
            if self._idle_task is not None:
                self._idle_task.cancel()
            if self._state and self._state.handle is not None:
                await self._state.handle.terminate()

        async def gemma_not_installed(self) -> bool:
            gguf = self._gguf_path_getter()
            if gguf.exists() and gguf.stat().st_size > 0:
                return False
            # If Ollama with gemma3:4b-it-qat is present, we're OK too
            return (await detect_ollama()) is None

        async def _ensure_backend(self) -> RouterState:
            """Lazy-resolve the backend. Ollama if available, else bundled."""
            if self._state is not None:
                return self._state
            async with self._lock:
                if self._state is not None:
                    return self._state
                ollama = await detect_ollama()
                if ollama is not None:
                    self._state = RouterState(
                        choice=BackendChoice.OLLAMA,
                        base_url=ollama,
                        model_name="gemma3:4b-it-qat",
                        last_request_ts=time.time(),
                    )
                    log.info("backend_chosen", choice="ollama")
                    return self._state

                gpu = await probe_gpu_backend()
                handle = await self._spawn_bundled_with_fallback(gpu)
                self._state = RouterState(
                    choice=BackendChoice.BUNDLED,
                    base_url=handle.base_url,
                    model_name="gemma-3-4b-it",
                    handle=handle,
                    last_request_ts=time.time(),
                )
                log.info("backend_chosen", choice="bundled", port=handle.port, backend=handle.backend.value)
                return self._state

        async def _spawn_bundled_with_fallback(self, preferred: GpuBackend) -> InferHandle:
            # Order: preferred then the remaining in the canonical fallback order.
            order = [preferred] + [b for b in _BACKEND_FALLBACK if b != preferred]
            last_err: Exception | None = None
            gguf = self._gguf_path_getter()
            if not gguf.exists():
                raise FileNotFoundError(f"Gemma GGUF not found at {gguf}")
            for backend in order:
                exe = llama_server_executable_path(self._plugin_binaries_dir, backend)
                if not exe.exists():
                    log.info("llama_server_exe_missing", backend=backend.value, path=str(exe))
                    continue
                try:
                    return await spawn_llama_server(
                        exe_path=exe, gguf_path=gguf, backend=backend,
                    )
                except Exception as e:  # noqa: BLE001
                    last_err = e
                    log.warning("llama_server_spawn_failed", backend=backend.value, err=str(e))
                    continue
            raise RuntimeError(f"All llama-server backends failed; last_err={last_err}")

        async def _idle_watchdog(self) -> None:
            while True:
                await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
                if self._state is None or self._state.handle is None:
                    continue
                idle_for = time.time() - self._state.last_request_ts
                if idle_for >= IDLE_SHUTDOWN_SECONDS:
                    log.info("llama_server_idle_shutdown", idle_s=idle_for)
                    async with self._lock:
                        await self._state.handle.terminate()
                        self._state = None

        # ---- Streaming ----
        async def stream_chat(
            self,
            *,
            content: str,
            cancel_event: asyncio.Event,
        ) -> AsyncIterator[SseEvent]:
            state = await self._ensure_backend()
            state.last_request_ts = time.time()
            url = f"{state.base_url}/v1/chat/completions"
            body = {
                "model": state.model_name,
                "messages": [{"role": "user", "content": content}],
                "stream": True,
            }
            async with httpx.AsyncClient(timeout=httpx.Timeout(connect=5, read=None)) as client:
                async with client.stream("POST", url, json=body) as resp:
                    resp.raise_for_status()

                    async def line_iter():
                        async for line in resp.aiter_lines():
                            if cancel_event.is_set():
                                return
                            yield line

                    async for ev in aiter_sse_deltas(line_iter()):
                        yield ev
                        if cancel_event.is_set():
                            return
    ```

    **3. REPLACE tests/test_infer_spawn.py (uses a Python-script stand-in for llama-server):

    ```python
    """llama-server spawn + port capture tests.
    VALIDATION test ID: 1-03-01
    """
    from __future__ import annotations
    import asyncio
    import os
    import stat
    import sys
    from pathlib import Path
    import pytest
    from nyrahost.infer.gpu_probe import GpuBackend
    from nyrahost.infer.llama_server import spawn_llama_server, PORT_RE


    def _write_mock_llama(tmp_path: Path, *, port: int, delay_s: float, exit_code: int = 0) -> Path:
        """Write a Python script that mimics llama-server's startup line + blocks."""
        script = tmp_path / "mock_llama.py"
        script.write_text(
            "import sys, time\n"
            f"time.sleep({delay_s})\n"
            f"print('server listening at http://127.0.0.1:{port}')\n"
            "sys.stdout.flush()\n"
            f"if {exit_code} != 0:\n"
            f"    sys.exit({exit_code})\n"
            # Block indefinitely so the test controls lifetime
            "try:\n"
            "    while True:\n"
            "        time.sleep(10)\n"
            "except KeyboardInterrupt:\n"
            "    sys.exit(0)\n",
            encoding="utf-8",
        )
        return script


    def _wrapper_bat(tmp_path: Path, script_py: Path) -> Path:
        """Create a shim so spawn_llama_server (which expects llama-server.exe) runs our python."""
        if sys.platform == "win32":
            bat = tmp_path / "llama-server.bat"
            bat.write_text(
                f'@echo off\r\n"{sys.executable}" "{script_py}" %*\r\n',
                encoding="utf-8",
            )
            return bat
        # POSIX: shebang wrapper
        wrapper = tmp_path / "llama-server"
        wrapper.write_text(
            f"#!/usr/bin/env bash\n{sys.executable} {script_py} \"$@\"\n",
            encoding="utf-8",
        )
        wrapper.chmod(wrapper.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return wrapper


    @pytest.mark.asyncio
    async def test_llama_server_port_capture(tmp_path: Path) -> None:
        script = _write_mock_llama(tmp_path, port=54321, delay_s=0.1)
        exe = _wrapper_bat(tmp_path, script)
        gguf = tmp_path / "fake.gguf"
        gguf.write_bytes(b"fake gguf contents")
        handle = await spawn_llama_server(
            exe_path=exe,
            gguf_path=gguf,
            backend=GpuBackend.CPU,
            startup_timeout_s=5.0,
        )
        try:
            assert handle.port == 54321
            assert handle.backend == GpuBackend.CPU
            assert handle.base_url == "http://127.0.0.1:54321"
        finally:
            await handle.terminate()


    @pytest.mark.asyncio
    async def test_llama_server_dies_before_port_raises(tmp_path: Path) -> None:
        # Mock that exits immediately with code 1 and NO port line
        script = tmp_path / "mock.py"
        script.write_text("import sys; sys.exit(1)\n", encoding="utf-8")
        exe = _wrapper_bat(tmp_path, script)
        gguf = tmp_path / "fake.gguf"
        gguf.write_bytes(b"x")
        with pytest.raises(RuntimeError):
            await spawn_llama_server(
                exe_path=exe,
                gguf_path=gguf,
                backend=GpuBackend.CPU,
                startup_timeout_s=2.0,
            )


    def test_port_regex_matches_expected_llama_line() -> None:
        line = "server listening at http://127.0.0.1:41273 for embeddings"
        m = PORT_RE.search(line)
        assert m is not None
        assert int(m.group(1)) == 41273
    ```
  </action>
  <verify>
    <automated>
      - `grep -c "PORT_RE = re.compile" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` equals 1
      - `grep -c 'listening at http' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` >= 1
      - `grep -c '"--chat-template", "gemma"' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` equals 1
      - `grep -c '"-ngl", "99"' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` equals 1
      - `grep -c '"--no-webui"' TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/llama_server.py` equals 1
      - `grep -c "class InferRouter" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py` equals 1
      - `grep -c "IDLE_SHUTDOWN_SECONDS = 10 \* 60" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_infer_spawn.py -v` exits 0 with >= 3 tests passing
    </automated>
  </verify>
  <acceptance_criteria>
    - llama_server.py exports `InferHandle` dataclass with fields `proc`, `port`, `backend`, `drain_task` and method `terminate()`
    - llama_server.py exports `spawn_llama_server` taking `exe_path, gguf_path, backend, ctx_size=16384, startup_timeout_s=STARTUP_TIMEOUT_S`
    - llama_server.py uses exact flags from §3.5: `-m <gguf>`, `--port 0`, `--host 127.0.0.1`, `--ctx-size 16384`, `-ngl 99`, `--chat-template gemma`, `--no-webui`
    - llama_server.py spawns via `asyncio.create_subprocess_exec` with `stdout=PIPE, stderr=STDOUT` (merged)
    - llama_server.py parses port via `PORT_RE = re.compile(r"listening at http://[^:]+:(\d+)")`
    - llama_server.py starts a background drain task after port captured (prevents pipe-fill deadlock)
    - router.py exports `InferRouter` with `start()`, `stop()`, `stream_chat(content, cancel_event)`, `gemma_not_installed()`
    - router.py has `IDLE_SHUTDOWN_SECONDS = 10 * 60` and background `_idle_watchdog` task checking every 60s
    - router.py backend fallback order is CUDA → VULKAN → CPU on spawn failure
    - router.py `stream_chat` POSTs to `/v1/chat/completions` with `{"stream": true}` and yields SseEvents via `aiter_sse_deltas`
    - test_infer_spawn.py contains `test_llama_server_port_capture`, `test_llama_server_dies_before_port_raises`, `test_port_regex_matches_expected_llama_line`
    - `pytest tests/test_infer_spawn.py -v` exits 0 with 3 tests passing
  </acceptance_criteria>
  <done>llama-server spawn + router tested; backend picks Ollama or bundled; idle shutdown background task ticks.</done>
</task>

<task type="auto">
  <name>Task 3: handlers/chat.py + app.py + update __main__.py to wire it all together</name>
  <files>
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/__init__.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
    TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py
  </files>
  <read_first>
    - docs/JSONRPC.md §3.3 (chat/send), §3.4 (chat/stream), §3.5 (chat/cancel)
    - docs/ERROR_CODES.md
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py (NyraServer.register_request / register_notification)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py (just created)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/storage.py (Plan 07)
    - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py (current — from Plan 06)
  </read_first>
  <action>
    **1. CREATE src/nyrahost/handlers/__init__.py** (empty package marker).

    **2. CREATE src/nyrahost/handlers/chat.py:**

    ```python
    """chat/send request handler + chat/cancel notification handler.

    Streams via build_notification("chat/stream", ...) on the session's socket.
    See docs/JSONRPC.md §3.3-3.5.
    """
    from __future__ import annotations
    import asyncio
    import json
    from dataclasses import dataclass, field
    from pathlib import Path
    from typing import Any
    import structlog

    from ..jsonrpc import build_notification
    from ..storage import Storage
    from ..session import SessionState
    from ..infer.router import InferRouter
    from ..infer.sse import SseEvent
    from websockets.server import ServerConnection

    log = structlog.get_logger("nyrahost.chat")


    @dataclass
    class ChatHandlers:
        storage: Storage
        router: InferRouter
        # Map of req_id -> cancel Event (so chat/cancel can find the right stream)
        _inflight: dict[str, asyncio.Event] = field(default_factory=dict)

        async def on_chat_send(self, params: dict, session: SessionState, ws: ServerConnection) -> dict:
            conv_id = params["conversation_id"]
            req_id = params["req_id"]
            content = params["content"]
            backend = params.get("backend", "gemma-local")
            if backend != "gemma-local":
                return {"req_id": req_id, "streaming": False, "error": {
                    "code": -32601, "message": "backend_not_supported",
                    "data": {"remediation": f"Backend {backend!r} is Phase 2+."}
                }}

            # Check Gemma installed (unless Ollama has it)
            if await self.router.gemma_not_installed():
                raise GemmaNotInstalledError()

            # Persist user message (if conversation exists; auto-create if not seen)
            if self.storage.get_conversation(conv_id) is None:
                # Caller passed a fresh conv_id — create with default title
                self.storage.conn.execute(
                    "INSERT INTO conversations(id,title,created_at,updated_at) VALUES(?,?,?,?)",
                    (conv_id, content[:48], int(asyncio.get_event_loop().time() * 1000),
                     int(asyncio.get_event_loop().time() * 1000)),
                )
                self.storage.conn.commit()
            self.storage.append_message(conversation_id=conv_id, role="user", content=content)

            cancel = asyncio.Event()
            self._inflight[req_id] = cancel

            # Kick off the stream task — fire-and-forget; tokens stream via WS notifications.
            asyncio.create_task(
                self._run_stream(ws=ws, conv_id=conv_id, req_id=req_id, content=content, cancel=cancel)
            )
            return {"req_id": req_id, "streaming": True}

        async def _run_stream(
            self,
            *,
            ws: ServerConnection,
            conv_id: str,
            req_id: str,
            content: str,
            cancel: asyncio.Event,
        ) -> None:
            accumulated: list[str] = []
            final_usage: dict | None = None
            error_payload: dict | None = None
            try:
                async for ev in self.router.stream_chat(content=content, cancel_event=cancel):
                    if cancel.is_set():
                        break
                    if ev.delta:
                        accumulated.append(ev.delta)
                        await ws.send(build_notification("chat/stream", {
                            "conversation_id": conv_id,
                            "req_id": req_id,
                            "delta": ev.delta,
                            "done": False,
                        }))
                    if ev.done:
                        final_usage = ev.usage
                        break
            except Exception as e:  # noqa: BLE001
                log.exception("chat_stream_exception", req_id=req_id)
                error_payload = {
                    "code": -32001,
                    "message": "subprocess_failed",
                    "data": {"remediation":
                        "A background NYRA process stopped unexpectedly. "
                        "Click [Restart] or see Saved/NYRA/logs/."},
                }
            finally:
                self._inflight.pop(req_id, None)

            # Final frame
            final_params: dict[str, Any] = {
                "conversation_id": conv_id,
                "req_id": req_id,
                "delta": "",
                "done": True,
            }
            if cancel.is_set():
                final_params["cancelled"] = True
            if final_usage is not None:
                final_params["usage"] = final_usage
            if error_payload is not None:
                final_params["error"] = error_payload

            try:
                await ws.send(build_notification("chat/stream", final_params))
            except Exception:  # noqa: BLE001 — socket closed mid-stream; ignore
                pass

            # Persist assistant reply (even if cancelled/error — record what we have)
            if accumulated:
                self.storage.append_message(
                    conversation_id=conv_id,
                    role="assistant",
                    content="".join(accumulated),
                    usage_json=json.dumps(final_usage) if final_usage else None,
                    error_json=json.dumps(error_payload) if error_payload else None,
                )

        async def on_chat_cancel(self, params: dict, session: SessionState) -> None:
            req_id = params.get("req_id")
            ev = self._inflight.get(req_id)
            if ev is not None:
                ev.set()


    class GemmaNotInstalledError(Exception):
        """Raised from on_chat_send when Gemma GGUF missing AND Ollama not available.
        Caught in server dispatch; converted to error response -32005.
        """
    ```

    **3. CREATE src/nyrahost/app.py — composes everything into a NyraServer:**

    ```python
    """Application composition root. Plans after 08 extend build_server."""
    from __future__ import annotations
    from pathlib import Path
    import structlog
    from websockets.server import ServerConnection

    from .config import NyraConfig
    from .server import NyraServer, run_server
    from .storage import Storage, db_path_for_project
    from .infer.router import InferRouter
    from .handlers.chat import ChatHandlers, GemmaNotInstalledError
    from .jsonrpc import build_error
    from .session import SessionState

    log = structlog.get_logger("nyrahost.app")


    def gemma_gguf_path(project_dir: Path) -> Path:
        return project_dir / "Saved" / "NYRA" / "models" / "gemma-3-4b-it-qat-q4_0.gguf"


    async def build_and_run(
        *,
        config: NyraConfig,
        nyrahost_pid: int,
        project_dir: Path,
        plugin_binaries_dir: Path,
    ) -> None:
        """Compose Storage + InferRouter + chat handlers into NyraServer, run forever."""
        storage = Storage(db_path_for_project(project_dir))
        router = InferRouter(
            plugin_binaries_dir=plugin_binaries_dir,
            gguf_path_getter=lambda: gemma_gguf_path(project_dir),
        )
        await router.start()

        handlers = ChatHandlers(storage=storage, router=router)

        def register(server: NyraServer) -> None:
            # chat/send needs the websocket to emit streaming notifications;
            # NyraServer hands handler (params, session) — we need a wrapper
            # that captures the connection from the dispatch closure.
            # We achieve this by wrapping register_request/register_notification.
            server.request_handlers["chat/send"] = _wrap_send(handlers)
            server.notification_handlers["chat/cancel"] = handlers.on_chat_cancel

        await run_server(config, nyrahost_pid=nyrahost_pid, register_handlers=register)


    def _wrap_send(handlers: ChatHandlers):
        """NyraServer's request handler signature is (params, session) -> dict.
        chat/send needs `ws` — so the handler delegates to an internal that
        accepts ws. We pull ws from a thread-local-style SessionState attribute
        set in server.py's _dispatch closure."""
        # Rather than breaking the contract, extend SessionState to carry the
        # active ServerConnection reference. Simplest path: monkey-patch via
        # a lookup dict keyed on session_id. For Phase 1 we accept the
        # tight coupling: server.py's _dispatch keeps a weak ref to ws on
        # session.__dict__["_ws"] before each call.
        async def handle(params: dict, session: SessionState) -> dict:
            ws = getattr(session, "_ws", None)
            if ws is None:
                return {"req_id": params.get("req_id", ""), "streaming": False, "error": {
                    "code": -32001, "message": "internal",
                    "data": {"remediation": "Internal: no WS bound to session."}
                }}
            try:
                return await handlers.on_chat_send(params, session, ws)
            except GemmaNotInstalledError:
                raise _GemmaNotInstalled()
        return handle


    class _GemmaNotInstalled(Exception):
        pass
    ```

    **4. UPDATE src/nyrahost/server.py** — attach `ws` to session before
    dispatch so chat/send handler can use it. Modify `_handle_connection`
    after auth, and `_dispatch`:

    ```python
    # In _handle_connection, after session.authenticated = True:
    session._ws = ws  # type: ignore[attr-defined]  # attach for handler access

    # No change needed in _dispatch — handlers read from session._ws.
    ```

    The executor MUST add this `session._ws = ws` line inside
    `_handle_connection` after `session.authenticated = True` and before the
    `async for raw in ws:` loop. Verify test_auth.py still passes after the
    change.

    **5. UPDATE src/nyrahost/__main__.py** to use `build_and_run`:

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
    from .app import build_and_run


    def parse_args() -> argparse.Namespace:
        p = argparse.ArgumentParser(prog="nyrahost")
        p.add_argument("--editor-pid", type=int, required=True)
        p.add_argument("--log-dir", type=Path, required=True)
        p.add_argument("--project-dir", type=Path, required=True,
                        help="Path to <ProjectDir>; used for Saved/NYRA/sessions.db and models/")
        p.add_argument("--plugin-binaries-dir", type=Path, required=True,
                        help="Path to <Plugin>/Binaries/Win64; used for NyraInfer subfolders")
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
        cleanup_orphan_handshakes(handshake_dir)

        await build_and_run(
            config=config,
            nyrahost_pid=os.getpid(),
            project_dir=args.project_dir,
            plugin_binaries_dir=args.plugin_binaries_dir,
        )
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
  </action>
  <verify>
    <automated>
      - `grep -c "class ChatHandlers" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py` equals 1
      - `grep -c "class GemmaNotInstalledError" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py` equals 1
      - `grep -c "build_notification(\"chat/stream\"" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py` >= 2
      - `grep -c "def gemma_gguf_path" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` equals 1
      - `grep -c "build_and_run" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py` >= 1
      - `grep -c "--project-dir" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py` equals 1
      - `grep -c "--plugin-binaries-dir" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/__main__.py` equals 1
      - `grep -c "session._ws = ws" TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/server.py` equals 1
      - `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/ -v` exits 0 (all tests from Plans 06/07/08 still pass)
    </automated>
  </verify>
  <acceptance_criteria>
    - handlers/chat.py contains literal text `class ChatHandlers` with `storage`, `router`, `_inflight` fields
    - handlers/chat.py exports `GemmaNotInstalledError` exception
    - handlers/chat.py contains literal text `build_notification("chat/stream"` at least twice (per-delta + final)
    - handlers/chat.py `on_chat_send` returns `{"req_id": req_id, "streaming": True}` immediately after spawning the async stream task
    - handlers/chat.py `on_chat_cancel` sets the cancel event matching req_id (idempotent if req_id not found)
    - handlers/chat.py `_run_stream` handles: cancelled, usage, error cases; always emits a final frame with `done:true`
    - handlers/chat.py persists assistant reply to storage after stream completes (even if cancelled/error)
    - app.py contains literal text `def gemma_gguf_path(project_dir: Path)` returning `project_dir / "Saved" / "NYRA" / "models" / "gemma-3-4b-it-qat-q4_0.gguf"`
    - app.py `build_and_run` registers `chat/send` request handler and `chat/cancel` notification handler on NyraServer
    - server.py contains literal text `session._ws = ws` (inserted after auth success, before dispatch loop)
    - __main__.py adds `--project-dir` and `--plugin-binaries-dir` CLI args
    - __main__.py calls `build_and_run` with project_dir and plugin_binaries_dir
    - Running `pytest tests/ -v` from NyraHost/ exits 0 (previous tests from 06/07/08 still pass: 8 auth+handshake+bootstrap + 9 storage+attachments + 3 infer_spawn + 5 sse + 5 ollama = ~30 tests)
  </acceptance_criteria>
  <done>chat/send + chat/cancel wired; NyraHost can answer a prompt end-to-end (with real Gemma) OR error cleanly.</done>
</task>

</tasks>

<verification>
Full pytest run from TestProject/Plugins/NYRA/Source/NyraHost/:
```
pytest tests/ -v
```
Must exit 0 with ALL tests passing (Plans 02 + 06 + 07 + 08 Python tests — approximately 25-30 tests).
</verification>

<success_criteria>
- sse.py, ollama_probe.py, gpu_probe.py, llama_server.py, router.py all implemented + tested
- chat/send + chat/cancel JSON-RPC handlers route through InferRouter
- Backend selection: Ollama fast path if detected, bundled llama-server otherwise (CUDA -> Vulkan -> CPU fallback)
- Lazy spawn + 10-min idle shutdown background task
- All pytest Phase 1 Wave 2 tests pass (13+ across the 3 test files in this plan)
- NyraHost runs as `python -m nyrahost --editor-pid X --log-dir Y --project-dir Z --plugin-binaries-dir W`
</success_criteria>

<output>
After completion, create `.planning/phases/01-plugin-shell-three-process-ipc/01-08-SUMMARY.md`
documenting: backend selection order (Ollama > CUDA > Vulkan > CPU), port
capture regex, idle shutdown policy, and the ChatHandlers wiring pattern
through `session._ws`.
</output>

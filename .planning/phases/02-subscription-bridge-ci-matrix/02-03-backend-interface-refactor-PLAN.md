---
phase: 02-subscription-bridge-ci-matrix
plan: 03
slug: backend-interface-refactor
type: execute
wave: 0
depends_on: []
autonomous: true
tdd: true
requirements: [SUBS-03]
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/base.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/gemma.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_backend_interface.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_backend_adapter.py
research_refs: [§2.5]
context_refs: [D-01, D-24]
phase0_clearance_required: false
must_haves:
  truths:
    - "nyrahost.backends.base.AgentBackend ABC defines async send(conversation_id, req_id, content, attachments, mcp_config_path, on_event), async cancel(req_id), async health_check() methods"
    - "BackendEvent tagged union covers Delta(text), ToolUse(id,name,input_json), ToolResult(id,output), Done(usage,stop_reason), Error(code,message,remediation,retryable), Retry(attempt,delay_ms,error_category)"
    - "nyrahost.backends.gemma.GemmaBackend(AgentBackend) wraps Phase 1 nyrahost.infer.router.InferRouter — zero behaviour change; every Phase 1 pytest still passes"
    - "nyrahost.backends.__init__.py exports a BACKEND_REGISTRY: dict[str, type[AgentBackend]] with 'gemma-local': GemmaBackend pre-registered; v1.1 Codex drop-in appends 'codex': CodexBackend without touching the router"
    - "handlers/chat.py.ChatHandlers.on_chat_send dispatches by params.backend ('gemma-local' default; 'claude' raises NotImplementedError with remediation hint pointing to Plan 02-04 until that plan lands)"
    - "app.py wiring updated to construct GemmaBackend + register with BACKEND_REGISTRY; ChatHandlers instantiated with the registry (not the raw InferRouter)"
    - "test_backend_interface.py asserts: (a) AgentBackend cannot be instantiated directly (ABC); (b) a minimal Dummy(AgentBackend) that implements all three methods satisfies isinstance(x, AgentBackend); (c) BackendEvent tagged-union discriminator works via isinstance checks; (d) BACKEND_REGISTRY['gemma-local'] is GemmaBackend"
    - "test_gemma_backend_adapter.py asserts: (a) GemmaBackend.health_check returns installed status from Plan 08's InferRouter.gemma_not_installed() inverse; (b) GemmaBackend.send emits Delta events wrapping Phase 1 SSE deltas; (c) GemmaBackend.cancel routes through Phase 1's existing cancel path"
    - "Full pytest suite passes: existing 34 tests + 2+ new test files (Phase 1 liquidation preserved, no @pytest.mark.skip regressions)"
  artifacts:
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/base.py
      provides: "AgentBackend ABC + BackendEvent tagged union + HealthState enum"
      exports: ["AgentBackend", "BackendEvent", "Delta", "ToolUse", "ToolResult", "Done", "Error", "Retry", "HealthState"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/gemma.py
      provides: "GemmaBackend(AgentBackend) wrapping Phase 1 InferRouter"
      exports: ["GemmaBackend"]
    - path: TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py
      provides: "BACKEND_REGISTRY + convenience factory"
      exports: ["BACKEND_REGISTRY", "get_backend(name)"]
  key_links:
    - from: GemmaBackend.send
      to: nyrahost.infer.router.InferRouter.stream_chat
      via: "Adapter layer wraps SSE deltas as BackendEvent.Delta, final done frame as Done, errors as Error"
      pattern: "async for.*yield Delta"
    - from: handlers/chat.py.ChatHandlers.on_chat_send
      to: BACKEND_REGISTRY[params.backend]
      via: "Registry lookup; default 'gemma-local' preserves Phase 1 behaviour"
      pattern: "BACKEND_REGISTRY\\[.*backend.*\\]"
---

<objective>
Refactor Phase 1's Gemma path behind a backend-agnostic abstract base class so Plan 02-04 (Claude adapter) can drop in as a second concrete implementation and Plan 02-05 (router) can switch on `params.backend` without touching wire code.

**This is NOT a behaviour change** — Phase 1's Gemma chat path is functionally identical after this refactor. Every Phase 1 pytest (the 34 passing tests landed in Plan 01-09) MUST pass unchanged after this plan lands.

Per CONTEXT.md:
- D-01: backend-abstract router refactor is Wave 0; every subsequent plan targets `AgentBackend`, not a concrete
- D-24: module-superset on `app.py` and `handlers/chat.py` — Phase 1 content preserved verbatim, this plan adds a dispatch dimension

Per RESEARCH §2.5 interface contract.

**TDD:** RED commits write failing tests for the abstract contract + Gemma adapter behaviour; GREEN commits extract the Gemma wrapper + register with the registry. Pattern matches Phase 1's RED/GREEN discipline (Plan 01-06 onwards).
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/02-subscription-bridge-ci-matrix/02-CONTEXT.md
@.planning/phases/02-subscription-bridge-ci-matrix/02-RESEARCH.md
@.planning/phases/01-plugin-shell-three-process-ipc/01-08-nyrahost-infer-spawn-ollama-sse-SUMMARY.md
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/infer/router.py

<interfaces>
<!-- RESEARCH §2.5 authoritative contract — implement exactly this: -->

```python
# nyrahost/backends/base.py
from __future__ import annotations
import abc
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Literal, Union

from nyrahost.attachments import AttachmentRef


class HealthState(str, Enum):
    READY = "ready"
    NOT_INSTALLED = "not-installed"
    AUTH_DRIFT = "auth-drift"
    RATE_LIMITED = "rate-limited"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Delta:
    text: str


@dataclass(frozen=True)
class ToolUse:
    id: str
    name: str
    input_json: str          # partial or complete


@dataclass(frozen=True)
class ToolResult:
    id: str
    output: str


@dataclass(frozen=True)
class Done:
    usage: dict                # {input_tokens, output_tokens, ...}
    stop_reason: str           # "end_turn" | "tool_use" | "max_tokens" | "error" | "cancelled"


@dataclass(frozen=True)
class Error:
    code: int                  # JSON-RPC error code (see ERROR_CODES.md)
    message: str
    remediation: str
    retryable: bool


@dataclass(frozen=True)
class Retry:
    attempt: int
    delay_ms: int
    error_category: Literal[
        "authentication_failed",
        "billing_error",
        "rate_limit",
        "invalid_request",
        "server_error",
        "max_output_tokens",
        "unknown",
    ]


BackendEvent = Union[Delta, ToolUse, ToolResult, Done, Error, Retry]


class AgentBackend(abc.ABC):
    """Abstract base class for every reasoning backend (Claude, Gemma, future Codex)."""

    name: str  # "claude" | "gemma-local" | "codex" (v1.1)

    @abc.abstractmethod
    async def send(
        self,
        conversation_id: str,
        req_id: str,
        content: str,
        attachments: list[AttachmentRef],
        mcp_config_path: Path | None,
        on_event: Callable[[BackendEvent], Awaitable[None]],
    ) -> None:
        """Emit BackendEvent objects via on_event; MUST end with a Done or Error event."""

    @abc.abstractmethod
    async def cancel(self, req_id: str) -> None: ...

    @abc.abstractmethod
    async def health_check(self) -> HealthState: ...
```

```python
# nyrahost/backends/__init__.py
from nyrahost.backends.base import AgentBackend, BackendEvent, Delta, ToolUse, ToolResult, Done, Error, Retry, HealthState
from nyrahost.backends.gemma import GemmaBackend

BACKEND_REGISTRY: dict[str, type[AgentBackend]] = {
    "gemma-local": GemmaBackend,
}


def get_backend(name: str) -> type[AgentBackend]:
    try:
        return BACKEND_REGISTRY[name]
    except KeyError as e:
        raise ValueError(f"Unknown backend: {name!r}. Registered: {list(BACKEND_REGISTRY)}") from e
```

GemmaBackend wraps Phase 1's InferRouter; ChatHandlers.on_chat_send dispatches on params.backend:

```python
# Snippet in handlers/chat.py.on_chat_send:
backend_name = getattr(params, "backend", "gemma-local")
if backend_name == "claude":
    # Plan 02-04 will wire this; for now raise with remediation hint
    raise NotImplementedError(
        "Claude backend lands in Plan 02-04 (claude-subprocess-driver). "
        "Current backend 'gemma-local' still works."
    )
backend_cls = BACKEND_REGISTRY[backend_name]
backend = backend_cls(self._infer_router)  # DI from app.py
await backend.send(..., on_event=self._emit_chat_stream)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1 (RED): Write failing abstract-contract + GemmaBackend tests</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/tests/test_backend_interface.py, TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_backend_adapter.py</files>
  <behavior>
    - test_backend_interface.py: `test_abc_rejects_direct_instantiation` — `AgentBackend()` raises TypeError because abstract
    - test_backend_interface.py: `test_dummy_subclass_satisfies_isinstance` — minimal subclass implementing all 3 abstracts satisfies isinstance(inst, AgentBackend)
    - test_backend_interface.py: `test_backend_event_tagged_union_isinstance` — given Delta/Done/Error/Retry instances, isinstance checks route correctly
    - test_backend_interface.py: `test_registry_has_gemma_local` — `BACKEND_REGISTRY['gemma-local']` is GemmaBackend
    - test_backend_interface.py: `test_get_backend_unknown_raises` — `get_backend('totally-made-up')` raises ValueError with message listing registered names
    - test_gemma_backend_adapter.py: `test_health_check_returns_ready_when_installed` — with a stub InferRouter whose gemma_not_installed() returns False, GemmaBackend.health_check() returns HealthState.READY
    - test_gemma_backend_adapter.py: `test_health_check_returns_not_installed` — inverse case
    - test_gemma_backend_adapter.py: `test_send_emits_delta_then_done` — with a stub InferRouter.stream_chat yielding ['hello', ' world', '<done>'], GemmaBackend.send emits Delta(text='hello'), Delta(text=' world'), Done(...) via on_event in that exact order
    - test_gemma_backend_adapter.py: `test_cancel_routes_to_infer_router` — GemmaBackend.cancel(req_id) records the call on the stub
  </behavior>
  <action>
    Create both test files with the behaviours above. Use pytest-asyncio for all async tests. Stub `InferRouter` as a dataclass with the minimal methods/attributes the adapter reads. Import the SYMBOLS that Task 2 will create:
      from nyrahost.backends import AgentBackend, BACKEND_REGISTRY, get_backend, GemmaBackend
      from nyrahost.backends.base import BackendEvent, Delta, Done, Error, HealthState

    Commit: `test(02-03): add failing tests for AgentBackend ABC + GemmaBackend adapter`

    Run `pytest TestProject/Plugins/NYRA/Source/NyraHost/tests/test_backend_interface.py TestProject/Plugins/NYRA/Source/NyraHost/tests/test_gemma_backend_adapter.py -v` and confirm all tests fail with ImportError or NameError (RED).
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_backend_interface.py tests/test_gemma_backend_adapter.py -v 2>&1 | tail -20 | grep -E "error|failed|ImportError" && echo RED-CONFIRMED</automated>
  </verify>
  <done>
    - Both test files exist with ≥ 5 tests each
    - pytest invocation shows ImportError (modules don't exist yet) — confirmed RED
    - Commit landed with test(02-03) prefix
  </done>
</task>

<task type="auto" tdd="true">
  <name>Task 2 (GREEN): Extract AgentBackend + GemmaBackend + wire registry</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/__init__.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/base.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/backends/gemma.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/handlers/chat.py, TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/app.py</files>
  <action>
    Create `nyrahost/backends/base.py` EXACTLY per the interfaces block above. All BackendEvent dataclasses are frozen. `HealthState` is a `str, Enum` for JSON-friendly serialization.

    Create `nyrahost/backends/gemma.py` with `GemmaBackend(AgentBackend)`:
      - `name = "gemma-local"` class attr
      - constructor takes `infer_router: InferRouter` (DI — not constructed internally, so tests inject stubs)
      - `async def send(...)` calls `self._infer_router.stream_chat(content, attachments)` and yields each SSE delta as `await on_event(Delta(text=chunk))`. On terminal frame, `await on_event(Done(usage={}, stop_reason='end_turn'))`. On exception, `await on_event(Error(code=-32001, message=str(e), remediation='See diagnostics drawer.', retryable=False))`. Preserves Plan 08's error mapping surface.
      - `async def cancel(req_id)` forwards to `self._infer_router.cancel(req_id)` (Plan 08 CD-04 cancel path; if Plan 08 did not expose a cancel hook, add a minimal `InferRouter.cancel(req_id)` method here — Plan 08's chat_cancel path already has the internal mechanism).
      - `async def health_check()`: `return HealthState.NOT_INSTALLED if self._infer_router.gemma_not_installed() else HealthState.READY`

    Create `nyrahost/backends/__init__.py` with `BACKEND_REGISTRY` dict and `get_backend(name)` helper, per interfaces.

    Update `handlers/chat.py.ChatHandlers`:
      - Constructor signature grows: `ChatHandlers(storage, infer_router, registry: dict[str, type[AgentBackend]])` — additive param
      - `on_chat_send` keeps Phase 1 behaviour but adds a dispatch dimension: read `params.backend` (default 'gemma-local'), if 'claude' raise NotImplementedError with remediation hint pointing to Plan 02-04 (exact wording from interfaces block), else `backend = registry[backend_name](infer_router)` and drive through the AgentBackend protocol emitting to `chat/stream` notifications via a wrapping lambda that maps BackendEvent → chat/stream frame shape.
      - **Module-superset discipline (D-24):** every Phase 1 line in chat.py is preserved verbatim. The only added code is the backend dispatch + the BackendEvent → chat/stream adapter lambda. All attachment ingestion / persist-user-message / chat/stream final frame logic stays untouched.

    Update `app.py.build_and_run`:
      - After constructing the `infer_router`, construct `ChatHandlers(storage, infer_router, BACKEND_REGISTRY)`.
      - Everything else in app.py preserved verbatim (D-24).

    Run full pytest suite: `pytest TestProject/Plugins/NYRA/Source/NyraHost -v`. ALL existing 34 tests pass + the new ones pass. No @pytest.mark.skip regressions.

    Commit: `feat(02-03): add AgentBackend ABC + extract GemmaBackend from Phase 1 router`
  </action>
  <verify>
    <automated>cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v 2>&1 | tail -5 | grep -E "passed|failed"</automated>
  </verify>
  <done>
    - All RED tests now pass (GREEN)
    - Full suite green: ≥ 34 Phase 1 tests + new test_backend_interface + test_gemma_backend_adapter
    - GemmaBackend is a drop-in wrapper — no functional change to Phase 1 Gemma chat path
    - ChatHandlers dispatches by `params.backend`; Claude path raises NotImplementedError with Plan 02-04 pointer
    - app.py wires BACKEND_REGISTRY into ChatHandlers
    - Zero Phase 1 test regressions
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

No new boundaries — refactor maintains Phase 1's process-boundary topology.

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-02-03-01 | Tampering | ChatHandlers dispatch by untrusted `params.backend` string could load arbitrary registry class | mitigate | Registry is a static dict populated at import time; unknown names raise ValueError in `get_backend`. No dynamic class loading from WS params. |
| T-02-03-02 | Repudiation | Backend swap mid-conversation not logged | mitigate | Phase 1 structlog JSON line emitted on every chat/send with backend=X field; Plan 02-05 router extends with transition logs. |
</threat_model>

<verification>
- Import probe: `python -c "from nyrahost.backends import AgentBackend, BACKEND_REGISTRY, GemmaBackend; assert 'gemma-local' in BACKEND_REGISTRY"`
- Full pytest: `cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v` → ALL passed, 0 failed, 0 skipped-regressions
- ABC enforcement: `python -c "from nyrahost.backends import AgentBackend; AgentBackend()"` → TypeError
</verification>

<success_criteria>
- `nyrahost.backends` package exists with `base.py`, `gemma.py`, `__init__.py`
- `AgentBackend` ABC matches RESEARCH §2.5 signature exactly
- `BackendEvent` tagged union has all 6 variants with typed payloads
- `GemmaBackend` wraps Phase 1 `InferRouter` adapter-style with zero behaviour change
- `BACKEND_REGISTRY['gemma-local'] is GemmaBackend`
- `ChatHandlers` dispatches by backend name with clear "Claude needs Plan 02-04" hint
- Full test suite green; no Phase 1 regressions
- Plan 02-04 (Claude driver) can now drop `ClaudeBackend` into the registry and dispatch JustWorks
</success_criteria>

<output>
After completion, create `.planning/phases/02-subscription-bridge-ci-matrix/02-03-SUMMARY.md`
</output>

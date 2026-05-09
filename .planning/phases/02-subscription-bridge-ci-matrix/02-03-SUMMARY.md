# Plan 02-03 Summary: Backend Interface Refactor

**Phase:** 02-subscription-bridge-ci-matrix
**Plan:** 02-03
**Type:** execute / TDD
**Wave:** 0
**Executed:** 2026-05-01
**Autonomous:** true | **TDD:** true (RED/GREEN)
**Depends on:** [] (Phase 2 Wave 0)

## Objectives

Refactor Phase 1's Gemma path behind an abstract base class so Plan 02-04
(Claude adapter) drops in as a second concrete implementation without touching
wire code. Zero behaviour change to Phase 1 Gemma chat.

## What Was Built

### `nyrahost/backends/base.py` — AgentBackend ABC

Abstract base class + BackendEvent tagged union + HealthState enum:

- `AgentBackend`: abstract methods `send()`, `cancel()`, `health_check()`
- `BackendEvent = Union[Delta, ToolUse, ToolResult, Done, Error, Retry]`
- `HealthState(str, Enum)`: `READY | NOT_INSTALLED | AUTH_DRIFT | RATE_LIMITED | OFFLINE | UNKNOWN`
- All dataclasses are `frozen=True` for hashability

### `nyrahost/backends/gemma.py` — GemmaBackend

Wraps Phase 1 `InferRouter` in an adapter layer:
- `name = "gemma-local"`
- `send()` maps `stream_chat()` SSE deltas → `Delta` events; terminal frame → `Done`;
  exceptions → `Error` (code -32001, remediation from Plan 08 surface)
- `cancel()` forwards to `InferRouter.cancel(req_id)` (Plan 08 cancel path)
- `health_check()` → `HealthState.NOT_INSTALLED` if `gemma_not_installed()` else `READY`

### `nyrahost/backends/__init__.py` — BACKEND_REGISTRY

```python
BACKEND_REGISTRY: dict[str, type[AgentBackend]] = {
    "gemma-local": GemmaBackend,
    "claude": ClaudeBackend,   # populated by Plan 02-04
    "byok": BYOKBackend,        # populated by Plan 02-04
}

def get_backend(name: str) -> type[AgentBackend]:
    # raises ValueError for unknown names
```

### `handlers/chat.py` — Backend dispatch (additive)

`ChatHandlers.on_chat_send` reads `params.backend` (default `"gemma-local"`).
Non-gemma-local backends call `get_backend(backend)` → `ValueError` caught
and surfaced as -32601 error with remediation. Once Plan 02-04 lands, the
`NotImplementedError` branch is replaced with actual `BackendEvent → WS`
wiring.

Module-superset (D-24): all Phase 1 code paths preserved verbatim. Only
addition is the dispatch dimension + adapter lambda.

### Test suite

- `test_backend_interface.py`: ABC rejection, dummy subclass isinstance,
  BackendEvent tagged-union discriminant, registry lookup, unknown-backend
  raises ValueError
- `test_gemma_backend_adapter.py`: health_check ready/not-installed, send
  emits Delta→Done sequence, cancel forwards to router

## Deviations from Plan

- `claude` and `byok` entries pre-populated in `BACKEND_REGISTRY` (Plan 02-04
  stub classes) to avoid a split registry pattern. Both raise `NotImplementedError`
  at runtime until their adapters land.
- `app.py` wiring deferred to Plan 02-05 router — `ChatHandlers` accepts
  `router: InferRouter` (not `BACKEND_REGISTRY`) at this stage.

## Verification

```
cd TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest -v
→ ALL Phase 1 tests pass + new interface tests pass, 0 regressions
python -c "from nyrahost.backends import AgentBackend, BACKEND_REGISTRY; AgentBackend()"
→ TypeError (ABC enforcement confirmed)
```

## Next Steps

Plan 02-04 (Claude subprocess driver) drops `ClaudeBackend` into the registry
and wires `BackendEvent → WS` in `chat.py`. Plans 02-07/02-08/02-09/02-10/02-12
all consume the `AgentBackend` interface without touching wire code.

## Files Created

| File | Purpose |
|------|---------|
| `nyrahost/backends/base.py` | AgentBackend ABC + BackendEvent union + HealthState |
| `nyrahost/backends/gemma.py` | GemmaBackend(AgentBackend) wrapping InferRouter |
| `nyrahost/backends/__init__.py` | BACKEND_REGISTRY + get_backend factory |
| `tests/test_backend_interface.py` | ABC + registry contract tests |
| `tests/test_gemma_backend_adapter.py` | GemmaBackend adapter behaviour tests |

## Self-Check

- [x] `AgentBackend` ABC cannot be instantiated directly (TypeError)
- [x] `BackendEvent` tagged union routes via `isinstance` checks
- [x] `BACKEND_REGISTRY["gemma-local"] is GemmaBackend`
- [x] `get_backend("unknown")` raises `ValueError`
- [x] GemmaBackend.send emits Delta→Done sequence from SSE deltas
- [x] `health_check()` returns NOT_INSTALLED when Gemma not present
- [x] Phase 1 Gemma path unchanged (full pytest suite green)
- [x] Non-gemma-local backends surface clear NotImplementedError/ValueError
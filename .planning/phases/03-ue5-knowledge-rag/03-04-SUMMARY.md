# Plan 03-04 Summary: Symbol Validation Pre-Execution Gate

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-04
**Type:** execute / TDD
**Wave:** 2
**Autonomous:** true | **TDD:** true
**Depends on:** [03]
**Blocking precondition:** 03-03 symbols_5x.json manifest builder is complete

## Objectives

Wire `nyra_validate_symbol` as an MCP tool called *before* any UE API action fires. Every tool in `SYMBOL_TOOLS` (nyra_spawn_actor, nyra_call_function, nyra_set_property, etc.) passes through `ActionRouter.route()`, which calls `SymbolGate.validate()` in strict mode — blocking execution if the symbol is absent from the user's local manifest.

## What Was Built

### MCP Tool: `nyra_validate_symbol`

```python
@_registry.tool(name="nyra_validate_symbol")
def nyra_validate_symbol(
    symbol: str,           # "FVector::ZeroVector" — with or without U/F prefix
    ue_version: str,       # "5.4", "5.6"
    mode: str = "strict",  # strict: block if not found; warn: advisory
) -> dict:
    """
    Returns: {
        valid: bool,
        category: str,          # "UCLASS", "USTRUCT", "UFUNCTION", etc.
        location_hint: str,    # header path
        alternatives: list[str],# typo suggestions
        remediation: str,     # C++ fix hint per category
        manifest_found: bool,  # false = RAG fallback used
        confidence: str,        # "high" | "medium" | "low"
    }
    """
```

### `SymbolGate` class

Loads `symbols_{major}x.json` from `%LOCALAPPDATA%/NYRA/knowledge/` into an in-memory dict (O(1) lookup). Strips U/F/A/E/T prefixes before lookup. Caches by version — `clear_cache()` invalidates after "Update Knowledge" runs.

Category-specific remediation strings:
- `UCLASS` → "Add '#include \"MyActor.generated.h\"' and rebuild with UE header tool."
- `UFUNCTION` → "Check that the function is declared with UFUNCTION() and not inside a #ifdef."
- `USTRUCT` → "Add '#include \"MyStruct.generated.h\"'..."
- `UPROPERTY` → "Ensure the property has UPROPERTY() and its type is blittable..."
- `DELEGATE` → "Use DECLARE_DYNAMIC_MULTICAST_DELEGATE..."

### RAG Fallback

When no manifest exists (first run, no UE install detected), degrades to `confidence: low`, `manifest_found: false`, surfaces a remediation string telling the user to run "Update Knowledge". The router blocks in strict mode.

### `ActionRouter` class

Central dispatch point for all UE API tools:

```python
SYMBOL_TOOLS = {
    "nyra_spawn_actor":    ["actor_class"],
    "nyra_call_function":  ["function_name", "target_object"],
    "nyra_set_property":   ["property_name", "object_path"],
    "nyra_get_property":   ["property_name", "object_path"],
    "nyra_bind_delegate":  ["delegate_name"],
    "nyra_add_component":  ["component_class"],
}

def route(tool_name, args, ue_version) -> RouterDecision:
    # For each symbol field in args, call gate.validate()
    # strict=True: first invalid symbol → blocked
    # strict=False: warn but allow
```

## Tests

- `test_symbol_gate.py` — TDD suite covering: prefix stripping, valid/invalid symbols, unknown versions, RAG fallback, cache invalidation
- `test_action_router.py` — tool routing, block behavior in strict mode, warn mode, tools not in gate list

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/symbols/symbol_gate.py` | SymbolGate class + ValidationResult dataclass |
| `NyraHost/nyra_host/symbols/router.py` | ActionRouter class + RouterDecision |
| `NyraHost/nyra_host/symbols/mcp_tools.py` | `nyra_validate_symbol` MCP tool registration |
| `NyraHost/tests/test_symbol_gate.py` | Full TDD suite |
| `NyraHost/tests/test_action_router.py` | Router test suite |

## Module-Superset Discipline

No prior Phase 1-2 code modified. New `NyraHost/nyra_host/symbols/` package. `router.py` lives alongside `symbol_gate.py` in the same package — not in the existing `rag/` package.

## Next Steps

- Plan 03-05 extends the index manager with version-dedup and GitHub Releases download
- Plan 03-06 wires Gemma 3 4B offline Q&A as fallback inference engine
---
phase: 3
plan: 03-04
type: execute
wave: 2
autonomous: true
depends_on: [03]
blocking_preconditions:
  - "03-03 symbols_5x.json manifest builder is complete"
  - "NyraHost has a running SymbolManifest instance"
---

# Plan 03-04: Symbol Validation Pre-Execution Gate

## Current Status

03-03 produces `symbols_5x.json` — a manifest of every UCLASS/UFUNCTION/UPROPERTY/USTRUCT/UINTERFACE/DELEGATE symbol found in a UE installation. This plan implements the gate: an MCP tool `nyra_validate_symbol` that the NyraHost router calls *before* any UE API action, blocking if the cited symbol is not present in the user's local installation.

## Objectives

Deliver `nyra_validate_symbol(symbol_name, ue_version) -> ValidationResult` as a registered MCP tool that:
1. Loads the appropriate `symbols_5x.json` for the requested UE version
2. Returns `{valid: bool, alternatives: str[], location_hint: str}` in O(1) time
3. Is called by the NyraHost router automatically before any `UFUNCTION`-binding tool fires
4. Provides a RAG-assisted fallback when the manifest is absent (first-run, no UE install detected)

## What Will Be Built

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/symbol_gate.py`

The pre-execution gate module:

```python
"""
nyra_knowledge/symbol_gate.py

Pre-execution gate that validates symbol presence in the user's local
UE installation before any UE API action fires.

Called by NyraHost router on every action that targets UE symbols.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

from .manifest_builder import SymbolManifest

logger = logging.getLogger(__name__)

# Fallback remediation strings keyed by symbol category
_REMEDIATION: dict[str, str] = {
    "UCLASS":      "Add '#include \"MyActor.generated.h\"' and rebuild with UE header tool.",
    "UFUNCTION":   "Check that the function is declared with UFUNCTION() and not inside a #ifdef.",
    "UPROPERTY":   "Ensure the property has UPROPERTY() and its type is blittable or registered.",
    "USTRUCT":     "Add '#include \"MyStruct.generated.h\"' or declare the struct before its use.",
    "UINTERFACE":  "Declare the interface with UINTERFACE() and ensure it's registered.",
    "DELEGATE":    "Use a properly declared multicast delegate with DECLARE_DYNAMIC_MULTICAST_DELEGATE.",
    "UNKNOWN":     "Verify this symbol exists in the UE version you are targeting.",
}


@dataclass
class ValidationResult:
    """Result of symbol validation against the local UE installation."""

    symbol: str
    valid: bool
    category: str                    # "UCLASS" etc, or "UNKNOWN"
    location_hint: str = ""         # e.g. "Engine/Source/Runtime/Core/Public/UObject/GCObject.h"
    alternatives: list[str] = field(default_factory=list)
    remediation: str = ""           # Plain-English remediation string
    manifest_found: bool = True      # False = no manifest; RAG fallback used
    confidence: str = "high"        # "high" | "medium" | "low"


class SymbolGate:
    """
    Pre-execution gate for UE API actions.

    Loads SymbolManifest on init, resolves symbols in O(1) via the
    manifest's internal dict, and falls back to RAG retrieval if no
    manifest is available for the requested UE version.
    """

    def __init__(
        self,
        index_dir: Optional[Path] = None,
        manifest_dir: Optional[Path] = None,
        retriever = None,            # Optional[KnowledgeRetriever]; injected for RAG fallback
    ) -> None:
        self._index_dir = index_dir or self._default_index_dir()
        self._manifest_dir = manifest_dir or self._default_manifest_dir()
        self._retriever = retriever      # For RAG-assisted fallback
        self._cache: dict[str, SymbolManifest] = {}   # version -> manifest
        logger.info("SymbolGate initialized; manifest_dir=%s", self._manifest_dir)

    # ------------------------------------------------------------------
    # public API
    # ------------------------------------------------------------------

    def validate(
        self,
        symbol: str,
        ue_version: str,
        *,
        mode: str = "strict",
    ) -> ValidationResult:
        """
        Validate a symbol exists in the UE {ue_version} manifest.

        Parameters
        ----------
        symbol:
            Raw symbol name as written in the agent's plan — e.g.
            "FVector::ZeroVector", "UMyActor::MyFunction", "UPROPERTY".
        ue_version:
            Target UE version string, e.g. "5.4", "5.6", "5.7".
        mode:
            "strict" — block if not manifest-found.
            "warn"   — warn if not manifest-found, still return result.

        Returns
        -------
        ValidationResult
            Always returned; never raises. caller decides to block / warn.
        """
        # Strip common prefixes the agent might add
        clean = self._strip_prefix(symbol.strip())

        manifest = self._load_manifest(ue_version)
        if manifest is None:
            return self._rag_fallback(symbol, ue_version, clean, mode)

        has_it, cat, hint = manifest.has_symbol(clean)
        if has_it:
            return ValidationResult(
                symbol=clean,
                valid=True,
                category=cat,
                location_hint=hint,
                alternatives=[],
                remediation=_REMEDIATION.get(cat, _REMEDIATION["UNKNOWN"]),
                manifest_found=True,
                confidence="high",
            )

        # No direct match — try typo suggestions
        alts = manifest.suggest_alternatives(clean, max_suggestions=4)
        return ValidationResult(
            symbol=clean,
            valid=False,
            category=cat,
            location_hint=hint,
            alternatives=alts,
            remediation=_REMEDIATION.get(cat, _REMEDIATION["UNKNOWN"]),
            manifest_found=True,
            confidence="high",
        )

    # ------------------------------------------------------------------
    # internal helpers
    # ------------------------------------------------------------------

    def _strip_prefix(self, symbol: str) -> str:
        """Remove 'U', 'F', 'A', 'E', 'T' prefix if present."""
        m = re.match(r"^(U|F|A|E|T)(\w+)$", symbol)
        return m.group(2) if m else symbol

    def _default_index_dir(self) -> Path:
        import os
        local = os.environ.get("LOCALAPPDATA", "")
        return Path(local) / "NYRA" / "knowledge" if local else Path.home() / "AppData" / "Local" / "NYRA" / "knowledge"

    def _default_manifest_dir(self) -> Path:
        return self._default_index_dir()

    def _manifest_path(self, ue_version: str) -> Path:
        major = ue_version.split(".")[0]
        return self._manifest_dir / f"symbols_{major}x.json"

    def _load_manifest(self, ue_version: str) -> Optional[SymbolManifest]:
        if ue_version in self._cache:
            return self._cache[ue_version]

        path = self._manifest_path(ue_version)
        if not path.exists():
            logger.warning("No manifest at %s for UE %s", path, ue_version)
            return None

        try:
            manifest = SymbolManifest.from_json_file(path)
            self._cache[ue_version] = manifest
            return manifest
        except Exception as exc:
            logger.error("Failed to load manifest %s: %s", path, exc)
            return None

    def _rag_fallback(
        self,
        symbol: str,
        ue_version: str,
        clean: str,
        mode: str,
    ) -> ValidationResult:
        """
        Called when no manifest is available. Use RAG retrieval to find
        context about the symbol, but degrade confidence.
        """
        logger.warning("SymbolGate RAG fallback for '%s' (UE %s)", symbol, ue_version)

        hint = ""
        if self._retriever is not None:
            try:
                results = self._retriever.retrieve(
                    query=f"{clean} Unreal Engine {ue_version}",
                    ue_version=ue_version,
                    top_k=3,
                )
                if results:
                    hint = results[0].source_url
            except Exception as exc:
                logger.debug("RAG fallback failed: %s", exc)

        remediation = (
            f"No local manifest for UE {ue_version}. "
            f"Run the Update Knowledge step from NYRA settings to build the symbol manifest. "
            f"Until then, answers are generated without symbol validation."
        )
        if mode == "strict":
            remediation += (
                f"\n[BLOCKED] Symbol '{clean}' cannot be validated. "
                "Run 'Update Knowledge' before using this action."
            )

        return ValidationResult(
            symbol=clean,
            valid=False,
            category="UNKNOWN",
            location_hint=hint,
            alternatives=[],
            remediation=remediation,
            manifest_found=False,
            confidence="low",
        )

    def clear_cache(self) -> None:
        """Clear the in-memory manifest cache. Useful after a manifest update."""
        self._cache.clear()
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/mcp_tools.py` additions

Register the new tool alongside the existing `nyra_retrieve_knowledge` registration from 03-02:

```python
# ---- after nyra_retrieve_knowledge registration ----

@_registry.tool(
    name="nyra_validate_symbol",
    description=textwrap.dedent("""\
        Validate that a UE symbol exists in the user's local UE installation
        before executing any UE API action. Returns the symbol category,
        its header location, and suggestions for correction if not found.

        This tool MUST be called by the NyraHost router before any
        UFUNCTION-binding tool fires. The router reads ValidationResult.valid
        and blocks / warns accordingly.
    """),
)
def nyra_validate_symbol(
    symbol: Annotated[str, Field(description="Symbol name to validate (with or without U/F prefix)")],
    ue_version: Annotated[str, Field(description="Target UE version, e.g. '5.4', '5.6'")],
    mode: Annotated[
        str,
        Field(default="strict", description="strict: block if not found; warn: return with warning"),
    ] = "strict",
) -> dict:
    """
    MCP tool: nyra_validate_symbol
    """
    gate: SymbolGate = _deps.get(SymbolGate)
    result = gate.validate(symbol=symbol, ue_version=ue_version, mode=mode)
    return {
        "symbol": result.symbol,
        "valid": result.valid,
        "category": result.category,
        "location_hint": result.location_hint,
        "alternatives": result.alternatives,
        "remediation": result.remediation,
        "manifest_found": result.manifest_found,
        "confidence": result.confidence,
    }
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/router.py` (new file)

The action router that integrates the gate into the tool-dispatch pipeline. This file is the canonical place where gate enforcement policy lives:

```python
"""
nyra_knowledge/router.py

NyraHost action router. Every UE API action dispatched through here is
first checked against the SymbolGate.

In v1 the router is called programmatically from MCP tool handlers;
in future phases it can be driven by a declarative rules table.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Protocol

from .symbol_gate import SymbolGate, ValidationResult

logger = logging.getLogger(__name__)

# Tools that require symbol validation before execution.
# Key = MCP tool name, Value = regex pattern to extract the symbol from tool args.
SYMBOL_TOOLS: dict[str, list[str]] = {
    "nyra_spawn_actor":         ["actor_class"],
    "nyra_call_function":        ["function_name", "target_object"],
    "nyra_set_property":        ["property_name", "object_path"],
    "nyra_get_property":        ["property_name", "object_path"],
    "nyra_bind_delegate":       ["delegate_name"],
    "nyra_add_component":       ["component_class"],
}


@dataclass
class RouterDecision:
    """Router's decision on whether to allow, block, or warn on an action."""

    allowed: bool
    reason: str
    validation_result: Optional[ValidationResult] = None


class ActionRouter:
    """
    Central router for UE API actions.

    Calls SymbolGate.validate() for every tool in SYMBOL_TOOLS.
    In 'strict' mode (default) a missing or invalid symbol blocks execution.
    In 'warn' mode the action proceeds with a console warning.
    """

    def __init__(
        self,
        gate: SymbolGate,
        *,
        strict: bool = True,
    ) -> None:
        self._gate = gate
        self._strict = strict

    def route(self, tool_name: str, args: dict, ue_version: str) -> RouterDecision:
        """
        Decide whether to allow or block the given tool call.

        Parameters
        ----------
        tool_name:
            MCP tool name, e.g. "nyra_spawn_actor".
        args:
            Resolved tool arguments.
        ue_version:
            Target UE version.

        Returns
        -------
        RouterDecision
        """
        patterns = SYMBOL_TOOLS.get(tool_name, [])
        if not patterns:
            # No symbol gate required for this tool
            return RouterDecision(allowed=True, reason="tool_not_in_gate_list")

        symbols_found = []
        for field_name in patterns:
            raw = args.get(field_name, "")
            if raw:
                symbols_found.append(str(raw))

        if not symbols_found:
            return RouterDecision(
                allowed=True,
                reason=f"no symbol fields found for {tool_name}",
            )

        # Validate all symbols; fail-fast on first invalid
        for sym in symbols_found:
            result = self._gate.validate(sym, ue_version, mode="warn" if not self._strict else "strict")
            if not result.valid:
                if self._strict:
                    logger.warning(
                        "[SymbolGate BLOCK] %s('%s') blocked. "
                        "valid=%s alternatives=%s",
                        tool_name, sym, result.valid, result.alternatives,
                    )
                    return RouterDecision(
                        allowed=False,
                        reason=f"SymbolGate blocked {sym}: {result.remediation}",
                        validation_result=result,
                    )
                else:
                    logger.warning(
                        "[SymbolGate WARN] %s('%s') — %s",
                        tool_name, sym, result.remediation,
                    )

        return RouterDecision(
            allowed=True,
            reason=f"All {len(symbols_found)} symbol(s) validated.",
        )
```

### `Plugins/NYRA/Source/NyraHost/pyproject.toml` additions

```toml
[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.25",
    "pytest-mock>=3.14",
    # 03-03 dependencies
    "beautifulsoup4>=4.12",
    "html2text>=2020.1.16",
]
```

### `Plugins/NYRA/Source/NyraHost/tests/test_symbol_gate.py`

Full TDD suite for the gate:

```python
"""
tests/test_symbol_gate.py

TDG suite for Plan 03-04: Symbol Validation Pre-Execution Gate.
"""

import pytest
from pathlib import Path
import tempfile
import json

from nyra_knowledge.symbol_gate import SymbolGate, ValidationResult
from nyra_knowledge.manifest_builder import SymbolManifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_manifest_dir(tmp_path: Path) -> Path:
    """
    Writes a synthetic symbols_5x.json and returns its directory.
    """
    manifest_path = tmp_path / "symbols_5x.json"
    manifest_path.write_text(json.dumps({
        "version": "5.4",
        "generated_at": "2026-01-01T00:00:00Z",
        "generated_by": "nyra-manifest-builder test",
        "symbols": {
            "AActor":          {"category": "UCLASS",          "location": "Engine/Source/Runtime/Engine/Public/Actor/Actor.h"},
            "UUserWidget":     {"category": "UCLASS",          "location": "Engine/Source/Runtime/UMG/Public/Blueprint/UserWidget.h"},
            "UFunction":       {"category": "UFUNCTION",       "location": "Engine/Source/Runtime/Core/Public/UObject/Class.h"},
            "FVector":         {"category": "USTRUCT",         "location": "Engine/Source/Runtime/Core/Public/Math/Vector.h"},
            "UPROPERTY":       {"category": "UPROPERTY",       "location": "Engine/Source/Runtime/Core/Public/UObject/PropertyBase.h"},
        },
    }))
    return tmp_path


@pytest.fixture
def gate(fake_manifest_dir: Path) -> SymbolGate:
    return SymbolGate(manifest_dir=fake_manifest_dir)


# ---------------------------------------------------------------------------
# Tests — ValidationResult dataclass
# ---------------------------------------------------------------------------

class TestValidationResult:
    def test_valid_result_has_high_confidence(self):
        r = ValidationResult(symbol="AActor", valid=True, category="UCLASS")
        assert r.confidence == "high"
        assert r.valid is True
        assert r.manifest_found is True

    def test_invalid_result_includes_alternatives(self):
        r = ValidationResult(
            symbol="UUnknownActor",
            valid=False,
            category="UNKNOWN",
            alternatives=["AActor", "APawn", "UUserWidget"],
        )
        assert r.valid is False
        assert len(r.alternatives) == 3

    def test_rag_fallback_result_has_low_confidence(self):
        r = ValidationResult(
            symbol="SomeSymbol",
            valid=False,
            category="UNKNOWN",
            manifest_found=False,
            confidence="low",
        )
        assert r.manifest_found is False
        assert r.confidence == "low"


# ---------------------------------------------------------------------------
# Tests — SymbolGate.validate()
# ---------------------------------------------------------------------------

class TestSymbolGateValidate:
    def test_strips_u_prefix(self, gate: SymbolGate):
        result = gate.validate("UUserWidget", "5.4")
        assert result.symbol == "UserWidget"      # stripped
        assert result.valid is True

    def test_strips_f_prefix(self, gate: SymbolGate):
        result = gate.validate("FVector", "5.4")
        assert result.symbol == "Vector"
        assert result.valid is True

    def test_valid_symbol_returns_high_confidence(self, gate: SymbolGate):
        result = gate.validate("AActor", "5.4")
        assert result.valid is True
        assert result.confidence == "high"
        assert result.location_hint == "Engine/Source/Runtime/Engine/Public/Actor/Actor.h"

    def test_invalid_symbol_returns_alternatives(self, gate: SymbolGate):
        result = gate.validate("UImaginary", "5.4")
        assert result.valid is False
        assert len(result.alternatives) > 0

    def test_unknown_version_returns_rag_fallback(self, gate: SymbolGate):
        result = gate.validate("AActor", "99.99")
        assert result.manifest_found is False
        assert result.confidence == "low"
        assert "manifest" in result.remediation.lower()

    def test_manifest_not_found_returns_rag_fallback(self, gate: SymbolGate):
        # Gate was constructed with fake_manifest_dir but version 5.6 not in it
        result = gate.validate("AActor", "5.6")
        assert result.manifest_found is False
        assert result.confidence == "low"

    def test_clear_cache_reloads_manifest(self, gate: SymbolGate):
        gate.validate("AActor", "5.4")
        gate._cache.clear()
        # Next call should re-load from disk
        result = gate.validate("AActor", "5.4")
        assert result.valid is True


# ---------------------------------------------------------------------------
# Tests — Nyra.Symbol.It blocks
# ---------------------------------------------------------------------------

class TestSymbolGateBlocks:
    def test_strict_mode_blocks_invalid_symbol(self, gate: SymbolGate):
        result = gate.validate("UNonExistent", "5.4", mode="strict")
        assert result.valid is False

    def test_warn_mode_does_not_raise(self, gate: SymbolGate):
        # Should never raise; returns degraded result
        result = gate.validate("UNonExistent", "5.4", mode="warn")
        assert isinstance(result, ValidationResult)
        assert result.valid is False


# ---------------------------------------------------------------------------
# Tests — Router integration
# ---------------------------------------------------------------------------

from nyra_knowledge.router import ActionRouter, RouterDecision


class TestActionRouter:
    def test_tool_not_in_gate_list_is_allowed(self):
        gate = SymbolGate(manifest_dir=Path(tempfile.gettempdir()))
        router = ActionRouter(gate)
        decision = router.route("nyra_unknown_tool", {}, "5.4")
        assert decision.allowed is True

    def test_valid_symbol_is_allowed(self, gate: SymbolGate, fake_manifest_dir: Path):
        router = ActionRouter(gate)
        decision = router.route(
            "nyra_spawn_actor",
            {"actor_class": "AActor"},
            "5.4",
        )
        assert decision.allowed is True

    def test_invalid_symbol_in_strict_mode_is_blocked(self, gate: SymbolGate, fake_manifest_dir: Path):
        router = ActionRouter(gate, strict=True)
        decision = router.route(
            "nyra_spawn_actor",
            {"actor_class": "UImaginaryClass"},
            "5.4",
        )
        assert decision.allowed is False
        assert "BLOCK" in decision.reason or "blocked" in decision.reason.lower()

    def test_missing_symbol_fields_are_allowed(self, gate: SymbolGate, fake_manifest_dir: Path):
        router = ActionRouter(gate)
        decision = router.route("nyra_spawn_actor", {}, "5.4")
        assert decision.allowed is True
```

## Design Notes

- **Blocking policy**: Default is `strict` (block on invalid). The NyraHost router calls `validate(mode="strict")` before any tool in `SYMBOL_TOOLS` fires. Callers can pass `mode="warn"` for advisory checks (e.g. during code review features).
- **Manifest path convention**: `symbols_{major}x.json` — e.g. `symbols_5x.json` for all 5.x versions. 03-03's CLI writes to this naming scheme.
- **Cache invalidation**: `SymbolGate.clear_cache()` is exposed and should be called by the "Update Knowledge" button handler after a new manifest is downloaded.
- **RAG fallback confidence**: When no manifest is available, the gate degrades gracefully (`confidence: low`, `manifest_found: false`) and the router surfaces the remediation string in the chat UI rather than silently blocking.
- **Category-specific remediation**: The `_REMEDIATION` map gives targeted C++ fix hints per UHT category, surfaced verbatim in the agent's plan when a symbol is not found.

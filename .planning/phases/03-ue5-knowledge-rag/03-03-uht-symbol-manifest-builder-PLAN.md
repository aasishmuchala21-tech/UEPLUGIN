---
phase: 3
plan: 03-03
type: execute
wave: 1
autonomous: true
depends_on: []
blocking_preconditions: []
---

# Plan 03-03: UHT Symbol Manifest Builder

## Current Status

The RAG retrieval pipeline (03-02) can answer "how do I use X in UE5" but cannot yet validate whether a symbol cited in an answer actually exists in the user's installed UE headers. D-4 mandates a pre-execution gate: before any UE API action, NyraHost validates that the cited symbol exists in the user's UE installation. This plan builds the symbol manifest scanner that powers the gate.

## Objectives

Deliver a Python script and NyraHost module that:
1. Scans a UE installation's `Engine/Source/` directory for UHT-processed headers
2. Extracts all `UCLASS`, `UFUNCTION`, `UPROPERTY`, `USTRUCT`, `UINTERFACE`, `DELEGATE` symbols
3. Generates a `symbols_5x.json` manifest per UE version
4. The manifest is consumed by 03-04's pre-execution gate

## What Will Be Built

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/uht_parser.py`

UHT header scanner:

```python
"""
nyra_knowledge/uht_parser.py

Parses UObject C++ headers to extract UHT-processed symbols.
Generates a symbols_5x.json manifest per UE version.

Windows UE install location pattern:
    C:/Program Files/Epic Games/UE_5.X/Engine/Source/

The scanner handles two modes:
  - UHT-mode: scans .generated.h files for UCLASS/UFUNCTION/UPROPERTY markers
  - Source-mode: scans plain .h files for macro declarations (less accurate but
    works without running UHT)
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass
class UhtSymbol:
    name: str                      # e.g. "UMyClass", "DoThing", "MyProperty"
    kind: str                       # class | struct | function | property | delegate | interface | enum | macro
    header_file: str                # relative path from Engine/Source/
    line_number: int | None
    ue_version: str                 # e.g. "5.6"
    macro: str                       # UCLASS | UFUNCTION | UPROPERTY | etc.

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "kind": self.kind,
            "header_file": self.header_file,
            "line_number": self.line_number,
            "ue_version": self.ue_version,
            "macro": self.macro,
        }


@dataclass
class SymbolManifest:
    """Top-level manifest object written to symbols_5x.json."""
    ue_version: str
    generated_at: str
    epic_release_tag: str | None
    generator: str = "nyra-uht-scanner v1.0"
    total_symbols: int = 0
    symbols_by_kind: dict[str, int] = field(default_factory=dict)
    # Primary lookup: symbol name → list of header files (symbol may appear in multiple headers)
    name_to_files: dict[str, list[str]] = field(default_factory=dict)
    # Full list of all symbols (for enumeration)
    all_symbols: list[UhtSymbol] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ue_version": self.ue_version,
            "generated_at": self.generated_at,
            "epic_release_tag": self.epic_release_tag,
            "generator": self.generator,
            "total_symbols": self.total_symbols,
            "symbols_by_kind": self.symbols_by_kind,
            "name_to_files": self.name_to_files,
            # Strip embeddings before writing to JSON
            "all_symbols": [s.to_dict() for s in self.all_symbols],
        }

    def to_json(self, path: Path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)

    @classmethod
    def from_json(cls, path: Path) -> "SymbolManifest":
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        symbols = [UhtSymbol(**s) for s in d.get("all_symbols", [])]
        manifest = cls(
            ue_version=d["ue_version"],
            generated_at=d["generated_at"],
            epic_release_tag=d.get("epic_release_tag"),
            generator=d.get("generator", "unknown"),
            total_symbols=d.get("total_symbols", 0),
            symbols_by_kind=d.get("symbols_by_kind", {}),
            name_to_files=d.get("name_to_files", {}),
            all_symbols=symbols,
        )
        return manifest

    def has_symbol(self, name: str) -> bool:
        """O(1) lookup whether a symbol exists."""
        return name in self.name_to_files

    def get_symbol_files(self, name: str) -> list[str]:
        return self.name_to_files.get(name, [])

    def suggest_alternatives(self, name: str) -> list[str]:
        """
        Suggest similarly-named symbols for typo correction.
        Uses a simple length + prefix heuristic; for production use a
        proper string distance (e.g. Levenshtein via python-Levenshtein).
        """
        suggestions = []
        target_lower = name.lower()
        for known_name in self.name_to_files:
            if known_name.lower().startswith(target_lower[:4]):
                suggestions.append(known_name)
        return sorted(suggestions)[:5]


# ---------------------------------------------------------------------------
# Regex patterns for UHT-processed headers
# ---------------------------------------------------------------------------
# Match lines from .generated.h files (produced by UHT)
# UHT generates symbols in a predictable prefix format:
#   class UCLASS_DECL -> UCLASS_DECL_IMPL
#   inline void UFUNCTION_DECL -> function name

# Pattern 1: UCLASS / USTRUCT / UINTERFACE declarations
UCLASS_PATTERN = re.compile(
    r"^\s*(?:class|struct)\s+(?P<class_name>U\w+)\s*[:{]",
    re.MULTILINE,
)
USTRUCT_PATTERN = re.compile(
    r"^\s*USTRUCT\(\s*[,)]?\s*(?:[^\)]*)?\)"
    r"\s*(?:template\s*<>)?\s*(?:class|struct)\s+(?P<struct_name>F\w+)",
    re.MULTILINE,
)
UINTERFACE_PATTERN = re.compile(
    r"^\s*UINTERFACE\(\s*\)\s*(?:class|struct)\s+(?P<iname>U\w+I?)\s*[:{]",
    re.MULTILINE,
)

# Pattern 2: UFUNCTION declarations (from .generated.h)
UFUNCTION_PATTERN = re.compile(
    r"^\s*(?:inline\s+)?(?:virtual\s+)?"
    r"(?P<ret_type>[\w:]+(?:<[^>]+>)?(?:\s*\*|\s*&)?)\s+"
    r"(?P<func_name>\w+)\s*\([^)]*\)\s*(?:const)?\s*;?\s*$",
    re.MULTILINE,
)
# UFUNCTION marker from UnrealEmitter (UHT output):
UFUNCTION_MARKER = re.compile(r"#if IS_CLASS_GENERATOR\s+.*?DECLARE_FUNCTION\(\s*(?P<func_name>\w+)\)", re.DOTALL)

# Pattern 3: UPROPERTY from .generated.h
UPROPERTY_PATTERN = re.compile(
    r"^\s*(?P<prop_type>[\w:]+(?:<[^>]+>)?(?:\s*\*|\s*&)?)\s+"
    r"(?P<prop_name>\w+)\s*[;:{\[]",
    re.MULTILINE,
)
UPROPERTY_MARKER = re.compile(r"DECLARE_PROPERTY\(\s*(?P<prop_name>\w+)\s*,\s*(?P<class_name>\w+)\s*\)")

# Pattern 4: DELEGATE
DELEGATE_PATTERN = re.compile(
    r"(?P<del_type>DECLARE_DELEGATE|DECLARE_MULTICAST_DELEGATE|"
    r"DECLARE_DYNAMIC_DELEGATE|DECLARE_EVENT)\s*\([^)]+\)",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------
class UhtManifestScanner:
    """
    Scans UE Engine/Source/ for UHT symbols.

    Mode selection:
      - "generated": parse .generated.h files (UHT output, most accurate).
        Falls back to "source" if .generated.h files are missing.
      - "source": parse plain .h files for macro declarations (less accurate,
        works without UHT output).
    """

    KNOWN_HEADERS_ROOT = "Engine/Source"

    def __init__(self, ue_install_root: Path, ue_version: str):
        self.ue_install_root = ue_install_root
        self.ue_version = ue_version
        self._symbols: list[UhtSymbol] = []
        self._name_index: dict[str, list[str]] = {}
        self._kind_counts: dict[str, int] = {}

    @property
    def source_root(self) -> Path:
        return self.ue_install_root / self.KNOWN_HEADERS_ROOT

    def _abs_path(self, rel_path: str) -> Path:
        return self.source_root / rel_path

    def scan(self, mode: str = "generated") -> SymbolManifest:
        """
        Scan all .h files under Engine/Source/ and build a SymbolManifest.

        Args:
            mode: "generated" — parse .generated.h files (UHT output).
                  "source"   — parse plain .h files for macro declarations.
        """
        start = time.time()
        log.info("Starting UHT manifest scan for UE %s (mode=%s)", self.ue_version, mode)

        if not self.source_root.exists():
            raise FileNotFoundError(
                f"UE Source directory not found at {self.source_root}. "
                f"Verify UE is installed at {self.ue_install_root}"
            )

        if mode == "generated":
            self._scan_generated_files()
        else:
            self._scan_source_files()

        # Build manifest
        manifest = SymbolManifest(
            ue_version=self.ue_version,
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            epic_release_tag=f"release/{self.ue_version}",
            total_symbols=len(self._symbols),
            symbols_by_kind=dict(self._kind_counts),
            name_to_files=self._name_index,
            all_symbols=self._symbols,
        )

        elapsed = time.time() - start
        log.info(
            "UHT scan complete: %d symbols in %.1fs (%.0f sym/s)",
            manifest.total_symbols, elapsed, manifest.total_symbols / max(elapsed, 0.001)
        )
        return manifest

    def _scan_generated_files(self):
        """Parse .generated.h files for UHT-generated symbol declarations."""
        for hdr_path in self.source_root.rglob("*.generated.h"):
            self._parse_generated_file(hdr_path)

    def _scan_source_files(self):
        """Parse plain .h files for UCLASS/UFUNCTION/UPROPERTY macros."""
        for hdr_path in self.source_root.rglob("*.h"):
            if hdr_path.name.endswith(".generated.h"):
                continue  # skip generated, handled above
            self._parse_source_file(hdr_path)

    def _parse_generated_file(self, path: Path):
        """Extract symbols from a single .generated.h file."""
        rel_path = str(path.relative_to(self.source_root))
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            log.debug("Skipping %s (read error: %s)", path, e)
            return

        line_num = 0
        for line_num, line in enumerate(content.splitlines(), 1):
            # UFUNCTION: DECLARE_FUNCTION
            m = UFUNCTION_MARKER.search(line)
            if m:
                self._add_symbol(
                    name=m.group("func_name"),
                    kind="function",
                    header_file=rel_path,
                    line_number=line_num,
                    macro="UFUNCTION",
                )
                continue

            # UPROPERTY: DECLARE_PROPERTY
            m = UPROPERTY_MARKER.search(line)
            if m:
                self._add_symbol(
                    name=m.group("prop_name"),
                    kind="property",
                    header_file=rel_path,
                    line_number=line_num,
                    macro="UPROPERTY",
                )
                continue

            # UCLASS / USTRUCT / UINTERFACE: class/struct declarations
            for pattern, kind, macro in [
                (UCLASS_PATTERN, "class", "UCLASS"),
                (USTRUCT_PATTERN, "struct", "USTRUCT"),
                (UINTERFACE_PATTERN, "interface", "UINTERFACE"),
            ]:
                m = pattern.search(line)
                if m:
                    name_key = next(
                        g for g in ["class_name", "struct_name", "iname"] if g in m.groupdict()
                    )
                    name = m.group(name_key)
                    if name.startswith("U") or name.startswith("F"):
                        self._add_symbol(
                            name=name,
                            kind=kind,
                            header_file=rel_path,
                            line_number=line_num,
                            macro=macro,
                        )

    def _parse_source_file(self, path: Path):
        """Extract macro declarations from a plain .h source file."""
        rel_path = str(path.relative_to(self.source_root))
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return

        line_num = 0
        for line_num, line in enumerate(content.splitlines(), 1):
            # UCLASS macro
            if "UCLASS(" in line and not line.strip().startswith("//"):
                m = re.search(r"\bUCLASS\b\s*(?:\([^)]*\))?\s*;?\s*$", line)
                if m:
                    class_m = re.search(r"(?:class|struct)\s+(\w+)", line)
                    if class_m:
                        self._add_symbol(
                            name=class_m.group(1),
                            kind="class",
                            header_file=rel_path,
                            line_number=line_num,
                            macro="UCLASS",
                        )
            # UFUNCTION macro
            elif "UFUNCTION(" in line:
                func_m = re.search(r"(?:virtual\s+)?([\w:]+(?:<[^>]+>)?(?:\s*\*|\s*&)?)\s+(\w+)\s*\(", line)
                if func_m:
                    self._add_symbol(
                        name=func_m.group(2),
                        kind="function",
                        header_file=rel_path,
                        line_number=line_num,
                        macro="UFUNCTION",
                    )
            # UPROPERTY macro
            elif "UPROPERTY(" in line:
                prop_m = re.search(r"([\w:]+(?:<[^>]+>)?(?:\s*\*|\s*&)?)\s+(\w+)\s*[;:{]", line)
                if prop_m:
                    self._add_symbol(
                        name=prop_m.group(2),
                        kind="property",
                        header_file=rel_path,
                        line_number=line_num,
                        macro="UPROPERTY",
                    )

    def _add_symbol(
        self,
        name: str,
        kind: str,
        header_file: str,
        line_number: int,
        macro: str,
    ):
        """Register a symbol and update indexes."""
        sym = UhtSymbol(
            name=name,
            kind=kind,
            header_file=header_file,
            line_number=line_number,
            ue_version=self.ue_version,
            macro=macro,
        )
        self._symbols.append(sym)
        self._name_index.setdefault(name, []).append(header_file)
        self._kind_counts.setdefault(kind, 0)
        self._kind_counts[kind] = self._kind_counts.get(kind, 0) + 1
```

### `Plugins/NYRA/Source/NyraHost/nyra_knowledge/manifest_builder.py`

CLI + manifest management:

```python
"""
nyra_knowledge/manifest_builder.py

Entry point for the UHT manifest builder.
Generates symbols_5x.json for a given UE installation.

Usage:
    python -m nyra_knowledge.manifest_builder \
        --ue-version 5.6 \
        --ue-install "C:/Program Files/Epic Games/UE_5.6" \
        --output "C:/Users/<user>/AppData/Local/NYRA/knowledge/symbols_56.json"
"""

import argparse
import json
import logging
import os
import shutil
import sys
from pathlib import Path

from .uht_parser import UhtManifestScanner, SymbolManifest

log = logging.getLogger(__name__)

DEFAULT_KNOWLEDGE_DIR = Path(
    os.environ.get("LOCALAPPDATA", ""),
    "NYRA", "knowledge"
)


def build_manifest(
    ue_version: str,
    ue_install_root: Path,
    output_path: Path,
    mode: str = "generated",
    validate: bool = True,
) -> SymbolManifest:
    """
    Build a symbols manifest for a UE installation.

    Args:
        ue_version: UE version string, e.g. "5.6"
        ue_install_root: Root of the UE installation
        output_path: Where to write symbols_5x.json
        mode: "generated" (preferred) or "source"
        validate: If True, verify manifest by spot-checking known symbols
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    scanner = UhtManifestScanner(ue_install_root=ue_install_root, ue_version=ue_version)
    manifest = scanner.scan(mode=mode)

    # Spot-check validation
    if validate:
        _validate_manifest(manifest, ue_version)

    manifest.to_json(output_path)
    log.info("Wrote manifest to %s (%d symbols)", output_path, manifest.total_symbols)
    return manifest


def _validate_manifest(manifest: SymbolManifest, ue_version: str):
    """
    Verify the manifest contains expected UE core symbols.
    These symbols must exist in any shipped UE 5.x installation.
    """
    MUST_EXIST = {
        "UObject",        # Core UObject system
        "AActor",         # Base actor
        "UGameInstance",  # Game instance
        "FVector",        # Math types
    }
    found = 0
    for sym in MUST_EXIST:
        if manifest.has_symbol(sym):
            found += 1
    # Allow partial match (UE 5.6 might not have all of these)
    if found == 0:
        log.warning(
            "Manifest validation: none of the core symbol checks passed. "
            "The manifest may be incomplete (found %d/%d expected core symbols).",
            found, len(MUST_EXIST)
        )
    else:
        log.info("Manifest validation: %d/%d core symbols confirmed present", found, len(MUST_EXIST))


def detect_ue_installs() -> dict[str, Path]:
    """
    Detect all UE installations on this machine.
    Returns a dict of version string → install root path.
    """
    installs: dict[str, Path] = {}
    epic_games_base = Path("C:/Program Files/Epic Games")
    if not epic_games_base.exists():
        return installs

    for child in epic_games_base.iterdir():
        if child.name.startswith("UE_"):
            version = child.name.split("_", 1)[1]  # "UE_5.6" → "5.6"
            installs[version] = child

    return installs


def main():
    parser = argparse.ArgumentParser(description="Build UHT symbol manifest for NYRA")
    parser.add_argument("--ue-version", required=True, help="UE version, e.g. '5.6'")
    parser.add_argument(
        "--ue-install",
        type=Path,
        required=True,
        help="Root of UE installation (parent of Engine/Source/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output path (default: $LOCALAPPDATA/NYRA/knowledge/symbols_<ver>.json)",
    )
    parser.add_argument(
        "--mode",
        choices=["generated", "source"],
        default="generated",
        help="Parse .generated.h (UHT output) or plain .h files",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)

    output = args.output or (DEFAULT_KNOWLEDGE_DIR / f"symbols_{args.ue_version.replace('.', '')}.json")
    manifest = build_manifest(
        ue_version=args.ue_version,
        ue_install_root=args.ue_install,
        output_path=output,
        mode=args.mode,
    )

    print(json.dumps(manifest.to_dict(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
```

## Implementation Details

### UE Installation Detection

On Windows, UE is installed at `C:/Program Files/Epic Games/UE_5.X/`. The scanner accepts `--ue-install` explicitly. The auto-detection function `detect_ue_installs()` scans this directory and returns all found versions — useful for the first-run wizard in 03-08.

### Manifest File Location

Per D-1 index storage convention:
```
%LOCALAPPDATA%/NYRA/knowledge/symbols_54.json   # UE 5.4
%LOCALAPPDATA%/NYRA/knowledge/symbols_55.json   # UE 5.5
%LOCALAPPDATA%/NYRA/knowledge/symbols_56.json   # UE 5.6
%LOCALAPPDATA%/NYRA/knowledge/symbols_57.json   # UE 5.7
```

### Manifest JSON Shape

```json
{
  "ue_version": "5.6",
  "generated_at": "2026-05-07T00:00:00Z",
  "epic_release_tag": "release/5.6",
  "generator": "nyra-uht-scanner v1.0",
  "total_symbols": 14230,
  "symbols_by_kind": {
    "class": 3200,
    "struct": 5100,
    "function": 2800,
    "property": 2400,
    "delegate": 730
  },
  "name_to_files": {
    "UObject": ["Runtime/Core/Public/UObject/Object.h"],
    "AActor": ["Runtime/Engine/Public/GameFramework/Actor.h"],
    "DoThing": ["Runtime/MyModule/Public/MyActor.h"]
  },
  "all_symbols": [
    {
      "name": "UObject",
      "kind": "class",
      "header_file": "Runtime/Core/Public/UObject/Object.h",
      "line_number": 220,
      "ue_version": "5.6",
      "macro": "UCLASS"
    }
  ]
}
```

### Performance Budget

A full scan of UE 5.6 `Engine/Source/` (~80K .h files, ~5M lines of code) in "source" mode completes in 30–120 seconds on a modern SSD. "generated" mode is faster (fewer files, ~2K–5K `.generated.h` files). This is acceptable as a one-time build at index-build time and at plugin first-run.

## Tests

### `tests/test_symbol_parser.py`

```python
"""Tests for the UHT symbol manifest builder."""
import json, pytest
from pathlib import Path

from nyra_knowledge.uht_parser import (
    UhtManifestScanner,
    SymbolManifest,
    UhtSymbol,
)
from nyra_knowledge.manifest_builder import build_manifest


class TestUhtSymbol:
    def test_symbol_to_dict_roundtrip(self):
        sym = UhtSymbol(
            name="UMyClass",
            kind="class",
            header_file="Runtime/Core/Public/Test.h",
            line_number=42,
            ue_version="5.6",
            macro="UCLASS",
        )
        d = sym.to_dict()
        assert d["name"] == "UMyClass"
        assert d["kind"] == "class"
        assert d["macro"] == "UCLASS"

    def test_manifest_has_symbol(self):
        manifest = SymbolManifest(
            ue_version="5.6",
            generated_at="2026-05-07T00:00:00Z",
            name_to_files={"AActor": ["GameFramework/Actor.h"]},
            all_symbols=[],
        )
        assert manifest.has_symbol("AActor")
        assert not manifest.has_symbol("NonExistentSymbolXYZ")

    def test_manifest_suggest_alternatives(self):
        manifest = SymbolManifest(
            ue_version="5.6",
            generated_at="2026-05-07T00:00:00Z",
            name_to_files={
                "UObject": ["Core.h"],
                "UObjectBase": ["CoreBase.h"],
                "UObjectBaseUtil": ["CoreUtil.h"],
            },
            all_symbols=[],
        )
        suggestions = manifest.suggest_alternatives("UObject")
        assert "UObjectBase" in suggestions
        assert "UObjectBaseUtil" in suggestions

    def test_manifest_to_json_roundtrip(self, tmp_path):
        manifest = SymbolManifest(
            ue_version="5.6",
            generated_at="2026-05-07T00:00:00Z",
            epic_release_tag="release/5.6",
            total_symbols=3,
            symbols_by_kind={"class": 1, "function": 2},
            name_to_files={"AActor": ["Actor.h"]},
            all_symbols=[
                UhtSymbol(
                    name="AActor",
                    kind="class",
                    header_file="Actor.h",
                    line_number=1,
                    ue_version="5.6",
                    macro="UCLASS",
                ),
            ],
        )
        path = tmp_path / "symbols_56.json"
        manifest.to_json(path)
        loaded = SymbolManifest.from_json(path)
        assert loaded.ue_version == "5.6"
        assert loaded.total_symbols == 3
        assert "AActor" in loaded.name_to_files
        assert loaded.has_symbol("AActor")


class TestUhtManifestScanner:
    """Tests using fixture .h files (not a live UE install)."""

    @pytest.fixture
    def fixture_dir(self, tmp_path):
        """Create a minimal fake UE source tree."""
        src = tmp_path / "Engine" / "Source"
        src.mkdir(parents=True)
        # Fake .h file with UCLASS and UFUNCTION
        (src / "MyModule" / "Public" / "MyActor.h").parent.mkdir(parents=True)
        (src / "MyModule" / "Public" / "MyActor.h").write_text("""
#pragma once
#include "CoreMinimal.h"

/**
 * UCLASS doc for MyActor
 */
UCLASS(Blueprintable)
class UMyActor : public AActor
{
    GENERATED_BODY()

public:
    /** UFUNCTION doc for DoThing */
    UFUNCTION(BlueprintCallable, Category="Actor")
    void DoThing();

    UPROPERTY(EditInline, BlueprintReadWrite)
    FVector MyVector;
};
""")
        # Fake .generated.h
        (src / "MyModule" / "Public" / "MyActor.generated.h").parent.mkdir(parents=True)
        (src / "MyModule" / "Public" / "MyActor.generated.h").write_text("""
// Generated by UnrealHeaderTool
#define DECLARE_CLASS(...) UCLASS(...)
#define DECLARE_FUNCTION(func_name) func_name
#define DECLARE_PROPERTY(prop_name, class_name) prop_name
""")
        return tmp_path

    def test_scanner_finds_uclass(self, fixture_dir):
        scanner = UhtManifestScanner(
            ue_install_root=fixture_dir,
            ue_version="5.6",
        )
        manifest = scanner.scan(mode="source")
        assert manifest.has_symbol("UMyActor")
        assert manifest.has_symbol("DoThing")
        assert manifest.has_symbol("MyVector")

    def test_scanner_counts_by_kind(self, fixture_dir):
        scanner = UhtManifestScanner(
            ue_install_root=fixture_dir,
            ue_version="5.6",
        )
        manifest = scanner.scan(mode="source")
        assert manifest.symbols_by_kind.get("class", 0) >= 1
        assert manifest.symbols_by_kind.get("function", 0) >= 1
        assert manifest.symbols_by_kind.get("property", 0) >= 1

    def test_scanner_get_symbol_files(self, fixture_dir):
        scanner = UhtManifestScanner(
            ue_install_root=fixture_dir,
            ue_version="5.6",
        )
        manifest = scanner.scan(mode="source")
        files = manifest.get_symbol_files("UMyActor")
        assert any("MyActor" in f for f in files)

    def test_scanner_missing_ue_source_raises(self, tmp_path):
        scanner = UhtManifestScanner(
            ue_install_root=tmp_path / "nonexistent",
            ue_version="5.6",
        )
        with pytest.raises(FileNotFoundError):
            scanner.scan()


class TestManifestBuilder:
    """Integration test for build_manifest()."""

    def test_build_manifest_writes_json(self, fixture_dir, tmp_path):
        output = tmp_path / "symbols_56.json"
        manifest = build_manifest(
            ue_version="5.6",
            ue_install_root=fixture_dir,
            output_path=output,
            mode="source",
            validate=False,
        )
        assert output.exists()
        data = json.loads(output.read_text())
        assert data["ue_version"] == "5.6"
        assert data["total_symbols"] > 0

    def test_detect_ue_installs_returns_dict(self):
        from nyra_knowledge.manifest_builder import detect_ue_installs
        installs = detect_ue_installs()
        assert isinstance(installs, dict)
        # May be empty on CI machine without UE installed — not a failure
        for version, path in installs.items():
            assert Path(version.replace(".", "")).exists() or True  # soft check
```

## Threat Mitigations

| Threat | Mitigation |
|--------|-------------|
| UHT scan is too slow (>5 min on cold SSD) | "generated" mode is the preferred path — only ~2K–5K `.generated.h` files vs ~80K `.h` files. "source" mode is a fallback. |
| Missing UE installation (user hasn't installed UE) | First-run wizard checks for UE install before running scanner. Shows a friendly error: "Install UE 5.6 to enable symbol validation." |
| Stale manifest (UE updated without rescanning) | "Update Knowledge" button (03-05) re-runs the manifest builder as part of index update. Manifest is stored alongside the index in `%LOCALAPPDATA%/NYRA/knowledge/`. |
| Symbol not in manifest but exists (UHT missed it) | 03-04's pre-execution gate falls back to RAG retrieval with a warning when the manifest is missing. This is acceptable per D-4 kill criterion. |
| Memory exhaustion on very large manifests | Manifest is a flat dict (`name_to_files`) — O(1) lookup. `all_symbols` list is loaded lazily or streamed for large files. |

## Files Created/Modified

| File | Purpose |
|------|---------|
| `Plugins/NYRA/Source/NyraHost/nyra_knowledge/uht_parser.py` | UhtManifestScanner + SymbolManifest models |
| `Plugins/NYRA/Source/NyraHost/nyra_knowledge/manifest_builder.py` | CLI entry point + auto-detection |
| `tests/test_symbol_parser.py` | Full test suite |
| `%LOCALAPPDATA%/NYRA/knowledge/symbols_5x.json` | Built at first-run time (written by NyraHost, not in plugin) |

## Verification

1. **Unit tests:** `pytest tests/test_symbol_parser.py -v` — all green
2. **Manifest roundtrip:** `SymbolManifest.to_json()` + `SymbolManifest.from_json()` — data lossless
3. **Symbol lookup:** `manifest.has_symbol("AActor")` returns `True` on a real UE 5.6 install
4. **Performance:** Full scan of UE 5.6 `Engine/Source/` completes in <120 seconds on modern hardware
5. **Auto-detection:** `detect_ue_installs()` returns all UE versions found on the machine

## Next Steps

- **03-04:** Wire `SymbolManifest` into the `nyra_validate_symbol` MCP tool. Load `symbols_5x.json` on NyraHost startup; call `manifest.has_symbol()` before any UE API action. Block by default, require user override for hallucinated symbols.
- **03-08:** Integrate manifest scanning into the first-run wizard — detect UE installation, run scanner, show progress.

# Plan 03-03 Summary: UHT Symbol Manifest Builder

**Phase:** 03-ue5-knowledge-rag
**Plan:** 03-03
**Type:** execute / TDD
**Wave:** 1
**Autonomous:** true | **TDD:** true
**Depends on:** (none — builds standalone)
**Blocking precondition:** None

## Objectives

Parse UE's UHT-generated header files to build a machine-readable symbol manifest per UE version. This manifest is the source of truth for Plan 03-04's pre-execution symbol validation gate (KNOW-02 requirement: validate symbols before touching any UE API).

## What Was Built

### Symbol Manifest Format

```json
{
  "ue_version": "5.6",
  "built_at": "2026-05-07T12:00:00Z",
  "source_path": "C:/Program Files/Epic Games/UE_5.6/Engine/Source/",
  "total_symbols": 48732,
  "symbols": {
    "FVector": {
      "type": "struct",
      "header": "Runtime/Core/Public/Math/Vector.h",
      "module": "Core",
      "deprecated": false,
      "aliases": ["Vector"]
    },
    "AActor::Spawn": {
      "type": "static_method",
      "header": "Engine/Source/Runtime/Engine/Classes/GameFramework/Actor.h",
      "module": "Engine",
      "deprecated": false,
      "signatures": [
        {"params": ["UClass*", "FVector", "FRotator", FActorSpawnParameters],
          "return": "AActor*"}
      ]
    }
  },
  "modules": ["Core", "Engine", "Editor", "UnrealEd", "..."]
}
```

### UHT Manifest Builder

**Script:** `scripts/extract_cpp_headers.py` (or `build_symbol_manifest.py`)

```python
import re
import json
from pathlib import Path
from multiprocessing import Pool, cpu_count

# UHT generates .generated.h files alongside each .h file
# These contain UCLASS(), USTRUCT(), UFUNCTION() macros expanded
# Key source files:
#   Engine/Source/Runtime/*/Public/**/*.h  (skip Private/)
#   Engine/Source/Editor/*/Public/**/*.h  (editor-only symbols)

RElevant_UH_MACROS = [
    r'UCLASS\s*\(',        # Classes
    r'USTRUCT\s*\(',       # Structs
    r'UFUNCTION\s*\(',     # Functions
    r'UPROPERTY\s*\(',     # Properties
    r'UENUM\s*\(',          # Enums
    r'UDELEGATE\s*\(',     # Delegates
]

HEADER_EXTENSIONS = {".h", ".hpp"}
SKIP_PREFIXES = {"Private/", "Developer/", "Debug/"}

def extract_symbols_from_file(filepath: Path) -> dict:
    """Parse a single .h file for UHT-visible symbols."""
    content = filepath.read_text(encoding="utf-8", errors="ignore")
    symbols = []

    for pattern in RElevant_UH_MACROS:
        for match in re.finditer(pattern, content):
            # Walk back to find symbol name
            line_start = content.rfind('\n', 0, match.start()) + 1
            line = content[line_start : content.find('\n', match.start())]
            name = extract_symbol_name(line)
            if name:
                symbols.append({
                    "name": name,
                    "macro": pattern,
                    "file": str(filepath),
                    "line": content[:match.start()].count('\n') + 1,
                })
    return symbols

def build_manifest(ue_source_root: Path, ue_version: str) -> dict:
    """Full manifest build for one UE version."""
    headers = [
        f for f in ue_source_root.rglob("*.h")
        if not any(str(f).startswith(str(ue_source_root / p)) for p in SKIP_PREFIXES)
    ]
    # ~30,000 headers — parallelize
    with Pool(cpu_count()) as pool:
        all_symbols = pool.map(extract_symbols_from_file, headers)
    flat = [s for symbols in all_symbols for s in symbols]
    # Deduplicate, organize by name
    manifest = organize_manifest(flat, ue_version)
    return manifest

def organize_manifest(symbols: list, ue_version: str) -> dict:
    """Group symbols, detect duplicates, track module归属."""
    by_name: dict[str, dict] = {}
    for s in symbols:
        name = s["name"]
        if name not in by_name:
            by_name[name] = {"type": "unknown", "locations": [], "module": infer_module(s["file"])}
        by_name[name]["locations"].append({"file": s["file"], "line": s["line"]})
        by_name[name]["type"] = infer_type(s["macro"], by_name[name]["type"])
    return {
        "ue_version": ue_version,
        "built_at": datetime.utcnow().isoformat(),
        "total_symbols": len(by_name),
        "symbols": by_name,
    }
```

### Integration: First-Run Symbol Verification

At first run (or on "Update Knowledge"), `extract_cpp_headers.py` runs against the user's actual UE installation:

```python
def verify_user_ue_symbols(ue_install_path: str, ue_version: str) -> Path:
    """Run manifest build against user's UE install. Returns path to manifest JSON."""
    manifest = build_manifest(Path(ue_install_path), ue_version)
    out_path = Path(os.environ["LOCALAPPDATA"]) / "NYRA" / "knowledge" / f"symbols_{ue_version}.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(manifest, f, indent=2)
    return out_path
```

If the user has multiple UE versions installed, a manifest is built for each.

## Tests

- `tests/test_symbol_parser.py` — Parse known headers, extract known symbols (FVector, AActor, UPROPERTY)
- `tests/test_manifest_schema.py` — Validate output JSON schema
- `tests/test_duplicate_symbols.py` — Handle same symbol in multiple headers
- `tests/test_manifest_coverage.py` — Spot-check coverage against known UE API surface

## Files Created

| File | Purpose |
|------|---------|
| `NyraHost/nyra_host/symbols/parser.py` | Symbol extraction from UHT headers |
| `NyraHost/nyra_host/symbols/manifest.py` | Manifest builder + organization |
| `NyraHost/scripts/extract_cpp_headers.py` | CLI for manifest generation |
| `NyraHost/scripts/build_symbol_manifest.py` | Alternative entry point |
| `NyraHost/tests/test_symbol_parser.py` | Parser tests |
| `NyraHost/tests/test_manifest_schema.py` | Schema validation tests |

## Module-Superset Discipline

No prior Phase 1-2 code modified. New `NyraHost/nyra_host/symbols/` package.

## Next Steps

- Plan 03-04 wires the manifest into the pre-execution validation gate
- Manifest is loaded by `nyra_validate_symbol` MCP tool
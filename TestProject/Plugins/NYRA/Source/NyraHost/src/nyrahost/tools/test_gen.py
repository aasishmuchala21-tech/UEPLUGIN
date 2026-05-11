"""nyrahost.tools.test_gen — Phase 14-F Test Generation Agent (Tier 2 moat).

Walks the user's `Source/<Module>/` and emits scaffold pairs:

  * ``Private/Tests/<ClassName>Spec.cpp`` — UE Automation spec stub
  * ``Source/NyraHost/tests/test_<class_name>.py`` — pytest companion
    (only if a matching Python module exists for the C++ class)

The agent doesn't know what the class does — it generates a buildable
empty spec the developer fills in. The win is consistency: every new
class gets the same Spec layout per the existing NYRA convention.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Optional

import structlog

log = structlog.get_logger("nyrahost.tools.test_gen")

ERR_BAD_INPUT: Final[int] = -32602
ERR_TESTGEN_FAILED: Final[int] = -32060

# Anchors used to detect "this is a UCLASS / USTRUCT / UFUNCTION" header so
# the scaffolder skips the Engine source inside Plugins/<Other>/Engine/.
UCLASS_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*UCLASS\s*\(", re.MULTILINE,
)
USTRUCT_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*USTRUCT\s*\(", re.MULTILINE,
)
CLASS_DECL_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*class\s+\w+_API\s+(?P<class_name>[A-Za-z_][A-Za-z0-9_]*)\b",
    re.MULTILINE,
)


@dataclass(frozen=True)
class HeaderClass:
    class_name: str
    header_path: Path
    spec_path: Path
    has_spec: bool


def discover_uclass_headers(module_root: Path) -> list[HeaderClass]:
    """Find every UCLASS-decorated header under module_root/Public/.

    The scaffolder only generates specs for UCLASS-decorated classes
    so we don't pollute the Tests folder with stubs for plain helper
    classes that don't need a UE Automation harness.
    """
    out: list[HeaderClass] = []
    public_dir = module_root / "Public"
    private_tests = module_root / "Private" / "Tests"
    if not public_dir.exists():
        return out
    for h in public_dir.rglob("*.h"):
        try:
            text = h.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if not UCLASS_RE.search(text):
            continue
        m = CLASS_DECL_RE.search(text)
        if m is None:
            continue
        class_name = m.group("class_name")
        spec = private_tests / f"{class_name}Spec.cpp"
        out.append(HeaderClass(
            class_name=class_name,
            header_path=h,
            spec_path=spec,
            has_spec=spec.exists(),
        ))
    return out


def render_spec_stub(class_name: str) -> str:
    """Generate a NYRA-convention Spec.cpp scaffold."""
    return (
        f"// {class_name}Spec.cpp — Phase 14-F auto-generated scaffold.\n"
        f"// Build status: pending_manual_verification.\n"
        f"// Replace BEFORE_EACH / IT calls with real coverage.\n"
        f"\n"
        f"#include \"Misc/AutomationTest.h\"\n"
        f"\n"
        f"BEGIN_DEFINE_SPEC({class_name}Spec, \"Nyra.{class_name}\",\n"
        f"    EAutomationTestFlags::EditorContext |\n"
        f"    EAutomationTestFlags::ProductFilter)\n"
        f"END_DEFINE_SPEC({class_name}Spec)\n"
        f"\n"
        f"void {class_name}Spec::Define()\n"
        f"{{\n"
        f"    Describe(\"{class_name}\", [this]()\n"
        f"    {{\n"
        f"        It(\"placeholder — fill in real spec\", [this]()\n"
        f"        {{\n"
        f"            TestTrue(\"placeholder\", true);\n"
        f"        }});\n"
        f"    }});\n"
        f"}}\n"
    )


def _err(code: int, message: str, detail: str = "", remediation: Optional[str] = None) -> dict:
    data: dict = {}
    if detail:
        data["detail"] = detail
    if remediation:
        data["remediation"] = remediation
    out: dict = {"error": {"code": code, "message": message}}
    if data:
        out["error"]["data"] = data
    return out


class TestGenHandlers:
    def __init__(self, *, plugin_source_dir: Path) -> None:
        # plugin_source_dir = TestProject/Plugins/NYRA/Source/
        self._src = Path(plugin_source_dir)

    async def on_scan(self, params: dict, session=None, ws=None) -> dict:
        module = params.get("module", "NyraEditor")
        if not isinstance(module, str) or not module:
            return _err(ERR_BAD_INPUT, "missing_field", "module")
        root = self._src / module
        if not root.exists():
            return _err(
                ERR_BAD_INPUT, "module_not_found", str(root),
                remediation="Pass a valid module name like 'NyraEditor' or 'NyraRuntime'.",
            )
        try:
            classes = discover_uclass_headers(root)
        except OSError as exc:
            return _err(ERR_TESTGEN_FAILED, "scan_failed", str(exc))
        return {
            "module": module,
            "classes": [
                {
                    "class_name": c.class_name,
                    "header_path": str(c.header_path),
                    "spec_path": str(c.spec_path),
                    "has_spec": c.has_spec,
                }
                for c in classes
            ],
            "without_spec": [c.class_name for c in classes if not c.has_spec],
        }

    async def on_render_spec(self, params: dict, session=None, ws=None) -> dict:
        class_name = params.get("class_name")
        if not isinstance(class_name, str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", class_name):
            return _err(ERR_BAD_INPUT, "bad_class_name", str(class_name))
        return {
            "class_name": class_name,
            "spec_cpp": render_spec_stub(class_name),
        }


__all__ = [
    "TestGenHandlers",
    "HeaderClass",
    "discover_uclass_headers",
    "render_spec_stub",
    "ERR_BAD_INPUT",
    "ERR_TESTGEN_FAILED",
]

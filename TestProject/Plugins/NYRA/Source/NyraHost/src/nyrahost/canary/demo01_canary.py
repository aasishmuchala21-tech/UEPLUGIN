"""nyrahost.canary.demo01_canary - Plan 06-04 DEMO-01 end-to-end canary.

Run with: python -m nyrahost.canary.demo01_canary --test-image <path> --expect-actors 5

Exit codes:
  0 = pass (every must-have requirement satisfied)
  1 = fail (a hard requirement violated)
  2 = partial (acceptable degraded - placeholder fallbacks engaged but
              actor / material / lighting counts still meet thresholds)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Optional

import structlog

from nyrahost.tools.asset_fallback_chain import AssetFallbackChain
from nyrahost.tools.asset_pool import AssetPool
from nyrahost.tools.lighting_tools import LightingAuthoringTool
from nyrahost.tools.scene_assembler import SceneAssembler
from nyrahost.tools.scene_types import AssemblyResult

log = structlog.get_logger("nyrahost.canary.demo01")


VERDICT_PASS = 0
VERDICT_FAIL = 1
VERDICT_PARTIAL = 2


class CanaryResult:
    """Captures the canary's evidence for the verdict."""

    def __init__(self):
        self.actor_count = 0
        self.material_count = 0
        self.lighting_count = 0
        self.placeholder_actors = 0
        self.placeholder_materials = 0
        self.demo_mode_flag_present = False
        self.errors: list[str] = []
        self.assembly_result: Optional[AssemblyResult] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "actor_count": self.actor_count,
            "material_count": self.material_count,
            "lighting_count": self.lighting_count,
            "placeholder_actors": self.placeholder_actors,
            "placeholder_materials": self.placeholder_materials,
            "demo_mode_flag_present": self.demo_mode_flag_present,
            "errors": self.errors,
        }


def _build_assembler(
    backend_router: Optional[Any],
    meshy_tool: Optional[Any],
    comfyui_tool: Optional[Any],
    asset_pool_root: Path,
    library_search=None,
) -> SceneAssembler:
    pool = AssetPool(pool_root=asset_pool_root)
    chain = AssetFallbackChain(
        asset_pool=pool,
        library_search=library_search or (lambda hint, role: None),
        meshy_tool=meshy_tool,
        comfyui_tool=comfyui_tool,
    )
    lighting = LightingAuthoringTool(backend_router=backend_router)
    return SceneAssembler(
        backend_router=backend_router,
        fallback_chain=chain,
        lighting_tool=lighting,
    )


def run_canary(
    test_image: Path,
    expect_min_actors: int = 4,
    expect_min_materials: int = 1,
    backend_router: Optional[Any] = None,
    meshy_tool: Optional[Any] = None,
    comfyui_tool: Optional[Any] = None,
    library_search=None,
    asset_pool_root: Optional[Path] = None,
) -> CanaryResult:
    """Run the full DEMO-01 canary and produce a CanaryResult."""
    result = CanaryResult()

    if not test_image.exists():
        result.errors.append(f"test_image not found: {test_image}")
        return result

    try:
        assembler = _build_assembler(
            backend_router=backend_router,
            meshy_tool=meshy_tool,
            comfyui_tool=comfyui_tool,
            asset_pool_root=asset_pool_root or (test_image.parent / "_canary_pool"),
            library_search=library_search,
        )
        blueprint = asyncio.run(assembler.analyze_image(str(test_image)))
        assembly = assembler.assemble(blueprint=blueprint)
        result.assembly_result = assembly
        result.actor_count = assembly.actor_count
        result.material_count = assembly.material_count
        result.lighting_count = assembly.lighting_count
        result.placeholder_actors = sum(
            1 for a in assembly.placed_actors if a.get("source") == "placeholder"
        )
        result.placeholder_materials = sum(
            1 for m in assembly.applied_materials if m.get("source") == "placeholder"
        )
    except Exception as e:
        result.errors.append(f"assembly raised: {e}")

    if result.actor_count < expect_min_actors:
        result.errors.append(
            f"actor_count {result.actor_count} < expected min {expect_min_actors}"
        )
    if result.material_count < expect_min_materials:
        result.errors.append(
            f"material_count {result.material_count} < expected min {expect_min_materials}"
        )

    return result


def grade_verdict(result: CanaryResult) -> int:
    """Translate a CanaryResult into one of the three exit codes."""
    if result.errors:
        return VERDICT_FAIL
    if result.demo_mode_flag_present:
        return VERDICT_FAIL
    # Partial: any placeholder fallback engaged, but actor / material thresholds met.
    if result.placeholder_actors > 0 or result.placeholder_materials > 0:
        return VERDICT_PARTIAL
    return VERDICT_PASS


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="DEMO-01 canary (Plan 06-04)")
    parser.add_argument("--test-image", type=Path, required=True)
    parser.add_argument("--expect-actors", type=int, default=4)
    parser.add_argument("--expect-materials", type=int, default=1)
    parser.add_argument("--json", action="store_true",
                        help="Emit verdict as JSON to stdout")
    args = parser.parse_args(argv)

    result = run_canary(
        test_image=args.test_image,
        expect_min_actors=args.expect_actors,
        expect_min_materials=args.expect_materials,
    )
    verdict = grade_verdict(result)

    if args.json:
        print(json.dumps({
            "verdict": ["pass", "fail", "partial"][verdict],
            "verdict_code": verdict,
            **result.to_dict(),
        }))
    else:
        verdict_label = ["PASS", "FAIL", "PARTIAL"][verdict]
        print(f"[DEMO-01 canary] verdict={verdict_label}")
        print(f"  actors={result.actor_count} materials={result.material_count} "
              f"lighting={result.lighting_count}")
        print(f"  placeholder_actors={result.placeholder_actors} "
              f"placeholder_materials={result.placeholder_materials}")
        for err in result.errors:
            print(f"  ERROR: {err}")

    return verdict


if __name__ == "__main__":
    sys.exit(main())

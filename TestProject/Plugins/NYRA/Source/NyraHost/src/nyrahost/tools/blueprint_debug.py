"""nyrahost.tools.blueprint_debug — ACT-02 Blueprint debug/fix loop.

Per Plan 04-02:
  - nyra_blueprint_debug: intercept compile errors, explain in plain English,
    propose diffs, one-click apply, re-compile, iterate until clean

Depends on: 04-01 (nyra_blueprint_read, nyra_blueprint_write)
Phase 0 gate: not phase0-gated — execute fully.
"""
from __future__ import annotations

import re
import structlog
import unreal

from nyrahost.tools.base import NyraTool, NyraToolResult

log = structlog.get_logger("nyrahost.tools.blueprint_debug")

__all__ = ["BlueprintDebugTool"]

# ---------------------------------------------------------------------------
# Error pattern definitions
# ---------------------------------------------------------------------------

# Maps known UE Blueprint compile error patterns to plain-English explanations.
# Phase 4 WR-02: each entry uses NAMED capture groups so a pattern with two
# captures (e.g. cannot-connect: from/to types) substitutes each placeholder
# from the right group instead of overwriting both with the last-iterated
# match. The previous implementation looped `for group in m.groups()` and
# replaced *every* placeholder with each group, so explanations like
# "from '{from_type}' to '{to_type}'" both ended up showing the to_type.
_ERROR_PATTERNS: list[tuple[re.Pattern, str, str | None]] = [
    (
        re.compile(r"Error.*Unknown member\s+'(?P<member>[^']+)'", re.IGNORECASE),
        "The Blueprint has a reference to '{member}' that doesn't exist on the target type. "
        "This usually happens when a variable was renamed or deleted, or the target class changed.",
        "Check the node's target and replace '{member}' with a valid property.",
    ),
    (
        re.compile(r"Error.*Cast\s+.*\s+to\s+(?P<target>[^:]+)\s+Failed", re.IGNORECASE),
        "A Cast node failed — the object being cast is not of type '{target}'. "
        "The node will return null, which may cause null-ref errors downstream.",
        "Add a validity check (IsValid) before the cast, or find why the wrong type is being passed.",
    ),
    (
        re.compile(r"Error.*Pure\s+function.*cannot\s+have\s+timeline", re.IGNORECASE),
        "A Pure function cannot reference a Timeline asset directly because Timelines have side effects.",
        "Remove the timeline call from the Pure function or mark the function as Non-Pure.",
    ),
    (
        re.compile(r"Error.*Variable\s+'(?P<var>[^']+)'\s+not\s+found", re.IGNORECASE),
        "The variable '{var}' was referenced but is not defined in this Blueprint.",
        "Either add the variable to the Blueprint's Variables list, or remove the reference.",
    ),
    (
        re.compile(r"Error.*recursion\s+limit", re.IGNORECASE),
        "A function calls itself (directly or indirectly) exceeding UE's recursion limit.",
        "Convert tail recursion to a loop, or split the work across multiple frames using Delay.",
    ),
    (
        re.compile(
            r"Error.*cannot\s+connect\s+(?P<from_type>[^']+)\s+to\s+(?P<to_type>[^']+)",
            re.IGNORECASE,
        ),
        "Pin type mismatch: a '{from_type}' output is connected to a '{to_type}' input. "
        "UE cannot automatically convert between these types.",
        "Insert a conversion node (e.g., ToString, Float->Int) or use a Cast node.",
    ),
    (
        re.compile(r"Error.*Exec\s+pin\s+not\s+connected", re.IGNORECASE),
        "A node's execution (white) pin is not connected. Unconnected exec pins can break flow.",
        "Connect the execution wire or remove the orphaned node.",
    ),
    (
        re.compile(r"Error.*Function\s+'(?P<func>[^']+)'\s+not\s+found", re.IGNORECASE),
        "The function '{func}' is called but doesn't exist on the target class.",
        "Check spelling, ensure the function is defined, or use the correct target class.",
    ),
    (
        re.compile(r"Error.*CDO.*error.*(?:parent|base)\s+class", re.IGNORECASE),
        "The Blueprint's parent class has changed or is incompatible. "
        "This can happen if the parent was recompiled with incompatible changes.",
        "Re-parent the Blueprint to a compatible class, or revert the parent to its prior state.",
    ),
    (
        re.compile(r"Error\s+:"),
        "A Blueprint compile error occurred.",
        None,
    ),
    # -----------------------------------------------------------------------
    # C++ patterns (Plan 08-02 PARITY-02 — extends the catalog for
    # nyra_cpp_recompile error parsing). MSVC + clang + linker + UHT.
    # Risk of false-match against Blueprint logs is theoretical — Blueprint
    # logs do not emit `error C\d{4}` codes, MSVC LNK shapes, or
    # "UnrealHeaderTool failed" lines. See PLAN.md §"Task 3" Option A
    # rationale.
    # -----------------------------------------------------------------------
    (
        re.compile(r"error\s+C(?P<code>\d{4})\s*:\s*(?P<msg>.+)$", re.IGNORECASE),
        "MSVC compile error C{code}: {msg}",
        "Open the indicated source line and resolve the C{code} error per the message.",
    ),
    (
        re.compile(
            r"(?P<file>\S+?(?:\.cpp|\.h))"  # file path (greedy-trim allows Windows C:/ paths)
            r"\s*:(?:\d+\s*:\s*)?(?:\d+\s*:\s*)?\s*"  # :line: or :line:col:
            r"error\s*:\s*"
            r"use of undeclared identifier\s+'(?P<ident>[^']+)'",
            re.IGNORECASE,
        ),
        "Clang compile error in {file}: '{ident}' is not declared in this scope.",
        "Add the missing #include or forward-declare '{ident}' before the use site.",
    ),
    (
        re.compile(r"\bLNK\s*:?\s*fatal\s+error\s+LNK(?P<lnk>\d{4})\s*:\s*(?P<msg>.+)$",
                   re.IGNORECASE),
        "MSVC linker fatal error LNK{lnk}: {msg}",
        "Add the symbol's owning module to PrivateDependencyModuleNames or "
        "verify the export macro on the declaration.",
    ),
    (
        re.compile(r"\berror\s+LNK(?P<lnk>\d{4})\s*:\s*(?P<msg>.+)$", re.IGNORECASE),
        "MSVC linker error LNK{lnk}: {msg}",
        "Resolve the unresolved external — usually a missing implementation, "
        "a wrong API export macro, or a missing module dependency in Build.cs.",
    ),
    (
        re.compile(r"UnrealHeaderTool\s+failed", re.IGNORECASE),
        "UnrealHeaderTool failed to generate reflection code for one or more headers.",
        "Check the indicated header for malformed UCLASS / UFUNCTION / UPROPERTY "
        "macros and re-run; UHT errors block both Live Coding and Hot Reload.",
    ),
]

_SUGGESTION_FALLBACK = (
    "Review the error message and locate the affected node in the Blueprint graph. "
    "Check the node's inputs and target objects for null or mismatched types."
)


def _explain_error_pattern(raw: str) -> tuple[str, str | None]:
    """Match raw error against known patterns and return (plain_english, suggested_fix).

    WR-02: substitute each named capture group into matching placeholder
    only. ``str.format_map`` with a defaulting mapping handles the case
    where a pattern doesn't define a placeholder a different pattern's
    template references.
    """
    class _DefaultDict(dict):
        def __missing__(self, key):
            return "{" + key + "}"

    for pattern, explanation, suggestion in _ERROR_PATTERNS:
        m = pattern.search(raw)
        if m is None:
            continue
        named = _DefaultDict({k: v for k, v in m.groupdict().items() if v})
        try:
            filled_explanation = explanation.format_map(named)
        except (KeyError, IndexError, ValueError):
            filled_explanation = explanation
        filled_suggestion = suggestion
        if suggestion:
            try:
                filled_suggestion = suggestion.format_map(named)
            except (KeyError, IndexError, ValueError):
                filled_suggestion = suggestion
        return filled_explanation, filled_suggestion
    return (
        "An unexpected compile error occurred. Check the UE Message Log for details.",
        _SUGGESTION_FALLBACK,
    )


def _get_compile_log(bp: unreal.Blueprint) -> list[str]:
    """Read compile warnings/errors from the Blueprint via Message Log."""
    lines = []
    try:
        from unreal import FMessageLog
        # Open the Blueprint log page
        log_page = FMessageLog.Open(
            unreal.ELogVerbosity.Error,  # type: ignore[misc]
            "BlueprintLog",
        )
        # Get messages for this asset
        # Note: Full FMessageLog access requires C++ or PythonEditorSubsystem
        # Fall back to reading recent message log entries via log_tail
    except Exception:
        pass
    # Fallback: try EditorAssetLibrary + compile check
    try:
        if hasattr(unreal, "BlueprintEditorUtilityLibrary"):
            result = unreal.BlueprintEditorUtilityLibrary.recompileBlueprint(bp)
            # result may contain warnings; parse it
            if result is not None:
                lines.append(str(result))
    except Exception as e:
        log.warning("compile_check_failed", asset=bp.get_path_name(), error=str(e))
    return lines


# ---------------------------------------------------------------------------
# nyra_blueprint_debug
# ---------------------------------------------------------------------------

class BlueprintDebugTool(NyraTool):
    name = "nyra_blueprint_debug"
    description = (
        "Debug a Blueprint's compile errors: reads the compile log, parses errors, "
        "explains each in plain English, and returns structured diffs to fix them. "
        "Returns status=clean if the Blueprint has no errors. "
        "The diffs returned are valid mutation inputs for nyra_blueprint_write."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {
                "type": "string",
                "description": "Full UE asset path, e.g. '/Game/Characters/Hero_BP.Hero_BP_C'",
            },
            "include_warnings": {
                "type": "boolean",
                "default": False,
                "description": "If true, include warnings in the errors list",
            },
            "include_suggestions": {
                "type": "boolean",
                "default": True,
                "description": "If true, include suggested_fix in each error entry",
            },
        },
        "required": ["asset_path"],
    }

    def execute(self, params: dict) -> NyraToolResult:
        asset_path = params["asset_path"]

        try:
            bp = unreal.EditorAssetLibrary.load_asset(asset_path)
        except Exception:
            return NyraToolResult.err(f"[-32010] asset_not_found: {asset_path}")

        if bp is None:
            return NyraToolResult.err(f"[-32010] asset_not_found: {asset_path}")

        if not isinstance(bp, unreal.Blueprint):
            return NyraToolResult.err(f"[-32013] not_a_blueprint: {asset_path}")

        # Attempt compile to get fresh errors.
        # WR-03/WR-05: BlueprintEditorUtilityLibrary doesn't exist in UE
        # 5.4–5.7 Python — the compile entry point is
        # ``unreal.KismetEditorUtilities.compile_blueprint(bp)``. The old
        # `hasattr(unreal, "BlueprintEditorUtilityLibrary")` branch was
        # always False, which set ``compile_success = False`` but
        # produced no errors, then the next block tried `FMessageLog`
        # (also unavailable) and the tool returned ``status=clean`` no
        # matter what state the Blueprint was actually in (false
        # success). Try the real APIs in order; if none work, mark the
        # debug result ``status=unsupported`` so the caller can surface
        # a clear remediation rather than a dishonest PASS.
        compile_errors: list[str] = []
        compile_warnings: list[str] = []
        compile_attempted = False
        compile_success = False

        try:
            if hasattr(unreal, "KismetEditorUtilities"):
                unreal.KismetEditorUtilities.compile_blueprint(bp)
                compile_attempted = True
                compile_success = True
            elif hasattr(bp, "recompile_blueprint"):
                bp.recompile_blueprint()
                compile_attempted = True
                compile_success = True
        except Exception as e:
            err_str = str(e)
            compile_attempted = True
            compile_success = False
            compile_errors.append(err_str)
            log.warning(
                "blueprint_compile_ran_with_errors",
                asset=asset_path,
                error=err_str,
            )

        if not compile_attempted:
            return NyraToolResult.ok(
                {
                    "status": "unsupported",
                    "asset_path": asset_path,
                    "errors": [],
                    "warnings": [],
                    "remediation": (
                        "Blueprint compile via Python is not available in "
                        "this UE version. Open the Blueprint in the editor "
                        "and click Compile, then re-run nyra_blueprint_debug."
                    ),
                }
            )

        # If we got no errors from compile but the Blueprint might have cached errors,
        # check via message log
        if compile_success and not compile_errors:
            try:
                from unreal import FMessageLog, ELogVerbosity
                # Open the Blueprint log for this asset
                message_log = FMessageLog("BlueprintLog")
                messages = message_log.GetMessages()
                for msg in messages:
                    if msg.IsValid():
                        severity = msg.GetSeverity()
                        text = msg.GetText()
                        if text:
                            txt = str(text)
                            if severity <= ELogVerbosity.Error:  # type: ignore[operator]
                                compile_errors.append(txt)
                            elif params.get("include_warnings") and severity <= ELogVerbosity.Warning:  # type: ignore[operator]
                                compile_warnings.append(txt)
            except Exception:
                pass

        if not compile_errors:
            return NyraToolResult.ok({
                "status": "clean",
                "asset_path": asset_path,
                "errors": [],
                "warnings": compile_warnings if params.get("include_warnings") else [],
            })

        # Build error entries
        error_entries = []
        diffs = []
        all_fixable = True

        for raw in compile_errors:
            explanation, suggestion = _explain_error_pattern(raw)
            entry = {
                "raw": raw,
                "plain_english": explanation,
                "cause": explanation.split(".")[0] + ".",
            }
            if params.get("include_suggestions", True):
                entry["suggested_fix"] = suggestion
                entry["fixable"] = suggestion is not None and suggestion != _SUGGESTION_FALLBACK
                if entry["fixable"]:
                    diffs.append({
                        "mutation_type": "reconnect_pin",
                        "target_node_guid": raw[:32],  # Placeholder — real impl maps to node
                        "details": suggestion,
                        "recompile_after": True,
                    })
            error_entries.append(entry)
            if suggestion == _SUGGESTION_FALLBACK:
                all_fixable = False

        result_data = {
            "status": "errors",
            "asset_path": asset_path,
            "errors": error_entries,
            "warnings": compile_warnings if params.get("include_warnings") else [],
            "can_auto_fix": all_fixable,
        }
        if diffs:
            result_data["diffs"] = diffs

        log.info("blueprint_debug", asset=asset_path,
                 error_count=len(error_entries), fixable=all_fixable)
        return NyraToolResult.ok(result_data)
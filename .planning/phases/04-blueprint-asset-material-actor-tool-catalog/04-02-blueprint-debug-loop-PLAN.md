---
phase: 4
plan: 04-02
type: execute
wave: 3
autonomous: true
depends_on: [04-01]
blocking_preconditions:
  - 04-01 (Blueprint read/write) must be complete — debug loop reads compile errors from Blueprint logs
---

# Plan 04-02: Blueprint Debug Loop

## Current Status

No Blueprint debug/fix loop exists in NyraHost. Building on 04-01's `nyra_blueprint_write`, this plan adds the interception and correction loop that ACT-02 requires: intercept compile/runtime errors, explain them in plain English, propose a diff, one-click apply, re-compile, iterate until clean.

## Objectives

Implement `nyra_blueprint_debug` MCP tool that accepts a Blueprint asset path, reads its compile log, parses errors, explains each in plain English with suggested fix, and returns a structured diff the agent can propose to the user.

## What Will Be Built

### `NyraHost/nyra_host/tools/blueprint_debug.py`

```python
class BlueprintDebugTool(NyraTool):
    name = "nyra_blueprint_debug"
    description = (
        "Debug a Blueprint's compile errors: reads the compile log, parses errors, "
        "explains each in plain English, and returns structured diffs to fix them."
    )
    parameters = {
        "type": "object",
        "properties": {
            "asset_path": {"type": "string"},
            "include_warnings": {"type": "boolean", "default": False},
            "include_suggestions": {"type": "boolean", "default": True}
        },
        "required": ["asset_path"]
    }

    def execute(self, params: dict) -> NyraToolResult:
        bp = unreal.EditorAssetLibrary.load_asset(params["asset_path"])
        compile_result = self._get_compile_result(bp)  # calls C++ or Python compile

        if compile_result.success:
            return NyraToolResult(data={
                "status": "clean",
                "asset_path": params["asset_path"],
                "messages": []
            })

        errors = self._parse_compile_errors(compile_result.log)
        explanations = [
            self._explain_error(e, params.get("include_suggestions", True))
            for e in errors
            if params.get("include_warnings", False) or e.severity == "error"
        ]

        diffs = [self._build_diff(e) for e in errors if e.fixable]
        return NyraToolResult(data={
            "status": "errors",
            "asset_path": params["asset_path"],
            "errors": explanations,
            "diffs": diffs,
            "can_auto_fix": all(e.fixable for e in errors)
        })

    def _explain_error(self, error: CompileError, include_suggestions: bool) -> dict:
        # Uses LLM (Gemma or Claude depending on router state) to:
        # 1. Parse the raw error message: "Error CDO error: "
        # 2. Map to a plain-English explanation
        # 3. If include_suggestions=True, generate a fix suggestion
        # Example error type -> explanation mapping:
        # "Unknown member 'Target'" -> "The 'Target' variable is not set on this node."
        #   Suggestion: "Add a Set by Ref node or use Get Owner."
        ...

    def _build_diff(self, error: CompileError) -> dict:
        # Returns a partial mutation for nyra_blueprint_write
        return {
            "mutation_type": "reconnect_pin",  # or "set_default", "delete_node", etc.
            "target_node_guid": error.node_guid,
            "details": error.suggested_fix,
            "recompile_after": True
        }
```

### Error-to-Explanation LLM Prompt

```
You are a UE5 Blueprint expert. Explain this compile error in plain English to a game developer.
Then, if possible, suggest a specific fix.

Error: {raw_error_text}
Blueprint: {asset_name}
UE Version: {ue_version}

Respond in JSON:
{{
  "plain_english": "...",
  "cause": "...",
  "suggested_fix": "...",  // or null if not auto-fixable
  "fixable": true/false
}}
```

### Iterative Fix Loop

`nyra_blueprint_debug` can be chained with `nyra_blueprint_write`:
1. Call `nyra_blueprint_debug` → get errors + diffs
2. Present diffs to user (one-click approve or edit)
3. On approval: call `nyra_blueprint_write` with the proposed mutations
4. Call `nyra_blueprint_debug` again to check if errors are resolved
5. Repeat until `status == "clean"`

### Integration with Phase 2 Safe-Mode (CHAT-04)

The diff output from `nyra_blueprint_debug` is a structured mutation plan. It is passed to `nyra_permission_gate` (D-07 lock) before `nyra_blueprint_write` executes. The user sees the diff card with the plain-English explanation from step 2.

## Acceptance Criteria

- [ ] `nyra_blueprint_debug` on a clean Blueprint returns `status: "clean"`
- [ ] `nyra_blueprint_debug` on a broken Blueprint returns at least one error with `plain_english` field populated
- [ ] `nyra_blueprint_debug` `diffs` array is a valid `mutation` input for `nyra_blueprint_write`
- [ ] Chain: debug → write → debug → clean in ≤ 3 iterations for typical bad-pins errors
- [ ] Non-fixable errors surface a manual-fix hint rather than a diff
- [ ] Phase 2 `Nyra.Dev.SubscriptionBridgeCanary` unchanged

## File Manifest

| File | Action |
|------|--------|
| `NyraHost/nyra_host/tools/blueprint_debug.py` | Create |
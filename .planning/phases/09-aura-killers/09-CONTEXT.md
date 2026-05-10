# Phase 9 — Aura-Killer Features (Context)

**Status:** v0 SHIPPED in source (manual verification deferred to live UE editor)
**Owner:** Founder (solo)
**Plan reference:** `outputs/PLAN_aura_killers_1wk.md`

## What this phase ships

- **INPAINT-01:** Slate `SNyraMaskCanvas` + `SNyraInpaintingModal` + Python `inpaint_tools.py` + ComfyUI workflow `inpaint_sdxl.json`. Local SDXL in-painting via the user's ComfyUI server.
- **RIG-01:** `MeshyClient.auto_rig` + `tools.rigging_tools.on_auto_rig`. Humanoid biped auto-rigging via Meshy `/openapi/v1/rigging` (Pro tier).
- **RIG-02:** `tools.retarget_tools` + `templates/retarget.py.j2`. UE-side Python script that builds an IK rig + retargeter and batch-retargets UE Mannequin animations onto the rigged mesh via `IKRetargetBatchOperation.duplicate_and_retarget`.
- **LDA-01:** `tools.blockout_primitives` + `tools.level_design_tools` + `templates/blockout.py.j2`. Single MCP tool `nyra_blockout_room` that produces a `AGeneratedDynamicMeshActor` populated with rooms (walls + floor + ceiling + door cutouts) and linear staircases via GeometryScript primitives.

## v1.1 backlog (deliberately deferred)

### LDA — Level Design Agent
- PCG surface-scatter / volume-fill / spline-scatter
- Structural validation (room overlap, door blocked by wall, missing floor below stair landing)
- Spiral staircases (verify `append_curved_stairs` 5.6 signature first)
- Arches at diagonal wall angles (Aura's docs flag this as their own known limitation)
- Multi-zone layouts >12 rooms; chunking strategy
- "Replace this placeholder cube with X" semantics (Aura ships this)

### INPAINT — In-painting modal
- ControlNet-inpaint reference panel (`ControlNetLoader` + `ControlNetApplyAdvanced`)
- IPAdapter reference panel (requires Cubiq custom nodes — wheel-cache impact)
- Reference-image drag-drop wiring in the modal (the visual UI shell exists; the reference panel is currently a placeholder)
- Per-image undo / iteration history within the modal

### RIG — Rigging + retargeting
- Quadruped + custom-skeleton rigging (Meshy current API is humanoid-only)
- Custom IK rig builder UI (replace fuzzy auto-map)
- Localhost HTTPS proxy over the staging manifest so generated meshes can flow into Meshy without manual public-URL upload
- Retarget UI panel toggle (currently the script is generated server-side and forwarded via console/exec; no in-panel toggle)

### Cross-cutting
- Compute the SC#1 / Anthropic ToS clearance before flipping the Claude path live (orthogonal to Phase 9 but blocks the wedge story)
- One-click MCP installer for IDE side (Phase 11)

## Hard caps locked into v0

- `MAX_ROOMS_PER_BLOCKOUT = 12` (Aura calls out the same magnitude as their threshold)
- `MAX_DIM_CM = 50_000` (500 m — anything larger is a config error)
- ComfyUI workflow validated against `/object_info` before submit (T-09-03 reuse of T-05-02)
- Mask uploads go through `/upload/image` only (no `/upload/mask` endpoint exists)
- Auto-rig requires Meshy Pro tier; unauthenticated calls map to -32030

## Error codes added (mirror docs/ERROR_CODES.md)

| Code | Message | Source |
|---|---|---|
| -32034 | inpaint failed | inpaint_tools |
| -32035 | input_must_be_url | rigging_tools |
| -32036 | blockout_empty | level_design_tools |
| -32037 | blockout_too_large | level_design_tools |
| -32038 | meshy_rig_failed | rigging_tools |
| -32039 | retarget_render_failed | retarget_tools |
| -32040 | blockout_render_failed | level_design_tools |

## Manual verification deferred

Phase 9 v0 was built without a live UE 5.6 editor in the loop. The
following must be performed on the founder's Windows box before tagging
`v0.2.0-beta`:

1. `RunUAT.bat BuildPlugin` matrix on UE 5.4 / 5.5 / 5.6 / 5.7
2. UE Automation tests `Automation RunTests Nyra`
3. Manual demo: in-painting a portrait through SDXL inpaint
4. Manual demo: auto-rig + retarget UE Mannequin walk anim
5. Manual demo: blockout a 6×8 m room with door + linear staircase

The pytest suite for the new tools (~16 tests) was run hermetically in
the sandbox during plan execution; see `outputs/pytest_phase_1_to_4.txt`
for the run record.

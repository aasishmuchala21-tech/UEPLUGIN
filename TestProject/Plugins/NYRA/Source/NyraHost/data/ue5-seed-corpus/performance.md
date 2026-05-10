# Performance

## stat unit / unitgraph

`stat unit` shows four primary metrics in the viewport:
- **Frame** — total time per frame (target: 16.6ms for 60fps, 33.3ms for 30fps)
- **Game** — game thread time (gameplay code, AI, physics dispatch)
- **Draw** — render thread time (visibility, draw call setup)
- **GPU** — GPU time (actual rendering)

The bottleneck is whichever is highest. If Game is high, profile in Insights with the `cpu` channel. If Draw is high, you have too many draw calls (see `stat scenerendering` for `Mesh Draw Calls`). If GPU is high, profile with RenderDoc or `stat gpu` for per-pass breakdown.

`stat unitgraph` adds a real-time graph overlay so you can see spikes vs steady-state. Useful for catching periodic stalls (GC, async load) that average reads miss.

## Common culprits and the stat that surfaces them

| Symptom | Stat command | Common cause |
|---|---|---|
| Game thread spikes every 10s | `stat gc` | Garbage collection cycle; reduce UObject churn |
| Draw thread heavy | `stat scenerendering` | Too many unique materials / draw calls; look at `Mesh Draw Calls` |
| GPU heavy on translucent | `r.ShaderComplexity 1` | Translucent overdraw; use opaque + masked where possible |
| Stalls on level load | `stat streaming` | Synchronous asset load; convert to async via FStreamableManager |
| Memory growth over time | `stat memory` | UObject leak; run `obj list` and look for unexpected counts |

## Unreal Insights for deeper profiling

`UnrealInsights.exe` (under `Engine/Binaries/Win64/`) attaches to a running editor or game and captures `.utrace` files. Launch the editor with `-tracehost=127.0.0.1 -trace=cpu,gpu,memory,bookmark` to start tracing; Insights connects automatically.

A capture file shows per-frame CPU timeline with named scopes (`SCOPED_NAMED_EVENT` macros in C++). Search for slow scopes via the Timing Insights panel. The `LoadTime` channel surfaces async-load stalls; the `Cpu` channel shows which functions burned how much wall time.

## Reducing draw calls

The cheapest draw call is the one you don't make. Strategies in increasing complexity:

1. **Static Mesh merging** — `Tools > Merge Actors` combines coplanar/coincident static meshes into one. Cuts draw calls but loses per-instance flexibility.
2. **HISM / Foliage** — Hierarchical Instanced Static Mesh batches identical meshes into one draw call regardless of count. Use for grass, rocks, props that share a mesh + material.
3. **Nanite** (UE 5.x) — automatic LOD + cluster culling. Just enable on a mesh asset; works for static geometry only (no skinned meshes pre-5.5). Drops draw call count by 100×+ for high-poly content.
4. **Material atlasing** — collapse N material variants into one master material with parameter-driven branching. Reduces material count = reduces shader-state changes.

## When to profile vs ship

Premature optimization in UE is real but the threshold is different from app dev: Tick code and rendering hot paths matter from day one. Heuristic — if a feature touches more than 50 actors per frame or runs in BeginPlay/Construction Script of a frequently-spawned class, profile it before shipping.

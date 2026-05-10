# Lighting

## Atmosphere stack

Modern UE 5.x outdoor scenes use the four-actor atmosphere stack:

1. **DirectionalLight** — the sun. `Mobility = Movable` for runtime-tweakable; `Mobility = Stationary` for baked-shadow performance with runtime intensity changes; `Mobility = Static` for fully-baked shadows (cheapest, no runtime adjustment).
2. **SkyAtmosphere** — physically-based sky scattering. Drives the colour of the sky based on sun angle. Has `RayleighScatteringScale` and `MieScatteringScale` for atmospheric tuning.
3. **SkyLight** — captures the SkyAtmosphere into an ambient cube map. Set `RealTimeCapture = true` for dynamic time-of-day; set to false and bake for static.
4. **ExponentialHeightFog** — global fog. Has `VolumetricFog = true` toggle for participating-media fog (expensive but cinematic).

For an indoor scene drop the SkyAtmosphere/SkyLight and use Rect Lights or Point Lights with Stationary mobility plus Lumen GI.

## Lumen vs Path Tracing vs Static

- **Lumen** (default UE 5.x) — real-time GI + reflections, scales to large worlds, 60fps target. Quality knob: `r.Lumen.HardwareRayTracing 1` (RT GPU only). Editor camera is the same Lumen path as game, so what you see in editor matches PIE.
- **Static lit** — `Build > Lighting > Build All`. Bakes lightmaps to UVs. Best quality at high cost, but no dynamic objects. Use only for entirely-static scenes.
- **Path Tracing** — the cinematic GPU reference renderer. Open the viewport's view-mode and switch to "Path Tracing". 5–60s per frame. Use for marketing renders, not gameplay.

## Spawning lights from Python

```python
sun = unreal.EditorActorSubsystem.spawn_actor_from_class(
    unreal.DirectionalLight,
    unreal.Vector(0, 0, 10000),
    unreal.Rotator(-45, 30, 0),
)
sky_atm = unreal.EditorActorSubsystem.spawn_actor_from_class(
    unreal.SkyAtmosphere, unreal.Vector(), unreal.Rotator()
)
sky_light = unreal.EditorActorSubsystem.spawn_actor_from_class(
    unreal.SkyLight, unreal.Vector(), unreal.Rotator()
)
sky_light_cmp = sky_light.get_component_by_class(unreal.SkyLightComponent)
sky_light_cmp.set_editor_property("real_time_capture", True)
fog = unreal.EditorActorSubsystem.spawn_actor_from_class(
    unreal.ExponentialHeightFog, unreal.Vector(), unreal.Rotator()
)
```

The `get_component_by_class` pattern is the canonical Python access path for component properties. Direct setattr on the actor doesn't reach component-owned properties.

## Light intensity reference values

Photometric (lux/lumens) intensity is the modern default. Useful starting values:
- Sunlight at noon: ~120,000 lux
- Cloudy daylight: ~10,000 lux
- Indoor office: 500 lux
- Candlelight: ~10 lux

Set via `light.set_intensity(120000)` on the DirectionalLight. SkyAtmosphere drives most of the sky color so the SkyLight is usually a low intensity (~1) — boosting it doubles the contribution from both stack actors and over-brightens.

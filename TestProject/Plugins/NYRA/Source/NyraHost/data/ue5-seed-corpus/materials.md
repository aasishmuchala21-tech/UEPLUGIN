# Materials

## Material Instance Constants vs Dynamic

A Material Instance Constant (MIC) is an editor-time asset deriving from a parent Material; parameters are baked at cook. A Material Instance Dynamic (MID) is created at runtime via `UMaterialInstanceDynamic::Create(ParentMaterial, Outer)` and lets you mutate scalar/vector/texture parameters per-frame.

Cost note: each MID is its own draw call — don't create one per actor unless the parameter actually varies. If 50 actors share a material instance, give them 1 MIC, not 50 MIDs.

## Reading and writing material parameters

From C++:
- `UMaterialInstanceConstant::SetScalarParameterValueEditorOnly(ParamName, Value)` — only available in editor builds.
- `UMaterialInstanceConstant::GetScalarParameterValue(ParamName)` — works at runtime via the parent material's parameter info.
- `UMaterialInstanceDynamic::SetScalarParameterValue(ParamName, Value)` — runtime mutation.

From Python (editor):
- `unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mic, "Roughness", 0.5)`
- `unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mic, "Roughness")`

Texture parameters use `set_material_instance_texture_parameter_value`. Vector parameters take `unreal.LinearColor(R,G,B,A)`.

## Creating a Material Instance Constant programmatically

```python
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
factory = unreal.MaterialInstanceConstantFactoryNew()
factory.initial_parent = unreal.load_asset("/Game/Materials/M_Hero")
mic = asset_tools.create_asset(
    asset_name="MIC_Hero_Red",
    package_path="/Game/Materials/Instances",
    asset_class=unreal.MaterialInstanceConstant,
    factory=factory,
)
unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(
    mic, "Roughness", 0.4
)
unreal.EditorAssetLibrary.save_loaded_asset(mic)
```

`save_loaded_asset` is critical — without it the MIC stays in memory but never persists to disk.

## Applying a material to an actor

`UPrimitiveComponent::SetMaterial(ElementIndex, Material)` sets the material on a specific element slot. Element indices match the material slots defined on the source mesh; out-of-range indices are silently ignored, which is a frequent source of "I called SetMaterial but nothing changed" bugs.

For a StaticMeshActor, get the StaticMeshComponent and call `SetMaterial`. For a SkeletalMeshActor, the SkeletalMeshComponent uses the same API.

## Master material organization pattern

The Epic-recommended structure: one Master Material per shading model (Opaque, Translucent, Subsurface, etc.) with parameters for the variations you need. Each variation becomes a MIC inheriting from that Master. This minimizes shader compile counts (a single master compiles once; 100 MICs reuse the compiled shader) and lets you batch-update look across the project by tweaking the master.

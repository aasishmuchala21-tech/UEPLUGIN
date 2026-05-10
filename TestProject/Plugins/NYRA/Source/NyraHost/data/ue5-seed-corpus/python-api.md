# UE Python API patterns

## Editor subsystems are the modern access layer

UE 5.0 deprecated `EditorLevelLibrary` and friends in favour of subsystem singletons. The canonical access pattern:

```python
actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
asset_subsystem = unreal.get_editor_subsystem(unreal.EditorAssetSubsystem)
level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
```

The shim functions (`unreal.EditorLevelLibrary.spawn_actor_from_class`, etc.) still work but route through the subsystem under the hood. New code should call subsystems directly.

## Asset Registry direct enumeration

For listing assets, the Asset Registry is dramatically faster than per-asset `find_asset_data` round-trips:

```python
ar = unreal.AssetRegistryHelpers.get_asset_registry()
assets = ar.get_assets_by_path("/Game", recursive=True)
for ad in assets:
    print(ad.package_name, ad.asset_name)
```

A 50,000-asset project enumerates in <100ms via this path; the older `EditorAssetLibrary.list_assets` + per-asset `find_asset_data` loop takes 5+ seconds on the same project.

## Asset class path (5.1+) vs asset class (older)

UE 5.1 replaced `FAssetData::AssetClass` (FName) with `AssetClassPath` (FTopLevelAssetPath). The old API still works as a deprecation alias but emits a warning. Modern code:

```python
class_path = ad.asset_class_path  # 5.1+
short_name = class_path.get_asset_name().to_string()  # e.g. "StaticMesh"
```

## Loading assets

`unreal.load_asset("/Game/Path/AssetName")` returns the in-memory UObject. The `.AssetName` suffix is optional in UE 5.x — the resolver appends it if needed. For class assets (Blueprints), use `unreal.load_class("/Game/BP_Hero.BP_Hero_C")` — note the `_C` suffix for the generated class.

## The `unreal` module is editor-only

Importing `unreal` outside the UE Python environment raises ImportError. NyraHost tools that touch UE handle this with:

```python
try:
    import unreal
except ImportError:
    unreal = None
    HAS_UNREAL = False
else:
    HAS_UNREAL = True
```

This pattern lets the same module load in pytest (no UE editor) and in production (live editor) without separate code paths. Tests skip live-UE branches via `pytestmark = pytest.mark.skipif(not HAS_UNREAL, ...)`.

## EditorAssetLibrary.save_loaded_asset

Programmatic edits to assets stay in memory until `save_loaded_asset(asset)` writes to disk. Forgetting this call is the most common reason "my Python changes don't show after editor restart." The EditorAssetSubsystem version is `save_asset(asset_path)` (path, not object).

For batch-save: `unreal.EditorAssetLibrary.save_directory("/Game/MyFolder", recursive=True)`.

## Slow-task progress bar

For long-running Python operations:

```python
with unreal.ScopedSlowTask(100, "Importing meshes...") as task:
    task.make_dialog(True)  # show cancel button
    for i, mesh in enumerate(meshes):
        if task.should_cancel():
            break
        task.enter_progress_frame(1, f"Mesh {i+1}/{len(meshes)}")
        process_mesh(mesh)
```

This surfaces a modal progress dialog with a working Cancel button. For background work that shouldn't block the editor, use `unreal.SystemLibrary.execute_console_command(...)` instead and read results from log.

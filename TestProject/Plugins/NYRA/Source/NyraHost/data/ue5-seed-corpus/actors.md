# Actors

## Spawning actors at runtime

Use `UWorld::SpawnActor<T>(Class, Location, Rotation)` to spawn an actor at runtime. The world reference is the canonical place to spawn — never bypass it. The `FActorSpawnParameters` struct controls collision handling, owner, instigator, and naming. The default `SpawnCollisionHandlingOverride` is `Undefined` which falls back to the actor class's `SpawnCollisionHandlingMethod`. Set it to `AlwaysSpawn` if you need to ignore collision, or `AdjustIfPossibleButAlwaysSpawn` for tolerant placement.

In editor scripting (Python), use `unreal.EditorActorSubsystem.spawn_actor_from_class(actor_class, location, rotation)`. The 5.4+ API replaced the older `EditorLevelLibrary.spawn_actor_from_class` which still works as a thin shim. For actor by asset path (StaticMesh, etc.), use `unreal.EditorActorSubsystem.spawn_actor_from_object(asset, location, rotation)`.

## Actor transforms

`AActor::GetActorTransform()` returns world-space transform. `SetActorTransform(NewTransform, bSweep, OutSweepHitResult, ETeleportType::ResetPhysics)` is the most-explicit setter — `bSweep` controls whether the actor sweeps for collisions during the move. `ETeleportType::None` updates physics; `TeleportPhysics` resets velocity. For attaching: `AttachToComponent(Parent, FAttachmentTransformRules::KeepWorldTransform, SocketName)` — the rules struct controls whether to keep relative or absolute transforms.

## Actor lifecycle

`BeginPlay` fires once when the actor enters play. `EndPlay(EndPlayReason)` fires when removed (Destroyed, LevelTransition, Quit, RemovedFromWorld, etc.). `Tick(DeltaTime)` runs every frame if `PrimaryActorTick.bCanEverTick = true`. `BeginDestroy` is the GC notification — too late for game logic, only for releasing C++ resources.

## Editor actors vs runtime actors

`UWorld::IsEditorWorld()` distinguishes editor preview from PIE/standalone. The `unreal.EditorAssetLibrary` and `unreal.EditorLevelLibrary` Python APIs only work against the editor world. Spawning at runtime via Python during PIE requires `unreal.EditorActorSubsystem.is_pie_active()` first to confirm the world type.

# Blueprints

## Compile errors and the Blueprint Compilation Manager

Blueprint compile errors flow through `FKismetCompilerContext` and surface in the `BlueprintLog` Message Log listing. The most common errors:

- **Unknown member 'X'** — a property name was renamed or its owning class changed. Check the node's target pin type. Use `FBlueprintEditorUtils::ReplaceVariableReferences(Blueprint, OldName, NewName)` for a safe rename.
- **Cast to X failed** — the source object isn't of the target type. The cast node returns null on failure, which propagates as a null-ref downstream. Always pair a Cast with `IsValid()` upstream.
- **Variable 'X' not found** — a soft variable reference outlived the variable. Open the Blueprint, reload, and the dangling reference will surface for cleanup.
- **Cannot connect X to Y** — pin type mismatch. UE inserts implicit conversions only for scalar promotions (Float ⇄ Double, Int ⇄ Float). For type changes, use a conversion node like `Float to Int` or `ToString`.

Recompile from Python with `unreal.KismetEditorUtilities.compile_blueprint(bp)`. The legacy `BlueprintEditorUtilityLibrary.recompileBlueprint` does NOT exist in UE 5.4+ — that API path was removed.

## Read / write Blueprint graph nodes

The `unreal.BlueprintEditorLibrary` (5.5+) exposes graph manipulation: `add_node`, `remove_node`, `get_nodes_in_graph`, `connect_pins`. Earlier versions need the C++ `UEdGraphSchema_K2` interface bound through a custom UCLASS helper. For NYRA's tool catalog, see `nyra_blueprint_read` and `nyra_blueprint_write`.

Pin connections require pin direction match (one input, one output) and compatible types. Using `K2Schema->TryCreateConnection(PinA, PinB)` validates and links; failure modes return an FString describing the conflict.

## Pure functions vs imperative

A pure function has no execution pin and is re-evaluated every time its output is read. Mark with `BlueprintPure` UFUNCTION specifier. Pure functions cannot reference Timelines, Latent Actions, or Tick — those have side effects. If a Pure function shows that error in compile, mark it `BlueprintCallable` instead and accept the explicit exec wire.

## Blueprint vs C++ tradeoff

Blueprints are 5–10× slower than equivalent C++ at runtime per Epic's own perf docs. For Tick-heavy code (animation update, AI controllers), keep the loop in C++ and call into Blueprint for one-shot events. Use BlueprintNativeEvent if you need both — C++ defines the default body, Blueprint can override.

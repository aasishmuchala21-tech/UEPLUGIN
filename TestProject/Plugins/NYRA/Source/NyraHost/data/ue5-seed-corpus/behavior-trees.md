# Behavior Trees

## What a Behavior Tree is

A Behavior Tree is a tree-structured AI controller. The AIController evaluates the tree top-down each tick, descending through composites (Selector, Sequence, SimpleParallel) into tasks (atomic AI actions like MoveTo, PlayAnimation). Decorators gate composites and tasks based on Blackboard state.

## The four composite types

- **Selector** (priority): runs children left-to-right; returns success on first child that succeeds. Used for "try plan A, fall back to plan B."
- **Sequence**: runs children left-to-right; returns success only if ALL children succeed. Stops at the first failure.
- **SimpleParallel**: one main task plus a background subtree. The main task drives termination; the background runs alongside.
- **(no Random composite by default; use a Decorator with Random Score Picker if needed.)**

## Tasks vs Decorators vs Services

- **Task** (BTTaskNode): the atomic unit of work. `MoveTo`, `Wait`, `RunBehavior` (subtree), or your custom `BTT_*` C++ class.
- **Decorator** (BTDecorator): a guard. Common decorators: `Blackboard` (run only if key value matches), `IsAtLocation`, `Cooldown`, `ForceSuccess`. Decorators can also abort a running subtree if conditions change.
- **Service** (BTService): runs every N seconds while its parent composite is active. Used for recurring updates like `KeepFaceTarget` or `UpdateBlackboard`.

## Blackboard keys

Blackboards are typed key-value stores that the BT reads/writes. Key types: `Bool`, `Int`, `Float`, `String`, `Vector`, `Object`, `Class`, `Enum`, `Name`, `Rotator`. Set programmatically via `UBlackboardComponent::SetValue<T>(KeyID, Value)` from C++; from Python use `unreal.BlackboardComponent.set_value_*(key_name, value)` variants.

## Author a BT from Python (UE 5.4–5.7)

```python
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
bt = asset_tools.create_asset(
    asset_name="BT_Hero",
    package_path="/Game/AI",
    asset_class=unreal.BehaviorTree,
    factory=unreal.BehaviorTreeFactory(),
)
bb = asset_tools.create_asset(
    asset_name="BB_Hero",
    package_path="/Game/AI",
    asset_class=unreal.BlackboardData,
    factory=unreal.BlackboardDataFactory(),
)
bt.blackboard_asset = bb
```

Adding composite/task/decorator nodes from Python isn't directly exposed in stock UE 5.x — it requires a UCLASS C++ helper that calls into `UBehaviorTreeGraphNode::CreateAddedNode`. NYRA's `UNyraBTHelper` provides this surface as `unreal.NyraBTHelper.add_composite_node(bt, "BTComposite_Sequence", parent, position)`.

## Common BT mistakes

- **Setting BlackboardKey on a Decorator that hasn't been added to the right child.** Decorators apply to the composite or task they're attached to. If a guard isn't firing, check Tree View in the BT editor to confirm attachment.
- **Run Behavior loops without a terminating Service** to update conditions. Without something modifying the Blackboard, a Selector keeps trying child A forever.
- **Ticking expensive logic in a Service every 0.1s.** Services run on a timer; a 0.1s interval at 60fps means 6× per second, which is fine for distance checks but ruinous for raycasts.

## When to use BT vs State Tree (UE 5.5+)

State Tree is the modern alternative — better suited for hierarchical state machines, visual transitions, and explicit data flow. BT remains the right choice for goal-oriented AI with frequent priority shifts (Selector-heavy trees). New project rule of thumb: if you find yourself writing many `ForceSuccess` decorators or simulating states via Blackboard ints, switch to State Tree.

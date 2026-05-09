---
phase: "06"
plan: "06-01"
type: execute
wave: 1
depends_on: []
files_modified:
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_llm_parser.py
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingPanel.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingSelector.cpp
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingPanel.h
  - TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingSelector.h
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_lighting_tools.py
  - TestProject/Plugins/NYRA/Source/NyraHost/tests/test_scene_llm_parser.py
autonomous: true
requirements:
  - SCENE-01
user_setup: []
must_haves:
  truths:
    - "User can type 'golden hour' in chat and get a configured directional light + SkyAtmosphere + ExponentialHeightFog in the UE level"
    - "User can attach a reference image and click 'Match Image Mood' to get lighting parameters derived from the image"
    - "Lighting preset cards in SNyraLightingSelector are hoverable for real-time dry-run preview in the UE viewport"
    - "SCENE-01 requirement is fully addressed: directional/point/spot/rect/sky lights + SkyAtmosphere + VolumetricCloud + ExponentialHeightFog + PostProcessVolume + exposure curves"
  artifacts:
    - path: "NyraHost/src/nyrahost/tools/lighting_tools.py"
      provides: "MCP tool: nyra_lighting_authoring — NL prompt + image-ref → UE lighting config"
      min_lines: 100
    - path: "NyraHost/src/nyrahost/tools/scene_llm_parser.py"
      provides: "LLM-powered scene parameter parser (lighting section)"
      min_lines: 60
    - path: "NyraEditor/Private/Panel/SNyraLightingPanel.cpp"
      provides: "SCENE-01 Slate panel hosting SNyraLightingSelector + 'Match Image Mood' button"
      min_lines: 80
    - path: "NyraEditor/Private/Panel/SNyraLightingSelector.cpp"
      provides: "SNyraLightingSelector horizontal preset card widget with hover-to-preview"
    - path: "NyraEditor/Public/Panel/SNyraLightingPanel.h"
      provides: "C++ header for SNyraLightingPanel"
    - path: "NyraEditor/Public/Panel/SNyraLightingSelector.h"
      provides: "C++ header for SNyraLightingSelector"
  key_links:
    - from: "NyraHost/lighting_tools.py"
      to: "NyraHost/tools/actor_tools.py"
      via: "nyra_actor_spawn for light actors, nyra_actor_transform for light config"
      pattern: "actor_spawn|actor_transform"
    - from: "NyraHost/lighting_tools.py"
      to: "NyraEditor/SNyraLightingPanel.cpp"
      via: "WS notification to panel on dry-run preview trigger"
      pattern: "dry_run_preview|ws_notification"
    - from: "SNyraLightingSelector.cpp"
      to: "lighting_tools.py"
      via: "IPC message from Slate hover event to NyraHost nl_to_lighting()"
      pattern: "ws.*send|SendWsMessage"
---

<objective>
Implement SCENE-01 Lighting Authoring: NL-to-lighting parser, UE lighting actuator (calls Tool Catalog from Phase 4), SNyraLightingSelector UI component per 06-UI-SPEC.md, real-time dry-run preview on preset hover, and "Match Image Mood" button that reads a reference image and calls LLM to extract lighting parameters.
</objective>

<execution_context>
@$HOME/.claude/get-shit-done/workflows/execute-plan.md
@$HOME/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-UI-SPEC.md
@TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraChatPanel.cpp
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/actor_tools.py
@TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/base.py
</context>

<interfaces>
<!-- Key types and contracts the executor needs. Extracted from codebase. -->

From nyrahost/tools/base.py:
```python
@dataclass
class NyraToolResult:
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    warnings: list[str] = field(default_factory=list)
    def to_dict(self) -> dict: ...
    @classmethod
    def ok(cls, data: dict) -> "NyraToolResult": ...
    @classmethod
    def err(cls, message: str) -> "NyraToolResult": ...

class NyraTool:
    name: str = ""
    description: str = ""
    parameters: dict = {}
    def execute(self, params: dict) -> NyraToolResult: ...
```

From nyrahost/tools/actor_tools.py (lines 29-74, ActorSpawnTool pattern):
```python
class ActorSpawnTool(NyraTool):
    name = "nyra_actor_spawn"
    def execute(self, params: dict) -> NyraToolResult:
        editor_level_lib = unreal.EditorLevelLibrary
        actor_class = unreal.UObject.load_system_class(params["class_name"])
        transform = unreal.Transform(unreal.Vector(...), unreal.Rotator(...), unreal.Vector(1,1,1))
        actor = editor_level_lib.spawn_actor_from_class(actor_class, transform)
        return NyraToolResult(data={"actor_name": actor.get_name(), "actor_path": actor.get_path_name(), "guid": str(actor.get_actor_guid())})
```

From SNyraChatPanel.cpp (existing Slate panel pattern):
- Panel lives in `NyraEditor/Private/Panel/`
- Uses `SAssignNew` for widget assignment
- WS communication via `FNyraWsClient::SendMessage` (pattern from FNyraWsClient.cpp)
- Design tokens applied via `FLinearColor(0.02f, 0.02f, 0.03f, 1.f)` for dominant `#050507`
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: scene_llm_parser.py — LLM-powered lighting parameter extractor</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/scene_llm_parser.py</files>
  <action>
Create `nyrahost/tools/scene_llm_parser.py` implementing the `LightingLLMParser` class.

**LightingLLMParser** takes either (a) a natural-language string or (b) a reference image path and calls Claude (via `NyraHost` backend router) to extract structured lighting parameters. The output is a dict that `LightingAuthoringTool.execute()` consumes.

**Interface:**
```python
class LightingLLMParser:
    def __init__(self, backend_router=None):
        self.router = backend_router  # injected for testability

    async def parse_from_text(self, nl_prompt: str) -> LightingParams:
        """Parse 'golden hour', 'harsh overhead', 'moody blue', etc."""
        # Calls Claude with system prompt asking for structured lighting JSON
        # System prompt specifies the exact JSON schema expected
        # Returns LightingParams dataclass

    async def parse_from_image(self, image_path: str) -> LightingParams:
        """Call Claude vision on reference image to extract lighting mood."""
        # Sends image to Claude Opus 4.7 with prompt like:
        # "Describe the lighting in this image: key light direction, color temperature,
        # intensity, fill light presence, atmosphere (fog, haze), sky/sun position.
        # Return a JSON object with these fields..."
        # Claude returns JSON -> parse -> return LightingParams
```

**LightingParams dataclass:**
```python
@dataclass
class LightingParams:
    # Light configuration
    primary_light_type: str         # "directional" | "spot" | "point" | "rect" | "sky"
    primary_intensity: float         # EV or Lux value
    primary_color: tuple[float,float,float]  # RGB 0-1
    primary_direction: tuple[float,float,float]  # rotation (pitch,yaw,roll) in degrees
    primary_temperature: float       # Kelvin (for color)
    use_shadow: bool = True
    shadow_cascades: int = 4

    # Fill / ambient
    fill_light_type: str = ""       # "" means no fill
    fill_intensity: float = 0.0
    fill_color: tuple[float,float,float] = (0.5, 0.5, 0.5)

    # Atmosphere
    use_sky_atmosphere: bool = False
    sky_atmosphere_composition: str = "earth"  # "earth" | "urban" | "clear"

    use_volumetric_cloud: bool = False
    cloud_coverage: float = 0.5     # 0-1

    use_exponential_height_fog: bool = False
    fog_density: float = 0.02
    fog_height_falloff: float = 0.2
    fog_color: tuple[float,float,float] = (0.8, 0.85, 1.0)  # cool blue default

    use_volumetric_fog: bool = False
    volumetric_fog_density: float = 0.1

    # Post-process
    use_post_process: bool = False
    exposure_compensation: float = 0.0  # EV
    contrast: float = 1.0
    color_saturation: float = 1.0

    # Metadata
    prompt: str = ""               # original user prompt
    mood_tags: list[str] = []      # ["warm", "high-contrast", "soft fill"]
    confidence: float = 0.0         # 0-1, how confident the LLM is
```

**LLM system prompt:**
```
You are NYRA's lighting analysis engine. Given a scene description or reference image,
output a JSON object describing the lighting setup.

Schema:
{
  "primary_light_type": "directional|spot|point|rect|sky",
  "primary_intensity": float,       // 0.0 to 10.0 (normalized)
  "primary_color": [r, g, b],       // 0-1 float RGB
  "primary_direction_deg": [pitch, yaw, roll],  // degrees
  "primary_temperature_k": float,   // 1000-20000 Kelvin
  "use_shadow": bool,
  "fill_light_type": "",
  "fill_intensity": float,
  "use_sky_atmosphere": bool,
  "sky_composition": "earth|urban|clear",
  "use_volumetric_cloud": bool,
  "cloud_coverage": float,
  "use_exponential_height_fog": bool,
  "fog_density": float,
  "fog_color": [r, g, b],
  "use_post_process": bool,
  "exposure_compensation": float,
  "mood_tags": ["warm", "high-contrast", ...],
  "confidence": float
}

Only output JSON. Do not add explanation.
```

**Key behaviors:**
- `parse_from_text` and `parse_from_image` are async (call Claude Opus over HTTP via backend router)
- Falls back to a simple rule-based parser if the backend is unavailable (offline mode via Gemma)
- Rule-based fallback: "golden hour" -> directional light 45deg, warm orange (0.9, 0.6, 0.3), SkyAtmosphere on; "harsh overhead" -> directional light pitch=-90, intensity=2.0, no fill; "moody blue" -> point light cool blue, ExponentialHeightFog, no sky atmosphere
- Import `from nyrahost.tools.base import NyraToolResult` — NOT used here but other tools import it
- Logging: log at INFO for parse success, WARNING for fallback activation, ERROR for complete failure
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_scene_llm_parser.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>LightingLLMParser implemented with parse_from_text and parse_from_image; LightingParams dataclass covers all SCENE-01 fields; rule-based fallback covers 5 presets</done>
</task>

<task type="auto">
  <name>Task 2: lighting_tools.py — nyra_lighting_authoring MCP tool</name>
  <files>TestProject/Plugins/NYRA/Source/NyraHost/src/nyrahost/tools/lighting_tools.py</files>
  <action>
Create `nyrahost/tools/lighting_tools.py` implementing `LightingAuthoringTool` and `LightingDryRunTool`.

**LightingAuthoringTool (nyra_lighting_authoring):**

```python
class LightingAuthoringTool(NyraTool):
    name = "nyra_lighting_authoring"
    description = (
        "Configure scene lighting in the current UE level: directional/point/spot/rect/sky lights, "
        "SkyAtmosphere, VolumetricCloud, ExponentialHeightFog, PostProcessVolume, and exposure curves. "
        "Use 'Match from Image' mode to have Claude analyze a reference image and derive lighting parameters. "
        "Use 'Apply Lighting' after previewing in the viewport."
    )
    parameters = {
        "type": "object",
        "properties": {
            "nl_prompt": {
                "type": "string",
                "description": "Natural-language lighting description, e.g. 'golden hour', 'harsh overhead studio', 'overcast forest'"
            },
            "reference_image_path": {
                "type": "string",
                "description": "Absolute path to a reference image for 'Match Image Mood' mode. If provided, nl_prompt is ignored."
            },
            "apply": {
                "type": "boolean",
                "default": True,
                "description": "If False, performs a dry-run preview (viewport highlight only, no actors placed)."
            },
            "preset_name": {
                "type": "string",
                "description": "Named lighting preset to use directly: 'golden_hour', 'harsh_overhead', 'moody_blue', 'studio_fill', 'dawn'"
            }
        }
    }

    def execute(self, params: dict) -> NyraToolResult:
        import unreal

        parser = LightingLLMParser(backend_router=self._router)

        # 1. Get LightingParams (from NL, image, or preset)
        if params.get("reference_image_path"):
            params_lit = asyncio.run(parser.parse_from_image(params["reference_image_path"]))
        elif params.get("preset_name"):
            params_lit = self._preset_to_params(params["preset_name"])
        elif params.get("nl_prompt"):
            params_lit = asyncio.run(parser.parse_from_text(params["nl_prompt"]))
        else:
            return NyraToolResult.err("[-32030] Either nl_prompt, reference_image_path, or preset_name must be provided.")

        # 2. Apply lighting if apply=True
        if params.get("apply", True):
            actors_placed = self._apply_lighting_params(params_lit)
            log.info("lighting_applied", actors=actors_placed, mood_tags=params_lit.mood_tags)
            return NyraToolResult.ok({
                "actors_placed": actors_placed,
                "mood_tags": params_lit.mood_tags,
                "primary_light_type": params_lit.primary_light_type,
                "exposure_compensation": params_lit.exposure_compensation,
                "message": f"Lighting applied: {params_lit.primary_light_type} with mood {params_lit.mood_tags}"
            })
        else:
            # Dry-run preview: send notification to Slate panel, don't place actors
            self._send_dry_run_notification(params_lit)
            return NyraToolResult.ok({
                "dry_run": True,
                "mood_tags": params_lit.mood_tags,
                "message": "Dry-run preview active. Click 'Apply Lighting' to commit."
            })
```

**LightingDryRunTool (nyra_lighting_dry_run_preview):**
```python
class LightingDryRunTool(NyraTool):
    name = "nyra_lighting_dry_run_preview"
    description = "Preview a lighting configuration in the UE viewport without placing actors. Triggered by hovering a preset card in SNyraLightingSelector."
    parameters = {
        "type": "object",
        "properties": {
            "preset_name": {"type": "string"},
            "lighting_params_json": {"type": "string", "description": "JSON string of LightingParams if custom (not from preset)"}
        }
    }

    def execute(self, params: dict) -> NyraToolResult:
        # Send dry-run message over WS to SNyraLightingPanel
        # Panel highlights the preview actors in the viewport (existing temp actors)
        # Does NOT place permanent actors
        self._send_dry_run_notification(...)
        return NyraToolResult.ok({"dry_run": True})
```

**`_apply_lighting_params` helper (inside LightingAuthoringTool):**
```python
def _apply_lighting_params(self, lp: LightingParams) -> list[dict]:
    """Apply LightingParams to UE level via Tool Catalog (Phase 4 actor tools)."""
    placed = []

    # Primary light
    light_class = {
        "directional": "/Script/Engine.DirectionalLight",
        "spot": "/Script/Engine.SpotLight",
        "point": "/Script/Engine.PointLight",
        "rect": "/Script/Engine.RectLight",
    }.get(lp.primary_light_type, "/Script/Engine.DirectionalLight")

    # Spawn primary light via nyra_actor_spawn
    spawn_result = self._spawn_actor(
        class_name=light_class,
        label=f"NYRA_Primary_{lp.primary_light_type}",
        transform=self._make_transform(lp.primary_direction, lp.primary_intensity)
    )
    placed.append(spawn_result)

    # Apply light intensity/color via nyra_actor_transform or Unreal Python API
    self._configure_light_actor(spawn_result["actor_path"], lp)

    # SkyAtmosphere
    if lp.use_sky_atmosphere:
        sky = self._spawn_actor(
            class_name="/Script/Engine.SkyAtmosphere",
            label="NYRA_SkyAtmosphere",
            location=(0, 0, 0)
        )
        placed.append(sky)

    # VolumetricCloud
    if lp.use_volumetric_cloud:
        cloud = self._spawn_actor(
            class_name="/Script/Engine.VolumetricCloud",
            label="NYRA_VolumetricCloud",
            location=(0, 0, 0)
        )
        placed.append(cloud)

    # ExponentialHeightFog
    if lp.use_exponential_height_fog:
        fog = self._spawn_actor(
            class_name="/Script/Engine.ExponentialHeightFog",
            label="NYRA_ExpHeightFog",
            location=(0, 0, 0)
        )
        placed.append(fog)
        # Configure fog params via unreal API
        self._configure_fog(fog["actor_path"], lp)

    # PostProcessVolume ( unbound, infinite )
    if lp.use_post_process:
        ppv = self._spawn_actor(
            class_name="/Script/Engine.PostProcessVolume",
            label="NYRA_PostProcessVolume"
        )
        placed.append(ppv)
        self._configure_post_process(ppv["actor_path"], lp)

    return placed

def _preset_to_params(self, preset_name: str) -> LightingParams:
    """Hardcoded preset to LightingParams mapping."""
    presets = {
        "golden_hour": LightingParams(
            primary_light_type="directional",
            primary_intensity=1.5,
            primary_color=(0.95, 0.65, 0.3),
            primary_direction=(45, -30, 0),
            primary_temperature_k=3500,
            use_shadow=True,
            use_sky_atmosphere=True,
            use_exponential_height_fog=True,
            fog_density=0.01,
            fog_color=(0.8, 0.7, 0.6),
            use_post_process=True,
            exposure_compensation=0.5,
            mood_tags=["warm", "low sun", "soft shadow"]
        ),
        "harsh_overhead": LightingParams(
            primary_light_type="directional",
            primary_intensity=2.5,
            primary_color=(1.0, 1.0, 1.0),
            primary_direction=(-90, 0, 0),
            primary_temperature_k=5500,
            use_shadow=True,
            shadow_cascades=4,
            use_exponential_height_fog=False,
            mood_tags=["harsh", "overhead", "high-contrast"]
        ),
        "moody_blue": LightingParams(
            primary_light_type="point",
            primary_intensity=0.5,
            primary_color=(0.4, 0.5, 0.9),
            primary_direction=(0, 0, 0),
            use_shadow=False,
            use_exponential_height_fog=True,
            fog_density=0.04,
            fog_color=(0.5, 0.6, 0.9),
            use_post_process=True,
            exposure_compensation=-1.5,
            mood_tags=["cool", "moody", "low-key"]
        ),
        "studio_fill": LightingParams(
            primary_light_type="rect",
            primary_intensity=1.0,
            primary_color=(1.0, 0.95, 0.9),
            primary_direction=(0, 0, 0),
            fill_light_type="point",
            fill_intensity=0.3,
            fill_color=(0.6, 0.7, 1.0),
            use_shadow=True,
            mood_tags=["neutral", "soft fill", "studio"]
        ),
        "dawn": LightingParams(
            primary_light_type="directional",
            primary_intensity=0.8,
            primary_color=(0.7, 0.5, 0.4),
            primary_direction=(15, -60, 0),
            primary_temperature_k=2800,
            use_shadow=True,
            use_sky_atmosphere=True,
            use_exponential_height_fog=True,
            fog_density=0.03,
            fog_color=(0.6, 0.5, 0.5),
            use_post_process=True,
            exposure_compensation=0.3,
            mood_tags=["dawn", "pink", "diffuse"]
        )
    }
    return presets.get(preset_name, presets["golden_hour"])
```

**Implement `_spawn_actor`, `_configure_light_actor`, `_configure_fog`, `_configure_post_process` as helper methods.**

`_spawn_actor` calls the Unreal `unreal` Python module:
```python
def _spawn_actor(self, class_name: str, label: str, transform: dict) -> dict:
    actor_class = unreal.UObject.load_system_class(class_name)
    loc = transform.get("location", {"x": 0, "y": 0, "z": 0})
    rot = transform.get("rotation", {"pitch": 0, "yaw": 0, "roll": 0})
    unreal_transform = unreal.Transform(
        unreal.Vector(loc["x"], loc["y"], loc["z"]),
        unreal.Rotator(rot["pitch"], rot["yaw"], rot["roll"]),
        unreal.Vector(1, 1, 1)
    )
    actor = unreal.EditorLevelLibrary.spawn_actor_from_class(actor_class, unreal_transform)
    actor.set_actor_label(label)
    return {"actor_name": actor.get_name(), "actor_path": actor.get_path_name(), "guid": str(actor.get_actor_guid())}
```

`_configure_light_actor` uses `unreal.EditorLevelLibrary.get_actor_reference()` then sets light component properties via Python API.

`_send_dry_run_notification` sends a WebSocket notification to the Slate panel (pattern: `FNyraWsClient::SendMessage`).

**Threat mitigations:**
- T-06-01: Image path passed to `parse_from_image` is validated with `Path.exists()` before being used
- T-06-02: All actor labels prefixed with `NYRA_` to allow identification for deletion/undo
  </action>
  <verify>
    <automated>cd /Users/aasish/CLAUDE\ PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraHost && python -m pytest tests/test_lighting_tools.py -x -q 2>&1 | tail -20</automated>
  </verify>
  <done>nyra_lighting_authoring accepts nl_prompt/image_path/preset_name; preset mapping covers 5 presets; dry-run sends WS notification without placing actors</done>
</task>

<task type="auto">
  <name>Task 3: SNyraLightingSelector.cpp + SNyraLightingPanel.cpp (Slate UI)</name>
  <files>TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingSelector.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Private/Panel/SNyraLightingPanel.cpp, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingSelector.h, TestProject/Plugins/NYRA/Source/NyraEditor/Public/Panel/SNyraLightingPanel.h</files>
  <action>
Create the two Slate components per 06-UI-SPEC.md.

**SNyraLightingSelector.h:**
```cpp
#pragma once
#include "Widgets/SCompoundWidget.h"
#include "SNyraLightingSelector.generated.h"

struct FLightingPresetCard {
    FString Name;         // "Golden Hour"
    FString PresetKey;    // "golden_hour"
    FLinearColor Accent;  // #C6BFFF
    bool bCustom;
};

class SNyraLightingSelector : public SCompoundWidget {
public:
    SLATE_BEGIN_ARGS(SNyraLightingSelector) {}
    SLATE_EVENT(FSimpleDelegate, OnPresetSelected)
    SLATE_EVENT(FSimpleDelegate, OnDryRunHover)
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);

    // Preset cards: "Golden Hour", "Harsh Overhead", "Moody Blue", "Studio Fill", "Dawn", "Matched from Image"
    // Horizontal scroll, 80x60px cards, hover triggers dry-run preview (OnDryRunHover delegate)
    // Selected state: accent border #C6BFFF 1px
    // Accent reserved-for: active card border only (per UI-SPEC)
    // Font: Inter 14px regular body; Label role uses 0.15em letter-spacing (uppercase, 11px)

    FReply OnCardClicked(const FString& PresetKey);
    FReply OnCardHovered(const FString& PresetKey);
    FReply OnCardUnhovered();

private:
    TArray<FLightingPresetCard> Presets;
    FString SelectedPreset;
    TSharedPtr<STextBlock> SelectedLabel;
    TSharedPtr<SScrollBox> ScrollBox;

    void BuildPresetCards();
    FLinearColor GetCardBorderColor(const FLightingPresetCard& Card) const;
    float GetCardBorderOpacity(const FLightingPresetCard& Card) const;
};
```

**SNyraLightingSelector.cpp — Construct():**
```cpp
void SNyraLightingSelector::Construct(const FArguments& InArgs) {
    // Horizontal scroll box (SScrollBox::Orient_Horizontal)
    // Direction = Slide_LEFT_TO_RIGHT
    // Padding = FMargin(16, 8)

    // Preset cards: SButton with SImage (icon) + STextBlock (label)
    // Card style: FButtonStyle with NormalTint=FLinearColor(0.05,0.05,0.08,1), HoveredTint=FLinearColor(0.08,0.07,0.12,1)
    // Border: 1px solid, color = GetCardBorderColor (accent #C6BFFF if selected, transparent if not)
    // Size: 80x60px
    // Margin: 4px between cards

    // "Matched from Image" card at end: accent border dashed (3px dash pattern)
    // This is the "Match Image Mood" button (per UI-SPEC primary button rule)

    // On hover: trigger InArgs._OnDryRunHover.Execute()
    // On click: trigger InArgs._OnPresetSelected.Execute()

    // Label: FText::FromString(Card.Name)
    // Font: FCoreStyle::Get().GetFontStyle("NormalText") with FNumberFormattingOptions letter-spacing 0.15em for Label role
    // Heading: 18px Semibold for section title (separate STextBlock above scroll box)

    // Selected state stored in SelectedPreset; border changes on selection
}
```

**SNyraLightingPanel.h:**
```cpp
class SNyraLightingPanel : public SCompoundWidget {
public:
    SLATE_BEGIN_ARGS(SNyraLightingPanel) {}
    SLATE_END_ARGS()

    void Construct(const FArguments& InArgs);
    // Hosts: reference thumbnail (if image attached), SNyraLightingSelector, "Apply Lighting" button, status pill
    // Layout: vertical box — header → selector → action row → status pill
    // Color tokens from 06-UI-SPEC.md applied via FLinearColor constants

    // WS listener: receive dry_run_preview messages from NyraHost (via FNyraWsClient)
    // On dry_run: highlight preset card with pulsing border animation (100ms ease-in-out)

    // "Match Image Mood" button: if reference image is in the chat/panel, calls nyra_lighting_authoring with reference_image_path

    TSharedPtr<FNyraWsClient> WsClient;

private:
    TSharedPtr<SNyraLightingSelector> LightingSelector;
    TSharedPtr<SNyraRefImageTile> RefImageTile;  // placeholder (will be implemented in 06-02)
    FString CurrentPreset;
};
```

**SNyraLightingPanel.cpp — Construct():**
```cpp
// Layout structure (SVerticalBox):
// [Heading: "Lighting Setup" — 18px Semibold]
// [Reference image thumbnail row — SNyraRefImageTile placeholder]
// [SNyraLightingSelector]
// [S NyraPrimaryButton: "Apply Lighting" — lavender #C6BFFF background, near-black text]
// [SNyraStatusPill: shows "Select a preset" → "Applying..." → "Applied: {mood}" per state]

// Design tokens from 06-UI-SPEC.md:
// Dominant: FLinearColor(0.02f, 0.02f, 0.03f, 1.f)  // #050507
// Secondary: FLinearColor(0.05f, 0.05f, 0.08f, 1.f)  // #0D0D14
// Accent: FLinearColor(0.776f, 0.749f, 1.f, 1.f)      // #C6BFFF
// Accent hover: FLinearColor(0.549f, 0.502f, 1.f, 1.f)  // #8C80FF
// Spacing: md=16px (FMargin(16,8)), lg=24px, xl=32px
// Font: Body=14px/400 Regular (Roboto fallback), Label=11px/400/letter-spacing 0.15em
```

**WS Dry-Run Integration:**

In `SNyraLightingPanel::Construct()`, register a message handler on `WsClient`:
```cpp
WsClient->OnMessageReceived().AddLambda([this](const FString& MsgType, const TSharedPtr<FJsonObject>& Payload) {
    if (MsgType == TEXT("dry_run_preview")) {
        // Pulse the selected card border — animate from #C6BFFF at 60% to 100% opacity over 200ms
        FWidgetAnimations::Get().GetOrCreate(this, "DryRunPulse");
    }
});
```

**Apply Lighting button:**
```cpp
// On click: call nyra_lighting_authoring via WS (NyraHost side) or direct Unreal Python call
// Uses SNyraPrimaryButton style (lavender fill, near-black text, 36px height per UI-SPEC)
```
  </action>
  <verify>
    <automated>find "/Users/aasish/CLAUDE PROJECTS/UEPLUG/UEPLUGIN/TestProject/Plugins/NYRA/Source/NyraEditor" -name "SNyraLightingSelector.cpp" -o -name "SNyraLightingPanel.cpp" | xargs grep -l "SLATE_BEGIN_ARGS\|Construct\|SLATE_ATTRIBUTE" 2>/dev/null | wc -l</automated>
  </verify>
  <done>Both Slate components compile with correct SLATE_BEGIN_ARGS/Construct pattern; WS dry-run integration wired; Apply button calls nyra_lighting_authoring</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| User NL prompt -> LightingLLMParser | Untrusted input crosses here; prompt is passed to LLM but never stored unfiltered |
| Reference image path -> parse_from_image | Validated with Path.exists() before LLM is called |
| NyraHost -> UE editor (actor spawn) | Actor spawn via unreal Python API; all labels prefixed NYRA_ for undo safety |

## STRIDE Threat Register

| Threat ID | Category | Component | Disposition | Mitigation Plan |
|-----------|----------|-----------|-------------|-----------------|
| T-06-01 | Information Disclosure | LightingLLMParser.parse_from_image | mitigate | image_path validated `Path.exists()` before LLM call; no file content stored |
| T-06-02 | Tampering | lighting_tools.py _apply_lighting_params | mitigate | All NYRA-placed actors prefixed `NYRA_`; `Ctrl+Z` wraps full session transaction per Phase 2 |
| T-06-03 | Elevation of Privilege | nl_prompt injection | mitigate | NL prompt passed to LLM only (not direct Unreal command); LLM output validated before actor spawn |
</threat_model>

<verification>
1. Unit tests:
   ```
   pytest tests/test_lighting_tools.py tests/test_scene_llm_parser.py -x -q
   ```
2. Manual verification:
   - Open UE editor with NYRA plugin loaded
   - Open chat panel, type "golden hour" → verify directional light + SkyAtmosphere actors appear in World Outliner with NYRA_ prefix
   - Click "Match Image Mood" with a reference image → verify lighting selector shows detected mood tags
   - Hover preset card → verify viewport updates with dry-run (no actor placed permanently)
   - Click "Apply Lighting" → verify actors are placed and status pill shows "Applied: warm, low sun"
</verification>

<success_criteria>
- SCENE-01 fully addressed: all 7 lighting types + 5 atmosphere/post types configurable
- SNyraLightingSelector renders 6 preset cards in horizontal scroll, hover triggers dry-run preview
- "Match Image Mood" button wired to LLM image analysis pipeline
- Status pill shows state transitions (idle → applying → applied/error)
- All NYRA-placed actors prefixed NYRA_ for undo tracking
</success_criteria>

<output>
After completion, create `.planning/phases/06-scene-assembly-image-to-scene-fallback-demo/06-01-SUMMARY.md`
</output>
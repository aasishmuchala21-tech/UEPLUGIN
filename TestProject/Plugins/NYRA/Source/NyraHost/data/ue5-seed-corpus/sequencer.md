# Sequencer

## Creating a Level Sequence

`UMovieSceneSequence` is the asset type. Create programmatically:

```python
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
ls = asset_tools.create_asset(
    asset_name="LS_HeroShot01",
    package_path="/Game/Cinematics",
    asset_class=unreal.LevelSequence,
    factory=unreal.LevelSequenceFactoryNew(),
)
```

The new sequence has one MovieScene with no tracks, no possessables, no spawnables.

## Bind an actor to the sequence

A possessable references an existing world actor by GUID. A spawnable defines an actor that the sequence creates and destroys. Use possessable for actors you've already placed; spawnable for shot-only actors that don't exist outside the take.

Possessable from Python:
```python
binding = ls.add_possessable(world_actor)  # world_actor is unreal.Actor
```

Spawnable:
```python
spawn = ls.add_spawnable_from_class(unreal.CineCameraActor)
binding = spawn  # spawn already returns the binding
```

The `add_spawnable_from_instance(instance)` variant captures the current state of an existing actor as the spawn template.

## Adding tracks and sections

Tracks are typed: `MovieScene3DTransformTrack` for transform animation, `MovieSceneCameraCutTrack` for camera switches, `MovieSceneFloatTrack` for FOV/CurrentFocalLength/etc. Each binding gets its own track set:

```python
transform_track = binding.add_track(unreal.MovieScene3DTransformTrack)
section = transform_track.add_section()
section.set_range(unreal.SequencerScriptingRange.make_range(0, 5*30))  # 5s @ 30fps
```

Then add keyframes to the section's channels (Translation X/Y/Z, Rotation X/Y/Z, Scale X/Y/Z).

## Camera focal length and FOV

CineCameraActor's CineCameraComponent exposes `CurrentFocalLength` (mm) and `CurrentAperture` (f-stop). FOV is derived from focal length + sensor size. To keyframe FOV, animate focal length — the equation is `FOV = 2 * atan((SensorWidth/2) / FocalLength)`.

The Python API uses `add_keyframe_absolute_focal_length(time, value)` on the focal-length channel. The older `add_keyframe_absolute_focal_focus` does NOT exist — that's a frequent fabricated-API error.

## Camera Cut track is mandatory for active camera

Sequencer renders whichever camera is bound on the Camera Cut track at the current time. Without a Camera Cut entry, even a perfectly authored CineCameraActor won't activate during playback. Add one Camera Cut section spanning the full sequence range, bind it to your CineCameraActor's binding GUID.

## Sequencer evaluation timing

`UMovieSceneSequencePlayer::Play()` advances the playhead from PlaybackStart. `Pause()` stops at the current frame. `JumpToFrame(FrameNumber)` seeks. The sequencer evaluates at the frame rate set on the MovieScene (default 30fps) — for cinematic-quality interpolation, match this to your render FPS.

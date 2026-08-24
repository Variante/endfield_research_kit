# Endfield character recovery lab

This Unity 2022.3 project is the maintained path for reproducing Endfield's
original Character Info render. Endminf is the current reference actor. Once
that frame is faithful, the same data-driven pipeline will be applied to every
playable character.

## Open the viewer

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\open_character_recovery_lab.bat
```

The default command opens the Endminf reference reproduction. Use `--lab` for
the general Unity editor view.

The canonical scene is:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

To rebuild the maintained character set:

```bat
.\build_all_character_recovery.bat
```

## Build reference frame sequences

Retail recordings can be split into character- and behavior-labelled PNG
sequences with pinned source timestamps:

```bat
scripts\reference_video\extract_reference_sequences.bat --list
scripts\reference_video\extract_reference_sequences.bat --recording endminf_overview_2026-08-21
scripts\reference_video\extract_reference_sequences.bat --recording roster_overview_2026-08-15 --character wulfa
```

The maintained annotations live in
`config/reference_video_sequences.json`; disposable decoded frames live under
`scratch/character_recovery/reference_sequences/`. See
`scripts/reference_video/README.md` for the capture, annotation, extraction,
and validation method to use for future videos.

Generated prefabs and contracts are rebuildable. Fix their importer, builder,
runtime component, or shader instead of editing generated files by hand.

## Active target

The source reference is `../videos/2026-08-15_10-32-32.mkv`; the focused
Endminf comparison capture is `../videos/2026-08-21_20-15-17.mkv`. Keep image
comparison, timing, camera, lighting, materials, effects, and post-processing
anchored to those recordings. Do not reintroduce actor-specific approximation
branches without source evidence.

Endminf is the only fidelity target during this phase. Shared import, material,
animation, camera, and render-pipeline code must remain character-neutral so
the completed result can later rebuild all characters.

## Recovered boundary

- All 31 playable post-models and 156 canonical post-model identities have
  generated prefab paths.
- Playable LOD0 meshes, materials, textures, cameras, profiles, lights,
  portraits, and the selected Overview animation sources are recovered.
- The selected playable UI animation scope is complete; runtime transition,
  blending, IK, secondary motion, and effect lifecycle behavior remain partial.
- Endminf's selected `ui_overview_start -> ui_overview_loop` handoff now runs
  through a generated source-backed Animator controller, and its four resolved
  overview rocks/crystals follow the exact 1.5-second active-state gate. The
  broader all-character runtime remains partial.
- Selected CharacterNPR, eye, hair, shadow, GBuffer, lighting, particle, and
  post-process contracts are source-backed and fail closed where inputs are
  unknown.
- The selected deferred resolver program has an executable HLSL port matching
  its recovered fixture within one float ULP. This proves the program and known
  inputs, not the missing retail frame resources.

Dormant all-character evidence remains under `Generated/OriginalData/` and
`tools/`: the 31-controller Overview census, per-character camera and light
contracts, playable Avatar/clip contracts, generic-actor boundaries,
secondary-dynamics contracts, and exact Last Rite head/Li Zhiyan finger effect
examples. These are retained contracts and validators, not enabled
actor-specific runtime branches. Retired M23, gacha, capture, and comparison
experiments should not be restored as production paths.

Published dynamics contracts remain auditable snapshots. Validators that
reconstruct them from native captures fail closed after the disposable capture
inputs are removed; retaining a contract does not promote its old scratch
capture into a maintained dependency.

## Useful conclusion from the retired explorations

Retail visual parity is not reached. More isolated shader approximation will
not close the main difference: the missing piece is the complete CharInfo
presentation frame, especially `SphereOutside`, `ShadowPlane`, the exact
character stencil path, and frame-produced lighting resources.

The reference video remains the visual authority. Native or GPU evidence can
strengthen individual bindings later, but the active work is to reconstruct
the complete Endminf frame from recovered game assets and measure it against
the video. Approximate layers stay labeled until their source path is closed.

Current status, evidence boundaries, and the remaining recovery queue live in
`../memory/character_render_and_animation_recovery.md`. Changing inventories
and exhaustive proof belong under `../reports/assets/character_recovery/`.

## Layout

- `Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/`: maintained import
  and scene builders.
- `Assets/EndfieldGraphShaderLab/Runtime/`: viewer, animation, and rendering
  runtime.
- `Assets/EndfieldGraphShaderLab/Shaders/`: maintained recovered and
  compatibility shaders.
- `Assets/EndfieldGraphShaderLab/Generated/`: rebuildable recovered assets and
  source contracts.
- `tools/`: source-contract builders and focused validators retained for
  reproducibility.

`Library/`, `Logs/`, `Temp/`, `Builds/`, `scratch/`, and `tmp/` are disposable
local output and are not part of the maintained project.

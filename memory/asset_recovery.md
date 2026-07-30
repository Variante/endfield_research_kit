# Asset recovery

## Current status

Asset extraction and discovery are strong. The project can index images,
models, materials, textures, shaders, animations, effects, audio, and video;
resolve many PathID-backed dependencies; and connect authored gameplay or Story
records to asset candidates with explicit provenance.

The main gap is semantic binding. Exporting an object does not prove its live
prefab composition, selected material variant, animation state, effect
activation, or placement time.

## Refresh

```bat
.\export.bat --export-from-game --with-assets
.\export_assets.bat
.\export_assets.bat --export-from-game
python scripts\build_assets.py
python tools\endfield_source_graph.py build
```

Asset modes, from narrowest to broadest, are `--focused-assets`,
`--default-assets`, and `--debug-assets`.

Primary outputs:

```text
export_full/recovered/AnimeStudio-cli/
export_full/structured/Audio/
webui/data/assets/index.json
webui/data/assets/story_media.json
webui/data/assets/videos.json
reports/assets/
reports/source_graph/
```

## Evidence order

Prefer:

1. authored asset/prefab path or direct table key;
2. source root plus PathID/PPtr;
3. exported prefab/component dependency;
4. material-to-texture/shader reference;
5. exact controller, clip, effect, audio, or video consumer;
6. stable normalized identity;
7. labeled name/token similarity.

Preserve source roots, PathIDs, LOD/state suffixes, material slots, texture
roles, and evidence kind. Never treat a global PathID or similar filename as a
unique binding.

## Current strengths

- WebUI asset and Story-media indexes.
- Renderable asset-entity grouping for many models and prefabs.
- Material, texture, shader, controller, animation, audio, and video links.
- Exact character post-model enumeration and baseline prefab generation.
- Selected static world placements and gameplay/entity associations.

## Remaining gaps

- Exact runtime prefab assembly and entity-to-renderable ownership.
- Material keyword/pass/queue selection and runtime overrides.
- Native texture descriptors and mip payloads outside validated families.
- Animation/effect activation and controller execution.
- Modular NPC and VFX composition.
- World visibility/spawn policy.
- Broader exact audio/video trigger ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

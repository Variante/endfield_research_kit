# Map page recovery

## Purpose

Map publishes level/task navigation, exact and bounded spatial evidence, Story
links, and independently selectable render layers. It does not turn proximity,
shared script context, or available assets into ownership.

## Inputs and recovery flow

1. Tables and registries establish level ids, regions, quests, missions, map
   art, and exact authored points.
2. Story/LevelScript recovery contributes only evidence-typed trigger, radio,
   reading-point, and NPC-proxy links.
3. AnimeStudio maps and converted Mesh/Material/Texture2D outputs provide asset
   identity. `recover_map_streaming_instances.py` streams installed
   `InitChunkData` and joins exact matrices to those exports.
4. `scripts.build_map_recovery_data` publishes the index and per-level payloads;
   its preview phase publishes minimap, terrain, HLOD/streaming surface, water,
   and point layers as independent evidence.

Outputs live under `webui/data/map_recovery/`; generated audits and changing
coverage live under `reports/assets/map_recovery/`.

## Evidence boundary

- Coordinates and matrices prove placement, not activation, visibility,
  interactivity, prefab identity, or renderer ownership.
- Story-to-point links require an exact trigger/action/slot, NPC attachment, or
  authored pin join. Mission context, sibling actions, filename similarity,
  and proximity are diagnostics only.
- Map01/Map02 and config-proven shared scenes stitch only through published
  region contracts. Dungeons and danger maps remain independent.
- Minimap, elevation, material surface, water, and point samples retain their
  own provenance and visibility controls.
- Ambiguous AssetMap collisions and missing mesh/material/texture closures fail
  closed. Presentation fallbacks must not be labeled exact game rendering.
- A streaming sidecar failure stops the canonical map phase instead of silently
  substituting sparse points.

## Focused refresh

```bat
python -m scripts.build_map_recovery_data --with-preview
python scripts\build_map_recovery_preview.py --level LEVEL
python scripts\build_map_recovery_preview.py --refresh-exact-fallbacks-only
```

Use the canonical export when installed inputs or extracted assets changed.
Mission Pipeline remains a standalone recovery workflow, not a WebUI page.

## Remaining gaps

- Recover exact scene hierarchy and renderer ownership.
- Close unresolved streaming mesh/material joins without normalized-name guesses.
- Recover water geometry where authored map art is insufficient.
- Add maintained behavior-level browser coverage for map navigation and layers.

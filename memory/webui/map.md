# Map page recovery

## Purpose

Map publishes level/task navigation, exact and bounded spatial evidence, Story
links, and independently selectable render layers. It does not turn proximity,
shared script context, or available assets into ownership.

## Inputs and recovery flow

1. Tables and registries establish level ids, regions, quests, missions, map
   art, and exact authored points. Every level is recovered the same way
   through the `WorldEntityRegistry` id encoding
   ([`build_map_recovery_data`](../../scripts/webui/map/build_map_recovery_data.py)).
2. Story/LevelScript recovery contributes only evidence-typed trigger, radio,
   reading-point, and NPC-proxy links.
3. AnimeStudio maps and converted Mesh/Material/Texture2D outputs provide asset
   identity. `recover_map_streaming_instances` streams installed
   `InitChunkData` and joins exact matrices to those exports.
4. `scripts.webui.map.build_map_recovery_data` publishes the index and
   per-level payloads; its preview phase
   ([`build_map_recovery_preview`](../../scripts/webui/map/build_map_recovery_preview.py))
   publishes minimap, terrain, HLOD/streaming surface, water, and point layers
   as independent evidence.

## Primary generated outputs

`webui/data/map_recovery/{index.json,maps/<levelId>.json,render/**}`; the
payload contract is in [`../../webui/README.md`](../../webui/README.md) and the
panel, layer, and inspector behavior in the header comment of
`webui/src/features/map_recovery/index.js`. Generated audits and changing
coverage live under `reports/assets/map_recovery/`.

## Evidence boundary

- Coordinates and matrices prove placement, not activation, visibility,
  interactivity, prefab identity, or renderer ownership.
- Story-to-point links require an exact trigger/action/slot, NPC attachment, or
  authored pin join. Mission context, sibling actions, filename similarity,
  and proximity are diagnostics only.
- Exact `LevelMapMark.basicData.markInstId` plus an equal decoded position
  attaches authored map-mark template and default-visibility data to an
  existing `WorldEntityRegistry` node; a narrower subset with an independent
  unique `LevelShortIdTable.sceneName` join may show authored scene evidence.
  Registry-only annotations claim no scene from the registry's id bucket.
  Unmatched marks are counted, never plotted by group key, and no live
  visibility or discovery is claimed. The annotation needs a current JsonData
  corpus receipt that the normal WebUI export does not rebuild: after an
  installed-game refresh, regenerate the VFS audit and its BuffData, SkillData,
  and JsonData corpus gates before rebuilding Map if the receipt no longer
  matches the exported JSON bytes.
- Map01/Map02 and config-proven shared scenes stitch only through published
  region contracts. Dungeons and danger maps remain independent.
- Minimap, elevation, material surface, water, and point samples retain their
  own provenance and visibility controls.
- Ambiguous AssetMap collisions and missing mesh/material/texture closures fail
  closed. Presentation fallbacks must not be labeled exact game rendering.
- A streaming sidecar failure stops the canonical map phase instead of silently
  substituting sparse points.

### Render layers, one grade at a time

- Static OBJ projection requires an exact matrix and mesh relation. Material
  color requires one unambiguous Mesh -> Material -> base texture path plus UVs.
- HLOD exports without an exact instance matrix remain diagnostic only (the
  inferred grid fit publishes its coverage, and an under-determined fit
  publishes no background). Map01/Map02 clusters join their `InitChunkData`
  matrix by exact level, HLOD level, grid i/j, and signed cluster hash;
  unmatched or non-unique rows are omitted with no name-prefix or spatial
  fallback. A seamless member uses a shared regional HLOD origin only when its
  own marker coverage stays within the fit tolerance; rejected origins stay in
  the render manifest rather than silently shifting a grid by one cell.
- HLOD cluster color binds each cluster to one generated material by the exact
  level/LOD/signed-suffix contract and follows that material's
  `_BaseColorMap` PathID to the exported atlas; missing or duplicate links fail
  closed to the elevation palette. This recovers unlit base color, not
  environment lighting or post-processing.
- Danger-map surfaces state their grade in the task column: inferred
  source-art HLOD crop, exact streaming mesh with unverified color, or exact
  streaming mesh with partial recovered base color. `dung01_wrdg001` prefers
  its exact streaming projection; its older inferred HLOD remains diagnostic.
- Map01 and Map02 use exact `UILevelMapLoadConfig` world rectangles for their
  minimaps and exact `InitChunkData` matrices for HLOD geometry. Surface and
  elevation keep every joined triangle; the point layer samples those exact
  surfaces on a deterministic world-space lattice
  (`--surface-point-density`) without changing transforms. Point, roof, and
  slab exclusion rules are in the preview module docstring.
- Terrain `_H` records give an independent diagnostic byte preview: the
  builder reads only validated finest Map01/Map02 cells intersecting the
  level's world rectangle and combines each two-byte texel little-endian only
  for grayscale contrast. No scalar height decode, relief ordering, world-Y
  scale, or no-data sentinel is proved; the native format evidence and open
  consumer join are in [`../game_data/world_terrain.md`](../game_data/world_terrain.md).
- Water requires both authored minimap water pixels and exact WaterData scene
  evidence. Packed flowmaps alone are not coverage.
- Levels without in-game minimaps keep an exact registry/quest transform point
  layer when an inferred HLOD surface is suppressed. The frontend applies no
  image-registration scale or translation, and a level with no exact Mesh join
  stays transform points only.

Marker eligibility, slot action bindings, and carrier identity domains are in
[`../game_data/story_carriers.md`](../game_data/story_carriers.md).

## Focused refresh commands

```bat
python -m scripts.webui.map.build_map_recovery_data --with-preview
python -m scripts.webui.map.build_map_recovery_preview --level LEVEL
python -m scripts.webui.map.build_map_recovery_preview --refresh-exact-fallbacks-only
```

Previews checkpoint after each completed scene and reuse matching outputs;
normal input changes invalidate the affected cache, and `--no-render-cache`
forces a rerender for audits. Use the canonical export when installed inputs or
extracted assets changed. Mission Pipeline remains a standalone recovery
workflow, not a WebUI page.

## Highest-value remaining gaps

- Recover exact scene hierarchy and renderer ownership.
- Close unresolved streaming mesh/material joins without normalized-name guesses.
- Recover water geometry where authored map art is insufficient.
- Add maintained behavior-level browser coverage for map navigation and layers.

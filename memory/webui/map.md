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
4. `scripts.webui.map.build_map_recovery_data` publishes the index and per-level payloads;
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
- Exact `LevelMapMark.basicData.markInstId` and equal decoded position attach
  authored map-mark template and default-visibility data to an existing
  `WorldEntityRegistry` node. A narrower subset has an independent unique
  `LevelShortIdTable.sceneName` join and may show authored scene evidence.
  Registry-only annotations do not claim an authored scene from the registry's
  id bucket. The Map payload reports both joins and per-level coverage; it
  does not plot unmatched marks by numeric group key or claim live visibility
  or discovery. The `Authored marks` filter shows only existing nodes carrying
  this annotation and keeps the selected authored floor constraint, so it does
  not manufacture nodes for the unmatched set.
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
- HLOD exports without an exact instance matrix remain diagnostic only. Map01
  and Map02 join each exported cluster to its `InitChunkData` 4x4 matrix by
  exact level, HLOD level, grid i/j, and signed cluster hash; unmatched or
  non-unique rows are omitted without a name-prefix or spatial fallback.
- Seamless Map01/Map02 members vote on a shared HLOD origin, but a member uses
  that origin only when its own multi-LOD marker coverage remains within the
  accepted fit tolerance. Rejected regional origins and their bounded coverage
  are retained in the render manifest instead of silently shifting a local grid
  by one cell.
- e0m0 HLOD clusters use the generated assets' exact level/LOD/signed-suffix
  contract to bind each cluster to one generated material, then follow that
  material's `_BaseColorMap` PathID to the exported diffuse atlas. Missing or
  duplicate links fail closed to the elevation palette. This recovers unlit
  base color, not the game's environment lighting or post-processing. The same
  generated-material contract applies to every published HLOD source and
  independent crop: current indexed clusters all resolve uniquely, and
  unresolved or duplicate future exports still fail closed.
- Danger-map surfaces state their evidence grade in the task column: inferred
  source-art HLOD crop, exact streaming mesh with unverified color, or exact
  streaming mesh with partial recovered base color. `dung01_wrdg001` prefers
  its exact streaming projection; its older inferred HLOD remains diagnostic.
- Map01 and Map02 use exact `UILevelMapLoadConfig` world rectangles for their
  authored minimaps and exact `InitChunkData` matrices for recovered HLOD
  geometry. Surface and elevation layers retain all successfully joined
  triangles; the point layer samples those exact transformed surfaces on a
  deterministic world-space X/Z lattice, and `--surface-point-density N`
  (default `0.25`, approximately 2 m spacing) controls samples per square metre
  without changing transforms or alignment.
- Point sampling excludes named floor, roof, ceiling, ground, and terrain
  meshes plus broad near-horizontal non-prop slabs from the point layer only;
  material and grayscale elevation layers retain floors and the remaining
  recovered environment surface while omitting explicitly named roof/ceiling
  covers. Explicitly named roof/ceiling instances are omitted from every
  recovered geometry layer.
- HLOD point overlays retain a deterministic sparse sample set for every
  projected pixel and elevation. The normal full-range view uses the compact
  sample sidecar; the browser groups samples into shallow height slabs and
  alpha-composites them from low to high. A bounded height filter omits
  excluded slabs, so removing an upper layer reveals co-projected geometry
  below it instead of retaining the upper layer's raster coverage.
- Exported Terrain `_H` records provide an independent diagnostic byte preview.
  The current authenticated Terrain corpus confirms the same 65-by-65,
  two-byte-texel header shape for every `_H` tile.
  The builder indexes only the validated finest Map01/Map02 grids, reads only
  cells intersecting the selected level's authored world rectangle, and reuses
  unchanged PNGs through source sidecars. Each stored texel is two bytes; the
  preview combines them little-endian solely to form grayscale contrast. The
  selected native format identifies two-channel texels, but no scalar height
  decode, relative relief ordering, absolute world-Y scale, or no-data sentinel
  has been proved. Map gives this preview its own control and leaves
  mesh-derived grayscale elevation separate. The native format evidence and
  remaining consumer join are in [`../game_data/world_terrain.md`](../game_data/world_terrain.md).
- Water requires both authored minimap water pixels and exact WaterData scene
  evidence. Packed flowmaps alone are not coverage.
- Levels without in-game minimaps retain an exact registry/quest transform
  point layer when an inferred HLOD surface is suppressed. The frontend applies
  no image-registration scale or translation, and a level with no exact Mesh
  join remains transform points only rather than falling back to inferred
  geometry.

Marker eligibility, slot action bindings, and carrier identity domains are in
[`../game_data/story_carriers.md`](../game_data/story_carriers.md). Frontend
panel, layer, and inspector controls are in
[`../../webui/README.md`](../../webui/README.md).

## Focused refresh

```bat
python -m scripts.webui.map.build_map_recovery_data --with-preview
python -m scripts.webui.map.build_map_recovery_preview --level LEVEL
python -m scripts.webui.map.build_map_recovery_preview --refresh-exact-fallbacks-only
```

Exact streaming, point-layer, and inferred HLOD previews checkpoint after each
completed scene and reuse matching outputs on later runs. Use
`--no-render-cache` only when auditing a forced rerender; normal input changes
invalidate the affected cache.

Use the canonical export when installed inputs or extracted assets changed.
Mission Pipeline remains a standalone recovery workflow, not a WebUI page.

## Remaining gaps

- Recover exact scene hierarchy and renderer ownership.
- Close unresolved streaming mesh/material joins without normalized-name guesses.
- Recover water geometry where authored map art is insufficient.
- Add maintained behavior-level browser coverage for map navigation and layers.

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
   `InitChunkData` and recovers exact matrices. Its level/HLOD/grid/cluster
   hash join gives exact HLOD Mesh identity; its generic entity-name to Mesh
   family join is a preview candidate until prefab or renderer ownership is
   proved.
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

- Static OBJ projection carries an exact matrix and a separately graded Mesh
  relation. Generic Mesh family matches remain preview candidates even with a
  unique name and exported PathID; a matching name does not prove prefab
  ownership. Equal-ranked distinct source/offset/PathID candidates are omitted
  instead of chosen alphabetically. Material color requires one unambiguous
  Mesh -> Material -> base texture path plus UVs.
  A focused dialog actor prefab probe proves an AssetBundle root -> child
  renderer -> exact Mesh PPtr chain for one candidate, but the streamed entity
  has no known pointer to that prefab. The WebUI therefore retains the
  candidate grade. The smallest useful capture is the streamed entity id with
  its selected prefab resource path or root source CAB+PathID at creation time.
  No current `EndfieldCapture` profile emits that pair: its graphics, audio,
  gameplay-semantic, SkillData, and ECS-list observations do not bind a streamed
  entity to prefab selection. The native Streaming contract proves selected
  anonymous row/path reads but no concrete Create instance or prefab-selection
  callback ABI. A new capture must first prove and gate a callback that observes
  scene/chunk context, entity id, and selected prefab root/path in one call;
  launching an existing profile or recording a screen image cannot fill this
  identity gap.
  The installed asset-conversion internal call was tested as a scoped hook
  lead and does not expose an Init entity ID with a prefab source at one
  boundary. Its separate entity-name getter does not make an arbitrary Unity
  object result into a prefab selection. The Map candidate grade remains in
  force, and no user capture is ready for this entity yet. The Init ID-keyed
  runtime carrier's eight-byte value reaches a new-record branch, but its
  first callback setup forwards the value and appends it as anonymous child
  state. That setup places the selected Init row's nested table and name in
  a context. The selected group loader builds the value as a descriptor-slot
  index plus a counter; the default callback uses its low 32 bits to index
  an anonymous context table, without a proved prefab source. The producer
  and callback reach their tables through two manager fields. The selected
  manager constructor copies the group-table pointer into one field and saves
  the address of its owner pointer in the other, so they alias at construction;
  a later mutation and live equality have not been checked. The immediate
  callback reads bit-masked fields in a 576-byte row, interns nonzero
  eight-byte values into local indices, and appends external-asset request
  records. A checked consumer of the matching context field deduplicates
  opaque keys into another local table without reading a resource path or
  source object; its execution for the target scene is unproved.
  The installed target pair has the same entity ID at the corresponding
  ordinal in both roots, but no live root receipt or callback-to-prefab
  source relation is known. The remaining edge is a selected downstream
  operation that resolves one of those opaque keys or child records to a
  prefab resource identity while retaining the entity ID or a stable keyed
  context. The ID-map insertion, field-intern call, external-asset request
  deduplication, and context name alone cannot name a prefab or support a
  capture profile.
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
- Recovered streaming previews state their surface grade in the normal map
  task column: exact HLOD-key geometry, or a name-matched Mesh preview with
  unverified or partially recovered base color. The instance matrix is exact;
  generic Mesh ownership is not. Danger-map surfaces also label inferred
  source-art HLOD crops. `dung01_wrdg001` prefers its streaming projection;
  its older inferred HLOD remains diagnostic.
- The local focused refresh covered `indie_dg008`, `dung02_dg005`, and
  `indie_dg006` (the exact LevelConfig scene for `dung02_bdg002`), plus the
  affected Map previews. Other streaming sidecars need a canonical Map refresh
  to carry the new per-Mesh grade and ambiguity diagnostics; older rows are
  labeled as legacy surfaces with an ungraded Mesh relation in the normal task
  column. Their old background wording is suppressed when no binding status is
  present, so it does not silently claim exact geometry.
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
  A focused Unity-store check of the selected `Config_water_Map02_0`
  MonoBehaviour found flow, wave, color and scattering settings. Its serialized
  TypeTree has only `m_GameObject` and `m_Script` PPtrs; `m_GameObject` is null,
  and there is no Mesh, renderer, or surface-geometry reference in this object.
  This rules out that config object as a water-geometry source, not other
  Map02 water assets. The missing edge remains a scene water-surface object or
  native consumer that identifies its actual renderer/Mesh and transform.
  A second focused source identifies a real WaterSurface Mesh candidate for
  `map02_lv002`: the AssetMap names `item_liquid_water#22800040000_WaterSurface`
  as a Mesh, and its selected CAB's AssetBundle container points directly to
  the same Mesh PathID. The converted object is a local four-vertex,
  two-triangle plane. `InteractiveData/Collections` assigns the matching
  numeric key to `map02_lv002`; this is a structural scene-key match, not a
  placed renderer or transform. The selected bundle exposes a Mesh asset,
  while the scene's instance transform and activation remain unjoined. Do not
  render this local plane as Map02 water coverage without that placement edge.
  A targeted same-CAB AnimeStudio renderer-index pass selected that
  AssetBundle and completed with zero renderer rows. The current generic
  MonoBehaviour/PlayableDirector object index has no PPtr carrying this Mesh
  PathID, and neither CABMap lists a CAB depending on the Mesh CAB. These are
  bounded negatives for serialized owners in those indexes, not evidence that
  the game never loads the Mesh directly or constructs a water renderer at
  runtime. The next missing link is the scene water consumer's resource
  selection and placement transform.
- Levels without in-game minimaps keep an exact registry/quest transform point
  layer when an inferred HLOD surface is suppressed. The frontend applies no
  image-registration scale or translation, and a level with no selected Mesh
  candidate stays transform points only.

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
- Close streaming prefab/renderer to Mesh ownership and unresolved material
  joins through serialized references or a runtime capture.
- Recover water geometry where authored map art is insufficient.
- Add maintained behavior-level browser coverage for map navigation and layers.

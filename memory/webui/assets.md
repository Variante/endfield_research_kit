# Assets page recovery

## Purpose

Assets inventories browser-visible exported images, video, OBJ, FBX, and
related resource metadata. Exported JSON documents are not listed: they are
rows of the export's Unity object store, browsed on the Data page, and Assets
links a material to its Data-page document. It is a resource browser and
evidence source for other pages, not proof that an asset was used at runtime.

## Inputs and recovery flow

1. AnimeStudio builds source-scoped AssetMaps and exports the selected asset
   scope. Focused mode targets referenced textures; default adds WebUI-facing
   model/material/animation needs; debug is exhaustive diagnostics.
2. `scripts.webui.assets.build_assets` indexes available outputs and publishes
   media lookup, Story media, and video catalogs. Sprite images have no files:
   each Sprite crop document is listed as an image at
   `Unity/Sprite/<name>.png` with its size and texture (`crop`); `serve.py`
   answers that path with the document and `webui/sprite_worker.js` renders it
   from the texture.
3. Gameplay's `asset-refs` stage consumes the Assets index and owns its
   consumer-specific join; the Assets builder does not write that sidecar.
4. [`table_asset_owners`](../../scripts/webui/assets/table_asset_owners.py)
   recovers exact table-row ownership: a Table row owns an asset only when an
   asset-bearing field holds a value equal to the whole normalized asset stem.
   It always reads the complete scan, not the focused projection.
5. Packaging may publish a compact normal-page media index and a complete
   resource index. Extract the resources archive last so the complete index
   wins.

## Primary generated outputs

`webui/data/assets/{index,relations,table_owners,activity_media,videos}.json`
(`build_assets --publish index`); Story media owns `story_media.json`
(`--publish story-media`, the `story_media` task) and Gameplay owns
`gameplay_refs.json`. Frontend behavior is in the header comment of
`webui/assets.js`.

Filter counts come from the same grouped entries that the list filters, not
raw exported files. They are dataset totals; type, category and source groups
combine with AND, and search narrows their result. A numbered category can
therefore have no matches with other filters active. Chip tooltips and the
empty-list message explain that distinction; reset clears the search and all
facet selections. Image categories (such as Boss) and OBJ model categories
(such as Model Boss) describe separate kinds of entries.
The expanded category catalog scrolls inside a bounded filter panel; the asset
list keeps its own space so matching rows remain visible below the filters.

OBJ and FBX previews share background presets and custom background/model
color controls in both WebGL and the software fallback. Model color is a
preview tint, not recovered material appearance.

Cooked collision previews are a separate Assets-owned projection from an
authenticated selected-corpus receipt. The broad builder checks its audited
inputs, full exporter closure, explicit identity coverage and typed/raw buffer
hashes, then runs the complete readers before publishing staged OBJs under
`webui/data/assets/collision/`. The `cl` metadata preserves physical source,
CAB, offset and decimal PathID without JavaScript integer rounding. The
`Collision` tag starts off and reset hides it again; collision variants remain
separate from render models and from other serialized collision identities.
There are no name-based material or table-owner joins for this projection.
Preview coordinates and winding remain in mesh local space.

`build_assets --publish collision` updates this projection in the existing
broad index without rescanning render media or rewriting ownership/media
sidecars. It rejects a changed index during publication. A missing/stale
receipt clears collision rows and retains an unavailable diagnostic; ordinary
Assets rows keep their last publication. The optional receipt is produced by
the raw-format corpus command, not by the page's ordinary `--from-game` scope.

OBJ WebGL previews preserve face UVs, authored normals, and `usemtl` draw
ranges. An OBJ without `usemtl` uses a material only when its published links
have one distinct material name; multiple candidates remain neutral. Linked
Unity material relations supply base textures, tint, alpha testing and blending.
Missing UVs keep the affected range untextured. These name-based preview links
do not prove runtime renderer ownership; the software fallback stays untextured.

FBX mesh controls classify `eyesshadow`, `hairshadow`, and a separate `hs`
token as shadows, alongside shadow proxies. Shadow model ancestors and shadow
material names also supply this preview classification. `vfxpart` names count
as VFX alongside FX/effect names. Shadows start hidden; VFX starts hidden when
ordinary meshes exist and remains visible in effect-only prefabs. These name
rules organize the preview and do not establish runtime renderer ownership.

The FBX viewer bakes stored mesh transforms into a static preview; its
Animation-stack count is metadata, not animation playback. Ultimate assets
often use `ult` or `ultskill` rather than `ultimate`, and appear as separate
effect, camera or model pieces. AnimationClip `.anim` documents belong to the
Data store browser, not the Assets media list. Complete FBX indexing therefore
does not establish complete skill presentation or its timed composition.

## Evidence boundary

- Source/CAB plus PathID is the stable Unity identity. Normalized names are
  discovery aids only.
- Indexed, loaded, exported, partial, and certified-clean are distinct states.
- Material/shader/texture presence does not establish runtime variant,
  renderer ownership, or final appearance.
- Missing optional previews remain visible and do not erase the indexed asset.
- A Sprite image equals AnimeStudio's rendering pixel for pixel
  ([`../game_data/unity_assets.md`](../game_data/unity_assets.md)); a crop whose
  texture is not exported is left out of the index. Sprites with the same
  pixels share `h`: a whole-texture Sprite shares its texture's SHA-256.
- Table ownership requires both gates: an asset-bearing field name and a
  whole-stem value match. A shared name prefix, a family stem, or an
  identifier field that coincides with an asset name is not ownership and is
  not published as a candidate. Most exported assets therefore stay unowned,
  because UI sprites are referenced from prefabs rather than from table rows.

## Focused refresh commands

```bat
python -m scripts.webui.assets.build_assets
.\export.bat assets --from-game
.\export.bat assets
```

The Assets page extracts Table, video, Material JSON and the Texture2D,
Sprite, Mesh and Animator media. Use `.\export.bat debug --from-game` only for
broad investigation; the index then also carries every debug class.

## Highest-value remaining gaps

- Empty OBJ markers and point-only OBJ files are inventoried, but hidden by
  default behind the off `Empty mesh / no drawable faces` tag. The index's
  `nd` flag follows the preview's valid indices and triangle-fan checks, not
  filename or file size. Reset hides them again, and empty variants never
  share a preview group with drawable variants. Classification says only
  that the exported OBJ has no drawable surface, not why its Unity source
  lacks render geometry; the extraction topic records the collision evidence.

- Decoded collision previews close the stored-geometry gap for their admitted
  selection. A MeshCollider PPtr and complete reciprocal Transform hierarchy
  can establish a serialized prefab binding; they do not establish a live
  scene instance, activation or physics behavior. See the Unity-assets topic
  for this boundary and the bounded scene-object reader.

- Improve object-level dependency and conversion diagnostics.
- Recover exact renderer/material/texture and animation ownership.
- Table rows cover only the sprites a table names directly. Activity
  background sets, achievement icons, AI-bark portraits, attachment widget
  models, and ability-entity models are referenced from prefabs and UI
  layouts, so closing them needs a prefab/UI reference pass, not a wider name
  rule.
- Keep broad resource browsing packageable without inflating normal-page loads.

See [`../game_data/unity_assets.md`](../game_data/unity_assets.md) for durable
asset identity and binding semantics.

Activity media is a compact Assets-owned publication from the existing full
scan. It follows exact activity asset fields, instructionId into InstructionBook
and fixed reward itemBundles into ItemTable; it prefers Sprite crops over
duplicate Texture2D representations and preserves distinct Sprite identities.
Activities reads the last publication without adding a cross-page dependency.

Assets collapses byte-confirmed identical exported media into one preview
variant within existing asset groups, including images, OBJ, FBX, and video.
The index retains every file row; `h` is the full content SHA-256 and `d` marks
same-kind, same-extension groups also checked for byte equality with bounded
memory. All original filenames and PathIDs remain searchable and appear in
same-content file details. Converted-file equality does not establish original
Unity object equality or ownership; OBJ omits skin weights and blend shapes.
Sprite crops retain their separate texture/crop content evidence. Export files
remain in place.

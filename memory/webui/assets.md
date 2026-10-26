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

FBX entries with matching geometry/material/rig content share one item page. Details
list every unique resource path from the index's `c`/`cs` memberships; path
aliases do not create variants or a difference note. Every original file link,
filename, PathID and resource path remains resolvable or searchable. Distinct
LOD content retains its prefab-scoped variants and per-LOD resource paths.
The versioned `fc` grouping key excludes document URLs naming this exported
file, its matching root label and non-bone Null carrier labels after ordinary
FBX normalization. It also ignores placement/joint transforms, preferred
angles, pose matrices and Cluster bind matrices. Geometry, materials,
mesh/bone names, hierarchy, skin indices/weights and animation stay in the
comparison; linked Null bones keep their names. Full-file hashes remain in
`h`, and every original stays downloadable under Resource files. The shared
preview follows the selected variant's original pose. The separate `fv` key
retains transforms, pose and bind values after excluding the same labels;
matrix arrays are decoded so compression cannot create a variant. Different
`fv` values become named variants with a placement/pose/skin-binding difference
fact, separate previews and Download current file links. Path/name-only aliases
stay together within their variant; Resource files links every original, and
deep links select the corresponding variant. This is conditional resource
grouping under the chosen pose-insensitive policy, not byte equality, Unity
identity or runtime equivalence. `--publish fbx-content` refreshes both keys without
rebuilding other Assets projections and rejects stale/concurrent inputs.

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

Runtime collision evidence is an optional separate metadata projection owned by
`scripts/webui/assets/collision_runtime.py`. It replays the maintained geometry
audit against explicitly selected installed native inputs, admitted capture
journal/archive and authenticated stored Mesh receipts. It joins full CAB/PathID,
physical source/offset, raw and cooked hashes, and dimensions; names never join.
The input selection is generated under `reports/assets/`, contains paths rather
than claims, and is revalidated on subsequent broad builds. It is not a saved
audit whose status alone can authorize labels.

`build_assets --publish collision-runtime` updates existing collision metadata
without rebuilding OBJ previews or media/ownership sidecars. Invalid or missing
runtime inputs clear old runtime labels and retain the stored geometry. Details
separate observed query geometry, uniquely matched movement returns, accepted
filter candidates, whole-array equality and prefix-only equality. Comparisons
using separately timed current poses remain conditional; nonpositive or initial
overlap sweep points do not become surface evidence. Neither queries nor accepted
filter candidates establish solver contacts, and unobserved rows are not unused.
With Collision enabled, bilingual evidence search terms select the observed
query, movement-result, accepted-filter, complete-array or captured-prefix rows.
The evidence lane remains owned by
[`world_dynamic_streaming.md`](../game_data/world_dynamic_streaming.md).

Stored collider ownership is a separate optional projection in
`scripts/webui/assets/collision_authored.py`. Its selected scene receipts are
revalidated through the installed VFS, physical chunks, exporter closure and
raw/typed census; derived owner rows are recomputed rather than trusted. A join
requires the full physical Mesh identity, raw/cooked hashes, dimensions and
the MeshCollider's triangle/convex selection. AssetBundle container GameObject
pointers identify prefab roots; preloads and names do not identify owners.
The admitted cooked-Mesh corpus can supply missing external targets through
the maintained scene/Mesh receipt composer, with both selections retained and
complete target geometry checked. This extends Mesh binding coverage, not the
selected scene-body census.

`build_assets --publish collision-authored` updates `cl.authored`, optional
`cl.models`, and their
publication diagnostic. Details show all admitted prefab paths and reciprocal
root-to-collider hierarchies with their stored enabled/active flags. Those are
authored settings, not live activation or world placement. Mesh previews retain
local coordinates. Bilingual `authored` / `存储归属` search finds these rows
even without runtime observations. Missing or invalid scene inputs clear old
owner claims while preserving stored previews and admitted runtime metadata.
This lane's raw evidence is owned by
[`unity_assets.md`](../game_data/unity_assets.md).

The authored selection v3 can also name existing Model and BoxCollider source receipts.
`collision_models.py` recomputes native-gated Model fields and manifest paths,
then joins the active logical Bundle and the declared prefab root to exact
collider identities. Details retain source files, grid IDs, Model ordinals and
stored Pos/Rot/Scl axes; Model axes and prefab-local collider matrices remain
separate, and neither is applied to the mesh preview. Bilingual `configured` /
`定义场景` search finds these records. Source-file links open Data's raw
DynamicStreaming row only when its authenticated physical path belongs to the
selected export root. These links use the Data page's shared in-page navigation
hook, including keyboard activation. Missing source/native gates clear only Model claims and
report the failure, retaining admitted owners, runtime evidence and previews.
The source-format boundary remains in
[`world_dynamic_streaming.md`](../game_data/world_dynamic_streaming.md).

The same admitted selections can publish optional `cl.prefabs` assembly links
through `collision_prefabs.py`. Assemblies group by full physical root identity,
not prefab name, and decode the selected cooked surfaces again before applying
each collider's stored root-and-descendant TRS chain. Distinct references to one
Mesh remain distinct parts. Reflected transforms reverse face winding; singular
or non-finite transforms fail the optional assembly projection. Disabled and
inactive definitions remain included and counted. Preview/reset controls and
OBJ downloads let users inspect relative collider placement without replacing
the original mesh preview or download. Bilingual `assembly` / `组合预览` search
finds these variants. `CollisionPrefab` maps to a staged generated output root.

This is selected collider coverage, not a complete prefab reconstruction:
primitive/custom colliders other than separately admitted boxes and unselected bodies are outside the projection,
and selected unrecovered siblings remain counted. Coordinates include the
stored root TRS; Model axes, runtime grid matrices, parenting and animation are
not applied. Assembly failures clear only their links and source root, retaining
admitted owner/Model/runtime evidence. Final source snapshot failures clear all
authored claims. The existing `collision-authored` publication refreshes these
assemblies without extraction or a live capture.

The optional `boxReceipt` selection is produced by `unity_box_corpus.py` from
the same admitted physical Bundle sources. Its independent raw/typed census,
serialized BoxCollider type-tree layout, original Bundle hashes and reciprocal
component/Transform links are revalidated before composition. The base scene
and cooked-Mesh scopes remain unchanged. `cl.prefabs` v2 distinguishes mesh
and box counts and retains each box's full dimensions, local center, stored
flags and exact physical identity. Boxes are mathematical surfaces in stored
Transform-chain coordinates, not recovered cooked payloads or effective live
PhysX shapes. Bilingual `BoxCollider` / `存储盒形` searches their assemblies.
Boxes lacking an exact admitted mesh assembly root are counted as unlinked;
name/path proximity never attaches them. Invalid supplemental admission retains
mesh-only assemblies; projection or final supplemental snapshot failures clear
assembly links and report the scoped error while retaining original previews
and admitted owner/Model/runtime metadata. Sphere, capsule and custom body
layouts remain outside this reader.

Optional `renderReceipt` in authored selection v5 admits the separately scoped
MeshFilter/MeshRenderer corpus. `cl.renderers` v3 links render components to
collision variants through the same full physical prefab-root identity, not
matching names. Details retain the root-to-renderer hierarchy, stored enabled
and active flags, material slot order, MeshFilter identity and raw hashes.
Expandable records distinguish a selected target identity, a witnessed external
CAB whose target is outside the selection, an unwitnessed external slot, an
ambiguous physical target, a missing MeshFilter and a null reference. PathIDs
remain decimal strings. Search `MeshRenderer` / `渲染组件` or `material slots` /
`材质槽` with Collision enabled to find these records.

The component projection alone does not apply materials to the collision viewer,
reconstruct render geometry, claim live drawing or infer other Renderer coverage. Optional
renderer admission/projection/snapshot failures clear only renderer labels,
retaining owners, Model sources, collision assemblies and runtime evidence.
Final base scene/Mesh source failure still revokes all authored claims. The
authored publication stage revalidates this receipt without extracting anything
or requiring a live capture; raw-format conclusions belong to the Unity-assets
game-data topic.

Optional `renderResourceReceipts` selects independently admitted complete
serialized-directory and resource scopes. The authored publisher recomputes
actual external-slot joins, exposes exact material names and stored-field JSON
downloads, and publishes neutral Mesh/LOD assembly OBJs through the `StoredRender`
source root under `webui/data/assets/stored_render/`. Material documents retain
UV-set indices and decimal object identities. They are Assets-owned evidence
files; this stage does not write Data's object store. Mesh previews use source
coordinates; assemblies apply the stored root/descendant TRS. LOD buttons select
stored ordinal membership, never a claimed camera-selected level. Unsupported
static-batch projection and selected missing surfaces remain counted.

The existing collision preview/download stays available. Neutral render previews
retain UV0 but do not apply materials; their source documents retain UV1 too.
Assembly normals are generated by the viewer rather than incorrectly transformed
under nonuniform TRS. Additional vertex streams, animation, material appearance
and world placement remain explicit gaps. Resource failures restore the admitted
component-only labels, remove render artifact links/source root and expose a
scoped diagnostic; owners, Models, collider assemblies and runtime evidence keep
their independent gates.

Stored-render v2 and Material-document v2 add exact-source Texture2D mip-zero
PNG links. Expand a material's stored textures to see bounded thumbnails, the
original property/name, UV set, tiling/offset, block format, stored mip count and
colour-space enum; the full Material JSON retains sampler fields. Clicking a
thumbnail opens its full decoded image. These previews retain raw decoded
channels with an export-coordinate vertical flip, not shader appearance.
Mesh/LOD views stay neutral. Texture decode failure keeps those neutral surfaces
and stored material references available and records a scoped diagnostic.

Each stored Material download also exposes lazy Shader analysis details from
`data/assets/shader_analysis/index.json`. The independent sidecar binds exact
physical Shader identity/raw hash to an unchanged published Material artifact;
the frontend also requires that artifact's descriptor hash to match. Missing or
stale bindings show a scoped unavailable message. The panel displays the Shader
name, stored valid/invalid keywords, stored passes and a conditional compiled
program shortlist, with a complete analysis JSON download. Additional engine
keywords are allowed; undeclared valid keywords are visible and prevent a
shortlist. This does not renew older renderer admission or establish runtime
pass selection, resource binding or material appearance. Neutral Mesh/LOD
previews retain their existing evidence boundary.

Shader-analysis sidecar v3 separates explicit numeric Material values from
unoverridden Shader declarations and shows conditional per-pass parameter-table
resource names and constant-buffer offset alternatives. The named table entry
does not establish an instruction read, upload or live binding. Stored value
and per-pass lists expand independently to keep large material schemas usable.
An independent compiled-input section now counts conservative static instruction
references within the same conditional candidate cohorts, separately by VS/PS.
Resource reads and named field-offset alternatives remain distinct from the
parameter declarations. Complete register joins, programs with dynamic indices,
anonymous byte reads and gaps stay visible. This is compiled-use evidence,
without runtime selection or execution. Unsupported/malformed sidecars remain
unavailable. Neutral and raw-channel previews keep their previous boundaries;
the saved graphics examples have no retained texture-content join to this
selection and do not authorize game-equivalent shading.
Assets with recovered renderer/material evidence place the inspector at full
width below the preview, so the expanded field/reference lists remain readable.

Stored texture inspection is an explicit diagnostic view on one exact referring
MeshRenderer material slot. Its generated OBJ submesh ordinal and complete declared UV channel
select the target surface; other slots remain neutral. Mesh/PNG hashes precede
rendering, and model cache geometry remains immutable. RGB/R/G/B/A views preserve
decoded channels, including RGB beneath zero alpha, with stored UV scale/offset
and wrap modes. Only decoded mip zero is used; trilinear storage receives
bilinear inspection at that level. No Material tint, normal reconstruction,
multi-layer combination, game lighting, transparency or colour conversion is
applied. Missing UV sets, unknown sampler modes and backend restrictions remain
unavailable. The reconstruction lab's source/native transport and partial-shader
boundaries were used as reference, not as evidence of prefab visual parity.

UV1 inspection uses `data/assets/mesh_uv/index.json` with independently admitted
Mesh bodies. The publisher reproduces the prior UV0 OBJ byte-for-byte before
replacing only texture coordinates with the stored UV1 channel. The lazy
`StoredUV` v2 source root binds by original Mesh artifact/body hashes and
stored-render publication root, so changed UV1 cannot reuse an unchanged UV0
artifact across publications; it never changes
the existing collision/renderer index. Absent channels and stale projections
remain unavailable, and stored UV-set selection is still a diagnostic choice
instead of proof of effective shader sampling.

OBJ WebGL previews preserve face UVs, authored normals, and `usemtl` draw
ranges. An OBJ without `usemtl` uses a material only when its published links
have one distinct material name; multiple candidates remain neutral. Linked
Unity material relations supply base textures, tint, alpha testing and blending.
Missing UVs keep the affected range untextured. These name-based preview links
do not prove runtime renderer ownership; the software fallback stays untextured.

Alpha-test queue 2450 is depth-writing cutout geometry, not alpha-blended
transparency. Treating it as transparent with a default disabled depth write
made rear rabbit surfaces draw over the front. The Assets material projection
keeps queues through 2500 opaque unless an explicit surface setting selects
transparency, while retaining alpha clipping (including `_EnableAlphaTest`).
This follows [Unity's queue boundary](https://docs.unity3d.com/2023.2/Documentation/Manual/built-in-rendering-order.html).
The WebGL viewer resets depth writes before clearing and drawing opaque/cutout
groups; transparent groups retain their own published depth setting.
Transparent, non-additive groups with depth writes disabled sort their
triangles back to front in camera space as the user orbits. File-order drawing
made rear surfaces appear over front surfaces in
`P_fxbat_lizhiyan_01_widget_01_start`: its effect material disables depth
writes, so a correct depth test alone cannot order its overlapping faces.
Sorting stays within each material range and retains authored render-queue
priority; it does not reproduce dissolve shaders or solve intersecting
transparency across materials. Depth-writing, additive and Model only draws
retain their original indices. The expanded-vertex WebGL fallback uses the
same order, with one draw per sorted triangle.
`build_assets --publish material-appearance` refreshes existing Material
appearance from the selected Unity store without rescanning media or collision
evidence. It retains texture/model joins and aborts on missing documents or a
concurrently changed publication; adding new links needs the broad index build.

WebGL material appearance also applies opaque base tints, keyword-enabled
CharacterNPR avatar colors, and enabled emission color/brightness/map. NPC ear
materials share palettes across boy/girl meshes: `_CUSTOMIZE_AVATAR` base maps
encode red intensity and green/blue palette masks, so displaying their raw RGB
produces false neon colors. The preview mixes the three saved customization
colors before lighting. Angel halos use `_EMISSION`; dropping it makes the
halo gray. Unavailable emission maps and UV-less ranges stay non-emissive.
These static approximations do not reproduce game lighting, bloom, animation,
or runtime avatar overrides, and material-name links remain preview candidates.

Houdini VAT effects can have nearly collapsed triangles in their stored mesh.
For `P_fxbat_endminf_relax_sp_03`, the source MeshFilter points to the idle-rock
VAT mesh and its renderer points to `M_fx_endminf_idle_rock_01`. The Material
sets `_EnableHoudiniVAT` and references `_PositionTexture`; the static viewer
does not evaluate that vertex deformation. A focused installed-source decode
matched the exported FBX's vertex coordinates (with X reflected) and triangle
indices (with winding reversed), and the actual viewer parser retained the
triangles with the effect mesh visible. Invisible surfaces in this case do
not establish missing face indices or a mesh-visibility filter failure.
This comparison establishes agreement between the decoded Unity mesh, FBX
conversion and viewer; it is not an independent proof of the Unity byte
decoder or of the shader's runtime output. The maintained conversion is in
`tools/AnimeStudio/AnimeStudio.Utility/ModelConverter.cs`; FBX parsing and
static placement are in `webui/assets.js`.
The Model only preview switch disables material appearance and uses opaque
geometry in the chosen model color. It does not supply VAT deformation.

`Att_widget_lizhiyan_cat_postmodel` has a separate export-completeness gap:
its Persistent prefab declares skinned body (`_03`), secondary (`_04`) and
fur renderers. The inspected publication retained only fur geometry at two
LODs while leaving the other renderer transforms and tail bones in the FBX.
The body and secondary mesh sources live in StreamingAssets; the updated
LOD-zero fur source lives in Persistent. A focused two-layer dependency-map
probe recovered the missing body and secondary geometry. Explicitly including
the fur bundle offset also retained the updated fur. This establishes that a
successful Animator output does not prove all renderer mesh references resolved;
conversion admission still needs a renderer-reference completeness check. The
viewer cannot restore missing FBX geometry, and VAT support does not address
this dependency-loading gap. The maintained dependency loader is
`tools/AnimeStudio/AnimeStudio/AssetsHelper.cs`. The maintained wrapper now
supplies the other layer's CABMap as an absent-name fallback, and the loader
keeps dependency offsets in filtered input chunks and normalizes source paths.
A focused export using the ordinary maps recovered all declared mesh parts;
the viewer parser accepts them and exposes body, secondary and fur at LOD zero.
The inspected cat export has been replaced in Unity.sqlite and its Assets
index row refreshed after the installed-build freshness gate passed. Other
previously published FBX files need re-extraction to acquire omitted geometry.

FBX mesh controls classify `eyesshadow`, `hairshadow`, and character-context or
terminal `hs` labels as shadows, alongside shadow proxies. An `hs` token by
itself inside an ordinary machine or container name is insufficient: names such
as `hs_machine` and the ancestor `HS File` previously hid valid surfaces, even
whole prefabs. Character `actor`/`npc`/`chr` contexts retain their hair-shadow
classification. Shadow model ancestors and shadow material names also supply
this preview classification. `vfxpart` names count
as VFX alongside FX/effect names. Shadows start hidden; VFX starts hidden when
ordinary meshes exist and remains visible in effect-only prefabs. These name
rules organize the preview and do not establish runtime renderer ownership.

The FBX viewer bakes connected skin weights against the stored bone hierarchy
for skinned meshes, and model transforms for rigid meshes. A binary cluster's
`Transform` already maps mesh coordinates into the bind bone's space (see
[Blender's FBX importer](https://github.com/blender/blender/blob/main/scripts/addons_core/io_scene_fbx/import_fbx.py));
applying its current bone world matrix produces the exported static pose
without applying the mesh placement twice. `Total1` retains the unweighted
fraction and `Normalize` normalizes weighted points; uninfluenced points keep
their mesh placement. Unsupported skin modes or invalid influences reject the
skin bake and use the existing FBX summary/proxy fallback. The rabbit
prefabs require this skin bake because their mesh coordinates differ from
their stored skeleton pose. The Animation-stack count remains metadata, not
animation playback. Ultimate assets
often use `ult` or `ultskill` rather than `ultimate`, and appear as separate
effect, camera or model pieces. AnimationClip `.anim` documents belong to the
Data store browser, not the Assets media list. Complete FBX indexing therefore
does not establish complete skill presentation or its timed composition.

The Ardelia sheep horn issue is material whiteout, not missing FBX geometry.
Every source LOD's vertex coordinates and triangle indices agree exactly with
the published FBX after the exporter's X reflection and winding reversal.
The prefab's renderer and LOD references account for those meshes; their
weapon-style internal names do not imply that the sheep body is absent.
Strong stored emission saturates the preview's display range and obscures the
pink horn texture. Assets therefore previews base textures without emission
by default, with a separate `Show emission` control retaining the authored
values. This applies to all model draw groups, including OBJ and admitted
stored-render previews. Disabling emission preserves tint, avatar palette,
alpha clipping, transparency, mesh selection and skin pose. `Model only`
temporarily disables the emission control without losing its selection.
This display correction does not certify other FBXs against their source
renderers or reconstruct the game's HDR post-processing and bloom.

OBJ and FBX initial framing use the normalized bounds' enclosing sphere and the
viewport's smaller angular dimension. A cube-sized model can exceed the old
fixed camera's view after orbiting, so fitting only the largest unrotated axis
could crop valid surfaces. The bounds-aware default retains user zoom/pan and
is shared by WebGL and the software view. FBX bounds still follow the parts
shown initially, excluding hidden LODs and proxies. Flat meshes normalize to
their actual largest nonzero extent; a zero depth must not introduce a synthetic
unit dimension and shrink a small plane. Fully degenerate bounds retain a
finite fallback. This changes inspection framing, not source mesh coordinates.

The model sweep also separates missing exports from hidden preview parts.
Independently authored body and weapon parts may have different lowest stored
LOD numbers. A single global minimum can therefore show a weapon while hiding
the whole body. FBX previews use `Best per part` by default when ordinary part
families have different available minima. Families follow normalized LOD names
within the exact owning hierarchy branch, preserving distinct same-name
instances. Numeric LOD buttons remain available. This is an inspection preset,
not proof of authored LODGroup membership or the game's selected LOD; stored
render assemblies retain their separate exact LODGroup-PPtr contract.

Focused Animator repairs are staged against exact source selection and expected
renderer counts before publication. The publisher backs up changed documents,
replaces only validated FBXs and their empty markers, refreshes their size/hash,
scene-root and content-group fields, and preserves unrelated Assets sidecars.
An index `mr` record can expose an incomplete source-geometry count; the viewer
accepts it only when its hash equals that file's current `h`, with bounded integer
counts. It describes missing referenced source data, not runtime invisibility.
An empty marker with no declared ordinary Mesh renderer remains an empty export
record; custom/procedural renderer components are recorded separately and are
not classified as intrinsically geometry-free game objects.

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

Assets PNG previews offer an opt-in `Ignore alpha / RGB` control. It sets alpha
to opaque on decoded pixels before browser bitmap conversion, preserving RGB
hidden by zero alpha. Original downloads and exported files stay unchanged;
this inspection mode does not reconstruct material shader appearance.

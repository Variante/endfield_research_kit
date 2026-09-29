# Unity assets: identity, and semantic bindings

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, Unity assets lane.** The `Bundle` block's payloads and what they can
be bound to. This topic owns semantic bindings between exported Unity assets and Story, characters, gameplay entities, world objects, audio, and video. The Assets page only inventories browser-visible files; AnimeStudio only extracts them.

Extraction correctness belongs to
[`extraction_pipeline.md`](extraction_pipeline.md); page publication belongs to
[`../webui/assets.md`](../webui/assets.md). This file owns the identity rules and
the binding evidence order that several pages and the source graph reuse.

## Current status

Asset extraction and discovery are strong: the project indexes every asset
kind, resolves many PathID-backed dependencies, and connects authored gameplay
or Story records to asset candidates with explicit provenance. The main gap is
semantic binding. Exporting an object does not prove its live prefab
composition, selected material variant, animation state, effect activation, or
placement time.

Every exported Unity type is already in a decoded or standard format:
AnimationClip as YAML with its curves and keyframes; Animator, AnimatorController,
AnimatorOverrideController, PlayableDirector, Material, MonoBehaviour and
TextAsset as JSON; Mesh as FBX; Texture2D as images; Sprite as crop documents.
No binary framing is left to recover here, which is why MonoBehaviour
*semantics*, not parsing, is what this file records as open.

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
unique binding; keep bindings at `(source root, CAB, PathID)`.

## Bundle identity and dependency joins

Each join below is a stored container relationship; none establishes Unity
object ownership, load order, or runtime use. The gates and their full readings
are `scripts/game_data/cabmap.py`, `bundle_cab_dependency_corpus.py`,
`bundle_cab_exceptions.py` and `bundle_external_identity_corpus.py`; the
manifest fields are proved by `scripts/game_data/contracts/bundle_manifest_native.json`.
Per-build counts and source hashes are in `reports/animestudio/`.

- **Container location is exact.** The VFS outer ledger verifies each selected
  logical Bundle's bytes and the inner ledger its Unity structure; joining the
  Persistent CABMap's source root, chunk path and offset to those spans gives
  every added or changed Bundle file one named CAB.
- **An AssetMap row is source containment, not an object check.** Some new
  bundles have no AssetMap row although their CABMap offsets and inner
  structure verify: an AssetMap coverage gap, never an empty container. Select
  StreamingAssets fallback rows by exact source chunk **and offset
  containment** in a verified current Bundle span; chunk membership alone
  cannot promote the fallback AssetMap to current overlay evidence.
- **Path/physical-Bundle disagreements are dependency placements.** Every
  Persistent disagreement and nearly every StreamingAssets one places the
  physical Bundle in the path's listed Bundle's `directDependencies`, with the
  reciprocal reverse entry.
- **The CAB graph matches the manifest.** Every projected external CAB is in
  the manifest direct list (plus a small manifest-only residual that the native
  loaders can consume, cause unproved); the reverse list is its inverse and
  `dependencies` its transitive closure. Unselected CAB targets stay unresolved.
- **`unity default resources` is an authored serialized identity**: an indexed
  pointer through that external reaches the `Capsule` Mesh in the exact-name
  installed Resources file. A second, CAB-shaped external stays unlocated. The
  resolver binding still needs a native or live trace.
- **AssetMap labels from before the ordinal-interning fix are historical.** The
  apparent no-dependency fallback residual was an exporter-label bug:
  `StringCache.Get` in AnimeStudio's `AssetMap.cs` interned by CRC32 alone, so a
  same-CRC path could replace the authored key; every corrected key (the
  Bundle's own `AssetBundle.m_Container` key) maps to that Bundle in both
  manifests. A smaller UI subset's old labels have a *different* CRC from the
  raw keys, so their mislabel mechanism remains open.
- **The no-AssetMap group is parse-only classes.** A ledger-matched dump and an
  opt-in metadata map agree on every `(logical file, CAB, type, PathID)`: mostly
  scene bundles (`AssetBundle`, `GameObject`, `Transform`, `PlayableDirector`),
  the rest controllers or avatars, each `AssetBundle` holding one authored
  `m_Container` path (level sequences, cutscene transitions, dialog timelines,
  UI model controllers, one avatar). All six classes are parse-only in the
  normal CLI configuration, so `AssetsHelper.BuildAssetMap` never emits them:
  that explains the gap without claiming empty bundles or ruling out others.

## Refresh

```bat
.\export.bat assets --from-game
.\export.bat --from-game
.\export.bat debug --from-game
python -m scripts.webui.assets.build_assets
python tools\endfield_source_graph.py build
```

A page run exports only the Unity classes its build tasks read
(`scripts/webui/pages.py`); `debug` exports every class. Primary outputs:
`<export root>/game/{Unity.sqlite,Unity/<Type>/,Audio/}`,
`webui/data/assets/{index,gameplay_refs,story_media,videos}.json`,
`webui/data/lang/<LANG>/audio/{index,events,media}.json`,
`webui/data/lang/<LANG>/gameplay/sound_effects.json`, `reports/assets/` and
`reports/source_graph/`.

## MonoBehaviour: from anonymous objects to named fields

Every MonoBehaviour decodes against an exact serialized TypeTree, but the export
carries only an anonymous `scriptPathId`: `m_Script` points into a MonoScript CAB
outside the export scope. The `scripts/game_data/monobehaviour/` modules close
that in steps, each measured; their docstrings hold the full rules and the
commands are in `scripts/README.md`.

| Module | Establishes | Does not establish |
| --- | --- | --- |
| `census.py` | objects sharing a `scriptPathId` share one layout; the corpus collapses to a few hundred classes | any name |
| `monoscript_catalog.py` | `scriptPathId -> class` from the one MonoScript CAB every `m_Script` reaches | what an instance owns |
| `script_names.py` | an independent layout-to-IL2CPP-class check | a class that serializes nothing, or which subclass of a field-contributing base |
| `field_semantics.py` | per field: declared TypeTree type beside observed occupancy, and PPtr tiers `exact`/`container_only`/`contradicted`/`unresolved` | when a class runs, or that a filled reference is reached |
| `table_keys.py` | string fields whose values are keys of an exported Table | that a consumer reads the field as a key |

A named class is an exact identity for the *script*, and a field row describes a
layout and its occupancy; ownership and runtime use still follow the evidence
order. Conclusions worth carrying:

- **Resolution.** PathIDs are measured unique across this export, and no CABMap
  prediction is contradicted where the target is exported. Most references are
  `container_only` (their GameObject, Transform or MonoScript targets are never
  exported); every filled reference field names a container through the
  ordered-dependency rule ([`containers_cabmap.md`](containers_cabmap.md)), with
  no fallback to a global PathID match. A field null in every object, or
  holding one value in every instance (about a third of all fields), records an
  authored default, not configuration.
- **Material links are uncheckable.** Material, TextAsset and
  AnimatorOverrideController carry no provenance, so Material texture links rest
  on a global PathID match the export cannot check
  ([`extraction_pipeline.md`](extraction_pipeline.md) owns the exporter gap).
- **Bindings at scale.** `Beyond.UI.UIImage.imgRefPath` carries authored asset
  paths (`Assets/Beyond/Arts/UI/Sprites/...`), the first rung of the evidence
  order, and its `m_Sprite` is filled in most objects and names its container.
  Timeline clip fields are the animation binding at scale:
  `AnimationPlayableAsset.m_Clip` is filled in nearly every object and
  `DialogNPCMorphPlayableAsset.m_Clip` in all. The `autoBindingPath` family
  (`DialogSkeletalMorphTrack`, `DialogMuteAutoBlinkTrack`, `DialogLipSyncTrack`)
  is a scene-hierarchy binding that names the character prefab and its
  `FacialMorphCtrlGO`, and `CutsceneRootComponent._director` resolves to a
  `PlayableDirector` at the exact tier in every object.
- **Table keys.** Numeric keys are refused outright, and a `key_of` needs every
  observed value in one table (`UIStateController.states[].stateName` coincides
  with a factory table on one value of 61 and is not a key field). Story's
  strongest bindings: `DialogLipSyncPlayableAsset._trunkId` and
  `DialogTrunkPlayableAsset._trunkId` are `DialogTextTable` keys,
  `DialogOptionPlayableAsset.options[]._optionId` a `DialogOptionTable` key,
  and `UIButton.hintTextId` a `TextTable` key, each over its full value sample.
  Grade a partial field by its best table's coverage, not by "in another table
  versus in none": only a dominant table (`mostly_key_of`) makes exceptions
  worth chasing. `UIText._textId`'s are mostly `PH_*` placeholders;
  `SubtitlePlayableAsset._textId`'s are cutscene and FMV subtitle ids that
  resolve nowhere, a Story finding owned by
  [`../webui/story_recovery.md`](../webui/story_recovery.md).

## Controllers and Sprites

`m_Controller` is structural, not an opaque blob: layers, state machines, state
and transition constants, blend-tree nodes, parameter ids and `m_TOSData`
transform paths all decode, so the controller-to-clip chain a character render
needs closes from the export alone, at the exact-serialized-object tier. For
example `P_actor_endminf_ui_overview_01` is one layer, one state machine and
one entry-selected state playing `A_actor_endminf_ui_overview_02`, a 60 fps
uncompressed clip with position, rotation and scale curves, and the
`ui_overview_start`/`_loop`/`_to_*` clips the lab's targets name all exist.
Runtime state selection is not observed.

A Sprite is exported as a crop of its Texture2D (`endfield.sprite-crop.v1`)
that reproduces AnimeStudio's image pixel for pixel; the crop steps, evidence
and texture PPtr join are in `scripts/game_data/sprite_crops.py`. Name matching
is not identity.

## Current strengths

- WebUI asset and Story-media indexes, renderable asset-entity grouping,
  material/texture/shader/controller/animation/audio/video links, exact
  character post-model enumeration and baseline prefabs, and selected static
  world placements and gameplay/entity associations.
- Gameplay-to-image/model links and playable Wwise-event media candidates for
  projectiles, character skills, and bounded enemy ownership; debug-only audio
  semantics keep Event identity, media id, and each physical
  `(storageRoot, relativePath)` occurrence separate.
- `chen` and `chenpast` are separate identities (`P_actor_chen_*` versus the
  independent `S_npc_major_chenpast_*` mesh family, with no shared model
  PathID), so folding them is a display-layer error.
  `webui/overrides/character_merges.json` is applied in the browser, never by a
  builder, so a merge there overrides this for every reader while generated
  data stays correct and the contradiction is invisible in the exported JSON.
- NPC CPU-animation templates have a native-gated path rule
  (`npc_animation_template_native`) joined to effective source/CAB/PathID and
  declared base and blend-tree clips; a validMontages tag describes authored
  hierarchy, not runtime montage selection or Character Info ownership.

## Remaining gaps

- Integer fields that are table ids cannot be identified from values alone: a
  numeric key belongs to one table only 0.5% of the time. Naming them needs a
  consumer, not a wider join.
- The `mostly_key_of` rows are the open list: fields that are a table's key
  apart from a few ids the tables do not hold. Each remainder is either a
  second key space or content that does not ship; the report does not choose.
- **How much is unexplained is a range; quote the range, not the floor.** Of
  the game-specific named classes, 382 (295,845 objects) have no
  class-specific signal when any non-null reference counts; requiring a
  reference to land on something named (a named target class or an exported
  asset type) raises it to 662 classes (331,986 objects), 71% of the set.
  `Beyond.UI.UIActionKeyHint` has thirteen filled references and none lands on
  a name. Three rules decide the count and must not be relaxed on re-measure:
  the four universal fields (`m_GameObject`, `m_Enabled`, `m_Script`,
  `m_Name`) are excluded first; public engine namespaces are excluded by
  prefix, so game namespaces such as `ScriptAnimation.*` stay in; and the
  unnamed-script class stays in. A Table-key or path-shaped string field also
  counts as signal.
- Which classes a page actually consumes (a question about consumers, not
  layouts); exact runtime prefab assembly, entity-to-renderable ownership, and
  modular NPC and VFX composition; world visibility/spawn policy.
- Material keyword/pass/queue selection and runtime overrides; native texture
  descriptors and mip payloads outside validated families.
- `InitChunkData` proves entity ids, names and matrices but currently exposes no
  prefab Source+PathID/hash field. The Map page's generic entity-name to Mesh
  family join therefore remains a presentation candidate, even if the Mesh
  object itself has an exact AssetMap source/offset/PathID. A current example
  is a world instance named `P_prop_com_plane+1_001_01` whose selected Mesh
  object is cataloged under a dialog-timeline prefab: the shared family name
  alone cannot establish that the world instance uses that prefab or Mesh.
  A targeted parse of that dialog actor prefab did recover its AssetBundle
  root GameObject and reciprocal Transform hierarchy, with direct MeshFilter
  PPtrs resolving through the ordered CABMap dependency to the candidate Mesh.
  That closes prefab-to-Mesh identity inside the actor prefab, but no serialized
  source identity links the streamed entity to this prefab. The Unity object
  store contains AssetBundle documents for the chain, while its published class
  set has no GameObject, Transform, MeshFilter, or MeshRenderer documents;
  those built-in objects required a targeted installed-bundle parse. A runtime
  observation from the streamed entity id to a prefab resource path or root
  source CAB+PathID would close the remaining selection gap.
  Current runtime capture profiles do not observe this pair. The reviewed
  Streaming native rows remain anonymous at the relevant edge, so hooking a
  nearby scene read and correlating by name, timestamp or position would not
  establish ownership. A capture hook needs a validated same-call entity id
  and selected prefab identity, authenticated against the installed native
  inputs and emitted with a bounded completeness receipt.
  Only the separate level/HLOD/grid/cluster hash contract closes HLOD Mesh
  identity; generic objects still need a streamed entity-to-prefab selection
  relation or a direct entity-to-renderer/Mesh runtime observation.
  A bounded current-build native probe rejects the generic
  `FlatBufferConvertContextV2::ConvertAssetFromImpl_Injected` internal call as
  that Map hook: it takes a conversion context and property key, reads the
  context's packed property table, and returns a Unity object pointer. A
  separate named getter reads the context's entity-name string, but the
  reviewed native path does not bind the Init row's ID/name column, a prefab
  root, and a source CAB+PathID/resource path at either call boundary. The
  managed wrapper's one literal direct caller does not supply the missing
  identity pair; other dispatch routes remain unexcluded. A checked runtime
  entity-construction caller/selection ABI is still needed before a dedicated
  capture profile can be built or a game session requested.
  A further selected-build probe of the Init group branch found an ID-keyed
  runtime map: each slot-6 numeric ID can be paired with an eight-byte value
  from a per-group runtime vector. That value's meaning is anonymous, and the
  conditional branch carries no prefab or renderer source identity. A bounded
  follow-up traced the first selected new-record consumer: the second root's
  field-3 ID is used to look up that map, the value is passed to a scope
  setup and copied into an anonymous child record. The scope puts the first
  root's selected row field-3 table and field-0 string into a conversion
  context, then forwards the map value to a dynamic callback. The selected
  group loader constructs the value as a 32-bit descriptor-slot index plus
  a 32-bit counter, rather than a Unity object pointer. The selected default
  callback uses the low 32 bits to index an anonymous context table and then
  select a 576-byte group row. The immediate helpers use the row's bit masks,
  stride and data pointer to resolve anonymous fields. The callback takes up
  to three eight-byte field values, interns each nonzero value as an opaque
  key, and appends 24-byte external-asset request records containing the
  original key, a kind value, and its local index. A named native conversion
  call appends the same record shape. A checked consumer of the matching native
  context field walks a 24-byte request vector and deduplicates its opaque
  keys into another local table; this consumer does not resolve a source path,
  Unity object, or CAB+PathID. Its execution for the target scene is unproved.
  The selected manager constructor receives the group table pointer from its
  owner and stores both a copy of that pointer and the address of the owner's
  pointer field. Thus the group-loader table and the callback context's first
  pointer alias at construction. A later mutation of that owner field or
  either manager field is not excluded by this static trace, and there is no
  live pointer receipt. In the exported target pair, both roots carry the same entity
  ID at the selected ordinal;
  this remains a serialized pair witness, not a runtime load receipt. The
  selected callback's runtime override state and the external-asset request
  consumer have no proven edge to a prefab source identity. A hook at the
  current ID lookup or field-intern call would record only an ID plus opaque
  numeric state; it is not yet a useful prefab-selection capture. A dedicated
  capture hook or WebUI join still needs that keyed resource-selection edge.
- Animation/effect activation and controller execution; broader exact
  audio/video trigger ownership, runtime-selected Wwise switch/random media,
  and stronger inferred skill/enemy sound ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

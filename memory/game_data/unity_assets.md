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
- Animation/effect activation and controller execution; broader exact
  audio/video trigger ownership, runtime-selected Wwise switch/random media,
  and stronger inferred skill/enemy sound ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

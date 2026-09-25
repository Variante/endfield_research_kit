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

Asset extraction and discovery are strong. The project can index images,
models, materials, textures, shaders, animations, effects, audio, and video;
resolve many PathID-backed dependencies; and connect authored gameplay or Story
records to asset candidates with explicit provenance.

The main gap is semantic binding. Exporting an object does not prove its live
prefab composition, selected material variant, animation state, effect
activation, or placement time.

## Refresh

```bat
.\export.bat --from-game --with-assets
.\export_assets.bat
.\export_assets.bat --from-game
python -m scripts.webui.assets.build_assets
python tools\endfield_source_graph.py build
```

Asset modes, from narrowest to broadest, are `--focused-assets`,
`--default-assets`, and `--debug-assets`.

Primary outputs:

```text
<export root>/game/Unity.sqlite
<export root>/game/Unity/<Type>/
<export root>/game/Audio/
webui/data/assets/index.json
webui/data/assets/gameplay_refs.json
webui/data/assets/story_media.json
webui/data/assets/videos.json
webui/data/lang/<LANG>/audio/index.json
webui/data/lang/<LANG>/audio/{events,media}.json
webui/data/lang/<LANG>/gameplay/sound_effects.json
reports/assets/
reports/source_graph/
```

## The MonoBehaviour corpus is a few hundred classes, not a million files

MonoBehaviour is the largest exported type by a wide margin -- more objects
than every other exported Unity type combined -- and every one of them decodes
against an exact serialized TypeTree. What the export does not carry is the
class name: `m_Script` points into a MonoScript CAB outside the WebUI export
scope, so each object resolves only to an anonymous `scriptPathId`.

Two facts make that tractable, and both are measured rather than assumed:

- **A script PPtr is a class key, and the corpus collapses onto it.** Objects
  sharing a `scriptPathId` share one serialized layout, so the file count
  reduces to a few hundred distinct classes.
  `scripts/game_data/monobehaviour/census.py` measures the collapse and records
  each class's layout, object count and source containers.
- **One MonoScript container names all of them**, and it is
  `CAB-5f527d7b7706baccdad9f794cf46420c`, holding the ~1,000 MonoScripts that
  carry `m_ClassName`, `m_Namespace` and `m_AssemblyName` outright.
  `scripts/game_data/monobehaviour/monoscript_catalog.py` parses the dump into the
  `scriptPathId -> class` table. Two independent routes name that CAB rather
  than one: every resolved `m_Script` in the corpus points at it across both
  VFS roots, and it is separately the most depended-on container in both
  CABMaps, at dependency slot 1 in 99.96% of the streaming CABs that reference
  it while declaring no dependencies itself. Resolve its chunk path through the
  CABMap at the time of use rather than recording it -- it sits in block
  `0CE8FA57`, which ships a *different chunk filename in each VFS root*, so a
  recorded literal picks one root and rots.

A second, independent route exists and is worth keeping as a check rather than
a fallback. Unity serializes a subset of a class's IL2CPP field declaration
chain and never reorders it, so a layout must be an ordered subsequence of that
chain, and the class that declares the layout's last field is the most-derived
one. `scripts/game_data/monobehaviour/script_names.py` runs both and reports
their agreement. Two limits are structural, not defects: a class that
serializes nothing is invisible to the layout route, and a subclass adding no
serialized field writes a byte-identical layout, so layout evidence names the
field-contributing base and must state the alternatives instead of choosing.
The script PPtr settles both.

A named class is an exact identity for the *script*. It does not establish what
an instance owns, when it runs, or that anything reaches it at runtime; that is
still the binding-evidence order below.

## What a named class owns is measured per field, not inferred from its name

`scripts/game_data/monobehaviour/field_semantics.py` sweeps the whole corpus a
second time and records, for each of the 44,844 flattened field paths across
the 1,045 classes, the declared TypeTree type beside what the 1.35M objects
actually hold there. Declaration and observation are kept apart because they
answer different questions: a declared `PPtr` *is* a reference field whether or
not anything fills it, and 1,029 of the 4,931 declared reference fields are
null in every object in the corpus. So is a third of the corpus's fields: over
16,000 hold one single value across every instance, which is authored default,
not configuration.

**A PathID resolves to exactly one exported object in this export, and that is
measured rather than assumed.** 1,874,804 exported objects carry 1,874,804
distinct PathIDs with no collision in any type directory. Resolution is still
tiered, because uniqueness inside the export does not make a cross-file PPtr a
proven binding:

- `exact` -- the container the CABMap rule predicts is the one the resolved
  file names. That is source root plus PathID, the second rung of the evidence
  order below.
- `container_only` -- the container is named and nothing exported sits at that
  PathID to check it against. This is most of the corpus, because most
  MonoBehaviour references point at GameObjects, Transforms and MonoScripts the
  export scope never writes. It is weaker than a verified row and much stronger
  than an unresolved one, and it is the tier that used to read as nothing.
- `contradicted` -- the prediction and the target disagree. None in the corpus:
  4,998 of 4,998 checks agree. The one contradiction this produced before the
  root selection was fixed is recorded in
  [`containers_cabmap.md`](containers_cabmap.md), because how little it showed
  is the lesson.
- `unresolved` -- the CABMap could not answer. The sweep never falls back to
  matching a PathID globally.

**A cross-file reference is no longer structural.** `m_FileID` indexes the
referrer's ordered CABMap dependency list at `m_FileID - 1`; the rule, its
measurement and the two-root trap it depends on live in
[`containers_cabmap.md`](containers_cabmap.md). Every one of the 3,902 filled
reference fields now names a container, where before the rule only 1,205 did
and 2,697 resolved to nothing.

**The rule reaches only the types that record where they came from**, and
Material is not one of them. Material, TextAsset and AnimatorOverrideController
carry no provenance in the export, so their cross-file references -- including
all 243,124 material-to-texture links, 97.7% of them cross-file -- still rest
on a global PathID match that cannot be checked. That is an exporter gap, and
it is stated in [`extraction_pipeline.md`](extraction_pipeline.md).

Three results worth carrying, all at the top of the corpus by object count:

- **`Beyond.UI.UIImage.imgRefPath` carries authored asset paths**
  (`Assets/Beyond/Arts/UI/Sprites/...`), which is the *first* rung of the
  evidence order rather than a PathID join. Its `m_Sprite` is filled in the
  large majority of 226,436 objects, and that reference now names its
  container.
- **Timeline's clip fields are the animation binding at scale.**
  `AnimationPlayableAsset.m_Clip` is filled in essentially every one of 188,970
  objects, and `DialogNPCMorphPlayableAsset.m_Clip` in all 9,082.
- **The `autoBindingPath` family is a scene-hierarchy binding, not a name.**
  The Dialog tracks (`DialogSkeletalMorphTrack`, `DialogMuteAutoBlinkTrack`,
  `DialogLipSyncTrack`) spell a transform path that names the character prefab
  and its `FacialMorphCtrlGO`, and `CutsceneRootComponent._director` resolves
  to a `PlayableDirector` at the exact tier in every one of its 1,284 objects.

Per-class and per-field rows belong to
`reports/assets/monobehaviour_field_semantics.json`; the command is in
`scripts/README.md`. A row there describes a *layout and its occupancy*. It
still does not establish when a class runs or that a filled reference is
reached at runtime.

## Which string fields are table keys, and why numeric ones cannot be

`scripts/game_data/monobehaviour/table_keys.py` joins the recorded field values
against the 724 exported tables' key sets. The join's whole shape comes from
one measurement: of 269,570 distinct keys, the 178,582 numeric ones are unique
to a single table **0.5%** of the time -- `"1"` is a key in 94 tables -- while
the 90,988 named ones are unique **90.5%** of the time. A numeric match
therefore names nothing and is refused outright; pooling the two would convert
a bounded candidate list into thousands of invented references.

Requiring *every* observed value to belong is what makes the rest hold up.
`UIStateController.states[].stateName` misses 59 of its 61 values and coincides
with `FactoryMachineCraftModeTable` on exactly one (`normal`); a
majority-match rule would have called it a factory key. Fields that match on
few values are reported and flagged rather than trusted, and a field matching
several tables keeps them all, because 9.5% of named keys legitimately belong
to more than one.

The bindings this establishes are strongest where Story needs them:
`DialogLipSyncPlayableAsset._trunkId` and `DialogTrunkPlayableAsset._trunkId`
are `DialogTextTable` keys, `DialogOptionPlayableAsset.options[]._optionId` is
a `DialogOptionTable` key, and `UIButton.hintTextId` is a `TextTable` key --
each over the full 64-value sample.

A match says the values are drawn from that key set. It does not establish
that any consumer reads the field as a key.

**A field no table fully covers is graded by how much its best table covers,
and that axis matters more than it looks.** The tempting split -- values in
another table versus values in none -- is the wrong one: `states[].stateName`
has 59 of 61 values in no table, and reading those as unresolved ids would
dress a single coincidental hit as evidence. It is simply not a key field.
Above a dominant share of 0.75 the field *is* that table's key with
exceptions, and only then are the exceptions worth chasing. That leaves 18
fields whose unresolved ids are a real queue, and the two largest are
different in kind: `UIText._textId`'s 13 are mostly `PH_*` authoring
placeholders, while `SubtitlePlayableAsset._textId`'s are cutscene and FMV
subtitle ids that resolve nowhere at all -- a Story finding, owned by
[`../webui/story_recovery.md`](../webui/story_recovery.md).

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
- Compact Gameplay-to-image/model links and playable Wwise-event media
  candidates for projectiles, character skills, and bounded enemy ownership.
- Debug-only audio semantics that keep Wwise Event identity, numeric media id,
  and each physical `(storageRoot, relativePath)` occurrence separate. Same-id
  files in different folders or language/shared scopes remain visible instead
  of being collapsed by filename stem.
- Exact character post-model enumeration and baseline prefab generation.
- `chen` and `chenpast` are separate identities: the playable `chen` row owns
  the `P_actor_chen_*` model family, while the historical NPC `chenpast` row
  owns the independent `S_npc_major_chenpast_*` mesh family; their exported
  model PathIDs do not overlap. The Characters builder keeps them as two
  records accordingly, so folding them together is a display-layer error, not a
  recovery conclusion. Note that `webui/overrides/character_merges.json` is
  applied by the Characters page in the browser and never by a builder: a merge
  entry there overrides this conclusion for every reader of the page while
  leaving generated data correct, so a contradiction between the two is
  invisible in the exported JSON.
- NPC CPU-animation templates have a native-gated path rule in
  `npc_animation_template_native`. The reconstruction audit joins the
  resulting asset path to effective source/CAB/PathID identity and declared base
  and blend-tree clips. A validMontages tag describes authored hierarchy, not
  runtime montage selection or Character Info ownership.
- Selected static world placements and gameplay/entity associations.

## The animation lane needs no framing work

Every exported Unity type is already in a decoded or standard format -- 101 GB
across 1.88M files, with AnimationClip as YAML, Animator / AnimatorController /
AnimatorOverrideController / PlayableDirector / Material / MonoBehaviour /
TextAsset as JSON, Mesh as FBX, and Texture2D / Sprite as images. There is no
binary framing left to recover here, which is why MonoBehaviour *semantics*,
not parsing, is what this file records as open.

`m_Controller` is structural, not an opaque blob: layers, state machines,
state constants, transition constants, blend-tree nodes, parameter ids and the
`m_TOSData` transform paths all decode. The chain a character render needs
therefore closes end to end from the export alone, at the exact-serialized-
object tier. Worked through for one character:
`P_actor_endminf_ui_overview_01` is one layer, one state machine, one state
with an entry-only selector transition and no state transitions, playing
`A_actor_endminf_ui_overview_02` -- a 60 fps, 5.883 s uncompressed clip with
position, rotation and scale curves over 435 keyframes. 3,285 Endminf clips
exist, including the `ui_overview_start`, `_loop`, `_to_equip`, `_to_skill` and
`_to_upgrade` set the lab's entrance-and-loop target names.

## Remaining gaps

- Integer fields that are table ids remain unidentifiable from values alone,
  and that is a property of the data rather than a missing tool: a numeric key
  belongs to one table only 0.5% of the time. Naming them needs a consumer, not
  a wider join.
- The `mostly_key_of` rows are the open list worth working: 18 fields that are
  a table's key apart from a handful of ids the tables do not hold. Each
  remainder is either a second key space or content that does not ship, and
  the report does not choose.
- **How much is unexplained is a range, and the lower bound flatters us.**
  Of 936 game-specific named classes, **382 (295,845 objects)** have no
  class-specific signal at all under the loose test, where any non-null
  reference counts. Requiring a reference to actually *land on something named*
  -- a named target class, or an exported asset type rather than another
  anonymous MonoBehaviour -- raises it to **662 classes (331,986 objects), 71%
  of the game-specific set**. The 280 classes between the two bounds hold
  filled references that resolve to nothing named:
  `Beyond.UI.UIActionKeyHint` has thirteen of them and not one lands on a name.
  Quote the range, not the floor: a filled reference is evidence that a field
  is a reference, and no evidence about what it means. Three rules decide the
  count and must not be relaxed if it is re-measured: the four universal fields
  (`m_GameObject`, `m_Enabled`, `m_Script`, `m_Name`) are excluded before
  anything counts; public engine namespaces are excluded by prefix, so game
  namespaces such as `ScriptAnimation.*` stay in; and the class whose script
  could not be named stays in. A string field joining a Table key set, or a
  path-shaped string field, also counts as signal.
- Which classes a page actually consumes is still open, and is a question about consumers rather than about layouts.
- Exact runtime prefab assembly and entity-to-renderable ownership.
- Material keyword/pass/queue selection and runtime overrides.
- Native texture descriptors and mip payloads outside validated families.
- Animation/effect activation and controller execution.
- Modular NPC and VFX composition.
- World visibility/spawn policy.
- Broader exact audio/video trigger ownership.
- Runtime-selected Wwise switch/random media and stronger inferred
  skill/enemy sound ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

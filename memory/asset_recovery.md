# Endfield asset recovery

This is the durable memory source of truth for finding, exporting, joining,
and interpreting Endfield models, entities, prefabs, materials, textures,
shaders, animations, effects, audio, and video as assets. Exporter mechanics
belong in `animestudio_recovery.md`; gameplay/table semantics in
`game_data_recovery.md`; Story placement in `game_story_recovery.md`; retail
character rendering in `character_render_and_animation_recovery.md`.

## Current conclusion

Asset extraction and discovery are strong. The repo can index exported media,
reconstruct many renderable `asset_entity` groups, resolve PathID-backed
material/texture/shader links, associate actors/weapons/world models with
assets, query animation/effect/audio/video consumers, and preserve source-root
provenance.

Semantic binding is still uneven. Exact table paths, prefab/component links,
PathIDs, asset-map relations, material dependencies, and controller references
are strong evidence. Normalized filenames and repeated visual-family tokens
are useful candidates but cannot by themselves prove runtime prefab
composition, material variant selection, object state, animation activation,
or playback order.

The practical goal is an evidence-first asset catalog, not a claim that every
gameplay id has one uniquely reconstructed renderable prefab.

## Refresh and current evidence

Use the root workflow rather than hand-running broad conversion:

```bat
.\export.bat --export-from-game --with-assets
.\export_assets.bat
.\export_assets.bat --export-from-game
python scripts\build_assets.py
python tools\endfield_source_graph.py build
```

Use the combined export when Story and assets both need installed-game data.
Use `export_assets.bat` when Story is current. `--webui-assets` is the lean
WebUI-referenced Texture2D mode; `--debug-assets` is for broad conversion and
diagnostic coverage.

Primary current artifacts:

```text
export_full/recovered/AnimeStudio-cli/<source>/maps/
export_full/recovered/AnimeStudio-cli/<source>/convert_by_type/
export_full/recovered/AnimeStudio-cli/<source>/json_by_type/
export_full/recovered/AnimeStudio-cli/<source>/asset_status/
export_full/structured/Audio/
webui/data/assets/index.json
webui/data/assets/story_media.json
webui/data/assets/videos.json
reports/source_graph/
reports/export_full_summary.md
```

Counts and candidate queues change after exports. Read the latest reports
instead of copying old per-session totals into new memory notes.

## Evidence model

Use this confidence order when joining a semantic object to an asset:

1. authored asset/prefab path or direct table/config foreign key;
2. Unity source-root + PathID or asset-map relation;
3. exported prefab/component/renderer dependency;
4. material-to-texture or material-to-shader reference;
5. decoded controller/clip/effect reference with an exact exported family;
6. exact normalized filename or stable entity-family identity;
7. token/name similarity, which remains a labeled candidate.

Preserve source root. The same PathID or natural filename is not globally
unique across StreamingAssets and Persistent. Preserve LOD/state suffixes,
original asset names, PathIDs, material slots, texture roles, and evidence
kind rather than flattening everything to one stem.

Useful boundaries:

- an asset map proves a Unity object/container relation, not live scene use;
- a world placement proves authored/static placement, not spawn or visibility;
- a controller reference proves an animation/effect family is named by that
  controller, not that a mesh is the controller's runtime renderable;
- a material reference proves an authored dependency, not the selected runtime
  keyword variant;
- a decoded audio/video binding proves identity or association at its stated
  evidence class, not every runtime trigger condition.

## Source-graph asset surface

The local source graph is the maintained lookup layer. Useful commands:

```bat
python tools\endfield_source_graph.py entity-assets TERM
python tools\endfield_source_graph.py model-bindings --status strong_exact
python tools\endfield_source_graph.py model-bindings --status no_exported_renderable_candidate
python tools\endfield_source_graph.py actor-usage TERM
python tools\endfield_source_graph.py animation-usage TERM
python tools\endfield_source_graph.py material-usage TERM
python tools\endfield_source_graph.py shader-usage TERM
python tools\endfield_source_graph.py effect-usage TERM
python tools\endfield_source_graph.py audio-usage TERM
python tools\endfield_source_graph.py video-usage TERM
```

The graph distinguishes low-level exported assets from reconstructed semantic
entities. Important node/evidence classes include:

- `asset`, `unity_asset`, `unity_pathid`, and source container;
- `asset_entity` with LOD model, material, texture, animation, and effect
  relations;
- decoded `model_config_model`, `model_prefab`, `model_radius`, world entity,
  interactive template, and model-view controller;
- shader export/program/snippet/backend and material usage;
- animation config/state/montage/clip/facial/lipsync references;
- Wwise/audio config/event/media and decoded file paths;
- FMV/video/playable/Story binding and unresolved candidate evidence.

Reverse edges are intentionally explicit. Examples include model LOD of
entity, material/texture used by entity, asset used by gameplay, visual token
used by, and shader program used by material. A reverse edge should mirror the
original evidence rather than silently strengthen it.

## Renderable asset entities

An `asset_entity` is a catalog grouping reconstructed from exported model
families and their dependencies. A strong group can contain:

- one or more LOD mesh/FBX assets;
- linked materials;
- linked texture roles;
- shader/PathID evidence;
- related animations, effects, icons, or gameplay records.

This is a practical lookup surface, not necessarily the original Unity prefab
root. Keep aggregate edges separate from raw PathID relations.

Filename fallback is deliberately conservative. If a material or material-like
texture filename normalizes exactly to an existing model entity base, it may
join that entity when the relation table omitted it. This is useful for
plus-separated interactive families, but the edge must remain a filename
fallback rather than masquerade as a prefab dependency.

Texture output reuse is also explicit: multiple source rows with different raw
serialized hashes can decode to the same `Name + PathID` PNG identity. The
collision audit records source containers, raw hashes, PathID, and output. It
does not indicate missing pixels or a general-purpose deduplication rule.

## Model, prefab, and placement recovery

Decoded model configuration provides model id, prefab/postmodel path, radius,
interactive use, and world/detail references. Exported maps and model assets
then provide the renderable side.

The current model-binding report replaced the original zero-match baseline.
At the last consolidated review it classified roughly 1,280 decoded model rows
and had more than 200 direct model-to-asset-entity edges, with most direct rows
strong and a smaller ambiguous/name-only set. Read
`reports/source_graph/model_config_asset_binding_candidates.*` for current
counts.

### Proven example shapes

Weapon assets can be strong end to end. For `wpn_sword_0019`, authored weapon
model data joins two renderable entities; the main entity has LOD meshes, a
material, and four texture roles with PathID-backed material relationships.
Catalog-scale checks found most linked weapon entities similarly complete.
This proves export-backed semantic lookup, not socket state, material variant,
VFX timing, or runtime prefab composition.

World placement can also reach a renderable. `int_collection_common` has
authored instance ids/transforms/detail ids, a decoded model/radius record, an
interactive template/component chain, a postmodel path, and an exported FBX
entity. It still does not prove runtime streaming, quest visibility, or
spawn/despawn state.

### Unresolved binding classes

Treat unresolved rows by evidence class rather than trying broader fuzzy
matching:

- **missing exported renderable candidate**: gameplay/model identity is real,
  but no current asset entity safely matches;
- **controller alias candidate**: a decoded model-view controller names an
  animation/effect family with an exported visual entity;
- **name-only candidate**: normalization suggests a family but lacks a direct
  controller, prefab, or PathID bridge;
- **ambiguous direct candidates**: more than one export-backed target survives
  the same evidence rule.

Current durable alias investigations:

- `int_switch_union_v2` is a real placed/common-switch interactive. Its
  controller names `interactive_universalswitch+1_001_01` clips/effects, and
  the exported universal-switch family has model/material/texture assets.
- `int_door_experbase_v2_postmodel` points through controller evidence toward
  the organ-door visual family.
- factory region upgrade rows point toward an upgrade-bot visual/controller
  family; keep the alias separate until prefab/map evidence closes it.
- `int_robot_fake_postmodel` references the ZMD-machine
  `interactive_zmdmachine_1_001_s01` family through both clip and effect names.
  The mesh evidence is meaningful, while exact material coverage is weaker.
- `int_system_spaceship_credit_shop` is a placed/template-backed system
  interactive whose controller references `anm_map01_zmdmachine_1_001_01`.
  Placement and animator/mesh evidence are strong; exact material-family
  selection remains open.
- ore-cluster and doodad-flower model ids are gameplay-real placed
  interactives. The missing direct postmodel bindings are likely prefab/GUID,
  pooled vegetation, or child-entity alias gaps. Nearby generic meshes are not
  safe substitutes.

Controller aliases are a useful middle layer. Promote one to a direct
renderable binding only when prefab children, asset-map relations, Animator
ownership, or an equivalent source-backed link confirms it.

## Materials, textures, and shaders

Material JSON plus asset maps provide shader PathIDs, texture PathIDs, colors,
floats, keywords, queues, and other serialized properties. The graph exposes:

- material-to-texture and reverse texture usage;
- material-to-shader PathID and exported shader program;
- entity-to-material/texture aggregate relations;
- raw and filename-fallback evidence as separate edge classes.

Converted shader exports contribute shader family, program, snippet, backend,
sidecar format, keywords, and PathID evidence. `shader-usage` answers which
materials/entities use an extracted program. It does not produce HLSL, prove
the runtime variant, or validate rendering fidelity.

Do not infer a material assignment only because a similarly named texture and
mesh coexist. Prefer renderer/material PathIDs or a preserved prefab relation.
Likewise, native texture format/mips and decoded PNG appearance are different
evidence; downstream rendering may need original compression and mip data.

## Actors, characters, and animation assets

Actor/character identity spans Story actor ids, playable character ids, SNS
identities, voice profiles, profile images, model entities, and progression
rows. These namespaces are not globally one-to-one.

`ActorImageTable` supplies authored avatar, bust, illustration, mission-panel,
and related visual tokens. `actor-usage` joins direct actor/character evidence
and emits token-based character or asset-entity candidates separately.

Animation evidence includes:

- decoded AnimationConfig states and refs;
- reverse links from montage, actor animation, cutscene-like ref, facial morph,
  and generic animation path back to config;
- AnimationClip assets and custom curve bindings;
- model-view controller clips/effects;
- Timeline, lipsync, damage-text, and selected UI animation references.

`animation-usage` is an authored/static lookup. A clip or state name does not
prove controller transition, event timing, root motion, facial routing, or
secondary physics. Character-lab conclusions and the maintained playable
roster live in `character_render_and_animation_recovery.md`.

## Effects, audio, and video

Effect lookup joins gameplay effect ids, decoded managed-reference effect
names, model-view controller effects, exported particle/model assets, and
asset-entity candidates. It proves references, not effect spawn conditions or
render order.

Audio recovery combines Wwise bank event-to-media links, decoded shared versus
language voice files, AudioDialog/config metadata, cue condition keys,
RTPC/override events, item/drop/model keys, and managed-reference `soundName`
fields. Shared SFX/music live once under `structured/Audio/shared`; language
voice lives under `structured/Audio/<LANG>`. `audio-usage` and the generated
voice-audio report distinguish path-backed relations from unresolved Story
audio ids. A matching event name does not prove runtime selection or RTPC
state.

Video recovery distinguishes:

- exported video file/stem;
- FMV binding and Timeline playable;
- source-root PathID/Unity asset;
- Story/mission association;
- WebUI manual override or filename candidate.

`video-usage` unifies those lookups without promoting filename candidates to
Timeline proof. Authoritative Story placement policy remains in
`game_story_recovery.md`.

## Recovery queue

1. Resolve high-use `no_exported_renderable_candidate` model rows through
   prefab/GUID/Animator/component evidence, starting with repeated ore,
   vegetation, switch/door, and machine families.
2. Promote controller aliases only when a second direct source proves the
   visual owner; keep candidate and direct bindings distinct in reports.
3. Improve material/texture completeness for already strong entity aliases,
   especially ZMD-machine and other plus-separated families.
4. Extend asset status manifests so each semantic catalog row can distinguish
   absent export, intentional empty, conversion error, output reuse, and
   unindexed dependency.
5. Keep actor/animation/effect/audio/video queries evidence-first and add new
   typed reverse edges only when they answer a maintained lookup.
6. Validate strong bindings on representative weapons, characters,
   interactives, and world props before generalizing a new normalization rule.
7. Store detailed inventories and changing counts in generated source-graph
   reports; update this conclusion instead of adding dated per-family notes.

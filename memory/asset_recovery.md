# Asset recovery

This topic owns semantic bindings between exported Unity assets and Story,
characters, gameplay entities, world objects, audio, and video. The Assets page
only inventories browser-visible files; AnimeStudio only extracts them.

## Why this file remains

Cross-domain identity and ownership rules are reused by Map, Characters,
Gameplay, Audio, packaging, and the source graph. They therefore remain separate
from [`webui/assets.md`](webui/assets.md), which documents page publication, and
[`animestudio_recovery.md`](animestudio_recovery.md), which documents extraction.

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
python scripts\build_assets.py
python tools\endfield_source_graph.py build
```

Asset modes, from narrowest to broadest, are `--focused-assets`,
`--default-assets`, and `--debug-assets`.

Primary outputs:

```text
export_full/recovered/AnimeStudio-cli/
export_full/structured/Audio/
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
- `chen` and `chenpast` are now kept as separate identities: the playable
  `chen` row owns the `P_actor_chen_*` model family, while the historical NPC
  `chenpast` row owns the independent `S_npc_major_chenpast_*` mesh family;
  their exported model PathIDs do not overlap. The WebUI manual merge that
  incorrectly folded `chenpast` into `chen` has been removed.
- Selected static world placements and gameplay/entity associations.

## CABMap container index

- **AnimeStudio's `Maps/*.bin` are CABMaps, not asset maps, and the format is now
  read byte-exact.** The framing comes from the writer itself --
  `AssetsHelper.DumpCABMap` in the submodule -- not from guessing at bytes: a
  .NET `BinaryWriter` stream of `string BaseFolder`, `int32 count`, then per entry
  a CAB name, a path, an `int64` offset, an `int32` dependency count and that many
  CAB names, with .NET's 7-bit encoded string length prefixes.
- Both current maps consume exactly to EOF: `endfield_persistent_assets.bin`
  (1,946 entries, 2,571,560 bytes) and `endfield_streamingassets_assets.bin`
  (254,723 entries, 47,318,490 bytes). Every CAB name is unique inside its file,
  which is what makes each map a map.
- **The dependency graph closes across the two maps, not within either.** Of
  661,808 edges only **3** name a CAB that appears nowhere. The persistent map is
  the reason to resolve across maps rather than within one: 10,025 of its distinct
  targets live in the streaming map and only 570 in its own, so a per-map check
  would report it as 95% dangling. 1,939 of its 1,946 CAB names also appear in the
  streaming map.
- **The CABMap offset is a physical byte offset into the `.chk`, and it lands
  inside a VFS logical file.** Joined against the VFS understanding ledger: all
  1,946 persistent entries land inside a ledger span, and 252,783 of 254,723
  streaming entries do. Two independently produced indexes -- AnimeStudio walking
  containers, the VFS audit walking blocks -- agree on where things are.
- **A coverage "hole" I reported here was my own bug. Retracted.** I compared
  *chunk filenames* and concluded the ledger never enumerated
  `VFS/0CE8FA57/4B06191A...chk` (222 MB, 1,053 containers). It does cover that
  content. Block `0CE8FA57` ships a **different chunk file in each VFS root** --
  `4B06191A...chk` under StreamingAssets, `F047E09F...chk` under Persistent -- and
  the ledger resolves each block from the **primary** root while the CABMap, built
  against StreamingAssets, names the fallback file. Both hold 1,053 containers.
  Same block, same count, different filename.
- Resolved by **block**, every block either map references is enumerated: nothing
  is missing in either direction. The check now keys on the block directory, and a
  test pins that so the filename comparison cannot come back.
- Two things worth carrying from the mistake. The repo already records that this
  VFS has two roots and that scans keyed on one silently mis-handle the other --
  **I hit the exact failure the notes warn about**, because I keyed a join on the
  most obvious identifier rather than the one the data is organised by. And I
  escalated it as a foundational problem before checking the sibling root, which
  is one `ls` away. **Check the cheap explanation before reporting a deep one.**
- **Every CAB is named by the logical bundle it sits in, and the relation is
  one to one.** Joining CABMap offsets to the ledger's logical-file spans names
  254,729 of 256,669 CABs, across 254,728 distinct bundles, of which **254,727
  hold exactly one CAB** and one holds two. The remainder split into 1,053 whose
  chunk is enumerated from the other VFS root and 887 whose offset falls inside no
  span; those two are counted separately because they are different situations.
- **Coverage and offsets need different join keys, and sharing one corrupts both.**
  Coverage keys on the *block*, because a block ships a different chunk file per
  root. Offsets key on the *chunk file*, because one block (`7064D8E2`) holds more
  than forty of them and merging their offset spaces invents matches. Keyed on the
  block, the join reported 256,601 names and "42 CABs in one bundle" -- a better
  looking number and a fabricated structure. The gate bounds both the one-to-one
  shape and the per-file maximum, since either bound alone passes a case it should
  not.
- Read by `scripts/asset_builder/cabmap.py`; report at
  [`reports/assets/cabmap_current_latest.json`](../reports/assets/cabmap_current_latest.json).
  This is a container index only -- it says nothing about the objects inside a CAB,
  their types, names or path ids, and an offset is not a readable object without
  the container format that sits at it.
- Note for anyone wanting a texture or asset inventory: this map does **not**
  provide one. That needs an AnimeStudio export; the `.bin` maps only locate
  containers.

## Remaining gaps

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

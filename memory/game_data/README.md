# Understanding the installed game data

Detail files for [`../game_data_recovery.md`](../game_data_recovery.md), which
holds what applies everywhere: the refresh and evidence rules, the
installed-data model, the shared asset/spatial and source-graph contracts, and
the topic-wide remaining gaps. Read the parent first if you only want the rules.

Files are organised by **level** (how deep the interpretation goes) and **lane**
(which kind of data), not by reading order. Each file states its level and lane
in its first line, and the lane prefix groups them in a directory listing.

## The four levels

A level can only be asked once the one below it is answered.

| Level | Question it answers |
| --- | --- |
| **1. Where the bytes are** | Which block is this file in, what reader owns it, what container is it wrapped in? |
| **2. How the bytes are framed** | Where does each record start and end, and does the framing consume the file exactly? |
| **3. What the fields are** | Which field is a count, an offset, an enum, a matrix -- proven against something outside the bytes? |
| **4. What it means** | What does a decoded record own, name, or reach in the game? |

A claim may cite evidence only from its own level or below. Most wrong
conclusions recorded in these files came from reading a level-4 meaning off a
level-2 framing -- a field name, an address order, or a filename standing in for
a proof.

## What lanes the binary data actually has

The client's own VFS block-type enum (`EndfieldVfsBlockType`, 26 dumpable
values) is the authoritative list. Collapsing its `Initial*`, `Hotfix*`,
`Audit*` and per-language variants, the installed data has these distinct
content kinds -- **more than this directory documents**:

| Block type | Holds | Lane | Documented in |
| --- | --- | --- | --- |
| `Bundle`, `InitialBundle` | Unity asset bundles: models, materials, textures, prefabs, scenes | **Unity assets** | [`unity_assets.md`](unity_assets.md), [`containers_cabmap.md`](containers_cabmap.md) |
| `Audio` + `InitialAudio`, `HotfixAudio`, `AudioChinese/English/Japanese/Korean` | Wwise banks and media | **audio** | here |
| `Video` | FMV | Unity assets | [`unity_assets.md`](unity_assets.md) |
| `Streaming` | `InitChunkData`, `StreamingChunkData`, `StreamingChunkInfo` | **world** | here |
| `DynamicStreaming` | `FBStreamArea` and the other four root families | **world** | [`install_and_vfs.md`](install_and_vfs.md) only |
| `Terrain` | `TRET` container, `LAYER_C/D/N` | **world** | here |
| `IV` | irradiance volumes -- the largest block at 4.17 GB | **world** | here |
| `Table` | 724 single-instance config tables | **gameplay** (Buff/Skill) and **text** | here for gameplay; [`../webui/story_recovery.md`](../webui/story_recovery.md) for Story/Text Tables |
| `JsonData` | ~1,264 JSON name shapes: LipSync, NPC Montage, conversations | **text**, partly **world** | [`install_and_vfs.md`](install_and_vfs.md) for LipSync/Montage framing; [`../webui/story_recovery.md`](../webui/story_recovery.md) for conversations |
| `ExtendData`, `InitialExtendData` | `StringPathHash.bin`, `FacBoneTRS.bin`, `CompressData.bin` | **catalog** | here |
| `Lua` | mission and consumer scripts | **code** | [`../webui/story_recovery.md`](../webui/story_recovery.md); index built by `scripts/webui/story/lua_consumer_references.py` |
| `IFixPatch` | runtime code patches | **code** | nowhere -- reader is `scripts/game_data/ifix_patch.py` |
| `BundleManifest` | one 50 MB `manifest.hgmmap` | **catalog** | [`extend_data.md`](extend_data.md): entropy is indistinguishable from random, so it is opaque |
| `Audit*` (5 kinds) | audit variants of streaming, dynamic streaming, IV, audio, video | provenance | [`extraction_pipeline.md`](extraction_pipeline.md) |

So this directory covers the world, audio, gameplay, catalog and Unity-asset
lanes, plus a **story** lane that has no block of its own: its activation and
placement carriers are serialized records read out of `Bundle` and `JsonData`,
so it is organised by what a carrier proves rather than by a block type. An
**extraction** lane sits beside them for the reader itself and how far each
family's reader is proven, and two cross-lane files cover the serialization
framework and the native read path.

Only **text** is owned elsewhere: `Table` text and `JsonData` conversations are
presentation-facing and belong to
[`../webui/story_recovery.md`](../webui/story_recovery.md). Two blocks are still
documented nowhere: `IFixPatch` has a reader but no durable conclusions, and
`DynamicStreaming` has only the summary in `install_and_vfs.md` rather than a
file of its own. Those are the honest gaps in the lane coverage, not in the
data.

`ExtendData` is worth calling out because the grouping is easy to get wrong:
`StringPathHash.bin` is the game's complete source-path table, a **global
catalog** rather than world data, and `FacBoneTRS.bin` is facial-bone
animation. Neither is spatial, so neither belongs in the world lane.

## Files

**Level 1 -- all lanes**

| File | Lines |
| --- | --- |
| [`install_and_vfs.md`](install_and_vfs.md) -- the block inventory, the reader each family routes to, and reading a logical file | 282 |
| [`shared_containers.md`](shared_containers.md) -- the `TRET` container, the terrain header, and the custom LZ4 with big-endian offsets and a bit-interleaved token | 164 |
| [`containers_cabmap.md`](containers_cabmap.md) -- the `CABMap` container index that gives a PathID its source root | 154 |

**World lane** -- terrain, chunks, irradiance.

| File | Level | Lines |
| --- | --- | --- |
| [`world_terrain.md`](world_terrain.md) -- the `LAYER_*` arrays, decoded end to end | 2 | 307 |
| [`world_chunks_schema.md`](world_chunks_schema.md) -- `InitChunkData`'s FlatBuffers schema, read from the bytes with no schema at all | 2 | 513 |
| [`world_chunks_families.md`](world_chunks_families.md) -- the second family, the per-level index, the corpus gate | 2 | 360 |
| [`world_irradiance.md`](world_irradiance.md) -- the largest block, and why its payload stays unread | 2 | 638 |
| [`world_chunk_slots.md`](world_chunk_slots.md) -- slot 5's kind codes and slot 7's descriptor mask | 3 | 305 |
| [`world_chunk_unread_region.md`](world_chunk_unread_region.md) -- the slot-4 region, and a coverage figure that was an artefact | 3 | 429 |
| [`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) -- the root retyped, and what that invalidated | 3 | 431 |
| [`world_chunk_transforms.md`](world_chunk_transforms.md) -- the transform-matrix bulk | 3 | 440 |

**Audio lane** -- the Wwise chain, from bank container to what is actually named.

| File | Level | Lines |
| --- | --- | --- |
| [`audio_overview.md`](audio_overview.md) -- the six evidence layers and the authored-versus-observed boundary | 2 | 542 |
| [`audio_bank_format.md`](audio_bank_format.md) -- the bank sections outside HIRC | 2 | 171 |
| [`audio_hirc_parser.md`](audio_hirc_parser.md) -- every HIRC layout, named from the SDK deserializer; the shipped parser read out of the engine | 2 | 819 |
| [`audio_native_hooks.md`](audio_native_hooks.md) -- the native request chain, and what a bounded capture would prove | 2 | 546 |
| [`audio_hirc_graph.md`](audio_hirc_graph.md) -- the object graph, the closed type layouts, and the typed v150 effect/bus parse | 3 | 1409 |
| [`audio_naming_coverage.md`](audio_naming_coverage.md) -- what is named and owned, and what nothing reaches | 4 | 317 |

**Gameplay lane** -- authored `Table` config joined to native contracts.

| File | Level | Lines |
| --- | --- | --- |
| [`gameplay_semantics.md`](gameplay_semantics.md) -- the root framing, the rules the 228 tracked contracts share, and what a decoded action row may be labelled | 4 | 224 |

**Story lane** -- the carriers that activate and place Story.

| File | Level | Lines |
| --- | --- | --- |
| [`story_carriers.md`](story_carriers.md) -- what a LevelScript action, Timeline record, or spatial carrier proves, its identity domain and slot action bindings, and the gates on all of it | 4 | 109 |

**Catalog lane** -- the `ExtendData` and `BundleManifest` blocks.

| File | Level | Lines |
| --- | --- | --- |
| [`extend_data.md`](extend_data.md) -- `StringPathHash.bin`, `FacBoneTRS.bin`, and the two opaque files | 2 | 242 |

**Unity assets lane** -- the `Bundle` and `Video` blocks.

| File | Level | Lines |
| --- | --- | --- |
| [`unity_assets.md`](unity_assets.md) -- object identity, the binding evidence order, and what exporting an object does not prove | 4 | 306 |

**Extraction lane** -- the reader itself, and how far it is proven.

| File | Level | Lines |
| --- | --- | --- |
| [`extraction_pipeline.md`](extraction_pipeline.md) -- AnimeStudio: export scopes, provenance states, scheduling, DummyDll, shader recovery, change workflow | 1 | 392 |
| [`extraction_payload_boundaries.md`](extraction_payload_boundaries.md) -- one statement per family: which reader is fail-closed and where it stops | 2 | 911 |

**Cross-lane**

| File | Level | Lines |
| --- | --- | --- |
| [`serialization_memorypack.md`](serialization_memorypack.md) -- MemoryPack framing status, and the IL2CPP chain that resolves a formatter | 2 | 2300 |
| [`native_read_path.md`](native_read_path.md) -- from `ResourceManager` down to `ReadFile`, and why it yields no authenticated receipt | 2 | 164 |
| [`settled_and_open.md`](settled_and_open.md) -- the settled tables, and what is open, stated accurately | 4 | 171 |

## Start here for a specific question

- *What is this `.bytes` file?* -> [`install_and_vfs.md`](install_and_vfs.md).
- *Why does the terrain codec decode chunk data?* -> [`shared_containers.md`](shared_containers.md).
- *How does the game actually read this file off disk?* -> [`native_read_path.md`](native_read_path.md).
- *What does the audio runtime do with a voice request, and what would a capture add?* -> [`audio_native_hooks.md`](audio_native_hooks.md).
- *Is this family's reader proven that far?* -> [`extraction_payload_boundaries.md`](extraction_payload_boundaries.md), not the lane file.
- *What is the layout of Buff action tag `0xNN`?* -> its `scripts/game_data/contracts/buff_NN_native.json` contract, not the gameplay file.
- *Does this LevelScript action or trigger volume prove a Story link?* -> [`story_carriers.md`](story_carriers.md).
- *Which native fact does a Story or Mission Pipeline builder rely on?* -> its `scripts/game_data/contracts/<name>.json` and `<name>_native.py` loader, then that contract's `nativeInputs` against the selected build.
- *Is this conclusion still current?* -> [`settled_and_open.md`](settled_and_open.md), then the contract's own `nativeInputs`.
- *What is worth attempting next?* -> the remaining gaps in [`../game_data_recovery.md`](../game_data_recovery.md), and the eliminations in `world_chunk_unread_region.md`, `world_irradiance.md` and `audio_hirc_parser.md` so an excluded route is not retried.

## What these files are for

They exist so an attempt is not repeated. Much of their length is **recorded
negatives** -- candidates tested and refused, with the test that refused them.
That is deliberate: an elimination is the expensive part, and deleting it
invites the same dead end. Four recurring traps are worth knowing before
reading any of them:

- **The degenerate subset.** A formula scoring 100% may be fitting a subset
  where every rival also scores 100%. Make rivals compete rather than checking
  one and stopping ([`settled_and_open.md`](settled_and_open.md)).
- **The cross-package join.** Pooling ids across packages manufactures matches
  that no single package supports ([`audio_naming_coverage.md`](audio_naming_coverage.md)).
- **The walk-based coverage figure.** Coverage measured by a walker reports the
  walker's reach, not the file's structure ([`world_chunk_unread_region.md`](world_chunk_unread_region.md)).
- **The inherited blocker.** Three "impossible" blockers here were misdiagnosed
  and fell on re-test. Re-test before accepting one ([`settled_and_open.md`](settled_and_open.md)).

## Maintenance

The rules in [`../README.md`](../README.md) apply unchanged. In addition:

- a file belongs to exactly one level and one lane, and its name carries the
  lane. If a conclusion needs evidence from a higher level, it belongs in the
  higher-level file with a link down -- not copied up;
- there is no reading order to maintain. Adding a file means adding a row to its
  lane, not renumbering anything;
- replace a superseded reading in place. These files carry explicit corrections
  and retractions, so a new conclusion overwrites the claim it corrects instead
  of sitting beside it;
- per-build addresses, hashes, full member orders, and inventories belong in a
  contract JSON under `scripts/` or a generated report under `reports/`, with
  only the durable interpretation here. The gameplay lane is the worked example:
  213 per-tag layouts live in their tracked contracts, and this directory keeps
  only the root framing and the shared rules;
- update this index, the parent file's index, and [`../README.md`](../README.md)
  in the same change as any file added or removed.

# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.
This file is the topic's entry point; the per-family evidence lives in
[`game_data/`](game_data/README.md).

## Why this topic remains

The WebUI page guides explain how recovered data is published. This topic is
still required because many evidence contracts are shared by several pages or
exist before any page projection: overlay behavior, binary framing, native
build gates, runtime/static distinctions, and cross-domain graph provenance.

## Refresh and evidence rules

```bat
python scripts\verify_export_freshness.py
.\export.bat --from-game
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

- StreamingAssets is the fallback; Persistent is the active overlay. Changed
  logical paths replace their fallback file as a whole unless a format-specific
  contract proves record-level merging.
- Native claims require the selected `GameAssembly.dll` plus
  `global-metadata.dat` gate. Missing or mismatched inputs skip that evidence
  and leave the last validated report untouched.
- A field name, code address, registration order, hash collision, filename,
  proximity, or available asset is not ownership or runtime execution.
- Preserve source root, logical path, file hash, record offset, parser/schema
  version, and validation status through every join.
- Exact parsers require bounded positive fixtures, malformed/truncated/trailing
  negatives, exact consumption, and a current-corpus sweep.
- Build-specific counts, hashes, tokens, addresses, and full inventories belong
  in reports or versioned code contracts.

## Installed-data model

The installed client exposes overlapping logical data through VFS catalogs and
payload roots. Maintained readers cover Unity bundles and AssetMaps, structured
Tables and JsonData, video, audio, Terrain, Streaming/DynamicStreaming, selected
ExtendData families, and native-gated contracts. A verified outer VFS boundary
proves byte identity and availability, not the inner payload schema.

Stable cross-format rules:

- Unity object identity is source/CAB plus PathID. A global PathID or basename
  is never sufficient.
- Table ids and localized strings are authored values; they do not by
  themselves prove a runtime consumer.
- Serialized TypeTrees are preferred when exact. `$partial`, `$unparsed`, and
  `$inferred` remain visible and must not be upgraded by a later name match.
- Runtime-mutable properties preserve their authored initializer but cannot be
  treated as final action targets without excluding later writes.
- Exact spatial transforms prove authored placement, not spawning, activation,
  visibility, or interaction.

## Where the detail lives

[`game_data/`](game_data/README.md) holds the per-family evidence, organised by
**level** (how deep the interpretation goes) and **lane** (which kind of data).
This file keeps what every one of them depends on -- the refresh and evidence
rules above, the installed-data model, the shared asset/spatial and source-graph
contracts below, and the topic-wide remaining gaps.

A level can only be asked once the one below it is answered, and a claim may
cite evidence only from its own level or below:

| Level | Question it answers |
| --- | --- |
| **1. Where the bytes are** | Which block, which reader, which container? |
| **2. How the bytes are framed** | Where does a record start and end, and is the file consumed exactly? |
| **3. What the fields are** | Which field is a count, offset, enum or matrix -- proven outside the bytes? |
| **4. What it means** | What does a record own, name or reach in the game? |

Most wrong conclusions recorded there came from reading a level-4 meaning off a
level-2 framing -- a field name, an address order, or a filename standing in for
a proof.

The client's own `EndfieldVfsBlockType` enum is the authoritative list of what
the installed data contains. `game_data/` documents five of its lanes -- **world**
(`Streaming`, `DynamicStreaming`, `Terrain`, `IV`), **audio**, **gameplay** (the
`Table` Buff/Skill subset), **catalog** (`ExtendData`, `BundleManifest`), and
**extraction**, which owns the AnimeStudio reader itself plus how far each
family's reader is proven. A **story** lane sits beside them with no block of
its own: [`game_data/story_carriers.md`](game_data/story_carriers.md) owns what
a serialized LevelScript action, Timeline record, or spatial carrier proves
about Story activation and placement. Two cross-lane files sit beside them for the
serialization framework (MemoryPack and its IL2CPP formatter resolution) and the
native read path down to `ReadFile`.
**Unity assets** (`Bundle`, `Video`) are here too, in
[`game_data/unity_assets.md`](game_data/unity_assets.md), with the container
index in [`game_data/containers_cabmap.md`](game_data/containers_cabmap.md).
Only **text** remains elsewhere: `Table` text and `JsonData` conversations are
presentation-facing and belong to
[`webui/story_recovery.md`](webui/story_recovery.md). `IFixPatch` has a reader
and no durable conclusions. [`game_data/README.md`](game_data/README.md) carries the
full block-to-lane table.

Read [`game_data/settled_and_open.md`](game_data/settled_and_open.md) before
reopening `InitChunkData`/`StreamingChunkData` slot typing or HIRC type
coverage. It records the conclusions a later session should not re-derive, and
the inherited blockers that turned out to be misdiagnosed on re-test.

Per-build member orders belong in their tracked `scripts/game_data/*_native.json`
contracts, not in memory prose. The gameplay lane is the worked example: 213
per-tag Buff action layouts live in their contracts, and
[`game_data/gameplay_semantics.md`](game_data/gameplay_semantics.md) keeps only
the root framing and the rules every contract shares.

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link must retain the earlier physical identity and cannot be substituted by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in
[`game_data/unity_assets.md`](game_data/unity_assets.md);
Map publication belongs in [`webui/map.md`](webui/map.md).

## Source graph

Canonical database:

```text
reports/source_graph/endfield_source_graph.sqlite
```

The graph indexes evidence already produced by owning builders. It is a query
and provenance surface, not an authority that may invent new recovery logic.

```bat
python tools\endfield_source_graph.py query IDENTIFIER
python tools\endfield_source_graph.py story STORY_KEY --limit-lines 8
python tools\endfield_source_graph.py build --relevant-asset-maps --skip-reference-rows --skip-followups
```

Default builds retain only exact AssetMap rows consumed by WebUI material,
shader, texture, and FMV edges. Full builds are for exhaustive Unity
object/PathID investigation. Every edge keeps an evidence kind; availability,
registration, address order, and mission environment context never become
ownership or chronology.

Before deleting or renaming a generated report, search graph readers and rebuild
the database if that report is an input.

## Diagnostics

Use the closest owning report first:

```text
reports/export/
reports/animestudio/
reports/assets/
reports/audio/
reports/source_graph/
reports/story/build/
reports/story/recovery/
```

Revisitable format probes belong in `scratch/<topic>/`; disposable extraction
and before/after evidence belongs in `tmp/<topic>/`.

## Remaining gaps

- Streaming's next advance requires independent record-end evidence or a
  bounded runtime carrier witness. Keep selector9 held until its component
  mapping indices and write span are authenticated; do not repeat anonymous
  load-width or target-distance statistics. Multi-target clusters need extents;
  neither zero values nor a loop skip establishes validity or sizeof.
  Marker13's observed gap profiles are anonymous, and serialized absence is
  not a numeric selector.
  Marker17 body profiles are structurally closed but anonymous. Marker15 still
  needs a concrete producer, source extent or independently bounded unread
  region: repeating a 16-byte native load does not prove record size. Its
  directory is bounded, not its records; missing count keys remain unsupported.
  Paired Init/Streaming paths, serialized ordinals and ordered witnesses do not
  prove concrete runtime root/key receipt, fresh key state, absence of overrides
  or execution. Native Info provenance is conditional, not a concrete record.
  Keep field namespaces and runtime semantics behind those gaps. Then Terrain
  block/channel semantics, DynamicStreaming, irradiance, manifest, mmap,
  patch, and JsonData body semantics.
- Continue Streaming nested element/byte-body framing using the bottom-up
  queue below, whose current Streaming framing state is in
  [`game_data/world_chunk_slots.md`](game_data/world_chunk_slots.md);
  concrete runtime paths and field names follow structural closure, not the
  reverse.
- Recover more exact gameplay action/selector/formula contracts without
  treating native names as byte-layout proof.
- Close more authored and observed audio consumers through exact Event/media
  traversal, while preserving branch and audibility gaps.
- Improve exact prefab, renderer, material, animation, and world-instance
  ownership.
- Keep native gates and source-graph provenance deterministic across client
  updates.

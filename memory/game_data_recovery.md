# Game-data recovery

This topic owns durable conclusions about installed data formats, gameplay and
audio semantics, native consumers, and the source graph. It does not own WebUI
presentation, page build commands, or AnimeStudio implementation mechanics.

## Why this file remains

The WebUI page guides explain how recovered data is published. This file is
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

## VFS-native payload families

The maintained evidence index in the AnimeStudio workflow routes each family to
its reader, fixtures, and generated corpus report. Durable current conclusions:

- DynamicStreaming is a generated FlatBuffers family with validated version,
  grid, string, resource/state, and area accessors. The deeper meaning of its
  DataMask and several record fields remains unresolved.
- Terrain accepts the observed raw or length-prefixed inverted-LZ4 envelope and
  TRET versioned prefix. `_H` records close as row-major little-endian height
  samples; adjacent cells establish grid orientation. Absolute height scale,
  no-data semantics, and other Terrain bodies remain unresolved.
- `ExtendData/Main/CompressData.bin` is an absolute-offset archive of Brotli
  records whose decoded bodies are strict UTF-16LE JSON. Current bodies contain
  NodeCanvas behavior graphs. This proves authored graph structure, not selected
  runtime branches or blackboard values.
- String/path hash, facial-bone TRS, and manifest files have separate mmap or
  native consumers. Their member names guide bounded parsers but do not prove
  complete byte layouts.
- LipSync JsonData has an exact selected-build MemoryPack layout. Its float rows
  are native-proven Unity keyframe values. LipSync animation data remains
  distinct from language voice-audio availability.
- Video has exact outer framing for the maintained corpus; codec/container
  validity does not prove narrative attachment or playback.

Changing sizes and totals live in `reports/animestudio/`, not here.

## Gameplay semantics

Gameplay recovery joins authored Tables, exact binary/serialized structures,
selected native enum contracts, Assets, Audio, and the curated graph.

- Enemy variants resolve their exact attribute template before stats are shown.
- Authored level points, cooldowns, modifiers, formulas, and Buff actions are
  preserved as source values. Final runtime values across other Buffs, IFix,
  equipment, and server state remain uncomputed.
- Action/condition unions publish only the typed prefix or body that consumes
  exactly. Unknown selectors, enums, tags, blackboard operations, and nested
  payloads stay unresolved.
- Gameplay tag names come from exact predefined/config registries or validated
  runtime capture under the same native gate. CRC/context-derived names retain
  their derivation label; raw unmapped ids remain visible.
- Projectile behavior is immutable authored data. Skill/projectile ownership,
  event hashes, decoded media, and asset references keep separate provenance.
- Combat/source-graph consumers reject stale inputs and publish a degraded
  reason rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](webui/gameplay.md).

## Audio evidence

Audio recovery separates six layers:

1. physical package/media identity;
2. decoded playable media;
3. Wwise Event/action/media graph;
4. authored game consumer and control parameters;
5. validated runtime request;
6. selected branch, audibility, and final DSP behavior.

Evidence may advance only one layer at a time. A stronger downstream fact does
not retroactively make every upstream candidate unique.

Stable conclusions:

- `build_audio.py` owns decode, bank/HIRC indexing, relinking, and Gameplay
  sidecars. Shared SFX/music and language voice remain separate physical roots.
- AKPK entries, Wwise numeric media ids, Events, containers, switches, random
  nodes, RTPC curves, and authored consumers keep their native identities.
  Same-id files in different roots are not collapsed by filename stem.
- Authored Event requests, controller callbacks, Timeline clips, Lua calls,
  serialized AudioCue trees, external sources, and responsive-voice tables are
  typed consumer evidence. They do not prove the selected runtime arm.
- A source prefab or component proves a possible emitter, not scene
  instantiation or level ownership.
- Native method names and callsites are accepted only with exact-build hashes
  and bounded argument/control-flow validation. Literal, dictionary, selector,
  callback, and external-source paths remain distinct.
- Runtime trace bundles must be complete, verified, language-compatible, and
  source-matched. They prove the captured request only; playback success,
  audibility, and DSP response remain separate gaps.
- Unsupported codec/plugin media, absent historical/language chunks, decode
  failures, and mapping failures are reported independently.

Detailed changing investigations live under `reports/story/recovery/audio/`.
Page behavior and focused publication belong in
[`webui/audio.md`](webui/audio.md).

## Asset and spatial semantics

AssetMap rows, PPtrs, prefab/component dependencies, material slots, textures,
controllers, clips, effects, and scene records form an evidence chain. A later
link must retain the earlier physical identity and cannot be substituted by a
normalized-name match.

World registries, LevelData, streaming matrices, NPC proxies, authored pins,
and trigger geometry use separate identity domains. Script-wide context and
proximity never fan out to sibling slots. Dynamic getters and runtime lists are
non-spatial unless a pinned producer proves one immutable authored target.

Semantic asset ownership belongs in [`asset_recovery.md`](asset_recovery.md);
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

- Complete unresolved Terrain, DynamicStreaming, irradiance, manifest, mmap,
  patch, and JsonData body semantics.
- Recover more exact gameplay action/selector/formula contracts without
  treating native names as byte-layout proof.
- Close more authored and observed audio consumers through exact Event/media
  traversal, while preserving branch and audibility gaps.
- Improve exact prefab, renderer, material, animation, and world-instance
  ownership.
- Keep native gates and source-graph provenance deterministic across client
  updates.

# What is settled, and what is open

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4.** The consolidated tables for every family in this directory, so a later session does
not re-derive them, plus the open questions stated accurately. Three inherited
blockers here turned out to be misdiagnosed on re-test, which is the single
highest-yield habit this topic records. Read it before reopening
`InitChunkData`/`StreamingChunkData` slot typing or the HIRC type coverage.

## `InitChunkData` / `StreamingChunkData` -- current slot-7 framing

| field | current reading | boundary |
| --- | --- | --- |
| 0 | the group's 128-bit descriptor-ID mask: its set bits equal the group's own field-3 descriptor IDs in every current group; not a `StreamingComponentType` mask | exact corpus gate (`streaming.descriptor_mask_corpus`, `field0DescriptorIdMask`); the IDs stay anonymous |
| 1 | count | multiplies the sum of field-3 descriptor strides to give the wrapped byte-vector length |
| 2 | centre and extents | spatial interpretation from paired chunk evidence |
| 3 | forward uoffset to a counted vector of 8-byte `(u16 anonymous id, u16 stride, u32 zero)` descriptors | exact framing and direct selected first-root consumer; descriptor 21 carries a NUL-terminated 63-byte name prefix duplicated with its ID in root rows across the current complete Init corpus; other descriptors remain open |
| 4 | forward uoffset, observed as `4`, to a one-field table wrapping a counted byte vector | exact framing and direct selected first-root consumer; the observed `4` is an offset, not a scalar constant |

Root slot 0 is version `47`; slot 1 is the chunk origin. Slots 2 through 7
are vectors: slot 2 is empty in Init and populated in StreamingChunkData;
slots 3/4/5 are parallel ids, a byte vector, and typed records; slots 6/7 are
parallel, slot 6 wrapping per-group ID vectors. The framing itself is
documented in `scripts/game_data/streaming/framing.py`. See
[`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) and the current
correction in [`world_chunk_unread_region.md`](world_chunk_unread_region.md).
Historical hypotheses elsewhere do not override this framing.

## Audio -- the HIRC types the notes called SDK-only

**Settled by the installed Wwise 2023.1.17 SDK**, whose static libraries carry
the deserializers as named object code ([`audio_hirc_parser.md`](audio_hirc_parser.md)):
every shipped type frames byte-exact from the engine's own grammar --
`0x02`-`0x07`, `0x09`-`0x0E`, `0x10`, `0x11` and `0x13`-`0x16` as lanes, and
`0x08`, `0x12`, `0x03` named. The music types the game DLL skips are read by
`AkMusicBank::LoadBankItem` in the music engine and are framed. What the game
DLL alone gave:

| type | how reached in the game DLL | state |
| --- | --- | --- |
| `0x02`, `0x05`, `0x09` | one shared class | **named**: `CAkParameterNodeBase::SetNodeBaseParams` |
| `0x0A`-`0x0D` | one shared arm | skipped by the shipped DLL; **framed** from `AkMusicEngine.lib` |
| `0x10`, `0x11` | one vtable slot | **named**: `CAkFxBase::SetInitialValues` |
| `0x12` | one vtable slot | **complete**, and the same `CAkBus` class as `0x08` |

## Still open, accurately

- **`LAYER_C`'s managed field and encoded channel.** A checked consumer routes
  `LAYER_C/D/N` through owner-local handles to `_ConeMaps` (conditional),
  `_Splats` and `_Normals`; a managed constructor copies eight
  `TextureResources` fields (both layer arrays, the color variation texture)
  into `VirtualTextureRenderer`; the `SetupTerrainManager` native bridge stops
  before the layer handles; an authored `HGRP/HGTerrainPS` variant samples
  `_ConeMaps` component zero, naming no live shader or file. Open: the join
  from any `LAYER_*` file or handle into those managed fields; neither
  `m_colorVariationTex` nor a mask-map reading for `LAYER_C` is established
  ([`world_terrain.md`](world_terrain.md) and its `terrain_*` contracts).
- **The other slot-7 descriptor payloads and their component labels.** The
  native path consumes consecutive `group count * descriptor stride` regions
  of the first paired root's slot 7, and every descriptor-21 slot joins a root
  row by ID and 63-byte name prefix. Open: a checked descriptor-ID-to-component
  mapping, a runtime root/file receipt, and a certified extent for the large
  residual runs ([`world_chunk_unread_region.md`](world_chunk_unread_region.md)).
- ~~**`0x0B`'s `+12`/`+20` words.**~~ **CLOSED** by the SDK: the `sourceID` and
  `eventID` of the 44-byte playlist item `CAkMusicTrack::SetInitialValues`
  reads; the whole type frames exactly.
- ~~**The 1 of 8 unowned media** that is not Init-bank embedded.~~ **IDENTIFIED.**
  Pooled over all audited packages, `hircMediaJoin` gives 1,284 unowned
  declared media while the recorded figure is 8 unowned: the same join before
  and after adding `0x0B` records, which closed 1,276 (1,284 - 1,276 = 8).
  Pooling `idValuesByType` (`type02` and `type0B`) against the declared media
  reproduces exactly 8 from the raw data:

  | media id | declared in |
  | --- | --- |
  | 67918417, 133192886, 213132781, 792360875, 934360813, 1028758860 | `default_banks.pck` + `default_stream_0.pck` |
  | **624424588** | `default_banks.pck` + **`default_stream_2.pck`** |
  | **1041213772** | **`default_stream_0.pck` only -- no bank entry** |

  **Correction:** an earlier note put all seven Init-bank ids in
  `default_stream_0.pck` and the eighth in `default_stream_2.pck` only; both
  halves were wrong. Enumerate a set rather than describe it from a summary.
  The pooled join's source ids naming no media are the cross-package trap.

## Eliminated readings

- Chunk reader in "packed native code" -- it is in unpacked `UnityPlayer.dll`.
- Audio types behind a "licensed SDK" -- the parser ships with the game.
- `StreamingComponentType` excluded -- that came from a one-byte read of a
  `ulong` enum.
- Numeric descriptor-ID-to-enum-index mapping -- an authenticated Init
  descriptor exceeds the selected `StreamingComponentType` bit-index range.
- Group field 0 as a `StreamingComponentType` component mask -- its bits equal
  the group's own descriptor IDs in every current group, so it is the
  descriptor-ID mask and inherits the same refusal.
- Native entity-name getter as descriptor 21's reader -- its context pointer is
  not joined to the packed column and the getter is absent from the selected
  IL2CPP type; a candidate only.
- `s4` as `24 + stride * n7` -- degenerate (below); Init's `s4` grows far faster
  than linearly in `n7`, so it is a byte size over variable-length records.
- Slot-5 fields 0/3/5 as byte sizes summing to a scalar -- best fit 16.70%; the
  one 46.47% hit is the degenerate subset.
- Slot-5 `(f1, f2)` as a per-chunk directory keyed by kind, or as a sort key --
  both refused (below). The union-tag reading is undecidable from bytes.

**The inherited blocker.** The first three entries were inherited blockers,
all misdiagnosed. **Re-test an inherited blocker before accepting it; that has
been the highest-yield move in this family.** Field 0's mask reading survived
because its bits are not what a small integer sets (bits 0-5 always on,
one-hot in 8-14); the same test on field 1 meant nothing.

**The degenerate subset.** `s4 == 24 + 24*n7` scores **100.00%** on the
Streaming family and looks like a decoded stride -- until rivals run beside it:
`24 + 32*n7`, `24 + 40*n7` and `24 + 44*n7` also score 100.00%, because
Streaming's `n7` is always zero and every candidate collapses to 24. On Init all
four score the same 46.47%, again exactly the `n7 == 0` subset. **Make the
rivals compete rather than check one and stop.** When a figure already
identified as the degenerate subset reappears as a match rate, it is the subset
talking, not the hypothesis.

## Slot 5: what the Init/Streaming pair shows

Comparing each chunk's two files element by element: element counts match in
every pair, and no element is byte-identical.

| slot-5 field | agrees across the pair |
| --- | --- |
| **field 1** | **100.0%** |
| **field 2** | **100.0%** |
| field 4 | 88.2% |
| field 3 | 9.7% |
| field 0 | 4.2% |
| **field 5** | **0.0%** |

Fields 1 and 2 never disagree and carry the fewest distinct values (5 and 11),
so they read as a **kind or type code identifying the same entry in both
files**; fields 0, 3 and 5 carry per-file quantities. **This partition is
invisible from either family alone.** Element vtable layouts match in only
2,930 of 7,433 pairs, so some fields are optional per file.

Fields 1 and 2 take `{5, 6, 8, 9, 10}` and `{1..10, 12}`, but only **19 of 55**
combinations occur, so they are coupled. A directory keyed by kind is refused
(3,410 of 7,433 files repeat an `(f1, f2)`), and so is a sort key (field 2 is
unordered in 2,226). **A test that cannot decide, recorded so it is not run
again:** `(f1, f2)` as a union tag predicts one vtable layout per kind; the
census gives 19 kinds against 16 layouts with only 6 kinds single-layout, which
looks like a refutation and **is not one** -- FlatBuffers omits fields equal to
their default, so one type legitimately yields several layouts. Separating the
cases needs the schema, not the bytes.

**Where this family stands.** At this `inputSetSha256`, slot 6 contains no
variation to index against, and slot 5's remaining questions reduce to a
19-value coupled code whose resolution needs the schema. Further mining needs a
different corpus, not a better test.

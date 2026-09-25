# What is settled, and what is open

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4.** The consolidated tables for every family in this directory, so a later session does
not re-derive them, plus the open questions stated accurately. Three inherited
blockers here turned out to be misdiagnosed on re-test, which is the single
highest-yield habit this topic records.

The consolidated conclusions for the families above, so a later session does not
re-derive them. Read this before reopening `InitChunkData`/`StreamingChunkData`
slot typing or the HIRC type coverage.

## `InitChunkData` / `StreamingChunkData` -- current slot-7 framing

| field | current reading | boundary |
| --- | --- | --- |
| 0 | `StreamingComponentType` mask, with optional collider bits and one-hot kind bits | selected enum and observed masks |
| 1 | count | multiplies the sum of field-3 descriptor strides to give the wrapped byte-vector length |
| 2 | centre and extents | spatial interpretation from paired chunk evidence |
| 3 | forward uoffset to a counted vector of 8-byte `(u16 anonymous id, u16 stride, u32 zero)` descriptors | exact framing and direct selected first-root consumer; descriptor 21 carries a NUL-terminated 63-byte name prefix duplicated with its ID in root rows across the current complete Init corpus; other descriptors remain open |
| 4 | forward uoffset, observed as `4`, to a one-field table wrapping a counted byte vector | exact framing and direct selected first-root consumer; the observed `4` is an offset, not a scalar constant |

Root slot 0 is version `47`; slot 1 is the chunk origin. Slots 2 through 7
are vectors: slot 2 is empty in the observed set; slots 3/4/5 are parallel
ids, packed words, and typed records; slots 6/7 are parallel. See
[`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) and the current
correction in [`world_chunk_unread_region.md`](world_chunk_unread_region.md).
Later historical hypotheses in this file do not override this framing.

## Audio -- the HIRC types the notes called SDK-only

**Settled by the installed Wwise 2023.1.17 SDK** (its static libraries carry the
deserializers as named object code; see [`audio_hirc_parser.md`](audio_hirc_parser.md)):
every type the corpus ships frames byte-exact from the engine's own grammar,
`0x02`-`0x07`, `0x09`-`0x0E`, `0x10`, `0x11` and `0x13`-`0x16` as lanes and `0x08`,
`0x12`, `0x03` named. The table below is what the game DLL alone gave; the music
types the shipped DLL skips are read by `AkMusicBank::LoadBankItem` in the music
engine, whose layouts are now framed.

| type | how reached | state |
| --- | --- | --- |
| `0x02`, `0x05`, `0x09` | one shared class; `[+0x1f0]`/`[+0x1f8]`/`[+0x200]` | **named**: `CAkParameterNodeBase::SetNodeBaseParams` |
| `0x0A`-`0x0D` | one shared arm | skipped by the shipped DLL; **framed** from `AkMusicEngine.lib` |
| `0x10`, `0x11` | `vtable[+0x28]` -> `0x18014c250` | **named**: `CAkFxBase::SetInitialValues` |
| `0x12` | `vtable[+0x278]` -> `0x180109030` | **complete**, and the same `CAkBus` class as `0x08` |

## Still open, accurately

- **`LAYER_C`'s managed field and encoded channel.** The selected UnityPlayer
  path loads `LAYER_C/D/N`; a checked consumer routes them through distinct
  owner-local handles and render-property IDs D/`_Splats`, N/`_Normals`, and
  C/`_ConeMaps`, with C conditional. A separate selected managed constructor
  directly copies eight `TextureResources` fields into
  `VirtualTextureRenderer`, including the two layer arrays and the color
  variation texture. The join from any installed `LAYER_*` file or native
  owner-local handle into those managed fields remains open, as does shader
  sampling. The separate six-file `Terrain_H/N/T/A/S/C` tile family has
  a checked render-property route: H/Heightmap, N/Normalmap, T/TintColor,
  A/Albedo, S/SplatCtrl, and C/CliffIndex. Neither `m_colorVariationTex` nor
  a mask-map reading for `LAYER_C` is established by the selected binding or field
  types; see [`world_terrain.md`](world_terrain.md) and the reviewed
  `terrain_layer_paths_native.json`/`terrain_layer_slots_native.json`/
  `terrain_virtual_texture_managed_native.json` contracts.
- ~~**`0x0B`'s `+12`/`+20` words.**~~ **CLOSED** by the SDK: they are the `sourceID`
  and `eventID` of the 44-byte playlist item `CAkMusicTrack::SetInitialValues` reads,
  and the whole type frames exactly.
- ~~**The 1 of 8 unowned media** that is not Init-bank embedded.~~ **IDENTIFIED** -- see
  below.

  *Reconciling two figures that look contradictory.* Pooling `hircMediaJoin` across all
  25 audited packages gives **61,333 declared media, 60,049 named, 1,284 unowned** --
  which sits oddly beside the recorded **61,325 of 61,333 (99.99%)**. They are the same
  join at two stages: `sourceIdsByPlugin` carries the type-`0x02` records only, and the
  note that **"adding `0x0B` closed 1,276 that no source record had named"** accounts for
  the gap exactly -- **1,284 - 1,276 = 8**. *Two numbers in these notes that read as a
  contradiction are the before and after of one step, and the arithmetic closes to the
  unit.* The pooled join also shows **948 source ids naming no declared media**, the
  reverse direction, which the cross-package trap predicts.

  ***The 8 named, and a correction.*** Pooling `idValuesByType` -- which carries `type02`
  (60,997 ids) **and** `type0B` (1,279) -- against the 61,333 declared media leaves
  **exactly 8**, reproducing the recorded figure from the raw data:

  | media id | declared in |
  | --- | --- |
  | 67918417, 133192886, 213132781, 792360875, 934360813, 1028758860 | `default_banks.pck` + `default_stream_0.pck` |
  | **624424588** | `default_banks.pck` + **`default_stream_2.pck`** |
  | **1041213772** | **`default_stream_0.pck` only -- no bank entry** |

  **The note above says "the same 7 ids are also declared as streamed copies in
  `default_stream_0.pck`. The 8th is in `default_stream_2.pck` only." Both halves are
  wrong.** Seven ids are in `default_banks.pck` -- the Init bank's `DIDX` media, as
  recorded -- but one of those seven streams from `default_stream_2.pck`, not
  `default_stream_0.pck`. And the odd one out is **`1041213772`**, which is in
  `default_stream_0.pck` *only* and has **no bank entry at all** -- so it is the media
  that is genuinely not Init-bank embedded, and it is not the one the note points at.

  *The characterisation was right in shape and wrong in both particulars, which is what
  happens when a set is described from its summary rather than enumerated.*
- **The other slot-7 descriptor payloads and their component labels.** The
  selected native path now follows the first paired root's slot 7 through
  each group's descriptor and wrapped byte vectors, consuming consecutive
  `group count * descriptor stride` byte regions. A complete current-corpus
  audit joins every descriptor-21 64-byte slot by ID and first-63-byte name
  prefix to a root row, while long full names lose their suffix in that slot.
  The selected native entity-name getter is only a candidate: its
  context pointer is not joined to descriptor 21's packed column, and the
  corresponding getter is absent from the selected IL2CPP type. The remaining
  gap is a checked mapping from descriptor IDs to named component consumers
  and a concrete runtime root/file receipt; the large
  residual runs have no certified record extent. See
  [`world_chunk_unread_region.md`](world_chunk_unread_region.md).

*Three blockers recorded earlier turned out to be misdiagnosed:* the chunk
reader's "packed native code" (it is in unpacked `UnityPlayer.dll`), the audio types'
"licensed SDK" (the parser ships with the game), and `StreamingComponentType`'s exclusion
(a one-byte read of a `ulong` enum). **Re-test an inherited blocker before
accepting it; that has been the highest-yield move in this family.**

*What made the difference:* field 0's mask reading survived because its bits
were **not** the bits a small integer sets -- bits 0-5 always on, one-hot in 8-14 -- which
no magnitude distribution produces. The same test on field 1 returned a high number and
meant nothing.

***A degenerate fit, caught by fitting four rivals at once.*** `s4 == 24 + 24*n7` scores
**100.00%** on the Streaming family, which reads like a decoded record stride -- until the
rivals are run beside it. `24 + 32*n7`, `24 + 40*n7` and `24 + 44*n7` **all score
100.00% too**, because Streaming's `n7` is *always* zero and every candidate collapses to
the constant 24. On the Init family all four score the same 46.47% -- again exactly the
`n7 == 0` subset. **The stride is unidentified, and the way to know that was to make the
rivals compete rather than to check one and stop.** Init's actual `s4` grows far faster
than linearly in `n7` (`n7=1` spans 188 distinct values; `n7=8` reaches 81,200), so it is
a byte size over variable-length records, not a count times a stride.

### THE PAIR SPLITS SLOT 5's FIELDS INTO INVARIANT AND VARYING -- WHICH ONE FAMILY CANNOT SHOW

Comparing each chunk's two files element by element, over **217,620 elements** in 7,433
pairs. The element counts match in **every** pair (0 differ), and **not one element is
byte-identical**:

| slot-5 field | agrees across the pair |
| --- | --- |
| **field 1** | **58,141 of 58,141 = 100.0%** |
| **field 2** | **100,822 of 100,822 = 100.0%** |
| field 4 | 88.2% |
| field 3 | 9.7% |
| field 0 | 4.2% |
| **field 5** | **0 of 81,172 = 0.0%** |

*Two fields never disagree and one never agrees.* Fields 1 and 2 also carry the fewest
distinct values in the corpus -- 5 and 11 -- so they read as a **kind or type code that
identifies the same entry in both files**, while 0, 3 and 5 carry per-file quantities.
**This partition is invisible from either family alone**: within `InitChunkData` all six
fields look alike, small integers with few distinct values. It took the pairing to
separate them.

Element *vtable layouts* match in only 2,930 of 7,433 pairs, so some of these fields are
optional and present in one file but not the other.

***What this does not establish.*** The natural follow-up -- that fields 0, 3 and 5 are
byte sizes summing to one of the scalars -- **fails**. Summing each across a chunk's
entries and testing against `s2`, `s3`, `s4` and the buffer length gives at best 16.70%,
and the one suggestive hit, `sum(field5) == s4 - 24` at **46.47%**, lands on **3,454**
files in *both* families -- the same recurring empty-chunk subset that every degenerate
fit in this family has produced. *When a number that has already been identified as the
degenerate subset turns up as a match rate, it is the subset talking, not the hypothesis.*
The scalars stay unexplained.

### THE KIND CODES ARE COUPLED, BUT NOT A SECTION DIRECTORY

Fields 1 and 2 -- the two that never disagree across the pair -- take
`{5, 6, 8, 9, 10}` and `{1..10, 12}`. Independent codes would give 55 combinations;
**only 19 occur**, so the two are coupled and carry less information than their ranges
suggest. Over **629,607** slot-5 elements:

| reading | result |
| --- | --- |
| a directory keyed by kind (each kind once per chunk) | **refused** -- 3,410 of 7,433 files repeat a `(f1, f2)` |
| a sort key | **refused** -- field 2 is unordered in 2,226 of 7,433 files |
| distinct `(f1, f2)` combinations | 19 of a possible 55 |

***A test that cannot decide, recorded so it is not run again.*** The remaining reading is
that `(f1, f2)` is a **union tag** selecting a record type, which predicts one vtable
layout per kind. The census gives 19 kinds against 16 layouts, with only **6 of 19** kinds
showing a single layout -- which looks like a refutation and **is not one**. *FlatBuffers
omits any field whose value equals its default*, so a single type legitimately produces
several layouts depending on which fields happen to be defaulted. Layout spread within a
kind is uninformative here, in both directions. **The union reading is neither supported
nor refused by this evidence, and re-running it will not change that** -- separating the
cases needs the schema, not the bytes.

**Where this family stands.** Slots 5 and 6 are not unindexed for want of effort -- at
this `inputSetSha256` **slot 6 contains no variation to index against at all**, and slot
5's remaining questions are now pinned to a 19-value coupled code whose resolution needs
the schema. Further mining needs a different corpus, not a better test.

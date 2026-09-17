# The second family, and the index that names both

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** `StreamingChunkData` shares the schema recovered in
[`world_chunks_schema.md`](world_chunks_schema.md) and carries none of the
placements. Having the pair is what splits the slot fields into invariant and
varying, so the slot files depend on this one. It also records the full-corpus
gate and where the native reader actually lives.

## `StreamingChunkInfo`: the per-level chunk index, and it checks out against the filenames

Asking what *else* lives in the directory turned out to be worth more than any amount of
further staring at the chunk payloads. Each level's `Data/Streaming/PC/<level>/Streaming/`
holds three families:

| file | per level |
| --- | --- |
| `InitChunkData_<x>_<y>_0_0.bytes` + `InitChunkData_Global_#_#.bytes` | one per chunk |
| `StreamingChunkData_<x>_<y>_0_0.bytes` + `_Global_` | **the same coordinates, paired 1:1** |
| **`StreamingChunkInfo.bytes`** | **exactly one -- the index** |

**The index is not in the terrain container at all.** It decodes with the terrain codec
**0 of 89** times, because it is a *plain, uncompressed FlatBuffers buffer* -- root
uoffset 16, vtable immediately after. Its neighbours in the same directory are all
codec-wrapped. *Sharing a directory does not mean sharing a container, and trying the
neighbour's codec first is what established that cheaply.*

**Framing, from the bytes.** 89 files, two root layouts and one element layout:

```
root   (4, 8, 12, 16) objectSize 20      x88        slot 3 = the chunk vector
root   (4, 8, 12)     objectSize 16      x1         DevOnly -- no slot 3
element (4, 12)       objectSize 16      x23,806    ALL of them, one layout
   field 0  8 bytes = two int32   the chunk's (x, y) grid coordinates
   field 1  4 bytes               the constant 4, in 23,806 of 23,806
```

Totals: **23,806 chunks indexed** across 88 levels, and exactly **88 sentinel entries** --
`(INT32_MIN, INT32_MIN)`, **one per level**, which is the `_Global_` chunk.

### THE INDEX AGREES WITH THE FILENAMES EXACTLY, 88 OF 88

The reading makes a prediction with nothing fitted to it: for every level, the set of
coordinates *inside* the index equals the set of coordinates *in the filenames beside it*.
It can fail in both directions -- an index entry with no file, or a file with no entry.

| | levels |
| --- | --- |
| **exact set equality** | **88 / 88** |
| any mismatch, either direction | **0** |
| index did not frame | 1 (`DevOnly`, whose root has no slot 3) |
| **control: matches a *different* level's files** | **1 / 88** |

*Note the coordinates here are raw grid indices* -- `(-2, 0)`, `(-1, 1)` -- **not** scaled
by 128 the way `InitChunkData`'s own origin field is. The same quantity is stored in two
units in two places, which is exactly the sort of thing that makes a name-based guess go
wrong and a join go right.

***The control deserves its own note, because the single hit is real and not a weakness.***
One adjacent pair of levels does share an identical chunk set -- because the data genuinely
repeats: **73 distinct coordinate sets cover 88 levels**, with **14 levels sharing one
65-chunk set** and 2 sharing a 257-chunk set. Those are instanced layouts. So the control
fires where the world actually is duplicated, and nowhere else. *A control that returns
exactly zero is sometimes a control that cannot fire at all; this one could, did once, and
for a reason that is visible in the data.*

## `StreamingChunkData` shares the schema -- and carries none of the placements


The paired family, over the same single-digit coordinate slice (**7,433 files each**, so
14,866 in total; the full family is larger):

- **7,433 of 7,433 decode with the terrain codec**, and show **one** root layout --
  `(4, 8, 16, 20, 24, 28, 32, 36)`, objectSize 40 -- *identical* to `InitChunkData`'s.
- **Slot 1 is the chunk origin here too: `(x*128, y*128)` in 7,433 of 7,433**, with the
  axes-swapped control at the same 633 symmetric cases. *This prediction was made from the
  Init family and tested on a family that had no part in fitting it.*
- **Slot 0 is the constant 47 in all 14,866 files of both families** -- a format version
  shared across the pair.

So the two are **one schema**. What separates them is population, and the split is total:

| | Init | Streaming |
| --- | --- | --- |
| slot 7 (placements) empty | 3,454 (46.47%) | **7,433 (100.00%)** |
| slot 5 length equal to its partner's | — | **7,433 (100.00%)** |
| byte-identical to its partner | — | **0 (0.00%)** |

***The naming intuition is backwards.*** `StreamingChunkData` carries **no placements at
all** in this slice, while `InitChunkData` carries them in 53.53% of chunks. Whatever
distinguishes the two files, it is not that the "streaming" one holds the streamed
objects. Their slot-5 vectors are the same length in every single pair, yet no pair is
byte-identical.

## THE SCALAR SLOTS ARE SIZES, AND ONE EXACT RELATION TIES THEM TO SLOT 5

`s2 = s3 + 8 + 4 * len(slot5)` in **14,866 of 14,866 files**, both families, no
exceptions. Since a FlatBuffers vector occupies `4 + 4n` bytes, the gap between these two
scalars is exactly slot 5's serialized footprint plus four of alignment.

They are **not** offsets into the buffer: `s3 == slot-5 vector base`, `s2 == buffer
length` and every related test score **0.00%**.

### SOLVED: they are payload sizes, and the formula is exact

Chasing the residual rather than the value settled it. `len(buffer) - s2` takes **exactly
two values** across all 7,433 Init files -- **44** (4,220) and **48** (3,213) -- and each
is fully determined by where the root table sits:

```
residual 44  <->  root at 24     4,220 of 4,220
residual 48  <->  root at 28     3,213 of 3,213
```

which is `rootOffset + 20`, and 20 is the root vtable's own size (4 header + 2x8 slots).
So:

| | Init | Streaming |
| --- | --- | --- |
| **`s2 == len - root - 20`** | **7,433 / 7,433 = 100.00%** | **0.00%** |
| **`s3 == len - root - 28 - 4*n5`** | **7,433 / 7,433 = 100.00%** | **0.00%** |
| control: `len - root - 16` / `- 24` | 0.00% | 0.00% |
| control: `len - 20`, dropping the root term | 0.00% | 0.00% |

**`s2` is the size of everything past the root vtable -- the serialized payload -- and
`s3` is that same size minus slot 5's vector footprint** (`4 + 4n` for the vector, plus 4
of alignment). The earlier exact relation `s2 = s3 + 8 + 4*n5` was these two formulas
seen from the side, with the length and root terms cancelling.

***That the same field means nothing of the sort in `StreamingChunkData` is the sharper
half.*** Every formula and control scores **0.00%** there, and `len - s2` spreads over
**845** distinct residuals. The two families share a root *layout*, a version constant and
a chunk origin -- and still do not agree on what slot 2 counts. *A shared schema does not
guarantee a shared meaning per field, and nothing short of testing the second family would
have shown it.*

## FULL-CORPUS GATE: 26,520 files per family, every claim re-run

Everything above was established on the single-digit coordinate slice. The gate re-runs it
over the whole family, and the headline is that **62.47% of the corpus -- 16,568
multi-digit-coordinate files -- had never been tested at all**, alongside 148 `_Global_`
files carrying no coordinate pair.

| claim | Init | Streaming |
| --- | --- | --- |
| total files | 26,520 | 26,520 |
| decoded with the terrain codec | 26,519 | 26,519 |
| **decode failed** | **1** | **1** |
| root layout `(4,8,16,20,24,28,32,36)`/40 | **26,519 / 26,519** | **26,519 / 26,519** |
| slot 0 == 47 | **26,519 / 26,519** | **26,519 / 26,519** |
| origin == `(x*128, y*128)` | **26,372 / 26,372**, 0 mismatches | **26,372 / 26,372**, 0 mismatches |
| origin unsupported (`_Global_`) | 147 | 147 |
| `s2 == len-root-20` | **26,519 (100.00%)** | **0 (0.00%)** |
| `s3 == len-root-28-4n5` | **26,519 (100.00%)** | **0 (0.00%)** |
| slot 7 (placements) empty | 20,517 (77.36%) | **26,519 (100.00%)** |

**Everything held, including on the 62% never previously seen.** And one slice-level
finding is *strengthened* rather than merely confirmed: `StreamingChunkData` carries
**no placements in any of its 26,519 decodable files, corpus-wide** -- not a property of
the sampled coordinates.

***The two failures are the same level, and they fail loudly.*** Both are `DevOnly`'s
`_Global_` files, rejected by the codec with `match offset 0 reaches before the output` --
a refusal, not a silent truncation. `DevOnly` is the consistent outlier in this family: it
is also the one level whose `StreamingChunkInfo` root has 3 slots instead of 4.

### THE TWO FILES DISAGREE ABOUT HOW TO SPELL "GLOBAL"

All **294** decodable `_Global_` chunk files carry **one** origin value:

```
StreamingChunkInfo entry for the global chunk   (INT32_MIN, INT32_MIN)
InitChunkData_Global_* own origin field         (INT32_MAX, INT32_MIN)
```

*Same concept, two different sentinels, in files that sit in the same directory and
describe the same chunk.* The earlier 88-of-88 index join survived only because it matched
on **filenames**, not on origin values -- a join written the other way would have scored
zero and read as a refutation of a correct reading.

## THE `streaming` VFS BLOCK IS NOW FULLY INVENTORIED

A bounded completeness claim, which is worth more than another partial one. Streaming the
block with a filter that **excludes** the three known families returns **0 files**, so
nothing else is in there. The totals close exactly:

| family | files |
| --- | --- |
| `InitChunkData_<x>_<y>_0_0.bytes` | 26,372 |
| `InitChunkData_Global_#_#.bytes` | 148 |
| `StreamingChunkData_<x>_<y>_0_0.bytes` | 26,372 |
| `StreamingChunkData_Global_#_#.bytes` | 148 |
| `StreamingChunkInfo.bytes` | 89 |
| **total** | **53,129 files, 719.4 MB** |

and the five shapes sum to 53,129 with nothing left over. **Every family in this block is
framed, and the framing is gated over all of it.** Two files -- `DevOnly`'s `_Global_`
pair -- are reported as codec refusals rather than skipped.

***The schema is not shipped, and that is now checked rather than assumed.*** Streaming
the `table`, `json-data`, `extend-data` and `initial-extend-data` blocks for
`*.fbs`, `*.bfbs`, `*.schema` and `*.proto` returns **0 files**. So the two things still
unknown here -- what a slot-7 element *is*, and what slot 5's 19-value coupled code
selects -- **cannot be settled from the shipped data at all**. They need the native
reader. *That is a different statement from "not yet found", and it is the one the
evidence supports.*

### WHERE THE NATIVE READER LIVES, AND WHY IT IS NOT READABLE

"Needs the native reader" is worth replacing with a measurement. The game ships
**`EndfieldBase.dll`, 35.8 MB**, which is the module that would hold a C++ FlatBuffers
reader -- and it yields **nothing**:

| probe | ASCII | UTF-16 |
| --- | --- | --- |
| `InitChunkData`, `StreamingChunkData`, `StreamingChunkInfo` | 0 | 0 |
| `ChunkData`, `Terrain`, `IrradianceVolume` | 0 | 0 |
| `flatbuffers`, `FlatBuffer` | 0 | 0 |

Section entropy says why:

| module | section | raw bytes | entropy |
| --- | --- | --- | --- |
| **`EndfieldBase.dll`** | **`.tvm0`** | **28,246,016** (79% of the file) | **7.60** |
| `HGP.dll` | `.tvm0` | 9,003,008 (92%) | **7.56** |
| `GameAssembly.dll` | `.tvm0` | 13,463,552 | 6.94 |
| `GameAssembly.dll` | `.text` / `il2cpp` | 11.2 MB / 165 MB | 6.46 / 6.35 |

**`EndfieldBase` is four fifths virtualised**, with the leftover `.rdata` at entropy 4.93
and odd companion sections (`.BNN`, `.i,9`) typical of a code virtualiser. `HGP.dll` is
the same construction plus `.detourc`/`.detourd` -- a detour engine, itself virtualised.

*This also explains the shape of every success so far.* `GameAssembly.dll`'s `.text` and
`il2cpp` sections are **not** packed, which is exactly why the managed metadata work keeps
paying -- 73 generated FlatBuffers types, field widths, `Il2CppFieldOffsets`. The moment a
question needs a *native* body, it moves into a `.tvm0` section and the evidence stops.
**The boundary is not "IL2CPP vs native"; it is "packed vs not", and it runs through
GameAssembly itself.**

#### CORRECTION: THE CEILING ABOVE IS WRONG -- I MEASURED THE WRONG MODULE

The paragraph this replaces concluded that every remaining question needs 28 MB of
entropy-7.6 bytes and that static recovery cannot reach it. **That is false, and the error
was testing `EndfieldBase.dll` because it looked like the right module rather than
following the evidence to the module that actually holds the code.**

**`UnityPlayer.dll` -- 33.1 MB, `.text` 25,530,880 bytes at entropy 6.52, not packed**
(its `.tvm0` is only 1.49 MB). This is a *heavily modified* Unity player carrying the
engine-side HyperGryph code with readable symbols:

| evidence in `UnityPlayer.dll` | count |
| --- | --- |
| `HyperGryph` symbols | **866** |
| `FlatBufferConvertContext` | 14 |
| `HG_ALWAYS_ASSERT failed on expression: '...'` | many, expression text intact |
| mangled `BindProxyEntityConvertFuncFromScript@HGStreamingSceneManager@HyperGryph@@...W4ProxyEntityType@3@` | present |
| `PropertySerializeId::GetComponentIndexFromType` | present |

### AND THE FILENAMES ARE BUILT HERE, WHICH CORRECTS A SECOND CONCLUSION

The earlier note reasoned that because no complete `InitChunkData_` literal exists in
`global-metadata.dat` or `GameAssembly.dll`, the files must be "addressed by catalogue id
or hash". **The premise was right and the conclusion was wrong.** The format strings are
in `UnityPlayer.dll`, immediately beside the literals `Init` and `Streaming` that fill
their `{1}` slot:

```
{0}/{1}{2}ChunkData_{3}_{4}_{5}_{6}.bytes
{0}/{1}{2}ChunkData_Global_{3}_{4}.bytes
   ... adjacent literals: "Streaming", "Init"
```

*A search for `InitChunkData_` could never have found this, because the name does not
exist anywhere as one string.* **A negative string search bounds where a literal is, not
where the behaviour is** -- and I turned the first into the second.

So the native reader is **not** behind the virtualiser. `EndfieldBase.dll` (79% `.tvm0`
at 7.60) and `HGP.dll` (92% at 7.56) are packed and stay unreadable, but they are not
where this code lives. **The route is open, via `UnityPlayer.dll` and the
`UnityEngine.HyperGryph.Streaming` namespace.**

### THE NEW SOURCE: `UnityEngine.HyperGryph.Streaming`

35 types in the IL2CPP metadata, engine-level rather than game-level, including the enums
a chunk record would plausibly reference:

| enum | members |
| --- | --- |
| `StreamingLayer` | Default, Persistent, HLOD0, HLOD1, HLOD2, Collider, Tiny, Water, Lighting, Audio, RendererWithCollider, Count |
| `ProxyEntityType` | IrradianceVolume, AudioVolume, AudioEmitter, AudioRoom, TerrainSurfaceTypeData, AudioPortal, SOCChunk, GrassGrid, GpuClothGroup, TreeGrid, GPUParticleSystem, TypeCount |
| `StreamingComponentType` | 45 members |
| `StreamingMode` | Stream, Pause, Teleport, Unload, TeleportUnload, TeleportLoad |
| `StreamingStatus` | Idle, Loading, Unloading, Empty |

***And `ProxyEntityType` is refused as the slot-5 kind code, despite reading perfectly.***
Its members are exactly the things a chunk places, which is the most seductive name match
in this whole family. It has an external anchor, so it is testable: the `iv` block
independently gives each level's IrradianceVolume count. Scoring **all 28** kind codes:

| | result |
| --- | --- |
| codes whose per-level total equals the IV count | **0 of 28, on 0 of 88 levels** |
| **positive control**: levels where *some* code equals the IV count | **17 of 88** -- the test can fire |
| slot-5 entries per level | median **4,861**, max 535,440 |
| IrradianceVolumes per level | median **1**, max 14 |

Three orders of magnitude apart. **Slot 5 is not a placement list at all**, whatever its
codes mean. *The positive control is what makes the zero worth anything: without it, a
test that cannot fire and a hypothesis that is false look identical.*

### WHAT THE ENGINE'S OWN ASSERTS AND LOGS SAY -- AND WHAT THE DATA DOES WITH IT

`UnityPlayer.dll` keeps its `HG_ALWAYS_ASSERT` expression text and log formats, which is
vocabulary straight from the authors:

```
fbMonoEntityData->componentDataList()->Get(0)->type() == kComponentTypeTransform
!fbMonoEntityData->componentDataList()->empty()
componentType != kComponentTypeNone        entityType != kECSEntityTypeCount
entityType != kProxyEntityTypeCount        transition < EntityTransition::Count

"Missing chunk file at %d,%d,%d, lod %d"   "Unexpected chunk status %u when load"
"Unsupported Proxy entity type %u to ConvertFrom"   "[Streaming] Failed to load %s"
```

The first line is **literal FlatBuffers accessor code**: a table `MonoEntityData` with a
`componentDataList()` vector whose elements carry a `type()`, and element 0 is always a
Transform. Three bind functions sit beside it -- `BindMonoComponentConvertFuncFromScript`
(`StreamingComponentType`), `BindProxyEntityConvertFuncFromScript` (`ProxyEntityType`),
`BindECSEntityConvertFuncFromScript` (`ECSEntityType`) -- **three entity categories
against the root's three vector slots.** That is the same matching-counts shape already
refused twice in this family, so it is left as a lead, not a conclusion.

***Two readings this vocabulary suggests, both refused by the bytes.***

**`componentDataList` is not slot 5.** The assert predicts element 0 has one fixed type.
Across all 26,372 files, slot-5 element 0 carries **15 distinct kind codes**, the most
common covering 66%. Not a constant, so this vector is not that one.

**The filename's fourth field is not a lod.** `Missing chunk file at %d,%d,%d, lod %d`
invites reading `InitChunkData_<x>_<y>_<z>_<w>` as x/y/z/lod. The distribution says
otherwise: `w` is **0 in 26,070 of 26,372** files, and where it is not it takes values
like **587717614** and **293885694** -- confined entirely to **one level, `map02`**
(302 files). A lod index does not look like that. *A log format string names the
engine's addressing, not necessarily the filename's.*

#### A refinement to the StreamingChunkInfo join

The third field *does* vary -- `z` runs 0..7+ -- and **7 of 88 levels hold more chunk
files than distinct `(x, y)` pairs**: `map01` has 7,599 files over 6,028 columns, `map02`
1,952 over 1,229. So chunks are addressed by more than `(x, y)`.

This does not break the earlier 88-of-88 index result, which compared **sets** of
coordinates and so collapsed the `z` variants harmlessly -- but it does correct the
impression that index entries and chunk files stand 1:1. **The index carries one entry per
`(x, y)` column; the files are per `(x, y, z)`.** *The test was sound and its natural
reading was not, which is a failure mode worth naming: set equality proves set equality,
and nothing about multiplicity.*

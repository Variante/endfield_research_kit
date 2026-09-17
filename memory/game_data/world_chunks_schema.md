# `InitChunkData`: a FlatBuffers schema read from the bytes

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** The same container as terrain, but the payload inside is
FlatBuffers with no schema shipped. This file recovers the root and element tables
from the bytes alone, then joins slot 1 to the filename to find the world
placements -- the single most productive move in this family.

## `InitChunkData`: the same container as terrain, and a named FlatBuffers schema

**26,520 files, 624 MB** -- the largest `.bytes` family by file count. Streaming a
312-file slice (`InitChunkData_-1_-1_0_0.bytes`, which recurs across scenes):

- **312 of 312 decode with the maintained terrain codec.** The custom LZ4 with
  big-endian offsets and bit-interleaved tokens in
  `scripts/asset_builder/terrain_stream.py` -- built for `Terrain_*` -- decodes these
  byte-exactly, each to the length its own leading word declares. *The container is
  shared across two families that no naming convention connects.*
- **All 312 decoded payloads are valid FlatBuffers**: root offset in range, vtable
  reachable, and a root table of **8 vtable slots** in every one.

The schema is named in the IL2CPP metadata:

```
Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneChunkData
    Version, StreamingVersion, UniqueId, Grids[], TotalStr[]

Beyond.Gameplay.Core.DynamicScene.FBDynamicSceneSingleGrid   (278 methods)
    UniqueId, SceneVisibleStateInts, SceneVisibleAreaInts, PrimitiveIntList,
    PrimitiveStringList, DataIndex, Vector3, Model, Effect, Ecs, EcsModel,
    DataGroup, ResourceGroupWithStateDesc, NavModifyArea, MountPair, IntStrMapEntry,
    MissionCondition, IdComp, SeatComp, PureFuncComp, TriggerComp, HittableComp,
    FactoryBlockComp, DynamicEntityControlComp, NavModifyAreaComp,
    InteractiveStateComp, ViewStateControlComp, MissionControlComp,
    GlobalVarControlComp, SettlementControlComp, FactoryRegionControlComp,
    ScriptControlComp, ResourceComp, RootComp, TreeRootComp, DecorationRootComp,
    ErosionRootComp, ModelViewStateControllerNewComp, ConveyorBeltComp,
    ConveyorBeltBoxComp, ConveyorBeltGroupComp, ConveyorPath, PureSystemComp,
    NatureResourceComp, SludgeComp, Bounds, ExtraSceneComp, SceneGridInfo,
    RemapSceneComp, WaterPipeComp, StreamingAreaComp, NavmeshObstacle,
    MapVarControlComp, ActivityCondition, ActivityControlComp, PoiControlComp,
    BlightMiasmaComp, LodGridResource, SnowFallTreeComp, Desc, **DataMask**
```

- ***`DataMask` is in there***, the field this file's own Remaining-gaps list names as
  unresolved. It is a field of `FBDynamicSceneSingleGrid`, alongside sixty-odd
  component vectors that say what a scene grid holds: conveyor belts, nav-mesh
  obstacles, mission conditions, factory blocks, erosion and sludge, POI control.
- Smaller schemas named alongside: `FBDynamicSceneActivityControlComp`
  (`Conditions`, `CompareType`, `ToBeTrue`), `FBDynamicScenePoiControlComp` (`Id`,
  `DomainType`), `FBDynamicSceneSingleGridDescriptor` (`Scene`, `Ranges`),
  `FBDynamicSceneVersionData` (`Entries`, `Major`, `Minor`).

### TESTED AND DISPROVED: the root is not `FBDynamicSceneChunkData`

The previous paragraph said the schema was *named*, not matched, and flagged the match
as unproven. It is now tested, and it fails.

- **Reading the 8 slots as the declared field order does not work.** `Grids` and
  `TotalStr` produce **identical** length distributions -- 1 in 46 files, 5 in 16, 3 in
  16, 4 in 15 -- which two independent vectors would not. And walking the supposed
  `Grids` elements, **0 of them resolve to a table**, in every file.
- **No declared root type has 8 fields.** The whole image contains exactly **six**
  FlatBuffers types with a `GetRootAs*`: `FBDynamicSceneChunkData` (5),
  `FBDynamicSceneSingleGrid` (61), `FBDynamicSceneSingleGridDescriptor` (2),
  `FBDynamicSceneVersionData` (3), `FBFactoryChunkData` (5) and
  `FBStreamAreaTotalData` (7). **None is 8.**
- The root's inline object is **40 bytes** in all 312 files, consistent with eight
  4-byte fields plus the vtable offset -- so the 8 slots are real fields, not deprecated
  holes.

**So `InitChunkData` is a FlatBuffer whose schema has no generated C# accessor.** Like
the IrradianceVolume payload, it is read natively; the `FBDynamicScene*` classes are a
different family that happens to sit in the same namespace.

***A schema that fits the subject matter is not thereby the schema of the file.*** The
sixty component names -- conveyor belts, nav-mesh obstacles, sludge, POI control --
described a scene grid so plausibly that it read as a match. The vtable disagreed in
two independent ways within one test.

**What survives, all of it measured from the bytes:**

| | |
| --- | --- |
| terrain codec decodes | **312 / 312**, each to its declared length |
| decoded payload is a valid FlatBuffer | **312 / 312** |
| root vtable slots | **8**, in every file |
| root inline object size | **40 bytes**, in every file |
| slot 0 | **constant 47** across all 312 -- a version, on any reading |

### The root schema, read from the bytes with no schema at all

**One vtable layout in all 312 files** -- offsets `(4, 8, 16, 20, 24, 28, 32, 36)` with a
40-byte inline object -- so every field's width falls out of the gaps, exactly as the
IrradianceVolume config layout did:

| slot | offset | width | type, from what it points at |
| --- | --- | --- | --- |
| 0 | +4 | 4 | **`u32` = 47 in all 312** -- a version |
| 1 | +8 | **8** | 64-bit scalar |
| 2 | +16 | 4 | `u32` scalar (289 of 312 read as one) |
| 3 | +20 | 4 | **vector** (277 plain, 22 also table-like) |
| 4 | +24 | 4 | **vector** |
| 5 | +28 | 4 | **vector of tables** -- all 312 |
| 6 | +32 | 4 | **vector of tables** -- all 312 |
| 7 | +36 | 4 | **vector of tables** -- all 312 |

Each vector-of-tables classification is earned: the vector length is read, then the
first elements are followed as uoffsets and each must land on a table whose vtable
resolves. **Slots 5, 6 and 7 pass that in every file.**

**That single layout is itself the evidence.** 312 files of wildly different sizes --
171 bytes to 4.5 MB -- share one vtable byte-for-byte, so they are one schema, and the
typing is a statement about that schema rather than about a sample.

**And it independently confirms the disproof.** `FBDynamicSceneChunkData` is three
scalars and two vectors. This root is **three scalars (one of them 64-bit) and five
vectors, three of which hold tables**. They are not the same shape, which is a second,
structural reason beyond the failed vector walk.

### The element tables, also read from the bytes

Walking the three vector-of-tables slots and collecting every element's vtable:

**Root slot 5 -- 7,272 element tables**, three layouts:

| slots | inline object | field widths | count |
| --- | --- | --- | --- |
| 6 | 40 | 4, 4, 4, 4, **16**, 4 | 4,294 |
| 4 | 20 | 4, 4, 4, 4 | 733 |
| 6 | 44 | 4, 4, 4, 4, **20**, 4 | 675 |

**Root slot 6 -- 642 element tables**, a single layout: **1 slot, 8-byte object, one
4-byte field.** No variation at all.

**Root slot 7 -- 642 element tables**, two layouts:

| slots | inline object | field widths | count |
| --- | --- | --- | --- |
| 5 | 60 | **20**, 4, **24**, 4, 4 | 430 |
| 5 | 56 | **16**, 4, **24**, 4, 4 | 212 |

- **Slots 6 and 7 are parallel arrays.** Identical vector-length distributions in every
  file -- 0 in 48 files, 1 in 166, 2 in 49, 3 in 14, 4 in 5 -- and **exactly 642 elements
  each**. Two vectors that agree on length in all 312 files are indexed together.
- **The 16, 20 and 24-byte fields are inline structs**, which is the only thing a
  FlatBuffers field of that width can be -- four, five or six 32-bit values held in the
  table rather than behind an offset. The 16-versus-20 variation in slot 5 and the
  16-versus-20 in slot 7 are the same choice appearing twice.
- Slot 5's population is a different scale entirely: 7,272 elements against 642, with
  its own length distribution.

**Where this family now stands**, all from the bytes and none of it from a schema:

| | |
| --- | --- |
| container | terrain codec, **312 / 312** |
| format | valid FlatBuffers, **312 / 312** |
| root | 8 fields: 3 scalars (one 64-bit), 2 vectors, 3 vectors-of-tables -- one layout in all 312 |
| element tables | typed for all three vector slots, 8,556 tables read |
| managed schema | **excluded twice** -- failed vector walk, and no declared root has 8 fields |

### ROOT SLOT 1 IS THE CHUNK'S WORLD ORIGIN, joined to the filename

The first field in this family with a *meaning*, and it came from a join rather than a
name. Streaming **7,433** files across **361** distinct grid coordinates:

```
root slot 1, at table offset +8, eight bytes = two int32
    +8  == x * 128        where x, y are the coordinates in
    +12 == y * 128        InitChunkData_<x>_<y>_0_0.bytes
```

**7,433 of 7,433**, with the controls failing as they should:

| reading | files |
| --- | --- |
| `+8 = x*128, +12 = y*128` | **7,433 / 7,433** |
| axes swapped | 633 -- exactly the `x == y` cases where both readings coincide |
| scale 64 or 256 | 85 -- exactly the origin chunks, where every scale gives 0 |

So the 64-bit field is the chunk's **world-space origin**, and **128 is the chunk size
in world units**. The 361 distinct coordinate pairs map to 361 distinct field values,
one-to-one.

***This also explains how the wrong schema looked right.*** Under
`FBDynamicSceneChunkData` this slot read as `StreamingVersion`, with values 4294967168
and 128 -- which is `0xFFFFFF80`, i.e. `-128`, i.e. `x * 128` for `x = -1`. A plausible
name made a coordinate look like a version number. *The join to the filename settles in
one test what no amount of reading the field alone could.*

### THE SLOT-7 ELEMENTS CARRY WORLD PLACEMENTS, found by joining to that origin

With the chunk origin known, the chunk is a **box in world units**, and a box is
something the other slots can be tested against. Over the same 7,433 files:

**Slots 5 and 6 are not spatial at all.** Every float-shaped field in them is
**0.0% non-denormal** -- the bytes are small integers, and reading them as float gives
denormals near zero. *Their apparent "box hits" in the first pass were entirely that
artefact:* a denormal lands in whatever box straddles zero, which is why own-box and
neighbour-box scored identically (28.9% vs 28.8%). **A test whose control matches it is
measuring the control.**

**Slot 7's element field 2 is a 24-byte inline struct of six floats.** Both element
shapes give it 24 bytes (`obj 60`: offsets 28..52; `obj 56`: 24..48), and it is either
**wholly zero or wholly populated, with zero exceptions**:

| | elements |
| --- | --- |
| all 24 bytes zero (unset) | 3,904 |
| populated | 7,112 |
| *records mixing the two* | **0** |

**The first triple is a world-space position, `(x, height, z)`:**

| reading | share of 7,112 |
| --- | --- |
| **f0 in own chunk's x, f2 in own chunk's z** | **73.96%** |
| same test against a neighbour chunk (control) | **1.28%** |
| `(f0, f1)` as the two axes -- the non-Y-up reading | 6.25% |
| rotations `(f1, f0)`, `(f2, f1)` (controls) | 1.92%, 1.91% |

A **58-fold** margin over the spatial control. The axis assignment is then confirmed a
*second* time, without using the box at all -- by sign:

```
axis 0 negative  61.7%      axis 1 negative   4.9%      axis 2 negative  48.2%
```

The middle axis is the one that stays positive, which is what a height does and what a
horizontal coordinate does not. *Two independent lines, one from geometry and one from
sign, pick the same middle float.*

**The second triple is non-negative, always.** 0 of 21,336 components negative across
7,112 records, range 0..687 -- while the position triple in those same records is
negative 61.7%/4.9%/48.2% of the time. It is **not** a second position (2.18% own box
against a 2.26% control -- chance), not a unit quaternion (lengths 411..693), not a
scale (magnitudes in the hundreds). An extent is consistent with all of it, but nothing
here *discriminates* an extent from any other non-negative triple, so it stays
**structural-only**.

***Disproved along the way:*** the six floats as a min/max bounding box. `min <= max`
componentwise holds for 38.52% -- **below** its own reversed control at 43.22%, and level
with a shuffled pairing at 37.69%. *The reversed control outscoring the claim is the
cleanest possible refutation, and it cost one run.* The `f3..f5 >= 0` check scored
100.00% in that same run and meant nothing, because the unset records were still in the
denominator; it only became evidence once the population was restricted to the 7,112 and
the position triple supplied the contrast.

### THE ELEMENT'S FIRST FIELD IS A DESCRIPTOR THAT STATES ITS OWN CATEGORY TWICE

Field 0 is 16 bytes at offset +4 and takes only **34 distinct values** across 11,016
elements -- a vocabulary, so a type or flag word, not a per-instance identifier. Read as
eight u16 it comes apart cleanly.

**It partitions the placements perfectly.** Of the 34 values, **0 occur both placed and
unset**: 2 values are unset-only (3,831 + 73 = exactly the 3,904 unset records) and 32
are placed-only. Byte 1 alone carries it -- non-zero for **7,112 of 7,112** populated and
zero for **3,904 of 3,904** unset.

**Byte 1 is one-hot, without exception**: 7,112 of 7,112 are a single set bit, drawn from
`{01, 02, 04, 08, 10, 20}`. A byte that happened to be one-hot would manage it 8 times in
256.

**The fifth u16 restates the same category, shifted four bits.** Writing `byte1 = 2^k`,
that word carries the bits `8 | 2^(k+4)`:

| test | share |
| --- | --- |
| **w4 carries the bits for k** | **6,570 / 6,570 = 100.00%** |
| same test with k+1 (control) | **0.00%** |
| same test with k-1 (control) | **0.00%** |

*Both shifted controls at exactly zero is the strongest form this evidence takes:* the
relation is not merely frequent, its neighbours are impossible. The census is conditioned
on the `w1 == 0x2024` family (6,570 elements); the other families, `0x0820` (393) and
`0x1020` (149), leave w4 zero. Eight elements carry the predicted bits *plus* one extra
bit (73 = 72|1, 137 = 136|1, 4360 = 264|4096), which is why the relation is a **subset**
test and not equality -- as equality it would have shown 8 spurious counter-examples.

**Field 4 is the constant 4** in all 11,016 elements.

***Disproved:*** field 3 as an index into a sibling vector. Its 2,136 distinct small
integers look exactly like indices, but they fall inside slot 5's length only 4.37% of
the time and inside slots 6 and 7 **never**. Field 1 scores 90.45% against slot 5, which
is not evidence either -- its values are 1, 2 and 4, and *any* small integer clears that
bound. **A containment test only discriminates when the candidate could plausibly fail.**

### THE 24-BYTE FIELD IS `FBDynamicSceneBounds`, AND THE NAME COMES FROM IL2CPP

The name from outside arrived. IL2CPP carries **73 generated FlatBuffers types**, 65 of
them in **`Beyond.Gameplay.Core.DynamicScene`** -- so InitChunkData belongs to the
DynamicScene family, and its generated vocabulary is readable:

| type | components | bytes |
| --- | --- | --- |
| `FBDynamicSceneVector3` | X, Y, Z (Single) | 12 |
| **`FBDynamicSceneBounds`** | **Center, Extents (Vector3)** | **24** |
| `FBDynamicSceneVisibilityInfo` | Center, BaseRadius, MinDis, Importance | 24 |
| `FBDynamicSceneTransform` | Pos, Rot, Scl (Vector3) | 36 |
| `FBDynamicSceneLodGridChain` | Lod0Grid, Lod1Grid, Lod2Grid (UInt32) | 12 |
| `FBDynamicSceneDataIndex` | IsInvalid, Type, Grid, Index | 13 |

**`Bounds` explains every byte-side observation at once**, and it was found by matching
the *shape* -- a 24-byte inline struct of six floats -- not by matching a name:

- **Center** is the first triple: a world position, in its own chunk 73.96% against a
  1.28% control
- **Extents** is the second triple, and an extent is a **half-size, so never negative** --
  which is exactly the 0-of-21,336 result, an invariant that had no explanation until
  the type supplied one
- `min <= max` had to fail: this is centre-and-extents, *not* a min/max pair. **The
  reading that the control killed was the reading the type was never going to support.**
- centre + extents lands in the chunk 32.94% of the time, which is what an AABB's far
  corner does -- it leaves the chunk whenever the object is large

**`VisibilityInfo` is ruled out, and it had to be ruled out** -- it is also 24 bytes, also
starts with a `Center`. The two differ in one place: its final component is
`Importance:Int32`, which read as a float would be a denormal.

| | share of 7,112 |
| --- | --- |
| f5 is a normal float | **7,112 / 7,112 = 100.00%** |
| f5 as Int32 in an Importance-like range | **0 / 7,112 = 0.00%** |

***`FBDynamicSceneModel` was also ruled out, by width.*** Its five fields match the
element's five exactly and its names are tempting -- `Guid, Trans, GridChain, PathHash,
VisInfo` -- but its slot 3 is `Int64`, eight bytes, where the data measures four. *A
five-field type with a plausible name is not a match; the widths are the match.*

#### The Bounds attribution has to be narrowed: the element is not a managed table

Checking the rest of the vocabulary walks part of the previous claim back, so it is
stated here rather than left standing.

**Exactly one of the 72 generated tables carries a `FBDynamicSceneBounds` field** --
`FBDynamicSceneSludgeComp`, which has **27** fields against the element's 5. And running
the widths against *every* generated table with 5 non-vector fields, **none matches**
`[16|20, 4, 24, 4, 4]`:

| table | widths |
| --- | --- |
| `FBDynamicSceneModel` | `[16, 36, 12, 8, 24]` |
| `FBDynamicSceneSeatComp` | `[4, 4, 12, 12, 4]` |
| `FBDynamicSceneRootComp`, `ActivityCondition`, `SettlementControlComp` | all `[4, 4, 4, 4, 4]` |
| `FBFactorySingleGridRangeData` | `[4, 4, 4, 4, 4]` |

So **the slot-7 element table is read by nothing in the managed assembly** -- the same
native boundary the IrradianceVolume lane hit. That is a real finding, and it is also the
reason the name has to be qualified.

***What survives and what does not.*** The *reading* stands on the bytes alone and is
unaffected: a centre that sits in its own chunk 73.96% against a 1.28% control, and a
second triple that is non-negative in 21,336 of 21,336 components. **What does not stand
is the stronger form -- that this field IS the declared `FBDynamicSceneBounds`.** The
engine declares a type with exactly this layout and that name, which is good evidence
that centre-and-extents is a real layout in this codebase; it is *not* evidence that this
particular field is that type, because no table that could contain it uses it. *The name
describes the layout; it does not locate a use site.* Anyone taking the earlier phrasing
literally would go looking for a managed reader that does not exist.

Note also that `FBDynamicSceneGuid` is **16 bytes** (V0..V3, UInt32) -- exactly slot 0's
width. It is still not a match: a GUID does not take **34 distinct values** across 11,016
records.

### WHY SLOTS 5 AND 6 STAY UNINDEXED: THE CORPUS HAS NO VARIATION TO INDEX

Not "not yet decoded" -- **decoded, and almost empty.** Establishing that is what stops
this being mined forever.

**The root layout is one shape, everywhere.** Offsets `(4, 8, 16, 20, 24, 28, 32, 36)`,
object size 40, in **7,433 of 7,433** files. A single layout, no variants.

**Slots 6 and 7 are genuinely parallel, and that was worth proving rather than assuming.**
`len(slot6) == len(slot7)` in **7,433 of 7,433** files with identical length
distributions -- which is exactly what reading *one* vector twice would also produce. It
is not that: resolving every root slot and comparing landing offsets, slots 6 and 7 never
coincide, and they **share zero element tables**. (Only slots 1&4 and 1&2 ever alias, in
10 and 1 files.) *Two vectors agreeing that precisely is a reason to check for aliasing,
not a finding.*

**Slot 6 carries no information at all.** Its elements have exactly one vtable layout,
`((4,), 8)` -- a single four-byte field -- in **11,016 of 11,016**, and that field holds
**4 in every element of every file**: one distinct value corpus-wide, across 349 distinct
chunk coordinates.

***A vacuous test, caught by running the control both ways.*** The natural reading of a
vector parallel to the placements is an offset table into slot 5, which predicts
non-decreasing values. That scored **100%** -- and so did **non-increasing**. Both
directions at 100% means the values never change, and the hypothesis was never under
test. **When a claim and its opposite both pass, the corpus is degenerate, not
confirming.** The slot-6 constant is why.

**Slot 5 is a real table vector -- checked, not assumed.** Its scalar fields hold values
like 36, 32 and 40, which are also the object sizes in its own vtable layouts, and that
coincidence is what reading a vtable *as* a table produces. The discriminator is that
FlatBuffers shares one vtable across same-shaped tables, so a genuine table vector has far
fewer vtable addresses than elements:

| slot | elements | distinct vtable addresses | per element |
| --- | --- | --- | --- |
| 5 | 185,063 | 18,480 | **0.100** |
| 6 | 11,016 | 3,979 | 0.361 |
| 7 | 11,016 | 5,207 | 0.473 |

All far below 1.0, with forward uoffsets at 100.0%. The reading holds.

**But slot 5's variation is almost nil**: across 185,063 element tables its scalar fields
carry only **5 to 29 distinct values** each, and its 16/20-byte field is **all zeros in
156,058 of 156,058 reads**.

***One more coincidence declined.*** Slot 5's wide field is 16 or 20 bytes -- the same
signature as slot 7's 34-value descriptor, which invites treating them as one vocabulary.
They **share 0 values**: slot 5's is a single all-zero constant. *Matching field widths
are not a shared type.*

### NO MANAGED CODE NAMES THESE FILES, AND THE TEMPTING MAPPING FAILS ITS OWN TEST

Chasing the reader through the filename ends in a clean negative:

| literal | global-metadata.dat | GameAssembly.dll |
| --- | --- | --- |
| `InitChunkData_` | **0** (ASCII and UTF-16) | **0** |
| `ChunkData_` | 0 | 0 |
| `_0_0.bytes` | 0 | 0 |
| `InitChunkData` | 2 -- *both* the method `_InitChunkDataPool` | 0 |

So **no managed string literal constructs these filenames.** The two hits are a
`MapManager` method that initialises a chunk-data *pool*, not a path. These files are
addressed some other way -- by catalogue id or hash -- which is consistent with the VFS
design and with the slot-7 element matching none of the 72 generated accessors.

***The mapping that looks obvious, and why it is refused.*** `MapManager+
LoaderChunkStaticData` holds **three** collections -- `grids`, `tiers`, `mists` -- against
the root's **three** vector slots, and `TierLoadConfigInfo` and `MistLoadConfigInfo` each
have **exactly 5 fields**, matching the slot-7 element's 5. Two independent-looking
coincidences pointing the same way.

It is still refused, on two counts:

1. **The widths disagree.** Both config types spend three of their five fields on vector
   members (`worldCenter`, `worldLeftBottom`, `worldRightTop`), where the data has one
   24-byte field and four small ones -- `[16|20, 4, 24, 4, 4]`. *A field-count match with
   a width mismatch is the same mistake `FBDynamicSceneModel` already cost.*
2. **The data argues against it directly.** `len(slot6) == len(slot7)` in **7,433 of
   7,433** files, with identical length distributions down to the 3,454 files where both
   are empty. Two *independent* collections -- tiers and mists -- would not have equal
   counts in every chunk in the world. Slots 6 and 7 read as **two parallel arrays over
   one list**, not as two separate concepts.

*The second point is the useful one: it is evidence from the corpus rather than an
absence of evidence from the binary, and it would still hold if a matching schema turned
up tomorrow.*

#### CONFIRMED LATER: the engine's own types say the same thing

The `<type-index:...>` placeholders that blocked this at the time are resolvable through
`MetadataRegistration.types` in `GameAssembly.dll`. Resolved, `LoaderChunkStaticData` reads:

```
loadConfig      Beyond.Gameplay.ChunkLoadConfigInfo     chunkId    string
compareId       uint                                    globalId   uint
levelId         string                                  levelNumId int
rectCenter / rectLeftBottom / rectRightTop  UnityEngine.Vector2
grids           List<...>
tiers           Dictionary<,>          mists      Dictionary<,>
```

***`tiers` and `mists` are dictionaries, not lists.*** The mapping was refused because
`len(slot6) == len(slot7)` in 7,433 of 7,433 files and two independent collections would not
match that exactly. The engine now says something stronger and quite separate: **two of the
three are not even the same container kind as the third**, so they could not serialize as
three parallel vectors whatever their lengths. *A refusal made on corpus evidence, upheld a
second time by type evidence that did not exist when it was made.*

Also worth keeping: the chunk rectangles are **`Vector2`** -- the loader addresses chunks in
two dimensions, matching `StreamingChunkInfo`'s two-int32 entries, while the *filenames*
carry a third coordinate that varies 0..7. And `LoaderLevelData` splits its chunks into
`lowChunks` / `mediumChunks` / `highChunks`, three `List<>` of chunk references, which is a
LOD tiering of chunks rather than of anything inside them.

### THE SIX CATEGORIES ARE UNORDERED: THE SIZE-CLASS READING IS REFUSED

The `w4 = 8 | 2^(k+4)` lock-step makes `k` look like an index into something *ordered* --
an LOD ladder or a size class -- which predicts that extents grow with `k`. Taking the
geometric mean of each record's three extents and the median per category:

| k | records | median extent | p25 | p75 |
| --- | --- | --- | --- | --- |
| 0 | 1,711 | 36.42 | 14.48 | 67.30 |
| 1 | 1,178 | 30.32 | 11.09 | 58.09 |
| 2 | 1,824 | **96.06** | 34.24 | 195.05 |
| 3 | 1,204 | 39.48 | 16.85 | 59.89 |
| 4 | 807 | 36.21 | 15.57 | 54.89 |
| 5 | 388 | 33.77 | 14.21 | 50.73 |

**Neither increasing nor decreasing.** Exact monotonicity across six bins would be a
1-in-720 accident, so this had real power to confirm; it declined. `k` is a **categorical
label, not a scale**, and the bit-shift relation between `byte1` and `w4` is an encoding
convenience rather than an ordering.

What the census does show: **k=2 is the distinctive class** -- the largest population and
extents roughly three times the rest -- and **k=0 is the only category carrying the
`0x0820` family** (393 of its 1,711). Both element object sizes, 56 and 60, occur in
every category in roughly equal share, so the two shapes cut across the categories rather
than encoding them.

**Still open, with the route now narrowed:** what a slot-7 element *is*. Its category is a
6-valued **unordered** one-hot code confirmed twice over and its 24-byte centre/extents
field is read, but no managed accessor, no filename literal and no loader type matches it.
A name has to come from the native reader.

# The root retyped, and the union vector it exposed

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** One mistyped slot propagated into several published
readings; correcting it re-typed the root, exposed a union vector, and closed the
name-to-id join at 100%. Check it before trusting any per-slot census in
[`world_chunk_slots.md`](world_chunk_slots.md) or
[`world_chunk_unread_region.md`](world_chunk_unread_region.md).

**Current correction:** slot-7 field 3 points to 8-byte descriptors, and
field 4 reaches a wrapper around a byte vector. The former 4-byte
"alternating code/zero" read below stopped halfway through each descriptor;
see [`world_chunk_unread_region.md`](world_chunk_unread_region.md).

## CORRECTION: slot 3 is a vector, not a size

Reading one large file from the top -- rather than from the unreached end -- exposes an
error in the root typing. In `InitChunkData_-1_0_0_0.bytes` (`blackbox02_dg001`), slot 3
holds **3,238,372**, and taken as a uoffset from `root+20` that lands at **3,238,420**,
where the first word is **59** -- exactly slot 5's element count.

Tested over 400 files:

| | |
| --- | --- |
| slot 3 resolves to a valid vector | **400 / 400 = 100.00%** |
| `len(slot 3) == len(slot 5)` | **400 / 400 = 100.00%** |
| slot 2 resolves to a vector | **0 / 400** |

***So slot 3 is a fourth vector, parallel to slot 5 in every file*** -- not one of the
"runtime allocation sizes" recorded earlier. **The formula `s3 == len - root - 28 - 4*n5`
still holds arithmetically, but it was describing where that vector sits, not what the field
is.** A vector pinned at a fixed distance from the end of the buffer makes its own offset
look like a size, and `s3`'s dependence on `n5` -- which read as suspicious coupling -- was
simply the vector's own length entering the address.

*Slot 2 is untouched by this: it resolves to nothing in any file, so the size reading stands
for it alone.* **The root now has four vectors (3, 5, 6, 7), two of them parallel, and one
scalar whose meaning is still open.**

**How the error survived:** `s3` was only ever tested as a number against other numbers. It
was never dereferenced. *An arithmetic identity that fits 26,519 files is strong evidence
about a value and no evidence at all about its type.*

## Slot 3 holds object ids, and the names carry the same id

Slot 3's elements are **not tables** -- 0 of 2,327 resolve as one. They are bare 32-bit
values: **975 distinct across 2,327 reads, none below 4096**, repeating across files
(`113214674` appears 70 times, `88420531` 42 times). *That is an id vocabulary, shared
between chunks.*

***And it is the same vocabulary the names use.*** The name strings end in a hex suffix --
`GrassGrid_0_0#0_A5F014`, `GrassGrid_0_-64#0_26E4C30` -- and parsing those tails as
hexadecimal:

| | |
| --- | --- |
| distinct slot-3 ids | 975 |
| distinct name-tail hex values | 77 |
| **intersection** | **40**, with **145 same-file pairs** |

**The ids span about 1.3 x 10^8**, so 975 of them occupy roughly 7 x 10^-6 of that space and
the expected intersection of 77 arbitrary values is **about 0.0005**. Observing **40** is not
a coincidence.

***So the hex suffix in a name is a slot-3 id.*** With slot 3 parallel to slot 5 in every
file, that gives the chain:

```
name string  ->  hex suffix  ==  slot-3 id  ->  (same index)  ->  slot-5 typed record
```

**Slot 5's entries are identifiable after all.** Its kind codes gave the *type*
(`StreamingLayer` x `ECSEntityType`); slot 3 gives the *identity*; and the name strings
attach a human-readable label to a subset of them -- 77 of 975 ids are named, so most
entries carry an id with no name in the file.

## THE ROOT RETYPED: slots 2, 3 and 4 are all vectors

Dereferencing the remaining scalars finishes the correction. Over 400 files:

| slot | resolves to | evidence |
| --- | --- | --- |
| **2** | a vector, **always empty** | target is exactly `len - 4` in **400/400**, count `0` in **400/400** |
| **3** | a vector of **ids** | 400/400, `len == len(slot 5)` in 400/400 |
| **4** | a vector, non-table elements | **400/400**, `len == len(slot 3) == len(slot 5)` in **400/400** |

***So every one of slots 2 through 7 is a vector, and the "runtime allocation sizes" reading
of 2, 3 and 4 was wrong for all three.*** The root is:

```
0  version 47          1  chunk origin (x*128, y*128), 8 bytes inline
2  empty vector        3 | 4 | 5   three PARALLEL vectors
                       6 | 7       two parallel vectors
```

**Slot 4's elements are packed bytes.** Its commonest values are `0x02020202` (324),
`0x01010101` (92), `0x03030303` (88), `0x03020202`, `0x00020203` -- *byte-replicated and
byte-packed words* -- mixed with small integers (1, 2, 3, 4, 16, 248, 356). Four small
values per word, one per parallel entry's worth of something.

**So a slot-5 record now has three columns beside it:** an **id** (slot 3), a **packed byte
quad** (slot 4), and its own typed fields. *That is a far richer row than the "kind code plus
five opaque fields" this section began with*, and all of it was hidden behind three fields
recorded as sizes because they were never dereferenced.

***And it changes nothing about the coverage gap.*** Marking those three vectors explicitly
moves coverage from **59.99% to 60.05%** over 400 files -- **17,062 bytes, 42 per file**.
They hold 59 entries at four bytes each; the gap is measured in megabytes.

*Two separate things were being conflated under "unexamined".* The root typing was **wrong**
and is now right, which matters for reading these files. The **byte volume** in the five
large files is a different problem entirely, and no amount of correcting the root touches it.
**A structural correction and a coverage gain are not the same currency**, and this one paid
entirely in the first.

## AND IT BREAKS THE SLOT-7 FIELD-3 READING TOO

Field 3 of a slot-7 element was recorded as *"a byte offset into the region `s4` sizes"*,
and `s4` has just turned out to be a **vector offset**, not a size. That interpretation is
void, so field 3 was dereferenced the same way -- **with controls this time**:

| field | recorded as | dereferences to a vector |
| --- | --- | --- |
| **3** | "byte offset into `s4`'s region" | **434 / 434 = 100.00%** |
| 1 | a count *(control)* | 9 / 434 = 2.07% |
| 4 | then treated as the constant 4 *(invalid control: it is a uoffset)* | **0 / 434 = 0.00%** |

**Field 3 is a uoffset**, and the controls show the test discriminates rather than accepting
anything. The vectors it reaches are short -- **length 2 in 392 of 434**, 15 in 32, 16 in 10
-- with non-table elements.

***So the records field 3 names are in the file after all.*** The earlier conclusion that
*"their content is not here to decode -- only their sizes and the offsets that will address
them once built"* is **withdrawn in full**. It rested on `s4` being an allocation size, which
it is not.

**That is the third claim in this family to fail the same way**: `s2`, `s3` and now field 3
were each verified as *arithmetic* against other numbers, across tens of thousands of files,
and each was a uoffset. *The formulas were real and the types were invented* -- and a
uoffset that lands at a predictable distance from the end of a buffer will satisfy an
arithmetic identity every time.

## Retracted: field 3 as an alternating code/zero list

Reading the elements: **952 words, and only 4 distinct values.**

| value | hex | as two u16 | count |
| --- | --- | --- | --- |
| `0` | -- | -- | 476 |
| `4194325` | `0x00400015` | (64, 21) | 392 |
| `262144` | `0x00040000` | (4, 0) | 42 |
| `262145` | `0x00040001` | (4, 1) | 42 |

**Exactly half the words are zero**, and the layout is strictly alternating -- `[4194325, 0]`
for the length-2 vectors, `[262144, 0, 262145, 0, ...]` for the length-15 ones. *So the
vector is a list of `(code, 0)` pairs*, and the codes come from a **three-value vocabulary**
across the whole sample.

Read as two 16-bit halves the codes are `(64, 21)`, `(4, 0)` and `(4, 1)` -- a high half of
64 or 4, a low half of 21, 0 or 1. **A three-code enumeration attached to a placement is a
flag or kind list, not payload**, which fits the vector being two entries long in 392 of 434
cases.

That historical reading did **not** complete the slot-7 element: it parsed
half-width words from an 8-byte descriptor vector and missed the field-4
wrapper. The current framing is in
[`world_chunk_unread_region.md`](world_chunk_unread_region.md).

## SWEEPING SLOT 5 FOR THE SAME ERROR -- two more uoffsets

Rather than wait for the next field to break, every width-4 field of a slot-5 element was
dereferenced at once:

| field | tested | vector-shaped | valid table |
| --- | --- | --- | --- |
| 0 | 2,327 | 95.57% | 18.99% |
| 1 *(kind code)* | 2,039 | **0.00%** | 2.40% |
| 2 *(kind code)* | 1,855 | 11.11% | 7.44% |
| **3** | 1,890 | 8.68% | **100.00%** |
| **4** | 437 | **100.00%** | 31.81% |
| 5 | 1,358 | **0.00%** | **0.00%** |

*Fields 1 and 5 scoring 0.00% are the control* -- the test rejects scalars rather than
accepting anything. **Field 3 is a uoffset to a table and field 4 a uoffset to a vector**,
both at 100%.

**The kind codes survive.** Fields 1 and 2 -- `StreamingLayer` and `ECSEntityType` -- are
scalars on this test, so that identification, which rests on five independent lines, is
untouched.

***And it re-explains the Init/Streaming comparison.*** That census found fields 1 and 2
**invariant** across a chunk's two files while 0, 3 and 5 **differed**, and read the
difference as "per-file quantities". **Fields 3 and 0 differ because they are offsets** --
two files with different layouts inevitably place the same object at different addresses.
*The invariant/varying split was partly types, not semantics*, and only field 5 (a genuine
scalar that differs in 100% of pairs) still needs a content explanation.

## The structure nests further than assumed

Following slot-5 field 3 to its table (1,890 of them): the vtable is
`(0, 0, 0, 12, 8, 4)` with objectSize **16** in 1,810 cases, `(0, 16, 0, 12, 8, 4)` with
objectSize 20 in 80. **Three live fields at *descending* offsets -- +12, +8, +4** -- in a
table whose whole body is 16 bytes: a soffset plus three words.

Their values give them away:

| field | offset | commonest value | resolves to |
| --- | --- | --- | --- |
| 5 | +4 | 12 (1,810), 16 (80) | `table + 16` / `table + 20` -- *immediately past the table* |
| 4 | +8 | 12, 20, 24 | `table + 20`, ... |
| 3 | +12 | 12, 24, 28 | `table + 24`, ... |

**Three more uoffsets**, pointing at objects laid out directly after their own table --
which is why the values are small and cluster on 12.

***So the depth is greater than this section has been assuming throughout.*** The chain now
runs root -> slot-5 vector -> element -> field-3 table -> three further objects, and each
level was reached only by dereferencing a field previously written down as a number.
**Every "distinct value" census in this family counted addresses as though they were data**,
which is why so many of them found large distinct-value counts with no structure in them.

## Re-checking the two censuses that finding casts doubt on

Applying the same dereference to the slot-3 "ids" and slot-4 "packed byte quads":

| | in-bounds as an offset | resolves to a table |
| --- | --- | --- |
| **slot 3** | **0.00%** | **0.00%** |
| slot 4 | 77.11% | **62.11%** |

***Slot 3 is vindicated.*** Its values are not offsets by any margin -- 0 of 3,325 -- so the
id reading survives, and with it the join to the name strings' hex suffix. **The test that
broke `s2`, `s3`, slot-7 field 3 and two slot-5 fields clears this one**, which is worth more
than never having doubted it.

***Slot 4 was read at the wrong width.*** At 62.11% resolving to a valid table against a
same-buffer random-position control of **3.13%**, the signal was real -- but 38% did not
resolve, and a vector of uoffsets is all or nothing. The `0x02020202`-style values that looked
like packed byte quads were the tell: **that is what a vector of *bytes* looks like read four
at a time.**

Read as a byte vector instead, over 400 files:

| test | result |
| --- | --- |
| byte-vector storage `4 + n` fits | **100.00%** |
| `count(slot4) == count(slot5)` | **100.00%** |
| `count(slot4) == count(slot3)` | **100.00%** |
| distinct byte values over 3,325 elements | **3** -- only `1`, `2`, `3` |

## Slots 4 and 5 are a union vector

A `ubyte` vector of three small values running exactly parallel to a vector of tables is the
FlatBuffers **union vector** signature: `field: [SomeUnion]` generates a `ubyte` type vector
plus an offset vector. That is falsifiable -- the tag must *determine the element's layout* --
so every slot-5 element was cross-tabulated against its tag over **1,200 files, Init and
Streaming, 12,417 elements**:

| tag | elements | vtable slot-count | distinct layouts |
| --- | --- | --- | --- |
| 1 | 2,368 | **5, always** | 2 |
| 2 | 7,653 | **6, always** | 6 |
| 3 | 2,396 | **4, always** | 4 |

***0 of 10 layouts appear under more than one tag.*** Slot-count is a function of the tag at
100% purity; the size variants inside a tag (obj 24/28, 40/44, 20/16) are ordinary
default-omission. **So root slots 3, 4 and 5 are one three-part structure: ids, union type
tags, union values** -- not three independent vectors, which is how they have been treated
throughout.

## What this invalidates

**The slot-5 field sweep and the field-3 table follow both pooled the three union members.**
"Field 3" is a different field in a 4-slot, a 5-slot and a 6-slot table, so those two tables
of percentages measured a mixture. It also explains their oddities -- the sweep's shrinking
sample sizes per field index were the tag-2-only fields, and *it is the likely explanation of
the "five lines" in the slot-5 kind codes*, which would be distinct union members rather than
five lines in one code space. **Both results are demoted to structural-only and must be re-read
per tag before anything is concluded from them.**

## The per-tag re-read

Done over **900 files, Init and Streaming**, each width-4 field tested as a uoffset against a
random-position control in the same buffer (`r` = resolves to a valid table, `c` = control):

| | field 0 | field 1 | field 2 | field 3 | field 4 | field 5 |
| --- | --- | --- | --- | --- | --- | --- |
| **tag 1** | 669 distinct, r 9.20% | **1 distinct** | -- | 8/12-byte inline struct | 11 distinct, r 14.62% | -- |
| **tag 2** | 1,445 distinct, r 10.74% | 2 distinct, r 0% | 5 distinct, r 0% | **r 100.00%**, c 3.35% | **16 bytes, 100% zero** | 12 distinct, r 0% |
| **tag 3** | 761 distinct, r 10.85% | 2 distinct, r 0% | 8 distinct, r 24.24% | **r 100.00%**, c 3.87% | -- | -- |

***The 100%-against-3.4% contrast is the useful part of this table.*** It shows what a real
uoffset looks like beside a scalar that coincidentally resolves, and retro-fits a calibration
this section never had: **field 0's ~10% is three times control and still not an offset.**
Cardinality agrees -- 669/1,445/761 distinct values is an id field, not a pointer.

Established per tag:

* **Field 0 of all three members is a high-cardinality id-like scalar**, not an offset.
* **Field 3 of tags 2 and 3 is a uoffset to a table at 100%.** This is the nested table
  followed earlier, so that result survives the demotion -- for those two members.
* **Field 1 is tiny-cardinality in every member** (1, 2, 2 distinct) and *tag 1's is constant
  across all 1,564 elements*.
* ***Tag 2 field 4 is sixteen bytes that are zero in 2,781 of 2,781 elements***, across both
  Init and Streaming. Read as 4 floats it is all-zero too. A struct field is written even when
  default, so this is most likely reserved or always-default space -- **it is not a transform,
  which is what a 16-byte inline struct in chunk data invites one to assume.**

***The "five lines" of slot-5 kind codes are confirmed as the pooling artefact predicted
above:*** per tag those fields have 2, 5 and 8 distinct values, and the earlier five-line
structure was three different members' fields overlaid in one space.

## Field 0 is the object's name, and the id join closes at 100%

***The per-tag table above understates field 0, and the "it is an id" reading in the previous
commit is wrong.*** That test asked only whether the target was a *table*; a uoffset can point
at a string or a vector just as well. Re-tested against every target kind:

| target | tag 1 | tag 2 | tag 3 | control |
| --- | --- | --- | --- | --- |
| **string** | **40.49%** | **40.59%** | **39.15%** | **0.19-0.31%** |
| table | 9.20% | 10.74% | 10.85% | 3.5-4.6% |

At 130x control this is not ambiguous, and the ~50% that resolved to nothing are **empty
strings**, whose zero length failed the `0 < count` guard in the checker. Decoded properly,
every field 0 is a NUL-terminated name and **100.00%** parse as `<base>#<N>_<HEX>`.

***These names give the three union members their identities:***

| tag | representative names |
| --- | --- |
| 1 | `Reflection Probes (5)#0_6BF84D2`, `rp_global#0_1C8A4C4`, `Env_rabbit hole (2)#0_73AB3B3` |
| 2 | `New Game Object#0_1255C60`, `MergedCollider_0_-1_0_0#0_51C0A5E` |
| 3 | `AudioBox_0#30_42A2041`, `AudioEmitter_4192702263#30_6F648D2`, `SurfaceTypeData_3_3#31_5EA5EA4` |

**The `#N` group is not decorative** -- it tracks field 1 exactly: `(tag 1, #0)` -> 8,
`(tag 2, #0/#31)` -> 5, `(tag 3, #30)` -> 9. *So the tiny-cardinality field 1 and the name's
group number are two encodings of the same thing*, which is the first independent check on
those kind codes this section has had.

### The id join

The hex suffix was compared to the parallel slot-3 id. Exact equality gave 72.24%, and the
misses were not random: the suffix differed from the id's low 28 bits **by exactly one bit**
each time (`D`->`5`, `B`->`3`, `A`->`2`). That is bit 27. The true rule, over **97,061 names
in 2,500 files**:

| rule | match |
| --- | --- |
| `suffix == id & 0x0FFFFFFF` | 98.613% |
| ***`suffix == id & 0x07FFFFFF`*** | ***100.000%*** |

***Exact, at full-corpus scale, with 0 names matching a different index.*** This establishes
what was previously only inferred from a chance argument: **slot 3 is an id vector running
index-parallel to slot 5, and the name carries that id masked to 27 bits.**

## Tag 1's field 3 is a StreamingComponentType mask -- the last union field, closed

Censused positionally rather than word-wise (**4,386 elements, 1,500 files**): byte +0 is
constant `0x01`, bytes +1..+4 are low-cardinality and bit-like, and **+5 onward are always
zero** -- including the whole 4-byte tail of the 12-wide variant, *so that tail is object
padding, not field content, and the field is 8 bytes.*

There are only **8 distinct combinations**, and **the name prefix determines the combination at
100%** -- every light type shares one, every reflection probe another. Read as a little-endian
u64 they decode against the `StreamingComponentType` enum recovered from IL2CPP:

| n | bytes | decodes to | names carrying it |
| --- | --- | --- | --- |
| 1,266 | `01 00 02 02 00` | `Transform \| Light \| HGAdditionalLightData` | Spot / Point / Linear Light, `lt_*` |
| 645 | `01 00 01 00 00` | `Transform \| ReflectionProbe` | Reflection Probe(s), `rp_global` |
| 217 | `01 40 00 00 00` | `Transform \| HGEnvironmentVolume` | `Env_*`, Global Env |
| 19 | `01 80 00 00 00` | `Transform \| Volume` | Global Volume |
| 19 | `01 00 02 22 00` | `Transform \| Light \| HGAdditionalLightData \| LensFlareComponentSRP` | Directional Light |
| 14 | `01 00 00 00 01` | `Transform \| HGWaterGlobalConfig` | Water |
| 5 | `01 00 08 00 00` | `Transform \| HGTerrain` | TerrainRoot |
| 1 | `01 00 00 00 02` | `Transform \| HGWindMotor` | Wind |

***8 of 8 masks decode with no unknown bits, and every decode matches its names.*** The enum
comes from the IL2CPP metadata and the names come from the file, so **these are two independent
sources agreeing eight times out of eight** -- this is not a name inference. The sharpest case
is `Directional Light`, which differs from the other lights by exactly one bit,
`LensFlareComponentSRP`: *a directional light that carries a lens flare, which is what a sun
is.* **Every field of all three union members is now characterised.**

This also ties the member back to known ground: **the slot-7 descriptor is a
`StreamingComponentType` mask too**, so the same component vocabulary appears at two levels of
this format.

## A cross-lane link the names open up, and why the raw route to it is closed

Tag 3's names embed numbers -- `AudioEmitter_4192702263`, `AudioScatterEmitter_771790068`.
Over 1,500 chunk files these yield **306 distinct ids in four kinds** (AudioEmitter 212,
AudioScatterEmitter 60, AudioBoxEmitter 30, AudioPrismEmitter 4), all inside u32 and ranging
15,460,646 .. 4,268,220,140. **That is the shape of Wwise short ids**, so if they appear among
the HIRC object or AKPK media ids, the chunk lane and the audio lane are joined by something
stronger than a name -- *and this section has wanted a cross-lane anchor for a long time.*

**The raw route is closed.** Every audio package begins with the magic `:)xD`, not `AKPK`, so
the containers are obfuscated and a byte scan finds no `HIRC`/`BKHD` at all -- 0 sections
across `Audio` and `InitAudio`. *A scan reporting zero here means the scanner never reached the
banks, not that the ids are absent*, and the intersection measured that way (0 of 306, with a
control also at 0) **carries no information and is recorded only so it is not re-run.**

The maintained audio pipeline already enumerates AKPK media ids through `AnimeStudio.CLI`,
which handles the container, and **its decoded intermediate is already on disk** --
`tmp/audio/hirc_action_current/audio_audit.json`, 325 MB of `akpk-structure-audit-v1`. So the
join could be run after all, without re-running the pipeline or touching its sources.

### The join runs, and it is a clean negative

Scanning the whole audit for each id as a decimal and as a hex token:

| set | found |
| --- | --- |
| 3 source ids known from the named-reach report *(positive control)* | **3 / 3** |
| the 306 emitter ids | **0 / 306** |
| 306 random ids drawn from the same range *(negative control)* | **0 / 306** |

***The positive control is what makes this worth recording.*** The first attempt at this join
scanned the raw packages, found nothing, and the zero meant only that the scanner never reached
the banks. Here a known-present id is found 3 times out of 3, in sorted id lists, **so the scan
demonstrably works and the absence of the emitter ids is a real result rather than a broken
tool.**

**The emitter numbers are not any id the AKPK/HIRC audit records** -- not source ids, not media
ids. They are therefore *not Wwise identifiers into the shipped banks*, and the obvious
hypothesis is closed. Supporting evidence from the chunk side agrees: the number **is not the
element's own id** (0.00% against both the id and its 27-bit mask), spans the full u32 range,
and **22 of 306 recur across level directories, one in six levels** -- an authored identifier
that is shared between places, rather than a per-instance Unity id.

*What they do identify is still open, but the search space is now smaller by the most obvious
candidate.*

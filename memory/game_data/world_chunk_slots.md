# What the chunk slots mean

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** From framing to meaning: slot 5's kind codes and slot 7's
descriptor, each identified against a named engine enum rather than a magnitude
distribution. The refused candidates are kept beside the accepted ones, because
the refusals are what make the accepted reading load-bearing.

## SLOT 5's KIND CODES, IDENTIFIED: `StreamingLayer` AND `ECSEntityType`

Four independent lines agree, and each could have failed.

***1. Range exclusivity.*** Over **1,602,882** elements, `f2` takes `{0..10, 12, 13}`:

| candidate enum | verdict for `f2` |
| --- | --- |
| `StreamingLayer` (11) | **out of range** -- 12, 13 |
| `ProxyEntityType` (11) | **out of range** -- 12, 13 |
| **`ECSEntityType` (14)** | **in range, 13 of 14 values used (93%)** |
| `StreamingComponentType` (44) | in range but only 30% used |

*Two candidates are excluded outright by two values.* `StreamingComponentType` survives
the range test and fails the coverage one: 30 of its 44 members never appearing across 1.6
million elements is not what a live discriminator looks like. `ECSEntityType` uses every
value but index 11 (`TerrainSplineDecal`), and its maximum is exactly `TypeCount - 1`.

`f1` takes `0..10` -- exactly 100% of `StreamingLayer`'s eleven, and of
`ProxyEntityType`'s eleven.

***2. A cross-block join that had to be earned.*** The `terrain` block gives terrain
presence per level independently. Scoring every `(f1, f2)` pair over 38 terrain levels and
50 without:

| pair | terrain | non-terrain | separation |
| --- | --- | --- | --- |
| **`(5, 7)`** | **37/38** | **0/50** | **+97.37%** |
| `(0, 4)` | 38/38 | 0/50 | +100.00% |
| everything else | -- | -- | +52% or below, most near 0 |

Under the reading, `(5, 7)` is **`StreamingLayer.Collider` + `ECSEntityType.TerrainCollider`**
-- a terrain collider on the collider layer, present in essentially every terrain level and
**no** level without terrain. *The name and the statistic were derived from different
files and agree.*

***3. An earlier negative becomes positive evidence.*** `ProxyEntityType` is the rival for
`f1`, and it was already refused: if `f1` were `ProxyEntityType`, then `f1 == 0` would be
`IrradianceVolume` and its per-level count had to equal the `iv` block's -- it matched on
**0 of 88 levels**, with a positive control confirming the test could fire. Under
`StreamingLayer`, `f1 == 0` is `Default`, which makes no such prediction. **The failed test
does not merely leave the question open; it discriminates between the two survivors.**

***4. Absence behaves like a default.*** `f2` is *absent* on 405,611 elements, and
FlatBuffers omits any field equal to its default. `ECSEntityType.Render` is 0 -- the
commonest thing in a chunk -- so the commonest record carries no type word at all.

***5. The enum values are now verified, not assumed.*** The mapping above originally read
member values off **declaration order**, which is a guess. IL2CPP stores the real values in
`fieldDefaultValues` (127,853 records) indexing `fieldAndParameterDefaultValueData`, and
decoding them confirms it:

| enum | values | terminator | valid range |
| --- | --- | --- | --- |
| `StreamingLayer` | **sequential 0..11** | `Count` = 11 | **0..10** |
| `ECSEntityType` | **sequential 0..14** | `TypeCount` = 14 | **0..13** |
| `ProxyEntityType` | sequential 0..11 | `TypeCount` = 11 | 0..10 |
| `StreamingComponentType` | **NOT sequential** -- max value **128** | `Count` = 43 | -- |

`ECSEntityType`'s valid range ends at exactly **13**, which is exactly `f2`'s observed
maximum.

***A caveat on the method, found by pushing it further.*** The read above takes **one byte**
per entry from `fieldAndParameterDefaultValueData`. For these three enums the result is
self-consistent -- strictly sequential `0..N-1` with the terminator landing exactly on the
member count -- which a misaligned read would not produce. **But the method is not generally
sound**: applied to flag enums it returns incoherent sequences, e.g.
`HGFactoryDirtyFlags` as `1, 2, 4, 16, 32, 1`, which is not a power-of-two ladder and
cannot be right. Entries wider than a byte are not read correctly.

**So the `StreamingComponentType` exclusion should lean on coverage, not on its values.**
That enum read as "non-sequential, max 128", and that reading is exactly the kind the
caveat above calls unreliable. *The exclusion still holds* -- `f2` uses 13 of 14
`ECSEntityType` values against 30% of `StreamingComponentType`'s 44, and its values are
contiguous `0..13` -- **but the structural argument from a 128 is withdrawn.**

**A read that failed usefully.** The values are stored as **single bytes**, and reading
them as int32 produced `0x03020100`, `0x04030201`, `0x05040302` -- consecutive overlapping
windows. *That the garbage was orderly is what identified the stride:* entries one byte
apart, values 0, 1, 2, 3. A wrong read that returns noise tells you nothing; a wrong read
that returns a pattern tells you the layout.

***6. The caveat is resolved, and the mapping is confirmed far harder than before.*** The
worry was `(0, 4)`, which separates terrain levels at 100% while reading as
`Default + SphereCollider`. Presence separation is a weak instrument -- it asks only
*whether* a pair occurs. Correlating **counts** against each level's terrain-file count,
over the 38 terrain levels, separates them completely:

| pair | reading | total | corr. with terrain files |
| --- | --- | --- | --- |
| **`(5, 7)`** | **Collider + TerrainCollider** | 5,406 | **+1.000** |
| `(0, 7)` | Default + TerrainCollider | 4,590 | +0.956 |
| `(0, 4)` | Default + SphereCollider | 5,312 | **+0.728** |
| `(3, 9)` | -- | 103,748 | +0.118 |
| `(1, 9)` | -- | 123,540 | -0.030 |

**`(5, 7)` is perfectly linear in terrain extent across all 38 levels.** A count of
"terrain colliders on the collider layer" rising exactly in step with the number of terrain
files is what the two enum names jointly predict, and nothing else in the census behaves
that way. *This is the confirmation the presence test could not give.*

**And `(0, 4)` behaves unlike a terrain record.** At +0.728 it is plainly correlated -- but
the two records that genuinely name terrain sit at +1.000 and +0.956, and the difference is
not marginal. `(0, 4)` is common on outdoor levels without scaling with terrain, which is
exactly what "sphere colliders are more numerous outdoors" predicts and what
"sphere colliders *are* a terrain feature" does not. *The pair that fit the statistic
without fitting the name turns out to fit a weaker statistic, which is the name's
prediction after all.*

## SLOT 7's DESCRIPTOR: THREE CANDIDATES REFUSED, AND MY OWN "6-VALUED" CORRECTED

The method that worked on slot 5 does not transfer, and saying so precisely is the result.

***The category is 7-valued, not 6.*** Corpus-wide the one-hot invariant **strengthens** --
byte 1 is a single set bit in **12,859 of 12,859** non-zero descriptors, no exceptions --
but `k` runs **0..6**, with `k = 6` present on 2 descriptors (0.016%). **The earlier
"6-valued" figure was an artefact of the single-digit coordinate slice.** Two descriptors
out of 12,859 is thin, and it is enough: a range claim is settled by its rarest member.

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| descriptors | 2,956 | 1,980 | **3,305** | 2,250 | 1,536 | 830 | **2** |

***Refused 1 -- a mask over `ECSEntityType`.*** The word is 14 bits wide and
`ECSEntityType` has exactly 14 values, which is the same coincidence that identified slot
5's `f2`. Testing it *within* each file, against the types that chunk's slot 5 actually
contains:

| | share of 18,391 descriptors |
| --- | --- |
| mask is a subset of the chunk's types | 41.42% |
| **control: the mask shifted right** | **45.37%** |
| control: the mask shifted left | 37.37% |
| control: subset of a *different* chunk's types | 40.53% |

**A control beat the claim.** The same reasoning that succeeded one slot over fails here,
and it fails against three controls at once.

***Refused 2 -- `ECSExplicitEntityType` and `StreamingMode`.*** Both have exactly 6
members, which is why the corrected range matters: `k` reaches **6**, so seven values, and
both are excluded outright.

***Refused 3 -- a cross-slot join on the one name both enums share.***
`HGDecalProjector` appears as `ECSExplicitEntityType` position 5 *and* `ECSEntityType`
value 10, so `k = 5` records should co-occur with slot-5 `f2 = 10`. They do, at 65.88% --
and `k = 4` does at 61.27%, `k = 1` at 59.49%, `k = 2` at 27.43%. *Highest is not
isolated*, and a spread of 27-66% across the categories discriminates nothing.

**What the descriptor is made of, precisely.** The low byte takes only four values --
`0xFF` (12,638), `0x00` (5,459), `0xBF` (283), `0x3F` (11) -- so only bits 6 and 7 vary
there, while bits 8..14 carry the one-hot category. *The structure is fully framed and the
referent is unidentified*, which is a different and more useful state than either half
alone.

### Three further constraints, each narrowing what the category can be

***It is not an enum in this vocabulary.*** Searching every enum in the HyperGryph,
Streaming and Beyond namespaces whose values are verified sequential from
`fieldDefaultValues`, exactly **one** has seven members -- `AudioDebugGizmosType`, a debug
gizmo list. There is no seven-valued streaming enum for `k` to be.

***It is orthogonal to level content.*** The terrain anchor that identified slot 5's `f2`
gives **nothing** here: every category appears in nearly every level, terrain or not.

| k | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| terrain-vs-not separation | +0.00% | -0.63% | -0.63% | -0.63% | -5.79% | +9.26% | +5.26% |

**A category present in all 88 levels in similar proportion is a per-object attribute, not
a content kind** -- which rules out the whole family of readings that name *what* is
placed, and is why `ProxyEntityType`-style guesses were never going to land.

***The ordering refusal holds on the full corpus.*** Re-run with the corrected seven-value
range (the earlier run used the slice that misreported it as six), the median geometric
extent per category is **38.98, 28.45, 97.74, 40.89, 38.05, 33.77, 31.51** -- neither
increasing nor decreasing. *Re-testing was justified because the input had been shown
unrepresentative, not because the answer was unwelcome.*

## SOLVED: THE DESCRIPTOR IS A `StreamingComponentType` MASK

The blocker was a **broken tool, not missing evidence**. `StreamingComponentType` had been
excluded partly because it read as "non-sequential, max 128" -- a misread from taking one
byte per enum value. Read at its declared width it is `ulong` and a **one-hot bitmask**:
`Transform` = 1, `MeshFilter` = 2, `MeshRenderer` = 4, ... `HGGPUParticleSystem` = 2^42.

Testing slot 7's first `u16` as a mask over it, across **12,932** non-empty descriptors:

| check | result |
| --- | --- |
| every set bit is <= 14 | **12,932 / 12,932 = 100.00%** |
| any bit 15 or above | **0** |
| bits 0-5 all set (`Transform`..`MeshCollider`) | **12,932 / 12,932 = 100.00%** |
| bits 8-15 one-hot | 12,859 / 12,932 = 99.44% |

**And the one-hot bit names the category outright:**

| k | bit | component | count |
| --- | --- | --- | --- |
| 0 | 8 | `TerrainCollider` | 2,956 |
| 1 | 9 | `MultiCollider` | 1,980 |
| 2 | 10 | **`HGDecalProjector`** | 3,305 |
| 3 | 11 | `HLODGroup` | 2,250 |
| 4 | 12 | `HGVolumetricLocalFog` | 1,536 |
| 5 | 13 | `HGWaterRenderer` | 830 |
| 6 | 14 | `HGEnvironmentVolume` | 2 |

*Those are exactly the k-counts measured earlier, from a census that knew nothing of this
enum.* The two varying low bits are **`SphereCollider`** (bit 6) and **`CapsuleCollider`**
(bit 7): both present 12,638 times, capsule only 283, neither 11.

***Every earlier observation now has a reason.*** `k = 2` was the outlier with the largest
population and a median extent **2.5x** the rest -- it is `HGDecalProjector`, and a decal
projector's bounds are large. The category looked "orthogonal to level content" because
every level has decals, HLOD groups, fog and water. The range was seven because exactly
seven component bits occur. `0xBF` appeared only with `k = 0` because a terrain-collider
placement is the one that carries no sphere collider. And the `ECSEntityType` mask test
failed against its controls because **it was the wrong enum, not the wrong idea**.

**The lesson is about the tool.** This sat unsolved across several batches behind a
one-byte read that silently produced a plausible-looking wrong answer. *A misread that
returns garbage gets caught; a misread that returns a small tidy number gets believed* --
and "max 128, non-sequential" was tidy enough to found an argument on.

### The element's other fields: one characterised, one degenerate test caught

With the mask reading proven for field 0, the obvious move is to try it on field 1, whose
commonest values are 1, 2 and 4. **It is not a mask.**

| | |
| --- | --- |
| every bit <= 10, i.e. "fits `StreamingLayer`" | 99.61% |
| **values below 2048** | **99.61%** |

*The two are the same test.* The bound a `StreamingLayer` mask would satisfy is satisfied
for free by any small integer, and the tell was the bit frequencies: 10,150 / 8,381 /
6,899 / 5,223 / 4,151 / 2,963 / ... a smooth geometric decay, which is what small integers
give and a mask over distinct concepts does not.

**Field 1 is a count.** Its values are dense over the small integers with no gaps --
`1`:3,455, `2`:1,905, `3`:1,154, `4`:1,113, `5`:734, `6`:574, `7`:463, `8`:405 -- **never
zero**, with 60.9% of reads landing on non-powers-of-two. 964 distinct values, a long tail
past 2048 in 0.39%.

**Field 4 is the constant 4** in all 18,391 reads.

### Field 3 is a byte offset into the slot-4 region

Its values are multiples of four -- 100, 180, 528, 340 -- which is a hint worth following
rather than a coincidence:

| check | result |
| --- | --- |
| divisible by 4 | **18,391 / 18,391 = 100.00%** |
| `max(f3) < s4` | **6,002 / 6,002 = 100.00%** |
| `max(f3) + 24 <= s4` | **6,002 / 6,002 = 100.00%** |
| distinct within a file | 5,970 / 6,002 = 99.47% |

**`s4` is the size of the region field 3 indexes into.** That closes a loop: `s4` was
established earlier as *"a byte size over variable-length records, not a count times a
stride"* -- with no idea what the records were. Field 3 points at them, and the gaps
between consecutive sorted offsets take **5,163 distinct values**, which is exactly the
variable-length structure `s4`'s growth implied. *Two findings made separately, each
half of one mechanism.*

**Two details that constrain the region.** The lowest offset in a file is never 24 and
varies widely (100, 180, 340, 528...), so the records start after a header of variable
size; and `s4 - max(f3)` is 136-448 bytes, so the last record is followed by a tail rather
than ending the region exactly.

***The offsets are not in element order.*** Only **74.36%** of files have field 3
non-decreasing across the slot-7 vector, so a quarter of chunks reference their records in
a different order from the order those records are stored. **Anyone walking the region by
following elements in order will read it out of sequence in one file in four** -- which is
the kind of thing that makes a parser look almost right.

### The region is not in the file, which unifies all three scalars

Trying to *find* the records, the two natural bases both fail. At `len - s4` the bytes at
`base + f3` are inconsistent across files -- small integers in one, a fragment of a name
string (`_4_0_0#0_31D97B9`) in another, zeros in a third. At `root + 40`, likewise nothing
that repeats. **There is no base in this file at which field 3's offsets land on a
consistent record.**

*That negative is the answer rather than a dead end.* `s2` and `s3` were already shown to
be **sizes of something outside the file** -- every test against the buffer's own offsets
scored 0.00%. Field 3 is bounded by `s4` and 4-byte aligned, `s4` grows with the
placements, and the gaps between offsets are variable -- **so `s4` sizes a runtime
allocation and field 3 is an offset within it**, exactly as `s2` and `s3` size runtime
structures.

**All three scalars describe the image the loader builds, not the file it reads.** That is
why `s2 == len - root - 20` held for `InitChunkData` and scored **0.00%** for
`StreamingChunkData`: in the Init case the payload happens to map one-to-one onto the
allocation, and in the Streaming case it does not. *A relation that holds in one family and
fails in its twin was never a fact about the byte layout.*

# The transform-matrix bulk, and corpus coverage

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** What fills the unreached majority of the file: an array of
transform matrices, how blocks and runs are organised around them, and the measured
coverage figure for the corpus.

## The unreached bulk of InitChunkData is an array of transform matrices

The coverage gap was last recorded as "~44% unreached, concentrated in five multi-megabyte
files", with the largest run 444,381 bytes in `blackbox02_dg001/InitChunkData_-1_0_0_0.bytes`.
***The run was being read at the wrong alignment.*** It begins at 2,601,975, which is not
4-aligned, so word reads were shifted by three bytes -- which is exactly why the earlier census
found top values `0x0000003f` / `0x000000bf` / `0x000000be`. **Those are float exponent bytes
sitting one byte off**, and it is the same three-byte shift the earlier note recorded as
"exponent bytes concentrate at `mod 4 == 3`" without following it up.

Realigned absolutely, the window is `0.0`, `1.0` (4,707x), `61.71` (2,966x), `0.049`, `0.286`
-- and consecutive `1.0` values are **24 words apart**. Laying the floats out on that stride:

```
-0.5947   0.0000   0.2789   0.0000
 0.0000   0.6569   0.0000   0.0000
-0.2789   0.0000  -0.5947   0.0000
-166.69  61.7100  37.6612   1.0000
```

***A row-major 4x4 affine transform.*** A rotation about Y at uniform scale 0.6569
(`|row0| = sqrt(0.5947^2 + 0.2789^2) = 0.6569`, matching row 1), translation in the last row,
fourth column `(0,0,0,1)`.

Tested as a hypothesis rather than read off one sample -- fourth column zero, rows mutually
orthogonal to 1e-3, scale uniform to 1e-3 -- **scanning every 4-aligned offset** of that file:

| | |
| --- | --- |
| matrices found | **19,990** |
| gap between consecutive matrices == 96 bytes | **18,451 / 19,989 = 92%** |
| random 16-float windows passing the same test *(control)* | **1.88%** |
| unreached bytes inside a 64-byte matrix | 41.84% |
| ***unreached bytes inside the 96-byte record*** | ***62.76%*** |

**The record is `[64-byte matrix][16 zero bytes][16 bytes of floats]`** -- words +16..+19 are
zero in **19,989 of 19,990**, the same always-zero 16-byte block seen in the union's tag-2
field 4, which suggests one reserved field reused at both levels.

***This also settles the `61.71` mystery.*** It was recorded as an unexplained value repeating
2,966 times and localised to a 2x2 chunk block whose chunks have no populated placements.
**It is the Y component of the translation row** -- the ground height where those objects stand.
*It was never a strange constant; it was a coordinate being read as an opaque number.*

**Scope:** measured on the worst file. A second large file (`InitChunkData_Global_0_0.bytes`,
1,846 matrices) gives 19.2%, so the share varies and *this is not yet a corpus figure.*

### Trying to make it a corpus figure -- partly done, and the diagnosis was wrong

The walk was rewritten with O(1) marking (spans resolved once by a numpy
difference array instead of a bytearray slice per call) and a cached `vtable_of`. It is
**byte-identical to `Walker3` on 120 of 120 files**, and it makes the 3.2 MB worst file walkable
in **15 s**, which `Walker3` could not do at all. *That part worked.* The `scratch/` prototype
that did it is deleted; the technique is the durable part.

***The corpus figure still does not exist, and the reason is not what was written above.***
A run over all `InitChunkData` files managed only **45 files in 554 s**, which is ~12 s each for
~59 KB files -- absurd. Profiling then showed **the walk is not the bottleneck**: 0.00 s per
file on typical inputs, and 6 files stream and decode in 0.4 s. *So "the pure-Python walker is
too slow" was the wrong diagnosis.* **A few specific files stall it**, and the rest are instant.

A node budget was added to `table()` so a stalling file fails closed as `unbounded` rather than
silently returning a truncated coverage number. **It did not stop the stall**, which localises
the problem usefully: *it is not in table recursion.* The remaining suspects are the O(count)
element list `follow()` rebuilds for every candidate vector (count up to 65,536), and the
Python loop over spans in `coverage()`.

What can be quoted, from **45 completed walks totalling 2.67 MB**:

| | |
| --- | --- |
| unreached by the structural walk | 46.75% |
| of that, inside a 96-byte TRS record | 19.36% |
| combined accounted for | **62.30%** |

### The stall, found

Printing each filename before walking it named the culprits directly: a **134 KB** file took
**38.6 s** at only 880 tables, a **323 KB** file took **70.2 s** at 679. *Time was unrelated to
table count and tracked `offsetVectors`.* The cause was in `follow()`: it built a Python list of
every element -- **up to 65,536 ints** -- for **every candidate vector**, before testing whether
the vector was acceptable. Replacing that test with a vectorised numpy read:

| file | before | after |
| --- | --- | --- |
| `InitChunkData_Global_1_0.bytes` (323 KB) | 70.2 s | **16.6 s** |
| `InitChunkData_-1_0_1_0.bytes` (134 KB) | 38.6 s | **12.0 s** |
| `InitChunkData_-1_0_0_0.bytes` (3.2 MB) | 15.0 s | **10.0 s** |

Still **byte-identical to `Walker3` on 150 of 150 files**, and every coverage value unchanged.

***One further optimisation was tried and was wrong.*** `as_string` tests printability with
`all(32 <= c < 127 for c in s)`; pushing that into C as `min(s) >= 32 and max(s) < 127` made it
**slower** -- the 3.2 MB file went 10.0 s -> 14.2 s. `min`/`max` each traverse the whole slice
while `all` short-circuits on the first non-printable byte, *and nearly every candidate fails on
byte one.* **Reverted, with the measurement recorded in the code so it is not retried.**

With the faster walk, **92 files / 5.51 MB** in one bounded run: 24.14% unreached, 19.23% of
that inside a 96-byte TRS record, **80.50% combined accounted for**.

***That is still a sample.*** 92 of 26,520 files is not a corpus figure and must not be quoted
as one.

### Benchmarking on this machine needs a quiet machine

A full-corpus background run reached 200 files in 1,088 s -- ~5.4 s/file, which extrapolates to
**about 40 hours**. To cut that, a numpy pre-filter was added to skip vector elements that could
be neither a string nor a table. Measured against the existing code it looked **3-4x slower**.

***That measurement was invalid, and the reason is worth keeping.*** The corpus run was still
going in the background, competing for CPU, while the "before" baselines had been taken on an
idle machine. **Re-measured with the background job stopped, the same three files varied by up
to 4x run to run with no code change at all** -- 16.6 s and 63.0 s for the same walk of the same
buffer. The pre-filter won on one file and lost on two, entirely inside that noise.

**It was reverted.** *An optimisation that cannot be shown to help is just more code*, and the
measurement is recorded in the source so it is not tried again. The earlier `min`/`max`
`as_string` result should be read with the same caution -- though that one at least was taken
against an idle machine.

### Fail-closed on the stragglers instead

Since a minority of files stall the walk while most are instant, `walk()` now takes a wall-clock
`seconds` budget alongside the node budget: a file that exceeds it is marked **`unbounded`** and
**excluded from the percentages**, with its count and bytes reported, rather than contributing a
truncated coverage. Still **byte-identical to `Walker3` on 150 of 150 files.**
The full-set runner used a 3 s/file budget and wrote `corpus_coverage.json` with
`total / success / unbounded / unboundedBytes / decodeFailed`, so the denominator and the
excluded share were both visible. That `scratch/` runner is deleted; a repeat run needs it
rebuilt, or promoted into `scripts/game_data/` as a corpus gate if the figure is wanted
again.

### The actual bottleneck, found by profiling instead of guessing

***Three successive diagnoses of this walk's cost were wrong*** -- "the pure-Python walker is too
slow over multi-megabyte files", then the O(count) element list in `follow()`, then a wall-clock
budget. A profile of one 134 KB file ends the argument:

```
268,365 calls   13.694s   method 'index' of 'list' objects
```

**`live.index(off)` in `table()` was 96% of the entire walk.** It rescans the sorted slot list
for every slot of every table, making the function quadratic in slot count. *Nothing to do with
vectors, element counts, or file size* -- which is exactly why every fix aimed at those missed.
Replacing it with a precomputed offset-to-position map (reproducing `index()` exactly, including
which position a duplicated offset maps to):

| file | before | after |
| --- | --- | --- |
| `InitChunkData_Global_1_0.bytes` (323 KB) | ~67 s | **0.31 s** |
| `InitChunkData_-1_0_1_0.bytes` (134 KB) | 13.4 s | **0.25 s** |
| `InitChunkData_-1_0_0_0.bytes` (3.2 MB) | 13.4 s | **0.31 s** |

**40-200x, still byte-identical to `Walker3` on 150 of 150 files**, every coverage value
unchanged.

***The profile also exposed why the budget never fired.*** It reported `work = 6,799` elements
on a file that took 13 seconds -- proof the time could not be in the element loops -- and the
deadline was checked every 8,192 elements, so on that file it was never checked at all. The
counter now advances where the work happens, though with the real bottleneck gone it should
rarely be needed.

***The lesson, which cost two turns:*** on this walk, *measure before optimising.* Every
guess-driven change was aimed at the wrong function, and the one that mattered took a single
profile to find.

## The corpus coverage figure

The full `InitChunkData` set now walks in **32 minutes** -- it had been extrapolating to 36
hours -- and completes with **0 unbounded files**: 26,519 of 26,520 walked, 1 decode failure,
2.91 GB decoded.

***The durable conclusion: the structural walk reaches barely half of this format, and the
largest single thing it does not reach is an array of transform matrices.*** Just under half
the bytes are unreached from the root, a little over a quarter of those sit inside the 96-byte
TRS record, and **over 6.7 million transform matrices** are present corpus-wide against a
control that passes at 1.88%. *The transform-array reading is not a property of one file; it is
the dominant content of the format.*

**A first pass of this must not be quoted.** It used a 3 s per-file budget and excluded 58 files
totalling 571 MB as `unbounded` -- ~20% of all bytes, and precisely the large files holding most
unreached content. **The exclusion was not neutral: it flattered the result by ~2.8 points.**
*A coverage percentage measured with the hard files dropped is worth less than no percentage.*

Counts, per-run totals and the acceptance test live in
`reports/chunk_data/init_chunk_coverage_latest.{json,md}`, per the rule that changing counts and
full inventories belong in reports rather than memory prose.

### What the unreached bytes actually hold

*"Unaccounted" is the absence of a finding, not a finding*, so every unreached byte was
attributed to exactly one named bucket, over the full corpus (26,519 files, 0 unbounded).
**The largest part is zero bytes -- 45.75% of everything the walk does not reach.** Zeros are
padding and default space, not undiscovered structure.

***The honest size of the gap is therefore 11.65% of the format, not the 34.4% the headline
coverage figure implies.*** Quoting "a third unaccounted" overstates it by roughly three times.
*The single most useful thing done to this number was refusing to leave it as one word.*

***The rest is not alien data; it is the same scene population, stored a second time.***
Searching the unreached region for the `<name>#<N>_<HEX>` form established for union field 0
finds it densely -- **39.1% of all such name occurrences lie in bytes the walk never reaches** --
and the vocabulary is the union's own, dominated by prefab instances (`P_prop_*`, `P_tree_*`,
`P_bush_*`, overwhelmingly `_ECSMerged`) then `MergedCollider`, `GrassGrid`, `AudioEmitter`,
`SOCChunk`, `SurfaceTypeData`, `Reflection Probe`, `Global Volume`.

***That first looked like additional objects the walk fails to traverse. It is not.***
**99.61% of the names found in unreached bytes are names the union already reaches**, and
counting occurrences shows why: **1,303 of 1,311 distinct names appear exactly twice** (mean
1.99 copies), **72.6% with one reached copy and one unreached copy**, and only one name with no
reached copy at all. *The same string is stored at two offsets* -- for example
`P_prop_map01_vatzmdlife+1_008_s03_ECSMerged#0_637998D` at 3,560 (unreached) and 1,054,728
(reached).

***So the unreached region does not extend the scene population; it duplicates its name set.***
Taken with the transform arrays, **`InitChunkData` embeds a second serialized payload that is
not reachable from the FlatBuffers root** and that carries the same objects' names alongside
their transforms. **The scene contents are therefore already enumerated by the union** -- the
gap is a second encoding of them, not unseen objects.

### How the second payload is organised

*It is not one opaque blob.* The root carries **two parallel vector groups**, not one: slots
3/4/5 at the union's element count, and **slots 6/7 at a second, much smaller count** (1, 9, 15,
20 ...). Following slot 7's elements as uoffsets lands them **immediately after each large
unreached block** -- block 38,288..82,404 ends exactly at slot-7 target 82,404, and so on down
the file. ***So the payload is a sequence of descriptor-delimited blocks, and the descriptors
are reachable even though the blocks are not.***

Each descriptor is a 56/60-byte table holding, in order: an **8-byte `StreamingComponentType`
mask** (which is the previously recorded slot-7 descriptor, now located), a **count**, **two
floats**, a large size-like word, and a constant `4`.

**The count nearly partitions the union.** Summed over a file's descriptors it equals the union
element count exactly in 15% of 400 files and falls short by just **1 to 7** in most of the rest
-- *a near-partition, so the descriptors group the scene's objects into streaming blocks.* The
residual is small and consistently positive; a plausible reading is the handful of global
objects (`Directional Light`, `Global Volume`, `Water`, `Wind`) that belong to no block, **but
that has not been tested and is not claimed.**

***The size-like word is not the block length*** -- summed against unreached bytes the ratio
ranges from **0.001 to 1.27**, and single-descriptor files pair a 2 KB sum with a 100 KB payload.

***It is the block's per-object payload size.*** It correlates **+0.943 with the descriptor's
count** and near zero with names, matrices or block length, and it is divisible by 4 in 100% of
cases. Fitting `size = a x count + b` **within each component mask**, over 29 masks in 120
files, gives **integer `a` and a constant `b` of about 20-22 bytes**:

| mask | bytes per object | b | max residual |
| --- | --- | --- | --- |
| `0x100000200000` | **80** | 20.00 | **0.00** |
| `0x0000082001ff` | **328** | 20.00 | **0.00** |
| `0x8000202402ff` | **589** | 21.59 | 1.68 |
| `0x8000202408ff` | **1021** | 21.72 | 1.72 |
| `0x8000202410ff` | **1597** | 22.00 | 2.00 |

So **`size = archetypeSize x count + ~20-byte header`**, where the archetype size is a constant
determined by the component mask -- *which is exactly what an ECS chunk's serialized size looks
like*, and it ties the descriptor's mask to its payload quantitatively rather than by name.

**The obvious corroboration is weak and is not claimed as support.** Bytes-per-object correlates
only **+0.550** with the number of components in the mask, and *masks with the same 13 components
give 505, 589, 733, 1021 and 1597* -- consistent with different components having different
sizes, but no evidence in its own right. **The fit is the result; the component count is not.**

A second confirmation fell out of the offsets: **slot 4's storage ends exactly where slot 5's
begins**, which is only true if slot 4 is a byte vector -- the reading established earlier from
value shape alone now also holds geometrically.

### Inside a block

**The names are a fixed-width array, not a string pool.** Across 100 blocks in 8 files, the
spacing between consecutive names is **exactly 64 bytes in 99.83%** of 2,420 gaps, and each slot
holds a **NUL-terminated ASCII name zero-padded to 64 bytes** -- text lengths run 15 to 63, never
exceeding 63 plus the terminator, and the remainder is zero in almost every case. That is a
`char[64]` field, which is *also why the names are duplicated*: **the block stores its own fixed
copy of a name the FlatBuffers side already stores as a variable-length string.**

### How a block's regions are ordered

Over **48 blocks** of at least 8 KB carrying both names and matrices:

| | |
| --- | --- |
| all matrices before all names | **47 / 48 (97.9%)** |
| all names before all matrices | 1 / 48 |
| ***interleaved*** | ***0 / 48*** |

***The zero is the informative cell.*** The two populations never mix, so a block is
**regionally partitioned**, not a sequence of per-object records -- which is the same conclusion
the failed name-to-matrix proximity test reached from the opposite direction. Median layout:
float/header content to ~0.31 of the block, transforms ~0.31-0.53, names ~0.54-0.61, trailer
after; and the gap from the last matrix to the first name is typically **96 bytes**, one
transform record.

**The name array is contiguous in 85.4%** of blocks -- `count x 64` spans exactly the distance
from first to last.

***The transform region, however, is not one contiguous array.*** At 96-byte stride it breaks
into a median of **58 separate runs** per block (min 3, max 1,027).

**But the stride itself is stable.** Grouping matrices by the descriptor whose block they fall
in, the dominant gap is **96 bytes in 50 of 50 groups, for all 19 distinct component masks
observed.** *So the record size does not vary by component mask* -- a hypothesis raised by one
file whose gaps were dominated by 160 (= 96 + 64, temptingly a record plus a name slot) and
**refuted as soon as it was measured across files.** The fragmentation is skipped slots within a
constant-stride array, not a varying record size.

A sample record reads as an identity rotation with translation (-67.30, 1.336, -2.051) followed
by `(0, 1, 0, 0)` and 80 zero bytes.

#### What separates the runs: two hypotheses, both refuted

***The skipped slots are not rejected matrices.*** Enumerating every 96-aligned slot between the
first and last accepted matrix gives **228,075 skipped slots**; they pass the scale-relaxed test
at **0.23%** against a random-position control of **1.90%**. **They are *less* transform-like
than random data**, so loosening the acceptance test would not recover them -- and the count
rising from 1,846 to 2,543 on one file, which suggested this, was measuring something else.

***There is no count word before a run.*** The dword preceding a run equals the run's length in
29.13% of 13,978 runs and its byte length in **0.00%** -- and the sampled cases read `0` before a
run of 2, contradicting the match outright. *29% is chance-level agreement between two small
integers*, and **is recorded as a non-result rather than a weak signal.**

***The framing itself was wrong.*** 228,075 skipped slots against a far smaller number of
accepted ones means the matrices are **not a dense constant-stride array with holes**; they are
**short runs scattered through a much larger region**.

#### The ECS reading predicts this, and is only half borne out

Once the descriptor is understood as an archetype plus an entity count, the natural reading is a
**struct-of-arrays chunk**: each component type gets its own contiguous array, which would
explain the never-interleaved regions, the `char[64]` array and the transform runs at once, with
the space between runs being *other components' arrays*. It makes a sharp prediction: a block's
transform array should hold exactly one entry per entity.

**It does not.** Across 87 descriptors and 16,577 runs, the number of matrices in a descriptor's
block equals its entity count in **0.00%** of cases.

*What does hold is weaker:* **no run exceeds the entity count** (99.3% at or below) and **20.73%
match it exactly**. But the array reading fails a second, independent test as well: **the span
from a group's first to last matrix, measured in 96-byte slots, equals its entity count in 0% of
groups and exceeds it in 60%**, with a median span/count of **2.07** and a maximum of **4,519**.
*Matrices are not laid out as one N-slot array per descriptor.* **The ECS struct-of-arrays
reading is not supported and is dropped rather than kept as a plausible story.**

#### What actually fills the space between transform runs

Measuring the acceptance test first -- as the failed hypothesis above said to do -- answers it.
Of 33,022 rejected slots adjacent to an accepted matrix, the conditions fail in a very
particular pattern: **`col3 zero` passes at 96.74% while `m15 == 1` passes at 8.98% and
`scale uniform` at 0.00%.** *That is the signature of all-zero data*, which satisfies a
zero-column test and fails every other one. Confirmed directly:

| | |
| --- | --- |
| zero words within those slots | **86.12%** |
| slots whose 64-byte matrix region is entirely zero | **56.15%** |
| slots that are entirely zero across all 96 bytes | 12.44% |

***So the space between transform runs is mostly zeros.*** Not a rival structure, not a component
array -- **sparse default space**, which is the same answer the corpus decomposition gave from
the other direction when it found 45.75% of all unreached bytes to be zero. *It also explains
the earlier puzzle that skipped slots are* **less** *matrix-like than random data (0.23% against
a 1.90% control): zeros fail the relaxed test too.*

**An earlier count of 25/25 for the ordering was measured on a smaller, easier subset** (blocks
with any names and matrices rather than at least three of each). The honest figure is 47/48.
*Widening the sample moved the number, which is the reason to widen it.*

***A length-prefix reading was tried and is not supported.*** The first dword of a block is close
to the block's length for some blocks -- **39 of 100 within 512 bytes**, with a suspiciously
consistent 132-142 byte difference -- but it is exact in **0 of 100**, and the remainder are
nowhere near (one reads 1,057,398,912 for a 61,138-byte block). *Either the block boundary taken
from the coverage mask is not the true block start, or the first dword is not a length.*
**Recorded as unresolved rather than as a near-miss worth quoting.**

***A plausible reading was tested and refuted.*** If each named instance carried its own
transform, names and matrices would interleave. They do not: the distance from a name to the
nearest matrix is **worse than chance** -- 0.5% within 256 bytes against a random-offset control
at 20.6%. **Names and transforms live in separate regions**, which is what a pooled string table
beside a contiguous transform array looks like, and *not* a record-per-instance layout.

One further structure was isolated in the residue: a **24-byte fixed-stride record** whose six
words are four constants, one sentinel `0xffffffff` and one small varying field -- a
fixed-capacity, mostly-default table. It is real (17x its control) but minor, **1.59%** of the
unreached bytes. **A constant-byte-fill hypothesis was measured and dropped** at 0.28%; the one
20 KB run of `0x02` that suggested it is an outlier, not a category.

The bucket counts live in `reports/chunk_data/init_chunk_residue_latest.{json,md}`.

### FIRST LOOK AT THE 98%: NAMED PROXY-ENTITY RECORDS

The unaccounted region opens with a **length-prefixed string** -- `16 00 00 00` followed by
exactly 22 bytes of `GrassGrid_0_0#0_A5F014`, `19 00 00 00` then 25 of
`GrassGrid_0_-64#0_26E4C30`. The names follow `<Type>_<x>_<y>#<n>_<hash>`, and the
coordinates step by **64**, not the 128 of the chunk origin.

**The type vocabulary is `ProxyEntityType`.** Over 400 files:

| name prefix | count | | name prefix | count |
| --- | --- | --- | --- | --- |
| `SurfaceTypeData` | 147 | | `GrassGrid` | 19 |
| `AudioEmitter` | 42 | | `AudioScatterEmitter` | 14 |
| `AudioRoom` | 39 | | `MergedCollider` | 7 |
| `AudioPortal` | 5 | | `ClothGroupInfo` | 6 |

-- `TerrainSurfaceTypeData`, `AudioEmitter`, `AudioRoom`, `AudioPortal`, `GrassGrid`,
`GpuClothGroup`, `MergedRenderCollider`, beside plain Unity object names
(`Reflection Probes`, `Point Light`, `New Game Object`).

***This vindicates the refusal and relocates the enum.*** `ProxyEntityType` was refused as
slot 5's kind code on an external anchor -- 0 of 28 codes matched the `iv` block's counts,
with a positive control proving the test could fire -- and slot 5 was shown not to be a
placement list at all. **Both conclusions stand, and the enum does appear in these files:
as the names of records in the region nothing had looked at.** *The enum was real, the
refusal was right, and they were about different parts of the file.*

**Strings are only 0.1% of the bytes**, roughly one name per file.

***And the records that carry them are small, which moves the mystery rather than solving
it.*** Tracing the single uoffset that points at `GrassGrid_0_0#0_A5F014` (at 2140, in a
9,480-byte file) reaches a table at 2128 with **vtable size 12, objectSize 16 and slots
`[4, 0, 8, 12]`** -- four fields, one absent, the name in the last. *A 16-byte table is a
directory entry, not a payload.*

So the earlier guess in this section -- "the bulk is the binary payload that follows each
name" -- is **not** supported: the name belongs to a compact record, and the 98% lies
elsewhere. **What the region contains is still open; what is now known is that it is not
hanging off these name tables.**

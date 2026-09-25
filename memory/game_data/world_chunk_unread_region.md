# The former slot-4 hypothesis and the gap the walker could not follow

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** This is the history of the unread-byte investigation,
including retractions and coverage figures that depended on the walk. Read
[`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) before using any
old claim about a runtime "slot-4 region": root slot 4 is a vector of
packed four-byte entries, and
slot-7 field 3 is a forward FlatBuffers offset rather than an offset into that
hypothetical region. The large unread runs discussed below are a separate
remaining gap.

## Current framing of the slot-7 references

The maintained paired-group reader in
`scripts/game_data/streaming/framing.py` (`_parse_paired_group_subgraph`)
continues the earlier correction. In the selected framing, each nonempty Init
group's slot-7 field 3 reaches a counted vector of **8-byte descriptors**. Each
descriptor has a little-endian `u16` anonymous id, a `u16` stride-shaped value,
and a zero `u32`.
In the current bounded probe, slot-7 field 4 stores the short forward offset
`4` in every nonempty group; dereferencing it reaches a one-field table, whose
field 0 reaches a counted byte vector. The complete byte-level equality is:

```
wrapped byte-vector length = group field-1 count * sum(descriptor u16 strides)
```

The byte reader establishes **exact anonymous framing**; the selected native
consumer below independently reads those vectors but does not name the
components. The old field-3 reading as an alternating `(code, 0)` list used 4-byte
elements and stopped halfway through the descriptor vector. The old field-4
reading as a scalar constant missed the wrapper because the relative offset
was never followed. A current source-authenticated, path-stratified probe of
paired Init/Streaming files, including large files, rechecks the equation from
the decoded bytes and compares it to the maintained reader. Every nonempty
Init group in that bounded probe satisfies it; the Streaming twins have empty
paired-group vectors in this selection, so the sample does not establish a
nonempty Streaming group shape. Changing counts and the source identities live
in `reports/chunk_data/slot4_pair_probe_latest.json`; the reusable check is in
the maintained reader. Increasing one descriptor stride by one makes the
reader reject the original blob length, and changing a field-4 relative offset
from `4` to `8` in the blackbox example makes the target fail table framing.

### Descriptor-major byte layout: one directly identified field

The length equation alone permits both descriptor-major and row-major storage.
Four bounded Init files from different scene directories resolve that ambiguity
without assigning the other descriptor IDs. Their packed MD5 and decoded SHA256
match the VFS-authenticated paired-file report, and the VFS stream independently
verified each file's MD5. For each group, split the byte vector in descriptor
order into regions of `group count * descriptor stride`, then split each region
into `group count` fixed-width slots. In those files, selected descriptor
**21** has stride **64** in each of 14 populated groups. All **239/239** of its
resulting slots are printable ASCII strings containing `#`, followed by a NUL
byte and zero padding through byte 63. Examples include
`New Game Object#0_3B09708` and `MergedCollider_-4_-2_0_0#0_5DC8105`.
The row-major control, using the same descriptor sequence and bytes, fails
that exact slot predicate in **224/239** slots.

There is an independent same-file identity join. The paired field-6 wrapper
holds one `u32` per group row. Pairing those values by index with the
descriptor-major strings yields **239/239** exact `(u32, string)` matches
against the root field-3 / field-5-field-0 parallel rows. The row-major
control gives only **9/239** exact pair matches. Three files' grouped pairs
cover all their root pairs; one has 22 grouped pairs among 30 root pairs.
That four-file result identified a stored name field and confirmed the
descriptor-major layout, but it missed a fixed-width limit. A current full
corpus gate now rereads every authenticated Init logical file from its physical
VFS chunk, checks its ledger MD5 and input-set identity, and applies the
maintained framing reader. Descriptor **21** occurs once per populated group
at stride **64**. Every NUL-terminated printable slot joins its paired group
ID to the same-file root ID and the **first 63 bytes** of the root name. The
row-major control fails that relationship for most slots.

The full-name comparison fails on long names whose serialized slot omits a
suffix; in a few cases truncation removes even the later `#` token. The old
predicate's requirement for `#` and full-name equality therefore rejected
valid stored prefixes. Additional root pairs have no matching descriptor-21
slot; the root catalog is not exhausted by these groups. This establishes a
duplicated *name prefix*,
not recovery of every complete name from the descriptor bytes, a component
label for other IDs, or runtime object ownership. The independently authenticated
DynamicStreaming auxiliary pairs show the same descriptor-21 prefix rule; see
[`world_dynamic_streaming.md`](world_dynamic_streaming.md). Neither selected
consumer maps that column to a named runtime component. The reusable audit is
`scripts/game_data/streaming/descriptor_name_corpus.py`, its selected-slot
reader and row-major control are in `streaming/descriptor_names.py`, and the
source identities, exceptions and changing totals are in
`reports/chunk_data/descriptor_name_corpus_latest.json`.

### Selected native consumer of the group descriptor and byte vectors

The reviewed `streaming_field2_native.json` contract now closes the **static
consumer path** from the first paired root, whose path formatter selects
`InitChunkData`. On the branch where both paired roots are available and the
group runtime state has not been populated, the selected UnityPlayer body
loads the first root from its carrier, follows root slot 7 to each group,
follows group field 3 to the counted
8-byte descriptor vector, and follows group field 4 through its one-field
wrapper to the counted byte vector. In parallel it follows root slot 6's
wrapper to an ID-vector count. It passes all three counts and the descriptor
and byte-vector data pointers to one native consumer. The exact body and
accessor bytes validate against the explicitly selected installed
`GameAssembly.dll`, metadata and `UnityPlayer.dll`; the direct call targets were
also checked in the local receipt.

That consumer reads the first and second descriptor words as signed 16-bit
values. The first selects an anonymous runtime field; the second is multiplied
by the group ID count. The consumer copies that many bytes from the current
position of the wrapped byte vector, then advances the position before the
next descriptor. It compares each proposed end with the passed blob length
and compares the final position with that length. **Both mismatch branches log
diagnostics and continue**; the native routine is evidence for
descriptor-major ordering and the count-times-stride extent, not a safe input
validator. The maintained framing reader is stricter and rejects a length
mismatch. The reader's `u16` labels describe the stored two-byte widths; the
selected consumer sign-extends **both** words. In the authenticated bounded
corpus, IDs and strides stay within the nonnegative signed range, so the two
interpretations agree there. A word with its high bit set would need separate
review.

This strengthens the byte-side ID/name join above: the native consumer uses
the same descriptor-major portions that make descriptor 21's 64-byte name prefixes
line up with the root IDs. It still does not assign component names to other
descriptor IDs, prove an actual run through this branch, or bind the runtime
root to one authenticated VFS file. The remaining native discriminator is a
checked mapping from a descriptor ID to a named component consumer, followed
by a concrete runtime root/file receipt. The selected contract records the
per-build instructions and hashes; `reports/chunk_data/slot7_native_consumer_latest.json`
holds the local call-target and source-byte checks.

A selected-build name-binding check narrows one tempting shortcut. The
`PropertySerializeId.GetComponentIndexFromType` UnityPlayer binding computes
the bit index of an input mask; the descriptor consumer uses a separate
anonymous bit-prefix helper to select a packed column. A raw executable-section
literal-call census finds only three calls to that helper: the selected
descriptor copy loop, its archetype setup, and another generic copy loop. The
`FlatBufferConvertContextV2.get_componentScopeEntityName_Injected` binding
does read a NUL-terminated pointer at native conversion context `+0x88`, but
the selected IL2CPP type has no corresponding getter method, and none of those
checked generic loops carries descriptor **21** to that context field. The
binding name and the matching stored strings therefore do **not** identify
descriptor 21 as a named runtime component. A direct reader of that packed
column, or a checked conversion-context constructor that passes its pointer
to the name getter, is the next discriminator. The reviewed contract's
`groupComponentNameCandidate` block pins the binding tables, code windows,
metadata absence, and bounded call census; it does not exclude indirect or
inlined column selection.

The previous complete Streaming root-subgraph corpus gate has an older
`inputSetSha256`, so its publication status is **not refreshed** by the
descriptor-name corpus gate. A separate
current-audit byte-identity transfer reread every block-15 packed logical file,
checked each against its VFS ledger MD5, reproduced the complete gate's sorted
logical-identity digest, and checked that the maintained framing reader has the
same bytes as the gate's recorded parser. The selected field-2 native contract
also validates against the explicitly selected installed client. Thus the
older complete gate's structural observations apply **conditionally to these
identical bytes**; its old provenance fingerprint remains old. The join receipt
and changing totals are under `reports/chunk_data/slot4_identity_join_latest.json`.
This transfer concerns byte framing; other native consumer claims in that
older report are outside this check.

The blackbox file used below gives a bounded example: group field-1 count `33`,
descriptors `(21, 64, 0)` and `(44, 16, 0)`, and a `2,640`-byte blob, exactly
`33 * (64 + 16)`. **The native join does not resolve its historical large unread
run.**
The current reader certifies the small wrapper and blob but no range within
that named run. The reader's `decodedCertifiedRanges` distinguish bytes it has
framed from other bytes merely present in the same decoded file; the residual
needs its own references or structure before it can be assigned an extent or
meaning.

## RETRACTED, AND A MUCH LARGER GAP FOUND

The paragraph this replaces claimed the records "are not here to decode". **That was an
inference from two guessed bases failing, and it is wrong.** The decisive test is coverage:
walk the FlatBuffers structure from the root, mark every byte it accounts for -- vtables,
tables by declared object size, vector prefixes and elements -- and measure what is left.

Over 3,000 files:

| | |
| --- | --- |
| buffer bytes accounted for by the FlatBuffers walk | **1.65%** |
| files with enough free bytes anywhere for an `s4` region | **94.60%** |
| files with a **contiguous** free run >= `s4` | **77.40%** |

**There is ample room; the claim was unsupported.** But the number that matters is the
first one. ***These files are 98% unaccounted for by everything this project has framed of
them.*** The root table, its eight slots and the three vectors -- the entire structure
recovered across many batches -- describe **one part in sixty** of the bytes.

*That was invisible because nothing ever measured it.* Every result here was framed as
"this field means X", verified against controls, and gated over the corpus -- all true, and
all about a sliver. A 34 KB file with `n5=1, n6=2, n7=2` was being described by a reading
that covers a few hundred bytes of it.

## CORRECTION: the 98% figure was an artefact of the walk, not a property of the files

The walk that produced 1.65% followed **only root slots 5-7**. A full recursive walk --
every root slot, recursing through tables, vectors of tables and strings -- reaches
**54.91%** of buffer bytes over 300 files, finding **7,751 tables, 1,258 vectors and 2,429
strings** (about eight strings per file, not the one the sampling suggested).

| walk | coverage |
| --- | --- |
| root slots 5-7 only | 1.65% |
| **full recursive** | **54.91%** |

***So "98% unaccounted" was wrong by a factor of thirty.*** I measured coverage with an
instrument I had already documented as partial, then quoted the result as though it
measured the files -- and wrote *"it will not raise it to anything near 100%"* in the same
breath, which was a prediction made to protect the number rather than test it. It rose to
more than half.

**What survives.** Roughly **45% of `InitChunkData` is still not reachable** from the
FlatBuffers root by this walk, which is a real and large gap -- the element table is still
complete only for the element, and the bulk question stands. *But the gap is a third of
what was claimed, and the claim was repeated across several entries before it was checked.*

**The lesson is narrower than "measure coverage".** Measuring was right. The error was
reporting a floor as though it were the value, when the instrument's known blind spot was
the obvious first thing to close.

## WHAT THE REMAINING 45% IS: vectors the walker cannot follow

Breaking the unreached bytes down by run length, **weighted by bytes rather than by run**:

| unreached runs | bytes | share |
| --- | --- | --- |
| < 16 (alignment padding) | 26,210 | 0.2% |
| 16-63 | 16,897 | 0.2% |
| 64-255 | 50,679 | 0.5% |
| **>= 256** | **10,953,692** | **99.2%** |

*A first pass at this counted runs instead of bytes and concluded "mostly padding" -- there
are indeed thousands of tiny runs, and they are 0.9% of the volume.* **The same mistake as
the coverage figure itself: the right measurement reported through the wrong statistic.**

**And the large runs are FlatBuffers.** Their heads look like this:

```
11 00 00 00   cc 02 00 00  bc 02 00 00  ac 02 00 00  9c 02 00 00  3c 02 00 00
   count 17      descending 32-bit offsets ...
```

A count followed by descending offsets is **a vector**, and 266 distinct 64-byte heads
across the sample share that shape. The walker misses them because `follow()` only accepts
a target as a vector when its first elements resolve to valid *vtables* -- so vectors of
**structs or scalars** are rejected and their bytes never marked.

***The obvious conclusion -- "the gap is walker capability" -- was drawn and then tested,
and it does not hold.*** Extending the walk to accept any vector whose elements all resolve
in-bounds as offsets (marking the vector's storage but recursing only into targets that
independently validate) finds **1,648 such vectors** and moves coverage from **54.91% to
56.30%**: a gain of **1.4 points** against a 45-point gap.

| walk | coverage |
| --- | --- |
| root slots 5-7 only | 1.65% |
| tables, table-vectors, strings | 54.91% |
| **+ offset-vectors** | **56.30%** |

So the large runs are **not** mostly vectors of the kind the walker was rejecting. *The
diagnosis was reasonable, specific, and wrong -- and it cost one run to find that out
rather than being carried forward as an assumption.*

**Where that leaves it, measured rather than guessed.** Two facts settle the character of
the remaining 44%:

- ***The gap is concentrated in a minority of files.*** Of 341 files, **221 have no
  unreached run of 256 bytes or more** -- they are walked essentially in full. Only **120**
  carry a large unreached region, and those are the big files.
- ***RETRACTED: "those regions are addressed".*** That claim came from scanning every
  4-byte position for a value resolving into the run -- 6,274 hits, 120 of 120 runs -- and
  it was published **without a control**. With one, it collapses: a **randomly placed
  window of the same size** in the same files draws **13,717 hits, 114.3 per run**, against
  the real run's **52.3**. *The real region attracts fewer apparent pointers than chance
  does.* **The test measures how often arbitrary 32-bit values land in a range, not whether
  anything points at it**, and the region's addressability is unknown.

  The tell was in the examples: `table@28 obj=40 +12, v=128` is the **root's own origin
  field** -- `y*128` -- read as though it were a uoffset. Coordinates, counts and floats all
  "resolve" when every word is treated as a pointer.

And they are not simple arrays: no run satisfies `4 + count*W == length` for `W` in
{4, 8, 12, 16, 24, 32, 36, 48}, so the head is not a count over a fixed stride.

***So the honest position is narrower than any of the four claims made about this region.***
It is not "unexamined bulk" (56.30% of the bytes are reached), not "walker capability" (the
fix gained 1.4 points), and not "densely cross-referenced" (the control refutes it). What is
established is only this: **about 44% of `InitChunkData` bytes are not reached from the
FlatBuffers root, concentrated in 120 of 341 files, in runs of 256 bytes and up whose
internal structure is unknown.**

*Four successive characterisations of this region were wrong, and each was caught by the
next measurement rather than by better thinking.* The one that should not have happened is
the last: **a positive result published without the control that this project applies
everywhere else.**

## What the region actually contains, described rather than theorised

Dropping the question of *how* it is reached and simply describing the bytes -- with the
**reached** bytes of the same 120 files as the control:

| word class | unreached | reached |
| --- | --- | --- |
| zero | **43.74%** | 23.79% |
| small int (< 4096) | **10.66%** | 5.41% |
| plausible float (1e-4..1e6) | 9.03% | **20.40%** |
| other | 36.57% | **50.40%** |
| *words sampled* | 791,863 | 2,293,309 |

**The profiles differ substantially**, so the unreached region is *not* simply more of the
walked structure: it is **~1.8x as sparse** (zeros), carries **~2x the small integers**, and
holds **less than half the float density**.

*The walked tables are where the floats live* -- transforms, bounds, centres and extents,
which is consistent with everything recovered from them. **The unreached region is
integer-and-zero-dominated, which is the signature of index or table data with many unused
slots**, not of geometry.

That is a description, not an identification, and it is offered as one. **But it is the
first statement about this region that was measured against a control and survived** --
after four that were not.

## The zeros are interleaved, but there is no record stride

Where the zeros *sit* distinguishes reserved space from records with empty fields. Measuring
run lengths inside the unreached region:

| zero-run length (words) | count | | non-zero run | count |
| --- | --- | --- | --- | --- |
| **1** | 34,554 | | 2 | 21,409 |
| **3** | 33,117 | | **8** | 14,178 |
| 4 | 2,170 | | 7 | 6,594 |
| >= 16 | 1,130 | | 6 | 5,860 |

**Almost no long zero blocks.** The 43.74% zeros are *interleaved* in runs of one and three
words -- empty fields between short bursts of data, not reserved padding.

***Which makes a fixed-size record array the obvious reading, and it is wrong.*** Testing
every stride from 2 to 32 words for how well position-mod-stride predicts zero-ness:

```
stride 32 words: 59.63%     stride 16: 59.58%     stride  8: 59.03%
stride 31 words: 59.18%     stride 24: 59.15%     stride  4: 58.97%
```

**Every stride scores between 58.97% and 59.63%** -- a spread of 0.66 points -- against a
majority-class baseline of about 56.3%. *The uniformity is the control: if any stride were
the record size it would stand clear of the others, and none does.* **There is no fixed
record period in this region.**

So the structure is short-range but not periodic: characteristic run lengths, no repeating
frame, and no flat array of fixed-size entries.

## Not encoded -- and a byte histogram that disputes an earlier claim of mine

"Encoded data" was one of two guesses offered above. **Entropy settles it:**

| region | byte entropy |
| --- | --- |
| unreached | **3.925 bits/byte** |
| reached (same files) | 5.110 bits/byte |
| compressed input to the terrain codec | ~7.6+ |

**Nothing compressed or encrypted looks like 3.9 bits/byte.** The region is plain data.

***And its byte histogram sits awkwardly with something recorded above.*** The commonest
bytes are `0x00` (1,972,692, **59.6%** of the region), then **`0x3F` (91,638), `0x3E`
(48,183), `0x42` (43,565), `0x80` (41,767), `0x3D` (36,344)**.

`0x3D`-`0x42` is precisely the **IEEE-754 exponent range for ordinary magnitudes** -- the
high byte of a float near 0.05 to 100. Their prominence is evidence of substantial float
content, which is hard to reconcile with the earlier finding that this region carries
**"less than half the float density"** of the walked structure (9.03% against 20.40%).

***Resolved: the float count was sampling the wrong alignment.*** Measuring the
float-plausible rate at each of the four byte phases inside the run:

| phase (relative to the run start) | float-plausible |
| --- | --- |
| 0 | 8.17% |
| **1** | **24.25%** |
| 2 | 9.41% |
| 3 | 9.92% |

and the exponent bytes `0x3D`-`0x42` sit at **absolute position mod 4 == 3** in **230,164**
cases against 8,794 / 5,519 / 6,450 elsewhere -- a 26-to-42-fold concentration.

**The two agree.** A little-endian float keeps its exponent in the *high* byte, at `+3`, so
exponents at `mod 4 == 3` mean the floats start at `mod 4 == 0`: **properly aligned in
absolute file coordinates**. The runs themselves do not begin on a 4-byte boundary, so
iterating phases *relative to the run start* sampled the wrong alignment -- which is exactly
what the 9.03% figure did.

***So the earlier characterisation is reversed, not merely unsafe.*** At correct alignment
the unreached region is about **24% float-plausible**, against **20.40%** measured over the
reached bytes (whose iteration was absolute, and so correctly aligned). *The region is at
least as float-dense as the structure that was walked* -- **not "integer-and-zero-dominated,
not geometry", which was an artefact of an off-by-one in the sampler.** (The two rates use
slightly different magnitude bands, `1e-3..1e5` against `1e-4..1e6`, so treat the comparison
as qualitative.)

**Worth naming the failure mode:** the byte histogram and the word classifier disagreed, and
the disagreement was the signal. A single measurement would have been believed.

## The floats are normalised, not positional

With the alignment fixed, the values can be read. Testing them against the chunk box that
identified slot 7's centre gives **nothing**: `own X` 35.53% against a neighbour-box control
of 31.00%, `own Z` 41.68% against 38.15% -- gaps of three and four points, where the slot-7
centre scored 73.96% against 1.28%. **These are not world coordinates.**

What they are is small:

| band | share of 332,031 aligned float-plausible words |
| --- | --- |
| `0..128` | **93.85%** |
| `128..256` | 4.63% |
| `256..384` | 1.42% |
| `384+` | ~0.00% |
| **of which `|f| <= 1`** | **72.05%** |

*The decay is the control* -- 93.85% into the first band against 4.63% into the next is not
what a positional quantity spread over a 128-unit chunk looks like; it is what **normalised
values** look like. **Nearly three quarters of these floats lie in `[0, 1]`.**

**So the unreached region is normalised float data interleaved with zeros** -- weights,
factors, normals, colours or coefficients rather than geometry -- **which is why the
world-box join that worked on slot 7 finds nothing here.** Taken with the rest: ~44% of
bytes, in 120 of 341 files, entropy 3.925, zeros in runs of one and three, no record stride,
floats 4-byte aligned in absolute coordinates and 72% of them in the unit interval.

## A lead on the consumer: the region tracks `GrassGrid`

Grouping 400 files by which names they contain, and measuring unreached bytes per group:

| name present | files | unreached | mean file size |
| --- | --- | --- | --- |
| **`GrassGrid`** | 17 | **68.5%** | **740,677** |
| `Reflection Probes (5)#0` | 45 | 51.5% | 1,227 |
| `AudioScatterEmitter` | 13 | 36.0% | 1,881 |
| `AudioRoom` | 38 | 30.1% | 6,269 |
| `AudioEmitter` | 42 | 22.4% | 6,769 |
| `SurfaceTypeData` | 147 | 16.2% | 83,829 |

***Files naming `GrassGrid` are about a hundred times larger than the rest and the most
unreached of any group*** -- 68.5% against `SurfaceTypeData`'s 16.2%, even though those
files average 83 KB and are the most common name by far.

**Normalised floats in `[0, 1]`, interleaved with zeros, in very large files that name
grass** is a coherent fit for density or per-instance attribute data.

***The test was run, and the lead does not survive it intact.*** Correlating against raw
unreached **bytes** gives `GrassGrid` +0.479 -- but **file size alone scores +0.978**
against the same target, because unreached bytes are a roughly fixed fraction of any file.
*Anything that correlates with size correlates with unreached bytes.* Normalising to the
unreached **fraction**:

| against the unreached fraction | correlation |
| --- | --- |
| `GrassGrid` count | **+0.234** |
| `SurfaceTypeData` count | **-0.768** |
| file size (residual) | +0.176 |

**Most of the grass signal was the size confound.** What survives is modest: files naming
`GrassGrid` average a 45.6% unreached fraction against 22.8% for those that do not -- a real
two-fold difference, but +0.234 is not the `+1.000` that identified `(Collider,
TerrainCollider)`, and it does not identify a consumer.

***The strongest effect in the data is the control, and it is negative.*** `SurfaceTypeData`
scores **-0.768**: the more of those records a file carries, the *better covered* it is.
That is worth more than the grass lead -- **it says the walk handles `SurfaceTypeData`
content well, and that the unreached region is largely what is left when those records are
accounted for.**

## THE GAP IS SEVEN FILES, NOT A PROPERTY OF THE FAMILY

Chasing *which name* owns the unreached bytes was the wrong question. Coverage tracks
**size**, not content: a **65,836-byte** file carrying a single `SurfaceTypeData` name is
**99.9% covered**, while a **2.2 MB** file with the same single name is 77.9% unreached.

Concentrating the 400-file sample (27,658,484 bytes, 40.01% unreached):

| | share of all unreached bytes |
| --- | --- |
| top 1 file | 22.72% |
| top 5 files | **84.13%** |
| top 10 files | 93.59% |
| **the 7 files >= 1 MB** | **90.41%** |
| **the 382 files < 100 KB** | **3.73%** |

***So "44% of `InitChunkData` is unreached" was a true number with a false implication.***
It is not a property distributed across the family -- **393 of 400 files are walked
essentially in full**, and the entire gap is a handful of multi-megabyte files, five of
which carry 84% of it.

**That is a far smaller and more tractable target than anything claimed for this region so
far**, and it explains every confusing correlation above: `GrassGrid` and file size both
correlated with unreached bytes because the giant files happen to name grass; `SurfaceTypeData`
correlated negatively because the small, fully-covered files are dominated by it. *The
size confound was not a nuisance in the measurement -- it was the finding.*

## Opening the largest offender

`InitChunkData_-1_0_0_0.bytes` in **`blackbox02_dg001`** -- 3,238,664 bytes, **77.6%
unreached**, across **125** runs, the largest **444,381** bytes.

Sampling the big run shows what the bytes are:

```
b9 f3 48 3d  b9 f3 48 3d  b9 f3 48 3d     <- 0.04905 repeated
e0 a3 a9 3c  e0 a3 a9 3c  e0 a3 a9 3c     <- 0.02071 repeated
00 00 80 3f                                <- 1.0
00 00 00 00 ... (long stretches)
```

**Identical floats repeated in threes, `1.0` constants, and long zero regions.** That is
consistent with the normalised-float profile measured earlier, and the *repetition* is new:
consecutive entries carrying the same value, either `Vector3(v, v, v)` or runs of identical
per-element data.

**Reading that run directly** -- 444,381 bytes at offset 2,601,975, **111,095** aligned
words:

| property | value |
| --- | --- |
| zero words | 66,768 = **60%** |
| distinct values | **13,164** of 111,095 = 12% |
| adjacent words equal | **47.5%** |
| equal-value run lengths | 1: 44,510 · 2: 6,624 · 3: 3,438 · 4: 3,640 · **12: 142** |

| commonest value | count | as float |
| --- | --- | --- |
| `0x00000000` | 66,768 | 0 |
| `0x3f800000` | 4,707 | **1.0** |
| `0x4276d70a` | 2,966 | **61.71** |
| `0x3d48bcb8` | 591 | 0.0490081 |
| `0x3f0161de` | 375 | 0.5054 |

**Only one word in eight is distinct**, and two constants dominate the non-zero content:
`1.0` and `61.71`. *`1.0` is the signature of a normalised default; `61.71` is not
normalised at all* -- a magnitude, repeated nearly three thousand times in one chunk.

The **12-word (48-byte) equal runs, occurring 142 times**, are the only long repeat, and
`48 = 12 x 4` is the size of three `Vector3`s or one `Transform` -- worth testing, though
run length is not a stride and the earlier periodicity test over this region found none.

***Answering that question, spatially.*** `61.71` occurs in only **5 of the level's 106
chunk files**, 19,144 times, and its distribution is **contiguous**:

| chunk origin | occurrences |
| --- | --- |
| (-256, 0) | 5,367 |
| (-128, 0) | 4,639 |
| (-256, -128) | 4,568 |
| (-128, -128) | 4,568 |
| `_Global_` | 2 |

**Four adjacent chunks forming a 2x2 block** -- x in {-256, -128}, z in {-128, 0}, a
256x256-unit area -- and nothing outside it. *A constant repeated thousands of times across
exactly one contiguous region is a property of that region, not of the format.*

It is **not** a bounds value from the walked structures: scanning every slot-7
centre-and-extents component in the level matches it **zero** times. So the unreached region
carries per-area quantities that the framed tables do not.

***The elevation reading was tested and is unsupported*** -- and the way it failed is the
finding. Comparing `61.71` against slot-7 centre heights:

| | result |
| --- | --- |
| placements **inside** the 2x2 block | **none at all** |
| placements outside (control) | 20, heights 25.80 to 124.22, median 70.41 |
| of those, within +-5 of 61.71 | 1 of 20 = 5%, i.e. chance |

**There was nothing inside the block to compare against, because those four chunks carry no
populated placements whatsoever.**

***That is a structural dichotomy, not a size difference.*** The large files are not "small
files with more in them": **their slot-7 vectors are empty and their entire content lives in
the unreached region**, while the small files carry their content in the tables the walker
reads. Two kinds of chunk file, and every coverage number in this section is the ratio
between them.

**So the framed structure and the unreached region are largely disjoint populations** --
which is why no join from one to the other has worked, and why `SurfaceTypeData` correlated
*negatively* with the unreached fraction. *The next attempt should stop trying to reach the
blob from the root and read it on its own terms.*

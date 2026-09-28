# The transform-matrix bulk, and corpus coverage

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** What fills the unreached majority of the file: an array of
transform matrices, how blocks and runs are organised around them, and the measured
coverage figure for the corpus.

**Read first.** Every coverage figure here came from a deleted structural
walker that never marked the byte vectors behind slot-7 group field-4
wrappers ([`world_chunk_unread_region.md`](world_chunk_unread_region.md), the
walk-based coverage trap). The maintained reader
(`scripts/game_data/streaming/framing.py`) frames those vectors exactly, so
"unreached" below means unreached *by that walker*. No tracked module
implements the matrix scan; its test definition is kept here.

## The matrices

The largest unread run (444,381 bytes in
`blackbox02_dg001/InitChunkData_-1_0_0_0.bytes`) starts at an offset that is
not 4-aligned. Word reads shifted by three bytes made float exponent bytes
look like the small integers `0x3f`, `0xbf`, `0xbe`. Realigned in absolute
coordinates, `1.0` recurs every 24 words, and sixteen floats on that stride
form a 4x4 affine transform -- read row-major, a Y-axis rotation at uniform
scale with the translation in the last row and a fourth column of
`(0, 0, 0, 1)`; this is the Unity column-major layout with translation at
indices 12-14.

**Acceptance test** (the TRS scan): sixteen floats whose fourth column is
`(0, 0, 0, 1)`, rows mutually orthogonal to 1e-3 and scale uniform to 1e-3,
tried at every 4-aligned offset. Random 16-float windows pass **1.88%**.

- In the blackbox file 19,990 windows pass; 92% of consecutive gaps are
  exactly 96 bytes, giving a record `[64-byte matrix][16 zero bytes][16 bytes
  of floats]`. A second large file's share was much lower, so one file is not
  a corpus figure.
- Across the full Init corpus about **6.7 million** matrices pass the test.
- `61.71`, the value that recurred thousands of times across a 2x2 chunk
  block with no populated groups, is the **Y translation** -- the ground
  height of those objects. It was a coordinate read as an opaque constant.

Map recovery (`scripts/webui/map/recover_map_streaming_instances.py`) reads
exact placements from the slot-7 group byte vectors: descriptor 18 (else 27)
as a column of column-major 4x4 matrices, descriptor 21 as names. That
column choice is the builder's; no native consumer names those descriptor
IDs. How the 96-byte-stride matrices the scan finds relate to those columns
is not established.

## Corpus coverage, as the deleted walker measured it

With the walk made fast (below), the full Init set walked with no file
excluded:

| measure | value |
| --- | --- |
| bytes the walk did not reach | just under half of the decoded bytes |
| share of those inside a 96-byte TRS record | a little over a quarter |
| share of those that are zero bytes | 45.75% |
| non-zero bytes attributed to nothing | **11.65% of the format** |

Quoting "a third unaccounted" would overstate the gap about threefold; the
most useful thing done to this number was splitting it into named buckets.
A first pass with a 3-second per-file budget excluded 58 large files (about
a fifth of all bytes -- exactly the files holding most unreached content)
and flattered the result by about 2.8 points: an exclusion is not neutral,
and a coverage figure with the hard files dropped is worth less than none.
The generated figures are in `reports/chunk_data/init_chunk_coverage_latest`
and `init_chunk_residue_latest` (`.json`/`.md`), produced by the deleted
runner against an older audit fingerprint.

Residue buckets besides records and zeros: a **24-byte fixed-stride record**
(four constants, one `0xffffffff`, one small varying word; 17x its control,
1.59% of unreached bytes). A constant-byte-fill hypothesis scored 0.28% and
was dropped; the one long `0x02` run that suggested it is an outlier.

## The second copy: the same objects, stored again

- **Names are duplicated, not new.** 39.1% of all `<name>#<N>_<HEX>`
  occurrences lie in unreached bytes, but 99.61% of those are names the
  union rows already reach; 1,303 of 1,311 distinct names appear exactly
  twice, 72.6% with one reached and one unreached copy. The unreached bytes
  do not extend the scene population; they encode it a second time.
- **Fixed-width names.** Consecutive names sit exactly 64 bytes apart in
  99.83% of gaps, NUL-terminated and zero-padded -- a `char[64]` column. The
  maintained reader identifies it: descriptor 21, stride 64, holding 63-byte
  prefixes of the root names ([`world_chunk_unread_region.md`](world_chunk_unread_region.md)).
- **Blocks sit beside slot-7 groups.** Each large unreached block ends where
  a slot-7 group reference lands. The group's "size-like word" -- which the
  current framing shows is group field 3, a forward uoffset -- fitted
  `bytes-per-object * count + about 20` exactly or within 2 bytes per
  component mask (80, 328, 589, 1021, 1597 bytes per object, correlation
  +0.943 with the count). That is consistent with the exact framing: the
  group's wrapped byte vector is `count * sum(strides)` bytes, and the
  descriptor vector field 3 points at lies past it. The per-mask values also
  equal the summed strides of the descriptor IDs set in the mask; see the
  open conflict in [`world_chunk_slots.md`](world_chunk_slots.md).
- **Region order inside a block.** In blocks of at least 8 KB with both
  names and matrices, all matrices precede all names in 47 of 48 and they
  never interleave -- as descriptor-major columns in descriptor order would
  lay them out. An earlier 25/25 came from an easier subset; widening the
  sample moved the number, which is the reason to widen it.

## Eliminated readings

- **The walk is slow because it is pure Python / because of vectors.** A
  profile found `list.index` inside `table()` was 96% of the time (quadratic
  in slot count); a precomputed offset-to-position map made it 40-200x
  faster with byte-identical coverage. Two earlier guesses aimed at the
  wrong function, and the time budget never fired because its check sat in
  loops that did no work. Profile before optimising.
- **`min`/`max` beats `all()` for the printable test.** It was slower:
  `all()` short-circuits, and nearly every candidate fails on byte one.
- **A numpy pre-filter helps.** Unmeasurable: with a background run
  competing, the same walk varied up to 4x between runs. Benchmark on a quiet
  machine; an optimisation that cannot be shown to help was reverted.
- **Skipped 96-byte slots are rejected matrices.** Between accepted matrices
  they pass a scale-relaxed test at 0.23%, *below* the 1.90% random control;
  86% of their words are zero. The space between transform runs is sparse
  default space, not a rival structure.
- **A count word before each run.** It equals the run length in 29.13% of
  runs and the byte length in 0.00% -- chance agreement between small
  integers.
- **One matrix per entity at a 96-byte stride.** Matrices found by the scan
  equal a group's entity count in 0.00% of groups and span a median 2.07
  slots per entity. This refutes that particular array reading; it does not
  bear on the exact descriptor-major framing, whose columns the scan was not
  aligned to.
- **The record size varies with the component mask.** The dominant gap is 96
  bytes for every one of 19 masks; one file's 160-byte gaps did not
  generalise.
- **A length prefix at the block start.** Near the block length in 39 of 100
  blocks, exact in 0.
- **Names and matrices interleave per instance.** Name-to-nearest-matrix
  distance within 256 bytes is 0.5% against a 20.6% random control.
- **The bulk hangs off the name tables.** The length-prefixed
  `<Type>_<x>_<y>#<n>_<hash>` names (grid step 64, not 128) belong to small
  four-field tables -- slot-5 union rows -- not to large payloads. That the
  `ProxyEntityType` vocabulary (`GrassGrid`, `AudioEmitter`, `AudioRoom`,
  `SurfaceTypeData`) appears as these names does not reverse its refusal as
  slot 5's kind code: the enum and the refusal concern different parts of
  the file.

## Open

- Recompute coverage from the reader's `decodedCertifiedRanges` and say
  which of the recorded "unreached" bytes the descriptor-major vectors
  already account for.
- Locate the 96-byte-stride matrices relative to the descriptor columns, and
  the named blackbox run relative to the certified ranges.

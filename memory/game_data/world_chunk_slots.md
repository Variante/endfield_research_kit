# What the chunk slots mean

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** From framing to meaning: slot 5's kind codes and slot 7's
descriptor, each identified against a named engine enum rather than a magnitude
distribution. The refused candidates are kept beside the accepted ones, because
the refusals are what make the accepted reading load-bearing.

**Current framing** (`scripts/game_data/streaming/framing.py`): slot-7 group
field 3 is a forward uoffset to 8-byte descriptors and field 4 a forward
uoffset to a wrapper around a byte vector; see
[`world_chunk_unread_region.md`](world_chunk_unread_region.md). The enum-width
lesson below is recorded in the docstring of
`scripts/game_data/streaming/descriptor_component_index_gate.py`.

## Slot-5 kind codes: `StreamingLayer` x `ECSEntityType`

**Scope caveat.** These tests ran on slot-5 rows pooled across the three
union members ([`world_chunk_union_vectors.md`](world_chunk_union_vectors.md)).
The later per-tag re-read found field 1 with only 1-2 distinct values per
member, which cannot produce the pooled `f1` range 0..10, so the record does
not say which member fields the pooled `f1`/`f2` were. The identification is
kept as recorded; re-run it per tag before building on it.

Five lines supported it, each able to fail:

1. **Range.** `f2` takes `{0..10, 12, 13}`, which excludes `StreamingLayer`
   and `ProxyEntityType` (11 values each) and fits `ECSEntityType` (14
   values, all used except 11 `TerrainSplineDecal`). `StreamingComponentType`
   is excluded by coverage (30 of 44 members unused), not by the withdrawn
   "maximum 128" argument. `f1` takes exactly `0..10`.
2. **A terrain join from another block.** Pair `(5, 7)` occurs in 37 of 38
   terrain levels and 0 of 50 others -- but `(0, 4)` separates them too (38
   of 38); presence could not tell them apart, counts did. Read as `Collider` + `TerrainCollider`,
   `(5, 7)`'s count correlates **+1.000** with each terrain level's
   terrain-file count; `(0, 7)` (`Default` + `TerrainCollider`) +0.956, and
   `(0, 4)` (`Default` + `SphereCollider`) only +0.728 -- common outdoors
   without scaling with terrain, as sphere colliders should be.
3. **An earlier negative discriminates.** `ProxyEntityType` failed its
   independent IV-count test ([`world_chunks_families.md`](world_chunks_families.md));
   under `StreamingLayer`, `f1 == 0` is `Default`, which predicts nothing.
4. **Absence behaves like the default.** `f2` is absent on hundreds of
   thousands of rows, and `ECSEntityType.Render` is 0.
5. **Enum values verified.** Metadata defaults give `StreamingLayer` 0..10
   (`Count` 11), `ECSEntityType` 0..13 (`TypeCount` 14) and `ProxyEntityType`
   0..10; `ECSEntityType`'s last valid value is exactly `f2`'s maximum.

## Slot-7 group field 0

**Structure.** A 16-byte inline field (20 bytes in 60-byte groups) with 34
distinct values over 11,016 slice records -- a vocabulary. In its low u16:

- bits 0-5 are set in every non-zero field;
- bits 6 and 7 vary: the low byte is `0xFF`, `0x00`, `0xBF` or `0x3F`;
- byte 1 (bits 8-15) is **one-hot** whenever it is non-zero, corpus-wide,
  and the set bit is 8-14: category `k = 0..6`. The earlier "6-valued" figure
  was a slice artefact; `k = 6` occurs on two groups, and a range claim is
  settled by its rarest member.
- on the coordinate slice, byte 1 is zero exactly on the groups whose field 2
  is unset.

The fifth u16 restates the category: in the `w1 == 0x2024` family it carries
the bits `8 | 2^(k+4)` in every record, with the `k+1` and `k-1` controls at
exactly 0% (a subset test: a few records carry one extra bit).

**Reading: a `StreamingComponentType` mask.** Read at its declared ulong
width the enum is one-hot, and the low u16 decodes against it with no bit
above 14: bits 0-5 `Transform`..`MeshCollider`, 6 `SphereCollider`, 7
`CapsuleCollider`, and the one-hot category:

| k | bit | component |
| --- | --- | --- |
| 0 | 8 | `TerrainCollider` |
| 1 | 9 | `MultiCollider` |
| 2 | 10 | `HGDecalProjector` |
| 3 | 11 | `HLODGroup` |
| 4 | 12 | `HGVolumetricLocalFog` |
| 5 | 13 | `HGWaterRenderer` |
| 6 | 14 | `HGEnvironmentVolume` |

It explains the earlier puzzles: `k = 2` has the largest population and
extents about 2.5x the rest (decal projectors have large bounds); every
category occurs in almost every level (every level has decals, HLODs, fog
and water); `0xBF` occurs only with `k = 0` (a terrain collider carries no
sphere collider). This sat unsolved behind a one-byte enum-default read that
returned a tidy wrong value.

**Open conflict -- treat the component names above as under review.**
Recorded numbers point to field 0 being the group's descriptor-ID bitmask
(the 128-bit mask the native setup builds from the descriptor IDs):

- the current descriptor-ID census (`descriptor_mask_corpus`) counts IDs
  0-14 exactly as the field-0 census above counts bits 0-14 (IDs 0-5 in
  every non-zero field, ID 6 at the `0xFF` total, ID 7 at `0xFF` + `0xBF`,
  IDs 8-14 at the per-`k` totals), and the fifth-u16 bits `8 | 2^(k+4)` sit
  at IDs 67 and `68+k`, whose counts equal the per-`k` totals for k = 1..6
  (k = 0 also carries the families that leave the fifth u16 zero);
- the per-mask payload fit in [`world_chunk_transforms.md`](world_chunk_transforms.md)
  reproduces as the sum of the stored descriptor strides of the IDs set in
  the mask (each ID has one stride in the sampled descriptors): mask
  `0x100000200000` is IDs 21 and 44, strides 64 + 16 = 80 bytes per object;
  `0x0000082001ff` is IDs 0-8, 21, 27, summing to 328; the `0x2024`-family
  masks add IDs 67 and `68+k` and give 589, 1021 and 1597 exactly.

If field 0 is that mask, naming its bits by `StreamingComponentType` is the
numeric equality `descriptor_component_index_gate` refuses (IDs reach 44 and
beyond; the enum ends at bit 42), and map recovery reads matrices from
descriptors 18 or 27, not from bit 0. This is arithmetic on recorded values,
not a gated result: a gate should compare field 0 with each group's own
descriptor IDs before either reading is used.

## Group field 1 is a count

Dense small integers, never zero, with a long tail -- and exactly the paired
slot-6 ID-vector count in every group (`framing.py` checks it). It is not a
mask: "every bit <= 10" and "value below 2048" are the same test for small
integers, and its bit frequencies decay geometrically.

## Eliminated readings

- Group field 0 as a mask over `ECSEntityType` (14 bits, 14 values): subset
  of the chunk's slot-5 types 41.42%, beaten by the shifted-right control
  (45.37%) and matched by the other-chunk control (40.53%).
- `ECSExplicitEntityType` or `StreamingMode` for the category: 6 members
  against 7 values.
- A cross-slot join on `HGDecalProjector`: `k` co-occurs with slot-5
  `f2 = 10` at 27-66% across categories -- highest is not isolated.
- A seven-member sequential enum for `k`: the only one in the HyperGryph,
  Streaming and Beyond namespaces is `AudioDebugGizmosType`.
- `k` as a content kind: every category occurs in nearly every level, and
  terrain-versus-not separation stays within about +-9%.
- `k` as an ordered size class: median extent per category is 38.98, 28.45,
  97.74, 40.89, 38.05, 33.77, 31.51 -- not monotone (full corpus, seven
  values; the six-value slice run agreed). The shift in the fifth u16 is an
  encoding convenience, not an order.
- `StreamingComponentType` excluded from the kind codes because it read as
  "non-sequential, maximum 128": that was a one-byte read of a ulong enum.
- Group field 1 as a `StreamingLayer` mask (above).
- Group field 3 as a byte offset into a runtime region sized by root slot 4
  (divisible by 4, below `s4`, not in element order in a quarter of files):
  it is a uoffset to descriptors, and `s4` is itself a uoffset.
- Group field 4 as the constant 4: a uoffset to a wrapper.
- "The region is not in the file; all three root scalars size the loader's
  image": withdrawn with the size readings
  ([`world_chunks_families.md`](world_chunks_families.md)).

## Open

- Resolve the field-0 conflict above with a gate that tests field-0 bits
  against each group's own descriptor IDs (the obvious owner is
  `streaming/descriptor_mask_corpus.py`).
- Re-run the slot-5 kind-code tests per union tag.
- What a slot-7 group is, beyond its descriptors and bounds.

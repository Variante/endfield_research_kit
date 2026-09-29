# What the chunk slots mean

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** Slot 5's row fields 1 and 2 are anonymous stored
scalars; slot 7's field 0 is the descriptor-ID mask. The old enum proposal
for the row scalars remains a candidate, not a field name.

**Current framing** (`scripts/game_data/streaming/framing.py`): slot-7 group
field 3 is a forward uoffset to 8-byte descriptors and field 4 a forward
uoffset to a wrapper around a byte vector; see
[`world_chunk_unread_region.md`](world_chunk_unread_region.md). The enum-width
lesson below is recorded in the docstring of
`scripts/game_data/streaming/descriptor_component_index_gate.py`.

## Slot-5 row scalars: the old enum proposal

The authenticated full-corpus gate now censuses row fields 1 and 2 separately
for each root tag and records omitted fields separately. The three tags have
different row shapes, and Init names carry a `#N` segment that often differs
from field 1 ([`world_chunk_union_vectors.md`](world_chunk_union_vectors.md)).
The earlier narrow per-tag result reporting only one or two field-1 values per
tag did not cover the full range; the complete census is in the generated
Streaming corpus report.

The old `StreamingLayer` x `ECSEntityType` reading had three leads: the
pooled stored values fit those metadata enum ranges, the `(5, 7)` word pair
scaled with terrain-file counts better than comparison pairs, and omitted
field 2 was compatible with a zero default. The independent IV-count test
also rejected `ProxyEntityType` for this slot. These are useful search
constraints, but they did not check a native consumer of field 1 or field 2
and pooled the distinct tag members. Even the exact terrain-count relation
does not name either stored word. Keep both fields anonymous until a checked
per-tag native read or another independent typed join supplies the names.

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

**Reading: the group's descriptor-ID mask (exact, gated).** Field 0, read as
one little-endian 128-bit value, sets exactly the bits of that group's own
field-3 descriptor IDs -- the two-QWORD mask the selected native setup builds
from those IDs. `python -m scripts.game_data.streaming.descriptor_mask_corpus`
checks every group of every authenticated current Init file and publishes
`field0DescriptorIdMask`; no group disagrees. The regularities above are
therefore descriptor-ID regularities: bits 0-5 are IDs 0-5, present in every
group that stores them; the one-hot byte-1 bit is one of IDs 8-14; the fifth
u16 carries IDs 67 and `68+k`. The per-mask payload fit in
[`world_chunk_transforms.md`](world_chunk_transforms.md) is the sum of the set
IDs' stored strides (mask `0x100000200000` is IDs 21 and 44, strides 64 + 16 =
80 bytes per object). The bits name no component: descriptor IDs and
`StreamingComponentType` bit indices are separate namespaces
(`descriptor_component_index_gate`), and IDs reach 76 while the enum ends at
bit 42.

## Group field 1 is a count

Dense small integers, never zero, with a long tail -- and exactly the paired
slot-6 ID-vector count in every group (`framing.py` checks it). It is not a
mask: "every bit <= 10" and "value below 2048" are the same test for small
integers, and its bit frequencies decay geometrically.

## Eliminated readings

- Group field 0 as a `StreamingComponentType` mask (bits 0-5
  `Transform`..`MeshCollider`, 6 `SphereCollider`, 7 `CapsuleCollider`, one-hot
  8-14 `TerrainCollider`..`HGEnvironmentVolume`): the fit was numeric equality
  between enum bits and descriptor IDs. The field is the group's descriptor-ID
  mask, and the decal/terrain stories told about `k` do not follow from it.
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
- `StreamingComponentType` excluded from the old kind-code proposal because
  it read as "non-sequential, maximum 128": that was a one-byte read of a
  ulong enum and is withdrawn.
- Group field 1 as a `StreamingLayer` mask (above).
- Group field 3 as a byte offset into a runtime region sized by root slot 4
  (divisible by 4, below `s4`, not in element order in a quarter of files):
  it is a uoffset to descriptors, and `s4` is itself a uoffset.
- Group field 4 as the constant 4: a uoffset to a wrapper.
- "The region is not in the file; all three root scalars size the loader's
  image": withdrawn with the size readings
  ([`world_chunks_families.md`](world_chunks_families.md)).

## Open

- What each descriptor ID, and so each field-0 bit, names: the IDs are
  anonymous column positions until a native consumer or table labels one.
- Find a checked native consumer or another typed source for root row fields
  1 and 2, using the current per-tag corpus census as the source boundary.
- What a slot-7 group is, beyond its descriptors and bounds.

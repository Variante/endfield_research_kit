# `InitChunkData`: a FlatBuffers schema read from the bytes

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** The same container as terrain, but the payload inside is
FlatBuffers with no schema shipped. This file recovers the root and element tables
from the bytes alone, then joins slot 1 to the filename to find the world
placements -- the single most productive move in this family.

## Owners and neighbours

- Reader: `scripts/game_data/streaming/framing.py` (`parse_streaming_file`).
  Its module docstring carries the root layout, the retracted size and
  constant readings and the refused managed schemas; each `_parse_*`
  docstring carries its subgraph. Codec: `scripts/game_data/inverted_lz4.py`.
- Gate: `python -m scripts.game_data.streaming.corpus --input-set-sha256
  CURRENT_VFS_INPUT_SET_SHA256` rereads the whole block from the VFS ledger;
  counts go to `reports/animestudio/streaming_root_subgraphs_latest.{json,md}`.
- Siblings: [`world_chunks_families.md`](world_chunks_families.md) (the
  paired family, the Info index, where the native reader lives),
  [`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) (root
  slots 3/4/5), [`world_chunk_slots.md`](world_chunk_slots.md) (slot-5 kind
  codes, slot-7 field 0), [`world_chunk_unread_region.md`](world_chunk_unread_region.md)
  (slot-7 descriptors and native consumer, the coverage trap) and
  [`world_chunk_transforms.md`](world_chunk_transforms.md) (the matrix bulk).

## Container

An `InitChunkData` file is a u32 decoded length followed by one block of the
bit-inverted LZ4 variant that `TRET` terrain also uses
([`shared_containers.md`](shared_containers.md)); every decoded payload is a
valid FlatBuffer. The container is the only link between the two families:
no naming convention connects them. A DevOnly Global pair is raw and is
accepted only through the gate's named raw exception.

## The root: one layout in every file

Every Init and Streaming file has the same root vtable -- eight fields at
offsets `(4, 8, 16, 20, 24, 28, 32, 36)`, a 40-byte object -- across files
from a few hundred bytes to megabytes. One vtable over that size range is
itself the evidence that the typing describes one schema, not a sample.

| field | stored | current reading | tier |
| --- | --- | --- | --- |
| 0 | u32 | `47` in every file of both families -- a format version | exact |
| 1 | 8 inline bytes, two int32 | chunk origin `(x*128, y*128)` | exact filename join |
| 2 | uoffset to vector | Init: always empty, count word = last 4 bytes; Streaming: populated row vector ([`world_chunks_families.md`](world_chunks_families.md)) | exact framing |
| 3 | uoffset to u32 vector | object IDs, parallel to 5 | [`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) |
| 4 | uoffset to byte vector | row tag 1/2/3, parallel to 5 | same |
| 5 | uoffset to table vector | rows whose vtable shape the tag fixes | same |
| 6 | uoffset to table vector | one-field wrappers, each to a u32 ID vector | [`world_chunk_unread_region.md`](world_chunk_unread_region.md) |
| 7 | uoffset to table vector | five-field groups (object 56 or 60), parallel to 6 | below |

The first pass typed fields 2-4 as scalars from their vtable gaps; each is a
uoffset (see Eliminated readings). Nothing above comes from a schema.

## Field 1 is the chunk origin, and 128 is the chunk size

Read as two int32, field 1 equals `(x*128, y*128)` for the coordinates in
`InitChunkData_<x>_<y>_<z>_<w>.bytes` in every numeric-name file of both
families, with no mismatch. The controls fail as they should: swapping the
axes matches only the `x == y` files, and scale 64 or 256 matches only the
origin chunks. Distinct coordinate pairs map one-to-one to distinct values.
Global files store `(INT32_MAX, INT32_MIN)`.

Under the refused `FBDynamicSceneChunkData` reading this field was
`StreamingVersion` with values like `0xFFFFFF80` -- which is `-128`, i.e.
`x*128` for `x = -1`. A join to the filename settled in one test what reading
the value alone could not.

## Slot-7 groups: what each field holds

| field | width | reading | tier |
| --- | --- | --- | --- |
| 0 | 16 (20 in 60-byte groups) inline | category bits; see [`world_chunk_slots.md`](world_chunk_slots.md) | structural; naming open |
| 1 | 4 | count, equal to the paired slot-6 ID-vector count | exact |
| 2 | 24 inline | centre and extents, six float32 | direct byte evidence, below |
| 3 | 4 | uoffset to 8-byte `(u16 id, u16 stride, u32 0)` descriptors | exact, native-consumed |
| 4 | 4 | uoffset (stored `4`) to a wrapper around a byte vector of `count * sum(strides)` bytes | exact, native-consumed |

Fields 3 and 4 are framed in `framing._parse_paired_group_subgraph`; their
native consumer and the descriptor-21 name join are in
[`world_chunk_unread_region.md`](world_chunk_unread_region.md). Most Init
files and every Streaming file have no groups.

### Field 2 is a centre and non-negative extents

Measured on a single-digit-coordinate slice of Init files:

- **Set or unset as a whole.** The 24 bytes are wholly zero or wholly
  populated, never mixed; the unset groups are exactly those whose field-0
  byte 1 is zero.
- **First triple = world position `(x, height, z)`.** `f0` and `f2` fall in
  the group's own chunk box 73.96% of the time against 1.28% for a
  neighbour-chunk control; the `(f0, f1)` reading scores 6.25%. By sign, the
  middle axis is negative 4.9% of the time against 61.7% and 48.2% for the
  other two -- a height stays positive, a horizontal coordinate does not.
- **Second triple = extents.** It is never negative (0 of 21,336
  components, range 0..687). It is not a second position (2.18% own box
  against a 2.26% control), not a unit quaternion and not a scale.
  Centre plus extents stays in the chunk 32.94% of the time, as an AABB's far
  corner does.
- **Layout match, no use site.** `FBDynamicSceneBounds` (`Center`, `Extents`,
  two `Vector3`) has exactly this layout and was found by shape. No
  generated table that could contain the group uses it: the only table with
  a Bounds field is `FBDynamicSceneSludgeComp` (27 fields), and no generated
  five-field table matches the widths `[16|20, 4, 24, 4, 4]`. The name
  describes the layout; it does not locate a managed reader, and none exists.

### Slots 5 and 6 are not spatial

Every float-shaped field in slot-5 and slot-6 elements is a denormal (small
integers read as float); their early "box hits" (28.9% own against 28.8%
neighbour) were that artefact. Slot 5 is a genuine table vector -- 0.10
distinct vtable addresses per element, against 0.36 and 0.47 for slots 6 and
7 -- and its 16/20-byte field is all zero in every read; it shares no value
with slot 7's field 0 despite the matching width.

## Managed schema: none matches

IL2CPP carries 73 generated FlatBuffers types, 65 of them in
`Beyond.Gameplay.Core.DynamicScene`. None is this root:

- `FBDynamicSceneChunkData` (`Version, StreamingVersion, UniqueId, Grids[],
  TotalStr[]`) fails twice: its `Grids` and `TotalStr` readings give
  identical length distributions and no `Grids` element resolves to a table;
  and no type with a `GetRootAs` accessor has eight fields (the six such types
  have 5, 61, 2, 3, 5 and 7). A schema that fits the subject matter is not
  thereby the schema of the file.
- `MapManager+LoaderChunkStaticData`'s three collections (`grids`, `tiers`,
  `mists`) against root slots 5/6/7 is refused: the tier and mist config
  widths do not match the group widths, slots 6 and 7 have equal counts in
  every file, and the resolved types make `tiers` and `mists` dictionaries
  while `grids` is a list. Its chunk rectangles are `Vector2`, and
  `LoaderLevelData` splits chunks into low/medium/high lists -- a LOD tiering
  of chunks, not of anything inside them.
- `InitChunkData_`, `ChunkData_` and `_0_0.bytes` do not occur in
  `global-metadata.dat` or `GameAssembly.dll` (`InitChunkData` only as the
  method `_InitChunkDataPool`). The paths are built natively; see
  [`world_chunks_families.md`](world_chunks_families.md).

The module docstring of `framing.py` records these refusals with their tests.

## Eliminated readings

One line each; the reasoning is in the owning docstring or above.

- Root = `FBDynamicSceneChunkData`, or any declared root type (no eight-field
  root exists).
- Root fields 2, 3, 4 as payload or allocation sizes (`framing.py` module
  docstring: uoffsets satisfy the size formulas by position).
- Group field 2 as a min/max box: `min <= max` holds 38.52%, below its own
  reversed control (43.22%) and level with a shuffled pairing (37.69%).
- Group field 2 as `FBDynamicSceneVisibilityInfo`: its last component is an
  Int32 `Importance`, but `f5` is a normal float in 7,112 of 7,112 records.
- Group as `FBDynamicSceneModel`: five fields, but widths
  `[16, 36, 12, 8, 24]`.
- Group field 0 as `FBDynamicSceneGuid` (16 bytes): 34 distinct values over
  11,016 records is a vocabulary, not identifiers.
- Group field 3 as an index into a sibling vector: in range of slot 5 only
  4.37% and of slots 6/7 never; field 1's 90% "in range" was vacuous for
  values 1, 2 and 4.
- Slot 6 as an offset table into slot 5: "non-decreasing" and
  "non-increasing" both scored 100% because the stored word is the constant
  uoffset `4` (`framing._parse_paired_group_subgraph`).
- Slot 7's categories as an ordered size class; see
  [`world_chunk_slots.md`](world_chunk_slots.md).
- The loader's grids/tiers/mists as root slots 5/6/7 (above).

## Open

- What a slot-7 group is, and what names its field-0 bits carry
  ([`world_chunk_slots.md`](world_chunk_slots.md)).
- Field names for any root slot: no schema ships, so they must come from the
  native reader ([`world_chunks_families.md`](world_chunks_families.md)).

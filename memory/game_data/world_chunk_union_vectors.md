# The root retyped, and the union vector it exposed

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** One mistyped slot propagated into several published
readings; correcting it re-typed the root, exposed a union vector, and closed the
name-to-id join at 100%. Check it before trusting any per-slot census in
[`world_chunk_slots.md`](world_chunk_slots.md) or
[`world_chunk_unread_region.md`](world_chunk_unread_region.md).

**Current correction:** slot-7 field 3 points to 8-byte descriptors, and
field 4 reaches a wrapper around a byte vector; see
[`world_chunk_unread_region.md`](world_chunk_unread_region.md). The reader for
everything here is `scripts/game_data/streaming/framing.py`
(`_parse_parallel_root_subgraph`), whose docstring records the ID/name rule
and the tag-to-shape join; the retyping is in its module docstring.
Its current-corpus gate records the per-tag field-1/2 words and omissions,
Init name suffixes, and empty Streaming names without assigning enum labels.

## The root retyped: slots 2-7 are all vectors

Slot 3 held 3,238,372 in one large file; taken as a uoffset it landed on a
word equal to slot 5's element count. Dereferencing every remaining "scalar":

| slot | resolves to | evidence |
| --- | --- | --- |
| 2 | a vector, always empty in Init | target is `len - 4`, count 0 |
| 3 | a vector of u32 object IDs | length equals slot 5's in every file |
| 4 | a **byte** vector of values 1, 2, 3 | storage `4 + n`; length equals slots 3 and 5 |
| 5 | a vector of tables | -- |

Slots 6 and 7 are the paired group vectors. Slot 4's "packed byte quads"
(`0x02020202`) were a byte vector read four bytes at a time; 38% of its
words failing to resolve as offsets was the tell. Slot 3 fails the
dereference test cleanly (0 offsets), so its ID reading survives the test
that broke `s2`, `s3`, group field 3 and two row fields. `s3` had survived
because it was only ever tested as a number, never dereferenced.

## Slots 3/4/5 are a union vector

A `ubyte` vector of three small values running index-parallel to a table
vector is what a FlatBuffers union vector (`field: [SomeUnion]`) serializes
to. That is falsifiable -- the tag must determine the element layout -- and
over 12,417 rows in 1,200 Init and Streaming files it does:

| tag | vtable slot count | distinct layouts |
| --- | --- | --- |
| 1 | 5, always | 2 |
| 2 | 6, always | 6 |
| 3 | 4, always | 4 |

No layout appears under two tags; the object-size variants inside a tag are
ordinary default omission. The maintained gate publishes the tag-to-shape
join at exact index over the current corpus. The reading is structural: no
managed union type is identified.
The paired Streaming rows have the same ordered IDs and tags but empty
field-0 byte ranges; only Init rows carry the names below.

**Demoted to structural-only by this:** the earlier slot-5 field-by-field
dereference sweep and nested-table follow, which pooled the three members
under one field index -- "field 3" is a different field in a 4-, 5- and
6-slot table. The old pooled kind-code/enum reading is not a field name;
[`world_chunk_slots.md`](world_chunk_slots.md) keeps the candidate and its
refused shortcuts. The current gate reports fields 1 and 2 per tag.

## Per-tag rows

Each width-4 field tested as a uoffset against a same-buffer random-position
control, over 900 Init and Streaming files:

| | field 0 | field 1 | field 2 | field 3 | field 4 | field 5 |
| --- | --- | --- | --- | --- | --- | --- |
| tag 1 | Init name, Streaming empty | anonymous scalar or absent | mostly absent scalar | 8-byte component mask | 11 distinct | -- |
| tag 2 | Init name, Streaming empty | anonymous scalar or absent | anonymous scalar or absent | uoffset to table (100% vs 3.35%) | 16 bytes, always zero | empty vector |
| tag 3 | Init name, Streaming empty | anonymous scalar or absent | anonymous scalar or absent | uoffset to table (100% vs 3.87%) | -- | -- |

- **Init field 0 is a name; Streaming field 0 is empty.** The earlier string
  probe required `0 < count` and discarded the empty paired Streaming
  entries. Every Init name parses as `<base>#<N>_<HEX>`. The maintained
  reader frames it as a length-prefixed byte range followed by a zero and
  keeps "string" and "byte vector" as equal candidates. A table-only test had
  read it as an "id-like scalar" at 3x control -- a real uoffset looks like
  100% against 3%.
- **The Init names identify the members.** Tag 1: reflection probes, lights,
  `Env_*`; tag 2: `New Game Object`, `MergedCollider_*`; tag 3: `AudioBox_*`,
  `AudioEmitter_<n>`, `SurfaceTypeData_*`. The `#N` segment is independent of
  row field 1: the complete authenticated census contains mismatches under
  every tag, including `New Game Object#0` with field 1 equal to 5. The old
  claim that they tracked exactly came from a narrow slice and is retracted.
- **Tag 2 field 4 is sixteen always-zero bytes** in every sampled Init and
  Streaming row: reserved or default space, not a transform.
- **Field 3 of tags 2 and 3 reaches a nested table** whose fields 3/4/5 are
  equal-count vectors of u32 keys, u8 markers and uoffsets -- a second
  keyed, marker-selected directory. Its markers (2, 13, 15, 17) are framed
  by the `marker*` modules beside `framing.py` and documented in
  [`install_and_vfs.md`](install_and_vfs.md); the marker association is not
  a proven union registry.
- **Row field 5 (six-slot rows) is an empty counted vector** in the current
  corpus; its element width is unresolved.

### The ID join is exact

Each Init name's hex suffix is the parallel slot-3 ID masked to 27 bits.
The 28-bit candidate fails only on bit 27; the 27-bit mask matches every
authenticated Init row in the current gate, at the same vector index. The
maintained reader fails on a suffix mismatch or a nonempty paired Streaming
name. Counts and source hashes live in the generated corpus report. With
the tag and Init name, each row has a type member, an identity and a label.
The same ID space appears in the slot-6 group ID vectors, which the
descriptor-21 name join uses
([`world_chunk_unread_region.md`](world_chunk_unread_region.md)).

### Tag 1 field 3 is a `StreamingComponentType` mask

Censused by byte position over 4,386 rows: byte 0 is `0x01`, bytes 1-4 are
bit-like and byte 5 onward is always zero, so the field is 8 bytes (the
12-byte variant's tail is object padding). There are 8 combinations, and the
name prefix determines the combination every time. Read as a little-endian
u64 over the IL2CPP enum:

| bytes | decodes to | names |
| --- | --- | --- |
| `01 00 02 02 00` | `Transform \| Light \| HGAdditionalLightData` | spot, point, linear lights |
| `01 00 01 00 00` | `Transform \| ReflectionProbe` | reflection probes |
| `01 40 00 00 00` | `Transform \| HGEnvironmentVolume` | `Env_*`, Global Env |
| `01 80 00 00 00` | `Transform \| Volume` | Global Volume |
| `01 00 02 22 00` | lights `\| LensFlareComponentSRP` | Directional Light |
| `01 00 00 00 01` | `Transform \| HGWaterGlobalConfig` | Water |
| `01 00 08 00 00` | `Transform \| HGTerrain` | TerrainRoot |
| `01 00 00 00 02` | `Transform \| HGWindMotor` | Wind |

Eight of eight decode with no unknown bit, and the enum (metadata) and the
names (file) are independent sources. The sharpest case is the directional
light, one bit away from the other lights: a light with a lens flare. This
mask has independent name evidence; the slot-7 group field-0 "mask" does
not ([`world_chunk_slots.md`](world_chunk_slots.md) records an open conflict
there).

## Tag-3 emitter numbers are not Wwise IDs

Tag-3 names embed u32 numbers (`AudioEmitter_4192702263`, 306 distinct over
1,500 files in four emitter kinds). Scanned against the decoded
AKPK/HIRC audit of the audio pipeline, a positive control of three known
source IDs is found 3 of 3, the 306 emitter numbers 0 of 306, and 306 random
numbers from the same range 0 of 306. They are neither source nor media IDs,
nor the row's own ID (0% against the ID and its 27-bit mask), and 22 of them
recur across level directories -- an authored identifier shared between
places. A raw byte scan of the audio packages is uninformative: they start
with `:)xD`, not `AKPK`, and that scan never reached a bank.

## Eliminated readings

- Root slots 2, 3, 4 as runtime sizes (`framing.py` module docstring).
- Slot 4 as packed byte quads (a byte vector read at the wrong width).
- Slot-7 field 3 as an alternating `(code, 0)` list: 952 words with 4
  distinct values, half zero, read as 4-byte elements of what are 8-byte
  descriptors.
- Row field 0 as an ID scalar (it is a name reference).
- Tag 2 field 4 as a transform (always zero).
- The Init/Streaming row differences in fields 0, 3 and 5 as per-file
  quantities: all three are uoffsets (field 5 to an empty vector), which
  differ whenever two files lay the same object out differently. The
  invariant fields 1 and 2 are the scalars.
- Every "distinct value" census that counted uoffsets as data: large
  distinct counts with no structure were addresses.
- The emitter numbers as Wwise IDs into the shipped banks.

## Open

- A named native consumer for row fields 1 and 2, beyond their checked
  per-tag stored-word distributions ([`world_chunk_slots.md`](world_chunk_slots.md)).
- What the emitter numbers identify.
- The nested marker directory's record extents and runtime selection
  ([`install_and_vfs.md`](install_and_vfs.md)).

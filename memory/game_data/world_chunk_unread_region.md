# The former slot-4 hypothesis and the gap the walker could not follow

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** This is the history of the unread-byte investigation,
including retractions and coverage figures that depended on the walk. Read
[`world_chunk_union_vectors.md`](world_chunk_union_vectors.md) before using any
old claim about a runtime "slot-4 region": root slot 4 is a byte vector of
row tags, and
slot-7 field 3 is a forward FlatBuffers offset rather than an offset into that
hypothetical region. The large unread runs discussed below are a separate
remaining gap.

## Owners

| structure | module (docstring carries the detail) | command / report |
| --- | --- | --- |
| group framing, descriptor vector, wrapped byte vector | `streaming/framing.py` `_parse_paired_group_subgraph` | `python -m scripts.game_data.streaming.corpus` |
| descriptor-21 name prefix | `streaming/descriptor_names.py`, `descriptor_name_corpus.py` | `reports/chunk_data/descriptor_name_corpus_latest.json` |
| native first-root consumer | `streaming/native.py` + `contracts/streaming_field2_native.json` | validated by every corpus run |
| 128-bit descriptor mask | `streaming/descriptor_mask_native.py`, `descriptor_mask_corpus.py` + `contracts/streaming_descriptor_mask_native.json` | `reports/chunk_data/descriptor_mask_corpus_latest.json` |
| ID-versus-enum-index counterexample | `streaming/descriptor_component_index_gate.py` | `reports/chunk_data/descriptor_component_index_boundary.json` |

All module paths are under `scripts/game_data/`. Commands and flags are in
[`../../scripts/README.md`](../../scripts/README.md).

## Current framing of the slot-7 references

Each non-empty Init group's field 3 reaches a counted vector of **8-byte
descriptors** -- a `u16` anonymous id, a `u16` stride-shaped value and a zero
`u32`. Field 4 stores the short forward offset `4`; following it reaches a
one-field wrapper whose field 0 reaches a counted byte vector, and

```
wrapped byte-vector length = group field-1 count * sum(descriptor u16 strides)
```

holds in every group. The byte reader establishes **exact anonymous framing**;
the selected native consumer below independently reads the same vectors. The
check is tested, not assumed: raising one stride by one makes a real file fail
the length check, and changing a field-4 offset from `4` to `8` makes the
target fail table framing. A path-stratified probe of paired files, large
ones included, rechecked the equation against the maintained reader; the
Streaming twins have no groups, so no non-empty Streaming group shape exists
to test.

The old field-3 reading as an alternating `(code, 0)` list used 4-byte
elements and stopped halfway through each descriptor; the old field-4 reading
as a scalar never followed the relative offset.

## Descriptor-major layout and the descriptor-21 name prefix

The length equation permits both descriptor-major storage (one
`count * stride` region per descriptor, in descriptor order, each split into
`count` slots) and row-major storage. Descriptor **21** decides it: it has
stride **64**, occurs once per populated group, and read descriptor-major
each slot is a printable NUL-terminated name with zero padding
(`New Game Object#0_3B09708`, `MergedCollider_-4_-2_0_0#0_5DC8105`). Pairing
slot `i` with the group's slot-6 ID `i` reproduces the same-file root pair
(field-3 ID, field-5 row name). On a four-file bounded sample the
descriptor-major reading passed 239 of 239 slots and 239 of 239 ID pairs;
row-major failed 224 slot predicates and matched 9 pairs.

The complete-corpus gate rereads every authenticated Init logical file from
its physical VFS chunk and checks its ledger MD5 before framing. Every
descriptor-21 slot joins its group ID to the same-file root ID and to the
**first 63 bytes** of the root name. Long names lose their suffix in the
slot, sometimes including the `#` token, so the four-file predicate that
required `#` and full-name equality rejected valid prefixes. Some root pairs
have no descriptor-21 slot; the groups do not exhaust the root catalogue.

This establishes a duplicated **name prefix** under the same ID -- not every
complete name, not a component label for other IDs, and not runtime
ownership. DynamicStreaming's auxiliary pairs follow the same 63-byte rule
([`world_dynamic_streaming.md`](world_dynamic_streaming.md)).

## The selected native consumer

The reviewed `streaming_field2_native.json` contract closes the **static
consumer path** from the first paired root, whose path formatter selects
`InitChunkData`. On the branch where both paired roots are present and the
group runtime state is not yet populated, the selected UnityPlayer body
follows root slot 7 to each group, group field 3 to the descriptor vector,
group field 4 through its wrapper to the byte vector, and root slot 6's
wrapper to the ID count, and passes all three counts and pointers to one
consumer. Body and accessor bytes validate against the explicitly selected
`GameAssembly.dll`, metadata and `UnityPlayer.dll`.

The consumer sign-extends **both** descriptor words: the first selects an
anonymous runtime field, the second times the ID count is the number of bytes
copied before the position advances. It compares each proposed end and the
final position with the blob length, and **both mismatch branches log and
continue** -- evidence for descriptor-major order and the count-times-stride
extent, not a safe validator. The maintained reader is stricter and rejects
a mismatch. Current IDs and strides are non-negative, so signed and unsigned
readings agree; a word with its high bit set would need review.

It does **not** name the other descriptor IDs, prove an actual run through
this branch, or bind the runtime root to one authenticated VFS file.

## Component-name shortcuts, refused

- **Binding names.** `PropertySerializeId.GetComponentIndexFromType` returns
  the bit index of an input mask; the descriptor consumer selects its column
  through a separate anonymous bit-prefix helper, whose literal-call census
  finds three callers (the selected copy loop, its archetype setup, one other
  generic copy loop). `FlatBufferConvertContextV2.get_componentScopeEntityName_Injected`
  reads a NUL-terminated pointer at context `+0x88`, but the selected IL2CPP
  type has no getter method for it and no checked loop carries descriptor 21
  there. Matching strings and a binding name do not make descriptor 21 a
  named runtime component. The contract's `groupComponentNameCandidate`
  block pins this; indirect or inlined column selection is not excluded.
- **Numeric equality.** `StreamingComponentType` is a one-hot ulong ending at
  bit 42; an authenticated Init file stores descriptor ID **44**. The selected
  setup divides the signed first word by 64 to pick one of two QWORDs and sets
  the remainder bit, so ID 44 is bit 44 of an **anonymous 128-bit mask**.
  Descriptor IDs and enum bit indices are distinct namespaces; an ID inside
  the enum's range is not labelled by equality either. A separate lookup
  table is not excluded, and the setup has no rejection for negative or
  >= 128 IDs. The mask corpus gate finds every current ID inside the mask --
  a current-input observation, not a rule.

The next direct witness is a checked reader that takes a descriptor-selected
column into a named converter or field, or a runtime trace joining one
concrete Init file to this consumer.

## Carrying an older gate forward

An older complete Streaming root-subgraph gate ran against an earlier audit
fingerprint. Its structural observations were carried to a later audit only
through a byte-identity transfer: every block-15 logical file reread and
checked against its ledger MD5, the complete gate's sorted identity digest
reproduced, and the reader bytes shown equal to the recorded parser. The
transfer is conditional on those identical bytes; the old fingerprint stays
old, and its other native claims were not transferred.

## The named unread run

`blackbox02_dg001/InitChunkData_-1_0_0_0.bytes` has one group with count 33,
descriptors `(21, 64, 0)` and `(44, 16, 0)` and a 2,640-byte blob, exactly
`33 * (64 + 16)`. **The native join does not resolve this file's historical
large unread run** (444,381 bytes starting at 2,601,975, holding transform
matrices -- [`world_chunk_transforms.md`](world_chunk_transforms.md)). The
reader certifies the small wrapper and blob but no range inside that run.
Its `decodedCertifiedRanges` separate bytes it has framed from bytes merely
present; the run needs its own references or structure before it gets an
extent or a meaning.

## The walk-based coverage trap

Every figure in this section came from a deleted structural walker (the
`scratch/` prototype is gone). It predates the field-4 wrapper reading and
accepted only vectors of tables, offsets or strings, so it never marked the
byte vectors behind group field-4 wrappers. Each figure measures that
walker, not the file. Recompute coverage from the reader's
`decodedCertifiedRanges` (the `parse_streaming_file` docstring says why).

Eliminated or narrowed readings, in the order they fell:

- **"The records are not here to decode."** Inferred from two guessed bases
  failing; most files had ample free room.
- **"98% unaccounted."** That walk followed only root slots 5-7 (1.65%). A
  full recursive walk of tables, table vectors and strings reached 54.91%.
  A floor was reported as the value, and a prediction was made to protect it.
- **"The rest is walker capability."** Accepting any in-bounds offset vector
  moved coverage only from 54.91% to 56.30%.
- **"Mostly padding."** Counting runs rather than bytes: 99.2% of unreached
  bytes sit in runs of 256 bytes or more.
- **"Those regions are addressed."** A pointer scan found hits into every
  run, but random windows of the same size drew 114.3 hits per run against
  the real runs' 52.3; it counted arbitrary words (the root's own `y*128`
  among them) landing in a range. It was published without a control.
- **A count over a fixed stride.** No run satisfies `4 + count*W == length`
  for W in 4-48.
- **"Integer-and-zero dominated, not geometry."** The float census iterated
  phases relative to unaligned run starts. In absolute coordinates the
  exponent bytes `0x3D`-`0x42` sit at `mod 4 == 3` 26-42x more than elsewhere
  and the region is about 24% float-plausible, against 20.40% for reached
  bytes. The byte histogram disagreeing with the word classifier was the
  signal.
- **"The region tracks `GrassGrid`."** Against raw unreached bytes GrassGrid
  scored +0.479, file size +0.978; against the unreached *fraction* GrassGrid
  +0.234 and `SurfaceTypeData` -0.768. Mostly the size confound.
- **"44% unreached is a property of the family."** In a 400-file sample the
  seven files of 1 MB or more held 90.41% of unreached bytes and the 382
  files under 100 KB held 3.73%.

What survives as description (not identification) of the unreached bytes:
zeros interleaved in runs of one and three words rather than long blocks; no
record stride (every stride from 2 to 32 words predicts zero-ness within
58.97-59.63% against a 56.3% baseline); byte entropy 3.925 bits, so neither
compressed nor encrypted; aligned floats small (93.85% in 0..128, 72% with
`|f| <= 1`) and not world coordinates (own-box 35.53% against a 31.00%
control). In the largest file, `61.71` recurs thousands of times across a
2x2 chunk block with no populated groups; it is the Y translation of the
matrices. Large files leave group bounds unset and keep their content
outside the walked tables; small files are the reverse, which is why no
join from the framed tables to the region worked.

*Four successive characterisations of this region fell to the next
measurement. The one that should not have happened was a positive result
published without the control applied everywhere else.*

## Open

- A checked mapping from a descriptor ID to a named component consumer, then
  a concrete runtime root/file receipt.
- An extent and meaning for the named unread run and any other bytes outside
  `decodedCertifiedRanges`.
- A corpus coverage figure recomputed from `decodedCertifiedRanges`.

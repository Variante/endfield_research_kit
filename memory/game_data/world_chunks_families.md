# The second family, and the index that names both

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** `StreamingChunkData` shares the schema recovered in
[`world_chunks_schema.md`](world_chunks_schema.md) and carries none of the
placements. Having the pair is what splits the slot fields into invariant and
varying, so the slot files depend on this one. It also records the full-corpus
gate and where the native reader actually lives.

## Owners

- `scripts/game_data/streaming/corpus.py` -- the block inventory, the raw
  exception, the Info catalog join (`_join_info_catalog`) and the ordered
  pair witnesses (`_join_root_witnesses`); `pairs.py` binds a pair row to its
  serialized ordinal. Run `python -m scripts.game_data.streaming.corpus
  --input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256`; current counts are in
  `reports/animestudio/streaming_root_subgraphs_latest.{json,md}`.
- `scripts/game_data/streaming/framing.py` -- `_parse_info_inner` (the Info
  graph) and `_parse_field2_terminal_subgraph` (Streaming's populated field 2).
- `scripts/game_data/streaming/native.py` and
  `scripts/game_data/contracts/streaming_field2_native.json` -- where the
  native reader lives and what its selected consumers read.

## The block inventory is closed

Each level's `Data/Streaming/PC/<level>/Streaming/` directory holds:

| file | per level |
| --- | --- |
| `InitChunkData_<x>_<y>_<z>_<w>.bytes` and `InitChunkData_Global_<a>_<b>.bytes` | one per chunk |
| `StreamingChunkData_...` with the same suffixes | paired 1:1 with the Init files |
| `StreamingChunkInfo.bytes` | exactly one -- the index |

Streaming the block with a filter that excludes these names returns nothing,
so the gate covers all of it. Every file frames. The DevOnly Global pair,
first recorded as two codec failures, is raw FlatBuffer with the standard
root; the gate admits it only through `RAW_DATA_EXCEPTIONS`. `DevOnly` is
also the one level whose Info file keeps a three-field legacy root.

## `StreamingChunkInfo`: the per-level index

- **A different container in the same directory.** It is a plain,
  uncompressed FlatBuffer; the neighbours' codec decodes none of them.
  Trying the neighbour's codec first is what established that cheaply.
- **Framing** (`framing._parse_info_inner`, exact to EOF): a four-field root
  whose field 3 is the row vector; each row holds two inline int32 -- the raw
  `(x, y)` grid indices, *not* scaled by 128 like the chunk origin -- and a
  uoffset, stored as `4` and once misread as a constant, to a counted vector
  of 8-byte elements.
- **The join is exact.** Each (row, element) pair's four words spell the
  same-directory `StreamingChunkData_<x>_<y>_<z>_<w>.bytes` under the
  identity permutation, and `(INT32_MIN, INT32_MIN)` rows spell
  `StreamingChunkData_Global_<a>_<b>.bytes`. The gate tries all 24
  permutations over complete filename multisets and publishes a relation only
  when exactly one reproduces every file; the current corpus has one. The
  index therefore holds one row per `(x, y)` column and one element per file.
- **The earlier set test was sound and incomplete.** Comparing the *sets* of
  `(x, y)` pairs matched every standard level, and its cross-level control
  fired once -- on levels that genuinely share an instanced chunk layout (a
  few coordinate sets repeat across many levels). It collapsed the `z`
  variants: some levels, `map01` and `map02` among them, hold many more files
  than columns. Set equality proves set equality, nothing about multiplicity.
- **The fourth filename coordinate is not a LOD.** It is 0 almost everywhere
  and takes large values (such as 587717614) only in `map02`, despite the log
  format `Missing chunk file at %d,%d,%d, lod %d`. A log string names the
  engine's addressing, not necessarily the filename's.
- **Two spellings of "global".** The Info row uses `(INT32_MIN, INT32_MIN)`;
  every Global chunk file's own origin field stores `(INT32_MAX, INT32_MIN)`.
  A join on origin values instead of filenames would score zero and read as a
  refutation of a correct reading.

## `StreamingChunkData`: same root, different population

- **One schema.** Same root layout, field 0 = `47`, and field 1 = the chunk
  origin -- a prediction made from the Init family and tested on a family
  that had no part in fitting it.
- **Same rows.** In every current pair the ordered root field-3 ID vector and
  field-4 tag vector are identical (`_join_root_witnesses`), so the two files
  index the same objects. Row field-0 bytes differ in every pair; the gate
  records that separately and does not use it as an identity key.
- **The groups are Init-only.** No Streaming file has any slot-7 group,
  corpus-wide. The "streaming" file is not the one that holds the placement
  groups -- the naming intuition is backwards.
- **Its field 2 is populated.** Init's field 2 is always an empty vector at
  EOF; Streaming's is a terminal vector of six-field rows framed exactly to
  EOF. The selected native consumer loads fields 0-2 as 32-bit scalars, field
  3 as two int32, field 4 as six float32, and each field-5 element as a
  32-bit hash-table key (`native.py`; its diagnostic string is
  `Grid with layer %u / sceneStateId %d / pos (%d, %d) already exist`).
  Names, key namespace and meaning are unresolved.

### The retracted size formulas

`s2 == len - root - 20` and `s3 == len - root - 28 - 4*len(slot 5)` hold in
every Init file and in no Streaming file, and `len - s2` takes only two
values, tied to the root offset. They were published as payload sizes, then
as sizes of a runtime image the loader builds. Both are wrong: fields 2 and 3
are uoffsets, Init's empty field-2 vector ends the file, and field 3's vector
sits a fixed distance before it; Streaming's populated field 2 breaks the
arithmetic. A shared schema did not guarantee a shared relation, and an
identity over every file said nothing about the field's type
(`framing.py` module docstring).

## Where the native reader lives

- **Not in the virtualised modules.** `EndfieldBase.dll` and `HGP.dll` are
  mostly `.tvm0` sections at entropy near 7.6 and contain no chunk strings.
  An earlier "static recovery cannot reach the reader" conclusion came from
  measuring `EndfieldBase.dll` because it looked like the right module.
- **In the unpacked `UnityPlayer.dll`.** A heavily modified player with
  HyperGryph symbols, `FlatBufferConvertContext`, intact `HG_ALWAYS_ASSERT`
  expressions and the path formats `{0}/{1}{2}ChunkData_{3}_{4}_{5}_{6}.bytes`
  and `{0}/{1}{2}ChunkData_Global_{3}_{4}.bytes` beside the literals `Init`
  and `Streaming`. No complete `InitChunkData_` literal exists anywhere, which
  is why the managed-metadata search found nothing: a negative string search
  bounds where a literal is, not where the behaviour is.
- **Managed vocabulary:** `UnityEngine.HyperGryph.Streaming` (35 types) with
  the enums `StreamingLayer`, `ProxyEntityType`, `StreamingComponentType`
  (a ulong bitmask), `StreamingMode` and `StreamingStatus`.
- **Assert vocabulary.** `fbMonoEntityData->componentDataList()->Get(0)->type()
  == kComponentTypeTransform` is literal FlatBuffers accessor code, and three
  bind functions (`BindMonoComponentConvertFuncFromScript`,
  `BindProxyEntityConvertFuncFromScript`, `BindECSEntityConvertFuncFromScript`)
  name three entity categories. Three categories against three root vectors
  is the count-match shape already refused twice here, so it stays a lead.
- **No schema ships.** No `*.fbs`, `*.bfbs`, `*.schema` or `*.proto` exists in
  the `table`, `json-data`, `extend-data` or `initial-extend-data` blocks, so
  field names cannot come from shipped data.

The pinned consumers and their evidence boundary are in
`streaming_field2_native.json`, validated by `native.py`; the native
entry is `StreamingSceneV2::Create_Injected`, whose first scene read formats
the Info path. A concrete runtime root-to-file receipt is not closed.

## Eliminated readings

- `ProxyEntityType` as the slot-5 kind code. Its `IrradianceVolume` code
  had to match each level's IV count from the `iv` block: 0 of 28 codes do,
  on 0 of 88 levels, while a positive control (some code matching the IV
  count) fires on 17 of 88. Slot 5 has thousands of entries per level against
  about one IV -- it is not a placement list. The enum's names do occur as
  object names ([`world_chunk_transforms.md`](world_chunk_transforms.md)).
- `componentDataList` as slot 5: element 0 carries 15 distinct kind codes,
  not one fixed Transform type.
- The fourth filename coordinate as a LOD index (above).
- The Info row's second field as the constant 4 (a uoffset).
- The DevOnly Global pair as corrupt or undecodable (raw, admitted by name).
- `EndfieldBase.dll` or `HGP.dll` as the chunk reader.
- Root fields 2 and 3 as sizes (above).

## Open

- The runtime root and path-to-authenticated-file join for one concrete read.
- Names and meanings of Streaming's field-2 row fields and key namespace.
- What the Init/Streaming split itself encodes beyond "groups are Init-only".

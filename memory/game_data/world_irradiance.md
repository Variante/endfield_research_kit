# IrradianceVolume: exact indexed ranges, open record meaning

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** [`irradiance_volume.py`](../../scripts/game_data/irradiance_volume.py)
frames the `index.bytes` filename tables, the index-directed payload ranges
and the `regionIv_room_*` files;
[`irradiance_volume_corpus.py`](../../scripts/game_data/irradiance_volume_corpus.py)
gates them against the current VFS ledger; and
[`irradiance_path_native.py`](../../scripts/game_data/irradiance_path_native.py)
validates the selected native path, stream and cursor chain against the
reviewed [`irradiance_v3_path_native.json`](../../scripts/game_data/contracts/irradiance_v3_path_native.json),
which pins `GameAssembly.dll`, `global-metadata.dat` and `UnityPlayer.dll`.
Their docstrings carry the layouts and the instruction-level chain. Neither
the index records' renderer meaning nor any `iv_*.bytes` record content is
established.

## What the installed bytes establish

- **Filename tables (exact).** Every current index has a unique bounded
  UTF-16LE filename table naming each payload in its own directory exactly
  once. Supported numeric magics are `0x03000003` (scene V3), `0x03000002`
  (Gacha V3) and `0x01000043` (legacy Gacha). Do not merge their layouts
  because they share an `iv` path or a nominal version.
- **Payload ranges (exact).** Index-resident directories give byte intervals
  into each named payload: V3 words 2 and 3 (scene nine-word records, Gacha
  eight-word), legacy words 7 and 8 (nine-word, sorted by offset). Every
  group starts at zero and reaches payload EOF without gaps or overlap. The
  other directory words stay anonymous.
- **Stored arithmetic (exact, unnamed).** Rejoined to the VFS ledger with
  each index MD5 checked, the current corpus shows two magic-specific
  relations. They are not compression sizes, texture roles or selection
  rules. No tracked module recomputes them; the per-index evidence was the
  local `reports/animestudio/iv_index_additive_relations.json`.

| Index magic | Exact stored relation | Limit |
| --- | --- | --- |
| Scene V3 `0x03000003` | `w4 = w5 + w6` | `w4` can exceed the interval length `w3`, and some intervals are shorter than `w5`: not an interval split. |
| Gacha V3 `0x03000002` | `w3 = w4 + w5` | No consumer establishes a physical split at `w4` or `w5`. |
| Legacy `0x01000043` | Neither relation | Separate record layout. |

- **Gacha shared key (structural).** The V3 Gacha `character` and `weapon`
  indexes have the same ordered record count and agree position by position
  on words 0, 1, 6 and 7 while their intervals differ; the corpus gate fails
  if that changes. This is a shared stored key and order, not co-loading,
  coordinates or shared lighting.
- **Room files (exact).** Every current `regionIv_room_*` file is exactly
  `44 + 16*nx*ny*nz` bytes. The tuples behave like bounding-box endpoints and
  the grid density is about two samples per world unit, but no axes, record
  fields or probe encoding are assigned.

| Byte offset | Stored field |
| --- | --- |
| `+0` | u32 `4096` |
| `+4` | u32 header size `44` |
| `+8` | six finite f32 values, two three-component tuples |
| `+32` | three positive u32 grid dimensions |
| `+44` | `nx*ny*nz` opaque 16-byte records |

## Selected native V3 index route

Direct and conditional on the selected branches:

1. **Path sources.** Scene (`StreamingInNewMap`, then `PipelineUpdate`) and
   Gacha (`CreateGachaIV`, `UpdateGachaIV`, a separate `PipelineUpdate`
   branch) append `/v3/index.bytes` to a supplied root and call `SetMapV3`. A
   proxy conversion branch supplies another root from the serialized
   `PROP_ID_IV_INDEX_PATH` string. The roots and the property's runtime value
   are not recovered.
2. **Handoff.** `ReloadIndexFileV3` only stores the path; the `SetMapV3`
   internal call stores it on the native volume; a downstream UnityPlayer
   parser retains it as a hash-table lookup key.
3. **Stream.** A lookup hit sizes a queued stream request. The singleton's
   queue drain routes it to a read branch that reports success only when the
   read count equals the requested size. A resource-name cache selects or
   opens a provider; when no registered provider matches, the default
   provider's open and read methods reach `CreateFileW`, `SetFilePointerEx`
   and `ReadFile`.
4. **Cursor.** On success the parser takes the stream's buffer pointer. Its
   cursor accepts both V3 magics and uses 36-byte scene and 32-byte Gacha
   directory records, independently supporting the reader's widths without
   naming words. Its byte and u32 readers have no local length check, and
   the complete parser body has no final EOF comparison.

The exact-size read gate bounds successful I/O, not the parser. Which
provider served an IV request, how the supplied string is canonicalized, and
which authenticated VFS `index.bytes` the buffer held remain open, as do
payload record meaning and renderer upload.

## Selected native room-file route

A separate UnityPlayer function formats `regionIv_%s_%u.bytes`, matching the
installed room names, and its handler appends that basename to the stored
root's directory prefix (through the last forward slash) before the same
checked lookup and stream constructor. In the ready-buffer branch the
handler checks the leading `0x1000` magic word, reads the header size, two
12-byte triples and three grid dimensions, locates records at the header
size, and copies grid-cell count times 8 or 16 bytes by a native
configuration branch; the current files fit the 16-byte branch. The copied
allocation descriptor goes into a callback payload whose command binds its
first word through a native helper and requests a virtual dispatch of
`ceil(nx*ny*nz/64)`, 1, 1 groups. This directly supports the offline header
and stride framing and identifies a command-side consumer of the records.
The record fields and tuple axes, the live root, the selected installed
file, GPU execution and the texture format remain open. The room branch is
separate from the V3 index parser.

## Evidence boundary

- **Exact:** filename tables, index-directed payload tiling, room-file
  framing, and the stored additive relations in the current corpus.
- **Direct (conditional):** scene, Gacha and proxy path construction; the
  path-keyed stream, queued exact-size read gate, V3 cursor widths and absent
  EOF check; the default Windows-file provider fallback; and the room path,
  header parse, record copy, command binding and dispatch.
- **Structural only:** the Gacha character/weapon shared key and order.
- **Unresolved:** directory words beyond offset and length, payload record
  fields and encoding, room record fields and tuple axes, the live roots and
  property value, the runtime provider and VFS file identity, renderer
  upload, GPU execution and texture format.

## Eliminated readings

Do not retry these; each was tested and refused (reasoning in the module
docstrings).

- **Self-describing payloads.** The early partial filename frame and the
  claim that indexes carry no payload ranges are superseded: every index is
  framed and carries exact intervals.
- **Block-compressed texture payloads.** A 16-byte autocorrelation peak is
  insufficient, and a BC6H mode check found no signal above shuffled
  controls. Payload encoding is unresolved.
- **Config names as file layout.** `HGIrradianceVolumeConfig`/`V2` field
  names (clipmaps, hash tables, indirection, physical blocks, basis,
  coefficients) describe runtime configuration; no read joins them to an
  `iv_*.bytes` offset, a one-file LOD layout or an index word.
- **Directory words as splits.** Neither additive relation is an interval or
  physical split.
- **`ReloadIndexFileV3` as the parser.** It stores a path; the parse happens
  later in UnityPlayer, so IL2CPP metadata never exhausted the path.
- **A constructed suffix as file identity.** The scene and Gacha suffix and
  the proxy source route give a constructed path, not a unique VFS file or a
  completed buffer fill.
- **The sibling direct worker as the fill.** The selected queued request
  reaches the type-zero read branch with its own exact-count gate.
- **An opaque virtual provider.** The registry has a concrete default
  Windows-file provider; only its selection for IV requests is open.
- **Offline Gacha EOF as native acceptance.** The reader requires its
  directory to reach index EOF; the native parser has no such check.
- **`BLOCK_IV_DATA_PATH` as the proxy root.** No selected read joins its
  `Data/IrradianceVolume/` prefix to the serialized property.
- **Byte-position smoothness as decoded lighting.** Clues only.
- **Generic file-I/O hooks or a repeated magic value as a join.** A runtime
  capture must supply exact build, entry, caller, buffer length and cursor
  provenance.

## Recovery queue

1. Join a supplied root and the native lookup normalization to one
   authenticated VFS `index.bytes`, and decide whether an IV request reaches
   the default Windows-file provider or a registered provider.
2. Only then look for a native read of a specific opaque directory word that
   supports a renderer meaning.
3. For room records, find a consumer of the bound allocation descriptor or
   the dispatched operation that reads individual record words.
4. Promote the existing runtime capture candidate only with exact build,
   entry, caller, buffer-length and cursor provenance.

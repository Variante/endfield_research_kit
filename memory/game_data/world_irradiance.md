# IrradianceVolume: exact indexed ranges, open record meaning

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** `scripts/game_data/irradiance_volume.py` frames the
current `index.bytes` filename tables and the index-directed payload ranges.
The seven `regionIv_room_*` files have exact 44-byte headers and 16-byte
records. Neither the index records' renderer meaning nor the `iv_*.bytes`
record contents are established. The selected native proof in
`scripts/game_data/irradiance_path_native.py` now joins the managed path to a
native path-keyed stream and its V3 cursor buffer pointer. Selected scene and
Gacha path builders append the literal `/v3/index.bytes` before that handoff.
The selected room handler separately checks a ready stream buffer's magic,
reads the room header, and copies grid records with a conditional 8- or
16-byte stride; the current files fit its 16-byte branch. It passes the
copy's allocation descriptor into a native command callback that binds its
first word and requests a dispatch sized from the grid-cell count. This
identifies a structural consumer without decoding an individual record.
The selected queued request reaches a native read branch with an exact-sized
success gate. The registry's default provider has a verified Windows-file
open/read method set, conditional on no registered provider matching the
request name. The active provider and buffer's exact VFS identity remain open,
and the selected parser body has no final EOF comparison.

## What the installed bytes establish

The installed `iv` VFS block has 92 `index.bytes`, 138 `iv_*.bytes`, and seven
`regionIv_room_*` files. All 92 indexes have a unique bounded UTF-16LE filename
table. Those tables name the 138 payloads exactly once, with each name joined
to the file in its own directory. The supported numeric index magics are
`0x03000003` (scene V3), `0x03000002` (Gacha V3), and `0x01000043`
(legacy Gacha). Do not merge their record layouts because they share an `iv`
path or a nominal format version.

The index-resident directories give exact byte intervals into each named
payload. For both V3 layouts, words 2 and 3 are the offset and length. The
scene V3 directory uses nine-word records and supports filename-ordered groups;
the Gacha V3 directory uses eight-word records. The legacy directory uses
nine-word records, with words 7 and 8 as offset and length. After sorting each
legacy filename group by offset, its intervals tile the corresponding payload.
Every supported group starts at byte zero and reaches EOF without gaps or
overlap. The scene V3 directory start has two observed alignment variants;
the reader accepts one only when the combined filename and payload-length
constraints choose a unique boundary. Validation reads the complete payload
streams, so a short read or trailing byte is an error. The other directory
words remain anonymous.

Rejoining the current corpus to a live VFS metadata listing by logical path,
chunk identity, offset, length and declared digest, then checking each index's
MD5, found two numeric-magic-specific relations:

| Index magic | Exact stored relation | Limit |
| --- | --- | --- |
| Scene V3 `0x03000003` | `w4 = w5 + w6` | `w4` can exceed the indexed interval length `w3`, so this is not an interval split. |
| Gacha V3 `0x03000002` | `w3 = w4 + w5` | No consumer establishes a physical split at `w4` or `w5`. |
| Legacy `0x01000043` | Neither relation | Its record layout is separate. |

These are stored arithmetic facts, not compression sizes, texture roles or
runtime selection rules. Per-index evidence and changing counts belong in
`reports/animestudio/iv_index_additive_relations.json`; the reusable framing
and checks are in the tracked reader.

The seven `regionIv_room_*` files have an exact `44 + 16*nx*ny*nz` length:

| Byte offset | Stored field |
| --- | --- |
| `+0` | u32 `4096` |
| `+4` | u32 header size `44` |
| `+8` | six finite f32 values, two three-component tuples |
| `+32` | three positive u32 grid dimensions |
| `+44` | `nx*ny*nz` opaque 16-byte records |

The tuples behave like bounding-box endpoints and the grid density is about
two samples per world unit across the seven files, but the maintained reader
does not assign coordinate axes, record fields or probe encoding. Earlier
byte-position smoothness tests are useful clues, not a decoded lighting
representation.

## Selected native path handoff

The reviewed `irradiance_v3_path_native.json` contract pins the installed
`GameAssembly.dll`, `global-metadata.dat` and `UnityPlayer.dll`. The validator
checks method identities, the IL2CPP internal-call name, the parallel UnityPlayer
name/function table, the selected native function's `.pdata` windows and code
hashes, and the following instruction chain:

The selected managed literal table carries `/v3/index.bytes`. The validator
checks its tag-5 usage cell, the selected loads, the `System.String.Concat` method
identity and calls, plus code windows for the path branches. On the scene
route, `StreamingInNewMap` appends the suffix to its supplied root, stages the
result in the manager, and `PipelineUpdate` promotes that staged string to its
current path before calling `SetMapV3` when the path changes. On the Gacha
route, `CreateGachaIV` stores the appended path in a separate field;
`UpdateGachaIV` uses the same suffix for comparison and replacement, and a
separate `PipelineUpdate` branch passes that field to `SetMapV3`. These are
conditional construction routes. A separate selected
`HGIrradianceVolumeProxyEntityConvertFunc.ConvertFrom` branch reads the static
`PROP_ID_IV_INDEX_PATH` property ID, passes it to
`FlatBufferConvertContextV2.ConvertStringFrom_Injected`, then appends the same
suffix to the returned string and stages the manager's pending path. The selected
`.cctor` writes twelve ID bytes `FF0000000000000000000000`; this is a stored
identifier, with no inferred sentinel meaning. The native converter is bound
through its UnityPlayer internal-call registration. Neither the serialized
property's runtime string value nor the other supplied roots are recovered.
The separate `Beyond.VFS.VFSDefine.BLOCK_IV_DATA_PATH` static construction
uses a `Data/IrradianceVolume/` literal, but no selected read joins that field
to the proxy property's value; the prefix cannot authenticate this path.
Other callers of `ReloadIndexFileV3` remain unidentified.

1. `HG.Rendering.Runtime.HGIrradianceVolumeManager.ReloadIndexFileV3` stores its
   supplied path in the manager. It releases an old volume if present; it does
   not read index bytes.
2. The manager's `PipelineUpdate` loads that stored path and calls
   `UnityEngine.HyperGryph.HGIrradianceVolume.SetMapV3`. A separate branch
   passes a different stored path; the audit keeps that branch distinct.
3. The IL2CPP stub resolves the `SetMapV3` internal call. Its registered
   UnityPlayer function forwards the string to a helper that obtains the
   native volume object and stores the path there.
4. A downstream UnityPlayer consumer calls the native getter for that same
   field and passes the returned path to a parser routine. The parser retains
   the path as a lookup key. On a changed key it copies the supplied path; in
   its open state it calls a native hash-table lookup with that retained key.
   A successful lookup yields two u64 result words and a resource name. The
   second word sizes a stream allocation and is stored as the stream's
   requested buffer size. The stream keeps a separate data-buffer pointer.
   The constructor sets the request type and queue partition to zero, leaves
   its multi-read descriptor null, queues the object, and installs a completion
   callback. The singleton's thread drains that pending vector, dereferences
   the request pointer, and routes type zero to a read branch. That branch
   passes the request's `+0x68` data buffer, `+0x70` requested size, and
   `+0x78` backend offset to an accumulating read helper. It stores the byte
   count at `+0x80` and sends success status zero only when the count equals
   the requested size. The completion callback writes the status and releases
   a reference; it does not fill the buffer. A separate direct worker on the
   same singleton has a similar read gate, but the selected queued request
   reaches the type-zero dispatcher instead.
5. In the ready state the parser retrieves that stream's data-buffer pointer
   for its V3 cursor. The cursor reads little-endian u32 values and advances
   four bytes per read. It accepts numeric V3 index magics `0x03000002` and
   `0x03000003`. Its scene branch copies `count*36` bytes of directory records;
   its other V3 branch consumes `count` 32-byte records. This independently
   supports the reader's V3 record widths, without assigning meanings to
   their words. The selected byte and u32 cursor helpers both load
   pointer-plus-offset without a local length check. The complete selected
   parser body has no final cursor-offset-versus-stream-size or EOF equality
   check. It requests the buffer pointer only after observing success status
   zero on its stream.

The selected-build audit is `reports/irradiance/v3_path_native.json`. Its
`validated` status establishes the path-keyed lookup, stream construction,
selected queue drain and type-zero read, exact-count outer I/O success gate,
queued status callback, buffer-pointer handoff, and V3 cursor. The lookup's
size word does not become an observed parser cursor bound: the cursor
initializes its middle word to `-1`, the selected byte and u32 readers have no
local comparison, and the complete selected parser body has no final EOF
comparison. The offline reader's Gacha directory EOF condition is its strict
framing rule, not a condition proved for this native parser. For the selected scene, Gacha, and
proxy branches the constructed path has an index-file suffix. The proxy route
shows that one root
comes from a serialized property, but the audit has not recovered its value or
joined any supplied directory root and native lookup normalization to one
authenticated VFS `index.bytes`. The selected lookup hashes the supplied string
bytes; its surrounding VFS canonicalization policy is not established. The
selected request has no optional resource handle, so its read branch calls a
handle selector. That selector compares the request's resource-name bytes
against a cache and returns a slot on a hit. On a miss it creates a slot through
a resource constructor and opens a provider through a virtual method loaded
from the handle. The read bridge later loads a provider from the returned slot
and invokes another virtual method. The registry searches its registered
providers by resource name before returning a default provider on a miss.
That default object's virtual open and read slots lead to methods that call
`CreateFileW`, `SetFilePointerEx`, and `ReadFile`. The selected instructions
do not show whether an IV request chose this fallback or a registered
provider, and they expose no normalized root or concrete VFS filename.
Payload record meaning and renderer upload remain unproved.

A separate selected UnityPlayer function loads the literal
`regionIv_%s_%u.bytes`, supplies a string and an unsigned number to its
formatting call, and later calls the same checked path-keyed lookup and stream
constructor used by the V3 index route. The reviewed contract checks this
function's `.pdata` extent and bytes, the literal and RIP-relative load, all
three direct calls, and the branch that skips stream construction when lookup
fails. A selected caller passes its stored root string to the room-handler
object. Its helper compares the supplied and stored strings and copies on
change. The handler finds the last forward slash in that stored string, takes
the prefix through it, appends the formatted room basename, and passes the
assembled local unchanged to the checked keyed lookup. The validator checks
the caller, equality/assignment, slash search, substring, prefix copy,
append helper, and lookup call windows. This supplies an exact construction
rule; the live root string, formatted room identity and chosen VFS file remain
unobserved. The format matches the seven installed `regionIv_room_*` names.
In another selected branch of the same function, a ready
stream status leads to its buffer pointer. The handler checks the leading
`0x1000` word, starts a cursor at byte four, reads a header-size word, two
12-byte triples, then three grid-dimension words. It adds the stored header
size to the buffer pointer to locate record data. The next copy uses the
product of the three dimensions times either 8 or 16 bytes, depending on a
native configuration branch. The current seven files have header size 44 and
exactly 16 bytes per cell. The validator authenticates the full room function,
cursor triple helper, record-copy helper, relevant instruction windows and
call targets against the selected build. This directly supports the offline
header and record-stride framing, but does not name the tuples' axes, decode
any record field, establish a live installed-file choice, or identify renderer
upload. The room branch is separate from the V3 index parser.

After the copy, the selected handler writes the three parsed grid dimensions
into the first three words of a separate 0x30-byte descriptor and fills its
other words from room and configuration state. It packages this descriptor
and the copied-record allocation descriptor in a 0x58-byte callback payload.
The selected command entry clones that payload and points to a callback; the
callback reads the record allocation descriptor's first word at payload
`+0x28` and passes it to a native binding helper. It then requests a virtual
dispatch with `ceil(nx*ny*nz/64)`, `1`, `1` as the group dimensions. The
reviewed contract checks the allocation and copy, descriptor stores, callback
payload construction and clone, binding call, and positive-count virtual
branch against the selected native build. This is direct evidence of a
command-side consumer of the record allocation. It does not establish what
any 8- or 16-byte record field represents, whether that dispatch executed in
a live session, or the eventual texture format.

The managed metadata also contains `HGIrradianceVolumeConfig` and
`HGIrradianceVolumeConfigV2`, with fields named for clipmaps, hash tables,
indirection, physical texture blocks, basis and coefficients. They describe
runtime configuration surfaces. Field names and fixed-buffer sizes do not
join either struct to a byte offset in an `iv_*.bytes` file. In particular,
they do not prove that a payload is a GPU texture blob, that all LODs occupy
one file, or that an index word names a hash table or upload size.

## Corrected interpretations

- The earlier 86-of-92 partial filename frame and claim that indexes carry no
  payload ranges are superseded. The maintained reader frames all current
  indexes and exact indexed intervals; the old inference that payload files
  must be self-describing was wrong.
- A 16-byte autocorrelation peak in some payloads is insufficient to call the
  V3 files block-compressed textures. The later BC6H mode check found no mode
  signal above shuffled controls. Payload encoding remains unresolved.
- The old claim that the config field names *identify* the V3 container as an
  indirection texture, hash table and physical blocks promoted metadata names
  into a file-layout conclusion. It is retracted pending a direct consumer
  read that maps file bytes to those fields.
- `ReloadIndexFileV3` does not parse the index. Its selected body stores a
  path, and the native `SetMapV3` handler stores it again. A later UnityPlayer
  routine uses that path as a lookup key and obtains the V3 index cursor from
  the resulting stream object; the previous claim that the entire path was
  exhausted by IL2CPP metadata was wrong.
- The earlier uncertainty over whether the selected scene and Gacha branches
  supplied an index-file path is narrowed: both append `/v3/index.bytes` to a
  supplied root. This establishes a constructed suffix, not a unique VFS file
  identity or completed buffer fill.
- One selected proxy conversion branch supplies another V3 index path from a
  serialized `PROP_ID_IV_INDEX_PATH` string. Its property name and static ID
  bytes identify the source route, but its runtime value is still missing.
- The earlier shared-singleton evidence left the selected queued fill
  conditional. The type-zero request now traces through that singleton's
  pending-vector drain to a separate read branch with its own exact-count
  success gate; it does not need the sibling direct worker.
- The earlier virtual-provider boundary hid a concrete conditional branch:
  the registry has a default OS-file provider with authenticated open/read
  methods. Its fallback selection depends on the request name missing the
  registered-provider search; the selected IV request's choice is still open.
- The offline Gacha index reader requires its directory to reach index EOF;
  the selected native parser has no final cursor EOF comparison. The offline
  requirement is a validated corpus-framing choice, not a native acceptance
  condition.
- The earlier room files had exact offline framing but no selected native
  filename or header witness. The conditional filename-format, stream request,
  and ready-buffer parser now identify the room-file path family and confirm
  the stored header/record-stride structure. The selected path assembly now
  proves how a supplied root directory and formatted basename reach lookup.
  It does not identify the live root, selected installed file, or what a grid
  record means to the renderer. The selected callback now binds the copied
  record allocation descriptor's first word into a native command and requests
  a grid-count-sized dispatch; it does not establish record fields or completed
  GPU execution.

The next useful boundary is the supplied-root/native-lookup join and the
runtime-selected provider behind the returned cache slot. A capture or
selected construction path must decide whether that request reaches the
default Windows-file provider or a registered provider, then bind its opened
name to one current authenticated VFS `index.bytes`. The selected queue's
exact-sized read gate does not add a final parser EOF check.
Only then can a native read of a specific
opaque directory word support a renderer meaning. The room-record command
handoff narrows the next field-level question to a consumer of the bound
allocation descriptor or the dispatched operation; the current callback reads
its descriptor word and count, not individual record words. A runtime capture
candidate exists, but it still needs exact build, entry, caller, buffer-length
and cursor provenance; a generic file-I/O hook or a repeated magic value does
not supply that join.

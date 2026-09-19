# IrradianceVolume: the largest family, still unread

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, world lane.** The biggest VFS block by size and the least decoded. The
index is framed and joins exactly; the payload is not, and the reason is
structural -- the payload parser is native while the index handler is managed. The
eliminations are recorded so they are not repeated.

## The irradiance-volume index

`Data/IrradianceVolume/PC/<level>/v3/index.bytes` decodes cleanly at the head: a u32
`0x03000003`, a u32, then a **length-prefixed UTF-16LE string** (`'under_construction'`), a
28-byte field block, then **back-to-back length-prefixed UTF-16LE file names** naming the
volume payloads this level uses -- `'iv_0_0.bytes'`, `'iv_1215527338_0.bytes'`.

**The strings are only a header.** In the sample level they occupy 150 of 6,390 bytes and the
remaining **6,240 bytes are small integers and zeros** -- *not* float positions or bounds, which
is what an irradiance-volume index invites one to expect: only **9.9%** of the tail reads as a
plausible float. Its record size is not settled -- 6,240 divides evenly by 12, 16, 24, 32 and 48
alike, **so the divisor proves nothing and none is claimed.**

**The second u32 is the named-entry count**, and it is **0 in 82 of 92 index files** -- *most
levels name no payload at all*, which is why the sampled level with three strings is the
exception rather than the pattern.

## The `iv` payloads are not one format

The block holds three kinds: **92 `index.bytes`, 138 `iv_N_N.bytes`, 7 `regionIv_room_*`**.

***A four-file sample said the payloads begin `(3, 2)` with a 512-byte header of `0`/`0xffffffff`
sentinels. Across 120 files that holds for only 25%.*** The sample came from the first
directories and was not representative. The majority open instead as `(N, 512)` or `(N, 768)`
-- 990, 1050, 1063, 1246, 2270 in the first word -- with **high-entropy data immediately after
an 8-byte head** and no sentinel region at all. *No header word equals the body or file length
in any of the 120*, and body sizes are unaligned (divisible by 4 in only 21.7%), **so the
payload length is not stated in the header** by any reading tried.

The bodies are packed: entropy **6.7-7.2 bits/byte** with adjacency **+0.01 to +0.09**, the same
signature that identified the block-compressed `LAYER` files.

***They are block-compressed at a 16-byte block size.*** Two measurements agree:

* **A 16-byte period.** Mean `|x[i] - x[i+lag]|` is minimised at **lag 16 in every file tested**
  (56.6 / 57.8 / 61.9 against lag-1 baselines of 73.5 / 75.6 / 68.4), with lags 32 and 48 next --
  multiples of the same period.
* **No positional structure within the block.** All 16 byte positions carry **256 distinct values
  with identical zero-fractions** (~0.12-0.14). *Compare the decoded `regionIv` probe, also 16
  bytes, where positions 11 and 15 are zero in every record* -- **a plain record has per-position
  structure and these have none.**

Periodic at 16 bytes but flat inside the block is what **BC-family block compression** looks
like: blocks are spatially coherent with their neighbours while every byte position spans the
full range. *The specific BC variant is not identified* -- an irradiance volume would plausibly
use an HDR format -- **but the block size and the compressed-texture reading are measured rather
than assumed.**

## `regionIv_room_*` decoded completely

The seven `regionIv_room_*` files are the only unpacked ones in the block, and they decode
end to end:

| offset | field |
| --- | --- |
| `+0` | u32, constant **4096** |
| `+4` | u32 **44** -- *the header size itself* |
| `+8` | 3 x f32 bounding-box **min** |
| `+20` | 3 x f32 bounding-box **max** |
| `+32` | 3 x u32 grid dimensions `nx, ny, nz` |
| `+44` | `nx*ny*nz` probe records of **16 bytes** |

***`44 + 16 * nx*ny*nz == file length` in 7 of 7 files*** -- 36x17x39, 39x17x36, 37x21x35,
40x16x62 and so on, against sizes from 381,932 to 634,924 bytes.

***The reading is confirmed independently by probe density.*** Dividing each grid dimension by
its bounding-box extent gives **1.92 to 2.01 probes per world unit on every axis of every
file** -- a fixed ~2/unit sampling. *A bounding box and a grid that happen to be mislabelled
would not produce a constant density across seven files and three different box shapes.*

**The 16-byte probe is four 4-byte groups.** Bytes 11 and 15 are **zero in every probe**, and
groups 1, 2 and 3 are near-identical triples -- mean absolute difference of **0.8-1.3** between
groups 1 and 2 and **2.2-3.5** between 2 and 3.

***Which bytes hold sampled field data can be settled without knowing the encoding.*** Real
irradiance is spatially smooth, so the probes were reshaped onto their `nx,ny,nz` grid and
neighbour correlation measured per byte position, against a shuffled-probe control:

| byte positions | neighbour correlation | mean abs. difference |
| --- | --- | --- |
| 4-10, 12-14 | **0.77 - 0.91** | 3.3 - 4.6 |
| 0, 3 | 0.77, 0.81 | 16.4, 6.1 |
| **1, 2** | **0.40, 0.17** | **56, 75** |
| 11, 15 | -- | constant zero |
| *shuffled control* | ***~0.00*** | -- |

***So groups 1-3 are genuinely a sampled field*** -- correlation up to 0.91 where shuffling the
same values gives 0.00. **Bytes 1 and 2 are not**: at 0.40 and 0.17 with neighbour differences of
56 and 75 they are packed or quantised data sitting inside an otherwise smooth record, *which is
why the record must not be read as four uniform RGBA groups.*

**The grid is stored x-fastest.** Ordering the probes with `x` innermost gives lower neighbour
differences at **every one of the 16 byte positions** than `z` innermost (16.4 vs 18.4 at
position 0, 3.93 vs 4.75 at position 4, and so on) -- *a small margin, but unanimous across all
sixteen.*


The audio lane's three open items are all blocked on evidence outside the shipped
audio data, so this batch triaged the whole VFS by byte volume to find where the
unread data actually is.

**The whole installed set is 67.5 GB over 455,691 ledger rows**, and by extension:

| extension | bytes | share |
| --- | --- | --- |
| `.ab` (Unity asset bundles) | 42.07 GB | **62.3%** |
| `.pck` (audio) | 11.49 GB | 17.0% |
| `.usm` (video) | 6.56 GB | 9.7% |
| **`.bytes` (VFS-native)** | **6.33 GB** | **9.4%** |
| `.json` | 827 MB | 1.2% |

Within `.bytes`, one family dominates:

| family | files | bytes | share of `.bytes` |
| --- | --- | --- | --- |
| **`iv_*.bytes`** | **132** | **4.16 GB** | **65.6%** |
| `LAYER_N_*` | 345 | 469 MB | 7.4% |
| `LAYER_D_*` | 345 | 414 MB | 6.5% |
| `InitChunkData_*` | 26,520 | 624 MB | 9.9% |
| `Terrain_*` | 30,280 | 245 MB | 3.9% |

## What is measured so far

- The family is **`Data/IrradianceVolume/PC/<scene>/v3/iv_<x>_<y>.bytes`**, streamed
  through the maintained CLI as `--block-type iv` (block value **14**); the `AuditIV`
  block is 8. Streaming every `iv_*.bytes` yields **138 files**, 16,064 bytes to
  70,032,579 bytes.
- The first two `u32` take **49 distinct pairs** across the 138 files. The most common
  is **`(3, 2)` in 34 files**; the rest are `(n, 512)`, `(n, 768)`, `(n, 1280)` with
  `n` in the 990-2,270 range, and `(12291, 8)` / `(12291, 6)` in the four smallest.
- The two 16,064-byte files (`gacha/character` and `gacha/weapon`) show a clear
  **16-byte repeat**: one word, then three `RGB 00` triples. Colour triples at a fixed
  stride are what an irradiance probe grid looks like, but that is a shape observation
  and nothing is claimed from it yet.

## What was measured and is WRONG

A first reading of one `(3, 2)` file showed `03 03 03 00` at `+40` and `472` at `+44`,
which looked like a 3x3x3 probe grid and a count. **Across the 34 files that share the
header, those offsets hold `(3,3,3)`/472, `(15,15,15)`/472, `(3,3,0)`/472 and
`(255,255,255)`/`0xFFFFFFFF`** -- the last being an all-`FF` region that starts at
different places. So `+40` is not a fixed field; what precedes it is variable-length.
*A tidy-looking triple in one file is a coincidence until the same offset is read in
every file that should share the layout.*

## The family splits in two, and the stride-4 peak is an artefact

Autocorrelating byte i against byte i+stride over each payload puts **stride 4** on top
in most files (0.14 to 0.42 agreement against a 0.03 to 0.09 mean), with 16, 32, 48 and
64 following as its harmonics. That reads as 4-byte records. **It is only half true,
and a per-phase content test says which half.**

Splitting each payload into its four byte phases and measuring each one separately:

| file | phase 0 | phase 1 | phase 2 | phase 3 | phase 3 zero |
| --- | --- | --- | --- | --- | --- |
| `gacha/character/iv_3_0_0` | 7.44 | 7.30 | 7.16 | **3.51** | **52.0%** |
| `gacha/weapon/iv_3_0_0` | 4.66 | 4.71 | 4.08 | **1.30** | **75.1%** |
| `indie_dg008/v3/iv_0_0` | 6.25 | 6.22 | 6.25 | 6.19 | 19.3% |
| `dung02_cdg012/v3/iv_0_0` | 7.30 | 7.28 | 7.28 | 7.18 | 14.5% |

(entropy in bits per byte)

- **The `gacha/*` files have a real 4-byte record.** Phase 3 carries a fraction of the
  entropy of phases 0 to 2 and is zero in half to three quarters of records -- the
  shape of three colour channels plus a shared exponent or alpha. Four such files, 16
  KB to 101 KB.
- **The `v3/*` files have no byte-phase structure at all.** All four phases have the
  same entropy to two decimal places and the same top byte values. **A file with
  4-byte records cannot look like that**, so the stride-4 peak there is an artefact of
  something else and not a record width. Those are 134 files and essentially the whole
  4.16 GB.
- *An autocorrelation peak says a distance matters; it does not say a record lives
  there. The phase test is what separates the two.*
- Entropy 6.2 to 7.3 with no phase structure is what compressed or block-packed data
  looks like. **The terrain container's codec does not apply** -- that reader needs the
  file's leading word to be the decoded size, and here the leading word is 3, 990,
  1,182 or 12,291 for files of 16 KB to 70 MB.

## The game names this format itself, and it has an INDEX

Rather than guess the container further, `global-metadata.dat` was asked what the
engine calls it. The answer is specific:

```
HGIrradianceVolumeManager / HGIrradianceVolumeManagerV2
HGIrradianceVolumeConfig  / HGIrradianceVolumeConfigV2
  GetCurrentIrradianceVolumePathV3      ReloadIndexFileV3 / ReloadIndexFileV2
  ToggleDebugUpdateClipmap              ToggleDebugUpdateClipmapLod0
  UpdateSceneStateMask                  UpdateGachaIV
  StreamingInNewMap / StreamingInCabin  SetOverrideStreamingCenterByCamera
```

Three of these change what to do next:

- **`ReloadIndexFileV3`** says there is an index. There is: **92 `index.bytes` files**
  in the IV block, 980 bytes to 504 KB, one per scene -- plus **7 `regionIv_*.bytes`**
  files totalling 3.09 MB. The earlier sweep matched only `iv_*.bytes` and missed both.
- **`ToggleDebugUpdateClipmap`, `...Lod0`** name the structure: a **clipmap**, a
  nested multi-resolution grid. That is what a volume file should be expected to hold.
- **`UpdateGachaIV`** is a separate entry point from the V3 streaming path, which
  independently confirms the `gacha` / `v3` split the byte-phase test measured.

### The index is framed enough to join, and the join is exact

The index holds **length-prefixed UTF-16LE strings**: `u32 byteLength`, then that many
bytes of UTF-16. The 980-byte index carries `u32 24` followed by `iv_0_0.bytes`.

- Across the 92 index files, **138 `.bytes` names are listed -- exactly the 138 volume
  files the block contains**.
- **91 of the 92 indexes name precisely the set of files present in their own
  directory.** Not a hit rate over a large population: each index names between one and
  a few dozen files and gets the whole set right.
- A `u32` at `+20` equals the name count in **86 of 92**, so it is a **candidate**
  count offset rather than an established one, and is recorded that way.

### The index IS framed: 86 of 92, and the other 6 are fenced by name

`scripts/webui/assets/irradiance_index.py`, with
`scripts/tests/test_irradiance_index.py`:

```
u32 magic            0x03000003 x82, 0x01000043 x2, 0x03000002 x2
u32 stateCount       the scene states GetStateNameList returns
stateCount x name    u32 byteLength, then that many bytes of UTF-16LE
u32 u32 u32          three words: 1, 0, 0 in every framed file
u32 volumeCount
volumeCount x name   the volume files in this directory
... remainder        the clipmap description, not framed
```

| | |
| --- | --- |
| indexes | **92** |
| framed exactly | **86** |
| fenced as unsupported | **6** |
| failed | **0** |
| volume names read | 103 |
| **volume sets matching the directory** | **86 of 86** |

- **The content check is the volume-name join, and it is strict on purpose.** Each
  index names between one and a few dozen files, so "the whole set, every time" is a far
  stronger statement than a percentage over a large population. A single name that is
  not there, or one missing, means the name table has been misread.
- **The three middle words are discriminated by closure.** At three words 86 files
  frame; at **zero, one, two, four or five words, not one file frames at all**. A width
  that framed fewer would be weak evidence; a width that frames none is the whole
  discrimination. Their values are constants -- 1, 0, 0 -- in all 86.
- **The 6 fenced files declare scene states**, and their names are what the engine's
  `GetStateNameList` returns: `Afternoon`, `Evening`, `001_damaged`, `001_normal`,
  `001_overcast_rainy`, `Map02_lv009_night`, `under_construction`. After those names the
  gap before the volume count is `3 + 3 x stateCount` words in three of them and
  something else in the other three, so **the variant is refused rather than guessed
  at** -- reported as `unsupported`, which cannot be mistaken for a defect.

### The remainder after the name table: measured, not framed

With a fixed start offset in 86 files the remainder can be characterised, and what it
is *not* is worth recording as clearly as what it is.

- **It begins with a run of small signed integers.** In **63 of the 86** files all
  sixteen leading words satisfy `|v| <= 4096`; the rest break sooner. First words are
  `(4,3)`, `(5,3)`, `(5,2)`, `(9,5)`, `(7,5)`, `(11,7)`, `(5,3)`, `(11,9)` -- 23
  distinct openings over 86 files.
- **The `gacha` pair opens `24, -32, -32, -32, 0, 0`**, which reads as a size followed
  by a negative corner. Reading these words as **signed** matters: unsigned they are
  `4294967264` and look like garbage.
- **They are not floats.** Every one of the leading words is `0.0` or `NaN` when read
  as float32.
- **No grid product predicts the remainder size.** Testing `w0*w1`, `w0*w1*w2` and
  `w0*w1*w2*w3` against remainder minus a header of 8, 12, 16, 20 or 24 bytes, for a
  record size between 1 and 4,096: **every combination that divides does so for exactly
  one file of 86.** A record array would divide for many.
- So the remainder is **not** `header + grid x record`, and the leading words are not a
  dimension triple that sizes it. They are recorded as small signed integers and
  nothing more.

### The index carries NO sizing for the volume payload, so the payload is self-describing

I said last batch that the volume payload should wait for the index, because the index
is what describes it. **Three joins say that is wrong, and the correction changes the
plan.**

| join tested | result |
| --- | --- |
| the volume file's byte length appears anywhere in its index | **0 of 86** |
| the sum of volume lengths, or length minus 8, or length over 4 | **0 of 86** |
| some remainder word divides the volume length into 1..4,096 parts | **2 of 71**, at record sizes 2,700 and 3,398 |

The index names its volume files and nothing more that this can find: no offset table,
no byte count, no probe count. **So the volume payload has to be self-describing**, and
framing should start from `iv_*.bytes` rather than waiting on the index.

*A plan built on "the index describes the payload" survived exactly as long as it took
to test the join.*

### The `gacha` volume header: a candidate relation on four files, not a frame

The volume filenames are `iv_<lod>_<x>_<y>.bytes`, and size falls with the first
number -- `iv_0_0_0` is 2.25 MB, `iv_1_0_0` is 84.8 KB, `iv_3_0_0` is 16.1 KB. That is
the clipmap LOD `ToggleDebugUpdateClipmapLod0` refers to.

Six files carry magic **`0x00003003`**, and in **four of them** the first eight words
line up:

| file | w1 | w2 | w3 | w4 | w5 | w6 | w7 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `character/iv_0_0_0` | 58 | **2000** | 140 | **604** | 5 | 3 | **32** |
| `weapon/iv_0_0_0` | 60 | **2000** | 140 | **620** | 4 | 3 | **32** |
| `character/iv_1_0_0` | 6 | **2000** | 64 | **112** | 3 | 2 | **32** |
| `weapon/iv_1_0_0` | 6 | **2000** | 64 | **112** | 5 | 2 | **32** |

- **`w4 = w1 x 8 + w3`** in all four: 58x8+140=604, 60x8+140=620, 6x8+64=112. So `w3`
  is a header size and `w1` counts 8-byte entries that follow it, ending at `w4`.
- `w2` is **2000** and `w7` is **32** in all four; `w6` is 3 at LOD 0 and 2 at LOD 1.
- **The two `iv_3_0_0` files share the magic and do not follow it**: their `w2` and `w3`
  are arbitrary 32-bit values. Either the deepest LOD has no header, or the magic is
  not what selects the layout.

***Four files is thin, and this is recorded as a candidate relation rather than a
frame.*** It is not in a maintained reader and has no gate. Three constants and one
arithmetic identity over four samples is the kind of pattern that has already failed
twice in this lane once the whole population was checked -- the stride-4 periodicity and
the clipmap grid extents both looked at least this good.

### What the 132 `v3` payloads are NOT: five containers eliminated

The `v3` files are 4.16 GB and the thing worth framing. Five hypotheses are now
excluded, each by a measurement rather than by inspection.

| hypothesis | test | result |
| --- | --- | --- |
| a chain of size-prefixed blocks | 1/2/4-byte sizes, prefix in or out, starts 0..32 | **no chain reaches EOF** in any file |
| the terrain container's LZ4 variant | its reader needs the leading word to be the decoded size | the leading word is 3, 990, 1,182 or 12,291 for files of 16 KB to 70 MB |
| standard compression | zlib, gzip, zstd, lz4 frame, bzip2 magics in the first 4 KB | **none**; the 22 "zlib" hits are coincidental `78 01` byte pairs, and no offset 0..63 inflates to more than 1 KB |
| an array of 4-byte records | byte-phase entropy | **all four phases equal to two decimals**, which a 4-byte record cannot produce |
| an array of spatially coherent probe values | delta entropy at every stride 1..64 | **every delta raises entropy above raw** -- 6.21 to 6.74 at best |

The last is the sharpest. Irradiance data is spatially smooth by nature, so if the
payload were probe values laid out on a grid, differencing at the record stride would
*drop* the entropy. It rises at every stride from 1 to 64. **There is no byte stride at
which consecutive values resemble each other.**

Two more, from content tests rather than statistics:

| hypothesis | test | result |
| --- | --- | --- |
| **BC6H blocks** (HDR, the natural choice for probes) | four 5-bit mode values are reserved, so real BC6H never lands on them | **7.9% to 11.1% reserved**, against **11.7% for the same bytes shuffled** -- no signal at all, at any block start from 0 to 63 |
| run-length or sparse encoding | share of bytes in runs of 4 or more | **0.0% to 8.3%**, against 0.4% shuffled; one file has none whatever |

**The BC6H test is the one that mattered**, because bit-packed block compression was
the shape argument left standing after the other eliminations. It fails completely: the
mode field carries no more structure than shuffled bytes do. *A shape argument survives
exactly until someone tests the thing it predicts.*

So after seven eliminations the `v3` container is still unidentified, and the profile it
has to satisfy is now quite specific: **entropy 5.0-6.9 bits per byte, all four byte
phases identical, no delta coherence at any stride 1-64, no runs, no standard
compression, no block-mode structure.** The byte census is dominated by `00`, then
`FF`, `04`, `80`, `CC`, `40`, `30`, `01` -- round values and `0xCC`, which is the
repeating bit pattern `11001100`.

### THE FORMAT IS DESCRIBED BY ITS OWN TYPE: `HGIrradianceVolumeConfigV2`

Seven eliminations by byte statistics had not identified the container. The IL2CPP type
layout identifies it in one read, using the metadata parser already in
`tools/endfield-il2cpp/catalog_option_flow_metadata.py`.

**`UnityEngine.HyperGryph.HGIrradianceVolumeConfigV2`, 34 fields:**

```
clipMapTextureSizeX / Y / Z          maxRegionCount
basisBaseGridDim, basisVoxelDataDim  perBasisLodBudget,  perBasisTextureOffset
coeffBaseGridDim, coeffVoxelDataDim  perCoeffLodBudget,  perCoeffTextureOffset
lod3BaseGridDim, lod3VoxelDataDim, lod3Budget
rawDataSize, modelBufferBudget, perLOD
perHalfStreamingChunkCountsX / Y / Z
perRawBufferOffsets, perRawBufferCounts
perBlockInfoBufferOffsets, perBlockInfoSize
perBasisTextureBlockCounts, perCoeffTextureBlockCounts
perFrameMaxLoadingByteCount, perFrameMaxUploadChunkCount
```

**`HGIrradianceVolumePipelineUpdateResultV2`:** `clipmapTextureALod0`, `BLod0`,
`ALod1`, `BLod1`, `ALod3`, `BLod3`.

So the payload is **GPU texture data for two textures per LOD** -- a **basis** and a
**coefficient** set, which is spherical-harmonic lighting -- uploaded to a clipmap.
***That is why no byte statistic found a record: there is no record.*** It is texture
upload data, and the block structure belongs to the GPU format, not to a file layout.

### The LODs are 0, 1 and 3, and that explains the two exceptions

The config names exactly `Lod0`, `Lod1` and `Lod3`, and gives **LOD 3 its own fields**
(`lod3BaseGridDim`, `lod3VoxelDataDim`, `lod3Budget`) where the others share
`basis*`/`coeff*` ones. The filenames agree: the six `iv_<lod>_<x>_<y>.bytes` files are
**two each at LOD 0, 1 and 3** and nothing else.

That settles the candidate relation recorded last batch. `w4 = w1 x 8 + w3` holds for
LOD 0 and LOD 1, which share `w2 = 2000` and `w3` of 140 and 64 -- and fails for the two
LOD 3 files, **because the engine declares LOD 3 as a separate case**. The exceptions
were not noise in a thin sample; they are a documented variant. *A relation with
unexplained exceptions and a relation whose exceptions the vendor's own config explains
are different things.*

### TWO SCHEMES, and the field names say which file uses which

There are two config types, and their fields are different schemes rather than
versions of one:

| `HGIrradianceVolumeConfigV2` (34 fields) | `HGIrradianceVolumeConfig` (26 fields) |
| --- | --- |
| `clipMapTextureSizeX/Y/Z` | `indirectionTextureSize`, `ClipmapTextureSize` |
| `basisBaseGridDim`, `basisVoxelDataDim` | `blockCountX/Y/Z`, **`blockSizesV3`** |
| `coeffBaseGridDim`, `coeffVoxelDataDim` | `hashTableSize`, `maxHashTableSize` |
| `perBasisTextureOffset`, `perCoeffTextureOffset` | `perHashTableOffsets`, `perHashTableSizes` |
| `lod3BaseGridDim`, `lod3VoxelDataDim`, `lod3Budget` | `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts` |
| `perRawBufferOffsets`, `perRawBufferCounts` | **`perFrameMaxLoadingByteCountV3`**, **`perFrameMaxUploadChunkCountV3`** |

- **V2 is a clipmap of basis and coefficient textures per LOD.** That is the
  `iv_<lod>_<x>_<y>.bytes` form -- the six non-`/v3/` gacha files at LODs 0, 1 and 3,
  with magic `0x00003003` and the `w4 = w1 x 8 + w3` header.
- **V3 is a sparse virtual texture: an indirection texture, a hash table, and physical
  texture blocks.** The three fields carrying the `V3` suffix all live in
  `HGIrradianceVolumeConfig`, alongside `blockSizesV3`. That is the
  `Data/.../v3/iv_<x>_<y>.bytes` form -- 132 files, 4.16 GB.

**This is what the byte statistics were seeing.** A hash table and an indirection
texture at the front of a file are exactly what "49 distinct leading word pairs, no byte
alignment, no delta coherence, no runs, entropy 5-7" look like. The leading words are
hash-table and indirection data, and the bulk is physical texture blocks. *Seven
eliminations were each correct and all pointing at the same answer, which none of them
could name.*

- **The LOD is carried inside the file, not in the name.** `perLOD`,
  `perHashTableOffsets`, `perHashTableSizes`, `perPhysicalTextureOffsets` and
  `perPhysicalTextureBlockCounts` are per-LOD arrays, so one `iv_<x>_<y>.bytes` holds
  every LOD for its chunk. The `<x>_<y>` are chunk coordinates, which is why 117 of 132
  begin `iv_0_`.

### Both configs are blittable structs of fixed buffers, and that closes the argument

Every `per*` field is a C# **fixed buffer**: each has a generated nested type
`<name>e__FixedBuffer` holding a single `FixedElementField`.

| type | fields | of which fixed buffers |
| --- | --- | --- |
| `HGIrradianceVolumeConfig` (V3) | 26 | **11** -- `perLOD`, `perHalfChunkCounts`, `perHashTableOffsets`, `perHashTableSizes`, `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts`, `perFrameMaxLoadingByteCount`, `perFrameMaxUploadChunkCount`, `ClipmapTextureSize`, **`blockSizesV3`**, `cameraForwardBiasForYAxis` |
| `HGIrradianceVolumeConfigV2` | 34 | **19** -- the `basis*`/`coeff*` dims, `perRawBuffer*`, `perBlockInfo*`, `perBasisTexture*`, `perCoeffTexture*`, `perHalfStreamingChunkCounts{X,Y,Z}`, `streamingCenterBias` |

So both are **blittable structs with fixed-size per-LOD arrays** -- native interop
configs, not serialised objects.

***`blockSizesV3` is a fixed buffer, so block size varies per LOD.*** That is the last
of the byte-statistic negatives explained: there is no single record stride in a `v3`
payload because the physical texture blocks are sized per LOD, and one file holds every
LOD for its chunk.

### THE EXTENTS: every per-LOD buffer is 3 x 4 bytes, so there are THREE LODs

`Il2CppTypeDefinitionSizes` in `GameAssembly.dll` gives each generated
`e__FixedBuffer` type's size, and that size *is* the buffer. Reached through the
existing bridge in `tools/endfield-il2cpp` -- CodeRegistration at `0x18a88e640`,
MetadataRegistration at `0x18a88e860`, 58,110 size entries.

**Every per-LOD buffer in both configs is `native 12` = 3 x 4 bytes**, without
exception:

| | buffers | native size | elements |
| --- | --- | --- | --- |
| `HGIrradianceVolumeConfig` (V3) | 11 | **12** each | **3** |
| `HGIrradianceVolumeConfigV2` | 17 of 19 | **12** each | **3** |
| `basisBaseGridDim`, `basisVoxelDataDim` | 2 | **24** | **6** |

- **Three LOD slots, and 28 independent fields agree on it.** That is not one
  measurement: `perLOD`, `perHashTableOffsets`, `perHashTableSizes`,
  `perPhysicalTextureOffsets`, `perPhysicalTextureBlockCounts`, `blockSizesV3`,
  `perRawBufferOffsets`, `perBlockInfoSize`, `perBasisTextureOffset`,
  `perCoeffTextureOffset` and the rest are all 12 bytes.
- **It matches the names.** `HGIrradianceVolumePipelineUpdateResultV2` exposes
  `Lod0`, `Lod1` and `Lod3` -- three textures per set, indices 0, 1 and 3, three slots.
- The two 24-byte buffers, `basisBaseGridDim` and `basisVoxelDataDim`, hold **six**
  words where the matching `coeff*` fields are plain scalars. Three LODs x two values,
  or two triples; that is not settled and is not claimed.
- `streamingCenterBias` and `cameraForwardBiasForYAxis` are also 12 bytes, but they are
  a `Vector3` rather than per-LOD -- *a size alone does not say what a buffer is for,
  and these two are the reminder.*

### The exact config layouts, read from `Il2CppFieldOffsets`

Both structs, byte-exact. Offsets below are struct-relative; the binary reports them
object-relative, so each is 16 higher there (the managed header), and the last field
lands on the struct size exactly -- which is the check that the table was read right.

**`HGIrradianceVolumeConfig` -- the V3 scheme, 192 bytes:**

```
+0   enableLowQualityMode    4     +96  perFrameMaxLoadingByteCount   12
+4   indirectionTextureSize  4     +108 perFrameMaxUploadChunkCount   12
+8   blockCountX             4     +120 perFrameMaxLoadingByteCountV3  4
+12  blockCountY             4     +124 perFrameMaxUploadChunkCountV3  4
+16  blockCountZ             4     +128 maxHashTableSize               4
+20  hashTableSize           4     +132 maxInactiveFrameCount          4
+24  perLOD                 12     +136 ClipmapTextureSize            12
+36  perHalfChunkCounts     12     +148 blockSizesV3                  12
+48  perHashTableOffsets    12     +160 cameraForwardBiasForYAxis     12
+60  perHashTableSizes      12     +172 maxRegionCount                 4
+72  perPhysicalTextureOffsets     12   +176 regionAtlasSizeX          4
+84  perPhysicalTextureBlockCounts 12   +180 regionAtlasSizeY          4
                                        +184 regionAtlasSizeZ          4
                                        +188 enableLowMemoryMode       4
```

**`HGIrradianceVolumeConfigV2` -- the clipmap scheme, 312 bytes:** same method;
`clipMapTextureSizeX/Y/Z` at +4/+8/+12, `basisBaseGridDim` +16 (24 bytes),
`basisVoxelDataDim` +40 (24), `coeffBaseGridDim` +64, `coeffVoxelDataDim` +68,
`perCoeffLodBudget` +72, `perBasisLodBudget` +84, `lod3BaseGridDim` +96,
`lod3VoxelDataDim` +100, `lod3Budget` +104, `rawDataSize` +108,
`modelBufferBudget` +112, `perLOD` +116, then the `perHalfStreamingChunkCounts{X,Y,Z}`,
`perRawBuffer{Offsets,Counts}`, `perBlockInfo{BufferOffsets,Size}`,
`perBasisTexture{Offset,BlockCounts}`, `perCoeffTexture{Offset,BlockCounts}` and
`perFrameMax{LoadingByteCount,UploadChunkCount}` buffers at 12 bytes each,
`maxRegionCount` +284, `regionAtlasSizeX/Y/Z` +288/+292/+296,
`streamingCenterBias` +300.

**The `v3` container, as far as the evidence goes:** an indirection texture and a hash
table addressing physical texture blocks, with **three** per-LOD offset/count pairs and
three per-LOD block sizes, all in fixed buffers inside these blittable structs.

### The config is NOT in the shipped files, and the search had a positive control

Knowing the struct exactly turns "is it in the file?" into a search with a
specification rather than a pattern hunt. A 192-byte window counts only if every field
is plausible for what it is named: `enableLowQualityMode` 0 or 1, the block counts and
`indirectionTextureSize` positive and under 8192, `maxHashTableSize >= hashTableSize`,
the three `perLOD` entries in 1..64, and `perHashTableOffsets` and
`perPhysicalTextureOffsets` non-decreasing.

| scanned | candidates |
| --- | --- |
| all 92 `index.bytes` | **0** |
| 12 `v3` payloads, first 400 KB each | **0** |
| the same payload bytes shuffled | 0 |

***A test that returns zero on everything has not shown it can detect anything***, so
the zero above is only worth having because of a positive control:

| control | candidates |
| --- | --- |
| a synthetic config filled the way the engine would | **1** |
| that struct embedded at offset 5000 in 20 KB of random bytes | **1, at exactly 5000** |
| the 20 KB of random bytes alone | **0** |

So the scanner detects the struct when it is there and does not fire on noise -- and
**the V3 config does not appear in any shipped index or payload**. It is a runtime
config the engine holds, not something serialised into the data, and the `.bytes` files
must carry their geometry some other way.

That closes the gap flagged last batch: knowing a struct exactly is not the same as
knowing it is in the file, and here it is not.

### WHY it is not: the payload parser is native, the index handler is managed

The method flags say exactly where the boundary runs.

| type | methods | `iflags` | kind |
| --- | --- | --- | --- |
| `HGIrradianceVolume`, `HGIrradianceVolumeV2` | `SetMap`, `SetMapV3`, `PipelineUpdate`, `StreamingInCabin`, `SetActiveSceneStateMask`, ... | **0x1000** | **InternalCall -- native C++** |
| `HGIrradianceVolumeManager` | `ReloadIndexFileV3`, `GetStateNameList`, `UpdateSceneStateMask`, `StreamingInNewMap`, ... | **0** | **managed C#** |

- **The `.bytes` payload is parsed in native code**, reached through internal calls. IL2CPP
  metadata cannot describe its layout because no managed type exists for it -- the
  managed side passes a path and a config struct and nothing else crosses.
- **That is why the config is not in the file.** It is the managed-to-native *parameter*,
  not serialised content. The two findings are the same fact seen from both sides.
- **The index handling is managed and therefore readable.** `ReloadIndexFileV3` and
  `GetStateNameList` are ordinary C# with method bodies in `GameAssembly.dll`, which the
  existing bridge can locate.

**So the lane splits cleanly by reachability.** The index frame at 86 of 92 can be
checked against the game's own parser. The payload layout cannot be reached this way at
all; it needs the native loader disassembled, and the project's existing note that
static work on `GameAssembly.dll` is constrained by HGP applies.

*Knowing that a thing is out of reach, and why, is worth more than another sweep that
was never going to find it.*

### `ReloadIndexFileV3` does not parse the index either

The one reachable check turned out not to exist. `ReloadIndexFileV3` is managed, its
body is at `0x188fc27d8` in `HG.RenderPipelines.Runtime.dll` (local method #2222 of
9,473), and it is **40 instructions long**:

```
class-init guard (0x75a)
if [this+0x10] != 0:  release it, null it, store a value at [this+0x18]
store the path argument at [this+0x20]        <- m_irradianceDataPathV3
return
```

It **releases the current volume and stores the new path**. No file is opened, no bytes
are read, nothing is parsed. The load happens later, natively.

- So **the entire IrradianceVolume format -- index as well as payload -- is parsed in
  native code.** The managed surface is paths, a config struct, and lifetime calls.
- **The index frame therefore cannot be cross-checked against the game's own parser**,
  which was the reachable next step identified last batch. It is not reachable after
  all.
- That is acceptable rather than fatal, because the frame's evidence does not depend on
  it: 86 of 92 files framed, **86 of 86 naming exactly the volume files present in
  their directory**, and every rival middle-word width framing zero. *A name join that
  gets the whole set right in every file is evidence in its own right.*

**The lane's boundary, stated once:** everything the shipped bytes and the IL2CPP
metadata can say has been said. Further progress on the payload needs the native loader,
and the project's existing note about HGP applies to that.

**Where this lane stands:** the index is framed and shipped at 86 of 92 with 20 tests;
the payload's container is **identified** rather than guessed, with every one of the
seven byte-statistic eliminations explained by the identification; the remaining work is
extents and element widths, and it is reachable with `tools/endfield-il2cpp`.

*Two batches of byte statistics eliminated seven containers and identified none. One
read of the type layout named the format, explained the residue, and resolved the
exceptions in a candidate relation. **When a format has a reader, read the reader.***

*Asking the shipped code what a format is called cost one metadata scan and moved this
further than two batches of byte-pattern search.*

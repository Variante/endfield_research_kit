# The containers more than one family shares

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1.** Two families that look unrelated -- terrain and chunk data -- arrive
inside the same container and the same custom LZ4 variant. Learning that layer
once saves re-deriving it per format, and it is why the terrain codec decodes
`InitChunkData` unchanged.

The serialization frameworks above this layer are covered in the lane that meets
them: schema-less FlatBuffers in
[`world_chunks_schema.md`](world_chunks_schema.md), the Wwise bank in
[`audio_bank_format.md`](audio_bank_format.md), and MemoryPack in
[`gameplay_semantics.md`](gameplay_semantics.md).

## The `TRET` container, decoded exactly

***Every file in the terrain block shares one container*** -- not just the `LAYER_*` families.
Over **2,500 files: 0 non-`TRET`, 0 decode failures**, version 1 in all, and
**`payload == file length - 20` in 2,500 of 2,500**, which fixes a 20-byte header:

| offset | field |
| --- | --- |
| `+0` | magic `TRET` |
| `+4` | version (always 1) |
| `+8`, `+10` | width, height |
| `+12` | mip count -- **1** for the per-chunk `Terrain_*` files (2,428), **11** for `LAYER_*` (72) |
| `+14` | format code |
| `+16` | payload size |

***The format code determines bytes per texel, exactly and with no variance.*** Over the
single-mip files:

| code | files | bytes/texel | seen on |
| --- | --- | --- | --- |
| 6 | 889 | **2.0** | `Terrain_*_C` (34^2), `Terrain_*_H` (65^2) |
| 8 | 329 | **4.0** | `Terrain_*_S` (132^2) |
| 100 | 552 | **1.0** | `Terrain_*_T` (132^2) |
| 101 | 658 | **1.0** | `Terrain_*_A`, `Terrain_*_N` (132^2) |
| 5 | 7 | 1.0, uncompressed | `LAYER_C` |
| 108 / 109 | 98 | 1.0, block-compressed | `LAYER_D` / `LAYER_N` |

*Each code yields a single value across every file carrying it* -- 889 files at exactly 2.0,
329 at exactly 4.0, and so on. **The per-chunk terrain maps are 34x34, 65x65 and 132x132
single-level surfaces; the layer maps are 1024x1024 with a full 11-level chain.**

## Terrain header

- **A terrain file is a compressed stream, not a header plus pixels.** The leading
  `u32` equals `payload + 20` -- the size of the *decompressed* record -- while the
  file itself is 50 to 250 times smaller. That is why the magic floats: `TRET` sits
  at offset 6 in 44,059 files but at 7, 8, 9, 10, 11, 17, 31 and beyond in 1,322
  others. The header is legible only where the compressor emitted it as literals.
- **Locate the header by its magic, never at a fixed offset, and try every
  occurrence.** Four bytes spelling `TRET` can occur inside compressed data; an
  occurrence is accepted only when the word after it is 1, the dimensions are
  nonzero, the mip count is at most 16 and `declaredTotal == payload + 20`. Under
  that rule **45,648 of 46,164 files frame**, up from 44,059 under the old
  fixed-offset reading. The remaining 516 are fenced as
  `headerNotLegibleInTheStream` -- their header is not contiguous in the file.
- **The record is 20 bytes**, not 26: `"TRET"`, `u32` 1, `u16` width, `u16` height,
  `u16` **mipLevels**, `u16` **formatCode**, `u32` payload. The two fields the
  earlier note called constants `1` and `6` are not constants at all.
- **`payload` is the whole mip chain, and it is predicted exactly.** Width, height,
  mip count and format code together give a byte total that matches on every one of
  the 45,648 framed files, zero exceptions, under one of two layouts: a linear
  bytes-per-pixel, or 4x4 blocks of a fixed size. `LAYER_*` textures are
  1024x1024 with **mipLevels 11** -- `log2(1024) + 1` -- and their payload is the
  full chain: 1,398,101 bytes at one byte per pixel.
- **The mip chain is what separates a block layout from a linear one.** A block
  chain costs a whole block for the 2x2 and 1x1 levels, so it lands 27 bytes above
  four thirds of its base. Format 5 hits 1,398,101 (linear, 1 B/px); formats 108
  and 109 hit 1,398,128 (4x4 blocks of 16 bytes). Neither could be told apart
  without the chain.
- **Formats 100 and 101 are ambiguous, and are reported as such.** They appear only
  at 132x132; 132 is a multiple of 4, so one byte per pixel and sixteen-byte blocks
  predict the same total. Nothing in these bytes separates them, so the audit names
  the ambiguity instead of picking one.
- **The channel in the file name decides `(mipLevels, formatCode)` exactly**, with
  no channel carrying two pairs: `C`,`H` -> `(1, 6)` at 2 B/px; `S` -> `(1, 8)` at
  4 B/px; `T` -> `(1, 100)`; `A`,`N` -> `(1, 101)`; `LAYER_C` -> `(11, 5)`;
  `LAYER_D` -> `(11, 108)`; `LAYER_N` -> `(11, 109)`. This *replaces* the older
  "channel letter decides bytes per pixel" claim with its mechanism: the name picks
  a format code, and the format code decides the layout.
- **Two name shapes ship here.** `Terrain_a_b_c_X.bytes` tiles carry the channel
  last; `LAYER_X_n.bytes` textures carry it in the middle and a **layer index**
  last. Reading the trailing token as a channel turns one channel into nine and
  drops the only files with a mip chain -- which is exactly what the earlier
  744-file "name not terrain shaped" bucket was.
- The six tile channels are exactly balanced: 7,570 files each across 37 scenes, so
  every tile ships all six.
- Read by `scripts/webui/assets/terrain_header.py`; report at
  [`reports/assets/terrain_header_current_latest.json`](../../reports/assets/terrain_header_current_latest.json).
  Terrain rows are `encrypted=False`, which is why a plain span read works here
  and not on the manifest.

## Terrain stream: LZ4 with big-endian offsets and a bit-interleaved token

- **The stream is an LZ4 block starting at offset 4, and its first literal run
  begins with the `TRET` record.** Ordinary LZ4 in every respect -- `0xFF`
  extension bytes summed with their terminator, match base 4, two-byte offset, a
  closing literal run no offset follows -- **except for two deviations: the match
  offset is big-endian, and the token's two 4-bit fields are bit-interleaved
  rather than split into nibbles.**
- The token byte `b7..b0` carries `literal length = b5 b4 b1 b0` and
  `match length = b7 b6 b3 b2`. The two fields are interleaved two bits at a time.
- **46,163 of 46,164 files decode to the byte** -- output exactly the declared
  size *and* input exactly consumed -- and all 46,163 agree with the file on the
  payload size and on the head of the record it carries in the clear. The
  remaining file is **stored uncompressed** and says so: magic at offset 0 and a
  payload size that accounts for the file exactly. Nothing is fenced.
- The payloads are real data, not flat fill: **27,524 carry nine or more distinct
  byte values** and 40,061 are aperiodic. That matters as evidence, for the reason
  below.
- The reading is discriminated, not merely workable. Scored identically over 4,000
  files against four controls -- offset little-endian, both plain-nibble readings,
  and the interleave with the fields swapped -- it closes 4,000 and **no control
  closes more than one**.

### Retraction: the nibble reading, and why 6,442 closures were worth nothing

- The previous conclusion here -- plain LZ4 nibbles, big-endian offset, 6,442 of
  46,164 closing -- **was wrong about the token**, and the closure count was not
  the partial success it looked like.
- **Every one of those 6,442 files was a flat tile**: 12 of the first 16 examined
  had a payload of one repeated byte, the other 4 of two. A flat tile is one
  literal run and one long match. Its sequence token is `0xFF`, and `0xFF` is one
  of only **four** byte values (`0x00`, `0x55`, `0xAA`, `0xFF`) on which the two
  readings agree. So the corpus that "validated" the grammar was exactly the
  corpus that cannot tell it from the alternative.
- The old decoder also never read the closing token. It hardcoded a six-byte
  remainder as `<token> <five literals>`. Five literals is precisely what `0x11`
  means **under the interleave** -- so a hardcoded constant stood in for the one
  token that would have exposed the reading. It was wrong wherever the closing run
  is not five bytes, which is about one file in five (5: 6,536 of 8,000; but also
  6, 7, 8, 9, 10, 11 and 12).
- Two eliminations recorded here previously were sound and are kept: it was **not**
  a preset dictionary, and **not** a free choice of endianness, nibble role or tail
  length per sequence. Both were correct. The conclusion drawn from them -- "the
  grammar contains an op that a token, literal run, offset and match length cannot
  express" -- was **wrong**: the grammar was complete, the token decode was not.

### How the interleave was actually found

- Not by enumerating conventions. By **measuring the unknown op**: parse the first
  sequence and the closing run, then tabulate (middle bytes -> output bytes still
  owed) across near-flat files, where the middle is a handful of bytes.
- Twenty rows were enough. `cc 08 c6 2c` owes 63; `cd 80 00 02 68` owes 124;
  `ce 0c 0c 00 44 6e` owes 131. Each parses as an ordinary sequence once you read
  `cc` as 0 literals, `cd` as 1, `ce` as 2, `cf` as 3 -- and `dc` as 4, which is
  what breaks the nibble hypothesis and forces the bit layout. Every row then
  closes to the byte with no residue.
- **The lesson, and it is the general one.** A structural claim validated only on
  the inputs that satisfy it trivially has not been validated at all. Before
  reporting a partial success rate, check what the *successes* have in common. If
  they are all degenerate, the rate is a measure of how much degenerate data the
  corpus holds -- not of how right the parser is. This is the second time the trap
  has been recorded in this repo and the first time it caught a live finding.
- **A warning about the shape of this problem, kept:** payload counts look almost
  reconcilable by hand and it is easy to fit one file. Accept a formula that closes
  thousands, exactly, and agrees with the file.
- Read by `scripts/webui/assets/terrain_stream.py`; report at
  [`reports/assets/terrain_stream_current_latest.json`](../../reports/assets/terrain_stream_current_latest.json).

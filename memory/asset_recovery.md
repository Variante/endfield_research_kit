# Asset recovery

This topic owns semantic bindings between exported Unity assets and Story,
characters, gameplay entities, world objects, audio, and video. The Assets page
only inventories browser-visible files; AnimeStudio only extracts them.

## Why this file remains

Cross-domain identity and ownership rules are reused by Map, Characters,
Gameplay, Audio, packaging, and the source graph. They therefore remain separate
from [`webui/assets.md`](webui/assets.md), which documents page publication, and
[`animestudio_recovery.md`](animestudio_recovery.md), which documents extraction.

## Current status

Asset extraction and discovery are strong. The project can index images,
models, materials, textures, shaders, animations, effects, audio, and video;
resolve many PathID-backed dependencies; and connect authored gameplay or Story
records to asset candidates with explicit provenance.

The main gap is semantic binding. Exporting an object does not prove its live
prefab composition, selected material variant, animation state, effect
activation, or placement time.

## Refresh

```bat
.\export.bat --from-game --with-assets
.\export_assets.bat
.\export_assets.bat --from-game
python scripts\build_assets.py
python tools\endfield_source_graph.py build
```

Asset modes, from narrowest to broadest, are `--focused-assets`,
`--default-assets`, and `--debug-assets`.

Primary outputs:

```text
export_full/recovered/AnimeStudio-cli/
export_full/structured/Audio/
webui/data/assets/index.json
webui/data/assets/gameplay_refs.json
webui/data/assets/story_media.json
webui/data/assets/videos.json
webui/data/lang/<LANG>/audio/index.json
webui/data/lang/<LANG>/audio/{events,media}.json
webui/data/lang/<LANG>/gameplay/sound_effects.json
reports/assets/
reports/source_graph/
```

## Evidence order

Prefer:

1. authored asset/prefab path or direct table key;
2. source root plus PathID/PPtr;
3. exported prefab/component dependency;
4. material-to-texture/shader reference;
5. exact controller, clip, effect, audio, or video consumer;
6. stable normalized identity;
7. labeled name/token similarity.

Preserve source roots, PathIDs, LOD/state suffixes, material slots, texture
roles, and evidence kind. Never treat a global PathID or similar filename as a
unique binding.

## Current strengths

- WebUI asset and Story-media indexes.
- Renderable asset-entity grouping for many models and prefabs.
- Material, texture, shader, controller, animation, audio, and video links.
- Compact Gameplay-to-image/model links and playable Wwise-event media
  candidates for projectiles, character skills, and bounded enemy ownership.
- Debug-only audio semantics that keep Wwise Event identity, numeric media id,
  and each physical `(storageRoot, relativePath)` occurrence separate. Same-id
  files in different folders or language/shared scopes remain visible instead
  of being collapsed by filename stem.
- Exact character post-model enumeration and baseline prefab generation.
- `chen` and `chenpast` are now kept as separate identities: the playable
  `chen` row owns the `P_actor_chen_*` model family, while the historical NPC
  `chenpast` row owns the independent `S_npc_major_chenpast_*` mesh family;
  their exported model PathIDs do not overlap. The WebUI manual merge that
  incorrectly folded `chenpast` into `chen` has been removed.
- Selected static world placements and gameplay/entity associations.

## CABMap container index

- **AnimeStudio's `Maps/*.bin` are CABMaps, not asset maps, and the format is now
  read byte-exact.** The framing comes from the writer itself --
  `AssetsHelper.DumpCABMap` in the submodule -- not from guessing at bytes: a
  .NET `BinaryWriter` stream of `string BaseFolder`, `int32 count`, then per entry
  a CAB name, a path, an `int64` offset, an `int32` dependency count and that many
  CAB names, with .NET's 7-bit encoded string length prefixes.
- Both current maps consume exactly to EOF: `endfield_persistent_assets.bin`
  (1,946 entries, 2,571,560 bytes) and `endfield_streamingassets_assets.bin`
  (254,723 entries, 47,318,490 bytes). Every CAB name is unique inside its file,
  which is what makes each map a map.
- **The dependency graph closes across the two maps, not within either.** Of
  661,808 edges only **3** name a CAB that appears nowhere. The persistent map is
  the reason to resolve across maps rather than within one: 10,025 of its distinct
  targets live in the streaming map and only 570 in its own, so a per-map check
  would report it as 95% dangling. 1,939 of its 1,946 CAB names also appear in the
  streaming map.
- **The CABMap offset is a physical byte offset into the `.chk`, and it lands
  inside a VFS logical file.** Joined against the VFS understanding ledger: all
  1,946 persistent entries land inside a ledger span, and 252,783 of 254,723
  streaming entries do. Two independently produced indexes -- AnimeStudio walking
  containers, the VFS audit walking blocks -- agree on where things are.
- **A coverage "hole" I reported here was my own bug. Retracted.** I compared
  *chunk filenames* and concluded the ledger never enumerated
  `VFS/0CE8FA57/4B06191A...chk` (222 MB, 1,053 containers). It does cover that
  content. Block `0CE8FA57` ships a **different chunk file in each VFS root** --
  `4B06191A...chk` under StreamingAssets, `F047E09F...chk` under Persistent -- and
  the ledger resolves each block from the **primary** root while the CABMap, built
  against StreamingAssets, names the fallback file. Both hold 1,053 containers.
  Same block, same count, different filename.
- Resolved by **block**, every block either map references is enumerated: nothing
  is missing in either direction. The check now keys on the block directory, and a
  test pins that so the filename comparison cannot come back.
- Two things worth carrying from the mistake. The repo already records that this
  VFS has two roots and that scans keyed on one silently mis-handle the other --
  **I hit the exact failure the notes warn about**, because I keyed a join on the
  most obvious identifier rather than the one the data is organised by. And I
  escalated it as a foundational problem before checking the sibling root, which
  is one `ls` away. **Check the cheap explanation before reporting a deep one.**
- **Every CAB is named by the logical bundle it sits in, and the relation is
  one to one.** Joining CABMap offsets to the ledger's logical-file spans names
  254,729 of 256,669 CABs, across 254,728 distinct bundles, of which **254,727
  hold exactly one CAB** and one holds two. The remainder split into 1,053 whose
  chunk is enumerated from the other VFS root and 887 whose offset falls inside no
  span; those two are counted separately because they are different situations.
- **Coverage and offsets need different join keys, and sharing one corrupts both.**
  Coverage keys on the *block*, because a block ships a different chunk file per
  root. Offsets key on the *chunk file*, because one block (`7064D8E2`) holds more
  than forty of them and merging their offset spaces invents matches. Keyed on the
  block, the join reported 256,601 names and "42 CABs in one bundle" -- a better
  looking number and a fabricated structure. The gate bounds both the one-to-one
  shape and the per-file maximum, since either bound alone passes a case it should
  not.
- **The CAB dependency graph is acyclic.** 254,732 nodes, 600,272 distinct edges,
  **zero back edges**, measured with an iterative walk rather than assumed.
  160,839 nodes have nothing depending on them and 141,896 depend on nothing. That
  a load order *exists* follows from this; which order the game actually uses does
  not, and is not claimed.
- 661,808 raw dependency entries reduce to 600,272 distinct edges, so **61,536
  entries repeat a dependency the same CAB already lists**. Both numbers are
  published: quoting only the distinct count misstates the file, quoting only the
  raw count misstates the graph. This is also why an earlier note said "661,808
  edges" -- that was the entry count, not the edge count.
- **Every CAB is accounted for, with exactly one documented exception.** 887 CAB
  *occurrences* sit at an offset the ledger does not enumerate; 886 of them are the
  same CAB *name* covered at its other occurrence, because a CAB appears once per
  VFS root and the ledger enumerates each block from one root only. One name is
  covered nowhere: `CAB-5dd5c779c787d592fb5184669bce5df9`, and it lives in
  `5B4A9EC7...chk` -- the chunk named by the ledger's single `shadowed_fallback`
  row. So the exception is a recorded shadowing decision, not a gap.
- **Judge coverage per CAB name, never per occurrence.** Per occurrence the same
  data reports 887 uncovered containers sitting in 865 unenumerated gaps, which
  reads like a large hole and is an artifact of the two roots. That is the third
  time in this domain that the two-root layout turned a correct measurement into a
  wrong conclusion; the other two were chunk-vs-block coverage and the CABMap
  offset join.
- Read by `scripts/asset_builder/cabmap.py`; report at
  [`reports/assets/cabmap_current_latest.json`](../reports/assets/cabmap_current_latest.json).
  This is a container index only -- it says nothing about the objects inside a CAB,
  their types, names or path ids, and an offset is not a readable object without
  the container format that sits at it.
- Note for anyone wanting a texture or asset inventory: this map does **not**
  provide one. That needs an AnimeStudio export; the `.bin` maps only locate
  containers.

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
- Read by `scripts/asset_builder/terrain_header.py`; report at
  [`reports/assets/terrain_header_current_latest.json`](../reports/assets/terrain_header_current_latest.json).
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
- Read by `scripts/asset_builder/terrain_stream.py`; report at
  [`reports/assets/terrain_stream_current_latest.json`](../reports/assets/terrain_stream_current_latest.json).

## Reading VFS logical files: three things that look like corruption and are not

- **A raw span read is only valid for `encrypted=False` rows.** The audio probe's
  `read_logical` seeks to a ledger row's offset, reads its length and checks the
  MD5. That works because every audio block is `encrypted=False`. Five block types
  are `encrypted=True` -- `BundleManifest`, `IFixPatchOut`, `JsonData`, `Lua` and
  `Table` -- and on those the same read produces a confident MD5 mismatch that
  looks exactly like a corrupt or stale file.
- **A chunk's filename is not the MD5 of its raw bytes.** `fileChunkMd5...` is not
  the raw-byte digest: checked across six chunks, including ones whose files
  verify normally, the filename never equals the raw MD5. So "filename does not
  match its hash" is **not** evidence that a chunk changed on disk. That control
  is cheap and worth running before concluding anything about a mismatch.
- **`manifest.hgmmap` is a Brotli stream**, so XOR-decrypting it yields no UTF-16
  and looks like a failed decrypt. `scripts/game_data/bundle_manifest.py` already
  frames it end to end -- headers, three fixed-width row regions, a variable region
  with counted UTF-16 fragments. Do not re-derive it.
- **There is no Python VFS decryption path, by design.** Encrypted blocks are
  decrypted by the AnimeStudio CLI during `dump`, and Python reads the structured
  output; that is why no script takes an `ivSeed`. Hand-rolling the XOR with the
  ledger's seed does not reproduce the file -- I tried, and the result is not a
  Brotli stream.
- So **naming bundles is not the cheap step I called it.** The current structured
  export covers only `table` and `json-data`, so the decrypted manifest is not on
  disk. The recipe is: dump with `--block-type BundleManifest` (the CLI's `list`
  confirms that name), then feed the decrypted `.hgmmap` to
  `scripts/game_data/bundle_manifest.py`, then join its names to the CAB-to-bundle
  relation above. The join is cheap; producing its input is an export run.
- All three cost time here because a wrong tool produced a plausible failure rather
  than an obvious one. **When a read fails, check whether the reader was valid for
  that row before believing the bytes are wrong.**

## Remaining gaps

- Exact runtime prefab assembly and entity-to-renderable ownership.
- Material keyword/pass/queue selection and runtime overrides.
- Native texture descriptors and mip payloads outside validated families.
- Animation/effect activation and controller execution.
- Modular NPC and VFX composition.
- World visibility/spawn policy.
- Broader exact audio/video trigger ownership.
- Runtime-selected Wwise switch/random media and stronger inferred
  skill/enemy sound ownership.

The goal is an evidence-first catalog, not a claim that every gameplay id has
one uniquely reconstructed renderable prefab.

# Where the installed data lives

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 1 -- the outermost layer.** Before any format question, this is what the
installed client exposes: which VFS blocks exist and which maintained reader
owns each payload family. Every other file assumes you know which block its
bytes came out of.

## Launcher patch downloads

The configured install is resolved from `endfield_paths.bat`; its game root
is the `Endfield_Data` directory, and launcher staging is beside it under
`launcher_tmp/<launcher-id>/`. An observed predownload uses
`predownload/<old-version>-<new-version>_file/` for archive parts and
`predownload/download_sdk_config` for the JSON download task. Read that task
to locate the actual package rather than assuming the launcher id or version
directory survives a future update. Its `file_list` records each part's
download filename and expected size; `total_size`, `version_id` and
`decompress_path` describe the package and configured extraction destination.
On observed download completion, the launcher moves the numbered archive parts
to the sibling `preload/` directory, retaining `.zip.<part>.tmp` filenames, and
clears the download task to an empty JSON array. Thus `decompress_path` does
not by itself mean extracted files: `preload/` can hold the completed encrypted
package. Completion and staging do not prove installation has occurred.

Direct reads of the first downloaded part prove ZIP local-file headers with
game-relative entry names. Inspected encrypted entries have method 99 and
the AES extra field (`0x9901`) identifying AE-2, AES-256 and underlying
Deflate. Filenames can therefore be inspected without decrypting contents;
payload extraction requires the appropriate password. Numbered `.zip` parts
form one package, and active download filenames carry temporary task suffixes.
An incomplete download cannot establish the complete archive inventory or
whole-package validity. Encryption observed in inspected entries does not
prove every entry uses it. A complete central-directory inspection established
AE-2/AES-256 on every non-directory entry in the observed package, with both
stored and Deflate inner methods; this is metadata evidence, not authenticated
payload validation. Read the numbered parts as one seekable byte stream to
inspect the directory without creating another full-size concatenated file.

The completed package contains client-relative binaries and control files
(`patch.json`, `delete_files.txt`, `game_files`, verification manifests), full
VFS catalogs/chunks under `vfs_files/files/Endfield_Data/StreamingAssets/VFS/`,
and `.chk_patch` payloads under `vfs_files/vfs_patch/diff_<new>_<old>/`.
This proves a mixed package layout; the chunk-patch algorithm, source/target
joins and deletion instructions remain unresolved until the encrypted control
files and payloads are read. The downloader task's patch flags alone cannot
exclude those chunk-patch members. Existing verified VFS catalog identities
can name their hash directories, but that join does not decode the new
catalogs or identify changed logical records, characters or Story content.

### Where to look for the archive password

Static inspection of the installed launcher's `Games.exe` gives two direct
anchors. `CLibNetworkUtils::ParseLatestGameJson` reads a JSON string field
`cd_key` into its parsed game info. `CDecompressAssist::Start` interpolates
a supplied nonempty password into `-p"%1"` for the bundled `7zg.exe`
extraction command. The complete join between those anchors is still
unresolved, so `cd_key` is a strong password candidate, not a recovered or
tested password.

Inspect the launcher's latest-game response (`/api/game/get_latest`, or the
`get_latest_game`/`batch_get_latest_game` messages supported by its launcher
API) and the response's `packs`, `patches` and `pre_patch` objects for that
field. Alternatively, the extraction process's password argument is a direct
observation point when the launcher actually unpacks the archive. Predownload
completion alone does not launch extraction. The observed download-task JSON
contains no password field; the launcher's `Cache/Config/Config` is not
plaintext JSON and its encoding remains unresolved. Account-login password
strings are a separate code path and do not establish an archive password.

The public HTTPS `launcher.hypergryph.com/api/game/get_latest` endpoint can
be read with the observed client fields `appcode`, `channel`, `sub_channel`,
`version` and `patch_encrypt=true`. Resolve the selected game's appcode from
its package/CDN identity rather than using the display name: the observed CDN
path's first segment selected the correct game's response. The response's
`pre_patch.patches` supplies part URLs, expected sizes and MD5s, which allow
transport identity checks without decryption. The queried responses supplied
no `cd_key`, including the fresh-install request and the request with launcher
fields; this observation does not establish that all endpoints omit it or
that it is withheld until release. Matching every part's checksum proves the
download matches that metadata, not that encrypted members have been
AES-authenticated or that their inner patch format has been understood. Keep
raw responses with signed URLs under `tmp/`, and checksum receipts under
`reports/launcher/`.

Separate package inspection from content recovery: a completed archive's
directory describes included physical files, while comparison of complete old
and new decoded exports describes recovered Story, character, map and gameplay
changes. Preserve the old export baseline before an installed-client refresh;
the maintained sync/Updates workflow is documented in `scripts/README.md`.
Predownload files are staging evidence, not the active `Persistent` overlay,
and must not be treated as installed-build native evidence. Package-specific
paths, sizes and inventories belong in `reports/launcher/`; the format and
interpretation boundaries above remain the durable record.

## The VFS blocks

The authenticated VFS audit locates every logical file by block, chunk, offset
and length and routes it to its reader. A `.chk` chunk is a physical container
that may pack many logical files, and location needs no payload: a block whose
chunks are not installed is still located, and its availability is reported
separately. The tracked per-block inventory (raw id, contents, lane, families,
path patterns) is `vfsBlocks` in
[`recovery_declarations.json`](../../scripts/webui/recovery/recovery_declarations.json);
which blocks the exporter decodes into `game/` and which it publishes undecoded
into `raw/` is `STRUCTURED_BLOCKS`/`RAW_BLOCKS` in
[`scope.py`](../../scripts/game_data/extraction/scope.py). Sizes and counts
live in the VFS audit report, not here.

| Block | Holds | Export | Reader; lane file |
| --- | --- | --- | --- |
| `Bundle`, `InitBundle` | Unity asset bundles | Unity objects (never dumped) | AnimeStudio; [`unity_assets.md`](unity_assets.md), [`containers_cabmap.md`](containers_cabmap.md) |
| `Audio`, `InitialAudio`, `Audio<Language>`, `HotfixAudio` | Wwise AKPK packages | decoded audio (never dumped) | AKPK/BNK readers; [`audio_overview.md`](audio_overview.md) |
| `Video` | CRI USM by directory | `game/Video` | outer framing only |
| `Table` | single-instance SparkBuffer config tables | `game/Table` | AnimeStudio dump |
| `JsonData` | plain JSON and MemoryPack payloads by root directory | `game/Json`, packed folders in `GameFiles.sqlite` | `jsondata_corpus`; [`extraction_payload_boundaries.md`](extraction_payload_boundaries.md) |
| `Lua` | base64+XXTEA-wrapped Lua | `game/Lua` plaintext | exporter unwrap |
| `Terrain` | TRET tiles and per-scene `LAYER_*` arrays | `game/` (`terrain-height` selects `_H` only) | `terrain/`; [`world_terrain.md`](world_terrain.md) |
| `Streaming` | `StreamingChunkInfo`, paired `InitChunkData`/`StreamingChunkData` | `raw/` | `streaming/`; [`world_chunks_schema.md`](world_chunks_schema.md) |
| `DynamicStreaming` | `fb_main_*`, `FBStreamArea`, `fb_init_*`, `fb_streaming_*`, `fb_version` | `raw/` | `dynamic_streaming`; [`world_dynamic_streaming.md`](world_dynamic_streaming.md) |
| `IV` | `index.bytes`, `iv_*` payloads, `regionIv_room_*` | `raw/` | `irradiance_volume`; [`world_irradiance.md`](world_irradiance.md) |
| `ExtendData`, `InitialExtendData` | `StringPathHash.bin`, `FacBoneTRS.bin`, `CompressData.bin`; `InitStringPathHash.bin` | `raw/` | `extend_data_binary`; [`extend_data.md`](extend_data.md) |
| `IFixPatch` | IFix code patches (the exporter names raw id 5 `IFixPatchOut`) | `raw/` | `ifix_patch`; [`ifix_patch.md`](ifix_patch.md) |
| `BundleManifest` | one Brotli `manifest.hgmmap` | `raw/` | `bundle_manifest`; [`extraction_payload_boundaries.md`](extraction_payload_boundaries.md) |
| `Audit*` | audit variants of Streaming, DynamicStreaming, IV, Audio, Video | shares the base block's folder | no separate content |

`raw/` bytes are shown by the Data page only; nothing builds from them, and
recovery tools stream those blocks from the installed client with
`AnimeStudio.CLI stream`.

## Payload families, and the reader each one routes to

The VFS recovery evidence index in the AnimeStudio skill reference maps each
family to its reader, fixtures and corpus report. How far each reader is
proven is [`extraction_payload_boundaries.md`](extraction_payload_boundaries.md);
the bullets below are the routing facts and the boundaries this file owns.

- **JsonData** routes through the `jsondata_corpus` family registry. LipSync
  has an exact 15-member MemoryPack layout whose six-float rows the native
  `LipSyncTrack._ConvertToAnimationCurve` consumer reads as Unity `Keyframe`
  values (`memorypack.lipsync`); lip-sync animation is distinct from
  language voice-audio availability, and playback selection is unproven. NPC
  MontageNew closes a complete named schema through EOF
  (`memorypack.npc_montage`); NPC PrefabInfo and the two NPC catalogs have
  exact JSON schema readers (`schemas.npc_prefab_info`, `schemas.npc_catalog`).
  Available TypeTrees do not cover MemoryPack JsonData.
- **SkillData** is a 48-member MemoryPack object (`memorypack.skill`).
  Exact-build native evidence resolves the resource type as `Core.SkillData`,
  field 0 as `actionGroupData` (nested `passiveEventActions` then
  `timelineActions`), and the five terminal members as two EOF-valid
  candidates that only a replayed live cursor receipt selects
  (`memorypack.skill_terminal`, `memorypack.skill_corpus`). Most current
  files close whole-schema that way; the residue keeps a named prefix, an
  authenticated terminal and opaque bytes past its first unsupported nested
  action tag. Registered static reader paths rank candidates but never select
  the runtime provider or close a parent. The registered `GameplayTag` reader
  stores `tagId` as `System.Int32` while the parser keeps an unsigned id view,
  so its signed interpretation stays open.
- **Video** has exact outer framing for the maintained corpus; container
  validity does not prove narrative attachment or playback.
- **Terrain** accepts the raw or length-prefixed inverted-LZ4 envelope and the
  versioned TRET prefix; `_H` records are row-major little-endian heights. The
  selected UnityPlayer reader consumes decoded offset 14 as `GraphicsFormat`,
  checks offset 16 against the allocated texture size and copies from offset
  20; every observed body has exact anonymous EOF-consuming ranges. Height
  scale, no-data, block channels, D/N ownership and rendering stay open.
- **ExtendData**: `CompressData.bin` is an absolute-offset archive of Brotli
  records whose bodies are strict UTF-16LE JSON NodeCanvas graphs (authored
  structure, not selected branches). The path-hash, facial-bone and manifest
  files have separate mmap or native consumers; their member names guide
  bounded parsers but do not prove complete byte layouts.

### Streaming (block 15)

- **StreamingChunkInfo** has an exact anonymous EOF graph with slot partitions
  from actual vtable positions. Standard rows hold one inline eight-byte pair
  and a counted vector of eight-byte pairs; their anonymous four-word
  projections uniquely match the same-directory secondary-file catalog among
  all permutations, keeping duplicates, missing paths and ambiguity. Legacy
  three-field roots are framed but unsupported by that projection, and no
  field is named. A separate native gate carries Info pairs through shared
  owner state, container pair equality, direct insertion guards and unchanged
  key assembly to the paired path formatters: conditional static value
  provenance, not a concrete runtime Info instance, every active-set mutation
  or spatial meaning (`layer3.infoCatalogRelation`,
  `layer4.infoKeyProducerStaticChain` in the `streaming.corpus` report).
- **InitChunkData/StreamingChunkData** have three exact anonymous subgraphs,
  not whole-file understanding: root field 2 through decoded EOF, parallel
  root fields 3/4/5, and paired fields 6/7. Init field 2 is an empty vector;
  Streaming field-2 rows are exact table/vtable layouts followed by counted
  scalar32 vectors, with present slots 0-5 spanning 4/4/4/8/24/4 bytes and no
  padding. Three-image native gates read them as scalar32, int32[2],
  float32[6] and a scalar32 key vector; names, key namespace and signedness
  are open. Filename relations are structural, not coordinates, and managed
  `GridData` names are candidates only. Parallel directories use equal-count
  width-4/1/4 vectors; row field 0 stays string-versus-byte-vector ambiguous,
  applicable row field-5 vectors are empty (nonempty fails closed), and row
  field 3 reaches another parallel directory.
- **Marker 17** bounds two wrappers and a counted opaque byte range. Its
  table-local directory keeps each key, marker, raw selector, serialized
  ordinal and wrapper/count range with logical-file provenance; duplicate
  keys stay ambiguous across markers, absent selectors are never defaulted,
  directory counts reconcile with framing counts, and a failed gate suppresses
  publication. The directory adds no owned bytes and names no body. Native
  construction, callback installation and publication of tag-5 bodies are
  pinned separately from execution, and the native reader checks neither
  source extent nor final cursor, so external-array equality stays
  conditional on an unavailable carrier. The tag1/4/6 profiles' fixed lengths
  match reviewed maximum read ends; bytes 30-31 are unread, not padding.
- **Marker 13 and marker 2** gaps start at a certified structural end and
  finish at the next certified start; other anonymous target addresses never
  define either boundary, and a physical gap is not a serialized `sizeof` or
  native EOF. Absent selectors are preserved as null after rechecking the
  row's field 2; the pinned slot-5 accessor default of zero is conditional on
  a new key, not a stored value. Marker 2 rebuilds the complete nested target
  directory, keeps unknown markers as raw slots (blocking occupancy closure),
  accepts any u32 structurally and refuses unseen exclusive gap lengths;
  native signed-positive loop use names no count. Constructor allocations or
  a presumed-valid runtime object never substitute for carrier and extent
  evidence.
- **Marker 15** targets occur under several key prefixes, not only the
  selector-5 `5,1,index` route. The reviewed default selector's first callback
  is a false stub; the later one uses the second root's row field 3 for one
  scoped context, with full-u32 key equality, collision probing, insertion and
  lookup native-gated. Native duplicates keep the first ordinal, while
  serialized joins reject ambiguity; unique keys yield bounded sixteen-byte
  candidate reads, and missing count keys stay explicit unsupported rows.
  Several targets often share one physical gap, and a gap can extend past the
  last target, so spacing is not a record end. The useful discriminator is a
  writer, or a selected consumer that carries the target pointer with a
  checked extent; for selector-9 keys it also needs the live mapping index and
  component-pool span, and applying the selector-5 reader there would cross an
  unproved dispatch boundary.
- **Pairs**: paired formatters make the first file Init and the second
  Streaming with identical root/dev/key inputs and one serialized ordinal
  (not runtime allocation order). New runtime keys use Init's marker; existing
  keys reuse a stored one. Live key-map state, overrides, scheduling and
  execution are not established by these bytes.
- The family-level native read closes requested and returned length, the
  exact-read success branch, first leaf `StreamingChunkInfo` and base-relative
  root resolution, then stays pointer-only. Static owner, handle and
  secondary-root chains do not supply a concrete runtime-root or
  scheduler-to-Create receipt. The native contract is
  [`streaming_field2_native.json`](../../scripts/game_data/contracts/streaming_field2_native.json).

### DynamicStreaming auxiliary roots

The five DynamicStreaming roots share `dynamic_streaming`; `fb_main_*` and
`FBStreamArea.bytes` have selected-build generated accessors and belong to
[`world_dynamic_streaming.md`](world_dynamic_streaming.md). The three
auxiliary roots keep a framing-only boundary here:

- `fb_init_*` and `fb_streaming_*` use the length-prefixed inverted-LZ4
  envelope and an eight-field anonymous FlatBuffer root.
  `dynamic_aux_pair_corpus` rejoins every pair to the VFS ledger and proves
  paired byte and count relations, the grouped-ID partition of root field 3,
  blob lengths equal to descriptor stride times ID count, and descriptor 21 as
  a stored name column clipped to 63 bytes. `dynamic_aux_bridge_native` checks
  the native handoff that reads first-root field 7 and second-root field 6.
  Other descriptor meanings, the selected provider, concrete file identity
  and live selection stay open.
- `fb_version` is a raw FlatBuffer with two scalars and an entry vector that
  is exact only when a native caller supplies its entry width.

## Reading VFS logical files: things that look like corruption and are not

When a read fails, check whether the reader was valid for that row before
believing the bytes are wrong. Each of these produced a plausible failure:

- **A raw span read is valid only for `encrypted=False` rows.** Seeking to a
  ledger offset, reading its length and checking the MD5 works for audio,
  whose blocks are unencrypted. `BundleManifest`, `IFixPatchOut`, `JsonData`,
  `Lua` and `Table` are `encrypted=True`, and the same read gives a confident
  MD5 mismatch that looks like a stale file.
- **A chunk's filename is not the MD5 of its raw bytes.** The ledger's chunk
  MD5 is a reference identity (`memorypack.corpus_gate` keeps it apart from
  the raw digest), so a filename that does not match its bytes is not
  evidence that a chunk changed.
- **`manifest.hgmmap` is a Brotli stream**, so XOR-decrypting it yields no
  UTF-16 and looks like a failed decrypt. `bundle_manifest` frames it end to
  end.
- **There is no Python VFS decryption path, by design.** AnimeStudio decrypts
  encrypted blocks during `dump`/`stream`, and Python reads that output; no
  script takes an `ivSeed`, and hand-rolling the XOR with the ledger seed does
  not reproduce the file. To read the manifest, dump it with
  `--block-type BundleManifest` (or run a page export that publishes it into
  `raw/`) and pass the result to `bundle_manifest`.

# AnimeStudio Reference

## Paths And Build

Local checkout:

```text
tools\AnimeStudio
```

Primary parent-repo build wrappers:

```bat
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\setup_vgmstream.bat
.\scripts\animestudio\rebuild.bat -Target CLI
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

`rebuild.ps1` uses the isolated SDK at `tools\AnimeStudio\.dotnet\dotnet.exe` unless `-UseSystemDotnet` is passed. Supported targets are `CLI`, `GUI`, `Patcher`, and `AllManaged`; common Endfield work normally needs only `CLI`.

Standalone build from `tools\AnimeStudio`:

```bat
dotnet restore AnimeStudio.CLI\AnimeStudio.CLI.csproj -p:RestoreIgnoreFailedSources=true -p:NuGetAudit=false
dotnet build AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -f net9.0-windows
```

## CLI Arguments

Entry point:

```text
tools\AnimeStudio\AnimeStudio.CLI\Program.cs
tools\AnimeStudio\AnimeStudio.CLI\Components\CommandLine.cs
```

Command shape:

```bat
AnimeStudio.CLI.exe input_path output_path --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType
```

Important options:

```text
--game              Required game name. Endfield uses ArknightsEndfield.
--logger_flags      LoggerEvent filters. Wrappers use Warning Error.
--types             Class filters, optionally Type:Parse, Type:Export, or Type:Both.
--names             Regex filters or a file containing regex lines.
--containers        Container regex filters or a file containing regex lines.
--map_op            None, Load, CABMap, AssetMap, Both, or All.
--map_type          XML, JSON, or MessagePack.
--map_name          Asset map file base name.
--unity_version     Override stripped Unity version.
--group_assets      ByType, ByContainer, BySource, or None.
--export_type       Convert, Raw, Dump, or JSON.
--key               XOR byte for MiHoYoBinData.
--ai_file           Resource index JSON for GI-style container recovery.
--dummy_dlls        Optional DummyDll folder for MonoBehaviour script schema recovery.
--object_index_jsonl  Compact object/schema/MonoScript JSONL sidecar for binary-first joins.
--filter_data       JSON list of source, offset, name, pathID, and type items.
```

`--object_index_jsonl` is opt-in and writes schema-v1 rows documented by
`AnimeStudio.CLI\Resources\ObjectIndexSchemaV1.json`. Use a unique sidecar per
CLI process. A consumer must reject a missing/non-terminal summary or
`complete=false`, and must globally uniqueness-check every external CAB
filename plus PathID before accepting a runtime-resolved external PPtr.
When the index is enabled for MonoBehaviour or PlayableDirector JSON, the CLI
also parses GameObject and Transform dependencies without exporting them.
Component object rows may then include `sceneContext`: exact GameObject and
Transform identities, hierarchy path, local/world position, and a
`worldPositionStatus`. Only `exact_transform_hierarchy` is a complete world
position; unresolved parents, cycles, and depth limits remain explicit gaps.

For a complete Story/all wrapper run, pass `--animestudio-object-index`
directly to `scripts\export_full_from_game.py`. Relevant MonoBehaviour and
PlayableDirector workers receive unique part paths. The deterministic merger
publishes, per source:

```text
<source>\object_index\parts\*.jsonl
<source>\object_index\objects.jsonl.gz
<source>\object_index\schemas.jsonl.gz
<source>\object_index\summary.json
```

`summary.json` is the last-written commit marker. Loading fails closed on
missing or malformed stage provenance, content-hash mismatches, stale current
source/CLI provenance, incomplete parts, conflicting physical identities, or
ambiguous external CAB-filename/PathID targets. CLI provenance covers the
apphost and first-party `AnimeStudio*.dll` implementation assemblies; optional
DummyDll provenance uses per-file content hashes. Story/all refreshes
invalidate an old marker before carrier workers start. Asset-only and
`--skip-animestudio` runs cannot publish this broad index.

`--types` replaces the default App.config parse/export surface. It does not layer on top of defaults. If GameObject or Animator export is selected, the CLI also parses dependencies such as Texture2D, Material, Animator, or GameObject as needed.

The Endfield fork names the installed native HGGraphics class IDs `HGTree`,
`HGTreeData`, `HGMeshRenderer`, and `HGMeshRendererData`. These may be used in
`--types` like built-in classes. Minimal AssetMap generation retains a generic
TypeTree object only when its export-enabled native type is explicitly
selected; this supports bounded native-type censuses without broadening normal
production maps.

## Integrated VFS Commands

The CLI also exposes the Endfield VFS subcommands used by the WebUI pipeline:

```bat
AnimeStudio.CLI.exe dump --streaming-assets path\to\StreamingAssets --output export_full\structured\StreamingAssets --fallback-assets path\to\Persistent --block-type table --block-type json-data
AnimeStudio.CLI.exe dump --streaming-assets path\to\Persistent --output export_full\structured\Persistent --fallback-assets path\to\StreamingAssets --block-type table --block-type json-data
AnimeStudio.CLI.exe audio --streaming-assets path\to\StreamingAssets --output export_full\structured\Audio\CN --language chinese --block all
AnimeStudio.CLI.exe stream --streaming-assets path\to\StreamingAssets --block-type audio --file-regex banks\.pck
AnimeStudio.CLI.exe vfs-index --streaming-assets path\to\StreamingAssets --output export_full\recovered\AnimeStudio-cli\StreamingAssets\vfs_index\bundle_vfs_index.json --block-type bundle
AnimeStudio.CLI.exe vfs-index --jsonl --streaming-assets path\to\StreamingAssets --output tmp\updates\source_scan\streaming.jsonl
AnimeStudio.CLI.exe list
```

`dump`, `audio`, `stream`, and `vfs-index` accept `--fallback-assets`; `dump`,
`stream`, and `vfs-index` accept repeated `--block-type` flags plus repeated
`--file-regex` filters. The fallback is consulted for `.blc` block metadata and
`.chk` payloads; the WebUI wrapper configures StreamingAssets and Persistent as
sibling fallbacks in both directions. `stream` writes matching file payloads as JSONL base64.
The `audio` command defaults to direct lossless FLAC. The pinned repo-local
vgmstream CLI decodes WEM to a PCM pipe consumed by the in-process CUETools
FLAKE encoder, without an intermediate WAV file. `setup_vgmstream.bat` installs
the decoder under `tools/vgmstream/`; `ANIMESTUDIO_VGMSTREAM_CLI` remains an
explicit override. Use `--format wav` or `--format wem` only when that
compatibility output is explicitly required.
`vfs-index --jsonl` writes compact streaming metadata records while its default
output remains the existing JSON document.
`list` prints the known dumpable VFS block types. The WebUI wrappers default to this same
AnimeStudio executable:

```text
scripts\export_full_from_game.py  DEFAULT_STRUCTURED_DUMPER = DEFAULT_ANIMESTUDIO
scripts\build_audio.py            DEFAULT_AUDIO_DUMPER = DEFAULT_ANIMESTUDIO
```

### VFS recovery evidence index

Use this index before starting a new format or semantic investigation. It
separates three evidence layers:

1. `reports/animestudio/vfs_understanding_latest.md` plus its JSON and gzip
   ledger certify the installed-build logical-file boundaries and hashes.
2. `reports/animestudio/vfs_payload_understanding_latest.md` records current
   payload-family framing, exact-consumption gates, corpus coverage, and
   unresolved sections.
3. `reports/animestudio/vfs_understanding_audit_latest.md` is the detailed
   design/diagnostic audit and recovery queue.

The stable code and fixture entry points are:

| Family | Maintained reader or classifier | Focused fixtures |
|---|---|---|
| VFS catalog, overlay, hashes | `AnimeStudio/Endfield/Vfs/EndfieldVfsLoader.cs`, `EndfieldVfsCorpusClassifier.cs`, CLI `vfs-audit`/`vfs-profile` | `AnimeStudio.CLI.Tests/Program.cs`, `AnimeStudio.CorpusClassifier.Tests` |
| Bundle / InitBundle inner container | `AnimeStudio/VFSFile.cs`, `AnimeStudio/Crypto/VFSUtils.cs`, CLI `vfs-inner-audit` | `VFSFileType5Tests.cs`, `VFSDirectoryInfoTests.cs`, `VFSInnerStructureTests.cs`, `StreamExtensionsTests.cs` |
| BundleManifest | `scripts/game_data/bundle_manifest.py` | `scripts/tests/test_bundle_manifest.py` |
| IFixPatchOut | `scripts/game_data/ifix_patch.py` and the selected-build native contract | `scripts/tests/test_ifix_patch.py`, `test_ifix_patch_contract.py` |
| Streaming | `scripts/game_data/streaming.py`, `scripts/game_data/streaming_corpus.py`, `scripts/game_data/streaming_native.py` | `scripts/tests/test_streaming.py`, `scripts/tests/test_streaming_corpus.py`, `scripts/tests/test_streaming_native.py` (all envelopes/roots, exact anonymous Info graphs, field-2 row slot partition plus terminal field-5 scalar32 vectors through EOF, selected-build native-gated fields 0--5 representations, family-level carrier base/length, and current filename-token relations, field3/4/5 first-level, and field6/7 paired-group subgraphs; concrete authenticated-file/final-cursor join, field names, field-5 key namespace/signedness, deeper parallel field-5 children, and semantics remain unresolved) |
| DynamicStreaming | `scripts/dynamic_streaming.py` | `scripts/tests/test_dynamic_streaming.py` |
| Irradiance volume | `scripts/game_data/irradiance_volume.py` | `scripts/tests/test_irradiance_volume.py` (region framing, bounded index filename tables, and single/grouped v3 index-directed payload ranges) |
| Terrain | `scripts/terrain_tret.py`, `scripts/game_data/terrain_native.py`, `scripts/game_data/terrain_corpus.py` | `scripts/tests/test_terrain_tret.py`, `test_terrain_native.py`, `test_terrain_corpus.py` (current native gate, exact selected-build tiling, negative framing/provenance fixtures; unsupported shapes fail closed) |
| Table / SparkBuffer | `AnimeStudio/Endfield/Extraction/EndfieldSparkBuffer.cs` | `EndfieldSparkBufferTests.cs` |
| JsonData / LipSync | `scripts/game_data/memorypack/lipsync.py` | `scripts/tests/test_memorypack_lipsync.py` |
| JsonData / gameplay subfamilies | `scripts/story_builder/*_binary.py`, `scripts/game_data/memorypack/`, routed per virtual-path family | matching `scripts/tests/test_*_binary.py`, including `test_jsondata_binary.py`; current SkillData/BuffData and LevelData/LevelScriptData partial framings stay non-exact |
| JsonData / NPC Montage | `scripts/game_data/memorypack/npc_montage.py`, `scripts/game_data/memorypack/npc_montage_corpus.py` | `scripts/tests/test_memorypack_npc_montage.py`, `scripts/tests/test_memorypack_npc_montage_corpus.py` (authenticated current ledger/stream join; exact EOF gate; report: `reports/animestudio/npc_montage_current_latest.{json,md}`) |
| ExtendData / CompressData | `AnimeStudio/Endfield/Extraction/EndfieldCompressData.cs`, `scripts/game_data/extend_data_binary.py` | AnimeStudio CLI fixtures and `scripts/tests/test_mmap_extend_data.py` |
| Lua | `AnimeStudio/Endfield/Extraction/EndfieldLuaDecoder.cs` | AnimeStudio CLI fixtures plus the `lua-sweep` mode |
| Video / USM | `AnimeStudio/Endfield/Extraction/EndfieldUsmConverter.cs` | AnimeStudio CLI USM framing fixtures |
| Audio / AKPK-Wwise | `AnimeStudio/Endfield/Audio/EndfieldAkpkPackage.cs`, CLI `audio-audit`, `scripts/build_audio.py` | `EndfieldAkpkTests.cs` plus audio-domain tests under `scripts/tests/` |

The mmap ExtendData reader proves file-provided counts, fixed record widths,
bounded string/TRS ranges, observed lookup/table overlaps, non-overlap of
owned value ranges, and exact EOF. FacBoneTRS now self-bounds its complete
lookup, unit, bone, and 64-byte value pools; hash roles and the 64-byte value
meaning must not be promoted without independent semantic evidence.

Changing counts, hashes, source roots, and per-file failures belong in the
reports or `tmp/animestudio/`, not in this reference. A parser may be promoted
from observational to exact only after bounded positive fixtures, malformed /
truncated / trailing-byte negatives, and a current-corpus sweep. Keep envelope
framing, authored field names, cross-file ownership, and observed runtime
behavior as separate claims. For a future client update, rerun the boundary
audit first and use its input-set fingerprint for every downstream census.

For nested Bundle/InitBundle container work, run the structural gate directly
before Unity object loading:

```bat
AnimeStudio.CLI.exe vfs-inner-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --block-type initial-bundle --block-type bundle --output reports/animestudio/vfs_inner_understanding_files_latest.jsonl.gz --summary-json reports/animestudio/vfs_inner_understanding_latest.json
```

`inner_structure_verified` proves exact outer extraction/FileDataMd5, custom
VFS header and block-info framing, block decompression sizes, directory path
and interval validity, non-overlap, and exact node reads. It does not prove
serialized Unity object boundaries, TypeTrees, PPtrs, or gameplay meaning. The
decoded custom-header `size` word must remain unnamed unless a specific flag
uses it; current files disprove treating it as the logical container length.

For Terrain work, first rebuild the outer VFS audit and pass its exact
`inputSetSha256` to the maintained corpus gate:

```bat
python -m scripts.game_data.terrain_corpus --outer-summary OUTER.json --outer-ledger OUTER.jsonl.gz --expected-input-set-sha256 SHA256 --game-root ENDFIELD_DATA --output-json reports/animestudio/terrain_tret_latest.json --output-md reports/animestudio/terrain_tret_latest.md
```

The gate revalidates the current `GameAssembly.dll`, `global-metadata.dat`, and
`UnityPlayer.dll`, the pinned reader/footprint byte ranges, GraphicsFormat enum
rows, outer ledger hash, every selected logical-file range/hash, and exact TRET
EOF consumption. The reader proves offset 14 is GraphicsFormat, offset 16 is
the checked payload length, and offset 20 is the copy source; its ABI has no
input length or final source cursor, so it cannot replace the outer/body-length
checks. Selected-build words 108/109 use 4x4, 16-byte BC7 footprints. Keep the
range contents, D/N ownership, channel meaning, texture-array slot, and runtime
selection unresolved.

For BundleManifest field recovery, first require all three corrected
size/count-delimited fixed-width sections and the repeated-size terminal
variable envelope to consume exact EOF, then join the manifest to the current
inner ledger before consulting generated AssetMaps. One anonymous record span
consumes sequentially from payload offset zero and the 48-byte rows' four
relative pointers bound a second span; both use UTF-16/count-u32 components and
have the same record multiset under different orders. All component meanings,
ordering roles, and terminal bytes stay unnamed. Equal table/file
counts, exact bundle-name multiplicity, and a numeric row-index sequence are
structural witnesses, not serialized field ownership. Reject an AssetMap as current-build
evidence when any recorded source chunk does not join the authoritative outer
ledger; do not infer field names from managed field order or row size.
Exact-build ManifestDataBinary method pins are not sufficient for a runtime
receipt when the stream or ref/out result carriers remain unresolved inflated
type specs. Resolve and test the ABI first; never derive it from field names,
managed native size, or call appearance.

For a low-output current-corpus SparkBuffer framing check, build the CLI test
project and run:

```bat
AnimeStudio.CLI.Tests.exe table-sweep PERSISTENT STREAMING_ASSETS tmp\animestudio\table_sparkbuffer_sweep.json INPUT_SET_SHA256
```

The sweep uses the maintained VFS loader, verifies each decoded FileDataMd5,
records the selected primary/fallback chunk and exact bytes read, invokes
`EndfieldSparkBuffer.ParseBytes`, and requires exact EOF for every metadata
declaration. Any file failure or count mismatch writes a structured report and
returns nonzero. Treat the supplied input-set SHA as a provenance label: obtain
it from the current `vfs-audit` report and reject the result during review if it
does not match; the sweep does not compute that aggregate fingerprint itself.

For shared/CN audio package work, run the low-output structural gate before
event/HIRC semantics:

```bat
AnimeStudio.CLI.exe audio-audit --streaming-assets PERSISTENT --fallback-assets STREAMING_ASSETS --output tmp/animestudio/audio_structure_audit.json
```

The default audit covers `InitAudio`, `Audio`, `AuditAudio`, `HotfixAudio`, and
all language audio blocks. A verified row
proves bounded AKPK sectors, bank/media intervals, BNK/DIDX/DATA framing,
required decryption, and RIFF/RIFX or PLUG envelopes. It does not prove HIRC
behavior, posted events, selected media, or audibility. Any audio block whose
declared chunks are all absent from both roots emits an explicit
`excluded_missing_audio` terminal row and does not fail; if any chunk exists,
the block enters normal parsing and partial absence or corruption fails.
Use `--hirc-only` for a lower-I/O BNK/HIRC census. It skips media magic checks
but still authenticates the selected VFS files and requires exact BNK section
and HIRC object consumption. Preserve numeric HIRC type IDs; object-envelope
framing is not object behavior, event selection, or audibility.
Numeric HIRC type `0x02` additionally has a bounded 14-byte source prefix and,
for plugin type `0x02`, a checked length-prefixed parameter range. Its body is
now consumed whole by a separate anonymous nine-group frame that must reach the
declared object-body end; run it through the same corpus gate and read
`reports/animestudio/hirc_type02_body_current_latest.md` before assuming the tail
is still unframed. The same nine groups are shared with numeric types `0x07`
and `0x05`: `0x07` adds one terminal counted vector of four-byte anonymous
references, `0x05` adds a fixed 24-byte opaque block plus two independently
counted vectors. Numeric type `0x06` shares them too and adds three counted
vectors, of which only the first resolves whole-corpus to same-bank identities;
the other two are published as `candidateWords` with their shortfall, never
joined. One maintained reader and one corpus lane frame all four, so
extend those rather than adding a parallel copy. Widths that stay unresolved must keep failing closed: group B has
no nonempty sample in any framed type, and group E's selector `0x02` is
unobserved, so bit-1-only and both-bits-set tie. Selector `0x01` does occur and
disproves a bit-0 rule, but in only 4 of 48,740 type `0x07` objects. The group I
anonymous key is variable-size, not a fixed byte, and the group H state is a key
plus its own counted six-byte elements, not a fixed twelve. Both fixed widths
survived whole corpora as degenerate cases, so a one-dimension sweep reporting a
width as uniquely determined proves only that no observed shape contradicts it.
Re-check every width when a new type enters, and read the published
`groupIKeyWidth_*` and `groupHStateWidth_*` histograms rather than assuming the
inherited five-byte varint cap is a corpus fact. Exact consumption is byte extent only;
keep group letters, selector bits, keys, values, and reference targets anonymous
until a serializer or consumer witness assigns them.
The reference vectors of numeric types `0x04`, `0x05`, `0x06` and `0x07` are the
one place this corpus reaches layer 4: every value resolves to exactly one object
identity declared by the same bank, and
`hirc_reference_graph_current_latest.md` carries the numeric edge counts plus a
per-type referenced-versus-population table. Treat that as identity resolution
only. The one direction it establishes is physical -- which object's body holds
the value -- and over that the relation is acyclic with at most one holder per
target. That is not parenthood, containment, membership, a tree or a root. Before extending it,
re-run the gate: it refuses to publish unless every reference names exactly one
unambiguous same-bank object, duplicate-id targets included.

Numeric type `0x16` is framed byte-exact (778 bodies, 16,635 bytes) and is worth
copying as a method: a byte count, that many one-byte keys followed by that many
four-byte values as two parallel runs, one anonymous byte, then the node frame's
group I structure verbatim. Most of it was already proven, so before decoding a
small type from scratch, check whether it ends with a structure another type
already closes. It shares only group I, so it carries only the group I residuals,
and its selector families are per-element -- one observation per counted thing --
and reconcile against their own counters rather than the body total.

Numeric type `0x0E` is framed byte-exact too, but on its own terms: it does not
use the node frame at all, so it must not inherit the node frame's residual list,
its group widths, or its unconditional selector families -- the lane framework now
takes all three as parameters, and reusing the node-frame defaults for `0x0E`
would publish claims about groups its bodies never contain. Layout: a fixed
21-byte head, a 20-byte block present only when body byte 1 is 1, 19 opaque bytes,
a byte-counted list of entries each carrying a selector byte, a `u16` element
count and that many 12-byte elements, then two closing bytes that must read as
zero. The prefix length is **read from that flag byte, never searched for**: a
shape sweep alone leaves thousands of bodies with two offsets that both consume
exactly, and only the flag removes the ambiguity. This lane also carries a
closed-form byte identity rather than the containment inequality the node-frame
lanes use, so a miscount breaks an equation instead of being absorbed. Before
extending it, check the minority branch the way this one was checked -- 164 bodies
across 89 banks with 21 distinct blocks, not one sample repeated.

The music types `0x0A`-`0x0D` are attempted and unframed; do not restart from
scratch. They do not open with the node frame, and searching for an offset where
the frame parses is worthless because every music body admits several such
offsets -- the frame is permissive, so "it parsed" is nearly no evidence. A
structural predictor is needed, the way byte 1 predicts the `0x0E` prefix.
The source id in a numeric type `0x02` bounded prefix names a media file the
corpus ships, and **the plug-in id decides whether it does** -- two ids always
resolve, five never, none both. Report the partition rather than the ~98% rate,
which hides it. Union the media ids across every package before joining: a bank's
media usually lives in another package, so a per-package join matches 12 of 75,958
and is worthless. The whole plug-in id decides, not its low nibble.

The HIRC serializer ships with the game: `Endfield_Data/Plugins/x86_64/
AkSoundEngine.dll` is built from **Wwise SDK v2023.1.17** (that string occurs 28
times and is the only version in the binary), against a vendored tree at
`E:\Engine\RM42.Beyond\Audio\Wwise\SDK`. Treat a stock 2023.1.17 layout as a
strong prior, not ground truth. The binary names no bank structures -- only the
chunk tags -- so string-mining it further will not yield layouts; its value is the
version. Where this corpus leaves a width genuinely tied, that SDK is the witness
that would settle it.

Numeric type `0x12` remains unframed and several readings are already eliminated:
not the `0x10`/`0x11` grammar (all 251 fail on the section size), not the `0x16`
shape, and chained counted blocks close only 8 of 251. Its leading word is not a
reference field -- it names nothing in 119 of 251 bodies -- so do not gate it like
the `0x08`/`0x0A`/`0x0C`/`0x0D` heads. A fixed-21-byte-tail reading fits two sample
bodies and fails on the corpus; work from the end-aligned census instead, where
bytes -5..-3 are zero everywhere.

Numeric types `0x13`, `0x14` and `0x15` are framed byte-exact but on 4, 9 and 5
bodies respectively, so read their report before relying on them: `0x13`/`0x14`
are a four-byte-value block, an eight-byte-value block, then two bytes, and `0x15`
is the `0x10`/`0x11` header plus eight bytes. The eight-byte width rests on the 6
bodies that carry a nonempty second block, and the gate refuses an all-empty
corpus so the width cannot pass unwitnessed.

Numeric type `0x09` is opened by the shared node frame in all 5,158 bodies; after
it come a counted four-byte run and a second count, and where that count is zero a
single byte closes the body -- 4,973 of them, now gated. The recovery memory
records a better layer grammar reaching 5,154, but it exists only as prose and a
later attempt could not reproduce it from 48 swept variants, so the shipped census
is the weaker verified one. Record grammars as widths and offsets, not sentences.

Numeric types `0x11` and `0x10` share one grammar: an eight-byte header whose
second word sizes an opaque section, one byte, group I, a 16-bit flag, then a
counted run of six-byte elements. 2,983 of 3,098 bodies close exactly. Type `0x10`
was never decoded on its own -- its header matched, the existing grammar was tried,
and 430 of 453 fit; its 23 stragglers all carry third byte `0x7F` and are fenced
under their own reason, which applies to `0x10` only. Do not try to close the other 92:
when the flag is set, block widths 21 and 27 both consume every flagged body
exactly (27 swallows the run's single element and reads a zero count), and the
flag is never above 1, so nothing in this corpus separates them. That is a tie,
not a gap, and it is fenced as its own outcome rather than failed or guessed.

Numeric type `0x08`'s leading word is null or names exactly one same-bank object
(157 resolve, 4 null, 0 unresolved over 161 bodies); null is an allowed outcome
for this type, unlike the music head where it is not. `0x08` is not framed: its
key/value block matches `0x16`'s, and after it a one-entry list whose key sizes
the value (`0x15` -> 11 bytes, `0x1D` -> 27) plus a recurring
`02 e8 03 00 00 00 00 c0 c2` signature explain 148 of 161 bodies and no more.
Types `0x10`, `0x11` and most of `0x12` do not share that head at all.

Type `0x0B` opens with a byte, a 32-bit record count, and that many fourteen-byte
source records; every one of the 4,447 records carries a plug-in id numeric type
`0x02` also uses, which is what evidences the stride -- plug-in ids are sparse, so
a wrong stride leaves the set at once, and the 230 records after a body's first
are the ones that test it. Do not extend this to a frame: the 88-byte entries that
follow consume only 2,221 of 4,325 bodies exactly, 248 of their words name no
declared source, and the node frame reaches EOF from there in 2 bodies.

Types `0x0A`, `0x0C` and `0x0D` share a head and carry one gated reference each:
body byte 2 selects the offset of a 32-bit word (0 -> offset 9, nonzero -> offset
5), and under that rule 7,326 of 7,331 bodies name exactly one same-bank object.
The five exceptions are `0x0C` bodies whose *first* byte is 6, a head shape
neither branch fits; they are excluded from the claim but kept in the denominator. Fixing the offset at 9 instead
resolves only ~97%, which looked like missing references and was not -- when a
rule is nearly always right, look for the byte that makes it always right before
recording a limit. When probing them, mirror the node frame in
Python under `tmp/` and prove the mirror against an already-closed type first --
the current mirror reproduces all 48,740 type `0x07` bodies exactly, which is why
its music-type failures can be believed.

One endpoint now has a witness. `scripts/audio_semantics/hirc_named_reach.py`
hashes the exact audio-like `stringLiteral` rows out of `global-metadata.dat`
with FNV-1 over UTF-16 code units and joins them to HIRC object identities. Every
current match lands on numeric type `0x04` and none on any other type, which is
what identifies `0x04` as the object shipped managed code addresses by name; the
type is only about seven percent of the corpus, and the gate measures that share
from the reader's own histogram rather than asserting it. Treat a single match on
another type as dissolving the identification, not lowering a rate -- the gate
refuses to publish in that case. Walking reference vectors from a named object
reaches the type `0x02` source ids, but the walk also crosses the type `0x03`
target word, which is *not* a gated reference vector, so report it separately.
Edges leaving the bank are counted and never followed. Nothing here names any
object but the `0x04` entry point, and none of it establishes playback,
ordering, selection, mixing, or audibility.

For IV recovery, region, index filename-table, and index-directed payload
framing are distinct claims. `parse_index_bytes` proves one unambiguous count-
prefixed UTF-16LE `iv_*.bytes` filename table. For supported single/grouped v3
indexes, the indexed-payload framers accept a directory only when filename-
ordered groups uniquely cover each authenticated payload from zero through EOF
without gaps or overlaps. Candidate starts may be absolute-four-byte aligned or
four-byte aligned relative to the filename-table end, but the combined
candidate set must still be unique. All non-range words and surrounding bytes
stay opaque. Legacy indexes use a separate unique EOF-ending record directory
whose filename-ordered groups must also tile each authenticated payload.
Preserve numeric magic values until consumer evidence supplies stable names.
Do not add a generic `ReadFile`/CRT capture for the remaining payloads. A narrow
UnityPlayer parser/cursor candidate exists, but a capture must still pin exact
build hashes, RVAs, entry bytes/body hashes, resolver/caller gates, path/hash
carrier, payload base/length, and final cursor/result contract; otherwise the
observation cannot join back to one authenticated VFS logical file. A capture
preflight mismatch is failed evidence and must be fixed before asking the user
to run the game. The current native parser signatures carry no payload length
and perform no final cursor/EOF comparison. Their numeric magic values recur
inside the same payloads, so signature scanning cannot substitute for those
missing bounds or establish a record start.

For BuffData tag `0x1B`, run `python -m scripts.game_data.memorypack.buff_1b_corpus --expected-input-set-sha256 CURRENT_VFS_INPUT_SET_SHA256`.
It rebuilds the current BuffData census, verifies the selected tag byte against
its authenticated VFS logical file, and joins the exact-build selected action
reader. Runtime provider selection, action meaning, suffix ownership and whole
BuffData EOF remain unresolved. Negative coverage lives in
`scripts/tests/test_memorypack_buff_1b_corpus.py`.

For SkillData work, run `python -m scripts.game_data.memorypack.skill_corpus`
against the current outer summary, ledger, and input-set SHA. Historical
export-backed censuses cannot be rebound by supplying a newer boundary report.
The gate joins current VFS stream bytes to the complete selected ledger set;
member counts and metadata field-name sets are discovery gates only. The
maintained SkillData framer enumerates direct-counted and wrapped terminal
candidates independently, including empty wrappers. A unique candidate is only
unique within that supported grammar, not proof of the actual formatter cursor.
Keep the prefix opaque and multiple starts or branches ambiguous. BuffData
work likewise requires a provenance-matched census rather than a historical
count. Its member-18 stacking-action framer proves only its anonymous
marker/extent/EOF contract and must keep intermediate bytes and field order
opaque. Do not label a family semantically decoded until nested unions, field
order, bounds, and EOF consumption are covered by maintained positive and
negative tests plus a full current sweep. For LevelScriptData and LevelData,
maintained prefix/suffix
framers may expose exact ranges with an opaque middle, but an apparent tail at
EOF remains insufficient for whole-schema status: the complete top-level
object and any ActionSerializedMap must be consumed first. AnimationConfig may
similarly expose an anonymous common prefix or exact small frame while leaving
the remaining payload explicitly opaque.
Historical lightweight v29 tooling failed to resolve generic types and used an
invalid registration witness; this is not proof that the current registration
lacks MethodSpec data. Revalidate the selected native inputs and unique
registration before mapping formatter/wrapper methods. A direct method pointer
still does not establish ref-reader ABI, nested read order, or a final cursor.
Do not promote setter declaration order or the union-tag registry to serialized
cursor order without complete current method bodies or a bounded trace.
For residual JsonData prioritization, the historical
`tmp/animestudio/jsondata_unclassified_family_census_20260903.json` supplies
family leads, not a current denominator without a ledger rejoin. Do not treat SkillData's uniform
`30 02` prefix as more than a 48-member envelope witness.
Use the payload-understanding report's current blocker/evidence pointers before
adding another family-specific probe.

`export_assets.bat --from-game` writes the lightweight bundle VFS index
through `vfs-index`, then decodes CN audio through `audio` before relinking
browser conversations.

The canonical post-Story map phase also runs
`recover_map_streaming_instances.py --all-published-map-scenes` before map
preview rendering. This uses AnimeStudio.CLI `stream` against the installed
game's `Streaming` blocks to recover exact `InitChunkData` matrices, then joins
the current exported AssetMap and Mesh OBJ files. Colored top-down surfaces and
point samples additionally require the Material JSON and Texture2D outputs
provided by the default asset scope. A stream/sidecar failure stops the map
task; it is not silently replaced by sparse registry points.

`export.bat --changed-only` uses `vfs-index --jsonl` to compare focused
structured logical files by decoded MD5, length, numeric type, path, and
encryption identity. It dumps additions/modifications with exact full-path
`--file-regex` filters, removes deleted outputs, and validates the staged file
set. It reuses existing bundle-derived AnimeStudio outputs and decoded audio,
then runs every normal WebUI builder. The private local snapshot advances only
after every builder succeeds. A retry after a later-stage failure may reuse
already-applied structured files only when the aborted manifest matches the
exact game root, output root, dump mode, and current source fingerprints. This
mode never calls the Updates builder or touches its previous-export baseline;
Updates remains the separate `build_updates.bat OLD NEW` workflow.

## Wrapper Integration

`export.bat --from-game` calls:

```bat
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type
```

Its structured VFS dump defaults to `--structured-dump-mode focused`, which dumps
only `table`, `json-data`, and video blocks. This skips raw asset bundles
(`Bundle`, `InitBundle`, and `BundleManifest`), audio PCK/media files, world
streaming, dynamic streaming, irradiance volumes, extend-data bins, patch bytes,
and Lua. `build_audio.py` streams Wwise bank metadata directly from VFS when
relinking audio events.
`--structured-dump-mode default` adds only Terrain `_H` height grids (not the
larger `C/T/S/A/N` families) while keeping the same production exclusions; pass
`--structured-dump-mode debug` for the old broad dump when diagnosing VFS
coverage.

Pass an optional usable DummyDll folder to the story JSON export with:

```bat
.\export.bat --from-game --animestudio-dummy-dlls path\to\DummyDll
```

Generate or refresh the preferred repo-local folder with:

```bat
python -m scripts.animestudio.generate_dummydll --status-only
python -m scripts.animestudio.generate_dummydll --dry-run
python -m scripts.animestudio.generate_dummydll --replace
```

The generator uses the installed `GameAssembly.dll` and matching
`global-metadata.dat`; matches the complete metadata image set to exactly one
Unity 2021 x64 CodeRegistration module table; derives the nearby
MetadataRegistration from the registration call site; and rejects missing,
ambiguous, or pointer-invalid results. The addresses are build-specific and
must never be copied from an earlier game build.

It initializes the optional `tools/Cpp2IL-Endfield` submodule on demand, then
uses the immutable `endfield-2022.0.7-vN` release pinned by both tag and commit
from `https://github.com/Variante/Cpp2IL-Endfield`. `setup.bat` deliberately
does not initialize this schema-recovery dependency. The maintained
source tolerates Endfield's malformed packing/type relationships, skips bad
images/types rather than aborting the whole set, makes
`--suppress-attributes` cover attribute restoration, and accepts the
generator's validated registration environment overrides without interactive
prompts. Endfield source changes belong on that fork's
`endfield/2022.0.7` branch; build and tag them there, then update both pins in
the generator. A clean checkout with the expected origin advances to a new pin
automatically; tracked local changes or a foreign origin fail closed. Do not
reintroduce an in-repo patch. Raw work stays under
`tmp/animestudio/dummydll/` on failure or with `--keep-work-dir`.

Before publication, every generated DLL name must exactly match the DLL images
in metadata and each file must be a managed PE. The built AnimeStudio CLI then
indexes the staged set, and every non-module metadata type must match exactly
on assembly, token, and full name; invalid, missing, unexpected, or mismatched
identities fail closed. Required-image skips,
catastrophic skipped-type ratios, and same-image-set size collapse are blocked
unless explicitly overridden for a reviewed diagnostic publication. Publication is atomic;
`--replace` moves the previous folder to a timestamped sibling. The resulting
`generation.json` records both native source hashes, registration summaries,
Cpp2IL-Endfield repository/tag/commit provenance, per-DLL hashes,
malformed-image/type skip counts, and the exact identity-join counts.

DummyDlls supply names, inheritance, and serialized field shapes, not original
method implementations. A loaded assembly does not prove a particular type was
emitted. Search the generated assembly for the resolved `scriptFullName` before
expecting `Studio.MonoBehaviourToTypeTree` to help, and compare a focused
serialized-first control with script-first output before changing defaults.

The wrapper checks explicit DummyDll paths, then falls back to
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`.
It forwards AnimeStudio.CLI `--dummy_dlls` only when the selected directory
contains a current, non-degraded `generation.json` whose native,
Cpp2IL-Endfield release, generator, DLL-list, size, and content provenance
validate. Missing, unverified,
stale, invalid, or degraded paths warn and continue without DummyDlls instead
of failing the export.

`export_assets.bat --from-game` defaults to the default asset mode:

```bat
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-asset-mode default --animestudio-stages maps convert_by_type json_by_type
```

Full asset mode uses the MessagePack asset map for per-type stages when safe:
each type worker loads only source bundles that contain that type, and
AnimeStudio indexes matched map/filter rows once so it can jump to selected
Endfield block offsets without re-scanning the full filter list for every file.
It exports the WebUI-facing image/model conversion set plus `Material` JSON for
model/material/texture relations. Animator conversion stays on the broad path
because FBX export may need related GameObject, Mesh, Material, and Texture2D
dependencies.

Pass `--focused-assets` to `export_assets.bat` or `--animestudio-asset-mode focused`
for the lean WebUI-focused mode. That mode exports only WebUI-referenced
`Texture2D` media. It writes a generated name-filter file from current Story/Wiki
media references, builds JSON plus MessagePack AnimeStudio maps, then loads the
MessagePack map with `--map_op AssetMap,Load` so matching map rows seed bundle
offset filtering.

Pass `--debug-assets` to `export_assets.bat` or `--animestudio-asset-mode debug`
for the exhaustive diagnostic mode. That mode restores the old broad conversion
set plus the default asset JSON set, then builds the normal complete Assets browser
index from whatever files are browser-visible.

The Python wrapper uses:

```text
scripts\export_full_from_game.py
DEFAULT_ANIMESTUDIO = tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
ANIMESTUDIO_GAME = ArknightsEndfield
ANIMESTUDIO_LOGGER_FLAGS = Warning, Error
ANIMESTUDIO_DEFAULT_JOBS = 8
ANIMESTUDIO_DEFAULT_SHARDS = 16
```

`--animestudio-jobs` controls the shared pool of concurrent AnimeStudio
processes for each source. `--animestudio-shards` controls how many filter-data
slices each deterministic asset type is split into. The default runs 8 workers
against 16 balanced shards; shards and other type requests are queued through the
same pool so one type does not monopolize the export. Lower jobs when peak memory
is too high.
`--animestudio-type-job-mode auto` merges map-filtered JSON types, but runs broad
Story TextAsset/MonoBehaviour/PlayableDirector jobs sequentially in isolated
processes. This prevents a large MonoBehaviour load from starving later Story
types. Use `parallel` for concurrent one-process-per-type behavior or `merged`
to explicitly combine every non-sharded type set.

Stage outputs:

```text
export_full\recovered\AnimeStudio-cli\StreamingAssets\maps
export_full\recovered\AnimeStudio-cli\StreamingAssets\json_by_type
export_full\recovered\AnimeStudio-cli\StreamingAssets\convert_by_type
export_full\recovered\AnimeStudio-cli\Persistent\...
export_full\recovered\AnimeStudio-cli\animestudio_type_manifest.json
```

Story JSON types:

```text
TextAsset:Both
MonoBehaviour:Both
PlayableDirector:Both
```

Full-mode asset conversion types:

```text
Texture2D:Both
Mesh:Both
Sprite:Both
Animator:Both
```

Full-mode asset JSON types:

```text
Material:Both
```

Debug-mode asset conversion types:

```text
Texture2D:Both
Shader:Both
TextAsset:Both
Font:Both
Mesh:Both
Sprite:Both
Animator:Both
AnimationClip:Both
```

Debug-mode asset JSON types add TextAsset, MonoBehaviour, Material, AssetBundle,
IndexObject, AnimatorController, AnimatorOverrideController, MonoScript,
PlayerSettings, PlayableDirector, ResourceManager, SpriteAtlas,
NapAssetBundleIndexAsset, PreloadData, and AvatarMask.

## Code Structure

Primary CLI orchestration:

```text
AnimeStudio.CLI\Components\CommandLine.cs
AnimeStudio.CLI\Program.cs
AnimeStudio.CLI\Studio.cs
AnimeStudio.CLI\Exporter.cs
```

Core library code:

```text
AnimeStudio\AssetsManager.cs
AnimeStudio\FileReader.cs
AnimeStudio\BundleFile.cs
AnimeStudio\VFSFile.cs
AnimeStudio\SerializedFile.cs
AnimeStudio\ObjectReader.cs
AnimeStudio\EndianBinaryReader.cs
AnimeStudio\TypeTreeHelper.cs
AnimeStudio\Classes\*.cs
AnimeStudio\YAML\*
```

High-level flow in `Program.Run`:

1. Resolve game with `GameManager.GetGame`.
2. Configure UnityCN key, logger flags, Unity version, and TypeFlags.
3. Load optional DummyDlls and optional filter data.
4. Lazily scan input files only when a map-build/no-map path needs it; `AssetMap,Load` uses matching map entries directly.
5. Build or load maps when `--map_op` asks for it.
6. For each selected file, load assets, build `AssetItem` data, export, then clear per-file state.

`Studio.BuildAssetData` collects exportable assets from loaded serialized files. `Studio.ExportAssets` dispatches to `Exporter` by `ExportType` and `ClassIDType`.

When callers have already merged and filtered split files, they use `AssetsManager.LoadPreparedFiles` to avoid repeating `MergeSplitAssets` / `ProcessingSplitFiles` for every selected file. `AssetsManager.Clear` closes readers, clears asset lists and caches, and triggers compacting GC only when the process is above the configured threshold. Per-type processes in the wrapper are the main RAM isolation boundary.

## MonoBehaviour Handling

`Exporter.ExportMonoBehaviour` first tries the serialized TypeTree via `MonoBehaviour.ToType()`. If that fails and `--dummy_dlls` loaded assemblies, it tries a script-derived TypeTree with `Studio.MonoBehaviourToTypeTree`.

If both decode paths fail but raw object data exists, the exporter writes metadata-only JSON with `$animestudio`, `type`, `name`, `pathId`, raw-data SHA-256, raw length, and decode error. This is intentional: the object was found and preserved for linking, but the script payload was not decoded into fields.

Use `--dummy_dlls` only when script field recovery matters. Without usable DummyDlls, serialized TypeTree fallback may still work for built-in or serialized objects, and script-specific MonoBehaviour payloads may fall back to partial or metadata-only output.

## Export Error Logs

`Studio.ExportAssets` catches exceptions per asset and logs:

```text
[Error] Export <Type>:<Name> error
```

This means the stage process continued after that asset failed. Causes include parser layout mismatches, invalid count fields, unsupported conversion data, missing external resources, and asset-specific converter errors.

Wrapper summary code in `scripts\export_full_from_game.py` parses these lines and samples them in `reports\export\export_full_summary.md`. A nonzero subprocess means the stage failed at process level; an `Export ... error` line means an item failed within an otherwise running process.

## Memory And Count Guards

The preferred guard for count-driven allocations is `EndianBinaryReader.ReadInt32Count(minBytesPerItem, fieldName)` or `EnsureCount`. It rejects negative counts and counts requiring more bytes than the remaining stream. Use it before arrays or lists driven by serialized counts, especially in Unity class parsers.

Examples already using count guards:

```text
SerializedFile.cs: typeCount, objectCount, scriptCount, externalsCount, refTypesCount
TypeTreeHelper.cs: map, TypelessData, and array sizes
AnimationClip.cs: numBindings, numMappings, ACL binding counts
BundleFile.cs: block and node counts
```

When fixing a suspected memory leak:

1. Find the count source with `rg -n "ReadInt32\(|ReadInt32Count|new .*\[|new List" tools\AnimeStudio\AnimeStudio`.
2. Check whether the count is schema-controlled or user-data-controlled.
3. Prefer `ReadInt32Count` with a realistic `minBytesPerItem`.
4. For variable-length records, use the smallest conservative item size.
5. Keep per-object failure local when possible so one malformed asset does not kill the full worker.
6. Rebuild the CLI and rerun the smallest matching stage/type with `--animestudio-refresh-types`.

## Useful Searches

```bat
rg -n "ReadInt32Count|EnsureCount|ReadInt32\(|new .*\[" tools\AnimeStudio\AnimeStudio -g "*.cs"
rg -n "Export .* error|metadata-only JSON|ExportMonoBehaviour|dummy_dlls" tools\AnimeStudio -g "*.cs"
rg -n "ANIMESTUDIO_|run_animestudio_stage|summarize_animestudio_log_issues" scripts\export_full_from_game.py
```

## Verification Pattern

For parser or exporter edits:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\export.bat --from-game --asset-jobs 4 --animestudio-refresh-types StreamingAssets:json_by_type:MonoBehaviour
```

For asset conversion edits:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\export_assets.bat --from-game --asset-jobs 4 --animestudio-refresh-types StreamingAssets:convert_by_type:Texture2D
```

Lower `--animestudio-jobs` if the targeted run exceeds available memory.

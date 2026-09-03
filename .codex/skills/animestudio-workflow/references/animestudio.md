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
| Streaming | `scripts/game_data/streaming.py` | `scripts/tests/test_streaming.py` |
| DynamicStreaming | `scripts/dynamic_streaming.py` | `scripts/tests/test_dynamic_streaming.py` |
| Irradiance volume | `scripts/game_data/irradiance_volume.py` | `scripts/tests/test_irradiance_volume.py` (region framing, bounded index filename tables, and single-file v3 index-directed payload ranges) |
| Terrain | `scripts/terrain_tret.py` | `scripts/tests/test_terrain_tret.py` |
| Table / SparkBuffer | `AnimeStudio/Endfield/Extraction/EndfieldSparkBuffer.cs` | `EndfieldSparkBufferTests.cs` |
| JsonData / LipSync | `scripts/game_data/memorypack/lipsync.py` | `scripts/tests/test_memorypack_lipsync.py` |
| JsonData / gameplay subfamilies | `scripts/story_builder/*_binary.py`, `scripts/game_data/memorypack/`, routed per virtual-path family | matching `scripts/tests/test_*_binary.py`, including `test_jsondata_binary.py`; current SkillData/BuffData and LevelData/LevelScriptData partial framings stay non-exact |
| ExtendData / CompressData | `AnimeStudio/Endfield/Extraction/EndfieldCompressData.cs`, `scripts/game_data/extend_data_binary.py` | AnimeStudio CLI fixtures and `scripts/tests/test_mmap_extend_data.py` |
| Lua | `AnimeStudio/Endfield/Extraction/EndfieldLuaDecoder.cs` | AnimeStudio CLI fixtures plus the `lua-sweep` mode |
| Video / USM | `AnimeStudio/Endfield/Extraction/EndfieldUsmConverter.cs` | AnimeStudio CLI USM framing fixtures |
| Audio / AKPK-Wwise | `AnimeStudio/Endfield/Audio/EndfieldAkpkPackage.cs`, CLI `audio-audit`, `scripts/build_audio.py` | `EndfieldAkpkTests.cs` plus audio-domain tests under `scripts/tests/` |

The mmap ExtendData reader proves count, fixed record widths, bounded string/TRS
ranges, non-overlap, and exact EOF for the current StringPathHash dictionaries.
FacBoneTRS still requires a current-build unit-count witness; its opaque gaps
and 64-byte value meaning must not be promoted to a self-describing schema.

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

For BundleManifest field recovery, join the manifest to this current inner
ledger before consulting generated AssetMaps. Equal table/file counts, exact
bundle-name multiplicity, and a numeric row-index sequence are structural
witnesses, not serialized field ownership. Reject an AssetMap as current-build
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
for plugin type `0x02`, a checked length-prefixed parameter range. Keep its
NodeBase and remaining tail bytes opaque until separately proven.

For IV recovery, region, index filename-table, and index-directed payload
framing are distinct claims. `parse_index_bytes` proves one unambiguous count-
prefixed UTF-16LE `iv_*.bytes` filename table. For supported single-file v3
indexes, `parse_indexed_payload_framing` additionally accepts one directory
only when its raw range words uniquely cover the authenticated payload from
zero through EOF without gaps or overlaps. It keeps all non-range words and
surrounding bytes opaque. Multi-filename and legacy layouts remain unsupported;
preserve numeric magic values until consumer evidence supplies stable names.
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

For SkillData/BuffData work, begin with the current envelope censuses under
`tmp/animestudio/` and the exact-build metadata hash recorded there. Member
counts and metadata field-name sets are discovery gates only. The maintained
SkillData framer may certify an anonymous EOF terminal shape while keeping its
prefix opaque and multiple starts ambiguous; this is not a whole schema. Do
not label a family exact until nested unions, field order, bounds, and EOF
consumption are covered by maintained positive and negative tests plus a full
current sweep. For LevelScriptData and LevelData, maintained prefix/suffix
framers may expose exact ranges with an opaque middle, but an apparent tail at
EOF remains insufficient for whole-schema status: the complete top-level
object and any ActionSerializedMap must be consumed first.
Current v29 metadata can identify formatter/wrapper methods and setter
declarations, but lacks a usable TypeSpec/MethodSpec mapping; if the recorded
native code registration maps outside the current image, fail closed. Do not
promote setter declaration order or the union-tag registry to serialized cursor
order without current method bodies or a bounded trace.
For residual JsonData prioritization, start from
`tmp/animestudio/jsondata_unclassified_family_census_20260903.json`; keep its
outer-verified rows in the denominator, and do not treat SkillData's uniform
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
python -m scripts.animestudio.generate_dummydll --dry-run
python -m scripts.animestudio.generate_dummydll --replace
```

The generator uses the installed `GameAssembly.dll` and matching
`global-metadata.dat`; matches the complete metadata image set to exactly one
Unity 2021 x64 CodeRegistration module table; derives the nearby
MetadataRegistration from the registration call site; and rejects missing,
ambiguous, or pointer-invalid results. The addresses are build-specific and
must never be copied from an earlier patch.

It prepares a local Cpp2IL `2022.0.7` checkout with the maintained
`scripts/animestudio/cpp2il-2022.0.7-endfield.patch`. That patch tolerates
Endfield's malformed packing/type relationships, skips bad images/types rather
than aborting the whole set, makes `--suppress-attributes` cover attribute
restoration, and accepts the generator's validated registration environment
overrides without interactive prompts. Raw work stays under
`tmp/animestudio/dummydll/` on failure or with `--keep-work-dir`.

Before publication, every generated DLL name must exactly match the DLL images
in metadata and each file must be a managed PE. Publication is atomic;
`--replace` moves the previous folder to a timestamped sibling. The resulting
`generation.json` records both source hashes, registration summaries, Cpp2IL
and patch provenance, per-DLL hashes, and malformed-image/type skip counts.

DummyDlls supply names, inheritance, and serialized field shapes, not original
method implementations. A loaded assembly does not prove a particular type was
emitted. Search the generated assembly for the resolved `scriptFullName` before
expecting `Studio.MonoBehaviourToTypeTree` to help, and compare a focused
serialized-first control with script-first output before changing defaults.

The wrapper checks explicit DummyDll paths, then falls back to
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`.
It only forwards AnimeStudio.CLI `--dummy_dlls` when the selected directory
exists and contains `.dll` files. Missing or stale DummyDll paths warn and
continue without DummyDlls instead of failing the export.

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

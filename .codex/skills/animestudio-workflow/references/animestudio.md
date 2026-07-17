# AnimeStudio Reference

## Paths And Build

Local checkout:

```text
tools\AnimeStudio
```

Primary parent-repo build wrappers:

```bat
.\scripts\animestudio\setup_dotnet9.bat
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
--filter_data       JSON list of source, offset, name, pathID, and type items.
```

`--types` replaces the default App.config parse/export surface. It does not layer on top of defaults. If GameObject or Animator export is selected, the CLI also parses dependencies such as Texture2D, Material, Animator, or GameObject as needed.

## Integrated VFS Commands

The CLI also exposes the Endfield VFS subcommands used by the WebUI pipeline:

```bat
AnimeStudio.CLI.exe dump --streaming-assets path\to\StreamingAssets --output export_full\structured\StreamingAssets --fallback-assets path\to\Persistent --block-type table --block-type json-data
AnimeStudio.CLI.exe dump --streaming-assets path\to\Persistent --output export_full\structured\Persistent --fallback-assets path\to\StreamingAssets --block-type table --block-type json-data
AnimeStudio.CLI.exe audio --streaming-assets path\to\StreamingAssets --output export_full\structured\Audio\CN --language chinese --format wav --block all
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
`vfs-index --jsonl` writes compact streaming metadata records while its default
output remains the existing JSON document.
`list` prints the known dumpable VFS block types. The WebUI wrappers default to this same
AnimeStudio executable:

```text
scripts\export_full_from_game.py  DEFAULT_STRUCTURED_DUMPER = DEFAULT_ANIMESTUDIO
scripts\build_audio.py            DEFAULT_AUDIO_DUMPER = DEFAULT_ANIMESTUDIO
```

`export_assets.bat --export-from-game` writes the lightweight bundle VFS index
through `vfs-index`, then decodes CN audio through `audio` before relinking
browser conversations.

`build_updates_by_patch.bat` uses `vfs-index --jsonl` to detect logical source
changes. Its patch apply path dumps changed Table/JsonData/Video/AuditVideo/Lua
files with exact `--file-regex` filters. If other changed blocks can affect
Unity assets or Story objects, it refreshes the configured AnimeStudio scope in
the cloned staging export rather than claiming unsafe per-output ownership.

## Wrapper Integration

`export.bat --export-from-game` calls:

```bat
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type
```

Its structured VFS dump defaults to `--structured-dump-mode webui`, which dumps
only `table`, `json-data`, and video blocks. This skips raw asset bundles
(`Bundle`, `InitBundle`, and `BundleManifest`), audio PCK/media files, world
streaming, dynamic streaming, irradiance volumes, extend-data bins, patch bytes,
and Lua. `build_audio.py` streams Wwise bank metadata directly from VFS when
relinking audio events.
`--structured-dump-mode full` keeps the same production skip rules; pass
`--structured-dump-mode debug` for the old broad dump when diagnosing VFS
coverage.

Pass an optional usable DummyDll folder to the story JSON export with:

```bat
.\export.bat --export-from-game --animestudio-dummy-dlls path\to\DummyDll
```

The wrapper checks explicit DummyDll paths, then falls back to
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`.
It only forwards AnimeStudio.CLI `--dummy_dlls` when the selected directory
exists and contains `.dll` files. Missing or stale DummyDll paths warn and
continue without DummyDlls instead of failing the export.

`export_assets.bat --export-from-game` defaults to the full asset mode:

```bat
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-asset-mode full --animestudio-stages maps convert_by_type json_by_type
```

Full asset mode uses the MessagePack asset map for per-type stages when safe:
each type worker loads only source bundles that contain that type, and
AnimeStudio indexes matched map/filter rows once so it can jump to selected
Endfield block offsets without re-scanning the full filter list for every file.
It exports the WebUI-facing image/model conversion set plus `Material` JSON for
model/material/texture relations. Animator conversion stays on the broad path
because FBX export may need related GameObject, Mesh, Material, and Texture2D
dependencies.

Pass `--webui-assets` to `export_assets.bat` or `--animestudio-asset-mode webui`
for the lean WebUI-focused mode. That mode exports only WebUI-referenced
`Texture2D` media. It writes a generated name-filter file from current Story/Wiki
media references, builds JSON plus MessagePack AnimeStudio maps, then loads the
MessagePack map with `--map_op AssetMap,Load` so matching map rows seed bundle
offset filtering.

Pass `--debug-assets` to `export_assets.bat` or `--animestudio-asset-mode debug`
for the exhaustive diagnostic mode. That mode restores the old broad conversion
set plus the full asset JSON set, then builds the normal full Assets browser
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
.\export.bat --export-from-game --animestudio-jobs 4 --animestudio-refresh-types StreamingAssets:json_by_type:MonoBehaviour
```

For asset conversion edits:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\export_assets.bat --export-from-game --animestudio-jobs 4 --animestudio-refresh-types StreamingAssets:convert_by_type:Texture2D
```

Lower `--animestudio-jobs` if the targeted run exceeds available memory.

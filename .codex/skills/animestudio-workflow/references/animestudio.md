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
--dummy_dlls        DummyDll folder for MonoBehaviour script schema recovery.
--filter_data       JSON list of source, offset, name, pathID, and type items.
```

`--types` replaces the default App.config parse/export surface. It does not layer on top of defaults. If GameObject or Animator export is selected, the CLI also parses dependencies such as Texture2D, Material, Animator, or GameObject as needed.

## Wrapper Integration

`export.bat --export-from-game` calls:

```bat
python .\scripts\export_full_from_game.py --animestudio-scope story --animestudio-stages maps json_by_type
```

Pass a usable DummyDll folder to the story JSON export with:

```bat
.\export.bat --export-from-game --animestudio-dummy-dlls path\to\DummyDll
```

The wrapper validates explicit DummyDll paths, then falls back to
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`.
It only forwards AnimeStudio.CLI `--dummy_dlls` when the selected directory
exists and contains `.dll` files.

`export_assets.bat --export-from-game` calls:

```bat
python .\scripts\export_full_from_game.py --skip-structured --animestudio-scope assets --animestudio-stages convert_by_type json_by_type
```

The Python wrapper uses:

```text
scripts\export_full_from_game.py
DEFAULT_ANIMESTUDIO = tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
ANIMESTUDIO_GAME = ArknightsEndfield
ANIMESTUDIO_LOGGER_FLAGS = Warning, Error
ANIMESTUDIO_DEFAULT_JOBS = 1
```

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

Asset conversion types:

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

Asset JSON types add Material, AssetBundle, IndexObject, AnimatorController, AnimatorOverrideController, MonoScript, PlayerSettings, PlayableDirector, ResourceManager, SpriteAtlas, NapAssetBundleIndexAsset, PreloadData, and AvatarMask.

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
4. Scan input files.
5. Build or load maps when `--map_op` asks for it.
6. For each file, load assets, build `AssetItem` data, export, then clear per-file state.

`Studio.BuildAssetData` collects exportable assets from loaded serialized files. `Studio.ExportAssets` dispatches to `Exporter` by `ExportType` and `ClassIDType`.

`AssetsManager.Clear` closes readers, clears asset lists and caches, and triggers compacting GC only when the process is above the configured threshold. Per-type processes in the wrapper are the main RAM isolation boundary.

## MonoBehaviour Handling

`Exporter.ExportMonoBehaviour` first tries the serialized TypeTree via `MonoBehaviour.ToType()`. If that fails and `--dummy_dlls` loaded assemblies, it tries a script-derived TypeTree with `Studio.MonoBehaviourToTypeTree`.

If both decode paths fail but raw object data exists, the exporter writes metadata-only JSON with `$animestudio`, `type`, `name`, `pathId`, raw-data SHA-256, raw length, and decode error. This is intentional: the object was found and preserved for linking, but the script payload was not decoded into fields.

Use `--dummy_dlls` when script field recovery matters. Without usable DummyDlls, TypeTree fallback may still work for built-in or serialized objects, but script-specific MonoBehaviour payloads can become metadata-only.

## Export Error Logs

`Studio.ExportAssets` catches exceptions per asset and logs:

```text
[Error] Export <Type>:<Name> error
```

This means the stage process continued after that asset failed. Causes include parser layout mismatches, invalid count fields, unsupported conversion data, missing external resources, and asset-specific converter errors.

Wrapper summary code in `scripts\export_full_from_game.py` parses these lines and samples them in `reports\export_full_summary.md`. A nonzero subprocess means the stage failed at process level; an `Export ... error` line means an item failed within an otherwise running process.

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
.\export.bat --export-from-game --animestudio-jobs 1 --animestudio-refresh-types StreamingAssets:json_by_type:MonoBehaviour
```

For asset conversion edits:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\export_assets.bat --export-from-game --animestudio-jobs 1 --animestudio-refresh-types StreamingAssets:convert_by_type:Texture2D
```

Use `--animestudio-jobs 2` only after the one-worker targeted run is clean.

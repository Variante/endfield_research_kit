# AnimeStudio Recovery Reproduction Matrix

Created on 2026-06-28 as the working matrix for reducing AnimeStudio export
warnings/errors from `reports/20260627_215637`.

## Baseline

- AnimeStudio executable:
  `tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe`
- Game root:
  `D:\Program Files\Endfield Game\Endfield_Data`
- Latest analyzed report run:
  `reports/20260627_215637`
- Baseline summary:
  `memory/animestudio_ab_understanding_report.md`

## Failure Classes

| Track | Baseline issue | Primary logs | Smallest existing filter scope |
| --- | --- | --- | --- |
| Shader | 454 shader export errors across both sources | `*Shader*.stdout.log` | per-source Shader shard |
| AnimationClip | 50 animation export errors across both sources | `*AnimationClip*.stdout.log` | per-source AnimationClip shard |
| MonoBehaviour | 13,434 partial decode warnings | `*json_by_type.stdout.log` | merged JSON type stage, needs narrower custom filter |
| Texture2D/Sprite | 27,149 unexpected missing conversion outputs | stage summary and empty Sprite shard logs | per-source Texture2D/Sprite shard |

## Direct Rebuild

After code edits:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

## Shader Repro

StreamingAssets shard with the first shader errors:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  "D:\fluffy-dump\scratch\animestudio_repro\shader_streaming_shard01" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Shader\shard_01_of_07_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Shader\shard_01_of_07_filter_data.json" ^
  --types Shader:Both
```

Persistent shard with broad shader errors:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  "D:\fluffy-dump\scratch\animestudio_repro\shader_persistent_shard02" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\Persistent\convert_by_type\Shader\shard_02_of_02_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\Persistent\convert_by_type\Shader\shard_02_of_02_filter_data.json" ^
  --types Shader:Both
```

## AnimationClip Repro

StreamingAssets shard with early animation errors:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  "D:\fluffy-dump\scratch\animestudio_repro\animation_streaming_shard01" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\AnimationClip\shard_01_of_16_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\AnimationClip\shard_01_of_16_filter_data.json" ^
  --types AnimationClip:Both
```

Persistent animation shard:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  "D:\fluffy-dump\scratch\animestudio_repro\animation_persistent_shard01" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\Persistent\convert_by_type\AnimationClip\shard_01_of_02_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\Persistent\convert_by_type\AnimationClip\shard_01_of_02_filter_data.json" ^
  --types AnimationClip:Both
```

## Texture2D/Sprite Repro

Texture2D has missing outputs without export errors. Start with a shard that
finished quickly, then inspect the generated file list against the filter data.

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  "D:\fluffy-dump\scratch\animestudio_repro\texture_streaming_shard01" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Texture2D\shard_01_of_16_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Texture2D\shard_01_of_16_filter_data.json" ^
  --types Texture2D:Both
```

Sprite currently has matched entries but no output files in summary accounting.

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  "D:\fluffy-dump\scratch\animestudio_repro\sprite_streaming_shard01" ^
  --game ArknightsEndfield ^
  --logger_flags Warning Error ^
  --group_assets ByType ^
  --export_type Convert ^
  --dummy_dlls "D:\fluffy-dump\tools\DummyDll" ^
  --names "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Sprite\shard_01_of_16_names.txt" ^
  --filter_data "D:\fluffy-dump\export_full\recovered\AnimeStudio-cli\filters\asset_shards\StreamingAssets\convert_by_type\Sprite\shard_01_of_16_filter_data.json" ^
  --types Sprite:Both
```

## MonoBehaviour Repro

The current warning lines do not include source AB paths. Before patching parser
logic, create a custom minimal filter from one warning object's source entry or
add source-path logging around partial `ExportMonoBehaviour` recovery.

Current broad repro:

```bat
.\export.bat --export-from-game --animestudio-jobs 1 --animestudio-refresh-types StreamingAssets:json_by_type:MonoBehaviour
```

This is still broad and can be slow. The preferred next step is a diagnostic
patch that logs source path, PathID, script type, serialized TypeTree status, and
DummyDll status for partial MonoBehaviour warnings.

## Commit Practice

Commit each verified increment separately:

1. Diagnostic/report-only changes.
2. One parser/exporter fix per failure class.
3. Wrapper/status-manifest changes separately from parser fixes.


# Fluffy Dumper VFS index parity checkpoint

Date: 2026-07-03

## Scope

Check the local `tools\fluffy-dumper-src` build against the current installed
Endfield data and compare its focused VFS index output with AnimeStudio's
integrated `vfs-index` command.

Local tool state:

```text
tools\fluffy-dumper-src\target\release\fluffy-dumper.exe
size: 11,911,168 bytes
last write: 2026-07-02 20:56:36
```

The CLI exposes the expected local Endfield patch:

- `dump --fallback-assets`
- `audio --fallback-assets`
- `vfs-index --fallback-assets`
- block filters including `table`, `json-data`, `hotfix-audio`, and per-language
  audio blocks.

The source checkout remains dirty relative to local commit
`1c8dd10 Document Endfield fallback-assets patch`:

```text
M fluffy-dumper/src/cli.rs
M fluffy-dumper/src/main.rs
M vfs/src/loader.rs
?? .cargo-ok
?? fluffy-dumper/src/indexer.rs
```

That dirty state is the local Endfield indexer/fallback-assets worktree, not a
new change from this checkpoint.

## Commands

Fluffy Dumper:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe vfs-index ^
  -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  -b table ^
  -o tmp\fluffy_dumper_current_probe_20260703\vfs_index_table.json

.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe vfs-index ^
  -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  -b json-data ^
  -o tmp\fluffy_dumper_current_probe_20260703\vfs_index_json_data.json
```

AnimeStudio parity check:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index ^
  -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  -b table ^
  -o tmp\animestudio_vfs_index_current_probe_20260703\vfs_index_table.json

.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index ^
  -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" ^
  --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\Persistent" ^
  -b json-data ^
  -o tmp\animestudio_vfs_index_current_probe_20260703\vfs_index_json_data.json
```

## Result

Both tools indexed the same focused current-install content:

| Block | Chunks | Files | Byte count | Unique names |
| --- | ---: | ---: | ---: | ---: |
| `table` | 42 | 629 | 161,084,549 | 629 |
| `json-data` | 69 | 81,735 | 700,046,680 | 81,735 |

Representative names matched:

```text
table first:
  Data/TableCfg/CharacterConst.bytes
  Data/TableCfg/DisplayEnemyTypeTable.bytes
  Data/TableCfg/WeaponPotentialUpItemTable.bytes
table last:
  Data/TableCfg/SimulationTrainingCardTable.bytes
  Data/TableCfg/SimulationTrainingCardPoolTable.bytes
  Data/TableCfg/I18nHotFix.bytes

json-data first:
  Data/Json/AIConfig/EnemyTemplateDataSummary.json
  Data/Json/AnimationConfig/anim_cfg_abilityEntity_0008.json
  Data/Json/AnimationConfig/anim_cfg_abilityEntity_0017.json
json-data last:
  Data/Json/LevelGenForRuntime/TotalFactoryRegions.json
  Data/Json/LevelGenForRuntime/DoodadGroupTable.json
  Data/Json/InteractiveData/Collections.json
```

The JSON files are not byte-identical because `generatedAtEpoch` differs between
runs. After parsing, the only structural difference for both `table` and
`json-data` outputs is:

```text
/generatedAtEpoch
```

## Conclusion

For current WebUI-relevant `table` and `json-data` VFS metadata, the local
Fluffy Dumper build and AnimeStudio integrated VFS index path agree exactly on
chunk count, file count, byte count, file names, and parsed metadata. Fluffy
Dumper remains useful as an independent Rust parity tool for VFS/table/json/audio
index checks, while AnimeStudio remains the active extractor for Unity object,
MonoBehaviour, shader, and WebUI export workflows.

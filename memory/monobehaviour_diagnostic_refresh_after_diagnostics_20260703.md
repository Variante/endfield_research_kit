# MonoBehaviour Diagnostic Refresh After Managed Reference Fixes - 2026-07-03

## Scope

Ran a full focused AnimeStudio Story/MonoBehaviour refresh after the camera and
low-volume managed-reference diagnostic decoders were committed.

Command:

```bat
python scripts\benchmark_export.py --label p3_mono_json_after_diagnostics -- python scripts\export_full_from_game.py --game-root "D:\Program Files\Endfield Game\Endfield_Data" --output export_full --skip-structured --skip-vfs-index --animestudio-scope story --animestudio-stages maps json_by_type --animestudio-jobs 1 --animestudio-type-job-mode auto --animestudio-dummy-dlls tools\DummyDll
```

## Export Result

Report run:

```text
reports/20260703_030504/
```

Benchmark:

```text
reports/export_benchmarks/p3_mono_json_after_diagnostics_20260703_035034_504.md
```

Result:

- status: succeeded
- commands: 4
- command failures: 0
- failed entries: 0
- manifest entries: 0
- wall time: 2,729.718 seconds
- peak working set: 13,736,591,360 bytes

AnimeStudio summary:

- StreamingAssets: maps=2, convert=388,754, json=1,109,797
- Persistent: maps=2, convert=25,792, json=105,266

## Decoded Index Validation

Rebuilt the MonoBehaviour decoded index:

```bat
python scripts\build_decoded_index.py --export-root export_full --sources StreamingAssets Persistent --types MonoBehaviour --output tmp\decoded_index_mono_after_diagnostics_20260703 --jobs 8
```

Result:

- files: 1,064,294
- output size: 10,982.8 MiB
- groups: 1,478

Status counts compared with `tmp/decoded_index_mono_current_20260703`:

| Status | Before | After |
|---|---:|---:|
| decoded | 1,063,602 | 1,063,560 |
| partial | 676 | 734 |
| unparsed | 16 | 0 |

Registry counts:

| Registry status | Before | After |
|---|---:|---:|
| fullyDecoded | 12,742 | 12,746 |
| heuristic | 89 | 73 |
| partialDecoded | 603 | 615 |

The removed `unparsed` rows became typed partial/decoded evidence:

- camera configs: `CameraControlAutoPitchConfig`, `CameraControlAutoYawConfig`,
  `CameraControlLockEnemyConfig`, `CameraControlWaterDroneConfig`
- low-volume gameplay configs: `CharacterHeightData`, `WeaponExhibitData`,
  `CheckRpgEquipCount`, `LineFollower`, `PlayLineSound`
- ProBuilder zero-byte shapes: `Cube`, `Prism`

Remaining residuals are all `partial`, led by existing larger parser frontiers:

- `ProjectileTemplateData`: 310 total partial rows
- `AbilityEntityTemplateData`: 162 total partial rows
- `EnemyTemplateData`: 156 total partial rows
- `CharacterTemplateData`: 30 total partial rows
- smaller `SpawnEntityHandler`, `RemoteFactoryEntityTemplateData`,
  `DialogMainFlowData`, `FootStepHandler`, and `RendererVisibilityHandler`
  groups

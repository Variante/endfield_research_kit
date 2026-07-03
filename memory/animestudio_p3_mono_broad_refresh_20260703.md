# AnimeStudio P3 MonoBehaviour Broad Refresh - 2026-07-03

## Context

P3 was the next MonoBehaviour recovery pass after the Persistent pilot showed
that the current AnimeStudio exporter preserves much larger serialized
MonoBehaviour payloads with managed-reference registry recovery enabled. The
broad run refreshed both installed-game source roots with DummyDlls enabled.

## Command

```bat
python scripts\benchmark_export.py --label p3_mono_json -- python scripts\export_full_from_game.py --game-root "D:\Program Files\Endfield Game\Endfield_Data" --output export_full --skip-structured --skip-vfs-index --animestudio-scope story --animestudio-stages maps json_by_type --animestudio-jobs 1 --animestudio-type-job-mode auto --animestudio-dummy-dlls tools\DummyDll
```

## Export Result

- Status: succeeded
- Return code: 0
- Wall time: 43m 58.7s
- Peak sampled process-tree RAM: 13.08 GiB working set
- Command failures: 0
- Failed decode entries: 0
- Manifest missing-reference entries: 0
- Summary: `reports/20260703_002301/export_full_summary.md`
- Benchmark: `reports/export_benchmarks/p3_mono_json_20260703_010659_707.md`

AnimeStudio refreshed:

- `StreamingAssets`: maps=2, json=1,109,797
- `Persistent`: maps=2, json=105,266

## Decoded Index

Current index:

```bat
python scripts\build_decoded_index.py --export-root export_full --sources StreamingAssets Persistent --types MonoBehaviour --output tmp\decoded_index_mono_current_20260703 --jobs 8
```

Output:

- Files: 1,064,294
- Bytes: 11,515,855,094
- Groups: 1,480
- Statuses: decoded=1,063,602, partial=676, unparsed=16

Previous comparable indexes:

- `tmp/decoded_index_mono_20260630/index.json`: decoded=1,060,650, partial=2,140, unparsed=1,504
- `webui/data/decoded/index.json`: decoded=1,060,650, partial=2,140, unparsed=1,504

Net improvement:

- +2,952 decoded files
- -1,464 partial files
- -1,488 unparsed files

## Remaining Buckets

The 692 remaining partial/unparsed files all still have:

- `$animestudio.typeTreeSource`: `serializedType`
- `managedReferencesRegistryRecovered`: `true`
- `serializedTypeTreeError`: present

No remaining bucket points to missing object discovery or a lost
managed-reference registry. The residual failures are nested layout/parser
drift after successful registry recovery.

Top remaining schemas:

- `ProjectileTemplateData`: 310
- `AbilityEntityTemplateData`: 162
- `EnemyTemplateData`: 156
- `CharacterTemplateData`: 30
- `SpawnEntityHandler`: 8
- `CameraControlAutoPitchConfig`: 4
- `RemoteFactoryEntityTemplateData`: 3
- `DialogMainFlowData`: 3
- `FootStepHandler`: 2
- `RendererVisibilityHandler`: 2

Top remaining domains:

- `camera/cinematic`: 479
- `gameplay/ability`: 186
- `managed-reference`: 11
- `metadata-only`: 7
- `gameplay/weapon`: 5
- `story/dialog`: 3
- `gameplay/character`: 1

Representative residual errors:

- `ProjectileTemplateData` / nested `AbilitySystemData`: `ReadAlignedString` requests impossible lengths such as `1769235301` (`0x69746365`).
- `AbilityEntityTemplateData`: impossible string lengths such as `1702458473` (`0x65797469`).
- Camera-control configs: impossible string lengths that look like float bytes, such as `1069547520` (`0x3FC00000`) and `1073741824` (`0x40000000`).
- `CharacterTemplateData`: impossible string length `825438256` (`0x31333030`).

These values look like valid field payload bytes being interpreted at the wrong
offset, so the next parser work should target nested layout boundaries in
projectile/ability/character template data and camera-control config layouts.

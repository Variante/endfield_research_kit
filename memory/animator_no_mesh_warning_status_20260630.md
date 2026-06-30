# Animator No-Mesh Dependency Recovery - 2026-06-30

## Scope

Focused recovery pass for the stored AnimeStudio warning family:

```text
[Warning] Animator no output reason=no_mesh ...
```

The checked historical logs contained 57,025 such warnings, all from:

```text
reports/20260628_194720/StreamingAssets/StreamingAssets_animestudio_convert_by_type.stdout.log
```

No other Warning/Error classes were found in the checked report log set
(`reports/20260628_194720`, `reports/20260628_200522`,
`reports/20260629_010651`, and `reports/20260629_023642`).

## Findings

`Animator` FBX conversion had two separate issues.

1. Explicit type filters under-loaded dependencies. A command such as
   `--export_type Convert --types Animator:Both` replaced the default parse
   surface and did not parse enough linked objects for `ModelConverter`.
   The converter needs the linked hierarchy and render payloads:

```text
GameObject, Transform, RectTransform, MeshFilter, MeshRenderer,
SkinnedMeshRenderer, Mesh, Texture2D, Material, Avatar,
AnimatorController, AnimatorOverrideController, AnimationClip
```

2. Successful Animator FBX exports used natural names such as `Main.fbx` while
   no-mesh markers used path-id-suffixed names such as
   `Main_p0000000000000029.fbx.empty.json`. Natural names collided heavily
   across duplicate Animator names and also prevented the wrapper status
   manifests from proving which asset-map entry owned each FBX.

## Implemented

AnimeStudio CLI now auto-adds the required parse dependencies when explicit
`GameObject` or `Animator` export is requested. Dependencies are added as
parse-only unless the user explicitly requested export for that type.

The parent wrapper `scripts/export_full_from_game.py` now passes the same
Animator convert parse dependencies, so wrapper-driven asset exports include the
related hierarchy and mesh objects.

Animator FBX export now reserves the final `.fbx` path with the same
`TryExportFile` helper used by other converted files. FBX outputs now include
the source Animator path ID, matching the wrapper's predicted output contract.
True no-mesh Animators still write `.fbx.empty.json` markers.

The wrapper now refreshes report-only asset status manifests after successful
normal `convert_by_type` runs, including unsafe broad-path types such as
`Animator`. This prevents latest summaries from carrying stale `asset_caches`
status forward after a real rerun.

## Focused Validation

Historical sample chunk:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\0CE8FA57\D937E67494E3B4C19C00B4CD263ED388.chk
```

Before the dependency fix, `Animator:Both` produced 0 FBX files and 31 no-mesh
markers for this chunk. Manually adding parse dependencies proved the issue by
recovering FBX geometry.

After the dependency and path-id naming fixes, the plain direct command:

```bat
AnimeStudio.CLI.exe <chunk> tmp\animator_pathid_suffix_probe_20260630 ^
  --game ArknightsEndfield --logger_flags Warning Error ^
  --group_assets ByType --map_op None ^
  --export_type Convert --types Animator:Both
```

Result:

- CLI exit code: 0.
- Warning/Error output: none.
- `.fbx` outputs: 6, all path-id-suffixed.
- `.fbx.empty.json` markers: 25.
- `.png` texture outputs: 3.
- marker parse errors: 0.

Example recovered FBX names:

```text
Main_p0000000000000029.fbx
Main_p95C4D7B778AEC181.fbx
SK_actor_f_p780C44930A6B6AFB.fbx
SK_actor_female_pD6377FDA12F5F767.fbx
SK_actor_male_p3FE7937818F371DF.fbx
SK_actor_no_gender_pC4450E0BB427A1F6.fbx
```

## Full Targeted Refresh

Command:

```bat
python scripts\export_full_from_game.py --skip-structured --skip-vfs-index ^
  --animestudio-scope assets --animestudio-asset-mode full ^
  --animestudio-stages convert_by_type --animestudio-asset-types Animator ^
  --animestudio-jobs 2
```

Run id:

```text
reports/20260629_221000
```

Both AnimeStudio stage logs are empty for stdout and stderr:

```text
reports/20260629_221000/StreamingAssets/StreamingAssets_animestudio_convert_by_type.stdout.log
reports/20260629_221000/StreamingAssets/StreamingAssets_animestudio_convert_by_type.stderr.log
reports/20260629_221000/Persistent/Persistent_animestudio_convert_by_type.stdout.log
reports/20260629_221000/Persistent/Persistent_animestudio_convert_by_type.stderr.log
```

Final status:

| root | matched Animator entries | resolved entries | FBX outputs | no-mesh markers | texture outputs | missing outputs | dirty source groups | export errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `StreamingAssets` | 57,025 | 57,025 | 4,733 | 52,292 | 736 | 0 | 0 | 0 |
| `Persistent` | 5,423 | 5,423 | 476 | 4,947 | 55 | 0 | 0 | 0 |

Compared with the first dependency-only refresh, path-id FBX naming recovered
many duplicate-name outputs that had previously collided under natural names:

| root | dependency-only natural-name FBX | final path-id FBX | gained FBX outputs |
| --- | ---: | ---: | ---: |
| `StreamingAssets` | 2,015 | 4,733 | 2,718 |
| `Persistent` | 181 | 476 | 295 |

## Conclusion

The historical Animator `no_mesh` warning family is now understood and resolved
for export status purposes.

- Mesh-bearing Animators produce path-id-addressable FBX files.
- True no-mesh Animators produce structured `.fbx.empty.json` evidence.
- The current status manifests resolve every matched Animator entry with zero
  missing outputs and zero dirty source groups.
- The targeted refresh produced no Warning/Error log output.

Remaining `no_mesh` markers are expected helper/UI/camera/effect hierarchy
objects with no mesh payload, not exporter failures.

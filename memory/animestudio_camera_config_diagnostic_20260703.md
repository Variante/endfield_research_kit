# AnimeStudio Camera Config Diagnostic Decode - 2026-07-03

## Context

The current MonoBehaviour refresh left only 16 `unparsed` entries in
`tmp/decoded_index_mono_current_20260703`, including seven camera/cinematic
assets whose managed-reference registry was recovered but whose
`CameraControl*Config` payloads still fell back to `$heuristic`/`$unparsed`.

The failure pattern was a managed-reference payload layout gap, not object
discovery or a core reader allocation issue: the serialized TypeTree path was
reading float/int payload words such as `0x3fc00000` and `0x40000000` as
string lengths inside `ReferencedObjectData`.

## Code Change

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now recognizes these
`Beyond.Gameplay.View` managed-reference classes:

- `CameraControlAutoPitchConfig`
- `CameraControlWaterLimitConfig`
- `CameraControlAutoYawConfig`
- `CameraControlFightOrbitConfig`
- `CameraControlAutoZoomConfig`
- `CameraControlLockEnemyConfig`
- `CameraControlWaterDroneConfig`

For word-aligned payloads up to 4096 bytes, AnimeStudio emits a typed
`$partial`/`$inferred` diagnostic object with `layout`, payload offsets,
`wordCount`, and `rawWords` using the existing int32/float32/ascii word trace
format. This does not claim semantic field names; it preserves typed evidence
and removes the misleading unresolved heuristic marker for this known payload
family.

## Validation

Rebuilt the CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Targeted all seven currently unparsed camera assets from:

```text
D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk
```

Command:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\camera_mono_all_unparsed_probe_after_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^(CCS_Default|CCS_Default_Debug|CCS_Default_Far|CCS_SnapShot|CCS_DefaultHome|CCS_LockEnemy|CCS_interact_waterdrone)$"
```

Result:

- 7 MonoBehaviour JSON files exported.
- 41 camera config payloads across the seven known classes.
- 41/41 camera config payloads now have `$partial` and `rawWords`.
- 0 camera config payloads have `$heuristic` or `$unparsed`.
- No `Export ... error` or `Partially decoded MonoBehaviour` lines appeared in
  the targeted probe output.

Expected next full MonoBehaviour refresh impact: the seven current
camera/cinematic `unparsed` rows should become `partial` typed evidence. The
remaining non-camera `unparsed` rows are still separate work:
`CharacterHeightData`, `WeaponExhibitData`, `CheckRpgEquipCount`, `Cube`,
`LineFollower`, and `Prism`.

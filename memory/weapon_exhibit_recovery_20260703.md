# Weapon Exhibit Recovery - 2026-07-03

## Scope

This pass promotes `Beyond.Gameplay.WeaponExhibitData` managed-reference
payloads from generic raw diagnostics into named fields.

It covers the single current `WeaponExhibitConfig` MonoBehaviour and its seven
managed-reference payloads.

## Evidence

IL2CPP metadata names:

- `WeaponExhibitData.cameraGroup`
- `WeaponExhibitData.boothPosition`
- `WeaponExhibitData.spawnDataList`

Nested `WeaponExhibitSpawnData` fields:

- `generateOffset`
- `generateRotationEuler`
- `generateScale`

All observed payloads parse as:

```text
aligned ASCII string cameraGroup
Vector3 boothPosition
int32 spawnDataList.count
spawnDataList.count * (
  Vector3 generateOffset
  Vector3 generateRotationEuler
  Vector3 generateScale
)
```

Observed payload lengths:

- `84` bytes: `5` refs
- `88` bytes: `1` ref
- `120` bytes: `1` ref

The `88` byte variant is explained by a 30-byte `cameraGroup` string aligning to
36 bytes before the vector fields. The `120` byte variant has two spawn rows.

## Implementation

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now routes
`Gameplay.Beyond/Beyond.Gameplay/WeaponExhibitData` through a dedicated decoder
before the generic low-volume fallback.

The decoder requires:

- a valid `WeaponExhibitData` managed-reference header
- a payload that fully parses through the aligned string, vector, count, and
  36-byte spawn-row list
- `spawnDataList.count` in `0..16`
- exact stream completion after the last spawn row

Future variants that do not satisfy the invariant are left to the existing raw
diagnostic fallback.

## Validation

Built AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

The build succeeded with the existing AnimeStudio warning set and `0` errors.

Focused export output:

```text
tmp\weapon_exhibit_after_20260703
```

Validation results:

- exported JSON files: `1`
- `WeaponExhibitData` refs decoded: `7`
- total spawn rows decoded: `8`
- validation assertion errors: `0`
- no decoded `WeaponExhibitData` retained `$partial`, `$unparsed`,
  `$heuristic`, `heuristicRawWordHints`, or generic top-level `rawWords`

Observed camera groups:

- `CameraGroup/pistol_cam_group`
- `CameraGroup/sword_cam_group`
- `CameraGroup/wand_cam_group`
- `CameraGroup/claymore_cam_group`
- `CameraGroup/gun_cam_group`
- `CameraGroup/lance_cam_group`

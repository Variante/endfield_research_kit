# AbilityEntity component recovery - 2026-07-03

## Scope

Recovered the remaining focused `data_abilityentity_*` MonoBehaviour frontier
after the projectile curve pass. The work targeted small, metadata-backed
AbilityEntity component gaps in AnimeStudio and converted the remaining broad
InteractiveEvent records from generic `$unparsed` heuristics into bounded
partial diagnostics.

## AnimeStudio changes

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now decodes:

- `Beyond.Gameplay.Core.PhysicsComponentData`
  - exact 16-byte payload
  - nested `PhysicalData` fields: `mass`, `drag`, `angularDrag`,
    `collisionDetectionMode`
- `Beyond.Gameplay.Core.NavMeshObstacleComponentData`
  - existing standard config shape remains supported
  - ability-entity embedded-name variant reads two strings, nine numeric words,
    non-empty `embeddedName`, then a shape RID
  - the embedded-name probe now requires the following RID to resolve to
    `NavMeshObstacleCapsuleData` or `NavMeshObstacleBoxData`, so multi-item
    `configList` payloads do not depend on the variant being the final item
- `Beyond.Gameplay.InteractiveEvent.AttachToInstigator`
- `Beyond.Gameplay.InteractiveEvent.EnterThrowMode`
- `Beyond.Gameplay.InteractiveEvent.InteractiveEventComponentData`

The three InteractiveEvent records are intentionally emitted as `$partial`
diagnostics, not exact semantic decodes. IL2CPP metadata supplies field order,
but nested `AbilityEntityFollowData`, throw-mode curve/effect/layer/SkillData
sections, and `interactiveActions` list header semantics are not yet byte-proven.
The partial payloads retain metadata field order, aligned string hints,
managed-reference RID links where available, and bounded raw words.

## IL2CPP evidence used

Focused metadata dumps under `tmp/` supplied these field orders:

- `PhysicsComponentData`: `physicalData`
- `PhysicalData`: `mass`, `drag`, `angularDrag`, `collisionDetectionMode`
- `NavMeshObstacleComponentData`: `configList`
- `AttachToInstigator`: `mountPoint`, `followData`
- `EnterThrowMode`: `skillId`, `aimMountPoint`, `aimOffset`,
  `aimRightOffset`, `angleCurve`, `layers`, `speed`, `fallSpeed`, `radius`,
  `bombRadius`, `maxDistance`, `bombLineEffectActionCfg`,
  `ignoreColliderOptions`, `secondCheckLayerMask`, `overlapRadius`,
  `m_skillData`
- `InteractiveEventComponentData`: `maxPickUpTime`, `interactiveActions`

## Validation

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: succeeded with 0 warnings and 0 errors.

Focused exports:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\abilityentity_interactive_partial_after2_20260703\68 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\71FC2E71A9F249B382BF8DAED3BCEE65.chk" tmp\abilityentity_interactive_partial_after2_20260703\71 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_"
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\abilityentity_interactive_partial_after2_20260703\fbad --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_"
```

Focused metrics:

| Metric | Count |
| --- | ---: |
| Exported JSON files | 161 |
| Managed-reference classes | 37 |
| `$unparsed` refs | 0 |
| `NavMeshObstacleComponentData` decoded | 6 |
| `PhysicsComponentData` decoded | 2 |
| `AttachToInstigator` partial diagnostics | 6 |
| `EnterThrowMode` partial diagnostics | 6 |
| `InteractiveEventComponentData` partial diagnostics | 3 |

Observed NavMesh embedded-name rows:

- `Trap` -> `NavMeshObstacleCapsuleData`: 5 rows
- standard no-embedded-name config -> `NavMeshObstacleBoxData`: 1 row

`InteractiveEventComponentData` diagnostics now preserve typed
`interactiveActions` RID evidence. One sample exposes 21 linked actions,
including `SetInstigator`, `AddTag`, `PlayAnimationAction`, `PlaySoundAction`,
`AddThrowCameraControl`, `CastSkill`, `DetachFromInstigator`, and `RemoveTag`.

## Follow-up

The next exact decode opportunity is not in this focused AbilityEntity frontier.
Further improvement needs either a broader MonoBehaviour refresh to find new
unparsed families, or deeper IL2CPP/body evidence for:

- `AbilityEntityFollowData`
- `EnterThrowMode` nested curve/effect/layer/SkillData sections
- the `InteractiveEventComponentData.interactiveActions` list header/grouping
  semantics

# Ability Entity Movement Component Recovery - 2026-07-03

## Summary

Added fail-closed AnimeStudio decoders for the ability-entity movement managed
reference family:

- `Beyond.Gameplay.Core.CharacterMovementComponentData` 64-byte variant
- `Beyond.Gameplay.AbilityEntityTemplateData/BasePositionMovementData`
- `Beyond.Gameplay.AbilityEntityTemplateData/BaseRotationData`
- `Beyond.Gameplay.AbilityEntityTemplateData/SurroundingMovementData`

The 64-byte parent movement payload extends the known 48-byte scalar movement
block with:

- 10 float-compatible scalar words
- `overrideMoveMode` fixed to `13`
- `abilityEntityMovementDataCount` fixed to `2`
- two required managed-reference RID links, exposed as `movementData` and
  `proxyShape`

The parent decoder now succeeds only when `movementData` resolves to
`BasePositionMovementData` and `proxyShape` resolves to either
`BaseRotationData` or `SurroundingMovementData`. The nested records use
IL2CPP-backed field names where proven; Blackboard-backed triplets are still
kept as raw word blocks until their key/value shape is promoted.

## Evidence

Representative pre-patch records came from targeted ability-entity exports under
`tmp/abilityentity_animation_after_68b3/`, `tmp/abilityentity_animation_after_fbad/`,
and `tmp/mono_frontier_camille_checkbuff_adv_after2/`.

Observed 64-byte `CharacterMovementComponentData` examples consistently had:

- word 10: `13` (`overrideMoveMode`)
- word 11: `2` (`abilityEntityMovementDataCount`)
- words 12-15: two 64-bit managed-reference RIDs

Resolved link examples after the patch:

- `data_abilityentity_chr_0011_seraph_normal_skill_pADF527FEC39ABD8F.json`
  links `BasePositionMovementData` and `SurroundingMovementData`.
- `data_abilityentity_chr_0025_ardelia_normal_skill_pA5B4F76F0CB3C2D7.json`
  links `BasePositionMovementData` and `BaseRotationData`.
- `data_abilityentity_chr_0033_camille_normal_skill_pD1E900E2AC5482B0.json`
  links `BasePositionMovementData` and `BaseRotationData`.

Nested payload shapes validated in focused outputs:

| Class | Length | Shape |
| --- | ---: | --- |
| `BasePositionMovementData` | 12 | `surroundingBaseType`, `rotationType`, `mountPoint` |
| `BaseRotationData` | 12 | `baseType`, `mountPoint`, `followSelfRotation` |
| `SurroundingMovementData` | 84 | `centerOffset`, `normalVector`, `radius`, `radiusBB`, `angleSpeed`, `angleSpeedBB`, `rotationClockwise`, `initAngleType`, `initAngle`, `initAngleBB`, `followSelfRotation` |

## Validation

Rebuilt AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with the existing 14 warnings and 0 errors.

Focused exports:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\68B3B9B8EB82E88FBFE6A313E6B18FB6.chk" tmp\abilityentity_movement_after_68b3 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^(data_abilityentity_chr_0011_seraph_normal_skill|data_abilityentity_chr_0025_ardelia_ultimate_skill|data_abilityentity_chr_0025_ardelia_normal_skill)$"

.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk" tmp\abilityentity_movement_after_fbad --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^(data_abilityentity_chr_0028_wulfa_combo_qte_timing|data_abilityentity_chr_0030_zhuangfy_air_attack)$"

.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" tmp\abilityentity_movement_after_3267 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names "^data_abilityentity_chr_0033_camille_normal_skill$"
```

Focused validation metrics across 6 exported JSON files:

| Class | Decoded | Lengths | Partial | Unparsed | Heuristic |
| --- | ---: | --- | ---: | ---: | ---: |
| `CharacterMovementComponentData` | 5 | 64: 4, 48: 1 | 0 | 0 | 0 |
| `BasePositionMovementData` | 4 | 12: 4 | 0 | 0 | 0 |
| `BaseRotationData` | 3 | 12: 3 | 0 | 0 | 0 |
| `SurroundingMovementData` | 1 | 84: 1 | 0 | 0 | 0 |

No `decodeError` entries appeared in the focused outputs.

Follow-up strict validation after adding required RID target checks and named
nested fields used the same three focused export commands with output roots:

- `tmp/abilityentity_movement_strict_after_68b3`
- `tmp/abilityentity_movement_strict_after_fbad`
- `tmp/abilityentity_movement_strict_after_3267`

Strict validation metrics matched the earlier pass:

| Class | Decoded | Lengths | Partial | Unparsed | Heuristic |
| --- | ---: | --- | ---: | ---: | ---: |
| `CharacterMovementComponentData` | 5 | 64: 4, 48: 1 | 0 | 0 | 0 |
| `BasePositionMovementData` | 4 | 12: 4 | 0 | 0 | 0 |
| `BaseRotationData` | 3 | 12: 3 | 0 | 0 | 0 |
| `SurroundingMovementData` | 1 | 84: 1 | 0 | 0 | 0 |

The strict outputs confirmed named nested fields and required RID targets, with
no `decodeError` entries.

## Follow-Ups

- Use IL2CPP field-order evidence before promoting the nested raw words to named
  fields.
- Run a broader MonoBehaviour index refresh later to measure corpus-wide partial
  reduction after the ability-entity movement and animation decoders.

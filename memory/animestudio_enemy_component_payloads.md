# AnimeStudio Enemy Component Payloads

Generated 2026-06-28 after fixing enemy managed-reference segmentation.
This note covers the first schema decoder pass for correctly segmented
`Gameplay.Beyond` enemy component records.

## Evidence Sources

- Corrected raw/JSON sidecars:
  - `D:\fluffy-dump\tmp\mb_enemy_inferred_after\MonoBehaviour\data_eny_0077_agshield_p9FCDDD0503D62AC0.json`
  - `D:\fluffy-dump\tmp\mb_enemy_inferred_after_nefarcore\MonoBehaviour\data_eny_0115_nefarcore_pB090D5EC4BCB9987.json`
- IL2CPP metadata query:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --type-regex "EnemyTemplateData|EnemyRootComponentData|ModelComponentData|RotatorComponentData|CharacterMovementComponentData|NavigationComponentData|AbilitySystemData|EnemyAnimationComponentData|EnemyAIComponentData|RVOComponentData|EnemyControllerData|ControlledStateComponentData|MeshAdjustComponentData|EnemyPivotComponentData|EnemyPartsControllerComponentData|NavMeshObstacleComponentData|EnemyPartsRootComponentData|AbilitySystemForEnemyPartData|EnemyPartAnimatorComponentData|NavMeshObstacleCapsuleData|NavMeshObstacleBoxData" --include-all-members --out tmp\enemy_component_metadata.json --markdown tmp\enemy_component_metadata.md --markdown-cap 30
```

The metadata confirms field names for several small components, but many nested
field type indexes remain unresolved by the local helper. Those records are
marked `$inferred` when the byte layout is proven but exact private field
semantics are not fully named.

## Implemented Decoders

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now decodes these enemy
component families:

- Exact or metadata-backed fields:
  - `ModelComponentData`: `modelId`, `modelScale`, `enableBornFadeIn`,
    `bornFadeInTime`
  - `EnemyAIComponentData`: `aiCfgPath`
  - `EnemyControllerData`: `deadEffectDelay`
  - `ControlledStateComponentData`: three bool fields
  - `NavMeshObstacleCapsuleData`: `m_radius`, `m_height`
  - `NavMeshObstacleBoxData`: `size` vector
- Inferred but bounded layouts:
  - `EnemyRootComponentData`: locator ids/names, transform records, trailing
    words
  - `CharacterMovementComponentData`: 12 float32 words
  - `RVOComponentData`: 3 raw int32 words
  - `MeshAdjustComponentData`: 24 float32 words
  - `EnemyPivotComponentData`: 4 raw words plus `maxWarpRatio`
  - `EnemyPartsRootComponentData`: eight prefix words, `partName`, path/hash
    `partTags`
  - `EnemyPartAnimatorComponentData`: one raw word
  - `EnemyAnimationComponentData`: string animation config path
- Zero-length typed records:
  - `NavigationComponentData`, `PullComponentData`, `EnemyAudioComponentData`,
    `EnemyHurtAnimComponentData`, `PushBackComponentData`,
    `AdditionalBattleShapeComponentData`

## Verification

Build:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with 0 warnings and 0 errors in the incremental pass.

Targeted results:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed |
| --- | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 38 | 23 | 12 |
| `data_eny_0115_nefarcore` | 19 | 17 | 7 | 2 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 |

Remaining unparsed enemy classes after this pass:

- `EnemyTemplateData`
- `AbilitySystemData`
- `AbilitySystemForEnemyPartData`
- `EnemyPartsControllerComponentData`
- `NavMeshObstacleComponentData`

These are deliberately left as heuristic/unparsed because their nested
RID/list payloads need more schema evidence. Raw-dumping the whole payload would
hide the remaining unknowns rather than resolve them.
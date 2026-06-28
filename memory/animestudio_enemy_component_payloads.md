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

## Wrapper Decoder Follow-up

A follow-up pass decoded two nested wrapper families that were left open in the
first component pass:

- `EnemyPartsControllerComponentData`: `partsData[]` entries with part name,
  unknown aligned name, unknown mode, six bounded float words, and typed RID
  links to the root/ability/animator component records for each part.
- `NavMeshObstacleComponentData`: `configList[]` entries with unknown aligned
  name, visible config name, ten bounded float words, and typed RID links to
  capsule/box obstacle shape records.

Verification after this wrapper pass:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed |
| --- | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 40 | 25 | 10 |
| `data_eny_0115_nefarcore` | 19 | 17 | 7 | 2 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 |

Remaining unparsed classes are now limited to:

- `EnemyTemplateData`
- `AbilitySystemData`
- `AbilitySystemForEnemyPartData`

## Template And Enemy-Part Ability Follow-up

A follow-up pass decoded two more enemy managed-reference families:

- `EnemyTemplateData`: model key, variable word-aligned attributes block,
  post-model key, rank/sub-rank flags, and animation config path. The raw order
  is not the same as the first IL2CPP field listing: the attributes block sits
  between `modelKey` and the post-model/rank/path tail in observed payloads.
- `AbilitySystemForEnemyPartData`: word-aligned numeric payload. Seven observed
  agshield records have a validated 20-word scalar tail matching the metadata
  fields after `partAttributes`; one 840-byte record is preserved as an explicit
  `$partial` raw numeric payload because its longer tail does not satisfy the
  same bool/enum/float constraints.

Verification after this pass:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed | Partial |
| --- | ---: | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 49 | 34 | 1 | 1 |
| `data_eny_0115_nefarcore` | 19 | 18 | 8 | 1 | 0 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 | 0 |

The only remaining unparsed class in these two enemy samples is
`AbilitySystemData`. The partial agshield part-ability record is no longer a
warning/error, but it is still intentionally marked partial until the longer
variant's nested attribute layout is understood.

## AbilitySystemData Follow-up

A fourth pass added a partial structured decoder for `AbilitySystemData`:

- `shapeData` is decoded as `detectedRadius` and `detectedHeight` from the
  `BasicShapeData` metadata.
- `modeConfig.modes` is decoded as counted `ModeData` records through the
  verified fields ending at `animBoolName`; each mode keeps its compact tail as
  explicit raw words because the later conditional fields are not yet fully
  semantic.
- The remaining payload is preserved as a large word-aligned raw tail with
  string hints. This removes heuristic/unparsed warnings while keeping the
  still-unknown `SkillDataBundle`, UI, blackboard, baked-mesh, effect, and
  preload sections visible for later schema work.

Verification after this pass:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed | Partial |
| --- | ---: | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 50 | 35 | 0 | 2 |
| `data_eny_0115_nefarcore` | 19 | 19 | 9 | 0 | 1 |
| `data_facemorph_avatar_antal` regression | 243 | 243 | 243 | 0 | 0 |

The two enemy samples now have no heuristic or unparsed managed-reference
records. Remaining semantic gaps are intentionally marked `$partial`:
`AbilitySystemData` in both samples and the longer 840-byte
`AbilitySystemForEnemyPartData` variant in `data_eny_0077_agshield`.

## AbilitySystem Skill Bundle Follow-up

A fifth pass improved the remaining enemy `AbilitySystemData` semantic tail
without changing the generic managed-reference recovery/classification path:

- `ModeData` now decodes the metadata-backed tail fields after `animBoolName`:
  `overrideStateClip`, optional raw `overrideClipMapping`, `overrideAnimCfg`,
  `animCfgPath`, `overrideModelKey`, `modelKey`, `mountPointDefIndex`,
  `overrideCmdMapping`, and the observed four-word raw `cmdMapping` block.
- `SkillDataBundle` is decoded through `comboSkillSpecialNodeName`. This
  exposes the enemy skill/passive string lists while deliberately leaving
  `defaultCmdMapping` and later `AbilitySystemData` sections in
  `remainingRawWords`.
- The UI, blackboard, baked-mesh point/path, extra-shape, skill-camera,
  effect, health, preload, and max-potential-effect sections remain unknown.
  They are still preserved as structured raw words plus string hints; no data is
  dropped to suppress partial status.

Verification after this pass:

| Sample | Refs | Decoded | Inferred | Heuristic/unparsed | Partial | AbilitySystem remaining words |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| `data_eny_0077_agshield` | 50 | 50 | 35 | 0 | 2 | 5132 |
| `data_eny_0115_nefarcore` | 19 | 19 | 9 | 0 | 1 | 554 |

Compared to the prior `AbilitySystemData` pass, agshield's remaining raw tail
shrinks from 5365 to 5132 words, and nefarcore's from 583 to 554 words. The
partial counts are unchanged because `AbilitySystemData` is still intentionally
partial, and agshield still has the one long 840-byte
`AbilitySystemForEnemyPartData` variant with a raw numeric payload.

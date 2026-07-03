# AbilityEntity Root Recovery - 2026-07-03

## Result

AnimeStudio now decodes `Beyond.Gameplay.Core.AbilityEntityRootComponentData`
managed-reference payloads instead of preserving them as partial raw words.

The decoder is byte-guarded:

- requires the observed eight-word zero prefix;
- decodes the ten MemoryPack setter-backed fields;
- consumes `BlackboardInt` as `bool32 useBlackboardKey`, `int32 value`,
  aligned `blackboardKey`;
- consumes `BlackboardDouble` as `bool32 useBlackboardKey`, `float32 value`,
  aligned `blackboardKey`;
- falls back to the previous partial raw diagnostic on any mismatch.

`Beyond.Gameplay.AbilityEntityTemplateData` remains partial, but the exporter
now also exposes its duplicated leading `abilityentity_*` key pair as
`abilityEntityKey`, `abilityEntityKeyMirror`, and
`abilityEntityKeyPrefixBytes`.

## Evidence

Local IL2CPP metadata plus generated MemoryPack wrappers expose the root setter
surface:

```text
maxStackingCnt, maxStackingCntBB, lifeType, duration, durationBB,
isEnergySource, maxIgniteNum, maxIgniteNumBB, moveUseFrameTick, headBarType
```

Focused final validation used `tmp/abilityentity_root_template_prefix_after_20260703`.
The saved StreamingAssets asset map selected 160 current AbilityEntity files,
the saved Persistent asset map selected 1, and
`data_abilityentity_eny_0051_rodin_wall_p8D1AC2C6602E462F.json` was exported
directly by name from its source bundle because the saved map did not select it.

Validation counts:

```text
files: 162 unique AbilityEntity JSON files
AbilityEntityRootComponentData: 162 structured, 0 partial, 0 raw-word fallback
AbilityEntityTemplateData: 162 partial, 162 with duplicated key prefix decoded
non-empty root blackboard keys decoded: 6
```

Non-empty root blackboard keys observed:

```text
EntityBB_bat_duration
EntityBB_swordLimit
EntityBB_swordDuration
EntityBB_duration
```

Representative decoded values include:

```text
data_abilityentity_chr_0030_zhuangfy_normal_skill_sword:
  maxStackingCnt = 5
  maxStackingCntBB = EntityBB_swordLimit, value 18
  duration = 45.0
  durationBB = EntityBB_swordDuration, value 0.0
  moveUseFrameTick = true

data_abilityentity_chr_0033_camille_normal_skill:
  duration = 30.0
  durationBB = EntityBB_bat_duration, value 5.0
```

## Remaining Frontier

The larger `AbilityEntityTemplateData` payload is still semantic/structural
frontier work. It contains duplicated base keys, gameplay tags, skill/model/nav/
physical/interactive sections, and nested tails. The current change intentionally
does not claim that full template layout is decoded.

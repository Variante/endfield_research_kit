# CheckRpgEquipCount Recovery - 2026-07-03

## Scope

This pass promotes non-empty
`Beyond.Gameplay.Core.CheckRpgEquipCount` managed-reference payloads from
generic raw diagnostics into named condition lists.

It covers the current partial `team_effect_rpg_check_equip_cnt_dmg_up` payloads.
The existing empty `team_effect_bonus_when_few_equip` reference remains an empty
decoded object.

## Evidence

IL2CPP metadata names:

- `CheckRpgEquipCount.tierConditions`
- `CheckRpgEquipCount.countConditions`
- nested `CompareWrapper.compareType`
- nested `CompareWrapper.value`

The nested `value` field uses the existing `Beyond.Blackboard.BlackboardDouble`
shape:

```text
bool32 useBlackboardKey
float32 value
aligned ASCII blackboardKey
```

All three observed non-empty payloads are 40 bytes:

```text
int32 tierConditions.count
CompareWrapper tierConditions[0]
int32 countConditions.count
CompareWrapper countConditions[0]
```

Current observed values:

- `tierConditions[0].compareType`: `4`
- `tierConditions[0].value`: `2.0`, `3.0`, or `1.0`
- `countConditions[0].compareType`: `3`
- `countConditions[0].value`: `1.0`

## Implementation

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now routes
`Gameplay.Beyond/Beyond.Gameplay.Core/CheckRpgEquipCount` through a dedicated
decoder before the generic low-volume fallback.

The decoder requires:

- a valid `CheckRpgEquipCount` managed-reference header
- condition-list counts in `0..16`
- each `CompareWrapper` to parse as `compareType` plus a BlackboardDouble value
- exact stream completion after `countConditions`

`compareType` is emitted as a bounded enum value without guessed enum names.

## Validation

Built AnimeStudio CLI:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

The build succeeded with the existing AnimeStudio warning set and `0` errors.

Focused export output:

```text
tmp\check_rpg_equip_after_20260703
```

Validation results:

- exported JSON files: `2`
- existing empty `CheckRpgEquipCount` refs: `1`
- non-empty `CheckRpgEquipCount` refs decoded: `3`
- `tierConditions` rows decoded: `3`
- `countConditions` rows decoded: `3`
- validation assertion errors: `0`
- no non-empty decoded ref retained `$partial`, `$unparsed`, `$heuristic`,
  `heuristicRawWordHints`, or generic top-level `rawWords`

# MonoBehaviour ProjectileComponentData status - 2026-06-30

## Target

The current focused projectile probe showed one active unparsed managed-reference
payload:

- Type: `Beyond.Gameplay.Core.ProjectileComponentData`.
- Assembly: `Gameplay.Beyond`.
- Example source:
  `data_projectile_chr_0033_camille_attack4_p59456F953E4D0820.json`.
- Payload offset/length in the focused object: offset `1436`, length `1456`.

The same object already decoded these sibling managed refs with the current CLI:

- `Beyond.Gameplay.ProjectileTemplateData`.
- `Beyond.Gameplay.Core.ProjectileRootComponentData`.
- `Beyond.Gameplay.Core.AbilitySystemData`, still partial for nested ability data.

## Metadata Evidence

The repo-local IL2CPP metadata parser against cached `global-metadata.dat`
shows `ProjectileComponentData` field order:

`id`, `finishDuration`, `finishDistance`, `finishOnReach`, `hitOnReach`,
`colliderShapeData`, `blockLayerDef`, `blockLayer`, `targetFilter`,
`ignoreImmuneLevel`, `maxHitCount`, `allowHitSameTarget`,
`hitIntervalPerTarget`, `keepMoveOnReach`, `presetPointKeys`,
`useSegmentMove`, `moveSegments`, `moveModeDict`, `mainEffectFinishType`,
`mainEffectFinishDistance`, `mainEffects`, `launchEffects`,
`showReachEffectOnlyWithTarget`, `reachEffects`, `hitEffects`, `blockEffects`,
`showFinishEffectOnlyWhenUnblockAndNotHit`, `finishEffects`,
`showAlertEffect`, `alertEffect`, `launchSound`, `loopSound`, `reachSound`,
`hitSound`, `blockSound`, `finishedSound`, `sizzleSound`,
`sizzleSoundTriggerDistance`, `ringProjectileSoundSmoothFactor`.

Nested metadata used for the promoted prefix:

- `ShapeData`: `shapeType`, `radius`, `center`, `extent`, `initOuterRadius`,
  `initInnerRadius`, `outerRadiusIncreaseSpeed`, `innerRadiusIncreaseSpeed`,
  `height`, `isSector`, `sectorDirection`, `sectorAngle`.
- `TargetFilter`: `checkAlive`, `autoSetTargetFaction`, `factionTarget`,
  `targetFactionType`, `filterSlot`, `slotIndex`, `filterGameplayTag`,
  `tagQuery`.
- `MoveSegment`: `startPointKey`, `moveModeId`, `endPointKey`,
  `earlyNextByDuration`, `segmentDuration`, `speedLerpTime`.

## Implementation

Added a conservative `ProjectileComponentData` decoder in
`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs`.

The decoder:

- marks the payload `$decoded`, `$partial`, and `$inferred`;
- decodes the metadata-backed prefix through `moveSegments`;
- names `ShapeData`, `TargetFilter`, and `MoveSegment` substructures;
- adds a `Beyond.Blackboard.BlackboardInt` raw three-word helper for
  `maxHitCount`;
- preserves the remaining fields from `moveModeDict` onward as a raw
  metadata-ordered `tail` diagnostic.

The tail stays raw intentionally. The current bytes contain nested dictionaries,
effect arrays, projectile sound structs, and final scalar fields; those shapes
need a separate cross-sample proof before being promoted.

## Validation

Build:

- `.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore`
- Result: succeeded, `0 Warning(s)`, `0 Error(s)`.

Focused exact probe:

- Source chunk:
  `D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk`
- Filtered object:
  `data_projectile_chr_0033_camille_attack4`
- Result: `ProjectileComponentData` now has no `$unparsed` or `$heuristic`
  marker. It remains `$partial`, with prefix fields decoded and tail length
  `1028` bytes.

Batch probe:

- 10 same-bundle projectile MonoBehaviours.
- Exported JSON count: 10.
- `ProjectileComponentData` entries decoded: 10.
- `ProjectileComponentData` `$unparsed`: 0.
- `ProjectileComponentData` `$heuristic`: 0.
- Payload lengths covered: `1456`, `1932`, `2400`, `2932`, `3532`, `3540`.
- Tail lengths covered: `1028`, `1496`, `1968`, `2492`, `3004`.

The remaining `$heuristic` and `decodeError` markers in those files belong to
the managed-reference registry recovery wrapper, not to
`ProjectileComponentData` itself.

## Remaining Unknowns

- Exact serialization of `moveModeDict`.
- Exact effect-list item layouts for `mainEffects`, `launchEffects`,
  `reachEffects`, `hitEffects`, `blockEffects`, and `finishEffects`.
- Exact projectile sound struct layout for `launchSound`, `loopSound`,
  `reachSound`, `hitSound`, `blockSound`, `finishedSound`, and `sizzleSound`.
- Whether non-default `TargetFilter` variants require richer enum names for
  faction and target-faction fields.

Next pass should use the 300 projectile payload family to prove the tail
collection boundaries before removing the `$partial` marker.

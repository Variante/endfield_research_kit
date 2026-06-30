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

## MoveModeDict Header Follow-up

The current export contains 10 `data_projectile_*` MonoBehaviours in the active
same-bundle projectile set. A second pass decoded only the `moveModeDict`
dictionary header and left the `MoveModeData` values plus subsequent
effect/sound/scalar fields as raw words.

Validated shape:

- 5 payloads have one key: `Default`.
- 5 payloads have four keys: `Default`, `T1`, `T2`, `T3`.
- Every decoded `valueCount` matches `keyCount`.
- `ProjectileComponentData` still has no `$unparsed`, `$heuristic`, or
  `decodeError` marker across the 10 exported JSON files.
- Remaining raw word counts after the dictionary header are `252`, `369`,
  `487`, `618`, and `740`.

This is promoted as a partial diagnostic only. A local full `MoveModeData`
prototype failed at the speed-info fields, so the nested values are not yet
safe to name. The available DummyDll reflection path is also not reliable for
this family; field order comes from `global-metadata.dat` and byte evidence.

Build and focused validation:

- `.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore`
- Result: succeeded with the existing project warnings and `0 Error(s)`.
- Targeted export:
  `tmp\projectile_component_movemode_after_20260630`.

## MoveModeData Value Follow-up

A byte-level pass over `tmp\projectile_component_movemode_after_20260630`
proved the value boundary inside `moveModeDict`:

- each `MoveModeData` value is exactly 124 int32 words, or 496 bytes;
- one-key samples therefore consume 124 value words after the dictionary header;
- four-key samples consume 496 value words after the dictionary header;
- suffix strings for effect names start immediately after that boundary in 9 of
  the 10 focused samples, and the remaining `attack4` sample has a plausible
  zero/count/scalar suffix with no ASCII effect string;
- the old raw tail minus the decoded dictionary header matches the current
  `remainingRawWords` bytes exactly for all 10 samples.

The exporter now emits keyed partial `MoveModeData` records under
`moveModeDict.values`. Each record decodes the metadata-backed prefix through
`parabolaDef` and preserves the remaining 115 words in that fixed-size value
record as raw data.

Focused validation after the change:

- `.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore`
- Result: succeeded with `0 Warning(s)` and `0 Error(s)`.
- Targeted export:
  `tmp\projectile_component_movemode_values_after_20260630`.
- Exported JSON count: 10.
- `moveModeDict` key distribution: five one-key rows and five four-key rows.
- Decoded `MoveModeData` values: 25.
- Value sizes: every value has `wordCount = 124` and `length = 496`.
- Per-value raw remainder: every value preserves 115 raw words after the named
  prefix.
- `ProjectileComponentData` `$unparsed`, `$heuristic`, and `decodeError`: 0.

Observed raw prefix values across the 25 value records:

- `traceType`: value `0` in 1 record, value `1` in 1 record, value `2` in 23 records.
- `moveType`: value `0` in 8 records, value `2` in 17 records.
- `parabolaDef`: value `0` in 25 records.

The JSON includes the IL2CPP enum type for those fields but intentionally does
not attach enum member names yet.

Metadata caveats:

- `global-metadata.dat` confirms the `MoveModeData` field order and names the
  enum types `ProjectileTraceType`, `ProjectileMoveType`, and
  `ProjectileParabolaDef`, but the numeric enum constants need a separate
  reliable proof before member names are emitted.
- The metadata entry is
  `Beyond.Gameplay.Core.ProjectileComponentData+MoveModeData`, type `10992`,
  with `fieldStart = 47811` and `fieldCount = 22`.
- The same metadata pass names the post-`parabolaDef` field order as
  speed-info strings, `BlackboardDouble` scalar wrappers, `UnityEngine.AnimationCurve`
  records, bool fields, and two `ProjectileComponentData+BezierPoint` records,
  but the byte layouts for those nested structures still need validation.
- The current metadata helper does not resolve several generic field type
  indices to friendly names, so the speed-info, curve, and BezierPoint payloads
  are still byte-validated raw words rather than decoded structures.
- `tools\DummyDll` and `tools\Cpp2IL-endfield-patched-dlls4` do not expose the
  projectile data types through the local Mono.Cecil probe, so they cannot
  replace the byte evidence for this family.

## Remaining Unknowns

- Exact internals of `MoveModeData` after `parabolaDef`: speed-info wrappers,
  `FAnimationCurve` records, scalar bools, BlackboardDouble wrappers, and
  BezierPoint records.
- Exact effect-list item layouts for `mainEffects`, `launchEffects`,
  `reachEffects`, `hitEffects`, `blockEffects`, and `finishEffects`.
- Exact projectile sound struct layout for `launchSound`, `loopSound`,
  `reachSound`, `hitSound`, `blockSound`, `finishedSound`, and `sizzleSound`.
- Whether non-default `TargetFilter` variants require richer enum names for
  faction and target-faction fields.

Next pass should use the 300 projectile payload family to prove the tail
collection boundaries before removing the `$partial` marker.

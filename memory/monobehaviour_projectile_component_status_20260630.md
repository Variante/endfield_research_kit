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

## MoveModeDict Container Status Follow-up

The current pass promoted only the `moveModeDict` dictionary container. The nested `MoveModeData` values remain partial.

Evidence:

- Current focused output still covers 10 `data_projectile_chr_0033_camille_*` MonoBehaviours.
- `moveModeDict` appears 10 times.
- Every dictionary has matching `keyCount` and `valueCount`.
- Key distribution is unchanged: `Default` appears 10 times, and `T1`, `T2`, `T3` each appear 5 times.
- The dictionary has no container-level raw remainder after keys and fixed-size values are consumed.
- The nested values remain unresolved: 25 `MoveModeData` records, each `wordCount = 124`, `length = 496`, with `decodedPrefixWordCount = 9` and `remainingRawWordCount = 115`.
- Parent `ProjectileComponentData` remains partial because effect, sound, and final scalar tail collections still remain raw after `moveModeDict`.

Implementation:

- `ReadProjectileMoveModeDictDiagnostic` now emits `$decoded` instead of `$partial` for the dictionary container.
- It adds `observedPayloadStatus` and `nestedPartialReasons` to make clear that the dictionary itself is consumed while nested values and the enclosing parent tail still need semantic work.
- `ReadProjectileMoveModeDataDiagnostic` still emits `$partial`; it now also emits `observedPayloadStatus`, `partialReasons`, `decodedPrefixWordCount`, and `remainingRawWordCount`.
- No enum member names or raw tail fields were promoted.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 warnings and 0 errors.

Targeted validation output: `tmp\projectile_movemode_dict_status_after_20260630` using the 10-row `tmp\projectile_component_movemode_values_after_20260630\filter_data.json` file.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 10 |
| `ProjectileComponentData` records | 10 |
| `ProjectileComponentData` records still `$partial` | 10 |
| `moveModeDict` dictionaries | 10 |
| `moveModeDict` dictionaries marked `$decoded` | 10 |
| `moveModeDict` dictionaries still `$partial` | 0 |
| Dictionaries with matching key/value counts | 10 |
| `MoveModeData` values | 25 |
| `MoveModeData` values still `$partial` | 25 |
| `MoveModeData` values marked `$decoded` | 0 |
| `MoveModeData wordCount = 124` | 25 |
| `MoveModeData length = 496` | 25 |
| `decodedPrefixWordCount = 9` | 25 |
| `remainingRawWordCount = 115` | 25 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |

Current classification: the dictionary container is structurally decoded. The next real projectile work is still inside `MoveModeData` value internals and the parent effect/sound/scalar tail, not in the dictionary key/value boundary.

## Tail MainEffect Finish And MoveModeData Suffix Follow-up

The current pass promoted two parent tail fields after `moveModeDict` and added a guarded structured view for the nested `MoveModeData` suffix. It still keeps the projectile family partial.

Evidence:

- The focused Camille projectile slice still covers 10 `ProjectileComponentData` records and 25 nested `MoveModeData` records.
- IL2CPP metadata places `mainEffectFinishType` and `mainEffectFinishDistance` immediately after `moveModeDict`.
- Tail byte evidence matches that order: one enum word followed by the three-word `Beyond.Blackboard.BlackboardDouble` shape already used elsewhere in `ProjectileComponentData`.
- `mainEffectFinishType` is `0` in all 10 focused samples.
- The middle BlackboardDouble word for `mainEffectFinishDistance` is `0` in 9 samples and `1119092736` in 1 sample.
- The remaining raw parent tail dropped by exactly four words per sample: `{128:1, 244:5, 245:2, 363:1, 494:1}` became `{124:1, 240:5, 241:2, 359:1, 490:1}`.
- A parallel MoveModeData suffix probe found that the metadata fields `m_parabolaSpeedInfo`, `m_bezierSpeedInfo`, and `m_speedCurveInfo` do not have serialized bytes in the focused payloads.
- The suffix boundary after `parabolaDef` is now byte-proven for `speed`, `speedCurve`, `useSpeedScaleWithDistance`, `speedScaleWithDistance`, `lockVelocityToXZ`, `groundedMove`, `limitAngularSpeed`, `angularSpeed`, `angularSpeedCurve`, `travelDuration`, `vertexYOffset`, `gravity`, and bounded BezierPoint records.
- `speedCurve` has 2 keyframes in all 25 records, `speedScaleWithDistance` has 2 keyframes in 24 records and 4 keyframes in 1 record, and `angularSpeedCurve` has 2 keyframes in all 25 records.
- `bezierMidPoint1` is a complete 21-word raw record in all 25 records. `bezierMidPoint2` is a complete 21-word raw record in 24 records and a truncated 7-word raw record in 1 record.

Implementation:

- `ReadProjectileComponentTailDiagnostic` now decodes `mainEffectFinishType` with `ReadPayloadEnum32Candidate`.
- `ReadProjectileComponentTailDiagnostic` now decodes `mainEffectFinishDistance` with `ReadAbilitySystemBlackboardDouble`.
- `ReadProjectileMoveModeDataDiagnostic` now adds `structuredSuffix` beside the original `remainingRawWords`.
- The structured suffix decodes scalar, bool, and `AnimationCurve<float>` boundaries while preserving BezierPoint records as bounded raw records.
- The original 115-word `remainingRawWords` suffix is still emitted for every `MoveModeData` record.
- Parent `ProjectileComponentData`, its tail, every `MoveModeData`, every structured suffix, and BezierPoint raw records remain `$partial`.
- No effect list, sound struct, final scalar, enum member name, or BezierPoint range-wrapper internals were promoted.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Latest rebuild result: 0 warnings and 0 errors.

Targeted validation output: `tmp\projectile_tail_and_movemode_suffix_after_20260630` using the same 10-row `tmp\projectile_component_movemode_values_after_20260630\filter_data.json` file.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 10 |
| `ProjectileComponentData` records | 10 |
| `ProjectileComponentData` records marked `$decoded` | 10 |
| `ProjectileComponentData` records still `$partial` | 10 |
| Tails with `mainEffectFinishType` | 10 |
| Tails with `mainEffectFinishDistance` | 10 |
| `moveModeDict` dictionaries marked `$decoded` | 10 |
| `MoveModeData` values | 25 |
| `MoveModeData` values still `$partial` | 25 |
| `MoveModeData` original raw suffix length 115 words | 25 |
| Structured suffix decode status `decoded` | 25 |
| `speedCurve` keyframes = 2 | 25 |
| `speedScaleWithDistance` keyframes = 2 | 24 |
| `speedScaleWithDistance` keyframes = 4 | 1 |
| `angularSpeedCurve` keyframes = 2 | 25 |
| `bezierMidPoint1` word count = 21 | 25 |
| `bezierMidPoint2` full 21-word record | 24 |
| `bezierMidPoint2` truncated 7 raw words | 1 |
| Remaining parent tail raw word counts | `{124:1, 240:5, 241:2, 359:1, 490:1}` |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |

Current classification: the parent projectile tail is decoded through `mainEffectFinishDistance`, and nested `MoveModeData` values now have a guarded structured suffix view. The remaining projectile parent-tail unknown starts at `mainEffects`; the nested value unknowns are BezierPoint internals and non-serialized speed-info metadata fields.

## BezierPoint Full Record Decode Follow-up

The current pass decoded the full 21-word `ProjectileComponentData/BezierPoint` records inside `MoveModeData.structuredSuffix` while preserving the observed truncated second point as raw bytes.

Evidence:

- The focused Camille projectile slice still covers 10 `ProjectileComponentData` records and 25 nested `MoveModeData` records.
- Full BezierPoint records have a stable 21-word payload that matches IL2CPP field order: `usePresetPoint`, `presetPointKey`, `xRatioRange`, `yzAngleRange`, `yzRadiusRange`, and `scaledYzRadius`.
- The full record shape is `bool32`, aligned ASCII string, three two-endpoint `BlackboardDouble` ranges, then `bool32`.
- All 49 full BezierPoint records in the focused slice decode with `presetPointKey = ""` and `scaledYzRadius = true`.
- The one short `bezierMidPoint2` case is still represented by the existing `truncated; 7 raw words preserved` path and is not forced through the full parser.
- The original 115-word `MoveModeData.remainingRawWords` suffix is still emitted for every value.

Implementation:

- `ReadProjectileBezierPointRawRecord` now decodes full 21-word records into fields instead of preserving them as opaque raw words.
- Added `ReadProjectileBlackboardDoubleRange` for the three BezierPoint range fields.
- Kept decoded BezierPoint records marked `$inferred` because the local metadata dump still does not resolve the wrapper type name for the range fields.
- Kept truncated BezierPoint records marked `$partial` and raw.
- Kept `MoveModeData` and `structuredSuffix` marked `$partial` because one `bezierMidPoint2` remains truncated and parent projectile effect/sound tails are still unresolved.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Latest rebuild result: 0 errors and the same 14 existing AnimeStudio project warnings.

Targeted validation output: `tmp\projectile_bezierpoint_decode_after_20260630` using the same 10-row `tmp\projectile_component_movemode_values_after_20260630\filter_data.json` file.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 10 |
| `ProjectileComponentData` records | 10 |
| `MoveModeData` values | 25 |
| `MoveModeData` original raw suffix length 115 words | 25 |
| Structured suffix decode status `decoded` | 25 |
| Full BezierPoint records | 49 |
| Full BezierPoint records marked `$decoded` | 49 |
| Full BezierPoint records marked `$partial` | 0 |
| Full BezierPoint `presetPointKey = ""` | 49 |
| Full BezierPoint `scaledYzRadius = true` | 49 |
| `bezierMidPoint2` full 21-word record | 24 |
| `bezierMidPoint2` truncated 7 raw words | 1 |
| Remaining parent tail raw word counts | `{124:1, 240:5, 241:2, 359:1, 490:1}` |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |

Current classification: full BezierPoint records in the focused projectile suffix are decoded. The remaining nested projectile unknown is the single truncated `bezierMidPoint2` variant plus the non-serialized speed-info metadata fields; the remaining parent-tail unknown still starts at `mainEffects`.
## Parent Tail End Suffix Follow-up

The current pass adds a guarded end-relative structured view of the `ProjectileComponentData` parent tail after `mainEffectFinishDistance`. It does not assign the variable `P_fxbat_*` effect blocks to named effect-list fields yet.

Evidence:

- The focused Camille projectile slice still covers 10 `ProjectileComponentData` records.
- The raw parent tail after `mainEffectFinishDistance` still has word counts `{124:1, 240:5, 241:2, 359:1, 490:1}`.
- The final 116 words decode consistently as the current default alert/sound/scalar suffix.
- The variable prefix before that suffix remains raw and has word counts `{8:1, 124:5, 125:2, 243:1, 374:1}`.
- `showAlertEffect` is `false` in all 10 focused samples.
- `alertEffect` is a bounded 106-word default effect record in all 10 focused samples and is still preserved raw.
- `launchSound`, `loopSound`, `reachSound`, `hitSound`, `blockSound`, `finishedSound`, and `sizzleSound` are empty strings in all 10 focused samples.
- `sizzleSoundTriggerDistance` is `0.0` and `ringProjectileSoundSmoothFactor` is `0.1` in all 10 focused samples.
- The original `remainingRawWords` tail is still emitted unchanged for byte audit.

Implementation:

- `ReadProjectileComponentTailDiagnostic` now adds `structuredRemainingTail` before `remainingRawWords`.
- `ReadProjectileComponentRemainingTailDiagnostic` decodes the stable end-relative suffix through current alert/sound/scalar fields using a local reader.
- `ReadProjectileDefaultEffectRecordDiagnostic` bounds and preserves the current default `alertEffect` record as raw words.
- The variable effect-list/finish prefix remains raw under `effectListAndFinishPrefixRawWords`.
- `ProjectileComponentData`, `structuredRemainingTail`, and `alertEffect` remain `$partial`.
- No named effect-list assignment, non-empty sound layout, or effect-record internals were promoted.

Validation:

```text
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Rebuild result: 0 errors and the same 14 existing AnimeStudio project warnings.

Targeted validation output: `tmp\projectile_tail_suffix_decode_after_20260630` using the same 10-row `tmp\projectile_component_movemode_values_after_20260630\filter_data.json` file.

| Metric | Result |
| --- | ---: |
| MonoBehaviour JSON files | 10 |
| `ProjectileComponentData` records | 10 |
| Structured remaining tails | 10 |
| Structured remaining tails decoded | 10 |
| Parent raw tail word counts | `{124:1, 240:5, 241:2, 359:1, 490:1}` |
| Raw effect/finish prefix word counts | `{8:1, 124:5, 125:2, 243:1, 374:1}` |
| `showAlertEffect = false` | 10 |
| `alertEffect` default records with 106 raw words | 10 |
| Empty `launchSound` / `loopSound` / `reachSound` / `hitSound` / `blockSound` / `finishedSound` / `sizzleSound` | 10 each |
| `sizzleSoundTriggerDistance = 0.0` | 10 |
| `ringProjectileSoundSmoothFactor = 0.1` | 10 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |

Current classification: the parent projectile tail now has a structured view through the stable end-relative alert/sound/scalar suffix. The unresolved parent-tail work is still the variable effect-list/finish prefix and the internal/default effect-record layout.
## AlertEffect Boundary Correction

This pass supersedes the earlier `structuredRemainingTail` interpretation that split the end-relative suffix into `alertEffect`, seven sound strings, and two scalar floats.

A 300-projectile raw payload audit showed that the bytes after `showAlertEffect` are better classified as one bounded `Beyond.Gameplay.EffectActionCfg` alert-effect variant that consumes through the observed tail end. The previously decoded sound/scalar fields are not byte-proven as a separate suffix in this corpus and are no longer emitted by the structured view.

Evidence:

- Raw payload slice count: 300 `ProjectileComponentData` payloads.
- Alert-effect names observed:
  - empty/default: 271 structured tails.
  - `P_skillalert_circle_01`: 13 structured tails.
  - `P_skillalert_circle_01_02`: 11 structured tails.
- Suffix word counts, including `showAlertEffect`:
  - default/empty: 116 words.
  - `P_skillalert_circle_01`: 122 words.
  - `P_skillalert_circle_01_02`: 123 words.
- `alertEffect.fxType = 1` in every decoded structured tail.
- The alert-effect parser now field-decodes only `fxType` and `effectName`, then preserves the remaining EffectActionCfg words raw.

Validation output:

```text
tmp\projectile_alert_effect_validation_after_20260630
```

Validation summary:

| Metric | Result |
| --- | ---: |
| ProjectileComponentData records | 300 |
| Structured remaining tails | 295 |
| Structured remaining tails decoded | 295 |
| AlertEffect records | 295 |
| AlertEffect records still `$partial` | 295 |
| `alertEffect.serializedWordCount = 115` | 271 |
| `alertEffect.serializedWordCount = 121` | 13 |
| `alertEffect.serializedWordCount = 122` | 11 |
| `alertEffect.remainingRawWordCount = 113` | 295 |
| Separate decoded sound/scalar suffix fields emitted | 0 |

Current classification: the projectile parent-tail end boundary is understood as `showAlertEffect` plus a bounded partial `EffectActionCfg` alert effect. The inner `EffectActionCfg` fields remain partial, and the projectile metadata sound fields are not byte-proven in this sample set.

## Adaptive BlackboardDouble And MainEffect Finish Guard

This pass resolves the five whole-record `ProjectileComponentData` decode misses from the 300-projectile validation slice.

Root cause:

- The projectile reader treated `Beyond.Blackboard.BlackboardDouble` as a fixed three-word wrapper.
- Five payloads serialize dynamic blackboard-key strings in the opening `finishDuration`/`finishDistance` fields:
  - `data_projectile_harddung_healball_02`
  - `data_projectile_cc_level_healball_02`
  - `data_projectile_chr_0030_zhuangfy_attack_sword_1`
  - `data_projectile_chr_0030_zhuangfy_attack_sword_2`
  - `data_projectile_chr_0030_zhuangfy_normal_skill_gene_sword`
- Three Zhuangfy payloads also start `mainEffectFinishDistance` immediately after `moveModeDict`; the metadata-listed `mainEffectFinishType` word is omitted in those observed variants.

Implementation:

- `ReadAbilitySystemBlackboardDouble` now prefers the metadata-backed `bool32 useBlackboardKey`, `float32 value`, aligned `blackboardKey` shape and falls back to the previous raw three-word wrapper when that shape does not validate.
- The reader preserves `valueFloatCandidate` in both shapes for existing summaries.
- `ReadProjectileComponentTailDiagnostic` now guards `mainEffectFinishType`: it accepts enum values `0..2` (`Default`, `ByTargetPosition`, `ByMaxDistance`), otherwise tries the observed distance-only variant and marks `mainEffectFinishTypeSerialized = false`.
- Failed focused `ProjectileComponentData` decodes now retain the known layout and `decodeError` instead of collapsing into an anonymous heuristic-only fallback.

Validation output:

```text
tmp\projectile_blackboard_adaptive_validation_after_20260630
```

Validation summary:

| Metric | Result |
| --- | ---: |
| Projectile template JSON files | 300 |
| `ProjectileComponentData` references | 300 |
| Decoded `ProjectileComponentData` layouts | 300 |
| Structured tails | 300 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |
| `mainEffectFinishTypeSerialized = true` | 294 |
| `mainEffectFinishTypeSerialized = false` | 6 |
| `BlackboardDouble` `bool-float-key` records | 10,560 |
| `BlackboardDouble` raw three-word fallback records | 48 |
| `alertEffect.effectName = ""` | 276 |
| `alertEffect.effectName = P_skillalert_circle_01` | 13 |
| `alertEffect.effectName = P_skillalert_circle_01_02` | 11 |

Remaining projectile diagnostic work at this stage:

- `ProjectileComponentData` remained parent `$partial` because effect-list assignment, inner `EffectActionCfg`, and some `MoveModeData` internals were still intentionally raw/diagnostic.
- The nested `BezierPoint` `decodeError` diagnostics listed here are resolved by the following terminal-prefix recovery pass.

## Terminal BezierPoint Prefix Recovery

This pass resolves the remaining nested `BezierPoint` `decodeError` diagnostics from the 300-projectile validation slice and removes the raw/truncated midpoint statuses introduced by fixed 21-word slicing.

Root cause:

- `MoveModeData` has fixed 124-word values, but `BezierPoint` internals are not fixed 21-word records when nested `BlackboardDouble` values carry dynamic keys or when the suffix ends before every metadata-listed Bezier field is serialized.
- The previous reader cut `bezierMidPoint1`/`bezierMidPoint2` at fixed 21-word boundaries. That split dynamic strings such as `EntityBB_BezierAngle`, `EntityBB_YZRadiusRange`, and `EntityBB_curve_rate` across midpoint boundaries.
- A few records serialize only a terminal prefix of the second midpoint, and one record ends with three zero padding words after a complete first midpoint.

Implementation:

- `ReadProjectileMoveModeDataSuffixDiagnostic` now attempts a metadata-order BezierPoint decode first, then a terminal-prefix BezierPoint decode.
- Complete BezierPoint records still use strict `usePresetPoint`, `presetPointKey`, `xRatioRange`, `yzAngleRange`, `yzRadiusRange`, and optional `scaledYzRadius` field order from IL2CPP metadata.
- Terminal-prefix records decode bounded `BlackboardDoubleRange` prefixes and mark partial terminal fields explicitly instead of emitting `decodeError` or raw midpoint records.
- All-zero terminal leftovers are classified as omitted second-midpoint padding and preserved as padding words.

Validation output:

```text
tmp\projectile_bezier_terminal_validation_after_20260630
```

Validation summary:

| Metric | Result |
| --- | ---: |
| Projectile template JSON files | 300 |
| `ProjectileComponentData` references | 300 |
| Decoded `ProjectileComponentData` layouts | 300 |
| Structured tails | 300 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |
| `BezierPoint` records | 571 |
| Decoded `BezierPoint` records | 571 |
| Full `BezierPoint` records | 524 |
| Terminal-prefix `BezierPoint` records | 46 |
| Terminal `BezierPoint` records with omitted `scaledYzRadius` | 1 |
| Raw/truncated midpoint statuses | 0 |
| Zero terminal padding cases | 1 |
| Nested terminal raw blackboard-key note | 1 |

Observed `BezierPoint.serializedWordCount` distribution:

| Words | Count |
| ---: | ---: |
| 7 | 23 |
| 11 | 1 |
| 12 | 1 |
| 14 | 16 |
| 17 | 3 |
| 19 | 1 |
| 21 | 519 |
| 23 | 2 |
| 24 | 1 |
| 31 | 3 |
| 42 | 1 |

Current projectile status:

- The focused 300-projectile slice has no tracked `$unparsed`, `$heuristic`, or `decodeError` markers and no raw/truncated Bezier midpoint statuses.
- `ProjectileComponentData` still remains parent `$partial` because inner `EffectActionCfg`, effect-list assignment, and some non-serialized `MoveModeData` speed-info metadata remain deliberately diagnostic.

## Projectile AlertEffect Prefix Recovery

This pass promotes the byte-proven projectile `alertEffect` prefix while preserving the still-unproven tail of `Beyond.Gameplay.EffectActionCfg`.

Root cause:

- Previous projectile `alertEffect` handling decoded only `fxType` and `effectName`, then preserved all remaining words raw.
- The 300-projectile focused slice consistently serializes a 24-word post-name prefix before the unknown `EffectActionCfg` tail.
- This projectile variant omits metadata field `useScaleBB`, then serializes `scale`, `scaleBB`, `useLengthBB`, `lengthBB`, `releaseByAction`, `ignoreOwnerTimeScale`, `interruptTime`, `terrainPrefab`, and empty `effectPosData`.

Implementation:

- `ReadProjectileAlertEffectActionCfgDiagnostic` now decodes the 24-word prefix only when the post-name payload has the observed 113-word shape and the prefix leaves exactly 89 words.
- The parser keeps `$partial` and preserves the remaining 89 words raw.
- If a future row does not match the proven shape, it falls back to the prior raw-preserving behavior instead of force-fitting fields.

Validation output:

```text
tmp\projectile_alert_prefix_validation_after_20260630
```

Validation summary:

| Metric | Result |
| --- | ---: |
| Projectile template JSON files | 300 |
| `ProjectileComponentData` references | 300 |
| Decoded `ProjectileComponentData` layouts | 300 |
| Structured tails | 300 |
| Data-level `$unparsed` records | 0 |
| Data-level `$heuristic` records | 0 |
| Data-level `decodeError` records | 0 |
| `alertEffect` records | 300 |
| `alertEffect` records with decoded 24-word prefix | 300 |
| `alertEffect.remainingRawWordCount = 89` | 300 |
| `alertEffect.effectName = ""` | 276 |
| `alertEffect.effectName = P_skillalert_circle_01` | 13 |
| `alertEffect.effectName = P_skillalert_circle_01_02` | 11 |
| `BezierPoint` records still decoded | 571 |
| Raw/truncated Bezier midpoint statuses | 0 |

Current projectile status:

- The focused 300-projectile slice still has no tracked `$unparsed`, `$heuristic`, or `decodeError` markers.
- Projectile `alertEffect` now exposes the proven prefix fields and keeps only the unproven 89-word tail raw.
- Remaining projectile semantic work is effect-list assignment and the later `EffectActionCfg` tail, not a whole-record decode failure.

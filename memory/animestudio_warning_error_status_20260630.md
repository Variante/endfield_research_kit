# AnimeStudio Warning/Error Status - 2026-06-30

## Current Focused Progress

- `ProjectileComponentData` focused slice: 300/300 records decode with structured tails and no tracked `$unparsed`, `$heuristic`, or `decodeError` markers after adaptive `BlackboardDouble`, guarded `mainEffectFinishType`, and terminal `BezierPoint` prefix recovery.
- Current focused validation output: `tmp\projectile_bezier_terminal_validation_after_20260630`.
- Remaining projectile work is not whole-record failure; it is semantic depth: inner `EffectActionCfg`, effect-list assignment, and some non-serialized `MoveModeData` metadata fields remain partial/diagnostic.

## Parallel Findings

EffectActionCfg bucket:

- 1,001 partial `Beyond.Gameplay.EffectActionCfg` records were observed in current validation roots.
- 701 are AbilitySystem-style fixed 107-word payloads; current reader consumes them but keeps them partial because wrapper internals and variants are not fully proven.
- 300 projectile `alertEffect` records have byte-proven `fxType`, `effectName`, and a safe 24-word post-name prefix. The remaining 89 words should stay raw for now.
- Smallest safe next promotion: guarded projectile-alert prefix parser only when `fxType == 1` and the post-name raw length is exactly 113 words.

ManagedReferencesRegistry bucket:

- Current decoded index scan: 1,064,294 MonoBehaviour JSON files, 3,644 incomplete/error-marked files.
- 1,937 `managedReferencesRegistryRecovery.status = heuristic` cases reconstruct consistent `version = 2` registries and matching reference counts; most are original TypeTree string-decode failures.
- 1,707 no-recovery partials stop at `references:ManagedReferencesRegistry`, but current artifacts do not record why recovery failed.
- Best next improvement is instrumentation: make `TryRecoverManagedReferences` return failure reason strings/enums and emit a `managedReferencesRegistryRecoveryAttempt` diagnostic when registry recovery fails.

## Next Targets

1. Add managed-reference recovery failure reasons before running another broad export, so the 1,707 no-recovery partials can be split into actionable buckets.
2. Continue projectile semantic recovery on effect-list assignment and the later 89-word `EffectActionCfg` tail.
3. Rebuild the decoded index after instrumentation to update the global incomplete/error-marked file report.

## 2026-06-30 AlertEffect Prefix Update

- Implemented guarded projectile `alertEffect` prefix decoding in AnimeStudio.
- Focused validation output: `tmp\projectile_alert_prefix_validation_after_20260630`.
- 300/300 focused projectile `alertEffect` records decoded the 24-word post-name prefix and preserved the remaining 89 raw words.
- The focused 300-projectile slice remains free of tracked `$unparsed`, `$heuristic`, and `decodeError` markers.

## ManagedReferencesRegistry Instrumentation Plan

The next best broad-data improvement is instrumentation, not another blind full export. The failed recovery branch should preserve current behavior and emit why `TryRecoverManagedReferences` returned false.

Recommended failure reason buckets:

- `rawDataMissing`
- `registryStartOffsetOutOfRange`
- `invalidRegistryVersion`
- `invalidRegistryCount`
- `registryCountLessThanExpectedRidCount`
- `firstHeaderInvalid`
- `duplicateHeaderRid`
- `nextHeaderNotFound`
- `remainingHeaderChainInvalid`
- `entryDataRangeInvalid`
- `duplicateRecoveredRid`
- `missingExpectedRid`

Implementation target:

- Change `TryRecoverManagedReferences` and `TryParseManagedReferenceHeaders` to return a diagnostic object on failure while leaving success output unchanged.
- In the partial TypeTree fallthrough, add `$animestudio.managedReferencesRegistryRecoveryAttempted = true` and `$animestudio.managedReferencesRegistryRecoveryFailure = {...}`.
- Do not change `BuildManagedReferenceData` payload decoding in this instrumentation pass.

## 2026-06-30 ManagedReferencesRegistry Diagnostic Update

Implemented failure diagnostics around `TryRecoverManagedReferences` without changing the recovered registry payload shape.

Build validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors after the instrumentation edit.
- `git -C tools\AnimeStudio diff --check` reports only Git's line-ending notice for `Exporter.cs`.

Runtime validation:

- Success probe: `tmp\managedrefs_failure_diag_probe_20260630` re-exported `CharacterDisplayConfig` and kept `managedReferencesRegistryRecovery.status = fullyDecoded` with 31/31 recovered references.
- UI partial probe: re-exporting `PathID 191669547493041408` from `activityv1d0d1checkinsignpopup.prefab` now recovers fully: `managedReferencesRegistryRecovered = true`, `managedReferencesRegistryFullyDecoded = true`, registry count 1/1.
- Candidate batch probe: `tmp\managedrefs_failure_batch_probe_20260630` re-exported 80 old no-recovery Persistent MonoBehaviours from `3267B09A76643181B4083C1E60B678D1.chk`; 80/80 now recover fully, 0 partial TypeTree outputs, 0 failure diagnostics.

Current interpretation:

- The instrumentation is compiled and success-path validated.
- I did not find a real current-data failure case in the sampled Persistent set; the stale no-recovery artifacts appear to be recoverable under the current exporter and recent parser fixes.
- The next broad export or decoded-index rebuild should bucket any remaining `references:ManagedReferencesRegistry` failures by `managedReferencesRegistryRecoveryFailure.reason` instead of leaving them as anonymous partial TypeTree stops.

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

1. Promote the safe projectile `alertEffect` 24-word prefix parser while preserving the remaining 89 raw words.
2. Add managed-reference recovery failure reasons before running another broad export, so the 1,707 no-recovery partials can be split into actionable buckets.
3. Rebuild the decoded index after instrumentation to update the global incomplete/error-marked file report.

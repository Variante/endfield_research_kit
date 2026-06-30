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

## 2026-06-30 Projectile AlertEffect Tail Update

Implemented the next projectile parser promotion after the alertEffect prefix recovery.

- Build validation: `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors after clearing one stale AnimeStudio.CLI probe process that was locking the output DLLs.
- Focused validation output: `tmp\projectile_alert_tail_validation_after_20260630`.
- 300/300 projectile `alertEffect` records now decode the 80-word post-prefix `EffectActionCfg` tail.
- 300/300 records decode the separate 9-word parent `postAlertEffectSoundTail`.
- `alertEffect.remainingRawWordCount` is now 0 for all 300 focused records.
- The focused slice still has 0 tracked `$unparsed`, `$heuristic`, or `decodeError` markers.

Broad inventory notes from this pass:

- A temp decoded MonoBehaviour index was rebuilt at `tmp\decoded_index_mono_20260630`: 1,064,294 files, 15,094 groups.
- Broad log review found the latest Texture2D asset run has 0 command failures, 0 warnings, 0 errors, 0 export errors, and 0 failed-to-decode entries.
- The largest remaining scary-looking asset markers are expected empty Animator/Texture2D marker outputs, not current parser failures.
- The old MonoBehaviour incomplete bucket is partly stale: multiple old no-recovery Persistent samples now recover fully when rerun with the current exporter.

## 2026-06-30 Audio Managed-Reference Payload Update

Implemented the next managed-reference recovery pass for `Beyond.Gameplay` audio/effect action payloads.

Root cause:

- The old export had two different failure shapes in this bucket:
  - heuristic recovered registries in `StreamingAssets\VFS\7064D8E2\FBAD673F662CF3EACDDB14A65999F7EF.chk` where raw payload bytes were present but the TypeTree string reader failed;
  - normal TypeTree-decoded registries where `references.RefIds[*].data` was `{}` even though raw MonoBehaviour bytes still contained the managed-reference payload.
- Subagent IL2CPP checks confirmed `PlaySingleSound`, `PlaySound`, and `PlaySoundByParticleCount` field order from `global-metadata.dat` / `Gameplay.Beyond.dll` metadata. This is schema recovery, not VFS loss or encryption.
- Wwise checks confirmed `PlaySound.soundName` and `PlaySoundByParticleCount.soundName` are valid event-name strings resolvable from banks. `PlaySingleSound.soundSpawn` / `soundFinish` are still game-side 32-bit hash/int fields, not directly proven Wwise event hashes in this pass.

Implementation:

- Added a raw-payload enrichment pass for TypeTree-decoded `references` registries that still have empty `data` for known audio managed-reference classes.
- The enrichment first validates a raw registry by RID and type before merging decoded data.
- Added a stricter per-header fallback for the null-sentinel edge case where a real `PlaySingleSound` entry has a zero-byte payload followed immediately by a negative blank sentinel entry.
- Added decoders for:
  - `Beyond.Gameplay.PlaySound`: aligned `soundName` plus `largeType` int32.
  - `Beyond.Gameplay.PlaySingleSound`: 28-byte sound/override payload plus an explicit zero-byte serialized variant.
  - `Beyond.Gameplay.PlaySoundByParticleCount`: aligned `soundName`, `particle` PPtr, `threshold` int32.

Validation output:

```text
tmp\audio_managed_ref_probe_after3_20260630\persistent
tmp\audio_managed_ref_probe_after3_20260630\streaming_fbad
tmp\audio_managed_ref_edge_after3_20260630\mono137074
```

Validation summary:

| Scope | Class | Refs | Decoded | Empty | `$unparsed`/`$heuristic`/`decodeError` |
| --- | --- | ---: | ---: | ---: | ---: |
| Persistent sample | `PlaySingleSound` | 59 | 59 | 0 | 0 |
| Persistent sample | `PlaySoundByParticleCount` | 12 | 12 | 0 | 0 |
| `FBAD...chk` sample | `PlaySingleSound` | 204 | 204 | 0 | 0 |
| `FBAD...chk` sample | `PlaySound` | 35 | 35 | 0 | 0 |
| `FBAD...chk` sample | `PlaySoundByParticleCount` | 185 | 185 | 0 | 0 |
| Combined focused probes | `PlaySingleSound` | 263 | 263 | 0 | 0 |
| Combined focused probes | `PlaySound` | 35 | 35 | 0 | 0 |
| Combined focused probes | `PlaySoundByParticleCount` | 197 | 197 | 0 | 0 |

Build validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors after the final exporter edit.

Follow-up:

- `build_audio.py` currently gathers wanted Wwise events from Story/cutscene/table inputs, not arbitrary managed-reference `soundName` fields. A later audio-index pass should optionally ingest decoded managed-reference sound names so entries like `au_sfx_ls_dung02_dg002_e9m2_zipline06`, `au_amb_emitter_lightning`, and `au_amb_emitter_damagefire_largelorlong_01` can be linked into the decoded audio catalog.

## 2026-06-30 Guide Managed-Reference Revalidation

Rechecked the largest stale MonoBehaviour warning bucket from `tmp\decoded_index_mono_20260630` against the current AnimeStudio exporter, then added one narrow raw-payload merge improvement for guide refs that TypeTree leaves as empty `{}` data.

Old-index bucket:

- `MonoBehaviour\StreamingAssets\guide_group`: 911 entries, 624 previously marked unparsed/heuristic.
- `MonoBehaviour\StreamingAssets\guide_blackbox`: 355 entries, 315 previously marked unparsed/heuristic.
- Dominant old classes included `CheckMissionState`, `CombineCondition`, `InMainHud`, `OnUIPanelOpen`, `CheckGuideGroupComplete`, `BlendOutFromCamera`, and `BlendToCameraTransformWithoutBack`.

Subagent evidence:

- Exported payloads are schema/string/RID recovery cases, not encrypted blobs.
- IL2CPP `global-metadata.dat` field order confirms the common guide layouts: string/id fields, bool flags, float fields, Vector3-like fields, enum-like fields, and RID-linked subconditions.
- Existing guide decoder coverage already handles the high-volume classes. The remaining implementation gap was the enrichment path for TypeTree-successful managed refs whose `data` remains `{}`; that path only admitted audio classes before this pass.

Implementation:

- Extended `IsKnownRawPayloadMergeCandidate` so empty managed-reference payloads in `Gameplay.Beyond` guide namespaces can be rechecked against the existing raw header-scan decoder.
- Preserved guide-specific decode failures with `BuildKnownManagedReferenceDecodeFailureData` instead of silently falling back to generic heuristic output when a focused guide layout rejects a payload.
- Unsupported guide classes are still left untouched unless the existing decoder returns fully decoded data.

Current focused validation outputs after rebuild:

```text
tmp\guide_managed_ref_probe_after_merge_20260630\validate_68b3
tmp\guide_managed_ref_probe_after_merge_20260630\validate_71fc
tmp\guide_managed_ref_probe_after_merge_20260630\validate_fbad
```

Validation summary:

| Scope | Files | Registry status | Managed-reference refs | Unresolved refs |
| --- | ---: | --- | ---: | ---: |
| Combined guide revalidation | 939 | 939 decoded | 8,857 decoded | 0 |

Notes:

- The focused guide revalidation did not contain current empty guide refs that exercised the new raw-payload merge branch; `rawPayloadDecoded` stayed absent in this sample.
- The old guide bucket is stale under the current exporter. A full decoded-index rebuild should replace those old guide warnings before ranking the next unresolved bucket.

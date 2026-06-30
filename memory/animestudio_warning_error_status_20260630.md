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

## 2026-06-30 Persistent Enemy AbilitySystemData Update

Rechecked the next largest current MonoBehaviour bucket with the current AnimeStudio exporter instead of trusting the stale decoded index.

Focused source:

```text
D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk
```

Focused filter:

```text
tmp\data_eny_probe_20260630\names_persistent_3267.txt
```

Current pre-patch validation:

```text
tmp\data_eny_probe_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_parts_adaptive_20260630\current_persistent_3267
```

Root cause:

- The old `Persistent/data_eny` bucket is a real current parser gap, not only stale index noise.
- `AbilitySystemData` was already decoding mode config, skill bundle, UI, buffs, and post-buff fields, then leaving a large raw tail of model/battle-shape bone paths and numeric point records.
- IL2CPP `global-metadata.dat` confirms the missing fields after `entityBlackboard`:
  - `bakedMeshPoints`: `SerializeFieldDictionary<string, AbilitySystemData.BakedMeshPointList>`
  - `bakedMeshPointBonePathList`: string list
  - `extraShapesData`: dictionary, empty in the focused samples
- `AbilitySystemData.BakedMeshPoint` field order is `Vector3 battleShapePointOffset`, `int bonePathIndex`, `Vector3 meshPointOffset`.
- `EnemyPartsRootComponentData` has two observed inherited-prefix variants. The previous decoder handled the 8-word prefix; this pass adds an adaptive 10-word prefix fallback without dropping the old variant.

Implementation:

- Added metadata-backed decoding for non-empty `AbilitySystemData.bakedMeshPoints` dictionaries.
- Added decoding for `AbilitySystemData.bakedMeshPointBonePathList` string lists.
- Added an adaptive `EnemyPartsRootComponentData` reader that tries both `prefixWords8` and `prefixWords10` layouts.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,478 | 1,554 |
| Managed refs partial | 87 | 16 |
| Managed refs unparsed | 23 | 18 |
| `AbilitySystemData` partial/unparsed refs | 78 | 6 |
| `EnemyPartsRootComponentData` decoded refs | 8 | 12 |
| Baked mesh dictionaries decoded | 0 | 73 |
| Baked mesh dictionary keys | 0 | 137 |
| Baked mesh point lists | 0 | 137 |
| Baked mesh points | 0 | 6,775 |

Build validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors after the final adaptive exporter edit.

Remaining current focused gaps in this bucket:

- `EnemyPartsRootComponentData`: 15 refs still heuristic/unparsed, likely additional prefix or tag-list variants.
- `AbilitySystemForEnemyPartData`: 11 refs still partial because the scalar tail constraints do not match the current focused decoder.
- `AbilitySystemData`: 5 refs still partial and 1 ref still heuristic/unparsed, mainly larger skill/mode variants such as `data_eny_0077_agshield` and `data_eny_0081_ruanyi`.
- `FootRippleComponentData`: 2 refs still heuristic/unparsed; metadata says the payload contains `entries`, `footWeightThreshold`, and `speedToRippleIntervalCurve`.

## 2026-06-30 Non-Mono Unresolved Format Ranking

A read-only audit found wrapper-level unresolved files are currently empty:

```text
export_full\unresolved\failed_to_decode.txt: 0 entries
export_full\unresolved\manifest_reference_missing.txt: 0 entries
```

The remaining non-Mono work is therefore mostly opaque-but-preserved data, not current AnimeStudio crashes.

Ranked non-Mono buckets:

1. MemoryPack-style binary `.json` gameplay configs: schema gaps, not encryption. Highest-value roots are `SkillData`, `BuffData`, `Interactive/InteractiveData`, and `LevelScriptData`.
2. World streaming `.bytes`: FlatBuffer-like schema gap. Samples validate as structured FlatBuffer-style roots rather than encrypted blobs.
3. `IrradianceVolume` `.bytes`: custom lighting binary format; index files expose readable labels while volume blobs look like dense numeric grids.
4. `ExtendData` `.bin`: binary index/table gap. `StringPathHash.bin` and `CompressData.bin` should be cross-checked against VFS and bundle paths.
5. Raw encoded `.ab` bundles and `manifest.hgmmap`: expected package/container layer. Compare raw structured bytes against bytes loaded through AnimeStudio before treating these as decode failures.
6. Wwise `.pck`: known encoded AKPK/Wwise container. Existing audio tooling normalizes and decodes CN audio; remaining work is coverage accounting, not basic decryption.
7. `IFixPatchOut` patch bytes: small compression/encryption-looking payloads outside normal WebUI consumption. Needs loader-code search and compression/decrypt probes.
8. Shader bytecode internals: container mostly understood; remaining gaps are downstream decompiler/SMOL-V variants.

## 2026-06-30 Enemy FootRippleComponentData Update

Continued the current `Persistent/data_eny` focused bucket after the baked mesh point recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_parts_adaptive_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_footripple_20260630\current_persistent_3267
```

Root cause:

- The remaining `Beyond.Gameplay.View.FootRippleComponentData` payloads were normal schema data, not encryption.
- IL2CPP metadata field order is:
  - `entries`: `List<FootRippleEntry>`
  - `footWeightThreshold`: float
  - `speedToRippleIntervalCurve`: Unity `AnimationCurve<float>`
- `FootRippleEntry` metadata field order is `mountPoint`, `footWeightCurveHash`, `rippleSize`.
- The two focused payloads are fixed 128-byte records: 4 entries, one float threshold, and a 2-keyframe Unity animation curve.

Implementation:

- Added `FootRippleComponentData` managed-reference decoding.
- Added guarded `ReadFootRippleEntryList` using the existing payload `AnimationCurve<float>` reader for `speedToRippleIntervalCurve`.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,554 | 1,556 |
| Managed refs partial | 16 | 16 |
| Managed refs unparsed | 18 | 16 |
| `FootRippleComponentData` decoded refs | 0 | 2 |
| Foot ripple entries decoded | 0 | 8 |
| Foot ripple curve keyframes decoded | 0 | 4 |

Build validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 errors after the exporter edit.
- The build emitted 14 pre-existing warnings from other AnimeStudio projects; no new compiler errors were introduced.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `EnemyPartsRootComponentData`: 15 refs still heuristic/unparsed.
- `AbilitySystemForEnemyPartData`: 11 refs still partial.
- `AbilitySystemData`: 5 refs still partial and 1 ref still heuristic/unparsed.

## 2026-06-30 EnemyPartsRootComponentData Part-ID List Update

Continued the current `Persistent/data_eny` focused bucket after FootRipple recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_footripple_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_partids_20260630\current_persistent_3267
```

Root cause:

- The remaining `Beyond.Gameplay.Core.EnemyPartsRootComponentData` misses were normal serialized schema variants, not encrypted payloads.
- Existing decoded variants used fixed 8-word and 10-word inherited prefixes before `partName` and `partTags`.
- The 15 missed refs share a count-driven middle section: six prefix words, a bool32/enabled word, an int32 count, then a compact list of part id/hash words before the aligned `partName` and normal `partTags` list.
- Observed equivalent opaque prefix sizes were 14, 16, and 17 words; naming the count-driven section preserves more structure than adding only larger raw prefixes.

Implementation:

- Added an adaptive `EnemyPartsRootComponentData` fallback for the `prefixWords6PartIdList` layout.
- Added guarded `ReadEnemyPartIdList` with count bounds and complete-consumption validation.
- Left the existing 8-word and 10-word variants unchanged.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,556 | 1,571 |
| Managed refs partial | 16 | 16 |
| Managed refs unparsed | 16 | 1 |
| `EnemyPartsRootComponentData` decoded refs | 12 | 27 |
| `EnemyPartsRootComponentData` unparsed refs | 15 | 0 |
| New `prefixWords6PartIdList` refs | 0 | 15 |
| Part-id words decoded in new variant | 0 | 122 |
| Part tags decoded across enemy parts | 15 | 26 |

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 errors and 14 pre-existing warnings.
- Focused AnimeStudio export of `D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk` with the 78-name `data_eny` filter succeeded with return code 0.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `AbilitySystemForEnemyPartData`: 11 refs still decoded+partial.
- `AbilitySystemData`: 5 refs still decoded+partial and 1 ref still unparsed+heuristic (`data_eny_0081_ruanyi`).
- Subagent review found no strong nested/multiple encryption signal in these remaining parent failures; observed bytes are aligned strings, sane counts/floats, and recognizable schema sections.

## 2026-06-30 AbilitySystemData Mount-Point Enum Update

Continued the same `Persistent/data_eny` focused bucket after the enemy part-id list recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_partids_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_mountpoint_20260630\current_persistent_3267
```

Root cause:

- `AbilitySystemData.BattleRootData.rootMountPoint` was decoded as a closed six-value enum.
- Focused samples contain additional small int/hash values in the same field (`151`, `155`, and `52`), and later bytes remain normal aligned schema data.
- Other AbilitySystem mount-point readers already preserve unknown values as hash/int objects, so this was a schema coverage gap rather than encryption.

Implementation:

- Changed `ReadAbilitySystemMountPoint` to preserve known values `0..5` by name and retain unknown values through the existing hash/int representation.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,571 | 1,573 |
| Managed refs partial | 16 | 15 |
| Managed refs unparsed | 1 | 0 |
| `AbilitySystemData` decoded refs | 72 | 74 |
| `AbilitySystemData` decoded+partial refs | 5 | 4 |
| `AbilitySystemData` unparsed refs | 1 | 0 |

Notable records:

- `data_eny_0061_palecore` now fully consumes `AbilitySystemData` with `rootMountPoint = 151`.
- `data_eny_0081_ruanyi` now fully consumes `AbilitySystemData` with `rootMountPoint = 52`; this removes the last unparsed/heuristic ref in the focused enemy bucket.
- `data_eny_0080_reaper` advances past `rootMountPoint = 155` but remains decoded+partial because a later tail still contains readable strings and raw words.

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 errors and the same 14 pre-existing warnings.
- The focused 78-name AnimeStudio export succeeded with return code 0.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `AbilitySystemForEnemyPartData`: 11 refs still decoded+partial.
- `AbilitySystemData`: 4 refs still decoded+partial (`data_eny_0077_agshield`, `data_eny_0080_reaper`, `data_eny_0090_wgabyss`, `data_eny_0092_slbomb`).
- No refs in this focused bucket remain unparsed/heuristic.
## 2026-06-30 AbilitySystemForEnemyPartData Tail Structuring

Continued the same `Persistent/data_eny` focused bucket after the AbilitySystemData mount-point recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_mountpoint_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_partability_tail_20260630\current_persistent_3267
```

Root cause:

- The remaining `AbilitySystemForEnemyPartData` partial refs are word-aligned numeric payloads, not encrypted blobs.
- Existing decoded records are 828 bytes and validate a full 20-word scalar tail after `partAttributesRawWords`.
- The 11 longer variants are 840 or 852 bytes. Treating their final 20 words as the full scalar tail overlaps unresolved `partAttributes`/front-scalar data, so the old bool checks rejected values like `0.1`, `0.45`, `50`, or `999`.
- The final 18 words, from `useMainBodyHp` through `damageTransferType`, validate contiguously across all 11 longer variants.

Implementation:

- Kept the existing full 20-word scalar-tail path first for already understood records.
- Added a `postAttributeScalarTail18` fallback that decodes only the proven final 18 scalar fields.
- Preserved the ambiguous front bytes as `partAttributesAndScalarPrologRawWords` and kept `$partial` with explicit reasons instead of pretending the `defaultEnabled` / `asIndividualInExcludeTargetProcessor` / `partAttributes` boundary is solved.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,573 | 1,573 |
| Managed refs decoded+partial | 15 | 15 |
| Managed refs unparsed | 0 | 0 |
| `AbilitySystemForEnemyPartData` decoded refs | 16 | 16 |
| `AbilitySystemForEnemyPartData` decoded+partial refs | 11 | 11 |
| Opaque `AbilitySystemForEnemyPartData.rawWords` partials | 11 | 0 |
| `postAttributeScalarTail18` structured partials | 0 | 11 |

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors.
- The focused 78-name AnimeStudio export succeeded with return code 0.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `AbilitySystemForEnemyPartData`: 11 refs still decoded+partial because the front prolog/`partAttributes` boundary is not fully decoded yet, but their final scalar suffix is now structured.
- `AbilitySystemData`: 4 refs still decoded+partial (`data_eny_0077_agshield`, `data_eny_0080_reaper`, `data_eny_0090_wgabyss`, `data_eny_0092_slbomb`).
- No refs in this focused bucket remain unparsed/heuristic.
## 2026-06-30 AbilitySystemData Reaper Extra Shape Recovery

Continued the same `Persistent/data_eny` focused bucket after the enemy-part ability tail structuring.

Focused validation baseline:

```text
tmp\data_eny_probe_after_partability_tail_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_reaper_extrashapes_20260630\current_persistent_3267
```

Root cause:

- `data_eny_0080_reaper` was not encrypted; the remaining tail was normal schema data after `defaultHitEffect`.
- The entity-blackboard stage rolled back because `bakedMeshPoints` contains two explicit `0x7fc00000` NaN sentinel vectors, and the generic float reader rejects non-finite values.
- The same tail also has a non-empty `extraShapesData` dictionary with two shape mount-point keys (`158`, `166`) and two `BasicShapeData` values `(4.0, 8.1)`, while the old reader only accepted empty dictionaries.

Implementation:

- Added a baked-mesh-point vector reader that preserves non-finite float32 values as raw `{ "$nonFinite", rawInt32, rawHex }` markers instead of rejecting the whole object.
- Replaced the empty-only `extraShapesData` reader with a bounded `SerializeFieldDictionary<MountPoint, BasicShapeData>` parser.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,573 | 1,574 |
| Managed refs decoded+partial | 15 | 14 |
| `AbilitySystemData` decoded refs | 74 | 75 |
| `AbilitySystemData` decoded+partial refs | 4 | 3 |

Notable record:

- `data_eny_0080_reaper` now fully consumes `AbilitySystemData`, including `entityBlackboard`, `bakedMeshPoints`, `bakedMeshPointBonePathList`, `extraShapesData`, `skillCameraConfig`, and post-camera fields.

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors.
- The focused 78-name AnimeStudio export succeeded with return code 0.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `AbilitySystemForEnemyPartData`: 11 refs still decoded+partial because the front prolog/`partAttributes` boundary is not fully decoded yet.
- `AbilitySystemData`: 3 refs still decoded+partial (`data_eny_0077_agshield`, `data_eny_0090_wgabyss`, `data_eny_0092_slbomb`).
- No refs in this focused bucket remain unparsed/heuristic.

## 2026-06-30 AbilitySystemData Mode Clip Mapping Recovery

Continued the same `Persistent/data_eny` focused bucket after the `data_eny_0080_reaper` recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_reaper_extrashapes_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_agshield_modeclip_20260630\current_persistent_3267
```

Root cause:

- `data_eny_0077_agshield` and `data_eny_0090_wgabyss` were not encrypted; both had real `modeConfig.modes` tail variants.
- `modeConfig.modes.overrideClipMapping` was treated as empty-only. In these rows it is a non-empty `SerializeFieldDictionary<int, string>` that maps a state-clip hash to `Skill01Loop`.
- Because the clip mapping was not consumed, `Skill01Loop` looked like a false next section/mode boundary. That left `agshield` at the start of `SkillDataBundle` and made `wgabyss` later parse `Settlement` bytes as a bool.
- In the same override-state-clip variant, an empty `cmdMapping` serializes as two count words (`0, 0`) rather than the older four-word empty header used by already-decoded modes.

Implementation:

- Replaced the empty-only override-clip reader with a bounded `SerializeFieldDictionary<int, string>` parser.
- Kept the legacy four-word `cmdMapping` path for existing modes, but added a scoped two-count empty dictionary path when the mode uses override-state-clip data.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,574 | 1,576 |
| Managed refs decoded+partial | 14 | 12 |
| `AbilitySystemData` decoded refs | 75 | 77 |
| `AbilitySystemData` decoded+partial refs | 3 | 1 |

Notable records:

- `data_eny_0077_agshield` now fully consumes `AbilitySystemData`, including `SkillDataBundle`, `uiData`, and later ability sections.
- `data_eny_0090_wgabyss` now fully consumes `AbilitySystemData`; the previous diagnostic `invalid bool32 1953785171 in modeConfig.modes.isStrafing` was a false boundary caused by not decoding `overrideClipMapping`.
- Per-reference status diff showed only these two `AbilitySystemData` refs changed from `$decoded+$partial` to `$decoded`.

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 14 pre-existing warnings and 0 errors.
- The focused 78-name AnimeStudio export succeeded with return code 0.

Remaining current focused gaps in `Persistent/data_eny` after this pass:

- `AbilitySystemForEnemyPartData`: 11 refs still decoded+partial because the front prolog/`partAttributes` boundary is not fully decoded yet.
- `AbilitySystemData`: 1 ref still decoded+partial (`data_eny_0092_slbomb`).
- No refs in this focused bucket remain unparsed/heuristic.
## 2026-06-30 AbilitySystemForEnemyPartData Dynamic Rule Update

Continued the same `Persistent/data_eny` focused bucket after the AbilitySystemData mode clip mapping recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_agshield_modeclip_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_partability_dynamicrules_20260630\current_persistent_3267
```

Root cause:

- The 11 remaining `AbilitySystemForEnemyPartData` partial refs were not encrypted and were not malformed tails.
- Word 188 is a small count, not `asIndividualInExcludeTargetProcessor`.
- The current focused layout is a 187-word raw `partAttributes` prefix, `defaultEnabled`, a counted post-default record list, then the existing 18 scalar fields from `useMainBodyHp` through `damageTransferType`.
- Observed counted records are 3-word triples: `kind:int32`, `flag:bool32`, `value:float32`.

Implementation:

- Added a guarded `partAttributesPostDefaultRules` parser that validates the count against payload length and decodes the 3-word records before reusing the existing 18-field scalar suffix reader.
- Kept the previous 20-word scalar and 18-word partial fallback paths for future variants that do not match this layout.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,576 | 1,587 |
| Managed refs decoded+partial | 12 | 1 |
| `AbilitySystemForEnemyPartData` decoded refs | 16 | 27 |
| `AbilitySystemForEnemyPartData` decoded+partial refs | 11 | 0 |
| `partAttributesPostDefaultRules` refs | 0 | 27 |

Observed non-empty post-default records:

- `data_eny_0077_agshield`: `(1, false, 0.1)`.
- `data_eny_0080_reaper`: `(20, true, 0.0)`, `(1, false, 0.45)`.
- `data_eny_0081_ruanyi`: `(1, false, 999.0)`, `(20, false, 999.0)` across seven parts.
- `data_eny_0113_jzogre`: `(1, true, 50.0)`.

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 warnings and 0 errors.
- The focused 78-name AnimeStudio export succeeded with return code 0.

Remaining current focused gap in `Persistent/data_eny` after this pass:

- `AbilitySystemData`: 1 ref still decoded+partial (`data_eny_0092_slbomb`).
- No `AbilitySystemForEnemyPartData`, `EnemyPartsRootComponentData`, or `FootRippleComponentData` refs in this focused bucket remain partial/unparsed/heuristic.

## 2026-06-30 AbilitySystemData Slbomb DeadEffect Update

Closed the last top-level partial in the focused `Persistent/data_eny` bucket after the enemy-part dynamic rule recovery.

Focused validation baseline:

```text
tmp\data_eny_probe_after_partability_dynamicrules_20260630\current_persistent_3267
```

Post-patch validation:

```text
tmp\data_eny_probe_after_slbomb_20260630\current_persistent_3267
```

Root cause:

- `data_eny_0092_slbomb` was not encrypted; the remaining 122 words after `skillCameraConfig` were normal post-camera `AbilitySystemData` fields.
- The payload serializes `overrideDeadEffect` before `deadEffect`, unlike most focused rows that start directly with `deadEffect`.
- The nested `deadEffect` payload uses the proven 104-word post-name `EffectActionCfg` body shape that omits `useScaleBB` and `centerOffset`.
- The byte split is:
  - word 0: `overrideDeadEffect`.
  - words 1..114: `deadEffect`, including a 24-word no-`useScaleBB` prefix and the existing 80-word `EffectActionCfg` tail reader.
  - words 115..121: parent suffix `effectScale`, hit-flash fields, `healthType`, empty `preloadAbilityEntities`, and empty `maxPotentialEffectBuffId`.

Implementation:

- Kept the existing no-`overrideDeadEffect` post-camera path unchanged for the majority layout.
- Added a guarded `overrideDeadEffect` post-camera variant that requires complete consumption.
- Reused the existing no-`useScaleBB` prefix and 80-word tail helpers rather than changing the global `EffectActionCfg` reader.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| Files re-exported | 78 | 78 |
| Managed refs decoded | 1,587 | 1,588 |
| Managed refs decoded+partial | 1 | 0 |
| `AbilitySystemData` decoded refs | 77 | 78 |
| `AbilitySystemData` decoded+partial refs | 1 | 0 |
| Focused top-level partial/unparsed/heuristic refs | 1 | 0 |

Notable record:

- `data_eny_0092_slbomb` now fully consumes `AbilitySystemData`: `overrideDeadEffect = false`, `deadEffect.effectName = P_fxbat_slbomb_dead_disappear`, `deadEffect.layoutVariant = omitUseScaleBBPostName104`, `effectScale = 1.0`, and `healthType = Normal`.

Build and validation:

- `scripts\animestudio\rebuild.bat -Target CLI -NoRestore` succeeded with 0 errors and 14 pre-existing warnings.
- The focused 78-name AnimeStudio export succeeded with return code 0.
- Focused status after this pass is `1588/1588` top-level managed references decoded, with no top-level `$partial`, `$unparsed`, or `$heuristic` refs in `Persistent/data_eny`.

Remaining caveat:

- The nested `deadEffect` object still uses the existing diagnostic `EffectActionCfg` tail readers, so inner `BlackboardDouble` wrapper semantics remain partially inferred. This is semantic depth, not unread parent bytes or an export warning in the focused enemy bucket.

## 2026-06-30 BB_eny Managed-Reference Revalidation

Re-ranked the next current-looking MonoBehaviour bucket after closing the focused `Persistent/data_eny` top-level partials.

Temporary broad index:

```text
tmp\decoded_index_mono_after_slbomb_baseline_20260630
```

The temporary index scans the existing `export_full/recovered/AnimeStudio-cli` outputs, so it still contains stale artifacts from before recent managed-reference recovery improvements. It ranked `BB_eny` as a coherent named bucket with stale partial TypeTree stops at final `references:ManagedReferencesRegistry`.

Focused current revalidation:

```text
tmp\bb_eny_probe_current_all_20260630\persistent
tmp\bb_eny_probe_current_all_20260630\streaming
```

Root cause:

- The old `export_full` `BB_eny` partials are stale. Their top-level fields already decoded, then old TypeTree output stopped at the final `references` registry after reading graph RID links.
- Current AnimeStudio managed-reference recovery can now recover these registries fully.
- This is a registry recovery/update freshness issue, not encryption and not a current BB_eny parser gap.

Focused validation summary:

| Scope | Files | Top-level decoded | Top-level partial/unparsed/heuristic | Fully recovered registries |
| --- | ---: | ---: | ---: | ---: |
| Persistent `BB_eny*` | 231 | 231 | 0 | 154 |
| StreamingAssets `BB_eny*` | 231 | 231 | 0 | 154 |

Recovered managed-reference class coverage includes:

- `EnemyBattleGraph/EnemyBattleGraphData`: 164 refs per source.
- `EnemyAttackBuildingGraph/EnemyAttackBuildingGraphDatta`: 104 refs per source.
- `EnemySettlementBattleBehavior/EnemySettlementBattleBehaviorData`: 52 refs per source.
- `EnemyBattleEventStimulus/EnemyBattleEventStimulusData`: 27 refs per source.
- `EnemySettlementBattleGraph/EnemySettlementBattleGraphData`: 24 refs per source.
- `EnemyCastSkillResponse/EnemyCastSkillResponseData`: 23 refs per source.

Follow-up:

- Do not spend implementation time on `BB_eny` until a current full export proves a fresh failure.
- The existing `export_full` decoded index should be refreshed before using it as an authoritative warning ranking.
- If we need an immediate non-Mono target while Mono warnings are stale, `Json/SkillData` `toggleBuffs` remains the strongest next schema bucket.

## 2026-06-30 SkillData ToggleBuffs Tail Recovery

Closed the non-empty `SkillData.toggleBuffs` post-switch tail gap in the Data index decoder.

Root cause:

- The affected files were not encrypted and did not need VFS-level changes.
- `SkillData` rows with non-empty `toggleBuffs` use regular MemoryPack list bodies after `switchToCenterBeforeCast` and `tagDuringAttach`.
- IL2CPP MemoryPack formatter metadata shows `ToggleBuffData` serializes in formatter setter order `buffs`, then `conditions`, even though the runtime field token order lists `conditions`, then `buffs`.
- Each observed `buffs` entry is a `BuffInput` with formatter order `assignBlackboard`, `assignItems`, `buffId`.
- Each observed `assignItems` entry is `Beyond.Blackboard.AssignPair` in formatter order `directValueType`, `inputValueKey`, `numericValue`, `stringValue`, `targetKey`, `useDirectValue`.
- Each observed `conditions` entry uses a compact compare/value shape: kind `1`, member count `2`, `compare`, then a `BlackboardDouble`-style key/use/value payload.

Evidence and temporary probes:

```text
tmp\skilldata_togglebuff_metadata_20260630.json
tmp\game_data_index_skill_toggle_validate_20260630
```

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| `SkillData` files scanned | 2,083 | 2,083 |
| `postIdTailPrefix=parsed-through-smartTargetTagQuery` | 2,025 | 2,025 |
| Post-switch exact tails | 1,948 | 2,024 |
| Post-switch `parsed-through-toggleBuffsCount` stops | 76 | 0 |
| Non-empty `toggleBuffs` files parsed exactly | 0 | 76 |
| Remaining post-switch parse errors | 1 | 1 |

Observed non-empty toggle coverage:

- 75 files have `toggleBuffsCount = 1`.
- 1 file has `toggleBuffsCount = 2` (`chr_0009_azrila_talent_0`).
- 77 total `ToggleBuffData` items were parsed.
- Every observed item has one `BuffInput` entry.
- Conditions are optional: 53 items have no conditions and 24 have one compact compare/value condition.
- Observed condition compare raw values are `0`, `1`, `2`, `3`, and `4`; observed blackboard keys include empty direct values, `hp_ratio`, and `hp_ratio_c`.

Integration validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_skill_toggle_validate_20260630` completed and indexed 81,735 Json files: 78,710 MemoryPack Json records and 3,025 text Json records.

Remaining SkillData gap:

- `chr_0026_lastrite_normal_skill.json` still fails after the default `SwitchToBuffConfig` byte boundary with `switchToCenterBeforeCast:byte=95`.
- This is a different switch-body layout: its `switchToBuffConfig.buffsCount = 1` and the current fixed 148-byte default boundary is too short for the non-empty switch body. Treat it as the next SkillData target, not as encryption.

## 2026-06-30 SkillData Non-Empty SwitchToBuffConfig Update

Closed the remaining post-switch `SkillData` parse error caused by a non-empty `SwitchToBuffConfig.buffs` list.

Root cause:

- The affected file is not encrypted and does not need another VFS decode pass.
- `chr_0026_lastrite_normal_skill.json` uses the same top-level `SkillData` tail schema, but its `SwitchToBuffConfig` body is larger than the 148-byte empty/default body used by the rest of the observed files.
- The fixed 148-byte boundary landed inside the switch buff body, specifically inside the string payload around `atk_up`, so the old parser misread `0x5f` as `switchToCenterBeforeCast`.
- The switch buff itself is a normal `BuffInput`: `assignBlackboard`, seven `AssignPair` values, and `buff_chr_0026_lastrite_normal_skill_inattack`.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| `SkillData` files scanned | 2,083 | 2,083 |
| Post-switch exact tails | 2,024 | 2,025 |
| Remaining post-switch parse errors | 1 | 0 |
| Default fixed switch boundaries | 2,024 | 2,024 |
| Dynamically validated switch boundaries | 0 | 1 |
| Files with non-empty `SwitchToBuffConfig.buffs` | 0 parsed | 1 parsed |

Observed `chr_0026_lastrite_normal_skill` switch body:

- `switchToBuffConfig.buffsCount = 1`.
- Dynamic switch body length is 624 bytes.
- The parsed `BuffInput` starts at `0x337c`, has member count `3`, and has seven assign items: `atk_scale`, `duration`, `atb`, `atk_up`, `poise`, `potential_1`, and `usp`.
- The post-switch tail starts at `0x35e6` and parses exactly through `toggleBuffsCount = 0` and `uiRangeHintsCount = 1`.

Implementation note:

- The parser now reads `SwitchToBuffConfig.buffs` and validates the switch-body boundary by requiring the following `switchToCenterBeforeCast`, `tagDuringAttach`, `toggleBuffs`, and `uiRangeHints` tail to reach exact EOF.
- The remaining `SwitchToBuffConfig` suffix fields after `buffs` are still recorded as raw diagnostic bytes/string hits under the expected field names `buffSource`, `condition`, and `targets`. Their exact nested semantics are the next deeper target if we choose to decode TargetSettings/SequenceActionData internals.

Integration validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_skill_switch_validate_20260630` completed and indexed 81,735 Json files, including all 2,083 `Json/SkillData` records.
## 2026-06-30 SkillData Ambiguous SkillId Anchor Recovery

Resolved most `SkillData` rows where the exact length-prefixed file stem appeared more than once in the raw MemoryPack payload.

Root cause:

- The extra id markers are real exact string references, not encryption and not duplicate top-level `SkillData.skillId` fields.
- They occur inside earlier nested action/config payloads before the top-level `skillId` field.
- Some embedded markers can superficially parse because the surrounding payload is zero/default-heavy, so choosing the first or last marker is not a sound rule.
- The reliable top-level anchor is the candidate marker whose following post-id prefix reaches a valid `SwitchToBuffConfig` marker and whose post-switch tail reaches exact EOF.

Implementation:

- `decode_skill_post_id_tail_prefix` now probes every recorded exact id marker for `SkillData`.
- It accepts exactly one candidate only when the post-id prefix parses, `skillTags.count == 1`, `SwitchToBuffConfig` is found, and the validated post-switch tail reaches exact EOF.
- Candidate summaries are retained on unresolved ambiguous rows so the remaining schema gaps are visible instead of hidden.
- `SkillData` marker collection now keeps up to 64 offsets so high-repeat rows such as `chr_0017_yvonne_ult_attack3_2` include the true final top-level anchor.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| `SkillData` files scanned | 2,083 | 2,083 |
| Parsed through post-id prefix and exact switch tail | 2,025 | 2,075 |
| Ambiguous id-marker rows | 53 | 3 |
| Ambiguous rows structurally selected | 0 | 50 |
| Single-marker smart-target parse errors | 5 | 5 |

Resolved examples:

- `chr_0002_endminm_normal_skill.json`: embedded markers at `0x4791` and `0x47e3`; top-level marker selected at `0x4d6a`.
- `chr_0017_yvonne_ult_attack3_2.json`: nine exact id-string markers; top-level marker selected only after collecting all offsets.
- Weapon/skill rows such as `sk_wpn_claym_0011.json`, `sk_wpn_funnel_0017.json`, and `sk_wpn_sword_0015.json` now resolve by the same structural rule.

Remaining ambiguous rows:

- `chr_0006_wolfgd_normal_skill.json`
- `chr_0017_yvonne_normal_skill.json`
- `chr_0028_wulfa_combo_2_skill.json`

These three have a likely top-level marker followed by non-empty smart-target/tag-query payloads. The current simple smart-target parser does not yet decode those nested branches, so they remain visible as schema work rather than being auto-selected from a weaker anchor.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- Direct raw-byte sweep over `export_full/structured/StreamingAssets/Data/Json/SkillData/*.json` produced `2,075` parsed, `3` ambiguous, and `5` parse-error rows.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_skill_anchor_validate_20260630` completed and indexed 81,735 Json files, including all 2,083 `Json/SkillData` records.
## 2026-06-30 SkillData Smart-Target Payload Recovery

Closed the remaining `SkillData` post-id warning buckets by validating and exposing the non-simple smart-target/tag-query payloads before `SwitchToBuffConfig`.

Root cause:

- The remaining rows are not encrypted and do not need another VFS pass.
- The old parser handled only the common simple path: `skillTags`, `smartTargetBuffFindSettings`, a simple string list for `smartTargetBuffIds`, `smartTargetSelectStrategy`, then one byte for `smartTargetTagQuery`.
- The unresolved rows contain additional smart-target/tag-query bytes before `SwitchToBuffConfig`. Some include buff-id strings, and some include GameplayTag-like records using `memberCount + tagId + length-prefixed tag path`.
- Local IL2CPP/formatter metadata confirms the relevant field names and order, while AnimeStudio's C# diagnostics already use related helpers for `BuffFindSettings` and `GameplayTagQuery` payloads.

Implementation:

- `decode_skill_switch_tail_probe` now scans farther for a validated `SwitchToBuffConfig` marker, but still accepts only candidates whose post-switch tail reaches exact EOF.
- The pre-switch payload is preserved with prefix bytes, length-prefixed string hits, and GameplayTag-like record hits.
- If simple smart-target parsing fails, `decode_skill_post_id_tail_prefix_at` returns `parsed-through-smartTargetPayload` only when the fallback payload hands off to a validated exact switch tail.
- Ambiguous id-marker selection now prefers a unique full scalar parse over fallback payload candidates. This resolves `chr_0017_yvonne_ult_attack3_2` to the final full top-level marker instead of an earlier bridgeable payload candidate.

Focused validation summary:

| Metric | Before | After |
| --- | ---: | ---: |
| `SkillData` files scanned | 2,083 | 2,083 |
| Simple post-id smart-target parses | 2,075 | 2,077 |
| Validated smart-target payload parses | 0 | 6 |
| Ambiguous id-marker rows | 3 | 0 |
| Post-id parse-error rows | 5 | 0 |
| Exact post-switch tails | 2,075 | 2,083 |

Validated smart-target payload rows:

- `chr_0022_bounda_ultimate_skill.json`: 31-byte default/zero-heavy payload; exact switch handoff.
- `chr_0024_deepfin_normal_skill.json`: buff id `buff_common_energy_shard_attached_cryst` and tag `Skill/Character/Common/SpellInflict/CrystInflict`.
- `chr_0028_wulfa_ultimate_skill.json`: buff id `buff_chr_0028_wulfa_normal_bleed`.
- `chr_0028_wulfa_combo_2_skill.json`: tag `Skill/Character/Common/SpellInflict`; this also resolves the last fallback-only ambiguous anchor.
- `chr_0030_zhuangfy_combo_skill.json`: tags `Skill/Character/Common/SpellInflict/PulseInflict` and `Skill/Character/Common/SpellInflict`.
- `chr_0030_zhuangfy_combo_skill_ult.json`: same two tag records as the combo row.

Remaining caveat:

- These rows are now byte-consumed through exact switch-tail validation and expose the semantic strings/tag records that caused the warnings. The generic `BuffFindSettings.buffIdList` and full `GameplayTagQuery` object boundaries are still marked as future deeper semantics rather than claimed as fully proven.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- Direct raw-byte sweep over all `export_full/structured/StreamingAssets/Data/Json/SkillData/*.json` produced `2,077` simple parses, `6` validated smart-target payload parses, `0` ambiguous rows, `0` parse errors, and `2,083` exact post-switch tails.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_skill_smarttarget_validate_20260630` completed and indexed 81,735 Json files, including all 2,083 `Json/SkillData` records.

## 2026-06-30 Structured Json Decoder Status Audit

Added compact decoder-status fields to the data index so warning/error reports can use parser status paths instead of grepping arbitrary sample text.

Result after rebuilding the full Json index:

| Metric | Count |
| --- | ---: |
| Json files indexed | 81,735 |
| Json groups indexed | 30 |
| Entries with decoder status fields (`ds`) | 72,900 |
| Entries with unresolved decoder issue fields (`di`) | 411 |
| `Json/BuffData` unresolved issue rows | 397 |
| `Json/LevelScriptData` unresolved issue rows | 14 |
| `Json/SkillData` unresolved issue rows | 0 |

The previous broad keyword buckets are now classified as false positives rather than parser gaps:

- `Json/LevelData`: 26 hits were the valid gameplay key/string `dont_log_error`.
- `Json/Interactive`: 10 hits were the valid `dont_log_error` component property key with empty component parse errors.
- `Json/NPC`: 2 hits were real content/action names containing `error`.
- `Json/BuffData`: the earlier single `INVALID` sample was a valid payload string; its direct post-id tail parser reached exact EOF.
- `Json/SkillData`: resolved ambiguous-anchor rows retain rejected candidate diagnostics, but those nested `candidateSummaries` are no longer counted as unresolved row issues.

Current strict unresolved status distribution:

| Status | Count |
| --- | ---: |
| `parse-error` | 299 |
| `ambiguous-id-marker` | 98 |
| `truncated` | 14 |

Remaining active parser targets:

- `Json/BuffData`: 397 rows still have top-level `decoded.postIdPrefix` issues, split between repeated-id anchor ambiguity and tail parse errors.
- `Json/LevelScriptData`: 14 rows still report `decoded.triggerVolumesDetails.parseStatus=truncated`.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_status_fields_validate2_20260630` completed and indexed 81,735 Json files.

## 2026-06-30 BuffData Anchors And LevelScript Trigger Volumes

Reduced the current structured Json issue bucket without suppressing unresolved parser gaps.

BuffData root cause and fix:

- `BuffData` previously rejected every row with more than one exact id-string marker as `ambiguous-id-marker`.
- A focused probe showed many of those extra markers are embedded buff references, while exactly one candidate anchor reaches the existing exact-tail parser.
- `decode_buff_post_id_prefix` now probes every exact id marker and selects an anchor only when exactly one candidate parses through exact EOF. Rejected candidates remain recorded in `anchorSelection.candidateSummaries`.

BuffData focused validation:

| Metric | Before | After |
| --- | ---: | ---: |
| `BuffData` files scanned | 2,291 | 2,291 |
| Parsed through exact tail | 1,884 | 1,966 |
| Ambiguous id-marker rows | 98 | 16 |
| Structurally selected ambiguous anchors | 0 | 82 |
| Tail parse-error rows | 296 | 296 |
| Direct post-id parse-error rows | 3 | 3 |

LevelScriptData root cause and fix:

- 12 of the 14 trigger-volume `truncated` rows were not file truncation. `LevelScriptTriggerVolumeShapeData.polyLinePoints` is encoded as 8-byte Vector2 points, while the parser was consuming 12-byte Vector3 points.
- `levelscript_binary.py` now decodes trigger-volume `polyLinePoints` as Vector2 lists.
- The two remaining `indie_hdg009` rows have an impossible top-level trigger-volume map candidate: count `4`, but only `39` bytes remain where at least `100` bytes would be needed for four minimal entries. These now report `count-exceeds-remaining` and stay visible in strict issue counts.

LevelScriptData focused validation:

| Metric | Before | After |
| --- | ---: | ---: |
| Trigger-volume rows decoded | 1,894 | 1,906 |
| Trigger-volume `truncated` rows | 14 | 0 |
| Trigger-volume `count-exceeds-remaining` rows | 0 | 2 |

Full Json strict issue validation after both fixes:

| Metric | Before structured audit | After |
| --- | ---: | ---: |
| Json files indexed | 81,735 | 81,735 |
| Entries with unresolved decoder issue fields (`di`) | 411 | 317 |
| `Json/BuffData` unresolved issue rows | 397 | 315 |
| `Json/LevelScriptData` unresolved issue rows | 14 | 2 |
| `Json/SkillData` unresolved issue rows | 0 | 0 |

Current strict unresolved status distribution:

| Status | Count |
| --- | ---: |
| `parse-error` | 299 |
| `ambiguous-id-marker` | 16 |
| `count-exceeds-remaining` | 2 |

Remaining parser targets:

- `BuffData` non-empty tail bodies: `stackingKey`, `stackEffects`, `timelineActions`, and non-empty `igniteEventAction` are real serialized payloads, not encryption.
- `BuffData` 16 repeated-id rows still lack a unique exact-tail candidate.
- `LevelScriptData` two `indie_hdg009` rows likely need tail-candidate scoring or a better top-level anchor; the raw selected trigger-volume offset is count-impossible.

Validation:

- `python -m py_compile scripts\build_data_index.py scripts\story_builder\levelscript_binary.py` succeeded.
- Focused `BuffData` raw-byte sweep produced `1,966` exact-tail rows, `82` selected repeated-id anchors, `16` ambiguous rows, `296` tail parse errors, and `3` direct parse errors.
- Focused `LevelScriptData` sweep produced `1,906` decoded trigger-volume maps and `2` `count-exceeds-remaining` rows.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_buff_levelscript_validate_20260630` completed and indexed 81,735 Json files.

## 2026-06-30 BuffData Tail Classification

Improved the remaining `BuffData` tail bucket by separating proven non-empty serialized bodies from generic parser desyncs. This does not reduce the strict unresolved row count yet; it makes the remaining work more accurately scoped.

Root cause refined:

- Several rows have a valid `BuffStackingSettings` prefix followed by non-empty `stackEffects` or `timelineActions` lists. The old parser tried to continue through those list bodies as if they were scalar tail fields, which produced misleading `parse-error` messages such as `triggerInterval:member-count=0/4`.
- Some rows contain a clean non-empty `stackingKey` string in the compact stacking-settings suffix. The parser now consumes that branch when the suffix bytes form a clean MemoryPack string.
- A tested hypothesis that `tagsAfterTriggerExtendBuffAction` member-count `2` always carried one extra u32 did not hold across the corpus, so that branch was not promoted.

Focused and full validation after classification:

| Metric | Count |
| --- | ---: |
| `BuffData` files scanned | 2,291 |
| Parsed through exact tail | 1,966 |
| Explicit `unparsed-stackEffects` rows | 82 |
| Explicit `unparsed-timelineActions` rows | 45 |
| Remaining generic BuffData tail `parse-error` rows | 169 |
| Remaining BuffData ambiguous id-marker rows | 16 |
| Remaining direct BuffData post-id parse-error rows | 3 |

Full Json strict issue validation remains at 317 rows, but the status distribution is now more informative:

| Status | Count |
| --- | ---: |
| `parse-error` | 172 |
| `unparsed-stackEffects` | 82 |
| `unparsed-timelineActions` | 45 |
| `ambiguous-id-marker` | 16 |
| `count-exceeds-remaining` | 2 |

Remaining parser targets:

- Implement real decoders or bounded skippers for `BuffStackingSettings.stackEffects` and `BuffData.timelineActions` list bodies.
- Decode or classify nonzero `igniteEventAction`, `poiseModifier`, and `shieldConfigs` bodies without reading their first item member count as a scalar field.
- Revisit `tagsAfterTriggerExtendBuffAction` as a list-shaped GameplayTag payload; it is not always a single tag record.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_buff_tailclass_validate_20260630` completed and indexed 81,735 Json files.

## 2026-06-30 BuffData List-Body And StackingKey Suffix Classification

Promoted the remaining easy `BuffData` tail evidence from generic failures to explicit opaque-body stops.

Root cause refined:

- Nonzero `igniteEventAction`, `poiseModifier`, and `shieldConfigs` counts are real serialized list bodies. The parser now stops at those body offsets and reports `unparsed-igniteEventAction`, `unparsed-poiseModifier`, or `unparsed-shieldConfigs` instead of reading the first item byte as the next scalar field.
- The non-empty `BuffStackingSettings.stackingKey` branch still carries the same compact suffix bytes as the empty-key branch: `stackingType`, `useMaxStackCntKey`, and `usePriorityKey`. Consuming only the string left the parser misaligned and produced misleading downstream tag/trigger errors.
- After consuming that suffix, 143 rows that were generic tail parse errors now land on the real unresolved body: nonzero `timelineActions`.

Full Json strict issue validation after the list-body and suffix fixes:

| Metric | Count |
| --- | ---: |
| Json files indexed | 81,735 |
| Entries with unresolved decoder issue fields (`di`) | 327 |
| `Json/BuffData` unresolved issue rows | 325 |
| `Json/LevelScriptData` unresolved issue rows | 2 |

Current strict unresolved status distribution:

| Status | Count |
| --- | ---: |
| `unparsed-timelineActions` | 188 |
| `unparsed-stackEffects` | 82 |
| `parse-error` | 26 |
| `ambiguous-id-marker` | 16 |
| `unparsed-poiseModifier` | 6 |
| `unparsed-shieldConfigs` | 4 |
| `unparsed-igniteEventAction` | 3 |
| `count-exceeds-remaining` | 2 |

BuffData parser state:

| Status | Count |
| --- | ---: |
| `parsed-through-exact-tail` | 1,966 |
| `parsed-through-timelineActionsCount` | 188 |
| `parsed-through-stackingSettings` | 82 |
| `parsed-through-shieldConfigsCount` | 30 |
| `ambiguous-id-marker` | 16 |
| `parsed-through-poiseModifierCount` | 6 |
| `parsed-through-igniteEventActionCount` | 3 |

Remaining parser targets:

- Decode or bounded-skip `timelineActions` and `stackEffects` list bodies. These now account for 270 of the 325 remaining BuffData strict rows.
- Resolve the 26 remaining BuffData generic parse errors; raw-byte probes suggest at least some are GameplayTag/Blackboard field-shape variants rather than encryption.
- Resolve 16 repeated-id BuffData rows where no unique exact-tail anchor exists yet.
- Investigate the two `LevelScriptData` `count-exceeds-remaining` rows separately; their current trigger-volume candidate is count-impossible.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_buff_stackingkey_validate_20260630` completed and indexed 81,735 Json files.

## 2026-06-30 BuffData Omitted Empty Timeline Count Recovery

Recovered a smaller `BuffData` tail variant where the serialized tail omits the explicit empty `timelineActions` count and jumps directly from `tagsAfterTriggerExtendBuffAction` to `triggerInterval`.

Root cause refined:

- Many remaining generic `timelineActionsCount:large-count` errors were not real large list counts. The parser was reading the first four bytes of a `BlackboardDouble`/float field, for example `03 08 00 00 "duration"` or `03 08 00 00 "interval"`, as a little-endian timeline action count.
- The new fallback accepts this only when `triggerInterval`, `useTimeDilationDt`, `waitFirstTriggerInterval`, and EOF all validate from the same offset. It records `timelineActionsEncoding=omitted-empty-count` and keeps `timelineActionsCount=0`.
- One row uses a `tagsAfterTriggerExtendBuffAction` member-count-1 empty payload before the direct trigger tail. That branch is recorded as `member1-empty-payload` and is also accepted only when the full remaining tail validates to EOF.

Focused BuffData validation:

| Metric | Before | After |
| --- | ---: | ---: |
| `BuffData` files scanned | 2,291 | 2,291 |
| Parsed through exact tail | 1,966 | 1,981 |
| Generic BuffData tail `parse-error` rows | 26 | 11 |
| `timelineActionsEncoding=omitted-empty-count` rows | 0 | 14 |
| `member1-empty-payload` tag rows | 0 | 1 |

Full Json strict issue validation after this recovery:

| Metric | Count |
| --- | ---: |
| Json files indexed | 81,735 |
| Entries with unresolved decoder issue fields (`di`) | 312 |
| `Json/BuffData` unresolved issue rows | 310 |
| `Json/LevelScriptData` unresolved issue rows | 2 |

Current strict unresolved status distribution:

| Status | Count |
| --- | ---: |
| `unparsed-timelineActions` | 188 |
| `unparsed-stackEffects` | 82 |
| `ambiguous-id-marker` | 16 |
| `parse-error` | 11 |
| `unparsed-poiseModifier` | 6 |
| `unparsed-shieldConfigs` | 4 |
| `unparsed-igniteEventAction` | 3 |
| `count-exceeds-remaining` | 2 |

Remaining parser targets:

- The 11 remaining generic BuffData rows are mostly Ruanyi variants with embedded Skill paths and extra numeric blocks in the tag/timeline region, plus one Ethillu fake-dead variant. They should stay visible until the list-body shape is understood.
- `timelineActions` and `stackEffects` remain the dominant unresolved bodies and are being investigated separately.

Validation:

- `python -m py_compile scripts\build_data_index.py` succeeded.
- Focused BuffData decode over all 2,291 rows produced `1,981` exact-tail rows, `188` `unparsed-timelineActions`, `82` `unparsed-stackEffects`, and `11` generic parse errors.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_buff_omitted_timeline_validate_20260630` completed and indexed 81,735 Json files.

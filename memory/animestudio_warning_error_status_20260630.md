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

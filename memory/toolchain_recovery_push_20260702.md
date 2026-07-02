# Toolchain Recovery Push - 2026-07-02

## Scope

Checked local AnimeStudio, fluffy-dumper, IL2CPP metadata/DummyDll outputs, and public tool docs for the next safe source of game-data recovery evidence.

## Local Tool Status

- `tools/AnimeStudio` is healthy enough for WebUI/export work. The built CLI exists at `tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`; `list` and help paths work. It exposes VFS `dump`, `stream`, `vfs-index`, `audio`, and `list`, plus DummyDll/TypeTree-related MonoBehaviour export paths.
- `tools/fluffy-dumper-src\target\release\fluffy-dumper.exe` is runnable and provides VFS `dump`, `audio`, `vfs-index`, and `list`. It is useful for VFS/audio/index evidence, but this checkout has no general IL2CPP, TypeTree, MonoBehaviour, or MemoryPack schema parser in fluffy-dumper.
- `tools/endfield-il2cpp` is the current reliable local source for declaration metadata. The targeted probe wrote `tmp\buff_action_runtime_metadata_probe_20260702.json` and `.md` from installed `global-metadata.dat` version 29.
- `tools/Cpp2IL-endfield-patched-dlls4` contains many DummyDlls, including `Gameplay.Beyond.dll` and `MemoryPack.Beyond.dll`, but the MemoryPack DummyDll type set is partial/corrupted for this task. Treat `global-metadata.dat` parser output as stronger evidence than DummyDll reflection here.

## External Tool Constraints

- MemoryPack's public docs confirm object payloads are member-count plus values, not self-delimiting, and member order is schema-dependent. This supports fail-closed parsing: wrapper/order evidence is not enough to split a chain when nested objects do not expose their own end.
- Il2CppDumper public docs confirm DummyDll/script outputs are intended for restored assemblies and MonoBehaviour/MonoScript extraction.
- AssetStudio public docs confirm IL2CPP MonoBehaviour export expects Il2CppDumper-generated DummyDlls.
- Cpp2IL public docs describe it as a work-in-progress IL2CPP reverse tool; local patched outputs are useful, but not sufficient by themselves for BuffData MemoryPack body order.

## BuffData Schema Evidence

Runtime IL2CPP field-token order is recoverable for:

- `FindTargetAction+FindTargetActionData`: `targetGroupKey`, `center`, `centerContextKey`, `useCenterEntityMountPoint`, `centerMountPoint`, `centerToGround`, `selectorOwner`, `selectorOwnerContextKey`, `selectorData`, `selectorDirection`, `target`, `contextKey`, `useAdvancedDirectionSetting`, `advancedSelectorDirection`.
- `Selector+SelectorData`: `finderData`, `validatorData`, `postProcessorData`.
- `TargetSettings`: `targetSource`, `targetGroupKey`, `selectorOwner`, `ownerContextKey`, `centerType`, `centerContextKey`, `centerToGround`, `selectorData`, `enableAdvancedDirection`, `advancedDirection`, `selectorDirection`, `target`, `targetContextKey`; static `Default` is not serialized.
- `DamageAction+DamageActionData`: `alwaysNext`, `attacker`, `targetSettings`, `effectSource`, `damageUnits`, `hitEnvironment`, `hitEnvData`.
- `DamageAction+DamageUnit`: 32 fields from `damageType` through `costDataList`.
- `HitSoundData`: `soundEvent`.

Generated `*ForMemoryPack` wrapper types are present in metadata for all of the above, including `FindTargetActionData`, `SelectorData`, `TargetSettings`, `DamageActionData`, `DamageUnit`, `HitSoundData`, and `HitEnvData`. Their setter-token order is a strong candidate for MemoryPack order, but no generated `Deserialize` body call order was recovered from this probe, so only byte-validated layouts should be promoted.

## Code Outcome

`scripts/build_data_index.py` was hardened after review:

- Added bounded common-prefix reads and switched action consumers to them.
- Rejected prefix-only FindTargetAction partials.
- Removed `DamageAction` from chain consumption until `DamageUnit` boundaries are proven. Exact single-item DamageAction probing remains available.
- Updated FindTargetAction schema note to mention generated wrapper presence while keeping selector/TargetSettings body opaque. Then promoted an exact-only FindTargetAction body partial: `advancedSelectorDirection.memberCount/directionType`, `selectorOwner`, `selectorOwnerContextKey`, `target`, `targetGroupKey`, and the two tail booleans are decoded only when the known item end is already proven; selector/middle bytes remain opaque and chain consumption remains disabled.

Validation:

- `python -m py_compile scripts\build_data_index.py` passed.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_toolchain_safety_validate_20260702` completed: 163,822 files, 30 groups.
- python scripts\build_data_index.py --groups Json --output tmp\game_data_index_findtarget_tail_validate_20260702` completed: 163,822 files, 30 groups after the exact-only FindTargetAction tail promotion.
- Compared to `tmp\game_data_index_final_validate_20260702`, the safety rollback changed only compact `ds` detail on the duplicate `buff_eny_0113_jzogre_skill05_onground_attack` entries. Compared to `tmp\game_data_index_toolchain_safety_validate_20260702`, the FindTarget tail promotion changed only `groups\Json_BuffData.json` and `index.json`, with 12 compact BuffData rows gaining exact-only FindTarget partial fields; no missing/extra files.
- Direct BuffData decode scan after rollback and FindTarget tail promotion: 24 `typed-chain-items`, 526 `single-item`, 112 ambiguous, 14 empty; item statuses 34 exact / 374 partial / 190 opaque. Exact FindTarget partials decode 20/20 with `targetGroupKey` values `thunderTarDmg` (8), `tar` (4), `abe` (4), `main` (2), and `ballPos` (2); all have `selectorOwner=1`, `target=0`, and direction type raw `1`.

## Next Safe Work

- Do not re-enable DamageAction chain consumption until `damageUnits` can be consumed exactly by count, including `DamageUnit`, `HitSoundData`, effect data, processors, and cost subblocks.
- Use IL2CPP metadata and byte evidence to target `SelectorData` first, because `FindTargetAction` is still the largest chain blocker (`no-typed-consumer=Core_FindTargetAction_FindTargetActionData` in 40 duplicate-root records).
- Consider an AnimeStudio raw-sidecar MonoBehaviour refresh only for MonoBehaviour managed-reference boundaries. It is not a replacement for raw BuffData table MemoryPack parsing.
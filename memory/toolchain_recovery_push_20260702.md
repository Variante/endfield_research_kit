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

## Follow-up: DamageAction tail and selector tag evidence

Second pass on 2026-07-02 changed the DamageAction conclusion. Full DamageUnit parsing is still unsafe, but chain consumption is safe for the one proven tail shape when all of these checks pass:

- `DamageActionData` tag/member count and common AbilityActionData prefix validate.
- Declared `damageUnits.count` is 1..16 and the first opaque unit starts with member count 32.
- The tail search starts only after `damageUnits.count * 64` opaque bytes, so a later target-settings-like byte pattern cannot be accepted immediately after the first unit marker.
- `effectSource` TargetSettings, bounded `HitEnvData + hitEnvironment`, and final `targetSettings` all consume exactly to the candidate item end. The HitEnv block still has unproven field names and remains partial.

Code result: `scripts/build_data_index.py` now registers `DamageAction` as a consume decoder again, but only through the exact bounded tail proof above. It still keeps `DamageUnit`, `HitSoundData`, effect data, and cost data opaque.

Validation:

- `python -m py_compile scripts\build_data_index.py` passed.
- `python scripts\build_data_index.py --groups Json --output tmp\game_data_index_damage_consume_validate_20260702` completed: 163,822 files, 30 groups.
- Compared to `tmp\game_data_index_findtarget_tail_validate_20260702`, only two compact BuffData entries changed: the duplicate StreamingAssets/Persistent copies of `buff_eny_0113_jzogre_skill05_onground_attack.json`.
- Direct decode of that row now splits record 0 as `DamageAction` (619 bytes, one opaque 426-byte DamageUnit, exact 35-byte HitEnv span) followed by `CameraImpulse` (366 bytes). Record 1 remains a single `EffectAction` item. No other BuffData compact rows changed.

Selector formatter body-map evidence:

- `tmp\selector_formatter_body_map_20260702.json/md` maps six selector formatter methods from installed `GameAssembly.dll` plus installed `global-metadata.dat`.
- `Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPack+...Formatter..cctor` at VA `0x185a738b0` constructs a dictionary-like table with capacity 9 and adds tag constants 0..8. Its `Deserialize` body at VA `0x18548afc0` also bounds dispatch with `cmp eax, 0x8`, so tag range 0..8 is high-confidence.
- Finder formatter `Deserialize` at VA `0x184c41d60` and Validator formatter `Deserialize` at VA `0x1850e7710` each bounds dispatch with `cmp eax, 0x6`, so their tag range 0..6 is medium-confidence.
- Do not promote selector subtype names yet. The body map currently resolves type-handle storage addresses, not managed subtype names. This evidence can constrain future parsers but cannot label selector finder/validator/postprocessor variants by itself.

Tool status / online source check:

- Local AnimeStudio CLI remains the preferred active extractor: VFS `dump`, `stream`, `vfs-index`, `audio`, `list`; recent logs have zero export errors and DummyDlls resolve from `tools\DummyDll`.
- Local fluffy-dumper is useful for VFS/audio/index checks but still has no general IL2CPP, TypeTree, MonoBehaviour, or MemoryPack schema parser.
- Public references checked: MemoryPack docs (`https://github.com/Cysharp/MemoryPack`) confirm member order and union serialization matter; Cpp2IL (`https://github.com/SamboyCoding/Cpp2IL`) and Il2CppDumper (`https://github.com/Perfare/Il2CppDumper`) are still metadata/body-recovery helpers; AssetStudio (`https://github.com/Perfare/AssetStudio`) is archived, while AssetRipper (`https://github.com/AssetRipper/AssetRipper`) is a better current candidate to compare against AnimeStudio for general Unity asset analysis.

Next safe work:

- Use the selector formatter tag ranges as constraints while looking for a metadata-usage/type-handle resolver that maps handle storage VAs such as `0x18ec32ff8` back to managed type names.
- Keep FindTargetAction out of chain consumption until `SelectorData` has a self-delimiting parser. The exact-only FindTarget tail parser remains valid for already-bounded single items.
- Consider targeted AnimeStudio probes only for VFS indexes, raw sidecars, and MonoBehaviour managed-reference boundaries; raw BuffData table parsing remains in `scripts/build_data_index.py`.

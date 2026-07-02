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

## Follow-up: selector subtype labels

A direct pass through the existing metadata-slot decoder resolved the PostProcessor formatter handle-storage VAs from `GameAssembly.dll`:

| tag | selector postprocessor formatter |
|---:|---|
| `0x0000` | `Core_Selector_ConvertToBoxCenterPlaneProjectionPoint_Data` |
| `0x0001` | `Core_Selector_ConvertToPosition_Data` |
| `0x0002` | `Core_Selector_ConvertToSlot_Data` |
| `0x0003` | `Core_Selector_ExcludeTarget_Data` |
| `0x0004` | `Core_Selector_LockOrMarkTargetFilter_Data` |
| `0x0005` | `Core_Selector_NavMeshPathPositionProcessor_Data` |
| `0x0006` | `Core_Selector_PriorityFilter_Data` |
| `0x0007` | `Core_Selector_ShuffleTarget_Data` |
| `0x0008` | `Core_Selector_TargetPriorityFilter_Data` |

Snapshot before the reproducible selector audit below: PostProcessor was the only selector family with explicit tag-to-formatter evidence from the existing ActionBase-style scanner. Finder and Validator still only had range constraints and metadata slot names at this point.

Spot checks of exact FindTarget bodies (`buff_chr_0026_lastrite_normal_skill_phantom`, `buff_chr_0030_zhuangfy_sword_triggerd`, `buff_eny_0116_zfydef_fireball`) show selector/middle bytes with plausible tag-like values and parameter strings, but no self-delimiting selector span. Keep `FindTargetAction` chain consumption disabled until `SelectorData` can prove its own end.

## Follow-up: reproducible selector formatter audit

Added `scripts/story_recovery/build_selector_formatter_tag_audit.py` so selector formatter tag recovery is repeatable after game updates instead of depending on inline probes. The script writes generated evidence to `reports/mission_order/selector_formatter_tag_audit.json` and `.md`.

Validation on the installed 2026-05-27 `GameAssembly.dll` and installed `global-metadata.dat`:

- `python -m py_compile scripts\story_recovery\build_selector_formatter_tag_audit.py` passed.
- `python scripts\story_recovery\build_selector_formatter_tag_audit.py --metadata "D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat"` completed.
- Recovered explicit cctor registration rows:
  - Finder: 20 tags, `0x0000..0x0013` (`AbilityEntityTargetFinder`, `CharacterTeamFinder`, `FixedPointFinder`, `GlobalContextFinder`, `GodEntityFinder`, `GuardAITargetFinder`, `HitBoxFinder`, `InFightEnemyFinder`, `InteractiveShapeFinder`, `MainTargetFinder`, `OwnerPartsFinder`, `OwnerSpawnedEntityFinder`, `PointFinder`, `RandomPointFinder`, `ShapeFinder`, `ShapeFinderData`, `SmartTargetFinder`, `SnapPointFinder`, `SourceFinder`, `TargetFinder`).
  - Validator: 11 tags, `0x0000..0x000a` (`AttributeValidator`, `CheckRaycastValidator`, `CurHpRatioValidator`, `DistanceValidator`, `ExcludeOwnerValidator`, `HittableObjectValidator`, `InteractiveKeyValidator`, `MainCharacterValidator`, `SkillCastIdValidator`, `TagValidator`, `TargetContainsValidator`).
  - PostProcessor: 9 tags, `0x0000..0x0008` (`ConvertToBoxCenterPlaneProjectionPoint`, `ConvertToPosition`, `ConvertToSlot`, `ExcludeTarget`, `LockOrMarkTargetFilter`, `NavMeshPathPositionProcessor`, `PriorityFilter`, `ShuffleTarget`, `TargetPriorityFilter`).

This upgrades the selector tag evidence from range-only to explicit tag-to-formatter maps. It still does not make FindTargetAction safe for chain consumption: exact FindTarget body spot checks show selector/middle bytes with plausible tag-like values and parameter strings, but no proven self-delimiting `SelectorData` end yet.

## Follow-up: skipped VFS block inventory

Checked the repo-local VFS toolchain after the selector audit:

- `tools/fluffy-dumper-src/target/release/fluffy-dumper.exe` is built and supports `dump`, `audio`, `vfs-index`, and `list`, including local `--fallback-assets` support.
- `tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe` supports the same block families and adds repeated `--block-type`, `--file-regex`, and the JSONL `stream` command. For targeted recovery probes, AnimeStudio is the better first tool; fluffy-dumper remains useful for parity checks.
- Online tool survey: AssetRipper is the active modern Unity fallback; AssetStudio and RazTools/Studio are archived/older. Il2CppDumper remains useful for DummyDlls, and Cpp2IL is useful for deeper IL2CPP method/IR analysis, but neither replaces the local Endfield VFS-specific dumpers.

Generated a disposable index for WebUI-skipped VFS blocks:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --streaming-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" --output tmp\skipped_vfs_index_20260702.json --block-type lua --block-type extend-data --block-type streaming --block-type dynamic-streaming --block-type bundle-manifest --block-type i-fix-patch --block-type audit-streaming --block-type audit-dynamic-streaming --block-type audit-iv
python scripts\story_recovery\build_skipped_vfs_block_audit.py --index tmp\skipped_vfs_index_20260702.json
```

Result: `39,738` files, `3,145,356,881` bytes, `83` chunks, no missing indexed blocks. The generated report is `reports/mission_order/skipped_vfs_block_audit.md`.

Most actionable blocks:

- Lua: `1,174` encrypted `.lua` files, `17,818,916` bytes total. A narrow dump with `--file-regex "DialogConst|SNSContent|RemoteComm|PanelConfig|GameSetting"` extracted plaintext Lua. The sample confirms useful runtime consumers: `SNSContentBase` reads `Tables.sNSDialogTable[dialogId].dialogContentData[contentInfo.contentId]`, `SNSContentPic` resolves `contentParam` through `SNSUtils.getDiffPicNameByGender`, and `PhaseRemoteComm` drives `RemoteCommonData` display through `RemoteComm`/`RemoteCommHud` panels.
- ExtendData: `StringPathHash.bin` (`103,398,986` bytes) plus `CompressData.bin` (`575,057` bytes). This looks high-value for resolving hashed paths/references before broad asset dumps.
- BundleManifest: single encrypted `Data/Bundles/Windows/manifest.hgmmap` (`44,596,126` bytes). Useful for bundle dependency/name recovery if parsed.
- Streaming/DynamicStreaming: large scene/world byte families. Keep to `vfs-index`, `stream --file-regex`, or very narrow dump probes until a parser target is known.

Added `scripts/story_recovery/build_skipped_vfs_block_audit.py` so this prioritization can be regenerated from any future `vfs-index` JSON.

Next split tracks:

- Lightweight VFS track: dump all Lua or a curated Lua subset, then build a Lua consumer/reference audit for SNS, RemoteComm, Dialog, map marks, and mission UI tables.
- AnimeStudio refresh track: run a separate current MonoBehaviour `json_by_type` refresh with `tools\DummyDll`, then rebuild a decoded index. This rewrites `export_full/recovered/AnimeStudio-cli/**`, so keep it out of the VFS-audit commit.
- IL2CPP track: follow the selector/TargetSettings metadata-body audit before re-enabling `FindTargetAction` chain consumption.

## Follow-up: Persistent skipped blocks and ExtendData parity

Ran the skipped-block probe against `Persistent` with `StreamingAssets` fallback:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o "D:\fluffy-dump\tmp\vfs_skipped_probe\Persistent_nonbundle_vfs_index.json" -b bundle-manifest -b extend-data -b streaming -b dynamic-streaming -b iv -b lua -b i-fix-patch -b hotfix-audio
python -B scripts\story_recovery\build_skipped_vfs_block_audit.py --index tmp\vfs_skipped_probe\Persistent_nonbundle_vfs_index.json --output-json reports\mission_order\skipped_vfs_block_audit_persistent.json --output-md reports\mission_order\skipped_vfs_block_audit_persistent.md
```

Persistent result: `40,004` files, `11,828,335,706` bytes, `146` chunks. It keeps the same Lua/Streaming/DynamicStreaming shape as StreamingAssets, but adds `IV` (`263` files, `8,647,006,666` bytes), `HotfixAudio` (`1` PCK, `34,412,094` bytes), and `IFixPatchOut` (`2` encrypted `.bytes`, `56,424` bytes). Treat `IV` as a large separate parser target; do not broad dump it.

Ran an ExtendData parity check between fluffy-dumper and AnimeStudio on StreamingAssets:

```bat
.\tools\fluffy-dumper-src\target\release\fluffy-dumper.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o "D:\fluffy-dump\tmp\fluffy_parity\StreamingAssets_extend-data_fluffy.json" -b extend-data
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o "D:\fluffy-dump\tmp\fluffy_parity\StreamingAssets_extend-data_animestudio.json" -b extend-data
```

Parity matched exactly for the two StreamingAssets ExtendData files: same filenames, sizes, data MD5s, and chunk path.

Narrow dumped ExtendData only for header probing:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump -s "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o "D:\fluffy-dump\tmp\extenddata_probe\StreamingAssets" -b extend-data
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump -s "D:\Program Files\Endfield Game\Endfield_Data\Persistent" --fallback-assets "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets" -o "D:\fluffy-dump\tmp\extenddata_probe\Persistent" -b extend-data
```

Findings:

- `CompressData.bin` starts with a 57-entry ascending little-endian offset table. The first offset is `0xE4` (`228`), and later offsets include `916`, `2731`, `4476`; most segment lengths match a segment-local first u32 plus 8. No `Data/`, `SNS`, `Dialog`, `RemoteComm`, `Compress`, or `StringPath` ASCII was found, and quick zlib/zstd/lz4/gzip probes did not decode segments.
- StreamingAssets `StringPathHash.bin` starts with `11030624, 459609, 0, 0`; Persistent starts with `11108816, 462867, ...`. Both look like dense fixed numeric/hash tables with no ASCII hits.
- Existing `scripts/build_data_index.py --groups ExtendData` refuses the group by design because the active WebUI Data index only supports decoded `Json`. Keep ExtendData recovery as a focused audit/probe track until exact semantics are proven.

The reviewed VFS audit script now includes block records even when a requested block has zero files, readable missing-block labels, `InitialExtendData` priority text, chunk/missing-chunk counts, and preserved multiline CLI help.

## Follow-up: selector TargetSettings body audit

Added `scripts/story_recovery/build_selector_targetsettings_body_audit.py` to make the selector/TargetSettings IL2CPP body evidence reproducible. It builds a focused MemoryPack metadata catalog, maps targets to `GameAssembly.dll`, preserves the full raw body report at `reports/mission_order/selector_targetsettings_body_targets_gameassembly.json` / `.md`, and writes a compact chain-gate summary at `reports/mission_order/selector_targetsettings_chain_summary.json` / `.md`.

Validation on the installed `GameAssembly.dll` and installed `global-metadata.dat`:

```bat
python -B -m py_compile scripts\story_recovery\build_selector_targetsettings_body_audit.py tools\endfield-il2cpp\catalog_option_flow_metadata.py
python scripts\story_recovery\build_selector_targetsettings_body_audit.py --metadata "D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat" --gameassembly "D:\Program Files\Endfield Game\GameAssembly.dll"
```

Current output maps `311/311` focused selector body targets across `147` MemoryPack types, resolves `3,999` direct calls, and finds `140` direct calls back into focused catalog targets. The compact summary now includes:

- wrapper call order for `ContinuousFindTargetAction`, `EffectFindTargetAction`, `SelectorData`, and `TargetSettingsForMemoryPack` deserializers;
- setter store offsets for `FindTargetActionData`, `SelectorData`, and `TargetSettings` fields, including `FindTargetActionData.selectorData` at `0x50`, `SelectorData.finderData`/`validatorData`/`postProcessorData` at `0x10`/`0x18`/`0x20`, and `TargetSettings.selectorData` at `0x48`;
- four alias warnings where one method-pointer VA resolves as both `TargetSettingsForMemoryPack.set___targetGroupKey__` and `SelectorDataForMemoryPack.set___validatorData__`; consumers must disambiguate by caller/context, not VA alone;
- selector formatter tag-map ranges from `selector_formatter_tag_audit`: Finder `0x0000..0x0013`, Validator `0x0000..0x000a`, PostProcessor `0x0000..0x0008`.

This upgrades the FindTargetAction evidence from separate raw reports into a single reproducible gate summary. It still does not enable chain consumption: the missing proof is a sample-byte parser that shows nested `SelectorData`/`TargetSettings` payloads are self-delimiting and end at the exact expected offset in real BuffData rows.

## Follow-up: FindTarget selector boundary sample audit

Added `scripts/story_recovery/build_findtarget_selector_boundary_audit.py` to scan real exported BuffData through the existing `scripts/build_data_index.py` decoder and make the FindTargetAction parser gate measurable.

Validation:

```bat
python -B -m py_compile scripts\story_recovery\build_findtarget_selector_boundary_audit.py
python scripts\story_recovery\build_findtarget_selector_boundary_audit.py
```

Current scan over `4,616` BuffData files found `24` already-decoded single-item FindTargetAction samples, grouped into `7` unique body-middle byte shapes, plus `30` ambiguous records where the first action is FindTargetAction but the action-data list cannot be safely split by typed consumption yet. The existing TargetSettings envelope parser accepts `0` candidates inside all decoded FindTargetAction body-middle bytes. The JSON report now keeps complete `bodyMiddleHex` bytes on both samples and unique shapes, so parser experiments can replay the opaque regions without reopening every BuffData source file.

This is useful negative evidence: the TargetSettings envelope shape used by other action parsers is not directly embedded in the current FindTargetAction middle bytes. The next parser work should focus on the selector/DirectionSettings reader state and ambiguous action-list splitting, not on reusing the current `read_buff_target_settings_envelope_partial` shape inside FindTargetAction.

## Follow-up: Lua consumer reference audit

Added `scripts/story_recovery/build_lua_consumer_reference_audit.py` to turn the already-extracted AnimeStudio VFS Lua into reproducible consumer evidence. It scans `export_full/structured/Persistent/Lua` and `export_full/structured/StreamingAssets/Lua`, deduplicates modules by relative Lua path, extracts `Tables.*`, `GEnums.*`, `CS.Beyond.*`, `contentParam`, dialog/RemoteComm ids, sprite/video/audio helper references, and writes `reports/mission_order/lua_consumer_reference_audit.json` / `.md`.

Validation:

```bat
python -B -m py_compile scripts\story_recovery\build_lua_consumer_reference_audit.py
python scripts\story_recovery\build_lua_consumer_reference_audit.py --lua-root export_full\structured\Persistent\Lua --lua-root export_full\structured\StreamingAssets\Lua --focus sns,remotecomm,dialog,mapmark,mission
```

Current output scans `2,348` Lua files across both roots, groups them into `1,174` unique modules, and finds `1,127/1,174` duplicated modules with identical bytes between Persistent and StreamingAssets. It records `3,641` `Tables.*` references, `2,413` `GEnums.*` references, `1,486` `CS.Beyond.*` references, `808` sprite helper hits, `284` video helper hits, and `1,457` audio helper hits. Of `502` distinct Lua `Tables.*` names, `494` match exported Table JSON names, covering `3,632/3,641` table-reference uses; only `8` names are unmatched (`formulaIdToStr`, `i18nTextTable`, `equipTierLevelTable`, `skillLockTable`, `blocShopItemTable`, `settlementOrderDataTable`, `formulaIdToNum`, `factoryProcessorCraftTable`). The JSON now also emits `2,027` graph-ready Lua module-to-table edge candidates with module path, table reference name, use count, focus tags, matched exported table name, and exported table paths.

Focused module coverage is: SNS `57`, RemoteComm `36`, Dialog `32`, map marks `86`, and mission UI `95`. Top focused modules include `Common/Utils/SNSUtils.lua`, `Phase/SNS/PhaseSNS.lua`, `UI/Widgets/SNSDialogContentCore.lua`; `LuaSystem/RadioSystem.lua`, `UI/Panels/RemoteComm/RemoteCommCtrl.lua`, `Phase/RemoteComm/PhaseRemoteComm.lua`; `UI/Widgets/FriendDialogueSendArea.lua`, `Phase/Dialog/PhaseDialog.lua`; `Phase/Map/PhaseMap.lua`, `UI/Widgets/LevelMapMark.lua`, `Common/Utils/MapUtils.lua`; and `UI/Panels/Mission/MissionCtrl.lua`, `UI/Panels/MissionHud/MissionHudCtrl.lua`, `UI/Panels/CommonTaskTrackHud/CommonTaskTrackHudCtrl.lua`.

This makes Lua the best next WebUI/source-graph enrichment path: add graph edges from Lua modules to table ids/enums/CS APIs and use the focus report to prioritize SNS/Dialog/RemoteComm/map-mark/mission consumer links before spending more effort on opaque ExtendData or unsafe FindTargetAction chain parsing.

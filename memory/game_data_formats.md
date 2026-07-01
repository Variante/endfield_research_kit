# StreamingAssets Data Format Notes

Source inspected: `export_full/structured/StreamingAssets/Data` and `export_full/structured/Persistent/Data`.

## Summary

- Current moved StreamingAssets root contains `Audio/`, `Bundles/`, `DynamicStreaming/`,
  `ExtendData/`, `IrradianceVolume/`, `Json/`, `Streaming/`, and `Video/`, but
  the active WebUI Data index only tracks final decoded config files under
  `Json/` from both StreamingAssets and Persistent.
- Current decoded Data scope: 163,822 `.json` config files, 1,403,397,770 bytes
  (about 1,338.4 MiB), split into 30 lazy-loaded groups.
- Source split: 81,735 StreamingAssets files and 82,087 Persistent files.
- `Json/`: 6,070 parseable text JSON files plus 157,752 binary MemoryPack-like
  config blobs with `.json` names.
- Raw archive/media folders are intentionally excluded from the Data tab:
  `.ab` bundles, packed Wwise audio, videos, streaming bytes, irradiance
  volumes, extend-data indexes, and bundle maps belong to the asset/export
  tooling rather than this decoded-config browser.

## Text JSON

The parseable subset starts with regular JSON text (`{` or `[`) and is UTF-8
compatible in this export. Major parseable groups include:

- `GameplayConfig/`
- `MapConfig/`
- `MissionRuntimeAsset/`
- `NPC/` top-level hash maps and avatar configs
- `UILevelMapLoadConfig/`
- several root `Json/*.json` tables

The WebUI Data tab classifies these as `text-json` and parses them for shape,
top keys, row counts, and selected sample strings.

## Binary `.json`

Binary `.json` families include:

- `AnimationConfig/`: 12-member MemoryPack blobs beginning with `0C`; the Data index now keeps the recovered root field schema, verifies the trailing `useRotateDirection` / `useStateVariables` boolean bytes for all 106 files, and previews animation state names, facial morph paths, montage paths, actor animation refs, and cutscene refs while leaving nested montage/curve bodies opaque.
- `AtmosphericNpcData/`: 1-member MemoryPack table blobs beginning with `01`; empty files are `01 00 00 00 00`, non-empty files expose verified row counts and 109-member NPC row boundaries, and the Data index previews row keys, AI configs, montage/facial paths, envTalk ids, templates, clusters, and levels while leaving the full row payload opaque.
- `BuffData/`: 29-member MemoryPack-like blobs beginning with `1D`; the Data index verifies the filename-stem `id` string for every row, reports exact length-prefixed id marker counts/offsets, and exposes installed-IL2CPP setter parameter types for the top-level schema: 13 scalar/flag/id fields and 16 complex/list fields. Rows with one exact top-level id marker parse the post-id prefix for 2,190 entries, exposing `igniteEventAction` count, `ignoreCooldownWhenAdding`, `ignoreTagImmune`, raw `lifeType`, `maxTriggerCnt` BlackboardInt, `poiseModifier` count, and `shieldConfigs` count where the intervening list is empty. A validated compact `BuffStackingSettings` Id-branch tail now consumes exactly for 1,884 rows and exposes `stackingType`, `maxStackCnt`, `triggerInterval`, and final wait/time-dilation flags; the remaining prefix-only rows stay opaque at non-empty list/body branches. Samples still preview length-prefixed tags, parameters, and references while middle modifier/action/blackboard/list bodies remain structurally opaque.
- `CharInteractPerformCfgs/`: 26-member MemoryPack blobs beginning with `1A`; the Data index now parses the exact `activeTags` GameplayTag list, `allowInheritPerform` boolean, and `bodyTypeActDataDict` count for all 159 files, then classifies body string previews into status tags, montage refs, actors, effects, perform refs, assets, CCS refs, and state/param strings while leaving the nested perform body opaque.
- `LevelData/`: 42-member MemoryPack blobs beginning with `2A`; the Data index now verifies the parent scene-id string for all 783 files across 141 scene folders and previews level script refs, task markers, params, refs, and assets.
- `LevelConfig/`: 15-member MemoryPack blobs beginning with `0F`; the Data index now verifies all 141 filename-stem ids, parses the default-state object, reads LevelData path counts, parses map ids and numeric transform/bounds tails, and leaves the middle path/grid payload opaque until nested evidence is mapped.
- `LevelScriptData/`: 26-member MemoryPack blobs beginning with `1A`; the Data index verifies filename-stem `scriptId` occurrences, decodes top-level `actionMap` status/counts, start shape/start type/task map/trigger-volume facts, and now splits present `ActionSerializedMap` payloads into compact `actionList`, `getterList`, and `headerList` list counts using UID record boundaries. All 3,658 files validate through the compact action-map helper with zero errors: 3,285 action maps are present and 373 use the absent marker. Generated summaries expose `uidRecords=`, serialized list counts, and action-list root/linked membership counts where UID records can be assigned, while full action payload semantics and residual/unanchored UID blocks remain bounded hints for the Story recovery workflow.
- `LevelScriptTemplateData/`: 6-member MemoryPack blobs beginning with `06`; the Data index now parses the exact ActionSerializedMap-style `actionMap` header for all 35 files, verifies the tail `templateId` filename stem, and classifies length-prefixed strings into key-like names, hashes, property refs, map-property refs, local refs, LSM keys, montage refs, audio/effect refs, and comments while leaving `maxStage`, properties, property maps, and task-map bodies structurally opaque.
- `GameplayConfig/DialogIdTable.json`: five-member MemoryPack root now parses exactly, including all 2,258 seven-member `DialogBriefInfo` rows in generated formatter order (`afterMaskBlendData`, `beforeMaskBlendData`, `dialogId`, `dialogType`, `interactText`, `npcProxyIds`, `useBlackScreen`), plus 2,258 int-to-dialog rows, 4,182 int-to-option rows, 4,182 reverse dialog/option id rows, and 2,258 reverse dialog rows; mask blend records expose exact surrounding fields while keeping only the nested curve bytes bounded.
- `GameplayConfig/*TeleportValidationDataTable.json`: four binary one-member MemoryPack tables now parse as keyed teleport rows with value member count 10, duplicate id strings, a float field, flag word, position/rotation vec3s, nullable map ids, and four observed tail ints; `LevelScriptTeleportValidationDataTable.json` is text JSON and remains handled by the text parser.
- `GameplayConfig/ModelRadiusTable.json`: one-member MemoryPack table beginning with `01`; the Data index now parses all 1,125 model-id rows, verifies a four-member value object marker for every row, exposes the observed constant fields/flag byte and finite radius float, and consumes the file exactly.
- `GameplayConfig/ModelTable.json` and `NonGeneratedConfigs/ModelTable.json`: two-member MemoryPack roots now parse exactly as a model-id dictionary plus a layout-key dictionary; the model rows expose nullable alternate ids, flag bytes, duplicate model ids, prefab paths, scale floats, and observed tail ints, while the layout rows now decode the 12-member `ModelExtraData_Interactive` body (`center`, collision/shape/obstacle flags, `dynamicUpdateRVO`, `hasMultiLevel`, `height`, `radius`, `rvoConcernValue`, `size`, and `gameplayLockViewConfig` maps).
- `GameplayConfigSubGameInstanceDataTable.json`: one-member MemoryPack root now parses exactly as four keyed six-member value records exposing key/source ids, failure/success text ids, short hashes, default group, quit-button text id, and fixed marker-byte gaps that are still unnamed.
- `GameplayConfigWorldEntityRegistry.json`: four-member MemoryPack root now parses exactly as two empty fields, 893 brief entity rows with nullable `detailId`, `entityType`, position, and rotation, plus four config property rows exposing `position`/`rotation` type-11 value arrays with signed `valueBit64` previews.
- `GameplayConfigMissionAreaTable.json`: one-member MemoryPack root now parses exactly as 73 keyed eight-member mission-area records with duplicate ids, observed flag/type bytes, primary/secondary vec3 float groups, size float values, and variable opaque tail blocks.
- `GPUISystemConfig/damage_text.json`: five-member MemoryPack root now parses exactly as 20 damage-text rows exposing the charset, 22 animation refs, 143 six-member UI node metadata records, node resource/path strings, and bounded opaque layout/keyframe tails.
- `Interactive/InteractiveTable.json`: one 2-member MemoryPack table beginning with `02`; the Data index now parses `coreTemplatePathDict` as 271 string-to-path entries, parses `interactiveDataDict` as 917 one-member template refs, verifies all 271 referenced template targets against the core template keys, and consumes the file exactly.
- `Interactive/InteractiveData/*.json`: 25-member inherited `InteractiveTemplateData` blobs now parse the root prefix (`name`, `factionIndex`, `objectType`, `bornTag`, and `componentList` count), the root/model/base-controller component prefix, optional zero-member `Core_SimpleAnimatorComponentData`, the first nonzero `BaseComponentData` payload tag, and a bounded component-list walk that continues through exact zero-member, TriggerObserver, one-property-map, CommonPerform, LogicController, Hittable, Audio, and ShowGuide payloads until the first unsupported mixed component. `Core_TriggerObserverComponentData` exposes a three-field property-map body with stable counts such as `[12, 0, 0]`, typed key/value previews for shape/radius/center/size and direction flags; 131 TriggerObserver component bodies are decoded across the 271 templates. Another 262 component bodies parse as one-member property maps, including newly exposed unnamed `0x0026` and `0x00eb` tags. The shared property-value grammar handles numeric tails plus string-tail value types `7` and `8`, exposing perform ids, effect ids, system ids, and related strings. `Core_InteractiveCommonPerformComponentData` parses as a dynamic property map plus counted `propertyDataList` rows and a final `syncGameplayLock` byte: 75 bodies decode, with row type counts `Bool:70`, `Int:21`, `Trigger:19`, and `Float:11`, and top names such as `LockedByGameplayLock`, `IsHit`, `state`, `Progress`, and `InTriggerVolume`. Parsed one-map families include `Core_PlayerInteractPerformComponentData`, `Core_KeepRelativeOffsetComponentData`, `Core_FactoryBuildingWrapperComponentData`, `Core_InteractCommonTwoStateComponentData`, `Core_InteractiveCommonMultiStateComponentData`, `Core_InteractiveWaterSwitchComponentData`, `Core_WaterProgressDriveCurveMovementComponentData`, `Core_WaterVolHeightMarkerComponentData`, `InteractiveStainComponentData`, `Core_HeightZeroMarkerComponentData`, `Core_InteractiveRunePointComponentData`, `Core_InteractiveManualMovePlatformComponentData`, `CraneContainerComponentData`, `Core_CanSetVisibleComponentData`, `ScannableTraceComponentData`, electric/navmesh/infrared/steam-blocker families, and additional still-unnamed all-pass union tags. `Core_InteractiveLogicControllerComponentData` parses exactly as a two-member body (`logicType` int plus a shared property map) for all 44 observed component bodies. `Core_InteractiveAudioData` parses exactly as a two-member body with an empty prefix count plus 13-member `InteractiveAudioComponentData` containing audio state/event rows, custom audio rows, and boolean audio/stencil flags for all 68 observed component bodies. `Core_ShowGuideComponentData` and `Core_ShowGuideWithConditionComponentData` parse as a property map followed by `Vector3 center`, `float radius`, one-byte `shape`, and `Vector3 size` for all 25 observed bodies. `Core_HittableComponentForIntData` parses as a 16-entry property map, fixed 80-byte `ColliderShapeData` blob, and trailing `enableExtraCheck` flag for all 14 observed component bodies. Mixed multi-member bodies such as click trigger, trigger zone, ability-system, dynamic-AI-nav, attack/step-on trigger, and a few named one-off components remain stop points with bounded string previews.
- `Interactive/ModelViewStateControllerData/`: 7-member MemoryPack blobs beginning with `07`; the Data index now parses camera signal hashes, clip asset hash/name records, effect ids, emissive config hashes, model animator data counts, and verifies the tail `modelId` filename stem plus final `preTickAnimator` boolean for all 399 files while leaving the nested animator graph body opaque except for string previews.
- `LipSync/`: many blobs beginning with `0F ...`.
- `SkillData/`: 45-member MemoryPack-like blobs beginning with `2D`; the Data index verifies the filename-stem id string for every row, reports exact id marker counts/offsets, and exposes cached IL2CPP setter parameter types for the top-level schema: 30 primitive/enum/string/vector-like fields and 15 complex/list fields. For 2,025 strict unique-id rows it parses a post-`skillId` tail prefix through `smartTargetTagQuery`, exposing `skillName`, raw `skillSpecification`, `skillTags` count/branch and clean tag-path samples, raw `smartTargetBuffFindSettings`, `smartTargetBuffIds` count, raw `smartTargetSelectStrategy`, and raw `smartTargetTagQuery`; 53 repeated-id rows remain ambiguous and five dirty/wrapped post-id rows are rejected instead of treated as decoded text. A schema-backed `switchToBuffConfig` marker probe uses local IL2CPP MemoryPack setter evidence to locate the following five-member switch config for all 2,025 strict rows and reports `asSkillCast`, `buffsCount`, and pre-switch residuals. For the default 148-byte switch-config branch, 1,948 rows now parse exactly through the file end, exposing `switchToCenterBeforeCast`, `tagDuringAttach`, `toggleBuffsCount`, `uiRangeHintsCount`, and exact `UIRangeHintData`/`SkillHintShapeData` items where toggle buffs are empty; 76 rows stop cleanly at non-empty `toggleBuffsCount`, and one non-default switch body remains marker-only. `ActionGroupData`, cast/buff/blackboard bodies, non-default `TargetSettings`/`SequenceActionData` switch bodies, non-empty toggle lists, and most target-query semantics remain structurally opaque.
- `NavMesh/*/LunaArea.json`: four one-member MemoryPack tables now parse as polygon area rows with row member count 6, area ids, center pairs, variable vec3 vertex lists, and two observed tail fields; all four files consume exactly.
- `NavMesh/*/NavMeshStateContainer.json`: all six six-member MemoryPack roots now parse exactly; simple containers use observed `bounds36`, `ints16`, and `ints20` row layouts, while `map01` and `map02` additionally use grouped u64-id lists plus id-to-small-value-list rows.
- `NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json`: two-member MemoryPack root now parses exactly as one root float list plus one section containing 10 hash-key rows, 12 nested point records, and final row floats; field names remain observed-only.
- `NonGeneratedConfigs/BambooRaftTaskTable.json`: one-member MemoryPack root now parses exactly as seven hash-key rows with duplicated task-id refs, value/task member-count markers of 2, observed `field0U32`, per-task `tailU32`, and zero row tails.
- `NPC/MontageJson/...`: one text `hashMapPath.Json` plus 3,400 3-member MemoryPack blobs beginning with `03`; the Data index now parses numeric `animType`, verifies nested data member count `22`, parses the exact tail GameplayTag hash/string for all binary files, and previews tag category/form/body/role/action plus extra strings while leaving the nested montage body opaque.
- `SpawnerConfig/`: 5-member MemoryPack blobs beginning with `05`; the Data index now verifies the filename-stem `configId` for all 413 files, parses all `enemyLibrary` item rows for counts and first-enemy previews, and still previews wave/route/settings strings until those nested structures are mapped.

These are not safe to feed to `response.json()` in the browser. The WebUI Data
tab treats unresolved files as `binary-json`; decoded MemoryPack families are shown as `memorypack-json` with recovered summaries and samples.

## Other Data Folders

The current `export_full/structured/StreamingAssets/Data` root still contains
raw installed-game Data families outside `Json/`, while Persistent contributes
additional decoded `Json/` config files. The WebUI Data tab no longer indexes
raw package/media/container folders.

- `Bundles/`: `.ab` asset bundle payloads and `manifest.hgmmap` are raw package
  metadata/container files, not final decoded Data page records.
- `Audio/`: `.pck` Wwise bank/stream packages remain packed audio inputs. The
  decoded-audio workflow writes final media under `export_full/structured/Audio/`.
- `Streaming/`, `DynamicStreaming/`, and `IrradianceVolume/`: dense world and
  lighting payloads remain raw binary inputs unless a schema-specific decoder is
  promoted into maintained tooling.
- `ExtendData/`: binary index payloads remain outside the Data page.
- `Video/`: MP4 media is excluded from the Data tab; media browsing belongs on
  the Assets/Story paths.

Generated WebUI indexes are local-only under `webui/data/game_data/` and are
ignored by git. The Data tab splits decoded JSON rows by directory and does not
copy raw Data files or package/media containers.

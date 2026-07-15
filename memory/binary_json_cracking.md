# Binary JSON Cracking Notes

Durable investigation notes for `export_full_1d3d2/structured/StreamingAssets/Data`.
The files named `.json` are mixed: some are real text JSON, but most are binary
game configuration blobs.

## 2026-06-27 Current Census

Scanned `StreamingAssets/Data/Json` after the move to `export_full_1d3d2`.

- Files: `81,735`
- Parseable text JSON by signature: `3,025`
- Binary `.json` payloads: `78,710`
- Top binary families:
  - `LipSync`: `64,812`, first byte always `0x0f`
  - `LevelScriptData`: `3,658`, first byte always `0x1a`
  - `NPC`: `3,400` binary rows under the mixed `NPC` tree, first byte `0x03`
  - `BuffData`: `2,291`, first byte always `0x1d`
  - `SkillData`: `2,083`, first byte always `0x2d`
  - `LevelData`: `783`, first byte always `0x2a`

Working interpretation: the first byte is usually a MemoryPack object/member
header. The common values line up as member counts: `0x0f = 15`,
`0x1a = 26`, `0x1d = 29`, `0x2a = 42`, `0x2d = 45`.

## Method Trail

1. **Signature and family census**
   - Confirmed the bulk of `.json` files are not UTF-8/UTF-16 JSON.
   - The strongest binary signatures are stable by top-level folder, which
     means family-specific parsers should cover most files.

2. **MemoryPack format check**
   - Checked Cysharp MemoryPack upstream source/docs:
     <https://github.com/Cysharp/MemoryPack>
   - The local byte patterns match MemoryPack-style object headers and
     4-byte collection/string lengths. This explains headers such as
     `1a 02 03 ...` for `LevelScriptData` and `0f <u32 count> ...` for
     `LipSync`.

3. **Existing repo evidence**
   - `scripts/story_builder/levelscript_binary.py` already decodes stable
     LevelScriptData facts.
   - The consolidated `memory/game_story_recovery.md` note records
     direct GameAssembly evidence that
     `Beyond_Gameplay_LevelScriptDataForMemoryPack.Deserialize` has
     `memberCount=26` with field order:
     `actionMap, activeShapeList, allowStartOnTravelPole, allowTick, endType,
     enemies, exitBuffer, exitBufferOverride, interactiveLocks, interactives,
     levelScriptType, lstTemplatePath, maxStage, modules, npcs,
     parentLevelScriptId, properties, propertyIdToKeyMap, refWorldEntityIdList,
     resetModeWhenActive, resetModeWhenEnd, scriptId, startShapeList,
     startType, taskMap, triggerVolumes`.
   - This is enough to parse/preview LevelScript top-level actionMap status,
     script id verification, startType, shape lists, taskMap status, and
     triggerVolumes for numeric script-id files.

4. **Local schema metadata attempt**
   - `tools/DummyDll/MemoryPack.Beyond.dll` exists but normal reflection fails
     with duplicate type names in the dumped assembly.
   - Added a disposable `scratch/metadata_probe` .NET metadata-reader probe.
     It can list type definitions without loading the invalid assembly.
   - It confirms many `*ForMemoryPack` type names survived, especially action
     and interactive types, but broad Buff/Skill field order is not available
     from the simple type table alone.

5. **LipSync structure probe**
   - Sample files:
     `Json/LipSync/Chinese/au_dlg_c13m1_10_002.json` and
     `Json/LipSync/Chinese/au_dlg_c13m1_1_001.json`.
   - Confirmed structure:
     - byte `0`: object member count `15`
     - members `1..15`: nullable MemoryPack collections
     - present collection layout: `<u32 item_count>` followed by repeated
       records, each record as `<u32 dimension>` plus `dimension` little-endian
       `float32` values
     - observed dimension is consistently `6`
     - null collection marker is `0xffffffff`
   - Example first file has collection counts:
     `52, 8, null, null, null, null, null, null, 64, 45, 22, null, 17, 25, 46`
     and consumes the file exactly.

## Current Plan

1. Promote the stable LevelScript and LipSync partial decoders into a shared
   binary-preview helper for the Data index/WebUI.
2. Keep BuffData/SkillData/LevelData as MemoryPack-identified but not
   field-decoded until setter order or a reliable schema source is recovered.
3. Probe `.bytes` outside Json next. The current index detects FlatBuffer-like
   `.bytes`, but we need a census of which roots are real FlatBuffers versus
   custom binary/irradiance payloads.
4. If schema recovery remains blocked, improve preview value by exposing
   format, member count, collection counts, string samples, and verified
   family-specific facts rather than guessing field names.

## 2026-06-27 Other Data Files

Scanned non-JSON files under `StreamingAssets/Data`.

- `.bytes`: `38,824`
  - `38,561` validate as FlatBuffer-like roots:
    - `Streaming/PC`: `36,788`
    - `DynamicStreaming/PC`: `1,773`
  - `263` are not FlatBuffers and belong to `IrradianceVolume/PC`:
    - `184` volume payloads such as `iv_0_0.bytes`
    - `72` `index.bytes`
    - `7` `regionIv_*.bytes`
- `.ab`: `258,422`, all classified as encoded asset-bundle payloads with
  non-`UnityFS` headers in the exported form.
- `.mp4`: `464`, normal MP4 files with `ftyp` brands.
- `.pck`: `16`, Wwise PCK containers (`banks`, `stream`, and main/default).
- `.bin`: `3`, binary indexes under `ExtendData`.
- `.hgmmap`: `1`, bundle manifest payload.

Current implication:

- The Data index's FlatBuffer detector is reliable for the streaming `.bytes`
  roots, but without `.fbs` schemas it should expose root offset, object length,
  and field count rather than inventing field names.
- `IrradianceVolume/PC` needs a separate custom parser; its headers do not
  match FlatBuffers.
- Encoded `.ab` and `.hgmmap` are container/index payloads, not the next best
  parser target for WebUI display. They are better treated as downloadable raw
  files unless the asset decoder is promoted into the Data page later.

## 2026-06-27 IL2CPP Field Order Recovery

Public schema search for Endfield MemoryPack wrappers did not find usable
`BuffData`, `SkillData`, or `LevelData` source definitions. The useful source
was the installed client metadata:

- `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat`
- `D:\Program Files\Endfield Game\GameAssembly.dll`

Method:

1. Reused `tools/endfield-il2cpp/catalog_option_flow_metadata.py` as a
   metadata parser instead of loading the invalid dumped
   `MemoryPack.Beyond.dll`.
2. Queried concrete `*ForMemoryPack` wrapper types and listed generated setter
   methods in metadata order.
3. Validated the method by comparing
   `Beyond_Gameplay_LevelScriptDataForMemoryPack` setter order against the
   already proven `LevelScriptData` order from GameAssembly body probes.
4. Promoted only field-name schemas where the top-level MemoryPack member
   count matches the byte header seen in the exported files.

Recovered top-level field order now integrated into the Data index:

- `BuffData`: 29 fields.
- `SkillData`: 45 fields.
- `LevelData`: 42 fields.
- `LevelScriptData`: 26 fields, plus the existing stable binary summary.
- `LipSync`: 15 fields named `A`, `E`, `EyebrowRaise`, `EyePitch`,
  `EyeYaw`, `HeadPitch`, `HeadRoll`, `HeadYaw`, `Height`, `I`, `O`,
  `Squint`, `U`, `WidthClose`, and `WidthOpen`, with exact collection record
  decoding.
- `AnimationConfig`, `CharInteractPerformCfgs`, `LevelConfig`,
  `LevelScriptTemplateData`, `NPCMontageJson`, `SpawnerConfig`,
  `InteractiveTable`, and `ModelViewStateControllerData`.

Still unresolved:

- At this point, most recovered schemas expose field names and high-level
  shape, not nested typed values. The next parser improvement is a generic
  MemoryPack value walker for strings, primitive arrays, maps, and nested
  object headers.
- `Json/Interactive/InteractiveData/*.json` was still unresolved at this stage;
  see the follow-up below for the later `InteractiveTemplateData` identification.

## 2026-06-27 InteractiveTemplateData Follow-up

The previously unresolved `Json/Interactive/InteractiveData/*.json` files are
now identified as inherited `InteractiveTemplateData` MemoryPack payloads, not
as a standalone `InteractiveDataForMemoryPack` wrapper.

Evidence and method:

1. Byte-prefix probing on files such as
   `data_int_001_comm_terminal.json` showed:
   - object header `0x19` / 25 members;
   - first field: UTF-8 string `int_001_comm_terminal`;
   - second field: 32-bit faction/index value;
   - third field: UTF-8 object/template id;
   - fourth field: a MemoryPack collection of 2-member gameplay-tag rows,
     e.g. `Invisible` and `Category/Interactive/Monitor`;
   - next field: a component-list count.
2. IL2CPP metadata shows `MemoryPackDeSerializerRegister` registers the
   template-data family, including `BaseTemplateData`, `EntityTemplateData`,
   and `InteractiveTemplateData`.
3. The 25-member count matches inherited serialized fields with non-serialized
   caches omitted:
   - `BaseTemplateData`: `name`, `factionIndex`.
   - `SimpleEntityTemplateData`: `objectType` backing field.
   - `EntityTemplateData`: `bornTag`, `componentList`, recycle/fade/send-event
     fields, excluding `m_componentDataCache`.
   - `InteractiveTemplateData`: interactive config/property/map fields,
     excluding runtime-only `m_runtimeConfig`.
4. The `InteractiveDataBaseForMemoryPack` union formatter was extracted from
   `GameAssembly.dll` using the current
   `tools/endfield-il2cpp/map_body_targets_to_gameassembly.py` default
   CodeRegistration `0x18c439740`. Its nested union tags are:
   `0=GameEventsUpdateConfig`, `1=InteractivePropertyData`,
   `2=LevelEntityConfig`, `3=NoUseConfig`, `4=SystemStateConfig`,
   `5=SystemUnlockConfig`, and `6=TargetEntityConfig`. This explains nested
   config/value records inside component/property fields, but it is not the
   top-level file wrapper.

Integrated Data-index behavior:

- `Json/Interactive/InteractiveData/*.json` now reports subtype
  `InteractiveTemplateData` with 25 field names.
- The WebUI shard decodes a stable prefix: `name`, `factionIndex`,
  `objectType`, `bornTag` rows, and `componentList` count.
- Example summary for `data_int_001_comm_terminal.json`:
  `name=int_001_comm_terminal; factionIndex=4; objectType=int_001_comm_terminal;
  bornTags=2; components=5; category=Category/Interactive/Monitor`.

Next parser target:

- Decode `componentList` entries by extracting the relevant component-data
  union formatter tables from `GameAssembly.dll`, then add a bounded generic
  MemoryPack walker for nested strings, primitive fields, maps, and arrays.

## 2026-06-27 ComponentList Union Follow-up

The `InteractiveTemplateData.componentList` field now has a conservative first
component preview in the Data index.

Evidence and method:

1. Official MemoryPack source/docs were used for external framing context around
   collection and union headers. The local checkout does not currently contain
   MemoryPack formatter source for these generated union readers.
2. Byte probing immediately after the decoded `InteractiveTemplateData` prefix
   showed all 271 `Json/Interactive/InteractiveData/*.json` files start their
   first component with tag byte `0x73`.
3. The `BaseComponentDataForMemoryPack` union formatter table was extracted
   from `GameAssembly.dll` with the current CodeRegistration `0x18c439740`.
   The table contains 272 continuous tags, `0x0000..0x010f`; tag `0x0073` maps
   to `Core_InteractiveRootComponentData`.
4. IL2CPP setter metadata for `RootComponentDataForMemoryPack` shows inherited
   fields such as `extraMountPointBundles`, `modelParts`, `mountPointData`,
   `needToSnapMountPoints`, `snapMountPointToSurface`, and `subGameObjects`.
   `InteractiveRootComponentDataForMemoryPack` does not expose additional own
   setters in the recovered metadata.

Integrated Data-index behavior:

- `Json/Interactive/InteractiveData/*.json` now reports
  `componentListFirstTag`, `componentListFirstType`, a union-source note, and a
  bounded `componentStringSamples` preview from the first component payload.
- Example served by the running WebUI shard for
  `data_int_001_comm_terminal.json`:
  `firstComponent=Core_InteractiveRootComponentData; componentStrings=int_001_comm_terminal_postmodel,shape,radius`.

Still unresolved:

- The parser does not yet skip or decode full component payloads. The next pass
  should implement a typed MemoryPack walker for `RootComponentDataForMemoryPack`
  fields, then iterate the remaining component union tags.

## 2026-06-27 FlatBuffer `.bytes` Preview Follow-up

The non-JSON `Streaming/` and `DynamicStreaming/` `.bytes` files now have a
schema-less FlatBuffer preview in the Data index.

Evidence and method:

1. Used the official FlatBuffers internals documentation for table layout
   context: root `uoffset_t`, signed vtable offset, vtable field offsets,
   vectors, and UTF-8 string targets.
2. Searched the local checkout for `.fbs`, generated FlatBuffer readers,
   `InitChunkData`, `fb_main`, and related names. No usable local schema was
   found, so field names are intentionally left as `field0`, `field1`, etc.
3. Probed representative files:
   - `Streaming/PC/base01_lv001/Streaming/InitChunkData_-1_-1_0_0.bytes`:
     root table at `24`, object length `40`, `8` present fields, root vector
     lengths such as `field3:135`, `field4:135`, and embedded object strings
     including `Env_qianneng#0_611883B` and `New Game Object#0_3B09708`.
   - `DynamicStreaming/PC/Extra/SpaceshipCabins/GrowCabin/fb_main_4_0003_0003.bytes`:
     root table at `24`, object length `32`, `5` present fields, plus short
     embedded string samples.
4. Integrated a bounded parser in `scripts/build_data_index.py` that validates
   the root table/vtable, exposes present field numbers, reports positive root
   vector lengths, and recursively samples proven UTF-8 FlatBuffer strings to a
   shallow depth. It does not guess semantic names without an `.fbs` schema.
5. Regenerated the WebUI Data shards with
   `python scripts\build_data_index.py --groups Streaming DynamicStreaming`.
   Note: this script's `--groups` option uses `nargs="*"`; repeated `--groups`
   flags preserve only the last occurrence, so multiple groups must be supplied
   after one flag.

Integrated Data-index behavior:

- `Streaming` entries now report field keys, largest positive root vector length
  as the row count, and embedded object-name samples.
- `DynamicStreaming` entries report the same structural facts where present;
  entries with only empty root vectors omit row count instead of showing `0`.
- The running WebUI server served the regenerated `Streaming.json` and
  `DynamicStreaming.json` shards with the new summaries.

Adjusted next parser plan:

1. Try to recover or infer `.fbs` schemas from installed client metadata or
   generated code names; only then promote semantic FlatBuffer field names.
2. If no schema evidence appears, move to the remaining custom non-JSON formats:
   `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.
3. For binary `.json`, continue replacing top-level MemoryPack field names with
   typed nested walkers only where IL2CPP metadata or byte-level validation
   proves the shape.

## 2026-06-27 BuffData Preview Follow-up

`Json/BuffData/*.json` now has a conservative value preview in the Data index.

Evidence and method:

1. Rechecked the official MemoryPack README/spec. The relevant constraints are:
   object payloads start with a one-byte member count, collections use a
   4-byte count, unions have tag bytes, and MemoryPack is not self-described;
   exact values require the matching C# schema.
2. Queried local IL2CPP metadata through
   `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. It confirms:
   - runtime `Beyond.Gameplay.Core.BuffData` has an `id` field plus many runtime
     config fields;
   - `Beyond_Gameplay_Core_BuffDataForMemoryPack` exposes generated setters in
     the 29-member serialized order used by the current WebUI schema.
   Many field type indexes remain unresolved by the lightweight metadata parser,
   so this pass does not claim full typed field decoding.
3. Probed all 2,291 `Json/BuffData/*.json` files. Every file starts with member
   count byte `0x1d` / `29`, and every file contains its filename stem as a
   length-prefixed UTF-8 string somewhere in the payload. That gives a strong
   validation gate for the `id` preview.
4. Added a bounded BuffData parser in `scripts/build_data_index.py`. It:
   - verifies member count `29`;
   - verifies `id` by matching the path stem against length-prefixed strings;
   - reports the total count of sampled length-prefixed strings;
   - buckets string samples into tags (`Status/...`, `Skill/...`, etc.),
     parameter-like names (`move_speed`, `dmg_hp_ratio`, etc.), and references
     (`buff_*`, `P_*`, `au_*`, `icon_*`).
5. Regenerated JSON Data shards with `python scripts\build_data_index.py --groups Json`.
   The generated `Json_BuffData.json` shard has 2,291 entries and all 2,291 have
   `idString=verified`. The running WebUI server served the regenerated shard.

Examples now exposed in the WebUI shard:

- `buff_abilityentity_interact_firewall_10m`: `idString=verified`, params
  `length,dmg_hp_ratio,tar`, refs `au_int_fire_wall_hit`,
  `P_interactive_firewall10m_01`, `au_int_fire_wall_start`.
- `buff_abilityentity_interact_mud_carpet_target`: tag `Status/Unjumpable`,
  params `move_speed,damage`, ref `P_common_poisoned_01_hit_asset`.
- `buff_chr_0030_zhuangfy_sword_triggerd_ult`: tags include
  `Skill/Character/chr_0030_zhuangfy/SwordTar` and
  `TimeDilation/Priority/HitStop`, params include `atk_scale`, `swordIndex`,
  `poise`, `atb_return`, and `swordCnt`.

Still unresolved:

- The parser does not yet assign those strings to exact BuffData fields such as
  `blackboard`, `applyTags`, or event-action lists. The next useful step is to
  recover nested BuffData field type names or generated deserialize body order
  for the complex fields, then replace the string buckets with typed field
  readers.

## 2026-06-27 SkillData Preview Follow-up

`Json/SkillData/*.json` now has the same kind of conservative value preview as
BuffData.

Evidence and method:

1. Rechecked the official MemoryPack source/docs again: the format relies on
   generated serializers and is not self-describing enough to assign all typed
   values without matching C# schema/body evidence.
2. Queried local IL2CPP metadata through
   `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. It confirms:
   - runtime `Beyond.Gameplay.Core.SkillData` has `skillId`, `skillName`,
     icon/cast/range/tag/action/buff/blackboard fields, plus a static
     `DEFAULT_DUMMY_POSITION_OFFSET` field that is not serialized;
   - `Beyond_Gameplay_Core_SkillDataForMemoryPack` exposes generated setters
     for the 45 serialized members used by the current WebUI schema.
   As with BuffData, many field type indexes remain unresolved by the
   lightweight metadata parser, so this pass does not claim full typed field
   decoding.
3. Probed all 2,083 `Json/SkillData/*.json` files. Every file starts with
   member count byte `0x2d` / `45`, and every file contains its filename stem as
   an exact length-prefixed UTF-8 string somewhere in the payload. Large files
   can place that id after an early sample window, so id verification now scans
   for the exact `<u32 length><utf8 stem>` marker separately from bounded string
   sampling.
4. Added a bounded SkillData parser in `scripts/build_data_index.py`. It:
   - verifies member count `45`;
   - verifies `skillId`/id by matching the path stem as a length-prefixed string;
   - reports the count of sampled length-prefixed strings;
   - buckets string samples into tags, parameter-like names, references, and
     asset paths.
5. Regenerated JSON Data shards with `python scripts\build_data_index.py --groups Json`.
   The generated `Json_SkillData.json` shard has 2,083 entries and all 2,083 have
   `idString=verified`. The running WebUI server served the regenerated shard.

Examples now exposed in the WebUI shard:

- `abilityentity_interact_bomb_passive`: ref
  `buff_abilityentity_interact_bomb_passive`.
- `chr_0002_endminm_attack1`: tag `TimeDilation/Priority/HitStop`, params
  `Attack01`, `BattleStepL`, `tar`, `atk_scale`, `atb`, and
  `char_normal_attack`, plus effect/audio refs.
- `chr_0028_wulfa_ultimate_skill`: tags include
  `TimeDilation/Layer/Entity/HitStop`, `TimeDilation/Priority/HitStop`, and
  `Immune/Damage`; params include `UltimateSkill`, `smart_target`, `maintar`,
  and `mainchar`; refs include related Wulfa buffs and effects.

Still unresolved:

- The parser does not yet assign strings to exact SkillData fields such as
  `skillTags`, `actionGroupData`, `buffs`, `blackboard`, or `uiRangeHints`.
  The next useful SkillData step is to recover nested field type names or
  deserialize body order for those complex fields.

## 2026-06-27 LevelData Preview Follow-up

`Json/LevelData/<scene>/*.json` now has a conservative MemoryPack preview in
the Data index.

Evidence and method:

1. Rechecked the official MemoryPack source/docs for the same constraint used in
   the BuffData and SkillData passes: object payloads carry member counts, but
   exact typed decoding still depends on generated serializers and matching C#
   schema/body evidence.
2. Queried local IL2CPP metadata through
   `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. Runtime
   `Beyond.Gameplay.LevelData` has 62 fields including lookup/static/runtime
   caches, while `Beyond_Gameplay_LevelDataForMemoryPack` exposes generated
   setters for 42 serialized members. Those 42 names match the current WebUI
   `LevelData` schema order.
3. Probed all 783 files under `Json/LevelData/`. Every file starts with member
   count byte `0x2a` / `42`. Unlike BuffData and SkillData, the filename stem is
   not embedded as a stable id string. The parent scene folder, such as
   `base01_dg001` or `map02_lv002`, is embedded as an exact length-prefixed
   UTF-8 marker in all 783 files, so that is now the validation gate.
4. Added a bounded LevelData parser in `scripts/build_data_index.py`. It:
   - verifies member count `42`;
   - verifies `sceneId` by matching the parent scene folder as a
     length-prefixed string;
   - reports the count of sampled length-prefixed strings;
   - buckets string samples into level script refs (`sc_*`), task/logic markers
     (`Task*`, `FinishObj_*`, `lt:*`, `guide_*`), parameter-like names, scene
     refs, and asset paths.
5. Regenerated JSON Data shards with `python scripts\build_data_index.py --groups Json`.
   The generated index now has 141 `Json/LevelData/...` groups, 783 LevelData
   entries, and all 783 have `sceneId=verified`. The running WebUI server served
   `groups/Json_LevelData_base01_dg001.json` with the new summaries.

Examples now exposed in the WebUI shard:

- `base01_dg001_lv_data.json`: `sceneId=base01_dg001`, params include
  `int_empty`, `dont_log_error`, `companionPosList`, `roomCenter`, and
  `lookatTarget`, with refs to base location-tip scenes.
- `base01_dg001_lv_data_sub_battle.json`: level script refs include
  `sc_base01_dg001_9900010016`, `sc_base01_dg001_9900010023`,
  `sc_base01_dg001_9900010017`, and `sc_base01_dg001_9900010024`; params include
  `spawner`, `cameraScript`, `playerPos`, and `partnerPos`.
- `base01_dg001_lv_data_sub_task.json`: task markers include `TaskFailed`,
  `TaskComplete`, `FinishObj_1`, and `FinishObj_2`.

Still unresolved:

- The parser does not yet assign nested lists and dictionaries to exact fields
  such as `levelScriptDataPathDict`, `interactives`, `enemies`, `spawners`, or
  `blackbox`. Those require nested formatter/body recovery rather than string
  scanning.
- The next useful LevelData step is to recover nested element type layouts from
  generated `ForMemoryPack` formatter metadata or GameAssembly deserialize body
  evidence, then replace selected string buckets with typed readers.

Adjusted next parser plan:

1. For LevelData, target one nested field with high story value first:
   `levelScriptDataPathDict` / `levelScriptBriefDataDict`, then spawners or
   interactives if the formatter/body evidence is clear.
2. Continue replacing top-level MemoryPack previews with typed nested walkers
   only where IL2CPP metadata and byte-level validation prove the shape.
3. For non-JSON formats, continue schema/evidence searches for FlatBuffer
   `.bytes`; if no `.fbs` evidence appears, move to focused probes for
   `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 SpawnerConfig Preview Follow-up

`Json/SpawnerConfig/<level>/*.json` now has a verified MemoryPack preview in
the Data index.

Evidence and method:

1. Rechecked official MemoryPack source/docs again for the same format
   constraints used in the previous passes: object payloads start with member
   counts, collection counts are explicit, but exact nested values still require
   generated serializer/schema evidence.
2. Queried local IL2CPP metadata through
   `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. Runtime
   `Beyond.Gameplay.SpawnerConfigData` has six fields, with `m_enemyLibraryDict`
   as a runtime lookup cache. The generated
   `Beyond_Gameplay_SpawnerConfigDataForMemoryPack` exposes five serialized
   setters in this order: `configId`, `enemyLibrary`, `routeMap`, `settings`,
   and `waveMap`. The related generated nested formatters identify useful next
   targets, including `SpawnerEnemyLibraryItem`, `SpawnerWaveData`,
   `SpawnerGroupData`, `SpawnerRouteData`, and `SpawnerSettings`.
3. Probed all 413 files under `Json/SpawnerConfig/`. Every file starts with
   member count byte `0x05`, and every file has its filename stem as the first
   MemoryPack string field. The next 4-byte value after that string is a sane
   `enemyLibrary` collection count for all files, ranging from 0 to 11.
4. Added a bounded SpawnerConfig parser in `scripts/build_data_index.py`. It:
   - verifies member count `5`;
   - reads and verifies the first `configId` string against the filename stem;
   - reads the top-level `enemyLibrary` collection count;
   - walks every `SpawnerEnemyLibraryItem` for all 413 files, including born
     buff lists, blackboard key/value pairs, `enemyId`, `enemyLevel`,
     `forceToBattle`, spawn key, override AI config, patrol gait, prewarn audio,
     16-byte fixed rotation, prewarn effect, and prewarn time;
   - still treats wave keys, params, route/settings strings, and other residual
     strings outside `enemyLibrary` as bounded previews until their nested
     formatter order is mapped.
5. Regenerated JSON Data shards with `python scripts\build_data_index.py --groups Json`.
   The generated index now has 76 `Json/SpawnerConfig/...` groups, 413 entries,
   and all 413 have both `idString=verified` and `enemyRows=parsed`. The running
   WebUI server served `groups/Json_SpawnerConfig_base01_dg001.json` with the
   enriched summaries.

Examples now exposed in the WebUI shard:

- `sc_base01_dg001_9900010011`: `enemyLibrary=2`, first exact enemy row is
  `eny_0018_lbtough_train` at level 20 with born buffs
  `buff_common_undeadable`, `buff_dung_maxhp`, and `buff_common_born`; one of
  the two enemy rows has `forceToBattle=true`, and wave keys include `w1` and
  `w2`.
- `sc_dung01_cdg016_31600000001`: `enemyLibrary=10`, enemies include
  bomb variants such as `eny_0025_agrange_bomb`, with speed/lockdown buffs and
  params such as `duration`, `multiplier_speed`, and `hp_ratio`.
- `sc_map02_lv001_10100600001`: `enemyLibrary=4`, settlement enemies include
  `eny_0055_hscrane_settlement`, `eny_0084_hshunt_settlement`, and related
  spawn audio/effect refs.

Still unresolved:

- The parser does not yet walk `waveMap`, `routeMap`, or `settings`. `waveMap`
  and `groupMap` likely require nested dictionary/list walkers and union-aware
  action parsing. Those should wait until the generated formatter order is
  mapped far enough to avoid false field assignment.
- The Data index currently stores compact row summaries only, so the exact
  parsed enemy-library item objects are used for counts and first-row previews;
  exposing full nested enemy rows would require extending the generated shard
  shape or adding a detail-sidecar format.

Adjusted next parser plan:

1. For SpawnerConfig, target exact `waveMap` / `groupMap` parsing next only
   after mapping `SpawnerWaveData` and `SpawnerGroupData` formatter order from
   IL2CPP and validating the remaining byte offset after `enemyLibrary`.
2. For LevelData, keep `levelScriptDataPathDict` / `levelScriptBriefDataDict` as
   the next high-value level-side nested target.
3. For the remaining generic MemoryPack families, prioritize large or
   cross-linking groups: `NPC/MontageJson`, `AtmosphericNpcData`, and
   `AnimationConfig`.
4. For non-JSON formats, continue schema/evidence searches for FlatBuffer
   `.bytes`; if no `.fbs` evidence appears, move to focused probes for
   `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 LevelConfig Preview Follow-up

`Json/LevelConfig/*.json` now has a verified MemoryPack preview in the Data
index.

Evidence and method:

1. Rechecked official MemoryPack source/docs again: object payloads carry member
   counts and generated serializers define field order, so byte-level validation
   is still required before assigning field names.
2. Queried local IL2CPP metadata through
   `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. Runtime
   `Beyond.Gameplay.LevelConfig` and generated
   `Beyond_Gameplay_LevelConfigForMemoryPack` agree on 15 serialized members,
   with a nested 3-member `LevelConfig_State` default-state object.
3. Compared `LevelConfig` against `NPC/MontageJson` as the next target.
   `NPC/MontageJson` has 3,400 binary files plus one large text hash map, but
   the payload quickly enters montage/union-heavy nested data. `LevelConfig` is
   smaller but gives stronger exact coverage for level IDs, map IDs, startup
   transforms, bounds, and LevelData linkage counts, so it was the safer parser
   target for this pass.
4. Probed all 141 files under `Json/LevelConfig/`. Every file starts with member
   count byte `0x0f` / `15`; the default-state nested object starts with member
   count `0x03`; every file contains its filename stem as the `id` string; and
   the last non-empty string leaves exactly 56 tail bytes.
5. Added a bounded LevelConfig parser in `scripts/build_data_index.py`. It:
   - parses `defaultState.exportedSceneConfigPath`, `name`, and
     `sourceSceneName`;
   - parses `dimensionSourceLevelId`, `id`, `idNum`, `isDimensionLevel`, and
     `isSeamless`;
   - reads the post-boolean `levelDataPaths` count, which matches the number of
     `Json/LevelData/<id>` files in observed cases;
   - treats the mixed payload before `mapId` as opaque for now, recording offset
     and byte length rather than assigning false nested fields;
   - parses the 56-byte tail as `mapId`, player init position, player init
     rotation, rect left-bottom/right-top, scope, and start position.
6. Regenerated JSON Data shards with `python scripts\build_data_index.py --groups Json`.
   The generated `Json_LevelConfig.json` shard has 141 entries, and all 141 have
   `idString=verified` plus exact numeric-tail parsing. The running WebUI server
   served `groups/Json_LevelConfig.json` with the new summaries.

Examples now exposed in the WebUI shard:

- `base01_dg001`: `idNum=99`, `mapId=base01_dg001`, `levelDataPaths=3`,
  `scope=8`, init position `(-100.0, 0.05, 135.0)`, rect
  `(-512.0,-512.0)-(512.0,512.0)`, default scene
  `base01_lv002/base01_lv002_art_streaming.asset`.
- `map02_lv002`: `idNum=228`, `mapId=map02`, `levelDataPaths=91`, `scope=1`,
  init position `(-778.6183, 289.83, -822.1053)`, rect
  `(-1664.0,-896.0)-(-512.0,384.0)`, default scene
  `map02/map02_streaming.asset`.
- `indie_dg002`: `idNum=87`, `mapId=indie_dg002`, `levelDataPaths=6`,
  `scope=1`, init position `(-370.3, 103.3, -94.836)`, rect
  `(-1024.0,-1024.0)-(1024.0,1024.0)`.

Still unresolved:

- The middle payload between the `levelDataPaths` count and `mapId` is not yet
  decoded. It likely contains `m_levelDataPaths` and/or `m_levelGrids` records,
  but the byte shape is not simple string-list encoding. It should be mapped
  against generated nested type evidence before field assignment.
- The exact enum names for `scope` are not recovered here; the Data index shows
  the numeric value.

Adjusted next parser plan:

1. For LevelConfig, compare the `levelDataPaths` count against generated
   `Json/LevelData/<id>` group counts and then map the opaque middle payload
   with stronger nested type evidence.
2. For SpawnerConfig, target exact `waveMap` / `groupMap` parsing only after
   mapping `SpawnerWaveData` and `SpawnerGroupData` formatter order from IL2CPP.
3. For the remaining generic MemoryPack families, prioritize
   `NPC/MontageJson`, `AtmosphericNpcData`, and `AnimationConfig`.
4. For non-JSON formats, continue schema/evidence searches for FlatBuffer
   `.bytes`; if no `.fbs` evidence appears, move to focused probes for
   `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 AtmosphericNpcData Preview Follow-up

`Json/AtmosphericNpcData/*.json` now has a verified table-level MemoryPack
preview in the Data index.

Evidence and method:

1. Rechecked official MemoryPack guidance/source again. The approach remains:
   trust the first member-count byte only as a framing clue, then validate field
   order and nested objects from generated IL2CPP formatter evidence plus byte
   offsets.
2. Compared `AnimationConfig` and `AtmosphericNpcData` as next parser targets.
   `AnimationConfig` has a clean 12-member root, but most useful values sit in
   nested montage/curve collections. `AtmosphericNpcData` starts with a simpler
   one-member root and exposes immediately useful NPC placement strings, so it
   was the safer next WebUI improvement.
3. Queried IL2CPP metadata. The root type is
   `Beyond.Gameplay.NpcAtmosphericDataTable` with a single `dataTable` member.
   Row payloads align with `LevelEntityData` / `LevelNpcData` metadata, but the
   serialized row object has a 109-member inherited payload. Only the root table
   and row boundary/preview fields are named for now.
4. Byte-probed all 134 files under `Json/AtmosphericNpcData/`. Empty files are
   exactly `01 00 00 00 00`: root member count 1 plus a zero-row table count.
   Non-empty files begin with `01 <u32 row count>`, then repeated
   length-prefixed row keys followed by row member count byte `0x6d` / 109.
5. Initial key detection that required `_atmospheric_` missed outliers with the
   misspelled `_enviromental_` marker and a few shorter/longer keys. The final
   boundary detector accepts plausible `npc_` keys containing `_atmospheric_`,
   `_enviromental_`, or `_environmental_`, with length up to 120 and a following
   `0x6d` row member marker. That matched all table counts: 134/134 files,
   7,692/7,692 rows.
6. Added a bounded `AtmosphericNpcData` decoder in
   `scripts/build_data_index.py`. It verifies root/table counts and row
   boundaries, then previews row ids, AI configs, montage paths, facial morph
   paths, envTalk ids, NPC template ids, cluster ids, and level ids. The full
   109-member row body remains marked opaque rather than assigning false field
   names.
7. Regenerated JSON Data shards with
   `python scripts\build_data_index.py --groups Json`. The generated
   `groups/Json_AtmosphericNpcData.json` shard has 134 entries and 7,692 total
   rows, and the running WebUI server served the shard with HTTP 200.

Examples now exposed in the WebUI shard:

- `NpcAtmosphericDataTableBase01_lv001`: 101 rows, first key
  `npc_gentleman_efstaff_a_05_base01_lv001_data_sub_npc_v1d0_atmospheric_001`,
  AI `aiconf_npc_normal`, montage samples including
  `Montage/NPC/Humanoid/CommonForm/Gentleman/VIP/Virtual/akimbo1`, and envTalk
  samples such as `envTalk_e0m2_1`.
- `NpcAtmosphericDataTableDung02_ssdg002`: 4 rows using the misspelled
  `_enviromental_` row-key marker; previews `aiconf_npc_bird_no_randomwalk`,
  `aiconf_npc_bird`, template `npc_obj_fowl_hs_01`, and level
  `dung02_ssdg002`.
- `NpcAtmosphericDataTableMap02`: 4,211 rows, first key
  `npc_boy_hsfarmer_a_02_map02_lv002_data_sub_npc_v1d0_atmospheric_001`, with
  AI `aiconf_npc_normal`, montage samples including `Montage/NPC/VirtualCrowd/sit`,
  and envTalk samples such as `envTalk_map02_lv002_env_33`.

Still unresolved:

- The 109-member row payload is not fully field-named. The current parser proves
  table boundaries and useful string previews; exact booleans, enums,
  transforms, and nested `LevelNpcData` members require mapping the inherited
  formatter chain beyond `LevelEntityData` / `LevelNpcData`.
- The compact Data shard stores row examples as summary/sample text, not nested
  row objects. Exposing full row samples would require a detail sidecar or a
  deliberate Data page payload expansion.

Adjusted next parser plan:

1. For `AtmosphericNpcData`, map the inherited 109-member row order far enough
   to parse base placement/transforms and the first `LevelNpcData` fields
   exactly.
2. For `AnimationConfig`, return to the 12-member root and recover safe string
   previews for controller paths, baked binding paths, montage paths, and curve
   collections.
3. For `NPC/MontageJson`, first parse only the 3-member root and union tags;
   delay full montage body parsing until formatter tag evidence is mapped.
4. For non-JSON files, continue schema/evidence searches for FlatBuffer
   `.bytes`; if no `.fbs` evidence appears, run focused probes for
   `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 AnimationConfig Preview Follow-up

`Json/AnimationConfig/*.json` now has a dedicated MemoryPack preview in the Data
index.

Evidence and method:

1. Compared the bytes against local IL2CPP metadata. The runtime type
   `Beyond.Gameplay.View.Animation.AnimationConfigJson` has 12 members, and the
   generated `AnimationConfigJsonForMemoryPack` setter order matches the WebUI
   schema order already recovered earlier: fallback montages, baked/controller
   paths, extra data, montage dictionaries, sync/time curves, and two trailing
   booleans.
2. Probed all 106 files under `Json/AnimationConfig/`. Every file starts with
   member count byte `0x0c` / 12. File sizes range from 52 bytes to 206,312
   bytes. Filename stems are not embedded as length-prefixed ids, so the parser
   does not claim id verification.
3. Verified the final two bytes as the boolean tail for all 106 files. Tail
   combinations are `00 00`, `01 01`, and `00 01`, matching the final
   `useRotateDirection` / `useStateVariables` fields from formatter order.
4. Added a bounded AnimationConfig decoder in `scripts/build_data_index.py`. It
   keeps the root field-name schema, verifies the 12-member header and boolean
   tail, and classifies embedded strings into animation state names, facial
   morph paths, montage paths, actor animation refs, cutscene refs, and other
   paths. It does not yet parse nested montage/curve collections exactly.
5. Regenerated JSON Data shards with
   `python scripts\build_data_index.py --groups Json`. The generated
   `groups/Json_AnimationConfig.json` shard has 106 `memorypack-json` entries,
   and the running WebUI server served it with HTTP 200.

Examples now exposed in the WebUI shard:

- `anim_cfg_abilityEntity_chr_0029_pograni_ultimate_skill`: 5 strings,
  states `AttackBL`, `AttackBR`, `AttackFL`, `AttackFR`, and `SoldierRush`,
  with both trailing booleans false.
- `anim_cfg_chr_0002_endminm`: large character config with state names such as
  `_EmotionBlend`, `Appear`, and `Attack01`, plus facial morph paths like
  `FacialMorph/MorphAnim/endminm_anim_battle_attack_01`.
- `anim_cfg_chr_0004_pelica`: previews state names, facial morph paths, and
  cutscene refs such as `cutscene_e1m1_2` / `e0m0_3_sc029`.

Still unresolved:

- The nested montage dictionaries, sync-group curves, time-reference curves, and
  extra-data union bodies are not parsed structurally. The current parser only
  provides safe root schema, string previews, and the verified boolean tail.
- The controller/baked binding path fields appear absent or hash-packed in many
  samples; no filename-stem id string is embedded, so id verification is not
  available for this family yet.

Adjusted next parser plan:

1. For `AnimationConfig`, map `AnimMontageDataForMemoryPack` and related curve
   collection formatters before assigning nested montage/curve fields.
2. For `AtmosphericNpcData`, map the inherited 109-member row order far enough
   to parse transforms and common `LevelNpcData` fields exactly.
3. For `NPC/MontageJson`, parse the 3-member root and union tags first, then
   defer the montage body until union tag evidence is complete.
4. For non-JSON files, continue the FlatBuffer/.bytes schema search and then
   run focused probes for `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 NPCMontageJson Root/Tag Preview Follow-up

`Json/NPC/MontageJson/**` now has a dedicated MemoryPack preview in the Data
index.

Evidence and method:

1. Checked official MemoryPack documentation/source for the object framing model:
   these blobs still need byte validation because generated formatter order and
   union-like nested bodies are not self-describing enough on their own.
2. Compared local IL2CPP metadata and generated formatter names. The runtime
   root type `Beyond.Montage.NPCMontageJson` exposes `tag`, `data`, and
   `animType`, while the generated wrapper setter order is `animType`, `data`,
   then `tag`. A nested `NPCMontageAnimForMemoryPack` formatter exists, but the
   22-member body is not parsed yet.
3. Probed all 3,401 files under `Json/NPC/MontageJson/`. One file is text JSON:
   `hashMapPath.Json`, an array map with 6,759 rows. The other 3,400 files are
   binary and start with root member count byte `0x03`.
4. Verified all binary files share the same root layout: `animType` is a 32-bit
   integer at offset 1, the nested data object starts with member count `22` at
   offset 5, and the tail is an exact GameplayTag object ending at EOF:
   member count `0x02`, a 32-bit hash, a 32-bit string length, then UTF-8 tag.
5. Added a bounded `NPCMontageJson` decoder in `scripts/build_data_index.py`.
   It exposes numeric `animType`, nested data member count, tag hash/string,
   tag category/form/body/role/action pieces, and extra embedded strings. It
   does not assign semantic names to the nested montage body fields yet.
6. Regenerated the JSON Data shards with
   `python scripts\build_data_index.py --groups Json`. The generated
   `groups/Json_NPC_MontageJson.json` shard has 3,401 entries: 3,400
   `memorypack-json` rows with subtype `NPCMontageJson` and one `text-json` row.
   The running WebUI server served the shard and the Data index with HTTP 200.

Observed counts:

- `animType`: `1` = 2,998 files, `3` = 298 files, `4` = 103 files, `0` = 1 file.
- Tail GameplayTag category: `Humanoid` = 3,196 files, `Generic` = 204 files.
- Tag depths are 5, 7, and 8 path segments.

Examples now exposed in the WebUI shard:

- `Json/NPC/MontageJson/MontageNew/Generic/agcanno/data_npc_montage_agcanno_idle.json`:
  `animType=1`, data member count `22`, tag
  `Montage/NPC/Generic/agcanno/idle`, category `Generic`, body `agcanno`, action
  `idle`.
- Humanoid crowd-state rows expose tags like
  `Montage/NPC/Humanoid/CommonForm/Boy/Crowd/afraid` and extra strings such as
  `A_actor_boy_dialog_state_afraid_loop`.
- `hashMapPath.Json` is normal text JSON and links 6,759 hash/path rows; it
  should be cross-checked against montage tags or clip hashes before assigning
  the binary hash fields.

Still unresolved:

- `animType` is still numeric. No enum names have been assigned safely yet.
- The nested 22-member `NPCMontageAnim` body remains opaque. Likely targets
  include clip async info, start/loop/end montage data, transition data, and
  related animation references, but those names require formatter or byte-order
  evidence before exposing them as fields.
- The tail tag hash algorithm is not identified; the parser only reads and
  displays the stored 32-bit value.

Adjusted next parser plan:

1. Map `NPCMontageAnimForMemoryPack`, `AnimMontageData`, and clip async-info
   bodies far enough to parse the 22-member nested data safely.
2. Cross-check `hashMapPath.Json` hash/path rows against tail tag hashes and
   embedded clip/hash strings.
3. Continue the `AtmosphericNpcData` 109-member row and `AnimationConfig` nested
   montage/curve body work.
4. For non-JSON files, keep searching for FlatBuffer schema evidence, then run
   focused probes for `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 ModelViewStateControllerData Preview Follow-up

`Json/Interactive/ModelViewStateControllerData/*.json` now has a dedicated
MemoryPack preview in the Data index.

Evidence and method:

1. Rechecked the official MemoryPack framing rule: member names are not written
   into the payload, so the recovered IL2CPP field order must be byte-validated
   before a WebUI parser can expose field values.
2. Used the existing recovered root schema for
   `ModelViewStateControllerData`: `cameraSignalSourceAssetHashes`,
   `clipAssetInfos`, `effectIds`, `emissiveConfigHashes`, `modelAnimatorDatas`,
   `modelId`, and `preTickAnimator`.
3. Probed all 399 files under
   `Json/Interactive/ModelViewStateControllerData/`. Every file starts with
   root member count `0x07` and parses through the first four fields exactly:
   camera signal hash list (`u64[]`), clip asset info list, effect id string
   list, and emissive config hash list (`u64[]`).
4. The `clipAssetInfos` field is a list of 2-member records shaped as
   `memberCount=2`, `u64 hash`, then a MemoryPack UTF-8 clip name string. This
   validated across all files.
5. After the first four fields, the next count is the `modelAnimatorDatas` item
   count. The nested animator graph body is variable and not structurally mapped
   yet, so the parser only records the count and scans bounded length-prefixed
   string previews from that body.
6. Every file ends with a MemoryPack UTF-8 string equal to the filename stem,
   followed by one final boolean byte. The parser treats these as exact
   `modelId` and `preTickAnimator` tail fields. The final boolean is false in
   392 files and true in 7 files.
7. Added a bounded `ModelViewStateControllerData` decoder in
   `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified that the
   running WebUI server serves both the Data index and
   `groups/Json_Interactive_ModelViewStateControllerData.json` with HTTP 200.

Observed counts:

- `clipAssetInfos`: 0 in 179 files, 4 in 83, 1 in 42, 2 in 29, 3 in 24, with
  the remaining files ranging up to 18.
- `effectIds`: 0 in 180 files, 2 in 74, 1 in 49, 3 in 39, with the remaining
  files ranging up to 11.
- `emissiveConfigHashes`: 0 in 352 files, 2 in 36, 3 in 8, 4 in 2, 1 in 1.
- `modelAnimatorDatas`: 1 in 350 files, 2 in 31, 3 in 9, 4 in 5, 0 in 2, 7 in
  1, and 6 in 1.

Examples now exposed in the WebUI shard:

- `dyn_anm_map02_door+1_007_01_postmodel`: 3 clip infos for close idle, open,
  and open idle; no effects; 1 animator-data body; `preTickAnimator=false`.
- `dyn_iprop_map02_light+1_003_09_postmodel`: no clip infos, one effect id
  `P_fxint_l_map02_lv006_sworddpt_switch_01`, 2 emissive hashes, and animator
  strings such as `Base`, `Idle`, `state`, and `On`.
- `dyn_lsm_controlled_big_sword_01`: 2 clip infos, one effect id,
  2 emissive hashes, and animator strings such as `MVSCAnimFsmGraph`,
  `Default`, `state`, and `Actived`.

Still unresolved:

- The nested `modelAnimatorDatas` graph body is not structurally decoded. The
  current parser only exposes its count and classified string samples.
- The clip and emissive hash algorithms/namespaces are not identified. Hashes
  are read as stored little-endian `u64` values.
- The exact semantics of the 7 `preTickAnimator=true` rows still need a content
  cross-check against runtime behavior or generated formatter evidence.

Adjusted next parser plan:

1. Map the nested `modelAnimatorDatas` body enough to expose animator layer,
   state, transition, clip, effect, and parameter records instead of only string
   samples.
2. Upgrade `CharInteractPerformCfgs` from schema-only preview to byte-validated
   root/tail/count previews; it is the next-largest schema-only MemoryPack
   family.
3. Continue `NPCMontageJson` nested 22-member body work and cross-check
   `hashMapPath.Json` against parsed clip/tag hashes.
4. For non-JSON files, keep searching for FlatBuffer schema evidence, then run
   focused probes for `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 CharInteractPerformCfgs Prefix Preview Follow-up

`Json/CharInteractPerformCfgs/*.json` now has a dedicated MemoryPack preview in
the Data index.

Evidence and method:

1. Rechecked the official MemoryPack collection/formatter source for the rule
   used here: collection fields write a count/header followed by item payloads,
   while object member names are not embedded. That means local field-order
   metadata still needs byte validation before exposing field values.
2. Used the recovered root field order for `CharInteractPerformCfgs`, which has
   26 members: `activeTags`, `allowInheritPerform`, `bodyTypeActDataDict`,
   `charPerformType`, `chars`, `decos`, `defaultSubPerformEntry`,
   `disableIKAndFollow`, `effects`, `endActions`, `fixedTime`,
   `forceExitCommandsContinuous`, `guardActiveTags`, `guardInterruptReasons`,
   `hideWeapon`, `inheritPerformIds`, `interactives`, `interruptReasons`,
   `loopActions`, `npcs`, `performType`, `preStartActions`, `startActions`,
   `subPerformEntries`, `tmpObjects`, and `usePreStartActions`.
3. Probed all 159 files under `Json/CharInteractPerformCfgs/`. Every file
   starts with root member count `0x1a` and validates through the first three
   fields:
   `activeTags` as a MemoryPack collection of GameplayTag records,
   `allowInheritPerform` as a boolean byte, then `bodyTypeActDataDict` as a
   dictionary count. The body itself is still opaque.
4. The active tag item shape matches the same GameplayTag pattern used elsewhere:
   `memberCount=2`, a stored 32-bit hash, then a MemoryPack UTF-8 tag string.
5. Added a bounded `CharInteractPerformCfgs` decoder in
   `scripts/build_data_index.py`. It exposes exact prefix fields and classifies
   body strings into status tags, montage refs, actors, effect ids, perform
   refs, asset refs, CCS refs, and state/parameter-like strings.
6. Regenerated with `python scripts\build_data_index.py --groups Json` and
   verified that the running WebUI server serves both the Data index and
   `groups/Json_CharInteractPerformCfgs.json` with HTTP 200.

Observed counts:

- `activeTags`: 0 in 76 files, 1 in 83 files.
- `allowInheritPerform`: false in 154 files, true in 5 files.
- `bodyTypeActDataDict`: count 1 in all 159 files.
- Top first status tags among parsed previews include
  `Status/InCommonInteractionCanMove`, `Status/InCommonInteraction`,
  `Status/InCommonInteractionCanCastSkill`, and `Status/AIPickUp`.

Examples now exposed in the WebUI shard:

- `CharIntPerform_Aglina_Spdash`: no active tags, one body-type action entry,
  effect refs such as `P_fxbat_aglina_sprint_dash_sp_01` and
  `P_fxbat_aglina_sprint_dash_sp_02`.
- `CharIntPerform_c28m3_Investigate`: one active tag
  `Status/InCommonInteraction`, montage refs for NPC humanoid think actions,
  actor refs such as `chr_0002_endminm`, `chr_0003_endminf`, and
  `chr_0016_laevat`, plus an LD/CCS ref.
- `CharIntPerform_Call`: no active tags, one body-type action entry, and status
  preview `Status/InCommonInteractionCanCastSkill`.

Still unresolved:

- The nested `bodyTypeActDataDict` value body is not structurally decoded. The
  current parser intentionally stops after its count and uses bounded string
  previews for the remaining body.
- Fields after `bodyTypeActDataDict` are not assigned exact offsets yet.
  Strings clearly correspond to effects, montages, actors, perform refs, CCS
  refs, and assets, but the parser does not yet know which nested action entry
  owns each string.
- No filename-stem id string appears consistently in this family, so the parser
  does not claim id verification.

Adjusted next parser plan:

1. Map the `bodyTypeActDataDict` entry/value layout far enough to assign
   `charPerformType`, action lists, `subPerformEntries`, character/NPC maps, and
   boolean tail fields structurally.
2. Continue the `ModelViewStateControllerData` nested `modelAnimatorDatas` graph
   work so animator layers/states/transitions are exposed as fields instead of
   only string previews.
3. Continue `NPCMontageJson` nested 22-member body work and cross-check
   `hashMapPath.Json` against parsed clip/tag hashes.
4. For non-JSON files, keep searching for FlatBuffer schema evidence, then run
   focused probes for `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 LevelScriptTemplateData Preview Follow-up

`Json/LevelScriptTemplateData/*.json` now has a dedicated MemoryPack preview in
the Data index.

Evidence and method:

1. Rechecked the official MemoryPack collection/formatter source while working
   on these files. The root field names are not serialized, and collection/map
   fields are count/header driven, so the parser only exposes fields where the
   local schema order and byte layout agree.
2. Used the recovered root field order for `LevelScriptTemplateData`, which has
   6 members: `actionMap`, `maxStage`, `properties`, `propertyIdToKeyMap`,
   `taskMap`, and `templateId`.
3. Probed all 35 files under `Json/LevelScriptTemplateData/`. Every file starts
   with root member count `0x06`, and the first field validates as the same
   ActionSerializedMap-style action-map header used by `LevelScriptData`:
   bytes `02 03 <u32 actionRecordCount>` immediately after the root count.
4. Every file ends with a MemoryPack UTF-8 string equal to the filename stem.
   The parser treats that exact EOF string as `templateId`.
5. Added a bounded `LevelScriptTemplateData` decoder in
   `scripts/build_data_index.py`. It exposes exact `actionMap` header facts,
   exact `templateId`, and classified length-prefixed string previews for the
   opaque middle payload: key-like names, 8-hex hashes, hash refs, property refs,
   map-property refs, local refs, LSM keys, montage refs, audio refs, effect
   refs, slash refs, and comment strings.
6. Regenerated with `python scripts\build_data_index.py --groups Json` and
   verified that the running WebUI server serves both the Data index and
   `groups/Json_LevelScriptTemplateData.json` with HTTP 200.

Observed counts:

- Decoder coverage: 35 decoded, 0 failed.
- `actionMap`: present in all 35 files.
- `actionMapRecordCount`: 0 in 8 files; 8 in 4; 7 in 4; 9 in 2; 172 in 2;
  19 in 2; 65 in 2; other files range across 1, 2, 5, 11, 13, 14, 18, 20, 24,
  38, and 137 records.
- Exact tail `templateId`: verified for all 35 files.

Examples now exposed in the WebUI shard:

- `LST_BlackBoxCamera_Graph`: action map present with 0 records; keys such as
  `blackbox_id`, `camera_pos`, `camera_rot`, and `tweentime`.
- `LST_ChasingRabbit_Graph`: 137 action records; keys such as `WaitRange`,
  `MaxTime`, `rabbitNpc`, and `check_entity_distance`; montage refs for rabbit
  NPC actions and audio refs such as `radio_wait_expired`.
- `LST_EnergyPoint_Small_Graph`: 38 action records; keys such as `fightHandle`,
  `Chest`, `ChestPosition`, and `blackboard`; audio and effect refs including
  `au_int_trchest_common_energypoint_reward_appear` and
  `P_interactive_lootshow_01_Variant`.

Still unresolved:

- `maxStage`, `properties`, `propertyIdToKeyMap`, and `taskMap` are not parsed
  structurally yet. Their strings are visible, but ownership and map/list
  boundaries need deeper ActionSerializedMap/property-map evidence.
- Action records inside template action maps are counted but not individually
  decoded in the Data index. The existing `LevelScriptData` helper only exposes
  stable header facts here.
- Hash algorithms and property ref namespaces remain unidentified; hashes are
  surfaced as observed strings, not resolved names.

Adjusted next parser plan:

1. Map the `LevelScriptTemplateData` middle fields enough to expose `maxStage`,
   property maps, and task-map counts/keys exactly.
2. Return to nested body work for `CharInteractPerformCfgs.bodyTypeActDataDict`
   and `ModelViewStateControllerData.modelAnimatorDatas`, where most remaining
   value lies after schema-only families.
3. Crack the remaining small/generic Json singletons: `GameplayConfig*`,
   `NonGeneratedConfigs`, `NavMesh`, `GPUISystemConfig`, and `InteractiveTable`.
4. For non-JSON files, keep searching for FlatBuffer schema evidence, then run
   focused probes for `IrradianceVolume/*.bytes` and `ExtendData/*.bin`.

## 2026-06-27 InteractiveTable Exact Dictionary Follow-up

`Json/Interactive/InteractiveTable.json` now has a dedicated exact MemoryPack
preview in the Data index.

Evidence and method:

1. Rechecked official MemoryPack collection formatter source while validating
   this table. The collection shape is count/header driven, so a dictionary can
   be tested by reading the count and then key/value pairs until EOF.
2. Confirmed the root object member count is `0x02`, matching the recovered
   `InteractiveTable` schema: `coreTemplatePathDict` and
   `interactiveDataDict`.
3. Parsed `coreTemplatePathDict` as a 271-entry string-to-string dictionary.
   The values are `Data/Json/Interactive/InteractiveData/...` paths.
4. Parsed `interactiveDataDict` as a 917-entry dictionary. Each entry is a
   MemoryPack UTF-8 key string, a one-byte nested value member count marker
   `0x01`, then a UTF-8 template id string.
5. The parser consumed exactly 73,949 bytes, matching the full file length.
   All 917 nested value markers are `0x01`, and every referenced template id
   has a matching `coreTemplatePathDict` key.
6. Added a bounded `InteractiveTable` decoder in `scripts/build_data_index.py`,
   regenerated with `python scripts\build_data_index.py --groups Json`, and
   verified that the running WebUI server serves both the Data index and
   `groups/Json_Interactive.json` with HTTP 200.

Observed counts:

- `coreTemplatePathDict`: 271 entries.
- `interactiveDataDict`: 917 entries.
- Unique template targets referenced by `interactiveDataDict`: 271.
- Self rows where interactive id equals template id: 271.
- Alias rows where an interactive id points at another template id: 646.
- Nested value member-count marker distribution: `{1: 917}`.

Examples now exposed in the WebUI shard:

- `int_001_comm_terminal` maps to
  `Data/Json/Interactive/InteractiveData/data_int_001_comm_terminal.json`.
- `int_003craneMonitor` maps to
  `Data/Json/Interactive/InteractiveData/data_int_003craneMonitor.json`.
- `gantry_terminal1`, `gantry_terminal2`, and `gantry_terminal3` all target
  template `int_switch_common`.
- `int_003craneGoodsTerminal` targets template `int_gantry_terminal`.
- `int_006_anchor_tree_story` targets template `int_006_dynamicBox_1`.

Still unresolved:

- The nested `0x01` byte is structurally a one-member value object marker, but
  the exact game-side field name for that single string has not been recovered.
  The WebUI labels it as a template id because all values resolve to core
  template ids.
- The table itself only links ids to template data. Runtime fields still live in
  the referenced `InteractiveData` files and their nested component bodies.

Adjusted next parser plan:

1. Crack the remaining small/schema-only Json singleton families first:
   `GameplayConfig*`, `NonGeneratedConfigs`, `NavMesh`, `GPUISystemConfig`,
   and root `InteractiveData`.
2. Return to deeper nested bodies after that: `CharInteractPerformCfgs`,
   `ModelViewStateControllerData`, and `NPCMontageJson`.
3. For non-JSON files, keep the FlatBuffer-schema search active and run focused
   probes against `Streaming/`, `DynamicStreaming/`, `IrradianceVolume/`, and
   `ExtendData/` samples once the high-value Json queue is smaller.

## 2026-06-27 ModelRadiusTable Exact Dictionary Follow-up

`Json/GameplayConfig/ModelRadiusTable.json` now has a dedicated exact
MemoryPack preview in the Data index.

Evidence and method:

1. Inventoried the remaining schema-only Json entries from the generated WebUI
   shards. The unresolved queue is now concentrated in `GameplayConfig*`,
   `GPUISystemConfig`, `NavMesh`, and a few `NonGeneratedConfigs` tables.
2. Probed several one-field dictionary-like tables. The teleport validation
   tables expose clear top-level string keys and duplicate id strings inside
   their values, but their value tails mix numeric fields and sometimes map
   strings, so they were not promoted to exact field-name decoders yet.
3. Probed `GameplayConfigSubGameInstanceDataTable.json`. It has four top-level
   string keys, but the six-member value body starts with mixed hash/tag-style
   bytes and nested option strings; this also stays parked until value-field
   evidence is stronger.
4. `ModelRadiusTable.json` validated cleanly as a one-member root table with
   1,125 entries. Each entry is a MemoryPack UTF-8 model id followed by a
   four-member value object: byte marker `0x04`, int32 `0`, a flag byte,
   int32 `-1`, and a finite float radius.
5. The parser consumed exactly 54,458 bytes, matching the file length. The
   value marker is `0x04` for all rows, the first int32 is `0` for all rows,
   and the second int32 is `-1` for all rows.
6. Added a bounded `ModelRadiusTable` decoder in `scripts/build_data_index.py`,
   regenerated with `python scripts\build_data_index.py --groups Json`, and
   verified that the running WebUI server serves `groups/Json_GameplayConfig.json`
   and `groups/Json_Interactive.json` with HTTP 200.

Observed counts:

- Rows: 1,125.
- Value member-count marker distribution: `{4: 1125}`.
- `field0` distribution: `{0: 1125}`.
- `field2` distribution: `{-1: 1125}`.
- Flag byte distribution: `{1: 1118, 0: 7}`.
- Radius range: `0.0` to about `426.107666`; all radii are finite.

Examples now exposed in the WebUI shard:

- `abilityentity_0007_mimicw_death_postmodel`: radius `0.1`.
- `abilityentity_0072_slimeml_death_postmodel`: radius `0.1`.
- `abilityentity_chr_0004_pelica_ultimate_skill_postmodel`: radius `10.651595`.
- `abilityentity_chr_0006_wolfgd_skill02_postmodel`: radius about `0.347487`.

Still unresolved:

- The game-side names for the two constant integer fields and the flag byte are
  not recovered. The WebUI labels them as `field0`, `flagByte`, and `field2`.
- The nearby `ModelTable.json` files have similar model ids but larger nested
  bodies and prefab paths. They should be decoded separately rather than
  inferred from radius rows.
- Teleport validation and SubGameInstanceData top-level dictionaries are known,
  but exact value field names and boundaries need another pass.

Adjusted next parser plan:

1. Continue exact dictionary decoders for low-risk `GameplayConfig` tables whose
   row payloads are fixed-size or have repeated duplicate ids.
2. Use the parked teleport-validation probes to map value object tails by table
   subtype, not as one generic decoder.
3. Keep `ModelTable.json`, `SubGameInstanceDataTable.json`, and
   `WorldEntityRegistry.json` for deeper nested-body work after the small fixed
   layouts are exhausted.
4. Start non-JSON probes only after this small Json queue is smaller, beginning
   with schema-less FlatBuffer candidates in `Streaming/` and `DynamicStreaming/`.

## 2026-06-27 Non-Json Data Folder Probe

After the `InteractiveTable` and `ModelRadiusTable` JSON decoders, I made a
bounded non-JSON pass over `ExtendData`, `IrradianceVolume`, `Streaming`, and
`DynamicStreaming`.

Evidence and method:

1. Listed file-only samples under each folder and captured exact sizes plus the
   first 32 bytes of representative payloads.
2. Compared the raw headers with the current generated WebUI Data summaries.
   `Streaming/` and `DynamicStreaming/` are already classified by the Data index
   as schema-less FlatBuffer-like `.bytes` files with root offsets, vtable/object
   sizes, present fields, vector lengths, and embedded string samples.
3. `IrradianceVolume/` is already split by the Data index into index, volume,
   and region-style previews. Index files begin with small table-like headers
   and UTF-16LE names such as `under_construction`; region files commonly start
   with `4096, 44` followed by float-looking vectors; large `iv_*` files start
   with `3, 2, 0, 0` and then dense binary data.
4. `ExtendData/Initial/InitStringPathHash.bin` starts with u32 values
   `38336, 1597, 35004, 2`; `ExtendData/Main/StringPathHash.bin` starts with
   `11030624, 459609, 0, 0`; `CompressData.bin` starts with a small offset-like
   sequence `228, 916, 2731, 4476`. These look like offset/hash tables, but the
   record width and string ownership were not proven.
5. No new non-JSON decoder was promoted in this pass. The current Data page
   previews are useful for triage, but exact semantic decoding still needs
   either schema evidence or stronger repeated-record validation.

Adjusted non-JSON plan:

1. For `Streaming/` and `DynamicStreaming/`, search for FlatBuffers schema names
   or generated table code before naming fields. The current schema-less walker
   should remain conservative.
2. For `IrradianceVolume/`, split future work by file subtype: index files first
   because they expose UTF-16LE names, then `regionIv_*` numeric headers, then
   the larger dense `iv_*` blobs.
3. For `ExtendData`, start with `InitStringPathHash.bin` because it is small
   enough to brute-force candidate record widths safely before touching the
   103 MB `StringPathHash.bin`.
4. Keep all non-JSON parser changes bounded by file size and exact EOF checks,
   matching the approach used for the successful JSON decoders.

## 2026-06-27 TeleportValidationDataTable Exact Dictionary Follow-up

Four binary `Json/GameplayConfig/*TeleportValidationDataTable.json` files now
have a dedicated exact MemoryPack preview in the Data index.

Evidence and method:

1. Re-inventoried unresolved Json entries from the generated WebUI shards after
   the `ModelRadiusTable` pass. The browser-visible unresolved count was 23,
   with the small teleport-validation tables still reported as generic
   MemoryPack-like configs.
2. Rechecked MemoryPack collection formatter source while validating these files.
   The top-level table shape follows the same count-driven dictionary pattern:
   root member count `0x01`, u32 row count, then key/value pairs.
3. A naive fixed-tail parse failed because the value body is not just duplicate
   id plus six floats. The byte windows showed a two-byte field before the
   vector triples and a nullable string before the final int tail.
4. The exact value layout validated across all four binary files:
   key string, value member-count byte `0x0A`, float32 `field0Float`, duplicate
   id string, uint16 `flagWord`, `position` vec3, `rotation` vec3, nullable
   `mapId` string, then four int32 tail fields.
5. The parser consumed each file exactly to EOF, verified every inner id string
   matches the dictionary key, and verified all numeric floats are finite.
6. Added a bounded `TeleportValidationDataTable` decoder in
   `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified that the
   running WebUI server serves `data/game_data/index.json` and
   `groups/Json_GameplayConfig.json` with HTTP 200.

Observed counts:

- `CommonSysTeleportValidationDataTable.json`: 3 rows; all map ids null;
  `flagWord=0`; `tail2=1002`; positions include cabin-room points.
- `GuideTeleportValidationDataTable.json`: 21 rows; all `mapId=map01_lv001`;
  `flagWord=256`; `field0Float` ranges from `3.2` to `18.8`; `tail2=1003` and
  `tail3=3`.
- `MapTeleportValidationDataTable.json`: 84 rows; map ids span map/dungeon ids;
  `flagWord=0`; `tail2=2` for 82 rows and `tail2=16` for 2 rows.
- `CinematicTeleportValidationDataTable.json`: 114 rows; 113 null map ids and
  one `base01_lv001`; `flagWord=0`; `field0Float` ranges from `0.0` to `0.5`;
  `tail2=1002`.
- `LevelScriptTeleportValidationDataTable.json` is not part of this decoder
  because it is regular text JSON with 426 object entries.

Examples now exposed in the WebUI shard:

- `TpForComSys_Mp:/CabinPoints/room_a_1`: null map id, position
  `[0.0, 1.1, 85.0]`, rotation `[0.0, 90.0, 0.0]`.
- `TpForGd_guide_group_blue_print1_50b153cd`: `map01_lv001`, position
  `[-380.0, 118.0, -172.0]`.
- `TpForMap_ent_10100020314`: `map02_lv001`, position about
  `[-1124.352, 226.687, -1738.601]`.
- `TpForCs_00488d45-96ae-4f94-a52b-ce6417a1b2bd`: null map id, position about
  `[-6.724, 57.998, -49.72]`.

Still unresolved:

- The game-side names for `field0Float`, `flagWord`, and the four tail ints are
  not recovered. The WebUI labels them as observed fields instead of guessing.
- The exact semantic difference between `tail2=2`, `16`, `1002`, and `1003`
  needs cross-referencing with text tables or IL2CPP schema metadata.
- Larger `GameplayConfig` tables such as `DialogIdTable`, `ModelTable`,
  `WorldEntityRegistry`, and `SubGameInstanceDataTable` still need deeper nested
  decoding.

Adjusted next parser plan:

1. Use the exact teleport row layout as evidence when comparing binary
   `GameplayConfig` rows with the text `LevelScriptTeleportValidationDataTable`.
2. Continue with small, bounded formats from the now 19-entry unresolved queue:
   `NonGeneratedConfigs/MatrixShockWaveBeatConfigTable.json`, `BambooRaftTaskTable`,
   `GameplayConfigMissionAreaTable`, and the smaller `NavMesh` files.
3. Keep large nested tables (`DialogIdTable`, `ModelTable`,
   `WorldEntityRegistry`, `SubGameInstanceDataTable`) for later once more value
   object layouts are known.

## 2026-06-27 LunaArea NavMesh Exact Polygon Follow-up

Four binary `Json/NavMesh/*/LunaArea.json` files now have a dedicated exact
MemoryPack preview in the Data index.

Evidence and method:

1. After the teleport-validation decoder, the browser-visible unresolved queue
   dropped to 19 rows. I tried the two smallest `NonGeneratedConfigs` files
   first, then moved to `LunaArea` because its byte layout was repeatable across
   multiple files.
2. `MatrixShockWaveBeatConfigTable.json` partially parsed as a two-member root
   with a small header, 10 hash-key rows, and row value blocks, but a 26-byte
   second top-level field/tail remained unexplained. It was not promoted.
3. `BambooRaftTaskTable.json` starts with non-string hash-like keys and nested
   string lists. Its row boundaries need more work, so it was not promoted.
4. `LunaArea.json` validated across all four files as a one-member root table:
   u32 area count, then row member-count byte `0x06`, int32 `areaId`, two-float
   center, u32 vertex count, that many vec3 vertices, a u64 tail, and a u32
   tail.
5. The parser consumed every LunaArea file exactly to EOF, verified all sampled
   floats are finite, and kept the two tail fields neutral as `tailU64` and
   `tailU32` because game-side names are not recovered.
6. Added a bounded `LunaArea` decoder in `scripts/build_data_index.py`,
   regenerated with `python scripts\build_data_index.py --groups Json`, and
   verified that the running WebUI server serves `groups/Json_NavMesh_map02.json`
   and `groups/Json_GameplayConfig.json` with HTTP 200.

Observed counts:

- `base01_lv001/LunaArea.json`: 1 area row, 17 vertices, `tailU32=1`.
- `indie_hdg004/LunaArea.json`: 1 area row, 4 vertices, `tailU32=0`.
- `map01/LunaArea.json`: 12 area rows, 48 vertices, `areaId` values `1` and
  `4`, all rows have 4 vertices, `tailU32=0`.
- `map02/LunaArea.json`: 125 area rows, 844 vertices, max 68 vertices in one
  polygon; `areaId` values include `1`, `12`, and `0`; `tailU32=0` for 90 rows
  and `1` for 35 rows.

Examples now exposed in the WebUI shard:

- `base01_lv001`: area `1`, center about `[2.377, 0.259]`, 17 vertices.
- `map01`: area `1`, center about `[126.745, 117.514]`, first polygon preview
  begins near `[-808.212, 122.129, 163.573]`.
- `map02`: area `12`, center about `[231.189, 226.692]`, first polygon preview
  begins near `[-738.689, 228.94, -1392.801]`.

Still unresolved:

- `tailU64` and `tailU32` are structurally decoded but unnamed.
- `NavMeshStateContainer.json` remains unresolved and should be decoded
  separately; its root starts with member count `0x06` but does not share the
  polygon row shape.
- The current unresolved queue is 15 browser-visible rows: large
  `GameplayConfig` tables, `GPUISystemConfig/damage_text.json`, six
  `NavMeshStateContainer` files, two small `NonGeneratedConfigs` files, and
  `NonGeneratedConfigs/ModelTable.json`.

Adjusted next parser plan:

1. Decode `NavMeshStateContainer.json` as the next NavMesh target, using the
   `LunaArea` area ids and vertices only as cross-check context, not as a shared
   schema.
2. Return to `MatrixShockWaveBeatConfigTable.json` only after identifying its
   26-byte second field; do not promote the partial row parser until that tail
   is exact.
3. Probe `BambooRaftTaskTable.json` for hash-key plus nested-list boundaries.
4. Keep the large `GameplayConfig` and `ModelTable` files for a later pass.

## 2026-06-27 NavMeshStateContainer Exact Subset Follow-up

Four of the six binary `Json/NavMesh/*/NavMeshStateContainer.json` files now
have a dedicated exact MemoryPack preview in the Data index. The two large map
variants remain generic because they include nested subsections that are not yet
mapped.

Evidence and method:

1. Searched online for exact Endfield/NavMeshStateContainer/LunaArea terms and
   did not find public schema evidence. I kept the decoder based on local byte
   evidence rather than guessed game-side names.
2. Checked local schema leads: `NavMeshComponents.dll` under both DummyDll roots
   had no useful literal `NavMeshStateContainer` or `LunaArea` strings, and the
   recovered `DefaultNavMeshBuildData` MonoBehaviour exposed NavMesh bake/build
   settings but not this Data-file schema.
3. Probed all six files as a six-member MemoryPack root. Four files consume
   exactly as count-prefixed numeric sections using three observed row widths:
   `bounds36` (`u32 key`, two ints, six finite floats), `ints16` (four int32s),
   and `ints20` (five int32s).
4. `map01` and `map02` start with the same root count but diverge into nested
   subsections after their early numeric rows, so the decoder intentionally
   declines them and leaves the generic binary summary in place.
5. Added a bounded subset decoder in `scripts/build_data_index.py`, regenerated
   with `python scripts\build_data_index.py --groups Json`, and verified the
   running WebUI server serves `index.json`, `Json_NavMesh_base01_lv001.json`,
   `Json_NavMesh_map02.json`, and `Json_GameplayConfig.json` with HTTP 200.

Observed exact subset counts:

- `base01_lv001/NavMeshStateContainer.json`: 96 rows; fields 5 and 6 contain
  48 `ints16` / 48 `ints20` records.
- `blackbox01_dg001/NavMeshStateContainer.json`: 28 rows; field 2 contains 28
  `bounds36` records.
- `blackbox02_dg001/NavMeshStateContainer.json`: 20 rows; fields 1 and 2
  contain 3 / 17 `bounds36` records.
- `indie_dg006/NavMeshStateContainer.json`: 122 rows; fields 5 and 6 contain
  61 / 61 `ints16` records.

Still unresolved:

- Game-side field names for the six sections and record columns are not
  recovered, so the WebUI labels them as observed numeric records.
- `map01/NavMeshStateContainer.json` and `map02/NavMeshStateContainer.json`
  need a nested-section parser before they can be promoted.
- The current browser-visible unresolved binary-json queue is 11 rows:
  large `GameplayConfig`/`ModelTable` rows, `GPUISystemConfig/damage_text.json`,
  two map `NavMeshStateContainer` files, and the remaining small
  `NonGeneratedConfigs` tables.

Adjusted next parser plan:

1. Map the nested subsections in the two map `NavMeshStateContainer` files.
2. Revisit `MatrixShockWaveBeatConfigTable.json` and `BambooRaftTaskTable.json`
   once their tails/nested list boundaries can be made exact.
3. Keep the larger `DialogIdTable`, `ModelTable`, `WorldEntityRegistry`, and
   `SubGameInstanceDataTable` tables for a later pass after more value-object
   layouts are known.

## 2026-06-27 NonGeneratedConfigs Exact Small Tables Follow-up

Two small `Json/NonGeneratedConfigs` binary tables now have dedicated exact
MemoryPack previews in the Data index: `MatrixShockWaveBeatConfigTable.json`
and `BambooRaftTaskTable.json`.

Evidence and method:

1. Searched online for the exact remaining table names
   (`MatrixShockWaveBeatConfigTable`, `BambooRaftTaskTable`,
   `GameplayConfigMissionAreaTable`, and `damage_text.json` with Endfield) and
   found no public schema hits. I kept the output to observed field labels.
2. A broad local schema/string search across export and DLL roots timed out, so
   I narrowed the pass to byte-level probes of the smallest unresolved files.
3. The earlier Matrix attempt had stopped on an apparent 26-byte tail. Rechecking
   row boundaries showed that the bytes belong to the final hash row: each row
   has a point-count, that many nested 3-member point records, and a final
   float. The parser now consumes the full 391-byte file exactly.
4. `BambooRaftTaskTable.json` validated as a one-member root with seven rows.
   Each row has a hash-like u32, an observed u32 field, a two-member value body,
   a count of duplicated task-id records, and an all-zero u64 tail. The parser
   consumes the full 559-byte file exactly.
5. Added bounded decoders in `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the running
   WebUI server serves `data/game_data/index.json` and
   `groups/Json_NonGeneratedConfigs.json` with HTTP 200.

Observed Matrix counts:

- Root float list: `[2.5]`.
- One section with range floats `1.0` and `2.0`.
- 10 hash-key rows with 12 total point records.
- Final row floats distribute as `12:4`, `15:3`, `10:2`, and `7:1`.
- Point member-count markers are consistently `3`; row member-count markers are
  consistently `2`.

Observed Bamboo counts:

- 7 rows, 13 total duplicated task refs.
- `field0U32` distribution is `5:4` and `2:3`.
- Task-count distribution is `2:6` and `1:1`.
- Value member-count and task member-count markers are consistently `2`.
- All duplicated task ids matched and all row tail u64 values are zero.

Still unresolved:

- Game-side field names for the Matrix numeric fields and Bamboo hash/field0
  values are not recovered.
- The current browser-visible unresolved binary-json queue is 9 rows:
  `DialogIdTable`, two `ModelTable` rows, `GameplayConfigMissionAreaTable`,
  `GameplayConfigSubGameInstanceDataTable`, `GameplayConfigWorldEntityRegistry`,
  `GPUISystemConfig/damage_text.json`, and the two nested map
  `NavMeshStateContainer` files.

Adjusted next parser plan:

1. Target `GPUISystemConfig/damage_text.json` next because its first field is a
   visible character set string and the file exposes many length-prefixed UI
   style names.
2. Probe `GameplayConfigMissionAreaTable.json` after that; its rows have clear
   ids plus transform/radius-like float tails.
3. Keep the two `ModelTable` files and larger gameplay registry tables for later
   because they are larger nested dictionaries.
4. Return to `map01`/`map02` `NavMeshStateContainer` once the nested section
   boundaries are mapped.

## 2026-06-27 SubGameInstanceDataTable Exact Follow-up

`Json/GameplayConfigSubGameInstanceDataTable.json` now has a dedicated exact
MemoryPack preview in the Data index, and the generator default source root has
been switched back to the active `export_full/` after the data move.

Evidence and method:

1. Verified that `export_full/structured/StreamingAssets/Data` contains the
   expected `Json`, `Bundles`, `Streaming`, `DynamicStreaming`, `Video`,
   `Audio`, `IrradianceVolume`, and `ExtendData` roots.
2. Searched online for exact `GameplayConfigSubGameInstanceDataTable`,
   `SubGameInstanceDataTable`, and row ids such as `world_challenge_race_03`;
   no public schema evidence surfaced.
3. Targeted local DLL/string searches found broad gameplay DLL string noise but
   no clean field-order schema for this table, so field labels stay conservative.
4. Revalidated the binary from `export_full`: one-member root, four keyed rows,
   and each value begins with a six-member marker. Row parsing consumes the full
   1,047-byte file exactly.
5. The useful recovered strings per row are: key, failure text id, source id,
   short hash, default group, quit-button text id, and success text id. Fixed
   marker-byte gaps remain exposed as marker bytes rather than named fields.
6. Added a bounded decoder in `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, waited for the long
   `export_full` scan to finish, and verified that the generated shard promotes
   this table.

Observed counts:

- 4 keyed rows.
- Value member-count markers are consistently `6`.
- `sourceId` matches the row key for all four rows.
- `failureTextId` is `world_challenge_fail` for all four rows.
- `successTextId` is `world_challenge_success` for all four rows.
- `defaultGroup` is `challenge_default` for all four rows.
- `quitButtonTextId` is `quit_challenge_btn_name` for all four rows.

Still unresolved:

- Game-side names for the fixed marker bytes around the strings are not
  recovered.
- The current browser-visible unresolved binary-json queue is 8 rows:
  `DialogIdTable`, `GameplayConfig/ModelTable`,
  `GameplayConfigMissionAreaTable`, `GameplayConfigWorldEntityRegistry`,
  `GPUISystemConfig/damage_text.json`, two nested map
  `NavMeshStateContainer` files, and `NonGeneratedConfigs/ModelTable`.

Adjusted next parser plan:

1. Continue probing `GPUISystemConfig/damage_text.json`; it has a visible
   charset string and many UI style names, but its nested layout blocks need
   exact row boundaries before promotion.
2. Probe `GameplayConfigMissionAreaTable.json`; it is smaller than the model
   tables and has readable ids plus transform/radius-like numeric tails.
3. Treat the two `ModelTable` files and `WorldEntityRegistry` as larger nested
   dictionaries that should wait until more value-object layouts are known.
4. Return to the two map `NavMeshStateContainer` files once their nested section
   boundaries are mapped.

## 2026-06-27 MissionAreaTable Exact Boundary Follow-up

`Json/GameplayConfigMissionAreaTable.json` now has a dedicated exact MemoryPack
preview in the Data index. The generator was rebuilt from the active
`export_full/structured/StreamingAssets/Data` root after the export data was
moved back to `export_full/`.

Evidence and method:

1. Searched online for exact `GameplayConfigMissionAreaTable`,
   `GameplayConfigMissionArea`, `MissionAreaTable`, and sample row ids such as
   `c13_001`; no public schema evidence surfaced.
2. Local broad string/schema searches over recovered exports and DLL-style
   sources did not produce a reliable field-order schema, so the decoder keeps
   field names observational.
3. Revalidated the binary header from `export_full`: one-member root, header
   counts `1` and `28`, followed by 73 keyed rows.
4. Parsed each row by validating the next row boundary as a length-prefixed row
   key, an eight-member value marker, marker byte `0`, and a duplicated id
   string matching the row key. The earlier idea that every row boundary was
   preceded by `0xFF` was discarded because valid rows lack that byte.
5. Parsed the first tail bytes as observed fields: flag byte, type byte, 10
   finite floats at tail offset 5, and the remaining tail bytes as opaque extra
   data. The float groups are exposed as `primaryVec3`, `secondaryVec3`, and
   `sizeValues`.
6. Added a bounded decoder in `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the served
   WebUI shard from the existing `http://127.0.0.1:8765/` server.

Observed counts:

- 73 keyed rows.
- Value member-count markers are consistently `8`.
- Duplicate id strings match row keys for all 73 rows.
- Flag/type distribution is `(0,1):33`, `(0,2):22`, `(1,1):16`, and `(1,2):2`.
- Type distribution in the WebUI summary is `1:49` and `2:24`.
- Tail length distribution is `67:55`, `157:10`, `191:2`, `123:1`,
  `174:1`, `140:1`, `373:1`, `242:1`, and `225:1`.
- The generated shard reports exact length and previews sample keys
  `c13_001`, `c13_002`, `c13m2_001`, and `c13m2_002`.

Still unresolved:

- Game-side names for the observed flag/type bytes, vector groups, size values,
  and variable extra tail blocks are not recovered.
- The current browser-visible unresolved binary-json queue is 7 rows:
  `DialogIdTable`, `GameplayConfig/ModelTable`,
  `GameplayConfigWorldEntityRegistry`, `GPUISystemConfig/damage_text.json`,
  two nested map `NavMeshStateContainer` files, and
  `NonGeneratedConfigs/ModelTable`.

Adjusted next parser plan:

1. Continue probing `GPUISystemConfig/damage_text.json`; it remains the most
   readable nested UI-style block, but needs exact row/section boundaries before
   promotion.
2. Return to `map01` and `map02` `NavMeshStateContainer` after mapping their
   nested sections; the smaller NavMesh exact decoders are useful comparison
   material.
3. Leave the two `ModelTable` files and `WorldEntityRegistry` for later because
   they are larger nested dictionaries.

## 2026-06-27 GPUISystemConfig damage_text Exact Row Follow-up

`Json/GPUISystemConfig/damage_text.json` now has a dedicated MemoryPack preview
in the Data index. The decoder promotes the table from a generic five-member
binary preview to exact top-level damage-text rows, while keeping the deeper
numeric layout/keyframe tails opaque until their fields are mapped.

Evidence and method:

1. Searched online for exact `GPUISystemConfig damage_text`, `damage_text.json`,
   `AirborneText`, `BuffColorBg`, and `ui_bat_physical_airborne`; no public
   schema evidence surfaced.
2. Revalidated the current `export_full` bytes. Both StreamingAssets and
   Persistent contain a 19,965-byte `damage_text.json`; the WebUI index source
   root is `export_full/structured/StreamingAssets/Data` and the logical path is
   `Json/GPUISystemConfig/damage_text.json`.
3. Mapped length-prefixed strings first. The file starts with root member count
   `5`, charset string `1234567890 .+-`, and a declared row count of `20`.
4. Parsed each row as a six-member object with a row flag, an animation-ref
   count, one or two five-member animation refs, matching node/layout counts,
   and a counted list of six-member UI node metadata records.
5. Corrected an early boundary mistake: `level0_damageblock_text` at row start
   `0x1bd6` looked like part of the previous knockdown tail until the detector
   was changed to validate the full row prefix. The final walk finds all 20
   rows and consumes EOF exactly.
6. Added the bounded decoder in `scripts/build_data_index.py`, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the
   existing `http://127.0.0.1:8765/` server serves the rebuilt index and
   `Json_GPUISystemConfig.json` shard.

Observed counts:

- Root member count is `5`.
- Declared and parsed damage-text rows: `20`.
- Row member-count markers are consistently `6`.
- Animation-ref member-count markers are consistently `5`; there are 22 total
  animation refs, with per-row animation counts `1:18` and `2:2`.
- Node metadata member-count markers are consistently `6`; there are 143 total
  node records.
- Node/layout count pairs are `11/11:7`, `2/2:5`, `12/12:2`, `3/3:2`,
  `5/5:1`, `4/4:1`, `10/10:1`, and `7/7:1`.
- The generated summary previews animation refs such as `element_fusion_in`,
  `level1_damage_text`, `level0_damage_text`, `level0_damageblock_text`, and
  `battletext_critical_left`.
- Layout/keyframe tail lengths are now bounded per row but still opaque; common
  examples include `184:2`, `272:2`, then single rows at lengths such as `992`,
  `908`, `911`, `993`, `1652`, and `938`.

Still unresolved:

- Game-side names for animation-ref numeric fields, node metadata numeric
  fields, and the per-row numeric layout/keyframe tails are not recovered.
- The current browser-visible unresolved binary-json queue is 6 rows:
  `DialogIdTable`, `GameplayConfig/ModelTable`,
  `GameplayConfigWorldEntityRegistry`, two nested map `NavMeshStateContainer`
  files, and `NonGeneratedConfigs/ModelTable`.

Adjusted next parser plan:

1. Probe `map01` and `map02` `NavMeshStateContainer` next if the goal is more
   exact boundary wins; four smaller sibling NavMesh containers already have
   exact numeric preview decoders for comparison.
2. Start `GameplayConfig/ModelTable` and `NonGeneratedConfigs/ModelTable` if the
   goal is model/asset linkage, but expect larger nested dictionaries.
3. Leave `GameplayConfigWorldEntityRegistry` and `DialogIdTable` for later
   unless new schema evidence appears; they are still broad registry-style
   tables with less obvious row boundaries.

## 2026-06-27 NavMeshStateContainer Grouped-List Follow-up

All six `Json/NavMesh/*/NavMeshStateContainer.json` files now use the dedicated
NavMeshStateContainer preview in the Data index. `map01` and `map02` were the
remaining generic entries because they contained variable grouped-list sections
rather than only fixed-width numeric rows.

Evidence and method:

1. Searched online for exact `NavMeshStateContainer`, `NavMeshStateContainer.json`,
   `LunaArea.json`, and `MemoryPack NavMeshStateContainer`; no public schema
   evidence surfaced.
2. Compared the four already decoded sibling containers against `map01` and
   `map02`. All six start with a six-member MemoryPack root and root fields are
   count-prefixed.
3. Revalidated `map01`/`map02` field 1 and field 2 as existing `bounds36` rows.
   The next divergence was a small count followed by hash-like u32/u64 ids,
   not another fixed-width bounds/int row.
4. Mapped the middle variable sections as `groupedU64Lists`: each group has a
   hash/key, one small observed field, a sublist count, then indexed lists of
   u64 ids. The u64 ids observed here fit in 32 bits with a zero high word.
5. Mapped the final variable section as `idValueLists`: each row has a u64-ish
   id, a small value count, and that many u32 values. This explained why the old
   fixed `ints16`/`ints20` guesses left 48 bytes or 376 bytes unconsumed.
6. A first full `python scripts\build_data_index.py --groups Json` run timed
   out while an older broad builder was also running, so I waited for the stale
   process, verified no competing builder remained, directly tested the decoder
   on full logical paths, then reran the full JSON rebuild successfully.
7. Verified the existing `http://127.0.0.1:8765/` server serves the rebuilt
   `Json_NavMesh.json` shard.

Observed counts:

- `map01/NavMeshStateContainer.json` now parses exactly as:
  `f1=bounds36:1`, `f2=bounds36:4`, `f3=empty:0`,
  `f4=groupedU64Lists:3`, `f5=ints16:104`, and
  `f6=idValueLists:104`, for 216 displayed rows/groups.
- `map02/NavMeshStateContainer.json` now parses exactly as:
  `f1=bounds36:1`, `f2=bounds36:3`, `f3=groupedU64Lists:1`,
  `f4=groupedU64Lists:2`, `f5=ints16:40`, and
  `f6=idValueLists:40`, for 87 displayed rows/groups.
- The four smaller containers still parse with their previous exact fixed-width
  layouts.

Still unresolved:

- Game-side names for the grouped-list `field0` values, id/value-list values,
  and fixed integer row fields are not recovered.
- The current browser-visible unresolved binary-json queue is 4 rows:
  `DialogIdTable`, `GameplayConfig/ModelTable`,
  `GameplayConfigWorldEntityRegistry`, and `NonGeneratedConfigs/ModelTable`.

Adjusted next parser plan:

1. Probe both `ModelTable` files next; they are the likely highest-value
   remaining tables for model/asset linkage, but expect larger nested
   dictionaries.
2. Keep `GameplayConfigWorldEntityRegistry` after the model tables because it is
   registry-shaped and may benefit from recovered model/entity id patterns.
3. Leave `DialogIdTable` for the final pass unless new schema evidence appears;
   it is still broad and less obviously bounded than the model tables.

## 2026-06-27 ModelTable Boundary Follow-up

Both remaining `ModelTable.json` binaries now have dedicated exact MemoryPack
previews in the Data index: `Json/GameplayConfig/ModelTable.json` and
`Json/NonGeneratedConfigs/ModelTable.json`.

Evidence and method:

1. Searched online for exact `GameplayConfig/ModelTable.json`,
   `NonGeneratedConfigs/ModelTable.json`, `ModelTable.json` with Endfield, and
   concrete ids such as `abilityentity_0007_mimicw_death_postmodel`; no public
   schema evidence surfaced.
2. Revalidated the current `export_full` bytes after the data was moved back to
   the default source root. Both files start with a two-member MemoryPack root.
3. Parsed the first root field as a counted model dictionary. Each row has a
   string key, a six-member value marker, nullable alternate-model string, one
   flag byte, a duplicate model-id string, a `.prefab` path, one finite float
   scale, and one tail int. The duplicate model id matches the key in every
   row.
4. Parsed the second root field as a counted layout dictionary with twelve-member
   value markers and opaque payload bodies. Row boundaries are found by the next
   valid length-prefixed layout key plus marker `0x0c`; the key grammar had to
   allow spaces because `int_trigger_dnarrative_widgetTianshiyi_postmodel 1` is
   a real row key.
5. The first boundary probe accidentally treated keys as strictly no-space and
   produced one oversized row. Allowing `[A-Za-z0-9_+ .-]` keys consumes both
   files exactly.
6. Added the bounded decoder in `scripts/build_data_index.py`, directly tested
   it on both ModelTable files, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the existing
   `http://127.0.0.1:8765/` server serves the rebuilt index plus the
   `Json_GameplayConfig.json` and `Json_NonGeneratedConfigs.json` shards.

Observed counts:

- `GameplayConfig/ModelTable.json`: 1,034 model rows and 876 layout rows, for
  1,910 displayed rows. Model flags are `0:778` and `1:256`; tail ints are
  `0:875`, `3:76`, `4:33`, `2:32`, and `6:18`; every layout payload is 55
  bytes.
- `NonGeneratedConfigs/ModelTable.json`: 1,164 model rows and 969 layout rows,
  for 2,133 displayed rows. Model flags are `0:756` and `1:408`; tail ints are
  `0:967`, `3:91`, `4:45`, `6:32`, and `2:29`; layout payload lengths are
  mostly `55:916`, with variable rows such as `143:14`, `149:7`, `131:7`,
  `114:5`, `145:4`, `130:4`, and `128:4`.
- NonGenerated variable layout payloads expose embedded strings such as
  `enemyLock`, `P_interactive_door+1_002_01`, `doorEnemyLock_Big`, and
  `mineEnemyLock_Middle`, but the numeric payload body remains observed-only.

Still unresolved:

- Game-side names for the model flag byte, tail int, and twelve-member layout
  payload fields are not recovered.
- The current browser-visible unresolved binary-json queue is 2 rows:
  `DialogIdTable` and `GameplayConfigWorldEntityRegistry`.

Adjusted next parser plan:

1. Probe `GameplayConfigWorldEntityRegistry` next; it is registry-shaped and may
   benefit from the recovered model/entity id patterns.
2. Leave `DialogIdTable` for the final pass unless new schema evidence appears;
   it is broad and still less obviously bounded than the registry.

## 2026-06-27 GameplayConfigWorldEntityRegistry Exact Follow-up

`Json/GameplayConfigWorldEntityRegistry.json` now has a dedicated exact
MemoryPack preview in the Data index. This leaves `DialogIdTable.json` as the
only browser-visible generic MemoryPack-like Json entry.

Evidence and method:

1. Searched online for exact `GameplayConfigWorldEntityRegistry.json`,
   `GameplayConfigWorldEntityRegistry`, `WorldEntityRegistry` with Endfield, and
   `Beyond.Gameplay WorldEntityRegistry`; no public schema evidence surfaced.
2. Ran a local type/reference search. A broad search through `tools/` timed out,
   then a narrower maintained-code search found only previous notes and the
   story logic-id audit treating this binary as a gameplay-config scan target.
3. Compared the binary against the large text
   `Json/GameplayConfig/WorldEntityRegistry.json`. The binary uses the same
   high-level row concepts (`detailId`, `entityType`, `position`, `rotation`,
   `propertyList`, `valueBit64`) but does not mirror the same text rows by key,
   so the parser treats it as its own compact runtime registry.
4. Parsed the root as four fields: two empty count-prefixed fields, one counted
   brief-info table, and one counted config-info table.
5. Parsed brief-info rows as `u64 entityId`, four-member value marker, nullable
   `detailId`, `entityType`, `position` vec3, and `rotation` vec3. Row 268 has a
   null `detailId`, which corrected an initial too-strict non-null string guard.
6. Parsed config-info rows as `u64 entityId`, one-member value marker, counted
   property list, two-member property key/value records, type `11` value arrays,
   and two-member value items containing signed `valueBit64` plus an observed
   tail int. The low 32 bits of `valueBit64` decode as useful float previews.
7. Added the bounded decoder in `scripts/build_data_index.py`, directly tested
   it on the current export, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the existing
   `http://127.0.0.1:8765/` server serves the rebuilt index and
   `Json_GameplayConfigWorldEntityRegistry.json` shard.

Observed counts:

- Root member count is `4` with field counts `0`, `0`, `893`, and `4`.
- The 893 brief rows all use value member count `4`.
- Entity type counts are `32:595`, `256:231`, `16:66`, and `128:1`.
- Top non-null detail ids include `int_doodad_ore_cluster_iron:92`,
  `int_doodad_ore_cluster_originium:52`, `int_doodad_flower_1:31`,
  `int_doodad_grade:26`, and `int_trigger_volume:24`.
- The four config rows all use value member count `1`, property count `2`,
  property names `position` and `rotation`, property value type `11`, three
  value items per property, value item member count `2`, and tail int `-1`.

Still unresolved:

- Game-side names for the first two empty root fields and the value-item tail
  int are not recovered.
- The current browser-visible unresolved binary-json queue is 1 row:
  `DialogIdTable`.

Adjusted next parser plan:

1. Focus exclusively on `DialogIdTable.json` next. It is the final generic
   binary Json row, but it is larger and likely has multiple string-keyed
   dictionaries or dialog-id arrays.
2. Keep using exact boundary validation plus targeted text-table/story-builder
   comparisons before promoting any partial parser.

## 2026-06-27 DialogIdTable Root-Field Follow-up

`Json/GameplayConfig/DialogIdTable.json` now has a dedicated exact MemoryPack
preview in the Data index. After rebuilding, there are no remaining
browser-visible generic `MemoryPack-like binary config` Json rows.

Evidence and method:

1. Searched online for exact `DialogIdTable.json`, `DialogIdTable` with Endfield,
   `Beyond.Gameplay DialogIdTable`, and sample `dlg_a1m*` terms; no public
   schema evidence surfaced.
2. Read the maintained `scripts/story_builder/dialog_registry.py` extractor. It
   confirms the runtime class as `Beyond.Gameplay.DialogIdTable` with nested
   `DialogBriefInfo`, but the existing Story workflow only scanned raw ids.
3. Tried managed reflection on `tools/DummyDll/MemoryPack.Beyond.dll`; it still
   fails with the known duplicate-type `BadImageFormatException`, so field names
   had to come from byte layout plus the existing registry extractor semantics.
4. Parsed the root as a five-member MemoryPack object. The first field is a
   2,258-row `DialogBriefInfo` dictionary keyed by length-prefixed dialog ids
   followed by value member count `7`.
5. The nested `DialogBriefInfo` value has nullable/variant leading subrecords,
   so the Data index now treats its internals as bounded payload previews rather
   than forcing a fragile full nested parser. Exact row boundaries are recovered
   by scanning valid length-prefixed `dlg_`/`radio_` keys followed by marker `7`
   and validating the next root field.
6. Parsed the remaining root fields exactly: field 2 is `int -> dialogId`
   (2,258 rows), field 3 is `int -> optionId` (4,182 rows), field 4 is the
   reverse `dialog/option id -> int` map (4,182 rows), and field 5 is the reverse
   `dialogId -> int` map (2,258 rows).
7. Reused the same regex semantics as `dialog_registry.py` to summarize runtime
   registry scenes, trunk/line ids, and option ids directly in the Data index.
8. Added the bounded decoder in `scripts/build_data_index.py`, directly tested it
   on the current export, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the existing
   `http://127.0.0.1:8765/` server serves the rebuilt `Json_GameplayConfig.json`
   shard.

Observed counts:

- Root member count is `5`.
- Field counts are `2,258`, `2,258`, `4,182`, `4,182`, and `2,258`.
- The first field consumes exactly up to offset `0x41581`; payload length counts
  start with `93:349`, `92:288`, `91:259`, `90:218`, `94:93`, and `97:45`.
- Registry summary from raw ids: 4,918 registered scenes, 4,870 root keys, 3,589
  line ids, 4,131 option ids, 1,156 scenes with trunk/line decomposition, 541
  multi-trunk scenes, 1,299 scenes with options, and no `radio_` scene keys in
  this export.
- Generated Data row summary reports 15,138 displayed rows across all five root
  fields.

Still unresolved:

- Full field names inside the seven-member `DialogBriefInfo` payload remain only
  partially inferred. The Data index preserves exact payload lengths and string
  samples while avoiding a brittle parser for the nullable subrecord variants.
- No browser-visible generic binary Json rows remain after this pass.

Adjusted next parser plan:

1. Move from generic-row elimination to deeper nested-body recovery. Highest
   value candidates are `DialogBriefInfo` nested fields, `DialogIdTable` payload
   subrecords, `Interactive` component union bodies, and other Data-index rows
   that still advertise opaque nested payloads in their summaries.
2. Continue using exact boundaries plus local IL2CPP/Story-builder evidence; do
   not promote speculative nested field names without validation across the full
   export.

## 2026-06-27 DialogBriefInfo Nested Field Follow-up

`Json/GameplayConfig/DialogIdTable.json` now parses the nested seven-member
`DialogBriefInfo` value, not just the root dictionaries. The Data index summary
now exposes `dialogType`, `interactText`, `npcProxyIds`, and `useBlackScreen`
columns for this row, and the parser validates the two mask blend subrecords for
every row before promoting the nested fields.

Evidence and method:

1. Searched online for exact `Beyond.Gameplay.DialogIdTable`,
   `DialogBriefInfoForMemoryPack`, and `DialogIdTable DialogBriefInfo
   MemoryPack`; no public Endfield schema or source hit surfaced.
2. Reran the local IL2CPP metadata catalog and narrowed it to
   `Beyond.Gameplay.DialogIdTable`, `Beyond.Gameplay.DialogIdTable+DialogBriefInfo`,
   `Beyond_Gameplay_DialogIdTableForMemoryPack`, and
   `Beyond_Gameplay_DialogIdTable_DialogBriefInfoForMemoryPack`.
3. The runtime type names the seven `DialogBriefInfo` fields as `dialogId`,
   `dialogType`, `useBlackScreen`, `beforeMaskBlendData`, `afterMaskBlendData`,
   `interactText`, and `npcProxyIds`; the generated MemoryPack formatter order is
   `afterMaskBlendData`, `beforeMaskBlendData`, `dialogId`, `dialogType`,
   `interactText`, `npcProxyIds`, and `useBlackScreen`.
4. The same metadata names `CommonMaskBlendData` fields and its formatter order:
   `audioBlackScreenBehaviour`, `curve`, `fadeInDuration`, `fadeOutDuration`,
   `maskType`, and `useCurve`. The parser treats the curve bytes as a bounded
   raw curve payload while decoding the surrounding typed fields exactly.
5. Built a byte-level probe that finds the duplicate length-prefixed `dialogId`
   inside each payload, splits the preceding bytes into the two nullable/common
   mask records, then parses `dialogType`, the one-member `LangKey` wrapper for
   `interactText`, the nullable string list for `npcProxyIds`, and the final
   `useBlackScreen` byte. This consumed every `DialogBriefInfo` payload exactly.
6. Promoted the parser into `scripts/build_data_index.py`, compiled it, directly
   decoded `export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json`,
   regenerated with `python scripts\build_data_index.py --groups Json`, and
   verified the existing `http://127.0.0.1:8765/` server serves the rebuilt
   `index.json` and `Json_GameplayConfig.json` shard.

Observed counts:

- All 2,258 `DialogBriefInfo` rows parse exactly, and all 2,258 duplicate
  `dialogId` values match their dictionary keys.
- `dialogType` counts are `2:1211`, `1:1045`, and `0:2`.
- `interactText` is null for 2,194 rows; top non-null values are
  `ui_nar_interact_as_talk:32`, `lang_npc_talk:8`, `npcName_unknown:6`,
  `ui_nar_interact_as_watch:4`, `ui_common_check:3`,
  `ui_nar_interact_as_ask:2`, and `lang_int_submit_option:2`.
- `npcProxyIds` count distribution is `null:1617`, `1:596`, `2:39`, `3:3`,
  `4:2`, and `5:1`.
- `useBlackScreen` is `true` for 1,225 rows and `false` for 1,033 rows.
- Mask prefix lengths are `62:2081`, `2:169`, `86:7`, and `74:1`; the paired
  mask byte lengths are `after:31|before:31` for 2,081 rows,
  `after:1|before:1` for 169 null-mask rows, `after:43|before:43` for 7 rows,
  and `after:31|before:43` for 1 row.
- The regenerated compact Data shard still has zero remaining generic
  MemoryPack-like JSON entries.

Still unresolved:

- `CommonMaskBlendData.curve` is still represented as a bounded byte segment
  with length/prefix metadata. Its surrounding mask fields are exact, but the
  curve payload needs Unity `AnimationCurve`/MemoryPack formatter evidence before
  field-level promotion.
- Several other decoded families still advertise opaque nested bodies even though
  no whole-file generic JSON entries remain.

Adjusted next parser plan:

1. Move to nested opaque bodies outside `DialogIdTable`, starting with high-value
   rows already surfaced in the Data summaries: `Interactive` component bodies,
   `ModelTable` layout payloads, animation/curve bodies, and ActionSerializedMap
   tails in `LevelScriptData`/`LevelScriptTemplateData`.
2. Keep the promotion rule strict: local metadata or code evidence plus exact
   byte consumption across the current `export_full` before adding fields to the
   WebUI Data summaries.

## 2026-06-27 ModelTable Layout Payload Follow-up

The two `ModelTable.json` entries no longer treat layout rows as opaque bounded
payloads. `scripts/build_data_index.py` now decodes the `extraData_interactive`
layout dictionary values for both `Json/GameplayConfig/ModelTable.json` and
`Json/NonGeneratedConfigs/ModelTable.json`.

Evidence and method:

1. Rechecked online for exact `ModelExtraData_Interactive`,
   `ModelTableForMemoryPack`, and `Beyond.Gameplay.View.ModelTable` names; no
   public Endfield schema or implementation surfaced.
2. Queried local IL2CPP metadata into `tmp/model_table_metadata.*` and
   `tmp/model_enums_metadata.*`. The useful runtime classes are
   `Beyond.Gameplay.View.ModelTable`, `ModelData`,
   `ModelExtraData_Interactive`, `ModelShapeData`, and
   `GameplayLockViewModelConfig`.
3. The generated formatter evidence gives the interactive layout value order as
   `center`, `collisionShapeDatas`, `collisionType`, `dynamicUpdateRVO`,
   `gameplayLockViewConfig`, `hasMultiLevel`, `height`, `obstacleType`,
   `radius`, `rvoConcernValue`, `shape`, and `size`.
4. Replaced the previous layout-boundary regex heuristic. That heuristic was too
   permissive because the first bytes of valid layout payloads can resemble a
   new short string key followed by marker `0x0c`, producing fake layout keys
   such as punctuation characters. The new parser reads every layout row
   sequentially from the dictionary count and consumes the 12-member value body.
5. Added parsers for the nested gameplay-lock-view map and future
   `collisionShapeDatas` list. Current export rows have zero collision-shape
   list items, but the parser validates and records the count.
6. Compiled `scripts/build_data_index.py`, directly decoded both current
   `export_full` files, regenerated with
   `python scripts\build_data_index.py --groups Json`, and verified the
   existing `http://127.0.0.1:8765/` server serves `data/game_data/index.json`,
   `Json_GameplayConfig.json`, and `Json_NonGeneratedConfigs.json`.

Observed counts:

- `GameplayConfig/ModelTable.json`: 1,034 model rows and 876 layout rows; every
  layout value is 55 bytes, `collisionType` is `0` for all rows,
  `gameplayLockViewConfig` count is `0` for all rows, `dynamicUpdateRVO` is
  `false:837` and `true:39`, `hasMultiLevel` is `false:867` and `true:9`,
  `obstacleType` is `0:571`, `2:194`, and `1:111`, and `shape` is `1:556` and
  `0:320`.
- `NonGeneratedConfigs/ModelTable.json`: 1,164 model rows and 969 layout rows;
  byte lengths are `55:916`, `143:14`, `149:7`, `131:7`, `114:5`, `145:4`,
  `130:4`, `128:4`, `132:3`, `129:3`, `133:1`, and `112:1`; lock-view config
  counts are `0:916` and `1:53`; all non-empty lock maps use key `enemyLock`;
  `dynamicUpdateRVO` is `false:930` and `true:39`, `hasMultiLevel` is
  `false:941` and `true:28`, `obstacleType` is `0:528`, `2:248`, and `1:193`,
  and `shape` is `1:659` and `0:310`.
- Sample lock-view rows decode model node names such as
  `P_interactive_door+1_002_01` and view config ids such as
  `doorEnemyLock_Big` / `mineEnemyLock_Middle` with vec3 `mountOffset` values.
- The regenerated compact Json shards still report zero remaining whole-file
  generic MemoryPack-like rows.

Still unresolved:

- The enum labels for `shape`, `obstacleType`, and `collisionType` are supported
  by metadata names, but the Data index currently keeps the numeric values until
  every value mapping is validated from enum constants rather than inferred from
  names alone.
- No current row exercises non-empty `collisionShapeDatas`, so that nested list
  grammar is implemented from formatter order but not proven on a positive row.

Adjusted next parser plan:

1. Continue nested-body recovery now that the whole-file generic queue is empty.
   High-value next candidates are `Interactive` component union bodies,
   `AnimationConfig` montage/curve bodies, `NPC/MontageJson` 22-member nested
   bodies, and `ActionSerializedMap` tails in `LevelScriptData` and
   `LevelScriptTemplateData`.
2. Keep using the strict promotion rule: exact byte consumption across the
   current export plus IL2CPP formatter/type evidence before adding fields to
   the WebUI Data summaries.

## 2026-06-27 Interactive Component Prefix Follow-up

`Json/Interactive/InteractiveData/*.json` now decodes the first two
`componentList` entries as typed MemoryPack union records instead of only
scanning strings from the first component payload.

Evidence and method:

1. Rechecked public MemoryPack documentation/source for the union framing rather
   than assuming local bytes: union tags use a one-byte tag for values below 250
   and `250 + ushort` for wider tags, while object values begin with a one-byte
   member count. No public Endfield-specific interactive schema surfaced.
2. Reused the local `build_memorypack_union_tag_audit.py` extractor with the
   current CodeRegistration `0x18c439740`, writing temporary results under
   `tmp/memorypack_union_tags.*`. The `BaseComponentData` union table contains
   272 continuous tags, `0x0000..0x010f`; `0x0073` is
   `Core_InteractiveRootComponentData`, and `0x0108` is
   `View_InteractiveModelComponentData`.
3. Queried local IL2CPP metadata for `InteractiveTemplateData`,
   `RootComponentData`, `InteractiveRootComponentData`, `ModelComponentData`,
   and observed component wrappers. `InteractiveTemplateData` retains the
   inherited 25-member root order already used by the Data index. The root
   component has no own fields, and the model component inherits the four
   `ModelComponentData` fields in generated setter order:
   `bornFadeInTime`, `enableBornFadeIn`, `modelId`, and `modelScale`.
4. Byte-probed all 271 current `InteractiveData` files. Every file has component
   1 as tag `0x0073` with member count `0`, followed by component 2 as wide tag
   `0x0108` with member count `4`. The parser now decodes that model component
   prefix exactly and then keeps the remaining component payload as bounded
   string samples until more component bodies are mapped.
5. Promoted the helper `read_memorypack_union_tag` and the interactive prefix
   parser into `scripts/build_data_index.py`, compiled it, directly validated all
   271 files, regenerated with `python scripts\build_data_index.py --groups Json`,
   and verified the existing server serves `data/game_data/index.json` and
   `data/game_data/groups/Json_Interactive.json`.

Observed counts:

- `componentList` counts across the 271 files are `7:69`, `5:36`, `8:35`,
  `9:33`, `6:25`, `4:22`, `10:21`, `11:16`, `12:6`, `3:4`, `13:3`, and `15:1`.
- First component: `0x0073/Core_InteractiveRootComponentData/memberCount=0` for
  all 271 files.
- Second component: `0x0108/View_InteractiveModelComponentData/memberCount=4`
  for all 271 files.
- The model component has `modelScale=1.0`, `bornFadeInTime=1.0`, and
  `enableBornFadeIn=false` for all 271 files. `modelId` is non-null for 209 rows
  and null for 62 rows.
- The compact WebUI summary now shows `firstComponent=Core_InteractiveRootComponentData`
  and, when non-null, `modelComponent=<postmodel id>`.

Still unresolved:

- Components after the second entry are still not skipped or decoded by type.
  The next step is a component-body walker that uses the `BaseComponentData`
  tag table plus per-wrapper setter metadata to skip/parse common component
  bodies such as `Core_BaseControllerData`, `Core_TriggerObserverComponentData`,
  and interactive trigger/collider/property records.
- The current parser remains intentionally prefix-only; it does not claim exact
  length for the full `InteractiveTemplateData` root.

Adjusted next parser plan:

1. Build a reusable component-body boundary walker using the extracted
   `BaseComponentData` tag table and formatter setter counts, then start with
   observed component tags from the 271 interactive templates.
2. If component bodies prove too broad, switch to another bounded family with
   clearer formatter evidence, such as `ModelViewStateControllerData` animator
   data or `NPC/MontageJson` 22-member montage bodies.

## 2026-06-27 Interactive Component Boundary Follow-up

The `InteractiveTemplateData.componentList` parser now walks past all
zero-member components immediately after the model component and exposes the
first nonzero component payload tag. This is still not a full component-body
parser, but it gives stable typed boundaries for the next work queue.

Evidence and method:

1. Reused the temporary `tmp/memorypack_union_tags.*` output from the local
   `BaseComponentDataForMemoryPack` union-tag extraction. No public Endfield
   component schema surfaced from web searches for the observed component names.
2. Added the observed first-payload component tag names to
   `BASE_COMPONENT_UNION_TAGS` in `scripts/build_data_index.py`, including
   `Core_BaseControllerData`, `Core_SimpleAnimatorComponentData`,
   `Core_TriggerObserverComponentData`, trigger/click/logic/audio components,
   and the rarer one-off component tags seen in current `InteractiveData`.
3. Extended the parser after the proven model component. It now reads component
   union tags and one-byte member counts until it reaches the first nonzero
   payload body. Zero-member components are exact because there is no body to
   skip; nonzero components are reported as the next payload tag/member count
   without consuming speculative body fields.
4. Direct validation over all 271
   `export_full/structured/StreamingAssets/Data/Json/Interactive/InteractiveData/*.json`
   files returned no parser errors. Regenerated with
   `python scripts\build_data_index.py --groups Json`, then verified the
   existing server serves `data/game_data/index.json` and
   `data/game_data/groups/Json_Interactive.json`.

Observed counts:

- `componentPrefix=3` for 262 files: root component, model component, and
  `0x0016/Core_BaseControllerData` with member count `0`.
- `componentPrefix=4` for 9 files: the same three entries plus
  `0x00bd/Core_SimpleAnimatorComponentData` with member count `0`.
- First nonzero payload tags are now named in the compact summaries. Top counts
  are `Core_TriggerObserverComponentData:3` for 88 files,
  `Core_InteractiveCommonPerformComponentData:3` for 30,
  `Core_ClickTriggerComponentForIntData:3` for 19,
  `Core_InteractiveLogicControllerComponentData:2` for 17,
  `Core_KeepRelativeOffsetComponentData:1` for 17,
  `Core_TriggerZoneComponentForIntData:3` for 17,
  `Core_FactoryBuildingWrapperComponentData:1` for 15,
  `Core_InteractiveAudioData:2` for 11, and
  `Core_AbilitySystemForIntData:36` for 10.
- Four templates have no first nonzero payload after the parsed zero-member
  prefix, which means the component list is exhausted by the exact prefix.

Still unresolved:

- The nonzero component payload bodies are not skipped or decoded yet. The
  largest next target is `Core_TriggerObserverComponentData`, where the first
  field is a property-style map containing keys such as `shape`, `radius`,
  `center`, `size`, `interactive_direction_check`, and related trigger bounds.
- The property/value encoding used inside these component bodies needs a small
  typed parser before it is safe to claim exact body consumption.

Adjusted next parser plan:

1. Decode the common property-map body shape used by
   `Core_TriggerObserverComponentData` and related trigger/click components,
   starting with count/key/value framing and primitive vector/list variants.
2. If that map grammar broadens too much, switch to a narrower bounded family
   such as `ModelViewStateControllerData` or `NPC/MontageJson` while keeping the
   interactive component tag inventory as the queue for later passes.

## 2026-06-27 Interactive TriggerObserver Body Follow-up

`Core_TriggerObserverComponentData` is now the first nonzero Interactive
component body with exact field-level parsing in the Data index. This covers the
largest first-payload family exposed by the component-boundary pass.

Evidence and method:

1. Rechecked public MemoryPack context through the upstream Cysharp MemoryPack
   repository and searched for the observed Endfield component names. The public
   source confirms MemoryPack is the C#/Unity binary serializer family, but no
   public Endfield `Core_TriggerObserverComponentData` schema surfaced.
2. Filtered local IL2CPP metadata for `InteractiveDataBase`,
   `InteractivePropertyData`, `GameEventsUpdateConfig`, `LevelEntityConfig`,
   `NoUseConfig`, `SystemStateConfig`, `SystemUnlockConfig`, and
   `TargetEntityConfig`. The relevant nested value shape uses a generated
   two-member property-value wrapper with a `valueType` int and a value array.
3. Matched the component bytes against the property/value shape already seen in
   other recovered config data: each property-map entry has member count `2`, a
   non-null key string, then a two-member value object containing `valueType`, a
   value-array count, and value items with member count `2`, `valueBit64`, and a
   tail int.
4. Promoted `parse_interactive_component_property_map` and the narrow
   `parse_interactive_trigger_observer_component` into
   `scripts/build_data_index.py`. The parser only consumes
   `Core_TriggerObserverComponentData` when tag `0x00d9` and member count `3`
   match; other nonzero component bodies remain tag-only.
5. Direct validation over all 271 `InteractiveData` files returned no component
   parse errors. All 88 first-payload TriggerObserver bodies consume exactly 587
   bytes, then hand off cleanly to the next component tag.
6. Regenerated with `python scripts\build_data_index.py --groups Json` and
   verified the existing server serves `data/game_data/index.json` and
   `data/game_data/groups/Json_Interactive.json`.

Observed counts:

- First nonzero payload `Core_TriggerObserverComponentData:3` appears in 88 of
  the 271 `InteractiveData` files.
- Every parsed TriggerObserver body has byte length `587` and property-map
  counts `[12, 0, 0]`.
- The 12 primary keys are stable across all 88 rows: `shape`, `radius`,
  `center`, `size`, `interactive_direction_check`, `check_area_offset`,
  `check_area_radius`, `check_area_height`, `check_angle`,
  `player_direction_check`, `is_important`, and
  `in_trigger_volume_performance`.
- Primary value-type counts per row are stable as `5:4`, `1:4`, `11:3`, and
  `3:1`; across all rows this totals `5:352`, `1:352`, `11:264`, and `3:88`.
- The compact WebUI summary now includes `triggerMaps=12,0,0`, plus typed
  `triggerShape` and `triggerRadius` previews for the parsed rows.

Still unresolved:

- TriggerObserver is exact only when it is the first nonzero payload. The same
  body shape can also appear later in component lists, but the parser does not
  yet walk arbitrary later components.
- Other first-payload families remain tag-only: common next targets are
  `Core_InteractiveCommonPerformComponentData`,
  `Core_ClickTriggerComponentForIntData`, `Core_TriggerZoneComponentForIntData`,
  and `Core_InteractiveAudioData`.

Adjusted next parser plan:

1. Generalize the component walker enough to parse the next nonzero component
   after TriggerObserver when the just-parsed body provides an exact end offset.
2. Reuse the property-map parser for smaller one-map component bodies such as
   `Core_KeepRelativeOffsetComponentData`, `Core_InteractCommonTwoStateComponentData`,
   and `Core_CanSetVisibleComponentData` before attempting broader audio or
   ability-system payloads.

## 2026-06-27 Interactive Single Property-Map Component Follow-up

The Interactive parser now decodes the next validated first-payload component-body family after TriggerObserver: one-member bodies that consist of a single MemoryPack property map.

Evidence and method:

1. Reused the proven `InteractivePropertyData` count/key/value parser from the TriggerObserver pass instead of inventing a second map grammar.
2. Ran a corpus probe over all 271 files in `export_full/structured/StreamingAssets/Data/Json/Interactive/InteractiveData/`, starting at `componentListFirstPayload.payloadOffset` for first-payload components with `memberCount == 1`.
3. Treated a candidate body as exact only when the property map consumed cleanly and, when another component followed, the next bytes framed as a plausible MemoryPack union tag plus member count. Later component union ids are not all named yet, so the check accepts plausible unnamed tags while keeping their type labels as `tag_0xNNNN`.
4. Promoted the exact set into `INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS` and `parse_interactive_single_property_map_component` in `scripts/build_data_index.py`. Known mixed bodies that failed the property-map shape, such as `Core_PlayerInteractPerformComponentData`, `ScannableTraceComponentData`, `tag_0x002e`, and `tag_0x0085`, remain tag-only.
5. Direct validation over all 271 `InteractiveData` files returned zero decode errors. Regenerated with `python scripts\build_data_index.py --groups Json`; the existing server returns HTTP 200 for `data/game_data/index.json` and `data/game_data/groups/Json_Interactive.json`.

Observed counts:

- 62 additional first-payload component bodies now parse as exact one-member property maps.
- Common rows: `Core_KeepRelativeOffsetComponentData` 17 rows with six keys (`value_bool`, `dont_log_error`, `target_list`, `follow_type`, `position_list`, `rotation_list`); `Core_FactoryBuildingWrapperComponentData` 15 rows with an empty map; `Core_InteractCommonTwoStateComponentData` 6 rows with `destroy_self`; `Core_InteractiveCommonMultiStateComponentData` 4 rows with `min_state`/`max_state`; `Core_CanSetVisibleComponentData` 3 rows with `is_visible`.
- Smaller exact families include Gameplay/Electric node rows, infrared laser group rows, custom curve movement, door/water/outfall destroy flags, navmesh dynamic bake area, steam blocker, hidden mark, and unnamed tags `0x0019`, `0x0083`, `0x00c6`, and `0x00d8`.
- Compact WebUI summaries now show `propertyMap=<count>` and the first few `propertyKeys=` for these rows; TriggerObserver summaries remain `triggerMaps=12,0,0` with trigger shape/radius previews.

Still unresolved:

- The parser still stops at the first nonzero payload body; it does not yet walk and parse later components after a decoded body.
- Multi-member first-payload families remain the highest-value queue: `Core_InteractiveCommonPerformComponentData`, `Core_ClickTriggerComponentForIntData`, `Core_TriggerZoneComponentForIntData`, `Core_InteractiveAudioData`, `Core_HittableComponentForIntData`, and `Core_AbilitySystemForIntData`.
- Several union tags are structurally validated but not named yet (`0x007f`, `0x008e`, `0x00ba`, `0x00d5`, and first-payload tags such as `0x0013`, `0x002e`, `0x0085`, `0x00c6`, `0x00ce`, `0x00d8`). The next naming pass should revisit GameAssembly/DummyDll formatter evidence.

Adjusted next parser plan:

1. Add a safe component walker that can continue after exact first-payload bodies and parse later zero/member-map bodies without losing boundary validation.
2. In parallel, inspect non-Json Data folders (`ExtendData`, `Streaming`, `DynamicStreaming`, and `IrradianceVolume`) for a small exact parser target, since the current WebUI already has bounded schema-less previews there but little semantic decoding.

## 2026-06-27 Interactive Component Walker Follow-up

The first-payload component parser has been generalized into a safe component-list walker. It parses exact body shapes repeatedly and stops at the first unsupported mixed payload instead of stopping immediately after the first nonzero component.

Evidence and method:

1. Prototyped a walker from `componentListSecondEndOffset`, reading each MemoryPack union tag and one-byte member count in order.
2. Allowed only three exact body classes: zero-member components, `Core_TriggerObserverComponentData` with three property maps, and validated one-member property-map components. Any other member shape becomes the stop component; no speculative skip is attempted.
3. The prototype over all 271 `InteractiveData` files had zero boundary errors. The promoted `decode_interactive_template_memorypack` now records parsed payload rows, the stop payload, scan offset, and lists of parsed TriggerObserver/property-map bodies.
4. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server serves the updated Interactive shard with HTTP 200.

Observed counts after regeneration:

- 129 of 271 templates now have at least one parsed nonzero payload before a stop point.
- Parsed payload count distribution per template: `0:121`, `1:102`, `2:43`, `3:5`.
- `Core_TriggerObserverComponentData` bodies decoded across component lists: 106 total, up from 88 when only the first payload was parsed.
- One-member property-map bodies decoded across component lists: 84 total across 79 WebUI summaries.
- Top stop components are still mixed or unknown shapes: `Core_InteractiveCommonPerformComponentData:3` 44, `Core_InteractiveAudioData:2` 41, `Core_InteractiveLogicControllerComponentData:2` 40, `Core_ClickTriggerComponentForIntData:3` 26, `Core_TriggerZoneComponentForIntData:3` 21, `tag_0x003f:1` 18, `Core_PlayerInteractPerformComponentData:1` 13, `Core_AbilitySystemForIntData:36` 11, and `Core_HittableComponentForIntData:3` 10.

Other-file check:

- In the moved `export_full`, `structured/StreamingAssets/Data` currently contains only `Json/` and `Video/`; the earlier non-Json binary folders noted in older exports are not present under this Data root.
- `Data/Video` is MP4 guide/media content and remains excluded from the Data tab because the Assets/media path owns video browsing.
- The only sibling structured data root in this export is `structured/StreamingAssets/Table`, containing 629 text `.json` table files already covered by the existing Text Tables/WebUI table workflows rather than the binary-Json decoder.

Adjusted next parser plan:

1. Name the newly observed stop/unknown union tags from GameAssembly/DummyDll formatter evidence where possible.
2. Attack one mixed stop family next. The best candidates are `Core_InteractiveLogicControllerComponentData:2` or `Core_InteractiveAudioData:2`, because their member counts are small and they appear often enough to validate across many files.
3. Leave videos out of the Data tab unless the user wants a media inventory there; they are not binary config schemas.

## 2026-06-27 Interactive LogicController Body Follow-up

`Core_InteractiveLogicControllerComponentData` is now decoded as the next exact mixed Interactive component body.

Evidence and method:

1. Rechecked public sources for Endfield component schemas and MemoryPack union/member behavior. No public Endfield schema was found for `Core_InteractiveLogicControllerComponentData` or `Core_InteractiveAudioData`; local byte validation remains the source of truth, with upstream MemoryPack only used for serializer context.
2. Queried local `reports/option_flow_runtime_metadata.json`. The runtime metadata exposes `Beyond.Gameplay.Core.InteractiveLogicControllerComponentData` with fields `logicType` and `propertyList`, and its `ForMemoryPack` wrapper has setters `set___logicType__` and `set___propertyList__`.
3. Tested the initial hypothesis that `propertyList` was a list of five-field `InteractivePropertyData` rows. This failed on all 40 payloads: after the `logicType` int, the first item marker was `2`, matching the shared property-map entry shape, not the five-member `InteractivePropertyData` object.
4. Corrected the layout to: member count `2`, `logicType` i32, then a shared Interactive property map (`count`, two-member key/value entries, and two-member typed value arrays). This parsed all 40 observed LogicController component bodies with zero failures and handed off cleanly to the next component tag or end of component-list walk.
5. Promoted `INTERACTIVE_LOGIC_CONTROLLER_COMPONENT_TAG`, `INTERACTIVE_LOGIC_CONTROLLER_MEMBER_COUNT`, and `parse_interactive_logic_controller_component` in `scripts/build_data_index.py`. The component walker now parses LogicController bodies after TriggerObserver/property-map bodies, records all parsed LogicController components, and includes compact `logicType=` / `logicKeys=` details when the summary budget allows.
6. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/index.json` and `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- `Core_InteractiveLogicControllerComponentData` bodies decoded: 40 total; 17 are first-payload bodies.
- Component walker parsed-payload distribution per template is now `0:104`, `1:96`, `2:53`, `3:16`, `4:2`.
- Parsed body totals across component lists: 120 TriggerObserver bodies, 85 one-property-map bodies, and 40 LogicController bodies.
- LogicController `propertyList` counts are `1:27`, `3:11`, `6:1`, and `5:1`.
- Stable LogicController property keys are led by `logic_type` in all 40 rows, with additional observed keys `state`, `destroy_self`, `index`, `is_completed`, `is_enabled`, `max_count`, `is_locked`, `is_do_once`, and `target_list`.
- Top remaining stop component is now `Core_InteractiveAudioData:2` with 51 stops. Its payloads start with a zero field followed by a nested 13-member audio object, so it needs a separate parser pass rather than speculative skipping.

Adjusted next parser plan:

1. Decode `Core_InteractiveAudioData:2` next. Start by proving the leading zero field and the nested 13-member audio object, then recover the audio-event row layout from local metadata (`InteractiveAudioComponent`, `InteractiveAudioSetting`, audio trigger/mount-point enums) and byte samples.
2. Keep common perform/click trigger/trigger zone as the next queue after audio unless the audio object broadens too much.
3. Revisit enum naming later. Numeric `logicType` values are exact, but mapping them to `EInteractiveLogicType` names should be validated against enum value metadata or runtime constants before exposing names in WebUI summaries.

## 2026-06-27 Interactive Audio Body Follow-up

`Core_InteractiveAudioData` is now decoded as an exact component body in the Interactive component walker.

Evidence and method:

1. Rechecked public search for Endfield `InteractiveAudioData`, `InteractiveAudioSetting`, and `Core_InteractiveAudioData`; no public game schema surfaced. Upstream MemoryPack remains useful only as serializer context.
2. Used the repo-local IL2CPP metadata parser against `global-metadata.dat` to recover the relevant type records. `Beyond.Gameplay.Core.InteractiveAudioData` has field `audioData`; its `ForMemoryPack` wrapper has `set___audioData__`. The nested `Beyond.Gameplay.Core.InteractiveAudioComponentData` has 13 fields, and the wrapper setter names expose the serialized members needed for this pass: `audioNameDict`, `customAudioData`, `openAudio`, and the 10 `use*Stencil` / `useDynamicLevel` booleans.
3. Validated the outer component layout as member count `2`: a zero `u32` prefix field, then a nested audio data object with member count `13`.
4. Validated the nested layout across every reachable audio component: `audioNameDict` is a count followed by rows of `state` i32 plus an audio-event string list; `customAudioData` is a count followed by three-member rows (`event`, `name`, `note`); the tail is 11 one-byte booleans in the observed MemoryPack setter order.
5. Promoted `INTERACTIVE_AUDIO_COMPONENT_TAG`, `INTERACTIVE_AUDIO_MEMBER_COUNT`, `INTERACTIVE_AUDIO_DATA_MEMBER_COUNT`, audio trigger-state names, boolean field names, and `parse_interactive_audio_component` in `scripts/build_data_index.py`. The component walker now records all parsed audio components and compactly exposes `audioStates=`, `customAudio=`, and first audio event ids when the summary budget allows.
6. Regenerated with `python scripts/build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/index.json` and `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- `Core_InteractiveAudioData` bodies decoded: 51 total; 11 are first-payload bodies.
- Parsed body totals across component lists: 121 TriggerObserver bodies, 85 one-property-map bodies, 40 LogicController bodies, and 51 Audio bodies.
- Component walker parsed-payload distribution per template is now `0:93`, `1:71`, `2:79`, `3:25`, `4:3`.
- Audio `audioNameDict` counts are `2:19`, `1:12`, `3:9`, `0:8`, and `4:3`. `customAudioData` counts are `0:35`, `2:5`, `1:4`, `3:2`, `4:2`, `5:1`, `6:1`, and `7:1`.
- Top audio trigger states are `StartUp`, `Stop`, `Interact`, `Active`, `Destroy`, `Idle`, `EnterArea`, and `NotActive`; this mapping is corroborated by the local enum field order and event names such as enter/leave/idle/destroy/interact.
- `openAudio` is true in all 51 parsed bodies. Other true tail flags include `useWorkStencil` 24, `useCustomStencil` 16, `useInteractStencil` 11, `useActiveStencil` 10, `useDestroyStencil` 7, `useTiggerStencil` 4, `useCollectStencil` 3, and `useRepairStencil` 1.
- Audio is no longer the top stop component. The current stop queue is led by `Core_InteractiveCommonPerformComponentData:3` 59, `Core_ClickTriggerComponentForIntData:3` 30, `Core_PlayerInteractPerformComponentData:1` 26, `Core_TriggerZoneComponentForIntData:3` 21, `tag_0x003f:1` 18, `Core_AbilitySystemForIntData:36` 15, and `Core_HittableComponentForIntData:3` 12.

Adjusted next parser plan:

1. Decode `Core_ClickTriggerComponentForIntData:3` or `Core_TriggerZoneComponentForIntData:3` next. Both are trigger-like three-member bodies and likely reuse the shared property-map grammar around a smaller trigger-specific wrapper.
2. If those branch into behavior graphs, switch to `Core_PlayerInteractPerformComponentData:1` because it is one-member and may be a smaller perform/property-map variant despite failing the plain map shape.
3. Keep `Core_InteractiveCommonPerformComponentData:3` in the queue, but treat it as broader because it now becomes the most frequent stop after audio and likely references multiple perform/action payload styles.

## 2026-06-27 Additional One-Member Component Map Pass

The moved data is now back under `export_full/structured/StreamingAssets/Data`. The `Json/` rebuild still covers 81,735 files (667.6 MiB) and `StreamingAssets/Data` currently has only `Json/` and `Video/` folders.

Evidence and method:

1. Re-ran public searches for `ClickTriggerComponentForIntData`, `TriggerZoneComponentForIntData`, `BaseTriggerComponentForIntData`, and related MemoryPack schema terms. No public Endfield component schema surfaced, so local metadata and byte handoff validation remain the source of truth.
2. Re-queried local IL2CPP metadata. `ClickTriggerComponentForIntData` and `TriggerZoneComponentForIntData` own no fields and inherit `BaseTriggerComponentForIntData`; the base type exposes `propertyStateData` and `triggerBehaviourBase`. `PropertyStateData` has 20 fields, and trigger condition payloads point at `ModelViewStateController.TriggerCondition`-style 9-member records plus nested condition/property data.
3. Checked local DummyDlls with repo-local Mono.Cecil. The stubs in `tools/DummyDll` do not contain these concrete trigger types or useful MemoryPack order attributes, so they cannot replace byte-order inference.
4. Tested `Core_ClickTriggerComponentForIntData:3` and `Core_TriggerZoneComponentForIntData:3`. Both start with a null u32 field, then a list count, then 20-member property-state records. The records have a stable prefix (`triggerId`, a small trigger-type byte, condition expression string, condition count), but the tail contains internal behavior/property-map blocks such as `ff 0x0154 + map`, `ff 0x017b + map`, and `ff 0x010f + map`. A naive prefixed-map scan produced false positives across component boundaries, so no trigger parser was promoted yet.
5. In parallel, validated remaining member-count-1 stop components against the already proven shared Interactive property-map grammar. Only all-pass tags were promoted to `INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS`: `0x0006`, `0x002f`, `0x0035`, `0x0044`, `0x0064`, `0x0066`, `0x007f`, `0x008d`, `0x008e`, `0x00bc`, `0x00d0`, `0x00d3`, `0x00d5`, `0x00f6`, and `0x00f9`. Partial/failing shapes such as `tag_0x003f`, `Core_PlayerInteractPerformComponentData`, `tag_0x0027`, `tag_0x002e`, `tag_0x0085`, `tag_0x00e7`, and `ScannableTraceComponentData` remain stop points.
6. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- Parsed-payload distribution across 271 templates: `0:93`, `1:61`, `2:77`, `3:22`, `4:17`, `5:1`.
- Parsed body totals in the component-list walk: 124 TriggerObserver property-map bodies, 116 one-member property-map bodies, 44 LogicController bodies, and 51 Audio bodies.
- The current stop queue is `none` 65, `Core_InteractiveCommonPerformComponentData:3` 62, `Core_ClickTriggerComponentForIntData:3` 31, `Core_PlayerInteractPerformComponentData:1` 26, `Core_TriggerZoneComponentForIntData:3` 21, `tag_0x003f:1` 18, `Core_AbilitySystemForIntData:36` 15, `Core_HittableComponentForIntData:3` 12, and `tag_0x00ba:5` 11.

Adjusted next parser plan:

1. Finish the base trigger parser only after the `PropertyStateData` tail can be consumed without boundary scans that mistake property-value null tails for internal behavior prefixes.
2. Query or derive the internal `triggerBehaviourBase` union/formatter tags (`0x010f`, `0x0125`, `0x0154`, `0x017b`, and related observed values) before promoting Click/Zone parsing.
3. If trigger tail decoding remains broad, switch to a smaller failing family next: `Core_HittableComponentForIntData:3`, `tag_0x003f:1`, or `Core_PlayerInteractPerformComponentData:1`, but keep the same rule that every promoted parser must validate across all observed handoffs.

## 2026-06-27 Hittable Component Body Pass

`Core_HittableComponentForIntData` is now decoded as an exact component body in the Interactive component walker.

Evidence and method:

1. Searched public web results for `Core_InteractiveCommonPerformComponentData`, `PlayerInteractPerformComponentData`, `Core_HittableComponentForIntData`, and related MemoryPack terms. No public Endfield schemas surfaced, so the pass used local IL2CPP metadata plus byte-level validation.
2. Queried local IL2CPP metadata. `Beyond.Gameplay.Core.HittableComponentForIntData` exposes `enableExtraCheck` and `battleShapeData`, and its MemoryPack wrapper has setters `set___battleShapeData__` and `set___enableExtraCheck__`. `Beyond.Gameplay.ColliderShapeData` exposes a 16-field collider-shape object and a matching MemoryPack wrapper.
3. Tested all 12 Hittable stop payloads. Each begins with a 16-entry shared Interactive property map containing stable keys such as `shape`, `extent`, `center`, `radius`, `height`, `load_from_table`, `active_skill`, `passive_skill`, `skill_blackboard`, `battle_enable_extra_check`, `bomb_check_ignore_raycast`, `use_self_blackboard`, `play_battle_hit_effect`, `trigger_hit_cd`, `disable_added_buff`, and `skill_blackboard_self`.
4. After that property map, every payload has a fixed 80-byte `ColliderShapeData` blob whose first byte is member count `16` and whose body includes nullable-string markers and numeric collider data. Full field naming inside this compact blob remains deferred, but its length and object marker are stable.
5. The final four bytes before the next component are `00 00 00 00` or `00 00 00 01`; this is treated as the `enableExtraCheck` flag from metadata and validated by exact next-component handoff. Nine Hittable bodies have it false and three have it true.
6. Promoted `parse_interactive_hittable_component` in `scripts/build_data_index.py`. The component walker now records Hittable property-map keys, fixed collider blob metadata, and the `enableExtraCheck` flag.
7. Probed `Core_InteractiveCommonPerformComponentData:3` as the next larger target. Its first segment parses as a two-entry property map (`use_dynamic_res`, `dynamic_entity_id`), but the remaining tail contains state/lock strings and mixed payload bytes, not a simple flag or clean boundary. No CommonPerform parser was promoted in this pass.
8. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- Hittable bodies decoded: 12 total, with `enableExtraCheck` false in 9 and true in 3.
- Parsed body totals across component lists: 124 TriggerObserver property-map bodies, 117 one-member property-map bodies, 55 Audio bodies, 44 LogicController bodies, 22 zero-member bodies after the first payload, and 12 Hittable bodies.
- Component walker parsed-payload distribution per template is now `0:86`, `1:62`, `2:78`, `3:26`, `4:17`, `5:2`.
- The current stop queue is `none` 66, `Core_InteractiveCommonPerformComponentData:3` 63, `Core_ClickTriggerComponentForIntData:3` 31, `Core_PlayerInteractPerformComponentData:1` 26, `Core_TriggerZoneComponentForIntData:3` 21, `tag_0x003f:1` 18, `Core_AbilitySystemForIntData:36` 15, `tag_0x00ba:5` 12, and newly exposed `tag_0x0055:1` 6.

Adjusted next parser plan:

1. Continue CommonPerform only after resolving its post-property-map state/lock tail; the first map alone is not enough for a safe parser.
2. `tag_0x003f:1` remains promising but needs an extension for the one failing row before it can join the all-pass property-map family.
3. Newly exposed tags from Hittable (`0x0055`, `0x0070`, and `0x00bb`) should be named from union formatter evidence before promotion where possible.

## 2026-06-27 Interactive Property Value String-Tail Pass

The shared Interactive property-map grammar now supports string-tail property values, which unlocked several one-member component bodies that previously looked like malformed maps.

Evidence and method:

1. Rechecked public web search for `tag_0x003f`, `InteractiveCommonPerformComponentData.propertyDataList`, `Beyond.Gameplay.Core.InteractiveCommonPerformComponentData`, and `Core_PlayerInteractPerformComponentData`; no public Endfield schemas surfaced. The pass stayed local: byte validation plus IL2CPP metadata where class names were known.
2. The failed one-member bodies all had valid property-map headers but failed inside `InteractivePropertyValue` rows after an item member count of `2`. The old parser always read the second item field as an i32 tail. Byte samples showed value types `7` and `8` store a UTF-8 string after the 64-bit value slot instead, for examples `CharIntPerform_Ipad`, `ForgeIron`, `item_liquid_water`, `P_shards_chaodiao+1_001_01`, and `P_fxint_s_tracelight_801`.
3. Extended `parse_interactive_component_property_value` so value types `7` and `8` read a nullable length-prefixed UTF-8 string tail. Numeric/boolean/float value types still use the old i32 tail path. Property maps now aggregate `stringTailCounts` alongside numeric `tailCounts`.
4. Revalidated every current member-count-1 stop payload. Promoted only all-pass tags to `INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS`: `0x0027`, `0x002a`, `0x002e`, `0x003f`, `0x0055`, `0x0070`, `0x0085`, `0x00aa` (`Core_PlayerInteractPerformComponentData`), `0x00dd`, `0x00de`, and `0x00fc` (`ScannableTraceComponentData`). `0x00e7` still fails and remains a stop point.
5. This also decoded all 26 observed `Core_PlayerInteractPerformComponentData` bodies as one-member property maps. Their common keys include `animation_key`, `position`, `rotation`, `wait_time`, and `available_list`, with string-tail perform ids such as `CharIntPerform_Ipad`, `CharIntPerform_QuickFix`, and `CharIntPerform_Fix`.
6. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- Component walker parsed-payload distribution per template is now `0:82`, `1:51`, `2:57`, `3:46`, `4:25`, `5:9`, `7:1`.
- Parsed body totals across component lists: 188 one-member property-map bodies, 124 TriggerObserver property-map bodies, 64 Audio bodies, 44 LogicController bodies, 22 zero-member bodies after first payload, and 13 Hittable bodies.
- Top string tails include empty strings, `CharIntPerform_Ipad`, `CharIntPerform_QuickFix`, `CharIntPerform_Fix`, `ForgeIron`, `DoodadGrade`, `battle_cannon_1_dg002`, `item_liquid_water`, and several effect/system ids.
- The current stop queue is `none` 76, `Core_InteractiveCommonPerformComponentData:3` 69, `Core_ClickTriggerComponentForIntData:3` 45, `Core_AbilitySystemForIntData:36` 33, `Core_TriggerZoneComponentForIntData:3` 23, `tag_0x00ba:5` 17, `tag_0x0013:3` 4, plus singletons `tag_0x001f:5`, `tag_0x00e7:1`, `tag_0x00bb:5`, and `tag_0x00ce:3`.

Adjusted next parser plan:

1. Attack `Core_InteractiveCommonPerformComponentData:3` again with the richer property-value parser. Its first property-map segment now parses, but the remaining state/lock tail still needs a separate structure.
2. `tag_0x00ba:5` and `tag_0x0013:3` are now higher-value smaller mixed families exposed after the property-map pass.
3. Keep `0x00e7` out of the property-map family until its later string/list field is understood; it still fails even with string-tail value types.

## 2026-06-27 CommonPerform Component Body Pass

`Core_InteractiveCommonPerformComponentData` is now decoded as an exact component body in the Interactive component walker.

Evidence and method:

1. Searched public web results for `Core_InteractiveCommonPerformComponentData`, `InteractivePerformPropertyData`, and `syncGameplayLock`. No public Endfield schema surfaced, so local IL2CPP metadata and byte handoff validation remained the source of truth.
2. Queried local `global-metadata.dat` with `tools/endfield-il2cpp/catalog_option_flow_metadata.py`. `Beyond.Gameplay.Core.InteractiveCommonPerformComponentData` exposes `propertyDataList` and `syncGameplayLock`; `InteractivePerformPropertyData` exposes `propertyName`, `propertyType`, and `isProperty`; `EPropertyType` names the observed enum values as `Int`, `Float`, `String`, `Ulong`, `Bool`, and `Trigger`.
3. The first attempted tail layout, `propertyType byte -> propertyName string -> isProperty bool`, parsed only 29 of 69 current handoffs. The failures were useful: rows such as `InTriggerVolume` and `LockedByGameplayLock` ended with `04 00 00 00`, showing that the trailing field is a 32-bit enum value, not a one-byte boolean.
4. The validated layout is: shared dynamic property map, counted `propertyDataList`, each row as member count `3`, one-byte `isProperty`, UTF-8 `propertyName`, i32 `propertyType`, then one final one-byte `syncGameplayLock`. This parsed all 69 current CommonPerform bodies and landed exactly on the next component union tag for every handoff.
5. Promoted `parse_interactive_common_perform_component` in `scripts/build_data_index.py`. The component walker now records dynamic property-map keys, perform property row names/types, `isProperty` counts, and `syncGameplayLock`.
6. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- CommonPerform bodies decoded: 69 total. Their dynamic property map has `use_dynamic_res` and `dynamic_entity_id` in all 69 bodies, plus `model_id` in 3 bodies.
- `propertyDataList` row-count distribution: `1:24`, `0:20`, `2:11`, `3:7`, `4:2`, `8:2`, `6:2`, `7:1`.
- Perform property types: `Bool:63`, `Int:20`, `Trigger:17`, and `Float:10`. Top names include `LockedByGameplayLock`, `state`, `Progress`, `IsHit`, `InTriggerVolume`, `IsMoving`, `Distance`, `isDead`, and `PlayerStepOn`.
- `syncGameplayLock` is false in 57 bodies and true in 12 bodies.
- Parsed body totals across component lists: 232 one-member property-map bodies, 131 TriggerObserver property-map bodies, 69 CommonPerform bodies, 66 Audio bodies, 44 LogicController bodies, 23 zero-member bodies after first payload, and 14 Hittable bodies.
- The current stop queue is `none` 94, `Core_ClickTriggerComponentForIntData:3` 58, `Core_AbilitySystemForIntData:36` 36, `Core_TriggerZoneComponentForIntData:3` 26, `tag_0x00ba:5` 20, `tag_0x0062:2` 8, `tag_0x0013:3` 7, `tag_0x00ce:3` 4, `tag_0x00bb:5` 3, and `tag_0x0087:1` 3.

Adjusted next parser plan:

1. Revisit `Core_ClickTriggerComponentForIntData:3` and `Core_TriggerZoneComponentForIntData:3`; they are now the largest exact stop families, but their internal trigger-behavior union tags still need a non-scanning parse.
2. Investigate `Core_AbilitySystemForIntData:36` with metadata first. Its high member count makes byte guessing risky, but it is now the second largest stop family.
3. Map new exposed unknown tags such as `0x0062`, `0x00ce`, `0x0087`, and `0x00ba` against the union formatter table before promoting parsers by shape alone.

## 2026-06-27 Trigger PropertyStateData Prefix Probe

`Core_ClickTriggerComponentForIntData` and `Core_TriggerZoneComponentForIntData` were probed after CommonPerform exposed them as the largest remaining stop families. No parser was promoted in this pass.

Evidence and method:

1. Searched public web results for `Core_ClickTriggerComponentForIntData`, `Core_TriggerZoneComponentForIntData`, `BaseTriggerComponentForIntData`, `PropertyStateData`, and `triggerBehaviourBase`. No public Endfield schema surfaced.
2. Queried local IL2CPP metadata. `ClickTriggerComponentForIntData` and `TriggerZoneComponentForIntData` have no direct fields and inherit `BaseTriggerComponentForIntData`, which exposes `propertyStateData` and `triggerBehaviourBase`. `PropertyStateData` has 20 fields, including `triggerId`, `triggerType`, `conditionExpression`, `conditions`, option strings, timing/flag fields, and expected-value fields.
3. Byte samples show the trigger component body starts with a leading null u32 field, then a counted `propertyStateData` list. Each row starts with member count `20`, then a stable prefix: `triggerId` i32, one-byte `triggerType`, `conditionExpression` string, and a counted condition list.
4. Nested condition items usually begin with marker/member count `9` and include expression symbols such as `A`/`B` plus a property key string such as `is_locked` or `state`. A fixed-offset condition skipper handled many rows, but variants exist: some conditions shift the key-string offset, and one rope-port condition includes an additional embedded string/value form.
5. The prototype parsed the deterministic prefix for 67 of 84 current Click/Zone stop components and failed 17. Top parsed condition keys were `state`, `is_locked`, empty string, `A`, `allow_turnon_inside`, and `done_once`. Because it could not consume all rows and land on `triggerBehaviourBase` reliably, no trigger parser was promoted.

Adjusted next parser plan:

1. Do not parse Click/Zone by scanning for the next internal `ff + tag` marker; previous scans can mistake null/value tails for boundaries.
2. Before retrying, derive the 9-member condition item variants and the `PropertyStateData` tail after `optionName`/`optionIcon`, then validate row ends across multi-row payloads.
3. Switch to smaller newly exposed stop families (`tag_0x0062:2`, `tag_0x00ce:3`, or `tag_0x0087:1`) for the next promotion attempt.

## 2026-06-27 Union Names And One-Member Map Promotion Pass

Several newly exposed stop tags were named from the existing `tmp/memorypack_union_tags.json` BaseComponentData formatter table, and another small batch of one-member component bodies was promoted to the shared Interactive property-map parser.

Evidence and method:

1. Searched public web results for `tag_0x0062`, `InteractiveDoor`, `Core_InteractiveDoor`, and `InteractiveDoorCommonComponentData`; no public schema or tag table surfaced.
2. Tried to rerun `scripts/story_recovery/build_memorypack_union_tag_audit.py` into `tmp/`, but the current installed binary/code-registration pairing failed with a `VA outside image` error. Used the earlier local artifact `tmp/memorypack_union_tags.json`, which contains the extracted `Beyond_Gameplay_BaseComponentData` union table.
3. Recovered names for the newly exposed stop tags: `0x0062` = `Core_InteractiveDynamicAINavComponentData`, `0x00ba` = `Core_ShowGuideComponentData`, `0x00bb` = `Core_ShowGuideWithConditionComponentData`, `0x0013` = `Core_AttackTriggerComponentForIntData`, `0x00ce` = `Core_StepOnTriggerComponentForIntData`, `0x006b` = `Core_InteractiveManualMovePlatformComponentData`, `0x0075` = `Core_InteractiveRunePointComponentData`, `0x0087` = `Core_InteractiveWaterSwitchComponentData`, `0x00df` = `Core_WaterProgressDriveCurveMovementComponentData`, `0x00e0` = `Core_WaterVolHeightMarkerComponentData`, `0x00e6` = `CraneContainerComponentData`, `0x00e7` = `CraneTowerComponentData`, `0x00e9` = `DungeonExitComponentData`, `0x00f5` = `InteractiveMovingPlatClientOnlyComponentData`, and `0x00f8` = `InteractiveStainComponentData`.
4. Queried local metadata for `Core_InteractiveDynamicAINavComponentData`. It exposes `obstacleType`, but observed bodies have member count `2` and contain nested state/property blocks after a fixed-looking AINav prefix. Because the body is not a simple one-field enum or fixed 73-byte record across all samples, no `0x0062` parser was promoted.
5. Revalidated member-count-1 bodies against the shared property-map grammar. Promoted only all-pass tags: `0x0049` (`Core_HeightZeroMarkerComponentData`), `0x006b`, `0x0075`, `0x0087`, `0x00df`, `0x00e0`, `0x00e6`, `0x00f5`, and `0x00f8`. Kept failing tags out: `0x005b` (`Core_InteractiveCoolerUnitComponentData`), `0x00e7` (`CraneTowerComponentData`), and `0x00e9` (`DungeonExitComponentData`).
6. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- Parsed body totals across component lists: 251 one-member property-map bodies, 131 TriggerObserver property-map bodies, 69 CommonPerform bodies, 66 Audio bodies, 44 LogicController bodies, 23 zero-member bodies after first payload, and 14 Hittable bodies.
- The current stop queue is `none` 102, `Core_ClickTriggerComponentForIntData:3` 58, `Core_AbilitySystemForIntData:36` 36, `Core_TriggerZoneComponentForIntData:3` 26, `Core_ShowGuideComponentData:5` 22, `Core_InteractiveDynamicAINavComponentData:2` 8, `Core_AttackTriggerComponentForIntData:3` 7, `Core_StepOnTriggerComponentForIntData:3` 4, `Core_ShowGuideWithConditionComponentData:5` 3, plus singletons `Core_CharacterMovementComponentData:5`, `CraneTowerComponentData:1`, `DungeonExitComponentData:1`, `Core_InteractiveModelLevelUpComponentData:2`, and `Core_InteractiveCoolerUnitComponentData:1`.

Adjusted next parser plan:

1. `Core_ShowGuideComponentData:5` is now the largest non-trigger smaller target; inspect metadata before parsing because it likely has condition/list fields.
2. `Core_InteractiveDynamicAINavComponentData:2` needs its nested state/property blocks mapped before promotion; a fixed prefix alone is not enough.
3. Trigger families remain high count but blocked on the 9-member condition variants and full `PropertyStateData` row tail.


## 2026-06-27 ShowGuide Component Body Pass

`Core_ShowGuideComponentData` and `Core_ShowGuideWithConditionComponentData` are now decoded as exact five-member component bodies in the Interactive component walker.

Evidence and method:

1. Rechecked public web searches for `Core_ShowGuideComponentData`, `ShowGuideWithConditionComponentData`, `Beyond.Gameplay.Core.ShowGuideComponentData`, `guide_id`, and `quest_id`; no public schema surfaced. The pass stayed local: installed IL2CPP metadata plus byte-level component-list validation.
2. Queried local `global-metadata.dat`. The concrete `Beyond.Gameplay.Core.ShowGuideComponentData` and `ShowGuideWithConditionComponentData` types expose only `get_interactiveComponentType` and `.ctor`; their generated ForMemoryPack wrappers expose formatter methods but no field setter names. That made the field names byte-inferred rather than metadata-named.
3. Bounded samples showed every stop payload begins with the shared Interactive property-map grammar. Plain ShowGuide rows have eight keys (`shape`, `center`, `size`, `radius`, `guide_id`, `id`, `wiki_id`, `duration`); the condition variant has 13 keys and swaps in `quest_id` plus second-guide fields.
4. After the property map, all 25 bodies validated as exactly 29 fixed bytes: `Vector3 center`, `float radius`, one-byte `shape`, and `Vector3 size`. For non-last components this landed exactly on the next union tag, including `0x005a` CommonPerform, `0x0051` Audio, `0x0066` one-property-map, and trigger/ability stops. For last components it landed at the component-list end before the remaining inherited template fields.
5. Promoted `parse_interactive_show_guide_component` in `scripts/build_data_index.py`. The component walker records `componentShowGuideComponents`, compact `showGuideMap=` / `guideShape=` summary details, and `showGuideBoundsData` parsed rows.
6. The new handoffs exposed two one-member tags, `0x00eb` and `0x0026`. Both parsed fully as shared property maps and either landed on a valid next component or the component-list end, so they were added to `INTERACTIVE_SINGLE_PROPERTY_MAP_COMPONENT_TAGS` without assigning names.
7. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_Interactive.json`.

Observed counts after regeneration:

- ShowGuide bodies decoded: 25 total (`Core_ShowGuideComponentData` 22, `Core_ShowGuideWithConditionComponentData` 3). Shape bytes are `2:17`, `0:5`, and `1:3`.
- Parsed body totals across component lists: 262 one-member property-map bodies, 131 TriggerObserver property-map bodies, 75 CommonPerform bodies, 68 Audio bodies, 44 LogicController bodies, 25 ShowGuide bodies, 23 zero-member bodies after first payload, and 14 Hittable bodies.
- CommonPerform grew to 75 bodies after ShowGuide exposed downstream components. `propertyDataList` row counts are `1:25`, `0:22`, `2:11`, `3:9`, `4:3`, `8:2`, `6:2`, `7:1`; type counts are `Bool:70`, `Int:21`, `Trigger:19`, and `Float:11`; `syncGameplayLock` is false in 62 and true in 13.
- The current stop queue is `none` 118, `Core_ClickTriggerComponentForIntData:3` 59, `Core_AbilitySystemForIntData:36` 37, `Core_TriggerZoneComponentForIntData:3` 30, `Core_AttackTriggerComponentForIntData:3` 10, `Core_InteractiveDynamicAINavComponentData:2` 8, `Core_StepOnTriggerComponentForIntData:3` 4, plus singletons `Core_CharacterMovementComponentData:5`, `CraneTowerComponentData:1`, `DungeonExitComponentData:1`, `Core_InteractiveModelLevelUpComponentData:2`, and `Core_InteractiveCoolerUnitComponentData:1`.

Adjusted next parser plan:

1. The trigger families remain the largest queue, but they are still blocked on full `PropertyStateData` rows and condition variants; do not promote a scanner-based parser.
2. `Core_AbilitySystemForIntData:36` is now the next large non-trigger family; inspect metadata before byte work because 36 members make blind parsing risky.
3. `Core_InteractiveDynamicAINavComponentData:2` remains a smaller target with eight samples, but it needs its nested state/property blocks understood before promotion.


## 2026-06-27 DynamicAINav Prefix Probe

`Core_InteractiveDynamicAINavComponentData` was probed after the ShowGuide pass left it as the largest small non-trigger family. No parser was promoted in this pass.

Evidence and method:

1. Searched public web results for `Core_InteractiveDynamicAINavComponentData`, `InteractiveDynamicAINavComponentData`, and `Beyond.Gameplay.Core.InteractiveDynamicAINavComponentData`; no public schema surfaced.
2. Queried local `global-metadata.dat`. The concrete type exposes one direct field, `obstacleType`, and its generated MemoryPack wrapper exposes `set___obstacleType__`.
3. All eight current stop samples have member count `2` and are the final component in their component lists. The first eight payload bytes are stable enough to suggest an empty/zero base field followed by `obstacleType` as an i32 (`0` or `1`).
4. The bytes after that prefix immediately resemble inherited `InteractiveTemplateData` tail fields in some files and property-like strings such as `state` or `destroy_self` in others, but because every sample is last-in-list there is no exact next-component handoff. Without parsing the remaining inherited template fields, an 8-byte body and a longer base-body interpretation cannot be distinguished safely.

Adjusted next parser plan:

1. Do not promote `Core_InteractiveDynamicAINavComponentData` on the prefix alone.
2. Either find a non-last DynamicAINav sample in a later export, or first decode the post-`componentList` inherited `InteractiveTemplateData` fields so body length can be validated against the template tail.
3. For immediate parser gains, switch back to families that have real next-component handoffs, or work on trigger `PropertyStateData` variants with full row-end validation.


## 2026-06-27 LevelScript Action Map Details Pass

`Json/LevelScriptData/**/*.json` now exposes compact action-map list boundaries and UID record samples in the WebUI Data index.

Evidence and method:

1. Searched public web results for `Arknights Endfield LevelScriptData MemoryPack`, `LevelScriptData Endfield MemoryPack`, and `Beyond.Gameplay LevelScriptData ForMemoryPack`; no public schema surfaced. This pass used local helper evidence from prior GameAssembly/metadata work plus byte validation over the export corpus.
2. Reused the existing `ActionSerializedMap` evidence in `scripts/story_builder/levelscript_binary.py`: generated setter order is `actionList`, `getterList`, then `headerList`, with the first list count in the top-level `actionMap` header and later list counts immediately before the next UID record block.
3. Added a lightweight UID/string scanner to `levelscript_binary.py` so the Data index can feed existing `levelscript_action_map_membership` and `decode_levelscript_record_payload` without importing the heavier Story binding module. The scanner recognizes the two established UID record layouts (`fa` and `plain`), attaches tagged `0x04` strings plus plain length-prefixed ASCII strings, and keeps only compact record samples/counts.
4. Full-corpus validation over all 3,658 LevelScriptData files completed with zero helper errors. Action maps are `present` in 3,285 files and `absent-marker` in 373 files. UID-record count distribution starts with `0:641`, `3:408`, `5:255`, `4:234`, `2:209`, `6:167`, `7:118`, `8:92`, `1:88`, and `9:85`.
5. The serialized list splitter finds `actionList` in all 3,285 present maps, `headerList` in 2,826 files, and `getterList` in 1,362 files, with another 1,465 maps using the validated `getterList` omitted/empty before a header-like final block pattern. The main non-error residual statuses are null/unanchored or unknown list markers, so those are reported as statuses rather than forced into a list.
6. Promoted the compact details into `scripts/build_data_index.py` summaries: LevelScript rows now show `uidRecords=`, `lists=actionList=...,getterList=...,headerList=...`, and action-list `root`/`linked` membership counts where available.
7. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returns HTTP 200 for `data/game_data/groups/Json_LevelScriptData.json`.

Observed output after regeneration:

- `Json_LevelScriptData.json` contains 3,658 entries and the endpoint response is about 3.8 MB.
- `lists=` appears in 3,285 generated summaries, matching the count of present action maps.
- `uidRecords=` appears in all 3,658 generated summaries; files with absent action maps or no decoded UID records report zero as appropriate.
- `actionMembership=` appears in 2,842 summaries where UID records can be assigned to serialized action-map lists.
- Top sampled payload hint labels include `action-header-prefix`, `event-args-continuation`, `trigger-volume-slot-gate`, `multi-scalar-control`, `actionbase-set-int`, `float-property-signal`, `property-key-control`, `boolean-or-flag-check`, and `local-record-ref-list`.

Adjusted next parser plan:

1. Keep LevelScript action-map details compact in the Data index; full control-flow semantics still belong in the Story builder/audit path, not generic Data browsing.
2. The next LevelScript improvement would be validating list-boundary residuals (`null-marker-or-unanchored`, `unknown-marker`, and `outsideSerializedActionMap`) against the post-actionMap top-level fields, but avoid promoting those records into lists without exact byte boundaries.
3. For binary JSON coverage outside LevelScript, revisit large shallow families such as BuffData/SkillData nested fields, or continue the Interactive trigger `PropertyStateData` work only with full row-end validation.


## 2026-06-28 SkillData Type-Hint And ID Marker Pass

`Json/BuffData/*.json` and `Json/SkillData/*.json` now expose stronger, still-conservative marker and schema evidence in the Data index.

Evidence and method:

1. Rechecked public web searches for `Arknights Endfield BuffData SkillData MemoryPack schema`, `BuffData Endfield`, `SkillData Endfield MemoryPack`, and `Beyond.Gameplay BuffData SkillData`. No public schema/source surfaced, so this pass stayed local.
2. The current moved export root has only `export_full/structured/StreamingAssets/Data/Json` plus `Data/Video`; the older Streaming/Irradiance/ExtendData folders are not present in this tree, so there were no extra non-JSON Data folders to parse in this pass.
3. Queried the cached local metadata JSON at `tmp/model_table_metadata.json`. It contains `Beyond_Gameplay_Core_SkillDataForMemoryPack` with setter parameter types for all 45 serialized fields. The cache did not contain `Beyond_Gameplay_Core_BuffDataForMemoryPack`, so BuffData remains limited to the previously recovered field-name schema and byte markers.
4. Promoted a generated SkillData top-level type map into `scripts/build_data_index.py`: 30 fields are primitive/enum/string/vector-like (`System.Boolean`, `System.Int32`, `System.Single`, `System.String`, `UnityEngine.Vector3`, and enum-like value fields), while 15 fields remain complex/list bodies such as `ActionGroupData`, `buffs`, `blackboard`, `GameplayTagList`, `SwitchToBuffConfig`, and targeting/tag-query settings.
5. Added exact length-prefixed UTF-8 marker counting for BuffData ids and SkillData ids. This distinguishes exact `<u32 len><id>` markers from substring hits inside longer refs such as `buff_<skillId>`. The Data index now reports `idMarkers=` and first `idOffsets=` in the compact sample field.
6. Did not promote a full SkillData body parser: the first serialized field is complex `ActionGroupData`, and nested action/buff/cast/blackboard structures still need formatter-specific skippers before a byte-exact forward parse is safe.
7. Regenerated `python scripts\build_data_index.py --groups Json`; the existing WebUI server returned HTTP 200 for `data/game_data/index.json` and `data/game_data/groups/Json_SkillData.json`.

Observed output after regeneration:

- `Json_BuffData.json` contains 2,291 rows. Exact id marker distribution is `1:2193`, `2:63`, `3:29`, `4:4`, `7:1`, and `6:1`.
- `Json_SkillData.json` contains 2,083 rows. Exact id marker distribution is `1:2030`, `3:27`, `2:20`, `5:4`, `9:1`, and `4:1`.
- SkillData summaries now say `field types recovered (30 primitive/enum/string/vector, 15 complex/list)`, and samples include `typedFields=30/45`, `idOffsets=...`, and compact `schemaTypes=skillId:String,skillName:String,level:Int32,iconId:String,durationFrame:Int32,exclusiveFrame:Int32`.

Adjusted next parser plan:

1. For SkillData, recover or implement formatter-specific skippers for `ActionGroupData`, `CastData`, `BuffInputBase`, `GameplayTagList`, and list/dictionary wrappers before assigning actual values to top-level fields.
2. For BuffData, reacquire full IL2CPP metadata or regenerate a broader metadata cache that includes `Beyond_Gameplay_Core_BuffDataForMemoryPack` before attempting typed field-value decoding.
3. Keep exact marker counts as evidence only: repeated SkillData id markers often appear in nested action bodies, not necessarily as multiple top-level fields.

## 2026-06-28 BuffData Metadata Type-Hint Pass

`Json/BuffData/*.json` now exposes top-level IL2CPP setter parameter types in the Data index. This replaces the previous "field names and markers only" BuffData state with a conservative typed-schema preview.

Evidence and method:

1. Rechecked public web searches for `Beyond_Gameplay_Core_BuffDataForMemoryPack`, `Beyond.Gameplay.Core.BuffData MemoryPack`, `BuffDataForMemoryPack Endfield`, and `Arknights Endfield BuffData MemoryPack`. No public schema/source surfaced, so the pass stayed local.
2. The moved data is back under `export_full/structured/StreamingAssets/Data`. The current root has `Json/` and `Video/`; the Json rebuild covers 81,735 files, while `Data/Video` contains 464 MP4 files totaling 5,217,460,601 bytes.
3. Queried the installed `global-metadata.dat` with `tools/endfield-il2cpp/catalog_option_flow_metadata.py` using a focused BuffData type regex. The generated local artifacts are `tmp/buffdata_metadata.json` and `tmp/buffdata_metadata.md`.
4. Recovered `Beyond_Gameplay_Core_BuffDataForMemoryPack` setter parameter types for all 29 serialized fields. The useful top-level scalar/flag/id fields are `id`, `addingCooldown`, `duration`, `finishOnRepatriate`, `hasAddingCooldown`, `hasIcon`, `ignoreCooldownWhenAdding`, `ignoreTagImmune`, `lifeType`, `maxTriggerCnt`, `triggerInterval`, `useTimeDilationDt`, and `waitFirstTriggerInterval`.
5. Promoted only top-level type hints and scalar-vs-complex grouping into `scripts/build_data_index.py`. The parser still does not assign concrete field values because `GameplayTagList`, `BlackboardDouble`, `BlackboardInt`, modifier lists, action lists, shield configs, and dictionaries need exact nested skippers first.
6. Regenerated `python scripts\build_data_index.py --groups Json`. The existing WebUI server returned HTTP 200 for `data/game_data/index.json` and `data/game_data/groups/Json_BuffData.json`.
7. Checked `Data/Video` as the only non-Json folder in the moved root. It is MP4 media, and `webui/data/assets/videos.json` already has 942 video entries, so the Data tab continues to exclude videos instead of duplicating large media rows.

Observed output after regeneration:

- `webui/data/game_data/index.json` reports 30 Json groups, 81,735 files, 700,046,680 bytes, 78,710 `memorypack-json` entries, and 3,025 `text-json` entries.
- `Json_BuffData.json` contains 2,291 rows. The first sampled row reports `field types recovered (13 scalar/flag/id, 16 complex/list)`, `typedFields=13/29`, and `schemaTypes=id:String,duration:BlackboardDouble,lifeType:LifeType,triggerInterval:BlackboardDouble,maxTriggerCnt:BlackboardInt,applyTags:GameplayTagList`.
- `Json_SkillData.json` still contains 2,083 rows and reports `field types recovered (30 primitive/enum/string/vector, 15 complex/list)` with `typedFields=30/45`.

Adjusted next parser plan:

1. Decode reusable MemoryPack wrapper bodies next: `BlackboardDouble`, `BlackboardInt`, `GameplayTagList`, list wrappers, and simple dictionaries. These will unlock both BuffData and SkillData more safely than byte-guessing action payloads.
2. Treat modifier/action/shield/timeline lists as opaque until their item formatter types are recovered from metadata or validated with exact byte boundaries.
3. Keep `Data/Video` on the Assets/video path unless a separate media metadata page is requested; it is already indexed and previewed elsewhere.

## 2026-06-28 BuffData Post-ID Prefix Pass

`Json/BuffData/*.json` now exposes a validated post-id scalar prefix in the Data index. This is the first promoted BuffData field-value decode beyond id/string/type hints.

Evidence and method:

1. Rechecked public web searches for `Beyond.Blackboard BlackboardParamBase MemoryPack`, `Beyond.Gameplay.Core.GameplayTagList MemoryPack`, `Beyond_Gameplay_Core_GameplayTagListForMemoryPack`, and `BuffStackingSettings Arknights Endfield`. No usable public schema/source surfaced.
2. Used local IL2CPP metadata to confirm `BlackboardParamBase` carries `useBlackboardKey`, `value`, and `blackboardKey`, and that generated wrappers serialize the Blackboard base fields as `blackboardKey`, `useBlackboardKey`, then `value`.
3. Byte-indexed BuffData samples validated `BlackboardInt` after the top-level `id` field as a 3-member nested wrapper: member count `3`, MemoryPack UTF-8 `blackboardKey`, one-byte `useBlackboardKey`, and signed i32 `value`.
4. Probed the BuffData start prefix (`abilityEventAction`, `addingCooldown`, `applyTags`) but did not promote it: only 1,174 rows followed the simple zero-action shape. Another 516 rows had nonzero ability action counts, and many rows diverged before `addingCooldown`, so this remains blocked on action-list skippers.
5. Anchored the safer parser after the exact filename-stem id marker. For unique-id rows it reads `igniteEventAction` count, `ignoreCooldownWhenAdding`, `ignoreTagImmune`, one-byte raw `lifeType`, `maxTriggerCnt` BlackboardInt, `poiseModifier` count, and, when `poiseModifier` is empty, `shieldConfigs` count. It stops before `stackingSettings`, which byte evidence shows is not a one-byte enum.
6. Full-corpus validation before promotion: `through-shield-count` 2,184 rows, `through-poise-count` 6 rows, repeated id marker skips `2:63`, `3:29`, `4:4`, `6:1`, `7:1`, and three unique-id rows failed bool validation. Parsed value distributions include `lifeTypeRaw` `1:1212`, `0:978`; `ignoreTagImmune` `0:2138`, `1:52`; and `maxTriggerCnt` top values `-1:968`, `1:796`, `0:367`, `999:20`.
7. Promoted `decode_buff_post_id_prefix` in `scripts/build_data_index.py`, regenerated `python scripts\build_data_index.py --groups Json`, and smoke-tested the existing WebUI server. `data/game_data/index.json` and `data/game_data/groups/Json_BuffData.json` both returned HTTP 200.

Observed output after regeneration:

- `Json_BuffData.json` still contains 2,291 rows.
- 2,190 compact summaries now include `post-id prefix parsed` and `postId=...` samples.
- First sampled row now reports `postId=lifeType:1,maxTriggerCnt:0,ignoreTagImmune:0,poise:0,shield:0`.
- Compact sample distributions from generated output match the probe: `lifeType` `1:1212`, `0:978`; `maxTriggerCnt` starts with `-1:968`, `1:796`, `0:367`, `999:20`.

Adjusted next parser plan:

1. Do not parse BuffData from the file start until `abilityEventAction` list bodies have exact skippers; the current initial-prefix probe proved the zero-action shortcut is not corpus-wide.
2. Decode `stackingSettings` next if metadata exposes its exact MemoryPack wrapper; otherwise continue with reusable wrappers (`BlackboardDouble`, `GameplayTag`, small list/dictionary counts) only where a validated anchor avoids the unknown middle body.
3. Keep repeated-id BuffData rows marked ambiguous for post-id parsing until the true top-level id occurrence can be distinguished from nested action references.

## 2026-06-28 BuffData Exact Tail Pass

`Json/BuffData/*.json` now has a second promoted value-decode step: rows in the compact post-id tail branch parse through the file end, including a validated `BuffStackingSettings` subset and the final timer fields.

Evidence and method:

1. Rechecked public web searches for `Beyond.Gameplay.Core.BuffStackingSettings`, `BuffStackingSettings Endfield`, `Beyond_Gameplay_Core_BuffStackingSettingsForMemoryPack`, and `BuffStackingSettings MemoryPack`. No public schema/source surfaced.
2. Extracted local IL2CPP metadata from `tmp/buff_wrappers_metadata.json` / `tmp/buffdata_metadata.json`. Runtime `BuffStackingSettings` has 12 non-static serialized fields plus static `TIMELINE_AVAILABLE_STACKING_TYPE`; generated setters expose `identifierType`, `isNeedStackEffect`, `maxStackCnt`, `maxStackCntKey`, `negatePriority`, `priority`, `priorityKey`, `stackEffects`, `stackingKey`, `stackingType`, `useMaxStackCntKey`, and `usePriorityKey`.
3. Method-body lookup did not produce a useful stacking formatter body target, so the promotion used local metadata plus exact byte handoff validation.
4. The exact branch is a compact `identifierType=Id` layout, not a full stacking-key branch parser: member count `12`, one-byte `identifierType`, `isNeedStackEffect`, i32 `maxStackCnt`, empty/non-empty `maxStackCntKey`, `negatePriority`, f32 `priority`, `priorityKey`, `stackEffects` count, one-byte `stackingType`, `useMaxStackCntKey`, and `usePriorityKey`. Rows needing `stackingKey` or non-empty list bodies remain opaque.
5. The handoff after the compact stacking block validates `tagsAfterTriggerExtendBuffAction` as a nested GameplayTag record, `timelineActions` as a u32 count, `triggerInterval` as the float-backed Blackboard wrapper (`memberCount=3`, `blackboardKey`, `useBlackboardKey`, f32 value), and final `useTimeDilationDt` / `waitFirstTriggerInterval` bools.
6. Full-corpus prototype result before promotion: 1,884 rows consumed exactly through the file end. Other rows were left unpromoted because of repeated id markers, non-empty `poiseModifier` / `shieldConfigs`, nonzero/complex tail bodies, or divergent action/list layouts.
7. Promoted the exact branch in `scripts/build_data_index.py`, regenerated `python scripts\build_data_index.py --groups Json`, and smoke-tested the existing WebUI server. `data/game_data/index.json`, `data/game_data/groups/Json_BuffData.json`, and `data/game_data/groups/Video.json` returned HTTP 200.

Observed output after regeneration:

- `webui/data/game_data/index.json` now reports 31 groups, 82,199 files, and kinds `memorypack-json:78710`, `text-json:3025`, `video:464`.
- `Json_BuffData.json` contains 2,291 rows: 1,884 summaries say `post-id tail parsed`, 306 say `post-id prefix parsed`, and 101 remain marker/error/opaque cases without a post-id sample.
- First sampled row now shows `postId=life:1,maxTrig:0,stack:0,maxStack:0,trig:-1.0,wait:1`.
- `Video.json` contains 464 MP4 entries with `ftyp`/brand summaries; this is lightweight media indexing, not a replacement for the richer Assets video browser.

Adjusted next parser plan:

1. For BuffData, do not broaden the compact stacking branch until a row with `identifierType=StackingKey` or non-empty `stackEffects` can be byte-validated with an exact handoff.
2. The next high-value BuffData work is still the middle body: `abilityEventAction`, modifier lists, `blackboard`, and shield/poise branches. These need item formatter skippers before they should be promoted.
3. Since Video is now indexed, future non-Json work should target data-bearing formats, not MP4 payload contents, unless the requested surface is media metadata.

## 2026-06-28 Raw Data Tree Index Pass

The moved `export_full/structured/StreamingAssets/Data` root now contains both
extracted `Json/`/`Video/` folders and raw installed-game Data folders. The WebUI
Data page has been broadened to index the full tree instead of only the
previous JSON/video subset.

Methods tried and findings:

1. Rechecked public web searches for `hgmmap`, `manifest.hgmmap`,
   `InitStringPathHash`, and `ArknightsEndfield hgmmap`. No usable public
   format documentation surfaced, so raw archive support stayed header-level.
2. Re-ran the BuffData tail branch hypothesis from the previous pass. A global
   `stackingKey`-after-`stackEffects` layout plus counted `GameplayTagList`
   failed corpus validation: it reduced exact tail coverage to zero for the
   1,884 already-valid compact rows. Byte comparison showed the format is
   branchy: the promoted compact branch has no `stackingKey`, while some
   remaining rows probably use a stacking-key branch or non-empty list bodies.
   This was not promoted.
3. Inventoried the current root: 379,465 files, 60,871,904,787 bytes, with
   kinds `asset-bundle:258422`, `memorypack-json:78710`, `flatbuffer-bytes:38561`,
   `text-json:3025`, `video:464`, `irradiance-volume:263`, `wwise-pck:16`,
   `binary-index:3`, and `hgmmap:1`.
4. Updated `scripts/build_data_index.py` to include PCK files, classify raw
   `.ab`, `.pck`, `.hgmmap`, `.bin`, world-streaming `.bytes`, and video files,
   and shard huge non-JSON groups. `Bundles/Windows/main` is split by first hex
   filename nibble; streaming/irradiance/video groups split by path.
5. Optimized the full index pass after a 15-minute timeout: the builder now
   reads each file header once, reuses stat/header data during entry generation,
   and uses a 1 KiB indexing header. The browser binary preview still fetches
   its own header range from the raw file.
6. Updated the Data frontend to honor `requiresGroupSelection` for large roots,
   so opening the tab loads only `index.json` and waits for a group choice
   instead of fetching every shard. The generated index now sets this flag
   because the file count exceeds the 120,000 auto-load limit.
7. Full rebuild completed in 726 seconds: 193 groups, 379,465 files, about
   58,052 MiB. HTTP smoke tests returned 200 for `data/game_data/index.json`,
   `groups/Audio_PCK.json`, and `groups/Bundles_Windows_main_0.json`.

Adjusted next parser plan:

1. Do not promote the failed BuffData stacking-key/count-list hypothesis until a
   branch-selective parser can consume representative rows exactly without
   regressing the compact branch.
2. For raw Data, treat `.ab`, `.pck`, and `.hgmmap` as encoded/archive payloads
   in the generic Data page. Deeper unpacking should use AnimeStudio or a
   dedicated extractor path rather than ad hoc browser indexing.
3. The next high-value non-JSON parser work is schema evidence for
   `Streaming/` FlatBuffer-like `.bytes` files or exact row layouts for
   `ExtendData/*StringPathHash.bin`; both need local schema/code evidence before
   naming fields.

## 2026-06-28 SkillData Post-ID Tail Prefix Pass

`Json/SkillData/*.json` now exposes the first validated field-value decode after
the exact `skillId` marker. This pass stays anchored after the top-level id
because the file starts with complex `actionGroupData`, which still lacks safe
item skippers.

Evidence and method:

1. Rechecked public web searches for `Beyond.Gameplay.Core.SkillDataForMemoryPack`,
   `SkillDataForMemoryPack Arknights Endfield`, `Beyond.Gameplay.Core.SkillData
   MemoryPack`, and `Arknights Endfield SkillData MemoryPack`. No public schema
   or source surfaced, so the promotion used local metadata plus corpus byte
   validation.
2. Inspected SkillData bytes after the verified `skillId` marker. The stable
   prefix is `skillName` as a MemoryPack UTF-8 string, `skillSpecification` as
   little-endian i32, then `skillTags`, `smartTargetBuffFindSettings`,
   `smartTargetBuffIds`, `smartTargetSelectStrategy`, and `smartTargetTagQuery`.
3. Two bad prototypes were rejected before promotion: treating all smart-target
   enum-like fields as i32 produced implausible values such as `512` and
   `65536`, while treating `skillSpecification` as u8 made `skillTags` look like
   a huge `16777216` count. The validated layout is mixed: `skillSpecification`
   is i32, while the later smart-target enum-like fields in this branch are
   one byte each.
4. `skillTags` has two observed branches. The common branch is a direct u32
   count with a compact empty/default tag record. The 23 dash/normal/combo rows
   use a one-member wrapper byte before the real u32 count and contain clean tag
   paths such as `Skill/Character/chr_0004_pelica/DashAttack`.
5. Full-corpus validation before promotion: 2,030 unique-id rows parsed through
   `smartTargetTagQuery` with zero parse errors; 53 rows remain ambiguous because
   the exact skill id appears more than once. Parsed distributions include
   `skillSpecification` raw values `0,1,2,3,4,5,6,7,8,9,10,11,100`,
   `smartTargetBuffFindSettings` raw `0:2007` and `3:23`,
   `smartTargetSelectStrategy` raw `0:2030`, and `smartTargetTagQuery` raw
   `0:2011`, `1:16`, `3:3`.
6. Promoted the parser in `scripts/build_data_index.py`, filtering compact
   samples to clean printable tag paths so two control-byte nested payloads do
   not display as valid tag text. The parsed structure still records the raw tag
   record in `decoded.postIdTailPrefix`.
7. Regenerated `python scripts\build_data_index.py --groups Json`. The full
   Data index remains 379,465 files / 193 groups, and `requiresGroupSelection`
   is true after fixing selected-group rebuilds to compute that flag from
   aggregate preserved group counts. HTTP smoke tests returned 200 for
   `data/game_data/index.json` and `data/game_data/groups/Json_SkillData.json`.

Observed output after regeneration:

- `Json_SkillData.json` contains 2,083 rows.
- 2,030 summaries now say `post-id tail prefix parsed`; each compact sample has
  `postId=spec:<raw>,tags:<count>,find:<raw>,buffIds:<count>,select:<raw>,query:<raw>`.
- 23 rows show `tagMode:wrap` plus a clean `Skill/...` tag path sample.
- 53 repeated-id rows stay marker-ambiguous and do not get post-id tail values.

Adjusted next parser plan:

1. Do not parse SkillData from the file start until `ActionGroupData` and
   related action/cast/buff item bodies have exact skippers.
2. The next SkillData boundary is `switchToBuffConfig`; promote it only after
   identifying its member count/layout and proving handoff to `switchToCenterBeforeCast`.
3. For broader binary JSON coverage, reusable wrappers remain the best leverage:
   exact `GameplayTagList` variants, small string/id lists, and enum-width rules
   can now be shared between SkillData and BuffData instead of guessed per file.

## 2026-06-28 SkillData Switch Tail Probe Pass

This pass corrected the previous SkillData post-id coverage and added a bounded
`switchToBuffConfig` tail probe instead of promoting an unsafe full nested decode.

Evidence and method:

1. Rechecked public web searches for `SwitchToBuffConfig`,
   `Beyond.Gameplay.Core.SwitchToBuffConfig`,
   `Beyond_Gameplay_Core_SwitchToBuffConfigForMemoryPack`,
   `smartTargetTagQuery`, and related SkillData names. No public Endfield schema
   or source surfaced. The stable schema evidence came from the installed
   `global-metadata.dat` parsed by `tools/endfield-il2cpp/catalog_option_flow_metadata.py`.
2. Local IL2CPP metadata confirms generated MemoryPack wrapper setters for
   `Beyond_Gameplay_Core_SkillDataForMemoryPack`, including the post-id order
   through `smartTargetTagQuery`, and confirms `SwitchToBuffConfig` generated
   fields in alphabetical setter order: `asSkillCast`, `buffs`, `buffSource`,
   `condition`, and `targets`.
3. A key false-positive was found in the previous parser: accepting any decoded
   256-byte string let binary payloads masquerade as `skillTags` or
   `smartTargetBuffIds`. Tight clean-string validation now rejects tag/id strings
   containing control or replacement characters, while still allowing empty
   default tag/id entries.
4. Re-ran the enum-width hypotheses. Treating the smart-target fields as i32
   still misaligns common rows (`512`, `65536`, and larger implausible values),
   while the observed generated branch validates as one-byte
   `smartTargetBuffFindSettings`, counted string/id list, one-byte
   `smartTargetSelectStrategy`, and one-byte `smartTargetTagQuery`.
5. After strict validation, SkillData coverage is now 2,025 parsed unique-id rows,
   53 repeated-id rows left ambiguous, and five rows deliberately rejected as
   parse errors rather than false positives:
   `chr_0022_bounda_ultimate_skill`, `chr_0024_deepfin_normal_skill`,
   `chr_0028_wulfa_ultimate_skill`, `chr_0030_zhuangfy_combo_skill`, and
   `chr_0030_zhuangfy_combo_skill_ult`.
6. Every one of the 2,025 strict parsed rows has a plausible `SwitchToBuffConfig`
   marker within the next 96 bytes: member count `5`, boolean `asSkillCast`, and
   a bounded `buffs` list count. The common branch has a 12-byte pre-switch
   residual and `buffsCount=0`; 23 dash rows have a 28-byte pre-switch residual;
   one Ardelia row has a 63-byte residual containing a clean
   `Skill/Character/Common/SpellStatus/Corrupt` tag string. Some character rows
   continue with non-empty switch/tail payloads, so the promoted parser records
   the marker, counts, byte lengths, hex prefixes, and string hits instead of
   claiming a complete handoff to `switchToCenterBeforeCast`.
7. Rebuilt `python scripts\build_data_index.py --groups Json`. The generated
   index remains 379,465 files / 193 groups / `requiresGroupSelection: true`.
   `Json_SkillData.json` now has 2,025 rows with `post-id tail prefix parsed`
   and `switchRel`, `switchBuffs`, and `tail` compact samples. HTTP smoke tests
   returned 200 for both `data/game_data/index.json` and
   `data/game_data/groups/Json_SkillData.json`.

Adjusted next parser plan:

1. The next SkillData step is to decode `SwitchToBuffConfig` nested bodies by
   writing exact skippers for `TargetSettings`, `SequenceActionData`, and
   `List<BuffInputBase>` union items. The current marker probe is intentionally
   not a full nested decode.
2. Revisit the five strict parse-error rows only after `smartTargetBuffIds` item
   variants are understood; three appear to use a wrapped/non-string id item
   shape, while two Zhuangfy rows use a different `skillTags` body shape.
3. The same clean-string validation should be reused for future MemoryPack list
   parsers so binary payloads cannot pass as text just because Python can decode
   them with replacement characters.

## 2026-06-28 SkillData Post-Switch Tail Exact Pass

This pass extends the previous `switchToBuffConfig` marker probe into a validated
post-switch tail decode for the default switch-config branch.

Evidence and method:

1. Rechecked public searches for `Beyond.Gameplay.Core.TargetSettings`,
   `Beyond.Gameplay.Core.SequenceActionData`, `TargetSettingsForMemoryPack`, and
   `SequenceActionDataForMemoryPack`. No public Endfield schema surfaced, so the
   promoted parser uses local IL2CPP metadata plus byte-level corpus validation.
2. Local metadata shows `SwitchToBuffConfig` generated order as `asSkillCast`,
   `buffs`, `buffSource`, `condition`, and `targets`. The representative switch
   tail starts with member count `05`, `asSkillCast=1`, empty `buffs`, then a
   `TargetSettings` block beginning with member count `0D`. The following
   `SequenceActionData` marker is `03`, matching its generated three-member
   body.
3. The common/default `SwitchToBuffConfig` branch has a stable 148-byte boundary
   from the switch marker. Immediately after that boundary, the bytes validate
   as `switchToCenterBeforeCast` bool, `tagDuringAttach` GameplayTagList,
   `toggleBuffs` count, and `uiRangeHints` count/body.
4. The first UI range prototype used one-byte enums and failed with consistent
   six-byte residues. Re-parsing `SkillHintShape` and `FactionType` as i32
   produced exact file-end handoffs. `UIRangeHintData` validates as a 3-member
   item (`selectAll`, `shapeData`, `targetFaction`) and `SkillHintShapeData` as
   a 21-member item with f32/string/bool/vector2 fields in generated setter
   order.
5. Full-corpus validation after promotion: among the 2,025 strict parsed
   SkillData rows, 1,948 parse exactly through the file end after the default
   switch-config branch, 76 parse cleanly through `toggleBuffsCount` and stop
   because the toggle list body is still opaque, and one row
   (`chr_0026_lastrite_normal_skill`) has a non-default switch body that does
   not satisfy the 148-byte default boundary.
6. Exact tail rows include 1,823 rows with `uiRangeHintsCount=0`, 122 rows with
   one UI range hint, and three rows with two UI range hints. Observed UI hint
   item lengths are 75, 81, and 86 bytes; shape raws include `Point`, `Circle`,
   `Sector`, and `Arrow`, with radius/angle key strings such as `radius` and
   `angle` on the keyed rows. Two exact rows carry non-empty `tagDuringAttach`
   lists while keeping empty toggle/UI bodies.
7. Rebuilt `python scripts\build_data_index.py --groups Json`. The generated
   full Data index remains 379,465 files, 193 groups, and
   `requiresGroupSelection: true`; `Json_SkillData.json` is served at HTTP 200
   from the existing local WebUI server.

Adjusted next parser plan:

1. Decode `toggleBuffs` next via `ToggleBuffData` and `BuffInputBase` list item
   skippers; the 76 stopped rows now have a clean `toggleBuffsCount` boundary.
2. Decode the one non-default `SwitchToBuffConfig` body by adding skippers for
   non-empty `buffs`, `TargetSettings`, and `SequenceActionData` bodies instead
   of assuming the 148-byte default branch.
3. Keep `ActionGroupData`, cast data, blackboard, and early SkillData fields out
   of field-value decoding until their item/list wrappers have exact handoffs.

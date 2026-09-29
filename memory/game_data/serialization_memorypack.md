# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and
level payloads: where each JsonData family's framing stands, how LevelScript,
SkillData and BuffData routes are promoted, and the IL2CPP chain that
identifies which formatter a payload resolves to -- static identity
throughout, never observed execution. Current denominators are in the
generated JsonData, SkillData and BuffData corpus reports; each reader,
validator and gate documents its own layout, evidence tier and non-proofs in
its module docstring, with per-build facts in `scripts/game_data/contracts/`.
Derived-plan EOF closure never substitutes for an independently named
whole-file schema.

## The JsonData registry gate

`python -m scripts.game_data.jsondata_corpus` joins each current JsonData
identity to its export file by path, length and logical MD5 and assigns one
terminal state (vocabulary in its docstring). The last complete gate
authenticated every current file with no unsupported or unclassified
identity: only LevelScriptData, LevelScriptTemplateData and SkillData keep
named partials, BuffData outside its exact cohort has named outer frames, and
every other family is schema decoded. A state is a structural lane, not field
coverage; family gates own cursor, native and semantic claims. A type with a
registered `MemoryPackFormatter` (`SerializeFieldDictionary` and siblings) is
read from that formatter, never from its field list; see
[`codecs/levelscript/action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py).

## JSON-schema and compact-table families

Each reader checks stored order, types and cross-index relations and fails
closed on drift; none proves runtime selection or consumption. Textual JSON
lives in the `scripts/game_data/schemas/` package (GameplayConfig compact and
`$type` tables, text tables, LevelMountPoint, NPC catalogs and PrefabInfo,
GoldCoin, UILevelMapLoadConfig, MissionRuntimeAsset, MapConfig). Binary
tables use `gameplay_compact_binary` (MissionArea, SubGame,
WorldEntityRegistry), `memorypack.tables` (DialogIdTable,
BambooRaftTaskTable), `interactive_binary`, the LevelConfig, NavMesh,
TeleportValidation, AetherEnergyLock and MatrixShockWave `*_binary` readers,
`atmospheric_npc_binary` and `gpu_ui_binary`/`gpu_ui_corpus`. Map marks
([`map_mark_relations.py`](../../scripts/game_data/map_mark_relations.py)):
a registry link needs an exact `markInstId` and equal position, a scene link
also a unique `LevelShortIdTable` scene, and it assigns only that marker.

## LevelData, Interactive, AbilitySystem and AnimationConfig

All are exact stored schemas in the last gate. LevelData's sequential
43-field reader (`leveldata_binary.py`, `codecs/leveldata/`) shares value
codecs with LevelScript and the 14+77+27 NPC row; its fallbacks are named
frames, never full schemas. SpawnerConfig and CharInteractPerform close every
owner. Interactive templates (`memorypack/interactive.py`) take component
tags from the native `BaseComponentData` dispatcher; the 38-member
`Core_AbilitySystemForIntData` refuses positive nested domains rather than
inherit a schema from field names. AnimationConfig and NPC MontageNew resolve
path hashes only through an authenticated `StringPathHash` catalog; the
shader-publication proof is conditional on runtime actor and IFix selection.

## LevelScriptData owner cursor

One generated-order walk (`codecs/levelscript/sequential_owner.py`) reads
members 2..27 after an exact action-map boundary: null (`0xff`), the 20-byte
empty `ActionMapAssetRaw`, or a positive map whose three lists and
`ParamListForGraph` close (`current_action_sequence.py`, then the reviewed
`action_map_layouts.json` nodes). `top_level_prefix` delegates positive
`enemies`, `interactiveLocks`, `interactives`, `modules` and `npcs` to exact
codecs and stops before an unowned positive count. `task_conditions.py`
decodes `taskMap`; a file is exact only when every entry and `triggerVolumes`
end at physical EOF, and a failed entry keeps its first bounded diagnostic.
GameCondition and module tags renumber per build and resolve by type name.
The unique-suffix and first-record lanes stay partial. Rank first stops by
whole files unlocked after every list and the owner tail close, not by raw
union counts, and rerank after each complete gate.
The previously isolated task-map first-stop queue now closes at named-exact
EOF for every selected, ledger-matched source under the current codecs. This
is a bounded queue closure; other LevelScript files require their own selected
source receipts before promotion.

## LevelScript action-map unions

`ActionMapAssetRaw` is the three-list `ActionSerializedMap` (action, getter,
header) plus a one-member `ParamListForGraph`; empty, it closes at root byte
20 (the map alone at byte 15). Templates and Interactive files reuse the same
reader ([template reader](../../scripts/game_data/levelscript_template_binary.py)).
Elements are unions keyed by `(tag, memberCount)` in four separate dispatcher
domains (ActionBase, PureGetter, ActionHeader, nested GameCondition). Tags are
per-build family ranks: name types via `scripts.game_data.levelscript_union_tags`.
`python -m scripts.game_data.levelscript_union_layouts` derives every layout
from setter order at the `direct` tier and returns nothing if a reviewed row
disagrees. Production reads only the reviewed (`exact`) rows of
`codecs/levelscript/action_map_layouts.json` through
[`action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py),
whose docstring owns wire shape, gate mechanics and non-obvious Param shapes.

One proof pattern covers every route: switch jump and registered wrapper fix
identity; the complete reader and forwarding formatter fix member count,
ordered reads and setters; typed `Param<T>` contexts fix parameter, element
and enum types; ledger-joined source spans replay exactly. That proves stored
fields only, never an action run, event fired, getter value or resolved ID.
Per route: `contracts/levelscript_<route>_native.json`, validator
`python -m scripts.game_data.levelscript_<route>_native` (its docstring holds
stored fields, reached authored forms and non-proofs), sometimes a
`codecs/levelscript/` codec, and an `action_map._required_native_gates` entry.
Promotion: (1) isolated contract, validator, tests; (2) layout row, gate
entry, production replay, clean derivation; (3) whole-owner closure, decided
only by the full JsonData gate (`scripts.game_data.jsondata_corpus`) at
physical EOF. Projections between (2) and (3) are provisional.

## LevelScript route status

- Integrated: every layout row and `_required_native_gates` contract; the
  code is the inventory.
- Step 1, awaiting production layout and targeted replay: newly isolated
  contracts are listed here as they are validated. Other unknown routes remain
  listed below.
- Step 2, awaiting the next combined gate (the last one predates them):
  ActionBase `0x00DB` FacSetInteractLockedState, `0x04DF`
  ToggleClearScreenButRadioV2, `0x0395` RemoveNPCDialog, `0x0366`
  PlayEffectOnNpc, `0x002B` BlockBattleMusic, `0x002A`
  BlockAutoMusicChangeCancel, `0x00C9` FacGetBuildingPosition,
  `0x0479` SettlementUpgradeShow, `0x00AE` EnvironmentEnable, and
  `0x0007` AddBuffsToTargetSelves, `0x0475`
  SetSquadSpecialIdleEnable, `0x0405` SetEnemyUIShowRange, `0x0446`
  SetListBuff, `0x0111` IsLookAtPointInScreen, and `0x0374`
  PlayVoiceNarrative, `0x03BA` ScriptedCharTeleportTo, and `0x03B5`
  ScriptedCharPatrolStart, `0x04BF` StopCharScriptedMode, and `0x0032`
  BuildingPosHintShow, `0x0031` BuildingPosHintHide, and `0x00CA`
  FacGuideHintEnable, `0x03FC` SetDecorationAnimatorInt, and `0x04C2`
  StopEffectOnNpcProxy, `0x0343` NpcStopCurMontage, `0x045E`
  SetMainCharHpBarActive, `0x0077` DestroyAbilityEntity, `0x04D6`
  TeleportGameplayNpc, `0x0521` ApplyMovementSettingModifier, `0x0472`
  SetSquadIconActive, `0x04EC` ToggleUI_DevOnly, `0x04AE`
  StartCutsceneAndHideSceneObjectAction, `0x04AD`
  StartCutsceneAndControlSceneObjectAction, `0x04A1`
  SkipEntityDieDisplay, `0x03FD` SetDecorationViewState, `0x04B3`
  StartFmvAndTeleportAction, `0x007E` DisableHudFade, `0x00A0`
  EntityMoveToWithSpeed, `0x0316` MoveBambooLast, and `0x03E8`
  SetBambooPosIndex, `0x04C7` StopRadio, `0x04B7`
  StartNarrativeBlackScreenAndTeleport, `0x0471`
  SetSquadEnableRelaxIdle, and `0x0042` CharacterPlayMontage;
  GetterBase `0x001C` CheckPerformanceReady, `0x03B4`
  ListMakeEntityPtr, `0x0182` GetterEntityPtr, `0x018A`
  GetterLevelScriptPtr, `0x0030` EntityToString, and `0x018E`
  GetterListBuff, `0x0053` GetCurSquadAllDead, and `0x004E`
  GetCharacterTemplateId, `0x03E3` NpcGetPackAnimHasClean, `0x0144`
  GetScriptTaskObjectiveIsCompleted, `0x01C5` IsEndminGender,
  `0x0043` FloatGetterIntToFloat, `0x000C` BoolGetterMultOr, and
  `0x0046` FloatGetterPlus, `0x009F` GetInteractivePropertyInt, and
  `0x013C` GetMissionSavePropertyInt;
  ActionHeader `0x00DC` OnMapVarChanged, `0x0065` OnEnemyInFight,
  `0x006A` LevelEvent.OnEntityHpChanged, and `0x00DF`
  OnSettlementReadyPerformance, `0x009C` LevelEvent.OnSpawnerStart,
  `0x00A4` LevelEvent.OnSpellAbnormalStart, `0x0031`
  EntityEvent.OnPhysicalNoGuard, `0x0045` LevelEvent.OnAnyEntityDie,
  `0x009E` LevelEvent.OnSpawnerWaveBegin, `0x0030`
  EntityEvent.OnPhysicalInfliction, and `0x0043`
  LevelEvent.OnAnyEnemyPoiseZero, and `0x00BA`
  ScriptEvent.OnBBVariableChanged, and `0x0042`
  LevelEvent.OnAnyEnemyPoiseKnotBreak, and `0x0040`
  LevelEvent.OnAetherEnergyLockEndPointScanned, and `0x0053`
  LevelEvent.OnCutsceneExit, `0x000F` EntityEvent.OnEntityDie, and
  `0x004E` LevelEvent.OnBlightMiasmaWeakGuide, and `0x00CD`
  ScriptEvent.OnStartScriptControlledCharMode, and `0x009B`
  LevelEvent.OnSpawnerPause, `0x005C`
  LevelEvent.OnEncounterIntroPartEnd, `0x007C`
  LevelEvent.OnNpcDirtyBlockCleaned, `0x008B`
  LevelEvent.OnServerDialogExit, `0x0077` LevelEvent.OnLevelReset, and
  `0x00A1` LevelEvent.OnSpecificEntityDie, `0x00E4` OnSubGameStart, and
  `0x007D` LevelEvent.OnNpcPatrolCheckpointReach, and `0x0098`
  LevelEvent.OnSpawnerGroupComplete, and `0x00A2`
  LevelEvent.OnSpecificEntityListDie, and `0x00B6`
  MissionEvent.OnClientGlobalVarChanged, and `0x00C9`
  ScriptEvent.OnScriptPreStart.
  Their individual validators,
  current source receipts, production layouts, and focused replay pass. The corrected
  OnMapVarChanged/OnEnemyInFight projection closes 8 reached owners at EOF
  and leaves 11 at later unions. FacGetBuildingPosition's targeted replay
  moves its former first-stop owners to ActionBase `0x0479`, with one
  reaching named-exact EOF. OnEntityHpChanged's targeted replay reaches
  named-exact EOF or later ActionHeader `0x0053`, `0x000F`, `0x009B`,
  and `0x005C` routes. SettlementUpgradeShow's hash-checked targeted
  replay advances the newly exposed owners to GetterBase `0x001C` or
  ActionBase `0x00AE`. Their subsequent hash-checked, selected-file
  replays converge at ActionHeader `0x00DF`. Its hash-checked, selected-file
  replay reaches named-exact EOF throughout that cohort; whole-owner
  closure awaits the combined gate. AddBuffsToTargetSelves's selected-file
  replay advances nine former first stops to ActionBase `0x0475`, one to
  `0x0405`, and one to `0x0446`. SetSquadSpecialIdleEnable's selected-file
  replay advances five to PureGetter `0x03B4` ListMakeEntityPtr, two to
  `0x018A` GetterLevelScriptPtr, and two to `0x0182` GetterEntityPtr.
  ListMakeEntityPtr's five selected files then all advance to `0x0182`,
  making seven source files in that next selected cohort. GetterEntityPtr's
  seven selected files all advance to `0x018A` GetterLevelScriptPtr;
  with the two direct files, that cohort contains nine. Its gated replay
  moves four to ActionHeader `0x009C`, three to ActionHeader `0x00A4`,
  one to GetterBase `0x0030`, and one to ActionHeader `0x0045`.
  SetEnemyUIShowRange's one selected file advances to ActionBase `0x0111`.
  SetListBuff's one selected file advances to GetterBase `0x018E`.
  EntityToString's one selected file advances to ActionHeader `0x00A4`,
  making four selected files there.
  OnSpawnerStart's four selected files advance three to ActionHeader
  `0x0031` and one to `0x00A4`, making five selected files in the latter
  cohort. IsLookAtPointInScreen's one selected file advances to ActionBase
  `0x0374`. GetterListBuff's one selected file reaches named-exact EOF;
  whole-owner closure still awaits the combined gate.
  OnSpellAbnormalStart's five selected files all advance to ActionHeader
  `0x009E`. PlayVoiceNarrative's one selected file advances to ActionBase
  `0x03BA`. OnPhysicalNoGuard's three selected files all advance to
  ActionHeader `0x0030` (21 members), distinct from GetterBase `0x0030`.
  OnAnyEntityDie's one selected file advances to ActionHeader `0x0043`.
  OnSpawnerWaveBegin's five selected files all advance to ActionHeader
  `0x00BA`.
  ScriptedCharTeleportTo's one selected file advances to ActionBase
  `0x03B5`.
  OnPhysicalInfliction's three selected files all advance to ActionHeader
  `0x00BA`, extending that unknown cohort. OnAnyEnemyPoiseZero's one
  selected file advances to ActionHeader `0x0042`.
  ScriptedCharPatrolStart's one selected file advances to ActionBase
  `0x04BF`.
  OnBBVariableChanged's eight selected files reach named-exact EOF under
  hash-checked replay; this is scoped closure, not a whole-owner gate.
  OnAnyEnemyPoiseKnotBreak's one selected file also reaches named-exact EOF.
  OnAetherEnergyLockEndPointScanned's two selected files reach named-exact
  EOF under their hash-checked replay.
  StopCharScriptedMode's one selected file advances to GetterBase
  `0x004E` (eight members).
  OnCutsceneExit's two selected files split between named-exact EOF and
  ActionHeader `0x004E` (15 members), distinct from that GetterBase.
  GetCurSquadAllDead's six selected files reach named-exact EOF.
  GetCharacterTemplateId's one selected file advances to ActionHeader
  `0x00CD` (18 members).
  OnEntityDie's three selected files reach named-exact EOF after the
  selected LevelEnemyData enum and nullable-float correction. The third
  source stores an unnamed enum value, retained as raw numeric evidence.
  OnBlightMiasmaWeakGuide's one selected file reaches named-exact EOF.
  OnStartScriptControlledCharMode's one selected file reaches named-exact
  EOF under its hash-checked replay.
  OnSpawnerPause's three selected files reach named-exact EOF under their
  hash-checked replay.
  BuildingPosHintShow's nine selected files advance eight to ActionBase
  `0x0031` and one to ActionBase `0x00CA`; these are later first stops, not
  complete owner records. Its Int32-backed rotation values are gated by the
  native enum members; authored world positions and handle paths do not prove
  a live building hint.
  NpcGetPackAnimHasClean's seven selected files all advance to ActionHeader
  `0x007C`. Its authored literal NPC targets do not prove an animation-state
  result or runtime execution.
  OnEncounterIntroPartEnd's one selected file reaches named-exact EOF after
  its typed `LsmPtr` input and nullable output. The authored pointer does not
  establish that the encounter intro ran.
  BuildingPosHintHide's eight selected files reach named-exact EOF in six,
  ActionBase `0x00CA` in one, and GetterBase `0x0144` in one. Its `Param<uint>`
  handle stores authored local paths; no produced handle or runtime hide is
  observed.
  OnNpcDirtyBlockCleaned's seven selected files all reach named-exact EOF.
  Their `ParamOutput<EntityPtr>` paths are authored outputs, not resolved
  entities or observed events.
  FacGuideHintEnable's two selected files reach named-exact EOF. Their
  constant enable values and hint IDs are authored inputs; the UI was not
  observed activating the hints.
  OnServerDialogExit's eight selected files reach named-exact EOF in seven
  and ActionHeader `0x0077` in one. Each reached dialog ID filter is an
  authored key; the output is null in these spans, and no server exit event
  is observed.
  OnLevelReset's one selected file reaches named-exact EOF. Its inherited
  validation parameter is a stored true value; no live reset is observed.
  SetDecorationAnimatorInt's eight selected files close three at named-exact
  EOF and advance five to later ActionBase `0x0077` (three), `0x04AE` (one),
  and `0x04A1` (one). These tags are ActionBase routes, distinct from the
  ActionHeader `0x0077` OnLevelReset. Stored animator inputs do not prove a
  live animation change.
  StopEffectOnNpcProxy's eight selected files close seven at named-exact EOF
  and advance one to GetterBase `0x01C5`. Its effect/proxy IDs and mount
  values are authored inputs, not an observed stopped effect.
  NpcStopCurMontage's eight selected files all advance to ActionBase
  `0x04D6`; their authored default montage mask and unresolved NPC getter
  references do not prove a live montage stop.
  SetMainCharHpBarActive's seven selected files all advance to later unions:
  ActionHeader `0x00E4` in three, ActionBase `0x0521` in one, `0x0472` in two,
  and `0x04EC` in one. DestroyAbilityEntity's three selected files all advance
  to ActionHeader `0x00A1`. These are scoped cursor advances, not whole-owner
  closure or evidence of executed HUD and ability-entity changes.
  IsEndminGender's one selected file reaches named-exact physical EOF after
  three stored Female inputs; no runtime gender evaluation is observed.
  TeleportGameplayNpc's eight selected files all advance to ActionHeader
  `0x007D` (21 members). Their NPC keys and property paths are authored
  references, not resolved coordinates or an observed teleport.
  ApplyMovementSettingModifier's one selected file advances to ActionHeader
  `0x00E4` (16 members). SetSquadIconActive's two selected files advance to
  ActionHeader `0x0098` (18 members) and ActionBase `0x03FD` (13 members).
  SetDecorationViewState's one selected file advances to ActionBase `0x007E`
  (9 members); that is a scoped cursor advance, not a live decoration change.
  These are later unknown routes, not observed movement or UI changes.
  ToggleUI_DevOnly's one selected file reaches named-exact EOF; its stored
  `MainHud` key and true flag do not establish a visible HUD transition.
  StartCutsceneAndHideSceneObjectAction's one selected file advances to
  ActionBase `0x04AD` (19 members) after two stored cutscene records. The
  selected cursor result does not establish runtime playback or hiding.
  StartCutsceneAndControlSceneObjectAction's one selected file then reaches
  named-exact EOF after three stored records with scene-object identifiers.
  Those identifiers do not establish a live scene-object state change.
  SkipEntityDieDisplay's one selected file advances to ActionBase `0x04B3`
  (16 members). Its slot-based target remains a stored reference, not an
  observed death-display decision.
  StartFmvAndTeleportAction's one selected file advances to GetterBase
  `0x0043` (8 members). DisableHudFade's one selected file advances to
  GetterBase `0x000C` (8 members), then reaches named-exact EOF after that
  getter's stored array of six local boolean references. These are selected
  cursor advances, not observed playback, teleport, HUD changes, or a getter
  result.
  FloatGetterIntToFloat's one selected file advances through its stored
  getter reference to a positive two-element `introPart.operaSegments`
  list. The native-gated nested reader consumes both records and the file
  reaches named-exact physical EOF. Neither the getter reference nor the
  authored opera IDs prove a runtime conversion or encounter operation.
  EntityMoveToWithSpeed's seven historical first-stop files contain 63
  native-gated action spans. Selected replay closes four files at
  named-exact EOF; two advance to GetterBase `0x0046` (nine members), and
  one advances to ActionBase `0x0316` (nine members). The selected
  MoveBambooLast reader then advances that file to ActionBase `0x03E8` (ten
  members). SetBambooPosIndex joins the newly exposed action and advances
  the same file to ActionHeader `0x00A2` (sixteen members). The gated
  OnSpecificEntityListDie reader then reaches named-exact EOF in that one
  file after a positive three-entity filter list and local output path.
  This is scoped to those files, not a whole-owner census.
  StopRadio's separate seven-source historical first-stop cohort has a
  gated stored radio ID in each selected file. Five reach named-exact EOF;
  one advances to ActionHeader `0x00B6` and one to GetterBase `0x009F`.
  The gated OnClientGlobalVarChanged and GetInteractivePropertyInt readers
  then each reach named-exact EOF in their one selected file. The seven-file
  StopRadio cohort is source-scoped closed; no whole-owner census was rerun.
  A separate seven-file historical `0x04B7` cohort passes the gated
  StartNarrativeBlackScreenAndTeleport reader. Five files reach named-exact
  EOF. The newly exposed ActionBase `0x0471` source passes its selected gate
  and advances to ActionBase `0x0042`; the ActionHeader `0x00C9` source passes
  its selected gate and reaches named-exact EOF. The gated CharacterPlayMontage
  reader then reaches named-exact EOF in the remaining file. All seven
  selected files close; this is not a new whole-owner classification.
  FloatGetterPlus then closes both newly exposed files at named-exact EOF
  through 26 gated spans. Its two stored float inputs do not establish a
  runtime sum.
  OnSpecificEntityDie's three selected files all reach named-exact physical
  EOF after stored entity output paths and slot-based entity filters.
  OnSubGameStart's four selected files and OnNpcPatrolCheckpointReach's eight
  selected files also reach named-exact physical EOF. These are scoped
  closures; no live start or checkpoint event is observed.
  GetScriptTaskObjectiveIsCompleted's one selected file passes the getter,
  then the newly proved CheckIsInFacLinkingMode task condition, and reaches
  named-exact physical EOF through every task entry and triggerVolumes.
  This does not establish a completed runtime objective or a live facility link.
- StopEffectOnNpcProxy's selected ActionBase branch has 11 serialized members:
  eight inherited fields, then typed `Param<string>` effect ID,
  `Param<MountPoint>` and `Param<string>` NPC proxy ID. The complete native
  reader, three generic contexts, enum backing and eight current source
  spans agree on that order. All eight reached values are authored literals;
  the selected native/source validator does not observe effect removal or
  resolve a live proxy. Whole-owner closure awaits the combined corpus gate.
- SetMainCharHpBarActive's selected ActionBase branch has eight inherited
  fields followed by a typed `Param<bool>` active input. The complete native
  reader, generic context and nine current spans in seven historical
  first-stop files agree; eight spans store false and one true. These are
  authored values, not an observed HUD transition. The gated production layout
  and seven-file selected replay pass; whole-owner closure awaits the combined
  gate.
- GetterBase `0x01C5` IsEndminGender: the selected PureGetter
  branch has seven inherited fields and a typed `Param<Gender>` input. Its
  complete native reader, generic context, Int32 enum backing and three
  source spans in one selected file agree; all three store raw 2. Native
  enum members are Male=1 and Female=2, so the scalar projection's earlier
  0/1 labels were corrected. The stored Female input does not show a runtime
  gender check. The gated production layout and one-file selected replay pass;
  whole-owner closure awaits the combined gate.
- ActionBase `0x0521` ApplyMovementSettingModifier: the selected
  branch has eight inherited fields followed by a typed `Param<string>`
  modifier name. The complete native reader, generic string context and one
  ledger-joined span in the newly exposed file agree; it stores the literal
  key `MSM_Fallslow`. That authored key does not show a movement change.
  The gated production layout and one-file selected replay pass; whole-owner
  closure awaits the combined gate.
- ActionHeader `0x00E4` OnSubGameStart: the selected wrapper has
  14 inherited fields, then `filterSubGameId: Param<string>` and
  `outSubGameId: ParamOutput<string>`. The complete native reader, typed
  generic contexts and four ledger-joined spans in the newly exposed files
  agree. Those spans have a null filter and local output paths; no subgame
  start or output value is observed. The gated production layout and four-file
  selected replay pass; whole-owner closure awaits the combined gate.
- ActionBase `0x04EC` ToggleUI_DevOnly has eight inherited fields followed by
  typed `Param<bool>` isShow and `Param<string>` panelName inputs. The
  complete native reader, two generic contexts and one ledger-joined source
  span agree on that order; it stores true and `MainHud`. Its gated production
  layout and one-file selected replay reach named-exact EOF. No live UI state
  is observed; whole-owner closure awaits the combined gate.
- ActionBase `0x04AE` StartCutsceneAndHideSceneObjectAction has eight base
  fields, six inherited cinematic fields, then typed cutscene ID, extra
  stream position and load flag parameters plus a raw preload flag. Its
  inherited cinematic fields include interactive EntityPtr and scene-object
  ulong lists, override flags, and before/after mask parameters. The complete
  generated reader and chained fragments, nine typed generic contexts and
  two ledger-joined spans in one selected source agree on that order. Those
  spans hold authored cutscene keys and one entity pointer each; neither
  live cutscene playback nor scene visibility is observed. The gated
  production layout and one-file selected replay pass, advancing to
  ActionBase `0x04AD`; whole-owner closure awaits the combined gate.
- ActionBase `0x04AD` StartCutsceneAndControlSceneObjectAction has eight
  ActionBase fields, seven inherited cinematic fields, then typed cutscene
  ID, extra stream position and load flag parameters plus a raw preload
  flag. The cinematic fields include two EntityPtr lists, a scene-object
  ulong list, override flags and before/after masks. The complete generated
  reader and chained fragments, ten typed generic contexts and three
  ledger-joined spans in the selected source agree on that order. The spans
  store authored cutscene keys and target identifiers. The gated production
  layout and one-file selected replay reach named-exact EOF; neither live
  cutscene playback nor object visibility is observed. Whole-owner closure
  awaits the combined gate.
- FacGetBuildingPosition's complete reader stores `instKey` as
  `Param<string>`, `isAdjustGround` as `Param<bool>`, then `position`
  and `rotation` as distinct `ParamOutput<Vector3>` paths after the
  inherited action fields. Reached actions carry facility instance keys and
  matched local `_position`/`_rotation` output property paths; those paths
  are stored references, not observed world coordinates. The isolated
  validator is `scripts.game_data.levelscript_fac_get_building_position_native`.
- LevelEvent.OnEntityHpChanged's complete reader stores an Int32-backed
  `ChangedDirection` enum (`Down`, `Up`, `UpAndDown`),
  `Param<List<EntityPtr>>` entity filter, `ParamOutput<EntityPtr>`
  entity output, and `Param<float>` HP ratio. Reached source forms include
  a direct entity list or a property path for the filter, plus optional
  output paths. The specialized `entity_hp_changed.py` decoder presents
  some of these authored forms, but serialized fields do not establish a
  live HP event, a server exchange, or runtime resolution of entity paths.
  The isolated validator is
  `scripts.game_data.levelscript_entity_hp_changed_native`.
- SettlementUpgradeShow's complete reader stores `targetSettlementId` as
  `Param<string>` and `transitionTime` as `Param<float>`. Reached
  values are authored settlement keys and finite transition durations;
  these do not prove a live upgrade presentation. Its isolated validator is
  `scripts.game_data.levelscript_settlement_upgrade_show_native`.
- CheckPerformanceReady's inherited `value` is `Param<bool>` and its own
  `targetSettlementId` is `Param<string>`. Reached getters store a constant
  bool slot and authored settlement keys, not an observed readiness result.
  Its isolated validator is
  `scripts.game_data.levelscript_check_performance_ready_native`.
- EnvironmentEnable's own `enable` is `Param<bool>` and `envPtr` is
  `Param<EnvironmentVolumePtr>` after the inherited action fields. The
  pointed native struct has one stored 64-bit `id`; reached source spans
  contain authored IDs, not observed environment activation. Its isolated
  validator is `scripts.game_data.levelscript_environment_enable_native`.
- OnSettlementReadyPerformance has an exact selected native reader and
  ledger-joined spans from the CheckPerformanceReady and EnvironmentEnable
  cohorts. Its own `settlementId` is `ParamOutput<string>` after the inherited
  `validate: Param<bool>`. Reached headers store a true validation slot and
  output property paths, not an observed settlement readiness event. Its
  isolated validator is
  `scripts.game_data.levelscript_settlement_ready_performance_native`.
- AddBuffsToTargetSelves has an exact selected switch jump, complete reader,
  and ledger-joined source spans from the historical first-stop cohort. Its
  own fields are `blackboardKey: Param<EventArgsPtr>`, `buffId:
  Param<string>`, `buffs: ParamOutput<List<BuffPtr>>`, `targets:
  Param<List<EntityPtr>>`, and `useBlackboard: Param<bool>`. Reached values
  include authored buff keys, output paths and nullable or referenced target
  lists; no positive buff or entity list interior and no runtime buff
  application is established. Its isolated validator is
  `scripts.game_data.levelscript_add_buffs_to_target_selves_native`.
- SetSquadSpecialIdleEnable has a selected switch jump, complete generated
  reader and formatter, ten ordered reads and setters, and two typed
  `Param<bool>` contexts for its own `enable` and `enableSpMoveLoop` fields.
  The targeted, hash-checked sources have ledger-joined action spans that
  end exactly after these fields. Both parameters are reached as
  constant bool values with absent ID references and paths; the second is
  true in every selected span. This establishes stored flags, not runtime
  squad idle state. Its isolated validator is
  `scripts.game_data.levelscript_set_squad_special_idle_enable_native`.
- SetEnemyUIShowRange's complete selected reader stores its own
  `forceHide: Param<bool>`, `reset: Param<bool>`, and
  `showRange: Param<float>` after the inherited action fields. The selected
  ledger-joined source span contains constant true, false, and 20.0 values
  respectively, with absent ID references and paths. These are authored
  settings, not an observed enemy UI change. Its isolated validator is
  `scripts.game_data.levelscript_set_enemy_ui_show_range_native`.
- SetListBuff has no own serialized fields: its inherited `key` and `value`
  are both `Param<List<BuffPtr>>`. The complete selected native reader calls
  typed `ReadValue` contexts for each and the ledger-joined source span
  closes after both. Their reached list payloads are null; authored paths
  `tempbuffs` and `$1@_buffs` carry the references. This establishes stored
  paths, not positive buff-list contents or runtime assignment. Its selected
  validator is `scripts.game_data.levelscript_set_list_buff_native`.
- IsLookAtPointInScreen stores `direction`, `lookAt`, `lookAtType`,
  `mountPoint`, `npcProxyId`, `position`, `result`, and `rotation` after the
  inherited action fields. Its selected native reader spans linked code
  fragments and establishes sixteen ordered reads and setters, eight typed
  `Param` or `ParamOutput` contexts, and Int32 widths for both enum fields.
  Two ledger-joined spans in one selected source close exactly after these
  fields. The reached `direction`, `position`, and `rotation` are null; the
  `lookAt` EntityPtr contains no concrete ID; the enum values are raw 4 and
  51; `npcProxyId` carries authored proxy keys; and `result` carries local
  output paths. This proves stored inputs and output references, not runtime
  screen visibility. Its selected validator is
  `scripts.game_data.levelscript_is_look_at_point_in_screen_native`.
- PlayVoiceNarrative's own fields are `voiceHandle: ParamOutput<uint>` and
  `voId: Param<string>` after the inherited action fields. Its complete
  selected native reader and formatter establish ten ordered reads and
  setters and typed contexts for both own fields. The one ledger-joined
  source span closes after a local `$76@_voiceHandle` output path and the
  authored `au_radio_c31m3_2_001` voice key. The serialized fields prove
  neither playback nor a produced handle value. Its selected validator is
  `scripts.game_data.levelscript_play_voice_narrative_native`.
- ScriptedCharTeleportTo's own fields are `angle: Param<float>`,
  `entity: Param<EntityPtr>`, `eularAngle: Param<Vector3>`,
  `pos: Param<Vector3>`, and `useEularAngle: Param<bool>`. The complete
  selected native reader and formatter establish thirteen ordered reads
  and setters and five typed parameter contexts. Its one ledger-joined
  source span stores a finite angle and position, a null `eularAngle`,
  false `useEularAngle`, and an authored `$130@_entityOutput` entity path
  with no concrete entity ID. These are stored inputs, not an observed
  teleport or resolved target. Its selected validator is
  `scripts.game_data.levelscript_scripted_char_teleport_to_native`.
- ScriptedCharPatrolStart's own fields are `entity: Param<EntityPtr>`,
  `patrolId: Param<ulong>`, and `restart: Param<bool>`. The complete
  selected native reader and formatter establish eleven ordered reads
  and setters and three typed parameter contexts. Its one ledger-joined
  source span stores the authored `$130@_entityOutput` entity path with
  no concrete entity ID, unsigned patrol ID 35400010000, and a false
  restart flag. These are stored inputs, not an observed patrol start or
  resolved target. Its selected validator is
  `scripts.game_data.levelscript_scripted_char_patrol_start_native`.
- StopCharScriptedMode's own fields are `id: Param<string>`,
  `leaderIdType: int32` (a four-byte native enum),
  `newLeaderPresetId: Param<string>`, and `usePresetLeader: bool`.
  The complete selected reader and formatter prove twelve ordered reads
  and setters and two typed string parameter contexts. Its one
  ledger-joined source span stores authored id `dc563c90`, raw enum zero,
  null preset id, and false preset flag. These are stored inputs; the
  enum's semantic choice and runtime mode termination remain unobserved.
  Its selected validator is
  `scripts.game_data.levelscript_stop_char_scripted_mode_native`.
- GetCurSquadAllDead stores only the seven inherited PureGetter node fields.
  Its complete selected reader and forwarding formatter establish those
  ordered reads and setters; six hash-checked, ledger-joined source spans
  close immediately after the inherited fields. The compact union header
  stores a one-byte tag and one-byte member count. No squad-state payload
  or getter result is serialized in this node, and live squad state is
  unobserved. Its selected validator is
  `scripts.game_data.levelscript_get_cur_squad_all_dead_native`.
- GetCharacterTemplateId adds `entity: Param<EntityPtr>` after seven
  inherited PureGetter fields. Its complete selected reader and formatter
  establish eight ordered reads and setters and a typed entity parameter
  context. The one ledger-joined source span stores an authored
  `$130@_entityOutput` path with no concrete entity ID. It establishes
  neither a resolved entity nor the template ID produced at runtime. Its
  selected validator is
  `scripts.game_data.levelscript_get_character_template_id_native`.
- NpcGetPackAnimHasClean adds `target: Param<EntityPtr>` after seven
  inherited PureGetter fields. Its complete selected reader and formatter
  establish eight ordered reads and setters and a typed entity parameter
  context. Seven ledger-joined source spans carry literal logic IDs in the
  selected map scripts, without a path or slot ID. They prove stored target
  references, not resolved entities or a runtime animation-state result.
  Its selected validator is
  `scripts.game_data.levelscript_npc_get_pack_anim_has_clean_native`.
- ScriptEvent.OnStartScriptControlledCharMode stores
  `entityOutput: ParamOutput<EntityPtr>` and
  `scriptedIdFilter: Param<string>` after sixteen inherited header fields.
  The complete selected reader and formatter establish eighteen ordered
  reads and setters, four typed parameter contexts, and four-byte enum
  storage in the header. Its one ledger-joined span has `validate` true,
  null `targetScript`, raw `triggerTarget` zero, the local
  `$130@_entityOutput` output path, and authored scripted ID `dc563c90`.
  These are stored filters and references, not an observed event or
  produced entity. Its selected validator is
  `scripts.game_data.levelscript_on_start_script_controlled_char_mode_native`.
- LevelEvent.OnSpawnerPause stores `pauseKeyFilter: Param<string>`,
  `pauseKeyOutput: ParamOutput<string>`,
  `spawnerFilter: Param<SpawnerPtr>`, and
  `spawnerOutput: ParamOutput<SpawnerPtr>` after fourteen inherited event
  fields. Its complete selected reader and formatter establish eighteen
  ordered reads and setters, five typed parameter contexts, and four-byte
  enum storage. Three ledger-joined spans carry authored `Pause4CS` or
  `Pause` keys and concrete spawner IDs; both output parameters are null.
  This proves stored filters, not a paused spawner or an emitted event.
  Its selected validator is `scripts.game_data.levelscript_on_spawner_pause_native`.
- BuildingPosHintShow stores `buildingId: Param<string>`,
  `handleOutput: ParamOutput<uint>`,
  `worldDir: Param<BuildingPosHintShow.EBuildingRot>`, and
  `worldPos: Param<Vector3>` after eight inherited action fields. Its
  complete selected reader and formatter establish twelve ordered reads
  and setters and four typed parameter contexts. Native metadata resolves
  the wire enum's dotted alias to the nested `EBuildingRot` type, with Int32
  backing and named values `UP=0`, `RIGHT=1`, `DOWN=2`, `LEFT=3`.
  The selected spans carry authored building IDs, local handle output
  paths, finite world positions and raw rotation values 0, 1 or 3.
  They do not establish displayed hints or produced handles. Its selected
  validator is `scripts.game_data.levelscript_building_pos_hint_show_native`.
- BuildingPosHintHide adds `handle: Param<uint>` after eight inherited
  action fields. Its complete selected reader and formatter establish nine
  ordered reads and setters and a typed unsigned-handle context. Eighteen
  ledger-joined spans in the newly exposed files store zero literal handle
  values with source-100 authored paths, including local `_handleOutput`
  paths and named `Hint` references. The paths do not establish produced
  handle values or runtime hint removal. Its selected validator is
  `scripts.game_data.levelscript_building_pos_hint_hide_native`.
- FacGuideHintEnable stores `enable: Param<bool>` and
  `hintId: Param<string>` after eight inherited action fields. Its complete
  selected reader and formatter establish ten ordered reads and setters and
  both typed parameter contexts. Four ledger-joined spans in the two newly
  exposed source files store constant true or false and authored
  `ConveyorGuideHint_1`, `ConveyorGuideHint_2`, or `pipe_hint_01` keys,
  all with absent ID references and paths. These are stored inputs, not
  observed guide-hint visibility. Its selected validator is
  `scripts.game_data.levelscript_fac_guide_hint_enable_native`.
- SetDecorationAnimatorInt stores `animatorParamName`, `groupName`, and
  `sceneName` as `Param<string>`, `targetDynamicEntity: Param<ulong>`, and
  `targetValue: Param<int>` after eight inherited action fields. Its
  complete selected reader and formatter establish thirteen ordered reads
  and setters and five typed parameter contexts. The eight historical
  first-stop source spans are ledger-joined and end exactly after those
  fields. They store the authored animator parameter `state`, null group
  and scene names, nonzero dynamic entity IDs, and integer values zero or
  one. Some null scene parameters use source 1000. These are stored inputs,
  not observed animator state changes or resolved scene objects. Its
  selected validator is
  `scripts.game_data.levelscript_set_decoration_animator_int_native`.
- SetDecorationViewState stores `groupName: Param<string>`,
  `mountPoint: Param<Deco_MountPoint>`, `sceneName: Param<string>`,
  `targetDynamicEntity: Param<ulong>`, and `targetState: Param<string>`
  after eight inherited fields. The selected switch, complete thirteen-field
  reader and formatter, ordered setters, and five typed contexts join one
  newly exposed source span. Native metadata proves that
  `Beyond.Gameplay.Deco_MountPoint` is byte-backed with sixteen named values;
  the selected span stores value zero, an authored group and scene, a dynamic
  entity ID, and the string `active`. These are stored references, not an
  observed decoration state change. The gated production layout and one-file
  replay pass; whole-owner closure awaits the combined gate. Its selected
  validator is `scripts.game_data.levelscript_set_decoration_view_state_native`.
- EntityMoveToWithSpeed stores seven own inputs after eight inherited action
  fields: ease, end position, entity, relative movement distance, speed,
  tween output, and a relative-mode flag. The selected switch, complete
  fifteen-member reader and formatter, ordered setters, seven typed generic
  contexts, and Int32 TweenEase enum backing join 63 exact spans in seven
  historical first-stop files. Reached ease values are named enum members;
  movement vectors, speeds, entities, and output paths remain stored inputs.
  The native gate and selected replay pass: four files reach named-exact EOF,
  two reach GetterBase `0x0046`, and one reaches ActionBase `0x0316`.
  Runtime movement and whole-owner closure remain unobserved. Its selected
  validator is `scripts.game_data.levelscript_entity_move_to_with_speed_native`.
- MoveBambooLast stores one own `entity: Param<EntityPtr>` after eight
  inherited action fields. The selected switch, complete nine-member reader
  and formatter, ordered reads and setters, typed entity parameter context,
  and one ledger-joined source span prove a stored slot-based entity
  reference. Its one-file replay advances to a later ActionBase union; neither
  movement nor entity resolution is observed. Its selected validator is
  `scripts.game_data.levelscript_move_bamboo_last_native`.
- SetBambooPosIndex stores `entityList: Param<List<EntityPtr>>` and
  `index: Param<int>` after eight inherited action fields. Its selected
  switch, complete ten-member reader and formatter, ordered reads and
  setters, two typed generic contexts including the nested EntityPtr list
  element, and one ledger-joined source span prove the stored layout. The
  reached list has two slot-based entity references and a constant index
  zero. Its gated production layout and one-file selected replay pass,
  advancing that file to ActionHeader `0x00A2`; no Bamboo position change
  or entity resolution is observed, and whole-owner closure awaits a
  combined gate. Its validator is
  `scripts.game_data.levelscript_set_bamboo_pos_index_native`.
- StopRadio stores `radioId: Param<string>` after eight inherited action
  fields. The selected switch, complete nine-member reader and formatter,
  ordered reads and setters, typed string context, and seven ledger-joined
  historical first-stop spans prove authored constant radio IDs. The native
  gate and seven-file selected replay pass: five files reach named-exact
  EOF, one reaches ActionHeader `0x00B6`, and one GetterBase `0x009F`.
  Runtime radio playback and stopping remain unobserved, and whole-owner
  closure awaits the combined gate. Its selected validator is
  `scripts.game_data.levelscript_stop_radio_native`.
- OnClientGlobalVarChanged stores `key: Param<string>` and
  `newValue`/`oldValue: ParamOutput<long>` after fourteen inherited event
  fields. The selected switch, complete seventeen-member reader and
  formatter, ordered reads and setters, four typed contexts, and one
  ledger-joined source span prove a stored mission-variable key and two
  local long output paths. The reached validation bool is a getter
  reference. Its gated production layout and single-source replay reach
  named-exact EOF. The key and paths do not prove a live value change or
  resulting values; whole-owner closure awaits the combined gate. Its
  validator is
  `scripts.game_data.levelscript_on_client_global_var_changed_native`.
- StartFmvAndTeleportAction stores 15 inherited action fields, including two
  `Param<CommonMaskBlendData>` masks, level and teleport strings, position
  and rotation vectors, and an Int32-backed `Param<TeleportUIType>`, then its
  own `fmvId: Param<string>`. The selected switch, complete sixteen-field
  reader and formatter, ordered setters, eight typed contexts, enum members,
  and one ledger-joined span prove the stored layout. That span carries an
  authored FMV key, teleport key, finite coordinates, and UI enum value zero.
  No FMV playback or teleport is observed. The gated production layout and
  one-file replay pass; whole-owner closure awaits the combined gate. Its
  selected validator is
  `scripts.game_data.levelscript_start_fmv_and_teleport_native`.
- StartNarrativeBlackScreenAndTeleport stores 15 inherited action fields,
  including mask, level, position, rotation, teleport ID and UI type inputs,
  followed by twelve own narrative and audio parameters. The selected
  ActionBase switch, complete 27-field reader and formatter, ordered reads
  and setters, nineteen typed `Param` contexts and three native enum
  definitions prove the stored layout. Two audio enum types have Byte
  backings; one has repeated numeric IDs for named aliases. All seven
  ledger-joined historical first-stop spans contain one positive LangKey
  text entry and an authored teleport ID. The gated seven-file replay
  reaches named-exact EOF in five and advances to ActionBase `0x0471` and
  ActionHeader `0x00C9` in the other two. Narrative playback, black-screen
  display and teleport are unobserved; whole-owner closure awaits a
  combined gate. Its validator is
  `scripts.game_data.levelscript_start_narrative_black_screen_teleport_native`.
- SetSquadEnableRelaxIdle stores `enable: Param<bool>` after eight inherited
  action fields. The selected switch, complete nine-field reader and
  formatter, ordered setter and typed bool context join one exact
  ledger-backed source span. That span stores false. Its gated production
  layout advances the one selected file to ActionBase `0x0042`; a live idle
  change is unobserved. The validator is
  `scripts.game_data.levelscript_set_squad_enable_relax_idle_native`.
- CharacterPlayMontage stores eighteen own parameters after eight inherited
  action fields. The selected switch, complete 26-field reader and formatter,
  ordered setters, eighteen typed `Param` and `ParamOutput` contexts, and one
  exact ledger-backed span prove the stored layout. The selected span contains
  a gameplay tag, output-handle path, finite position, character template ID,
  and finite blend and play-rate values. Its gated one-file replay reaches
  named-exact EOF. Montage playback, entity selection, and output-handle
  delivery remain unobserved. The validator is
  `scripts.game_data.levelscript_character_play_montage_native`.
- OnScriptPreStart has sixteen inherited event fields, including
  `validate: Param<bool>`, `targetScript: Param<LevelScriptPtr>`, and a
  scalar32 trigger target enum. The selected switch, complete reader and
  formatter, ordered setters, typed parameter contexts and one exact
  ledger-backed source span prove the stored layout. That span stores true
  validation, a null targetScript and trigger target zero. Its selected
  replay reaches named-exact EOF; no live pre-start event is observed. The
  validator is `scripts.game_data.levelscript_on_script_pre_start_native`.
- DisableHudFade stores `showHud: Param<bool>` after eight inherited fields.
  The selected switch, complete nine-field reader and formatter, ordered
  setters, typed bool context, and one ledger-joined span prove the stored
  true flag. No live HUD fade is observed. The gated production layout and
  one-file replay pass; whole-owner closure awaits the combined gate. Its
  selected validator is `scripts.game_data.levelscript_disable_hud_fade_native`.
- FloatGetterIntToFloat stores `value: Param<int>` after seven inherited
  getter fields. The selected PureGetter switch, complete eight-member
  reader and formatter, ordered setters, typed integer parameter context,
  and one ledger-joined source span prove the stored layout. The reached
  value is a local getter reference. Its gated production layout and one-file
  selected replay pass, advancing to a positive two-element encounter opera
  list. The separately gated nested reader then reaches named-exact EOF in
  that selected file; runtime conversion remains unobserved, and whole-owner
  corpus closure awaits a combined gate. Its
  selected validator is `scripts.game_data.levelscript_float_getter_int_to_float_native`.
- The positive Encounter `introPart.operaSegments` reader accepts the two
  source-reviewed list lengths, each with one keyed parameter and one value
  atom per segment. Four complete native wrapper readers authenticate the
  nested fields. The newly exposed source has two records with stored type
  values 1 and 2, both keyed by `id`, holding `dlg_e7m4_1` and
  `cutscene_e7m4_1`; its hash-checked span rejoins the owner and the one
  selected file reaches named-exact physical EOF. These keys do not prove
  dialogue or cutscene execution. Other positive list lengths and deeper
  child shapes remain unsupported.
- FloatGetterPlus stores `valueA` and `valueB` as `Param<float>` after seven
  inherited getter fields. The selected PureGetter switch, complete
  nine-member reader and formatter, ordered setters, two typed contexts,
  and 26 ledger-joined spans in two newly exposed files prove the stored
  inputs. In every reached span, `valueA` is an authored source-100 local Y
  property path and `valueB` is a source-0 float constant. The native gate
  passes and selected replay reaches named-exact EOF in both files. Runtime
  addition and whole-owner closure remain unobserved. Its validator is
  `scripts.game_data.levelscript_float_getter_plus_native`.
- GetInteractivePropertyInt stores `entity: Param<EntityPtr>` and
  `key: Param<string>` after seven common getter fields; both are inherited
  through its property-getter base. The selected PureGetter dispatch, complete
  chained reader and formatter, nine ordered reads and setters, two typed
  `ReadValue` contexts, and one ledger-joined exact span prove those stored
  inputs. The selected entity has a logic ID and the key is `state`; neither
  establishes the runtime property value. Its gated one-file replay reaches
  named-exact EOF. Whole-owner closure remains provisional. The validator is
  `scripts.game_data.levelscript_get_interactive_property_int_native`.
- GetMissionSavePropertyInt stores `missionId: Param<string>` and
  `path: Param<string>` after seven inherited getter fields. The selected
  PureGetter dispatcher, complete nine-member reader and formatter, ordered
  setters, both typed string contexts, and seven ledger-joined historical
  first-stop spans prove the stored inputs. Its native gate and selected
  seven-file replay reach named-exact EOF in every file. Runtime mission-save
  lookup, integer result and whole-owner closure remain unobserved. The
  validator is `scripts.game_data.levelscript_get_mission_save_property_int_native`.
- BoolGetterMultOr stores a `Param<bool>[]` list after seven inherited
  getter fields. Its selected PureGetter switch, complete eight-member
  reader and formatter, ordered setters, typed `ReadArray<Param<bool>>`
  context, and one ledger-joined source span prove the stored layout. The
  selected span has six local boolean getter references; their values and
  the runtime OR result are unobserved. Its gated production layout and
  one-file selected replay reach named-exact EOF. Whole-owner closure
  awaits the combined gate; the validator is
  `scripts.game_data.levelscript_bool_getter_mult_or_native`.
- NpcStopCurMontage stores `montageMaskType:
  Param<ENPCAnimationAvatarMaskType>` and `npcId: Param<string>` after
  eight inherited action fields. Its complete selected reader and formatter
  establish ten ordered reads and setters, and both typed parameter
  contexts. Native metadata proves an Int32-backed avatar mask enum with
  eight named values. Eight historical first-stop source spans are
  ledger-joined and close after these fields; each stores raw zero
  (`Default`) for the mask and a null NPC string with a getter-reference
  ID, not a concrete NPC name. These are stored inputs, not an observed
  montage stop or resolved NPC. Its selected validator is
  `scripts.game_data.levelscript_npc_stop_cur_montage_native`.
- DestroyAbilityEntity stores `target: Param<EntityPtr>` after eight
  inherited action fields. Its complete selected reader and formatter
  establish nine ordered reads and setters and a typed entity parameter
  context. The three newly exposed, ledger-joined source spans close after
  a slot-based target with `useSlotId` true and no concrete logic ID.
  This proves the stored target reference, not runtime entity resolution
  or destruction. Its selected validator is
  `scripts.game_data.levelscript_destroy_ability_entity_native`.
  The gated production layout and three-file selected replay pass; whole-owner
  closure awaits the combined gate.
- SkipEntityDieDisplay stores `target: Param<EntityPtr>` after eight inherited
  action fields. Its selected switch branch, complete native reader and
  forwarding formatter, typed entity context, and one ledger-joined source
  span agree on that order. The selected target uses a slot ID without a
  concrete logic ID; no live death presentation is observed. Its validator is
  `scripts.game_data.levelscript_skip_entity_die_display_native`. The gated
  production layout and one-file selected replay pass; whole-owner closure
  awaits the combined gate.
- CheckIsInFacLinkingMode is a six-member GameCondition in a LevelScript
  task map: four inherited scope/identity fields, `Param<bool>` for the
  requested linking state, and `Param<LinkType>` for the selected link type.
  The selected native switch, complete reader and formatter, ordered reads
  and setters, two typed parameter contexts, and current source span agree.
  Native enum defaults prove an Int32-backed `LinkType` with named values.
  The selected task stores true and `PowerPole`; its full owner reaches
  physical EOF. Runtime condition truth and facility
  state remain unresolved. The validator is
  `scripts.game_data.levelscript_check_fac_linking_mode_native`; the separate
  codec admits this condition only while its native gate validates.
- OnSpecificEntityDie stores `entity: ParamOutput<EntityPtr>` and
  `filterEntity: Param<EntityPtr>` after fourteen inherited event fields.
  Its complete native reader and formatter, typed entity contexts, and three
  ledger-joined spans agree on that order. Each selected source stores an
  authored output path and the same slot-based entity filter; neither proves
  which entity died at runtime. The gated production layout and three-file
  selected replay pass; whole-owner closure awaits the combined gate. Its
  validator is `scripts.game_data.levelscript_on_specific_entity_die_native`.
- OnSpecificEntityListDie stores `entity: ParamOutput<EntityPtr>` and
  `filterEntityList: Param<List<EntityPtr>>` after fourteen inherited event
  fields. The selected switch, complete sixteen-member reader and
  formatter, ordered reads and setters, three typed contexts including the
  nested EntityPtr list element, and one ledger-joined source span prove the
  stored layout. The reached list holds three slot-based entity references;
  the entity output names an authored local path. Its gated production
  layout and one-file selected replay reach named-exact EOF. Neither the
  event firing nor entity resolution is observed, and whole-owner closure
  awaits a combined gate. Its validator is
  `scripts.game_data.levelscript_on_specific_entity_list_die_native`.
- TeleportGameplayNpc stores `npcId: Param<string>`, `pos:
  Param<Vector3>`, and `rot: Param<Vector3>` after eight inherited action
  fields. Its selected native reader includes a hot entry and chained
  fragments; the contract authenticates all eight code windows, eleven
  ordered reads and setters, and three typed parameter contexts. Eight
  newly exposed, ledger-joined source spans close after authored NPC keys
  and position/rotation paths with source 200. The stored vector payloads
  are zero placeholders for those references; they do not establish
  resolved world coordinates or an observed teleport. Its selected
  validator is `scripts.game_data.levelscript_teleport_gameplay_npc_native`.
  The gated production layout and eight-file selected replay pass; whole-owner
  closure awaits the combined gate.
- SetSquadIconActive stores `hide: Param<bool>` after eight inherited
  action fields. Its complete selected reader and formatter establish nine
  ordered reads and setters and a typed bool parameter context. Two newly
  exposed, ledger-joined source spans close exactly after constant false
  and true values with absent ID references and paths. These are authored
  flags, not observed squad icon visibility. Its selected validator is
  `scripts.game_data.levelscript_set_squad_icon_active_native`.
  The gated production layout and two-file selected replay pass; whole-owner
  closure awaits the combined gate.
- ListMakeEntityPtr has no own serialized fields: its inherited PureGetter
  `list` is `Param<EntityPtr>[]`. The selected native reader calls the typed
  `ReadArray<Param<EntityPtr>>` specialization, and the hash-checked source
  spans close after a counted list. Each reached list contains one
  getter-reference child (`idRef` present, `paramSource=-1`, no path), with
  no stored concrete entity ID. The array helper accepts only that child
  framing in positive lists. This proves stored references, not a runtime
  list result or resolved entities. Its isolated validator is
  `scripts.game_data.levelscript_list_make_entity_ptr_native`.
- GetterEntityPtr has no own serialized fields: its inherited PureGetter
  `value` is `Param<EntityPtr>`. Its selected native reader is split across
  linked code fragments; the contract authenticates all fragments, the
  eight ordered field reads and setters, and a typed
  `ReadValue<Param<EntityPtr>>` context. The two hash-checked targeted
  cohorts yield ledger-joined spans whose values store the `Target`
  property path with no concrete entity ID. This proves authored reference
  storage, not a resolved entity or runtime getter result. Its isolated
  validator is `scripts.game_data.levelscript_getter_entity_ptr_native`.
- GetterListBuff has no own serialized fields: its inherited PureGetter
  `value` is `Param<List<BuffPtr>>`. The complete selected native reader and
  forwarding formatter establish eight ordered reads and setters with a
  typed `ReadValue<Param<List<BuffPtr>>>` context. The one hash-checked,
  ledger-joined source span closes after that value. Its list payload is
  null and its authored `tempbuffs` path carries the reference; this proves
  neither positive list contents nor the runtime getter result. Its
  selected validator is `scripts.game_data.levelscript_getter_list_buff_native`.
- GetterLevelScriptPtr has no own serialized fields: its inherited
  PureGetter `value` is `Param<LevelScriptPtr>`. The complete selected native
  reader stores eight ordered fields and calls typed
  `ReadValue<Param<LevelScriptPtr>>`. The two hash-checked source cohorts
  have ledger-joined spans whose value stores the `cameraScript` property
  path and an empty literal script ID. This proves an authored reference,
  not the script selected at runtime. Its selected native validator is
  `scripts.game_data.levelscript_getter_levelscript_ptr_native`.
- GetScriptTaskObjectiveIsCompleted's selected PureGetter reader stores
  seven inherited fields, then `objectiveEnum: Param<TaskObjectiveEnum>`,
  `scriptPtr: Param<LevelScriptPtr>`, and `taskKey: Param<ScriptTaskPtr>`.
  The direct switch branch, complete reader and forwarding formatter, ten
  ordered reads and setters, three typed parameter contexts, signed Int32
  objective enum and one ledger-joined source span establish the stored
  shape. The reached value selects raw objective zero, current-script mode,
  and an authored task key. They do not establish the task's completion
  state or a resolved script pointer. Its selected validator is
  `scripts.game_data.levelscript_get_script_task_objective_is_completed_native`.
- EntityToString stores `value: Param<EntityPtr>` after seven inherited
  getter fields. Its selected native reader, typed parameter context and
  ledger-joined source span establish an authored `$101@_entity` path with
  no observed runtime entity. The serialized value does not establish the
  string produced at execution. Its selected validator is
  `scripts.game_data.levelscript_entity_to_string_native`.
- LevelEvent.OnSpawnerStart's selected ActionHeader reader stores 14
  inherited fields, then `spawnerFilter: Param<SpawnerPtr>` and
  `spawnerOutput: ParamOutput<SpawnerPtr>`. Its direct switch branch,
  complete reader and forwarding formatter, ordered setters, typed parameter
  contexts and ledger-joined selected source spans establish stored fields.
  Those spans use a zero constant in the filter with a source-200 `spawner`
  property path and an output property path. Zero is a placeholder here, not
  a resolved spawner identity; event execution and output values remain
  unobserved. The selected validator is
  `scripts.game_data.levelscript_on_spawner_start_native`.
- LevelEvent.OnSpellAbnormalStart's selected ActionHeader reader stores 14
  inherited fields, then an entity filter and output, source output,
  `typeFilter: Param<SpellAbnormalType>`, type output, and
  `useEntityFilter: Param<bool>`. The direct switch branch, complete reader
  and forwarding formatter, ordered setters, typed parameter contexts,
  signed Int32 enum backing and members, and ledger-joined selected source
  spans prove the stored layout. Reached entity filters are `Target`
  property paths with zero literal identities; type filters store authored
  enum constants. The output paths do not prove returned entities, and no
  spell-abnormal event execution is observed. The selected validator and
  enum-gated cursor are `scripts.game_data.levelscript_on_spell_abnormal_start_native`
  and `codecs.levelscript.on_spell_abnormal_start`.
- EntityEvent.OnPhysicalNoGuard's selected ActionHeader reader stores 14
  inherited fields, then `countOutput: ParamOutput<int>`,
  `entityFilter: Param<EntityPtr>`, `entityOutput: ParamOutput<EntityPtr>`,
  and `sourceOutput: ParamOutput<EntityPtr>`. Its direct switch branch,
  complete reader and forwarding formatter, ordered setters, typed parameter
  contexts and ledger-joined selected source spans prove the stored layout.
  Reached entity filters are `Target` property paths with zero literal
  identities; the count, entity and source fields hold local output paths.
  No physical no-guard event or output value is observed. The selected
  validator is `scripts.game_data.levelscript_on_physical_no_guard_native`.
- EntityEvent.OnPhysicalInfliction's selected ActionHeader reader stores 14
  inherited fields, then an entity filter and output,
  `inflictionTypeFilter: Param<PhysicalInflictionType>`, an Int32 output,
  source output and two Boolean filter flags. The direct switch branch,
  complete reader and forwarding formatter, ordered setters, typed
  parameter contexts, signed Int32 enum backing and members, and
  ledger-joined selected source spans prove the stored layout. The reached
  filters refer to the authored `Target` path with zero literal entity ID
  and hold enum constants; the other fields hold local output paths. No
  physical infliction event or output value is observed. The selected
  validator and enum-gated cursor are
  `scripts.game_data.levelscript_on_physical_infliction_native` and
  `codecs.levelscript.on_physical_infliction`. A later selected file stores
  a nullable type filter; the cursor preserves that null marker before
  checking enum values on present filters.
- LevelEvent.OnSpawnerWaveBegin's selected ActionHeader reader stores 14
  inherited fields, then `spawnerFilter: Param<SpawnerPtr>`,
  `spawnerOutput: ParamOutput<SpawnerPtr>`, `waveKeyFilter: Param<string>`,
  and `waveKeyOutput: ParamOutput<string>`. Its direct switch branch,
  complete reader and forwarding formatter, ordered setters, typed parameter
  contexts and ledger-joined selected source spans prove the stored layout.
  Reached spawner filters hold zero literal IDs with a source-200 `spawner`
  property path, while wave-key filters are null and the outputs hold local
  property paths. No resolved spawner, active wave or event execution is
  observed. The selected validator is
  `scripts.game_data.levelscript_on_spawner_wave_begin_native`.
- ScriptEvent.OnBBVariableChanged's selected ActionHeader reader stores 14
  common event fields, inherited `targetScript: Param<LevelScriptPtr>` and
  an Int32-backed `TriggerTarget`, then `key: Param<string>` and distinct
  `oldValue`/`value: ParamOutput<object>` paths. Its direct switch branch,
  complete hot and chained reader and forwarding formatter, ordered
  setters, typed generic contexts, enum width, and ledger-joined selected
  source spans prove the stored layout. Reached target scripts are null;
  keys are authored `Progress` or `ProgressShatter` strings, while old/new
  values are only local output paths. No live blackboard value or event
  execution is observed. The selected validator and cursor are
  `scripts.game_data.levelscript_on_bb_variable_changed_native` and
  `codecs.levelscript.on_bb_variable_changed`.
- LevelEvent.OnAetherEnergyLockEndPointScanned's selected ActionHeader
  reader stores 14 inherited fields followed by
  `filterEntity: Param<EntityPtr>`. The direct switch branch, complete
  reader and forwarding formatter, 15 ordered reads and setters, two typed
  parameter contexts, and ledger-joined selected source spans prove this
  stored shape. The two reached source files have three headers whose
  entity filters carry authored logic IDs, with no property path. Those
  constants do not prove that an endpoint was scanned or that the event
  ran. The selected validator is
  `scripts.game_data.levelscript_on_aether_lock_endpoint_scanned_native`.
- LevelEvent.OnCutsceneExit's selected ActionHeader reader stores 14
  inherited fields, then `cutsceneId: ParamOutput<string>`,
  `filteredCutsceneId: Param<string>`, and `isSkip: ParamOutput<bool>`.
  The direct switch branch, complete reader and forwarding formatter,
  ordered setters, typed parameter contexts, and ledger-joined selected
  source spans establish this stored layout. The two reached headers have
  authored cutscene filter strings and local skip output paths;
  `cutsceneId` is null in both. Neither cutscene playback nor an exit event
  is observed. The selected validator is
  `scripts.game_data.levelscript_on_cutscene_exit_native`.
- LevelEvent.OnServerDialogExit's selected ActionHeader reader stores 14
  inherited fields, then `dialogId: ParamOutput<string>` and
  `dialogIdFilter: Param<string>`. The selected switch branch, complete
  reader entry and chained fragments, forwarding formatter, 16 ordered
  reads and setters, and three typed parameter contexts establish this
  stored layout. Eight ledger-joined spans from the historical unknown
  cohort store true validation flags, null dialog ID outputs, and authored
  dialog filter keys. No server dialog exit event or emitted dialog ID is
  observed. Its selected validator is
  `scripts.game_data.levelscript_on_server_dialog_exit_native`.
- LevelEvent.OnNpcPatrolCheckpointReach's selected ActionHeader reader stores
  14 inherited fields, then `filteredNpcEntity: Param<EntityPtr>`,
  `filteredPatrolId: Param<int>`, `filteredPointIndex: Param<int>`,
  `npcEntity: ParamOutput<EntityPtr>`, `npcPosition: ParamOutput<Vector3>`,
  `patrolId: ParamOutput<int>`, and `pointIndex: ParamOutput<int>`. The
  selected switch branch, complete reader and forwarding formatter, 21
  ordered reads and setters, eight typed parameter contexts, and eight
  ledger-joined spans establish the stored layout. Selected filters contain
  authored NPC paths and patrol/point integers; the entity and integer
  outputs are null, and the position output is a local property path. No
  checkpoint event, resolved entity, or emitted output is observed. Its
  selected validator is
  `scripts.game_data.levelscript_on_npc_patrol_checkpoint_reach_native`.
  The gated production layout and eight-file selected replay pass; whole-owner
  closure awaits the combined gate.
- LevelEvent.OnSpawnerGroupComplete's selected ActionHeader reader stores 14
  inherited fields, then `groupKeyFilter: Param<string>`,
  `groupKeyOutput: ParamOutput<string>`, `spawnerFilter: Param<SpawnerPtr>`,
  and `spawnerOutput: ParamOutput<SpawnerPtr>`. The selected switch branch,
  complete reader and forwarding formatter, 18 ordered reads and setters,
  five typed parameter contexts, and one ledger-joined newly exposed span
  establish the stored layout. That span carries an authored group key and
  SpawnerPtr ID with both outputs null. No spawner-group completion event or
  emitted output is observed. Its selected validator is
  `scripts.game_data.levelscript_on_spawner_group_complete_native`. The
  selected one-file replay reaches named-exact physical EOF; whole-owner
  closure awaits the combined gate.
- EntityEvent.OnEntityDie's selected ActionHeader reader stores 14 common
  fields plus inherited `targetEntity: Param<EntityPtr>`,
  `targetEntityList: Param<List<EntityPtr>>`,
  `targetEntityListOutput: ParamOutput<EntityPtr>`, and an Int32-backed
  `TriggerTarget`. Its direct switch branch, complete reader and forwarding
  formatter, ordered setters, typed list and pointer contexts, enum width,
  and ledger-joined selected source spans prove the stored layout. Reached
  headers carry one authored logic ID or authored slot IDs; the entity
  list payload and list output are null, and `triggerTarget` stores one.
  No resolved entity death event is observed. The selected validator and
  cursor are `scripts.game_data.levelscript_on_entity_die_native` and
  `codecs.levelscript.on_entity_die`.
- The selected `LevelEnemyData` wrapper reads `enemyDefaultActionType` as
  signed Int32 and `extraDelayToRecycleTime` as an eight-byte
  `Nullable<float>` before the following fields. Native enum metadata names
  only `Patrol=0`; one authored `LevelScriptData` source stores raw `1`,
  so the codec preserves that number without assigning a meaning. Its
  nonzero nullable value is laid out as a flag, three zero padding bytes,
  then a float, and yields 120.0. The corrected codec reaches exact EOF in
  that selected source. This proves stored framing and value, not enemy
  behavior or a semantic name for raw `1`. The selected validator is
  `scripts.game_data.level_enemy_default_action_native`.
- LevelEvent.OnBlightMiasmaWeakGuide's selected ActionHeader reader stores
  14 inherited fields followed by `key: Param<string>`. Its direct switch
  branch, complete reader and forwarding formatter, ordered setters, typed
  parameter contexts and one ledger-joined source span prove that stored
  layout. The reached header holds the authored key `all_guideline_area1`,
  without a property path. No guide event execution is observed. The
  selected validator is
  `scripts.game_data.levelscript_on_blight_miasma_weak_guide_native`.
- LevelEvent.OnNpcDirtyBlockCleaned's selected ActionHeader reader stores
  14 inherited fields followed by `selfId: ParamOutput<EntityPtr>`. The
  direct switch branch, complete reader and forwarding formatter, all 15
  ordered setters, typed parameter contexts and seven ledger-joined source
  spans establish this stored layout. The reached outputs are local paths;
  they do not provide a resolved entity ID or show that a dirty block was
  cleaned. The selected validator is
  `scripts.game_data.levelscript_on_npc_dirty_block_cleaned_native`.
- LevelEvent.OnAnyEntityDie's complete selected ActionHeader reader stores
  14 inherited fields, then `entity: ParamOutput<EntityPtr>`,
  `entityList: Param<List<EntityPtr>>`, `filterByList: Param<bool>`, and
  `isMonster: Param<bool>`. The direct switch entry, eighteen ordered reads
  and setters, five typed parameter contexts and ledger-joined source span
  establish these stored fields. The reached entity list has a null payload
  and a getter reference to local ID 16; `entity` holds the local
  `$17@_entity` output path, while `filterByList` and `isMonster` store
  true and false. This proves neither a resolved list nor event execution.
  Its selected validator is
  `scripts.game_data.levelscript_on_any_entity_die_native`.
- LevelEvent.OnAnyEnemyPoiseZero's complete selected ActionHeader reader
  stores 14 inherited fields, then `attacker` and `entity` as distinct
  `ParamOutput<EntityPtr>` fields. The direct switch entry, sixteen ordered
  reads and setters, three typed parameter contexts, and one ledger-joined
  source span establish the stored layout. The reached outputs hold the
  separate `$20@_attacker` and `$20@_entity` paths; no enemy poise event or
  output value is observed. Its selected validator is
  `scripts.game_data.levelscript_on_any_enemy_poise_zero_native`.
- LevelEvent.OnAnyEnemyPoiseKnotBreak's complete selected ActionHeader
  reader stores 14 inherited fields, then `attacker` and `entity` as
  distinct `ParamOutput<EntityPtr>` fields and `knotIndex` as
  `ParamOutput<int>`. The direct switch entry, seventeen ordered reads and
  setters, four typed parameter contexts, and one ledger-joined source
  span establish the stored layout. The reached outputs hold separate
  `$33@_attacker`, `$33@_entity`, and `$33@_knotIndex` paths; no event or
  output value is observed. Its selected validator is
  `scripts.game_data.levelscript_on_any_enemy_poise_knot_break_native`.
- `SetAudioCueVar.Execute`: build-independent claims contract
  `levelscript_audio_cue_execute_claims.json` (validator
  `levelscript_audio_cue_execute_native`) proves ordered call sites only.

## LevelScript route-specific conclusions

- A path/ID-sourced Param's constant slot is a placeholder: often
  `BoolCompare`'s first operand, and every reached `EventArgsAssignFloat`
  `EventArgsPtr`.
- `PlayFmvAction.beforeMask` is `Param<bool>`; names never decide wire types.
  `SendLuaEvent1` reads a seven-member inner value, bypassing its setter.
- Widths vary (`AudioBlackScreenBehaviour` enums byte-backed, most Int32);
  action `Param<GameplayTag>` is a raw int32; short `LevelScriptPtr` IDs
  frame exactly like long ones.

## BuffData

The 30-member root readers (`memorypack/buff.py`, `buff_actions.py`,
`buff_residual_actions.py`, `buff_icon_config.py`, and the top-level
`buff_frontiers_native.py`) give every file a named outer frame, but `memorypack/buff_named_schema.py`
keeps nested action, positive `stackEffects` and timeline bodies opaque. A
whole schema needs a forward receipt from byte 0 through all 30 fields, `id`
equal to the source stem and physical EOF: `buff_root_no_positive`
(empty-list, narrow blackboard/globalModifier, and positive-damage roots whose
conditions and processors each have a selected receipt) or
`buff_create_action_root_receipt` (a sole `CreateBuffAction`); JsonData
replays it. The isolated gradual positive-damage work leaves the canonical
exact set unchanged until the whole corpus gate runs again. The selected
gradual root now replays to physical EOF through a four-action condition:
CheckDamageDecorateMask, SaveBuffStackNumAdvanced, ModifyDynamicBlackboard,
and SimpleCalcBBAction, followed by the selected damage-scale processor.
The two new action readers authenticate their member order and typed nested
contexts; the selected finder, target and BlackboardDouble children tile
their original source spans. The targeted audit joins the prior complete
BuffData report's native receipts to freshly validated gradual native inputs
on the same build and rereads only that source. This proves stored structure,
not live buff or damage behavior. Child receipts name direct members only; strings, flags
and value bits stay raw. Tag meanings are local to the Buff dispatcher.
The current complete BuffData report also carries a selected positive-damage
root with two `CheckTwoDirectionAngle` conditions and ordered damage processor
tags `[5, 6]`. Its reviewed condition, nested target, processor, root,
source-ID and EOF receipts compose to all 30 named fields in that one source.
The remaining sword positive-damage root has a different eight-action
condition and remains partial; neither closed root proves live damage behavior.
For that one sword source, the selected condition now has source-bound receipts
for its first CheckDamageTypeMask and FindTarget actions and the following
CheckEntityNum action. The first two compose the existing mask reader with the
already validated Buff FindTarget formatter/dispatcher audit, rather than
borrowing native authority from the SkillData timeline parser. The
CheckEntityNum receipt independently matches the audited formatter and its
TargetSettings generic context to the current generated direct-member plan;
the original source closes both the action and its `checkTarget` child at their
selected endpoints. Its stored `targetGroupKey` and `storeKey` are file values,
not observed target or damage behavior. The TargetSettings direction and
selector interiors remain structural here. The next IfElse action also closes
on this source: independently native-gated CompareFloat and
ModifyDynamicBlackboard children rejoin the selected eight-member IfElse
wrapper, whose fail sequence stores zero actions. The nested scalar, target
and blackboard interiors retain their structural tier; no branch decision was
observed. The two later top-level ModifyDynamicBlackboard actions also close
under the existing native reader. A selected storage receipt now tiles all six
top-level actions and both terminal bytes through the condition endpoint.
Its status is deliberately nonrecursive: the structural nested interiors
prevent whole-condition schema and whole-BuffData promotion even though the
stored condition span is exact. The reviewed gates and source selection are in
`buff_damage_sword_condition_prefix_native.json` and
`buff_damage_check_entity_num_child_native.json` and
`buff_damage_sword_if_else_child_native.json` and
`buff_damage_sword_condition_storage_native.json`; their readers consume only
the selected logical bytes and existing validated native contracts or audit rows.
The claymore upgrade buff has a separate positive `healModifier` field. A
source-hash-checked selected replay joins the current root field-13 frame to
the native-audited `CheckHealTag` route, including four inherited action
members, its `query` setter and the two named `GameplayTagQuery` children.
The same selected native build proves the parent heal modifier's three direct
members and the tag-zero processor's `modifier` and `modifyTargetSide` reads.
The nested attribute modifier has four direct members; its `param` reuses the
native-gated BlackboardDouble child reader. The selected composition now
replays all 30 root fields in order, checks the stored `id` against the source
stem and reaches physical EOF. This is a one-source diagnostic: the canonical
BuffData exact set remains unchanged until a combined corpus gate. Stored
bits do not establish live heal behavior or provider selection. The reviewed
selection and source windows are in `buff_heal_check_tag_selected_native.json`
and `buff_heal_processor_zero_native.json`; the readers are
`memorypack/buff_heal_check_tag_selected.py`,
`memorypack/buff_heal_processor_zero.py` and the selected root branch of
`memorypack/buff_root_no_positive.py`.

Another selected partial, `buff_common_break_passing_small_scene_object`, has
one `buffEventAction` map containing one SequenceActionData and one tag-`0x21`
BreakPassingSmallSceneObject action. The existing residual frontier proves the
four inherited action members; the reviewed root-sixth and Sequence contracts
fix the map's action-array-before-event order and its two terminal booleans.
The source-bound receipt in `buff_break_passing_selected_native.json` and
`memorypack/buff_break_passing_selected.py` replays field five to its exact
endpoint, then the selected root branch consumes all 30 named fields at
physical EOF. This remains a local diagnostic pending the combined corpus
gate. Stored event and priority bits do not prove runtime execution.

The selected `buff_equipsuit_defup_01` source adds a different positive
`damageModifier` boundary: an empty SequenceActionData condition and one
tag-ten ModifyCalcResult processor with two native-gated BlackboardDouble
children. Its root also contains a positive `attributeModifier` before that
field. The cached blocker list names only the damage child, so a root replay
must still prove the earlier attribute child. The selected contract
`buff_empty_condition_tag_ten_selected_native.json` reuses reviewed root
prefix and attribute-item source windows, generated setters and stores to
name its one AttributeModifier element and converted-attribute terminal.
Both child spans compose with the 30-field root reader and original source ID
at physical EOF. The selected receipt remains outside canonical corpus
publication; raw enum/scalar values do not establish modifier arithmetic.

## SkillData

SkillData is one 48-member object: field 0 `ActionGroupData`, fields 1-42
read by a sequential reader derived from the generated wrapper types, and a
five-member terminal (fields 43-47). A gated immediate-registration site joins
the Core `ReadValue<T>` key to `GenericMemoryPackFormatter`. That is static
adapter identity, not executed registration or active dispatch
(`scripts/game_data/il2cpp/context_audit_skilldata.py`). Promotion climbs from
exact action to exact timeline record, whole ActionGroup, then whole file
(fields 1-42 plus the selected terminal at physical EOF). A lower rung never
counts as a higher one.

Per-tag layouts live in code, one reader per route:
`scripts/game_data/memorypack/skill_timeline_*.py` for actions,
`skill_selector_*.py` for nested selectors (their own switch tables), and
`skill_timeline_shared_sequence.py`, whose composite contract also admits
routes reused from reviewed Buff readers. Each route's contract pins the
dispatcher, reader body, source calls and generic contexts. Readers check
every reached union tag and member-count byte. Nested children
(`skill_selector_postprocessor_convert_to_slot`, `skill_selector_zero_member`
-- where `FF` is not a zero header -- `skill_damage_unit_gameplay_tag_list`,
`skill_timeline_two_*`) are admitted only where reached. All of it is stored
framing only. Gate: `python -m scripts.game_data.memorypack.skill_corpus`.

**Static limit.** Rows with no content-bound prior receipt (files added by the
newer VFS overlay) have two terminal framings that both parse exactly to EOF.
The native field-43 bool and field-44 `GameplayTagList` header favor the
earlier one only conditionally on the ordinary formatter/provider route, and
static evidence cannot observe provider choice or the executed cursor. The
subset rebind carries a prior live selection only to logically identical rows,
so new rows stayed `ambiguous` until the live target-set capture. The capture
is gated by `il2cpp.skill_cursor_native_context` and
`il2cpp.skill_cursor_target_set_context`, verified by
`skill_cursor_capture_target_set` and promoted by
`skill_cursor_target_set_overlay`. Those docstrings own the provenance chain,
the rebuild order after a reader change, and the capture procedure.

Historical export-backed censuses do not establish current VFS coverage;
`memorypack.skill_corpus` starts from the authenticated ledger and stream
bytes, and a unique EOF candidate is unique only within its grammar.

## SkillData live cursor evidence

The live SkillData capture (session `20260928T005315Z`) is complete and
loss-free. The strict target-set verifier confirms every requested target
plus the positive control, so that set needs no further capture. Every
witnessed source reads the earlier one-member terminal: field 43
`switchToCenterBeforeCast` through field 47 `useAIExclusiveFrame` at EOF. The
full sweep promoted every formerly ambiguous target-set source to whole-schema
exact. A live cursor selects stored cursor positions for one exact source:
terminal candidate, field vector and ActionGroup child checkpoints
(`skill_cursor_receipt`). It does not name a populated ActionGroup interior,
choose a provider, show a gameplay branch, or give any action semantics.
Purrche's parent `IfElseAction` puts the base combo ability-range source in
the fail branch of `potential_3 >= 1`. The below-Potential-3 branch was
unavailable on the user's save: its stored source and native logic are
recovered, but its execution is unobserved.

The later AnimeStudio audit changed `inputSetSha256` while the installed
native build remained the captured one. A sparse current VFS stream over the
reviewed target set rechecked each logical source's path, length, SHA-256 and
copied bytes. `skill_cursor_capture_target_set --rebind-current-corpus`
replayed the unchanged loss-free receipt against those current rows, the
current native reader bodies and callsites, and the static whole-file joins:
every unresolved target and the positive control closed again. The observer
contract grew a recorder length declaration after capture; the rebind retains
its historical fingerprint and requires the historical field and child
callsite vectors to equal the native-validated vectors. This was a current
**target-set** result at that parser revision, not a full-family census. The
sparse report remains partial and cannot establish the status of unstreamed
files; its strict parser fingerprint now predates the DiceFloat addition.

A separate sparse check of the three earlier family cursor samples also
rebound their unchanged raw receipt and source-corpus rows to current source
bytes and native code. All three remain whole-schema exact: the farming-end
sample uses a reviewed timeline shared-sequence profile; the Potential-test
and mimic passive samples use empty ActionGroup profiles. Its large
`missingOld` counter is the expected count of historical rows outside that
three-file selection, not evidence that those sources disappeared. Neither
sparse check fills a populated ActionGroup child interior or establishes
runtime branch execution. A whole-current-family claim still needs a
separate complete corpus gate when publication requires it.

The historical Mifu nested-finder stop was already addressed by the selected
SnapPointFinder reader (`skill_selector_finder_snap_point`), whose two stored
children are a `BlackboardDouble` radius and `TargetSettings`; it does not
show live target choice. A current sparse recheck streamed only the three
formerly stopped Mifu sources and composed them in memory with the already
authenticated family cursor samples. The control report predates a change
inside the downstream target-set rebind verifier; `skill_sparse_corpus_compose`
requires the exact old source bytes and proves by AST that no parser function
changed before reusing those controls. Mifu power attack and ultimate now
close as whole stored SkillData records. The combo skill advances beyond the
finder but stays a verified prefix plus terminal at an uncontracted current
action route `0x004B`. This is a three-source diagnostic, not an updated
whole-family count.

That later route is the selected `CheckSkillHasHit` action. Its independent
native contract (`skill_timeline_check_skill_has_hit_native.json`) pins the
dispatcher wrapper, reader body, member-count check and four ordered source
calls: `isEnable`, `priorityLevel`, `priorityOffset`, then
`serverActionIndex`. The isolated decoder rejoins the exact current combo
bytes at the previous stop and closes this stored action. A one-source
diagnostic replay with that route admitted then closes the full timeline list
and ActionGroup; the existing top-level reader reaches field 42 exactly at
the family receipt's selected terminal start. This supports whole stored-file
closure for the combo **as a focused diagnostic**. The shared corpus parser
has not yet incorporated the route, so the published family census and its
parser provenance remain unchanged. Stored `CheckSkillHasHit` values do not
prove a live hit, server action, or branch execution; no new capture is needed
for this framing join.

The next sparse check took only the two previously stopped Lbshamman
SkillData sources. Their current VFS rows and copied source bytes agree, and
the selected `DiceFloat` reader resolves the action route, seven ordered
members, byte-payload key, and two `BlackboardDouble` generic children.
`skill_timeline_dice_float` validates the complete reader and child evidence
before consuming either source at its prior first stop. The shared parser
now admits this route through the same selected native check and reviewed
composite contract. A current two-source VFS replay has no later timeline or
passive first stop and closes both ActionGroups; its unselected terminal
remains ambiguous by design. `skill_sparse_corpus_compose` reuses the three
authenticated family cursor controls after proving the shared source changed
only by this exact route addition, the reviewed contract gained only that
route and dependency, the new native validation passed, and no control
reaches `DiceFloat`. It reselects the terminals without re-streaming controls
and closes both stored files **in a nonpublishable two-source diagnostic**.
The earlier 27-target report predates this parser edit and is not claimed to
pass a strict current-parser fingerprint gate. No unchanged target was
re-streamed. The stored key and scalar children do not show a live dice roll
or branch execution, and no new capture is needed for this framing join.

The next selected check streamed only two previously stopped Agtrinit
SkillData sources. Their physical `FA FA 00` action is `MoveToSlotAction`
`0x00FA`, not a one-byte `0xFA` route. The reviewed
`skill_timeline_move_to_slot_native.json` contract pins its dispatcher,
17-member reader, every ordered source call, and the LayerMask,
TargetSettings and AnimationCurve generic contexts. The finite child readers
and source bytes close this stored action from the former offset 1137 to
1264 in both files. After admission to the shared parser, a current VFS
replay of only those two paths passes the composite native gate and moves
both first stops to a later action `0x00E5` (at distinct offsets). Neither
whole ActionGroup nor terminal is established yet; no unchanged cursor
control or 27-target source was re-streamed. The selected motion fields do
not prove live target choice or movement. This is a bounded sparse result,
not an updated whole-family census, and this route needs no new capture.

The exposed `0x00E5` route is `LogAction`: the selected native reader pins ten
ordered calls, including two bounded string payloads. Both Agtrinit sources
close that stored action and then their complete timeline lists and
ActionGroups under the shared parser. A new current VFS stream checked only
these two changed paths, with zero timeline or passive first stops. The
strict sparse composer authenticates the old control source bytes against
the saved report, strips exactly the three reviewed route additions
(`DiceFloat`, `MoveToSlotAction`, `LogAction`) from the current shared parser
and contract to recover the old bytes, checks that no captured control reached
them, and compares every other parser, source, tool and native provenance
entry before replaying the unchanged family cursor receipt. Both Agtrinit
files then close as **whole stored SkillData records** in a nonpublishable
two-source diagnostic. No unchanged control or 27-target source was
re-streamed. Stored log fields do not show that logging executed; the
complete-family census still predates these parser additions.

The next distinct historical stop was a later `IgniteAction` `0x00CE` in
the two Endmin ultimate SkillData sources. That action was already admitted
by the shared contract through the reviewed `buff_ce_native.json` source;
no parser route was changed for this batch. A selected current VFS stream of
only those two files confirms zero timeline or passive stops and exact whole
ActionGroups. The same strict three-route additive proof reuses the three
captured controls and the unchanged cursor receipt, promoting both stored
files to whole-schema exact **within a nonpublishable two-source
diagnostic**. This says nothing about whether `IgniteAction` executed or
what the two ultimate skills did at runtime, and it is not a current
complete-family census.

Another bounded check grouped four distinct historical unknown paths that
the current parser already covers: common battle-step left/right reach the
reviewed nested finder tag 6, and the two Lbshield skill-four variants reach
the reviewed `0x0054` action. Only those four paths were streamed from the
current VFS. All four now close complete timeline lists and ActionGroups;
the unchanged saved cursor controls select the exact terminal through the
same strict additive-source proof, yielding four whole-schema exact stored
files in a nonpublishable four-source diagnostic. No route code or native
contract changed for this check; it does not prove battle-step target choice,
shield action execution, or a complete-family count.

Two other historical stops reached `HurtAnimAction` `0x00C8` in Azrila's
extra attack and Seraph's projectile-hit SkillData. The composite contract
previously listed a derived route, but the shared reader still refused the
action. The reviewed `skill_timeline_hurt_anim_native.json` now pins the
selected dispatcher, ten ordered reads, member-count check, and final
TargetSettings generic context; a finite target reader closes both stored
actions. After the shared parser promotes that exact route, a selected VFS
stream of only these two paths closes their timeline lists and ActionGroups
with no later first stop. The sparse composer proves the three earlier route
additions plus this one exact derived-to-reviewed promotion, checks the
captured controls never reach any changed route, and reuses the unchanged
cursor receipt. Both files close whole-schema exact in a nonpublishable
two-source diagnostic. Stored hurt-animation fields and target bytes do not
show a live animation, target choice or branch execution; no capture is
needed for this framing join.

The two Wulfa combo SkillData sources were another later historical stop at
`TriggerComboSkillAction` `0x0187`. That route was already admitted through
the reviewed Buff native contract, so the shared parser needed no change.
Only those two previously unknown VFS paths were streamed against the current
audit; neither has a timeline or passive first stop. The same authenticated
three-control composition proves both complete stored records whole-schema
exact in a nonpublishable two-source diagnostic. This closes stored framing,
not the combo's runtime trigger or a current complete-family count.

The next distinct historical stop reached `SaveBuffStackNumByTag` `0x0137`
in Ikut's ultimate ability entity and Lastrite's combo SkillData. The selected
native dispatcher joins its wrapper to an eight-member reader: one bool,
four scalar words, TargetSettings, a bounded key payload, then a finite
GameplayTagQuery. The reviewed route pins all eight ordered source calls and
both nested generic types. The shared parser now admits only that selected
member count and physical extended tag. A current VFS stream checked only
these two newly unknown paths and found no later timeline or passive stop.
Strict composition with the three unchanged captured controls proves both
whole stored records exact within a nonpublishable two-source diagnostic; it
also proves the exact fifth route addition leaves the controls untouched.
The key, tag query and stack-type fields do not prove a live stack value or
action execution. The complete-family census still predates these additions.

The two Zhuangfy ultimate-attack files had historically stopped at nested
selector-validator tag 6. The current shared parser already admits that
reviewed zero-member HittableObject validator. A new current VFS stream of
only those two previously unknown files has no later first stop, and the
unchanged three-control composition closes both whole stored SkillData
records in a nonpublishable diagnostic. This identifies stored validator
framing, not the runtime hit-test result. No parser code changed for this
check and no unchanged source was re-streamed.

Antal's combo and Pograni's normal skill had historically stopped at
`FractureAction` `0x00BE`. Its fifteen stored reads and seven nested contexts
were already reviewed in the selected Buff frontier9 native contract. The
SkillData reader now reuses that contract under explicit selected native
inputs and admits only the matching route and member count. A current VFS
stream of those two newly unknown files has no later timeline or passive
stop. The six-route sparse proof confirms the parser's only new behavior is
this reviewed admission and that the unchanged controls never reach it;
both stored files close whole-schema exact in a nonpublishable two-source
diagnostic. Stored motion, time and target fields do not prove a live fracture
or selected target, and the complete-family report has not been rebuilt.

Five separate historical passive first stops in the doodad passive,
Pograni talent-one, Zhuangfy talent-two, Camille passive talent-one and
weapon-funnel sources are already admitted by the current reviewed passive
routes. One bounded VFS stream authenticated only those five previously
unknown files. All five now close the passive action map and the whole stored
SkillData record under the reused three-control receipt, in a nonpublishable
five-source diagnostic. No route code changed for this batch. The stored
passive maps do not establish that any event fired or condition passed.

Azrila's combo-defend file had stopped at `ShowComboSkillUI` `0x015F`. Its
four-member direct native read was already reviewed in the Buff residual
frontier; the new SkillData reader authenticates that frontier against the
explicit selected binaries and checks the same derived wrapper plan. A
current VFS stream of this one newly unknown path has no later stop, and the
seven-route sparse proof preserves the unchanged controls while selecting
whole-schema exact stored framing in a nonpublishable one-source diagnostic.
The stored action does not show that the combo UI appeared at runtime.

Wulfa's ultimate skill had a separate historical stop at
`TryToTeleportSquadAction` `0x018C`. The selected dispatcher, four-member
native reader and generated wrapper plan agree on `isEnable`, `priorityLevel`,
`priorityOffset` and `serverActionIndex` in that order. The reviewed SkillData
reader admits only the physical extended tag and exact member count. A VFS
stream of this one newly unknown path authenticates the source against the
current audit; its local bytes match that row and the selected reader closes
the stored action span exactly. The eight-route sparse proof reuses the three
unchanged captured controls without re-streaming them. The same source then
stops at a later `0x0012` timeline action, so this is a **structural prefix**
in a nonpublishable one-source diagnostic, not a whole-schema closure. The
stored teleport fields do not establish a runtime teleport; the next action
is a separate native framing route to resolve offline.

That next Wulfa action is `AnimEventReceiver` `0x0012`. The selected native
dispatcher and seven-member source reader place the inherited bool and three
scalar fields before `SequenceActionData` and two bounded string payloads.
The generic source cell selects the same SequenceActionData reader whose
member-three list and two terminal bytes are independently reviewed. Its
positive nested list and both following payloads close as one exact stored
action on the previously authenticated Wulfa bytes. The shared parser now
admits only that selected route and member count. A strict ninth-route source
diff proof, current VFS provenance recheck, and reuse of the three captured
controls support a **nonpublishable same-source replay** without streaming any
unchanged file. Parsing advances to a later `0x008B` timeline action. The
Wulfa file remains a structural prefix; stored event keys and nested actions
do not prove that an animation event fired. The later route can be investigated
from this selected source without a new runtime capture.

The later `0x008B` action is `ContinuousSetAnimTimeScale`. Its selected native
dispatch, five-member reader, formatter and generic source calls agree on the
inherited bool and three scalar fields followed by a `BlackboardDouble`
`timeScale`. The reviewed reader admits only that tag, exact count and nested
payload shape. Replaying the already authenticated Wulfa source and three
unchanged controls against an exact ten-route additive parser proof closes
this action, the whole timeline ActionGroup and SkillData fields through 42.
Field 42 ends exactly at the earlier EOF-anchored terminal candidate. This is
a **nonpublishable same-source diagnostic**: both terminal framings remain
statically possible, and none of the saved live cursor receipts covers Wulfa.
Only a source-bound executed cursor can select its fields 43-47 for a
whole-schema claim. The stored time-scale value does not establish a live
animation effect.

The dedicated Wulfa capture preflight reuses that saved one-source VFS row and
the three unchanged controls. Its exact additive parser attestation, current
VFS/source gate and selected native observer produce a partial, source-bound
context. The recorder admits the larger Wulfa copy by exact hash while its
older target-set limit stays fixed. The non-launching host preflight passed,
then a live session yielded one loss-free exact-source cursor. The strict
single-target verifier closed the executed terminal at EOF, selecting the
earlier one-member-wrapper framing. That cursor report alone still calls the
ActionGroup interior opaque; `skill_cursor_wulfa_terminal` joins all its field
and child checkpoints to the independently exact current static fields 0-42.
The reviewed `skill_cursor_wulfa_terminal_selection.json` records the selected
terminal vector and receipt provenance. The joined **one-source diagnostic**
closes Wulfa's whole stored SkillData schema; it does not publish a current
family census, establish formatter/provider execution, or show the ultimate
or animation effect in play. `tools/EndfieldCapture/README.md` retains the
source-bound capture procedure for this selected build.

Seraph's ultimate is a separate historical SkillData first stop at
`DispelAction` `0x009F`. One newly unknown source was streamed under the current
VFS audit; its exact copied bytes match the local export. The reviewed
SkillData action reader reuses the selected Buff reader's nine-member native
order, code windows, nested contexts and generated wrapper plan. In a
source-only diagnostic, that action and the populated timeline ActionGroup
close, and static fields through 42 reach a terminal whose two field-43..47
framings still both reach EOF. The shared SkillData parser has not admitted
this route, so this is neither a current family census nor a whole-schema
publication. Stored target and query profiles do not prove which target was
dispelled, or that a dispel occurred in play.

The Seraph cursor preflight bound only that source with the existing v3
target-set transport and reused the already authenticated three-control
report. Its exact source, VFS and selected-native gates passed, as did the
non-launching capture-host preflight. A live session then yielded one
loss-free copied-source cursor. The source-only receipt selected the earlier
one-member-wrapper terminal and reached EOF, while its report alone still
left the populated ActionGroup interior opaque. The reviewed
`skill_cursor_seraph_terminal_selection.json` and
`skill_cursor_seraph_terminal` replay that receipt and join its two child
checkpoints and all direct field cursors to the independently exact current
static DispelAction, timeline and fields 0-42. This **one-source diagnostic**
closes Seraph's whole stored SkillData schema, without publishing a current
family census or establishing that a dispel or ultimate effect occurred in
play.

For a later set of unresolved sources, `skill_cursor_scoped_group` prepares
one reviewed v3 binding from only the newly selected paths in a current
partial VFS report. It requires exact local copied bytes, unique source
hashes, the recorder's target-count and byte caps, and the selected native
cursor observer. No historical control is included or streamed for this
transport check; previously authenticated controls remain available to
source-specific static proofs. The strict receipt verifier requires every
selected source to be observed with an exact EOF cursor and no global or
per-target losses. Even a complete group establishes only executed top-level
field and child cursors. Each populated ActionGroup interior and route still
needs its own native-gated static join before any whole-schema claim, and the
normal full corpus gate remains the publication boundary.

The first reviewed scoped group now selects **four previously unresolved
Zhuangfy sources**: normal skill, its ultimate-mode variant, perfect dodge,
and ultimate skill. One VFS run streamed exactly these four paths under the
current full audit; every row remained partial and its logical length/SHA
matched the local copied source. Their first timeline stops are `0x0038` in
both normal-skill variants, `0x0049` in perfect dodge, and `0x002E` in the
ultimate. The selected native dispatcher identifies these as
`CheckAbilityEntityCurDuration`, `CheckPerfectDodgeDirection`, and
`ChangeSpecificLayerAction`, respectively, but supplies no payload cursors:
the five-member perfect-dodge route is a short offline reader candidate,
while the other two contain nested objects and need focused native/source
decoding. None needs a live gameplay value to establish its stored action
layout. All four still have two EOF-valid top-level terminal framings, so a
live cursor is the remaining way to select those terminal fields without
guessing. The reviewed
`skill_cursor_capture_zhuangfy_group_target.json` pins their exact source
identities and the native observer; the prepared four-source v3 binding and
non-launching host preflight passed. A **single capture session can cover the
set if all four source hashes execute**; the filenames suggest ordinary
skill, ultimate-mode skill, perfect dodge, and ultimate triggers, but that
gameplay mapping is a trigger plan rather than source proof. The strict group
verifier fails if any target is missing. The subsequent one-session receipt
passed that strict verifier: **four of four** exact copied-source and EOF
cursors, with no missing target or loss. In every source the executed field
cursor selects the earlier one-member-wrapper terminal. This is a
**cursor-only four-source diagnostic**: its ActionGroup interior remains
opaque until each earlier action route is joined to selected native and
source bytes. It neither publishes a current family census nor proves that
an ability comparison, dodge, layer change, or skill effect occurred in play.
No prior control or closed source was streamed again.

The two normal-skill sources share a reached `CheckAbilityEntityCurDuration`
action at `0x0038`. The selected native dispatcher, nine ordered source
reads, generated setters and generic contexts prove the wire order: four
inherited action fields, TargetSettings, a bounded key string, CompareType,
a bool and BlackboardDouble. Both immediately reach
`SetAbilityEntityDuration` `0x0146`; its independent selected native reader
proves ten ordered reads, including two enums, a bool, a bounded key,
TargetSettings and BlackboardDouble. Both routes reuse native-gated child
profiles and close their stored action spans in these two copied sources.
Stored operands show neither a live duration/comparison result nor a target
selection.

The source-bound `skill_cursor_zhuangfy_group_join` authenticates the saved
four-source terminal result and replays only the two reached action routes.
The ordinary normal skill later stops at unreviewed `0x0197`; it remains a
partial ActionGroup despite its selected EOF terminal. The ultimate-mode
normal skill has no later action stop: its timeline ActionGroup cursor agrees
with the executed child cursor, static fields 0-42 agree with the direct
field vector, and the selected one-member-wrapper terminal reaches EOF. Thus
**one whole stored SkillData file closes** in a nonpublishable selected-source
diagnostic. The perfect-dodge and ultimate sources still have their earlier
first stops in that earlier join. `skill_cursor_zhuangfy_terminal_selection.json` pins the
receipt, verification and selected terminal vectors. At this diagnostic
stage, the shared parser and complete-family census were untouched.

The ordinary normal skill's later `VoiceInterruptAction` `0x0197` is now
isolated by its own selected-native six-member reader: the four inherited
fields, a 32-bit interrupt time and a one-byte immediate-interrupt flag.
Its exact stored action span is pinned in the reviewed ordinary-source
selection contract. The focused `skill_cursor_zhuangfy_normal_skill_join` reads
**only that source**, reuses the frozen four-source receipt and current VFS
provenance, and rechecks the three reached native routes. The complete
ActionGroup ends at the executed child cursor; static fields 0-42 match the
captured field vector and the selected terminal reaches EOF. Thus a
**second whole stored SkillData file closes** under this one-source,
nonpublishable diagnostic. The older group join still records the earlier
two-route boundary; no unchanged source or control was streamed again.
Neither a voice interruption nor its runtime timing is inferred from the
stored operands.

Perfect dodge's `CheckPerfectDodgeDirection` `0x0049` has five native-proven
fixed-width members: four inherited fields and a direction enum32. The
source-only join validates every reached `0x0049` span, then closes its
ActionGroup and static fields 0-42 against the saved executed child cursor
and selected EOF terminal. This is a **third whole stored SkillData source**
under a nonpublishable diagnostic. The direction operand does not establish
that a perfect dodge happened in play.

Ultimate's `ChangeSpecificLayerAction` `0x002E` has seven native-proven
members. Its two LayerMask fields use a shared helper that checks and
advances four source bytes each; the last member uses the established
TargetSettings profile. The focused ultimate-source join validates every
reached action and also matches a complete ActionGroup, static fields 0-42,
and the selected live EOF terminal. This closes the **fourth grouped stored
SkillData source** only under the selected diagnostic. It does not prove an
executed layer transition or chosen entity. The frozen group receipt is now
joined to exact stored structure for all selected sources without another
capture or VFS stream. These source-bound joins were nonpublishable pending
shared parser admission and a current corpus gate.

The shared SkillData timeline parser now admits `0x0038`, `0x0146`,
`0x0197`, `0x0049` and `0x002E` through separate source-contract shape
checks and the selected-build native validators. A bounded replay of the
four formerly partial Zhuangfy sources closes each ActionGroup under the
shared reader, matching the already authenticated selected-source joins.
The route additions also advance Lizhiyan's previously partial combo skill
past its `0x0146` stop: its entire timeline ActionGroup now closes, and the
exact continuation through field 42 ends at the earlier of its two EOF-valid
terminal candidates. The later counted candidate starts after the exact
field boundary and cannot be this record's terminal. This is a selected
stored-source conclusion; the old full corpus report has prior parser
provenance, so it is not a current family publication. No historical
control or unrelated exact source was replayed.

A current VFS gate then streamed **only the still partial Lizhiyan combo
source**. Its installed logical bytes match the copied source and the saved
historical identity; the new shared parser has no timeline or passive stop,
closes field 0, and ends field 42 exactly at the earlier terminal candidate.
The second EOF-valid candidate begins a byte after that proven boundary.
The resulting one-file report remains `partial`, `publicationEligible=false`
and `wholeSchemaExact=false`: it is a source-scoped static terminal
discrimination, not an executed Lizhiyan terminal cursor or a family-wide
selection. The frozen Zhuangfy group basis still authenticates its original
four-source capture, but its prior parser fingerprint makes the old join
commands fail the current provenance gate after shared admission. Their
saved reports remain historical diagnostics. A later publication pass must
either prove an exact current-parser rebind of unchanged corpus rows or run
the normal current family gate; neither has been inferred from these five
bounded replays.

The existing complete family report stores parsed rows and logical hashes,
not the decrypted source bytes, and its parser and reviewed contract
fingerprints predate these route additions. A frozen-row rebind would need an
immutable authenticated basis, a proof that the parser delta only adds the
named routes, a reachability check for every reused row, and focused replays
where a newly admitted route was reached. That proves conclusions over the
frozen input set. It does not by itself prove the unchanged installed VFS
chunks still contain those bytes: the current-family publication contract
also checks live source fingerprints, chunk selection, and selected chunk
hashes. Without equivalent immutable-source evidence, skipping all unchanged
source checks leaves the family publication gate unsatisfied; the bounded
source reports remain nonpublishable.

The historical Pograni ultimate first refusal at `0x0152` now has a
source-scoped selected-native reader. The current dispatcher identifies
`SetIgnoreGlobalTimeScaleAction`; its generated seven-member wrapper, ordered
source calls, setter sequence and generic contexts prove two stored flags
followed by `TargetSettings` after the inherited action fields. The selected
export copy matches the historical logical hashes, and that first action's
finite target child closes at the next stored action. This remains a
nonpublishable selected-source span: the reader alone does not check the
current VFS chunk or establish runtime time-scale behavior. The later
timeline and terminal are evaluated separately below.

A focused composition of that native-gated route with the current shared
SkillData reader advances the same Pograni copy through its remaining timeline
records without another source stream. Its ActionGroup and fields 0-42 close
at the earlier EOF-valid terminal candidate; the later candidate begins one
byte beyond the proven field boundary. No later unknown action tag is reached
in this source. The earlier anonymous terminal shape reaches physical EOF, so
the stored bytes close structurally. This is a static selected-source terminal
discrimination, not an executed cursor naming fields 43-47 or a current family
publication; the report remains nonpublishable and whole-schema exact status
is not promoted.

A bounded current VFS gate streamed only that still unknown Pograni ultimate
source. Its installed logical length and SHA-256 match the selected copied
bytes. The family reader continues to report its first `0x0152` stop, since
the selected native route is intentionally separate from the shared parser.
The selected structural EOF result can therefore be rebound to the current
logical source, but no live terminal cursor or current family publication is
inferred. No already checked SkillData source was restreamed.

The Lizhiyan combo and Pograni ultimate sources are now bound in one reviewed
cursor target-set contract. Its v2 preparation accepts their separate
single-source VFS reports, verifies matching input-set and copied-source
identities, and pins both reports in the native-gated context. This avoids
re-streaming or rehashing the already checked Lizhiyan chunk merely to make a
combined capture basis. The non-launching host preflight passes. Only a later
loss-free runtime receipt can select the terminal cursors for both sources;
the contract and preflight alone do not make either whole-schema exact.

## Resolving the native formatter

Each step is `direct` static evidence, never the live formatter, cache, cursor
or EOF; `il2cpp.context_audit` checks it, and each report `boundary` says what.

1. Registration is a pointer array of 16-byte records; `GetFormatter<T>`'s
   parameter belongs to `ReadValue<T>` (`il2cpp.context`).
2. The MVAR leaf ordinal indexes the method-inst vector; modules join by
   unique image name; usage cells resolve via the lazy MethodSpec resolver.
3. The cache is seeded from the registration and compares only the tag plus
   one flag bit. RGCTX slots are not module entries. Never put shared
   object/object arguments into the companion's class context.
4. Setter order is the wire order: generated setters, inherited first, never
   `fields_for` (`memorypack.wrapper_members`).
5. `memorypack.action_dispatcher` walks every AbilityActionData tag;
   `memorypack.union_subtypes` orders nested unions (`structuralOnly`).
6. A body is tag, member-count header, members. The opt-in `derived_*`
   modules fail closed; a plan-only tag is self-consistent, not proven.

## Wire rules every reader relies on

Owners: `memorypack.derived_schema`, `memorypack.wrapper_members`,
`il2cpp.context_audit_memorypack`.

- `List<T>` elements carry a header or `FF`; unmanaged `T[]` is packed raw.
- A struct is its aligned size; a union base is abstract without `Deserialize`.
- Maps are a count plus pairs, padded only when both sides are unmanaged.
- The wrapper reader takes one header byte; `ListFormatter` compares its
  signed count with the remaining bytes, unscaled.
- The `FF` peek consumes one byte; other elements convert through
  `IMemoryPackDeSerializeWrapper<T0>`, so output width is not consumption.
- The provider takes a companion, not the reader; its caches are stateful.
- Cursor state is never an EOF test; no caller compares consumption.
- The formatter-check carrier's last 16 bytes are opaque.

## Recovery acceleration

- `native_union_atlas` checks every union contract in one native context
  with family-qualified tags; publication still needs full corpus gates.
- A Skill replay cache keyed by `dependency_snapshot` reproduces warm and miss
  rows faster, but it is a prototype: changed bytes need a fresh stream, and
  admitting a route can change old bounded rows.

## Eliminated readings

Each line is a reading that was tested and refused; the owning module's
docstring keeps the refuting test.

**JsonData families and tables**

- `SerializeFieldDictionary` header as map count; `MapMarkTempTable` key
  always equal to `markInfoId`; marker group key as scene or level.
- UID-shaped bytes or an audio-map scan as extents; TriggerZone owning a
  later audio-key map; one tag number reused across union families.
- Buff: one-byte `FF` as `0x00FF`; anonymous first `globalModifier` member;
  compact-stacking EOF as ownership; shifted `tagsAfterTriggerExtendBuffAction`.
- Quest state `1`; `0x04B1` as `StopLevelSeqLoopSegment`; `AirWallPtr` as
  `EntityPtr`; `StartLevelCustomPerformance` bool as always present.
- `posList` as three floats; `preWarnEffectFixedRotation` as four floats;
  AnimationConfig offset 62 as `montages`; bulk `FKeyframe` in wrapper order;
  `npcMontages` tags as 64-bit; MontageNew 20-byte vectors; `renderNodes`
  count equal to `nodeCount`; a corpus enum subset for component keys.

**LevelScript unions**

- Byte-7 action-map framing (first list count only); a terminal template ID
  making earlier bytes exact; a child layout guessed from member count or
  position; an outer `WaitForCondition` licensing a nested-condition parse;
  merging dispatcher domains on identical scalar layouts.
- All-EOF `0x00DC`/`0x0065` projections: a scratch counter bug.

**SkillData**

- A one-byte-later terminal (refused by the native field-43 bool and every
  live cursor); EOF validity or another source's witness as a terminal
  selector; promotion by derived-plan EOF, a same-tag layout, or a tag only
  the Buff reader admits.
- A diagnostic integer as a physical tag without a failed union-tag check;
  `FA FF 00` (`0x00FF`) as null; `BoneAttachAction` `0x0000` as a sentinel;
  `CheckSuperArmor` tail anomalies as offset errors (later bytes select other
  routes).
- SkillAIMove `markerInfo` as a wrapper call (it is an eight-byte unmanaged
  copy); `TeleportPosSelectAction` as an alias of `TeleportAction`; Buff's
  compact selector-tag or handwritten tag/member-count tables applied to Skill.
- A PlayAnimation prefix outranking a complete shared-sequence profile; broad
  catches that dropped later refusals; per-build RVAs or method indexes in
  Python as identity; file bytes for virtual-only PE globals.

**Formatter identity and wire framing**

- Identity: the `GetFormatter<T>` counterexample (a probe indirection bug);
  `table + i*16` as a record address; byte equality with `System.Object`
  selecting a shared body; all switch-table pins as one union; reviewed rows
  joined by tag across unions instead of by type name.
- Types: declaration order as wire order; nested-union tags in ordinal order;
  a subclass making a type a union; a memberless wrapper as unresolvable; an
  enum's base as `System.ValueType` or every enum as four bytes; a struct as
  the sum of its member widths; a four-byte output slot as a serialized width.
- Framing: one framing for list and array elements; a counted map with a
  managed side as unreadable; a short `ForceSyncAnimData` header (cursor
  drift); a depth limit of 24 or an empty (falsy) `PlanRegistry` as a
  schema signal; the reference census counting more than nested `skillId`;
  `MissionRuntimeAsset` payloads as MemoryPack (they are JSON).

## Remaining gaps

The ordered queue across families is in
[`../game_data_recovery.md`](../game_data_recovery.md); these are the open
items this topic owns.

- **LevelScript.** The gate rerun, first-stop leaders and route integration
  order are item 1 of the queue;
  [`levelscript_first_stop_census.py`](../../scripts/game_data/levelscript_first_stop_census.py)
  reruns the owner over the JsonData receipt's partial files and ranks first
  stops by whole files. Unsupported values: positive
  `PosRot`/`GameplayTag`/`BuffPtr`
  list elements, non-null `CameraControllerBase` and target-script values,
  non-constant patrol `EntityPtr`, positive dynamic AI blackboards, camera
  poses and curve keys; `SendLuaEvent2` is unobserved; partial templates stop
  at unreviewed unions.
- **BuffData.** The remaining sword root, other positive
  `attributeModifier` and `healModifier` processor interiors;
  timeline, `stackEffects` and
  `buffEventAction` interiors; string parity.
- **SkillData.** The bounded-partial residue stops at mostly distinct action
  tags with one or two files each; the Agtrinit `0x00FA` and `0x00E5` routes
  now close their two sources under a sparse diagnostic. Open grammars:
  FindTarget nested tags `0x02`/`0x03`, the
  85-member `EffectActionCfg` body, DamageAction variants and `DamageUnit`
  member 33, CameraImpulse's nested actions. No cursor receipt names a
  populated ActionGroup interior; a terminal proof cannot fill an earlier
  child.
- **Formatter and runtime.** Registration history and the outer
  provider/cache path are unjoined; provider selection, live formatter/cache
  contents and substitution are unobserved; the DamageUnit tag-list and
  `CheckSkillType` list providers stay conditional. Nested-union tags stay
  `structuralOnly` until their tables are walked, and each plan-only tag needs
  a whole-corpus adoption run. `Dictionary<string, object>` has no plan.
- **Tooling.** Dependency-scoped Skill replay needs a route registry and
  mutation tests before it leaves prototype. CharInteractPerform's
  `FAnimationCurve` now shares AnimationConfig's proven bulk-key reader; no
  current custom curve has positive keys to exercise it in that family.

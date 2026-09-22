# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and level
payloads. The first section is where each family's framing stands; the rest is the
IL2CPP evidence chain that identifies *which* formatter a payload resolves to --
static identity throughout, never observed execution.

## Framing status, by serialized family

The block-wide `scripts.game_data.jsondata_corpus` gate gives every current
JsonData file a terminal registry state after an exact VFS-ledger-to-structured-
export length/MD5 join. It separates valid UTF-8 JSON, exact named schemas,
anonymous exact frames, named prefixes with opaque remainders, and ambiguous
partial frames. The current authenticated sweep has no unsupported or
unclassified identity. That means every file has a structural evidence lane;
it does not mean every field is named. Family gates remain the deeper proof for
formatter, cursor, native-input, and semantic claims.

`Beyond.SerializeFieldDictionary<K,V>` and its `Paired`/`Sorted` siblings are
not framed like `Dictionary<K,V>`. Each has a registered `MemoryPackFormatter`,
so the generated member list does not describe the wire: the formatter writes
the ordinary one-member object header -- a one-byte `0xff` null marker, or a
member count of one -- and only then the same counted map a `Dictionary<K,V>`
member writes. Reading that header as the map's own count consumes four bytes
where one belongs and desynchronises the rest of the file, which is how the
defect hid: most such members are empty, so the misread often still landed on a
plausible boundary. The reviewed CharInteractPerform reader always read the
correct shape and reaches EOF on every current owner; the derived declared-root
codec in `codecs/levelscript/action_map.py` did not, and now does. The
correction raised named coverage in four families at once -- LevelData and
LevelScriptData most -- with no family losing a byte. Counts live in
`reports/game_data/jsondata_schema_coverage_declared.json`. Treat any other
type with its own registered formatter the same way: derive its wire form from
the formatter, never from the field list.

Current exact named readers additionally cover LevelConfig,
AtmosphericNpcData tables, NavMesh area/state containers,
TeleportValidation tables, DialogIdTable including its two added row members,
AetherEnergyLockConfigDataTable, MatrixShockWaveBeatConfigTable, the compact
MissionAreaTable, WorldChallenge SubGame table, compact WorldEntityRegistry,
BambooRaftTaskTable, and InteractiveTable. The registry's persisted root has
four dictionaries; the script lists in the larger textual table are derived
postprocessing and are not serialized members.

The two NPC JSON catalogs are exact as well: `PrefabInfo/manifest.json` is a
case-insensitively unique `npc_*.json` filename list, while MontageJson's
`hashMapPath.Json` is a nonnegative hash-to-nonempty-path array. The latter
contains repeated identical rows, but every repeated hash retains the same
path; a conflicting collision fails closed. Both validate their root and row
keys exactly.

`NonGeneratedConfigs/GoldCoinConfigTable.json` is an exact named JSON schema:
its assembly/type identity, source-keyed rows, pickup and lifetime scalars,
raycast vector, legacy sine-arc settings, and physical-bounce motion settings
are all validated in stored order. Duplicate source enum values and shape or
type drift fail closed.

The 22 current `UILevelMapLoadConfig` JSON files are also exact named schemas.
The level-list row closes its string array; each level row validates the map
rectangle and movement settings, all supported static-element variants and
their condition phases, tier-name dictionary, three LOD chunk dictionaries,
and the grid, mist, and tier information dictionaries. Dictionary identities
must match each value's stored ID, vectors and scalar types are checked, and
unknown fields or condition variants fail closed.

All 37 textual JSON files under `GameplayConfig` now have exact named schemas;
the six binary tables keep their existing MemoryPack readers. Compact tables
validate their explicit roots, rows, vectors, curves, type identities and
cross-index relations. This includes inverse map/short-ID dictionaries, all
three atmospheric-NPC indexes, 1,956 NPC proxy placements, model paths and
interactive lock-view metadata, 18,030 world-entity briefs, focus modes,
mission areas, map regions and LevelScript teleport rows. The five broad
polymorphic tables (`ForbidByGameplayTagTable`, `GameModeTable`, `LevelMapMark`,
`ScriptTaskExtraInfoTable` and `SubGameInstanceDataTable`) use a byte-pinned
declarative contract covering 813 schema nodes and 88 stored `$type`
identities. Only their explicitly named
authored-ID dictionaries are dynamic; unknown fields, shapes, scalar types or
discriminators fail closed. This establishes stored configuration structure,
while runtime selection and render consumption remain separate evidence.

The remaining ten textual JsonData rows also have named schemas rather than a
generic JSON classification. A byte-pinned 473-node contract closes the AI
global settings and enemy-template paths, the root-level NPC-proxy and script-
task tables, interactive collection counts, doodad groups, factory regions and
spaceship cabin spawn data. The two LevelMountPoint files use a recursive
reader for named branches, position/rotation mounts and typed cabin-teleport
extras; each currently contains 61 nodes and 47 mounts. These tables directly
support reconstruction placement, navigation, attachment and idle-behavior
work, but do not by themselves prove which runtime object consumes a row.

The three 16-member GPU UI configurations are
`ExtendedPrefabGroupSerializeData`.
`decode_gpu_ui_root16` now closes all root fields and nested ExtendedPrefab,
ExtendedAnimation, NodeMetadata, ExtendedNode and Subroot records with a real
sequential cursor to EOF. Generated wrapper order plus the original field types
name animation timing, affected-node indices, render-node offsets, node text and
autosizing, UV/animation sampling values, material/fill parameters, subroot anchors,
and both texture hashes. The root distinction between `layoutType`,
`prefabBufferSize` and the following `prefabs` count is explicit. This is an exact
stored schema, not proof of shader consumption or a resolved texture-hash join.
The bounded prefix reader remains a fallback for unsupported nested layouts.
DamageText's six-field `PrefabGroupSerializeData` now also closes by a real
sequential cursor through every nested record and the root tail. Its reviewed
[`gpu_ui_damage_text_native.json`](../../scripts/game_data/contracts/gpu_ui_damage_text_native.json)
contract pins current native inputs, generated reader order, original field
types and offsets, and the selected reader windows. It names the six-member
prefabs, five-member animations, twelve-member node metadata, and distinct
ten-member `NodeSerializeData` bodies, including contiguous animation vectors,
unsigned material parameters, and UVs. The final texture references are signed
64-bit `StringPathHash.hash` values with the text-ID list between them.
`renderNodes` can contain more entries than `nodeCount`; those stored counts
must not be equated. The native-gated exact reader fails closed on drift;
the older row-boundary scanner remains only a structural fallback.
`scripts.game_data.gpu_ui_corpus` authenticates every GPUI export against the
current VFS ledger and requires each named reader to reach EOF. Stored render
configuration does not establish runtime prefab selection, GPU buffer
addressing, animation evaluation, shader consumption or texture identity.

Populated AtmosphericNpcData tables decode every dictionary entry through the
next key or physical EOF. Their 118-member values flatten `LevelEntityData`,
`LevelNpcData`, and `NpcRuntimeProxyData`; the maintained reader shares the
same exact 14 + 77 + 27 member codec as LevelData and names the complete row.
Strict strings, booleans, finite transforms, nested member counts and supported
polymorphic routes all advance a real cursor through the bounded value. An
unsupported positive nested variant remains fail-closed at exact framing or a
named entity prefix rather than being promoted to a complete schema.

LevelData's factory fields now use the current generated wrappers instead of
stopping at their positive list counts. `factoryMines` is a seven-member
`LevelFactoryRegionMineInstanceData` list with typed density levels, item and
prototype IDs, logic ID, height/offset and a three-member grid transform.
`factoryRegions` is the 26-member derived wrapper: the inherited 14-member
`LevelEntityData` prefix precedes twelve region members in generated setter
order. Its maintained codec also owns the nested area/level/bound, buildable
range/mask, bus, belt/path, initial-building, mine and settlement wrappers.
Current positive region rows exercise typed areas and buses; the other nested
collections are empty, while top-level mine rows exercise the complete mine
and transform shape. Unsupported member counts, malformed booleans/non-finite
floats, and non-null repair-item instance data fail closed. Files that formerly
stopped at these factory members now hand off exactly to later `guideHints` or
`predefinedParams` records, with the fully empty remainder closing at EOF.

InteractiveTemplateData carries a 26-member root marker throughout the current
`Interactive/InteractiveData` family. Current generated setter order places
`relatedGuideTimestampGameVar` between `propertyKeyToIdMap` and
`saveProperties`. The exact supported-`dataMap`, empty-`templateVariant` lane now
consumes every field after `configProperties` through physical EOF, including
populated `NameMountPointDef` arrays, the paired property-ID dictionaries,
guide-timestamp strings, and typed `ParamKeyValue` save/temporary lists. This
closes the base tail shared by current templates. The same reader now consumes
the populated `SerializeFieldDictionary<string, InteractiveTemplateVariant>`:
all 389 current values use the generated 14-member order, including typed
optional scalars/references, component property diffs, model/tag/mount-point
overrides, and global/map property diffs. This closes 92 more files, bringing
the family to 220 of 312 exact. The two-field
`Core_InteractiveModelLevelUpComponentData` wrapper then closes its inherited
typed property map and derived model-level string list in all five current
owners. The current two-field `Core_NarrativeComponentData` wrapper likewise
closes its inherited typed property map and derived `NarrativeObjType` enum in
all four owners. Three of those owners have no later unsupported field, bringing
the family to 228 of 312 exact; the fourth retains a separate positive action
map. The remaining current component/config exceptions are now closed as well.
`ParamValueType` 29 carries the same string tail as the other string-backed
property types; this advances the language-key lists in template config and in
both lifter components without treating their UTF-8 bytes as later object
markers. Selected-build dispatcher joins identify tags `0x00ab`, `0x00ac`,
`0x010c`, and `0x00d2` as `LifterCore`, `LifterForBoxGameCore`,
`GameplayLockedReward`, and `Rotator` wrappers. Their current one-member bodies
are exact typed property maps. The five-member `CharacterMovementComponentData`
wrapper closes its inherited property map, current null ability-movement list,
five-float `MovementData`, bounded `MoveMode`, and two-float proxy shape at the
next component union. A present `ActionSerializedMap` with three zero list
counts now advances through the same typed suffix to physical EOF, preserving
the distinction from a null map. Positive maps now use the shared sequential
`codecs/levelscript/action_map.py` reader. Its byte-pinned
`action_map_layouts.json` records selected native dispatcher/type-usage joins
and generated inherited field order. Supported maps include control-flow
checks/branches, effects/audio, typed assignments, interaction options, simple
getters, and entity-event headers. The NodeBase prefix retains every field,
including arbitrary nullable UTF-8 UIDs; union tags may use plain or wide
encoding. ActionBase adds `nextID`; PureGetter and PureGetter<T> add no fields
after NodeBase. Generic Set<T> adds key/value parameters, while concrete getter
inheritance must be resolved before counting its fields. Signed/unsigned and
floating values retain their original unpacked values without display rounding.
String-key structs, integer/string lists, typed parameters and output references
retain null/value/source/path distinctions. Numeric list parameters also close
their declared Int32, binary32 or Vector3 elements, preserving null and empty
collections separately. Factory-state getters and event headers use independent
authenticated union families. Camera-controller parameters currently accept
only a null constant plus the ordinary binding tail; non-null camera objects
remain unsupported. The shared Param tail also accepts
the proven getter-reference form: bounded nonnegative `idRef`, source -1 and
null path; other negative-source shapes remain closed. Entity-list parameters
currently accept only null or empty values. Unknown unions/member counts and
unsupported positive lists stop at the real cursor. This proves stored layout,
not runtime action execution; UID-scanned audio observations cannot establish
map extents. Remaining owners need further concrete actions, getters or headers
after their now-decoded prefixes. Counts, hashes, actual remaining blocker tags
and the authenticated isolated before/after comparison belong to
`reports/game_data/interactive_action_map_isolated_current.json`; the broader
initial inventory remains `interactive_action_frontier_current.json` beside it.

The reconstruction-relevant Interactive residual now also closes the current
camera-control and forge time-dilation lane. Selected native dispatcher/type
joins and generated setters bind ActionBase tags `0x0C`, `0x392`, and `0x4DA`
to `AddCameraControlState`, `RemoveCameraControlState`, and
`TimeDilationToTarget`; header tag `0xD8` binds the derived
`OnForgeIronCameraShake` wrapper. Their maintained readers consume the exact
camera-curve, style, duration, output, nullable camera-state, raw GameplayTag,
entity-pointer and header-output fields at the real sequential cursors. This
promotes `data_int_accelerate_buff.json` and `data_int_forge_iron.json` to
whole-file named schemas. The remaining current stops are explicit action
unions: `StartDialogAction` (`0x4B0`), `SetEnablePlayerAction` (`0x3FF`),
`Play3DRadioAndWait` (`0x355`), `NpcPlayMontage` (`0x32C`),
`BlackScreenFadeInAndOut` (`0x20`), `RaiseCustomScriptEvent` (`0x38C`), and
`BlendToCameraTransform` (`0x26`). Each stays bounded at its union cursor until
all nested members and the later action/getter/header lists rejoin the typed
template tail at EOF.

The selected native BaseComponentData dispatcher is the authority for current
component union identities. Its generated registration joins observed union
tags through the branch's unresolved tag-1 usage cell and the current
MetadataRegistration type table, correcting stale aliases in the earlier
reader. Newly reached factory-battle, physics-audio, movement, spaceship,
butterfly, special-sight and related wrappers use the same authenticated join.
One-member component bodies
advance only when one complete typed property map reaches an exact next-union
or template-field handoff. Dynamic AI navigation additionally closes its
bounded `ObstacleType` enum after that map.

The current three-field Attack, Click, Scan, StepOn and TriggerZone wrappers
advance inherited `propertyList` (currently null), a `propertyStateData` list,
and `triggerBehaviourBase`. TriggerZone adds no serialized fields to
BaseTrigger; its body ends immediately after that behavior object. A following
audio-key map therefore belongs to a later field or component, not TriggerZone.
The stale signature/audio-map scan has been removed from structural parsing
and Audio ownership recovery; unanchored typed maps retain unresolved ownership. Generated wrapper order names all 20 property-state
members and all nine nested `BaseConditionData` members. Current generic-type
registration proves the condition, table-condition, server-condition and event
list identities. The current populated four-member behavior bodies now close
nullable `TableFieldCondition` and `ServerPropertyCondition` lists, the property
key, and bounded `EAffectTriggerBehaviourType`; the condition wrappers share
the generated expression/condition-list/trigger-type prefix, with table rows
adding `fieldName`. Unknown nested member counts and future positive shapes
still fail closed. These component joins expose more of a template without
promoting runtime behavior.

The current `Core_AbilitySystemForIntData` wrapper has 38 serialized members.
Its native reader consumes the 34 inherited `AbilitySystemData` members first,
in generated setter order, then `battleShapeData`, `propertyList`,
`skillBlackboardDataPairs`, and `useSelfBlackboard`. The maintained reader
closes every current occurrence through an exact next-union or template-field
handoff. It names the fixed inherited scalars and wrapper objects, the complete
`SkillDataBundle` string-list/ID shape used here, the 83-byte 16-member battle
collider, and the shared typed `ParamKeyValue` property map. Current buff-input,
effect, mode, combo-condition and auxiliary dictionary fields are null or empty;
their positive bodies remain fail-closed rather than inheriting a schema from
their names.

SkillData historical export-backed censuses cannot establish current VFS
coverage by accepting a newer boundary report. Its maintained
`memorypack.skill_corpus` gate starts from the authenticated outer ledger and
current decrypted VFS stream bytes, checks the complete identity set and
source/overlay/tool provenance at both ends, and records logical hashes.
The anonymous terminal reader enumerates direct-counted and wrapped branches
independently, including empty wrappers; unknown record member counts fail
closed. A unique EOF candidate is unique only within the supported grammar,
not a proven preceding cursor. Full record ranges, ambiguous candidates and
opaque gaps remain distinct from whole-file ownership. Current coverage and
full candidate inventories belong to
`reports/animestudio/skilldata_current_latest.json` and its Markdown companion;
the historical two-ambiguity census is superseded, not a current baseline.
BuffData's current provenance-matched census covers the complete ledger family.
The generated current wrapper names the 30 root fields. The event reader advances
`abilityEventAction` from byte zero, and supported continuations name
`addingCooldown`, `applyTags`, `attributeModifier`, `blackboard`, and
`buffEventAction`. A second sequential reader consumes `damageModifier` and
`healModifier` lists through the generated three-field item wrappers. It closes
damage processor union routes 0, 2, 3, 4, 5, 6, 9 and 10 and both heal processor routes
present in the current corpus; every other damage route stops at its union tag. Current
native dispatch binds route 5 to `DamageScaleProcessorForMemoryPack`; its exact
three-member reader consumes `addition`, `side`, and `zoneName`. Route 6 binds
to `DamageTextProcessorForMemoryPack`; its exact two-member reader consumes a
bounded `DamageTextStyle` scalar and the `useHpChangeAsDisplayValue` boolean.
Route 10 binds to `ModifyCalcResultForMemoryPack`; its generated and native
three-member order is `baseMultiplier`, `modifyType`, `multiplierCnt`, with
the two multiplier fields using the bounded BlackboardDouble profile around a
raw enum-like scalar. Routes 2, 3 and 4 bind respectively to
`AttackerCriticalDamageProcessorForMemoryPack`,
`AttackerPenProcessorForMemoryPack`, and
`DamageIndependentHealthProcessorForMemoryPack`; each generated one-member
wrapper and selected native reader consumes one bounded BlackboardDouble
`scale` or `multiplier`. The stored names and order do not establish these processors' runtime
arithmetic or presentation behavior. The selected Buff action dispatcher binds
tag `0x130` to the fieldless `ReturnFalseAction` generated wrapper. Its current
four-member base-action body has the exact reader order byte, scalar32,
scalar32, scalar32. The authenticated supplemental codec uses that route only
inside the two reached damage-modifier condition sequences, then rejoins the
existing named middle reader; it does not transfer the numeric tag or a layout
from another action domain. The same current dispatcher binds tags `0xEE` and
`0xEF` to the seven-member `ModifyPartsDamageRatio` and
`ModifyPartsPoiseRatio` wrappers. Both read the inherited byte/three-scalar
prefix, one bounded BlackboardDouble profile, one bounded GameplayTagQuery and
a terminal byte; the two wrappers reverse the order of the nested profiles in
accord with their generated setters and selected readers. Their supplemental
root-action routes close all four current weak-part BuffData owners without
sharing a tag interpretation with another action domain. Tag `0xF5` similarly
joins the seven-member `MoveTickAction` wrapper. After the inherited prefix its
selected reader consumes bounded TargetSettings, SequenceActionData and
BlackboardDouble profiles in generated setter order, closing both current
distance-travelled BuffData owners while retaining fail-closed recursion for
unknown child actions. The root reader also
consumes positive `globalModifier` lists through the generated four-field item order:
`applyToReturnAtbGain`, `formulaItem`, `param`, and `type`. It consumes the root
reader's raw-eight-byte `dispelConfig`, then advances `duration`, the three
booleans, and the `hasIcon` flag. It retains `iconConfig` as one named opaque
range only when the current native contract is unavailable. On the authenticated
build, the generated 19-member `BuffIconConfigForMemoryPack` wrapper and selected
reader close that range exactly at the independently accepted `id` marker. The
order-priority value is a direct twelve-byte native-value read containing a
boolean, three preserved padding bytes, a signed priority value, and an enum-like
DWORD; the remaining members are the sprite path, three enum-like DWORDs, and
fourteen booleans in generated setter order. The authenticated Buff corpus
replays this cursor for every reached icon record. When that cursor joins the
unique suffix reader, fields `id` through `waitFirstTriggerInterval` close at EOF
and the block registry promotes the file to named exact framing. The same
current Buff action dispatcher now authenticates tag `0x10A` as the 16-member
`PassiveJumpAction.Data` wrapper and tag `0x6C` as the reached
`CheckPartTagMatch` wrapper. Their selected readers consume inherited action
members and generated wrapper fields in exact order. The first route closes the
current `teammate_jump` owner at physical EOF; the second advances
`player_jump` to its final unsupported tag `0x29` without claiming that tail.
These tag meanings remain local to the reviewed Buff dispatcher and do not
transfer to other action domains. The current dispatcher further binds tag
`0x29` to the nine-member `ChangeMoveGaitMultiplier`, tag `0x46` to the
seven-member `CheckMoveSpeed`, and tag `0xD0` to the four-member
`IgnoreModelIntervalCheck`. The first stores three
`SerializeFieldDictionary<GroundedMoveGait, float>` values; each reached
non-null dictionary has a one-member header, a signed count, and fixed
enum/float pairs. `CheckMoveSpeed` adds a direct compare scalar,
`BlackboardDouble`, and `TargetSettings` after the inherited action prefix.
These exact routes close the reached `player_jump`, `common_speedup`, and
ultimate-listener owners, but do not assign gameplay meaning to enum values or
movement behavior. Three additional authenticated base-only routes are
`BreakPassingSmallSceneObject` (`0x21`), `OnPhysicalNoGuardStart` (`0x100`),
and `ShowComboSkillUI` (`0x15F`). Each wrapper serializes exactly the four
inherited action members in byte, scalar32, scalar32, scalar32 order. Their
input-gated dispatcher, wrapper, method-pointer, and reader-window contract
lets the reached cursors rejoin the established named middle, exact icon
configuration, and suffix readers. It establishes stored wrapper identity and
cursor advance, not runtime behavior.
Seven further current-build routes are authenticated: base-only
`DisableRootMotion`; `ChangePushBackDistanceFactor` with `BlackboardDouble`;
`LockMainCharacterToggle` and `TyphoeaArcheryBrainToggleRegister` with direct
booleans; `ReplaceAnimationShake` with a string; and
`IntRollingStoneRepatriateAction` and `PausePoiseRecover` with
`TargetSettings`. Admission requires both exact native and input-set contracts.
Every reached route rejoins the independently accepted named middle through
the exact icon configuration. A `TargetSettings` body may close nested actions,
so action-record gains can exceed newly closed root files. These layouts prove
stored member order and cursor advance, not runtime action behavior.
The current dispatcher also authenticates eight six-member wrappers whose two
derived fields are, respectively, `BlackboardDouble`/`TargetSettings`,
`BuffInput`/enum32, string/int32, int64/`TargetSettings`, string/string,
enum32/string, string/`TargetSettings`, or `TargetSettings`/string. These are
`ObtainUspInNormalSkill`, `OverrideJumpAction`,
`OverrideStateAnimationWithMontage`, `SetAllowedDamageDecoMask`,
`ShowTyphoeaHudHint`, `StoreAtbValue`, `StoreCurSkillExecuteFrame`, and
`UpdateGlobalContextTarget`. Union tag `0x00FF` is admitted only in extended
`FA FF 00` encoding; one-byte `FF` remains the null-union sentinel. Gated corpus
replay proves the reached routes rejoin the independently exact icon
configuration and named suffix through EOF, without asserting runtime behavior.
Residual Buff framing now has another separately authenticated contract for
twelve reached wrappers. Pinned dispatch, registered wrapper identity,
deserialize bodies, setter signatures, generated fields, and nested generic
contexts establish exact member counts and source order. The reader preserves
short versus extended union width, null union versus null wrapper, and
independent nested null states. Two routes are base-only four-member records;
the rest reuse independently bounded string-list, paired/scalar, sequence,
target, and buff-finder profiles. Every affected current file rejoins the named
middle and terminal suffix. Runtime behavior and field-value meaning remain
outside this structural boundary.
The final root-action frontier authenticates every previously unsupported root
plus the downstream `0x00E9` and `0x017E` routes reached by the floating-mode
record. Each route joins the Buff sequence dispatcher, generated wrapper,
selected reader and exact cursor back to the independently named icon
configuration and terminal suffix. Root continuation is therefore complete for
the current corpus. The last damage-modifier stop used the already authenticated
Buff condition route `CheckTwoDirectionAngle`; the frontier-nine reader could
consume it, but the named-middle retry had admitted only an older residual
contract. The retry now requires every residual contract to match the selected
input set and accepts only union tags declared by one of them. The affected file
therefore rejoins the processor list, exact icon configuration and terminal
suffix, and every current BuffData file has a named outer frame. A numeric tag
match against the LevelScript `ActionBase` layout remains insufficient because
union families can assign different member counts to the same number.
Unsupported nested bodies stay opaque even in a closed outer frame; icon
presentation behavior and UI ownership do not follow from the recovered
serialization field names.

The Buff named-schema receipt composes the independently proved prefix, middle,
icon and suffix ranges before measuring what remains. It subtracts downstream
coverage once, preserves opaque nested action bodies, and counts positive
`stackingSettings.stackEffects` explicitly instead of treating a closed outer
cursor as a fully named record. Anonymous Blackboard member ownership, the
raw-eight-byte `dispelConfig`, and legacy stacking, tag, timeline-branch and
fallback interiors remain separate naming obligations. Consequently, a file
with zero unconsumed composed bytes is still not a whole named schema unless
those interiors have direct ownership evidence; no current BuffData file meets
that stronger boundary.

LevelData now has one sequential 43-field reader. It closes null and empty
collections, the current empty `LevelFactoryPredefineData` and
`LevelFunctionAreaData` wrappers, and the complete member-22
`Dictionary<ulong, LevelScriptBriefData>` with its eight named value fields.
Every LevelData payload in the authenticated current corpus now reaches exact
EOF through this reader; future wrapper, union, or member-count drift still
fails closed at the first changed field.
The function-area lane also advances exact 13-member base rows and two-vector
`ThreeDimRange` records, including nullable list elements. The generated base
row's `posList` is a `List<Vector2>`; consuming three floats per point can look
plausible across several records but eventually shifts the cursor into the
following condition count, so the maintained reader fixes each point at two
finite floats. The two polymorphic nested collections now close every current
shape. `ConditionData` reads `conditionRuntimeBase` before `uniqueId` and
supports the current combined, mission-not-paused, mission-state and
quest-state condition routes. The shared condition codec also closes the
three-member `SimpleConditionCheckGlobalVar` route reached by bamboo-raft dock
filters (`compareOperator`, `compareTarget`, `globalVarName`).
`FunctionAreaSpecificData` uses the authenticated
current native tag dispatcher; the observed records cover ambience and camera
control/volume/look-at settings, blight and bark flags, carry tags, dither
factory bounds, entity-hiding filters, radio triggers, repatriation, scene
toast keys, teammate-follow bounds, Story safe zones, and visit-location
statistics. The current tag-16 `VisitLocStatData` route is a one-member wrapper
containing the signed `saveId`. Each concrete value
uses its generated setter order and member count, including nested LangKey,
string/identity lists and finite Vector3 values. Unknown tags or changed member
counts stop at the nested union instead of shifting later LevelData fields.
The top-level `buildableCondition` field uses that same authenticated
`ConditionRuntimeBase` codec. Its 13 current positive values are four
mission-state and nine quest-state checks; each now closes before
`cameraPoses` instead of remaining an anonymous nullable-object body.
`dynamicOccludeAreas` then closes its generated three-field area and grid
wrappers plus the two-field integer line shape. All 16 reached positive lists
close at EOF, covering 53 conditioned areas, 68 grids and 3,379 lines. A
condition route outside the maintained union still fails closed.
LevelData's member-20 list now shares the exact 25-member
`LevelInteractiveData` codec with LevelScript's keyed dictionary: inherited
entity identity/pose fields, component property maps, authored property lists,
integer-key lists, flags and model scale advance one cursor. Current null
progress locks close, as do the proved mission-state, quest-state and recursive
combined-condition unions. The selected native dispatcher additionally binds
current tag `0x11` to the three-member `SimpleConditionCheckQuestState` wrapper;
any other positive condition tag still fails closed. `componentProperties` is
the generated `Dictionary<InteractiveComponentType, List<ParamKeyValue>>`:
its Int32 enum key does not dispatch a polymorphic payload. The reader retains
that raw integer, rejects duplicate keys, and always advances the complete
typed property list. A corpus-derived enum subset must not block this fixed
layout. Preserving an unfamiliar raw key makes no claim about runtime component
validity or ownership. Selected native inputs and the generated enum confirm
the observed keys; per-build inventories and the isolated coverage comparison
live in `reports/game_data/leveldata_interactive_frontier_current.json`.
LevelData's `spawners` member is a list of the generated six-member
`LevelSpawnerInstDataForMemoryPack` wrapper. Its exact stored order is
`belongLevelScriptId`, `configId`, `enableWaveDieEvent`, `position`, `rotation`
and `spawnerId`; the two poses are finite three-float vectors and both IDs are
unsigned 64-bit values. The maintained codec accepts nullable list elements,
rejects every other member count, and hands off at the exact following
`specificData` marker. Every positive list in the current corpus closes through
that handoff and the remaining empty tail.
The spatial lane decodes the generated four-field `LevelCameraPoseData` rows
(`cameraId`, FOV, position and rotation) and the current twelve-field
`LevelEnvironmentVolume` profile. Environment rows expose the environment-phase
asset path, blend/fade settings, transform, priority, volume identity/type and
authored polygon points. Their current polyline records have empty BVH and
convex-polygon caches and a null tree; a populated future cache fails closed.
The same lane decodes `LevelMapRegionData` through its nested map-shape polygons
and tier links, and `LevelSplineData` through Unity Splines' current
`BezierKnot` layout (position, in/out tangents, quaternion and width). These
records retain their owner transforms and IDs instead of flattening all points
into world space.
The current water-volume record also closes all 26 generated fields, including
OBB/pivot geometry, polygon points, mesh/Luna/navmesh identities, fill/flow
settings, localized name key and start/stop audio names.
The `riftVolumes` member declares that same `List<LevelWaterVolumeData>` type
and reuses the identical codec; all three reached positive rift lists now close
through the next field without inventing a second layout. Factory doodad groups
close their nine-field owner with center/outer identities, integer grid
position and the four progression lists; later dynamic-occlusion records remain
a separate polymorphic-condition boundary.
The top-level polymorphic `specificData` member now closes the current tag-zero
`SpaceShipSpecificData` route. Its generated eight-member order retains the
cabin-slot dictionary, grow-box identities, manufacturing-machine map,
showcase root/bind/local-pose lists, and spawn pose. `CabinSlotInfo` values use
their exact four-member order (`boundSize`, `logicId`, position, rotation), and
unknown union tags or changed member counts remain fail-closed.
The `levelWideConfigs` field is an exact nested dictionary from the raw
`LevelWideConfigType` integer to string-keyed polymorphic values. Current tag
zero selects the two-member `BambooRaftDockWideConfig`, whose dock rows retain
logic ID, localized name, nullable or typed condition, and node index; tag one
selects the three-member `BambooRaftWideConfig` with config key, raft logic ID
and moving-spline ID. Duplicate keys, unknown tags and changed member counts
fail closed.
LevelData's `npcs` member now consumes the complete inherited
`NpcRuntimeProxyData` wrapper sequentially. AtmosphericNpcData dictionaries
reuse this codec for the same flattened row shape. Current generated wrappers prove
the 118-member partition as 14 `LevelEntityData` members, 77 `LevelNpcData`
members and 27 `NpcRuntimeProxyData` members. It retains authored identity and
pose, animation and interaction tags,
battle/collider settings, localized overrides, patrol and environment-talk
configuration, runtime proxy identity, audio ID and optional AI/runtime data.
All 258 currently reached rows in 44 files advance through the following
LevelData members. Nested generated wrappers are admitted only with their exact
member counts, strict primitive types and current polymorphic routes; an
unknown positive runtime-extension body or changed wrapper stops in place.
Authored `LevelUIData` rows now close their argument strings, global identity,
position/rotation/scale and prefab path. Enemy groups also close their eight
generated members plus nested three-field slots and `EntityPtr` identities;
later enemy patrol, spawner or lock records remain owned by their own fields.
LevelData's preceding `enemies` member reuses the same exact 30-member
`LevelEnemyData` value codec as LevelScript's keyed enemy dictionary, but stores
the values directly in a list. It therefore retains entity identity and pose,
AI/born settings, buffs, patrol selection, recycling, idle-break and override
data without duplicating a second field order. Every currently reached positive
list advances exactly; 13 files close at EOF and the other owners expose their
later independent blocker. Null list elements are represented explicitly, and
positive AI-blackboard shapes or changed nested wrappers remain fail-closed.
The following `enemyPatrol` list closes its generated three-member owner
(`enemyPatrolLoopType`, `patrolId`, `points`), three-member point
(`actions`, `patrolGait`, `position`), and fixed 13-member action wrapper. The
action retains its end/type enums, animation and template strings, duration,
wait/rotation values, event/radio IDs, and repeat/root-motion flags. Current
coverage is 559 owners, 1,832 points, and 821 actions across 57 reached files;
21 files close at EOF and the others expose later independent fields. Null list
elements and null collections remain distinct, while changed member counts or
malformed scalars fail closed.
The earlier `charPatrol` list follows the parallel generated three-member
`CharacterPatrolData` owner and point wrappers. Its fixed 18-member action
retains blend/duration/timing values, animation, environment-talk, event,
radio/template IDs, montage GameplayTag, flags and bounded action enums. All 14
reached lists advance exactly, covering 47 owners, 152 points and 63 actions;
null elements remain distinct and changed wrappers fail closed.
The NPC placement lane closes the complete 34-member generated
`AttractPointInEditorData` wrapper: action/movement modes, GameplayTag IDs,
position and quaternion, waypoint and attract-point links, animation strings,
spaceship tags, timing, chair/point identities and initialization flags. These
are authored placement and behavior-selection values; they do not establish
which point a runtime NPC actually selects. Later NPC patrol records retain
their own independent boundaries. The terminal authored
`WayPointInEditorData` collection is also exact: its nine fields include pose,
identity, gate/POI flags, level, linked point IDs, and nested two-field lane
records (`laneDir`, `totalLane`). This closes files that end in waypoint graphs,
but still does not prove a runtime traversal.
NPC patrols now close the generated ten-field owner, three-field points and
positive `PatrolSubAction` lists. The action codec follows all 26 generated
members, including the four-field `Beyond.Blackboard.DataPair` order
(`isDynamic`, `key`, `valueDouble`, `valueStr`). Its polymorphic payload accepts
only the current null route, tag-0 three-field `PatrolSubActionEnvTalkData`, and
tag-1 one-field `PatrolSubPlayAudioData`; the latter stores `AudioId._id` as an
unsigned 32-bit value. Unknown tags, changed member counts and malformed nested
values fail closed. The authenticated current corpus exercises 949 actions,
27 populated blackboard pairs, 18 EnvTalk payloads and 34 PlayAudio payloads.
This eliminates every former `npcPatrol` stop: 66 files become exact named
schemas and ten advance to a later independent LevelData field.
The separate top-level `patrols` list reuses the authored patrol grammar also
present in Spawner routes. Its generated `PatrolData` wrapper has 39 stored
members, beginning with the action list and ending with `worldOffset`; each
`PatrolAction` has four members (`actionType`, position, subactions and
subpositions). Current positive LevelData lists close with the same strict
member markers and maintained `PatrolSubActionData` union routes.
LevelData's `interactiveLockData` member likewise reuses LevelScript's exact
two-field `InteractiveLockData` value codec without dictionary keys. Its nested
18-member lock values retain interactive/quest/submit identities, localized
panel and toast keys, presentation flags and bounded unlock type. All 86
currently reached positive lists advance exactly, covering 1,171 owners and
1,173 nested locks; seven files close as complete schemas, six gain an exact
outer frame around later opaque interactives, and the rest reach a later named
field. Unknown unlock enums and changed nested wrappers fail closed.
The ten-member `LevelDataGuideHintConfig` list also advances in generated order:
begin/end guide IDs, enable flag, source/target instance keys, hint ID, integer
grid segments, start face/point and bounded hint type. All 28 reached positive
lists close, covering 87 hint rows and 141 two-integer segments; each owner then
continues to its later lock, interactive or predefined-parameter blocker.
Files made entirely from those supported shapes close as full named schemas.
When the independently proved member-21 tail bounds a nonempty `interactives`
list, every record receives an exact opaque range and the 43-field owner closes
as a named outer frame rather than a full nested schema.
Other files stop at the first nonempty unsupported nested body and retain an
independently proved terminal frame: generated setter order names the recurring
long tail as members 21 through 43, from `levelIdNum` through
`worldWayPointData`, and the shorter form as members 36 through 43, from
`safeZone` through the same terminal collection.
SpawnerConfig has one sequential five-field owner reader plus a retained
fallback. The owner always starts with `configId` and the exact current
enemy-library prefix, including named 13-member rows and the nullable
born-behavior boundary. Its high-coverage route profile then closes generated
two-field `SpawnerRouteData` values, 39-field `PatrolData` values whose
action list contains exact four-member `PatrolAction` values, and the complete
six-field settings object. Patrol actions name their position and type, nested
positions, and current 26-member subactions. The latter retain every generated
field; their blackboard-pair lists are empty and polymorphic `subActionData` is
null throughout the current corpus, so a future positive body fails closed.
This proves the terminal `waveMap` cursor. From there the sequential wave/group
reader closes the generated 11- and 12-field values and all current action maps
through physical EOF. The current tag map covers pause, play-audio,
preview-route, raise-event, and spawn-monster, with each concrete wrapper read
in generated order. The authenticated corpus therefore closes all 608 current
SpawnerConfig files as exact named schemas. The older unique-tail fallback
remains for a changed future route profile; failure of both readers preserves
the exact enemy-library prefix as bounded partial evidence.
CharInteractPerform now closes the complete 27-member owner through physical
EOF for every current file. The byte-pinned
`char_interact_perform_native.json` contract records the exact 37-entry native
tag-to-wrapper dispatch; generated wrapper properties and whole-owner cursor
closure establish the read order of every concrete action shape present in the
current corpus. The reader also keeps `FAnimationCurve`'s wrapped key records
separate from Unity `AnimationCurve`'s wrap-mode/count/raw-28-byte-key layout.
The complete-frame result publishes every action's exact byte range, native
type name, phase placement, base fields, and actor index where present, while
retaining the richer recovered audio rows. This makes all 202 current files
complete named schemas rather than anonymous structural frames. A future
unobserved concrete tag or changed member count still fails closed before the
prefix fallback.
LevelScriptData now has a sequential complete-schema lane rooted at the exact
20-byte empty `ActionMapAssetRaw`. The current generated 27-member wrapper
names the following cursor as `activeShapeList`, three activation booleans,
`endType`, `enemies`, `exitBuffer`, `exitBufferOverride`, `interactiveLocks`,
`interactives`, `levelScriptType`, `lstTemplatePath`, `maxStage`, `modules`,
`npcs`, `parentLevelScriptId`, `properties`, `propertyIdToKeyMap`,
`refWorldEntityIdList`, both reset modes, and the final five members. Authored
shape values, signed enum values, finite floats, booleans and UTF-8 strings are
validated at their physical cursor. Null or empty complex collections advance;
a positive unsupported collection stops before its count and names the exact
field. When those owner collections and `taskMap` are null or empty, the same
cursor closes `scriptId`, `startShapeList`, `startType`, and the exact current
`triggerVolumes` codec at physical EOF, yielding a complete named schema.
Positive task maps also close when every declared `LevelScriptTaskData` entry
uses a supported exact condition-union codec and the following
`triggerVolumes` map ends at physical EOF. Unsupported task-condition bodies
still stop immediately after the named task count; later bytes are not scanned
or assigned to a guessed entry. The current authenticated `GameCondition`
formatter registration binds tag `0x0080` to the seven-member
`CheckQuestState`, `0x00a3` to the six-member `CheckTalkOptionFinish`, and
extended tag `0x0130` to the nine-member `InteractiveCheckInt`. Their generated
wrappers prove the concrete member orders: comparer/quest id/quest state,
dialog id/finish id, and comparer/value/entity/key/level respectively. Quest
state accepts the generated sparse enum values `0,2,3,4,5`; value `1` is not a
valid quest state and fails closed. The same authenticated registration and
generated setter order now close the remaining current task-condition frontier:
`CheckFactoryBlackBoxState` (`0x0037`), `CheckLevelScriptStageReachMax`
(`0x0054`), `CheckPRTSUnlocked` (`0x007f`), `CheckRepeatableTalkFinish`
(`0x0087`), `CheckScriptMonsterKilled` (`0x008e`),
`CheckSpaceshipRoomBuilt` (`0x009c`), `CombineCondition` (`0x00b7`),
`OnBuildingPanelOpen` (`0x00d6`), and `SystemPoiLevel` (`0x0137`). Nullable
`Param<T>` values, scalar/list payloads, sparse enums, nested pointers and raw
trailing booleans advance only their declared member order; an unknown tag,
member count, enum value, or malformed parameter still stops before promotion.
The final current task-map tags are also authenticated against the selected
dispatcher and decoded in generated property order: `CheckScanInteractive`
(`0x008b`, entity then level), `CheckTerminalReadingDone` (`0x00a7`, terminal
unique ID), and `Conditions.CheckCurrentDungeonBoth` (`0x00bc`, dungeon ID).
These close the current positive task-map frontier; an unseen tag or changed
member count still fails before the task entry is promoted.

The generated-order LevelScript lane also starts after a null `actionMap`.
The outer wrapper's first member is a nullable reference, and MemoryPack's
one-byte `0xff` null marker closes it exactly, so `activeShapeList` begins at
physical offset 2. The reader advances from that boundary through the same
owner collections, terminal task map, and `triggerVolumes` EOF gate; it does
not use the independently found terminal suffix. Current null-map exceptions
stop inside a positive Encounter module whose `introPart` has a non-empty
opera-segment list. Closing those records requires the generated opera-segment
wrapper member order or equivalent authenticated formatter IL.

Positive `ActionSerializedMap` now has one complete selected-build lane. The
authenticated `ActionBase` dispatcher identifies tag `0x0035` as `CallServer`,
and the generated wrapper closes its callback UID list, event-argument and
event-name parameters, and three booleans. For the dominant one-action route,
the following physical list counts prove an empty `getterList` and one
`headerList` row. The selected `ActionHeader` dispatcher identifies tag
`0x00bf` as `ScriptEvent_OnLeaderEnterTriggerVolume`; its generated inheritance
chain closes the seven `NodeBase` fields, seven common header fields, two
script-event fields, and the two slot-filter fields. An empty one-member
`ParamListForGraph` then closes `ActionMapAssetRaw`, and the existing sequential
owner reader can continue through physical EOF. The broader sequence lane below
adds supported actions, getters and headers without changing those member
boundaries. Non-null target-script values and positive parameter blackboards
remain unsupported. Scanning UID-shaped bytes is not an acceptable substitute
for sequential record extents.

That selected-build action cursor now also advances `StartDialogAction`
(`0x04b0`, seven concrete members), `Split` (`0x04a7`, one integer list),
`SwitchInt` (`0x04cf`, two integer lists, a default ID and integer parameter),
`PlayRadio` (`0x036e`, five parameters), and `IfElseAction` (`0x0109`, a
condition and two branch IDs). `CheckBoolIfTrue` (`0x0053`) is included because
it is the common terminal action after current dialog and radio records. Exact
map promotion requires every declared action, getter and header to use a
supported layout, followed by an empty `ParamListForGraph`. `SwitchInt` and
`IfElseAction` commonly carry positive `getterList` rows, which require their
own authenticated PureGetter layouts. `StartDialogAction.afterMask` and
`beforeMask` are both the same current `Param<CommonMaskBlendData>` wrapper:
the selected generated setter order places them consecutively after
`shouldWaitForFinish`, and the parameter wrapper reads `constValue`, `idRef`,
`paramSource`, then `path`. A non-null constant value uses the six generated
members `audioBlackScreenBehaviour`, `curve`, `fadeInDuration`,
`fadeOutDuration`, `maskType`, and `useCurve`. The sequential reader now reuses
that exact cursor for both fields, accepting null values, current null or empty
curves, finite durations, reviewed mask enums and exact parameter tails. On the
authenticated full-family sweep this closes additional whole files without
regressions; an unknown nested curve or parameter representation still stops at
the mask field. The following `overrideAfterMaskConfig` and
`overrideBeforeMaskConfig` are nullable `Param<bool>` members in current data;
the one-byte null representation and the already-proven present bool parameter
both advance explicitly before the next action or list boundary.

The next post-mask first-stop profile is led by ActionBase tag `0x03ff` in 88
files. The selected current dispatcher binds that tag and member count 11 to
`SetEnablePlayerAction`; its generated wrapper adds `actionMask`, `advanced`,
and `enablePlayerInput` after `ActionBase`. The maintained codec reads those as
`Param<InputActionType>`, `Param<bool>`, and `Param<bool>` in that order. All 88
reached records close the exact three-field cursor across the observed signed
mask values, advancing 382 actions and completing 37 action lists. The
authenticated 5,030-file LevelScript comparison promotes one whole file from
bounded partial to named exact, keeps 2,945 bounded partial and 2,084 prior
exact files unchanged, and has no regression. Parameter markers, bool values,
and tails remain strict, so a changed field encoding stops at its named field.

The next reviewed action-map extension binds wide tag `0x030c`, member count
10, to `ManualEndLevelScript`. The selected dispatcher/type-usage join and the
generated wrapper agree that its two concrete fields are `levelId` as
`Param<string>` followed by `scriptId` as `Param<LevelScriptPtr>`. The shared
action-map codec now owns the exact pointer representation: a 16-byte value
with a zero reserved half followed by the ordinary parameter binding tail.
Every currently reached `ManualEndLevelScript` record advances to the next
declared action, getter, or header boundary without changing any previously
accepted file. Most of this cohort next stops at an independently unsupported
action-header union, so this recovery improves the exact cursor but does not
promote a whole file by itself. Unknown member counts, nonzero pointer-reserved
words, and invalid parameter tails fail closed. The identifier is the stored
unsigned 64-bit value; decimal magnitude is not a framing invariant, and the
current template/Interactive corpus includes a valid short local script ID.

Wide ActionBase tag `0x0384`, member count 10, is the current
`PreloadLevelSeqAction` wrapper. Its two fields after the common ActionBase
members are `levelSeqId` as `Param<string>` and `showAfterPreload` as
`Param<bool>`. The selected dispatcher/type-usage row, generated setter order,
and the sequential bytes agree on that cursor. This removes the leading stop
from 52 current files and advances each to its next declared union boundary;
all 52 contain another unsupported action or header, so this layout produces
no whole-file promotion by itself. The authenticated 5,030-file comparison
keeps 2,164 named-exact and 2,866 bounded-partial files with no regression.
Changed member counts, parameter markers, boolean values, or binding tails
remain hard failures.

The next aggregate first-stop recovery binds wide ActionBase tag `0x03f1`,
member count 11, to `SetCharacterGait`. The selected dispatcher and generated
wrapper place `character` as `Param<EntityPtr>`, `gait` as
`Param<GroundedMoveGait>`, and `handle` as `ParamOutput<uint>` after the common
ActionBase members. Generic-type reuse in current metadata proves the entity
and unsigned-output wrappers; the exact sequential cursor accepts both gait
values present in the corpus. This advances 93 current files by 95 or 96 bytes
to their next declared union boundary. Every one has another unsupported
action, so the isolated layout adds no whole-file promotion: the same-state
5,030-file comparison retains 2,165 named-exact and 2,865 bounded-partial
files, with zero regressions. Member counts, entity-pointer envelopes, enum
parameter tails, and output bindings remain fail-closed.

The following reviewed header extension binds wide tag `0x00c1`, member count
18, to `ScriptEvent_OnLeaderLeaveTriggerVolume`. The selected ActionHeader
dispatcher authenticates the concrete wrapper, while its generated inheritance
chain fixes the complete order: seven `NodeBase` fields, seven `ActionHeader`
fields, `ScriptEventHeader.targetScript` and `triggerTarget`, then
`triggerSlotIdFilter` and `triggerSlotIdOutput`. The final two members are
`Param<uint>` and `ParamOutput<uint>` respectively. Every currently reached
record closes at the exact next header or action-map boundary; maps that end
after this header can then continue through the existing empty blackboard and
owner reader to physical EOF. Remaining rows stop at a different unreviewed
header tag. Unknown member counts, invalid booleans or parameter bindings, and
changed nested pointer forms remain fail-closed.

ActionHeader tag `0x00bb`, member count 18, is the current
`ScriptEvent_OnCustomEvent` wrapper. It shares the authenticated
`ScriptEventHeader` prefix, then reads `eventArgsPtr` as
`ParamOutput<EventArgsPtr>` and `eventKey` as `Param<string>`. The exact cursor
closes all currently reached records and rejoins 59 complete serialized maps.
In the isolated 5,030-file LevelScript comparison this promotes 53 whole files
to named exact schemas with no regression; the other reached maps stop at a
different reviewed boundary or a positive `ParamListForGraph` count. The same
layout closes the final header lists in the six progression templates described
below. This identifies stored event arguments and keys, not runtime event
dispatch or handler ownership.

The first positive-getter extension authenticates two current `PureGetter`
dispatcher entries against the selected native pair. Tag `0x0130` is
`GetLevelScriptStage` with one `Param<LevelScriptPtr>` member after `NodeBase`;
tag `0x0101` is `GetLevelScriptPropertyGenericBool` with string-path and
level-script-target parameters. Their exact envelopes and generated fields now
advance inside the same list cursor. This closes supported `SwitchInt` maps
whose value parameter references a local stage getter and one supported
`IfElseAction` map. Positive getter lists are therefore a shared physical
boundary, but not a shared schema: the remaining IfElse cohort uses several
other boolean-getter tags and header types, while most remaining SwitchInt
graphs also contain unsupported action tags. Each requires its own selected
dispatcher identity and generated layout before promotion.

The later-action histogram is dominated by repeated actions inside large
graphs, so raw occurrence count overstates immediate map yield. The current
dispatcher maps `0x001f` to `BlackScreenFadeIn`, `0x0370` to
`PlayRemoteComm`, `0x0496` to `ShowSceneDecorationNew`, `0x04b5` to
`StartLevelCustomPerformance`, and `0x0511` to `WaitForSeconds`. The first two
generated wrappers close nine parameters each;
`BlackScreenFadeIn` includes byte-backed audio enums and nullable override
duration parameters, while `PlayRemoteComm` carries four fades, its identity,
two booleans, and two mask-type parameters. `ShowSceneDecorationNew` reads a
`Param<ulong>` dynamic-entity identity followed by `Param<bool>` visibility;
`WaitForSeconds` reads one `Param<float>`. `StartLevelCustomPerformance` reads
a nullable `Param<bool>` and `ParamOutput<uint>`; the current corpus contains
both null and present boolean wrappers, so treating the field as an always
present scalar loses the cursor. These actions now advance in the sequential
list and close a small set of complete maps. The newly exposed leading blocker,
tag `0x04b1`, is current-build `StartDialogAndTeleportAction`, not the stale
`StopLevelSeqLoopSegment` identity in older catalogs. Its exact inherited
`ClientCutsceneTeleport` sequence is two `Param<CommonMaskBlendData>` values,
level ID, position, Euler rotation, teleport ID and nullable teleport UI type,
followed by the concrete dialog ID. Current mask values retain the aligned
16-byte audio-behaviour struct and either a null curve or the observed empty
three-member `AnimationCurve`; a future curve with keys fails closed. The same
selected dispatcher authenticates and the sequential lane now reads
`BlackScreenFadeOut` (`0x0021`), `BlendToCameraTransformWithoutBack`
(`0x0027`), `CheckBoolIfFalse` (`0x0052`) and `WaitForNpcProxyReady`
(`0x050f`). The camera action follows its 16 generated parameters exactly;
its current alternative-pose lists are null or empty and its curve key is
nullable, so positive poses or a new curve-key shape remain unsupported. Rank
future work by whole maps unlocked after all list boundaries, while retaining
the raw histogram as a workload measure.

The next selected dispatcher batch closes five more dominant action-list
frontiers. `NpcProxyPatrolStart` (`0x0331`) reads force-idle, level ID, patrol
ID, restart mode and target proxy parameters. `BlendToCameraTransform`
(`0x0026`) shares the exact null-or-empty alternative-pose boundary and camera
parameter primitives with the without-back variant, but retains its distinct
need-interrupt/reset/use-angle prefix and 15-member generated order.
`AirWallEnable` (`0x0015`) proves that `AirWallPtr` is not the compact
`EntityPtr` wire shape: its constant is the aligned 24-byte struct containing
the use-slot flag, logic ID and slot ID before the ordinary `Param` tail.
`PlayRadioAndWait` (`0x036f`) inherits the five `PlayRadio` parameters without
adding a concrete member, and `PlayAudio` (`0x0358`) reads output handle, audio
key and stop-on-release. Positive camera alternative-pose lists remain outside
the supported current lane.

Four compact actions from the following frontier also close in exact generated
order. `ManualStartLevelScript` (`0x0312`) carries level ID and level-script
pointer parameters. `PreloadCutsceneAction` (`0x0381`) carries cutscene ID,
multiple-preload flag, a nullable string-list parameter and the post-preload
visibility flag. `RaiseCustomLevelEvent` (`0x038a`) uses a one-member
`EventArgsPtr` constant inside its parameter before the event key, and
`ShowUIToast_DevOnly` (`0x049f`) carries duration and text.

The same selected dispatcher now closes `SetPlayerGait` (`0x0468`),
`UnnoticeableTeleportAbsolute` (`0x0500`), `NarrativeBlackScreenAction`
(`0x031A`), `ResetCameraPosition` (`0x03A0`), and `ToggleClearScreen`
(`0x04DD`) in generated order. Their nested values reuse the independently
proved parameter, pointer and nullable-list codecs; the narrative action's
localized text is a strict `Param<List<LangKey>>`. Getter tag `0x0109` is the
separate `GetLevelScriptPropertyGenericInt` wrapper and reads its property path,
string and `LevelScriptPtr` without borrowing the same-numbered action layout.
The shared action-map contract authenticates all six identities against the
selected native inputs before any owner cursor advances.

The following frontier adds six more actions plus one header and one getter.
`SetEnablePlayerMoveCamera` (`0x0402`), `WaitForEntityStart` (`0x050C`),
`TreasureHuntConfigAction` (`0x04F5`), `RestorePlayerGait` (`0x03A9`),
`LoadLevelSequenceAction` (`0x0304`), and `ManuallyStartGuideGroup` (`0x030E`)
use their generated parameter orders. The treasure-hunt route establishes the
current nonempty `Param<List<EntityPtr>>` element as the exact three-member
logic-ID, slot-ID and use-slot-ID structure; invalid member counts and boolean
markers fail at that element. Header `0x0085` is
`LevelEvent_OnProxyPatrolCheckpointReach` with seven concrete members, while
getter `0x0022` is `CompareQuestState` with its comparer and two quest-state
parameters. Their switch routes, wrapper identities, setters and reader windows
are byte-pinned independently; same-numbered rows in another dispatcher family
cannot select these layouts.

`LevelCameraLookAt` now advances its 31 concrete parameters after the inherited
action envelope. The LevelScript-owned `camera_look_at.py` reader loads the
byte-pinned `camera_look_at_layout.json` contract and gates on both selected
native inputs. Its initial/exit state constants are unmanaged 24-byte structs:
the `Param` formatter copies that raw value, rather than invoking the separately
generated seven-member state wrapper. Four booleans and three floats have exact
native offsets; padding is preserved without semantic interpretation. Mount
points and look-at modes are Int32 enums. Camera-control outputs serialize only
their target and nullable path, with no camera object payload. The blend curve
key is a one-string wrapper inside its parameter, not an enum. Null parameters
remain distinct from present values; unknown nested member counts and native
input drift fail closed. These are exact stored-field boundaries, not proof
that a camera action executes. Later unsupported actions still prevent complete
maps from closing in affected files.

`RemoveCameraControlState` (`0x0392`) closes as a separate six-parameter camera
route: nullable blend-curve key, blend style, blend time, camera-control state,
control-state ID and override flag. Every exposed current camera-control-state
constant is null; its binding tail remains meaningful and includes both the
dynamic named-path form and one fully unset `-1/-1/null` form. The reader admits
only that null constant and those exact `Param` tail rules, so a future concrete
`CameraControlState` value fails before advancing the action cursor.

The LevelScript sequence reader now reuses the shared byte-pinned
`action_map_layouts.json` node codecs at each unsupported action, getter or
header cursor. The shared entry point validates both selected native inputs
before decoding; a missing/mismatched pair, unknown union, changed member count,
or unsupported nested value fails at that node. This brings the independently
reviewed assignment, control-flow, entity-event and typed getter layouts into
LevelScript without inferring their identities from another union family.
All three declared lists advance sequentially, including zero or multiple
headers, and ordinary nullable UTF-8 UIDs retain their actual lengths. The
existing specialized dialog/camera/script codecs remain available within the
same sequence. A complete map still requires the following empty parameter
blackboard and a complete named owner cursor through physical EOF. Thus a
decoded map alone cannot promote an unsupported owner tail. The authenticated
isolated before/after inventory and next exact-cursor blockers are recorded in
`reports/game_data/levelscript_shared_action_isolated_current.json`; the durable
result is shared stored-layout coverage, not runtime graph execution.

Positive LevelScript `enemies` dictionaries now advance the exact current
`uint -> LevelEnemyData` wrapper. Each 30-member value consists of the 14
inherited `LevelEntityData` members and 16 generated enemy members in formatter
read order. The nested lane closes nullable 18-member born behavior, spawned
buffs and their four-member blackboard pairs, the eight-byte native
`Nullable<float>` representation, idle-animation strings, nullable three-float
AI override attributes, and the generated action/patrol enums. Current dynamic
AI blackboards are null; a future positive `Dictionary<string, object>` stops
there because its runtime object union is not yet named. This establishes the
real cursor into `exitBuffer` without searching for a later entity key.

Positive `interactiveLocks` dictionaries also close their generated two-member
owner and 18-member `InteractiveSingleLockData` values. The exact order covers
interactive identity, mini-game IDs, the nine one-string `LangKey` wrappers,
panel configuration, quest/submit strings, blend/submit flags and the six-value
unlock enum before the global logic ID. This is authored lock and localized UI
configuration; it does not prove which lock the runtime currently presents.

Positive LevelScript `interactives` dictionaries now advance exactly as
`uint -> LevelInteractiveData`. The generated value wrapper has 25 members:
14 inherited `LevelEntityData` members followed by 11 interactive members.
Nested component/global/map/property values use the generated
`ParamKeyValue(key,value)`, `ParamValue(type,valueArray)`, and
`ParamValueAtom(valueBit64,valueString)` orders. Every current value has a null
`progressLockCondition`; the codec accepts that exact union-null tag and fails
closed on a non-null condition until its concrete runtime union is recovered.
All current positive dictionaries reach their next top-level member with one
sequential cursor; files with later positive modules or unsupported task maps
remain partial at those later named fields.

Positive LevelScript `modules` dictionaries have the same exact sequential
handoff for all eight current concrete wrappers. The selected native
`LevelScriptModuleData` dispatcher binds tag `0x0006` to the 27-member
`GhostWallModuleData`, `0x000d` to the four-member
`SpecialSightControllerData`, `0x000e` to the nine-member
`SuperPressureBoardGroupData`, and `0x0013` to the seven-member
`WaterProgressSyncData`. Their generated orders name the two inherited
`disableWhenCompleted`/`id` members before the concrete fields. The codecs
validate strict booleans, finite vectors and timing values, `EntityPtr`
wrappers, collection counts, and the generated movement/pressure-board enum
ranges. Tag `0x0007` additionally closes the nine-member
`GuideButterflyModuleData`, including gather/scatter timing and effects, the
leader pointer, and exact three-member scatter records with their butterfly
pointer lists and trigger-volume IDs.
Tag `0x0005` closes the seven-member `FogNestControllerData`: AirWall pointers,
five-member transform/effect rows, the fog-nest entity pointer, controller size
flag and one-member LSM pointers all advance their generated boundaries.
Tag `0x0011` closes the eight-member `TyphoeaArcheryUnitData` and its
12-member target rows, including nullable extra-battle, spline-movement and
scale configurations, spawn transforms and VFX connection lists. Tag `0x0002`
closes the 16-member `EncounterData`, including AirWall/enemy pointers and the
generated battle, intro, alternate-intro, teleport-slot and tail shapes. The
current encounter opera arrays are null or empty; a future positive
`OperaSegment` array remains fail-closed until its nested `ParamKeyValue`
sequence is separately proved.

The independent terminal fallback remains for files outside that sequential
profile. Its final five members are `scriptId`, `startShapeList`, `startType`,
`taskMap`, and `triggerVolumes`; it accepts the range only when one
filename-independent byte-grammar candidate closes at physical EOF. Because
the preceding members are opaque there, that result remains a named partial
schema. Other nonempty-action-map shapes retain their weaker exact prefixes;
changing coverage belongs in the corpus report.

LevelData exposes full schemas or bounded top-level frames only when its
sequential cursor and any independent suffix ranges are exact. Its current
15-member `LevelDataBlackbox` wrapper is read in generated order from `basic`
through `statistics`. The maintained codec closes the 13-member basic flags,
four completion flags, nullable one-list craft/blueprint/statistics objects,
discard restrictions, task and fail-task rows, general-ability states, intro
effect vectors, and inventory bundles. Member counts, booleans, finite floats,
UTF-8 strings and collection bounds fail closed. Positive
`predefinedTemplates` are an object list whose two-member wrapper reads
`predefinedParam`, then `templateId`. The current generated `PredefinedParam`
wrapper has 20 nullable component slots, in order: cache, common,
env-generator-with-activator, fluid-container, fluid-reaction, grid-box, hub,
miner, power-diffuser, power-gate, power-pole, power-port, producer, selector,
the two sewage-plant endpoints, sign, travel-pole, underground-pipe and valve.
Each slot is accepted only with its current generated member count and typed
body; this includes the nested two-member item/social records, three-member
hub selector ports, and nested fluid container. Thus all current positive,
empty and null template shapes continue from the exact end of the blackbox
into later LevelData members; future component-count drift remains fail-closed.
The top-level `predefinedParams` field reuses that same 20-member component
codec inside the generated two-member `LevelFactoryPredefinedParamData` owner.
Its stored order is `instKey`, then nullable `param`. Current positive lists
exercise common, cache, producer, power, selector, hub, grid, pipe, fluid,
travel, miner, valve and environment-activator component wrappers, all with
their independently checked member markers and typed bodies. A changed owner,
component marker, scalar, string, collection count or nested wrapper stops at
the field instead of shifting the remaining LevelData cursor.

Nonempty/null LevelScript
action maps expose a named `actionMap.dataMap.actionList` count and first-record
envelope, or a named null `actionMap`, while all later union data stays opaque. One high-coverage
first-record variant has a bounded sequential body reader, but later
records/lists remain unowned. AnimationConfig now advances the first five
generated wrapper members at a real cursor in every current file:
`_fallbackMontages`, `avatarBlendProfilePath`, `bakedBindingPath`,
`boneWeightMasks`, and `controllerPath`. The fallback reference is null in the
supported shape; each populated mask row has the exact two-member `layerName`,
`maskPath` order with bounded UTF-8 and a signed 64-bit path hash. The following
`AnimationConfigExtraData` is polymorphic at the root. `0xff` is null; current
tag zero selects the 30-member `CharacterAnimExtraData` wrapper and tag one
selects the 20-member `EnemyAnimExtraData` wrapper. Consequently, the byte at
the old character offset 62 is the concrete extra-data object header, not the
start of `montages`. The character reader names all six inherited shader/event
members, strict enable flags, movement/cloth scalars, hurt-animation curve
dictionaries with `Vector2` and five-member `SkMorphPlaySetting` values, and
both empty and populated move-additive dictionaries. The current move value is
a five-member wrapper containing four fixed `AnimationClipAsyncInfo` records
and one `SkMorphPlaySetting`. It then closes override performs, loop counts,
the three-member special-dash wrapper, the two-member special-idle wrapper and
all six observed idle-condition union tags, and three-member state-perform rows.
The true `montages` boundary follows `walkSpLoopCount`; in Endminf its exact
cursor is 2234 and its stored count is 94.

The montage dictionary is now sequentially decoded. Current union tag zero is
the 26-member `ClipMontageData`, tag one is the 20-member
`SequenceMontageData`; both share the 17 generated `AnimMontageData` members.
The clip branch adds one fixed async-clip record, its root-rotation flag and
seven named root-motion curves. The sequence branch adds its end, loop and
start async-clip records. `AlphaBlend` is the current three-member option/time/
custom-curve wrapper. Only those current tags are accepted, so a future nested
variant fails at its exact tag and member-count cursor.

After a supported montage dictionary, the sequential tail closes
`npcMontages`, the optional/retarget controller hashes, empty
`syncGroupAnimationCurves`, both serialized `FAnimationCurve` dictionaries and
the trailing booleans. Curve rows retain the generated three-field wrapper and
all eight fixed-width `FKeyframe` members. Two representations must remain
separate. The standalone generated keyframe wrapper reads alphabetical setter
order and stores into native offsets, but `FAnimationCurve.keys` is a counted
bulk unmanaged array whose 32-byte elements use native struct order:
`time`, `value`, `inTangent`, `outTangent`, `tangentMode`, `weightedMode`,
`inWeight`, `outWeight`. Treating bulk slots as standalone-wrapper fields turns
one-third weight bit patterns into an enum and erases increasing key times.
The matching curve wrapper directly reads `keys`, `postWrapMode`, then
`preWrapMode`. The byte-pinned identities,
windows, offsets and helper joins live in
`scripts/game_data/contracts/animation_curve_native.json`; its reader fails closed when
the contract bytes or shape change. This closes character and ability
frames with both empty and populated sync-group dictionaries, without resolving
numeric hashes back to source paths. Positive `npcMontages` was the apparent
alternate-tail gap: each `GameplayTag` is a one-member value wrapper carrying a
32-bit tag, so treating it as an unwrapped 64-bit value displaced every later
cursor. The corrected five-byte row framing makes the existing one-member
sync-group dictionary wrapper align exactly and closes those tails. The enemy
reader closes all 20 generated
members. Its three-member blow-off config contains total time and two root-
motion curves; the two-member turn-start config contains duration and total yaw.
The ten-member hurt-data wrapper closes both enum lists, its valid/supported
masks, strict behavior flags, shake duration, and both typed dictionaries.
Hurt entries use the generated seven-member scalar/curve/`Vector2` order.
Shake-intensity keys retain their byte enum width and their two-member values
retain the object header before animation speed and weight. This distinction is
required to keep every later cursor aligned. The current extra-data formatter's
native static initializer registers three union entries; tag two joins the
current `UpperBodyFightExtraDataForMemoryPack` wrapper. It inherits the 30
character members and appends the generated `upperBodyFightTimeout`,
`upperBodyLayerName` order. Purrchena's 32-member value reaches those fields at
the exact character-base cursor, reads a finite timeout and bounded non-null
UTF-8 layer name, then joins its montage dictionary and closes at EOF. Thus the
current AnimationConfig family has an exact named frame for every file. A
consumer may resolve path identities only through an authenticated
`StringPathHash.bin` catalog; the framing reader itself does not guess paths.

AnimationConfig's shader declaration has a separate native consumption proof in
`scripts/game_data/native_contracts/animation_material_publication.json`.
The gameplay component reads numbered Animator output parameters and forwards
their evaluated floats using configured shader IDs and renderer masks; this
publication branch does not directly evaluate the stored montage curve keys.
Character UI instead has `CharUIModelMono`'s `EmotionBlend` parameter to
`_EmotionBlend` material-helper route. The selected Overview controller declares
that parameter, but neither selected start nor loop clip binds it. These are
authenticated base-code and selected-source facts, conditional on runtime
actor/IFix selection; live writers and draw consumption remain unresolved.

NPC MontageNew closes a three-field `animType`, `data`, `tag` root and all 24
named `NPCMontageAnim` members through EOF. The generated formatter order also
names clip info, dynamic entities, their show/hide events, and transition
overrides. Fixed async-clip and transition values are decoded with finite-float
and boolean gates. Each four-member `DynamicEntityExtraEffect` advances its
effect path, two consecutive 12-byte `Vector3` values, and mount-node path.
The parent then consumes `hideAccName`, the loop flag, integer `MountPoint`,
16-byte prefab GUID, path hash, sync flag, and event type in generated order.
This corrects the former 20-byte vector span that misread the last vector word
as an empty string. All current MontageNew binaries now have a complete named
schema; runtime selection and playback remain separate evidence requirements.
NPC PrefabInfo's textual JSON lane is also schema-gated rather than promoted by
generic JSON parsing. Its current 42-field `NPCPrefabInfo` object, the two older
41-field rows without `correspondingCharId`, battle shape and vectors,
accessories, born effects, water interaction, confront/battle tags, and every
scalar/list type are validated exactly. The current skill-blackboard and
idle-break collections are empty; an unsupported populated body fails closed.
The separate PrefabInfo manifest and Montage hash map use the exact catalog
schemas described above.

MissionRuntimeAsset now has separate exact textual-JSON schemas for metadata
and the main mission body. All current `_meta.json` rows validate the
five-field mission root and the three-field accept-mode object. The populated
mode-info branch admits only the stored `$type` identities and exact fields for
`NPCInfo` or `EnterAreaInfo`, including its typed area rows. The main-body
reader validates every nested object shape, array member and scalar type, and
dispatches every polymorphic condition, tracking row, external-info row and
client action through its stored `$type`. Only three objects are semantically
dynamic dictionaries: `questDic` maps authored quest IDs to the closed quest
schema, while `propertyIdToKeyMap` and `propertyKeyToIdMap` are typed inverse
maps. Quest keys must equal the nested `questId`; property maps must be exact
inverses; client-action key/value arrays must have equal lengths. Unknown
fields, discriminators, populated formerly-empty branches or scalar-type drift
therefore fail closed. `jsondata_corpus` binds both readers to the authenticated
VFS ledger and classifies the entire current MissionRuntimeAsset family as
schema-decoded. This is stored-schema closure; runtime activation and mission
ordering remain separate evidence questions.

MapConfig textual JSON also has a complete current schema. Both root shapes
are admitted explicitly, with optional `sceneStates`; level arrays, 574 named
scene-state values, 87 typed condition rows and their recursive combined
conditions, and both directions of the 158-entry map-variable dictionaries are
validated. The two dictionaries must be exact inverses. Client defaults are
empty throughout the current corpus, so a populated future shape fails closed.

An empty LevelScript `ActionMapAssetRaw` is longer than its three empty
`ActionSerializedMap` lists: it also contains the following one-member
`ParamListForGraph`. When that value list is empty, the complete action-map
boundary is byte 20. Files with a nonempty parameter blackboard close only the
serialized-map boundary at byte 15 until the parameter values are decoded.
Earlier byte-7 framing covered only the first list count and must not be treated
as a complete action map.

`LevelScriptTemplateData` uses the six-field wrapper order `actionMap`,
`maxStage`, `properties`, `propertyIdToKeyMap`, `taskMap`, `templateId`. The
empty action-map boundary includes both the empty three-list `dataMap` and the
empty `paramBlackboard`; it ends at byte 20, not byte 15. Two current templates
originally carried `maxStage = 1`, three null collections, and the terminal ID.
The same sequential reader now also advances populated `ParamKeyValue`
properties and their paired `Dictionary<int, string>` IDs. Null task maps join
the terminal ID directly. Positive task maps reuse the authenticated
`LevelScriptTaskData` entry and condition-union codec and must consume exactly
to that same boundary. This closes every current empty-action-map template as
a complete named schema. Populated maps now reuse the same authenticated
sequential action/getter/header codec as LevelScript and Interactive data. In
the six `LST_Sdg_*` progression templates, the last missing map record is
header tag `0x00bb`, member count 18: the current dispatcher binds it to
`ScriptEvent_OnCustomEvent`, whose inherited script-event fields are followed
by `eventArgsPtr` as `ParamOutput<EventArgsPtr>` and `eventKey` as
`Param<string>`. Those maps now join the empty parameter blackboard, named
properties and task map, and the terminal template ID at physical EOF. Other
populated templates retain their exact endpoint ranges until their first
unsupported map record is reviewed; the terminal ID does not make the
intervening action/task bytes exact.

`LST_Test_1` additionally closes its one-entry positive task map. The selected
current `GameCondition` dispatcher binds wide tag `0x012f`, member count eight,
to `InteractiveCheckBool`. A byte-pinned native contract validates that switch
branch and generated inheritance before the task decoder admits the four
common condition members followed by `compareValue`, `entityId`, `key`, and
`levelId`. The task cursor then rejoins the terminal template ID at physical
EOF. This proves the stored condition and parameter layout; it does not prove
server evaluation, entity resolution, or the resulting interactive state.

The shared LevelScript action-map reader also has current-build-authenticated
exact layouts for `BlendOutFromCamera`, `RestoreCharacterGait`,
`ToggleClearScreenButRadio`, `LevelEvent_OnCustomEvent`, and
`ScriptEvent_OnScriptActive`. Their inherited base fields and generated wrapper
fields are consumed sequentially through reviewed Param codecs, including the
camera reset enum. A following reviewed batch binds ActionBase tag `0x00BD` to
`ExitLevelCustomPerformance`, tag `0x0020` to
`BlackScreenFadeInAndOut`, and tag `0x036B` to
`PlayLevelSequenceAction`. The black-screen audio enums are byte-backed; the
sequence action uses an exact `Param<List<ulong>>` plus nullable or empty entity
lists. Each layout advances only through authenticated generated order and real
Param cursors. The next reviewed group binds header tag `0x00CA` to
`ScriptEvent_OnScriptStageChanged`, ActionBase tag `0x0376` to `PostAudioCue`,
and tag `0x0039` to `CameraShake2D`. The stage event names its script/target,
integer filter, and integer output; the audio cue's two enum parameters use the
generated default Int32 backing; the shake action closes a camera-shake config
pointer and integer output. The next authenticated group adds `Play3DRadio`,
`NpcProxyOverrideEnvTalk`, and `PlayCutsceneAction`, plus the getters
`CheckLevelScriptStage` and `CheckMissionOrQuestIsComplete`. Strict generated
codecs own the environment-talk struct list and `CommonMaskBlendData`; radio
voice attenuation remains a reviewed enum parameter. Current coverage counts
and first-stop frequencies stay in the generated LevelScript frontier reports.
The next authenticated layouts add `ManuallyAcceptClientGuideGroup`,
`MainCharMoveTo`, `TeleportNpcProxy`, `PreloadDialogAction`,
`NpcProxyPlayMontage`, and `LevelEvent_OnDialogEnter`. Their exact codecs add
`Param<List<string>>`, signed-int-backed enums, and the action-specific raw-i32
`Param<GameplayTag>` representation; the latter does not contain the standalone
GameplayTag reader's nested one-member header.
The following reviewed layouts add `OnDialogExit`, `OnQuestStateChanged`,
`PostMusicEvent`, `ShowLimitedGuide`, and `SetNpcProxyVisible`. Their level-event
owners, quest-state filter, music pre-action enum, guide types, and visibility
parameters all follow current generated setter order and exact Param codecs;
unsupported future enum or nested shapes still stop at their owning cursor.

The next two reviewed batches extend the same shared reader rather than adding
family-local guesses. They authenticate `CharTutorialPushStage`,
`SetCharSkillButtonActive`, `IntGetterRandom`, `AllGuardSwitchAIMode`,
`SetEnablePlayerActionMask`, `BlockAutoMusicChange`,
`ShowSceneDecorationWithHandle`,
`OnGhostWallAfterTeleportPerformFinish`, `EnterCustomMusicMode`, and
`SwitchAIBarkEnable`, followed by `SetInteractive3DUIEnable`,
`ShowSceneDecorationNew`, `RepeatEntityPtrListAction`, `StopEffectOnNpc`,
`StartDialogAction`, `SetEnablePlayerAction`, `Play3DRadioAndWaitFor`,
`NpcPlayMontage`, `NpcPatrolPause`, `PlayCameraWorldEffect`, `PlayRadio`, and
`ListGetValueString`. The new parameter shapes include signed enum aliases,
entity and string lists, dialog mask records, montage fields, and output
handles, all in authenticated generated order. Because Template and
Interactive reuse this reader, the layouts also close the two populated
treasure-chest templates and the race teleporter, electric jump machine, and
phantom-radio Interactive files.

The shared reader now also closes three of the four former Interactive stops.
The horn route authenticates `UIntToInt` and `StringEqual`; the week-raid camera
route authenticates `BlendToCameraTransform`, `Vector3Construct`,
`Vector3NewCompare`, `Vector3LookRotationToEuler`, and `Vector3MultiplyInt`.
Its `Param<List<PosRot>>` is exact only for the observed null or empty list;
positive elements remain unsupported. The split-platform route exposed that
`LevelScriptPtr` has no decimal-magnitude framing rule: its short local ID is a
valid unsigned 64-bit value with the same zero reserved word and exact Param
tail as long IDs. `SetEntityPosition` also closes the camera minigame template.
All these routes rejoin their owners only at physical EOF.

The former chasing-rabbit remainder now closes through its complete observed
chain. Fifteen separately authenticated action, getter, and header layouts end
at `LevelEvent_OnPatrolEvent`; nested `GetConditionResult` uses the independent
`CheckWikiEntryUnlocked` condition layout. Counted `Param<bool>` values and a
null-or-empty-only `Param<List<GameplayTag>>` supply the two new exact parameter
shapes, while positive GameplayTag elements remain unsupported. This brings
every current Interactive file to a complete named schema. The same shared
layouts advance LevelScript files only through their own exact later nodes;
cross-family reuse never bypasses the owning dispatcher or EOF gate.

The following LevelScript frontier authenticates `SetEnemyAIMode`,
`SetFunctionAreaEnable`, `GetQuestState`, `CharacterPlayPerform`, and
`StopLevelSeqLoopSegment`. Their generated layouts add bounded AI-mode and
quest-state parameters, function-area identifiers, the character-performance
record, and the level-sequence loop-segment stop fields. Each route was replayed
through the full LevelScript family with paired before/after cursors; only files
that reached physical EOF moved to exact status, and no earlier exact file
regressed.

The next authenticated group adds `OnTeleportFinish`,
`StopLevelSequenceAction`, `CheckMissionOrQuestIsProcessing`,
`CharTutorialToggleStepHUD`, and `SwitchString`. The shared reader preserves the
header, action, and getter dispatcher domains separately while consuming their
teleport target, level-sequence handle, mission/quest state, tutorial HUD, and
string-switch parameters in generated setter order. Full-family paired replay
again promotes only exact EOF joins and retains unsupported following nodes at
their first byte.

The next group closes `ScriptEvent_OnScriptComplete`,
`AddBuffToTargetFromGodEntity`, `ManualSetMusicState`,
`SetTargetForceInFight`, and `GetClientGlobalVar`. It adds the exact
`Param<List<BlackboardKVPair>>` and buff-output shapes, three independently
authenticated music-state enums, and the target/entity and global-key
parameters. The Script event remains in its header dispatcher and the global
lookup remains in its getter dispatcher; identical scalar representations do
not merge those domains.

The following six exact routes are `SwitchTempAbility`,
`AddBuffsToTargetsFromGodEntity`, `ScriptEvent_OnPropertyChanged`,
`AddBuffToTargetV2`, `EntityCastSkill`, and `GetCurDungeonId`. Their generated
layouts distinguish the multi-target and V2 buff parameter sets, the script
property-change header, the entity skill-cast fields, and the dungeon getter's
own dispatcher. Each layout preserves its nested Param ownership and rejoins
only after the authenticated member count and cursor agree.

The next supported routes are `FillCharacterUsp`, `EndCameraShake`,
`EntityHideList`, and `NpcProxyResetEnvTalk`. `WaitForCondition` is also
authenticated at its outer action wrapper, but remains deliberately withheld:
its `GameCondition` member reaches two different tag/member-count variants and
there is no exact nested condition-union codec yet. An outer wrapper identity
does not authorize scanning past that second polymorphic boundary.

The first exact nested-condition batch now admits `CheckLevelScriptPropertyBool`
and `CheckPlayerOnGround` under the separate GameCondition dispatcher, allowing
their `WaitForCondition` actions to close. The same frontier adds
`SetAtbValue`, `PauseSquadMemberAI`, and `SummmonTeamWithPos`. Four other
observed condition tag/member-count variants remain at their first byte until
their own dispatcher and generated layouts are authenticated; the outer Wait
wrapper does not transfer the two supported condition shapes to them.

The remaining reached `WaitForCondition` variants now have their own exact
condition layouts: `CheckTalkOptionFinish`, `CheckQuestState`,
`Conditions_OnEnterMainHud`, and recursive `CombineCondition`. The same shared
batch adds `CharTutorialStepStateChange`, `ShowUIReadingPopPanel`, and
`BlendToCameraTransformWithTime`; the last also closes a populated template.
The next action frontier authenticates `PauseEnemyAI`,
`NpcProxyStopCurMontage`, and `TryEnterTyphoeaArcheryAbility`. Their generated
fields traverse every reached occurrence, but a file is promoted only when all
later nodes also close and the owner reaches physical EOF. The small-family
layouts above can therefore unlock additional LevelScript files without
weakening the independent action, getter, and condition dispatcher gates.

The following frontier adds `CharTutorialOpenStepHUD`, `FinishBuff`,
`ShowUIToast`, `MoveBambooNext`, `ExitCustomMusicMode`, and
`ClearEnablePlayerActionMask`. `FinishBuff` uses an exact `Param<BuffPtr>` whose
observed nested value follows the generated 4/1/2 member chain, cached unsigned
identity, null object marker, and ordinary parameter tail. `ShowUIToast` keeps
its generated toast type as an Int32-backed enum alias. The two traversal-only
routes remain valuable cursor advances but do not count as whole-file gains;
only later physical EOF closure promotes their owners.

## The SkillData formatter and wrapper registration

Current registration locates real SkillData formatter/wrapper bodies and
their relative five-operation terminal read sequence, not a file offset.
The Core type used by `ReadValue<T>` differs from the generated wrapper's
`Register<T>` type; a generated wrapped reader alone does not prove the
adapter or active formatter. A separately gated immediate-registration site
now joins the Core key to `GenericMemoryPackFormatter` with ordered arguments
Core and `Beyond_Gameplay_Core_GameplayTagListForMemoryPack`: its type carrier
and constructor MethodSpec share the same registered class instantiation.
This proves static adapter identity and a conditional registration callsite,
not completed allocation ABI, executed registration or active Deserialize
dispatch. Registration and lookup independently share one RIP-relative cell
and the same class/static-storage dereferences. The lookup's matched node
supplies its returned value, but misses can invoke callbacks, retry or construct
alternatives; this does not fix live contents or replacement history. The separate
generic serializer's pointer/length-word carrier is not yet joined to this
formatter or authenticated VFS allocation. That static gap no longer controls
the stored-field boundary: the authenticated runtime cursor described below
selects the active reader order. Non-empty ActionGroup profiles remain
incomplete. Native pins and reviewed
limits belong to `reports/animestudio/skilldata_native_review_latest.json`;
PE reads must remain within raw section extents: virtual-only globals have
no disk value and need runtime-initialization evidence, not adjacent file bytes.

The maintained EndfieldCapture `skilldata-cursor` profile now observes the
complete direct-call surface of that selected reader: 47 field-indexed
post-read cursors for the 48-member object (field 17 is inline), plus the two
exact ActionGroup child-list post-call cursors reached inside field 0. Seven
typed helper hooks preserve the original ABI; the runtime admits only the
424-, 533-, and 568-byte hash-join samples, copies each source once into bounded
storage, and publishes only after the existing quiescent teardown proves every
detour and trampoline vacant. The accepted receipt exercised the first two
lengths; the third is the supplemental nonempty-ActionGroup target below. The
loaded complete reader body, seven helper
entries and ActionGroup window are separately hash-pinned in addition to the
native file gate. The accepted v2 receipt has zero genuine loss and overflow,
observes both required source shapes, and records complete field/child cursor
vectors after quiescent teardown. In both hash-joined samples the earlier
`one-member-wrapper` candidate begins at field 43
`switchToCenterBeforeCast`, and field 47 `useAIExclusiveFrame` closes at EOF.
Every current corpus row has that same two-candidate encoding and the same five
terminal member kinds; the native field-43 bool read therefore rejects the
candidate that begins one byte later. The census replays the verifier from its
exact receipt, source-corpus, native-context and verifier hashes before applying
this selection to all rows.

The same receipt records every field-0-through-field-42 cursor in two
byte-distinct samples whose field 0 contains the identical empty two-list
`ActionGroupData` representation. A sequential reader derived from the current
generated wrapper types reproduces both vectors exactly, then applies only to
that structurally identical profile. It closes every current profile member
except one `switchToBuffConfig` body whose nested action begins with unsupported
tag `0x0078`; that row remains exact only through field 41 plus the independent
field-43-through-field-47 terminal. Other empty-ActionGroup rows are complete
named stored schemas. Non-empty ActionGroup rows retain the selected terminal
and now name the exact start of field 0: the `ActionGroupData` member-count,
then the `passiveEventActions` and, when the first list is empty,
`timelineActions` nullable-list counts in authenticated reader order. A
positive list stops before its first record body, at byte 6 for passive actions
or byte 10 for timeline actions. The intervening action bodies remain explicit
as opaque; naming these count cursors does not promote an ActionGroup endpoint.
Unsupported nested unions stop at their owning field; names or nearby anchors
never advance the cursor.

The dominant timeline branch now has an exact current-build reader for a first
`TimelineActionData` whose `SequenceActionData` contains one extended-tag
`0x0115` `PlayAnimation` action. The generated `TimelineActionData`,
`ForceSyncAnimData`, `SequenceActionData`, and `PlayAnimation` wrapper orders
name every consumed member. The admitted shape also has an empty nested
`onEndAction`, so every reached first record closes at an exact cursor. When
`timelineActions` contains only that record, the
exact `ActionGroupData` endpoint feeds the existing fields 1 through 42 reader
and authenticated terminal selection to close the whole file.
Other first action tags and later timeline elements remain open at their first
unsupported boundary. Provider selection stays conditional on the pinned
native and input-set gates.

Physical tag `0x00B2` similarly maps to the 18-member `FindTargetActionData`.
Its nested selector tags differ from the older Buff selector table, so the
Skill reader supplies only byte-pinned current finder, validator, and
postprocessor routes and fails closed elsewhere. The reached one-action first
timeline records close exactly, but each still has later timeline records and
therefore remains a bounded partial file. Tags `0x02` and `0x03` stay open
because their finder payloads are not authenticated. Physical tag `0x009A` is
the current 11-member `DamageAction`; even its shortest current candidates
enter positive `DamageUnit` member-33 payloads and nested 85-member
`EffectActionCfg` lists whose element grammars remain unresolved, so no cursor
is promoted through that body.

Physical tag `0x008A` selects the 19-member
`ContinuousFindTargetAction.Data`. Its authenticated order is the shared
four-member action prefix, fourteen target-selection members, and terminal
`findInterval` float. Current Skill selector routes include the two-member
`ExcludeTarget` form (`excludedTargetSettings`, `processTargetType`). The narrow
first-timeline decoder closes every reached current first record, but each
ActionGroup contains later timeline records, so whole-file closure remains
open. Physical tag `0x00A2` is the 18-member `EffectActionData`; its current
85-member `EffectActionCfg` body remains opaque, so structurally reachable
cursors are not promoted to named-exact evidence.

Physical tag `0x0116` selects `PlayAnimationWithStepData`. Its 30-member wrapper
inherits the exact 16-member `PlayAnimation` layout, then reads
`animBlendInAfterStep`, `battlePoseWhenStep`, `frameToOriginAnim`, `hideWeapon`,
`hideWeaponFrame`, `montageName`, `snapDistance`, `snapFrame`, `speed`,
`speedCurveKey`, `stepBlendIn`, `stepDistance`, `stepTarget`, and `useFixSpeed`
in generated setter order. `speed` uses `BlackboardDouble` and `stepTarget`
uses `TargetSettings`; unresolved nested selector routes fail closed. The
reader closes the first timeline record at an exact cursor without claiming
later timeline elements or the whole SkillData file.

Physical tag `0x0092` selects the 19-member `CreateBuffActionData` wrapper. Its
four inherited members are followed by `asChildBuff`, `autoFinishByAction`,
`buffIconDurationSource`, `buffs`, `buffSource`, `contextKey`, `count`,
`finishWithNextSkillIfNotInherited`, `inheritSkillIdList`,
`inheritSourceSkillCastId`, `inheritSourceSkillCastInfo`, `isExtra`,
`overrideBuffIconDuration`, `passTargetGroupsToBuff`, and `targetSettings`.
Byte-pinned nested readers close every reached first action. A one-action
sequence closes the enclosing first timeline record; multi-action sequences
stop before the first unsupported later action. A one-action, one-timeline
shape can then reuse the authenticated top-level continuation and terminal
wrapper to close the whole SkillData file. Dispatch requires the complete
top-level ActionGroup/timeline/sequence shape so an unrelated byte equal to
`0x92` cannot select this decoder.

The shared timeline-sequence reader reuses only byte-pinned action contracts
and preserves the distinction between an exact action, an exact enclosing
timeline record, and a whole ActionGroup. It closes reviewed roots for
`ConvertToTargetContext` (`0x008C`), multi-action `CreateBuff` (`0x0092`),
`LaunchProjectile` (`0x00DE`), and `SpawnAbilityEntity` (`0x0169`), then reuses
the top-level continuation only when every timeline record is exact.
`IfElseAction` (`0x00C9`) is an eight-member reader whose three nested
`SequenceActionData` members are selected through the byte-pinned RIP-load and
usage-cell chain to MethodSpec 619962. The atlas mechanically validates that
MethodSpec's generic instantiation as `SequenceActionData`, and the contract
checks its ordered reads and member count against the shared reader. Recursive
decoding is capped at depth 64 and accepts the native null-wrapper branch.
Positive unproved damage-unit lists and unknown children remain bounded at their
owning child. Later `0x0148` likewise remains unsupported.

The next Skill-only shared-sequence extension authenticates `0x0147` as
`SetAbilityEntityTarget`: an extended tag, five-member wrapper, one byte, three
scalar32 values and `TargetSettings`, including the nested MethodSpec provider.
It also admits the compact `0x00D9` `JumpToAction` route without changing Buff's
ownership of its residual action reader. The positive first `DamageUnit` list
now uses the authenticated `List<CastData.CostData>` instantiation and Buff's
existing exact `CostData` element grammar, closing every current positive-list
case without widening Buff ownership. `0x0118` is now authenticated as the
six-member `PlayPerfectDodgeAnim.Data` wrapper: its booleans, enum-like scalar,
two integer fields, and float advance exactly in generated read order. This
closes every currently reached `IfElseAction` child, including nested use, but
does not promote a multi-timeline file unless all later records also close.

The same shared sequence lane admits `DamageAction` (`0x009A`) at the first
timeline root through its byte-pinned dependency and exact action cursor. The
complete supported wrapper can rejoin the top-level Skill continuation and EOF;
six distinct unsupported variants still stop at their owning selector rather
than borrowing the admitted layout. This distinction accounts for the large
whole-file gain while retaining explicit opaque ranges for the remaining
variants.

The following Skill frontier adds exact first-root readers for `EffectAction`
(`0x00A2`), `FindTargetAction` (`0x00B2`), `DebugPrintAction` (`0x009B`), and
`CheckBuffStackNumAdvanced` (`0x003C`). The common FindTarget route subsumes the
older specialized prefixes only where its stronger authenticated wrapper and
cursor close the same bytes. Variant member-count or nested-shape mismatches for
all four roots remain bounded at the selector, so the admitted roots can rejoin
the top-level continuation without widening unsupported variants.

The next Skill batch exhausts the authenticated roots that currently yield a
whole-file closure: `CheckTimedMarkerCondition`, `CheckObjectTypeMatch`,
`InterruptAction`, `PlaySoundAction`, `SendBattleSignalToLevel`,
`TimeDilationAction`, `HealAction`, `BlowOffCharacterAction`, and
`CheckTagMatch`. Each exact first record can rejoin the existing top-level
continuation, while unsupported variants and later records remain bounded. The
remaining authenticated roots improve exact record and byte coverage but do not
yet close a current whole file, so future ranking must report both gains rather
than treating record closure as a file promotion.

That exact-record frontier now also admits `CameraImpulseAction`,
`FinishBuffAdvanced`, `AddTagAction`, `SpellInfliction`, `MergeTargetAction`,
`FinishOwnerAction`, `ModifyDynamicBlackboard`, `CompareFloat`, and
`CheckBuffStackNum`. These routes reduce opaque action bytes while leaving the
same whole-file denominator because later records still stop. CameraImpulse's
uncontracted nested actions and unsupported union bytes, the non-applicable
ModifyDynamicBlackboard shape, and the earlier DamageAction variants remain
explicit bounded branches.

`CheckEntityNum` now closes with its separately authenticated nested
`SimpleCalcBBAction`, `AddDynamicCcsAction`, and `PullAction` dependencies.
The following Skill batch authenticates `ForEachAction`,
`CharWeaponVisibleAction`, and `AuraAction`; already supported downstream
`FindTargetAction` records become reachable through the same exact sequence
cursor. `ForEachAction` and `CharWeaponVisibleAction` close current whole files,
while `AuraAction` currently improves exact record and named-byte coverage only.
Unsupported `CreateBuff`, Damage, Camera and other variants remain bounded at
their own selector rather than inheriting a same-tag layout from another shape.

The next Skill frontier adds `SelfRotateAction`, `MoveToAction`,
`SetAnimatorParamAction`, and `RandomAction`, plus the nested-only
`CheckDistanceCondition`. The condition unlocks supported `InterruptAction`
and `FindTargetAction` parents; `RandomAction` also exposes one previously
blocked supported Damage route. Only exact enclosing sequences and the existing
top-level continuation can promote a whole file. Other records gain named byte
ranges without being misreported as file closure.

The accepted `183745Z` live receipt contains two different current SkillData
sources and directly confirms the two ActionGroup child checkpoints at cursors
six and ten together with the complete top-level field vectors. It does not
contain BuffData or the earlier 568-byte farming target. Its accepted stream
has no lost observations, retained-record overflow, cursor-transition errors,
or incomplete pairs; overflow in its separate off-target callsite catalog does
not weaken those two accepted observations. This receipt supports the shared
ActionGroup prefix and passive-versus-timeline split, while exact
`PlayAnimation` body ownership comes from the separately authenticated native
wrapper and corpus joins.
The native-context audit now pins an immutable promoted SkillData cursor-basis
report rather than the final `current_latest` report. The cursor verification
pins that basis and native context, and the final corpus pins the verification;
this removes the former circular provenance path and keeps replay valid when
`current_latest` is atomically replaced. The non-launching `skilldata-cursor`
preflight passes.
Start `skilldata-cursor` in targeted mode, wait for `runtime.ready`,
complete one character farming interaction so the unique farming-end payload
is deserialized, idle briefly, then stop with `Numpad 9`. Preserve the raw
receipt; do not replace the accepted publication verification until the new
source hash, both child checkpoints, teardown state, and top-level vector pass
review.

## Generic-instantiation registration is a pointer array

Generic-instantiation registration is a pointer array, not inline records;
preserve the record's padding separately from its u32 argument count. The
maintained `scripts.game_data.il2cpp_context_audit` validates current native
inputs, every registered instance, and reciprocal open-parameter ownership.
Its inventory is `reports/animestudio/il2cpp_context_current_latest.json`.
The selected `GetFormatter<T>` parameter belongs to `ReadValue<T>`; a prior
concrete-type probe was an indirection bug, not a runtime counterexample.
This static join does not establish actual generic substitution or formatter
selection. The accepted direct-reader cursor independently resolves the current
terminal candidate; it does not promote the unresolved registration history or
earlier nested fields.

## Resolving the formatter: the MVAR leaf, modules, and usage cells

The native MVAR leaf reads a parameter ordinal and indexes the supplied
method-inst vector. The gate checks that ordinal against the selected call's
registered argument. Native normal-path stores now connect method records to
their class, the metadata image-range directory, and a module selected by
bytewise name comparison from the gated CodeRegistration. The static image
partition must be complete and unambiguous; module names must be unique since
the native loop continues after a match. This does not certify initialization
execution, all cold paths, active formatter selection, or source/cursor/EOF.
The selected call's on-disk usage cell also joins through the wrapper's guarded
lazy initializer and tag-specific MethodSpec/triple resolver. This establishes
the static initialization mechanism, not an observed live cell or cache entry.
The open formatter-check carrier independently joins the same MVAR through its
class-inst pointer; reject duplicate pointer identities and token ranges.
The native method-pointer resolver retries a missed original-context lookup
with transformed argument vectors. Its direct class-tag branch uses one shared
global carrier plus the type-record offset for both adapter arguments. The
normal producer's image/namespace/name lookup and class copy connect this to
the unique `mscorlib.dll / System.Object` byval record; its bytes match both
arguments of the static object/object candidate. Actual initialization, cache
population and interned pointer identity remain unobserved: byte equality does
not select a particular shared Deserialize body.

## The instantiation cache, MethodSpec joins, and RGCTX slots

A separately gated initializer seeds the generic-instantiation cache from the
selected registration's pointer table; insertion and lookup share the same
storage global. This conditional path is not an observation of cache contents.
The gated object-tag comparator and hash use only the tag and one flag bit,
not record addresses; enumerate every registered pair matching that projection.
A unique static match still does not prove the returned runtime instance.
Matching MethodSpecs join bounded method/invoker index triples and pointer
slots; the no-adjustor sentinel reuses the ordinary method pointer. Other
adjustors need an independently bounded table and remain unsupported here.
Keep RGCTX range-relative slots distinct from module entry indices. The adapter
class-token range connects its selected slot to a reciprocal second type
parameter (VAR), not an unrelated concrete type. The class initializer's
conditional path converts 16-byte definitions to eight-byte runtime slots
using the class generic context; static definitions are not observed slots.
The reviewed MethodInfo construction path stores the original instantiated
class separately from resolved shared-code pointers. Do not substitute the
shared body candidate's object/object arguments for the companion's class
context; actual cache contents and invocation still need independent evidence.
Nested class slots independently link MethodSpecs for the non-null adapter,
formatter lookup and instance creation to reciprocal parameters of that same
adapter type. Keep these static links separate from serialized read order.

## The generated wrapper reader, and `ListFormatter`

The generated wrapper reader conditionally forwards the same reader after a
one-byte fast-path header to an independently joined `ReadPackable<List<...>>`
usage/MethodSpec/type carrier. Its nested body follows relative slot zero through
`ReadPackable` to `ReadValue`, then `GetFormatter`, then the latter's MVAR type.
Each method edge independently joins one ordinal-zero parameter owned by its
preceding method; these are distinct records, not interchangeable MVAR identities.
The original concrete argument propagates only conditionally on context inflation.
This remains a provider/dispatch layer, not the list element reader or a selected
runtime formatter. A separately joined `ListFormatter` registration shares the
list element instantiation and supplies a static Deserialize code candidate.
Its fast path consumes a four-byte count; the remaining-length comparison is
unscaled, and each positive iteration delegates element decoding. The four-byte
element output slot is not a serialized-width proof. Counts below minus one
reach an error helper only on the new-output path; the existing-output path
clears its length and skips the nonpositive loop. Preserve that native distinction
without relaxing the maintained parser's negative-count rejection. Actual
provider selection and EOF are still open. The element dispatcher reloads the
actual object's class after initialization and takes its target/companion pair.
The non-specialized branch calls that target with object, reader, output slot
and the loaded companion; a distinct equal-target path delegates through class
RGCTX helpers. Incoming RCX is not a caller-selected slot. Neither branch proves
the live formatter identity or a fixed element byte width.

## Element dispatch, the `FF` peek, and the conversion carrier

The comparison target separately joins a shared adapter code candidate with
GameplayTag/Object arguments; do not replace the loaded companion's context
with that candidate's Object argument. Its selected helper peeks for `FF` and
only on a match consumes one byte before returning true and clearing the output.
The byte consumer's own boolean is different and is not forwarded. A nonmatch
does not directly advance this helper's cursor; ensure may still replace its
segment. The non-FF helper passes the same reader and an initialized writable
object-reference slot to formatter dispatch. A null result produces zero;
otherwise a separate interface lookup selects a target/companion pair and
tail-jumps with the result object, without forwarding the reader. Returned EAX
becomes the four-byte output. This is a converted result width, not serialized
consumption. Interface record offsets and slot arithmetic are directly pinned,
and the conversion carrier independently joins
`IMemoryPackDeSerializeWrapper<T0>`: its argument reciprocally belongs to adapter
ordinal zero, distinct from the formatter query's ordinal-one argument. The
adjacent MethodSpec uses that same instantiation and names `GetValue`; its
metadata slot is explicitly zero, matching the native request without assuming
declaration order. The native branch does not directly read that MethodSpec slot.
Target-pair bounds, live provider/conversion implementation, branch selection
and non-FF source consumption remain unresolved; follow the delegated formatter
context before interpreting this output or eliminating a terminal candidate.

## The provider takes a companion, not the reader

That provider takes a companion, not the reader: its first method-context slot
supplies a type-derived lookup key, and its second supplies the returned-object
check. A carrier table and a separate formatter cache participate; cache misses
reach conditional generation and writeback paths. This is direct state-dependent
control flow, not an observed cache entry or proof of the registered candidate's
selection. The class helper's identity return is conditional on an initialized
flag; its other branch delegates initialization. Do not collapse these branches
into unconditional pointer identity or infer serialization from provider names.

## Cursor state, and why none of it is an EOF test

Cold advance normally returns true, resets
the segment counter and accumulates the request; ensure can replace the cursor
with an existing or copied segment. Pointer deltas cannot certify source offsets.
The 24-byte descriptor has a conditional same-endpoint position-difference
length path. Independently token-joined constructors accept that descriptor or
a 16-byte pointer/length carrier and initialize total/remaining state and zero
consumption. Native getters identify consumed and total-minus-consumed roles;
reviewed caller paths return consumption but do not themselves compare EOF.
The token-joined object-return overload discards this count. Selected async
paths either discard it or forward it to another operation, not an EOF test.
These general serializer paths do not establish SkillData entry selection.
Exact Core.SkillData type arguments also join ResourceManager MethodSpecs;
their generic definition module slots are null. Separately enumerated
same-definition Object MethodSpecs supply shared-code candidates, not observed
sharing selection or invocation. Never confuse the same-named nested AI type
with the Core type, or substitute a shared body's arguments for live context.
A downstream native carrier wrapper forwards a reconstructed pointer/length
carrier to an inlined reader-state builder. Conditional dispatch uses that
state and an output slot; its returned consumption is discarded by the wrapper.
This corroborates the non-EOF boundary, not an authenticated file receipt.

## The formatter-check carrier's uninterpreted tail

identity remain unresolved. No observed final cursor or terminal uniqueness
follows from this conditional ABI.
Preserve the open formatter-check carrier window's uninterpreted tail: its bytes do not certify a
runtime allocation extent or select the returned formatter. Provider fallback
includes a lazy callback path whose population remains a separate evidence gap.

## Recovery acceleration

`scripts.game_data.native_union_atlas` validates reviewed Skill, Buff, and
LevelScript union contracts through one shared current-build PE/metadata
context and writes its generated index under `reports/`. Tags remain qualified
by dispatcher family, conflicting identities fail closed, and the atlas cannot
promote a field or invent a schema: setter types, nested layouts, and exact
cursors still come from the owning byte-pinned contract and reader. It replaces
repeated native discovery during frontier ranking, while publication continues
to require complete family and JsonData corpus gates. Dependency-scoped replay
remains developmental until mechanically derived transitive dependencies and
merged rows prove equivalent to a complete family sweep under mutation tests.
`scripts.game_data.dependency_snapshot` follows repo-local Python imports,
literal contract resources, transitive contract-declared JSON/Python
dependencies, and supported literal `spec_from_file_location` helper paths. It
fails closed on ambiguous basenames, conflicting assignments, missing or
escaping paths and unsupported declarations; runtime-computed paths and dynamic
contract discovery remain outside its static proof.

The Skill cache prototype separates content-addressed logical bytes from
classification entries, includes the cache tool and complete dependency
snapshot in its keys, and restores shared object aliases from a drift-checked
generic manifest. Warm, one-miss and all-miss replay reproduce the maintained
identity set and row semantics; warm replay is about sixteen times faster than
a full build. It is still not a publication path: new or changed logical bytes
require a fresh authenticated stream, cold replay retains the full parser cost,
and route admission has a global negative dependency because adding a formerly
unknown route can change old bounded rows. Broad package snapshots and complete
family sweeps therefore remain authoritative until a declarative route registry
and mutation tests cover every dependency class.

## Remaining gaps

- Continue SkillData from the maintained prefix through fields 1 through 42,
  prioritizing the nested ActionGroup/action-union readers that account for the
  opaque middle. Fields 43 through 47 and EOF are now selected by the accepted
  direct-reader cursor receipt, but this disjoint terminal proof cannot fill the
  earlier gap or make a whole record exact. Any further promotion must keep the
  exact receipt/corpus/native/verifier replay and current identity-set gates.
- `memorypack.buff_corpus` supplies the full current BuffData denominator from
  authenticated outer-ledger identities and decrypted stream bytes, using shared
  `memorypack.corpus_gate` provenance guards. It retains all filename-string
  anchors and reader-accepted EOF suffix candidates rather than inheriting the
  legacy reader's anchor selection. A unique accepted suffix does not establish
  its top-level ownership or certify internal opaque regions; whole-schema status
  remains false. Coverage, multiple-anchor counts and per-file diagnostics belong
  in `reports/animestudio/buffdata_current_latest.{json,md}`. All current root
  and reached damage-modifier condition actions now rejoin the named outer
  frame. The remaining Buff gap is nested semantics inside the structurally
  bounded anonymous event/action bodies, not an outer-frame cursor failure.
  The legacy prefix reader now rejects invalid anchor limits instead of clamping
  them and receives only bytes before the anchor, so count/string/scalar helpers
  cannot borrow suffix bytes. The corpus records its accepted prefix endpoint or
  unsupported-action stop and the remaining gap for every accepted suffix; this
  does not certify the legacy field labels or close that gap.
  `memorypack.buff_1b_corpus` rebuilds the authenticated census and checks exact
  root-continuation tag `0x1B` ranges against re-streamed logical bytes, then
  joins the record to the current exact-build selected action reader. This
  continuation profile does not prove root-field ownership. The
  SequenceActionData provider remains unresolved; the anonymous action reader
  does not close BuffData suffix ownership or whole-file EOF.

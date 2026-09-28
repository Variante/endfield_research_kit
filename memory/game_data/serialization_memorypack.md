# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and level
payloads. The first section is where each family's framing stands; the rest is the
IL2CPP evidence chain that identifies *which* formatter a payload resolves to --
static identity throughout, never observed execution.
Historical per-build counts in the evidence chain below describe the corpus
used when each proof was made; current denominators and states are in the
generated JsonData, SkillData, and BuffData corpus reports. Derived-plan EOF
closure remains separate from an independently named whole-file schema.

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
the four serialized TeleportValidation tables, DialogIdTable including its
two added row members, AetherEnergyLockConfigDataTable,
MatrixShockWaveBeatConfigTable, the compact MissionAreaTable, WorldChallenge SubGame table, compact WorldEntityRegistry,
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
`ScriptTaskExtraInfoTable` and `SubGameInstanceDataTable`) use a reviewed
declarative contract covering 813 schema nodes and 88 stored `$type`
identities. Only their explicitly named
authored-ID dictionaries are dynamic; unknown fields, shapes, scalar types or
discriminators fail closed. This establishes stored configuration structure,
while runtime selection and render consumption remain separate evidence.

`GameplayConfig/LevelMapMark.json` is a useful static map-marker source, but
its numeric root key must not be promoted to a scene id. The named JSON schema
closes the authored marker records: each carries a `basicData` template id,
instance id and position, and most carry a typed `visibilityData` body. The
reusable [`map_mark_relations.py`](../../scripts/game_data/map_mark_relations.py)
audit checks those bytes against the complete JsonData corpus receipt, reruns
the named schema readers, then joins each used template id to
`Table/MapMarkTempTable.json`. Every used template in the selected corpus has
one table row whose `markInfoId` agrees. The full template table also has
variant keys such as `_invalid` and `_social` whose `markInfoId` names a base
template, so a blanket table-key-equals-row-id rule is false. The audit keeps
those variants out of the authored-marker join.

The marker root keys separately meet `MapBriefInfoTable.subLevelTable` keys
and some `MapRegionTable` keys; the latter rows explicitly carry a `levelId`.
Neither relation supplies a scene for every marker group. A MapBrief map id
must not be rewritten as a level id: multiple region level ids occur under the
same MapBrief id. In the common `MapDetectorEntity` visibility variant, the
stored `entityId` equals `basicData.markInstId` across the selected rows; that
is an exact stored-value relation, not proof of when a marker appears or what
server state controls it.

There are two distinct individual-marker joins. The broader one requires an
exact `basicData.markInstId` key and equal decoded position in
`WorldEntityRegistry.worldEntityBriefInfos`, plus a matching used template.
This assigns authored marker data to that existing registry entity; it does
not assign an authored scene. The registry's numeric id bucket can plot the
entity on Map, but that bucket is not a `LevelMapMark` scene field. A changed
position or missing registry ID fails this annotation instead of being joined
by proximity or by the marker's numeric group key.

The narrower direct scene join uses `LevelShortIdTable` for individual markers.
`LevelShortIdTable` is keyed by `sceneName`, and its `ids` dictionaries store
logic IDs. The audit joins a marker's exact `basicData.markInstId` to one such
ID, requires that scene in `LevelBasicInfoTable`, and then requires the same
ID and exactly equal position in `WorldEntityRegistry.worldEntityBriefInfos`.
In the selected corpus, the qualifying markers are the campfire variant;
they are a subset of the registry-linked annotations on Map. This does
**not** assign the marker's whole numeric group, or any other registry-linked
marker, to that scene. `defaultVisible` is authored configuration, not observed
runtime visibility. The current join inventory and changing counts live in
`reports/game_data/map_mark_relations.json`.

The remaining ten textual JsonData rows also have named schemas rather than a
generic JSON classification. A reviewed 473-node contract closes the AI
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
`codecs/levelscript/action_map.py` reader. Its reviewed
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
consumes positive `globalModifier` lists through a structural four-member item
profile labelled `applyToReturnAtbGain`, `formulaItem`, `param`, and `type`.
The selected native root owns the list read and field store. A separate
selected formatter contract now authenticates its four-member header and all
four setter calls in that order, including the leading boolean. The earlier
three-setter inspection missed this generated wrapper; it is not evidence that
the first member is anonymous. The authenticated BuffData corpus now rejoins
every reached positive `globalModifier` list to this exact child cursor and
its source identity. This child proof alone does not close the parent; the
complete root reader must consume the same bytes through physical EOF. The root reader then
consumes raw-eight-byte `dispelConfig` and advances `duration`, the three
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
cursor as a fully named record. Field one, `addingCooldown`, now has a separately
gated child receipt. The selected root reader's `BlackboardDouble` source call
stores its result in the installed `BuffData.addingCooldown` field; the current
generated wrapper, checked separately against the selected build, orders the
child's `blackboardKey`, `useBlackboardKey`, and `value` setters. Missing or
stale optional DummyDll evidence leaves the native source-to-field claim intact
but suppresses these child labels. The selected child reader consumes a nullable
signed-length byte payload, one byte, and four raw value bytes. Source-hash-checked current
files rejoin the existing field endpoint with those named spans. The key's bytes,
boolean byte, and value bits remain raw; this does not prove string-decoder
parity, a live provider choice, blackboard lookup, or an evaluated cooldown.
The receipt removes only this field's anonymous member-ownership blocker.
The separate Buff action-receipt gate rechecks every completed corpus identity
against the matching exported logical bytes and selected native inputs before
using eight named action adapters. Physical tag `0x0050` selects the seven-member
`CompareFloat.Data` wrapper, `0x0092` the 19-member `CreateBuffActionData`,
`0x00A2` the 18-member `EffectActionData`, `0x00B4` the 13-member
`FinishBuffAdvanced`, `0x00C9` the eight-member `IfElseActionData`, and
`0x00EC` the 10-member `ModifyDynamicBlackboard.Data`, `0x011F` the
eight-member `RaiseTrainLevelEvent.Data`, and `0x0159` the seven-member
`SetSuperArmorAction.Data` wrapper.
Their generated member order and selected readers name each reached
wrapper field and close the exact reported action span, whether it occurs in
`abilityEventAction` or the supported root continuation. The `0x00A2` adapter
also checks each current generated field kind against the selected source read
kind, and checks its nested declared types against the source's five nested
call contexts. The `0x0050` adapter checks both blackboard-value member types
against the selected source's two direct call contexts. The `0x00EC` adapter
likewise checks its generated member kinds
against the source order and its target and blackboard-value types against
the source's direct nested contexts. The receipt inventory records these joins
under `reports/`.
The `0x0159` adapter checks the selected dispatcher, generated wrapper types,
complete action and nested-value readers, and the generic calls for the
priority, impact, super-armor, and target members. It rejoins the exact action
end in the current VFS-ledger-matched Buff corpus. A separate selected-native
receipt names the four ordered members of both direct blackboard children:
`blackboardKey`, `useBlackboardKey`, `value`, and `useCustomValue` within
`impactResistance` and `superArmorValue`. It replays each child against the
authenticated source bytes and exact parent action endpoint. String and flag
bytes remain raw, `TargetSettings` remains structural, and these stored reads
do not prove when super armor is applied. The field-five `buffEventAction`
frontier contains
many distinct action unions, so a single named wrapper does not close its
recursive schema obligation.
Nested input, selector, scalar, target, blackboard and effect-configuration
profiles remain structural where
their concrete providers or values are unproved; the gate does not remove a
recursive action-interior blocker or promote the enclosing BuffData schema.
The integrated `0x00C9` `IfElseAction` adapter has its own build gate in
`memorypack.buff_if_else_action_receipt`. Its selected dispatcher, complete
source reader and three identical `SequenceActionData` MethodSpec callsites
fix an eight-member read order; the generated wrapper setters name the
inherited action prefix, `alwaysNext`, `conditionAction`, `failActions`, and
`succeedActions`. For each authenticated current Buff corpus union span, the
adapter requires the selected candidate's certified child union ranges,
rechecks the three SequenceActionData headers, counts and terminal booleans,
and rejoins the exact outer action end. This names the parent fields while
leaving nested union bodies at the corpus's existing structural or derived
evidence tier. The standalone anonymous action reader stops at a reached
`0x0082` child, so it cannot independently replay every current `0x00C9`
record; the adapter fails closed when a certified child range is absent or
mismatched. Full selected-source counts and field spans live in
`reports/animestudio/buff_if_else_action_receipt_20260927.json`. Neither this
receipt nor the child ranges prove evaluated condition or runtime branch
selection, and whole BuffData schema remains open.
The integrated `0x011F` `RaiseTrainLevelEvent` adapter rechecks the selected
eight-member source reader, generated wrapper route, and three native
Blackboard call contexts before naming `isEnable`, `priorityLevel`,
`priorityOffset`, `serverActionIndex`, `eventKey`, `numericValue`,
`outputStringValue`, and `stringValue` in source read order. Its current-corpus
receipt authenticates the logical source and rejoins every reported physical
action span exactly. `eventKey` and `stringValue` use structurally framed
`BlackboardString` payloads; `numericValue` uses a structurally framed
`BlackboardDouble` payload. Their contents, lookup or evaluation, and runtime
event dispatch remain unproved. The adapter names this wrapper only; it does
not establish recursive action interiors or the enclosing BuffData schema.
The selected `BlackboardDouble` child reader now composes with four independently
gated action wrappers: `CreateBuffAction.count`,
`FinishBuffAdvanced.finishLayerCnt`, `ModifyDynamicBlackboard.value`, and
`RaiseTrainLevelEvent.numericValue`. The parent adapters reparse each reported
action and fix the exact field extent; the shared child receipt then names its
stored `blackboardKey`, `useBlackboardKey`, and `value` spans in generated setter
order. This closes the direct member-ownership gap for every currently reached
instance of these fields. Null provider and malformed length branches remain
explicit and fail closed. The key bytes, flag byte and four value bytes stay raw;
string decoding, live blackboard lookup, provider selection, evaluated values
and the rest of each action's nested interior remain open. The source-hash and
current-corpus replay is recorded under `reports/`, without whole BuffData
promotion.
The shared `TargetSettings` child receipt composes the selected thirteen-member
reader and generated setter plan with four independently gated parent actions:
`CreateBuffAction`, `EffectAction`, `FinishBuffAdvanced`, and
`ModifyDynamicBlackboard`. The direct stored order is `advancedDirection`,
`centerContextKey`, `centerToGround`, `centerType`,
`enableAdvancedDirection`, `ownerContextKey`, `selectorData`,
`selectorDirection`, `selectorOwner`, `target`, `targetContextKey`,
`targetGroupKey`, and `targetSource`. Each parent action is reparsed before its
target fields are admitted, and the child reader must end at that exact field
boundary. The current authenticated corpus closes every reached child span;
the reusable gate covers these targets and the `BlackboardDouble` fields above
in one source-hash and selected-native replay. `selectorData`'s inner bodies and
`advancedDirection`'s inner references retain nested structural evidence;
this direct-member receipt does not establish their recursive ownership, live
target selection, or a whole BuffData schema. Null and malformed target
branches fail closed.
The `advancedDirection` field has a second child receipt. Its selected
`DirectionSettings` source MethodSpec, reader window, generated setters and
derived plan name `clampToXZ`, `customSourceAndTarget`, `directionType`,
`invertDirection`, `source`, `sourceMountPoint`, `target`, and
`targetMountPoint` in direct stored order. It reparses each parent target and
requires the direction reader to end at the independently fixed field extent.
Every current reached direction child closes, and its two nested
`TargetSettings` references are null markers in the authenticated corpus.
Those nulls do not establish a future nonnull reference body or runtime
direction selection. The shared child gate records these direct spans while
retaining recursive action and whole-BuffData refusal.
The `selectorData` field also has a selected child receipt. Its source
MethodSpec and reader window, generated setters, and derived plan establish
three direct stored members in order: `finderData`, `postProcessorData`, and
`validatorData`. The child reader reparses its parent target, records the
finder union's selected tag/type and both list counts, and must end at the
parent's independently fixed selector field boundary. The maintained gate
replays every reached selector span against current logical source hashes and
the selected native build. The most-reached positive finder route,
`SelectorFinder` tag 2, has a separate selected-native child reader: its switch
branch loads the `CharacterTeamFinder.Data` wrapper, whose generated setters
are empty and whose `Deserialize` body consumes exactly one wrapper header
byte. A zero header ends the nonnull child; `FF` is a distinct null-wrapper
branch. Every reached tag-2 span in the authenticated current BuffData corpus
is the two-byte tag-plus-zero-header form and ends at the parent finder field's
fixed boundary. A second selected reader closes `OwnerSpawnedEntityFinder`
tag 13: its generated setter names the sole `spawnedObjectType` member as
`ObjectType`, and the native reader checks a one-member header, takes four
source bytes, and passes that result to the setter. Every current reached
tag-13 span ends after exactly that tag, header, and raw signed 32-bit member.
The shared child gate records both exact receipts against current source hashes
and parent extents. The selected validator switch and generated setter plans
also close three reached `SelectorValidator` routes at their independently
fixed one-entry list extents. Tags 5 (`ExcludeOwner`) and 9 (`MainCharacter`)
have zero serialized members and consume only their union tag and wrapper
header; their current reached wrappers are nonnull. Tag 11 (`TagValidator`)
has one direct `query` member declared as `GameplayTagQuery`. Its selected
reader consumes the wrapper header, invokes the typed query bridge, and stores
the result at the generated setter's destination offset. The existing
`GameplayTagQuery` reader frames the nested body as a scalar followed by a
counted scalar array, and each reached tag-11 list ends exactly at its parent
field extent. The current corpus reaches eight tag-5, two tag-9, and ten
tag-11 lists, all with source-hash and native-build receipts. Other positive
finder subtype bodies remain structural. These stored validators do not
establish a runtime predicate, recursive action ownership, or a whole
BuffData schema. Null, unknown-tag, malformed-count, and changed-build
branches fail closed.
The `CreateBuffAction.buffs` list has a separate selected-build child receipt.
The registered `CreateBuffActionInput` reader consumes a five-member wrapper:
inherited `assignBlackboard`, `assignItems`, and `buffId`, followed by
`buffIdKey` and `readIdFromBlackboard`. Its `assignItems` generic source
context resolves to `List<AssignPair>`, and the registered `AssignPair` reader
consumes `directValueType`, `inputValueKey`, `numericValue`, `stringValue`,
`targetKey`, and `useDirectValue` in generated setter order. The maintained
gate checks source calls, destination stores, runtime field offsets, and
complete reader windows against the selected native build, rechecks every
current BuffData logical source hash, reparses each
certified CreateBuffAction parent, and requires the nested list to end exactly
at the parent's `buffs` field boundary. Current reached input and assignment
wrappers, including positive assignment lists, all close with named direct
fields; the per-build reach counts stay in its generated report. String
members remain signed-length byte spans, and `numericValue` remains raw float
bits. This names stored child ownership without claiming decoded strings,
live assignment behavior, recursive ownership elsewhere, or whole BuffData.
The selected two-member `BuffIconDurationSourceSetting` reader now has a
direct-field receipt for `durationSourceType` and `timedMarkerId`. The validator
checks the selected reader window, generated setters, source read call, and
destination stores against runtime field offsets. A narrow BuffData root route
composes this with the existing CreateBuff input, BlackboardDouble,
TargetSettings, DirectionSettings, SelectorData, and selected null or zero-member
finder receipts. It accepts only a sole `CreateBuffAction` in
`abilityEventAction`, empty `buffEventAction`, and the already supported other
root children. It reads the original logical bytes through all thirty root
members, checks the stored `id` against the source stem, and reaches physical
EOF. The Buff corpus records the exact receipt per accepted row, and JsonData
checks the installed native build, source SHA, and entire receipt again before
classifying that row as schema decoded. Assignment execution, decoded string
parity, duration selection, and gameplay effects remain unobserved.
The separate `EffectAction.effectActionCfg` child receipt names its 85 direct
`EffectActionCfg` members. The generated wrapper's setter order agrees with the
selected reader's 85 source operations, and every operation has a checked
destination store at the corresponding runtime field offset; the vector members
also have their companion stores checked. The runtime type has two additional
fields, `forceGuardEffect` and `centerOffset`, which this serialized wrapper
does not read. The authenticated current BuffData gate reparses each selected
`EffectAction` and requires the child to end at the independently certified
parent field boundary. Current reached children all close. Their strings remain
signed-length byte spans, and the `TerrainEffectData` array is proved only on
its null or empty branch. The gate refuses positive arrays and keeps effect
execution and the whole BuffData schema unresolved; changing counts and source
identities belong in the generated corpus report.
The three `BlackboardVector3` members of this configuration have a separately
selected child proof. The generated vector wrapper names `x`, `y` and `z` in
the same order as three selected `BlackboardDouble` generic source reads, with
direct stores to the corresponding runtime fields. The independent scalar
reader names `blackboardKey`, `useBlackboardKey` and the raw four-byte `value`
inside each component, as well as the configuration's two direct scalar
blackboard children. The current VFS and source-hash gate reparses every
reached action and requires each nested child to close at the enclosing field
boundary. This closes the stored blackboard interiors on the reached branch;
it does not decode key strings, select a live blackboard provider, assign
coordinate meaning, prove effect execution, admit positive effect arrays, or
complete the enclosing BuffData record.
The selected `FinishBuffAdvanced.buffSettings` child is `BuffFindSettings`.
Its reader consumes `buffIdList`, `checkType`, and `tagQuery` in generated setter
order; the nested `GameplayTagQuery` reader stores `queryType` and `tags`.
Selected normal/null reader windows, source contexts, runtime field offsets,
and direct destination stores authenticate these five names. The current
BuffData gate rechecks every source and parent action, then closes every reached
`buffSettings` span at its independently fixed boundary, including positive
string lists and positive packed tag arrays. The string list's selected generic
type and signed-length byte grammar do not identify a live
`ListFormatter<string>` provider, so decoded text and provider parity remain
conditional. Tag values are raw stored IDs; the runtime buff finder and tag
predicate, as well as whole BuffData, remain unresolved.
Field seven, `dispelConfig`, has an independent selected-build child receipt.
The root reader checks and copies eight source bytes directly into the installed
`BuffData.dispelConfig` value. Current metadata places `canBeDispelled` at byte
zero and the signed `DispelLevel` value at byte four; the three intervening
bytes are preserved as padding. The validator checks the generated setter,
source advance, destination store, field offsets and value size before the
corpus attaches named spans. Missing or changed native inputs retain the raw
eight bytes and the naming blocker. These stored values do not prove runtime
dispel decisions or enum effects, and the reader does not constrain padding or
enum values to current corpus observations.
The selected root reader also passes `BuffStackingSettings` to its child reader
and stores the result in `BuffData.stackingSettings`. Its twelve generated
setters establish the stored member order. The `stackingKey` string reader
consumes a signed four-byte length before distinguishing null, empty and
nonempty values; the following `stackingType` occupies two bytes before two
one-byte flags. The earlier compact reader left an empty key's length in place
and consumed just one byte of `stackingType`. Its suffix could still appear to
reach EOF by assigning those bytes to later fields, so EOF alone was not a
field-ownership proof. The corrected child receipt rejoins the next field in
source-hash-checked current files, including positive `stackEffects` with
separately opaque action interiors. A missing or changed selected native build
withholds the named child and raw-tag joins.
The next root source call reads `tagsAfterTriggerExtendBuffAction` as a signed
count followed by packed four-byte `GameplayTag` values, then stores that
array in the named root field. It is a raw stored ID array; the apparent
member-prefix/tag-name variants of the earlier suffix reader were shifted
interpretations. The current exported files rejoin the following timeline and
trigger tail at physical EOF under this correction. A separate selected native
join identifies the next root call as `ReadPackable<List<TimelineActionData>>`,
stores its result in `BuffData.timelineActions`, and then reads and stores
`triggerInterval` through a different `BlackboardDouble` context. The
source-hash-checked empty timeline branch consumes exactly its four-byte zero
count before that exact trigger tail. In the selected current corpus, every
remaining suffix-fallback first blocker was on this empty branch, so the
conditional child receipt removes that blocker only when both the native gate
and cursor joins validate. Positive timeline bodies still use a structural
endpoint and retain their fallback-ownership blocker;
positive `stackEffects` interiors and anonymous actions remain separate naming
obligations. Consequently, a file with zero unconsumed composed bytes is still
not a whole named schema unless those interiors have direct ownership evidence.

The root `blackboard` list now has a selected native `List<Blackboard.DataPair>`
argument and generated four-member child setter order: `isDynamic`, `key`,
raw double `valueDouble`, and `valueStr`. The current BuffData gate decodes
every reached list against its exact field endpoint, including positive
children, with a source fingerprint for the reader and native contract.
This closes the list's stored child layout at those cursors; it does not by
itself authenticate every other recursive root field or promote a whole file.

The selected-build `buff_root_no_positive_native.json` contract joins all 30
root source reads, generic contexts, generated setters, and destination
stores to the installed native body. Its forward reader admits a unique
outer-frame cohort with independently validated child layouts: an empty-list
branch, a narrow positive `blackboard` DataPair plus `globalModifier` branch,
one positive `damageModifier` branch whose condition and processor children
are separately selected and checked, and a narrow sole `CreateBuffAction`
branch with selected nested child receipts. Other positive recursive branches remain
refused. Each admitted file
is reread from byte zero through 30 contiguous named fields, checks the stored
`id` against its source stem, and ends at physical EOF. The BuffData corpus
first authenticates its stream with the VFS ledger length and MD5; it records
each logical SHA for the later JsonData registry, which revalidates native
inputs and replays the exported bytes against the entire receipt before
classifying that row as schema decoded. The current corpus report holds the
selected-file count and byte total. The earlier positive branch exercises
finite DataPair values and a one-element GlobalModifier list. The damage
branch admits one modifier with an empty `SequenceActionData` condition, one
selected tag-five `DamageScaleProcessor`, and a four-byte `enableSide` member.
Its forward reader continues on the original logical bytes through every
later root member and physical EOF. Nonzero condition actions, other
processors, positive heal and other action lists, stack effects, and timeline
interiors retain their own named-ownership blockers. This is exact
stored layout for the selected rows; live formatter-provider choice and
gameplay behavior remain open.

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
born-behavior boundary. The enemy row's `preWarnEffectFixedRotation` uses a
16-byte `Optional<Vector3>` value (presence byte, zero padding, three floats);
the previous four-float interpretation reached the same cursor but turned the
presence byte into a tiny false axis. Its high-coverage route profile then
closes generated
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
in generated order. The current JsonData corpus classifies every selected
SpawnerConfig file as an exact named schema. The older unique-tail fallback
remains for a changed future route profile; failure of both readers preserves
the exact enemy-library prefix as bounded partial evidence.
CharInteractPerform now closes the complete 27-member owner through physical
EOF for every current file. The reviewed
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
These close their reached positive task maps; an unseen tag or changed member
count still fails before the task entry is promoted.

A further selected-native GameCondition batch closes positive task maps reached
after complete action maps: `CheckMonsterSpawnerCompleteState`,
`CheckSnapshotIdentifySuccess`, `CheckSNSDialogComplete`, and
`Conditions.OnEnterMainHud`. Their selected dispatcher entries, generated
member lists, complete reader and formatter bodies, and ordered field reads
authenticate the stored layouts. The first condition carries a level string and
`Param<SpawnerPtr>`; that pointer stores one unsigned 64-bit id. The snapshot
and SNS conditions each carry one string parameter; the HUD condition has only
the four shared condition fields. Current exported cursor spans are joined to
the JsonData ledger. The enclosing sequential task parser promotes a file only
when every condition, task entry, and final trigger-volume map closes at
physical EOF. Other positive maps remain partial at their first unsupported
condition; these stored conditions do not establish runtime evaluation or
mission ownership.

The followon selected-native task-map set closes the reached
`CheckMapVar`, `CheckAliveCharNumInCurTeam`, `CheckRemoteCommFinish`,
`CheckInteractiveIsActivated`, `CompareInteractivePropertyBool`,
`CheckUnlockTech`, `CheckLsmCompleted`, `Conditions.CheckIsInFactoryMode`,
`Conditions.CheckIsItemInQuickBar`, and `InMainHud` conditions. Their
generated fields and ordered native reads distinguish scalar comparison
parameters, signed map values, entity pointers, LSM and LevelScript pointers,
and null or authored string parameters. Each reached condition has an exact
source cursor joined to the current JsonData ledger. The sequential task-map
reader still promotes only complete owners at physical EOF.

`CheckInteractiveSubmitSuccess` has a short hot reader followed by a chained
native continuation. The continuation checks the seven-member payload and
reads four inherited fields, then `Param<EntityPtr>` for `entityId`,
`Param<bool>` for `expectedSubmitSuccess`, and `Param<string>` for `levelId`.
Each read reaches its generated setter in order; the generic Param contexts
and complete chained reader and forwarding formatter are authenticated. The
current source spans parse as three complete conditions, and the enclosing
sequential LevelScript reader reaches physical EOF. This closes the remaining
reached positive task-map condition route, while live submission success and
condition evaluation remain unobserved.

`CheckTyphoeaArcheryUnitsComplete` stores the shared four condition members,
then `Param<string>` `levelId`, `Param<List<LsmPtr>>` `lsm`, and
`Param<LevelScriptPtr>` `scriptId`. Its selected GameCondition branch,
complete reader and forwarding formatter, ordered read/setter calls, and
nested MethodSpec context resolve the list element to the one-member
`LsmPtr`. Authenticated source spans contain a positive LSM list and a
current-script pointer. The sequential task-map reader closes the reached
archery dungeon owners at physical EOF. These stored values establish neither
runtime condition evaluation nor completion of the archery challenge.

The generated-order LevelScript lane also starts after a null `actionMap`.
The outer wrapper's first member is a nullable reference, and MemoryPack's
one-byte `0xff` null marker closes it exactly, so `activeShapeList` begins at
physical offset 2. The reader advances from that boundary through the same
owner collections, terminal task map, and `triggerVolumes` EOF gate; it does
not use the independently found terminal suffix. A selected positive
Encounter `introPart.operaSegments` route now closes through the generated
`OperaSegment`, `ParamKeyValue`, `ParamValue`, and `ParamValueAtom` wrappers.
The current source spans carry one segment, one keyed parameter, and one atom;
the nested cursor rejoins the sequential owner, which reaches physical EOF.
Other positive shapes remain fail-closed, and these stored values do not
establish runtime encounter behavior.

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
boundaries. Its populated `ParamListForGraph` branch now reuses the exact
`List<ParamKeyValue>` codec and requires the selected native owner contract
before reading a positive count. It consumes each nested `ParamValue` and atom
at the physical cursor, then hands the resulting action-map endpoint to the
same generated-order owner reader. The current source-authenticated LevelScript
replay promotes only files that reach EOF, with no earlier exact file regressing;
current totals are in the JsonData and focused replay reports. Non-null
target-script values remain unsupported. Scanning UID-shaped bytes is not an
acceptable substitute for sequential record extents.

That selected-build action cursor now also advances `StartDialogAction`
(`0x04b0`, seven concrete members), `Split` (`0x04a7`, one integer list),
`SwitchInt` (`0x04cf`, two integer lists, a default ID and integer parameter),
`PlayRadio` (`0x036e`, five parameters), and `IfElseAction` (`0x0109`, a
condition and two branch IDs). `CheckBoolIfTrue` (`0x0053`) is included because
it is the common terminal action after current dialog and radio records. Exact
map promotion requires every declared action, getter and header to use a
supported layout, followed by an exact `ParamListForGraph` and owner cursor.
`SwitchInt` and
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
to named exact schemas with no regression; other reached maps historically
stopped at a different reviewed boundary or a positive `ParamListForGraph`
count. The current shared list decoder closes that latter boundary when its
selected native gate validates and every later owner member reaches EOF. The same
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
are reviewed independently; same-numbered rows in another dispatcher family
cannot select these layouts.

`LevelCameraLookAt` now advances its 31 concrete parameters after the inherited
action envelope. The LevelScript-owned `camera_look_at.py` reader loads the
reviewed `camera_look_at_layout.json` contract and gates on both selected
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

The LevelScript sequence reader now reuses the shared reviewed
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

Positive LevelScript `npcs` dictionaries are `uint -> NpcRuntimeProxyData`,
using the same flattened 14 + 77 + 27 member reader as placed LevelData and
AtmosphericNpc rows. The dictionary reader validates each key and advances
each value at its real cursor; an unsupported nested NPC value leaves the
whole dictionary unread rather than guessing the next top-level offset.
Current source-hash-joined focused replays reach the final LevelScript tail
and physical EOF with the stored `scriptId` matching the source identity.
These are authored NPC placements, not proof of spawning at runtime.

Positive LevelScript `modules` dictionaries have the same exact sequential
handoff for the reviewed concrete wrappers. The selected native
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
selected positive opera arrays have one segment with one keyed parameter and
one value atom. A separate selected-native contract checks all four nested
wrapper layouts and complete reader windows before the positive branch runs;
authenticated source spans then close their enclosing LevelScript files at
physical EOF. Other positive array shapes remain fail-closed. The stored
opera type, key and value do not establish when or whether an encounter
operation executes.

The selected dispatcher also identifies `EncounterDataV2` at tag `0x0003`
with the same 16-member stored shape as `EncounterData`, and
`MatrixRepairControllerData` at tag `0x0009` with a center `EntityPtr` and a
list of element pointers. The generated wrapper order supports the
`TianshizhuangData` tag `0x000f` LangKey, pointer, transform and vector-list
fields, and `WaterAbsorbedImpactData` tag `0x0012` curve, UI and pointer-list
fields. Tag `0x0010` is `TyphoeaArcheryUnitAdvancedData`; its positive
eight-member obstacle records carry stage and time lists, a destructible flag,
model strings, spawn transform and spline ID, followed by shooting-unit and
stage-type lists. The codec admits each route only when the current native
union tag and member count agree with its reviewed body. Source-hash-joined
replays advance every current module-first-stop dictionary through its exact
module span. Whole-file results require the subsequent sequential cursor to
reach physical EOF; mixed archery files currently stop later at positive
`taskMap.entries`. These stored module settings do not establish when or
whether the client activates them at runtime.

The independent terminal fallback remains for files outside that sequential
profile. Its final five members are `scriptId`, `startShapeList`, `startType`,
`taskMap`, and `triggerVolumes`; it accepts the range only when one
filename-independent byte-grammar candidate closes at physical EOF. Because
the preceding members are opaque there, that result remains a named partial
schema. Other nonempty-action-map shapes retain their weaker exact prefixes;
changing coverage belongs in the corpus report.

When an exact sequential owner reaches a positive `taskMap` but one entry
fails, its partial result and authenticated corpus file row retain the first
bounded condition diagnostic,
including the task key and checked union tag when readable. This makes the
next reader frontier identifiable without promoting any later bytes.

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
`preWrapMode`. The reviewed identities,
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
`scripts/game_data/contracts/animation_material_publication.json`.
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
to `InteractiveCheckBool`. A reviewed native contract validates that switch
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

The current selected-build ActionBase dispatcher also binds tag `0x0002`,
member count nine, to
`ActionForSubGame.ManuallySyncMainTaskTrackingStage`. The generated wrapper
has one concrete member after the eight common action fields:
`subGameId` as `Param<string>`. Its reviewed row consumes the parameter at
the exact action cursor, including the observed null constant and its binding
tail. In the source-hash-authenticated current LevelScriptData corpus, this
advances every file whose first stop was that union to a later declared
action or getter boundary, with no regression or whole-file promotion from
this isolated route. Most of that cohort next stops at an
unsupported PureGetter union; its member count and apparent position do not
authorize a guessed child layout. Native switch identity, generated setter
order, and observed sequential extents establish stored fields only, not
SubGame task-tracking behavior at runtime.

The next reached PureGetter boundary is `SpawnerGetSpawnedEntityList` at the
selected getter dispatcher tag `0x041f`, member count eight. Its generated
wrapper adds one `Param<SpawnerPtr>` after `NodeBase`. The independently
reviewed SpawnerPtr parameter contract and selected generated raw layout
establish a four-member parameter whose constant is one unmanaged UInt64 ID;
the ordinary binding tail follows it. In the source-authenticated files
whose first stop was this getter after the SubGame action, the stored constant
ID is zero and the binding instead names source `200` properties `wave01`,
`wave02`, or `wave03`. Those exact getter cursors now advance to independently
unsupported getter or header unions. Elsewhere the same reviewed shape lets
whole LevelScript files reach physical EOF with nonzero stored SpawnerPtr
constants. The full-family replay shows no regression; its current totals and
the distinct next-stop counts remain in the generated receipts. Neither form
establishes that a spawned entity list is evaluated or which runtime spawner
instance ultimately supplies it.

The leading current LevelScript first stop after those routes was
`PlayFmvAction`. Its selected ActionBase dispatcher entry and generated
14-member wrapper add six fields after the common action envelope, in this
order: `moviePath` as `Param<string>`, `param` as
`Param<CommonMaskBlendData>`, `shouldWaitForFinish` as `Param<bool>`,
`afterMask` as another mask parameter, then `beforeMask` and
`overrideAfterMaskConfig` as boolean parameters. The names do not determine
the wire types: the generated setters establish that `beforeMask` is boolean.
The reviewed nested mask codec accepts the observed null or empty curve and
strict audio and mask values, then consumes each parameter's own binding tail.
All 19 source-authenticated first-stop files advance through the action at
their physical cursors; 17 now close their entire owner at EOF, while the
other two stop at distinct unsupported getter and action unions. The complete
LevelScript replay has no regression. A stored FMV path and masks do not prove
that playback occurs or establish its runtime order.

The next ActionBase first stop is `EntityShowList`, whose selected dispatcher
and generated wrapper put `allowMissing` as `Param<bool>` before
`entityListPtr` as `Param<List<EntityPtr>>` after the common action fields.
The already reviewed list codec consumes a null count or each declared
three-member `EntityPtr` value, then the enclosing parameter binding tail.
Current source-authenticated files exercise both null and populated lists; the
populated lists contain one or three exact pointer records. Every reached
first-stop action advances at its physical cursor, and some owners now close
at EOF; the rest stop at later independent action or header unions. The
selected route proves stored pointer lists and the allow-missing flag, not
entity visibility, resolved entity identity, or action execution. Current
whole-file totals and subsequent stop frequencies live in the generated
LevelScript replay and cursor receipts.

The selected `ListAddValueEntityPtr` ActionBase wrapper carries the common
action fields followed by `Param<List<EntityPtr>>` and `Param<EntityPtr>`.
Its complete native reader and forwarding formatter authenticate the ordered
reads and setters, including a generic list context whose element is
`EntityPtr`. The reviewed cursor reuses the established list and pointer
grammar and closes ledger-joined source spans. The reached lists in this
source set are null and bound to paths; a populated list for this action has
not been observed. Whole-owner replay reaches EOF in one file and encounters
independent earlier or later unions in the others. These stored bindings do
not establish a runtime list mutation or resolved entity identity.

The next source-authenticated first-stop cohort reaches
`SetEntityEulerAnglesLookAt` at ActionBase tag `0x0408`. Its selected native
dispatcher binds the 11-member generated wrapper. After the eight common
action fields, the generated setters read `lookatTarget` as
`Param<EntityPtr>`, `target` as a second `Param<EntityPtr>`, and `yawOnly` as
`Param<bool>`. The two pointer parameters each retain the nested
three-member logic-ID/slot-ID/use-slot-ID value and their own binding tail;
the boolean parameter has its own tail too. Exact sequential cursors advance
every reached first-stop action. Six of those owners now close at physical
EOF; the rest stop at separately unsupported action or getter unions. The
full-family source-hash-authenticated replay has no regression. These stored
targets and flags do not establish runtime orientation or action execution.

Three more first-refusal unions now use reviewed rows in
`codecs/levelscript/action_map_layouts.json`. The selected PureGetter
dispatcher resolves `InteractiveGetSavePropertyInt` to the generated wrapper
whose two members after `NodeBase` are `entity` as `Param<EntityPtr>` and
`key` as `Param<string>`. The selected ActionBase dispatcher resolves
`EndCustomAbility` to a wrapper with no own members after the eight common
action fields. It also resolves `PlayDialogAndHideSceneObjectAction` through
the inherited `StartCinematicAndHideSceneObject` fields: interactive and
scene-object hide lists, two override booleans, then after/before masks, with
its own `dialogId` string parameter last. The native formatter branches,
registered types, and inherited generated setter order establish these
stored layouts; the shared reviewed codec advances each reached physical
cursor. A complete current-VFS and export-hash replay promotes only owners
that reach named physical EOF, with no regression. The same replay checks
every `LevelScriptTemplateData` file; these three routes do not yet close
its remaining partial files. Current counts and exact source-span receipts
are in the generated LevelScript route replay. Stored getter keys, ability
ends, and dialog requests do not prove evaluation, action execution, or
runtime order.

The next ranked first-stop batch authenticates `LevelEvent_OnBattleSignal`,
`EnterFocusMode`, and `LevelEvent_OnGuideGroupComplete` through their separate
ActionHeader and ActionBase native dispatcher branches. The two headers inherit
the common event fields and append, respectively, a float output plus signal
string and a guide string output plus guide filter string. `EnterFocusMode`
adds one instance-ID string parameter after the common action fields. The
selected registered wrapper, inherited setter order, member count, and exact
parameter cursors agree for each route. A complete current-source replay
advances every file stopped at one of these unions; only owners that rejoin
their terminal fields and physical EOF become named exact. The same replay
checks the Template family, whose remaining partial files still stop at other
unions. Stored battle signals, guide filters, and focus-mode IDs do not prove
runtime dispatch or execution. The ranked projection and per-file receipts
stay in generated reports.

The next five source-authenticated first stops are `ForceShowDecorationWithHandle`,
`SetSquadLeaderBySlot`, `EnterFocusModeFadeOut`, `ScriptEvent_OnScriptStart`,
and `GetterVector3`. The selected ActionBase, ActionHeader, and PureGetter
formatter switches bind each compact tag to its registered wrapper, and the
generated inherited setters fix member order. The first action adds
`targetDynamicEntity` as `Param<ulong>` and `visible` as `Param<bool>`; the
second adds `slot` as `Param<int>`. `EnterFocusModeFadeOut` has only the eight
common action members. `OnScriptStart` inherits the common event fields and
then reads `targetScript` as `Param<LevelScriptPtr>` and `triggerTarget` as an
integer. `GetterVector3` adds `value` as `Param<Vector3>` to the common getter.
The reviewed codec consumes the exact current source spans without searching
for another node boundary. In the current VFS/structured-export hash-joined
replay, the five routes together advance every one of their 56 first-stop
files and promote 42 whole LevelScriptData owners to named physical EOF,
raising exact closure to 3,944 of 5,091 with zero regression. The 25 partial
LevelScriptTemplateData files remain partial at other boundaries. The
generated replay retains each source hash, union span hash, and next stop;
stored members do not prove action or getter execution.

The next selected ActionBase first stop is `RepeatAction`. Its reviewed
dispatcher row binds the generated wrapper and the common action fields,
followed by `doID` as an integer, `repeatIndex` as `ParamOutput<int>`, and
`repeatTimes` as `Param<int>`. The shared reader consumes those members at the
actual source cursor and rejoins either a later independently unsupported
union or the owner's physical EOF. Malformed member counts and truncated
parameters stop before promotion. Source-authenticated focused replay and the
native row validator agree; current coverage and exact promoted owners belong
in the generated LevelScript report. Stored repeat settings do not establish
runtime loop execution.

The current reviewed LevelScript batch admits `ScriptEvent_OnScriptEnd`,
`NpcProxyGetter`, `BoolGetterOr`, `EntityHide`, and `ResetSummonTeamAI` at their
current first-stop cursors. Selected union branches establish wrapper identity;
the generated native `Deserialize` bodies establish the member counts and
ordered field reads. `OnScriptEnd` adds a `ScriptEndReason` parameter whose
underlying value is a signed integer, while `NpcProxyGetter` adds a string
parameter. `BoolGetterOr` adds two boolean parameters, `EntityHide` adds an
allow-missing boolean and entity pointer, and `ResetSummonTeamAI` has only the
inherited action fields. The shared reviewed reader consumes these records at
their actual cursors. Current source-hash-checked focused replay takes some
owners to physical EOF and exposes a distinct later stop in the others. The
full authenticated JsonData sweep publishes only the physical-EOF owners as
whole named schemas; per-file receipts and changing totals remain in generated
output. These stored records do not establish evaluation, action execution,
or event causality.

A following selected-native batch admits `LevelEvent_OnSpawnerComplete`,
`GetMainLevelCameraController`, `EntityAttachToParent`, and
`SetNpcAtmosphericClusterVisible`. The spawner header adds a spawner pointer
filter and a separately framed spawner output after the inherited event fields;
the camera getter has only its inherited node fields. Entity attachment adds
child and parent entity pointers, a follow-node name, local position and
rotation, and a boolean offset flag. The cluster action adds a cluster string
and visibility boolean. Each native union branch resolves the generated
wrapper, and the selected `Deserialize` body checks its member count and
reads the declared fields in order. Source-hash-checked focused replay joins
these records at their actual cursors, reaching physical EOF for some owners
and leaving explicit later stops for others. The full authenticated JsonData
gate publishes only the owners that reach physical EOF as whole named schemas.
The counts and source receipts remain in generated output; the stored values
do not prove gameplay effects.

The selected `DeadZoneDoRepatriate` ActionBase route adds a ninth member,
`damageRatioPerFall` as `Param<float>`, after the eight inherited action
fields. The native dispatcher, generated read/setter order, and `System.Single`
generic context are authenticated against the installed build. Its reviewed
layout also carries a source-hash cursor record; the native route validator
checks that the layout's fields and cursor evidence still agree with the
selected route. Focused current-source replay consumes the action at its
declared cursor, while the authenticated JsonData gate promotes only owners
that then reach physical EOF. The parameter is a stored setting, not evidence
that repatriation ran or damage was applied.

The two reached snapshot event headers, `LevelEvent_OnSnapShotEnter` and
`LevelEvent_OnSnapShotLeave`, have the same stored 14-member shape. Their
generated wrappers add no own fields: the selected `ActionHeader` switch
resolves each registered wrapper directly, and each complete native
`Deserialize` body reads the inherited `NodeBase` and event-header members in
order, ending with `Param<bool>` validation. The checked generic context and
inherited setter identify that last member independently of its source bytes.
The reviewed layout admits these routes only while their dedicated selected
native validator confirms the switch, full method windows, ordered helper
calls and current build. Ledger-joined source replay consumes both records at
their declared cursors. Some owners close at physical EOF; others advance to
the distinct `FinishSceneEffect` ActionBase union or remain partial for an
independent owner boundary. The generated replay holds exact source and span
receipts. Snapshot entry or exit bytes alone do not prove the event ran.

The selected `FinishSceneEffect` ActionBase branch has ten stored members:
the eight inherited action fields, `effectSaveId` as `Param<int>`, and
`forceImm` as `Param<bool>`. Its separate current-build contract checks the
switch target and registered wrapper, the complete source and formatter
bodies, ten ordered native reads, two own setters, and both generic parameter
contexts. Source-hash and ledger-joined focused replay consumes the reached
records at their declared cursors. The reviewed reader admits this route only
while that native validator passes; the full corpus gate decides whole-file
status at physical EOF. Some owners continue to later ActionBase or getter
unions. The stored effect settings do not establish that the effect executed.

The selected `GetterInt` PureGetter branch has no own serialized fields; it
inherits eight members from `Getter<int>`, ending with `value` as
`Param<int>`. Its formatter tail jump, complete source body including chained
fragments, eight native reads, inherited setter and generic parameter context
are authenticated on the current build. A source-hash and JsonData-ledger
receipt places the wide-tagged record at its exact cursor. The reviewed
reader keeps this getter gated on that native route, and the full JsonData
corpus decides whole-owner status at physical EOF. Stored getter bytes do not
establish that it was evaluated or which gameplay value it returned.

The selected `CompareMissionState` and `EntityCompare` PureGetter branches
each inherit seven node fields and add `comparer`, `valueA`, and `valueB` as
`Param<T>` members. Their comparer and mission-state enums have four-byte
storage; the entity values contain three-member `EntityPtr` records with
independent source/path tails, including authored property references. The
current-build contract authenticates both dispatcher branches, complete
chained readers and forwarding formatters, ordered reads and setters, and all
three generic parameter contexts for each branch. Current JsonData source
hashes and ledger joins place the reached getters at exact cursors, and the
reviewed reader consumes those spans only while native validation passes.
This proves stored comparisons, not their runtime inputs, evaluation, or
result.

The selected `GetMissionState` PureGetter branch inherits seven node fields
and adds `missionId` as `Param<string>`. Its current-build contract checks the
dispatcher and registered wrapper, complete chained reader and forwarding
formatter bodies, eight ordered native reads and setters, and the string
parameter's generic reader context. Source hashes joined through the current
JsonData summary and per-file ledger place the reached getters at exact
cursors; reviewed ActionMap replay consumes their spans while the native gate
passes. Whole-file status still depends on the corpus EOF gate. The stored
mission ID does not prove when the getter evaluates or what state it returns.

The selected `NpcProxyPatrolStop` ActionBase branch adds `levelId` and
`targetProxy`, both `Param<string>`, after the eight inherited action fields.
The reviewed current-build route checks the dispatcher, complete reader and
formatter bodies, ten ordered reads, two setters and both `System.String`
generic contexts. Source hashes and the JsonData ledger place reached records
at exact cursors. The reader admits the branch only while that native route
validates, and later union stops remain partial until separately reviewed.
The stored patrol targets do not prove that a proxy stopped at runtime.

The selected `StartLevelSeqLoopSegment` ActionBase branch adds four stored
members after the inherited action fields: two `Param<string>` values,
`segmentList` as `Param<List<string>>`, and `setMultipleSegment` as
`Param<bool>`. Its selected native contract checks the switch jump and
registered wrapper, full reader and formatter extents, twelve ordered reads,
four setters, and the nested generic contexts down to the list's string
element. Source-hash and JsonData-ledger receipts locate the reached wide-tag
records, and reviewed cursor replay consumes each span exactly. Later unions
and owner EOF still require independent closure. Stored loop settings do not
show that a sequence ran.

The selected `EntityEvent.OnBeingScanned` ActionHeader branch has 18 inherited
stored members and no own wrapper fields. Its final four parameters are
`Param<bool>`, `Param<EntityPtr>`, `Param<List<EntityPtr>>`, and
`ParamOutput<EntityPtr>`, followed by a stored trigger-target enum. The
current-build validator authenticates the selected switch and registered
wrapper, complete reader and formatter bodies, all 18 ordered reads and
setters, and the four nested generic contexts. Seven source-hash and
JsonData-ledger receipts rejoin exact event-header cursors; the reviewed
reader admits this route only while the validator passes. The full corpus
gate decides whether each owner reaches physical EOF. The serialized event
does not establish that a scan fired or which runtime system owned it.

The selected `LevelEvent.OnSquadInFightChanged` ActionHeader branch inherits
the common 14 stored header members and adds `inFight` as
`ParamOutput<bool>`. Its current-build contract authenticates the direct
switch branch, registered wrapper, complete generated reader including owned
fragments, forwarding formatter, every ordered read and setter, and both
generic parameter contexts. The reached output paths are stored local property
references; source hashes, the JsonData summary and ledger, and exact cursor
replay place them at current header spans. The reviewed ActionMap reader
requires that native validation. Some enclosing files close at physical EOF;
others still stop at later unions. Neither a stored output path nor the event
name proves the live squad combat state or that the event fired.

The selected `LevelEvent.OnSquadAllMemberDie` ActionHeader branch contains only
the common 14 inherited header members. Its native contract authenticates the
direct switch branch and registered wrapper, complete generated reader and
formatter, ordered reads and setters, and the `Param<bool>` generic context.
Current source hashes join the JsonData ledger, and the reviewed cursor replays
the reached event spans exactly. A derived root independently reached script ID
and physical EOF for those sources; the authenticated whole-corpus gate decides
their final owner status. The stored event name does not prove a runtime squad
death or event firing.

The selected `LevelEvent.OnMissionStateChanged` ActionHeader branch has the
common inherited header plus stored filters for mission ID, new state, and
succeed ID, and four `ParamOutput` references for the observed IDs and states.
Its current-build contract checks the direct switch branch, registered
wrapper, complete generated reader with owned fragments and formatter, all
ordered reads and setters, and eight nested parameter contexts. The filter
state is a finite signed-integer enum authenticated against the native
declaration. Current source hashes join to the JsonData ledger, and reviewed
cursor replay consumes each event span exactly. A derived root reaches script
ID and physical EOF in the reached files; the full reviewed corpus gate alone
promotes an enclosing owner to exact. These stored filters and output paths do
not establish a runtime mission transition or event firing.

The selected `AddTrackingPointForEntity` ActionBase branch stores six
parameters after the eight inherited action members: an entity pointer,
guiding-area float, level ID, tracking-point style, tracking-point ID, and
tracking type. Its current-build contract authenticates the selected switch
branch and wrapper, complete generated reader and formatter, all ordered
reads and setters, six generic parameter contexts, and both signed-integer
enum declarations with finite members. Source hashes join to the current
JsonData ledger, and reviewed cursor replay consumes the reached action spans
exactly. A derived root replay corroborates script ID and physical EOF, but
whole-owner exactness still depends on the reviewed sequential reader clearing
later unions and its corpus gate. Stored tracking-point arguments do not prove
that a marker appeared in a live game.

The selected `AddTrackingPoint` ActionBase branch stores a building-instance
key, an unsigned entity logic ID, guiding area, level ID, position, tracking
style, tracking-point ID, and tracking type after the common action fields.
Its native contract authenticates the selected switch branch, complete
fragmented reader and forwarding formatter, ordered setters, eight typed
parameter contexts, and both tracking enums' signed 32-bit storage. Current
ledger-joined action spans include positive and null entity IDs and concrete
positions. The reviewed whole-owner reader closes some enclosing scripts at
physical EOF and reaches later unsupported unions in others. These stored
arguments do not establish that a tracking marker appeared at runtime.

The selected `SetForbidMapTeleport` ActionBase stores `allowGetUnstuckPoint`
and `forbid` as Boolean parameters after the common action fields. Its native
contract authenticates the switch branch, complete fragmented reader and
forwarding formatter, ordered setters, and both typed parameter contexts.
Ledger-joined cursors consume the reached action spans exactly. The stored
flags do not show whether map teleport was restricted during live play.

The selected `ResumeSpawner` ActionBase stores a pause key and spawner
pointer as typed parameters after the common action fields. Its native
contract authenticates the selected dispatcher branch, complete reader and
forwarding formatter, ordered setters, and both generic parameter contexts.
Ledger-joined source cursors include concrete spawner IDs and consume each
reached action span exactly. The enclosing files continue to later unsupported
unions, so stored pointers do not show live spawner resumption.

The selected `StartCutsceneAndTeleportAction` ActionBase branch stores mask
blends, destination and teleport IDs, position and rotation vectors, a
cutscene ID, existing entity and scene-object lists, extra streaming settings,
and a preload flag. Its current-build contract authenticates the selected
switch jump and wrapper, complete generated reader and formatter, all ordered
reads and setters, thirteen `Param` contexts including the element types of
three nested lists, and a finite signed-integer teleport UI enum. Ledger-joined
source hashes and reviewed cursor replay consume the reached action spans
exactly. Derived root ID and physical EOF corroborate framing; the full
reviewed corpus gate decides whole-owner status when later unions remain.
Stored cutscene and teleport arguments do not establish live playback or
movement.

The selected `ManuallyStopGuideGroup` ActionBase branch stores `groupId` as a
`Param<string>` after the eight inherited action fields. The current-build
contract authenticates the selected switch jump and wrapper, complete reader
and forwarding formatter, all ordered reads and setters, and the generic
string parameter context. Current source hashes join to the JsonData ledger,
and reviewed cursor replay consumes the reached action spans exactly. The
reached group IDs are concrete authored strings, with no local parameter path.
Derived root ID and physical EOF corroborate framing; the full reviewed
corpus gate decides enclosing-owner status. A stored group ID does not show a
live guide transition.

The selected `RemoveTrackingPoint` ActionBase branch stores `trackingPointId`
as `Param<string>` after the eight inherited action fields. Its current-build
contract authenticates the selected switch jump and registered wrapper, the
complete generated reader including owned fragments and forwarding formatter,
all ordered reads and setters, and the generic string parameter context.
Current source hashes join the JsonData ledger, and the shared reader consumes
every reached action span exactly. The reached IDs are authored string values
without a local parameter path or reference; root replay corroborates script
ID and physical EOF. Most enclosing owners continue to unsupported fields or
unions, so the full corpus EOF gate remains the owner-level boundary. Stored
IDs do not show a live tracking-point removal.

The selected `GetIsLeaderInTriggerVolume` GetterBase branch stores
`scriptPtr` as `Param<LevelScriptPtr>` and `triggerSlotId` as `Param<uint>`
after the seven inherited getter fields. The native contract authenticates
the selected switch jump and wrapper, complete reader including owned
fragments and formatter, ordered reads and setters, and both distinct generic
parameter contexts. Current source hashes join the JsonData ledger, and
shared cursor replay consumes each reached getter span exactly. Observed
script pointers select the current script, while the slot IDs are authored
constants. A derived root reaches script ID and physical EOF; the full
reviewed corpus gate decides which enclosing files are exact when later
unions remain. These stored arguments do not establish a live leader or
trigger-volume state.

The selected `SendLuaEvent1` ActionBase branch stores `manualValue` after the
inherited action fields. Its generated outer reader has eight ordinary setter
calls, then `ReadValue<SendLuaEvent1>` and an instance assignment; it does not
call the wrapper's declared `manualValue` setter. The nested wire value has
seven members: ID, UID, two boolean positions and one integer position that
retain neutral names, an event-name `Param<string>`, and a string containing
a JSON parameter descriptor. The native switch, wrapper, complete reader and
formatter, and nested type context authenticate the outer route; current
ledger-joined source cursors establish the inner seven-member shape and every
reached span. Derived roots reach script ID and physical EOF. Enclosing files
continue to later unions in the reviewed decoder, and a stored Lua event name
does not prove the event fires at runtime.

The selected `StartSubGameCountDownByTimer` ActionBase branch stores a finite
signed-integer countdown type, `ParamOutput<uint>` handle, current-script
`Param<LevelScriptPtr>`, and string timer ID after the inherited members. Its
native contract authenticates the selected switch and wrapper, complete
generated reader and formatter, ordered reads and setters, three distinct
generic parameter contexts, and the enum declaration. Current ledger-joined
source cursors consume the reached spans exactly. Observed countdown type is
the `Center` enum member; handle references are local output paths. Derived
roots reach script ID and physical EOF, while enclosing owners can continue
to other unsupported actions. Stored timer arguments do not show a live
countdown or UI state.

The selected `ShowStartToast` ActionBase branch has four parameter fields
after its inherited action members: description and title are `LangKey`
values; icon and toast object names are strings. The selected
`StopSubGameCountDownByHandle` branch has one `Param<uint>` handle after the
same inherited members. Both native contracts authenticate their switch
branches, complete generated readers and formatters, ordered setter calls,
and generic parameter contexts. Current ledger-joined source spans replay
exactly. Every observed stop handle path names a countdown output handle path
in the same serialized owner, establishing a stored reference between these
actions. The reached owners still stop at later unions in the reviewed reader;
the stored reference does not establish that a countdown or toast appears at
runtime.

The selected `ShowFinishToast` ActionBase branch has description and title
`LangKey` parameters, an icon-name string parameter, and a boolean success
parameter after the inherited members. Its complete native reader and
formatter, ordered setter calls, and typed parameter contexts authenticate the
stored order. Current ledger-joined source spans replay exactly; the reached
race records store a false success value. Their enclosing reviewed action
maps contain subsequent header unions, so this action alone does not prove a
whole owner or a displayed failure toast.

The selected `ToggleMainHudActionPlayIgnoreMainHud` ActionBase branch stores
`Param<string> actionType` and `Param<bool> playIgnoreMainHud` after the eight
inherited action members. Its selected switch branch, complete native reader
and formatter, ordered reads and setters, and both typed parameter contexts
authenticate the stored shape; ledger-joined source cursors replay exactly.
The reached records store true boolean values and authored action-type strings
with spacing variants. Their enclosing action maps continue to later chapter
panel unions, so these stored values do not establish runtime HUD behavior or
whole-owner exactness.

The selected `ShowChapterPanelDirect` ActionBase branch stores an Int32 backed
`ChapterEffectType` parameter, chapter ID string, continuation boolean, and
version string after the inherited members. Its native switch, complete reader
and formatter, ordered setters, four typed parameter contexts, and finite enum
declaration authenticate the stored order. Ledger-joined source spans replay
exactly. Several enclosing action maps now reach their script ID and physical
EOF; another continues to an unsupported header. The corpus gate decides
whole-owner promotion. Stored chapter fields do not prove a panel displayed.

The selected `ShowChapterCompletedPanel` ActionBase branch has the same four
stored chapter parameters but a distinct native switch branch and generated
reader. Its own contract validates that branch, the finite enum, and current
ledger-joined source spans, including a reached owner after the HUD-action
route. Production framing now reaches script ID and physical EOF for its
reached owners. The corpus gate remains the whole-owner promotion boundary;
no displayed chapter panel is inferred from the stored fields.

The selected `SwitchToCamera` ActionBase branch stores blend style and time,
a `ParamOutput<CameraControllerBase>` path, camera name, two boolean controls,
optional entity look-at and bone fields, optional spawn position, and a spawn
position flag. Its native switch, complete reader and formatter, ordered
setters, ten typed generic contexts, and finite Int32 blend-style enum
authenticate the stored order. Ledger-joined source spans replay exactly,
including non-null camera output paths and authored entity or vector values.
Reached owners continue to other camera actions in the reviewed reader; stored
camera parameters do not prove a camera transition at runtime.

The chained `StartTrackCamera` ActionBase branch stores a camera-controller
parameter, follow and look-at entity pointers, follow offset, track name, and
tween time after the inherited action fields. `ExitCamera` has a separate
branch with blend style and time, camera name, and two boolean controls. Their
selected native switches, complete readers and formatters, ordered setters,
typed generic contexts, and the ExitCamera finite Int32 blend-style enum
authenticate the stored fields. Current ledger-joined spans replay exactly in
the reviewed decoder. Some enclosing camera action maps reach script ID and
physical EOF; others stop at later unsupported unions. The corpus gate decides
whole-owner promotion. Stored fields do not establish a live camera sequence.

`ResetFollowCamera` is a separate inherited-only ActionBase branch. Its
selected native switch, complete reader and formatter, and eight ordered
reads and setters authenticate the stored record. Current ledger-joined spans
replay exactly in the reviewed decoder; several enclosing action maps reach
script ID and physical EOF while others stop at later unions. The corpus gate
decides whole-owner promotion, and the record does not prove a runtime reset.

Three additional ActionBase branches have independently reviewed native and
current source layouts. `FacSetInteractLockedState` stores an instance key,
lock flag, and radio ID as typed parameters; `ToggleClearScreenButRadioV2`
stores an `isShow` boolean parameter; `RemoveNPCDialog` stores dialog and proxy
ID string parameters. Their selected switches, complete readers and
formatters, ordered setters, typed generic contexts, and ledger-joined source
cursors replay exactly in the reviewed decoder. Some enclosing action maps
reach script ID and physical EOF while others continue to later unions. The
corpus gate decides whole-owner promotion; stored fields do not prove a live
lock, display, or dialog change.

The selected `ScriptEvent.OnLeaderEnterTriggerVolume` ActionHeader branch
stores an unsigned trigger-slot filter and nullable unsigned output parameter
after its inherited header fields. Its native contract authenticates the
direct switch branch, complete fragmented generated reader and formatter,
ordered reads and setters, and four typed generic contexts across the
inherited and own fields. Current ledger-joined source spans replay exactly;
their stored slot filters are authored constants and their output parameters
are null. With the related leave header also reviewed, the reached race
owners now close their complete action maps, and the derived root reaches
script ID and physical EOF. The corpus gate remains the owner-level promotion
step; the stored header does not prove a live trigger-volume entry.

The selected `RequireSettlementShow` ActionBase branch stores constant
`targetDynamicEntity` (`Param<ulong>`), `targetLevel` (`Param<int>`), and
`targetSettlementId` (`Param<string>`) after the inherited action fields. Its
native contract authenticates the selected switch jump and registered wrapper,
complete reader and formatter, ordered reads, own setters, and all three
generic parameter contexts. Current source hashes join the JsonData ledger,
and reviewed cursor replay consumes each reached action span exactly. The
authored settlement IDs have tundra and hongs families with level values; this
is stored configuration, not an observed display. Enclosing owners still
require the full corpus gate and can stop at other unions.

Three related nine-member ActionBase routes, `FacShowForceUpdateSwitch`,
`AddListenerToSettlementReady`, and `LandMarkUpgradeShow`, each add one
typed parameter after the inherited fields: a boolean switch or a settlement
ID string. Their shared native contract authenticates each selected switch
jump and registered wrapper, complete generated reader and formatter, ordered
reads, own setter, and generic parameter context. Ledger-joined direct source
cursors and the reviewed decoder establish the reached stored spans. These
values describe authored facility and settlement behavior; no runtime effect
is inferred from the stored actions. Whole-owner status remains subject to the
current JsonData EOF gate.

The selected `BoolCompare` ActionBase route stores a `Param<BoolComparer>`
and two `Param<bool>` operands after the inherited action fields. Its native
contract authenticates the dispatcher and registered wrapper, complete hot
reader plus owned fragments and formatter, ordered reads and setters, and
three generic parameter contexts. The enum is a four-byte value type in the
selected native reader; current ledger-joined source cursors and the reviewed
decoder establish reached stored spans. An authored comparison is not a live
comparison result. In reached sources the comparer is stored as the same
enum value, while the first boolean operand often points to an ID reference
or a named path; its serialized constant slot is then a placeholder, not a
resolved runtime value. The second operand is usually an authored constant.
Only the whole-file JsonData gate closes an owner.

The selected `SetFacTopViewCustomRange` ActionBase route stores two
`Param<Vector3>` coordinates after the inherited action fields. Its native
contract authenticates the selected jump and wrapper, complete generated
reader and formatter, ordered reads, own setters, and both value-type
parameter contexts. Current ledger-joined source cursors and reviewed replay
close the reached spans. Both coordinates use constant parameter sources;
some authored pairs are zero and others are nonzero spatial bounds. They do
not demonstrate a live camera or facility view change. Whole-owner status
still requires the JsonData EOF gate.

The selected `FacPlayBuildEffect` ActionBase route stores a boolean build
effect switch, a float effect duration, and an instance-key string after the
inherited fields. Its selected-build contract authenticates the switch jump,
registered wrapper, complete reader and formatter, ordered reads and setters,
and all three generic parameter contexts. Ledger-joined source cursors and
reviewed replay close every reached action span. The current authored spans
store a false switch, a unit duration, and sub-hub instance keys across
several map regions. These are stored configuration values, not an observed
effect. Enclosing owners can still stop at later unions and require the
whole-file JsonData gate for closure.

The selected `FacChangeBuildingTemplate` ActionBase route stores a building
instance key, level, `FCNodeMode`, new template name, build-effect switch,
and duration as typed parameters. Its native contract authenticates the
selected wrapper and complete reader/formatter, ordered reads and own setters,
all six generic contexts, and the enum's Int32 backing and declared members.
Ledger-joined source spans and reviewed replay establish the stored fields.
Reached authored actions describe sub-hub template changes across several map
regions and levels, with the normal mode and a build-effect duration. They do
not show a live building transition; enclosing scripts still require their
later unions and the whole-file JsonData gate.

The selected `PlayEffectOnNpcProxy` ActionBase route stores an effect ID,
`NpcEffectType`, `MountPoint`, and NPC proxy ID as four typed parameters.
Its native contract authenticates the wide selected tag, registered wrapper,
complete reader and formatter, ordered reads and setters, all four generic
contexts, and both enum Int32 backings and member catalogs. Ledger-joined
source spans and reviewed replay prove the stored records. Reached authored
IDs name map transmission and character expression effects; enum values
include normal/material effects and no mount point, head, or custom point.
These values do not prove an effect played on a live NPC, and enclosing owners
still depend on their later unions and the whole-file JsonData gate.

The selected `EventArgsAssignFloat` ActionBase route stores an
`EventArgsPtr`, key, and float value as typed parameters. Its native contract
authenticates the selected reader and formatter, ordered reads and setters,
and all three generic contexts; ledger-joined source cursors close the reached
spans. Authored records mostly target a `ratio` key with a unit float, but
the `EventArgsPtr` parameter is path-sourced in those records. Its serialized
wrapped-string slot does not resolve the event-argument object or demonstrate
a live mutation. Enclosing scripts still stop at other unions pending the
whole-file JsonData gate.

The selected `SetAudioCueVar` ActionBase route stores a boolean, float,
integer, string, variable name, `EAudioVarScope`, and `EAudioCueVarType` as
typed parameters. The selected native jump, complete reader and formatter,
ordered setter calls, seven generic contexts, and both Int32 enum catalogs
authenticate that layout. Current ledger-joined source spans replay exactly
in the production decoder. In the reached cohort, the authored scope is
`LEVEL`, type is `BOOL`, and only the boolean value and variable name are
populated. Some variable names exactly match `AudioCueTable` `exprType=8`
operand strings; other names have no such match in the current table. This is
an authored name join, without a proved runtime cue selection or variable
update. A separate build-independent named-body claim revalidated on the
selected installed client establishes that `SetAudioCueVar.Execute` reads all
seven authored parameter fields and contains ordered iFix state-check,
string/float/int/bool cue-variable setter, and patch lookup call sites. This
is native body topology, not proof of which branch or
setter ran. The generated source and table audit owns the changing inventory.

The selected `OverrideNPCDialog` ActionBase route stores `Param<string>`
dialog and NPC proxy IDs after the inherited fields. Its selected-build
contract authenticates the wide ActionBase tag, registered wrapper, complete
reader and formatter, ordered reads and own setters, and both string parameter
contexts. Ledger-joined source spans and reviewed cursor replay prove the
stored IDs. The reached parameter values are authored constants; the dialog
IDs often prefix `DialogTextTable` row keys, while some do not join by that
rule; the proxy IDs name NPC variants. This establishes a stored reference
shape, not which
dialog a live NPC displays. Whole-owner status remains with the JsonData EOF
gate.

The selected `EnterDollyTrackCamera` ActionBase branch has a larger stored
body after the eight inherited action fields. Its current-build validator
authenticates the switch, complete generated reader and formatter bodies, every
ordered reader/setter pair, and each nested `Param<T>` method context. The
`moveWay` member is a `Param<TrackCameraMoveState>` whose enum has four-byte
`int` storage and exactly two declared values, `Distance` and `WayPoints`.
Both are present in current source. A dedicated finite enum codec reads the
four-member `Param` envelope and shared source/path tail; unknown enum values
fail closed. Ledger-joined source hashes and cursor replay establish the
reached route spans, and the reviewed ActionMap reader admits this branch only
while the selected native validator passes. Whole-file status still requires
the JsonData corpus EOF gate. These bytes record authored camera settings,
not camera movement observed at runtime.

The selected `PostAudioStatusEvent` ActionBase branch adds
`onlyTriggerExitAfterNodeTriggered` as `Param<bool>` and the entry and exit
event names as `Param<string>` after the inherited action fields. Its
current-build validator authenticates the dispatcher and registered wrapper,
complete reader and formatter bodies, ordered native reads, own setters, and
the three generic parameter contexts. Source hashes joined through the
JsonData summary and per-file ledger reproduce the reviewed action cursors;
the ActionMap reader requires that native validation before admitting the
route. Whole-file status still depends on the corpus EOF gate. The stored
event names and exit flag do not establish observed audio status changes.

The selected `SetEntitiesVisibility` ActionBase branch adds two boolean
parameters, a list of entity pointers, and the `ModelVisibleType` parameter
after the inherited action fields. Its current-build contract checks the
selected dispatcher, registered wrapper, complete generated reader and
formatter, all ordered reads and setters, and four nested generic contexts.
The enum has signed four-byte storage and a finite set of declared values;
unknown values fail closed. Ledger-joined source cursors reparse every reached
span, including populated entity-pointer lists, through the shared ActionMap
reader. Whole-file promotion still requires the JsonData EOF gate. The
serialized target list and visibility settings do not establish an observed
runtime visibility change.

The selected `WaterVolumeInfiniteSetHeight` ActionBase branch adds
`isFixedSpeed` and `isSmooth` as `Param<bool>`, `target` as
`Param<WaterVolumePtr>`, and `value` as `Param<float>` after the inherited
action fields. The current native reader resolves the water-volume pointer
to a raw eight-byte ID record. Its selected contract checks the dispatcher,
complete chained reader and forwarding formatter, all ordered reads and
setters, and the four generic parameter contexts. Ledger-joined source hashes
and reviewed cursor replay close the reached spans. Whole-file status still
depends on the JsonData EOF gate. The stored target and value do not show a
runtime water-height change.

The selected `SetFacMode` ActionBase branch adds one `Param<bool>` member,
`toFacMode`, after the inherited action fields. Its native gate authenticates
the dispatcher and registered wrapper, the complete reader and forwarding
formatter, ordered reads and setters, and the generic boolean context.
Ledger-joined source hashes and reviewed cursor replay close the reached
action spans. The enclosing LevelScript file becomes exact only if the full
JsonData gate reaches physical EOF. The stored mode flag does not prove a
facility mode changed at runtime.

The selected `EnemyPatrolStart` ActionBase branch adds a `Param<ulong>`
patrol ID and `Param<EntityPtr>` target after the inherited action fields.
Its native gate authenticates the selected dispatcher, registered wrapper,
complete reader and forwarding formatter, ordered field reads and setters,
and both generic parameter contexts. Current source cursors are joined to
the JsonData summary and per-file ledger, then replayed through the exact
field codec to the pinned action end. The reached target values use the
reviewed constant `EntityPtr` form; other pointer forms remain explicit
stops. Whole-file status still requires the JsonData EOF gate. Stored patrol
arguments do not establish that an enemy began patrolling at runtime.

The selected `EnableTyphoeaArcheryStage` ActionBase branch stores a level ID,
an LSM module pointer, a LevelScript pointer, and a stage index as four
`Param<T>` members after the inherited action fields. Its current-build gate
checks the dispatcher and registered wrapper, complete generated reader and
forwarding formatter, all ordered reads and setters, and four nested generic
`ReadValue<Param<T>>` contexts. Source hashes joined to the JsonData ledger
replay the exact action cursors; the shared ActionMap reader admits the route
only while the native gate passes. The full JsonData EOF gate determines
whether enclosing files become exact. Stored stage arguments do not establish
that an archery stage was enabled in a live session.

The selected `TyphoeaArcherySetChipId` ActionBase branch stores `mainChipId`
and `subChipId` as two `Param<string>` members after the inherited action
fields. Its current-build gate checks the dispatcher and registered wrapper,
complete generated reader and forwarding formatter, every ordered read and
setter, and both generic `ReadValue<Param<string>>` contexts. Current source
hashes join to the JsonData ledger and replay the exact action cursors. The
shared ActionMap reader admits this route only while that native gate passes.
Whole-file exactness still depends on the JsonData EOF gate. Stored chip IDs
do not establish which chip a live game selected.

The selected `FinishBuffs` ActionBase branch stores a
`Param<List<BuffPtr>>` member after the inherited action fields. Its native
gate checks the selected dispatcher, registered wrapper, complete reader and
forwarding formatter, nine ordered reads and setters, and the generic
`ReadValue<Param<List<BuffPtr>>>` context through `List<BuffPtr>` to its
`BuffPtr` element type. Current ledger-joined source spans all carry a null
list value with a local parameter path, so the exact codec accepts that form
and refuses positive list elements. A focused enclosing-owner replay reaches
physical EOF for some files; the other reached files stop later on distinct
unreviewed unions. The full JsonData gate decides published whole-file status.
The stored pointer list does not show any live buff ending.

The selected `MarkTaskConditionFailed` ActionBase branch stores a
`Param<TaskObjectiveEnum>` and a `Param<ScriptTaskPtr>` after the inherited
action fields. The pointer is a one-member `key` string wrapper. The native
gate checks the selected dispatcher and generated wrapper, complete reader
and forwarding formatter, ordered reads and setters, and both generic
parameter contexts. Ledger-joined LevelScript and template source receipts
replay their exact action cursors. The reached dungeon files continue through
the separately authenticated archery ActionHeader variants below; the tower
files advance to positive task-map entries. The Battle Tower template's action
map is exact,
while later owner fields remain partial. These stored task arguments do not
establish that a task condition failed at runtime.

The paired `OnTyphoeaArcheryUnitAdvancedStageComplete` and
`OnTyphoeaArcheryUnitAdvancedStageListComplete` ActionHeader branches share
the inherited header fields and add, respectively, a filtered module ID with
module and stage outputs plus a stage index, or a filtered module ID with a
positive integer stage list. Their selected native gate checks both dispatcher
branches, complete readers and forwarding formatters, ordered setters, and
the generic `Param` and `ParamOutput` contexts. Ledger-joined source cursors
close the stored headers; some enclosing dungeon owners now reach physical
EOF, while others first stop at a task-map condition. Stored event arguments
do not establish that either event fired in a live game.

The selected `CheckGameInstStartDuration` GameCondition has the four inherited
condition fields followed by `Param<CompareOperator>`, `Param<int>`,
`Param<string>` for the level, `Param<LevelScriptPtr>` for the script, and
`Param<string>` for the sub-game. Its native contract authenticates the
dispatcher, generated wrapper and script pointer, complete reader and
forwarding formatter, nine ordered reads and setters, and all five generic
parameter contexts. Ledger-joined source receipts close each selected
condition cursor; the reached dungeon owners now advance through their task
maps and final trigger volumes to physical EOF. The stored comparison and
parameter sources do not establish elapsed runtime or the condition's truth.

The selected `OnTrainLevelEvent` ActionHeader adds an event-key
`Param<string>` and a `ParamOutput<object>` to the inherited header. Its
native contract authenticates the dispatcher branch, complete reader and
forwarding formatter, ordered reads and setters, and the three generic
parameter contexts. Current ledger-joined source cursors close the stored
headers and advance the enclosing dungeon files to later, unsupported event
headers. The object output stores a parameter source and path; it does not
show a runtime value or prove that the train event fired.

The selected `OnEnemyTakeLastAttackDamage` and `OnSpellInfliction` headers
share the inherited event fields. The damage header adds a damage output,
an entity filter and output, and two Boolean filters. The spell header adds
count, entity, source and type outputs plus entity and energy-shard type
filters. Their native contracts check the selected dispatcher branches,
complete readers and forwarding formatters, ordered setters, and each typed
generic parameter context. Ledger-joined cursors include null entity fields
in the damage header and a positive stored entity pointer in the spell
header. The enclosing dungeon files advance to later unsupported event
headers. Stored filters and outputs do not establish that either event fired
or what value an output held at runtime.

The selected `OnSpawnerEntitySpawn` ActionHeader adds entity, group-key, and
wave-key outputs; a typed filter enum; group and wave key filters; and a
`Param<SpawnerPtr>` filter. Its native contract authenticates the selected
dispatcher branch, complete reader and forwarding formatter, ordered reads
and setters, and all typed parameter contexts. Ledger-joined cursors include
both explicit spawner IDs and parameter paths that name a spawner at runtime.
Whole-owner replay reaches physical EOF for some sources and advances the
others to later unsupported headers. The stored pointer and output paths do
not prove a spawn event, spawner lookup, or runtime output value.

The selected `OnSpawnerGroupBegin` ActionHeader stores group-key and spawner
filters together with corresponding string and spawner-pointer outputs. Its
native contract authenticates the dispatcher branch, complete reader and
forwarding formatter, ordered setters, and five typed parameter contexts.
Ledger-joined source cursors replay exactly. Two enclosing LevelScript files
reach physical EOF; the others advance to later unsupported headers. These
stored filters and output paths do not establish that a group began or what
values the outputs held at runtime.

The selected `OnSpawnerEntityDie` ActionHeader stores an entity output, a
signed 32-bit typed death filter, group and wave key filters and outputs, and
a spawner pointer filter. Its native contract authenticates the dispatcher
branch, complete chained reader and forwarding formatter, ordered setters,
eight typed parameter contexts, and the filter enum's underlying type.
Ledger-joined stored cursors replay exactly. Most enclosing LevelScript files
reach physical EOF; the remaining file advances to a later encounter header.
Stored paths and pointer IDs do not prove a death event or runtime output.

Three selected encounter ActionHeaders now have separate native contracts:
`OnEncounterActivated` stores an `LsmPtr` filter and output;
`OnEncounterBattlePartBegin` stores the same pointer type under `lsvPtr`
field names; and `OnEncounterBattlePartEnd` adds a Boolean completion filter
and output. Their complete readers, forwarding formatters, ordered setters,
and typed parameter contexts authenticate the stored layouts. Ledger-joined
cursors replay exactly across the encounter sources. Combined owner replay
closes some files at physical EOF and exposes later header or positive module
branches in others. Stored pointer IDs and output paths do not establish live
encounter state or completion.

The selected `OnEntityCastSkill` ActionHeader adds entity, entity-template,
first-target and skill ID outputs, a Boolean character filter, and a typed
`SkillTypeMask` filter. The native contract authenticates its dispatcher
branch, complete reader and forwarding formatter, ordered setters, all seven
generic parameter contexts, and the filter enum's signed 32-bit underlying
type. Ledger-joined cursors include consecutive headers in one source. Several
enclosing owners now close at physical EOF; the others advance to later
unsupported headers. The stored output paths do not establish a cast event,
target identity, or runtime output values.

The selected `OnLeaderEnterTriggerVolumeList` ActionHeader inherits the
common event fields and adds a target-script parameter, a `TriggerTarget`
enum with signed 32-bit storage, and `Param<List<uint>>` trigger slot IDs.
Its native contract authenticates the selected dispatcher branch, complete
fragmented reader and forwarding formatter, ordered setters, all three typed
parameter contexts, and the list's unsigned element type. Ledger-joined
source cursors include positive slot lists. Whole-owner replay closes some
LevelScript files at physical EOF and advances others to later unsupported
headers. The stored slot IDs do not establish live trigger membership or
event execution.

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
typed helper hooks preserve the original ABI; the runtime admits bounded
424-, 533-, 561-, and 568-byte samples, with exact copied-byte SHA-256 admission
for the current 561-byte target. It copies each source once into bounded storage
and publishes only after quiescent teardown proves every detour and trampoline
vacant. The accepted receipt exercised the first two lengths; the 561-byte
target is still awaiting a live observation, and 568 bytes is the separate
supplemental nonempty-ActionGroup probe. The
loaded complete reader body, seven helper
entries and ActionGroup window are separately hash-pinned in addition to the
native file gate. The accepted v2 receipt has zero genuine loss and overflow,
observes both required source shapes, and records complete field/child cursor
vectors after quiescent teardown. In both hash-joined samples the earlier
`one-member-wrapper` candidate begins at field 43
`switchToCenterBeforeCast`, and field 47 `useAIExclusiveFrame` closes at EOF.
The old and new corpora share that two-candidate encoding and the same five
terminal member kinds; the native field-43 bool read rejects the candidate
that begins one byte later on the witnessed reader route. The census replays
the verifier from its exact receipt, source-corpus, native-context and verifier
hashes before applying this selection to admitted, byte-identical prior rows.
New rows keep both candidates pending a current cursor witness.

The same receipt records every field-0-through-field-42 cursor in two
byte-distinct samples whose field 0 contains the identical empty two-list
`ActionGroupData` representation. A sequential reader derived from the current
generated wrapper types reproduces both vectors exactly, then applies only to
that structurally identical profile on admitted rows. It closes every reached profile member
except one `switchToBuffConfig` body whose nested action begins with unsupported
tag `0x0078`; that row remains exact only through field 41 plus the independent
field-43-through-field-47 terminal. Other admitted empty-ActionGroup rows are complete
named stored schemas. Admitted non-empty ActionGroup rows retain the selected terminal
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
This specialized reader leaves other first action tags and later timeline
elements to the separate shared-sequence reader described below. Each reader
stops at its own first unsupported boundary. Provider selection stays
conditional on the pinned native and input-set gates.

Physical tag `0x00B2` similarly maps to the 18-member `FindTargetActionData`.
Its nested selector tags differ from the older Buff selector table, so the
Skill reader supplies only reviewed current finder, validator, and
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
85-member `EffectActionCfg` body remains opaque in SkillData, so structurally
reachable SkillData cursors are not promoted to named-exact evidence. The
separate BuffData action gate closes its bounded `0x00A2` wrapper spans while
retaining that same nested effect-configuration boundary.

Physical tag `0x0116` selects `PlayAnimationWithStepData`. Its 30-member wrapper
inherits the exact 16-member `PlayAnimation` layout, then reads
`animBlendInAfterStep`, `battlePoseWhenStep`, `frameToOriginAnim`, `hideWeapon`,
`hideWeaponFrame`, `montageName`, `snapDistance`, `snapFrame`, `speed`,
`speedCurveKey`, `stepBlendIn`, `stepDistance`, `stepTarget`, and `useFixSpeed`
in generated setter order. `speed` uses `BlackboardDouble` and `stepTarget`
uses `TargetSettings`; unresolved nested selector routes fail closed. The
specialized reader closes the first timeline record at an exact cursor. The
shared sequence reader now calls that same bounded reader for reached later
`0x0116` actions. An authenticated exported-byte replay advances through the
formerly hidden later-timeline stops and rejoins whole-file EOF where every
following child is admitted. A later unsupported physical action remains a
first refusal; the shared adapter does not assign runtime animation behavior.

Physical tag `0x0092` selects the 19-member `CreateBuffActionData` wrapper. Its
four inherited members are followed by `asChildBuff`, `autoFinishByAction`,
`buffIconDurationSource`, `buffs`, `buffSource`, `contextKey`, `count`,
`finishWithNextSkillIfNotInherited`, `inheritSkillIdList`,
`inheritSourceSkillCastId`, `inheritSourceSkillCastInfo`, `isExtra`,
`overrideBuffIconDuration`, `passTargetGroupsToBuff`, and `targetSettings`.
Byte-pinned nested readers close every reached first action. A one-action
sequence closes the enclosing first timeline record; later sequence actions
are separately checked by the shared route table and can close when every
reached child is supported. A one-action, one-timeline shape can reuse the
authenticated top-level continuation and terminal wrapper to close the whole
SkillData file. Dispatch requires the complete
top-level ActionGroup/timeline/sequence shape so an unrelated byte equal to
`0x92` cannot select this decoder.
The first sequence can contain only CreateBuff while its ActionGroup still has
later timeline records. A separate continuation keeps the detailed first
CreateBuff proof and passes later records through the admitted shared routes;
it promotes the whole ActionGroup only when every later record closes. The
generic Buff reader can parse some later tags that are absent from the Skill
composite contract, including `0x019E` and `0x000C`; those stay explicit
stops until their Skill route ownership is authenticated.

The shared timeline-sequence reader reuses only reviewed action contracts
and preserves the distinction between an exact action, an exact enclosing
timeline record, and a whole ActionGroup. It closes reviewed roots for
`ConvertToTargetContext` (`0x008C`), multi-action `CreateBuff` (`0x0092`),
`LaunchProjectile` (`0x00DE`), and `SpawnAbilityEntity` (`0x0169`), then reuses
the top-level continuation only when every timeline record is exact.
It now advances through later `TimelineActionData` elements with the same
bounded member order and checks each reached union tag and member-count byte
against the reviewed route contract. A complete list can rejoin SkillData's
top-level fields and selected terminal wrapper; any unsupported later child
retains only the exact first-record prefix and its stop reason. The current
export probe found both paths, so a first-record closure alone must never
be treated as a whole ActionGroup.
The reached later `BroadcastAlertToCharactersAction` tag (`0x0023`) is now
admitted through the reviewed Buff formatter's eleven-member source order,
including its bounded SkillAlert, byte payload, and TargetSettings children.
The shared reader checks that dependency and the stored member-count byte
before promoting a later record. Other later tags and nonempty nested forms
still stop at their first unsupported child; an action name alone is not
sufficient to extend the list.
The corpus publisher chooses a complete shared-sequence profile over a
specialized PlayAnimation first-record prefix when both describe the same
file. The earlier priority order hid whole-file closures even though the
shared list and top-level continuation were already exact; both evidence
profiles remain in the generated row for review.
`CustomRootMotionAction` (`0x0099`) is a separate Skill-only finite route:
the selected native formatter reads a 24-member wrapper with bounded
Blackboard, curve, target, LayerMask, and byte-payload children. The reviewed
contract rechecks the dispatcher, method bodies, ordered callsites, and nested
type instantiations on the selected build. Current exported bytes can then
advance past this formerly unsupported action; later unsupported children
remain bounded, and stored root-motion data does not establish live movement.
The `FacBuildingPlayAnimationAction` route (`0x00B0`) exposed a different
gap: the composite route was already admitted by the current derived plan and
observed member-count checks, but the shared finite reader had no action
body. Its six stored reads are a bool byte, three scalar words, a bounded
length-prefixed byte payload, and a final bool byte. The selected native
derived plan is re-evaluated at the corpus gate and must match that shape;
the Skill reader then proves the following timeline and top-level cursors
against authenticated export bytes. These stored fields do not prove which
factory animation runs at runtime.
`SetSuperArmorAction` (`0x0159`) had the converse gap: the shared Buff reader
already had a finite body, but the Skill route table did not admit it. The
selected native formatter and existing Buff contract authenticate seven reads,
including two bounded scalar-flag payloads and a TargetSettings reference.
The Skill composite contract now names that dependency, and the shared reader
checks each reached payload's tag and member count before extending a later
timeline. The stored route does not establish when super armor is applied.
`EnemyWarningAction` (`0x00AA`) was a larger later-timeline stop. Its selected
dispatcher and generated reader establish an 18-member source order with
bounded TargetSettings and EffectActionCfg children. A separate native
contract pins the dispatcher, complete reader body, ordered calls, nested
generic type joins, and the existing Buff action profile it shares. The
Skill reader admits this route only through that contract and still stops
where a nested child has no finite grammar. The action name and stored
parameters do not establish a warning event or on-screen behavior.
`FinishAngryOnEnd` (`0x00B3`) is a later four-member stop reached after the
warning route. Its independent selected native dispatcher and reader contract
pin the common byte and three scalar words, including the Priority generic
context. The finite Skill action reader now checks that route and can advance
to the next timeline member without claiming that an angry state ever ran.
`SaveValueFromAIBlackboard` (`0x0142`) reuses an already finite shared Buff
body, but its Skill route was previously absent. The selected Buff formatter
contract pins eleven reads: the common action prefix, a byte payload,
TargetSettings, four further byte payloads, and a final scalar word. The
composite Skill contract now admits that exact tag/member shape and checks
the source dependency; a later unsupported action still stops the list.
Three further Skill routes already had finite shared Buff readers and
selected-build source contracts: `SetWeaknessAction` (`0x015B`) reads an
eleven-member body with scalar payloads and a nested Sequence;
`SetSkillCdAtOnce` (`0x0157`) reads eleven members including a byte payload,
TargetSettings and scalar payload; `LockCameraAimAction` (`0x00E0`) has a
54-member source order with curve, scalar, vector, and target profiles. Their
new Skill route joins check the physical tags and member counts, and the
selected gate rechecks the source method identities and code windows. An
exact stored timeline does not establish whether a weakness, cooldown, or
camera action executed.
`TeleportAction` (`0x017C`) is another admitted later route. Its reviewed
14-member source order includes a nested Sequence, scalar payload, and
TargetSettings profile; the selected code windows and reached member-count
bytes gate its use. Closing a serialized teleport action still does not prove
an active destination or movement in the scene.
`TeleportPosSelectAction` (`0x017D`) is a distinct nine-member route, not an
alias of `TeleportAction`. The reviewed Buff frontier-nine contract authenticates
its dispatcher, generated reader, ordered string/FixDistanceData/RangedData/
TargetSettings members, and nested type joins on the selected build. The Skill
reader reuses that contract and the bounded nested grammars; current VFS bytes
advance through reached instances with populated child forms, while later
unsupported actions still stop at their own tags. These
stored selection parameters do not establish which teleport destination was
chosen at runtime.
`CheckTwoDirectionAngle` (`0x0082`) is another reached Skill condition whose
finite reader was already reviewed for BuffData. Frontier nine pins its
physical action tag, twelve source reads, four TargetSettings children, and a
BlackboardDouble child on the selected native build. The Skill route now
checks that same read order and native gate before consuming the nested
profiles. SHA-matched exported SkillData records advance past this stop, and
records with no further unsupported child can rejoin the independent timeline
cursor. The stored directions and comparison value do not establish a live
condition result.
`SaveTwoDirectionAngle` (`0x0141`) is a separate eleven-member action. The
reviewed Buff frontier-nine route pins its source order and four
TargetSettings children; the selected Skill reader reuses those bounded
profiles and ends with a stored string. Reached timelines can pass this action
without treating its serialized directions as a measured angle or a live
blackboard update.
`PushBackAction` (`0x011E`) has a separately reviewed 20-member selected
native reader. Its ordered calls and eight nested type joins authenticate
TargetSettings, AnimationCurve, and BlackboardDouble children; the Skill
reader reuses their bounded profiles. SHA-matched records can pass this
action and rejoin the independent top-level continuation when no later route
is missing. Stored curve and distance fields do not show a pushback event.
`SnapToTargetWithRangeAction` (`0x0168`) has a separate selected-build reader
contract for its 18-member `Data` wrapper. The native dispatcher, complete
normal reader body, ordered source calls, and nested generic type contexts
authenticate TargetSettings, AnimationCurve, and BlackboardDouble reads. A
finite Skill reader advances every currently reached instance in SHA-matched
exported records; some whole files rejoin the independent continuation, while
others stop at later action tags such as `0x004E`. The stored target and curve
fields describe serialized inputs only: this evidence does not observe a snap
motion or a selected target in play.
`ComboCacheAction` (`0x004E`) reuses the independently reviewed Buff action
reader. Its five stored members end in a nullable counted mapping list; each
populated mapping has its own six-member profile, including a bounded scalar
and byte payload. The Skill route now requires the selected Buff contract's
read order and code windows. Reached records advance to later action tags,
which remain separately bounded; admitting this route alone does not close
those whole files or show how a combo cache behaves during play.
`AllowNextSkillAction` (`0x000E`) follows that route in many serialized
timelines. The installed dispatcher and generated wrapper re-derive a direct
five-member plan: the common bool/three-word prefix and a nullable
`List<string>` named `allowedSkillIdList`. The Skill reader requires that
type, tag, member order, and nested list element kind from the selected native
build, then bounds each string payload. SHA-matched VFS replay advances the
reached records to their next independent cursor; the full corpus gate still
decides which files are exact. The decoded strings mostly match SkillData file
identifiers, but some have no file in the current corpus. They are stored
allowed IDs, not proof that a player could or did transition between skills.
`DisableRootMotionAction` (`0x009E`) and `MarkCanInterrupt` (`0x00E8`) each
store the common four-member action prefix. The selected dispatcher and
generated-wrapper derivation recheck both direct plans; the reviewed Buff
frontier also pins the complete `0x009E` native reader. Their Skill decoder
admits only those physical tags and the four-member header, and SHA-matched
files can advance to the independent following cursor. These stored flags
do not show root-motion or interruption behavior at runtime.
`AddCameraControlStateAction` (`0x019E`) is a distinct 23-member View action.
The selected native Buff contract pins its complete reader and nested curve,
byte-payload, and nullable-list profiles; the Skill admission additionally
checks the current dispatcher route. Reusing that finite reader advances
reached Skill records to their next independent cursor while retaining stops
for later unsupported actions. The stored camera-state parameters do not
establish a camera change in live play.
`AddAIMarkerAction` (`0x0007`) reuses a reviewed Buff reader whose eight
stored members include a BlackboardDouble scalar, TargetSettings profile,
and direct scalar/byte fields. The Skill route now checks that source order
and selected native code windows before extending a reached timeline.
Records can rejoin the following cursor when every later action is also
supported; a stored marker action does not prove an AI marker was applied.
`AddDynamicNavmeshObstacle` (`0x0009`) reuses the reviewed Buff frontier-eight
route. Its six source reads end with a nullable counted `List<string>` and a
TargetSettings child; the Skill reader bounds both against the selected native
contract before advancing. Current authenticated bytes exercise populated
lists. A stored obstacle action describes serialization, not a runtime
navigation change, and later unsupported actions retain their own stops.
`TickIntervalAction` (`0x0181`) has a separately reviewed nine-member selected
native route. The source order identifies a nested SequenceActionData followed
by stored interval fields, including a string key; the nested sequence still
uses the shared action grammar and retains its own unsupported-child stops.
The Skill reader admits this route only after native validation. Its stored
interval does not establish a timer firing during play.
`CheckHp` (`0x0065`), `CheckPoiseValue` (`0x006E`), and `AddTagToEntities`
(`0x000C`) reuse separately
reviewed Buff action readers and their selected code windows. The Skill
composite checks each eight-member read order before admitting the route;
the existing finite TargetSettings, BlackboardString, GameplayTag-list, and
scalar profiles retain their own bounds. Reached records can advance through
these stored conditions/actions, while later tags remain independent stops.
This evidence does not establish a health or poise check result or an applied
gameplay tag.
`CameraRotateAction` (`0x0025`) has a selected ten-member native reader with
ordered enum, curve, and BlackboardDouble children. Its finite Skill reader
advances authenticated reached records, but the observed files still encounter
later actions. `NotNextCheckAction` (`0x00FD`) uses the reviewed Buff four-member
reader and an extended physical union tag; it advances those continuations
to `CurveEvaluateFloat` (`0x0098`). That nine-member route now has a selected
native dispatcher gate and reuses the reviewed Buff source order, curve,
BlackboardDouble, and bounded string payloads. Authenticated reached files can
rejoin the independent top-level continuation when later routes are supported.
These stored routes do not prove a camera rotation, a live next-action decision,
or a curve result during play.
`GainBreakingAttackAtb` (`0x00BF`) has a selected seven-member reader with
BlackboardDouble and two TargetSettings children. `OverrideCameraFollowAction`
(`0x0104`) reuses the reviewed Buff frontier-nine twelve-member route, including
its scalar and target children. SHA-matched reached Skill records can pass
these actions and rejoin the independent top-level continuation when no later
unsupported child remains. The stored parameters do not establish an attack
meter gain or a camera follow change during play.
The selected dispatcher also reaches four previously unadmitted Buff readers:
`CheckSuperArmor` (`0x007B`), `CheckTargetsEqual` (`0x0080`),
`EnablePartsAction` (`0x00A7`), and `CharWeaponAnimationAction` (`0x0036`).
Their reviewed native contracts pin seven, six, eleven, and twelve source
reads respectively, and the existing finite Buff reader owns each nested
profile. The Skill composite checks the source order and selected wrapper
identity before admitting these routes. A reached action can still stop on
an unsupported nested child; the stored condition or animation parameters
do not prove a runtime result.
An authenticated recheck of the apparent `CheckSuperArmor` tail anomalies
confirmed the reader's exact endpoint: its TargetSettings and scalar-profile
children close before the next physical union tag. The following byte patterns
select separately registered `BoneAttachAction` or `SaveBuffStackNumByTag`
routes, so those files retain a new-action stop rather than indicating an
offset repair to `CheckSuperArmor`.
`CommandToCharactersAction` (`0x004F`) has a separate selected fourteen-member
reader. Its ordered source calls and nested type contexts authenticate the
SkillAlertData and TargetSettings children, which reuse reviewed finite
profiles. Reached Skill records can pass the action and join the following
cursor; the command fields do not show that a character obeyed one at runtime.
`ReceiveMoveInputAction` (`0x0123`) has a selected twenty-member outer reader
and a nine-member MoveParamData child. The reviewed source calls and generic
contexts identify enum, BlackboardDouble, AnimationCurve, and move-parameter
reads; the Skill reader retains a finite child boundary. Stored move input
configuration does not establish a player input or resulting movement.
`CheckComboSkillCameraAlphaSetting` (`0x003D`) has a selected five-member
reader with the common bool and four source scalar reads. Its reached Skill
records continue to `TemporaryUnlockAction` (`0x017E`), whose reviewed Buff
frontier-nine route fixes eight reads and a TargetSettings child. The Skill
reader checks both selected native routes before admitting that chain.
`CheckHasMoveInput` (`0x0045`) is another reached four-member condition with
its own selected dispatcher, four source calls, and Priority enum context;
after it, later actions retain their own stop. These stored conditions and
flags do not show a camera state, input event, or unlock at runtime.
`TogglableAction` (`0x0184`) reuses a reviewed six-member Buff reader whose
last two members are independently bounded SequenceActionData children. The
Skill admission checks the selected union route, code windows, and nested
generic contexts before reusing that finite reader. An unsupported child
retains its own stop; a stored toggle does not establish runtime state.
`CheckSquadInFight` (`0x0052`) likewise reuses a reviewed five-member Buff
reader. The selected AbilityActionData switch and Priority generic context
are rechecked before the Skill reader admits either physical tag width. Its
stored condition does not establish the squad's live combat state.
`BreakInteractiveAction` (`0x0001`) has a selected nine-member action reader
and a separately selected twelve-member `InteractiveShapeFinder` child. The
native contract pins their source calls and nested types, while the finite
Skill reader scopes finder admission to this action's TargetSettings child.
The encoded calculation, damage-processor list, and target describe stored
inputs; they do not show an interactive object breaking during play.
`InheritBuffAction` (`0x00D2`) has a selected nine-member reader. Its native
source order and generic contexts identify a TargetSettings child and a
nullable string list; the Skill reader bounds both before the final string
payload. Reached files with later action or finder gaps remain partial. The
stored buff identifiers do not establish that a buff was inherited in play.
`SwitchModeAction` (`0x0178`) and `ClearProjectileAction` (`0x004C`) reuse
reviewed Buff readers with eight and twelve selected source reads. The Skill
composite checks their current dispatcher wrappers and source contracts;
the finite readers retain bounds on string, target, scalar, and list children.
Some reached rows advance to later physical actions. These serialized
commands do not establish a mode change or projectile removal during play.
`AnimatedCameraAction` (`0x0010`) has a selected twenty-four-member reader.
The native source and setter orders identify the camera fields and enum
contexts, while the finite Skill reader preserves raw float bits and bounds
the camera animation key payload. Current reached records continue to later
action stops; serialized camera parameters do not show a camera animation
playing at runtime.
`HideUIAction` (`0x00C6`) has a selected five-member reader. Its source order
and dispatcher identity bound the small action payload; the reached camera
sequence continues to a later physical action. Stored UI flags do not show a
live interface transition.
`MoveToLocationAction` (`0x00F8`) has a selected twenty-three-member reader.
The source order and generic contexts identify LayerMask, TargetSettings,
and AnimationCurve children; the finite reader retains raw scalar and float
bits and bounds each nested payload. Authenticated replay closes direct and
post-`SwitchModeAction` whole files, while other reached rows continue to a
later action or postprocessor. A stored movement request does not prove that
an entity moved during play.
`UltimateTimeAction` (`0x0194`) has a selected seven-member reader. Its source
order and setter calls identify the nullable TargetSettings list, GameplayTag,
and float fields; the list carrier reuses a reviewed Buff framing. Reached
records continue to `UltimateShowAction` after the bounded payload, so this
route alone does not close those whole files or show an ultimate effect in play.
`UltimateShowAction` (`0x0193`) has a selected four-member inherited-action
reader: one byte followed by Priority and two scalar words. The native route,
member count, source calls, and Priority context are checked on the selected
build. Authenticated replay closes some post-`UltimateTimeAction` whole files;
the others keep their next physical action stop. The stored show command is
not evidence that an ultimate display appeared during play.
`ChannelingCastingAction` (`0x0031`) has a selected eight-member reader. Its
inherited header, three stored Boolean fields, and BlackboardDouble duration
are fixed by source calls and setter order; the scalar payload uses a reviewed
Buff carrier. Authenticated replay closes both direct and post-ultimate reached
files, but a stored duration and flag set do not establish a cast at runtime.
`ModifyWeaponMountPoint` (`0x00F3`) has a selected nine-member primitive
reader. The native source order fixes its stored mount-point words, override
flags, and weapon index. Authenticated replay closes most reached whole files;
the remaining row continues to a later physical action. The stored words do
not establish a weapon transform or mount state during play.
`RayCastEffectAction` (`0x0121`) has five selected source readers: the action
and four ray-data records. Their ordered calls and nested generic contexts
bound EffectActionCfg, TargetSettings, AnimationCurve, raycast-list, audio-id,
and blackboard-vector payloads. The Skill reader admits the reviewed nested
profiles and authenticated replay closes the reached files. These are stored
ray and effect settings, not observed hits or effects.
`PickTargetAction` (`0x0114`) has a selected seven-member reader. Its source
calls and setter order identify the context key, BlackboardInt index, and
TargetSettings child after the inherited header. Authenticated replay closes
reached whole files or retains a later action stop; the stored target settings
do not prove a target was selected during play.
`DoOnceAction` (`0x00A0`) has a selected five-member reader with a bounded
SequenceActionData child. Its native source order identifies the child type;
that child still uses the admitted action grammar and preserves an unsupported
descendant as a stop. Authenticated replay closes reached whole files where
the child is supported. A stored sequence does not establish execution count.
`CheckSkillCameraMotionFree` (`0x0072`) has a selected six-member reader. Two
bounded strings follow its inherited header in native source order.
Authenticated replay closes some reached files and retains later action or
route gaps in the others. The stored camera keys do not prove camera motion.
`CheckTargetAngle` (`0x007D`) has a selected eight-member reader whose native
generic contexts identify a BlackboardDouble angle and two TargetSettings
children. The finite profiles bound both target objects. Reached files either
close exactly or retain later action/route stops; these fields do not establish
a live angle check result.
`MoveToTargetAction` (`0x00FB`) has a selected seventeen-member reader. Its
source calls and setter order fix LayerMask, TargetSettings, and AnimationCurve
children among primitive flags and float bits. Authenticated direct-stop
replay closes supported whole files and leaves later actions visible in the
others. Stored movement parameters do not prove actual motion.
`JumpToTargetAction` (`0x00DA`) has a selected eleven-member reader with two
TargetSettings children, a BlackboardVector3, and two BlackboardDouble values.
The native contexts and reviewed finite profiles bound those objects; replay
closes supported rows and retains next physical action stops in the rest.
Stored jump data does not establish runtime traversal.
`EliteBackSwingBeHit` (`0x00A5`) has a selected seven-member reader. Source
calls and setter order identify a BlackboardDouble duration, a stored finish
flag, and a BlackboardInt limit. Authenticated replay closes supported rows
and retains later route gaps; the fields do not prove a reaction played.
`GetTargetBuffBBAdvanced` (`0x00C4`) has a selected eight-member reader with
two bounded string payloads, BuffFindSettings, and TargetSettings. Its source
calls, nested contexts, and reviewed Buff child windows constrain the stored
shape. Authenticated replay closes reached files after preceding camera-motion
conditions where applicable; it does not prove a buff lookup at runtime.
`CheckTargetContains` (`0x007E`) has a selected six-member reader with two
TargetSettings children. Its source order distinguishes child and parent
settings, and authenticated replay either closes the whole SkillData record or
retains the next unsupported child. The stored pair does not establish the
condition's result during play.
`PhysicsCastAction` (`0x0113`) has a selected twenty-member reader. Separate
native sections pin its SourceForwardData and SourceToTargetData children;
the action also holds bounded fail/succeed sequences, target settings, scalar
settings, and hit-result blackboard keys. Authenticated replay closes reached
records where all descendants are admitted and retains a later route stop in
the others. These stored parameters do not prove a cast or hit occurred.
`LaunchUpwardAction` (`0x00DF`) has a selected fifteen-member reader with
finite airborne-effect, direction, source, and target child profiles. Direct
VFS replay confirms its reached first-stop records can advance; later values
seen at the cursor remain next-stop observations until their enclosing reader
and union route are independently proved. Stored upward-motion settings do
not establish a runtime trajectory.
`ChangeSkillAction` (`0x002C`) has a selected fourteen-member reader. Its
native source order distinguishes target and reverted skill IDs, slot and
source selectors, and cache and lifetime settings. Authenticated direct VFS
replay advances every reached first stop; an unsupported later child remains
visible where the whole record does not yet close. Stored skill replacement
settings do not prove a runtime transition.
`CheckBuffIdInContextAdvanced` (`0x0057`) has a selected eight-member reader
with a bounded buff-ID list and GameplayTagQuery child. Its native contract
points to the reviewed Buff child windows, while the Skill composite checks
the selected route before admitting it. Reached records advance to later
physical action tags; neither the stored query nor its ID list proves a buff
was present at runtime.
`ComboAction` (`0x004D`) has a selected seven-member reader. Its native
generic contexts distinguish BlackboardInt count, BlackboardDouble duration,
and TargetSettings source after the inherited header. Authenticated replay
advances reached records; one row then reaches the independently proved
BoneAttach route. Stored combo settings do not prove a combo was executed.
`StoreCurSkillExecuteFrame` (`0x0173`) has a selected six-member reader. Its
native source calls identify a bounded blackboard key and TargetSettings
child after the inherited action fields; the target profile is tied to its
reviewed Buff source window. Authenticated replay advances both reached
records to a later unsupported action. The stored frame key does not prove
when a skill executes.
`SkillAIMoveAction` (`0x0165`) has a selected sixteen-member reader. Its
`markerInfo` member is an eight-byte unmanaged copy in the selected generic
reader, not an invocation of the separately generated marker wrapper. The
native copy-size instructions and ordered source calls constrain that
boundary, while the final TargetSettings child uses its reviewed profile.
Authenticated replay closes both reached whole SkillData records; the stored
movement settings do not establish an AI path taken during play.
`BoneAttachAction` (`0x0000`) is a real selected union route, not a null
sentinel. Its native switch target resolves to a distinct registered wrapper
and thirteen source reads, including raw Vector3 rotation angles and a
TargetSettings child. Authenticated replay of the reached Camille row advances
from this action through the remaining timeline and rejoins the selected
terminal at physical EOF. Stored bone attachment settings do not prove an
attachment appeared in play.
`IgnoreModelIntervalCheck` (`0x00D0`) has a selected four-member reader made
only of the inherited action fields. Authenticated replay advances every
reached first stop; some rows close the whole file, while others retain later
physical action tags. Its name does not prove a model interval was skipped.
`KnockDownAction` (`0x00DD`) has a selected thirteen-member reader. Native
source calls and generic contexts distinguish BlackboardDouble duration,
DirectionSettings face direction, and two TargetSettings children. Its finite
child profiles rejoin the outer action; reached records either close the whole
file or retain a later action stop. Stored knockdown parameters do not prove a
character fell during play.
`TargetPostProcessorAction` (`0x017B`) has a selected eleven-member reader
with bounded center, direction, source and target selectors, plus lists of
postprocessor and validator data. Native generic contexts and reviewed Buff
child windows constrain those nested profiles. Authenticated replay closes
every reached whole SkillData record; the stored selection graph does not
establish which target was chosen at runtime.
`RemoveAIMarkerAction` (`0x012D`) has a selected six-member reader. Its two
new members are a raw GameplayTag word and a finite TargetSettings owner;
their source calls and child windows are checked against the current native
inputs. Authenticated replay closes every reached whole SkillData record.
The stored marker and owner do not prove a live marker was removed.
`TyphoeaArcheryChipDataAction` (`0x018E`) has a selected eighteen-member
reader. After the inherited action fields it stores bounded blackboard-key
strings and boolean save flags for projectile, ricochet, split, and trajectory
settings. Selected source calls and setter types pin the order; authenticated
replay closes every reached whole SkillData record. The fields do not prove a
projectile was emitted or an affix applied during play.
`TickIntervalActionV2` (`0x0182`) has a selected ten-member reader with a
SequenceActionData child, BlackboardInt tick count, and BlackboardDouble
interval. The native generic contexts and reviewed child readers constrain
those fields. Authenticated replay closes the supported reached records and
retains a later action tag in the remaining row; stored tick settings do not
prove when a sequence ran.
`CheckOriginSkillType` (`0x0048`) has a selected six-member reader shared with
the reviewed Buff source shape: an attack-type mask and a bounded list of
skill types follow the inherited action fields. Weapon SkillData records reach
this previously hidden passive-list first refusal. Direct VFS replay
authenticates their logical bytes; some close after admitting the route, while
others advance to later physical action tags. The stored predicate inputs do
not show whether the condition was true during play.
`SaveMoveAxisAngle` (`0x013D`) has a selected five-member reader ending in a
bounded key string. Reached Typhoea records advance past it, then stop inside
nested finder or validator unions; none closes solely from this route.
The key does not establish runtime movement-axis behavior.
`MoveToDirectionAction` (`0x00F7`) has a selected nineteen-member reader. Its
reviewed generic contexts distinguish a direction enum, raw LayerMask word,
finite TargetSettings child, and AnimationCurve profile. Authenticated VFS
replay decodes the reached action instances and closes their SkillData files.
Stored motion parameters do not prove an executed movement.
`CrushAction` (`0x0097`) reuses a selected Buff frontier contract with
seventeen ordered reads and eight nested generic contexts. Authenticated VFS
replay decodes the reached instances and closes their SkillData files. Its
stored targets, blackboard values, and flags do not prove a crush
or damage event during play.
`BlowOffEnemyAction` (`0x001D`) reuses the selected Buff frontier contract's
fourteen ordered reads and seven nested generic contexts. Authenticated VFS
replay closes the reached SkillData files after admitting this action. Its
target, direction, blackboard values, and flags are stored parameters; they do
not prove knockback or movement during play.
`CheckPhysicalInflictionType` (`0x006D`) has a selected six-member Skill route
backed by the reviewed Buff source order. The final members are an enum mask
and bounded saved-key bytes; two enum contexts authenticate their types.
Authenticated VFS replay closes some reached passive files and advances a
remaining file to a later action. The stored condition inputs do not prove a
physical infliction occurred.
`CreateBuffAttachingSkill` (`0x0093`) has a selected nineteen-member Skill
route. Its derived wrapper declares no own setters and inherits the reviewed
`CreateBuffAction` stored order; the independent route and source profile are
checked against the selected native build. Authenticated VFS replay closes the
reached passive files, including the continuation from `0x006D` when both
routes are admitted. The wrapper name and stored buff fields do not establish
runtime attachment behavior.
`InheritCCSAction` (`0x00D3`) has a selected eight-member Skill route. Its
native reader pins the stored blend-out float, bounded CCS key, TargetSettings
owner, and override flag after the inherited action fields. Direct VFS replay
of a reached Pelica timeline crosses this later stop, finishes every timeline
record, and joins the independently selected terminal start. The stored key and owner
do not prove live CCS ownership or blend effects.
`ChannelingDamageAction` (`0x0032`) has a selected twelve-member Skill route.
Its first eleven reads match the independently reviewed DamageAction source
profile, followed by a float32 trigger interval. Six native generic contexts
identify the nested types, including the DamageUnit list, whose elements still
use the bounded child reader. Authenticated direct VFS replay closes every
file at this first refusal through the selected terminal and EOF. The stored
damage units and interval do not prove that channeling or damage occurred.
`CheckHitColliderOptions` (`0x0064`) has a selected six-member Skill route. Its
last two stored values are typed collider-option and check-type enums; native
setter calls and generic contexts pin the read order. Authenticated direct VFS
replay closes both reached whole files. The stored predicate does not prove a
runtime hit or collider selection.
`CompareDeckAttr` (`0x0085`) has a selected ten-member Skill route backed by
the reviewed Buff source profile. Native reads and generic contexts identify
two operand enums, two bounded BlackboardDouble values, a comparison enum,
and a finite TargetSettings child. Authenticated direct VFS replay closes the
reached passive lists and joins field 42 to the selected terminal starts in
both files. The operands do not establish the condition's runtime result.
`CheckBuffStackNumByTag` (`0x0059`) has a selected nine-member Skill route.
Native source calls and generic contexts distinguish the stored stack-type
enum, TargetSettings, comparison enum, finite GameplayTagQuery, and
BlackboardDouble value. Authenticated VFS replay closes a Lifeng timeline and
advances the other reached files to later physical or contracted route stops;
the stored predicate does not establish a runtime buff stack count.
`ForceSpellStatusAction` (`0x00BA`) has a selected eleven-member Skill route
with three BlackboardInt children, two TargetSettings children, an energy
shard enum, and a flag after the inherited action fields. Authenticated VFS
replay advances the Yvonne and Deepfin timelines after `0x0059` through this
action without later stops. Their maintained outer continuations meet the
independently selected terminal starts and EOF, so the authenticated replay
closes both whole files. Stored spell-state parameters do not prove a runtime
transition.
`ModifyCameraLockPointAction` (`0x00EB`) has a selected six-member Skill route.
Native source calls and generic contexts identify the TargetSettings
mount-point owner and typed MountPoint override after the inherited fields.
Authenticated VFS replay closes the reached Agshield and Nefarp timelines and
joins field 42 to each independently selected terminal start and EOF. The
stored target and mount-point choice do not prove live camera behavior.
The nested `SelectorFinder` physical tag `0x0017` is a zero-member
TyphoeaArcherySelectedFinder wrapper; nested `SelectorValidator` tags
`0x0007` and `0x0008` are respectively a zero-member InScreenValidator and a
one-member InteractiveKeyValidator with a bounded key string. They have
independent selected native switch tables, not AbilityActionData action tags.
Authenticated VFS replay closes reached Typhoea and Rodin records where every
later child and the selected terminal also close; the stored selector/validator
objects do not show which target or key matched at runtime.
An extended action prefix `FA FF 00` represents physical AbilityActionData tag
`0x00FF`, `ObtainUspInNormalSkill`, and is distinct from the one-byte `FF` null
union. Its reviewed Buff frontier route has six stored members. A shared
reader that treats every numeric tag 255 as null loses this identity even when
its byte cursor is exact; only width-one `FF` may take the null-summary path.
`ApplyArmor` (`0x0013`) has a selected five-member action reader. Its inherited
bool, Priority enum, and two scalar words precede a finite TargetSettings
`applyTo` child; the pinned native reader and generic contexts establish that
order. Authenticated direct VFS replay advances every reached timeline through
field 42 to the independently selected terminal and EOF. The stored target
does not prove that armor was applied during play.
`BlightMiasmaToleranceZero` (`0x0019`) has a selected four-member wrapper with
no own setters beyond the inherited action fields. Its pinned native reader
and Priority generic context constrain the bool and three four-byte reads.
Authenticated VFS replay closes the reached enemy timelines through their
selected terminals and EOF. The wrapper name does not prove a live tolerance
change.
`BlockMoveInterruptSkill` (`0x001A`) has a selected four-member action reader:
bool, Priority enum, and two scalar words. Authenticated VFS replay closes one
reached Zhuangfy SkillData file through its selected terminal and advances two
others to later physical action tags `0x00AF` and `0x0038`. The stored flag and
priority do not establish runtime movement or interruption behavior.
`ChannelingActionV2` (`0x0030`) has a selected ten-member route with a finite
SequenceActionData child, TargetSettings child, count and interval words after
the inherited action fields. The pinned reader checks six own setter calls and
three generic contexts; its structure matches a reviewed sibling without
equating the two wrappers. Authenticated replay crosses the reached Typhoea
and Liino actions, closes their complete timeline lists and rejoins each
selected terminal after field 42. Stored channel settings do not establish
repeated runtime execution.
`CharFollowAction` (`0x0034`) has a selected four-member derived wrapper with
no own setters. Its native reader and Priority context constrain the inherited
bool and three four-byte slots. Authenticated replay closes the reached enemy
SkillData records through field 42 and their selected terminals. The wrapper
name does not prove a character followed another during play.
`FinishBuffByTag` (`0x00B5`) reuses a reviewed twelve-member Buff frontier
route. Its finite child sequence includes three TargetSettings objects, a
BlackboardDouble and a GameplayTagQuery after primitive members. Authenticated
replay closes the reached timeline lists; a separate maintained fields 1–42
continuation reaches each selected terminal exactly. These stored selection
parameters do not prove that a live buff ended.
`ExtendBuffAction` (`0x00AF`) reuses the selected six-member Buff frontier
route: four primitive members, TargetSettings and finite BuffFindSettings.
Authenticated replay closes two reached Zhuangfy records through field 42 and
their selected terminals. Another advances to an unsupported nested
SelectorValidator tag `0x06`; the surrounding file remains partial. Stored
settings do not prove an extension occurred at runtime.
`GetPatrolTeleportPos` (`0x00C2`) reuses a selected six-member Buff frontier
route with a bounded string and float-width value after the inherited action
fields. Authenticated replay closes every reached action group and rejoins
field 42 to each selected terminal. The stored distance and key do not prove a
runtime teleport or patrol decision.
`OverrideBornPosition` (`0x0103`) has a selected five-member action wrapper
reached through the three-byte extended union prefix. Its inherited bool,
Priority enum and scalar words precede the own `overrideRot` byte; a pinned
source call and setter constrain that final field. Authenticated VFS replay
closes the reached JZMonk action groups and rejoins field 42 to their selected
terminals. The stored flag does not prove a runtime birth position or rotation.
`RefreshHeadBarShowHideAction` (`0x012C`) has a selected four-member derived
wrapper with no own setters. The three-byte extended tag precedes the inherited
bool and three four-byte reads; the Priority generic context is pinned by the
current native contract. Authenticated replay closes reached enemy files
through field 42 and their selected terminals, including records with the
separate physical `0x00B9` action below. The wrapper name does not prove a
live head-bar change.
`ForceHideHeadBarAction` (`0x00B9`) has its own selected Skill dispatcher
route, while its six source reads reuse the reviewed Buff formatter: four
inherited action values, the `finishByAction` byte, and finite
`TargetSettings`. The target can be null independently of the outer wrapper.
Direct authenticated VFS replay closes all three reached enemy action groups,
continues through field 42, and rejoins each verified terminal start. The
complete Skill corpus gate confirms these files exact to EOF. This is stored
action data; neither head-bar visibility nor live target selection is observed
at runtime.
`CreateAdditionalBattleShape` (`0x0091`) has a separate selected Skill
dispatcher route to a ten-member generated wrapper. The first four reads are
the inherited action fields; its six own setters receive `duration`, three
follow/release flags, `ColliderShapeData`, and `TargetSettings` in native source
order. The finite collider and target children reuse reviewed Buff readers;
their opaque scalar bits retain structural-only interpretation. Direct
authenticated VFS replay closes one reached action in each of three SkillData
files and advances all three through their complete timeline lists. The
complete Skill corpus gate confirms these files exact to EOF. Stored fields do
not prove a live battle shape was created, followed a target, or released.
`ThrowPickupItemStartAction` (`0x0180`) and `ThrowPickupItemAction` (`0x017F`)
have separate selected four-member native wrappers with no own setters. Each
stores the inherited bool, Priority enum, and two scalar words after its
three-byte physical tag. The reached common-character records use `0x0180`
as a first root and `0x017F` as a later action; admitting only the first leaves
a later stop. Authenticated replay of both closes their action groups and
rejoins field 42 to the selected terminals. Stored action assignments do not
prove that an item was thrown during play.
`TakeDownAction` (`0x017A`) has a selected twelve-member wrapper and three-byte
physical tag. Four inherited action values precede `deadOption`, a finite
BlackboardDouble `duration`, DirectionSettings `faceDirection`, float-width
`immobilizedTime`, `returnTrueWhen`, two independently framed TargetSettings
members `source` and `targetSettings`, and the terminal `teammateBigStagger`
byte. The reviewed native route pins all twelve source calls, seven generic
type arguments, and eight own-field setters. Direct authenticated VFS replay
crosses the three reached actions in Aurora, Meurs, and Pogranichnik SkillData
and rejoins each complete timeline list and selected terminal; the full corpus
gate has yet to measure the resulting exact-file gain. The stored layout does
not prove a runtime takedown or teammate state change.
`CheckSpellInflictionType` (`0x007A`) has a selected six-member Skill route
backed by the reviewed Buff source profile. Its last two members are a mask
enum and bounded saved-key string; two generic contexts and the output
setters authenticate the read order. Authenticated VFS replay closes the
weapon SkillData files that reached this later passive route. The
stored mask and key do not prove that the condition held during play.
`CheckHealTag` (`0x0063`) has a selected five-member Skill route with a finite
GameplayTagQuery child. Authenticated VFS replay closes some reached passive
files and advances others to later tags `0x0044` or
`0x006B`. The stored query does not show whether a healing condition was true
at runtime.
`CheckConsumeBuffLayer` (`0x003F`) has a selected seven-member Skill route
backed by the reviewed Buff source and finite BlackboardInt child. Positive
passive files reach this condition. Authenticated VFS replay closes
their passive lists and fields through 42; each continuation meets the
independently selected terminal start, and the full corpus gate verifies their
whole-file exactness. The stored comparison inputs do not prove runtime buff
consumption.
`CheckObtainAtbType` (`0x006A`) has a selected eight-member Skill route with
two bounded typed enum lists. Authenticated VFS replay closes some reached
passive files and advances another to later tag `0x0132`. The stored flags and
list values do not prove a live ATB
change.
`CheckGlobalCDTimerAction` (`0x0044`) has a selected six-member Skill route
with a bounded buff identifier and finite TargetSettings child. Authenticated
weapon files advance through it and next reach passive
tag `0x000A`. This is a storage boundary, not evidence that a cooldown was
evaluated during play.
`AddGlobalCDTimer` (`0x000A`) has a selected seven-member Skill route with a
bounded buff identifier, finite BlackboardDouble duration, and TargetSettings
child. Authenticated replay closes the passive ActionGroupData in the files
that advanced from `0x0044`. The top-level continuation through field
42 then ends exactly at each independently selected terminal start; the full
corpus gate verifies their whole-file closures. The stored duration and
target do not establish runtime cooldown timing.
The selected native contracts carry helper targets and code addresses. Reader
modules check named field shapes, while their native validators compare the
installed call targets to those contracts. Duplicating per-build helper RVAs
in Python would make the code itself a second stale native catalog.
The separate TimelineActionData diagnostic cursor derives the selected image
base from a unique declaring-type/method row and its named reader window in
the generated native context. Missing or ambiguous rows fail closed; a prior
method index or RVA is not a cross-build identity.
Frontier ranking must keep a stop's parser frame. A diagnostic `actual` integer
can be a nested collection count or profile marker as well as a physical
action tag; only a failed union-tag check identifies the latter. Replaying
authenticated bytes and retaining the enclosing stop reason prevents a
numeric coincidence from promoting an unrelated action route.
The maintained Skill corpus builder retains the shared timeline decoder's
first refusal per nonexact positive-timeline file, alongside passive first
refusals. Earlier broad prefix handling obscured many later `0x0116` stops;
another diagnostic gap discarded `laterStopReason` when the reader returned an
exact first-record prefix with a later refusal. Both thrown and returned
refusals are now recorded. The bounded diagnostic exposes an integer as a
physical action tag only when the reader explicitly reports a union-tag
failure. The generated report owns the changing counts and ranked inventory.
Native route evidence and exact enclosing cursors, rather than diagnostic
frequency alone, decide promotion.

Positive `passiveEventActions` are a second, independent ActionGroup shape.
The current native ActionGroup order and reviewed `AbilityActionMap` formatter
establish a map header, scalar word, and nullable Sequence array before the
next list count. The maintained Skill reader now admits this shape only when
the following `timelineActions` count is zero and every reached action tag
and member count matches an admitted contract route. The supported rows rejoin the
existing fields 1 through 42 and selected terminal reader. Other passive
rows retain the count prefix when their action routes remain outside the
admitted table; the corpus now records each positive passive reader's first
refusal in the file row, with a bounded reason ranking in the report and CLI.
The previous broad catch hid these actionable route stops. The exact EOF
result of the separate derived-plan oracle
does not itself promote those rows in the reviewed Skill corpus.
The selected native Buff contracts for `CheckBuffIdInContext` (`0x0056`),
`CheckDamageDecorateMask` (`0x005B`), and `CheckSkillType` (`0x0078`) now supply
three more finite condition routes. The Skill composite contract checks their
read order and physical tag/member counts, and the selected gate revalidates
their method identities and code windows before publishing passive maps.
`CheckSkillType`'s list provider remains conditional where its Buff contract
says so; observed passive rows rejoin an independent following cursor, while
other missing action routes stay bounded.

This review also found that Buff's handwritten tag/member-count table had
drifted from the selected union contract at multiple routes, including an old
23-member count for this 24-member wrapper. Buff's header check now asks the
build-gated union contract for the pair instead of maintaining that second
count table.
`IfElseAction` (`0x00C9`) is an eight-member reader whose three nested
`SequenceActionData` members are selected through the reviewed RIP-load and
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
timeline root through its reviewed dependency and exact action cursor. The
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

The newer installed JsonData overlay adds SkillData and BuffData records while
retaining the prior records' logical lengths and MD5s. This is a real corpus
change, so the older complete family reports cannot be reclassified under the
new input set by an exporter-only rebind. The focused addition audit first joins
each added exported payload to its current verified VFS ledger row, then runs
the selected-build derived plan to EOF and checks its embedded identifier
against the file name. The maintained Buff reader still reaches its known
post-ID tail on those added records; that tail is not a recursively named
BuffData schema. A complete current BuffData census also found one new first
refusal before that tail: `buff_chr_0038_purrche_aura_block` reached
`EnableMoveColliderAction` (`0x00A6`) within `buffEventAction`. Its selected
native dispatcher and generated five-member wrapper constrain the inherited
bool and three DWORDs followed by a raw enum32 `mountPoint`. The bounded
reader now rejoins the named middle fields and exact `iconConfig` child at the
independently accepted id marker. The current full BuffData family census
again has no unsupported root continuation, while recursive action interiors
and suffix children remain open.

The added SkillData records exposed `ExecuteIntervalAction` (`0x00AE`) and
`GetTargetBuffBBAction` (`0x00C3`) as finite later actions, and
`SaveBuffStackNum` (`0x0135`) as a reached route already framed by the reviewed
Buff reader. The selected dispatcher and generated plans constrain their
member counts and nested SequenceActionData, BlackboardDouble, and
TargetSettings children; `0x0135` additionally rechecks the selected Buff
reader's code windows and source order. The `0x00C3` TargetSettings union
retains structural-only evidence. Two other first refusals were nested selector
routes: `TargetContainsValidator` (`SelectorValidator` tag `0x000C`) and
`ProjectileFinder` (`SelectorFinder` tag `0x000F`). Their selected native switch
tables are hash-checked, each reached branch's type-usage load resolves to the
generated wrapper, and its one-member plan hands the child to the existing
bounded TargetSettings or ColliderShapeData reader. Unknown children still
stop at their owning cursor. Focused replay now carries every added SkillData
record through the complete ActionGroup list and fields 1 through 42 to the
existing native field-43 terminal candidate. This establishes stored framing
under the selected build and current source-byte joins. Before the targeted
capture below, the added files had no direct runtime cursor receipt; this
static replay does not observe action execution,
selector results, blackboard values, or native refill/error parity.
The selected `SelectorFinder` dispatcher also authenticates
`SnapPointFinder` at its reached nested tag. Its generated wrapper reads
`radius` as a structurally framed BlackboardDouble before
`snapTargetSettings` as TargetSettings. The exact child cursor advances the
Mifu power-attack, ultimate, and combo sequences; the first two rejoin their
top-level continuation and previously verified terminal at physical EOF,
while the combo stops at a later independent action union. The current
SkillData corpus report holds source coverage and first refusals. These
stored selector fields do not establish live snap-point selection.
An independent static recheck gives the field-1-through-42 reader EOF as its
hard limit rather than either terminal candidate start. For every added row,
its resulting cursor lands on the earlier of two exact EOF terminal framings;
the later framing starts one byte farther in. A malformed bool at the earlier
start is refused while the later shape still parses, so mere terminal EOF
validity cannot select the formatter's actual cursor. This closes the added
ActionGroup parser frontier under the selected structural route, while leaving
terminal ownership and runtime behavior conditional on a current direct cursor
witness. The per-file joins, cursor offsets and malformed-byte checks are in
the generated added-file frontier and independent-cursor reports.
The selected native field-43 bool is followed by a field-44
`GameplayTagList` wrapper whose rechecked generated reader accepts a one-byte
non-null header of `1` or null header `FF`. Current source-hash joins show the
earlier terminal candidate supplies header `1` for every added row; the
one-byte-shifted EOF candidate would supply `0`. The selected native code and
registered formatter windows still match the installed build. This excludes
the shifted candidate **conditional on that wrapper/provider route**. This
static step did not observe a live formatter cursor or provider choice, so it
retained both terminal candidates. The per-file native-tail
comparison and window gates are in the generated added-file native-tail report.
The changing per-file counts and first-stop receipts are in the generated
gameplay MemoryPack addition and route-replay reports. A new-input complete
family gate is required after any further reader or source-byte change.
The new-input SkillData census retains the earlier live cursor inference only
for old logical files whose current VFS stream reproduces the prior path,
length, MD5 and SHA-256 under the unchanged selected native build. Its
maintained subset gate replays the pinned receipt, source corpus, native
context and verifier exactly. It distinguishes rows with unchanged full
physical identity from byte-identical rows whose VFS chunk or offset moved;
the latter are sound content rebindings because the SkillData reader consumes
decoded bytes and its terminal selection does not use physical VFS location.
The subset rebind alone leaves new files and any logically changed row
`ambiguous` in the complete family report. It transfers the prior parser
inference without creating a new live observation. The accepted supplemental farming source closes its
own cursor, while only the two required empty-ActionGroup samples anchor the
family-wide field-43 through field-47 selection. Focused ActionGroup closures
for added files therefore remain conditional on a source-bound direct cursor
witness for their terminal candidate. The changing tier counts, row identities
and current report hash are in the generated subset-rebind readiness,
validation and SkillData corpus reports.

### Static limit for new SkillData terminal cursors

The refreshed all-unselected VFS basis and native-only observer context pass
their exact provenance replay. Every row without a content-bound prior cursor
receipt SHA-joins its exported bytes to the current VFS logical source; none
duplicates the bytes of a previously selected row. The finite ActionGroup and
fields through `switchToBuffConfig` reach the earlier terminal candidate without
using either terminal candidate as their hard limit. Both anonymous terminal
framings still parse exactly to EOF. The selected native field-43 bool and
field-44 `GameplayTagList` wrapper favor the earlier candidate under the
reviewed ordinary formatter path. This static evidence alone does not observe
provider choice, the executed parent cursor, or refill/error parity. These
rows remained ambiguous under static evidence alone; the later complete
target-set receipt supplies their exact-source live cursors. The bounded
per-source checks and current provenance are in the
generated terminal static-limit and capture-readiness receipts.

The targeted `skilldata-cursor` receipt now directly witnesses the reviewed
new, exact SHA-joined Purrche second-talent source. Its quiescent cleanup,
complete same-reader top-level vector, ActionGroup child checkpoints, and zero
primary loss/overflow counters pass the separate capture-target verifier
against the unselected basis and native-only context. Fields 0 through 42
match the maintained static empty-ActionGroup profile; the runtime cursor
selects the earlier one-member terminal and closes at EOF. The current corpus
therefore promotes only that exact logical path and SHA-256 to whole-schema
exact. Three other captured sources close their own cursor, but they are not
admitted to this promotion, and the supplemental source with a populated
ActionGroup still has unresolved interior ownership. Overflow in the separate
off-target diagnostic sampler does not weaken the zero-overflow target capture.
The earlier publication receipt and its 424/533-byte selection remain separate.
The reviewed target, offsets, counter state, and current report paths live in
the generated verification receipt, not in this durable interpretation.

The JsonData family adapter consumes the exact passive shared-list and
multi-record CreateBuff profiles through separate structural predicates;
malformed profile claims identify the failed predicate, path and bounded
current row state instead of collapsing to a generic validation failure.

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
preflight passed for that prior basis. After a VFS content addition, a fresh
capture first needs an immutable unselected SkillData basis and IL2CPP context
report under the new input set; a prior context cannot serve as current
preflight even when the native binaries match.
An all-unselected basis has now been produced from the current VFS stream and
preserved separately. The maintained full IL2CPP context audit currently
requires a previously selected SkillData terminal sample: it stops on the
unselected sample's `ambiguous` boundary before it can emit a current context.
Its selected-sample prerequisite remains intact. A separate
`il2cpp.skill_cursor_native_context` path now validates the complete-shaped,
all-ambiguous current basis and its live source/tool provenance, pins the exact
basis report digest, and checks the selected native method identities, body
windows and every top-level and ActionGroup observer callsite. It does not
re-stream the whole corpus or convert a static observer coordinate into an
executed cursor. The former context cannot substitute for this current input
set. The existing receipt verifier's source bytes and selected-sample meaning
remain unchanged; its preflight can consume the separate native-only context
without promoting a candidate.
A later exporter rebuild changed the VFS input-set identity while the selected
native inputs and relevant logical SkillData bytes stayed stable. Regenerating
the complete unselected basis under that audit and applying the maintained
subset rebind retained the prior receipt's terminal selection only for sources
with authenticated matching logical identity and bytes; newly added sources
remain ambiguous. This transfers an inference from the earlier live witness
under unchanged selected reader bytes; it does not add a live cursor capture.
The reviewed capture-target contract binds one added SkillData logical path,
length and current source SHA-256 to the unselected basis. Another file shares
the length, so the recorder first safely copies the bounded source and hashes
those copied bytes; it rejects the other same-length source before opening a
cursor transaction. A failed hash calculation fails closed. The copy cap,
native manifest gate, quiescence checks and source-hash join remain in force.
The new direct target receipt was written by stopping the capture while the
game remained open; runtime readiness alone would not have supplied a cursor.
One earlier session ended when the game exited and left no receipt. Future
targeted captures must wait for `runtime.ready`, exercise a plausible source
trigger, then stop with `Numpad 9` and retain the raw receipt before exiting.
Authored links identify plausible triggers, not proof that the game loads the
source. A standalone reviewed binding for Purrche's smaller combo-skill source
preceded the target-set recorder. It admitted that source by an exact copied
hash; its populated ActionGroup requires separate interior evidence. The
second-talent witness cannot select its terminal by analogy.
The target-set capture binds the complete set of current
ambiguous SkillData logical sources plus the already closed second-talent
source as a positive control. The target-set contract pins an immutable
pre-capture selected-status report and the current native reader; a
non-launching audit rechecks source identity, exact set membership, native
inputs, and observer callsites before it emits the host's SHA-authenticated
binding file. The new recorder admits each source by copied-byte hash,
retains one full cursor vector per identity, and counts identical repeats,
conflicting repeats, and locally incomplete pairs separately. Its atomic
live progress is provisional. A quiescent, loss-free receipt is required for
publication. Sources never loaded during play remain missing rather than
acquiring another source's terminal selection. A direct top-level cursor
cannot by itself name the interior of a populated ActionGroup child.
The prelaunch target-set gate treats both its unselected corpus and its
immutable selected-status snapshot as parser-provenance-bound evidence. A
reader change requires rebuilding the unselected basis, freezing a newly
selected report, updating the reviewed target-set reference, and regenerating
the native-only context before preflight can pass. A stale-context rejection
after that contract change is expected, not a reason to loosen the gate.
A live target-set session retained complete direct cursor vectors for most
reviewed sources, but its bounded recorder-lock wait lost callbacks and the
positive control ended with an incomplete pair. The strict collector and
verifier reject the globally incomplete receipt. The opt-in diagnostic
authenticates current native inputs, exact copied source bytes, and each
retained field and child cursor independently; its output is explicitly
incomplete and not eligible for corpus publication. The retained rows select
the one-member terminal at EOF, but do not settle their populated ActionGroup
interiors or repair unassigned callback loss. V3 callbacks now wait on an SRW
lock while worker drains remain nonblocking; a long-contention regression
and non-launching preflight pass. A subsequent live run exercised the fixed
collector and produced a complete, loss-free receipt for every reviewed source
and the positive control. The strict target-set verifier replays the current
native and corpus gates, exact copied source bytes, field cursors, child
checkpoints and terminal EOF for each source independently. Its generated
report holds the source-level selections; the earlier diagnostic remains
nonpublishable.
The corpus overlay composes each reviewed live field vector with its
native-gated, whole ActionGroup static profile and exact fields through 42.
The full authenticated SkillData sweep promoted every formerly ambiguous
target-set source to a whole stored-schema exact row; the prior singleton
positive control remains under its separate verifier. No terminal-ambiguous
SkillData rows remain in that published input set. Unsupported action children
in other files and nested gameplay meanings remain separate recovery gaps.
Purrche's base combo ability-range variant was among the observed reads even
on a Potential-3+ save. Its exact-source static replay closes the authored
timeline and fields through 42; the live source-bound cursor selects the
earlier one-member terminal directly after field 42. The shifted EOF-valid
framing is now refused for this source. Authenticated `IfElseAction` bytes in
the parent projectile-hit skill place the base source in the fail branch of
`potential_3 >= 1` and the Potential-3 variant in the succeed branch, while
Purrche's Potential-3 table sets that blackboard value. The maintained
`buff_if_else_action_receipt` and `buff_compare_float_action_receipt`
validators make the named authored condition repeatable. Deserializing the
base resource does not establish that gameplay took its fail branch or used
that resource at runtime; preloading remains possible. The outer provider and
cache-selection path is still not source-bound by this cursor receipt.

## Generic-instantiation registration is a pointer array

Generic-instantiation registration is a pointer array, not inline records;
preserve the record's padding separately from its u32 argument count. The
maintained `scripts.game_data.il2cpp.context_audit` validates current native
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

## Setter order is the wire order, and it is derivable in bulk

A generated `*ForMemoryPack` wrapper carries one `set___<member>__` property
setter per serialized member, and the selected build's readers consume those
members in setter order, every inherited wrapper's members first. The runtime
type's own field declaration order is a *different* order and does not describe
the wire. The two disagree often enough to matter: where a reviewed contract
records both its `generatedOwnFields` declaration list and a natively proved
positional read order, the setter order reproduces the proved order and the
declaration order contradicts it, with no counterexample in either direction.
`OverrideJumpAction` is the compact case -- declared `overrideJumpType,
buffInput`, read `buff-input, enum32`. Never order a new reader by
`fields_for`; order it by the wrapper's setters.

That rule needs only metadata plus the runtime type table, so it does not have
to be recovered one wrapper at a time from a disassembled `Deserialize` body.
`scripts.game_data.memorypack.wrapper_members` derives the member order and
each member's declared type for every wrapper in the selected build in one
pass, and re-derives every reviewed contract to report agreement. Reviewed
member counts, reviewed setter lists, and the LevelScript layouts' named read
orders all currently agree with the derivation with zero disagreements; the
counts belong to `reports/game_data/memorypack_wrapper_members.json` and the
atlas's `generatedMemberEnrichment` block. Contracts differ on whether they
keep a member's backing-field underscore, which is a spelling difference and
not an ordering one.

The derivation's tier is `direct`, never `exact`: it names what a reader walks
and proves nothing about a cursor, a serialized width, a nested extent, or an
enum's values. Use it to name the members a reviewed reader already consumes,
and to propose the shape of an unreviewed wrapper that a native route must
still authenticate. `native_union_atlas` consumes it through the image it
already opened, joins a row only by explicit wrapper type definition or a
unique assembly-qualified wrapper name, and reports a member-count conflict
rather than overwriting the reviewed row.

## The action dispatcher enumerates generically

The AbilityActionData union has one switch table, and the chain each reviewed
contract proves per tag -- switch entry, route target, the rip-relative usage
cell that route's first instruction loads, the registered type index that cell
encodes, the generated wrapper that index names -- is mechanical. Walking it
for every entry resolves the whole union at once:
`scripts.game_data.memorypack.action_dispatcher` currently resolves every
route, agrees with every reviewed tag that records a wrapper definition, and
names a large majority of tags that no contract covers. All routes are distinct,
so there is no shared default target to disambiguate. Counts belong to
`reports/game_data/memorypack_action_dispatcher.json`.

The table's identity is not rediscovered or hard-coded: the reviewed
`AbilityActionData` catalog first identifies this union's wrappers, then their
contracts pin its RVA, entry count and SHA256. Every pin for that selected
table is compared, and the live image's bytes are re-hashed against it.
Nested finder and validator unions also have reviewed switch tables; treating
all contract-directory pins as one union made action enumeration fail when
those contracts were added. The catalog join keeps those independent tables
out of the AbilityActionData agreement check without relaxing a contradiction
within that union. A build whose dispatcher moved yields no routes.

Member widths come with the names. A member's size is fixed by its type for
every primitive, and for an enum by the primitive its generated `value__` field
declares -- which is not always int32: this build has enums underlain by `byte`,
`uint`, `short`, `ushort`, `long`, `sbyte` and `ulong`, so an assumed four-byte
enum would mis-size several hundred types. Derived widths agree with every
reviewed read-order token whose width is unambiguous, with no disagreement.
Where every member of a wrapper is fixed, the derivation reports the members'
summed width. That sum excludes whatever header the wrapper's own formatter
writes, so it is a lower bound on a record's extent and not a proven boundary;
resolving that header is what still separates a named tag from a readable one.

This establishes a tag's *identity* and its wrapper's member names, tier
`direct`. It reads no payload and proves no cursor, member width, nested extent
or EOF, so an enumerated tag is not `exact` and still needs a reader plus a
reviewed contract before its bytes are pinned. Its value is that an unreviewed
tag stops being anonymous: the BuffData and SkillData readers' failure mode
moves from an unknown union tag to a known wrapper with unnamed widths. A route
whose prologue is not the expected rip-relative load is recorded with that
status rather than guessed at, and a tag that contradicts its contract fails the
run closed.

## Fixed-width action bodies can be read from the derivation

The frozen `buff_actions` reader frames a root action as a union tag, then
either a `0xFF` null wrapper or one header byte equal to the serialized member
count, then the members. Its `header()` rejects any other byte, so its whole
tag-to-member-count table is confirmed by the authenticated corpus's own bytes.
That table and the bulk derivation agree on every entry, which both validates
the derivation against serialized data and fixes the framing constant: a
record's extent is the tag width, plus one header byte, plus the members.

Where every member of a wrapper is fixed-width, that makes the body a known
length, and a string member extends the same reach without a new evidence class
because the frozen reader already proves its length-prefixed framing.
`scripts.game_data.memorypack.derived_actions` admits exactly those tags on top
of the frozen reader and names each field instead of taking it anonymously. It is strictly additive -- a tag the frozen reader admits is
always delegated, never intercepted -- and it fails closed, so without the
installed build it is the frozen reader. Its cross-check rebuilds a record from
the derived member count and widths and feeds it to the frozen reader: on every
tag the frozen reader admits, the record is consumed and ends exactly where the
derivation predicts, with no disagreement.

Reaching further than a flat body needs one more join. A nested member declares
the type it holds, not the generated wrapper that frames it, and every wrapper
stores what it wraps in a single field whose name varies by generator vintage
(`__realInstance`, `__instance`, `___instance`). Reading that field's declared
type maps wrapped type to wrapper for all 4,857 wrappers with no ambiguity, so
the join is structural rather than a mangled-name match, and
`wrapper_members.wrapped_type_index` exposes it. Measured against the
dispatcher, recursing through fixed members, strings, nested wrappers and list
elements determines a little under half the current routes; treating a
recursive type as undeterminable is wrong, because recursion is bounded at read
time by a depth limit rather than by a static width.

A union's membership and tag order turn out to be recoverable from metadata
alone, which matters because nothing in the image addresses a nested union's
jump table with a rip-relative load, so the dispatcher walk does not reach one.
A union's members are exactly the wrapper types descending from its base
wrapper, and the tag is the member's position when those are ordered by a
**case-insensitive** comparison of the wrapped type's full name, `+` separators
included. Ordinal order is wrong (`animat` < `animato` < `anime`), and removing
the separators is wrong. On the one union whose tags are walked natively the
rule reproduces every route exactly, and it also reproduces the reviewed nested
rows: the selector subtype routes a timeline contract records, and the tag each
selector contract is filed under.

`scripts.game_data.memorypack.union_subtypes` applies it, re-checking the
walked union on every run and returning nothing when the rule stops reproducing
it. Its tier is `structuralOnly`, below the dispatcher's `direct`: a predicted
tag is an ordering inference corroborated against walked routes, not a route
read out of the binary. Where a walked route exists it wins.

What blocks nearly all of the rest is a single shape: a union base such as
`Selector.Finder.Data` has no members of its own, because it is a discriminated
union read as a tag plus a concrete wrapper, not a record. Enumerating those
nested union dispatchers the way the root AbilityActionData dispatcher is
enumerated is therefore the one remaining lever on this path, and it is the same
mechanical walk. Unity value types and a `SerializeFieldDictionary` member are
the small remainder, and that dictionary is exactly the family whose registered
formatter does not frame like its member list.

Recursing past a flat body closes most of the rest.
`scripts.game_data.memorypack.derived_schema` turns a tag into a tree of member
reads over the same tables: a nested record from its generated members, a list
or array as a nullable count plus elements, and a nested union as a tag plus its
concrete wrapper. A recursive type is a cycle in the plan registry rather than an
infinite expansion, bounded when the plan is executed, not when it is built.
Lists and arrays share one framing, which is why modelling `T[]` alongside
`List<T>` moved the resolved share from roughly a third of current routes to
most of them; `GameplayTag[]` alone had been blocking hundreds.

Every declared route now resolves, and closing the last of them was three
separate questions, not one.

**An enum that no member declares.** A member holding `List<T>` or `T[]` names
its element nowhere in any member list, so an enum reached only that way has no
width -- and an enum is written as its underlying type, which this build does
not always make int32. Deriving every enum's width from its own `value__` field,
over every enum definition rather than over the enums some member happens to
declare, is what makes such an element resolvable at all. `load_derived_tables`
returns that table beside the wrappers from the one parse that already
classifies them.

**The counted-map families, which are modelled rather than refused.** A type
whose framing is not its member list is never read from that list, but that is a
reason to look for a proven framing, not to stop. `Dictionary<K,V>` writes a
nullable count and then that many `KeyValuePair<K,V>` structs laid out with
.NET's own padding -- the value aligned to its own width, the struct padded to
the wider of the two -- and the `SerializeFieldDictionary` family writes the
one-member object header before exactly that. Both come from the reviewed
`codecs.levelscript.action_map`, whose CharInteractPerform reader reaches EOF on
all 202 current owners reading them, and the `<GroundedMoveGait, float>`
instantiation is separately walked by the `buff_residual_actions` exact-build
contract. Only an unmanaged key *and* value are modelled, because that is the
shape the pair layout is proven for; a managed side refuses the whole member.
This is the case worth generalising from: the family had been refused as a
whole while the framing it needed was already proven one lane over.

**`Beyond.Audio.AudioId`, settled from its formatter's body.** It is a
`System.ValueType` holding one `int _id`, with a hand-written
`MemoryPackFormatter`, so its field list proved nothing. Its `Deserialize` body
is a class-init guard, one `MethodInfo`-carrying call into a reader generic
instance, one 32-bit store into the value, and a return: no null-marker test,
no member-count byte, no second call, no loop, so no framing but the value
itself fits in it. `Beyond.Resource.StringPathHashFormatter.Deserialize` is the
same body shape, differing only in calling the int64 instantiation and storing
eight bytes, and its wire is already settled as its one int64 field. The settled
case fixes what the shape means; the store width fixes this one's extent. Two
consequences: `AudioId` joins `StringPathHash` as a settled formatter in
`levelscript_union_layouts.FORMATTER_BACKED_TYPES`, and a short formatter body
is now a readable proof route -- the store width and the absence of a branch say
what the wire is without decoding the reader call.

What is still refused is what has no such evidence: `SerializeReferenceDictionary`,
which no reviewed reader routes, and the remaining entries of
`FORMATTER_BACKED_TYPES` -- `BezierKnot`, `Gradient`, `RectOffset`,
`SendLuaEvent1`, `SendLuaEvent2` -- which that lane records as read from their
field lists on the strength of nothing. None of them is reached by a current
route, so the refusal is a guard against a future build rather than a live
blocker. Unity value types have no generated wrapper either, so only the widths
the frozen reader already consumes are modelled, and `UnityEngine.AnimationCurve`
is named as that reader's own proven `curve_profile` instead of a width. A plan
carries the weakest tier it contains, so any plan reaching a nested union is
`structuralOnly`.

**Resolution is not consumption**, so the plans are executed rather than only
described. `scripts.game_data.memorypack.derived_plans` walks a plan with the
frozen reader's own primitives -- its null marker, member header, nullable
count, length-prefixed payload and 28-byte keyframe curve -- so no plan kind
introduces a framing that reader does not already prove somewhere else. It is
strictly additive and fails closed on the same terms as `derived_actions`.

Executing them is what found the model's errors, and each was caught by the
reviewed reader rather than by argument. Three corrections came out of it.

**Having a subclass is not being a union.** The resolver had treated any
wrapper with a descendant as polymorphic and read a tag before it. That is
wrong for a concrete base: `Beyond.Blackboard.BlackboardString` has a subclass,
and the reviewed `paired_payload` reads it as the plain three-member object its
member list describes -- a string, a bool, a string -- with no tag at all. The
actual test is two independent metadata facts that agree: a union base is
**abstract**, and it declares **no `Deserialize` of its own**, because its
generated union formatter reads the tag and dispatches to the concrete
subtype's formatter instead. They agree on all 910 wrappers that have a
subclass, with no exception, and the one union whose tags are read out of the
binary -- `AbilityActionData` -- satisfies both. `WrapperType.frames_as_union`
carries it. Correcting this alone moved 22 reviewed tags from disagreement to
agreement and promoted 30 plans from `structuralOnly` to `direct`.

**A memberless union subtype is not unresolvable.** It writes a header byte of
zero and nothing else, which the reviewed `selector_finder_profile` records
directly: its per-tag header table is 0 for seven of its fifteen tags. Skipping
those subtypes left the executor with no plan to reach; planning them as an
empty member list closed every remaining derived-only route.

**A struct is raw memory, at its aligned size.** MemoryPack writes an unmanaged
struct with no null marker and no member header, so it is a width rather than a
nested body -- and the width is its size in memory, not its members' summed
widths. `CameraControlStateInitialParam` is the case that separates the two:
four bools and three floats sum to 16, the struct is 24, and the reviewed
reader takes 24 raw bytes. That size is not computed here. It is read from the
build's own `Il2CppTypeDefinitionSizes`, whose `instance_size` is the boxed
size, so the object header comes off. Five independent checks agree with it:
`GameplayTag` 4 and `CameraControlStateInitialParam` 24 from the frozen
reader's own raw takes, `AudioId` 4 from its formatter body's 32-bit store, and
`Vector3` 12 and `Quaternion` 16 from widths that reader already consumes.
Blittability is decided structurally and recursively -- every non-static field
a primitive other than `string`, an enum, or another qualifying value type --
which yields 2,295 sized structs and leaves a struct with a managed field
unsized rather than guessed. This replaced two hand-maintained width tables,
reproducing every value they held and correcting one.

*The general lesson is the same one this directory records elsewhere.* Each of
the three was a level-4 reading taken off a level-2 fact: inheritance standing
in for polymorphic framing, an empty member list standing in for an
unresolvable one, a member-width sum standing in for a struct's extent. The
reviewed reader refuted all three, which is what a cross-check against a
corpus-validated framing is for.

**Where it now stands, and what each measurement proves.** Of the 416 routes,
the frozen reader admits 209; a record built from the plan and fed to that
reviewed reader is consumed to exactly the plan's own end for **209 of 209**.
The other 207 are shown self-consistent, which synthesis cannot raise above
that. The corpus run is the evidence synthesis is not: over the exported
BuffData family, the frozen reader frames the root's members 2-6 and then the
named middle's fields 6-14 in 2,815 of 2,873 files, and the plan reader in
**all 2,873** -- the 58 it gains being the files an unknown action tag had
blocked, 55 at the root and 3 in the middle. Additivity is measured rather than
asserted: every one of the 2,815 files that already closed ends at the
**identical extent with the identical range count**, and none is lost.

**The inferred union ordering now has a sharper check.** The nested unions are
tagged by the ordering rule rather than by a walked table, which is why any
plan reaching one is `structuralOnly`. The frozen reader nonetheless reads six
of them -- selector finder, validator and post-processor, damage and heal
processor, and calculation -- with an explicit per-tag member count, and none
of the six is natively walked, so the rule has to place every one of those tags
correctly on its own. It does: **40 of 40 rows agree**, with no disagreement
and no missing base. `union_subtypes.check_reviewed_nested_tables` keeps that
as a standing check, keyed by the managed base names so a client update does
not invalidate it, and reports a misplaced tag as a member count that does not
match rather than as a plausible name. It corroborates the ordering; it does
not promote it, and a tag no reviewed reader covers stays an inference.

**Closing every file is not validating every plan**, and the run says so
rather than leaving the inference open. It walked **58 of the 416** routes and
**11 nested-union placements across 3 bases**; the rest of the plans are simply
not present in this family's payloads. So the three bodies of evidence cover
different slices and none subsumes another: the reviewed cross-check reaches
209 routes, the union tables 40 placements, and the corpus 58 routes and 11
placements on real bytes. `planTagsExercised` and
`nestedUnionPlacementsExercised` are in the report for exactly this reason.

**A second reviewed family, and a trap re-run on this very check.** Twelve
contracts record rows carrying a union tag, a member count and a type name.
Compared tag-first, 38 of them "disagree" -- and every one of those is an
artefact. `action_entity_fields.json` indexes the `Beyond.Gameplay.Actions`
family, not the `AbilityActionData` dispatcher these plans resolve, so joining
on the tag pits two unrelated numbering schemes against each other; not one of
its 83 action names appears in the wrapper the same tag plans. That is the
cross-package join this directory warns about, reproduced by accident while
checking something else. **Joining on the type name instead inverts it: the tag
becomes the thing checked rather than the key, and the result is 53 rows
agreeing on tag and member count with no mismatch**, with rows naming another
union's types reported unjoinable instead of compared.
`derived_schema.verify_against_reviewed_routes` keeps that discipline.

**Historical plan-reader comparison, not current corpus coverage.** The early
comparison showed that an optional generated plan could advance a reader yet
leave the reviewed Skill result unchanged. The decoder gates twice before that
reader matters: `rootTags` admits the first timeline tag, and
`allowedReachedRoutes` admits each route reached later. Widening only the root
set converted some anonymous union failures into named `not-contracted`
refusals; closure required admitting the reached child routes too. This is why
the current first-stop profile belongs in the generated Skill corpus report,
not in an old plan-reader result.

The admitted derived routes retain `evidence: derivedPlanCorpusVerified` so
they remain distinguishable from hand-reviewed native readers. For every
reached route, the decoder compares the recorded member count with the
payload's own header and fails closed on disagreement. That check corroborates
framing; it does not establish field meanings, source-reader order, or runtime
behavior. Unreached generated plans are not admitted merely because a wrapper
exists. `derivedRouteEvidence` in the composite contract records the method
and its boundary, while the current corpus report records changing coverage.

### Four families, and what each refusal turned out to be

Testing every exported payload directory against a root wrapper of the same
name found two more families that read whole for nothing but the asking --
**LevelConfig 216 of 216 and LevelScriptTemplateData 46 of 46**, both exactly
to EOF -- and turned the remaining refusals into four distinct, named causes
rather than one backlog.

- **`MissionRuntimeAsset` is not MemoryPack at all.** Its 1,046 exported files
  begin `7b 0d 0a`, which is `{
`: ordinary JSON text. The reader refusing
  them is correct behaviour, not a gap, and the family is excluded by name.
- **`LevelData` and `LevelScriptData` hold a `Dictionary<string, object>`.**
  `System.Object` names no layout for this generic plan reader, so its refusal
  stands. A separate LevelData reader frames the known object shape. Its
  14-float spline knot is independently confirmed by the selected native
  `BezierKnot` formatter's 56-byte copy and struct offsets; that does not
  resolve the dictionary's anonymous values or runtime use.
- **A counted map with a managed side was refused, and should not have been.**
  The rule had been to model only an unmanaged key *and* value, because that is
  the shape the padded-pair layout is proven for. But `declared_dictionary`
  frames the other case too: it computes a pair size only when both sides are
  unmanaged, and otherwise reads the key and then the value with nothing
  between them. Modelling that unblocked every family that carries one.
- **A memberless wrapper is not a derivation gap.** `FacOcclusionHandle` has
  nine instance fields and its generated wrapper has no serialized members,
  because MemoryPack serializes none of them; the formatter writes the object
  framing and nothing else. Refusing it had blocked MissionRuntimeAsset,
  LevelScriptTemplateData, LevelScriptData and the whole 1,026-subtype
  `ActionBase` union from one type.

*Two of my own defects surfaced in the same pass.* `plan()` walked a member and
its list element but not a map's key and value, so refs in those positions were
never planned and surfaced much later as an `unplanned` refusal at read time --
which is what the last 22 LevelScriptTemplateData files were. And a
formatter-backed type appearing anywhere in a tree failed the whole plan, even
where no payload ever reaches it.

***A refused body, and a position that is not the same thing.*** A
formatter-backed type's member list does not describe its wire, so its body
stays unread -- but a null marker is one byte whatever would have followed it.
The `nullOnly` plan kind accepts exactly that byte and refuses anything else,
so a payload that really carries such a body stops with a named reason instead
of being guessed at. It is a claim about the corpus rather than the type, so
the sweep counts how often the position was reached: **zero, across all four
families**. The kind earns its place by letting a plan *build* where such a
type sits in the tree, and the counter is what shows nothing was assumed at
read time.

**Both original families read whole, which no reviewed reader had claimed.** A family's
root type is itself a planned wrapper, so a file can be executed from its first
byte rather than decoded to an anchor -- and **all 2,873 BuffData and all 2,621
SkillData files consume exactly to EOF, with nothing refused and not one
landing short**. The reviewed readers reach an anchor or a first record and
leave the remainder explicitly opaque; this reaches the end.

*BuffData took one more correction to get there, and it was a classification
error rather than a framing one.* Every one of its 2,873 files stopped at
`dispelConfig`, which the reviewed root reader takes as **eight raw bytes** and
the plan was reading as a nested object. The type is a `bool` beside an enum,
so it should have been sized as a blittable struct -- but the blittable test
asked whether a type's base was `System.ValueType`, and **an enum's base is
`System.Enum`**. That one omission excluded every enum, and with it every
struct holding one: correcting it took the sized-struct table from 2,295 types
to **7,498**, and gave `DispelConfig` exactly the 8 bytes the reviewed reader
already recorded. That shape is the
evidence: a wrong member layout drifts, and a drifted cursor stops at an
arbitrary offset, so landing on the last byte repeatedly across files spanning
orders of magnitude in size is not something a wrong layout produces. The sweep reports `shortOfEof` beside `exactEof` precisely because it is the
number that would expose a drifting model, and it reached zero only after the
collection rule below; the 138 files that refused before it were refusing
correctly.

This also closes the family the timeline decoder initially never reached. 88
files carry a non-empty `passiveEventActions` list; the derived-plan oracle
consumes all of them exactly to EOF. The maintained Skill reader separately
promotes only passive maps whose reached routes are admitted and checked.
The other 206 files the timeline
decoder refuses at the envelope are correctly refused -- both action-group
lists are empty, so there is no first timeline record to decode, which is an
absence rather than a gap.

*Two corrections came out of getting there, and both were mine rather than the
data's.* The depth limit was set at 24 plan steps, roughly twelve nesting
levels, and refused 818 ordinary files; SkillData's real maximum is 55 with a
99th percentile of 39. Termination never rested on that limit -- every plan
step consumes at least one byte -- so it was a guard masquerading as a
correctness bound. And `PlanRegistry` defines `__len__`, which makes a registry
holding no dispatcher roots *falsy*; three reader paths tested it for
truthiness and so behaved as if unregistered, which is exactly the shape a
named-root run has.

***A hypothesis tested and refused, and then explained.*** The dominant
refusal was `TimelineAction+ForceSyncAnimData`, where the plan expected four
members and the payload's header byte said zero -- the same type, the same
value, 85 times, which reads like MemoryPack writing fewer members than the
type declares. Accepting a short header gained **nothing**: still 2,483 exact,
with 60 refusals merely changing category. Were those headers legitimately
short, reading them short would land on EOF. It did not, so the cursor was
wrong there rather than the header. The cause is the collection rule below,
and the refutation is worth keeping: the zero was a symptom several members
downstream of the real error, which is what a drifted cursor looks like when it
happens to land on a plausible-looking byte.

### From framing to values, and an oracle that checks the whole chain

Framing says where a member begins and ends. `derived_values` takes the same
plan and the same cursor and keeps what each member holds, under the name its
generated wrapper gives it, so the gameplay config reads as named data rather
than as proven byte ranges. **All 5,756 records of four families decode** --
2,873 BuffData, 2,621 SkillData, 216 LevelConfig and 46 LevelScriptTemplateData.

The interpretation is deliberately narrow, because a width is not a meaning. A
primitive decodes as its declared type. An enum keeps the integer actually
stored rather than a member name, which would be a second inference on top of
the first. A blittable struct keeps its bytes: the build's size table proves
its extent but not its internal field offsets, so rendering a twelve-byte
struct as three floats would be knowledge of the library rather than evidence
from it. A profile reports the span the frozen reader consumed rather than a
reading it does not make.

***The check worth having is one the decoder does not control.*** A record
carries its own identifier and the exported file is named after it, from the
exporter's logical path -- two sources that only agree if the framing, the
member order *and* the string decoding are simultaneously right. A wrong member
order still decodes a string; it decodes the wrong one. **All 5,756 decoded
identifiers equal their filenames**, with none refused. Each family names that
member differently -- `skillId`, `id`, `m_id`, `templateId` -- and a family
carrying none at all is reported as such rather than counted as a
disagreement.

***A second check, semantic rather than structural.*** The decode surfaces a
reference graph -- 3,554 distinct audio event names, 5,664 effect names, 1,675
buff ids, named blackboard keys -- and a reference either lands in the exported
world or it does not. Four members name another record of a known family, and
they resolve at **1,662 of 1,675 (`buffId`), 501 of 508 (`buffIdList`), 291 of
294 (`skillId`) and 277 of 279 (`projectileSkillId`)**. That is a far harder
thing to pass by accident than the identifier oracle: a wrong decode yields
strings that resolve to nothing.

*The measurement needed one correction before it meant anything.* Counting
every `skillId` gave 2,621 of 2,624, which looks conclusive and measures
almost nothing -- SkillData's own identifier *is* `skillId`, so nearly every
value counted was a file resolving to itself. Restricting the census to nested
occurrences drops it to 294 genuine references, and the ratio survives.
`verify_references` builds that restriction in.

What none of this establishes is what any member means. The names come from the
same metadata the framing does and carry the same tier; resolution shows that a
member names a record of that family, not what the reference is *for*; a stored
value is not a runtime value; and an unresolved name is reported rather than
explained, since absence from the export does not make a name wrong.

### A list and an array do not frame their elements the same way

**`List<T>` writes each element through `T`'s own formatter; `T[]` of an
unmanaged `T` is a packed array.** For a type with a generated wrapper the
first emits that wrapper's member header before each element and the second
does not, so the same type is four bytes in one position and five in the other.

The reviewed readers state both halves. `_skill_read_gameplay_tag_list` frames
every `List<GameplayTag>` element as five bytes -- a member-count byte of one,
then four -- and `_skill_read_buff_id_list` calls the same shape the retained
nested one-member wrapper. Against that, the frozen reader takes a
`GameplayTag` *member* as four raw bytes in its tag-7 route, and this lane's
own note that `GameplayTag[]` had been blocking hundreds of routes is the array
half of the same fact.

Getting it wrong in either direction is visible immediately, which is what
fixes the rule rather than a preference. Framing every struct element through
its wrapper costs BuffData 8 files and SkillData 98. Framing none of them
leaves 138 SkillData files refused. Splitting on the container closes
**both**: BuffData stays at 2,873 of 2,873 with no file's cursor moved, and
SkillData goes to **2,621 of 2,621 -- every exported file, consumed exactly to
EOF, with nothing refused and nothing short**.

*The general shape of the error is worth naming.* A type's framing was being
read as a property of the type, when it is a property of the type **in a
position**. The same reading had already been made correctly once, for a struct
as a member versus a struct in a counted map pair; a collection element is the
third position, and nothing but a corpus was going to reveal that the first
answer did not generalise.

That BuffData closure is also fields 2-14 reaching the accepted id anchor, not
a whole-file EOF claim: the named suffix beyond the anchor and the opaque nested
bodies inside those fields are unchanged. BuffData is one family -- the
SkillData timeline readers are validated by the Skill corpus gate and this
run does not cover them. And what the plans describe is still a generated
member order, not a proven cursor, for every tag no reviewed route touches.

The tags the frozen reader does not admit are only shown to be self-consistent.
That a real payload has that shape is not established by synthesis, and
admitting a formerly unknown route can change a previously bounded row
elsewhere in a record. The module is therefore opt-in and is not wired into the
corpus gates; a whole-corpus run is the adoption gate, and it belongs at a batch
boundary rather than after a focused edit.

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

The open formatter-check carrier window's uninterpreted tail does not certify
a runtime allocation extent or select the returned formatter. No observed final
cursor or terminal uniqueness follows from this conditional ABI. Provider
fallback includes a lazy callback path whose population remains a separate
evidence gap.

## Recovery acceleration

`scripts.game_data.native_union_atlas` validates reviewed Skill, Buff, and
LevelScript union contracts through one shared current-build PE/metadata
context and writes its generated index under `reports/`. Tags remain qualified
by dispatcher family, conflicting identities fail closed, and the atlas cannot
promote a field or invent a schema: setter types, nested layouts, and exact
cursors still come from the owning reviewed contract and reader. It replaces
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

## ConvertToSlot nested postprocessor closure

The selected `SelectorPostProcessor` switch dispatches physical tag `0x03` to
`ConvertToSlot.Data`. Its generated wrapper has no setters, and its selected
`Deserialize` body reads a single wrapper header with zero members; `FF` is a
separate null-wrapper state. The reviewed native contract checks the switch
target, registered wrapper type, formatter and reader bodies, source header
call, zero-member branch, and the current installed inputs. The finite Skill
reader applies this shape only at reached postprocessor children and still
requires the complete enclosing timeline, fields through 42, selected terminal,
and EOF before calling a SkillData file exact.

The current authenticated SkillData sweep closes the reached whole files whose
other children are already admitted. Two reached files advance to later
unsupported action tags, so admitting this postprocessor does not promote
their earlier prefix to a full record. The accepted corpus report holds the
per-build counts and file paths. This static stored type does not establish
runtime target conversion. The reviewed target-set terminal cursors are now
directly witnessed and published where their static interiors also close.

## Additional SkillData nested routes

The selected `DamageUnit` reader's tenth source member is a
`List<GameplayTag>`. Its generic callsite, element formatter, and list-count
source have independent native windows. The Skill reader accepts a signed
nullable count and elements that are either `FF` or a one-member wrapper with
one four-byte tag. It retains the following `DamageUnit` tail as a separate
bounded region and requires the parent action, ActionGroup and top-level
fields to rejoin before a whole file becomes exact. The active inflated list
provider has not been observed live; this is a stored-layout proof, not a
claim that a tag caused damage.

Three reached selector variants have distinct zero-member wrappers:
`GuardAITargetFinder`, `HittableObjectValidator`, and `ConvertToPosition`.
Their reviewed contracts pin the selected dispatch, wrapper identity, empty
setter set, source-header read and complete zero-member native body. The
finite reader distinguishes a null `FF` wrapper from a present zero-member
header and still requires exact enclosing cursors. These bytes do not prove
which target was found, validated or converted during play.

The Skill timeline reader also admits selected `SetAbilityEntityToMainChar`,
`LookAtAction`, `CheckAttackRangeType`, and `DisableMoveCollider` children
through separate native-gated read-order contracts. Their bounded readers
preserve the inherited action fields, then the route's stored string,
`TargetSettings`, enum or scalar members. Existing selected Buff action
sources separately authenticate the reached `IgniteAction`,
`TriggerComboSkillAction`, and passive action-route continuations. Direct
current-source probes rejoin each new child to an exact ActionGroup and the
top-level field-42 cursor. Whole-file status is decided by the authenticated
corpus gate and the selected source-bound terminal. Stored arguments and
branch conditions do not establish runtime action effects.

## Remaining gaps

- Continue SkillData through unsupported nested ActionGroup/action-union routes
  in the remaining partial files. The maintained reader closes supported
  multi-timeline lists and rejoins the selected terminal, but a terminal proof
  cannot fill an earlier unsupported child or make that file exact. The
  reviewed target set now has direct source-bound fields through 47 and EOF;
  newly added or changed sources require their own current terminal evidence.
  Further promotion must keep the exact receipt/corpus/native/verifier replay
  and current identity-set gates.
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
  The selected native BuffData reader's `List<DamageModifier.Data>` context
  stores its result in `damageModifier`. The selected child wrapper reads
  `condition`, `damageProcessors`, then `enableSide`; the independently gated
  `memorypack.buff_damage_modifier_receipt` replays those stored spans against
  logical-byte hashes for the current positive-list first blockers. This names
  the parent members without promoting nested condition actions or processor
  bodies to recursive schemas. Even condition-free rows can contain positive
  processor lists; neither a bounded outer cursor nor a wrapper name proves
  their leaf ownership or modifier behavior.
  The separately native-gated `DamageScaleProcessor` child receipt now binds
  the selected processor tag to its generated three-member order: `addition`
  is a selected BlackboardDouble, `side` is a stored enum-width integer, and
  `zoneName` is a signed-length byte string. The `addition` callsite's generic
  type joins the independently selected child reader and generated setters,
  naming `blackboardKey`, `useBlackboardKey`, and `value` at exact field
  boundaries. The `zoneName` call reaches the separately pinned signed-length
  string helper; the receipt retains its signed length and raw bytes without
  claiming native string-decoder parity. Current logical-source-hash replay
  rejoins every reached tag-five processor span. These stored fields do not
  establish damage arithmetic, zone selection, or a complete BuffData schema.
  The reviewed contract and generated child report hold the build-specific
  gates and coverage.
  For the bounded condition-free, tag-five damage cohort, a further selected
  native MethodSpec join proves that the child condition call reads
  `SequenceActionData`. Its separately checked formatter and reader windows
  establish the three-member header, zero action count and two terminal
  bytes for an empty sequence. A report-backed source join now checks the
  named parent `condition` span against the current logical file hash before
  accepting that exact seven-byte child. The terminal values remain stored
  booleans without live behavior evidence. All otherwise clean current
  zero-action/tag-five modifier sources now have exact named stored child
  boundaries for both condition and processor. The selected
  `CheckDamageDecorateMask` condition action is also exact at its stored span:
  the `AbilityActionData` dispatcher, complete source reader and generated
  wrapper bind six fields, including the enum-width check type and 64-bit mask.
  A one-action `SequenceActionData` with that tag and two terminal bytes
  replays to its parent condition endpoint. Its check type, mask bits and
  terminal bytes remain authored values, not an evaluated predicate.
  The Buff forward reader composes an empty condition with exactly one
  tag-five processor, one selected `CheckDamageDecorateMask` or
  `CheckDamageType` action with exactly one tag-five or tag-ten processor,
  or one selected `CheckDamageTypeMask`, simple `CheckTagMatch`, simple
  `CheckMainCharacterCondition`, selected `CheckBuffStackNumAdvanced`, simple
  `CheckHp`, or simple `CheckPoiseValue` action with exactly one tag-five
  processor. The selected `CheckBuffStackNumAdvanced` action also admits one
  tag-nine processor.
  A `CheckDamageDecorateMask` action also admits exactly one selected scalar
  processor tag zero, two or three; a simple `CheckTagMatch` action admits
  scalar tag zero or three.
  An empty condition additionally admits the ordered processor list [5, 6],
  and the ordered `CheckDamageDecorateMask`/`CheckDamageTypeMask` two-action
  condition admits one tag-five processor.
  It then reads
  the original bytes through all remaining root fields, checks source-ID
  equality and physical EOF, and records a distinct exact root receipt. The
  Buff corpus publishes this receipt only after current VFS identity and
  logical hash checks; JsonData independently replays the same reader against
  exported bytes before classifying it as an exact stored schema. Positive
  `attributeModifier` children remain a separate root proof obligation. Other
  condition action and processor variants retain their explicit gaps. Runtime
  provider selection, damage arithmetic, and actual modifier effects are not
  established by the stored layout.
  The selected-native `CheckDamageType` condition reader binds its five
  generated members, including the final `DamageType` enum-width field, to the
  complete source reader and both generic enum contexts. Current VFS identities
  and logical hashes rejoin its one-action sequence spans. The narrow
  selected-processor cohort now also closes the enclosing root on original
  bytes; JsonData's independent replay retains the same condition selection
  and EOF gate. Authored damage types do not establish runtime predicate
  results.
  A separate tag-ten `ModifyCalcResult` processor child now has selected-native
  ownership of `baseMultiplier`, enum-width `modifyType`, and `multiplierCnt`,
  with both BlackboardDouble interiors decoded by the independently checked
  child reader. Current VFS identities and source hashes replay the reached
  tag-ten spans. The Buff forward reader admits the sole tag-ten processor
  only with one selected `CheckDamageDecorateMask` or `CheckDamageType` action,
  and checks both nested BlackboardDouble endpoints before continuing through
  all 30 root fields to source-ID equality and physical EOF. Focused replay
  closes the current selected tag-ten sources. The full corpus gate requires
  current VFS identity and logical-hash authentication, while JsonData
  independently replays that exact receipt against exported bytes. An empty
  condition with tag ten and other condition or processor variants remain
  partial. Stored values do not establish evaluated multiplier or damage
  arithmetic.
  Selected scalar processor tags zero and three use separate one-member native
  wrappers. Their union entries, complete formatter and source reader windows,
  generated setters, source calls, and nested BlackboardDouble contexts bind
  the stored `addition` and `scale` members respectively. The independent
  BlackboardDouble reader then proves each child's three stored fields and
  exact endpoint. Current VFS identities and logical hashes rejoin these
  processor spans. Their compatible single-action conditions reach all 30
  original root fields, stored source ID and physical EOF, with independent
  JsonData replay. Other conditions and processor tags stay partial; these
  stored scalar bits do not establish critical-rate or penetration arithmetic.
  The separate tag-six `DamageTextProcessor` reader binds its generated
  `damageTextStyle` enum-width member and one-byte
  `useHpChangeAsDisplayValue` member to the selected union route, complete
  source reader and two source-to-setter calls. In reached two-processor lists,
  an exact tag-five child tiles directly into this exact tag-six child. The
  zero-action condition variant closes the original BuffData root through 30
  fields, source ID and physical EOF; a nonempty condition in another reached
  list remains partial. Stored style and bool bytes do not prove displayed text.
  The selected SequenceActionData reader's signed action count and terminal
  stores also support an ordered two-action list. Separately checked
  `CheckDamageDecorateMask` and `CheckDamageTypeMask` native readers name all
  direct members in their consecutive original-byte spans. With one tag-five
  processor, the two-action condition closes the enclosing root through the
  same source ID and EOF proof. Other action orders and lengths remain partial;
  stored predicates do not establish runtime condition results.
  The separately selected `CheckDamageTypeMask` condition child now binds the
  AbilityActionData dispatcher, complete formatter and source reader, and both
  enum contexts to five generated members ending in an enum-width
  `damageTypeMask`. Current VFS identities and logical hashes rejoin the
  reached one-action sequence spans, each with a sole tag-five processor.
  The forward reader now admits only this combination and replays the original
  bytes through 30 contiguous root fields, source-ID equality, and physical
  EOF. JsonData independently repeats that replay against exported logical
  bytes. Other processor combinations retain their partial boundary, and
  stored mask bits do not establish the evaluated condition.
  The selected `CheckTagMatch` action binds six generated members: the common
  primitive prefix, `checkTarget`, and `query`. Its source reader and nested
  MethodSpec contexts join separately validated TargetSettings,
  DirectionSettings, SelectorData, and GameplayTagQuery readers. The narrow
  reached target variant has empty context strings, null direction source and
  target references, a null selector finder, and empty selector lists. Its
  query stores an enum-width value and a bounded list of raw gameplay-tag
  words. Current VFS identity and logical-hash replay establishes the exact
  one-action condition child; the selected sole tag-five, tag-zero and
  tag-three processor subsets also close all 30 original BuffData fields through source-ID equality and
  physical EOF. Other target/query variants and processor tags remain
  partial. These authored tags and target settings do not establish runtime
  matching or targeting behavior.
  The selected `CheckMainCharacterCondition` action binds the four common
  primitive members and a `checkTarget` member through its generated
  five-member reader and TargetSettings MethodSpec context. The reached sole
  action uses the separately authenticated simple TargetSettings,
  DirectionSettings and SelectorData shape. Its original-byte condition span
  closes with the selected tag-five processor and then all 30 BuffData fields,
  source ID and physical EOF. Other compound lists containing this action
  remain partial. The stored target does not prove the live main-character predicate.
  The selected tag-two `AttackerCriticalDamageProcessor` binds its sole
  `scale` member to a three-member BlackboardDouble child. The union table,
  source reader, generated setter, direct calls and generic child context
  agree on the current native build. With a sole `CheckDamageDecorateMask`
  condition, it closes the same original-byte root proof. Other tag-two
  condition combinations remain partial; the stored scalar does not prove
  critical-damage arithmetic.
  The selected `CheckBuffStackNumAdvanced` action binds ten generated members:
  four common primitives, BuffFindSettings, buffStackNumType, TargetSettings,
  compareType, limitSkillCastId, and BlackboardDouble value. The reached
  sole-action conditions have one finder ID, an empty tag query, a simple
  target, and exact scalar child. The selected tag-nine
  `InstantModifyAttribute` processor binds a four-member AttributeModifier
  child and a final side enum. That modifier stores three enum-width values
  and a BlackboardDouble param. Its union route, generated setters, native
  source windows and nested contexts agree with original source bytes. The
  sole 0x003C condition with tag five or tag nine can tile all 30 BuffData
  fields through source ID and physical EOF. Other compound action lists and
  processor combinations stay partial; neither stack comparison nor
  attribute mutation is established as runtime behavior.
  The selected `CheckHp` and `CheckPoiseValue` actions share a direct
  eight-member source order while retaining separate native union routes and
  generated names. Each stores the four common members, `compare`, its named
  target, a bool, and a BlackboardDouble value. The current sole-action
  sources use exact simple TargetSettings and BlackboardDouble children.
  With one tag-five processor, each rejoins all 30 original BuffData fields,
  source ID and physical EOF. Other compound action lists, other target shapes,
  and live HP or poise predicates remain outside this proof.
  A separate selected-native compound-condition receipt now closes two
  remaining Mifu damage-condition spans on the original source bytes. Both
  start with the six-member `CheckOriginSkillType` action and its one-element
  SkillType list. One then stores the selected simple `CheckPoiseValue`
  action. The other stores the five-member `OrConditionAction`, whose terminal
  list contains one `CheckPoiseValue` sequence and one
  `CheckBuffStackNumAdvanced` sequence. The nested buff finder has an empty
  ID list and one query tag, a distinct exact variant from the sole-action
  stack condition above. Each pairs with one selected tag-five damage
  processor and rejoins all 30 original BuffData fields, source ID and
  physical EOF. Stored OR membership does not prove runtime condition
  evaluation or short-circuit behavior.
  A second selected compound receipt joins the ordered
  `CheckBuffStackNumAdvanced`/`CheckDamageType` condition and the ordered
  `CheckDamageDecorateMask`/`CheckBuffStackNumAdvanced`/`CheckTagMatch`
  condition. Both reached stack actions use the one-ID, empty-query finder
  variant, simple target and exact BlackboardDouble child; the reached
  TagMatch action has a simple target and one stored query tag. Both pair
  with a selected tag-five damage processor and replay through the same
  30-field root, source ID and physical EOF. The stored values do not prove
  comparison results or execution order.
  Two selected nested `IfElseAction` conditions now rejoin the original source
  bytes. Its eight generated members place one exact simple
  `CheckMainCharacterCondition` sequence in `conditionAction`, an empty
  `failActions` sequence, and one fieldless `ReturnFalseAction` sequence in
  `succeedActions`. One outer condition ends there; the other stores a following
  `CheckDamageDecorateMask` action. Each has one tag-five processor and closes
  all 30 BuffData fields through source ID and physical EOF. The exact stored
  branch lists do not show which branch executes at runtime.
  A separate two-action condition stores fieldless `NotNextCheckAction`
  followed by the same simple `CheckMainCharacterCondition` target. The
  accompanying tag-four `DamageIndependentHealthProcessor` binds its sole
  `multiplier` setter to an exact three-member BlackboardDouble child. The
  selected union route, complete native reader, source calls, target child and
  original source bytes agree through the 30-field root, source ID and physical
  EOF. Stored flags, target, and multiplier do not establish condition outcome
  or damage arithmetic. Other tag-four combinations remain partial.
  A further selected-native `ModifyDynamicBlackboard` receipt now closes four
  reached tag-236 action children across two still-partial positive damage
  conditions. Its ten generated members place a simple 13-member
  `TargetSettings` in `calculationTarget` and a three-member BlackboardDouble
  in `value`; both children reparse at their original named field endpoints
  under the current logical source hash. This names the stored child spans,
  including their nested target and value, but neither compound condition nor
  enclosing BuffData root is promoted. The other actions in those conditions
  and any runtime blackboard mutation remain separate questions.
  A selected `CheckTwoDirectionAngle` damage condition closes two consecutive
  twelve-member actions. The independently validated dispatcher and source
  reader order agree with all eight simple TargetSettings children and both
  BlackboardDouble values on the original logical source bytes. The
  condition's two terminal bytes rejoin the existing exact ordered tag-five
  and tag-six damage-processor pair. The narrow Broshan branch then tiles all
  30 BuffData fields through source ID and physical EOF. Other angle target
  shapes, action counts, terminal values and processor combinations stay
  partial; the stored directions and values do not establish the runtime
  comparison result.
  `memorypack.buff_1b_corpus` rebuilds the authenticated census and checks exact
  root-continuation tag `0x1B` ranges against re-streamed logical bytes, then
  joins the record to the current exact-build selected action reader. This
  continuation profile does not prove root-field ownership. The
  SequenceActionData provider remains unresolved; the anonymous action reader
  does not close BuffData suffix ownership or whole-file EOF.

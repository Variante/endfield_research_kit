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

Family receipt filenames are defaults, not freshness authority. The registry
can select an alternate complete Buff or Skill receipt through `--buff-report`
or `--skill-report`, but still checks its input set, source bytes and live
helper/native provenance. Admission failures identify the validator, failed
predicate, source identity and bounded expected/actual values. Buff's selected
root provenance follows its parser import closure, contributing dispatcher
declarations and transitive contract references. A contributing change requires
a fresh complete receipt; an unrelated contract change does not. Newly relevant
or conflicting dispatcher declarations still change or fail the dependency set.
Do not repair a provenance mismatch by editing receipt pins or repeating a
capture.

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

The Data page now exposes SpawnerConfig's one sequential owner cursor through
`frame_spawner_named`, with an earlier enemy-library or through-settings prefix
on refusal. It never uses a tail match to close an unknown prefix. Atmospheric
NPC rows retain the shared proxy codec's own named/framed status, and MapConfig
publishes its validated fields rather than only counts; duplicate JSON keys
fail closed. These views expose authored storage, not observed spawning,
action execution or condition results.

## LevelScriptData owner cursor

`levelscript_binary.frame_levelscript_named` owns the shared reader order for
the JsonData registry and Data page. It preserves each reader's own status and
physical cursor, keeps earlier exact-lane refusals on bounded fallbacks, and
reports all rejected profiles with bounded source/hash diagnostics if none
applies. A suffix fallback remains partial even after a native-lane refusal.

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
The previously isolated task-map queue closed for its selected ledger-matched
sources. Newly admitted earlier actions can expose additional task, module or
trigger-volume stops, so rerank these owner fields after each shared batch;
the old queue is not a family-wide closure claim.

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

The production inventory is the reviewed `action_map_layouts.json` plus
`action_map._required_native_gates`; route-specific fields, native proofs and
reached authored forms belong to each validator's docstring and contract.
The earlier per-route investigation narrative is condensed into that reusable
surface rather than duplicated here.

The recent action/getter/header and task-condition batches pass their native
validators, source-span receipts, layout derivation and selected production
replays. Some selected owners close at named-exact physical EOF; others expose
later routes. The combined `jsondata_corpus` gate owns their whole-owner
publication. A source-specific EOF result never changes a family denominator
by itself.

After that boundary, run `levelscript_first_stop_census` against the new
summary and pinned per-file ledger. It rechecks each residual source and ranks
whole files at the first refusal; later unions stay hidden until that refusal
is recovered. Native-gate failures are tooling/build diagnostics, not schema
frontiers. Keep changing rankings and selected-source inventories in reports.
Stored action, event, getter and task-condition inputs establish no execution,
resolved target, property value or mission order.

The full JsonData gate compares the complete raw-format reader scope before
and after decoding, including added Python sources and contract JSON. Prepare
capture-profile and other raw-format edits before starting that sweep, then
keep those inputs fixed until publication. A drift refusal preserves the
previous publication and reports a bounded, sorted list of added, removed or
modified files with their expected and actual lengths and hashes.

The reusable `levelscript_route_deserialize_native.py` validator now admits
typed route contracts as well as the earlier read/setter-window contracts.
Typed admission joins the native union switch and registered wrapper to the
generated member count, complete reader and owned native fragments, ordered
read/setter calls, exact generic `ReadValue` context and authenticated logical
source spans. The reviewed `contracts/levelscript_stored_routes_native.json`
uses that path for simple UI, factory-highlight, water-gun-response,
enemy-signal and decoration-animator actions with already established primitive
Params. It also authenticates `ParamOutput<T>` separately from `Param<T>`:
the selected generic reader must name the exact output type, while the existing
two-member output codec reads only its source selector and path. This covers
scripted-patrol event outputs and camera-effect save IDs without treating those
stored destinations as observed values. Header enums additionally require
their native `value__` field to be signed Int32; a four-byte wrapper shape alone
cannot distinguish signed and unsigned backing types. The shared validator
refuses missing or different generic contexts and enum declarations.
The same admission now covers `EntityEvent_OnIntTryUnlock`,
`LevelEvent_OnTravelPoleBegin`, `OnHitByLaser`, `GetterString`,
`GetSpawnerGroupKeyOfEntity` and `ToggleGeneralAbilityLoneClick`. The unlock
header retains separate target entity, entity-list and output operands; its
`EntityEventHeader.TriggerTarget` requires its own signed-Int32 declaration.
The travel-pole and laser-hit headers retain typed output destinations, while
the getters retain authored string/entity inputs. None proves the output value,
resolved spawner group, target selection, unlocked state or event firing.
`LevelEvent_OnEntityTakeDamage` now retains its damage/entity outputs and typed
entity and boolean filters. `ListGetValueInt` and `ListGetLengthInt` compose
the shared integer-list grammar. `MainCharMoveToDirection` and
`MainCharStopNavMove` retain their direction, gait and navigation identifiers;
the gait requires its own native signed-Int32 backing proof. Their selected
`ParamOutput<float>`, `Param<List<int>>` and gait readers must resolve the exact
typed generic contexts. Stored routes do not prove damage, getter results,
actor movement or navigation completion; later owner blockers remain partial.
This improves the canonical stored owner and Data inspector; it adds
no Story playback, mission trigger/order or runtime property claims. Source-span
replay still requires the complete current JsonData gate before whole-owner
EOF or corpus counts are published.

## LevelScript route-specific conclusions

- The three EnvTalk action variants share a bounded
  `Param<List<EnvTalkStruct>>` stored grammar while retaining separate
  concrete type receipts in `levelscript_envtalk_native.py` and its reviewed
  contract. Exact original/wrapper/adapter registration identities, typed
  parent and list contexts, formatter/interface slots, and the child's
  string-then-signed-int reader establish the default stored format. The
  wrapper conversion returns a native 16-byte value; that is not the serialized
  element width. This closes the offline reader join without another capture
  of the default provider. Runtime provider replacement, cache history and
  action execution remain outside the claim.
- A path/ID-sourced Param's constant slot is a placeholder: often
  `BoolCompare`'s first operand, and every reached `EventArgsAssignFloat`
  `EventArgsPtr`.
- `PlayFmvAction.beforeMask` is `Param<bool>`; names never decide wire types.
  `SendLuaEvent1` reads a seven-member inner value, bypassing its setter.
- Widths vary (`AudioBlackScreenBehaviour` enums byte-backed, most Int32);
  action `Param<GameplayTag>` is a raw int32; short `LevelScriptPtr` IDs
  frame exactly like long ones.
- `Param<CameraBlendCurveKey>` is a four-member parameter whose constant
  is the one-member `CameraBlendCurveKey` wrapper: a nullable UTF-8 key,
  then the ordinary Int32 `idRef`, Int32 `paramSource` and string `path`
  tail. The selected registered native readers and typed `ReadValue` context
  authenticate the reviewed declarations in
  `contracts/levelscript_camera_look_at_native.json` through
  `levelscript_camera_look_at_native.py`. The shared bounded wrapper in
  `codecs/levelscript/params.py` serves the camera and transform readers;
  the ActionMap typed branch shares its key-value grammar while retaining
  its existing parameter-tail rules. Current source replay closes selected
  owners, and malformed/trailing sources keep their refusal. Only the full
  corpus gate promotes a whole owner; this establishes no runtime camera
  activation. A similarly named field in another action keeps its existing
  codec until its own native type is proved.
- The `PosRot` generated wrapper has an exact two-member stored
  child: Euler angles first, then position, each a raw three-Float32
  `Vector3`. Selected registered readers, typed unmanaged-read context and
  the matching named setter stores authenticate this order through
  `contracts/levelscript_pos_rot_native.json` and
  `levelscript_pos_rot_native.py`; `codecs/levelscript/pos_rot.py` exposes
  a bounded finite-value child reader and the default stored list reader.
  The parent `Param<List<PosRot>>` now joins its typed `ReadPackable` context
  to the registered list formatter, exact original/adapter/wrapper identities,
  concrete conversion interface and formatter dispatch. Both transform and
  ActionMap readers share this composition. The conversion returns a native
  twenty-four-byte value; the stored child additionally carries its member
  header. Native output width is never a substitute for serialized framing.
  Runtime provider replacement, camera execution, refill/error behavior and
  resolved world-coordinate meaning remain outside the stored-format claim.

- `OnSquadMemberUspReachMax` supplies direct typed reads of `Param<bool>`,
  `ParamOutput<EntityPtr>` and `ParamOutput<float>`. The isolated generated
  output wrappers store only `paramTarget` and `path`; no serialized value of
  the generic output type is present. Their owned native body fragments,
  argument contexts and setters authenticate these child grammars through
  `levelscript_on_squad_member_usp_native.py` and its reviewed contract.
  Exact parent argument pointers now join the registered original types,
  adapters, generated wrappers, conversion interfaces and concrete formatter
  slots. The reference adapter returns an original object reference, rather
  than an inline value of the output's generic argument. The composed reader
  admits bounded positive and null children through this default stored
  grammar, while the direct outer-wrapper null branch remains independent.
  These facts establish neither live output values nor header execution.

  `il2cpp/formatter_composition.py` shares the registration, interface,
  constructor context, generic-context and usage-cell authentication across
  EnvTalk, camera poses, squad-USP and module readers. Each domain retains its
  own reviewed type identities, native ABI witnesses and field grammar.
  Constructor pairs or matching declarations alone remain insufficient.
  Once the complete static default chain is joined, no live cache history is
  required to re-prove that stored grammar. Runtime provider replacement and
  executed source cursors remain separate unresolved observations.

- `RollingStoneControllerData` and `RunePuzzleData` have reusable complete
  module grammars in `codecs/levelscript/modules.py`, authenticated through
  `levelscript_module_structures_native.py` and its reviewed contract.
  Launcher records compose typed float lists and existing `EntityPtr`
  children; the puzzle composes typed arrays, entity lists and an unmanaged
  `Dictionary<ulong,int>`. Its native pair reader copies sixteen stored bytes:
  the key, value and four trailing padding bytes. The bounded profile currently
  refuses nonzero padding; the native copy itself does not require zero.
  Whole-owner publication still requires the corpus gate after these nested
  structures advance the sequential owner.

- The removed live LevelScript provider probe supplied no admitted observation
  and is unnecessary for the statically proved default stored grammar. Runtime
  provider selection remains unresolved: a useful witness would bind copied
  source bytes, the actual MethodInfo, returned formatter, typed class/context
  identity, child entry/registers and before/after cursor in one admitted source
  scope. Snapshot pointer offsets alone establish no typed slot or inflated
  companion identity; scene/name associations do not authenticate copied bytes.
  This gap cannot promote gameplay execution, other contexts' cache behavior,
  or whole-owner EOF.

## BuffData

The 30-member root readers (`memorypack/buff.py`, `buff_actions.py`,
`buff_residual_actions.py`, `buff_icon_config.py`, and the top-level
`buff_frontiers_native.py`) give every file a named outer frame, but `memorypack/buff_named_schema.py`
keeps nested action, positive `stackEffects` and timeline bodies opaque. A
whole schema needs a forward receipt from byte 0 through all 30 fields, `id`
equal to the source stem and physical EOF: `buff_root_no_positive`
(null/empty recursive lists, shared DataPair/AttributeModifier children,
reviewed GlobalModifier branches, and positive-damage roots whose
conditions and processors each have a selected receipt) or
`buff_create_action_root_receipt` (a sole `CreateBuffAction`); JsonData
replays it. The complete Buff family gate admits the selected gradual
positive-damage root at physical EOF through a four-action condition:
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
The selected sword positive-damage root has a different recursive condition.
Its source-bound composition below also closes stored structure; neither root
proves live damage behavior.
For that one sword source, the selected condition now has source-bound receipts
for its first CheckDamageTypeMask and FindTarget actions and the following
CheckEntityNum action. The first two compose the existing mask reader with the
already validated Buff FindTarget formatter/dispatcher audit, rather than
borrowing native authority from the SkillData timeline parser. The
CheckEntityNum receipt independently matches the audited formatter and its
TargetSettings generic context to the current generated direct-member plan;
the original source closes both the action and its `checkTarget` child at their
selected endpoints. Its stored `targetGroupKey` and `storeKey` are file values,
not observed target or damage behavior. The original direct-child receipt
keeps its TargetSettings direction and selector interiors structural. The
independent `memorypack/buff_damage_check_entity_num_target_children.py`
now reparses that owned target through the existing TargetSettings,
DirectionSettings and SelectorData native gates. Its reached direction has
null nested source/target objects; its selector has a null finder and empty
subtype lists. Those branches close the selected stored target recursively;
positive interiors remain refused. The shared child owners expose
source-hash-checked bounded value readers for this composition. Its receipt
is selected-only and nonpublishable. The recursive condition and selected
root compositions below consume it through its owning reader; neither the
complete family gate nor the registry admits this isolated child directly.
The next IfElse action also closes
on this source: independently native-gated CompareFloat and
ModifyDynamicBlackboard children rejoin the selected eight-member IfElse
wrapper, whose fail sequence stores zero actions. The nested scalar, target
and blackboard interiors retain their structural tier in that storage receipt;
no branch decision was observed. The independent
`memorypack/buff_compare_float_blackboard_children.py` now joins both
CompareFloat operands to the exact BlackboardDouble child grammar in
`buff_adding_cooldown.py`. The parent validator rechecks each recorded
MethodSpec and type argument; the child gate authenticates its own reader and
generated setter order. Each original operand endpoint closes with named
`blackboardKey`, `useBlackboardKey` and `value` spans, retaining raw bytes.
This is a reusable stored-child proof, not a condition result or family
promotion. The independent selected condition composition below joins these
operands and target/selector children. The two later top-level ModifyDynamicBlackboard actions also close
under the existing native reader. A selected storage receipt now tiles all six
top-level actions and both terminal bytes through the condition endpoint.
That earlier storage receipt remains nonrecursive: its structural nested interiors
prevent whole-condition schema and whole-BuffData promotion even though the
stored condition span is exact. The reviewed gates and source selection are in
`buff_damage_sword_condition_prefix_native.json` and
`buff_damage_check_entity_num_child_native.json` and
`buff_damage_sword_if_else_child_native.json` and
`buff_damage_sword_condition_storage_native.json`; their readers consume only
the selected logical bytes and existing validated native contracts or audit rows.
The independent `memorypack/buff_damage_sword_condition_receipt.py` now
composes those action and child owners, the nested IfElse sequences and the
outer sequence terminals into a recursive selected stored-condition receipt.
The ModifyDynamicBlackboard parent rechecks both direct MethodSpec rows,
generic argument bytes and resolved child types before this composition. The
receipt marks `wholeConditionStoredSchemaExact`, while condition truth,
branch results and effects remain unobserved. It stays a nonpublishable child
diagnostic. The selected sword modifier below deliberately joins this child
to independently proved processor and enum reads before the sole root reader
can check all thirty fields, source-ID equality and physical EOF.
Four source-bound Buff roots have complete stored-schema compositions:

- The claymore upgrade's positive `healModifier` joins its native-audited
  `CheckHealTag` condition, four inherited members, `query` setter and two named
  `GameplayTagQuery` children to the parent heal modifier's three direct members.
  The tag-zero processor names `modifier` and `modifyTargetSide`; its nested
  attribute modifier names four members, with native-gated BlackboardDouble
  `param`. Reviewed selections: `buff_heal_check_tag_selected_native.json` and
  `buff_heal_processor_zero_native.json`.
- The selected BreakPassingSmallSceneObject source's `buffEventAction` contains
  one map and one SequenceActionData. The residual frontier proves the action's
  four inherited members; reviewed root-sixth and Sequence readers establish
  actions-before-event order and the two terminal booleans. The source selection
  is in `buff_break_passing_selected_native.json`.
- The selected empty-condition/tag-ten source first proves its positive root
  `attributeModifier`, including one named AttributeModifier and its converted
  attribute terminal. Its damage modifier then joins an empty SequenceActionData
  condition and one ModifyCalcResult processor with two native-gated
  BlackboardDouble children. The earlier attribute proof is required even though
  the cached blocker list names only damage. Reviewed selection:
  `buff_empty_condition_tag_ten_selected_native.json`.
- The selected sword damage source joins its recursive stored condition,
  one tag-five processor and stored `enableSide`. The parent condition,
  processor-list and enum MethodSpec arguments match the actual named setters
  and destination-field types. Reviewed selection:
  `buff_damage_sword_selected_native.json`. The JSON-safe condition certificate
  is checked against a regenerated private reader context on the selected
  native paths; it never serializes or trusts a cached parser object. The
  existing root reader then traverses every remaining field and physical EOF.

These selected fixtures no longer define the reach of shared root children.
`memorypack/buff_event_maps.py` owns the two event-map grammars: an
AbilityActionMap reads its event before its sequence list, while a BuffActionMap
reads the sequence list before its event. Their shared SequenceActionData child
uses the independently proved positive-sequence reader. The recursive action
owner composes reviewed CreateBuffAction and EffectAction children, including
bounded input and sibling-action lists; unsupported nested unions still refuse
the whole composition. This is a reusable root route, not an extension of a
selected filename's authority. Its complete root receipt must traverse all
thirty fields, match the source ID and reach physical EOF before either corpus
gate can admit it.

The complete family sweep now admits the shared event-map composition and
AttributeModifier root compositions beyond the earlier selected fixtures.
Older corpus receipts that predate those shared readers understate their
coverage. Use the current authenticated per-file root receipts and canonical
registry to select residual work; do not repeat already passing source probes
unless a related child, parent, contract or source finding requires it.

DamageAction's supported DamageUnit and calculation children compose through [the named reader](../../scripts/game_data/memorypack/buff_damage_action.py); unproved variants still refuse the root.
AuraAction and HealAction compose independently typed input, filter, shape and tag children through [their named reader](../../scripts/game_data/memorypack/buff_aura_heal_actions.py); unsupported recursive children still refuse the root.
CheckSkillType, CheckBuffStackNum and InterruptAction compose independently typed lists, BuffId values, blackboards and targets through [their named reader](../../scripts/game_data/memorypack/buff_skill_stack_interrupt_actions.py); live provider selection and gameplay evaluation remain unresolved.

CheckHp and CheckPoiseValue compose through
[`buff_vitals_actions.py`](../../scripts/game_data/memorypack/buff_vitals_actions.py).
The selected-condition contract still owns their named parent fields; the shared
reader removes the former single-action restriction and independently closes
each target and BlackboardDouble on the original span. A condition's stored
comparison operands do not establish which live entity or value it evaluates.

ReadSkillSettingData and SendBattleSignalToLevel compose through
[`buff_data_transfer_actions.py`](../../scripts/game_data/memorypack/buff_data_transfer_actions.py)
and its reviewed native contract. ReadData keeps `column`, `dataKey`,
`enhanceAttributeSource` and `storeKey` separate. Its nullable list, null elements,
targets and blackboards have independent boundaries; absent and empty lists
are distinct. The signal's `doubleValue` and `signalId` also have distinct typed
children. Formatter-to-setter transfers prove stored fields, rather than field
names alone proving wire order. Key payloads retain their original bytes while
encoding is unresolved. Live skill lookup, output-key writes, signal delivery
and ownership remain separate consumer joins.

[`buff_action_consumers_native.py`](../../scripts/game_data/buff_action_consumers_native.py)
re-proves narrow method-call claims from
[`buff_action_consumers_native.json`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
on the selected build. CheckHp and CheckPoiseValue contain target-selection and
blackboard-evaluation calls; CheckPoiseValue also calls `get_hasPoise`.
ReadSkillSettingData contains attribute lookup and dynamic blackboard assignment.
SendBattleSignalToLevel contains event allocation, sender/parameter assignment
and level-event raising. These are direct static call observations, conditional
on execution reaching those compiled paths. They do not join individual stored
fields to call arguments or establish IFix selection, values, delivery or mission
ownership. A failed method claim empties its group and marks it `pendingReview`;
native-input drift during evaluation empties all groups. This consumer audit is
independent of the stored-format coverage gates.

The same claims contract follows the root consumers. `Buff.Reset` contains
action, ignite, shield and modifier loading calls. `_LoadActions` reaches
sequence construction/reassignment, action-container registration and timeline
loading; `_ExecuteBuffAction` contains both ordinary and instant sequence
execution calls, while `OnStart` reaches dispatch and triggering. These joins
establish compiled consumer stages, not the active Buff instance, selected
stored list, event, target or branch. `BuffData.ConvertToServer` and
`_ConvertAction` provide a separate client-side projection through action and
modifier converters into `BUFF_RES`. That projection does not establish
transport, server processing or parity with client execution. The loader uses
unique method names for these generic signatures; its claims do not declare
their argument ABI.

The independent Buff profile in
[`buff_runtime_trace_capture.json`](../../scripts/game_data/contracts/buff_runtime_trace_capture.json)
targets the missing stored-definition-to-instance-to-action join. Native
preparation proves the selected methods, field types and read programs before
recording. Buff lifecycle entries retain supplied definition IDs separately
from stored IDs and instance carriers. Action assignment and selected consumer
entries retain their environment reference identities. Closed generic ancestry
can establish access to a nongeneric base field without establishing a closed
generic field layout or value ABI. Reference identity observations read pointer
bits only; they do not enumerate collections or invoke getters.

This profile is prepared and offline validated, with live observations still
required. Same-process receiver and environment equality must be joined through
assignment, reset and finish events because pooled pointers can recur. Reset
entry caches precede reassignment; temporal proximity does not establish
ownership. Per-frame triggering, action returns, target/provider values, dynamic
blackboard writes, IFix selection, server acceptance and final attribute writes
remain outside this observer. Archived BuffData bytes do not authenticate a
schema or native receipt by themselves. Format residuals remain independent
offline work even after a runtime sample is collected.

`buff_target_settings_child_receipt.decode_target_settings_value` is the bounded
value owner shared by typed action parents. Factoring this existing member loop
preserves earlier CreateBuff and Effect receipts; a new parent must independently
prove its field type, source context and exact child span. SetSuperArmor joins
its target to the reviewed final generic source read and composes the two
Blackboard value children. FinishBuffAdvanced joins its named BuffFindSettings
field to the exact child reader, including positive ID lists and GameplayTagQuery
arrays, and independently owns each target and BlackboardDouble field.

`buff_direct_target_actions.py` and `buff_direct_target_actions_native.json`
share an adapter across ShowHideActor, PlaySound, FinishOwner and
CheckMainCharacterCondition while retaining
a separate reviewed read order, member count and TargetSettings field for each
type. Every selected source context must belong to that parent's reader and
match the generated member type; a context belonging to a nested finder is not
another parent member. Physical union escapes retain their decoded action
identity: an extended union carrying the null-byte value is still an action,
whereas a literal null union consumes only its own byte. Named target composition
requires null nested direction targets and empty processor lists. Validator
lists may compose the independently proved zero-member and tag-query types;
finder values must use an independently named reader. Other selector children
remain explicit refusals even when their cursor framing succeeds.
These stored PlaySound members establish neither audio ownership nor live
playback. Action or child EOF alone never substitutes for complete root replay.

`buff_recursive_control_actions.py` composes IfElse's typed sequence children
recursively, CompareFloat operands, ModifyDynamicBlackboard targets and scalar
values, and CheckBuffStackNumAdvanced's independently owned children. Each
physical action span must close before its named child reader runs; recursively
anonymous children still refuse the root. `buff_id_actions.py` distinguishes
the one-member BuffId wrapper from BuffFindSettings' raw string-list elements.
Their different parent field types and native source contexts prevent treating
the two wire shapes as interchangeable.
CheckDamageDecorateMask also composes as a standalone event-map action through
its existing reviewed condition member plan. The original mask's eight stored
bytes stay intact; this broader parent composition does not add a predicate
evaluation claim.

`buff_blackboard_string_child_receipt.py` names the stored blackboard key,
use-key flag and value through matching native source stores and generated
setter destinations. CheckSkillId's list and RaiseTrainLevelEvent's direct
children independently join this grammar through their typed source calls.
Payload encoding and runtime interpretation remain unresolved: receipts retain
raw payload and flag bytes. Child contract reads observe current file bytes,
including after an earlier successful decode in the same process.

`buff_check_buff_id_context_advanced.py` independently joins the advanced
condition's list to BlackboardBuffId. That type inherits BlackboardString's
three members, but its own reader and typed list context still need proof:
the selected source calls invoke the same byte-payload, byte and byte-payload
helpers, then pass each result to the matching inherited setter in order.
Only after that join does the shared BlackboardString value decoder name each
list element. Null lists, empty lists and null elements remain distinct, and
the GameplayTagQuery field composes its own named child. This three-member
subtype is separate from the one-member BuffId wrapper. Neither inherited
layout nor child EOF proves condition execution, provider selection or whole
BuffData completeness; event-map admission still requires all original root
fields, source-ID equality and physical EOF.

`buff_selector_geometry.py` and `buff_find_target_action.py` compose the
FindTarget parent with independently typed DirectionSettings and SelectorData.
HitBoxFinder's bounded shape list contains named ShapeData records; each Double
and Vector3 field joins its own native child proof. BlackboardVector3 uses
three nullable, variable-width BlackboardDouble children, not a fixed raw
coordinate triple. Its value reader is shared with EffectAction. InFight's
zero-member finder is separately proved. Successful cursor traversal alone
does not supply any of these names, and unsupported finder or nested direction
target variants still refuse complete root admission.

`memorypack/buff_attribute_modifier.py` and its own reviewed native contract
own the reusable AttributeModifierData collection/element grammar. It separates
null collection, null array, null elements and null BlackboardDouble params;
the terminal collection byte is still consumed after null or empty arrays.
The selected empty-condition route consumes this shared owner while preserving
its original complete receipt. Parameter, enum and flag values are stored
data, without attribute evaluation or live formatter selection.

The root's one-DataPair and GlobalModifier co-occurrence restrictions were
historical candidate filters, not native presence rules. The native-gated
bounded DataPair reader and complete forward root admit larger lists without
changing the wire grammar. Every promoted root still needs all thirty fields,
source-ID equality and EOF. `memorypack/buff_residual_census.py` excludes exact
roots before ranking unresolved child obligations and counts unique sources;
overlapping completed-action cohorts do not predict complete root closures.
It counts authenticated per-file exact flags and cross-checks total, exact and
residual counts against the canonical registry. A family summary may omit the
aggregate exact counter; when present it must agree with the per-file count.

The census's `--replay-shared-events` mode distinguishes that recorded baseline
from the newer shared event-map reader. It rereads only unresolved eligible
roots, rejoins their logical bytes, and authenticates current root/event native
inputs and the contributing reader/contract closure before and after the run.
Already exact roots remain excluded. A receipt must still cover thirty
contiguous fields, the source-ID join and physical EOF; this diagnostic never
publishes coverage. The ordinary null-event candidate filter cannot assess
event-bearing residuals, and event-map eligibility alone does not close them.
Composing proved children can close additional roots; residual refusals still
reach unsupported action dispatch and nested finder/selector interiors. Those
are typed child obligations, not a reason to loosen the parent or infer action
behavior.
Its first-stop cohorts normalize byte positions while retaining union tags and
raw per-source diagnostics. They rank unique sources sharing the first reached
gap, not all future gaps or predicted closures. Generated counts and examples
belong in the census report; complete-family admission and canonical original-
byte replay remain the publication boundary.

`memorypack/buff_selected_roots.py` owns their complete-family admission and
canonical export replay. It requires the exact reviewed logical path, length
and SHA, current root and child native gates, all 30 contiguous named fields,
source-ID equality and physical EOF. The positive-heal route also authenticates
its existing selected native audit. Helper source closure, contracts contributing
to dispatcher comparison, the audit and all three native inputs are pinned and
rechecked before and after the corpus scan and registry replay. Each source has
one exclusive cohort; a different source or changed bytes receive no admission.
The standalone selected child/root diagnostics keep `selectedOnly` and
`publicationEligible: false`; only a complete authenticated Buff family report
can supply a row for registry `schema_decoded` after fresh original-byte replay.
Other unsupported nested interiors remain partial. Raw query, enum, event,
priority and scalar bits do not prove live
healing, modifier arithmetic, event execution or formatter-provider selection.

The complete Buff family gate admits these sources after current dependency
and native validation. Registry publication additionally requires canonical
export replay; the standalone diagnostics never supply that publication.

## SkillData

SkillData is one 48-member object: field 0 `ActionGroupData`, fields 1-42
read by a sequential reader derived from the generated wrapper types, and a
five-member terminal (fields 43-47). A gated immediate-registration site joins
the Core `ReadValue<T>` key to `GenericMemoryPackFormatter`. That is static
adapter identity, not executed registration or active dispatch
(`scripts/game_data/il2cpp/context_audit_skilldata.py`). Framing admission
climbs from exact action extent to timeline record, whole ActionGroup, then
whole file (fields 1-42 plus the selected terminal at physical EOF). A lower
rung never counts as a higher one.

The family report's legacy `wholeSchemaExact` flag and corresponding coverage
tokens describe top-level framing and EOF, not recursively named interiors.
`jsondata_corpus` retains that source flag as `familyWholeSchemaExact`,
publishes `storedFrameExact` separately, and keeps `namedSchemaStatus=unproved`
until an owning reader supplies complete recursive naming evidence. Anonymous
nested ranges and records carrying only a type, tag and extent remain
structural. Some compact profiles discard child receipts, so absence of an
anonymous marker is not affirmative named-schema proof. Known fields and
accepted frame evidence remain available; this correction requires no repeat
capture of an already authenticated terminal.

Per-tag layouts live in code, one reader per route:
`scripts/game_data/memorypack/skill_timeline_*.py` for actions,
`skill_selector_*.py` for nested selectors (their own switch tables), and
`skill_timeline_shared_sequence.py`, whose composite contract also admits
routes reused from reviewed Buff readers. Reviewed source routes pin the
dispatcher, reader body, source calls and generic contexts; declaration-derived
routes retain their weaker framing evidence. Readers check
every reached union tag and member-count byte. Nested children
(`skill_selector_postprocessor_convert_to_slot`, `skill_selector_zero_member`
-- where `FF` is not a zero header -- `skill_damage_unit_gameplay_tag_list`,
`skill_timeline_two_*`) are admitted only where reached. All of it is stored
framing only. Gate: `python -m scripts.game_data.memorypack.skill_corpus`.

`skill_timeline_recursive_actions` composes RepeatAction from the reviewed
BlackboardInt and SequenceActionData children. SetMultiTimesWeakness adds
BlackboardDouble and a nullable list of that child to the same Int/sequence
grammar. BlackboardDouble's stored scalar occupies four bytes despite its
type name; the reader preserves arbitrary scalar bits, including nonfinite
values, and distinguishes null, empty and positive lists. These recursive
routes use the ordinary shared sequence bounds and unknown-child refusals,
without source-name exceptions.

Their native join checks the exact typed MethodSpec/context operands and the
reviewed shared-consumer RGCTX propagation. These direct shared consumers do
not have closed-type entries in the generic-method pointer table; an absent
entry cannot establish a different child or a concrete provider selection.
The contract establishes stored read order and child boundaries. Formatter
replacement, runtime repetition and weakness-effect execution remain separate
questions, and whole-file admission still needs the complete family gate and
the existing source-bound terminal evidence.

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

The reviewed target-set capture and positive control are complete and
loss-free. Every witnessed source reads the earlier one-member terminal:
field 43 `switchToCenterBeforeCast` through field 47 `useAIExclusiveFrame` at
physical EOF. The prior complete sweep promoted that selected set; later
sparse checks do not replace a current complete family gate.

A cursor selects positions for one exact logical source: terminal candidate,
field vector and ActionGroup child checkpoints (`skill_cursor_receipt`). It
cannot name an unparsed populated child, choose a formatter/provider/cache,
show a gameplay branch, or give action semantics. Purrche's authored parent
places the base combo ability-range source in the fail branch of
`potential_3 >= 1`; the below-Potential-3 branch was unavailable on the user's
save. Its storage and native logic are recovered, execution is unobserved,
and preloading can explain a deserialization witness.

Capture reuse is source scoped. `skill_cursor_capture_target_set
--rebind-current-corpus` checks current logical path, length, hashes, copied
bytes, native reader/callsite vectors and loss-free transport before retaining
a historical selection. It preserves the historical observer fingerprint and
requires the captured vectors to equal the selected native vectors. An
exporter fingerprint change is not a new observation. Sparse reports remain
nonpublishable; a changed parser fingerprint must be revalidated rather than
silently carried forward.

The original empty/passive/timeline family controls have unchanged-source
cursor replays. `skill_sparse_corpus_compose` can compose selected diagnostics
with frozen controls only after proving the admitted parser/contract delta
and that the controls do not reach it. A diagnostic's large `missingOld`
count describes rows outside its selection, not deleted installed sources.
A frozen complete-report rebind additionally needs current VFS chunk selection
and fingerprints; logical hashes stored in an old report alone are insufficient.

Selected-source joins beyond the original target set:

| Scope | Reusable proof owner | Current boundary |
| --- | --- | --- |
| Mifu | selected SnapPointFinder and `skill_timeline_check_skill_has_hit` | CheckSkillHasHit is admitted by the shared native gate; its ActionGroup closes in focused replay. The complete family gate and source-bound terminal evidence decide whole-file publication. No duplicate framing capture is needed. |
| Lbshamman / Agtrinit and other admitted routes | `skill_timeline_shared_sequence` and each route's native contract | Source-scoped replays close or advance under the shared reader. The code/contract inventory owns the route list; the family report owns publication. |
| Wulfa | `skill_cursor_wulfa_scope`, `skill_cursor_wulfa_terminal` | The separate native-gated cursor joins one whole stored source; no gameplay transition is inferred. |
| Seraph | `skill_cursor_seraph_capture`, `skill_cursor_seraph_terminal` | The separate cursor and independent ActionGroup reader join one whole stored source; no live action semantics are inferred. |
| Zhuangfy | `skill_cursor_zhuangfy_group_join` and source-specific joins | The grouped receipt and independently checked child readers close the selected stored sources. Five routes are admitted to the shared reader; saved earlier joins remain historical where parser provenance changed. |
| Lizhiyan combo / Pograni ultimate | `skill_cursor_lizhiyan_pograni_join`, `skill_cursor_lizhiyan_pograni_terminal_selection.json` | The loss-free grouped receipt names fields 43-47; static ActionGroup and fields 0-42 match every executed cursor and reach EOF in both selected sources. |

For Lizhiyan/Pograni, the reviewed context joins their separate one-source VFS
reports and copied-source identities. SetIgnoreGlobalTimeScale now joins the
shared reader through its own selected-build native gate, as do CheckSkillHasHit
and DispelAction. The composite contract references each domain contract and
checks its tag, member count and source-read declaration before admission.
Missing, mismatched or drifted native evidence refuses the route. Focused
ActionGroup closure does not replace the complete family gate or a source-bound
terminal selection. Both witnessed whole stored-record conclusions need no
further capture; changed parser provenance requires a current corpus basis and
offline receipt revalidation before publication.
The shared Skill reader also admits reusable Buff-owned action grammars only
after the Skill dispatcher, wrapper, read order and nested type contexts agree
with each owner's reviewed contract. Numeric tag equality alone is never an
admission. CheckPartTagMatch's TargetSettings is followed by the value-type
GameplayTagQuery, not a reference wrapper. Historical source-bound terminal
selections can be reused after current parser/source revalidation; adding these
stored action readers needs no duplicate live framing observation.
The earlier static one-byte-later terminal alternatives are superseded for
these witnessed sources only. Stored flags, keys, masks, movement and action
operands establish no gameplay execution, timing, target choice or final value.

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

The shared LevelScript reader now admits `GetClientMapVar` and
`GetSquadInFight` through the generic per-route Deserialize validator and
their reviewed contracts. Selected complete owners rejoin physical EOF after
those getter nodes. The map-variable getter stores an authored key and a
nonconstant map-ID Param selection; it does not supply a current map or live
variable value. The squad getter stores only inherited node fields, not an
authored combat-state result. Whole-owner publication still requires the
authenticated combined JsonData gate. The mount-point getter now uses the same
generated-reader proof, including its separately checked enum backing type;
stored entity and position operands remain unevaluated.

The stored-route contract now extends this pattern across multi-file action
and getter cohorts: full native reader fragments and exact typed calls admit
existing Param, list, mask and blackboard codecs without changing their child
grammars. Enum Params additionally require a selected-metadata backing-type
proof; missing or wrong declarations fail closed with a named diagnostic.
Nonconstant getter slots remain stored operands, not evaluated values.
Derivation must reproduce the resulting declarations; source-span
replay measures route admission, and the sequential owner separately measures
EOF or the next refusal. Recovering a cinematic, NPC or arithmetic node never
establishes its live execution, result or mission ordering. Current route lists
and source spans belong in the reviewed contract, with corpus deltas in reports.

Plain collection fields additionally require their own typed `ReadPackable`
join. The stored-route contract's collection-aware version authenticates the
integer switch's exact `List<int>` argument, default list allocation and
registration key, concrete list and primitive formatter identities, complete
generic context slots and native read windows. Its stored count is signed
Int32 with the null-list sentinel; positive elements use the reviewed Int32
grammar. Replaying positive lists does not replace that parent/child proof,
and native object layout does not determine serialized width. The shared
formatter checker exposes the same generic-context validation to wrapper and
collection compositions. Live provider replacement remains unresolved.

Environment-talk wrappers now carry a complete reviewed default composition
through the shared formatter checker. Their string/Int32 child order and
positive source occurrences alone would not suffice: admission additionally
authenticates the typed parent and list contexts, registered adapters and
concrete formatter/conversion identities. Keep that standard for every new
parent/child composition, independently of live provider history.

The canonical JsonData report retains the complete LevelScript reader detail.
Data may reuse that result only when the versioned reader-input receipt also
matches a fresh, complete path enumeration and byte snapshot. That scope covers
the raw-format package, external shared imports and the native metadata/mapper
helpers; a saved dependency path list or the narrower development cache closure
cannot establish admission. Canonical start/end snapshots must match, and Data
rechecks the selected native/source receipt, full ledger fingerprint, complete
LevelScript source path set and every source length/hash before and after its
projection. Detail payloads remain unchanged, including their Json-relative
refusal locators; the outer Data source descriptor retains the full export path.
Missing, old or changed receipts invoke the maintained direct reader and bypass
the older page cache. Native-input failure makes the dataset unavailable before
either path. Receipt reuse does not promote partial owners or runtime meaning.

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

- A one-byte-later terminal for sources whose executed cursors select the
  earlier one; treating the ordinary formatter/provider profile as an observed
  runtime selection; EOF validity or another source's witness as a terminal
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

- **BuffData.** Recover shared event-action children and compose already proved
  root fields before adding source-specific exceptions. Other positive
  `attributeModifier` and `healModifier` processor interiors; remaining action
  parents, selector finders and nested direction targets; timeline and
  `stackEffects` interiors; string encoding remain open. Rank distinct residual
  sources after excluding complete roots. Separate recursive child refusals
  from a missing whole-root receipt; overlapping child reach does not predict
  complete-root admission. Every composition still needs all root fields,
  source-ID equality, physical EOF and the complete family/registry gates.
- **LevelScript.** The gate rerun, first-stop leaders and route integration
  follow Buff in the queue;
  [`levelscript_first_stop_census.py`](../../scripts/game_data/levelscript_first_stop_census.py)
  reruns the owner over the JsonData receipt's partial files and ranks first
  stops by whole files. Unsupported values: positive
  `GameplayTag`/`BuffPtr`
  list elements, non-null `CameraControllerBase` and target-script values,
  non-constant patrol `EntityPtr`, positive dynamic AI blackboards, camera
  configurations and curve keys without reviewed parent routes;
  `SendLuaEvent2` is unobserved; partial templates stop
  at unreviewed unions.
- **SkillData.** Remaining framing failures involve unreviewed action parents
  or typed children, positive `EffectActionCfg` arrays and a remaining selector
  postprocessor. Use the current family report's first refusal to select the
  next shared reader. Separately, complete frames still need recursively named
  child evidence, including children omitted by the common top-level
  continuation receipt. A terminal proof cannot name an earlier interior.
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

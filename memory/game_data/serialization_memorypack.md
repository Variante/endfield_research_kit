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
terminal state (vocabulary in its docstring). The last retained complete gate
authenticated its selected corpus with no unsupported or unclassified
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
The static parser closure follows repository imports across lane boundaries,
including IL2CPP helpers, per-module relative imports and package initializers.
Explicitly loaded external metadata/mapper helpers still need their owning
validator's source snapshots; this closure cannot discover dynamic loading.
Do not repair a provenance mismatch by editing receipt pins or repeating a
capture.

A rewritten outer VFS catalog invalidates its source fingerprint even when
the selected native build and Buff logical bytes still agree. Rerun the full
AnimeStudio VFS audit, compare the current logical identities and bytes, then
run the complete Buff family gate against the new audit. A previous JsonData
registry remains stale until its own complete gate succeeds. Current Buff
family admission and selected canonical Buff replay can retain independent
evidence without relabeling that older registry as current or weakening an
unrelated family's required primary receipt.

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
During that run, freeze every `.py` and `.json` under `scripts/game_data/`,
including consumer contracts and census tools outside the active Buff import
closure. The complete LevelScript scope protects these negative dependencies
too; checking only the current family's imported files is insufficient. Keep
independent probes and their output outside the package until the run finishes.

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
CheckSkillType, CheckObtainAtbType, CheckBuffStackNum and InterruptAction compose independently typed lists, BuffId values, blackboards and targets through [their named reader](../../scripts/game_data/memorypack/buff_skill_stack_interrupt_actions.py). CheckObtainAtbType retains separate `checkObtainMethod` and `checkObtainType` flags and separate nullable lists of GainAtbMethod and GainAtbType. Named formatter-to-setter transfers, closed list element types and independent four-byte source witnesses establish storage. Null, empty and populated lists remain distinct; stored flags and enum bits do not establish the evaluated ATB event or condition result.

The same domain owns SetSkillCdAtOnce and SwitchModeAction. The cooldown
record retains its function, percentage flag, skill ID, type mask, target,
type-selection flag and BlackboardDouble operand independently. The mode
record retains its mode ID and independent start/end interruption and reset
flags. Reviewed source calls and runtime destinations prove this order;
the target and scalar children must close on their original spans. Storage
does not establish cooldown arithmetic, the selected skill, mode transition
or interrupt/reset execution.

[`animation_curve.py`](../../scripts/game_data/memorypack/animation_curve.py)
owns the shared named AnimationCurve value reader, independently of any
action that first exposed it. Its
[`native contract`](../../scripts/game_data/contracts/memorypack_animation_curve_native.json)
joins two source DWORDs to separately named pre/post wrap-mode resolution
caches. A closed Keyframe array allocation, index-times-stride instruction,
source loads, cursor accounting and actual typed array-field stores name
each keyframe's time, value, in/out tangents, weighted mode and in/out
weights. Native structure size corroborates those copies; it does not by
itself prove the wire grammar. Original floating-point and enum bits remain
intact. A null curve, null key array, empty key array and populated key
array retain distinct receipts. Each parent must independently prove its
typed curve field and original bounded span. Callback-name bindings do not
establish callback execution, evaluated interpolation or game effects.

[`buff_curve_actions.py`](../../scripts/game_data/memorypack/buff_curve_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_curve_actions_native.json)
compose TimeDilationAction and EnemyHurtAnimAction. Time dilation retains
independent effect/ignore target lists, BlackboardDouble duration and skill
cooldown operand, layer, slot/priority tags, curve and curve-key flags.
Enemy hurt retains separate attacker/defender, distance curve, direction,
BlackboardImpactValue and pushback/transition/immobilization providers,
alongside its stored animation, shake and scale flags. Every nested value
must independently close on its original span; positive direction targets
without recursive evidence still refuse this parent. The shared impact
reader now exposes a source-bound provider value without reusing a
SetSuperArmorAction parent receipt as authority for another action. Stored
names establish neither the selected live targets nor time scaling,
cooldown changes, hurt animation, displacement or armor effects. Complete
root and canonical registry gates still govern coverage admission.

The same curve owner separately joins HitStopAction's source order and
destinations. `attacker` and `target` are independent TargetSettings children;
`directCurve` has its own AnimationCurve receipt, while `curveKey` retains
nullable raw bytes. The plain floating-point duration, affect type, curve
selection flag and GameplayTag priority retain their original bits. The tag's
closed unmanaged source entry, actual DWORD read, cursor advance and returned
value must agree; a four-byte native type size is insufficient. Stored curve
choices do not establish which curve reaches StartHitStop or its evaluated
duration and affected entities.

The curve owner also independently joins CharHurtAnimAction's own source
order and destinations. Its attacker and defender targets, distance curve,
DirectionSettings and BlackboardDouble push-back operand retain separate
original-span receipts. Raw animation enum, armor limit and custom flags
remain uninterpreted. A direction profile closes here only when its nested
targets are independently exact nulls; a positive nested target leaves the
parent open. Stored curve, direction and distance values do not establish
hurt animation, facing, displacement or selected entities.

[`buff_marker_mask_actions.py`](../../scripts/game_data/memorypack/buff_marker_mask_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_marker_mask_actions_native.json)
compose CreateTimedMarker, CheckTagMatch, CheckObjectTypeMatch and
CheckPhysicalInflictionType and CheckSpellInflictionType. The marker retains independent duration,
BlackboardString ID, target and finish/time-dilation flags. The conditions
retain independent target/query, object-type mask, or physical-infliction
mask and nullable stored key. Every provider, target and query requires its
same-build child receipt on the original span. Raw enum, flag and payload
bits stay intact; storage does not establish marker registration, expiration,
selected entities, mask/query evaluation or predicate results.

CheckSpellInflictionType independently owns its stored enum mask and
nullable raw saved-key payload. The source's payload-kind spelling remains
part of the reviewed read order. A key name or mask does not establish the
state queried, bit-test result or condition outcome.

CheckTagMatch's query illustrates a second source-transfer shape. The typed
ReadValue context passes a hidden stack output pointer and the reader; only
after that call does an instance getter supply the runtime destination.
The complete intervening program reloads that same stack value and copies
its full runtime extent into the independently named field. The explicit
`providerOutputSource` check authenticates argument order, getter identity
and return type, runtime value extent, contiguous stack transfer and field
copy. This value contains a managed reference: the runtime copy extent is
not a raw wire length, and the independent GameplayTagQuery reader still
owns its serialized grammar. A nearest-call scan would mistake the getter
for the source. This proof does not equate the optimized target with a
distinct registered generic entry or establish live provider selection.

GameplayTag adds an object-identity boundary to named field recovery. It is
a value type stored inline in a generated class wrapper. Its actual reader
receives the wrapper by reference, aliases that argument, dereferences it and
preserves the resulting receiver through the scalar store. The
[`Aura/Heal child contract`](../../scripts/game_data/contracts/buff_aura_heal_actions_native.json)
records this complete normal program. `named_native_records` authenticates
the reader's two reference parameters, instance-field declaration and native
offset, then projects each boxed member offset into the wrapper's inline
value. Equal numerical offsets on the boxed type and wrapper are insufficient
without that receiver proof. The generated tag element retains its member
header; a nullable list of these elements is distinct from both a
GameplayTagList object and an unframed DWORD array.

[`buff_tag_sequence_actions.py`](../../scripts/game_data/memorypack/buff_tag_sequence_actions.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_tag_sequence_actions_native.json)
compose AddTagAction's BlackboardString, target and direct GameplayTag list,
and ForEachAction's SequenceActionData and target. Parent fields independently
prove their closed source types before using the shared children.
[`buff_sequence.py`](../../scripts/game_data/memorypack/buff_sequence.py)
owns the common sequence proof and recursive value reader below event maps
and action parents. Its declaration remains once in the shared-event
contract. Every positive action must close on its own original span; null
wrappers, null/empty action arrays and null elements stay distinct. The two
terminal flag bytes remain stored values, without inferring iteration order,
guard selection, tag attachment or action execution.

[`buff_spawn_entity_action.py`](../../scripts/game_data/memorypack/buff_spawn_entity_action.py)
and its
[`parent contract`](../../scripts/game_data/contracts/buff_spawn_entity_action_native.json)
compose SpawnAbilityEntity's complete named parent with independently proved
targets, direction targets, Blackboard duration, assignment elements and
nullable string lists. Its Vector3 field uses an actual typed unmanaged
return-buffer call before an independently identified wrapper getter.
[`struct_output_sources.py`](../../scripts/game_data/memorypack/struct_output_sources.py)
proves the direct reader and distinct registered reader separately: both
copy eight plus four source bytes and account for twelve consumed bytes.
The complete caller transfer reloads that same temporary and authenticates
both runtime stores. Quaternion instead copies sixteen bytes inline from
the parent reader, updates its stored cursor slots and copies the same
temporary into the complete destination field. Both paths require an
authenticated normal prefix preserving the reader and wrapper-reference
argument aliases. Runtime extent alone proves neither wire read. Stored
names and flags do not establish evaluated strings, entity creation,
ownership, navigation selection, rotation evaluation or lifetime; native
short-segment/provider selection remains outside these normal-path proofs.

[`buff_launch_projectile_action.py`](../../scripts/game_data/memorypack/buff_launch_projectile_action.py)
and its [named contract](../../scripts/game_data/contracts/buff_launch_projectile_action_native.json)
compose LaunchProjectile's complete stored parent with four independently
proved inline Vector3 transfers. Each source/cursor/temporary/destination
program owns its register profile, reader-argument restoration and complete
field stores; a nearby call or runtime extent cannot substitute for it.
PresetPointDef's target and nullable key have their own named read order,
while assignment elements use the independent AssignPair owner. Null wrappers,
null/empty lists and null elements remain distinct, and mandatory later
fields still have to close. Vector and scalar bits remain raw. This storage
proof does not establish emitted entities, trajectories, preset selection,
weapon calculations or projectile delivery.

[`buff_camera_impulse_action.py`](../../scripts/game_data/memorypack/buff_camera_impulse_action.py)
and its [named contract](../../scripts/game_data/contracts/buff_camera_impulse_action_native.json)
compose CameraImpulseAction, its ImpulseDefinitionData and the inline
EnvelopeDefinition wrapper, with independently typed AnimationCurve and
TargetSettings children. The parent's Vector3 is an inline eight-plus-four
source copy: its complete cursor program advances twelve, reloads the same
stack temporary and preserved remaining word, and writes both destination
parts. It does not use SpawnAbilityEntity's unmanaged return-buffer route.
The envelope instead arrives through a typed ReadValue result buffer. The
selected helper zeroes and forwards a thirty-two-byte output to provider
dispatch, then returns that buffer; the parent copies both sixteen-byte
halves into its independently named runtime field. Runtime output extent
does not establish serialized wire width or live formatter selection.
[`value_wrapper_sources.py`](../../scripts/game_data/memorypack/value_wrapper_sources.py)
independently projects each envelope member from the exact wrapper-reference
argument and actual inline instance field. Its complete normal program
preserves the incoming reader, requires the curve type context to reach the
source argument, and follows each returned reference, float or byte to its
named destination. Boxed field-offset coincidence, a partial store, a
clobbered alias or an unrecognized instruction cannot supply that proof.
Null stored wrappers remain distinct from evaluated runtime values. Curves,
flags, mount points and signal paths establish stored configuration; curve
evaluation, signal resolution, impulse creation, camera ownership and screen
motion remain open. Complete Buff admission still requires the family gate
and canonical original-byte root replay.

[`buff_leaf_actions.py`](../../scripts/game_data/memorypack/buff_leaf_actions.py)
and its [named contract](../../scripts/game_data/contracts/buff_leaf_actions_native.json)
separately admit NotNextCheckAction's four inherited action fields in recursive
sequences. The selected source reader and generated setter order contain no
fifth stored member or recursive child; this reusable action receipt removes
the earlier restriction to one specific damage-condition pair. The union uses
its proved extended encoding, including null wrappers. A plain reserved lead
byte, wrong member count, truncated scalar or trailing bytes cannot close the
action. Raw enable, priority and server-index bits establish storage. They do
not establish a no-op, a returned condition result, next-check suppression,
sequence ordering or gameplay execution.

The same nonrecursive reader and its versioned contract also name
PauseBuffTime's inherited prefix plus `isPaused`, and
OnSpellAbnormalStartFinish's inherited prefix plus `abnormalType` and
`isStart`. The latter's serialized member order differs from its runtime
field placement; generated setters, actual source calls and selected runtime
fields must be joined independently. Only byte and scalar suffixes belong to
this reader. Raw values and exact null-wrapper states do not establish pause
transitions, abnormal-event delivery or evaluated enum meaning.

RefreshBuffAttrModifierValue independently uses the same inherited-only leaf
shape and its own extended union tag. Its stored fields do not establish a
no-op or an attribute update; the named consumer is a separate obligation.

[`buff_keyword_actions.py`](../../scripts/game_data/memorypack/buff_keyword_actions.py)
and its [contract](../../scripts/game_data/contracts/buff_keyword_actions_native.json)
join VulnerableAction, ShelterAction, SlowAction, SpeedupAction, WeakAction,
EnhancedAction and SpellInflictionOnChar to their independent source orders
and actual destinations. The keyword parents separately prove their common
fields; the subtype parents retain an additional required enum word. The
minimum list suffix is derived from each proved subsequent storage field,
rather than borrowing the subtype parent's larger tail. VulnerableAction retains inherited keyword
fields, BlackboardString child ID, separate duration/rate providers, two
targets and subtype. Its KeywordEnhanceEdit elements separately own `buffIds`,
`operationType` and `value`. Nullable raw string lists, null edit wrappers,
null/empty outer lists and positive elements remain distinct; the parent's
required suffix still follows the list. SpellInflictionOnChar retains plain
count/type/immune-level values, a nullable stored blackboard key, separate
source/target and raw flags. Every provider and target receipt must close its
own original range. These grammars do not calculate keyword edits, choose a
count source, consume/add a live Buff or deliver an infliction event.

SpellInfliction has a separate stored parent from SpellInflictionOnChar.
Its energy-shard enum and raw extra flag precede independent source and
target profiles. Each target still requires its own same-build receipt on
its original extent. The shorter stored layout does not borrow the other
action's counts, immunity or trigger fields, and does not establish actual
infliction or the selected entities.

The [data-transfer owner](../../scripts/game_data/memorypack/buff_data_transfer_actions.py)
separately names GetAITransDataAction's `aiTransKey` and `saveTo` payloads.
Null and empty keys remain distinct, arbitrary payload bytes are preserved,
and the second signed length remains mandatory. The grammar does not prove
an AI transfer lookup, its returned value or a Blackboard save.

[`buff_global_creation_action.py`](../../scripts/game_data/memorypack/buff_global_creation_action.py)
and its [contract](../../scripts/game_data/contracts/buff_global_creation_action_native.json)
name CreateGlobalBuffAction's count, creation-finish flag, GlobalBuffInput
list and independent source target. Each GlobalBuffInput independently
names its assignment flag, AssignPair list and GlobalBuffId. The selected
inline-value proof follows the reader argument, wrapper reference and
address of GlobalBuffId's own `id` field through the complete string return
and reference store. Its in-memory reference extent does not change its
length-prefixed serialized bytes. Null wrapper, null string, empty string
and null/empty list remain distinct; evaluated counts, assignment execution
and actual global Buff creation or finish require consumer evidence.

[`buff_switch_action.py`](../../scripts/game_data/memorypack/buff_switch_action.py)
and its [contract](../../scripts/game_data/contracts/buff_switch_action_native.json)
separately name SwitchAction's `alwaysNext`, BlackboardDouble `choice` and
nullable Option list. Each Option owns `actionData` as SequenceActionData
and `value` as BlackboardDouble. Every reached sequence must recursively
prove its original action ranges; unsupported actions and excessive nesting
refuse the parent. The grammar does not evaluate choice or select an Option.

The [skill/stack owner](../../scripts/game_data/memorypack/buff_skill_stack_interrupt_actions.py)
separately names SetBuffDurationAction's BuffFindSettings, early-finish flag,
operation enum, target and BlackboardDouble value. BuffFindSettings and its
tag query use their independently authenticated child reader. The enum's
declaring type is ModifyDynamicBlackboard's OperationType; this remains a
SetBuffDurationAction record. Stored operands do not determine lifetime
arithmetic, selected Buff handles or accepted writes.

[`buff_ignite_text_action.py`](../../scripts/game_data/memorypack/buff_ignite_text_action.py)
and its [contract](../../scripts/game_data/contracts/buff_ignite_text_action_native.json)
own IgniteBuffTextAction's complete stored parent, including its raw
Vector2 offset, flags, enums, independent TargetSettings and final nullable
text payload. Its eight-byte source proof is separate from the DWORD
unmanaged reader and from a runtime-size inference. The actual helper reads
two Float32 words, advances eight bytes and packs their unchanged bits into
RAX. The selected generic registration independently proves a second entry
and its cursor helper. The parent forwards the full RAX value as RDX to its
own wrapper setter; that setter saves the argument, obtains the typed Data
reference and writes both words at the independently selected field offset.
The getter's normal program returns its own typed `__realInstance`, after
its reference checks. Full instruction boundaries, current windows, argument
aliases, closed type, cursor fields, word order and both destination stores
are separate gates. A raw eight-byte member without this explicit proof
fails closed. These are selected normal-path byte and ownership proofs;
slow/error behavior stays within the source formatter's existing boundary.
They do not establish evaluated offsets, energy effects, displayed text,
live provider selection or action execution.

The [marker/condition contract](../../scripts/game_data/contracts/buff_marker_mask_actions_native.json)
separately names CheckTargetsEqual's two TargetSettings source children.
Both must close on their own original ranges; matching bytes or a successful
receipt for the other target cannot stand in for that child. The
[skill/stack/interrupt contract](../../scripts/game_data/contracts/buff_skill_stack_interrupt_actions_native.json)
independently names InterruptCurSkillAction's single `skillOwner` target.
It also separately names RecoverLockOnEndIfNoLockAction's target after the
common AbilityActionData fields. That stored target, its null state and
original span do not prove lock-on recovery or a selected entity.
That family's reader now checks original child extents for targets, BuffId
values, blackboard operands and counted scalar lists, alongside current native
dependencies. The source window's null wrapper is separate from a non-null
wrapper with null target children; neither accepts a trailing byte.

[`buff_super_armor_condition.py`](../../scripts/game_data/memorypack/buff_super_armor_condition.py)
owns CheckSuperArmor's named target, comparison and BlackboardDouble operand.
Its independently typed child joins establish stored comparison inputs,
not a live entity's armor value or the evaluated predicate.

[`buff_debug_print_action.py`](../../scripts/game_data/memorypack/buff_debug_print_action.py)
owns DebugPrintAction's nullable `bbKey` and `identifier`, inline `color`,
`logType` and independent target. Color has no nested source MethodSpec in
this reader: the parent copies sixteen source bytes to a stack temporary,
explicitly advances sixteen, then copies that same temporary into the
runtime field. The named contract independently authenticates the source
pointer load, both complete copies, cursor helper, exact intervening bytes
and field destination. `named_native_records` admits this only through an
explicit `inlineSource` proof and selected unmanaged extent; it does not
waive the typed-context requirement for arbitrary object fields. Raw color
bits, stored strings and enum values do not establish rendered color or log
output. Short-segment/refill parity remains outside the normal-path proof.

[`buff_selector_distance_validator.py`](../../scripts/game_data/memorypack/buff_selector_distance_validator.py) owns the selector's DistanceValidator child. Its named contract proves the selected union branch and the stored `clampToXZ`, `compareType` and BlackboardDouble `value` fields. The shared selector-list reader composes that child on the original span, including a null wrapper; the scalar provider must have an independently exact boundary. This establishes stored distance operands. Live entity positions, projection, provider evaluation and predicate results remain unresolved. Whole Buff coverage still requires the root reader's contiguous thirty-field receipt and physical EOF, followed by the complete-family and canonical JsonData gates.

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

The same data-transfer domain also owns GetTargetBuffBBAdvanced and
StoreAttributeValue. The former keeps its output `blackboardKey`, requested
`desiredKey`, Buff finder and target in separate original-byte spans. The latter
keeps `baseValue`, `divisorValue` and `multiplierValue` as independent providers,
alongside the attribute selectors, output key, target and `useFloor`. These
stored names do not establish live arithmetic or the value written.
It also owns SaveBuffStackNumAdvanced and SimpleCalcBBAction. SaveBuffStackNumAdvanced
keeps its Buff finder, `buffStackNumType`, checked target, output `key` and
`limitSkillCastId` flag in independently proved spans. SimpleCalcBBAction keeps
its output key, operation and two BlackboardDouble operands separate. The
selected native readers prove those source reads and destinations; the finder,
target and provider children must independently close on the original bytes.
Stored selectors and operands do not establish the selected Buff, live stack
count, calculation result or blackboard assignment.

[`buff_timed_marker_condition.py`](../../scripts/game_data/memorypack/buff_timed_marker_condition.py)
owns CheckTimedMarkerCondition's named stored parent. Its marker `id` and
`blackboardKey` remain separate nullable byte payloads; `checkTarget` has its
own exact typed child, and `returnTrueIfNotExists` and `useBlackboardKey` retain
their stored flag bits. Source-to-setter transfers establish the parent layout.
They do not establish marker existence, evaluated key selection or predicate
results. Unsupported target children still refuse the parent composition.

[`buff_probability_action.py`](../../scripts/game_data/memorypack/buff_probability_action.py)
owns Conditions.Probablity, retaining the client's spelling. Its probability
provider has its own exact child boundary; stored probability is distinct from
the evaluated input, random source and decision.

[`buff_entity_count_action.py`](../../scripts/game_data/memorypack/buff_entity_count_action.py)
owns the general shared-event CheckEntityNum parent, separate from the earlier
source-bound positive-damage receipt. Its reviewed contract proves all ten
source reads and their actual runtime-field destinations. `minNum` is a plain
stored integer; `checkTarget` is a separately typed TargetSettings child.
The comparison and two flags retain their raw values, and `storeKey` retains
nullable bytes. Null targets close directly; positive targets compose their
direction, selector and finder children on the original span. Stored structure
does not establish selected entities, counted entities, the comparison result
or a blackboard write.

[`buff_notify_char_passive_ui_action.py`](../../scripts/game_data/memorypack/buff_notify_char_passive_ui_action.py)
owns NotifyCharPassiveUIAction's six stored fields. Its own native contract
proves the source reads, actual destinations and closed TargetSettings and
BlackboardDouble types. Both children must close on their original byte spans;
null targets and null providers remain distinct. This proves stored `target`
and `value`, without establishing live target selection, evaluated values,
notification delivery or the visible passive indicator.

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

The skill-cooldown consumer group proves active-skill lookup, float-provider
evaluation, the cooldown helper and global-event calls. The helper separately
contains current-timer, period/cooldown and remaining-time reads, plus both
remaining-time update sinks. The mode-switch group contains owner lookup and
mode enabling in execution, then base ending and mode-handle disabling in
`OnEnd`. CheckSuperArmor contains target selection and provider evaluation;
its anonymous armor lookup and comparison remain separate unresolved joins.
These claims prove compiled calls, not individual stored field arguments,
selected branches, calculated values, timer changes or restored live modes.

TimeDilationAction has separately re-proved compiled global and entity
start calls, target collection and Blackboard evaluation. Its `OnEnd`
contains a TimeDilationHandle stop call. EnemyHurtAnimAction reaches
first-target and target-list selection, Blackboard evaluation, ordinary
hurt animation, back-swing hurt handling and additive animation sinks.
These consumer groups remain independent of the exact stored parent
receipts. They do not establish which effect/ignore list, curve, operand,
attacker/defender or finish flag supplied a live invocation, nor that
the selected IFix path actually executed or changed time/animation state.
The time-dilation end predicate still lacks its stored `finishByAction`
join: its data pointer passes through closed generic action storage whose
instantiated layout has not been proved for this consumer. Matching a
displacement to the nongeneric Data field does not establish that pointer's
ownership. Keep this separate from the already proved stop-call presence.

CreateTimedMarker's compiled body/helper paths contain target collection,
Blackboard evaluation and `AddTimedMarker`; its end path contains
`TimedMarker.Remove`. CheckTagMatch contains target-view selection,
part-source resolution and `MatchesQuery`. CheckObjectTypeMatch contains
target-view selection and object-type reads. CheckPhysicalInflictionType
contains event-context acquisition and Blackboard reads/assignment. These
claims are re-proved by the same consumer contract. Exact marker operands
and lifetime flags, query/mask argument ownership, target quantifiers,
short-circuit behavior, event variants and evaluated results remain
independent unresolved joins. Call presence does not settle those branches.

AddTagAction's compiled execution paths contain first-target selection,
Blackboard evaluation and Entity.AddTag; its ending contains
MultiTagHandle.RemoveTag. ForEachAction contains target collection/access,
target binding and SequenceAction.ExecuteInstant, with SequenceAction.End
in its ending. SpawnAbilityEntity contains target selection, rotation and
assignment helpers, entity-table lookup, ObjectContainer.SpawnAbilityEntity
and controller initialization; its ending contains entity release, attached
effect pause and target disposal. These independently re-proved calls do not
identify the stored argument values, selected branches, sequence/entity/handle
ownership or actual attachment, execution and cleanup.

CameraImpulseAction's compiled execution contains target collection, node
transform lookup, the camera-shake property and both two-dimensional and
ordinary impulse-start sinks; its ending contains EndImpulse. These named
call claims remain separate from the stored child receipts. Exact impulse
arguments, branch conditions, handle lifetime and camera ownership remain
unresolved.

NotNextCheckAction's `get_executeReturnType` has a narrower proved normal
return in the [consumer claims](../../scripts/game_data/contracts/buff_action_consumers_native.json).
When the selected Boolean IFix guard returns false, it returns the declared
`AlwaysReturnTrue` enum. The
[`constant_returns.py`](../../scripts/game_data/il2cpp/constant_returns.py)
check independently joins the selected method and Int32-backed enum, requires
the actual direct Boolean call and JNE false fallthrough, and proves that the
complete EAX literal survives a contiguous plain epilogue to RET. A literal
load alone, partial return, result clobber, unknown instruction, wrong guard
or branch into the return tail refuses the claim. This property is separate
from ExecuteInternal's result and from the sequence's returned result.
The environment/context getter dispatch, its returned receiver, policy-field
store and later sequence-policy branches still need separate ownership and
flow proofs. The action name does not establish skipped execution or a no-op.

The
[`consumer claims`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
also distinguish receiver-proved reads from an arbitrary field-displacement
match. CheckTagMatch's `checkTarget`, CheckObjectTypeMatch's `objectTypeMask`
and CheckPhysicalInflictionType's `mask` each have a compiled normal-path
read through the incoming instance's closed generic data reference.
[`reference_layouts.py`](../../scripts/game_data/il2cpp/reference_layouts.py)
requires a sole instance reference type parameter, an immediate concrete
witness with no declared instance fields, a fully occupied nongeneric base and exactly one reference
of additional concrete size. Declared fields are counted using their selected
static attributes: static declarations do not occupy the concrete instance,
while any own instance field still refuses this witness. Open generic offsets
and sizes remain excluded.
[`closed_data_fields.py`](../../scripts/game_data/il2cpp/closed_data_fields.py)
then checks body ownership and incoming-instance ABI, follows preserved
receiver/data aliases and joins the read to the actual nongeneric Data field.
Unknown instructions, partial pointer writes, clobbers and wrong owners erase
provenance. This closes selected stored-field reads, without promoting a
later call's argument, mask operation, branch selection or live condition
result. Classes with their own instance fields cannot use the fieldless
witness rule; the time-dilation finish predicate remains a separate layout
and flow gap.

[`cmp_memory_reads.py`](../../scripts/game_data/il2cpp/cmp_memory_reads.py)
also authenticates complete byte/DWORD memory CMP operands against the
selected declared field width, owned data-register base, displacement and
actual opcode bytes. Legacy address/operand prefixes, partial instructions,
unsupported addressing and mismatched text do not qualify. This is a read
claim only: comparison does not supply a value register for reference or byte
argument forwarding, nor does it establish flags or branch selection. Adding
that proof form does not recover candidate fields whose receiver provenance
has already been erased.

The same receiver proof independently reaches CheckTargetsEqual's two target
references and InterruptCurSkillAction's `skillOwner`. PauseBuffTime's
`isPaused` and OnSpellAbnormalStartFinish's `isStart` have complete byte reads
through that owned Data reference. Byte mode authenticates the actual byte
MOV or unsigned-byte MOVZX opcode, complete destination byte, memory base,
displacement and register width; a word read, wrong register/displacement or
partial pointer does not qualify. This preserves the stored byte without
normalizing it or evaluating a condition. OnSpellAbnormalStartFinish's
`abnormalType` ownership remains unproved where unknown instructions interrupt
the pointer chain, even though a later matching displacement is visible.

A small value-type extent alone also does not establish a callee's return
ABI. [Microsoft's x64 calling convention](https://learn.microsoft.com/en-us/cpp/build/x64-calling-convention)
places additional native type requirements on direct aggregate returns.
Selected managed metadata does not by itself prove all those C++ properties.
The reference forwarding mode therefore admits only independently named
reference parameters with direct primitive/reference returns. GetTargetsView's
value-type return still needs an independent entry/register witness before
its stored target field can be certified at the argument position; its call
presence and receiver-proved field read remain separate established claims.

The reference-argument check separately accepts either selected undecorated
String type record, with a complete pointer read and the exact declared
parameter type. Byref, pinned/decorated records and another primitive kind
still refuse forwarding. GetAITransDataAction's owned `aiTransKey` reaches
TryGetAITransData's `key`; its independent `saveTo` reaches
UpdateTargetGroup's `key`. The intervening SetTarget call is a separately
proved compiled sink. This makes `saveTo` a target-group key in this flow;
lookup outcomes, the returned transform/handle, update selection and live
group effects remain unresolved.

An explicitly selected concrete-field suffix provides a second closed
reference layout witness. It requires the same immediate closed generic
parent and sole VAR reference field, and the non-generic base still must
have no trailing padding. Every declared concrete instance field then needs
an independently named scalar or reference extent. Those fields must fill a
continuous suffix beginning immediately after one pointer beyond the base,
with no overlap, internal gap or unproved trailing extent. Static fields
remain separate. Unproved value types, a changed owner, wrong parent, field
count drift or padding fail closed; the original instance-fieldless mode
does not automatically admit this shape. LaunchProjectile's own string
fields satisfy the explicit suffix witness. Its `emitPos`, `projectileId`,
`projectileSource` and `targetSettings` Data reads are then independently
owned; the latter two reach their separately typed selection parameters.
Table lookup, start-position and launch calls remain compiled sinks, with
vector/provider evaluation, spawned objects, skill callbacks and trajectory
or delivery effects unresolved. RecoverLockOnEndIfNoLockAction's declared
ObjectPtr value field does not satisfy this suffix proof. Its execution and
end calls are authenticated without promoting a Data-field or recorded
pointer ownership claim.

Closed generic suffix references require an independent selected reference
class definition, generic owner/arity and complete closed argument identity.
Their argument's representation does not determine the reference width;
ObjectPtr and other generic value types remain excluded. This establishes
the complete concrete suffixes of CreateGlobalBuffAction and SwitchAction.
An explicit closed-generic-reference-field claim can then prove a whole
owned List reference read; generic callee-parameter forwarding stays open.
An explicit normal-forward-jump profile preserves aliases only across exact
local EB/E9 jumps whose byte-derived targets agree with the decoded text and
an instruction boundary in the selected body. Conditional branches keep
the fallthrough choice; external/backward/indirect jumps end this path.
Unknown instructions and partial pointer writes still erase provenance.

An independently selected local-path profile can examine both edges of a
complete local conditional branch. The
[`compiled_paths.py`](../../scripts/game_data/il2cpp/compiled_paths.py)
helper requires contiguous original instruction spans, byte-derived branch
targets and actual in-body instruction boundaries. Paths preserve the same
incoming-instance, named field, ABI and clobber checks; unknown instructions
end that path, loops and enumeration remain bounded, and a refused proof
reports inventory or traversal limits. This establishes a compiled control
flow prefix under unspecified branch outcomes. It does not establish
predicate feasibility, actual branch selection, callee return or effects.

With those explicit witnesses, CreateGlobalBuffAction owns its creation-
finish flag, count, input list and source target. The count reaches the
typed GetValue parameter; the source reaches GetFirstTarget's targetSettings.
SetBuffDurationAction's BuffFindSettings reaches GetBuffFindHandle_Dispose's
buffFindSettings, and its target reaches GetFirstTarget's targetSettings.
Creation, finish and lifetime-write calls remain compiled sinks, with live
handles and effects unresolved. Explicit local paths additionally prove
SetBuffDurationAction's stored operation and early-finish reads, and its
value reference reaches the typed GetValue parameter. Lifetime arithmetic,
finish-reason derivation and accepted writes remain separate obligations.
SwitchAction independently owns its choice and options references; a local
path sends choice to the typed GetValue parameter. Sequence creation,
reassignment, ticking, reset and end calls remain compiled evidence, with
Option-to-live-sequence identity, comparisons and selected results open.
Its return policy is CustomReturnType; global creation and duration actions
separately prove AlwaysReturnTrue policy getters. These getters do not
establish sequence or action results.

SwitchAction's separate Boolean `AlwaysReturnTrue` method has a narrower
owned-byte return proof. After false from the selected Boolean IFix guard,
its non-null owned Data fallthrough loads `alwaysNext` into AL and returns
that byte through a complete unchanged epilogue. The
[`owned_byte_returns.py`](../../scripts/game_data/il2cpp/owned_byte_returns.py)
checker requires the actual nongeneric Boolean caller and guard declarations,
incoming-instance field ownership, complete byte-load instruction and
separate guard/null alternatives. This Boolean method is distinct from
the enum-returning CustomReturnType getter. Live Data assignment, byte
normalization, IFix selection and the caller's use of the Boolean remain
unresolved.

The separately reviewed
[`buff_leaf_actions_native.json`](../../scripts/game_data/contracts/buff_leaf_actions_native.json)
and
[`buff_skill_stack_interrupt_actions_native.json`](../../scripts/game_data/contracts/buff_skill_stack_interrupt_actions_native.json)
name CheckSquadInFight's inversion byte and CheckOriginSkillType's attack
mask plus nullable List of SkillType. The mask reuses CheckSkillType's
declared enum without changing the parent action's identity. The list joins
the independently selected closed element type and four-byte element
reader. Null/empty lists and raw enum bits remain distinct. Native consumers
independently read the inversion byte and stored skill-type list and return
CustomReturnType on their normal false-guard property paths; fight-state
receiver ownership, originating event/skill selection, predicates and
condition results remain unresolved.

[`buff_weapon_visual_action_native.json`](../../scripts/game_data/contracts/buff_weapon_visual_action_native.json)
separately names CharWeaponVisibleAction and WeaponVFXOverrideConfig. The
parent retains include-all, override-VFX, show-VFX, visible and weapon-index
storage with its independently typed VFX child. That child has separate
enable flags and nullable string byte payloads for fight/idle appearance
and disappearance effects. Null wrappers, null strings and empty strings
remain distinct; string reference width does not define wire framing or
decoder parity. Compiled consumers call the single/all weapon-state and
VFX-override methods, with a separately proved CustomReturnType getter.
The concrete action's suffix still fails the strict complete contiguous
layout witness, so no configuration-field-to-rendering-parameter claim is
promoted. Selected weapon receivers, asset binding and actual rendering
effects remain open.

A separate explicit byte-argument mode admits only the sole bool/byte
parameter of a nongeneric reference instance method returning void or bool.
This excludes a hidden result buffer and aggregate parameter placement.
PauseBuffTime's normal branch supplies the complete byte read from its owned
Data `isPaused` field to `Buff.SetPaused.isPaused`; the independently selected
callee declaration and argument register agree. This joins a runtime Data
field to a compiled call argument. It does not prove assignment from a
particular serialized Buff into that Data object, source-byte normalization,
the returned/cast Buff receiver, selected IFix branch or an actual pause
transition.

The independently owned `Buff.SetPaused` body closes the next compiled step.
[`byte_instance_stores.py`](../../scripts/game_data/il2cpp/byte_instance_stores.py)
checks the selected instance declaration, complete incoming `this` and byte
argument aliases, the named Boolean IFix test and its false JNE fallthrough.
The actual byte-store instruction then writes that argument to this instance's
named `m_isPaused` field. Unknown instructions, partial pointers, clobbers,
wrong field owners or a different branch refuse the claim. Together with the
argument claim this establishes a compiled Data-field-to-instance-field path;
it still leaves the caller's returned/cast Buff ownership, active patch path,
serialized-source assignment and timer/tick effects unresolved.

The consumer contract separately follows HitStopAction to target selection
and StartHitStop; only its `attacker` and `target` Data reads currently have
the complete owned-field chain. RefreshBuffAttrModifierValue contains
OnBlackboardValueChange, attribute refresh recording and server-operation
creation calls. SpellInflictionOnChar contains blackboard lookup, infliction
Buff lookup, allocation/add/consume and event sinks. Its declared dictionary
is static, so the separately checkable `closedReferenceLayout` claim now
proves its instance-fieldless generic Data slot. Complete byte CMP decoding
now preserves the saved incoming-instance pointer across the initialization
check instead of treating its bytes as unknown instructions. This
independently reaches the `source` and `target` Data references: `source`
reaches GetFirstTarget's `targetSettings` argument, and `target` reaches
GetTargets_Dispose's same named argument. Both require the actual selected
callee signature and complete reference-argument ABI; the crossed mappings
are refused. Counts, immunity/trigger flags and other candidate chains still
lack complete owned reads. Compiled argument ownership does not establish
selected entities, branches, delivery or live infliction outcomes.

SpellInfliction independently proves the same source/target selection
argument pattern for its own shorter Data type. Its energy-shard Buff,
allocation, consumption, add and event calls do not close the enum/extra-flag
field chains or establish actual infliction. CharHurtAnimAction separately
owns attacker/defender references and their selection arguments; Blackboard
evaluation and ApplyCharHurtAnim calls do not prove the configuration values
or animation effects. CheckSpellInflictionType owns complete mask and saved-
key reads. Register-only BT decoding independently preserves operand
direction, width, instruction boundaries and its flags-only write, so the
saved receiver chain survives the bit-test instruction. Its event-context,
Blackboard and server-operation calls still retain gaps for context ownership,
bit-test results, saved-key sink arguments and condition outcomes.
IgniteBuffTextAction's target profile reaches its selection parameter. Its
generic EventDispatcher and EventBinding dispatch calls still need a closed
event-payload identity proof; their presence does not establish text output.
Shelter, Slow, Speedup, Weak and Enhanced independently prove their concrete
return-policy getters, with inherited keyword execution ownership left open.

The normal return policies are independently typed: HitStopAction and
RefreshBuffAttrModifierValue return AlwaysReturnTrue; CheckTargetsEqual,
VulnerableAction and SpellInflictionOnChar return CustomReturnType. The
[`constant return proof`](../../scripts/game_data/il2cpp/constant_returns.py)
admits the latter's actual complete EAX XOR-zero only when the selected enum
member is zero, then checks the same guard direction and uninterrupted return
epilogue. A byte/word clear or a nonself XOR cannot qualify. VulnerableAction's
policy getter does not establish ownership or behavior of inherited keyword
execution. None of these property returns is the action or sequence result.

DebugPrintAction has a stronger bounded conditional claim: when its compiled
IFix Boolean check returns false, the checked JNE falls through to `AL=1`
and a plain return epilogue without any intervening print call. The
`returnsAfterFalseCall` claim verifies the named call, test, branch direction,
constant and epilogue; a changed branch, additional call, unknown instruction
or return-register overwrite refuses it. This establishes the compiled
unpatched path only. The live IFix check and patched implementation remain
unresolved, so the action name alone does not establish logging behavior.

The additional consumer groups establish compiled Buff-finder and blackboard
read/assignment calls for GetTargetBuffBBAdvanced, attribute/provider reads,
dynamic assignment and Buff notification for StoreAttributeValue, and provider
evaluation plus `RandomUtils.Dice` for Conditions.Probablity. Method presence
does not establish field-to-argument flow, selected branches, numerical results
or server operation delivery. Whole-root replay and these consumer claims are
separate checks.

The CheckEntityNum consumer group separately proves target-list selection,
entity and hit-reaction carrier reads, blackboard retrieval/assignment and
server-operation construction calls. AddGlobalCDTimer calls first-target
selection, provider evaluation and `BattleManager.AddGlobalTimedMarker`;
NotifyCharPassiveUIAction calls first-target selection, provider evaluation and
`AbilitySystem.set_charPassiveNum`. These build-independent claims connect each
named action to compiled consumers while leaving its stored fields' argument
flow, live filters/count/comparison, evaluated duration or number, actual writes
and visible effects unresolved. Each group remains independently fail-closed;
a missing downstream call does not admit its partially proved rows or invalidate
unrelated groups.

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

The recipe also selects the registered `AbilityAction<T>.AssignData` body.
[`il2cpp/generic_entries.py`](../../scripts/game_data/il2cpp/generic_entries.py)
joins the current MethodSpec class/method contexts to the generic-function
table and requires one non-null entry without another method definition folded
onto it. Normal metadata signatures, bounded native extents and body windows
remain separate gates. The selected shared reference instantiation establishes
an entry address, not the live closed receiver type, hidden MethodInfo or
generic field layout. Observations retain nongeneric base fields and supplied
data/environment references; `m_data`, cast success and completed assignment
remain unread. Supplied data identity and server action index are separate
carriers, not a serialized action-node join.
Saved follow-up entries establish live use of the selected target-Buff
blackboard, attribute-store and probability consumers. Some entries have
confirmed Buff environment reference associations; others match an
Ability initialization environment or remain unresolved. This includes
probability entries in both Buff and Ability contexts. The method name or
its presence in BuffData does not establish a Buff owner.
Both ordinary and registered generic `AssignData` entries remain unobserved in
that complete, lossless sample. Matching explicit assignments still come from
`ReAssign`, which carries no supplied action-data reference. Registration proof
is not proof of an active initialization path, and a longer replay of the same
encounter cannot be assumed to close this gap. The reviewed loading consumer
claims establish sequence construction/reassignment stages; initializer entry
arguments can now be associated separately, while the selected action-data node
remains unresolved.

The initialization consumer claims now independently re-prove the compiled
`SequenceAction.Init` call to `AbilityActionData.NewAction` and forwarding of
the incoming environment. Skill highlight-condition initialization contains
skill-environment construction and sequence creation; the environment
constructor stores its incoming skill reference. These named claims establish
compiled paths, not live branch selection or a skill owner for the previously
unlinked probability entries. The capture recipe observes those initializer
entries plus `Skill.Init` and `Ability.Init`, retaining supplied data,
environment and skill references with separate stored skill identifiers.
`NewAction`'s direct class-reference return ABI is proved from the selected
declared native type; its returned action remains unobserved. Consequently a
creation entry cannot establish which consumer receiver received its data.

Saved initialization entries now distinguish two receiver carriers:
`SkillHighlightEnvironment` construction and `Ability.Init`. Selected probability,
target-Buff blackboard and attribute-store consumers have prior environment
references matching `Ability.Init` receivers, with captured incoming skill
references and matching stored/data skill IDs. Their references have no observed
Buff Reset or matching highlight-environment constructor. This is direct entry
argument evidence and a conditional reference association; it does not establish
a Buff or skill owner. Probability actions therefore cannot be assigned to a
Buff merely because their formatter also occurs in BuffData.

The runtime inspector retains constructor and Ability initialization arguments
in separate columns. Each association requires exactly one matching initializer
over the capture, prior entry order, a single observed environment thread, no
Buff-reset evidence or conflicting initializer receiver type, and consistent
observed skill identities. A later initializer or skill identity conflict
rejects earlier candidate joins; the rejected entry and reason remain visible.
This does not establish initializer completion, object lifetime, skill ownership
or serialized action-node identity. No runtime environment downcast or getter is
used. Available SkillData source bytes are archived with BuffData, and skill
ID-to-filename byte candidates remain distinct from a current schema receipt
and runtime file loading. Both selected `AssignData` entries remain unobserved
despite live sequence/creation entries. Their absence does not prove that data
assignment was absent. The initialization claims now re-prove the intervening
native dispatch: `NewAction` forwards its environment into a bounded anonymous
helper that reads the metadata-selected `AssignData` virtual slot and compares
its function pointer with the registered shared generic implementation. On the
equal side, the helper contains direct writes to the nongeneric base environment
and execution-state fields; on the unequal side, an owned native fragment
forwards action receiver, data, environment and MethodInfo through that virtual
slot. Thus a compiled initialization path can bypass both observed named entry
addresses. This is a conditional compiled-path explanation, not evidence that
the saved session selected it or completed assignment.

The rule derives the slot, base field offsets, declared signature and generic
registration from the selected build. It rejects implementation, slot, argument,
branch-direction, fragment-ownership or base-field drift, with bounded failure
diagnostics. It does not name the generic data-field offset, prove a cast, follow
IFix execution, or establish a runtime closed type. This dispatch proof alone
does not observe `NewAction`'s returned action or associate its data with a
consumer. Entry observations must retain that identity independently of branch
timing.

A named-consumer metadata check offers a narrower candidate for a future
association: `CheckEntityNum`, `AddGlobalCDTimer` and `NotifyCharPassiveUIAction`
inherit `AbilityAction<Data>` with their respective concrete nested `Data`
types. None declares its own data field or accessor; the shared base declares
`m_data` as a generic type parameter. This establishes declared ancestry, not
an instantiated field offset or the live receiver's closed type. A future
entry observation of that reference needs an independent closed-layout proof;
open generic offsets or a nearby native load cannot supply it.

Recipe v7 permits a narrowly proved reference slot on selected named consumers.
`il2cpp.reference_layouts` requires a sole instance type-parameter field, its
exact closed parent, a fieldless concrete subclass, a fully occupied nongeneric
base and a concrete size increment of exactly one reference. Selected native
inputs are authenticated before and after preparation; open generic placeholder
offsets are never used. Consumer entries retain the stored data pointer without
following it. The runtime inspector matches a unique earlier `NewAction` data
receiver and supplied environment to the consumer's stored references. Missing
fields, null references, repeated factory entries, thread conflicts, intervening
action/Buff resets or changed stored references withhold the match, including
conflicts observed later. Shared data in distinct environments is permitted.
This is reference agreement only: factory return, assignment completion, object
lifetime and serialized-node/file selection remain separate gaps. Existing
recordings receive no synthesized stored-data observation.

A complete, healthy combat recording has exercised this stored-reference
bridge on the covered consumers. An earlier factory and later consumer can
agree on both reference identities while still failing the reset boundary;
these entries remain refused. Live field coverage and per-entry results belong
in the generated capture reports, separate from the preparation layout proof.

The reviewed consumer recipe also composes this reference-slot witness with
named Data fields and inherited `AbilityActionData` fields. Within the existing
field budget it retains `serverActionIndex` plus selected comparison flags,
attribute enums, string keys or common configuration fields. The compiler
checks every declared owner/type and enum storage; stored strings require a
separate final reference read and remain within the two-indirection bound.
These bounded reads observe stored configuration, not evaluated blackboards,
collection elements, dynamic thresholds or the runtime Data class.

An authenticated payload recording has exercised the added fields on every
selected consumer class. On accepted reference/reset-window associations,
the stored consumer index agrees with the earlier factory entry. Rejected
associations retain their observed payload but supply no factory comparison.
This is sampled entry-value agreement, not proof of index conservation across
all creation paths or of an unchanged Data object between those entries.

An admitted whole Buff source can contain a unique action of the consumer's
declared Data type with an index equal to the factory entry's stored index.
This supplies a conditional source-node candidate. Reference agreement does
not prove that the Data index or parameters were unchanged before consumption,
and index agreement does not establish runtime file loading or node selection.
Compare newly recorded consumer fields separately, preserve ambiguous or absent
matches, and never synthesize these fields for an older recording. A SkillData
anonymous frame with physical EOF remains unnamed even when a legacy family
coverage flag says whole; it supplies no recursively named action-node join.
New payload comparisons also agree with scalar and enum fields in conditional
whole-Buff candidates. `utf8_source_helper.py` independently proves the actual
source helper's signed byte length, null and empty branches and UTF-8 decoder
call through `memorypack_utf8_source_helper_native.json`. It authenticates the
original source hash and exact field span before comparing a stored string
with its captured value. Invalid UTF-8 is refused; native replacement and error
behavior remain unproved. This supplies a supplemental comparison without
rewriting an older byte-payload receipt or promoting the containing schema.
Candidate uniqueness is limited to the admitted source, and does not identify
the runtime-selected node or loaded file.

The capture compiler now admits that reviewed helper through recipe v6. It first
authenticates the named caller's signature and direct reference return ABI, then
re-proves the unique anonymous entry, both dispatch sides, environment forwarding
and caller receiver forwarding into the data register. The helper is a separate
native entry, not a metadata method or a `NewAction` return observation. Only
the simultaneous action, data and environment register identities are retained;
the opaque context register, generic fields and all pointees are unread. Current
native preparation and host preflight pass. The observer is withdrawn from the
active Buff recipe after a Capture-only scene-load crash. The reduced named-entry
profile subsequently passed a user-recorded scene-load check with a complete,
healthy, lossless journal and screen backup. The captured runtime binary and all
retained hooks match the crashing profile, with only the anonymous observer
removed. This validates that loading sequence, not the corruption mechanism or
other workloads. Static argument and dispatch proof does not establish observer
safety; no complete dispatch association is admitted from the aborted recording.
An earlier startup attempt reached the helper but lost journal
records during an initialization burst. Those partial entries diagnose recorder
load; they do not establish a dispatch association. Offline preparation proves
hook selection and read programs, not queue throughput under live startup load.

The subsequent crash dump shows substantial remaining system commit capacity,
and the failure stack reaches shader-property string marshaling with an abnormal
length-derived allocation size. This does not establish ordinary memory
exhaustion or identify the recorder instruction that caused corruption. The
user reports that ordinary startup succeeds and Capture crashes during scene
loading. Retain the anonymous-observer regression as unresolved despite the
successful reduced-profile loading check; do not request another identical combat
sample to fill the disabled data-assignment gap. The loading check observes named
initialization entries but no selected consumer or assignment entry, so it adds
no action/data/consumer association. Its Buff definition identities join existing
authenticated stored-schema receipts without establishing runtime node selection
or increasing format coverage. Subsequent offline parent extensions can close
the remaining observed stored definitions when the complete family and canonical
JsonData receipts pass; replay that schema join separately while preserving the
original scene-load receipt. Such a format improvement supplies no additional
runtime assignment or consumer association.
Game-exit diagnostics retain the source log and incomplete session context,
without weakening journal completeness or promoting partial observations.

The Buff inspector records the triplet independently of named assignments and
Buff identity. It can associate a later consumer only through the same action
reference, environment and thread, refusing null data, intervening action or
Buff resets and conflicting thread or stored-instance evidence. A dispatch match
does not establish completed assignment, branch selection, object lifetime,
returned action, serialized-node selection or skill ownership. Existing saved
sessions validated before this hook was added contain no helper observation and
acquire no new dispatch association. A failed session remains inadmissible even
when its surviving helper and consumer entries appear to match.

Saved Buff sessions now provide lifecycle and selected consumer entries.
[`buff_runtime_trace_inspect.py`](../../scripts/game_data/buff_runtime_trace_inspect.py)
reuses a passing generic inspection, checks each interpreted field against its
retained raw row and profile, and requires a complete, healthy, lossless receipt.
It separates a consumer's stored environment reference from a same-thread Buff
Reset window confirmed by subsequent matching stored definition and instance
fields. A matching supplied action-assignment reference is a further, separate
association; action Reset, Buff Reset, conflicting instance fields and
cross-thread reference use prevent stale joins. Entry order and reference
equality do not establish the assignment's write or an independently proved
object lifetime.
Diagnostics distinguish an absent observed Buff Reset from an unconfirmed
stored identity and thread mismatch. A later identity conflict invalidates the
whole observed reset window and clears its consumer ID and identity claims,
while retaining the entry fields and reset sequence as evidence. Hook coverage
also lists selected entries with no records; zero entries do not establish
absence of behavior or an inactive alternate route.

The observed pooled reuse establishes a field-specific boundary: at Reset
entry, stored definition/data IDs can retain prior values while instance UID and
client-instance ID have already changed since the preceding observation.
Do not classify all Reset entry fields as the previous instance, or attribute
those changes to the body of Reset. Cached action execute-result fields likewise
precede the observed consumer call and are not its return value.

The named vitals, skill-setting and battle-signal consumers are observed in
confirmed Buff reference windows. Only some have a matching explicit action
reassignment entry; unlinked references and missing assignment records remain
gaps. Optional canonical receipt joins match archived source bytes and selected
native inputs, keeping whole stored schemas distinct from framed residuals.
They establish neither runtime file loading nor selection of a particular
action-data node. A failed schema gate empties that join while retaining valid
runtime observations. Source and reader identities are checked before and after
the join; changing coverage and per-session inventories remain in reports.

Per-frame triggering, action returns, target/provider values, dynamic
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
uses the shared recursive direction and selector owners. Each reached direction
reference and processor child must have its own native join and original-span
proof. Validator lists may compose the independently proved zero-member and
tag-query types; finder values must use an independently named reader. Other
selector children remain explicit refusals even when their cursor framing
succeeds.
These stored PlaySound members establish neither audio ownership nor live
playback. Action or child EOF alone never substitutes for complete root replay.

`buff_recursive_control_actions.py` composes IfElse's typed sequence children
recursively, CompareFloat operands, ModifyDynamicBlackboard targets and scalar
values, and CheckBuffStackNumAdvanced's independently owned children. Each
physical action span must close before its named child reader runs; recursively
anonymous children still refuse the root. `buff_id_actions.py` distinguishes
the one-member BuffId wrapper from BuffFindSettings' raw string-list elements
and CheckGlobalCDTimerAction's plain `buffId` string. The timer action joins its
separate TargetSettings child through the selected formatter source context;
its identifier bytes remain raw, and runtime timer selection or expiry remains
unobserved. Different parent field types and native source contexts prevent
treating these wire shapes as interchangeable.
The same owner independently admits AddGlobalCDTimer through its own reviewed
formatter and actual source-result stores. Its plain `buffId` bytes,
BlackboardDouble `cdTime` and TargetSettings `target` occupy separate spans;
the scalar and target generic contexts are checked independently of the common
priority context. Nullable identifiers and providers remain distinct from
evaluated durations and applied timers. This parent uses the Buff dispatcher
and its own current native gate; the earlier SkillData source-order proof
alone does not authorize a Buff composition.
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

The shared selector composer keeps the named `finderData`, `postProcessorData`,
`validatorData` order. `buff_selector_postprocessors` independently joins the
postprocessor list's closed `ReadPackable` context to its actual owned runtime
field, then authenticates the selected CircularOrderSort, Projection,
ExcludeTarget, NavMeshPathPositionProcessor, PriorityFilter and ShuffleTarget routes.
Projection's `boxShape` list composes the independently proved ShapeData
records; ShuffleTarget keeps raw `processTargetType` bits and the concrete
BlackboardInt's key, use-key flag and integer value. The latter reuses the
root's maintained concrete child proof, with an independently checked parent
type join. ExcludeTarget's child context joins the actual TargetSettings
wrapper's owned `__instance` type before invoking the shared recursive target
reader. PriorityFilter's separately typed BuffFilterSettings child composes
the maintained BuffFindSettings/GameplayTagQuery owner; the remaining filter,
count, reserve and process-mode operands retain their stored bytes. The
selector/target/postprocessor cycle uses the same bounded target depth and
strict original child endpoints, including repeated ExcludeTarget nesting.
Null list, empty list, null union, null wrapper and null Blackboard are
separate states. Other postprocessor subtypes still refuse the enclosing
composition. The [reviewed postprocessor contract](../../scripts/game_data/contracts/buff_selector_postprocessors_native.json)
records these current source/destination and child joins; target projection,
filtering, shuffling, provider choice and blackboard evaluation remain unresolved.

CircularOrderSort and NavMeshPathPositionProcessor now belong to the maintained
list composer, through actual union switch/type-usage chains and the
[reviewed source programs](../../scripts/game_data/contracts/postprocessor_circular_navmesh_native.json).
`setter_output_sources` proves their incoming byref-reader and ref-wrapper ABI,
the complete read-result/setter bridges, and the setter's exact owned Data
stores. These readers retain the reader in RDI and the ref-wrapper in RBX;
the final member deliberately replaces RBX with the wrapper it references.
Their typed `__realInstance` getter's selected ordinary path checks that its
cached derived Data equals the inherited base instance before returning it.
The proof retains an explicit condition that preceding calls return ordinarily
and preserve Win64 nonvolatile registers. Generic source contexts have no
unique registered entry join; the actual physical calls and their typed
MethodInfo argument programs are checked, without filling that gap by name.
CircularOrderSort
owns `desireCount` as BlackboardInt; `heightOffset`, `rangeThreshold` and
`reverseFlag` as BlackboardDouble; `indexKey` as a raw string payload; and a
separate `rangeCheckTarget` reference. In particular, the name `reverseFlag`
does not make its declared BlackboardDouble a Boolean. NavMeshPath's radius
joins BlackboardDouble, its maximum distance retains raw Single bits, and its
navigation flags retain their byte representation. The independently checked
primitive source programs read and account for one byte or four Single bytes;
the byte source's selected normal path applies nonzero normalization before
AL reaches the setter. Keeping raw stored flag bytes does not assert that the
runtime field preserves those bytes. Blackboard and recursive TargetSettings
children join their independently admitted actual types; `indexKey` reaches
the reviewed nullable byte-length string helper and retains raw payload bytes.
Complete original lists now replay through the maintained composer, including
mixed processors and these children. Complete family and independent canonical
root replay remain the enclosing-root admission boundary. These stored
declarations and conditional transfers do not establish circular order,
blackboard evaluation or navigation effects.

The corresponding Data `PostProcess` methods also expose separate consumer
leads. Bounded original prefixes trace their incoming reference receiver to
owned configuration reads. CircularOrderSort's scalar operands and NavMesh's
radius reach the actual static `ActionBlackboardExtensions.GetValue` parameter;
the BlackboardDouble overload returns Single. The selected `reverseFlag`
program compares that return with zero and assigns a local flag, without
proving the evaluated value or resulting order. NavMesh's `checkMaxDistance`
and `maxDistance` reads belong to `_GetRealLandPos`, with another distance read
in `_TryFindStraightLineDest`; absence from the main body's proved reads does
not establish that a field is unused.
The owned `checkMaxDistance` byte is compared with a separately proved zero
register, and its immediate JE reaches the local result's return-copy path;
the other compiled edge continues into distance processing. Its runtime value
and chosen edge remain unknown.

These helpers illustrate why aggregate return ABI must be proved per call.
The actual `_GetRealLandPos` caller supplies Data in RDX and a separate result
buffer in RCX. Its selected complete ordinary return program copies the
Nullable<Vector3> representation into that buffer and returns its address in
RAX. This is separate from the Boolean-returning straight-line helper's RCX
receiver. The straight-line distance program retains its owned maximum-distance
operand across a shared Vector3 squared-magnitude entry: its complete program
uses the actual coordinate fields, writes only other vector registers and
returns the sum of coordinate squares before the caller squares and compares
the maximum. The entry has both static and instance method declarations, so
this proves the compiled operation rather than a unique method-name join.
Vector provenance, floating-point exceptional behavior, chosen branches,
navigation success and target mutation remain open. These observations use
the [bounded compiled-path boundary](../../scripts/game_data/il2cpp/compiled_paths.py)
and the reviewed runtime field declarations above; isolated prototypes have
not added maintained consumer claims.

`buff_direction_target_children` composes nonnull `source` and `target`
TargetSettings through [separate reviewed reference transfers](../../scripts/game_data/contracts/buff_direction_target_joins_native.json).
The source has an independently initialized null stack reference, overwritten
only on the selected cached-provider branch before transfer to its owned field.
The target transfers its separate returned reference to a different owned
field. Complete normal pointer programs preserve the incoming reader and
ref-wrapper aliases; neither an eight-byte reference transfer nor a matching
type name establishes a child's wire format. Each nested TargetSettings must
pass its own reader, Selector/finder/validator/postprocessor composition and a
strictly contained original span. Recursion is bounded; no child completion
waives its siblings, parent endpoint or physical root EOF. CreateBuffAction,
EffectAction, the hurt-animation curve parents and the shared target callback
use this same composition, while FindTarget passes its own separately typed
direction and selector fields. Curve parents no longer require their
direction's source and target to be literal null values: each positive child
must independently close through the shared target owner.
Stored recursion does not establish evaluated directions or selected targets.

The single-CreateBuff root adapter now receives the same complete recursive
action proof as the shared event-map route, rather than assembling a separate
subset of target children. The corpus validates the shared action context once
and passes it to this adapter; standalone callers validate the same owner.
The adapter still checks its own sole action, input cardinality, every root
member, source-ID equality and physical EOF. Missing nested proofs and build
drift remain explicit failures before action replay. This prevents a newly
composed shared child from silently bypassing, or being omitted by, the older
root path.

The remaining consumer leads remain outside maintained execution claims.
The [reviewed FindTarget family](../../scripts/game_data/contracts/buff_b2_native.json)
contains the ExcludeTarget and PriorityFilter parents and BuffFilterSettings
reader. Their stored child joins now belong to the maintained postprocessor
composer, under independently checked closed contexts and exact original
spans. The authored filtering
methods belong to the nested Data types; method ownership must be resolved
before tracing incoming receivers. Native enum declarations distinguish
Targets and HittableTargets and name distance, HP, Buff-stack and screen-position
filter modes. These declarations and stored words do not prove that a mode
executes, forwards its operands, or mutates a target view.
Isolated current native prefixes also trace the incoming Data receiver to its
direct configuration reads. Naming a subsequent call parameter requires a
separate ABI and forwarding proof. In particular, GetTargetsView's caller
saves its RAX result directly, whereas FilterParamWrapper.Wrap's caller passes
a stack buffer and copies the returned aggregate. A value-type declaration
alone must not shift all named parameters as though a hidden buffer were
present; the actual caller, callee, return representation and field stores
must agree. An isolated original-program probe closes Wrap's ordinary
buffer-return path and its actual constructor. Each constructor helper has a
closed local retry/return graph: its instructions modify the bitmap through a
bounded native-image address range and preserve the volatile aliases carrying
the remaining constructor operands. The constructor's complete typed stores
establish the unboxed field representation; Wrap returns its original incoming
buffer after that constructor returns. Under the ordinary IsPatched-false path
and the explicit x64 nonvolatile-call boundary, incoming PriorityFilter Data
fields `buffFilterSettings`, `onlyReserveMaxPriorityTargets` and
`processTargetType` reach Wrap's separately identified named parameters.
The compiled caller prefix does not prove predicate feasibility, the action
environment's provenance or any evaluated filter result. These observations
remain outside the maintained consumer claims, and the concrete Wrap proof
does not supply an ABI rule for GetTargetsView or other aggregate returns.
An additional isolated forwarding check reuses the same owned caller prefix:
stored `maxNum` reaches Filter's register parameter after Wrap's complete
normal epilogue restores its incoming nonvolatile value, and `filterType`
reaches Filter's separately named outgoing stack parameter. The actual static
Filter declaration returns Int32, excluding a hidden result buffer for this
particular call; its enum parameter joins its declared Int32 underlying type.
The selected configured-count/fallthrough branches and the prior ordinary
callee boundary remain attached. Parameter forwarding does not establish
count enforcement, comparison order, the Filter result or target mutation.

`buff_camera_control_state_action` composes the
[camera-control parent window](../../scripts/game_data/contracts/buff_19e_native.json)
through its own [reviewed action contract](../../scripts/game_data/contracts/buff_camera_control_state_action_native.json).
Action bodies are located through their union
headers; an object-header-only inventory can miss them. The two custom-curve
fields have separate closed contexts that join the actual AnimationCurve
argument of the selected formatter's generic base. The existing
[AnimationCurve proof](../../scripts/game_data/contracts/memorypack_animation_curve_native.json)
can replay each independently owned original child without claiming curve
evaluation. The inheritSkillIds list joins the same actual closed List<string>
context and source read target as BuffFindSettings's buffIdList. Its bounded
nullable byte-payload grammar is shared, while string decoding and live
provider selection remain conditional. Null list, empty list, null elements,
empty payloads and arbitrary payload bytes retain distinct receipts. All
other parent flags, enums, scalar bits and key payloads retain their original
spans; no successful child replay waives sibling fields or complete root EOF.
Compiled addition, inheritance and cleanup calls are leads for argument/handle
flow. The separately checked ordinary getter returns CustomReturnType; that
policy does not identify the action result or prove a camera-state effect.

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
A selected forward replay can close the complete named Buff root while an
earlier candidate filter prevents family admission. Embedded filename markers
can create rejected suffix candidates; shared-event selection counts only the
single suffix accepted through EOF and retains rejected markers as diagnostics.
Selection establishes eligibility only. The original byte-zero reader must
still prove every root field, source identity, current native dependencies and
exact EOF before the whole-family and canonical gates admit the file. A bounded
replay alone never changes coverage or the recorded-definition join.

[`buff_cost_action.py`](../../scripts/game_data/memorypack/buff_cost_action.py)
now owns the named stored `ObtainCostAction` parent. Its
`atbGainTag` and `uspRecoverTag` are `GameplayTag` value types, so the
primitive member-width derivation intentionally returns no width. The
reviewed `buff_fe_native.json` reader independently takes a DWORD for each
closed type, and `wrapper_members.unmanaged_value_sizes_from_image` derives
the same extent from the selected build. These are separate witnesses, not
permission to treat arbitrary value types as scalar integers. General named
parent admission now uses an explicit reviewed `unmanagedSource` proof to join
unmanaged size, closed source MethodSpec, source read width, cursor accounting
and destination. The registered generic entry and the parent's optimized
direct-call entry can differ: both native bodies are authenticated separately.
The registered normal path reads a DWORD and invokes its own cursor helper
with four; the optimized normal path performs the same four-byte reader-slot
updates directly. This proves the selected stored width without equating
addresses or extending the claim to short-segment/provider behavior. A missing
or changed entry, instruction window, typed context or destination refuses
admission with the record and field identified.
The cost reader keeps `coefficient` and `costValue` as independent BlackboardDouble
children, `source` and `target` as independent TargetSettings children, and
ATB/USP selectors, GameplayTag bits and flags as stored values. All children
must close on their original spans. These names and stored values do not
establish live resource gains, deductions, provider results, target selection
or sound/effect dispatch. The complete Buff root and canonical replay gates
remain required for coverage publication.

The census also ranks shared-event refusals already stored in the complete
family report, without running the parser again. It removes source-specific
positions from grouping keys while preserving union tags and structural
expectations, retains original diagnostics and source hashes in bounded
examples, and counts residual files with no recorded refusal separately. That
absence supplies no closure evidence.
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

An independently named action can be replayed at an existing Skill span when
the selected native dispatcher, reached source reader and typed children agree
with the reviewed Buff route. Keep the original archive hash, physical span and
field bytes; this proves only that action's stored layout. Comparing its named
leaves with a consumer additionally requires an accepted same-reference
NewAction/environment window and supplied Ability skill identity. Type/index
and equal payloads can still match repeated physical nodes. Preserve every
candidate; missing nodes in a partial Skill profile are coverage gaps, and
neither outcome names the whole Skill root or proves runtime node selection.
Initializer entry caller addresses are separate evidence: native body ownership
may identify a registered caller, but an indirect call or an anonymous body
does not reveal the factory return or an assignment branch.

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

The historical target-set verification and rebind summaries remain available,
but their original capture receipt is absent from its recorded local source
path. A summary's `validated` token cannot replace that primary input.
`jsondata_corpus._skill_capture_target_set_reference` correctly refuses the
complete registry when the original/rebind overlay cannot replay its pinned
receipt. Restore a hash-identical saved receipt and every required dependency
before rebuilding the complete canonical registry. A passing Buff family gate
or selected canonical Buff replay remains separate evidence and does not
repair the missing Skill capture or publish new registry coverage.

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

Historical schema bundles such as the ignored
`tools/endfield_schema_recovery_1.4.4/` are candidate references for recursive
Buff/Skill shapes and manual wire exceptions, never production dependencies.
Join their exact runtime types through `wrapper_members` and `action_dispatcher`;
rederive ordinal tags and check root layouts against the selected build. The
historical Buff root can retain its field order while nested union ordinals and
child records change. The existing derived-plan lane already
supplies current names and member order, so prioritize independently useful
physical-layout corrections rather than duplicate catalogs. Declaration agreement
and a successful reference-body parse still require current native reader,
typed-child and source-span proof before the ordinary family/registry gates;
they recover neither missing cursor receipts nor live consumer/provider selection.

The historical decoder, after isolated current-identity and declaration overlays,
now gives a structurally clean candidate for the complete selected Buff corpus.
It also reproduces the named root spans of previously admitted roots. These
checks close the reference grammar frontier; they do not admit the remaining
roots or establish preservation of raw flags, enum values, float bits and string
encodings. Keep the candidate outside production, authenticate each recursive
formatter and typed composition, then replay original source spans through the
maintained readers. Trial variants, coverage and per-source results belong in
the generated historical-schema leads report.

The maintained `buff_cast_skill_action` reader uses
`buff_cast_skill_action_native.json` to join `buff_27_native.json`'s named
parent source/destination program to its selected action route. Its `caster`
and `target` are separately owned TargetSettings records, while `skillId`
composes the independently authenticated paired BlackboardString. Null wrappers,
null/empty payloads and noncanonical flag bytes retain their original states.
These are stored operands; evaluating a skill ID, selecting a caster/target,
accepting costs, interrupting or invoking a skill are separate consumer claims.
Unsupported nested target children refuse the action instead of closing it
through a matching parent name or candidate endpoint.

The independent names-only consumer groups in
`buff_action_consumers_native.json` prove the incoming owned CastSkill Data
reads, `caster` flowing to `GetFirstTarget.targetSettings`, and `skillId`
flowing to `ActionBlackboardExtensions.GetValue.param`. They also prove the
three flag reads and the named target-view/cast calls. The target-view operand
forwarding remains a separate obligation: the current reference-flow checker
excludes that callee's aggregate return ABI. Its false-IFix property path
returns the typed `CustomReturnType` enum through a complete return epilogue.

The separate `buff_cast_skill_consumer_flow_native.json` contract and
`buff_cast_skill_consumer_flow_native` loader authenticate a narrower local
completion program through `il2cpp.call_completion_return`. The actual
`TryCastSkillDuringAction` callee returns void. After it returns ordinarily,
CastSkill assigns true to AL and directly reaches the complete matching
frame restore and return, preserving that Boolean. The checked entry saves,
allocation, exit jump and every epilogue instruction exclude a partial
return-tail claim. This proves the selected compiled completion value; it
does not prove branch feasibility, skill acceptance or effects, and that
true value is not a success result returned by the void callee. Other exits,
flag forwarding and inherited cast information remain separate.

The maintained `buff_animator_param_action` reader and
`buff_animator_param_action_native.json` use the separate parent and child
programs in `buff_14a_native.json`. `endAction` and `paramAction` each have their
own independently nullable AnimatorParamAction span. That child's ordered
animator parameter, Boolean value, float value, integer value and typed
AnimatorControllerParameterType enum retain raw bytes/bits. The required final
enum precedes the next parent field; truncating it cannot borrow the parent's
name-payload boundary. Name encoding, action-on-end selection, receiver state
and animation effects remain unresolved. Complete root admission still needs
the current family and canonical original-byte gates.

The separate names-only animator consumer groups prove `OnEnd` reading the
incoming owned Data's `actionOnEnd` byte, and owner-getter calls in `OnEnd`
and `ExecuteInternal`. The false-IFix return-policy getter reaches the typed
`AlwaysReturnTrue` enum through a complete epilogue. These claims do not
establish the flag branch outcome or selected animator. The two nested
configuration operands, their helper/receiver ownership and actual parameter
writes still require independent flow proofs; a return-policy enum is not an
observed animation result.

Useful current differences have selected evidence owners: the icon's
`showDirectlyInHeadBuff` flag (`buff_icon_config_native.json`), RandomPointFinder's
`extent2D` (`finder_10_native.json`), DamageUnit's `damageTags`
(`buff_damage_action_native.json`), EffectAction's `bigEffectTarget`
(`buff_a2_native.json`) and Aura's faction, angle and height operands
(`buff_aura_heal_actions_native.json`). RandomPointFinder's extent is a
BlackboardVector2 with two BlackboardDouble children, not a raw Vector2. A
DamageUnit tag list has wrapped elements and must not borrow the packed root
GameplayTag array grammar. Declaration matches are useful candidates for
FinishGlobalBuffAction, CheckDistanceCondition, RecoverPoiseAction and
ShapeFinder; their selected named source/destination checks now pass against
`buff_03_native.json`, `buff_42_native.json`, `buff_128_native.json` and
`buff_7c_native.json`. Those checks still leave recursive child admission and
consumer behavior as separate obligations.

The maintained DamageUnit reader now composes positive `damageTags` through
the independently authenticated signed nullable list grammar in
`skill_damage_unit_gameplay_tag_list_native.json` and named GameplayTag elements
in `buff_aura_heal_actions_native.json`. Null elements carry one byte; non-null
elements carry their own one-member header and four scalar bytes. The Damage
contract binds this collection to its named source member and fails closed on
either missing proof. Skill keeps its own cost-list and tag-list receipts when
composing the same physical DamageUnit. Cost lists do not gain Buff admission
from this tag-list proof; tag names and effects remain unresolved.
For the separate `damageProcessors` member, selected reads in
`buff_damage_action_native.json` and `buff_damage_modifier_child_native.json`
resolve the same closed `List<DamageProcessorBase>` MethodSpec and actual native
helper. The maintained `buff_damage_processor_collection.py` now binds this
source to DamageUnit's own member and composes ordered processor elements through
their independent scalar, scale, text, attribute-modifier and calculation span
readers. Signed null and empty lists remain distinct. Original source hashes,
element endpoints and the following tag-list and remaining unit fields must
rejoin before admission; the root modifier's receipt does not stand in for this
different parent. The reviewed `buff_damage_processor_collection_native.json`
authenticates the shared reference-list count program and its registered Object
instantiation as a conditional grammar reference. Live inflated list/provider
selection is still unresolved. Unsupported variants and unproved null union
elements refuse; raw numeric, payload and flag bits do not establish damage
arithmetic or accepted mutations. Whole-root coverage requires the complete
family gate and canonical original-byte replay.

CheckDistanceCondition has a maintained named reader under
`buff_check_distance_condition_native.json`. Its two distinct TargetSettings
operands compose through their own original spans; the distance float, radius
inclusion and comparison flags remain raw stored operands. The selected action
route and named reads do not establish evaluated distances or a predicate result.

ShapeFinder's `shapeData` is `Beyond.Gameplay.ColliderShapeData`, not
HitBoxFinder's separate eighteen-member ShapeData. Its maintained reader in
`buff_selector_shape_finder_native.json` depends on the independently named
sixteen-member `buff_collider_shape_native.json`. Collider's center, extent and
rotation offset are raw Vector3 values; each selected direct reader and separate
registered entry proves twelve-byte input and cursor accounting. The complete
parent transfer loads the typed wrapper instance directly into RCX, then copies
eight bytes from one result slot and four from the next. This explicit
`struct_output_sources.py` destination profile has no invented getter call.
String keys, geometry bits, enum and flags remain unevaluated. Both parent and
child proofs are required; missing or different native inputs refuse even a
structurally readable finder. Whole-root coverage still requires the complete
family gate and canonical original-byte replay.

FixedPointFinder has a maintained reader under
`buff_selector_fixed_point_finder_native.json`, whose selected source windows
are owned by `buff_119_native.json`. The current finder route and SelectorData
union plan join the concrete wrapper independently of the action source that
first exposed it. Position is an inline twelve-byte read and eight-plus-four
copy; rotation is an inline sixteen-byte read and complete SIMD copy. Both
programs update the same buffered-reader cursor slots and forward the entire
temporary through the typed wrapper getter to the named field. Explicit
temporary-stack and destination-displacement declarations must match every
read/store instruction; a native value size alone does not prove either wire
width or transfer. `sampleRadius` composes its independent BlackboardDouble
receipt, and `snapToNavmesh` retains its original byte. Null union, null wrapper
and null radius are distinct. These stored geometry/radius operands do not
establish sampling, snapping, selected coordinates or a target entity.

RandomPointFinder now has a maintained named reader under
`buff_selector_random_point_finder_native.json`. Its selected selector branch,
generated destinations and closed source contexts authenticate the complete
finder and BlackboardVector2 record. Vector2's two independently read
BlackboardDouble children and the separate Vector3 child compose at their
original spans; flags and shape enum bits remain raw. This proves stored
operands, not random choices, navigation snapping or resulting coordinates.

RecoverPoiseAction likewise has a maintained reader under
`buff_recover_poise_action_native.json`. Its dispatcher join and named source
reads authenticate the parent, including the distinct `effectData`,
`recoverValue` and `target` fields. EffectActionCfg, admitted CalculationBase
variants and TargetSettings reuse their independent readers on original byte
ranges. Unsupported recursive children still refuse the action. These child
admissions require the complete family gate and canonical original-byte replay
before a surrounding Buff root gains coverage; actual recovery amounts,
selected receivers and effect playback remain unresolved.

The independent consumer claims in `buff_action_consumers_native.json` now
cover RecoverPoiseAction's direct target-resolution, `NewPoise` and effect
creation calls, and a `target` read through its proved incoming closed
`m_data` slot on a checked local compiled path. Its false-IFix return-policy
getter yields `CustomReturnType`; the separate Boolean `AlwaysReturnTrue`
method returns the owned `alwaysNext` byte only on false-IFix/non-null-Data
fallthrough. `owned_byte_returns.py` authenticates unsigned byte-to-EAX loads
and owned cold branch targets without relaxing the contiguous return epilogue.
These claims do not prove target forwarding, recovery arithmetic, accepted
poise writes or playback. The `healer`, `effectData`, `recoverValue`, `poiseType`
and `playHealEffect` read proofs still encounter undecoded local instructions.
An isolated byte-XOR/long-NOP decoder trial reduces that frontier but reaches
the bounded local-path budget without proving these reads; it remains outside
production. Refusal is not proof that those fields are unused.

Stack effects require a separate concrete-value composition. The selected
wrapper declarations derived by `wrapper_members.py` expose
`StackBuffEffectData.effectActions` as a list of concrete
`EffectAction.EffectActionData`, rather than the abstract action union. Do not
prepend an invented action tag to reuse that union reader. The current
`buff_a2_native.json` reader includes an inline DWORD source for priority;
the maintained concrete record validator proves that scalar program and the
other named source/destination members. Priority is an Int32 enum, and its complete input read,
cursor accounting and full DWORD store reach the immediate parent's typed
AbilityActionData slot through the wrapper's inherited instance field. It is
not a helper call or a child-class-owned field. The maintained
[`struct_output_sources.py`](../../scripts/game_data/memorypack/struct_output_sources.py)
now checks this explicit scalar program, with the concrete record declared in
[`buff_effect_action_data_native.json`](../../scripts/game_data/contracts/buff_effect_action_data_native.json)
and authenticated by
[`buff_effect_action_data.py`](../../scripts/game_data/memorypack/buff_effect_action_data.py).
The profile independently checks the ref-reader/ref-wrapper ABI, Int32 enum
underlying type, retained pointer aliases, actual wrapper ancestor reference,
four-byte input and cursor accounting, and full store into the immediate
Data parent. It neither fabricates a helper call nor validates enum meaning.
Collection provider/registration joins and complete original-span composition
remain open.
The compact stacking contract therefore keeps positive interiors opaque.

The current stacking source contexts identify `ReadArray<StackBuffEffectData>`
and `ReadPackable<List<EffectActionData>>`. The list's concrete element definition
is exactly the reference type held by the generated EffectActionData wrapper,
whose selected reader remains owned by `buff_a2_native.json`. A complete selected
`GenericEntries` table lookup finds no exact closed registration for either
source context, and no registered generic pointer at either observed direct
helper target. Other instantiations of those method definitions are recorded.
Treat these as direct-call helper observations: their typed source joins remain
valid, while array/list helper programs, adapter conversion flow and element
formatter dispatch require independent checking. A nearby registered body or
an Object instantiation cannot supply the missing helper/element connection.

The selected generated initialization also constructs the original-value
adapters for StackBuffEffectData and concrete EffectActionData, retaining each
adapter object into `RegisterWrap` with its exact original type key. The
registration, conversion-interface return type, concrete formatter vtable and
forwarded reader identities pass the shared
`il2cpp/formatter_composition.py` checker. Stack's own `RegisterFormatter`
preserves its allocated `ListFormatter<EffectActionData>` into a registration
whose closed List argument and element pointer are exactly those of the source
field. These are static argument-flow and identity proofs, beyond names or
nearby generic registrations. Complete method-owned RGCTX ranges expose the
source-to-inner-reader and provider/formatter type propagation under ordinary
inflation. They do not substitute a registered Object template for the actual
direct helper, select a live cache return, prove the adapter's conversion
program, or admit positive original array/list spans. Keep the concrete
eighteen-member reader's inline scalar proof separate until those collection
programs, recursive children and following stacking tail are checked.

The actual array helper's normal buffered path also supplies a direct count
and loop witness: it loads four bytes into the count register, advances the
input and cursor counters by four, distinguishes minus-one null and zero
empty counts, and passes ordered reference-array element destinations with
the reader to the retained formatter receiver. Its selected source context
forwards the same owned generic parameter into the inner array reader, whose
provider slot is `GetFormatter<T>`. This is conditional on ordinary inflation
and the available-buffer cursor path. Keep refill/error branches, provider
success, adapter conversion and full original child spans as separate claims;
this normal-path witness alone does not admit a positive Stack root.

StackBuffEffectData's separate one-member record also passes the shared named
source/destination checker: its concrete list source result reaches the
`effectActions` setter through the non-null wrapper guard, and the selected
reader compares the member count with one. This isolated record is independent
of the EffectActionData record and its priority source. Positive list grammar,
object header/null parity and complete original parent spans still require
their own composition before the compact stacking reader can admit them.

Keep concrete wrapper return programs, object header/null paths, inherited
instance/cache relationships and generic adapter dispatch as separate proof
obligations. A wrapper's typed `GetValue` signature or captured constructor
body cannot establish which adapter invokes it. Likewise, metadata type
pointers can differ because field and return attributes differ while naming
the same reference definition: check the definition, reference kind and
decorations independently rather than requiring pointer equality. The
maintained source validator's ancestor check does not admit a collection or
prove the concrete getter's cache/class-check program.

For the concrete EffectActionData wrapper, the next conversion proof can be
split at two independently checkable points: the constructor's original
reference transfer into the inherited instance and concrete cache slots, and
the getter's non-null cache-equality fast path. Isolated current-body probes
have located those paths, but the helper's allocation and intervening memory
effects, cache refresh/cast branches and actual generic adapter invocation
remain outside the maintained concrete record contract. Preserve that boundary
when converting these leads into a reviewed profile; neither the constructor
signature nor a fast return admits a positive Stack collection.

Independently named processor-list children can succeed while a surrounding
sequence still refuses another action. The current source/dispatcher joins
in `buff_f4_native.json` and `buff_186_native.json` authenticate MoveGaitAction
and TriggerCharSpellInflictionEvent respectively. The former's six stored
members include separate `maxGait` and `minGait` enum operands; original child
spans reproduce their raw bits through the shared bounded Reader. The latter's
seven members include an independently typed `eventSource` TargetSettings,
`eventType` and `inflictionType`. The source/destination checker and current
union dispatcher establish these identities beyond a historical name match.
The maintained
[`buff_leaf_actions.py`](../../scripts/game_data/memorypack/buff_leaf_actions.py)
and its reviewed contract preserve MoveGait's `maxGait` before `minGait`;
[`buff_spell_infliction_action.py`](../../scripts/game_data/memorypack/buff_spell_infliction_action.py)
and its reviewed contract compose the independent TargetSettings child,
followed by both required four-byte enum operands. A target endpoint cannot
finish this action, even when the target is null. Original action spans now
reproduce through these independently native-gated readers. Complete sequence
ownership and root admission still come from the full family and canonical
original-owner replay gates. Stored gait limits and event operands do not
prove movement changes, event dispatch or spell attachment.

PlayAnimation and JumpTo now have a maintained recursive composition in
[`buff_animation_sequence_actions.py`](../../scripts/game_data/memorypack/buff_animation_sequence_actions.py),
declared by
[`buff_animation_sequence_actions_native.json`](../../scripts/game_data/contracts/buff_animation_sequence_actions_native.json).
The current source windows in `buff_115_native.json` and `buff_d9_native.json`
independently authenticate their named destinations and dispatcher identities.
PlayAnimation's `animName` and `startTimeBlackboardKey` additionally use the
independently proved UTF-8 source helper on their original byte ranges; null,
empty and embedded-NUL strings stay distinct, while invalid UTF-8 refuses this
profile. Float operands preserve all original bits. Its `onEndAction` composes
the shared independently owned SequenceActionData, including positive recursive
actions and both terminal flag bytes. JumpTo composes its separate
`conditionAction` sequence and then requires the following Int32 `destFrame`;
the sequence endpoint cannot finish the action. Complete root admissions pass
both the full Buff family gate and independent canonical original-owner replay
through every root field, source ID and physical EOF. Animation playback,
callback execution, condition results and actual frame jumps remain unresolved.

The maintained
[`buff_custom_ability_event_condition.py`](../../scripts/game_data/memorypack/buff_custom_ability_event_condition.py)
and its reviewed
[`buff_custom_ability_event_condition_native.json`](../../scripts/game_data/contracts/buff_custom_ability_event_condition_native.json)
compose CheckCustomAbilityEvent's separate `eventName` BlackboardString and
required following `savedParamKey`. The former reuses the independently
named three-member child, preserving its key, selector flag and value bytes;
the latter additionally uses the independently authenticated current UTF-8
source helper. Null wrapper, null BlackboardString and null/empty parameter
keys remain distinct. The child's endpoint cannot omit the following key.
Current source/destination and dispatcher proofs establish authored operands,
not event matching, parameter capture or a condition result.

The reviewed direct-target contract's named-record version in
[`buff_direct_target_actions_native.json`](../../scripts/game_data/contracts/buff_direct_target_actions_native.json)
adds ForceHideHeadBar and RecoverFromPoiseBreak through the existing
[`buff_direct_target_actions.py`](../../scripts/game_data/memorypack/buff_direct_target_actions.py)
owner. Each new record independently proves its source-result assignment,
generated field order and closed TargetSettings context. ForceHideHeadBar's
`finishByAction` byte is required before its target; RecoverFromPoiseBreak
has no extra field between the inherited members and its final target.
The new named records separately admit null wrappers and null targets, retain
arbitrary flag/enum bits and require physical action end. Positive targets
must reproduce their same original ranges through the recursive child owner.
Selected native inputs, including UnityPlayer, are checked before and after
the validation; missing or changed inputs empty the result. Complete root
and canonical original-owner gates remain independent of selected action-span
diagnostics. Stored flags and target settings establish neither head-bar
behavior nor accepted poise-break recovery.

The maintained
[`buff_finish_global_action.py`](../../scripts/game_data/memorypack/buff_finish_global_action.py)
and
[`buff_finish_global_action_native.json`](../../scripts/game_data/contracts/buff_finish_global_action_native.json)
now own FinishGlobalBuff's nine-member parent and its conditional original-value
ID list. The parent proves its own source/destination order and current union
route; it composes the independently owned Blackboard scalar `finishCount`
on the same original range. The required `isFinishedEarly` byte follows the
complete ID list, including null and empty lists. Exact action end remains
required. Stored flags and evaluated finish count are separate evidence lanes.

Its ID collection is independent of Stack's reference-element collection. The
[`buff_global_creation_action_native.json`](../../scripts/game_data/contracts/buff_global_creation_action_native.json)
and [`buff_global_creation_action.py`](../../scripts/game_data/memorypack/buff_global_creation_action.py)
establish GlobalBuffId's value wrapper and addressed string reference. The new
profile authenticates exact ListFormatter and original-value adapter entries,
the source-list element's type pointer, value size and generic ownership. It
keeps the registered adapter's Object wrapper argument explicit; ordinary
inflation to the concrete wrapper is a condition, not an observed MethodInfo.
Runtime reference width does not establish wire framing.

The collection profile independently authenticates the buffered signed Int32
count and its four-byte cursor accounting, minus-one null list and the element
loop with a cleared eight-byte value slot. A fixed-slot call forwards the same
reader, original output and receiver MethodInfo. The shared
[`formatter_composition.py`](../../scripts/game_data/il2cpp/formatter_composition.py)
checker also proves the original-list registration using typed usage cells,
exact source/formatter element pointers, matching generic instantiation,
constructor/register call targets and allocation-result object flow. The
reviewed byte windows authenticate explicit arithmetic instruction programs
where the general body decoder has no operand support; no undecoded operand
is inferred from a diagnostic disassembly row.

Default registration has two independently checked static paths.
`MemoryPackGeneratedInit_Gameplay_Beyond.InitEager` allocates the concrete
GlobalBuffId/GlobalBuffIdForMemoryPack adapter and forwards that same object
with the exact original type key to `RegisterWrap`. The FinishGlobalBuff
wrapper's `RegisterFormatter` separately retains its allocated
ListFormatter object through its matching constructor and passes it to
`Register<List<GlobalBuffId>>`. That registration's generic argument is the
exact source-list carrier, and the formatter's element pointer is identical
to the source-list element pointer. The ID wrapper's own registration covers
its wrapper and wrapper array; it is not the original-list registration site.
These object/type flows are direct static evidence, conditional on executing
the initialization sites. They do not establish a later provider/cache return
or the inflated companion passed to a shared physical adapter entry.

The same maintained composition checker also validates the concrete ID
wrapper's `IMemoryPackDeSerializeWrapper<GlobalBuffId>` interface argument,
its GetValue virtual slot and exact original return-type pointer. Its concrete
formatter Deserialize slot forwards to the already reviewed ID reader.
Selected module/token ranges separately preserve generic-parameter ownership
through ListFormatter, the generic adapter, ReadPackable/ReadValue and
GetFormatter contexts. A shared leaf getter needs only its explicit MOV/RET
program; a diagnostic native-unwind extent can include neighboring methods
and is not a semantic method boundary. These identities narrow the missing
conversion join without proving which inflated MethodInfo or stateful
provider result the collection used.

The actual adapter's null probe first peeks at the null marker without moving
the reader. Its true branch then consumes one byte and the adapter clears the
original value slot. On the non-null branch, the checked concrete formatter
avoids the dispatcher's optimized pointer alternatives and follows its
generic fallback with the same reader/output. The concrete wrapper's interface
offset selects its checked GetValue slot; the getter reads the ID field and
the adapter writes the returned reference into the original value slot. This
conversion is conditional on the reviewed concrete formatter/wrapper,
ordinary generic inflation and successful initialized-buffer calls. Refill,
error, allocation and stateful provider paths remain unresolved.

Under that explicit composition, the stored reader preserves list order,
null versus empty list, null wrapper versus null payload versus empty payload,
raw ID bytes and the required following parent flag. IDs are not assigned an
unproved text encoding. Independently named parent/list reads reproduce
selected complete original action spans; candidate enclosing Timeline/event
ownership is still separate. The complete current Buff family and independent
canonical original-byte root gates decide coverage. These storage and static
composition proofs establish neither evaluated IDs/finish count nor which
global Buff instances finish, finish reasons or resulting effects.

The reviewed names-only consumer groups in
[`buff_action_consumers_native.json`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
separately prove FinishGlobal's incoming owned closed `m_data` slot, its
configuration reads and compiled calls to list count/indexing, Blackboard
evaluation, parent-root lookup, RemoveGlobalBuff and MarkFinish. Its
`finishCount` reference reaches the named `GetValue.param` parameter on a
checked local compiled path. The default fallthrough traversal skips that
field on the `finishAll` path, so the count claims explicitly select the
existing complete local-branch validator. This proves a compiled path,
without asserting branch feasibility or runtime selection.

Its false-IFix `get_executeReturnType` path returns the typed
`AlwaysReturnTrue` enum policy through a complete epilogue. It does not return
the `CustomReturnType` policy used by other reviewed actions, and this enum
getter is distinct from a Boolean method named AlwaysReturnTrue.
Additional selected-program joins use the independently derived closed Data
layout and actual callee parameter types: on the checked normal parent/list
paths, the owned `isFinishedEarly` byte is compared with zero and SETNE is
forwarded into the declared byte-sized FinishReason argument. Zero selects
Default and nonzero selects Early. Server remains a declared enum alternative
that these two argument programs do not generate. Those argument programs
remain isolated from the maintained names-only claim vocabulary and never
establish which manager or global Buff instance was selected.

The `finishAll` branch loads an exact float32 minus-one constant before the
same conversion helper used after Blackboard evaluation. The actual helper
has additional calls, sign-dependent branches and SSE conversions that the
general body decoder does not fully decode. Do not replace it with an assumed
ordinary integer cast, assign minus one's gameplay meaning, or infer accepted
removal counts. Count arithmetic, receiver identity, finish acceptance and
effects still require their own proofs.

The maintained `buff_blow_off_character_action` reader uses the selected
BlowOffCharacter source windows in `buff_1c_native.json` and its reviewed
[`buff_blow_off_character_action_native.json`](../../scripts/game_data/contracts/buff_blow_off_character_action_native.json)
contract. Its distinct blackboard priority child has four required members:
key, key-selection flag, integer value and final custom-value flag.
`inherited_reference_sources` independently authenticates the runtime and
wrapper inheritance chains and concrete setter programs; it does not widen
the immediate-owner profile with guessed inherited offsets.
The runtime's closed generic parent and the base wrapper's instance field share
the exact generic-class carrier and instantiation; their field attributes
differ. The generic definition's offset table is not an inflated instance
layout. Its VAR payload is a metadata parameter index, whose reciprocal
container join supplies the ordinal; the displayed VAR number must not be
used as that ordinal. The generated integer setter's parameter pointer matches
the argument selected by this owned ordinal.

The inherited generated setters separately establish the key, key-selection
flag and value stores through the wrapper's base-instance field. The original
priority reader's normal source-result bridges reach those same stores.
Its final custom-value flag follows a distinct generated setter and instance
getter. The ordinary buffered Boolean source consumes one byte and returns
its nonzero normalization; the integer source consumes and returns four
raw bytes. Both update the same reader's current pointer and consumption
slots. The key uses the independently proved nullable signed-length UTF-8
source. Raw flag bytes remain distinct from their normalized stored values.
The custom getter's coherent non-null cache path returns the identical
underlying base instance; cache initialization and cast success remain
explicit conditions, rather than inferred synchronization.

The parent composes this child with two independently owned TargetSettings,
DirectionSettings and four nullable BlackboardDouble values in its proved
source order. The required fourth priority flag ends before the parent's
direction-angle value; a member-three Blackboard record cannot replace it.
The maintained readers reproduce complete original action spans. Complete
current-family and canonical original-byte root gates separately decide
enclosing admission. Evaluated priority/speeds, replacement and armor
decisions, selected targets, root motion and live blow-off effects remain
unresolved; a matching stored field or setter does not establish them.

The maintained names-only BlowOff consumer groups separately prove the
incoming owned closed `m_data` slot and its two target-setting references.
`attackerTargetSettings` reaches `GetFirstTarget.targetSettings`, while
`targetSettings` reaches `GetTargets_Dispose.targetSettings` in the ordinary
compiled prefix. A later same-body `GetTargetsView` name does not substitute
for this actual call-site identity. On the false selected IFix guard, the
return-policy getter returns the typed `CustomReturnType` enum through its
complete epilogue. This policy is separate from the action's Boolean result.
Later priority, speed, direction and ApplyBlowOff operands still need their
own supported instruction and ownership proofs; the large consumer body
contains SIMD/atomic operations outside the current complete decode profile.
Neither these narrow groups nor an ApplyBlowOff name proves selected targets,
accepted movement, replacement/armor decisions or live effects.

The separately reviewed
[`buff_blow_off_consumer_flow_native.json`](../../scripts/game_data/contracts/buff_blow_off_consumer_flow_native.json)
and `buff_blow_off_consumer_flow_native` loader authenticate a narrower local
return program. The actual `ApplyBlowOff` callee returns Boolean. After its
ordinary return, the selected caller updates the loop index, then overwrites
EAX with the loop count before its checked local back edge; no returned
AL/EAX/RAX value is consumed by that program. This proves a local discard,
not the whole caller's result or CFG. The action's CustomReturnType policy
and an accepted individual blow-off operation must therefore retain separate
evidence boundaries. The generic `il2cpp.call_result_discard` checker requires
the Boolean ABI, contiguous authenticated instructions, complete EAX overwrite
and an in-owner back edge; it does not need to decode the earlier SIMD/atomic
paths or infer gameplay success from a call name.

The selected `buff_timeline_empty_native.json` root context likewise exposes a
closed `List<TimelineAction.TimelineActionData>`. Its element type definition
matches the exact reference field held by the generated TimelineActionData
wrapper already reviewed in `skill_timeline_play_animation_native.json`; this
is a current metadata identity join, beyond a historical name match. Reuse the
four-member element evidence independently of SkillData's ActionGroup envelope
and first-record policy. Do not invent a SkillData prefix to pass Buff bytes
through a Skill root decoder. Positive Buff lists still need their own formatter
and nullable element parity, original spans, reached recursive actions and the
following trigger tail before gaining whole-root coverage.

[`buff_timeline_element_sources`](../../scripts/game_data/memorypack/buff_timeline_element_sources.py)
now owns the positive source elements independently of either root envelope.
Its reviewed
[`buff_timeline_element_sources_native.json`](../../scripts/game_data/contracts/buff_timeline_element_sources_native.json)
requires one authenticated entry-to-final-store program per wrapper. Timeline
reads `_endFrame`, `_sequenceActionData`, `_startFrame`, then
`forceSyncAnimData`; ForceSync reads `forceSync`, `montageName`,
`playbackSpeed`, then `targetFrame`. The shared `buffered_owned_sources`
algorithm checks actual local successors, the byref-reader/ref-wrapper ABI,
the wrapper's exact typed instance field, closed reference contexts, complete
buffered Int32/bool helpers, inline scalar cursor accounting and every owned
destination. Partial pointer writes, lost source values, wrong counters and
incomplete field programs refuse. Ordinary nonvolatile preservation across
returning calls remains conditional; the four-member header and source order
come from instructions, not runtime object size or setter address order.

The focused element codec takes absolute offsets into the original file,
reuses the independently gated Sequence reader for each reached action and
accepts only valid UTF-8 through the authenticated string helper. It preserves
raw flag, integer and floating-point bits and requires the exact element end.
Its `positiveSourceFieldsExact` receipt deliberately keeps
`recursiveStoredSchemaExact`, `positiveListAdmitted` and `wholeRootAdmitted`
false. Null Timeline/ForceSync runtime references, the list's count/loop and
conversion chain, preceding root fields and the following trigger tail remain
independent obligations. The registered Object shared-code adapter and list
entries are useful static candidates; their Object arguments must not replace
the original closed Timeline or ForceSync context. Actual provider, cache and
inflated MethodInfo selection are unresolved.

[`buff_timeline_composition`](../../scripts/game_data/memorypack/buff_timeline_composition.py)
adds an independent static registration proof, governed by
[`buff_timeline_static_composition_native.json`](../../scripts/game_data/contracts/buff_timeline_static_composition_native.json).
Generated wrapper `RegisterFormatter` methods register the concrete wrapper
formatter and wrapper array; the original runtime adapters are registered in
the separate generated `InitEager` owner. That owner allocates each exact
original/wrapper adapter, retains the object across its constructor calls,
resolves the original type handle, and passes the same object and returned
type key into `RegisterWrap`. Its concrete constructor thunks reload the
identical closed constructor MethodSpec before tail-jumping into separately
registered shared code. Absence of an exact closed generic table entry is
therefore not evidence that this concrete registration is absent; the actual
thunk, context and target must be joined. The shared Object/Object entry
identifies physical code and never replaces either concrete type argument.

The reusable `il2cpp.formatter_registration` checks complete static object/key
programs, exact allocation and registration type pointers, constructor thunk
contexts, typed helper signatures and concrete wrapper registration. The
composition additionally authenticates conversion interfaces and formatter
vtables. A typed reference `GetValue` loads the wrapper's owned original
instance, while the warmed formatter tail path preserves the same byref reader
and wrapper output into that wrapper's static source reader. Buff initialization
separately registers the original Timeline runtime-data list: its formatter
element pointer and registration carrier match the root's actual ReadPackable
context, rather than a list of generated wrappers.

This static validator remains outside root admission. It gates all native
inputs before and after validation and returns no proved rows after build
drift. Successful registration and forwarding checks do not establish that
initialization ran, that the provider/cache returned those objects, that a
nullable reference converted correctly, or that the list loop consumed its
original variable-width elements. These are separate obligations before the
source-only element receipt can gain a stored-list or whole-root claim.

[`buff_timeline_reference`](../../scripts/game_data/memorypack/buff_timeline_reference.py)
and its reviewed
[`buff_timeline_reference_native.json`](../../scripts/game_data/contracts/buff_timeline_reference_native.json)
separately authenticate the shared reference declarations, complete buffered
null path and selected conditional non-null conversion. The instance `Deserialize` takes the reader and original output by
reference. Static `DeserializeNotNull` instead takes a third `wrap` argument
by value. The selected complete helper program carries that incoming value
through the wrapper formatter's local byref slot; it does not presume an
initially null value or confuse it with a byref incoming wrapper. Each open
VAR ordinal is checked against the owning class generic container; shared Object registration
continues to identify physical code rather than concrete runtime inflation.

The reusable `reference_nullable_sources` checks the initialized, available-buffer
entry-to-return path without omitting pointer aliases, selected guard edges,
counter stores or the epilogue. Its original-byte `FF` comparison precedes
consumption: the null branch subtracts one remaining byte, advances the buffer
pointer and both counters once, and clears the original output reference.
The eight-byte output is runtime reference storage, not wire payload width.
Native drift discards this scoped proof. Source-wrapper refill/error paths,
original child dispatch, list iteration and actual provider
selection remain open; neither this proof nor a passing positive source element
admits an enclosing positive list or root.

Nonvolatile ABI preservation applies across returning calls. It does not
establish that the selected caller itself preserves a reader alias while
running its cache/query logic. The reusable
[`reference_conversion_sources`](../../scripts/game_data/memorypack/reference_conversion_sources.py)
tracks saved entry slots, temporary register reuse and the actual reader reload
on the selected initialized cache-hit branch. The same input reader and preserved
incoming wrap slot reach formatter slot five; the caller reloads the output
wrapper afterward. A null wrapper clears the original output. Otherwise the
same wrapper reaches slot zero of the original-value conversion interface and
the getter's reference return is stored into the original output. Both selected
paths include their epilogues and own every selected successor through return.

The context proof dereferences the static RGCTX payload indices rather than
trusting their recorded names. Reciprocal class-parameter ownership joins the
provider, formatter and Deserialize to the wrapper parameter, and the conversion
interface and GetValue to the distinct original parameter. Both concrete wrapper
interface tables place that typed interface after an earlier nonmatching pair;
the selected helper proves the actual ordinal increment and repeated lookup.
Concrete formatter and getter pointers differ from the helpers' optimized
special cases, so the complete ordinary-call fallback forwards the receiver,
reader/output references and MethodInfo, and preserves the getter return.

These are conditional selected programs. They assume compatible inflated runtime
contexts, the reviewed concrete provider result, normal returning calls and the
recorded guard outcomes, including the selected suffix without a GC barrier.
They do not prove cache misses, alternate probe repetitions, runtime context
inflation or provider state. The instance adapter's inlined logic is validated
independently; resemblance to the static helper never substitutes for that proof.

[`buff_timeline_instance`](../../scripts/game_data/memorypack/buff_timeline_instance.py)
and its reviewed
[`buff_timeline_instance_native.json`](../../scripts/game_data/contracts/buff_timeline_instance_native.json)
now prove the selected positive parent paths through both original-output stores
and complete returns. The positive non-FF peek consumes no bytes directly. The
parent saves its Reader and output references, passes the wrapper-owned
CreateInstance MethodInfo, preserves the returned wrapper in a local slot and
dispatches its formatter with that same Reader and slot. A null child output
clears the original; a non-null child reaches the original typed interface and
stores its getter return. Provider and Activator method parameters each have
reciprocal ownership, and both method instantiations bind the adapter's wrapper
parameter rather than its distinct original parameter.

The concrete wrappers' metadata has the abstract mask clear. Conditional on the
selected RuntimeType returning those same attributes, the parent therefore takes
the Activator branch. The direct-zero alternative cannot stand in for concrete
wrapper creation. The actual call matches the independently registered shared
CreateInstance entry. A separately authenticated class-key prefix proves that
unused incoming Reader/output pointer bits in argument registers are overwritten
before use on that selected helper path; it does not prove a complete helper
return or cache purity. The type-attribute dispatch proves its class Int32 read,
while the runtime class-to-metadata bridge remains conditional. Full Activator
invocation, allocation, cache/provider and global effects, child cursor
composition and alternate paths remain open. This parent proof stays outside
positive-list and whole-root admission.

[`buff_timeline_source_wrappers`](../../scripts/game_data/memorypack/buff_timeline_source_wrappers.py)
and its reviewed
[`buff_timeline_source_wrappers_native.json`](../../scripts/game_data/contracts/buff_timeline_source_wrappers_native.json)
separately close the initialized, available-buffer source `FF` path for both
concrete wrappers. It consumes one byte, updates all four Reader cursors and
clears the wrapper byref itself before completing the return. It does not
write the original instance's fields. One source restores its caller frame and
tail-jumps to the actual reference barrier; the other calls that barrier and
returns through its own epilogue. The independently proved disabled-barrier
path copies the output address and returns without a memory write or call;
the runtime flag state is a condition.

The same lane proves each concrete wrapper constructor's selected non-null
allocation path. The original-type usage descriptor is authenticated, the
wrapper receiver survives the allocation call, and the exact returned reference
is stored into its metadata-owned `__instance` field before the complete return.
This establishes the local field assignment under a compatible allocation
return; it does not prove allocation contents, actual Activator constructor
invocation or active barrier behavior. Source null semantics, positive field
reads and parent reference conversion have distinct ownership scopes. Their
proofs still require original child cursor composition before an enclosing
stored list can be admitted. The tracked positive-source contract records
separately closed `MemoryPackReader.ReadValue` MethodInfos for SequenceActionData
and ForceSyncAnimData at the same actual helper call target. A passed MethodInfo
name does not establish body identity with a registered shared entry. Keep this
child `ReadValue` join distinct from the root list's `ReadPackable` dispatch.

[`buff_timeline_source_returns`](../../scripts/game_data/memorypack/buff_timeline_source_returns.py)
and its reviewed
[`buff_timeline_source_returns_native.json`](../../scripts/game_data/contracts/buff_timeline_source_returns_native.json)
extend the same independently proved positive Timeline and ForceSync field
programs through their complete returns. The suffixes restore the exact caller
stack and saved nonvolatile registers, with no further calls, object writes or
Reader cursor writes. Timeline requires the final reference-store barrier's
disabled branch; ForceSync also restores its saved nonvolatile vector before
the last scalar field store. This removes the earlier last-store boundary from
the source proof. It does not supply the missing nullable original child cursor
composition or infer child wire widths from the epilogue.

[`buff_timeline_read_value`](../../scripts/game_data/memorypack/buff_timeline_read_value.py)
and its reviewed
[`buff_timeline_read_value_native.json`](../../scripts/game_data/contracts/buff_timeline_read_value_native.json)
now authenticate that actual helper's complete selected ABI and output return.
Its separately registered `ReadValue<Object>` entry differs from the called
physical entry, so named body identity stays unresolved. Reciprocal method
parameter ownership joins the closed Reader context to the provider key,
expected formatter class and slot-five Deserialize; the latter takes the same
Reader and original output by reference. The outer physical helper initializes
one local original output, forwards the saved Reader and that local, then
returns the same local in the full-width return register. It reads no Reader
fields and updates no Reader cursors directly.

The original adapter pointer matches the dispatcher's first optimized case.
That case inlines adapter logic; the already proved ordinary fallback cannot
replace it. The reusable
[`read_value_reference_sources`](../../scripts/game_data/memorypack/read_value_reference_sources.py)
owns the selected instructions, guard outcomes, context slots, locals, physical
calls and epilogues for all three output paths. Its FF branch consumes one
byte, updates all four cursors and clears the original output. Positive paths
preserve the Reader and original output, select the wrapper-owned Activator
context, save the returned wrapper, and call the actual physical wrapper
GetFormatter helper before nested formatter dispatch. The nested output either
clears the original or reaches its typed conversion interface and getter return.
The non-null output path selects the disabled-barrier state. Runtime cache,
class/context/provider selection and correctly typed normal callee returns
remain explicit conditions; anonymous cache fields do not establish collection
semantics or branch feasibility.

The known Timeline, ForceSync and Sequence wrapper formatters use the
independently proved nested ordinary fallback. The physical wrapper GetFormatter
helper's selected typed return is independently joined below. Its full effects,
original nullable child cursor composition, other paths
and root ReadPackable/list composition remain separate obligations. This scoped
transfer proof admits no child grammar, positive list or whole root and does not
observe runtime execution.

[`buff_formatter_provider`](../../scripts/game_data/memorypack/buff_formatter_provider.py)
and its reviewed
[`buff_formatter_provider_native.json`](../../scripts/game_data/contracts/buff_formatter_provider_native.json)
prove the actual helper's complete selected context and return transfer. The
incoming MethodInfo remains the same while its owned first context slot supplies
the type key and its second supplies the expected formatter class. The selected
cached candidate reaches the formatter-result helper; its non-null result is
checked against that expected class and returned as the identical full-width
reference through the complete epilogue. The body writes only caller stack
slots directly, but two indirect global calls have unproved effects. Stable
non-aliasing contexts, the selected initialized cache and correctly typed normal
helper returns remain explicit conditions. A different independently registered
Object entry still prevents promoting the physical clone to a named body.
Both the child ReadValue and selected list-control contracts require this proof;
a missing dependency cannot preserve their provider-return join. This closes
value and context transfer, not original child cursor accounting, provider/cache
effects, runtime selection or stored list/root admission.

[`buff_sequence_composition`](../../scripts/game_data/memorypack/buff_sequence_composition.py)
and its reviewed
[`buff_sequence_static_composition_native.json`](../../scripts/game_data/contracts/buff_sequence_static_composition_native.json)
independently establish SequenceActionData's concrete static composition. The
generated eager owner allocates the exact original/wrapper adapter, preserves
that object and the original type key through the closed constructor thunk,
and passes them together to RegisterWrap. The thunk reloads the identical closed
constructor context before entering the independently registered shared code.
The wrapper's RegisterFormatter allocates and passes its own concrete formatter
to Register<Wrapper>. Both selected blocks are checked inside their named
physical method extents. Allocation-null guards accept the exact short or near
JE encoding; a different condition fails the proof.

The Sequence wrapper's owned original-instance field, typed getter, conversion
interface and slot-five formatter are joined to the independently proved
Sequence source. Its warmed formatter preserves the same Reader and output
byrefs into that source. The actual formatter/getter pointers differ from all
optimized special cases, and the typed interface follows an earlier nonmatching
pair, so the complete nested ordinary-call and interface-lookup programs apply.
This composition is now a required dependency of the ReadValue contract; a
missing or mismatched dependency cannot leave the old concrete-selection gap
silently resolved. Metadata has the abstract mask clear, with runtime attributes
for the same class remaining a condition. Initialization, actual provider
selection, allocation/constructor effects and original Sequence cursor
composition remain unobserved or unproved. Static composition grants no list
or root admission.

[`buff_sequence_array_source`](../../scripts/game_data/memorypack/buff_sequence_array_source.py),
[`array_reference_sources`](../../scripts/game_data/memorypack/array_reference_sources.py)
and the reviewed
[`buff_sequence_array_source_native.json`](../../scripts/game_data/contracts/buff_sequence_array_source_native.json)
now prove the complete selected buffered array control inside that named
Sequence source. Its actual usage is `ReadArray<AbilityActionData>`; the single
owned context slot joins the `ReadArray(ref T[])` overload, whose reciprocal
method parameter independently binds Empty, the array class, provider,
formatter class and slot-five Deserialize. A similarly named ArrayFormatter
is not evidence for this inline path. Static context records are not runtime
context slots, and the proof does not observe their inflation or selection.

Complete wrapper-FF, null-array, empty-array and single/repeated positive-element
programs authenticate every selected successor through return. They prove the
signed count and remaining-length guard, all four direct cursor updates, the
allocation/count and provider arguments, the unchanged Reader, the repeated
child-call block and both ordered normalized flag stores. The caller advances
seven direct bytes for a nonnull Sequence, plus the child advances; the child
advances themselves remain unresolved. A wrapper FF advances one byte and
clears the wrapper reference through the independently proved disabled barrier.
The runtime element address is array base plus its data offset and index times
reference stride; this says nothing about a child wire width.

The selected paths require warmed compatible contexts/classes, stable
non-aliasing typed objects and local storage, valid buffered/counter bounds,
normal correctly typed helper and child returns, disabled reference barriers
and the Win64 stack/nonvolatile ABI. Full return includes exact stack and
nonvolatile restoration. Passing an Empty MethodInfo to a physical helper does
not name that helper or prove its managed effects. Empty/allocation identity
and effects, child grammar/cursor composition, alternate GC/refill/error/reuse
paths and runtime selection remain open. This source control proof grants no
child, positive list or complete root admission.

[`buff_timeline_list`](../../scripts/game_data/memorypack/buff_timeline_list.py)
and its reviewed
[`buff_timeline_list_control_native.json`](../../scripts/game_data/contracts/buff_timeline_list_control_native.json)
add a separate selected list-control proof. The buffered header reads a signed
Int32 count, consumes four bytes and updates all four Reader cursor fields.
Its count guard compares against `totalLength - consumed`; this guard does not
determine any element's wire width. The loop retains the same Reader, clears a
local reference before each element dispatch and loads both the method and its
MethodInfo from formatter slot five. It appends the returned reference using
the runtime array's pointer stride, increments the index and compares against
the saved original count. Temporary reuse of the count register does not replace
that saved count. A separately authenticated repeated program reaches the same
complete block through the actual back edge, and both paths include the return.

Static reciprocal ownership joins List, Clear, GetFormatter, element formatter,
Deserialize and Add to the same original element parameter. The selected
programs cover an existing list with spare capacity and normal returning calls.
The physical helpers receiving Clear and GetFormatter contexts differ from
the independently registered Object method entries. Their passed contexts do
not establish body identity. [`list_context_helpers`](../../scripts/game_data/memorypack/list_context_helpers.py)
independently proves the actual reset helper writes the caller's index slot to
zero and increments its version before branching on the old count; the
nonpositive path returns without calls. Its selected positive path passes array
data, zero and a sign-extended Int32 product to a span helper, whose writes
remain unresolved. The intended formatter result and compatible runtime contexts remain conditions;
allocation, growth, refill/error and GC-barrier paths remain outside this proof.
The same actual formatter helper now has the independently required key/class
and complete typed-return proof above; this does not close its indirect global
effects or establish runtime formatter selection.
Original nullable child composition and cursor accounting, allocation state
and complete root composition remain required for stored-list admission.
Neither the pointer stride nor a passing selected loop
promotes source-only elements to a positive list or whole root.

[`buff_timeline_root_list`](../../scripts/game_data/memorypack/buff_timeline_root_list.py),
[`packable_reference_sources`](../../scripts/game_data/memorypack/packable_reference_sources.py)
and [`new_list_reference_sources`](../../scripts/game_data/memorypack/new_list_reference_sources.py)
extend this control proof under the reviewed
[`buff_timeline_root_list_native.json`](../../scripts/game_data/contracts/buff_timeline_root_list_native.json).
The root's owned `ReadPackable` parameter joins its nested `ReadValue` slot.
The actual called helper inlines formatter selection, preserves the same Reader,
zeroes its local reference output, dispatches the concrete list formatter through
the ordinary fallback and returns the same full-width output through its complete
epilogue. Its independently registered Object entry differs, so the physical
body's named identity remains unresolved. A separately checked local root
program passes the current Reader and stores that returned reference into the
owned timeline field. This local join does not prove Reader/wrapper provenance
from the full root entry or the root's remaining fields and tail.

Complete selected null-list, empty-new-list and single/repeated new-list programs
now join allocation and the capacity constructor to the same independently
proved element loop. They retain the original count, same Reader, constructed
list and output location through return. The actual capacity constructor matches
its independent shared List registration; its reciprocal class parameter joins
the List and element-array context slots. The positive path forwards the signed
capacity unchanged to array allocation and stores the returned reference into
the observed receiver slot. The zero-capacity path stores its loaded static
reference. Both restore the caller frame, and the constructor/list output paths
use the same independently proved disabled barrier state.

The receiver reference slot remains a structural observation: open generic
field offsets are placeholders and are not used to name it. Neither selected
constructor path writes a count or version, so a freshly allocated list's zero
count and sufficient array capacity remain conditions, alongside compatible
runtime contexts/classes, correctly typed normal helper/child returns, stable
non-aliasing storage and the Win64 ABI. Actual allocation, static-field parity,
cache/global effects and runtime selection remain open. RIP-relative targets
are computed from complete instruction bytes, including trailing immediates;
candidate disassembly text cannot authenticate them. No child grammar,
positive list or whole root is admitted by this control proof.

[`buff_timeline_cursor_composition`](../../scripts/game_data/memorypack/buff_timeline_cursor_composition.py)
joins the complete nullable ReadValue paths, concrete wrapper forwarding,
Sequence array source and Timeline/ForceSync source returns. On the selected
buffered paths the outer helper adds no direct cursor advance. The adapter's
FF branch consumes one byte and updates all four cursors; its positive branch
only peeks at that byte, leaving the concrete source to consume the object
header once. Continuity requires stable buffered bytes and no cursor changes
through indirect/global aliases during the intervening non-reading helpers.

The positive Timeline source directly consumes its one-byte header and two
Int32 fields, plus the advances of the nullable Sequence and ForceSync children.
Positive Sequence consumes its header, array count and two flag bytes, plus
the action callbacks' advances. Positive ForceSync consumes its header,
normalized byte and two four-byte scalars, plus the string helper's advance.
Reference destination widths do not enter these wire equations. Complete
source epilogues add no calls or Reader writes. A bounded audit now checks
these framing equations against the unchanged certified original element,
Sequence/action and UTF-8 spans. Null objects, null arrays, empty arrays and
raw flag bytes remain distinct; an unproved null ForceSync source receipt is
refused. The original source-only receipts retain their admission boundary.
Equality between callback native advances and their certified stored spans,
full string-helper cursor/global effects, runtime selection and allocation
state remain separate obligations. This arithmetic audit grants no positive
list or whole-root admission and does not reparse previously passing sources.

The action array needs a distinct original/base-wrapper/union callback join.
[`buff_action_union_header`](../../scripts/game_data/memorypack/buff_action_union_header.py)
authenticates the selected original array element and all three metadata owners
through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_action_union_header_native.json).
Both `AbilityActionData` and its generated base wrapper are abstract; the union
formatter is concrete. The original/base-wrapper adapter is independently
located in `InitEager`: its allocation, closed constructor context, original
type key and `RegisterWrap` call form one checked flow. Its constructor thunk
joins an independently registered shared entry. The concrete union formatter's
separate registration reaches `Register<Wrapper>`. Static registration does
not establish runtime provider selection. The concrete Timeline/ForceSync
creation proof cannot cover this abstract wrapper's alternate creation branch
without the runtime class-attribute bridge. The requested schema bundle
locates names only; its old registrations and addresses are not reused.

[`buff_action_array_callback_binding`](../../scripts/game_data/memorypack/buff_action_array_callback_binding.py)
now joins that eager binding to the array's independently owned transfer through
its [`reviewed contract`](../../scripts/game_data/contracts/buff_action_array_callback_binding_native.json).
The shared
[`formatter_callback_signatures`](../../scripts/game_data/il2cpp/formatter_callback_signatures.py)
validator checks the sealed reference adapter, reciprocal class-generic owners,
the original-type substitution in its formatter parent, and the declared
instance virtual `Deserialize` slot. Its void return, byref unboxed Reader and
byref original reference output match the array's saved Reader, receiver and
indexed pointer-sized output. This is an exact declaration and static-transfer
join; it does not identify the runtime receiver or its inflated method.

The adapter's selected vtable entry names its metadata method definition. The
abstract base's selected slot is separately checked as stored representation;
it is not interpreted as a native callback address. Independently registered
shared code is still distinct from an inflated closed MethodInfo and companion
vtable entry. A missing unique closed entry in the compiled registration table
does not prove that runtime generic inflation cannot construct one. Provider
registration/cache identity, actual callback selection and callback advances
remain unresolved, so this binding admits no child, positive list or root.

[`buff_formatter_registration_state`](../../scripts/game_data/memorypack/buff_formatter_registration_state.py)
continues the eager registration through the complete named `RegisterWrap`
caller, using its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_registration_state_native.json)
and the shared
[`registration-state transfer validator`](../../scripts/game_data/il2cpp/formatter_registration_state.py).
The original type key and adapter reference reach `ConcurrentDictionary.set_Item`
together, after restoring the caller frame. Its MethodSpec and the named
`GetFormatter_` lookup's `TryGetValue` MethodSpec share the exact closed
`ConcurrentDictionary<System.Type, IMemoryPackFormatter>` instantiation. Both
read the same provider class usage cell and dictionary address expression.
The selected warmed first-hit lookup returns its full byref reference output;
only AL selects that hit. The complete public `GetFormatter(Type)` caller
preserves its type key and tails to the same physical result helper called by
the independently owned array provider.

This closes caller argument/return and static context joins. It does not prove
the dictionary mutation, equality comparer, retrieval, initialized cache contents
or the physical result helper's inlined lookup control. The declared static
field-offset word and native class-carrier displacements remain structural-only;
equal address expressions require stable initialized live storage. Some provider
loads select image regions without on-disk backing, so the installed bytes do
not supply their runtime values and cannot establish an empty cache. Live
class/MethodInfo/vtable selection and action callback cursor equality remain
separate requirements. No positive list or root gains admission.

[`buff_formatter_dictionary_lookup`](../../scripts/game_data/memorypack/buff_formatter_dictionary_lookup.py)
now authenticates the named lookup caller's original call and the callee's
complete unwind-owned instruction inventory through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_dictionary_lookup_native.json).
The shared
[`lookup-control validator`](../../scripts/game_data/il2cpp/dictionary_lookup_control.py)
checks every local branch against original instruction boundaries, including
the node loop, full reference output and restored return frame.

The selected word producer's original dword is retained for candidate word
comparison. A separate copy clears its sign bit, is sign-extended into the
double-width dividend and undergoes signed division. The remainder, rather
than the quotient, passes an unsigned bound guard and supplies the
pointer-sized slot index. With a positive signed divisor and stable compatible
storage this is the sign-cleared word modulo that divisor. The
[`signed-integer decoder`](../../scripts/game_data/il2cpp/signed_division.py)
owns the complete BTR/CDQ/IDIV encodings, operand widths, implicit registers,
divide faults and undefined flags. These instruction facts follow Intel's
[instruction reference](https://cdrdv2-public.intel.com/835781/325462-sdm-vol-1-2abcd-3abcd-4.pdf).

The ordinary node route compares the original word, forwards the original
query and candidate key to the selected predicate, and follows the next-node
reference when no candidate is selected. A finite stable miss clears the full
byref reference and returns false in AL. A hit copies the full node value and
returns true through the shared restored frame when the barrier flag is zero.
The guard's RIP target is computed from all original bytes, including its
immediate; the older mapper's displayed target for this form omits that final
byte and cannot supply the flag identity. LOCK operations on stack storage
retain their writes/order role; no whole-method purity is claimed.

This is conditional anonymous storage/control evidence. Valid compatible
memory, stable carriers/chain, normal ABI-compatible helper returns, a positive
divisor, valid disjoint output and the selected disabled barrier remain
conditions. The word producer's hash meaning and predicate's equality meaning
are not inferred from their callers. Closed generic field identities, live
dictionary contents, setter mutation, active barrier effects, physical result
helper control, runtime class/MethodInfo/vtable selection and callback cursor
equivalence remain open. The instruction coverage audit and opaque-helper
inventories belong in generated reports; this proof admits no positive list
or complete root.

[`buff_formatter_comparer_dispatch`](../../scripts/game_data/memorypack/buff_formatter_comparer_dispatch.py)
now joins the lookup's actual selector/argument transfers to both complete
word and predicate dispatch programs through its
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_comparer_dispatch_native.json)
and the shared
[`dispatch-control validator`](../../scripts/game_data/il2cpp/comparer_dispatch_control.py).
The caller selects one for word production and zero for the predicate; both
helpers explicitly truncate the selector to UInt16. Their record scan uses a
word count and word counter with unsigned guards. Because increment occurs
only below that count, ordinary exhaustion precedes low-word wrap. A matching
record's dword offset plus selector wraps at dword width before signed
extension and pair-address arithmetic. Function and companion method-context
qwords are loaded together; the fallback receives the original receiver,
context and narrowed selector.

The ordinary indirect routes preserve the original key arguments and selected
method-context word. Complete specialization branches and restored returns
are checked separately. One predicate specialization compares the two full
reference words directly and returns true/false in AL; byte XOR does not
establish a zero full return register. Other branches retain opaque object
or payload helper calls and their normal-return/compatible-storage conditions.
The
[`integer-width decoder`](../../scripts/game_data/il2cpp/integer_widths.py)
owns CDQE, word MOVZX/CMP/INC and register-byte XOR; the older display's widened
register names cannot establish these source widths. The instruction facts
follow Intel's [extension/reference](https://cdrdv2-public.intel.com/835781/325462-sdm-vol-1-2abcd-3abcd-4.pdf)
and [increment reference](https://cdrdv2-public.intel.com/782156/325383-sdm-vol-2abcd.pdf).

This closes anonymous dispatch control, not named runtime interface/slot
identity. A pointer comparison against a compiled specialization cannot select
the live comparer or substitute a nominal compiled generic instantiation for
an inflated MethodInfo. Current registered-target inventories remain candidates
under the [compiled registration index](../../scripts/game_data/il2cpp/body_claims.py);
class preparation, fallback resolution, opaque child effects, actual hash/
equality meaning and live cache/class selection require further evidence.
An absent primary unwind extent for a preparation helper does not prove an
empty function or no effects. Action callback identity/cursor and list/root
admission remain separate.

The preparation entry and fallback resolver now have a separate
[`conditional control proof`](../../scripts/game_data/memorypack/buff_formatter_dispatch_fallback.py)
under their
[`reviewed contract`](../../scripts/game_data/contracts/buff_formatter_dispatch_fallback_native.json).
The preparation entry is a complete pointer-load/tail-jump transfer; its lack
of a primary unwind record does not prevent proving that transfer to the
independently owned target. That target tests stored bytes and either restores
its frame immediately or calls three actual helpers with a saved global-address
stack slot and the original loaded argument. Its middle helper receives the
slot's address, so the final forwarded slot value is not assumed unchanged.

The resolver retains the original receiver/context and truncates its selector
to UInt16 before the first child call. A nonnull first result returns unchanged.
If that result is null, anonymous byte/pointer gates decide whether an alternate
child is called with the original arguments; a nonnull alternate result is
preserved across a continuation and returned through the shared restored frame.
The remaining path calls an opaque failure helper and then reaches INT3 if it
returns. Valid compatible stable storage and normal ABI-compatible helper
returns remain conditions. These facts do not identify initialization, locking,
search semantics, mutation, live class/interface selection or actual effects.

[`integer_source_operands`](../../scripts/game_data/il2cpp/integer_source_operands.py)
owns complete source-memory ADD/AND, immediate IMUL, byte TEST and byte MOVZX
encodings. Immediate widths, memory widths and full instruction ends matter;
the former linear display had split immediate bytes into apparent returns and
other instructions. An unknown directive is recognized by its leading `db`,
not a substring in a hex operand. Instruction facts follow Intel's
[instruction reference](https://cdrdv2-public.intel.com/868137/325462-089-sdm-vol-1-2abcd-3abcd-4.pdf)
and [TEST reference](https://cdrdv2-public.intel.com/874240/325462-090-sdm-vol-1-2abcd-3abcd-4.pdf).
An owned resolver range can mix executable code, indexed dispatch tables and
padding; linear decoding of the whole range cannot certify that boundary. The
four resolver-child control owners below each partition their complete
primary/chained unwind-owned bytes into code, table data and padding, and check
every original branch, terminal transfer, indirect dispatch site and stored
table target against instruction boundaries. Their facts are `conditional`
on compatible stable storage and normal ABI-compatible child returns; none
extends the recursive storage reader's admission or the validated corpus
reader, and each fails closed through the selected native/source gates.

- **Resolver scan** --
  [`buff_formatter_resolver_scan`](../../scripts/game_data/memorypack/buff_formatter_resolver_scan.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_resolver_scan_native.json),
  lane [`il2cpp/resolver_scan_control`](../../scripts/game_data/il2cpp/resolver_scan_control.py)).
  Byte-selector/DWORD-target tables with guarded routes, non-wrapping record
  (UInt16) and parameter (DWORD) counters, and two closed-return index leaves.
  The resolver returns zero on missing context or exhausted records, else the
  receiver-relative pair address (DWORD offset + UInt16 selector, biased and
  scaled). Index arithmetic does not prove a live metadata header, bounds or
  valid records.
- **Carrier conversion** --
  [`buff_formatter_carrier_conversion`](../../scripts/game_data/memorypack/buff_formatter_carrier_conversion.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_carrier_conversion_native.json),
  lane [`il2cpp/carrier_conversion_control`](../../scripts/game_data/il2cpp/carrier_conversion_control.py)).
  A nonnull selected global returns unchanged; zero falls back to the input
  tag; other routes tail-forward the input, its payload, or a recursively
  obtained carrier with retained argument widths. No inline global/payload
  writes. Because the resolver reads the same global expressions, returned
  carriers support `conditional` value equality with the comparison carriers
  while the globals stay stable; this identifies no initialized runtime type.
  Recursive termination and tail-child effects are unproved.
- **Relation control** --
  [`buff_formatter_relation_control`](../../scripts/game_data/memorypack/buff_formatter_relation_control.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_relation_control_native.json),
  lane [`il2cpp/relation_control`](../../scripts/game_data/il2cpp/relation_control.py)).
  Equal input pointers return true before any call; other paths carry
  enumerated stack/global/context writes (locked exchange-add and
  compare-exchange -- a failed CMPXCHG still writes -- plus ordinary stores),
  so the relation is not read-only. Indirect calls prove only the storage
  address. Corrected RIP-relative immediate-store decoding joins one store to
  the shared global DWORD, not the adjacent cell the legacy display showed.
- **Relation imports** --
  [`buff_formatter_relation_import_control`](../../scripts/game_data/memorypack/buff_formatter_relation_import_control.py)
  ([contract](../../scripts/game_data/contracts/buff_formatter_relation_import_control_native.json),
  lanes [`il2cpp/relation_import_control`](../../scripts/game_data/il2cpp/relation_import_control.py)
  and [`il2cpp/pe_imports`](../../scripts/game_data/il2cpp/pe_imports.py)).
  The relation's indirect storage sites are `exact` on-disk import
  declarations of `baselib.dll` thread-ID and system-semaphore acquire/release
  (walked lookup tables and unbound IAT slots, never address proximity). The
  call sites implement an owner/reentry counter around a semaphore handle;
  this is declaration coverage, not a live IAT binding, initialized lock state
  or an executed acquire. The context pointer reloaded after the child call is
  treated as a fresh value.

Instruction-width facts these owners depend on live in
[`integer_tag_dispatch`](../../scripts/game_data/il2cpp/integer_tag_dispatch.py)
(signed-extension/compare/increment operands),
[`integer_decrement`](../../scripts/game_data/il2cpp/integer_decrement.py)
and [`integer_effects`](../../scripts/game_data/il2cpp/integer_effects.py)
(locked exchanges, unary arithmetic, physical write spans).

Still `unresolved`: typed conversion/relation meaning, named
class/interface/slot and inflated MethodInfo, initialization/cache/lock
semantics, the Baselib export bodies and context children's stack-slot writes
(next candidates; missing byte INC/OR decoding there is a tooling gap),
callback cursor equivalence, and positive list/full-root admission.

The union formatter's caller prefix saves its entry Reader and wrapper output,
initializes a UInt16 stack local, passes the same Reader/local to the actual
physical tag helper, tests only AL and reloads that unsigned word on success.
The helper's three selected buffered paths are checked through complete returns:
markers below `FA` consume one byte and produce that tag; `FA` consumes two
additional little-endian bytes and produces a UInt16 tag; `FB` through `FF`
consume one byte, write zero and return false. Each read updates the pointer,
remaining length, advanced count and consumed count. Saved nonvolatile state
and the frame are restored. Success establishes AL only; the false path clears
the full return register. These claims require warmed caller/helper state,
valid buffered/counter bounds, disjoint stable Reader/buffer/output/caller
storage and the Win64 ABI. The helper has no uniquely named metadata owner.

This native false behavior does not admit reserved `FB..FE` markers as canonical
stored nulls; the existing reader still requires its proved `FF` null encoding.
The header proof ends at the caller prefix. A separate
[`buff_action_reference`](../../scripts/game_data/memorypack/buff_action_reference.py)
proof, owned by its
[`reviewed contract`](../../scripts/game_data/contracts/buff_action_reference_native.json),
now follows the same actual shared adapter through the abstract branch. When
the owned runtime attribute query reports the abstract mask, the branch sets
the full wrapper reference local to zero instead of calling `Activator`.
The same saved Reader and initialized local reach slot-five child dispatch.
Complete zero and nonzero child-output paths respectively clear the original
output or call its owned typed getter and store that reference. Full frame and
nonvolatile restoration is preserved. This extends the existing instance
ownership algorithm with an explicit abstract mode; it does not reinterpret
the previously proved concrete creation paths. Matching runtime attributes,
inflated contexts/provider results, typed normal child returns and stable
Reader aliases remain conditions. Static eager registration does not establish
that the actual array callback selected this adapter.

The union formatter's AL-false branch is also proved through complete return:
its saved, zero-initialized RSI clears the full wrapper output, and the caller
passes that same output address to the actual barrier call. That target is a
short jump entry into the independently proved shared barrier, not a separate
barrier inferred from address proximity. Only its actual first jump is needed;
no complete leaf extent is inferred in the absence of a function-range record.
With the shared barrier disabled, its selected path has no calls or memory
writes and returns to the restored union caller. No direct Reader writes occur
outside the tag helper. The disabled state and indirect/global alias effects
remain conditions; this proof does not cover an active barrier.

Actual array callback/class/provider selection, positive union switch and
concrete-child advances relative to original spans, initialization/refill/error/
global effects and complete list/root composition remain open. Reserved-marker
false behavior still grants no canonical null admission. No grammar, positive
list, whole root or gameplay effect gains admission from these control proofs.

[`buff_pick_target_union_route`](../../scripts/game_data/memorypack/buff_pick_target_union_route.py)
now closes the selected new-child route for the leading reached
`PickTargetAction`, with its own
[`reviewed contract`](../../scripts/game_data/contracts/buff_pick_target_union_route_native.json).
The current UInt16 tag passes an unsigned range check, indexes four-byte
unsigned RVAs and adds the actual image base before the computed jump.
The current table entry selects the independently checked wrapper; old bundle
ordinals are not reused. On entry with a null wrapper output, the actual cast
helper has a complete no-call path returning a full null reference without
class or Reader dereferences. The route preserves the same saved Reader and
loads a closed `ReadPackable<PickTargetWrapper>` context.

That child entry is a two-instruction context thunk: it reloads the identical
closed MethodSpec into RDX without changing RCX, then jumps to the already
proved actual shared ReadPackable body. Its reciprocal generic parameter,
owned nested ReadValue/provider/formatter contexts and complete initialized
local-output/Reader/return transfer are reused. An unrelated Object entry does
not supply this physical identity. The route stores the full returned child
wrapper and passes that same value/address through the actual disabled shared
barrier before restoring the complete union caller. No Reader cursor writes
occur in the route or thunk; header and concrete child advances remain distinct.
No full leaf extent is inferred for the context thunk.

These are conditional control/value joins: initialized compatible inflated
contexts/cache/provider results, the selected tag and null prior wrapper,
stable disjoint storage, typed normal child returns, disabled barrier and
Win64 preservation remain required. Actual array virtual selection, reused
wrapper paths and native callback advancement relative to original spans
remain open. Its current named source identifies the
inherited action fields followed by `contextKey`, BlackboardInt `index` and
TargetSettings `target`; the route proof alone does not admit those payloads,
positive lists, whole roots or gameplay target selection.

The maintained [`PickTarget storage reader`](../../scripts/game_data/memorypack/buff_pick_target_action.py)
and its [`source contract`](../../scripts/game_data/contracts/buff_pick_target_action_native.json)
now extend that route into the concrete seven-member source. A complete
buffered object-header helper writes the original byte to the caller's local,
updates all four Reader counters and returns the FF comparison in AL. The
positive source forwards its inherited enable byte and three DWORDs, then
`contextKey`, BlackboardInt `index` and TargetSettings `target`, through the
actual generated setters. The concrete getter's coherent-cache path returns
the same underlying base instance; the source and setters restore their
ordinary frames. Allocation, refill, exceptional paths, active barriers and
actual provider choice remain independent conditions.

The BlackboardInt proof strengthens the previously named child with complete
ordinary header, source-result/store and return programs. Its inherited key,
use-key flag and integer value belong to the same closed `int/int` base carried
by its generated wrapper. The value's VAR record names a metadata parameter
index, whose owning container determines the relative argument ordinal; the
record's integer must not be used directly as that ordinal. Generic-definition
offset placeholders do not establish destinations: the emitted closed setters
and source stores do. Raw flag, DWORD and string bytes are retained, and the
typed TargetSettings field delegates to the existing recursive target owner.
Canonical null wrappers and children keep exact bounded spans. Any unsupported
target interior, wrong typed evidence, malformed child or incomplete action
refuses the action. The complete current corpus gate and independent
original-element/root replays now validate this extension. Complete roots
retain their other blockers. The newly reached following action also makes
selected refusing Timeline elements relevant again: complete unchanged
PickTarget decoder returns before that same refusal can be retained as
independent original action receipts. Passing elements are reused. A closed
action does not admit its enclosing element, positive list or root; native
callback selection and advancement remain distinct from stored-span closure.

The names-only
[`consumer claims`](../../scripts/game_data/contracts/buff_action_consumers_native.json)
also independently join the actual `ExecuteInternal` receiver to its closed
`AbilityAction<Data>` slot. That owned Data supplies `contextKey`, `target` and
`index` reads; the integer reference reaches the named static
`ActionBlackboardExtensions.GetValue.param` argument with an Int32 return ABI.
The compiled body contains the target-list getter, `GetTargetsView`, `SetTarget`
and `Context.UpdateTargetGroup` calls. The existing argument checker excludes
the aggregate return ABI of `GetTargetsView`, so its target argument is not
promoted from call proximity. Key-to-update forwarding, evaluated index,
selected list item, bounds result, target-group writes, IFix selection and
actual execution remain separate gaps. This consumer claim supplies no stored
payload, positive-list or complete-root admission.

The next reached `EffectLineCenterAction` now has a maintained
[`source-field validator`](../../scripts/game_data/memorypack/buff_effect_line_center_action.py)
and a separately reviewed
[`current native contract`](../../scripts/game_data/contracts/buff_effect_line_center_action_native.json).
Its generated declaration has nineteen members, eighteen inherited. The
historical bundle omits the current inherited `bigEffectTarget`; its old member
count and union ordinal cannot supply the current layout. The actual reader
compares the current member count and performs individual source/setter calls,
rather than delegating the inherited prefix to the concrete EffectAction
reader. The first four fields use AbilityAction setters, the next fields use
EffectAction setters and the final `effectCenter` uses its own derived setter.
Current closed contexts independently identify the TargetSettings and
EffectActionCfg source returns.

The proof pairs actual wrapper and runtime ancestries, validates each owned
setter parameter and field, and carries the same saved Reader/ref-wrapper
through the ordered source calls and complete ordinary return. Base Effect
setters have their own inlined coherent-cache checks before the typed field
store. The derived target setter calls its concrete coherent-cache getter and
uses a full displacement store; it must not be reduced to a signed-byte
offset. Reference stores reach the independently proved shared barrier.
The switch route's actual RIP-relative load is joined to its recorded usage
cell as well as to the current table and wrapper identity.

The buffered object-header proof now lives in the shared
`buffered_owned_sources` owner and checks the complete ordinary byte read,
caller output, cursor commits, FF comparison and returned AL. The derived
reader's false-header branch clears its original ref-wrapper output, passes
that output to the shared barrier and jumps into the complete saved-register
epilogue. It skips the RSI restore used only after the positive header path.
Refills, exceptions and ordinary returning-call assumptions remain conditional.

The derived bounded decoder now reads its own nineteen-member original span.
Five separate TargetSettings fields and the EffectActionCfg field must join
their closed source contexts to the actual runtime type in each child wrapper's
instance field; wrapper and runtime definition indices are not interchangeable.
The configuration's independent `decode_effect_config_value` entry point names
its complete direct fields and scalar/vector interiors while preserving raw
values and null/empty terrain-effect collection states. Positive terrain-effect
arrays still refuse. Prepending an EffectAction tag or changing the derived
header to fit a parent-bound receipt is not a valid join.

The structural and recursive action dispatchers use this derived owner. Fresh
native validation, the complete current corpus gate, original source-element
replay and selected canonical root replay have passed. Prior complete elements
and roots are retained; additional original source elements now close through
their own derived action and child spans. Related partial roots still refuse at
the positive Timeline list boundary. Closing all source elements in a selected
file does not supply the array callback/cursor proof for its enclosing list.
Current inventories remain in generated reports. These stored-byte proofs do
not establish enclosing positive-list/root admission, actual array/provider
selection, target evaluation or effect execution.

Child source binding must respect each validator's actual input surface. The
metadata-owned wrapper plan authenticates GameAssembly and metadata, and its
hash strings may use lowercase. The independently validated target,
configuration and vector owners authenticate the full selected three-input
build. Comparing the plan to that larger dictionary wrongly rejects the
selected build; requiring its own exact keys and case-insensitive hash values
preserves the input gate. A child-binding failure names the specific owner,
status, inputs or ordered layout instead of truncating the entire recursive
child catalog. A failed native join must leave the previous complete corpus
report as a comparison baseline.

Consumer layout and conditional preparation flow have a separate
[`validator`](../../scripts/game_data/buff_effect_line_center_consumer_native.py)
and [`reviewed contract`](../../scripts/game_data/contracts/buff_effect_line_center_consumer_native.json).
The closed generic Data reference is witnessed by EffectAction's completely
occupied concrete field suffix. Its immediate EffectLineCenter receiver adds
no instance fields and has the same selected instance extent. Open generic
offsets are not substituted for that proof. The named target helper returns an
AbilitySystem; the selected ancestry supplies its Entity field through
BaseComponent. The concrete runtime type declares `PreExecuteInternal`, while
the inspected effect execution body belongs to its EffectAction parent.

The independent [`Vector3 leaf checker`](../../scripts/game_data/il2cpp/vector_arithmetic.py)
proves all three Single left-minus-right components, their twelve-byte output
and the returned original buffer through the complete straight-line RET. The
leaf requires neither a guessed next-method boundary nor the subset decoder's
unsupported unpack instruction. This is a compiled arithmetic/callee ABI
fact; caller arguments require the separate complete preparation grammar.

The current consumer contract now proves the complete preparation caller,
including original local branch destinations and its whole return frame.
The independent [`conditional-move decoder`](../../scripts/game_data/il2cpp/conditional_moves.py)
keeps CMOV as a flags-dependent write retaining the old destination on the
other outcome; fallback bytes are not allowed to invent jumps or pops.
The [`program grammar`](../../scripts/game_data/il2cpp/program_grammar.py)
checks branch predicates from original bytes and closes labels at checked
instruction boundaries. Memory widths are checked separately where a decoded
operand name alone would hide a partial reference-slot clear or a wider flag
comparison.

The source and center calls receive their respective TargetSettings and the
original input TargetHandleView. The handle's sole reference field and selected
boxed size establish its single-pointer unboxed representation. The complete
reference-filter helper returns its original input or null; its called class
predicate remains opaque. The actual initialized TypeInfo usage cell selects
the concrete EffectLineCenter Data declaration, but this does not observe a
runtime object or prove the predicate's meaning. Each current `forceMainBody`
zero branch alone enters that target's remap. A true Boolean return selects
the byref output; false retains the original AbilitySystem. The context helper
and actual target/out-slot values remain unevaluated.

Under the caller's unpatched branch and both Entity getters' validated primary
fallthrough returns, all three center-position and source-position components
are copied before either buffer is reused. The subtraction inputs and output
are disjoint, the complete leaf returns its original output buffer, and the
caller writes the twelve-byte center-minus-source displacement into
`centerOffset` of the configuration obtained from its final current Data
reload. Null selected AbilitySystem values branch to the complete epilogue
without that write. `centerOffset` remains an unserialized runtime field;
the persisted `positionOffset` is not this destination. The getter proof is
explicitly conditional on its primary return: initialization, IFix and other
getter paths are not admitted by it.

EffectAction's ordinary `OnCreate` loads the Data's configuration reference
after its base call and stores that same reference in `m_effectActionCfg`;
the checked assignment does not clone it. This closes the creation-time
cache assignment, not later object identity. Data reloads across intervening
calls are not equated, and neither stable references over the action lifetime
nor parent `ExecuteInternal` consumption and effect creation are proved.
These static consumer facts add no serialized field or list/root admission,
and do not establish observed target selection or effect execution.

The independent [`trail consumer validator`](../../scripts/game_data/buff_effect_line_center_trail_native.py)
now checks the ordinary entry prefix that reads the current EffectInstance
`m_data` configuration and forwards all three `centerOffset` components before
calling the current trail receiver's `Start`. Its static query/enumerator
MethodSpec cells consistently select VFXTrailPointsTool; initialized generic
objects and actual query results remain conditional. Ordinary `Start` skips
point calls when `isErosionLine` is nonzero. The trail's offset predicate checks
exact component zero, including negative zero, and treats NaN as nonzero;
the effect-instance entry instead compares the squared displacement to a small
float threshold. The parent execution/configuration lifetime join remains
open, alongside initialized component/query results and actual execution.

The independent [`point consumer validator`](../../scripts/game_data/buff_effect_line_center_points_native.py)
checks the complete ordinary `_ApplyCenterOffset` loop and its per-iteration
value flow. It first requires at least two source points, increments the
temporary list's compiled version slot and zeros its count slot, then checks
the offset predicate and calls `_GetPoints`. The deformation loop begins at
index one. This proves that the loop does not overwrite index zero; preservation
of the original first point still requires the initial population/alias join.
The physical list slots and twelve-byte array stride come from complete
selected get/set consumers and their Vector3 MethodSpecs. Open `List<T>` field
offsets are placeholders and are not used to claim a closed runtime layout.

Within a checked iteration, a complete TransformPoint wrapper binds the input
and output buffers. The loop converts the signed point index and count-minus-one
to Single, multiplies `right` by the converted index and then by
`offset.x / converted(count - 1)`, adds that vector to the TransformPoint output,
and repeats the two multiplications for `forward` and `offset.z` before adding
them to the first sum. These are ordered native Single operations: the multiply
leaf uses the scalar low lane as its first operand, and the formula must not be
collapsed into real-number interpolation or an exact endpoint displacement.
The complete addition/multiplication/axis leaves establish their returned
twelve-byte output buffers and preserve the held list/result pointers used by
the caller. Only x/z are direct displacement operands in this loop; y still
participates in the earlier zero predicate, so a y-only offset is not dismissed
as an inactive path.

The complete InverseTransformPoint wrapper returns its original output buffer,
whose twelve bytes pass through a proved copy wrapper to the selected bounded
list setter. That setter writes one element and increments the compiled version
slot without changing the count slot. The Unity wrappers' indirect internal
calls, coordinate meaning and floating-point environment remain separate from
this buffer proof. The separate population proof below establishes conditional
source transfer; complete initial population still depends on growth and
list/reference lifetime. ApplyPoints/renderer value submission, parent
configuration identity and observed execution remain open. This independent
consumer proof changes no serialized route, positive-list admission or
complete-root count.

The independent [`population consumer validator`](../../scripts/game_data/buff_effect_line_center_population_native.py)
checks the complete ordinary `_GetPoints`, trail constructor, physical Add
wrapper/append, AddWithResize, EnsureCapacity, set_Capacity and selected list
constructor programs. `_GetPoints` starts at index zero, reloads `this.points`
and its current count each iteration, obtains one bounded Vector3 value, and
passes all twelve bytes unchanged through the actual append chain. It does not
clear the destination. The parent offset program clears the temporary count
before this call; equating source and destination can therefore erase the source
count, while a standalone same-header copy can grow its own loop bound.

Whole-source copying without resize is proved only for ordinary successful
paths with stable nonnegative source count/reference/values, an initially empty
destination, distinct list headers, valid nonoverlapping or same-index array
storage, and sufficient destination capacity for every append. These are
explicit selections, not proved runtime preconditions. The constructor stores
the results of two separate allocation and List<Vector3> constructor calls into
the source and temporary fields, initializes useWorldSpace and zero centerOffset,
and retains an anonymous ancestor-byte assignment without naming its meaning.
Neither two allocation calls nor the selected list constructor proves fresh or
zeroed objects, an empty static array, or nonaliasing throughout the lifetime.

The append fast path increments the compiled version and writes one twelve-byte
element at the incoming count. The slow path snapshots that count, requests its
signed-int32 successor, calls EnsureCapacity, reloads the items reference, writes
the successor count and appends at the saved index. EnsureCapacity uses the
reviewed contract's default/maximum constants, a full-width zero-length test,
wrapping dword doubling, an unsigned ceiling comparison and a signed request
comparison in their original order. set_Capacity rejects capacity below count,
returns for equal capacity, forwards the old positive count to Array.Copy, then
replaces items; it does not itself alter count or version.

The actual named Array.Copy declaration has five managed parameters:
source array/index, destination array/index and length. The extra zero qword
stack argument is a trailing IL2CPP context under the static-method ABI, not a
sixth managed copy-policy parameter; its consumer read is not proved. Argument
forwarding does not establish Array.Copy's implementation or preservation of
old elements during resize. Static typed contexts and their complete matching
registration rows also do not equate the registered Add pointer with the actual
optimized append body or establish live RGCTX selection. The next joins are
the array-copy/helper implementation, compatible array class/stride, allocation
and reference lifetime, renderer submission and parent configuration identity.
These consumer facts add no stored route or list/root admission.

The separate [`copy-argument validator`](../../scripts/game_data/buff_effect_line_center_copy_arguments_native.py)
now joins the actual five managed Array.Copy arguments to its selected
same-element-class helper branch and actual bulk-callee entry. Correct REX.X
decoding establishes the extended length/index registers in the dword bounds
expressions. The helper sign-extends the runtime destination-class scalar,
multiplies it by the old count for the byte length, and uses that same scalar
with the source/destination indices to form the two payload addresses. The
multiply and address-add instructions are qword operations. The scalar's live
value and its equality to the separately proved Vector3 element stride remain
an explicit runtime join; this does not name an anonymous class field.

After normal bulk return with the required nonvolatile values preserved, the
selected helper checks an optional static-bitset update, including its qword
bit set and locked compare/exchange retry, then returns AL true through the
complete matching frame. Bitset disjointness from the array payloads and
successful retry termination are separate conditions. The managed caller's
true-result return is checked; its error and false-result fallback paths remain
outside this selection. The bulk body is authenticated in full; the REP subset
below now has conditional copy semantics. Independent proofs below also cover
the selected small, snapshot, bounded-vector and aligned temporal-loop paths;
non-temporal visibility/consumption and backward-overlap paths remain open. Consequently
the old-count-to-byte-length join is direct evidence, while general preservation
of old points across resize stays unresolved.

The independent [`REP copy validator`](../../scripts/game_data/buff_effect_line_center_copy_rep_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_rep_native.json)
revalidate that argument chain against the same opened native image. Complete
selected entry, size, overlap, mode and option blocks join both conditional
branches to the actual leaf entry through RET. The entry preserves the original
destination in the return register; the leaf saves RSI/RDI, copies the incoming
source/destination/byte-count operands into RSI/RDI/RCX, executes the exact
default-address REP MOVSB instruction, restores the saved registers and returns.
Mode and option remain anonymous dword/byte runtime cells. Their current values
and provider names are not supplied by a static branch proof.

Forward copying is established under DF=0, normal complete execution over
valid stable non-wrapping memory, a caller frame disjoint from the payloads,
and destination at/below source or at/above the source endpoint. The overlap
comparison excludes a destination strictly inside the source range from these
REP branches. The byte-prefix invariant then preserves each initial source
byte in the corresponding destination byte without overwriting future unread
source bytes. The [Intel MOVS/REP instruction reference](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf)
supplies the count/direction semantics. The [Windows x64 ABI convention](https://learn.microsoft.com/en-us/cpp/build/x64-software-conventions?view=msvc-170)
is not a measurement of the actual direction flag; DF=0 stays a condition.

Combining this subset with the existing helper and append proofs establishes
conditional old-point preservation only when the same-element selections,
runtime class stride equal to the independently checked Vector3 width,
REP size/mode/option branch, memory/frame conditions, optional static-bitset
disjointness and successful retry all hold. This REP subset does not cover small
growth copying; the independent bounded proof below covers those selected
paths, with the aligned temporal-loop proof below covering selected larger
forward transfers. Non-temporal/backward paths, array providers and
allocation/alias lifetime still need their own proofs. Neither the conditional
copy nor the ABI reference establishes observed
execution, renderer submission or the parent configuration lifetime join.

The shared [`memory-move decoder`](../../scripts/game_data/il2cpp/memory_moves.py)
retains exact GP byte/word/dword/qword and legacy SSE/VEX transfer widths,
independent register/base/index extension bits, signed displacements,
instruction-specific alignment and partial/upper-register effects. It covers
the indexed vector tail forms and original dispatch-table dword loads without
changing the older shared mapper. Unsupported prefixes/maps/register forms and
invalid reserved VEX fields supply no move claim; recognized truncation has a
bounded diagnostic. Its selected padding decoder also keeps an entire legal
multi-prefix NOP in one original byte span without treating the operand as a
memory read. These operand facts are proof tooling, not whole-copy semantics.
The independent bounded consumer below now proves selected small-target,
snapshot and vector joins, table-index bounds, payload coverage and overlap
safety. Decoding other blocks alone still supplies no complete copy effect.

The [`bounded copy validator`](../../scripts/game_data/buff_effect_line_center_copy_small_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_small_native.json)
revalidate the parent argument/REP-selection proof on the same opened image and
authenticate the original dword RVA tables. The small dispatcher uses the
incoming full-width unsigned byte count, a zero-extended table entry and the
checked image base. Every reachable small-table target is checked through its
plain RET. Small and snapshot programs read all required source bytes before
writing, keep every access within the selected payload length, and therefore
retain conditional copy correctness under arbitrary source/destination overlap.

The two bounded vector branches save the head and final vector, round the
length using checked qword arithmetic, and join the resulting bounded index to
an actual instruction boundary in the original tail program. For every integer
length under each native bound, the shared
[`symbolic byte-copy proof`](../../scripts/game_data/il2cpp/byte_copy_programs.py)
tracks each distinct initial-source byte through register loads and stores,
checks every read/write range and proves complete destination coverage. Its
interleaved-load invariant places all earlier relative destination endpoints
at/below the next source start. Consequently a destination at/below source cannot
overwrite an unread source byte, while a destination at/above the source endpoint
is disjoint. The remaining destructive-overlap branch is outside this selection.

The complete selected programs preserve the original destination return value,
stack pointer, required nonvolatile GP registers and low nonvolatile vector
lanes; any vector cleanup follows all payload writes. These fixed memory moves
do not consult DF. The ordinary growth transfer now fits both checked mode
branches, but joining old points to preserved new-array elements still requires
the runtime class stride to equal the independently checked Vector3 width,
compatible current arrays/code/tables, supported instruction state, stable
memory and the parent frame/bitset/normal-return conditions. The separate proof
below closes larger aligned temporal loops. Non-temporal ordering, backward
copies, fresh allocation and reference lifetime remain separate. The bounded proof adds no stored route,
positive-list/root admission, observed execution or renderer/parent lifetime fact.

The [`aligned temporal-loop validator`](../../scripts/game_data/buff_effect_line_center_copy_loops_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_loops_native.json)
revalidate the small/REP/argument chain on the same opened native image. Complete
original alignment, padding, loop and unsigned guards join the bounded vector
prefixes to their actual shared tails. The destination advances to the next
vector boundary, including a full vector advance when already aligned. Source
advances by exactly the same amount and remaining length decreases equally;
the original destination and saved head/final vectors remain available.

The shared [`aligned-loop byte proof`](../../scripts/game_data/il2cpp/aligned_copy_loops.py)
first proves every chunk byte from distinct initial-source identities, checking
the alignment required by each temporal store. The original equal pointer
advances and strictly decreasing unsigned count then establish a natural-number
induction for arbitrary iteration counts under valid stable non-wrapping memory
and the parent forward-safe-overlap selection. This is an induction over the
checked program, not a sample of large copies. Every reachable remainder is
checked against the actual raw table and an original instruction boundary.
Affine byte identities retain the arbitrary copied-prefix displacement and
original endpoint, including saved-last stores that extend before the current
pointer when less than one vector remains. A zero remainder still reaches the
original-head write, closing the skipped alignment prefix.

Combining these programs establishes conditional larger temporal copying and
conditional old-point preservation through the selected helper/append chain.
The wider-vector non-temporal threshold edge is checked but its alternative
body and ordering are not proved here. Runtime class stride and mode/CPU
selection, non-temporal and backward copying, allocation/alias lifetime,
general resize preservation, renderer submission and the parent configuration
join remain open. No stored route or list/root admission changes, and no actual
execution is observed.

The independent [`non-temporal store validator`](../../scripts/game_data/buff_effect_line_center_copy_non_temporal_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_non_temporal_native.json)
now revalidate that parent chain and join the actual wider-vector threshold
edge to the complete non-temporal loop, its distinct raw tail table and every
reachable tail through fence, cleanup and plain return. The counter proof
requires at least one full initial chunk and exits below a chunk; affine tail
proofs retain the original head and endpoint even for a zero remainder.

The shared [`non-temporal value proof`](../../scripts/game_data/il2cpp/non_temporal_copy.py)
checks each streaming-store alignment before projecting only its transferred
byte values onto the existing loop/tail invariants. All writes, including
overlapping cached ordinary stores, carry the corresponding initial-source
bytes. This proves complete store-value coverage after the checked stores
become visible; it does not turn weak non-temporal ordering into ordinary
temporal ordering. The original instruction inventory remains contiguous,
and every reachable payload contains the exact fence after its final write.

The [Intel MOVNTDQ/SFENCE reference](https://www.intel.com/content/dam/www/public/us/en/documents/manuals/64-ia-32-architectures-software-developer-vol-2b-manual.pdf)
establishes the aligned register-to-memory transfer and store-fence boundary:
stores before SFENCE become globally visible before following stores. SFENCE
does not order loads. That standalone proof leaves global visibility at RET,
subsequent read consumption and the actual parent publication-store join open;
the separate proof below now joins the actual following publication store.
It does not admit complete non-temporal copying or general resize old-value
preservation. Backward copying, live providers/stride/CPU choices, allocation
and alias lifetime, renderer and parent configuration joins remain separate;
stored/list/root admission and observed execution do not change.

The [`copy-publication validator`](../../scripts/game_data/buff_effect_line_center_copy_publication_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_publication_native.json)
revalidate the non-temporal and complete population proofs on the same selected
native image. The actual positive-count capacity path saves the allocation
result as a full reference, passes it to the checked Array.Copy entry, and
publishes it into the list's items slot in the instruction immediately after
that call returns. Complete original return-frame checks establish preservation
of the saved allocation and list references, under the existing selected
helper/normal-return and valid disjoint frame conditions. The earlier checked
SFENCE therefore orders its payload stores before this actual following store.

The complete bounds-checked getter reads the same compiled reference slot.
The [`scalar memory-fragment proof`](../../scripts/game_data/il2cpp/scalar_memory_moves.py)
checks the original eight-byte MOVSD and four-byte GP transfers and proves all
output bytes equal the selected indexed element's bytes. MOVSD performs no
floating-point conversion; its load clears the next vector qword, whose state
is explicitly outside this low-byte projection. The common symbolic index must
remain unchanged across source reads. This joins complete value consumption
to the published representation without equating separate runtime references.

Conditional old-point preservation now requires the actual publication to be
globally visible and the selected getter to observe that reference before its
payload reads, with stable coherent compatible memory, no intervening overwrite
or interfering alias, valid old-index bounds and disjoint output. All parent
branch/CPU/memory/frame/bitset conditions remain; the live class stride must
equal the independently checked getter width. Neither SFENCE nor the static
store/read join proves those visibility, selection or lifetime conditions.
Allocation freshness, general resize preservation, renderer
and parent configuration joins, stored/list/root admission and observed
execution remain unchanged.

The independent [`backward-copy validator`](../../scripts/game_data/buff_effect_line_center_copy_backward_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_backward_native.json)
now revalidate the argument/common-dispatch proof and authenticate the complete
called bulk body on one selected native image. The actual unsigned overlap edge
enters the complete original backward program before runtime mode selection.
The [`legacy vector decoder`](../../scripts/game_data/il2cpp/backward_copy_instructions.py)
checks full MOVUPS/MOVAPS bit transfers, alignment and preserved upper vector
state, the unchanged low-byte alignment test and complete padding spans;
these moves do not perform floating-point conversion. Original local edges and
qword arithmetic/counters are checked throughout, including the already-aligned
path that skips the unaligned path's remaining-length recomputation.

The [`descending byte proof`](../../scripts/game_data/il2cpp/backward_copy_programs.py)
retains symbolic source positions. Original head/last caches and alignment
establish a copied upper suffix or a cached current vector. A chunk body reads
every byte while writing its upper vectors; its two lowest vectors remain
pending in registers. The repeat header stores both before entering the next
body; the exit stores the upper pending vector and forwards the lowest into the
tail cache. Distinct byte identities establish both completions, and the actual
positive divided counter, single decrement and checked back edge establish
natural-number induction for arbitrary selected chunk counts. A store begins
at or above every later unread source endpoint in relative coordinates; with
destination greater than source, those stores cannot overwrite future reads.

Every bounded post-chunk remainder is checked through the descending vector
tail and final writes. A zero low remainder needs only its cached current
vector; a nonzero low remainder also writes the original cached head. Their
overlapping stores carry agreeing initial-source byte identities. The complete
selected backward program therefore has conditional byte-preservation,
destination-return and nonvolatile-preservation proofs under valid stable
non-wrapping memory and the parent return/frame/bitset conditions. Actual
overlap/stride/CPU choices remain unobserved. Its standalone proof does not
combine the other programs; the combined dispatch proof below now closes that
selection-coverage join. Publication/consumption across all selected paths,
compatible allocation and reference lifetime, general resize preservation and
renderer/parent joins remain separate; stored/list/root admissions do not change.

The [`combined copy-dispatch validator`](../../scripts/game_data/buff_effect_line_center_copy_dispatch_native.py)
and its [reviewed contract](../../scripts/game_data/contracts/buff_effect_line_center_copy_dispatch_native.json)
revalidate the complete forward proof chain and backward program on the same
selected native image. Original unsigned size/overlap/mode/option blocks and
both vector prefixes/alignment blocks are decoded again for their actual joins.
Both false option tests fall through exactly into their checked vector prefixes;
bounded and rebased tails, temporal loops, the non-temporal entry and the backward
overlap entry all connect to the complete programs owned by the earlier proofs.
No branch is admitted through a name match or by conjoining report flags alone.

The [`integer-domain partition proof`](../../scripts/game_data/il2cpp/copy_dispatch_domains.py)
uses disjoint closed integer intervals and checked adjacency to cover every
unsigned count and mode, rather than sampling representative lengths. The
option-bit conditions are complementary. With a positive count and non-wrapping
source endpoint, ordered trichotomy partitions destination-before-source,
interior backward overlap and destination-at-or-after-source-end; the actual
CMOVBE and unsigned comparison select exactly the middle case for backward copy.
Every possible masked destination residue has a separate complete count
partition. Alignment advances a full vector width when already aligned, and
the high non-temporal threshold applies to remaining after that advance, not
original length. An originally large count can therefore reach the shared tail
or temporal loop. Integer clipping preserves extreme count endpoints without
inventing wrapped comparisons; only bounded post-loop remainders are rounded.

Together these joins and complete payload proofs establish conditional store
values for every selected program: small and snapshot paths allow arbitrary
overlap, common forward paths use their checked forward-safe overlap, and the
backward path uses the actual interior-overlap selection. Every checked store
carries the corresponding initial-source bytes, including agreeing cached
overlap writes. Valid stable supported compatible ordinary memory, non-wrapping
endpoints, no interfering writes and all same-element/normal-return/frame/bitset
conditions remain required; only selected REP additionally requires clear DF.
Non-temporal visibility retains its fence/publication/observation boundary.
Complete static coverage does not prove global visibility at RET, actual getter
observation, live stride or CPU/option selection, compatible fresh allocation
and reference lifetime, general resize preservation or observed effects. It
does not admit new stored elements, enclosing lists or complete roots.

After the derived action is admitted, reached original-element refusals move
to other actions such as TickInterval, ConvertToTargetContext, SelfRotate and
RayCastEffect, alongside populated nested geometry/validator and damage lists.
Current dispatcher identity names those reached action wrappers; it supplies
no source program, stored child grammar or runtime behavior for the still
refusing action. First-refusal groups and overlapping source reach must remain
distinct from predicted full-root gains.

TickInterval has an independently reviewed current
[`Skill normal-source contract`](../../scripts/game_data/contracts/skill_timeline_tick_interval_native.json)
whose ordered reads name a `SequenceActionData` child. The shared
[`Buff sequence declaration`](../../scripts/game_data/contracts/buff_event_maps_native.json)
and reader remain reusable child evidence. The
[`complete source-flow owner`](../../scripts/game_data/memorypack/buff_tick_interval_sources.py)
now checks the complete unwind-owned caller, generated/inherited setters,
concrete cached-instance getter, FF output clear, normal return and formatter
forwarding against its
[`reviewed contract`](../../scripts/game_data/contracts/buff_tick_interval_sources_native.json).
Each of the nine source returns reaches its metadata-owned Data field under
the explicit normal-call, ABI, compatible-cache and noninterference conditions.
The selected Sequence context is joined to current metadata. The separate
[`source/helper composition owner`](../../scripts/game_data/memorypack/buff_tick_interval_composition.py)
checks the actual physical ReadValue body, same Reader and full reference
output, concrete Sequence adapter/getter and selected complete array-source
programs. That output conditionally reaches the owned `actionOnTick` field.
The actual primitive callees also join independently proved buffered
object-header, normalized byte, Int32 and Single source programs; the Single
low bits reach the owned setter, and the string field uses the proved nullable
valid-UTF8 helper. The Single source window belongs to the per-record source
contract, rather than the containing postprocessor catalog.
These joins require the stated compatible context, provider, cache, ABI,
buffer and normal-return conditions. The closed Sequence usage is metadata
joined, but no compiled row for that particular closed usage or actual runtime
inflation/invocation has been observed. Physical helper naming remains
unresolved. Historical candidate field names cannot replace the current
indexed dispatcher identity.

The [`isolated stored-parent reader`](../../scripts/game_data/memorypack/buff_tick_interval_action.py)
takes the fresh complete recursive native context and the separate Tick
composition proof as distinct inputs. It consumes canonical extended-tag
original parents with all named fields and exact recursive Sequence children;
null wrapper, null/empty arrays, raw terminal flags and valid stored strings
retain their separate representations. Original reached parents now replay
completely with matching independent current-metadata parent boundaries and
unchanged original child receipts. Metadata framing of the following enclosing
bytes supplies only a structural boundary check.

The separate [`Tick union-route owner`](../../scripts/game_data/memorypack/buff_tick_interval_union_route.py)
and [`reviewed route contract`](../../scripts/game_data/contracts/buff_tick_interval_union_route_native.json)
now prove the complete current indexed new-child case and restored return.
The null-prior-wrapper path sends the same Reader through the actual closed
wrapper ReadPackable thunk and shared packable body, stores the full reference
result and passes it through the actual shared barrier. Indexed prefix,
null-cast, restored return, shared contexts and barrier declarations remain in
their existing owning contracts rather than being copied into the Tick
contract. The selected path retains compatible initialized contexts/provider,
null prior output, normal ABI, stable disjoint storage and disabled-barrier
conditions; the reuse path and runtime selection remain separate.
The recursive action owner now registers Tick stored decoding and independently
validates the helper/source and union-route packets. Its adapter requires both
owned proofs and matching current concrete wrapper/original identities, with
no incomplete-proof fallback. The anonymous reader frames the same named
current layout. A fresh complete native context has now been generated by the
full-family gate, preserving its original return and the complete original
source keyset/hashes. Reached original parents pass the global recursive entry
with current metadata boundary agreement, and their enclosing positive
Timeline source elements independently close every field and typed Sequence
child. These element receipts grant no positive-list or whole-root admission;
the independently completed full corpus records no Tick-integration root gains
or regressions. The previous cached validator return is not extended,
relabeled or reused as current. Native action callback cursor equality and
positive-list adapter/root admission remain separate obligations; live
scheduling and effects remain unobserved.

Current named runtime bodies provide a further consumer lane through OnCreate,
ReAssign, ExecuteInternal, OnTick, End and Reset, with V2 kept distinct. The
stored Data reference, runtime counter/timer and frame guards still require
complete receiver/layout and control-flow proofs. The current OnTick primary
and owned chained fragments now decode completely through the existing
[`SSE lane decoder`](../../scripts/game_data/il2cpp/sse_lanes.py). Its complete
register CVTDQ2PS converts signed Int32 lanes to Single; the spurious POP from
the shared mapper's earlier split bytes is not frame restoration. Inexact
conversion follows MXCSR rounding, so no implicit exact-real or default
rounding assumption belongs in a tick formula. See the
[Intel instruction reference](https://cdrdv2-public.intel.com/774492/325383-sdm-vol-2abcd.pdf).
Complete instruction decoding still does not prove operand ownership or
branch selection, and call presence does not prove that the created Sequence
or retained target reaches a later execution call.

The independent named
[`consumer claims`](../../scripts/game_data/contracts/buff_tick_interval_consumers_native.json)
and [`validator`](../../scripts/game_data/buff_tick_interval_consumer_native.py)
now prove the getter's `AlwaysReturnTrue` policy through a complete Int32-backed
enum return and plain epilogue when `IFix.IsPatched` returns false. This policy
does not prove an actual ExecuteInternal/OnTick result. Selected metadata also
identifies OnReset's argument as `AbilityAction.ResetReason`, an Int32-backed
enum, rather than a byte Boolean. Forwarding that argument to the cached
Sequence receiver remains a separate ownership and call-ABI obligation.
The existing strict generic-reference layout checker refuses the concrete
Tick witness because its instance suffix has a gap; the selected closed parent
has no alternative immediate concrete witness. Preserve this refusal until a
separate layout or accessor proof authenticates the closed Data slot. Do not
reuse an open generic offset or silently admit suffix padding.
The selected compiled generic-method registration search provides no usable
closed Tick accessor entry; this says nothing about runtime inflation and
does not establish the slot by absence.

Reached original tick-sequence prefixes contain damage actions. Canonical
zero/FF Finder children now have an independent
[`source/type owner`](../../scripts/game_data/memorypack/buff_selector_zero_finders.py).
The [`recursive selector`](../../scripts/game_data/memorypack/buff_find_target_action.py)
now routes these tags to their source/type owner and refuses missing, mismatched
or incomplete native proof. The anonymous boundary reader also frames the
proved GuardAI and Typhoea zero-field tags. Fresh complete recursive native
validation and original Damage child replay now establish their current stored
composition. The complete family gate preserves the original source keyset and
hashes, records full-root gains, and reports no regressions. Generated counts,
source catalogs and replay receipts stay in reports; TickInterval's positive
list and enclosing runtime consumption remain open.
Isolated child replay grants no enclosing action, element, list or root receipt;
live context/formatter selection, ticking and damage effects remain separate.

CircularOrderSort and NavMesh lists can be embedded inside these positive
timeline records. Closing their local lists does not close the enclosing
TimelineActionData list: the root's conservative suffix frontier remains,
and selected related roots independently replay from byte zero until the
positive timeline count refuses. Earlier structural action receipts can still
retain anonymous naming obligations; structural eligibility and the native
forward replay's first refusal are separate evidence.
The maintained
[`buff_timeline_empty_native`](../../scripts/game_data/memorypack/buff_timeline_empty_native.py)
gate deliberately admits only null or empty lists; positive-list composition
must reuse the proved element identity without bypassing that boundary.

Find the first incorrect field before interpreting a late parse failure. In the
complete candidate, CheckSkillInterruptReason's `reasonList` required the
selected metadata's Int32 enum-element grammar; treating its elements as object
headers caused a later false PoiseModifier anomaly. The remaining missing
declarations were AttributeOverrideEntry (`attributeType`, `overrideValue`) and
BuffValidator (`buffFindSettings`, `validateMode`). Their historical or generated
names alone do not prove current source reads or nested union selection.

Static lifetime analysis also exposed an argument-location tooling gap:
`BodyIndex.parameter_location` describes general-purpose registers and cannot
prove a floating-point argument's carrier. The observed RawSetLifeTime caller
and callee use a SIMD register for `time`. A typed ABI resolver and direct value
flow proof are required before admitting lifetime arithmetic into that parameter;
existing call presence is insufficient.

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
  complete-root admission. CheckEntityNum and AddGlobalCDTimer now have
  independent general parent gates in the shared Buff event-map reader;
  their older source-bound or SkillData proofs are insufficient on their own.
  AddGlobalCDTimer's stored fields remain separate from CheckGlobalCDTimerAction's
  timer check and from live timer application. Every
  composition still needs all root fields,
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

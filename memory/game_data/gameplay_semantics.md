# Gameplay: Tables, MemoryPack, and the native action contracts

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, gameplay lane.** Where authored `Table` config joins exact MemoryPack
framing and selected native enum contracts to become gameplay meaning.

Per-action layouts are **not** here: each union tag has a tracked
`scripts/game_data/contracts/buff_*_native.json` or `skill_*_native.json`
contract (plus the `finder_*`, `validator_*` and `postprocessor_*` ones) with
its member order, nested profiles, null paths and pinned native inputs, and a
`memorypack/` validator that states what it proves. Gameplay joins selected
action tags to these native reader contracts; provider selection and action
semantics stay unresolved (below).

## Combat simulator objective and recovery priorities

The intended outcome is a lightweight combat simulator grounded in the game's
binary implementation, to help compare teams, loadouts, skill sequences and
combat decisions. The current stage advances understanding of game data and
native execution rules. An architectural description is useful, but is not
sufficient: supported scenarios need reproducible state transitions, numerical
evaluation, timing and event effects. Do not start implementing speculative
simulation rules merely because a field or method has a plausible name.

| Priority | Rules to recover | Why simulation needs them |
| --- | --- | --- |
| Inputs and construction | Character/weapon/equipment/enemy definitions; growth, talent and potential processing; Blackboard resolution and attribute stages. | Instantiate the selected build rather than substitute values from one captured combat. |
| Damage and Poise settlement | Snapshot producer/consumer, dynamic inputs, processors, damage modifiers, mitigation/immunity, rounding, final resource writes and event generation. | Existing attack intermediates cannot yet predict final damage or breaks. |
| Buff state and feedback | Creation, stacking/refresh/replacement, expiry/tick, conditions, event order and the relevant talent/gear/skill listeners. | Predict which effects exist at each calculation and how one action changes subsequent actions. |
| Combat time and resources | Skill phases and hit times, continuation/cancellation, cooldown, shared skill resource, ultimate energy and combo gates. | Predict a rotation over time instead of summing independent skill multipliers. |
| Scenario and validation | Target/element/status inputs, target count and hit selection, relevant enemy behaviour, and bounded comparisons against existing observations. | State the supported combat scenario and expose unknown rules instead of silently inventing precision. |

A later simulator can abstract rendering, audio, world traversal and unrelated
account/production systems. Geometry and server corrections can be abstracted
only where the selected combat scenario makes their effects explicit. A
discrete-event approach is a candidate, not a recovered engine fact; update
cadence, same-time ordering and cancellation still need binary evidence.

Progress is a recovered reusable rule or a joined state transition that makes
more combat predictions possible. Keep stored schema, native rule and bounded
runtime validation separate. A supported scenario is ready only when missing
rules affecting its outputs are resolved or exposed as explicit assumptions;
no claim of whole-game or whole-character parity follows from a partial model.

## Shared combat model and completion boundary

The existing configuration, native-consumer and retained-runtime evidence is
sufficient to explain the default Skill/Buff/healing design. This is a
conditional system model, not complete semantics for every action subtype or
an exact replay of a player's combat. Detailed evidence follows in the owning
sections; [the game-data entry point](../game_data_recovery.md#understanding-the-running-game)
sets the cross-system priorities and capture stopping rule.

| Stage | Owner and operation | Interface to the next stage |
| --- | --- | --- |
| Assemble skill | Character configuration selects the base SkillData; selected ordinary construction applies level, talent and potential processing. | The constructed data supplies Skill initialization, with optional construction inputs. |
| Initialize parameters | Skill owns running Blackboard storage and a creation snapshot; Ability has a dynamic baseline. Selected initialization applies base, patch and extra, snapshots, then owner source. | Actions query direct storage first and entity storage on a failed Float lookup; literal and keyed expressions are distinct. Duplicate keys prevent universal dictionary assumptions. |
| Execute behaviour | Skill/Buff lifecycle and event action containers invoke action sequences, which can synchronously create other Buffs and reenter execution. | Action result, outer execution result, sequence continuation and side effect are separate. Cross-frame scheduling is not yet a unified model. |
| Evaluate state | Attributes owns staged values, modifier inputs, caches and dirty recomputation; HealPack carries actor attribute snapshots. | Healing construction samples actors, processors can refresh snapshots, and formulas consume the refreshed values. |
| Settle healing | The default path scales the pack by `1 + HealOutputIncrease + HealTakenIncrease`, submits an HP modifier, clamps HP and records readback difference. | Requested delta, actual delta and ApplyResult are separate; a positive successful request can have zero actual gain. |
| Publish feedback | AbilitySystem checks separate output/received-healing interest and routes contexts through dispatcher, action container, skills and combo handling. | Event sequences can create Buffs and feed back into behaviour/state. Local notification and serialized reporting do not establish server acceptance. |

Remaining combat-model work concerns scheduling/cancellation, complete damage
settlement, materially different action behaviours, relevant listeners and
state authority where it changes combat results. Missing historical snapshot
values or patch choices do not block explaining the shared design above.
However, the rules generating those values and selecting relevant effects must
be understood for simulation. Treatment of failed journals and native gates
is unchanged.

The prepared healing observer remains available for a future discriminating
experiment or necessary numerical/timing validation. Further healing capture
and observer expansion are deferred while higher-value combat rules can be
recovered from existing data and code.

## Tables and authored joins

- Decoded Table JSON gives each authored field's name and stored value. Units,
  enum meanings and cross-table keys are proven only where a consumer has been
  checked; most tables have no consumer-proven meaning. Gameplay joins selected
  Buff/Skill tables to native contracts; Story publishes the text tables.
- Enemy variants resolve their exact attribute template before stats show.
  Authored points, cooldowns, modifiers, formulas and Buff actions stay source
  values; final values across Buffs, IFix, equipment and server state are not
  computed.
- The Table overlay is checked at the logical and decoded layers: the SparkBuffer
  dump verifies every payload and equals the export, and the previous export's
  changed set equals the changed Table identities in both VFS ledgers. With
  dictionary keys treated as IDs, tables populated in both exports gain no new
  value field paths; tables gaining or losing all rows are data-population
  changes, not a reader change.
- Character and weapon rows form a direct authored ID chain: `CharacterTable`
  and `CharGrowthTable.skillGroupMap` name skill IDs, `SkillPatchTable`
  repeats them, `WeaponBasicTable` names its potential skill, and potential and
  talent effects carry more. Exact stored strings in decoded `SkillData`/
  `BuffData` join skills to Buffs and Buffs to Buffs: authored references, not
  execution, skill ownership of every referenced Buff, or activation.

Energy Alluvium's authored group rows store separate primary-attribute,
secondary-attribute and skill term pools in WorldEnergyPointGroupTable.
Its world-level map names WorldEnergyPointTable rows directly; their level IDs
resolve through LevelDescTable, and GameMechanicTable supplies corresponding
costs when the group owner agrees. Weapon SkillPatch tags resolve through
GemTagIdTable to GemTable; unique tags at every published skill level and the
expected term type establish an exact stored-reference join. Membership of all
three terms in their respective pools is an authored compatibility candidate,
not a consumer-proven probability or a guarantee that the combination drops.
Missing or ambiguous mappings do not establish compatibility. Group identity
is checked on both point and mechanic rows. Region comes from
DomainDataTable.levelGroup only when ownership is unique across the group's
level variants (label and sortId); otherwise it stays unresolved, and no map
coordinates are inferred. The WebUI projection is owned by
`scripts/webui/gameplay/gems.py`.

## Factory blueprints: installed layouts and remote account data

- The client `BuiltinBlueprintTable` TextAsset contains decoded JSON under
  `factorySysBluePrint`, keyed by `bpKey`. Each layout stores its icon, tags,
  size and nodes. Building transforms store position/direction; conveyor
  transforms additionally store input/output ports and path points. Component
  payloads retain selected items, formula modes and valve settings.
  Item-control-port item labels join `boxValve.selectedItemId` to the exact
  `ItemTable` key; retain that selection identity separately from `productIcon`.
  Valve outlet graphics compose the authored local output-port rotation with
  the stored node rotation. Device facing alone is not the outlet direction;
  adjacent conveyor endpoints corroborate the composition where available.
  `FactorySystemBlueprintMetaTable` supplies localized name/description/creator
  references by exact key. An unmatched payload keeps an unresolved label;
  embedded presence does not establish that a player's account unlocks it.
- Current selected metadata names a distinct runtime layout
  (`RemoteFactoryBlueprint`: building/conveyor lists and source rectangle) and
  its Protocol Buffers representation (`Proto.CSD_FACTORY_BLUE_PRINT_DATA`,
  `CSD_BLUE_PRINT_NODE`, `CSD_BLUE_PRINT_TRANSFORM`). The generated protobuf
  member surface gives field numbers and managed types. It does not alone
  prove scalar wire encodings, a complete nested codec or actual server bytes.
  Resolve this surface from the selected native pair through `NativeImage` and
  `il2cpp.protocol`; reject a cached catalog with different source hashes.
- `BlueprintPreview` centers footprints on `worldSpatial.worldPosition`,
  swaps authored width/depth for quarter-turn faces, and centers conveyor
  grid cells with a half-cell offset. Selected native `FromBuiltinData` bodies
  copy the building world transform and convert stored direction into a
  quarter-turn face. The conveyor branch projects stored points to X/Z and
  passes the inlet/outlet facing separately to
  `GridUtil.InOutDirAndPointsToStartFaceAndGridPath`; `PointJustDir` agrees with
  the Lua face vectors. These are inspected unpatched branches; loaded IFix
  selection remains unobserved. An outlet facing is independent of the last
  point-to-point segment direction, including a corner on the terminal cell.
  Do not replace it with that segment's tangent. Stored port positions can
  differ from point endpoints; preserve both, while the preview's path follows
  the points. A top-down view flattens height, and declared machine ports do
  not establish which recipe-mode ports are open or that placement succeeds.
- The exported Lua owners directly expose the client flow:
  `FacLuaSystem.GetBlueprintFromBatchSelectTargets` builds the selected layout;
  `FacSaveBlueprintCtrl._OnClickSave` passes it and its metadata to
  `SendSaveBlueprint`; `BlueprintContent._PendingShare` requests review.
  `BlueprintShareBlackScreenCtrl` requests a share code, then passes that code
  to the external screenshot/copy panel or friend chat. `FacBlueprintCtrl`
  queries a code to preview its returned layout, and `FacSaveBlueprintCtrl`
  fetches it into the gift collection. These are source-visible call paths,
  not a recorded live session or native method-body proof.
- The protobuf surface separates the share request's blueprint identity, the
  share reply's code, and the query reply's full blueprint data. Friend chat
  carries the code. This supports a remote lookup workflow; it does not expose
  the server database, code-generation algorithm, cross-region rules or an
  offline code-to-layout decoder. Player-created and received layouts require
  their response/cache data; the installed builtin catalog is not that save.
- Local persistence is distinct from the runtime collections. The inspected
  `%USERPROFILE%/AppData/LocalLow/Hypergryph/Endfield/ClientData` JSON stores
  blueprint UI/consent state but contains no recovered player layout or share
  code. `FacBlueprintCtrl` explicitly persists `FAC_BP_LAST_TAB_INDEX` through
  `ClientDataManager`, while layout save/query/fetch use the remote blueprint
  system. This is a scoped disk observation, not proof that every possible
  binary cache is absent. The runtime own/gift collections remain possible
  recovery sources after the server supplies their data.

Generated inventories and current native-input receipts belong under
`reports/game_data/blueprint/`. The installed TextAsset, exact authored table
keys, generated protobuf declarations and the named Lua owners above are the
source evidence; the reports only inventory it. A targeted response/cache
capture is specified in
[`../runtime_capture_requirements.md`](../runtime_capture_requirements.md#factory-blueprint-response-and-cache-data).

## BuffData root and union encoding

- [`memorypack/buff_actions.py`](../../scripts/game_data/memorypack/buff_actions.py)
  documents the root reader, its six cursor ranges (`abilityEventAction`
  through `buffEventAction`, pinned by the `buff_root_prefix`/`fifth`/`sixth`
  native contracts), the closed damage-processor routes, the `FA` extended-tag
  escape and the non-identifying action prefix. Generated wrapper order names
  the outer fields and storage order, not action behavior; the opaque physical
  remainder after a stop is not a decoded record.
- `buff.frame_buff_named_middle` continues through the modifier lists,
  `dispelConfig` and native-gated exact `iconConfig` to the accepted `id`
  marker; without that gate, `iconConfig` stays opaque. The suffix reader
  closes `id` through `waitFirstTriggerInterval` at EOF. Any unsupported
  processor route or condition action stops at its tag.
- The selected-build `memorypack.derived_plans`/`derived_values` route decodes
  whole `BuffData`/`SkillData` records to EOF with id/filename agreement. It
  does not upgrade the bounded legacy readers, and the JsonData gate's BuffData
  `schema_decoded` state also needs a recorded root receipt (`jsondata_corpus`).
  Its PlaySound actions: [`audio_naming_coverage.md`](audio_naming_coverage.md).
- Gameplay's compact Buff publication uses `memorypack.buff_values` with the
  selected export's explicit indexed string pool. It requires complete EOF and
  filename/id agreement, then joins lifecycle and stacking enum fields to their
  selected native backing widths. Byte and signed Int16 defaults are raw bytes;
  Int32 defaults retain their compressed encoding. This is derived-plan stored
  evidence, not an independent whole-schema receipt or action execution proof.
  A legacy missing-id-marker result is never a resolved Buff.
  Optional derived union spans retain actual start/end cursors for action
  summaries. They are labelled derived consumption, with matching counts and
  type names; recording those ranges does not promote them to reviewed exact
  action semantics.
  An unnamed numeric ability-event value is retained without an invented enum
  name and keeps the effect pending; complete stored framing and a known event
  meaning are separate requirements.
- The ATK-scale, Breaking Attack, Definite Value, normal-damage and Poise
  contracts use `il2cpp.reviewed_program` to authenticate selected signatures
  (including by-reference parameters), typed fields, enums, code windows,
  linked calls/branches and literal operands. Split code sections and the
  anonymous calculation dispatcher are reviewed explicitly. Native patch guards
  can use indirect tables; old named IFix helper calls are not a current proof.
  These contracts establish conditional arithmetic and stored routes, not final
  damage or a live invocation. Build-specific declarations stay in their JSON.
- [`buff_selected_roots.py`](../../scripts/game_data/memorypack/buff_selected_roots.py)
  composes independent positive-heal, scene-object event-map,
  attribute/condition and recursive sword-damage child receipts through all
  thirty root fields. Each route retains its selected logical identity,
  current native and child gates, contiguous field cursors, source ID and
  physical EOF. Only the complete current family census admits these source
  rows; a standalone selected diagnostic does not authorize publication or
  establish that its actions execute.

## SkillData stored action members

[`skill_timeline_two_five_member.py`](../../scripts/game_data/memorypack/skill_timeline_two_five_member.py)
also admits `CheckTargetInScreen`, `ConvertWeaknessToInterruptible`,
`PatrolRefreshCheckPoint`, `PlayNormalDashAnimAction`,
`TyphoeaArcheryClearMissileAction`, and `TyphoeaArcheryGetPhantomPosAction`.
Each keeps its own union identity, generated wrapper, whole native reader and
owned continuation fragments. Their four inherited members precede one
concrete member: respectively `TargetSettings`, `TargetSettings`, a float,
a byte, a byte, or a string. The contracts recheck the ordered source calls,
exact final setter and any nested MethodSpec context against the explicitly
selected native inputs before the shared Skill reader admits them.

This closes stored action grammar only. A nonzero byte keeps its raw value;
the managed names do not prove a screen test, converter behavior, distance
units, dash direction, missile visibility, target ownership or execution.
Null wrappers and null child values remain independent, and every decoded
action must end at the next authenticated source boundary. Whole SkillData
publication still requires the complete current family receipt and the
source-bound prior cursor selection.

## The rules every contract shares

Each was violated at least once and caught.

- **Equal member counts never select a layout.** Select from an independent
  token/module or registered-type join, never from arity, a managed name or
  byte length.
- **A shared type argument permits profile reuse, not instance merging.** Each
  repeated target or scalar context is its own instance with its own null state.
- **Structural equivalence is not shared behavior.** Tags sharing a parser
  branch keep distinct union identities and effects.
- **No legacy tag/name aliases.** Current routes contradict the legacy map, and
  exact byte consumption does not validate a legacy label.
- **Source cursor order, not destination layout.** A later object offset never
  moves a field later on the wire; setters, getters, casts, stores and cached
  constructions consume no source bytes. Enum and static type contexts pick
  the helper without adding a header or narrowing the allowed bits.
- **A normal exit may tail-jump to the write barrier**; pin the instruction and
  the separate null rejoin. Readers cross chained unwind regions, so the first
  `.pdata` end is not a record or function end.
- **Null, empty and null-wrapper are three states**; lengths below -1 fail
  closed, and a completed or null child never makes a later terminal byte or
  DWORD optional.
- **Lists reserve the remaining minimum tail before iterating**; count, null
  and loop framing stays conditional on the shared reference-list consumer, and
  a provider bridge proves neither element width nor runtime selection.
- **An unknown tag or nested union stops at its own first byte**, with no scan
  for a later marker; completed children are kept, incomplete parents are not.
- **Raw widths stay anonymous.** Several `Double`-named payloads consume four
  bytes; a vector may be three variable-width scalars rather than twelve raw
  bytes, and only the consumer's own advance decides.
- **A managed action, type or enum name is an identity.** It establishes
  nothing about behavior, units, boolean meaning, ownership, activation or
  execution order.

## What stays unresolved for every action

- **Live provider selection.** A static reader is structural evidence, not proof
  the formatter executes; IfElse paths overwrite the callsite companion in
  native thunks, and reuse reaches state-dependent dispatch. The saved
  gameplay-semantics profile observes seven selected
  `ExecuteInternal` outcomes with bounded raw data words and opaque target
  carriers. It does not record the MemoryPack formatter provider, source-file
  identity, or action union tag at that boundary, so its receipt cannot close
  a serialized action's live provider selection. A dedicated hook needs a
  validated same-call or stable-key bridge between source identity, union tag,
  and selected provider before a capture is requested for that join.
  The existing Skill cursor profile supplies admitted source identity and
  before/after child cursors, but omits the provider result. The current
  [IL2CPP context contract](../../scripts/game_data/contracts/il2cpp_context_audit_native.json)
  proves a conditional MethodSpec chain through `ReadPackable`, `ReadValue`
  and `GetFormatter`, followed by cache lookup, construction and dispatch.
  It does not establish initialized companion contexts or cache contents.
  A useful provider extension must retain that admitted source scope and
  record the actual companion context, returned formatter, class dispatch
  target/companion pair and source cursors together. Repeating the existing
  cursor or execution profile does not supply this missing observation.
- **Legacy suffix ownership for partial rows.** An unsupported action or
  damage-processor route leaves a physical gap in the bounded reader; the
  derived whole-record route does not convert that row into a complete one.
- **Field meaning and payload encoding** for anonymous scalars and byte spans,
  and runtime meaning even where a native enum names the stored number.

`memorypack.buff_corpus` fails on a malformed prefix even when the suffix
succeeds. `memorypack.buff_1b_corpus` joins exact-closed tag `0x1B` records to
re-streamed bytes and the `BlowOffAction_Data` reader without authenticating
root-field ownership;
[`buff_1b_action_native.json`](../../scripts/game_data/contracts/buff_1b_action_native.json)
names the thirteen `BlowOffAction.Data` fields in source order and proves a
guarded direct call from unpatched `ExecuteInternal` to
`ControlledStateComponent.ApplyBlowOff` -- a runtime consumer, not per-field
expressions, units, target choice or an observed execution.

**Recovery queue.** Close the remaining damage-processor routes from their
native union contexts, then the unsupported condition actions and
`buffEventAction` actions (until then those outer frames cannot join the named
middle). The selected
[`buff_icon_config_native.json`](../../scripts/game_data/contracts/buff_icon_config_native.json)
contract already closes `iconConfig`'s 19-member stored body at the following
independently accepted `id` marker; its presentation behavior stays unresolved.
The residual Skill action tags are a separate offline grammar queue: for
example `ReadSkillSettingData` already has a selected Buff reader contract,
while `PauseComboSkillTime`, `EffectControlAction` and
`InverseSpellInfliction` have finite native source bodies whose child calls
can be joined independently. Missing admission of these stored layouts is
not a reason to request a provider capture.

## Buff runtime invocation observations

Current passive capture layouts use the named generated setter claims in
`capture_closed_cells.json`. A typed closed wrapper load and unchanged parameter
store establish the physical BlackboardDouble cells without open generic
instance offsets. This establishes no serialized-source transfer, Boolean
normalization, runtime type selection or provider lookup; the installed-format
validators keep those separate obligations. Current HealDetail observations
retain typed ProtoBuf property access, field numbers, raw message snapshots and
full-width getter result identities without pointee reads. They are not whole
message encode/parse intervals. The selected named IsPatched helper has no
retained direct caller site in this scope, so its inactive hook is omitted;
inline patch-table/delegate routes remain unobserved.

The reviewed
[`Buff paired recipe`](../../scripts/game_data/contracts/buff_runtime_paired_capture.json)
selects uniquely resolved lifecycle and action entries, their argument layouts,
common runtime state and bounded stored Data fields. The maintained
[`paired reader`](../../scripts/game_data/buff_runtime_paired_inspect.py)
uses the generic trace reader and explicit invocation IDs to join entry and
return records. A completed pair proves the recorded Boolean return and
sequential snapshots for that selected synchronous call; it does not establish
the final effect of an action, a source union tag or a serialized node.

A retained normal-combat and combo session exercised two user-reported squads:
庄方宜、黎诺、弧光、佩丽卡, then 卡缪、诀、洛茜、洁尔佩塔. Its saved
records show OnStart, OnTrigger and OnFinish enclosing `_ExecuteBuffAction`,
and Buff action dispatch enclosing further Buff dispatch, initialization and
lifecycle entries. These are nearest **observed** synchronous ancestors;
unobserved intermediate calls remain possible. Runtime execution can therefore
reenter the Buff lifecycle while another observed Buff event call is open;
the diagram must not imply a single linear, nonrecursive pass.

Every reached OnTrigger entry/return pair in that session reduced the raw
32-bit `m_triggerCount` value by one modulo its stored width, including negative
signed values. This establishes an observed counter transition, not the meaning
of a sentinel, its initialization policy or a universal rule for every Buff.
Reached AbilityAction.Reset pairs cleared the common executing-state cell;
some also cleared the prior execute-result byte. The selected CheckHp call
inside `buff_common_checkhp_passiveskill`'s OnBuffTrigger enclosure returned
both Boolean values. This joins an observed Buff ID/event enclosure to a named
condition outcome, without proving the exact serialized condition node or the
HP inputs that caused that outcome.

SelfRotateAction and BlowOffAction returned true in reached calls, but those
calls had no observed `_ExecuteBuffAction` ancestor; do not attribute them to a
Buff just because their hook names share the recipe prefix. CheckSkillDamageType,
SaveHealValue and the two selected assignment entries were not reached in that
session. Missing coverage says nothing about whether their implementations work.
Two finish/dispatch enclosures also changed the same receiver's instance-UID
cell to zero before return. A pointer retained across entry and return therefore
does not establish an unchanged logical Buff instance or allocation lifetime.

The original session is retained under
`scratch/reverse_engineering/endfield_capture/buff-paired-20261013T102230425`;
changing counts and per-call examples are in its corresponding
`reports/runtime_capture/` analysis directory. Those local files support these
selected observations; the reviewed recipe and maintained readers own the
observable fields and pairing boundaries. No installed-format root admission,
WebUI publication or missing historical Skill receipt is promoted by this run.

The maintained
[`source-candidate comparator`](../../scripts/game_data/buff_runtime_source_candidates.py)
now reuses a completed immutable Buff family receipt and the native dispatch
contracts actually consumed in that epoch. Captured exported bytes must match
the admitted source hash; the root still needs its original thirty-member,
source-ID and EOF receipt. The comparator selects the recorded Buff event,
declared action Data type and serverActionIndex, then compares every supported
captured stored configuration field at its proved source span. Current action
receipts retain direct fields either on the action or in its parent subreceipt;
their missing type labels are supplied only by a byte-bound, selected-build
dispatch declaration. No reader is selected from a class name or tag alone.
Changed entry/return identity snapshots revoke the enclosing-context match;
multiple matches and unsupported fields remain explicit. Agreement at the two
boundaries still does not establish intervening immutability or allocation
lifetime. The comparison reuses the existing family result; it does not admit
new roots or rerun that expensive gate.

The retained combat session provides configuration-concordant candidates for
the named sword-check passive's CheckEntityNum and UI notification nodes, the
common HP-check passive, Camille's bat target check/reset nodes, and selected
skill-setting, Buff-blackboard and attribute-storage nodes. In explicit
OnBuffTrigger enclosures of the common HP-check passive, the observed false
CheckHp calls had no reached SendBattleSignalToLevel entry; the one reached
true case did contain that entry and its true return. The sword-check passive
also repeatedly contained a true CheckEntityNum return followed by a true UI
notification return in the same event enclosure. These are observed contrasts,
not a general proof of sequence short-circuit rules or downstream signal/UI
effects. The unique stored candidates do not close runtime source loading or
the exact serialized-node join.

The reviewed paired recipe consequently adds the outer AbilityAction.Execute,
both SequenceAction execution routes and IfElseAction's child-sequence
references. This scope can observe the outer result/state snapshots and match
nested sequence receiver bits to condition/success/failure references in a
single conditional call. It is prepared against selected native signatures;
the first retained session did not arm those additional entries. Its results
must not be retrospectively filled from the earlier condition-only trace.

A second retained session,
`scratch/reverse_engineering/endfield_capture/buff-paired-20261013T113956624`,
used only the user-reported Camille squad and armed those additional entries.
Its explicit pairs establish outer AbilityAction.Execute results and both
sequence execution routes; the selected IfElseAction.ExecuteInternal entry
remained unreached. Every reached
outer Execute returned the same Boolean as its return-boundary
`m_executeResult` snapshot. Its entry state was Pending and its return state
was ExecutedNotStartTick or, for a subset, Ended, using the selected metadata
enum declaration. A false action result therefore does not mean that the
action remained Pending, and a true result does not by itself establish Ended
or a gameplay effect.

Reached named ExecuteInternal calls had an observed outer Execute ancestor
with the same receiver and target argument bits. For CheckEntityNum, CheckHp,
Buff-blackboard reads, attribute storage, SelfRotate and BlowOff, the inner
result-field snapshots were still false even when the inner call returned
true; the outer return snapshot then held true. Other reached named actions,
including skill-setting reads, already held true at their inner entry. These
boundary observations distinguish result preparation and later changes;
they do not locate a particular store instruction or prove that all action
types use the same return policy. The maintained paired reader retains those
field changes, while the reviewed recipe owns their field/type declarations.

Most reached ExecuteInstant calls enclosed a same-receiver, same-target
SequenceAction.Execute pair and returned the same Boolean; a smaller false
subset had no observed nested Execute entry. All reached ordinary Execute
calls enclosed an observed AbilityAction.Execute call. Some sequences
continued to later observed action calls after a false return, and some
returned true despite an observed false child. Thus neither unconditional
short-circuiting nor conjunction of all observed child results is a valid
general explanation. Selected action-return policies, sequence context,
iteration/target selection and unobserved intermediates still need a native
consumer join; the capture does not identify which policy caused a case.

The common HP passive repeated the earlier contrast: false CheckHp cases
enclosed false Execute and ExecuteInstant returns without a reached battle
signal, while a true case enclosed the signal and true sequence returns.
Camille's bat target-check enclosure separately showed a true condition
followed by a false sequence result, and another sequence in that event
returned true. A condition result, its containing sequence result and the
Buff event enclosure must therefore remain separate observations. The frozen
source-candidate comparator again found configuration-concordant nodes;
exact runtime source loading, serialized-node selection and downstream
effects remain unresolved. Per-call counts and examples belong to this
session's analysis and source-candidate reports under `reports/runtime_capture/`.

### Checking Buff observations against character configuration

Use localized skill and combat-talent descriptions as expected behavior, then
join CharGrowthTable skill groups and PotentialTalentEffectTable attachments
and patches to stored action records. A character's exact-ID
CharacterTemplateData and reachable AbilitySystemData component additionally
own its registered/default-enabled skills. A filename containing a character
ID only selects an investigation candidate. Likewise, a template's
maxPotentialEffectBuffId declares an available reference, not the player's
current potential level. Attribute/effect names require the selected metadata
enum declaration, not a filename, icon or apparent numeric value.

The user supplied combat-talents-unlocked and potential information for the
two retained squads. The comparison uses the highest published combat-talent
rank as a stated selection; actual rank, skill level, equipment, panel
attributes and resolved runtime Blackboard values were not captured. Keep
approximate user-provided potential levels approximate. The existing
[derived values reader](../../scripts/game_data/memorypack/derived_values.py)
reads selected source records to EOF with internal-ID agreement under its
selected-native wrapper plan, retaining structuralOnly union interpretation.
This is distinct from canonical full-family admission and does not replace a
missing historical Skill receipt. The current export guard, rather than an
old graph edge or stale Skill-reference publication, decides source freshness.

This comparison separates three easily confused mechanisms. The common HP
passive stores a low-HP ratio check followed by the PlayBgm battle signal;
it is not evidence of a character's healing talent or music actually playing.
Camille's bat target-check condition sequence contains both the entity-count
check and a comparison of EntityBB_retargeting. The recorded entity-count
true / containing-sequence false contrast is therefore compatible with an
additional condition. Its stored IfElse has alwaysNext; zero hits at the
selected IfElseAction.ExecuteInternal entry remain an observer-route gap,
not proof that the conditional mechanism never ran. The exact runtime branch
and the result of the unhooked comparison remain open.

Keyed providers and talent/potential patches explain apparent numeric
conflicts. Camille's talent1_atkup modifier names FireDamageIncrease in the
selected metadata; its configuration enables the keyed stack limit, so the
adjacent fixed limit alone does not establish the resolved limit. Ikut's
highest-potential effect overwrites the normal skill's counter
requirement, so fixed stacking capacity does not establish the required
trigger count. Pelica's potential attaches a listener Buff carrying the attack
increase, duration and limit used by its child Buff. Wulfa's first potential
patches damage multipliers and energy return directly on her skills. Read the
patch operation and activeCondition before combining values; stored fallback
zeros and disabled actions do not describe an evaluated effect.

Healing talents need the same ownership distinction. Aglina's healing
parameters and target-selection conditions live in normal/combo SkillData;
absence of an entry for a similarly named standalone healing Buff does not
show that the talent failed. Her selected stored HP checks use a near-full
ratio threshold while the description says full HP. Preserve that boundary as
an open interpretation of runtime target selection and tolerance, rather than
declaring a gameplay bug. Liino's aura/exit effects also require tracing
skill-supplied provider values and the player's enabled potential patches.
Lizhiyan's descriptions additionally use conditionId1/2 and
conditionPostDesc1/2 in CharGrowthTable: a generic group description can be
empty while both wisdom/will forms have complete authored text. Her live form
cannot be selected from a Buff name without the panel-attribute condition.

The selected description/configuration comparisons agree on checked
attachment and patch values, and matching named Buff IDs reached lifecycle
entries in the saved sessions. This supports the interpretation; it does not
independently verify final damage, healing, energy, resolved stack count or
exact character receiver. The per-character checklist, user selection,
configuration assertions, unresolved source references and changing counts
remain under reports/runtime_capture/buff-character-crosscheck/.

### Native execution and recorded callsite joins

The reviewed
[consumer contract](../../scripts/game_data/contracts/buff_action_consumers_native.json)
now contains narrow claims for IfElse execution routes, its custom return
policy, outer result composition, heal calculation/modifier calls, separate
energy delivery paths, and potential/talent attachment access. The selected
false IFix guard returns IfElse's owned alwaysNext Data byte, independently of
its declared CustomReturnType getter. The outer AbilityAction.Execute body
contains policy/custom-result getter dispatch, common result-cell reads and
writes, byte OR and Boolean normalization. These findings explain why a false
internal result need not make the outer action false; the contract does not
claim every alias or the player's live policy.

The selected sequence loop also reads Context.executePolicy. Its reviewed
normal path uses LastSucceed continuation, while the LastFailed path reverses
the last-result continuation test and resets the policy. NotNextCheckAction's
selected normal body writes the latter policy. This is a selected compiled
path interpretation, not a universal rule for patched code or a claim that
every observed continuation came from that action. Capture-only child-result
lists cannot identify the policy setter or its current Context receiver.

The maintained
[callsite reader](../../scripts/game_data/buff_runtime_callsite_inspect.py)
authenticates the selected native pair against the retained profile, derives
IfElse._DoExecute's direct condition ExecuteInstant and selected-branch
Execute callsites from complete E8 bytes, and joins their return RVAs to
recorded explicit invocation pairs. Existing records agree with these
callsites even though the selected ExecuteInternal observer was not reached.
The selected compiled virtual-dispatch helper contains an implementation
comparison and inline target-copy/_DoExecute route that can bypass that entry.
Therefore zero named-entry coverage does not establish absent IfElse
execution. Return-address agreement still does not independently authenticate
loaded instructions, identify a serialized node or prove object lifetime.
In Camille's recorded bat target-check enclosures, the complete condition
sequence returned false even when its entity-count condition returned true;
the enclosing outer action returned true. The unobserved extra comparison's
exact live operands and outcome remain open.

PotentialUtil and TalentUtil's selected attachment paths contain
CheckSkillConditions and distinct typed attachSkill/attachBuff accesses.
CalculatePotentialModifiedValue's selected body has addition, multiplication
and overwrite paths, consistent with the authored patch operations; actual
unlocks, ordering inside patch production and evaluated Blackboard values
remain separate from the initialization layer order below.
Skill.AssignSourceBlackboard additionally has a checked incoming-reference
join to ActionBlackboard.Assign.another, with compiled continuation to
Ability.AssignSourceBlackboard. Buff.Reset reaches Blackboard.CreateFrom and
assignment, and CreateBuffAction reaches action-Blackboard access/evaluation
and AddBuffByAbilityAction. Skill._OnCreate's initial extraBlackboard transfer
now has a separate checked stack-spill witness, rather than being inferred
from call presence or accepted by the old register-only argument checker.
HealAction's compiled body reaches target collection, HealModifier,
BattleFormula.CalculateHeal and Modifier.NewHeal. ObtainCostAction contains
separate ultimate-SP formula/modifier and BattleManager.GainAtb calls.
Compiled call presence does not establish an operand-to-amount join, a target
receiver or an accepted final resource change.

### Initial Blackboard transfer, layer order and reset

The maintained
[stack argument checker](../../scripts/game_data/il2cpp/stack_argument_flow.py)
decodes the original save/load widths and stack addressing, follows local
branch edges and carries entry-relative slot coordinates through stack frame
changes. The incoming Skill extraBlackboard save and later reload select the
same QWORD slot, which reaches ActionBlackboard.Assign.another. The selected
normal prefix contains no overlapping write, outgoing-home clobber or escaped
stack address that invalidates that slot. This is conditional on the named
false IFix guards, normal Win64 callees and valid non-forged heap references.
It covers first arrival at that call within its method prefix, not a path
that leaves the prefix and subsequently re-enters or a live patched method.
The reviewed consumer contract records this check and fails closed when it
cannot reproduce the witness. Closed generic IList selectors are resolved
from the selected native type, not admitted through anonymous type indices.

Reading the selected compiled initialization body together with the typed
Skill, SkillData, SkillPatchData, AbilitySystem and BlackboardWithOwner fields
gives this order. These source/destination and snapshot observations are a
direct interpretation of that body; the contract's separate field/call claims
do not constitute a complete alias or whole-method proof of this table.

| Stage | Source | Destination and consequence |
| --- | --- | --- |
| Base | SkillData.blackboard | A new direct Blackboard receives the configured entries through AddRange; the ActionBlackboard wrapper carries owner context separately. |
| Patch | SkillPatchData.blackboard, when patch data exists | Assign into the same Skill.blackboard direct storage. |
| Extra | Incoming extraBlackboard, when present | Assign after patch into that same direct storage; its stack transfer is independently checked. |
| Creation snapshot | The merged direct Blackboard | A separate Blackboard copy becomes Skill.onCreateBlackboard. It already includes this initialization's patch and extra inputs. |
| Owner source | Skill.owner.sourceBlackboard | Assign into the running direct Blackboard after the creation snapshot. It is not part of that snapshot. |

For unique matching keys and the selected ordinary assignment routes, the
running initialization precedence is therefore base, then patch, then extra,
then owner source. The snapshot stops after extra. Owner.entityBlackboard is
a different field reached by the entity getter; it is not the final source
assignment in this table. ActionBlackboard's list Assign selects its direct
getter and forwards the list to Blackboard.Assign. Its entity read channel
must not be treated as another copied initialization layer.

Blackboard is a List<DataPair>, not an intrinsically unique-key dictionary.
The empty-destination IList Assign route appends the input through AddRange;
that route and the copy constructor do not themselves deduplicate it. On the
selected nonempty assignment route, each input pair reaches _AssignInternal.
The observed key-match route replaces a matched existing slot, retains the
existing isDynamic byte and returns; the no-match route appends. The maintained
[matched-pair checker](../../scripts/game_data/il2cpp/blackboard_assignment.py)
independently checks the selected true-comparison fallthrough, DataPair layout,
complete pair stores, retained dynamic byte and return. It does not prove the
entire preceding scan, comparison implementation or incoming base provenance.
The body also contains the ignore-case comparison implementation route; exact
comparator behavior and live Burst/IFix selection remain separate. Thus a
later matching assignment replaces values rather than adding/multiplying
them, while a raw copied input can still contain duplicate keys. Do not turn
the unique-key precedence into a universal deduplication rule.

Skill.AssignSourceBlackboard's selected normal body clears running direct
storage, restores onCreateBlackboard and then applies its new extraBlackboard.
It forwards the creation snapshot and new extra to Ability.AssignSourceBlackboard.
Consequently the creation-time extra is already in the restore baseline; this
method does not merely accumulate writes on the old running table. It has no
additional owner.sourceBlackboard assignment in that selected body. The
Ability continuation similarly clears direct storage, assigns its supplied
source and extra, then clears/rebuilds m_initialDynamicBlackboard through
AssignDynamic using the merged direct storage. The dynamic sink's input
selection is now checked below; complete bulk-list copying and the later
consumption of this dynamic baseline remain separate proof obligations.

Still open are the live extra/source entries, internal iteration while talent,
potential and other systems construct a patch, duplicate keys in actual
inputs, current IFix selection, expression-specific lookup and the exact
evaluated value used by an action. Additional native joins or appropriately
typed runtime values are needed for these, rather than another ordinary
combat capture to re-establish the initialization layers above.

### Skill-data construction, keyed lookup and dynamic selection

CreateSkillDataWithCharInfo's selected ordinary construction path obtains the
base SkillData, applies CalculateLevelSkillData, then CalculateTalentModifiedSkillData,
then CalculatePotentialModifiedSkillData. The
[reference-result checker](../../scripts/game_data/il2cpp/reference_result_flow.py)
checks that the base result reaches the level template input, the level result
reaches the talent template input and the talent result reaches the potential
template input. It validates selected native reference representations and
types, complete register copies, normal Win64 call preservation and contiguous
conditional fallthrough; scalar/byref/pinned records, partial pointer copies,
unknown instructions and unconditional control transfers cannot supply that
join. This establishes the selected object chain, not just call ordering.
Branches can skip stages, and no live character information or unlock set is
admitted. The level body contains a clone, selected skill-patch Blackboard
access and assignment. The construction body subsequently has an optional
CreateSkillOptions Blackboard assignment into the resulting SkillData's
Blackboard. This is before Skill._OnCreate's separate initialization layers.
These observations do not equate a later arithmetic modifier with simple
last-writer replacement, or prove ordering among multiple talent nodes.

The
[keyed Float query checker](../../scripts/game_data/il2cpp/blackboard_query_flow.py)
checks the complete ordinary ActionBlackboard.TryGetFloat program. It obtains
direct storage and queries it first with the incoming key and output pointer.
A successful result returns immediately. Only false reaches entity storage,
where the same key and output pointer are used. Missing entity storage or a
second false result writes Float zero and returns false. A null direct getter
takes the error route, not the entity fallback. Thus Boolean success, not a
nonzero numeric value, determines whether entity lookup is attempted. This
proof includes the checked local branches, virtual-slot selectors, argument
lanes, return values and restores under false IFix selection. Observed keyed
String and Double bodies have corresponding source/fallback routes, but that
observation is not a complete proof for those programs or for typed
BlackboardDouble/BlackboardString expressions. GetAllDataPairs appends direct
then entity entries into a new list; its flattened inventory is not a keyed
override operation or a substitute for lookup precedence.

The dynamic entry check in
[the assignment checker](../../scripts/game_data/il2cpp/blackboard_assignment.py)
proves that _AssignDynamicInternal's false-IFix prefix compares the incoming
DataPair.isDynamic against the retained false AL and returns false before
scanning when the incoming pair is not dynamic. Numeric/string convenience
AssignDynamic bodies construct a dynamic pair; the pair and list variants
preserve their supplied flag. The bulk-list body's instruction inventory is
now completely decoded by the
[pair vector reader](../../scripts/game_data/il2cpp/blackboard_vector_transfers.py),
which composes the maintained MOVQ/PSRLDQ readers with a complete register
UNPCKHPD operation. The selected field-copy window sends key, valueDouble,
valueStr and the supplied isDynamic byte to _AssignDynamicInternal; it does
not mark every copied record as dynamic. The
[bounded helper-entry checker](../../scripts/game_data/il2cpp/vector_preservation.py)
proves both intervening calls use the same entry graph, with only GP operations,
local branches and RET exits, so they do not clobber the source vector lanes.
That bounded graph is not promoted to a pdata-owned whole function. Correct
source-record address, unchanged caller destination and helper memory
noninterference remain explicit conditions. The separate
[list-loop checker](../../scripts/game_data/il2cpp/blackboard_bulk_iteration.py)
now checks the complete selected ordinary loop: index zero, one captured
helper return, positive-count entry, both source bounds, record addressing,
the independently proved field-copy window, Int32 increment and signed
backedge. It passes every selected record through the dynamic sink; the
sink's own flag filter still decides whether that record is accepted. The
on-disk MethodInfo cell names SafeCount<DataPair>, but its registered entry
differs from the compiled helper call target. Those identities remain
separate; a shared name or similar body cannot join them. Correct helper
count, resolved live context, valid unchanged source/list/frame and helper
memory noninterference are conditions. Actual collection mutation and later
baseline consumption remain unproved.

The selected dynamic matched-key body separately tests the existing entry's
flag. If it is false, the byte-derived conditional edge enters a diagnostic
fragment containing DLogger.LogError, whose ordinary continuation jumps back
to the same replacement block used for an already dynamic entry. It therefore
does not establish rejection or protection of a static key: after a normally
returning logger, the selected route still passes the incoming full pair to
the list setter and returns true. This cold-route and replacement observation
is a direct interpretation of checked branch targets and bytes, not a claim
that the complete collision loop or incoming bases have been formally proved.
Unlike ordinary Assign's retained old flag, this selected dynamic route uses
the incoming dynamic pair, so the key can become dynamic. RemoveAllDynamic's
observed normal loop scans backwards and removes flagged entries; detailed
scan/list-setter and complete bulk transfer proofs remain distinct.

The reviewed consumer contract contains independent groups for the typed
construction joins, complete keyed Float lookup, dynamic input filter,
selected bulk field transfer, captured-bound loop framing and embedded-table
partitioning. The
[table partition checker](../../scripts/game_data/il2cpp/embedded_rva_switch.py)
binds an unsigned guard, indexed DWORD load, image-base addition and indirect
jump to a tail RVA table. Both talent/potential code prefixes now decode
completely, and every table target is a checked code boundary. The former
tail failures came from treating that table as instructions. Older base-register
preservation remains conditional; complete framing does not prove every
operation or live IFix/lazy-initialization selection.

The selected talent construction clones the template and its Blackboard,
then enumerates the supplied HashSet of talent node IDs and calls the effect
calculator for selected nodes. It does not sort those IDs into authored-file
order. The potential construction instead iterates the unlock bundle's stored
records, reads their signed level, compares it with the zero-extended supplied
UInt32 potential level, and skips a record whose level is greater. The named
PotentialUnlockData getters independently identify the level and effect-ID
Bean field requests used by that inlined route. Eligible records pass their
effect IDs to the common effect calculator. This is selected native control
and field interpretation, not a proof of live unlock-set contents or every
Bean-array transition.

The effect calculator checks active conditions and has distinct parameter,
numeric Blackboard and string Blackboard modification routes. Its numeric
route tests Blackboard.TryGetFloat's Boolean result. False enters a logger,
then rejoins the same calculation and Assign continuation as success; it
does not skip the modifier on a missing key. The loaded Float is modified,
converted to Double and written back. This observation does not yet prove
the lower Blackboard getter's complete failure-output semantics. Unlike
initialization-layer replacement, Add/Multiply/Overwrite effects can perform
arithmetic on the previously read value. All code bytes in this selected
effect body now decode, including the existing signed Single conversion
reader and correctly prefixed packed Double-to-Single conversion. Numeric
results, rounding/exception outcomes, live condition selection and complete
typed-expression lookup remain open.

CheckHp's selected ratio path obtains hp/maxHp and converts the Double ratio
to Single before comparison; its comparison setup also supplies a small
Single constant. The authored near-full ratio threshold is not itself a
measured HP value. Aglina's actual healing recipient, runtime HP and the
comparison helper's complete tolerance semantics remain open. Resolving these
amounts requires a correctly typed floating-result or settlement observation;
the existing paired GP bool/void preset alone cannot supply them. The separate
[numeric recipe](../../scripts/game_data/contracts/buff_runtime_values_capture.json)
inherits the reviewed paired recipe and prepares named Blackboard getters,
keyed Float byref outputs, calculated healing returns, Skill source reset
identities and talent/potential effect-entry arguments. Selected undecorated
R4/R8 returns use a typed XMM0 return ABI and are stored as raw IEEE-754 bits;
ordinary floating input arguments remain refused. A scalar-byref read
requires the selected native type's byref bit, not just a declared Float name.
HealPackData's normal instance entry receives an unboxed value pointer, not
a managed-object identity. Nullable detail fields remain absent-carrier
observations; offset-zero invalid byref pointers remain read failures.
Finite values, signed zero and nonfinite payloads retain their raw bits in
offline analysis. An effect entry is a candidate-selection observation,
not proof that its active-condition check passed; protocol HP fields and a
healing return do not establish a final HP write. A clean numeric capture now
supplies initialization candidate arguments, Boolean lookup results, byref
Float values and typed numeric returns. The
[numeric inspector](../../scripts/game_data/buff_runtime_values_inspect.py)
reuses its completed paired inspection and validates explicit synchronous
enclosures. Observed same-input GetFloat/GetDouble child pairs agree with
Single rounding at the bit level. Rechecked compiled query callsites label
direct reads and entity fallback separately; both successful zero and failed
zero are observed. Not every lookup has one of those named caller sites.
Neither sequential queries inside an action nor an entry-only initialization
event invents the missing invocation interval of an unhooked helper.

The supplied potential levels and effect-entry candidates agree with the
reported squad configuration. Talent effects are visited across skill
templates, including ordinary attacks, shared movement and equipment skills;
repeated candidate entries do not imply that each effect modifies every
template. Skill-ID and active-condition filtering remain separate. Selected
potential multiplier predictions from the retained level/effect tables agree
with later numeric returns in the corresponding initialized-skill environment
candidates. Matching a value does not identify an unobserved expression key
or distinguish equal-valued source fields. Numeric modifier reads in this
capture return success; the static missing-key logger/continuation route
therefore still lacks an observed failure case.

Ability.Init entry snapshots can supply earlier matching environment/skill
identity candidates for later action enclosures. The inspector retains that
association as a candidate because unobserved reuse, reinitialization and
lifetime are not excluded. The captured healing return's candidate belongs
to Camille's combo environment, while the captured CheckHp candidate belongs
to Rossi's combo environment and evaluates a zero threshold. It does not
cover Aglina's near-full threshold case. Skill source-reset snapshots preserve
the observed onCreate/ActionBlackboard identities, which supports mutation of
contents without proving which contents were restored.

GetFinalHealValue is only the HealPack-level return boundary: the selected
BattleFormula.CalculateHeal body subsequently has a heal-type-dependent
attribute multiplier before its own numeric return. The reviewed consumer
contract's separate heal-boundary group rechecks named pack/report/cleanup
calls and the outer scalar multiply; these presence claims do not certify
every numeric alias or live branch. The protocol source,
target, value and current-HP fields remain unpopulated at the captured pack
boundary. Those zeros are not measured actor HP or evidence of zero healing.
The outer formula result, populated settlement fields, exact recipient and
final HP update need later observations. The current capture therefore does
not establish Aglina's healing amount or final HP effects. Changing
counts, native anchors and per-call examples stay in
the ignored reports/runtime_capture/ investigation outputs; these observations add no
whole-Buff roots or final-effect admission.

The passive resolution recipe extends the numeric recipe without copying
its catalog. Its reviewed inheritance updates the two expression observers
with the stored key selector, string key and Single literal, and turns the
effect calculator into a completed interval. Concrete scalar cells reuse the
named setter/source proof; open generic offsets remain forbidden. The ordinary
public scalar getter has a compiled keyed-failure diagnostic/zero-return path
and a separate direct-value consumer. Call/operator presence alone does not
prove every virtual or IFix branch.

An important write-observer boundary is now explicit: the selected
Blackboard.Assign(string, double) body inlines its internal assignment rather
than calling the named internal writer. Observing only _AssignInternal would
miss those initializer write submissions. The resolution recipe therefore
observes the actual Double Assign entry and return through a narrowly typed
instance void(this, string, double, MethodInfo) caller. Its Double input uses
XMM2 and is retained as raw bits; other floating-input signatures remain
refused. Internal static/dynamic writer requests remain separate observations.
A completed void write request is not a destination collection snapshot or
evidence of live IFix selection.

The selected HealAction contains the outer formula, NewHeal, modifier Apply
and final-delta consumers. The named _OnHealed notification writes distinct
finalHealValue and realHealValue context cells and consumes the final-delta
getter. These reviewed presence claims leave complete numeric/receiver aliases
conditional. Formula values, modifier values, realDelta, stored client HP and
cached server HP must remain distinct. The closed SyncedValue<double> client
cell is derived from its sequential Double-pair declaration and the ordinary
HP getter's actual return cell, never from open generic offsets. Passive cell
reads do not call a game getter or establish its live patch selection.

Resolution capture acceptance requires starting before initialization with the same
potential/talent squad, exercise Camille/Rossi skills and combos, then trigger
Camille and Aglina healing after a specific character loses HP. Require clean
complete effect/query/write enclosures, readable selector/key/literal fields,
outer formula returns, and same-action/same-receiver HP writer entries and
healing notifications with target identities. Compare explicit recorded
intervals, typed bits and sequential fields; do not join by time proximity or
reuse a prior lifetime. Missing observers, inlined routes or incomplete pairs
remain missing coverage. The prior saved numeric session has been replayed
with the extended reader and contains none of these new boundaries, so its
unchanged preset cannot decide these questions. Complete collection contents,
populated settlement packets and server acceptance remain open in that saved
session. The reviewed
[resolution recipe](../../scripts/game_data/contracts/buff_runtime_resolution_capture.json)
owns fields and phases; the internal tool README owns launch/case instructions.

The [bundled recipe](../../scripts/game_data/contracts/buff_runtime_bundle_capture.json)
extends those observations in the same capture with string submissions,
list Assign/AddRange/AssignDynamic intervals, modifier application results,
final-delta returns, named IsPatched decisions, and internal HealDetail codec
entry/return fields. The selected modifier ApplyResult is an Int32-backed enum;
its whole return bits and metadata names must remain distinct from Boolean
success. Modifier value, target type, delta type and cancellation reason are
separate fields. Global modifier/patch helpers record only under an already
recorded paired ancestor. Calls outside that scope are forwarded transparently
and their absence from the journal is a collection policy, not missing gameplay.

The uniquely owned internal codecs accept concrete value-type context byrefs,
forwarded as opaque pointers without any context layout or pointee read.
Public protobuf codec bodies folded across message types are refused by the
unique-owner gate. Codec fields before/after a completed call may establish
observed population, but do not establish transport direction, object lifetime
or acknowledgement. Named IsPatched records establish only those observed
checks; inline dispatch remains outside their coverage. Merge intervals retain
reached per-item submissions in explicit observed order; empty append and
inlined mutations prevent a complete collection claim. The same full-health,
injured-healing and cooldown-repeat cases cover this bundle; let temporary
Buffs expire before stopping. Do not widen missing cases into complete coverage.

The bundled normal Modifier instance methods receive unboxed value addresses.
Field offsets from IL2CPP type-definition metadata include a boxed object
header, which must be removed exactly once at the root. Passing the receiver
correctly does not prove field paths use its representation. A failed bundled
capture exposed this distinction: Apply/get_finalDelta read the environment
string with a boxed offset, and the strict recorder stopped on an unreadable
field. Other apparently readable fields from those receiver paths are also
misplaced and must not be interpreted. Preserve that failed journal as
non-admitted diagnosis; a clean earlier prefix does not repair its layout.

The corrected recipe requires a bounded concrete nongeneric value receiver,
normal method ownership, an explicit unboxed size on every receiver field
path, and a paired ABI. The retained proof binds the receiver type/method/size,
original boxed offset, storage width and unboxed root offset. Both preparation
and inspection fail closed on missing or contradictory declarations. The
sampler regression reproduces the invalid boxed string read and checks the
correct unboxed numeric/string cells at entry and return. This closes the
known observer layout bug; live coverage and healthy complete capture remain
requirements before using these fields as gameplay evidence.

A healthy bundled capture now closes representative query-to-write initializer
intervals, including Camille's healing keys, Rossi's talent and potential
keys, and Aglina's healing keys for normal/combo skills. The observed query,
submitted key and destination receiver occur inside the same effect call.
Multiplication cases round in Single precision before widening to the Double
Assign input. This goes beyond table-only value agreement, while stored-row
identity, every activeCondition branch and complete destination contents remain
separate. Direct-literal expression snapshots and their observed returns agree;
keyed selection and direct/entity query ownership retain their stated limits.

Source-reset descendants establish the live order for covered non-null extra
inputs: restore from the onCreate Blackboard, then assign the extra source
through ActionBlackboard, with additional dynamic merging on some paths.
Recorded source-list arguments match the enclosing reset's source identities.
The named calls and their order are direct evidence; list elements and all
inlined writes are not reconstructed from those pointers. The maintained
numeric inspector retains reset intervals and source arguments explicitly.

A completed Camille HealAction has distinct pack and outer formula returns,
a successful Modifier application, an observed same-action/same-receiver HP
writer entry, and later notification/client-HP snapshots. The client HP
change agrees with realDelta; the requested amount remains distinct from
rounded subtraction of HP snapshots. A later internal codec write contains
consistent source/target battle-instance IDs, amount and current HP. That codec
call is outside the healing enclosure, so matching identity/values corroborate
population without proving allocation lifetime or server acknowledgement.
DamageImmune cancellations are also observed: the typed result and cancellation
reason change while client HP remains unchanged. These are damage cancellations,
not failed healing or Boolean interpretations of an enum result. Aglina's
initializer keys are observed, but her live healing settlement and near-full
condition remain outside the covered representative chain.

The idle named IFix observer exposed an owner-selection gap, not evidence that
no patch guards run. WrappersManagerImpl is defined in multiple metadata images;
the Gameplay consumers call the Gameplay.Beyond.dll definition, while the old
name-only dictionary selected a logging-image definition. The image-qualified
recipe names Gameplay.Beyond.dll, and preparation rejects ambiguous declaring
types instead of choosing the last name. Qualification currently admits only
static scalar observers and records the exact image/type/method ownership;
it does not grant ambiguous field layouts. Live decisions at that corrected
entry still require observation. Preparation/inspection also bind paired
argument masks to the declared slot count, retaining the documented legacy
mask policy only for older schemas. No new capture is justified merely to
repeat the already covered healing and initializer cases.

Aglina's stored normal/combo healing routes have an earlier target-count gate:
`heal_const > 0` and `CheckEntityNum >= 2`, before the later HP-ratio test.
The normal skill counts the `explo` group and the combo counts `tar`; those
groups are not interchangeable. Covered calls associated with her earlier
skill-initialization candidates returned false at this quantity condition,
and her later HP checks and healing settlement were not reached in the saved
journal. This explains the representative coverage gap without claiming an
exact live count, an exact serialized-node identity or failed healing.
The stored later path tests the current main character below the near-full
threshold, otherwise finds a team candidate named `CureTarget` and tests HP
again. That authored fallback is not a proved live target choice.

`CompareFloat.ExecuteInternal` calls `ActionBlackboardExtensions.GetValueOrDefault`,
which calls `GetDoubleValueOrDefault` and the generic Blackboard parameter
lookup rather than the separately observed `ActionBlackboard.GetDouble`.
Absence from the ordinary getter journal therefore does not establish that
the comparison did not read a keyed expression. The selected native bodies
contain the Single-to-Double default conversion and Double-to-Single result
conversion; generic lookup success and the live intermediate scalar remain
unobserved. The maintained
[bundled recipe](../../scripts/game_data/contracts/buff_runtime_bundle_capture.json)
now pairs the comparator's inputs/result and observes the helper's expression
and supplied Blackboard identities at entry. Its floating default and return
are forwarded transparently but are not recorded by that entry-only observer.

The same bundle pairs `Skill._OnCreate` and `Ability.AssignSourceBlackboard`
to retain incoming extra/source identities and completed snapshot, dynamic
Blackboard and destination identities. The numeric inspector encloses their
observed merge/source-transfer descendants explicitly. These boundaries can
connect stack-passed extra input to a reached merge submission; they do not
enumerate source collections. Base/Patch closed-generic list fields remain
outside the admitted layout witnesses. Initialization missing-key failures,
complete collection state, helper lookup success, corrected IFix live decisions
and protocol acknowledgement retain their separate gaps.

If a future investigation requires observing Aglina's quantity branch, use the same
squad/build/talents, start recording before game launch, then make the normal
skill's final explosion and combo each affect at least two enemies while the
main character is clearly injured. Repeat with the main character full and
another teammate injured to exercise the stored fallback. Return brief notes
identifying the injured/main character and skill used; repeated ordinary
combat or HP loss alone does not establish this gate's positive coverage.

A later bundled session failed on queue-full drops, with most traffic from
the corrected Gameplay IFix helper. It remains non-admitted even where
individual matching entry/return records precede the missing sequences.
Diagnostic indications of Aglina's quantity/HP positive branch and healing
of Rossi (`chr_0028_wulfa`, user-confirmed identity) guide the next short case;
they do not admit a healthy execution record. This is not a prerequisite for
the conditional system model. Do not map that internal
name to Wulfgard or treat reported HP loss as a recorded healing source.

The v14 bundle additionally restricts named IFix observation to selected
direct caller return sites in already observed paired initialization,
comparison and healing bodies. Preparation derives each E8 target/return site
from current native bytes and retains the caller method/body proof. Activation
v2 carries the bounded filter; the runtime forwards excluded calls and the
reader rejects filtered records from any other caller. Existing activation v1
sessions keep their original policy. The diagnosis reconciles per-hook
attempted counters with recorded rows and queue drops instead of incorrectly
requiring attempted counts to equal the failed journal. This reduces the
known traffic source; only a healthy new session establishes live coverage.

A subsequent session had no dropped, unreadable or truncated records and
structurally closed every retained paired call, but the old stop procedure
still failed it. Setting the stopping flag immediately counted returning
in-flight calls as pairing failures, and disabling their detours first could
omit later descendants. A structurally closed journal cannot repair that
coverage boundary. Keep its numeric groupings diagnostic and preserve the
original failed receipt.

The corrected stop procedure seals new root observations, transparently
forwards their originals, and keeps the recorder and detours live for
descendants of already admitted synchronous roots. It drains the queue while
waiting, then disables hooks and revokes publication after those callbacks
quiesce. Admission accounting begins before reading the closing flag, closing
the start/stop race. An expired quiescence deadline still fails closed even
when a late return subsequently makes the journal structurally balanced.
Native tests exercise a closing root, a recorded nested paired call and
entry-only descendant, excluded roots on another thread, and timeout failure.
The failed session's diagnostic treatment and healthy-capture gate are unchanged.

The reviewed [healing settlement contract](../../scripts/game_data/contracts/buff_healing_settlement_native.json)
and `buff_healing_settlement_native` authenticate the selected compiled method
entries, context windows, scalar literals, field offsets and enum members.
They retain a conditional disassembly interpretation rather than claiming a
complete CFG or admitting the failed journal. On the normal compiled healing
path, the HealPack return is multiplied by one plus the sum of the healer's
HealOutputIncrease and the receiver's HealTakenIncrease. These increases add;
the pack boundary is not the final submitted amount. IFix replacements,
attribute processors and actual snapshot values remain separate selections.

The normal non-damage HP branch checks `Modifier.get_isCancelled` before
writing HP. For finite values its default predicate accepts DeltaType.Cancelled
or an absolute amount within the supplied Single epsilon; it does not inspect
cancelReason. The selected true branch returns the typed ApplyResult.Cancelled.
A positive request can instead reach SetHpInternal, whose first step clamps
the candidate between zero and maxHp. The caller rereads HP and stores the
difference from the earlier HP as realDelta. HP floor, death and early-return
policies retain their conditions; a living target with stable valid bounds and
a nonnegative increase does not select the floor reduction guard. A successful
application and a positive actual HP increment are distinct outcomes.

The selected post-readback heal callsite reaches `_OnHealed` without testing
realDelta for positivity. Its guarded event population keeps finalHealValue
from finalDelta separate from realHealValue from realDelta. An observed
`_OnHealed` entry is a reached callback, not proof that the later event guard
allowed broadcasting or that a listener received it. The failed journal has
diagnostic examples of positive requests reaching that callback with no HP
gain, while zero requests return Cancelled without reaching the HP writer or
callback. Every retained healing enclosure agrees on outer amount versus
submitted amount and on HP difference versus realDelta; this concordance does
not repair producer completeness.

The maintained stored-value reader distinguishes the moss Buff's start and
periodic expressions: OnBuffStart contains separate `value` and `triggerheal`
heals, while OnBuffTrigger uses `triggerheal`. Diagnostic assignments submit
zero for the former and a positive amount for the latter before these calls;
the saved getter returns agree. The first zero is therefore not evidence that
a common periodic formula evaluated with zero elapsed time. Neither name nor
numeric agreement binds a live action to a unique serialized node. Ether Cure
stores a current-target healer and a MaxHp multiplier keyed by `cure`, followed
by the usual outer healing formula. Its pack returns support upper-HP
candidates that explain the saved clipping/zero-gain cases, but maxHp itself
was not observed by this bundle.

Fresh BattleConst and AttributeMetaTable inputs further constrain the formula:
the default healing increases begin at zero, the Will-to-output conversion is
zero, and the Will-to-taken conversion is positive. The observed factors admit
integer floored-Will candidates using the reviewed
[attribute formula](../../scripts/game_data/contracts/attribute_formula_native.json).
This is a conditional concordance assuming no other healing modifiers, not
an independent live Will measurement or a proof of equipment contribution.
Later internal HealDetail codec snapshots agree with requested amount and
post-write HP even when actual gain is smaller or zero; they must not be used
as measurements of realHealValue, allocation lifetime or server acceptance.
Exact runtime attribution would require clean producer completion, direct
attribute/maxHp values, actual event delivery and server acknowledgement.
Those measurements are not completion criteria for the default design model.

The settlement contract's snapshot and event-routing extension separates
those obligations further. HealPack construction samples both actors; the
processor path later refreshes them through `_DumpAttributes`. Its two owned
loops call `Attributes.GetValue` and copy the returned Double unchanged into
the healer and receiver arrays at the selected attribute index. The formula
consumes the refreshed arrays. This identifies the producer and the two copy
sites, not their historical live values. The reviewed copy windows and named
callee bindings are authenticated independently; a capture must retain the
false snapshot IFix decision and the getter receiver/UID before assigning a
compiled side. Actor ownership additionally needs agreement with same-heal
actor attribute identities/UIDs. Missing getters are not zero-valued cells.

`_OnHealed` has two separate channels: OnOutputHeal on the resolved source,
then OnReceiveHeal on its own receiver. A false source-interest result still
reaches the receiver-interest check; a null resolved source exits both routes
on the reviewed compiled path. NeedTriggerEvent is an interest OR across
nonempty action queues, dispatcher key presence, combo-manager interest and
skill interest. Interest does not prove invocation of a particular listener.
The HealContext's eventSource represents the counterpart: receiver for output
healing, source for received healing. TriggerEvent sets the base eventType,
then reaches the generic dispatcher, the action container, skill notifications
and the combo manager in that order. The action container uses the selected
event queue to invoke sequences. Keep each of those stages separate from the
downstream effect and from protocol/server acceptance.

The failed journal provides a stronger diagnostic for Camille than a generic
callback entry: selected final-delta getters reach the receiver-context
population site, and the enclosing OnHealed patch check returns false. The
authenticated local continuation submits OnReceiveHeal. Its retained
synchronous descendants include action execution and creation of the named
Camille talent attack Buff even for a zero-realDelta combo heal. Stored passive
SkillData and BuffData both contain the received-healing event candidate;
that agreement does not identify which serialized root supplied a live action.
These observations establish diagnostic concordance with zero-gain talent
processing, while direct interest/dispatch parameters, generic delegate
invocation and healthy producer completeness remain separate. Do not promote
missing descendants in the failed journal to negative listener coverage.

The prepared bundle now pairs snapshot refresh, caller-filtered attribute
getters, received/output interest checks, dispatch and action-container
execution. Attribute pointers plus instance UIDs, event-owner identities,
context UIDs/types and explicit sequence descendants are retained without
invoking game getters from observer callbacks. The numeric inspector records
these intervals separately and labels snapshot sides only under its native
gate and observed false snapshot guard. This measures final snapshot
attributes, including Will and MaxHp, rather than enumerating equipment/Buff
modifier sources or proving a virtual maxHp override absent. Caller windows
include contiguous fragments only when unwind chaining proves the same
method owner; unrelated adjacent functions and gaps are excluded.

Existing records omit the separate snapshot scalars and direct interest/event
arguments. Further native reading cannot reconstruct those past values, and a
new session would measure a different execution. The default formula, refresh
timing, settlement and event routing already explain the design; no new
healing capture is required for the current architectural pass. If a later
contradiction or explicit numerical attribution task justifies sampling,
the prepared cases are injured/full Camille combo healing and an Aglina heal
with the stored two-enemy quantity gate satisfied. Use the same configured
party, the corrected stop runtime and existing preset, retaining the game
through saving; these remain optional prepared cases, not the next work item.

## What the published Gameplay datasets establish

- Every exact `chr_NNNN_token` identity in `StrIdNumTable` is published as an
  evidence-limited record, even without a `CharacterTable` row (no playable
  claim); longer skill/Buff/projectile ids are not promoted to characters.
- Referenced BuffData ids resolve into a fail-closed lifecycle/stacking/value
  catalog. Native enum names (enemy modifier, ability event, skill type,
  cooldown operation) appear only after the native gate passes, and Buff
  action chains only where typed actions consume to the next field boundary.
- GameplayTag names come from the predefined table, the serialized
  `GameplayTagConfig` CRC32 path join, an exact `tagName2Immune` context
  (`exact-context-derived`), or validated runtime capture under the same native
  gate; derived names keep their label and unmapped ids stay raw with a
  structured reason (`load_gameplay_tag_registry` in
  [`base_data.py`](../../scripts/webui/gameplay/base_data.py)).
- The Audio builder's Gameplay sound sidecar reads derived-plan records that
  reach EOF; that does not promote the Buff child corpus to a whole named
  BuffData schema. HIRC Event identity and Skill/Buff owner links are separate
  gates, and branch activation, target choice and audibility stay unresolved.

**Action-row labels** come only from the contract's own decoding: the native
`HpRatio` type and decoded operation (incl. `Floor`/`Ceil`/`RoundToInt`),
`SimpleCalcBBAction`'s decoded operation (division is not a default), and the
decoded `CompareFloat`, `SpellInfliction` and `ConvertToTargetContext` modes.
`TargetSettings` fields are readable inside a partial action, which stays
partial. Complex-entity spawn, projectile, heal-calculation and selector
execution stay unresolved; a stored field name never establishes placement,
damage arithmetic or activation.

## Selected enum audits

Each follows derived-plan references through whole records to EOF with
id/filename agreement, joins stored members to selected native field types and
enum defaults, and fails incomplete on any gap. Current values all land on
declared members; distributions and hashes stay in the local reports.

| Audit | What it names | Boundary |
| --- | --- | --- |
| `memorypack.target_settings_corpus` | `ActionTargetType`, `DirectionType`, `TargetSource` fields | co-occurrences (Context/group key, InstantSearch/finder) have counterexamples and are not constraints |
| `memorypack.effect_config_corpus` | fifteen `EffectActionCfg` enum members; reused by projectile effects after a cross-format check | replaces the older "unresolved" reading; an option such as `FollowTarget` is authored, not executed |
| `memorypack.damage_unit_corpus` | four `DamageUnit` enums, the stored `atkCalculation`/`poiseCalculation` subtype, and parameter enums of two subtypes | a subtype names the stored body, not the arithmetic that runs; no immunity bit-mask claim |

## Damage calculation routes

Each contract is selected-build, **unpatched** and normally returning, fails
closed when the native pair or a reviewed body window changes, and gives an
**intermediate** value, never final damage. Full readings are in each
validator's docstring.

| Contract (validator in `memorypack/`) | Proven intermediate |
| --- | --- |
| [`multiply_attribute_calculation_native.json`](../../scripts/game_data/contracts/multiply_attribute_calculation_native.json) (`multiply_attribute_native`) | `GetAttribute(source, attributeType) * multiplier + addition`; `valueSource` 0 attacker, 1 defender |
| [`atk_scale_calculation_native.json`](../../scripts/game_data/contracts/atk_scale_calculation_native.json) (`atk_scale_native`) | `attack * resolved(atkScale)`; attack from override element 2 or `get_atk()` when the array is null |
| [`definite_value_calculation_native.json`](../../scripts/game_data/contracts/definite_value_calculation_native.json) (`definite_value_native`) | `base`, or `base * double(scale)` when `applyScale` |
| [`breaking_attack_calculation_native.json`](../../scripts/game_data/contracts/breaking_attack_calculation_native.json) (`breaking_attack_native`) | `Double(Single(S * M) * Single(D * A))`, attacker Atk times defender breaking-attack scalar |
| [`damage_action_normal_route_native.json`](../../scripts/game_data/contracts/damage_action_normal_route_native.json) (`damage_action_route_native`) | with `takeAtkSnapshot` false: `simpleCalculation` true gives `resolved(atkScale) * attackerAttributes[2]`; false dispatches the stored `atkCalculation`. `GetAttribute` uses a supplied override array and falls back only when it is null |
| [`damage_action_poise_route_native.json`](../../scripts/game_data/contracts/damage_action_poise_route_native.json) (`damage_action_poise_route_native`) | a nonnull `poiseCalculation` is dispatched and its value copied into `PoisePackData`, independent of `simpleCalculation` |
| [`poise_result_native.json`](../../scripts/game_data/contracts/poise_result_native.json) (`poise_result_native`) | post-calculation value times attacker/defender Poise scalars, sign-flipped into `Modifier.NewPoise`, submitted through virtual slot 87 (six candidate types; `AbilitySystemForGod` fails); base path records readback `realDelta` |

- **A stored evaluator subtype does not imply its `Evaluate` body runs**:
  `simpleCalculation` is true on some character rows that store
  `AtkScaleCalculation` or `DefiniteValueCalculation`.
  [`route_audit.py`](../../scripts/webui/gameplay/route_audit.py) records the
  branch partition; the WebUI gates each badge on the caller route and the
  evaluator contract together.
- Authored Poise input, the scaled modifier candidate and readback `realDelta`
  are different quantities; target choice, accessor overrides, guards, live
  iFix state and entity attributes block any applied or displayed amount.
- The current `IFixPatchOut` dump's declared targets
  ([`ifix_patch.json`](../../scripts/game_data/contracts/ifix_patch.json))
  name none of the two callers, four evaluators or their providers -- a
  statement about declared targets only ([`ifix_patch.md`](ifix_patch.md)).
- The independent [snapshot consumer claims](../../scripts/game_data/contracts/damage_snapshot_consumers_native.json), checked by `damage_snapshot_consumer_native`, re-prove named body-wide accesses without pinning a build. `_TakeDamageCalculationSnapshot` contains owner and action-target resolution, Blackboard scalar lookup and the AbilitySystem attack getter; it reads `m_calcResultCache` and writes `m_cachedAttacker`. The normal-entity calculation reads the same named cache and contains a List item getter. These are `direct` access/call claims, not a producer-to-consumer value-flow proof. This inventory alone does not prove the getter receiver or scalar return flow; the separate bounded consumer proof below addresses that path. List production/index correspondence, complete snapshot arithmetic and live branch choice remain `unresolved`. The audit refuses all rows on native-input, proof-source or claim drift, and records no live or final damage observation.
- The independent [snapshot cache-flow checker](../../scripts/game_data/damage_snapshot_cache_flow.py) additionally proves one bounded consumer path from entry to return. On the installed build it checks the inline patch-table guard ([`il2cpp/patch_table_guard.py`](../../scripts/game_data/il2cpp/patch_table_guard.py); selection = null table or null slot, anonymous runtime state, **conditional**), nonnull DamageUnit, nonzero `takeAtkSnapshot` branch, and nonnull cache edge from machine bytes. Incoming `this` supplies `m_calcResultCache`; the incoming Int32 `index` is loaded from its entry-relative stack slot into the getter argument. The static MethodSpec and registered entry identify `List<Double>.get_Item`. Its normally returned XMM0 bits pass through a full vector copy and MOVQ into RAX, followed by a completely checked restoring epilogue. The selected `CalcResult` is a value type with only one instance Double field and its authenticated eight-byte unboxed extent. Thus this path returns the selected cached Double unchanged; it does not establish how that cache was produced. All selected instruction encodings, continuations and branch targets are checked independently of the broad inventories above. Valid unchanged live receiver/frame, resolved matching MethodInfo and normal Win64 getter return remain conditions; the getter's internals and actual invocation are not proved. Native skips retain the previous audit file and print the current missing/mismatched diagnostic; claim drift returns `pendingReview` with no rows and publishes independent diagnostics while preserving the last validated main report. Only validated results replace that report; an older receipt is not current proof when its native/source freshness gates fail.
- The separate [simple snapshot append-transfer checker](../../scripts/game_data/damage_snapshot_append_flow.py) proves the producer's bounded request fragment, conditional on its incoming action, typed DamageUnit, selected AbilitySystem source and retained zero comparison byte. The checked nonzero `simpleCalculation` fallthrough loads that unit's `atkScale`, passes it with the action's returned Blackboard to the named Single provider, and preserves the Single result across the named Double attack getter. It widens the scale to Double and multiplies it by that getter result, then sends the product in XMM1 and the same action's `m_calcResultCache` in RCX to the physical compiled helper. R8 carries an independently resolved static `List<Double>.Add` MethodSpec; its sole ordinary type parameter is proved to belong to that List generic owner. Every selected instruction encoding, guard edge and continuation is checked, with complete register copies and normal Win64 preservation. The compiled call target differs from the registered Add entry on the selected build; those identities remain separate. No helper-internal list mutation or append order is claimed, and the producer request does not yet join the consumer's incoming index to a particular cache element. Enclosing producer guards, register-entry roles, live MethodInfo and provider behavior/values remain conditions.
- The actual compiled target now has an independent [raw fast-path store proof](../../scripts/game_data/damage_snapshot_append_helper.py). It uses the exact `.pdata` entry and owned extent rather than a neighbouring-code estimate, and checks the complete selected entry-to-RET instruction program. The previously proved cache receiver and XMM1 request reach this same physical target. Its nonnull and unsigned-capacity fallthrough increments an anonymous DWORD, writes the old count plus one into a second DWORD, and stores the incoming Double bits in the array carrier at the sign-extended old count times the Double width. The address uses the old count, not the newly stored count; two unsigned length guards and the full restoring epilogue are checked. This is a `conditional` physical write into `structuralOnly` anonymous slots, not a named generic List/managed-array layout proof. Valid unchanged receiver, frame and array, a nonnegative Int32 array length and no concurrent mutation remain conditions. The capacity/resizing and failure routes stay excluded, registered Add identity remains separate, and the consumer's incoming index is still not joined to this producer's old count.
- The independently checked [physical cache getter](../../scripts/game_data/damage_snapshot_getter_flow.py) now covers the actual caller target's complete selected return path inside its exact `.pdata` extent. It checks unsigned receiver-count and array-length bounds, excludes the null/throw routes, sign-extends the incoming Int32 index and loads exactly a Double-width element into XMM0 before a complete stack epilogue. The getter and actual compiled writer use the same reviewed anonymous carrier/payload slots; the caller-target equality is proved from the native call bytes, not from a shared method name. There is consequently a precise conditional element relation: with the same cache receiver and array, consumer index equal to the writer's old count, valid nonnegative Int32 bounds and no intervening/concurrent change, the getter reads the same eight-byte address the writer stored and the consumer returns those bits. The checked old-count range also prevents the increment from overflowing Int32. This supplies neither observed index equality nor whole producer order. Managed layout/runtime class parity remain conditions, and excluded throw/failure paths are not promoted to normal returns.
- The [producer entry reset checker](../../scripts/game_data/damage_snapshot_clear_flow.py) separately proves incoming-this ownership of an early cache reset. It checks the false IFix entry guard and the nonnull opaque selection carrier/owner, then requires the selected target getter's return to be an ordinary AbilitySystem reference. A nonnull target and cache reach the anonymous counter increment and four-byte count zero. That zero comes from a complete R13D XOR before the target call and normal Win64 preservation, rather than from an assumed default value. A null target instead reaches a completely checked restoring RET without the cache stores. Generic selection/handle loads stay opaque, and valid live action/frame/carriers, normal providers and callee memory noninterference remain conditions. The reset uses the same reviewed raw count slot as the compiled writer/getter, but it does not name a generic List Clear operation or prove the complete producer loop/order.
- The [OnCreate transfer checker](../../scripts/game_data/damage_snapshot_oncreate_flow.py) independently links a lifecycle definition to that snapshot entry. On the checked false IFix branch, it retains the incoming action in nonvolatile RBX, restores the same pointer into snapshot RCX and fully restores its own stack before the physical tail jump. Both selected concrete methods have checked instance, void, no-argument ABIs, and the tail target equals the previously proved producer entry. This is a precise `direct` receiver/control transfer, not evidence that OnCreate was invoked, that a live action/class was selected, or that a snapshot/final damage occurred. Normal Win64 guard return and default patch selection remain conditions.
- The [constructor pointer-transfer checker](../../scripts/game_data/damage_snapshot_constructor_flow.py) covers the concrete constructor's complete selected allocation/store path. Tagged ClassInfo requests and instance-void constructor MethodSpecs agree with the declared destination reference types, including the closed Double cache. The full allocator-returned RAX bits are saved in nonvolatile RDI, passed as the constructor receiver and retained across its normal Win64 return, then stored into the same incoming action's cache field. The final transfer supplies the field address to a distinct physical slot helper after restoring the caller frame. The selected List constructor callee body is folded with LowLevelList aliases; its selected context and all physical aliases remain recorded separately. This proves the pre-helper pointer store and static requests, not allocator or folded constructor behavior, initialized live ClassInfo/MethodInfo, final slot-helper effect or heap-class parity. A later clear/store/getter fact is not used to assume those initialization semantics.
- The [slot helper checker](../../scripts/game_data/damage_snapshot_slot_helper.py) proves only the constructor's actual bounded entry graph, independently of function ownership. Its zero gate reaches the checked RET; the other path derives one anonymous word address from input-slot bits and a RIP base, then a complete BTS/LOCK CMPXCHG retry graph returns. Every reachable instruction, edge, RET and write width is checked. The RIP base does not establish a table allocation or extent. If the actual derived write range is disjoint from the input field slot, storage is valid/nonwrapping, return is normal and there is no interference, the pre-tail pointer bits are preserved. The helper has no explicit local frame or stack-pointer adjustment, but RET consumes its return address; the derived word may alias valid stack storage, so caller frame or return-slot preservation is not asserted.
- The [private ordinary ABI gate](../../scripts/game_data/damage_snapshot_abi.py) authenticates raw selected type records separately from their printed names. IFix Bool/Int32, provider Single/Double, consumer index, generic formal/closed Double arguments, concrete value return and constructor reference destinations must have compatible ordinary kind/flag records. Same-name byref, pinned/modifier or incompatible-kind records refuse the claim. This strengthens the existing conditional register transfers; it does not resolve provider values, allocator/constructor semantics, live class parity or final damage. Tool implementation exceptions carry a distinct toolingFailure stage/check/source diagnostic; the CLI preserves the published report and writes separate diagnostics, so an implementation fault is not classified as native claim drift.
- The [snapshot skip checker](../../scripts/game_data/damage_snapshot_skip_flow.py) connects the named snapshot-flag branch to the fresh simple-append fragment and its continuation. Zero flag reaches the shared iteration increment without any call or explicit memory store, then a signed comparison either branches to an earlier complete instruction boundary or reaches the same fully checked producer RET. Nonzero flag reaches the fresh append-fragment entry, and its continuation joins that same increment. The raw increment is Int32 and zero-extends its destination; the decoded register label alone is not accepted as its width. This proves the local skip/append control join only. Unit/counter/bound register roles, valid frame, zero comparison register and live selection remain conditions; counter initialization, loop header, non-simple branch, overflow-free ordinal interpretation and actual consumer-index correspondence remain open. A skipped unit cannot be assumed to occupy an append position.
- The [counter initialization checker](../../scripts/game_data/damage_snapshot_counter_flow.py) extends the fresh reset zero through a complete selected fallthrough into the first counter assignment. It checks the ordinary Bool/Int32 IFix call and its false branch, nonnull opaque root and null inner-reference selection, every intervening instruction and absence of R13 writes. Under normal Win64 nonvolatile preservation and valid/noninterfering frame/carriers, that same zero produces the local flag and the Int32 ESI initial value. Other branch selections and the meaning of opaque pointer/payload loads stay open; this does not prove the subsequent count source or full loop. Count-provider naming or loop proximity alone is insufficient to certify collection ownership or cached-result index correspondence.
- The [count request/null-path checker](../../scripts/game_data/damage_snapshot_count_flow.py) authenticates a static SafeCount method request with an ordinary Int32 result, ordinary IList generic-reference formal, reciprocal method-MVAR owner and selected DamageUnit reference argument. The producer supplies an opaque child pointer and the request in their actual ABI registers. Separately, the actual physical helper's nonzero anonymous context-slot/null-collection path reaches a complete owned restoring RET fragment and explicitly returns EAX zero. The caller preserves this result into its bound register and its checked signed branch reaches the previously proved producer RET. Exact first-prefix and return-fragment ownership do not certify a whole helper function; physical and registered request identities stay separately recorded. Valid initialized runtime context, matching live generic ABI, frame/storage and noninterference remain conditions. Nonnull count semantics, collection ownership/layout, full loop and actual consumer-index correspondence remain unresolved.
- The [indexed unit-pointer checker](../../scripts/game_data/damage_snapshot_unit_flow.py) connects the exact loop target from the flag/append graph to the same flag instruction. Fresh count-request proof supplies the anonymous action-root/child read operands; nonnull carrier and array plus two unsigned Int32 bounds precede sign extension of the iteration register and a full eight-byte element load into RBX. The pointer is tested nonnull before the named snapshot-flag offset is read. The static count method's selected reference argument must match that field owner, but runtime object parity is still conditional. With nonnegative Int32 bounds and valid nonwrapping storage, the raw address equation is array base plus payload plus index times pointer width. This selected path makes no calls or stores. The slots remain anonymous: matching displacement patterns do not identify List fields, managed arrays or actual DamageUnit instances, and unchanged root/child continuity requires no intervening mutation. Nonnull count behavior, full-loop ordering, compact cache positions and actual consumer-index correspondence remain open.
- The [iteration connection checker](../../scripts/game_data/damage_snapshot_iteration_flow.py) joins the fresh zero assignment to the fresh count request through an exact interval without counter writes, then requires the positive signed result fallthrough to equal the fresh unit-read entry. The independently checked skip and simple-append continuations join the same Int32 increment and signed backedge. Under a positive Int32 bound, normal Win64 preservation of the nonvolatile counter/bound registers, valid noninterfering storage/frame and every selected unit guard/skip/simple path, this conditional graph visits counter values from zero to bound-minus-one without overflow. Any excluded branch invalidates that model. It does not prove all producer branches, nonnull count behavior, raw cache position equality, actual consumer-index correspondence or live/final output.
- The [compact-cache checker](../../scripts/game_data/damage_snapshot_compact_flow.py) composes the fresh reset, selected skip/iteration and actual physical writer proofs as a `conditional` recurrence. Starting from zero, a skip increases only the iteration counter; a selected simple snapshot append increases the anonymous cache count and uses its old value as the raw payload index. This requires the same unchanged action/cache/array identities, matching live ABI/class, normal selected calls/fast paths and explicit memory noninterference. In particular, the actual payload write must be disjoint from count storage, helper writes must preserve the carrier array reference and action cache slot, and other local/interim/provider/external stores must preserve those values. Under these conditions, cache count equals the number of selected appends, so an earlier skip makes a later append index smaller than the iteration counter. The utility checks actual caller-supplied ranges but observes no live ranges or values; this is not a runtime index join, managed List semantics or evidence that the consumer receives the compact index. Physical and registered Add remain separate.
- The [ByType forwarding checker](../../scripts/game_data/damage_snapshot_forward_flow.py) connects the upstream named ordinary Int32 index and unit reference to the existing normal consumer's exact ABI slots. It checks stack arithmetic, full receiver/target/attacker register chains and the normally returned low-bit result transfers through a complete restoring RET. Three adjacent owned fragments cover this selected path; other branches and whole-function ownership are excluded. Selection requires the unpatched inline patch-table guard (same conditional boundary), nonzero anonymous RIP-carrier words and normally returned AL zero from two unnamed actual targets. Those byte predicates do not prove Bool or target-classification semantics. The separately checked Bool reference-proxy byte store requires actual storage disjoint from incoming/outgoing index, unit, return and saved-register ranges, with normal Win64 frame/storage/provider noninterference. The checker observes neither live disjointness nor index values, and does not show that an upstream caller chose a compact cache index or that the normal callee selected its cache branch.
- Installed-build status: the cache-return and ByType-forward checkers are re-proved through the patch-table guard; ~15 other snapshot/formula stages of `damage_snapshot_consumer_native` still expect the retired direct `IsPatched` call and return `pendingReview` until migrated to the same recognizer. Open join: `_ProcessDamage` unit loop → ByType request. A complete Process sweep ([`il2cpp/register_shift_instructions.py`](../../scripts/game_data/il2cpp/register_shift_instructions.py), zero unknown rows) and an offline writer survey indicate the ByType Int32 index is the loop counter that selects the ByType unit from `m_data.damageUnits`, and `this`/`hitEnvCalcResult` are Process's own; not yet a maintained claim (needs a closed-CFG writer census; the `[rsp+0x80]` object escapes to callees below the counter/unit slots, so the result stays **conditional**).
- The snapshot audit CLI protects both its main report and separate tool-failure diagnostics against aliases of every native input and provenance proof source, including the reviewed contract and helpers. Final same-file/root checks and atomic replacement preserve source bytes and the previous report on rejected aliases. Missing/mismatched input skips preserve the published report; unexpected tool failures keep a distinct named-stage diagnostic rather than becoming native claim drift.
- `snapshotActualProcessProbeRaxAndConditionalFrame` checks the actual compiled probe complete owned body, every edge/page-write loop and restoring RET, the true GS prefix and low-word 16-bit alignment, and absence of any RAX destination. A separate raw Process entry proof establishes zero-extended immediate allocation, the actual helper CALL and full64 SUB RSP,RAX. Preserved allocation therefore uses actual helper bytes rather than volatile ABI assumptions. Anonymous GS storage has no inferred thread/allocation meaning. Finite loop, valid storage and each derived byte write disjoint from saved locals/return storage remain conditions; no later Process frame continuity, local-index writers or snapshot compact-index equality follows.

- `snapshotProcessLocalIndexNormalRequestAndTemporary` independently partitions one raw local fragment: an anonymous current-SP Int32 slot reaches the actual normal-consumer index ABI slot, complete reference-bit transfers reach its parameter slots, and normally returned low64 RAX bits move through MOVQ/MOVAPS into a temporary before the outside continuation. This fragment calls the fresh normal consumer directly. Ordinary Int32/class/value-return ABI and explicit unpinned Bool/value ref proxies are separate gates; same-name byvalue, pinned or incompatible kinds fail closed. The unnamed predicate only selects normal AL zero. Valid local/outgoing/pointed storage, concrete range disjointness, normal Win64 returns and frame/storage noninterference remain conditions; the range utility proves only supplied addresses/widths, not live storage or initialization. Whole Process entry-to-fragment CFG/SP continuity, local initialization/all writers and producer compact-index correspondence remain unresolved.

- `snapshotProcessLocalIncrementGuardAndProviderRequest` checks separate raw local load32/INC32/store32/direct-JMP fragments, their identical actual guard target, the complete signed Int32 comparison/nonnegative-independent JGE selection, anonymous nonnull receiver guards and index32 request in EDX. Their local displacement matches the fresh normal-request source, conditional on unchanged current-SP/frame and noninterfering storage. Increment is modulo 32 bits; a signed nonoverflow recurrence additionally requires the actual old signed value below INT32_MAX. Negative values are not excluded by assumption. The anonymous bound and provider have no inferred count/getter semantics. Immediately after normal provider return, full RAX overwrites R13; the pre-call R13D index origin ends there. No whole Process loop/initialization/all-writer claim, provider return reference identity, continuous frame or snapshot compact-index correspondence is established.

- `snapshotProcessActualProviderEightByteNormalReturn` connects the fresh Process provider request to its actual compiled target and completely partitions that owned body. Selected unsigned anonymous count/array bounds and nonnull array guards lead to sign-extended Int32 index addressing, one eight-byte payload read into full RAX, local SP restoration and RET; fresh caller bytes then overwrite R13 with those returned bits. Every excluded guard targets a checked owned CALL/INT3 branch whose normal return/throw semantics remain unproved. Registration names are provenance only: the folded reference getter does not establish closed Unit/runtime-class identity. Unsigned guards alone do not establish nonnegative signed index or managed array layout. The concrete address utility retains signed negative inputs and separately checks nonwrapping eight-byte ranges. Valid anonymous receiver/context, read/local/return storage and noninterference remain conditions; no live Unit identity, provider generic semantics, full Process frame continuity or compact-cache-index equality follows.

- `snapshotProcessStaticClosedUnitGetterRequest` authenticates the fresh caller static RIP-loaded R8 usage as an instance closed `List<DamageUnit>.get_Item` MethodSpec request: ordinary Int32 parameter, reciprocal ordinary type VAR return owner/ordinal, ordinary Unit class argument and absent method instantiation are checked separately. Registered requested entries and the independently proved physical target stay distinct; absence of a matching requested entry does not identify the folded physical Object getter as a closed Unit implementation. Initialized/live-resolved compatible generic context, receiver/array layout, returned bits representing an actual Unit reference and runtime ABI parity remain conditions or unresolved. The typed request descriptor does not upgrade anonymous physical read semantics or prove Process frame/compact-index correspondence.

- `snapshotProcessCountResultToSignedBound` independently checks the selected nonnull anonymous-root typed count request and normally returned EAX four-byte store into the fresh Process guard bound displacement. It reuses the typed SafeCount request gate and authenticates the same actual physical count-helper target as the earlier independent null-helper proof; registered identity remains separate. Selected compatible context/null collection normal return supplies zero to the bound store. Reaching the guard with that value additionally requires unchanged current-SP/frame/local storage and no interference. The actual signed Int32 JGE excludes only when current signed index is at least signed bound; a zero bound alone does not exclude negative index. No nonnegative initialization, nonnull count semantics, all bound/index writers, whole Process CFG or snapshot compact-index equality follows.

- `snapshotProcessProviderBitsToUnitTemporaryAndReload` checks the actual provider normally returned full RAX bits, their immediate R13 transfer and adjacent exact eight-byte anonymous local store. A separate complete group-exit fragment increments EBX modulo 32 bits, compares signed EBX/R15D, reloads the same displacement into full RSI and excludes its actual signed-less-than backedge. Same current-SP/storage, no intervening local write, selected fallthrough and preservation of reloaded RSI/frame to the independently entered normal request are explicit conditions for the carrier bits to reach R9. Intervening getter writes to RSI are not ignored or assigned the old origin. EBX/R15D roles are not promoted to damage/snapshot indices, carrier bits are not promoted to live Unit identity, and whole Process CFG/frame continuity/all local writers/lifetime/layout/compact-index joins remain unresolved.

- `snapshotProcessBoolProxyZeroToCompleteFalseReturn` checks the fresh normal temporary continuation, full XMM temporary copy and one-byte comparison of the same explicit Bool proxy local. Selected zero reaches actual XOR AL,AL and an exact direct jump to the complete raw epilogue: XMM save loads, frame-base SP transfer, every GPR pop and RET. Ordinary Process Bool return is independently gated, and no epilogue instruction writes AL/RAX; only AL zero is established, not upper RAX zero. The epilogue frame advance matches the independent actual entry allocation request, but this arithmetic equality does not prove continuous frame or original saved bits. Valid aligned save/pop/return storage with appropriate saved bits, normal request/path selection and no intervening out-local/frame interference remain conditions. Nonzero proxy branch, provider Bool-write semantics, full Process execution, final damage and cache compact-index correspondence remain excluded or unresolved.

- `snapshotNormalSimpleFloatScaleTimesDoubleCarrierToResult` checks a complete selected false-IFix, nonnull Unit, zero snapshot-byte and nonzero simple-byte normal-consumer path through its common restoring RET. Ordinary Unit input/CalcResult return, explicit value-type pack ref, selected value owner and reviewed boxed-to-unboxed field adjustment, named pack Float scale/Double[] attributes fields, ordinary array/Double element ABI and metadata ancestry to the Blackboard receiver are independently gated. The actual ordinary Float getter result is stored in the pack scale field and widened by CVTSS2SD, then multiplied by a low64 anonymous attributes carrier read using MULSD; exact bit transfers reach the same CalcResult return entry as the independent cache path. Every array/static/debug guard and excluded target remains explicit. The anonymous slot has no inferred attribute-enum identity; Double[] runtime heap layout, initialized providers/receivers/static/frame storage, compatible live classes, normal Win64 returns and noninterference remain conditions. Actual floating MXCSR rounding/DAZ/exception state and live provider values are unobserved, so the checked operation sequence is not promoted to final damage, a full formula-provider semantic model or cache compact-index equality.

- `snapshotProcessAnonymousPackBytesCopyToNormalArgument` checks a complete owned Process fragment of paired MOVUPS loads/stores, both source/destination base adjustments and the middle negative displacement store. Every selected unboxed value-size byte is covered exactly once, with the selected native size row and reviewed boxed-header adjustment authenticated separately. Destination displacement matches the fresh normal explicit pack-ref argument, and the independently typed attributes-pointer view fits wholly in a copied segment. Valid nonwrapping disjoint source/destination storage, same current-SP/frame and no interference establish only corresponding byte equality immediately after the copy. Source buffer type/initialization/reference and array contents, later preservation, actual class/layout parity and source producer semantics remain conditional or unresolved; this relation does not assign an attribute enum/element index, prove whole Process CFG/all writers or establish final damage.

- `damage_snapshot_multiply_formula_flow.py` authenticates an independent selected MultiplyAttributeCalculation affine formula. Ordinary typed multiplier/addition providers return Float; actual low values are widened, the multiplier is multiplied by the ordinary Double attribute provider result, and converted addition is the destination of the final addition before low result bits enter the independently authenticated sole-Double CalcResult return. Actual branch-linked physical pdata ranges, selected branches, direct calls, register origins and restoring return are checked. The nonzero anonymous initialization byte, false patch result, selected stored Int32 source bits, null server argument, compatible live objects/frame, normal provider returns and floating environment remain conditions; provider internals and actual damage invocation are open.
- This checker separately authenticates the selected cold-entry defender bridge: nonzero stored Int32 source bits replace the saved attacker carrier with the ordinary incoming defender and replace the override argument with the named Double-array defender override, then jump exactly to the fresh common attribute request. The selected prefix is complete; same managed unwind family is not inferred from adjacency, and the remaining cold body and enum member names are unproved. No runtime subtype-selection join follows from these independent formula paths.
- `damage_snapshot_poise_copy_flow.py` authenticates an independent conditional Poise raw-bit transfer after an opaque dispatch call. Normal RAX low bits enter XMM6, a selected anonymous class guard skips initialization, and an opaque debug call normally returning low AL zero selects the copy. Neither call has a proved managed signature, so neither typed CalcResult return nor Bool debug semantics is claimed. The named PoisePackData result field independently joins the same concrete ordinary value definition as the fresh sole-Double consumer result, and the native boxed size and field offset are authenticated. The complete raw copy is exact; deriving the unboxed span and low-half typed field view remains conditional on the reviewed header/storage-layout assumption, with no independent boxed-to-unboxed bridge proved.
- The Poise result update physically writes a full vector chunk: an immediate original chunk load supplies the high half, register-to-register scalar move replaces only the low half, then vector stores write the original pack and its new copy. The rest of the pack is transferred through complete paired vector moves and a scalar tail. Valid aligned nonwrapping disjoint storage, compatible live layout, current-frame continuity, normal opaque returns and register/storage noninterference remain conditions; earlier typed pack initialization, dispatch internals, whole Process control flow and final Poise output remain open. Candidate selection requires the unique complete postdispatch-and-copy grammar, not a repeated prefix or proximity.
- `damage_snapshot_poise_constructor_flow.py` independently authenticates the selected caller-side Poise construction request. A false ordinary patch result selects complete zero stores over the raw pack-copy span, followed by an actual named instance constructor call with independently checked ordinary actor-reference, signed Int64 enum-mask and environment-reference ABI. Caller outgoing stack storage is related to callee entry storage through the normal return-address push. The live argument values, constructor receiver compatibility and typed span interpretation under the reviewed header/storage-layout assumption remain conditions.
- Normal constructor return is followed by complete vector/scalar reloads, a direct branch to the exact publication entry, and complete stores over the same span at the fresh later Poise-copy source. This proves a conditional caller transfer of the constructor-produced bytes, while constructor internals, survival of pre-call zeros, validity/noninterference of caller frame/storage and subsequent modifier effects remain open. The later Poise-result update cannot inherit unchanged initialized values across the intervening modifier call without an additional preservation proof.
- `damage_snapshot_poise_attribute_flow.py` separately authenticates a local Poise attribute-element producer: under the compatible AbilitySystem carrier condition, the ordinary declared Attributes field supplies the actual instance GetValue receiver and the Int32 enum request. Normally returned Double bits reach an eight-byte anonymous-array store indexed by the signextended old Int32 carrier. The counter increments after forming the old address index, and the actual direct backedge is checked. Carrier origin, array layout/storage and surrounding control flow remain conditional or unresolved; no concrete attribute member or snapshot-consumer index correspondence is inferred.
- The same domain separately checks zero-index initialization, complete NOP framing, the anonymous class selection and actual signed-bound guard at that fresh backedge. Stable nonnegative signed bound, valid storage, unproved guard-to-store control flow and carrier preservation are explicit finite-recurrence conditions. Physical pdata coverage proves byte ownership by actual ranges without promoting adjacent ranges to one managed unwind family.
- `damage_snapshot_attribute_cached_flow.py` independently checks one selected cache-read and complete restoring return inside that actual ordinary Double provider. A full-width masked shift and the actual TEST/SETA/AL selection precede anonymous-array null and unsigned-count guards; the selected eight-byte load reaches XMM0 unchanged. Current receiver/index origins, valid array and saved-frame storage remain conditions. Nested cache/header meaning, entry-to-fragment control flow, other provider paths and flag semantics are open; this local result does not establish every GetValue invocation returns cached data.
- Consumer audit publication now replaces its main report only for validated results. Every other result preserves the main bytes and writes a separately guarded atomic diagnostics companion; pending-review claim or proof-source drift still refuses all current rows. Main and companion outputs reject native/proof-source aliases, and the companion also rejects aliases of the prior main. Consumers must continue checking receipt freshness rather than treating preserved historical validation as current proof.
- The Poise attribute domain additionally authenticates the complete selected guard-to-store bridge. Its anonymous value-carrier slot supplies RSI, and every actor/null/class/signed-limit excluded branch is checked. The bridge contains no call or index/actor-carrier write, so it joins the independent signed-bound fallthrough to the typed attribute request and old-index Double store; the direct backedge returns to that same guard. This closes one conditional selected-cycle control-flow relation, while stable signed bound and class selection, original receiver/actor origins, compatible storage/layout, normal provider preservation and actual live cycle selection remain conditions. Nested typed header/array semantics and snapshot-consumer index correspondence stay open.
- The Attributes cache domain additionally authenticates one complete selected native entry-to-return path. The actual incoming receiver and signed Int32 enum bits are transferred to the registers used by the independently checked cache read, through every opaque class/null/signed-limit branch and exact fallthrough. All excluded targets are outside the entire selected path, not just an individual fragment. This path makes no call, and each actual nonvolatile GPR save plus the full XMM6 save is matched to the later reload; stack allocation and pushed RSI are reversed before RET reads and pops the entry return address. Valid current frame/shadow storage, compatible receiver and anonymous array/layout backing, selected raw predicates and noninterference remain conditions. This proves actual saved-state preservation on this selected provider path rather than relying solely on an ordinary calling-convention assumption; other GetValue paths, live selection and nested typed header/flag meanings remain unresolved.
- A fresh complete cached-provider entry/return witness now joins the independent caller request/store witness: the old caller Int32 index bits reach the actual provider's signed source index, actual saved RDI restores those bits, and the same old index addresses the destination before its increment. The source eight-byte load reaches XMM0 and the actual eight-byte destination store without numeric conversion. This is conditional on the selected normal cached path, compatible current carriers, valid nonwrapping heap/frame storage and noninterference; it observes no live index, cache value, nested header/array meaning or final Poise result. The source value is the value read during that selected call, not an assumed pre-call initialized cache. The domain-private copy-flow checker rejects a different actual target, incomplete saved-state return and narrower store even when names match.
- The actual attribute-provider cache publication now has an independent complete selected raw slice: it reloads the anonymous array pointer, physically writes sixteen receiver-header bytes, selects nonnull/unsigned-count guards, writes entry XMM6 low64 to the eight-byte indexed array location, transfers the same bits to XMM0 and jumps to the previously authenticated complete restoring footer. No call occurs in that slice. Entry receiver/index/value origins and earlier CFG remain conditional; neither the anonymous header write nor its flags are given semantic names. Its array address expression matches the selected cached-read expression only with the same receiver, unchanged array pointer and signed index, valid backing and no interference from header/array writes. This closes a local raw publication/return relation while value generation, nested type/header interpretation and live result remain open.
- A separate complete direct-call/caller bridge supplies the cache publication's value carrier: conditional on the actual opaque callee's normal return and preserved caller carriers/frame, low64 XMM0 is captured in XMM6 and remains unchanged through the selected raw guards into the existing eight-byte store and normal return. The exact register BTR is a full-width operation after masking its register bit index to six bits; it clears one bit of the loaded anonymous first qword, while a separately loaded second qword forms the remaining half of the sixteen-byte anonymous header copy. This proves bit transfer and raw header preparation, without interpreting the opaque callee's return type or computation, assigning flag meanings, or proving earlier entry/carrier origins, other paths or live results. Temporary, header and array writes require valid storage and noninterference.
- The other actual signed-index edge has its own complete raw proof: it spills the unchanged first anonymous qword, loads the second, clears a masked bit with BTR64 and jumps exactly to the authenticated second-qword spill/reload and common header/array-store/return tail. XMM6 remains untouched across that edge. The preceding signed comparison selects indices at least sixty-four; it does not establish an upper bound of one hundred twenty-eight, and larger indices still use the masked low-six bit index. The later unsigned array-count guard and actual nonwrapping storage conditions remain necessary. These first/second-word names describe physical qword positions and do not assign typed flag semantics.
- The cached-read provider's other actual signed-index edge independently selects a complete TEST64 of the second anonymous qword and jumps to the authenticated SETA, guarded eight-byte array read and complete restoring return. The same fresh entry-to-parameter/receiver transfers and saved-state restoration apply conditionally across that explicit edge. TEST clears carry, so the existing selected AL-zero predicate remains a raw tested-bit relation. Indices at least sixty-four are not thereby bounded below one hundred twenty-eight; semantic flag labels, nested cache layout, actual values and live selection remain open.
- The Poise indexed destination carrier now has an independent local production relation: an actual opaque direct-call request receives an anonymous RIP qword and dword arguments; its normally returned full64 RAX is physically published into the same anonymous R15 slot later read into RSI by the authenticated selected loop bridge. A second actual opaque call follows that publication before the direct continuation into zero-index initialization and the selected guard/bridge. Both calls must normally preserve the compatible value carrier/frame, and the post-store call plus temporary writes must preserve the published slot until the read. This supplies conditional pointer-bit provenance without calling the first helper an array allocator, the second a write barrier, or interpreting typeinfo, declared array/nested layout, original receiver origin or live backing.
- The actual named Poise constructor entry has its own complete byte proof for frame setup and incoming carriers: this is copied to R15, attacker to RBP, defender to R14 and the full-width mask to RBX, after exact saves, three pushes and local allocation. The readable anonymous byte nonzero path has no call and excludes initialization; MOV copies preserve that byte comparison's flags. The fresh ordinary named request anchors these argument labels. Its fifth-argument ABI entry slot plus actual frame delta derives a conditional current-stack address only; the entry fragment does not read the environment. Later R15/carrier preservation and complete CFG to pointer publication or loop remain separate gaps, as do constructor return, typed header interpretation and live values.
- Complete selected setup bytes now connect the constructor entry through raw out-at-return carrier copies, environment/mask stores, low64 zero and actual pointer publication into the first guarded attribute request/store. This closes one conditional first-iteration caller CFG: every opaque call must normally preserve the nonvolatile carriers/frame, all relevant temporary/receiver/root writes must be noninterfering, and the signed bound must select the initial zero-index iteration. The out helpers are not assumed to initialize their sixteen-byte buffers. The setup and guard load the same actual anonymous root storage and static-carrier displacement, so the publication call's DWORD argument and later signed bound read share a derived source address under unchanged current root/class/static/count backing. This does not prove the returned object's length or allocator behavior. Incoming this/actor/mask continuity is conditional across the complete selected caller path; typed header/fields, whole constructor return, other paths and live values remain open.
- The first selected Poise loop's signed exit now connects to a second opaque pointer request/publication and complete signed EBX guard. The defender lane independently reads compatible incoming defender AbilitySystem attributes, calls the same ordinary Double/Int32-enum provider and writes unchanged return bits to the second anonymous pointer's old-index eight-byte location before modulo32 counter advancement. Its complete bridge uses literal zero for class comparison because EBX now holds the second counter. Stable nonnegative signed bound, initial zero and normal noninterfering callee/storage behavior give a conditional selected recurrence; opaque allocation/post-store meaning, returned-object length/type and header/layout remain open. Physical ranges are authenticated through actual branch links without inferring managed unwind ownership.
- The second guard's actual signed exit and store fallthrough select a complete constructor void-return footer. Its exact RSI/RBX/RBP reload slots join the original first RSI spill and entry saves; allocation and the three matching pushes are reversed before RET reads and pops the original entry return address. Original RSI preservation before its spill, unchanged frame/save/return storage and prior normal callee preservation remain conditions. This closes selected frame restoration, not all constructor paths or live output.
The selected numerical consumers below preserve machine precision and operand order. `F(field, bb)` denotes the ordinary Single blackboard getter; `D(field, bb)` the ordinary Double getter; `A(actor, enum, overrides)` the ordinary Double attribute getter; `Atk(actor)` the ordinary Double attack getter. `w64` widens a Single low lane to Double, `r32` rounds a Double to Single, and `mul32`, `mul64`, `add64` retain the actual instruction precision and operand order. All results refer to the authenticated concrete `CalcResult` low half. No provider implementation or live value follows from these symbols.

| Consumer and reusable checker | Selected guards and operand sources | Ordered result |
| --- | --- | --- |
| [`NormalAttackPoiseCalculation`](../../scripts/game_data/damage_snapshot_normal_attack_poise_flow.py) | False patch; typed `atkScale`; actual image Single operand `c`. | `w64(mul32(F(this.atkScale, bb), c))` |
| [`DefiniteValueCalculation`](../../scripts/game_data/damage_snapshot_definite_value_flow.py) | False patch, nonzero `applyScale`, null server; `v = D(this.value, bb)`, `t = F(this.valueScale, bb)`. | `mul64(v, w64(t))` |
| [`PrimaryAttrCalculation` local consumer](../../scripts/game_data/damage_snapshot_primary_attr_flow.py) | Compatible named attribute-call inputs/this/blackboard/frame at fragment entry; nonzero `applyScale`, null server; normal attribute Double `a`, `t = F(this.valueScale, bb)`. | `w64(mul32(r32(a), t))`; actual widening is packed `CVTPS2PD`, with only its low lane returned. |
| [`PrimaryAttrCalculation` selector](../../scripts/game_data/damage_snapshot_primary_selector_flow.py) | Nonzero readiness byte, false patch; typed selector differs from both freshly selected native `Main` and `Sub` IDs. Selected actor, nullable fields, providers and server argument are not read on this caller path. | Positive-zero Double low64 via `XORPS XMM0` then `MOVQ RAX`, through a complete selected entry/frame/restore/`RET`. This is a separate selector rule, not a result inferred from the local arithmetic path. |
| [`BreakingAttackCalculation`](../../scripts/game_data/damage_snapshot_breaking_attack_flow.py) | Nonzero readiness byte, false patch, null server; `a = A(attacker, Atk, attackerOverrides)`, `b = A(defender, BreakingAttackDamageTakenScalar, defenderOverrides)`, `s = F(this.atkScale, bb)`, `m = F(this.multiplier, bb)`. Enum member names are joined to selected native defaults and actual request immediates. | `p = mul64(b, a)`; `q = mul32(s, m)`; `w64(mul32(q, r32(p)))`. |
| [`AtkScaleCalculation` null override](../../scripts/game_data/damage_snapshot_atk_scale_flow.py) | Nonzero readiness byte, false patch, null attacker override, nonnull incoming attacker, null server; `s = F(this.atkScale, bb)`. | `mul64(w64(s), Atk(attacker))` |
| [`MultiplyAttributeCalculation`](../../scripts/game_data/damage_snapshot_multiply_formula_flow.py) | Nonzero readiness byte, false patch, null server; source bits zero select attacker, the separately checked nonzero bridge selects defender and corresponding override; `a = A(selectedActor, this.attributeType, selectedOverrides)`, `m = F(this.multiplier, bb)`, `b = F(this.addition, bb)`. | `add64(w64(b), mul64(w64(m), a))`; actual addition destination is widened addition. |
| [`DamageAction` simple normal consumer](../../scripts/game_data/damage_snapshot_normal_formula_flow.py) | False patch, compatible unit, zero snapshot flag, nonzero simple flag and selected static/debug guards; `s = F(unit.atkScale, resolvedBlackboard)`, `a` is the anonymous Double carrier read through typed attacker attributes. | `mul64(w64(s), a)`; also stores `s` low32 into the typed explicit-ref pack scale view. |

NormalAttackPoise's reviewed disk operand is positive-zero Single in a unique raw-backed PE readable/nonwritable/nonexecutable section; the operand has no overlapping admitted base relocation, and unsupported relocation kinds fail closed. This is disk evidence, not observed live protection or immutability: original body/operand unchanged at invocation remains a condition. Do not simplify this Single multiplication to constant zero for NaN, infinity or signed zero. DefiniteValue's default Single literal is overwritten on its selected scaling path and is not a product operand.

The checkers independently verify ordinary getter/input/field ABI, concrete result owner, exact selected raw instructions/edges and restoring `RET`. The independent PrimaryAttr zero selector checks ordinary source/selector Int32 enum storage and actual Main/Sub comparison IDs; the exact intermediate CMOV bytes do not supply a nullable-layout or helper-identity proof. Main/Sub nullable helper identity and layout remain open; the zero selector does not need them, and unrelated generic-entry tooling failures are not evidence about this call. PrimaryAttr is a **local consumer** with a separate entry-save witness: prefragment actor/enum/nullable selection, intervening control/dataflow and this/blackboard/frame continuity remain open or conditional; no upper packed-lane meaning is inferred. AtkScale uses complete per-instruction unique physical range coverage and explicit cold links. Physical range adjacency or branch linkage does not establish a shared managed unwind family. The simple normal consumer's anonymous array displacement does not establish an element number or borrow the `Atk` enum name; typed pack/header and compatible array-layout conditions remain as stated above.

The actual non-simple calculation callback has a separate selection/forwarding proof in [`damage_snapshot_calculation_dispatch_flow.py`](../../scripts/game_data/damage_snapshot_calculation_dispatch_flow.py). A bounded caller request reads typed `DamageUnit.atkCalculation` into retained storage and passes that receiver in **RDX**, not RCX. The complete selected helper path rereads the receiver first-qword carrier after an opaque direct call, loads two actual carrier slots and compares the loaded function pointer with the selected named `DefiniteValueCalculation.Evaluate` entry. A non-equal pointer selects the actual indirect callback; seven ordinary arguments and an additional info-carrier argument are forwarded, and its normally returned low64 bits pass through the complete restoring `RET` unchanged. The caller's local Unit/actor/this/frame origins, opaque context return validity and anonymous pack carriers remain conditional; the helper is not granted a managed identity and its pre-dispatch callee is not named as a class initializer.

Actual carrier loads, offsets, pointer comparison, argument transfers and restoring return are exact/direct evidence. The metadata `CalculationBase.Evaluate` and named comparison method share an ordinary virtual prototype and slot; interpreting the observed cells as that virtual request is **conditional** on the JSON-declared runtime carrier layout, compatible live runtime class/prototype/parity/MethodInfo, valid contexts and normal noninterfering register/SIMD/frame preservation. Offset/slot arithmetic does not establish live class layout or runtime subtype selection, and the loaded callback stays unnamed. The equal-pointer inline body now has independent source/control/precision and restoring-return witnesses in [`damage_snapshot_calculation_inline_flow.py`](../../scripts/game_data/damage_snapshot_calculation_inline_flow.py): false patch, zero actual `applyScale` byte and null server return the named Double getter low64 unchanged; the nonzero-byte branch independently requests the named Single scale getter, widens it and multiplies the retained Double before the same helper return. The default Single load is not a product operand. The separate DefiniteValue method body supplies no inline proof. Typed `value`/`applyScale`/`valueScale` declarations still require a compatible Definite field view, which pointer equality does not establish; valid storage, ordinary saved-state preservation and runtime class/prototype/parity conditions remain. Only scaled arithmetic additionally depends on actual floating environment and normal completion; other patch/server paths and live selector/value remain open.

[`damage_snapshot_poise_delta_flow.py`](../../scripts/game_data/damage_snapshot_poise_delta_flow.py), through the same reviewed snapshot claims contract, independently proves selected normal `Modifier.get_finalDelta` numerical paths over a complete raw entry partition. Its inputs remain an anonymous raw DWORD direction `d` and raw Double magnitude `v`; ordinary named `DeltaType`/Double declarations and the full selected enum membership are checked, but the boxed-to-raw storage/header adjustment is **conditional**, not independently recovered layout. Anonymous static readiness, carrier, null and signed-threshold guards select these paths; they are not an ordinary false `IsPatched` call.

| Selected raw condition | Low Double returned in `XMM0` |
| --- | --- |
| `d == 0` | Direct positive-zero bit construction; no magnitude read or XMM6 save. |
| `d != 0`, actual `COMISD(+0, v)` has `JA` false | Retained `v` multiplied by the direction coefficient. |
| `d != 0`, actual compare flags have `CF == 0 && ZF == 0` | Clear magnitude to positive zero, then multiply by the direction coefficient; returned zero sign is preserved. |

The coefficient is selected by the actual DWORD comparison/`CMOVNE`: the freshly selected native Add ID matches the actual positive-one integer; other nonzero directions select negative one. `MOVD` followed by **packed `CVTDQ2PD`** creates the low Double coefficient before `MULSD`, and each selected path has its own complete frame/RBX/XMM6 restoring-return witness. The compare's ordered-negative interpretation, denormal behavior, NaN/traps, multiplication and signed-zero behavior retain the actual floating-environment and normal-completion conditions; this is not a `max(v, 0)` simplification. Other initializer/diversion/throw paths and live operands remain open.

A separate bounded named `PoiseController.ModifyPoise` caller witness passes retained Modifier storage to that actual getter and converts the normal Double result with `CVTSD2SS`, adds a retained Single with `ADDSS`, then requests an actual opaque setter helper. The selected parameter is an explicit-reference value record bound to the same concrete Modifier definition; it is not accepted by stripping its flags or treating it as an ordinary byvalue parameter. Compatible reference/storage ABI, caller entry-to-fragment carrier/frame continuity, the prior Single getter origin, normal register/frame noninterference and the typed getter header/view are conditions. The witness does not prove the whole caller return, runtime virtual accessor identity or applied/readback Poise.

[`damage_snapshot_poise_setter_flow.py`](../../scripts/game_data/damage_snapshot_poise_setter_flow.py) independently closes two complete selected `AbilitySystem.set_poise` normal-return paths. The ordinary Single input is retained, the typed controller is nonnull, ordinary `IsPatched` and `get_inPoiseRecovery` return false, and the anonymous static readiness predicate is nonzero. Named ordinary `get_maxPoise` supplies a Single request operand to an **unnamed** helper; the candidate `q` is only its actual post-call `XMM0.low32` carrier, not a proved managed Single return, Clamp result or min/max semantic value. Typed receiver/Single parameter/provider declarations and the class's `m_poise`/controller fields are checked without a boxed-header adjustment.

Both paths compute `SUBSS(q, p)` with `p` taken from the actual `m_poise` load at subtraction time, apply the selected bitwise mask, and perform `COMISS(threshold, maskedDifference)`. The selected original threshold and sign-clearing mask bytes have unique complete raw backing, readable/nonwritable/nonexecutable PE attributes and no admitted overlapping relocation across every used byte; this proves disk operands, not live immutability or protection. `CF == 1` emits a four-byte typed `m_poise` store from `q`, while `CF == 0` reaches a tail with no local store. Both independently restore the full frame/RBX/XMM6/XMM7 state and return normally. This is the actual carry predicate: normally returning **unordered** comparison also selects the store, so it is not simplified to an unconditional `abs(delta) > epsilon` test or NaN suppression.

Original code/operands unchanged, valid compatible receiver/context/frame/save/return storage, normal callee ABI/saved-state preservation, storage noninterference and floating environment/normal completion remain conditions. Earlier callees can have effects: no-local-store does not prove whole invocation field preservation, and the subtraction's field load is not identified with the entry value. Anonymous helper value production/prototype, other patch/recovery/initializer/null/throw routes, live virtual setter choice, entity state and applied/displayed amount remain open.

[`damage_snapshot_max_poise_flow.py`](../../scripts/game_data/damage_snapshot_max_poise_flow.py) adds a complete selected `AbilitySystem.get_maxPoise` source consumer: load typed `m_attributes`, request the freshly selected native `AttributeType.MaxPoise` through the actual named `Attributes.GetValue`, receive an ordinary Double, then **`CVTSD2SS`** it into the returned Single low lane through the full frame/RBX return. Receiver/field/provider concrete class definition indices and enum definition/storage/ordinary ABI are joined within the same selected image; type names or coincident offsets alone do not pass, and all same-ID native enum aliases remain recorded. Anonymous dual static readiness/carrier/null/signed-threshold guards select this path, without an ordinary false `IsPatched` call.

A separate actual getter-to-setter request witness carries that normal Single low lane into XMM6 and then XMM2 for the already independently proved setter's anonymous helper request. Only the getter input source is linked: there is no proved upper-bound/Clamp/min/max use or equality between that input and the helper's post-call candidate `q`. Other SIMD lanes have no asserted typed meaning. `Attributes.GetValue` value production and cached/recompute selection are not newly recovered or assumed; valid compatible receiver/attributes/class/frame storage, original code unchanged, normal callee and saved-state/storage noninterference, and the actual floating environment/normal narrowing remain conditions. Live attribute values, runtime invocation and applied/displayed Poise remain open.




All rows require compatible initialized object/field/array/static/frame storage as applicable, unchanged selected code and relevant saved storage, and normal Win64 calls preserving nonvolatile registers/SIMD state. Arithmetic rows also require normal completion under actual MXCSR rounding/DAZ/FTZ/exception state; the non-Main/non-Sub zero rule constructs bits and does not depend on floating rounding. Initializer/patched/server/other excluded paths, provider internals, runtime `CalculationBase` subtype selection and final live damage or Poise are not proved by this table. As a teaching example **assuming round-to-nearest/ties-to-even**, Double `16777217` with Single scale `1` remains `16777217` in DefiniteValue, but the selected PrimaryAttr narrowing and BreakingAttack attribute-product narrowing produce `16777216` for otherwise unit factors. These are illustrative operands, not native inputs or observed game values.

- Open: snapshot production and value/index correspondence, the helper's full subtype dispatch, provider and
  attack-getter internals, override-array construction, mitigation, immunity
  and final damage.

### Damage-pack scale composition

The reviewed [damage-pack scale contract](../../scripts/game_data/contracts/damage_pack_scale_native.json)
and [native validator](../../scripts/game_data/damage_pack_scale_native.py)
authenticate named entries, compiled windows including the special cold return,
value-type fields, the initial Double literal and the DamageType enum member.
Missing/mismatched native inputs and byte/layout/enum drift publish no rule.
The interpretation is a conditional disassembly reading, not a complete CFG
proof or a measured final HP loss.

On the selected false-IFix ordinary path, `DamagePackData.GetFinalAttackValue`
first calls `ApplyDamageModifer`, then `_GetFinalDamageScale`, and multiplies
the returned Double by `calcResult.value`. The reviewed non-debug continuation
returns that product. `_GetFinalDamageScale` starts with the original disk Double-one operand and treats an actual post-call EAX carrier as a signed bound: a non-positive bound reaches the seed return; a positive bound initializes a zero Int32 index, passes each raw item carrier to the named `_GetDamageScale`, and updates the accumulator with `MULSD` in request order. The arithmetic is an **ordered floating left fold**, with rounding/exception behavior at each multiply, not a reassociated real-number product or one flat sum of damage bonuses. A positive signed bound permits indices from zero through bound minus one and the final increment equal to bound without signed overflow, subject to normal callee preservation of counters/receiver/SIMD/frame state and valid compatible storage/contexts.

The count helper's managed signature and list/configuration identity remain open. The actual item entry has a registered `List<Object>.get_Item` alias, which does not establish a typed `List<Zone>`, actual heap list layout or live item class; raw RAX is only a Zone-compatible request carrier under a stated condition. The named scale provider's ordinary Double/Zone-reference declaration does not prove its internals or actual values. Original code/seed unchanged at invocation, normal return, floating environment, and storage/register/SIMD/frame noninterference remain conditions. The independent [ordered Double-fold checker](../../scripts/game_data/damage_snapshot_damage_scale_fold.py) authenticates the complete physical entry partition, every branch target, selected empty/positive normal return and all saved-state/frame restoration. Its same-image concrete Pack/Zone owner and ordinary ABI gates establish the named scale request separately from anonymous count/item semantics. The complete eight-byte original seed has unique raw backing, readable/nonwritable/nonexecutable PE attributes and no admitted overlapping relocation; live immutability is not inferred. The existing wide scale validator remains conditional disassembly evidence. Individual zone arithmetic, configured list ownership, live values and final settlement require their own proofs.

The independent [final-attack checker](../../scripts/game_data/damage_snapshot_final_attack_flow.py) proves one complete selected normal-result path through `GetFinalAttackValue`. Its fresh ordinary Int32 `AfterCalculation` request goes to the same concrete Pack owner's named `ApplyDamageModifer`, whose effects remain opaque. The next direct request targets the same freshly proved final-scale entry; this connection is evidence within the result rule, not a second recovery claim. The normal Double scale is retained in XMM6, then the actual low-Double value carrier is loaded **after both calls** and used by `MULSD(scale, loadedValue)`, followed by the complete XMM6/RBX/frame restoring return. It does not assert that this field still equals its entry value.

The raw result and damage-kind accesses are exact instruction observations; their typed `calcResult`/`damageType` views remain conditional on the declared value-type header/storage adjustment. The same-image concrete owners, sole ordinary Double result field, ordinary enum storage and all same-ID `AfterCalculation`/`LifeDrain` aliases are checked independently, but those declarations do not prove boxed/unboxed layout, modifier effects or live values. Original code, compatible receiver/debug carriers/storage, normally returning named calls, actual floating environment and register/frame/object noninterference remain conditions. The selected debug flag and nonnull carriers are anonymous machine guards; patched, initializer, debug-diversion and LifeDrain cold paths are excluded.

The independent [DamageType selector checker](../../scripts/game_data/damage_snapshot_damage_type_selector.py) separates a finite UInt32 RVA jump table from the complete physical code partition. Its unsigned enum guard admits only the eight table indices; negative Int32 values are excluded before the scaled read. Five selected cases have independent nonnull/unsigned-count guards, an exact eight-byte payload load into XMM0 and a full RBX/frame restoring return. The other three table targets remain excluded cold paths. The table's whole raw backing, readable/nonwritable PE section and absence of admitted overlapping relocation are checked separately; executable table sections are admitted without weakening literal-operand checks, and original runtime table/code unchanged remains a condition.

| Native damage kind | Selected-slot AttributeType annotation (conditional) |
| --- | --- |
| Physical | PhysicalDamageIncrease |
| Fire | FireDamageIncrease |
| Pulse | PulseDamageIncrease |
| Cryst | CrystDamageIncrease |
| Natural | NaturalDamageIncrease |

The named `attackerAttributes` declaration is an ordinary Double array with an independently checked ordinary primitive element. The physical-index interpretation retains the declared array count/payload/stride layout and Pack header/storage conditions. **Same-ID AttributeType names are conditional numeric annotations**: this checker does not prove that the array producer filled each slot from that attribute, nor identify its live value. `MOVSD` preserves the loaded low 64 bits through return without arithmetic, conversion or NaN/signed-zero filtering. Compatible valid current receiver/array/frame storage, false ordinary patch return, normal instructions and no external interference remain conditions; no Buff/provider or cold-path behavior follows.

The independent [attribute-array producer checker](../../scripts/game_data/damage_snapshot_dump_attributes_flow.py) proves one complete selected `_DumpAttributes` normal-return path through both loops. Each loop starts its own Int32 index at zero, passes the old index to the same actual named ordinary `Attributes.GetValue(AttributeType)` request, and transfers its normal Double low bits unchanged to the current iteration's array at that same old index. Sign extension occurs before `INC`; the incremented counter is used only by the next signed guard. A stable anonymous bound in the nonnegative Int32 range yields the ordered indices up to bound minus one without signed increment overflow. The entire saved-state/frame return is checked. The first-phase index/array registers later become a defender-array pointer and a second actor carrier; their earlier meanings are not carried across those writes.

The two actor acquisition calls share a physical entry, but a registered generic Object alias does not prove a typed `ObjectPtr<AbilitySystem>.Lock` ABI or return. Each raw RAX carrier must be compatible actor storage before its fresh declared `m_attributes` reference is interpreted. Pack value-field and array-layout views, normal callee/nonvolatile/frame preservation, valid storage and object/payload noninterference remain conditions. The anonymous bound's source/value, provider internals and a coherent-time attribute snapshot remain open.

This supplies a **conditional** source connection to the fresh DamageType selector: when the same Pack and attacker array remain stable, the bound covers the selected slot, and no later defender store, opaque callee effect or external write overwrites it, that slot contains the normal bits returned by `GetValue` for the same enum-index request. The connection is part of the producer row; it does not establish actual invocation/order, infer that opaque `ApplyDamageModifer` calls this producer, or make the selector's numeric annotations into observed live attribute values.

The native enum names the special branch `LifeDrain`. At this pack entry its
selected false-IFix branch directly returns `calcResult.value` through the
common epilogue, bypassing the ordinary modifier/zone calls in this method.
This does not say that its caller or later HP settlement bypasses other logic.
Do not infer a localized mechanic or equate this branch with every authored
healing/lifesteal effect on a name alone.

The v3 contract extends this interpretation through configured zones,
modifier stages, BattleFormula, shield consumption and the ordinary base HP
path. Its validator additionally checks signatures/slots, static and instance
fields, typed Int64 damage masks, selected scalar literals and closed caller
MethodSpec requests. These are
reviewed conditional algorithms, not full CFG proofs. Unsupported instructions
in the general disassembler are read from their authenticated bytes rather
than treated as valid decoded instructions. Existing damage-action and
snapshot contracts remain separate upstream evidence.

### Zone inputs and combination rules

The native configuration path reads `GameInstance.dataManager` and its typed
`damageScaleProcessorConfig`, then `allZones`. The maintained
[configuration projection](../../scripts/game_data/damage_zone_config.py)
reads the named serialized-TypeTree fields from the Unity store and retains
object/source identity. The CLI admits it only under current MonoBehaviour
export freshness. This identifies a stored configuration candidate; it does
not prove that this object is the live singleton's configuration. Array index
comes from list position, not `serverIndex`; server indexes can repeat.

For a newly constructed pack both actor zone arrays start at one. A modifier
resolves a named zone and updates the selected side:

| Zone operation | Compiled rule for finite values |
| --- | --- |
| Additive write | `side = side + resolvedValue` |
| Multiplicative write | `side = side * (1 + resolvedValue)` |
| Separate-side evaluation | `max(attackerSide * defenderSide, 0)` |
| Merged additive evaluation | `max(attackerSide + defenderSide - 1, 0)` |

The merge alternative is selected only for a non-multiplicative zone. A
missing zone name logs and returns without applying the write. A zone marked
as damage-type-dependent can select neutral one when its type/mask gate fails.
The named damage-type, skill-type, ignite, broken-target, enhanced and
vulnerable configuration routes add their built-in contributions into actor
cells during evaluation. The selected stored definition sends damage-type,
skill-type and broken-target contributions to the same additive zone; enhanced
and vulnerable use separate routes. The projection exposes that join from
fields rather than replacing it with a hardcoded zone inventory.

Physical, Fire, Pulse, Cryst, Natural and Ether select their matching attacker
damage-increase/enhanced attribute or defender vulnerable attribute; Real and
LifeDrain have no matching typed addition in these helpers. Skill and reaction
masks select additional attributes, with combined mask handling distinct from
simple enum equality. Built-in contributions mutate pack cells in place;
repeatedly evaluating the same unreinitialized pack would accumulate them.
Model one evaluation per prepared pack, rather than treating this getter as
a pure reusable calculation.

### Damage modifiers and numerical precision

The ordinary modifier pass visits the attacker's collection before the
defender's, selects matching `EnableSide`, checks any valid condition sequence
and visits the stored processor list in index order. A false condition skips
processing. Container insertion/sorting and individual condition providers
remain separate. Processor admission checks timing and supported health type.
DamageAction submits `BeforeCalculation` before calculating the unit;
GetFinalAttackValue submits `AfterCalculation` before composing zones. After
both sides of a modifier pass, the two actor attribute snapshots are refreshed.
The stages therefore cannot be collapsed into a single modifier sum.

`DamageScaleProcessor` widens its Single Blackboard result to Double for the
zone write. `ModifyCalcResult`'s selected Multiply case changes the base value
by a factor formed as Single multiply followed by Single addition of one,
then widened to Double. Keeping the stored expression as Double throughout
would change the binary's numerical rule. The compiled default
`AttackCriticalRateProcessor` body is a no-op despite its stored addition and
BeforeCalculation declaration. `IgnoreShieldProcessor` sets the pack flag in
BeforeCalculation. IFix alternatives retain their separate selection boundary.

The complete selected processor admission reads virtual processTiming and
modifiableHealthTypeMask. LifeDrain is rejected; otherwise requested timing
must match and the defender selects NormalHealth bit one or IndependentHealth
bit two. Concrete default getters put IgnoreShield, InstantModifyAttribute
and AttackCriticalRate in BeforeCalculation/NormalHealth. DamageScale,
ModifyCalcResult, DamageText and the legacy attack/defense processors select
AfterCalculation/NormalHealth; DamageIndependentHealth selects
AfterCalculation/IndependentHealth. The latter changes calcResult.value by
`Double(Single(resolvedMultiplier))`, with no plus-one. The legacy
AttackerAtk, AttackerCriticalDamage, AttackerPen and DefenderDef default bodies
are also no-ops. Their stored fields do not establish additional arithmetic.

For a nonnull condition, DamageModifier requires a valid SequenceAction,
prepares the other actor's target carrier and pushes the current damage context
into the children's environments. It executes with resetAfterExecute enabled,
then removes those contexts before admitting processors. SequenceAction is
stateful: ended children are skipped, pending children execute in list order,
and other positive execution states stop with false. The per-step execution
policy normally requires success; LastFailed consumes a failure requirement
and restores LastSucceed. Reset after each attempted child is a separate step.
An exhausted or empty valid sequence returns true. This cannot be modeled as
an unconditional Boolean AND or a permanent negation of the whole sequence.
Leaf conditions and context provider effects remain conditional.

### Formula, shields and actual HP loss

For normal health, the selected ordinary formula is the Double product of
the scaled pack value, attacker WeaknessDmgScalar, the critical factor, DEF
factor, `1 - defender.ShelterDmgScalar`, nonnegative typed resistance/taken
factor and defenderPoiseFactor. IgniteDamageSet and PhysicalInfliction masks
independently select their additional attacker scalar. CriticalRate feeds the
Dice call; a true result uses `1 + CriticalDamageIncrease`, otherwise one.
Exact RNG state is not recovered. The unpatched defenderPoiseFactor getter
returns one; its name alone does not establish an additional broken multiplier.

Real damage selects neutral DEF and typed resistance factors, while the other
normal formula inputs remain. For other types, nonnegative DEF uses
`1 / (1 + efficiencyOfDEF * DEF)`. The coefficient is the named BattleConst
Single getter widened to Double. Below the compiled negative epsilon, the
alternative is `2 - pow(Double(Single(1 - efficiencyOfDEF)), -DEF)`; near-zero
negative DEF retains the rational path. Typed resistance is
`(1 - defender.Resistance / 100) * defender.DamageTakenScalar`, with a matching
attribute pair per damage type, and the caller clamps that result at zero.
Normal-health LifeDrain returns the pack value without these ordinary factors;
Independent health returns current calcResult.value. Both selected branches
clear critical/blocked outputs and the report reference.

The ordinary HP chain then checks cancellation and damage immunity, processes
shields unless ignored, and writes the residual into Modifier.value. The
shield controller visits its current collection in reverse index order. A
shield's initial capacity is its Double valueCalculation result multiplied
by the widened Single attribute factor. The shield buff's owner supplies
ShieldTakenIncrease and its source supplies ShieldOutputIncrease; an invalid
source contributes zero. The compiled factor adds ownerTaken to one, then
sourceOutput, with both additions in Single precision. These are live actor
attributes sampled at shield initialization, not the damage pack's snapshots;
the selected getter does not clamp this attribute factor.

Each shield's absorption dictionary supplies `(ratio, scale)`: an empty dictionary
uses `(1, 1)`, while an absent damage key in a nonempty dictionary uses `(0, 1)`.
For positive finite scale, requested absorption is `input * ratio` and required
shield value is that amount divided by scale. Sufficient value leaves
`input - requestedAbsorption`; a finite shortfall leaves
`input - remainingShieldValue * scale` and consumes the value. The stored
absorption count is decremented. Infinite-value/count and consumption policies
must remain active: in particular, `absorbAllDmgWhenConsume` can replace the
shortfall residual with `input - requestedAbsorption` on the consuming hit.
Consumed, near-zero-input and near-zero-ratio shields pass the amount through.
Nonpositive-scale cases remain outside this finite rule. The stored AddShield
MethodSpec is PriorityQueue<ObjectPtr<ShieldInst>>, not PriorityQueue<ShieldInst>.
Its shared compiled insertion uses ObjectPtr instance UID with unsigned
comparison, inserting before the first greater UID and after existing equals.
Under normally resolved matching generic contexts, valid ObjectPtrs and an
otherwise unchanged container, reverse consumption therefore uses descending
UID, with the latest insertion first for equal UID. ShieldInst.CompareTo's
configuration-priority/remainingTime comparison is a separate body not used
by this shared comparison. UID order must not be translated into creation-time
order until allocation chronology is proved. Live list mutation and IFix
selection retain their own boundaries.

A near-zero shield residual selects ShieldBlock cancellation. Remaining damage
produces `finalDelta = -max(Modifier.value, 0)`. The caller submits old HP plus
that delta through virtual SetHpInternal and records a new readback minus the
earlier HP as realDelta. The base setter clamps to zero/maxHp, applies its HP
floor and undead/server-death policies, and can emit synchronous callbacks.
Thus the simple `clamp(oldHP - residual, 0, maxHp)` rule is conditional on a
living unprotected base target and no callback rewriting HP, rather than a
universal rule for enemy parts or every entity subclass.

Successful default HP processing reaches `_OnAttacked`, whose selected
notification paths distinguish receiver OnTakeDamage/OnTakeCriticalDamage from
source OnOutputDamage/OnOutputCriticalDamage. The ordinary receiver dispatches
precede source dispatches under their interest/critical gates. Their contexts
keep requested damage separate from real HP loss. Before these dispatches,
the default LifeSteal branch requires distinct source/receiver, negative
realDelta and positive source LifeSteal; it builds the self-heal base from
actual HP loss times the source's Single LifeSteal value widened to Double,
then uses the healing pipeline. Overkill request is not its base.

### Immunity and damage-tag policies

The compiled immunity check has early returns. LifeDrain returns false. The
level-immunity predicate returns true; skill-immunity and dodge-immunity
predicates each return the inverse of their corresponding ignore mask
immediately. An ignore flag on one of these paths therefore bypasses the later
allowed-mask and tag-rule checks too. Only when neither predicate is active
does a disjoint allowed damage mask reject the hit, followed by the tag-rule
loop. The selected predicate constants correlate with the predefined registry;
fully resolving each anonymous predicate's loaded provider remains separate.

Multiple requested allowed masks combine by bitwise intersection. Removing
the last request restores an absent nullable mask, rather than a zero mask.
Tag queries have different matching algorithms: HasAny walks each damage tag's
parent descriptors; HasAll requires exact tag IDs for every query tag. Both
ExceptAny and ExceptAll reject any exact-ID intersection, with different loop
orders. They are not inferred complements of the hierarchy query. For valid
collections, an empty HasAll or exception query succeeds, while an empty
HasAny fails. Descriptor resolution, initialized registry and IFix selection
remain conditions on these compiled rules.

### Enemy-part HP and transferred damage

The selected EnemyPart HP/maxHP overrides read the main body when
`data.useMainBodyHp` is true and use the base accessor otherwise. Its HP setter
does no write when sharing is enabled; otherwise it delegates to the base
setter. Sharing alone is not a forwarded HP write. The selected ordinary
AbilitySystemForGod ApplyModifier override returns Failed.

PartDamageTransferType separates two calculations. PartAttributes submits a
main-body modifier from the part's calculated damage times its Single
damageRatio widened to Double, after the normal successful
calculation/application gate. That amount comes from CalculateDamage before
part HP settlement, rather than actual part HP loss. MainBodyAttributes queues
an ExtraTarget for the main body, retains the struck part as transferredSource,
calculates the new target independently, then multiplies that calculated damage
by the part ratio. Its extra-target flag suppresses another extra-target queue;
the queue-admission gate can also admit poiseRatio. These ratio gates use the
compiled Single near-zero threshold, rather than any value greater than zero.
Do not calculate
both modes with one defender snapshot or turn the queue gate into a damage
multiplier.

Both use ApplyTransferredModifier. Its selected HP branch checks cancellation
and damage immunity, writes HP plus finalDelta through the virtual setter and
records readback realDelta; it does not repeat ordinary shield absorption or
submit the ordinary _OnAttacked LifeSteal/source-output path. PartAttributes
passes false for triggerTakeDamageEvent, while the ExtraTarget route passes
true, admitting receiver before/take-damage notifications. OnPartsBeHit is a
separate interest-gated main-body/part notification, not proof of HP loss.
These are valid, normally returning false-IFix paths; HP floors, callbacks,
live target/configuration and authority still affect the result.

These rules advance the simulator's numerical and state-transition kernel.
The reviewed DamagePackData dump refresh calls Attributes.GetValue in ascending
attribute-index order and stores the returned Double at the same index in the
attacker or defender array. Its two direct caller sites distinguish the sides;
the ordinary modifier pass reaches this refresh after both collections.
Normal-return getter values provide numerical inputs under stable actor and
array storage; an entry field alone does not establish the completed snapshot.

Remaining work includes leaf condition/listener effects, shield UID allocation
and container mutation, specialized authority/death policy, and live config or
patch selection. Existing failed combat sessions can cross-check residual HP
arithmetic on retained complete pairs, but cannot establish a healthy whole
capture or reconstruct the same hit's full attacker/defender inputs.
The reviewed [damage kernel recipe](../../scripts/game_data/contracts/damage_runtime_kernel_capture.json)
addresses that numerical validation gap with paired formula/pack returns,
getter returns limited to the two dump callers, formula critical/blocked
Boolean output pointees and modifier/HP snapshots. The Boolean reads use the
selected native byref declaration and one-byte runtime reader. Only normal
return values are interpreted; entry bytes of output parameters may be
uninitialized and have no semantic meaning.
It excludes the global IFix observer. Capture transport health, source/native
binding, nested call identity and side selection must be checked before using
these observations to compare the formula; stored client HP is not a virtual
part/main-body accessor or server acknowledgement.

## Character attribute formula

[`attribute_formula_native.json`](../../scripts/game_data/contracts/attribute_formula_native.json)
records how `Beyond.Gameplay.Core.Attributes` turns modifiers into a final
value (exact expressions there); `attribute_formula_native` re-proves its call
structure on the installed build.

- Three stages, each clamped to `AttributeMetaTable` bounds: base = raw +
  BaseAddition; armed applies BaseMultiplier (`max(1 + Σ, 0)`),
  BaseFinalAddition and the BaseFinalMultiplier product; final applies
  Addition, Multiplier, FinalAddition and the FinalMultiplier product.
  Same-type modifiers sum, except the two FinalMultiplier types, which multiply.
- Conversions are table data: `BattleConst` `atkRateOfMain`/`atkRateOfSub` feed
  `AtkIncreaseFactorFrom{Str,Agi,Wisd,Will}` (attributes 76-79), ATK's final
  scalar is `1 + Σ floor(X)·factor`, and MaxHp gains `floor(Str)·efficiencyOfSTR`.
  Attributes are floored before conversion.
- `modifyAttributeType` Main/Sub retarget to the owner's main/sub attribute and
  All to Str/Agi/Wisd/Will; an equipment line with `attrType` 0 is such a line.
- Sources: weapons add `(Atk, BaseAddition, baseAtk)` from the upgrade curve;
  weapon, set and passive skills carry `SkillData.cardAttributeModifier`
  (`formulaItem` is the ModifierType); equipment reads `equipAttrModifiers`.
- Healing base additions are `floor(Will)` times the corresponding
  `healerEfficiencyOfWILL` / `recoverEfficiencyOfWILL` table coefficient.
  Physical resistance gains `100 * (1 - 1 / (1 + floor(Agi) * efficiencyOfAGI))`;
  Natural/Cryst/Pulse/Fire use Wisd and `efficiencyOfWISD`. Ether has no
  ability conversion in the default base-add dispatcher. These additions enter
  before base multipliers, rather than being added to the final display value.
- MoveSpeedScalar's armed-stage conversion multiplies by
  `1 - final(SlowActionSpeedScalar)`. ComboSkillCooldownScalar's final-stage
  conversion multiplies by `final(ComboSkillCooldownDecrease)`; it does not
  derive directly from Agi. The recovery scalar is a separate attribute.
- Each element's DamageTakenScalar also multiplies by the corresponding
  final DamageTakenReduction. The reviewed final dispatcher supplies these
  joins independently of the similarly named resistance attributes.
- Call structure is `direct`; general arithmetic order remains a reviewed
  disassembly reading (`conditional`, the stdlib decoder skips some SSE forms).
  The complete base/armed/final bodies, conversion dispatchers and
  healing/resistance paths additionally authenticate reviewed native code
  windows, external float literals and enum IDs from the v2 contract. Movement
  conversion can be inlined into the armed body: its GetValue call and pinned
  arithmetic replace the obsolete requirement for a separate helper call.
  Byte/literal/enum drift produces `pendingReview`
  instead of publishing an old formula. This covers default paths without
  IFix replacements; combat buffs, gems, team effects and exceptional paths
  remain outside the loadout inputs.
- Loadout skill modifiers decode the selected export's pooled strings explicitly
  when its StringPool exists; older exports retain inline strings. Publication
  still requires the entire SkillData record through EOF and an identifier
  matching its filename. Dispatcher-table selection requires both the catalog's
  wrapper identity and complete family size, so an unchanged early tag in an
  older, smaller family cannot select its stale table. Conflicting current
  pins and native table-byte drift still withhold the plans.

Projectile behavior is immutable authored data; skill/projectile ownership,
event hashes, decoded media and asset references keep separate provenance.
Combat/source-graph consumers reject stale inputs and publish a degraded reason
rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](../webui/gameplay.md).

Gameplay semantics observes seven named typed action consumers. The data
reference belongs to the instantiated generic base; its open generic field row
cannot supply a runtime offset. TargetHandleView is a small value carrier.
Bounded raw Data words can contain padding and do not prove evaluated action
semantics or target ownership. Original-call exceptions invalidate completeness
and must propagate while callback and thread-local observation scopes drain.

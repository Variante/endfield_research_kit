# Story activation and placement carriers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, story lane.** What a decoded LevelScript action, Timeline record, or
spatial carrier actually owns, reaches, and places -- and the exact-build native
gate and overlay rules that bound every such claim. The Story reconstruction
model these carriers feed, and everything about presenting the result, is
[`../webui/story_recovery.md`](../webui/story_recovery.md).

## LevelScript, Timeline, and native evidence

Selected LevelScript actions prove Story links under explicit gates. That
covers the carriers Story reads, not the whole LevelScript family.

- LevelScript actions, headers, UIDs, callbacks, lists, and target carriers are
  accepted only through versioned parsers and bounded validation.
- Active evidence uses one logical-path overlay. Persistent replaces the
  complete StreamingAssets file; changed shadow data is decoded from active
  bytes or rejected.
- A direct playback carrier requires one typed header-to-action path. Preload,
  load, stop, sibling actions, foreign headers, unresolved graph shapes, and
  raw numeric hits remain diagnostics.
- CallServer ordering requires one complete linear Story-to-callback-to-Story
  closure with no branch, merge, loop, truncation, or ambiguous target. A
  one-sided path adds no cross-Story edge.
- Timeline track/clip ownership proves authored scheduling, not Director
  activation, selected option, or Wwise playback.
- Native evidence is locked to exact `GameAssembly.dll` and metadata hashes.
  Registration order and code addresses never imply Story order.

`levelscript_node_strings_native --add-wrapper` adds a missing UID prefix only
after its maintained wire plan, selected native declarations and pooled setter
transfer pass an existing complete proof profile. Existing records are reused
only on the same reviewed build; the cutscene control/hide-scene wrappers now
have that prefix proof. Their later fields and whole-owner closure stay separate.

Source replay retains each Param's declared enum kind and its current typed
component gate. A matching integer or byte width does not authorize replacing
that enum with a generic primitive Param.

Protocol-registry listener coverage uses complete typed action-map lists only.
A refused map retains its source hash, failed gate and cursor and contributes no
candidate records. Reported listener counts therefore establish no absence in
unavailable maps. The independent native/protobuf audit can remain validated
while that serialized coverage is partial. Story parallel-fanout authority
requires the shared current registry schema, the named scheduler proof shape,
and matching selected native inputs before and after reading its source files.

CallServer's hash-shaped event name can repeat its own action UID. That is a
local correlation label, not an additional Story node or a resolved server
handler. Resolve the reviewed action envelope by type name through
`levelscript_union_tags`; a client update can renumber the tag without changing
this identity rule. Keep the callback-output UID list separate from that event
name. `waitForCallback` with a null output list supplies no named callback
header; an explicit output requires its own exact same-file header/action join.

An exact callback can stop at `LsmEncounterSendOperaSignal` rather than another
Story playback. Its reviewed stored route retains a typed `Param<LsmPtr>` and
`Param<string>` signal, not a Story target. A same-file module dictionary key
and the module's stored `id` can resolve a constant operand to an EncounterData
configuration; matching a neighboring script filename cannot. A matching
`battlePart.completeDelayStrParam` describes a configured signal relationship,
not delivery or completion. A signal named `finish` is therefore not a Story
completion or chronology edge. Joining that configuration to the encounter's
pending runtime state and post-completion actions remains unresolved.
The portable `encounterOperaSignalBoundary` claims in
`scripts/game_data/contracts/story_native_consumers.json` re-prove the named
signal operand reads and comparison path. The V2 battle-delay completion body
loads `CompleteBattlePart` and calls `LevelScriptModule.TriggerServerEvent`.
That is a server handoff boundary, not a local quest-success or Story edge.
Stored `WaitOperaSignal` configuration alone does not prove which pending mode
accepted the signal, that the V2 completion body ran, or how the server response
activates a later callback.
The next named consumers to join are the module event prefix/sender and the
V2 `get_battleTaskCompleted`, `BattlePartDoRegisterEvent`,
`_IsBattleTaskCompletedOnChanged`, and `_OnBattleTaskCompleted` paths. Treat
saved-property origin, value, receiver identity, selected generic context, and
patch selection as separate open checks. Even a validated client transport
chain cannot supply a server quest decision or order for an unvisited branch.
The adjacent `LevelEvent.OnSpawnerWaveComplete` family has separate spawner and
wave-key filters and typed output destinations; those outputs are not observed
wave values or evidence that the event fired.

DialogTree UI continuation has two independent native maps: named outgoing
port labels and configured default indexes. Selector enum defaults use the shared
IL2CPP compressed signed-integer reader; the former local three-byte and
extra-prefix grammar is not a second supported metadata format. Truncated or
unsupported defaults refuse with the enum, field and data-section source.
 The initializer can call shared
`Dictionary.Add` bodies for both, so the exact MethodSpec passed at each call
must supply the closed key/value types. The reusable integer-map and lookup
return programs live in `scripts/game_data/il2cpp/static_dictionary.py`; the
Story family reader binds them to the declared static field, owned method
bodies, and current IFix exclusion. Do not substitute an Object instantiation
sharing a code address for the supplied closed MethodSpec.

The native panel-name getter parses the selected UI enum, then reads the
default-index dictionary. Failed parsing or a missing dictionary key returns
zero. The shipped Lua router uses that getter when no nonnegative temporary UI
result was supplied, and forwards the resulting index to the native dialogue
continuation. Configured defaults and explicit result-message producers remain
separate. Port names and default indexes prove conditional local alternatives;
they do not observe a selected UI outcome, mission activation, or cross-Story
chronology. The family reader validates the complete shipped Lua producer
census as well as the native consumers.

AirWall state predicates distinguish mission IDs from quest IDs with the
serialized `isQuest` flag. A quest predicate is admitted only when its ID is
both a `questDic` key and that row's stored `questId` in the named target
MissionRuntimeAsset. A matching name prefix supplies no membership evidence.
Valid predicates describe wall configuration and its later pushback radio
callback; they do not establish a mission transition or relative Story order.
The current stored air-wall reader uses the selected export pool and checks it
and the source-native gate again after collection. Its pooled field/setter
proof does not re-prove the callback consumer chain; those Story context rows
keep `nativeConsumerStatus=pending_current_build_review` until current body
claims establish that chain.

Reviewed quest attachment diagnostic declarations live in
`scripts/game_data/contracts/quest_attachment_diagnostics.json`. Their source
hashes and exact generated-field predicates close diagnostic co-membership;
they do not add ownership or chronology. Source drift empties the pinned index
and reopens its gaps. The source-gap API records that index's row count before
merging separately validated generic boundaries. Mission publication accepts
the two source-pinned catalogs' inactive status only with an explicit empty-row
receipt and no independent validation failure. It still withholds their stale
classifications; parser, shape, and nonempty-index failures stop publication.

## Native claims across a client update

- A contract records its build in its own `nativeInputs`/`sources`; no module
  repeats that hash. On another build it reports `mismatched` until the claim
  is proved again, and only names carry over: addresses, tokens, offsets,
  registers and enum values are re-derived, and code registration is located
  from the metadata image names, never pinned.
- Claims that re-prove from the binary use maintained source validators
  (GenderSelect) or regenerators (CallServer callback, iFix patch, cinematic
  queue, TeleportParam). Census
  conclusions (identity-carrier negative boundaries, cross-system consumers)
  have none and stay `mismatched` until reviewed again.
- Instruction-shape analyses must survive codegen churn. The current build
  wraps many methods in an iFix patch-flag test, moves rare paths into
  separate `.pdata` fragments, calls unnamed helpers (struct-argument shims,
  inlined copies of named methods), reallocates saved registers, and widens
  short jumps to rel32 `jcc`. A body is the function plus every fragment
  chained to it by `UNW_FLAG_CHAININFO` (`BodyIndex.chained_fragments` in
  `scripts/game_data/il2cpp/body_claims.py`), however reached; a jump-target
  walk misses fragment-to-fragment edges. Follow one level into an unnamed
  helper, name a jump from its opcode, accept any save/restore register pair,
  and label a helper-reached callee as such. Compiler-generated names
  (`<M>d__N`, `<>c__DisplayClassN_M`, `b__N_M`) renumber between builds; match
  them with the ordinal normalized, and only when unique.
- An iFix wrapper may test its patch id after a class-init prologue, so an
  opening-window miss does not prove it absent. The inlined
  `TaskCondition.InvokeOnIsCompleteChangeAction` escapes a hook on the named
  method (`scripts/game_data/mission_task_paths_native.py`).
- Task hooks are named claims in `mission_task_paths.json`, re-proved against
  the selected native pair with source and native bookends. Missing inputs,
  failed claims or drift publish no hook rows. The SET_DONE handler is selected
  by its exact packet parameter because its method name is overloaded. Declared
  storage stays typed: `levelScriptPtr` and `taskKey` are value holders, not the
  former flat scalar identities. The dialog task audit joins the current
  method's symbol, token, metadata index and RVA to the independently proved
  lifecycle row instead of keeping a token in Python. These identities and
  listed claims do not establish execution or complete hook coverage.
- Register provenance must follow control-flow edges. An early replacement
  return can restore saved registers before a later original block that an
  earlier branch reaches directly; linear origin scans then invent packet-field
  aliases. Such a scan cannot prove identity forwarding or control predicates.
- Protocol discovery uses `protobuf_schema.message_fields` to join wire-tag
  literals to pooled members or auto-property backing fields, preserving the
  actual member spelling. Message audits resolve offsets through the same join;
  stable logical audit keys are not physical storage names. A storage-name suffix
  alone is not message evidence.
- The protocol event-token claim follows the current inline store instead of
  requiring a called setter. `storesStackParameterInTypedFactoryField` binds
  the closed factory MethodInfo, registered shared-reference entry, declared
  return ABI, unchanged incoming stack string and exact packet field. This is
  `conditional` on ordinary returning callees and stable, disjoint storage;
  allocator internals and runtime message delivery remain unproved. Native
  claim receipt reuse binds the complete reader inputs before and after reads.
- The current quest-enable handler consumes both the enable flag and previous
  state. Enabled stores the packet state; disabled stores `Disabled`. Lifecycle
  dispatch uses that effective state and the runtime pause flag; `DisableQuest`
  receives the opposite selected prior-state source. The matrix covers declared
  enum values, not arbitrary wire integers or server selection. Its owning
  protocol registry withholds publication while other required native gates fail.
- The current original active-area rule is conditional:
  `!rangeSensitive || hit(enterShapes) || (prevWithin &&
  !IsNullOrEmpty(exitShapes) && hit(exitShapes))`. The outside list is a hold
  zone, not an exclusion zone. The caller selects an anonymous optimized body.
  The reviewed `levelscript_area_rule_native` contract authenticates its typed
  caller, original named outer branches, complete paired geometry control/value
  transfer, protected outer slots and registered Quaternion buffer effects.
  The shared `il2cpp/scalar_buffer_effects.py` proof rejects pointer bits,
  undeclared inputs and uninitialized locals reaching those outputs; both scalar
  dispatch paths and the selected order-four rotation adapter are covered.
  This establishes the same stored Boolean on initialized original paths with
  finite Euler inputs, selected original icall caches, no active named override,
  stable disjoint storage and ordinary nontrapping floating-point behavior.
  Cold initialization, nonfinite/error paths, exception/resumption entries,
  replacements and live execution remain outside that claim. The registry keeps
  those premises and exclusions in its current projection; the proof supplies
  no mission owner, execution observation or ordering edge.
- Consumer meanings the Story builders cite are claims about named bodies
  proved on the installed build (`contracts/story_native_consumers.json`,
  `contracts/dialog_finish_native.json`), not pinned tokens. The current
  Timeline option-index claim proves a wider current-or-previous gate. The
  director getter now proves its typed root-to-director field return after the
  false Unity null guard, with a null return on the true guard; IFix replacement
  results and runtime execution remain separate. The If-node index now proves
  the activated condition's typed Int32 field read through the saved comparison
  and equality return; reference/byref ABI, owned control and frame restoration
  are checked. Trunk playback and NPC selection now use typed ordinary-path
  claims, including the selected object, getter and stored-index joins. Timeline
  authenticates the selected binary hashes and displayed method identities
  against that evaluation, then rechecks native and reader inputs before return.
  The current Branch dispatch reserves its own ID only before a nonfinal item.
  A checked normal scheduler fragment replaces the current cursor with the
  action's next ID when its reservation is negative; otherwise it stores the
  reserved ID and retains the next ID for the following path. These components
  do not establish an automatic Branch default-next continuation after the
  final child. Whole executor origins, push/pop paths and error exits still
  need proof before changing the withheld sequence projection.
  The current dialog-branch claim separately proves first-match selection:
  a null condition selects its arm when reached; otherwise activation precedes
  the typed True-result comparison. No matching arm returns ordinal zero.
  The complete selector and SafeCount clone are checked with their declared
  contexts, and Story marks the null arm as unconditional only when reached.
  Action-sequence admission remains withheld: item dispatch, reservation and
  index reset do not themselves prove scheduler resumption at ActionBase.nextId.
  Their owning loader is
  [`story_native_consumers_native.py`](../../scripts/game_data/story_native_consumers_native.py).
- A generated artifact made on one build is current only when its recorded
  native hashes equal the installed build's. The reverse-PPtr audit (Story
  root playback aliases) and `webui/story/dynamic_scene.json` were made on the
  previous build and publish nothing until regenerated. The reverse audit
  regenerates through `scripts.webui.story_recovery.audit_story_objects` after
  an export published with `--animestudio-object-index`; `dynamic_scene.json`
  has no generator (see `scripts/webui/story/dynamic_scene.py`).
- Mission Pipeline `RUNTIME_CONTRACT` rows are re-verified by name each run
  (`scripts/webui/mission_pipeline/runtime_contract_native.py`); a row whose
  chain no longer holds is `link_failed` and needs a fresh reading, not a pin.

## Current mission JsonData carrier boundary

The selected VFS ledger and exported `game/Json` bytes agree for the active
LevelScriptData, LevelData, LevelConfig, SpawnerConfig and MissionRuntimeAsset
families; that direct comparison is needed because the export lacks
per-output provenance, so `verify_export_freshness` alone cannot authenticate
every file's content.

- Changed LevelScriptData, LevelData and SpawnerConfig files close at physical
  EOF with `levelscript_binary.frame_levelscript_declared_root` and declarations
  derived from the matching installed native build: the byte boundary is
  complete, member names stay `direct`. Changed LevelConfig files close under
  `decode_level_config`. Both MissionRuntimeAsset main and meta sets pass their
  named schema readers (`scripts/game_data/schemas/mission_runtime_main.py`);
  the current-corpus gate authenticates both readers and the selected file set.
  The schema contract carries no generated corpus receipt.
- The source path chain is LevelConfig's signed `levelDataPaths` int64 -> the
  authenticated `StringPathHash.bin` bucket/path-offset pair -> active LevelData
  logical path. LevelData `levelScriptBriefDataDict` stores a `dataPath.hash`;
  a unique catalog path plus equality of its dictionary key, embedded
  `scriptId` and LevelScriptData filename stem proves that script reference.
  `spawners[].configId` matches the SpawnerConfig root `configId` and path.
  These are JsonData source-path and typed-id joins; Unity CAB/PathID identity
  applies only when crossing into serialized Unity objects, and a filename
  resemblance alone is insufficient.
- Mission name and description keys resolve directly in the byte-verified
  `TextTable`; matching Dialog prefixes are candidates until a typed
  mission-to-dialog field connects them. A level field, a mission name in a
  LevelData filename, script brief, condition, or `mainPathQuests` array proves
  authored definition or reference, **not** client activation, a server quest
  branch, or a played Story. Producer-to-mission ownership and activation
  order stay unresolved until an exact consumer trace or observed runtime event
  joins them; the source joins never become a Story edge or order on their own.

## Shared mission state and condition connections

[`mission_shared_native.py`](../../scripts/game_data/mission_shared_native.py)
re-evaluates the reviewed named claims in
[`mission_shared_native.json`](../../scripts/game_data/contracts/mission_shared_native.json)
against explicitly selected assembly and metadata paths, with input gates
before and after evaluation. Its bodies are limited to exact `.pdata` extents
and unwind-owned fragments; unnamed helper bytes do not silently supply a
callee. Field predicates match offsets, not typed receivers or complete control
flow. The typed chains below also rely on reviewed instruction and metadata
evidence. All behavior describes native default paths: live IFix selection,
server policy and unvisited runtime execution remain unresolved.

The working model separates authored eligibility and action graphs, delivered
quest/mission state, locally selected condition evaluation, objective
presentation, and playback requests. A mission timeline records their explicit
identity-bearing entries within one admitted interval. Stored dependencies
explain candidate handoffs; received state records observed progress; local
conditions are one selected evaluation lane; UI counts are presentation. None
of these carriers alone establishes the server's decision or playback owner.
The retained marker and photo paths corroborate this separation: a non-client
marker objective advances without the selected local leaf callbacks, while a
photo payload reaches several explicitly owned conditions with different
authored group operands. Quest IDs and source membership select the mission;
shared names, reused condition IDs and clock proximity do not.

The reusable
[`mission_mechanism_audit`](../../scripts/webui/story_recovery/mission_mechanism_audit.py)
sweeps named-schema-validated objective condition trees in a selected export.
`ConditionSelectors` in `mission_shared_native.py` follows concrete metadata
inheritance and registered generic parent contexts to the nearest declared
`get_conditionType`. Only a unique instance virtual getter in the base
condition's slot can join a reviewed, authenticated enum-return claim. A nearer
unreviewed override withholds the inherited selection. This establishes
conditional applicability of a default selector, not a specific `Check` body,
live subtype, IFix choice or server rule. Generic parent binding supplies no
closed field layout or instantiated body by itself.

The reviewed `commonConditionSelectors` claims cover named getter overrides
through the selected objective census, using complete typed enum-return
paths after `IsPatched` returns false, rather than accepting a nearby EAX
literal. Server placeholders return the declared `None` sentinel; arrival,
quest-state, mission-state and interactive-integer families return their own
named non-`ClientOnly` enum members. The default Mission objective leaf lane
therefore excludes them. This does not prohibit their condition classes from
having local methods or being used by another subsystem. Combined objectives
return `Combined` and recurse into children; a container is not a failed or
server-only leaf. These distinctions explain missing selected local callbacks
without inventing a missing progression event or a server predicate.
An export whose families all join these getters has closed default-selector
coverage only. The census does not prove the specific predicate bodies, actual
activation, server evaluation, or a fully observed timeline; a future family or
nearer getter still remains unreviewed until its own claim is checked.

The audit separately counts entries associated with a quest containing a
condition family and entries naming one uniquely owned condition. Association
requires explicit quest identity, matching selected-native profile hashes and
identical retained/current mission-definition bytes. A condition referenced by
an operand does not become the condition's owning quest. This is a selected
export census and retained-interval coverage, not installed VFS completeness.
Main-path lists are subsets of the authored dependency graph; branches,
multiple predecessors and off-path quests cannot be flattened into one total
timeline merely because a source array has an order.
The audit retains quest/mission-state operands with their owning objective,
comparator and requested state. The reviewed `questMissionStatePredicates` and
`combinedConditionAst` groups join selected native enum names and checked
consumer flow to these operands. A referenced quest or mission remains a
constraint target, separate from the objective's owner. Dynamic operands remain
unresolved. The generated Boolean model distinguishes a condition required to
be true, one required to be false, and an alternative. Its conclusions assume
live parameter initialization, successful native helper/context behavior, stable
child results and coherent nested combined caches. A separately authenticated
parser review enables the bounded ASCII native caller model, including mixed
binary operators; without that review the earlier unambiguous model remains
the fallback. Objectives are modeled individually; the audit supplies no
quest-level combination rule or accepted timeline edge.

[`mission_expression_native.json`](../../scripts/game_data/contracts/mission_expression_native.json)
records the reviewed parser/resolver bodies and typed state-publication joins;
[`mission_expression_native.py`](../../scripts/game_data/mission_expression_native.py)
authenticates their owned bytes, declarations, literals and actual usage cells
against selected native inputs before and after evaluation. Its caller review
is distinct from the small symbolic instruction proofs below and from live
source-to-object parity. The reusable
[`mission_expression.py`](../../scripts/game_data/mission_expression.py) model
implements these reviewed ASCII rules:

- The lexer lowercases the string, skips only space and tab, scans `not`, `and`
  and `or` without requiring word boundaries, and accepts braced ASCII digits
  through Int32 parsing. Culture-dependent Unicode behavior is withheld.
- Immediate stack reduction gives AND and OR equal precedence and left
  associativity: `A or B and C` means `(A or B) and C`. NOT reduces on its next
  completed subtree; an incomplete parenthesis blocks reduction until closed,
  and pruning removes the grouping node.
- Parsing requires exactly one completed root and a contiguous distinct index
  set starting at zero. Repeated indices are allowed. Parsing receives only
  the expression; reviewed activation does not require every supplied child
  to appear in it. The bounded source model additionally refuses child indices
  outside the supplied array. The outer evaluator still waits for unused
  children; the audit records decision-wait inputs separately from expression
  inputs.
- State activation passes each typed Param, the type's default value, and the
  true option into `GetValue`, caching the resulting ID, comparator and state.
  The source-zero `TryGetValue` path copies its typed constant and succeeds
  before getter/blackboard dispatch. Getter sources with the sentinel ID return
  the passed default. Actual caller MethodSpecs establish string/comparator/
  state types; a generic shared reference or enum body alone cannot do so.
  Generated named wrapper setters establish concrete Param cells without
  importing open generic field offsets.
- Source-selector leaves now have complete equality-only Int32 programs checked
  against their selected registered representations and a concrete source-cell
  witness. The checked memberships distinguish getter references, bound
  blackboard/temp variables, action/self/config/save/server sources and current
  context IDs. Membership does not prove that every named source is implemented
  by every resolver. In particular, a current-mission selector is not an
  offline mission-ID value or an ownership join.
  The reviewed reference resolver calls the bound-variable getter for its
  blackboard/temp lane, and its getter-reference lane uses ActionContext plus
  the reference ID, with raw-getter/conversion fallback after a failed typed
  lookup. Its path lane calls the nullable cached runtime-path resolver,
  PropertyPath lookup/concatenation and selected blackboard consumers. A stored
  path is therefore insufficient to select the live blackboard or its value.
  Null Params, sentinel getter references and failed TryGetValue resolution
  select the supplied GetValue default; keep those outcomes distinct from
  successful queries. Actual bindings, getter registry, context owner, rewritten
  path, provider values and returning delegate effects remain live joins.
  Static RGCTX MethodSpec-index candidates are withheld; static definition
  records are not runtime MethodInfo slots.
- Selected ordinary value constructors explicitly store source zero, a null
  path, the sentinel ID and the supplied constant. The reference barrier is a
  returning helper assumption. Typed MemoryPack wrappers allocate and install
  a Param, then a full deserialize reads constant, reference ID, source selector
  and path in that order. A null header clears the wrapper; a nonnull header
  must contain all four properties. Fresh and reused objects therefore receive
  an explicit serialized source, rather than a partial-header omission default.
  Buffered reader/refill effects remain conditional.
- Mission resource loading includes TextAsset JSON and ResourceManager paths.
  Formatter availability selects a MemoryPack or JSON reader, and the
  MemoryPack caller also contains a JSON fallback. Default JSON settings do
  not identify the Param creator or the result of setting an omitted member.
  These paths and constructors cannot identify which live instance a source
  constant created. Source-to-object ownership, effective patches and the
  source actually consumed remain runtime joins.
- Uncached quest ownership uses the prefix before the first ordinal `_q#`
  delimiter, or an empty string when absent; a quest-ID cache wins first.
  Agreement with exported ownership can be audited, but this lookup contains
  no chronological or server-admission rule.

[`mission_condition_flow.py`](../../scripts/game_data/il2cpp/mission_condition_flow.py)
checks complete admitted instruction programs for the following default paths,
binding named fields, enum members, call signatures, branch targets and
unwind-owned regions. Collection/getter bodies, general closed event-packet
layout, actual objects and live IFix choices remain separate obligations.

- Quest and mission callbacks filter the incoming packet's identifier lane by
  the cached configured ID. Only the matching path passes its incoming state
  lane, cached comparator and target to the Int32 comparator, then passes a
  normalized `False` or `True` to the result setter. They do not re-query current
  state. The selected comparator supports equality, inequality and signed
  ordered comparisons. State integers form a comparison domain, not a
  chronological order of mission events.
- Activation resolves parameters and checks existing client state as well as
  binding a state-change callback. Quest activation binds before its query;
  mission activation compares existing mission data (or `None` when absent),
  sets the result, then binds. A bounded walk of every completing default
  control path verifies these critical call sequences after the false patch
  guard, including the quest predicate's result-setter tail return. It follows
  branches rather than native address order. Callees are returning opaque
  boundaries; actual
  parameter initialization, subscriptions and delivery remain open. The
  condition classes retain their non-`ClientOnly`
  selectors, so this does not establish execution in the default Mission
  objective leaf lane.
- Default objective setup and direct combined activation are different routes.
  The complete ordinary GameCondition objective initializer returns without
  effects after its false patch guard; CombineCondition and its intervening
  base declare no override. The checked initialized/non-null combined client
  activation loop dispatches on children only: exact combined children recurse,
  and other children require ClientOnly. It does not activate its own receiver,
  parse its AST or write parent pointers. This is a caller-flow claim under
  returning collection/virtual helpers and default recursive selection, not a
  global claim about callee effects, patches or live receivers. It explains why
  a Mission composite can receive copied objective progress without activating
  local quest-state predicates or entering the guide-style result AST lane.
- There is also a lazy progress AST route. The checked non-null default
  CombineCondition.GetResultByProgress caller parses conditionEvalString when
  its AST is invalid, then evaluates rootNode with useProgress=true. It has no
  outer all-child-result waiting loop or own result-setter call. The separately
  checked valid-node progress evaluator keeps NOT/AND/OR recursion and short
  circuits but dispatches visited leaves to virtual GetResultByProgress,
  instead of testing cached result == True. Returning getters, valid helper
  contexts and parser/evaluator success remain conditions; exception/patch
  paths and live ownership remain separate. Thus an AST may be used for a
  progress check without predicate activation, subscription, parent callback
  publication or a quest-state transition. Absence of activation hooks alone
  cannot exclude this route. The retained daily contains no owned invocation
  of it; future recipes now retain its own paired observer.
  The complete ordinary base GetResultByProgress caller separately passes
  virtual comparator/progress/target returns into the typed Int32 comparison.
  It does not read the cached result or query a quest/mission identifier.
  Overrides, getter effects and the provenance of those progress values remain
  separate; a Boolean progress check cannot identify a state-event callback.
- Exported source context supplies explicit current-mission selectors in
  mission-property checks, including stored failure branches. The reviewed
  Int/Bool property classes derive from GameConditionServer, declare no local
  OnActivate/GetResult/client-activation overrides and select CheckMissionProperty,
  distinct from ClientOnly. These stored nonconstant operands therefore do not
  supply a default client state-Param capture case. The new source inventory
  found no explicit nonconstant operands in its quest/mission-state predicates;
  omitted JSON selectors stay omitted, rather than becoming proved live zero
  values. Neither a dormant server-family operand nor a nonempty path beside a
  stored constant is evidence of a nonconstant live read.
- A new useful capture must distinguish the activation-time query/result from
  a subsequent matching event, and bind receiver, owning quest/mission, live
  operands and nested callbacks to one invocation. Entry timestamps alone
  cannot establish subscription success, a completed result update or parent
  quiescence. The concrete requirements live in
  [the shared runtime backlog](../runtime_capture_requirements.md#mission-timeline).
  Further collection/allocator review may refine conditional value transfers;
  it cannot supply an omitted event interval or authoritative server admission.
- The focused
  [state/AST capture recipe](../../scripts/game_data/contracts/mission_state_trace_capture.json)
  now prepares live typed Param cell snapshots at state activation entry/return
  and cached resolved operands separately. Its EventData argument witness
  proves sequential string/Int32-enum layout and the Windows x64 indirect
  aggregate transport. It does not claim complete callback evaluation. Passive
  Param cells come from the current named generated setters through
  `capture_closed_cells.json`, separately from serialized-source transfer and
  the expression evaluator's stronger native contract. Unique GP-only
  void/Boolean observers retain explicit
  same-thread invocation/parent identity through recursive AST calls, result
  setters and selected callbacks. Offline inspection/decoded replay retain
  incomplete/crossing-pair constraints. The refactored runtime keeps observation
  bounds and callback cleanup, while collection now inventories raw files
  without certifying their contents.
  These are prepared observations, not live evidence. They do not sample each
  resolver instruction, enumerate unused children, establish JSON initialization,
  authenticate a subscription handle or make nested cache updates atomic.
- The additional
  [daily capture recipe](../../scripts/game_data/contracts/mission_daily_trace_capture.json)
  retains those AST/state hooks alongside selected interactive/photo, SNS,
  script and action entries. Its current preset retains all available mission
  definitions, including the distinct stored `m1m42` interactive variant and
  photo variants such as `m1m39` and `m1m61`; reused labels do not select a
  runtime variant. These definitions contain no quest/mission-state
  predicates, so recording these tasks cannot by itself close the live state
  Param gap. Selected pre-run exports are copied as source context, with source
  freshness, omitted dependencies and live instance ownership left separate.
  The three-target tracking variants instead store a combined objective over
  sibling quest-state predicates; their expression and condition unique ID are
  shared across different mission IDs. HUD target count can help choose a
  recording route, but neither that count nor the shared condition ID selects
  the runtime definition. Capture the sibling completions and final handoff
  continuously, preferably in a different freely selectable order, and keep
  mission-owned progress AST execution conditional on actual observed calls.
  The stored `m1m61` photo route has one quest, no predecessor and no mission
  action-map entries. It supplies a second identification-group case for the
  shared photo consumer, rather than a multi-quest handoff or dynamic-Param case.
- Current paired observations close a constant-activation example for
  `CheckQuestState` in an AST with source label `_InitGuideGroupCondition` and
  no owning quest ID. Distinct live Param objects retain source zero, `idRef`
  minus one and empty paths; the resolved ID/comparator/target cache changes
  from its entry defaults to the configured constants at return. The observed
  `e1m6_q#5d2 / NotEqual / Completed` case yields a False result. This does not
  expose the queried quest-state value, the individual resolver instructions,
  nonconstant selection, subscription handles or JSON construction.
  No matching state-change callback is recorded: an activation-time result
  must not be treated as the time of a quest handoff.
  The state's stored parent pointer matches the enclosing CombineCondition
  receiver in that invocation. Parse fills its previously null root; nested
  result setters trigger parent evaluations, and one AND traversal returns
  after index zero yields false without entering the remaining leaf indices.
  This is consistent with the reviewed waiting/short-circuit rules. A node's
  `completed=true` coexists with a false Boolean return; that flag cannot stand
  for condition truth, objective completion or mission success. Guide-labelled
  AST evidence must not be attached to a Mission objective without an owner join.
- The current daily trace contains `m1m46`, whose current definition reuses
  `m1m42_name`, rather than a lifecycle for the distinct `m1m42` variant.
  Its observed local handoff starts the combined quest and sibling quests
  after the predecessor succeeds; sibling success order differs from start
  order. The composite's incoming objective-handler intervals enclose copies
  receiving false, false, then true, with the final normal return retaining
  a changed completed cache. Later quest-state handlers separately enclose
  composite success and successor start. This binds individual copies and
  lifecycle calls to explicit incoming handlers; it does not turn earlier
  quest success into the enclosing cause of a later handler or reveal the
  server's dependency decision. No mission-owned AST/state-leaf invocation was
  recorded for that composite. Its definition was absent from the selected
  pre-run sources; current-export context cannot repair that omission.
  The maintained preset now snapshots all mission variants to avoid repeating
  this display-name/source-selection gap.
- A current `m1m39` photo notification encloses a matching GetResult entry,
  the result setter and its nested Mission progress callback. The setter's
  normal return retains True. Base deactivation later enters with True, while
  the subclass deactivation and base normal return retain Undecided with
  progress one: teardown resets the result before the subclass callback.
  Thus a deactivation-time Undecided value is not evidence of failed photo
  identification. The GetResult entry remains unpaired; notification and
  setter enclosures do not add an observed GetResult return.
  These are local-file analyses of the refactored collector, distinct from
  admission of older hash-bound captures. The reusable inspector's explicit
  `--local-files` mode checks row accounting, field programs and call pairs
  but writes an analysis schema and refuses to imply legacy replay admission.
- `GetQuestState` first returns a nonnull current quest record's state. When
  that record is absent, its normal caller uses `GetMissionIdByQuestId` and a
  mission dictionary lookup: a completed owning mission yields quest
  `Completed`; an absent/empty owner ID, missing mission or another mission
  state yields `None`. The existing quest record takes precedence over this
  fallback. The returned owner ID and dictionary results are successful-callee
  assumptions, and expanded patched paths remain excluded. This explains how
  a state predicate can match restored state or a completed mission without a
  new quest-state event inside the recording; it supplies no missing handoff.
- The valid-node `_EvaluateNode` path with `useProgress=false` compares a leaf
  result exactly with `True`, flips Boolean values for `Not`, and short circuits
  `And` and `Or`. Its leaf projection treats `Undecided` as false. The outer
  `Evaluate` loop first waits on every null or `Undecided` child before invoking
  that AST path, including children the expression does not use. Consequently
  an OR alternative cannot bypass the outer waiting gate, and the inner NOT
  projection alone does not establish a resolved combined result. An undecided
  combined cache forces a setter call after evaluation; an unchanged decided
  Boolean result skips it.
- The normal result setter accepts updates only while active, rejects incoming
  `Undecided`, and skips unchanged values. A changed decided result is cached
  before the callback helper, then a nonnull parent is evaluated. The callback
  helper is assumed to return; its purity is not proved. Reentrant callbacks or
  child/parent mutation prevent promoting this local propagation rule into
  atomic nested-cache coherence.

The reviewed state producers add local publication relationships. Normal quest
updates create/add or overwrite the current quest record before their state-case
`StartQuest`/`SucceedQuest` calls and global state-change send. Normal mission
updates build and publish their new mission record before the availability,
start or completion branch. Completion show-data, processing-membership and
property helpers can run earlier, so these relationships do not describe whole
handlers as atomic operations.

Producer calls select a string ID plus the appropriate state enum; condition
subscriptions select the matching closed event type and named event key. The
selected compiled sender writes reference/Int32 packet lanes and passes the
packet address through the dispatcher and binding into synchronous delegate
calls. Its compiler helper includes a specialized quest-state callback branch.
These are compiled representation and caller/context joins, not a general open
generic layout proof. Dispatch follows runtime registration/list state, and
callbacks may reenter or alter it. Actual subscriptions, runtime generic context
resolution, helpers, exceptions and patches remain conditional. A later state
query can consequently see published data without proving that all listeners
or combined caches have been refreshed.

These constraints explain eligibility and delayed evaluation, while explicit
received state and owned runtime entries establish observed handoffs. Positive
completion predicates may already hold when an interval begins; negated checks
and OR alternatives need not impose a positive predecessor. Main-path membership
and a satisfied state check therefore cannot fill an unrecorded transition or
flatten the authored dependency graph into a complete timeline. Current offline
inputs cannot recover an event outside their retained intervals, identify an
unobserved effective patch/receiver/subscription, or reveal authoritative server
admission. Further collection/allocator/helper analysis can refine conditional
native semantics but cannot manufacture these missing chronological facts.

- Mission quest state, objective progress, and LevelScript task state use
  separate message paths. `MissionSystem.Handle_QuestStateUpdate` reaches
  `StartQuest`/`SucceedQuest`; `Handle_MissionStateUpdate` reaches
  `CompleteMission`. Objective updates copy `ObjectiveData` and refresh
  progress. Runtime `ObjectiveData.Copy` callers distinguish logic and display
  destinations in both initial synchronization and later updates; duplicate
  copies of one incoming condition are not independent completion messages.
  Its receiver fields are before-copy snapshots, so a missing old receiver ID
  does not erase the explicitly observed incoming ID.
  Tracking data identifies navigation/presentation targets and does
  not replace a completion condition. These consumers do not establish a
  Mission quest-to-LevelScript task owner.
- `MissionSystem.OnSubConditionProgressChanged` retains an explicit quest
  argument even when the supplied condition's stored `parentQuestId` is null.
  Retained quest definitions can independently locate that condition within a
  combined objective. Restoration observations include a supplied progress
  value that differs from the pre-entry progress cache, followed by another
  request for the same quest and condition with a different supplied value.
  Preserve argument and cache separately; neither callback counts nor their
  values alone identify player actions, incoming objective-map contents, or
  acknowledged server progress. Stored condition types do not authenticate
  the receiver's runtime subtype. Advanced-progress UI refresh remains a
  separate path.
  Active identification evidence now includes `m1m70_q#2`: `StartQuest` enters
  with `isNewQuest=true`, and a later callback supplies progress `1` while the
  pre-entry progress cache is `0`. The explicit quest and stored parent agree;
  archived quest/objective membership selects `CheckSnapshotIdentifySuccess`,
  rather than its reused condition ID alone. Later deactivation retains a
  `True` result and progress `1`; separate carriers record quest success and
  mission completion. These are separate named entries and cache
  snapshots, not a reconstructed request/reply pairing.
- Default Mission client activation and result-callback binding select leaves
  whose virtual `get_conditionType` returns `ClientOnly`. Combined objectives
  recurse into exact `CombineCondition` children and apply that selection to
  their leaves. `MissionSystem.IsServerCondition` classifies the other enum
  values as server conditions. `GameConditionBoth` inherits this activation
  selector; its name does not mean both implementations execute for every
  quest. The symbolic enum/getter checks re-resolve the selected metadata and
  bounded dispatch helper. Their predicates check instruction relationships;
  branch meaning also relies on the reviewed bodies, and does not identify a
  live receiver, IFix replacement or authoritative server rule.
  Photo/identification objectives (`CheckSnapshotIdentifySuccess`) inherit
  `GameConditionClient`, whose default getter returns `ClientOnly`; they are
  now represented by a retained active callback as well as source evidence.
  The admitted restoration and active identification calls share an
  authenticated return into a Boolean delegate specialization: it widens the
  Boolean argument to the supplied progress integer and resolves the Mission
  closure's quest and condition.
  The reviewed default `GameCondition.set_result` path supplies whether the
  changed result equals `True`. These observations therefore demonstrate a
  Boolean-result bridge, not arbitrary numeric counters. The caller witness
  does not reconstruct every earlier frame or select an IFix branch.
  Identification group IDs must be distinguished from an entrust's snapshot
  preset: the mission condition's group joins `SnapshotIdentifyGroupTable`
  to target IDs, then the base and target-family tables supply stored target
  requirements. A sphere-family target can describe an empty interactive
  template rather than a named tree entity; localized scenery does not prove
  its live entity identity. The capture recipe now retains named group
  registration/notification entries and snapshot-condition lifecycle/callback
  context and the callback's supplied string group ID. The closed
  `EventData<string>` layout is proved from its selected generic container,
  sole instance type-parameter field, sequential layout and default class
  size. Open-generic native size/offset rows are placeholders and must never
  supply closed-instance offsets. Layout does not establish argument passing:
  the selected snapshot callback receives this eight-byte value indirectly.
  Preparation separately proves the entry argument's zero-offset pointer load
  reaching a named string comparison, retaining register identity across calls
  and control-flow joins. A small native equality wrapper is followed only
  when it preserves both string arguments and reaches the named two-string
  comparison. Missing or changed proof rejects preparation. An earlier inline
  read failed in a live photo callback; its failed journal remains diagnostic
  evidence and cannot be admitted as a complete collection. Together, layout
  and passing proofs enable a payload-to-condition entry association. A clean
  retained photo run now observes the supplied group at several explicitly
  owned `GetResult` entries: the `m1m32` group also enters the active `m1m70`,
  `m1m71` and `m1m31` conditions, whose stored groups differ. The later `m1m31`
  group likewise enters other active photo conditions. Only the quests whose
  archived group matches have retained progress-one callbacks and completion
  entries in that run. This admits the repaired payload read and demonstrates
  why neither the reused condition ID nor entry occurrence selects the
  completed quest. The match compares stored constants; the live bound group
  parameter, actual `GetResult` return, IFix selection and event nesting remain
  unobserved. Base deactivation retains `True` with progress one before a later
  specialized deactivation retains `Undecided` with the same progress. Keep
  those separate cache snapshots; neither is an earlier callback return.
  `InteractiveCheckInt` is a server-condition family, with no declared local
  event-check lifecycle. Named interactive state requests, integer property
  callbacks and incoming packet identities provide separate carriers for its
  investigation. Old/new callback arguments are supplied values, not proof of
  a blackboard write; stored EntityPtr logic IDs, entity server IDs and packet
  IDs must stay distinct until an explicit join is established. Incoming
  property/objective maps and server completion rules remain unresolved.
  The reviewed `interactivePropertyDelivery` claims identify the default
  packet path through `EntityManager.ServerSyncInteractiveProperty` to
  `InteractiveInfo.UpdateServerProperty`, including only unwind-owned native
  fragments. The consumer reaches the retained server-data property blackboard
  and has a separate loaded-entity blackboard branch. An absent
  `InteractiveRootComponent.OnInteractivePropertyUpdate` entry therefore does
  not establish absent property delivery; this default-body distinction does
  not identify the branch executed in an earlier session.
  Conversion reads the wire parameter's real/value type selectors and integer
  list storage. A list field is not a concrete scalar value, and unproved
  generic value-field offsets cannot establish a closed numeric layout. The
  blackboard setter's named dictionary lookup is validated; its remaining
  mutation helpers and existing-value behavior still need their own proof.
  The capture recipe separately retains the property consumer's stored
  entity-data ID, level, template, parent script and generation alongside the
  supplied packet identity, and the navigation consumer's supplied signed
  old/new state arguments alongside its explicit entity argument's stored
  server/level/script identity. These are entry associations, not applied
  writes or authoritative Mission child values. Default navigation dispatch
  is conditional and precedes blackboard setter calls; observed ordering alone
  cannot establish nesting or causal ownership. Incoming Mission objective
  dictionaries remain a separate carrier from both property blackboards.
  The clean marker/photo run now admits both retained-data and navigation
  entries. The consumer's stored ID and level agree with its supplied packet
  within each observed entry, and marker-related entries retain the authored
  script as their parent. Navigation supplies old state zero and new state one
  for those runtime entities. That parent-script association does not map a
  dynamic server ID to an authored local interactive key or a particular marker
  Boolean property, and the supplied states still prove no applied write.
- `StartQuest` distinguishes restoration from a newly entered quest. The
  world-ready restore path passes `isNewQuest=false`; the quest-state update
  path derives the flag from the prior state. A method entry alone cannot
  identify a new progression. Client lifecycle phase dispatch uses the exact
  `(questId, QuestAction)` pair in `MissionRuntimeAsset.runtimeClientActionMap`,
  reconstructed from matching key/value array positions. A missing key returns
  without an authored ActionMap action; a hit forwards the stored start-node ID
  to `ActionMapAsset.RunAction`. Other script or server effects remain possible.
  An observed null ActionMap key does not mean the phase map is empty: explicit
  mission/start-node carriers and authenticated caller sites can still retain
  its dispatch into an embedded action map.
  Daily variants can share a localized title, root condition IDs and radio
  assets while selecting different scripts and start nodes. Identify the
  observed variant through explicit mission/quest carriers and the retained
  definition; neither the visible title nor a reused radio ID selects it.
  A condition ID alone is not a globally unique mission owner.
  Mission completion observations include the incoming mission-state carrier,
  `CompleteMission` with its supplied succeed ID, and the corresponding
  `Processing` to `Completed` state-event arguments. Cleanup can revisit
  explicitly owned conditions from earlier quests with zero entry progress
  caches. Such deactivation entries are not new quest failures or recomputed
  condition results. A subsequent mission's availability and acceptance need
  their own identity-bearing notifications; adjacency does not establish its
  unlock dependency or reward credit.
- Objective presentation has a separate numeric consumer. The default
  `ObjectiveData.GetValue` supplies its stored condition ID and values
  dictionary to `CollectionExtensions.GetValueOrDefault`. The reviewed
  `Copy` body clears and repopulates a destination dictionary from the incoming
  objective map. Its complete normal caller grammar now checks source aliases,
  selected fields, argument lanes and loop control; collection/helper semantics
  and live map members remain separate. Preserve the incoming map, the copied
  completion flag and the displayed count as separate carriers.
  `CombineCondition` presentation getters sum each child's numeric presentation
  value or target. For an `Objective` displaying a multiple combined condition,
  the default progress getter instead counts children whose
  `GetResultByProgress` comparison passes; its target is the child count.
  `GetResultByProgress` compares current progress with the configured target
  using the virtual comparator. It does not read the cached condition result.
  A single combined condition uses a completion-based presentation; an explicit
  display condition and advanced progress have separate branches. Completed
  objective show data can present its target as progress. These default paths
  explain how partial counts can appear without a per-child Mission callback;
  they do not identify the numeric values delivered in a retained session or
  establish the live IFix branch.
  The reviewed `ObjectiveData.Copy` claim now checks a packed argument transfer
  beside a named `Dictionary.Add` call. The exact passed MethodSpec selects
  String/Int32; a shared Object specialization is insufficient. The complete
  vector program passes its low pointer-sized component as the key and the
  next Int32 component as the value. This closes the argument-split question
  that the subset disassembler left unread. The separate
  [`packed_pair_current`](../../scripts/game_data/il2cpp/packed_pair_current.py)
  claim checks the complete owned producer helper and adjacent caller window.
  Reciprocal generic-parameter ownership joins a selected closed
  `IEnumerator<KeyValuePair<K,V>>` to its slot-zero `get_Current` return. This
  type join is independent of field layout and argument passing. Complete owned
  helper grammars cover String/Int32, String/`Proto.QUEST_OBJECTIVE_DETAIL` and
  UInt64/Boolean contexts, including their post-return fast-path tails and the
  caller-supplied TypeInfo variant. On matching-interface dispatch each helper
  invokes the getter with its supplied receiver and copies a 16-byte return
  window. The separate String/Int32 window proves its components reach the
  selected `Dictionary.Add`. The complete
  [`mission_objective_copy`](../../scripts/game_data/il2cpp/mission_objective_copy.py)
  grammar now binds all normal Copy loops: values are cleared and enumerated,
  the root completion flag is copied, then extra details are cleared and each
  incoming detail supplies a newly allocated `ConditionDetail`. Its nested
  hash loop finishes before the outer detail is added. Typed fields and passed
  MethodSpecs bind each source map and destination; complete interface searches,
  current helpers, backedges, false exits and normal cleanup control are checked.
  The nested hash loop passes unchanged low-64-bit return-window arguments from
  its UInt64 context to a signed Int64 Add context without caller arithmetic or
  a range check. This is a bit-transfer proof, not a recovered wire value or a
  closed generic pair field-layout proof.
  The caller grammar also checks its usage-initialization instruction stream,
  incoming nonvolatile aliases and matching stack restoration. Its claims
  require unpatched dispatch, normal usage/class resolution and Win64 ABI,
  valid objects/interface tables/current returns, successful allocation,
  collection and cleanup calls, and no external alias mutation. Initializer,
  fallback, enumerator, collection and cleanup helper semantics, exceptional
  paths, actual delivered entries, live IFix choice and quest ownership remain
  open. Neither this proof nor capture enumerates a runtime dictionary. A
  completed objective flag copied here is not a quest-state update or proof
  that a quest handoff occurred. A Copy entry alone proves neither successful
  completion of these loops nor atomic replacement of the destination.
- `CheckTalkOptionFinish` belongs to `GameConditionBoth`. Activation resolves
  and caches its dialog/finish operands, checks existing finish history
  immediately, and binds `Check` to `ON_SYNC_ALL_DIALOG` and `ON_FINISH_DIALOG`;
  deactivation removes both bindings. The corresponding CinematicSystem
  handlers populate or update the client finish-history dictionary before
  raising those notifications. A negative configured finish ID accepts an
  existing history entry; a nonnegative ID must occur in its recorded finish list.
  This can use synchronized prior history and is distinct from a UI exit.
  `SetFinishId` stores a local value and `_SendServer` forwards supplied finish
  IDs/options, but their complete cached-value/request/reply ownership remains
  unresolved. Entry observations from the typed Mission trace recipe show that
  the supplied finish ID can differ from the cached field at `_SendServer`;
  retain both instead of substituting the cache for the outgoing argument.
  On the current ordinary carrier/code-absent path, `FinishDialog` stores its
  incoming finish ID and finish type directly before tail-exiting with the
  original dialog string and stored skip byte. A `SetFinishId` hook alone
  cannot observe that inlined write. `CheckTalkOptionFinish.Check` likewise
  reads the player's cinematic history through the original getter field;
  its typed lookup, signed operand, list-membership and result paths have
  separate current body proofs. These are conditional source transfers,
  without replacement, live-history or server-success claims.
  Sends have been observed in both `Exiting` and `Exited` states through
  different callers, which does not by itself identify their branch predicate.
  Dialogue wire identities have a separate explicit join: `DataManager` owns
  `DialogIdTable`; the outgoing consumer uses `dialogStrToNum`, and the incoming
  finish consumer uses `dialogNumToStr`. The stored MemoryPack table has bounded
  dialogue/option maps and inverse maps that can be checked through EOF with
  the maintained table readers. Preserve these bytes with the capture. A
  current-source mapping can name an incoming wire ID without timing-based
  pairing, but does not correlate a particular request or expose unsampled
  finish-list contents; it is not a snapshot of the live dictionary.
  A quest configured with `CheckTalkOptionFinish` can have observed success
  and a generic condition deactivation without any entry at the selected
  type's `OnActivate`, `Check`, or `OnDeactivate` hooks. Its default virtual
  type is `CheckTalkFinish`, outside the `ClientOnly` selection above, so the
  default Mission client path explains how those specialized hooks can be
  absent. Matching authored dialog/finish operands to playback still does not
  authenticate the live subtype, IFix selection or server decision.
- `CheckLevelScriptPropertyBool` also inherits `GameConditionBoth` and returns
  the non-`ClientOnly` type `CheckLevelScriptProperty`. Its default local
  `OnActivate` resolves the map, script, property key, comparator and boolean
  operand. `_DoCheck` reads the property, assigns a comparison result and
  registers a property-change listener; `_OnEvent` compares the event value
  with the cached operand, and deactivation removes the listener. This is a
  boolean result path, not a marker counter. `GameCondition.set_result` can
  forward a boolean result through a bound callback to
  `OnSubConditionProgressChanged`, but the Mission callback binder above
  selects `ClientOnly` leaves. These bodies therefore do not prove that a
  stored script-property objective uses that callback in a live mission.
  Individual property writes, incoming objective-map entries and active
  partial progress need their own identity-bearing observations.
  Retained `m1m12_q#2` evidence separates these gaps: its archived combined
  objective checks the marker boolean properties, and its copied root
  completion flag remains false before the final true update and explicit
  quest/mission completion. The screen separately records partial HUD counts.
  No per-condition Mission progress callback is retained for that quest, so
  neither the root flag nor the screen identifies a changed child property or
  the incoming numeric count. Observed LevelScript task notifications carry a
  different script ID from the archived marker operands; their timing cannot
  establish property ownership.
  The property's synchronization consumer is also explicit: the default
  network handler constructs a script pointer from the incoming script ID and
  forwards its property map. The manager resolves that runtime; its
  `ServerSyncProperties` loop obtains the brief-data property-ID map and
  blackboard, looks up each ID, converts its value, writes the mapped key and
  recycles the temporary variable. The reviewed handler does not establish
  scene ownership from the packet's scene field. Missing maps, unknown IDs,
  failed conversions and an unresolved runtime remain distinct refusal paths.
  Complete, ledger-authenticated `LevelData` owners supply the marker scripts'
  `LevelScriptBriefData`: the marker Boolean defaults are false, and their
  numeric IDs map to the exact `bMarker1`/`bMarker2`/`bMarker3` keys. The separate
  full `LevelScriptData` graph has null property fields and only effect-save
  variables in its graph blackboard; that does not erase the brief-data map.
  Its authored actions contain marker property readers but no Boolean setter.
  These stored defaults and the native sync path establish a possible writer
  carrier, not an observed property update or the server rule producing it.
  A clean `m1m15` variant now records packet and runtime property-sync entries
  whose explicit script and level match the combined objective's authored
  operands, together with quest-owned objective refresh entries and the
  same-thread predecessor handoff. Its selected local Boolean-condition hooks
  remain unhit, and no per-child Mission progress callback is retained for
  that quest. The screen separately shows partial counts and completion.
  Anonymous root-copy entries remain unassigned despite their matching reused
  condition ID; their false/false/true completion flags cannot reveal child
  values. This closes the observed script-delivery identity gap for that
  variant, while property-map contents, numeric child values, successful
  writes and the server rule remain unresolved. Its brief-data property IDs
  come from the selected LevelData owner, not the MissionRuntimeAsset's
  separate property map or an assumed common numeric ordering.
- The retained `m1m43` gathering daily exercises the same distinction through
  an `InteractiveCheckInt` combined objective. Its archived MissionRuntimeAsset
  reuses `m1m41` display-text keys but supplies its own objective and entity
  operands; shared text does not make the mission IDs interchangeable. The
  maintained `mission_trace_inspect` verifies the package and source inventory
  before decoding the bounded recipe in
  `scripts/game_data/contracts/mission_trace_capture.json`.
  In that session the incoming interactive packet IDs match the five archived
  operands, while copied combined-root completion stays false through partial
  HUD advances and becomes true at the final update. Explicit quest-state,
  successor acceptance and mission-state entries complete the observed path.
  This is a case-specific packet-ID/operand match, not a universal equivalence
  between logical IDs and server IDs. No Mission subcondition-progress entry
  names the gathering quest, and neither selected interactive property callback
  nor state-request hook fires. The network hook observes identity fields only:
  delivered property values, applied writes, incoming objective numeric values
  and the selected live consumer remain unresolved. Adjacent packet/objective
  entries and independently visible HUD counts cannot supply those missing
  payloads or causal ownership. The default Server condition selection is
  consistent with the missing local callbacks; absence alone proves no live
  subtype, IFix choice or callback failure.
- `GetScopeMask` uses the virtual force-override tuple when enabled, otherwise
  the authored scope mask; `GetUseGraphScope` reads the authored graph flag.
  Named `ScopeName` flags describe the stored scope domain. These selectors
  do not establish the effective current or graph scope, script availability,
  or condition execution admission.
- `CheckActivityConditionalStageStatus` and `GameConditionServerPlaceHolder`
  inherit the server-condition lane and declare no local `Check`; the activity
  class also declares no activation override. Activity-stage descriptions and
  block-condition admission are configuration consumers, not proof of a local
  stage-state query. Placeholder conditions can compare delivered progress
  locally; the client does not reveal the server criterion that produced it.
  Keep authored stage/comparator/threshold parameters, received progress, and
  authoritative completion policy as distinct evidence. Condition lifecycle
  entries can retain progress equal to the threshold while the cached result
  remains `Undecided`; these snapshots do not observe a `Check` return or prove
  that a local comparison produced `True`.
  Activity configuration supplies a separate stored dependency join:
  `ActivityConditionalMultiStageTable` associates stage, mission and time keys;
  its condition and stage-owner tables retain explicit predicates, while
  `TimeRangeTable` retains candidate opening/closing ranges. A named
  `MissionStateEqual` predicate can establish the configured prerequisite
  independently of adjacent runtime notifications. It does not prove server
  evaluation, the selected range/timezone, or the actual unlock instant.
- LevelScript local condition changes send script/task/condition identity and
  absolute progress (`isAdd=false`). Incoming task-state messages apply task
  state through manager/runtime/task-runtime consumers. Separate condition maps
  look up condition IDs, update `TaskCondition.isCompleted` and invoke its
  completion delegate inline; a hook on the named invoker alone misses this
  path. `TaskCondition.OnTaskStateCompleted` disposes the condition rather than
  writing that flag. The native default `UpdateLevelScriptTaskStartFinish` path
  is a no-op, while script-done synchronization follows its own state update.
  The typed `UpdateTrackingObjectiveCompleted` entry is shared tracking
  behavior: captures include both setting and clearing completion, including
  clearing calls without an intervening observed progress-message handler.
  Its objective-kind argument is not a condition-map key; it does not expose
  unchanged map items or uniquely identify the source condition.
  Neither task IDs nor temporal proximity supply Mission quest ownership.
  Registry packet fields use the current PascalCase C# property names,
  joined to their field-number constants and backing storage. Mission Pipeline
  checks those names exactly; older camelCase spellings are not aliases.

The reusable entry/field declarations are in
[`mission_trace_capture.json`](../../scripts/game_data/contracts/mission_trace_capture.json).
Interpret their observations with the session's retained profile and explicit
source identities; entry snapshots do not prove successful returns or message
causality. Capture inventories and sequence-level corroboration remain under
`reports/runtime_capture/`.

The reusable `mission_trace_replay` reader reuses a passing inspection while
binding every decoded row to the retained journal, profile and complete receipt.
It compares JSON value types as well as values, keeps scalar widths and enum
names from the retained profile, and refuses altered clocks, arguments, fields,
failure markers or loss accounting. Inventory consistency authenticates the
retained package's bytes, not its external origin or a newly executed native
branch. Native preparation and live collection are not repeated by replay.

The offline `mission_capture_timeline` projection associates entries through
their explicit mission ID or quest/parent-quest ID plus archived `questDic`
membership. Conflicting carriers, repeated membership and missing quests remain
unassigned. A condition ID supplies stored candidates only, even if only one
candidate remains; an objective-copy root does not identify the live quest or
reveal individual incoming numeric values. A configured predecessor is
corroborated only by a same-thread success entry preceding a canonical
`isNewQuest=true` start entry. Restoration entries, cross-thread observations
and a thread clock reversal withhold that corroboration. This proves the
observed entry order beside the configured dependency, not a successful return,
server prerequisite evaluation, asynchronous parentage or Story order. Optional
current reuse checks the selected native hashes and each observed mission
definition's bytes; that targeted match is not whole-export freshness.
The explicit `mainPathQuests` list is retained as authored structure. Its
ordering can differ from numeric suffix order: the retained `a1m15` path and
source-bound quest entries agree on the `q#6` to `q#8` to `q#7` route and the
`q#11d1` continuation. A stored main-path list does not fill a recording gap or
establish the server's branch-selection rule.

The stored `m1m9` definition also shows why a main-path list is not the entire
quest dependency graph. Its `mainPathQuests` contains `q#1` and `q#2`, while
explicit predecessor lists form `q#3` → `q#6` → `q#4` → `q#1` → `q#2` → `q#5`.
Some of these quest rows have no objective records; that representation does
not prove that they execute no effects. A recording begun at the three-marker
objective can preserve its restoration and remaining handoff, but cannot
reconstruct the earlier SNS or acceptance stages. Keep those stored
dependencies separate from newly observed transitions. The marker condition
cohort and the photo condition's reused ID likewise require explicit source
membership; another available variant is useful only for a still-unobserved
carrier or branch, not to repeat the admitted Boolean-to-progress bridge.
`m1m15` shares the `m1m9` display-name key and radio names while storing its own
quest IDs, script operand and shorter quest graph. Retained runtime entries
select that variant directly. A visible `日常·寻机启事` label or an `m1m9` radio
prefix cannot transfer the original mission's SNS stages or later quests to it.

Use the named MissionRuntimeAsset schema reader for corpus comparisons;
its reviewed baseline count is not a current denominator. Export freshness and
schema closure describe stored definitions, not VFS byte identity or runtime
activation. Changing census counts, exact native windows, excluded proof checks
and inventories stay under `reports/runtime_capture/`.

## LevelScript FMV path to installed Video

Current FMV source evidence comes from a complete typed LevelScript owner and
its selected StringPool, never from printable movie bytes or an inline-string
tail scan. `PlayFmvAction._moviePath` is a pooled `Param<string>`; the source
consumer independently re-reads the entire typed field and requires physical
owner EOF. Only an exact integer constant source is selected. Its reference and
path fields are inactive in the proved constant getter path, but the maintained
stored reader still decides which complete Param variants it admits.
`StartFmvAndTeleportAction._fmvId` remains a structural projection: it does not
inherit the PlayFmv consumer's native mapping.

[`levelscript_fmv_video_native.py`](../../scripts/game_data/levelscript_fmv_video_native.py)
authenticates the reviewed current contract on every operation, including typed
source fields, actual caller transfers, reciprocal generic contexts, registered
canonical entries where present, complete owned native windows, metadata
literals and the links between independently proved components. The selected
original path carries the constant movie reference through `GameAction.PlayFmv`,
gender-prefix selection and missing-candidate fallback, the cutscene subpath
formatter, VideoManager's suffix branch and the VFS name probe. Actual closed
format forwarding paths are proved directly; a canonical entry at a different
address is not an alias proof. The bounded formatter/parser, selected default
string delegate, cached builder, String allocation, inline copies and ordinary
Concat compose with the separately gated bounded-copy helper. The VFS readonly
video-root field has a selected reached fallback-initializer proof; earlier,
cold and other initializer paths are excluded. The output recipe is derived
from those authenticated literal cells, not accepted as an independent JSON
name map.

The admitted string domain and excluded helper branches are explicit in the
contract. Initialized compatible generic/literal slots, mutable default
delegate selection, same-thread unused cached scratch storage, sufficient
capacity, the selected allocator state and normal noninterfering helpers remain
conditions. iFix state, effective gender, candidate existence and the
CurrentCulture suffix-comparison result are separate runtime witnesses; a VFS
filename match does not establish any of them. Unbacked runtime globals are not
read as zero. Larger strings, custom formatters, growth and cold paths fail
closed rather than inheriting the selected source result.

[`levelscript_fmv_video_corpus.py`](../../scripts/game_data/levelscript_fmv_video_corpus.py)
requires the current standalone LevelScript family receipt with complete raw,
logical export, StringPool and reader-input bookends. Each operation replays
its selected owners and verifies matching current unencrypted Video slices
against their declared data MD5, with physical chunk-selection and byte
bookends. The generated source plan can select files for another operation; it
cannot cache native or schema success. Story consumes these fresh conditional
source/name rows separately from its generic UID scan and never marks them as
an observed activation or playback chain. An unavailable source receipt and
incomplete consumer coverage keep the unused-cutscene guard degraded even when
the native name gate passes. Whole-source coverage, live playback, mission
ownership and Story order remain independent evidence requirements.

## Spatial carriers

Story is placed on Map only through the exact carrier's own authored geometry
or identity: trigger volumes, constant EntityPtr targets, entity lists, patrol
checkpoints, SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk,
atmospheric NPC clusters, narrative components, reading points, and 3D radio
actions. Each has its own schema and uniqueness gate, under shared rules:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology; per-level coverage belongs in the generated frontier
  and map reports.

## What each carrier's identity domain is

Numerically equal ids in unrelated domains are different identities:

- validated local Story trigger volumes carry their own decoded Box/Sphere
  geometry at an authored X/Z position and rotation. Current-build native
  consumers confirm these ids address the LevelScript-local `triggerVolumes`
  domain through a runtime registered-id bridge; **they are not
  WorldEntityRegistry slots.** Their Story links stay distinct from nominal
  mission context and imply neither mission ownership nor runtime firing.
- MissionArea pins have an exact MissionAreaTable Box/Sphere definition and
  remain **Story-unresolved**; proximity never supplies their Story or order.
- NPC proxy rows use their own domain. A build-locked `NpcProxyGetter` reference
  attaches actions through an exact proxy-id/segment/table join and **never
  reuses a numerically equal world-entity identity.** The unreviewed
  `jumpToCampFireGlobalId` tracking field (by name an optional campfire jump
  target) is accepted only at 0 (`npc_proxy_tracking_fields_are_exact` in
  `scripts/webui/story/source_gap/data.py`); any other value or new field fails
  closed until reviewed.
  The external `activeCondIndex` and stored `m_activeCondIndex` also have
  distinct meanings: the selected original `ChangeActiveCondition` path stores
  minus one for negative inputs, otherwise the incoming index minus one.
  `get_activeCondIndex` returns that stored ordinal, and the original interaction
  path selects `exDatas[m_activeCondIndex].dialogId` after its count and
  nonnegative bounds checks. Recover the conversion, getter and selected list
  output together; row indexing supplies neither mission ownership nor chronology.
- current-script slot actions resolve through the pinned
  [`entityptr_script_slot_native.py`](../../scripts/game_data/entityptr_script_slot_native.py)
  contract: the lookup is keyed by the current `LevelScriptRuntime` script id
  and slot in `EntityManager`. A unique WorldEntityRegistry script/slot row
  proves the authored map target; **runtime registration and lifetime stay
  unproven.**
- world scenery receives a Story link when one counted `LevelInteractiveData`
  record stores both its exact `embeddedLogicId` and a NarrativeComponent
  `typeId`. e0m0's four tombs use that direct binding, **not numeric order or
  spatial proximity.**
- every `LevelInteractiveData` string member (`entityDataIdKey`, component
  `ParamKeyValue` keys and atom strings, progress-lock `ownerId`, the final
  record's `sceneId`) and every `InteractiveTable` id/path is a StringPool
  index on the current build, in LevelData and LevelScript alike (corpus
  correspondence + maintained pooled codecs, not a native formatter proof).
  Every interactive Story route (quest lock, world dialog, narrative mission,
  LevelData/LevelScript narrative, registered script entities) frames and
  decodes only through the export pool: no pool, or a pool that changes
  mid-run, admits nothing, and an unresolvable index in a framed record
  raises with its offset. The horn route stays closed because
  `data_int_horn.json` no longer matches its pinned template.
  Historical 27-member Narrative evidence remains separate from the current
  28-member route in
  [`levelscript_narrative.py`](../../scripts/webui/story/levelscript_narrative.py).
  The current route requires a fresh
  [`CurrentLevelScriptSource`](../../scripts/game_data/memorypack/levelscript_current_source.py)
  operation: reviewed selected-native source facts, authenticated logical owner
  and StringPool bytes, every reached child capability, generated field order
  and sequential physical EOF. A missing contract, refused child or late source
  change withholds its rows. A zero result is not evidence of absent Narrative
  configuration. The component and scalar-string kind come from their actual
  native enum declarations; a historical numeric key cannot grant either
  meaning. The projection records stored configuration only. Runtime consumption,
  activation, playback and mission ownership remain separate joins.
  The separate
  [`ExistingLevelScriptSource`](../../scripts/game_data/memorypack/levelscript_existing_source.py)
  operation accepts an explicit export root and native pair for existing-file
  diagnostics. It freshly validates the same native grammar, binds the selected
  owner files, StringPool and any InteractiveTable reads, and rechecks their
  full path set and bytes with reader/native bookends. It grants no current
  census, VFS, source-receipt, absence or publication authority. A stale census
  must still fail in `CurrentLevelScriptSource`; existing-file EOF cannot repair
  producer or installed-VFS fingerprint drift, and Story projections never
  fall back to this diagnostic operation. Historical receipts keep their
  original provenance.
  A fresh lexical source operation may reuse successful pure native validators
  for the same function and complete arguments. Reuse begins after all native
  and child entry gates, ends before every exit gate, and stays suspended across
  nested entry and exit. Results are copied; failures and payload decoding are
  never cached. Complete reader, native, pool and selected-file bookends still
  decide the operation. Outside that scope validators run freshly, and saved
  reports never seed the private cache.
  A direct selected validator call may also borrow that pending operation's
  complete fresh entry reader identity. Delegation requires its exact live
  call frame and callable code; helper, direct, default, foreign and recursive
  calls cannot inherit it. Returned snapshots are copied, and closing the
  scope clears the identity. Every outer and independent child exit still
  performs fresh checks; changed source bytes, imports, contracts or negative
  dependencies withhold the completed operation receipt. Native, contract,
  pool and payload reads retain their own gates.
  Dependency discovery may reuse immutable syntax extracted from identical
  freshly read bytes. Every fresh scan still enumerates current paths, resolves
  imports and resources, checks ambiguity and escape boundaries, and hashes the
  complete source set. Cached syntax cannot supply a saved manifest or proof.
  The current owner contract's second schema stores structurally interned
  provenance through
  [`levelscript_contract_provenance.py`](../../scripts/game_data/memorypack/levelscript_contract_provenance.py).
  Semantic child scopes, typed requests, actual targets and callback conditions
  remain lossless. Native windows and metadata methods have separate catalogs;
  literal native constant data retain their bytes and native hash without
  becoming code windows. Decoded rows and copied instruction regions remain
  report-only traces. The normal validator still derives the complete graph
  freshly and compares both directions before exposing semantic capabilities;
  expanding a compact graph alone grants no source or owner admission.
  One validation may keep its strictly expanded semantic tree locally for
  comparison and capability extraction; it never shares that tree with another
  operation or skips a fresh native derivation.
- NPC patrols have a separate current pooled source contract in
  [`leveldata_npc_patrol_native.py`](../../scripts/game_data/leveldata_npc_patrol_native.py).
  The current generated `NpcPatrolData` has ten members, including
  `pauseActionWhenPatrolDisabled`; the historical nine-member inline locator
  is not a current owner proof. Its strings are pooled under the contract's
  selected typed helper/provider conditions. Positive Blackboard pairs and
  list states outside that standalone profile's reviewed bounds remain closed.
  The separate whole-host extension re-proves the repeated reference-list
  source and applies its own finite resource bound. Its exact
  `PatrolSubAction.eventBBDataPairs` parent composes the independently owned
  managed-value DataPair list, callback and child source; it does not borrow
  SkillData's parent field. A DataPair FF produces the default managed value,
  rather than a null reference, and its positive pooled record has a different
  wire extent. This extension still requires the complete current owner gate
  before any source receipt or Story projection can publish it.
  Story's radio projection now reuses `CurrentNpcPatrolSource`, which delegates
  to the same current whole-LevelData source operation as the pooled host
  cursor: selected
  native inputs, authenticated logical source/pool bytes, reader and exit
  bookends, and sequential physical LevelData EOF are required together.
  A proved radio field and enum case supply stored configuration only;
  runtime radio consumption, playback, mission ownership and chronology are
  unresolved. Earlier unsupported children, including positive Brief
  properties/reference lists or interactives, withhold that owner rather
  than causing a patrol tail search or proving absence.
  The checkpoint-to-mission join remains explicitly `pendingReview` until
  its complete current pooled Patrol/Brief/property host is authenticated.
  Its old ID/MC9 locator cannot admit rows; the Story patrol audits expose
  the failed join and affected source instead of treating pooling itself
  as unproved.
  `AI.Config.NpcPatrolData` and `Core.PatrolData` are separate stored identity
  and grammar domains. A controller's `patrolData` field, matching point index
  or matching numeric id cannot substitute for an authenticated lookup and
  conversion between them. The complete LevelData host, Brief/property graph,
  controller conversion, checkpoint event producer/filter and radio request
  transfer each require their own current source proof. Even a proved request
  path does not establish an observed callback or playback.
  The current Core stored graph has its own
  [source composition](../../scripts/game_data/memorypack/leveldata_core_patrol_sources.py)
  and [pooled cursor](../../scripts/game_data/codecs/leveldata/current_core_patrol.py).
  Its root and action records independently join their generated readers,
  ordinary adapters, nominal enum backings, raw Vector3 lists and actual
  `LevelData.patrols` call. The shared SubAction and its finite union/DataPair
  children are freshly proved separately; the child evaluator reads the
  actual source span without inventing a collection header. The host requires
  this whole finite profile before null or empty input and retains its
  initially-null list, matching callback and resource conditions. This closes
  a stored Core grammar; it supplies none of the controller conversion,
  checkpoint or runtime joins described above.
  The [selected checkpoint request program](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_sources.py)
  separately proves the actual sender/id/index/position literal loads and
  typed blackboard call arguments. It copies the controller's entity through
  the complete EntityPtr local, passes the same entity to SetReceiver, and
  transfers a compatible Core lookup's id, incoming checkpoint index and
  actual named position getter result to their typed calls. The final request
  carries the event-key literal independently joined to the header getter.
  Lookup, conversion, blackboard write and disposal effects, the final callee's
  event-dispatch identity and filter semantics remain separate obligations.
  This complete request source neither proves a produced live event nor
  promotes the still-open checkpoint-to-mission join.
  A separate [checkpoint filter caller proof](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_filter_sources.py)
  authenticates the receiver/id/index/position keys, the inherited mode field,
  all optional-filter combinations, failed-read and mismatch returns, complete
  EntityPtr/position copies and the base Process call. Its typed helpers join
  their exact current registered targets. The producer's sender key and the
  filter's receiver key remain distinct: SetReceiver and blackboard storage
  effects must establish that relationship. The independent helper, value,
  storage and output owners below supply selected source effects; the caller
  graph alone supplies none of them. Actual bound output-property effects,
  event invocation and the checkpoint-to-mission relationship still require
  their own ownership and live selection evidence.
  The [selected helper paths](../../scripts/game_data/memorypack/leveldata_patrol_helper_sources.py)
  now independently bind the producer's virtual-slot thunk to the controller's
  named `get_patrolData` slot. The thunk restores its frame and tail-jumps with
  the same receiver and selected MethodInfo; the getter's complete bounded
  leaf returns the Core patrol backing reference unchanged. The actual class
  slot must still match that getter. This does not identify an authored NPC
  configuration or prove its conversion. The base `ActionHeader.Process`
  source separately returns true without a blackboard read or write on both
  selected absent-replacement paths. Runtime replacement absence, the remaining
  typed helper effects and controller conversion are supplied by separate
  owners; actual controller selection and live dispatch remain unobserved.
  A separate [Config-to-Core prefix proof](../../scripts/game_data/memorypack/leveldata_patrol_config_prefix_sources.py)
  selects the New controller's own conversion method and exact Config/Core
  byref ABI. It proves the initial authored scalar copies and literal
  new-patrol/born-checkpoint flags before the asset/config lookup tail. The
  same-named base controller method is not substituted. The own Core
  constructor target and typed allocation request are authenticated, while
  normal constructor/heap/barrier effects come from independent selected-path
  owners rather than from this prefix. Later asset lookup, optional settings,
  action-list conversion and installation likewise require their separate
  source joins. The prefix neither establishes actual initializer/controller
  selection nor produces a checkpoint event or observes playback.
  Closed List arguments and the generic declaration establish ownership, not
  instantiated field offsets. The selected complete GetItem/Add programs must
  independently prove the actual storage displacements. A SafeCount interface
  tail supplies only its selected Count result until the inflated receiver,
  interface, MethodInfo and callback sources are joined. Likewise, an Add proof
  conditional on spare capacity does not cover conversion from the actual
  empty no-argument List constructor; the selected positive growth and copy
  owner must supply that path independently. These boundaries are enforced by the
  [Patrol helper](../../scripts/game_data/memorypack/leveldata_patrol_helper_sources.py)
  and [Count-selection](../../scripts/game_data/memorypack/leveldata_patrol_count_selection_sources.py)
  owners rather than inferred from a closed type name.
  The [offline source composition](../../scripts/game_data/memorypack/leveldata_patrol_offline_sources.py)
  joins the Config prefix, lead/gait/point seams, named Core and Action defaults,
  typed list constructors, controller-loader publication and Count-selection
  normalization, lookup, projection and fallback. Independent growth and copy
  sources cover the selected positive list path; the initializer passes its
  unchanged Core output to the canonical installed field. File-backed startup publication
  and a selected interner or table path do not observe live cell, table or
  MethodInfo values. Complete helper effects remain separate from caller
  control; activation, checkpoint delivery and playback still need runtime
  ownership. The [normal supplement](../../scripts/game_data/memorypack/leveldata_patrol_normal_sources.py)
  freshly joins the complete selected finite normal source path, including the
  atomic event/executor supplement, without a remaining selected native-source
  frontier. Its exhaustion flag applies only to that recorded path. Cold setup,
  growth, misses, other input/resource states, different callback or action
  schedules and fresh factory invocation remain nonselected native alternatives;
  live identities, mutable state, callback effects, activation and playback
  remain capture requirements. A source-derived target inventory is not a
  sufficient observation recipe: the selected ABI, fields and entry/return
  phases must cover the actual question, and the offline consumer must compare
  the same references, state and property effects. Unsupported value returns,
  container/callback identity or missing effects withhold the corresponding
  join. Review recorder support, bounded fixtures and affected saved evidence
  before requesting another run; a named target or loss-free event count alone
  supplies none of those missing operands. The complete Patrol observer recipe
  and `patrol_runtime_capture_sources` require finite source-owned raw spans,
  independently derived closed container roles and live callback-pair reads;
  an unavailable closed consumer keeps that preparation refused. The separate
  discovery recipe selects ordinary reference/scalar callers and callback pairs
  without demanding unrelated container proofs. Its unfiltered converter keeps
  the actual recorded return address and parent; it supplies no causal Init
  enclosure or complete conversion claim. Current caller scopes may include
  noncontiguous code only through the exact primary's complete unwind-parent
  family, with independently retained window bytes and direct call bindings.
  A contiguous range is never widened across unrelated code to find a call.
  `patrol_runtime_inspect` checks original retained packages and explicit
  invocation pairs. Padding stays opaque, and null, unreadable, bounded-out and
  changed snapshots remain distinct. These profiles do not close resource
  activation, complete event/queue state, authored callback effects or downstream
  audio ownership. Authored `npcPatrol` configuration is distinct from enemy
  and character patrol data. A useful observation must identify the selected
  NPC configuration and controller, and recording must encompass its relevant
  initialization or event lifecycle; an already visible ambient patrol does not
  establish that selection. A healthy session with no selected hook entries
  provides no activation or absence proof.
  Recorder builds and synthetic fixtures do not establish those runtime joins.
  The optional Mission/Audio bridge records synchronous enclosure using the
  original Mission invocation and Audio capture identities. Its bounded queue,
  sampled calls outside a Mission scope, losses and unfinished scopes remain
  explicit. The importer admits only the exact declared provider composition
  and reconciles its sidecar with both original journals; a matching thread or
  nearby timestamp supplies no ownership. Even a valid synchronous link does
  not establish asynchronous callbacks, completion or audible playback.
  The path owners independently prove the managed
  UTF16 fold and the finite byte-hash arithmetic; neither a CRC-like name nor a
  shared width supplies another hash algorithm. The
  [concat owner](../../scripts/game_data/memorypack/leveldata_patrol_concat_sources.py)
  joins the actual closed three-string caller, own empty-string field and
  independently replayed builder creation, append, string construction, cached
  allocation, current copy family and disposal. It preserves the exact ordered
  UTF16 payload for a total length of at most 128 code units. Type/provider/TLS/cache
  and allocation identities remain conditions. The selected ASCII encoding and
  cached byte-pool owners establish output mapping and same-thread buffer
  ownership, without assuming allocator zero-state or general Unicode behavior.
  The [handle Get owner](../../scripts/game_data/memorypack/leveldata_patrol_get_sources.py)
  independently proves each generic handle hop, actual interface invocation,
  warm MethodInfo-cache hit and selected named proxy getter. An absent closed
  native registration does not become a canonical pointer alias. Requested
  asset-class compatibility, the actual cache/callback pair and valid handle
  state remain conditions. Monitor source covers the selected existing lock's
  acquisition, query and release, while OS/import and live ownership remain
  explicit runtime requirements.
  The [canonical installation source](../../scripts/game_data/memorypack/leveldata_patrol_install_sources.py)
  separately proves the New controller helper's own named-setter branch. It
  compares the selected class slot with the authenticated setter, stores the
  supplied Core reference unchanged into the exact patrol backing field, and
  passes that field's address to the independently proved disabled barrier.
  The successful initializer fragment passes a Config reference and distinct
  Core output local to conversion, then passes that same output reference to
  installation. Independent selected conversion and lookup sources do not
  grant the dynamic setter alternative, other initializer branches or actual
  callback selection. This source join does not establish a running controller, checkpoint
  delivery or playback.
  The [Init helper source](../../scripts/game_data/memorypack/leveldata_patrol_init_helper_sources.py)
  additionally joins the actual Boolean setter/getter to the same owned backing
  byte and the Core getter to the installed reference field. Its entity-key
  lookup reaches the exact GameLevel `levelData` reference and that LevelData's
  cached patrol dictionary. Default Int32/reference search has independent
  hash/key collision, hit/miss, null-bucket and full-output programs with a
  bounded mixed-chain induction; a shared body never substitutes for its closed
  caller contexts. The [preparation owner](../../scripts/game_data/memorypack/leveldata_patrol_class_preparation_sources.py)
  checks only the actual short wrapper span and the separately owned inner
  normal returns: the selected descriptor-bit paths make no nonframe writes
  or opaque calls. The bit predicates do not observe initialization or assign
  meanings to unproved descriptor fields. Stable valid hash chains, selected
  comparer/callback pairs and coherent storage remain conditions; lazy index
  construction, miss logging, custom-comparer and cold/replacement paths remain
  separate source obligations. None of these sources observes a live lookup,
  controller activation or playback.
  The [checkpoint typed helper owner](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_helper_sources.py)
  preserves the full EntityPtr, Vector3 or integer through the own closed
  GetOrCreate request and actual virtual/invoker argument transfer. Its read
  helpers use their own typed string/ParamVariable dictionary requests and
  complete returned-value transfers; absent canonical native rows do not
  authorize an erased-body alias. Receiver construction preserves its whole
  value through the invalid/null, server/parent-script and selected slot paths.
  Direct integer output and constant Entity/integer Param reads are distinct
  conditional source domains. The
  [output supplement](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_output_sources.py)
  joins the output predicate, bound/inert setter caller and ordinary delegate
  forwarding source, including the exact reciprocal context. Actual delegate
  target and property/storage effects remain runtime identity obligations;
  other Param modes, optimized delegate alternatives and logging are not
  admitted by these selected programs.
  The [checkpoint value helper owner](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_value_sources.py)
  independently replays the receiver's whole EntityPtr forwarding copy, the
  named Entity/RootComponent position copy, ObjectPtr conversion, cached UID,
  validity, `Equals` and `Lock` paths, and EntityPtr's selected normal comparison
  paths. Its slot-parent resolver returns the Entity's parent-script UInt64;
  it is not an Entity-reference lookup. The UID dispatcher requires its actual
  literal class-discriminator branch, which is not equated with a metadata
  type index. Exact closed caller contexts and complete actual call bodies
  establish these source effects without a canonical-registration alias.
  Ready contexts, stable compatible storage, absent selected replacements and
  the selected cached-object state remain conditions. Cold setup, uncached
  resolver alternatives, live liveness/selection and event delivery remain
  separate; this helper proof does not grant whole checkpoint or playback
  evidence.
  The [checkpoint callee composition](../../scripts/game_data/memorypack/leveldata_patrol_checkpoint_pool_sources.py)
  joins the actual typed GetOrCreate, value property and virtual getter/setter
  programs to their own string-key table lookup and mode-one mutation. Hash
  and ordinal equality source is independently replayed for the exact owned
  literal domain; an erased comparer body is not a closed nominal pointer
  alias. Table insertion requires the selected no-free-entry path and spare
  capacity. Pool reuse and fresh-allocation paths both invoke the independently
  proved OnAllocate resets before use: key, observers, counters and every value
  byte are established by that reset, never by assuming allocator zero-state.
  The actual allocator source is retained, while allocation success, adequate
  writable capacity and live pool/callback/table identity remain conditions.
  Cold setup, resizing, free-list reuse, observer alternatives and event
  activation remain separate; these source effects do not observe checkpoint
  delivery or playback.
  The [EventParams scope source](../../scripts/game_data/memorypack/leveldata_patrol_event_params_sources.py)
  keeps the returned Event reference identical through allocation, Scope value
  insertion and last-scope removal. Disposal invokes Clear before pool recycle;
  clearing the Scope stack reference makes a later Dispose a no-op without
  clearing its stored Event value. The [cleanup source](../../scripts/game_data/memorypack/leveldata_patrol_event_cleanup_sources.py)
  independently proves the ordinary variable enumeration, both dictionary
  clear calls and the actual byte-fill body against this caller's own bounded
  array extents. The variable dictionary is held stable until enumeration
  finishes; selected ordinary values exclude the separate global/map-variable
  subclasses. Base variable recycling clears its serial, key and observer
  state but leaves its constant payload for the next typed OnAllocate reset.
  Event OnAllocate resets debug/serial fields and leaves both dictionaries
  untouched. A prior Clear can establish empty dictionary state for reuse;
  a fresh dictionary constructor that only sets comparer state cannot itself
  prove zero count, buckets or entries. Actual allocator initialization and
  selected pool/callback identity must therefore stay explicit, with no
  allocator zero-state assumption or runtime event-delivery grant.
  The [Event pool callback composition](../../scripts/game_data/memorypack/leveldata_patrol_event_pool_sources.py)
  closes the selected ordinary cleanup through its own type-keyed pool
  registry, typed recycle methods and base reset callbacks. RuntimeType hash
  and reference equality are proved independently from the string lane. An
  absent closed comparer registration leaves the actual selected comparer
  body/MethodInfo compatibility conditional; it does not authorize a pointer
  alias. The pool's declared backing container is `Stack<object>`, whose
  independently checked append stores the same Event reference. It is not a
  nominal `Stack<EventParams>` substitution. Interface dispatch uses the actual
  class discriminator interval and matching table entry, without equating that
  discriminator to a metadata type index. Clear precedes recycling, which
  either retains the Event in the pool or updates the count when it is dropped.
  These selected disposal effects do not close the separate fresh-allocation
  dictionary initialization boundary or observe live callback selection.
  The separate [constructor initialization owner](../../scripts/game_data/memorypack/leveldata_patrol_event_initialization_sources.py)
  proves a selected object-allocation branch that writes the class/monitor
  header and explicitly fills the complete payload before the independently
  named constructors store the two dictionary references. The raw allocator is
  required to return adequate writable storage; it is never assumed to return
  zeroed storage. Exact class-flag predicates, ready initialization and the
  finite aligned instance extent remain conditions. The other class-flag
  allocation branches and the actual pool factory/Activator invocation of
  these constructors remain separate native-source joins, alongside live
  allocator/capacity and callback selection. A constructor proof must not
  silently discharge those caller obligations.
  The [executor copy supplement](../../scripts/game_data/memorypack/leveldata_patrol_executor_copy_sources.py)
  proves that AssignEventParams maintains a separate cached Event container:
  it obtains one through NewEmpty when missing, clears it, then deep-copies
  the incoming ordinary variables. It does not store the incoming Event
  reference in that field. Complete enumeration forwards each key/value pair
  into the actual typed Copy, pool allocation/reset, value getter and property
  setter source, followed by the dictionary's own mode-one setter. Whole
  Int32, Vector3 and opaque EntityPtr stored bits are preserved in distinct
  variables. The enumerated key replaces the clone's initially copied key.
  The selected destination already has sufficient bucket/entry capacity after
  Clear; source and destination storage, variables and pool ownership must be
  distinct and stable. NewEmpty uses the proved nonempty Event pool reuse
  path, without borrowing fresh factory/Activator effects. The actual
  GetEnumerator call and reciprocal value return are independently proved
  when its exact closed registration is absent; absence never supplies a
  canonical pointer alias. The machine-readable postcondition admits only
  the producer key/type subset and independently supplied receiver key, with
  no other entries. Its absence of `@event_key` is conditional source state,
  not an observed live dictionary; a subsequent insert needs another spare
  slot and no intervening key writer. Cold initialization, resizing, aliased
  input, foreign variable types and actual action execution remain separate.
  The [cached-string lifecycle supplement](../../scripts/game_data/memorypack/leveldata_patrol_cached_string_lifecycle_sources.py)
  closes the selected later Clear of a cached Event containing the ordinary
  producer keys and its string event key. The executor reloads that cached
  container before writing the key. Its generic interface recycler arm, own
  String Type registry lookup, typed pool, base OnRecycle and spare Stack.Push
  are independently replayed. OnRecycle leaves the constant string reference
  in the pooled variable; the separately proved next OnAllocate clears it.
  Empty or mixed ordinary/string dictionaries use the same complete Clear
  enumeration and final byte fill under their exact key/type and ownership
  conditions. The original three-family owner remains unchanged. Absent closed
  string registrations require compatible selected reference-body callbacks
  and closed String MethodInfos, without a canonical pointer alias.
  The [warm RuntimeType cache owner](../../scripts/game_data/memorypack/leveldata_patrol_runtime_type_cache_sources.py)
  additionally proves GetTypeFromHandle's selected cache-hit frame, actual
  primitive and value-class resolution, raw type-key hash/equality and unchanged
  indexed cached return. A direct leaf without an unwind primary has an exact
  authenticated source span and no invented physical extent. Named class and
  Type identities, initialized handles and caches, the occupied matching probe,
  valid indexed storage and normal exclusive mutex imports remain conditions.
  Cold creation, collision, allocation and insertion are separate alternatives;
  neither this source return nor a corresponding Type key observes live pool,
  registry, callback or executor identity.
  The [resource validity source owner](../../scripts/game_data/memorypack/leveldata_patrol_resource_validity_sources.py)
  independently joins both handle-validity callers, the actual ObjectHandle and
  proxy getters, the closed Int32/reference table search, and the selected
  interface-compatibility and preparation returns. Handle ID offsets come from
  the nested nominal value fields; proxy class discriminators remain literal
  runtime predicates. Membership covers both the inline ID set and its actual
  closed Int32 HashSet tail, including hash/key collisions, empty results and
  the native slot-index and chain-counter guards. Disposal covers the selected
  state field and finite recursive wrapper path. Complete owned helpers and
  explicitly bounded no-unwind spans are hashed and replayed without claiming
  physical extents for those spans or canonical pointer aliases. Stable typed
  storage, coherent ready contexts, the selected callback pairs, absent
  replacements and disabled collection remain conditions. Cold/exceptional
  alternatives, live table contents, asset lifetime, successful loading and
  playback are not observed by this source proof.
  The [Radio dispatcher source owner](../../scripts/game_data/memorypack/leveldata_patrol_radio_dispatch_sources.py)
  keeps its plain `CombineKey` value distinct from an enum or primitive key.
  Its own dictionary source proves the masked hash, complete raw-key equality,
  both bucket-division paths and finite collision-chain lookup. The actual
  context-indexed default-comparer body and its separately registered closed
  provider are independently replayed against the same nominal static slot;
  unequal physical pointers do not become aliases. Play calls a separate typed
  Dispatcher body, while Stop inlines that lookup and needs its enclosing
  SendGlobal frame and EventData local proved independently. Both EventBinding
  listener loops preserve the original EventData address, capture their bound
  before iteration and skip disabled entries. Selected callback class/context
  equality, normal callback return, stable remaining list entries and empty
  pending operations at outermost cleanup remain conditions. The selected
  Stop delegate tail excludes its explicit inline callback alternatives.
  These caller and lookup effects neither identify installed listeners nor
  prove arbitrary listener mutation, callback effects, Lua dispatch or audio
  playback.
  The [resource ID source owner](../../scripts/game_data/memorypack/leveldata_patrol_resource_id_sources.py)
  joins the zeroed handle-construction local to the actual untracked-handle
  constructor and both concrete `RetainHandle` methods. The constructor copies
  the log-channel enum byte unchanged; it does not normalize a Bool. Its
  padding stays caller-zero, while the optional main-version value comes from
  the named resource-manager static field. The ID utility returns the old
  counter bits and increments modulo the stored integer width; this is neither
  atomic nor proof of uniqueness. Independent byte programs cover compact
  inline packing, duplicates, the existing integer set, free slots and collision
  chains, and promotion of four inline IDs into a spare pooled set. Promotion
  requires an empty set with sufficient existing capacity; ready metadata,
  compatible selected comparer contexts, stable storage, absent replacements
  and disabled collection remain conditions. Pool construction, capacity
  allocation, optional diagnostics, live proxy state and asset lifetime are
  outside these selected normal effects.
  The [resource value-hash owner](../../scripts/game_data/memorypack/leveldata_patrol_value_hash_sources.py)
  independently follows the actual native `InternalGetHashCode` field walk.
  A handle contains a nested value, so the wrapper's null-object-array witness
  cannot discharge its hash: the outer walk boxes the untracked handle, whose
  walk boxes the two ID values and two byte-backed enums while XORing its stored
  integer fields. The owning metadata image's token/adjustor rows independently
  select boxed-aware ID hash bodies; an unboxed method address is never reused
  as a boxed callback. The ordinary enum body reads the same boxed byte. Exact
  source programs also cover ready class/type resolution, the primitive Object
  array-class cache, spare plain/reference allocation, payload copy and zeroing,
  and the named thread-storage and balanced cache-lock imports. These are finite
  normal effects under exact live callback/MethodInfo selection, ready coherent
  metadata/cache state, valid committed storage, sufficient spare blocks and
  disabled collection/profiling. Cold allocation and initialization, exhausted
  storage, replacements, live hash values and successful retention remain
  outside the source proof. The class-pointer seed is retained, not replaced by
  a presumed stable or deterministic asset identifier.
  The [Bundle proxy cache source](../../scripts/game_data/memorypack/leveldata_patrol_bundle_cache_sources.py)
  separately owns the selected cached `GetOrCreateAssetProxy` path. Its key
  starts at `AssetInfoPack.assetData.pathHashHead`, combines the stored integer
  bits with the selected RuntimeType hash and the actual HashCode seed, then
  preserves the resulting Int64 through default-comparer lookup. The ordinary
  Type hash and underlying-type self getter have independent named source
  proofs; the inherited `_impl` field supplies the selected hash bits. Hash and
  full-key collisions follow the actual bounded entry chain, and a hit writes
  the same cached proxy to the original output address with its complete frame
  restored. The own Int64 comparer registration and actual closed dictionary
  request stay distinct from live MethodInfo selection. Ready contexts, a
  stable seed and cache, compatible callback pairs, an existing hit, disabled
  collection and the selected diagnostics flag remain conditions. This does
  not prove cache creation/miss effects, loading, a stable asset identifier or
  a live proxy reference.
  The [cached request composition](../../scripts/game_data/memorypack/leveldata_patrol_request_sources.py)
  joins the exact successful manifest lookup, nominal byref asset-info value,
  seeded RuntimeType/key cache lookup and loader return. Its proxy-state tests
  remain literal numeric predicates; they do not assign a ready/loading name
  or prove scheduling and completion. The operation counter's bounded source
  arithmetic is distinct from the priority enum's unsigned backing and from
  uniqueness or atomicity. The
  [temporary string-block owner](../../scripts/game_data/memorypack/leveldata_patrol_string_scope_sources.py)
  balances the selected existing empty block through spare-pool removal,
  active-stack insertion and the actual IDisposable cleanup. This domain creates
  no temporary string and covers no cold pool construction. The
  [retention composition](../../scripts/game_data/memorypack/leveldata_patrol_retention_sources.py)
  binds the exact outer hash wrapper to its independent nested field-walk,
  boxed callbacks and same whole-value spare-slot insertion, including padding.
  Actual manifest/cache hits, RuntimeType/hash seeds, callback/MethodInfo pairs,
  valid tables and spare storage remain conditions; no asset or retained set is
  observed live.
  The [SendGlobal owner](../../scripts/game_data/memorypack/leveldata_patrol_radio_send_sources.py)
  supplies the enclosing Play and Stop frames required by the independent radio
  dispatcher. It preserves the whole value payload or same string reference in
  distinct EventData locals and authenticates the own cached EventManager
  singleton/context. Its finite no-Lua path uses the actual Contains body on
  null key-set storage; open generic definition offsets do not establish a
  closed HashSet layout. Nonempty Lua-key search and Lua dispatch remain outside
  that grant. Ready contexts, the current singleton/dispatcher, ordinary bound
  listeners and normal callback return remain conditions. Source transport does
  not identify a live listener target, prove its arbitrary effects or observe
  downstream audio playback.
  The [ASCII Encoding source owner](../../scripts/game_data/memorypack/leveldata_patrol_encoding_sources.py)
  joins the data-path caller's actual getter call to Encoding's named cached
  UTF8 field, and independently owns the string and internal UTF8 callbacks.
  It replays every length in the finite small-buffer domain at both UTF16
  alignments, including the scalar loop, alignment peel, packed four-character
  loop and scalar tail. Each output byte maps to the same input ASCII code
  unit; the returned count equals the input length. Named string fields and
  the packed path's little-endian flag have independent metadata joins. The
  live cached object's callback and MethodInfo identities for both virtual
  slots remain explicit selection conditions; nominal method declarations
  do not establish a live vtable alias. Ready contexts, disjoint valid storage,
  adequate capacity, null encoder state and ASCII input remain conditions.
  Unicode fallback, cold cache creation, live buffers and loading/playback
  are outside this finite source grant.
  The [event collection source owner](../../scripts/game_data/memorypack/leveldata_patrol_event_collection_sources.py)
  joins the actual manager callers to default-comparer lookup, cached Values,
  spare pooled-list allocation and an opaque listener snapshot. It preserves
  every payload bit across active dictionary entries, skips free slots, and
  independently replays clearing, disposal, pool recycling and the selected
  release callback. Zeroing includes the selected vector and repeat-store
  paths, with native jump-table bytes checked alongside code. Canonical
  generic registrations keep their original arguments: closed EventListener
  callback and MethodInfo selection, compatible storage, stable dictionaries,
  spare capacity, ready state and disabled collection remain explicit
  conditions. This does not admit a closed generic registration or establish
  a live callback alias, listener invocation, event execution or playback.
  The [checkpoint event-manager source](../../scripts/game_data/memorypack/leveldata_patrol_event_sources.py)
  consults the current enum-key cache and listener tables, transports the same
  EventParams through the own optional `DoSecondFilter` and `OnEventAction`
  delegate requests, or reads the selected EventActionTrigger, header and
  action-map entry before requesting its executor. These are the manager's
  own typed delegate declarations, not nominal Action/Func substitutes. The
  independently authenticated virtual header getter returns the producer's
  same event key; actual class-slot/MethodInfo selection stays conditional.
  Collection/snapshot and EventParams owners supply separate lifetime effects.
  The [atomic event owner](../../scripts/game_data/memorypack/leveldata_patrol_event_atomic_sources.py)
  joins those lifetime effects to the selected executor, cached-container copy,
  event-key storage and first-tick manager programs. It compares complete
  source packets and parent/pool facts, then checks the actual false-force
  transfer, tracked UID requirements, success-to-tick state and extra dictionary
  capacity together. The cached destination stays distinct from the incoming
  producer; its event-key write does not modify the producer's dictionary.
  Mixed cached-string cleanup and warm Type resolution have separate source
  proofs. These joins cover the recorded finite conditions, without granting
  every executor branch or a whole repeated event cycle. Current registration,
  concrete callback and action-map identities, authored effects, actual dispatch
  and playback require live evidence.
  The [executor event-key source](../../scripts/game_data/memorypack/leveldata_patrol_executor_key_sources.py)
  resolves the actual request as `SetValue<string>` under the literal
  `@event_key`. A shared reference body does not make that request nominally
  `object`. Its selected missing-key path joins the exact string dictionary
  lookup and mode-one insertion to nonempty typed-pool reuse, base and value
  reset, and the property/value setters. Its separate actual-key source replays
  the literal's UTF16 hash and inline hash invocation, then joins the same
  dictionary mask, bucket and entry probes. The copied five-key domain remains
  unchanged. Every existing key has a different UTF16 length, so the proved
  ordinal length-mismatch path rejects even a hash collision; no same-length
  content comparison is assumed for this missing-key insertion. The atomic
  composition requires that exact collision domain to equal all copied keys.
  The closed string registrations may
  be absent; independently authenticated canonical reference callbacks keep
  their original arguments and require compatible closed string storage and
  actual callback/MethodInfo selection. No pointer equivalence is inferred.
  Reset establishes the no-observer state before both the null initializer
  and the incoming string reference are stored. A distinct pool-owned variable,
  the absent key, an extra spare entry beyond the copied keys, stable storage
  and disabled collection remain conditions, rather than live observations.
  The [executor source owner](../../scripts/game_data/memorypack/leveldata_patrol_executor_sources.py)
  joins the actual manager's first direct invocation call to a selected
  header-hit path, the distinct header array, named setup and cleanup,
  ObjectPtr conversion and comparison, scoped context entry and disposal,
  constant Boolean validation and complete frame restoration. Node IDs,
  header IDs and the action-map node, header and action arrays remain
  separate declarations. Assignment and the string event-key write require
  their independent full source supplements; caller transfers alone do not
  discharge them. The selected success state clears the current action,
  timer and execution timestamp, installs the header's next ID in the cursor
  stack and records a true previous result. A later timer-wait cannot assume
  a positive timestamp from this path.
  These finite paths use the actual false force flag and require a valid
  coherent context, a header hit, a true constant validation value, spare arrays,
  an empty iterated-node table, a null pre-clean node context and scopes
  without a pop delegate. Actual header virtual callbacks and MethodInfos,
  the UID discriminator branch, stable storage, ready contexts, absent
  replacements and disabled collection remain explicit conditions. The
  discriminator is not equated with a nominal metadata index. Positive
  start-node IDs additionally join the distinct node array and the node UID
  string: a null or empty UID needs no link, and a nonempty UID with null
  wait-dictionary buckets returns the exact missing-entry result without
  hashing or a callback. It does not reinterpret the string length as an
  action-list count. Other validation, existing wait-map links and
  scope-delegate branches are not promoted by
  this selected source proof, and no running executor, live binding or
  action playback is observed.
  The [manager postamble source](../../scripts/game_data/memorypack/leveldata_patrol_manager_sources.py)
  checks that successful false-force state against the first tick's actual
  input. It separately joins empty child-list snapshotting and pool release,
  the time singleton's own logic-delta field, scoped context transfer, the
  empty Int32 iteration table's spare insertion, ordinary action entry and
  execution requests, the positive-delay return and the unchanged complete
  ObjectPtr queue value. The selected domain uses a tracked nonzero executor
  UID, one initial cursor/action and a zero logic delta. Action callbacks must
  preserve the recorded executor and scope state and publish the stated
  result, next-node and positive-delay fields; their identity and authored
  effects are not inferred. The action execution declaration is abstract:
  its wrapper is not a substitute callback body. Pool reference payloads and
  ObjectPtr elements retain their distinct sizes and exact closed contexts.
  This is a coherent finite source path, rather than independent predicates
  that contradict the invocation's stores. Other tick schedules, recursive
  child executors, actual activation and playback remain separate.
  The simple radio request, delayed scheduling and due-timer request now have
  separate complete selected source programs. The delayed path copies the
  authored radio identifier and wait value into nominal controller fields,
  accumulates the timer, makes the exact playback request when due and clears
  the pending state. The range handler's scheduling transfer is separate from
  its distance trigger. These facts remain conditional on initialized source
  state, absent replacement callbacks and compatible helper selection; they
  establish neither controller ticking nor observed playback.
  The first range request has a separate source composition: it joins the
  actual player-controller/entity position fields, complete position getter,
  and the ordered Vector3 subtraction and squared-length programs before
  passing the authored radio identifier to PlayRadio. Finite ordered geometry
  and absent replacement callbacks remain conditions. Repeated-state string
  comparisons, action selection and actual audio playback remain separate;
  the request source does not observe any of them running.
  The authored Character/Enemy patrol subtrees have a separate
  [finite record composition](../../scripts/game_data/memorypack/leveldata_authored_patrol_sources.py)
  and [stored-field cursor](../../scripts/game_data/codecs/leveldata/current_authored_patrol.py).
  Their distinct action, point and root records keep their own current
  ordinary adapters, nominal enums, pooled strings and nested list callbacks;
  Character's montage GameplayTag is independently typed. Both LevelData host
  fields bind their actual list request and call, including null and empty
  lists. The cursor preserves the initially null list and matching-callback
  conditions and shares a finite subtree budget. Neither this authored graph
  nor its exact field boundaries supplies the NpcPatrol-to-Core conversion,
  controller activation, action dispatch, checkpoint ownership or observed
  radio playback. Whole-owner source/pool/physical-EOF gates still precede any
  publication.

## Registered shells and slot action bindings

- An `int_empty` shell is a registered, unresolved empty slot in its own layer.
- A registered shell referenced by a strict constant `Param<EntityPtr>` inside
  a validated action record becomes a script target **only when a build-locked
  native formatter contract also proves its named member boundary**
  ([`action_entity_fields_native.py`](../../scripts/game_data/action_entity_fields_native.py));
  unresolved occurrences stay candidates. Neither form inherits sibling Story,
  cutscene, or sequence ownership.
- Script-container files, conditions, and ordering anchors are map-level
  context, not repeated onto sibling slots; a point receives a Story or a file
  **only from an exact script/slot consumer.**
- Every spatial world/script registry slot publishes an observational action
  binding status and action array. `no_reference_observed` means only that
  current decoded LevelScript evidence has no matching constant pointer --
  **not that the slot has no action.** Exact and unresolved references stay
  separate even when both address the same slot.
- A dynamic local-output reference becomes a slot action **only when a pinned
  producer contract proves a same-header constant alias**
  ([`entityptr_output_alias_native.py`](../../scripts/game_data/entityptr_output_alias_native.py)):
  a non-slot (`useSlotId` false) constant filter aliases the output by logic-id
  identity only, `conditional` on no IFix patch; slot-addressed filters stay
  `unresolved` and validated non-alias outputs remain unplaced.
- The exhaustive per-slot audit -- contracted EntityPtr field states,
  diagnostic-only dynamic `idRef`/output/variable references, and non-spatial
  references that must not become map markers -- belongs in
  `reports/assets/map_recovery/action_binding_index.json`.

The GenderSelect consumer gate proves a conditional initialized original-body
bridge: its action creates a callback, the GameAction sends the owned named
event key with that callback, and the shipped Lua message handler opens the
phase whose first activation requests its literal cutscene name. The event-key
constructor, typed generic contexts and selected source transfers are checked
freshly. Compatible reference sharing, coherent native/Lua event registration,
delivery, phase activation and playback remain conditions. Exact installed Lua
wrapper and maintained decoder/normalizer facts bind the exported source; raw
decoded text and normalized export hashes are different representations.

A unique ASCII-casefolded Story key is a reviewed source association, not a
proved runtime lookup result. Absence of case-conversion calls does not prove
case-sensitive lookup. The Pipeline preserves runtime key resolution as
unresolved and checks uniqueness in its selected Story registry. Stored trigger
geometry and header/switch/action closure require their separate whole-owner
reader and source/pool/native guards; the native/Lua bridge supplies none by
itself and establishes no mission ownership or order.

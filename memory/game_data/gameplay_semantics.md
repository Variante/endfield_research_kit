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

The simulator's retained joint execution now composes source-zero skill clocks,
authored Find/Damage dispatch and calculated HP in the same reusable component.
Later timer/HP endpoints compare only; they do not reseed state. Cast-start,
retirement, physical targets and arithmetic intermediate ports remain explicit.
Only consecutive original cast epochs count as a complete combo; excluding an
unproved action must not manufacture a handoff, a miss or an uninterrupted cycle.

The simulator subproject now executes a conditional first-normal-attack slice:
local input admission, authored timeline timer, target query, calculated Pack,
selected damage/HP arithmetic and a recovery-gate probe share one state machine
and Gym adapter. It remains separate from whole-battle admission. Historical
Pack/Modifier/HP results are comparison targets, not assigned outcomes; captured
initial attributes and selected skill rank are explicit state premises. A fresh
current-source decode was obtained with the retained authenticated reader;
neither an older source digest nor a failed current reader was promoted.

For the selected attack, the source Box geometry is constant rather than
runtime-blackboard-dependent. The ordinary scalar getter widens stored Single
to Double, and Vector3 construction narrows components to Single. The Box
consumer passes half-size to OverlapBox; its position reference is the owner's
mount point and its direction reference is owner forward. GetRayBox is used
for contact reporting, not an additional BoxCast candidate query. This recovers
local query geometry, not the actor's world pose, root motion, final rotations,
target collider or subsequent candidate filters.
The selected Win64 query ABI also distinguishes an inline TargetHandleView
reference word from indirect Vector3/Quaternion aggregates. DoFindEntity's owner
is an ordinary AbilitySystem reference, not an ObjectPtr aggregate; sampling it
as an ObjectPtr would be an invalid cast. The used non-results-array overlap
helper invokes its native query directly, bypassing the other managed overload.
A hook on the latter would not observe these queries. The proved argument-root
indexed sampler reads the Find action's input TargetHandle, even when sampled
after return; that timing does not make it the selector's output. The ordinary
Find consumer passes the selector result to Context.UpdateTargetGroup. Damage
obtains its actual target carrier through GetTargets_Dispose, whereas its
GetFirst(input) call selects a separate attacker/effect-source operand. Equal
input wrappers and later Process targets therefore do not prove the blackboard
write/read join. A nonempty input GetFirst and nonzero physics candidate counts
can coexist with a Damage action that returns false without Process. The native
zero-actual-target-count branch is one possible cause, not an observed cause
until that actual carrier/count is sampled or otherwise proved.
The ordinary GetTargets_Dispose body supplies an argument-root observation
alternative: it obtains a source handle, obtains a destination, calls
TargetHandle.CopyFrom(destination, source), and returns that destination. A
CopyFrom return sample can read the actual destination list without casting a
saved return register as a sampler argument. Runtime joins must still match the
exact caller, parent invocation and returned pointer; the copy, blackboard
publication and later consumer read keep their own lifetime/writer premises.
The target-group dictionary is owned by IActionEnvironment.Context, separately
from Beyond.ActionBlackboard and CenterBlackboard.skillInputData. A publication
endpoint cannot substitute for a later successful dictionary lookup/out-view.
The selected TryGetTarget observer keeps its out-view as raw bytes and interprets
it only after a true return; false does not itself prove a null or empty list.
The successful out-view can join CopyFrom's source handle, whose complete bounded
list is sampled independently. Lists exceeding the sampled item limit stay partial,
and Damage's persistent hit-count field is not presumed written by every call.

The retained target-results observation now joins the actual publication,
successful lookup, clone source and returned destination within independently
identified Skill/cast/Find-index domains. Logical counts and complete wrapper
payloads compare; clone source and destination have distinct container identities.
Empty results and singleton results are both observed. Every selected empty
normal-action Find still had physical query candidates, so overlap counts cannot
replace accepted-target counts. Source-binding success is not a Process census:
all raw Process ancestors must be checked before an action is classified as having
no Process. Matching endpoints retain ordinary forwarding, no extra writer/pool
reuse and allocation-lifetime conditions; they do not prove all writer histories.
Associating world queries by actual Find identity also preserves queries from an
earlier Skill Tick than their Damage consumer, which a Damage-Tick-only view omits.

Current native immunity cancellation has a separately checked bounded suffix:
after selecting the immune branch, ordinary Cancel marks the modifier cancelled
with the DamageImmune reason and the outer method returns Cancelled before the
ordinary HP tail. Cancel does not initialize realDelta. The simulator's conditional
settlement therefore preserves both entry HP and entry realDelta, requiring no
other prefix/callback/helper/external writer and ordinary execution; a zero entry
is a separate input fact. Typed cancellation outcomes can supply an external
policy port for regression, but do not predict the immunity predicate or timing.

The current immunity predicate has distinct predefined query and tag inputs:
IsDamageImmuneByLevel, DamageImmuneBySkill and DamageImmuneByDodge are not
interchangeable. Its direct compiled query/tag helpers differ from similarly
named registered wrappers; hook selection cannot use the wrapper name alone.
The tag lookup can consult entity, global and player/controller containers.
The shared nullable accessor at the mask callsite is selected through its actual
DamageDecorateMask generic context, not by a shared-code address match. Retained
identity spans preserve tag-container pointers, but pointer observation alone
neither supplies set/bitset contents nor establishes membership or mutation
history. A zero optional-mask snapshot does not make the other predicate inputs
converge. Existing source/provider/writer recovery should precede another capture.

The complete stored Endminf Dodge graph has no explicit Add/RemoveTag action;
its skillTags and tagDuringAttach lists are empty. PlayPerfectDodgeAnim and the
authored AllowNextSkill/visual/audio windows remain distinct from runtime dodge
immunity. Neither the animation action's authored span nor the root exclusive
or duration field establishes DamageImmuneByDodge membership. Trace the native
controller state and effective tag-container writers instead.

The current actor-data source candidate names common_character_perfect_dodge
and buff_common_dash, while retained Endminf request text independently names
the common Dodge. The request follows the completed immune cancellation. This
supports following the dash-buff/provider route; it does not select the immune
cause from temporal order, equate requested text with a live Data object, or
prove static managed-reference configuration is the effective actor provider.

A source-clock control replay can now own lazy successor clocks and retain every
retired call in the same checkpointed state. Handoffs use computed source
mapping/AllowNext time, an independent target predicate and selected ordinary
Stop effects. Unlinked starts remain external scheduling ports. Getter regression
locates the last completed computed timer through actual Skill, timer and call
sequence identities; observed timer values compare only. In-flight candidates
must converge or remain unresolved. This establishes selected kernel continuity,
not hardware-input ownership, global writer histories or every permission
transition. Runtime row order and invocation identifiers are not interchangeable.

Current HitStop source validation now covers the initializer as well as Tick:
Reset writes a zero elapsed value and the supplied duration/curve, then ordinary
successful registration forwards the same instance to the selected OnTick slot
with zero delta. Runtime setup callers agree with that source route, while the
Reset invocation itself remains unobserved. Owner construction, registration
selection and helper noninterference remain conditional. Instance elapsed must
use its own manager delta, not the Ability or Skill delta. A source interval
explains scheduling frequency but does not replace the actual manager TF/stamp
binding or justify equating those different deltas.

Attack-command regression now carries source Reset state through ordered update,
execution and Tick operations. The force Consume in this sample is nested in
active-instant Command.Tick, not in OnExecute. Game command storage, actual
callback helpers and selected dictionary entry remain separate from a controller
receiver or a similarly timed Skill request. No later Tick endpoint resets the
command state. Cache Refresh can reset permission false before its zero-delta
success tail recomputes it; omitting that tail creates a false delivery gap.

The shared FSM ManualTransit selected source chain checks transitions before
reading running, enumerates registered transitions in order and accepts the
first true checker; a missing checker is the explicit true path. Transit requests
Leave before storing current state and requests Enter afterwards. A model-owned
pending callback can retain these phases across a checkpoint. This establishes
ordered control, not complete CenterFSM registration/sort, live initial state,
predicate values or the actual virtual callback target. A computed request ID
can feed a conditional source-zero startup without reading BeforeCast as a
state or scheduling seed; held-driver callback attribution alone does not prove
the full input-acceptance filter.

The AbilitySystem current-Skill backing field and its posted cast-request field
are different typed carriers. A nearby request field must not stand in for the
current Skill, and SkillData castType must not replace runtime SkillType when
checking interruption priority. The provider's default-cache getter is reached
from mapping creation, while the request-time cache helper can instead reuse a
selected modifier or read movement/perfect-dodge overrides. A capture scoped to
the wrong parent helper can therefore be healthy yet never observe the default
getter; absent calls do not establish an empty provider.

Player command type and ComboController mapping command type are different
enums. In the selected ordinary path, Dash's player command selects the Dash
mapping key. A fresh source controller whose real map lacks that key takes the
invalid-selection return without clearing or rewriting an existing request.
This does not prove that the remainder of the Dash callback cannot change
controller state. Its owned body can update an existing offset modifier pack.
That pack's lifecycle can add a higher-priority attack mapping or remove its
handle and clear a request, so a disjoint direct request-field write is not a
noninterference proof. An absent offset pack with no external creator is a
sufficient selected source premise for skipping those writes; it is not an
observed runtime initial state. Dash-buff refresh and state-transition callbacks
remain additional effect boundaries. A later normal Refresh must establish its
whole constructor and permission tail before a preceding Dash can be excluded
from the request's writer cone; header ordering alone is insufficient. A
normal-input projection must remain distinct from a complete runtime cache
history.

The Skill-command request path has a separate residual constructor: after a
successful input-view lookup, unequal current normal/combo/ultimate skill IDs
select a temporary modifier with source short-cache duration and zero priority.
This is a stack construction, not registration into the real mapping queue.
The simulator can explicitly select that source branch for the configured
perfect-dodge ID; matching returned duration, payload presence or skill text
cannot prove the actual input dictionary entry or live slot values. A fresh
model-owned allocation label is not a prediction of the game's counter. If a
later source Tick expires both possible permission values to the same owned
request state, only that common endpoint may be used; intermediate visibility,
helper side effects and external CopyFrom/Dispose lifetimes remain unresolved.
Invalid source or typed-input validation must not be treated as an unknown
permission candidate.

Fresh stored dash-related sources include a Limited base buff which creates an
Infinity immune buff during enable; its nested weak-immune buff supplies the
DodgeDamageImmune tag, and a separate listener can request perfect-dodge effects.
The action auto-finish flag and limited duration alone do not establish removal
time: action-end reachability, MarkFinish processing, enable/disable and tag
storage effects remain separate joins. Request/event ordering does not select
the reason of a cancelled modifier. An existing string payload beside an enum
field is not proof of an active string assignment when its mode or direct-value
selection does not choose that payload.

Tag handles are value storage, so local validity and global ownership cannot be
collapsed. Candidate lower paths preserve duplicate direct tags and remove one
matching occurrence; parent membership must reflect remaining tags. The source
MultiTagHandle cleanup invalidates its own storage and requests pooled-list
disposal, without proving that every copied handle value becomes invalid or
that a retained list pointer was cleared. A future model may choose linear
opaque handles only with explicit no-copy/foreign-removal conditions; it must
not attribute native allocator identity or runtime immunity intervals to them.

The first-normal-attack motion projection now binds animation and root-motion
keys through the selected current StringPool. Its MoveTo uses RootMotion, so a
stored zero speed does not define zero movement. Step/snap distances, animation
keys and authored windows still need their actual displacement/target-gap and
collision consumers before producing a pose. Optional AnimationConfig decoding
has a bounded child/stage diagnostic; a partial or interrupted decoder result
is not source admission.

Rodin shape recovery must distinguish movement proxy and ability-detection
fields from combat colliders. The selected EnemyData's registry contains typed
source candidates while its EnemyTemplateData root remains undecoded, preventing
component-ownership admission. This is a Unity serialized managed-reference
payload, not a missing MemoryPack schema. The current MonoScript lookup can
resolve TemplateDataConfig despite exporter-time unresolved status. A legacy
inferred exporter branch is not an exact root reader. Model/render-helper joins
and an export omitting GameObject/Transform/collider classes do not establish an
installed collider or its absence; raw-root decoding and hierarchy availability
are offline gaps before shape/filter/activation binding.

The conditional HitStop port samples old elapsed/duration and keeps delayed
expiry, Clear-token effects, list/cache recomputation and actual Skill-group
reads separate. Each visit needs a fresh handle read because ordinary Tick can
replace it; post-Tick unknown handles are not carried forward from construction.
The source curve has weighted segments. The ordinary internal-call resolver
first searches the full signature, then on a miss can strip the parenthesized
suffix and search the same registration tree. Registration and resolution use
the same callback value storage under the selected ordinary string/map helper
conditions. This establishes a source binding path, not the actual runtime
cache or curve-object identity. The selected attack curve uses an unweighted
Hermite first segment and a weighted later segment with an inverse Bezier
parameter solver. CPU dispatch, floating-point narrowing and math-helper
semantics remain necessary before replacing supplied factors.

A narrower source-evaluated path now has a reviewed
[curve math declaration](../../scripts/game_data/contracts/skill_hitstop_curve_math_native.json).
It pins the selected native trio, instruction framing and literal tables for a
finite source-order transcription. Its consumer and arithmetic owner remain in
`tools/endfield_battle_sim/scripts/single_attack_hitstop_source.py` and
`tools/endfield_battle_sim/src/endfield_battle_sim/hitstop_rules.py`; the parent
curve-source reader has not been replaced. The bounded model evaluates both
CPU arithmetic variants and rejects differing final Single results. Unsupported
one-sided weighted segments and solver domains fail closed. This is conditional
source evaluation, not a general exact Unity curve implementation.

Actual Action-to-Start ancestry plus Data key-pointer equality can bind a key;
Reset arguments and first Stop then bound that specific lifecycle. Factor
agreement cannot supply that identity. Scoped source factors have now been
propagated through the simulator's group products, Ability arguments and owned
Skill-clock input histories without reading measured factors as inputs.
Library asset selection, ordinary callback/cache and floating-point premises,
unscoped lifetimes, allocation labels and incoming instance delta remain explicit.
A pooled pointer must not extend a closed lifecycle across unobserved reuse.

The dash before-damage listener also stores a direct inline Unity curve in an
entity-layer TimeDilationAction, distinct from the HitStopConfig key path.
Source event/action selection and the live Data/curve/listener binding remain
explicit premises; endpoint agreement does not select the node. Duration is a
BlackboardDouble reference, not an inline runtime Single: the selected literal
helper widens the serialized scalar to Double before the consumer narrows it.
Both slot and priority are GameplayTag values with a single four-byte tagId;
raw equality is not an ordinal priority comparison. The shared source evaluator
can admit inline action data with separate binding conditions while preserving
the original library-key premise set and arithmetic. This source/native
candidate does not itself prove a runtime owner resolver, actual Reset event
or complete instance effects. A partial simulator replay now advances elapsed
from the selected source-zero rule and independently computed Manager deltas,
evaluates supported inline samples, and preserves explicit ports where the
native inverse cubic takes its negative-discriminant angle/cosine helper path.
Neither observed factors nor Python transcendental formulas select that path.
Complete downstream input-history equivalence can reuse prior execution without
claiming that those helper implementations or runtime node identities are proved.
The remaining helper work is offline; repeating a healthy capture does not
recover its mathematical implementation.

Runtime HitStop lifetimes contain distinct curve pointers with different
factors even at computed sample position zero. A library key cannot be assigned
to one of those pointers by factor equality or temporal proximity. Actual curve
selection and lifetime continuity must join independently to source keys;
supplied curve samples and independently supplied cache reads remain explicit
conditions, including when they drive a simulator's Skill delta and its
same-cast-frame zeroing rule.

A complete selected AnimationConfig operation now exposes the Attack01
ClipMontageData root position and rotation curve fields as stored
Beyond.FAnimationCurve values. Their FKeyframe records retain named fields,
raw bits, exact spans and wrap words. The position domain is montage seconds,
not normalized HitStop time; empty rotation channels do not imply an effective
identity rotation. Independent Beyond curve evaluation, live montage selection,
movement time, start offset, scaling, step blending and collision remain joins.
The Beyond evaluator has its own time-solving control, so an unweighted flag
alone cannot authorize replacing it with a Unity/Hermite evaluator.

The simulator now has a separately qualified ordinary unweighted Beyond
curve evaluator, preserving its source Single arithmetic, Newton acceptance,
monotonic residual, old-parameter bounds and bounded bisection/limit return.
Its outer wrapper retains native count and exact-key/endpoint selection under
explicit initialized-context and Array fast-path/rank/storage premises; these
are not observed runtime interface-slot contents. The source library supplies
key data and counts, never measured curve returns. Scalar evaluation still does
not bind an animation clock or apply movement. Runtime patch selection retains
the separate boundary in [IFix recovery](ifix_patch.md).

The Charge Z consumer has selected arithmetic fragments which evaluate new
movement time before old movement time, subtract in Single, multiply by the
effective Z scale, then multiply each selected basis component separately.
Movement times, evaluated scale and world-Z basis remain explicit ports;
Nullable presence and intervening parameter/intermediate preservation are
separate conditions. Stored PosZ does not prove live Nullable.HasValue, and
normal Win64 alone does not prevent the caller from overwriting an intermediate.
This yields a Z-direction contribution, not a complete owner displacement or a
collision result. A separate cached-parameter clock path computes local
elapsed as Single global-minus-begin, applies scaled offset and the type-selected
curve divisor, and adds the selected movement delta only to the new sample.
PreLate chooses incoming versus cached Tick delta and advances global time after
Calculate. Those field seeds, active stack/parameter choice, stable repeated
reads and preserved advance state remain conditions; the Skill timer does not
supply them. Existing RootMotionData observations describe animation blending
and motion output, with a leading weight field, rather than the Charge clock.
For a selected ordinary MoveTo RootMotion path, disabled XY axes explicitly
supply null extra-speed references and absent XY curve values; the request
consumer copies these into ChargeParam. The selected no-speed caller paths
preserve the Z intermediate across the bounded direction/callback sequence.
Delivery identity and copied-selector retention still require an explicit
premise. This does not freeze arbitrary Param contents or replace the independent
clock, scale and basis conditions. The ChargeParam constructor's constant writes
alone cannot establish those nulls; the proved request writes/copies supply them.
Later complete Charge observations bind the actual cached parameter and clock
arguments to local-return and curve-sample times, with separately observed
scale/basis operands. These support conditional Z arithmetic without treating
Evaluate results as recovered asset keys or the Z contribution as the full
CalculateDelta vector. The ordinary native writer accumulates the full vector
into MoveInput's nullable charge delta; a selected charge consumer divides it
by its delivered delta subject to its near-zero gate. Actual input alias and
pipeline selection remain independent of matching the final Movement Tick
output. FixedTick's selected Reset projection preserves nullable presence while
zeroing XYZ when present, and preserves absence otherwise. Same-scope observed
resets support that projection; between-scope presence changes do not identify
the writer or establish object lifetime. Curve identity still requires actual
lookup/library and source-copy binding, rather than matching key counts or
sampled values.
The selected Z vector multiply is a complete leaf whose missing unwind entry
can be qualified by its bounded body, typed method pointer and exact caller;
this is not a general exception to unwind qualification. At that call point
the caller still carries the selected parameter pointer in saved RAX. The
hidden output buffer is distinct from the vector input and does not contain a
valid returned vector at entry. Capturing the parameter and scale at this use
point avoids treating an earlier parameter snapshot as proof of stability.
Unboxed curve headers and their Array length still do not expose key contents
or prove authored source identity. Charge-local elapsed and curve returns need
the actual Charge parent and caller, not a nearest-in-time skill association.
Normal attack motion sources differ: the first and fifth use
MoveTo RootMotion, the second FixedSpeed, and the third/fourth CustomRootMotion;
the fourth also contains a disable action. A node/field inventory must not be
promoted to a complete decoder for the Custom action's nested scalar payload.

The complete-reader cost was localized to recursively repeated native copy
proof validation before payload decoding. A successful isolated source cohort
uses operation-local reuse of the pure proof with its full immutable byte,
address, instruction and table inputs, returning detached results. Native,
source, pool and physical-EOF exits remain mandatory. Canonical shared source
files were locked by another operation and were not changed; this is not a
claim that ordinary export uses the isolated optimization or report artifacts.

The later single-attack recording now binds same-cast Skill/Ability endpoints,
delivered clock arguments, world Box query parameters, target endpoints and
Pack/Modifier/HP scopes. A bounded large-log streaming adapter retains the frozen
exact row semantics and all health/source gates; a short-budget refusal is not
evidence corruption or a reason to repeat a healthy recording. The simulator's
original kernel consumes variable observed clocks and explicit physics-result
boundaries while computing timer, Pack, damage and HP independently of outcome
targets. Query return counts do not identify individual colliders or establish
a standalone collision backend.

The same admitted recording now supplies attack2's own delivered clock prefix,
query geometry, attributes and settlement scopes. The child simulator composes
two existing Skill components, carries computed HP across preparation, and
coalesces the shared PreLate world frame instead of adding two world deltas.
The successor starts from its explicit preparation descriptor; no extra player
press is invented. This proves a conditional two-hit numerical prefix, while
the later frozen timer suffix, independent collision and full control recovery
remain unresolved. Current source decoding also shows multiple Find/Damage
pairs in attack3, so single-hit logic must reject it rather than silently omit
the later hit.

The child's reviewed input and Combo-offset contracts distinguish continuous
attack command generation from spatial movement. The selected held reader
subtracts positive Single timers without clamping. Nonzero movement clears
keep timers but still reaches the command-permission request. Combo offset is
a command mapping: a record threshold advances the normal-attack target;
replacement requests add the new mapping, remove the old handle, then publish
the new pack. Priority ordering is descending and stable for ties under the
original comparer/List helper premises. Neither these native rules nor
separate Start/End/Command roots prove the live controller-to-cache identity,
actual offset pack, selected mapping winner or original path selection.

A later scoped observation contains nonempty offset packs, so an earlier
no-offset projection cannot be generalized to complete input history. The
selected original CenterDashState entry reaches Skill.Interrupt with reason
six; for normal SkillType it requests CreateComboOffset with the Dash trigger
before its CastEnd request. Source normal-attack ordering and record thresholds
can then produce an offset target without reading the observed target as input.
The Dash offset lifetime comes from its own mapping configuration field, not
the request-time attack-cache override used while moving in Dash mode.

The simulator's existing offset owner now carries empty initialization,
source-computed normal timing, Dash creation, expiry/reduction and cleanup;
observed pack fields and later getter targets compare against that state.
Opaque allocation labels, source base-versus-skin selection and ordinary
helper/dispatcher premises remain explicit. A matching offset target does not
by itself prove the complete competing mapping queue, actual winner or every
external input origin. These contracts live with the independent simulator,
and do not widen the parent's stored-data reader into runtime simulation.

The later driver recording supplies controller/main-character/command-controller
endpoints, an actual scoped dictionary index and a directly nested
Execute/OnExecute/Refresh chain. Its CommandBase cache value is distinct from
OnExecute's CharacterMainCtrlSystem receiver. Matching those as one object is
a type error, even within a single synchronous scope. Multiple earlier Create
endpoints are compatible with the selected cached value; nearest-time matching
does not identify a unique producer.

The simulator's semantic request component now uses an actual Combo Tick delta
and a permission return from the same recorded PreLate parent. The native
allow-tail forwards that Boolean unchanged on its selected original path;
computed Single remaining/allow match the independent following request
sample. Original-path/storage-continuity premises remain explicit, and the
request string reference is an opaque identity token, not observed contents.
The later Clear entry is already empty, so its empty-to-empty return cannot be
used as the actual consumption point. Timeline modifier cleanup is a concrete
source candidate; request.modifierInstId alone does not identify the missing
owning Handle or establish that this candidate executed.

Current source/native projection also closes a useful simulator route without
another instance-identity capture. ComboCache creates an owned mapping Handle
per source modifier, forwards cacheEndByAction to request-clear-on-remove, and
preserves override=false as a missing override rather than a default duration.
Its end removes those owned handles. AllowNext creates one pack for its whole
source list; Init AddRange preserves source members/duplicates, while configured
always-allowed entries only append. A positive membership already present in
the source therefore does not need the unknown full configuration. The child
simulator now derives that predicate inside the authenticated authored window
at its computed Skill passed time, while retaining actual dispatch/lifetime
premises and same-frame end-order gaps.

The player command cache likewise reuses a CommandBase on a hit and resets its
time/state/delay/blocked storage; it does not enqueue one event per Create.
Controller update can consume or block before activation/Execute, and the
following Tick can consume an instant command or expire a cached command.
Those source rules require effective configuration and predicate operands.
The driver capture did not observe this state/Tick path, so aggregate input
and execution counts cannot select those missing operands.

Delivered delta is not equivalent to timer consumption: the selected prefix
includes an unchanged initial timer and a later unchanged suffix despite
normal delivered values. First-frame/other gates and continuous lifetime remain
conditions; temporal dilation correlations do not bind HitStop ownership.
Observed runtime duration/exclusive declarations agree with the stored source,
and a later Skill can prepare under Delivery.Tick without a true sampled
interrupt getter. An adjacent completed Command does not own that preparation
by proximity. These observations narrow the remaining ordinary-attack cache /
continuation join and must not be converted into a universal rejection rule
for false interrupt predicates.

The selected CenterAttack update requests direct TryCast only after an initial
nonempty attack-ID guard and a selected target branch. A later independent ID
read supplies the cast request. Its selected options ignore distance/angle but
do not force interruption: the original TryCast still checks interrupt
permission. Earlier allowed-pack and other predicate branches can permit before
the old canInterrupt getter; force true is a separate bypass. Request clearing
after normal TryCast return does not consume its Boolean or prove player-input
acceptance. A generic Delivery.Tick endpoint does not identify its live state
or these nullable options by name alone.

The checked ordinary replacement tail requests old Skill.Interrupt before its
new-current store. The selected reason's nonnull-owner/false-dontInterruptCombo
route requests CastEnd; a reached processor-clear block writes isCasting false.
The same later processor then skips duration update, subject to the earlier
entry/cooldown gates and no intervening casting write. This field differs from
Skill initialization, applied-cost and executed-exclusive flags. A conditional
simulation can compose this rule with source-bound delivery observations and
match frozen timer storage while keeping the old interrupt getter false. It
does not prove the actual old-current slot, cleanup traversal, state selection,
allowed-pack membership or full control recovery. These remain explicit runtime
binding gaps rather than conclusions inferred from the unchanged timer.

Passive string observations require a different terminal address from scalar
field observations: the selected producer's string sampler consumes an actual
managed string object after all pointer dereferences, not the address of a
string-reference slot. A current-Skill-to-skill-ID sample therefore must chase
both reference slots before reading the string at zero final offset. A null
current Skill can hide an incorrect terminal recipe until the first nonnull
instance. Production sampler tests need nonempty, empty and null strings plus
unreadable storage; decoding fabricated event rows is not such a test. Failed
capture endpoints can remain diagnostic observations but never satisfy healthy
runtime admission, and a missing collection inventory must not be fabricated.

The corrected control capture now binds one same-Delivery CenterAttack update,
its initial attack-ID query, the direct attempt's two further ID queries, actual
TryCast entry context, successful permission, old Interrupt/CastEnd and next
BeforeCast. Returned string pointers are forwarded consistently; their contents
are not sampled at those query returns, and the prepared name instead comes
from CheckCost and current-Skill snapshots. Same-session Skill/instance/Ability
and cast endpoints distinguish attack1 from attack2. A Skill object can be
recast, so pointer equality alone must not define a cast epoch or lifetime.

Observed CastEnd pairs change the same processor's casting flag from true to
false while leaving timer storage unchanged through Interrupt return. The live
combo-flag getters in these selected normal replacements are true. The complete
reason-seven original normal-return control flow still converges on CastEnd:
context presence, old skill type, offset presence, typed next-Skill lookup and
next data flag can select a prior CreateComboOffset request, but that helper's
normal return rejoins the same ending call. Its first parameter is an enum,
not an override Boolean. Null/invalid-context traps, original-path selection
and normal-helper premises remain explicit, and lookup/data-flag observations
or offset internals have not been supplied by the stored configuration.

These direct stop/delivery endpoints calibrate the simulator's shared stopping
rule. They do not supply later old-Skill OnTick reads, every cross-root input
cause or full control recovery. General rules can transfer between admitted
captures; concrete pointers, cast epochs, clocks and damage operands cannot be
spliced between them to create an apparently complete historical battle.

The selected physical Pack merged-zone arithmetic adds the defender and
attacker sides before subtracting Double one, then applies the ordered product
to base attack. Reassociation can change one ULP. The selected HP interior uses
the Minus modifier's negative nonnegative value, Double HP addition, virtual
setter dispatch and a final HP reread for realDelta. Setter guards, shield/death
branches and callback side effects remain explicit prerequisites, not removed
by a matching final HP observation. The child contracts and implementations own
these reusable rules; their generated reports are not their sole definition.

The executable slice exposes missing effective time and world bindings instead
of substituting render time or a guessed target. In particular, ordinary
Skill.OnTick inlines PeriodicTimer.Update after target selection: a hook on the
timer leaf would not observe that duration path. Capture preparation must check
physical call sites and supported ABI before requesting another recording.

For an explicitly selected character profile, existing CharacterTable attributes
can be joined by the stored level attribute and breakStage; CharGrowthTable's
skillGroupMap supplies exact SkillPatchTable skill IDs and rank rows. Keep
selection explicit, reject duplicate/missing rows and retain numeric attribute
IDs until their consumer meanings are independently proved. This is a stored
parameter projection, not final equipped attributes or live rank selection.
For Endminf, the third and fourth normal attacks' `atk_scale` and
`display_atk_scale` differ. Both fields must be retained: display data alone
does not establish hit multiplicity or the parameter consumed by an individual
DamageAction. This lane can advance offline while SkillData timeline decoding
and runtime factor evidence remain unresolved.

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

The battle simulator independently rechecks the selected ordinary Normal-heal
consumer on its retained cohort and preserves separate Binary64 stages:
healer output increase plus one, then receiver taken increase, then multiplication
by the actual GetFinalHealValue result. Replacing this sum with two separate
multiplicative bonuses changes the rule. Damage-time snapshots cannot substitute
for heal-time snapshots. A HealPack is a value carrier and may be copied across
calls, so different `this` addresses are not evidence of different healing
events. Bind actual GetValue children to their Dump invocation, and bind the
resulting snapshot array identities and action epoch to the formula pack;
do not select an association by amount fit or nearest timestamp. No unguarded
array-cell observer is needed merely to obtain the existing getter results.
Buff configuration can independently expose periodic timing and blackboard
references, but does not identify the actual item or creation-time parameters.

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
  Int32 defaults retain their compressed encoding. The shared metadata-default
  reader treats the F0 escape as a raw little-endian UInt32 after its prefix;
  signed callers keep the existing zigzag and sentinel rules. The selected
  literal/default source proof lives in `il2cpp/metadata_default_sources.py`;
  this does not identify other compressed protocols or admit runtime execution.
  This is derived-plan stored
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

## Skill frame conversion and interrupt marker

The independent [Skill timing consumer contract](../../scripts/game_data/contracts/skill_timing_runtime_native.json)
and [validator](../../scripts/game_data/skill_timing_runtime_native.py) authenticate
the selected native pair, method signatures and pointers, ordinary field types
and offsets, reviewed original-path windows, source operands and referenced
float literals. A missing or mismatched build, changed field or changed window
withholds every timing fact, conversion rule and conditional getter rule.

On the original native paths, `SkillData.duration` converts
`max(durationFrame, 1)` to Single and divides by 30; `exclusiveTime` and
`aiExclusiveTime` convert their corresponding signed frame fields and divide
by 30 without that clamp. `TimelineActionData.ToAction` converts both authored
start and end frames by the same divisor on the successful sequence-creation
path, retaining the integer frames alongside the converted values. This proves
30 authored frames per second for these conversions. It does not establish
the game's complete update cadence, asynchronous timing, timeScale handling,
or execution of a particular decoded timeline. Allocation ownership in
`ToAction` remains conditional.

The successful audit exposes `authoredFramesPerSecond`,
`durationClampMinimumFrames` and `originalPathOnly` with its authenticated
native identities. A consumer may project conditional seconds only when those
identities match the decoded source's native evidence. `exclusiveTime` is an
authored conversion, not a proved player recovery or animation-lock duration;
downstream selection and actual recovery conditions still need their own
consumer evidence. Selection through `useAIExclusiveFrame` is also separate
from the AI-exclusive getter's conversion.

The v2 consumer contract also authenticates the typed chain from
`Skill.m_durationTimer` to `PeriodicTimer.m_passedTime`, and from `Skill.m_data`
to `SkillData.exclusiveFrame`. On the original path with non-null timer and
data, `Skill.canInterrupt` returns true when passed time is **strictly greater
than** the exclusive-frame conversion plus epsilon; otherwise it returns
`m_markCanInterrupt`. Division and threshold addition use Single precision.
The epsilon comes from the native ADDSS instruction's referenced float literal,
approximately `1e-5` seconds; the audit retains its exact Single value and bits.
Equality with the threshold therefore falls through to the marker flag.
`Skill.canDash` calls `canInterrupt` and returns true on a true result;
otherwise it returns `m_markCanDash`.

The audit publishes these predicates as `conditionalCancelRules`, with
`getterOnly` and `originalPathOnly` boundaries and matching getter fact rows.
They describe the getters for explicit timer/marker inputs. They do not prove
which player commands reach them, timer advancement under all states, skill
priority or bypass branches, hit-stun, successful dodge casting, or a complete
cancellation acceptance window. A consumer must keep those gaps visible when
using the conditional threshold.

`Skill.MarkCanInterrupt` sets the named `m_markCanInterrupt` flag on its
original path. The reviewed `MarkCanInterrupt.ExecuteInternal` fallback calls
that method on its non-null environment path, but the cast and environment-to-
Skill ownership remain conditional. The reviewed fallback does not read the
action's `Data.priorityLevel`; no cancellation rank is inferred from that
inherited field. Setting the flag does not prove a complete cancellation
acceptance window or all command/skill transition conditions. iFix
interception remains outside every original-path conclusion above.

### Reading authored normal-attack windows

The admitted Endminf normal-attack SkillData sources separate target-selection,
damage-request, command-cache and allowed-next-skill declarations. A containing
TimelineAction interval is an authored scheduling candidate; it does not prove
that a target was selected, DamageAction settled damage, or a HitStop branch
executed. The third and fourth normal attacks contain multiple DamageAction
declarations, and the fourth's serialized windows are not chronological. Keep
source order and authored frame order separate rather than treating the action
array as a hit sequence or a duration as repeated damage every frame.

HitStop actions may sit inside IfElse child sequences, and an authored action
may be explicitly disabled. Preserve the stored duration, enable state and
physical parent path together; do not sum the durations into mandatory elapsed
pause time. The existing [HitStop consumer claims](../../scripts/game_data/contracts/buff_action_consumers_native.json)
separate named `StartHitStop` sinks and owned attacker/target reads from actual
sink operands, branch selection and effects. Complete time-dilation behavior
still requires its own selected-build proof.

The independent [action timing consumer contract](../../scripts/game_data/contracts/skill_action_timing_consumers_native.json)
and [validator](../../scripts/game_data/skill_action_timing_consumers_native.py)
now bind the original HitStop call block's closed Data slot, ordinary Single
`duration` field and named `StartHitStop.duration` argument. The later
`StartEntityTimeDilation.duration` call is a conditional continuation: the
incoming duration stack slot must remain unchanged through intervening callee
paths, the key-curve lookup must succeed, and iFix interception must remain
inactive. Stack preservation across those paths and actual original-path
selection are not observed. This proves a request operand and a conditional
reload/call, not the actual duration of freezing, suspended timer progression
or control recovery.

The same gate joins every selected call role to its nominal owner, exact named
method declaration and actual compiled target; signature and call-target checks
are not independent evidence. It authenticates the `OnlyAttacker`, `OnlyTarget`
and `Both` enum identities, but withholds an executable affect-selection rule:
temporary-list ownership, target normalization/filtering and complete loops
remain open. An authored `Both` request does not prove simultaneous actual
freezing of both sides.

ComboCache and AllowNextSkill authored windows differ from the root exclusive
threshold. Their command mappings and allowed skill IDs must be followed through
ComboController consumers and actual input acceptance; their action names alone
do not establish an effective buffer or cancel window.
The action consumer gate authenticates AllowNextSkill's named add sink and its
OnEnd-to-helper-to-remove edge, and ComboCache's selected add-mapping sink. Its
rows retain the joined caller/callee identities. That initial action gate alone
does not close AllowNextSkill's concrete Data/ObjectPtr layout or live ownership.
The independent combo contract below supplies a dedicated closed-layout and
argument/return-copy proof, without broadening the shared generic layout helper.
ComboCache's closed Data prefix and complete concrete suffix are proved, while
its cache expression, complete operand binding and effective cache duration
remain separate. Selected mapping and cleanup requests below still do not
establish complete input acceptance.
The simulator's `skill_timing.summarize_authored_skill_timing` retains these
declarations, source offsets, conditional containers and declared enable states,
with conditional seconds only from the authenticated timing rules. Per-source
windows and duration values remain generated report data.

### HitStop clocks and ordered interruption

The [HitStop clock contract](../../scripts/game_data/contracts/skill_hitstop_clock_native.json)
and its [validator](../../scripts/game_data/skill_hitstop_clock_native.py) separate
the original timer leaf from conditional local time-dilation fragments.
`PeriodicTimer.Update` performs Single remaining-minus-delta and
passed-plus-delta; when remaining becomes nonpositive, it writes zero remaining,
period into passed, and returns true. Skill's supported default duration leaf
uses the first named deltaTime argument. It does not establish the upstream
delta provider, earlier suppression, replacement selection or scheduling.

Entity time-dilation validity additionally requires a valid owner and nonzero
UInt32 scale handle. Its ordinary duration predicate accepts equality at
Single(duration + epsilon), with a separate negative-duration branch. The
normalization fragment divides old elapsed by duration in Single precision and
clamps to [0,1]. The curve result is the second operand of MAXSS against positive
zero; finite negative results become zero, while negative zero is preserved.
The reviewed OnTick fragments order sampling/scale request before elapsed
increment, optionally multiplying the increment by global scale. Treat their
composition as conditional on intervening ownership and control/dataflow, not
a complete OnTick closure. The ordinary manager checks validity before tick;
OnTick overshoot alone does not establish same-call removal or control recovery.

The selected Skill delta fragment has two Single multiplications, global scale
then entity self scale, with an explicit ignore-global selection. That fragment
does not prove its incoming value, complete delivery to Skill or the effective
scale's modifier merge. Thus HitStop elapsed, Skill passed time and wall time
must remain separate quantities. Neither timer completion nor a true cancel
getter alone restores player control.

The battle-simulator subproject's reviewed Stop bridge separates instance
handle clearing from group-cache effects. The selected ordinary Stop fragment
skips Clear and Sync on a zero handle; after a normal Clear return it requests
Sync. Clear reads the owner's typed group, requests physical removal with the
old handle, then clears the instance handle. The selected removal scan requests
RemoveAt, recomputation and propagation only for a registered group's first
matching handle. Clearing the instance handle therefore does not imply a
modifier was removed or the cache returned to one. Recalculation starts at
Single one, snapshots count, and rereads the list and cache before each Single
product. List helper effects and propagation remain opaque. The physical
removal target is distinct from the named metadata method; selected-fragment
grammar is not complete entry-to-fragment continuity or whole-method dataflow.

Admitted input records also support a local control-delivery distinction:
a current normal skill can have positive remaining time and a true interrupt
getter, followed in the same Command/Transit by another Skill reference's
Cost/Tag/State checks and BeforeCast. Preserve exact call ancestry, same-reference
guard endpoints and every candidate. This proves observed preparation after
an interrupt check, not HitStop ownership, OS-input acceptance, complete control
recovery, completed casting or a hit. These rules and observation consumers
are maintained in `tools/endfield_battle_sim`; generated reports are not the
sole definition of the evidence boundary.

The simulator's separate propagation contract now checks selected cache-to-scale
fragments: Single cache/external-register multiplication, negative-only clamp,
conditional `m_timeScale` store, then a member-specific scale argument request.
The original adapter keeps the tolerance decision explicit; a separate checked
tolerance contract now derives it from supplied reads. A member chooses
its supplied unscaled register or rereads its own group's effective field,
then multiplies `m_additionalTimeScale` before requesting its owner's setter.
Do not replace that read with the originating group's cached value or invent a
constant-one unscaled register. Entry continuity, external register provenance,
complete list traversal and setter effects are still unproved. Recorded paired
OnTick endpoints include both zero-delta zero-to-nonzero handles and nonzero
ticks replacing one nonzero handle with another. Handle stability therefore
cannot establish HitStop ownership or lifetime; repeated receiver pointers are
also only endpoint equality until reset/reuse and intervening writes are proved.

The selected tolerance program compares an absolute rounded Single difference
against the larger of relative magnitude and a runtime `Mathf.Epsilon` floor.
Strictly smaller differences skip the store; equality admits it. Literal inputs,
mask and typed static-read source are checked, while runtime Epsilon and FP state
remain explicit. The complete item scale helper independently proves unscaled
Single one versus its own group's effective value, then additional-scale
multiplication. Its named OnTimeScaleChange wrapper evaluates the helper before
checking owner nonnull and requests notification dispatch; this is not a proved
callback field write. That helper's constant-one proof does not establish the
separate inline propagation register's source.

The independent Ability clock-prefix proof connects ordinary PreLateTick entry
delta to its first scaled-result stack store. It validates the inherited
BaseComponent entity field and complete original nonnull prefix. The first group
read supplies self-cache, a later entity/group reload supplies ignore-global,
and TimeManager supplies global scale. These reads do not establish identical
group instances or a notification-to-Skill causal chain. Subsequent stack
delivery to Skill.OnTick, concrete notification dispatch and scheduling remain
open. Durable simulator contracts preserve these separate proof scopes.

The simulator's callback contract independently proves one selected dispatcher
equality branch and the complete TickComponent.OnTimeScaleChange callback.
Its ordinary branch requests Object.GetType and opaque formatting/metadata/emission
helpers without using the incoming scale or directly storing an instance-scale
field. This does not prove absence of helper side effects. The replacement branch
forwards the scale. Exhaustive declared-method inspection finds no same-name or
same-slot AbilitySystem override, but metadata inheritance does not prove the
live class discriminator, vtable or selected inherited callback.

A separate Ability delivery contract proves selected stack reloads through
normal nonvolatile preservation to the two float arguments of Skill.OnTick;
the zero hidden MethodInfo argument is not a gameplay Boolean. The caller
selects replacement pause AL or the typed entity pause field, checks the opaque
enumerator step and supplies its nonnull current as receiver. A checked local
predecessor bypasses reload, while the adjacent token-zero path enters reload.
Whole-method ownership/reachability and initial scaled-store-to-reload continuity
remain open, as do live Skill identity and later timer effects. Equal stack
offsets or metadata method names cannot close those joins.

The separate Skill entry proof checks initialization and cast-type return gates,
then compares the requested frame-count result with the cast-start field. Equal
values zero both retained delta arguments before continuing; unequal values
retain them. The cached function and named frame-count resolver request are
distinct from proof of the runtime target or returned frame. This rule is not
an early return and does not show that all skill processing stops. Conditional
regressions preserve these boundaries and do not admit a complete battle clock.

The simulator's ordinary Ability extension now proves selected register
preservation without relying on later stack reload: the primary scaled delta
has no intervening destination in the complete selected local CFG before the
Skill call. The second delta has a closed set of two Single product origins,
using either one or an earlier manager-scale read with the incoming delta.
The later manager-reason read and opaque alternative selector remain separate
inputs. Exact instruction boundaries, external exits and normal call sites are
checked; prefix bindings, normal ABI/frame preservation and actual selection
are conditions. This does not prove the entire method or exception path.

A separate continuation proof joins Skill entry to duration updates when the
cooldown list is null, replacement/readiness gates admit the ordinary path,
the processor is casting and the Skill is not paused. The matched PeriodicTimer
target's inline update uses the primary delta and normalizes expired timers;
its body and the named Update body are independently checked. Timer operands
are reads after the initialization helper. Same-frame zeroing therefore does
not imply no subsequent writes: an already-expired timer still normalizes.
Conditional composition rejects overrides of the derived delta and requires
explicit path and carrier continuity. Present cooldown-list paths, opaque
initializer effects, live scheduling/identity and later Skill behavior stay open.

The simulator's present cooldown-list extension proves the count request,
per-iteration list/count/array/element reloads, independent unsigned bounds and
opaque selector-four predicate request. The signed helper result bounds the
loop; it is not identified with any independently reloaded count. All true
iterations reach the common ability gate, while the first false result exits
to a separate route. Conditional replay consumes exactly the visited sample
prefix and never forges a null-list premise. Generic helper semantics, collection
stability and actual cooldown effects remain unresolved.

The post-duration extension distinguishes completion requests from incomplete
threshold checks. Completion reloads timer/ability and requests Ability Tick,
exclusive callback and CastEnd. Incompletion compares fresh passed time against
Single frame-to-seconds thresholds with subtractive epsilon for inclusive cost
selection and additive epsilon for strict exclusive selection; an interrupt
marker can also select the exclusive callback. Post-cost reads stay independent.
These are ordered requests, not proven helper effects or player control recovery.
Composition derives the completion Boolean and primary delta without allowing
caller overrides, while requiring explicit carrier continuity and later reads.

The simulator's helper-effect extensions now prove pointwise stores. Exclusive
callback invocation precedes setting its executed flag, so the flag is not a
pre-call reentry lock; later owner reads remain independent. ApplyCost's checked
low-query path writes the applied marker even when debit requests are bypassed.
Its positive-query out-store path separately preserves an initial comparison
sample while a post-initializer sample can supply the stored Ability amount.
Neither store establishes the resource helper's actual debit or final state.

Selected CastEnd paths prove an initial casting early return, finish-dependent
executing-state stores and processor cleanup: clear target/jump storage, set
processor casting false and clear a freshly read context after an earlier payload
copy. The nonnull raw-action path enumerates TimelineAction entries and invokes
SequenceAction.End when its sequence is present. That method requests virtual
AbilityAction.OnEnd for states one or two, then stores ended state three for
each nonnull action. Stable storage, count/helper dispatch and ordinary callback
returns remain explicit conditions; callback effects are not supplied by an
enumeration proof. A separate ordinary tail in AbilitySystem._OnCastEnd clears
its current-Skill reference. TryCastSkill's selected local windows supply either
the direct system callback method or a wrapper closure; the Skill callback field
is written and later loaded by CastEnd. The complete wrapper invokes the system
callback before an optional external callback. These local operands and typed
stores do not prove continuous register/object identity between windows, ordinary
delegate-constructor effects or external-callback noninterference. Reaching the
selected owner therefore remains conditional, and a clear does not establish
idle control. Ordinary no-current-Skill request admission has no Center-idle
operand: request availability and physical control restoration are separate
boundaries. The simulator connects computed completion, owned handle cleanup,
selected clear and a later source-cache request under explicit completion ports;
its synthetic nonnull-inventory regression is not a runtime inventory witness.
The reviewed declarations live in the battle simulator's
[cleanup](../../tools/endfield_battle_sim/contracts/cast_end_cleanup_native.json)
and [callback-tail](../../tools/endfield_battle_sim/contracts/cast_end_prefix_native.json)
contracts. Existing perfect-dodge natural-completion samples show casting clear
and a null current slot at the same parent-call return. Retired pooled Skill
ticks can continue after that slot is null; object lifetime is not slot ownership,
and these samples do not by themselves prove normal-attack completion.
Context identity, cross-window/live callback binding and control restoration remain
unresolved. Cooldown readiness
uses absolute remaining versus epsilon; false-predicate updates use the second
Skill delta and the second independently returned timer, then rejoin the ability
gate. Candidate selection keeps a strictly smaller remaining value and replaces
ties. Index helper bounds are checked, while live interface targets and coherent
repeated reads remain conditions.

Special-type cooldown recovery now has a checked clean-cache path: request
attribute 93, read Double, narrow to Single, multiply the second Skill delta and
join the common timer update. Dirty recomputation and live owner selection stay
open. Count interface dispatch and shared List body registration are checked
separately from actual closed runtime class/slot binding.

The CostAtb core additionally proves the epsilon availability check, initial out
zero, fresh ATB subtraction and ordered setter clamp/store. Setter callbacks
precede a fresh returned-ATB read; returned remainder and net out amount use
explicit Single stages. Its following pause branch copies the configured skill
recovery interval, then requests consume recording with the original source and
Single widened to Double. Final balances, recorder effects and live source/manager
identity are not established by those pointwise stores.

The [existing-export curve reader](../../scripts/game_data/skill_hitstop_curve_sources.py)
joins admitted HitStop field byte ranges to current StringPool pages and the
named HitStopConfig object, retaining its serialized-object identity and read
bookends. Its explicit asset-map join compares source path, offset, PathID and
Unity type against the exported header, with complete map-input hash bookends;
the header's source-file identity is independently checked against the store.
An absent or unmatched map remains unresolved. This exported physical join does
not identify the object actually returned by the runtime resource loader.
Referenced curves have nonzero keys, tangents, weights and wrap modes;
they are not constant-zero freeze curves. Current pool resolution is not an
independent historical pool authentication when an older intake omitted page
hashes. Runtime configuration selection and Unity weighted-curve evaluation
are separate evidence joins. Do not substitute linear interpolation or integrate
stored duration into a claimed wall-clock pause.

The [configuration-load contract](../../scripts/game_data/contracts/skill_hitstop_config_load_native.json)
and [validator](../../scripts/game_data/skill_hitstop_config_load_native.py)
authenticate a narrower bridge: the reviewed `_LoadConstConfigs` callsite
supplies the HitStopConfig key and closed MethodInfo, then stores the returned
reference in the typed hitStopConfig field. Its physical call target contains
an authenticated call to the named ResourceRouter path helper. The selected
generic-entry lookup did not join that closed MethodSpec to this physical
target; supplying a MethodInfo does not by itself identify the callee's closed
implementation. Keep `compiledTargetClosedDeclarationProved` false. This is a
missing registration/warmup join, not proof the request never executes.
The three-string composition helper, path-hash forwarding and selected resource
result still need their own joins to the exported asset. Neither the exact
load key nor the exact exported asset-map match establishes runtime selection.

The [combo consumer contract](../../scripts/game_data/contracts/skill_combo_acceptance_native.json)
and [validator](../../scripts/game_data/skill_combo_acceptance_native.py) follow
the original `CheckCanInterruptCurSkill` predicate in order: no current skill,
membership in an allowed pack, plunging-start equality, plunging-end equality,
new skill priority signed-Int32 strictly greater than current priority, then
current canInterrupt. Equal priority falls through. An allowed-pack hit bypasses
the later priority/getter branches of this gate; it does not bypass every cast
guard or prove that a player input was accepted. Collection receiver, normal
returns, selected originals and live operands remain explicit conditions.

AllowNextSkill's dedicated closed-layout witness binds the inherited Data
reference, query-handle field and entire returned ObjectPtr suffix. Selected
normal ObjectPtr output writes and controller/action copies cover its reference
and identity fields together; open-generic zero offsets/sizes are not used as a
closed value layout. The action's allowed-list argument reaches the selected
AddAllowedNextSkillPack request, and the returned carrier is retained for
cleanup. Init requests AddRange on the existing pack list, then adds an
always-allowed string only when Contains is false. No clearing or pool reset is
inferred. Live ownership, handle lifetime, collection callback ABI and original
path selection remain separate from this closed storage proof.

Combo mapping refresh clears the effective map and visits command slots in the
reviewed order. A nonempty runtime queue supplies item zero; an existing empty
queue supplies the base GetValueOrDefault result; an absent queue copies a base
value only when TryGetValue succeeds. The copied value is the complete selected
MappingModifier carrier, not only its skill string. This does not prove queue
priority ordering or the default helper's returned bits. Removal searches
backwards by exact UInt64 instance ID, requests Remove(value) on the first
match, and refreshes even without a match. Do not infer Remove's actual removed
index without its comparer semantics. Handle cleanup re-Locks the owner for
each requested stage; a failed Lock skips that request, and request/offset
cleanup flags remain explicit operands rather than inferred runtime settings.

### Input predicates, caching and pending casts

Whole-fight acquisition must cover the known input/control, clock, movement,
numeric, Buff/resource and enemy-behavior lanes together. A short command-only
profile is not a complete battle observer. Full paired cast returns and Skill,
Combo and Buff deltas require their actual physical signatures; an entry context
under Delivery does not cover every action path. Keep by-value indirect
aggregates distinct from explicit byrefs, and derive string roots from the
actual argument representation (unboxed storage has no object header).

Acquisition audits keep three important distinctions explicit. Byte reads have
one-byte storage even when projected from a larger raw span. AbilitySystem AP/SP
snapshots do not substitute for BattleManager's shared ATB or its recovery
clock; an exact cost caller filter on SetAtb excludes other writers. Finally,
TimeManager's managed frame counter is not automatically Unity's frame counter
used by the Skill first-frame condition. Qualified field snapshots and actual
branch results remain separate claims.

The simulator's maintained roadmap owns the next combined recording procedure.
Static collider hierarchy/animation curve decoding, retained-log joins and
general metadata/vtable/manager writer-history proofs continue offline; their
unfinished state alone is not a reason for another recording. A further capture
request must identify a material numerical, spatial or control ambiguity that
the retained evidence cannot distinguish, and prepare all known additions
together before asking the user to record.

The [cast gate](../../scripts/game_data/contracts/skill_cast_gate_native.json)
joins active-map ContainsKey/get_Item, optional interruption, the nonnull Skill
guard and CanCastToTarget. Missing keys return false after normal logging;
null selected Skills do not become a false geometry result. CanCastSkill's
skipAngle/skipDistance parameter order differs from CanCastToTarget's
skipDistance/skipAngle order, and the actual forwarding is checked. The view
overload explicitly sets skipInterruptCheck false. Target admission evaluates
readiness, optional CheckCastDistance with ignoreOutOfRangeStrategy true, then
optional CheckCastAngle, preserving short-circuit behavior.

Readiness reaches an independently checked native helper, not an invented
alias for IsAvailable or CheckCd. Its first invalid/null owner returns false;
its repeated owner lookup must yield a nonnull owner or take the exceptional
path. A selected type-check result is followed by the local cooldown helper,
CheckCost, CheckTag and CheckState in order. Helper internals, owner lifetime,
distance/angle geometry and replacement selection remain explicit inputs.
Repeated reads/calls must not be folded into one observation without a stability
premise.

The [request-cache contract](../../scripts/game_data/contracts/skill_request_cache_native.json)
binds CmdType.Attack to the real-map BattleCommandType.Attack request and copies
the actual received MappingModifier carrier into construction; this route has
no new input view. The provided closed MethodInfo is checked, while the
physical helper's closed compiled identity and collection effects remain open.
An empty selected skill ID leaves the previous request unchanged. A nonempty
ID requests disposal of any previous owned-input copy, then installs the new
request with selected ID, instance ID, cache time and allow=false. There is no
old/new priority comparison in that construction. Optional input CopyFrom uses
the original view, which must not be conflated with a possibly overridden
request skill ID. The selected Nullable byte propagation is authenticated;
pool allocation, GC preservation and target-handle lifetime retain their stated
conditions.

Cache-time selection uses the supplied modifier value except for Attack's
selected movement-mode override, then the current-skill/perfect-dodge override.
The override values come from the actual configuration provider, not guessed
durations. The [dispatch contract](../../scripts/game_data/contracts/skill_cast_dispatch_native.json)
proves that request Tick first recalculates allow, subtracts allScaledTime in
Single precision and retains the request only when the result is strictly
greater than its native epsilon. Equality expires it. Expiry disposes the
retained input when present and clears the whole Nullable. Tick does not cast.
Visibility getters only inspect HasValue and stored allow; they do not recompute
readiness, check remaining time or consume the request.

The [player-command contract](../../scripts/game_data/contracts/skill_player_command_native.json)
connects PlayerCommandController.Execute through the typed GameWorld/AIManager
receiver to CharacterMainCtrlSystem.OnExecutePlayerCommand and Refresh. Refresh's
Boolean controls command-specific fallback branches; it is not propagated as
a universal command-accepted result. The selected cache read reaches
CenterStateMachine._ToSkill or CharacterSkillSystem._TickToCastSkill. The latter
checks CanCastSkill with angle skipped and distance checked, then CastComboSkill
checks again through the view overload with both geometry checks enabled.
Passing the earlier check does not guarantee passing the later one. CastComboSkill
prepares a pending record with castType and casting fields and requests an AI
mode switch; it does not itself call TryCastSkill or DoCast.

TryCastNormalAttack is a separate first-normal-Skill-list path, not a proved
consumer of the cached request. TryCastSkill's true result also has a
switch-to-buff shortcut distinct from its ordinary current-Skill/state writes.
DoCast returns void, and some callers inline cast initialization instead of
calling that method. Do not turn every true TryCastSkill result or a method
named CastComboSkill into evidence of a new skill start.

The [pending-cast contract](../../scripts/game_data/contracts/skill_pending_cast_native.json)
closes a conditional consumer definition path through
CharacterCastSkillBehavior.OnEnter/OnTick, CharacterAIBrain.GetComboSkillData and
the selected pending selector. OnEnter resets timer/success and stores the
returned record. OnTick replaces it only for a nonnull newly returned record
whose casting flag is false, then permits retry. A null current record returns
without inventing success; failed TryGetSkill writes success=false without a
pending casting write.

The direct attempt rotates, obtains the pending input's named getters and
calls AbilitySystem.TryCastSkill with authenticated argument transfer. The
switchToCenterBeforeCast branch may instead request PlayerController.CastSkill
after a successful center switch; it is not a synchronous success claim.
The air-check receiver comes from a global provider chain, so its result must
not silently be substituted with the pending entity's movement state.
The direct TryCastSkill result always updates behavior success. Only true
causes a fresh read of behavior.m_skillData and a casting=true write when that
post-call reference is nonnull. Callbacks can replace the field; a claim about
the original record requires an explicit identity-stability premise.

The unresolved join is now specific: the requested AI mode must be bound to its
CharacterAIModeData/config entry, configured graph/behavior tags and actual
callback dispatch. Class names and a numeric mode do not establish selection.
Pending selection also depends on collection/ObjectPtr coherence. The inherited
entity carrier is now a named, directly authenticated AIBehavior.m_entity field:
the empty CharacterAIBehavior intermediate class has no offset table because it
declares no fields. It is not the declaring owner. The pending consumer contract
checks every parent edge from CharacterCastSkillBehavior through its selected
closed generic parent to AIBehavior, and binds the native loads to that owner's
Entity reference field. The independent `skill_behavior_entity_native` contract
accounts for the complete concrete layout, including necessary alignment gaps,
and checks inherited-layout stores in the concrete constructor, the consumer's
entity read, and the original AIBehavior.Init argument store before its barrier
call. The generic
data slot is proved only for this closed reference instantiation; no open generic
placeholder offset is used. This proves layout and the selected original write,
not that a live instance was initialized or remained unchanged.
Cost/tag/state internals, geometry, runtime replacements and
callback/scheduler ordering remain separate. This is a connected conditional
definition chain, not observed end-to-end player acceptance.

The [input execution carrier contract](../../scripts/game_data/contracts/skill_input_execution_native.json)
adds the original AbilityAction.AssignData/ReAssign environment stores, the
Ability.Init source-Skill store and the Skill/Ability instance-id getter reads.
DamageAction's exact generic-parent chain reaches the declaring AbilityAction
owner. An environment reference must not be cast blindly to Ability: retain
the explicit assignment and independently observed Ability identity. Rebinding,
object reuse and copied cast identifiers prevent a pointer or numerical id from
being treated as a globally unique cast occurrence. Synchronous input ancestry
ends when that call returns; it cannot be inherited by a later tick.

The [battle input capture recipe](../../scripts/game_data/contracts/battle_input_capture.json)
observes game-action callbacks, player commands, cast predicates, request-cache
entry/return snapshots, pending-record state, skill/Ability lifecycle and damage
processing with ordinary paired observers. `battle_input_capture_sources` derives
the closed request storage from the selected request construction/clear proof;
open Nullable field offsets are never used. Snapshot coherence is not implied
by one guarded read. `battle_input_inspect` admits only complete healthy retained
sessions through the shared reader and keeps boolean predicate results, cache
contents, preparatory execution and damage processing separate. A false inner
predicate is not a global input rejection; a true cache refresh or void normal
return is not a completed cast. A damage-processing return is not automatically
a damaging hit. Cross-tick environment/Ability matches remain conditional
candidates, with request ownership and lifetime explicitly unresolved.

The existing numerical captures contain no complete input stream. Default input
configuration and Lua callbacks can explain possible operations but cannot
reconstruct missed presses or the user's live rebinding. The new recipe is not
an OS key log and does not prove every physical press was delivered. Capturing
DoCast alone is insufficient because initialization can be inlined in callers;
unsupported aggregate or oversized signatures must not be forced through a
smaller generic hook ABI. Live coverage remains to be observed separately from
successful preparation and compilation.

Stored key maps are subject to export freshness independently of the native
observer ABI. If the installed asset layers differ from the export provenance,
the input-source reader may retain authenticated stored-export observations with
`currentInstalledDataProved=false`; it must not label those defaults or Lua
handlers as the current live configuration. This does not authorize extraction.
The [stored input-source contract](../../scripts/game_data/contracts/skill_input_bindings_sources.json)
selects named InputSetting objects, local UI PPtrs and bounded Lua text sections.
The stored Battle defaults separate Mouse0 press/release and digit/Alt-digit
actions. AttackButton's authored text connects the attack actions to start/end
requests with cursor/button/mode gates. MainHud button references identify jump
and sprint actions, but their default Space/Shift/Mouse1 mapping and long-press
ultimate acceptance remain unresolved. The separate
[native input contract](../../scripts/game_data/contracts/skill_input_bindings_native.json)
authenticates key/timing enums, callback declarations and bounded argument-save
and held-field-write spans. Entry-to-span argument/receiver continuity is an
explicit premise, not a whole-function path proof. Held state alone establishes
neither repeated-attack scheduling nor successful cast acceptance.

Complete retained input observations now distinguish a held attack's game
action callbacks from the repeated player-command stream. A cache refresh may
return false while a previously stored request is still present; neither that
return nor the mere presence of the cache is a global input-rejection or cast
acceptance label. Entry/return raw snapshots must be compared separately.
Some successful Refresh calls exit with allow=true even though an enclosed
AllowNext call observes allow=false at both its entry and return. This is not
a counterexample to the selected constructor's initial false flag. The
[Refresh-tail contract](../../scripts/game_data/contracts/skill_request_refresh_tail_native.json)
locates a postconstruction virtual dispatch with three zero Single arguments.
Conditional on the selected ordinary Combo Tick target, Tick calls AllowNext,
transfers its Boolean result into a request replacement and writes the whole
request back. That copyback occurs after the child observer's return snapshot.
The recorded child caller addresses match the selected Tick callsite and the
parent/child controller identities agree. The parent return snapshots conform
to the allow-byte change while retaining the other bytes.

The tail returns true after normal dispatch completion, independently of whether
Tick retained or expired the request. The constructor's initial false flag and
the public Refresh exit flag are different boundaries. The new proof is bounded:
generic dispatch branch reachability, register/stack carrier continuity, live
virtual target/IFix selection remain explicit premises; existing matching Tick
evidence owns expiry. `battle_input_refresh_cases` generates conditional tail
regressions from exact observed child callsite/controller/string-pointer matches
and raw snapshots. It excludes false Refresh results rather than inventing their
missing construction operands. This is not a complete simulator replay.

`battle_input_request_links` preserves exact cache-pointer matches within a
recorded command, all matching getter/CheckCost/BeforeCast candidates and observed
Clear boundaries. Equal skill text can occur at distinct managed-string pointers;
text equality cannot replace pointer identity or a request-carrier transfer.
Historical cross-command matches retain unknown ownership/lifetime, and a common
command ancestor does not prove which particular getter value fed the cast.
The recorded execution lane also observes different cast identifiers on the
same Ability pointer/instance-uid pair. Treat the uid as an object observation,
not a unique cast key. Explicit same-thread ExecuteInternal/ProcessDamage
ancestry with equal action/environment identities is a stronger join than a
historical pointer match, but a ProcessDamage true return still does not prove
HP loss. Missing Skill.Init or pending-behavior events are coverage gaps and
cannot by themselves identify inlining, reuse or an alternate execution path.

The [request delivery contract](../../scripts/game_data/contracts/skill_request_delivery_native.json)
now authenticates the selected `_ToSkill` fragment that forwards the cache
getter's returned string reference into `_TryGetSkill`, with a stack by-reference
Skill output and a false-result edge. Its caller classification checks physical
call targets and the `GetNextSkillId` wrapper's tail jump. `GetNextAttackId` and
`HasNextAttackRequest` are query callers; their getter observations must not be
counted as skill executions. The fragment does not yet bind the lookup's output
to the later selected pending record or cast.

The [cast identity contract](../../scripts/game_data/contracts/skill_cast_identity_native.json)
separates Skill/Ability field carriers from individual casts. The recorded Init
caller is the runtime-data refresh path, and recorded BeforeCast callers belong
to the selected TryCastSkill tail. This identifies the immediate native caller;
it does not recover an unrecorded caller above TryCastSkill. Original
AssignSkillCastInfo copies a nonzero supplied ID, origin and cost bits. Its zero
branch assigns one counter read to the ID, independently reloads for a wrapping
increment, uses sourceSkill as origin and writes positive-zero cost bits. The
two reads are not assumed equal, the counter write is not atomic, and copied
IDs and UInt32 wrap preclude a global uniqueness promise.

`battle_input_delivery` matches these native receipts to the admitted capture
and retains all earlier matching Init snapshots as candidates. It keys observed
BeforeCast occurrences by thread/invocation, never Ability UID or cast ID alone.
Source-origin equality does not select the unobserved assignment branch. Its
simulator cases separate observed Init argument-to-field pairs from portable
identity-rule fixtures. Sequence order and command boundaries do not supply
frame IDs, authenticated intervening writes, object lifetime or cross-frame
delivery. These missing joins remain explicit; the real battle factory stays
closed.

The [request transfer contract](../../scripts/game_data/contracts/skill_request_transfer_native.json)
now follows the middle of `_ToSkill`. The first lookup's output is read for the
typed SkillType guard, with an unsigned comparison against the explicit upstream
register operand. A null output leaves the selected nonnull path; the gate does
not name the opaque null-exit helper's complete exception semantics. The later
admission independently reads a skill name. A finite local control-flow check
proves that this second name and the separately returned view's target reach
CanCastSkill under normal Win64 calls and coherent local stack assumptions.
The view's last word overwrites the first lookup output's stack slot. Neither
that reused slot nor the first Skill pointer is a persistent execution identity.
The destination declaration and its Center-state consumer are described below;
runtime getter type, same-object handoff and scheduling remain separate open joins.
`battle_input_handoff` checks the retained read/admission caller sites and exact
argument equality, preserving all same-command candidates. The command is an
observed ancestor; an unrecorded `_ToSkill` invocation is not manufactured from it.

The [pending storage contract](../../scripts/game_data/contracts/skill_pending_storage_native.json)
authenticates the request record's complete direct instance-field set and parent
chain. There is no direct selected-Skill field, but the stored input contains a
nested cast-info originSkill reference. That origin is not automatically the
Skill selected for execution. The consumer prechecks by the current record's
skill ID and independently reloads record input for the later TryCastSkill call.
Write selection searches forward for the first resolved-entity match; read
selection searches backward for the last. Neither filters on casting or castType.
Both fetch the matched index again, so the compared record and final record are
not assumed identical. A null final write fetch requests a pooled record; a null
final read fetch returns null. A null entry encountered during the initial scan
does not become a normal miss.

Dispose directly clears only the target-handle slot. ClearAll additionally
requests zeroing the whole input payload; opaque helper side effects remain
outside the direct-store proof. The pending-list getter exposes the mutable
list reference, so the selected writer inventory is not a complete writer set.
Stable list/record lifetime across frames and observed behavior dispatch remain
conditions, not consequences of the field layout.

The [normal attack delivery contract](../../scripts/game_data/contracts/skill_normal_attack_delivery_native.json)
also distinguishes direct casting from pending dispatch. On the selected
CharacterAIComponent normal-return path, a false CanCastSkill stops the attempt;
true reaches TryCastSkill and its Boolean return is forwarded. Both angle and
distance checks are skipped at this admission call; interrupt checking is not.
The selected name and target are preserved while AbilitySystem is separately
read for admission and execution. A separate CenterAttackState direct-cast
fragment does not consume TryCastSkill's Boolean before its later clear path.
Neither a Clear observation nor a BeforeCast event substitutes for that missing
return. These static paths do not assign the retained sample's unobserved
upstream callers or prove which frame delivered a particular request.

The [Center blackboard writer contract](../../scripts/game_data/contracts/skill_input_blackboard_native.json)
names the destination as `CenterBlackboard.skillInputData`. The supplied closed
MethodInfo requests `StateMachine<CenterState, CenterBlackboard>.get_stateBlackboard`,
but its compiled closed getter identity is not established. The field binding
therefore requires each returned object to actually be a CenterBlackboard.
CanCast false skips both getters and all writes. True obtains a first blackboard
and requests Dispose on its input, independently obtains a second blackboard,
calls CopyFrom on the supplied view, then checks that second destination for
null and writes the full input value. CopyFrom precedes the second null check;
there is no rollback claim. Normal completion returns the original predicate.
The two blackboard results and the source view locals remain explicit operands.

The [blackboard getter contract](../../scripts/game_data/contracts/skill_blackboard_getter_native.json)
connects the supplied closed MethodInfo to a static generic-context slot for the
second StateMachine type parameter, giving CenterBlackboard under static
substitution. This does not authenticate the initialized runtime context, the
compiled closed getter or a named closed-layout source field. The physical
getter reads its source once and resolves the type twice even when that source
is null. For a nonnull source it checks against the second resolved type first,
then against the first, rereading the source class for each check. On the ordinary
class-bit path, first-check failure returns null; second-check failure requests
an opaque cast-failure exit; both passing return the original source reference.
Special class fallbacks and the full relation helper remain outside the proof.
Normal resolver outcomes are explicit nonnull premises, not inferred from the
static substitution. Source-class flag reads occur only after a reached failure.

The [Center FSM construction contract](../../scripts/game_data/contracts/skill_center_fsm_native.json)
separately binds the CenterStateBase constructor's two supplied cast contexts to
CenterBlackboard. Its physical cast helper returns only the original source or
null on normal return; the classifier's type semantics are not recovered by that
identity proof. After the base constructor returns, the first cast result is
stored even if null. A second cast uses the original argument again but its
result is unused; its normal return precedes the blackboard barrier request.
A null AI component skips both later field writes, preserving old values;
otherwise the component is stored before its entity is read and stored, including
a null entity value. That entity read belongs to the inherited BaseComponent
`<entity>k__BackingField`, not a newly declared CharacterAIComponent `m_entity`.
These rules preserve reached effects and normal Win64 saved
carriers, without inventing helper side effects.

The machine construction fragments provide the same saved blackboard argument
to the Skill state construction and request AddState for the same constructed
token, under the stated saved-carrier continuity premise. The allocation context
requests CenterSkillState; neither allocator result type nor collection insertion
effects follow from that request alone. Nominal OnEnter vtable membership and a
located fixed-tick virtual call do not close the generic dispatcher, actual
state selection or runtime OnEnter occurrence. A complete writer census and
object lifetime proof are still required to carry the constructor alias into
the later input writer and state reader. CenterStateBase's blackboard field is
not init-only in metadata; absence of a named setter is not an immutability proof
and cannot replace that writer census.

The [constructor carrier-flow contract](../../scripts/game_data/contracts/skill_center_construction_flow_native.json)
now closes the intermediate machine-entry-to-Skill-block register preservation
premise under normal Win64 helper returns. Its finite instruction/control-flow
check covers the metadata-initialization alternative, entity setup cold block
and earlier state construction branches. No reached instruction overwrites any
alias of the saved machine/blackboard registers or the stack base; every selected
edge reaches an authenticated instruction, the Skill block or the opaque null
exit. This proves argument continuity to that block, not allocator results,
collection registration, helper heap effects or object lifetime.

The [runtime generic-context contract](../../scripts/game_data/contracts/skill_blackboard_context_native.json)
separates the canonical compiled getter from its supplied closed MethodInfo.
Reference normalization uses the Object default and the eligible Int32-enum
branch uses Int32Enum. The selected metadata-parameter fixup changes an index
into a parameter-record pointer; VAR substitution then reads its ordinal from
the class instantiation. The local kind-two RGCTX path inflates the type,
requests its class and stores the result into a runtime slot. These are
conditional native relations, not an observation that a particular live class
was initialized or that either recorded getter returned that class.
The selected pointer selector compares the original three-part key before
normalizing class and method instantiations for another lookup. Existing
interning-hit equality compares argument count and the selected type relations;
pointer-record decoding then projects the registered method/invoker/adjustor
indices. Probe helpers, new interning insertion, locks, attribute-mismatch copies
and complete class initialization remain outside that conditional path.

The [shared FSM dispatch contract](../../scripts/game_data/contracts/skill_center_dispatch_native.json)
binds canonical compiled entries and checks their selected instruction paths.
GetState checks ContainsKey and rereads the dictionary before get_Item with the
original state ID. The selector returns the first yielded transition whose
condition is true; absent condition checker means true. Delegate fallback
forwards its stored target and MethodInfo only after the inline-target misses.
List iteration is not evidence of a priority order or of an actual _ToSkill
closure. Dictionary, iterator and callback results retain their own premises.
Enumerator initialization copies the list and version into its local carrier.
MoveNext checks version before its unsigned index comparison; successful yield
sets current and increments index. Its slow path can prepare the class and then
rechecks list/version independently, so the first mismatch alone is not the
final exception decision. Normal end sets index to size plus one and current
to null. AddState copies two physical context references before the dictionary
Add tail request, captures the dictionary before state-context initialization
and reads the state ID afterwards. These anonymous physical slots do not
establish a closed nominal field's live contents or successful insertion.

Tick checks running on entry, optionally ticks the blackboard, then requests
selection. A first selected transition bypasses the later running recheck.
Only after a failed first selection does it update the current state, reread
the state, select again and recheck running. SwitchState and Transit request
exit before writing current state, then use fresh reads for entry. Exit and
entry receivers, the stored destination and the entry destination may differ
after callbacks or barriers; no final current state is inferred after OnEnter.
Nominal slot membership and a proved fallback request still do not establish
the live virtual target, actual OnEnter occurrence or cross-frame delivery.

The [Center lifecycle contract](../../scripts/game_data/contracts/skill_center_lifecycle_native.json)
distinguishes RefreshData from construction: RefreshData writes the AI reference
and requests its barrier before checking null. Null AI takes the opaque failure
path with the earlier write retained and no entity write; nonnull AI supplies
the inherited entity field, including a null value. The selected barrier's
complete leaf preserves the volatile argument carriers used here. Stop/Clear
dispose then zero the input at the same saved blackboard receiver; this is not
a post-callback lookup. The bounded writer inventory cannot exclude writes
through aliases, replacements or other helpers, and supplies no object lifetime.

The [inline refresh contract](../../scripts/game_data/contracts/skill_center_inline_refresh_native.json)
identifies another writer: CenterStateMachine.RefreshData takes an Entity,
reads its named character-AI component field and stores machine AI/entity
references. The complete selected normal entry and loop schedule is verified:
the machine replacement returns before original writes; collection helper and
iterator results remain explicit premises. Each yielded item reloads machine AI
before two separate type predicates. The second predicate can null the state
passed to the inline replacement; the original path cannot write a null state.
Original refresh writes state AI before checking it, then reads that AI's
inherited entity field once, including a null entity value. The state-refresh
replacement test is inlined too; this path does not call the Base.RefreshData
entry. No entry event at that hook therefore excludes neither refresh nor a
field write. Actual replacement selection, helper effects, collection contents,
and exception/unwind execution remain premises. Helper calls can change heap
fields despite preserving nonvolatile carriers; successive machine-AI reads
must not be collapsed. The first bitmap barrier preserves the carriers needed
by the later entity write; the final bitmap sequence may consume them. Marking
is flag-dependent and is not an unconditional observed barrier count.

The dedicated Center capture now supplies observed getter results and state
blackboard endpoints. `battle_center_observations` verifies the two native
getter call sites within recorded ToSkill pairs, reports each returned address
independently and retains sampled equality with OnEnter/DoCast blackboards.
Actual OnEnter encloses DoCast and a subset of BeforeCast calls; other BeforeCast
events remain separate. The OnEnter return site matches the shared enum virtual
fallback, while DoCast's return site is its original OnEnter call. BeforeCast's
caller belongs to TryCastSkill's inline initialization route, not Skill.DoCast.
These observations prove synchronous enclosure and sampled endpoint equality,
not a full upstream Tick/transition identity or an unobserved TryCast Boolean.
Adjacency of ToSkill return and OnEnter entry is reported as adjacency only.
The dispatch gate now derives the CheckCondition delegate-fallback call return
from its validated instruction span. The Center projection requires this audit
to match the capture's native inputs and classifies every ToSkill caller,
including false polling results. The admitted recording matches this direct
callsite throughout. This identifies the actual caller branch, not the checker
object, transition identity, selected transition, or a rejected user input.
Unknown callsites remain unclassified instead of inheriting the observed route.
The paired argument-read mask also admits the second ToSkill GP argument at
those exact fallback callsites. It is the forwarded MethodInfo pointer value,
separate from the later shared blackboard getter's context argument. The
admitted session repeats one nonnull pointer value across these calls, but
records no pointee bytes. The projector reports observed arguments and distinct
pointer values without equating pointer repetition with contents or lifetime;
an unread slot or unknown caller supplies no MethodInfo observation.

The [transition construction contract](../../scripts/game_data/contracts/skill_center_transition_construction_native.json)
separately proves selected constructor request slices. They load the on-disk
MethodDef usage for ToSkill, supply the same saved machine as target to a physical
initializer call, and pass the same saved delegate token with a closed Center
AddTransition context. Reaching these slices with the declared entry carriers
and normal ABI helper returns remains conditional. The requests include a
Skill-to-Skill transition; an entry callback therefore must not automatically
be interpreted as a new input. Neither initialized MethodInfo/delegate contents,
physical callee compiled generic identity, collection mutation nor the live
selected transition is established by these request slices.

The [delegate initializer contract](../../scripts/game_data/contracts/skill_center_delegate_native.json)
now authenticates the canonical enum ConditionChecker constructor, its full
normal main/cold control flow, and the physical slots inherited from
System.Delegate. Its resolver uses mask `0x02`; the later initializer dispatch
uses mask `0x10`. Resolver and bitmap-barrier instructions prove preservation of
the volatile carriers used by this caller; Win64 ABI alone would not prove it.
The initializer first stores the resolved method pointer, MethodInfo and target,
then requests the target barrier. Later flag and target/pointer reads remain
independent. Depending on those reads it either uses the reread target/pointer
or a fixed thunk with the delegate itself as dispatch target. The null-target
failure retains earlier stores. Final invoke/MethodInfo/dispatch-target slots
match the slots consumed by CheckCondition's fallback. This closes a conditional
write/read layout join, not the initialized runtime MethodInfo identity, actual
ToSkill binding, or persistence of a particular delegate instance.

The [plain MethodInfo fragment contract](../../scripts/game_data/contracts/skill_center_method_info_native.json)
separately validates descriptor population sources. A nonnull secondary code
pointer is retained; a null value is filled from a fresh base-code read. Saved
metadata fields provide flags and the low parameter-count byte under the stated
carrier/stack-local premises. The selected flag fragment clears `0x02`, uses a
leaf generic-container lookup that preserves its saved byte, optionally writes
that saved byte OR `0x01`, and finally applies AND `0xf7` to a fresh byte read.
The last read is not replaced with a previously written value. These are local
fragments, not proof that the observed MethodInfo pointer underwent this whole
population path or that its fields remained unchanged. Live descriptor identity
remains unresolved;
the plain descriptor layout does not establish the delegate resolver's alternate
code slot contents.

The [usage publication contract](../../scripts/game_data/contracts/skill_center_usage_publication_native.json)
closes the separate constructor usage-cell request through tag3 resolution to
the previously proved definition cache. The updater reads via atomic fetch-add
zero, returns an even word unchanged, and sends the low encoded word to the
selected resolver for tag3. A null computed result causes no publication;
a nonnull result is atomically exchanged into the cell, discarding the old word,
and that computed result is returned. There is no compare/exchange winner check.
The constructor's ready byte skips initialization when nonzero; otherwise its
ordered updater calls are followed by ready=1 without checking individual return
values. Ready does not prove that every cell is populated. This closes conditional
static publication semantics, not the observed descriptor's allocation history,
concurrent final value or lifetime.

The [default comparer contract](../../scripts/game_data/contracts/skill_center_default_comparer_native.json)
extends the null-comparer request to the default getter and the selected first
factory branch. The getter fences after reading the cached slot. On a miss it
saves the factory result, fences, independently resolves static bases for the
write and barrier, and returns the saved result without rereading the cache.
The first comparable factory branch requests the GenericComparer definition and
runtime element type, followed by an explicit cast result. GenericComparer
returns local null ordering or the full signed interface result. The transition
metadata's comparable interface and CompareTo slot agree with the selected
conditional fallback carrier. Array sorting still constructs a comparison
delegate through a resolved interface target; its actual target/initialization,
runtime comparer identity, other factory branches, sorting effects and tie
stability are not established by this contract.

The Center recording does not contain selector/executor pairs or descriptor
pointee bytes, so those live joins require a further targeted observation.
The [delivery recipe](../../scripts/game_data/contracts/battle_center_delivery_capture.json)
and [ABI reader](../../scripts/game_data/battle_center_delivery_capture_abi.py)
admit only the selected canonical Tick/selector/executor/condition signatures,
authenticated direct caller sites and bounded native read spans. The generic
root is not itself proof of a closed Center machine. The
[delivery projector](../../scripts/game_data/battle_center_delivery_observations.py)
retains same-Tick selector matches and nested state/cast endpoints, rechecks
normal stack enclosure, preserves ambiguous matches, and leaves cross-frame
identity, atomicity and lifetime unresolved. Preparation is not an observation.

The same delivery recipe also admits the reviewed input/cache/admission,
Skill/Ability/Action lifecycle, damage call and ordinary modifier/HP hooks in one
selection. Duplicate physical observers are not installed. The high-volume
upstream command observer is excluded while downstream OnExecute is retained.
Bounded EntityTimeDilationInst Tick/Stop and Skill interrupt/dash observations use
ordinary paired ABI and metadata-resolved fields: explicit Single delta, elapsed
and duration, timer/curve identity, stored flags and authored frames. Scoped
predicate absence is not false. No world-position, root-motion or contact layout
is inferred, and no suspended factor context observer is re-enabled. These
declarations prepare observations; they do not establish dilation owner, curve
output, continuous timer delivery or complete control recovery. The delivery
projector preserves nested modifier calls separately, so repeated HP endpoints
are not summed, and retains lifecycle and timing samples without promoting
pointer equality to asynchronous ownership.

The combined delivery recording supplies healthy paired Tick observations:
each Transit receiver has a unique earlier matching Select return in its Tick,
and current-slot endpoints match stored from/to. Successful Center casts instead
occur in a command scope after Condition/ToSkill and two getters, followed by
OnEnter/DoCast/BeforeCast; corresponding Select/Transit invocations are unobserved.
This is not proof of a bypass. `paired-ancestor` requires an active recorded
ancestor, whereas a caller filter names a physical return site; that physical
caller's invocation can fail its own recording filter. Readers must preserve
the actual parent and leave the missing invocation unobserved. The delivery
projector now handles both command-local and Tick-local observations.

The selected original Command.OnExecute path reaches the canonical state-machine
refresh helper, which makes out-of-line calls to the same selector and Transit
executor used by Tick. The retained activation accepts their Tick return sites
but excludes the refresh return sites. Command-local Condition caller addresses
match the selector's callsite even though the selector's own invocation is
filtered. This explains the missing parent observations by caller filtering,
not inlining or a demonstrated state-machine bypass. The selection helper here
is distinct from the state RefreshData field-refresh path. Selected native bytes,
relative call targets and retained activation were checked together; original
path reachability and runtime execution remain separate claims. No omitted
selector result, Transit receiver or intermediate current-state write can be
reconstructed from these static calls.

ToSkill descriptor code/flag bytes are sampled and code slots match its selected
native entry; successful callback descriptor/forwarded-pointer values agree.
Initialization history, closed generic context and uninterrupted lifetime remain
unproved. Transition endpoint equality also cannot supply the missing state IDs
and callback-surrounding rereads needed by the full executor model.

Observed non-global dilation elapsed endpoints agree with Single addition.
Native-authenticated authored normal-attack thresholds agree with captured false
interrupt outcomes. Skills without an admitted authored asset match can be
checked separately from directly captured exclusiveFrame, timer and mark fields,
provided their named field paths and selected native frame conversion are
validated. That comparison includes true getter outcomes; it neither establishes
external SkillData asset ownership nor shows that a player input was accepted.
Keep authored-asset and captured-receiver operands distinguishable. Adjacent
observed dilation Tick elapsed endpoints agree, but this does not prove omitted
intervals, the delta provider or a continuous owner clock. Stop handle clearing
is separate from evaluated curve output, effective scale and control recovery.
Nested outer/inner modifier endpoints agree and count once; non-HP targets are
not damage mismatches.

Missing damage Action binding candidates do not mean that all Ability evidence
is absent. The existing projection first requires a matching Action bind/rebind
receiver; the observed damage receivers have no such match in this recording.
Independent environment-pointer equality nevertheless yields historical Ability
Init-epoch candidates. Init sourceSkill matches the supplied Skill, BeforeCast
may update cast ID, and Ability pointer reuse is observed. Keep the Action bind
and Ability equality lanes separate. Observed reinitialization/release or UID/
source drift invalidates an epoch candidate; absence of such a recorded event
does not prove uninterrupted lifetime. Damage-time UID/source/cast snapshots
are still missing, so historical equality is not asynchronous ownership or a
unique cast occurrence.

The simulator subproject owns the reviewed command-scope extension, raw-prefix
capture preparation and conditional snapshot comparator. The research-kit
delivery recipe and its admission whitelist remain unchanged: the extended
manifest requires its child-specific reader, not a patched parent gate. An
unhooked refresh helper is the physical caller; a recorded Command ancestor is
not substituted for it. Existing bounded guarded reads can retain an environment
prefix and Ability receiver headers without assuming an IActionEnvironment is
an Ability. Unknown prefixes remain raw. Matching nonzero leading words permits
only conditional display at baseline-declared field offsets; managed-header ABI,
exact dynamic type, allocation extent, atomicity and lifetime are not proved by
that equality. New unreadable/truncated spans or incomplete/lost records reject
admission; observed null remains distinct from an unreadable value. Offline
parser tests and old-record transport compatibility do not observe these new
fields. The remaining command return and damage-time identity joins therefore
require a short targeted observation, not another full boss battle.

The maintained implementation is in the independent simulator's
`scripts/command_dispatch_analysis.py`, `scripts/observed_timing_regression.py`,
`scripts/action_binding_audit.py`, `scripts/command_dispatch_extension.py` and
`scripts/environment_snapshot_audit.py`; selected-build declarations stay in
that project's reviewed contracts. The interpretations above are retained here
so research-kit readers do not depend on local generated reports for the rules.

The child command-delivery projector now accepts the extended transport without
requiring every Transit to have a recorded Tick parent. It reconstructs complete
same-thread normal ancestry, scopes candidates to the nearest actual Tick or
Command invocation, and retains every earlier selector with explicit pointer
match/nonmatch/unknown results. Multiple matches remain ambiguous. Nested state
entry/cast endpoints and equality with sampled target/current-state pointers
remain separate observations. Empty or null samples cannot supply identity;
unique pointer equality cannot supply cross-frame lifetime or causal delivery.
Its command branch has bounded fixture coverage, not a new runtime observation.
Changed source bookends invalidate old consumer admission even when the raw
journal is unchanged; do not repair such a receipt by replacing its recorded
hashes. The research-kit's original Tick-scoped projector remains unchanged.

The later command-refresh extension recording has passed complete healthy
transport admission and actually contains the added refresh caller sites. In
this sample each Tick/Command Transit has a unique preceding matching selector
return within its actual invocation scope. Sampled current-slot entry/return
values equal the transition's from/to pointers. Some Command scopes now contain
the full nested Transit -> Center.OnEnter -> DoCast -> Ability.BeforeCast chain;
OnEnter receiver equality with sampled to-state and returned current-slot is
observed directly. Other transitions have BeforeCast without Center endpoints
or no captured cast endpoint. This closes the sampled synchronous dispatch join,
not callback-surrounding rereads, closed generic identity or cross-frame delivery.

The same recording provides readable damage-time raw prefixes with equal paired
entry/return bytes. Most leading words match observed Ability receiver prefixes;
under the explicit baseline-layout interpretation their UID/source/cast/origin
values also match actual BeforeCast endpoints. Unmatched prefixes remain raw.
Some outer DamageAction invocations match a unique preceding Center Command
BeforeCast candidate on the same thread. All equal-value matches are retained;
future or different-thread matches are not silently selected. Actual outer
ExecuteInternal ancestry groups nested ProcessDamage observations, preventing
double counting of callbacks as hits. Reused Ability UID with different cast
IDs demonstrates why UID alone is insufficient. Exact dynamic type, continuous
lifetime, atomicity and asynchronous ownership remain unproved by these values.

New timing regression samples include true interrupt getters for endminf's
third and fifth normal attacks with markCanInterrupt false, consistent with the
sampled timer exceeding the native-authenticated threshold. The ordinary skill
and a Rodin skill also supply positive captured-frame cases. The previous
normal-attack evidence was false-only; it no longer describes the whole retained
sample set. Original-path/Single assumptions, asset ownership, input acceptance,
clock owner, effective dilation and full control recovery retain their boundaries.
These rules are checked through the simulator's child-transport timing consumer,
without fabricating parent-profile admission or modifying its whitelist.

Further offline projection separates successful Refresh from readiness: the
selected constructed-request tail writes the nested AllowNext result, which
can be either Boolean value. Its stable paired request snapshots now exercise
the simulator's existing conditional tail model; false full-Refresh paths remain
excluded. Some Center commands clear the cache before DoCast, so current cache
presence cannot identify whether an earlier request was delivered. Same-command
name getters and both blackboard getter pointers match sampled endpoints, while
cache versus blackboard input bytes differ only at the target-handle cell.

The selected execution path obtains Skill through TryCastSkill's dictionary
lookup and carries that instance through CanCastToTarget and a physical readiness
helper to CheckCost. The helper has no matched managed method identity and must
not be renamed CanCast, IsAvailable or CheckCd. The first `_TryGetSkill`
output in `_ToSkill` is only a type guard, not this execution instance. Captured
DoCast-enclosed CheckCost and BeforeCast Skill pointers agree. Input.CopyFrom
obtains a separate target handle and copies target-view lists; pointer inequality
therefore does not establish target inequality. The retained recording lacks
those list elements. Actual content equality and continuity across that copy
remain open, and require scoped observations rather than another lookup hook.

Positive cancellation getters have distinct synchronous consequences: ordinary
skill checks in Attack commands can precede BeforeCast of a normal attack, while
normal-attack third/fifth checks precede Tick transitions without a captured cast
in those scopes. Keep checked current skill separate from incoming execution
skill. Negative AllowNext can still precede selector evaluation; selector entry
alone is not acceptance. This projection does not prove a cancellation writer,
complete control recovery or asynchronous ownership. Reusable child auditors
preserve normal ancestry, every candidate and source bookends; generated counts
remain in the child's reports.

Before the next carrier recording, review found that a whole-list read sized
for one inline wrapper can stop capture readiness when the list is larger;
offline partial admission cannot recover later unrecorded commands. The child
profile now selects bounded individual elements through a generic indexed
inline-container reader in EndfieldCapture. Absent indices read no payload and
do not fail the session; larger lists preserve explicit counts and missing
coverage. Header agreement within and across pages remains required, without
claiming atomicity. Capture-time source snapshots are inert provenance separate
from current reader bookends, so compatible reader fixes can reuse recordings.
These are transport improvements, not new runtime target or lifetime evidence.

The resulting target-copy recording now passes healthy complete child admission
and covers every observed target-list element. Source-entry versus destination-
return bytes agree for each normal paired copy, and source entry/return bytes
remain equal. Actual ancestry distinguishes input callbacks, cache construction
and ToSkill blackboard delivery. Same-Command cache-return target handles match
ToSkill copy sources; copy destinations match OnEnter/DoCast input snapshots.
Both blackboard getters also match cast state fields. These sampled joins close
the former content-observation gap without asserting atomicity, validity or
continuous lifetime. Clear is observed both before casts and after BeforeCast,
so its relative order must remain explicit. The child projection keeps all
candidates and rejects incomplete whole-list comparison; it does not turn
conditional CopyFrom requests into proved universal collection or pool effects.

The child's independent target-identity contract now authenticates wrapper
layout, Entity tag and closed ObjectPtr<AbilitySystem>.Lock usage. Shared Lock
null-tests the reference, rereads it for UID dispatch, compares returned UInt32
with a subsequent cached-UID read, and rereads the result reference on success.
The wrapper's original Entity branch instead copies the token to a local value
before those helper reads and final conditional selection. Preserve these
separate carriers and reads; successful comparison alone proves no lifetime.
The UID dispatcher uses a runtime class discriminator. The nominal inherited
getter and a dispatcher branch reading the same backing-field offset do not
establish the actual class's selected route.

The admitted copied token's reference bits also match named modifier-receiver
and damage-effectSource records carrying Rodin's entity name and server ID,
plus CanCastById receiver records with Rodin skill names. This is an observed
named-argument association, stronger than surrounding scenario context, but
not a separately read enemy-config identity or continuous object lifetime.
The sampled Attributes UID belongs to a different carrier and cannot validate
the ObjectPtr cached UID. No live UID/Lock result was recorded for this target;
dynamic validity and actual skill-target consumption remain independent gaps.
The child conditional regression preserves the selected original Lock rule
without making these endpoint matches into an unconditional entity binding.
Additional child consumer windows connect CanCastToTarget distance/angle
requests to the input TargetHandleView's get_firstTarget accessor, including
the argument home slot and original accessor forwarding. The internal accessor
copies list elements and contains an Entity-tag copied-local validity branch.
This identifies actual target consumption separately from Skill-owner Lock,
but not complete traversal/order, which sampled element was chosen, runtime
UID selection, geometry-check results or actual input acceptance.

The child's subsequent complete-range target-selection proof establishes the
ordinary scan: snapshot signed Count once, independently load the storage
list, scan ascending indices with current unsigned size/array bounds, and
return the first selected resolution even when null. There is no retry after
an invalid accepted target. One wrapper copy supplies resolution, a second
supplies the Entity filter, and a third supplies the Slot filter when needed.
Only under stable-source premises is this simply the first stored Entity or
Slot. Bounds/storage failures are exceptional requests rather than ordinary
null exhaustion. Dynamic Count dispatch, producer order, Slot resolution and
the actual observed selection remain separate from this conditional rule.

The selected native class creator also supplies a conditional UID route:
it locates the metadata definition record from the supplied index and selected
table globals, then copies the record's extra-index word into the class
discriminator. AbilitySystem's selected record takes the proved signed branches
and guarded selector/target tables to a direct instance-UID field read. Do not
equate the definition row index, discriminator, or instance UID. Normal creation,
matching globals, helper/register preservation and an unchanged class word are
premises; cache selection, other class-word writers and the recorded receiver's
runtime class are still unbound. Existing Ability/environment prefix captures
do not contain the dereferenced class word or live UID of this selected target.
The simulator now preserves explicit Count/copy reads and signed/table dispatch
in conditional regression; no live UID is supplied by an unrelated Attributes
or Ability UID. New source declarations and reports remain owned by the child.

The child's current class-cache/global-binding proof reuses parent proof
algorithms with freshly authenticated declarations, rather than admitting old
contracts against a different native pair. The resolver's sentinel returns
null; cache hits perform a fresh return read. The selected locked cold miss
forwards the signed index to class creation, publishes its result, unlocks on
the depth-one path, then rereads the cache. Other lock paths retain separate
semantic boundaries. Metadata initialization publishes the loader result to
base before testing null. Failure leaves header/cache untouched; a nonnull
path probes the header before publishing it, then later uses a fresh section
size in the authenticated allocation arithmetic. Normal allocator-result
publication does not prove capacity or completed initialization.

Current loader/path control, metadata path literals and imported close/error
declarations are proved separately from actual mapping-child effects and live
IAT/global values. A filename literal or old nonnull header does not bind
runtime metadata to a selected disk file. The conditional chain now reaches
cache creation/publication while retaining that runtime identity gap.

Slot resolution is an Entity ObjectPtr list lookup followed by Entity's
abilityCom read and AbilitySystem ObjectPtr construction. Negative index,
initial null list and signed out-of-count return default; a subsequent null
list or unsigned internal bounds failure takes an exceptional path. Item/null
comparison uses separate validity results and then cached UIDs when those
booleans agree. A non-equal item is independently validated for Lock; failed
Lock is exceptional. Construction checks one UID, writes the saved ability
reference and requests its barrier, then caches a second independently read
UID, including zero. Neither the earlier validity nor first UID can stand in
for later reads. Actual manager/list/Entity identity and lifetime are not
observed by this native proof or its simulator regression.

The child's current metadata-mapping extension connects loader forwarding to
the actual mapping body and verifies its complete enclosing control. Create
status selects the view request; a nonzero view still passes through registry
calls, subtraction using fresh local-slot values, two payload stores and a
final return-slot read before release. Depth-specific release preserves that
saved return under normal ABI premises. Initial view and final returned base
must not be equated. The child's complete create/view extension now checks
owned instructions, branches, stores, frames and closed access/protection helper
programs. Live IAT, OS effects, output validity and mapped-file identity remain
separate gaps. Normal string/helper calls retain ABI and valid-storage premises.

Create checks file information and size before its name/API path. The API's
size low/high parts are separate reads; its protection table differs from the
VirtualAlloc helper. Nonnull create result samples last error once; already-
exists closes it and writes status before cleanup, other results leave status
untouched. Null create result with nonzero first error samples again, and the
second error determines status. First error zero returns zero without writing
status. This reinforces why create status and returned handle are distinct.

View uses signed division for offset alignment and separates size's predicate
read from its value read. A refreshed system granularity is published and used
from the same sample. Map failure optionally writes status and requests close;
later allocation failure returns zero without close/unmap. Query return values
are ignored, so query output storage must remain explicit sampled operands.
One first region-size sample feeds both allocation comparison and zero-length
fallback; successful allocation triggers a fresh query. Final size is reread
after the selected region sample, and success returns the original view rather
than the allocation result. No actual file identity follows from this control.

The Slot producer chain now includes manager/controller constructor stores,
Reset and OnCenterChanged forwarding, and list/helper bodies. Constructor
backing-array initialization alone does not establish zero count/version.
Clear resets count before its positive-old-count backing-clear request; fast
Add increments version and writes count before the second bounds check, then
stores full token bytes with the selected barrier order. Resize stays opaque.
Reset snapshots source Count, filters only the first literal-null read, then
rereads the entity for conversion and appends its returned token. A null second
read yields an authenticated zero token and is still appended.

Reset and OnCenterChanged request swapping the first qualifying main-character
entry with index zero; this is not removal. Reset stops even at index zero;
OnCenterChanged continues there. The latter separately null-checks and rereads
charCtrl, so stability cannot be inferred between those reads. Generic Swap
gets right then left and requests left/right writes in that order; actual
generic destinations and resulting list state remain unresolved. The newer
Swap contract checks each runtime class/interface lookup: exact pointer scan,
first match, fresh table reread for the signed offset, Int32 slot arithmetic,
vtable code/MethodInfo reads, resolver miss and distinguished setter branch.
List metadata joins the requested interface slots, but precise Entity generic
specifications lack direct registration candidates; canonical registration is
not proof of live generic sharing. Conditional candidate get/set bodies are
available. Setter copies the input before the array bounds check, writes all
token bytes with the barrier order, then increments a fresh list version only
after normal child return. Failure does not increment version. The intercepted
array-setter extension now authenticates its code discriminator, normal body,
type/boxing helpers and raw/reference writer bodies. It initializes and rechecks
context before an unsigned index/count check. The reference-array path freshly
reads boxing context, requests boxing/compatibility, then uses a separate bounds
check and reference store. Raw writing independently reads stride and copy
length, requests byte-copy then barrier, without a local bounds/equal-size check.
Neither path updates a List version. Opaque helper effects and actual runtime
selection remain separate obligations.

The generic-sharing extension freshly locates the current normalizer and its
actual method-pointer selector. Reference kinds collapse through the reference
class cell; generic value recursion rereads type data for composition after
normalizing nested arguments. The startup name-lookup/publication slice requests
System.Object, without proving lookup identity or execution. The selected
original-miss/normalized-hit path compares three exact pointers: method key,
reloaded class-instantiation result and saved method-instantiation result.
Matched slot data feeds pointer projection. Checked primary/invoker indices
and later actual indices are separate samples; adjustor has a sentinel branch,
not an invented bounds check. Primary/adjustor/flag stores precede the final
invoker sample and store. Static canonical registrations do not establish
initialized runtime table population, canonical interning or live vtable binding.

The subsequent offline residency/table/delivery extension proves the missing
source mechanisms conditionally. The actual interner's selected count-one hit
saves and returns the resident pointer across normal unlock. Its cold path
writes count without padding, independently rereads the argument-array pointer
for each copy, requests insertion through the allocated-record local, ignores
insertion outcome and preserves the saved allocation for normal return. The
composer also ignores insertion outcome and only initializes its first two
words. Equal type content therefore cannot alone prove unique pointer residency;
allocator initialization and actual table history remain independent premises.
Object-kind equality ignores data identity, and generic comparison with two
null instantiations does not compare definitions.

Registration seeding writes the same global method table read by the selector.
Each selected row supplies a MethodSpec key and a saved-row pointer to its index
triple. MethodSpec check/return reads are separate; the cold path independently
reloads class index, registration, store-cache base and return-cache base. The
selected same-thread key constructor preserves its three pointer words and
allocated result across insertion. First-empty bucket publication increments
occupied count before fresh input reads/stores; duplicate insertion preserves
the existing value. These are conditional production rules, not observations
that startup executed or a normalized key equals a canonical resident pointer.

MethodInfo construction samples selector blocks and independently rereads direct,
writes direct before primary, and may overwrite direct via fallback when primary
is absent. Alternate publication and vtable selection inspect different flag
bits and independent gate samples. Ordinary vtable publication checks direct
before flags; linked publication saves flags first and permits a carrier/helper
route when direct is absent. Both write MethodInfo before code. A successful
nonnull check does not constrain the later selected target reread to stay nonnull.
Live class/MethodInfo identity, actual getter/setter choice and initialization
history remain unresolved. These durable rules are also encoded in the child
simulator's reviewed generic-intern, generic-table and vtable-delivery contracts;
they do not change the older blackboard contract's narrower proof boundary.

The allocator extension distinguishes two conditional sufficient-capacity fast
paths. Raw interning allocation reserves an eight-byte-rounded UInt64 length,
checks arena capacity, advances the cursor and subtracts from a fresh remaining
sample; it returns the old cursor without initializing payload. Composer
allocation reserves the rounded low UInt64 count-times-size product, then
requests zero-fill for the unrounded length and returns that helper's result.
Zero-helper effects/identity, slow allocation paths and disjointness remain
unresolved. Equal-key insertion returns false without publishing a replacement
before opaque unlock, whereas success returns true; callers still ignore that
outcome. Actual canonical seed execution and unique pointer residency therefore
remain independent obligations rather than consequences of content equality.

The class-initialization extension joins actual ordinary/linked writers to their
setup owner and traces a reached initializer fragment through recursive class
preparation to that setup request. The saved resolver-result class is not assumed
to be the incoming initializing class. Setup checks flags before and after its
opaque acquisition fragment, and the generic-field check, resolver argument and
retained key are separate reads. Completion first requests a helper on one flag
byte's address, then directly updates a different byte after normal return; the
helper's store/synchronization effects remain unproved. A complete adapter returns
the pair-storage address after setup, not pair contents. These bounded carrier
and branch facts do not prove whole initializer reachability or live vtable state.

The subsequent initializer-control proof covers that initializer's complete owned
instruction partition, local control graph, static reachability and normal frame
restoration, including the previously located carrier and setup call. It does not
cover the setup owner's whole control flow or prove branch feasibility, helper
effects, recursive termination or runtime execution. Ready and pending bits are
separate early-true checks; the DWORD error handle is read only after both clear.
The ordinary path freshly marks pending and increments a byte counter. Selected
post-recursion inheritance copies one resolved-class flag bit while preserving
other bits from the fresh original-class sample. Early true is not a completion
observation, and those class receivers need not be identical.

Ordinary slow allocation now has a checked descriptor/list-publication route:
descriptor and payload allocation remain opaque, then cursor/base, remaining/
capacity and header are written before a new list node is spliced at a saved
anchor. The owner-count exceptional guard is equality-only and later increment
uses a fresh memory sample. The actual zero helper's short paths cover exactly
the requested byte range and return the original destination; this includes the
composer's record-sized request. Larger zero paths, indirect allocator semantics,
disjointness and post-helper persistence are separate from that bounded proof.

Static canonical provenance is now joined to startup metadata seeding. The
argument loop uses the registration alias, starts at zero and passes increasing
pointer-array slot addresses to insertion, with fresh registration/count reads
and ignored insertion outcomes. Insertion samples the slot after acquisition and
publishes the unchanged saved pointer on its selected first-empty route, using
the same interner table/hash/comparator. Complete static comparison finds unique
equivalent inner-object and outer argument vectors. Generic-class seeding also
receives the registered pointer array and conditionally publishes its unchanged
carrier to the actual composer table. The carrier pointer appears once in that
static array; this is not a generic-class content-key uniqueness result. Its
opaque slot predicates, full helper control flow, composer equality, collision/
resize behavior and preexisting dynamic residents remain unresolved. Static seed
source proof therefore does not establish runtime canonical pointer identity or
actual Entity getter/setter selection.

The composer lookup extension now proves its selected ordinary-slot hash and
comparison paths. Hashing mixes the definition's type hash with shifted class-
and method-instantiation pointers, while equality compares definition types,
class-instantiation counts and ordered argument contents. A fresh zero count
skips argument arrays. The selected equality does not read the method-instantiation
word, which is null in the authenticated canonical carrier. Separately allocated
content-equal class instantiations may hash differently; content equality alone
cannot close the runtime canonical-hit premise. A mismatch uses incrementing-step
triangular probing with modular arithmetic. A further cold-path proof shows equal
occupied/deleted counts bypass the key and hash, reread capacity then slots and
publish an end iterator. Iterator writes are current, table, end; equality returns
without a scan-flag read, and a false scan byte avoids slot reads. Selected scan
tails prove predicate-false stop and predicate-true cursor increment to end, with
the cursor reread for its update. Complete iterator and deleted-predicate grammars
now check all local edges, content-comparison loops and ordered reads. Their record
and definition read orders differ; both retain a fresh marker count for iteration.
Skip updates the cursor and then independently rereads it for comparison. Finite
sample-driven regression fails on missing operands rather than inventing a return.
Type-comparator effects, termination, actual table history and live getter/setter
selection remain unresolved.

The resident-table extension authenticates marker comparison, growth-candidate
and cleanup programs. Marker equality rereads the sentinel tag, and a reached
zero-tag route compares actual record counts/type contents; it is not simply a
deleted-bit check. Growth uses staged Single arithmetic and unsigned conversion
before a strict count/threshold comparison, with wrapping capacity doubling and
no universal termination proof. The simulator keeps the converted threshold an
explicit operand rather than replacing the native algorithm with integer division.
Cleanup can clear its marker without rebuilding. Its actual constructor, swap and
destructor now have bounded effect proofs: constructor copies/zeros in ordered
read/write pairs before checking a source flag, and its growth-only branch does
not establish migrated records. The other branch's actual copy/rebuild child and
its setup, slot hash, vacancy, deleted-skip and advance helpers now have complete
independent program checks. Copy publishes tag before rereading and writing the
source record pointer, then updates occupied count and iterator before advance;
normal return increments version even for empty input. Hash loop count and seed
come from separate count reads. Setup stores the allocator return, uses independent
fill start/end bases, writes each tag before reading its record and publishes
capacity/zero counters before recalculating thresholds. Allocation/reuse effects,
termination and preserved map invariants are still premises. Swap exchanges
semantic fields, but some marker-region padding comes from
uninitialized temporary stack bytes, so it is not a complete bytewise structure
swap. It then rereads capacities, recomputes thresholds through the native Single
stages and clears markers during those stores. Destructor conditionally rereads
the payload pointer for release and performs no field clear. Neither these effects
nor marker clearing establish release success, initialized sentinels/slots, resize
correctness or all-map invariants. The simulator keeps conditional operands and
bounded write fragments separate from complete container behavior.

The allocator/reuse extension proves zero normalization, unsigned size rejection,
two-gate retry control, explicit error/null paths and conditional pointer publication.
Nonzero-old-pointer reallocation with zero bytes requests release then returns null;
the reuse wrapper treats that null as a diagnostic/failure/trap path, not success.
The caller's modular size shift precedes allocator checks. On-disk Heap API imports
do not establish live IAT targets or successful heap effects. These storage bodies
do not initialize table sentinel fields, so initial markers remain an offline gap.

The vtable setup owner's complete control graph and normal frame are now proved
separately from the initializer, with joins to the prior writer fragments. Its
auxiliary and pair loops use wrapping UInt16 increments and fresh UInt16 count
reads at each latch. Static reachability and restored frames do not establish
stable counts, feasible execution, termination, child effects or actual class/
MethodInfo identity. Earlier entry/allocation counts cannot replace latch reads.

An authenticated offline coverage audit of the retained target-copy and
command-refresh recordings found no named manager/controller/Slot-list samples
or caller origins within the reviewed manager/Slot bodies. TargetHandle's
BattleTargetWrapper list cannot stand in for Slot's ObjectPtr<Entity> list;
anonymous raw spans and pointer equality do not establish their owners. This
bounded absence of coverage does not imply absence of runtime execution. No
manager/slot identity, caller order, exhaustive writer inventory, or captured
character slot number follows from these conditional native producer rules.

Static manager access is now joined through GameWorld's public static battle
field, not a GameWorld instance field. The consumer checks battle null before
saved IFix table/handler selection; nonnull table with null handler falls back
to m_slotController. Creation publishes the typed manager-lookup return, even
null, with independent static-storage reloads for the store and barrier.
Destruction requests public/static reflected fields, BaseWorldManager type
assignability and SetValue(null,null). The battle field is nominally eligible;
actual reflection results and clearance are unobserved. These source proofs do
not supply the missing runtime instance samples or continuous lifetime.

The typed ManagerCollection lookup now has an additional conditional carrier
proof: initial context check/initialization precedes array null/bounds checks;
fresh context is read before the element, and the saved element is retained
across type-context resolution into the cast. Null input returns zero and
successful assignability returns the original input. Failed assignability
continues further checks rather than implying null; secondary helper values
are predicates, not replacement manager references. All ordinary cast returns
preserve the original reference or null-input result under normal ABI returns.
Actual array contents, writer order, compatible runtime type and continuous
manager/Slot binding still need independent evidence.

The manager lifecycle extension proves conditional array production and request
order. Collection construction saves the freshly read sorted type-list count,
requests the context-selected array allocation and publishes its returned
reference. PreInit saves its destination array before type lookup, Activator
creation and cast; the cast result, including null, is written into that saved
array. The writer checks unsigned bounds, reads the barrier gate, writes the
reference, then conditionally marks the barrier; it adds no compatibility check.
Original World initialization requests PreInit, manager-created publication and
Init in that order, with independent collection reads. Release traverses in
reverse using signed Int32 termination and fresh array/element checks, then
requests Array.Clear with a length from one array read and a receiver from another.
Only the length-source array is null-checked by the caller. Allocation/lifecycle
child effects, replacement paths, successful clearing and continuous manager/Slot
identity remain conditional or unresolved. These findings are recorded in the
child's reviewed class-init, residency-premises and manager-lifecycle contracts;
no recording or parent contract is retroactively promoted by them.

The simulator's bounded reverse-release step now preserves decrement-before-test,
signed-negative exit, independent array/element reads and unsigned bounds checks
before the lifecycle child request. Initial length and successive equal pointer
samples do not establish a persistent manager array or Slot owner. Exceptional
paths, actual child effects and the separately reread Clear receiver remain
outside that step's normal-return premise.

The collection release child is now bound to the concrete BaseManager.Release
method. Selected normal paths authenticate patch-table/handler fallback and
original short-circuit byte checks. An active original path writes a third state
byte, requests the same numbered dispatch helper twice in order, then clears the
first two bytes after normal returns. This final word store does not cover the
third byte, whose post-child value is not known. A replacement skips that original
logic. The helper is now independently proved to truncate its selector to UInt16,
preserve the original receiver, read its class before a preparation call and
reread class afterward for code/MethodInfo pair reads. After excluding three inline
specialization code targets, the generic indirect call passes the original receiver
and the loaded MethodInfo. There are no preceding null/bounds guards. Physical pair
selection does not identify a nominal callback or prove that the class stayed the
same across preparation. Preparation now joins to the existing setup owner through
a carrier field read from the incoming class; carrier identity is not assumed.
The three inline branches have complete instruction/control inventories and
independently checked modeled byte paths: patch/state/dependency guards in the
first, non-vector flag writes in the second, and gate/state/class-init/tail-receiver
requests in the third. The tail check and call use independent pointer reads.
Vector/float outcomes, lazy binding, unknown callbacks, exception/log routes and
continuous manager/Slot identity remain unresolved. These source facts and
conditional models stay separate from the recordings' limited instance coverage.

The vector specialization is now identified through authenticated method/field
metadata as TMP text rendering. Its input is lossyScale Y, not a position. Native
control uses a sign-cleared Single difference and ordered-above comparison; NaN
does not take that branch if COMISS completes. The checked indexer returns an array
element address, whose first word gates the callback; it does not return a count.
The denominator is reread and the saved scale is written after the callback.
Numerical regression explicitly assumes RNE, DAZ=0, FTZ=0 and completed operations.
These facts must not be labeled battle-manager runtime behavior without the actual
code selection. The selected class-creation prefix also writes a self-pointer into
the setup-carrier field, conditionally explaining preparation's carrier read without
proving that the live manager class used that creator or kept the field unchanged.

Retained target-copy pages only observed Entity targets in this scope. Missing
named manager/controller/list and GetFirst return samples prevent recovering live
selection from copied wrappers alone; absence of Slot observations does not make
Slot a required branch for the single-character scenario. Future focused capture
must distinguish primary Entity selection from optional naturally reached Slot
lookup and preserve no-hit/partial states rather than demand a Slot sample.

The child simulator now prepares caller-scoped ordinary GetFirst/SlotGet paired
observations with typed bounded list pages and existing IFix selector snapshots.
The hidden SlotGet output buffer, controller receiver and low-word index have
separate ABI roles. Unused GP slots are not promoted to MethodInfo identities, and
entry output-buffer bytes are not constructed-token evidence. Offline parser,
relocation and bounded-reader checks validate the proposal, not runtime execution.
Endpoint tuples still do not prove a branch load between samples or cross-frame
lifetime; filtered outer hooks can leave usable but unassociated inner endpoints.

The admitted target-binding capture now distinguishes cast-distance GetFirst from
damage-time Slot lookup. The former returns the reference word in its single
sampled Entity wrapper. Same-scope CopyFrom endpoints pass the check handle into
a distinct ToSkill destination used by OnEnter/DoCast; raw handle equality alone
would miss that transfer. Conditional model comparison uses stored token bytes
to predict the separately observed return, retaining stable-copy, Count dispatch,
ordinary-path and ObjectPtr-validity premises. Stored cached UID is not live UID.
Slot endpoints instead have damage-execution ancestry and the physical caller
from GetFirst's Slot callsite; their missing outer hook cannot be replaced by a
nearby recorded GetFirst. Controller/list/Entity token, hidden output address and
returned Ability token are different observed roles. No named Ability/damage
scalar equality identifies that output with player or boss. IFix boundary tables
are null, but intervening selection, numeric UID dispatch, singleton binding,
Entity.abilityCom reads and uninterrupted lifetime remain unobserved.

The missing damage consumer GetFirst origin is recoverable offline from an owned
native instruction fragment, rather than a proximity or byte-search inference.
The follow-up proposal therefore widens only that caller and observes selected
validity sites and Slot's direct Ability UID construction calls. Scoped capture
currently means any active paired ancestor, not a named ancestor filter; excluding
the shared validity-to-UID caller is necessary to avoid unrelated baseline traffic.
A common validity helper receives both Entity and Ability tokens, so an unconditional
Entity.abilityCom projection there would not have a proved receiver type. Guarded
class/discriminator samples and actual Boolean/UID returns keep their separate
evidence boundaries, including the still-unobserved numeric Entity UID.

The follow-up live-identity capture records the previously missing same-invocation
GetFirst → Slot → validity/constructor-UID → final-validity → GetFirst-return chain.
The Slot item checks return true, its zero-token comparison returns false, and
both constructor UID calls use the same receiver. The second actual UID and saved
receiver match the separately observed output token; the later caller validity
token and returned reference also agree. Constructor values are actual dispatcher
returns, not inferred cached UIDs. They do not observe validity's internal UID
calls. This particular Slot-containing damage-execution scope has no recorded
ProcessDamage child, so target validity alone does not establish an applied hit.
Ancestry, cached words, actual return values and class-field samples retain
separate evidence tiers; internal reads, runtime type and lifetime remain gaps.
The constructor receiver matches later skill-admission receivers with Endminf's
normal-skill ID and damage effectSource arguments with a sampled Endminf entity
name. Those are separate recorded scopes, so this narrows character association
without proving constructor-time actor identity or continuous lifetime. The child
auditor retains their original argument slots, typed field paths and ancestry.

The child `target_slot_runtime_flow` further closes the instruction interval from
the Entity lock-local read through abilityCom loading, saved-register delivery to
both recorded constructor UID calls, token stores and output copy. It consumes
the existing reviewed Slot windows and checks every instruction and branch join,
rather than inferring register continuity from address order. Under explicit
ordinary execution, Win64 nonvolatile-register preservation and stable local-read
premises, the actual UID receiver conditionally identifies that one abilityCom
load result. The Entity identity additionally requires the later token-local
read to match its sampled lock input. No direct field observation, atomic snapshot
or lifetime claim follows. Independent token output matches the prediction from
the observed constructor inputs, so this narrow binding does not require another
recording merely to repeat the same evidence.

For saved capture intake, historical source provenance must be distinguished from
current native validation. The battle subproject now has a separate reproof reader
that preserves changed transitive hashes as unavailable historical bytes, keeps
critical capture/runtime/contract and transport gates, and independently validates
the current selected native pair and dependency graph before and after decoding.
It does not modify the saved manifest, run retained source text, or reuse a stale
native result. Source drift during a run still rejects publication.
Native-only dependency changes after decoding can be handled by a derivative
receipt that reauthenticates the original inventory, journal, decoded bytes and
unchanged transport readers, then reruns the current native proof. Earlier
receipts remain immutable; changing transport code still requires new admission.

The [transition storage contract](../../scripts/game_data/contracts/skill_center_transition_storage_native.json)
composes the constructor request proof with canonical machine/state AddTransition
registrations and selected normal schedules. Each Contains/get_Item request
rereads the state dictionary. Both get_Item results are obtained before testing
the from result for null; a null to result can still be forwarded. The state
helper writes from, to, priority and checker into the allocated object, with
reference barriers in their observed order, then rereads the source state's
transition list and requests List.Add. After that helper returns the machine
rereads its transition map and requests set_Item using the original target ID.
Written from/to/checker slots match the executor and condition-reader slots.
The helpers' normal outcomes, runtime RGCTX, allocated nominal type, collection
mutation, lifetime and actual selected transition remain explicit boundaries.

The [transition list contract](../../scripts/game_data/contracts/skill_center_transition_list_native.json)
extends the selected List.Add request to its fast-capacity mutation: version is
incremented before the array null guard, size is written before a second bounds
check, and the original item is stored at the old index before optional bitmap
marking. Version/size increments wrap in the stored width; capacity comparison
uses unsigned low bits. The resize branch remains an opaque AddWithResize
request. Written list/array/version slots match the selector's iterator reads;
this does not establish that a particular runtime list instance persisted.
Under coherent reads, a mutation can invalidate an old enumerator version even
when the subsequent operation fails; portable regressions keep the version
operands explicit instead of inventing a recorded collection join.

Start requests the sort-all chain before writing running and making entry
dispatch requests. State sorting forwards its list to List.Sort; the latter
requests the range from zero through the read count with a null comparer.
The transition CompareTo body reads other priority first, reads this priority,
and rereads this priority on the non-less branch. With coherent values it has
ascending signed-priority comparison semantics. Actual default-comparer
selection, sort effects and tie stability remain unproved. The BB entry leg is
a physical slot request, not proof of a particular virtual callback execution.

The recorded constructor returns have empty AI/entity fields; later state-entry
samples at the same address have populated fields despite no base RefreshData
entry. The inline writer is a proven possible route, not attribution of the
actual intervening write or proof that the address's lifetime was continuous.
Raw getter MethodInfo bits lack pointee/context contents and still cannot
establish the actual closed runtime type. Stop/Clear endpoints include a
nonzero-to-zero whole-input sample; reset byte regression compares the observed
return bytes, without substituting expected zeros when a recording disagrees.

The [Center blackboard consumer contract](../../scripts/game_data/contracts/skill_blackboard_consumer_native.json)
identifies a separate direct route: CenterSkillState reads that named input field,
constructs a view and calls AbilitySystem.TryCastSkill. It is not the independent
`_TickToCastSkill` → CastComboSkill → pending route. Matching a named field closes
the static producer/consumer declaration, not the live writer/reader object join.
After a normal TryCast return the caller does not branch on its Boolean. It
reloads the current blackboard, clears only `skillInputData.skillEndCallback`,
then reloads entity and AbilitySystem before ClearSkillRequest. A later null
carrier stops after earlier effects; it does not undo callback clearing.
ClearSkillRequest's original tail forwarding explains the retained Combo.Clear
caller's outer return address, without inferring cast success from the clear.

`battle_input_center_links` reuses admitted pair/enclosure evidence and the
native call/tail-wrapper bindings to retain all same-command ordered admission,
BeforeCast and selected Clear candidates. It does not manufacture hidden
_ToSkill/_DoCastSkill invocations, a TryCast Boolean or a shared blackboard from
a single candidate. Unmatched and multiple candidates remain explicit.
The retained input profile has no Center state/FSM hook, blackboard getter result
or state-to-blackboard relation field. Its pending hooks concern the separate
CharacterCastSkillBehavior path, and a Combo request snapshot is not a Center
blackboard input snapshot. Static caller classification adds no missing runtime
endpoints to that recording; these candidates cannot establish same-instance
continuity or cross-frame scheduling.

The CenterSkillState keep flag is checked after base OnEnter. A true flag is
reset and skips the local cast call; base effects are not excluded. Cleanup
names must retain their owners: CenterBlackboard Stop/Clear dispose and zero its
input, while its original ClearAll body does nothing. The separately reviewed
pending SkillData.ClearAll requests whole-input zeroing. None of those paths
is interchangeable with post-cast callback-only cleanup.

The exported configuration can now be followed without a type-name heuristic.
`skill_ai_mode_sources` selects an explicit CharacterTemplateData root RID,
checks its componentList ownership of CharacterAIComponentData, resolves aiCfg
by external source/PPtr identity, then follows the configuration's brainConfig.
The selected mode maps to a blackboard mode tag; the mode's graph and behavior
tags resolve to exact managed-reference payloads in the explicitly selected
root blackboard. Physical AssetMap tuples and source/freshness bookends guard
the involved documents. The current endminf template follows this stored chain
to the melee AI configuration and cast graph, with distinct cast/plunging
behavior payloads. Empty config templates are not alternate evidence for this
populated selection. The configured aiBBPath still needs its resource-loading
join; an explicit blackboard argument does not prove that live loading chose it.
The behavior data's authored duration is a stored field, not a recovered player
lock duration, skill duration or control-restoration boundary.

The separate `skill_ai_mode_sources_native` contract binds the original brain
InitData parameter to aiComp.data.aiCfg and its brain configuration, then checks
the physical mode-pair/cache-selection transfer into CharacterAIMode.InitData
and the following m_modeData Add request. Resource-loader and dictionary
MethodInfo arguments are checked at their actual receiving call sites. A typed
supplied context does not authenticate the compiled closed helper or its
effects. Resource path construction/resolution, actual loaded blackboard and
the active entity configuration therefore remain unadmitted joins.

The [closed mode layout](../../scripts/game_data/contracts/skill_ai_mode_layout_native.json)
now binds the concrete CharacterAIMode carrier through its generic AIMode and
AIClassPool ancestors. Complete declarations, the concrete suffix, native
constructor stores and the only remaining aligned reference slot identify the
inherited graph field without using open-generic placeholder offsets. The
dispatch validator consumes this proof on the same opened native image, with
matching selected input pins and separate contract bookends. Its brain-forward
graph receiver therefore has named closed-field ownership, rather than an
anonymous physical-slot premise. This does not prove live initialization.

A bounded factory fragment separately maps an explicit graph-enum result to
the supplied GetClassFromPool<CharacterCastSkillGraph> MethodInfo and follows
the normal nonnull physical result into that graph slot. The supplied context
does not identify the compiled closed pool implementation or the returned
object's dynamic type. A bounded CFG over the complete framed InitData body now
checks the indexed jump tables and propagates the image-base register from the
actual entry. All paths reaching the factory table load carry the image base,
under normal Win64 nonvolatile-register preservation. Guarded table access may
not be entered midway, and unsupported control transfers or register writes
fail closed. The virtual getter result and whole InitData receiver continuity
remain separate premises. Only the layout proof is consumed by graph dispatch; no actual graph
or behavior selection is promoted by this combination.

Original cast-graph routing tests the returned pending record first. Absence
requests ResetAIMode with no force/guard. Presence chooses the plunging static
tag only for castType one, otherwise the cast static tag; Int32 tag inequality
controls whether a switch is requested. Comparison, requested value and
post-call field write are distinct reads. The brain only forwards a present
mode/inherited graph receiver, with force=true. The selected graph's entry path
clears the current list before lookup, issues ordered Enter requests only when
the nullable tag is present and lookup returns true, and writes the nullable
tag even when lookup fails. Enter requests do not prove the concrete OnEnter
virtual callback ran.

Completion checks the post-entry current list independently. Null/empty lists
satisfy all-finished; the first false flag skips invocation and clearing. The
callback reference is reread after the checks: a null reread skips invocation
but still clears its field; a normal invocation also precedes the clear.
Reentrant writes can therefore be cleared rather than preserved. The simulator
keeps these observations separate and requires coherent collection accesses;
it does not infer live graph type, concrete behavior selection, callback effects
or scheduler ordering from a successful local request.

The simulator maintains finite Single clock and ordered-interruption reference
models with whole-result conditional regression. Getter boundaries reuse the
admitted authored projections; synthetic deltas, curve samples, markers and
membership results remain labelled assumptions. The regression neither runs a
native gate nor upgrades these operands to observations or enables the real
Gym battle environment. The simulator's `input_rules` additionally models the
ordered cast gates, Attack mapping request, cache selection/replacement,
epsilon expiry, stored visibility and the distinct repeated admission checks.
Input/target tokens stand for explicitly supplied external results; copy/dispose
requests do not simulate unproved reference-counting effects. Pending commit
cases name the post-call record explicitly and keep actual-new-skill-start
unproved even when the TryCastSkill result is true.

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

LevelScript EntityPtr/SpawnerPtr getters and producer output aliases are owned
by [Story carriers](story_carriers.md); their open item is the slot-addressed
(`useSlotId` true) filter, which needs a runtime script-slot binding.

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

The [damage session reader](../../scripts/game_data/damage_runtime_inspect.py)
reuses the maintained transport/pair inspector and requires the reviewed kernel
hook and return-ABI selection. It groups observations only under their explicit
same-thread DamageAction invocation ancestors, retains unrelated observations
separately, and refuses incomplete calls, failed transport or changed retained
inputs. Local-file inventories establish consistency of the retained files,
not producer authenticity or a fresh native proof. Formula floating returns
retain raw bits beside decoded values; modifier target identity fields remain
observations at their own entry/return boundaries. A DamageAction enclosure is
not automatically one normal attack, one hit or one target. Operator-declared
solo Endminf/Rodin context cannot supply missing runtime actor/skill ownership,
input acceptance, animation recovery or asynchronous descendants. No live
observation is added by preparing the capture preset or running fixture tests.

A retained full Endminf/Rodin combat session now supplies healthy, accounted
paired observations. Its stable Rodin HP target reaches stored client HP zero;
the admitted outer HP pairs agree exactly with returned `realDelta`. The inner
`_DoApplyModifier` observations are nested views of the outer `ApplyModifier`
calls, not additional damage to sum. Non-HP modifiers compare different
quantities, and identity changes revoke the HP residual comparison.
[The numerical reader](../../scripts/game_data/damage_runtime_numerics.py)
keeps those cases separate and streams the source-bound attribute sidecar.
Attribute UID/pointer equality supplies candidate joins to observed targets,
not proof of uninterrupted object lifetime. User-reported weekly selection,
loadout and victory remain separate from the captured target fields and HP.

The standalone `BattleFormula.CalculateDamage` observer was not reached in
that session despite complete Pack and DEF-helper observations. Selected-build
return-site resolution instead reaches `DamageAction._ProcessDamage` as the
immediate Pack caller. Its native body contains subsequent Dice, DEF/type-
resistance calls and Double arithmetic on the Pack result. Thus absence of the
standalone entry does not imply absence of damage calculation. This bounded
caller/body evidence does not establish compiler-inlining provenance, all
executed branches, critical flags or complete numerical formula parity; old
Pack arithmetic contracts still require their own selected-build gate.
The session also observes separate targets named for Rodin wall AbilityEntities;
those identities must not be merged into the boss's HP series or treated as
proof of collider geometry. Per-session counts, numerical snapshots and native
addresses remain in generated analysis reports.

The [ProcessDamage arithmetic contract](../../scripts/game_data/contracts/damage_process_formula_native.json)
now records a conditional, finite-number fragment of that actual caller. Its
[validator](../../scripts/game_data/damage_process_formula_native.py) checks the
selected native pair, opened bytes, named entries, reviewed windows and external
literals, then rechecks the files. Missing inputs, drift or failed checks withhold
the expression. This authenticates a reviewed disassembly interpretation; it
does not prove full control-flow dominance, typed array ownership, live provider
selection or an entire damage result. The earlier Pack contract remains separate.

Within the stated branch, ordered Double operations apply the attack scalar,
Pack return, critical bonus, DEF factor, damage reduction, nonnegative type
factor, defenderPoiseFactor and two mask-selected scalars. DEF uses
the observed Single coefficient widened to Double; replacing it with its short
decimal display changes the calculation. Type resistance and damage-taken scalar
are separate operands. Exact indices, predicates and byte provenance belong to
the contract. The conditional expression ends before a later optional Actor
Single scale, block and settlement processing, so it is not final HP loss.

The earlier calibration capture does not observe the actual Dice Boolean, defenderPoiseFactor
replacement selection/result or subsequent Actor-scale branch/value. A null callback can
select the identity factor in the reviewed code, but an unobserved callback is
not evidence of null. Do not back-solve those missing values from settled HP,
choose critical outcomes by residual fit or label the fragment a full prediction.
The next numerical capture needs proved observations of those selections plus
an explicit Pack-to-target/modifier association; skill-instance ownership remains
a separate requirement before a sample can represent a player action.

The simulator-owned full-fight capture now supplies actual Dice and
health/UsesRaw returns, plus the factor's report-entry register value in the
same Process/local-Pack scope. In its eligible recorded calls the factor is
directly observed as one; early-return calls with no eligible context remain
unset. This does not select every possible getter replacement branch or make
one a universal default. Same pointer-plus-UID attribute observations and
target/Modifier scope binding let the existing ordered damage arithmetic be
checked without back-solving missing operands from HP. The full-fight lane
still supplies PackFinal as an observed intermediate. A continuous Boss HP
domain initializes once, advances only from computed damage and compares
later HP/realDelta independently, stopping at the death/clamp boundary of its
interior-only rule. Observed typed DamageImmune cancellations are classified
outside the no-immunity domain, not promoted to an immunity activation model.
The owning implementation and maintained boundary are in the separate
[simulator recovery contract](../../tools/endfield_battle_sim/docs/recovery.md#full-fight-numeric-and-cast-regression).

Native physical argument storage and native value width must stay distinct.
A Win64 Boolean uses its low byte; a saved eight-byte carrier may have dirty
upper bits even when that Boolean is false. Preserve the full raw carrier for
audit and mask only when interpreting the declared native value. Whole-carrier
truth incorrectly classifies some normal damage as extra-target damage. Fixing
the analysis does not invalidate or require replacing the original capture.

The full-call lane also connects ordinary attacks to actual Skill Tick
ancestry and BeforeCast epochs. The recorded actionEnvironment receiver and
its UID/source-Skill/castId byte span match the typed Ability observation for
ordinary attack1 through attack5; guarded raw sampling is non-atomic and is
not an unrestricted allocation-lifetime proof. Child normal-skill environments
can differ and retain that gap. DamageAction dispatches are distinct from
Process target calls, so a multi-dispatch attack cannot use a single-hit model.
Logical TimeManager frameCount has an ordinary initialization and per-Tick
increment of its own; do not substitute it for Unity frameCount at Skill's
same-cast-start-frame gate merely because observed counts correlate.

The simulator's authored multi-hit component now checks the current five normal
attack plans against the recorded Skill Tick/target/settlement scopes. Source
start times drive event dispatch; recorded dispatch IDs and timer/HP endpoints
remain independent comparisons. Multiple Find/Damage actions can share a Tick
or reuse a target-group key in later windows. A preceding Find and Damage need
not have equal end frames; pairing must retain its targetSource, context/key,
writer-order and BB-lifetime conditions instead of zipping equal-size lists.
The measured suffix initializes each Skill timer once and carries computed HP
across Skills for one unchanged target/attributes identity. This is conditional
suffix execution, not recovery of the unresolved full entry gate or autonomous
input acceptance. Pointwise raw entry fields do not establish a later helper's
read when intervening writes or replacement paths remain possible.

An observer qualified for ordinary native function entry is not qualified for
an internal instruction site. The existing entry-context bridge assumes entry
stack alignment and a hardware return address at the original stack top;
post-call body sites need their own alignment, stack-layout, register/flags and
relocation proof. Renaming an entry ABI or treating local stack bytes as its
caller return is invalid. Such a future observer must pass a production-native
harness before any game recording command is published.

The child simulator's qualified private clock observer now uses a dedicated
CALL-site ABI and a real instrumentation return address, while explicitly
leaving the original function caller unobserved. It preserves the original
source stack address and pairs post-frame-call/duration operands to the actual
thread-local Skill Tick. The native harness executes both displaced sequences,
checks register/flags/MXCSR/x87 protection, real Windows unwind walks and Stop
with subsequent instrumented executions. Active exception delivery is untested.
Stop closes logging only: the pinned module and CALL sites remain resident until
the game exits, and same-process rearming is rejected. This lifecycle needs its
own summary health policy; it cannot be admitted by forging the older
hook-disabled fields or renaming internal contexts as function entries.
Independent production forwarding/sampler qualifications and frozen launch
checks authorize a short normal-attack clock capture, not a repeated full fight.
No runtime clock selection or complete battle parity follows from tool readiness.

The admitted short clock recording now directly connects the original Unity
frame return, live castType, saved input deltas and actual duration delta/timer
under one Skill Tick. Same-cast-frame zeroing explains the selected nonzero-input
stopped Tick; it is not an ordinal rule or a TimeManager/Unity counter equality.
Five authored Skill components execute from source period/remaining and zero
elapsed state, carrying computed HP and comparing actual timing/dispatch/HP
without injecting suffix timer seeds or post-entry deltas. Query/Pack inputs,
source-order/BB semantics and helper/object continuity remain conditional.

A non-null cooldown list must not be promoted to the null-list path. In the
selected source, the signed helper return is preserved in one nonvolatile GP
carrier, and a separate counter starts at zero and grows only after a true
predicate. Bounded proof of both ordinary and special false-predicate routes
and the downstream gates excludes alternative counter writes, conditional on
ordinary Win64 helper preservation. Matching same-call count/completion and
element-offset carriers can therefore witness loop exhaustion. This recovers
the executed path without inventing concrete reloaded bounds or item values;
the helper's meaning as actual List.Count and independent cooldown prediction
remain unresolved. A sampled register value alone, without that full def-use
and alternative-path proof, would not establish the earlier helper result or
loop history. Other counter states are not silently forced into this case.

The same recording also closes four direct TryCast-local old/new Skill handoff
chains. Interrupt checking, old Interrupt, nested same-processor CastEnd with
casting clear, and new BeforeCast retain concrete same-thread scope and pointer
bindings. Their outer roots are separate Delivery calls, not observed physical
input or cache-dequeue causes. The copied nullable options prefix supports
conditional hasValue/force/ignore-distance/ignore-angle facts at reviewed
consumer offsets; it does not establish full Nullable extent, override-CD
meaning or replacement-path absence.

The simulator's conditional combo kernel now selects successors from authored
ComboCache modifiers and checks positive AllowNext membership in strict source
windows using computed old Skill time. It creates later components internally
only after selected admission and reason-seven stop rules, carrying computed HP
and resetting their timer from source duration. Actual success and timer/HP
endpoints remain comparisons. Readiness, actual mapping winner and native/helper
continuity are explicit conditions, and strict defaults do not turn them true.
This is a source-selected request/stop composition, not proof of the held-input
driver or a production-ready real-battle Gym action contract.

Post-CastEnd same-Skill Tick samples are retained only until the next same-Skill
BeforeCast. In these bounded epochs, casting is false, the post-frame point is
present, duration update absent and timer storage stable. Conditional retired
duration probes leave both the old timer and current component clock/HP alone;
they do not simulate all cooldown side effects, prove natural completion, or
establish allocation lifetime or global player-control restoration.

The selected request writer has now been authenticated separately. Its real-map
modifier is an unboxed value, whose skillId and instId pass through local storage
into the current request; remainingTime instead comes from the cache-helper
return. A successful ordinary selected Refresh therefore conditionally admits
the stored request ID as the selected modifier ID, without proving priority or
an authored creator. PlayerCommandData.GetCacheTime belongs to CommandBase.Tick
expiry and is not this mapping's default cache provider. Equal terminology is
not a dataflow join.

Static readiness inspection cannot turn the recorded source flags or empty
SkillTags into a constant true result. Dynamic entity-tag/controller/movement
checks remain, and nearby movement snapshots are not call-local operands.
The combined short observer targets named CanCastToTarget,
CheckTag/CheckState and actual ComboCache ExecuteInternal/OnEnd handle prefixes.
There is no declared OnStart hook in the selected class, and its environment
interface is recorded only as an opaque pointer. Exact ordinary prototypes and
typed list traversal, rather than open-generic placeholder offsets, gate these
recipes; the qualified existing producer is reused. Capturing created handles
and independent child returns is distinct from already admitted clock/stop data.

The combined recording is now admitted, and actual same-thread paired ancestry
separates Hero and Rodin predicate domains. Independent Cost/Tag/State results
are available; Rodin AI target refusals cannot be assigned to the player, and
normal/ultimate-skill cost checks under input callbacks cannot be assigned to the normal
attack target gate. Final TryCast success remains a comparison, never evidence
from which to fill missing owner/type/local-cooldown results. A whole-target
Boolean is an external CanCastToTarget port, not a readiness predicate. Selected
instruction-chain validation is not an every-path dominance proof, and a compact
projection that drops caller RVA cannot establish the exact native callsite.

Coherent complete individual Handle-list endpoints now link ExecuteInternal
empty-to-populated, stored request owner/instance ID, and OnEnd populated-to-empty.
The reviewed action native bridge supports a conditional creator/request/cleanup
interpretation; no-alias/helper/identity continuity remain premises, and neither
allocation lifetime nor absence of intermediate writes follows from equal
endpoint addresses. Captured OnEnd calls are nested under Interrupt/CastEnd;
this is not evidence of natural authored completion. Each removal-stage owner
Lock is independent, and emitting ClearSkillRequestByModifierInstId is not proof
that the callee's exact-ID guard cleared the request. Unmatched requests and
cache-helper return provenance remain explicit. These recovered rules are also
documented in the child simulator's maintained recovery and rule modules; the
generated inventories are not the sole durable record.

Input callbacks separately observe false normal/ultimate-skill cost predicates
while the callback Boolean itself remains true. In their complete projected
synchronous scopes no command creation or skill execution is observed. The
callback return therefore cannot stand in for gameplay acceptance, and a child
cost refusal cannot prove absence of deferred or independent-root delivery. The
reviewed input entry/save fragment does not establish a complete cost-guard to
command/return CFG; action binding fields do not identify physical keys by name.

A separately bounded callback audit now closes the metadata-ready ordinary
wrapper through its restored return: a present Func delegate receives the saved
arguments and supplies the Boolean; a null delegate defaults to true. Opaque
post helpers must return normally and preserve the saved nonvolatile result.
The indirect replacement route remains separate. No direct ordinary-wrapper
CheckCost guard or downstream delegate identity is thereby recovered. The
simulator models this return wrapper with an independent delegate result port;
an observed callback true does not fill that port for a prediction.

The complete getter projection also separates same-Delivery delivery from
historical writer candidates. Stored request modifier ID and skill-name pointer,
getter return and TryCast argument can agree inside one actual invocation, with
the selected Skill/Ability matching BeforeCast and the returned current Skill.
UID and cast identity delimit the prepared epoch. Earlier matching Refresh
endpoints are not a unique source; later observed conflicting Refresh marks
them superseded, without proving all intervening writes. Missing getters may
be called absent only after full per-hook projection accounting, never from a
deduplicated report. The child simulator now consumes independent whole-target
results and compares this local cache/preparation chain in the same five-attack
replay; source mapping winner, original helper paths, global scheduling and
independent collision prediction remain explicit boundaries.

The cache lane now recovers hardware caller headers already retained in the
original capture. Same-Tick CheckCanInterrupt results bind to the reviewed
`_AllowNextSkill` direct-return tail; no final allow byte supplies the predicate
being predicted. The reviewed zero-time Refresh dispatcher continuation also
retains its nested Tick's computed request on the selected normal tail. An
unknown constructor starts a new cache domain, seeded once from an actual Tick
entry; later snapshots compare rather than overwrite state. Matched outer
clears and nested Tick-owned clears are distinct effects, and getters do not
consume. This computed visibility, independent source-action Handle owner and
exact UInt64 ID now gate source Skill delivery in the simulator. Missing
modeled domains stay unresolved; no historical matching write becomes a unique
cause. Cache allScaledTime and Skill effective delta remain independent ports.

A retained serialized BattleCommandMappingConfig supplies separate ordinary,
dash and perfect-dodge cache candidates. The simulator's reviewed native
configuration contract now joins the typed global configuration field, serialized
enum-to-Single map field, named GetDefaultCacheTime signature and shared
GetValueOrDefault MethodSpec. The maintained export freshness guard validates
the selected source against the configured installed resource fingerprints.
The earlier expectation that each provenance stamp must contain nativeInputs
was a validator assumption, not evidence that a re-export was required.
Concrete runtime generic context, dictionary dispatch/FindEntry and the live
configuration object remain unproved; static typing and numerical agreement do
not admit the candidate as a global runtime default. A runtime remaining endpoint
never supplies the provider operand it is compared against.

A subsequent admitted selected-provider observation records the actual indirect
MappingModifier value at the cache selector, bounded skill text, typed current
Skill pointer and returned Single bits. Inner movement/perfect-dodge results
are owned by exact same-thread selector parents and reviewed native caller
sites, rather than neighboring frames. The simulator now independently selects
the input UInt32 provider bits and compares both selector return and published
request reference/instance/time. A normal-attack movement child at the native
original site distinguishes the actual ordinary route; nonattack calls lacking
an internal body witness retain original-path selection as a premise. The
published allow bit is a separate nested-Tick result, not necessarily the
constructor's initial false. Selected value observation does not recover the
competing priority queue, all map writers, or the upstream configuration/generic
binding. Equal current-Skill samples at Refresh and selector entries do not
prove uninterrupted lifetime, and no new-session operand fills an old session's
missing state. These durable distinctions also apply when scalar values agree.

Those same-session selector input operands now feed the simulator's complete
source-combo/cache execution instead of a fixed ordinary-route case. The actual
selected skill/instance must match the authored successor and created source
Handle; actual getter returns supply only visited selector operands. Independent
target predicates and cache-to-prepared-instance joins retain exact invocation
ownership. Request/selector outputs only compare with computed state; no request
or Tick-entry seed is introduced. Current and retained retired Skill clocks,
cache, pending handoffs, HP and actual frame-dispatch observations share one
checkpoint history. This narrower measured selection does not predict the
initial competing map, every mutation, or autonomous global scheduling.

Complete held/command observations already retained in that capture also allow
offline request prediction and command-state carry from recorded Reset history.
Reset actor capture remains an explicit opaque helper-identity port; numerical
state, time, blocked flag and delay are computed by the native lifecycle rule.
Independent consume/block predicates and exact synchronous OnExecute scopes
connect the resulting Attack commands to the selected cache constructions.
Later independent Delivery roots are not reassigned to nearby input callbacks.
When unknown movement and nonmovement branches produce identical timer bytes,
the simulator can eliminate that operand for the narrow result without claiming
the actual moveAxis value or branch. Positive timers whose outcomes differ
still require their own operands; nonpositive samples do not calibrate a delta
provider. A separate MoveAxis-command delay-write mismatch remains a named
mutation frontier rather than an invented default or an Attack-domain failure.

The authored canonical base map is recoverable offline through the precise
CharacterTemplate root, component RID, AbilitySystemData and
SkillDataBundle.defaultCmdMapping. The selected native OnInit field chain reads
that same typed member. The stored map includes the first normal attack plus
normal/combo/ultimate skill identities; complete initialization reachability,
priority-register continuity, collection helper effects and live owner choice
remain separate conditional joins. Fresh simulated opaque IDs may preserve
identity/equality without reproducing the historical absolute shared counter.
Allocation/recycle method names alone are not reset proof: their selected
original paths are no-op, while Release requests collection clearing. Full
pooled lifecycle effects still require their own control/helper proof.

The child fresh-map factory now constructs base values, absent runtime queues
and ordinary effective-map refresh from authored rows and explicit cache
candidates. Opaque allocators belong to the model; measured instance IDs and
provider values never initialize it. Current concrete dictionary allocation
contexts, constructor requests and publication are authenticated separately
from the selected fresh-zeroed-allocation and normal nonescaping-helper
premises. These premises do not establish a full allocator or later-writer
closure, and matching recorded base selections remains comparison evidence.

The fixed Delivery registration source requests FixedTickGroup with zero
interval and the OnFixedTick MethodDef, then stores the returned TickFunction
on the same controller. The ordinary callback's typed entity/AbilitySystem/
TickOwnerInfo path scales incoming delta in two Single stages; initial scale
guards and the later running reload remain separate. The observed delta is
not a universal simulation timestep. Actual callback registration lifetime,
virtual target, local scale values and engine phase/frame production need their
own binding. Execute's separately resolved bark-system notifications must not
be relabelled as AbilitySystem state events or used to attribute a delay writer.

The combined passive control observer is now qualified offline in the child
simulator. Controller/Base Consume binds by synchronous parent, native caller,
receiver and low-byte force; both effective delay getter returns are retained
as independent Single carriers. Returned command state is comparison-only.
Getter-free clear branches remain valid but an unobserved virtual OnConsume
effect blocks their full-state prediction. Device-specific affect and missing
visited operands are explicit per-row frontiers, not guessed defaults.

Concrete MainCtrl.OnFixedTick supplies the center/entity/Ability endpoint path
and retained TickFunction delegate identity. The existing shared generic FSM
Tick receives no derived-class deep reads and keeps its established ABI. Its
default virtual-slot helper is joined through a reviewed native caller,
immediate parent and matching center receiver; other fast targets remain
distinct. Scheduler owner info cannot replace the local Ability scale operand,
and matching callback endpoints do not prove uninterrupted registration life.
These declarations and production/frozen gates prepare a short combined sample;
they do not retroactively add runtime coverage to the previous recording.

The admitted combined recording now directly supplies the actual MoveAxis
Controller-to-Base Consume branch and both reached effective getter results.
Delayed state is computed from entry operands and independent Single returns;
the returned nullable value only compares. Getter-free threshold clearing is a
legitimate lazy path. The controller call is a separate observed root, so this
does not attribute it to an earlier attack scope or reconstruct all input roots.
MoveAxis has its own OnConsume override; the attack class's inherited empty
callback must not be generalized to it. Its ordinary body clears a derived
Vector2 and preserves Base fields, while its own replacement selector remains
separate from the observed Base Consume selector.

The same recording binds concrete OnFixed callback target, method pointer and
MethodInfo endpoints to immediate center-FSM calls and onward selected
CenterAttack TryCast/BeforeCast preparation. Concrete entity/Ability pointers
can change during the session and are retained separately. Stable generic
current-state endpoints are not proof of the selected OnUpdate implementation.
The reviewed shared float-delegate helper explains the observed callback caller
and has a source caller from TickFunction, but its sharing prevents inferring
the live outer TickFunction object from delegate equality. Local Ability scale
operands, scheduler gates and uninterrupted registration remain explicit gaps.
Reusable declarations and checks are maintained in the child simulator's
contracts and recovery modules; detailed observations remain generated reports.

The delayed command value now carries through subsequent independent controller
gates and Tick deltas to expiry and invalid-state continuation without later
entry seeds. Concrete callback Base-field noninterference remains an explicit
source-backed selection; strict mode stops at its unobserved dispatch rather
than borrowing returned state. ConsumeMoveCommand's first direct StartMove
consume is followed by a controller reload and tail MoveAxis consume with no
intervening call. Exact adjacent scopes and inherited return addresses support
this conditional continuation, not an attack or physical-key attribution.

The pure TickFunction model preserves the initialization-ready normal callee's
ordering. Its return is Boolean: owner-group skip returns before stamp/frame
writes, near-zero callback rejection occurs after them, and a null callback may
still return true. Caller-owned interval/frame eligibility remains distinct.
The next child observer combines the concrete MoveAxis callback selector/axis,
pre-multiplication OnFixed arithmetic inputs and filtered outer TickFunction
invocation. Its isolated overlay, mixed ABI, displaced MULSS behavior, parent
scope, transport and all sampler groups are qualified separately. No original
SDK source or older capsule is changed, and qualification creates no runtime
observation or guarantee of process stability.

That observer's retained follow-up failed from queue saturation, rather than
unreadable or truncated fields. It is not a complete admitted capture. The
child's maintained salvage consumer authenticates its staged producer and
current observer/layout closure, hashes the raw journal, finds exact missing
sequence IDs and stops before the loss/failure frontier. Inter-thread row
reorder is not loss; unfinished scopes and post-gap state remain unavailable.
Complete pre-loss pairs nevertheless observe the concrete MoveAxis selector
endpoints and axis clear, actual outer TickFunction object/callback dispatch,
and reached local scaling operands delivered to FSM. The core recomputes both
Single multiplication stages from those operands, without inferring one from
equal input/output deltas. Ordinary callback continuity remains conditional;
empty selector endpoints do not close all writers. TickFunction's own group
scale is still distinct from the local Ability owner and is not supplied by it.
These observations do not need repeating. The broad legacy Skill tick traffic
dominated the failed profile; any genuinely necessary future observer requires
a separately qualified narrow scope and throughput evidence. Local regression
does not rehabilitate an incomplete capture or enable the real scenario.

The child now also proves the complete initialized ordinary nonexclusive
TickGroup path. Released and direct shouldTick checks precede interval
eligibility, whose threshold is a nonzero native literal. Under the supplied
Boolean, signed wrapping frame-difference and timestamp conditions, the group
may narrow elapsed Double time into the forwarded Single delta. Tick and this
group request Unity's frameCount internal call; a resolver name does not identify
the live cached function pointer or generate runtime frame values. SetInterval's
ordinary store copies its new timestamp from an unresolved helper result, not
from an assumed engine clock.

Actual pre-loss TF callers bind to the nonexclusive group's direct callsite.
Their zero-interval entry snapshots satisfy the recovered eligibility projection
under explicit snapshot-preservation premises. Original group delta and Boolean
inputs remain absent; downstream TF delta does not supply them. This does not
observe a positive-interval or catch-up branch, close helper/list lifecycle, or
prove global scheduling. The child extends its existing clock core and contract
rather than adding one module per proof; exact frozen historical sources retain
the earlier diagnostic's provenance when the current contract evolves.

The TimeManager ordinary source now supplies the fixed dispatch's actual input
origins: cached logic delta and Double logic time, with a true flag. Initialize
converts the configured integer rate to Single before the Single division;
Tick accumulates a supplied render Single into Double time and emits each
reached fixed step. PreLate has a distinct metadata-authenticated phase and
forwards cached render delta/time with a false flag. Managed manager frames
remain distinct from Unity frame-provider results. This is a source-derived
cadence projection, not a frequency guessed from observed deltas or wall time.

The child carries one initial clock snapshot through consecutive manager frames
using independent cached render inputs, and one initial TF stamp through later
source stores. Unexpected configuration/writes, multiple threads or missing
frames stop the projection without reseeding. Predicted fixed calls match the
actual TF parameters in sequence-bounded render windows under explicitly
selected root membership and ordering premises. Numerical agreement does not
prove that the live TF group is a member of the sampled manager's fixed root;
that missing identity join alone does not demand another recording.

The original full-fight journal already contains the physical world fields
that earlier compact clock outputs omitted. A bounded re-selection connects the
same clock model to a complete normal-attack sequence. Native metadata gates
each admitted field; labels or containment within a raw span are insufficient.
Ordinary Skill second-argument candidates converge bitwise when the independent
manager scale makes the unknown reason/selector alternatives equal. Initialization
zero arguments are independently tied to the checked TryCastSkill call block.
Neither route is selected from the observed callee argument, and signed-zero
differences remain distinct. Ordinary first/scaled delta, local HitStop factors,
internal frame gates and full control recovery remain separate. Check actual
frozen read declarations and retained journal coverage before treating a compact
projection's omission as a reason to request a new capture.

Retained Dilation return witnesses can recover synchronous Skill invocation
context through exact thread and immediate-parent invocation IDs, closed parent
scope containment and actual PreLate ancestry to Ability. This is distinct from
the affected-owner binding: readable return handles, duration, curve references
and elapsed values do not prove entry state, curve evaluation, handle lifetime
or the effective group-cache write. Zero Dilation delta/elapsed endpoints do not
justify a zero or identity Skill scale. Nearby returns without an exact parent
remain unbound rather than being assigned by time or address proximity.

Observation coverage requires the consumer's actual physical call route, not
only a same-named metadata method and a valid prolog. Entity Dilation bypasses
the named AnimationCurve Evaluate wrapper through its cached icall and reaches
physical modifier helpers distinct from the named registered methods. Its
curve return is clamped before the actual modifier Add input; the delivered
factor cannot recover an arbitrary negative/NaN raw curve result. Source-typed
machine operands and opaque trailing GP carriers are not a complete managed
prototype. In particular, a caller ignoring a return does not prove void and
does not justify a typed void detour for unknown callers. Preserve unknown ABI
effects through a transparent entry observation instead.

The admitted combined clock/control sample confirms that Root.DoTick reaches
its ordinary and exclusive group functions directly. Absence of a separate
TickGroup.Tick wrapper observation is therefore not evidence that group
scheduling is absent. Actual manager input, its root-slot pointer, the native
caller and the recorded Root scope bind fixed dispatches without selecting an
instance by matching timestamps. Unobserved list elements still require a
registration/no-migration premise; manager FP controls remain distinct from
separately sampled Ability controls.

The retained physical modifier inputs also support an ordered self-cache fold:
start at source Single one and narrow each multiplication over the complete
incoming list. Add's already-clamped factor and an opaque UInt32 allocation
label construct the expected appended entry; returned lists and cache values
are comparison endpoints, not seeds. This does not recover the raw curve or
the handle allocator. One initial list per group can carry later mutations
without resetting, conditional on successful Remove/Clear effects, no other
writer, preserved FP controls and uninterrupted group-address lifetime. Strict
replay stops at the first unproved effect. Missing Stop-scoped recalculation
observations do not establish that no recalculation executed.

The second local Ability probe precedes both MULSS operations: its selected
global-or-one register is not the first product. Preserve each probe's own
group pointer and observed floating controls before predicting Skill inputs.
TickOwnerInfoGroup's owner metadata declaration is Object; same-scope actual
get_owner results and Remove-group owner equality may independently bind the
selected Entity, but the declaration alone does not give Entity type or a
continuous lifetime. These component rules and their explicit external ports
are maintained in the simulator's existing hitstop and replay owners.

DamageActionData carries the inherited serialized `serverActionIndex`; this is
distinct from a recovery reader's node ordinal. In the selected normal-attack
plans, independently bound source Skill, Damage data type and stored index can
uniquely select a source action. That uniqueness is local to the reviewed plans,
not a global game identity, and a live match still needs its own runtime read.
An inherited generic reference prefix may be proved separately from a derived
class's full suffix extent: the concrete parent argument, sole reference field,
base size, first derived field and exact native consumer reads must agree.
Unsupported later value-structure fields do not justify guessing the whole
layout or weakening a general reference-layout validator.

The combined runtime sample now supplies the stored Damage index together with
actual cast/environment endpoints, so selected normal Damage actions can join
their unique authored nodes without ordinal matching. The native order agrees
with the source time schedule even where the physical serialized node array is
ordered differently. A scope without Process observation is not automatically
a miss. Extra non-HP modifiers within the same Process are separate effects,
and incoming player HP cannot be appended to the outgoing boss HP domain.

The same sample supplies reached duration-loop witnesses and callback-time
TickFunction/component/owner snapshots. Opaque helper counts and completed
cursors are actual inputs, not inferred List.Count. Per-call admission must not
leak to an unobserved retired/paused path. Previous valid same-object TF stamps
can conditionally drive interval/catch-up arithmetic; first samples, replacement
or missing snapshots break the carry. The actual callback owner/unscaled and
additional-scale reads select the arithmetic branch, rather than choosing one
because its result equals a recorded delta. Manager frames and the independent
TF/Unity frame provider remain distinct.

The same admitted sample can now start normal Skill timers at actual BeforeCast
epochs using authored duration and zero elapsed time, then carry calculated
local cache through actual Unity frame-return gates. Later timer endpoints only
compare; older pooled Skill calls before a known cast cannot be back-seeded.
Every observed cooldown list is present. Without its internal traversal witness,
strict execution stops, while the conditional model explicitly selects ordinary
helper return and timer/processor/delta/FP noninterference; it never invents a
zero Count or substitutes null. A recorded not-casting predicate explains timer
freeze but does not independently predict complete control recovery.

Damage request ancestry and retained environment UID/castId/sourceSkill bytes
bind the same invocation to the current cast. Request timing/count agreement
does not identify a runtime Action with a source reader's node ordinal or settle
target HP. Also retain Ability's delivered delta as an independent port: some
actors receive a different delta from their enclosing PreLate Root. Even when
all selected-actor values match, equality is not an observed TickFunction
interval/catch-up selection. The simulator's existing source-clock component
and lane regression preserve these boundaries.

Skill.m_ability is an Ability behavior carrier, not the execution AbilitySystem.
Use actual direct PreLate/TryCast parents and native callers for that execution
context. Retired Skills may retain different Ability instances from the current
Skill; a pointer mismatch between those layers is not a reason to discard Tick.
An observed CastEnd with a direct same-Skill Tick parent can be bound to the
audited duration-completion callsite and explicit argument/timer endpoints.
This proves the reached request and casting transition, not the earliest
accepted input or the cause of later movement.

An independently admitted joint session now supplies normal-attack natural
completion witnesses. Recompute each complete active prefix from authored zero
timer state through actual delivered arguments, ending at the exact parent Tick
of CastEnd; compare later timer endpoints rather than using them as seeds.
Same-owner PreLate slot clear followed by a normal-input signal and a new
accepted cast establishes that observed chain, while callback lifetime and
physical idle remain separate. Conditional shared cleanup joins can preserve
unknown raw-action/target presence and apply only common direct stores; their
opaque-effect noninterference premises must stay explicit. A shared generic
rule for other normal skills does not expand the observed skill domain.

Creation-bounded normal handoffs can now construct a request without observing
an old request payload or seeding from Tick entry. Refresh.entry contributes only
a complete no-retained-input witness. With the independent source successor,
created Handle identity and explicit provider/route operands, the selected
nonempty mapping computes an identical whole replacement for both old-presence
possibilities and emits no old-input Dispose request. Unknown cache therefore
becomes known through a computed overwrite; an empty mapping preserves unknown
or existing state instead of manufacturing an empty request. Subsequent Tick
and getter state is carried continuously, with returned request fields and
Refresh Boolean used only for comparison. This narrower construction proof and
its continued checkpoint forks coexist with the broader entry-seeded cache
replay. Actual winner, runtime branch/provider selection and writer/instance
continuity remain conditional.

The simulator now reexecutes source construction, cache clocks and Skill clocks
in one checkpointed state machine rather than supplying previously calculated
cache visibility to a separate Skill runner. Getter state is read from that
same instance before Handle/source/target-gated submission. A checkpoint with a
visible cache and pending handoff replays subsequent cache and Skill operations
together. When the covered source-action lifetime ends, loss of cache knowledge
is explicit: unknown cache is not a predicted Clear or known-empty state, and
it does not cancel pending delivery or alter Skill time/HP.

The retained post-stop samples can be replayed throughout the covered interval,
not just at its first probe. Each keeps the stopped Skill's computed duration
unchanged while the current Skill, cache and HP continue independently. Retained
prefix coverage does not include omitted callbacks or prove full cooldown
effects. An explicit observed-dispatch port tracks actual Unity frame values,
thread/invocation order, bounded cast identity and active/retired roles. Multiple
Skill calls in one frame are not additional world-time steps; neither missing
frames nor autonomous scheduler callbacks are synthesized.

Additional complete normal cycles retain usable clock operands and cooldown
completion witnesses. Their missing spatial projections can be recovered by a
targeted authenticated original-journal pass, with actual scope/epoch ownership;
the existing compressed clock carrier supplies later retirement windows. Each
cycle now has its own query geometry, target prefix, formula/cache operands and
handoff scopes for the same joint kernel. Authored-duration/zero-elapsed timers
and within-cycle HP are calculated; cross-cycle HP/input gaps remain external.
Downstream damage never supplies its own upstream spatial selection.

The wider scope establishes that equal Skill and action pointers can refer to
different casts. An earliest equal-pointer creator is therefore not a valid
later-cast source. The source-slice selector requires the unique same-thread
creator and exact-Handle OnEnd interval that contains the actual handoff request
entry; outcomes and returned cache payloads do not choose it. Overlapping
candidates fail closed. This narrows the sampled epoch without proving all
unobserved lifecycle writes or the runtime competitor queue.

The current retained recordings lack the actual MappingModifier value passed
into the cache selector and its float return, plus same-call movement/perfect
predicate returns. Source candidates and repeated numeric agreement cannot
reconstruct these absent observations. The simulator-owned combined passive
recipe observes those entry/return operands and current Skill while preserving
input/delivery/clock scopes. It reuses qualified SDK wrappers and additionally
tests the exact newly used typed-return variants; no SDK source edit or game
launch is part of preparation. Live readability/coverage still requires the
short sample, and selected-value observation alone does not establish candidate
queue construction or unrestricted global scheduling.

Actual cancellation getter scopes can be joined to the nearest completed Tick
within the same cast and checked against independently source-computed Single
timer bytes. Conditional timer-branch eligibility at other endpoints is not an
observed marker state, query return or input-restoration event. The first actual
true query need not be the first eligible timer endpoint; full player-control
restoration remains a separate join.

The selected Refresh.entry samples independently retain the typed owner's
current-Skill pointer. Exact thread/invocation/controller/owner/source binding
admits passive presence at entry, not continuity to a later selector read.
Movement mode, perfect-dodge and live provider selection stay unresolved. The
retained dictionary pointers and action-owned Handle lists do not expose the
controller's complete competitor queue or selected real-map value. A complete
one-Handle action list therefore does not prove the actual priority winner.

The admitted false-Refresh audit observes unchanged semantic old requests and no
nested cache Tick in other command domains; it contains no false attack Refresh.
Neither false return nor missing child call identifies a null/empty provider.
Exact-instance cleanup uses independent entry IDs before comparing returned state;
unobserved mismatch and empty-provider cases retain their conditional boundary.
These local coverage limits do not require another capture while source-constructed
normal-attack delivery can still progress on the retained evidence.

The cancellation getter's source conversion is now also checked against both
false and true queries in one actual later attack5 cast, bound by Skill, Ability,
timer and cast epoch. The threshold is calculated from authenticated source
frames and Single rules, not from the first observed true time. Sparse query
brackets do not prove earliest input acceptance or unchanged marks between
queries. Player-action permission remains independent and supplies no observed
false-to-true restoration edge in this sample.

The [calibration reader](../../scripts/game_data/damage_runtime_calibration.py)
retains Pack returns, enclosing actions, dump calls, typed getter callers and
outer modifier candidates without merging multiple targets into a hit. Unknown
or zero pointers do not create joins; non-exact typed fields cannot supply
numeric operands. It streams a source-bound attribute sidecar, verifies source
fingerprints and counts before publishing, and leaves prior outputs intact on
input-validation failure. Candidate identity equality still does not establish
object lifetime or attack ownership. Critical/block/RNG/skill fields remain
unknown; these diagnostic candidates are not Gym transitions or reward labels.

The retained EnemyTable selects the same attribute template, with no per-row
attribute modifiers, for ordinary and weekly Rodin. That retained template's
level row agrees with observed Level, MaxHp, Atk and Def in the admitted battle.
This is a stored-data/observed-value comparison, not a proof of initialization
order or of an unchanged export. These numbers cannot distinguish the two
variants; the weekly row separately names an AI override. Re-recording base
stats alone therefore cannot resolve weekly AI selection.

The current fragment contract also authenticates the Modifier flag enum and
construction windows, the normal Dice threshold branch, and the extra-target
consumer. Critical and blocked bits can be interpreted in the retained later
Modifier field under the explicit normal-construction/no-intervening-writer
conditions. This is separate from directly observing the Dice return. In the
reviewed normal Dice path, a finite probability at or below the authenticated
epsilon returns false; applying that fact to a dump still requires the correct
source-array and invocation join. A later flag or final HP must not select the
source array or the random outcome used for a formula prediction.

The later Single multiplier is the enemy-part `damageRatio` field. It is used
only on the selected extra-target path with the stated damage-type exclusion.
The two ExecuteInternal call sites pass different literal extra-target values,
but a recorded damage-unit index of zero alone does not identify either call.
An ordinary entity name also cannot exclude a part-compatible receiver.
Consequently the existing record narrows this gap without proving the branch
was skipped. The runtime replacement table's live selection remains unknown;
a static null/default branch is not evidence that it was taken.

That formerly anonymous selector now matches
`DamagePackData.get_defenderPoiseFactor`: the selected named getter, the
ProcessDamage fragment and the standalone formula share the same root, table,
function and receiver slots. The normal getter returns Double one; an active
replacement supplies the factor instead. The native validator checks these
selector identities and default/patch edges, not merely a similar method name.
This identifies the operand without proving its live value. Because the
selector is present directly in ProcessDamage, a named getter observer may
remain unvisited; nonentry cannot establish a factor of one.

A later complete joint capture independently observes the factor Double at
its arithmetic use, the health/UsesRaw return values and typed defender.data /
healthType boundaries within the same Process/Pack context. Its admitted
normal contexts supply factor one and false predicate returns without fitting
HP residuals. This closes those actual operand/data joins for that session;
it does not prove default versus IFix selection, exclude intervening writers
or repair the identities of earlier crashed sessions.
Typed HP settlement must bind both outer and child modifier entry types to
the selected branch. HP/Add is a positive signed operation, while zero Add
can return Cancelled with cancelReason None and preserve entry realDelta;
that differs from DamageImmune's type/reason mutation. Continuous player HP
can include directly parented healing events from the same actor/attributes,
without reseeding from later damage entries. Healing amount/schedule remain
external until Buff production and its parameters are independently recovered.

Existing retained IFix payloads contain no fix record for this getter. The
current patch publication path requests the runtime HotPatch API; its internal
call boundary does not expose the historical replacement-slot state. See
[IFix ownership and limits](ifix_patch.md). Neither an absent stored fix record
nor an empty log search proves that a past invocation used the default factor.
Poise-related attribute snapshots and outer Poise modifier deltas also do not
record the getter result, current-poise state or the actual replacement choice.
For those earlier unobserved invocations, keep the live factor and independent
bounds unknown; settled HP must not supply them through residual fitting.

The extended branch recipe observes the module selector at ProcessDamage entry
and return, with two bounded collections of root/table/function/receiver at each
boundary. Null, unresolved, changed and unreadable snapshots remain distinct.
Even equal snapshots do not prove unchanged state between reads or selection at
the arithmetic instruction. Two typed wrapper candidates are scoped to the
reviewed indirect-call return site inside ProcessDamage. A captured normal
return observes that physical callback's Double result; no hits or an unmatched
active function do not select one. Calibration retains these returns separately
from selector snapshots and from each Pack's unknown factor, because a shared
ProcessDamage ancestor alone does not prove a unique Pack-to-callback mapping.

A retained short branch session now supplies admitted selector boundaries: its
entry/return snapshots show a resolved root with a null table, and neither
scoped callback candidate is entered. The incoming extra-target flags are false.
This narrows the selected samples without recording the factor instruction
itself. The conditional rule is precise: if the original normal arithmetic path
reaches the selector and no intervening write changes its root/table choice
before the selector loads, the null-table fallback contributes Double one.
No existing writer/synchronization proof excludes an intermediate change and
restoration, so actual path/value remain unknown in the observation report.
Repeated identical boundary recordings alone would not remove that condition.

Under that explicit factor-one/ordinary-non-RawDamage hypothesis, the existing
simulator arithmetic reference reproduces every compared outer Modifier request
in the short session bit-for-bit as Double. Inputs come from the authenticated
attacker/defender caller roles in each Pack's own nested dump, its observed DEF
Single return and the conditional later critical flag interpretation. The sample
also narrows each comparison to a single Pack and outer Modifier under the same
ProcessDamage, with matching source/target attribute identities. No multiplier
or critical branch is chosen by residual fitting. This supports the conditional
fragment model; it does not prove selector continuity, normal-path reachability,
array-to-frame lifetime, general floating-environment parity or final HP policy.

The independent [Process route reader](../../scripts/game_data/damage_process_route_native.py)
and [reviewed contract](../../scripts/game_data/contracts/damage_process_route_native.json)
now authenticate the Pack caller, predicate argument joins, default enum rules,
selector families and bounded bypass/merge windows on the selected native pair.
The retained Pack return sites match the original Process call fragment. This
does not prove arrival at the factor selector: the health and Raw alternatives
occur afterward, and later Modifier observations are already past their merge.
The captured efficiency getter's caller identifies its Def helper body, not
the helper's incoming Process callsite; unobserved provider/replacement reentry
therefore cannot be excluded from this trace alone.

The ordinary `UsesRawDamageValue` rule is true for LifeDrain and Fixed and false
for Physical. It reads the local Pack's damage type, whose captured boundary
value still needs continuity to that read. Its replacement selector shares the
factor's root/table family, while the health predicate uses the same root with
a different table family. The latter matches `AbilitySystem.get_healthType`:
its original path reads the defender's data reference and then
`AbilitySystemData.healthType`; the predicate compares the resulting enum with
Independent. A replacement may supply that enum instead. The current enum maps
Normal and Independent separately, and existing fresh ordinary-Rodin component
data stores Normal. This remains a stored candidate, not a binding to the
historical defender.data or proof that its getter used the original path.
Factor-family null boundary samples do not observe the separate health family.

These default rules and call markers narrow the remaining questions to live
defender/data ownership, both predicate selections, local Pack continuity and
root/table publication during the interval. The route validator deliberately
retains unknown actual reachability/value; numerical agreement and later HP
settlement cannot supply those missing observations.

The retained field inventory explicitly separates AbilitySystem identities
from their Attributes objects. Neither retained combat session records the
defender's data-reference value or its healthType. A computed field address,
entity UID, Unity path ID or managed-reference ID cannot supply that missing
pointer value. Fresh Endminf and ordinary-Rodin stored Normal values remain
static candidates. No repeat decode of the full battle is needed to establish
this absence from the admitted capture schema.

The independent [HotPatch publication proof](ifix_patch.md) now bounds native
Set/Clear/ClearAll store order and the getter's stored native-slot identity.
Its writer/getter roots share an initialization value, not proven lifetime
identity. The conditional null-page persistence rule still requires exclusion
of resets and other writers, which the retained trace does not provide.
These static gains do not change the conditional damage regression or supply
an admitted observed factor. Operand evidence must bind live defender.data,
the actual health/Raw decisions and the arithmetic selector/result, rather
than repeat the existing Process entry/return snapshots. A later report
getter call can reevaluate the property and is not the original arithmetic
operand; the Process caller's saved pre-entry XMM register is not that operand either.

The separate [operand contract](../../scripts/game_data/contracts/damage_operand_capture_native.json)
and [validator](../../scripts/game_data/damage_operand_capture_native.py) now prove
a bounded alternative using ordinary function entries. The arithmetic factor
remains in XMM1 until one of the first post-arithmetic calls. The complete
reviewed normal-flow alternatives include class initialization, the report
getter and report-info entry. Only the earliest matching context in a complete
Process invocation can supply this carrier; later calls may clobber it or
reevaluate the property. This does not require historical patch-writer
continuity to observe the carrier, and does not establish that continuity.

The [operand recipe](../../scripts/game_data/contracts/damage_operand_capture.json)
adds scoped paired health/UsesRaw predicates and ordinary-entry contexts to
the existing branch profile. The health entry binds defender identity to its
live data reference and stored health-type snapshot. This is an entry snapshot,
not proof of the later native load or the getter's internal replacement choice.
Normal predicate returns record the actual health/Raw decisions. Projection
requires same-thread active Process ancestry, exact callers, a unique local
Pack identity and ordered false health/Raw returns before the factor context.

The [operand reader](../../scripts/game_data/damage_operand_inspect.py) separates
direct raw carrier bits from their conditional factor interpretation. The
normal-flow proof excludes exception/unwind, nonlocal and debugger resumes;
a normal Process return alone does not prove that no such event occurred.
Missing proof conditions or ambiguous joins withhold interpretation, and absent
factor observations never become one. Producer build, native checks and offline
decoder tests have passed. The first live operand attempt was interrupted by a
system bugcheck. A subsequent inspection of the retained files corrects the
earlier empty-journal assessment: the top-level journal is empty, but the
mission-trace journal contains paired predicates and raw factor contexts. The
earlier report already fingerprinted that nonempty journal: this corrects its
interpretation, rather than claiming the files were subsequently restored.
The separate [salvage reader](../../scripts/game_data/damage_operand_salvage.py)
checks retained DLL/session identity, profile/activation bindings, every complete
row's ABI, caller and synchronous ancestry, and source bookends. Only a closed
leading scope is projected. Its report remains explicitly unadmitted and does
not synthesize a complete capture receipt or relax the normal transport gate.

The salvaged scopes contain false health and UsesRaw normal returns. Their
health receivers equal the unique normally returning outer ApplyModifier
receiver in the same Process, whose entry identifies Rodin. The health-entry
data pointer and health-type field remain snapshots, not observations of the
later native load. Each scoped saved XMM1 low Double is one and its stack-local
address matches the unique Pack receiver. This is direct saved-carrier evidence;
it does not yet prove that the earliest *saved* context was the first actual
post-arithmetic call. No default getter or replacement path follows from the
absence of other contexts, and equal selector boundaries still do not establish
writer continuity.

The running status and journal can be checked as a local checkpoint. Session
termination is not logically required to prove delivery for an already closed
synchronous scope. A source-level candidate proof uses the exit row's queue
publication and consumption, followed by writer/status publication, to order
earlier loss counters before the checkpoint. The producer proof now has separate
bounded compiled lanes for recorder operations, writer fields and context
accounting. The [COFF/PE reader](../../scripts/game_data/coff_pe_match.py) treats
relocation-masked bytes only as candidate discovery, then checks actual targets;
same-cohort target consistency, exact literal contents and unresolved externals
remain distinct. TLS section-relative relocations are not ordinary RVAs, and
matching offsets do not establish the named TLS object's complete layout.
Capture rebuilds can replace Release objects without changing a retained
session's DLL. Preserve the selected object/DLL cohort before rebuilding and
use that retained cohort for historical checkpoint validation; current `out/`
objects do not inherit a previous producer proof.

The retained pre-input object cohort still matches the crash session's DLL.
The battle-simulator's independent TLS bridge checks selected context,
paired-entry and exit address programs against that cohort: PE AddressOfIndex,
the thread TLS table lookup, and the matching named SECREL displacement with
the count access inside the TLS storage extent. Compiled operand grammar is
checked separately from recorded bytes. Under ordinary Windows AMD64 TLS
semantics this proves selected storage-address relationships, not every TLS
access, active ancestry, guard dominance or hook epoch. Silent early exits and
Recorder/writer/output continuity remain necessary to exclude an earlier
omitted carrier; these selected address joins do not admit a numeric factor.

The simulator's compiled context-prefix extension now checks the ordinary
rejection cleanup and silent omissions. Null Recorder, invalid index, empty
nesting, no selected nonzero parent and caller lookup miss can omit records
without increasing the caller-read-failure counter. The newest matching nesting
key wins even when its stored identifier is zero. Only a nonzero selected parent
and failed caller-pointer read or a result length other than exactly eight
increase that counter. The search-result/end-pointer comparison is compiled
evidence; its allowlist interpretation retains an external-helper premise.
Rejected paths balance the active increment, while a passed prefix still holds
it until later processing. Capacity guards in paired entry do not make the
context reader safe against a corrupt nesting count. None of these local facts
establishes all earlier runtime guard values or complete callback delivery.

The retained-start extension additionally binds the retained-byte load to the
installation-attempt test on the valid-base/count path. Retained starts bypass
the atomic attempted-byte exchange; nonretained starts exchange one and branch
on the old byte. This excludes interpreting that guard as an unconditional
single Recorder lifetime. Retained eligibility/adoption, Recorder allocation,
publication and stop exchange, writer ownership and callback quiescence remain
unclosed. The corresponding regression models emit conditional control requests,
not successful adoption or proof of one runtime epoch.

The finite Recorder publication extension binds replacement, both start-route
publications, stop exchange and poll consumer operands against the retained
session/provider objects and DLL. Allocation's nonnull branch requests the
matched constructor; the selected join replaces one owner slot and conditionally
requests old-owner disposal. Both publications read that slot into the same
global recorder cell. Stop exchanges a supplied register into that cell; its
zero value is not established by the exchange slice. Poll relates the owner's
recorder pop to its writer request through the same record buffer and checked
write flag. Complete callee byte matches do not prove all allocator, constructor
or disposer effects. The unchanged instance across slices, full start/stop
control, writer lifetime, callback quiescence and one uninterrupted runtime epoch
remain unclosed. These local joins therefore do not admit raw factor carriers.

The simulator's complete stop-CFG extension now independently decodes every
selected instruction, branch/fallthrough edge and call relocation, then computes
register states to a fixed point. Under ordinary Windows AMD64 nonvolatile
preservation, the selected exchange receives zero; its sole value-copy predecessor
also prevents entry that bypasses that copy. Reaching this exchange atomically
revokes the global publication. Reachability of that runtime event is not
guaranteed. A conditional owner-slot clear still depends on an unclassified
register predicate, not a proved quiescence or disposal result. Direct owner
write inventory does not exclude aliases or callee effects. Start-to-publication
continuity, replacements, writer lifetime and one continuous Recorder epoch
remain unresolved, so the stronger stop proof still does not admit numeric
factor candidates or exclude earlier silent omissions.

The complete selected start-CFG extension additionally proves original-Session
receiver preservation to its state load, excludes reentry to that load and
tracks the nonvolatile state base through replacement and both publication
paths. The sole direct same-base owner replacement store dominates both
publication loads, including retained-hook publication. Checked load/NOP/store
predecessors prevent publishing through a bypass of the selected load. Reusing
retained hooks therefore does not imply skipping the Recorder owner write.
Intervening call effects, aliases and concurrent writes remain unclosed;
unchanged owner-slot bits require a separate premise and do not prove the same
live allocation. Start/stop control facts alone still cannot establish one
continuous epoch or admit the candidate damage-factor values.

A further retained-code alias witness binds both intervening status calls to
their actual linked target and passes the original state receiver with zero
flags through non-bypassable argument preparation. A complete selected acyclic
callee prefix preserves that receiver and freshly reads its Recorder owner slot
under normal ABI returns. This proves an exposed state alias and callee read;
it does not establish absence of later writes or unchanged pointee state.
Other calls, aliases/concurrency and live allocation lifetime still leave the
replacement-to-publication and publication-to-stop instance joins unresolved.

The complete selected status-body extension checks its switch table, call targets
and direct writes. Absence of a direct same-offset owner write does not exclude
aliases, overlapping writes, callees or concurrency. The selected old crash rows
and incomplete final summary do not carry Recorder allocation identity; static
code cannot create that missing observation. A separate new producer identity
lane is required for future records and must not repin or upgrade old receipts.

The simulator now retains a reviewed producer supplement with immutable serials
that saturate permanently instead of wrapping. New rows explicitly stamp
borrow/queue/drain identity; final publication/unpublication and loss/quiescence
checks are separate. Legacy rows remain historical without allocation identity.
The new source/version gate and passive Skill/ATB endpoint profile were compiled
and exercised offline through production parsing, disabled prologue examples and
real queue/allocator code. This prepares future observation; it is not a live
capture, full lifecycle journal, unobserved-callback proof or numeric factor
admission. A fresh game process and a short new sample are required for the
selected live bindings; unrelated static branches remain recoverable offline.

The subsequent serial Skill capture was received and independently admitted.
For its selected lossless paired records, borrower, queue and drain serials agree
with final publication/unpublication witnesses. Identity is scoped to one loaded
producer module and the observed records. This does not supply timestamps for
every allocation/destruction or callback borrow, prove a global no-reset history,
or retroactively bind the older crashed session. Complete Recorder epoch and
candidate damage-factor admission remain separate open joins.

Passive ApplyCost/exclusive/ATB setter entry and return observations are now
available. Fresh applied-cost flag changes have directly nested successful cost
checks; setter arguments and independent return balances are clamp-compatible
under original-path and maximum-read premises. Stable owner/delegate bytes are
endpoint observations, not continuous allocation identity or callback effects.
Actual debit, callback nonmutation and cost-query inputs cannot be obtained by
subtracting resource endpoints. Single elapsed additions and native-derived
interrupt getters also match the admitted endpoints under explicit precision
and original-path premises; neither match proves scale propagation or complete
input/control recovery. These distinctions are maintained by the simulator's
separate observed audits and conditional regression operations.

The new physical cost-query proof separates CostData's resource discriminator
from its base Single and from the selected normal-skill attribute adjustment.
Wrong or null CostData selects a zero base without necessarily selecting a zero
ATB query. On the selected original ready path the attribute's Double return is
converted to Single before the Single sum and nonnegative clamp. Nominal
ownership of the physical queries, live arguments and that attribute return
remain unresolved. Authored exports and resource residuals cannot replace these
operands. The new synchronous scope audit likewise preserves separate input
and command roots rather than inferring cross-frame acceptance by proximity.

The nonnull exclusive delegate code slots in the new admitted cohort identify a
registered enemy AI callback. Native fallback forwarding and the callback's
complete selected original body distinguish AI finish-state updates from player
control restoration. The callback clears its guard before null checks, requests
disabling the ability's CastEnd callback, then copies finish-wait bits and writes
WaitFinish. A later null failure does not undo the earlier guard-clear request.
The callback's Skill argument is unused on this original path. Observed delegate
bytes do not establish invocation, target-object class/lifetime or actual field
effects; those runtime joins remain separate from the native conditional rule.

The subsequent owner dispatch proof binds the full object-type getter to its
inherited entity field and typed Character discriminator. The caller's first
owner-kind check selects a second independent owner request before the
AbilitySystem wrapper tail-requests its controller with the Skill ID. First and
second owners must not be unified without additional binding evidence. The
selected controller prefix has a structural Nullable-storage byte test only;
its closed hasValue meaning and full Combo behavior remain unproved.

A safe next observation uses the naturally called, metadata-typed attribute
GetValue API at the actual cost-query caller and preserves its Double return.
Direct cached attribute bytes are not that API result, especially across dirty
or recalculation paths. Separate named primary cost getter entries can expose
their CostData argument fields and Single returns when naturally called, but
their complete bodies have no direct forwarding edge to ApplyCost's physical
query entries. A shared method name does not establish an ABI alias. The
physical callers also do not establish a zero hidden context register, so a
three-GP hook for those anonymous entries remains unadmitted. The next reduced
profile keeps these observation families distinct and uses the existing bounded
sampler rather than adding an unproved method-middle probe.

The selected original AI WaitFinish continuation stores Single(wait minus delta)
before testing completion. Only ordered nonpositive results additionally set
the finish flag and state None; positive or unordered results retain the countdown
store without those finish writes. The selected Tick state4 lane forwards its
preserved delta and returns true after the helper's normal return. Runtime
scheduling/receiver/delta and player control recovery are not supplied by this
native continuation or by an earlier zero-wait callback endpoint.

The complete Skill refresh wrapper and selected creation prefix also prove a
direct store of the caller-supplied SkillData reference before later helpers.
There is no clone before this selected store. The wrapper rereads initialized
after the helper, then conditionally requests refresh with false. This does not
close the live object's producer, subsequent writes or CostData values, and must
not equate a retained serialized asset with the live supplied reference.

The subsequent scoped endpoint capture has now passed an explicitly qualified
prepared-isolated reproof. Exact prepared source preimages execute in a separate
tree; reviewed simulator-Git JSON supplements supply prerequisites absent from
the historical inventory. Original profile failure is retained, and neither a
complete historical input cohort nor equivalence to the current research
workspace is claimed. Raw recordings, historical hashes and readers remain
unchanged. The simulator's source-snapshot, reproof and observed-identity tools
keep this distinction checkable for later endpoint audits.

The naturally called cost-addition attribute API returned positive-zero Double
bits in the admitted scope. This supplies the additive operand only: live
CostData's discriminator/base, complete query and actual debit remain unknown.
Skill labels use actual synchronous ancestry or nested gate observations,
not nearest timestamps. Independently authored conditional regression goldens
retain unknown base/debit flags; no model generates its own expected result.
Named-primary getter non-observation is not zero cost or a reason to repeat the
same observation scope.

Directly nested exclusive-to-AI callback pairs now bind the Skill argument,
delegate code/this/opaque argument slots and sampled ability component at the
endpoints. The raw parent owner prefix is an AbilitySystem pointer, compared
with Entity.abilityCom rather than the Entity pointer. Its remaining suffix
has no proved generation interpretation. Guard/CastEnd-callback clearing and
zero-wait WaitFinish endpoints match the conditional original rule, but do not
prove interior iFix selection, causal stores, allocation lifetime or later Tick
completion. Live cost-query context and AI continuation require distinct
observations. Legal null CostData must remain absent/unknown, not a numeric zero
or an unreadable-memory failure in a future context sampler.

The simulator's next observer now distinguishes arity-free ordinary-entry
architectural context from typed paired hooks. Saved registers bind the physical
cost-query arguments; the real ATB request is sampled at its typed resource
consumer, not inferred by subtracting balances. Legal null-root NoChain reads
are absent with no bytes, while invalid and short reads still fail. The fix is
built in an isolated SDK copy, with whole-thunk/sampler and selected compiled
transport checks against retained baseline evidence. Ordinary external ABI/CRT
and unresolved linked-target premises remain explicit. A fresh immutable reader
cohort, staged runtime/config/activation checks and streamed output prevent
unrelated current-source changes from requiring another recording. This is
prepared observation code, not an observed gameplay value, full DLL equivalence,
complete object lifetime, damage-factor admission or resource debit proof.

The combined cost/clock recording has since been admitted by its frozen
reader executed from the retained source tree. All selected observations are
present and final transport is stopped/lossless; an earlier running status
snapshot must not supersede the final summary. Saved RDX at the two physical
queries equals sampled live CostData; SP's saved RCX is CastData and ATB's is
Skill. Live discriminator/base and naturally returned attribute input now
conditionally predict the independently observed CostAtb XMM2 request for
same-invocation normal-skill gates. Upper register bits of a Boolean argument
remain unspecified; use its low byte. Context MXCSR confirms nearest rounding
and gradual underflow at observed entries, with differing sticky exception flags
kept distinct. Query return, read continuity and full debit remain separate.

The same recording also supplies a direct nested AI Tick/WaitFinish receiver
and delta. The countdown's negative result, finish flag and None state match
the selected native rule. The enclosing Tick returns true; a later separate
root Tick at the same address retains finish and returns false. This is
observed local dispatch and endpoint compatibility, not a general scheduler,
cross-frame allocation identity, callback causality or player control recovery.
The simulator's source-bound actual regressions use independent golden data;
models never author their own expected result, and absent inputs stay unknown.

The resource continuation can also be checked within the same observed
ApplyCost: the real request and nested SetAtb share the sampled manager, the
separate setter-entry ATB minus that request matches the passed parameter, and
the return endpoint matches the conditional clamp. Equality with an earlier
resource-entry sample does not make these reads continuous or prove callback
nonmutation. Helper Boolean/out-slot and final debit remain unobserved.

The captured AI Tick caller is now resolved by exact registered pointer and
instruction call target to EnemyCastSkillInRangeBehavior.OnTick. Its selected
original wrapper tests inherited finish state, passes delta unchanged to the
common skill Tick, then on a false result requests Exit, reloads the skill for
Finish and tail-requests its own finish setter. Each receiver reload is distinct
across calls. The setter's additional graph branches and the child effects are
not admitted by this caller proof; actual wrapper fields and receiver continuity
remain a separate runtime join. Proximity of native method addresses was not
used to assign the method name.

Full saved query context also shows nonzero incoming R8 words. The selected SP
body does not read them and the selected ATB path overwrites R8 before use;
they are not a proved MethodInfo or typed argument. Exhaustive exact registered
pointer lookup still does not name the physical query entries, leaving generic
or unregistered ownership unresolved. No getter alias or ABI arity follows from
these register values or native address proximity.

The simulator now has a separate verified observer family for the typed
wrapper OnTick and common Exit/Finish methods, with their selector roots/slots
proved from actual prefixes rather than copied by method ordering. Passive
Skill-to-Ability pointer and nonReturnedAtbCost reads reuse the existing paired
sampler: null chains remain absent, unreadable/short reads fail. This requires
no new SDK binary. Exact manifest/parser/guard/compiled-template checks and a
fresh immutable reader cohort prepare the next runtime join without repinning
old receipts or changing their frozen readers. Actual wrapper/cleanup fields,
stored cost and continuous lifetime are still unobserved at this point.

The [writer contract](../../scripts/game_data/contracts/capture_checkpoint_writer_native.json)
joins pop/write/flush/status requests to the selected physical candidates,
checks actual E8 destinations, and binds successful row/byte increments and
failure unrecorded increments to their branch conditions. Status labels, value
carriers and receiving insertion calls are checked together. The selected flush
body comes from the runtime translation unit; a different same-named COMDAT in
the mission session object does not match. A single object's nonmatch therefore
does not establish source drift or missing linked implementation. The recorder's
copy/fill targets likewise match retained older toolchain archive members rather
than the newest available members. Ordinary CRT behavior remains an explicit
helper premise, not a consequence of a symbol name or byte match.

The [recorder contract](../../scripts/game_data/contracts/capture_checkpoint_recorder_native.json)
checks complete finite push/pop programs, reachable roles, memory-write coverage
and queue geometry. Copy precedes admission and sequence publication; a matching
sequence precedes pop's copy, then cell release precedes dequeue advancement.
Error counters and the constructor's zero/sequence initialization are separate
from the operations' monotonic updates. No local counter reset is proved only
under compatible live objects, ordinary helpers, and an output Record disjoint
from the Recorder's complete storage. It does not exclude construction of a new
Recorder elsewhere.

The [context contract](../../scripts/game_data/contracts/capture_checkpoint_context_native.json)
binds selected actual thunk calls and TLS-relative consistency, and checks the
early unreadable counter increment before event sequence allocation. Other
early exits can still omit a row without incrementing that counter; their guards
need Process/caller/hook coverage. Executable references in the selected COFF
unit identify increment-only sequence uses and the enumerated recorder loads,
start stores and stop exchange. These are not an inventory of all module writes
or an observed lifetime. The ordinary-start attempt guard is a bounded fragment,
not proof that retained-hook adoption or another writer never occurred.

These local gains still require hook coverage and recorder-epoch/reset
continuity before the closed Process checkpoint argument can be admitted. Timestamp order
and equal counters alone do not close these joins or create a global atomic
snapshot. The existing entry-thunk/unwind checks do not prove these producer
paths. Consequently the value remains a conditional carrier candidate, not an
admitted numeric operand or replacement for the factor-one regression assumption.
The retained release DLL has no CodeView identity to bind the available older
debug PDBs. The COFF joins provide a bounded alternative, with explicit external
helper and lifecycle boundaries. No-reset inside a push/pop operation must not
be promoted to no replacement of the Recorder across Process callbacks and
checkpoint publication. Sequence-from-start plus truncate-on-restart can help
exclude intervening epochs only after global sequence lifetime, all publication
paths and the active writer/output instance are connected. Continue those
lifecycle joins offline before requesting new captures.
Stream-write success is not a crash durability receipt. Preserve the original
session and hold further live use pending crash diagnosis; the bugcheck alone
does not identify its cause.

The admitted branch session separately observes a Rodin-source modifier cancelled with
`DamageImmune`, leaving HP unchanged despite a nonzero modifier request. This
is an observed settlement cancellation, not a zero factor or evidence of which
animation/state caused immunity. Keep it separate from outgoing HP-decrease
samples and never use settled zero damage to infer a formula operand.

Saved branch admission uses the same reviewed recipe-inheritance loader as
preparation, including inherited kernel hooks. The closed generic source
carrier also requires its own narrow native ABI witness: ordinary concrete
value-type rules do not admit it, and its lack of pointee reads is deliberate.
Direct Boolean GP observations use the declared low byte; nonzero unspecified
upper register bits do not turn an observed false into true.

The [coverage reader](../../scripts/game_data/damage_runtime_coverage.py) uses
the dump's explicit GetFinalAttackValue parent before matching target attribute
pointer/UID and modifier candidates. This avoids conflating successive packs
that reuse one stack address within a DamageAction. A unique candidate remains
conditional ownership. Optional native interpretation additionally binds the
current contract digest, selected native identities and the retained flag field
layout, preserving raw observations and interpretation as separate fields.

The [source-role reader](../../scripts/game_data/damage_runtime_source_roles_native.py)
authenticates the current Dump body, typed Pack array fields, Attributes provider
ABI and the two getter-return/array-store transfers against the selected native
pair. It maps immediate getter callers to named attacker/defender destination
arrays. Old snapshot selector/body receipts are not reused when their build or
grammar differs. The role proof and its implementation sources are checked before
and after evaluation. Coverage may consume it only when its source fingerprints
and native identities match the retained capture. This removes the source-role
guess; it does not close runtime object lifetime, coherent snapshot timing or the
complete array-to-ProcessDamage-frame dataflow. The later flags and settled HP
never select which source is the attacker.

The separate branch recipe now supports a scoped observation of the actual
transferred-source ObjectPtr.Lock normal return. Its selected shared-reference
ABI and unique immediate ProcessDamage caller are independently checked. A
bounded return snapshot reads the returned object's class first and admits UID
and Single damageRatio only for exact equality with the resolved EnemyPart
ClassInfo. Entry, null return, unresolved ClassInfo, class mismatch and unreadable
memory remain distinct states; only the admitted finite ratio is numeric.
The offline reader binds both the return phase and returned pointer, and the
provider checks the ClassInfo cell against the actual loaded module size.
No extra getter/Lock call is made and no observed argument or result is changed.
This is observation code preparation, not a new live sample. The snapshot still
does not prove that the later arithmetic load sees an unchanged value; derived
classes and unknown replacement effects remain outside this observation grant.
The selected metadata includes `AbilitySystemForSoul` as an EnemyPart-derived
type; this exact-class observer deliberately does not admit it. A mismatch is
therefore not evidence that a returned object has no compatible inherited field.

## Character attribute formula

[`attribute_formula_native.json`](../../scripts/game_data/contracts/attribute_formula_native.json)
records how `Beyond.Gameplay.Core.Attributes` turns modifiers into a final
value (exact expressions there); `attribute_formula_native` re-proves its call
structure on the installed build.

The loader also accepts an explicit GameAssembly/metadata pair and optional
expected identities, checks the opened buffers and rechecks the selected files
after evaluation. Missing inputs, drift or failed claims withhold both formula
and method rows; the receipt retains native identities and the failed check.
This mixed claims/arithmetic-window contract still authenticates body bytes and
literals: absence of a `nativeInputs` block does not make its formula independent
of the selected build, and native validation does not establish runtime parity.

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

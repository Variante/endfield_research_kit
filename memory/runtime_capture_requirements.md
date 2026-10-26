# Required runtime captures

This is the shared backlog of game-data evidence that still requires runtime
capture. Append future requirements here under their owning topic. Extend an
existing matching entry rather than duplicate it. Keep accepted entries with
their evidence boundary and owning-topic link so later work can reuse them.

For each requirement, record the unresolved question, required fields and
ordered phases, representative cases, acceptance criteria, and links to the
owning memory topic and reviewed contracts. Native sites and build-specific
layouts belong in contracts; changing counts, hashes, inventories and raw
sessions belong in ignored reports or capture directories. The owning topic
continues to hold durable conclusions. Collection policy and authorization
remain governed by [AGENTS.md](../AGENTS.md).

## Shared capture requirements

Every observation must carry enough identity to join it to its own invocation
and selected native program:

- Selected binary identities, including GameAssembly, metadata and UnityPlayer
  where required by the owning native contract; loaded module base and image
  bounds for any address rebasing.
- Session and process incarnation, thread ID, invocation ID, sequence and
  monotonic timestamp; explicit linkage between entry, intermediate phases,
  nested calls and return or failure endpoints.
- Exact native instruction/phase and the applicable observer schema, ABI and
  source recipe identity.
- Raw register/value bits and memory bytes with their declared widths,
  addresses, read extents and per-read success status. Preserve interpretation
  separately from the raw observations.
- Complete final receipt, consistent attempted/admitted/written accounting,
  drained and stable final counters, and no losses or required-field read/write
  errors. Incomplete or contradictory evidence withholds the affected claim.

An entry snapshot cannot establish a later read, completed helper, result or
storage write. Pointer equality needs same-invocation address/range evidence;
address reuse alone does not establish object lifetime. A caller address needs
an authenticated same-session map for its actual module.

## Buff type identity, name-cache initialization and selected consumers

**Status:** required live joins remain uncollected. Offline constructor and
allocator-wrapper proofs establish conditional field/control results; they do
not establish the loaded metadata/image, live heap/import/callback selection,
cache isolation or concrete formatter/provider execution. Keep the static
proofs and hypothetical failure/alias traces separate from observations.

Owning evidence is in
[MemoryPack recovery](game_data/serialization_memorypack.md), with the reviewed
[constructor](../scripts/game_data/contracts/buff_name_cache_constructor_native.json),
[allocator wrapper](../scripts/game_data/contracts/buff_name_cache_allocator_native.json),
[handler getter/CFG storage](../scripts/game_data/contracts/buff_name_cache_handler_getter_native.json),
[guard tails](../scripts/game_data/contracts/buff_name_cache_handler_guard_native.json),
[guard lifecycle](../scripts/game_data/contracts/buff_name_cache_handler_lifecycle_native.json),
[handler setter](../scripts/game_data/contracts/buff_name_cache_handler_setter_native.json),
[direct saved-cookie writer](../scripts/game_data/contracts/buff_name_cache_handler_direct_init_native.json),
[complete direct-child stores](../scripts/game_data/contracts/buff_name_cache_handler_sibling_stores_native.json),
[name lookup](../scripts/game_data/contracts/buff_class_name_lookup_native.json),
[type-data initialization](../scripts/game_data/contracts/buff_type_data_initialization_native.json)
and [enum class fields](../scripts/game_data/contracts/buff_class_enum_fields_native.json)
contracts. Resolve sites and widths from the selected contracts and authenticate
their native inputs before collection; prose carries no rebasing constants.

Required phases and fields:

1. Link the selected name lookup and cache construction to their image, actual
   metadata header/base, query string bytes and candidate record/index/type
   identities. Capture entry and returned cache pointers plus independently
   read counts, capacity, generation and marker/node fields at each actual
   consumption phase. Track allocation range and lifetime, not pointer equality
   alone.
2. Link constructor allocation to the wrapper's actual input, heap-handle read,
   flags/byte-count arguments, live IAT pointer and loaded target-module identity,
   return or failure. For selected retries, record each fresh gate value,
   getter word, dispatcher slot/target and low-width returned value. For an
   encoded handler getter, sample the cookie and encoded word at their actual
   separate reads and the saved decoded word across the second guard call.
   Resolve the loaded/rebased CFG dispatch slot rather than treating its
   on-disk default JMP RAX target as live selection. For an
   error path, record the context child result, chosen field/fallback address,
   write bytes and overlapping ranges. Before/after cache/frame observations
   must share the invocation; an entry snapshot cannot prove noninterference.
   For guard lifecycle, record the actual caller/order, counter at initializer
   entry, each object argument and full EAX API result, counter writes and each
   reverse cleanup invocation. Preserve AL and full RAX separately at returns.
   Link getter/setter guard calls to valid initialized object lifetimes, loaded
   import targets and actual acquisition/release phases. For every selected
   writer, distinguish the saved cookie from the global value at later phases,
   capture the emitted eight-byte store and subsequent sibling/guard writes,
   and retain thread/invocation/lock chronology. A direct store without its own
   guard call does not establish absence of an enclosing lock. Cover startup
   direct writes and later setter replacements separately; a partial writer
   inventory cannot establish a common cookie/encoded epoch.
   The selected direct caller's complete child bodies now prove their exact
   nonoverlapping global stores and conditional normal-return state. A live
   transaction still needs actual invocation/order, per-write raw values and
   intervening-writer chronology; these static bodies do not establish that
   the transaction occurred or that all other writers are covered.
3. Link insertion, duplicate-key selection and any growth/migration to the
   query/node string bytes, record pointer, selected table bounds and each
   consumed count/capacity view. Link the resulting class/primitive cell to its
   exact metadata/type record rather than treating a System.Int32 name request
   as returned class identity.
4. Follow the selected Buff enum/generic normalization and formatter/provider
   through actual field reads, output writes and the owning parent/root. Retain
   concrete type/method/context and source-byte identities. A shared entry,
   stored value, nonzero pointer or completed lookup does not establish the
   chosen provider or a game-side effect.

Representative cases include initialization, a later hit, miss, duplicate
insertion and actual growth, plus different concrete enum/provider selections.
Observed retry/failure cases may extend coverage; supplied external returns and
model aliases do not count as those observations. Require complete paired
endpoints, bounded raw reads, actual consumed-width values, no losses/errors and
consistent same-invocation/module/metadata joins before admitting each claim.
Unselected paths stay open. The missing original Skill source-capture receipt
is a separate cross-family acceptance gap: a new live run or reconstructed
receipt cannot stand in for the original authenticated source artifact.

## Audio Event, owner, listener and output selection

**Status:** playback and device captures accepted with partial coverage. Their
sampled records drain cleanly, native phases close and declared fields are
readable. The `audio-device` capture adds successful GetBuffer results,
byte-exact sink/render prefix copies and successful ReleaseBuffer results.
Queue lifetime and complete source-to-mixed-frame attribution remain required
captures; repeating the present playback/device fields does not expose them.
Offline original native cohorts already cover selected
physical Event/Action/source bytes, decoding, owner readiness and voice
admission, inherited bank parameters, filters, matrix/gain mixing and finite
render-buffer submission. They supply registry capacity, scheduling, a null
object component/default empty listener branch, one mixer bus and finite COM
responses. These conditions cannot decide which object, listeners, current
parameter overrides, bus/effects or device the game selects.

Existing saved source-owner and source-bridge profiles observe entry-only
source/carrier/owner fields. They lack component getter results, listener
selection, later frame/mixer reads and completed output. Repeating the same
entry-only observer cannot close this join. A bounded return/phase profile
needs reviewed consumer declarations and offline build preparation; the existing entry
profile is not that recorder. The new `audio-playback` preset is now prepared in
the current EndfieldCapture checkout. Its reviewed declaration is
[`wwise_playback_capture_native.json`](../scripts/game_data/contracts/wwise_playback_capture_native.json),
compiled by Audio's playback profile owner through the maintained preparation
command. Paired getter, routing, parameter-output, source-output, sink-submit and
frame-request calls preserve normal-return/unwind phases and synchronous nesting;
other consumers remain transparent entry snapshots. Reads retain their addresses,
width declarations and states, plus bounded listener/route/sample prefixes.
Frequent consumers use non-evicting receiver buckets and a bounded per-hook
budget; getter children of selected owner-routing calls remain together.
Other nested frame consumers obey their own budgets. Selected/skipped counters
preserve intentional coverage separately from queue loss. The first phase
capture shows default and held-component returns, a nonempty chosen listener
list, finite nonzero source PCM prefixes and normal sink-submit returns.
Selector playback serials match managed Event return IDs under the reviewed
queue transport, but these are conditional candidates without observed queue
allocation generations. Current package headers narrow source-word candidates;
they do not identify the occurrence the live stream selected.

The observer was corrected before the accepted repeat: aligned receiver bucket
collisions and unrestricted nested sampling amplified frame records; pre-binding
context reads now guard an absent embedded owner. Action serial/allocation fields
now follow their checked native load operands. The earlier fields with those
labels used different storage and must remain anonymous historical observations.
The streaming review in Audio's `playback_capture` domain owns saved runtime,
recipe, window, row-shape and pair checks; `playback_package_candidates` compares
only supplied corpus candidates with current headers. Their reports are local
evidence and do not publish a live Event-to-device claim. Corrected Action
serial/allocation reads now match selectors under completed native nesting;
playback-blob and selected-source inputs match constructed owners. Later PCM
retains those primary/embedded addresses under explicit lifetime conditions.
Complete native voice paths match full external package keys, and one live
finite nonzero prefix exactly matches original offline codec output from its
matching physical WEM. These are sparse content/ownership witnesses, not whole
live-buffer or device acceptance. The shorter managed path field can truncate
text while retaining valid Event/playing-ID scalar pairs.

The sampled sink-to-Windows submission gap is now closed by `audio-device`, projected from
[`wwise_device_capture_native.json`](../scripts/game_data/contracts/wwise_device_capture_native.json)
through the playback preparation command's `--device` option. It retains actual
GetBuffer HRESULT and returned-buffer identity, a bounded copied prefix before
ReleaseBuffer, and the release HRESULT. The existing sink-submit pair does not
retain those internal results; the native body ignores the release result and
can tolerate one buffer-request error without marking the sink invalid.
The observer discovers actual render-client implementations from the retained
client, installs them on the worker, and records only the reviewed native caller
sites inside sampled sink invocations. Early calls before installation are
counted separately. Device children retain their parent window during stop,
and buffer bytes are never read after release. Accepted pairs use the same
client and returned buffer under completed sampled sink nesting; nonzero finite
prefixes exactly match sink input and the actual releases return success.
Bootstrap skips remain excluded. This observes matched stereo submission,
without proving complete buffers, device processing or audibility. The reusable
review rejects changed caller/client/buffer/frame links and preserves failures.
Do not request another identical device capture to re-prove these passing facts.
The next recorder extension must observe queue allocation/retention/release
generations across handoffs, or retain a proved mixer-frame identity with actual
source/route/bus inputs and output. Existing sampled route pointers and latest
constructed owners are conditional continuity, not such a generation/frame join.
Complete cross-thread generations, ending frames, topology, unexercised device
formats/failures and downstream processing remain acceptance gaps.

The `audio-mixer` extension has now been captured, from
[`wwise_mixer_capture_native.json`](../scripts/game_data/contracts/wwise_mixer_capture_native.json).
It declares the owner's current stored playback serial/allocation/source beside PCM,
the actual mixer-row array and first-row descriptor/gain/matrix, and completed
master-output/consumer/sink-conversion nesting with raw stack gain pairs. It
retains the accepted device observer. These fields narrow the current identity
and conversion joins; asynchronous task and allocation generations still require
separate endpoints. Review of the caller operands found that earlier recipes
read task-state bytes instead of the row-pointer array. The corrected streaming
review excludes those historical array labels while retaining other valid phases.
The mixer session supplies completed output conversion, correct row/descriptor
reads and accepted device copies. Recorded constant gain reproduces the saved
first-channel output prefix, and another native decoded voice prefix matches
physical WEM content. Full frame/reset generations and unrecorded channels
remain open.
The initial serial declaration read a neighboring parameter word; its zero
values must not be interpreted as playing IDs. Corrected declarations now
authenticate the owner load against the already owned selector-blob serial
field. The old ID read is excluded, other owner/source storage stays usable
with an unavailable serial, and a short `audio-mixer` repeat is required for
that corrected current identity. The generic recorder binary is unchanged.
Exercise an already traced UI sound, a spatial character voice/attack while moving
the listener, then repeat a sound after its end. Stop cleanly and retain the
game until saving finishes. Accept only current owner/row read addresses,
completed native nesting and matching descriptor/sink identity with the shared
loss-free gates. Do not promote the later device frame by time or pointer reuse.

Required ordered phases and fields:

1. Preserve managed Event/playing/object identity and the corresponding native
   Action/queue allocation generation, source selection and owner creation.
   Record allocation, retention and release endpoints across thread handoffs.
2. At inherited refresh and component/listener selection, retain the same primary
   and embedded owner, stored object, component getter input and returned
   pointer, override flags, chosen listener vector/count/identities and default
   versus object-specific branch. Retain current parameter key/value bits and
   override/default branch, plus selected State/Switch/effect inputs where used.
3. Through voice admission, route attachment and frame preparation, retain native
   return/failure results, source/context identity, retained format/rate/pitch,
   filter controls, route/mixer bus identities and actual channel matrices/gains.
   Sample the same decoded/source-filtered/mixed buffers with bounded PCM spans
   and explicit frame counts; preserve leading, steady and ending/tail phases.
4. Follow the actual bus/effect graph to selected sink/device format, service and
   capacity results and render-buffer release/completion. Record failures and
   cleanup as endpoints. Submission proves only submission; real endpoint
   acceptance requires the corresponding returned result, and audibility needs
   independent observation.

Representative cases: first record one already traced UI action, such as the
factory belt-build click or photo popup, from normal bank readiness through its
end and clean stop. Then record one spatial character/voice sound while moving
the listener, retaining an actual object-specific component and listener choice
if that branch occurs. Include a repeat after the first voice is released to
distinguish allocation generations. A current parameter change is useful only
when its exact key/store and later consumer read are included. Unexercised
branches remain open; no per-character or exhaustive-line recording is required.

Accept only same-invocation/generation joins with authenticated native sites,
bounded successful field reads, completed return/failure phases and the shared
loss-free final receipt above. Name matches, timestamp proximity, pointer reuse,
an entry snapshot or a supplied offline topology cannot promote the result.
The inherited default branch remains reusable without recording it again.

Owning conclusion:
[`audio_native_hooks.md`](game_data/audio_native_hooks.md). Reviewed sites and
operand layouts:
[`wwise_inheritance_native.json`](../scripts/game_data/contracts/wwise_inheritance_native.json),
[`wwise_source_queue_native.json`](../scripts/game_data/contracts/wwise_source_queue_native.json),
[`wwise_voice_pipeline_native.json`](../scripts/game_data/contracts/wwise_voice_pipeline_native.json),
[`wwise_voice_routing_native.json`](../scripts/game_data/contracts/wwise_voice_routing_native.json)
and [`wwise_sink_negotiation_native.json`](../scripts/game_data/contracts/wwise_sink_negotiation_native.json).

## Cooked collision and live Mesh state

**Status:** accepted for the selected Dijiang light Mesh's CAB/PathID identity,
later completed-physics checkpoints, complete vertex/index cache equivalence,
the observed Collider-to-PxShape-to-cache attachment, and sampled actor scene
membership where typed actor headers are present.
The native-core session reaches every requested epoch without loss or lifetime
gaps. Its held `PxBVH34TriangleMesh` path and native getters authenticate the
pointer-bound arrays; the decoded values agree with the stored cooked payload
throughout the sampled epochs. Remap/edge/slab bytes also agree over their
stored extents. The intermediate busy identity-map lock remains explicit and
uses conditional retained-identity reuse; later direct mapped reads agree.
The saved Collider windows also establish concrete current-shape attachments
after instantiation and at the first completed-physics checkpoint, with partial
intermediate coverage. Their triangle geometry points to the same typed cache.
Later held shape pointers remain unchanged where sampled, but missing final
shape headers withhold fresh final geometry/flag claims. Another capture is
unnecessary for this selected geometry and attachment case. Distinct sources,
fresh uncaptured later shape fields and contact participation remain separate
requirements; no accepted result yet proves selected-mesh contact participation.
The offline actor reader additionally proves fully registered rigid-static
membership in the Collider's public PhysX scene for the covered headers, and
joins covered later observations to the raw completed native-core scene records.
Missing actor headers and the reverse scene actor array remain unavailable.
Scene membership does not require another capture for the already covered
observations; fresh uncaptured actor fields remain a separate coverage gap.
The empty split-results header array cannot settle contact participation:
normal result fetching dispatches raw reports directly and clears report state
before these completed-step snapshots. Its raw report-core pointer field is
absent from the saved archive, and no captured callback or touching-pair result
repairs that missing phase. Repeating the same observer would not settle contacts.

The observer now records finalized contact headers before dispatch and
cleanup on both native report routes, with raw pair buffers and selected
Collider/shape/actor/source provenance. Retention continues past the final
checkpoint until stop. Offline validation covers the ABI, actual-client disabled
trampolines, removal guards, exception forwarding and later retention; retail
report coverage remains required. The earlier contact-only retail run reached all retained
checkpoints and stopped cleanly, but its contact-finalizer entry census was zero
before selection gating. Its saved archive lacks both the native callback
consumer guard and raw report-core pointer. The reviewed dispatch can bypass
the finalizer on absent callbacks, empty reports or excluded streams, so this
run cannot identify the responsible guard or establish contact absence. Offline
review authenticates scene callback installation and descriptor filter copying,
but the selected filter and pair-notification policy remain unresolved. Named
movement claims establish available capsule/ray/overlap, floor and penetration
query routes with layer/gameplay filtering and position handling. These do not
prove live branch selection or a selected-mesh hit. Do not repeat the same
scenario without a discriminator.

The query observer is validated offline and has an admitted retail session. It preserves
arguments, effective masks/trigger policy and IFix route, bounded returned
buffers, ordinary Collider and ECS identities, post-filter decisions and
position/floor results. Join selected results to Collider/PxShape/source and
step identities without attributing unknown ECS hits to a managed object.
Selected result ABI, native writers and requested-name/cache/caller routes are
authenticated. Live binding additionally requires the original caller and cache
to match the reviewed target; table adjacency does not establish registration.
Buffer getters and hit-to-proxy conversion record consumption, native hit
conversion supplies actor/shape provenance, and the reporting entry guards are
captured alongside the finalizer. The retail session observes bound native
queries, accepted/rejected filters, walkable floor results and blocked movement
with a nonzero request and unchanged logic position. Both ordinary Collider and
ECS identities occur. Its sampled pre-original dispatch guards have a callback
and raw report core but empty pair lists; builder/finalizer entry censuses stay
zero. Cleanup timing and absent callbacks do not explain those sampled guards.
Upstream notification policy and physical solver-contact participation remain
unresolved; query-driven blocking does not require a notification report.

No query conversion joins to the retained light meshes. Saved hit actor/shape
headers are absent, and runtime ECS identities do not establish installed
source identity. Extra original caller sites fall outside the reviewed binding
gate, leaving their result buffers uncaptured. Exact getter/proxy pointer-copy
chains also remain incomplete. Continue offline through ECS creation/ownership
and caller proofs first; do not repeat the same observer merely because selected
reports are zero. A future capture needs a concrete source-identity or caller
coverage discriminator. Do not change notification flags to force a positive
report or interpret missing callbacks as no contact.

Offline ECS recovery now authenticates the packed collider-definition framing
and a named factory byte-array/ordered-Mesh-to-actor creation route. Authored PPtr
targets remain separate from hit ownership. Physics collider ID/version resolves
through a registry to a distinct packed Entity; the covered indexed hit-conversion
path follows actor shape enumeration. The current archive lacks the needed hit-actor userdata
and registry values, so no offline ID/name/position match can complete that join.
The next observer needs bounded query-time userdata/Entity snapshots, source
records from the common native decoder and later owner-binding validation.
Native streaming producers bind entities inline after decoder return, bypassing
the managed `RecordEntity` API; covered producers pass a word count converted
from a byte-length prefix. Preserve both timing and units when adding those
hooks. Existing geometry/attachment proofs and authored-definition decoding do
not need another identical capture.

Stored Streaming collision bodies now join the authenticated marker-17 and ECS
decoder routes, with ordered mesh resource keys and a separate fixed heightmap
resource key. Full-width manifest candidates and selected Bundle main-asset Mesh
PPtrs add offline source evidence. These remain distinct from native resource
map population, `##subasset` selection and live hit ownership. The parameter
reader preserves gameplay-option aliases and the complex-mesh flag exception;
neither a stored flag nor a clear complex bit zero proves runtime activation.
Do not expand the next capture simply to repeat stored framing or cooked
geometry. Its decisive evidence must be the missing query-time userdata,
creation/source key records and subsequent owner binding.

The refactored capture tool now implements those observations: the generic
decoder source/ordered-ID spans, covered Streaming resource resolution and
native object provenance, callback-return owner reads, the explicit
`RecordEntity` route, and query-time actor/shape userdata with repeated versioned
registry-row reads. Physics/query sampling is independent of light-collider
retention. Caller addresses are retained diagnostically while a reviewed native
callee plus its matching live cache admits the result carrier. Run the
`collision` preset after offline native review and compilation, loading the
Dijiang hub followed by outdoor terrain/props to exercise multiple source
families. Live route coverage, successful source/owner joins and solver-contact
participation are still pending a new session; raw capture completion does not
establish those conclusions.

The first source-capable run failed on event transport during scene loading,
before movement coverage. Native read and userdata counters did not report a
gap, but dropped rows and the unpreserved admitted tail prevent complete-session
admission. The observer now uses bounded larger queues, compact batched records,
explicit transport diagnostics and final tail draining. The same source/owner
capture is still required with that correction; do not change native arguments,
notification flags or evidence gates to compensate for queue loss.

The corrected compact-record session now completes without loss and admits
unique decoder/source/owner joins for the captured ECS conversions. Query-time
actor userdata, repeated registry rows and returned physics ID/version close
the packed Entity ownership route; ordinary Collider conversions remain a
separate lane. Same-callback successful resource/object lookups and the serialized
map identify observed ordered mesh inputs by CAB/PathID, with lock-busy inputs
and unobserved lookup routes retained as gaps. The reusable offline audit is
[`collision_runtime_ecs.py`](../scripts/game_data/collision_runtime_ecs.py).

Do not request another capture merely for that already-closed ownership route.
Continue offline through exact returned-shape geometry and stored source
candidates. Native bodies now separate the complex shape at parameter index
zero from positive ordinary actor-shape indices; the corrected candidates explain
the apparent `Stairs` difference from the already-flagged triangle descriptor.
No flag-mutation capture is required for that former audit error. Current
AssetBundle local PPtrs also give observed mesh inputs container paths through
exact CAB/PathID equality; use the runtime source audit's optional `--export-root`
join before requesting asset-selection coverage. Constructor
success and later shape attachment history still need independent proof.
Targeted extraction recovers both collision-only cooked input meshes for the
sampled `Stairs` actor. Under the source pose, its saved face IDs, points and
normals discriminate the ordinary triangle input from the auxiliary mesh.
Retain this as conditional geometric evidence; exact runtime geometry-pointer
identity and pose/attachment history still require their own observation.
Contact reporting remains empty in
the sampled guards: solver contact and notification policy require an independent
consumer/observation discriminator, not an inference from successful queries.

The admitted archive has now been exhaustively checked for returned-shape
geometry field ranges, including windows from other calls. Those bytes are
absent. Nonsentinel face results prove the original successful virtual
geometry-getter/remap path, but not its returned pointer value or concrete
vtable. Repeated userdata does distinguish auxiliary complex shapes from the
ordinary query shape where that pointer is present. Same-completed-core typed
scene reads also join some empty-report guards to the observed public scene;
unentered report builders/finalizers and absent pairs/streams leave solver
participation unresolved. Reusable boundary audit:
[`collision_runtime_evidence_boundary.py`](../scripts/game_data/collision_runtime_evidence_boundary.py).

Further capture for these two exact claims requires additional observations:
the original triangle-geometry getter output inside hit conversion, a live
source-Mesh held-cache/physical-identity comparison at that observation, and
solver contact-constraint preparation/solve provenance before notification
selection or cleanup. Keep body/shape, scene/step and cross-thread causality
explicit. A generated contact manifold alone must remain distinct from a
constraint that actually enters solving. Do not request an unchanged or simply
longer run to repeat already-closed ownership, asset-path or query-consumption
coverage. The expanded observer is implemented and its getter, preparation and
PGS/TGS scalar, static, batched and extended-contact adapters have selected-native
validation. Reviewed declarations and validation live in
[`collision_physics_stage_native.json`](../scripts/game_data/contracts/collision_physics_stage_native.json)
and [`collision_physics_stage_native.py`](../scripts/game_data/collision_physics_stage_native.py).
The expanded capture now proves sampled original getter-to-live-Mesh-cache
pointer identity with repeated CAB/PathID for an ECS query shape. Exact scale
bits and the reviewed ordinary shape ordinal discriminate repeated source slots
conditionally; targeted authenticated extraction supplies the corresponding
collision-only cooked mesh and matching cache counts. Reuse
[`collision_runtime_geometry.py`](../scripts/game_data/collision_runtime_geometry.py)
for this closed sampled identity route. Runtime array equality, actual pose and
continuous attachment history remain separate; the array spans are absent.

Selected contact-preparation and solver hooks have zero original entries in
that capture. This cannot establish contact absence or be attributed to sample
limits. Context pointee headers are absent from the saved archive, leaving
backend selection, awake-body eligibility and task dispatch open. Offline native
tracing now proves separate CPU controller and dynamics-update paths, and the
PGS/TGS zero-active-island early return. The selected CPU controller's named
rigid-body-solver delegate is empty; it cannot replace an original dynamics
update witness. The native facts are owned by
[`collision_solver_dispatch_native.json`](../scripts/game_data/contracts/collision_solver_dispatch_native.json)
and [`collision_solver_dispatch_native.py`](../scripts/game_data/collision_solver_dispatch_native.py).
The updated boundary audit confirms the relevant vtables and island population
fields are absent even in other archived ranges.

Further capture for this idle-route question needs original scene dynamics
update coverage, its actual context/backend, and the original active-island
decision with scene/update/step provenance, followed independently by contact
preparation/solve. A later zero-count checkpoint is not a branch witness. Keep
an explicit unentered-update census so a run with no solver-eligible work can
answer the question without another identical attempt. There is no proved
awake-body target in the existing selected-type export inventory; gameplay
movement or combat alone must not be advertised as guaranteed solver coverage.
The tool now includes those observation points: original scene dynamics entry,
PGS/TGS update entry/return and the saved original island-count operand at the
reviewed flush return site. It retains typed scalar snapshots, entry censuses,
read masks, separate limits and original argument bits. The parent admission
decoder rechecks original callback nesting, stack-site derivation, repeated
operand and same-thread typed scene/core joins. Worker step ownership remains
an explicit gap. Capture readiness has selected-native validation, compiled
forwarding review and a Release build; live route coverage awaits the next run.
Keep an idle Dijiang baseline and stairs/ramps/walls movement, then outdoor
terrain and normal combat/prop interaction in one session, so a zero island
decision can be compared with the game's query-driven movement evidence.
Do not repeat the completed geometry identity, owner or asset-path route merely
to improve a count. Streaming-owned source framing remains strict, while
unbound shared-decoder callers have an unresolved length unit and cannot supply
a definition by borrowing that framing.

The observer freezes solver routes before the original solve, repeats CM and
actor identity afterward, and retains bounded native context bytes. Worker
scene/step ownership, continuous lifetime and positive impulse are still
independent evidence requirements; zero sampled solves cannot establish absence.

Owner: [DynamicStreaming collision recovery](game_data/world_dynamic_streaming.md#offline-boundary-and-next-capture).
Reviewed ABI, source and observation rules:
[collision_capture_native.json](../scripts/game_data/contracts/collision_capture_native.json).
Reviewed cache ownership/layout and saved-data comparison:
[collision_runtime_mesh_native.json](../scripts/game_data/contracts/collision_runtime_mesh_native.json),
[collision_runtime_mesh.py](../scripts/game_data/collision_runtime_mesh.py).
Reviewed Collider current-shape consumers and saved attachment comparison:
[collision_runtime_shape_native.json](../scripts/game_data/contracts/collision_runtime_shape_native.json),
[collision_runtime_shape.py](../scripts/game_data/collision_runtime_shape.py).
Reviewed actor registration, scene/result consumers and saved evidence audit:
[collision_runtime_actor_native.json](../scripts/game_data/contracts/collision_runtime_actor_native.json),
[collision_runtime_actor.py](../scripts/game_data/collision_runtime_actor.py).
Reviewed available character movement/query routes:
[collision_movement_queries.json](../scripts/game_data/contracts/collision_movement_queries.json),
[collision_movement_native.py](../scripts/game_data/collision_movement_native.py).
Reviewed query/result ABI, conditional bindings and saved observation admission:
[collision_query_native.json](../scripts/game_data/contracts/collision_query_native.json),
[collision_query_native.py](../scripts/game_data/collision_query_native.py),
[collision_capture_queries.py](../scripts/game_data/collision_capture_queries.py).
Stored cooked-format reader:
[cooked_collision.py](../scripts/game_data/cooked_collision.py).

For a new distinct source case, retain a continuous session from before scene instantiation through later
completed physics steps. Begin with the selected Dijiang hub resource so its
accepted source identity can be reused. A distinct prefab or scene is a new
case; its missing source or checkpoint is not repaired by another object's
observation. Require the following ordered phases:

- Exact stored Model bytes and source-file identity, grid/UniqueId, element,
  Guid and resource hash; loader request/result and the chosen root/parent.
- After original instantiation returns, enumerate children including inactive
  components. Record Collider and root/Transform/GameObject identities, world
  matrices, active/enabled/convex state and shared Mesh identity. Keep the
  post-parent and post-instantiation matrices as separate observations.
- In one native identity-map scope, retain the runtime Mesh's raw serialized
  filename, file index and PathID, plus its unique frozen-source join. A cloned
  Collider's absent serialized entry is a valid result, not a prefab PathID.
- Preserve native-core manager, scene handle and raw float step, entry/normal
  return linkage, and the exact nested completion call and return. Sample the
  retained objects after the requested later completed-step ordinals, with
  original enrollment time, managed pins and cached native-pointer/instance/
  root identity checks. Record destruction, replacement, busy locks and missing
  epochs explicitly; account for every retained handle at quiescent stop.
- At instantiation and the later checkpoints, retain bounded native
  Collider/Mesh windows, read ranges, region/protection metadata, parent pointer
  edges, timestamps, traversal/read/queue limits and archive hashes. Preserve
  these as opaque bytes until authenticated native consumers establish cache
  ownership and layouts. The admitted selected case has that owning path and
  complete array comparison; a copied float sequence or nearby pointer alone
  cannot establish a PhysX object or a live triangle buffer.
- Before report cleanup, retain finalized header/actor identities and raw shape
  pairs, removal flags, raw event/count fields and readable stream prefixes.
  Recheck any selected side's retained lifetime, native current-shape and actor
  attachment, and fresh source identity. Unknown peer asset identity, skipped
  pairs, newly changed shape candidates and uncaptured stream tails remain gaps.

Accept the selected stored-source identity separately from later state and
cache geometry. Later state requires the normal-return/completion and lifetime
joins. Runtime geometry requires an authenticated owning cache path, bounded
array counts and element widths, and a complete decoded comparison with the
selected stored payload; uncaptured representations remain unknown.
Shape attachment additionally needs the native Collider current-shape consumer,
the concrete PxShape type and that same invocation's geometry-to-cache join.
Preserve missing later shape fields independently from observed held pointers;
do not fill them from a different invocation or retained address alone. Contact
participation needs its own observed pair/shape ownership and result phases,
which the older observer did not implement and the pre-cleanup observer has not
yet observed in retail. If that question is pursued, preserve dispatch guard
coverage and capture reports or authenticated touching interactions before report cleanup, joined to
both actors, their shapes, the source-bound cache and the completed step. Preserve
event state, removed-object flags and available contact data; a report alone
must not be promoted into current touch or solver response. Capture absence of
reported events only under explicit reporting/filter coverage, never from an
empty post-completion header array. Stop after coverage reaches the final
requested checkpoint for every still-live retained object, then require the
shared clean-receipt and stable-file gates. Carry forward each accepted phase
without requesting it again merely because another phase remains open.

## Mission timeline

**Status:** the next useful evidence for handoff chronology and live parameter/
combined-cache behavior requires capture. Additional ordinary callee review can
refine conditional transfers but cannot settle these runtime joins.

Owner: [Story carriers](game_data/story_carriers.md#shared-mission-state-and-condition-connections)
and [Story recovery](webui/story_recovery.md#remaining-gaps).
Reviewed native rules:
[mission_expression_native.json](../scripts/game_data/contracts/mission_expression_native.json),
[mission_shared_native.json](../scripts/game_data/contracts/mission_shared_native.json).
Existing entry observers:
[mission_trace_capture.json](../scripts/game_data/contracts/mission_trace_capture.json).
Entry-only support does not imply that the outcome/intermediate phases below
are implemented by that recipe.

The additional focused observer is prepared in
[mission_state_trace_capture.json](../scripts/game_data/contracts/mission_state_trace_capture.json).
Its versioned GP-only paired ABI records state activation/callback snapshots,
AST parse/evaluation recursion, result setters and selected owning callbacks
with explicit thread, invocation, parent and entry/return identity. Param cells
use the authenticated concrete setter witnesses; the closed EventData layout
and native indirect callback argument are separately proved. The maintained
preparer and offline inspector retain paired-call constraints. The refactored
runtime retains bounded observation and cleanup, while its collector inventories
files without certifying their contents. Use the internal `Capture.ps1` launcher
and named presets; the former batch launcher and `-CheckOnly` path were removed.
This recipe now has a locally analyzed live constant-Param activation in a
guide-labelled combined AST, including resolved-cache updates, nested parent
evaluation and a false AND traversal. It supplies neither a Mission objective
owner nor a subsequent state-event callback. Params are sampled at activation
entry/return, not at every resolver instruction. Nonconstant selection,
constructor/subscription selection, all supplied child snapshots, effective
IFix selection and atomic cache coherence remain additional joins.

For daily interactive/photo routes, the additional
[mission_daily_trace_capture.json](../scripts/game_data/contracts/mission_daily_trace_capture.json)
recipe retains the state/AST observers alongside selected interactive, snapshot,
SNS, script and action entries. Its `mission-daily` preset currently selects
all available MissionRuntimeAsset definitions plus selected supporting context.
The `m1m42` definition stores an AND of five interactive state checks and a
prerequisite chain through an SNS-backed objective; `m1m39` stores a
snapshot-group success condition. Neither definition contains
quest/mission-state predicates, but the observed `m1m46` variant reuses an
`m1m42` display-name key and does store a sibling quest-state conjunction.
Runtime IDs choose the definition. The retained local sequence includes its
parallel sibling handoffs and incoming composite-copy cache update, with no
corresponding Mission-owned AST/state predicate activation. Guide ASTs and
their live Param evidence are a separate owner lane.
Default combined objective setup dispatches only the client child lane and has
no own AST activation. A separate lazy GetResultByProgress path can parse and
evaluate the expression from visited child progress without predicate activation
or the result evaluator's all-child-decided gate. Both maintained recipes now
include a paired ast.GetResultByProgress observer; use its enclosing invocation,
owner fields and useProgress=true node calls to distinguish this lane from
guide activation and incoming objective copies. This addition is prepared
offline, not an observation in the retained daily.
Capture each interactive action, the last-child transition and a successful
photo callback continuously. The launcher retains selected pre-run export bytes
under `source-files/`; this is a bounded subset, not the former all-mission
archive, and export/live-build and omitted-source joins remain independent.
The earlier selected-source session omitted its actual runtime variant's
definition; current-export context is separate and cannot retroactively supply
pre-run bytes. Analyze current path/size inventories with the inspector's
explicit `--local-files` mode; an analysis is not a legacy hash-bound replay.
The current launcher waits for a manually launched client and supplies no
automatic Mission screen backup. Keep a separate screen recording when the
HUD sequence is needed. See the internal capture README for current commands.

### Continuous quest handoff

Start before the last action of a currently available multi-quest route, and
retain one continuous interval through predecessor success, successor new
start and successor activation or its explicit absence. Preserve incoming
quest/mission state packet identity and state, supplied quest-action identity,
restoration flags, objective/condition identity, and any dialogue identities.
Include the screen recording and a clean final receipt. Runtime IDs select the
definition: reused display text and labels do not select daily variants.

Accept only the observed, explicitly owned route and its same-invocation or
same-thread local order. Do not infer server policy, successful returns,
playback ownership or a total mission order from entries. A later restoration
of the successor cannot repair an older unrecorded transition; repairing that
historical interval needs its original evidence or a legitimately replayable
case, not another unrelated recording.

### Live state predicates and combined evaluation

Choose a currently accessible case whose authenticated definition contains a
quest/mission-state predicate, preferably nested in a combined condition. Such
a definition is a capture candidate only: the reviewed default Mission leaf
lane excludes these non-ClientOnly predicates, so their native activation is
not guaranteed. Preserve a consumer/owner join if they execute through another
lane; leave an unhit hook as unobserved.
For mission-owned AST evidence, select a route that actually invokes direct
combined activation or the separate progress predicate. A stored conjunction
of server/state leaves is insufficient. The observed daily's incoming objective
copies and separate quest-state handlers already establish their local order;
repeating that daily alone cannot supply a missing resolver invocation or server
decision rule.

For nonconstant resolution, choose an executing client consumer with an explicit
source family and retain the resolver input/output, selected closed MethodInfo,
condition/Param/context identity and selected provider. Bound-variable sources
need the live bind flag, getter identity and returning delegate value; getter
references need the ActionContext registry/ref-ID lookup and any raw conversion;
path sources need the selected blackboard, cached/resolved PropertyPath and
lookup outcome. Record a failed lookup/default separately from a successful
value. Existing activation snapshots do not contain these provider joins.
Exported current-mission operands in mission-property/server conditions are
source candidates, not guaranteed client resolver activity. No explicit
nonconstant state operand was found in the new exported-source inventory;
omitted JSON selectors do not close construction. Select and prepare the actual
consumer before requesting another run, rather than expecting an unrelated
daily or stored server predicate to exercise the state observer.

For a selected invocation, require:

- Condition receiver/lifetime and owning mission/quest/objective/source path;
  effective native/patch choice and applicable context.
- The actual Param references, typed constant/raw value, source selector,
  reference ID and path at resolution, plus the returned ID, comparator and
  target cached in that same condition. To claim construction, additionally
  retain the selected source bytes, JSON/MemoryPack reader/creator, created or
  reused object identity and before/after fields. A value constructor or stored
  JSON constant by itself cannot identify this join.
- Event subscription identity and completion; initial state query/outcome and
  initial result update; later matching event key, ID and state with its own
  dispatch/invocation linkage. Quest activation binds before its initial result,
  while mission activation sets its initial result before binding. Keep initial
  matches separate from later event-driven matches.
- Child/root/parent identities and cached results, expression/AST association,
  entry/intermediate/return linkage, result writes and callback/parent-evaluation
  nesting. Include every supplied child's decided state, even when unused by
  the expression. Observe mutation/reentrancy or enough paired outcomes to
  establish the bounded interval's quiescence.

Accept live operands, a completed result update or a nested-cache consequence
only with these phase/identity joins and the shared clean-receipt requirements.
The existing entry recipe can establish chronological carriers but cannot
alone close construction, result returns or callback quiescence. Develop and
validate any additional observer offline before requesting a recording.

Authoritative server admission remains a separate question. A received state
sequence records the selected outcome; it does not reveal the selection rule.

## IFix

**Status:** required runtime observations remain unobserved. Retained unrelated
entry profiles do not close these questions.

Owner: [IFix patch and VM evidence](game_data/ifix_patch.md).
Reviewed requirements:
[ifix_runtime_evidence.json](../scripts/game_data/contracts/ifix_runtime_evidence.json).
Native programs and layouts:
[ifix_vm_operands_native.json](../scripts/game_data/contracts/ifix_vm_operands_native.json).

### Reference aliasing: negative instance fields

For each selected `Ldfld` or `Stfld` invocation, capture:

- The raw field operand, resolved field index, receiver, evaluation base and
  selected unmanaged-field address.
- Source and destination Value descriptor addresses and their complete
  12-byte contents before copying.
- Receiver, unmanaged-array/header and computed field-address observations
  across copy and rebase, to establish the stable-storage premises separately
  from managed-array identities.
- The source tag actually read after both copy stores, including the observed
  branch selection.
- On the managed branch, the destination `Value1` rebase write and, for
  `Stfld`, the source `Value1` subsequently reread after that rebase.
- Managed-array identities, lengths and the selected reference before
  assignment/store requests, followed by the destination state after the
  request and the correlated normal return or failure endpoint.

Cover distinct nonoverlapping descriptors, identical Value addresses, partial
overlap changing the post-copy tag guard, a `Stfld` rebase changing the later
source index, and distinct/shared managed arrays. Record only relations actually
observed; an unavailable case remains open.

Accept a sampled alias consequence only when its ordered phases, descriptor
bytes, address stability and array/reference prerequisites are independently
supported. A store request and a completed store are separate observations.

### Generic contexts and results

For each selected `GetAsType` or GenericDelegate bridge invocation, capture:

- The actual ordinary or adjustor entry, incoming arguments and hidden context
  carrier according to that entry's reviewed native ABI.
- The saved incoming context, whether preparation ran, and the effective
  context pointer and selected entry at the actual consuming query.
- For `GetAsType`, the context entry reloaded after optional preparation and
  `GetObject`; for Func bridges, the result-type entry reloaded after `Execute`
  and `GetObject`, selected according to generic input arity. Action bridges
  have preparation observations but no local typed result-entry query.
- Type-query input and returned Type carrier, correlated cast or unbox
  outcome, returned pointer/scalar bits, and readable result-storage provenance.
- The reference selected by `GetObject` before clearing and the physical slot
  after clearing as separate phases.
- For adjustors, the receiver/context before adjustment and the values forwarded
  to the ordinary target, linked to the same invocation.

Cover reference, bool and native-pointer results; prepared/unprepared contexts;
ordinary/adjustor entries; and the same generic code with different runtime
contexts.

Accept raw context bits independently of a type interpretation. Effective
contexts and results require the consuming phase and paired outcome; entry
addresses, stored candidates and printed names do not identify the live closed
type. Byref ambiguity, unsupported layouts, missing phases or failed reads
withhold the corresponding interpretation.

### Closed generic and delegate identity

To claim closed-type selection or delegate construction/dispatch, additionally
capture:

- An authenticated mapping from the actual native runtime context to its method
  definition and generic instantiation.
- Separate class and method generic arguments, including raw type carriers,
  their kinds, arities and byref flags.
- The constructed delegate type, target, managed reflection MethodInfo,
  selected registered wrapper and observed invocation linkage.
- An authenticated connection between managed reflection identity and the
  native hidden context wherever that connection is claimed. These are
  different representations and need their own bridge evidence.

An ordinary shared-code address or a stored MethodSpec alone does not establish
this join. Keep opaque contexts unresolved until their mapping is proved.

### Patch execution lineage

To attribute observed behavior to an installed patch, capture:

- Accepted patch bytes/hash at `LoadInternal`.
- The selected fix record and registered wrapper identity.
- Same-invocation `IsPatched`/`GetPatch` selection and `Execute` entry, with the
  selected VM method and instruction position.

Keep patch-file declarations, wrapper registration and observed execution as
separate facts until this lineage is joined. Alias/context observations alone
do not prove that a declared replacement ran.

## Endminf later portrait refraction and temporal composition

**Status:** later portrait inputs received and independently analysed; no repeat
is requested now. The native provider/collector verdict remains incomplete
because shutdown erased retained CPU scope before report publication. A separate
source-authenticated retained-input scope rechecks the complete original
native/module/loss/payload/chronology joins, and selected original draw/post
replays are exact. Strict readers never substitute this scope. The reporting
bug is corrected and the new runtime passes build and nonlaunching preflight.
The completed first-pre-portrait transaction still describes its own different
effect and post phase.
Local Unity DLSS loaded-module identity is repaired and verified. Lab stage
isolation identifies M28 refraction as the main settled head-edge loss boundary;
the fragment-helper and texture controls did not justify a renderer default fix.
Further retained-byte/source-mesh comparison resolves the final expanded RGBA8
colour packing boundary. The identified M28 mesh renderer now reproduces that
carrier with GPU particles and source clocks preserved; every admitted settled
frame improves. No new capture is required for this correction.
Offline original-program execution also closes a temporal DOF prefilter
transcription gap: exact float32 immediates and native nested accumulation
reproduce the original on the lab's own history and dispatch inputs. Fresh
opening/settled diagnostics agree with their beauty controls. Visual effects
are measured separately and mixed; this does not establish retail dispatch
constants/history or every near-range mode. Retained portrait bone palettes now correspond to consecutive source Animator
updates across the selected body/face/hair/cloth families, including the
transparent cape. Actual opaque lab palettes and current camera preserve that
own correspondence. Most native dark outline writes overlap the lab; complete
movie and effect/temporal history remain separate.
The source-identified smoke material also exposes incorrect lab sampler address
modes. Actual native descriptors now select its material-specific tuple. Original
sampler ablations isolate the mismatch; full-crop and head image results are
  mixed. The source fragment's different final alpha clamp reproduces every
  supplied own output at the observed blend mode zero; other values remain open.
  Original vertex inputs also select centered outline-normal projection and
  native FOV arithmetic. Those corrections preserve recorded source state, with
  very small movie-score regressions and mixed matched-portrait dark writes.
  The existing first pre-portrait packet now permits a bounded source-palette
  comparison: body, face and one opaque cloth family match its first retained
  Animator Tick, while early hair/other cloth application remains unresolved.
  Exact recorded source sampling plus the one-frame UI cloth chain now closes
  early hair palette bounds and original vertex projection. Other cloth and
  world-position precision still fail, and the retained hair crop has no writes;
  the conditional geometry view is not a scored rendering improvement.
  Public lab GPU skin readback also preserves the matched beauty/source control
  and leaves only small original hair position/direction differences. Equal
  current/previous buffers do not prove retail history. Continue offline with
  shader object-origin/radial shadow ownership before another runtime request.

Owner: [lab capture queue](../endfield_reconstruction_lab/docs/capture-queue.md).
Durable rendering interpretation:
[lab rendering boundary](../endfield_reconstruction_lab/docs/rendering-pipeline-and-shadows.md).
Internal observer schemas, preparation and operator steps remain in the
EndfieldCapture checkout. Build with `Build.ps1`, then select a recipe with
`Capture.ps1`. The recorder consumes the supplied native declarations without
producer-side fingerprint, code-window or receipt verification; collection only
inventories files. Required source/native admission remains an independent
recovery-consumer concern and is not established by a successful capture.

Required ordered phases in one own Present:

- Exact body Forward selection after own Character Info Play in the reviewed
  later portrait window, with actor/Animator/cohort identity and original
  geometry, programs, constants, resources and target/depth state.
- Own opaque outline and M28 refraction inputs and before/after outputs.
- Tagged DLAA colour, depth and motion inputs/output, selected token/viewport,
  options/constants, exposure and evaluation entry/return chronology.
- Original post-consumer programs, inputs/state/output and presented SDR bytes,
  with exact linkage to the same body/refraction/temporal Present.

Acceptance requires complete native provider and scoped publications, no losses,
selected-build/module/source identity, complete authenticated payloads and exact
chronology. Original replays must reproduce the retained outputs before visual
stage measurements support a source correction. Early or shifted frames and
missing M28 remain withheld. Internal DLAA history, movie cadence, source-pose
parity, particle birth and renderer ownership are separate claims; an unrelated
active-particle timing bracket is not required for this draw transaction.

The received evidence supports bounded original-input and stage-contribution
analysis. Native provider completion remains withheld. Later radial post is
inactive; DLAA brightens the own selected dark-edge mask on average. The own
M28 output and tagged DLAA input differ across intervening processing, whose
individual producers are not captured by this transaction. The own tagged depth
split shows near head pixels pass exactly; far room pixels change, consistent
with recovered DOF. Full movie pose and internal history remain recovery questions rather than
reasons to repeat this capture automatically.

The latest Endminf offline portrait control carries its own authenticated shader
mip bias. Hair normals and dark outline writes largely agree at the matched
pose/camera. Original body BC5 texture recovery closes a further normal-import
gap: installed and retained bytes agree across eleven mips, and actual Unity
import preserves the material binding. Residual own dark pixels are primarily
cloth; most have a lab dark pixel within one pixel. Fresh movie comparisons
retain their separate source-pose and temporal boundaries.
Original body colour and skin LUT BC7 chains also match the retained own PS
bindings. Exact Unity imports preserve material identity and reduce matched own
opaque colour error a further7.9%, without changing contour coverage. Cloth
outline directions use the authored averaged normal; the correctly selected
basis agrees below0.006 degrees. These joins use existing capture evidence.

The current capture checkout uses Capture.ps1 presets and has removed historical
verifiers. Preserved offline readers recheck old captures without modifying that
checkout or certifying a future run. No old launcher is proposed for another
human capture. Further source initialization and temporal questions remain
separate; review current preset/provider code before asking for a new run.
Durable details remain in the lab's capture queue and rendering topic documents.

Further offline recovery replaces selected cloth colour, normal and material
PNG imports with their exact original compressed chains and preserves bindings.
Matched contours improve. A source-only current-position skin diagnostic further
improves cloth contours using imported vertices/weights and live source bones;
the original GPU matrix blend is checked independently. Neither requires another
human run. Default pre-temporal stages remain exact while final vendor output
has a separate history boundary. Regular complete-sequence reviews now accompany
visual milestones; a diagnostic full review keeps clock gaps explicit rather
than relaxing the exact-cadence gate or asking for an otherwise unnecessary capture.

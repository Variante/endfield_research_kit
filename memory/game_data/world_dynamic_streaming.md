# DynamicStreaming main grids and area records

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** The main `fb_main_*.bytes`, area `FBStreamArea.bytes`
and version `fb_version.bytes` roots have selected-build generated FlatBuffer
accessors; the auxiliary `fb_init`/`fb_streaming` roots have none. Envelopes
and root framing belong to
[`dynamic_streaming.py`](../../scripts/game_data/dynamic_streaming.py). Field
names come from the reviewed [`contracts/`](../../scripts/game_data/contracts/)
and the modules below, whose docstrings hold layouts and proof detail.

## Shared proof pattern

Each native audit gates on the explicit installed `GameAssembly.dll` and
`global-metadata.dat` (plus `UnityPlayer.dll` for UnityPlayer routes),
matches pinned code windows or named body claims, and fails closed on a
missing or mismatched build. Each corpus gate rejoins every dumped file to
the authenticated VFS ledger by path, length and FileDataMd5 before naming a
field. Changing counts, value distributions, scene sets and receipts live in
the generated reports under `reports/animestudio/` (portal join:
`reports/game_data/`). A **direct conditional** route below is a selected
unpatched body: cache hits, failed lookups, other branches and iFix
`IsPatched` wrappers may take other paths, and no route records what ran in
play.

| Module | Owns |
| --- | --- |
| [`dynamic_main_native`](../../scripts/game_data/dynamic_main_native.py) | main `SingleGrid` vector widths; DataMask presence test |
| [`dynamic_data_index_native`](../../scripts/game_data/dynamic_data_index_native.py) | DataIndex layout; grid-local Type/Index partitions |
| [`dynamic_scalar_components_native`](../../scripts/game_data/dynamic_scalar_components_native.py) | scalar and spatial inline component getters, builder field parameters, MissionCondition string-index consumer and current-corpus value census |
| [`dynamic_system_routing_native`](../../scripts/game_data/dynamic_system_routing_native.py) | `EDynamicSceneData` to system route |
| [`dynamic_root_comp_native`](../../scripts/game_data/dynamic_root_comp_native.py) | RootComp layout and partition, authenticated directory-to-instance owner decoder, visible groups and controller, template lookup and match, lifecycle, IdComp branch |
| [`dynamic_resource_comp_native`](../../scripts/game_data/dynamic_resource_comp_native.py) | ResourceComp, ResourceGroupWithStateDesc, cross-grid payloads |
| [`dynamic_resource_state_native`](../../scripts/game_data/dynamic_resource_state_native.py) | selected ResourceGroup LogicState query mask and zero-overlap skip |
| [`dynamic_model_runtime_native`](../../scripts/game_data/dynamic_model_runtime_native.py) | named body claims for stored-transform/grid-matrix calls, instantiated-model parenting and child-collider enable control |
| [`dynamic_model_native`](../../scripts/game_data/dynamic_model_native.py) | complete inline Model fields, current main-file bytes and manifest prefab-path joins; optional declared prefab-root/collider joins |
| [`collision_runtime_mesh`](../../scripts/game_data/collision_runtime_mesh.py), [`collision_runtime_mesh_native`](../../scripts/game_data/collision_runtime_mesh_native.py) | admitted saved-window decoder and native Unity Mesh held-cache/type/count/index-width proof; one source-bound runtime geometry comparison per sample |
| [`collision_runtime_shape`](../../scripts/game_data/collision_runtime_shape.py) | admitted Collider current-shape member, concrete PxShape and same-call source-bound triangle-cache attachment; independent actor/flag fields and missing-window diagnostics |
| [`collision_runtime_actor`](../../scripts/game_data/collision_runtime_actor.py) | typed actor registration and public scene from the same-call windows; raw completed-core scene join and explicit contact-storage coverage, without inferring contact absence from empty report arrays |
| [`collision_movement_native`](../../scripts/game_data/collision_movement_native.py) | replayable named character movement, query, layer-mask and gameplay-filter claims on explicit native inputs; available routes only, without live branch or hit claims |
| [`dynamic_sludge_surf_tile_native`](../../scripts/game_data/dynamic_sludge_surf_tile_native.py) | `SludgeComp.SurfTileIDs`; `PrimitiveIntList` closure; conditional navmesh consumer |
| [`dynamic_visibility_area_join`](../../scripts/game_data/dynamic_visibility_area_join.py), [`dynamic_visibility_state_join`](../../scripts/game_data/dynamic_visibility_state_join.py) | visible-group values to area IDs and MapConfig states |
| [`dynamic_visibility_runtime_native`](../../scripts/game_data/dynamic_visibility_runtime_native.py) | body claims: scene state, conditions, MapConfig and streaming-config load, loader file selection, area dealer and centers, portal assignment, spawn and AOI |
| [`dynamic_streaming_config_join`](../../scripts/game_data/dynamic_streaming_config_join.py) | MapConfig to `StreamingMapConfig` asset and scene roots |
| [`dynamic_main_path_join`](../../scripts/game_data/dynamic_main_path_join.py) | `fb_main` filename to root `UniqueId` |
| [`dynamic_version_native`](../../scripts/game_data/dynamic_version_native.py), [`dynamic_version_id_domain`](../../scripts/game_data/dynamic_version_id_domain.py) | version root and entries; same-scene IdComp join |
| [`dynamic_active_version_native`](../../scripts/game_data/dynamic_active_version_native.py), [`dynamic_version_ban_native`](../../scripts/game_data/dynamic_version_ban_native.py) | branch-version source and parser; ban-set consumer |
| [`dynamic_aux_pair_corpus`](../../scripts/game_data/dynamic_aux_pair_corpus.py), [`dynamic_aux_bridge_native`](../../scripts/game_data/dynamic_aux_bridge_native.py) | auxiliary pair relations and descriptor 21; native path-to-copy route |
| [`dynamic_stream_area_corpus`](../../scripts/game_data/dynamic_stream_area_corpus.py), [`dynamic_stream_area_native`](../../scripts/game_data/dynamic_stream_area_native.py) | area framing; area records, relations, `CheckInArea` |
| [`portal_center_join`](../../scripts/game_data/portal_center_join.py) | portal template and override destination vectors |

## Model instantiation and collider control

[`dynamic_model_native.json`](../../scripts/game_data/contracts/dynamic_model_native.json)
records the selected generated Model layout, nested getter carriers and builder
declarations. Its validator authenticates the explicit installed native pair
and the independent main-vector contract before decoding. The inline record
contains Guid words, Trans position/rotation/scale, LodGridChain, PathHash and
VisibilityInfo. Each transform member carries three float32 axes; do not read
stored Rot as a four-component quaternion. Full nested fields tile the record.
Nonfinite visibility values are stored float32 representations, not a framing
failure: retain their exact bit pattern and special-value class, without
assigning sentinel semantics.

The current-corpus gate rejoins every main file and the manifest by VFS length
and MD5, then resolves unsigned PathHash against native-validated AssetInfo
rows. Repeated identical manifest rows add no association; distinct path/Bundle
rows with one hash remain ambiguous. `--scene-receipt` revalidates an existing
selected scene export, then requires asset path, active logical Bundle and the
AssetBundle container's actual GameObject root before linking its colliders.
The result stores the authored Model transform beside the prefab-local matrix;
it deliberately does not synthesize a live world matrix. Per-build counts and
object rows live in `reports/animestudio/dynamic_model_current_latest.json`.

[`dynamic_model_runtime_claims.json`](../../scripts/game_data/contracts/dynamic_model_runtime_claims.json)
reproves selected method bodies by name on explicit native/metadata inputs.
`DynamicSceneModelSystem._GetModelTransform` contains the named stored
`Pos`/`Rot`/`Scl` getter calls, `DynamicStreamingScene.GetMat`, matrix point
and vector multiplication, and quaternion look-rotation calls. The instantiated
model path calls that transform routine, obtains a root Transform and calls
`Transform.SetParent`. A prefab's stored root-to-collider TRS is therefore only
one part of the placement investigation; a selected grid matrix, parent and
instantiated-prefab identity need their own joins.

`_SetColliderEnable` reads the named collider cache and contains child-component
collection and `Collider.set_enabled` calls. Saved prefab enabled/active flags
are authored state, not a proof of live collider activation. These claims prove
named reads/calls, including the evaluator's bounded owned fragments and
one-helper boundary. They do not prove complete argument dataflow, the branch
that ran, a live grid/parent value, subsequent animation or an IFix patch's
effect. A failed source gate produces no method rows; a failed claim remains
`pendingReview` in a separate report. Current method bodies, hashes and outcomes
are in `reports/animestudio/dynamic_model_runtime_claims_latest.json`.

The named claims also check Model.PathHash reads and
`ResourceManager.InstantiatePrefabAsync` calls in `_DoInitModel`.
`DynamicStreamingScene.GetMat` reads `m_runtimeMapData` and calls its sparse-array
element accessor; `OnAddUniqueId` allocates an id, accesses that array and calls
`Matrix4x4.TRS`. The registration API takes a scene unique-id string, direction,
position and bounds. Its selected runtime matrix and id mapping are not fields
in the stored Model record. These claims establish the source of the remaining
runtime boundary, while preserving their named-call/field-read scope.

### Offline boundary and next capture

Supported cooked geometry, stored prefab hierarchy and authored Model resource
paths can be recovered offline. Static coverage can still be widened to more
prefabs, but it cannot identify which loading/hold/IFix branch ran, which
GameObject was instantiated, the selected registration matrix and parent, or
the enabled/active state after animation and gameplay changes. Those questions
now warrant a bounded live capture.

Capture one source-identified Model in a known scene, carrying its source-file
hash, grid ordinal/UniqueId, element ordinal, Guid words and PathHash. Keep the
following events in one ordered, call-correlated session:

- `OnAddUniqueId` and `GetMat`: registration name, direction, position/bounds,
  runtime id, selected matrix and return status.
- `_DoInitModel` and `_DoInitInstantiateModel`: Model identity, requested prefab
  hash, resource handle/result, instantiated GameObject instance id, selected
  root/parent and resulting transform.
- `_GetModelTransform` and the collider-control route: input stored transform,
  selected scene matrix, returned transform, collider/mesh instance ids and
  enabled/active transitions. Snapshot collider world matrices after parenting
  and after the next physics update, so later changes remain distinguishable.

Use the checked serialized prefab root and Mesh CAB/PathID/raw/cooked hashes as
the offline side of the join. A runtime pointer, display name or reused
instance id alone is insufficient: record the resource/object lifetime and a
loader-to-instance identity bridge. Validate the selected-build ABI and hidden
return carriers before installing hooks, especially Matrix4x4 and
FAssetProxyHandle returns; named-call claims do not validate these carriers.
Do not infer active colliders from the prefab's saved flags or report a failed
load as an instantiated object. The generated current target shortlist belongs
in `reports/assets/collision_live_capture_plan.json`.

The first observer is prepared through
`scripts.game_data.collision_capture_prepare` and the standalone collision
target in `tools/EndfieldCapture/providers/collision/`. It uses EndfieldCapture's existing
prelaunch host and strict MinHook transaction implementation. The reviewed
`collision_capture_native.json` contract proves selected metadata signatures,
by-reference parameters, carrier/field layouts and bounded native bodies.
Preparation preserves the explicit output pointers of `_GetModelTransform`,
the hidden Matrix4x4 and FAssetProxyHandle return carriers, and the public
IL2CPP getter slots in provider order. Callback scopes unwind on either
exception kind, restore the thread-local parent and mark missing returns as
incomplete. The shared host retains process identity and the acknowledged stop
protocol; the collision host requests stop after an attempted attachment even
when it exits through an exception.

The recorder now consumes prepared declarations without comparing installed
file fingerprints or native body windows. Its file inventory is not an evidence
admission report. Keep the selected-build contract and independent recovery
inspector as the source/native admission boundary; existing admitted sessions
retain their earlier evidence and do not need to be recaptured for this refactor.

Start `tools/EndfieldCapture/Capture.ps1 -Preset collision` with the game closed.
Launch manually after `COLLISION WAITING`, then log in or enter **OMV Dijiang /
O.M.V.帝江号 (`base01_lv001`)** only after `COLLISION ARMED`. The target scene
name is checked against LevelDescTable and SpaceshipConst; the selected light
prefab has exact authored Model rows in this hub. Let it load and walk until
every retained live object reaches the final displayed checkpoint and pending
is zero, then type `stop` and keep the game open until saved. The launcher
uses the already built recorder and archives the selected source reports and
raw Model files with the session; it does not seal or verify them.

`scripts.game_data.collision_capture_inspect` authenticates the saved native
inputs, staged runtime, source archives, completion/loss counters and paired
same-thread calls before admitting observations. Exact Model bytes can join a
runtime call to a frozen authored row. Post-setter Unity reads occur on the
original caller and are skipped explicitly off the main thread. Runtime scene
names, matrices, prefab handles, parent pointers and collider/mesh identities
remain separately timed observations. This first pass still does not prove
loader-to-CAB/PathID identity, destruction/reuse, IFix branch selection or the
state at the next physics step; watched element IDs are selection candidates,
not lifetime receipts. Unobserved hooks stay visible in the inspection.

The first admitted Dijiang light-prefab capture establishes a live source join:
selected Model records matched their frozen bytes, the prefab requests used the
same PathHash, and the transform output bits matched authored Pos/Rot/Scl. The
captured component snapshots had a zero root-grid index; no `GetMat` call was
nested under these selected transforms, although that hook was entered elsewhere.
After `SetParent(null, true)` returned, the selected root objects were active and
their queried world matrices were retained as separately timed observations.
The matrix translation differed slightly from the returned position, so keep
both samples rather than replacing one with the other or inventing a cause.
These observations constrain this loading episode; they do not prove every
transform/IFix branch or a serialized collider's live mesh identity.

No `_SetColliderEnable` entry occurred in that capture, and the observed
`Collider.set_enabled` entries were outside selected scopes. An active prefab
root and a stored `enableState` are therefore insufficient to classify its child
colliders. The saved-session inspector now retains component/context fields,
registration bounds, source UniqueId, exact transform comparisons and a named
hook census that distinguishes filtered calls from hooks with no entries.
Numeric load status remains numeric; component snapshots taken inside one
method are not a complete lifecycle receipt. The observer now takes a bounded
child-collider snapshot after selected instantiation. A separately timed
physics-step/lifetime observation and a loader-to-CAB/PathID bridge remain open.
Repeating the same scene walk cannot guarantee that an enable setter will run. Per-session
counts and joined rows belong in the collected inspection and generated
`reports/runtime_capture/collision/` findings.

The child snapshot uses the unique direct `SetParent` root recorded within the
selected instantiation. Its non-generic child-component query includes inactive
descendants and filters components through the native Collider ancestry. The
selected client signatures and entry/return witnesses authenticate that query,
managed Array length/index reads and the public class/type/GC-handle APIs.
Array access uses the checked managed methods, without an assumed array header.
Transient GC handles pin the root, reflected query type, result array and sampled
colliders; they are released on normal or observer-exception exits. No handle
is retained as a cross-frame lifetime claim.

A saved original-return timestamp precedes the child sample interval. The
inspection distinguishes these observer samples from original game calls,
binds summaries/child rows to the same source Model and root, and requires the
reported sample counts and component indices to agree. A completed empty
enumeration is distinct from an off-main-thread skip. Missing/ambiguous roots,
read/query failures and exceeded bounds invalidate capture admission and retain
a bounded `runtime-child-failure.json` diagnostic with the stage and source
record. Synthetic cases prove ordering, inactive/disabled state retention,
original error preservation, stop during instantiation, bounds and transient-pin
cleanup. The admitted retail child-query capture now exercises this path for the
selected Dijiang light models, with completed enumeration and no observer loss
or read failures.

The sampled descendants were active, enabled non-convex MeshColliders. Distinct
collider instances shared one observed runtime mesh, and each child's world
matrix matched its sampled root bit-for-bit after instantiation. The mesh name,
convex state and identity prefab-local matrix agree with the frozen serialized
candidate, whose empty render stream has a recovered cooked triangle payload.
That earlier session established conditional runtime state and candidate
consistency. The later admitted provenance session closes the selected Mesh's
CAB/PathID join. Those provenance-only sessions did not measure the runtime
cache; the admitted memory decoder below now compares it. Preserve the
post-parent and post-instantiation matrices separately: some basis entries
changed between those samples, while the small authored-position versus queried
translation difference remained. Neither difference establishes its cause.
The selected enable setter was still unobserved, so setter coverage is not a
prerequisite for this sampled state. The admitted provenance session reads the
shared runtime Mesh's serialized filename and PathID from the native identity
map. They agree exactly with the authenticated frozen selected Mesh source,
closing that identity gap for the observed instances. The runtime-created
Collider instances have no serialized map entry; do not assign their prefab
Collider's PathID to them. The raw/cooked hashes alone select the stored source.
The separately proved cache path and complete array comparison below establish
observed geometry; physical contact participation remains unobserved.

The reviewed native contract records the PersistentManager instance-ID map,
its concrete vtable, filename vector and identity consumer. The map yields a
serialized-file index and the raw 64-bit PathID; the concrete filename consumer
uses that same index to select a native string. The observer copies both in one
manager critical-section scope. Import-table ownership establishes that the
client uses Windows `EnterCriticalSection`/`LeaveCriticalSection`; it does not
use an SRW lock. The observer uses nonblocking `TryEnterCriticalSection`,
retains a busy-lock gap and retries during later snapshots. Native operand
witnesses authenticate the singleton, vtable and field declarations, while
runtime gates also check the concrete vtable and actual Windows lock bindings.
Bounds, string representation and reader failures retain stage diagnostics.
The observer calls the read-only identity lookup directly: it excludes the
consumer's subsequent file-opening path. No map entry is a valid observation
for a runtime-created collider and cannot be replaced with a name-based join.
Only an observed mesh CAB/PathID may match a unique frozen selected mesh source;
the raw serialized filename and signed/unsigned PathID interpretation remain
available separately. The client’s custom AssetBundle file-ID interface returns
PathIDs without the serialized-file index, so that interface alone cannot prove
a CAB join.

Later snapshots retain pinned managed Collider/root GameObject references,
which keep the wrappers available without proving native Unity object lifetime.
The observer checks cached native pointers, instance IDs and the original
GameObject/Transform identity before admitting another object read. Destruction
or replacement produces a lifetime gap and retires that retained record. It
samples after the first, sixtieth and six-hundredth later completed native
simulation-core calls. The reviewed native manager pointer, scene handle and
float step are forwarded unchanged in their own machine argument slots, and a
native completion function must return from the authenticated simulation-core
call site exactly once before the outer original core returns normally.
Rejected, skipped, reentrant or unwitnessed routes do not
advance the retained object's sample ordinals. A simulation whose entry precedes
enrollment is excluded. These are separately timed reads after the witnessed
completion path. The state reads alone do not measure contact pairs or native
geometry; the independently timed memory windows require their own decoder.
Missing sample epochs remain visible coverage gaps; acknowledged quiescent stop
releases every remaining handle and records the pending count. The saved-session
reader authenticates provenance, completion, source, timing and handle accounting
while continuing to accept the earlier capture schemas.

The admitted provenance session exposed a coverage failure in the earlier
manual-physics selection: the managed `Physics.Simulate_Internal` entry was
unhit while native completion entered outside an admitted outer context. No
later checkpoint was recorded. Additional walking cannot repair that hook
selection. The current observer instead hooks the reviewed UnityPlayer
simulation core itself; stored native caller and managed-icall transfers prove
the manager/scene/step ABI into that shared core. This covers those callers
when they execute that core, without asserting the earlier session's actual
caller addresses or universal physics-route coverage. Its offline ABI,
forwarding, completion and trampoline gates pass. The admitted native-core
session now observes every requested checkpoint for the retained selected
objects, with no lifetime gap, unfinished epoch, loss or handle-accounting gap.

The expanded observer also retains opaque native memory windows rooted at each
sampled Collider and shared Mesh cached pointer, at instantiation and every
requested later checkpoint. It follows plausible aligned pointer values only
through committed private or mapped nonexecutable regions. Window size, scanned
pointer prefix, traversal depth, node count, session bytes and session block
count are bounded by the reviewed contract. A soft time budget is checked
between operations; it cannot bound an individual page fault or thread
preemption. Every recorded child edge must agree with bytes captured in its
parent window. Reads, limits and queue loss stay explicit coverage gaps, while
archive framing, counts, timestamps and receipt hashes are admission gates.
The worker writes the archive outside the game thread. This preserves more
bytes for later offline PhysX investigation without calling cooking functions
or guessing their ABI. These windows can contain neighboring allocations, and
the reads are separately timed: they do not prove allocation extents, a native
type, PhysX ownership, geometry equivalence or contact participation. A missing
or corrupt archive rejects the expanded session; a correctly recorded traversal
limit preserves the separately authenticated state and source observations.
The capture console reports retained-object and checkpoint coverage while the
session is active, so a scene walk can reach the last checkpoint before stop.

The earlier header-only memory session retained native Collider/Mesh headers and a managed
wrapper edge, but every traversal reached the soft time limit before a useful
physics-cache graph was collected. The saved Mesh windows contain the stored
submesh bounds byte sequence; no complete selected cooked payload, decoded
vertex array or triangle-index array occurs contiguously in those windows.
This is a bounded byte comparison, not proof that the client discarded,
recooked or replaced that geometry. The improved traversal filters plausible
pointer values while scanning the parent, then queries page protection only
when processing each distinct candidate immediately before reading it. Limits
and rejected candidates remain explicit. The subsequent native-core session
collected the required cache path and complete arrays despite recorded time
and node limits. A traversal limit does not erase an independently complete,
authenticated range; it leaves uncollected ranges unknown.

### Admitted runtime cache decoding

The reviewed
[`collision_runtime_mesh_native.json`](../../scripts/game_data/contracts/collision_runtime_mesh_native.json)
binds Unity Mesh's held physics-cache member to its native cleanup/release
consumer. The captured pointee has the concrete `PxBVH34TriangleMesh` vtable;
its type-name and vertex/triangle/count/remap getters, index-width selector and
selected word/DWORD readers are authenticated against the selected native
inputs. This is a pointer-bound type and array proof, beyond a name match or
the occurrence of vertex bytes in a neighboring allocation.

[`collision_runtime_mesh.py`](../../scripts/game_data/collision_runtime_mesh.py)
reuses an admitted session only while the frozen profile/runtime/sources,
journal and archive still authenticate. It rechecks archive framing and pointer
edges, reconciles selected cached observations with journal bytes, gates the
new native layout, and requires the raw Mesh and embedded cooked payload hashes
to select one frozen CAB/PathID identity. Each read uses one complete captured
window from the same invocation and Mesh root; partial windows are never
stitched, and contradicting overlaps withhold the affected comparison. Read
addresses, hashes and independent timestamps remain available.

For the selected Dijiang light Mesh, every admitted instantiation and later
checkpoint sample has identical complete vertex float bits and triangle index
values/order to the stored cooked payload. The runtime uses word indices where
the stored stream uses byte indices, and DWORD face remaps where the stored
stream uses byte remaps. These are distinct representations of the same
decoded values. Pointer-bound edge bytes and BV4 slab bytes also agree over
their complete stored extents; the runtime node count matches the stored
slot count. This auxiliary comparison does not decode a complete runtime BV4
traversal or optional material/adjacency layouts.

The source identity-map lock was busy at an intermediate checkpoint. Those
samples explicitly reuse the initial mapped Mesh identity conditionally,
through the admitted retained object, unchanged Mesh pointer/instance ID and
root/lifetime identity. They do not claim a fresh CAB/PathID read. Later direct
mapped reads agree. The shared cache and decoded geometry remain unchanged
across sampled epochs while the final child world matrices change in their
horizontal basis entries; translations remain unchanged. Preserve geometry
and placement separately, without assigning the matrix change a cause.

The selected source, cache geometry and later-state requirements in the
[runtime-capture backlog](../runtime_capture_requirements.md#cooked-collision-and-live-mesh-state)
are accepted. Another capture is unnecessary for this case's mesh equivalence.
This result is conditional on this source and these separately timed samples;
it does not prove allocation extents, an atomic cache snapshot, a Collider's
`PxShape` attachment by itself, contact participation, other meshes or unobserved
physics routes. The separate attachment reader below supplies that additional
owning path. Generated comparison inventories and the validated source-local
collision OBJ belong under `reports/runtime_capture/collision/` or the saved
session's `collected/` directory.

### Collider current-shape attachment

The reviewed
[`collision_runtime_shape_native.json`](../../scripts/game_data/contracts/collision_runtime_shape_native.json)
establishes the Collider's current-shape member through both an actor getter
consumer and the MeshCollider vtable's physics cleanup path. The cleanup passes
the same receiver into the detach helper, consumes that member through the
bound `PxShape.getActor` slot, and clears it on the reviewed normal branch.
The concrete shape vtable, type-name getter, triangle geometry getter and
flag getter are authenticated against the selected native inputs. These are
native consumer relationships; the capture does not observe cleanup executing.

[`collision_runtime_shape.py`](../../scripts/game_data/collision_runtime_shape.py)
recomputes the admitted source-bound Mesh comparison, then reads the native
Collider root, its current-shape pointer, concrete shape type and triangle
geometry pointer from that invocation's Collider windows. The shape's triangle
Mesh equals the separately typed Mesh-held cache from the same invocation.
This proves a Collider-to-PxShape-to-cooked-source join for the selected samples;
it does not rely on nearby vertex bytes, an anonymous pointer or a name match.
The PhysX geometry/flag buffered-state branches are followed independently;
missing buffers never fall back to inline data. All interpreted field offsets,
state masks, virtual slots and code anchors live in the reviewed contract.

For the selected Dijiang light case, each instantiated Collider has its own
concrete shape and all shapes refer to the same decoded triangle cache. The
full join is captured after instantiation and at the first completed-physics
checkpoint. An intermediate checkpoint has only partial shape-window coverage;
the final checkpoint captures the Collider members but no shape headers. Each
held member is unchanged across its observed checkpoints. This preserves a
sampled pointer observation, without promoting it into a fresh later geometry
or flag read, or a continuous shape lifetime proof.

Captured shape flags configure simulation and scene query, with trigger clear;
the native actor getter also yields a non-null association. Neither establishes
actor scene membership, an actual collision pair, or a contact result. The
windows and roots are independently timed, so the same-call join remains
conditional rather than an atomic scene snapshot. Another capture is unnecessary
to establish this selected case's attachment. Fresh final shape fields, distinct
source cases and contact participation remain separate questions. Generated
per-call/epoch coverage belongs under `reports/runtime_capture/collision/` or
the session's `collected/` directory.

### Actor scene membership and contact evidence

[`collision_runtime_actor_native.json`](../../scripts/game_data/contracts/collision_runtime_actor_native.json)
authenticates the rigid-static vtable/type name, the specialized static actor's
buffering subobject and registration-state consumer, and the conversion from
the buffering scene to the public PhysX scene. The generic actor scene getter
checks the same registration policy, but its actor-offset table lives in
unbacked BSS. The reader uses the specialized native offset operand; it does
not substitute PE zero-fill or an assumed runtime value for that generic table.

[`collision_runtime_actor.py`](../../scripts/game_data/collision_runtime_actor.py)
recomputes the source-bound shape/cache comparison and admits each actor only
from its own invocation's Collider windows. `in_scene` establishes sampled
registration; `insert_pending` establishes API membership with pending insertion
and cannot establish completed registration. `not_in_scene` and `remove_pending`
withhold API membership even when a stored scene pointer remains non-null.
These state meanings follow the [PhysX buffering control-state contract](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/physx/src/buffering/ScbBase.h),
with offsets and state extraction separately authenticated on the selected
native build.

For the selected light Mesh, the available typed actor headers establish fully
registered rigid-static actors in a common public scene. The scene also equals
the one reached through each Collider's Unity physics-scene wrapper. At covered
completed-step checkpoints, the reader joins that wrapper to raw simulation
parent/completion records, authenticates the completion caller and ordering,
and uses the native core's bound scene `fetchResults` dispatch. Missing later
actor headers stay unavailable; neither an earlier actor observation nor a held
shape address fills them. The reverse scene actor array is outside the saved
windows, so its contents remain unobserved. Membership is conditional on these
separately timed reads, not an atomic snapshot or continuous registration proof.

Contact participation remains unresolved after this offline audit. The saved
scene contains an empty split-results contact-header array, but that array is
constructed lazily by `fetchResultsStart`; normal `fetchResults` instead
dispatches the raw report actor pairs directly. The reviewed native normal path
then resets the report stream and report actor-pair count before the completed
step snapshot. The [PhysX scene implementation](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/simulationcontroller/src/ScScene.cpp)
and [report-pair cleanup](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/simulationcontroller/src/ScNPhaseCore.cpp)
explain why empty report storage cannot prove that no contact occurred.

The raw report-core pointer field and reverse actor-array fields have no complete
window anywhere in the admitted archive. No recorded contact callback, decoded
pair with these actors/shapes, or authenticated current touching interaction
supplies the missing result. Additional reinterpretation of the same archive
cannot recover those uncaptured bytes or earlier report phases. If actual
participation is required, the useful future evidence is an actor/shape-bound
report or touching-interaction observation before report cleanup, including event
state and contact data; another identical post-completion opaque-window capture
would not settle it. A contact report is also distinct from solver response or
a current physical touch, which need their own result semantics.

The maintained observer now hooks the native contact-header finalizer used by
both normal direct dispatch and split-result header construction. Its five
Windows x64 arguments, closed native body, header writes, pair stride and both
callers are authenticated in the capture contract. It copies the finalized
header and bounded raw pairs after the writer returns, before the caller can
dispatch or clear them. Callback notification/filter settings are left as the
game configured them, so a quiet report hook still cannot establish no contact.

Each report retains both native actor and shape pointer values, removal flags,
and raw event/count/stream fields. A selected side additionally requires rooted
managed Collider/root identities, unchanged native pointers and instance IDs,
the typed current Collider shape, and that typed shape's actor matching the
header side. A per-step candidate index reduces observer work; the binding is
checked again at report time. A shape newly attached inside the step may lack a
selected-side binding and remains an unbound report, rather than receiving an
inferred asset identity. Fresh serialized Mesh identity joins the frozen source
independently; an unmapped cloned Collider or unknown peer CAB remains explicit.

Raw pair field names beyond the natively anchored stride/removal field follow
the matching public PhysX declaration and remain conditional pending selected
native consumer validation. Stream windows are preserved as bounded opaque
bytes for later decoding. Removed sides are never followed.
Contact byte streams can be unaligned even when their pointer fields and shape
objects are aligned. The newer window archive permits those report-buffer
addresses while retaining the original alignment rules for object traversal
and older archives.
Captures prioritize
transient streams and live shape/actor headers, limit unrelated pair samples,
and report bounds, skipped samples and missing windows. Selected Collider
attachment windows use a narrow traversal instead of repeating a broad graph.
The objects stay retained after the final requested physics checkpoint and are
released at a lifetime gap or quiescent stop, allowing later movement to produce
contact evidence. A clean stop accounts for every handle separately from
checkpoint coverage. Offline ABI/trampoline and synthetic forwarding tests do
not establish retail activation, notification delivery, solver response, or
decoded contact-point semantics. The admitted retail session using this observer
has a clean enable/disable receipt, retained checkpoint coverage through stop,
and normal native core/completion records, but no contact-finalizer hook entries.
The entry census increments before thread, selected-object and caller admission;
zero entries therefore cannot be explained by a failed selected-side asset join
or those admission filters. The receipt is still not a positive execution witness
for the contact hook itself.

The pinned `dispatch_contact_callbacks` window tests its native callback consumer
before processing reports, bypasses an empty raw actor-pair set, and skips a null
or excluded-state stream before calling the finalizer. The split-header builder
also checks stream state before that call. Neither the callback-consumer pointer
nor the raw report-core pointer has a complete saved window in this session.
Thus the archive cannot distinguish these bypasses, prove contact absence, or
settle character query-based movement. An identical observer/scenario supplies
no targeted discriminator.

The actor contract also authenticates the complete native scene constructor and
callback setter, including their split instruction windows. The constructor
passes its descriptor's callback slot to that setter and copies the descriptor's
filter slots into the scene. The setter writes the same callback-consumer field
tested by normal report dispatch. This closes the configuration route, but the
actual callback value and selected filter function remain unobserved. It does
not identify the game's notification policy. The
[PhysX pair flags](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/include/PxFiltering.h)
separate solve/detect flags from notification flags, and
[shape interaction reporting](https://github.com/NVIDIAGameWorks/PhysX/blob/4.1/physx/source/simulationcontroller/src/ScShapeInteraction.cpp)
requires a report-enabled pair. A shape's simulation/query configuration alone
cannot establish notification delivery. The selected game's pair-flag producer
and its live pair configuration remain unresolved.

This session separately preserves typed Collider/shape/held-cache pointer joins
and simulation/query configuration in covered epochs. Full geometry equality
cannot be repeated because the same-call vertex buffers are missing, and fresh
actor membership is unavailable because its headers are missing. Those gaps do
not revoke the earlier session's accepted geometry/attachment/membership proofs.
The maintained comparators classify an upstream missing-cache window as
unavailable, retain independently readable scene evidence, and surface bounded
sample failures when an upstream comparison is rejected. Missing bytes are not
a mismatch and must never be repaired from another invocation's windows.

Changing actor/epoch counts, native validation receipts and per-read coverage
belong in `reports/runtime_capture/collision/`. The shared
[capture backlog](../runtime_capture_requirements.md#cooked-collision-and-live-mesh-state)
preserves the accepted membership phase separately from the contact requirement.

### Character movement query boundary

[`collision_movement_queries.json`](../../scripts/game_data/contracts/collision_movement_queries.json)
records named body claims, re-proved by `collision_movement_native` instead of
carrying addresses forward across builds. Its complete method set is required:
missing or mismatched selected native inputs or a failed claim withhold all
admitted methods and preserve the failed check. The current selected bodies
validate the following **direct conditional** routes:

- `TryMoveCapsule` reaches `CharacterCollisionSweep` and a logic-position update;
  the sweep calls `MovePhysQuery.CapsuleCastAll`, reads its hit buffer and applies
  `_CheckIfColliderValidForCollisions`.
- Ground movement reaches `MoveAlongFloor` and capsule movement. Air movement
  reaches capsule movement and impact handling. Floor handling reaches sphere
  sweeps, walkability checks and floor-result postprocessing.
- Penetration handling obtains collider-proxy position/rotation and reaches
  `PhysHelper.ComputeCapsulePenetration`. Ray and overlap routes also expose
  returned buffers and character filtering.
- Collidable and overlap mask getters read the configured base and ignored
  masks. The candidate filter reads collider layers and gameplay options.
  These checks establish reads and calls, not their live values or exact option
  semantics.

These routes can affect character movement through query results independently
of solver contact notifications. Their existence supplies a concrete alternative
to interpreting walking or jumping as evidence that the report finalizer must
execute. The admitted query capture now observes original movement invocations,
returned native hits, accepted/rejected gameplay filters and floor results.
Some nonzero requested moves return a hit while leaving the logic position
unchanged. Same-owner full-proxy value joins connect covered returned hits,
accepted filters and movement output; an exact pointer-copy chain remains a
separate stronger witness. This proves sampled query-driven blocking, while
selected-Mesh provenance and unobserved IFix dispatch branches remain unresolved.

The native query review identifies both ordinary Collider identity and ECS
identity routes in `RaycastHit.get_colliderProxy` and
`ECSColliderResultProxy.get_layer`; resolving only a managed Collider is
insufficient. The capsule-overlap lookup names an ECS proxy result array, while
capsule/sphere cast lookups name hit arrays. Internal-call lookup literals name
the requested API, not the live cached function pointer. A paired native query
table candidate has complete array framing, but its registration route is not
proved and no binding is admitted from adjacency alone.

[`collision_query_native.json`](../../scripts/game_data/contracts/collision_query_native.json)
now authenticates the selected argument/result ABI, native result writers and
requested-name/resolver/cache/caller routes. Metadata value widths agree with
the native array-copy loops; the array-length export supplies the checked header
field. The observer admits native result interpretation only at a reviewed
original caller whose live cache contains the exact reviewed target. Other
callers/cache values remain diagnostics. This conditional gate supplies the
missing live binding witness without inferring registration from table adjacency.

The observer records actual query arguments, masks, trigger mode, returned counts
and bounded cast/ray/ECS-overlap buffers. Buffer getters and the hidden-return
hit-to-proxy conversion preserve consumption witnesses. Character filters retain
their Boolean return, input/output proxy, movement receiver and base/ignored
masks, plus the layer and option reads made inside the original filter. The
option helper takes its proxy by reference, so mutations remain visible. Exact
pointer/byte joins and value-only or ambiguous matches remain distinct.

Native hit conversion retains the original PhysX actor and shape. Selected
bindings recheck rooted Collider/root lifetime, typed current shape and actor,
obtain fresh shared-Mesh identity and CAB/PathID provenance, and retain narrow
Collider/shape/actor windows. Query-result joins require unique byte agreement,
excluding UV fields that a later native stage may fill. The reported Collider
identity and retained physical-shape owner remain separate observations. Recent
completed-core references and retained source-step ordinals are recorded without
claiming atomic scene state or continuous membership. An actor or instance ID
alone never supplies a query-shape join. Overlap proxies have no shape field;
missing native shape conversions remain unresolved.

Dispatch/header-builder entry diagnostics copy the callback consumer, raw pair
pointer/count and bounded stream null/excluded-state checks before the original
can clear them. Dispatch's second byte argument is forwarded unchanged. The
finalizer retains its native simulation ancestry through these new scopes.
Original arguments, return values, output carriers, exceptions and last-error
state are preserved; game notification settings remain unchanged. Entry censuses,
sampling intervals, bounds and unbound calls are explicit.

[`collision_query_native.py`](../../scripts/game_data/collision_query_native.py)
and [`collision_capture_queries.py`](../../scripts/game_data/collision_capture_queries.py)
validate the native declarations and saved observations. Offline checks cover
disabled client trampolines, synthetic forwarding/stop/exception/bound cases and
saved-session admission. Retail execution now supplies live caller/cache
matches, both ordinary Collider and ECS hit identities, actual filter returns
and sampled blocking. Covered queries retain a preceding completed native-core
reference, not an atomic scene-membership observation. Executed original call
sites provide route witnesses; an owner without admitted descendant queries
does not establish IFix selection or query absence. Earlier accepted geometry,
attachment and membership proofs do not require recapture.

The pre-original dispatch samples resolve the reporting guard: the callback
consumer and raw report core are present, but the raw pair count is zero and
the pair pointer null. Neither builder nor finalizer executes in the saved
entry census. This identifies empty reports at the sampled dispatch boundary;
it does not prove absent physical touch or identify the upstream notification
policy. There are no saved streams whose exclusion state could explain these
samples. Query-driven movement blocking is observed independently of reports.

No query conversion joins to the retained light colliders. Hit actor/shape
headers are absent from the saved windows, and ephemeral ECS IDs/component
indices do not supply installed CAB/PathID identity. Floor and blocking results
therefore retain their distinct runtime identities. Fresh source-bound final
checkpoint cache/attachment/membership reads also remain unavailable where the
same-call cache header was clipped; earlier geometry proofs are not substituted.
The geometry reader accepts the newer query inspection while preserving all
frozen-source, journal, runtime, receipt-loss and archive checks.

Additional indirect native caller sites execute beyond the reviewed binding
set. Their diagnostic returns and cache values are saved, but rejected binding
sites have no captured input/result buffers. Offline caller review cannot
recreate those bytes. Converter/array/consumer field changes and incomplete
getter/proxy pointer chains remain explicit; do not replace exact byte joins
with actor-only source attribution. The reusable ABI/writer declarations stay
in the reviewed query contract; per-session counts, caller inventories and
blocking witnesses belong in `reports/runtime_capture/collision/`. The next
offline target is ECS collider creation/ownership and additional caller routes,
before considering a capture that measures their missing source joins.

### ECS collision definitions and ownership

[`ecs_collision.py`](../../scripts/game_data/ecs_collision.py) reads the packed
collider byte-array family, separately from the cooked PhysX mesh codec. Its
[`native contract`](../../scripts/game_data/contracts/ecs_collision_native.json)
authenticates the selected common header, primitive/mesh/multi/terrain cases,
descriptor-group strides, native hit userdata consumers and direct native
decoder callers. The reader requires bounded counts, an ordered mesh-list count
consistent with mesh-bearing groups and exact EOF. Those are defensive stored
projection checks; the native consumer's own bounds checks are weaker. Anonymous
flag/mesh words and capsule dimension lanes retain their raw values. A disabled
ordinary attachment gate still consumes its stored record and mesh slot. The
optional complex-mesh record has a different packed flag profile and no such
bit-zero gate; it must not be classified as disabled from that bit.

The exported `FactoryUnitConfigAsset` source family has `colliderData` and
`colliderMeshes` fields. The named
[`ownership claims`](../../scripts/game_data/contracts/ecs_collision_ownership.json)
re-prove a `CreateBusRender` route that reads both fields, supplies ordered Mesh
instance IDs to decoding, obtains a returned actor's physics ID/version and
records an owning entity. MonoScript CAB/PathID, exported PPtr declarations and
per-output freshness can authenticate these authored inputs. The current stored
factory definitions tile through EOF and preserve their declared mesh targets;
they do not establish this route's retail execution or Dijiang hit ownership.

The hit's ECS ID/version and owning Entity are **different identity lanes**.
The native hit writer reads physics ID/version from masked actor userdata. A
distinct resolver uses a versioned physics registry and reads the packed Entity
stored elsewhere in that userdata. Metadata authenticates the Entity's packed
global-index/version pair separately from the collider proxy and collider
component. Native getter candidate labels remain conditional on registration;
paired name/function table framing alone is not a live binding proof. In the
covered indexed hit-conversion path, the component index follows the actor's
shape enumeration, not a
Streaming component mask or an Entity type index. Inactive records, invalid mesh
resolution and later shape changes prevent equating stored record order with
live shape order.

Direct native producer bodies also call the decoder and write the packed Entity
inline **after** its return. Hooking only the managed `RecordEntity` API would
miss these writes. Covered byte-length-prefixed producers pass the payload after
the prefix and shift its byte length into a word count. A future decoder hook
must respect that unit; a decoder-return snapshot is too early to assert the
subsequent owner binding. Keep creation/source observations separate from later
query-time actor/shape/userdata validation.

The admitted query session lacks hit-actor userdata and the relevant registry
snapshot. Offline definitions, returned physics IDs, world positions and names
cannot restore that mutable join. Per-session and per-export inventories stay
under `reports/runtime_capture/collision/`. The remaining useful capture must
measure query-time userdata/Entity identity and native creation/source records,
including native producers, rather than repeat the unchanged light-only observer.

#### Streaming source definitions and parameter interpretation

[`streaming/collision_native.py`](../../scripts/game_data/streaming/collision_native.py)
joins independently authenticated marker-17 and ECS decoder roles by the same
entry, extent and code bytes. This gives the anonymous marker-17 bodies a
collision-definition interpretation without guessing from their lengths.
[`streaming/collision_corpus.py`](../../scripts/game_data/streaming/collision_corpus.py)
replays the current root directory, VFS file hashes, full table-local keys,
counted body framing and native-selected descriptor layouts. Default callback
compatibility is conditional: it is not a receipt of runtime root pairing,
callback registration, resource load or scene activation.

The reviewed
[`Streaming collision contract`](../../scripts/game_data/contracts/streaming_collision_native.json)
records the native mesh-count keys, ordered resource keys and fixed terrain
resource key. Their helpers consume a sixteen-byte resource span. The first
qword is the full lookup key; the following words remain explicit. Consumed
width does not prove whole target extent. Terrain has a separate resource input
passed to the decoder's heightmap argument, not an ordered Mesh slot. Runtime
cache contents and actual texture/height samples are separate from that stored
declaration.

The descriptor's first parameter word is forwarded as gameplay options and its
second as tag configuration. The surface value is packed in the flag word.
The ordinary records shift by two; the optional complex record shifts by one
and its entry does not test a packed attachment bit. Covered native userdata
construction and getter operands, plus selected metadata enum defaults, are
authenticated by the ECS contract. Keep the words and unknown bits, and retain
every enum alias: `AirWall` and `IgnoreFromBakeNavmesh` share a value, so a bit
alone cannot choose their consumer context. The earlier provisional
`surfaceWord`/`optionWord` labels are superseded; the current projection exposes
`gameplayOptionsWord`, `tagConfigWord` and `surfaceTypeByte`. Capsule dimensions,
high flag bits, tag lookup and native dimension normalization remain separate
from raw stored framing.

[`streaming/collision_assets.py`](../../scripts/game_data/streaming/collision_assets.py)
authenticates an existing plaintext manifest against the current VFS row and
native manifest layout before joining full-width keys. This is an exact numeric
join to authored path/Bundle candidates, not proof of the resource namespace or
selected runtime object. Preserve ambiguous candidates. The selected Bundle
gate can then authenticate raw container main-asset PPtrs and supported cooked
Mesh buffers; [`collision_mesh_candidates.py`](../../scripts/game_data/streaming/collision_mesh_candidates.py)
keeps this stored relation distinct from `##subasset` selection. Neither names
nor preload membership choose a Mesh. A fresh selected witness includes
collision-only Meshes with no render vertices but complete cooked geometry,
and no ordinary MeshCollider component in those Bundles. Streaming ECS sources
therefore explain another legitimate empty-OBJ case.

The maintained collision observer now samples the generic native decoder on
every route, independently of the retained light-collider selection. Its length
argument counts words, so the bounded source archive multiplies it by four and
stores exact terminal chunks rather than inferred allocation windows. Ordered
mesh IDs are archived separately. Covered Streaming callbacks provide one
same-thread parent for resource resolution and decoder calls, then sample the
created actor after the callback returns, when the inline Entity write has
finished. The managed/native `RecordEntity` route is observed separately.

Query conversion samples both actor and shape tagged userdata and the actor's
versioned registry row. Repeat userdata, registry-header and row reads expose
drift; they do not make the observation atomic. A runtime source join requires
matching actor, userdata address, physics ID/version, registry validation and
causal order. A covered callback additionally supplies the declared Entity for
comparison with the later userdata. An uncaptured callback may supply a decoder
identity candidate with the owning Entity measured later at query time; keep
that weaker boundary explicit. Resource-object lookup observations preserve the
handle, returned native object, decoder mesh ID and serialized instance-ID map
result; resource-key, ordered-mesh and CAB/PathID joins remain separate.

The reviewed query target and its live cached binding establish the native
callee ABI for copying its results. The current observer preserves caller
addresses as diagnostics without restricting that typed callee to one reviewed
managed call site. Physics/query sampling no longer depends on an unrelated
light collider being retained. Bounds, absent or drifting userdata, unresolved
resource candidates and missing report callbacks remain visible gaps. These
observations are designed to close source/owner joins; they do not promise
solver contacts when reporting is disabled or follows an unobserved route.

The selected declarations and offline reader are owned by
[`collision_ecs_capture_native.json`](../../scripts/game_data/contracts/collision_ecs_capture_native.json),
[`collision_ecs_capture_native.py`](../../scripts/game_data/collision_ecs_capture_native.py)
and [`collision_capture_ecs.py`](../../scripts/game_data/collision_capture_ecs.py).
Capture-project implementation follows its refactored `AGENTS.md`: one build
graph and output directory, guarded observations, unchanged original calls,
worker initialization and callback quiescence. Live execution remains a
separate user-run capture after offline native review and compilation.

Scene-loading source callbacks can overflow the event transport even while
native reads and hook forwarding succeed. The first source-capable session
reached that boundary before movement-query coverage; its failed completion
cannot be admitted as a complete collision session. Zero initial console
coverage is not the final receipt census. Keep transport drops, unreadable
memory, abandoned originals and identity gaps distinct when diagnosing it.

The current observer uses a larger bounded event queue, worker-time queue
allocation, direct JSON appends and batched writes. Default-value omission is
lossless under the declared event format; the recovery reader restores only
documented defaults and never fills missing required identity/argument fields.
Queue capacity, peak occupancy, full-queue drops and bounded-retry contention
are separate diagnostics. Health failure preserves admitted records during
quiescence and final drain, rather than labeling the writer failed and
discarding the tail. A failed session remains failed even if its retained
records contain successful source/owner observations. Size projections over
saved records establish format equivalence, not live writer throughput.

The subsequent compact-record session completes without transport or native-read
loss and closes the versioned runtime ownership route for its admitted ECS hit
conversions. Same-callback decoder inputs, actor userdata after the source
callback's inline Entity write, and query-time repeated userdata/registry rows
agree on the actor, physics ID/version and owning packed Entity. The returned
hit's physics ID/version agrees as well. Ordinary Collider results have no ECS
identity to resolve; their missing ECS-registry checks are not transport loss or
an unreadable-memory failure. Keep the Collider and ECS result lanes distinct.

The source audit strictly decodes complete captured definition spans and their
ordered mesh IDs on the reviewed Streaming producer routes. An unbound decoder
caller does not inherit the Streaming length argument's word units: a managed
wrapper forwards that argument unchanged, and the shared decoder only checks a
minimum before replacing it. Such calls retain raw argument and span evidence
as `unbound_decoder_input`; they do not supply a framing projection. Owned
definitions still require exact EOF, and failures identify the decoder,
producer, expected span and captured source hash. Resource resolution and object lookup records in the same
original callback can join a successful resource handle to the actual decoder
input ID and the serialized instance-ID map's CAB/PathID. Repeated observations
must agree; no name, position, manifest suffix or cross-frame ID lookup chooses
an input. Map-lock contention and source routes without observed lookup records
remain explicit gaps. The reusable audit is
[`collision_runtime_ecs.py`](../../scripts/game_data/collision_runtime_ecs.py).
Cached capture consumers expand the current compact format before validating
native-memory framing; omission never repairs missing required record identity.

This establishes the owning Entity and source definition of sampled ECS hits,
and observed physical identities for the actor's mesh-input set. It does not
automatically establish which input supplies the geometry of the returned
PxShape. Native constructor and parameter-lookup bodies establish two index
domains: the optional complex mesh is stored separately in masked actor userdata
and read at parameter index zero; positive indices enumerate the actor's
ordinary shapes starting at one. The hit writer compares the returned shape
against that same actor enumeration. Positive descriptor candidates therefore
exclude the complex record, as well as records whose ordinary attachment gate
is false. The reviewed declarations and exact unwind-family membership live in
[`collision_shape_index_native.json`](../../scripts/game_data/contracts/collision_shape_index_native.json),
authenticated by
[`collision_shape_index_native.py`](../../scripts/game_data/collision_shape_index_native.py).

The earlier apparent `Stairs` augmentation compared a positive shape index with
the separate complex descriptor. The following ordinary triangle descriptor
already carries `Stairs`, and the corrected candidates agree with every sampled
ECS hit's option, tag and surface tuple in this session. This removes that
claimed mutation gap; it does not prove constructor success, skipped records,
later attachment/removal, shape reordering or exact hit geometry. Preserve both
raw source records and observed userdata rather than treating equal parameters
as an exact geometry join.

Observed input identities can also join current exported AssetBundle containers
through exact CAB and unsigned PathID equality with a local PPtr. The optional
`--export-root` path in the runtime source audit uses the maintained export
freshness guard and verifies each selected document's stored hash. The reusable
join lives in
[`collision_runtime_asset_inputs.py`](../../scripts/game_data/collision_runtime_asset_inputs.py).
Container aliases remain explicit; external-file PPtrs do not join by PathID
alone. This gives physical inputs asset paths without choosing by an FBX name or
manifest subasset suffix. A container pointer by itself neither proves the
target Unity class nor decodes its raw/cooked geometry.

A targeted current Bundle extraction for the sampled `Stairs` actor identifies
both ordered inputs as collision-only Unity Mesh objects with no render
vertices and complete cooked CPU BV4 triangle payloads. The ordinary input's
stored face-remap, transformed triangles and normals explain the sampled hit
positions; the auxiliary complex input's corresponding faces do not. This is
conditional on the source pose and stored triangle mesh still describing the
queried shape. The reusable numerical comparison is
[`collision_geometry_evidence.py`](../../scripts/game_data/collision_geometry_evidence.py),
which retains remap aliases, plane distance, normal agreement and barycentric
coordinates without turning tolerances into an attachment claim. Selected
Bundle authentication stays owned by
[`unity_scene_corpus.py`](../../scripts/game_data/unity_scene_corpus.py), and
complete payload decoding by
[`cooked_collision.py`](../../scripts/game_data/cooked_collision.py).
This gives positive stored geometry evidence for render-empty assets and
discriminates these two inputs, while a live geometry-pointer join and later
attachment history remain unresolved.

The earlier archive's exact address-range audit distinguishes absent geometry
fields from failed decoding. None of the returned query shapes has an archived
vtable, geometry selection or triangle-cache pointer at its native address,
including separately timed windows.
The observer's hit-conversion geometry graph is restricted to matching retained
light colliders, and no saved hit matches that selection. Its broader ECS
userdata snapshots therefore close ownership while leaving geometry fields
uncopied. Repeated ECS userdata does preserve the
auxiliary complex-shape pointer for applicable actors; it differs from the
sampled ordinary query shape. This reinforces the index-domain distinction but
does not expose either shape's geometry pointer. The hit writer's nonsentinel
face result additionally witnesses its successful virtual geometry-getter and
face-remap consumer path. It proves that the original took that path, without
recovering the returned pointer value or admitting a concrete getter vtable
from an unobserved header. A sentinel result leaves that path ambiguous.

Typed scene reads after a completed core can join the Unity wrapper, public
PxScene and internal scene to a preceding report guard under the same original
core. Guards from another core, another scene or after the reads never supply
that join. Missing scene windows remain gaps instead of borrowing another
checkpoint. This establishes that some empty-report guards belong to the
observed scene, but no report pair or contact stream is saved. Entry censuses
also distinguish unentered builders/finalizers from sampled dispatch guards.
Neither that route census nor an empty notification report proves absent
touching pairs or solver participation. These conclusions are reproduced by
[`collision_runtime_evidence_boundary.py`](../../scripts/game_data/collision_runtime_evidence_boundary.py),
which rechecks admitted bytes, native field gates and cached query/ECS values.

That earlier capture reaches a missing-observation boundary for these exact
runtime claims. The smallest geometry observation is the output of the game's own
triangle-geometry getter inside hit conversion, joined to the current source
Mesh cache and repeated physical identity. The selected getter's native body
already establishes a shape/output-pointer Boolean ABI and its inline/buffered
copy paths in
[`collision_runtime_shape_native.json`](../../scripts/game_data/contracts/collision_runtime_shape_native.json).
Observing that existing call avoids issuing a game query. Solver participation
needs a native contact-constraint preparation/solve witness with body/shape and
scene/step provenance, independently of notification configuration. A longer
recording with the earlier outputs cannot supply either missing value.

The expanded observer now copies the original triangle-getter's consumed
output fields, excluding unwritten padding, inside its observed hit conversion.
Source resource lookups enroll native Mesh objects with their decoder actor and
version. Query-time joins repeat the native Mesh vtable, instance ID, held-cache
pointer and serialized CAB/PathID, then compare that pointer to the getter's
actual output. Busy maps, expired objects, changed identity and unmatched inputs
remain explicit gaps. This is sampled identity evidence, without a claim of
continuous lifetime or an atomic snapshot.

Solver capture independently observes contact preparation and original contact
solve entry/return for regular and temporal solver paths, including batched and
temporal extended contacts. It preserves descriptors, contact-manager bytes,
body state and bounded native context/constraint windows. Preparation replaces
the descriptor's contact-manager pointer with a constraint pointer; the solve
observer freezes a matching descriptor/body/writeback route before forwarding
the original, then rechecks CM provenance and versioned actor identity afterward.
The CM shape-core/API conversion remains a typed candidate: no untyped
subtraction is promoted to a PxShape. Owning scene/step on worker threads,
continuous descriptor lifetime and positive impulse remain separate joins.
An observed contact solver call can establish sampled solver participation even
when notification reports are empty; a prepared manifold alone cannot.

These adapters are recorded in
[`collision_physics_stage_native.json`](../../scripts/game_data/contracts/collision_physics_stage_native.json),
validated by [`collision_physics_stage_native.py`](../../scripts/game_data/collision_physics_stage_native.py),
and decoded by [`collision_capture_stages.py`](../../scripts/game_data/collision_capture_stages.py).
Preparation gates the selected native inputs, complete unwind families, concrete
getter vtable slot, solver dispatch tables and native call operands. Passing
validation and compilation establish the selected adapters; their live route
coverage is evaluated independently below.

The expanded capture closes sampled runtime geometry-pointer identity for an
ECS query shape. The original getter's triangle pointer equals a live, typed
Unity Mesh object's held triangle-cache pointer, with repeated native instance
identity and serialized CAB/PathID before and after observation. Repeated
source slots alias the same Mesh; the getter's exact scale bits and the reviewed
positive shape-index domain select the same ordinary triangle descriptor. This
descriptor selection is conditional on constructor/attachment history; actual
current collider pose and continuous lifetime are not recovered by the join.
The reusable audit is
[`collision_runtime_geometry.py`](../../scripts/game_data/collision_runtime_geometry.py).

A targeted authenticated extraction of that exact CAB/PathID yields a
collision-only Unity Mesh with zero render vertices and a complete cooked CPU
BV4 triangle payload. Its vertex and triangle counts agree with the live typed
cache header. This directly associates a render-empty asset with geometry used
by the original query and explains why its OBJ is empty. Runtime vertex/index
arrays lie outside the archived cache window, so their bytewise equality with
the cooked payload remains unavailable. Count agreement and pointer identity
must not silently replace that missing comparison.

All selected regular and temporal contact-preparation/solve entry censuses are
zero in the expanded capture. These are original hook-entry counters, not just
bounded sample counts, so exhausted getter/source budgets do not explain the
unentered solver routes. Empty notification guards still establish neither
absent contacts nor solver participation. Saved scene windows contain candidate
context pointers but no pointee headers, even across other captured ranges;
the active backend, awake-body eligibility and worker dispatch remain unresolved.

Offline native tracing now separates the named rigid-body solver task from the
actual CPU dynamics update. The selected CPU simulation-controller factory
installs an empty return in that task's delegated vtable slot. The independently
stored dynamics context receives the scene's update call through its own virtual
slot; the reviewed constructor selects regular PGS or temporal TGS context
factories from the solver-type descriptor. A task name alone therefore must not
choose a solver hook or prove that the dynamics update ran.

Both reviewed CPU update bodies copy the accurate island simulation's active
island count and return before solver-task allocation when that count is zero.
Their ordinary body, kinematic, articulation, contact-manager and constraint
counts are separate fields. The complete update/factory unwind families,
constructor selection operands, concrete vtable slots and branch windows are
recorded in
[`collision_solver_dispatch_native.json`](../../scripts/game_data/contracts/collision_solver_dispatch_native.json),
loaded by
[`collision_solver_dispatch_native.py`](../../scripts/game_data/collision_solver_dispatch_native.py).
This proves the selected native dispatch and eligibility conditions; it does not
identify which backend or branch the saved game executed.

The reusable observation-boundary audit now reads these context members and
population fields only through the same checkpoint's typed scene graph. It also
censuses other archived address ranges without borrowing their bytes. All
required context vtables and population fields for the sampled scene are absent
from this capture.
Even an observed zero population at a later checkpoint would remain distinct
from the original update's copied branch operand. Successful character queries
and query blocking do not imply awake dynamic islands or solver constraints.

For the idle-solver question, this archive now reaches an observation boundary:
another capture must distinguish an unentered dynamics update, its actual
backend, the original zero-island decision and later contact preparation/solve.
Scene, original update and worker/step provenance must accompany those samples.
Merely enlarging generic pointer traversal or taking later checkpoints cannot
establish the original branch. The existing Unity store and object index cover
selected exported types; their lack of Rigidbody documents does not establish
absence from the installed game or identify a guaranteed awake-body scene.

The expanded observer now captures original scene dynamics entry, both CPU
update implementations and the selected list-flush thunk used to reset their
thread contexts. At the reviewed original update return site it copies the
already-saved active-island count from the caller's stack, then repeats the
value after forwarding the flush unchanged. This is the original comparison
operand, rather than an island count read later from the manager. Normal update
return and unchanged operand select the proved zero/nonzero gate path; passing
the island gate still does not prove a contact constraint or solve.

The update adapters forward every positional argument, including the stack
float, and preserve original returns and LastError. Bounded before/after scalar
snapshots retain native scene, held context, backend vtable, island manager,
thread-pool pointer and population read masks. The original scene/update nesting
supplies scene provenance. A same-thread physics core is joined only through
its typed completed public-scene projection; prior completions and worker
timestamps do not repair an absent step join. Sampling, unreadable fields,
unbound updates and exhausted budgets have independent counters. The reusable
decoder is
[`collision_capture_dispatch.py`](../../scripts/game_data/collision_capture_dispatch.py),
integrated with immutable session admission and the observation-boundary audit.
Native ABI, operand, branch, import and complete-function validation plus a
Release build establish readiness for another capture; they do not certify live
route coverage before that run.

The captured pre-dispatch reporting guards still contain empty reports. Native
query participation and filter decisions are positive collision evidence;
solver-contact participation and notification policy remain separate. This
successful session supplies substantial offline source and ownership work, so
an identical follow-up capture is not required to repeat those joins.

Current inventories and receipts live in `reports/animestudio/` and
`reports/runtime_capture/collision/`; changing counts are not durable format
facts. The root gate now authenticates the VFS audit's catalog/build fingerprints
before scanning and again afterward. Referenced bytes passing their MD5 does
not make a stale catalog audit current, and an exporter fingerprint is not the
game build. Re-audit instead of changing an input-set token.

This recovery closes stored definition framing and source-key declarations;
the corrected capture also supplies the previously missing sampled hit-actor
userdata, registry state and native source/creation observations. It closes
versioned ECS ownership and observed input selection, including current
AssetBundle container paths. Returned-shape geometry and solver-contact
participation still need independent observations. Widening the stored Mesh
catalog improves geometry coverage without supplying the absent shape geometry
pointer or later attachment history.

## Main grids

- **Vector extent (exact).** Selected accessor and builder widths bound every
  current grid vector count word and body without overlap. The shared reader
  now also bounds root/grid table objects, both root vectors, shared vtables
  and complete `TotalStr` UTF-8 strings including their count and NUL byte,
  rejecting partial overlap or an alias between different allocation kinds.
  Exact shared vtable/string extents are counted once. Every uncovered range,
  including the physical tail, stays explicitly recorded as a residual; the
  authenticated current main corpus has only zero-filled residuals. This is
  allocation extent, not a padding proof or nested-record field closure.
  Positive `Desc` table targets still need a reader; the current empty vector
  supplies no target evidence. `DataMask` stays a raw `UInt64`.
- **Filename (exact).** Every current `fb_main` filename decodes to its own
  root `UniqueId` under the selected `GetPath` packed-ID rule (low byte, next
  byte, one high nibble). Which ID the game requests is open.
- **DataIndex (structural).** Every valid `DataIndex.Grid` equals its
  containing `SingleGrid.UniqueId` (not always the file root's), and for each
  observed `Type` the `Index` values partition the same-named vector exactly.
  Where counts alone are ambiguous the native enum and accessor names decide;
  every observed Type has a nonzero named system route, distinct for the
  count-only rivals.
- **RootComp (structural, plus direct conditional consumer).** RootComp
  `Comps` groups tile each grid's DataIndex directory, and each entity type's
  ordered child Types equal its `comps` list in the exported
  `DynamicSceneTemplates` asset. Natively, `RootComp.Type` keys the typed
  template dictionary that `OnInit` fills from `TEMPLATE_PATH`; grid
  load, reload and enter reach `_ParseLoad`, which walks DataIndex entries
  (bounded by the template's `comps`, not stored `Comps.Num`), routes each
  Type to its system and can call `RegisterEntity`. The IdComp branch reads
  `UniqueId` and rejoins routing. The public
  `decode_authenticated_root_components` decoder authenticates current raw
  bytes before rechecking main framing, directory target bounds, group
  tiling and the fresh authored template signatures. It returns each
  checked directory reference with its source-local grid, component-vector
  and instance ordinals, and the owning RootComp ordinal and typed entity
  label. This closes the authored `RootComp.Comps` -> directory `DataIndex`
  -> component instance join. It does not assign indirectly grouped
  children or demonstrate that the authored entity exists in play.
- **ResourceComp (structural).** Its five groups partition their same-grid
  vectors; each resource descriptor's inner group partitions `Model`,
  `Effect` or `Ecs` targets across grids and files, resolved by scene path
  plus grid ID. The descriptor's state, level and factory scalars have exact
  offsets. A selected LogicState query consumer is authenticated below;
  the other scalars' runtime use remains open.
- **`PrimitiveIntList` closure (structural).** RootComp visibility,
  ResourceGroup visibility and Sludge `SurfTileIDs` spans are disjoint and
  tile each grid's `PrimitiveIntList` exactly. `SurfTileIDs` values are
  nonzero stored tile IDs. Their selected conditional navmesh consumer is
  authenticated separately from the stored partition.

## Scalar and spatial inline components

`dynamic_scalar_components_native` closes the stored layouts of
`MissionCondition`, `ActivityCondition`, `MapVarControlComp`, `PoiControlComp`,
`TreeRootComp`, `DecorationRootComp`, `ConveyorBeltComp` and
`ConveyorBeltBoxComp` (**exact selected layout**). Each generated getter's
metadata return type and native position read establishes its field type
and byte offset. The generated constructor's named field parameters,
record width and alignment agree with the main vector contract. Complete
main allocation framing and authenticated VFS path/length/MD5 joins run
before the corpus census; a different or missing native build produces no
layout.

The same contract also closes `Vector3`, `SeatComp`, `FactoryBlockComp`,
`SceneGridInfo`, `ExtraSceneComp`, `NavModifyArea`, `Bounds`, `ConveyorPath`,
`WaterPipeComp`, `InteractiveStateComp`, `GlobalVarControlComp` and
`SettlementControlComp`. Selected `Vector3` getter fast paths
read named `Single` fields `X`, `Y` and `Z` at byte offsets zero, four and
eight; the constructor names those same three fields and declares their
inline width. Typed nested getters pass the containing record's position
plus a proved offset to checked carrier initializers, which retain the
ByteBuffer and return a `Vector3` carrier. Their constructor's flattened
parameters independently match the named axes. This establishes stored
`SeatComp.Pos`/`Rot`, factory and scene-grid `Center`, and extra-scene
`MinPos`/`MaxPos`/`CurrentPos`; scalar `Radius`, `Len`, `Direction`, seat
keys and the byte Boolean `RaiseLevelEvent` retain their declared types.
The same carrier proof covers the additional named position, rotation,
scale and bounds fields. Conveyor paths retain the generated names
`WorldStartPoint`, `WorldEndPoint` and `WorldCenter`; a stored name alone
does not prove the live transform used by their consumer. Water-pipe
angles, delays, heights and interactive IDs, and interactive/global/settlement
control scalars retain their declared types. These are authored spatial
and control fields, without world-space, parent-transform, rotation-unit,
radius-unit, target-table, operator-enum or live occupancy claims.

Keep representation separate from meaning. `MissionCondition.IsQuest` and
`IsSame` are stored `Int32`, while `MapVarControlComp.ControlLoad` and the
conveyor entry/exit fields are byte-sized native Booleans. Map variable
`CompareValue` is signed `Int64`; `CompareType`, `MapKey`, `MapId` and the
four `Extra` fields stay signed integers with no inferred operator, target
or sentinel meaning. `TreeRootComp.NormalModel` is signed `Int64`, distinct
from the conveyors' unsigned group IDs. A getter name ending in `Id` or
`Tid` does not establish an external table key or rule out a string-vector
index. Consumers must prove those joins before labels are projected.

`MissionCondition.Id` now has that independent consumer proof (**direct
selected unpatched path**). `RegisterEntityCaredCondition` retains the
containing `FBDynamicSceneChunkData` carrier and passes the generated `Id`
getter's signed integer result to `DynamicSceneChunkStrExt.GetStrSpan`.
That method selects root field `TotalStr`, bounds the signed index, reads
its four-byte string uoffset and byte length, and returns the stored span.
Index zero is an ordinary string slot: it can contain a quest key, not an
absence sentinel. Negative and out-of-range indices return an empty span
on this selected path; the census reports that fallback separately from a
resolved authored empty string. All current authored condition indices
resolve within their own containing root. The returned span is passed to
`DynamicSceneRuntimeStringManager.GetStrKey`; an allocated runtime key is
not the stored index and is not established by this offline join.

The census keeps the original integer beside its resolved authored text.
Mission and quest keys may support a definition-level UI link after the
matching published definition is checked, but this does not establish that
the condition ran, passed or activated an entity. Other component IDs have
no equivalent target proof yet.

The current corpus has no authored `ActivityCondition`,
`DecorationRootComp` or `Bounds` examples, so their generated layouts do not establish
usage. Unassigned internal bytes in tree, conveyor and map-variable
records are zero in the authenticated current corpus; they remain reported
gaps, not a runtime padding or allocator proof. Counts, distributions,
bounded record samples and source MD5s belong in
`reports/animestudio/dynamic_scalar_components_native_latest.{json,md}`.
Enum meanings, control-ID targets, evaluated conditions and live activation
remain unresolved.

`decode_authenticated_main` lets a caller reuse existing exported raw
bytes after the explicit selected-native layout gate and current VFS
receipt gate. It checks the receipt's length and MD5 before complete main
framing and field decoding; the census also records each file's SHA256.
The public result retains source-relative grid and component ordinals,
original scalar values and separate proved string references, with nested
vectors represented by named axes. A component's entity or group owner is
not established by its position in a vector; direct directory references
can acquire an authored RootComp association only through the independent
root decoder and its current template gate. These associations retain
their directory ordinal, rather than treating vector order as entity order.
Raw `Vector3`, `NavModifyArea`, condition and path children have no owner
projection unless a specific checked DataGroup join establishes it.
Corpus and report receipts
must describe the current native inputs and current bytes before a Data
view projects them; bounded report samples are not a substitute for the
authenticated decoder.

The next runtime witness for this branch is a single selected scene/grid
load or reload: record the selected MapConfig and streaming configuration,
the requested `fb_main` path and accepted bytes, the grid UniqueId,
RootComp position and matched template component list, then the actual
DataIndex/system route and `RegisterEntity` call. Record whether the
selected iFix path is active. A condition-controlled example additionally
needs the stored TotalStr key, evaluated condition result and selected
state/area list at that call. This would test the conditional native path
and authored owner join against a live entity; offline directory or string
membership cannot supply that observation. Indirect DataGroup ownership
remains a separate static join rather than a reason to require a capture.

## ResourceGroup state query

`dynamic_resource_state_native` authenticates the registered
`DynamicSceneResourceGroupSystem._FillTargetStateGroupSet` unpatched body
(**direct conditional**). Its `FBDynamicSceneResourceGroupWithStateDesc`
`get_LogicState` call returns a checked `UInt32`, which the caller tests
against its named incoming `UInt32 mask` parameter. The native frame is
checked against entry RSP so this is the supplied mask rather than a
similarly shaped local. Zero bit intersection branches past the subsequent
`Group` getter to the loop advance: the selected query includes a group only
when `(LogicState & mask) != 0`. This is a bit-intersection filter, not numeric
equality; zero LogicState does not pass this particular query.

The reviewed contract pins the selected native inputs and complete caller
main-body window. The validator also authenticates the generated resource
layout, caller identity and full signature, both direct getter targets,
getter-return-to-test handoff, argument location and zero-overlap branch.
A missing or mismatched input or changed body produces no rule and preserves
an existing receipt. Focused tests cover wrong argument slots, comparison or
branch substitutions, getter targets, loop target and native gate failure.
The generated audit belongs under
`reports/dynamic_streaming/ifix_parallel/`; the reusable proof is the tracked
[`dynamic_resource_state_native.json`](../../scripts/game_data/contracts/dynamic_resource_state_native.json)
and its validator.

This selected query does not establish the loading or activation predicate
of every resource consumer. The anonymous descriptor-source helper's owner
join, live selected scene/grid/group, insertion ownership and iFix routes
remain outside this scalar gate. `SceneState`, `LevelNum` and `FactoryIndex`
need their own authenticated consumers before receiving runtime semantics.

## Sludge surface tile consumer

`dynamic_sludge_surf_tile_native` authenticates the selected unpatched
`DynamicSceneSludgeSystem._GetSludgeSurfTileIDs` path (**direct conditional**).
The original generated getter and inlined collector return the same
`SurfTileIDs` group position with the same ByteBuffer carrier. Checked group
`Index`/`Num` accessors select grid-local `PrimitiveIntList` entries. Each
iteration rejects a negative index, an index at or above the generated
vector length, and a zero or negative Int32 value. Positive Int32 values
are sign-extended to UInt64, so only the positive Int32 range is retained.
The indexed accessor clone shares the registered generated accessor's
vtable slot, vector helper, stride and selected little-endian Int32 read;
the length accessor is itself registered.

The output is the supplied `List<UInt64>`, cleared before the selected loop.
Its static `Add` companion is joined through the bounded MethodSpec and
class-instantiation tables, separately from the inline insertion helper.
That helper and the registered generic candidate agree on the list size
field, qword insertion stride and resize target. This closes the selected
insertion relationship without treating shared code or a static companion
as a live MethodInfo; the resize helper implementation remains open.

`_AreSurfTilesLoaded` passes each retained UInt64 ID to the registered
`NavMeshChunkManager.IsSurfaceLoaded` method. A false result returns false
immediately; a null, empty or exhausted selected list path returns true.
`_TryApplyNavMeshState` passes the same local collector output to this check
and reaches `_ApplyNavAndMaybeUnbind` on the selected empty-list or
load-check-true branch. This establishes **conditional navmesh use**, not
active Sludge state, an observed tile load, or a successful state mutation.
Live grid/component selection, patch routes, deferred callbacks and
physical/rendering effects remain unresolved.

A runtime receipt must correlate the caller's global ID/state, selected
scene/file identity and grid ID, Sludge wrapper/group `Index`/`Num`, produced
UInt64 IDs, each `IsSurfaceLoaded` result, the aggregate load-check result,
and the reached apply or deferred callback under one bounded thread/call
lineage. It must include the exact selected native build and loss/overflow
status. A graphics/audio-only session or a method-name hit cannot establish
that join; an observation profile needs these specific call/data receipts
before a capture is useful for Sludge recovery.

## Visibility and scene state

The nested `VisibleStateGroup`/`VisibleAreaGroup` spans address the grid's
`PrimitiveIntList`. `SceneVisibilityControllerBase.Register` reads each value
through that vector slot for the group chosen by the typed state or area
controller: a **direct conditional consumer**, not a name match. The stored
values join scene-locally (**stored cross-file relations**): every
`VisibleAreaGroup` value is in the same scene's `FBStreamArea.TotalAreas`
(including zero; spaceship-cabin main files have no area file), and every
`VisibleStateGroup` value is an index in the scene's `MapConfig.sceneStates`,
where index zero is a named state.

Those state indices have a named native source. `BaseGameScene` calculates a
mask and index list from the MapConfig conditions (or sets one state by
name) and hands the list through `DynamicStreamingScene.SyncSceneStates` to
the entity and resource systems' state controllers; area changes reach their
area controllers through `OnAreaChanged`. Conditions dispatch to quest,
mission, current-map variable and client-global variable leaves and to
`And`/`Or` trees; variable leaves compare as `Single` with an absolute
tolerance near `1e-5`, and a missing variable returns false. The MapConfig
comes from `DataManager.MapConfigTable` (`Data/Json/MapConfig/<id>.json`)
through normal and seamless loading. In the current export (observed; no
tracked gate rechecks it) every `LevelConfig.mapIdStr` names a MapConfig
whose own `mapIdStr` equals its file stem. Evaluated conditions, the active
state list, and whether a stored RootComp group is registered in play are open.

## Scene to DynamicStreaming files

Every `MapConfig.streamingMapConfigPath` resolves to one exported
`StreamingMapConfig` MonoBehaviour by container, source file and PathID, the
class coming from the original object index (many-to-one; unreferenced
assets stay as unselected candidates). Natively, `GameScene._ExtractSceneConfig`
loads that asset into the typed `BaseGameScene.streamingMapConfig`, and its
`mapSceneName` reaches `DynamicStreamingScene.InitScene`, which builds the
scene base path for `DynamicDataLoader.SetBasePath` (`fb_main`, `fb_init`,
`fb_streaming` templates) and `DynamicSceneVersionBanSet.LoadFromBasePath`
(`fb_version`). The typed chunk loader reads through
`VirtualFileSystem.ReadFileByLowIO` and checks chunk version fields. These
are **direct conditional file-selection and read routes**, not receipts that
a file was requested or accepted. The authored `streamingDataPathRoot`
(`Data/Streaming/...`) is a separate path family from the DynamicStreaming
`Scene` files; the link is `mapSceneName` plus the initializer. One-sided
scene sets stay in the join report and do not show a failed load.

## Version roots and the ban set

- **Layout (exact, direct).** `fb_version` is `Entries`, `Major`, `Minor`;
  each 16-byte entry is `UInt64 Id`, `Int32 Version` and alignment. The
  selected-width reader closes every current file through EOF.
- **Id domain (structural).** Every populated `Entry.Id` occurs as an indexed
  `IdComp.UniqueId` in the same scene's main grids; the entries are a subset,
  never a grid `UniqueId`, and the `map01` control has no overlap.
- **Active version source (direct, conditional).** The enter-game login
  response (`Proto.MSG_B1`, message ID `1`) reaches
  `PlayerInfoSystem.SyncBranchVersion`, which stores string field `f14_` as
  `m_branchVersion`; `_ResolveActiveVersion` parses it with
  `GlobalOptions._ParseVersion` (`v<major>d<minor>` with optional further
  `d<phase>` segments). Active phase defaults to a full-phase sentinel and
  changes only when a parsed output is nonzero, so a matched two-component
  value with a nonzero part sets phase zero while `v0d0` keeps the sentinel.
- **Ban consumer (direct, conditional).** `LoadFromBasePath` exits when the
  phase is at least the sentinel or a path, file, root or major/minor check
  fails; otherwise entries with `Version > activePhase` add their `Id` to
  `m_banned`, and `IsEntityVersionBanned(globalId)` returns
  `m_banned.Contains(globalId)` only when `m_needCheck` is set.

## Auxiliary `fb_init`/`fb_streaming` pairs

- **Stored pairing (exact).** Every current file has its counterpart. Root
  fields 0-1 and vector bodies 2-3 agree, field 4 agrees on its checked prefix
  only, field-5 tables agree in count and shape, and init field 7 and
  streaming field 6 are the complementary nonempty positions.
- **ID, descriptor and blob groups (exact).** Streaming field-6 rows carry
  four-byte IDs; init field-7 rows carry eight-byte descriptors (signed 16-bit
  ID and stride, zero reserved word) and a nested byte blob. Stride times the
  group ID count gives descriptor-major segments that tile the blob, and the
  grouped IDs partition the root field-3 IDs as a multiset.
- **Descriptor 21 (exact stored projection).** One stride-64 descriptor per
  group holds the root field-5 names clipped to 63 bytes: a stored name
  column, not a lossless copy, and not a named runtime component.
- **Native route (direct, conditional).** The ECS load transition passes both
  paths through `AllocateRuntimeChunk_Injected` to a native object that
  stores them separately, requests two streams in one indexed record,
  resolves both ready buffers to FlatBuffer roots, reads init field 7 and
  streaming field 6 at one ordinal, and hands IDs, descriptors and blob to a
  builder that copies stride-times-count bytes per descriptor into per-ID
  destinations. It shares the lookup and stream helpers checked by the IV
  path contract ([`world_irradiance.md`](world_irradiance.md)); the provider
  and VFS file a request chose are open.

## `FBStreamArea` records and area selection

- **Framing (exact).** With the corrected `Int32` widths the six vector count
  words and bodies tile the root tail through EOF; root bounds are inline.
- **Records and relations (direct, structural).** Area, trigger, point and
  bounds records have native offsets. In the populated file, area ranges
  partition `AreaVisibleGroups`, trigger ranges partition `Points`, every
  point lies in its trigger's XY bounds and those bounds are exactly the point
  extrema. The other current files are empty with an inverted-sentinel box.
- **Selection (direct, conditional).** `GameSceneAreaDealer.InitData` reads
  the scene's area file through VFS into a typed root, builds a trigger quad
  tree and seeds its active set from `RootVisible`. `FlushStreamingArea`
  enables areas against that set: nonzero areas go to
  `StreamingSceneV2.SetArea_Injected` and `DynamicStreamingScene.OnAreaChanged`;
  zero takes a default-area layer path. Refreshes query the tree around the
  stored streaming center (plus an optional extra-load sub-center) and apply
  the stored visibility slices.
- **Predicate (direct).** `CheckInArea` applies inclusive X/Z and height
  bounds, then an even-odd ray test over the trigger's closed point ring,
  comparing stored `Coord.Y` with query Z.
- **Centers (direct conditional, stored).** A regular load's center is the
  `pos` that `SquadManager.ServerTeleportSquad` passes to `LoadAtPos`; a
  seamless load's is the portal component's `tpPosition`. Placed portals
  store nondefault `tp_position` overrides, distinct from their world
  position, which the selected `ApplyProperties` route writes into
  `tpPosition`. The placed interactive reaches the allocator through a spawn
  pipeline entered from AOI interest (no dependency group; grid force-load
  and range-exit callers).

## Evidence boundary

Tiers are marked inline above. **Exact** covers VFS identity, vector and
tail framing, the filename-to-root ID and the auxiliary pair bytes;
**direct** covers selected accessors and the conditional native routes;
partitions, the template match and cross-file joins are **structural only**.
**Unresolved:** other nested main fields, positive table-reference targets and
allocator-backed proof for the zero-filled residual ranges; `DataMask`;
auxiliary descriptors other than 21 and whole-root closure; `Entry.Id`
meaning beyond the IdComp join; resource activation conditions and state,
level and factory consumers beyond the selected LogicState query; live Sludge tile
selection and navmesh effects; live login bytes, branch-version value,
registration execution
and repeated-segment captures; and every live selection: MapConfig,
streaming and template asset loads, grid and area activation, evaluated
conditions, version phase, ban results and ban-set reuse, auxiliary file and
provider, the squad teleport `pos` source, portal values and AOI/spawn
execution, polygon-edge equality, patch state. `RootVisible` is an authored
initial-set input, not a runtime receipt.

## Eliminated readings

Each was tested and refused; the module docstring has the reasoning.

| Refused reading | Module |
| --- | --- |
| a universal four-byte main vector width | `dynamic_main_native` |
| `DataMask` bits as present or nonempty vector flags, any base shift | `dynamic_main_native` |
| a DataIndex target chosen by counts alone | `dynamic_data_index_native` |
| `EDynamicSystem` defaults read as signed compressed `Int32` | `dynamic_system_routing_native` |
| `RootComp.Type` labels from numeric agreement alone | `dynamic_root_comp_native` |
| `SceneVisibleStateInts`/`SceneVisibleAreaInts` as visible-group targets | `dynamic_root_comp_native` |
| the IdComp branch skipping routing; stored `Comps.Num` as the loop bound | `dynamic_root_comp_native` |
| `MountViewModel` as a model record (it addresses `PrimitiveStringList`) | `dynamic_resource_comp_native` |
| `VisibleStateGroup` index zero as an invalid marker | `dynamic_visibility_state_join` |
| the MapConfig condition list as a complete state catalog | `schemas/map_config.py` |
| variable conditions as exact integer tests; a missing variable as zero | `dynamic_visibility_runtime_native` |
| a shared generic loader pointer as proof of the loaded class | `dynamic_visibility_runtime_native` |
| `streamingDataPathRoot` as the DynamicStreaming path | `dynamic_streaming_config_join` |
| an all-scalar `fb_version` root; an ungated 16-byte entry width | `dynamic_version_native` |
| auxiliary field-4 prefix equality as full-width equality | `dynamic_aux_pair_corpus` |
| descriptor 21 as a lossless root-name copy | `dynamic_aux_pair_corpus` |
| byte-sized `RootVisible`/`AreaVisibleGroups` from `Get*Bytes` helpers | `dynamic_stream_area_corpus` |
| `RootVisible` as the union of area slices; the empty inverted box as malformed | `dynamic_stream_area_native` |
| a portal's world position as its destination; `forceLoad` as the skip-AOI flag | `portal_center_join` |

## Recovery queue

1. A component-ownership witness for descriptor 21 or a source-backed meaning
   for another auxiliary descriptor, with a runtime path/provider receipt.
2. ResourceGroup consumers beyond the selected LogicState mask query,
   including the descriptor-source helper's owner join and the SceneState,
   LevelNum and FactoryIndex scalars. The Sludge
   `SurfTileIDs` group-to-primitive/list and load-check-to-apply joins are
   authenticated conditional native consumers; a live Sludge/grid/tile
   receipt and deferred callback behavior remain the next Sludge boundary.
3. Runtime receipts (exact build, caller, file identity) for MapConfig and
   streaming-config selection, grid and area activation, version phase and
   ban results, portal AOI and spawn, and the squad teleport `pos` source.
4. The remaining nested main fields and positive table targets, then an
   allocator-backed residual/padding proof and `DataMask`.

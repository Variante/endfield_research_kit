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
| [`dynamic_group_components_native`](../../scripts/game_data/dynamic_group_components_native.py) | typed nested DataGroup component layouts and authenticated file-relative, grid-local child spans |
| [`dynamic_group_owner_join`](../../scripts/game_data/dynamic_group_owner_join.py) | same-source typed DataGroup children to directory-witnessed, template-checked authored RootComp candidate chains |
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

The Model receipt API replays this source set without streaming or exporting.
It normalizes one physical DynamicStreaming root, authenticates manifest and
outer/ledger hashes, recomputes the native/source audit and compares the full
file selection. Saved derived Model values and collider edges never authorize
fresh labels. Missing/mismatched gates, source selection drift and consumption
changes fail closed with source-specific diagnostics. The Assets consumer uses
the manifest path, active logical Bundle and actual prefab-root PPtr to attach
stored source records to admitted collision variants. It retains Model axes
and per-collider prefab-local matrices separately; grid UniqueId is not a live
Model instance ID, and source-directory names do not establish a loaded area.

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
load as an instantiated object. The current capture filter plan belongs under
`reports/runtime_capture/collision-current-source/`; wider historical asset
shortlists retain their original-build evidence boundary.

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

The installed-client port rederives the Mesh/cache and shape contracts from
current constructor/destructor publications, named native type getters and
their actual virtual slots. The named Mesh creation binding reaches the
current Mesh factory and constructor; the holder release uses the current
devirtualized consumer. The former standalone collider actor getter is now
represented by its inline detach call site. These declarations pass their
native gates and focused offline checks; historical captures remain evidence
for their own frozen build. Other Collision capture dependencies still require
porting before its preset can select this build.

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
the requested API, not the live cached function pointer. The current Physics
registration loop pairs explicit same-index names and functions using its
compiled count. Array adjacency alone never admits an observed query binding.

[`collision_query_native.json`](../../scripts/game_data/contracts/collision_query_native.json)
now authenticates the selected argument/result ABI, native result writers and
requested-name/resolver/cache/caller routes. Metadata value widths agree with
the native array-copy loops; the array-length export supplies the checked header
field. The observer admits native result interpretation only at a reviewed
original caller whose live cache contains the exact reviewed target. Other
callers/cache values remain diagnostics. This conditional gate supplies the
missing live binding witness without inferring registration from table adjacency.
Its current contract also names each selected managed caller and authenticates
the lookup, cache store/load and indirect call within that caller's actual unwind
family, including cold resolver fragments. Unused historical paired-array
inventories and overlapping body slices are omitted from the observer contract.

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
saved-session admission. Previously admitted retail sessions supply live caller/cache
matches on their frozen build, both ordinary Collider and ECS hit identities, actual filter returns
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

The installed-client port re-derives this family independently of the wider
Streaming row decoder. Its ordinary and complex records gained an anonymous
trailing word; terrain retains its previous width. Shape userdata now retains
that word and uses different surface/secondary storage. The reviewed contract
owns those coordinates, and both stored projection and runtime comparison use
it. An absent shape-userdata read withholds parameter comparison; zero-filled
transport storage is not an observed parameter value. Complex secondary
selection remains separate from the ordinary packed secondary byte.

The exported `FactoryUnitConfigAsset` source family has `colliderData` and
`colliderMeshes` fields. The named
[`ownership claims`](../../scripts/game_data/contracts/ecs_collision_ownership.json)
re-prove a `CreateBusRender` route that reads both fields, supplies ordered Mesh
instance IDs to decoding, obtains a returned actor's physics ID/version and
records an owning entity. MonoScript CAB/PathID, exported PPtr declarations and
per-output freshness can authenticate these authored inputs. Previously
authenticated factory definitions tile through EOF and preserve their declared mesh targets;
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

The broader field-2/marker contracts still describe their own selected build.
The current Collision observer does not relabel them as current: its ECS
contract independently authenticates the selected constructor's descriptor,
slot-three callback assignments and publications, and its observer contract
owns the current resource helper families, including cold paths. Producer
labels follow those current selector assignments. This closes the capture
dependencies without claiming a current stored Streaming corpus projection.

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
as `unbound_decoder_input`; they do not supply a caller-sized or source-owned
framing claim. `ecs_collision.decode_prefix` can separately project the complete
self-sized definition prefix from its authenticated kind and record counts.
It never uses the raw length argument to trim the definition. The existing
strict reader still requires exact EOF on that schema-sized slice, and captured
trailing bytes remain opaque. Prefix projections retain their own
`structuralOnly` boundary, unknown length units and absent file/resource owner;
they cannot replace an owned definition or supply a missing mesh-ID span.
Clipped prefixes remain unavailable, including captures that contain a complete
header but not its declared records. Owned definitions still require exact EOF,
and failures identify the decoder,
producer, expected span and captured source hash. Resource resolution and object lookup records in the same
original callback can join a successful resource handle to the actual decoder
input ID and the serialized instance-ID map's CAB/PathID. Repeated observations
must agree; no name, position, manifest suffix or cross-frame ID lookup chooses
an input. Map-lock contention and source routes without observed lookup records
remain explicit gaps. The reusable audit is
[`collision_runtime_ecs.py`](../../scripts/game_data/collision_runtime_ecs.py).

An independently observed original native Entity setter supplies another runtime
join for callers without the recorded Streaming source callback. The decoder's
returned actor identity, setter's before/after userdata and registry identity,
copied Entity argument, and later query result must agree on actor, userdata,
physics ID/version and assigned Entity. The decoder must precede the setter,
which must precede the query; changed Entity/version, stale addresses, missing
argument reads and multiple candidate setters withhold a unique route. This
route is published separately from source-callback ownership. It can connect a
schema-sized captured definition prefix to a sampled runtime Entity/query,
without identifying its stored file, declaring the length argument's units,
selecting one actor shape, or proving continuous lifetime.
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
zero in the preceding getter/cache capture. These are original hook-entry counters, not just
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
This proves the selected native dispatch and eligibility conditions; the earlier
getter/cache archive alone does not identify the executed backend or branch.

The reusable observation-boundary audit now reads these context members and
population fields only through the same checkpoint's typed scene graph. It also
censuses other archived address ranges without borrowing their bytes. All
required context vtables and population fields for the sampled scene are absent
from that earlier capture.
Even an observed zero population at a later checkpoint would remain distinct
from the original update's copied branch operand. Successful character queries
and query blocking do not imply awake dynamic islands or solver constraints.

For the idle-solver question, that earlier archive reached an observation boundary:
a further observation had to distinguish an unentered dynamics update, its actual
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

The admitted dynamics-entry capture closes this idle-route question for its
sampled updates. Original scene entry encloses a typed PGS context update whose
receiver and island manager equal the scene's held members. The reviewed flush
return site exposes an unchanged zero saved active-island operand, and the
original update returns normally. This directly proves the zero-island early
return before solver-task allocation in those samples. Independent entry censuses
also show scene/PGS activity while the selected contact preparation/solve routes
remain unentered. Sampling does not extend the observed branch to every update.

The sampled accurate-island fields contain varying kinematic counts but zero
active islands, rigid bodies, articulations, contact managers and constraints;
before/after typed context members remain stable. Positive query hits and filter
decisions therefore coexist with an idle contact solver. They are distinct
collision consumers, and neither kinematic activity nor visible character
movement guarantees solver-eligible dynamic work. Some original updates also
have a same-thread physics-core ancestry and matching typed completed public
scene. Worker updates retain direct scene/context ownership but no proved core
step join; timestamps and prior completions do not fill that gap.

This capture also broadens the exact getter/cache/CAB/PathID route across
collision-only stairs, buildings, rocks, furniture and props. Fresh targeted
AnimeStudio extraction decodes their complete cooked CPU triangle payloads
despite zero render vertices, and the decoded vertex/triangle counts agree with
every joined live cache header. This remains header agreement: no joined sample
archives the complete runtime vertex/index arrays. Repeated source slots with identical scale bits
remain descriptor aliases, even when the ordinary shape ordinal is available;
the audit preserves that ambiguity rather than asserting a unique scale join.
Generated inventories and per-call comparisons remain under the capture's
`collected/` directory and `reports/runtime_capture/collision/`.

An unchanged capture is no longer needed to explain the idle solver or repeat
the completed asset identity route. Positive solver-contact participation needs
an actually observed nonzero island gate followed by preparation/solve and its
actor/shape ownership. There is still no authenticated gameplay target guaranteed
to produce that work. Runtime array equality, current shape pose and continuous
attachment history remain separate requirements.

The offline geometry audit now also follows the saved query consumers. It
recomputes query, ECS source and getter/cache records from admitted events before
trusting their cached projections, and authenticates the frozen source layout's
selected native inputs. The complete cooked Mesh receipt supplies face-remap
aliases and triangles. Creation-source actor/local poses transform each aliased
descriptor separately; plane distance, barycentric coordinates and normal
agreement remain numerical evidence, not a current pose claim. Equal-scale
aliases can be discriminated by their transformed face positions under that
source-pose assumption, while the strict scale-only selection remains ambiguous.

Recorded sphere/capsule sweep normals need not equal a triangle's facet normal
at an edge or vertex. The query's original direction, distance, radius and hit
point supply an independent numerical support-feature comparison. Positive
distance samples agree closely with the radial sphere or closest capsule-segment
feature; initial-overlap/nonpositive-distance results retain a separate gap.
The earlier zero-distance capsule results had zero position vectors and lacked
native validity fields. The expanded observer now keeps the whole consumed
native prefix before and after conversion. Its zero-distance sweep results omit
the standard ABI candidate position bit; copied point bytes can be nonzero as
well as zero. They do not supply a surface-point comparison. Native face/remap
agreement, geometry identity and filter consumption remain independently
checkable. The validity-word location and candidate masks remain explicit in
the geometry-state contract rather than being promoted from correlation alone.
The comparison does not normalize the recorded query direction or claim the
native feature-selection branch. These calculations are owned by
[`collision_geometry_evidence.py`](../../scripts/game_data/collision_geometry_evidence.py).

Same-owner/thread returned floor hits have bitwise matching point, normal, face,
distance and collider identity fields, including observed walkable-floor
results for recovered collision-only stairs and other environment assets.
Observed filter returns also accept uniquely joined collider proxies from these
queries. UV equality is recorded separately, and a stack-copy value comparison
does not become pointer identity. Repeated equal hit candidates and ambiguous
proxy filters remain explicit. This closes sampled gameplay consumption of
render-empty cooked meshes independently of contact solving. The reusable
consumer join is
[`collision_query_consumption.py`](../../scripts/game_data/collision_query_consumption.py).

The header-only archive's exact address-union census found no joined runtime
vertex/index bytes. The expanded observer closes byte-exact vertex and ordered
triangle-index comparisons for complete extents within their original getter/
cache observations, with repeated header, CAB/PathID and ECS identity. The
collision-only Meshes have empty render geometry but real stored and live
collision surfaces. Independently authenticated selected source receipts may
be combined without re-extracting unchanged source objects. Clipped array tails
remain absent elsewhere in the expanded archive; unrelated callbacks do not
complete those snapshots or establish continuous lifetime.

[`collision_runtime_dispatch.py`](../../scripts/game_data/collision_runtime_dispatch.py)
narrows header-only sampled updates to one enclosing original core with a matching
typed completed public scene and equal step bits. Worker candidates remain
conditional. The reviewed complete task-run wrapper dispatches a virtual task
and supplies the common observed return site, while the continuation address is
reused across original steps. Neither identifies a task generation. The native
window is retained in the solver-dispatch contract. The expanded observations
now close sampled original scene generation, zero task reference decrement,
typed task run, original scene update, PGS update and saved island-decision
chains across threads. Original producer/update step bits agree. These are
observed worker-step joins; unobserved generations remain temporal candidates.

The remaining observation gaps are clipped arrays, global poses and body mode
for unsupported dynamic actor types, unobserved worker generations, continuous
attachment history, runtime BVH equality and positive contact preparation/solve
if eligible work occurs. Current static poses and sampled worker ownership no
longer require another identical run. Do not repeat the capture merely to raise
the recovered asset count or hope ordinary movement/combat creates solver work.

The expanded observer is implemented in the collision provider, with reviewed
declarations in
[`collision_geometry_state_native.json`](../../scripts/game_data/contracts/collision_geometry_state_native.json)
and selected-build validation in
[`collision_geometry_state_native.py`](../../scripts/game_data/collision_geometry_state_native.py).
It copies bounded vertex/index extents inside the original getter's live-cache
sample and repeats typed cache pointers/counts, CAB/PathID and ECS identity.
Complete extents are compared only within that getter/cache observation by
`collision_runtime_geometry.py`; deduplication does not grant later callbacks
the same byte snapshot. Separately timed current static-actor global and shape
local pose fields follow the original getter consumers. Dynamic actor poses,
continuous lifetime and an atomic mesh/pose snapshot remain unresolved.

The observer also preserves the original native hit prefix before and after
conversion. Face, position, normal and distance have direct selected consumer
reads; the adjacent validity-flags word follows the standard PhysX ABI candidate
and remains conditional until live validity evidence is reviewed. No flag
candidate alone promotes a zero-distance point to a valid surface measurement.

For worker ownership, original scene simulation supplies a sampled generation,
the typed task manager's original zero reference decrement supplies its dispatch
decision, and the typed task-run wrapper supplies the original worker phase.
The dispatch token is retained before the original manager can submit the task;
reused addresses, stale/changed generation or missing phases stay unjoined.
Completed-core scene and original task/scene nesting are checked independently
by `collision_capture_geometry_state.py`; `collision_runtime_dispatch.py` retains
these observations separately from enclosing-time candidates. Lock contention
at generation closure invalidates pending joins rather than retaining stale
ownership. Offline validation cannot supply the still-unobserved live phase
records or positive solver contacts.
Selected-build ABI validation, compiled original-call forwarding review and
saved-session admission tests pass. The expanded collision host and runtime are
built. The expanded live capture has passed admission and closes its complete
array comparisons and sampled worker chains. Repeated inline static-actor global
and shape-local poses put valid-position query hits on their recorded cooked
faces. Captured native face indices and converted face fields agree with the
stored face remap, including zero-distance cases whose point remains excluded.
Creation-source positions agree exactly with current positions in this selected
set; quaternion differences are bounded at floating-point precision. Keep the
numerical comparison conditional on separately timed reads and checked identity
mesh-scale orientation rather than declaring an atomic query snapshot.

The unsupported pose vtable resolves through its complete pure type-name getter
to `PxRigidDynamic`. Its declaration and the `PxRigidStatic` control live in
[`collision_actor_type_native.json`](../../scripts/game_data/contracts/collision_actor_type_native.json),
validated by
[`collision_actor_type_native.py`](../../scripts/game_data/collision_actor_type_native.py).
That class name does not distinguish dynamic/kinematic mode, awake participation
or contact response. The observer intentionally withholds its unread global pose;
the local shape pose alone is insufficient for world placement.

The current actor-type declarations select final constructor/factory address
points, excluding intermediate construction tables that share the same name
getter. The current body-mode contract follows the named managed setter through
its cache/resolver, same-index Physics registration and native bool/flag path.
That registration is bounded by its authenticated compiled count; the next word
belongs to adjacent data and is not a sentinel. Neither static port establishes
current live setter execution or changes the historical capture boundary.

The reviewed
[`collision_ecs_shape_policy_native.json`](../../scripts/game_data/contracts/collision_ecs_shape_policy_native.json),
authenticated by
[`collision_ecs_shape_policy_native.py`](../../scripts/game_data/collision_ecs_shape_policy_native.py),
now records the common native ECS shape-setup discriminator. The true secondary
option clears simulation while keeping scene query enabled; a separately read
runtime setting selects trigger versus query-only configuration. The false
secondary option clears trigger and keeps scene query enabled. For mesh geometry,
simulation additionally depends on the original actor-kind result and, for the
tested concrete dynamic type, a bit returned by its original body-flags getter.
The named static actor implementation takes the simulation-enabled ordinary
branch. These are conditional native configuration rules; stored secondary
options and class names do not establish the selected runtime branch or final
flags. The mode bit's kinematic name is now proved by
[`collision_body_mode_native.py`](../../scripts/game_data/collision_body_mode_native.py)
and its reviewed contract: the named managed bool setter, compiled same-index
registration loop, native bool forwarding, typed dynamic flag getter and final
cached-property comparison establish its original compiled meaning. This is
not a live setter, registration or IFix-selection claim.

The typed dynamic getter follows its own buffered-state mask, reads a word from
the selected inline or buffer field, and clears its high bit. Its declarations
are independent of the static pose getter's buffering fields. The existing
static pose observer alone does not supply this word or final shape API flags.
The admitted body-state observations now supply repeated typed native body/shape
flags and registration fields. The sampled shapes have simulation and scene
query enabled, trigger disabled, and in-scene registration; the dynamic
implementations return a mode word with the authenticated kinematic bit set.
These sampled native modes are separate from awake-body classification or
contact participation. Independent original updates still take the zero-active-island
return, with no sampled awake rigid bodies, contact managers or constraints.

The body-state expansion is owned by
[`collision_body_state_native.json`](../../scripts/game_data/contracts/collision_body_state_native.json)
and [`collision_body_state_native.py`](../../scripts/game_data/collision_body_state_native.py).
It uses the existing original geometry getter and adds no hook endpoint or game
query. Separately timed before/after snapshots preserve typed actor and shape
identities, repeated ECS ownership, buffered body/shape flags, geometry type,
registration and public scene, scene configuration pointers, and shape simulation/query filter
words. Static and dynamic registration offsets are independently anchored.
`collision_capture_body_state.py` validates each sampled join; the geometry audit
attaches it only to that same getter. Missing fields stay missing, changed
snapshots withhold a stable join, and configuration pointers never stand for
executed filter decisions. Historical sessions without these fields remain
readable and retain their missing-byte boundary.
The type getter reads the inline geometry tag directly, independently of the
triangle-geometry getter's buffered data selection. Its current tag distinguishes
mesh from other moving shapes when the original triangle getter returns false.
The native configuration reads also cover ordinary Unity actors without ready
ECS userdata. `collision_runtime_configuration.py` preserves complete stable
typed native reads independently of the stricter versioned ECS/source join.
Missing ECS ownership cannot discard those native fields or invent CAB/PathID
ownership. The same original query converter supplies nonzero Unity Collider
InstanceIDs and zero ECS identities for those native-only records; those IDs
still do not supply serialized ownership. The dynamics argument is an internal
scene pointer and must be converted through its own reviewed public-interface
offset before comparison with the body snapshot. Matching public-scene addresses are conditional
comparisons, not body-to-original-step or continuous lifetime evidence.

The observed scene filter address now selects the complete original compiled
pair shader authenticated by
[`collision_pair_filter_native.json`](../../scripts/game_data/contracts/collision_pair_filter_native.json)
and [`collision_pair_filter_native.py`](../../scripts/game_data/collision_pair_filter_native.py).
The reviewed scene packet, indirect caller and hidden-result ABI distinguish
this shader slot from the separate pair callback and notification callback.
The shader consults a layer-matrix row, a sorted object-ignore list for two
nonzero untagged keys, and shape policy words. A tagged key bypasses only the
object-list lookup; it does not bypass layer filtering. One shape exclusion bit
or a separate bit on both shapes returns exclusion without writing pair flags.
Otherwise the shader combines stored flag contributions, trigger attributes
and the mutual notification formula. Its cold branches are part of the proof,
including the invalid-layer diagnostic path, whose return does not exclude.

Upstream, the original pair routine can exclude non-trigger kinematic-static
and kinematic-kinematic pairs before the shader, depending on separately stored
scene modes and committed body-core override bits. For two kinematic body cores,
the ordinary downstream path also clears the first pair-flag bit after the
shader. Public buffered body flags must not be substituted for those unobserved
committed cores. These conditional native rules help explain why simulation
enabled shapes and a non-null notification callback do not guarantee solving
or reporting; they do not establish the actual cause of a quiet sampled step.

[`collision_runtime_filter.py`](../../scripts/game_data/collision_runtime_filter.py)
replays the admitted original body records, authenticates the selected build and
reports sampled shader selection separately from required operand coverage.
The earlier body-only archive has no coverage for the manager-pointer cell needed by the
layer matrix, the two scene-mode fields, or the notification object's vtable.
The sampled untagged keys' ignore-list headers are also outside saved coverage.
The recorded callback address itself remains a direct body-frame observation.
No pair is manufactured from separately timed query-hit shapes, and no missing
operand is borrowed from another callback. Further pair/contact work needs an
original pair and step, committed core flags, scene exclusion modes and the
shader's actual matrix/list decisions; repeating the current configuration
capture unchanged cannot supply that evidence.

The expanded observer profile includes original general pair, shared dispatcher,
shader, layer and object-ignore hooks. The dispatcher covers the fast caller
that bypasses the general prefilter. Its paired records preserve private core
flags and raw filter outputs independently of public buffered flags. Passive
typed owner reads retain actor/shape and ECS identities before/after the original
pair call; observed task generations or simulation/update ancestry remain
separate from unbound pairs. Existing simulation and body callbacks also sample
scene modes, the full layer matrix and notification target, so a quiet solver
still supplies configuration evidence. Bounded ignore-list prefixes never repair
missing tails; the original helper return supplies its own sampled decision.
Declarations and read layouts remain in the reviewed pair contract; native
admission and replay stay in the parent repository, outside the recorder.

The expanded live session now supplies selected original general-pair,
dispatcher, shader, layer and object-ignore calls, with unchanged original
inputs/results and complete repeated scene-policy and typed pair-owner reads.
All sampled shader results agree with the recovered rules. Permitted shader
flags agree as well, while excluded calls preserve their incoming flags.
Original layer-helper exclusions explain most excluded results; the remaining
excluded results agree with the forced-shape predicate. Observed object-ignore
helpers do not exclude: their captured inputs distinguish complete empty lists
from tagged/null-key bypasses. These are sampled execution facts, not a global
pair census. `collision_runtime_filter.py` publishes them separately from the
older body-window address-coverage questions, which inline policy records do
not retroactively fill.

The stable sampled scene policy permits kinematic-kinematic processing and
enables the ordinary kinematic-static exclusion mode. Its matrix and
notification virtual target are readable. Every sampled general pair reaches
its nested dispatcher, and each permitted pair's shader attributes select the
trigger rule. The observed pair cores are kinematic-static, with a trigger
shape; the reviewed upstream rule bypasses that mode exclusion for triggers.
Permitted trigger processing therefore supplies no positive contact-solving
control. The sampled query-hit dynamic bodies are also kinematic. None of these
observations establishes the whole scene's dynamic-body population.

Pair-bound typed owners remain stable across the original calls. Some retain
a repeated versioned ECS registry identity; others retain only native ownership.
The ECS identity must match that pair's actor and shape and survive JSON report
publication as an array. Fixed transport slots are interpreted by event role:
policy matrices and ignore-list prefixes are not ECS snapshots. Reader tests
preserve strict malformed-ECS rejection and actionable call/field diagnostics;
these offline routing and report-round-trip corrections need no recapture.

The original pair calls have no observed simulation/update/task ancestry in
this archive. Their step ownership remains unbound despite readable scene
configuration and actor registration. Some shader calls also lack a captured
dispatcher/pair parent, including permitted non-trigger outputs. Original
return-site bytes distinguish dispatcher-route calls from another caller
family, but native code membership cannot supply the absent invocation's body
owners or step generation. The reviewed downstream flag rewrite remains a
reason not to equate a shader output with solving. The dynamics updates still
take their observed zero-island early return, with no selected contact
preparation/solve entries. Before any further solver-focused capture, identify
an eligible body/scene and a concrete original pair-to-step route; an unchanged
repeat would not settle those gaps. Per-session counts and callsite inventories
remain under the admitted session's `collected/` directory.

Offline source recovery identifies a concrete activation target in the
breakable-box postmodel prefab. The selected current Bundle contains dormant
Rigidbody components with positive mass, gravity enabled and no frozen
constraints, each reciprocally declared alongside an enabled, non-trigger
convex MeshCollider on its own active GameObject. Their complete stored TRS
chains reach the AssetBundle's declared prefab root. The model table joins that
prefab by its full resource path. The exported production scope's absence of
Rigidbody rows was an extraction omission, not evidence that the client had no
bodies. `unity_scene.py` now reads the observed Rigidbody body through EOF and
`trace_rigidbody` retains stored candidate status separately from live eligibility.

The named DestructiblePhysicsMono script is authenticated through its external
MonoScript CAB/PathID slot. Its independently read physics-settings prefix in
[`monobehaviour/destructible_physics.py`](../../scripts/game_data/monobehaviour/destructible_physics.py)
names exactly the selected debris colliders; the subsequent effect/curve tail
remains opaque. The original initialization routine sets bodies kinematic; the
original break routine clears that flag and applies force to the item bodies.
The original kickable launch path enables simulation, wakes a present body and
forces simulation for that frame. These named compiled claims, including the
literal setter arguments, are re-proved by
[`collision_solver_body_native.py`](../../scripts/game_data/collision_solver_body_native.py)
and [`collision_solver_body_claims.json`](../../scripts/game_data/contracts/collision_solver_body_claims.json).
They establish conditional activation targets, not observed branch execution:
IFix selection, body existence, break-manager budgets, live scene/filter flags,
awake state and eventual contact preparation remain separate. The stored world
detail selects the destructible physics template and supplies coordinates.
The maintained Interactive template reader closes that template through EOF:
its exact detail-keyed variant enables the selected box model and overrides the
physics component's node to the GameObject that owns the authenticated
DestructiblePhysicsMono. This closes the stored detail-to-model and node joins,
without relying on name similarity. The template's authored destructible
properties allow bombs and disable physical and interactive damage; the box
variant has no property diff changing those defaults. The physics component
also requests a freeze interval. These are stored defaults, not a proved live
damage policy: level properties, runtime changes, IFix selection and the actual
accessible instance remain open. A bombable obstacle is therefore a better
capture control than ordinary loot crates that only disappear or play effects.
The format boundary belongs to
[`memorypack/interactive.py`](../../scripts/game_data/memorypack/interactive.py)
and its current-build union gate; the per-build projection belongs in the
stored-body audit under `reports/`.

The original broadphase pair route now has a reviewed task boundary in
[`collision_pair_step_native.json`](../../scripts/game_data/contracts/collision_pair_step_native.json),
authenticated by
[`collision_pair_step_native.py`](../../scripts/game_data/collision_pair_step_native.py).
Scene construction gives `ScScene.postBroadPhase` and
`ScScene.postBroadPhaseCont` separate concrete task vtables and embedded owner
slots. Original dependency code wires the former's continuation to the latter,
with reference retention and manager propagation. The continuation run reaches
the general pair packet; that routine also constructs `OverlapFilterTask`,
whose run reaches the separate batch shader caller. Its owner is NPhaseCore,
which holds the Scene pointer, whereas the embedded broadphase owners are the
Scene itself. Both domains must be decoded before comparing an owner to a step.
The concrete task tables use the already authenticated common run wrapper;
complete unwind families include the batch's downstream flag rewrite. The
protected/indirect entry into the dependency routine is not proved as a direct
public-simulation call. This is exact compiled wiring and a conditional route,
not an executed producer-to-step claim.

The archive's recorder and admission decoder selected only the dynamics-task
vtable at the common release/run hooks. Other task types are forwarded without
records. The saved archive contains neither embedded broadphase task header,
even as separately timed address coverage. Consequently the current pair calls
cannot be assigned a simulation generation offline. The expanded observer now
supplies type-aware task headers and original producer,
continuation/reference-release and run records, retaining NPhaseCore-to-Scene
reciprocity and task reuse boundaries. A shared scene, task name, last scene
generation or nearby update is insufficient. Stored box activation gives a
concrete future physical control, while positive awake-body, pair-step and
solver-contact evidence still requires those original live observations.

An admitted expanded session supplies original dependency-wiring and
post-broadphase producer calls, typed embedded task headers and worker runs,
but all new producer generations remain unbound. The recorded return site is
the common virtual task-run wrapper; simulation ancestry does not follow a
worker thread. The compiled named `ScScene.rigidBodyNarrowPhase` task stores
its Scene owner and tail-calls the dependency program with that owner and its
original continuation. This prerequisite was absent from the observer's typed
task set. Its constructor, name, virtual slots and complete tail thunk are
reviewed in
[`collision_narrowphase_task_native.json`](../../scripts/game_data/contracts/collision_narrowphase_task_native.json)
and authenticated by
[`collision_narrowphase_task_native.py`](../../scripts/game_data/collision_narrowphase_task_native.py).
The saved producer caller is consistent with this route, but lacks that task's
header, enqueue and original generation source; neither a shared Scene nor a
nearby completed simulation repairs the join. The extended observer now covers the original public-Scene execution task,
native scene phase, collide-step and narrowphase producers before broadphase.
The reviewed task contract authenticates each constructor, owner domain,
continuation thunk and concrete virtual run. The original scene-simulation guard
releases the execution task; a declared collide task is not accepted as that
same producer's seed. Zero or unordered native-simulation inputs do not seed
work. Admission requires original release/zero-decrement/run and the preceding
producer route at each handoff; an unresolved completed core propagates to all
its descendants. The live chain is still unobserved in the saved session above;
these are compiled and adapter facts, not recovered missing runtime records.

The same session records original kinematic setters and sleeping reads with
matching live binding caches. All setter samples request kinematic mode; none
of the body-operation samples establish an awake committed dynamic body. The
break and force hooks have no entries, so the observed action does not supply
the selected destructible activation control. No rooted body or solver-stage
pair is available to complete that evidence chain. These are sampled coverage
boundaries, not claims that the game never destroys objects or solves contacts.
The offline reader now admits the saved expanded profile's native simulation
and complete hook census; filter summaries count only named admitted ancestry
or worker-generation statuses as observed steps. An unbound producer or an
unresolved core projection remains outside that count.

The activation-stage observer records the original load, interactive physics
break request, attack preparation, attack callback and manager submission. Its
complete unwind families include cold IFix paths; selected metadata proves the
receiver, reference-handle, indirect Vector3 and MethodInfo carriers. Hook entry
uniqueness and field layouts are gated on the opened native image. Reviewed
facts live in
[`collision_activation_capture_native.json`](../../scripts/game_data/contracts/collision_activation_capture_native.json),
validated by
[`collision_activation_capture_native.py`](../../scripts/game_data/collision_activation_capture_native.py).
[`collision_capture_activation.py`](../../scripts/game_data/collision_capture_activation.py)
keeps original manager Boolean results separate from new admission or solving,
and retains separately timed item/collider counts, timers, handle validity,
manager counts and Mono serialized identity. Stage coverage distinguishes a
loaded dormant object from an executed request, preparation or callback; it
cannot identify an unobserved IFix or budget branch.
Each activation stage has its own bounded event budget, so loading a populated
scene cannot exhaust later request, callback or submission observation.
Observed body operations inside the attack callback can also select bounded rooted rechecks without
inventing a missing final break call.

Saved activation records exposed an invalid generic-layout assumption: the open
`List<T>` definition supplies placeholder field offsets, not a concrete list
layout. The activation contract now proves the original receiver-to-settings,
settings-to-items and integer size read that supplies the Mono's collider count.
The native accessor supplies the concrete coordinate; the open definition does
not. Earlier stage records preserve their raw word but withhold `itemCount`.
Their independently validated collider count, Mono identity and original stage
entry/return remain usable. Successful ABI, field-table and build checks alone
did not establish that generic coordinate.

The expanded saved session now proves original producer/reference/run chains
through filter tasks, and actual pair-prefilter calls inherit those exact scene
generations. The joined sample consists of trigger pairs; it does not establish
a solver-eligible physical pair. Original PGS preparation and solve calls are
also observed, with repeated descriptor keys, contact-manager/context route
samples and, for some sides, repeated versioned ECS identity. The nonzero island
decisions lack captured original task generations. Neither those updates nor
the separately observed solver calls can be assigned to a particular physics
step by equal context pointers or timing.
Source-decoder samples sharing a later solver actor address carry different
userdata and physics versions; they are rejected as address reuse, not accepted
as stored-source provenance. An independently observed kinematic-to-awake
dynamic transition lies outside destructible-stage ancestry. Missing break
requests therefore do not mean that the session contained no active bodies.
The remaining boundary is a same-lifetime body/shape/source and positive-step
join, not the existence of physical solver work.

Saved post-solve constraint windows now establish positive accumulated normal
response for sampled original PGS contact invocations. The reviewed scalar
consumer contract
[`collision_solver_response_native.json`](../../scripts/game_data/contracts/collision_solver_response_native.json)
and validator
[`collision_solver_response_native.py`](../../scripts/game_data/collision_solver_response_native.py)
bind complete original wrapper/core unwind families, dispatch tags, descriptor
extent and the header/count/point-to-response-array path. The maintained
[`collision_runtime_solver_response.py`](../../scripts/game_data/collision_runtime_solver_response.py)
uses admitted same-call archive windows after the original solve returns and
keeps clipped response arrays unknown. A positive accumulated value can include
earlier iterations or warm starting; it does not establish a newly generated
impulse in that call, a force in world units, or an asset/step owner.

The same routines consume only the proved body vector lanes. The older observer
copied a larger prefix, whose remaining words can belong to padding or a
neighboring body; changes there are excluded from the response classification.
Those body copies lack recorded read-success flags, so vector differences stay
conditional even when archived constraint response is direct. Some sampled
solver-side actor, shape and geometry prefixes are absent from the archive;
others occur only under a different call. They cannot replace a same-lifetime
owner snapshot. This leaves a precise source/step gap while closing the earlier
question of whether positive physical constraint response was observed at all.

The copied contact-manager shape-core prefix also preserves geometry types and
complete analytic primitive dimensions. The selected getter leaves and native
type predicates are authenticated by
[`collision_solver_geometry_native.py`](../../scripts/game_data/collision_solver_geometry_native.py)
and [`collision_solver_geometry_native.json`](../../scripts/game_data/contracts/collision_solver_geometry_native.json).
These declarations agree with the documented PhysX capsule/box geometry ABI;
they do not identify a Unity Mesh object. The maintained
[`collision_runtime_solver_geometry.py`](../../scripts/game_data/collision_runtime_solver_geometry.py)
recomputes admitted stage/ECS records and response values before classifying
each same-call core prefix. It groups positive sides by the original solve call
and descriptor, preserving the candidate public-shape/core and lifetime boundary.
Finite capsule radius/half-height and box half-extents are recoverable without
new capture data or an invented cooked mesh.

The admitted positive response samples classify as capsule or box candidate
geometry. A separately observed triangle-mesh preparation pair has no selected
matching solve route in this archive. The triangle Mesh pointer begins beyond
the saved core prefix, so neither its stored asset nor its response can be
filled from another callback. That is a missing observation, not proof that the
prepared pair was never solved. Source candidates require the exact actor,
masked userdata, physics ID/version, assigned Entity and earlier original
source callback; a reused actor address or equal dimensions never select one.
The available solver observations therefore do not establish physical solving
for the recovered cooked meshes. Generic movement captures should not be
treated as a route to that asset proof. Existing query/getter/cache and complete
array evidence remain independently useful for Assets.

The source and observation-boundary audits reuse the admitted expanded event
context for current captures. They no longer perform a second journal pass with
an outdated compact-format version list, which could withhold valid source
evidence from newer captures. Input/native freshness gates and immutable source
receipts remain enforced.

The compiled PGS route has a separate context-owned task family, authenticated
by [`collision_solver_task_native.py`](../../scripts/game_data/collision_solver_task_native.py)
and [`collision_solver_task_native.json`](../../scripts/game_data/contracts/collision_solver_task_native.json).
The original update constructs `UpdateContinuationTask` with its exact dynamics
context, island manager, continuation and auxiliary arguments. Its concrete run
enters the solver phase. Solver start, partition, setup, preparation, solve and
end callbacks have their own typed vtables; their owner fields must not be
interpreted as a Scene merely because broadphase tasks use that layout.

The common run wrapper returns before the dispatcher's subsequent base-task
release. That release decrements the completed task's continuation outside the
worker callback's original scope. Observing only the worker scope loses this
scheduling edge. The prepared observer retains original manager release,
reference-zero decision and concrete worker generations, then consumes an
unchanged same-thread completed-task witness at the original base release.
Only the actual continuation target can inherit that completion's cause.
Nested original solver-task releases can also inherit their active worker's
cause. Every new release/run invalidates older entries at that address; lock
contention invalidates the route epoch, and bounded-budget failures leave
missing routes unbound. No nearest-time/context lookup repairs a missing edge.
[`collision_capture_solver_tasks.py`](../../scripts/game_data/collision_capture_solver_tasks.py)
checks the original intervals, raw headers, typed manager, queue decision,
source generation and continuation equality independently. These adapters are
validated offline; their new live route coverage remains unobserved. A proved
PGS dynamics-call owner still does not supply an absent public simulation core,
asset identity or continuous actor lifetime.

The prepared contact sample also keeps bounded actor and shape prefixes under
the same descriptor-side call as its constraint window. Buffered geometry or
uncaptured pointees still require their own bytes. The constraint limit covers
the proved maximum byte-counted normal response prefix rather than clipping it
at the former small header window. Separate before/after body-copy success bits
prevent a failed read from becoming a vector-response claim. Historical samples
retain their original clipping and unknown read completeness. A response array
crossing archive chunks is accepted only when every complete scalar is present
under the same call/root, with each read time retained. A missing word or bytes
from another callback still withhold the response; no atomic snapshot is claimed.

Contact reports can be nested below the existing report guard and the original
simulation call. The reader resolves this bounded declared guard route for
current capture profiles, gives both header and pair the original simulation
owner, and checks retained-object enrollment against that owner's entry. A
later guard entry cannot repair late enrollment or missing simulation ancestry.

The expanded profile observes original Rigidbody setter, force and sleeping
wrappers and the original destructible break callback. Reviewed registration,
cache, forwarding and sleeping-getter routes live in
[`collision_live_body_native.json`](../../scripts/game_data/contracts/collision_live_body_native.json),
validated by [`collision_live_body_native.py`](../../scripts/game_data/collision_live_body_native.py).
Records retain passive native component/typed actor ownership, buffered and
committed flags separately, the original sleeping scalar, registration and the
runtime InstanceID-offset witness. A buffered request cannot replace committed
mode. Observed break or attack-stage ancestry selects the activation context; the observer issues no
physics getter, force or simulation. A bounded sampling burst after activation
covers subsequent original steps and pair/solver stages.

A bounded set of observed Rigidbody references is pinned and rechecked at
pair-owner and solver pair boundaries. The prepared selection also retains an
original non-kinematic setter outside destruction callbacks when repeated native
component, InstanceID and actor identity agree and the returned typed body is
registered, committed non-kinematic and awake. This selects the observed
`ScenePhysicsObject.set_isSimulating` route without inventing break ancestry.
Active-island population reads prioritize original updates but do not prove the
original branch decision. These samples carry the original body
operation, handle and enrollment timestamp. Actor address reuse cannot select
a stale rooted body: current native component, InstanceID and owned actor must
agree. Workers read pinned managed addresses rather than issuing managed
queries. Handles are released after callback quiescence. Native destruction
withholds the ownership join instead of reusing its old pointer.

[`collision_capture_lifecycle.py`](../../scripts/game_data/collision_capture_lifecycle.py)
admits these body records and producer/atomic/run routes. Unbound producers
retain zero generation fields and caller diagnostics. Filter tasks require an
observed creator; any new release invalidates an older queued generation at
that address. The task base and raw owner use one bounded prefix snapshot to
avoid combining type epochs after a heap task is freed. Pair replay uses the
admitted lifecycle route and withholds a step claim on a missing producer or
completed-core projection. Offline validation establishes the adapter; new live
branch coverage and positive contacts remain to be observed.

Review corrected the pair reader's offset base: filter and mode offsets belong
to the internal scene, while its typed public interface has a separately proved
displacement. The existing recorder already uses the internal base. Both pointer
domains are now explicit in coverage output and fixtures. This correction does
not supply any formerly missing bytes. A build and original-session replay alone
establish neither new live hook coverage nor positive solver contacts; the
expanded live records above supply selected hook coverage independently.

A static review of the expanded observer found and corrected an offline report
round-trip mismatch: body-class count keys must remain strings after JSON
publication so the geometry audit can compare its recomputation with saved
inspection data. Tests cover the round trip and rejection of a changed saved
count. This is a reader correction; it needs no new live session.

The body-state observer itself samples query-hit actors and shapes. It does not census
every solver body or execute the selected pair filter. Consequently, even a
complete new configuration snapshot cannot promise positive solver contacts or
close the per-pair execution join. Cooked geometry decoding, source identity and
movement-query surface use are already established for the covered cases. More
capture work serves the additional runtime-configuration/contact objective,
rather than being a prerequisite for those asset conclusions or their display.

The geometry audit now compares authenticated contiguous prefixes even when a
bounded array read stops early. Repeated typed headers, CAB/PathID and ECS
identity remain required, and each extent stays bound to one original sample.
The clipped observations' saved vertex and index prefixes match their cooked
sources. Missing tails stay unavailable and do not become complete arrays by
joining another callback, role or stored source. This closes the partial-byte
comparison without creating a reason to capture the same route again.

The observed original island decisions still take the zero-island early return.
Both sides of those updates have no awake rigid bodies, articulations, contact
managers or constraints, while kinematic population varies. The selected contact
preparation/solve hooks have no entries, and reporting guards remain empty.
Observed floor/filter use proves query-based gameplay participation independently
of positive contact solving. A future solver capture needs an identified eligible
body/scene and the missing body-mode/shape/filter-policy observations; an unchanged
repeat is not the next step. Counts and asset inventories remain generated reports.

The captured pre-dispatch reporting guards still contain empty reports. Native
query participation and filter decisions are positive collision evidence;
solver-contact participation and notification policy remain separate. This
successful session supplies substantial offline source and ownership work, so
an identical follow-up capture is not required to repeat those joins.

The Assets projection consumes this evidence through the maintained geometry
audit, not a saved investigation summary. Its joins require full serialized and
physical identity plus raw/cooked hashes. Query observations, unique movement
returns, accepted filter candidates and conditional pose-based surface checks
are separate published facts; none is solver-contact evidence. Complete arrays
and saved prefixes also remain separate. The frontend/publication contract is in
[`../webui/assets.md`](../webui/assets.md).

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
AssetBundle container paths. Original getter output and live held-cache equality
now supply sampled returned-shape geometry-pointer identity. Complete runtime
arrays and repeated current static poses close their sampled joins, with clipped
and unsupported cases left explicit. Later attachment history, unobserved dynamic
poses and positive solver-contact participation still need independent
observations. Widening the stored Mesh catalog does not supply those remaining
runtime states.

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

The contract additionally closes `PureFuncComp.Type`, `HittableComp.HitType`,
`DynamicEntityControlComp.EntityId`, `FactoryRegionControlComp.Level`/`Index`,
`ScriptControlComp.DefaultLoad`, `PureSystemComp.Type`, `NatureResourceComp.Type`,
and `BlightMiasmaComp.Empty`/`SnowFallTreeComp.Empty` (**exact selected layout**).
Single-field constructors pass the same checked argument to the alignment and
width slots; the validator requires the explicit argument-register transfer,
not equal constants inferred from the main vector width. `EntityId` is unsigned
64-bit, the two `Empty` fields are byte-sized Booleans, and all the other
fields remain signed 32-bit integers. In particular, `DefaultLoad` retains its
integer representation even when observed values are Boolean-shaped. The
current authenticated corpus contains the hit, factory-region, script,
pure-system, nature-resource and empty-marker records, while the pure-function
and dynamic-entity-control vectors have no authored examples. Generated layout
proof therefore does not establish usage for the latter pair. Hit/system/resource
enum labels, factory targets, load behavior and the meaning of an empty marker
need their own consumer proofs; this extension adds no live activation claims.

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

## Nested component DataGroup spans

[`dynamic_group_components_native.json`](../../scripts/game_data/contracts/dynamic_group_components_native.json)
and its validator close `NavModifyAreaComp`, `ViewStateControlComp`,
`MissionControlComp`, `ConveyorBeltGroupComp`, `RemapSceneComp`,
`StreamingAreaComp`, `ActivityControlComp` and `ErosionRootComp`
(**exact selected layout**).
Generated typed group getters pass a checked containing-position offset through
the shared ByteBuffer carrier helpers. The constructor's flattened DataIndex,
group-count and scalar parameter names match that nesting; its first struct
declaration supplies the containing width/alignment. The independent RootComp
and DataIndex validators own the group and index layouts, so this domain neither
duplicates their native catalog nor infers a group from its width alone.

The group contract's second schema version declares the scalar-owned `Vector3`
as an inline dependency without copying its methods or offsets. The validator
authenticates only that dependency's generated getters and constructor from its
owning contract against the same opened native image. `ErosionRootComp` stores
unsigned `ErosionCoreId`, a typed `PosList` DataGroup and inline `ErosionCorePos`
axes. The final unassigned bytes remain a reported gap; constructor alignment
does not establish padding semantics. Nested spatial fields remain decoded
values, not DataGroup references. Core-ID targets, coordinate space and units
need separate consumers before receiving meaning.

The authenticated decoder first joins path, length and VFS MD5, then checks the
complete main allocation framing. Each decoded component retains its grid and
vector ordinal and exact file-relative byte span. A valid group's stored
`Type`, `Grid`, `Index`, `Num` and `TotalInGrid` select a bounded same-grid target
span; the named target comes from the validated `EDynamicSceneData` enum and
SingleGrid vector, not a guessed meaning of the containing field. The output
retains target ordinals and target byte spans separately from the containing
record. Negative or overflowing spans, unknown type values, non-Boolean
invalid flags and invalid groups with nonzero count fail closed. Invalid,
valid-empty, resolved-nonempty and other-grid-unresolved groups remain distinct.

The current corpus establishes **structuralOnly** stored links from
`MissionControlComp.Conditions` to `MissionCondition`,
`NavModifyAreaComp.Group` to `NavModifyArea`,
`ConveyorBeltGroupComp.Paths` to `ConveyorPath`, and
`RemapSceneComp.SceneGridInfoList` to `SceneGridInfo`, and
`ErosionRootComp.PosList` to `Vector3`. Authored ActivityControl
condition groups are invalid with zero count; this establishes no activity
condition children or runtime predicate. `ViewStateControlComp` and
`StreamingAreaComp` have generated layout proof but no current authored rows.
Per-build counts, samples, group statuses and source receipts belong in
`reports/animestudio/dynamic_group_components_native_latest.json`.

These are containing-component-to-child relations, not RootComp-to-live-entity
ownership. Cross-grid resolution, template-root association of these indirect
children, `CompareType`/`ToBeTrue` behavior, control IDs, speed/length units,
condition evaluation and activation remain unresolved. A missing or mismatched
native build produces no report and preserves the previous publication.

Publication is restricted to the ignored `reports/`, `scratch/` and `tmp/`
roots, outside selected input directories. Resolved-path and file-identity
checks reject aliases of source files, contracts, native binaries and the
VFS outer report, ledger or exporter. The generated receipt records the
current parser import closure, the independently owned contracts and native
helper sources, plus selected native and VFS proof inputs. The same snapshots
must still match immediately before atomic publication. Missing inputs,
native mismatch, failed proof or source drift leave an earlier valid report
untouched and emit a bounded diagnostic; the fingerprints authenticate this
generated receipt and are not tracked-contract hash pins.

### Authored owners of indirect children

`dynamic_group_owner_join` reuses the group validator's authenticated root,
index and entity-enum context rather than repeating the native scan or
duplicating a catalog. The existing root decoder checks the current
DynamicSceneTemplates asset and each RootComp directory signature against it.
On the same VFS-identified bytes, a containing component is joined by exact
grid ordinal/UniqueId, component type and component ordinal. Its DataGroup
then supplies each child ordinal and byte range. The output retains source
path, containing span, group field, directory ordinal, RootComp ordinal,
entity type and ordered template signature alongside each child span.

These chains are **structuralOnly authored ownership**. Multiple parent
components and multiple RootComp candidates remain separate witnessed chains;
the join never selects a preferred owner or turns vector proximity into a
relationship. A group parent without a direct RootComp directory reference
keeps an explicit ownership gap. Invalid, empty and other-grid groups keep
their statuses and generate no child ownership. The selected template object
and its source provenance are re-read before publication, and the parser,
contract, native, VFS and template proof inputs must remain unchanged.
The publication gate also reauthenticates every original raw dump by its
physical resolved path, byte length and SHA256 after decoding; a same-path
rewrite or path rebinding preserves the previous report and fails closed.
The generated owner-join receipt keeps this per-file proof separately from
the parser and native inputs, so a retained older receipt describes only its
recorded publication boundary.
The selected SQLite document digest is the template witness; hashing the whole
Unity object store would unnecessarily bind unrelated asset work to this join.
Generated complete parent/child chains and receipts belong in
`reports/animestudio/dynamic_group_owner_join_latest.json`.

The authenticated current corpus supplies a unique authored RootComp candidate
for the admitted `MissionCondition`, `NavModifyArea`, `ConveyorPath` and
`SceneGridInfo` and `Vector3` children through their typed containing components.
The `Vector3` child chain is witnessed through `ErosionRootComp.PosList`, without
assigning a spatial role from that field name. The current
ActivityControl components also have direct authored-root candidates, but
their invalid condition groups supply no children. Parent ownership and a
valid child group are therefore independent observations: one does not fill
the other's gap. Current multiplicities and byte identities stay in the report;
the reader continues to retain multiple candidates if a future corpus supplies
them rather than asserting a universal single-owner rule.

This closes only a source-backed authored chain. It does not prove
RegisterEntity execution, live entity identity, condition evaluation,
load/activation state, spatial units, or IFix selection. Cross-grid ownership
and indirect children beyond the admitted DataGroup layouts remain unresolved.

### Mission returned-key writer lane

`dynamic_mission_key_source_native` owns the names-based claims in
`contracts/dynamic_mission_key_source_native_claims.json`. It reuses the
selected scalar string-index consumer and Mission query declarations,
authenticates their native build and method windows, and proves an
independent bounded writer block. It does not re-decode the source corpus or
claim the complete registration entry or lifecycle.

The selected `RegisterEntityCaredCondition` request receives an Int32 from
`GetStrKey`, preserves those bits in `R14D`, and writes them into the
returned slot's anonymous Int32 lane at `+8`. The query uses the same actual
helper and context cell and reads that lane for its dictionary key. This
extends the previously authenticated authored Id to string-span request
with **direct conditional returned-value flow**. It does not prove
allocation, deduplication, stability rules, or a numeric key value.

The shared generic context declares a typed
`SystemSegmentPool<MissionConditionSlotData>` request with a reciprocal
referenced value return, matching the concrete system's pool field. Its
registered method pointer differs from the actual helper: the reader keeps
that helper's implementation identity unresolved. The stored value type's
named metadata fields likewise do not authorize subtracting an assumed
object header to rename the anonymous lane as `missionKey`.

The writer block has a complete byte partition, actual call targets and
context, a selected nonnull-pool branch, and alias-aware preservation from
the Int32 return to the store. Declared unwind membership supplies the block's
native ownership only, without interpreting stack-allocation codes or
proving the rest of the method. Normal returning Win64 calls and valid
arguments/slot memory are required. Composing the write with a later query
requires the same returned slot, pool/hot-slot/index, stable storage and
lookup/context results, valid record selection and nonwrapping arithmetic.
Live storage selection, actual execution, complete registration control
flow and the authored-to-runtime numeric mapping remain unresolved.

The writer's actual `GetStrKey` call clears the Boolean argument. The current
key-source claims join that exact method identity to the provider's complete
normal false-Boolean program. Its anonymous carrier Int32 lane at `+8` is
checked only for zero: zero returns -1. On the nonzero route, a successful
typed dictionary request's referenced Int32 output is returned; a failed
request takes the actual counter path, forwards the counter candidate to the
same UInt64/Int32 dictionary setter request, and returns those candidate bits.
Those alternatives now reach the slot lane and subsequent query-key read.
They do not establish dictionary mutation, actual key selection or allocation
identity, hash values, deduplication or permanently unique keys.

The string-hash algorithm remains an independent recovery gap. The current
instruction subset treats the MOVZX form with an extended SIB index as a
complete unknown instruction boundary. That boundary prevents proving the hash
loop's input address or value flow. Typed dictionary lookup requests and independent
counter consumers can be proved separately; neither establishes equal hashes
for the span and managed-string conversion paths.

### Mission string-provider requests

`dynamic_mission_string_providers_native` owns names-based claims for
`TryGetStrKey` and `_GetUniqueKey`. Qualified metadata owners and ordinary
primitive/reference or explicit Int32-reference ABI records select the actual
calls. Complete primary instruction grammars close the entry, false IFix route,
initialization return, owned branch boundaries and balanced normal frames.

The nonnull string's concrete `System.String._stringLength` Int32 field joins
the caller's length read. Null or zero length returns false and writes -1 to
the original referenced output. The other normal path calls `_HashStrUtf8`,
then forwards its UInt64 return and the original output reference to the actual
context-bound `Dictionary<UInt64, Int32>.TryGetValue`; its Boolean return is
preserved. The dictionary's selected MethodSpec, unique generic pointer,
concrete definition and both argument records agree with the system's own
`m_hashToIntMap` field. Hash computation, conversion equivalence, dictionary
execution and retained runtime mappings remain unresolved.

`GetStrKey` is selected by its full ordinary return/parameter ABI and
static/instance role, rather than taking either same-named overload. Its
normal entry and initialized/uninitialized routes are closed across explicitly
owned unwind fragments. For the original Boolean false, all admitted paths
reach the same balanced frame: an anonymous carrier word equal to zero returns
-1, while the nonzero route returns either the successful referenced lookup
output or the actual counter candidate after a same-map setter request.
The declared `ReadOnlySpan<Byte>` value instantiation and observed mechanical
16-byte copy are proved separately; span instance fields, word meaning and
hash internals remain opaque. Saved Boolean, hash and candidate checks cover
all register aliases, and context/field argument records must agree.

The independent counter reads and writes the selected `m_uniqueKey` Int32
field. A negative stored value is reset to zero before incrementing; a
nonnegative value is incremented modulo two to the thirty-second power.
The incremented bits are returned and stored. At the maximum positive Int32,
the result becomes negative; a subsequent normal call follows the reset route.
This proves a bounded counter, not permanent uniqueness, thread safety,
deduplication or an authored numeric key. Normal returning Win64 callees,
valid receiver/output memory and preserved caller storage remain conditions.

### Mission state callback cache requests

`dynamic_mission_state_cache_native` owns the names-based callback claims.
The selected Mission and Quest callbacks join actual `GetMissionState` or
`GetQuestState` calls to the contextual `Dictionary<Int32, Int32>.set_Item`
request on their concrete `m_currentStateMap` field. Each enum definition has exactly one instance field, `value__`, with ordinary
Int32 ABI; static constants do not participate. The getter's returned bits are
passed as the dictionary value. The same successful `TryGetStrKey` referenced Int32
output is loaded for that setter and for `_EnqueueCompsForStr`.

Concrete inherited `manager`, its string-manager getter, the static player
getter and the player's `mission` field close both receiver chains. Shared
provider code owns the dictionary-context algorithm: field and MethodSpec
concrete definitions, generic parameter roles, raw argument records and the
unique actual generic pointer must agree. Separate complete primary/cold
instruction grammars prove false IFix, successful lookup, nonnull branches,
initialization returns, owned exception CALL starts and normal frame balance.
The getter-result interval and the post-lookup frame/local intervals exclude
admitted direct clobbers. Normal opaque callees must preserve caller storage;
unwind families establish ownership without proving unwind-code semantics.

The EventData parameter is an explicit reference to a closed generic value.
Its first generic argument is String, but its instance field layout remains
unproved: the actual first-pointer read is anonymous and must be a valid
String on the selected route. The callback does not read the event's declared
state enum fields. State getter computation, callback subscription/execution,
dictionary mutation, cache timing and enqueue effects remain unresolved.
Composing a setter request with the existing query requires the same concrete
cache/key and retained storage; it does not select a live entity or state.

### Mission returned stored-state getter

`dynamic_mission_stored_state_native` owns the names-based `GetMissionState`
normal getter claim. It preserves the original receiver and String argument,
passes them to the actual instance `GetMissionData` request with its Boolean
argument cleared, and reads `missionState` from a nonnull returned concrete
`MissionData` reference. That ordinary enum field has the same concrete
`MissionState` definition as the getter return, with only the Int32 underlying
instance field. If the lookup returns null, the closed return path preserves
its zero EAX bits instead. Both normal returns restore the complete frame.

Complete primary and owned IFix-cold instruction partitions close the entry,
actual patch and lookup calls, branch instruction starts, saved-register aliases
and field/default return paths. The selected patch returns false; opaque
returning Win64 callees preserve the saved receiver/String and frame, and a
nonnull returned reference must be valid for the field read. The cold ownership
does not prove unwind-code execution semantics.

The nested `GetMissionData` dictionary implementation remains open when its
concrete MethodSpec has no exact registered pointer candidate. A correct
String/class context alone does not select an Object/Object shared body: the
existing class-tag normalizer does not prove String-tag code normalization.
That producer/context/shared-target bridge remains a separate requirement.
Unsupported instructions in the owned normalizer are a tooling lead, not an
identity proof.

This supplies a direct conditional stored-field source for the Mission callback
cache request. It does not decode `GetMissionData` selection, classify a zero
return as an observed enum member, prove Quest getter behavior, or establish
live state, transitions or cache contents. Composing getter, cache setter and
query still requires the same concrete receiver/key and preserved storage.

### Mission and Quest typed state declarations

`dynamic_mission_state_symbols_native` binds static enum default declarations
to the actual qualified Mission and Quest state getter return definitions.
It reuses the protocol default-value decoder after checking the unique concrete
enum owner, sole ordinary Int32 instance backing, every member field's enum
identity and static/default flags, ordinary Int32 default type and exact member
roster. The shared decoder proves bounded compressed default framing; the
reader does not duplicate a numeric member catalog. Generated receipts retain
field/default provenance and every declared alias rather than choosing one.

The two typed declaration domains remain separate. A compared Int32 can have
a declared symbol only under the selected return domain, and an unlisted value
remains anonymous. This does not attach one enum to the whole cache, classify
query miss or a getter's default return as observed state, or authenticate an
authored source-to-symbol association. Runtime values, transitions and state
selection remain unresolved.

### Mission string lookup to owner requests

`dynamic_mission_string_enqueue_native` owns the independent names-based
`_EnqueueCompsForStr` consumer. Its ordinary Int32 input is preserved for the
actual contextual `Dictionary<Int32, NativeParallelHashSet<UInt64>>.TryGetValue`
request on the concrete `m_strCaredIdMap` field. The field and actual MethodSpec
share the complete raw type arguments and unique generic call pointer. The
successful route copies the same caller-local sixteen bytes and passes that
local address to the actual instance `_EnqueueOwnerComps` method. Its declared
value parameter has the same concrete generic value definition, owned generic
container and ordinary UInt64 argument as the lookup output.

The complete owned primary grammar and instruction-start branches close all
selected normal paths: initialization may occur, lookup miss returns without
an owner request, and hit makes the request before testing an anonymous Int32
lane of the typed pending reference. Register aliases, explicit local-copy
bytes and disjoint local/spill/return-address ranges are checked. Actual IFix
must return false, reached receivers must be nonnull, initialization and opaque
calls must return normally, and caller storage must remain intact.

This proves typed method/context identity and mechanical copy/address requests.
The referenced lookup output and downstream parameter must support compatible
normal indirect argument/local-storage ABI. Managed value size, complete
by-value ABI and instance field layout remain unproved; the sixteen-byte copy
alone proves none of them. The pending lane is not named a count, and the
post-request helper remains opaque. Dictionary implementation, component/entity
selection and actual enqueue or refresh effects remain unresolved.

### Authored quest predicate to mission-set requests

`dynamic_mission_state_set_native` owns a bounded registration continuation
following the authenticated key-return writer. It preserves the actual
`GetStrKey` returned Int32 bits in all aliases of the saved key register,
then requests the actual authored `MissionCondition.IsQuest` getter through
the retained condition proxy. A result equal to one skips the set request;
all other Int32 results request `HashSet<Int32>.Add` on the concrete
`m_missionStrSet` field with those same saved key bits. The alternate route
normalizes only SIL's low byte to zero; it does not zero the whole ESI value.

The actual set field, MethodSpec definition, ordinary Boolean return, VAR
parameter owner/ordinal, complete Int32 argument record and unique registered
call pointer agree. Complete bounded instruction partitions and fixed argument
bytes close the predicate branches and request path. All aliases of the system,
saved key and reached set receiver are checked against admitted clobbers.
The reached caller must retain the same valid system and authored proxy;
reached map/set/pool receivers must be nonnull, and all opaque callees must
return under the normal Win64 preservation/storage conditions. Preceding
indirect native-value calls retain their compatible ABI/size conditions.

This is a direct conditional Add request and a stored-key value transfer,
not a set mutation, completed registration entry or live Mission/Quest choice.
The source string index remains distinct from the returned key bits, and the
numeric returned key, native-value instance layout, lifecycle and actual
component/entity selection remain unresolved.

A bulk decoder's terminal exception does not authenticate its earlier emitted
rows. A selected interval must first pass contiguous raw-byte equality and
recognized instruction-boundary checks, and stop at the earliest rejection.
Unknown rows before a later truncation invalidate subsequent linear call and CFG
interpretations. The BeforeTick frontier therefore remains a bounded entry
prefix; neither discarding the terminal bytes nor collecting calls after an
unknown instruction proves its complete body or state-dispatch route.

### Quest state message to compatible record fields

`dynamic_quest_state_message_writes_native` owns two independently bounded
blocks inside the completely partitioned `Handle_QuestStateUpdate` primary.
One passes an opaque type-context call's returned pointer to the actual ordinary
QuestData constructor, then copies the message's `questId_` String reference and
`questState_` Int32 bits into the concrete record's `questId` and `questState`
fields. The on-disk tagged TypeInfo lane resolves to the same exact definition
as the constructor owner, but does not prove live resolution or successful
allocation. The receiver must be valid compatible QuestData, and opaque calls
must return normally while preserving the watched registers and storage.

The other block starts from a caller-local reference that must independently be
valid compatible nonnull QuestData. It saves the old state field's 32 bits into
the caller frame, then writes the current message's 32 bits into that same typed
field. Message state storage is ordinary Int32, not a sender enum. The target is
the exact Int32-backed QuestState definition returned by the qualified state
getter; this is a type-domain identity rather than evidence that a query later
selected this record. No range check or normalization of message bits is proved.

Both blocks retain exact source/target displacement and alias-preservation
checks. Their reachability from the complete handler entry, dictionary lookup
and insertion, String sharing, object allocation, live message execution,
state transitions, task order and callback effects remain unresolved. In
particular, a fresh field read after a call is not equated with an earlier read
without a separate storage-stability condition. The upstream asset check remains
an unexplained guard; its Assets behavior is outside this lane.

### Mission and Quest completion Boolean predicates

`dynamic_mission_completion_predicates_native` owns names-based normal-return
claims for the actual `IsMissionCompleted` and `IsQuestCompleted` consumers.
Under their independent false IFix selection and normal opaque-callee/storage
conditions, the former requests `GetMissionData` with the original String and
Boolean zero. Null returned data produces Boolean false. A valid nonnull returned
MissionData compares its actual ordinary Int32-backed `missionState` field to
the selected encoded constant; equality produces AL one, and inequality produces
AL zero. The field displacement is explicitly joined to the authenticated
concrete instance field, not merely to a neighboring layout.

The Quest predicate requests the actual qualified `GetQuestState` with the
original receiver and String, compares that ordinary enum's returned Int32 bits,
and uses SETE for Boolean AL zero or one. Both compare within the concrete enum
domain whose exact instance backing field and static default roster are checked;
all declarations sharing the compared value are retained as aliases. No label
is chosen by name or discarded to make a value unique. Complete owned partitions,
actual call targets, original register aliases and balanced frames establish the
selected normal paths. This proves the Boolean low byte; it does not assert that
the entire RAX register is zero-extended.

The Mission field-to-getter enum join is a type identity, not evidence that two
separate queries selected the same runtime data. GetMissionData selection,
GetQuestState's internal provider, source association, live completion, task
order and transitions remain unresolved. A matching enum declaration does not
turn the compared bits into an observed runtime state.

### MissionData display-list field return

`dynamic_quest_display_list_native` binds the concrete `GetDisplayQuestIds`
return and `m_displayQuestIds` instance field to the same closed List<String>
reference carrier, generic definition and ordinary String argument. The selected
false-IFix path calls the actual same-owner `RefreshIfDirty` method with the
original receiver, then returns that receiver's field pointer and restores its
balanced frame. Declared unwind chains establish the cold range's membership;
complete recognized primary and cold partitions keep the selected branch at an
owned instruction start. They do not establish execution of the patched route.

This composes a typed returned reference with an explicit normal-return request,
not the refresh algorithm. The receiver and watched frame must survive opaque
normal callees under the stated Win64 conditions. The dirty-field owner
separately proves selected zero-byte early return and
conditional clear-byte return using complete recognized declared ranges; this
still leaves mutation, list contents, ordering, cache freshness and live
execution unresolved.
The closed reference proof establishes a pointer representation rather than the
managed List object's size.

### Quest-related MissionData dirty-byte writes

`dynamic_quest_pause_dirty_native` independently binds the actual concrete
MissionData owner and ordinary Boolean `m_dirty` field for `AddPausedQuest` and
`RemovePausedQuest`. Complete primary partitions and selected paths prove a
constant byte-one write to that field. In the former, the first opaque call must
return AL zero, and a later call must return normally. In the latter, the opaque
call must return AL nonzero. Both require actual false IFix selection, a valid
receiver and the selected nonnull anonymous reference lane. Every receiver and
String-argument alias is preserved along the admitted paths under the stated
ordinary Win64 and watched-storage conditions.

The same owner also proves a selected `RefreshIfDirty` early return when this
field's raw byte is zero. The actual entry falls through into a declared owned
part; a complete recognized bounded prefix covers the field test, saved-register
restoration and balanced return without calls. This additionally requires the
explicit initialized-class, valid cache-pointer and anonymous signed-lane
selection conditions, whose patch meaning is not inferred. An existing
multibyte-NOP primitive also closes all declared owned range
partitions without widening the shared decoder. Under the separately stated
nonzero-dirty and valid context/reference conditions, a selected route makes
three opaque normally returning calls, reads two anonymous signed Int32 lanes
at reference-relative storage, and requires both values to be nonpositive. It
then stores byte zero to the same dirty field and takes the balanced return.
Those lanes are not named List.Count. Positive-lane loops, patch/cache
alternatives and the refresh or collection algorithms remain unproved despite
the complete recognized range partitions.

The reference lane and the calls through it remain anonymous in this claim.
Neither method names nor this dirty-byte store prove List<String> generic helper
identity, collection mutation, a live dirty observation or complete lifecycle
behavior. External consumers and later lifecycle effects remain open. The
AddPausedQuest and RemovePausedQuest claims stop at their selected byte-one
stores; their complete normal returns are not part of this proof.

### Quest pause typed requests

`dynamic_quest_pause_requests_native` owns independent names-based claims for
`PauseQuest` and the pre-dictionary dispatch of `Handle_UpdateQuestPauseState`.
The former's selected false-IFix path passes its original concrete system
receiver and String argument to the actual `_StopQuestListening` method, then
restores its balanced frame and returns if that callee returns normally. This
is a typed request, not a direct pause-field write.

The handler binds the actual message definition, its ordinary String `questId_`
and Boolean `isPaused_` fields. A false IFix result leaves AL zero through the
message comparison. With a valid nonnull message, a zero raw message byte
requests the actual `StartQuest` method with Boolean argument zero; any nonzero
byte requests the actual `PauseQuest`. The complete owned primary partition is
checked, but the proved selected routes stop at the common pre-dictionary join.
They do not prove full handler return, dictionary sharing, later processing or
paused collection mutation, or live quest state. Nested composition from the
handler's PauseQuest request to StopQuestListening additionally needs the
callee's independent false-patch selection. Ordinary Boolean metadata does not
prove normalization of the stored message byte; opaque callees must satisfy the
explicit normal Win64 and watched-storage conditions.

### Mission pause byte writes

`dynamic_mission_pause_writes_native` owns names-based claims for the selected
`PauseMission` and `Handle_UpdateMissionPauseState` direct writes. Complete owned
primary instruction partitions and branch targets establish the selected routes
from entry, through the actual false IFix test and typed requests, to the concrete
`MissionData.isPaused` Boolean field. Under the declared nonnull/helper-return
conditions, the former stores constant byte one. With the selected state getter
return bits unequal to two, the latter copies the message's ordinary Boolean
`isPaused_` byte exactly to the first returned data object. Boolean metadata does
not prove that every incoming byte is normalized.

Register preservation follows admitted paths and every RSI alias. The handler's
state-equal-to-two route writes SIL, so it is excluded from the data-pointer proof
rather than treated as harmless. These are selected pre-store paths, not complete
normal-return or post-store callback proofs. Opaque callees must return under the
stated ordinary Win64 and watched-storage conditions. The predicate getter's
later lookup and the object receiving the store are separate requests: composing
them as one object requires independent same-data and storage-stability evidence.
`GetMissionData` String sharing, actual handler execution, live pause state,
network effects and subsequent callbacks remain unresolved.

### Mission ready request boundary

`dynamic_mission_ready_native` owns the names-based claims in
`contracts/dynamic_mission_ready_native_claims.json`. It selects concrete
methods by type, method and assembly, then proves complete primary
instruction partitions and ordinary ABI records on the supplied native pair.
The shared `returnsAfterFalseCall` claim supplements its domain checks; it
does not substitute for the actual entry path, frame or receiver proof.

On the non-replacement path, `_CheckMissionSystemReady` requests the selected
player and reads its typed `GamePlayer.mission` reference. Both references
must be valid and nonnull. The entry restores its Win64 frame before the
actual tail request to that concrete receiver's `MissionSystem` getter.
The getter's non-replacement path returns constant true; it does not read a
stored readiness field. This is **direct conditional native request/return**,
not live readiness or a newly decoded state record. Opaque initialization
helpers must return normally, and both selected patch checks must return
false. Null receivers select an opaque helper followed by `int3`, outside
the admitted value-returning paths.

The IFix wrapper full type name is shared by multiple concrete assembly
owners. The reader retains all owner candidates and uses explicit assembly
identity plus the actual decoded CALL pointer and ordinary signature; a
fullname dictionary's last row cannot choose the helper. The mission field's
concrete definition must equal the tail getter's declaring type. Full entry
grammars close both patch-check prefixes and balance stack restoration;
branch targets must be real owned instruction starts. Method addresses and
body hashes are derived only into the generated audit. Input/source drift,
ambiguous ownership or changed code refuses publication and preserves the
previous valid receipt. Actual invocation, instance selection and patch
replacement behavior remain unresolved.

### MissionCondition stored comparisons

`dynamic_mission_condition_consumers_native` owns the independent comparison
consumer in `contracts/dynamic_mission_condition_consumers_native.json`.
It reuses the selected main-vector, scalar accessors and primitive ABI checks;
it does not re-decode the source corpus or copy the field catalogs.

On the admitted non-replacement route, `_UpdateConditionValue` requests an
Int32 value from `_GetCurrentConditionValue` using the original component
identifier's high-half hot slot and the anonymous cache's first index plus
the loop counter. The same supplied grid's MissionCondition vector yields
the stored `State` and `IsSame` Int32 fields. Only literal `IsSame == 1`
selects equality between State and the requested value; every other Int32
selects inequality. This is **direct conditional comparison flow**, not an
enum interpretation or a receipt that a task condition was evaluated live.

The consumer stores the new predicate in an anonymous cache byte and returns
whether that byte changed. Its Boolean return therefore does not directly
report the current predicate. The aggregation input byte, authored Conditions
group to cache ownership, numeric condition identity, provider value origin,
hot-slot to file/grid identity and runtime invocation remain **unresolved**.

The selected `_GetCurrentConditionValue` route now closes one provider
boundary: an opaque lookup returns an object whose Int32 field supplies the
key to an explicitly bound `Dictionary<Int32, Int32>.TryGetValue` request.
A true return selects the caller's Int32 output local; a false return
selects zero. Null dictionary receivers branch to an opaque helper followed
by `int3`, outside the admitted value-returning paths. The validator derives
the generic usage cell from the selected R9 instruction, authenticates its
MethodSpec and reciprocal concrete generic-parameter owners, and joins the
selected native pointer to the direct call. Ordinary Int32 instantiation
arguments, the Boolean return and explicit referenced output parameter are
checked from raw type records. This proves a conditional request/result
boundary, not the dictionary's internal implementation or live contents.
The opaque key identity and live dictionary/cache ownership remain unresolved.

The validator checks concrete owners and static/instance roles, ordinary raw
primitive ABI records, exact helper agreement with the source-owned vector
and getters, disjoint carrier spans, and complete instruction boundaries.
Its getter-to-predicate CFG follows both admitted comparison branches,
rejects unknown bytes, escapes, cycles and watched-register alias writes,
and excludes only the explicit patch-replacement edge. Strict ADD32 and
byte logical instruction composition preserves physical register writes;
normal Win64 nonvolatile preservation, valid pointers and normal returns
remain explicit conditions. The main table fast route must provide a nonzero
slot, the 32-bit index shift and position addition must not wrap, and the
selected record must be valid: equal raw index bits do not establish that
condition for arbitrary large values. Direct fixed-frame stores on the
admitted paths are checked for overlap with the saved provider Int32 local;
callee and indirect writes must not interfere with that local or frame bases.
Publication authenticates parser, dependencies
and native inputs before and after, with atomic output and alias protection.

### Erosion stored-value consumers

`dynamic_erosion_consumers_native` owns the independent selected native
consumers in `contracts/dynamic_erosion_consumers_native.json`. It reuses
the reviewed group, main-vector, scalar, root and index methods instead of
copying their catalogs or re-decoding the source corpus.

The selected `_FillPosListFromFB` path preserves its original typed
`List<UnityEngine.Vector3>` receiver. `PosList.Num` bounds the loop and
`PosList.index.Index` plus the loop counter addresses the same supplied
grid's Vector3 accessor. The decoder calls the named stored X/Y/Z getters
and writes their values to the same return slots as the named Unity
constructor parameters. The returned value's three axes are then copied
into the list-call argument. This is **direct conditional value flow**,
under the collector's non-replacement route and the generated accessor
fast paths; the opaque forwarding helper and nested callee do not prove
successful insertion, coordinate space, spatial units or runtime selection.

An independent `_GetErosionIdFromFB` path reads the selected root's
`ErosionCoreId` UInt64 getter and returns its result without a subsequent
write to the return register. It witnesses stored value to function return,
not the numeric value's target or a runtime entity relationship.

Names alone do not authenticate these signatures: the type-name helpers
omit raw ABI flags. The consumer checks exact primitive kind plus zero low
seven flag bits, and separately authenticates the explicit FB proxy,
ordinary List definition and Unity Vector3 value argument/return shapes.
Same-name nonordinary type records fail closed. Selected method identities,
concrete declaring owners and static/instance method flags are read from
the selected metadata. In particular, the constructor is an instance method:
its ordinary Single parameters occupy the x/y/z argument slots reflected in
the three named stores.

Direct calls come from a complete native instruction partition, never from
searching opcode bytes inside immediates or displacements. The source-owned
vector's full pinned window is checked, while its authenticated primary
function boundary supplies the call partition. The selected intervals reject
watched-register writes and unexpected calls between getter returns, saved
axis registers, stores and restored list arguments. The caller's FB carrier,
Unity return and list-value buffers occupy disjoint local frame spans.
The remaining **conditional ABI assumption** is normal Win64 calls preserving
nonvolatile receiver and saved-axis registers, with valid pointers and normal
returns. An opaque helper's success or behavior is still outside this proof.

Code windows and native inputs are checked against the supplied build;
parser, contract, dependency and native fingerprints must remain unchanged
before atomic publication. A missing build, mismatched ABI, output alias or
proof drift preserves the previous report and gives a bounded diagnostic.
The generated receipt belongs in
`reports/animestudio/dynamic_erosion_consumers_native_latest.json`.

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

The Erosion and Mission consumer contracts use the standard dependency-array
shape, with each entry retaining its relative contract path, schema and selected
method roles. Their readers and Mission key-source claims are validated through
the complete recursive dependency closure. Shape revisions preserve the proved
programs and layouts; generated native receipts authenticate the current parser
and dependency snapshot without hash-pinning tracked contracts.

### Quest state value sources

`dynamic_quest_state_value_source_native` independently closes the selected
`GetQuestState` normal-return value policy over all its declared owned ranges.
Both actual patch checks take their false branches; selected storage,
class-cache and compatible-record conditions admit eleven complete normal paths.
The direct compatible `QuestData` slot returns its authenticated typed state
field. The fallback requests an actual String-returning method with the original
String, checks the returned String's authenticated length field, and passes that
returned String to a second opaque slot request. A compatible `MissionData`
state matching the encoded comparison produces the encoded Quest-state result;
other selected returns produce zero. The owning enum reader retains every
matching declared alias rather than choosing one by name.

Both storage fields are authenticated ordinary closed Dictionary references
with String keys and their respective concrete record arguments. This establishes
representation and actual field displacements, not the identity or behavior of
the String-sharing dictionary API. The returned String method's name does not
establish a mission hierarchy. Normal opaque callees must preserve watched
registers and the local frame; slot values must independently satisfy stated
compatible-type conditions. Same-record identity, storage stability, provider
selection, mutation, capture ordering and live state remain unresolved. The
maintained claims reader gates concrete method/field/enum ABIs and complete owned
programs, and its atomic receipt authenticates dependencies and selected native
inputs before and after validation.

### Quest String return producer

`dynamic_quest_parent_string_source_native` independently closes the selected
normal return paths of the actual String-returning method requested by the
Quest state value-source consumer. All declared owned ranges have recognized,
continuous instruction boundaries. With its actual patch check false and the
stated nonnull storage/input conditions, three complete normal paths return
an opaque request's out-local pointer, an anonymous global pointer, or a saved
actual `System.String.Substring` return pointer.

The last path feeds the actual ordinary `System.String.IndexOf` call the original
String receiver, an anonymous global String argument, zero start, the
receiver's authenticated length-field bits and a declared comparison-enum value.
Its signed nonnegative Int32 return becomes the second Int32 argument to the
actual ordinary `Substring` call, whose first argument is zero and receiver is
the same original String. The returned pointer is saved in a fixed frame local,
passed to a subsequent opaque request and reloaded at the balanced return.
The String methods share the same concrete selected metadata owner; the enum
reader retains every matching declared comparison alias. The system storage
field is an authenticated closed Dictionary<String, String> reference.

These are conditional parameter and pointer transfers, not proofs of the String
methods' algorithms, delimiter contents, cache lookup or mutation, task hierarchy
or provider selection. Opaque request AL zero/nonzero branches are not promoted
to named dictionary hit/miss operations. Normal callees must preserve the watched
registers and saved local; the first out-address call must not retain a later
interfering frame alias. Returned local/global pointers require independent
String-or-null compatibility. Runtime execution, storage stability and live
hierarchy remain unresolved. Publication authenticates current dependency and
selected native snapshots before and after the proof and preserves old output
on refusal.

### Typed Quest action requests

`dynamic_quest_action_requests_native` proves two independent request boundaries.
A bounded, declared owned `SucceedQuest` suffix requests the actual
`RemovePendingQuestAction` and `SafeRunQuestAction` methods with encoded argument
bits matching the selected `QuestAction` declarations. It then restores the
caller frame and returns. The concrete ordinary enum definition and its sole
Int32 backing are shared by the source and recipients; every matching static
alias is retained. This suffix requires original system/String values in its
incoming saved registers and a valid original caller frame. Its branch
instruction start and entry bindings are authenticated, but the complete path
from `SucceedQuest` entry to that suffix remains unclaimed.

The selected false-patch `SafeRunQuestAction` path requests the actual static
Boolean `GameUtil.IsLevelAvailable` with a null String. When that return's low
byte is nonzero, both admitted initialization paths forward the original
system receiver, String and unchanged QuestAction low-32 bits to the actual
`RunQuestAction` method and return with a balanced frame. Complete recognized
owned partitions, raw argument/branch/frame checks and all watched register
aliases bound this normal path. Normal callees must satisfy the stated Win64
register and frame non-interference conditions.

A Boolean method name does not prove live level availability, and typed action
requests do not prove action execution or Quest completion. The queue branch,
its String/enum local copy, managed tuple size or indirect ABI, and receiver
preservation across its opaque helper remain separate pending joins. No Asset
field meaning or complete SucceedQuest entry behavior is recovered here. The
native receipt authenticates current source/dependency and selected native
inputs before and after publication; old producer proofs remain reusable.

### Generic collection proof boundaries

A declared closed generic field and its passed MethodSpec establish representation
and requested metadata identity separately from the actual generic native-pointer
binding. An empty exact candidate set does not authorize selecting a canonical
Object body by name. Likewise, open-generic installed field-offset records may
lack usable instance positions; a familiar collection field name does not label
a caller's anonymous stored lane. Keep signed lane comparisons separate from
valid-index, item-ordinal, Count and collection-mutation claims.

A direct byte-to-Boolean normalization can still have an independent boundary
when the callee's normal return is explicitly required to supply a compatible
concrete record. That condition must remain visible rather than being presented
as proved collection selection or ownership. Concrete non-generic field identity,
primitive ABI, raw read width and normalized low-byte return require their own
selected evidence; method names and passed context alone do not close them.

### Objective byte normalization

`dynamic_quest_objective_boolean_native` authenticates the complete owned
`IsObjectiveCompleted` partition and six selected false-patch normal paths.
The original String and Int32 argument bits survive all admitted normal calls.
An opaque first request returning a zero low byte, or a signed comparison of the
original Int32 against an anonymous stored Int32 lane selecting its greater-or-
equal branch, returns a zero Boolean low byte. Otherwise, an independently
compatible nonnull ObjectiveData normal return supplies the authenticated
`isCompleted` byte; compare-to-zero followed by SETNE produces a normalized
Boolean low byte. Other RAX bits are not normalized by this proof.

The system dictionary field, compatible QuestData's `questObjectives` closed
List reference and its concrete ObjectiveData Class argument, and the concrete
ordinary Boolean field are independently authenticated. The passed indexed-call
MethodSpec describes List.get_Item with an ordinary Int32 parameter and the
same argument's VAR return; this describes the passed context without selecting
an actual generic native API. The exact candidate set does not close that join.
The generic stored integer lane remains anonymous: installed open-generic
positions do not authenticate its ownership as size or Count.

Both opaque calls require their stated normal-return and compatible-record
conditions, plus valid memory and Win64 register/frame non-interference.
A signed less-than lane comparison does not establish a valid index or item
ordinal. Dictionary selection, indexed API behavior, item ownership, collection
contents or mutation, provider and source association, capture ordering and
live Objective completion remain unresolved. Atomic native publication rechecks
selected inputs and all proof dependencies before writing; previously passed
value-source and producer proofs are reused.

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


### Level predicate and getter value sources

`dynamic_level_predicate_value_sources_native` and its named claims contract
now authenticate the complete owned partitions of `GameUtil.IsLevelAvailable`
and its actual `GameLevel.get_isStarted` and `WorldInfo.get_curLevelId`
consumers. Qualified image/type identity and full ordinary parameter, return,
and static/instance roles select each actual method, including the patch helper
and concrete mscorlib String equality overload. Raw branch and call targets,
continuous instruction boundaries, balanced return frames, and all saved
receiver aliases constrain the selected normal paths.

The caller's false-patch path first rejects null compatible WorldInfo or
GameLevel pointers. A nonzero low byte from the actual started getter permits
a true Boolean low byte for a null input String or zero authenticated String
length lane. Otherwise the actual current-level-id getter result and original
input String are supplied to the actual static String equality request, whose
returned low byte selects true or false. This authenticates the request and
return selection, not the equality implementation. Boolean normalization
covers AL, not all RAX bits.

The getter value sources are independently conditional. On their selected
anonymous inline/header guard branches and normal callee returns, the started
getter compares the concrete GameLevel stored State Int32 with the declared
threshold using signed greater-or-equal and normalizes AL. The enum's sole
ordinary Int32 instance underlying field and every declaration alias remain
explicit; neither threshold comparison nor aliases prove lifecycle order.
The id getter reads the concrete WorldInfo current-level reference, returning
null for a null reference or the compatible GameLevel's stored ordinary String
id pointer. Each metadata field offset is explicitly joined to the proved raw
body displacement.

A registered GameWorld type context and its concrete static worldInfo field
are authenticated, but the intervening anonymous class-header slot does not
prove initialized static storage. Repeated reads from the same on-disk
context slot do not establish identical or stable runtime records. The
getter's anonymous inline cache/epoch guards do not prove patch-cache or
initialization semantics. Live availability, actual current level, runtime
started state, record stability, and lifecycle transitions remain unresolved.
The independent native publication now uses `dynamic_native_provenance` for
its own contract and the provider contract it actually reads, alongside its
Python source closure and explicit selected native inputs. The shared World
helper snapshots the direct declared JSON roster, checks resolved paths and
content again at the end, and supplies every input to publication alias guards.
The public native API applies the same JSON checks before returning validated.
It also copies and authenticates the supplied native fingerprint manifest before
and after proof: that manifest must correspond exactly to the explicit selected
GameAssembly, metadata, and sibling UnityPlayer paths, and neither the selected
physical path set nor the caller's manifest may drift. The CLI retains a wider
interval through atomic publication. Imported JSON
resources that are never read on this path are not made proof inputs.
Missing, mismatched or detected drifting inputs preserve prior valid output.
The complete family gate separately authenticates its broader JSON scope.

The provenance review also found the same real omission in the maintained
Mission/Quest consumer CLIs: their validators read declared provider contracts,
but the old CLI snapshots included only their own JSON. These publication and
API paths now share the same direct-input gate. Old body and typed-field proof
results remain useful, while an old receipt without the read JSON fingerprints
must not be presented as a current dependency-contract authentication. Adding,
removing, relocating, or changing a read dependency invalidates that receipt;
this is a source/proof boundary, not a new native behavior claim.


### Conditional GameLevel State writes

`dynamic_level_state_writes_native` and its named claims contract authenticate
independent direct writes in Load, Start, Ready and Unload. Each claim covers a
continuous owned entry prefix, both admitted initialization paths, the actual
qualified patch request and its false branch, and the full Int32 store through
the saved incoming receiver. Ordinary instance ABI, the concrete field owner,
the enum underlying representation and all declaration aliases are checked
against selected metadata. Register preservation includes partial aliases;
pre-store opaque callees require normal Win64 preservation and noninterference
with the active frame and receiver storage.

Load selects a comparison observing a zero State lane immediately before its
store; this is not an atomic transition. Start additionally selects a zero low
byte from the actual started getter requested on the saved receiver. That
request does not establish the stored pre-call State value, because replacement
and context paths remain possible. The other stores do not require an incoming
State value. Following requests, complete normal returns, live object identity,
initialization semantics and lifecycle order remain unresolved. This consumer
uses the same direct JSON and explicit native before/end proof gates as the
other maintained World consumers; it does not enlarge their source schemas.


### Selected loaded and ready predicates

`dynamic_level_state_predicates_native` authenticates the ordinary instance
Boolean getters isLoaded and isReady against the same concrete GameLevel State
field and its Int32 enum representation. The former selects the actual qualified
patch request's false result and returns a normalized low byte for signed State
at least the Loaded declaration. The latter selects its anonymous context and
header guards, including either admitted initialization path, and returns a
normalized low byte for signed State at least the Ready declaration. Both
proofs include continuous complete owned partitions, receiver alias preservation
and balanced normal-return frames. Full RAX normalization, guard meanings and
live loaded/ready status remain unresolved.

The report also computes a conditional mathematical table for the separately
reviewed writer declarations and these signed comparisons. This table is not a
new authentication of the writer bodies. Applying it to a store/getter pair
requires the independent writer proof to be current, the same concrete receiver,
unchanged State storage through the comparison, the getter's selected path and
normal callee/frame noninterference. Neither method names nor enum declarations
establish lifecycle order, reachability or runtime object identity.


### Installed-build Collision observer port

The Collision declaration families authenticate the selected installed engine
and managed inputs through the ordinary `collision_capture_prepare` path.
Current witnesses cover the compiled query-registration count, short accessor
leaves, inline attachment sites and refactored helpers. Generated declarations
live under `reports/runtime_capture/collision-current/`; the earlier profile
remains historical. Release compilation and private-buffer forwarding, hidden
returns, mixed arguments, LastError, C++/SEH unwind, nested stop and bounded-read
checks pass. These checks establish no live ABI, worker ownership, continuous
object lifetime, query hit or impulse.

`collision_model_source_native` owns a narrow source filter: named
Grids/UniqueId/Model/PathHash accessors and the vector builder establish only
the selected table fields, inline stride and hash position. Preparation re-reads
current VFS source frames through that layout. Other Model fields, authored
prefab names, CAB/PathID and cooked-mesh joins are not carried over from the
historical inventory. A path hash remains a filter until runtime enrollment
supplies an actual identity.

The current packed ECS layout adds anonymous trailing words to ordinary multi
and single records, while single terrain retains its framing. Shape userdata
moves the surface/secondary fields and carries an anonymous word. The ordinary
secondary bit does not describe complex-mesh auxiliaries. The runtime decoder
requires readable copied userdata before comparing values; unreadable fields
are gaps rather than zeros. Current selector-to-callback identities are proved
through descriptor, slot assignment and publication, including changed selector
assignments. The ECS capture resource bodies own their current access path
independently of the broader stored Streaming contracts; those older contracts
still fail closed on this build.

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
  offsets and no established runtime use.
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
meaning beyond the IdComp join; resource state conditions; live Sludge tile
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
2. A selected consumer of the ResourceGroup state scalars. The Sludge
   `SurfTileIDs` group-to-primitive/list and load-check-to-apply joins are
   authenticated conditional native consumers; a live Sludge/grid/tile
   receipt and deferred callback behavior remain the next Sludge boundary.
3. Runtime receipts (exact build, caller, file identity) for MapConfig and
   streaming-config selection, grid and area activation, version phase and
   ban results, portal AOI and spawn, and the squad teleport `pos` source.
4. The remaining nested main fields and positive table targets, then an
   allocator-backed residual/padding proof and `DataMask`.

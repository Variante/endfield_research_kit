# DynamicStreaming main grids and area records

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 3, world lane.** The main `fb_main_*.bytes` and area
`FBStreamArea.bytes` roots have selected-build generated FlatBuffer accessors.
Their envelopes and root framing belong to
[`dynamic_streaming.py`](../../scripts/game_data/dynamic_streaming.py).
The reviewed main [vector contract](../../scripts/game_data/contracts/dynamic_main_vector_native.json)
and [native audit](../../scripts/game_data/dynamic_main_native.py), and the area
[record contract](../../scripts/game_data/contracts/dynamic_stream_area_native.json)
and [native audit](../../scripts/game_data/dynamic_stream_area_native.py),
recheck explicit installed binaries and authenticated VFS identities before
naming selected-build fields.

## Main grid vector widths

The earlier main reader used a four-byte element width for every `SingleGrid`
vector. That was neither a universal lower bound nor an exact width. The
generated indexed accessors and vector builders agree on the element size for
each field: four fields carry `Int32` values, most carry inline structs, and
one carries table references. The selected widths range from one byte to a
much larger fixed struct. The contract records every field name, width,
alignment, method identity, and pinned code window; the generic reader now
uses only a one-byte lower bound until that native contract validates.

Every current main payload is rejoined to the VFS ledger by path, length, and
FileDataMd5. The selected-width audit bounds all observed grid vector count
words and bodies without overlap, including the byte-sized vectors the old
reader could overrun and the inline structs it used to undercount. This is
**exact vector extent**, not whole-file closure: grid tables, string bodies,
padding, and nested record fields still need their own ownership checks.
Changing counts and the complete width census are in the generated audit
under `reports/animestudio/`.

The `DataMask` field remains a raw `UInt64`. The current selected-width audit
retests the old proposal that its bits simply indicate present or nonempty
vector fields, under several base shifts. None matches the whole corpus, so
that proposal remains rejected. It does not supply an alternative meaning.

## DataIndex references within a grid

The selected-build `FBDynamicSceneDataIndex` builder creates a 16-byte inline
record: `IsInvalid` at byte zero, followed by three padding bytes, then
`Type`, `Grid`, and `Index` as four-byte values. The generated getters confirm
the three integer offsets. The reviewed [DataIndex contract](../../scripts/game_data/contracts/dynamic_data_index_native.json)
and [native audit](../../scripts/game_data/dynamic_data_index_native.py)
validate these witnesses and the main vector contract against explicit native
inputs before decoding current main files.

Every valid `DataIndex.Grid` in the authenticated current main corpus equals
its **containing `SingleGrid.UniqueId`**, which is sometimes different from the
file root's `UniqueId`. For each observed `Type`, the selected-build
`EDynamicSceneData` member has the same numeric value and name as a
`SingleGrid` vector accessor. The `Index` values partition that named vector
exactly within each grid: no observed element is skipped or indexed twice.
This is a strong stored reference relationship across the main corpus.
`DataIndex.Type` is exposed as an
`Int32` by the generated getter; the enum association rests on numeric/name
agreement and the complete grid-local partition.

Counts alone cannot always identify the target vector. In the current files,
`NavModifyAreaComp` and `ErosionRootComp` have indistinguishable count/index
partitions, as do `TreeRootComp` and `NatureResourceComp`. The native enum and
vector accessor names distinguish those candidates; the audit retains the
count-only rivals in its local report rather than silently promoting that
weaker evidence. The report also holds changing counts and the full Type
census under `reports/animestudio/`.

## Selected data-type to system route

The selected `DynamicStreamingScene.GetSystemByDataType` body calls a bounded
native jump-table route, then passes its result to `GetSystem`. The separately
registered `GetSystemTypeByDataType` switch agrees with that called route for
every member of `EDynamicSceneData`. The reviewed [route contract](../../scripts/game_data/contracts/dynamic_system_routing_native.json)
and [route audit](../../scripts/game_data/dynamic_system_routing_native.py)
recheck both code paths and join their outputs to the authenticated current
`DataIndex.Type` census. Every Type observed in current valid records has a
nonzero, named system route. For the count-only ambiguous pairs above, the
routes are distinct: NavModifyAreaComp selects NavmeshModify while
ErosionRootComp selects Erosion; TreeRootComp selects Tree while
NatureResourceComp selects NatureResource. The full route table and changing
record counts are in the local audit under `reports/animestudio/`.

`EDynamicSystem` is byte-backed in the selected native registration. Reading
its default bytes as signed compressed `Int32` produced false negative enum
IDs; the route audit now decodes its selected primitive type before naming a
system. `EDynamicSceneData` is `Int32`-backed and retains its earlier numeric
IDs. A callable route establishes what this code would select for a supplied
data-type value.

## RootComp groups and the selected consumer

The selected `FBDynamicSceneRootComp` builder makes an 84-byte inline record;
its `Comps` field is a 24-byte `FBDynamicSceneDataGroup` at offset eight.
The group contains a 16-byte `FBDynamicSceneDataIndex` at offset zero, then
`Num` and `TotalInGrid` as four-byte integers. The generated builders and
getters, the main vector width contract, and the reviewed
[RootComp contract](../../scripts/game_data/contracts/dynamic_root_comp_native.json)
and [audit](../../scripts/game_data/dynamic_root_comp_native.py) check that
layout against explicit selected native inputs.

In every authenticated current main grid, each `RootComp.Comps.Index` has
`Type=DataIndex`, `Grid=SingleGrid.UniqueId`, and a nonnegative `Index`.
`Num` is positive, `TotalInGrid` equals the grid's `DataIndex` vector count,
and the groups' `[Index, Index+Num)` spans are disjoint and tile that vector
exactly. This is the authored first hop: `RootComp` groups partition the
`DataIndex` directory; each directory row then addresses a component in its
same-named grid vector as described above. The embedded group's `Type=DataIndex`
identifies the directory, not the target component type.

The remaining RootComp bytes have a selected native layout: `State` is a
`UInt32` after `Type`, `NeedLazyDestroy` is a Boolean after `Comps`, and the
last 48 bytes are `FBDynamicSceneVisibleDesc`. Its two consecutive
`FBDynamicSceneDataGroup` fields are `VisibleStateGroup` and
`VisibleAreaGroup`. Both embedded indexes carry
`EDynamicSceneData.PrimitiveInt`, refer to the containing grid's ID, and have
`TotalInGrid` equal to that grid's `PrimitiveIntList` count. The selected
enum names the group type, while the selected grid accessor names the
four-byte target vector; `PrimitiveInt` has a different numeric ID from
`PrimitiveIntList`'s field index. The similarly named
`SceneVisibleStateInts` and `SceneVisibleAreaInts` vectors are not the targets
of these group spans.

Across the authenticated current main files, both groups' nonempty spans
stay within `PrimitiveIntList` and never overlap. Every `VisibleAreaGroup` is
nonempty; `VisibleStateGroup` is usually marked invalid with zero elements.
The two groups alone leave some primitive integers without an owner, so they
do not partition the vector. The resource and Sludge groups below close this
stored ownership question for the current corpus. `State` has no variation in
this corpus, and the sparse other values do not establish a visibility rule.
The generated local audit records their counts and value distributions.

There is now a selected native consumer for those two groups. The
`DynamicSceneEntitySystem.RegisterEntity` path passes its typed state and
area entity controllers and the grid to
`SceneVisibilityControllerBase.Register`. The controllers' respective
`GetValidIndexGroup` overrides select `RootComp.VisibleDesc.VisibleStateGroup`
and `VisibleAreaGroup`. Base `Register` calls that virtual group lookup,
checks the group's `Num`, starts from its embedded `Index`, and reads each
four-byte value through the grid's `PrimitiveIntList` vector slot. The
reviewed contract checks the typed controller fields, inheritance, native
method windows, call sites, root and group offsets, and the primitive-vector
helper. The vector selection comes from that native slot, not from the stored
group `Type` number. This upgrades the target-vector link from a matching
name and corpus shape to a **direct conditional consumer**. Whether a given
grid actually takes this path remains open.

A separate [scene-local area join](../../scripts/game_data/dynamic_visibility_area_join.py)
rechecks both native audit reports, their selected contracts and installed
inputs, the shared VFS input set, and every compared dump's source hash. For
every current main file under `Scene/<name>/`, each value selected by
`VisibleAreaGroup` belongs to that scene's `FBStreamArea.TotalAreas` ID set.
This includes the shared zero ID; nonzero values are authored area IDs
in the matching area file. Main files under `Extra/SpaceshipCabins/` have no
paired area file, so their zero values remain outside this join. The generated
report keeps changing counts, scenes, and IDs. The membership is a **stored
cross-file relationship**; it does not show which area is active during play.

A separate [scene-local state join](../../scripts/game_data/dynamic_visibility_state_join.py)
rechecks the RootComp native report and every current main dump hash, and
requires a fresh Persistent export from the selected installed game. The
authored `VisibleStateGroup` integers in `Scene/<name>/` main files all occur
as indices in that scene's exported `Json/MapConfig/<name>.json` `sceneStates`
map. These indices therefore resolve to named scene states in the stored
configuration. Index zero is a named state in the matched configs, not a
generic invalid marker. Some scenes with no authored visible-state values do
not have a `MapConfig` export; the join needs a config only for scenes whose
values it names. The current state join also finds both auxiliary grid
vectors, `SceneVisibleStateInts` and `SceneVisibleAreaInts`, empty; this
supports the direct native finding that the nested visible groups instead
address `PrimitiveIntList`. The generated report records the changing values,
names, scene set, and counts. This is a **stored cross-file relationship**;
it does not report which indices became active.

The maintained [MapConfig reader](../../scripts/game_data/schemas/map_config.py)
now checks that scene-state indices are distinct positions in a 32-bit mask
and that each condition row names a distinct key in `sceneStates`. The
[JsonData corpus gate](../../scripts/game_data/jsondata_corpus.py) validates
every current MapConfig against the authenticated VFS export with those checks.
Some configured state names have no condition row, so the condition list is
not an exhaustive state catalog. The selected native
`BaseGameScene.CalculateSceneStateMask` body reads both fields through its
`m_mapConfig`, resolves condition-row names in `sceneStates`, shifts a mask
bit by the resulting index, and branches on a condition result when updating
the state lists. This identifies an authored source for runtime state indices;
it does not establish the result of any condition for a particular save or
session. The selected `BaseGameScene.SetSceneState` body independently looks
up a supplied state name in the same dictionary, updates the mask and lists
according to its Boolean input, and can call the same setter. A state without
a condition row therefore still has a named update route; whether and when
that route is called is a separate question.

The [visibility runtime claims](../../scripts/game_data/contracts/dynamic_visibility_runtime_claims.json)
recheck the selected native method bodies by name rather than pinning this
client's addresses. The contract also checks `SetSceneState`'s dictionary
read and setter call. `BaseGameScene.DoUpdateSceneState` calls the calculation
before `SetSceneStateMaskAndList`. The setter stores its state-index-list
argument and passes that field as the second argument to
`DynamicStreamingScene.SyncSceneStates`, with the scene's dynamic-streaming
object as the receiver. `SyncSceneStates` reads its
`m_activeSceneStateIndices` field and calls the entity and resource systems'
`UpdateStateIndex` methods. Each update method reads its typed state
controller and calls `SceneVisibilityControllerBase.UpdateIndex`.
`InitSceneVisible` in both systems reads the state and area controllers and
calls the base `InitActiveSet`. The parallel area route is visible through
`DynamicStreamingScene.OnAreaChanged`, both systems' `UpdateAreaId`, and
their area controllers. The generated claim audit records method identities
and body hashes for the explicitly selected installed binaries. This is a
**direct conditional native controller route**: the named reads and calls are
checked, including the nested configuration reads and the setter's
list-to-sync argument handoff. The selected disassembly shows the list
produced by calculation passed to the setter, but a later changed body needs
that handoff inspected again.

The same native claims now trace how a `MapConfig` can reach that route.
`DataManager.MapConfigTable.TryGetData` first checks its typed cache. On a
miss, it calls `ResourceRouter.GetMapJsonConfigFullPath`, whose selected body
loads `Data/Json/MapConfig/` and `.json` literals, then calls the shared
`DataManager.LoadJson` implementation and caches a non-null result. The
table's declared value and output type is `MapConfig`; the shared generic
method pointer by itself does not identify a unique instantiation. The
authenticated JsonData export has the matching original path family, so this
closes the static source route to the authored config files without claiming
that a particular file was requested at runtime.

The current authenticated export also supports the lookup key: every decoded
`LevelConfig.mapIdStr` names an exported `MapConfig` file, each
`MapConfig.mapIdStr` equals its filename stem, and every exported MapConfig
is named by at least one LevelConfig. Several levels can share a map. This is
a **stored cross-file key relation**; it does not identify a live selected
level or prove that the loader successfully read that file.

Normal `GameLevelLoader.LoadingPipeline.LoadBeginStep.DoPrepare` gets a
`LevelConfig`, obtains its map ID, asks `_TryLoadMapConfig` to use that table,
and stores the returned object in the pipeline's `m_mapConfig` on success.
`LoadSceneStep` later reads that field and, when the map ID differs, stores
it in `BaseGameScene.m_mapConfig`, unregisters old condition listeners,
reinitializes scene state, and notifies the dynamic scene. Seamless loading
uses the same table in `PrepareStep`, stores the result in its own
`m_mapConfig`, and passes that field from `PreloadSceneStep` to
`BaseGameScene.TryChangeMapConfig`. The latter compares incoming and current
`mapIdStr`; its change branch unregisters listeners, replaces the config,
calls `_InitSceneState`, and calls `_OnMapConfigChanged`. Initialization
registers condition listeners before `DoUpdateSceneState`;
`_OnMapConfigChanged` forwards to `DynamicStreamingScene.OnMapConfigChanged`,
which can refresh registered entities. These are **direct conditional native
routes** for the selected unpatched bodies. The named contract checks the
lookup, typed field reads and writes, argument handoff, path literals, and
calls; the generated audit carries their body hashes. Cache hits, failed
lookups, equal map IDs, null systems, and iFix branches may take other paths.
The chosen live scene, evaluated condition results, active-state list, and
whether a particular stored RootComp group is registered or evaluated in play
remain open.

The authored streaming asset path has a separate, now verified source route.
Every current exported `MapConfig.streamingMapConfigPath` resolves through the
fresh StreamingAssets asset map to one exported MonoBehaviour by its container,
source file, and Unity PathID. The original object index resolves each matched
MonoScript to `Beyond.Gameplay.Streaming.StreamingMapConfig`; this is stronger
than assigning the class from matching JSON fields or an asset name. A full
class census also finds streaming-config assets absent from every current
MapConfig reference. They are retained as authored but unselected candidates,
not silently dropped from the catalog. The objects' `mapSceneName`,
`exportScenePathRoot`, and `streamingDataPathRoot` agree with their authored
container paths. Several MapConfigs share one streaming asset, so the path is
a many-to-one relation. The
[config join](../../scripts/game_data/dynamic_streaming_config_join.py)
rechecks identities, export freshness, and native-report provenance and keeps
the changing inventory in its generated report.

The selected unpatched `GameScene._ExtractSceneConfig` body reads
`MapConfig.streamingMapConfigPath` through `BaseGameScene.m_mapConfig`, builds
the current platform asset path under
`Assets/Beyond/DynamicAssets/Scenes`, calls the asset loader, and stores the
result in the typed `BaseGameScene.streamingMapConfig` field. Its shared
generic loader body is instantiated as `System.Object`, so that generic
pointer alone does not prove the target class; the typed field and original
object index supply independent class evidence. `get_mapSceneName` reads the
loaded object's `mapSceneName`. `CreateDynamicStreamingScene` passes that name
to `DynamicStreamingScene.InitScene`, which builds a base path with the
DynamicStreaming root, current data-platform folder, and `Scene`, then passes
it to `DynamicDataLoader.SetBasePath` and
`DynamicSceneVersionBanSet.LoadFromBasePath`. The reviewed
[runtime claims](../../scripts/game_data/contracts/dynamic_visibility_runtime_claims.json)
recheck these named reads, writes, literals, and calls. The argument-to-path
handoffs were inspected in the selected body disassembly; the simple claims
do not prove full dataflow after a changed body.

The selected `DynamicDataLoader.SetBasePath` body initializes a
`DynamicSceneFbDataLoader` with the scene base path and sets up separate
`fb_init` and `fb_streaming` filename templates. The main loader's `Init`
body uses an `fb_main` template; its `GetPath` reads stored character offsets,
replaces indexed digits from a packed grid value, and returns the resulting
path. The selected `GetGridData` path calls the
`DynamicSceneFbDataLoaderBase<UInt32, FBDynamicSceneChunkData>` instance and
reads a chunk's grid vector and each grid's `UniqueId`. `AddChunkRef` can
request the selected typed base loader's `TryLoadResource`; that body calls
`VirtualFileSystem.ReadFileByLowIO`, while the
derived `GetFbData` reads the tracked handle as a FlatBuffer chunk and checks
its data and streaming version getters. The class-instantiation selector in
the reviewed claims distinguishes this body from the other generic base
instance. `DynamicSceneVersionBanSet.LoadFromBasePath` separately names the
`fb_version` path. These are **direct conditional native file-selection and
read routes**, not receipts that a particular grid file was requested or
accepted in play.

## Version root and entry framing

The earlier generic `fb_version` reader treated all three root fields as
scalars. The selected [version contract](../../scripts/game_data/contracts/dynamic_version_native.json)
corrects that layout: `FBDynamicSceneVersionData` field zero is an `Entries`
vector, followed by signed `Major` and `Minor` scalars. The generated indexed
accessor and vector builder agree on a 16-byte, eight-byte-aligned
`FBDynamicSceneVersionEntry`. Its getters name a `UInt64 Id` at the start and
an `Int32 Version` after it; the remaining four bytes are alignment space.
The contract checks the accessor identities, selected code windows, vector
stride, builder width, and field operands against explicit installed binaries.

The [version corpus gate](../../scripts/game_data/dynamic_version_native.py)
rejoins every current `fb_version.bytes` dump to the authenticated VFS ledger
by path, length and MD5. Its selected-width reader finds each vector count
word immediately after the root and each vector body ending at payload EOF.
All current roots carry a non-null `Entries` vector; most are empty, while a
populated scene file contains entry records. The generated report records
changing counts, values and source names under `reports/animestudio/`.
The generic reader uses only a one-byte vector lower bound until the selected
native width is supplied, avoiding an ungated 16-byte assumption.

The [version Id-domain gate](../../scripts/game_data/dynamic_version_id_domain.py)
uses the selected version, main-grid, DataIndex, and RootComp native contracts,
then streams all current `fb_version` files and the main files for each
populated scene through AnimeStudio. It rejoins every streamed file to the
authenticated VFS path, length, and FileDataMd5. In each selected main grid,
valid `DataIndex` references partition its `IdComp` vector, so the compared
values are indexed `IdComp.UniqueId` fields rather than an arbitrary byte
search. Every current populated `fb_version.Entry.Id` occurs in an indexed
`IdComp.UniqueId` of the **same scene**. Additional same-scene `IdComp` values
have no version entry, so the version vector is a subset, not an exhaustive
entity inventory. No version entry equals a same-scene main-grid `UniqueId`;
an independently authenticated `map01` IdComp control has no overlap. The
changing counts and source receipts are in
`reports/animestudio/dynamic_version_id_domain_latest.{json,md}`.

The selected [active-version source contract](../../scripts/game_data/contracts/dynamic_active_version_native.json)
and [validator](../../scripts/game_data/dynamic_active_version_native.py)
check a conditional enter-game login chain. The outer coroutine passes its
`<loginRespRef>5__5` object reference to `_NetConnectAndGSLogin`; the inner
coroutine retains that reference, calls `NetClientManager.LoginAsync`, and
stores the returned `HGNetSessionLoginYield`. On its success branch,
`GetResponse` reads that yield object's typed `m_resp` field and the inner
coroutine stores the returned `Proto.MSG_B1` in the same reference's `value`.
A selected `HGNetSession._SessionLoginThreadTask` route calls
`_ReadMessageInSessionThread` with a `NetResponse` output. That read method
passes the received bytes to `NetUtil.GetNetMessageFromDataBytes`. On the
selected decoder route, `Google.Protobuf.ParsingPrimitivesMessages.ReadRawMessage`
parses a typed `Proto.CSHead`; its `msgid_` is used for a
`NetUtil.s_sc_id2MessageType` lookup. In the selected registration body,
`FastRegisterMessage` resolves `Proto.MSG_B1` to a `System.Type` and calls
`RegisterSCMessage` with literal ID `1`; that method `TryAdd`s the pair to
the same dictionary. This establishes the authored ID-to-type route when
registration runs through its unpatched path. A mapped type is instantiated and
`Google.Protobuf.MessageExtensions.MergeFrom` reads its body. The decoded
message is stored in `NetResponse.msgBody`, beside its `headMsg`.
The session task requires a successful read and `NetResponse.get_msgId() == 1`,
then loads `msgBody`, checks it against the `Proto.MSG_B1` type usage, and
passes that object to `_HandleLoginEncryp`. After that method succeeds,
the same object is passed to `HGNetSessionLoginYield.SetSucceed`, which stores
its typed argument in `m_resp`. The outer coroutine later reads `value`
for a guarded `PlayerInfoSystem.SyncBranchVersion` call. On the sync method's
unpatched, nonnull-message route, it reads the string field `f14_` from the
typed message and passes it to `set_branchVersion`, which stores
`m_branchVersion`. The selected resolver
`DynamicSceneVersionBanSet._ResolveActiveVersion` then reads through
`GameInstance.get_player`, `GamePlayer.playerInfoSystem`, and
`PlayerInfoSystem.get_branchVersion` to the stored `m_branchVersion` string.
The resolver passes that string to `GlobalOptions._ParseVersion`, whose
selected body loads the exact regular-expression literal
`^v(\d+)d(\d+)(d(\d+))*?$`, calls `Regex.Match`, and makes three integer
parse calls. The pattern starts with `v`, requires two `d`-separated decimal
components, and permits further `d`-prefixed decimal components. The selected
group calls feed group 1 to major, group 2 to minor, and nonempty group 4 to
phase. The parser first zeroes all three outputs. A failed major parse exits
with zeros; a failed minor parse can leave the successfully parsed major;
a failed nonempty phase parse resets all three outputs. An absent or empty
phase group leaves phase at zero. The exact capture returned for multiple
repeated `d` segments has not been exercised in the selected game runtime.
It initializes active major and minor to zero and active phase to the
full-phase sentinel. When at least one parsed output is nonzero, it copies
all three outputs to the ban set's active fields; the all-zero path retains
the defaults. A partial major output from a failed minor parse can therefore
still be copied when that major is nonzero. Null or all-zero parser paths
retain the defaults.
Thus a matched two-component value with a nonzero major or minor would assign
phase zero, while `v0d0` would retain the full-phase sentinel. This is a
selected-body implication, not an observed branch-version value.
This is a **direct selected-build source chain with conditional guards**, not
a live player-version value or evidence that a particular version file was
accepted. The response-to-`Proto.MSG_B1` check is a runtime cast: its presence
does not prove that a live server response passed it. Registration execution,
live network bytes and values, selected patch branches, and live accepted
version strings remain open.

The [selected ban-set contract](../../scripts/game_data/contracts/dynamic_version_ban_native.json)
and [validator](../../scripts/game_data/dynamic_version_ban_native.py) check
the named fields, method signatures, full code windows, direct call targets,
and controlling branches against the installed binaries. The selected
`DynamicSceneVersionBanSet.LoadFromBasePath` route first resolves its active
major, minor, and phase. It exits before version entry processing when the
phase is at least the full-phase sentinel, or when the path/file/root checks
or version root major/minor comparisons fail. On its successful unpatched
entry loop, `Entry.Version > m_activePhase` selects a candidate; the loop
passes that entry's `UInt64 Id` to `m_banned`, a `HashSet<ulong>`, through
`HashSet.Add`. It sets `m_needCheck` when at least one candidate was processed.
That selection does not by itself prove a later query will return true.

On the checked unpatched query route,
`DynamicStreamingScene.IsEntityVersionBanned(globalId)` reads its
`m_versionBanSet` and passes the same `UInt64` argument to `IsBanned`.
`IsBanned` returns false when `m_needCheck` is false; when it is true, it
returns `m_banned.Contains(globalId)`. Its `Reset` branch clears the set and
resets the flag; the selected `LoadFromBasePath` body has no direct
`HashSet.Clear` call. IFix `IsPatched` checks can route the loader and both
query methods through wrappers, so this consumer conclusion is **direct but
conditional on the selected unpatched branches**. The local receipt is
`reports/animestudio/dynamic_version_ban_native_latest.json`. The stored
same-scene IdComp join above does not establish which version file, active
phase, patch state, or ban result occurs in play; ban-set reuse across loads
also remains open.

## Paired init and streaming roots

The [auxiliary pair gate](../../scripts/game_data/dynamic_aux_pair_corpus.py)
rejoins every current `fb_init` and `fb_streaming` dump to the authenticated
VFS ledger by path, length, and FileDataMd5. Every current filename has its
other-family counterpart, and both files pass the separate compressed-envelope
and eight-field FlatBuffer framing checks. The paired root scalar fields zero
and one agree; vector fields two and three have equal bodies. Field four has
an equal checked count-byte prefix followed by zero bytes up to the next
aligned vector count word. Without a native element-width witness, this is a
prefix equality, not a proved full-width element comparison.

At the same index, field five has the same number of structurally valid nested
table references on each side. Their six-slot vtable present-field masks
agree, as do the first four raw bytes of slots one and two whenever present.
The first four bytes of slots three through five differ across the current
pairs. Init field seven and streaming field six hold the same number of
structurally valid nested table references, while the opposite fields are
empty. Within each paired group row, streaming field-six row field zero is a
four-byte ID vector. Init field-seven row field three is an eight-byte
descriptor vector, and row field four leads to a nested field-zero byte blob.
Each descriptor is two signed 16-bit words followed by a zero reserved word;
the positive second word times the group's ID count accounts for one
descriptor-major blob segment. Those segments tile the blob exactly. The
grouped IDs, as a multiset, exactly partition the same file's root field-three
IDs across every authenticated current pair. This is an exact stored record
identity even though group order can differ from root ID order. The report
retains the changing counts and vtable shapes.

The current-corpus gate also proves one semantic column in those records.
Init root field-five rows contain a field-zero FlatBuffer string, parallel by
ordinal with root field-three IDs. Each init group has exactly one descriptor
ID 21 with stride 64. Its descriptor-major segment holds one zero-padded name
slot per paired streaming group ID. Across all authenticated pairs, the
multiset of `(ID, descriptor-21 name)` equals the root `(ID, field-five
string)` multiset after clipping the root string to 63 bytes. In the current
corpus, most slots reproduce the whole root string, while longer names lose
their suffix after the first 63 bytes. Thus descriptor 21 is a **stored name
column with a 63-byte content limit**, not a lossless copy of every root name.
This is a paired-file byte identity, corroborated by the selected descriptor-major copy
consumer below. It does not identify a named runtime component: the reviewed
native getter and prefix-mask census for ordinary Streaming also lacked an
edge from descriptor 21 to their entity-name context field. No reviewed
accessor names the other auxiliary descriptor IDs or nested slots.

The selected [auxiliary bridge contract](../../scripts/game_data/contracts/dynamic_aux_bridge_native.json)
checks the native route beyond filename construction. On the unpatched
`DynamicSceneEcsSystem.TransitionFromUnLoadedToLoaded` route,
`DynamicStreamingScene.GetDataHandle` calls both auxiliary path getters and
passes their results in separate arguments to
`StreamingGameplayManager.AllocateRuntimeChunk_Injected`. The selected
managed injected stub resolves the same fully qualified internal-call name,
which the selected UnityPlayer parallel name/function arrays pair with a
native callback. The callback forwards the two converted strings to a helper
that stores them in separate members of the native streaming object.
Selected native request branches then use those members as indexed path
keys. Each successful lookup passes its path to the same resource lookup
helper and constructs a separate stream handle in one indexed, 80-byte native
record: first at record `+0x18`, second at `+0x20`. The shared resource lookup,
stream constructor, and ready-buffer helper are also independently checked in
the [IV path contract](../../scripts/game_data/contracts/irradiance_v3_path_native.json);
there the selected queue's read and byte-count gate reach a backend virtual
read. The auxiliary route shares those helpers but does not establish which
provider or VFS file a runtime request chose.

A later native branch addresses that same owner record by its index, checks
the two handles, retrieves their ready data-buffer pointers, adds each
buffer's opening FlatBuffer root offset, and stores separate first and second
root pointers at record `+0x28` and `+0x30`. A selected consumer addresses the
same owner record by the same indexed form and reads both root pointers. It
uses FlatBuffer vtable slot `0x12` of the first root, field seven, and slot
`0x10` of the second root, field six, then indexes both vector targets with
the consumer's same ordinal. These are the complementary nonempty vector
positions found in the authenticated current auxiliary pairs. The native
route does not give either vector a semantic field name or prove a concrete
pair was active in play.

That consumer then takes the second-root row's field-zero ID vector and the
first-root row's field-three descriptor vector and nested field-zero blob.
It passes their counts and body pointers together to one native builder. The
builder loops over the eight-byte descriptors, reads a signed 16-bit ID and
stride from each, multiplies the stride by the group ID count, and copies
that segment from the blob into a per-ID destination. Its source cursor
advances by the same segment length. This is a **direct conditional
descriptor-major consumer**, corroborated by the exact current-corpus blob
length, root-ID partition, and descriptor-21 name checks above. The selected
body does not assign gameplay component names to descriptor IDs, nor does this
prove any current pair or ordinal was loaded during play.

The maintained [bridge validator](../../scripts/game_data/dynamic_aux_bridge_native.py)
rechecks the managed identities, argument handoff, internal-call registration,
native path stores, both indexed request branches, resource-lookup and stream
constructor calls, ready-buffer root resolution, the consumer's two
vtable-slot reads, and the ID/descriptor/blob handoff and copy loop against
the selected installed binaries. Its local receipt
is `reports/animestudio/dynamic_aux_bridge_native_latest.json`. The proof is
**direct and conditional on the unpatched managed and successful native
branches**. The pair corpus gate independently authenticates the current
stored bytes by path, length, and FileDataMd5. The next discriminator is a downstream component ownership witness for
descriptor 21 or a source-backed meaning for another descriptor ID,
alongside a concrete runtime path/provider receipt; worker
scheduling, selected ordinal, and actual load remain open.

The main filename has an exact stored identity relation in the authenticated
current corpus. The selected `DynamicSceneFbDataLoader.GetPath` body takes a
packed `UInt32`, extracts its low byte, next byte, and a masked high nibble,
then replaces the indexed characters in the `fb_main` template. Those values
appear as the filename's `x`, `z`, and first one-character segments; every
current `fb_main` file's root `UniqueId` equals
`(first << 16) | (z << 8) | x`. The maintained
[main path join](../../scripts/game_data/dynamic_main_path_join.py) rechecks
the named native claims, each dump's authenticated VFS MD5, and this relation
over the full current main-file set. This establishes the file-to-root ID
join, including the selected code's use of only one high nibble; it does not
tell us which packed ID the game requests at a particular moment.

The authored `streamingDataPathRoot` names `Data/Streaming/PC/...`, a separate
path family from the `Data/DynamicStreaming/PC/Scene/...` main files. The
connection to DynamicStreaming comes through `mapSceneName` and the native
initializer, not by equating those two stored root strings. Every currently
catalogued streaming-config asset has files under its ordinary Streaming VFS
root. Some of those scenes have no DynamicStreaming main files. Of the
main-file scenes lacking a current MapConfig reference, most still have a
catalogued streaming-config asset; the remaining development scene has no
such asset. The join report keeps all one-sided scene sets and source receipts.
These gaps do not show a failed live load or a complete scene catalog. Which
MapConfig is selected, whether its asset load succeeds, and which main grids
activate in play remain unobserved.

The authored condition trees now have a selected evaluator route. The
`RuntimeSceneStateCondition` record stores a state name and a
`ConditionRuntimeBase` object. Its `GetResult` reads the cached Boolean
while listening and otherwise dispatches to the concrete
`GetResultWithoutListening` method. The selected
`CombinedConditionRuntime` body reads its `conditionOperator`,
`subConditions`, and `reverse` fields and implements the named `And` and
`Or` branches, then optionally reverses the result. Current authored
combined rows have paired children without reversal; their changing inventory
is in the local census. The native enum claims recheck the operator and
quest/mission state names against the selected installed build.

The quest and mission leaves fetch `MissionSystem` state and pass it with
their stored operator and target to the `Int32` `TableUtils.DoCompare`
overload. A missing mission-data object follows the body's `None` state
comparison path. Map-variable leaves instead call
`MapVarSystem.TryGetMapVarInCurrentMap`; that method forwards
`m_curMapStr` to the named map lookup. Global-variable leaves call
`GlobalVarSystem.TryGetClientVar`, not the server-variable getter. On a
successful variable lookup, both leaves convert the retrieved `Int64` and
stored integer target to `Single` and call the `Single` comparer. Its
selected equality and inequality branches use an absolute-difference
tolerance of about `1e-5`, so these variable tests are not exact integer
comparisons; large integer values may also lose precision in the conversion.
The selected missing-variable branches return false after logging instead of
comparing a default zero. These are **conditional native evaluation routes**,
not evaluated results for a save or session.

The maintained MapConfig reader now checks that every authored map-variable
condition names its containing map and a key in that map's variable
dictionary, including within combined trees. Every current MapConfig passes.
This is a **stored authoring constraint**. `BaseGameScene` iterates the
authored condition rows when registering listeners; the four concrete
condition types have selected quest-state, mission-state, map-variable, or
client-global-variable registration paths. Those calls show how a changed
value can prompt reevaluation, while live listener registration and event
delivery remain unobserved. The reviewed native claims check the named
method bodies and enum defaults; the generated audit records their hashes.
The selected Boolean branches, float tolerance, and virtual dispatch need
reinspection if those bodies change.

`RootComp.Type` is an `Int32` at the start of the record. The selected
`_ParseLoad` body reads it through the generated scalar reader and uses its
byte value as a key into `m_templateDataMap`. The registered map field is
`Dictionary<EDynamicSceneEntityType, DynamicSceneEntityTemplateData>`, so the
enum names have a **direct typed consumer** even though the serialized getter
itself returns `Int32`. The selected `OnInit` body inserts template records
into this map using each record's typed `entityType` field. This supersedes
the earlier candidate-label interpretation based only on numeric agreement.

`OnInit` also has a direct source path: its literal matches the metadata
default for `TEMPLATE_PATH`, and it calls typed
`TryLoad<DynamicSceneTemplates>` and `FAssetProxyHandle.Get<DynamicSceneTemplates>`.
It reads the resulting object's `templateDataList` through typed list count
and item calls before filling the map. The path joins the fresh export's
asset map to a `DynamicSceneTemplates` MonoBehaviour whose serialized type
tree exposes `entityType` and `comps`; the export manifest and source identity
agree. The reviewed contract and audit validate this whole static chain.

In the authenticated current main corpus, each observed `RootComp.Type` has
one invariant ordered sequence of child `DataIndex.Type` values across all
its groups. Each sequence equals that entity type's ordered `comps` list in
the current exported template asset. Thus stored `Comps.Num` also equals the
authored template list length for every observed group. The audit records
the signatures, including template rows absent from current main grids, and
fails on a missing or differing match. This proves a current **authored
match**, not a receipt that the runtime loaded the asset or visited every
stored entry.

The selected `DynamicSceneDynamicEntitySystem` advertises `RootComp` as its
grid lifecycle data type. Its grid load and reload handlers call
`_RegisterEntities`, whose count-bounded loop walks the grid's `RootComp`
vector with an 84-byte stride and calls `_ParseLoad`. The grid-enter handler
also calls `_ParseLoad` directly. That body takes the embedded group start,
reads 16-byte entries from the same grid's `DataIndex` vector, obtains an
entry's `Type`, calls the selected data-type system route, and has a
conditional call to `DynamicSceneEntitySystem.RegisterEntity`. The audit
verifies these method identities, call targets, and instruction sequences
against pinned native code windows. This corrects the earlier open link from
stored groups to a native lifecycle and registration path.

`IdComp` has a selected native detour within that loop. When the current
`DataIndex.Type` is `IdComp`, `_ParseLoad` passes its `Index` and the containing
grid to an IdComp vector helper, then reads `FBDynamicSceneIdComp.UniqueId`
through the same scalar reader as the generated getter. The unpatched branch
returns to the common `DataIndex.Type` system route with the original type
value. It does **not** skip routing. The helper's selected code window, vector
slot, eight-byte stride, getter target, and return branch are checked by the
RootComp contract. The current audit also matches the number of valid IdComp
directory rows to their authored template signatures; changing counts stay
in the local report. Patched IFix branches and live execution remain outside
this claim.

The inner `DataIndex` loop bound comes from a selected
`SafeCount<EDynamicSceneData>` call on the template record's registered
`List<EDynamicSceneData> comps` field. The native path does not directly read
stored `Comps.Num` for this bound. The current asset and stored groups match
in length and order, but it remains unknown whether a particular grid takes
this path during play, whether the asset is loaded without substitution,
whether each authored directory entry is visited, or which components become
active. Changing counts and source hashes stay in the generated local report.

## ResourceComp groups and scene-local resource grids

The reviewed [resource contract](../../scripts/game_data/contracts/dynamic_resource_comp_native.json)
and [audit](../../scripts/game_data/dynamic_resource_comp_native.py) authenticate
the selected generated getters and builders against the explicit installed
native pair and UnityPlayer. `ResourceComp` is a 124-byte inline record with
five `DataGroup` fields, `Res`, `Mount`, `MountViewModel`, `NavData`, and
`LodInfo`, plus a four-byte `NavState`. The 88-byte
`ResourceGroupWithStateDesc` has a `Group`, four scalar fields, and a nested
`VisibleDesc`. Shared `DataGroup` and `VisibleDesc` layouts come from the
separately checked RootComp contract.

In every authenticated current main grid, the five `ResourceComp` groups
partition their respective vectors exactly. `Res` addresses
`ResourceGroupWithStateDesc`; `Mount` addresses `MountPair`;
`MountViewModel` addresses `PrimitiveStringList`; `NavData` addresses
`DataGroup`; and `LodInfo` addresses `LodGridResource`. These targets use
the selected `EDynamicSceneData` type value, checked grid ID, index, count,
and `TotalInGrid`. The `MountViewModel` name alone would suggest a model
record, but its stored type and partition select primitive string indices.

Each valid resource descriptor's inner `Group` selects `Model`, `Effect`, or
`Ecs` records. Unlike the outer `Res` group, its `Grid` can name another
grid and another main file. Grid IDs repeat across scenes, so the audit
resolves targets by **scene path plus grid ID**. Every current valid target
resolves to one grid in that scene, and the inner groups partition the three
target vectors exactly, including cross-file spans. Invalid inner groups
have no selected payload span. This is an **authored cross-grid relation**;
it does not prove which grids or resources load during play.

The resource descriptor's two visible groups address its containing grid's
`PrimitiveIntList`, as do RootComp's visible groups. Their selected stored
spans are mutually disjoint and account for nearly all current primitive
integers. The resource audit leaves the remainder unassigned within its own
scope; the separate Sludge join below identifies it. The descriptor's
`SceneState`, `LogicState`, `LevelNum`, and `FactoryIndex` fields have exact
selected offsets and primitive types, but this join does not establish their
runtime conditions or use. Changing counts and value distributions are in
the generated audit under `reports/animestudio/`.

## Sludge surface tile IDs and primitive-int closure

The selected [SurfTileIDs native contract](../../scripts/game_data/contracts/dynamic_sludge_surf_tile_native.json)
checks the generated `FBDynamicSceneSludgeComp.get_SurfTileIDs` fast path
against the installed build. It returns an inline `FBDynamicSceneDataGroup` from the
`SludgeComp` record. The separately checked main-vector contract establishes
that record's vector and width; the RootComp contract establishes the shared
DataGroup layout and the `PrimitiveInt` type. This identifies the named field
and its offset by native code rather than by nearby bytes or a value pattern.

The [current-corpus audit](../../scripts/game_data/dynamic_sludge_surf_tile_native.py)
checks the selected native inputs, VFS input set, every main dump's size and
MD5, all main-vector bounds, and each group's type, grid ID, index, count and
total. In every authenticated current grid, the `SurfTileIDs` spans are
disjoint from both RootComp and ResourceGroup visibility spans. The three
families tile `PrimitiveIntList` exactly, closing the prior stored ownership
gap. The values selected by `SurfTileIDs` are nonzero in this corpus; they
are stored tile IDs, not padding. Changing counts and samples are in the
generated report under `reports/animestudio/`.

The selected getter window has an alternate native branch outside its checked
fast path. The getter and stored partition do not establish a runtime consumer
of those IDs, when the Sludge component is active, or how a tile affects
navigation or rendering. Those require a selected consumer or runtime receipt.

## The corrected area vector width

The earlier reader treated `RootVisible` and `AreaVisibleGroups` as byte
vectors because the generated root exposes `Get*Bytes` helpers. Those helpers
return a raw byte view of a vector. The indexed accessors return `System.Int32`
and advance by four bytes per element, as do `TotalAreas`' indexed reads.
With the corrected widths, all six vector count words and bodies tile the
range from the root object's end to payload EOF in the current corpus. The
old apparent gaps were remaining vector elements, not unowned data.

The native getter bodies also establish fixed inline records: an area holds
an ID and a visibility start/count pair; a trigger holds an area ID, a point
start/count pair, and bounds; a point holds two `Single` coordinates; bounds
hold minimum and maximum coordinates and minimum and maximum heights. The
contract records each selected-build offset and accessor witness. The parser
uses their widths to prove framing and leaves values unnamed until the native
gate passes.

## Authored relations in the current files

The populated current file has a coherent index structure. `TotalAreas`
contains zero and the other area IDs, with no duplicate IDs.
`RootVisible` and `AreaVisibleGroups` contain IDs from that same set. The
populated sample has `RootVisible` IDs absent from all area-group slices, so
the root list must not be reconstructed as their union. Every
area's `VisibleStart`/`VisibleNum` range is within `AreaVisibleGroups`, and
the area ranges partition that vector exactly. Each area slice starts with
one zero entry; its role remains unknown. Every trigger's `AreaId`
names a present area. Its `AreaPointStart`/`AreaPointNum` range is within
`Points`, and the trigger ranges partition the point vector exactly. Every
point lies inside its owning trigger's stored XY bounds, and each trigger's
stored XY bounds are exactly the extrema of its points. The populated root bounds
enclose the trigger bounds. Rotating the trigger bounds among the point spans
contains far fewer points, so the ownership check is not a tautology of broad
boxes. These are **stored relationships** and geometry checks, not observations
of visibility or trigger evaluation. Per-build counts
and the file path are in the generated native audit under `reports/animestudio/`.

The remaining current files have empty area, trigger, visibility-group, and
point vectors. Their root bounds use an inverted sentinel rather than a
spatial box. A validator must require ordered bounds only for a populated
root; interpreting the empty sentinel as a malformed map would reject valid
current files. Their `TotalAreas` and `RootVisible` zero entries have a native
consumer: zero is seeded into the dealer's active-ID set, then handled by the
default-area branch of `SetAreaEnable`. It is not a nonzero area forwarded to
the streaming engine or DynamicStreaming's area-change handler.

## Native area selection path

On the selected native bodies, `GameSceneAreaDealer.InitData` constructs a
scene-specific `FBStreamArea.bytes` path from the DynamicStreaming root,
current asset-folder name, and map scene name. It reads the file through VFS
low IO, parses a typed `FBStreamAreaTotalData` root, initializes a trigger
quad tree, and calls `_BuildMapping`. The latter builds the total-area and
trigger-to-area mappings and inserts each indexed `RootVisible` value into
`m_activeAreaIds`. The indexed getter used there is an unnamed native clone of
the reviewed `RootVisible(Int32)` accessor: both use the same root field and
four-byte element stride. This establishes `RootVisible` as an **initial
active-set seed on that path**, although the authored file alone is not a
record of a successful load or executed scene.

`BaseGameScene.CreateStreamingScene` calls `FlushStreamingArea`. That method
walks the dealer's total-area list, tests each ID against its active-area set,
and passes the result to `SetAreaEnable`. On its valid-scene branch, a nonzero
area goes to the engine's `StreamingSceneV2.SetArea_Injected` and to
`DynamicStreamingScene.OnAreaChanged`, which updates the entity and resource
area controllers. Area ID zero takes a separate default-area layer path.

The selected unpatched loading bodies identify the area's query centers.
For a regular load, `SquadManager.ServerTeleportSquad` forwards its `pos`
argument to `GameLevelLoader.LoadAtPos`. That loader supplies the requested
`Vector3` to `LoadingPipeline`, which stores it as `m_centerPos`; the load-scene
step passes that field to `BaseGameScene.SetStreamingCenter`. For a seamless
load, both `LoadingPortalComponent._OnInteract` and
`SeamlessPortalComponent.StartLoading` read `tpPosition` from their respective
component-data objects and pass it to `SeamlessLoadMap`. That method puts the
requested position in the teleport parameters;
`SeamlessLoadingPipeline.Prepare` copies it to `m_tpPos`, and the preload-scene
step passes `m_tpPos` to the same setter. The setter initializes
and stores `m_streamingCenter`, then copies it into a valid area dealer's
`m_mainCenter` and requests a refresh. `BaseGameScene.Update` also compares
that stored center with the dealer's last-checked center; its selected branch
requests a refresh when squared distance exceeds one. The explicit
`ForceRefreshAreaMainCenter` path uses the same stored center.

An extra-load position has a separate optional route:
`BaseGameScene.LoadExtraAtPos` passes it through `SetAreaSubCenter` to the
dealer's `SetSubCenter`. The dealer's `_UpdateIfNeeded` copies `m_mainCenter`
into `m_lastCheckCenter`, puts the main center and, when enabled, the sub-center
into its update list, then calls `_UpdateActiveArea`. The clear-extra-load path
clears sub-center use. These paths name the centers the selected code uses;
they do not establish the source of the squad teleport's `pos` or which native
branches ran during a particular scene load.

The stored origin of portal destinations is now more specific. The maintained
[portal center join](../../scripts/game_data/portal_center_join.py) checks the
selected build's `BaseComponentData` union tags and
`InteractiveComponentType` enum, the exact `InteractiveData` template frames,
and the exact `LevelData` frames. The loading and seamless portal templates
each carry a `tp_position` property with a zero-vector default. The matching
placed interactives carry separate, nondefault `tp_position` overrides in
their portal component entries, alongside `tp_level_id`. The interactive's
own world position is a distinct field and is not the destination vector.
The generated report records the vectors, level IDs, source hashes, and
changing corpus counts.

The selected `ApplyProperties` bodies bind the literal `tp_position` to a
`Vector3` assignment callback at the same typed `_TryAssign` call. Those
callbacks write each component data object's `tpPosition` field, and the
portal handler reads that field on the load route above. Each portal data
class's `get_interactiveComponentType` returns the enum member used as its
`LevelData.componentProperties` key. After `Entity.AssignLevelEntityData`
stores the level object, `InteractiveRootComponent.OnLevelDataAssigned` reads
that map, enumerates the typed keys, and loads selected property rows into a
component `ParamBlackboard`. Both portal components inherit through
`InteractiveCoreComponent` from a concrete
`LogicComponentWithDynamicProperty<InteractiveCoreComponentData>` parent.
Its shared `AssignData` body creates a component blackboard, loads template
properties, and adds that blackboard under the component key to the entity
blackboard. Its `InitSelf` body reads the same component blackboard for a
dynamic data-application dispatch. That shared code pointer is registered as
`System.Object`, so the selected class hierarchy is an essential separate
check. The selected `InitSelf` call passes its instance data and component
blackboard to an unnamed IL2CPP helper. Its native body indexes the receiver's
virtual table by the passed slot and invokes that entry with the blackboard;
the base `DynamicPropertyComponentData.ApplyProperties` and both portal
overrides declare that same selected slot. The reviewed native claim checks
the helper shape and slot equality on the installed build, without pinning an
address or slot number in prose. This closes the stored
override-to-`ApplyProperties` route for the selected unpatched branch, but neither
the stored rows nor the native bodies are a receipt for live assignment,
interaction, or streaming-center selection.

The selected placed-interactive creation path now narrows allocator selection.
`EntityManager.SpawnInLevelClientInteractive` obtains the level number and
creates an `InteractiveInfo` for a logic ID. Its level lookup uses
`LevelData.TryGetInteractiveInLevelData`; the selected overload reads the
interactive lookup table and returns a `LevelInteractiveData` through an out
slot. The caller passes that exact slot value to
`EntityDataStorage.CreateInteractiveFromLevelData`, which passes it to
`InteractiveInfo.InitFromLevelData`. That initializer sets the template and
stores the same level object through `BaseEntityData.SetupInLevelData`.
`BaseEntityData.Commit` can apply the data and construct an `EntityNode` that
stores the `BaseEntityData`.

When that node enters its spawn pipeline, `_SpawnEntity` reads its stored
`BaseEntityData.inLevelData` and passes it as
`ObjectContainer.SpawnEntity.overrideInLevelData`. `SpawnEntity` forwards the
same stack argument to `ObjectContainer.LoadEntity.inLevelData`, and
`LoadEntity` forwards it to the placed-data
`EntityAllocator.AllocateObject` overload. This selected overload calls
`Entity.Construct`, prepares the root position, calls
`Entity.AssignLevelEntityData`, and only then calls `Entity.PreInit`.
`PreInit` enters `ComponentContainer.PreInit`, which pre-initializes components.
The same `LoadEntity` body later calls `Entity.Init`; that enters
`ComponentContainer.Init`, whose body calls `BaseComponent.Init`. The reviewed
claims verify the named fields, argument handoffs, and call order against the
installed native bodies.

The joined portal `LevelData` rows in the current verified corpus store an
unsigned `dependencyGroupId` of zero. The selected
`EntityNode.get_dependencyGroupId` body reads that ID
through its stored `BaseEntityData.inLevelData`. When `SetInAoi(true)` runs on
a node with no dependency group, it flips the Boolean and advances it to the
native `AoiState.Intrested` member. `SetAoiState` launches the spawn pipeline
when that state changes and its node guard permits it;
`_LaunchSpawnPipeline` calls `SwitchToNextPipelineState`, which can enter the
`_EnterPipeline` spawn branch above. The queue's `_SpawnNode` body has a
separate call into `_EnterPipeline`. Grouped nodes have a different path:
`AddToGroup` first assigns `NotIntrested`, while an interested-group update
can assign `Intrested` to its member nodes. These selected native paths now
explain the conditional transition from AOI interest to spawning. They do
not show which pipeline state or patch branch ran for a live portal.

The selected grid code identifies an AOI update caller. The validated grid
callers target an unnamed body rather than the registered `SetInAoi` entry.
`GridProcessor._TryDoSetInAoi` passes its named node and Boolean AOI input
to an unnamed native body. Its chained fragments perform the same checked
dependency-group lookup and Boolean-to-`AoiState` mapping. The force-load
entry and grid-range exit methods on `NodeGrid` call that body with true and
false respectively; `OnNodeSkipAoiCheck` selects the force-load branch when
its runtime flag is set. The joined portal rows have authored `forceLoad`
false, but that stored field has not been proved to be the runtime skip-AOI
flag. These calls establish a native source for AOI state changes, while
leaving the grid update for either portal and a live spawn unobserved.

On a requested refresh, the dealer's `_UpdateActiveArea` queries the trigger
quad tree. The tree's `Query` body calls `FBStreamingAreaHelper.CheckInArea`
and can add trigger indices to its result set. The dealer then
reads selected areas' `VisibleStart`/`VisibleNum` slices, compares
the resulting IDs with the active set, and calls `SetAreaEnable` for changes.
It also requests a chunk-grid refresh after changes. The selected bodies
therefore explain how stored area IDs can affect streaming visibility.

The selected unpatched `CheckInArea` body resolves the trigger predicate. Its
trigger index selects one `Triggers` record; that record's
`AreaPointStart`/`AreaPointNum` select a closed ring from `Points`. The query
`Vector3.x` and `.z` are compared with stored `Coord.X` and `.Y`, and
`Vector3.y` is compared with `MinHeight`/`MaxHeight`. For finite values, all
six bounding comparisons include equality. After those checks, the body walks
consecutive point pairs with wraparound and toggles an even-odd flag when
their stored Y coordinates straddle query Z and their interpolated edge X is
strictly to the positive-X side of query X. The false-toggle code sits in a
separate native window; the area contract authenticates both windows and
their branch link.
This proves the selected code's X/Z projection and polygon rule. It does not
fix the position's source before the identified teleport or portal route,
classify every point exactly on a polygon edge, or show a particular trigger
firing in play.

## Evidence boundary

- **Exact:** current VFS ledger identity and payload MD5; selected-width main
  vector bodies are bounded and nonoverlapping, while the area root's six
  count words and vector bodies tile its tail through EOF. Area bounds sit
  inline in the root. The selected-width version entry vector also tiles the
  root-to-EOF tail in every authenticated current version file. Every
  authenticated current main filename decodes to
  its own FlatBuffer root `UniqueId` under the selected packed-ID rule.
- **Direct:** selected-build accessor signatures and pinned code windows name
  the main vector fields and widths, the DataIndex and RootComp fields,
  ResourceComp and ResourceGroupWithStateDesc field offsets and widths,
  including RootComp's nested visible-group offsets and the selected
  controller path that reads their `PrimitiveIntList` elements, plus the area
  integer vectors and records. The RootComp lifecycle handlers
  call `_RegisterEntities` and `_ParseLoad`. `OnInit` requests the selected
  template asset path and populates the typed dictionary; `_ParseLoad` reads
  from RootComp through that dictionary and DataIndex to the selected system
  route, gets its inner bound from template `comps`, reads indexed
  `IdComp.UniqueId` on its selected unpatched IdComp branch, and can call
  `RegisterEntity` on a conditional native path. The selected BaseGameScene
  bodies read both MapConfig scene-state fields, calculate a mask and index
  list, and pass that list to DynamicStreaming state synchronization. The
  separate `SetSceneState` body can update the same list by state name.
  Named condition leaves read quest, mission, current-map, and client-global
  sources through selected comparator overloads; the combined body reads its
  Boolean operator and child list.
  Normal and seamless loading have conditional MapConfig-table lookup and
  scene-field handoffs; the router body uses the matching JSON path literals.
  The streaming-config path reader, asset loader, scene-name reader and
  DynamicStreaming initializer establish a conditional native source route.
  The main, init, streaming, and version path builders name their filename
  templates. The selected typed FlatBuffer loader has a VFS low-IO call and
  reads chunk version fields before accepting a result. Selected version-root
  and entry accessors identify their stored fields, widths and offsets. The selected area
  dealer reads `FBStreamArea.bytes` through VFS into a typed root, builds a
  trigger tree and mappings, seeds its active IDs from `RootVisible`, and
  uses `CheckInArea` and the stored visibility spans to drive later area
  changes. The interactive root reads selected component overrides from
  `LevelData`, loads their property rows into a component blackboard, and the
  portal data getters agree with the native component enum keys. The selected
  generic component body creates that blackboard from template properties and
  passes it with instance data through the selected `ApplyProperties` virtual
  slot at initialization; both portal data overrides declare that slot.
  Concrete portal inheritance is checked
  separately because the shared code pointer is registered as
  `System.Object`. The `tp_position` callback writes the field the portal
  load handlers read. The selected logic-ID lookup passes its returned
  `LevelInteractiveData` through `InteractiveInfo` into the node's stored
  `BaseEntityData`. The node dependency getter reads the placed ID; with no
  dependency group, `SetInAoi(true)` maps to `AoiState.Intrested`, and the
  selected state path can launch and enter the spawn pipeline. The grid
  processor passes a named node and AOI Boolean to an unnamed native setter
  with the same checked state transform, and NodeGrid has separate force-load
  and range-exit calls to it. On the spawn branch, named stack handoffs carry
  level data through `ObjectContainer` to
  the placed-data allocator. The allocator assigns level data before
  component pre-initialization; `LoadEntity` later enters component
  initialization.
  Squad teleport and portal component-data positions pass through
  named pipeline center fields to `SetStreamingCenter`; an extra load can
  supply an optional sub-center. The dealer assembles those centers for its
  query, while the base scene's update and force-refresh paths read its stored
  streaming center. The base scene flush checks seeded IDs against `TotalAreas` and
  forwards nonzero area changes to the streaming engine and DynamicStreaming
  area controllers. Selected `CheckInArea` code windows establish inclusive
  X/Z and height bounds followed by the stored ring's even-odd ray test.
- **Structural only:** RootComp's exact partition of each grid's DataIndex
  directory and the exact authored template match per observed entity type,
  ResourceComp's five same-grid vector partitions and the scene-scoped
  cross-grid resource payload partitions, plus the disjoint ResourceGroup
  visibility, RootComp visibility and Sludge `SurfTileIDs` spans that tile
  the current `PrimitiveIntList` vectors,
  both visible groups' bounded, disjoint spans into the grid's
  `PrimitiveIntList`, the scene-local membership of `VisibleAreaGroup` values
  in `FBStreamArea.TotalAreas`, DataIndex's grid-local ID and Type/Index vector
  partitions, the same-scene join from authored visible-state indices to
  `MapConfig` names, the LevelConfig-to-MapConfig stored key relation, the
  condition-name subset, map-variable condition ownership, and distinct mask-index
  relation in the current MapConfigs, the MapConfig-to-asset-map-to-MonoScript
  identity join, full MonoScript-class census, ordinary Streaming VFS paths,
  and shared scene names, the exact portal template and instance override
  relation (including separate source and destination positions, zero-valued
  dependency-group IDs, and authored force-load flags), the join
  from stored Type values to available system routes, authored area ID
  membership and exact span
  partitions, and XY containment within serialized bounds.
- **Unresolved:** other nested main struct fields, whole-main-file closure,
  live login-response object/value, registration execution, network bytes and selected patch branch,
  live accepted version strings and repeated phase-capture behavior,
  version-entry `Id` meaning and runtime version-ban selection,
  resource descriptor state conditions, the runtime consumer and meaning of
  stored Sludge `SurfTileIDs`, live resource grid selection and resource activation,
  `DataMask`, actual loading of the authored template asset, executed DataIndex
  lookup, selected live MapConfig file, successful streaming-config asset load,
  one-sided scene-name gaps, evaluated scene-state conditions and
  executed area selection for a particular scene,
  origin of the squad teleport position and live portal component values,
  live grid selection, visibility
  changes, polygon-edge equality cases, selected runtime patch state, the
  actual grid AOI update and selected pipeline state for either observed portal, and
  live activation for either instance. A field named
  `RootVisible` is an authored initial-set input, not a runtime receipt.

The `init` and `streaming` DynamicStreaming roots now have an exact stored
pairing, root-ID partition, and descriptor-major blob boundary. The selected
native path-to-root route connects the two file-family names to separate
ready buffers and a consumer of first-root field seven and second-root field
six, then to a per-ID byte-copy builder. Descriptor and component meanings
remain anonymous. The version entry layout is separately checked; runtime
selection of all three auxiliary families remains open.

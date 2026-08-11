# Character rendering and animation recovery

## Current status

The Unity lab is a useful source-backed reconstruction of Endfield character
models and Character Info presentation. It is not the original renderer and
has not reached retail visual parity.

| Layer | Current status |
| --- | --- |
| Playable model coverage | 31/31 imported and rendered, including Liino |
| Canonical post-model coverage | 156/156 identities have prefab paths |
| Static playable Overview assets | high, roughly 90%+ |
| Selected CharacterNPR equations | medium-high, roughly 60–75% |
| Complete CharInfo/HGRP frame | partial, roughly 35–50% |
| Playable UI clips | complete for the selected `all-ui` scope |
| Original animation behavior | partial |
| Final retail visual parity | not reached |

The 156 canonical identities are 31 playables, 1 NPC character, 1 cutscene
clone, 94 enemies, and 29 ability/prop actors. Six additional modular ambient
NPC archetypes are imported as labeled source kits.

## What works

- All 31 playable post-models, materials, textures, cameras, profiles, lights,
  portraits, and Overview animation sources are cataloged.
- The previous 30-character Overview capture set remains valid and nonblank;
  Liino is imported and awaits the next capture refresh.
- Playable UI recovery contains 779 body clips and 348 private item/deco clips.
- Roster discovery now treats `structured/Persistent/Table/CharacterTable.json`
  as the current patch overlay and resolves AnimatorControllers from both
  StreamingAssets and Persistent. Liino proves this boundary: her roster row,
  CharInfo camera/light/portrait, 25 body UI clips, 27 private-deco clips, and
  external UI controllers are patch-layer data, while her post-model and exact
  Grounder remain in StreamingAssets.
- The Playable-only native texture payload contract now closes 193 selected
  Texture2D objects over 398 generated GUID owners. Unity validates all 11
  Liino-owned entries byte-for-byte, including compressed mip chains, stable
  GUID/PPtr identity, and exact importer state.
- The Endfield 101-muscle ABI and exact Avatar bases are preserved.
- Narrow exact behaviors include Wulfa/Li automatic blink, one Zhuang facial
  fixture, and one Wulfa 33-frame physical-transform animation oracle.
- All non-playable post-model identities have dependency-safe static prefab
  baselines.
- Chen and Chenpast remain separate source-authored model identities: their
  canonical post-model containers, Animator PathIDs, VFS sources, and generated
  Unity mesh GUID sets are all distinct. Each generated prefab binds its own
  ten-mesh set with no cross-prefab mesh GUIDs. Chenpast's shared
  facial-morph/CPU-animation basis is not a mesh identity join; the regression
  check is `test_generated_chen_prefabs_keep_mesh_guid_sets_disjoint`.
- Selected CharacterNPR, eye, hair, shadow, material, particle, and gacha
  presentation paths have source-backed diagnostics.
- The installed UnityPlayer fallback selector now closes the exact
  DefaultDeferred pass-0 D3D11 pair; both original stages execute once in a
  fail-closed standalone diagnostic, while live frame bindings remain open.
- A default-off SphereOutside sidecar now uses the source CharInfo camera and
  transform to produce the exact logical 640x720 SceneColor/SceneMV/GBuffer
  A/B/C formats plus D32S8. All five readbacks are bit-identical on D3D11 and
  D3D12, the presented frame is unchanged, and missing binning/reflection/b33
  prerequisites fail closed. It is deliberately non-presented: canonical
  render-graph lifetime and pass 0 remain open. The current installed
  `RenderWithAlpha=false` route submits no WriteAlpha draw.
- Deferred binding 32 now has its exact native 48-byte
  `_LightBinningConstants` layout/upload and a default-off isolated-count
  publisher verified bit-for-bit on D3D11/D3D12. Its unique native
  `CullLights` producer, two `HGCamera.DoECSCulling` call sites, 256-candidate
  cap, pointer/count ABI, and first consumer are also closed. Installed
  InitBundle settings now close the Windows desktop
  `PunctualLightMaxCount=256`; `SetupState` keeps types 0/2, sorts priority
  descending then squared camera distance ascending, and takes
  `min(survivors, cap)`. Because the upstream cap is also 256, settings cannot
  truncate the list again. Installed Gacha Lua plus decoded Zhuangfy and room
  prefabs now close the known authored input as 6 `light_overview` lights + 12
  `SceneLight6Rarity` lights: 3 type 0, 15 type 2, zero authored cookies, one
  shadow request, and four bone followers. The shipped Gacha cull route uses
  the normal core with fallback and occlusion disabled. Matching read-only
  Unity/game settings select `3840x2160`; at that 16:9 aspect, native AABB,
  authored OBB, point-sphere, and spot-cone tests admit exactly 11 room lights
  and reject only `Spot Light (20)`. Installed layer data fixes recursive
  Gacha assignment at layer 30. Identity prefab/Timeline placement, native
  follower equations, and the original entrance/loop ACL streams close all six
  character lights: their constant root motion removes to identity, no muscle
  lanes are mapped, and every light passes across all 844 decoded QVV frames.
  The exact known authored contribution is therefore 17, with its internal
  priority/distance order closed. Other display aspects, runtime/custom
  carry-in, the target-frame pointer/count, whole-list order, and final retail
  `lightCount` remain open. The maintained cap audit now directly pins both
  `DoECSCulling` call sites through the UnityPlayer candidate core: its native
  gates, hidden-sret handoff, 16-byte `LightCullResult`, and 148-byte
  `VisibleLight` capture stride are source-closed. The native candidate-pointer
  vector is then converted by the hash-pinned `0x180543CE0` producer into
  `inputCount * 0x94` rows, with the source-to-row field projection recorded
  in the audit. The enclosing hash-pinned `CullLightsInternal` wrapper now
  also closes the `viewHandle == -1` zero-result path, hidden-sret pointer/count
  publication, manager retention-vector append, and local-vector cleanup. An
  authorized target-frame
  capture therefore has an exact pointer/count/row decoding contract, but no
  live values are inferred offline. The same maintained audit now closes
  the post-cull consumer contract: `LightClusteringPassConstructor.SetupState`
  projects the returned rows into a zero-based `<=256` slice, preserves each
  original `VisibleLight` row index through the priority/distance sort, and
  passes the sorted `Int32` index array to punctual shadow preparation. This
  closes index transport, not the missing target-frame row values.
  The same maintained audit now closes
  `AddCullViewByMatrix` from its 16-argument binding through six-plane
  construction and the scheduled view record. The managed screen-size minimum
  is squared and stored at view `+0x18`; its installed desktop default is zero.
  Candidate visibility bit 0 is evaluated before the mask-enabled bit and
  `Camera.cullingMask & candidate.layerMask`. `sceneCullingMask` is forwarded
  but not read by this hash-pinned constructor. Its managed producer is now
  source-closed as the pure `HGUtils.GetSceneCullingMaskFromCamera` IFix wrapper
  target 793, with no ordinary Camera-field computation; the non-zero patch or
  runtime payload remains capture-only. The next dispatch boundary is
  now split exactly: normal views use a six-plane AABB predicate, while
  `cameraType == 0x80` uses a sphere/distance predicate; neither reads view
  `+0x18`. The complete hash-pinned scheduled batch core also has no direct
  scalar load from that offset. Its separate `state +0x180` input is squared
  `parentLODBias` and is only forwarded through the core and child-job thunk,
  not consumed as the view threshold. The complete installed CullView-named
  internal-call surface is now closed: matrix/planes additions share the same
  scheduled constructor; dispatch passes the `manager+0x38` view-pointer array
  directly to the batch loop; that loop, both predicates, fence lookup, and
  reset do not read `+0x18`. Child views instead use a separate
  `manager+0x58` array of `0xE8`-byte records. Thus the installed
  `screenSizeMinimumSquared` field is write-only on this pinned native surface,
  with no later packet copy or threshold gate. Retail serializer/deserializer
  evidence now identifies the formerly
  generic 28-byte record exactly as `HGTreeRenderer`, nested under
  `HGTreeInstance.renderers`, with `lodScreenSizeMaxSquared` and
  `lodScreenSizeMinSquared` at `+0x14/+0x18`. The dedicated 729-entry HG
  internal-call name/function tables pair `HGTreeRender.CreateRendererList`
  index 564 with `0x1801D9D10` and `RegisterTreeBatchGroup` index 567 with
  `0x1801DA040`. The former reaches `0x18107EE40 -> 0x181080730` and selects
  runtime batch jobs `0x181067A70/0x181064190`; the latter reaches registration
  core `0x181086050`. Loader `0x1810C5F30` now closes that transform: it
  writes `count`, a `0x18`-stride runtime-record array sized to capacity
  buckets 1/2/4/8/16/32, then a separate 8-byte LOD pair array at
  `4 + 0x18*capacity`. Each source record calls `0x181086050` with
  `batchKey`, mesh/material PPtrs, and `subMeshIndex`; its returned 16-bit
  handle plus `batchKey/renderFlags` enter the runtime record, while the two
  serialized LOD floats copy verbatim to the pair array. Dedicated HG entries
  568/569 are `UnregisterTreeBatchGroup` and
  `UnregisterTreeBatchGroupWithHandle`; owner cleanup `0x1810BCE00` iterates
  the same blob and passes record `+0x04` as `batchKey` and `+0x02` as the
  16-bit handle to `0x181087E00`, closing that registration lifecycle. The
  tail is now split by binary behavior. Serialized `renderFlags` at `+0x08`
  remains mutable, with four particle mode-2/3/4/5 setup variants replacing it
  with bit 20 and a scheduled callback consuming it. A second independent,
  hash-pinned route corrects the resource mapping by accounting for the
  4-byte blob header: `HGMeshRendererData` fields
  `m_Materials/m_Meshes/m_ShadowProxyMeshes` at native `+0x58/+0x78/+0x98`
  resolve through singleton Material/GeometryHandle maps at `+0x90/+0xA0`
  and write runtime record `+0x04/+0x08/+0x0C`. Availability writers
  `0x181157760/0x181159010` and cleanup use the same three destinations.
  Consequently record `+0x0C` is specifically the shadow-proxy
  `GeometryHandle`: owner handle `+0x18` supplies it at
  `0x181157AD1/0x1811592A0`, cleanup clears it at `0x18115C110`, and callback
  `0x181064B73` consumes it in a combined masked filter. HG internal-call
  entries 300/301 name `HGGeometrySystem.GetGeometryHandle/GetMesh`; the
  hash-pinned slot builder closes bits 0..23 as the slot index and bits 24..31
  as the 8-bit generation incremented at slot `+0x06`. Installed
  `HGTreeRender.CreateRendererList` metadata names the upstream UInt32 values
  `renderFlagsMask/renderFlagsValue/lightModeMask`; binding `0x1801D9D10`, core
  `0x18107EE40`, and scheduler `0x181080730` preserve them into descriptor
  `+0x40/+0x44/+0x48`. Callback `0x181064190` receives descriptor `+0x04`, so
  its `+0x3C/+0x40/+0x44` reads are those exact fields. GeometryHandle is thus
  intentionally folded into the HGTree renderFlags comparison, not a separate
  bitfield. The current `GameAssembly.dll` direct-call census closes all seven
  managed callers: three punctual-shadow paths, Deferred PreZ/GBuffer, ASM
  static shadows, and both directional CSM builders. Deferred uses
  mask/value/light-mode `0x500/0x100/0x1`; ASM uses
  `0x01080100/0x01080100/0x400`. Punctual paths add Opaque to the exact
  `GetECSRenderFlags` static/dynamic truth table. Directional paths use identical
  mask/value `m_cascadeRenderFlags[i] | 0x02080100`; the hash-named metadata
  initializer closes the four results as
  `0x02180100/0x02280100/0x02480100/0x02880100`. Record `+0x10` is not
  resource-seeded; common
  Renderer state sync `0x180432CD0` alone maintains that property-flag word at
  blob `+0x14`. Dedicated HG
  internal-call entry 204 names `+0x14` as `enabledLightModes`; wrapper
  `0x1801EB940` reaches the all-record writer at `0x1810D9110`. Installed
  IL2CPP metadata closes its argument as `UInt32 lightModeMask` and
  `HGShaderLightMode` as 31 named pass bits `0..30` (`None=0`). The hash-pinned
  `Beyond.Gameplay.Factory.PerDrawPassConfig._ParseToHGShaderLightMode` body
  maps its narrower gameplay enum into those sparse bits, and `Apply` calls
  the managed wrapper directly at `0x1869F3904`. Native initialization is now
  closed too: the Renderer base constructor defaults field `+0x250` to
  `0xFFFFFFFF`; builders `0x18042A130/0x18042AB50` copy it directly to every
  record `+0x14`, while generic path `0x180BCCB60 -> 0x180BCB760` carries the
  same value through constructor input `+0x20`. The two HGTree renderer-list
  callbacks store the requested mask at job `+0x44` and test it against a
  separate `0x60`-stride renderer-entry word at `+0x1C`. That word is now
  independently closed: builders `0x18109BE90/0x18109C9D0` clear it, query the
  renderer material/shader against the exact 31-name `HGShaderLightMode` pass
  table, and set each supported bit. It is therefore a shader-supported-pass
  mask, not a projection of runtime record `+0x14`. The direct lookup surface
  is now bounded: all 53 calls to `0x180424C30` are pinned and partitioned into
  44 exact `0x7F00` calls across 41 entry CFGs plus nine other-family calls.
  Width-aware cross-hot/cold CFG taint finds no exact-path record `+0x14` read,
  non-stack record-base pointer store, record-base return, or address-taken
  stack spill. Its seven exact-result stack stores are local spills/reloads or
  reused slots (four `blob+0x00`, three `blob+0x04`); none becomes a nested job
  descriptor. The six direct `blob+0x04` call escapes are
  three zero initializers at `0x181CA0040` and three calls to classifier
  `0x181131FC0`, which reads only record `+0x00`. One additional `blob+0x00`
  tail path, `0x1810CE280 -> 0x181C9F9A0`, copies the full layout with byte
  count `4 + 32*(familyMask>>8)`: count, `24*capacity` runtime records, and
  `8*capacity` LOD pairs. It carries `+0x14` verbatim between exact-family
  blobs but does not interpret it. HG Factory internal-call entries 198/215
  name the current/obsolete `CreateBatchedEntities` routes; their hash-pinned
  copy cores `0x1810CE510/0x1810CEBC0` both call this helper. A third exact component-K /
  ray-tracing-K grouping consumer at `0x18112A790` reads only record
  `+0x00/+0x04/+0x08/+0x10`. The apparent callback-A `+0x14` read at the same
  stride is not this blob: `0x181038D70/0x181038DE0` derive its base from ECS
  archetype component columns 127/126, and the value is consumed as a float.
  The other HGTree renderer-list variants do not reveal another route:
  internal-call entries 564/565/566 (default, child-view, and PreZ) reach cores
  `0x18107EE40/0x18107FCF0/0x181080190`, which all converge on scheduler
  `0x181080730` and the same two already inspected callbacks. The actual
  downstream consumer is instead in the separate GPU-driven renderer path.
  HG internal-call entries 151/152 and 164/165 identify
  `GPUDrivenRendererV1/V2` default/PreZ routes; their four cores build
  `0xA0`-byte jobs, whose callbacks read requested light modes from `+0x54`,
  select the `0x7F00` ECS renderer column, and reach V1/V2 default/PreZ
  consumers. Representative consumers `0x1810E87E0/0x1810E9AD0/`
  `0x1810F58F0/0x1810F6BC0` form a record cursor at base `+0x0C` or `+0x10`,
  read dword `+0x14`, and advance by `0x18`. They OR this
  `enabledLightModes` word with candidate-pass `+0x18` and callback-derived
  flags, then apply `(combinedFlags & job[+0x48]) == job[+0x4C]`; requested
  light modes are independently tested against candidate-pass `+0x1C` with
  the request mask at job `+0x54`. The downstream native consumption and its separation from
  the shader-supported-pass mask are therefore closed for all four routes.
  This loader blob is not the other 24-byte structure used by LOD jobs. The latter
  is archetype component bit 67: `+0x00` is LOD count, `+0x01/+0x02` are the
  desired and availability-resolved indices, `+0x03` carries transition/output
  history, `+0x04/+0x05` are pending/available LOD masks, `+0x08` is a 64-bit
  renderer-readiness set, and `+0x10..+0x17` are eight cumulative renderer
  range endpoints. Writer `0x1810842E0` closes the request, completion, and
  unload bit transitions. The indexed accessor `0x1811648A0` exposes the same
  component per entity, and writer `0x181159010` closes its initial LOD0
  completion/fallback transition: when only LOD0 is pending it zeroes the
  desired/resolved/history indices, changes pending/available masks to `0/1`,
  and fills readiness bits from the companion renderer/subresource count;
  otherwise it writes sentinel 8 to all three indices and clears readiness.
  The intervening `+0x06/+0x07` word is now closed as reserved/alignment on
  the direct accessor-derived surface: all 25 direct calls and 21 logical
  caller bodies are pinned, no caller gives it a standalone/field-specific
  access or writes it, and all 1,305,818 serialized instances initialize it
  to zero. Dword reads rooted at `+0x04` include it physically but only update
  the lower pending/available bytes.
  It does not produce the LOD count or cumulative range endpoints. Installed
  scripting registration `0x1807EEEE0 -> 0x1807EC5E0` now directly closes
  `::Scripting::UnityEngine::HyperGryph::ECS::HGTreeComponentProxy` to native
  type `HGTreeComponent` in namespace `UnityEngine.HyperGryph.ECS`, module
  `UnityEngine.HGGraphicsModule.dll`. Dedicated HG internal-call index 712,
  `EntityManager.GetOrRegisterEntityTypeImpl_Injected` at `0x1801E0D90`, now
  closes the next step: each stride-8 input contributes its signed 16-bit
  component ID to `mask[id >> 6]` at bit `id & 63`, so ID 67 is exactly high
  qword bit 3 (`0x8`). Current metadata method 478429/token `0x06000279`
  maps `HGTreeComponent.get_id` to GameAssembly `0x184DBCEC0`; its exact body
  is `mov eax, 0x50; ret`. `HGTreeComponent` is therefore ID 80/high-qword
  bit 16 (`0x10000`), proving that the component-67 LOD state is a separate,
  still unnamed native component rather than `HGTreeComponent`. The similarly
  named managed `RenderObjectLODInfoComponent.get_id` maps to
  `0x184D9EC60` and returns 6. A complete installed-metadata/codegen census now
  pins all 30 `UnityEngine.HyperGryph.ECS` declarations returning `Int32` from
  `get_id`, all 30 module pointer slots, and all 29 concrete constant-return
  bodies. Their exposed ID set does not contain 67, so component 67 has no
  managed name on this shipped surface rather than merely failing the two
  likely-name checks. Raw 8-byte
  `global-metadata.dat` defaults now close the separate serialized
  `StreamingComponentType` enum: `HLODGroup = 1<<11`, `HGTree = 1<<41`, and
  `Count = 43`. HG internal call 677 binds script converters through
  `0x1801DFF50 -> 0x181170720`; the native registry constructs exactly 43
  `0x308`-byte slots, selects one with `bsf(componentTypeMask)`, and requires
  a non-empty component list whose first entry is Transform. These values are
  converter bits, not ECS component IDs, so they narrow the component-67
  search to the native LOD-state type identity rather than either managed name.
  The native entity lifecycle registry is now closed separately: one
  `ECSEntityType` record is `0x288` bytes, with ten `0x40`-byte callback
  slots at `+0x08`. Installed `EntityTransition` metadata names slots 0..9.
  All 105 calls to installer `0x1811701B0` partition exactly between two
  hash-pinned `StreamingGameplayManager` constructors (52/53). Both install
  the same component-67 callbacks for `Render` and `MergedRenderCollider` at
  `UnloadedToLoading`, `LoadingToLoaded`, `UnloadingToUnloaded`, and
  `LoadingToUnloaded`; waiting slots 2/7 are unbound. The managed constructor
  replaces only `Water` and `WaterDecal`, so it does not overwrite either
  component-67 owner registry. The two teardown paths are now exact too.
  Callbacks intersect the archetype high mask with `0x7F0`; the complete
  serialized corpus makes that selection one-hot with exactly one of IDs
  68..73 beside every component-67 archetype. Their sizes
  `48/88/168/328/648/1288` are an 8-byte header plus 1/2/4/8/16/32 rows of
  40 bytes, each holding three source pointers and three resource handles.
  Transition 6 (`UnloadingToUnloaded`) walks `pending|available` LOD ranges,
  releases all three handles, clears the mapped Material/main-Mesh/
  shadow-proxy runtime words, and zeroes both mask bytes; type 9 alone adds
  merged-render-collider cleanup. Shared transition 8
  (`LoadingToUnloaded`) walks only pending ranges, releases owner handles,
  clears only pending byte `+0x04`, and preserves the available byte and
  mapped runtime words. Code admits selector bit 74, but no serialized ID-74
  companion or native name is claimed.
  The paired transition-1 load path is now exact. HG internal calls 273..291
  name `enableLODStreaming` at state `+0x38`, keep-last-resource at `+0x39`,
  embedded `LODCrossFadeConfig` at `+0x3C`, and the squared HLOD unload-
  distance table at `+0x474`; entries 283..291 additionally name dirty-distance,
  reset, status-query, and pending/load/unload-count controls without yet
  assigning new native fields. Installed IL2CPP field offsets place config
  `c1` at embedded `+0x18` and managed component-6
  `RenderObjectLODInfoComponent.lodCenter` at `+0x00`. Type 9 requests either
  the terminal LOD or every LOD from the streaming switch. Type 0 requests
  its single row directly when streaming is disabled; when enabled it gates
  the request by squared `lodCenter`-to-`c1` distance and an unnamed
  component-75 HLOD-level byte. Both callbacks acquire the exact
  Material/Mesh/shadow-proxy-Mesh triplet and append 24-byte
  source/AssetType/handle descriptors at transition context `+0x58`. The
  acquire core already performs manager bookkeeping. Outer task
  `0x181172DD0` combines context `+0x50` deferred entries and `+0x58` direct
  descriptors into a request batch; poller `0x181172750` retains state 0,
  publishes ready state 1, and removes state 2 without publishing a resolvable
  relation. The installed `Streaming load asset %lld failed` resolver path and
  component fallback close state 2 semantically as load failure. Once pending
  is empty, the task projects the batch through context
  `+0x60/+0x68/+0x70` and invokes `LoadingToLoaded`, connecting the requests
  to the pinned Material/Mesh/shadow-proxy runtime writers and LOD availability
  updates. Its four direct calls are also closed: one in the grid-load state
  driver and three entity-set branches in the Streaming gameplay batch update.
  The next update layer is now separated rather than inferred. HG internal-call
  entry 614 names `StreamingGameplayManager::Tick_Injected`; its binding jumps
  to `0x181174750`, whose direct call at `0x18117486A` enters the batch update.
  Entry 615 names a distinct `TickResource_Injected` core at `0x181174AD0`;
  it has no direct call to the component-67 transition task or request poller,
  though indirect participation remains possible. The grid path is driven by
  a native registered callback: constructor code stores thunk `0x180FC5F10`
  in global slot `0x1821A87F8`, Unity registration records that slot address,
  and the hash-pinned chain reaches manager, scene, grid, grid-load driver, then
  transition task synchronously. The managed host is now closed separately.
  Virtual `GameSceneManager.Tick` calls `BaseGameScene.Update`, then
  `DynamicStreamingScene.Update -> TickSystem`. `TickSystem` first invokes
  `TickResource_Injected` on field `m_gameplayManager` at `+0x20`, then walks
  `m_validSystems` at `+0x180` through virtual Tick slot 19. `_InitTickStatus`
  constructs `DynamicSceneEcsSystem` and adds it to `m_systems` at `+0x170`;
  that slot-19 implementation invokes `Tick_Injected` with batch limit
  `0x800` when its opaque state `+0x54` equals 2, otherwise `0x100`.
  The native callback's exact lifecycle phase/thread, the virtual caller/thread
  above `GameSceneManager.Tick`, the stripped state-2 enum symbol, and standalone
  component names remain open; an `Update` method name alone is not evidence of
  Unity main-thread execution.
  The complete hash-pinned `StreamingSceneManagerScript..ctor` has nine Mono
  converter bindings (bits 12/14/15/19/25/29/32/33/40) and no HGTree bit-41
  binding, excluding that static constructor delegate route. A direct installed-VFS
  export also closes all 117 `HGMeshRendererData` objects in chunk
  `7064D8E2/B428...chk`: their 1,449 valid descriptors cover IDs
  `0..11,18,29,44,46,47,48`, with no ID 67 and no layout failures. This
  excludes the generic serialized renderer-data blob family without naming
  the remaining native producer. The installed UnityPlayer native descriptor
  table now closes the top-level serialized class IDs as `HGTree=0x2C9CB981`
  and `HGTreeData=0x59383C91` (with the two HGMesh IDs as positive controls).
  AnimeStudio now recognizes those exact IDs and admits explicitly selected
  generic TypeTree objects into an otherwise minimal AssetMap. One controlled
  full-StreamingAssets scan produced and re-exported the same 117 unique
  `HGMeshRendererData` identities but zero `HGTree`/`HGTreeData` objects. The
  static top-level Unity object surface is therefore excluded. The proprietary
  `.bytes` route is now substantially narrower too: managed
  `StreamingSceneV2.Create` reaches dedicated HG icall 621 and native loader
  `0x18117B200`, with the exact path builder, request callback, and custom
  interleaved-token LZ4 decoder pinned. All 83 serialized `StreamingMapConfig`
  roots have matching `StreamingChunkInfo` files. A complete scan of 51,012
  main Streaming payloads (3,088,714,060 decoded bytes; 3,084,834 union
  records) finds neither HGTree bit 41 nor HLODGroup bit 11 in tag-1 component
  vectors. Native dispatch tables identify tag 1 as MonoEntity, tag 2 as
  native ECS, and tag 3 as Proxy; installed byte-backed enums close all 14
  `ECSEntityType`, 11 `ProxyEntityType`, and 10 `EntityTransition` values.
  The exact native callback map proves component 67 is shared by type 0
  `Render` and type 9 `MergedRenderCollider` across transitions 1/3/6/8.
  The complete scan counts 34,672 Render records
  across 1,384 files and 2,576,964 MergedRenderCollider records across 4,720
  files. Entity ownership is therefore closed. Root fields 6/7 pair native
  entity-ID groups with archetype descriptions; each description carries
  8-byte `(int16 componentId, int16 elementSize, uint32 auxiliary)` rows and a
  serialized initial-data blob. Component 67 is exactly `(67,24)`, and
  hash-pinned copier `0x1801F95E0` copies each
  `entityCount*elementSize` slice directly into native ECS storage. Across all
  83 map scopes, its 1,230,041 distinct entity IDs exactly match the type-0/9
  owner set. The 1,305,818 serialized occurrences initialize LOD count 1..6,
  fixed state bytes `8/8/8/0/0`, the `+0x06` reserved word to zero, zero
  readiness, and 102 cumulative renderer range patterns; repeated map/entity
  records are byte-identical. Thus the
  LOD-count/range producer is now closed to original game-binary data rather
  than a later `ConvertFrom` inference. Only the standalone native component
  name remains open. All 1,576
  DynamicStreaming init/stream payloads contain only tag-2 records and no
  component entry. The 457 dynamic `fb_main` files do contain 2,828
  `FBDynamicSceneTreeRootComp` rows, but their gameplay identities
  `EDynamicSystem.Tree=11` and `EDynamicSceneData.TreeRootComp=64` are separate
  from both serialized HGTree bit 41 and ECS component 67. The compact
  hash/count evidence is
  `Generated/OriginalData/CharInfoPresentation/streaming_scene_v2_payload_census.json`.
  Native entity-type registration core `0x1801FAEC0` now closes each input as
  an 8-byte row `(int16 id, uint16 size, uint32 cumulativeOffset)`, with
  component storage beginning at byte 8 and archetype size/offset lookups at
  `+0x42/+0x44 + 8*rank`. No installed-code immediate encodes `(67, 24)`, so
  the recovered StreamingSceneV2 descriptor/blob path, rather than a static
  descriptor constant, supplies the ID-67 row and initial LOD values.
  Writer `0x181157760` also closes a second direct-availability initialization path:
  it either marks every LOD and companion subresource available or marks only
  the terminal LOD and the exact readiness range selected through the
  cumulative endpoints. It consumes the serialized LOD count/endpoints but
  does not infer them. Dispatch
  segment `0x181079FB1` selects the recovered LOD job variants. The direct route uses
  `minSquared < distanceSquared <= maxSquared`; the scaled route uses
  `(viewFactor*instanceScale)/max(0.0001,distanceSquared)` and the same
  exclusive-lower/inclusive-upper interval after ArtTag scaling. Its upstream
  controls are now closed: builder `0x18106EAD0` emits a `0xC30` payload and a
  64-byte packet containing its pointer plus the 56-byte
  `LODCrossFadeConfig`; packet `+0x3C/+0x3E` are `enableDither/lodBias`.
  `HGCullingSystem` stores squared `parentLODBias` at state `+0x180` and the
  two 256-entry ArtTag encodings at `+0x184/+0x584`. Nonzero view `lodBias`
  multiplies both copied tables by `(1 + lodBias/255)^2`.
  `HGLODStreamingSystem.Get/SetArtTagLODStreamingOffset` directly owns the
  256-int table at state `+0x74`; payload `+0x82C` copies it, and every LOD job
  adds its signed entry to the selected index before clamping to
  `[0,lodCount-1]`. The
  former index-10320,
  `0x180175A10 -> 0x180A5E320`, and virtual-slot conclusion is retracted: it
  crossed the HG table boundary into unrelated Animator code. The standalone
  component-67 native type name and target-frame survivor rows remain open. The
  complete installed CullView-named census found no separate
  `sceneCullingMask` consumer: the field is forwarded by the constructor but
  not read by the scheduled view loop, either selected predicate, fence/reset
  lifecycle, child-view path, or a post-dispatch packet copy. The complete
  0x4E1-byte UnityPlayer candidate core and the candidate-to-`VisibleLight`
  producer and `CullLightsInternal` lifetime wrapper are now hash-pinned in the
  maintained audit, so the native gate/sort/output-cap/row-conversion/result-
  ownership boundary cannot silently drift.
  `tools/decode_light_cull_capture.py` now consumes a detached JSON artifact
  only after checking the exact build hashes, 0..256 count, pointer/null rule,
  exact `count * 148` raw-row length, and converter-written zero at
  `VisibleLight+0x84`; it decodes the source-closed type, priority, range,
  spot angle, position, finalColor, specularIntensity, and localToWorldMatrix
  fields without attaching to the retail process; its matrix columns 2 and 3
  are emitted directly for the source-backed GetForward/GetPosition b31
  inputs. Converter-unwritten ScreenRect/ScreenSpaceArea fields remain
  deliberately unclaimed. It is an intake/validation tool, not a substitute
  for the still-missing authorized target-frame capture.
  A direct census of the
  installed `UnityPlayer.dll` native strings/RTTI (with the matching
  `GameAssembly.dll` build) adds no unambiguous name for component 67:
  `HGTreeComponent`, `HGTreeRenderer`, `HGTreeInstance`, `HGTree`, and
  `HGTreeData` are each already tied to distinct managed/serialized surfaces.
  Keep the component unnamed and fail closed rather than reusing one of those
  labels as a speculative native type.
- Installed `LightBinningXYCS`/`LightBinningZCS` recovery now pins all eight
  D3D11/Vulkan kernel programs plus the exact 28-byte `BinningData` ABI,
  32-pixel/2,048-slice layout, 8x8/64x1 dispatch formulas, and shared light +
  reflection word offsets. The existing Unity light producer matches those
  equations for the isolated Overview rig. A default-off raw bridge now
  publishes its exact light words plus the source-closed zero-local-reflection
  tail through canonical `_BinningBuffer`; all 90,848 words at 3840x2160 read
  back bit-exactly on D3D11/D3D12. Under the same default-off selector, the
  pipeline now co-publishes the exact `T_hdri_env_char_01` reflection oct/global
  resources in the same camera command stream without overwriting that buffer;
  the full 260-vector `ReflectionProbeGlobalData` and original D3D11
  `EndfieldCB2` 259-vector prefix now read back bit-exactly on both APIs, while
  both readiness gates, the 576x576x32 texture, and source rejection also pass.
  The native 128-byte `VisibilitySHConstData` b33 layout,
  fixed rows and frame dimensions/scales are now source-closed. The producer's
  pinned 128-byte zero-fill proves untouched rows 5..7 are exact zero, so all
  32 words—not only the selected consumer's bytes 32..63—read back bit-exactly
  on D3D11/D3D12 under that same frame gate. The source-backed Wulfa capsule
  pass now publishes its canonical `_VisibilitySHRT` only when that gate is
  ready: D3D11/D3D12 produce the same 320x360 RGBAHalf hash with 20,006
  nonzero pixels, while an upstream-off run keeps canonical publication closed.
  A retail settled-frame capture, exact retail posed/view-culled records,
  target-frame light survivors, and the pass-0 consumer remain open.
- The selected retail `OverlayShadow` fragment now has a maintained,
  hash-pinned verifier for its `_TaaJitterStrength`/clustered-light ABI and
  the native Halton jitter producer (`HGCamera+0x68 -> ShaderVariablesGlobal
  +0x130`). The installed TAA pass order is Dilation -> MaskDilation ->
  Resolve, and the recovered light-binning bridge now matches its promoted
  source constants. This closes the normal static jitter/input contract only;
  IFix-wrapped history constants, shared-depth overlay scheduling, and settled
  retail TAA frames remain open.
- The maintained `audit_taau_history_contract.py` now closes the complementary
  source-backed history/resource ABI. Current retail metadata identifies the
  `TAAUPassConstructor` history fields and methods; the decompiled constructor
  proves the `historySceneColor`/`prevTAAUState` gate, the quality-0 depth/MV
  validity extension, the 192-byte `TAAUConstants` upload, and persistent
  render-size dilated depth/MV textures preserved across frames. It also pins
  the quality-dependent Dilation -> MaskDilation -> Resolve schedule and the
  history/size constant lanes. This is still static evidence: live
  `TextureHandle` identities, settled weights/internal extent, reset state, and
  any IFix replacement remain capture-only/open. The scene-level handoff is
  now explicit: `HGRenderPathScene` supplies `historySceneColor` to TAAU and
  `OnPostRendering` preserves either the current output or the prior history
  on a skipped frame, then resets `fastConvergeState`. Run
  `python tools/audit_taau_history_contract.py --check` after refreshing the
  installed evidence.
- The selected original pass-0 `_TransformVariables` b30 reads are now
  source-closed for view, inverse-view, inverse GPU view-projection, and camera
  position. The default-off same-frame publisher reads all 1,312 bytes back
  identically on D3D11/D3D12; its 13 selected vectors match and the other 69
  history/jitter/stereo rows remain zero. Pass 0 is still disabled.
- The selected original pass-0 `_LightDataBuffer` b31 consumer is now closed
  for the isolated Wulfa/Zhuangfy CharInfo fixture. Native allocation/packing
  proves `6 + 256*8` float4 (32,864 bytes), not the earlier assumed `128*16`:
  the directional header comes from the exact CharInfo environment, while each
  CharacterOnly row reads zero OBB flags then exits before general punctual or
  shadow words. All 8,216 words match through `_LightDataBuffer` and the D3D11
  `EndfieldCB4` bridge on both APIs; unknown words remain zero, same-frame
  activation is fail-closed, beauty is unchanged, and pass 0 remains disabled.
  The installed `PrepareCPUData` body now also closes the complete eight-float4
  write schema for both Spot and Point/linear-extension rows. The exact
  selected-aspect Gacha room contribution is one Spot, six ordinary Point,
  and four positive-length linear-extension Point lights; all eleven enable
  authored OBB culling and are unshadowed/cookie-free. Each has an exact
  serialized `HGAdditionalLightData` component rather than an unresolved
  default. Installed `GetLightNPRData`/`GetLightAdditionalData` close the
  32-byte return layout and b31 record3.yzw, record4, and record6.w: every row
  uses NPR type 0 with `(1,1,0,0)`, `CharacterOnly=false`, and falloff `-1`;
  volumetric intensity is 0/1/10 on 2/5/4 rows. The same body now closes the
  OBB chain as inverse TRS of authored relative position, ZXY orientation, and
  half extents, packed row-major into six half2 words at record5.xyz/6.xyz.
  Installed `HGUtils.PackTwoHalfValuesAsFloat` and
  `Unity.Mathematics.math.f32tof16` close the word order and IEEE conversion.
  UnityPlayer icall 2471 (`Matrix4x4::Inverse3DAffine_Injected`) now resolves
  through stub `0x1800A2020` to the hash-pinned `0x180569BD0` scalar
  determinant/cofactor body; the native float32 order and `-0` sign-mask
  candidate bits are replayed for all 11 rows. Native candidates map authored
  corners back to the unit box within `0.002611`; the `Spot Light (12)`
  one-float32-ULP boundary is now explained by the source body. Retail signed-
  zero/packed-word capture and the preceding Quaternion.Euler runtime order remain open.
  The adjacent UnityPlayer icall 2470 (`Matrix4x4::TRS_Injected`) is now also
  source-closed: its `0x1800A1BB0` wrapper, `0x18056CB40` scalar column-scale /
  position-copy body, and `0x18056B8A0` quaternion-to-column-major helper are
  hash-pinned and replayed. The managed `Quaternion.Euler` wrapper and exact
  float32 degree-to-radian/half-angle input are now source-closed as well;
  UnityPlayer icall 2489, its `0x180567590` body, and all six native sin/cos
  call targets are pinned. The GameAssembly lazy resolver now also has a
  hash-pinned resolver string, `0x180059FC0` call, and slot load/store at
  `0x18F36FAC8`. The audit maps the installed UnityPlayer image
  with `DONT_RESOLVE_DLL_REFERENCES` and calls the pinned `0x1800A5010` wrapper,
  yielding bit-exact native sin/cos quaternion candidates for all 11 authored
  rows. The wrapper's explicit native order-4 immediate and six-entry jump
  table are also pinned (case offset `0x425`). The runtime slot/patch state,
  patched IFix output selection, and retail packed-word capture remain open.
  After the installed-data refresh, Persistent VFS block `DAFE52C9`
  (`IFixPatchOut`, block version `23167343`) contains the current
  `Gameplay.Beyond.patch.bytes` at 86,926 bytes, SHA-256
  `baa28ae497e64d94e152886622bbe5fb391199bcbf8366e2df91591c9a9f172c`, with
  32 signature targets. `tools/refresh_installed_ifix_patch_state.py` now
  regenerates the ignored report and extracted payload from the live local
  block; `verify_installed_ifix_patch_state.py` passes against that refreshed
  evidence; the installed-patch verifier now reports the live target count and
  checks refresh metadata, and the LightCull cap audit validates the report's pinned
  GameAssembly/patch consistency instead of a stale whole-report SHA-256. The
  target list adds `FacQuality.Apply`,
  `NpcSpaceShipController.OnPauseStart`, and `CharacterPhotoSystem.OnExitSystem`,
  while dropping `BlightMiasmaBrain.Release`; none is a searched
  render/Character-Info owner. The live IFix slot value and patched output
  selection still require an authorized runtime capture.
  Pinned
  `globalgamemanagers` objects prove
  Linear color space and linear light intensity; all 11 rows disable color
  temperature, distance/far-show falloff, animation, multistate, and flicker.
  UnityPlayer `finalColor`, `Color.linear`, animation-disable, and flicker
  bodies therefore close exact b31 record0.xyz bits as linearized authored RGB
  times intensity, with falloff/flicker both 1. The two `PrepareCPUData`
  branches close record0.w as `float(lightKind + 2*shadowOnly)`: the one Spot
  row is exactly 0 and all ten Point/linear-extension rows are exactly 1.
  Record0 is therefore fully closed. The metadata-backed
  `VisibleLight.get_range` field at `+0x68` and the native scalar divide close
  record1.w for all 11 rows. Hash-pinned half-angle scaling and the original
  scalar-cosine body close record2.z plus the Spot row's record2.w; the Point
  branch closes record2.z as `HGSharedLightData.length` (`-1` on six ordinary
  Points, `18` on four linear extensions). Target-frame record1.xyz/record2.xy,
  live Point record2.w/record3.x shadow-face cache-index values, runtime
  carry-in, and final byte-exact b31 rows remain open. The Point/linear
  branch's `record2.w` contract is now
  source-closed separately: it constructs six `LightCaster` face requests in
  order 0..5, calls `GetShadowCacheIndexForCaster` for each, maps `-1` to the
  shader sentinel `255`, and packs faces 0..3 into `record2.w` plus faces 4..5
  into the low bytes of `record3.x`. The six target-frame cache-index values
  remain capture-only; this closes the producer packing rule, not their live
  contents. The original `GetShadowCacheIndexForCaster` resolver is now
  source-closed too: a dynamic-list match returns `40 + dynamicOrdinal`, a
  static-list match returns `PunctualLightCachedShadowDesc.shadowCacheSlotIndex`
  at native `+0x0C`, and an unmatched caster returns `-1`; null manager/list
  state fail-fast. Therefore the `-1 -> 255` mapping is confirmed as the
  unavailable-cache sentinel, while the six target-frame indices remain
  capture-only. The native `HGSharedLightData` getters are also pinned: the
  packed `m_CasterProperties` masks are `0x01` (dynamic caster), `0x02`
  (static objects), and `0x04` (dynamic objects). All 11 selected room lights
  serialize `m_CasterProperties=6`, `m_PointLightShadowCasterFaces=-1`, and
  `LightShadowCasterMode=0`. Because those caster bits are enabled, serialized
  `shadowType=0` is not evidence that the runtime resolver must return `-1`;
  the hash-pinned `GetShadowRenderType` body (method `0x886`) now closes the
  exact gate: `WrappersManagerImpl.IsPatched(0x886)` selects either the native
  path or `GetPatch(0x886) -> __Gen_Wrap_874`. When unpatched, a static request
  directly returns `castStaticObjects=true, castDynamicObjects=false`, while a
  dynamic request follows the three pinned caster-property getters. Runtime
  wrapper-table membership, patched return flags, and live caster-list
  membership remain capture/runtime-bound. The adjacent `GetRendererConfig`
  method (`0x887`) is also hash-pinned: its unpatched projection is
  `0x4800 | (castStaticObjects ? 0x1000 : 0) |
  (castDynamicObjects ? 0x2000 : 0)`, while its patched route is
  `GetPatch(0x887) -> __Gen_Wrap_875`; both runtime wrapper-table entries and
  patched flag returns remain open. The same native body now pins the
  following `GetECSRenderFlags(0x888)` projection: defaults are object flags /
  masks `0x08000002` and render flags / masks `0x02080000`; exactly one of the
  static/dynamic caster outputs adds `0x04000000` to object flags and
  `0x01000000` to render flags, and the enabled+active HDPLS-character-light
  path sets object-flags-mask bit 28. Its `__Gen_Wrap_876` route and runtime
  return values remain open. The same native body now pins the
  `WrappersManagerImpl.IsPatched`/`GetPatch` lookup contract itself: both use
  the manager singleton at `0x18E28EC48`, follow manager `+0xB8` to the active
  table, read its entry count at `+0x18`, and use 8-byte entries beginning at
  `+0x20`. The signed `IsPatched` gate, cold unsigned bounds check, null-entry
  test, and `GetPatch` pointer load are hash-pinned in the installed
  `GameAssembly.dll`. This closes table semantics, not live membership:
  whether entries `0x886/0x887/0x888` are populated and what their wrappers
  return remains runtime-boundary evidence.
  The same native body now pins the
  transform producer order:
  `GetForward` → `PackNormalOctRectEncode` supplies `record2.xy`, while
  `GetPosition` supplies world-space `record1.xyz`; the selected deferred
  consumer subtracts camera position at read time. The target-frame positions
  and encoded directions remain capture-only. The helper bodies are now pinned:
  `GetForward` reads `VisibleLight.LocalToWorldMatrix` column 2 and
  `GetPosition` reads column 3 via `Matrix4x4.GetColumn` plus
  `Vector4.op_Implicit`; the pinned bodies contain no extra forward
  normalization. `PackNormalOctRectEncode` takes the resulting float3 and
  emits the float2 octahedral rectangle encoding. Retail IFix gates are
  `0x77A`, `0x77D`, and `0x77B`; patched-branch return values and target-frame
  values remain runtime/capture-boundary evidence. The pinned SceneLight6Rarity
  hierarchy and `rotatehouse` transform now recompose all 12 authored room
  world positions and directions with float32 lane rounding, bit-matching the
  independent cull-view audit. These are authored static candidates only; they
  do not replace a retail `LightCullResult` capture. The unpatched
  `PackNormalOctRectEncode` call chain is now also closed: abs/dot/L1 reciprocal,
  float3 multiply, clamp, and `CopySign` produce
  `u=CopySign(clamp(0.5+0.5*(n1.y-n1.x),0,1),n1.z,true)` and
  `v=n1.x+n1.y`; all 12 authored `record2.xy` candidates are bit-generated
  from that formula. IFix patched returns and retail target-frame values remain
  capture-only.
- Deferred binding 34 is the exact 11,440-byte `ShadowData`; the selected
  resolver reads only its Punctual rows `c64..c400` (bytes 1,024..6,415).
  Native allocation, four-section copy/bind transport, atlas sizing/format,
  cache scheduling, point/spot matrix math, PCF_3x3 bias, strength fade,
  normalized rects, and texel size remain binary-source-closed. A default-off
  same-frame publisher now closes the isolated CharInfo punctual subset:
  Wulfa row 4 produces spot slot 40 and Zhuangfy row 4 produces point slots
  40..45, each with the matching `6144x4096` D16 atlas. The full 715 vectors
  and D3D11 `EndfieldCB5` 401-vector prefix read back bit-exactly on both APIs;
  all unowned sections stay zero, missing prerequisites fail closed, and Wulfa
  active/control beauty is identical. Every isolated light is `CharacterOnly`,
  so the selected pass-0 consumer exits before its first b34 or atlas read;
  pass 0 remains disabled. General-scene/static-cache rows, retail physical
  resource identity and settled atlas pixels, runtime IFix/setting overrides,
  and the non-punctual sections remain open.
- `ShaderVariablesGlobal` b35 is no longer an undifferentiated 3,200-byte gap.
  A hash-pinned selected-body audit finds 33 referenced fields and closes exact
  installed reset output for atmosphere c71..c76, height fog c77..c82, and
  disabled volumetric fog c83..c87. Current constructors, `IsActive`/camera
  getters, and all selected/global/LookDev VolumeProfiles close c30 as
  `(0,0,1,1)`; the code default and every shipped setting override close
  c31.x as `reflectionProbeMaxSampleMip=7`. Native `HGCamera.UpdateFrustum`
  constructs c3 as `(-1, near, far, 1/far)` and the selected serialized
  Zhuangfy Overview lens is exactly near=0.1/far=50, closing live c3.y as 0.1.
  The selected route also closes perspective c4.w, mip bias c26.x,
  binning/environment rows c28/c29, inactive IV params c132..c134, and wetness
  c156.x; frame count is behind the exact-zero volumetric gate. The enabled
  weight-1 CharInfo environment volume selects `CharInfo_Env`; native
  `UpdateShaderVariablesIrradianceVolume` and `GetCoefficientsL1` prove that
  c135..c137 each equal the serialized ambient-SH reorder
  `(SH3,SH1,SH2,SH0) * skyDirectIntensity`, or exactly
  `(-0.0075507611,0.4722373188,0.0121708093,1.0963056087)`. All selected b35
  value producers are source-closed. A default-off publisher now binds all 200
  canonical vectors plus the 157-vector `EndfieldCB1` prefix. D3D11/D3D12
  read back 800/800 and 628/628 words exactly; all unselected rows stay zero,
  c28 keeps its raw integer bit pattern, same-frame Wulfa activation succeeds,
  and missing canonical prerequisites fail closed without changing D3D12
  beauty. Pass 0 remains disabled.
- Deferred binding 37 now has its exact native 2,560-byte `LightCookieData`
  initialization/upload and `cookieIndex >= 0` consumer guard closed. The
  source-closed Wulfa/Zhuangfy Overview lists have no cookies, so a default-off
  all-zero publisher is exact for that narrow path and is bit-verified on
  D3D11/D3D12 (640/640 words). Cookie-bearing or non-isolated frames fail
  closed; non-empty retail atlas history, pixels, transforms, and settled
  whole-scene values still require capture.
- Deferred binding 38 now has its native `HGHDPLSCharacterShadowManager`
  owner, per-frame reset, 3,568-byte reflected layout, push-pass packing, and
  selected `.y`-only consumer closed. Inactive frames clear all 56 HDPLS
  channel selectors, proving the selected resolver falls back to the punctual
  atlas. Do not publish a full zero fixture: matrices/params persist, trailing
  values are frame-derived, and the native callback logically binds 3,552
  bytes while writing the reflected final float4 at byte 3,552. Installed
  `UnityPlayer` recovery closes `CBHandle.size=3,552`, 16-byte length rounding,
  and 256-byte allocation-start alignment: the next allocation begins at byte
  3,584, so the final CPU write is safe in padding. The recorded target forces
  D3D11; its backend rounds 222 constants to 224 before
  `PSSetConstantBuffers1`, exposing 3,584 bytes and proving c222 GPU-visible.
  Native getter/constructor recovery also closes the six HDPLS setting offsets
  and current defaults: enabled, atlas height 2,048, reduced screen-space
  resolution enabled, and zero depth bias/normal bias/softness. With
  `S=max(256, atlasHeight)`, the atlas is `2S x S`; requests use a `4x2` grid
  through eight entries or `8x4` above eight at the default. Normalized tile
  rectangles, `(1/(2S),1/S,2S,S)` texel size, `(softness,0,0,0)` global params,
  `float4(worldPosition,0)` screen-space positions, and both selector writes are
  exact. The installed unpatched character-matrix path is also closed:
  `Bounds.extents` supplies a bounding-sphere radius, the light aims at the
  bounds center with a `1e-5` degenerate-direction fallback, the cone is
  `clamp(2*asin(radius/distance),0.1°,179.9°)`, and the derived TRS plus
  light near/far/guard feeds the exact reversed-Z spot-shadow transform. Depth
  and normal bias also reach the caster pass exactly. Resource recovery now
  distinguishes the request-gated `2S x S` D16 `_HDPLSTex` caster atlas from
  the reduced/full-size RGBA8 `_HDPLSScreenSpaceShadowMask` consumed by
  deferred binding 22. Their RenderGraph dependencies and global publication
  are closed; inactive frames clear all selectors and bind white to both slots,
  so stale resources cannot escape. The current hash-pinned installed
  Persistent IFix snapshot and refreshed overlay both decode to 32 targets;
  the overlay still replaces neither `0x877` nor `0x890` owner method,
  closing the current on-disk branch choice. The maintained
  `refresh_ifix_deferred_reports.py` projection keeps the deferred contracts
  synchronized with that snapshot without reformatting their source evidence;
  future/network patches remain a version boundary. Live input values, active
  rows/selectors, unused persistent rows, atlas texels, and resolved RGBA
  pixels remain capture-only.

- The installed no-reload CharInfo V2 irradiance route is now closed as
  inactive. `SetMap` enters native clear state 4, releases all six full-size
  clipmaps, then an empty or unresolved path settles in state 2. The result
  publishes one shared 1x1x1 Unity default 3D zero texture to all six slots and
  default parameters `0/0/0/(0,1/3,0,0)`; it does not retain zero-filled
  128x64 clipmaps. `/aiTest/index.bytes` is absent from all 224 shipped IV
  files. `ReloadIndexFileV2` and `StreamingInNewMapV2` each have only their
  IL2CPP method-table pointer, with no direct managed, Lua, or installed IFix
  owner. Generic reflection/external reload remains a boundary; if observed,
  its caller path, populated atlas dimensions, parameters, and texels must be
  recovered separately.

## Main rendering gap

The largest missing piece is the coupled retail frame contract:

- HGRP light scheduling, culling, cookies, and irradiance;
- character shadow atlases, screen shadows, stencil, and VisibilitySH;
- shared depth, GBuffer, motion, and deferred `SphereOutside` resolve;
- exact material variants, native mip payloads, and live per-renderer state;
- exposure, history, post-processing, and final composition;
- retail-frame validation across all characters.

Current images are recognizable but remain flatter than retail, especially on
faces, pale cloth/armor, hair, dark hardware, and contact/ground shadows.

## Main animation gap

Recovered clips are not equivalent to the complete runtime. Remaining work:

- controller transitions, interruption, blending, and root motion;
- broader exact Avatar/clip transport;
- grounding, foot IK, hand targets, and constraints;
- live facial emotion, lip sync, eye direction, look-at, and events;
- secondary motion, wind, cloth, hair, and dynamic bones;
- item/deco/FX lifecycle and gacha timing;
- non-playable controller, rig, animation, and VFX execution.

Do not enable generic Humanoid animation for enemies or props without
actor-specific source evidence.

## Non-playable limitations

The 94 enemy, 29 ability/prop, and six ambient-NPC baselines prove enumeration,
hierarchy, and admitted geometry dependencies—not authored appearance.
Runtime VFX, modular assembly, exact keywords/passes/queues, texture
descriptors, animation, and material overrides remain incomplete.

## Maintained workflows

```bat
cd unity_endfield_graph_shader_lab

.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat

.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat

.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
.\verify_recovered_light_binning_constants.bat --all
.\verify_recovered_light_cookie_data.bat --all
.\verify_recovered_shader_variables_global.bat --all
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated character assets are rebuildable. Fix generators, importers,
runtime code, or shaders rather than hand-editing generated prefabs.

## Highest-value next work

1. Resolve the exact native type names for component 67, its 68..74
   companion-capacity family, and component 75 from remaining pure-native
   descriptor/RTTI registries; lifecycle slots, transition-1 load requests,
   transition-6/8 teardown, managed layouts, serialized LOD-count/range
   producer, and HGTree renderer-list filter callers are closed. Then recover
   the retail survivor list at the exact `HGCamera.DoECSCulling` return boundary,
   starting from the source-closed 18-row authored input and exact
   selected-aspect 17-row authored result while preserving runtime/custom
   carry-in and other display aspects; populate exact shadow, depth, GBuffer,
   irradiance, non-empty cookie, and VisibilitySH inputs afterward.
2. Validate selected paths against accepted retail captures.
3. Extend exact texture/mip and material-variant support only where visible.
4. Generalize animation from a second exact Avatar/clip oracle.
5. Implement controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
6. Upgrade representative non-playable families before making broad parity
   claims.

Every production value must come from serialized data, native behavior, or a
valid runtime capture. Unknown values stay neutral, diagnostic, or disabled.

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
- The playable mesh-identity audit now passes all 31 generated prefabs (460
  LOD0 renderer rows, 434 source mesh PathIDs, and 434 prefab GUID bindings),
  including the separately-owned Zhuangfy piaodai Timeline effect clone.
- The previous 30-character Overview capture set remains valid and nonblank;
  Liino is imported and awaits the next capture refresh.
- Playable UI recovery contains 779 body clips and 348 private item/deco clips.
- Roster discovery now treats `structured/Persistent/Table/CharacterTable.json`
  as the current patch overlay and resolves AnimatorControllers from both
  StreamingAssets and Persistent. Liino proves this boundary: her roster row,
  CharInfo camera/light/portrait, 25 body UI clips, 27 private-deco clips, and
  external UI controllers are patch-layer data, while her post-model and exact
  Grounder remain in StreamingAssets.
- Shared `operator_lights.json` now contains the expanded 31-character roster;
  isolated Wulfa/Zhuangfy ShadowData and Gacha audits hash only the actor rows
  they consume, so a Liino/roster addition cannot hide a relevant light-data
  drift or invalidate an unrelated source boundary.
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
  check is `test_generated_chen_prefabs_keep_mesh_guid_sets_disjoint`. The
  current source audit pins Chen to PathID `3146666496379329674` from
  `98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk` and Chenpast to PathID
  `-1377940589218415556` from `B428C352B17C75CA29122CAACC037A59.chk`; their
  body index-buffer hashes also differ, so this is not only a naming/container
  distinction.
- Selected CharacterNPR, eye, hair, shadow, material, particle, and gacha
  presentation paths have source-backed diagnostics.
- The CharacterNPR PreGBuffer/canonical-depth owner contract now passes its
  source and generated-material checks, including the installed
  `DepthCharacterOnly` state and owner-before-opaque chronology. This remains
  a fail-closed diagnostic path; it does not claim live retail frame parity.
- The refreshed Skin `PreGBuffer` DXBC fragment is now decompiled through the
  repo-local Ruri tool and pins the source MRT boundary: `Target0` is zero,
  `Target1` carries motion-vector data (`z=1`, `w=0.4`), `Target2` carries
  packed 10-bit selector bits, `Target3` carries octahedral world normal
  (`z=0`, `w=0.4`), and `Target4` carries the material/color payload. The
  pass is `DepthCharacterOnly` with stencil `Ref 36 / Always / Replace` and
  the `HG_ENABLE_PER_OBJECT_MV` + `SRP_INSTANCING_ON` variant. The maintained
  lab now also writes the source-shaped material/color payload into a
  default-off `R8G8B8A8_SRGB` GBuffer C sidecar and validates its readback;
  motion vectors remain unbound. The paired source vertex DXBC now closes the
  producer-side history boundary: `TEXCOORD_3` is current clip x/y/w,
  `TEXCOORD_4_1` is previous skinned/object clip x/y/w, and the variant
  consumes `_NonJitteredViewNoTransProjMatrix`,
  `_PrevNonJitteredViewNoTransProjMatrix`, `_PrevCamPosRWS_Internal`, and
  `unity_MatrixPreviousM`. This is more than a camera-only delta: the previous
  skinned/object path is separately generated, so the lab does not publish a
  guessed motion lane. The C sidecar is not consumed by the retail resolver
  yet, so this closes a producer input without claiming full deferred
  publication. Eye's PreGBuffer uses a different pass index but the exact same
  6044-byte vertex DXBC/decompilation, so this history boundary is shared by
  Skin and Eye rather than a Skin-only special case. Eye's fragment keeps the
  same five MRT topology while its oct-normal alpha is `0.7` rather than Skin's
  `0.4`. The current export audit reports the five-MRT contract and this
  explicit subset. The refreshed current `CharacterNPR_Hair` export now closes
  the third family too: it uses the exact same 6044-byte vertex DXBC and
  decompilation (pass index 3), while its fragment keeps the five MRT lanes,
  sets the oct-normal alpha to `1.0`, and multiplies sampled color by the
  per-material tint words. This is a family-specific payload distinction, not
  a generic Skin/Eye alias. The current generic `HGRP/CharacterNPR` export is
  now pinned as a fourth source family: its base `HG_ENABLE_PER_OBJECT_MV` +
  `SRP_INSTANCING_ON` PreGBuffer vertex is byte/text-identical to Skin/Eye/Hair,
  but its fragment has `Target3.w=0.0` and the sampled-color × tint `Target4`
  lane. Its AssetMap identity is PathID `-7822190029627442914` at offset
  `185104054` in the current `19F0903A...` chunk; the generic fragment is not
  substituted with Hair's `Target3.w=1.0` output.
- The default-off screen/direct same-owner audit also passes its Skin/Cloth/Hair
  shader and pipeline chronology checks, including canonical forward depth and
  the separate PreG D32S8 sidecar.
- The CharacterNPR clear-coat audit now covers Liino's three independent
  authored variants (cloth, skill, and skill LOD) instead of collapsing them
  by actor token; all 11 selected source materials and generated `.mat`
  counterparts pass exact PathID, source-hash, property, and mask checks.
- The current installed-data refresh moved `CharacterNPR_Skin` to source
  `19F0903A12BA87C0D43E67E64889B525.chk` (PathID
  `4484747192473637154`). A targeted AnimeStudio export now closes the two
  body material identities and the selected `0120`--`0125` sidecars; all 846
  current ForwardLit metadata records across 141 keyword sets include
  `HG_ENABLE_SCREEN_SPACE_SHADOW_MASK`, with zero current no-screen sets.
  The older no-screen body contract is therefore stale evidence and remains
  fail-closed; its current SPIR-V consumer also pins an integer-pixel
  `_ScreenSpaceShadowMask` load (R = directional scene shadow, G = character
  shadow), the exact directional selector
  `lerp(lerp(1, R, DirectionalShadowParams.x), 1, CharacterParams1.z)`,
  G*alpha and `min(G, alpha, material-shadow-sample)` uses, clustered-light
  bit scanning, and punctual-shadow/rim dispatch.
  `verify_current_character_npr_skin_export.py` records these source and
  variant semantics only, not retail frame parity.
- The current screen-shadow binding audit now makes the remaining connection
  explicit: the lab producer binds the retail-named RG8 resource but keeps
  `contentValid=false`. Skin now has a source-shaped retail R/G keyword and
  integer-load branch, but the producer disables it together with Eye until
  canonical publication is recovered; the older diagnostic texture branch is
  still available for comparison. The audit therefore passes as a fail-closed
  boundary while reporting Skin retail publication and frame parity as open.
- A fresh targeted export of the original `HGRP/ScreenSpaceShadowResolve`
  closes the retail producer side of that boundary. AssetMap PathID
  `-2059563319398876808` comes from
  `hgrenderpipelineglobalsettings.asset` in
  `19F0903A12BA87C0D43E67E64889B525.chk`. Its independent
  `ScreenSpaceShadowResolve_Character` pass binds
  `_CharacterShadowmapTex` plus 15 character world-to-shadow, bias, light,
  and atlas records; it decodes the character index from packed GBuffer0,
  projects with light-facing bias, performs 16 `GatherRed` depth-comparison
  taps, and writes `float3(scene_directional_shadow, character_shadow, 0)`.
  `verify_current_screen_shadow_resolve_export.py` and its focused test pin
  the export/decompilation hashes and these equations. This establishes the
  G producer semantics, but the lab still keeps publication disabled until
  the runtime character atlas upload and target-frame state are validated.
- The lab screen-shadow resolve now mirrors that producer shape: it receives
  the same-frame PreGBuffer selector/normal lanes and character shadow frame,
  chooses scalar or 15-slot atlas transforms, applies the original
  light-facing bias, and performs the 16-tap `GatherRed` depth filter into G.
  Its two attachment passes now also preserve the original stencil ownership:
  scene resolve `Ref 4/ReadMask 7/NotEqual`, character resolve
  `Ref 4/ReadMask 7/Equal`.
  The producer validates camera/atlas/GBuffer ownership before drawing, but
  `contentValid` remains false and Eye/Skin keywords stay disabled because the
  complete retail scene-R publication, full deferred-GBuffer ownership, and
  frame parity are still open.
- The source-shaped scene-R path now carries the recovered final directional
  strength gate for the installed CharInfo environment: the CSM producer
  publishes the serialized `csmIntensity=1.0` value copied into
  `DirectionalShadowParams.x`, and resolve applies it after CSM composition as
  the original `lerp(1, min(sceneShadow, 1), DirectionalShadowParams.x)`.
  This is still diagnostic-only and does not assert that the lab's
  CSM/ASM/cloud state equals a retail frame; Unity `Light.shadowStrength` is a
  separate field and is not substituted here.
- The installed UnityPlayer fallback selector now closes the exact
  DefaultDeferred pass-0 D3D11 pair; both original stages execute once in a
  fail-closed standalone diagnostic, while live frame bindings remain open.
- The refreshed AnimeStudio shader export still preserves the 14 resolver pass
  names and 640 D3D11 variants in one populated LOD subshader; the three other
  serialized LOD blocks are empty fallbacks. Current installed IFix evidence is
  version `23167343` with 32 targets, and the deferred source/report
  fingerprint gates pass. A full verifier invocation can still be stopped by
  an unrelated dirty `HGCompatRenderPipeline.cs` fingerprint, so that run is
  not treated as a complete runtime-parity result.
  After the latest installed-data refresh, a targeted current-game
  `HGRP/DeferredLighting` export re-selected the same source row (PathID
  `6850169740889141214`, offset `102276665`, source
  `19F0903A12BA87C0D43E67E64889B525.chk`) and the same exact D3D11 pair:
  `0096` vertex SHA-256
  `a6afe2c96caa3fd940004ce9ee725886d0f8df683d5f73403278743e32563155` and
  `0097` fragment SHA-256
  `b21a1e35eda1c5bcb60198c6af313799ddcc94d0cee0be9025938f3ba8c56b6f`.
  This confirms the pass-0 binary evidence remains current, while the live
  resolver bindings and numeric frame parity remain open.
  The latest isolated Unity exact-DXBC rerun now passes in the standalone
  player through a native render event: both embedded stages are created from
  the selected bytes, bound for the draw, and produce the changed one-pixel
  result `[0, 0, 0, 1]` (`render_event_count=2`, exact-bound=true,
  `callback_count=0`). The player-side compiler callback is intentionally not
  required; the editor immediate command-buffer check remains fail-closed.
  The native event now recreates all 25 source-texture SRVs from the fixture's
  D3D11 resources before the exact draw (`shader_resource_mask=0x3fffffe`);
  Unity has cleared those slots by the post-draw inspection event, as expected.
  This closes source-texture population in the disposable fixture, while the
  retail target-frame resource ownership and numeric parity remain open.
  This proves exact bytecode execution in the disposable D3D11 fixture only,
  not retail resolver activation or frame parity.
- The deferred resolver input boundary is exercised by actual same-camera
  D3D11/D3D12 compatibility frames. The producer stamps camera, frame, extent,
  and publication serial; stale or cross-camera inputs fail closed. The exact
  D3D11 compact register audit now covers all `t0..t25`: `t11` is the source
  screen-space shadow mask, `t22` is wetness, and `t23/t24/t25` are GBuffer
  A/B/C (`_60/_61/_62`). This corrects the former C/B/A and t22-HDPLS guess;
  source set-3 binding numbers are not D3D11 register numbers.
- The same-frame SphereOutside sidecar publishes resolver aliases `t23=A`,
  `t24=B`, `t25=C` and source identifiers `_60/_61/_62`; validators and the
  generated binding contract lock this order. The sidecar remains non-presented
  and retail pass 0 remains disabled.
- `ENDFIELD_RECOVERED_DEFERRED_EXACT_CONSUMER=1` now submits the exact selected
  resolver DXBC against the corrected same-frame slots into a private D3D11
  output. Two runs reproduce `resourceMask=0x3ffffff`,
  `resourceFailureMask=0`, `constantBufferMask=0x1ff`, all 1,843,200 floats
  finite, and the corrected stable RGBA-float SHA-256
  `b93a4b5a38c96133bf6f0fa95e7ecb5b6fee9a0c46b48b7a85d3dfbf8b34d8c2`
  (`nonzeroBytes=6,441,402`, min `0.3043011`, max `1`). This proves exact
  shader execution and corrected resource transport only; numerical lighting
  comparison, settled retail pixels, and pass-0 presentation remain open.
- The exact consumer now feeds the source-backed Multiscattering LUT at t10,
  zero-cookie LightCookie black at t12, disabled-volumetric-fog 1x1x1 ASTC
  black at t13, same-frame screen-shadow at t11, and the VisibilitySH
  producer's exact LogSH LUT and half-resolution output at t14/t15. Missing
  t14/t15 still fails closed instead of silently selecting a neutral fallback.
  The latest D3D11 runs log the nine source-backed/closed slots plus the six
  inactive-V2 zero-result slots t16–t21 and produce stable hash
  `04f18f095e02b9d2dfcb2263bd6051e988594b4cf82eb264f402482d9be9eae2`.
  It also uses the source-closed inactive HDPLS white fallback at t8, the
  null-CharInfo black CSM ramp at t9, and the disabled-wetness white fallback
  at t22. Only t2/t3/t4 remain generic fallback slots. The current
  `EndfieldRecoveredDeferredExactConsumer` labels t16–t21 as
  `IrradianceV2:zero-inactive-fallback`: this mirrors the source-closed
  missing-map result's shared 1×1×1 zero texel for the inactive fixture, but
  does not claim a live atlas. A direct AnimeStudio `stream --block-type iv`
  probe re-read the shipped Gacha V3 index (1,008 bytes) and payload
  (1,399,240 bytes, SHA-256
  `ccba259839d3b91cf9d32c2edce1d672eb82f489c7aae33014982aa310b351b4`); the
  complete IV inventory still contains zero `/aiTest/index.bytes` files, so
  that legacy Gacha payload remains explicitly barred from CharInfo V2.
- A default-off SphereOutside sidecar now uses the source CharInfo camera and
  transform to produce the exact logical 640x720 SceneColor/SceneMV/GBuffer
  A/B/C formats plus D32S8. All five readbacks are bit-identical on D3D11 and
  D3D12, the presented frame is unchanged, and missing binning/reflection/b33
  prerequisites fail closed. It is deliberately non-presented: canonical
  render-graph lifetime and pass 0 remain open. The current installed
  `RenderWithAlpha=false` route submits no WriteAlpha draw.
- The source `HGRP/Lit` `HGBuffer` motion lane is now pinned independently of
  the Skin PreGBuffer audit: vertex `TEXCOORD_5` carries current clip x/y/w and
  `TEXCOORD_6` carries the separately generated previous clip x/y/w; the
  fragment computes the same signed fourth-root deltas, then blends them with
  the source motion-validity mask (`Target1.z/w`). The default-off
  SphereOutside sidecar now transports the preceding camera VP and
  object-to-world matrices and emits this source-shaped SceneMV for settled
  adjacent same-camera/same-renderer samples using the source non-jittered
  projection; first samples and discontinuities remain neutral. Reflection
  metadata still exposes native
  `unity_MatrixPreviousM`, `_PrevNonJitteredViewNoTransProjMatrix`, and
  `unity_MotionVectorsParamsInternal`. The recovered MeshRenderer now derives
  Unity's managed motion-vector tuple explicitly: SphereOutside's serialized
  `MotionVectorGenerationMode.Object` maps to `(x,y,z,w)=(0,1,0,1)`, while
  Camera and ForceNoMotion are fail-closed alternatives. The shader selects
  current object history for camera-only mode and suppresses unsupported
  deformed-position history, so the static Object producer is closed without
  claiming native previous-history carry-in or skinned/deformed parity.
  The verifier also pins the remaining source MRT payload: `Target2.x/y/z/w`
  carry the sampled MRO/porosity/packed-flag lanes, `Target3.z/w` carry the
  sampled mask and low packed flags beside octahedral normal xy, and
  `Target4.xyz/w` carry the tint-blended base colour with zero alpha. These
  source equations are now evidence-closed. The maintained
  `verify_deferred_gbuffer_payload_contract.py` gate passes all nine producer,
  sidecar, alias, and material checks and reports the remaining three open
  boundaries explicitly: native history/deformation inputs, packed-flag
  inputs, and retail pass-0 publication. The runtime sidecar still
  does not publish these lanes through the retail deferred resolver.
- The packed-flag consumer remains closed against the refreshed installed
  GameAssembly/metadata (metadata SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`). The
  original fragment and generated DXBC read an independent `register(b3)`
  one-vector buffer (`cb3[0].w`), then split its integer bits into `Target2.w`
  and `Target3.w`. The earlier producer census was incomplete: native
  `Beyond.Rendering.CustomPerDrawDataChannelUtils.SetPerDrawData_CharacterParams`
  copies a Vector4 unchanged into renderer custom-per-draw channel
  `CHARACTER_PARAMS_INDEX=2`, and `EntityRenderHelperMaterialController` has
  matching `TrySetCharacterPerDrawData`/controller forwarding. The recovered
  Unity API contract is `Renderer.SetCustomPerDrawData(int, Vector4)`, with a
  logical typed index; native producer disassembly independently confirms
  character params and lit emissive use index 2, emissive-albedo/dissolve and
  VFX alpha use index 4, and Houdini/UV/trail scan use index 3. This recovers a
  source-backed character per-draw producer and proves the runtime slot ABI.
  A current GameAssembly body audit tightens that producer contract:
  `SetPerDrawData_CharacterParams` at `0x18323af00` copies the incoming
  Vector4 to a 16-byte stack temporary, passes `edx=2`, `rcx=affectRenderer`,
  and `r8=&temporary` to a lazy indirect renderer setter slot (`0x18f36f578`).
  That slot is the same one read by the generated
  `Renderer.SetCustomPerDrawData_Injected` wrapper (`0x183e6e280`), which
  forwards `rcx/edx/r8` to UnityPlayer's registered internal call.
  The body has no compute dispatch, buffer bind, or resource `+0xd0` access;
  it ends at the renderer custom-per-draw API. This confirms the channel-2
  producer boundary while leaving the resource-to-GPU upload edge open.
  The original DXBC has no RDEF and the shipped fragment metadata is a
  stale vertex copy. A refreshed targeted AnimeStudio export with bytecode
  sidecars now closes the shader-side half independently: the raw Vulkan
  HGBuffer fragment declares the equivalent uniform at descriptor set 0,
  binding 33 as a four-float block and accesses member index 3 (`w`) before
  the packed-bit extraction. The D3D11 fragment sidecar is stage-confirmed
  but still RDEF-less; the binary Vulkan descriptor/access chain is the
  authoritative cross-platform reflection. The remaining gap is channel 2
  into Unity's resource binding, not the cb3 component itself. The durable audit is
  `Generated/OriginalData/CharInfoPresentation/packed_flags_producer_recovery.json`.
  Installed metadata also closes the producer's packed layout: controller type
  values 8/16/24/32 (rain, wet, wet-global, snow) quantize into byte lanes at
  bits 8/16/24/32 (`CHANNELS_PER_PARAM=4`, bias 8), while type 1 and type 3
  write `customPerDrawData0.y/w`; type >=4 writes the reinterpreted packed word
  to `customPerDrawData0.x` before forwarding channel 2. Native offsets are
  controller field `m_characterEnvironmentEffectPackedValue +0x18` and
  renderer-info `customPerDrawData0 +0x48`, with quantizer `0x182f3ea70`.
  UnityPlayer now closes the native setter/getter storage ABI independently.
  Its internal-call registration pair maps
  `UnityEngine.Renderer::SetCustomPerDrawData_Injected` to native
  `0x1800fe590` (UnityPlayer SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`).
  That registration target is a lazy/error-handling stub whose successful path
  calls implementation body `0x180430680`. The body accepts only indices
  `0..4`, writes the Vector4 to
  `nativeRenderer + 0x140 + 0x10*index` (channel 2 therefore `+0x160`), then
  conditionally mirrors it to the returned per-draw resource at
  `+0xb0 + 0x10*index` (channel 2 `+0xd0`). `GetCustomPerDrawData_Injected`
  `GetCustomPerDrawData_Injected` implementation `0x18042db70` reads the same
  five-slot renderer formula, and `GetCustomPerDrawDataPtr` returns the
  `+0x140` base on its successful path. This proves the channel-2 native
  storage/resource layout rather than merely the managed forwarding path. An
  independent UnityPlayer refresh path at `0x18042f750` resolves the same
  resource and copies all five renderer vectors (`renderer +0x140..+0x180`) to
  its contiguous five-vector array (`resource +0xb0..+0xf0`); its callers at
  `0x18042c947` and `0x18042d692` cover renderer registration and create/rebuild
  paths. This closes the shared five-slot resource layout and reconfirms channel
  2 at `resource +0xd0`, but the resource-to-descriptor upload remains open. Do
  not treat the sidecar
  metadata label `_TerrainSubsurfaceConstants` as a recovered source name: it
  is inherited from the serialized parameter record, while raw Vulkan binding
  33/member 3 is the stable fact. Keep this channel-to-resource edge fail
  closed.
  An exhaustive direct-call census for UnityPlayer resolver `0x1804255f0`
  (26 call sites) found only the setter and refresh paths as confirmed writers
  of the custom five-slot array. The related renderer-list helpers
  `0x1810ccd20` and `0x1810d2fc4/0x1810d2fd9` copy generic 0x80-byte resource
  blocks between records but expose no custom-channel or descriptor identity.
  A follow-up sample of the remaining resolver callers separates more false
  positives: `0x18051304f/0x18051c938/0x18051d3e0` only update renderer-list
  metadata (`+0x4c/+0x50/+0x54`), `0x1810417fa` and its sibling constructors
  initialize fixed four-vector records, and
  `0x180bcb760/0x180bccb60/0x180bcd7ab/0x1810d00aa` prepare ordinary
  lighting/material records. None of the inspected bodies reads resource
  `+0xd0` or calls a descriptor/constant-buffer upload primitive. The explicit
  `MaterialPropertyBlock` routes (`0x1800be830 -> 0x1805d5280`,
  `0x1800befb0 -> 0x1805d5870`, `0x1800bf780 -> 0x1805d5850`) and global
  buffer routes (`0x18011ba30 -> 0x1804b5960`,
  `0x18011c7c0 -> 0x1804b59a0`) likewise have no call edge from
  `SetCustomPerDrawData_Injected`, its refresh path, or resolver
  `0x1804255f0`. This closes additional false-positive writers; the structured
  details are in `packed_flags_producer_recovery.json` under
  `secondary_callsite_followup`.
  A broader fixed-offset scan also found `0x1810d26bf` writing a generic
  destination record at `+0xb0..+0xf0`, including `+0xd0`. Its source is a
  separate `0x8c`-stride component array with flags at `+0x70`; the body only
  stages paired generic records and has no custom-per-draw setter/refresh,
  resource identity, or descriptor/constant-buffer edge. The equal
  displacement is therefore a negative audit result, not a newly recovered
  channel-2 binding.
  The same function RVA appears only as paired 32-bit function/metadata records
  (`0x10d26bf` / `0x204a398`) in the installed `.rdata` and matching `.tvm0`
  tables (`0x18204a3d8/0x18204a3e8` and `0x1824d1058/0x1824d1060`); no direct
  UnityPlayer `.text` call or RIP reference targets it or those records. This
  is consistent with table-driven Burst/job dispatch, but adds no
  custom-resource or GPU descriptor identity. The durable details are recorded
  in `packed_flags_producer_recovery.json` under `burst_table_followup`.
  No inspected UnityPlayer path reads `resource +0xd0` (or an equivalent vector
  lane) into a constant-buffer/descriptor binding, and no direct call edge names
  Vulkan set 0/binding 33. Keep the channel-to-resource-to-GPU edge open.
  The installed UnityPlayer GPU-driven internal-call table is now mapped as a
  separate negative audit. V1 frame/buffer entrypoints are
  `0x1801e9200/0x1801e9280/0x1801e9360/0x1801e93a0/0x1801e9480`, and V2 uses
  `0x1801e98f0/0x1801e9970/0x1801e9a50/0x1801e9a90/0x1801e9b70`. The most
  tempting V2 candidate, `0x1810fb5a0`, enumerates
  `[gpuDrivenState +0xa0..+0xd0]` where `gpuDrivenState = [this+0x68]`, then
  passes each lane to generic indexed binder `0x1805f84a0`; that helper checks
  command-context capacity at its own `+0xd0`. No edge aliases this array to
  the `0x1804255f0` custom-per-draw resource, so it is GPU-driven buffer/property
  binding rather than the missing channel-2 descriptor consumer. The durable
  entrypoint/candidate audit is recorded in
  `Generated/OriginalData/CharInfoPresentation/packed_flags_producer_recovery.json`;
  the resource-to-descriptor edge remains fail-closed.
  The current installed `HGRenderPipelineRuntimeResources.shaders`
  serialization now closes the positive object edge for the GPU carrier:
  `gpuSceneDirtyUpdateCS` (field index `173512`, token `0x040017f7`) resolves to
  ComputeShader PathID `9129651272751059356`, explicitly named
  `GpuSceneDirtyUpdateCS`, from the current Persistent chunk
  `36243F039A1BFD05676B5D323B50D4AA.chk` at offset `4105822`. Its only
  renderer-21/level-0 variant contains eight kernels; `UploadPerDrawParams` is
  kernel index 7. That kernel reads `_UploadBuffer` records with an 84-byte
  stride (a leading index plus five 16-byte lanes) and writes the five lanes to
  `_DstPerDrawParamsBuffer` with an 80-byte stride, using
  `GpuSceneUploadConstants._UploadBufferOffset` and `_EntryCount` and a
  `[64,1,1]` dispatch. The raw ComputeShader hash remains
  `0202830400d56f224dd45c43f2ff1cdfe848272509ae8663cccfa1abd0351f36`, so the
  earlier byte-level contract is current rather than a stale object path.
  This closes the serialized resource-to-object-to-kernel identity, but not the
  native dispatch selection: the native bridge still does not prove that a
  particular call supplies this object and kernel 7, and the shader has no
  renderer/resource identity, custom channel index, resource `+0xd0`, or
  binding-33 label. No native edge from `SetCustomPerDrawData_Injected` or
  `0x18042f750` to the upload-buffer producer has been recovered. Details are
  recorded under `gpu_scene_upload_kernel_evidence` in the packed-flag audit;
  keep channel 2 to GPU descriptor binding fail-closed.
  The managed/native initialization chain for that GPU carrier is now also
  closed. Installed metadata identifies the public static
  `HGShadingStateSystem.SetupGpuSceneUploadCs(ComputeShader)` method (index
  477986); its IL2CPP wrapper is `GameAssembly!0x1839454d0`, and the
  `HGRenderPipeline` constructor (native `0x183947230`, callsite
  `0x183948786`) loads a ComputeShader from the object chain
  `[returned+0x18]+0x638` before calling it. UnityPlayer internal-call
  implementation `0x1801ee4c0` uses four calls to the IL2CPP GC write-barrier
  slot `0x1821be708` (resolved at `0x18077c055` from the literal
  `il2cpp_gc_wbarrier_set_field`) to maintain managed pointer locals, then
  consults the RuntimeInitializeOnLoadManager pointer table and conditionally
  reads the wrapper's native handle at `+0x10`. `HGRayTracingScene.SetupGpuSceneUploadCs`
  shares that native implementation. These calls are not CFG dispatch calls and
  do not identify a ComputeShader kernel or upload producer. The native
  compute-dispatch bridge is independently closed for
  GPUDriven V1/V2: their four dispatch wrappers reach cores
  `0x1810f1890/0x1810f17e0` and `0x1810fe040/0x1810fdf90`; each uses
  `0x1805e7e10` for immediate context/vtable dispatch or `0x1804c74d0` to
  record CommandBuffer opcode `0x11`. This proves the Unity dispatch
  mechanism. The only non-wrapper native callers (`0x181280530` for the
  meshlet pair and `0x18127c730` for the bucket pair) explicitly pass `r9d=0`,
  so those internal GPUDriven paths select kernel index 0, not the identified
  `GpuSceneDirtyUpdateCS` kernel `UploadPerDrawParams` (index 7). The managed
  wrappers still accept a caller-supplied kernel index; therefore this is
  negative evidence for the known internal paths, not a proof that no managed
  caller can select index 7. Dispatch selection and the upload-buffer producer
  remain unresolved, and no edge from custom-per-draw channel 2/resource `+0xd0`
  has been recovered. Structured hashes, addresses, caller census, resource
  field identity, and the fail-closed boundary are recorded under
  `gpu_scene_setup_wiring`, `gpu_scene_upload_kernel_evidence`, and
  `gpu_dispatch_bridge_evidence` in the packed-flag audit.
  The current UnityPlayer binding path is now bounded as a separate edge:
  V1 `BindBuffersForCulling` (`0x1810eece0`) and V2
  `BindBuffersForCulling` (`0x1810fb5a0`) preserve the managed caller's
  `kernelIdx` from `r9d`, then pass it as `edx` to the per-kernel binding-record
  helper `0x1805f84a0` (immediate path) or record command opcode `0xd` through
  `0x1804cb1a0`. The corresponding GameAssembly internal-call wrappers preserve
  `r8d` unchanged; no wrapper-side kernel constant is present. V1/V2 native
  GPUDriven callers `0x18127c730` and `0x181280530` pass zero for this index,
  so their known culling/binding routes still select kernel 0. The global
  Shader.PropertyToID registry initializes `_RTPerDrawParamsBuffer` at field
  `+0x130c` of the table rooted at `0x1821ed7b0`; the binding cores consume
  per-shader property IDs and fixed payload offsets, but no static edge ties
  that property to the character resource `+0xd0` or to `UploadPerDrawParams`
  kernel 7. This closes the kernel-index/binding-record ABI while keeping the
  channel-2 resource-to-descriptor and upload-dispatch edges fail-closed;
  details are recorded under `gpu_driven_binding_path_evidence`. The helper's
  valid-index path is now explicit: `0x1805f84a0` gates
  `kernelIdx < [bindingState+0xd0]`, takes the selected metadata slot's first
  dword as a binding-record key, and updates
  `[bindingState+0xc0]+0x818+kernelIdx*0x880` through `0x1805f8630`; this is
  cache/command metadata, not yet a named `SetBuffer` edge. A complete current
  UnityPlayer E8 census finds exactly one native caller for each V1/V2 dispatch
  core (`0x18127c7b4`, `0x181280849`, `0x18127c814`, `0x1812808ac`) plus the
  managed wrappers, and all four native callers zero `r9d`. Thus no additional
  direct dispatch producer selects kernel 7 in the installed binary, while a
  managed caller could still do so dynamically.
  The RenderGraph GPUDriven culling producer is now mapped at the managed
  callback `GPUDrivenCullingPassConstructor+<>c.<.cctor>b__10_0`,
  `GameAssembly 0x189bb558c` (metadata method `287367`). Its V1 and V2
  branches each run `Valid`, `PopulatePerFrameData` (thread-group size `0x40`),
  then `BindFrameConstantsBuffer`, `BindBuffersForCulling`, and one of the
  bucket/meshlet dispatch wrappers twice for shader values at callback-data
  offsets `+0x10` and `+0x18`. The callback explicitly clears the wrapper
  `kernelIdx` argument (`r8d=0`) for every bind/dispatch call; the wrappers
  preserve it as native `r9d`, so this live culling route selects kernel 0 in
  both renderer versions. This is the first closed managed RenderGraph
  producer for the known GPUDriven dispatch cores, and is negative evidence
  against `GpuSceneDirtyUpdateCS.UploadPerDrawParams` kernel 7 on this route;
  it still does not connect channel 2/resource `+0xd0` to `_UploadBuffer` or
  binding 33. Details are recorded under
  `gpu_driven_culling_pass_callback` in the packed-flag audit.
  `HGConstantBufferPool.ApplyPendingUpload` is a separate generic upload
  candidate: `GameAssembly 0x189b6a7c0` updates `this+0x10` through
  `ComputeBuffer.SetData` (`0x187af05e0`), but its visible body has no
  ComputeShader dispatch, `SetBuffer`, named `GpuSceneDirtyUpdateCS`, or edge
  from the factory shared-payload producer. It therefore remains an unresolved
  generic buffer path, not evidence for `_UploadBuffer` or channel 2/resource
  `+0xd0`; details are under `constant_buffer_pool_cross_check`.
  Generic-instantiation mapping now recovers the strongest CPU-side factory
  producer that the ordinary method table hid: concrete
  `HGFactoryRendererBinderComponent.SetCustomPerDrawData<Vector4>` at
  `GameAssembly 0x1834a3d60` (`MethodSpec 515702`). Its body guards
  `offset + 16 <= 0x50`, copies one Vector4, takes `sharedDataIndex` from
  `this+0x8`, and calls the same lazy `0x18f370720` slot as
  `HGFactoryRenderManager.SetEntitySharedDataPartial` (`0x183d689c0`) with
  `(index, data, offset, 16)`, then marks `HGFactoryDirtyFlags.PerDrawData`
  (`1`). The 80-byte guarded payload matches the five-lane width consumed by
  `UploadPerDrawParams`, so the generic binder/shared-payload producer boundary
  is now closed. The native partial-update body is still dynamic: no installed
  file edge yet proves this payload reaches `_UploadBuffer`, kernel 7, or
  channel 2/resource `+0xd0`; keep the GPU edge fail-closed. Details are in
  `packed_flags_producer_recovery.json` under
  `factory_per_draw_shared_payload_evidence`.
  The factory producer is broader than the Vector4 path alone. Static
  GameAssembly bodies show `SetPosition` (`0x1834a3ce0`, offset `0x50`, 12
  bytes), `SetRotation` (`0x183e21230`, offset `0x60`, 16 bytes), and the
  float `SetCustomPerDrawData` instantiation (`0x1840f30e0`, 4 bytes) using
  the same 80-byte shared record and dirty-state mechanism; the Vector4
  writer remains `0x1834a3d60` with the caller-supplied offset plus 16-byte
  guard. This closes a coherent CPU-side writer family, while all paths still
  terminate at the dynamically dispatched factory service rather than a
  statically named `_UploadBuffer`, shader bind, or compute dispatch.
  A direct GameAssembly bridge now closes the caller-side entry into that
  factory path. The generated/native range `0x180471cd8..0x180471d27` calls
  `ApplyPerDrawRender` at `0x1869d8488` (`rsi`/`rdi`/`ebx` preserve
  `binderPtr`/`perDrawConfigs`/`length`, while `r9d` is cleared). The Burst
  path reaches `PerDrawGlobalSetting.Apply` at `0x1869d5d30`, loops the
  configs, and calls `PerDrawConfig.Apply` at `0x1869f3654`, which ends at
  the concrete `SetCustomPerDrawData<Vector4>` writer `0x1834a3d60`. The
  bridge range has no ordinary IL2CPP method-pointer owner, so its managed
  name remains intentionally unresolved. This closes native entry through
  binder Vector4 production, not the GPU edge: `_UploadBuffer`, kernel 7,
  and channel-2/resource `+0xd0` consumption remain fail-closed. The durable
  details are under `apply_per_draw_render_bridge` in the packed-flag audit.
  The UnityPlayer registration target for that partial update is now bounded,
  rather than treated as a false static upload edge: internal-call table entry
  206 maps `SetEntitySharedDataPartial` to `0x180155300`, whose PData-split body
  unwraps the managed wrapper, calls the factory service's virtual slot `+0xb0`, walks generic
  records, and never visibly preserves the incoming `data`/`offset`/`size`
  registers or calls a buffer/property/command API. The paired full-set target
  `0x180153ee0` has the same dynamic service shape and ends at virtual slot
  `+0xc0`. This confirms the native boundary is real but dynamically
  implemented; it does not prove shared payload → `_UploadBuffer` or GPU
  dispatch. The bounded registration/body evidence is recorded under
  `native_partial_endpoint_evidence`; keep the upload edge fail-closed.
  The dynamic service side is now bounded one step further: UnityPlayer helper
  `0x180776410` calls registry accessor `0x18030f100`, whose table is at
  `0x182168800`; the partial endpoint requests slot `5`. Constructor
  `0x18076ff30..0x180770173` registers its approximately `0x368`-byte service
  object into that slot at `0x18077011a` and initializes the record-container
  field `+0x1c8`. The partial body reads `[slot5+0x1c8]`, selects a record using
  the global index at `0x180155417`, and walks the wrapper `+0xb0` result through
  `0x180769da0`/`0x180760900`. This is concrete factory-service/record evidence,
  not GPU identity: the incoming `data`, `offset`, and `size` registers still do
  not reach a visible copy, buffer API, command recording, or dispatch, so the
  shared-payload-to-`_UploadBuffer` edge remains fail-closed.
  The managed `HGFactoryRenderManager.FrameUpdateEntities` entry is an
  additional bounded negative: metadata method `477917` resolves through the
  current code-registration pair to `GameAssembly 0x1841e1670`, whose body is
  exactly one byte (`ret`). A static census finds five callers, but this
  installed build contains no frame-update instructions at that entry, so it
  cannot be credited as the shared-payload to `_UploadBuffer` or GPU-dispatch
  producer. This does not rule out a dynamically initialized factory service,
  IFix-patched code, or unrelated GPU-driven ECS work; the channel-2 upload edge
  remains fail-closed. Details are recorded under
  `managed_frame_update_evidence` in the packed-flag audit.
  A follow-up call-graph audit covered all 21 resolver call sites that had
  recorded memory accesses, plus their direct and one-level child calls. The
  renderer registration/rebuild path (`0x18042c910..0x18042cb01`) reaches
  virtual lifecycle slots `+0x128`/`+0x130`, refreshes the resolved resource,
  invokes `+0x120`/`+0xf0`, and prepares the ordinary renderer record through
  `0x18042a130`; teardown (`0x18042f3d0..0x18042f4ed`) uses `+0x128`/`+0x80`
  /`+0xe8`/`+0xf8` and clears the component record. None of these visible
  bodies reads `resource +0xd0`, calls an explicit buffer/property API, or
  reaches the mapped GPU-driven entrypoints. The virtual implementations are
  still a dynamic boundary, so this is a bounded negative audit rather than
  proof that the upload does not exist; keep the channel-2 resource-to-GPU
  edge fail-closed. Structured details are in
  `packed_flags_producer_recovery.json` under `indirect_lifecycle_followup`.
  The renderer constructor (`0x18042bf10..0x18042c0b8`) now resolves the
  visible virtual boundary: it writes main vtable `0x181d664e8` and embedded
  vtable `0x181d66658` at `+0`/`+0x38`. Main `+0x80` is the generic
  property/material metadata route (`0x180433300` -> `0x1804262a0`),
  `+0xe8`/`+0xf0`/`+0xf8` are generic flag/manager paths,
  `+0x120` is generic index output, `+0x128` is an always-false stub, and
  `+0x130` checks embedded record count. Embedded `+0x30`/`+0x38` access
  ordinary record state, while `+0x80`/`+0x88` read component18 validity/key
  at main `+0x268`/`+0x26c`. A PData-scoped Capstone scan of these roots and
  direct callees found zero literal `resource +0xd0` reads, zero direct calls
  to mapped GPU-driven entrypoints, and no explicit buffer/property API. This
  closes the visible vtable indirection but remains a bounded negative result;
  an indirect or table-dispatched upload consumer is still open. Details are
  in `packed_flags_producer_recovery.json` under `concrete_vtable_followup`.
  An exact inlined component18 lookup scan found only three sites: the
  canonical resolver (`0x1804256db`), a generic allocation/copy path
  (`0x180ba0d40`), and a generic component-initialization writer
  (`0x1811497c1`). The last reads its separate source record at
  `+0xd0/+0xe0/+0xf0/+0x100` and writes four vectors to the resolved
  component; it does not read the custom resource or call a descriptor/
  constant-buffer upload primitive. This closes another equal-displacement
  false positive while leaving the channel-2 resource-to-GPU edge open. The
  structured result is recorded under `inlined_lookup_followup`.
  The refresh body also has a separate five-slot override path: after the
  `+0x140..+0x180` to `+0xb0..+0xf0` copy, `0x18042f750` interns five fixed
  keys through `0x180627040`, binary-searches the optional manager table at
  `+0xc0` with `0x18042ba20`, and writes any found `Vector4` to the matching
  renderer/resource slot. This is still a named per-draw override writer,
  not a read of resource `+0xd0` or a descriptor/constant-buffer upload.
  The apparent `0x180fc5e60` service lookup on these paths is now identified
  as registry index 20 (`RuntimeInitializeOnLoadManager`) through
  `0x18030f100`, so its `+0x38`/`+0xf0` fields are not custom-resource lanes.
  Both boundaries are recorded under `override_refresh_followup` and
  `runtime_initialize_service_identity` in the packed-flag audit.
  The upstream `HG.Rendering.Runtime.HGCharacterVolume.GetPackedEnvironmentEffectIntensity`
  body is also recovered at native `0x183523ad0`: it quantizes two
  environment getter results (from `this+0x180` and `this+0x178`) together with
  fixed `255` and `0` lanes, then returns the reinterpreted four-byte word.
  This is a source-backed packed-word producer, but no direct call edge to the
  character renderer upload was recovered, so it remains upstream evidence.
  A separate global-CB production path is now source-closed: installed
  `HGRenderPathScene.UpdateShaderVariablesGlobal` calls
  `UpdateShaderVariablesGlobalCharacter`, whose native body calls
  `HGCharacterVolume.GetPackedEnvironmentEffectIntensity` and writes its
  result to `cb + 0x754`, exactly `ShaderVariablesGlobal` c117.y. The
  `ShaderVariablesGlobal` metadata names `_CharacterParams10`, and the
  CharacterNPR source consumes c117.y as the global packed-word override when
  c117.x is enabled (otherwise it uses UnityPerDraw Param2.x). This proves a
  second real producer/carrier, but it is not the HGRP/Lit HGBuffer `b3[0].w`
  binding; keep that register/component boundary fail-closed in the audit.
  A cross-variant CharacterNPR forward source closes the ordinary UnityPerDraw
  carrier independently: `UnityPerDrawArray` `Param2` is at byte offset `+208`
  (`_m7`), with `_m7.x` carrying the packed environment word and `_m7.y` the
  wet world-space height. That narrows the standard channel-2 layout, but does
  not establish the HGRP/Lit HGBuffer `register(b3)` `cb3[0].w` component remap.
  The durable audit records both additions in
  `Generated/OriginalData/CharInfoPresentation/packed_flags_producer_recovery.json`.
  The native history/deformation census is narrowed as well: `GpuClothManager._SetPerDrawData`
  (`0x189c6cbec`) walks ECS cloth data and enters a dynamic IFix wrapper without a
  statically resolved custom-per-draw call; `_SetCharacterProxyMesh`
  (`0x1847a53c0`) only updates proxy bounds/cloth constants; and
  `SkinnedMeshCaptureManager.SetCaptureDataForPropertyBlock`
  (`0x183d438b0`) allocates/copies/binds `BAKE_SKIN_MATRICES_CB` through a
  property block. These routes do not identify the missing HGRP packed scalar or
  previous-deformed-position upload. The IFix cloth wrapper and renderer-side
  history state remain open and are recorded as such in the same audit.
  Do not substitute `_ShadingModel`, UnityPerDraw, channel 2, or zero/default
  values; the sidecar remains neutral and fail-closed until that binding or an
  authorized target-frame upload is recovered.
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
  The generated `gacha_light_survivor_transport.json` and default-off
  `EndfieldRecoveredGachaLightSurvivorTransport` now carry the selected
  3840x2160 authored identity/order (six `light_overview` plus eleven room
  rows) into a reusable runtime diagnostic boundary. The transport is gated to
  the canonical perspective 16:9 sample, publishes no shader buffer, and
  explicitly keeps the retail `LightCullResult` pointer/count/rows capture-only.
  `build_gacha_light_cull_capture_contract.py` now consumes an authorized,
  binary-pinned capture, reproduces SetupState priority/distance ordering, and
  bit-matches captured room rows against the eleven authored candidates. It
  rejects unsupported types, sort ties, ambiguous/duplicate identities, and
  incomplete selected-room captures. It now also accepts an optional detached
  raw b31 payload only when all capture-row indices, 8-record/128-byte rows,
  whole GameAssembly hash, and `PrepareCPUData` body hash validate; the payload
  is retained for later consumption but `b31Ready` remains false until runtime
  carry-in and retail publication are captured.
  The deferred native audit now also closes `PrepareCPUData` record5.w as
  `uint(enableOBBCullingBox) | (uint(enableOverrideShadowLight) << 1)`;
  the selected authored room rows therefore use integer 1 (`0x3F800000` as
  float bits), while target-frame row values and live shadow-cache indices
  remain capture-only.
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
  component-75 HLOD-level byte. The native Render transition-1 body now
  source-closes that byte at component-75 `+0x00` and indexes the squared
  unload-distance table as `state+0x474+4*byte0`; the type name itself remains
  intentionally unresolved. Both callbacks acquire the exact
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
  retail TAA frames remain open. The chronology verifier also pins the
  installed transparent queue selector: low-resolution, pre-refraction,
  refraction, and all-transparent branches feed the exact queue range, while
  `CreateTransparentRendererListDesc` preserves world-UI layer removal,
  culling ratios/mask, renderer configuration, queue range, sorting criteria
  87, state/material/feedback/motion-vector fields, and IFix targets 2589/1047.
  This is still source/static evidence; same-queue tie ordering and live IFix
  replacement remain open.
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
  record1.w for all 11 rows. The native record7 producer is now source-closed
  on both Spot and Point/linear branches: culling-box falloff threshold,
  soft-source radius, specular intensity, and the precomputed cookie-slot
  integer carrier project to lanes x/y/z/w before the common record7 store.
  Hash-pinned half-angle scaling and the original
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

# Character rendering and animation recovery

## Current status

The Unity lab is a source-backed reconstruction of Endfield character models
and Character Info presentation. It is useful for asset and shader research but
is not the retail renderer.

| Layer | Current status |
| --- | --- |
| Playable models | 31/31 imported and rendered |
| Canonical post-model identities | 156/156 have generated prefab paths |
| Static playable Overview assets | strong |
| Selected CharacterNPR equations | partial but source-backed |
| Complete HGRP/CharInfo frame | partial |
| Playable UI clips | complete for the selected `all-ui` scope |
| Runtime animation behavior | partial |
| Retail visual parity | not reached |

The canonical identities are 31 playables, one NPC character, one cutscene
clone, 94 enemies, and 29 ability/prop actors. Six modular ambient-NPC
archetypes are imported as labeled source kits rather than finished characters.

## What is recovered

- Playable post-models, LOD0 mesh bindings, materials, textures, cameras,
  profiles, lights, portraits, and Overview animation sources.
- Dependency-safe static prefab baselines for every canonical non-playable
  post-model identity.
- Current Persistent patch-layer roster/controller data alongside base
  StreamingAssets models. Liino validates that cross-layer boundary.
- Playable UI body and private item/deco clips for the selected scope.
- The Endfield 101-muscle Avatar contract and selected exact clip/Avatar paths.
- Narrow verified behaviors for blink, facial, and physical-transform fixtures.
- Selected CharacterNPR, eye, hair, shadow, material, particle, gacha, depth,
  GBuffer, light, cookie, and irradiance diagnostics.
- Fail-closed native texture payload recovery for the admitted playable set.

Generated mesh identity is source-scoped. Chen and Chenpast remain separate
model families with distinct containers, Animator identities, VFS sources, and
generated mesh GUID sets. Shared facial or animation bases do not merge their
mesh ownership.

The native `HGRenderPath` slot roles are now corrected from the installed
UnityPlayer registration: wrapper `+0x8` is the BeforeCulling setup
(`0x1812fdb20` → `0x1813022d0`), `+0x10` is the Render forwarding wrapper
(`0x1812fdd80` → `0x1813018c0` → `0x1813042d0`), and `+0x18` is Destroy
(`0x1812fddc0` → `0x181300ab0`). The bounded BeforeCulling/Render bodies still
show no factory staging, CommandBuffer/Compute upload, or kernel-7 edge; the
factory-record-to-`_UploadBuffer` link remains fail-closed.

The follow-up RenderGraph census separates the shared graphics-context
dispatch slot `+0xab8` (used by the immediate ComputeShader helper family)
from the HGRenderPath graph-record lifecycle slots `+0xcd0`, `+0xea0`, and
`+0xeb0`. The checked Render, helper, and graph-state bodies contain no
`+0xab8` call and no direct factory staging or GPUDriven dispatch target, so
the factory-record-to-`UploadPerDrawParams` kernel-7 edge remains unproven.
The complete UnityPlayer `+0xab8` census has ten sites: fixed kernel `1`
resource passes, dynamic generic helpers, and one command-stream interpreter;
none statically identifies kernel `7` or binds factory channel-2 `+0xd0`, so
the dynamic command/resource record remains the only open bridge.
The current GameAssembly PData-scoped dispatch census finds 110 direct
`CommandBuffer.Internal_DispatchCompute` calls from 37 named built-in render
passes, with no `factory`, `perdraw`, `upload`, or character producer; the only
direct `ComputeShader.Dispatch` caller is unrelated MagicaCloth physics code.
This closes the direct managed dispatch candidates, while leaving the native
command-stream record feeding the generic interpreter open and fail-closed.
The native Unity CommandBuffer layer is now separated from that low-level
interpreter: the recovered internal-call table maps
`CommandBuffer.Internal_DispatchCompute` to `0x180119fc0`, which calls
`0x1804c73e0` to record opcode `0x11`; buffer binding maps to
`0x180116180` and `0x1804cb1a0`, which records opcode `0x0d`. A separate
GameAssembly census found 47 direct compute-buffer binding calls from eight
named bodies and 35 texture-binding calls; they are built-in passes or
CommandBuffer overload wrappers, with no factory/per-draw/character hits.
The consumer is now bounded: `ExecuteCommandBuffer_Internal_Injected`
(`0x1800b6f40`) reaches `0x18052d730` -> `0x1804cdf70` -> the high-level
opcode interpreter `0x1804ce0a0`. Opcode `0x11` (`0x1804cf455`) resolves its
resource handle and calls `0x1805e7a10`, which reaches graphics-context slot
`+0xab8` at `0x1805e7a8b`; its indirect-dispatch branch calls
`0x1805e7bc0` -> slot `+0xab0`. Opcode `0x0d` (`0x1804cf350`) resolves the
same record kind and calls `0x1805f84a0` for resource-state binding, with no
direct `+0xab8` or low-level `0x27ef` call. Thus high-level records do reach
the generic immediate-compute sink, but remain a separate stream from the
native `0x27ef` record, and neither path identifies the factory channel-2 /
kernel-7 upload producer.
An expanded UnityPlayer direct-call census covers the two high-level writers:
`0x1804cb1a0` (opcode `0x0d`) has 58 direct callsites in 20 PData bodies and
`0x1804c73e0` (opcode `0x11`) has 42 callsites in 18 bodies, 27 unique bodies
in the union. The bounded caller set has no direct call to the factory
`0x8c`/`0x100` staging functions, the custom-resource resolver
`0x1804255f0`, or the immediate dispatch helpers; the only known
factory-adjacent bodies are the already-separated generic GPUDriven V1/V2
binders (`0x1810eece0`, `0x1810fb5a0`). This closes the direct native writer
surface as a factory producer while leaving virtual/table-dispatched callers
and the channel-2 resource upload edge fail-closed.
The native command-stream pair is now bounded for one dispatch opcode: writer
`0x18092bed0..0x18092c123` stores opcode `0x27ef`, a resource/handle qword, and
three 32-bit dispatch values (`0x18092bf54`, `0x18092bfb6`, `0x18092c00a`,
`0x18092c05d`, `0x18092c0aa`). Interpreter case `0x27ef` begins at
`0x1813b805b`, consumes the same four-field shape, and reaches graphics
context slot `+0xab8` at `0x1813b819f`; the writer also has an immediate
fallback at `0x18092c10e`. This closes the generic native command-record
boundary, but the record is not tied to factory channel-2/resource `+0xd0` or
`UploadPerDrawParams` kernel 7, so the character upload edge remains
fail-closed.
The current protected `Gameplay.Beyond` IFix payload is now structurally
bounded beyond its 32 target signatures: its 330-entry external-method table
contains only factory LOD/quality references (`SetFactoryLodTier` and
`FacQuality.Apply`) plus unrelated dynamic-scene buffer helpers, with no
`ComputeShader`, `ComputeBuffer`, `CommandBuffer`, `GPUDriven`, per-draw,
`UploadPerDrawParams`, or dispatch API. The `0x7301`
`RemoteFactoryGameWorldController.FrameUpdateEntitiesJobForward` target is
also absent from this on-disk table. This strengthens the static negative but
does not expose runtime wrapper-array slots or another loaded patch payload;
the IFix route and factory-record-to-`_UploadBuffer` edge stay fail-closed.

The installed `HGRenderPathDefaultDeferred` route is now pinned at the GBuffer
attachment boundary. `GBufferPassConstructor.ConstructPass` submits
`SceneColor`, neutral-cleared `SceneMV`, `GBufferA/B/C`, and writable
`SceneDepth` in that order; the renderer-list uses LightMode `GBuffer` in the
opaque `CommonOpaque` queue, while render-graph load/store remains automatic.
`OnePassDeferred` independently preserves the same MRT order and adds
`PreDepth`/`GBuffer`/`Decal` subpasses. This closes the source-side five-MRT
contract needed by `HGRP/Lit` but not the physical `SceneColor` allocation or
the channel-2 resource-to-descriptor upload. Durable details and hashes are in
`reports/assets/character_recovery/gacha_room_gbuffer_rendergraph.md`.

The upstream SceneColor contract is now source-pinned as well. The selected
`HGRenderPathDefaultDeferred` route creates SceneColor in
`HGRenderPathScene.OnPreRendering` with format
`B10G11R11_UFloatPack32`, Point/Clamp sampling, the selected Gacha clear
`(0.025, 0.07, 0.19, 0)`, and 1x MSAA/`bindTextureMS=false`. The transient
logical handle is physically created/released at compiled first-write/last-use
boundaries through the descriptor-hash `RTHandle` pool; stale entries require
an 11-frame gap before purge. The initial handle is at `+0x12e0` and the
preserved history lane at `+0x1328`. Scene dimensions are target-relative and
evenized using the live persistent-camera viewport and
`video_rendering_scale_pc`, so exact pixels, active scale, native pointer, and
alias peer remain open. The deterministic checkers currently cannot rerun
because the expected exported `HGRenderPipelineAsset` JSON is absent; retain
the hash-pinned snapshot and boundary in
`reports/assets/character_recovery/gacha_scene_color_physical_lifetime.md`.

The shared SceneMV/motion boundary is now source-closed for the isolated
selected-character CharInfo/VFX scene. `HGRenderPathScene.OnPreRendering`
creates a transient full-resolution `A2B10G10R10_UNormPack32` SceneMV target at
`+0x1300` only when `HGCamera.enableMV` is true, clears it to
`(0.5,0.5,0,0)`, and uses it as GBuffer/ForwardOpaque attachment 1; it is
current-frame data, not a history texture. The native total order is now
verified as GBuffer → ForwardOpaque character target-1 writers → main
ForwardOnly → Distortion → Phase 1 (LightShaft/Parafin/DOF/MotionBlur) →
after-DOF ForwardOnly → LensFlare → optional pre-TAAU blur → Phase 2. Sixteen
Wulfa/Zhuang Fangyi skin, cloth, hair, and eye variants write packed motion to
`SV_Target1`; selected VFX must consume that populated attachment. Camera
previous constants and paired skin-matrix ranges are also source-pinned, while
terrain/foliage target-1 enumeration, physical skin-buffer reuse, and a
source-compatible lab MRT remain open. See
`reports/assets/character_recovery/gacha_scene_mv_motion_contract.md`.

The ordinary DefaultDeferred resolver boundary is now source-pinned. The
selected route is a five-MRT producer (`SceneColor`, `SceneMV`, `GBufferA/B/C`)
followed by a separate one-RT SceneColor resolver with read-only depth and
GBuffer A/B/C as ordinary `Texture2D` SRVs; the matched Vulkan payload has no
subpass image reads. Installed state enables screen-space shadow masking and
disables the OnePass subpass bit. UnityPlayer's native best-match loop then
selects the unique serialized pass-0 pair 96/97 (screen-shadow plus subpass)
for the missing ordinary variant. Its nine-CB/25-SRV/structured-buffer ABI
and static fallback values are mapped, while live light/bin, shadow/cookie,
VisibilitySH, irradiance, AO/SSR, camera, and remaining frame contents remain
open. The current standalone diagnostic is finite and binding-compatible only;
the maintained isolated-diagnostic validator now accepts its direct-runtime
`0/0/0` callback/swap mode after the current plugin hash and GBuffer-order token
were refreshed. This does not establish retail numeric fidelity or justify
enabling a lab draw.
See `reports/assets/character_recovery/gacha_deferred_resolver_framebuffer_contract.md`.

The Gacha final-color chain is now source-pinned through post processing.
`Env_gachaRoom_01` owns Manual exposure on the persistent physical main Camera,
while CinemachineExternalCamera supplies only virtual transform/lens state.
Native Phase 1 is DepthOfField → MotionBlur → conditional AfterDOF; Phase 2 is
ColorGrading/LUT → Bloom → AutoExposure → Uber. Gacha Bloom is high quality
with threshold `0.95`, effective intensity `0.41421356`, effective scatter
`0.41`; Vignette and chromatic aberration are explicitly inactive. Exposure
recurs as `E[n+1] = Lerp(E[n], 1, clamp(0.6*Time.deltaTime[n],0,1))`, and
`_ExposureWithMiscParams` publishes current exposure, reciprocal exposure,
target aspect, and the recovered reciprocal camera field. The camera-local
Gacha Bloom selector and exposure ownership probe are validated, but physical
camera carry-in, exact deltas, AfterDOF state, lower volume ownership, and
final pixels remain runtime history. Do not force a fresh exposure reset or
selected-frame multiplier. See
`reports/assets/character_recovery/gacha_postprocess_exposure_contract.md`.

The deferred environment-global publisher boundary is now also pinned. The
Gacha path has two exact closures: `_MultiscatteringLUT` is a fixed 32x32
`RHalf` payload (raw SHA `1A15AFE2…289F030E`) published by
`PreparePCMultiscattering`, and disabled ASM binds the default shadow texture.
V2 irradiance, volumetric scattering, cloud shadow, CSM, and punctual shadow
producer/fallback ownership and shader slots are mapped, but their live branch,
camera settings, atlas/voxel contents, and frame parameters remain open.
`RenderForwardTransparent` does not publish these globals, so M02 stays
fail-closed. See
`reports/assets/character_recovery/gacha_environment_global_publishers_contract.md`.

The Gacha light cull-view boundary is now source-pinned independently of that
missing pipeline-asset export. The installed fallback has
`useFallbackLightCulling=false`, zero occlusion dimensions, and the normal
native candidate core. Active `SceneLight6Rarity` rows initialize
`mask=1<<layer` and `flags=0x701`; Gacha layer 30 intersects the camera mask
`0x40010008`, so the generic flag/mask gate is closed for all twelve authored
rows. The native point-sphere top-plane branch guarantees `Spot Light (20)` is
absent (margin `81.4967041015625`), leaving an exact conditional order for the
other eleven and an authored maximum of 11. Horizontal AABB planes, unrelated
live lights, the 256-row input cap, and the runtime punctual-light cap still
own the exact selected list. The regenerated checker passes with current
binary hashes; details are in
`reports/assets/character_recovery/gacha_light_cull_survivor_contract.md`.

The selected-light result's downstream HGRP publication chain is now also
source-pinned. `UpdateLightCookieAtlas` precedes
`LightCulling.PrepareCPUData`, which embeds cookie indices; then
`LightCulling.SetupGlobalConstants` publishes the 32,864-byte
`_LightDataBuffer` and 48-byte `_LightBinningConstants`.
`LightCullingGPU.PrepareGPUData` and reflection clustering share one graph
binning buffer, and the Binning pass publishes it as `_GlobalBinningBuffer`.
M02 transparency only consumes these globals and does not rebuild them. The
desktop cookie atlas is persistent 4096x4096, while cookie slots/CB and light
constant buffers are rebuilt per frame. Exact selected rows, surviving cookie
membership, shadow/CSM, ASM, irradiance, reflection contents, and original
clustering kernels remain open; details and binding slots are in
`reports/assets/character_recovery/gacha_light_global_publication_contract.md`.

The HDPLS character-shadow resource route is now source-pinned. The current
Persistent IFix table has 32 records and matches neither HDPLS wrapper gate
`0x877` nor screen-resolve gate `0x890`, so the unpatched native route is the
current static path. Its reflected 3,568-byte layout is requested/bound as
`0xDE0` bytes; the selected consumer reads `uint4[56].y` at bytes 2560..3455.
Active requests create a transient D16 `4096x2048` (request-grid-scaled)
`_HDPLSTex` atlas, then a single-sample RGBA8 resolve publishes
`_HDPLSScreenSpaceShadowMask`; inactive frames reset selectors and bind white
textures. Atlas geometry, selector formulas, and publication/lifetime are
closed, but live character/light rows, atlas pixels, and resolved mask pixels
remain capture-only. See
`reports/assets/character_recovery/hdpls_character_shadow_resource_contract.md`.

V2 irradiance ownership is now source-pinned for the updated AnimeStudio
exporter and unchanged installed game binaries. The Gacha Lua
`Data/IrradianceVolume/PC/gacha/character` files feed the older
`HGIrradianceVolumeManager.CreateGachaIV` path; they do not own M02's six V2
clipmap globals. `HGIrradianceVolumeManagerV2.PipelineUpdateV2` renders the
underlying scene's `m_defaultIV`, while `m_gachaIV` only gates update-center.
The current Gacha room is a prefab overlay with no Scene object and no
room-owned V2 IV payload: the installed VFS has 224 IV files across 60 chunks,
83 current scene indexes, 12 legacy Gacha files, and zero room files. The six
V2 clipmap slots, texture formats/dimensions, shader-global order, and missing
map zero-texture fallback are closed; the selected scene index, streamed voxel
contents, transient atlas dimensions, and live frame parameters remain open.
Keep Gacha/M02 irradiance fail-closed and do not substitute legacy files or an
arbitrary scene index. See
`reports/assets/character_recovery/gacha_irradiance_scene_ownership_contract.md`.

## Evidence boundary

Every production value must come from serialized data, installed native
behavior, or a validated runtime capture. Unknown values stay neutral,
diagnostic, or disabled.

Static prefab enumeration proves admitted geometry and hierarchy, not final
appearance or runtime activation. Shader decompilation proves a selected
program’s inputs/outputs and render state, not the active keyword variant or
frame schedule. A recovered clip does not prove controller transitions,
blending, IK, facial state, physics, or effect timing.

Do not enable generic Humanoid animation for enemies or props without
actor-specific source evidence. Do not treat filename similarity, shared
materials, or controller proximity as exact actor ownership.

## Main rendering gap

The missing work is the coupled retail frame contract:

- HGRP light scheduling, culling, cookies, and irradiance;
- character shadow atlases, screen shadows, stencil, and VisibilitySH;
- shared depth, GBuffer, motion, and deferred resolve;
- exact material variants, mip payloads, and live renderer state;
- exposure, history, post-processing, and final composition;
- retail-frame validation across representative characters.

Current images are recognizable but flatter than retail, especially around
faces, pale cloth/armor, hair, dark hardware, and contact shadows.

## Main animation gap

Remaining runtime systems include:

- controller transitions, interruption, blending, and root motion;
- broader exact Avatar/clip transport;
- grounding, foot IK, hand targets, and constraints;
- facial emotion, lip sync, gaze, look-at, and animation events;
- secondary motion, wind, cloth, hair, and dynamic bones;
- item/deco/FX lifecycle and gacha timing;
- non-playable rigs, controllers, animation, and VFX execution.

The non-playable baselines prove enumeration and admitted dependencies only.
Runtime modular assembly, VFX, material overrides, animation, and exact
keywords/passes/queues remain incomplete.

## Maintained workflows

```bat
cd unity_endfield_graph_shader_lab

.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat
.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat
.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated assets are rebuildable. Fix generators, importers, runtime code, or
shaders rather than hand-editing generated prefabs.

## Durable reports

Changing inventories and exhaustive renderer/shader proof live under
`reports/assets/character_recovery/` and the lab’s own reports. This file keeps
only stable interpretation and priorities.

## Highest-value next work

1. Close the remaining native component identities and retail culling survivor
   list before populating shadow, depth, GBuffer, irradiance, cookie, and
   VisibilitySH inputs.
2. Validate representative paths against accepted retail captures.
3. Extend texture/mip and material-variant recovery only where visible.
4. Generalize animation from another exact Avatar/clip oracle.
5. Add controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
6. Upgrade representative non-playable families before broad parity claims.

# Li Zhiyan Overview Persistent DXBC contract

## Result

The six materials used by
`P_fxui_lizhiyan_overview_trails_Bip001_R_Finger2Nub` now resolve to exact
compiled programs from the installed client's **Persistent VFS override** of
`HGRP/Effect/VFXBaseV2`, rather than relying on the same-PathID base copy under
StreamingAssets.

The authoritative Persistent Shader source is
`HGRP_Effect_VFXBaseV2_pEC273EDA76F7FCDA.shader`, SHA-256
`F0E2D0C0B486621EC1B88D2B12D65AB07DD7C375CE53268116E8568DFFA903CD`.
It is backed by installed chunk
`36243F039A1BFD05676B5D323B50D4AA.chk`, SHA-256
`BDB0DD43442A795FE67D0722667D0F3B9A33AFBD42BC477C5DA63CC4391CA556`.
The matching Shader PathID is `-1430105248647086886`, pass is `ForwardOnly`,
and `GpuProgramID` is `59433`.

A focused AnimeStudio export produced 2,720 uniquely keyed D3D11 metadata
rows: 1,360 compiled keyword signatures, each with exactly one vertex and one
fragment stage. The three material-selected signatures each have a unique
non-instanced pair and a unique `SRP_INSTANCING_ON` pair:

| Serialized material keywords | Materials | VS SHA-256 | PS SHA-256 | PS samples |
| --- | ---: | --- | --- | ---: |
| none | 01, 05 | `80A32372...A2652A` | `494A1E58...B9E9D` | 1 |
| `_USE_SOFTBLEND` | 06 | `80A32372...A2652A` | `703F6A3D...9E9C6C` | 2 |
| `_SAMPLE_TEX0 + _USE_SOFTBLEND` | 04, 07, 08 | `6747FE2C...A494D` | `D79A6229...7D559` | 3 |

`HG_ENABLE_MV` is an implicit compiled pipeline keyword and is deliberately not
added to the serialized material keyword sets. Every selected fragment writes
both `SV_Target0` and `SV_Target1`. Exact selected DXBC bytes, metadata, FXC
assembly, Ruri HLSL, register declarations, and material mappings are pinned under
`Generated/OriginalData/ShaderEvidence/LiZhiyanOverviewFinger`.

The exact pixel-stage ABI is closed at the bytecode boundary. All three
variants use `b0[28]`, `b1[105]`, and `b2[5]`; `b3` is respectively 21, 22,
and 28 float4 registers. The base variant samples `t0/s0`; soft blend adds
`t1/s1`; sample-texture plus soft blend adds `t2/s2`. Static shader deltas and
coordinate use identify `_MainTex`, scene depth, and `_SampleTex0` with the
applicable LinearClamp/LinearRepeat/LinearMirror samplers. `b0` and `b1`
structurally match TransformVariables and ShaderVariablesGlobal; `b3` is the
material packet, but its lane names are not fully joined. `b2` remains an
unresolved per-draw/particle auxiliary packet because its actual `c4.x/y`
reads do not match the one known `_PerPassConstants` field offset. This
identifies the shader ABI, not the identity of a live retail descriptor table.

The generated contract SHA-256 is
`1191F96B45FD11C47D31C71681B25E77B3DF2CBD2179F21B4D2854D3AD90796B`.

## Scheduling boundary

Queue `3700` lies in the source-defined `3660..3740` after-postprocess
transparent interval. Static native render-path sources prove that the
`Forward Transparent After DOF` pass:

- creates/stores a new scene-color target;
- loads/stores SceneMV as target 1 when valid;
- reads scene depth;
- builds the renderer list with the after-DOF pass-name set.

This is not the queue-3000 main-transparent path. Unity's existing after-post
compositor has the corresponding structural lane, but the retail live handles,
descriptor table, root signature, PSO overrides, renderer-list survivors,
per-particle order, and final compositing remain uncaptured.

The current installed binary is now pinned through exact `.pdata` function
boundaries rather than method-to-next-pointer scan ranges:

| Method | VA | bytes | function SHA-256 |
| --- | --- | ---: | --- |
| `PrepareAfterDOFTranparentRendererList` | `0x189bab274` | 622 | `319799A9...A5E0` |
| `TransparentAfterDOFPassConstructor.ConstructPass` | `0x189bb2e40` | 1,578 | `D54DCF38...12CC` |
| after-DOF render callback | `0x189bb5264` | 806 | `D49C4DE6...11CC` |
| `CreateTransparentRendererListDesc` | `0x189c08904` | 708 | `08E90A05...7163` |
| `RenderForwardRendererList` | `0x189c0a6ec` | 224 | `76DC5D1B...5879` |
| `RenderForwardECSRendererList` | `0x189c0a628` | 194 | `BBA699B5...6F42` |

Rel32 call gates prove `ConstructPass -> prepare list -> create list -> use
list`, and the callback executes global scene-color/vector/texture setup,
fullscreen draw, the ordinary forward renderer list, then the ECS renderer
list. The callback contains no constant-buffer publication. The generated
native ABI contract is `lizhiyan_after_dof_native_abi.json`, SHA-256
`7C89778C66C816F4343E843B7B18B26E395DA0E95379EDD33305228DF173F33C`.

The deferred ECS producer is now closed as well. Current-build
`HGRenderPathDeferred.OnPreRendering` recreates the 32-bit handle each camera
frame when the `forwardTransparent` feature and camera after-DOF gate are both
enabled, otherwise storing `0xffffffff`. The exact creation call uses the
camera culling-view handle, mask/value `0x4400/0x4000`
(`TransparentAfterPP | ShadowOnly` / `TransparentAfterPP`), light-mode mask
`0x20e0 | (outlineState << 9)`, multi-draw and transparent sorting enabled,
and `RemoveWorldUILayer(0xffffffff)`. The result is stored at render-path
offset `0x1388`, copied into PassInput offset `0x04`, and consumed only after
the ordinary list. `HGRenderPathForward.OnPreRendering` creates ordinary
transparent/opaque/pre-Z ECS lists but has no `0x4400/0x4000` AfterPP call and
never writes `0x1388`, so its constructor sentinel remains. Live deferred ECS
survivors remain unobserved.

The transparent-list descriptor is now statically closed before culling:
sorting criteria is numeric `87` (`CommonTransparent | OptimizeStateChanges |
RendererPriority`), the layer mask is `RemoveWorldUILayer(camera.cullingMask)`,
the nullable state block is absent, override material is null, and
`excludeObjectMotionVectors` is false. The per-object request remains the live
`bakedLightingConfig | GetPerObjectMotionVectorConfig(hgCamera)`. Screen-culling
ratio/distance/mask and the resulting survivors remain runtime inputs.

The current-build writer audit narrows those inputs further. `HGCamera..ctor`
is the only mapped HG runtime writer of ratio `+0x9d8` (`0.005`) and distance
`+0x9dc` (`30.0`). Mask `+0xa20` is different: `DoECSCullingCPP`,
`DoECSCulling`, and `HGRenderPipeline.Render` overwrite it from
lightweight-camera culling results. `ExecuteRenderRequestCPP` copies the two
floats into request `+0x68/+0x6c`, then reads the mask getter. These are custom
request/PassInput values, not fields of ordinary Unity `RendererListDesc`.

The exact HGMeshRender internal call is registered at UnityPlayer table index
395 and targets `0x1801f1e40` (206-byte pdata body, SHA-256
`EB9B02F8...1AC153C`). It forwards through request packer `0x18104e7a0` to
registration core `0x18104e300`. The core rejects request index `0xffffffff`,
otherwise appends a 16-byte slot to the manager vector (`+0x08` base, `+0x18`
count) and returns the old count as a zero-based UInt32 handle. Slot `+0x08`
points to a 48-byte state record; helper `0x18104e920` builds its downstream
resource record. These functions contain no entity iteration, survivor write,
sort loop, multi-draw dispatch, or final draw. Final ECS membership, order, and
frame lifetime remain downstream and cannot be represented safely as
`Renderer[]`. The correct ordinary HGMesh command chain is now separated from
HGTree: `AddDrawECSMeshRendererList` icall `0x180063180` records opcode `0x4e`
through `0x1804c77b0`; interpreter case `0x1804ce43a` selects singleton
`+0xb0` and consumer `0x181005c10`, which indexes the same 16-byte slots and
reads state pointer `+0x08`. Its callback thunk `0x180feade0` reaches resource
handler `0x181047160`. This chain constructs command/resource state but still
contains no survivor loop, transparent sort, indirect draw, or queue submit.
HGTree opcode `0x55`, singleton `+0xc0`, 24-byte slots, and consumer
`0x18106aae0` are a separate family and are not evidence for HGMesh execution.

The manager lifecycle is bounded more tightly within this chain. Registration
grows the vector through `0x1802ed7d0 -> 0x180662870` when needed, increments
the count, zeroes the new slot, allocates its 0x30-byte state through
`0x1802fd650`, and stores that pointer at slot `+0x08`. Opcode `0x4e` consumes
the state pointer without changing the vector or count. No count decrement,
in-place reset, slot-clear loop, free, or reuse occurs in the pinned
registration/interpreter/consumer spans. An external context replacement or
teardown remains possible and is the next lifecycle boundary; per-frame reuse
must not be invented from this append-only local path.
Accessor `0x180fc5e60` supplies index `0x14` to generic table accessor
`0x18030f100`, resolving singleton pointer cell `0x1821688a0`. The HGMesh and
HGTree managers are separate context fields at `+0xb0` and `+0xc0`. Generic
setter `0x18030f5b0` owns table writes; bulk registrar `0x180319e60` loops
indices `0..0x15` and conditionally registers slot `0x14`. Global teardown
`0x18058cc20` walks indices `0x1a..1`, invokes object cleanup, and necessarily
clears slot `0x14`. Constructor `0x180fc21d0` installs context vtable
`0x181e1c328`; initialization `0x180fc3500 -> 0x180fc7030` allocates a
0x70-byte manager and initializes it
through `0x1810454c0` with type/category `0xb5`, and stores it at `+0xb0`.
Context teardown `0x180fc2e00 -> 0x180fc3fc0 -> 0x1810459f0` destroys its
16-byte nested entries through `0x18105fe30`, frees its `+0x28/+0x08`
allocations, clears the count, and frees the manager. Logical reset uses
`0x181060330`. Only the registry factory identity that initially supplies
slot `0x14` remains unresolved. More precisely, `0x180319e60` resolves its
binary descriptor to a type ID through `0x1807c5240`, looks it up through
`0x18012be60`, and `0x18031a370` ultimately calls the dynamically initialized
allocator at `[runtime_type_descriptor+0x08]`. The globalgamemanagers
descriptor has no readable class name, so neither that name nor callback
identity is statically proven.

The downstream ordering stage is now positively identified. Resource builder
`0x18104e920` selects one of 14 post-filter workers. The workers assemble
accepted 64-byte records and call in-place sorter `0x181043bd0`; comparator
`0x180fe0740` lexicographically orders the first 16 bytes as unsigned bytes.
Append helper `0x18105e400` copies each complete record without transforming
or reordering it. Key construction is worker-family-dependent, not one uniform
four-dword field ABI. One family puts a 16-bit `asuint(float)>>15` rank plus a
selector in dword 0, followed by the masked 20-bit source/selector lane;
another starts with that source lane and puts a 14-bit
`(~asuint(float)>>17)` rank into dword 3. Both also pack context/resource/type/
index selectors and a conditional `0x01000000` marker. This difference is not
a record-order reversal.
All 14 workers require the two source/context mask tests, the `0x60000` and
`0x7f00` flag groups, `(source+0x10 & 0xc0) == 0xc0`, a view-mask hit, and
source bit 45 clear. Four variants additionally require signed
`source+0x2c > 0` on the source `+0x18` bit-15 path.
The publication path skips records with `+0x20 == 0xffffffff`, resolves their
IDs through `0x181059410`, and appends resolved pointers through
`0x18105e350`. This proves a survivor-record → sort → resource-publication
pipeline. The key is an opaque, worker-variant packed renderer-state key; its
semantic field names remain unresolved, so this must not be called transparent
depth sorting, material sorting, or batch sorting yet.
No indirect draw or backend queue submission has been reached.
The resolved resource pointer is converted into a CPU publication/result
object, then callback thunk `0x180feaea0` reaches generic front-end handoff
`0x1810484e0..0x181049007`. That handoff performs CPU/resource work and virtual
dispatch, but no pointer identity is proven to enter a GPU descriptor, indirect
buffer, or draw command. This UnityPlayer imports no D3D12/D3D11 command API,
contains no D3D12 command-method strings, and explicitly contains
`D3D12 support not compiled in!`; a D3D12 backend cannot be recovered inside
this image. A bounded snapshot of `Player-prev.log` from 2026-08-15 positively
observes this installed-client session creating a threaded Vulkan device on an
RTX 5080 with Vulkan API 1.4.341. The log records the same installed-data path
and Unity 2021.3.34f5, but no UnityPlayer hash, so it is not a cryptographic
join to the pinned image or proof of the exact Li Zhiyan video frame. Generic
Vulkan/API-2 wrappers still are not HGMesh evidence until resource identity is
joined to a Vulkan command.

The generic front-end is now structurally identified. Getter `0x180725dc0`
returns the context whose constructor `0x1809258c0` installs vtable
`0x181dcb360`; the publication handoff's resource paths record opcodes `0x2748`
and `0x274a`. Backend selector `0x18072f7e0` routes internal backend ID 2 to
factory `0x180891210` and table `0x181dbc098`. This ID is an internal HG family,
not Unity's public `GraphicsDeviceType` value. API-2 slot `+0xde8` reaches
`0x18083f1e0 -> 0x180843d60`, which resolves Vulkan pipeline, descriptor,
draw, and queue operations including `vkCmdDraw`, indirect variants, and
`vkQueueSubmit`. This closes backend family and submission capability, not the
remaining HGMesh resource-identity edge into one specific Vulkan draw.

The graphics command stream is now decoded one layer farther. Front slot
`+0x268` writes aligned opcode `0x2748` records containing the resource-object
pointer and increments its `+0x0c` reference field; slot `+0x280` writes
variable opcode `0x274a` records containing an opaque token/length-like qword
and serialized payload. Interpreter `0x1813aee90`, through dispatch table
`0x1813bb574`, routes cases `0x1813b1624/0x1813b16f0` back to API-2 slots
`+0x268/+0x280`. Both converge on `0x180842370` with modes 1 and 0 and operate
on the API-2 `context+0x2e48` collection of 16-byte resource/state records.
They are resource/state operations, not Vulkan draw opcodes.

For `0x2748`, the decoder preserves the original object pointer unchanged.
`0x180842370` resolves object-local maps at resource offsets
`+0x20..+0x30/+0x50/+0x70`, writes descriptor-like entries under `S+0x2a0`,
and writes payload backing under `S+0x22d0`. A later opcode `0x2730` calls
API-2 `+0xe90` (`0x180843bf0`), which packages those exact state regions for
`0x18083f680`; its call at `0x18083f89d` reaches
`vkUpdateDescriptorSetWithTemplate`. This is a conditional shared-API-2-state
route, not a per-record HGMesh-to-descriptor identity: the HGMesh handoff
itself never emits `0x2730`.

The later Vulkan executor consumes a separate master callback list at
`context+0x2b50`. Its verified callbacks bind index/vertex buffers
(`0x18082d6b0`), bind pipeline/descriptors and dynamic state (`0x18082e660`),
issue indirect draws (`0x18082e820`), or issue the bounded fullscreen-style
`vkCmdDraw(3,1,0,0)` helper (`0x18083d264`). The exact remaining static/runtime
edge is therefore the same-stream/same-frame association from the
`0x2748`-populated state and `0x2730` descriptor update into a particular
`0x2731` execution, `+0x2b50` callback node, and draw record—not a generic
uncertainty about which graphics API is active.

All four front writers use the same per-instance recorder state at context
`+0x2711/+0x2720`; buffer base/cursor/capacity are `+0x140/+0x148/+0x14c`.
Opcode `0x2730` records seven qwords plus a counted u32 payload and dispatches
to `+0xe90`; `0x2731` has no payload and dispatches to `+0xde8`. Begin/end
recording are front slots `+0xf78/+0x880`, and bounded-substream wrapper
`0x1813aea00` advances one shared parser cursor. This proves append order equals
invocation order inside one recorder interval, but no producer call edge
guarantees `0x2748 -> 0x2730 -> 0x2731` or that all three share an interval.
Direct handoff audit proves only `0x181048848: +0x268 (0x2748)` followed by
`0x1810488dc: +0x280 (0x274a)` for the same 0x90-byte result record and front
context. No `+0x2a0/+0x3e8` call occurs in the handoff or its bounded direct
callees. Known `0x2730/0x2731` producers are separate generic helpers without
a proven shared resource identity or recorder interval.

API-2 `+0xda0` constructs 0x68-byte resource-binding and 0x40-byte
pipeline/descriptor-state child nodes; `+0xda8` constructs a 0x50-byte
indirect-draw node. `0x180841c40` packages the child heads at `+0x2b58/+0x2b60`
into master nodes at `+0x2b50`. The indirect payload contains its buffer at
`+0x30`, byte offset at `+0x38`, draw count 1, and stride 0. The original
`0x2748` pointer itself is not copied into these nodes, so derived-state
association still requires runtime values or a capture.
These nodes are generic API-2 capabilities. Ordinary HGMesh renderer-list
wrappers and the publication handoff contain no static `+0xda8`, `+0xde8`,
indirect-draw, or queue-submit edge, so they must not be attributed to the
character path without runtime identity.

Global singleton teardown is now closed through the concrete slot-0x14 context
vtable and `+0xb0` manager destruction chain described above; it is no longer
part of the live-draw recovery gap.

The live-draw gap now has an executable offline intake contract rather than a
prose-only request. `build_lizhiyan_retail_draw_observation_contract.py` pins
the 1,678,613,397-byte retail MKV at SHA-256
`2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7`,
validates its 3840x2160 H.264 High, yuv420p, BT.709 limited-range stream, and
uses integer millisecond PTS instead of `frameIndex/60`. The generated fixture
is deliberately `proof_pending` with no trace inputs and
`visibleAdmission=false`. A future offline import admits only an ordered,
same-session/frame/recorder chain across the full HGMesh record and stable
resource generation, `0x2748`, identical derived-state hash, descriptor
update/bind, `0x2731`, draw, submit, and exact decoded retail pixel, plus a
same-build Li-absent or Wulfa control. Pointer equality, timestamps, generic
API-2 events, or teal pixels alone fail closed.

`lizhiyan_retail_visual_oracle.json` now supplies the separate deterministic
visual regression contract. It decodes exact input PTS
`38000/40000/42000/43000/44000/46000` to 960x540 RGB24, pins every scaled-frame
hash, and measures four fixed source-space ROIs with one predeclared teal
predicate. Broad-ROI teal coverage rises from `0.020755576` at PTS 38000 to
`0.216991352` at PTS 40000 and falls to `0.006558944` at PTS 46000. This closes
repeatable phase anchors for Unity comparison, not material or draw ownership;
the artifact remains diagnostic-only and non-admitting.

The exact transition is now bounded one frame at a time. The prior actor is last
stable at PTS 37667 and begins fading at 37683; the blank interval is PTS
37700..37950, and Li is first recognizable at PTS 37967. The first teal edge is
tentative at PTS 38167 and the first unambiguous slab is PTS 38183. Source controller data independently
closes the 10.7-second start clip entry to clip-local `0.062452073 s`, exit to
`10.68547903 s`, and normalized transition to `0.014519697 s`; the clip contains
no AnimationEvents. `lizhiyan_overview_timing_alignment.json` keeps PTS 37967
as a visual candidate restart only. Under current lab publication semantics the
finger effect would exist from candidate PTS 38800 through 41134, which covers
the PTS-40000 peak but not the measured teal at PTS 42000. This falsifies the
idea that the one recovered finger prefab alone explains the full retail teal
sequence and prioritizes the other eleven serialized entrance requests plus the
original request producer.

The next root request is now classified rather than left as a generic missing
effect. `P_fxui_lizhiyan_overview_start_01` is a source-closed five-node static
mesh hierarchy with four MeshFilter/MeshRenderer pairs, zero ParticleSystems,
duration `2.2`, delay `0`, one shared mesh PathID `-6840663686705882004`, and
three material PathIDs mapping exactly to `M_fxui__lizhiyan_overview_09/_10/_11`.
The converted OBJ and serialized queue-3704 VFXBaseV2 material payloads exist.
Animation-helper start clip PathID `7360398354216100382` resolves to converted
`A_fxui__lizhiyan_overview_start_01` at 30 Hz with stop time 6.366667 and no
AnimationEvents. All eight serialized Texture2D dependencies resolve through
the AssetMap to converted PNGs. The clip's 53 material float curves are now
fully named: Unity `Animator.StringToHash` resolves four targets to start_01
and six to start_02/start_03, while AnimeStudio's CRC28-plus-channel encoding
resolves `_MainTex_ST.x/y/z/w`, `_TintColorAlpha`,
`_DissolveScheduleOffset`, and `_DisturbUIntensity1`. The generated resolved
clip imports as exactly 53 MeshRenderer curves with the expected ten paths and
seven properties.
Native mesh/texture import parity and
shader/draw admission are not closed. The lab
therefore records a `static_mesh_animated` contract but does not fabricate a
particle prefab or install a runtime binding.

The lab runtime now represents that distinction explicitly through
`BindingKind.StaticMesh` and `EndfieldRecoveredStaticMeshEffectSource`.
Runtime validation pins the exact start_01 root, EffectSetting, Animator,
animation helper, clip, four MeshFilter/MeshRenderer pairs, shared mesh, and
three-material identity set; it also requires zero ParticleSystems and every
native/import/shader gate. The current negative Unity validator exits
successfully only when the contract is refused at `sourcePayloadApplied=false`
and `visibleAdmission=false`. No prefab or Li controller binding was added.

A requested English-only Claude Code second-opinion audit produced no output
within roughly eight minutes and was terminated. It contributes no evidence;
the remaining native-consumer question stays open under the local fail-closed
boundary.

The fixed-build managed consumer question is now narrower than that earlier
boundary. Exact metadata/body mapping proves this chain:

| Method | Token | VA | Role |
|---|---:|---:|---|
| `AnimatorBehaviourPlayEffect.OnStateEnter` | `0x06000DEF` | `0x186B85E54` | consumes the authored controller effect record |
| `AnimatorBehaviourPlayEffectHelper.Add` | `0x06000DFA` | `0x186B859F4` | owns the live effect entry and starts its instance |
| `EffectSetting.Init` | `0x06005C6D` | `0x183963ED0` | initializes the serialized EffectSetting |
| `EffectSetting._InitLodData` | `0x06005C75` | `0x18339D530` | initializes animator/renderer/particle LOD rows |
| `EffectSetting.PlayEffect` | `0x06005C7C` | `0x1834FC4D0` | dispatches `EffectLodCfg.Play` |
| `EffectAnimation.Play` | `0x060059DA` | `0x1831DDA80` | drives the effect animation |
| `EffectAnimation._CreatePlayableGraph` | `0x060059D0` | `0x183437F90` | constructs PlayableGraph, AnimationPlayableOutput, and mixer |
| `EffectAnimation._AddClip` | `0x060059CD` | `0x183437D60` | creates AnimationClipPlayable |
| `EffectAnimation._PlayAnimation` | `0x060059D1` | `0x183436AD0` | samples and advances the clip |

The full build gate and broader lifecycle census remain in
`overview_effect_owner_animator_negative_20260815.md`. For start_01, exact
serialized LOD entries contain a root Animator and four MeshRenderers with all
particle pointers null. This proves the managed static-mesh animation owner;
it still does not join `EffectLodCfg.renderer` to a specific renderer-list,
API-2 resource, descriptor, PSO, Vulkan draw/submit, or visible pixel. The
published native catalog has exact VAs, bounded spans, head bytes, and direct
calls but no per-method body SHA-256 values, so none are claimed here.

The next positive proof is now an explicit runtime-capture contract rather
than a generic request for “a capture.” On this exact build it must join one
`CreateRendererList` handle through opcode `0x4e`, a complete accepted/sorted
64-byte record and resolved resource identity, to a same-frame final draw and
visible Li Zhiyan after-DOF pixel. The bounded observation points are
`0x1801f1e40`, `0x18104e300`, `0x181005c10`, `0x18105e400`, and
`0x18105e350`, plus `0x1813b1624`, `0x18083f89d`, and `0x1813afed9`; the
strongest oracle remains the hand-adjacent teal layer near
40 s. A Li-absent or Wulfa replacement capture is required as a negative
control. The contract itself does not authorize retail attachment or injection,
and mandates stopping on protection refusal or any build/prologue drift.

The normal current-build per-object request is now source-closed to `47`:
pipeline construction and every normal `ConfigureKeywords` call write baked
lighting flags `15`, while `get_enableMV` and
`GetPerObjectMotionVectorConfig(non-null HGCamera)` produce `32`. IFix patch
branches remain an explicit replacement boundary. Unity now requests the same
combined `PerObjectData` value instead of motion vectors alone.

HGCamera construction writes screen ratio `0.005` and distance `30.0`; its lazy
mask getter builds a mask from 17 named layers. The selected Viewer camera has
Unity culling mask `0xffffffff` and no serialized HG screen-culling overrides,
but the runtime ECS/lightweight-camera path rewrites the HG mask and actual
survivors remain live facts. Standard Unity `DrawRenderers` has no equivalent
for HG's extra three screen-culling descriptor fields.

## Unity admission

An editor-only validator now verifies the source overlay, shader/program
identity, complete compiled census, six-to-three material mapping, artifact
hashes, exact assembly, constant-buffer lengths, texture/sampler pair counts,
fragment register signature, dual outputs, and after-DOF queue contract. The
effect importer calls this validator before building the prefab.

All six generated materials remain on `VFXUnavailableFailClosed`. Exact DXBC
identity is necessary evidence, but it does not prove that a particular retail
draw used a particular live descriptor table or PSO.

The lab after-post list now uses numeric-equivalent sorting criteria `87` and
removes a named `WorldUI` layer when that layer exists, without copying the
installed client's numeric layer index. It still has no HG ECS renderer-list
consumer and no equivalent for HG's screen-culling fields; both remain visible
diagnostic gaps rather than inferred behavior.

## Remaining work

The offline ABI audit also found that the lab's after-DOF color/depth/sceneMV
attachment schedule matches the static retail pass. All six selected materials
serialize `_IsSceneEffect=0` and `_EnableTransparentMV=0`; the exact fragment
therefore bypasses `_VFXParams1` and motion-history output. Publishing a guessed
neutral `_VFXParams1` or fabricated previous-frame matrices would be a less
accurate recovery. Exact inverse-VP soft-depth behavior remains missing, and
the selected-material gates do not form a general VFX motion contract.

The highest-value evidence is a retail D3D12 capture in the recorded
`38-47 s` Li Zhiyan window, around the hand-adjacent teal layer near 40 s.
Without such a capture, the remaining offline step is the live native
root-signature/descriptor/PSO join and renderer-list survivor identity. Static
resource names, neutral `_VFXParams1`, or attachment parity must not unlock
visible pixels.

Before any authorized runtime capture, render the current Li Zhiyan entrance at
the six oracle PTS-equivalent phases and compare the same fixed ROIs. Camera,
controller-event chronology, background, depth/blur, and final compositing must
be closed independently; do not replace the six original VFXBaseV2 materials
with an approximate visible shader merely to reduce the image difference.

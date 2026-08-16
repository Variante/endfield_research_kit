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
`4B6963A4BE824C6A8B8FA92AD36FCCEEFE677A541F69C5203BA35E6104E0AA46`.

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

The downstream ordering stage is now positively identified. Resource builder
`0x18104e920` selects one of 14 post-filter workers. The workers assemble
accepted 64-byte records and call in-place sorter `0x181043bd0`; comparator
`0x180fe0740` lexicographically orders the first 16 bytes as unsigned bytes.
Append helper `0x18105e400` copies each complete record without transforming
it. The four key dwords are source-closed to packed renderer-state fields: a
masked 20-bit source and shifted selectors/flags, source offsets `+0x08` and
`+0x0c`, a conditional `0x01000000` marker, context byte state, source
`+0x22` u16, and `((~asuint(float)) >> 17) & 0x3fff`.
All 14 workers require the two source/context mask tests, the `0x60000` and
`0x7f00` flag groups, `(source+0x10 & 0xc0) == 0xc0`, a view-mask hit, and
source bit 45 clear. Four variants additionally require signed
`source+0x2c > 0` on the source `+0x18` bit-15 path.
The publication path skips records with `+0x20 == 0xffffffff`, resolves their
IDs through `0x181059410`, and appends resolved pointers through
`0x18105e350`. This proves a survivor-record → sort → resource-publication
pipeline. The key is an opaque packed renderer-state key; its semantic field
names remain unresolved, so this must not be called transparent depth sorting,
material sorting, or batch sorting yet.
No indirect draw or backend queue submission has been reached.

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

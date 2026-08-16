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
`6A73576511DE6FF071C05DDD6E6023C2A836358F2BB4841561BD9405BEB8B63A`.

The transparent-list descriptor is now statically closed before culling:
sorting criteria is numeric `87` (`CommonTransparent | OptimizeStateChanges |
RendererPriority`), the layer mask is `RemoveWorldUILayer(camera.cullingMask)`,
the nullable state block is absent, override material is null, and
`excludeObjectMotionVectors` is false. The per-object request remains the live
`bakedLightingConfig | GetPerObjectMotionVectorConfig(hgCamera)`. Screen-culling
ratio/distance/mask and the resulting survivors remain runtime inputs.

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

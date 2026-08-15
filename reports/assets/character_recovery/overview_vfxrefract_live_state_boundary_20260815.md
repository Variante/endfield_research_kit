# Character Info `M_UI_charChoose_12` VFXRefract live-state boundary

Date: 2026-08-15

Scope: read-only audit of the pinned desktop client for the Character Info
`CharEffect/trail` draw.  This report separates shader/material state that is
recoverable from serialized data from the final D3D12 draw packet that still
requires capture.  It does not change the Unity lab or memory documentation.

## Exact native gate

All native statements in this report use the selected installed pair and pass
`scripts.common.check_installed_native_inputs()` with `status=validated`:

| input | path | SHA-256 |
| --- | --- | --- |
| `GameAssembly.dll` | `D:\Program Files\Endfield Game\GameAssembly.dll` | `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce` |
| `global-metadata.dat` | `D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat` | `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e` |

The supporting render-path audit also pins `UnityPlayer.dll` to
`b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`.
Missing or mismatched native inputs invalidate the native portions below;
there is no fallback to another build.

## State-resolution result

The important correction is that the converted ShaderLab text is not, by
itself, the effective fixed-function state.  The serialized shader's parsed
`m_State` names the blend, depth, and cull fields as material properties:

```text
rtBlend[0].srcBlend       = property _SrcBlend
rtBlend[0].destBlend      = property _DstBlend
rtBlend[0].srcBlendAlpha  = <noninit> = Zero
rtBlend[0].destBlendAlpha = <noninit> = One
rtBlend[1].srcBlend       = property _MVSrcColorBlend
rtBlend[1].destBlend      = property _MVDstColorBlend
rtBlend[1].srcBlendAlpha  = <noninit> = One
rtBlend[1].destBlendAlpha = <noninit> = One
zTest                     = property _ZTest
zWrite                    = property _ZWrite
culling                   = property _CullMode
rtSeparateBlend           = true
```

The converted shader contains `Blend ... Zero Zero`, `ZTest Off`, and
`Cull Off` because the converter emits the parsed default values (`val=0`)
for the property-bound fields.  Treating those textual defaults as the live
PSO would make Target 0 write zero color, contradicting the fragment's
scene-color output and the material-state contract.  The material instance is
therefore the source of the selected live state, subject to a final API
capture for absolute proof.

For `M_UI_charChoose_12` the serialized material values are:

| state | property/value | selected interpretation |
| --- | --- | --- |
| Target 0 color | `_SrcBlend=5`, `_DstBlend=10` | `SrcAlpha`, `OneMinusSrcAlpha` |
| Target 0 alpha | parsed non-property `Zero`, `One` | preserve destination alpha |
| Target 1 color | `_MVSrcColorBlend=3`, `_MVDstColorBlend=6` | `SrcColor`, `OneMinusSrcColor` |
| Target 1 alpha | parsed non-property `One`, `One` | additive alpha |
| depth test | `_ZTest=4` | numeric `LessEqual` in the Unity enum |
| depth write | `_ZWrite=0` | `Off` |
| culling | `_CullMode=2` | preserve numeric value 2; do not rename it from the source property enum without a capture/native enum decode |
| color masks | parsed `15` for both targets | `RGBA` |

The material also stores `_AlphaSrcBlend=1` and `_AlphaDstBlend=10`, but the
selected Refraction pass marks its Target 0 alpha fields `<noninit>` rather
than those properties.  They must not be substituted into this pass.

The selected fragment writes Target 1 as `(0,0,1,0)` because
`_SurfaceType=1` and `_EnableTransparentMV=0`.  With the selected Target 1
blend, the result is:

```text
out.r = dst.r
out.g = dst.g
out.b = 1
out.a = dst.a
```

This is the current Character Info result, not a general claim for materials
with transparent motion enabled.

## `_VFXParams0` producer and use

The native producer is source-closed for this build:

```text
HGRenderPathBase.UpdateShaderVariablesGlobalVFX
  -> ShaderVariablesGlobal + 0x670

_VFXParams0.xyz = HGVFXManager.m_playerPosition
_VFXParams0.w   = fmodf(UnityEngine.Time.time, 1024.0f)
```

The selected VFXRefract fragment reads global constant register `c103.w`
(`_27_m0[103u].w` in the decompiled HLSL), corresponding to metadata byte
offset `1648` and CB byte offset `0x670 + 0xc`.  The selected material's UV
speed properties are zero, so the current Character Info image is not
visibly time-animated by this lane, but the global write is still part of the
retail shader contract and must be published when the compatible shader is
used.  `_VFXParams0.xyz` is not read by this selected fragment.

The previously confused `unity_LODFade` lane is separate: it is a PerDraw
`b2/c4` value used by selected VFXBase dither/fade programs, not
`ShaderVariablesGlobal._VFXParams0.xy`.

## Culling, sorting, and particle inputs

The native HGRP route is:

```text
HGRenderPathScene
  -> ForwardPassUtils.PrepareForwardTransparentRendererList(...)
  -> renderer list with LightMode=Distortion and queue=3000
  -> ForwardPassUtils.RenderForwardTransparent
```

The pinned renderer-list sorting criteria is
`CommonTransparent | RendererPriority = 0x57`.  The selected renderer has
`m_RendererPriority=0`, sorting layer/order `0/0`, and sorting fudge `0`, so
there is no source-backed per-renderer priority offset to add.  Queue 3000
selects the main transparent/Distortion lane; it is not the separate
after-DOF range `3660..3740`.

The serialized `CharEffect/trail` particle inputs are:

```text
ParticleSystem: cullingMode=0 (Automatic), maxAliveDistance=10,
                limitAliveDistance=false, lengthInSec=0.5,
                looping=false, prewarm=false, playOnAwake=false
ParticleSystemRenderer: enabled=true, renderMode=1, sortMode=0,
                        rendererPriority=0, sortingFudge=0,
                        dynamicOccludee=1, GPUInstancing=true,
                        custom vertex streams=[0,1,3,4,5,34]
```

The root `CharEffect` renderer is disabled and has no material; the child
`trail` renderer is the only draw admission.  Automatic particle culling,
camera frustum culling, live particle bounds, simulation time, and the exact
survivor/order list remain runtime values.  Static `m_SortMode=0` and the
renderer-list criteria do not prove the order of individual live particles.

## SceneColor / SceneMV resource binding

The native render-graph contract is closed to the following minimum:

```text
incoming sceneColor snapshot -> _SceneColorTexture
new Target 0 clone: B10G11R11_UFloatPack32 (GraphicsFormat 74), Store
sceneMV Target 1: A2B10G10R10_UNormPack32 (GraphicsFormat 75), Load/Store
sceneDepth: Distortion ReadWrite
LightMode: Distortion
queue: 3000
```

The pass copies the incoming SceneColor into the new Target 0 before drawing,
binds the old handle as `_SceneColorTexture`, and publishes the new handle for
the next consumer.  SceneMV is the current-frame accumulated attachment, not
a fabricated history texture; its neutral clear belongs to the earlier
GBuffer/opaque owner.  The selected `_USE_RBOFFSET` variant samples the same
incoming SceneColor twice (ordinary and `_RBOffset` UV) and combines the
samples with the serialized channel masks before writing Target 0.

Native anchors for the current build include:

| method | VA |
| --- | ---: |
| `ForwardPassUtils.PrepareForwardTransparentRendererList` (cull overload) | `0x189babb58` |
| `ForwardPassUtils.PrepareForwardTransparentRendererList` (HGRP overload) | `0x189bab94c` |
| `ForwardPassUtils.PrepareTransparentPassData` | `0x189bac2f8` |
| `ForwardPassUtils.RenderForwardTransparent` | `0x189bacfcc` |
| `TransparentAfterDOFPassConstructor.ConstructPass` | `0x189bb2e40` |
| `HGRenderPathScene.RenderPostProcessPhase1` | `0x189bffeb0` |

## Minimum Unity implementation contract

The lab implementation should use the following identity and state gates:

1. Material `M_UI_charChoose_12`, shader `HGRP/Effect/VFXRefract`, valid
   keyword exactly `{_USE_RBOFFSET}`, and texture `T_fx_mask_01_M`.
2. Refraction/Distortion pass with property-bound state: Target 0 color
   `_SrcBlend/_DstBlend`, Target 0 alpha `Zero/One`, Target 1 color
   `_MVSrcColorBlend/_MVDstColorBlend`, Target 1 alpha `One/One`, and
   `_ZTest/_ZWrite/_CullMode` from the material instance.
3. Keep the SceneColor clone/snapshot and SceneMV Load/Store attachment
   lifecycle; do not use one ordinary transparent color target.
4. Publish `_VFXParams0` at global CB offset `0x670`, including the `fmod`
   time lane, even when this material's speed values are zero.
5. Feed the renderer list with queue 3000, LightMode `Distortion`, sorting
   criteria `0x57`, and the exact trail particle payload.  Keep cull survivors
   fail-closed when camera/particle runtime state is unavailable.

## What still requires D3D12 capture

The following are not proved by the offline assets/native bodies and remain
capture gates:

- final D3D12 PSO blend factors, cull face, depth/stencil state, and any
  native RenderStateBlock override over the property-bound shader state;
- actual renderer-list survivors and per-particle order for the recorded
  camera/frame;
- physical SceneColor/SceneMV descriptor aliases, sample count, and live
  `_SceneColorTexture` descriptor identity;
- the live `_VFXParams0`, `_ScreenSize`, mip bias, camera matrices, particle
  instance buffer, and `_RBOffset` sample coordinates;
- low-resolution transparent/refraction branch selection and the final draw
  submission packet.

Until those values are captured from the same gated client, this report is a
source-backed executable contract, not a pixel-parity claim.

## Evidence pins

| artifact | SHA-256 |
| --- | --- |
| `M_UI_charChoose_12` material JSON | `531854ec624fb21b74a2793fc6a10a5fea739ceb2a8d432c2ccdccd3815be1a6` |
| converted `HGRP_Effect_VFXRefract` shader | `c18d2f942cdb6a4cc921fe81c43a7e560ec0a46c9c812dad0e894465f16d2f0d` |
| parsed selected DXBC `0091_endfield_dxbc_1.dxbc` | `8c449c937e39f90af7dca4543c8be1dbd3a50c846df2015e54abaa6b6bfb241` |
| selected fragment HLSL | `8e0e94193287154d06ffd9fa7d7848ce084598aca73130244fe207f7b42454a3` |
| selected DXBC metadata | `a86ccc272017222f94d21c9db9780bad94c24cf51bd57131d86aca121a574f78` |
| `vfx_mrt_source_chain.json` | `34d75c19d64bfb0b6e12035810e842994780a15b1b0f47ce0de45594d9887b53` |

The last hash is a report-content pin only; rerun the existing
`scratch/reverse_engineering/vfx_mrt_source_chain/build_vfx_mrt_source_chain.py --check`
when regenerating its report.

# `M_fx_ui_glow_902`: native SceneMV queue-3005 boundary

Date: 2026-08-15

Verdict: **queue 3005 belongs to the main transparent SceneMV MRT lane, not
the after-post lane; current lab admission is correctly fail-closed, but the
retail native evidence does not justify broadening all transparent queues.**

## Gate and source identity

Native conclusions use the selected exact build:

- `GameAssembly.dll` SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`;
- `global-metadata.dat` SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`;
- `UnityPlayer.dll` SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`.

Source material facts already pinned by the shader/material audit:

```text
material:             M_fx_ui_glow_902
custom queue:         3005
shader GUID:          43f9bd357f94af04b93b7864ca8e3c0f
source material PathID: -6130217779138746968
source artifact SHA256: 8A861419BB03197A98A9AAFB2EEDCB4EB38B57D47795535F319075E8AD754540
RenderType:           Transparent
SurfaceType:          1
EnableTransparentMV:  0
IgnorePostExposure:   1
InParticle:           1
```

The shader is `Hidden/Endfield/Recovered/Zhuangfy/VFXBaseV2MRT`, with
`LightMode=ForwardOnly` and
`EndfieldSceneMVMRT=ExactSelectedFiftyThree`.

## Facts: native scheduling and targets

The gated native callsite census establishes the following relevant methods
(addresses are recorded here only, not in memory prose):

| method | VA |
|---|---:|
| `ForwardPassUtils.PrepareForwardTransparentRendererList(cullResults, hgCamera, passNames, ...)` | `0x189babb58` |
| `ForwardPassUtils.PrepareForwardTransparentRendererList(hgrp, camera, ...)` | `0x189bab94c` |
| `ForwardPassUtils.PrepareTransparentPassData(...)` | `0x189bac2f8` |
| `ForwardPassUtils.RenderForwardTransparent(context, data)` | `0x189bacfcc` |
| `HGRenderPathScene.RenderPostProcessPhase1(...)` | `0x189bffeb0` |
| `TransparentAfterDOFPassConstructor.ConstructPass(...)` | `0x189bb2e40` |

The source-closed pass order is:

```text
GBuffer / initial SceneMV clear
  -> ForwardOpaque
  -> main ForwardOnly transparent
  -> Distortion
  -> Phase 1 post (DOF, MotionBlur, ...)
  -> after-DOF ForwardOnly
  -> Phase 2 post
```

Native/resource evidence closes the main ForwardOnly attachment contract as:

- target 0: a new scene-color target cloned from the incoming SceneColor
  descriptor; incoming SceneColor is copied into it before drawing;
- target 1: current SceneMV, `Load/Store`, format
  `A2B10G10R10_UNormPack32` when valid;
- depth: current SceneDepth, read-only for ForwardOnly;
- `_SceneColorTexture`: the incoming pre-draw SceneColor snapshot, never the
  target currently being written.

The after-post transparent list is separately admitted at queue range
`3660..3740`. Gacha M02 is queue 3000 and is not after-DOF. Therefore a
serialized queue of 3005 cannot be assigned to after-post merely because it is
transparent.

## Facts: shader program outputs

The recovered BaseV2 MRT fragment declares:

```hlsl
float4 color   : SV_Target0;
float4 sceneMV : SV_Target1;
```

Its selected non-instanced path emits:

```text
Target0 = premultiplied scene color, output alpha
Target1 = (0, 0, 1, coverageActiveMask)
```

`_EnableTransparentMV=0` gates SceneMV XY to zero. Target-1 blending preserves
the destination motion R/G, forces B to 1, and accumulates the source alpha
coverage. This is a two-target producer and cannot safely be sent through the
ordinary color-only transparent fallback.

The shader also clips unless `_EndfieldSceneMVMRTReady` and the recovered VFX
globals-ready gate are active. Thus merely drawing the material at queue 3005
without the MRT compositor would not reproduce its intended output.

## Narrow implementable boundary

The smallest safe support unit is a source-identity-gated **Glow902 main
transparent lane**:

1. Admit only the exact material PathID/artifact hash, shader GUID, shader tag,
   queue 3005, render state, and BaseV2 MRT pass signature.
2. Create/use the existing SceneMV resource and MRT attachments.
3. In the main transparent callback, draw queue 3000 first, then queue 3005
   exactly, using the same SceneColor clone, SceneMV Load/Store target 1,
   read-only depth, `_SceneColorTexture` snapshot, and ready gate.
4. Continue the existing Distortion and post phases unchanged.

The required relative order is therefore:

```text
main ForwardOnly queue 3000 -> Glow902 queue 3005 -> Distortion -> post
```

It must not be placed in `3660..3740`, and it must not be admitted by changing
the generic BaseV2 rule to `3000..3659`; that would silently admit unverified
MRT materials and alter SceneColor/SceneMV ownership.

## Inference

- Queue 3005 is an intra-main-transparent ordering offset, not an after-post
  selector. The material's `ForwardOnly` pass, dual MRT outputs, and target-1
  blend semantics all agree with that placement.
- The current `CollectRequest` rejection is a valid safety boundary, not proof
  that the material is an ordinary fallback transparent object.
- A precise Glow902 lane can be implemented without changing the established
  retail pass order; generic queue widening cannot.

## Unclosed

- Offline evidence does not prove the exact retail renderer instance/lifetime
  that owns Glow902 at the selected frame, nor its particle draw ordering
  relative to other queue-3000 objects.
- The native binary closes renderer-list preparation and pass/resource order,
  but not a unique Glow902 object-to-renderer-list membership record.
- Physical SceneColor/SceneMV pool aliases, camera viewport scale, and runtime
  culling remain live state.
- No evidence supports sending Glow902 to after-post, fabricating SceneMV, or
  treating `_EnableTransparentMV=0` as permission to use a single RTV.

Primary evidence: `scratch/character_recovery/glow902_unity_scenemv/README.md`,
`scratch/reverse_engineering/vfx_mrt_compositor/`,
`scratch/reverse_engineering/vfx_mrt_source_chain/`,
`scratch/reverse_engineering/scenemv_total_order_recovery/`, and
`scratch/reverse_engineering/zhuangfy_gacha_room_scene_admission/`.

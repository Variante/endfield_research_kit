# Gacha DefaultDeferred resolver and framebuffer contract

Date: 2026-08-14

Verdict: **SOURCE_CLOSED_RESOURCE_FRAMEBUFFER; CONTENT FAIL-CLOSED**

The original binaries now close the ordinary DefaultDeferred producer/resolver
topology and the missing pass-0 variant selection. They do not provide the
settled retail contents for the resolver's 25 SRVs, nine constant buffers,
structured binning buffer, or live shadow/irradiance/AO/SSR inputs. No lab draw
or Unity patch is enabled from this evidence.

## Evidence pins

- Installed `GameAssembly.dll` SHA-256:
  `0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`.
- Installed `UnityPlayer.dll` SHA-256:
  `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`.
- Installed `global-metadata.dat` SHA-256:
  `90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`.
- Current offline audit pins:
  - framebuffer compatibility `audit.json`:
    `98D4B4798545E640F96A2970FD78CC339BA2FBDED0727AEC70BE342F97646FEB`;
  - fallback selector `audit.json`:
    `CD02CC0A8636546A8D3D45A5E322ECED8FF26DFAE68EFF1643E33CBDAF16E409`;
  - keyword state `audit.json`:
    `2DBDC0A7AADCB15592C8F74CCD871329AD5ECC2BBD976FEEC625766DE1F241D9`.

## Installed route and variant selection

`HGRenderPipelineRuntimeResources` supplies `deferredPS` from the
`HGRP/DeferredLighting` asset. `DeferredLightingPassConstructor` creates the
material from this runtime shader slot; there is no serialized deferred
Material PathID to substitute. The ordinary Gacha route calls the deferred
constructor and draws resolver passes 0, 1, and 2, then invokes WriteAlpha.
The selected camera has `HGUtils.RenderWithAlpha(hgCamera)=false`, so WriteAlpha
submits no draw; SphereOutside stencil ref 0 makes pass 0 the effective
lighting route.

The installed ordinary state is:

- `HG_ENABLE_SCREEN_SPACE_SHADOW_MASK = true`;
- `HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED = false`.

All 64 serialized D3D11 pass-0 pairs carry the subpass keyword. UnityPlayer's
best-match selector at `0x18061f807` scores each supported state as
`popcount(request & variant) - 16 * popcount((~request) & variant)`, updates
only on a strict `>` score, and loads the winning subprogram from
`Program+0x8`. The unique winner for the ordinary request is serialized pair
96/97, with screen-shadow plus subpass keywords, despite the ordinary global
subpass bit being false. The pair is therefore a proven missing-variant
fallback, not a claim that the ordinary route publishes the subpass keyword.

Selected pass-0 payloads:

- vertex: 496 bytes, `vs_5_0`, SHA-256
  `A6AFE2C96CAA3FD940004CE9EE725886D0F8DF683D5F73403278743E32563155`;
- pixel: 48,984 bytes, `ps_5_0`, SHA-256
  `B21A1E35EDA1C5BCB60198C6AF313799DDCC94D0CEE0BE9025938F3BA8C56B6F`.

## Framebuffer topology

The selected producer is `HGRenderPathDefaultDeferred` /
`GBufferPassConstructor.ConstructPass`:

| Slot | Resource | Format |
|---:|---|---|
| 0 | SceneColor | `B10G11R11_UFloatPack32` |
| 1 | SceneMV | `A2B10G10R10_UNormPack32` |
| 2 | GBuffer A | `A2B10G10R10_UNormPack32` |
| 3 | GBuffer B | `A2B10G10R10_UNormPack32` |
| 4 | GBuffer C | `R8G8B8A8_SRGB` |

It has one writable depth attachment with authored intent
`D32_SFloat_S8_UInt`; the selected route is single-sample. The resolver is a
separate pass, not an Endfield-only input-attachment pass:

- one color attachment, SceneColor, with Load/Store;
- one read-only sceneDepth attachment;
- GBuffer A/B/C registered as ordinary `Texture2D` SRVs/globals, not RTVs;
- one `SV_Target0.xyzw` pixel output and one-sample reads.

The same-keyword Vulkan payload has no `SubpassData` image, no multisampled
image, and no `OpImageRead`. Unity 2022 custom SRP can express this topology,
but public Unity APIs do not import the loose raw DXBC pair as a runnable
Shader asset.

## Resolver binding ABI and diagnostic boundary

The selected D3D11 pair uses `SV_VertexID` input, `SV_Position`/`TEXCOORD0`
linkage, nine constant buffers (`b0..b8`), five samplers (`s0..s4`), one
structured `t0` binning buffer, and textures `t1..t25`; it has no UAV and no
multisample load. Static/default fallbacks are source-pinned for disabled
height fog, wetness, integrated fog, CSM ramp, empty VisibilitySH, and missing
irradiance objects. Live contents remain camera/depth/GBuffer, selected
lights/bins, shadows/cookies, VisibilitySH, streamed irradiance, AO/SSR, and
the remaining per-frame constants.

The current project standalone diagnostic report
`unity_endfield_graph_shader_lab/scratch/reverse_engineering/original_dxbc_exact_diagnostic/standalone_validation.json`
is a finite Direct3D11 diagnostic (`[0,0,0,1]`) with exact shader objects
bound, render-event count 2, shader-resource mask `0x3fffffe`, constant-buffer
mask `0x1ff`, sampler mask `0x1f`, and no production-room submission. Its
current direct-runtime mode reports callback/vertex/pixel swap counters
`0/0/0`; the maintained project validator now accepts that mode and passes for
the isolated standalone scope (`ACTIVATION`, with the editor's expected
no-activation result retained). The validator was corrected in this round to
pin the current deterministic plugin hash and current GBuffer-order source
token. The older local `gacha_deferred_exact_binding_contents` checker still
encodes the previous `2/1/1` callback expectation, so that scratch checker is
not claimed as passing here. The finite result is binding-compatible smoke
evidence only, not retail numeric fidelity.

## Recovery rule

Keep the deferred resolver default-off. Do not bind the selected fallback pair
with neutral live resources, reinterpret the ordinary route as OnePassDeferred,
or treat the finite diagnostic pixel as a retail result. The next exact step
requires settled frame publication/capture for the remaining CB/SRV contents.

Primary scratch evidence:

- `scratch/reverse_engineering/gacha_deferred_resolver_chain/`;
- `scratch/reverse_engineering/gacha_deferred_framebuffer_compatibility/`;
- `scratch/reverse_engineering/gacha_deferred_fallback_program/`;
- `scratch/reverse_engineering/gacha_deferred_exact_binding_contents/`.

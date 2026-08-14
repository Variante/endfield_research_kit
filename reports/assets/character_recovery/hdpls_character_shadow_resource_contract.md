# HDPLS character-shadow resource contract

This is an offline audit of the installed fallback binaries, shader metadata,
and the current Persistent IFix table. Endfield and Unity were not launched.
The audit output was regenerated on 2026-08-14 after reconciling an obsolete
scratch-only guard that expected 30 IFix target records; the current installed
table contains 32 records. No production or Unity-lab file was changed.

Pinned installed inputs:

- `GameAssembly.dll`: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `UnityPlayer.dll`: SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `global-metadata.dat`: SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- regenerated audit: `scratch/reverse_engineering/hdpunctual_character_shadow_data/audit.json`,
  SHA-256
  `cec6c0230734798a6cec16dfaeba11e23b8aa2df03c783f0f67da1b3c5a7f3c0`

## IFix route and constant-buffer layout

The installed Persistent patch has 32 target records and matches neither
`HGHDPLSCharacterShadowManager.GetShadowParamsFromCharacter` (wrapper gate
`0x877`) nor
`ScreenSpaceShadowMaskPassConstructor.RenderHDPLSScreenSpaceShadowResolve`
(wrapper gate `0x890`). The recovered unpatched native branches therefore
describe the current on-disk route; future/network or memory-only patches stay
outside this static claim.

The reflected request is 3,568 bytes, while the native callback requests and
binds a `0xDE0` (3,552-byte) logical constant buffer. Its regions are:

| Region | Offset | Size |
| --- | ---: | ---: |
| character world-to-shadow matrices | 0 | 2,048 |
| PLS params | 2,048 | 512 |
| character indices (`uint4[56]`, consumer reads `.y`) | 2,560 | 896 |
| screen-space shadow indices | 3,456 | 16 |
| atlas texel size | 3,472 | 16 |
| screen-space light positions | 3,488 | 64 |
| global params | 3,552 | 16 |

Inactive `FrameSetup` resets all 56 character indices/channels and four
screen-space indices. Active state is `m_renderRequestCount > 0`; unused
matrix/parameter rows are persistent storage and are not silently treated as
zeroed live rows. The recorded D3D11 path rounds 222 constants to 224 before
`PSSetConstantBuffers1`, making the tail shader-visible; the CPU tail write
also remains within the 256-byte inter-allocation padding.

## Atlas and resolve publication

For active requests, `FrameSetup` creates one transient depth atlas with a
default size of 4096x2048. Request grids are 4x2 for up to eight requests and
8x4 above eight. The atlas is D16, Bilinear/Clamp, and has extent `2S x S`.
Caster passes target it, and the caster callback publishes the raw atlas as
`HGShaderIDs._HDPLSTex`.

The screen-space resolve is scheduled only while HDPLS is active. It produces
a single-sample `R8G8B8A8_UNorm` Texture2D with Bilinear/Clamp filtering. Its
render size is the camera size, reduced and clamped to at most 1920x1080 when
the reduction branch is enabled. The resolve reads scene depth, sampleable
depth, the raw `_HDPLSTex`, and `_GBufferTexture1`; material pass 2 writes four
independent HDPLS channels and publishes the result as
`HGShaderIDs._HDPLSScreenSpaceShadowMask`.

On inactive frames, both HDPLS texture globals bind `Texture2D.whiteTexture`,
and the deferred channel path falls back to the punctual-atlas result. This is
an explicit inactive contract, not permission to publish a neutral active
frame.

The unpatched bounds/light → TRS/spot-angle → reversed-Z world-to-shadow
formula, atlas rectangles/texel-size/global fields, selector formulas, and
RenderGraph dependencies are binary-closed. The exact active matrix rows,
selected channels, atlas pixels, and resolved mask pixels remain frame-derived.

## Recovery boundary

This closes the installed route, buffer ABI, atlas/resolve descriptors,
publication order, inactive fallback, and the resource lifetime boundary that
feeds HGRP/Lit character shadows. It does not close settled live bounds/light
inputs, active character rows, shadow atlas pixels, resolved screen-mask
pixels, or the original capture state. The recommended capture point is
immediately before
`CommandBuffer.SetGlobalConstantBufferInternal0` in
`HGHDPLSCharacterShadowManager+<>c.<.cctor>b__33_1`.

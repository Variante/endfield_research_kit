# Gacha light global-publication contract

This is an offline audit of the installed fallback binaries and the selected
Gacha M02 forward/deferred resource evidence. The game and Unity lab were not
launched. The deterministic audit passed on 2026-08-14:

```bat
python scratch\reverse_engineering\gacha_m02_forward_light_publishers\build_audit.py --check
```

Pinned installed inputs:

- `GameAssembly.dll`: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `UnityPlayer.dll`: SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `global-metadata.dat`: SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- source audit `gacha_m02_forward_light_publishers/audit.json`: SHA-256
  `137feead5d93e4413b9b8f00563829a22297272c8eef6309154093eac4cc69ef`

## Publication order

The installed graph establishes this order before M02 transparency draws:

1. `HGLightCookieManager.UpdateLightCookieAtlas` updates the desktop cookie
   atlas. `LightCulling.PrepareCPUData` then embeds each selected light's
   cookie index in its CPU row.
2. `LightCulling.SetupGlobalConstants` publishes `_LightDataBuffer` and
   `_LightBinningConstants`. The light data buffer is 32,864 bytes: six
   header/directional `float4` values plus 256 punctual records of eight
   `float4` values. The binning constants are 48 bytes.
3. `LightCullingGPU.PrepareGPUData` writes the light region of the
   render-graph-owned binning buffer.
4. Reflection-probe clustering writes its region into that same physical
   buffer.
5. The `Binning Pass` reads the completed buffer and publishes it as
   `_GlobalBinningBuffer` with `CommandBuffer.SetGlobalBufferInternal`.
6. `ForwardPassUtils.RenderForwardTransparent` only consumes the already
   published globals; it does not rebuild, repair, or neutralize light state.

The shared binning layout uses 32-pixel tiles, 2048 Z slices, and eight uints
per bin. This proves that M02 forward transparency and the deferred light path
reuse the same clustered result rather than maintaining separate forward light
buffers.

## Shader-resource ABI and lifetime

The selected runtime-local property slots are:

| Symbol | Binding | Size / kind |
| --- | ---: | --- |
| `_LightDataBuffer` | 14 | 32,864-byte constant buffer |
| `_LightBinningConstants` | 47 | 48-byte constant buffer |
| `_LightCookie` | 28 | texture |
| `LightCookieCB` | 49 | 2,560-byte constant buffer |
| `_GlobalBinningBuffer` | 50 | buffer |

The desktop cookie atlas is a persistent manager-owned 4096x4096 `Texture2D`.
Its active slots and 2,560-byte `LightCookieCB` (32 `Vector4` slot records,
then 32 `Matrix4x4` transforms) are rebuilt and published each frame. Constant
buffers are fresh `ScriptableRenderContext` command-stream allocations. The
global binning `ComputeBuffer` belongs to the render graph and may be recycled
after graph execution; it is rebuilt and rebound for the next frame.

The exact native publishers are hash-pinned in the source audit, including
`LightCulling.SetupGlobalConstants` at `0x189d0e188`,
`LightCullingGPU.PrepareGPUData` at `0x189d0ad84`, the Binning callback at
`0x189b9de44`, cookie atlas update at `0x189d07a74`, and the transparent
consumer at `0x189bacfcc`.

## Recovery boundary

This closes the mechanism, resource ownership, publication order, binding
slots, and per-frame lifetime connecting native light culling to HGRP/Lit
global inputs. It does not close the selected frame's final visible-light
list/order, surviving cookie-light membership, reflection data, shadow/CSM or
ASM contents, irradiance-volume data, or the original clustering compute
kernels. Replacing those with authored rows or neutral resources would not be
retail-state recovery, so the Unity lab remains fail-closed for M02.

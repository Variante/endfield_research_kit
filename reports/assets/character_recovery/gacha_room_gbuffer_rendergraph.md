# DefaultDeferred GBuffer render-graph contract

This report records the installed-game GBuffer attachment contract recovered
from the current GameAssembly/metadata pair. It is an offline binary audit;
the game was not launched.

Inputs:

- `GameAssembly.dll` SHA-256 `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `global-metadata.dat` SHA-256 `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- `GBufferPassConstructor.ConstructPass` at `0x189badf00`, body size `0x970`
- `OnePassDeferredPassConstructor` bodies at `0x189bbf010`, `0x189bbfea4`,
  `0x189bc00c4`, `0x189bc05dc`, and `0x189bc5674`

## Selected route

The installed room path is `HGRenderPathDefaultDeferred` ->
`GBufferPassConstructor.ConstructPass`. The `HGBuffer` shader pass is admitted
through renderer-list LightMode `GBuffer` in the opaque `CommonOpaque` list;
the pass runs on the graphics queue and leaves load/store selection to the
render-graph compiler (`manuallyOverride=false`).

The selected attachment order is:

1. `SceneColor`, write, no caller clear;
2. `SceneMV`, write, clear `(0.5, 0.5, 0, 0)`, format `A2B10G10R10_UNormPack32`;
3. `GBufferA` (ID 0), write, format `A2B10G10R10_UNormPack32`;
4. `GBufferB` (ID 1), write, format `A2B10G10R10_UNormPack32`;
5. `GBufferC` (ID 2), write, format `R8G8B8A8_SRGB`.

`SceneDepth` is bound as a writable depth-stencil attachment (intent
`D32_SFloat_S8_UInt`, with a supported runtime fallback possible). The
constructor consumes a pre-created `SceneColor` handle, so its physical
descriptor, allocation, aliasing, and first-use state remain unresolved.

`OnePassDeferred` independently preserves the same color order and neutral
motion-vector clear, uses read/write depth, and installs `PreDepth`, `GBuffer`,
and `Decal` subpasses. It is supporting evidence, not the selected current
room route.

## Recovery boundary

This closes the source-side five-MRT/depth contract needed by the original
`HGRP/Lit` `HGBuffer` shader. It does not authorize adding a `GBuffer` tag to
the lab's opaque list by itself: the deferred consumer and physical
`SceneColor` allocation are still required. The next unresolved rendering
inputs are the camera color descriptor/lifetime and the channel-2 custom
per-draw resource-to-descriptor upload; both remain fail-closed.

The deterministic source audit is retained under
`scratch/reverse_engineering/gacha_room_gbuffer_rendergraph/`.

# Gacha SceneColor producer and physical lifetime

This is an offline audit of the installed fallback binaries and exported
render-path evidence. The game and the Unity recovery lab were not launched.
The source audit snapshots were refreshed on 2026-08-14 after a targeted
AnimeStudio export of the current `HGRenderPipelineAsset` object; the installed
binary hashes below still match the current checkout.

Inputs:

- `GameAssembly.dll`: SHA-256
  `0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`
- `UnityPlayer.dll`: SHA-256
  `b47728ba10f09c46e8a107b4c7055e48cfe402d3d8c88a4529074981f9672aa2`
- `global-metadata.dat`: SHA-256
  `90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`
- source snapshots: `gacha_scene_color_producer_audit.json`,
  `gacha_scene_color_physical_owner_audit.json`,
  `gacha_scene_color_live_state_audit.json`, and the deferred framebuffer
  compatibility audit under the matching `scratch/reverse_engineering/`
  directories.
- current exported pipeline asset:
  `HGRenderPipelineAsset_p626CD9CED6F75568.json`, SHA-256
  `8f459ab4e65bf826376e71e8ed9d88f3a30e52960cf5590229594ce2cbd14b0b`.
- `scripts/verify_export_freshness.py` passes for both current
  `StreamingAssets` and `Persistent` roots after the targeted refresh.

## Producer and descriptor

The selected room route is `HGRenderPathDefaultDeferred`:
`HGRenderPathScene.OnPreRendering` calls
`HGRenderPipeline.GetColorBufferFormat` and
`HGRenderPipeline.CreateColorBuffer`, then stores the logical handle at
`HGRenderPathScene+0x12e0`. The selected camera has `enableAlpha=false`, so
the format is enum 74, `B10G11R11_UFloatPack32`. The descriptor is one Tex2D
slice, Point filtering, Clamp wrapping, no depth, mipmaps, UAV, or shadow-map
flag, with fast-memory flags 1/residency 1. The installed fallback fixes the
selected SceneColor to 1x MSAA with `bindTextureMS=false`.

The selected Gacha clear is `(0.025, 0.07, 0.19, 0)`. The resource is first a
transient logical render-graph texture; it is not itself a native texture
pointer.

## Physical allocation and frame lifetime

The graph compiler derives the first valid write and latest valid read/write,
then puts the resource in `CompiledPassInfo.resourceCreateList` and
`resourceReleaseList`. Pre-pass execution calls `CreatePooledResource` and
post-pass execution calls `ReleasePooledResource`. The texture pool selects an
`RTHandle` from a descriptor-hash bucket; a compatible released handle may be
reused by a later logical resource. Unused entries become purge-eligible only
when `lastUsedFrameIndex + 10 < currentFrameIndex`, i.e. after an 11-frame
gap, and are then released.

For the selected first Gacha path, SceneColor is published at `+0x12e0`, is
GBuffer/deferred RT0, and can be replaced by post-processing phases in that
same lane. `OnPostRendering` preserves the selected output into the history
lane at `HGRenderPathScene+0x1328` with one-frame flag 1. This does not prove a
cold pool, a specific physical pointer, or an alias peer: those depend on the
live compiled pass set, culling, pool warmth, frame index, and active history.

The physical extent is target-relative, not a hard-coded 1920x1080:

```text
sceneWidth  = min(actualWidth,  RoundToEven(actualWidth  * renderingScale)) & ~1
sceneHeight = min(actualHeight, RoundToEven(actualHeight * renderingScale)) & ~1
```

`actualWidth/Height` come from the persistent physical Unity Camera viewport,
unless the runtime `HGCamera.overridePixelRect` is active. The PC
`video_rendering_scale_pc` choice remains a live input even though the asset's
Unity dynamic-resolution range is disabled; the source audit exposes 100/90/80/70/60%
choices but not the persisted selection.

The separate resolver is compatible with an ordinary non-subpass deferred
pass: SceneColor is the only RTV, sceneDepth is read-only, and GBuffer A/B/C
are ordinary sampled textures. The selected fallback shader has no Vulkan
subpass input or multisample image requirement.

## Recovery boundary

This closes the SceneColor format, filter, MSAA, logical-to-physical pool
policy, publication/history lanes, and exact target-relative sizing equation.
It does not close the live camera target/viewport, persisted scale, optional
pixel-rect override, active IFix state, native pointer, or concrete alias peer.

The three deterministic SceneColor checkers now pass against the targeted
current export: producer (`PATCH_APPLIED_WITH_RUNTIME_BOUNDARY`), physical
owner (`PHYSICAL_POLICY_CLOSED_IDENTITY_LIVE`), and live state
(`MSAA_CLOSED_DIMENSIONS_TARGET_RELATIVE`). Their current audit hashes are
`99650b713e5c04d64bd1b5ba54b7749e2115cd1d2fed2f4ea73f57ad51322efa`,
`1908a43285253ba7769619e3305c4360d2c10b4ed604d3acefa9b3ffd578da24`, and
`c693f9edde09834be42ccf54aa0082651d08de43d99ef2a0caceb78421a99559`.
The remaining boundary is live frame identity: physical camera target/window,
persisted `video_rendering_scale_pc`, optional pixel-rect override, native
pointer, pool hit, and alias peer remain capture/runtime inputs rather than
being replaced with defaults.

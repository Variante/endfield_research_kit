# Character rendering and animation recovery

## Current status

The Unity lab is a useful source-backed reconstruction of Endfield character
models and Character Info presentation. It is not the original renderer and
has not reached retail visual parity.

| Layer | Current status |
| --- | --- |
| Playable model coverage | 30/30 imported and rendered |
| Canonical post-model coverage | 156/156 identities have prefab paths |
| Static playable Overview assets | high, roughly 90%+ |
| Selected CharacterNPR equations | medium-high, roughly 60–75% |
| Complete CharInfo/HGRP frame | partial, roughly 35–50% |
| Playable UI clips | complete for the selected `all-ui` scope |
| Original animation behavior | partial |
| Final retail visual parity | not reached |

The 156 canonical identities are 30 playables, 2 NPC characters, 1 cutscene
clone, 94 enemies, and 29 ability/prop actors. Six additional modular ambient
NPC archetypes are imported as labeled source kits.

## What works

- All 30 playable post-models, materials, textures, cameras, profiles, lights,
  portraits, and Overview animation sources are cataloged.
- All 30 current Overview captures are valid and nonblank.
- Playable UI recovery contains 754 body clips and 321 private item/deco clips.
- The Endfield 101-muscle ABI and exact Avatar bases are preserved.
- Narrow exact behaviors include Wulfa/Li automatic blink, one Zhuang facial
  fixture, and one Wulfa 33-frame physical-transform animation oracle.
- All non-playable post-model identities have dependency-safe static prefab
  baselines.
- Selected CharacterNPR, eye, hair, shadow, material, particle, and gacha
  presentation paths have source-backed diagnostics.
- The installed UnityPlayer fallback selector now closes the exact
  DefaultDeferred pass-0 D3D11 pair; both original stages execute once in a
  fail-closed standalone diagnostic, while live frame bindings remain open.
- Deferred binding 32 now has its exact native 48-byte
  `_LightBinningConstants` layout/upload and a default-off isolated-count
  publisher verified bit-for-bit on D3D11/D3D12. Its unique native
  `CullLights` producer, two `HGCamera.DoECSCulling` call sites, 256-candidate
  cap, pointer/count ABI, and first consumer are also closed; only an
  authorized target-frame array capture can settle retail order/`lightCount`.
- Installed `LightBinningXYCS`/`LightBinningZCS` recovery now pins all eight
  D3D11/Vulkan kernel programs plus the exact 28-byte `BinningData` ABI,
  32-pixel/2,048-slice layout, 8x8/64x1 dispatch formulas, and shared light +
  reflection word offsets. The existing Unity light producer matches those
  equations for the isolated Overview rig. A default-off raw bridge now
  publishes its exact light words plus the source-closed zero-local-reflection
  tail through canonical `_BinningBuffer`; all 90,848 words at 3840x2160 read
  back bit-exactly on D3D11/D3D12. Retail light survivors, reflection oct/global
  co-publication, and pass-0 activation remain open.
- Deferred binding 34 is the exact 11,440-byte `ShadowData` layout. The native
  `HGShadowConstantBufferUtils` transport allocates the full buffer, copies one
  of four exact same-offset sections (CSM 1,024; Punctual 6,144; Character
  2,048; ASM 2,224 bytes), then binds the full size. The selected resolver
  reads only Punctual bytes 1,024..6,415. Its enabled frame writer serializes
  all 56 matrix/params/params2 rows plus texel size before callback `b__49_2`
  publishes section enum 1 and binds the atlas. The disabled callback binds
  only a default texture and never publishes b34, so no neutral fixture is
  proven. The matching native `Punctual Shadowmap` RTHandle is now closed too:
  `4T x 4T` with no dynamic casters, otherwise
  `(ceil(N/4)+4)T x 4T`; one Depth16 Tex2D slice, Point/Clamp, shadow-map
  sampling, and no mip/UAV/MSAA. The enabled path imports and binds this
  RTHandle; the disabled path uses the exact
  `HGRenderGraphDefaultResources.defaultShadowTexture`. Constructor defaults
  are now closed as enabled, `T=512`, environment/movable caps `6/2`, cull
  distance `200`, and screen minimum `0.001`; the manager derives `N=8` and
  `3072x2048` before runtime overrides. The exact request resolves to
  `D16_UNorm` on pinned Unity 2022.3.62f3 D3D12; raw/comparison sampling,
  reversed-Z endpoints, and exact D16 quantization pass. Cache population is
  now binary-closed too: static rows 0..39 are nested 12/12/16 slots at
  `T`/`T/2`/`T/4`; dynamic caster `i` uses row `40+i` and tile
  `(4+floor(i/4), i mod 4)*T`; point/spot indices are 0..5/0. Unchanged static
  depth is reused, only one prioritized static allocation/migration redraw can
  run per frame, same-level pressure evicts the oldest visit, and dynamic rows
  redraw every frame. The installed unpatched row math is now closed: exact
  point-face bases/guarded projection or spot inverse-view feed reversed-Z
  `B*(P*V)`; PCF_3x3 stores zero depth bias, 1.5-scaled normal bias, base texel
  size, and saturated distance-faded strength; Params2 is normalized atlas
  `xyxy`, and texel size is `(1/W,1/H,W,H)`. Live IFix state, overridden target
  `N/T`, caster/light inputs, target-client resource confirmation, atlas texels,
  and settled b34 values still require one capture immediately before
  `0x189b57155`.
- Deferred binding 37 now has its exact native 2,560-byte `LightCookieData`
  initialization/upload and `cookieIndex >= 0` consumer guard closed. The
  source-closed Wulfa/Zhuangfy Overview lists have no cookies, so a default-off
  all-zero publisher is exact for that narrow path and is bit-verified on
  D3D11/D3D12 (640/640 words). Cookie-bearing or non-isolated frames fail
  closed; non-empty retail atlas history, pixels, transforms, and settled
  whole-scene values still require capture.
- Deferred binding 38 now has its native `HGHDPLSCharacterShadowManager`
  owner, per-frame reset, 3,568-byte reflected layout, push-pass packing, and
  selected `.y`-only consumer closed. Inactive frames clear all 56 HDPLS
  channel selectors, proving the selected resolver falls back to the punctual
  atlas. Do not publish a full zero fixture: matrices/params persist, trailing
  values are frame-derived, and the native callback logically binds 3,552
  bytes while writing the reflected final float4 at byte 3,552. Installed
  `UnityPlayer` recovery closes `CBHandle.size=3,552`, 16-byte length rounding,
  and 256-byte allocation-start alignment: the next allocation begins at byte
  3,584, so the final CPU write is safe in padding. The recorded target forces
  D3D11; its backend rounds 222 constants to 224 before
  `PSSetConstantBuffers1`, exposing 3,584 bytes and proving c222 GPU-visible.
  Native getter/constructor recovery also closes the six HDPLS setting offsets
  and current defaults: enabled, atlas height 2,048, reduced screen-space
  resolution enabled, and zero depth bias/normal bias/softness. With
  `S=max(256, atlasHeight)`, the atlas is `2S x S`; requests use a `4x2` grid
  through eight entries or `8x4` above eight at the default. Normalized tile
  rectangles, `(1/(2S),1/S,2S,S)` texel size, `(softness,0,0,0)` global params,
  `float4(worldPosition,0)` screen-space positions, and both selector writes are
  exact. The installed unpatched character-matrix path is also closed:
  `Bounds.extents` supplies a bounding-sphere radius, the light aims at the
  bounds center with a `1e-5` degenerate-direction fallback, the cone is
  `clamp(2*asin(radius/distance),0.1°,179.9°)`, and the derived TRS plus
  light near/far/guard feeds the exact reversed-Z spot-shadow transform. Depth
  and normal bias also reach the caster pass exactly. Resource recovery now
  distinguishes the request-gated `2S x S` D16 `_HDPLSTex` caster atlas from
  the reduced/full-size RGBA8 `_HDPLSScreenSpaceShadowMask` consumed by
  deferred binding 22. Their RenderGraph dependencies and global publication
  are closed; inactive frames clear all selectors and bind white to both slots,
  so stale resources cannot escape. The hash-pinned installed Persistent IFix
  table has 30 targets and replaces neither `0x877` nor `0x890` owner method,
  closing the current on-disk branch choice; future/network patches remain a
  version boundary. Live input values, active rows/selectors, unused persistent
  rows, atlas texels, and resolved RGBA pixels remain capture-only.

- The installed no-reload CharInfo V2 irradiance route is now closed as
  inactive. `SetMap` enters native clear state 4, releases all six full-size
  clipmaps, then an empty or unresolved path settles in state 2. The result
  publishes one shared 1x1x1 Unity default 3D zero texture to all six slots and
  default parameters `0/0/0/(0,1/3,0,0)`; it does not retain zero-filled
  128x64 clipmaps. `/aiTest/index.bytes` is absent from all 224 shipped IV
  files. `ReloadIndexFileV2` and `StreamingInNewMapV2` each have only their
  IL2CPP method-table pointer, with no direct managed, Lua, or installed IFix
  owner. Generic reflection/external reload remains a boundary; if observed,
  its caller path, populated atlas dimensions, parameters, and texels must be
  recovered separately.

## Main rendering gap

The largest missing piece is the coupled retail frame contract:

- HGRP light scheduling, culling, cookies, and irradiance;
- character shadow atlases, screen shadows, stencil, and VisibilitySH;
- shared depth, GBuffer, motion, and deferred `SphereOutside` resolve;
- exact material variants, native mip payloads, and live per-renderer state;
- exposure, history, post-processing, and final composition;
- retail-frame validation across all characters.

Current images are recognizable but remain flatter than retail, especially on
faces, pale cloth/armor, hair, dark hardware, and contact/ground shadows.

## Main animation gap

Recovered clips are not equivalent to the complete runtime. Remaining work:

- controller transitions, interruption, blending, and root motion;
- broader exact Avatar/clip transport;
- grounding, foot IK, hand targets, and constraints;
- live facial emotion, lip sync, eye direction, look-at, and events;
- secondary motion, wind, cloth, hair, and dynamic bones;
- item/deco/FX lifecycle and gacha timing;
- non-playable controller, rig, animation, and VFX execution.

Do not enable generic Humanoid animation for enemies or props without
actor-specific source evidence.

## Non-playable limitations

The 94 enemy, 29 ability/prop, and six ambient-NPC baselines prove enumeration,
hierarchy, and admitted geometry dependencies—not authored appearance.
Runtime VFX, modular assembly, exact keywords/passes/queues, texture
descriptors, animation, and material overrides remain incomplete.

## Maintained workflows

```bat
cd unity_endfield_graph_shader_lab

.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat

.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat

.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
.\verify_recovered_light_binning_constants.bat --all
.\verify_recovered_light_cookie_data.bat --all
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated character assets are rebuildable. Fix generators, importers,
runtime code, or shaders rather than hand-editing generated prefabs.

## Highest-value next work

1. Complete the minimum binding-compatible deferred CharInfo frame.
2. Recover the retail light-cull survivor list, then populate exact shadow,
   depth, GBuffer, irradiance, non-empty cookie, and VisibilitySH inputs.
3. Validate selected paths against accepted retail captures.
4. Extend exact texture/mip and material-variant support only where visible.
5. Generalize animation from a second exact Avatar/clip oracle.
6. Implement controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
7. Upgrade representative non-playable families before making broad parity
   claims.

Every production value must come from serialized data, native behavior, or a
valid runtime capture. Unknown values stay neutral, diagnostic, or disabled.

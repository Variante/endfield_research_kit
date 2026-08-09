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
- A default-off SphereOutside sidecar now uses the source CharInfo camera and
  transform to produce the exact logical 640x720 SceneColor/SceneMV/GBuffer
  A/B/C formats plus D32S8. All five readbacks are bit-identical on D3D11 and
  D3D12, the presented frame is unchanged, and missing binning/reflection/b33
  prerequisites fail closed. It is deliberately non-presented: canonical
  render-graph lifetime and pass 0 remain open. The current installed
  `RenderWithAlpha=false` route submits no WriteAlpha draw.
- Deferred binding 32 now has its exact native 48-byte
  `_LightBinningConstants` layout/upload and a default-off isolated-count
  publisher verified bit-for-bit on D3D11/D3D12. Its unique native
  `CullLights` producer, two `HGCamera.DoECSCulling` call sites, 256-candidate
  cap, pointer/count ABI, and first consumer are also closed. Installed
  InitBundle settings now close the Windows desktop
  `PunctualLightMaxCount=256`; `SetupState` keeps types 0/2, sorts priority
  descending then squared camera distance ascending, and takes
  `min(survivors, cap)`. Because the upstream cap is also 256, settings cannot
  truncate the list again. Installed Gacha Lua plus decoded Zhuangfy and room
  prefabs now close the known authored input as 6 `light_overview` lights + 12
  `SceneLight6Rarity` lights: 3 type 0, 15 type 2, zero authored cookies, one
  shadow request, and four bone followers. The shipped Gacha cull route uses
  the normal core with fallback and occlusion disabled. Matching read-only
  Unity/game settings select `3840x2160`; at that 16:9 aspect, native AABB,
  authored OBB, point-sphere, and spot-cone tests admit exactly 11 room lights
  and reject only `Spot Light (20)`. Installed layer data fixes recursive
  Gacha assignment at layer 30. Identity prefab/Timeline placement, native
  follower equations, and the original entrance/loop ACL streams close all six
  character lights: their constant root motion removes to identity, no muscle
  lanes are mapped, and every light passes across all 844 decoded QVV frames.
  The exact known authored contribution is therefore 17, with its internal
  priority/distance order closed. Other display aspects, runtime/custom
  carry-in, the target-frame pointer/count, whole-list order, and final retail
  `lightCount` remain open. The maintained cap audit now directly pins both
  `DoECSCulling` call sites through the UnityPlayer candidate core: its native
  gates, hidden-sret handoff, 16-byte `LightCullResult`, and 148-byte
  `VisibleLight` capture stride are source-closed. An authorized target-frame
  capture therefore has an exact pointer/count/row decoding contract, but no
  live values are inferred offline.
- Installed `LightBinningXYCS`/`LightBinningZCS` recovery now pins all eight
  D3D11/Vulkan kernel programs plus the exact 28-byte `BinningData` ABI,
  32-pixel/2,048-slice layout, 8x8/64x1 dispatch formulas, and shared light +
  reflection word offsets. The existing Unity light producer matches those
  equations for the isolated Overview rig. A default-off raw bridge now
  publishes its exact light words plus the source-closed zero-local-reflection
  tail through canonical `_BinningBuffer`; all 90,848 words at 3840x2160 read
  back bit-exactly on D3D11/D3D12. Under the same default-off selector, the
  pipeline now co-publishes the exact `T_hdri_env_char_01` reflection oct/global
  resources in the same camera command stream without overwriting that buffer;
  the full 260-vector `ReflectionProbeGlobalData` and original D3D11
  `EndfieldCB2` 259-vector prefix now read back bit-exactly on both APIs, while
  both readiness gates, the 576x576x32 texture, and source rejection also pass.
  The native 128-byte `VisibilitySHConstData` b33 layout,
  fixed rows and frame dimensions/scales are now source-closed. The producer's
  pinned 128-byte zero-fill proves untouched rows 5..7 are exact zero, so all
  32 words—not only the selected consumer's bytes 32..63—read back bit-exactly
  on D3D11/D3D12 under that same frame gate. The source-backed Wulfa capsule
  pass now publishes its canonical `_VisibilitySHRT` only when that gate is
  ready: D3D11/D3D12 produce the same 320x360 RGBAHalf hash with 20,006
  nonzero pixels, while an upstream-off run keeps canonical publication closed.
  A retail settled-frame capture, exact retail posed/view-culled records,
  target-frame light survivors, and the pass-0 consumer remain open.
- The selected original pass-0 `_TransformVariables` b30 reads are now
  source-closed for view, inverse-view, inverse GPU view-projection, and camera
  position. The default-off same-frame publisher reads all 1,312 bytes back
  identically on D3D11/D3D12; its 13 selected vectors match and the other 69
  history/jitter/stereo rows remain zero. Pass 0 is still disabled.
- The selected original pass-0 `_LightDataBuffer` b31 consumer is now closed
  for the isolated Wulfa/Zhuangfy CharInfo fixture. Native allocation/packing
  proves `6 + 256*8` float4 (32,864 bytes), not the earlier assumed `128*16`:
  the directional header comes from the exact CharInfo environment, while each
  CharacterOnly row reads zero OBB flags then exits before general punctual or
  shadow words. All 8,216 words match through `_LightDataBuffer` and the D3D11
  `EndfieldCB4` bridge on both APIs; unknown words remain zero, same-frame
  activation is fail-closed, beauty is unchanged, and pass 0 remains disabled.
  The installed `PrepareCPUData` body now also closes the complete eight-float4
  write schema for both Spot and Point/linear-extension rows. The exact
  selected-aspect Gacha room contribution is one Spot, six ordinary Point,
  and four positive-length linear-extension Point lights; all eleven enable
  authored OBB culling and are unshadowed/cookie-free. Each has an exact
  serialized `HGAdditionalLightData` component rather than an unresolved
  default. Installed `GetLightNPRData`/`GetLightAdditionalData` close the
  32-byte return layout and b31 record3.yzw, record4, and record6.w: every row
  uses NPR type 0 with `(1,1,0,0)`, `CharacterOnly=false`, and falloff `-1`;
  volumetric intensity is 0/1/10 on 2/5/4 rows. The same body now closes the
  OBB chain as inverse TRS of authored relative position, ZXY orientation, and
  half extents, packed row-major into six half2 words at record5.xyz/6.xyz.
  Installed `HGUtils.PackTwoHalfValuesAsFloat` and
  `Unity.Mathematics.math.f32tof16` close the word order and IEEE conversion;
  all 11 analytic candidates map authored corners back to the unit box within
  `0.002611`. Exact signed-zero bits and one `Spot Light (12)` reciprocal at a
  one-float32-ULP half boundary still need the exact UnityPlayer matrix-inverse
  output or a retail buffer capture. Pinned `globalgamemanagers` objects prove
  Linear color space and linear light intensity; all 11 rows disable color
  temperature, distance/far-show falloff, animation, multistate, and flicker.
  UnityPlayer `finalColor`, `Color.linear`, animation-disable, and flicker
  bodies therefore close exact b31 record0.xyz bits as linearized authored RGB
  times intensity, with falloff/flicker both 1. The two `PrepareCPUData`
  branches close record0.w as `float(lightKind + 2*shadowOnly)`: the one Spot
  row is exactly 0 and all ten Point/linear-extension rows are exactly 1.
  Record0 is therefore fully closed. The metadata-backed
  `VisibleLight.get_range` field at `+0x68` and the native scalar divide close
  record1.w for all 11 rows. Hash-pinned half-angle scaling and the original
  scalar-cosine body close record2.z plus the Spot row's record2.w; the Point
  branch closes record2.z as `HGSharedLightData.length` (`-1` on six ordinary
  Points, `18` on four linear extensions). Target-frame record1.xyz/record2.xy,
  Point record2.w shadow-face packing, runtime carry-in, and final byte-exact
  b31 rows remain open.
- Deferred binding 34 is the exact 11,440-byte `ShadowData`; the selected
  resolver reads only its Punctual rows `c64..c400` (bytes 1,024..6,415).
  Native allocation, four-section copy/bind transport, atlas sizing/format,
  cache scheduling, point/spot matrix math, PCF_3x3 bias, strength fade,
  normalized rects, and texel size remain binary-source-closed. A default-off
  same-frame publisher now closes the isolated CharInfo punctual subset:
  Wulfa row 4 produces spot slot 40 and Zhuangfy row 4 produces point slots
  40..45, each with the matching `6144x4096` D16 atlas. The full 715 vectors
  and D3D11 `EndfieldCB5` 401-vector prefix read back bit-exactly on both APIs;
  all unowned sections stay zero, missing prerequisites fail closed, and Wulfa
  active/control beauty is identical. Every isolated light is `CharacterOnly`,
  so the selected pass-0 consumer exits before its first b34 or atlas read;
  pass 0 remains disabled. General-scene/static-cache rows, retail physical
  resource identity and settled atlas pixels, runtime IFix/setting overrides,
  and the non-punctual sections remain open.
- `ShaderVariablesGlobal` b35 is no longer an undifferentiated 3,200-byte gap.
  A hash-pinned selected-body audit finds 33 referenced fields and closes exact
  installed reset output for atmosphere c71..c76, height fog c77..c82, and
  disabled volumetric fog c83..c87. Current constructors, `IsActive`/camera
  getters, and all selected/global/LookDev VolumeProfiles close c30 as
  `(0,0,1,1)`; the code default and every shipped setting override close
  c31.x as `reflectionProbeMaxSampleMip=7`. Native `HGCamera.UpdateFrustum`
  constructs c3 as `(-1, near, far, 1/far)` and the selected serialized
  Zhuangfy Overview lens is exactly near=0.1/far=50, closing live c3.y as 0.1.
  The selected route also closes perspective c4.w, mip bias c26.x,
  binning/environment rows c28/c29, inactive IV params c132..c134, and wetness
  c156.x; frame count is behind the exact-zero volumetric gate. The enabled
  weight-1 CharInfo environment volume selects `CharInfo_Env`; native
  `UpdateShaderVariablesIrradianceVolume` and `GetCoefficientsL1` prove that
  c135..c137 each equal the serialized ambient-SH reorder
  `(SH3,SH1,SH2,SH0) * skyDirectIntensity`, or exactly
  `(-0.0075507611,0.4722373188,0.0121708093,1.0963056087)`. All selected b35
  value producers are source-closed. A default-off publisher now binds all 200
  canonical vectors plus the 157-vector `EndfieldCB1` prefix. D3D11/D3D12
  read back 800/800 and 628/628 words exactly; all unselected rows stay zero,
  c28 keeps its raw integer bit pattern, same-frame Wulfa activation succeeds,
  and missing canonical prerequisites fail closed without changing D3D12
  beauty. Pass 0 remains disabled.
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
.\verify_recovered_shader_variables_global.bat --all
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated character assets are rebuildable. Fix generators, importers,
runtime code, or shaders rather than hand-editing generated prefabs.

## Highest-value next work

1. Recover the retail survivor list at the exact `HGCamera.DoECSCulling` return
   boundary, starting from the source-closed 18-row authored input and exact
   selected-aspect 17-row authored result while preserving runtime/custom
   carry-in and other display aspects; populate exact shadow, depth, GBuffer,
   irradiance, non-empty cookie, and VisibilitySH inputs afterward.
2. Validate selected paths against accepted retail captures.
3. Extend exact texture/mip and material-variant support only where visible.
4. Generalize animation from a second exact Avatar/clip oracle.
5. Implement controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
6. Upgrade representative non-playable families before making broad parity
   claims.

Every production value must come from serialized data, native behavior, or a
valid runtime capture. Unknown values stay neutral, diagnostic, or disabled.

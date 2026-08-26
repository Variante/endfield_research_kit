# Character rendering and animation recovery

## Current status

The Unity lab is now focused on reproducing the original Character Info render.
Endminf is the sole active reference actor; after that render is faithful, the
same character-neutral pipeline will be used to rebuild every playable
character.

| Layer | Current status |
| --- | --- |
| Playable models | 31/31 imported and rendered |
| Canonical post-model identities | 156/156 have generated prefab paths |
| Static playable Overview assets | strong |
| Selected CharacterNPR equations | partial but source-backed |
| Complete HGRP/CharInfo frame | partial |
| Playable UI clips | complete for the selected `all-ui` scope |
| Runtime animation behavior | Endminf start/loop handoff source-backed; broader systems partial |
| Retail visual parity | not reached |

The canonical identities comprise 31 playables, one NPC character, one
cutscene clone, 94 enemies, and 29 ability/prop actors. Six modular ambient-NPC
archetypes remain labeled source kits rather than finished characters.

Staged capture-only 3DMigoto is the independently valid retail-tested path for
graphics evidence. Capture sessions belong under the relevant scratch recovery
topic, and evidence requires the captured provider request and session summary.

Secondary-dynamics session `20260825T125815Z` closed the global live
`UseCrossFrameJob=true` value across 700 `ClothUpdate` calls and observed 2,772
false `TeamData.useRelativeTransform` getter reads. It remains uncertified for
Endminf: 93 rotating TeamData addresses were observed and the capture records
`endminfFourOwnerCertification=false`, so none can be attributed to the four
Endminf owners. Preserve the settings as scheduler telemetry, but do not use
them to admit target writeback without an owner-identity join.

Native D3D11 COM hooks must use the exact Windows SDK vtable order. Shader
creation occupies `ID3D11Device` slots 12-18 (with stream-output geometry at
14); slots 20-26 are state/query methods with incompatible ABIs. The native
wrapper now keeps those methods untouched in its lifecycle regression test,
but remains uncertified until a new retail session captures and collects one
complete frame without a client fault.

## Stable conclusions

- Playable post-models, LOD0 mesh bindings, materials, textures, cameras,
  profiles, lights, portraits, and selected Overview animation sources are
  recovered.
- The Unity lab's authoritative Windows backend is Direct3D11, matching the
  recovered retail shader binaries. Project settings disable automatic API
  selection and normal Editor, batch, import, sweep, capture, and standalone
  workflows explicitly request D3D11. Historical D3D12 probes remain labeled
  evidence snapshots rather than active defaults. A full 41-frame D3D11
  Endminf capture passes the transition, settled-loop, entrance cleanup,
  rotation-only root-motion, 68-renderer admission, and exact two-row
  fail-closed gates, and regenerates both maintained reference comparisons.
- Every canonical non-playable post-model identity has a dependency-safe
  static prefab baseline. These prove identity and admitted dependencies, not
  full runtime assembly or behavior.
- The selected playable UI body and private item/deco clip scope is recovered.
  The Endfield 101-muscle Avatar contract and selected exact clip paths are
  source-backed.
- Endminf now executes `ui_overview_start -> ui_overview_loop` through a
  generated Animator controller rather than the former Legacy
  `Animation.CrossFade` approximation. The controller preserves the recovered
  `FromIndex=0`, `ToIndex=0`, `EnableSwitch` entry route, 0.75 exit time, 0.25
  normalized transition duration, destination offset, Write Defaults, and
  interruption ordering. A Viewer capture of 41 saved frames proves controller
  entry, the transition, settled looping, four entrance-effect roots, and
  effect cleanup. Those frames are sampled at 4 fps from a 60 Hz
  simulation; they are not a 41-frame 60 fps movie. Its AnimatorMove path now
  follows the pinned native consumer:
  it multiplies the actor rotation by `animator.deltaRotation` and never reads
  or applies `deltaPosition`. The capture observed 599 callbacks, zero root
  position drift, and no authored rotation delta in these two clips. Stock
  Unity 2022.3 still does not serialize the retail per-transition
  `m_EnableBlendRootMotion` field; that flag remains retained evidence for the
  transition/callback path rather than permission to apply translation.
- Five neutral 3DMigoto analyses now retain full presented retail frames across
  the settled loop, early turn, raised-arm turn, hand-rock presentation, and
  peak burst. Their final JPGs join exactly to no-framegen extracted frames
  407, 50, 103, 150, and 269 from `videos/2026-08-24_06-37-22.mkv`. A focused
  60 Hz Unity window matches the early
  turn's retail start-clip phase `0.8509083` with Unity `0.850907922`; head,
  arms, torso, and rigid accessories align closely while the lower-body
  silhouette and loose coat panels/cords remain different. Endminf's four
  enabled `BeyondDynamicBone.BeyondBoneCloth` components are source-recovered
  at full simulation weight; `MC_Coat` owns the five cape roots, while the body
  clip animates those same chains as its animation-pose input. The ordinary
  Grounder path has no exact Endminf overview `FootIKWeight` curve and remains
  effectively disabled. The main residual owner is therefore the missing
  retail bone-cloth solve/history, not general clip timing, clip import,
  terrain IK, or a global camera correction. The generated Endminf overview
  start and loop now retain all decoded 60 Hz keys: removing the former
  stride-two preview reduces the retail-to-Unity early-turn affine correction
  from 2.29 degrees/1.22 percent scale to 1.20 degrees/0.09 percent without
  eliminating the cloth silhouette gap. Rock cadence and peak burst timing are
  also substantially aligned, while temporal VFX shape remains open. Captured
  Forward vertex streams are undeformed and duplicated; retail skinning lives
  in structured SRV `vs-t0`. Decompiled CharacterNPR Skin PreGBuffer vertex
  code closes its layout: each bone is three `float4` rows, while b2
  instance-word-5 x/y select current/previous palettes. EndfieldCapture session
  `20260825T191720Z` now joins those values at draw time for 40 complete frames
  of body, cloth-01, cloth-04, and hair. Reconstructing root-space bone matrices
  through the generated Unity bind poses produces 800 cross-renderer shared-bone
  comparisons with a worst delta below `5.7e-8`; the worst orthonormality error
  is below `2.2e-5`. The owner-tagged trajectories and changing coverage live in
  `reports/assets/character_recovery/endminf_captured_secondary_dynamics_oracle.json`.
  Decoding all 40 captured 4K backbuffers closes their sequence-time join to
  the no-frame-generation reference: presented frame 1887 maps to source frame
  117 within one frame, and every later checkpoint preserves the presented-frame
  delta through source frame 791. This makes the oracle suitable for direct
  Unity-vs-retail hair/cape trajectory comparisons without guessing a phase.
  A synchronized Unity capture at `(presentedFrame - 1884) / 60` now compares
  all 74 retail-rendered owner bones at those 40 checkpoints. The entrance is
  the material gap: frame means reach 0.133 m and 29.7 degrees, with individual
  maxima of 0.289 m and 96.6 degrees. From settled-loop checkpoint 20 onward,
  means remain 1.5-2.3 mm and 0.86-1.07 degrees. The generated comparison is
  `reports/assets/character_recovery/endminf_secondary_dynamics_trajectory_comparison.json`.
  This closes the retail hair/cape shape oracle for the captured sequence, but
  does not by itself certify the recovered solver. The generated Endminf actor
  now uses that oracle directly through a bounded replay owner: 40 samples and
  74 unique hair/cape bones are interpolated in root space after Animator
  evaluation, reset on each Overview playback generation, and clamped outside
  the captured 0-11.233-second span. It fails closed on stale data, missing
  bones, or simultaneous experimental-solver writeback. This removes guessed
  entrance solver history from the canonical captured sequence while remaining
  explicit replay evidence rather than a general BeyondBoneCloth solve.
  Deterministic Unity capture
  also hash-binds the owner contract and verifies Endminf's 4 cloth owners, 18
  root references, and 10 collider owners against the instantiated prefab.
  The refreshed three-actor static solver-input contract now maps all 333
  non-null authored proxy-transform PPtrs to current hierarchy paths while
  preserving transform-array indices (Endminf: 7/31/21/71); this closes the
  source binding only and does not identify those transforms as write targets.
- Endminf's overview rock/crystal animation now combines the exact retained
  transform clip with four source-resolved `GameObject.m_IsActive` curves.
  They remain active through 1.5 seconds and deactivate on the source boundary.
  The fifth constant-zero binding has no resolved hierarchy target and remains
  fail-closed rather than being fabricated.
- The canonical capture now restores eleven retained LitEffect rock/crystal
  renderers: seven M01 rows, three M38 rows, and the later M27 hand-crystal row,
  all keyed by exact renderer/material PathIDs and the exact
  `S_rock_small_1_017_02_lod2` mesh. Direct references are validated against
  pinned asset hashes, the default remains disabled/fail-closed, and only
  `ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1` activates them. Capture schema
  v4 proves 68 admitted entrance renderers and exactly two separately blocked
  non-LitEffect rows. Frames 19-22 now contain M27's dark/amber faceted debris;
  its default-off Unity ABI probe still proves an empty material/mesh binding.
  A same-seed M27-excluded differential isolates only that small late fragment
  cohort; it does not own the much larger raised-hand ring/bloom burst.
  This remains a non-exact forward LitEffect compatibility layer. A separate
  M27-only five-MRT source port now publishes the captured attachment formats
  in a private D3D11 sidecar; it does not make the compatibility layer exact or
  present deferred output. No crystal retiming, scale change, or bloom tuning
  was admitted.
- The no-frame-generation reference makes two stone systems distinguishable:
  the ten LitEffect M01/M38 rows are the early fly-in faceted rocks, while the
  later raised-hand glow/particles are separate BaseV2 renderers and must not
  be calibrated as one material. A refreshed, hash-pinned LitEffect export now
  recovers the selected HGBuffer fragment's 576-byte `UnityPerMaterial` table
  and exact offsets for all 17 parallax fields used through the 496-byte b3
  prefix (including `_ParallaxColor` at byte 464 and its dark color at 480).
  This closes the selected physical b3 slice, not visual admission. Selected-
  frame b1 VFX globals, b2 per-draw history/LOD state, the selected b4 value,
  `ParserBindChannels`, and complete HGBuffer frame publication remain
  fail-closed. The raw retail peak frame itself contains the large M13 orange
  ring, so it is not evidence for shrinking or dimming that authored row.
- A renderer-isolation audit distinguishes the earlier broad glow
  `overview_04/1/guangyun (3)` with `M_fx_endminm_gfx_30` from the actual
  ten-piece crystal burst,
  `overview_02/all/shitou (1)` with `M_fx_endminm_gfx_21`. The crystal row is
  an exact mesh-particle binding with the serialized 4.45-second delay and the
  hash-pinned `_USE_FRESNEL` BaseV2 variant; it must not be resized, brightened,
  or retimed to compensate for the glow. At the strongest saved raised-hand
  frame M30 is already dead; isolating the live `overview_02` companions with
  M21 disabled still produces the large amber ring/globe, while isolated M21
  produces only the small stone burst. The large volume therefore belongs to
  the surrounding ring/glow/particle family and its composition, not to the
  crystal mesh. Explicit batch selector values of
  zero and one produced byte-identical focused frames because the active Viewer
  presentation republishes its scene-owned recovered-post selector; that run is
  not evidence for a post bypass or a material correction. The selected BaseV2
  fragment already premultiplies RGB by recovered coverage before the authored
  `One / OneMinusSrcAlpha` blend, so a second alpha multiplication is also not
  admissible. A deterministic Viewer-path readback now captures the canonical
  packed `B10G11R11_UFloatPack32` CameraColor immediately before bloom/Uber.
  Two independent full runs at saved frame 18 (4.4667 seconds) are
  byte-identical. Excluding only M21 removes exactly one live renderer and its
  ten particles; every companion row remains identical, and the crystal
  changes only 90 of 2,073,600 pre-post pixels. By contrast, excluding the
  unique `overview_02/all/huan` M13 row changes 352,660 pixels and removes the
  large outer amber ring. This closes the attribution boundary without
  changing any authored material: M21 owns the small stones, while M13 and the
  other `overview_02` companions own the surrounding burst and its
  compositing footprint. The combined burst remains clipped relative to the
  no-frame-generation reference, so the open boundary is complete
  presentation/compositing admission, not either authored particle system or
  material.
- The original `HGRP/PostProcessing/UberPost` serialized Shader now has an
  exact public-loader transport experiment. Its containing Endfield VFS node
  can be unpacked and wrapped in a standard uncompressed UnityFS container
  without changing the CAB bytes; AnimeStudio re-exports the Shader from that
  wrapper byte-identically. Public Unity loads the AssetBundle, asset names,
  Shader name, and pass table, but marks the Shader unsupported on both D3D11
  and D3D12 in the 2022.3.62f3 lab. An isolated 2021.3.34f1 D3D11 project also
  loads it but marks its sole post pass unsupported; the source CAB records
  2021.3.34f5 and the retail HyperGryph engine fork. Therefore exact serialized
  transport is closed, while executable Shader ABI admission remains
  fail-closed. Do not replace the compatibility post path or use this result to
  tune the separately authored crystal material.
- The focused Endminf comparison now anchors its first saved Unity frame
  directly to retail frame 1110, the first visible body frame. The former map
  added the already-advanced 0.0509083-second body phase a second time and put
  every retail sample three frames late. The canonical D3D11 capture maps frames
  1110 through 1512 with less than 0.000046 source-frame residue; the corrected
  central comparison improves 24 of 28 pairs over the old three-frame-late map.
- The reference recording enters Endminf through a same-page Wolfgd character
  replacement, so the authored `weapon_overview` dolly is correctly excluded.
  Its visible lower-right pointer selects the otherwise external gyroscope
  endpoint. The live Viewer now runs the exact serialized-entry-to-input,
  two-second OutQuad camera correction on selection; the UI-free 28-frame RGB
  MAE falls from 27.6752 to 24.0733, with frame 1 falling from 56.156 to 30.986.
  This endpoint remains explicitly recording-specific rather than a roster
  default. The admitted `CharInfo_Volume` contains no `HGMotionBlur`; an exact
  `MotionBlurCS` asset is recovered for future scenes, but enabling it here
  would import an unrelated profile. Skin, hair, eye, and cloth now publish the
  recovered CharacterNPR SceneMV encoding. The camera preserves the recorded
  blank model-swap frame as temporal history before Endminf becomes visible,
  avoiding first-frame self-seeding. The ordinary Quality-0 TAA schedule and
  shader bindings are now closed as Dilation -> MaskDilation -> Resolve, with
  scene-color, dilated-depth, and dilated-SceneMV histories. The compatibility
  path now persists the auxiliary depth/SceneMV histories and implements
  Dilation's recovered 3x3 maximum-depth winner scan, previous-non-jittered-VP
  reprojection, and exact B/Z-lane flag repacking. Exact MaskDilation also
  generates its R8 current-frame resource from packed B/Z at the center plus
  four diagonals. The no-keyword Quality-0 resolve math is now decoded through
  its packed bit-1 Gaussian selector, direct-history bound, topology/confidence
  rejection, adaptive weights, and confidence-alpha history. It is available
  only through `ENDFIELD_RECOVERED_TAAU_PACKED_RESOLVE=1`: with zero jitter,
  frame-info Y one, default-zero convergence/responsive lanes, and the
  deterministic alpha-one seed, the 28-frame ROI MAE regresses from 22.3101 to
  58.2411. A fresh gate-off capture returns to 22.3101. Keep the canonical
  raw-lane partial consumer until live jitter/frame state, first-allocation
  history alpha, IFix selection, and capture-time upscaler admission close.
  Retail confidence alpha must remain internal history metadata; the lab's
  later Uber treats source alpha as opacity, so the experiment presents RGB
  through a separate opaque-alpha copy.
- Upscaler admission for the August 21 reference remains deliberately
  fail-closed. The dated July 14 saved profile and the post-capture August 24
  read both request DLSS/DLAA, so it is the strongest comparison target, but
  neither brackets the recording with live telemetry and runtime fallback is
  unobserved. The current saved request additionally selects DLSS frame
  generation X3; the older `render_parameter_provenance.json` off/Auto result
  is explicitly a July snapshot, not current state. A disposable Unity 2022
  NVIDIA-module probe successfully created a valid 1920x1080-to-1920x1080 DLSS
  feature through the installed game's application directory and NGX binary.
  That proves a native-scale lab experiment is feasible, not that Unity's
  public wrapper reproduces Endfield's custom Streamline schedule, DLAA model,
  input conventions, executed output, or frame generation. Do not wire it into
  the canonical beauty path until those contracts are recovered and an
  opt-in comparison improves the reference sequence.
- The pinned client now closes most of that custom Streamline contract. Its
  order is velocity combine, current-frame constants/resource tags, then DLSS
  evaluate; HG quality 4 maps exactly to Streamline DLAA mode 6. The five DLSS
  resources are HDR input color, output color, reverse-Z depth, a newly built
  full-resolution combined motion texture, and optional exposure. Motion is
  tagged as normalized with scale `(1,1)`, includes camera motion, is neither
  jittered nor dilated, and Streamline receives the rendered camera jitter
  with both signs negated. Pre-exposure/exposure scale are one, sharpness is
  zero, and no reactive or transparency-composition masks enter DLSS. The
  exact velocity kernel only fourth-root decodes packed SceneMV XY into
  normalized UV-fraction motion; depth and camera matrices do not enter that
  kernel. Packed SceneMV is exactly `A2B10G10R10_UNormPack32`; the native
  `0x2d` descriptor is instead `R16_SFloat` dilated depth and supplies no
  evidence for combined velocity. Four full retail D3D11 FrameAnalysis captures
  independently close the transient output as full-native-resolution
  `R16G16_FLOAT` with SRV, RTV, and UAV bindings: the 3840x2160 packed input is
  decoded by a 480x270 dispatch of the 8x8 kernel. Unity now publishes the same
  temporary `R16G16_SFloat` `_CombinedVelocity` producer without enabling a
  DLSS/DLAA consumer or changing beauty. Direct attachment of every retail
  non-character motion producer remains open. The same-frame reset is exactly large de-jittered camera
  movement or `isFirstFrame`, after which `isFirstFrame` is cleared; size and
  AA-mode changes are not independent compiled terms. DLAA scale is delegated
  to Streamline optimal-settings mode 6 rather than forced to one by HG. The
  installed default callback maps mode 6 to NGX quality index 5 and its 1.0
  scale, proving equal input/output extents for that path; explicit profile
  overrides and live feature availability remain outside the static proof.
  Until the remaining motion boundary closes, do not map
  the game contract onto Unity's public NVIDIA wrapper by convention.
  That wrapper can carry the recovered numeric resource subset, including
  negated pixel jitter, reverse depth, reset, exposure, and combined motion at
  scale `(1,1)`, but it cannot select Streamline DLAA mode 6, model presets, or
  the game's constants/tag schedule. Any future experiment must be labeled
  `UnityPublicNgxProxy`, stay opt-in, and never count as parity evidence.
- Effect-02's animated radial/chromatic values, exact 1.0 radial power, native
  mode/effective-power packing, signed/clamped post-projection center transform,
  source-only warped taps, and separate bloom sampling order are source-backed.
  The exact combined Uber variant now also closes the CharInfo merge: source-only
  global exposure, channel-wise bloom decoding above 0.3, serialized intensity,
  white normalized tint, zero blend mode, and saturated source alpha. The D3D12
  compatibility implementation reduced the UI-free 28-frame RGB MAE from
  27.6888 to 27.6752. The supplied recording's Wolfgd-to-Endminf route starts
  this post owner nine 60 Hz frames before the first visible Endminf body frame;
  applying that explicit 0.15-second recording pre-roll removes the two
  incorrectly shifted chromatic pulses and, together with the recovered
  gyroscope transition, lowers the same MAE to 22.3254. That age belongs to
  the compatibility post clock, not to `_02`'s ParticleSystems. A phase-paired
  check against no-frame-generation source frames 367, 382, and 397 proves
  that applying the nine-tick post offset to particle simulation makes M13
  appear before retail and removes it from the retail peak. Particle delays
  therefore remain on the selection/body timeline: M13 is absent at requested
  4.2167 seconds, alive at 4.4667, and gone by 4.7167, while the post clock is
  still 0.15 seconds ahead. The streamed late-pulse coefficients are the same
  zero-tangent cubic as the current `SmoothStep` evaluation within about
  2.5e-8. The pinned native producer selects mode 6 when both effects are active
  and radial intensity exceeds 0.01, and mode 3 otherwise; the recovered mode-3
  and mode-6 DXBC sampling equations and the source-warp/bloom-merge order are
  already represented by the compatibility shader. A tempting mode-3 c0/c25
  vector in `FrameAnalysis-2026-08-24-182850` is not draw evidence: 3DMigoto
  dumped the complete shared 4 MiB dynamic constant-buffer ring without the
  `PSSetConstantBuffers1` first-constant value needed to identify the bound
  subrange. Direct UI-free registration of the retained draw-163 output against
  adjacent no-frame-generation frames places it at source frame 381 (shared ROI
  MAE 15.9454, versus 17.8257 at 382 and 19.8977 at 380). The authored pulse and
  documented one-frame body-anchor uncertainty therefore admit zero pre-roll
  for the August 24 route, not the older recording-specific 0.15 seconds. A
  16-frame D3D11 mode-6 capture at zero pre-roll passes the grey-background,
  portrait, no-foreground-UI, SphereOutside, and exact-M27 gates; relative to
  the old 0.15-second baseline, its UI-free ROI MAE improves 35.3839 to 32.8222,
  effect ROI MAE 45.1446 to 40.5320, and temporal-delta MAE 33.1514 to 30.5939.
  Viewer capture schema v5 records evaluated chromatic intensity, radial
  intensity, effective power, and mode on every row so the next dense 60 Hz
  comparison can verify that phase without inferring it from the final image.
  The focused D3D11 capture passes those renderer
  liveness gates and visually restores the large ring at source frame 382
  without changing M13/M21 delay, scale, material, or emission data. Its
  remaining over-saturated halo is a presentation/bloom gap; the exact source
  material still authors intensity 100, exposure intensity 10.7, alpha 0.43,
  and premultiplied blending, so no unsupported material multiplier is used.
  The five retained retail FrameAnalysis snapshots also expose
  `_ExposureWithMiscParams.xy=(1,1)` in the selected global constant-buffer
  allocations, so neutral exposure is captured state rather than a tuning
  assumption. Actor SceneMV coverage and the source blank-frame history
  boundary lower the comparison to 22.3102;
  current-frame SceneMV dilation lowers it again to 22.3099. Exact retail D3D12
  presentation binding remains open.
- The selected rock-family `HGRP/LitEffect` subprograms now have cross-platform
  physical constant-buffer identities: transform variables, global variables,
  `UnityPerDraw`, `UnityPerMaterial`, and terrain subsurface constants. The
  shader parameter blob's pre-descriptor table closes all 37 named
  `UnityPerMaterial` members, including the complete `_PARALLAX_MAP` extension
  from byte 352. Decompiled use also corrects the physical texture order to
  BaseColor, Normal, MRO, ParallaxNoise, ParallaxMask, and Parallax at t0..t5.
  The selected `HGRP/DeferredLighting` pass closes the five-MRT A/B/C consumer
  at t23/t24/t25. Exact HGBuffer admission remains blocked only on live retail
  global/per-draw completeness and the complete deferred frame, not material
  layout or buffer identity. The exact remaining constant inputs are bounded to
  ShaderVariablesGlobal c27.y and live AnchorWaveBright c105.z/w, validated
  UnityPerDraw history/LOD state, and terrain subsurface profile c0.w.
  For Endminf M27 specifically, the selected retail D3D11 pair is HGBuffer
  source subprogram 113 with `HG_ENABLE_MV,SRP_INSTANCING_ON,_PARALLAX_MAP`;
  subprogram 19 is only the earlier non-instanced representative. Every selected
  draw still uses `InstanceCount=1` and `StartInstanceLocation=0`. The late
  1,080-index draw is exactly 15 copies of the 72-index source rock, matching
  M27's authored 15-particle burst: retail expands particle geometry into the
  vertex/index stream and uses SRP per-draw record 0, not Unity's standard
  procedural-particle transform buffer. The first valid pipeline change remains
  an M27-PathID-only five-MRT owner before deferred resolve, never global
  `GBuffer` admission. EndfieldCapture session `20260826T042005Z`, frame 7439,
  closes all eight numeric active constant-buffer ranges for that exact draw.
  The 16-float4 per-draw record is identity-based, its c4.w skin bit 5 is clear,
  and the captured b3 values match the exported material (`0.096` strength,
  five steps, `3.36` tiling, `20/10` radii, and the authored HDR colors). The
  optional `_VertexSkinMatrices` path is therefore inactive, consistent with
  the source mesh's zero skin rows. The hash-pinned fragment equations now have
  an M27-PathID-only five-target Unity source port. A D3D11 runtime probe proves
  the live 15-particle draw, M27-specific publication signal, and nonempty
  SceneColor, SceneMV, GBufferA, GBufferB, and GBufferC readbacks without the
  prior disabled-renderer crash. The initial zero GBufferC was a Unity owner
  transport bug: broad material copying replaced captured shader defaults with
  zeroes for properties absent from the narrow exported compatibility material.
  The owner now transfers only properties serialized by that M27 asset and
  preserves captured defaults such as `_BaseColorBrighterScale=1`. A default-off
  presentation probe now keeps private A/B/C and depth in one same-frame
  publication, stages only identity-owned M27 depth before low-resolution
  directional shadow generation, and composites color at equal depth before
  ForwardOpaque. Its 4.60-second D3D11 joined readback finds about 2.1K owned
  pixels, but the recovered pass-0 HLSL result is RGB-zero at every owned pixel;
  canonical color already equals M27's black SceneColor there. This is a
  content-invalid diagnostic, not exact admission. The remaining gap is the
  deferred light/resource fixture selected for those M27 pixels, not more
  material tuning. The `37eacbc3c84bb392` variant's descriptor layout is now
  corrected independently: its simple-subsurface arrays occupy t11/t12, the
  full-resolution screen-shadow mask occupies t13, and the zero-cookie fallback
  moves to t14. A focused 4.60-second D3D11 run verifies an all-white t13 R
  channel and valid same-frame M27 publication, yet all 2,138 owned pixels remain
  RGB-zero. This disproves the earlier t13-only explanation. M27's exported
  `_ShadingModel=0`, stencil ref 0, HGBuffer Replace operation, neutral b4/c0
  terrain-profile payload, and the retail resolver stencil contracts close its
  family as Default Lit; the adjacent foliage and subsurface fullscreen passes
  are stencil alternatives, not competing M27 classifications. An exact
  Subsurface diagnostic also remains RGB-zero and is rejected for M27. The
  remaining fault is therefore inside the Default Lit frame-input closure.
  Session `20260826T042005Z` does not contain the fullscreen resolver's state:
  the capture runtime counted plain draws but previously retained full state
  only for `DrawIndexedInstanced`, while the resolver uses
  `DrawInstanced(3,1,0,0)`. EndfieldCapture now hooks that call in a separate
  eight-record bounded list, gives the hash-pinned Default Lit resolver
  priority over generic fullscreen triangles, records both shader identities
  and compact PS b0-b10 ranges, and selects every unique backing constant
  buffer once into `resources.bin`. Its full 14-test Release suite includes an
  end-to-end D3D11 proxy package gate. The old frame contains 24 fullscreen
  triangles and Default Lit is the sixteenth. Session `20260826T083131Z` is a
  complete 50-frame, zero-drop sequence, but every package retained only the
  first eight generic fullscreen records: the game created the Default Lit
  shader before hook attachment, so the local shader registry could not apply
  hash priority. Session `20260826T085934Z` then retained the eleven-range
  Subsurface anchor at ordinal 17 in 15 clean sequence packages, confirming the
  old-frame Default/Foliage/Subsurface order at 15/16/17. It also exposed two
  independent bounds: the narrower Default/Foliage layouts did not satisfy the
  initial all-range shape gate, and two earlier 4.0/8.0 MiB buffers left too
  little of the 16 MiB resource budget for the shared 4 MiB constant arena.
  EndfieldCapture now retains 32 fullscreen records, covering the complete
  observed 24-pass sequence with headroom, and gives the targeted profile a
  32 MiB resource budget. The end-to-end proxy regression still overflows that
  list with 40 generic passes before a prioritized resolver; the full 14-test
  Release suite passes. The decoder accepts exact hashes, the old-frame-proven
  zero-based ordinal 15 range shape, or the Default record exactly two passes
  before the observed eleven-range Subsurface anchor. Fallback identities must
  be absent/zero or agree with the exact hashes; any conflict fails closed.
  Session `20260826T091023Z` closes that request: all 49 sequence frames are
  complete, zero-drop packages and retain the live Default Lit resolver plus
  its shared 4 MiB constant arena. The selected current pixel program is
  `b21a1e35eda1c5bc...`, 48,984 bytes, with nine constant buffers (`b0..b8`),
  resources `t0..t25`, and no simple-subsurface keyword. The prior exact
  consumer embedded the older ten-buffer/28-resource subsurface variant and
  shifted every binding after b6/t10. The maintained consumer, ShaderLab ABI
  shell, native bridge, standalone diagnostic, and decoder now use the live
  layout; D3D11 standalone validation passes with CB mask `0x1ff` and SRV mask
  `0x3fffffe`. The capture also proves AnchorWaveBright b1/c105 is exactly zero
  in all 49 frames. No further Default-resolver or M27 material capture is
  required. The same session
  frame observed 48 compute dispatches but retained only the first 16, with
  explicit truncation. EndfieldCapture now retains 64 compact dispatch records
  under the targeted profile, enough to preserve the complete observed peak
  sequence without quadrupling the frame snapshot's stack footprint; its full
  14-test Release suite includes a 48-dispatch no-truncation regression gate.
  Current-build native evidence proves that AnchorWaveBright c105
  is `(position.x, position.y, radius, intensity * enabledFlag)` and is published
  verbatim to the global constant buffer; the new selected-frame capture closes
  its value as zero. The current-build terrain
  profile producer is now bounded further: a reserved zero-key dictionary maps
  to float(index + 1), with zero meaning no registered terrain profile. Its
  CharInfo selected-frame value remains unobserved, so canonical M27 still must
  not assume zero.
  `decode_endminf_default_deferred_capture.py` is the maintained fail-closed
  join from the prioritized resolver record and its nine live PS ranges to the
  deduplicated resource blob. It writes source-shaped b0-b8 binary slices and
  rejects conflicting identities, unverified fallback ordinals, missing slots,
  backing buffers, or bounds.
- The two remaining M28 `VFXRefract` rows stay fail-closed, but the four new
  neutral forced-D3D11 frame analyses reopen their recovery path. All four
  record the exact SRP-instanced 0624/0625 program pair; the newest capture's
  event 127 is a one-instance, 1,764-index draw with the source two-MRT
  topology: 4K `R11G11B10_FLOAT` SceneColor,
  `R10G10B10A2_UNORM` SceneMV, and D32S8 depth. It also records the input
  layout, vertex/instance buffers, constant-buffer bindings, two material
  textures, pre-distortion SceneColor, and state-object handles. This closes
  the former shader-pair-selection and attachment-format gaps for that draw.
  Admission still requires an exact join from event 127 to one of the two M28
  hierarchy rows, decoding the selected constant-buffer ranges and instance
  record, recovering the blend/depth/raster descriptors behind the captured
  handles, identifying or capturing the other authored live window, and
  focused 60 Hz exact-versus-disabled validation for both rows. The capture is
  forced-D3D11 renderer-path evidence and does not by itself authorize enabling
  either renderer. The maintained importer therefore keeps M28 behind the
  diagnostic-only `ENDFIELD_ENDMINF_M28_VISUAL_COMPAT=1` switch; broad Endminf
  visual compatibility still preserves the canonical 68-admitted/2-blocked
  boundary. M21, exact `suikuai (1)`, and M27's exact HGBuffer boundary remain
  unchanged.
- The `M_fx_endminm_gfx_09` burst stripes now bind the exact exported RGBA
  `T_fx_star_07_D` payload. The previous missing `_MainTex` silently sampled
  white and produced a large opaque rectangle; the repaired source-alpha
  binding restores the narrow retail-like horizontal streaks without a shader
  tuning constant.
- The `M_fx_endminm_gfx_13` surrounding ring now has a focused, hash-pinned
  repair path for its exact exported decoded textures. `_DisturbTex2` and
  `_SampleTex1` share `T_fx_flow_01_M`; `_DissolveTex` and `_SampleTex3` share
  `T_fx_flow_26_M`. This replaces two dangling generated GUIDs with persistent,
  file-backed Endminf-local assets. It restores reproducible source bindings;
  it does not justify changing M13 material values or the separately authored
  M21 crystal.
- A fail-closed five-stage Viewer diagnostic now captures owned, exact-format
  copies before temporal resolve, after temporal resolve, at bloom prefilter
  mip 0, after bloom reconstruction, and after final Uber. Paired 4.40-4.55
  second D3D12 runs retain M21 in both cohorts and exclude only M13 in the
  second. The pre-temporal difference remains bounded to the raised-hand
  effect region; temporal resolve preserves that boundary, bloom prefilter
  downsamples it, and bloom reconstruction spreads its energy across the
  frame before Uber. The broad final halo is therefore downstream propagation
  of M13, not evidence that M21's small crystal mesh should be resized,
  brightened, or retimed. Detailed per-stage thresholds, bounds, and hashes
  live in `reports/assets/character_recovery/endminf_post_stage_m13_delta.json`.
  This is Unity-path attribution only and does not establish a retail mismatch.
  A later D3D11 repeat after the BaseV2 linear-tint repair sampled 4.4333,
  4.4667, 4.5000, and 4.5333 seconds with the recorded camera input. All runs
  reached the same requested/actual 60 Hz times, but two full controls did not
  produce byte- or pixel-identical final PNGs because cross-process temporal
  history differs. Final-output subtraction must therefore fail closed for
material ownership; use the deterministic pre-temporal stage diagnostic
above, and treat final PNGs as visual comparisons only.
Arbitrary requested-time five-stage capture now closes the raised-hand Unity
ownership boundary with duplicate D3D11 controls and duplicate exclusions.
The 4.40-4.4667-second surfaces remain cross-process nondeterministic and are
metadata-only; all five surfaces are byte-identical from 4.4833 through
4.7167 seconds. In that stable suffix M13 owns the large outer ring, M14 the
dense segmented trail, M21 the compact ten-stone burst, and M27 the faceted
fragment burst. M13 has exact pre-temporal zero gates after its authored
lifetime at 4.70/4.7167, while M27 is exactly absent at 4.4833 before its
4.49-second delay. M27's particle/material ownership is exact. Its ordinary
beauty rendering remains compatibility-only, while the separate five-MRT
source port is a non-presented diagnostic producer. Detailed stage
hashes, repeated-exclusion gates, thresholds, and bounds live in
`reports/assets/character_recovery/endminf_post_stage_raised_hand_delta.json`.
- The frame-generation-off recording visibly confirms additional faceted
fragments around the raised hand. Both `overview_02/all/suikuai` source rows are authored
  enabled, nonlooping, GPU-instanced mesh bursts at 4.49 seconds; an importer
  marker bug formerly mislabeled blocked rows as source-disabled and is now
  corrected. The `suikuai (1)` Refract row selects the distinct `_USE_BLEND +
  _USE_RBOFFSET + _USE_RGBOFFSET` fragment, including BlendTex alpha and a
  three-tap RGB split, plus the original particle-instance vertex transport.
  Its exact branch and `T_fx_mask_138_M` payload are now hash-pinned and admitted:
  an exact-versus-control 60 Hz run changes no pixels before 4.50 seconds, peaks
  at 3,260 bounded pixels near the hand, and decays/moves outward without the
  former oversized chromatic triangles. The generated sequence now reports 68
  admitted renderers. `suikuai (2)` is visually restored only under the
  LitEffect compatibility switch: its exact mesh, particle simulation,
  material identity, and four material textures feed a one-target ForwardOnly
  stand-in. Its source LitEffect material disables ForwardOnly and selects the
  five-MRT deferred HGBuffer program, so exact admission remains fail-closed.
  The frame analyses contain the selected M27 HGBuffer pair and close its
  one-instance, engine-expanded particle topology. The maintained targeted
  profile then recorded 52 complete frames with zero drops in session
  `20260826T042005Z`; strict verification finds the exact draw in frame 7439.
  Numeric VS/PS ranges, per-draw record 0, the inactive optional-skin branch,
  PS c103/c105, complete material b3, and b4/c0 are now captured and decoded in
  `reports/assets/character_recovery/endminf_m27_particle_abi.json`. No further
  M27 material-draw capture is needed; one resolver-state capture remains as
  bounded above. Unity now has a crash-safe, layer-
  isolated five-attachment M27 publisher with an explicit per-frame readiness
  signal. All five attachment readbacks are now content-nonzero after preserving
  captured shader defaults during exact material-property transfer. The staged
  presentation path is ordering-correct and report-visible but remains
  content-invalid because the recovered deferred resolver contributes zero on
  the M27 ownership mask. A
  compiler-extension inventory showed that Unity's callback DXBC strips RDEF,
  so source names and constant-buffer reflection cannot identify this shell.
  Activating the dedicated reserved material variant after arming adds exactly
  one VS 10/9 callback and one PS 10/5 callback to an otherwise identical
  133-hash inventory. Their stage+SHA identities are now pinned as
  `b6ffa6a650c43fa8...` and `9a6803527679aa4d...`; repeat validation clears
  Unity's per-shader cached GPU data, observes exactly two substitutions, and
  reports zero mismatches or hash conflicts. Unknown callback hashes remain
  unchanged. This closes shell identification and exact shader-object creation,
  but exact transport still must bind the captured b0-b4 ranges, six pixel
  textures, and retail particle vertex streams before the result can replace
  the visual HLSL fallback. Do not compensate by resizing, brightening,
  retiming, or disabling M21.
- Blink, facial, physical-transform, CharacterNPR, eye, hair, shadow, GBuffer,
  light, cookie, irradiance, particle, gacha, and post-processing behavior is
  recovered only where its input contract is verified. Unknown inputs remain
  explicit gaps.
- Four neutral D3D11 `ui_overview_start`/loop frame analyses pin the actual
  five-output CharacterNPR Hair PreGBuffer pair as `7b3a141f99cd9b39` /
  `00cf31fc5c40c10d`. Its 27,615 indices, stencil ref 36, and three exact
  BC7 inputs join to Endminf hair LOD0 and its D/HN/sw_M textures; in the
  newest capture event 47 changes every dump-visible attachment snapshot.
  The later `f3b955247775c7bf` / `31e969822a004ce4` draw is Hair
  `DepthOnlyOutline`: five RTVs remain bound, but its fragment writes only a
  zero Target0 after alpha test, and event 49 to 50 changes none of the four
  available attachment JPGs. Those JPGs remain cumulative snapshots and do
  not assign the complete actor silhouette to one draw. Across the four
  captures the eight CharacterNPR PreG draw sizes match eyebrow, iris,
  cloth-04, face, body, cloth-03, cloth-01, and hair exactly. Do not use this
  evidence to admit the separate generic HGRP/Lit resolver. The full matrix is in
  `reports/assets/character_recovery/endminf_ui_overview_frame_analysis_20260824.md`.
- The selected deferred resolver DXBC has a compile-valid Unity HLSL port. It
  matches the neutral fixture exactly and the recovered Wulfa fixture within
  one float ULP. The non-presented Endminf D3D11 fixture now also binds all 26
  shader resources and all nine constant buffers with zero binding failures;
  its 33,177,600 finite output floats match the recovered HLSL with maximum
  absolute error `1.1920929e-7` and no value above `1e-6`. The fixture uses an
  explicitly owned same-frame depth resource and waits for both asynchronous
  readbacks before batch teardown. This proves executable program, transport,
  and fixture-input equivalence; its screen-shadow R remains explicitly
  content-invalid and the exact output is not presented, so it does not prove
  the complete retail frame.
- D3D12 diagnostic capture proves canonical light/reflection binning,
  VisibilitySH, and SphereOutside's exact five-MRT sidecars can populate during
  the full Endminf sequence without changing any of the 41 presented beauty
  frames. The exact DXBC consumer remains D3D11-only and its private float
  readback is intentionally non-presented; those sidecars are evidence, not a
  hidden beauty path.
- Endminf's exact 12-row Overview light fixture now passes the selected
  SphereOutside b31 boundary for every saved frame: all rows are
  CharacterOnly, no-OBB, no-cookie, no-flicker, and no-culling, while the two
  serialized soft-shadow identities remain fixed at rows 3 and 11. A bounded
  D3D12 capture observes `_LightDataBuffer` and the exact zero-cookie buffer
  ready across all 41 frames while b34, the combined pass-0 gate, and beauty
  presentation remain false. The exact-consumer bridge now also requires a
  successful same-camera, same-size, same-frame constants/cookie publication;
  an allocated zero fallback can no longer pass as provenance. A new 12-row
  GPU word-readback is still open because the historical verifier's pinned
  decompiled shader inputs were retired from scratch; do not extend its older
  eight-row proof by implication.
- The interactive D3D11 Endminf B31 probe now reproduces that selected
  12-light/zero-cookie transport over the actual `ui_overview_start` to loop
  41-frame sequence. It still reports no presented deferred pass-0/shadow
  consumer, so the probe is transport evidence only; it must not be promoted
  into the beauty path or used to admit the separate HGRP/Lit resolver.
- The maintained 41-frame D3D11 Endminf reproduction now executes a canonical
  CharacterPrePass owner before Forward. Endminf's eight opaque
  DepthCharacterOnly-compatible draws write the captured Target0 zero,
  Target1 packed motion, Target2 selector, Target3 normal/family, and Target4
  material payload into the exact five formats over the shared D32S8 target.
  SceneMV is neutral-cleared once before PreG, then loaded by Forward only from
  a same-camera, same-size, same-frame publication; source `Equal` activates
  only after owner submission. A 41-frame D3D11 capture observes that owner in
  every frame and improves 28-pair no-framegen reference PSNR from 13.3608 to
  13.3886 dB; the three crystal-clean settled samples are effectively neutral.
  Actor-only frames must allocate and retain both the exact D32S8 depth owner
  and neutral A2B10G10R10 SceneMV attachment for this request even after all
  selected transparent SceneMV consumers have expired. The validated
  `endminf_canonical_attachments_fix` run keeps both readiness gates true over
  all 41 frames; the previous consumer-derived lifetime dropped them for the
  final 17 frames. D3D11 teardown explicitly unbinds the depth target before
  release so repeated manual camera renders do not retain an active surface.
  The editor harness also refreshes its
  cached standalone selectors after installing the bounded Endminf profile, so
  an earlier process-wide cache no longer deactivates the selected source
  hierarchy.
- A strengthened interactive exact-consumer probe now requires an actual DXBC
  submission instead of passing on b31/b34/GBuffer readiness alone. It remains
  fail-closed: on `MainCamera`, physical camera depth and the Endminf punctual
  atlas become ready in different observed phases, so t1 and t6 never coexist
  with the otherwise physical t0/t5/t7/t11 set. This is a bounded transport
  scheduling gap in the non-presented SphereOutside diagnostic, not evidence
  for routing CharacterNPR hair through that resolver.
- Endminf's two punctual-shadow rows now populate the lab-owned diagnostic
  atlas and selected b34 transport as two validated spot entries in contiguous
  dynamic slots 40-41. Publication still requires exact source rows 11 and 3
  by name/type, and the one-spot and six-face fixtures remain independently
  validated. The retail settled-frame light-to-shadow slot mapping has not
  been captured, so this closes the non-presented exact-consumer fixture only;
  do not infer retail order from source row, packed light, registration, or lab
  allocation order.
- The recovered VisibilitySH/capsule term improves measured character deltas,
  but it still runs against the partial ready-subset floor rather than the real
  presentation scene. The softer result is not evidence of a missing constant
  or a different capsule set.
- Native renderer-list, resource-record, and command-stream work bounds several
  producer and transport edges. It does not establish a final retail draw or
  justify replacing missing frame inputs with inferred values.

Exhaustive addresses, hashes, inventories, shader bindings, and changing
measurements belong in generated reports and versioned code contracts, not in
this memory topic.

## Evidence boundary

Recovered assets and serialized contracts prove what the client contains and,
for selected consumers, how values are interpreted. Compatibility shaders and
lab-side producers are labeled approximations unless the corresponding retail
producer and frame binding are independently established.

The lab must continue to fail closed for absent or mismatched native inputs.
Visual similarity, a lower image delta, or a working Unity replacement is not
evidence that the retail path used the same value or producer.

## Retained all-character evidence

The cleanup deliberately retains character-neutral contracts and a small
number of actor-specific, source-closed examples that will shorten the later
all-character pass:

- all 31 main Overview controllers are identified. Their recovered handoffs
  comprise 4 fixed-duration and 27 normalized transitions, with 636
  controller-proven state compositions;
- those controllers contain 165 decoded `AnimatorBehaviourPlayEffect`
  records, 369 effect entries, and 304 unique effect identities. Of 228
  non-root mounts, 217 resolve uniquely and 11 remain explicitly ambiguous;
- the exact playable 101-muscle Avatar/clip contract is retained. It applies
  to the verified playable UI scope, not automatically to generic actors or
  enemies. The generic actor audit covers 131 canonical identities and found
  no safe broad transform-retarget cohort;
- per-character CharInfo camera contracts cover 30 rigs. The 31 recovered
  light groups contain 1,583 serialized lights, with 41-67 per character;
- secondary-dynamics owner, root, collider, constraint, layout, callback,
  integration, and writeback contracts and their validators are retained.
  They preserve recovered inputs and boundaries. Some native reconstruction
  checks require the original disposable capture inputs and now fail closed
  when those inputs are absent. The exact unpatched native schedule is now
  closed, while IFix route selection and the complete numeric solver remain
  unproven. Endminf's MC_Coat payload closes its
  particles, transforms, lines, roots, capsules, and active constraint feature
  set. The pinned `VirtualMesh.ShareSerializationData` contract now closes the
  element identity and native stride for all 35 serialized proxy-array slots;
  31 contain MC_Coat data and four are source-authored empty arrays. The typed
  decoder preserves the original serialized bytes, accepts signed parent/root
  sentinels, and keeps `FixedList32Bytes<uint>` plus 32-byte
  `VirtualMeshBoneWeight` elements opaque rather than inventing inner fields.
  The authoritative codegen pointer table and full-body hashes now pin the
  unpatched `VirtualMesh.ShareSerialize`/`ShareDeserialize` implementations,
  their object field offsets, and all 35 bidirectional assignments: 11
  `ExSimpleNativeArray` rows, 20 raw native-array rows, the split edge hash-map
  keys/values, and two managed array copies. This is exact unpatched native
  assignment only. IFix patch IDs `0x555` and `0x60` are present, but their
  runtime activity and patch targets remain unaudited, so unconditional runtime
  serializer equivalence is not established. The same gate now closes the
  three nested `TransformData` arrays as `ExBitFlag8`, `float3`, and
  `quaternion` with 1/12/16-byte strides and exact unpatched bidirectional
  assignments; all 38 array-like payload rows are therefore typed while their
  original serialized bytes remain preserved.
  The four selected simulation/collider job structs now also have a closed
  inner payload ABI: 59 `NativeArray<T>` slots and four
  `NativeReference<int>` slots are exactly 16 bytes in those jobs. Combined
  with the pinned accessor bodies, `NativeArray` is pointer/length/allocator at
  `0x0/0x8/0xc`; `NativeReference` is pointer/allocator at `0x0/0x8` with four
  bytes of unclaimed-value trailing padding. This is intentionally scoped to
  the selected closed job instances and does not claim a universal open-generic
  IL2CPP size.
  The pinned managed `ColliderManager.EndSimulationStepJob.Execute(int)` body
  now also closes its per-collider frame transition: it copies the current
  24-byte `double3` position and 16-byte quaternion into the corresponding
  old-state arrays. This is exact managed carry-forward behavior only; it does
  not identify the Burst range export or recover collision/solver numerics.
  `SimulationStepUpdate` schedules the exact ordered cross-frame chain
  ClearStepCounter, CreateUpdateParticleList, StartSimulationStepJob,
  UpdateStepBasicPotureJob, and EndSimulationStepJob at schedule mode two and
  priority zero. `CompleteMasterJob` completes the same master handle and
  clears its 16-byte storage. `WriteTransform` constructs the exact 0x70-byte
  TransformAccess job, using the manager's current position/rotation/local
  arrays for the job fields named `last*`, and schedules the closed
  `WriteTransformJob` MethodSpec at mode one. Full native bodies, generic
  identities, icall slots, and literals are pinned in the generated schedule
  contract. IFix IDs `0x31a` and `0x32a` are present but unaudited, so these
  conclusions apply only to the unpatched route and do not recover Burst
  numerics or prove Unity runtime execution.
  The two former Collider End ABI-shape candidates remain rejected by their
  pinned AVX2/SSE2 cores: one uses 12-byte float3 positions where the canonical
  job requires 24-byte double3, and the other treats its first lane as a scalar
  while operating on 184-byte records. A whole-DLL semantic scan found the
  omitted struct-payload export `b44b8d6a5416f62541c69d9812961578` instead.
  The monolithic `burst.initialize` function assigns its slot `0x3c6060` to
  the pinned SSE2 `0xae190 -> 0xae300` and AVX2
  `0x24a030 -> 0x24a1a0` entry/core pairs; both cores implement the exact
  24-byte position and 16-byte rotation carry-forward. Runtime resolver
  telemetry remains necessary only to prove the managed BurstDirectCall route
  selected that hash, not to identify the export or its dual-CPU semantics.
  The same `burst.initialize` slot graph now closes Simulation Start export
  `c7e2be088565d3ff7a6e7ba86d23fd51`: slot `0x3c6390` reaches the SSE2
  `0xd3c20 -> 0xd3db0 -> 0xc6f10` and AVX2
  `0x26a370 -> 0x26a440 -> 0x25e830` entry/range/core chains. The final
  6,687-byte and 5,074-byte solver bodies are hash-pinned and expose the
  canonical particle, 464-byte TeamData, and 808-byte ClothParameters strides.
  Bounded AVX2 decoding now closes particle/team selection, shortest-arc base
  transform interpolation, simulation bypass, inertia, 16-sample damping,
  gravity and impact dispatch, semi-implicit prediction, spring distance/noise,
  and both final position writebacks. Normal-cone helper `0x23c1c0` is now
  pinned as Burst's 718-byte scalar binary64 cosine implementation, including
  its small/medium reduction, large reducer, polynomial, and non-finite cases.
  Wind helper `0x247190` now also has closed zone/moving accumulation,
  friction/depth attenuation, turbulence/noise, ZXY Euler direction, and
  magnitude equations; its two 5,775-byte inlined sine/cnoise/quaternion
  specializations remain hash-pinned rather than coefficient-transcribed. The
  inline normal-cone stage is now closed too: distance and signed-normal
  projection clamps, its two-range asin polynomial, exact Burst cosine
  composition, threshold, and final correction are recorded. Start's semantic
  equations are closed for the valid authored domain; thirteen native/source
  golden vectors now match bit-for-bit across bypass, interpolation, inertia,
  damping/gravity, both authored force modes, spring clamp/noise, and cone
  restriction, including non-identity base/center quaternion slerp, nlerp,
  shortest-arc sign correction, and rotated inertia position/velocity. The
  directly invoked spring sine and cone cosine are now standalone source
  transcriptions with a hash-pinned 3,876-double reducer table; 23 boundary
  vectors plus 45,470 finite inputs match native binary64 outputs exactly.
  The Unity `StartSimulationParticleZeroWind` port now matches all thirteen
  Start vectors bit-for-bit and embeds the same checked reducer table without
  calling the game DLL. Nonzero wind remains the general Start-port boundary,
  but the complete selected Endminf postmodel census contains only four cloth
  and ten capsule components, and the Character Info environment contains no
  wind zone, so zero wind is the authored target domain. Collision and later
  constraints belong to subsequent stages.
  The same static slot graph now closes the remaining Simulation range stages.
  `UpdateStepBasicPotureRangeKernel` is export
  `a8df0cddc9889e0c46f8bec650d8b959`, slot `0x3c5ed0`, with SSE2
  `0xa5480 -> 0xa5e70 -> 0xa5670` and AVX2
  `0x241910 -> 0x2421b0 -> 0x241aa0` entry/range/core chains. Its ordered
  element accesses match the managed job exactly: one-byte attributes,
  four-byte parent indices, and 16-byte quaternion output writes. A newly
  closed representation boundary corrects the prior position-width claim:
  managed fallback metadata reports 24-byte `double3`, but both Burst cores
  index `basePos` and `stepBasicPosition` as packed 12-byte `float3`. The AVX2
  equations now close baseline selection, parent/root hierarchy reconstruction,
  negative-scale handling, and the animation-pose position/quaternion blend;
  six native/source vectors cover its hierarchy, scale-sign, pose-ratio,
  nlerp, and slerp branches, and the Unity source port matches every recorded
  binary32 output exactly. `EndSimulationStepRangeKernel` is export
  `41ab6c9cba7b13c1177cc44fe548d030`, slot `0x3c4fb0`, with SSE2
  `0xcc240 -> 0xcc460 -> 0xb5450` and AVX2
  `0x2630a0 -> 0x263250 -> 0x24fa60` chains. Its positional ABI maps the
  particle index, 464-byte TeamData, 808-byte ClothParameters, and 696-byte
  CenterData inputs. Runtime telemetry remains necessary only to observe the
  managed wrapper-to-hash selection. The call-free 1,745-byte AVX2 core now
  has closed equations for inactive bypass, static-friction accumulation and
  release, dynamic-friction attenuation, particle speed limiting, center
  centrifugal response, and the velocity/real-velocity/old-position writes.
  Eight native/source vectors cover every closed branch, and the Unity port
  matches all recorded binary32 and binary64 outputs exactly.
  The managed projection chain between posture reconstruction and End is also
  closed in order: Tether, Distance, Angle, Triangle Bending, Collider
  Collision, a second Distance pass, Motion, and both Self Collision calls.
  Endminf's four owners require tether/distance/angle; triangle bending is a
  topology no-op because all four have zero triangles despite nonzero authored
  stiffness. All four owners author collider mode `1` (Point); Ribbon2,
  Ribbon, and Coat have capsule references while Hair has none. The Edge
  kernel requires mode `2`, so Endminf's line topology does not activate edge
  collision. Authored Motion and Self Collision are off.
  Collider End export `b44b8d6a5416f62541c69d9812961578`
  is now explicitly classified as a 117-byte current-to-previous collider
  transform snapshot, not the contact solver. Contact position, friction, and
  normal writes belong to `ColliderCollisionConstraint.SolverConstraint`.
  Tether export `5f353c4e9c4136cbe284ba1795d08c96` now has
  closed compression/stretch projection equations and five controlled native
  AVX2 golden vectors. The source transcription matches the original core's
  binary64 output exactly for full/partial stretch, compression, dead-zone,
  and oblique-normalization cases; the Unity port matches all five exactly.
  Distance export `166b2138a31dc6d21b37fb45b233bcbc` now has closed
  two-pass mixed-precision equations, including packed 12/20-bit constraint
  lists, 16-sample stiffness interpolation, mobility weights, rest/base-pose
  target blending, averaged correction, and velocity-position writeback.
  Point collision export `6a5470d135bde394bed7e7182cdf7c65`
  likewise closes the active moving-capsule transport, penetration averaging,
  contact normal, and friction equations. Six native cases now cover static,
  translated, rotated, tapered, no-contact, and near-contact/friction capsule
  paths exactly. Distance has eight native cases and a Unity source port that
  matches their binary64 outputs exactly; the Point port also matches all six
  cases. Both remain disconnected from transform writeback.
  Collider Start export `8b3d2761aaaac71a35d4a2557d570456`
  is now closed to its AVX2 `0x243810` core and canonical 16-pointer ABI.
  Ten native/source vectors match every output byte across bypass, static and
  moving capsules, translation, rotation, scale, all axis directions,
  reverse/alignment modes, and radius-separation clamps. This closes collider
  work-data construction; the Unity port matches all ten native vectors
  bit-for-bit. Collider End is also ported as the exact selected-index
  current-to-previous snapshot with no-access and fail-before-write coverage.
  Managed registration/input construction is closed too: Endminf has nine
  type-2 X capsules and one aligned-center type-4 Z pelvis capsule, so the
  otherwise unsupported type-7 branch is absent. Exact flags, reset-bit
  consumption, size/radius rewrite, center-offset frame position, rotation,
  and scale provenance are pinned for all ten rows.
  Angle export `1835a4d768d0158271d1bcd27c64126f` is now closed as a
  three-sweep baseline solver. All owners use restoration, while only Hair
  uses the angle-limit branch. The pinned equations include scratch
  precomputation, 16-sample curves, friction mobility, limit and restoration
  parent/child writes, deterministic parallel/antiparallel handling, Burst
  acos polynomials, and the scalar float sincos helper. Seven Angle vectors
  match the native core exactly. The formerly native-only sincos dependency is
  now a standalone source transcription with a pinned 416-word reducer table:
  24 boundary vectors, every finite exponent, and a further 25,000 finite
  inputs matched native binary32 outputs exactly. Unity Angle integration now
  preserves parent-indexed immediate writes across the original ordered three
  sweeps and matches the seven controlled pairs plus all 18 decoded Endminf
  baselines (3-9 particles) bit-for-bit. Those baseline vectors begin from
  decoded bind pose with controlled velocity, friction, and constraint values;
  live per-frame state remains unavailable, and displaced multi-particle
  limit-plus-restoration combinations retain the controlled two-particle
  branch evidence.
  The Unity lab now has one actor-root, fail-closed secondary-dynamics
  coordinator with all seven recovered PlayerLoop boundaries. FixedUpdate
  only increments the original counter; one mutually exclusive callback runs
  the complete cloth pipeline before or after `ScriptRunBehaviourLateUpdate`
  according to `updateLocation`. Its generated Endminf data validates all 126 ordered proxy
  bindings, 100 unique transforms, and 26 overlapping MC_Ribbon/MC_Coat writes,
  and reproduces the nonzero-target 8/s enable and 6/s disable weight ramp.
  The data layer now also bakes source-order attributes, hierarchy indices,
  local posture arrays, baseline slices, center-fixed vertices, packed Distance
  constraints/rest lengths, authored solver scalars, all ten capsule shapes and
  transform bindings, and each owner's exact collider index list. All twenty
  required compiled curve buffers (five per owner, 320 binary32 lanes) are now
  hash-gated and baked exactly after matching Unity 2021 and Unity 2022 probes;
  no authored AnimationCurve approximation remains in the Endminf target path.
  The remaining solver-scalar packing is closed from the pinned retail
  `GetClothParameters` body: Tether stretch is binary32 `0x3cf5c28f`,
  Distance velocity attenuation is `0x3e99999a`, and the one authored collider
  friction value is copied to both dynamic and static parameter slots. The
  data builder bakes these values and runtime validation rejects stale assets
  or any dynamic/static split.
  An inert owner solver now allocates transactional proxy state and executes the
  recovered Start, Basic posture, Tether, Distance, Angle, optional Point,
  second Distance, End, and collider-snapshot order at the retail cadence. It
  exposes publication-ready arrays but still requires explicit certified
  center/team and prepared-capsule inputs and performs no runtime writes.
  A four-owner inert frame coordinator now supplies those inputs by composing
  exact fixed-center aggregation, team-step state, ten-collider preparation,
  owner collider subsets, and the retail clock. It remains value-only and
  transactionally rejects uncertified relative/cross-frame session flags.
  TimeManager now has a pinned stepping contract: retail defaults are 90 Hz
  with a three-step cap, runtime clamps are 30-150 Hz and 1-5 steps, and the
  default `SimulationDeltaTime`, `MaxDeltaTime`, and four power lanes are
  closed. The unpatched per-team float32 accumulator, maximum-team reduction,
  solver loop, and team clock are now closed too. At ordinary 60 fps the
  default 90 Hz path executes one or two steps per render frame, averaging
  1.5; its phase is not a guaranteed strict alternation. An inert managed
  helper now reproduces that accumulator exactly (89 steps in the first 60
  frames and 1800 in 1200) while rejecting IFix and unsupported nondefault
  power-helper routes. World and local proxy publication equations,
  source-array manager offsets, scheduling order, final TransformAccess flags, simulation/LOD
  weight, and blend branches are also closed. The final TransformAccess list
  retains all 126 entries rather than deduplicating them: Ribbon2/Coat share
  six transforms and Ribbon/Coat share twenty. The TransformAccess write gates
  now close the apparent conflict without an owner-priority policy: Ribbon2 is
  the only writer on six paths, Ribbon is the only writer on eighteen, and the
  two fixed/fixed paths have no writer; Coat wins none. Source-order execution
  remains unproven because the job is parallel, but there are no competing
  TransformAccess writers. A pure managed publication
  helper verifies the world/local, weight, culling, shortest-rotation, spring,
  and fixed branches while preserving duplicate outputs without touching any
  Transform. The input-side transform contract now also preserves all 126
  manager entries and closes the active attribute flags and six read channels;
  proxy bases come from each world local-to-world matrix, while captured local
  channels serve restore/writeback. `UseAnimatorTransform` is source-statically
  false, selecting ordinary Transform reads and TransformAccess writes, while
  public `CopyDoubleBuffer` has no direct caller and is dormant in `ClothUpdate`.
  Live `TeamData.useRelativeTransform` and `UseCrossFrameJob` can still be
  changed by reset, timeline, and authored physics-quality paths; these are the
  two remaining target-session gaps. Minimum telemetry is one manager static
  byte before each `ClothUpdate` plus the four team relative-transform bytes
  (or the corresponding setter watch) across the maintained 770-frame sequence.
  Runtime writeback therefore remains disabled until that telemetry is captured;
  no unchanged-output rerender is treated as progress.
  For the two Endminf target clips, all four MC center objects are identity
  children of the actor root and Unity reports no root or motion curves, zero
  average speed, and zero average angular speed. Root translation/rotation is
  therefore target-static. CalcCenter aggregation is now closed for all authored
  1/8/4/9 fixed lists: ordered float64 position means and binary32 fixed-vertex
  rotation reduction match 13 native vectors, including independent spatial
  cases. Its stationary-root smoothing is also exact. Native sentinel and
  instruction-flow checks prove CalcCenter preserves, rather than computes,
  the center step/inertia/angular block. Those Hair/Coat inputs belong to the
  separately scheduled `SimulationStepTeamUpdate` kernel. That kernel is now
  target-ready for stationary-root, positive-scale, no-wind, unpatched overview
  playback, including interpolation, local-inertia ratios, translation/rotation
  speed clamps, angular velocity/axis, and state advancement. Hair's local
  inertia produces zero ratios; Coat uses the exact 0.2 base ratio and its
  720-degree/s rotation clamp. `depthInertia` remains a later Simulation Start
  input as expected; target gravity/scale ratios remain one.
  The bounded read-only Burst resolver telemetry manifest now includes exact
  constructor, static-constructor, shared-initializer, function-pointer, and
  invoke windows for Collider Start and Collider End alongside the three
  Simulation kernels. Its target block is hash-pinned and passes the installed
  four-file check-only gate; no live attach or kernel execution observation has
  been performed.
  Regenerate with
  `python unity_endfield_graph_shader_lab/tools/build_secondary_dynamics_proxy_layout_contract.py`,
  then publish the read-only decode explicitly with
  `python unity_endfield_graph_shader_lab/tools/build_secondary_dynamics_payload_decoder.py --allow-source-hash-mismatch`
  while the three disposable target-filter inputs are absent. All constraint
  families activated by Endminf now have managed numeric ports; the remaining
  gate is exact center/team frame-state publication, composition into the
  recovered substep loop, and duplicate-safe transform publication. Do not
  replace that path with a simple spring/gravity surrogate;
- the Last Rite head effect and Li Zhiyan finger effect remain as exact,
  fail-closed source contracts and builders. They are useful reference cases
  for hierarchy, mount, timing, particle, mesh, material, and texture recovery,
  but their retired actor-specific Unity bindings are not active runtime code;
- Zhuangfy's durable Overview animator/effect binding result remains in the
  generated recovery report. Its gacha runtime and capture experiments were
  not retained.

The corresponding inventories and evidence live in versioned contracts and
`reports/assets/character_recovery/`. M23 diagnostics, gacha-room trials,
visual capture harnesses, generated comparison materials, and actor-specific
approximation branches were retired because they do not establish reusable
retail behavior.

## Active reproduction target

The visual source of truth is `videos/2026-08-15_10-32-32.mkv`, with
`videos/2026-08-21_20-15-17.mkv` used by the focused Endminf comparison path
and `videos/2026-08-24_06-37-22.mkv` retained as its 4K, user-confirmed
frame-generation-off companion reference.
Current work should compare camera, timing, pose, materials, effects, lighting,
background, shadows, and final post-processing against those recordings.
For the current Endminf deliverable, Unity retains the CharInfo grey background
target and actor-specific background portrait with the main character and her
spawned visual effects. Foreground controls, labels, icons, cursor, and other
front UI overlays are excluded. The portrait transport is source-recovered.
The grey carrier now uses the frame-proven physical `SphereOutside` HGBuffer
plus Default Lit resolve before ForwardOpaque; foreground UI remains excluded.

The maintained video-to-frame workflow is
`unity_endfield_graph_shader_lab/scripts/reference_video/`. Its config records
explicit character intervals and uncertain identities; generated PNG sequences
and source-pinned sidecars stay disposable under the lab's
`scratch/character_recovery/reference_sequences/` tree. The focused Endminf
capture is labeled `ui_overview_start_then_loop`; its maintained reference
window begins at user-selected original decoded frame 1109 (18.4666667 seconds
at 60 fps) and continues through the recording end. Frame 1109 is the blank
model-swap boundary and frame 1110 is the first visible body frame. The Viewer
comparison validates the extracted sidecar, anchors that body frame, and maps
each saved Unity frame to an exact decoded source frame from measured
selection-edge elapsed time. It no longer compares against the unrelated
earlier occurrence at 3.64 seconds. The latest 28-pair sheet and its explicit
source-frame map remain disposable beside the Viewer capture output.

The August 24 sequence retains one-based source frame 113 as the final
model-swap/prehistory frame and begins visible Endminf on frame 114. Motion
correlation best aligns the first saved Unity phase to source frame 115, with a
bounded plus-or-minus-one source-frame uncertainty; this companion pairing is
diagnostic rather than exact. The same strong opening comb trails remain
visible with frame generation disabled, so they must not be attributed to
generated-frame interpolation; their exact game-rendered temporal or
authored-effect producer remains open. The amber rock/crystal, orbiting
fragments, and bloom are a separate actor-owned entrance effect. Obvious amber
particles persist through source frame 461 and frame 462 remains ambiguous;
unmasked body/material measurements begin at source frame 472, and the phase
uncertainty excludes any paired row whose lower bound precedes 472. Earlier
rows require an actual moving amber-component mask dilated for bloom because a
fixed ROI crosses unrelated character pixels. M27's authored 4.49-second delay
maps near one-based source frames 384-385; inspection of decoded frames 381-392
confirms the physical faceted-shard burst in the no-frame-generation capture,
but overlapping exact consumers prevent assigning every visible shard to M27.
The maintained comparison
resamples 3840x2160 to 1920x1080 with Lanczos and no crop before sheet
downscaling; do not use cross-resolution whole-frame metrics outside that
explicit contract.

The pre-burst `overview_04/1/Particle System (1)` M29 mesh particle uses
`M_fx_endminm_gfx_29`. Its source Material pins `_MainTex` to
`T_fx_flow_17_M` (`pE9BD526F8E515836`, decoded PNG SHA-256
`28406becfc0f0eaf58cd234a3e590fbc2823975d307bfe990d19fa2af28ed8fb`)
and `_DisturbTex1`, `_MaskTex`, `_SampleTex0`, and `_SampleTex1` to
`T_fx_flow_01_M` (`pE924975F4B2F54A4`). Both generated bindings had fallen
back to white; the maintained Overview texture repair now restores and
hash-gates them. Arbitrary requested-time capture can now retain all five
post-stage surfaces. Duplicate D3D11 controls and duplicate M29/M30 exclusions
fail closed at 4.15-4.1833 seconds but are byte-identical from 4.20 through
4.2667 seconds. In that stable interval, excluding M30 removes the broad early
amber halo owned by `overview_04/1/guangyun (3)`, while excluding M29 also
changes the pre-temporal scene buffer and final image independently; M29 is
therefore a real mesh contribution, not a negative control, even where its
final-image change is visually subtle. Detailed stage hashes, thresholds, and
bounds live in
`reports/assets/character_recovery/endminf_post_stage_m30_m29_delta.json`.
The later outer ring belongs to `overview_02/all/huan` with M13. M31/M43
contribute minor haze, M42/M32 inner arcs, M24 sparks, M14 segmented trails,
and M21 the small stones. Do not tune M29 or the crystal system to compensate
for M30/M13. M29 still has unclosed per-draw color/LOD semantics; a useful
future graphics sequence is retail source frames 364-371 (center 367/extracted
frame 255), retaining its 1,386-index one-instance Sphere001 draw.

The same audit found 20 additional dangling generated texture slots across
M18, M20, M28, M32, M35, M42, M46, and `M_ui_wind_901`. One targeted
AnimeStudio pass recovered their exact source-local flow maps; the maintained
repair now hash-gates seven decoded PathIDs and restores 29 bindings across ten
materials (including the earlier M13/M29 closure). Two source-local assets are
both named `T_fx_flow_902_M`, so M35 `_OffsetTex` is explicitly pinned to the
cloudy `p8CA0E6F6DA6348A5` payload rather than the unrelated triangular
`pC983DCCB52F1F83F` payload. Unity batch import passes and the generated
Overview material census has zero unresolved texture GUIDs. Historical phase-
matched 4.2167/4.4667/4.7167-second actor-only renders remove the white-fallback
shapes but exaggerate the M13 ring and dotted trails against black. The
canonical capture now includes the grey CharInfo carrier and actor-specific
portrait, which makes the same source-authored smoke pale and translucent
without material attenuation. Existing exact-owner evidence says M13 owns the
large ring; do not tune it from the retired black comparison.
A current-build, exact-AssetMap AnimeStudio pass now restores the complete
serialized Material JSON boundary for all 36 admitted Endminf BaseV2 rows from
their two source chunks. The fail-closed admission audit validates every
source hash, common shader PathID, ordered local keyword set, render queue, and
matching original D3D11 variant with zero failures. This closes source
provenance for the active M21/M24/M30/M31/M32/M35/M42/M43 crystal and hand-VFX
rows as well as the remaining Overview BaseV2 materials; it does not itself
prove a visual parameter mismatch or authorize aesthetic tuning.
A same-seed exclusion at 4.2167/4.4667/4.7167 seconds now attributes the dense
segmented white trail specifically to `overview_02/all/Particle System` and
`M_fx_endminm_gfx_14`: it owns 466 of 531 live particles at the last sample,
and excluding only M14 removes that trail while preserving the surrounding
smoke, stones, fragments, and isolated lights. Retail retains a much finer
version, so M14 must not be removed. Exact-build graphics session
`20260826T000901Z`, frame 13175, closes its shader and expanded-particle ABI:
the dynamic VS4914/PS4915 draw has 1,710 indices/285 quads and complete bounded
VS b0-b4 plus PS b0-b3 snapshots. VS b3/c13 is zero, so source vertex color is
unmodified. All eight retained exact-pair draws (seven unique generated
materials: M14, M22, M26, M31, M39, M40, and M43) expose PS b3/c4 values that
match Unity's normal authored-Color linear upload; M31 appears in two draws.
The former compatibility raw-sRGB tint path was therefore a systemic recovery
error, not an M14 exception. The maintained importer now applies normal linear
Color transport to all 36 admitted Endminf BaseV2 materials and validates all
seven captured material witnesses. A D3D11 Viewer rerender passes and changes
30.2%, 42.0%, and 66.6% of pixels at the three bounded late-effect samples;
phase-matched comparison confirms the color moves toward retail. The remaining
early M30 halo and later M13 ring are separate phase-specific contracts, and
most of M30's rightward extent is hidden behind opaque retail UI in the
reference. Their actor-only size therefore cannot be corrected from the
composited reference alone and is not evidence for restoring raw-sRGB tint.

The same frame's complete `resources.bin` contains the shared dynamic particle
buffer despite its recorder label reflecting the first SRV observation. The
verifier recovers the exact 36-byte Position/Normal/packed-Color/UV stream: 288
contiguous expanded quads contain the 285 consumed by M14, with 247
non-degenerate witnesses and median width:height `1.9973:1`. This independently
confirms the recovered Stretch renderer and `lengthScale=2`; the authored
start-size/size-over-life, 2,000/s emission window, 4.4-second delay, and timing
remain unchanged. A count-matched Unity sample at 4.55 seconds has 300 M14
particles versus retail's 285, while the earlier 4.7167 comparison had 466 and
was too late for a shape-density judgment. Remaining actor-only contrast is a
presentation/compositing boundary, not evidence for resizing, retiming,
attenuating, or disabling M14. M14's exact AssetMap source now also supplies the
complete native `T_fx_glow_105_D` BC7 payload: 256x128, nine authored mips,
43,728 bytes, SHA-256
`FFD3A6F707D0D0A6C92D3012BEC11A41B59AB4949E377558F426EAD4AD22D672`.
The importer validates every mip offset/size and the reloaded Unity raw bytes
before binding `_MainTex`, instead of allowing Unity to regenerate lower mips
from the decoded PNG. Focused positive/negative verifier tests and the Unity
material rebuild pass. No further M14 or secondary-dynamics capture is needed
for these corrections.

Exact-build session
`scratch/reverse_engineering/endfield_capture/20260825T230225Z` is the complete
replacement secondary-dynamics capture. Its finalized, lossless ten-second
window records 598 readable `ClothUpdate` calls with
`UseCrossFrameJob=true`, 598 matching direct-array scans, and all 184 live
TeamData rows on every scan. All 110,032 `useRelativeTransform` reads are false,
with zero unreadable scans, overflow, dropped events, or invalid records. The
strict session builder verifies the exact game build, collector inventory and
hashes, shutdown cleanup, full row/call cadence, and bounded universal coverage;
the generated contract is therefore target-certified for
`useRelativeTransform=false`, `UseCrossFrameJob=true`, ordinary Transform reads,
and TransformAccess writeback. EndfieldCapture's retained-row bound is 256 and
its exact 171-row regression plus the complete 14-test Release suite pass.

Certification closes the retail settings route, not the recovered solver's
numeric behavior. A prior 770-frame diagnostic run inflated the entrance cape
into a broad rigid sheet and degraded hanging-strip and hair silhouettes. The
captured skinning oracle shows that the authored baseline is already close in
the settled loop but diverges during the entrance. Solver writeback therefore
remains default-off until a phase-paired run passes the retail shape gate;
normal actor/VFX reproduction retains the authored baseline. Regenerate the
session contract with an explicit `--session-root` and `--require-certified`;
the builder supports the current direct-array full-scan evidence and rejects
partial rows or incomplete collection.

The four August 24 observer captures also close Endminf's post-Forward
CharacterOutline owner. Retail draws exactly six LOD0 submeshes (face, body,
cloth-01, cloth-04, cloth-03, and hair), omitting eyebrow and iris. Exact
exported shader joins recover `Cull Front`, `ZTest Less`, `ZWrite Off`, black
target-0 blend, packed SceneMV target 1, Skin/generic stencil ref 36, and Hair's
stencil-16 exclusion. The Unity owner now uses the recovered clip-space
depth/FOV/aspect width law and publishes SceneMV in the same frame. The source
mesh importer now preserves the four-component `m_UV2`/`TEXCOORD2` stream, so
the selected material's packed average-normal reconstruction is active. The
outline-mask green channel and `_OutlineOffsetZ` also reproject the exact
camera-space depth bias instead of applying the former generic clip nudge. Its
41-frame D3D11 gate passes. Two phase-identical post-rebuild captures still
match zero of 41 frame hashes and have 31.4456 dB mutual PSNR; their three
crystal-clean retail comparisons span 14.0684-14.0744 dB, containing the prior
14.0693 dB result. Do not attribute that cross-run metric movement to the
outline until the broader temporal/physical nondeterminism is closed.

Do not fork the renderer per actor. Endminf-specific code may own source asset
selection and timing, while the importer, material mapping, animation,
presentation scene, and render pipeline must remain reusable for the eventual
all-character rebuild.

## Main rendering gap

The blocking gap is the complete CharInfo physical presentation frame, not
another per-material shader approximation. The missing boundary includes:

- the real `SphereOutside` and `ShadowPlane` scene participation;
- the downstream character stencil receiver integration beyond the now-closed
  PreG/Forward/CharacterOutline writer states;
- render-graph/subpass state and frame-produced lighting resources;
- confirmation of the final source camera and presentation bindings.
- ten still-blocked rock-family renderer identities awaiting the bounded live
  global/per-draw/subsurface values and the complete deferred frame resources;
- exact retail D3D11 presentation binding after the now-closed Effect-02
  combined Uber source, bloom, LUT, and output-tail contract;
- the full TAA producer/consumer chain beyond the now-complete actor SceneMV
  MRT coverage, recorded blank-frame history boundary, and recovered Dilation
  auxiliary-history producer.
- the custom Streamline DLAA consumer/output after the now-exact
  `_CombinedVelocity` producer. Four retail D3D11 descriptors prove the
  producer's full-resolution `R16G16_FLOAT` UAV allocation; this does not make
  Unity's public D3D12 NVIDIA wrapper equivalent to the game's D3D11 schedule.

`SphereOutside` is asset-complete. Its remaining gates are runtime frame state
and resources. The live exact deferred resolver is no longer a blocker. The
Unity-owned M27 HGBuffer shell now closes the retail `10/9` vertex and `10/5`
pixel signatures with independently isolated, stage+SHA-pinned callback
identities; WARP object creation and a repeatable Unity cache-cleared activation
both pass. Session `20260826T042005Z` also contains the exact 435-vertex,
1,080-index expanded 15-rock draw in its shared graphics ring, and the maintained
generator recovers the unique 60-byte Position/Normal/Color/UV/UV2/Custom1
stream plus its 16-bit index stream. Older M27-bearing sessions (`042005`,
`083131`, and `091023`) retained only b0/c0-c27 while the retail vertex shader
projects through b0/c32-c35 and reads c44/c81. Targeted session
`20260826T141208Z`, frame 2529, closes that gate: its exact 1,080-index draw
retains all 82 VS b0 vectors through c81, and the shared b0-b2 buffer/range
identities prove that the larger VS b0 prefix is also the correct shared-stage
payload. The maintained generator rebases the immutable 435-vertex packet and
constant arrays to this frame and reports the exact vertex envelope closed. It
also emits the eight distinct stage-specific native buffers instead of folding
same-numbered VS/PS slots through Unity material constants. The direct D3D11
path binds the captured six-texture order, zero skin SRV, shared sampler,
five-MRT/depth/stencil state, packet-local 60-byte input layout, and exact
1,080-index draw. WARP creates both shaders and the layout. A synchronized
4.50-second combined Viewer run validates nonzero M13, M14, and M27 native draw
counts with zero callback failures and `S_OK`; M27 writes 22,110 owned pixels
and changes 4,553 presentation pixels in the same command sequence.

Session `20260826T162514Z` closes M27's temporal IA envelope. Its 65-frame
targeted sequence contains 37 M27-pair-bearing frames and safely reuses aliased
SRV/IA blobs. The maintained fail-closed verifier selects 16 phase samples from
frame 2905 through 3027: 39 exact draws spanning the four-crystal hand phase,
an explicit zero-M27-draw flash transition at frame 2970, the 1,080-index
15-crystal peak at frame 2978, and the complete decay. Frame 2905 retains four
separate 72-index draws with the exact 68-byte slot-0 stream, 20-byte
stride-zero slot-1 carrier, R16 index base, byte offsets, and complete
stage-specific constants. Every effective index slice byte-equals the 72-index
source mesh, and every effective vertex slice contains all 29 source UV pairs
at the captured 68-byte cadence. The peak and decay use the separate 60-byte
layout and pass the same source-index/UV and constant-range gates. The report is
`reports/assets/character_recovery/endminf_m27_temporal_capture_latest.json`;
its verifier and three focused regressions pass. No further M27 material,
resolver, geometry, or temporal game capture is currently needed.

The shader-pair-only `M27` label above is narrower than the retained evidence
permits. M01, M27, and M38 share that exact LitEffect VS/PS pair and repeated
29-vertex/72-index topology. The aggregate fail-closed verifier now scans all
38 retained frames from 2721 through 3027 and validates 157 draws: 105 carry
the bright M01-or-M27 PS b3/c29 fingerprint and 52 carry the lower M38
fingerprint. All 23,112 indices repeat the source topology, all 9,309 effective
vertices are exactly sliceable, and the source-UV signature is recorded rather
than incorrectly used to reject the 59 alternate particle-layout draws. The
sequence contains early M01/M38 aggregates, a zero-draw transition at frame
2970, and the late single M27 draw. Treat the existing 16-packet native replay
as a proven shared-LitEffect transport over its selected late window, not as
proof that every early 72-index draw belongs to M27. The full aggregate report
is `reports/assets/character_recovery/endminf_liteffect_temporal_capture_latest.json`;
the existing session is sufficient and no additional game capture is needed
for this owner split.

The complete M27 sequence now replays through the native D3D11 owner rather
than holding the old peak checkpoint. A generated 16-packet/39-draw payload
retains each packet's effective vertex/index slices, separate VS/PS constants,
the retail 60- and 68-byte input layouts, the captured t0-t3 BC5/BC7 resources,
the shared black t4/t5 fallback, and the explicit zero-draw packet. The actor
overview clock owns packet selection through the corrected captured
3.2167-5.2500-second
envelope; it deliberately outlives AnimeStudio's approximate ParticleSystem
lifetime. A five-phase D3D11 Viewer run covering rise, zero draw, 1,080-index
peak, and decay publishes M27 in every requested frame, reports nonzero native
draws, zero failures, and `S_OK`. The zero packet byte-identically preserves
the no-M27 image, while the rise and peak change only their expected rendered
samples. The decayed tail remains a valid but pixel-neutral publication at the
sampled presentation frame. WARP validates both retail input layouts, and the
runtime fails closed with a resource-stage code if creation or binding drifts.
The full 41-frame actor-only sequence now treats M27 readiness as required only
inside that captured packet envelope and can initialize the native owner from
the retained inactive PathID binding before the approximate renderer spawns.
Rise, peak, decay, and the later no-M27 tail therefore pass one continuous
capture instead of requiring a peak-only probe.

The same `20260826T162514Z` packages close the selected-view exposure boundary.
Across frames 2970-3027, the relevant PS b1 c27 global is consistently
`_ExposureWithMiscParams=(1, 1, 1.7777778, 0.1002004)`: adapted exposure and
its reciprocal are both exactly one. A matched Unity D3D11 frame reports
`(1, 1, 1.7777778, 0)`; the recovered Endminf BaseV2 consumers read only `.y`,
so exposure does not explain the oversized actor-only peak. Grouped renderer
exclusions instead attribute that peak to the ordinary additive BaseV2 stack:
removing all ordinary producers removes it while exact M13/M14/M27 publication
remains healthy. M20 owns most of the broad brown decay smoke, M14 owns the
later dense gold fragments, and M22 owns thin rays/sparks. The staged M20
Material and ParticleSystem JSON byte-for-value match their generated Unity
assets, so do not suppress or rescale them to compensate for comparing black
actor-only output with retail's grey Character Info composition. The canonical
peak render now includes the grey CharInfo carrier and recovered Endminf
portrait with no foreground UI. `20260826T162514Z` contains no exact
`SphereOutside` HGBuffer pair, and no earlier EndfieldCapture metadata contains
that pair. The next graphics evidence is therefore one settled full-profile
frame after the entrance VFX has disappeared; it must retain SphereOutside and
the neighboring exact Default Lit resolver. EndfieldCapture now priority-
retains the Sphere pair, IA geometry, all bounded Sphere PS SRVs, resolver
b0-b10, and all 32 resolver PS SRV slots in that single package. Its direct
`DrawIndexed` path and exact 2,304-index static-mesh fallback are retained too,
so shader creation before attachment cannot silently drop the draw. Do not use a
long full-profile sequence because its 128 MiB resource budget can stall the
client.

The same frame priority-retains the exact M13 `overview_02/all/huan` six-index
VFXBaseV2 pair. EndfieldCapture computes BC block rows, copies each SRV-selected
mip into a one-subresource staging texture, and records its complete descriptor.
Session `20260826T142935Z`, frame 2383, closed all five exact BC7 SRVs and the
unique 240-byte dynamic quad, but correctly failed admission because PS b3
stopped at c35. Corrected session `20260826T144934Z`, frame 5404, retains the
full distinct backing allocations for VS b0-b4 and PS b0-b3 through c49, the
five BC7 SRVs, and the unique current quad. The hash-pinned packet generator
now publishes those complete constants, textures, shader bytecode, vertices,
and indices to the native D3D11 path. WARP creates both shaders, the exact input
layout, and a captured BC7 resource. A synchronized 4.50-second Viewer capture
then reports a nonzero native draw count, zero callback failures, `S_OK`, and
`targeted_ok`; submitting the plugin event alone is not accepted as validation.
The compatibility M13 renderer is suppressed only inside the captured
4.375-4.625-second window and restored outside it. The older FrameAnalysis peak
also proves its billboard carries authored RGBA
`(1, 0.2862745, 0.0235294, 0.0862745)`, agreeing with the generated particle
contract. The conspicuous actor-only ring is therefore not evidence for
arbitrary attenuation. No further M13 or M14 graphics capture is needed.
Capture admission remains separate and fail-closed: M13 requires the exact
shader pair, complete constant allocations, all five textures, and unique
geometry, while M27 requires all 82 VS b0 vectors through c81. The legacy HLSL
sidecar keeps its separate old-layout bindings as the visual fallback.

M14 `overview_02/all/tuowei` no longer has a shader-identity gate. Capture
`20260826T000901Z` closes its exact VS4914/PS4915 pair, all used constant ranges,
the phase-matched 285-quad 36-byte particle stream, and its native BC7 texture
mip chain. A
dedicated Unity 8/7-to-7/2 ABI shell is now stage+SHA pinned; WARP creates both
retail objects and a live Unity reserved-variant run reports four deterministic
substitutions (two imports per stage), balanced VS/PS swaps, and zero failures.
The opt-in D3D11 runtime transport is also live: it binds stage-specific captured
buffers, the zero skin carrier, scene depth, and the exact texture, then draws
the captured stream into SceneColor/SceneMV with `One, OneMinusSrcAlpha`.
FrameAnalysis draw 115 closes the otherwise ambiguous input layout: layout
`48fadbbd` aliases the slot-0 UV at byte 28 into TEXCOORD0/1/4 and reads packed
zero blend indices/weights from a 20-byte slot-1 buffer submitted with stride
zero. The native plugin reproduces that layout, passes WARP creation, and a
matched 4.50-second exact-versus-suppressed run visibly isolates the dense amber
segmented/smoky trail around the raised hand while retaining M13's outer ring.

Sequence capture `20260826T091023Z` extends that closure across seven complete
exact-pair packets at game frames 1405-1453. The packets are sampled at 0.25 s
cadence and contain dynamic 328, 480, 477, 415, 346, 277, and 216-quad streams,
with independently retained stage-specific constants. Holding the old 285-quad
packet across time was disproved: its strong contribution collapsed after two
samples because its captured camera/particle state was valid at only one
instant. The opt-in native path now creates all seven immutable packets, anchors
their phase to the Overview-start epoch, selects the nearest packet only inside
the evidenced 4.375-6.125 s window, and restores the compatibility renderer
outside it. It continues through the body transition even after Unity retires
the source particle renderer, matching the captured effect lifetime boundary.
A seven-sample D3D11 exact/suppressed run completes with no native failures and
shows the intended ring/trail burst decaying to sparse amber fragments instead
of freezing one geometry packet. The measured no-frame-generation A/B now
admits this path in the canonical Endminf profile; no further M14 graphics
capture is currently needed.

The later continuous session `20260826T162514Z` adds nine M14 packets with
1,872, 2,898, 2,898, 2,874, 2,628, 2,328, 2,058, 1,782, and 1,584 indices.
Their provisional phase labels inherited M27's stale frame-2905 anchor and were
rejected by a retail A/B: replay at 5.72-6.80 seconds worsened every UI-free
metric. The authoritative no-frame-generation peak instead pins the session's
frame 2978 to body phase 4.433333 seconds/source frame 381. Presented-frame
deltas place the nine packets at 4.433333-5.516666 seconds, interleaving them
with the older coarse checkpoints; the dense packet owns the exact duplicate
at 5.25 seconds. The same correction reanchors M27 frame 2905 from 4.50 to
3.216666 seconds and its 1,080-index frame 2978 to 4.433333 seconds. The
zero-draw frame 2970 is now accepted as an exact successful callback rather
than misclassified as a failed submission. A synchronized 21-frame D3D11 run
validates all M14/M27 callbacks, preserves the grey background and portrait
with no foreground UI, and improves baseline effect-ROI MAE from 42.9247 to
42.4441. The stale-label render was microscopically lower at 42.4235, but that
accidental metric difference does not override the direct peak registration.

The same continuous session retains the complete shared LitEffect shader-pair
sequence, not only the owner previously labelled M27: 38 phase packets contain
157 M01/M38/M27 draws from 0.15 through 5.25 seconds, with at most six draws in
one packet. The generated native payload now submits every retained draw and
the managed validator checks the exact per-frame counter delta, including the
intentional zero-draw packet. D3D11 probes at 0.15, 0.50, 1.00, 2.00, 2.80,
3.00, 3.2167, 4.30, 4.4333, and 5.25 seconds validate the 3/4/5/6/0/1-draw
families without drift. The 21-frame UI-free dense render remains byte-identical
to the prior M27-only replay and therefore keeps ROI MAE 34.3644, effect-ROI
MAE 42.4441, and effect temporal-delta MAE 30.8086. This is a stronger exact
transport boundary but not a claimed visual improvement: the additional rows
are currently hidden or rejected by the recovered depth/composite path. All
validation renders include the grey CharInfo gameplay field and actor portrait
and exclude the foreground UI overlay.

The canonical Viewer capture now retains the physical SphereOutside-resolved
grey CharInfo field and the actor-specific background portrait while excluding
all foreground UI. A one-frame 3840x2160 probe at requested 4.4667 seconds
passed the same exact M27/SphereOutside gates and, after Lanczos reduction to
1920x1080, improved the UI-free retail ROI PSNR from 14.4202 to 14.5289 dB.
Native resolution is therefore a real but small presentation contributor, not
the dominant crystal/VFX gap. The source-backed radial/chromatic kernel is
already stronger than retail when sampled at its actual 4.4667-second post
peak; do not increase blur or bloom to compensate. On the 21-frame UI-free
no-frame-generation window, enabling the already validated exact M13 and
then-seven-packet M14 transports improved mean ROI MAE from 34.6230 to 34.3530,
effect-ROI MAE from 42.9247 to 42.4235, and effect temporal-delta MAE from
30.8982 to 30.7600. They are therefore part of the canonical Endminf
reproduction profile. Their remaining coarse packet cadence is not a reason to
retune bloom; the largest unclosed early shape is the compact M29/M30
flash/glow, while M13 owns the late outer ring and M14 the segmented trail. The
higher-value boundary is
the still-unclosed retail temporal/upscaler state and its phase relationship to
the late effect pulse. Focused verifier-only resolution overrides are available
through paired `ENDFIELD_ENDMINF_CAPTURE_WIDTH` and
`ENDFIELD_ENDMINF_CAPTURE_HEIGHT`; canonical captures remain 1920x1080.

Viewer reports now distinguish requested composition from observed renderer
state. Every capture mode, including targeted diagnostics, fails if the active
recovered grey-field renderer or the exact Endminf portrait mesh/material is
missing; foreground screen-space UI remains outside the camera render. A fresh
one-frame D3D11 pulse probe passed both observed gates, the physical
SphereOutside gate, and the no-foreground-UI contract. Disabling the partial
temporal resolve changes that pulse frame by only 1.21 mean RGB levels and does
not remove its broad multicolour pull. The dominant over-warp was instead a
coordinate-space translation defect: the compatibility clock returned signed
viewport coordinates for ordinary on-screen centers even though the Uber
consumer subtracts a 0..1 UV. The corrected runtime keeps the ordinary center
in viewport space and uses signed space only for the native far-offscreen
normalization test. At body phase 4.4667 seconds it publishes
`(0.509934, 0.532675)`, within 0.00024 of the retained retail Uber-shaped ring
candidate `(0.509984, 0.532905)`. The same 21-frame UI-free comparison improves
ROI MAE from 34.3644 to 29.8231, effect-ROI MAE from 42.4441 to 34.6499, and
effect temporal-delta MAE from 30.8086 to 27.3592. A controlled mode-3 replay
is worse on all three metrics (30.5015, 35.3130, and 28.4171), so the pinned
native producer's combined mode 6 remains canonical; the unbound ring's mode-3
lane is not admitted as draw state. The remaining mismatch is the exact shipped
Uber presentation/binding ABI plus effect shape, not hair/cape geometry or the
required background layers. Direct disassembly of exact combined fragment
`3f490e1504c43554...` confirms the compatibility helper's distance exponent,
mode threshold, nine mode-6 taps, mode-3 taps, LOD-0 source sampling, and
separate bloom sample. The fragment does not consume `_ScreenSize`, so neither
an aspect correction nor further kernel tuning is evidence-backed.
The same retained Uber draw binds a full-resolution
`R16G16B16A16_FLOAT` source `t0`, while the recovered physical sceneColor
owner correctly remains packed `B10G11R11_UFloatPack32`. The canonical
Endminf path now performs the missing RGBA16F post handoff after temporal
resolve and uses it for both bloom prefiltering and Uber. The 21-frame A/B
improves ROI MAE from 29.8231 to 29.7657, effect-ROI MAE from 34.6499 to
34.5757, and temporal-delta MAE from 27.3592 to 27.1143. Capture reports record
the live post-source format and fail if the Endminf reproduction does not
observe RGBA16F; this promotion does not replace the separately proven packed
pre-post CameraColor owner.
The retained Uber `t1` descriptor separately proves a 1920x1080
`R11G11B10_FLOAT` reconstructed bloom input for the 3840x2160 source. The
recovered bloom pyramid now uses that explicit packed format instead of
platform `DefaultHDR`, and Viewer reports fail if the live binding regresses.
Its dense comparison moves ROI/effect-ROI/temporal MAE from
29.7657/34.5757/27.1143 to 29.8295/34.6175/27.1543. That small regression does
not override the direct resource descriptor; it indicates remaining upstream
effect-shape/timing differences can still dominate whole-ROI scores.

The active task is to reconstruct these missing frame systems from recovered
assets and measure the resulting Endminf frame against the reference video.
M13, M14, and M27 packet capture/admission and temporal native replay are now
closed, and the latest capture also proves neutral retail exposure. Measure the
complete crystal/VFX sequence with a retail-like neutral composition against
the no-frame-generation reference, close the remaining bloom/compositing and
non-M27 effect-shape differences, then return to body, hair, and cloth polish.
The largest early unclosed shape is M29/M30 around no-frame-generation source
frames 376-385. Session `20260826T162514Z` identifies M29 by exact pair
`CE755059DEDDC2E0/F2AD2A14856044AC`, 1,386 indices, and its PS b3 c1/c4
fingerprint; M30 uses `62A5CE6C09171DE9/5558DEDDB1EE6188`, 6/12 indices, and
a separate b3 fingerprint. That session did not retain their own draw-time IA
or PS SRVs, so it supports source-assisted reconstruction but not exact replay.
EndfieldCapture now priority-retains M29's pair plus full bound constant
allocations, IA, and t0-t5, and retains IA/t0-t5 for the shared M14/M30 pair.
Session `20260826T231348Z` contains two targeted sequences and closes the
temporal constant side: each sequence retains the 13 exact 1,386-index M29
packets, and raw `bindings.v1.bin` preserves all nine VS/PS constant slices,
including complete PS b3. The combined-runtime JSON writer had omitted those
already captured slices, so it now emits the same constant-buffer and
fullscreen-resolver records as the graphics-only writer. This session does not
close texture replay: 110 of 111 frames reached the 32-resource selector cap,
because repeated unsupported exact-pair PS slots consumed ten records before
later M29/M30 textures. The narrow exact-pair selector now skips zero-byte
unsupported resources. Retained draw records now also carry their own bounded
IA/PS resource observations, keyed to the frame-wide selected payload records;
this removes the ownership ambiguity that remained even when a texture blob
survived. The WARP test covers PS slot plus IA/index ownership. The fail-closed
`verify_endminf_m29_m30_capture_completeness.py` gate rejects truncation,
missing constants, missing draw ownership, and missing byte-bearing payloads;
it rejects `20260826T231348Z` at its 110 truncated frames. The Release
`build-local` and all 15 tests pass. One new bounded `graphics targeted`
sequence over reference frames 376-385 remains required to close owner-specific
IA/t0-t5. Full/everything capture is not required for that focused rerun.

The pre-patch session is now covered by a fail-closed M29/M30 temporal
verifier. It identifies 13 M29 packets at 2.5333-4.1667 seconds and 11 M30
packets at 2.8000-4.1667 seconds using shader pair plus exact PS b3 c1/c4
fingerprints, rather than index count alone. M29 is always a one-instance
1,386-index Sphere001 draw; M30 is a one-instance 6/12-index billboard draw.
Both captured c4 values exactly equal the linear upload of the generated
materials' authored `_TintColor`, while c1 matches their authored intensity
and alpha, so no tint retuning is authorized. The report remains explicitly
`validated_source_assisted_only`: selected IA belongs to another retained
carrier and neither owner has its own PS t0-t5 closure. A current 21-frame
UI-free/no-frame-generation ablation with the grey field and portrait proves
that both source-assisted owners should remain enabled. Excluding M29 worsens
effect-ROI MAE from 42.4441 to 42.4787; excluding M30 worsens it to 42.5368
and also worsens temporal-delta MAE from 30.8086 to 30.8190. Exact replay still
waits on the focused post-patch capture; the compatibility result is measured,
not treated as completion.

## Main animation gap

The remaining runtime systems are generalized controller and rotation-only
root-motion routing beyond the certified Endminf path, broader Avatar
transport, grounding and IK, facial emotion/lip sync, gaze, secondary motion
outside the certified positive-scale stationary Endminf subset,
remaining item/deco/FX lifecycle, gacha timing, and non-playable runtime
assembly.

These are implementation gaps, not reasons to weaken the recovered evidence
boundary. Static prefabs and isolated clip playback must remain labeled as
such.

## Maintained workflow

```bat
cd unity_endfield_graph_shader_lab
.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
```

Canonical scene:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated assets are rebuildable. Change generators, importers, runtime code,
or shaders rather than hand-editing generated prefabs.

## Recovery queue

1. Close the public-Unity Uber presentation/binding and retail temporal/upscaler
   boundary now that the late-pulse center, combined mode, and exact kernel are
   measured, then
   compare the resulting background+portrait+actor/VFX 770-frame output against
   the no-frame-generation recording with foreground UI masked out. Keep the
   source-backed bloom/material values fixed unless new evidence supersedes
   their current contracts.
2. Close Endminf secondary motion against the joined retail shape oracle from
   EndfieldCapture session `20260825T191720Z`. Its 40 complete frames each
   contain 32 valid draw-time b2 snapshots with no dropped/incomplete/failed
   package. `8e65872` preserves the exact 16-byte row consumed by each retained
   draw in a bounded 512-byte GPU copy; all 14 Release tests and 30 consecutive
   multi-capture stress runs pass. Confirmed skinning draws bind all 4096 b2
   constants; same-index-count 16-constant passes are separate non-skin
   submissions and must remain excluded.
   `unity_endfield_graph_shader_lab/tools/decode_endminf_endfield_capture_skinning.py`
   performs that join for the exact body, cloth-01, cloth-03, cloth-04, and
   hair LOD0 index/bindpose counts. It accepts repeated 4096-constant skinning
   passes only when their draw-time current/previous palette pair agrees and
   fails closed on older packages without the snapshot. The resulting
   owner-tagged trajectory oracle is now the phase-paired comparison target for
   the default-off solver. The baseline comparison is complete: entrance
   checkpoints contain the large trajectory gap, while the settled loop is
   already near retail. A synchronized 40-frame solver-writeback A/B is also
   complete and rejects the current diagnostic solver: it worsens translation
   at all 40 checkpoints, with owner means increasing from 0.0137-0.0286 m to
   0.0170-0.0872 m and rotation means increasing from 7.0-8.6 degrees to
   15.6-22.7 degrees. The persistent settled-loop offset begins in solver state,
   not from a local/world mismatch in the publication adapter, so the solver
   remains disabled and must not be parameter-tuned around this error. The
   generated A/B is
   `reports/assets/character_recovery/endminf_secondary_dynamics_solver_trajectory_comparison.json`.
   Session `20260826T231348Z` directly certifies the four owners' world-relative
   mode: one bounded window observed 155 teams across 617 cloth updates with
   every relative flag false and no unreadable/overflow calls. It does not
   contain owner matrices or particle trajectories, so repeating the current
   `Numpad 5` window cannot provide exact two-animation replay data. Extend the
   dynamics provider to retain bounded per-owner transforms/positions and
   validate that payload synthetically before requesting another game capture.
3. Generalize the finished Endminf path and rebuild every playable character
   without actor-specific renderer forks.
4. Keep changing inventories and exhaustive validation output under
   `reports/assets/character_recovery/`; update this file only when the durable
   conclusion or evidence boundary changes.

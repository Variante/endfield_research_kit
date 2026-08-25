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
  does not by itself certify the recovered solver. Deterministic Unity capture
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
  This remains a non-exact forward LitEffect compatibility layer; its exact
  five-MRT HGBuffer publication and deferred consumer remain fail-closed. No
  crystal retiming, scale change, or bloom tuning was admitted.
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
  evidence for combined velocity. The transient combined-output format and
  direct producer attachment remain open. The same-frame reset is exactly large de-jittered camera
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
  gyroscope transition, lowers the same MAE to 22.3254. The whole `_02` owner,
  not only its post components, has that age: the compatibility spawner now
  advances each
  particle system by the same nine discrete 60 Hz ticks before playback.
  A focused source-frame 372-396 comparison moves M13 and M21 from their
  former nine-frame-late peak to the retail burst window; the subsequent
  41-frame D3D11 capture passes entrance VFX, cleanup, start-to-loop handoff,
  and settled-loop gates. At the body-matched retail frame 382 this replaces
  the former opaque peak ring with the late crystal cloud and residual glow,
  without changing M13/M21 delay, scale, material, or emission data. The five
  retained retail FrameAnalysis snapshots also expose
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
  `GBuffer` admission. The exact path remains fail-closed because numeric active
  constant-buffer ranges, selected-frame AnchorWaveBright, terrain profile,
  and a presented content-valid deferred consumer are not yet closed.
  Current-build native evidence now proves that AnchorWaveBright c105
  is `(position.x, position.y, radius, intensity * enabledFlag)` and is published
  verbatim to the global constant buffer; its zero construction default is not
  a selected-frame fact. The current-build terrain
  profile producer is now bounded further: a reserved zero-key dictionary maps
  to float(index + 1), with zero meaning no registered terrain profile. Its
  CharInfo selected-frame value remains unobserved, so canonical M27 still must
  not assume zero.
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
  either renderer. M21, exact `suikuai (1)`, and M27's exact HGBuffer boundary
  remain unchanged.
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
  The frame analyses contain the selected M27 HGBuffer pair
  and close its one-instance, engine-expanded particle topology. Its numeric
  active constant-buffer slices, optional-skin gate, five-attachment publication,
  and presented deferred consumer remain open. EndfieldCapture session
  `20260825T161654Z` cannot close them because its targeted graphics profile
  deliberately omits retail instanced draws. Do not compensate by resizing,
  brightening, retiming, or disabling M21.
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
For the current Endminf deliverable, retail UI and CharInfo presentation layers
are reference-only evidence: Unity renders the main character and her spawned
visual effects against a plain clear target.

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

The exact-build secondary-dynamics session at
`scratch/reverse_engineering/endfield_capture/20260825T125815Z` observes
`UseCrossFrameJob=true` and exclusively false `useRelativeTransform` reads,
but does not identify the four Endminf TeamData owners; its own summary records
`endminfFourOwnerCertification=false`. A 770-frame diagnostic run of the
recovered four-owner solver/coordinator and source-ordered TransformAccess
publication proved bounded execution but failed visible retail-shape review:
during the entrance it inflated the cape into a broad rigid sheet and degraded
hanging-strip/hair silhouettes. Solver writeback is therefore diagnostic-only,
default-off, and session-uncertified until an owner-identity join and a
phase-paired retail shape gate both pass. Normal actor/VFX reproduction retains
the authored baseline; entrance VFX, cleanup, and rotation-only root motion
remain active.

The captured skinning oracle now supplies the phase-sequenced retail shape
target, and the deterministic owner-path comparison confirms that the authored
baseline is already close in the settled loop but diverges substantially during
the entrance. The recovered solver still fails closed because session
`20260825T125815Z` did not certify the four Endminf TeamData identities. The
remaining admission evidence is one bounded Endminf `Numpad 5` dynamics window
that either isolates the four owners or records the current collector's bounded
universal-false coverage while confirming the maintained cross-frame route.
The native contract already closes ordinary Transform reads and TransformAccess
writes; do not bypass the session gate or enable writeback from the graphics
oracle alone.

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
- the exact `_CombinedVelocity` allocation format used by the recovered
  Streamline DLAA velocity-combine dispatch. The pinned retail helper has no
  credible stock Unity/PDB equivalent, and its later `0x2d` virtual-call
  argument has no statically recoverable enum domain. Keep the native proxy
  disabled until a D3D11/RenderDoc resource descriptor proves the format.

`SphereOutside` is asset-complete. Its remaining gates are runtime frame state
and resources. The exact deferred program is no longer a blocker.

The active task is to reconstruct these missing frame systems from recovered
assets and measure the resulting Endminf frame against the reference video.
An original-client GPU capture would improve exact resource binding later, but
its absence no longer pauses the Unity reproduction work.

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

1. Compare the actor/VFX-only 770-frame Endminf output against the
   no-frame-generation recording with retail UI masked out, then close the
   remaining camera, effect-shape, and material differences.
2. Reproduce the complete Endminf Character Info frame against the reference
   video, closing the presentation scene before further isolated shader work.
3. Close Endminf secondary motion against the joined retail shape oracle from
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
   already near retail. No additional graphics capture is needed. One new
   `dynamics`-profile `Numpad 5` window is required to certify Endminf through
   either direct four-owner isolation or the maintained bounded universal-false
   coverage before solver writeback can be tested.
4. Generalize the finished Endminf path and rebuild every playable character
   without actor-specific renderer forks.
5. Keep changing inventories and exhaustive validation output under
   `reports/assets/character_recovery/`; update this file only when the durable
   conclusion or evidence boundary changes.

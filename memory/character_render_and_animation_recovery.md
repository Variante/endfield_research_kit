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
  rotation-only root-motion, 67-renderer admission, and exact three-row
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
- Endminf's overview rock/crystal animation now combines the exact retained
  transform clip with four source-resolved `GameObject.m_IsActive` curves.
  They remain active through 1.5 seconds and deactivate on the source boundary.
  The fifth constant-zero binding has no resolved hierarchy target and remains
  fail-closed rather than being fabricated.
- The canonical capture now restores the ten retained physical rock renderers
  that were absent from the previous sheet: seven M01 rows and three M38 rows,
  all keyed by exact renderer/material PathIDs and the exact
  `S_rock_small_1_017_02_lod2` mesh. Direct references are validated against
  pinned asset hashes, the default remains disabled/fail-closed, and only
  `ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1` activates them. Capture schema
  v4 proves 67 admitted entrance renderers and exactly three separately blocked
  rows (one secondary LitEffect and two M28 VFXRefract rows). This restores the amber
  faceted stone/chunks but remains a non-exact forward LitEffect compatibility
  layer; do not treat its emission, lighting, or whole-frame MAE as retail
  HGBuffer parity. Both references support the existing spawn, 1.5-second
  nanguan visibility, hand-focus, peak-burst, and state-exit cleanup cadence,
  so no crystal retiming or bloom tuning was admitted in this batch.
- The no-frame-generation reference makes two stone systems distinguishable:
  the ten LitEffect M01/M38 rows are the early fly-in faceted rocks, while the
  later raised-hand glow/particles are separate BaseV2 renderers and must not
  be calibrated as one material. A refreshed, hash-pinned LitEffect export now
  recovers the selected HGBuffer fragment's 576-byte `UnityPerMaterial` table
  and exact offsets for all 17 parallax fields used through the 496-byte b3
  prefix (including `_ParallaxColor` at byte 464 and its dark color at 480).
  This closes the selected physical b3 slice, not visual admission. Selected-
  frame b1 VFX globals, b2 per-draw history/LOD state, the selected b4 value,
  `ParserBindChannels`, complete HGBuffer frame publication, and the visibly
  over-bright raised-hand glow remain fail-closed; do not tune the non-exact
  compatibility shader against the video.
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
  gyroscope transition, lowers the same MAE to 22.3254. Actor SceneMV coverage
  and the source blank-frame history boundary lower the comparison to 22.3102;
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
  at t23/t24/t25. The ten rock renderers remain blocked only on live retail
  global/per-draw completeness and the complete deferred frame, not material
  layout or buffer identity. The exact remaining constant inputs are bounded to
  ShaderVariablesGlobal c27.y and live AnchorWaveBright c105.z/w, validated
  UnityPerDraw history/LOD state, and terrain subsurface profile c0.w.
  For Endminf M27 specifically, the unique selected D3D11 pair is HGBuffer
  source subprogram 19 with `HG_ENABLE_MV,_PARALLAX_MAP`; its retained particle
  streams already match Position/Normal/Color/UV/UV2/Custom1XYZW. The first
  valid pipeline change is an M27-PathID-only five-MRT owner before deferred
  resolve, never global `GBuffer` admission. It remains fail-closed because the
  selected-frame AnchorWaveBright value, per-draw/instance history, terrain
  profile value, and a presented content-valid deferred consumer are not yet
  closed. Current-build native evidence now proves that AnchorWaveBright c105
  is `(position.x, position.y, radius, intensity * enabledFlag)` and is published
  verbatim to the global constant buffer; its zero construction default is not
  a selected-frame fact. The current-build terrain
  profile producer is now bounded further: a reserved zero-key dictionary maps
  to float(index + 1), with zero meaning no registered terrain profile. Its
  CharInfo selected-frame value remains unobserved, so canonical M27 still must
  not assume zero.
- The two remaining M28 `VFXRefract` rows stay fail-closed even though the
  Distortion SceneColor/SceneMV/depth compositor topology is available. Exact
  current-build recovery now closes the material and both unrounded
  GameObject/Transform/ParticleSystem/Renderer tuples, including source-enabled
  state, Sphere001, GPU instancing, and streams `[0,1,3,4,5,34]`. Both complete
  D3D11 program pairs (0090/0091 non-instanced and 0624/0625 SRP-instanced) are
  hash-, signature-, resource-, instruction-, and two-MRT-equation-pinned.
  Four compatibility-fragment differences collapse for this exact material's
  fixed values, but that does not select the retail pair or prove the engine
  BLEND/TEXCOORD4/instance publisher, LOD/time/frame resources, descriptors,
  attachments, or PSO. Current-build `UnityPlayer.dll` now proves
  `SRP_INSTANCING_ON` is HyperGryph built-in keyword ordinal 30, and the exact
  instanced pair directly indexes 256-byte records for instance IDs 0-255 with
  no shader-side base. The body-hashed native registry/accessor path seeds only
  stereo built-ins 35/33/36/37 by default; it does not seed ordinal 30. An
  apparent `bts ..., 0x1e` site is instead mutually exclusive high-bit encoding
  of a dynamic keyword ID, not a built-in keyword-set write. The sole audited
  default-set caller closes the actual keyword storage as an inline-or-heap
  bitset at owner offsets `0x100`/`0x118`; names are first resolved to internal
  16-bit IDs, so immediate ordinal-30 or `0x40000000` searches cannot identify
  the draw publisher. The ordinal table is registration-only. Selection and
  the per-instance publisher therefore require a live D3D11 draw capture;
  GPU-instancing state, registry ownership, and the one-particle batch are not
  substitutes. Admission still requires that capture plus both fixed-control
  60 Hz windows; M21, exact `suikuai (1)`, and M27 must remain unchanged.
  Recovery is now intentionally bounded to offline evidence: no retail client
  launch, attachment, or injection is permitted. A local Endminf-specific
  D3D11 standalone and RenderDoc census proves that the `_03` M28 source is
  instantiated and alive at `particleTime=0.320262` with one particle while
  its fail-closed renderer remains disabled and material-less. The fixed M21
  crystal and exact `suikuai (1)` controls remain enabled with their expected
  materials, and M27 remains unchanged and fail-closed. This local capture is
  not retail draw evidence: its shared CharEffect, physical-HDR/SceneMV,
  post-Uber world-UI, and ShadowPlane target paths are incomplete. Static
  binaries, serialized assets, recovered programs, video, and this local draw
  therefore exhaust the allowed evidence. Retail pair selection, per-instance
  publication, live descriptors/attachments/PSO, and selected M28 pixels are
  the irreducible boundary; M28 must remain blocked rather than inferred.
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
  former oversized chromatic triangles. The generated sequence now reports 67
  admitted renderers. `suikuai (2)` remains separately fail-closed: its
  LitEffect material disables ForwardOnly and selects the five-MRT deferred
  HGBuffer program, while the compatibility shader is a one-target ForwardOnly
  stand-in. Recover that deferred consumer for the remaining physical fragments;
  do not compensate by resizing, brightening, retiming, or disabling M21.
- Blink, facial, physical-transform, CharacterNPR, eye, hair, shadow, GBuffer,
  light, cookie, irradiance, particle, gacha, and post-processing behavior is
  recovered only where its input contract is verified. Unknown inputs remain
  explicit gaps.
- Four new neutral D3D11 `ui_overview_start`/loop frame analyses now pin the
  live Endminf body producer as a five-color-target draw over D32S8: scene
  color, scene motion, GBuffer A/B, and GBuffer C. The Unity deferred-sidecar
  formats and depth ownership agree with this boundary. The capture does not
  yet source-join that build-specific shader/material binding to the recovered
  body shader, so it strengthens the producer contract but does not authorize
  global GBuffer admission or a guessed material change.
  Across the four newest captures the draw remains 27,615 indices with the
  same build-specific VS/PS pair; only its event number shifts as transient
  setup draws vary. Treat this as a stable Endminf presentation boundary, not
  a one-frame artifact. The full event/resource matrix is in
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
  The two former Collider End ABI-shape candidates are now both rejected by
  their pinned AVX2/SSE2 cores: one uses 12-byte float3 positions where the
  canonical job requires 24-byte double3, and the other treats its first lane
  as a scalar while operating on 184-byte records. The filter therefore has no
  semantic survivor; runtime GetProcAddress telemetry remains the exact
  identity gate instead of assigning either hash.
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
  while the three disposable target-filter inputs are absent. The complete
  solver numerics remain open; do not replace them with a simple spring/gravity
  surrogate;
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

Do not fork the renderer per actor. Endminf-specific code may own source asset
selection and timing, while the importer, material mapping, animation,
presentation scene, and render pipeline must remain reusable for the eventual
all-character rebuild.

## Main rendering gap

The blocking gap is the complete CharInfo physical presentation frame, not
another per-material shader approximation. The missing boundary includes:

- the real `SphereOutside` and `ShadowPlane` scene participation;
- the exact character stencil writer and receiver integration;
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
root-motion routing, broader Avatar transport, grounding and IK, facial
emotion/lip sync, gaze, secondary motion, cloth/hair dynamics,
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

1. Reproduce the complete Endminf Character Info frame against the reference
   video, closing the presentation scene before further isolated shader work.
2. Generalize Endminf's proven Animator path from source contracts, close the
   root-motion compatibility boundary, then prioritize IK, facial systems, and
   secondary motion.
3. Generalize the finished Endminf path and rebuild every playable character
   without actor-specific renderer forks.
4. Keep changing inventories and exhaustive validation output under
   `reports/assets/character_recovery/`; update this file only when the durable
   conclusion or evidence boundary changes.

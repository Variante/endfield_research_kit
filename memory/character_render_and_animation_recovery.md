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
  interruption ordering. A 41-frame 60 Hz Viewer capture proves controller
  entry, the transition, settled looping, four entrance-effect roots, and
  effect cleanup. Its AnimatorMove path now follows the pinned native consumer:
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
- The focused Endminf comparison now anchors its first saved Unity frame
  directly to retail frame 1110, the first visible body frame. The former map
  added the already-advanced 0.0509083-second body phase a second time and put
  every retail sample three frames late. The latest D3D12 capture maps frames
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
  four diagonals. These packed resources are not yet fed to the partial beauty
  resolve: that consumer still expects raw SceneMV B, while retail reads
  normalized 10-bit flags. Packed-flag/mask resolve consumption, complete
  resolve policy, jitter, fast convergence, live IFix selection, the retail
  first-frame auxiliary clear payload, and
  constructor-seeded constant lanes remain open.
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
- The `M_fx_endminm_gfx_09` burst stripes now bind the exact exported RGBA
  `T_fx_star_07_D` payload. The previous missing `_MainTex` silently sampled
  white and produced a large opaque rectangle; the repaired source-alpha
  binding restores the narrow retail-like horizontal streaks without a shader
  tuning constant.
- Blink, facial, physical-transform, CharacterNPR, eye, hair, shadow, GBuffer,
  light, cookie, irradiance, particle, gacha, and post-processing behavior is
  recovered only where its input contract is verified. Unknown inputs remain
  explicit gaps.
- The selected deferred resolver DXBC has a compile-valid Unity HLSL port. It
  matches the neutral fixture exactly and the recovered Wulfa fixture within
  one float ULP. This proves executable program and recovered-input
  equivalence; it does not prove the retail frame resources.
- D3D12 diagnostic capture proves canonical light/reflection binning,
  VisibilitySH, and SphereOutside's exact five-MRT sidecars can populate during
  the full Endminf sequence without changing any of the 41 presented beauty
  frames. The exact DXBC consumer remains D3D11-only and its private float
  readback is intentionally non-presented; those sidecars are evidence, not a
  hidden beauty path.
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
  when those inputs are absent; exact retail scheduling and the complete
  numeric solver are still unproven. Endminf's MC_Coat payload closes its
  particles, transforms, lines, roots, capsules, and active constraint feature
  set, but 35 proxy/prebuild arrays still lack proven strides and element
  semantics; do not replace that gap with a simple spring/gravity surrogate;
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
`videos/2026-08-21_20-15-17.mkv` used by the focused Endminf comparison path.
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
- exact retail D3D12 presentation binding after the now-closed Effect-02
  combined Uber source, bloom, LUT, and output-tail contract;
- the full TAA producer/consumer chain beyond the now-complete actor SceneMV
  MRT coverage, recorded blank-frame history boundary, and recovered Dilation
  auxiliary-history producer.

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

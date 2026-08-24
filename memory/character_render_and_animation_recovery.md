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
  effect cleanup. Stock Unity 2022.3 does not serialize the retail
  per-transition `m_EnableBlendRootMotion` field; the recovered true value is
  currently mapped to Animator-level root-motion execution and remains an
  explicit compatibility boundary.
- Endminf's overview rock/crystal animation now combines the exact retained
  transform clip with four source-resolved `GameObject.m_IsActive` curves.
  They remain active through 1.5 seconds and deactivate on the source boundary.
  The fifth constant-zero binding has no resolved hierarchy target and remains
  fail-closed rather than being fabricated.
- Blink, facial, physical-transform, CharacterNPR, eye, hair, shadow, GBuffer,
  light, cookie, irradiance, particle, gacha, and post-processing behavior is
  recovered only where its input contract is verified. Unknown inputs remain
  explicit gaps.
- The selected deferred resolver DXBC has a compile-valid Unity HLSL port. It
  matches the neutral fixture exactly and the recovered Wulfa fixture within
  one float ULP. This proves executable program and recovered-input
  equivalence; it does not prove the retail frame resources.
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
  numeric solver are still unproven;
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
at 60 fps) and continues through the recording end.

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

`SphereOutside` is asset-complete. Its remaining gates are runtime frame state
and resources. The exact deferred program is no longer a blocker.

The active task is to reconstruct these missing frame systems from recovered
assets and measure the resulting Endminf frame against the reference video.
An original-client GPU capture would improve exact resource binding later, but
its absence no longer pauses the Unity reproduction work.

## Main animation gap

The remaining runtime systems are generalized controller routing, exact
per-transition root-motion semantics, broader Avatar transport, grounding and
IK, facial emotion/lip sync, gaze, secondary motion, cloth/hair dynamics,
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

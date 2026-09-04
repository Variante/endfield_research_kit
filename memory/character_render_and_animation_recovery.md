# Character rendering and animation recovery

This topic owns the durable recovery model for the optional Unity reconstruction
lab. It is not a WebUI page guide and no normal WebUI/export workflow depends on
the lab, 3DMigoto, or EndfieldCapture.

## Why this file remains

The Characters page catalogs identities and assets. The reconstruction lab has
a different goal: reproduce one retail Character Info render closely enough to
validate reusable model, animation, material, lighting, post-processing, VFX,
and secondary-dynamics contracts. Those parity rules and observation gates need
an independent source of truth.

## Current target

Endminf is the sole active reference actor. The lab first closes her Character
Info entrance and loop, then applies only character-neutral contracts to the
other playable characters.

Current durable state:

- all playable models have a renderable static baseline;
- canonical post-model identities have generated prefab paths, while modular
  NPC kits remain source kits rather than reconstructed characters;
- Endminf's selected Character Info camera, lighting, profile, model,
  materials, textures, UI clips, entry/loop controller, root-rotation behavior,
  and major entrance effects are source-backed;
- selected CharacterNPR/HGRP frame equations and resources are partial;
- retail visual parity is not reached;
- the main silhouette gap is secondary cloth/bone simulation and history, not
  a license to hand-author mesh, pose, or camera corrections.

Changing actor counts, shader hashes, frame metrics, session ids, and capture
inventories belong in `reports/assets/character_recovery/`.

## Maintained ownership

| Area | Owner |
| --- | --- |
| Lab workflow and generated Unity assets | `endfield_reconstruction_lab/` |
| Extracted Unity objects and conversion quality | `tools/AnimeStudio/` |
| Static semantic asset identities | `memory/asset_recovery.md` and Assets reports |
| Retail graphics capture | maintained 3DMigoto fork and its operator guide |
| Exact-build runtime observation | `tools/EndfieldCapture/` |
| Per-build proof and measurements | `reports/assets/character_recovery/` |
| Raw/revisitable sessions | `scratch/character_recovery/` and `scratch/reverse_engineering/endfield_capture/` |

The disabled-by-default Character Info ground-truth preset and operator guide
live under `tools/3Dmigoto-AE/Mods/DISABLED-GroundTruthNoUI/`. The lab links to
that owner and must not copy its build-specific shader catalog.

## Evidence hierarchy

From strongest to weakest:

1. exact serialized object, PPtr, controller, clip, or shader resource;
2. selected-build native consumer with validated hashes and bounded fields;
3. complete observation session with provider request, terminal summary, no
   dropped evidence, and exact actor/frame/surface join;
4. deterministic Unity reproduction using the recovered inputs;
5. image comparison or visual similarity.

A lower layer can identify a useful gap but cannot upgrade the layer above it.
In particular, a lower image delta does not prove the retail producer, shader
variant, scheduling path, or runtime value.

All native and capture paths fail closed. Missing modules, mismatched hashes,
hook errors, lost events, incomplete provider summaries, client crashes,
ambiguous identities, or stale option associations make the session diagnostic
only.

## Model and prefab boundary

- Canonical identity, renderable model, runtime prefab, and active scene actor
  are different claims.
- LOD0 mesh/material bindings are suitable for the selected viewer baseline;
  they do not establish full runtime assembly, modular NPC composition, or
  world spawn policy.
- Source/CAB plus PathID is the stable object identity. Names and normalized
  tokens are candidate aids only.
- Generated static prefabs retain missing dependencies and approximations as
  explicit status rather than fabricating a complete actor.
- Character-specific exceptions must remain data/profile entries. Do not fork
  the renderer or importer per actor when the source contract is neutral.

## Animation boundary

- The playable Character Info scope uses the recovered humanoid Avatar and
  authored UI controller/clip relationships.
- Endminf enters her start state and hands off to the loop through a generated
  Animator controller using recovered transition properties. The lab does not
  replace this with a Legacy `Animation.CrossFade` approximation.
- The selected runtime root-motion consumer applies rotation and does not grant
  permission to apply translation.
- Recovered ACL keys remain the source. Preview decimation, corrective curves,
  tangent rewriting, pose offsets, or manual timing changes require independent
  evidence and must not be committed merely because one frame looks closer.
- Direct clip selection, state-graph selection, and restart share the same
  effect/audio composition owner. Resuming a paused clip remains side-effect
  free.
- Character Info's common `CharEffect` is one scene-level non-looping particle
  system. Selection activates it and calls `Play`; repeated selection while it
  is in flight preserves its survivor clock and must not inject `Stop/Clear`.
- Exact-build session `20260904T180646Z` proves a retained completed effect is
  stopped at time 1/count 0 before `Play` and playing at time 0/count 0 after
  it. The first overview Tick follows about 16.734 ms later. Its body clock is
  already seeded to 0.034241635 s before Play, so Animator state time and
  particle time remain distinct; the recovered scheduling must not add a
  preroll, delayed actor start, or Animator-aliased effect clock.
- Its recovered owner publishes a fail-closed generation plus source
  hierarchy, Unity identities, system clocks, and live trail count. Exact
  retained packet selection may use that evidence diagnostically, but
  canonical output continues to simulate the source system.
- Deterministic capture setup must not age the shared system while settling the
  actor. The Endminf harness recreates the observed retained-completed
  precondition, then invokes the same production-order Animator entry and
  `Play`; this is a capture precondition, not a runtime particle-time override.
  The corrected first saved frame measures 0.016666668 s particle time and
  0.050908305 s body time, agreeing with the retail/QPC join within about
  0.101 ms.
- A controller or effect definition proves authored composition, not that the
  retail frame executed it.

## Rendering boundary

- Direct3D11 is the authoritative lab backend because it matches the recovered
  retail shader binaries. D3D12 experiments remain labeled diagnostics.
- CharacterNPR, LitEffect, deferred resolve, shadow, post-processing, temporal,
  and Streamline resources retain separate producers and frame-lifetime gates.
- Recovered offscreen scene-color/SceneMV passes must pair any render-texture
  projection winding flip with rasterizer cull inversion, then restore both.
  RenderDoc proved that omitting this state rejected every shared CharEffect
  billboard after a valid VS/PS submission; the corrected pass writes both
  physical HDR color and SceneMV.
- Endminf overview_01 combines ten physical rock renderers using LitEffect
  `_PARALLAX_MAP` M01/M38 with a companion VFXBaseV2 particle cohort. Complete
  serialized prefab ownership, including fail-closed renderers, is the required
  shader-census starting point. The later overview_02 M27 and overview_02/03
  M28 owners remain separately gated.
- Recovered LitEffect material handoff uses one character-neutral, fail-closed
  schema for the complete serialized texture, transform, color, and float
  surface shared by the compatibility and five-MRT shaders. Overview_01 now
  also has exact runtime evidence for exposure/aspect, the live VFX clock,
  authenticated-zero anchor-wave state, and identity particle-mesh object
  translation across its complete early M01/M38 sequence. The anchor state is
  promoted through a hashed Resource plus active source-marker join, preserving
  readiness separately from the zero value. That scope does not authorize the
  later overview_02 M27 globals or either path's final deferred presentation.
- Material keywords, pass/queue selection, constant-buffer values, textures,
  depth, motion vectors, shadows, exposure, and history are accepted only from
  their exact serialized or observed owner.
- A component-complete current-build Streamline capture retains two consecutive
  native-resolution DLAA input/output/depth/motion transactions and a complete
  selected-actor Animator timeline. Its direct
  `ScalingInputColor` previews already contain Endminf's horizontal chromatic
  entrance strips, proving that feature belongs to upstream
  CharEffect/VFXRefract rendering rather than DLAA history. The output remains
  close to the current input and slightly attenuates aggregate consecutive
  change. The shared-QPC join places them at `ui_overview_start` 0.051009 s and
  0.076166 s with no intervening selected-actor Tick. The broad whole-actor
  echoes present at the matching bounded clean-video anchor are absent from
  both surfaces, localizing their producer downstream of DLAA to Uber/final or
  recording presentation. The lab's ordinary TAAU consumer remains
  compatibility-only pending an exact reusable DLAA integration.
- Native-resolution comparison is explicit rather than inferred: the lab
  renderer accepts a paired 3840x2160 profile and the comparator's `source`
  mode requires the exact recorded source dimensions, preserving the default
  annotation-pinned 1920x1080 contract for existing diagnostics.
- The observation-only Streamline schema-v2 capture is prepared to retain a
  hashed 4K swapchain color immediately before each accepted packet's closing
  `Present`, alongside its DLAA/depth/motion data on the same QPC chronology.
  This is a collection capability, not evidence, until a fresh exact-build
  session publishes and validates the new files.
- A resource that exists or hashes identically is not necessarily bound to the
  selected draw. Same-camera, same-size, same-frame, submission-order, and
  lifetime constraints remain part of the join.
- Compatibility shaders and lab-created buffers are explicitly approximations
  until the retail producer and consumer are independently closed.
- The graphics-only Full screen-shadow observer is pinned to the August 25
  client through a dedicated five-file manifest and passes installed-client
  preflight without native gameplay/IL2CPP hooks. Current dense evidence proves
  that two instanced fullscreen producers write one RG8 resource consumed by
  Default Deferred at PS t7; Default t11 is a distinct upstream resource also
  sampled by the scene producer at t5. Deferred presentation remains fail-closed
  until a corrected current-outfit capture validates the draw-local t7 payload.
- The AnimeStudio-owned shader recovery path may provide readable code and
  metadata. It does not prove runtime variant selection or final appearance.

## Secondary dynamics boundary

Endminf's enabled cloth components, roots, colliders, constraints, serialized
payload arrays, and selected native schedule are partially recovered. The lab
retains exact bytes and typed outer layouts while leaving unknown inner values
opaque.

The pure-managed frame coordinator retains one registered collider state across
frames, prepares only each owner's source indices, preserves old-frame state
across multiple 90 Hz substeps, and publishes current state at the frame
boundary. Its two-frame moving-collider verifier fails if registration reasserts
`Reset` or caller-provided stale previous samples replace retained history.

Sparse Unity comparison runs must use the capture report's `targetSeconds`;
image ordinals are not elapsed 60 Hz time. On synchronized retail checkpoints,
the current solver is worse than animation-only in both translation and
rotation, and adding the recovered rotation-only post-proxy CalcLine stage does
not repair the positional error. CalcLine therefore remains an independently
gated diagnostic, while canonical output keeps solver writeback disabled. Angle
jobs consume exactly their serialized baseline slices: the first
`baseLineData` vertex is the local root even when its hierarchy parent is
outside that slice.

Sparse captured-trajectory replay must publish the requested target time again
immediately before rendering; relying on the preceding `LateUpdate` can lag the
oracle by one frame. Exact-time replay of the retained August 26 trajectory
improves the matching August 26 visual sequence, but it is still evidence, not
the maintained solver. Its first visible state is already materially displaced
from an authored-pose solver seed, so the next recovery boundary is the retail
actor's pre-visible cloth lifetime/reset/stabilization sequence. Bone-oracle
metrics must not silently compare trajectories captured in different retail
sessions.

That lifecycle question now has a distinct observation contract rather than a
weakened trajectory claim. EndfieldCapture's diagnostic-only
`registration-timing full` profile retains one name-authenticated AddCloth
return QPC per Endminf owner plus a bounded ledger of every matching clock,
team/generation, and object identity independently of trajectory-window
readiness. Its native source gate requires complete ledger accounting and rejects
capacity loss, missing owners, clock, thread, lifecycle, hierarchy, publication,
and shutdown failures. Animator timeline schema v5 reads the selected
`CharUIModelMono.m_magicaCloths` collection (exact-build field token
`0x04009205`, offset `0xf0`) after the original Tick and retains bounded cloth
component pointers plus signed Unity instance IDs. The lab verifier joins each
named registration to that authoritative actor-owned collection using both
identities; other loaded Endminf instances remain reported but excluded. It
then joins the selected ticks only to the same session's complete Animator
timeline. A dedicated August 25 manifest now authenticates all five visual
files, and the runtime pins only the current AddCloth/identity dependencies;
trajectory hooks and windows remain disabled. The installed-client preflight
passes. One diagnostic session observed four registrations per name among 179
distinct cloth teams in one complete Animator entry; those first timestamps are
not attributable to the visible actor. That session predates Animator schema v4;
three fresh-process sessions must validate the ownership join and distinguish
warm-up from cache state before solver initialization changes.

The missing result is the complete retail numeric solve and actor-owned
writeback/history across all relevant branches. Global scheduler values or a
frequently observed TeamData address are insufficient; evidence must join the
specific Endminf owners and complete after the proven job dependency.

Do not replace the missing solver with hand-tuned bones, generic spring motion,
or a visually convenient writeback and label it recovered. A proxy may be used
only as a clearly marked comparison layer.

## Capture boundaries

### 3DMigoto

3DMigoto is the retail-tested graphics evidence path. Ground-truth capture must
remain disabled by default, exact-build sensitive, and UI suppression must fail
open when shader hashes change. A fresh A/B is required before a recording is
accepted as UI-free evidence.

### EndfieldCapture

EndfieldCapture is observation-only. Use it with the game closed and follow its
exact-build, prelaunch, one-attachment, bounded-session, and collection gates.
It must not alter shaders, suppress draws, hook input, or modify the game.

D3D11 COM hooks use the Windows SDK vtable order. Streamline function pointers,
viewport handles, command buffers, frame tokens, and resources have explicit
lifetime and identity rules; an address observed in one process is not a stable
actor identifier. Observer storage must remain bounded and off large callback
stack frames. Cleanup may not invalidate function pointers retained by the
client.

Failed or partially collected retail sessions remain under scratch as
diagnostics. Their observations may justify a tool fix, but never become parity
evidence retroactively.

## Reference and comparison policy

- Keep one named clean retail sequence as the primary visual reference and
  record its source video, frame mapping, extraction settings, and hashes in a
  generated report.
- Comparison frames must join exact no-frame-generation source frames and the
  corresponding Unity clock/state. Do not align by appearance alone.
- Annotate visible pointer/controller changes and split input-stable frames
  from camera-motion-affected frames. Deterministic animation renders use the
  actor's serialized camera entry state; capture-specific input endpoints or
  trajectories remain external reference evidence and never become actor or
  runtime constants.
- Report spatial, temporal, silhouette, effect, and color errors separately.
  One aggregate score can hide a regression in a critical layer.
- Captured resources and replayed lab outputs keep their color space, format,
  viewport, frame, camera, and producer provenance.
- Reference videos and raw frames are evidence inputs, not repository memory
  prose.

## Maintained workflow

```bat
cd endfield_reconstruction_lab
.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
```

For a focused change:

1. Verify export freshness and the exact source objects.
2. Regenerate only the affected model, material, controller, clip, effect, or
   profile contract.
3. Run the smallest importer/validator/capture path that owns the change.
4. Compare against the fixed retail frame/state contract.
5. Publish changing measurements to `reports/assets/character_recovery/` and
   keep raw captures in scratch.
6. Update this file only when the durable boundary or recovery queue changes.

The reconstruction lab README owns exact operator commands. The AnimeStudio
workflow owns exporter build/test commands. EndfieldCapture's README owns its
build and collection procedure.

## Remaining gaps

- Close the character-neutral retail render frame: exact shader variants,
  bindings, lighting/shadow resources, post-processing, a phase-joined final
  swapchain boundary, and final presentation route.
- Recover Endminf's complete secondary-dynamics numeric solver, owner identity,
  job completion, and writeback/history.
- Close the shared CharEffect live render packet. Production lifecycle timing
  is source-joined; the old 1,935-quad packet is a later automatic tail sample.
  The exact-build observer now captures the first two VS/PS draw occurrences
  directly from authenticated `Play`, including IA/VB/IB, constants,
  `_VertexSkinMatrices`, SRVs/samplers, MRT/depth, and PSO. Collect one new
  session and compare it with a live Unity D3D11 draw before changing the
  reusable shader or renderer. Capture readiness must follow actual application
  device/context attachment, not private WARP hook bootstrap; otherwise the
  dedicated worker attempts deferred preallocation with no attached device.
  The observer now publishes readiness only after attachment and hook success,
  with a real D3D11 bootstrap/first-Present regression covering this boundary.
- Expand converter and shader fixtures while preserving exact source bytes.
- Turn the validated Endminf solution into data-driven profiles for all
  playables without actor-specific renderer forks.
- Keep capture tooling bounded, observation-only, exact-build gated, and
  reproducible across client updates.

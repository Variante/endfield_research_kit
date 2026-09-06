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
- secondary cloth/bone simulation and history remain a confirmed silhouette
  gap; early rigid pose/presentation is also unresolved. Animator state timing
  alone does not prove that pose, and does not justify hand-authored corrections.
- sampled entrance skin palettes agree closely with independent source-clip
  poses at recorded Animator phases. That consistency does not authenticate
  frame-end bytes as draw-consumed data or resolve the earlier visual pose gap;
  the maintained palette audit preserves both phase candidates and both banks.
  Draw metadata clocks bound observer state reads and constant copies, while
  palette SRV aliases prove binding identity; neither establishes frame-end
  palette bytes as draw-consumed data. Full capture's Streamline publication
  prerequisite can postpone dense palette sampling beyond the early pose gap.

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
- A first-effect RenderDoc capture must arm before the normal restart, after
  the retained effect finishes naturally. Waiting for live particles and then
  requesting the following frame misses that boundary. The lab's dedicated
  windowed mode records and checks the single-step Play-to-render join; its
  receipt and live draw still establish only Unity-side evidence.
- A controller or effect definition proves authored composition, not that the
  retail frame executed it.

## Rendering boundary

- Direct3D11 is the authoritative lab backend because it matches the recovered
  retail shader binaries. D3D12 experiments remain labeled diagnostics.
- CharacterNPR, LitEffect, deferred resolve, shadow, post-processing, temporal,
  and Streamline resources retain separate producers and frame-lifetime gates.
- Scene-shadow attenuation/blend are environment-phase inputs copied each
  frame by the ordinary native shadow-manager route. The inspected volume path
  preserves authored values; a disable flag alone does not establish blend 1.
  Recover per-camera/shared-phase selection and interpolation ownership before
  publishing live values. Per-camera interpolation state is not itself an
  authored override. Trigger selection, active volumes and weights remain
  necessary; constructor defaults and captured constants do not establish them. See
  `reports/assets/character_recovery/shadow_simulation_native_ownership.json`.
- ContactShadow captured-input replay needs repeat controls: original dispatches
  can differ at pixels with overlapping recovered output writes. Preserve the
  original dot-product instructions through distance quantization; scalar
  multiply-add expansion caused a stable single-writer rounding mismatch.
  Matching the single-writer subset does not certify overlapping writes, live
  input ownership, or complete rendering parity. The compact evidence is in
  `reports/assets/character_recovery/contact_shadow_write_overlap.json`.
- Recovered scene-color/SceneMV copies must preserve attachment orientation so
  color remains registered to shared depth. `SetViewProjectionMatrices` takes
  the API-independent camera projection, not `GetGPUProjectionMatrix` output;
  the latter caused a second Y/depth conversion and a compensating cull flip.
  Actual post-fix VP and byte-identical scene-copy checks validate the D3D11
  correction. GPU matrices still belong in explicitly GPU-space shader globals.
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
- Shared CharEffect retains the source BC7 texture's complete authored mip
  chain and sRGB interpretation. Its shader-owned linear-repeat sampler must
  sample raw UVs; manually wrapping coordinates before clamp sampling changes
  seam filtering and derivatives. Serialized curve infinity codes likewise
  require explicit translation to Unity's public WrapMode enum, verified by
  independent engine serialization rather than the importer's own mapping.
  VFXRefract's separate RB displacement uses `_Intensity * vertexAlpha` and
  `_UseMainTexAsMask`; its normal-derived magnitude includes refraction strength.
  Recover names from the original compressed program's referenced parameter
  record when exported metadata omits fields. Exact RB, RGB/blend, and dissolve
  variants establish this contract; see the CharEffect RB parameter audit.
  Offline hardware replay of the retained original first draw reproduces its
  complete RT0 exactly. This proves packet sufficiency for that color output,
  not reconstructed Unity fidelity or RT1 parity; preserve those boundaries.
  Public Unity particle instance records require their own stream-layout
  contract. The recovered refraction path selects its Custom1 record variant
  from the renderer's mesh/GPU/active-stream settings and isolates that choice
  from shared billboard materials. A native matrix-bank declaration does not
  establish Unity's procedural buffer stride; validate the bound descriptor,
  shader loads, and actual post-VS positions together.
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
  both surfaces. Validated paired final-swapchain evidence now places broad
  echoes inside the game's post-DLAA radial Uber draw before UI composition.
  The lab's ordinary TAAU consumer remains
  compatibility-only pending an exact reusable DLAA integration.
- Native-resolution comparison is explicit rather than inferred: the lab
  renderer accepts a paired 3840x2160 profile and the comparator's `source`
  mode requires the exact recorded source dimensions, preserving the default
  annotation-pinned 1920x1080 contract for existing diagnostics.
- The observation-only Streamline schema-v2 capture retains a
  hashed 4K swapchain color immediately before each accepted packet's closing
  `Present`, alongside its DLAA/depth/motion data on the same QPC chronology.
  The validated pair is independent of Full owner-packet completeness. Keep
  that evidence scope separate from exact draw/pose phase and clean-video
  registration; see the generated paired-presentation review.
  Schema-v3 evidence now authenticates the first unique fullscreen consumer of
  that exact DLAA output, its immediate target, and draw-bound parameters before
  UI or subsequent writes. Both retained frames show the echoes in that target;
  the archived shader matches the recovered six-RGB-tap radial Uber exactly.
  Joint radial/chromatic values distinguish the authored entrance pulse from
  its late pulse. This identifies curve-value phases, not body-pose phases or
  EffectInstance clock ownership. See the generated
  `post_dlaa_uber_producer_review.json` and parameter audit.
  Native-resolution lab stage captures already show the authored radial echoes
  appearing in final Uber from comparatively clean after-temporal input. Keep
  body-pose/camera alignment separate from the now-authenticated retail consumer
  and parameters; preserve the existing runtime clock while closing those joins.
- A resource that exists or hashes identically is not necessarily bound to the
  selected draw. Same-camera, same-size, same-frame, submission-order, and
  lifetime constraints remain part of the join.
- Compatibility shaders and lab-created buffers are explicitly approximations
  until the retail producer and consumer are independently closed.
- The graphics-only Full screen-shadow observer is pinned to the August 25
  client through a dedicated five-file manifest and passes installed-client
  preflight without native gameplay/IL2CPP hooks. Current dense evidence proves
  that two instanced fullscreen producers write one RG8 resource consumed by
  Default Deferred at PS t7. An exact source/runtime compute-bytecode join
  identifies distinct Default t11 as ContactShadowCS/RayTracingV2's
  `_ContactShadow` UAV output, also sampled by the scene producer at t5.
  The legacy cross-backend screen-mask name is disproven. Dispatch-local
  constant-buffer slices and output bytes are authenticated in the combined
  two-entry evidence package. Bounded isolated GPU
  comparisons support the recovered arithmetic, but current native publishers
  read interpolated environment settings and a camera frame counter; constructor
  defaults do not validate those live values. Exact t7 uses the completed
  resolve, and t11 uses same-camera/frame contact output with separate content
  gates. Legacy HLSL bindings remain a different contract.
  The base native camera lifecycle resets its counter to zero and increments
  on camera Update, independently of contact dispatch readiness. The lab now
  owns that counter in pipeline camera state and passes it to contact; producer
  recreation, disabled passes, and setup failures cannot reset or pause it.
  This does not establish the retail camera's initial phase or an IFix override.
  Contact settings now import the selected authored phase with independent
  provenance, native percent conversions and ignore-edge lane; the installed
  base feature getter gates intensity. Unknown settings fail closed. This does
  not validate runtime blend/IFix state or refresh the legacy light/exposure
  snapshot's identity. Current authored exposure metadata is retained separately.
  The reusable shadow visibility interpolator now preserves inactive configs,
  copies active endpoints and applies the native scalar/boolean rules. Ordered
  retained-volume replay matches the selected visibility subset; an inactive
  higher-priority shadow config preserves the preceding active phase. This
  does not identify that phase's runtime source asset or close native upload
  ownership. The authored CharInfo prefab contains both the legacy shadow phase
  and an active migrated phase with the observed simulation values. Exact
  serialized references and ancestor flags establish that authored population;
  equal-priority native sorting does not guarantee hierarchy precedence. Source
  values alone cannot identify a live instance. See
  `reports/assets/character_recovery/charinfo_authored_shadow_volumes.json`.
  See `contact_shadow_authored_feature_source.json` in the same report directory.
  The combined capture needs no repeat for those graphics inputs. The optional
  environment-shadow extension observes selected phases, ordered applied
  volumes/factors and camera/shadow-manager state within the same two entries.
  It uses guarded reads and original-call forwarding without Unity API calls.
  FrameSetup may have no observed calls during these entries. Pinned deferred
  and contact-parameter getter callers supply independent observation routes;
  route labels, hook-entry counters and patch checks preserve that distinction.
  Retail entry/tail getters in the CPP render-request path yield complete
  selected-phase and volume observations. The legacy manager can remain zero
  while phase values and draw constants are one; do not assume its FrameSetup
  publication contract governs CPP rendering. Different camera frames can share
  one Present and identical matrices; the native-backed draw-local CB1 camera
  frame counter disambiguates them. BeforeCullingCPP converts the selected
  phase to a separate CPP shadow config. The engine can zero the pair for manual
  CSM override, then packs it into pooled upload data. The observer retains the
  earlier phase and compact request/config/working/packed state, guarded by live
  code pins. Publication requires the unique camera-frame join, coherent pointer
  rereads and the native branch. Matching owned producer-vector bytes still
  does not identify the actual pooled upload resource and binding range;
  that missing runtime lineage keeps publication closed.
  Per-window completeness and exact camera bytes must validate before using
  a runtime phase to explain a captured draw; raw instance IDs are not source
  asset names. Follow the EndfieldCapture README's opt-in procedure and retain
  any unresolved source identity explicitly.
  See `reports/assets/character_recovery/contact_shadow_runtime_source_join.json`.
  Offline execution of the original Default shader with authenticated draw-local
  inputs and the captured blend reproduces the retained pass output byte-for-byte.
  The earlier M27 color is numerically sufficient as its starting target; this
  does not establish temporal identity with the immediate pre-Default color.
  See `reports/assets/character_recovery/default_deferred_original_dxbc_replay.json`.
  Canonical deferred presentation remains fail-closed until live t7/t11 input
  production is validated; frozen capture replay is not a replacement.
  Default also depends on low-bit stencil rejection: captured-input ablations
  isolate its effect independently of depth. Unity's paired depth must carry
  source-correct stencil population and an output-merger attachment; a blank
  attachment cannot close this gap. See `default_deferred_stencil_ablation.json`
  in the same report directory.
  The diagnostic now records CharacterPrePass and HGBuffer on one five-MRT/
  D32S8 surface, using the same character draw collector as canonical PreG.
  Contact, low-resolution directional, VisibilitySH, and screen-shadow producers
  consume that post-HG surface and its R32 depth copy. An active HG owner failure
  cannot fall back to the independent character diagnostic. Default's paired
  DSV is its t1 depth resource; t0 is the binning buffer. Native draw failure
  cannot certify content merely because the metadata shell produced finite pixels.
  Foreground HG geometry replaces classification only after passing shared
  depth. This does not establish every retail stencil writer. The shared surface
  now includes the floor's separate source-owned distance-field HGBuffer pass:
  it writes class 5 and fixed unlit GBuffer lanes before its later ForwardOnly
  color. Its motion uses current/previous nonjittered camera and rigid-object
  transforms. Dense retained draw metadata and material parameters identify
  this writer; later Default per-pixel attribution remains a separate gate.
  Generic depth overrides must honor source `DepthOnly` membership: Endminf's authored crystal
  materials disable that pass, and the importer preserves this selection.
  Opaque render queue alone does not authorize an earlier replacement draw.
  Keep the captured output-merger blend: shader-side equivalent arithmetic
  changes retained pixels. Sidecar presentation seeds owned scene color, then
  blends the resolver through hardware; its equality test uses the published
  surface depth, not the fullscreen triangle depth.
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

Unity image comparisons use physical `actualSeconds` relative to the first
saved frame, gated by its annotated body phase; sparse runs must include time
zero. Requested times and image ordinals can disagree with rendered phase.
This relative join preserves the video anchor's existing uncertainty.
The clean reference's central anchor also fails a conditional entry-phase
consistency check: its first visible rigid actor maps before the authored
controller entry. Overlapping silhouettes mean that image is not authenticated
as one current physical pose. Preserve the runtime clock and annotation until
the captured radial curve phase is joined to body-pose and camera consumption; do not
choose a replacement anchor by visual fit. The bounded arithmetic and source
hashes live in `reports/assets/character_recovery/reference_entry_phase_consistency.json`.
Animator schema v6 brackets state API reads and the following Present-clock
observation. Consumers validate those bounds; v5 remains interval-unobserved.
Neither interval proves engine pose-evaluation order or palette upload ownership.
On synchronized retail checkpoints,
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

When several visual gaps need retail observation, prefer the explicit combined
Endminf workflow in the observer README: one attachment, two authenticated UI
entries, early palettes and native timeline, a separately published ContactShadow
transaction, then exact M27 and joined Default resources. Descriptor discovery
must allocate no GPU staging, and later-entry readiness requires writer
acknowledgments plus a completed Animator sequence. Keep GPU and retained CPU
limits distinct, record arming delays, and never join resource contents across
entries as one frame. Retain authenticated transient entry triggers across disk
publication; require current actor evidence when arming instead of requiring the
entrance shader to recur. This does not replace fresh-process cloth lifecycle proof.
Retain exact SphereOutside draw metadata before owner-window collection starts
and through joined-packet compaction; require its actual same-Present call order.
Once every bounded packet is published, rejected admission must terminate instead
of waiting for another entry. A constant scene-shadow R channel is admissible only
when the archived original shader and same-draw bound constants prove its explicit
white-output branch; texture appearance alone cannot establish this exception.
Shader admission pins must match original bytes from the selected installed
shader variant and a retained retail observation. Exercise bytecode hashing in
capture regressions; fixtures that synthesize the expected identity can conceal
a stale pin even when every local test passes.
The combined packet contract now has a fully collected retail example. Use its
authenticated source inputs for deferred recovery; capture completeness does
not establish final rendering or cloth parity. Collection must validate the
individual producer/consumer owners within a joined packet, and its streamed
artifact hashing bound must accommodate the observer's permitted payload size.

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

- Current-build Animator callbacks confirm the lab's rotation-only formula,
  but alternate built-in root-motion flags and forced-evaluation caller order
  remain unresolved. A native forced evaluation method alone does not justify
  a playback offset or establish the PlayerLoop/particle phase. Use the current
  Animator lifecycle report under `reports/assets/character_recovery/`; older
  build addresses cannot authenticate this ordering.
- Join the early rigid pose and camera to source animation. EndfieldCapture's
  dedicated pose-timing launcher preallocates a bounded dense palette sequence
  before readiness and arms on a new Animator/graphics trigger without waiting
  for Full mode's Streamline publication. Follow its README procedure. Retained
  palettes remain frame-end samples; metadata clocks and VS resource aliases
  do not establish same-draw consumption. The first validated retail pose
  session reaches the early entrance; use its phase-joined packets for an
  independent Unity palette comparison. See the lab progress log and generated
  pose-timing session review for the retained sample and startup-join gaps.
- Close the character-neutral retail render frame: exact shader variants,
  bindings, lighting/shadow resources, post-processing, a phase-joined final
  swapchain boundary, and final presentation route.
- Recover Endminf's complete secondary-dynamics numeric solver, owner identity,
  job completion, and writeback/history.
- Continue shared CharEffect draw comparison using the retained first-two-draw
  packets. Topology, UVs, population, and the complete authored texture now agree;
  the RB parameter mismatch is corrected. The strict particle-phase join remains
  open, and broad temporal echoes are a separate downstream question. Preserve
  exact-owner draw-local resource selection, readiness after application-device
  attachment, and idle waiting before authenticated Play/draw; WARP bootstrap
  readiness and regular Present scheduling are not valid substitutes.
- Expand converter and shader fixtures while preserving exact source bytes.
- Turn the validated Endminf solution into data-driven profiles for all
  playables without actor-specific renderer forks.
- Keep capture tooling bounded, observation-only, exact-build gated, and
  reproducible across client updates.

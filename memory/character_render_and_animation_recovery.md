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
The maintained 3DMigoto fork now includes a disabled-by-default Character Info
ground-truth recording preset derived from a retained frame's clean scene/UI
boundary. It suppresses only the observed post-scene foreground UI family,
fails open when client shader hashes change, and still requires a fresh retail
A/B before a recording is accepted as UI-free evidence.

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

Failed session `20260829T220238Z` exposed a separate Streamline observer
lifetime defect: the game cached an observer-owned `slDLSSSetOptions` detour,
then bounded shutdown removed the direct MinHook trampoline still called by
that escaped pointer, producing a native access violation. The observer now
hooks only the exact plugin entry point, never replaces pointers returned by
`slGetFeatureFunction`, never maps the immediate context during control-thread
cleanup, and limits exposure staging to the exact armed two-packet window.
Exposure joins use accepted-packet order, viewport, and command-buffer identity
rather than the unstable address of a `SlFrameToken` reference. Build and all
20 native tests pass. Follow-up session `20260829T224523Z` exited without a
client crash and retained two complete Streamline packets with matching
input/output/depth/motion hashes, but remains failed evidence: post-launch
attachment missed `slInit`, pre-trigger chronology overflowed, and the option
association was stale. Per-call chronology now resets at the exact trigger and
freezes after the bounded pair, while initialization lifetime remains separate;
a guaranteed pre-`slInit` observation still requires an explicitly approved,
exact-build-gated prelaunch lifecycle rather than synthesized evidence.

Session `20260830T033415Z` is also rejected evidence because the observer
crashed the client with WER exception `0xc00000fd` inside
`EndfieldCapture.dll`. The cause was excessive fixed local storage in observer
callbacks: the Streamline capture window alone reserved about 30.7 MiB per
call. EndfieldCapture commit `fc37afc` moves those records to bounded heap
storage and adds linked-image stack-frame gates for the runtime and D3D11
proxy; the largest verified linked frame is now below 93 KiB and all 21 native
tests pass. This repairs capture readiness only; it does not make the failed
session usable or provide missing graphics/secondary-motion evidence.

Streamline viewport values are opaque per-process lifetime handles, not stable
Endminf identifiers. Session `20260831T004510Z` supplied two otherwise exact
surface joins on viewport 5; the former viewport-3 constant rejected them
before staging. EndfieldCapture now binds the first exact scheduled packet's
viewport at runtime, requires the consecutive packet, exposure samples,
deferred-route provenance, observer, sidecar, and published summaries to retain
that identity, and rejects ambiguous or cross-viewport evidence. Full capture
also exposes the sidecar's immutable trigger Present so repeated later
body/Uber observations cannot move the graphics/Animator join. Release build,
all 26 native tests, repeated evidence-shaped viewport-3/viewport-5 cases, and
the nonlaunching installed-client preflight pass; a fresh retail collection is
still required before the repaired path supplies usable visual evidence.

The same session proved why the secondary observer recorded 32,097
`crossFrame=true` cloth updates but no writes. That branch bypasses the former
`WriteTransform`/`CompleteMasterJob` hooks and publishes through
`WriteDoubleBufferTransform`, then completes its returned job handle before the
outer `ClothUpdate` returns. The observer now identity-gates that exact call,
accepts only a nonzero handle, and samples the proven `last*` arrays only after
the outer return; the false path remains intact and all 20 native tests pass.

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
- `videos/2026-08-26_21-25-50.mkv` is the primary clean visual reference. It
  is 3840x2160 at native 60 Hz, retains the grey Character Info field and faint
  Endminf portrait, and contains no foreground UI. One-based source frame 88
  is the final blank swap frame and frame 89 is the first visible entrance
  frame. The maintained extractor writes 558 lossless frames under the
  `endminf_overview_clean_2026-08-26` reference sequence. A five-candidate
  sweep selects source anchor 91 by effect-region MAE with a bounded one-frame
  residual; this supersedes UI-masked video for visual comparisons.
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
  ACL-to-Unity validation now checks every retained key rather than spot
  samples: the start clip has 134,140 exact key values and the loop has 40,202,
  with every manifest-flagged position and rotation curve present. The
  validator reports fractional-frame quaternion interpolation separately; its
  current worst midpoint differences are 6.4803 degrees in the start and
  1.12324 degrees in the loop. Those measurements are an open runtime
  interpolation-semantics question, not permission to hand-author corrective
  positions, tangents, or curves. A trial tangent rewrite was rejected because
  it produced antipodal near-180-degree errors; the generated clips remain the
  direct recovered ACL keys.
  A character-neutral runtime bridge now imports validated ACL sample contracts
  as generated `RecoveredAclClipData` assets and drives Animator states with the
  recovered clamp/wrap clock, stable endpoint vector interpolation, and
  shortest-hemisphere normalized quaternion interpolation. The bridge preserves
  each manifest binding's position/rotation/scale mask and fails closed on
  source, decoded-payload, hierarchy, or state mismatch; it contains no
  Endminf pose constants or corrective curves. The retail Overview states all
  use `Write Defaults`, while the recovered start/loop ACL sets are asymmetric:
  273 versus 249 bindings, with 29 start-only paths, 5 loop-only paths, and 25
  shared component-mask differences. The driver now retains the union of
  source-bound components and restores a component absent from the current
  state to the captured hierarchy reference pose instead of retaining a stale
  transition sample. A compact source-hash-bound contract records that binding
  evidence, including the affected hair, cape, and thigh-cloth paths, but no
  pose values, curves, captured motion, or fitted timing. A canonical D3D11
  770-frame v25 render now proves source-decoded ACL publication throughout the
  complete start-to-loop sequence: all frames retain a valid binding, positive
  application across 278 transforms, and exact current-state, next-state, and
  transition-weight agreement with the directly evaluated Animator state.
  Captured replay and solver writeback both remain disabled for the entire run.
  The zero-offset clean-reference comparison is control-equivalent, confirming
  that this closes the body-pose publication boundary rather than claiming a
  visual gain. The visible entrance residual belongs primarily to unsolved
  hair, coat, and strap dynamics, not permission to tune the body trajectory.
  The two automatic Legacy owners under Endminf overview_01 now start from one
  authenticated `ui_overview_start` source-state clock sample: exactly
  `effect_01/A_actor_endminf_ui_overview_02` and
  `effect_nanguan/A_fx_endminf_ui_overview_04` must be present, enabled,
  Legacy, unique, and automatic before either is played or the source-post
  clock is published. The raw elapsed time is assigned once after `Play`, with
  no clamp, repeat, continuous resampling, or particle retiming. Runtime v2
  marker validation continues to rejoin every source PathID and descendant
  name, but canonicalizes the mutable Unity clone root back to the marker's
  pinned `effectRoot`; failures now report the deterministic row and bounded
  expected/actual hierarchy instead of a generic drift status. A dedicated
  D3D11 source rebuild and a 770-frame Viewer capture pass the two-clip seed,
  start-to-loop, settled-loop, four-root VFX, 68-renderer, M01/M38/M27 stone and
  crystal, suikuai, cleanup, and secondary-ownership gates.
  The retained peak Uber packet's body/reference mapping remains 4.35 seconds,
  while its captured radial/chromatic lanes solve the authenticated source-
  effect clock to 4.4333334 seconds; exact packet admission now uses the latter
  clock domain. The incomplete Far-only and physical-HDR sky branches remain
  explicit diagnostics and cannot satisfy canonical background inclusion.
  Canonical presentation holds the fitted plate off, keeps the source portrait,
  uses the existing neutral preview camera clear `(0.70,0.71,0.70,1)`, and
  requires presented top-left 128x128 luma at 0.65, 4.4333334, and 6.65 seconds;
  the current 770-frame report closes those frames at indices 41/268/401 with
  minimum mean/pixel luma 165.9324/154. The opening post pulse is deliberately
  outside this static-carrier gate. Across 554 bounded clean-reference rows the
  refreshed sequence's best -1-frame alignment is 32.6150 actor ROI, 34.5048
  effect ROI, and 15.2511 temporal-delta MAE. This removes the false black-
  background regression but is not parity: remaining differences include the
  retail floor/grid/background composite, source portrait grade, and unresolved
  effect/temporal ownership. Do not fit those gaps with a screenshot plate.
  Captured
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
  now uses the merged dense oracle directly through a bounded replay owner: 145
  retail samples and 74 unique hair/cape bones span playback source frames
  117-1264. Session `20260826T231348Z` contributes 7,635 direct render-boundary
  observations; only 431 per-bone values are bounded interpolations.
  Skin-matrix reconstruction and actor-root publication are consistent with
  Unity bind poses. The visible shift was a clock defect: sample zero belongs
  to body phase 0.08424164 seconds, while the old replay began at controller
  time zero. Replay now synchronizes to the evaluated body clock during the
  entrance, preserves the measured two-frame sequence anchor, then continues
  the finite retail trajectory across transition and loop wraps. It clamps
  rather than fabricating periodic motion after the captured endpoint and
  fails closed on stale v3 data, missing bones, or simultaneous experimental-
  solver writeback. This is explicit replay evidence, not a general
  BeyondBoneCloth solve.
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
  fail-closed rather than being fabricated. The publish gate now rejoins all
  101 saved GameObject/Transform rows to their exact source PathIDs and checks
  parentage, name, layer, hierarchy, and local TRS. The two used AnimationClips
  are decoded reproducibly from their exact serialized source payloads into 58
  scalar bindings and 17,984 keys. Their tracked v2 contract contains every
  float32 time, value, source-derived tangent, tangent mode, weight, and
  transport setting, so a clean checkout creates or replaces both `.anim`
  assets without the ignored source stage or an existing generated cache.
  The explicit local updater rederives the contract only from the two
  hash-pinned serialized AnimationClip JSON files, while normal Unity builds
  consume and validate the tracked payload. Cached `.anim` bytes,
  capture-fitted positions, and fitted curves are not admitted.
- The canonical capture now restores eleven retained LitEffect rock/crystal
  renderers: seven M01 rows, three M38 rows, and the later M27 hand-crystal row,
  all keyed by exact renderer/material PathIDs and the exact
  `S_rock_small_1_017_02_lod2` mesh. Direct references are validated against
  the v2 source marker before any renderer is enabled; the runtime rejoins each
  row to its exact source owner, renderer, particle system, mesh, material, and
  PathIDs. Material validation uses hash-pinned source JSON plus authored
  fields, textures, transforms, shader, keyword, and queue rather than hashes
  of generated `.mat` files. The opt-in runtime transaction now snapshots and
  restores each selected renderer's layer, enabled state, render mode,
  materials, and complete mesh slots on disable, destruction, or a partial
  apply failure. This makes enable/disable/enable deterministic and prevents
  M27's diagnostic layer 31 or compatibility bindings from leaking into a
  later run. The default remains disabled/fail-closed, and only
  `ENDFIELD_ENDMINF_LITEFFECT_VISUAL_COMPAT=1` activates them. Exact M27 mode
  now redirects only M27 to its identity-gated layer while retaining the ten
  separate M01/M38 ForwardOnly owners; the former blanket exclusion caused the
  visible 58-renderer/12-blocked stone regression. A current exact-M27 probe
  proves 68 admitted entrance renderers and exactly two separately blocked
  non-LitEffect rows. Frames 19-22 now contain M27's dark/amber faceted debris;
  its default-off Unity ABI probe still proves an empty material/mesh binding.
  The maintained Endminf launcher now enables this proven compatibility path;
  it had incorrectly forced the flag off even though canonical batch captures
  enabled it, which made the ten M01/M38 stones disappear in interactive use.
  Their shared four-texture family now imports the installed compressed mip
  chains rather than PNG-derived pixels while preserving the existing texture
  asset paths, GUIDs, local file IDs, and M01/M27/M38 material PPtrs. The
  transport is gated by the installed AssetMap identities, serialized
  Texture2D descriptors, full BC7-sRGB/BC5-linear mip-chain hashes, and exact
  material property-to-PPtr mappings; it has no live-capture dependency. The
  selected runtime sessions remain diagnostic only: `20260828T224210Z` has an
  incomplete graphics-provider summary, while `20260826T231028Z` has complete
  provider summaries but a truncated/failed full-frame resource selection.
  They corroborate the four complete top mips but do not close the conflicting
  logical LitEffect register names. Unity D3D11 validation confirms the full
  payloads, mip counts, normal-map typing, stable identities, and all twelve
  material-property bindings. This closes source texture transport only;
  LitEffect lighting, deferred composition, and particle placement still
  require their own source/runtime evidence.
  `effect_nanguan` owns the exact child Animator/controller whose default state
  zero uses `A_fx_endminf_ui_overview_04`. The native
  chain is now closed from `EffectInstance.Start`: after the SetActive IFix gate
  returns false, a false-to-true activation-latch change enters SetActive's
  internal core with `active=true`, which calls `PlayEffect`, enumerates exact
  `lodSetting[30]`, calls `EffectLodCfg.Play`, and resets the child Animator with
  `Animator.Play(0)`. This is exact only for the pinned unpatched route and the
  recorded installed local IFix snapshot, which replaces none of SetActive,
  PlayEffect, or LOD Play; runtime/remote/memory-only patch state remains outside
  proof. The separate zero-delay path conditionally enables the EffectInstance's
  own runtime Animator, whose exact serialized controller is null; it must not
  be conflated with the LOD-owned child Animator. The former
  `A_fx_endminf_ui_overview_03_04` composite and fitted 2.7667-second delay are
  rejected: the original AssetMap contains no composite row, and clip 03 belongs
  to a different prefab owner. The lab starts exact clip 04 when it instantiates
  the recovered effect root as an explicit transport mapping. On the same
  conditional pinned-unpatched route, FromOveview starts the child state during
  `EffectInstance.Start` and then applies the one-shot raw
  `length * normalizedTime` seed after Start returns.
  The Unity spawner now consumes that already-authenticated source transaction:
  after each automatic child Legacy `Animation` starts, it assigns the raw
  elapsed value and samples exactly once, then returns progression to the
  effect-owned scaled clock. Default/manual clocks stay at zero, while a stale
  clock that claimed validity fails closed. Focused tests pin the two automatic
  overview-01 children (`A_actor_endminf_ui_overview_02` and
  `A_fx_endminf_ui_overview_04`), forbid clamp/wrap and particle retiming, and
  require the state-time write after `Play`. The v20 canonical capture contract
  now records the authenticated overview-01 seed, its raw elapsed seconds, and
  the count of successfully seeded automatic children, and requires the exact
  count of two for the observation to pass. Canonical D3D11 visual validation
  remains pending because the shared Unity project lock is still present; it
  was not removed or bypassed.
  Child `GameObject.SetActive`/LOD display is also closed under that same
  conditional pinned-unpatched route. The original serialized TypeTree has
  `effect_nanguan.m_IsActive=true`; `EffectLodCfg.InitData` preserves that as
  `m_initActive`. Normal immediate creation reaches `EffectInstance.InitLod`,
  which copies the manager quality through `SetAllSettingLod` and refreshes
  every row. The manager normalizes quality to exactly one of `{1,2,4,8}`, so
  row 30's authored setting mask `15` admits every possible normalized value;
  its authored target mask `3` admits the untouched runtime target default
  `1`, and its sole distance row is active. `_RefreshLod` therefore requests
  `GameObject.SetActive(true)` for row 30. The authored masks are not runtime
  `showSettingLodLevel`/`showTargetLayers` values and must not be copied as
  hardcoded `15/3` display state. The lab activation preflight now pins all 101
  original GameObject TypeTree active bits plus the exact metadata identities,
  method pointers/bodies, `8/1` defaults, normalization branches, creation-to-
  refresh calls, `_RefreshLod` predicate/`SetActive` identity, and installed-
  local IFix nonreplacement. The exhaustive target-layer caller census maps
  only to `BattleNormalEffect._RefreshGuardLodAlpha` and the hash-pinned cold
  blocks returning into `BattleNormalEffect._RefreshTowerLod`, excluding the
  normal FromOveview/create/load/`InitLod` method identities. The Python rebuild
  preflight now validates this contract and the resolved installed native pair
  before it writes ACL jobs or launches Unity/BuildActor.
  Runtime/remote/memory-only IFix replacement,
  the retail effect tick domain, and any absolute capture/video offset remain
  outside proof.
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
  The current actual-geometry M27 draw also closes the physical resource ABI:
  PS t0-t3 are BaseColor/Normal/MRO/Parallax, PS t4/t5 are real sampled slots
  backed by one shared null/default resource because both serialized material
  properties are null, and VS t0 is the optional structured skin palette. The
  selected stone mesh has no skin rows and the live b2 record clears the skin
  branch, but the dependency remains declared and fail-closed. A source-driven
  Unity shell now declares that full ABI and has repeatable independently
  observed D3D11 compiler hashes plus successful stage+SHA substitution and
  `SetPass`; it consumes no captured VB/IB/CB packet arrays and still cannot
  submit a draw. Selected b0/b1 reads, authenticated PSR b2 range/resource
  ownership, complete b3 word provenance, fresh b4 producer/value lifecycle,
  s0-s5 descriptors, and synchronized MRT publication remain fail-closed. The
  raw retail peak frame itself contains the large M13 orange ring, so it is not
  evidence for shrinking or dimming that authored row.
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
- Unity diagnostic phase labels must use the captured `actualSeconds`, not
  `frameIndex / 60`. The full-sequence scheduler advances on an editor update,
  and its initial clamped thresholds drain one per update, so saved frame 263
  is post phase 4.4000 seconds rather than 4.3833. Explicit targeted timestamps
  are direct elapsed-time thresholds and are not subject to that startup
  backlog. Capture schema v12 records the authored `targetSeconds`, internal
  `requestedSeconds` threshold, actual phase, and signed phase error separately;
  this is telemetry clarification and does not retime the animation or VFX.
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
  decoded by a 480x270 dispatch of the 8x8 kernel. Four retained retail peak
  frames also close the actual consumer route rather than merely its producer:
  full-resolution `R11G11B10_FLOAT` scene color flows through that exact
  velocity-combine dispatch into a Streamline evaluation with reverse-Z
  `D32S8` depth/exposure, producing full-resolution `RGBA16_FLOAT`; bloom then
  reads that RGBA16 surface into a half-resolution `R11G11B10_FLOAT` chain and
  the exact Uber resolves it to `RGBA8_UNorm`. None of those frames executes
  any of the three ordinary TAAU shader hashes. This proves the retained-frame
  consumer is Streamline and excludes the ordinary TAAU path; the static
  quality mapping makes DLAA mode 6 overwhelmingly likely, but exact-frame
  `slDLSSSetOptions` evidence is still required before labeling that invocation
  mode-exact. Unity now publishes the same
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
- Full-profile capture `20260829T024828Z` closes the retained Endminf Uber
  `t2` resource itself: object `120495531488` is a stable 1024x32 linear
  `R16G16B16A16_SFloat` CharInfo LUT with no row or channel transform. Its raw
  payload is retained behind a byte-length, SHA-256, and five-sentinel gate and
  is used only by the exact Endminf Uber path; compatibility rendering keeps
  the procedural LUT. The session is not complete temporal evidence: 36
  cadence gaps remain, it predates the current Streamline observer, and its
  `R11G11B10_FLOAT` bloom input was not collected. A replacement bounded
  capture must close those three gates plus a unique peak-frame VS/PS constant
  packet before the peak Uber header is refreshed. The rebuilt observer now
  reserves and requires the exact Uber `t0/t1/t2` closure, rejects selection
  truncation, and admits `t1` only as a unique complete half-resolution
  `R11G11B10_FLOAT` payload. Its Streamline gate uses the latest required tag
  state, rejects null/zero-extent/non-finite evidence, revalidates the loaded
  pinned modules, and cannot be bypassed through an absent game directory.
- Effect-02's exact serialized streamed-cubic radial/chromatic coefficients,
  constant 1.0 radial-power curve, native mode/effective-power packing,
  signed/clamped post-projection center transform, source-only warped taps, and
  separate bloom sampling order are source-backed. The exact source owner is
  `Base Layer.Overview.FromOveview` (`0x5D0225EB`): its single joined
  `AnimatorBehaviourPlayEffect` owns ordered effects `_01`, `_02`, `_03`, and
  `_04`; `_01` owns `A_fx_endminf_ui_overview_02` and its `post (1)` child at
  local `(0,1.266,0)`. On the pinned unpatched route, `OnStateEnter` completes
  the accepted `LoadImmediately -> LoadFinish -> EffectInstance.Start` path,
  then `_SyncEffectTime` seeds active effect animators and `ManualSyncTime` once
  with raw `length * normalizedTime`. The recorded installed local IFix payload
  replaces none of these methods, while runtime/remote/memory-only and future
  patch state remain outside static proof. The lab carries that one-shot seed
  synchronously into the started `_01` instance and advances it with scaled
  `Time.timeAsDouble`; it never uses an absolute capture offset or continuously
  resamples the body Animator. Invalid selector, owner, generation, Animator,
  root, startup, or bind state revokes the transaction and capture records only
  a successfully evaluated source-post state. Runtime center projection
  resolves the imported `post (1)` Transform through
  its exact GameObject/Transform PathIDs and direct marker reference; it no
  longer duplicates `(0,1.266,0)` as a hardcoded placement value.
  The former fitted peak scaling,
  shifted late-pulse key, and downstream quarter-intensity factor remain
  removed. Retail `EffectInstance` tick ownership, SceneColor/pass chronology,
  and retail-equivalent presentation are still unresolved and explicitly not
  claimed.
  Runtime spawning also preserves each imported
  `ParticleSystemRenderer.maxParticleSize` value. The former visual-only
  billboard adaptation replaced source values at or below `0.5` with `10`
  across broad Endminf owners; it is removed rather than retained as an
  unproven substitute for the missing retail HGRP particle-size code path.
  The exact combined Uber variant now also closes the CharInfo merge: source-only
  global exposure, channel-wise bloom decoding above 0.3, serialized intensity,
  white normalized tint, zero blend mode, and saturated source alpha. The D3D12
  compatibility implementation reduced the UI-free 28-frame RGB MAE from
  27.6888 to 27.6752. An earlier recording registration found a nine-tick
  image-alignment offset and lowered the same MAE to 22.3254, but that result is
  comparison evidence only and no longer advances the source post clock. A phase-paired
  check against no-frame-generation source frames 367, 382, and 397 proves
  that applying the nine-tick post offset to particle simulation makes M13
  appear before retail and removes it from the retail peak. Particle delays
  therefore remain on the selection/body timeline: M13 is absent at requested
  4.2167 seconds, alive at 4.4667, and gone by 4.7167. The former 0.15-second
  post lead is retired comparison evidence and is never an active source clock.
  The pinned native producer selects mode 6 when both effects are active
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
  from byte 352. Decompiled use and the serialized source table close the
  physical PackedBinding order and static sampler ABI as BaseColor/LinearClamp
  at t0, Normal/LinearRepeat at t1, MRO/LinearMirror at t2,
  Parallax/LinearMirrorOnce at t3, Mask/PointClamp at t4, and Noise/PointRepeat
  at t5. MRO stores metallic, roughness, and occlusion in R, G, and B;
  parallax marching reads Noise.r and the final parallax contribution reads
  Parallax.g. M27's derivative transport now consumes the live source global
  `_GlobalMipBiasPow2`; the former capture-fitted `0.5` compatibility scalar is
  forbidden. Bounded shader dataflow checks reject later reassignment of the
  admitted UV, sample, material-channel, or output-feed variables.
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
- Endminf's exact 12-row Overview light fixture now has a separate complete
  native b31 contract rather than extending the selected SphereOutside subset.
  It packs all six headers and eight float4 words for each source-backed live
  row, uses the prepared rig's live transforms, and consumes the punctual
  producer's same-camera generation token. Every serialized row carries a
  deterministic source semantic hash, so inspector edits fail closed instead
  of becoming hidden light tuning. The bounded clean capture
  `20260828T121603Z`, frame 1758, owns only its 1,632-byte active prefix; its
  inactive allocator tail is explicitly outside the oracle. The extended
  invariant retains source-stable oct lanes and matches offline, while the new
  named/CB4 GPU transport verifier remains to be executed when the shared Unity
  project lock is released.
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
- Endminf's two punctual-shadow rows populate the lab-owned diagnostic atlas
  and selected b34 transport from the already prepared packed order rather
  than a row-to-slot table. The admitted clean retail frame closes packed order
  `[7,4,2,6,10,3,9,5,8,0,11,1]`: source row 3 / packed row 5 receives dynamic
  slot 40, then source row 11 / packed row 10 receives slot 41. Runtime code
  derives this by filtering the prepared order and allocating contiguous cache
  faces; captured order and slots are verifier inputs only. b4, b5, and t6 now
  require one matching camera/generation token before the exact consumer can
  submit. The maintained rig now starts from the pinned native
  `HGSettingParameters` base-tile default `T=512`; captured `T=1024` remains an
  explicit diagnostic override because the runtime/quality override owner and
  predicate are not source-closed.
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
  cases. The v2 constraint-schedule contract now hash-joins these active
  Tether, two-pass Distance, three-sweep Angle, and Point-capsule contracts to
  the pinned managed call order and Endminf's authored activation census. It
  admits only the source-static AVX2 candidate: 5/8/25/6 native vectors,
  eighteen complete Endminf Angle baselines, and the separately closed
  dual-CPU float sin/cos helper all retain exact source/Unity results. This
  closes one bounded active constraint/collision candidate, not the
  process-selected retail route. Runtime solver composition and Transform
  writeback remain disconnected until the live CalcLine route artifact is
  admitted.
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
  The startup/reset lifecycle is now source-closed without a captured motion
  trajectory: `AddTeam` seeds `Valid|Reset|TimeReset`, enabling the process
  adds the active flags and reasserts `Reset`, and the pre-simulation reset job
  copies the current animation pose into the simulation/base/display/velocity
  history arrays while zeroing velocity, friction, and collision state.
  `PostTeam` consumes `Reset|TimeReset` after publication, including on a
  zero-substep update. The managed owner solver implements this exact
  transactional fan-out and has deterministic distinct-current/previous-pose
  coverage. This closes initialization only; it is not permission to replay a
  captured trajectory or invent the unresolved cross-frame transport.
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
  Static recovery identifies it as a current-to-last value copy rather than a
  pointer swap, but does not identify a live caller in the target pipeline.
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
  invoke windows for Collider Start, Collider End, CalcLineNormalTangent, and
  the three Simulation kernels. CalcLine additionally carries hash-pinned
  read-only return probes for its exact `BurstCompiler.get_IsEnabled` call and,
  only on an admitted managed CalcLine caller stack, IFix `IsPatched(0x219)`.
  The target and route-probe blocks pass the installed four-file check-only
  gate plus exact body/call-target verification; no live attach, selected-route
  result, or kernel execution observation has been performed.
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
The canonical grey carrier remains a neutral clear while the physical
`SphereOutside` HGBuffer plus Default Lit resolve is fail-closed on its missing
content-valid t11 producer/consumer join; foreground UI remains excluded.

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
hash-gates them. The complete M29 packet in session `20260827T064009Z`
independently closes this extraction boundary: decoded BC7 PS t0 and t1/t2
match the generated PNG pixels exactly after the expected vertical texture
orientation. Remaining M29 differences are shader/output behavior, not an
AnimeStudio texture-payload mismatch. Arbitrary requested-time capture can now retain all five
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

The replay's fixed-function state is now independently source-gated. Globally
complete targeted session `20260827T225644Z` contains four draws of the exact
LitEffect VS/PS pair at frame 2723 with five MRTs, writable reversed-Z
`GREATER_EQUAL` depth, back-face culling, front-CCW winding, and scissor enabled.
The focused report
`reports/assets/character_recovery/endminf_m27_fixed_state_capture_latest.json`
fails closed on session, frame, shader, IA, sampler, target, and state drift.
The native replay control uses that captured state and a WARP validator instead
of its former `ALWAYS`/no-cull substitute. This corrects diagnostic transport
only: it remains immutable packet replay, is not canonical presentation, and
does not close the source textures' full mip chains or the unrecorded s3-s5
samplers. The generative target remains the exact compiler-substituted shader
over live ParticleSystemRenderer geometry and source-authored state.

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
The later retained peak proves the active `86a732cef7eedb15` Uber is already
the Unity exact-transport payload. Relative to the ordinary `de96a55f118305ea`
variant it adds only six-tap radial averaging, not a hue or chromatic transform,
so the amber-versus-blue-white gap belongs to its inputs, grade, or phase. The
retail `t2` is now a stable exact 1024x32 RGBA16F LUT and differs materially
from the procedural replay LUT; keep it as a build/CharInfo-gated raw oracle
until row orientation is validated. The peak `t1` bytes were absent because
the observer did not size `R11G11B10_FLOAT`; four-byte readback support and a
WARP regression now make the next bounded capture authoritative for bloom.

A fresh five-stage 4.40-4.55-second diagnostic against the clean August 26
reference localizes the apparent shifted hair, cape, portrait, and particle
UVs to the final compatibility Uber pulse. The pre-Uber character geometry is
coherent; at 4.4333/4.50 seconds, suppressing only that late pulse preserves
the authored hand burst and ring while reducing 1920x1080 retail ROI MAE from
33.6897/33.8937 to 31.5582/31.6457 and reducing the ROI fraction with channel
spread at least 24 from 35.70%/33.29% to 19.25%/18.92%. This does not authorize
removing the retail radial/chromatic effect or retuning its source curves. It
proves that another bind-pose, renderer-transform, UV, camera, or replay-offset
patch would target the wrong stage. The exact combined DXBC reads live PS b1
c0/c25; the old 3DMigoto constant arena contains one plausible candidate but
does not bind its `PSSetConstantBuffers1` offset to the draw. EndfieldCapture
now priority-retains exact combined fragment
`3f490e1504c435541769ee03e881583df554e652df155e5b942a3a410d8e086b`
and all fullscreen PS b0-b10 ranges. Direct disassembly additionally proves
that exact vertex fragment
`a8c084c37eba0ecc78f26d984a2b8c658f8d743002048c84431807d9dee0ce4e`
reads a separate stage-local VS b0; PS b0 cannot stand in for it despite the
shared slot number. EndfieldCapture now retains and serializes this VS b0 for
the priority Uber draw too. The verifier requires the exact VS/PS pair, VS
b0[1], PS b0[28], and PS b1[26], and publishes byte-exact declared ranges.
The payload builder accepts only one unambiguous validated packet. Both exact
shader objects are now hash-pinned in the native Unity tool and create
successfully on WARP D3D11. The Unity path now has a dedicated exact native
`Draw(3,0)` transport rather than compiler substitution: a 64-packet immutable
render-thread ring keeps main/render thread state separate, validates the exact
RGBA16F source, half-resolution R11G11B10 bloom, 1024x32 FP16 LUT, and linear
R8G8B8A8 output, binds stage-local constant buffers, and restores every touched
D3D11 state. The managed bridge owns stable exact-format copies around SRP
temporary identifiers and the Viewer report distinguishes requested,
submitted, and fail-closed fallback. Fallback and generated-payload validators
both pass, including mode 0 outside the pulse, modes 3/6 during it, 64 unique
queued events, overflow rejection, and invalid flag rejection. A live Unity
negative run rejects the absent payload visibly and keeps compatibility output;
runtime submission remains fail-closed until the new live constants exist. The
same remaining targeted Numpad-1 frame must
therefore close M30/M31 scene depth and the complete Uber VS/PS constant ABI
before changing the canonical post path.

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
close texture replay: 110 of 111 frames reached the 32-resource selector cap
because repeated unsupported exact-pair PS slots consumed ten records before
later M29/M30 textures. The narrow exact-pair selector now skips zero-byte
unsupported resources. Retained draw records also carry their own bounded
IA/PS resource observations, keyed to the frame-wide selected payload records;
this removes the ownership ambiguity that remained even when a texture blob
survived. The WARP test covers PS slot plus IA/index ownership.

Focused session `20260827T061004Z` contains one 31-package sequence covering
the buildup, peak, and fade. It retains 12 exact M29 packets and 10 exact M30
packets. M29 now has complete owned IA and PS t0-t2 payloads. M30 has complete
IA, constants, and PS t1, but its stable PS t0 is a 3840x2160 four-byte
scene-depth soft-particle input (33,177,600 bytes) and is absent from every packet: the old
targeted aggregate ceiling was only 32 MiB and about 25 MiB of prior bounded
evidence was already selected. Follow-up session `20260827T064009Z` proves the
64 MiB patch is active across 38 complete packages, but exposes larger
16-MiB geometry carriers: the exact M30 frames already retain 58.66-59.25 MiB
before its scene-depth input, so t0 remains absent. Session
`20260827T081152Z` is healthy and contains two complete targeted Numpad-1
packages, but disproves the subsequent 96-MiB estimate: frame 1845 retains
75,579,484 resource bytes before the exact M30 draw and still omits its
33,177,600-byte scene-depth PS t0. The measured closure is therefore about
107.4 MiB. EndfieldCapture's targeted byte ceiling is now 128 MiB, with a
regression gate for 76 MiB of measured pre-M30 evidence plus that exact depth
input. The one-frame and 32-resource bounds remain unchanged. The
focused `verify_endminf_m29_m30_capture_completeness.py` gate treats global
unrelated selector pressure as a visible diagnostic after checking every exact
owner binding; it now distinguishes M31 by its exact shared shader pair,
intensity/alpha tuple, and two capture-proven tint states instead of folding it
into M30. Missing owner payloads still fail closed. The existing temporal
sequences do not need repeating. The 128-MiB production launcher and D3D11 DLL
rebuilt successfully and all 15 native tests, including the D3D11 proxy
lifecycle, pass. One targeted Numpad-1 frame at the crystal peak is the only
remaining graphics evidence needed. Full/everything mode and another Numpad-4
sequence are not required.
The existing temporal sequence plus `081152Z` now also generate eleven
hash-pinned M30 packets: exact captured constant prefixes, canonical one/two-
quad IA slices, the 20-byte secondary stream, and immutable 256x256 PS t1.
Both generated C# and native payload contracts explicitly publish
`DepthContractReady=false`; the native plugin compiles and statically validates
that fail-closed boundary. No M30 draw is admitted until the replacement frame
retains and validates the full-resolution PS t0 scene-depth descriptor.
The first post-stone 770-frame baseline was not a valid hair/cape oracle: its
capture command enabled the rejected diagnostic secondary-dynamics solver,
which made the dense captured retail trajectory fail closed because both paths
owned the same 74 bones. Canonical video export now rejects that combination.
A corrected 770-frame, 60 Hz Viewer sequence has solver writeback in 0/770
frames and the 145-sample, 74-bone retail replay bound and applied in 770/770;
it completes the start-to-loop transition, restores the LitEffect stones and
their authored lifetime, includes the grey background and portrait, and
excludes foreground UI. M27 HGBuffer presentation is active in all 326 captured
phase frames after making its presentation selector transitively request the
deferred consumer. The synchronized peak improves from 16.5448 to 16.6648 dB
RGB PSNR but remains only 0.7023 SSIM: retail has a compact amber ring/core,
while Unity still has a broad RGB-separated ghost field and an overbright core
that obscure the hand and body. The exact Uber payload remains the dominant
visual blocker; do not compensate for that post distortion by shifting bones
or UVs.

The CharInfo gyroscope path is code-closed through its input-provider boundary.
The pinned Tick returns PreLate option `8`, polls
`Beyond.Input.InputManager.mousePosition`, clamps and normalizes against half
screen extents, evaluates the two serialized curves and scales, and applies
one evaluated-target squared-distance gate at `1e-10`. An inactive path creates
the serialized two-second ease-6/OutQuad tween; an active path calls
`ChangeEndValue(rawTarget, -1, true)`, preserving duration and snapping the new
start to the reached value. Presentation-profile data owns actor entry offsets.
Canonical/batch capture no longer embeds the clean video's endpoint or cursor
track: it defaults to deterministic serialized entry, rejects live input, and
reports mode, provider, explicit input when present, and entry offsets. The
interactive public-Unity mouse adapter remains useful for exploration but is
not retail-input parity because Beyond's virtual/controller provider is not
implemented.

The captured-replay renderer-consumption audit rules out a disconnected or
unused secondary skeleton. All 74 replay transforms resolve in active target
skinning palettes and have positive vertex weight. Hair consumes 21 replay
bones across 3,359/7,900 weighted vertices, cloth-01 consumes 52 across
7,389/27,314, and cloth-04 consumes 2 across 612/7,811; cloth-03 is correctly
rigid to non-replay `mask_jnt`. The unique consumed count is still 74 because
one bone is shared by cloth-01 and cloth-04. This necessary structural gate
passes, so remaining cape-width differences require a retained-sample baked-
mesh/GPU-palette differential or stronger same-initialization retail trajectory
evidence rather than another path-remap or constant replay delay.

An opt-in retained-skinning probe now samples only after each beauty render and
serializes `BakeMesh` local/world bounds, vertex checksums and positions, every
active bone matrix and bindpose, and renderer-local/world skin palettes. Its
3.0/5.0-second D3D11 validation reports six visible LOD0 hair/cloth renderers
per frame, matching bone/bindpose counts, non-empty baked geometry, and applied
captured replay for all 12 rows. This is a diagnostic boundary, not a beauty
change. A fail-closed comparator now joins those rows to `20260826T231348Z`'s
draw-time VS b2 palettes by exact mesh count, shader identity, source-palette
SRV/CB object identity, and a documented +/-1-frame timing boundary. At 5.0
seconds, mean retail-to-Unity rotation error is `1.83` degrees for cloth-01,
`4.72` for cloth-04, and `0.42` for hair; hair translation error is only
`0.00072`. The 3.0-second cloth-04/hair observations require much wider retail
brackets and remain explicitly reduced-fidelity. This proves that late hair
palette transport is already very close and that residual cape shape is not a
global matrix convention or transpose failure. It remains CPU-semantic and
partly circular because Unity is driven by the recovered retail replay; it is
not yet direct readback of Unity's submitted GPU palette.

A same-time early-entrance ablation at 0.4667-1.10 seconds rejects removing the
recovered pre-Bloom temporal resolve, M36, or M46. With temporal resolve active,
M46 improves effect MAE at every 0.4667-1.05 sample and only regresses the
1.0833/1.10 tail; excluding it worsens temporal-delta MAE from `77.2471` to
`77.3810`. With temporal resolve disabled, excluding M46 worsens both effect
and temporal metrics. M36 exclusion likewise worsens the effect and temporal
metrics. Retain all three source-authored contributions.

Five-surface post captures at 0/0.0167 seconds localize the conspicuous initial
RGB comb unambiguously: `before_temporal`, `after_temporal_bloom_input`, bloom
prefilter, and reconstructed bloom are clean, while the repeated colored actor
silhouettes first appear in `final_uber`. The same surfaces are clean at
0.5/1.0833 seconds after the initial recovered radial/chromatic curves reach
zero. Therefore the dominant initial trail mismatch is the compatibility Uber
kernel/parameter transport, not TAA history, authored M36/M46 particles, or
bloom. Do not compensate in those upstream systems; the exact runtime Uber
capture remains the required closure.

The pinned native Uber parameter producer has now been regenerated and
hash-gated against the selected client instead of relying on the retired
native-map artifact. It packs `c0=(center.x, center.y, radialIntensity,
effectivePower)` and `c25=(mode, chromaticIntensity, radialAverageSteps,
chromaticAverageStep)` with unit-preserving radial/chromatic intensities. Mode
6 is selected exactly when both effects are active and radial intensity exceeds
`0.01`; otherwise mode 3 is selected. In the both-active branch, effective
power is `lerp(1, radialPower, saturate(radial/chromatic))`. The matching
FrameAnalysis call order places DLSS/DLAA before the final Uber draw, so an
upscaler cannot attenuate or correct this final RGB split. Keep the recovered
curve units and mode predicate fixed. The remaining uncertainty is live
stage-local constants/binding timing and the shipped Uber output transport,
which still requires an exact retained Uber packet.

The same corrected run exposed a separate native validation gap hidden by the
old readiness flag: render event 3 armed the deferred exact draw but did not
restore `SubstitutionRoute::DeferredDiagnostic` after M27 shader preparation
reset the mutually exclusive compiler route. The native event now sets and
clears that route explicitly. A 1920x1080 M27 peak probe validates exact-bound
state, all t0-t25 resources (`0x3ffffff`), all b0-b8 buffers (`0x1ff`), finite
RGBA, and the recovered-HLSL comparison at one ULP (`maxAbs=1.1920929e-7`, no
values over `1e-6`). The maintained validator now uses the current 26-texture,
9-buffer ABI instead of the retired 28/10 contract.
The `064009Z` backbuffers show the cyan promotion presentation (blue skin,
shoulder accent, and visible effect grading), while the canonical clean
`2026-08-26_21-25-50.mkv` reference uses the yellow-accent natural-skin
presentation. Reuse the capture's shader ownership, geometry, timing,
constants, and depth behavior, but do not use its final composited color as
the clean-reference color oracle.
The combined gate
`verify_endminf_combined_graphics_capture.py` checks this closure together with
render-boundary skin-palette coverage across entrance and settled-loop bursts.
It deliberately permits a mesh to be absent from individual retained frames,
but rejects ambiguous draw-time b2 pairs and insufficient per-burst coverage.
For `20260826T231348Z`, cloth-01/cloth-04/hair have 109/56/91 unambiguous
observations across both 55/56-frame bursts; the capture is rejected only by
the old resource truncation, so its cloth evidence is usable while its
M29/M30 texture evidence is not.

The pre-patch session is now covered by a fail-closed M29/M30 temporal
verifier. Capture timing uses `timestampQpc`, never presented-frame deltas:
the 13-packet M29 sequence begins at 2.4833 seconds and the 11-packet M30
sequence begins at 2.7666 seconds, matching M30's authored 2.77-second delay.
Legacy sessions report the verified 10 MHz Windows-host clock fallback;
new EndfieldCapture sessions record `qpcFrequency` directly in `session.json`.
Owner selection uses shader pair plus exact PS b3 c1/c4
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

The large grey triangular artifact visible above the early crystal burst was
not M29/M30. A same-time material ablation assigns it to the M35 Loft pair.
M35 authors Sample2 as its only blend carrier (`weight4=1`) while Sample0 is
disturbance-only (`weight4=0`); the recovered non-polar three-sample branch
incorrectly routed blend through Sample0. Routing that exact specialization
through Sample2 removes the dark Loft silhouette and restores thin warm wind
streaks without disabling the source material.

The broad late circular burst is M31, not M30. A synchronized 4.4333/4.50 s
material ablation removes the ring while preserving the central flash, rays,
and debris. Session `20260827T064009Z` contains two exact M31 packets in frame
1841 (draws 3 and 11): the shared VFXBaseV2 pair is
`62A5CE6C09171DE9/5558DEDDB1EE6188`, PS b3 c1/c4 exactly match M31's authored
intensity/alpha and linearized tint, and its 256x256 BC7-sRGB t1 payload plus
IA bindings are retained. M31 and M30 both soft-sample the same 3840x2160
scene-depth object at t0, which is the one 33,177,600-byte payload omitted by
the old 64-MiB package. Disabling only M30 soft blend restores several thin
upper-right streaks but does not create the circular burst; retain the authored
soft-blend keyword and do not treat the missing depth as the cause of the ring.
The remaining 128-MiB targeted recapture is for exact M30/M31 edge fading and
resource closure, not for ring ownership, shader selection, tint, or texture
identity. Session `20260827T081152Z` is not that recapture: its runtime status
records the retired 96-MiB budget, it contains one two-frame burst rather than
the required entrance/settled sequences, and M31 draw 3 still lacks its
33,177,600-byte PS t0 scene-depth payload. The combined, Uber, and M29/M30/M31
verifiers all fail closed on those exact omissions.

The next targeted D3D11 recapture also closes the formerly inferred Uber draw
state in the same frame. EndfieldCapture now records the priority combined
Uber resolver's output texture/view format and dimensions, MRT/depth binding,
viewport and scissor, PS s0 descriptor, blend state/factor/sample mask,
depth/stencil state, and rasterizer state. The exact-Uber verifier requires
that draw-bound state together with VS b0, PS b0/b1, shader identities, and the
128-MiB resource policy. This prevents a successful constant payload from
silently retaining guessed sampler, output, viewport, blend, or raster state
and avoids another runtime pass solely to recover presentation bindings.
The retained retail Uber draw additionally proves that its R8G8B8A8 output is
paired with a distinct full-resolution `R24G8_TYPELESS` resource viewed as
`D24_UNORM_S8_UINT`, cleared to reverse-Z far depth `0` and stencil `0` before
the pass. The exact Unity transport previously required a null DSV. It now
allocates, binds, and clears a dedicated D24S8 attachment, while the native
draw rejects any other depth descriptor. This attachment is not the primary
scene depth and must never clear or replace that owner. Uber depth testing is
disabled, so the immediate pixel delta may be zero; the correction closes the
retail render-pass binding and later-draw continuity contract.

The two useful skin-palette rows in session `20260827T081152Z` are now joined
to the clean no-frame-generation sequence by independent backbuffer edge and
74-bone pose matches. Capture frames 1845/2578 map to clean frames 257/273 and
playback source frames 369/385 within a one-frame anchor boundary. They carry
73/74 and 74/74 replay bones respectively and override older-run dynamics only
at those two phases. The dense replay contract is schema v4; source frame 385
no longer interpolates either cloth-04 owner. This improves same-reference
hair/cape evidence without treating the capture's cyan final composite as a
color oracle.

At the matched crystal peak, the public-Unity HLSL Uber fallback was the source
of the broad RGB echoes: a clean-frame-269 sweep over exact source parameters
selected `0.25` of the radial/chromatic intensity for that fallback, improving
full-frame PSNR from 17.5342 to 17.5831 dB once the recovered smoke is also
present. The native exact runtime continues to receive the unscaled retail
state. This is a public-Unity pre-Uber temporal-source correction, not authority
to alter the recovered curve units. The remaining dominant local peak shape
error was the oversized `M_fx_endminm_gfx_17` / `baoshan` bright wedge. The
installed no-keyword BASE fragment samples MainTex through static
`LinearClamp`, while the recovered shader had used Unity's paired sampler from
the source Repeat Texture2D. Exact-owner diagnostics showed continuous UVs,
uniform vertex alpha, and a smooth radial texture; switching only the BASE
sampling ABI to static LinearClamp removes the repeated out-of-range radial
carrier while preserving the authored `7.4` intensity, premultiplied zero-alpha
output, blend state, queue, curves, and texture. The matched peak phase sweep
now reaches 19.5151 dB against clean reference frame 269, versus 17.5831 dB
before this correction. The BaseV2 admission verifier now fails closed if this
static sampler boundary regresses. A source-identity-scoped A/B also rejects
Unity procedural particle instancing as the cause: disabling it for `baoshan`
left the former wedge visually unchanged and moved matched-peak PSNR by only
+0.007 dB, so the adaptation remains reverted.

The static-LinearClamp M17 correction also survives the full clean-reference
sequence rather than only the selected peak. Across all 554 mapped frames
(clean reference = Unity frame + 4), aggregate RGB PSNR improves from
18.0352384 to 18.0672940 dB, with a mean per-frame gain of 0.033 dB. This
confirms a real but deliberately localized transport fix; it does not close the
remaining M31 shell, exact Uber, gas shape, or particle-composition gaps.

M31's missing shell is not safely correctable with particle pre-roll. A narrow
two-tick diagnostic moved `overview_02/all/guangyun (6)` from alpha 10/255 to
108/255 at the matched frame, but M31-only output remained a broad brown haze;
the timing adaptation was reverted. A separate source-equivalent
`vertInstancingColor(input.color)` diagnostic changed the broad haze but did
not recover the retail shell, so that shader adaptation was also reverted. Its
`_USE_SOFTBLEND` path uses a 0.001 distance and still lacks the captured
33,177,600-byte retail scene-depth input, so exact depth/edge reconstruction
remains the owner of this gap.

The missing peak gas is source-identified `overview_02/all/smoke (2)` using
`M_fx_endminm_gfx_20`. Its authored 4.46-second delay and six-particle payload
are retained. The former owner-gated `2/60`-second `ParticleSystem.Simulate`
advance came only from a matched retail frame and has been removed: it was a
video-fitted timing correction, not recovered producer code. M20, crystals,
stones, rays, and every other particle now start from their authored source
delays on the selection/body clock. Recover the missing gas through its actual
particle/render transport rather than an output-alignment offset. The separate
runtime `2/60` Viewer lead used by packet replays was likewise an Editor
capture-scheduler fit and has been removed from runtime diagnostics. Their
phase arrays remain default-off capture diagnostics and select packets only
from authenticated source-effect elapsed time; they do not retime source
particles, animation, or effects.

The CharInfo background now has a source-honest Endminf selector independent of
the generic ready-subset diagnostic and fitted backdrop. It admits the exact
`S_GridFar`/`M_GridFar` route with its 1,012-vertex/1,518-index mesh, layer 13,
queue 2950, `ForwardOnly` pass, exact transform, BC7-sRGB `T_GridLineFar`
texture, static `sampler_LinearClamp`, and unattenuated serialized open-state
tint. It also admits the exact source `ShadowPlane` identity only as a
source-backed partial owner; final retail pixel ownership remains unresolved.
The canonical source path enables only `GridDeco/Far` and `ShadowPlane`, keeps
Sphere/floor/wall off, and requires the generated `ReferenceBackdrop` plate off.
That plate's actor-bounds placement, paired-frame grade, and 0.125 grid-alpha
attenuation are capture-fitted diagnostics and remain available only under the
separate compatibility selector. The upright source-recovered portrait remains
independent. Bounds and sampler corrections alone did not admit GridFar; the
recovered pre-GBuffer owner had been forcing the `ReferenceBackdrop` through a
generic depth-only path even though its shader declares `ZWrite Off`.
Excluding that diagnostic shader from generic depth admission makes the exact
source grid visible with normal character occlusion. Remaining differences
belong to final ShadowPlane/SphereOutside ownership, Uber, camera, and portrait
composition rather than procedural replacement geometry.

The maintained Endminf launcher, editor reproduction entry point, and canonical
video setup now pin the fitted plate, generic ready subset, measured opening
strip, captured packet replays, and incomplete deferred/M27 presentation
selectors off instead of inheriting them from the parent process. The exact
CharInfo sky and GridDeco/Far own normal background pixels; a failed source gate
exposes the black camera fallback rather than substituting an actor-bounds plate
or fitted clear color. ShadowPlane remains excluded despite source-closed mesh,
material, shader, and VisibilitySH inputs because its physical-camera stencil
and final color-target owner are not proven. SphereOutside and the post-Uber
portrait-depth sync diagnostic are likewise forced off. Camera aspect is derived
from the serialized sensor dimensions, and incomplete or non-finite source
camera, look-at, gyroscope, portrait-offset, lens, clip, or quaternion rows fail
closed instead of falling back to 16:9, zero vectors, or identity rotation.

Portrait alignment is likewise no longer a screenshot-fitting task. Lua and
raw RectTransform evidence confirm `CharInfoCamAttachment` at
`lookat_overview`, the authored overview-camera rotation, centered anchors and
pivots, canvas scale 0.0016, card size 900, settled anchored position
`(-300,50)`, and zero Endminf `overviewImgOffset`. All 31 generated Tight,
unrotated portrait meshes map bottom vertices to `vMin` and top vertices to
`vMax`. The exact selected D3D11
`CLIP_SCENEDEPTH + HG_WORLD_UI` program is now extracted from Endfield blob 207;
its vertex/pixel SHA-256 values exactly match the retained manifest
`14b05d...e0d52` / `1ff3fa...f0546`. The vertex path transforms absolute
object-to-world position, subtracts `_WorldSpaceCameraPos_Internal` exactly
once when `_RenderPathInjected>0`, multiplies by the non-jittered view-without-
translation projection from the 720-byte `_UIRenderingConstants` prefix, then
applies destination-dependent `_HGFlipX/Y` only to clip X/Y. For an offscreen
target both flips are zero; an unrotated D3D backbuffer uses flip Y=1. The lab
now publishes that exact no-translation matrix/camera/flip contract only for
the post-Uber world-UI draw and resets it afterward. `charinfobgdeco_in` also
drives the recovered portrait from the Overview playback clock: CharTexture
alpha rises from 0 to 90/255 over one second and anchored X moves from -200 to
-300 over 3.5 seconds with the retained weighted tangents. Focused renders at
0, 0.5, 1.0, 3.5, and 4.4333 seconds validate startup fade, settled placement,
orientation, and coexistence with the source grid; any remaining bounded
layout discrepancy must be measured against the mapped clean frames rather
than corrected with a screenshot-only offset.

Full capture `20260828T004942Z` closes its own Endminf camera endpoint, but not
the endpoint of the clean reference recording used by the Unity harness.
GridFar's `_TransformVariables` in complete frames 2187, 2262, 2702, and 2775
publishes the identical world camera position
`(-299.99887085,300.99005127,-296.50051880)`. Relative to the source camera
`(0,0.998,3.5)`, actor root `(-300,300,-300)`, and look-at
`(0.022,1.225,0)`, this is camera-local gyroscope correction
`(-0.0011258671,-0.0079661010)` with only a negligible forward residual.
Inverting the recovered input curves gives normalized inputs
`(-0.000508373,-0.0000217753)`. The former pointer-coordinate guess
`(-0.4604167,0.9305556)` generated the much larger correction
`(0.2433200,0.1480061)`; a visible cursor position is therefore not the live
gyroscope state. A focused Unity render using that exact input shifted the
settled clean-video character about 50-60 pixels left and the portrait roughly
200 pixels left, so the endpoint is session-specific rather than a replacement
for the `2026-08-26_21-25-50.mkv` state. Canonical renders retain the clean
video's pointer-derived input; use the two environment input overrides above
when comparing directly with `20260828T004942Z`.

The neutral gray compatibility plate is now registered to the clean settled
recording independently of actor bounds. Its prior gradient was 9-16 display
levels too dark through the upper/middle field, while its UV-space bottom
vignette began too late and then fell to RGB 58-60 instead of retail 107. The
plate now uses a neutral/slightly warm measured grade and applies only its
empirical lower rolloff in normalized screen space; GridFar and the portrait
remain source-authored world geometry. At 1920x1080, side-region medians for
clean frame 407 versus the focused 7-second Unity render are respectively
`136/133`, `171/171`, `186/184`, `192/192`, `181/187`, `126/133`,
`111/110`, and `107/107` at y=`0,300,500,700,820,900,1020,1070`. The old Unity
values were `127,157,170,178,178,165,100,58`. This closes the large gray-field
grade/rolloff regression; the bounded y=820-900 delta remains downstream of
the compatibility-wall approximation rather than evidence for moving the
exact camera or GridFar transform.

The Endminf capture harness now preserves Texture2D pixel order end to end.
`ReadPixels`/`GetPixels32` and `SetPixels32` already share bottom-left ordering;
the former writer and reader each applied an extra vertical flip, producing
misleading upside-down PNGs while keeping their internal frame-difference check
self-consistent. Removing both flips yields upright 4.4333-second peak and
7-second settled-loop captures with valid retained secondary replay, source
GridFar, portrait, and no foreground UI. This is a validation-output correction,
not a render-pipeline or camera adaptation.

The opening camera effect is a short horizontal slice/fracture transition
layered over a weaker radial/chromatic ghost, not generic distortion or square
mosaic pixelation. Clean reference frames 4-22 bound the visible body-relative
phase to about 0.033-0.350 seconds (one-frame anchor uncertainty): neighboring
hard-edged, variable-height horizontal bands preserve scene imagery while
applying different constant X offsets, with only small cyan/red edge separation.
The recovered final Uber has no row-displacement schedule, and the later
`baofahengxian` additive particles begin around 2.4 seconds, so neither owns
this fracture. A source-equivalent owner still requires an opening graphics
capture of consecutive source frames 89-112 and the scene-color resources
before/after each full-screen draw. Until then, any implementation must remain
a narrowly timed pre-Uber scene-color slice pass and retain the broad ghost as
an independent weaker layer.

EndfieldCapture Numpad 4 now requests 24 one-present packages followed by 40
packages at six-present spacing in one bounded session. Publication
backpressure means the first 24 are not guaranteed consecutive: session
`20260827T183054Z` completed all 64 packages but observed mostly 9-12 presented
frames between early packages. It still spans gameplay through the complete
overview burst and closes exact IA plus owned PS resources for M29 (8 packets),
M30 (6), and M31 (15), including the formerly missing scene-depth payloads.
The 64-package limit and 128-MiB targeted per-package cap remain unchanged;
Release x64 and all 15 native tests pass.

The same session corrects the final Uber identity. Active frames 1600 and 1818
use VS `A8C084C37EBA0ECC` and PS `86A732CEF7EEDB15`, the retail
`BLOOM + RADIAL_BLUR + VIGNETTE` variant, rather than the previously selected
`RADIAL_BLUR_CHROMATIC_ABERRATION` variant. Frame 1818 captures exact VS b0,
PS b0[28], and PS b1[26]; live c0 is approximately
`(0.5100073,0.5330563,0.1088480,1)`. The Unity native transport now embeds that
4,216-byte pixel program, preserves all captured vignette/bloom/LUT constants,
patches only screen/exposure and dynamic c0 radial lanes, and creates explicit
typed SRVs for Unity's typeless FP16 backing resources. The focused 4.4333 s
render validates one native draw with no failure and removes the false RGB
split. Ruri decompilation closes its radial source kernel: center plus five
same-RGB `SampleLevel` taps at factors `0.5,1,1.5,2,2.5`, averaged by `1/6`.
The canonical compatibility shader now uses that kernel instead of the older
per-channel combined variant. At matched 4.35-second phase the focused D3D11
full-frame PSNR changes `18.5790 -> 18.7057 dB` and the conspicuous RGB
silhouettes disappear. Keep chromatic curve transport for producer auditing,
but do not apply it as channel-separated source taps at this captured peak.
The broad M31 ring/shell, gas, and missing stones remain the dominant peak
mismatch; the neutral radial average alone does not close those owners.

The clean opening reference contains horizontal slices throughout ticks 4-20,
while the current explicit rectangle table closes only ticks
`4,6-12,18-20`. Do not fill the missing ticks with one repeated procedural
band: their rectangles, displacements, and RGB edges vary per frame. The next
valid automatic opening capture must retain the source before/after fullscreen
surfaces needed to close ticks `5,13-17` and the additional bands on already
admitted ticks.

Frame 1818 also closes a narrower exact M31 checkpoint: two owner-gated
`M_fx_endminm_gfx_31` draws (metadata draw indices 13 and 20) share the captured
scene-depth input and one 256x256 BC7-sRGB main texture, and use the exact
`62A5CE6C09171DE9` / `5558DEDDB1EE6188` shader pair. The native Unity route
suppresses exactly the two live M31 renderers, submits both captured IA,
constant-buffer, texture, and depth packets to SceneColor/SceneMV, and validates
two draws with `S_OK`. Direct backbuffer matching places frame 1818 at clean
extracted frame 264, so the viewer-request clock is 4.3500 seconds (the body
Animator is two 60-Hz ticks ahead at capture time), not the former inferred
4.4333-second anchor. Its upright
output is visually equivalent to the compatibility checkpoint and does not
restore the clean reference's large smooth orange loop. A diagnostic that
treated repeated 3840x2160 values in the shared vertex/pixel globals as freely
patchable screen-size lanes produced a screen-wide invalid result and was
reverted; those buffers are not a safe generic resolution-adaptation surface.
This bounds M31 as a proven secondary checkpoint layer, not evidence that its
two peak draws alone own the missing broad shell. Recover the temporal M29/M30
composition and exact queue ordering before changing source tint, curves, or
particle timing.

The same capture now drives a coherent six-packet M30 replay from frames
1753/1764/1775/1785/1796/1807, with captured IA, constants, one BC7 texture,
and live scene depth. Direct backbuffer matching maps those packets to clean
frames 182/195/210/224/238/251 and viewer-request phases
2.9833/3.2000/3.4500/3.6833/3.9167/4.1333; capture frame deltas are not an
animation clock because synchronous readback stalls presentation. Focused renders validate
one native draw per active packet with `S_OK`, but M30's isolated final output
is subtle and does not create the missing smooth peak loop. Retail queue
ownership is now bounded as M31=2999 and M29/M30/M14=3000; the relative order
inside queue 3000 is not preserved by the capture's priority-retention array.

Session `20260827T225644Z` closes the formerly missing fixed-function and
draw-local IA state for the open-palm stone-halo checkpoint. Its complete
targeted frame 2723 retains 32 priority draws through retail ordinal 88, with
valid topology, draw ordinals, IA offsets, constants, resources, samplers,
blend, depth/stencil, rasterizer, viewport, and scissor. It proves exact M29 at
ordinal 73 and a 15-draw shared VFXBaseV2 cohort at ordinals
68,74-81,83-88. Both native transports validate `S_OK`; the cohort is replayed
only at clean frame 219 / viewer-request phase 3.6000 and no longer contaminates
the later burst. The targeted 32-draw priority set can still displace smaller
stone, gas, and peripheral shell owners, so it is not full peak closure.

M29 now combines the eight temporal packets from `20260827T183054Z` with the
frame-2723 draw contract. Unsafe old shared-ring geometry is replaced by the
exact draw-local 60-byte packet geometry, so all nine packets are replay-safe.
Direct clean-reference matches map source frames
1732/1743/1753/1764/1775/2723/1785/1796/1807 to viewer-request phases
2.5500/2.7333/2.9833/3.2000/3.4500/3.6000/3.6833/3.9167/4.1333. The prior
presented-frame anchor was wrong. The exact M13 burst owner is now a
three-packet transport. Targeted capture frames 5395 and 5404 match clean
frames 266 and 275; Full frame 2775 matches clean frame 273. They use phases
4.3833, 4.5000, and 4.5333, retain distinct draw-local geometry/constants with
the same five BC7 textures, and select the nearest packet without interpolation.
Full frame 2775 also closes the formerly guessed sampler contract: retail uses
s0 Wrap and s1/s2 Clamp, while the native replay had those policies reversed.
Correcting the addressing restores the large smooth amber ring; shader/layout,
BC7 creation, and the runtime callback all validate `S_OK`.
Focused `temporal_rephase_v2` renders validate M13, M29, M30, M31, the shared
15-draw cohort, and the exact Uber transport. They remove the former broad
open-palm contamination from the crystal peak. The M13 ring is now present;
gas, peripheral particles, retail temporal history, and exact equal-queue
composition remain open.

EndfieldCapture Full now retains up to 96 draw records, 64 resources, and a
128-MiB resource payload. The 96-record temporary and per-frame storage is heap
backed, avoiding the stack overflow that crashed the earlier Full prototype;
all 15 Release/WARP/proxy tests pass with no game process owning the global
events. Session `20260828T004942Z` validates that path with four complete
Numpad-1 packages, no dropped events or truncation flags, and 100.6-105.8 MiB
resource blobs. Frame 2262 directly matches the clean open-palm neighborhood
(best match 222) and contains five physical stones plus their amber halo;
frame 2775 matches the burst neighborhood (best match 273) and contains the
large ring, core, stones, haze, and particles. Full retention exposes three
peak-only non-priority draws omitted by Targeted: ordinal 74 (1,110 indices,
shader pair `e7f5568d34fd467b/c5b21fee8e9936a6`), ordinal 82 (900,
`7d1953e7b7d5310f/601242f701cb4380`), and ordinal 87 (1,764,
`7f5111cf80387bee/a3c9bfc94f0caea9`). They classify respectively as the
M21 `_02 shitou shell` stones, M18 `_02 kuosan` amber diffusion shell, and
M28 refractive sphere. M21 now has a hash-pinned frame-2775 native packet with
1,080 draw-local 52-byte vertices, 1,110 R16 indices, exact DXBC/constants,
white-texture default, premultiplied blend, and retail depth state. Direct byte
inspection closes its input layout as full-float position/normal/tangent,
RGBA8 color at byte 40, and float2 UV at byte 44. WARP validates its two shader
stages and layout, and the focused Viewer callback completes `S_OK`; the stones
are restored. Their final-frame enlargement is downstream Uber/temporal trail,
not a reason to resize the exact geometry. M18 now has the corresponding
hash-pinned ordinal-82 packet: 204 draw-local 76-byte vertices, 900 R16
indices, exact DXBC/constants, and the five source material texture slots from
`M_fx_endminm_gfx_18`. Direct byte inspection closes its layout as full-float
position/normal/tangent, RGBA8 color at byte 40, and two float4 UV lanes at
bytes 44 and 60. WARP validates both shaders and the input layout, the focused
Viewer callback completes `S_OK`, and an M18-on/off diagnostic changes every
stage from the pre-temporal source through final Uber. The source texture
closure is logical rather than capture-byte-identical because the Full frame
did not retain this draw's SRV payloads; do not claim exact texture bytes.
M28 now has the corresponding hash-pinned ordinal-87 packet: 344 draw-local
60-byte vertices, 1,764 R16 indices, exact instanced VFXRefract DXBC/constants,
the source `T_fx_flow_121_M` and `T_fx_mask_17_C_M` texture identities, and a
persistent packed-HDR snapshot of SceneColor for t2. For
`T_fx_flow_121_M`, exactness means the hash-pinned decoded PNG plus the
recovered 256x256, nine-source-mip, sRGB, Bilinear, Repeat, aniso-1,
zero-mip-bias, mipmapped, non-streaming Texture2D/importer profile. It does not
mean that the original native BC7 mip bytes were retained or reproduced. The
snapshot is copied immediately
before the draw, breaking the D3D11 SRV/RTV alias while the shader writes the
live SceneColor+SceneMV MRT pair against the retained depth target. WARP
validates both shaders and the input layout; the focused Viewer callback
submits one draw and completes `S_OK`. The default scene deliberately omits
the old approximate M28 material, so Editor validation resolves the pinned
generated material asset directly while suppressing the source Particle
System (9) node by exact effect-root identity. Player-build resource
publication for that otherwise-unreferenced material remains an explicit
packaging gap, not a reason to re-enable the approximation.

Full frame 2775 supplies one authoritative 60 Hz packet for each of M18, M21,
and M28; it does not establish a seven-frame animation window. Their exact
runtimes therefore admit only the nearest simulation sample (`+/-1/120` second)
and restore the authored particle renderer on adjacent ticks. A phase-matched
13-frame A/B against the clean recording improves mean effect-ROI MAE from
34.214 to 34.018 and temporal-delta MAE from 28.157 to 27.978 versus the former
`+/-0.05`-second repeated-packet control. Keep geometry, UVs, tint, and bloom
fixed unless another captured frame supplies a different packet.

The complete M21 stone-shell packet is now enabled in the normal interactive
Endminf reproduction profile. A fresh isolated three-frame targeted A/B at
4.4833/4.5000/4.5167 seconds improves effect-ROI MAE on every row
(35.684/34.622/33.270 to 35.463/34.550/33.233) and leaves M18/M28 opt-in;
the latter still lack an equally complete temporal or captured-texture
contract. Enabling all sparse exact peak transports together is rejected as a
canonical default: over the 4.30-4.75 second window it improves temporal-delta
MAE 23.470 to 22.662 but worsens ROI/effect MAE 24.211/29.160 to
26.623/32.448 because one-tick packets suppress authored neighboring output.
The corresponding 770-frame M21-only canonical render passes every sequence,
background, VFX-cleanup, and no-foreground-UI gate, submits and validates M21
exactly once at 4.5000 seconds, and improves aggregate ROI/effect/temporal MAE
from 21.6325/22.7560/14.1828 to 21.6304/22.7547/14.1827. Canonical video
exports therefore default this owner on; an explicit environment value of `0`
remains a full-sequence A/B override.

The Viewer report schema now records requested, active, submitted, validated,
and failure state independently for the exact M18/M21/M28 packets. A focused
60 Hz run proves all three are submitted and callback-validated only at the
4.5000-second sample, with adjacent rows inactive and failure-free. A separate
exact-Uber A/B around 4.35-4.55 seconds retains the pre-Bloom temporal resolve:
disabling it worsens mean character/effect ROI MAE from 27.935/35.212 to
28.375/35.623. The broad peak blur is therefore not evidence for bypassing
history or moving Uber ahead of the recovered temporal stage.

An earlier comparison-only experiment advanced the authored 4.4333-second
late-pulse key by five 60 Hz samples to align it with retail frame 1818. It
improved the 11-sample character/effect/temporal metrics from
27.935/35.212/29.301 to 27.581/34.690/25.685, but it fitted the reference video
and did not recover the missing outer effect-start owner. That shifted curve is
retired; the runtime now retains the exact serialized key and coefficients.
Keep temporal -> bloom -> actor-inclusive exact Uber ordering intact and close
the outer clock from source/runtime ownership before interpreting residual late
echoes. The subsequent 770-frame exact-Uber render completed without a crash and kept
the best global phase offset at -1; its aggregate ROI/effect/temporal MAE is
21.134/22.069/11.889. Do not compare its first two aggregates directly with
the older 20.972/21.937 compatibility-Uber run, because that baseline did not
request the native exact Uber. The full verifier still fails closed on the
pre-existing incomplete eleven-row LitEffect plus exact `suikuai (1)` binding;
successful image export alone does not close that admission gap.

The retained exact `overview_02/all/suikuai (1)` branch now survives focused
character/effect rebuilds even when the disposable broad importer stage is
absent. Its targeted repair accepts the one known stale fail-closed boundary
(authored-enabled marker, disabled renderer, empty material array) only after
revalidating the pinned source material, BlendTex, four-mesh palette, shader,
PathIDs, and particle contract. A canonical 41-frame Viewer run now passes
`status=ok` with 68 admitted renderers, exactly the two expected blocked rows,
and live `M_fx_common_teleport_03` VFXRefract shards through transition and
cleanup. This closes the former misleading eleven-row LitEffect/`suikuai (1)`
admission failure; it does not replace the still-needed M20 capture.

The distinct drifting plume is not one of those three draws. Source evidence
identifies `overview_02/all/smoke (2)`, material `M_fx_endminm_gfx_20`, starting
at 4.46 seconds with six near-peak billboards and textures
`T_fx_smoke_100_M`, `T_fx_flow_01_M`, and `T_fx_flow_121_M`. Neither expected
M20 shader pair nor a 36-index draw appears in Full frame 2775, whose direct
match is clean frame 273. Exact M20 replay therefore needs one priority capture
around clean frames 276-281 after the current M18/M28 evidence is integrated.

EndfieldCapture now priority-retains both exact source-compiled M20 shader
routes: non-instanced VS/PS `e8f38f2f7519383d`/`fea38543389b6ff4` and
SRP-instanced VS/PS `4bef98c73ca34880`/`246a0f4f2d3c34f4`. The retained packet
includes draw-local IA, constant-buffer allocations, samplers, and PS resources.
The exact-Endminf trigger starts one 72-package sequence without human input in
both the graphics-only proxy and general runtime: 24 opening requests as quickly
as the complete-frame lifecycle permits, then 48 at six-Present target spacing.
The request-target arithmetic ends at relative Present 311, but that is not the
captured-frame span. Every request needs one Present to arm the following frame
and another to complete it, so the ideal first-to-last package span is at least
453 Presents (about 7.55 seconds), with full-profile readback able to widen it.
This crosses M20's 4.433-second onset and cleanup when the overview remains
alive for at least ten seconds. Automatic full sessions `20260828T224210Z` and
`20260828T224407Z` close the live identity gap: retail binds a third VFXBaseV2
route, VS/PS `62a5ce6c09171de9`/`5558deddb1ee6188`, rather than either
source-compiled pair. Session `224210Z` is the cleaner authority: it completed
all 72 packages with zero drops and retains five 36-index packets, including
frame 1748 near the expected plume onset, plus IA, VS t0, PS t0-t1, constants,
samplers, and the complete shader archive. The retail program is shared by
unrelated VFX draws, so identity-only admission is unsound; require the measured
36-index peak geometry. Its pixel route samples only scene input t0 and one
atlas-backed Main texture t1. This supersedes the extracted source-variant
assumption that M20 necessarily samples the standalone Main/Sample0/Sample1
texture trio and explains the shifted plume UV in the compatibility render.

The first automatic-trigger implementation admitted only source-combined Uber
fragment prefix `3f490e1504c43554`. That is insufficient: validated live capture
`20260827T183054Z` and the native Unity exact transport both use the independent
Endminf `BLOOM + RADIAL_BLUR + VIGNETTE` fragment prefix
`86a732cef7eedb15`. The live identity belongs to a reusable post-process family,
so admitting it directly could consume the one-shot sequence before Endminf.
The recovered Endminf LOD0 body has one 16,524-index submesh, that count is
unique across the current playable-character mesh export, and live capture
observes the exact `DrawIndexedInstanced(16524,1,0,0,0)` before its Uber pass.
EndfieldCapture therefore lets the source-combined route arm directly but gates
the validated live route on that prior body draw. Adjacent shader identities and
nearby draw arguments fail focused tests; Release x64 and all 15 native tests
pass. Sequence intervals are target Present spacing rather than a promise of
consecutive packages: the next request waits for prior readback/publication, so
frame IDs in the live result remain the authority for actual cadence.

Both decompiled M20 vertex variants declare a VS t0 `ByteAddressBuffer` and
contain live structured loads for their skin/instance branches. EndfieldCapture
now retains that draw-local VS t0 buffer in addition to M20's IA, VS/PS
constants, samplers, and six PS resource slots. The WARP test covers vertex-SRV
buffer readback, stage/slot ownership, coexistence with compute aliases, and IA
alias publication; Release x64 and all 15 native tests pass. This closes a
capture-tool omission before the next live run rather than discovering an
unreplayable M20 packet afterward.

The unattended sequence should use the `full` profile. Its selected-resource
table now retains 96 entries, matching the 96 indexed-draw records, while the
aggregate payload remains bounded at 128 MiB. This leaves metadata capacity for
late exact M20 IA/VS/PS owners after broad full-profile collection. Release x64
and all 15 native tests pass with the enlarged bounded table.

The combined graphics validator now recognizes that unattended workflow as a
separate fail-closed policy instead of requiring the retired two-burst shape.
An automatic session must report the exact Endminf trigger, automatic ownership,
72 completed packages, inactive/quiescent sequence state, no pending frame,
zero dropped events, and one 72-package logical sequence before the existing per-mesh
palette and M29/M30/M31 resource-closure gates run. Runtime status owns the
single logical window, so full-profile readback stalls cannot be mistaken for
separate bursts merely because frame IDs have a large gap. Old 64-package
sessions remain on the legacy two-burst policy and cannot accidentally certify
the new workflow. The focused validator suite has ten passing tests.

A focused M21 ablation also clarifies its presentation boundary. Its source
material has no authored texture and the zero VS buffer is valid for the
non-skinned branch; the exact frame-2775 stones become most visible in following
temporal-resolve samples. Disabling the one-frame packet removes those stones
from the follow-up sequence, so M21 remains canonical. A single targeted PNG at
the callback tick is not a valid M21 visibility test.

Decompiling source variants 0876/0877 and 4950/4951 closes M20's static sampler
ABI: t0 scene depth uses LinearClamp, t1 Main uses LinearRepeat, t2 Sample0
uses LinearMirror, and t3 Sample1 uses LinearMirrorOnce. The recovered BaseV2
shader previously used texture-paired samplers (and PointClamp depth) for this
soft two-sample specialization. Keep these routes because bytecode proves the
ABI, not because one noisy aggregate happens to improve. Focused runs have a
three-image shader/mip warm-up boundary: images 3-12 and all reported M20
particle states repeat byte-for-byte, while images 0-2 vary after every process
start. On the stable ten-image suffix, paired versus exact samplers score
26.642271/30.849221/21.745348 versus 26.650365/30.863199/21.739843
(ROI/effect/temporal-delta MAE): spatial movement is a tiny regression and
temporal movement a tiny improvement, both dwarfed by the unresolved transport
gap. Extending stock Unity's packed particle-color translation to M20 and
routing Sample0 custom speed through retail Custom1.Y were separately tested
and rejected; retail c13/stream carriers are not equivalent to multiplying or
reinterpreting the current extracted procedural streams. The admission
verifier hash-gates both M20 source pairs and the exact sampler translation.

The clean recording's late cursor move remains useful validation that the
source gyroscope is dynamic, but its observed samples, endpoint, and timing are
not implementation inputs. The earlier recording-specific endpoint/track A/Bs
are superseded diagnostics and must not become canonical defaults or corrective
camera offsets. Closing the remaining live-input boundary requires Beyond's
virtual/controller provider or exact runtime provider state; it does not
justify changing FOV, actor scale, portrait placement, GridFar, or adding a
screenshot-fit transform.

The CharInfo portrait's earlier inversion was a tight-sprite UV error, not
another RectTransform or camera offset. The exported PNG is display-upright
and TextureImporter already maps its rows to Unity's bottom-origin sampling,
so generated portrait quads now map bottom vertices to `vMin` and top vertices
to `vMax`; a second vertical flip or full-texture `1-v` transform is wrong.
A focused D3D11 render is upright and improves the portrait-left ROI MAE from
about 29.7 to 27.5 against the clean reference despite a three-tick pose
difference. Every playable profile now has a fail-closed mesh/importer
orientation verifier. Keep the recovered Lua/layout placement fixed.

M01/M38 stone texture identity is closed: their Unity materials bind the exact
recovered base, RG normal, MRO, and parallax maps. The physical shader samples
BaseColor/Normal/MRO/Parallax/Mask/Noise through t0..t5 with the exact static
samplers listed above; MRO is metallic/roughness/occlusion in R/G/B, the
parallax march reads Noise.r, and final parallax color reads Parallax.g. The
flat-yellow surface came from the forward compatibility path, not from missing
stone textures. Its shader now preserves those source sampling/channel gates
and bounded GGX behavior, but it is still a non-exact ForwardOnly substitute
for retail HGBuffer/deferred lighting. Do not tune its light model, texture
scale, owner placement, or effect curves as if it were exact presentation;
deferred light/shadow/frame ownership and peak composition remain open.

The LitEffect fallback now preserves more of that source boundary before its
explicitly approximate GGX evaluation: Base/Normal/MRO/Parallax samples use the
live `_GlobalMipBias`, noise-march derivatives use the live
`_GlobalMipBiasPow2`, base color applies the authored brighter/tint-cover
equation, two-sided normal handling is retained, and unclamped source
metallic/roughness/occlusion values remain distinct from fallback-only safety
bounds. The rebuild gate verifies those extra material fields directly against
all three exported M01/M27/M38 JSON objects. The non-generative M27 HGBuffer
port also uses the validated shared runtime fixed state (`ZTest GEqual`, depth
write, `Cull Back`) instead of the serialized shader dump's unresolved
Off/Off placeholders. Its compatibility lighting no longer invents a fixed
direction: it consumes the serialized CharInfo `sceneMainLight` direction and
clips when that direct-reference provenance is unavailable. This corrects
source transport, not retail presentation: exact deferred LightData GPU words,
ShadowData/atlas GPU contents, physical-resource alias/lifetime, frame readiness,
and owner chronology remain fail-closed, so no shadow term, material multiplier,
placement, curve, timing, or capture packet was tuned or replayed.

The measured opening-fracture reconstruction is diagnostic-only. Clean-reference
frames 91-109 establish a bounded table for effect-clock frames 4-20, but its
explicit destination rectangles, pixel offsets, and RGB separations describe
screenshots rather than the missing retail producer. The table did not produce
a proven full-sequence gain and the retained fullscreen chronology places the
strips in SceneColor before Uber. Canonical batch capture and the interactive
launcher therefore leave
`ENDFIELD_ENDMINF_MEASURED_OPENING_STRIP_DIAGNOSTIC` unset; the evaluator and
pre-temporal pass both fail closed without that explicit diagnostic flag. A
41-frame and a complete 770-frame D3D11 render apply the measured pass in zero
frames while preserving the source-authored transition, loop, portrait, and
VFX gates, with no crash or device-removal signal. Recover the pre-Uber
geometry/material owner and its temporal consumer instead of expanding or
tuning the rectangle table.

Canonical batch video export currently defaults only to the validated exact
M13, one-sample M21, and ordinary/peak Uber paths. M14, M20, M27 deferred
presentation, M29/M30, M31, and the public NGX proxy remain controlled
diagnostics; transport submission alone is not visual admission. An explicit
environment value, including `0`, remains an A/B override. M27 already consumes
the four exact captured base/MRO/normal/parallax textures, and M21's textureless
white default is source-valid, so the remaining visibly wrong stone appearance
belongs to deferred lighting/compositing and gas transport rather than texture
extraction.

M27's prior `presentationReady` signal was not visual proof. A peak-targeted
same-command readback showed GBufferC claiming all 2,073,600 pixels while the
presentation changed zero. SceneColor identifies only the 1,801 emissive
fragments and is not a complete ownership mask: it discards deferred-lit stone
faces. The exact Default Lit resolver has the opposite row orientation, with
zero nonzero samples at direct coordinates versus 1,730 at mirrored Y. Both
presentation passes now use the isolated sidecar's positive reversed-Z depth as
the complete M27 owner while retaining mirrored-Y resolver sampling, depth
before ForwardOpaque, and color after ForwardOpaque. A focused D3D11 probe at
4.4833/4.5000/4.5167 seconds is `targeted_ok`; the joined diagnostic measures
1,801 emissive pixels, and the peak same-command presentation changes 1,671,106
pixels while visibly restoring dark angular stone pieces around the hand and
burst. Frames 2978-3027 remain identity-gated as M27; earlier M01/M38 draws
sharing the shader pair remain excluded. A controlled 1920x1080 A/B at
0.5667/1.9833/4.1667 seconds proves that this exclusion is necessary: routing
those early packets through the M27 private-depth presentation introduces
large black/gray triangles across the backdrop, while the hand-gated control
does not. Recover the early rows' distinct owner transforms/state before
attempting exact deferred M01/M38 presentation. The preceding complete 770-frame
sequence still scores 21.4410 actor ROI, 22.2208 effect ROI, and 11.8080
temporal-delta MAE versus the prior 21.2970/21.8941/11.9846; the private-depth
correction has not yet received a complete-sequence comparison or user review.
Treat the remaining color/gas gap as deferred light/resource and transport
recovery, not as solved fidelity or a texture-substitution problem.

Automatic full session `20260828T121603Z` closes the hair/cape capture gap.
All 72 packages contain one unambiguous body, hair, and every
`cloth_01`-`cloth_04` LOD0 palette, with zero drops or incomplete packages.
The v6 replay uses both previous/current palettes for 144 samples and writes
all 74 primary dynamic bones plus the six transparent-cape
`clothes_touming_{L,R}_b_{1,2,3}_jnt` bones. Their parent and child tracks now
come from the same session, so the former fail-closed sparse extension is
runtime-eligible. Present IDs are not a clock: full readback stalls produce
0.135-0.250 s package gaps. Sample times therefore come from capture QPC,
anchored by exact Uber frame 1977 at 4.35 s, and preserve the immediately
previous 60 Hz palette. The generated 144-sample/80-bone asset validates and a
targeted D3D11 run reports the replay bound and applied at every checkpoint.

A focused post-integration audit rejects another fixed hair/cape clock or
bone-space offset, but does not close temporal fidelity. All 80 recovered bones
bind and apply, root-space transforms remain orthonormal at unit actor scale,
and retail-versus-Unity motion correlation is 0.78-0.90 with best offsets
within two frames. However, the 144 retained states are 72 previous/current
pairs spread across 13.87 seconds: 70 interpolation intervals exceed eight
60-Hz frames and the worst hole is 14.03 frames. Linear position interpolation
and quaternion Slerp suppress unsampled extrema and create the visibly
constant-arc hair motion. Thresholded motion remains narrower by about 6.5%
for hair, 16% for the left cape, and 32% for the right cape. Dense native
palette cadence is therefore the primary missing owner; post-skin output,
alpha/depth visibility, and temporal softness remain secondary silhouette
gaps rather than justification for inventing intermediate bone transforms.

The first downstream renderer-state audit found two real compatibility
regressions. `M_actor_endminf_cloth_03` is source-opaque alpha-test despite its
legacy alpha-content hint and `BlendMode=4`; material setup must not normalize
it into transparent blending. Pipeline disposal also must not overwrite the
transparent hair shell's captured `ZTest Less` with the general `LessEqual`
fallback. The global reset is now opaque-only, while the transparent cape
retains queue 3000, `Cull Off`, and its captured depth state. The body-material
and CharacterOutline verifiers pass, but this correct state does not by itself
close the remaining post-skin silhouette/visibility gap.

The corrected chronological camera/background audit rejects every fixed
portrait, actor-root, camera, FOV, or GridFar nudge. The earlier apparent
50/130-pixel settled displacement was caused by pairing wrapped loop-local time
as though it were continuous sequence time. With chronological pairs, actor
scale is 0.9992 with about (+0.2,-0.4) pixel displacement and portrait scale is
0.9977 with about (+0.6,+0.2) pixel displacement. Static framing is effectively
closed; only a small late same-session gyroscope state residual remains.

The same session strengthens but does not complete peak/opening effects. It
retains exact M29/M30 resource closure and nine M31 phases from 2.863329 to
4.564017 s with draw counts `2,2,2,2,2,2,2,3,1`. All 18 M31 draws now own
their exact temporal-frame geometry, constants, and secondary stream in the
generated native contract instead of replaying frame 1818 at every phase; the
shared BC7 texture remains byte/hash pinned. The native temporal selector
accepts only rows 0-6, whose two draws have the proven
`M31 -> M29/M30 -> M31` split, and maps event 0/1 to that row's own payloads.
It rejects the encoded three-draw peak, one-draw tail, and out-of-range rows
before renderer suppression or submission. Those unsupported rows therefore
restore the ordinary renderer rather than substituting constants or geometry
across incompatible packet shapes. Fixed-function replay for the supported
route is now owned by the dedicated M31 contract described below; a hardened
retail recapture still has to close the remaining live view descriptors and
runtime validation. No M20 shader identity
occurs, and the only opening-strip package inside the maintained 0.0667-0.35 s
interval is frame 1758 at about 0.2325 s. This capture therefore must not be
used to invent M20 ownership or expand the partial strip table. Runtime strip
admission now exactly matches shader-backed frames and no longer issues the
unsupported frame-13 no-op pass.

The older canonical M27 payload remains authoritative because this session
lacks its exact 1,080-index/15-copy peak. Its runtime clock is now normalized
from the live actor animation every frame by the established two-tick viewer
lead. Requested 4.5000 s therefore selects frame 2978's 15-stone peak rather
than frame 2987's four-stone tail. A focused D3D11 run validates the native
packet and preserves 921 deferred-presentation pixels into the saved frame;
this fixes missing geometry but does not close the known dark/gray deferred
lighting gap.

Although all 72 automatic packages published, their QPC gaps are
135.2-250.5 ms (195.1 ms mean), with every gap over the 25 ms native-cadence
limit. Full-profile synchronous readback therefore makes this session valid
for retained packet/resource closure and same-session palette identity, but
not as a Present-spaced opening or short-lived M20 clock. Automatic capture
now has a bounded 72-slot/4-GiB deferred staging ring: Present callbacks copy
per-slot backbuffer, selected resources, and metadata without synchronous
mapping; later Presents drain with render-thread `DO_NOT_WAIT`, and the worker
publishes only CPU-ready packages. Release builds and all 15 synthetic/WARP/
proxy tests pass, including deferred copy/map byte validation. This closes the
tool architecture in tests, but the first real-game run must still prove
`72/72` staged, drained, and published with `cadenceValid=true` before it is
accepted as native-cadence temporal evidence.

The current split-M31/80-bone checkpoint has a complete 770-frame D3D11
render and a 558-frame clean-reference comparison. Within the documented
one-frame anchor uncertainty, offset -1 is best at 22.7765 actor-ROI MAE,
23.5194 effect-ROI MAE, and 12.2248 effect temporal-delta MAE. Against the
earlier clean-gyroscope checkpoint (23.7086/23.6431/13.7609), this improves
actor alignment, effect spatial error, and especially temporal behavior, but
does not close fidelity. The peak window remains 25.4235/29.1226/19.8482; its
largest visible omissions are the broad flash/gas and shell composition.

The first exact M13 packet is source-matched at 4.3833 s. Its former
nearest-packet window repeated that ring backward to 4.325 s, producing the
large white ring at 4.35 s where the clean reference has none. Admission now
uses a one-tick lower bound for the first packet while preserving the
established continuous nearest-packet suffix. A focused D3D11 comparison at
4.35/4.4167/4.50 improves effect-ROI MAE to 33.8108 versus 34.4416 for
fully sparse exact admission and 34.9943 for ordinary M13 rendering.

The captured combined Uber packet is not a reusable animated post shader.
Capture `20260827T183054Z` frame 1818 contains the active
`BLOOM + RADIAL_BLUR + VIGNETTE` variant at overview phase 4.350000 s, while
its PS constants retain frame-local values including chromatic intensity.
Replaying it over the full sequence regresses 558-frame spatial and temporal
metrics and visibly creates a severe full-character smear. The exact transport
therefore remains default-off and admits only the nearest 60 Hz sample around
4.35 s when explicitly requested; adjacent frames use the compatibility Uber.
A focused D3D11 run proves submission only at 4.350000 s and no submission at
4.333333/4.366667 s. Even that one exact frame is rejected from canonical
presentation by the clean-reference visual boundary, not promoted on a small
static-MAE improvement.

Frame 1600 from the same capture closes a second exact combined-Uber constant
payload. Its retained radial/chromatic lanes solve the authored curves to
0.02256267 s, while its accumulated UI-bearing backbuffer registers to clean
reference frame 8. A one-sample native replay is technically valid but is also
rejected from presentation: versus the restored smooth/upright 770-frame
baseline at source offset -1, first-frame character/effect ROI MAE worsens by
6.53/1.85, and first-30-frame temporal-delta MAE worsens by 0.48. Preserve it
only behind `ENDFIELD_RECOVERED_ENDMINF_UBER_EARLY_DIAGNOSTIC=1`; canonical
video export and the interactive presentation continue to use the ordinary
Uber shader at this early sample.

The clean canonical cloth-state render at
`exports/endminf_overview_20260828_cloth_state_fix/frames` completes 770/770
with exact Uber disabled. At offset -1 its 558-frame scores are 22.9257 actor
ROI, 23.8478 effect ROI, and 12.1997 temporal-delta MAE. The renderer-state
correction slightly improves temporal behavior but increases raw spatial MAE;
retain it because the state is source-backed, and do not compensate by
inventing alpha or depth values. Five-stage peak diagnostics also reject a
global bloom increase: the recovered peak crosses from under- to over-bright
within adjacent samples, so the remaining gap is flash/gas ownership and pulse
shape/timing rather than one global intensity scalar.

The next complete D3D11 checkpoint at
`exports/endminf_overview_20260828_radial_uber/frames` also completes 770/770
with temporal resolve enabled, exact packet replay disabled, the Character Info
background and portrait present, and foreground UI absent. Ruri decompilation
of the active retail `BLOOM + RADIAL_BLUR + VIGNETTE` pixel shader proves that
its radial path averages the center sample with five same-RGB taps at radial
factors 0.5, 1.0, 1.5, 2.0, and 2.5; it does not apply the prior compatibility
RGB channel split. Replacing only that sampling equation removes the invented
colored silhouettes. At the same offset -1, the 558-frame scores become
22.8468 actor ROI, 23.6537 effect ROI, and 12.4339 temporal-delta MAE: spatial
error improves by 0.0788/0.1940 while temporal error regresses by 0.2342. Treat
this as a bounded source-correct transport improvement, not closure of the
missing gas, stones, particles, opening-strip, hair, or cape gaps. Pause at
this checkpoint for user visual review before another complete render.

Frame-local M31 evidence does not justify admitting the three-draw 4.35-second
packet at the current compositor boundaries. Session `20260828T121603Z` frame
1977 closes all three M31 draw payloads, so a controlled native probe embedded
those exact draws at the available pre-cohort, mid-cohort, and post-M18
insertion points. Direct3D11 submitted and validated all three events, but the
matched clean-reference frame regressed actor/effect ROI MAE from
`25.1910/32.0855` to `27.2113/35.9731` and introduced a blue rectangular shell
absent from retail. The experiment was fully reverted. Treat frame 1977 as
valid packet evidence but keep its three-draw presentation blocked on exact
SceneColor and intervening-owner chronology; do not substitute its constants
into the older two-draw transport.

Automatic session `20260828T121603Z` contains the exact M21 shader pair in
frames 1977, 1989, and 2000, but it does not close the stone texture binding.
The capture hook did not classify M21 as a retained owner, so each M21 draw has
an empty draw-local resource table even though unrelated frame-wide textures
were read back. The serialized `M_fx_endminm_gfx_21` material has a null
`_MainTex`, which supports but does not prove Unity's white fallback. The
capture hook now recognizes the exact M21 VS/PS identities and retains its IA,
constants, and PS t0-t5 in the same unattended sequence as M20 and the other
peak owners. Release build and all 15 synthetic/WARP/proxy tests pass; one new
real-game automatic sequence is still required to establish the live M21 t0
resource and deferred 72/72 native cadence.

The first deferred real-game attempt, `20260828T155751Z`, failed before any
frame package was publishable. It staged 30 Full-profile frames, drained and
published zero, reached 4,259,378,888 bytes of the 4-GiB staging budget, and
then failed closed; `graphics/frames` is empty. The game subsequently exited,
but the deterministic staging exhaustion is sufficient to reject the old
architecture independently of the crash. Deferred capture now drains and
publishes completed slots while later samples remain active, releasing each
slot's GPU/readback allocation back to the bounded budget instead of waiting
for all 72 samples. Automatic sequences also suppress the broad per-frame
compute-resource sweep while retaining every draw/dispatch record, copied
constant/palette slices, the 4K backbuffer, and resources selected by exact
Endminf material owners. The rejected broad sweep copied a 63-MiB UAV plus
pooled 16-MiB buffers into otherwise redundant samples and could still outrun
single-package publication during the dense prefix. Superseded-DLL session
`20260828T160748Z` confirms that distinction: continuous drain published 18 of
48 staged packages, but their 141-155-MiB broad payloads still reached
4,269,389,000 staging bytes and failed closed. Its opening packages contain no
M20/M21 peak draw, so they are not dense cloth/hair or peak evidence. Their
3840x2160 DXGI-format-28 backbuffers are RGBA, not BGRA; decoding them as RGBA
preserves the retail opening-strip burst and correct colors.

The pruned automatic build is validated by session `20260828T181119Z`: all 72
Full packages published with no pending slot, failure, or drop, and its exact
M21/M27 packets, character palettes, and M29/M30/M31 closure are usable peak
evidence. It still is not a complete peak-owner capture. Its tail samples are
six Presents apart, and no package contains either exact M20 shader pair; the
strict combined validator now requires M20 and M21 explicitly and rejects this
session instead of accepting a superficially complete sequence. M21's live t0
identity has zero captured bytes, so its existing white fallback remains
source-compatible rather than byte-closed.

The same session closes the fullscreen-strip hypothesis without staging more
texture payload. Across all 71 normal-Uber samples, none of Uber's t0/t1/t2
resource identities matches an earlier retained `DrawInstanced(3,1)` RTV in
the frame. SceneColor therefore enters the retained fullscreen resolver chain
already containing the opening strips; do not attribute them to or invent an
additional pre-Uber fullscreen distortion pass. Recover their transport from
the pre-Uber geometry/material owners while retaining the measured rectangles
only as bounded visual evidence. M17 `baoshan` remains a separate crystal-peak
owner and must not be conflated with the opening fracture.

Sessions `20260828T181119Z` and `20260828T212621Z` close the opening owner's
shader, geometry, and static resource binding. Exact VFXRefract pair
`297e7323cb0a7c42`/`76db04f0bc22dd3e` submits four shrinking independent-quad
packets: 11,610, 7,998, 4,176, and 420 indices, or 1,935, 1,333, 696, and 70
quads. Every packet is overwhelmingly horizontal, uses the 60-byte particle
vertex layout, R16 indices, 3840x2160 target, and SrcAlpha/InvSrcAlpha blend.
The byte-identical programs already exist in AnimeStudio's exported
`HGRP_Effect_VFXRefract` variants 0546/0547 with `HG_ENABLE_MV +
SRP_INSTANCING_ON + _USE_RBOFFSET`. Their source owner is the shared Character
Info `CharEffect/trail` and `M_UI_charChoose_12`, not an Endminf overview
material. Unity reproduces the fixed-seed particle population closely: 1,930,
1,286, 608, and 10 live particles at 0.1500, 0.1833, 0.2167, and 0.2500 seconds,
bracketing the retained six-Present retail samples. The renderer is active,
has the exact material/pass, and is accepted by the Distortion request scan,
but stock SRP submission emits no visible generated particle geometry; even a
solid fragment and clip/depth probes remain absent. The retained D3D11 replay
closes submission transport: generated payloads preserve all four IA and
shader-used constant ranges and submit the exact 0546/0547 programs. Per-frame
diagnostics map requested phases 0.1500, 0.1833, 0.2167, and 0.2500 seconds to
capture frames 1034-1037 and validate every native draw with `S_OK`; clean-video
source frame 90 is requested phase zero, so those samples correspond to clean
frames 99, 101, 103, and 105. Session `20260828T212621Z` priority-retains five
more exact packets with 11,568, 7,956, 4,134, 372, and 60 indices. Their PS t0
owner is one byte-identical 256x256 BC7-sRGB payload in all five packets; its
SHA-256 is
`d25b9741808a5d8cbd9264d899091ac6af623a3f30d98bf2522a304130a8045f`.
PS t1 is the live full-resolution scene-color input: it is bound consistently
but is an unsupported dynamic format with no retained static payload, and
replay must supply the current Unity scene snapshot. The native replay now
creates PS t0 directly from the captured BC7 blocks instead of sampling
AnimeStudio's mismatched `T_fx_mask_01_M` extraction; the four reference packet
geometries/constants and dynamic t1 remain unchanged. Its runtime admission no
longer depends on that superseded AnimeStudio material or texture being spawned;
the optional ordinary source renderer is disabled when present, while the
native API accepts only the live scene-color resource. The strict verifier
requires VS t0 and PS t0 payload closure plus a bound dynamic PS t1 and accepts
both particle-count realizations by their descending horizontal-quad shape.
The old bounded rectangle compatibility pass remains the fail-closed fallback.
Do not reinterpret this owner as a fullscreen post effect or recapture shader
bytes.

EndfieldCapture now detects either exact M20 shader pair inside the indexed-draw
callback and, when the ordinary three-slot producer gate would skip it, arms a
fourth bounded deferred package before recording that same draw. Status and
summary expose `graphicsSequencePriorityM20DrawArms` and
`deferredPriorityM20DrawArms`. The session now also archives every immutable
D3D11 shader program under `graphics/shaders/`, deduplicated by SHA-256, so a
newly observed material owner can be decompiled without another capture.
Session `20260828T212621Z` proved a startup race: all expected M20 bytecode
identities were absent from its otherwise complete 413-file archive, so their
objects were created before the asynchronous proxy bootstrap published capture
state and the exact detector could never arm. The proxy device exports now join
that bootstrap before forwarding device creation, then install device/context
hooks before returning the game device. A real proxy regression creates a
shader immediately before the ready handshake and requires its exact bytecode
in the final archive. All 16 native tests pass in the launcher's `build-local`
tree. Sessions `20260828T224210Z` and `20260828T224407Z` close the real-game
gate with 72/72 automatic packages and no drops; `224210Z` is the cleaner
authority. The live owner is the third VFXBaseV2 pair
`62a5ce6c09171de9`/`5558deddb1ee6188`, admitted only with the measured 36-index
packet shape because the programs are shared by unrelated effects. Frame 1748
draw 77 closes exact IA, five VS and four PS constant buffers, the 4 MiB VS t0
ByteAddressBuffer, scene-depth PS t0, and the runtime 256x128 BC7-sRGB PS t1
atlas. The exact Unity transport submits and validates this packet once at
4.433333 seconds; its native shader/layout validator and six-export ABI
validator pass. No further M20 capture is required.

The first complete M20-integrated review has 770/770 1920x1080 frames, report
status `ok`, and one requested/active/submitted/validated M20 frame with zero
failures. Dense comparison against the clean reference selects source offset
-1, within the recorded plus-or-minus-one-frame anchor uncertainty. The burst
window remains the largest measured error: at 4.433333 seconds actor ROI MAE is
55.37 and effect ROI MAE is 53.15. Retail has broad overexposed radial/temporal
smear across the actor while Unity remains sharp and darker around a localized
burst. Treat the next crystal-peak work as Uber/temporal/bloom composition and
remaining owner-order recovery, not another standalone M20 texture substitute.

The M13, M14, M20, and M21 native BaseV2 transports previously replayed captured
3840x2160 `_ScreenSize`/viewport vectors at the 1920x1080 review target. Their
reflected VS b2 and PS b1 rows c0/c1/c5 are now patched fail-closed to the live
target, with explicit viewport/scissor ownership and restoration. Native builds
and focused callback validation pass. Earlier M13/M20 visual scores were invalid:
the clean August 26 MKV begins with another character, so treating video frame
zero as Endminf phase zero compared the packets against the wrong frames. Peak
pose/effect cross-correlation selects local offset +86. At that alignment M13
packets 1/2 improve the effect ROI by 0.50/0.36 dB at 4.5000/4.5333 seconds;
packet 0 regresses its pre-peak checkpoint and is rejected by maintained replay.
M14 remains neutral/slightly worse, and M20's isolated gain is only about 0.01 dB,
so both remain diagnostic-only. Corrected M21 remains admitted at its one
certified stone-shell tick.

A six-frame clean-reference A/B across 4.406667-4.516667 seconds keeps accepted
M13/M31 constant and toggles M18/M20/M21/M28 together. The exact group produces
a small net gain at the best bounded source offset: mean actor/effect ROI MAE
changes from 28.6668/36.3826 to 28.5186/36.1777. Almost all improvement is at
the first M20-onset sample, whose actor/effect ROI MAE improves by 0.7457/1.1033;
the 4.5000-second sample slightly regresses by 0.1008/0.1509 and the final sample
is pixel-identical. Keep the group available for the next complete review, but
do not describe this narrow gain as closure of the visibly missing soft bloom,
gas, and temporal smear.

The resulting `endminf_full_clean_presentation_v4_20260829` checkpoint completes
770/770 1920x1080 frames with report status `ok`. It observes the authored
start-to-loop transition, settled loop, entrance VFX cleanup, and animator/root
motion contracts; foreground UI remains absent. M18, M20, M21, and M28 each
activate, submit, and validate at their one certified tick with no native
failure. A 12.833-second H.264 review render and eight-frame contact sheet live
beside the generated report in scratch. This supersedes v3 for visual review,
but not the fail-closed evidence limitations above.

Full clean-reference comparison over 555 shared frames selects the allowed
source offset -1 and measures mean actor/effect ROI MAE 21.5466/22.3183 with
temporal-delta MAE 12.1147. The largest residual is opening motion from about
0.50-1.23 seconds (body yaw, arms, cape, and hair); the second is the
4.25-4.73-second peak, where retail has broad soft bloom/radial temporal smear
and Unity retains a harder ring/streak; the settled 7.50-9.22-second loop has
low temporal error but persistent scale, placement, secondary-settle, and grey
composition differences. This localizes the remaining work without treating a
whole-window average as evidence for any one renderer owner.

The exact Uber transport now embeds the ordinary retail pixel shader as well
as the peak-only radial variant. Thirty-five
complete ordinary packets in session `20260829T024828Z` are bit-stable in every
shader-read lane and match the corresponding lanes of the retained peak
template, so ordinary frames safely reuse the larger captured constant buffers
while preserving live source/bloom/LUT textures. Native selection uses the
ordinary shader throughout the sequence and the peak shader only in the
already certified 4.3500-second window; it also patches live screen size,
exposure, and the previously omitted `b0.c27.z` aspect ratio. Both shaders
execute to distinct pinned pixels on a deterministic WARP fixture using the
exact captured CharInfo LUT, and a
64-packet alternating-variant ring passes transport validation. This is
source-sparse transport, not a new parity claim: that session failed cadence
and predates complete t1 and latest VS-b0 retention, so a hardened recapture
and Unity image comparison remain required.

The retained peak t0 can nevertheless execute offline through the exact retail
Uber shader with its frame-local PS ranges and exact CharInfo LUT. This confirms
that Uber writes a vertically inverted intermediate which the immediately
following fullscreen copy resolves into the upright swap-chain image. A
fail-closed diagnostic replay requires matching external b0/b1 and labels the
missing R11 t1 as zero; it localizes the remaining bloom and downstream-UI
residual without promoting the incomplete session to sequence evidence.

A seven-frame frame-local replay spanning ordinary/peak/ordinary packets keeps
the central actor/effect crop closely aligned with the corresponding retail
backbuffers even while t1 remains zero. The peak residual rises only modestly
relative to its ordinary neighbors, so missing Uber bloom is a bounded parity
gap rather than an explanation for the broad Unity peak mismatch. Keep exact
t1 as a required final-evidence input, but prioritize differences already
present in Unity's pre-Uber temporal scene color, actor/VFX composition, and
equal-queue owner ordering.

Dense-window comparison schema v3 now derives retail frames from each report
row's measured `activeBodyClipTime` and the reference's nonzero
`bodyClipPhaseSeconds`, rather than treating requested/post time as animation
phase. Target 4.3500 therefore maps to source frame 351 instead of the former
heuristic frame 352. Do not compare v2 and v3 offset labels directly: v2 baked
in a one-frame shift. With M13/M18/M20/M21/M28/M31 held constant, the corrected
three-frame exact-Uber A/B selects residual offset -1 within the reference's
recorded anchor uncertainty and changes mean actor/effect ROI MAE from
24.5409/30.1609 to 24.3816/29.5874. Temporal-delta MAE changes from 28.2466 to
28.9995 because the exact packet is one measured tick, not a recovered
neighboring-frame temporal sequence. The two separately launched runs also
differ on adjacent rows where exact Uber reports no submission, so the
three-frame mean is not a clean causal A/B. At the source-registered offset-0
tick against retail frame 351, the submitted exact packet changes actor/effect
ROI MAE from 25.1415/31.4593 to 24.7693/30.5054, gains of 0.3722/0.9538; use
that bounded tick rather than the neighboring-frame mean when attributing the
exact draw. The resulting
`endminf_full_clean_presentation_v5_20260829` render completes 770/770 frames
with report status `ok`, observes start-to-loop, settled-loop, and VFX-cleanup
contracts, and submits the peak exact Uber once with no failure.

The superseding `endminf_full_clean_presentation_v7_20260829` checkpoint renders
the ordinary exact Uber on every non-peak frame and the peak variant on its one
certified tick. Its schema-v13 report is `ok`; every exact-Uber submission and
the active split M31 schedule validate without a frame failure. A same-schema
full-reference comparison shows v7 slightly worse than v4, but a controlled
current-code 13-sample Uber on/off probe slightly improves actor and temporal
MAE while changing effect MAE by less than one tenth. Therefore the exact
ordinary shader is not the cause of the remaining full-sequence gap and stays
enabled. The durable residual is upstream: retail temporal/ghost composition,
pre-Uber scene color, and equal-queue owner ordering. Exact changing metrics
and artifact paths live in
`reports/assets/character_recovery/endminf_full_clean_presentation_latest.json`.

The full deferred/SphereOutside diagnostic path is not presentation-ready. Its
explicitly content-invalid screen-shadow R attachment produces the reported
vertically inverted body mask over the background portrait. Disabling that one
attachment restores the correctly oriented portrait and improves the aligned
4.5000-second full actor/effect crop from 12.69 to 15.75 dB, while making the
incomplete exact deferred chain fail closed. The maintained launcher and video
profile therefore omit that diagnostic chain rather than publishing a green
readiness state with corrupted pixels. Across five aligned 4.3833-4.5833 peak
checkpoints, the cleaned M13/M21 presentation averages 16.99 dB versus 13.08 dB
for the former diagnostic-heavy profile.

The exact-owner policy deliberately retains one compute exception: the unique
8,413,184-byte slot-0 skin-palette UAV required to reconstruct body, hair, and
all four cloth palettes. A WARP byte test binds that palette beside an
unrelated UAV, proves the palette's complete first/last bytes, and proves the
unrelated buffer is excluded. Exact M13 now also retains IA, while the known
M18 diffusion-shell and M28 refractive-sphere pairs retain IA, constants, and
PS t0-t5. All 15 native tests pass after these owner-closure corrections.

The reported vertically inverted light appearance does not authorize another
texture flip. All 70 source `ParticleSystemRenderer.m_Flip` vectors are zero,
the recovered material Y scales are positive, exact post-VS packets preserve
their captured UV lanes, and AnimeStudio already performs the required
vertical row normalization. Peak trails travel toward the same upper-right
quadrant in matched retail and Unity frames. The apparent orientation gap is
instead missing/undersized M20 gas, glow, particles, and additive energy; a
Unity-side `1-y` or negative Y scale would double-flip source assets.

The body-shaped portrait contamination is a color-post mismatch, not an open
depth-owner choice. Native `UberPass` data flow copies
`HGRenderPathScene.sceneDepth` into `UberPostPassData.sceneDepthBuffer`; its
registered callback draws fullscreen Uber, binds that preserved primary depth
as `_SceneDepth`, then draws standard/ECS/HGUI world UI. The exact
`CLIP_SCENEDEPTH + HG_WORLD_UI` fragment therefore intentionally clips the
post-Uber portrait against unwarped primary depth containing CharacterPrePass.
Compatibility Uber/temporal color currently shifts the visible actor more than
retail, exposing that undistorted silhouette. Do not remove the clip or replace
its source-backed owner. A default-off
`ENDFIELD_DIAGNOSTIC_SYNC_POST_UBER_PORTRAIT_DEPTH=1` probe now warps primary
depth over the exact compatibility-Uber color-sampling footprint and retains
the nearest contributor only while radial/chromatic Uber is active. Controlled
4.35-second runs with temporal resolve and exact Uber disabled reject that
policy: clean-reference full-frame PSNR changes `18.5790 -> 18.5784 dB` and
the portrait ROI changes `18.8917 -> 18.8844 dB`; the settled no-warp path
continues to bind primary depth directly. Keep the probe diagnostic-only. Fix
the radial/chromatic color transport and temporal input instead of blindly
warping every contributing depth.

The opening hair/cape defect includes an application-space error, but the
current evidence also has a hard opening-coverage gap. The old runtime wrote
captured actor-root-space matrices after an
independently evaluated Unity body pose and interpolated them across 0.12-0.23
second package gaps. The v7 oracle now stores each hair pose relative to the
same captured Head and each cape pose relative to the same captured Spine2;
runtime publication applies those residuals to Unity's current Head/Spine2
after Animator evaluation, parent-first. Only measured previous/current 60-Hz
pairs interpolate; longer unobserved intervals select the nearest retained
endpoint. A five-checkpoint D3D11 capture validates the 144-sample/80-bone
binding and keeps the opening hair attached to the head. Its first retained
palette aligns to clean-reference source frame 115, while the entrance becomes
visible around source frame 90; frames 90-114 therefore remain uncaptured and
Unity necessarily holds a later pose at the start. Sparse cadence still limits
unsampled extrema, so this is not exact dynamics recovery. EndfieldCapture now
uses 36 palette-focused consecutive opening packages (the unique 8,413,184-byte
skin-palette UAV every Present and a 4K visual checkpoint every sixth package),
followed by 36 bounded full-owner packages at eight-Present spacing through the
peak/loop. Both `build-final` and
the launcher-owned `build-local` pass all 16 tests. One new unattended Full
capture is required before further opening-hair tuning. Session
`20260829T024828Z` did publish all 72 unattended packages with zero dropped
graphics events and preserves individually complete opening, peak, Uber, and
settled-loop frames. It does not close the sequence: cadence validation failed
with 36 unexpected Present gaps, including a 347.262-ms opening gap and a
2.006-second opening-to-peak gap, so the exact start-to-loop transition remains
bounded only after retained dispersal frame 2142 and by loop-like frame 2164.
That session also began before the compute-boundary-enabled observer DLLs were
rebuilt and therefore contains no `dispatchRecords` or per-frame
compute-completeness gate. Recapture rather than interpreting its sparse
extrema or transition timing. At 4.35 seconds the replay selects capture frame
1977 directly with effectively zero
interpolation, so that phase separates sparse-motion error from renderer
plumbing. The retained-skinning probe at exactly 4.35 seconds closes all six
deforming renderer rows and directly compares frame 1977's retail palette with
Unity's CPU-side renderer-local palette. The source mesh proves that cloth_02
uses 2,286 indices and 29 bindposes; the nearby 16,524-index retail draw is the
body and must not be used as a cape contract. With that mapping corrected,
mean root rotation error is 6.78 degrees for cloth_02, 6.77 for hair, 12.09 for
cloth_01, and 17.70 for cloth_04; mean root translation error is respectively
0.0152, 0.0149, 0.0442, and 0.0911 model units. This rules out a wholesale
cloth_02 bone-order or import failure and keeps sparse secondary-motion cadence
as the primary motion gap. The capture omitted the older duplicate source-SRV
alias row, so this comparison proves the complete source palette and exact draw
b2 binding separately and reports that limitation; it is not a GPU-submitted
Unity palette or baked-vertex equality proof.

Sessions `20260829T020746Z` and `20260829T024828Z` are diagnostic-only and do
not close that gap. The former published 72 packages without drops but retained
only five exact palettes around clean source frames 113-117. The latter retains
all six meshes and 74 owner bones in every dense package 1823-1858, with its
first visual checkpoint aligned around clean source frame 94 plus or minus one,
but a 347 ms QPC gap between packages 1834 and 1835 skips about 21 nominal 60-Hz
frames. Consecutive package IDs therefore do not prove continuous frames 94-129.
The capture path accepts the exact palette from the Endminf body VS t0 binding,
permits asynchronous dense draining, rejects incomplete dense palettes, and
derives failure flags from finalized readbacks. It now also arms on the unique
16,524-index Endminf body draw before Uber and stages 4K backbuffers only at the
first and final dense packages so intermediate readback cannot accumulate the
observed stall. The observer's exact fullscreen state record now closes every
bound RTV descriptor, DSV view dimension/flags, sampler border colors,
alpha-to-coverage and all per-target blend descriptors, full stencil faces,
and depth-bias/forced-sample raster state. A real WARP integration test binds
two distinct RTVs, a read-only depth/stencil DSV, three samplers, independent
blend targets, asymmetric stencil faces, and nondefault raster bias, then
asserts the production collector returns each descriptor. The observer now
adds an automatic-Full-only M31 chronology sidecar. The exact first
`DrawIndexedInstanced(6,1,4542,1082,0)` signature arms one bounded candidate
and must continue as base vertices `443` then `32` in the same Present. It
retains a 64-call draw/dispatch census with the bound VS/PS/CS identities,
stable RTV0/RTV1/DSV identities and descriptors,
and six immediate pre/post RTV0 copies. Readback is deferred with
`DO_NOT_WAIT`, shares the existing 1-GiB aggregate ceiling, and publishes only
after metadata plus all six blobs reach disk; wrong order, target drift,
capacity, budget, copy/map, device, or publication failures keep the dedicated
sidecar incomplete. The current Release observer passes all 19 native tests.
Its census retains bound VS/PS/CS identities so
each intervening call can be mapped to a retail owner instead of inferred from
arguments alone. The earlier final rebuild fixes
the live route to the retail `DrawIndexedInstanced` signature; the prior build
matched the non-instanced API and cannot produce this evidence. The next
capture must use
this build and pass cadence, resource, base completeness, and M31 chronology
gates before its palettes, fixed state, or three-draw boundary evidence enter
replay.
`verify_endminf_draw_contract_capture.py` schema v2 now enforces those session
gates before draw inspection, requires the complete eight-slot RTV/blend and
DSV/sampler/stencil/raster descriptors, and checks the already proven M31
4K target/depth, sampler, blend, depth/stencil, viewport/scissor, and raster
values. It rejects `20260829T024828Z` deterministically at the false graphics
`complete` gate instead of publishing partial fixed-state evidence.
The captured M31 c1/c4 fingerprint resolves directly to serialized material
`M_fx_endminm_gfx_31` (PathID `602883BD6BB1831B`), not the unrelated mission
alias returned by a bare source-graph query for `M31`. Its `_StencilComp=8`,
`_StencilOp=0`, and 255 read/write masks map to D3D11 Always/Keep on both faces,
matching the retained runtime stencil-enabled/reference-zero state. Verifier v2
now rejects any different face operation/function or mask rather than waiting
for those values to be guessed in the Unity callback.
Targeted extraction of the exact `HGRP/Effect/VFXBaseV2` Shader object closes
the serialized half of the remaining fixed-state gap. Its `ForwardOnly` pass
sets separate MRT blending and alpha-to-coverage off. Substitution of M31's
saved properties gives RTV0 ONE/INV_SRC_ALPHA for color and alpha, while RTV1
uses SRC_COLOR/INV_SRC_COLOR for color and ONE/ONE for alpha; both use Add and
write mask 15. The same pass fixes zero depth bias and no conservative raster,
and the retained runtime record closes scissor, reversed-Z GREATER_EQUAL,
point-clamp s0, linear-wrap s1, RTV0, and the depth formats. Verifier v2 now
rejects incompatible RTV1 dimensions/view type/sample count, a writable or
malformed DSV, drift in either active blend target or disabled targets 2-7,
independent blend, alpha-to-coverage, bias, and forced-sample state. RTV1's
live resource/view formats and whether retail marks stencil read-only remain
explicit recapture fields rather than guessed constants. The exact native M31
callback no longer borrows M14's
wrap/linear samplers, disabled depth, or duplicated MRT blend: it owns the M31
descriptors, binds the D32/S8 resource through a read-only depth/stencil view
while sampling its depth plane, and restores the captured shader, resource,
output, and fixed-function bindings. It queries the live context after every
void D3D11 setter and suppresses the draw with `E_FAIL` unless both RTVs, the
DSV/SRV pair, samplers, state objects, blend factor/mask, and stencil reference
all remain bound exactly. A dedicated WARP validator now binds two distinct
RTVs with the read-only DSV/depth SRV and query-checks the production
combination (`independent=1`, RTV1 `3/4`, depth func `7`, stencil on, DSV flags
`3`). The hardened retail recapture must still confirm its live DSV flags and
RTV1 formats before this is treated as final runtime parity.

The retained frame-1977 owner order now has an explicit fail-closed schedule
contract. M31 draws at ordinals 66, 74, and 89; ordinal 88 is the exact M18
`DrawIndexedInstanced(900,1,3642,1615,0)` owner, so the third M31 event belongs
immediately after M18 and before Unity's queue-3001 continuation. Generated
M31 data distinguishes the proven two-event queue-3000 schedule, the observed
three-event queue-3000-plus-post-M18 schedule, and unsupported packets. A
separate per-packet chronology-validation gate remains false for the
three-event packet, so both managed and native selectors reject it and retain
the ordinary renderer until a corrected observer capture proves the three
SceneColor boundaries. The managed state machine and native callback support
up to three ordered events, complete validation only after the selected event
count, and abort partial schedules. The native tool-only build, WARP shader
validation, M31 fixed-state validator, and direct selector probe pass; the
selector accepts the seven proven two-event packets and rejects the pending
three-event and unsupported packets. The chronology verifier additionally
requires nonempty monotonic owner intervals and the exact M18 call as the final
census entry before draw 3; well-shaped but owner-ambiguous census data no
longer passes.

Unity sequence report schema v13 now makes the split M31 transport observable
per frame instead of treating an enabled environment flag as proof. Every
captured row records whether its body-clock phase lies in the recovered M31
envelope, whether the runtime admitted and submitted every scheduled event, the
selected packet/source frame, and whether the synchronized native draw-count
gate validated. A requested targeted capture fails closed when any expected
M31 row lacks active, submitted, and validated evidence. The focused contract
suite and the complete v7 Unity sequence pass. Retail chronology evidence still
requires the next hardened D3D11 game capture; Unity submission validates the
replay transport, not the missing live SceneColor boundaries.

The complete v8 Unity sequence supersedes v7 for user review. It preserves the
validated exact Uber/M13/M21 presentation but removes M31 from maintained
defaults: a formal ten-sample toggle holds the animation clocks byte-for-byte
equal while M31-on worsens actor, effect, and temporal comparison metrics. M31
transport remains available and validates as a diagnostic, but is not visual
admission evidence until the live SceneColor chronology is closed. v8 improves
slightly over v7, while the older v4 remains visually better overall; treat v8
as the evidence-correct current build, not a parity claim.

The subsequent schema-v17 v9 diagnostic corrects the compatibility opening
strip's consumer order: it now composites into packed SceneColor before the
temporal/DLSS boundary, while the separately gated exact retained packet remains
authoritative. A complete 770-frame run observes this compatibility submission
on ten opening frames and passes transition, cleanup, exact Uber, and output
format gates. Against the same chronological -1-frame alignment, v9 scores
23.9181 actor, 25.7429 effect, and 15.5716 temporal MAE versus v8's
23.8874/25.7000/15.5958. Keep the evidence-backed ordering correction, but do
not promote v9 over v8 for review: its small temporal gain accompanies small
actor/effect regressions. A paired 4.4833/4.5000-second audit also rejects
removing exact M13: enabled improves actor/effect/temporal MAE from
31.3171/37.3131/28.6593 to 29.9246/36.2230/27.1432. M13 therefore remains
canonical; M21 remains the compact palm-centered ten-stone owner and must not be
resized or retimed to compensate for the broad shell.

The retail opening owner also writes SceneMV Target1 independently: its
`(0,0,1,0)` source with SrcColor/InvSrcColor RGB and One/One alpha preserves
motion XY/A while setting the B validity marker. Capture schema v18 exposes a
compatibility implementation of that publication. A controlled 17-frame
on/off/repeated-off audit cannot distinguish it from startup temporal-history
variance: the enabled result scores 25.2271/14.2720/7.7644 actor/effect/temporal
MAE, while two disabled runs span 25.1132-25.2664, 14.2448-14.2758, and
7.5946-7.8058; frames 4-16 are byte-identical. Keep the compatibility Target1
publication explicit diagnostic-only. The exact retained packet transport does
use the recovered independent Target1 blend state, which corrects its previous
RT0-state reuse without promoting the compatibility approximation.

A fresh complete schema-v18 checkpoint under
`scratch/character_recovery/endminf_full_clean_presentation_v10_20260829`
passes all canonical D3D11, animation, cleanup, and exact-Uber gates across 770
frames. At the established chronological -1-frame alignment its actor, effect,
and temporal means are 23.8688/25.6961/15.5843, only
0.0186/0.0039/0.0116 below v8 and inside the larger startup-history variance
measured by the controlled SceneMV repeats. Retain v8 as the review baseline;
v10 is a schema-v18 checkpoint, not evidence for a beauty-default change. Its
sheet still localizes the dominant residual to the missing broad retail
opening multi-exposure strips.

The exact four-packet `CharEffect/trail` path is now canonical only at its
captured phases. A full v11 probe exposed two fail-open integration defects:
packet activation disabled the compatibility owner without forcing the SceneMV
transport, and actor replacement left a destroyed optional source-renderer
reference. The capture report also accepted active packets with zero submitted
or validated draws. The repaired path forces SceneMV, refreshes and guards the
optional renderer, and requires every active packet to submit and validate.
The targeted 0.1500/0.1833/0.2167/0.2500-second probe closes packets 0-3 and
source frames 1034-1037 with `S_OK`; the 770-frame v12 checkpoint under
`scratch/character_recovery/endminf_full_clean_presentation_v12_exact_strip_fixed_20260829`
passes the same gate. At offset -1 its actor/effect/temporal means are
23.5678/25.7378/15.6023: actor ROI improves 0.3010 versus v10, while effect and
temporal means regress 0.0417/0.0181. The exact geometry now restores the broad
strip population but remains too dark without retail temporal accumulation.
Keep v8 as the beauty baseline; retain the exact bounded owner as canonical
source fidelity and close its downstream temporal history separately.

Sparse secondary-motion samples do not justify endpoint snapping in the
presentation path. That experiment introduced visible hair and cloth steps at
every retained-sample boundary and is rejected. Until a dense same-session
runtime trajectory is captured, compatibility replay interpolates positions
and rotations continuously across sparse intervals; the remaining uncertainty
is an evidence gap, not permission to add discontinuities.

The native cross-frame callback order is now closed through publication: finish
the retained previous master, read current transforms, publish the distinct
`last` arrays through `WriteDoubleBufferTransform`, schedule current simulation
through display/PostProxy, and retain its master for the next callback. The
exact positive-scale Endminf `CalcDisplayPosition` stage is also implemented:
after final Simulation End it extrapolates `oldPos` by binary32 velocity and
timestep, lerps persistent display state with the retained team clock, applies
the source 1.3x root-distance clamp, stores display state, applies independent
`blendWeight`, and captures running history before PostProxy/writeback. Exact
golden vectors and integrated owner/coordinator order pass. The transform-read
and duplicate-write dependency chain now follows the source-backed componentwise
quaternion-value publication fix; maintained generation refreshes the Unity
binding identities while leaving solver and replay defaults off. A current v18
diagnostic compares all 74 rendered owner bones at the accepted 40 checkpoints.
The first proven divergence is already post-publication at requested 0.05 s:
36.45 mm/6.82 degrees mean and 78.00 mm/24.51 degrees maximum. At 0.35 s the
mean reaches 141.64 mm/14.38 degrees. Overall the solver averages
104.20 mm/10.89 degrees, versus 20.24 mm/7.19 degrees with the solver disabled.
This capture does not retain internal stage snapshots, so it cannot attribute
the first error to Start, Tether, Angle, CalcDisplayPosition, or another kernel.
Keep the solver diagnostic-only and recover that internal stage boundary; do
not publish scratch state or invent smoothing curves.

The optional compatibility replay clock itself is continuous: all 770
presentation frames advance without repeated requested times. Its visible jerk
is caused by a sparse 144-pose oracle (72 adjacent previous/current pairs, with
many multi-frame gaps) joined by piecewise interpolation, which is only C0 at
sample boundaries and suppresses extrema. Canonical rendering keeps that replay
disabled. Do not replace its limitation with authored per-bone positions or
smoothing curves. The recovery target is the already identified BeyondBoneCloth
solver and publication path; captured pose replay remains a diagnostic bridge.

The original `ui_overview_start` and `ui_overview_loop` sources contain no
ordinary Unity transform or float curves. Their poses are stored in ACL 2.1
transform buffers and the pinned UnityPlayer samples those buffers directly.
Fractional samples use non-negative floor, adjacent sample selection, float32
stable endpoint vector interpolation, and shortest-hemisphere normalized
stable quaternion nlerp; controller time wrapping occurs before the ACL clamp
seek. Unity auto-tangent curves, Hermite interpolation, `Quaternion.Slerp`, and
generic `Quaternion.Lerp` are therefore not source-faithful replacements. The
lab imports decoded ACL sample contracts through source/payload hash gates and
publishes their recovered component masks through a character-neutral runtime
driver synchronized to the generated Animator controller. The canonical v25
capture verifies the driver against the directly evaluated Animator state on
all 770 frames and all 278 bound transforms. Endminf body timing and pose
publication are therefore closed for this two-clip scope; entrance secondary
dynamics remain separate and incomplete.

Directly transplanting the retail Streamline path into the Unity lab remains
fail-closed. Unity's D3D11 plugin interface exposes both the native device and
active swapchain, so the resource/evaluation lane is technically reachable,
but Unity retains and presents through its own native swapchain pointer. A
late native plugin cannot replace that pointer with Streamline's upgraded
proxy or prove the required once-per-Present `presentCommon()` lifecycle.
Calling only `slInit`, `slSetD3DDevice`, and `slEvaluateFeature` would therefore
be an invalid host. EndfieldCapture schema v4 now observes the original
prelaunch `slInit` call and requires one readable successful non-truncated DLSS
request, retaining its SDK version, flags, feature list, application/project
identity, engine/version, render API, and plugin paths. The next exact retail
capture must close that initialization record plus the consecutive Streamline
surface pair before any direct-host experiment is reconsidered. Retail NVIDIA
binaries remain local inputs and are not packaged by this repository.

Presented-frame registration does not authorize moving M13. Its recovered
shell fits `(1229.5,427.5)`, radius 251.2 px, while adjacent retail frames fit
`(1205.5,443.5)`, radius 253.4 px and `(1208.5,441.5)`, radius 272.1 px.
Palm/cuff proxies yield inconsistent candidate translations `(-23,+32)` and
`(-32,+14)` pixels, and both Unity samples reuse one packet while retail is a
changing temporal composite. Current-body features are already within roughly
five pixels. Require same-session pre-temporal packet and current-palm evidence
before any M13 translation, scaling, or retiming.

The retained exact Uber resource also exposed a native-resolution bloom-layout
bug in the reproduction. The old builder capped a 3840x2160 source to
1920x1080 and then halved it again, yielding an invalid 960x540 first mip. The
working scale is now `min(0.5, 1080/sourceHeight)`, capture schema v14 publishes
the live first-mip dimensions, and a focused 3840x2160 probe observes the exact
1920x1080 packed bloom texture with the peak Uber submitted and validated. At
the maintained 1920x1080 review resolution this preserves the existing
960x540 first mip; it corrects native-resolution evidence rather than claiming
a new visual improvement.

The same v7 audit narrows two unresolved presentation boundaries. M31 packets
submit and validate across their certified window, but packets 2-6 mildly
worsen the aligned actor/effect comparison; transport execution does not prove
that the replay sees the correct live SceneColor chronology. The current
public Unity NGX proxy is likewise rejected as a presentation path: it
validates technically but produces a severely dark result. Capture
`20260829T115328Z` instead proves the retail Streamline lane uses a nonzero
repeating eight-sample pixel-jitter cycle and indicator inversion X/Y `0/1`,
while v7 still uses the zero-jitter compatibility temporal resolve. Preserve
those distinctions and do not retune the body animation to compensate.

The full-sequence comparator now uses elapsed sequence time from the established
start anchor rather than reusing wrapped clip-local time after the dominant
clip changes to `overview_loop`. It supports a separate paired loop anchor when
one is independently recovered and fails closed on incomplete or backwards
mappings. The corrected chronological pairing disproves the apparent settled
camera/framing gap: actor and portrait scale are within a few tenths of one
percent and displacement is sub-pixel before the late cursor move. Do not
change FOV, actor root scale, static camera position, portrait placement, or
GridFar to fit the old clip-wrapped comparison. The remaining late offset is an
input-provider state gap, not permission to replay clean-video cursor samples.
Those tracks and their offset sweep are removed from canonical capture.
Resolving the remaining few-pixel tail requires the retail Beyond input provider
or same-session runtime state used as validation evidence, not a global camera,
portrait, or screenshot-fit offset. Loop-only diagnostics can supply an explicit
paired sequence origin to the comparator; the tool rejects partial origins and
continues to require chronological output.

The background portrait inversion was a Unity mesh bug, not missing capture
evidence: both portrait builders vertically flipped UVs that TextureImporter
had already mapped from the display-upright PNG. Their tight-rectangle UVs now
use unflipped `vMin`/`vMax` order, a targeted 0.65/4.4333/6.65-second render
shows the silhouette upright, and all 31 playable profile meshes pass the
independent bottom=`vMin`/top=`vMax` verifier. The builder and verifier also
require `meshType=Tight`, `packingMode=Tight`, `packingRotation=None`, and
`packed=0` before using that unflipped UV path. Canonical capture and the
maintained launcher forcibly clear the content-invalid screen-shadow-R and
SphereOutside presentation selectors, so an inherited diagnostic environment
cannot reintroduce the upside-down body-shaped mask; no second portrait flip is
admitted. Endminf LitEffect compatibility
textures now also enforce source semantics on import: BaseColor and Parallax
are sRGB, while MRO and Normal are linear, with Normal imported as
`NormalMap`. This
corrects the stone normal sampling contract but does not claim retail lighting
parity. The compatibility LitEffect shader still contains an approximate
directional-light model, while exact deferred light, shadow, and HGBuffer frame
ownership remain incomplete. Do not tune that heuristic or move effects to fit
screenshots. The Overview VFX source-stage contract is now schema v2. It gates
the exact four root GameObject/Transform identities and node/particle counts,
carries exact hierarchy identities plus direct ParticleSystem,
ParticleSystemRenderer, resolved material/mesh, and shape-texture references
instead of positional list joins, and
validates the complete saved particle/renderer payload by source PathID after
effect-animation reconstruction. The current local generated Overview prefabs
are still schema v1 and therefore fail closed until a clean, coordinated Unity
rebuild regenerates and validates them; no current render is certified by the
v2 gate yet. The broader exact stage, generated prefabs, materials, and shader
sidecars remain intentionally local evidence inputs rather than tracked binary
blobs; the rebuildable v2 animation payload closes the new cached-clip
dependency but does not claim the whole visual lab is standalone.
The exact deferred subset no longer substitutes a 1x1 zero texture at t10:
`SetupMultiscatteringLut` is reproduced as a source-generated 32x32
`R16_UNorm` Bilinear/Clamp LUT with exact 2,048-byte SHA-256
`1a15afe25b25e7aa64dcf17d74f5375dd1b692b3805cd00aa4f531ad289f030e`.
Its b4 direct-light scalar is likewise source-derived as
`8.631674 / pi = 2.7475471`. Exact presentation remains default-off and now
requires a current asynchronous readback with nonzero RGB content; alpha-only
black output fails closed instead of replacing the ordinary source renderers.
The isolated Endminf deferred gate confirms the recovered 12-light operator
fixture, same-frame punctual ShadowData/atlas, HGBuffer frame, and exact
resolver consumer can all publish together. The full-LightData verifier also
GPU-compares all six published headers and twelve live-light records against
the source-derived packing contract instead of accepting a truncated subset.
Its M27 probe had separately requested the presentation consumer without
requesting the recovered M27 HGBuffer producer; the probe now connects both
selectors. The cached viewer rebuild now preserves the fingerprint-validated
playable prefabs instead of overwriting Endminf from the incomplete generated
manifest. A targeted exact capture fails closed unless the four Overview
effect roots, primary rock binding, LightData, ShadowData, pass-0 subset,
five-MRT GBuffer, and M27 HGBuffer are all observed. The repaired 4.60-second
D3D11 probe restores four roots and 68 admitted renderers, publishes every
deferred prerequisite, submits and reads back the native consumer, and exits
without a Unity crash.

The earlier combined diagnostic also enabled the generic SphereOutside
producer in the same depth/GBuffer set, then used shared depth as M27
ownership; that routed an inverted body-shaped resolve behind the upright
portrait. The Endminf exact-consumer probe now excludes SphereOutside and the
generic producer, and the identity-only A/B removes the contamination without
an image flip. Physical resource validity and presentation validity are kept
separate: the current full-resolution t11 attachment can be allocated and
bound while `t11ContentValid` and `screenContentValid` remain false. The exact
consumer may execute for transport validation, but M27 presentation stays
withheld until the retail producer content is certified. This does not yet
promote the chain to the maintained presentation. The retail attachment owner
is now recovered:
`ScreenSpaceShadowMaskPassConstructor` publishes a full-resolution bilinear,
clamped `R8G8_UNorm` target through two ordinary fullscreen `Draw(3,0)` calls.
The first writes scene-shadow R as
`1 + strength * (min(sceneShadow, 1) - 1)` and the second preserves that R
while adding character-shadow G; neutral R is 1. Capture `20260829T224523Z`
retains the deferred consumer but missed those ordinary-draw producer payloads.
The joined M27+Default lane retains distinct producer-1-after,
producer-2-after, and Default-consumer-before t11 snapshots for the same RG8
object. Its current static admission is exact rather than descriptor-only: it
requires the pinned fullscreen VS, scene-R PS, character-G PS, and Default Lit
PS in that order; the exact one-draw SphereOutside HGBuffer carrier must precede
both producers in the same Present epoch. The independent verifier repeats
those program, owner/occurrence, resolver-to-readback ordinal, Present-epoch,
Texture2D/no-mip/no-MSAA descriptor, and carrier gates using the serialized
capture rather than trusting the native boolean. It also authenticates the
collector inventory and pinned client build, requires scene-shadow R
preservation plus a changed/non-constant character-shadow G, and fails closed
with structured diagnostics. This closes a static false-admission boundary; it
does not close game-only ECS/grass/tree caster content or authorize the
persistent SphereOutside presentation without live same-frame bytes. Pass
`--artifact-dir <scratch>`
to emit lossless native-row-order PNGs for both R/G channels of P1, P2, the
consumer, and the producer deltas; these are comparison evidence, not runtime
textures. `Numpad 9` finalizes providers but does not run the collector. After
the capture host exits, run `EndfieldCapture.exe collect --session <id> --session-root <capture>`
and require validated collector JSON plus
`collected/inventory.json` before invoking the strict verifier. The rejected
`20260831T184411Z` session omitted this required collection step. After a
capture passes, run
`python tools/build_endminf_screen_shadow_capture_artifact.py <capture>
--output-dir <scratch-output>` from `unity_endfield_graph_shader_lab/` to emit
the inventory-authenticated raw P2 RG8 bytes plus a deterministic manifest.
The builder refuses output inside the authenticated capture and labels the
result `diagnosticReplayOnly`; it does not authorize presentation or certify
the procedural Unity producer. A fresh bounded Full graphics capture is still
required before the RG attachment can be admitted to presentation.
The maintained live path is now
`tools\EndfieldCapture\StartEndminfScreenShadowCapture.bat` with Endfield
closed. This explicit opt-in keeps generic `StartCapture.bat graphics full`
manual, but for the Endminf lane it waits for the exact published capture-host
PID/path, authenticates the same immutable session ID/root after host exit,
requires `collected/inventory.json`, and runs the strict screen-shadow verifier
automatically. This closes the collection handoff only; preflight or launcher
success is not t11 presentation evidence until the verifier admits exactly one
live packet.
The current source-background probe also closes the ordinary renderer order as
CharFloorEffect then GridFar, with SphereOutside isolated to the deferred
sidecar and wall/ShadowPlane disabled. Its v22 presented-pixel gate correctly
fails because no current capture certifies content-valid draw-local t11 data.
Historical SphereOutside probes predate that gate and are not presentation
authority; maintained playback therefore retains the neutral clear while this
exact producer-to-consumer handoff remains open.

The compatibility Quality-0 temporal resolve now follows the decoded source
bound in both shader branches: five-tap reconstructed history is clamped to
0.2x..1.8x the direct reprojected history sample, not to the current scene
sample. A continuous 770-frame D3D11 run passes all entrance, cleanup,
transition, and settled-loop gates. Against the same aligned clean retail
window, the correction has no material spatial effect and produces a small
temporal-delta improvement at every selected entrance and crystal-peak
checkpoint. Retain it as a literal pipeline correction; it does not authorize
crystal, stone, or animation retiming, and the larger temporal/Uber residual
remains open.

The captured Endminf CharInfo LUT is now the maintained compatibility and
exact-Uber resource only for the active source-recovered
`chr_0003_endminf` profile. Admission requires its pinned byte length/hash and
five CPU sentinels, then five texel-center samples through the actual
bilinear/clamp GPU sampler into a 5x1 RGBA16F target and byte-exact D3D11
readback. Capture schema v23 fails closed unless the profile, GPU result, hash,
and exact compatibility binding hold on every published frame. A continuous
770-frame run passes those gates plus the entrance, cleanup, transition, and
settled-loop lifecycle. Against the same 555-row clean retail window, replacing
the procedural LUT has only a negligible spatial regression and negligible
temporal improvement; retain the source-exact LUT, but treat the remaining
color/VFX mismatch as upstream scene-color, bloom/Uber chronology, or lighting
rather than compensating with a fitted grade.

The native Phase-2 command order is now reproduced as ColorGrading/LUT, Bloom,
AutoExposure, then Uber. The prior Unity command buffer recorded Bloom and the
optional histogram before LUT preparation. A complete 770-frame D3D11 capture
under `scratch/character_recovery/endminf_phase2_lut_order_full_770_20260901`
passes entrance, cleanup, transition, settled-loop, exact-LUT, post-source, and
bloom gates. Representative frames are byte-identical to the preceding exact-
LUT checkpoint and the 555-row comparison remains
33.3722/35.5934/15.4469 ROI/effect/temporal MAE, as expected for a static LUT;
retain the literal source chronology without claiming a fitted pixel gain.

The captured Endminf Uber packets remain diagnostic-only. Their native draws
and resources validate, but the retained evidence consists of one early and
one peak 60-Hz source-effect sample. The exact transport now submits only
inside those two authenticated half-frame windows and falls back to the
compatibility Uber elsewhere instead of reusing the peak payload as a
sequence-wide normal packet. The 770-row D3D11 diagnostic under
`scratch/character_recovery/endminf_uber_sparse_full_770_diagnostic_20260901`
passes the full animation/VFX lifecycle and exact-LUT gates, with exactly one
submitted/validated peak row and 769 cleanly withheld rows. The current exact-
packet input chronology still regresses the three aligned effect samples
against the otherwise identical
exact-off control (mean effect ROI MAE 36.2987 versus 35.0779). The maintained
launcher and canonical capture defaults therefore do not request it; recover
per-frame retail constants plus draw-local SceneColor/bloom/LUT producer and
consumer chronology before reconsidering presentation ownership.

The same dense comparison localizes the settled mismatch without authorizing
global tuning. Eroded actor interiors retain roughly 35.4-40.7 RGB MAE, almost
entirely in luminance, while a best global affine luma correction removes only
6.6-9.7 percent. The spatial residual is consistent with material/light
response or local post, and final PNGs cannot distinguish those without matched
retail pre-Uber SceneColor. The strongest literal visual gap remains the
crystal/stone LitEffect compatibility shader: it is approximate ForwardOnly
shading while the recovered five-MRT HGBuffer/Default-Lit path is still gated
on a same-frame, content-valid t11 screen-shadow producer-to-consumer capture.
Do not compensate with exposure, saturation, bloom, material multipliers,
stone scale, or animation timing.

The current clean-video bridge does not prove the complete 770-frame animation
schedule. Its source sidecar covers retail frames 88-645, anchors start-clip
phase 0.0509083 at source frame 91 with plus-or-minus-one-frame uncertainty,
and can therefore pair only Unity rows 0-554 by elapsed time. Transition entry,
loop dominance/completion, later loop wraps, and Unity rows 555-769 are
controller-timing extrapolations rather than observed retail animation state.
The exact-build observer now supplies that missing lane. In a Full general-
runtime capture it hooks only `CharUIModelMono.Tick`, filters copied runtime
owner identity to exact `chr_0003_endminf`, and reads current state,
transition-only next state, normalized/local timing, transition progress, Tick
delta, thread, and a seqlock-published prior Present ordinal/QPC pair through
Unity's explicit-out Animator query shims. Schema v3 also derives the next
Present pair observed by a later Tick while keeping Tick and Present as
different clocks. Both native inputs and all hooked/query entry bytes are
gated; ownership changes, any active owner-read or pre-Tick failure, reentrant
Tick, nonfinite payloads, missing/inconsistent Present association, clock
regression, overflow, or non-quiescent cleanup keep the artifact incomplete.
Duplicate or skipped prior-Present associations are accepted only when their
ordinal/QPC pair remains coherent and monotonic. Publication additionally
requires the exact source-controller full-path hashes
`Base Layer.Overview.FromOveview` (`0x5D0225EB`) and
`Base Layer.Overview.OverviewIdle` (`0xAFC694A7`), positive state lengths,
monotonic start/transition/loop clocks, three settled loop samples, and the
first adjacent unwrapped loop-cycle rise. The independent Python verifier
re-derives every boundary from raw samples and separates tick-quantized QPC
intervals from the Animator transition contract. Session `20260829T115328Z`
contains two sequential native owner/Animator identities; each independently
repeats the recovered 0.75 exit, 0.25 normalized non-fixed transition, zero
destination offset, start/loop lengths, and first settled wrap. This is strong
corroboration, but the session does not certify the lane: automatic graphics
capture armed during loading, cadence failed, and the second owner recreation
invalidated the old single-identity summary. More specifically, its graphics
trigger armed at Present 1305 while exact Endminf `overview_start` begins near
Present 1694, roughly 389 Presents later. The observer now segments sequential
identities, requires the same-Present body candidate and exact Endminf Uber one
or two Presents after an exact early non-looping `overview_start` Animator
sample before automatic arming, excludes unscheduled priority M20
packages from scheduled cadence, and admits priority M20 only for an exact
matched shader route with `DrawIndexedInstanced(36,1,...)`. Do not use the
wall-clock extrapolation to claim exact loop-phase visual equality; replace it
only after the next complete observer run passes this corrected contract.
The same failed session exposed two collection gaps rather than retail-render
conclusions: a cached viewport-3 `slDLSSSetOptions` caller bypassed the
returned-pointer detour, and no actual 1x1 exposure texel or pre/post DLSS
surfaces were retained. EndfieldCapture commits `325b632`, `b1e5e2f`,
`7656c5e`, and `4139de0` close those observer gaps. Full capture now directly
hooks the validated options target, joins options/token/constants/tags/evaluate
to one prior and immediate-next Present, asynchronously records the viewport-3
type-13 descriptor and payload, and retains two consecutive exact DLSS packets
around the original evaluation. Each packet contains input color format 26
(33,177,600 bytes), output color format 10 (66,355,200), depth format 19
(66,355,200), and motion format 34 (33,177,600); the pair is 398,131,200 bytes
and exactly eight `CopyResource` calls. Readback is `DO_NOT_WAIT`, packet files
are size/hash gated, and deferred, M31, and Streamline allocations share the
authoritative 1-GiB staging ceiling. Failed session `20260829T115328Z` reached
654,590,032 bytes of deferred staging before the surface-pair observer existed;
it completed collection cleanly but supplied no crash artifact, so that memory
pressure is a risk signal rather than a proven crash cause. EndfieldCapture
commit `db2b915` now serializes the two workloads in both the general runtime
and graphics-only proxy: the complete 398,131,200-byte pair must be published
and its staging released before the independent 72-frame/M31 sequence can arm.
The summary and collector require
`streamlineSurfacesPublishedBeforeDeferredSequence:true`, and surface failure
stops before the heavyweight sequence. These are capture-readiness facts, not
evidence that the missing retail temporal boundary is closed; that still
requires a newly collected complete session.
The same session's secondary-dynamics v1 summary was also falsely optimistic:
it reported complete despite zero Transform write calls/samples and 60,704
relative-slot overflows. EndfieldCapture commit `7a09410` replaces that lane.
The exact early Animator sample now arms the dynamics window synchronously;
stable TeamData indices are retained through serialized, epoch-bound whole-
array scans; and the exact `ClothUpdate` `WriteTransform` schedule is sampled
only after its later `CompleteMasterJob` returns. Scheduled, completed, and
recorded writebacks must match; empty writes, unequal arrays, cache contention,
overflow, unreadable data, trigger drift, failed finalization, and cleanup
failure all keep summary v2 incomplete. The independent trajectory verifier
requires one exact Animator/graphics-joined complete window and unique complete
6/30/20/70-transform candidates before publishing evidence. These fixes make
the next capture diagnostic-ready; they do not retrofit trajectory evidence
into `20260829T115328Z`, whose v1 summary is rejected. EndfieldCapture commit
`6eb9788` closes the remaining duration/clock contract: the automatic
secondary-dynamics window now stays active after the shorter graphics sequence
and closes only on clean session stop, while trajectory timestamps use the
same QPC epoch as the Animator timeline. The verifier now requires the last
writeback to reach the timeline's first settled loop wrap. The canonical
all-character Unity build also runs the generated Endminf binding verifier
before it reports success, so missing or hash-stale replay data can no longer
pass through the ordinary rebuild path as a log-only warning.
EndfieldCapture commit `484aa62` closes the registration, effective-pose, and
owner-identity instrumentation boundary for the next run. Exact-build
`AddCloth`/`RemoveCloth` and `AddTransform`/`RemoveTransform` hooks retain
generation-bound cloth and one-row Transform registrations, with invalidation
bracketing each removal. After the exact `CompleteMasterJob` return, the
observer uses the pinned `ExTransformAccessArray.get_Item` wrapper and
read-only Transform getters to retain the live effective world/local pose.
Registration callbacks call the additional pinned name/parent getters only on
the uniquely resolved main-window thread, strictly decode bounded UTF-16, and
copy full `Root/...` paths plus `MC_*` cloth names into immutable native
records. The cloth objects and skeleton `Root` are siblings, so the join uses
their common actor-parent instance ID rather than inventing a cloth-root path.
Summary/window/trajectory v4 fail closed on stale generations, lifecycle or
storage-capacity failure, thread drift, malformed/cyclic/truncated hierarchy,
live-instance mismatch, or incomplete effective pose. The independent
verifier pins the static contract and native hashes; requires the exact
0/6/36/56 owner ranges and ordered 6/30/20/70 path vectors; checks 126 unique
registration records, 100 runtime Transform identities with 26 cross-owner
duplicates, four exact cloth names, one shared skeleton Root and actor parent;
and joins the trajectory through the first settled exact Endminf overview-loop
wrap. This is capture readiness, not recovered motion evidence; a fresh retail
run must pass the gate.
The maintained consumer gate is
`unity_endfield_graph_shader_lab/tools/verify_endminf_streamline_surface_capture.py`.
It independently rechecks the collected/runtime/graphics summaries, exact
Streamline options/token/constants/tag/evaluate/Present joins, the supported
1x1 exposure descriptor and payload, both packet schemas, formats, extents,
sizes, chronology, and all eight file hashes before publishing a compact
validation report. It deliberately creates no Unity assets from rejected or
absent evidence. Session `20260829T115328Z` exits at the expected missing-pair
boundary; run the verifier on the next capture before importing any temporal
diagnostic data.
Session `20260829T224523Z` retained and hash-validated both four-surface
packets, proving the next-Present surface scheduler, but it is still rejected:
the observer attached after `slInit`, its global Streamline chronology tables
overflowed before the Endminf trigger, and the options-to-Present association
is consequently one Present stale. The session has no crash artifact or D3D11
device-removal evidence. Its 398,131,200-byte Streamline pair plus the
664,355,624-byte deferred staging peak totals 1,062,486,824 bytes, however, so
the old concurrent schedule was a credible near-ceiling memory risk, not a
proven crash cause. These are observer lifetime/association and capture-budget
gaps, not retail-render conclusions. Keep the raw pair quarantined until a new
session passes the unchanged strict verifier. EndfieldCapture commit `18aed6a`
now resets the per-call chronology at the exact trigger, retains only the
bounded readable options warm-up, preserves initialization as independent
lifetime evidence, and freezes the completed pair. It deliberately does not
synthesize a missed `slInit`: the general injector has a pre-attachment launch
gap, while the existing early D3D11 proxy is graphics-only and rejects the Full
multi-provider mask.

The same session is not secondary-motion evidence. It observed 32,097
cross-frame cloth updates but zero scheduled, completed, or written Transform
jobs and one registration-lifecycle failure. Binary recovery subsequently
identified `WriteDoubleBufferTransform` as the active `last`-array publication
route. EndfieldCapture commit `fc37afc` retains the `4cac2fc` route and array
source evidence while bounding every observer callback stack frame; it requires
complete scheduled/completed/write counts, trajectory, publication, lifecycle,
hierarchy, effective-pose, and four-owner coverage. The current deferred
screen-shadow observer and its renderer-admission boundary are recorded above;
native observer coverage is not itself presentation authority. EndfieldCapture
also retains pixel-sampler slots s0-s5 for the targeted LitEffect draw while
preserving the bounded resource contract.
Session `20260830T154827Z` is rejected as a collected session: it has no
collector inventory, the selected audio provider had no requested window, the
graphics summary is incomplete with invalid cadence, and 36 of 72 regular
frame packets report selected-resource truncation. The 128 MiB shared graphics
lane spent about 91.5 MiB on automatic reservations and left only about
42.7 MiB for ordinary resources; this cannot close the pinned Default
resolver's t0-t27, MRT, and depth set. One exact M27 draw is locally complete
and corrects an earlier conclusion: its inactive b2 skin bit is accompanied by
a real bound VS t0 structured buffer, not an explicit null binding. That local
draw does not override the failed session gates. The maintained converter
authenticates a complete collector inventory, every artifact hash, one exact
draw, IA, b2, t0, textures, and pipeline descriptors, emits no captured
VB/IB/CB arrays, and leaves Unity-only owners unresolved. It now requires the
fixed-width, pointer-free `bindings.v3.bin` timing proof, exact draw-local owner
chronology, all five exact packet counters, and byte-for-byte JSON/wire parity;
historical v1/v2 sidecars are rejected. It deterministically rejects this
session before producing output.

The same session closes only the generic secondary publication route. All
2,299 scheduled writes completed and emitted 55,176 readable rows, but every
row belongs to one unowned team-16 tuple and its motion is effectively static;
the required 6/30/70 Endminf owner candidates are absent. The failed lifecycle
join exposed an observer ABI bug: the single-Transform `AddTransform` overload
returns one inserted index, whereas the observer decoded it as a packed
`DataChunk`. The corrected decoder derives length one and distinguishes valid
index zero from the manager-disabled zero return. None of these rows is
admissible as hair/cloth replay, a fitted curve, or a hardcoded trajectory.

EndfieldCapture commit `11ffb1a` added the missing bounded draw-local staging.
The first overview entry discovers exact descriptors and alias topology; its
Present allocates separate M21, M27, and Default-family plans. The second entry
copies mutable inputs immediately before each exact owner and outputs
immediately after it. Joined publication owns only the Default bytes and
authenticates the separate same-epoch M27 packet, whose retail draw precedes
M21 in the locally complete frame. Descriptor/range drift, owner/call/epoch
drift, alias drift, zero or unsupported resources, context contention, map
failure, event loss, and unacknowledged publication all fail closed. Lane paths
include the lane identity; that initial implementation capped each physical
plan at 384 MiB and their aggregate at 1 GiB. The fixed `bindings.v3.bin` ABI
has explicit
record sizes, counts, extent, layout hash, reserved-zero checks, and no native
container pointers. An independent Release run passed all 22 native tests five
times (110/110), including WARP readback and failed-session collector
quarantine. A fresh retail capture is now required; enter Endminf Character
Info twice in one bounded session so discovery and actual owner-draw capture
cannot be conflated.

Attempt `20260830T192522Z` failed before injection and contains no game
evidence: `host.target-ready`, `host.attach-started`, and `runtime.error` were
published in the same second, the one-shot Toolhelp module snapshot did not
resolve `LoadLibraryW`, and the runtime DLL never loaded. EndfieldCapture
commit `10484db` resolves the module that actually owns the local export
(Kernel32 or KernelBase), retries only transient/absent startup-module state
for at most five seconds, rechecks process identity on every probe, and does so
before `VirtualAllocEx` or `CreateRemoteThread`. Exit, identity drift, fatal
snapshot error, missing owner timeout, and out-of-range RVA now have distinct
fail-closed diagnostics. One hundred consecutive synthetic attachment
lifecycles and five complete 22-test passes succeed; this remains capture
readiness, not recovered renderer evidence.

Session `20260830T194329Z` proves that loader repair but is still rejected
evidence. The runtime attached and installed its hooks without a client crash,
then the Streamline surface lane failed before the deferred sequence. The exact
chronology is now closed: trigger Present 4967 contained one readable viewport-3
evaluation whose evaluate token did not join its tag/constants token; Present
4968 proved that interval had no complete packet; the first complete packet was
prior-Present 4968 and the second was the consecutive prior-Present 4969. This
is a bounded one-Present-deferred route, not permission to shift captured
resources or author replacement timing. EndfieldCapture commit `e2df98a`
admits only trigger offset 0 or that proven offset 1, stages type-13 exposure
only after a complete packet is admitted, requires exactly one bounded
unjoinable trigger evaluation on the offset-1 route, and revalidates the pair
before publication. Exposure Copy/Map/Unmap is confined to the first accepted
evaluation thread, rejects reentry and cross-device resources before copying,
and never holds the observer mutex across D3D11 calls. The automatic collector
uses one production/test gate for the surface pair, four two-entry exact-owner
packets, and all 72 regular packages. Late attachment is reported honestly as
`post-init-feature0-runtime-proof`: it leaves `initObserved=false`,
`initCalls=0`, and strict `sequenceComplete=false`; only the no-init surface
consumer accepts the exact later runtime proof. Initialization-argument
consumers still require a genuinely observed `slInit`. The settled patch passes
all 24 native tests five times, the three failure-sensitive tests 100 times
each, the 43-case strict M27 converter suite, and the 16-case independent
surface verifier. No usable surface, deferred-owner, or secondary-motion payload
has yet passed a fresh retail collection gate.

EndfieldCapture commit `4536910` hardens the maintained recapture launcher
without changing that evidence boundary. Its dedicated `endminf`/Full profile
selects only graphics plus secondary dynamics: audio's manual window and
gameplay-semantics completeness are unrelated to this visual gate and made
otherwise valid sessions uncollectable. Non-launching `--preflight-only` now
gates the exact installed executable, GameAssembly, metadata, provider set,
and runtime flavor; the latter is classified from a bounded offline PE export
table rather than a filename. Synthetic tests reject missing or changed native
inputs, missing manifest keys, renamed/swapped/unsupported runtimes, and prove
that absent audio and semantic artifacts remain valid for mask 5. The final
Release suite passed all 25 tests five times, and the installed-client preflight
validated Full mask 5 without starting the host or game.

Session `20260831T184411Z` is rejected evidence, but it is not a recorded game
crash. The exact-build observer shut down quiescently with 31 collector records,
zero dropped or invalid records, no writer error, and no crash artifact. Its
two-packet Streamline surface lane completed before deferred graphics, and the
51 accepted regular samples preserved the exact dense/eight-Present cadence.
Regular sample 52 failed closed at Present 2280 because the nominally
metadata-only tail still inherited a 33,243,136-byte 3840x2160 backbuffer
charge. The recorded deferred peak was 1,049,073,096 bytes, leaving only
24,668,728 bytes under the unchanged 1-GiB staging gate. Secondary dynamics
retained 4,824 rows, but every row was rejected at
`joinMissingTransformGeneration`: this build registers those transforms through
the bulk `AddTransform(VirtualMeshContainer, teamId)` overload, while the old
observer hooked only the single-Transform overload.

EndfieldCapture commit `dac972a` fixed the regular-tail staging defect, but its
new process-wide bulk Transform registration detour was not retail-safe.
Session `20260831T225915Z` reached login and ordinary resource loading, then
ended as Windows Application Hang event 1002 rather than a native crash. It
never wrote final provider summaries or a usable recovery payload. The old v1
status proves one decoded 13-entry callback and one aggregate rejection before
the hang event; no stack or dump proves which getter or lock branch executed.
The reachable inline per-entry engine getters, hierarchy walk, hashing, and
registry transaction are therefore the bounded correlated suspect, not an
established mechanism. The prior `20260831T184411Z` session had not patched that
entry and did not hang. Do not retry that per-entry design.

EndfieldCapture commit `051d835` re-enables the exact bulk function/body hook
only as a constant-work receipt observer. It forwards once through a non-null
MinHook trampoline with byte-identical arguments, never dereferences the
manager/container/MethodInfo pointers, and publishes one POD call/result receipt
to a fixed 1,024-slot lock-free ledger. Missing trampolines, ambiguous zero,
capacity exhaustion, callback non-quiescence, call-count mismatch, and
publication mismatch all fail closed. Clean stop writes
`secondary-dynamics/bulk-transform-observations.json`; the exact 976-byte body
hash and prologue still gate installation. This receipt does not materialize
the inserted per-entry Transform identities, so registration evidence remains
explicitly incomplete: evidence readiness stays false, the overlay rejects
`Numpad 5`, and the combined Endminf wrapper refuses a retail launch. The
post-fix Release build and full CTest suite pass 28/28, including preflight,
overlay, withheld-launch, and secondary-dynamics tests. This is synthetic and
disassembly-backed safety evidence only; no new retail run has tested the
replacement hook. The graphics-only Full profile remains available for
independent graphics evidence, but it cannot claim the missing lifecycle join.

EndfieldCapture commit `2605bc0` adds the separate, exclusive
`bulk-transform-receipts` diagnostic profile needed to validate that boundary
without enabling the full secondary provider. It installs exactly two
hash-gated hooks: bulk `AddTransform(VirtualMeshContainer, teamId)` and its
source-loop `VirtualMeshContainer.GetTransformFromIndex` callee. A TLS token,
exact return-address/container/thread checks, and fixed 1,024-row lock-free
ledgers retain the outer `DataChunk` plus each ordinal/opaque Transform pointer;
null identity, per-token reordering, duplicate/missing/range/count/token,
capacity, trampoline, publication, and teardown failures remain incomplete.
The profile creates no secondary recorder, snapshot, window event, Animator
trigger, or other dynamics hook, and its collector accepts only
`bulk-transform-receipts/{summary,observations}.json` labeled
`secondaryDynamicsEvidence=false`. Acceptance closes before hook disable; late
prologues forward through process-lifetime-retained trampolines without
publication. Independent callback/lifetime and profile-isolation reviews pass,
as does the final Release suite at 31/31. No retail run has tested this profile,
so the per-entry join and full dynamics evidence readiness remain false.

The deferred-capture consumer audit now uses one exact observer-build contract
for Animator, Streamline, and M31 verification. It pins the current Release
observer's source identity, DLL size/hash, 8,192-row Animator capacity, and
8,192-row M31 candidate/census capacities. The Streamline verifier accepts the
retail raw `sl::Resource` descriptor only when its optional width/height/format
tuple is either wholly zero or wholly agrees with the authoritative D3D11
descriptor, and it enforces tag < evaluate-entry <= copy-enqueue <=
evaluate-exit <= payload-ready plus the bounded retained prior-Present options
state. Rechecking `20260831T184411Z` against its captured observer identity now
removes the former impossible descriptor/timestamp errors; it remains rejected
only by six genuine incomplete-session gates. No additional capture is needed
to diagnose those historical failures.

The Endminf overview importer now preserves the complete serialized source
hierarchy order rather than relying on Unity creation order. It validates all
101 source nodes before mutation, applies every `m_Children` sequence, and
revalidates saved sibling indices plus direct Transform references. In
`overview_02/all`, M13/M14/M21 occupy source indices 2/3/10; in
`overview_04/1`, M29/M30 occupy indices 0/1. This closes deterministic
equal-queue source ordering only: no particle timing, scale, placement, TRS, or
runtime packet-owner chronology was changed or inferred.

The six `overview_01` stone systems no longer discard their authored external
forces. The exact stage now closes six enabled `ParticleSystemForceField`
owners on the source `suikuai (3)` through `suikuai (6)` hosts, with one unique
ordered influence per particle system. All six share one exact 16x16x16,
five-mip RGBA vector field recovered from its unique CAB-map carrier. The
extractor gates the carrier plus raw and inline payload identities; the Unity
importer reconstructs the `Texture3D`, applies every force-field payload, adds
the typed influences, and revalidates complete saved-prefab coverage. No
particle clock, material, transform, placement, scale, or source sibling order
was changed.

The current 770-frame canonical source-authored Unity run at
`scratch/character_recovery/endminf_v27_force_fields_full_770_d3d11_20260902_retry2`
is D3D11/status-ok and completes the ACL-backed start-to-loop sequence with all
four VFX roots and the settled loop. Captured secondary replay, the unverified
source solver, measured opening rectangles, and content-invalid deferred
presentation remain disabled. It retains the neutral preview clear plus only
the source `CharFloorEffect` queue-2000 and `GridFar` queue-2950 forward
overlay; `SphereOutside`, wall, ShadowPlane, the fitted plate, and the full
source-background/deferred consumer stay off.

Across the same 554-row clean-reference window, the best alignment remains the
bounded -1-frame candidate. V27 measures 32.2892 actor ROI, 34.1848 effect ROI,
and 15.2547 temporal-delta MAE, versus v26's 32.2896/34.1855/15.2507. The exact
external forces change 118 frames from indices 30 through 181 and peak near
frame 41; the actor/effect means improve slightly while temporal delta worsens
slightly. This is a small source-correct stone-motion change, not retail parity.
The dominant opening residual remains the unresolved broad multi-exposure and
SceneColor transport, while entrance hair, coat, and strap silhouettes still
lack certified secondary motion.

The strict retail screen-shadow verifier now also requires the two producer
snapshots and the consumer snapshot to occupy three valid, non-overlapping
stored payload ranges. One stored readback can no longer masquerade as multiple
draw-local observations. A fresh authenticated current-build receipt is still
required. The installed 2026-08-25 client replaces the previously pinned
native pair, so the dedicated observation-only EndfieldCapture lane now has a
separate current-build manifest rather than weakening the July audio manifest.
That manifest also authenticates the current signed Streamline 2.10.3
`sl.interposer.dll` and unchanged `sl.dlss.dll` before attachment. The August
interposer keeps the required x64 exports and ABI but has a different exact
file identity from the July module; the runtime pin and preflight manifest now
agree, so this drift fails before launch rather than after injection.
M27's global mip-bias equation is re-closed against that exact pair: the field
offsets survive, and the producer, publication, and dynamic-handler-accessor
bodies are re-hashed. The current publication no longer re-calls the accessor,
so the observer carries the accessor-authenticated handler identity from the
same HGCamera source slot only after its camera, epoch, sequence, and
additional-camera identity gates pass under the slot lock; caller-supplied
publication handler identities are rejected. Its Release build, complete
33-test native gate, source/session verifier gate, batch contract, and
nonlaunching exact-installed-build preflight all pass. A maintained raw-session
promoter now re-runs every inventory, source, identity, hash, equation, and
authority gate before it can write the minimal Unity Resource. The Resource is
still absent pending explicit promotion; its Unity owner fails closed, and the
c26 overlay preserves every other b1 source lane. The focused Python suite and
Unity D3D11 verifier pass the inline, malformed, pow2, overlay,
lane-preservation, and absent-Resource checks. Its unrelated historical
source-audit input is absent on this
checkout, so the aggregate verifier remains red even though the focused c26
component is valid. The current AssetMap revalidates the same renderer PathID,
material, mesh, and source VS, but the exact PS changed from the historical
8200-byte program to the current 8260-byte program. The capture and receipt
gates pin the current PS identity. The static mesh remains 72 indices; the
historical 1080-index runtime expansion remains a strict expected draw gate
and is now confirmed by the authenticated current-build draw. The inventoried
retail receipt admits the source equation with material and dynamic terms both
zero, equal 3840-wide input/output, and published `c26.xy=(0,1)`. This is source
authority for the observed physical-camera state even though it coincides with
the serialized virtual-camera default; captured constants were not used as the
source. `c26.xy` remains unpromoted until the maintained raw-session promoter
writes the Unity Resource. Adjacent `c19` TAA jitter and unrelated `c105` are
not substitutes. The inventoried session verifier remains explicitly
non-authoritative for presentation.

The archived `20260826T091023Z` exact M27 draw independently decodes
`c105=(0,0,0,0)`, but a strict existing-session verifier rejects it at inventory
binding because the contemporaneous collection inventory and source-frame
alignment artifact are absent. Those bytes remain one-draw validation evidence:
they do not establish the HGVFXManager field lifecycle, a sequence default, a
canonical publisher value, or presentation authority. Unity c105 therefore
remains disconnected.

The source-backed secondary-dynamics dependency chain is current, but the
recovered solver remains disabled. Exact per-owner child topology is now
retained as inert source data: the four owners have 5/22/16/65 child entries,
with packed UInt32 range headers and ordered UInt16 child arrays; MC_Hair
parent 17's exact ordered children are `[19,18]`. The builder validates
contiguous ranges, unique membership, and exact order, but no solver,
coordinator, prefab, or writeback path consumes these arrays while the selected
native CalcLine/Burst/managed route remains unresolved. Its 40-checkpoint comparison diverges at the
first post-publication sample (36.45 mm/6.82 degrees mean) and reaches
104.20 mm/10.89 degrees overall versus 20.24 mm/7.19 degrees with the solver
off. The generated PostProxy contract now closes the hidden JobHandle ABI,
four-stage dependency order, job payload layouts, exact scheduling identities
and batch sizes, and the pinned unpatched CalcLine managed worker. The
create-list integer kernel is now numerically source-closed for both pinned CPU
variants: its exact team gate selects four signed contiguous-index queues, each
using one atomic fetch-add reservation followed by `start+i` writes. It has no
capacity or team-index bounds check. This closure is route-independent because
the Burst and managed DirectCall fallback paths produce the same integer queue
result; the process-selected route is still unobserved. The CalcLine worker's
exact 17-parameter ABI, packed child traversal, Move-bit branches, signed local
rotation, parent/child quaternion equations, helper spans, and
`FromToRotation` parallel/antiparallel degeneracy branches are code-closed.
Each child selects a fresh direction (live position minus parent for Move,
otherwise the rotated rest vector), adds that value to the parent sum, and
passes that same per-child direction to the child `FromToRotation`; only the
parent write consumes the final sum.
Method `384854` is now also closed as a thin 296-byte argument forwarder into
the generated BurstDirectCall `Invoke`; it contains no line/vector math.
`Invoke` uses `BurstCompiler.get_IsEnabled` plus a nonzero
`GetILPPMethodFunctionPointer2` result for its indirect call, otherwise it
enters a separately emitted managed fallback. That fallback and method
`384856` have the same 396-instruction mnemonic sequence, operand structures,
18-branch control-flow topology, 22 direct-call targets, and numeric
immediates; only stack/local layout differs. Despite the job name, these
bodies write rotations and have no separate normal/tangent output buffer.
The exact non-null Burst target is now statically joined by its unique complete
17-argument and baseline/team/chunk/packed-child signature: export hash
`7342567c29c434b5b924be51bd8e34b7` assigns zero-fill slot `0x3c57b0` to the
pinned SSE2 `0x10ef20 -> 0x10f190 -> 0xf4100` or AVX2
`0x29a3c0 -> 0x29a5c0 -> 0x284c50` route. Both cores now also have a
source-only numeric transcription that matches character-neutral branch
vectors bit-for-bit, including the exact double-precision acos polynomial,
float32 quaternion grouping, packed traversal, empty-child no-write behavior,
and negative-X antiparallel zero-axis NaN propagation. Their separate SSE2 and
AVX2 scalar sin/cos helpers match the same source transcription across
controlled vectors and a stratified sweep of every finite float exponent.
Each core calls only its local helper twice; neither calls GameAssembly or IFix.
Their common source-closed value equation is now available through separate
inert SSE2 and AVX2 routes with the recovered binary64 acos polynomial and
explicit non-fused operation grouping. A fail-closed selector admits no route
without one validated Burst gate observation plus exactly one matched CPU
selection, or one validated Burst-disabled direct-call fallback with
`IFix(0x219)=false`. It is not referenced by the solver, frame coordinator,
prefabs, or Transform writeback. The live route remains the gate before global
PostProxy scheduling or trajectory validation can begin. Overall static runtime
selection is narrower but remains fail-closed. The pinned Burst
initializers construct global `Options(true)` and publish `_IsEnabled=true`
unless the exact disable command-line token or a non-empty/non-`0` disable
environment value sets `ForceDisableBurstCompilation`; the player-build
secondary-process predicate returns false. `GetILPPMethodFunctionPointer2`
null-checks all three arguments and then returns its first argument unchanged,
so its emitted null fallback branch is unreachable after a normal return (a
null input throws). The exact helper chain also proves that method `489292`'s
constant-false registered body is not the value stored in `IsBurstGenerated`:
the helper initializer stores whether `BurstCompilerService` returned a non-null
compiled delegate. Retail selection still depends on that async service result,
actual process inputs, later public Options mutation, and normal DirectCall
initialization, none of which is serialized here.
The post-proxy contract now mechanically rejoins and parses the hash-pinned
installed IFix report, VFS chunk/catalog, decrypted payload, loader map, and
exact native build. BeyondDynamicBone's generated wrapper initializer creates
an empty local wrapper array, and its `IsPatched` succeeds only for an in-range,
non-null slot. The sole installed local payload uses the `Gameplay.Beyond`
bridge; its 32-target table has no BeyondDynamicBone, `MathUtility`, or
`FromToRotation` target. This closes absence from local startup/bootstrap, not
live ownership: `InitWrapperArray` or a later remote/memory-only load could
still populate the patch-id entry used by `0x219`. The contract uses
no captured positions, timing, curves, fitted constants, or replay data.
A pure C# CalcLine value model now transcribes the managed/direct-call-fallback
and both pinned Burst CPU equations with explicit binary32 grouping. Its v2
detached identity-negative-scale/team fixture executes every baseline and
packed-child visit for Endminf's four hash-pinned owners in bind/rest plus two
deterministic synthetic perturbed states: all 12 topology cases match the
source transcription bit-for-bit on the native SSE2 and AVX2 cores, and only
the rotation buffer mutates. This broader gate exposed two
details hidden by the earlier branch vectors: Burst uses its packed-float4
quaternion grouping with child `FromTo` left-applied, while fixed/non-Move
children contribute their rest direction but neither execute child `FromTo`
nor write a rotation. The Unity verifier covers both rules, including MC_Hair's
fixed zero-offset child. The model still is not referenced by the solver, frame
coordinator, generated prefabs, scenes, assets, or Transform writeback.
Zero/non-finite and the finite negative-X antiparallel zero-axis case fail
closed. This is executable code recovery, not evidence that retail chose the
Burst or managed route on a particular frame. CalcLine runtime readiness
therefore remains false until live DirectCall and IFix selection are closed,
and it is not a retail-equivalent secondary solver: simulation, constraint,
collision, cross-frame ownership, and writeback selection remain separate
unresolved stages. No captured positions, curves, or timing are used as
implementation input.

Endminf's duplicate TransformAccess publication rule is now closed for the
hash-pinned installed target rather than left behind a stale route assertion.
The transform-read contract proves `UseAnimatorTransform=false` from its sole
compiled cctor writer, so the target selects ordinary TransformAccess
`WriteTransform`; the installed IFix snapshot has no `BeyondDynamicBone`
target. All 126 source lanes remain distinct, but every one of the 26 duplicate
paths has at most one write-eligible entry: Ribbon2 owns six, Ribbon owns
eighteen, and the two fixed/fixed pairs publish neither entry. Execution order
and owner priority are therefore irrelevant, and the Unity publication adapter
already applies the matching per-entry flags. Changed files, a future/live IFix
payload, or any duplicate group with two eligible writers still fail closed.
This removes duplicate-winner selection from the current blocker set; it does
not select the live CalcLine route, supply cross-frame/team state, validate the
solver trajectory, or authorize default writeback.

CalcLine route promotion is now an explicit immutable evidence boundary rather
than a manual interpretation of the general telemetry report. The dedicated
`build_secondary_dynamics_calc_line_route_artifact.py` builder independently
revalidates the referenced trace, binds the trace/validation/manifest plus
pinned disk and runtime native identities by SHA-256, and publishes a route
only for one mutually exclusive closure: enabled Burst with exactly one
source-authenticated SSE2/AVX2 selection, or disabled Burst with exactly one
unpatched `direct_call_fallback` IFix observation. Missing, duplicated,
conflicting, or tampered inputs fail closed. The resulting selector payload is
still inert: it does not connect the solver, frame coordinator, scene assets,
Transforms, or writeback.

The historical M27 live exact-ABI admission verifier validates the prior source
subprogram-113 shader pair, actual ParticleSystemRenderer/mesh/material
identities, 60/68-byte IA layouts, five MRT/depth descriptors, and full t0-t3
texture mip payloads. The current exact keyword pair moved to source subprogram
107: its VS is byte-identical, while its PS changed, so the historical pair is
no longer a current-build admission authority. The current capture gate pins
the new PS; the wider Unity exact-ABI artifact must be regenerated from that
current program before it can claim current-build presentation admission.
Its b0 producer is now source-closed from the live camera plus per-camera
contiguous history: all 22 published vectors pass the D3D11 GPU verifier, reset
and discontinuity reuse the current frame, and captured constant-buffer bytes
remain validation-only. All 50 selected b3 words are tied bit-exactly to 37
original material fields, explicit packoffsets, the generated Unity material,
and the compatibility shader's effective defaults. The b1 source contract has
distinct readiness for target dimensions, perspective, TAA jitter,
physical-camera global mip bias, exposure, VFX player/time, and the HGVFX
anchor. Its partial live publisher admits c27 only from the source-closed
Manual-exposure path with the exact selected camera/environment gate,
automatic exposure disabled, a persistent non-null state, and finite positive
exposure. It publishes c103 from the unique actor root plus `Time.time` only as
an explicit lab carrier, not as proof of the retail selected-frame HGVFX
identity. The authenticated c26 Resource/overlay route is now statically
connected and the current inventoried session `20260902T164359Z` is promoted
as the exact `(globalMipBias, globalMipBiasPow2) = (0, 1)` source. The promoted
receipt explicitly grants no presentation authority; c19 and c105 remain
zero/unready and exact b1 admission remains closed. The historical July capture observed
c26.xy=(-1,0.5), while the current authenticated physical-camera receipt proves
c26.xy=(0,1) for its observed selected state. The exact-build observer
now admits any finite live value only when the authenticated source equation,
later publication, and exact M27 draw join in one ordered epoch. Its dedicated
collector ignores only unrelated aggregate graphics-provider incompleteness
and safely unfinished generic deferred frames; explicit deferred failure or
impossible publication-counter ordering still rejects. It requires a complete
source receipt, the Animator gate, exact session/runtime identity, and strict
inventory verification. The strict inventoried session verifier and
raw-session promoter admit the current receipt as source evidence and bind the
Unity Resource to the session/report/receipt/runtime identities. Admission also still
requires a synchronized runtime join for engine-produced b2, its inactive skin
bit plus the authenticated draw-local VS t0 outcome, b4, ordered MRTs, s0-s5, the observation
writer, and the actual generative ParticleSystemRenderer path. Captured packet constants and fitted
placement, transforms, curves, texture sampling, or lighting are never an
admissible substitute.
After that gate passes,
`unity_endfield_graph_shader_lab/tools/analyze_endminf_streamline_surface_pair.py`
decodes the captured R11G11B10 input and RGBA16F output without third-party
packages, writes fixed-exposure input/output/difference PNGs for both frames,
and reports sampled consecutive input-versus-output temporal change. It is an
offline diagnostic only: its tonemap and aggregate deltas localize the consumer
boundary but do not claim an internal DLSS algorithm or Unity parity.
Capture runtime builds are statically linked to the MSVC CRT/STL: Endfield's app-local
older runtime is not an evidence-safe ABI for newer observer synchronization
objects, and injected-runtime dependency tests fail if that boundary regresses.

## Main animation gap

Endminf's source ACL body timing and pose publication are closed for
`ui_overview_start -> ui_overview_loop`. The primary remaining animation
residual is entrance secondary motion in the recovered hair, coat, and strap
chains; settled-loop oracle error is small, while entrance checkpoints diverge
materially. The next bounded recovery is the process-selected CalcLine route:
observe the nonzero Burst DirectCall target/CPU variant and IFix
`FromToRotation` patch `0x219`, integrate only the selected exact kernel through
the existing 5/22/16/65 child arrays, and require the 40-checkpoint trajectory
regression to beat solver-off before enabling writeback.

The latest full-frame comparison still places the largest overall visual gap
earlier than that animation residual: roughly 0.4-1.25 seconds of the opening
needs the live multi-exposure/SceneColor temporal owner chronology. The rejected
opening-strip approximation remains default-off; recover the live pre-Uber
producer/consumer order before changing canonical presentation.

Beyond this selected scope, remaining runtime systems include generalized
controller and rotation-only root-motion routing, broader Avatar transport,
grounding and IK, facial emotion/lip sync, gaze, secondary motion outside the
certified positive-scale stationary Endminf subset, remaining item/deco/FX
lifecycle, gacha timing, and non-playable runtime assembly.

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

The maintained all-character batch now performs a source-only Endminf preflight
before Unity starts. It validates the 31 profile/render/light rows, both legacy
portrait sources, the four-root/101-node Overview stage and its complete
material/mesh/texture closure, the semantic effect-animation and `suikuai`
contracts, and regenerates both ACL runtime import contracts. The Unity entry
then imports ACL first, rebuilds the Endminf actor without deleting the ACL
assets, validates the pose driver and packed outline streams, rebuilds the four
Overview roots and exact clips, restores LitEffect source materials and direct
prefab bindings, verifies secondary-dynamics bindings, and only then rebuilds
the cached viewer and verifies portrait orientation. This replaces the former
path that could reuse a stale Endminf prefab or erase ACL `.asset` files without
regenerating them. The batch waits while Unity, Unity Hub, Endfield, or the
project lock indicates shared use; it never removes or bypasses the lock.
The effect-LOD contract is pinned to the current installed native build and
retains all 18 methods and 11 fields; only
`EffectInstance.m_settingLodLevel` moved from `0x8c` to `0xac`. Its exact
quality/target masks, initialization, refresh predicate, hot/cold caller
ownership, and installed-IFix nonreplacement gates remain closed. Current
AssetMap/CAB remapping also refreshes the exact 39-material/12-mesh/45-texture
Overview dependency set without a broad asset export. Skeletal-morph avatar
loading prefers the historical Persistent mirror and falls back to the current
StreamingAssets export when the mirror is absent.

## Recovery queue

1. Do not run the combined Endminf graphics-plus-dynamics wrapper while the
   bulk Transform per-entry identity join is unavailable; it rejects a real
   launch even though the bounded receipt hook is installed. Method
   `384854` and its DirectCall managed fallback are statically closed; the
   remaining CalcLine route boundary is the runtime-selected nonzero Burst
   function pointer plus the IFix selection state for `FromToRotation` patch
   `0x219`. Do not implement the managed/fallback equations as retail-active
   until those runtime states close.
   The dedicated `burst_resolver_telemetry.py` v3 observer now supplies that
   narrow lane without depending on the unavailable Transform identity join.
   After the exact CalcLine
   GetFunctionPointer wrapper returns, it reads only the hash-pinned resolver
   slot at RVA `0x3c57b0`; validation names `x64_sse2` or `avx2` only for the
   two source-authenticated entry RVAs and keeps missing, null, unreadable,
   unknown, or conflicting observations incomplete. The same bounded trace
   observes the exact Burst-enabled return and `IsPatched(0x219)` only on
   admitted CalcLine caller stacks. Its installed-build preflight is:
   `python unity_endfield_graph_shader_lab/tools/burst_resolver_telemetry.py --check-only`.
   `capture_endminf_burst_resolver.bat` now records unique trace, validation,
   and immutable CalcLine-route paths, then rebuild-checks the artifact before
   reporting route closure. The tooling does not itself close either live
   route; collect one actual trace and require a checked route artifact before
   selecting even the inert value kernel. Solver/writeback integration remains
   a separate gate. Keep the older trajectory capture validation-only. If new
   registration identity evidence is needed, close Endfield and run
   `tools\EndfieldCapture\StartCapture.bat bulk-transform-receipts`; require a
   complete diagnostic-only two-hook artifact before designing post-writeback
   pointer/hierarchy enrichment, and never treat that artifact itself as
   secondary-dynamics evidence. If new
   graphics evidence is independently
   required, use
   `StartCapture.bat graphics full` with Endfield closed and do not interpret
   it as secondary-motion evidence.
   Accept strict `observed-slInit` only when it is genuinely retained;
   otherwise the no-init Streamline surface consumer may use only the exact
   `post-init-feature0-runtime-proof`, while all initialization-argument
   consumers remain incomplete. Validate any graphics-only Streamline result
   with
   `python unity_endfield_graph_shader_lab/tools/verify_endminf_streamline_surface_capture.py SESSION`
   before generating Unity diagnostic assets, then run
   `python unity_endfield_graph_shader_lab/tools/analyze_endminf_streamline_surface_pair.py SESSION`
   to compare the exact input/output pair offline.
   The screenshot-measured opening strip is now default-off in canonical and
   interactive presentation; its correctly ordered pre-temporal diagnostic did
   not reproduce retail's broad multi-exposure history. Recover the live
   pre-Uber owner and consumer chronology instead. Keep the rejected public NGX
   proxy and M31 replay diagnostic-only until that chronology is complete.
2. Close the palm/crystal runtime owner chronology from same-session evidence.
   Static serialized sibling order is already exact for the complete 101-node
   hierarchy, including M13/M14/M21 at 2/3/10 and M29/M30 at 0/1; it does not
   prove game-runtime packet admission or temporal-owner order. Retain the
   source-authored M13 and M21 timelines; their exact packet checkpoints remain
   bounded diagnostics and their controlled A/Bs reject compensatory resizing,
   retiming, or removal. M20's live gas checkpoint is already source-closed by
   the exact frame-1748 packet and requires no further capture. Its shared
   VFXBaseV2 shader pair plus a 36-index count is not a sufficient owner key:
   the combined capture gate now additionally requires the authenticated
   36-byte/stride-zero/R16 IA shape and complete 256x128 BC7-sRGB PS-t1 atlas,
   which admits only frame 1748 in the authority session. Keep that one-sample
   transport diagnostic while the generating runtime is incomplete. Visually
   certify M29, M30, and M14 one at a time before changing defaults or
   suppressing their compatibility renderers. Preserve the captured hierarchy
   transforms and serialized source sibling order unless a same-session
   packet-to-palm registration proves a specific delta. Canonical Viewer report v26 now
   enumerates any presentation-diagnostic selector that escaped the maintained
   forced-off policy and fails video export unless the entire packet/deferred/
   Uber diagnostic set is explicitly zero. For M27, keep the independently
   pinned source shell at t0-t5 and the source-closed b0/b3 producers; leave b1
   closed until each live owner is recovered. Promote the admitted inventoried
   M27 receipt through the maintained raw-session builder when refreshing the
   c26 Resource; the current promoted receipt remains source-only and must not
   be treated as presentation authority. Do not copy the captured constant. Retain
   engine-produced b2 and use the next
   admissible observer run to join its inactive skin bit to the already observed bound,
   complete VS t0 palette payload, s0-s5 descriptors, b4 producer/value
   lifecycle, and synchronized target evidence. Require the live
   exact-ABI verifier to admit the generative ParticleSystemRenderer draw before
   presentation; never restore captured packet constants or tune placement,
   transforms, curves, texture sampling, or lighting to compensate.
3. Generalize the finished Endminf path and rebuild every playable character
   without actor-specific renderer forks.
4. Keep changing inventories and exhaustive validation output under
   `reports/assets/character_recovery/`; update this file only when the durable
   conclusion or evidence boundary changes.

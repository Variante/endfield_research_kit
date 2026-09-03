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
- A controller or effect definition proves authored composition, not that the
  retail frame executed it.

## Rendering boundary

- Direct3D11 is the authoritative lab backend because it matches the recovered
  retail shader binaries. D3D12 experiments remain labeled diagnostics.
- CharacterNPR, LitEffect, deferred resolve, shadow, post-processing, temporal,
  and Streamline resources retain separate producers and frame-lifetime gates.
- Material keywords, pass/queue selection, constant-buffer values, textures,
  depth, motion vectors, shadows, exposure, and history are accepted only from
  their exact serialized or observed owner.
- A resource that exists or hashes identically is not necessarily bound to the
  selected draw. Same-camera, same-size, same-frame, submission-order, and
  lifetime constraints remain part of the join.
- Compatibility shaders and lab-created buffers are explicitly approximations
  until the retail producer and consumer are independently closed.
- The AnimeStudio-owned shader recovery path may provide readable code and
  metadata. It does not prove runtime variant selection or final appearance.

## Secondary dynamics boundary

Endminf's enabled cloth components, roots, colliders, constraints, serialized
payload arrays, and selected native schedule are partially recovered. The lab
retains exact bytes and typed outer layouts while leaving unknown inner values
opaque.

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
  bindings, lighting/shadow resources, post-processing, temporal history, and
  final presentation route.
- Recover Endminf's complete secondary-dynamics numeric solver, owner identity,
  job completion, and writeback/history.
- Complete entrance/loop VFX timing and lifetime without hand-authored offsets.
- Expand converter and shader fixtures while preserving exact source bytes.
- Turn the validated Endminf solution into data-driven profiles for all
  playables without actor-specific renderer forks.
- Keep capture tooling bounded, observation-only, exact-build gated, and
  reproducible across client updates.

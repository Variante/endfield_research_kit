# Character rendering and animation recovery

This topic owns the durable recovery model for the optional Unity reconstruction
lab. It is not a WebUI page guide and no normal WebUI/export workflow depends on
the lab, 3DMigoto, or EndfieldCapture.

The parity, rendering, animation, secondary-dynamics, capture, workflow and
recovery-queue detail now lives in `endfield_reconstruction_lab/docs/`. That
lab is an optional submodule and may be uninitialized in a fresh clone; the
framing, ownership and evidence rules kept below hold with or without it.

## Why this file remains

The Characters page catalogs identities and assets. The reconstruction lab has
a different goal: reproduce one retail Character Info render closely enough to
validate reusable model, animation, material, lighting, post-processing, VFX,
and secondary-dynamics contracts. Those parity rules and observation gates need
an independent source of truth.

## Maintained ownership

| Area | Owner |
| --- | --- |
| Lab workflow and generated Unity assets | `endfield_reconstruction_lab/` |
| Extracted Unity objects and conversion quality | `tools/AnimeStudio/` |
| Static semantic asset identities | `memory/game_data/unity_assets.md` and Assets reports |
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

## Where the detail lives

`endfield_reconstruction_lab/docs/README.md` is the doc map. Read
`overview.md` first: it carries the current Endminf target.

- `overview.md` -- scope, current target, ownership, evidence hierarchy.
- `model-and-animation.md` -- object identity, Animator and facial ownership,
  root motion, CharEffect scheduling.
- `rendering-pipeline-and-shadows.md`, `rendering-effects-and-post.md`,
  `rendering-native-publication.md` -- the three-part rendering boundary.
- `secondary-dynamics.md` -- cloth/bone state and the missing solver writeback.
- `capture-and-reference.md` -- 3DMigoto/EndfieldCapture gates and the retail
  reference comparison policy.
- `workflow-and-gaps.md` -- the focused-change loop and the recovery queue.
- `lighting-dxbc-verification.md` -- CharacterParams-to-`cb1` mapping and which
  lab shader code is actually live.

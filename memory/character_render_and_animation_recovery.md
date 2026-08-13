# Character rendering and animation recovery

## Current status

The Unity lab is a source-backed reconstruction of Endfield character models
and Character Info presentation. It is useful for asset and shader research but
is not the retail renderer.

| Layer | Current status |
| --- | --- |
| Playable models | 31/31 imported and rendered |
| Canonical post-model identities | 156/156 have generated prefab paths |
| Static playable Overview assets | strong |
| Selected CharacterNPR equations | partial but source-backed |
| Complete HGRP/CharInfo frame | partial |
| Playable UI clips | complete for the selected `all-ui` scope |
| Runtime animation behavior | partial |
| Retail visual parity | not reached |

The canonical identities are 31 playables, one NPC character, one cutscene
clone, 94 enemies, and 29 ability/prop actors. Six modular ambient-NPC
archetypes are imported as labeled source kits rather than finished characters.

## What is recovered

- Playable post-models, LOD0 mesh bindings, materials, textures, cameras,
  profiles, lights, portraits, and Overview animation sources.
- Dependency-safe static prefab baselines for every canonical non-playable
  post-model identity.
- Current Persistent patch-layer roster/controller data alongside base
  StreamingAssets models. Liino validates that cross-layer boundary.
- Playable UI body and private item/deco clips for the selected scope.
- The Endfield 101-muscle Avatar contract and selected exact clip/Avatar paths.
- Narrow verified behaviors for blink, facial, and physical-transform fixtures.
- Selected CharacterNPR, eye, hair, shadow, material, particle, gacha, depth,
  GBuffer, light, cookie, and irradiance diagnostics.
- Fail-closed native texture payload recovery for the admitted playable set.

Generated mesh identity is source-scoped. Chen and Chenpast remain separate
model families with distinct containers, Animator identities, VFS sources, and
generated mesh GUID sets. Shared facial or animation bases do not merge their
mesh ownership.

The native `HGRenderPath` slot roles are now corrected from the installed
UnityPlayer registration: wrapper `+0x8` is the BeforeCulling setup
(`0x1812fdb20` → `0x1813022d0`), `+0x10` is the Render forwarding wrapper
(`0x1812fdd80` → `0x1813018c0` → `0x1813042d0`), and `+0x18` is Destroy
(`0x1812fddc0` → `0x181300ab0`). The bounded BeforeCulling/Render bodies still
show no factory staging, CommandBuffer/Compute upload, or kernel-7 edge; the
factory-record-to-`_UploadBuffer` link remains fail-closed.

The follow-up RenderGraph census separates the shared graphics-context
dispatch slot `+0xab8` (used by the immediate ComputeShader helper family)
from the HGRenderPath graph-record lifecycle slots `+0xcd0`, `+0xea0`, and
`+0xeb0`. The checked Render, helper, and graph-state bodies contain no
`+0xab8` call and no direct factory staging or GPUDriven dispatch target, so
the factory-record-to-`UploadPerDrawParams` kernel-7 edge remains unproven.
The complete UnityPlayer `+0xab8` census has ten sites: fixed kernel `1`
resource passes, dynamic generic helpers, and one command-stream interpreter;
none statically identifies kernel `7` or binds factory channel-2 `+0xd0`, so
the dynamic command/resource record remains the only open bridge.
The current GameAssembly PData-scoped dispatch census finds 110 direct
`CommandBuffer.Internal_DispatchCompute` calls from 37 named built-in render
passes, with no `factory`, `perdraw`, `upload`, or character producer; the only
direct `ComputeShader.Dispatch` caller is unrelated MagicaCloth physics code.
This closes the direct managed dispatch candidates, while leaving the native
command-stream record feeding the generic interpreter open and fail-closed.

## Evidence boundary

Every production value must come from serialized data, installed native
behavior, or a validated runtime capture. Unknown values stay neutral,
diagnostic, or disabled.

Static prefab enumeration proves admitted geometry and hierarchy, not final
appearance or runtime activation. Shader decompilation proves a selected
program’s inputs/outputs and render state, not the active keyword variant or
frame schedule. A recovered clip does not prove controller transitions,
blending, IK, facial state, physics, or effect timing.

Do not enable generic Humanoid animation for enemies or props without
actor-specific source evidence. Do not treat filename similarity, shared
materials, or controller proximity as exact actor ownership.

## Main rendering gap

The missing work is the coupled retail frame contract:

- HGRP light scheduling, culling, cookies, and irradiance;
- character shadow atlases, screen shadows, stencil, and VisibilitySH;
- shared depth, GBuffer, motion, and deferred resolve;
- exact material variants, mip payloads, and live renderer state;
- exposure, history, post-processing, and final composition;
- retail-frame validation across representative characters.

Current images are recognizable but flatter than retail, especially around
faces, pale cloth/armor, hair, dark hardware, and contact shadows.

## Main animation gap

Remaining runtime systems include:

- controller transitions, interruption, blending, and root motion;
- broader exact Avatar/clip transport;
- grounding, foot IK, hand targets, and constraints;
- facial emotion, lip sync, gaze, look-at, and animation events;
- secondary motion, wind, cloth, hair, and dynamic bones;
- item/deco/FX lifecycle and gacha timing;
- non-playable rigs, controllers, animation, and VFX execution.

The non-playable baselines prove enumeration and admitted dependencies only.
Runtime modular assembly, VFX, material overrides, animation, and exact
keywords/passes/queues remain incomplete.

## Maintained workflows

```bat
cd unity_endfield_graph_shader_lab

.\open_character_recovery_lab.bat
.\build_all_character_recovery.bat
.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat
.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat
.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
```

Canonical viewer:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Generated assets are rebuildable. Fix generators, importers, runtime code, or
shaders rather than hand-editing generated prefabs.

## Durable reports

Changing inventories and exhaustive renderer/shader proof live under
`reports/assets/character_recovery/` and the lab’s own reports. This file keeps
only stable interpretation and priorities.

## Highest-value next work

1. Close the remaining native component identities and retail culling survivor
   list before populating shadow, depth, GBuffer, irradiance, cookie, and
   VisibilitySH inputs.
2. Validate representative paths against accepted retail captures.
3. Extend texture/mip and material-variant recovery only where visible.
4. Generalize animation from another exact Avatar/clip oracle.
5. Add controller, grounding, facial, FX, and secondary systems behind
   source-validated fail-closed gates.
6. Upgrade representative non-playable families before broad parity claims.

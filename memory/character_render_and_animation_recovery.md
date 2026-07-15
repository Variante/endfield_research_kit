# Endfield character rendering and animation recovery

This is the single current status and workflow memory for
`unity_endfield_graph_shader_lab/`. It replaces the earlier chronological
shader, CharInfo, playable-character, client-observation, and animation
snapshots.

## Current conclusion

The project is now a useful, source-backed reconstruction of Endfield's
Character Info presentation, but it is not the original renderer and it is not
visually at parity with the retail client.

The strongest result is data recovery. The canonical viewer contains all 28
concrete playable post-models, their original UI overview clips, exact material
and texture records, exact operator cameras, per-operator CharacterVolume
modifiers, portraits, and all exported overview-light groups. The current
Unity output is repeatable, cleanly compiled, and much closer to the supplied
Wulfa and Zhuangfy references than the former Standard-material viewer.

The largest remaining problem is no longer missing texture or camera data. It
is the coupled retail frame contract: exact material response across all
variants, the modified-HGRP light and shadow schedulers, the shared
depth/stencil/GBuffer path, `SphereOutside` deferred lighting, `ShadowPlane`
stencil/character-shadow/VisibilitySH inputs, live per-frame state, and final
compositor behavior. The current images remain obviously flatter and place
light and shadow differently from retail, especially on faces, pale
cloth/armor, hair, dark hardware, and ground/contact shading.

Animation recovery is intentionally narrower. Every playable character has
the original overview entrance and loop in the canonical project, and selected
private item-widget clips play on independent layers. This is clip playback,
not recovery of the complete Animator/controller/facial/physics behavior.

There is no honest single percentage for the whole effort. If rough
engineering ranges are useful, they should be read as scope estimates rather
than test scores:

| Layer | Current maturity | Meaning |
| --- | --- | --- |
| Static actor/CharInfo assets and serialized parameters | high, roughly 90%+ for the selected Overview scope | Most identities, payloads, transforms, textures, profiles, and selected clips are source-derived and validated. |
| Selected local CharacterNPR surface equations | medium-high, roughly 60-75% | Important cloth, skin, hair, eye, outline, shadow, and post equations are ported, but variant coverage and live inputs are incomplete. |
| Complete retail CharInfo frame behavior | partial, roughly 35-50% | Several exact diagnostic subgraphs exist, but the complete HGRP scheduling/resource contract is not active as one production path. |
| Final visual parity | not reached | Wulfa and Zhuangfy are recognizable and compositionally close, but still visibly different without close inspection. All 28 characters have not been retail-frame validated. |
| Overview animation clips | complete for the chosen two-clip-per-actor scope | 56 body clips are imported, plus 14 selected widget clips. |
| Original animation behavior | early/partial | Only Wulfa and Zhuangfy have meaningful controller-level recovery; facial, event, root-motion, FX, and secondary systems remain open. |

DLSS/DLAA, frame generation, and a blanket x8 sampler imitation are excluded
from the requested shader-recovery scope. Their absence should not be used to
explain broad face/material-light errors. The retail/lab backend difference
still matters when interpreting edges, precision, and temporal artifacts.

## What is runnable now

### Canonical full viewer

Open this scene when character selection or animation playback is needed:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

or run:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\open_character_recovery_lab.bat
```

The top-left Model dropdown lazy-loads one of 28 canonical playable prefabs,
unloads the previous runtime-created actor, and swaps the recovered CharInfo
profile with it.

### Fast shader viewer

Use the animation-free scene for ordinary material and render-pipeline work:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRenderStyleFast.unity
```

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\open_fast_render_style_viewer.bat
```

It keeps static sampled Wulfa/Zhuangfy poses and the render stack while
removing `Animation`, `Animator`, overview playback, layer synchronization, and
procedural IK from the scene.

### Current accepted images and reports

| Artifact | Current status |
| --- | --- |
| `scratch/character_recovery_viewer.png` | Latest shared-viewer Wulfa render, 1920x1080, SHA-256 `AD3B35AA8B61806C3055E55F9776A42D06E7BDDC71C27E1CA14C24AB72335B61`. |
| `scratch/runtime_reference_wulfa.png` | Current 4K cumulative Wulfa reconstruction, SHA-256 `C5D035DD00730E94B7DE6D4FDA9EFC4E1DEBF832FAAB56077673D3FA998ACBC5`. |
| `scratch/runtime_reference_zhuangfy.png` | Current 4K cumulative Zhuangfy reconstruction, SHA-256 `FC22179F2268B33FF7A45601A6A93BD42F7249F0D215BCAB7DBFA118C0E0673C`. |
| `unity_endfield_graph_shader_lab/ReferenceCaptures/{Wulfa,Zhuangfy}/front_full.png` | Supplied retail references. They include the ordinary overlay UI and therefore are not direct character-only pixel targets. |
| `scratch/character_ui_import/renders/*.png` | 28 current 1920x1080 source-profile roster renders. |
| `scratch/character_ui_import/renders/playable_character_preview_manifest.json` | Status `ok`: 28 attempted, 28 succeeded, zero failed/pending. |
| `scratch/character_ui_import/widget_renders/*.png` | Seven source-bound widget-entry renders. |
| `scratch/character_ui_import/widget_renders/playable_item_widget_preview_manifest.json` | Status `ok`: seven succeeded, zero failed. |

The latest viewer update, viewer preview, all-roster render, item-widget render,
and all-playable import logs exit batch mode with code zero and contain no
bounded C# compiler error, shader error, null reference, or unhandled exception.
The roster postflight also reports zero magenta error-shader pixels. This proves
build/capture health, not retail fidelity.

## Canonical source and generated coverage

### Playable roster and generated assets

- `CharacterTable` has 29 rows. Twenty-eight rows join to a concrete shipped
  `<charId>_postmodel` Animator and are imported.
- `chr_9000_endmin` is an abstract selector row with no concrete post-model and
  is correctly excluded. Male and female Endministrator post-models are both
  included.
- The canonical generated root is
  `Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/<Actor>/`.
- Current generated inventory: 28 actor directories, 28 prefabs, 70 `.anim`
  assets, 367 mesh assets, 388 materials, and 1,152 imported files under actor
  texture directories.
- Only LOD0 non-VFX body renderers are active in the character viewer. Lower
  LODs, ordinary actor VFX renderers, and shadow proxies are deliberately not
  stacked into the beauty render.
- Old duplicate generated roots `Characters/Wulfa`, `Characters/Zhuangfy`, and
  `Characters/Mifu` were removed. Their old 563-clip/roughly-29-GiB research
  cache is not the current canonical animation state.

### Per-character CharInfo profile coverage

The source-profile extractor has complete records for all 28 playable actors:

- 28 authored Overview cameras, including position, FOV, clip planes, LookAt,
  and neutral centered Composer behavior;
- 28 portrait textures, Sprite geometry records, and authored overview image
  offsets;
- 28 actor-specific `HGCharacterVolume` modifiers;
- 28 overview additional-light groups containing 246 enabled lights;
- 119 enabled `CharInfoLightFollower` records;
- maximum source rig size 13 lights for Aglina.

The compatibility GPU carrier has 16 slots so no recovered Overview rig is
truncated. The capacity and dynamic loop are implementation choices; the
individual light records are original data.

Primary profile payloads:

```text
Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPlayableProfiles/source_profiles.json
Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/operator_lights.json
Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/character_render_parameters.json
render_parameter_provenance.json
```

### UI-deco and item-widget coverage

- Original `prefabs/uimodels/decoitems/chr_*_deco_*` recovery finds 35 prefabs
  for 15 actors.
- Thirteen actors have no exact matching UI-deco prefab in the current export;
  this is recorded as source-proven zero rather than filled with a guessed prop.
- The current selected Overview scope imports 14 private-rig widget clips for
  seven actors. All selected transform bindings resolve without gaps.
- The wider inventory contains many more associated UI/deco clips, but name or
  suffix association alone is not proof that a controller activates them in a
  particular state.

## Evidence chain and original-pipeline understanding

The reconstruction uses original game data as the authority. Screenshot
fitting is a diagnostic only and is not allowed to become a per-character
render parameter.

Primary evidence layers are:

1. AnimeStudio exports original GameObject/Transform/Renderer/Mesh/Material/
   Texture/AnimationClip/AnimatorController/MonoBehaviour records and raw
   shader programs from installed VFS data.
2. Original material JSON establishes shader family, keywords, render queues,
   textures, colors, floats, and feature gates.
3. AnimeStudio bytecode sidecars retain subshader, pass, stage, platform,
   keywords, and packed Vulkan bindings.
4. Ruri.ShaderDecompiler and SPIRV-Cross supply instruction-level D3D11/Vulkan
   dataflow for selected variants.
5. FractalMiner's readable HGRP reconstruction supplies semantic names and
   equations where it agrees with original bytecode; its explicitly removed
   features are never treated as proof of absence in retail.
6. Installed IL2CPP metadata/native code supplies publisher/update/scheduling
   behavior and enum semantics.
7. The original NVIDIA Vulkan PSO cache corroborates compiled shader families;
   it is not an execution timeline and cannot select a live branch.
8. RenderDoc captures of the standalone Unity lab validate the reconstructed
   D3D12 bindings, formats, passes, and draws. They are not captures of retail.
9. Supplied lossless screenshots and videos validate presentation, recurrence,
   pose, and visible error, but do not define hidden constants or pass order.

The symbol-aware sidecar bridge recovered exact selected shader fields rather
than generic constant-buffer slots. One representative closed carrier is the
ambient exposure term:

```text
mix(EnvironmentGlobalParams0.x, 1.0, CharacterParams12.w) * ExposureParams.x
```

This is source-level equation evidence for the selected variant, not proof of
the live values or scheduling that retail supplied to those fields.

The retail client observed on this machine is Unity 2021.3.34f5 using Vulkan
and a proprietary source-modified HGRP. The lab is Unity 2022.3.62f3 with a
custom D3D12-capable compatibility SRP. This is an architectural gap, not a
small material preset difference.

The recovered CharInfo frame contract is broadly:

1. shared physical camera and settled Cinemachine Composer;
2. depth/pre-depth and character PreG classification on shared depth/stencil;
3. ordinary deferred scene/GBuffer work and character shadow producers;
4. CharacterNPR forward surface, outline, and overlay composition;
5. scene bloom, grading LUT, `ACES_modified`, vignette, exposure normalization,
   OETF, and dither;
6. source world-space portrait after Uber while sampling the preserved primary
   scene depth;
7. later overlay UI and final presentation/copy/scaler work.

The lab implements meaningful parts of this chronology, but not every producer
or shared attachment as one retail-equivalent path.

## Shader and render-pipeline status

Status terms below are deliberate:

- **source-closed**: identity, data, and selected behavior are recovered from
  original evidence;
- **ported subset**: selected original behavior runs in the lab but is not the
  whole shader/pipeline family;
- **diagnostic**: validated behind an opt-in and not promoted to ordinary
  rendering;
- **missing**: no faithful active implementation exists.

### Camera, volume, sky, and exposure

| Area | Recovered | Current boundary |
| --- | --- | --- |
| Overview camera | Source-closed positions, FOV, clips, LookAt targets, centered zero-damping Composer | Transition history, shared-camera lifetime, input-driven gyroscope state, target-texture mutation, jitter and previous matrices remain live/runtime state. |
| Gyroscope | Exact Finalize callback, serialized entry offsets, input curves, centered endpoint, and recorded-input endpoint evaluator | Default off because supplied captures do not contain the cursor/controller trace or two-second transition phase. |
| Character volume | `_CharacterParams0..15` packing and actor-specific Overview modifiers | Some per-frame engine globals, visibility/irradiance data, and custom per-draw state remain absent. |
| Exposure | CharInfo selects Manual, not Auto; EV0 target and new/settled value are exactly `1` | A reused physical camera can carry a prior current value into the first frames. That history was not captured. The 16-bin histogram implementation is a valid HGRP diagnostic but is not selected by CharInfo. |
| Sky | Exact `T_hdri_006` 128x128 BC6H cubemap, tint, rotation, and effective exposure | Later compositor/target behavior remains separate. |
| Fog | Source-closed as disabled: atmosphere fog, height fog, volumetric fog, flow noise, and fog-LUT baking are all off | Do not add gray fog to imitate the reference background. The background comes from presentation assets. |

### Character material families

| Family | Running recovery | Important remaining gap |
| --- | --- | --- |
| Cloth/body `CharacterNPR` | Original Base/normal/packed/ramp contracts; linear data-map imports; packed M/S/shadow/smoothness; source-shaped diffuse/light blend; selected direct/specular carriers; back-face sign; shadow and light-list hooks | Complete variant matrix, full GGX/DFG/environment energy in one accepted path, parallax/clear coat/pantyhose/customization/dissolve/weather branches, exact additional-light population, and full downstream shadow composition. |
| Skin/face | LUT, face SDF/mask/emotion/highlight inputs; packed normal path; selected Wulfa/Zhuangfy body ForwardLit source branch; selected Default/Fog/Rim punctual rows; face/head basis publication | Only two body materials are deeply source-gated. Other skin materials and generalized nonzero rim/subsurface/weather state are incomplete. Face dark-side organization remains visibly wrong. Native texture compression/mips and all live per-draw inputs are unproven. |
| Hair | Split normal, stroke/line maps, packed shadow/smoothness, authored tangent sign, back-face behavior, two-lobe/aniso diagnostics, rain/wet carrier, outline and shadow hooks | Full original diffuse/specular/ambient energy is not closed across all hair variants. The recovered lobe diagnostic helps Wulfa but over-brightens Zhuangfy, so it is not a universal default. Secondary hair motion is not a shader feature and remains absent. |
| Eye/brow | Pseudo-spherical/parallax/matcap/highlight/scattering structure; selected overview Eye response; screen-mask R consumer; opaque alpha | Remaining selected raster tail, auxiliary motion MRT, temporal context, and broader VFX/weather variants. Eye response is source-shaped but not a whole-pipeline equivalence proof. |
| Outline | Correct `CHARACTER_OUTLINE` pass is now scheduled; original width/mask/depth inputs are represented where available | Still a compatibility shell. Original average-normal stream use, depth-aware width, exact lit NPR composition, visibility/temporal behavior, and all internal ordering are incomplete. |
| Overlay shadow | Multiplicative material, `PREDEPTH` and `OVERLAY_SHADOW` pass separation, basic stencil approximation | Exact behind-hair/eye/face shared-depth/stencil order and prevention of double-darkening are not production-closed. |

The active generated shaders are:

```text
Endfield/Recovered/CharacterCloth
Endfield/Recovered/CharacterSkin
Endfield/Recovered/CharacterHair
Endfield/Recovered/CharacterEye
Endfield/Recovered/CharacterOverlayShadow
```

The selected Wulfa/Zhuangfy source-energy work is generalized through these
shared families for all 28 actors. That is a useful breadth implementation, but
it is not equivalent to proving the bound retail variant and live resources for
each material of every actor. Current all-roster renders expose this boundary:
Last Rite still has blown-white face/effect regions and Fluorite has visibly
incorrect/banded material response.

### Lighting and shadows

| Area | Recovered | Runtime status and gap |
| --- | --- | --- |
| Main character light | Exact CharacterVolume packing, CharInfo direct-intensity carrier, direction/color/multiplier inputs | Active compatibility path; full retail global update and scene coupling remain partial. |
| Overview operator lights | All 246 records, 119 followers, native priority-descending/camera-distance ordering, 32-pixel XY plus linear-Z membership representation, selected old-CharacterNPR Default/Fog/Rim responses | Active bounded roster path. It bypasses retail `HGCullingSystem.CullLights`, the full interleaved scene/character candidate list, native equal-key ordering, and cache history. Seven source lights use behavior outside the direct supported subset. |
| Punctual soft shadow | Exact Wulfa Spot row and Zhuangfy Point row, D16 atlas layouts at 512/1024, matrices, bias, casters, optimized comparison receiver | GPU-validated diagnostic only and disabled for the general roster. Full live cache-slot population and all actors are not recovered. |
| Dedicated character shadow | Wulfa/Zhuangfy authored sphere unions, CameraVirtualLight direction, 1024 D16 tile, biases, 16-gather/64-tap receiver and correct unblocked endpoint | Single-active-character diagnostic. Retail supports 15 slots with dynamic list/index/rendering-layer scheduling and multi-actor ownership. |
| CharInfo screen shadow | Source-closed RG8 topology; neutral scene R for CharInfo; character G from PreG depth/normal/selector plus atlas; selected Skin/Cloth/Hair/Eye consumers; executed lab D3D12 bindings | Exact one-actor default-off diagnostic. Mixed visual results, retail equal-depth/DrawECS ownership, multi-actor QueryID order, and generic scene-R producers prevent promotion. |
| `ShadowPlane` | Material, multiplicative blend, bit-32 exclusion, circle fade, 15-slot atlas ABI, and VisibilitySH capsule topology are recovered | Not runtime-ready. The lab lacks canonical physical-camera bit-32 integration, full atlas scheduler, and live posed capsule records. VisibilitySH stays at its neutral zero-occlusion endpoint. |

### PreGBuffer and shared frame resources

The default-off PreGBuffer sidecar is one of the strongest isolated pipeline
recoveries:

- D32S8 depth/stencil intent with D24S8 fallback;
- R32 copied depth;
- A2B10G10R10 GBuffer A/B;
- character selector packing, family tags, Y-up oct normal, stencil low bits;
- recovered opaque queues and fixed two-sided Character PreG culling;
- exact source authored tangents and Forward/PreG fragment TBN contract.

GPU ownership audits validate 220,432/220,432 exact same-draw/same-primitive
tangent pairs with zero post-TBN world-normal mismatches or non-finite values
for the focused Wulfa frame. This closes the selected lab normal path. It does
not recover retail DrawECS query/chunk/PSO/instance order, multi-character
selector assignment, all alpha/dither/parallax variants, or the complete
shared main-attachment chronology.

The ordinary viewer does not claim that this sidecar is the retail production
GBuffer. It remains a diagnostic producer used by focused shadow validation.

### Post-processing and final composition

Recovered from original CharInfo data and compiled/native behavior:

- `ACES_modified` in AP1/ACEScg with the recovered rational curve, ODT
  desaturation, AP1-to-linear-sRGB conversion, and highlight gamut limiter;
- 1024x32 RGBAHalf grading LUT behavior;
- CharInfo saturation/shadow grade and procedural vignette;
- general scene bloom with the exact threshold/intensity/scatter transforms;
- eight-level high-quality bloom pyramid and recovered kernels;
- final OETF/dither ordering;
- Manual EV0 selection and neutral settled exposure.

The current viewer uses the recovered post path needed by the source portrait
insertion route. It is still not a proof of final retail output because live
pre-exposure history, exact intermediate/backbuffer formats, MSAA/device
fallbacks, later copy/scaler state, temporal resolve, and overlay UI are not all
present. A mathematically correct downstream curve cannot repair an incorrect
upstream light/material signal.

### Physical CharInfo presentation and portrait

The gray CharInfo scene is source-identified, not guessed fog. The original
layer-13 physical branch has five renderers:

1. `SphereOutside`;
2. `CharFloorEffect`;
3. `GeoSphere001` wall;
4. `ShadowPlane`;
5. `GridDeco/Far`.

Exact hierarchy, transforms, meshes (including essential UV1 channels),
compressed textures, material values, and selected shader evidence are
imported. The current viewer activates only the source-ready floor/wall/far-grid
subset. This subset does not alter pre-post character shading; its bright scene
contribution enters bloom/post and lifts opaque display pixels slightly.

`SphereOutside` is still fail-closed. Its selected `HGRP/Lit` HGBuffer stages,
five-MRT packing, HighEnd formats, 14 deferred resolver passes, 640 D3D11
variants, and native route topology are known. The settled resolver parameters,
bindings, subpass/load-store/stencil state, tile/per-light route, and live
lighting/shadow/indirect/history resources are not. A Standard/URP/HDRP gray
sphere would conceal this real gap and is intentionally not used.

`ShadowPlane` remains disabled for the reasons in the lighting table above.

The large hatched actor silhouette is separately source-closed as
`CharInfo/bg_charinfo_<templateId>`, loaded into the world-space layer-16
`CharTexture` Image. The exact Texture2D, Sprite rect/tight geometry, Canvas
layout, settled alpha, UI shader, raw-depth offset, and post-Uber insertion
against primary scene depth are implemented for all 28 actors. The lab
preserves full-scene D32S8 (D24S8 fallback), applies post, then draws the
standard layer-16 portrait. It does not claim the retail paired output-depth
descriptor, ECS/HGUI world-UI lists, exact equal-sort batch ordinal, or later
copy/scaler branch.

The ordinary 2D Character Info overlay UI is intentionally absent from the
lab. It should not be confused with a shader-recovery failure when comparing
whole screenshots.

## Original data versus implementation choices

No per-character camera, light, volume, portrait, exposure, or material value
was hand-tuned for the all-28 pass.

| Recovered directly from original data/code | Deliberate lab implementation or fallback |
| --- | --- |
| Playable roster/post-model identities; LOD0 meshes, skeletons, bindposes, authored tangents, materials, textures, shader names, properties, queues, and feature toggles | Unity 2022.3 compatibility import and custom SRP instead of the retail modified Unity 2021/HGRP runtime |
| All 28 Overview cameras, Composer LookAt data, volumes, portraits, light groups, and followers | Sixteen-slot dynamic light loop chosen to hold the largest recovered 13-light rig |
| Manual EV0, disabled fog, exact sky cubemap, post parameters, portrait layout, and ready physical backdrop subset | Neutral/settled exposure value `1` when no captured reused-camera history exists |
| Selected CharacterNPR equations, pass names, shadow formats, buffer packing, and post graph | Source-level HLSL ports and compatibility buffer publishers needed to run those equations in stock Unity |
| Exact Wulfa/Zhuangfy punctual and character-shadow diagnostics | Disabled for the general roster until per-actor producer contracts are recovered |
| Wulfa/Zhuangfy deeply audited source-energy variants | Generalized family implementation for the other 26 actors without per-actor retail GPU captures |
| Fifty-six original body overview clips and fourteen selected original widget clips | UI-first import scope; combat/dialog/cutscene/full-gacha animation is intentionally excluded |
| Exact selected clip samples, rates, durations, paths, and loop metadata | Roster QA samples each overview loop at time zero for deterministic breadth renders |
| Wulfa/Zhuangfy controller evidence where recovered | Other actors fall back to entry offset 0, exit at clip boundary, and zero transition instead of inventing controller timing |
| Source portrait after Uber using primary scene depth | Bounded standard MeshRenderer world-UI path without retail paired output depth or ECS/HGUI lists |
| Source-ready floor/wall/far-grid presentation | Procedural `ReferenceBackdrop` retained only as a failure fallback |

Screenshot-derived translations, actor-specific EVs, shadow strengths, and
per-material color fixes are not production parameters. They remain rejected
unless original data or a valid runtime capture proves them.

## Animation recovery status

### Current canonical scope

The project currently imports:

- 28 original CharInfo Overview entrance body clips;
- 28 original settled Overview body loops;
- 14 selected source-matched item-widget clips;
- 70 Unity legacy `.anim` assets total.

The importer uses original `AnimationClip` metadata plus decoded
ACL/QVVF `TransformBufferData`; the standard Unity/MuscleClip path is available
as fallback. It emits local position, quaternion, and scale curves only where
the decoded channel varies or differs from bind pose, preserves quaternion
continuity, loop metadata, sample rate, duration, and source binding evidence,
and binds private widget rigs by explicit paths rather than collision-prone CRC
alone.

The runtime deliberately uses Unity's legacy `Animation` component. This keeps
the imported clip surface simple and does not imply that the original Mecanim
state machine was reconstructed.

### Behavior that is represented

- The Model dropdown loads the selected actor and its clip catalog on demand.
- The viewer can search, select, restart, and reset imported clips.
- `CharacterAnimationLayerSync` can keep recovered additive/helper layers on
  the base clip's normalized clock.
- `EndfieldOverviewPlayback` supports independent item-widget animation layers,
  entry playback, loop crossfade, and evidence-driven hide-after-transition.
- A two-bone IK helper stabilizes selected lab poses and bend planes. It is a
  presentation aid, not original gameplay IK.

Wulfa has controller-proven body/widget start and loop pairing for item widget
02.

Zhuangfy has the most complete Overview controller recovery:

```text
start clip duration                  11.25 s
loop duration                         3.33333325 s
entry normalized offset               0.0058366423
exit normalized time                  0.97950697
normalized transition duration        0.05543705
transition duration                   about 0.624 s
interruption source                   2
WeaponHide                            1
MagicaClothWeight                     0.01
StaticWeaponHide                      1
```

Four original entrance-FX requests and their mount metadata are published
through an interface. No matching visual FX consumer/prefab path is active.
Widget 03 has complete private-rig bindings and a controller-proven entrance,
but its settled activation is not proven, so it is hidden after handoff.

For the other actors, exact clip data is present but most controller semantics
are not. Suffix-matched widget/body pairings are labelled `source_inferred`,
not controller-proven.

### What is still missing

| Animation area | Current gap |
| --- | --- |
| Animator graph | Full states, transition conditions, blend trees, layers, interruption/exit semantics, parameter consumers, and Lua/UI controller ownership for most actors |
| Root motion | Root-motion sidecars and scalar evidence can be preserved, but trajectory versus in-place ownership and runtime application are not defined |
| Humanoid/muscle data | Standard MuscleClip and FloatBuffer scalars are not mapped into an exact Avatar/controller policy in the canonical UI viewer |
| Facial behavior | Blendshape/morph curves, emotion indices, face material curves, lip/eye control, look-at, and facial state machines |
| Events | Animation events, visibility handlers, audio, material/VFX events, prop toggles, and timeline signals |
| Item widgets | Fourteen selected clips work, but 14 of 35 deco prefab controllers remain unresolved; FX-only/weapon/creature companions and settled lifecycle rules need separate evidence |
| CharInfo scene animation | Floor/grid one-second opened endpoints are recovered, but complete UIAnimation in/out curves and transition policy are not played |
| FX | Zhuangfy entrance requests are known but particle/trail resources and effect spawner are absent |
| Secondary dynamics | Original Magica Cloth version/manager timing, cloth/hair/ear/tail solvers, colliders, wind, initialization, and parameter bridges |
| Procedural motion | Retail grounding, interaction IK, weapon constraints, look-at, sway, camera gyroscope time history, and gameplay pose drivers |
| Broader clip scope | Combat, locomotion, dialog, cutscene, and complete gacha/team libraries are intentionally outside the current UI-first asset set |

The earlier deep Wulfa work proved that 390 ACL/QVVF clips and 25 standard
Unity/MuscleClip clips can be decoded, including private widget hierarchies.
That was useful tool validation, but the old huge cache was retired. Do not
report 415 Wulfa clips or 563 total clips as the current Unity project state.

## Honest visual gap

Direct inspection of the current Wulfa and Zhuangfy reconstructions against
the supplied retail frames gives the same conclusion as the preserved
fixed-registration diagnostics:

- camera, crop, portrait scale, and broad CharInfo layout are now close;
- Wulfa's face and white dress remain too uniformly bright and locally flat;
- Zhuangfy's face, hair, and pale/green materials lack the retail dark-side and
  highlight organization;
- hair response and internal occlusion are different, not merely noisier;
- dark hardware and layered cloth have compressed or misplaced response;
- ground/contact shadow and physical background integration are incomplete;
- shell outlines and behind-hair composition still expose compatibility
  behavior;
- the retail overlay UI is absent by design.

Historical registered material-span diagnostics varied from roughly 1.3x to
4.0x reference/candidate range depending on actor/material. Those numbers are
not a current acceptance score: pose, masks, background, and final SDR post are
confounders. They do establish that the gap is broad and material-dependent,
so a global exposure, saturation, bloom, or sharpness adjustment cannot close
it.

The all-roster success count only proves breadth and technical validity. It does
not prove that the generalized shaders are correct for every actor. Last Rite
and Fluorite are current visible counterexamples.

## Highest-value next work

### Rendering

1. Recover and implement the minimum binding-compatible `SphereOutside`
   HGBuffer plus deferred resolve path. Do not substitute a generic Lit sphere.
2. Integrate character PreG bit 32 into the real camera depth/stencil path,
   recover the full 15-slot character atlas/list schedule and live posed
   VisibilitySH capsule records, then activate `ShadowPlane`.
3. Move the validated one-actor PreG/screen-shadow branch toward a shared
   production attachment only after DrawECS/equal-depth ownership and
   multi-character QueryID ordering are proven.
4. Recover the full interleaved visible-light/cache population and finish
   per-family material carriers. Use Wulfa and Zhuangfy pose-locked A/Bs, then
   audit every actor; prioritize Last Rite and Fluorite as variant failures.
5. Recover native texture formats/mip texels and any live per-renderer weather/
   customization state before judging the last material differences.
6. Close the remaining post-Uber paired-depth/copy/scaler and overlay UI state
   only where it affects the selected shader target. DLSS/DLAA remains out of
   scope unless the user explicitly reopens temporal reconstruction.

### Animation

1. Recover the Overview Animator/state-machine route for every actor and label
   controller-proven versus inferred widget activation.
2. Map FloatBuffer/muscle/root-motion data into explicit runtime consumers,
   then import facial/morph/material curves and events.
3. Implement the original UIAnimation policy for floor/grid and exact item
   widget/FX lifecycle rules.
4. Import the proven Zhuangfy entrance effects and required mount behavior.
5. Reconstruct the matching Magica Cloth generation, solver update order,
   colliders, wind, and initialization before attempting to match secondary
   motion from video.
6. Add retail look-at/grounding/interaction IK only after deterministic clip,
   camera, and render validation is stable.

### Acceptance rules

- Every production parameter must cite original serialized data, shader/native
  behavior, or a valid runtime capture.
- Unknown values stay neutral, fail-closed, or explicitly diagnostic.
- No actor-specific screenshot fit is promoted as recovered behavior.
- Every shader change must pass at least Wulfa and Zhuangfy pose-locked A/Bs and
  the 28-character technical render sweep.
- Component recovery and whole-frame parity are reported separately.
- Build success, non-magenta output, or a closer single material never counts
  as global parity.

## Maintained workflows

Refresh installed-game WebUI-facing assets/materials when the export is stale:

```bat
cd D:\fluffy-dump
.\export_assets.bat --export-from-game --animestudio-jobs 4
```

Use debug asset export only for broad shader/AnimationClip diagnostics:

```bat
.\export_assets.bat --export-from-game --debug-assets --animestudio-jobs 4
```

Rebuild the canonical UI-first roster and viewer:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\import_playable_characters_ui.bat
.\recover_playable_charinfo_profiles.bat
.\update_character_recovery_viewer.bat
```

Render current outputs:

```bat
.\render_character_recovery_preview.bat
.\render_playable_character_previews.bat
.\render_playable_character_widget_previews.bat
```

Build/verify the fast shader scene:

```bat
.\build_fast_render_style_viewer.bat
.\verify_fast_render_style_viewer.bat
.\render_fast_render_style_preview.bat
```

The generated `Playable/<Actor>` tree is rebuildable. Durable fixes belong in
the character-import generators, Unity editor importer, runtime renderer, or
shader sources, not as manual edits to generated assets.

## Original-client observation boundary

The installed retail client uses Vulkan and includes AntiCheatExpert. The
current approved boundary is observation and offline recovery, not custom
client injection:

- installed assets, IL2CPP code, shader bytecode, settings, logs, screenshots,
  videos, caches, and external telemetry are usable;
- a signed stock profiler may be used only through its documented
  process-scoped workflow and the normal launcher/protection chain when the
  tool/service terms and protection system accept it;
- if protection blocks or terminates capture, stop;
- do not patch the client, alter protection services/drivers, register a global
  Vulkan layer, force another graphics API, manual-map a DLL, use a custom
  injector, or evade access controls.

Lab-only RenderDoc capture is already valid and useful for proving the Unity
reconstruction. It must not be confused with original-client evidence. The
retail build's dormant-looking HGRP dump classes have no recovered normal
retail trigger, so private-method hooks are not an acceptable substitute.

The highest-value future retail packet, if obtained through an accepted stock
or vendor-sanctioned path, is one settled Wulfa and one settled Zhuangfy Vulkan
frame containing the selected CharacterNPR draws, descriptors/constants,
PreG/shared depth-stencil, shadow atlases/masks, HDR inputs/outputs, and later
post/world-UI history.

## Neighboring recovery topics

Reusable exporter, shader-container, AnimationClip, Texture2D, and managed-
reference behavior lives in `animestudio_recovery.md`. Semantic model,
material, texture, animation, effect, audio, and video lookup lives in
`asset_recovery.md`. This file owns the reconstructed Unity frame and animation
behavior only.

The prior dated Unity/CharInfo/render/animation snapshots were chronological
working notes. Their durable conclusions, limitations, commands, and
acceptance rules are folded here; obsolete intermediate hashes, failed probes,
and superseded blockers are intentionally not carried forward.

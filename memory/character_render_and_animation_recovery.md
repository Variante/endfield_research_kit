# Endfield character rendering and animation recovery

This is the single current status and workflow memory for
`unity_endfield_graph_shader_lab/`. It replaces the earlier chronological
shader, CharInfo, playable-character, client-observation, and animation
snapshots.

## Current conclusion

The project is now a useful, source-backed reconstruction of Endfield's
Character Info presentation, but it is not the original renderer and it is not
visually at parity with the retail client.

The strongest result is data recovery. The source catalog and manifests now
contain all 30 concrete playable post-models, their original UI overview clips, exact material
and texture records, exact operator cameras, per-operator CharacterVolume
modifiers, portraits, and all exported overview-light groups. The current
Unity viewer and generated prefab set now contain all 30 actors. Li Zhiyan is
the `chr_0032_lizhiyan` / `Lizhiyan` source actor whose English catalog name is
`Arcane`; the viewer labels her `Arcane (Li Zhiyan)` so the identity is visible.
The existing output remains much closer to the supplied Wulfa and Zhuangfy
references than the former Standard-material viewer.

The largest remaining problem is no longer missing texture or camera data. It
is the coupled retail frame contract: exact material response across all
variants, the modified-HGRP light and shadow schedulers, the shared
depth/stencil/GBuffer path, `SphereOutside` deferred lighting, `ShadowPlane`
stencil/character-shadow/VisibilitySH inputs, live per-frame state, and final
compositor behavior. The current images remain obviously flatter and place
light and shadow differently from retail, especially on faces, pale
cloth/armor, hair, dark hardware, and ground/contact shading.

Animation recovery now covers the complete source-owned `all-ui` selection for
all 30 playable characters. The manifests contain 754 body UI clips and 321
private item/deco clips, including transform animation and recovered GameObject
visibility curves. This remains clip playback, not recovery of the complete
Animator/controller/facial/physics behavior. Endfield's 101-slot humanoid ABI
is preserved. Its six added leg degrees of freedom are inserted at Endfield
slots 28/30/31/39/41/42 rather than appended at 95-100. Exact referenced
Avatar bases are resolved for all 34 audited postmodel Animators, but muscle
transform baking remains disabled pending an original full-frame numeric
fixture. Native hierarchy propagation is now closed: all 272 TwistSolve pairs
are adjacent mapped parent/child nodes, while named twist nodes are untouched
side branches. The normal `Animator.Update` materialization edge and the
ordered eight-pair TwistSolve are recovered.

There is no honest single percentage for the whole effort. If rough
engineering ranges are useful, they should be read as scope estimates rather
than test scores:

| Layer | Current maturity | Meaning |
| --- | --- | --- |
| Static actor/CharInfo assets and serialized parameters | high, roughly 90%+ for the selected Overview scope | Most identities, payloads, transforms, textures, profiles, and selected clips are source-derived and validated. |
| Selected local CharacterNPR surface equations | medium-high, roughly 60-75% | Important cloth, skin, hair, eye, outline, shadow, and post equations are ported, but variant coverage and live inputs are incomplete. |
| Complete retail CharInfo frame behavior | partial, roughly 35-50% | Several exact diagnostic subgraphs exist, but the complete HGRP scheduling/resource contract is not active as one production path. |
| Final visual parity | not reached | Wulfa and Zhuangfy are recognizable and compositionally close, but still visibly different without close inspection. All 30 characters have not been retail-frame validated. |
| Playable UI animation clips | source recovery complete for the `all-ui` selection | 754 body clips and 321 private item/deco clips are represented across all 30 manifests and generated prefabs. The roster verifier reports all 30 animation providers present. |
| Original animation behavior | partial | All 30 main UI controller graphs are source-backed, but the legacy runtime executes only a bounded subset. The retail quality-3 world-up and root-aligned Grounding base paths and external hand-target path are source-closed; two blackboard absent-key fallbacks, shared prediction/capsule branches, facial, events, gameplay root motion, FX, secondary systems, and knee/weapon constraints remain open. |

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

The scene embeds all 30 canonical playable prefabs in one horizontal,
alphabetically ordered resident lineup. The top-left Model dropdown moves the
camera to the chosen actor and swaps the recovered CharInfo profile without
loading or destroying character models during selection.

`validate_resident_character_lineup.bat` verifies the saved scene and the
profile-switch path. The accepted run reports 30 active instances at 3.5-unit
spacing across 101.5 units; switching from the first to last alphabetical
profile moved the camera 101.677 units while preserving every instance ID.

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
| `scratch/character_recovery/character_recovery_viewer.png` | Latest resident-lineup shared-viewer Tangtang render, 1920x1080, SHA-256 `6ED269F005C9DB18DA56AFD9BB7C6EF850E7FC409C73EDBF575CFF9853DE9AF4`; no neighboring actor enters the selected camera framing. |
| `scratch/character_recovery/runtime_reference_wulfa.png` | Current 4K cumulative Wulfa reconstruction, SHA-256 `C5D035DD00730E94B7DE6D4FDA9EFC4E1DEBF832FAAB56077673D3FA998ACBC5`. |
| `scratch/character_recovery/runtime_reference_zhuangfy.png` | Current 4K cumulative Zhuangfy reconstruction, SHA-256 `FC22179F2268B33FF7A45601A6A93BD42F7249F0D215BCAB7DBFA118C0E0673C`. |
| `unity_endfield_graph_shader_lab/ReferenceCaptures/{Wulfa,Zhuangfy}/front_full.png` | Supplied retail references. They include the ordinary overlay UI and therefore are not direct character-only pixel targets. |
| `scratch/character_ui_import/renders/*.png` | 30 current 1920x1080 source-profile Overview roster renders. |
| `scratch/character_ui_import/renders/playable_character_preview_manifest.json` | Status `ok`: 30 attempted, 30 succeeded, zero failed/pending. |
| `scratch/character_ui_import/widget_renders/*.png` | Ten nonblank Overview-bound item/deco renders. |
| `scratch/character_ui_import/widget_renders/playable_item_widget_preview_manifest.json` | Status `ok`: ten succeeded, zero failed. |
| `scratch/character_recovery/roster_feature_validation/standalone_widget_renders/*.png` | Five nonblank source-owned standalone item/deco renders for actors without proven Overview binding. |
| `scratch/character_recovery/roster_feature_validation/non_overview_renders/*.png` | 28 deterministic non-overview actor renders, one per playable character. |
| `scratch/character_recovery/roster_feature_validation/{roster_feature_validation_plan.json,roster_feature_validation_matrix.md}` | Passing 28-character structural feature matrix: 28 Overview, 28 non-overview, 13 widget actors, and 28 presentation profiles. Material source-input fidelity is fail-closed: 11 complete and 17 partial. |

The latest viewer update, viewer preview, 30-character all-roster render, item-widget render,
and all-playable import logs exit batch mode with code zero and contain no
bounded C# compiler error, shader error, null reference, or unhandled exception.
The strict roster postflight additionally decodes PNG pixels and rejects blank
images; all 30 current Overview captures are nonblank. The older non-overview
and widget sweeps still cover the former 28-character roster and should be
regenerated before their counts are treated as current. This proves
build/capture health, not retail fidelity.

## Canonical source and generated coverage

### Playable roster and generated assets

- The `CharacterTable`-derived catalog has 30 rows that join to a concrete
  shipped `<charId>_postmodel` Animator, and all 30 are imported.
- `chr_9000_endmin` is an abstract selector row with no concrete post-model and
  is correctly excluded. Male and female Endministrator post-models are both
  included.
- The canonical generated root is
  `Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/<Actor>/`.
- Current generated inventory: 30 actor directories, 30 prefabs, 1,075 `.anim`
  assets, 411 path-ID-safe mesh assets, 448 materials, and 1,284 imported
  texture files.
- Seven fur meshes use a 32-bit source index buffer despite remaining below the
  usual 65,535-vertex threshold. Index width must therefore be inferred from
  original submesh byte offsets, not vertex count alone. The corrected targeted
  rebuild preserves GUIDs and the strict postflight now matches original vertex
  and submesh index counts for all 372 mesh assets and prefab references.
- Only LOD0 non-VFX body renderers are active in the character viewer. Lower
  LODs, ordinary actor VFX renderers, and shadow proxies are deliberately not
  stacked into the beauty render.
- Old duplicate generated roots `Characters/Wulfa`, `Characters/Zhuangfy`, and
  `Characters/Mifu` were removed. Their old 563-clip/roughly-29-GiB research
  cache is not the current canonical animation state.

The roster feature plan keeps nonblank structural renderability separate from
material source-input fidelity. The previous catastrophic fallback set has
been narrowed with original-data evidence:

- material PathID `7337858377406896398` resolves to canonical
  `M_eyeshadow_common_05` by its stable `_p65D54F510D76590E` suffix, even when
  the hash-derived map name differs. Ardelia, Bounda, Camille, Last Rite,
  Lifeng, and Zhuang Fangyi now retain the original OverlayShadow shader,
  `T_actor_common_eyeshadow_01_M`, blue-gray tint, and authored float values;
- Last Rite's large `S_actor_lastrite_skill_01_lod0` shell is an authored
  `VFXTransparentDepthOnly` auxiliary renderer. It remains in the manifest as
  evidence but is hidden by default instead of becoming opaque white;
- Zhuang Fangyi widget 03 uses `DefaultHGMaterial`, a runtime-controlled
  placeholder. It is hidden by default until its runtime material override is
  recovered rather than rendered through Standard;
- unknown material records now fail closed through the no-color unavailable
  shader, preventing new missing records from silently becoming white models.

The bounded all-roster feature/material coverage audit should be regenerated;
older fallback and texture-loss counts are no longer current. The current
strict mesh audit does cover all 30 prefabs and reports 411 generated mesh
assets, zero pending assets, and zero asset errors.

### Per-character CharInfo profile coverage

The source-profile extractor has complete records for all 30 playable actors:

- 30 authored Overview cameras, including position, FOV, clip planes, LookAt,
  and neutral centered Composer behavior;
- 30 portrait textures, Sprite geometry records, and authored overview image
  offsets;
- 30 actor-specific `HGCharacterVolume` modifiers;
- 30 overview additional-light groups containing 266 enabled lights;
- 133 enabled `CharInfoLightFollower` records;
- maximum source rig size 13 lights for Aglina.

The current serialized TypeTree cannot fully decode the managed-reference
`CharacterDisplayData` registry. The maintained recovery workflow therefore
performs a bounded raw-sidecar export of only `CharacterDisplayConfig`, then
reads each record's exact aligned camera/light strings, height enum, and
overview-offset floats. This byte-backed path reproduced all 28 previously
known profiles and recovered the missing Li Zhiyan and Camille records without
inventing camera or light names.

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
- The canonical `all-ui` scope imports 204 owner-qualified private item/deco clips.
  The generated set includes 202 transform clips plus two
  Pelica `GameObject.m_IsActive` visibility clips; all admitted bindings resolve
  to exact shipped private hierarchies.
- Exact deco-controller ownership is known for the imported families, but name
  or suffix association alone is not proof that the retail controller activates
  a clip in a particular state. Sixteen external-camera selections and ten
  external-container selections remain deliberately outside actor animation
  import; semantically, 25 are camera-like and one is the Endminf external
  effect/model-rig clip.
- Deterministic Overview render validation currently covers the ten actors with
  source-bound item-widget entry compositions. Chen and Aurora have exact prefab
  assets but zero selected widget clips; the remaining controller-unavailable or
  standalone families stay selectable as source evidence rather than being
  presented as proven Overview activation. Standalone sampling proves the
  recovered clip/prefab/material path, not retail activation
  timing.

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
5. The optional `tools/RuriRipperImporter` checkout supplies a second decoder
   for Unity Force-Text YAML, GUID-linked materials, interleaved mesh streams,
   bind-pose reconstruction, Hermite curves, and Avatar muscle referentials.
   It is a cross-check and Blender bridge, not a replacement for original
   AnimeStudio shader bytecode or installed native code. Its current humanoid
   solver models stock Unity's 95 muscles, assigns toe Up-Down to the wrong
   Endfield selector, and clamps muscle inputs without binary proof; it must
   not govern Endfield recovery unchanged.
6. FractalMiner's readable HGRP reconstruction supplies semantic names and
   equations where it agrees with original bytecode; its explicitly removed
   features are never treated as proof of absence in retail.
7. Installed IL2CPP metadata/native code supplies publisher/update/scheduling
   behavior and enum semantics.
8. The original NVIDIA Vulkan PSO cache corroborates compiled shader families;
   it is not an execution timeline and cannot select a live branch.
9. RenderDoc captures of the standalone Unity lab validate the reconstructed
   D3D12 bindings, formats, passes, and draws. They are not captures of retail.
10. Supplied lossless screenshots and videos validate presentation, recurrence,
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
| Cloth/body `CharacterNPR` | Original Base/normal/packed/ramp contracts; linear data-map imports; packed M/S/shadow/smoothness; source-shaped diffuse/light blend; selected direct/specular carriers; back-face sign; shadow and light-list hooks; `_ParallaxMarchNum` refinement; source-proven Repeat/Bilinear/aniso-1 sampling for `_ParallaxTex` | Complete variant matrix, full GGX/DFG/environment energy in one accepted path, clear coat/pantyhose/customization/dissolve/weather branches, exact additional-light population, and full downstream shadow composition. |
| Skin/face | LUT, face SDF/mask/emotion/highlight inputs; packed normal path; selected Wulfa/Zhuangfy body ForwardLit source branch; selected Default/Fog/Rim punctual rows; face/head basis publication | Only two body materials are deeply source-gated. Other skin materials and generalized nonzero rim/subsurface/weather state are incomplete. Face dark-side organization remains visibly wrong. Native texture compression/mips and all live per-draw inputs are unproven. |
| Hair | Split normal, stroke/line maps, packed shadow/smoothness, authored tangent sign, back-face behavior, two-lobe/aniso diagnostics, rain/wet carrier, outline and shadow hooks | Full original diffuse/specular/ambient energy is not closed across all hair variants. The recovered lobe diagnostic helps Wulfa but over-brightens Zhuangfy, so it is not a universal default. Secondary hair motion is not a shader feature and remains absent. |
| Eye/brow | Pseudo-spherical/parallax/matcap/highlight/scattering structure; selected overview Eye response; screen-mask R consumer; opaque alpha | Remaining selected raster tail, auxiliary motion MRT, temporal context, and broader VFX/weather variants. Eye response is source-shaped but not a whole-pipeline equivalence proof. |
| Outline | Correct `CHARACTER_OUTLINE` pass is now scheduled; original width/mask/depth inputs are represented where available | Still a compatibility shell. Original average-normal stream use, depth-aware width, exact lit NPR composition, visibility/temporal behavior, and all internal ordering are incomplete. |
| Overlay shadow | Multiplicative material; `PREDEPTH` and `OVERLAY_SHADOW` pass separation; exact shipped `Ref [_ShadowOverIris]`, read-mask 20, equal comparison, keep-only stencil state; source material refs 4/20; `DISABLE_DRAW_UNDER_HAIR` material keyword binding; source eye-mask Bilinear/aniso-1 import | Shared-depth/screen attachment ownership, the non-keyword hair-shadow screen-mask branch, clustered-light/atmosphere modulation, complete behind-hair/eye/face chronology, and prevention of all double-darkening are not production-closed. |

The active generated shaders are:

```text
Endfield/Recovered/CharacterCloth
Endfield/Recovered/CharacterSkin
Endfield/Recovered/CharacterHair
Endfield/Recovered/CharacterEye
Endfield/Recovered/CharacterOverlayShadow
```

The selected Wulfa/Zhuangfy source-energy work is generalized through these
shared families for all 30 actors. That is a useful breadth implementation, but
it is not equivalent to proving the bound retail variant and live resources for
each material of every actor. The current all-roster postflight confirms that
Last Rite's former opaque-white depth shell and Zhuang Fangyi's white runtime-
placeholder ribbons are absent. Remaining family-level response differences
are therefore shader/light/compositor gaps rather than those two fallback
geometries. Camille's current Overview render is still strongly red and
overexposed, which remains an explicit lighting/material-variant counterexample.

### Lighting and shadows

| Area | Recovered | Runtime status and gap |
| --- | --- | --- |
| Main character light | Exact CharacterVolume packing, CharInfo direct-intensity carrier, direction/color/multiplier inputs | Active compatibility path; full retail global update and scene coupling remain partial. |
| Overview operator lights | All 266 records, 133 followers, native priority-descending/camera-distance ordering, 32-pixel XY plus linear-Z membership representation, selected old-CharacterNPR Default/Fog/Rim responses | Active bounded roster path for 259 records. It bypasses retail `HGCullingSystem.CullLights`, the full interleaved scene/character candidate list, native equal-key ordering, and cache history. Seven positive-linear-length source lights remain unsupported. |
| Punctual soft shadow | Exact Wulfa Spot row and Zhuangfy Point row, D16 atlas layouts at 512/1024, matrices, bias, casters, optimized comparison receiver | Two default-off exact diagnostic rows out of 32 shadowed source rows across 23 actors. Full live cache-slot population and the other 30 rows are not recovered. |
| Dedicated character shadow | Wulfa/Zhuangfy authored sphere unions, CameraVirtualLight direction, 1024 D16 tile, biases, 16-gather/64-tap receiver and correct unblocked endpoint | Two sphere-bound profiles out of 30; single-active-character diagnostic only. Retail supports 15 slots with dynamic list/index/rendering-layer scheduling and multi-actor ownership. |
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
against primary scene depth are implemented for all 30 actors. The lab
preserves full-scene D32S8 (D24S8 fallback), applies post, then draws the
standard layer-16 portrait. It does not claim the retail paired output-depth
descriptor, ECS/HGUI world-UI lists, exact equal-sort batch ordinal, or later
copy/scaler branch.

The ordinary 2D Character Info overlay UI is intentionally absent from the
lab. It should not be confused with a shader-recovery failure when comparing
whole screenshots.

## Original data versus implementation choices

No per-character camera, light, volume, portrait, exposure, or material value
was hand-tuned for the all-30 pass.

| Recovered directly from original data/code | Deliberate lab implementation or fallback |
| --- | --- |
| Playable roster/post-model identities; LOD0 meshes, skeletons, bindposes, authored tangents, materials, textures, shader names, properties, queues, and feature toggles | Unity 2022.3 compatibility import and custom SRP instead of the retail modified Unity 2021/HGRP runtime |
| All 30 Overview cameras, Composer LookAt data, volumes, portraits, light groups, and followers | Sixteen-slot dynamic light loop chosen to hold the largest recovered 13-light rig |
| Manual EV0, disabled fog, exact sky cubemap, post parameters, portrait layout, and ready physical backdrop subset | Neutral/settled exposure value `1` when no captured reused-camera history exists |
| Selected CharacterNPR equations, pass names, shadow formats, buffer packing, and post graph | Source-level HLSL ports and compatibility buffer publishers needed to run those equations in stock Unity |
| Exact Wulfa/Zhuangfy punctual and character-shadow diagnostics | Disabled for the general roster until per-actor producer contracts are recovered |
| Wulfa/Zhuangfy deeply audited source-energy variants | Generalized family implementation for the other 28 actors without per-actor retail GPU captures |
| 754 original body UI clips and 321 owner-qualified item/deco clips across all 30 actors | UI-first import scope; combat/dialog/cutscene and non-actor external camera/effect animation remain intentionally excluded |
| Exact selected clip samples, rates, durations, paths, and loop metadata | Roster QA samples each overview loop at time zero for deterministic breadth renders |
| All 30 shipped main UI AnimatorControllers, including their 40-state graphs, 31 transitions, Overview entrance selectors, and start-to-idle timing | The legacy viewer does not yet reproduce the complete parameter-driven menu graph, interruption policy, events, or every state-to-state transition |
| Source portrait after Uber using primary scene depth | Bounded standard MeshRenderer world-UI path without retail paired output depth or ECS/HGUI lists |
| Source-ready floor/wall/far-grid presentation | Procedural `ReferenceBackdrop` retained only as a failure fallback |

Screenshot-derived translations, actor-specific EVs, shadow strengths, and
per-material color fixes are not production parameters. They remain rejected
unless original data or a valid runtime capture proves them.

## Animation recovery status

### Current canonical scope

The canonical catalog now uses `clip_scope=all-ui` for all 30 playable actors:

- 754 original actor-owned body UI clips;
- 321 owner-qualified private item/deco runtime clips, including distinct copies
  where one shipped controller clip is shared by multiple private prop owners;
- 1,075 generated Unity legacy `.anim` assets;
- at least one deterministic non-overview clip for every actor, in addition to
  the original Overview entrance and settled-loop coverage.

The Wulfa subset contains 42 clips: 25 body and 17 companion clips.
Exact deco-controller ownership joins apple-01 to `chr_0028_wulfa_deco_1` and
apple-02 to `chr_0028_wulfa_deco_3`; every imported apple curve binds its
private shipped hierarchy. The suffix pairing identifies source-owned states,
and the exact private controllers prove that the three Overview entrance props
hand off to their respective disappear clips; FX lifecycle remains separate.
The two apple prefabs each ship four meshes with the same authored names but
different Mesh path IDs, vertex buffers, and submesh layouts. Generated Unity
mesh assets must therefore use the source path ID in their asset basename;
name-only caching aliases the two rigs and produces hybrid geometry. The same
identity audit also finds a body/private-deco collision for Wulfgard's
`S_actor_wolfgd_cloth_05_lod0`. Across the 30 current manifests there are five
distinct authored-name collision groups: four Wulfa apple names and one
Wulfgard cloth name. The roster verifier enforces source-unique asset names for
all five and validates exact private-deco hierarchy, animation-binding,
state-visibility, and Overview widget paths before Unity postflight. The
current source audit covers 436 LOD0 renderers backed by 411 distinct Mesh path
IDs, including 98 private-deco skinned meshes and two private-deco static
meshes.

The importer uses original `AnimationClip` metadata plus decoded
ACL/QVVF `TransformBufferData`; the standard Unity/MuscleClip path is available
as fallback. It emits local position, quaternion, and scale curves only where
the decoded channel varies or differs from bind pose, preserves quaternion
continuity, loop metadata, sample rate, duration, and source binding evidence,
and binds private widget rigs by explicit paths rather than collision-prone CRC
alone.

Endfield's serialized humanoid ABI is now preserved explicitly rather than
treated as stock Unity. `m_IndexArray` uses the observed 206-entry layout: 42
motion/root/limb-IK attributes, the 101-muscle range, then reserved/padded
entries. The installed `UnityPlayer.dll` proves that the six additions are
inserted into the leg ranges: Endfield slots 28/30/31 are `Left Foot Twist
Roll`, `Left Toes Left-Right`, and `Left Toes Twist Roll`; slots 39/41/42 are
their right-side equivalents. Their serialized attributes are therefore
70/72/73/81/83/84. Every later stock arm/finger semantic is shifted by three or
six Endfield slots, so treating 95-100 as the extensions mislabels stock finger
channels. Both the standard MuscleClip sampler and ACL sample sidecars retain
the Endfield ordering and propagate it into generated clip manifests. Names,
bone ownership, selector ordering, default limits, and exact Avatar
referentials are closed. GetZYRoll's muscle-to-angle scaling and angle range
reduction are now instruction-closed: it selects lower/upper limits by muscle
sign, extrapolates over-range values without an internal `[-1,1]` clamp, applies
the Avatar sign bit to the tangent lane, reduces modulo `2*pi`, and clamps only
the half-angle near `pi/2`. `SetInternalHumanPose`, the 101-slot production
gather at `0xB25830/0xB25910`, and the `0xB38B10 -> 0xB34260` conversion chain
also preserve raw values without a stock clamp; an individual curve producer
could still constrain its own values earlier.
The maintained sampler exposes the complete per-bone muscle-to-Avatar-local
stage but does not apply it as a final pose. `HumanPoseHandler.SetInternalHumanPose`
stages the modified 61-body-plus-40-finger layout and calls shared pose-to-
skeleton core RVA `0xB314D0`; three additional native callers prove this is not
managed-only. Conditional helper `0xB31D10` is now source-closed as the
translation-DoF position stage, not TwistSolve: it iterates every non-Hips core
bone, consumes 21 positional records, and writes only position. All 33 unique
playable Avatars disable translation DoF, so this path is inactive. The
additional callers are now bounded: `AnimationClip.SampleAnimation` worker
`0xA5AD60`, lazy AnimationStream materializer `0xAAB6E0`, and subordinate
humanoid apply/reset stage `0xB13620`. The normal `Animator.Update` path is now
closed from thunk `0x177AB0` through scheduler `0xA64610`, callback `0xA5AD10`,
`0xB13620`, and `0xB314D0`, with a separate ordered post-pass through
`0xB13240 -> 0xB323F0`. `0xB17DB0` is not TwistSolve; it rebuilds the two
foot-goal/IK groups after pose conversion. Real TwistSolve is `0xB323F0`, which
calls `0xB27930` for eight ordered arm/leg parent-child pairs. The worker scales
only parent selector 0 by the Avatar factor, reconstructs the parent, then
compensates the child so the child world orientation is preserved. The exact
compact-to-physical map is now closed: all 272 pair observations are adjacent,
and `0xB06170 -> 0xB33BD0` copies only the mapped parent/child TRS records.
Named twist bones are direct side branches whose generic local curves remain
untouched. All 33 exact playable Avatars use
`(Arm, ForeArm, UpperLeg, Leg) = (1, 0, 1, 0)`.

#### Native animation implementation recovery

Expert-supplied reverse-engineering evidence narrowed three open runtime
questions into concrete leads. Static binary/data analysis has now closed part
of each lead while preserving the remaining implementation boundary:

| Lead | Current evidence | What must still be proved before implementation |
| --- | --- | --- |
| Six extra leg muscles | Source-closed for names, order, bone ownership, selector order, limits/sign, per-Avatar referential, GetZYRoll scaling/range reduction, native 101-slot production, the normal `Animator.Update` materialization edge, and TwistSolve pair order/semantics. The current `UnityPlayer.dll` SHA-256 is `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`. All 34 exact postmodel Animator -> Avatar references resolve. For each affected bone, `Qlocal = preQ * Qaxes * inverse(postQ)` matches serialized rest within `8.01e-6` degrees. The `0xB25830/0xB25910` production table includes all six fork slots and passes raw floats into `0xB38B10 -> 0xB34260` without a stock clamp. Normal Update reaches `0xB314D0`, the separate foot-goal rebuild `0xB17DB0`, then `0xB13240 -> 0xB323F0`. TwistSolve performs eight ordered `0xB27930` corrections; all playable Avatars use factors `(1,0,1,0)`. All 272 audited pairs are adjacent in compact and mapped physical skeletons; only mapped parent/child TRS records are copied, while named twist side branches preserve their local curves. | Build an original full-frame numeric fixture and validate the complete pose bake, generic-curve coexistence, and clip-write order. Native tangent normalization remains semantic rather than bit-identical, individual clip producers may still constrain their own values, and current all-UI standard samples do not exercise the six extensions. |
| Explicit baked IK targets | Exact Grounder exports now cover all 30 current actors and prove PPtr equality from `IK_Foot_L/R_001` to `GrounderBipedIK.solver.IKFootBoneL/R`. The maintained profile builder embeds every exact tuning block, binding, mode, and hash into the actor manifest and a 30-profile catalog. These are sampled authored foot references consumed by Grounding, not serialized BipedIK limb targets. `CharacterAnimationBlackboard._UpdateFootIK` at RVA `0x3413830` requests `FOOT_IK_WEIGHT`, `FOOT_IK_FOOT_WEIGHT`, and `FOOT_IK_ADSORB_WEIGHT`; the bridge at RVA `0x326CF60` copies the processed block into Grounding. Across 754 unique current UI clips, only `FootIKWeight` hash `0x2B797234` is authored: 23 exact 60 Hz ACL scalar arrays, all track 15 and constant one. The other two hashes occur in zero clips, so their absent-key fallback remains unproven. Quality-3 world-up and Chen/Li root-aligned base paths are source-closed; shared prediction/capsule branches remain open. Hand targets enter separately from `CharLimbIKAction` exData offsets `+0x48/+0x50`; sampled bend goals are null. | Do not implement Grounding until the two absent-key fallback/default owners, terrain query ownership/layer mapping, live controller state, C# runtime consumption of the recovered profile, a pelvis-aware foot-only solver surface, callback order, and numeric original-frame fixtures are present. Separately recover other quality modes, `overstepFallsDown == false`, full prediction, exact capsule no-hit branches, the dynamic hand exData producer, and any knee/weapon consumer. Distance-derived activation remains unsupported. |
| Separated Motion/Root semantics | `MotionT/MotionQ` is character-object trajectory in clip space; `RootT/RootQ` is the absolute skeleton body reference in that same space, never a Motion-relative object delta. Character Info is source-closed: `CharUIModelMono._OnAnimatorMove` at RVA `0x6C2ABD0` applies only `worldQ = normalize(worldQ * animator.deltaRotation)` and never reads translation. Gameplay stores evaluated Animator deltas in `RootMotionData`. Its divisor producer is now closed at RVA `0x343D002..0x343D038`; `_OnAnimatorMove` accumulates only above weight `1e-5`, distinct from the `1e-4` `hasRootMotion` accessor. Translation is yaw-warped and routed through `VelocityMixer` and the movement motor. | Higher-level divisor semantics, exact controller transition/interruption quaternion blending, cycle accumulation, multi-modifier aggregation, movement/collision/cliff gates, and final motor application. Gameplay GameObject root motion and generic `Animator.applyRootMotion` remain disabled. |

Reproducible source-only audit artifacts are grouped under
`scratch/character_recovery/humanoid_avatar_basis/` (including
`get_zyroll_scaling.md`, `b17db0_twist_and_clamp.md`, and
`animator_update_scheduler_findings.md`),
`scratch/character_recovery/ik_target_binding/`, and
`scratch/character_recovery/root_motion_policy/`. They are investigation
evidence; this topic document remains the durable conclusion and recovery
queue.

The recovered implementation boundary is divided along those three
boundaries: the 101-slot native ABI, the baked-IK runtime consumer, and the
Motion/Root application path. Offline binary/data inspection is allowed;
client injection, patching, protection changes, or execution hooks are not.

The runtime deliberately uses Unity's legacy `Animation` component. This keeps
the imported clip surface simple and does not imply that the original Mecanim
state machine was reconstructed.

Legacy `Animation.Stop()` does not restore channels omitted by the next clip.
This matters when a dense standard MuscleClip is followed by a sparse ACL clip:
before the fix, Wulfa's team-idle-to-overview switch retained 290 stale local
channels, including paw/tail rotations near 178 degrees. Generated prefabs now
capture their complete local reference pose during `Awake`; manual base-clip
selection stops the old state, restores that immutable pose, then samples the
new clip. Manual selection also cancels the delayed automatic Overview handoff,
while initial model loading preserves the recovered Overview entrance owner.
The Wulfa validator compares dense-to-sparse switching with a fresh ACL sample
transform-for-transform rather than treating finite curves as sufficient.

The roster audit proves that this is not Wulfa-specific. Of 18,208 ordered
body-clip transitions, 18,056 can inherit at least one channel from the prior
clip unless the reference pose owns the switch. The 25 standard MuscleClip
fallbacks now use compact sampler binding indices rather than source array
indices assigned before unmatched paths were removed; all current manifests
validate with zero mapping mismatches and zero out-of-range tracks. Automatic
Overview start-to-loop handoffs also receive constant reference curves for
channels written only by the start clip. The current catalog has 43 such
handoff pairs, including 14 whose loop name ends directly in
`_overview_loop`.

The all-roster Unity runtime validator passes 30 actors and all 754 body clips.
It exercised 752 contaminated source-to-target probes, prevented 71,434 stale
transform values, and reported zero post-reset mismatches. It also passed 30
Overview ownership checks and all 43 start-to-loop handoffs. The canonical
visual postflight passes 30/30 body previews. The older 10/10 source-bound
Overview widget preview remains valid for its bounded roster; Wulfa's widget
preview samples both apple entrance clips on
their exact private deco roots plus the controller-proven widget-02 entrance.

### Behavior that is represented

- The Model dropdown loads the selected actor and its clip catalog on demand.
- The viewer can search, select, restart, and reset imported clips.
- `CharacterAnimationLayerSync` can keep recovered additive/helper layers on
  the base clip's normalized clock.
- `EndfieldOverviewPlayback` supports independent item-widget animation layers,
  entry playback, loop crossfade, and evidence-driven hide-after-transition.
- Manual viewer playback now adopts the matching recovered composition even
  when a body clip is chosen from the ordinary clip list, then recomputes the
  exact private-prop renderer set from the active body clip, helper, and
  recovered controller layers after Sample/Play ownership on every Play,
  Restart, state-transition entry, and loop handoff. Prop roots and renderer
  objects are reactivated with the renderer itself. This closes the bug where
  an item hidden by its prior lifecycle appeared only on the first playback.
- The viewer derives state-connection buttons only from an exact imported
  `_ui_<from>_to_<to>` body clip plus an exact destination loop, plays the
  transition once, and then owns the destination loop. The current 30-character
  catalog preserves these evidence-backed connections; Da Pan has nine, including paired
  Overview/Weapon, Overview/Equip, Overview/Skill, and Overview/Upgrade routes
  plus Idle -> Relax. Missing transition or loop clips remain absent rather
  than being inferred.
- `validate_character_viewer_state_items.bat` validates the generated assets in
  Unity. The accepted run forcibly disabled every Wulfa recovered renderer
  object twice and recovered all three Overview prop families on both passes;
  it also proved that each of Da Pan's nine visible buttons resolves both its
  transition and destination-loop `AnimationState`.
- A two-bone IK helper remains available as an explicitly enabled `Lab IK`
  diagnostic. It defaults off and no longer overwrites authored clip motion.

The refreshed dedicated IK evidence catalog covers all 30 characters and 1,075
generated UI body/item clips. Of those, 756 contain complete bilateral hand
targets, foot targets, knee targets, and weapon targets; 776 contain bilateral
deforming-hand curves. Every partial or unilateral count is zero. The catalog
now separates proven retail foot-reference binding and the one available
authored UI foot-weight curve family from the two absent runtime keys and the
still-unproven overall/non-foot solver policy. The refreshed
catalog-driven Unity verifier passes all 30 actors and
1,075 clips, including 30 fail-closed pose checks proving that disabled IK
evaluation does not modify the pose. It also parses all 23 exact
`FootIKWeight` arrays, verifies every sample remains one at 60 Hz/track 15,
requires zero bindings for the other two requested keys, and rejects promotion
of the incomplete three-value source. The resident lineup revalidates all 30
active instances at 3.5-unit spacing without runtime model loads. The full
roster switch sweep validates all 754 body clips and 43 Overview start-to-loop
handoffs, prevents 71,434 stale-transform contaminations, and reports zero
post-reset mismatches. The earlier Chen
Qianyu and Da Pan hand artifacts came from applying the lab's guessed late
two-bone solve at 0.65 weight, 0.35 hand-rotation weight, and no source arm pole
on top of authored curves. The solver is now fail-closed and defaults off.

The retail foot path is no longer an inference from transform names. Exact
Grounder components for all 30 current actors serialize PPtr equality between
`IK_Foot_L/R_001` and `GrounderBipedIK.solver.IKFootBoneL/R`.
`GrounderBipedIK.OnSolverUpdate` runs
Grounding before writing both leg solver states. Its three foot-related runtime
values are requested from the animation blackboard, not derived by the lab/Ruri
target-distance heuristic. Only `FootIKWeight` is present in current UI clip
data: 23 exact 60 Hz ACL curves, all constant one. `FootIKFootWeight` and
`FootIKAdsorbWeight` occur in zero of 754 unique UI clips, so their missing-key
fallback/default ownership remains open. Conversely, retail hand IK accepts explicit
external interaction targets, sampled knee bend goals are null, and no weapon
consumer has been recovered. Authored hand/knee/weapon marker curves therefore
remain preserved but do not activate the lab solver.

Da Pan's original postmodel does contain an exact enabled FinalIK-style
`BipedIK` component (MonoBehaviour PathID `4783797638219936524`) with
`fixTransforms=1`, complete `BipedReferences`, four `IKSolverLimb` chains, and
the three-bone hand references UpperArm -> Forearm -> Hand at per-bone weight
`1`. The serialized left/right hand bend normals are respectively
`[-0.011747229, 0.021824287, 0.002246252]` and
`[-0.01174728, -0.021824459, -0.0022459808]`; both use bend modifier `0`, bend
modifier weight `1`, and maintain-rotation weight `0`. An adjacent enabled
Grounder component (PathID `6557541568967848716`) references that exact BipedIK
plus the authored bilateral IK-foot bones and first spine reference. This
closes component identity and reference-chain recovery, but not activation:
the serialized hand IK position/rotation weights are all `0`, targets and bend
goals are null, the main/private UI controller layers have `m_IKPass=false`
and `m_IKOnFeet=false`, and their decoded behaviours contain no IK bridge.
The former 28-character targeted component export closes the serialized side of
that bounded audit: all 28 audited playable postmodels contain one enabled root `BipedIK`
and an exact linked Grounder (Laevat also has a second enabled `BipedIK` on
`Bip001`). Across all 29 BipedIK instances every limb position/rotation weight
is `0`, every limb target and bend goal is null, per-bone weights are `1`, bend
modifier is `0`, bend-modifier weight is `1`, and maintain-rotation weight is
`0`. Chen Qianyu therefore matches Da Pan rather than providing a nonzero UI
activation example. The installed managed/native audit also separates the
systems: `CharUIModelMono`, the 33-field/55-method UI model/deco owner, has no
BipedIK target/weight member and no native direct-call edge to RootMotion IK.
`CharPerformHandleBase` does expose `charIKRoot`, targets, and
`m_useCharIKTargets`, but belongs to the separate world/cinematic
CharInteractPerform timeline/action subsystem; no source edge connects it to
Overview playback. The only CharUI native target edges recovered are its own
deco unload and curve-driven visibility updates. See
`reports/assets/character_ik_activation_audit.json`. The original solver
therefore remains evidence-only and fail-closed rather than being enabled with
guessed Overview weights.

The exact Grounder profile audit now covers all 30 actors. Every profile uses
quality 3, `overstepFallsDown=1`, `footAdsorbWeight=1`, and prediction 0.
Twenty-eight select the non-rotated family. Chen Qianyu and Li Zhiyan use
`rotateSolver=1`, `footRadius=0.2`, and `footRotationSpeed=2`; their
root-aligned base path is now source-closed too. The registered field table
places `rotateSolver` at `Grounding+0x9C`; `+0x3D` is `isAccelerating`.
Rotated root/foot queries use `root.up`, forward/right use the root frame,
vertical comparisons use inverse-root local Y, and pelvis composition uses
`root.up*heightOffset + root.forward*forwardOffset`. These blocks rejoin the
ordinary `FinalSetIKPosition` and `SetLegIK` stages. Camille uses the ordinary
family. Whiten's overall Grounder weight is `0.348`. Da Pan and Deepfin keep a
zero layer mask, which must remain a no-hit/synthetic-fallback case rather than
being replaced with Unity's default/all-layer query. Runtime Grounding remains
disabled because only the available `FootIKWeight` arrays are imported into an
evidence catalog while the other two blackboard values have no recovered
absent-key fallback, and because the lab does not own queryable terrain/layer
mapping, carry the live controller state,
consume the recovered profile in a dedicated C# runtime, expose the retail
pelvis-aware foot-only solver surface, or have numeric original-frame fixtures.
The exact serialized blocks are now normalized into all 30 actor manifests and
`playable_character_grounder_profiles.json`; the catalog resolves bilateral
foot names for all 30 and records zero runtime-enabled profiles.

Wulfa's private Overview controllers prove start-to-disappear handoffs for both
apple props and widget 02. The older suffix-paired widget-02 loop is retained as
selectable source evidence but is not the settled Overview state.

Da Pan's main and private-deco controllers share the same 40-state topology.
`Overview.FromOveview` pairs the 8.4333334-second body entrance with
`widget_dapan_01_ui_overview_01`, then exits at normalized time `0.95146173`
with normalized duration `0.051952947` and interruption source `2`.
`Overview.OverviewIdle` and every other imported deco state use
`widget_dapan_01_ui_displayoff_01`; leaving the entrance noodle/bowl state
clamped after the body settled was therefore wrong. The runtime binding now
supports a controller-proven post-transition clip instead of guessing a hide.

Da Pan's first long dark obstruction in the deterministic widget preview did
include the embedded body claymore renderer `S_actor_dapan_cloth_02_lod0`, whose
original SkinnedMeshRenderer is rooted at `Root/.../wepon_joint`; the source
controller publishes `WeaponHide=1` during Overview. The batch widget preview
now explicitly applies that recovered parameter after direct clip sampling and
fails if the source-hidden renderer remains enabled. A second exclusion audit
proved that the remaining long sheets/rods came from dynamic deformation inside
the legitimate 68-bone `S_actor_dapan_cloth_01_lod0`, not from an additional
renderer that could safely be hidden. The floating glass is also an authored
cloth-01 vertex group: 1,253 vertices are weighted entirely to `glass_joint`,
which the entrance clip deliberately moves. After correcting ACL track order,
the representative preview sampler chooses the first continuous interval where
the source-bound widget family is finite and overlaps the body. The current Da
Pan sample is normalized time `0.49308300018310547` (`4.1583333` seconds), with
`S_widget_dapan_03_lod0` as the overlap witness. All four widget renderers are
enabled and active before diagnostic isolation; their animated roots, bounds,
and scale determine visible participation (`widget_01` and `widget_02` scale
`0.692`, `widget_03` scale `1`, and `widget_04` scale `0.001`). Diagnostics now
snapshot that source state before isolating renderers and restore it around
every capture, avoiding the earlier false report that only widget 01 was
enabled.

The dynamic deformation root cause is the ACL transform-track binding order.
The importer formerly assigned QVVF tracks by the first occurrence of each
Transform path across generic bindings. Endfield groups those bindings by
channel; when position omits a rotation-only bone this puts the omitted path at
the end and shifts every later ACL track. Da Pan's Overview entrance has 265
output tracks but only 263 position paths and 265 rotation paths. The bad map
therefore first diverges at track 43 and remains shifted across 222 later paths:
for example the track labeled `wep_M` carried `collarRt01_joint` values, the one
labeled `Belly02_joint` carried `wep_M`, the one labeled `towel_01_joint` carried
`cup_03_joint`, and the one labeled `towel_03_joint` carried `towel_01_joint`.
This also explains why bind/rest previews could look correct while animated
limbs and accessories twisted. The parser now selects a source binding-channel
order only when its unique path count exactly equals ACL `OutputTrackCount`,
requires every complete candidate channel to agree, prefers rotation then
position then scale, records the ordering evidence, and fails closed when no
unambiguous complete order exists. The source-only report at
`reports/assets/character_acl_track_order_audit.json` covers all 817 manifested
ACL clips: every clip has an unambiguous complete channel order. The audit
identified 53 previously stale manifests across 18 actors, including all ten
affected Da Pan clips and two recovered item/widget clips; the canonical
all-roster rebuild regenerated them, and the current postflight reports zero
manifest/order mismatches. Rotation is complete for all but
Lifeng's dragon widget, whose position run is the sole complete order. Da Pan's
four food meshes and the
cloth-01 skin stream independently match source bind poses, ordered bones,
indices, and weights, so those were not rewritten. The controller also proves
nine entrance-effect requests, but their effect assets/spawner remain a separate
visual-recovery gap.

The roster-wide serialized binding audit at
`reports/assets/character_item_renderer_binding_audit.json` extends that Da Pan
check to all 80 recovered item/deco SkinnedMeshRenderers. Every ordered bone
array and root bone matches its original owner-qualified hierarchy path and
source Transform path ID through the generated prefab; none resolve into the
body skeleton or another deco owner. Thirty-nine renderers have at least one
same-named transform outside their owner, so global name/CRC fallback is unsafe
even though the current generated references are exact. The setup importer now
fails closed on owner-escaping or unresolved recovered-prop bones/root bones and
never fills a partial explicit path list from the global CRC map. This audit
proves binding identity only; it does not prove decoded pose values, visibility
behavior, IK, or the rendered result.

The companion body report at
`reports/assets/character_body_renderer_binding_audit.json` validates all 310
selected LOD0 body SkinnedMeshRenderers across the former 28-actor scope against the same
source-to-prefab chain. Da Pan `S_actor_dapan_cloth_01_lod0` retains its exact
68 ordered source bone Transform path IDs, 68 bind poses, and original root
bone in the generated prefab; it does not resolve into `RecoveredProps`.
Consequently its dynamic-preview deformation is not evidence of wrong body
SMR ownership or duplicate-name/CRC binding. Explicit body and item bone lists
now fail closed on count mismatch, unresolved entries, or unresolved declared
root bones rather than leaving null skin bones or consulting CRC fallback. The
independent serialized stream report at
`reports/assets/character_body_skin_weight_audit.json` additionally decodes
all 1,867,523 source/generated body vertices: all 310 meshes retain their exact
four weight/index slots, 4,593,438 positive influences, and valid bone ranges.
Da Pan cloth 01 has zero tuple mismatches across 25,275 vertices; its maximum
source-to-generated weight delta is only float32 rounding (`2.98e-08`).

Mifu's Overview item belongs to `chr_0031_mifu_deco_2`; exact controller PPtr
ownership now overrides the misleading higher transform-match score from
deco 3, and the entrance hands off to
`A_item_widget_mifu_01_ui_disappear_01`. Pograni's four left/right weapon props
share one shipped idle-disappear PPtr. The importer emits four owner-qualified
runtime copies of that source clip so every private hierarchy receives its own
controller-proven post-transition instead of leaving all four entrance states
clamped. The item audit reports zero missing controller clips, wrong owners,
Overview visibility mismatches, channel overlaps, or source-sample failures for
Mifu and Pograni.

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

The shipped main UI AnimatorController JSON is now joined for all 30 actors.
Every controller has one full-body blend layer, 40 states, and 31 serialized
state transitions. The exact `Overview.FromOveview` entrance and
`Overview.OverviewIdle` handoff are published roster-wide, including the
AnyState destination offset, exit time, transition duration, fixed-versus-
normalized duration flag, destination offset, interruption source, and source
JSON path. Both fixed-second and normalized-duration Overview handoffs occur,
so treating every transition duration as normalized is incorrect.

Private-deco controllers are also joined to body controllers by exact state
path and clip PPtr. The current generated controller audit proves 357 imported
body+item state compositions across Overview, weapon, equip, skill, document,
upgrade, formation/team, and relax families. Remaining suffix-only pairings
stay labelled `source_inferred`. Suffix matching is not enough to establish that two
companion variants may be layered: recovered states reject any combination
whose clips write the same exact transform or active-state channel. The
current item audit contains 938 recovered companion layers and 257 multi-layer
states across seven actors, with zero admitted exact-channel overlaps;
ambiguous conflicting variants remain separately selectable evidence instead
of being played together.

### What is still missing

| Animation area | Current gap |
| --- | --- |
| Animator graph | Serialized main UI graphs are present for all 30 actors; the missing part is faithful runtime execution of their selector/parameter routing, all state-to-state transitions, interruption semantics, parameter consumers, and Lua/UI ownership |
| Root motion | Motion is clip-space object trajectory and Root is the absolute skeleton body reference. Character Info's rotation-only post-multiply is source-closed and translation is proven absent. The gameplay divisor expression and distinct `1e-5` accumulation/`1e-4` accessor gates are recovered, but controller blending, cycle accumulation, multi-modifier aggregation, higher-level divisor semantics, and final movement/collision/motor behavior remain open, so gameplay GameObject application stays disabled |
| Humanoid/muscle data | The 206-entry/101-muscle layout, inserted slots 28/30/31/39/41/42, 34/34 exact audited postmodel Avatar referentials, GetZYRoll scaling/range reduction, native ZYRoll construction, raw no-clamp production table, normal `Animator.Update` materialization edge, separate foot-goal rebuild, inactive translation-DoF stage, and eight-pair TwistSolve are recovered. All 272 mapped TwistSolve pairs are adjacent, exact physical write ownership is closed, and named twist branches preserve their generic local curves. An original full-frame numeric fixture still blocks final transform baking; current all-UI standard clips do not exercise the six extensions |
| Facial behavior | Blendshape/morph curves, emotion indices, face material curves, lip/eye control, look-at, and facial state machines |
| Events | Animation events, visibility handlers, audio, material/VFX events, prop toggles, and timeline signals |
| Item widgets | All 204 owner-qualified item/deco runtime clips validate against their decoded source samples, including six exact Wulfa apple clips, two Pelica visibility curves, Mifu's exact deco-2 owner, and four owner-qualified Pograni copies of the shared disappear PPtr. Exact private controllers now drive known Overview start-to-loop/disappear/displayoff handoffs; 14 private controller sources remain unavailable, and external FX/weapon/creature companions still need separate evidence. |
| CharInfo scene animation | Floor/grid one-second opened endpoints are recovered, but complete UIAnimation in/out curves and transition policy are not played |
| FX | Zhuangfy entrance requests are known but particle/trail resources and effect spawner are absent |
| Secondary dynamics | Original Magica Cloth version/manager timing, cloth/hair/ear/tail solvers, colliders, wind, initialization, and parameter bridges |
| Procedural motion | Authored targets are preserved roster-wide and guessed lab IK is fail-closed. Exact Grounder/foot bindings and serialized profiles cover all 30 actors; 28 use world-up and Chen/Li use the now-recovered root-aligned base path. The three foot-weight roles, quality-3 queries, missing-ground continuity, pelvis/leg order, final length clamp, and external hand-target path are source-proven. Runtime implementation is blocked on safely decoded available scalar samples plus unresolved absent-curve defaults, terrain/layers, live state, C# profile consumption, the retail solver surface, and numeric fixtures; alternate-quality/overstep/prediction/capsule branches, dynamic hand exData, knee/weapon consumers, look-at, sway, camera gyroscope history, and broader gameplay pose drivers remain unrecovered |
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
2. Build an original full-frame numeric oracle, then bake and validate the recovered
   `GetZYRoll -> B314D0 -> B17DB0 foot goals -> B323F0 TwistSolve` order.
   Normal `Animator.Update`, the eight pair order, `(1,0,1,0)` playable
   factors, all 272 adjacent compact/physical pair mappings, and exact mapped
   write ownership are already closed. Preserve named twist side-branch local
   curves. Do not feed the extensions into a stock
   95-muscle retargeter or clamp authored over-range values; only a specific
   curve producer may constrain values if its own original code proves it.
3. Recover controller transition/interruption root-motion blending, loop-cycle
   accumulation, multi-modifier aggregation, pipeline time, and final movement
   motor/collision gates before enabling gameplay object motion. Character Info
   remains rotation-only and must never consume Root as object motion.
4. Bind the 23 recovered `FootIKWeight` arrays only when a dedicated source-
   compatible runtime exists; first recover the two absent-key fallback/default
   owners, terrain query owner
   and layer mapping, live controller inputs, C# consumption of the already
   recovered per-actor Grounder profiles, the pelvis-aware foot-only consumer
   surface, and numeric original-frame
   fixtures before implementing the quality-3 Grounding path. The ordinary and
   Chen/Li root-aligned base coordinate frames are already closed. Then reverse
   the alternate quality/overstep/prediction/capsule bodies and recover the hand exData
   producer and any knee/weapon consumers. Keep the lab two-bone solver
   fail-closed and never infer weights from target distance.
5. Import facial/morph/material curves and events.
6. Implement the original UIAnimation policy for floor/grid and exact item
   widget/FX lifecycle rules.
7. Import the proven Zhuangfy entrance effects and required mount behavior.
8. Reconstruct the matching Magica Cloth generation, solver update order,
   colliders, wind, and initialization before attempting to match secondary
   motion from video.
9. Extend to look-at, grounding, and interaction constraints only with
   equivalent source evidence.

### Acceptance rules

- Every production parameter must cite original serialized data, shader/native
  behavior, or a valid runtime capture.
- Unknown values stay neutral, fail-closed, or explicitly diagnostic.
- No actor-specific screenshot fit is promoted as recovered behavior.
- Every shader change must pass at least Wulfa and Zhuangfy pose-locked A/Bs and
  the 30-character technical render sweep.
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

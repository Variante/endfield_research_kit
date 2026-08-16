# Endfield Character Recovery Lab

Unity 2022.3.62f3 project for viewing recovered Endfield character rendering,
materials, meshes, and animation clips in one shared scene.

The installed retail client reports `2021.3.34f5`, but that is Endfield's
proprietary Unity fork and no matching public editor is available. The lab is
therefore pinned to the exact installed public `2022.3.62f3 (96770f904ca7)`;
the separately installed public `2021.3.34f1` is used only for binary/ABI
differential probes and must not be used to open the maintained project.

Use the full recovery lab as the default viewer for shader, material, lighting,
camera, and animation work:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\open_character_recovery_lab.bat
```

This opens the canonical scene:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

Or directly:

```bat
"D:\Program Files\2022.3.62f3\Editor\Unity.exe" -projectPath "D:\fluffy-dump\unity_endfield_graph_shader_lab"
```

## All Canonical Character Models

The source-derived superset contains 33 canonical character-container
identities: 31 playables including Liino, plus Si/Jsspsi and Chenpast.
It selects only exact
`postmodels/characters/chr_<id>_<token>_postmodel.prefab` Animator roots.
The duplicate `postmodels/npc` mirrors and Zhuang Fangyi's `_ult` variant are
not separate people and are not duplicated in the lineup. Enemies and
ability/prop postmodels are inventoried as separate source categories rather
than being mislabeled as character identities.

Refresh the 33-character catalog without extracting assets:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_all_character_models.bat
```

Recover the two nonplayable character models from exact hierarchy
Mesh/Material PPtrs and decode only their source-owned preview animation when
one exists:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_all_character_models.bat --execute --unity
```

Jsspsi exposes its exact `A_actor_*_t_pose`; Chenpast remains static because no
token-owned preview clip is shipped. Liino uses the full playable UI pipeline.
Use
`CharacterRecoveryViewer.unity` as the maintained viewer; the separate
all-character resident scene is no longer retained.

## Enemy, Ability/Prop, and Ambient NPC Archetype Galleries

Non-character actors remain separate from the 33 named character identities.
The source catalogs cover 94 canonical enemy postmodels, 29 ability/prop
postmodels, and 6 supplemental ambient NPC source archetypes. The six NPC
prefabs are visibly labelled as incomplete modular archetypes; they are not
claims that a named NPC's authored appearance has been reconstructed.
Exact source renderer totals are 1173 for enemies, 423 for ability/props, and
86 for the modular NPC archetypes. The catalogs deliberately keep the
source-baseline candidate count separate from the admitted prefab count: a
candidate with an exact null Mesh PPtr is excluded rather than rendered. The
per-row baseline, hidden, and excluded counts in the current catalogs are the
authoritative totals. Excluded lower LOD, null-mesh, placeholder, and
unsupported particle records remain evidence rather than being presented as
successfully rendered scene content.

Recover every canonical source, generate all 129 manifests, import the
prefabs, and build the seven resident galleries with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
```

After source recovery has emitted an enabled manifest and imported prefab for
every catalog row, build the bounded resident gallery scenes with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\build_all_generic_actor_galleries.bat
```

If all manifests exist but Unity prefabs have not yet been generated, use the
combined importer and scene builder:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_and_build_all_generic_actor_galleries.bat
```

Enemies are split into batches of 24, ability/props into batches of 16, and
ambient NPC archetypes into their own batch under
`Assets/EndfieldGraphShaderLab/Generated/Actors/Scenes/`. Every batch keeps all
roots active in a horizontal lineup; selecting a model only reframes the
camera. Generic actors receive neither Humanoid manifests nor playable
CharInfo presentation profiles. Static MeshRenderer/MeshFilter recovery is
supported. The only source-explicit Unity built-in mesh admitted is Cube
PathID 10202 (`builtin_primitive: cube`); other built-ins and
ParticleSystemRenderer remain fail-closed. A zero-renderer source is admitted
only with an explicit source-proof flag and appears as a labelled transform-root
diagnostic whose TextMesh is not counted as recovered actor geometry.
`source_proven_external_geometry` is a separate diagnostic for an exact source
renderer whose embedded Mesh PPtr is null, such as Nefarcore; it does not claim
that the external/runtime-supplied geometry was recovered.

Scene construction is prefab-only and stops before saving if an enabled row
has no imported prefab or silently lost a required renderer. Existing 30- and
33-character scenes and build-settings entries are preserved.

All-scope import/build requires exactly 94, 29, and 6 enabled canonical rows.
After the prefabs and seven gallery scenes exist, validate all 129 active
resident roots, prefab bindings and baseline counts, 3.5-unit spacing, null
humanoid presentation profiles, and camera-only selection with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\validate_all_generic_actor_galleries.bat
```

## All Playable Characters: UI-Only Import

The maintained all-roster path derives its character list from the exported
game `CharacterTable` and keeps only rows that join to an exact Animator under
the shipped `postmodels/characters/<charId>_postmodel.prefab` container. On the
current patch-aware export that produces 31 concrete playable post-models. The abstract
`chr_9000_endmin` selector row is excluded because it has no concrete playable
post-model; both actual Endministrator variants remain included.

Refresh the source catalog and inspect the plan without starting a large asset
recovery:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\scripts\character_import\refresh_playable_character_ui_catalog.bat
```

Recover all post-models, decode the original UI overview body clips, generate
the Unity manifests, and build the selectable viewer:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_playable_characters_ui.bat
```

After a source-only repair, rebuild only selected actor mesh contents,
materials, and prefabs, then refresh the shared viewer catalog with a
comma-separated root-name list. Existing mesh assets are updated in place so
their GUIDs and prefab references survive while stale vertex/skin streams are
replaced. Close the Unity editor first because Unity refuses a second process
for this project:

```bat
refresh_targeted_character_assets.bat "Lizhiyan,Lastrite,Zhuangfy"
```

Recover the per-character CharInfo presentation records from installed-game
data and refresh an existing viewer without rebuilding every character:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\recover_playable_charinfo_profiles.bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\update_character_recovery_viewer.bat
```

The profile recovery first exports only `CharacterDisplayConfig` with its raw
sidecar. This is intentional: the current serialized TypeTree leaves its
managed-reference records heuristic-only, so the maintained decoder reads the
exact aligned camera/light strings, height enum, and overview-offset floats
from each bounded raw record before exporting the 31 camera/light/portrait
dependencies.

The second command writes all 31 prefab/profile references into
`CharacterRecoveryViewer.unity`. In Play Mode, use the top-left **Model**
dropdown to instantiate and switch characters on demand.

The canonical scope is now `all-ui`: it imports source-owned actor UI, team,
relax, equipment, skill, weapon, and gacha body families plus exact private
item/deco families for all 31 playable characters. Narrower scopes remain
available for diagnostics:

```bat
import_playable_characters_ui.bat --clip-scope overview-team
import_playable_characters_ui.bat --clip-scope all-ui
import_playable_characters_ui.bat --actor wulfa
```

For an actor-scoped Wulfa diagnostic without rebuilding the other 30 actors,
run:

```bat
rebuild_wulfa_animation_recovery.bat

import_playable_characters_ui.bat --actor wulfa --clip-scope all-ui
scripts\character_import\refresh_playable_character_ui_catalog.bat
update_character_recovery_viewer.bat
verify_wulfa_apple_animation_recovery.bat
```

Audit source Mesh identity across all 31 manifests, including exact private
item/deco hierarchy, clip-binding, recovered-state visibility, and Overview
widget paths, without reading or launching Unity:

```bat
verify_playable_character_mesh_identity.bat --source-only --output ..\reports\assets\playable_character_mesh_identity.json
```

After a completed Unity rebuild, omit `--source-only` to compare every existing
generated mesh's vertices/submeshes with its source JSON and verify its GUID is
referenced by the generated actor prefab. Add `--require-assets` for strict
postflight where every expected mesh asset must exist. The validator treats a
repeated authored name as an identity collision whenever it resolves to more
than one original Mesh path ID; those rows must have distinct path-ID-qualified
Unity asset basenames. Mesh index width is recovered from original submesh byte
offsets rather than vertex count alone; seven current fur meshes use 32-bit
indices below the usual 65,535-vertex threshold.

The Wulfa animation wrapper regenerates only Wulfa and validates mixed
ACL/MuscleClip playback. The viewer restores the generated prefab's complete
local reference pose before sampling a newly selected base clip, preventing
channels omitted by a sparse clip from retaining limb, tail, cloth, or facial
values from the previously playing clip. The final validation samples a dense
team-idle clip followed by a sparse ACL overview clip and requires the reset
result to match a fresh ACL sample transform-for-transform. It refuses to start
a second Unity editor while the project is open.

The same sparse-clip ownership fix applies to the complete playable roster.
Regenerate all 31 prefabs, require compact MuscleClip track mappings and one
Awake-time reference-pose provider per prefab, then sample every one of the 779
body clips with the runtime validator using:

```bat
rebuild_roster_animation_recovery.bat
```

For a manifest/source audit that does not start Unity, use
`verify_roster_animation_switch_recovery.bat`. The Unity-only
`validate_roster_animation_switch_runtime.bat` refuses to open a competing
editor when the project lock exists. Primary mode exposes only standalone body
clips; raw private widget clips remain available under All and their recovered
compositions remain under Recovered.

Audit private item/deco clip ownership, original controller state use,
body/prop duration agreement, recovered-state layers, Overview visibility, and
generated clip metadata without starting Unity:

```bat
python tools\verify_roster_item_animation_recovery.py --output ..\reports\assets\character_item_animation_audit.json
```

Pass `--strict` when known evidence gaps should make the audit return nonzero.

Audit every recovered item/deco `SkinnedMeshRenderer` root bone and ordered
bone array from the original owner-qualified manifest paths through the
serialized generated prefab with:

```bat
python tools\verify_roster_item_renderer_bindings.py --strict
```

The durable result is written to
`reports/assets/character_item_renderer_binding_audit.json`. This proves
binding identity and source transform path IDs; it does not replace rendered
pose validation in Unity.

Use the matching body audit to verify every selected LOD0 body renderer,
including exact ordered source Transform path IDs and collisions introduced by
private `RecoveredProps` hierarchies:

```bat
python tools\verify_roster_body_renderer_bindings.py --strict
```

Its durable output is
`reports/assets/character_body_renderer_binding_audit.json`.

The actor-scoped import deliberately builds a one-actor validation viewer.
Refresh the canonical `all-ui` catalog and update the shared viewer afterward,
as shown above, to restore all 31 selectable actors.

Generic companion names are admitted only when an exact shipped
`chr_<id>_<token>_deco_<slot>_controller.controller` contains an animation in
the same family. This source ownership edge is what joins the generic
`A_item_widget_apple_*` clips to Wulfa's exact apple deco prefabs; unrelated
shared widget names remain excluded.

`all-ui` still fails closed against combat, dialog, locomotion, and cutscene
clips. Body clips must also come from an original
`arts/entity/actor/.../animations/` container: name-matched effect/model rigs
are inventoried as deferred external UI effects. External gacha cameras are
inventoried but never loaded as body animation. The importer also recovers every exact shipped
`prefabs/uimodels/decoitems/chr_*_deco_*` hierarchy, its LOD0 mesh/material/
texture dependencies, and source clips whose transform bindings resolve
against that private hierarchy. On the current export this is 35 deco prefabs
for 15 actors (80 skinned and two static LOD0 renderers). The other 13 actors
have no exact UI-deco prefab in the exported data and are recorded as
source-proven zero rather than receiving a fabricated prop. The catalog is:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/playable_character_ui_catalog.json
```

Normalized per-character generated assets live below
`Generated/Characters/Playable/<Actor>/`; extraction caches and the
checkpointed run report live below `scratch/character_ui_import/`. The
canonical `Playable/` tree replaces the old duplicate Wulfa/Zhuangfy/Mifu
generated folders; the maintained viewer, fast scene, material audits, and
capture probes all resolve through the canonical manifests and prefabs.

After the import finishes and builds the shared viewer, render one consistent
1920x1080 source-profile image per enabled catalog character with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_playable_character_previews.bat
```

PNG files and `playable_character_preview_manifest.json` are written under
`scratch/character_ui_import/renders/`. The renderer checkpoints the manifest
after every character, keeps only one actor instantiated at a time, continues
past ordinary per-actor failures, and exits nonzero if any record failed. The
wrapper refuses an already locked Unity project, then strictly verifies complete
catalog/report accounting, the exact PNG set, PNG CRCs and 1920x1080 headers,
plus Unity's sampled finite/nonblank image metrics. Each render applies the
installed-game Overview camera, character-volume modifier, operator-light
group, `bg_charinfo_*` portrait texture/tight Sprite mesh and authored image
offset. The common background uses the recovered source-owned CharInfo
floor/wall/far-grid subset. Item widgets are deliberately hidden in these
body-only QA images. Animation sampling is currently fixed at loop time zero;
animation/controller timing, facial state, VFX, cloth and hair simulation are
separate recovery work. Render the recovered overview entry plus every
source-bound companion widget with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_playable_character_widget_previews.bat
```

Those PNGs and their evidence-labelled manifest are written below
`scratch/character_ui_import/widget_renders/`. Overview-paired and standalone
source-owned widget validation are separate: standalone sampling does not
claim that retail activation timing is known. Wulfa is controller-proven;
Zhuangfy's deco-3 `DefaultHGMaterial` Actor copy is source-proven inactive and
is never enabled. Its visible piaodai is imported from the separate gacha Effect
clone with the exact three material slots, Timeline clip-in/hold interval,
39-track ribbon motion and material-alpha fade. The remaining pairings are
marked `source_inferred` from an exact UI-state suffix plus complete private-rig
transform bindings. Verify the source contract and generated Zhuangfy manifest
with:

```bat
python tools\verify_zhuangfy_piaodai_effect_recovery.py
```

Render the three piaodai layers through the owned sceneMV MRT and compare them
against a renderer-disabled control frame with:

```bat
render_zhuangfy_piaodai_mrt_probe.bat
```

This probe must run with the wrapper's normal D3D12 device; `-nographics`
supports only one simultaneous render target and is rejected. The current
Unity `2022.3.62f3` result admits all three queue-3700 materials through the
exact `ExactSelectedPiaodaiThree` tag, renders 2,046 vertices, and changes
7,571 pixels with absolute RGB difference 1,327,352. The report and images are
written below
`scratch/character_recovery/zhuangfy_piaodai_mrt_probe/`. This validates the
lab's gated MRT execution, not pixel parity with a captured retail frame.

Build and strictly validate the six particle-bearing Zhuangfy gacha Effect
roots with the pinned Unity `2022.3.62f3` editor using:

```bat
build_zhuangfy_gacha_particle_recovery.bat
```

This imports the exact source hierarchy and stock ParticleSystem/module/
renderer payloads into six standalone prefabs. It preserves the original
material, mesh, texture, shader, and PathID provenance. Fifty-two complete
PathID/name/original-shader/ordered-keyword/queue identities use the selected
two-target BaseV2/RadialBlur/Refract ports; the remaining eight mode-4 source
variants remain intentionally invisible through the `ColorMask 0` fail-closed
shader. Both Lightning901 source-material identities remain in that fail-closed
set. The three exact renderers sharing `M_fx_ui_lightning_901` are instead
admitted through one renderer-scoped clone: the importer appends AgePercent and
InvStartLifetime, disables GPU instancing, and the shader replays the exact
linear Line006 or 62-row nonlinear third-renderer Custom1 step. The third
renderer also applies the original shader's precise packed-color round trip.
The separate `M_fx_ui_zhuangfy_lightning_901` identity remains fail-closed.
The newly admitted `M_fx_ui_lizi_905` moving trail and four-renderer
`M_fx_ui_lizi_907` billboard group share the exact non-instanced
`_SAMPLE_TEX0 + _USE_SOFTBLEND` specialization. Sample 0 is its weight-4
Blend carrier:
`blendFactor=saturate(preMaskMainAlpha+sample0.a)`, and pre-exposure RGB adds
`blendFactor*sample0.rgb*_BlendTint.rgb`. Blend does not replace main alpha;
the retail soft-depth factor multiplies the authored main/tint/vertex-alpha
path. Re-run the hash-pinned source/DXBC/Ruri audit with:

```bat
python ..\scratch\reverse_engineering\zhuangfy_lizi907_blend_runtime\audit_zhuangfy_lizi907_blend_runtime.py
```

Eight additional BaseV2 identities cover the active power/wind mesh-particle
cluster. `M_fx_ui_power_901..904` and `M_fx_ui_wind_901..903` use the exact
`_SAMPLE_TEX0,_SAMPLE_TEX1,_SAMPLE_TEX2,_USE_FRESNEL,_USE_SOFTBLEND`
specialization across nine renderers; `M_fxgp_char_buff_speedup_wind` uses the
related two-sample specialization across four renderers. The recovered shader
transports world normals and executes the installed Fresnel opacity equation.
All eight source materials set Fresnel color alpha to zero,
bias `-0.007`, and power/flip/opacity influence to one, so RGB is unchanged and
opacity is multiplied by `saturate(dot(V,N)-0.007)`. Re-run their hash-pinned
audits with:

```bat
python ..\scratch\reverse_engineering\zhuangfy_power_wind_fresnel_variant\audit_power_wind_fresnel_variant.py
python ..\scratch\reverse_engineering\zhuangfy_speedup_wind_fresnel_variant\audit_speedup_wind_fresnel_variant.py
```

Do not treat the friendly sampler names in the Ruri HLSL as original filter/
wrap evidence. `ShaderDecompiler.cs` assigns those names from a fixed pool in
register order; the stripped proof DXBC containers have no `RDEF` and their
pre-patch AnimeStudio sidecars have empty sampler tables. The particle importer now
preserves each of the 75 original Texture2D filter, wrap, anisotropy, and
mip-bias descriptors, and BaseV2 samples material textures through paired
Unity samplers. The packed-record/sentinel audit below closes that paired state
as the retail material-sampler behavior. The same binary audit
also corrected two real equations: `Use*AsAlpha` selects white RGB through
`lerp(sample.rgb, 1.xxx, selector)` while alpha selects sampled red, and
threshold/highlight runs before exposure multiplication.

The original packed Shader does contain descriptor metadata that the
pre-patch AnimeStudio sidecars skipped. `progVertex.m_PlayerSubPrograms` and
its parallel `m_ParameterBlobIndices` map the proof executable blobs
`1254/1394/1414` to native parameter records `0/127/147`; those records recover
descriptor-set/resource names, bindings, `PackedBinding`, and `PackedInfo`.
`progFragment` is genuinely empty because each Endfield executable record
contains both vertex and fragment DXBC. The material samplers carry sentinel
`PackedInfo=0x0001FFFF`: across 1,920 exact parameter tails from four original
shaders, every one of 5,570 sentinel samplers has a same-set/same-name texture
and none of 18,708 explicit static samplers does. A stock Unity 2022.3 control
reproduces this texture-derived versus explicit-static split. Parameter record
127 separately closes soft scene depth as point-clamp
`s_point_clamp_float_sampler=0x00010054`. This supports the
material-sampler admission gate without claiming that decoded PNGs preserve
the original compressed payload. Re-run the cross-shader/Unity-control proof
with:

```bat
python ..\scratch\reverse_engineering\zhuangfy_packed_sampler_sentinel\audit_packed_sampler_sentinel.py
```
The hash-pinned audit lives under
`scratch/animestudio/zhuangfy_vfx_sampler_metadata/`.
AnimeStudio now preserves this mapping in exported metadata, validates native
record tails fail-closed, de-duplicates native/common sampler entries, and
emits the raw sentinel without inventing a static-state decode; the separate
cross-shader/Unity control above closes it as texture-derived. Its targeted
VFXBaseV2 regression covers all 8,148 sidecars and passes with no
mapped-but-unparsed record or duplicate sampler key.

The `EndfieldZhuangfyPowerWindVFXBatchProbe` D3D12 check validates
`M_fx_ui_power_901` through `ExactSelectedFiftyThree`, the actual
159-vertex/159-normal source mesh, and imported Custom1/color/size curves. Its
current best sample changes 2,108 pixels with absolute RGB difference 91,174.
Public Unity 2022.3 batchmode asserts and
returns zero geometry for `BakeMesh` on this authored mode-4 renderer, even
when its public GPU-instancing preference is disabled, so the probe submits a
direct source-mesh copy. This validates the visible non-instanced material
specialization; the fork particle transport, `SRP_INSTANCING_ON` per-draw
array ABI, previous-clip sceneMV, and retail-frame pixel comparison remain
explicit boundaries.

The exact `_USE_SOFTBLEND` fragment reconstructs scene and particle positions
through inverse VP, applies the view-matrix Z row, and subtracts absolute
view-space Z. A literal public-Unity inverse-projection port produced zero
coverage in this D3D12 probe because its matrix/depth conventions differ from
the retail HGRP constants. For the maintained perspective camera that metric
reduces algebraically to `LinearEyeDepth(rawDepth)`; the shader uses that
projection-correct equivalent and keeps the retail continuous scene-depth
sample UV. This validates the compatibility camera, not the retail instruction
sequence. The scene-depth sampler itself is point-clamp as closed above.

The newly admitted mode-0 billboard families are two evidence-equivalent
clusters: nine BASE identities/ten active
renderers (including `M_fx_ui_lizi_901`) and eight soft-only identities/nine
active renderers (including `M_fx_ui_lizi_906`). Every renderer is active,
enabled, unmeshed, and uses stock `[0,1,3,4]` streams. The
`EndfieldZhuangfyLizi901BaseVFXBatchProbe` validates exact fixed-seed source
simulation and deterministic visible BASE output. The
`EndfieldZhuangfyLizi906SoftVFXBatchProbe` additionally validates point-clamp
soft-depth attenuation from 70 changed pixels/RGB 8,364 unobstructed through
28/RGB 2,999 at a shallow intersection to zero under full occlusion.

Three later source-closure waves admit eight more identities. Glow902 uses
the retail absolute view-space-Z near fade with its signed authored
denominators. Dian903, glow901, and glow904 use the exact weight-3
per-channel Sample0 RGB/alpha mask plus soft blend. Gacha10, gacha12, lizi902,
and suidian901 use the exact non-soft Sample0/Sample1 disturbance, dissolve,
and near-fade routes enabled by their material constants.

Four binary-first admissions first brought the coordinated gate to 46 visible.
`M_chen_jiaju_woodenstake_02_901` closes the corrected white RGB-as-alpha,
weighted disturbance, and dissolve-edge equations. `M_fx_ui_rainbow_901`
adds the exact per-fragment polar approximation, four sample carriers,
blend-before-dissolve ordering, and five native BC7 payloads; its compiled
screen-UV route is admitted only because the authored screen selector and all
five screen-coordinate weights are zero. `M_fx_ui_trail_904` uses Unity's
stock mode-5 Ribbon path and the already recovered BaseV2 fragment. Its
fixed-seed D3D12 proof emits nine particles, bakes a deterministic 20-vertex
ribbon twice under one fixed camera, and renders 52,189 changed pixels.
`M_fx_ui_trail_901` uses the stock lit mode-5 Ribbon path. Its exact 0018/0019
specialization collapses the compiled Sample0 dissolve branch because
`_InParticle=0`; its active 1024x512 MainTex preserves all 11 native BC7 mips.
The forced-D3D12 proof emits 13 particles, bakes 28 vertices/78 indices with
Color, UV, Normal, and Tangent arrays sized to the vertex count, and renders
4,788 changed pixels. Mesh and raster repeats are deterministic.

A later six-identity admission brought the coordinated gate to 52 visible and
eight fail-closed. Trail902/903 use the exact
0894/0895 specialization and stock unlit `0x19` Ribbon geometry. Their
fixed-seed D3D12 probes each bake 18 vertices/48 indices with Color/UV and
zero Normal/Tangent payloads; both mesh and raster repeats are deterministic.
The four tianshiyi additive EntityVFX materials execute through the exact
deco-1 LOD0-L3 ownership, newest-first/native-four-record/original-last
lifecycle, and `_TintColorAlpha` start curve. Their D3D12 probe produces four
distinct deterministic overlays on the source skinned LOD0 renderer. Run all
current and retained checks with:

```bat
run_zhuangfy_vfx_regressions.bat
```

`M_fx_ui_glow_903` was the next source-closed admission, raising that build's
gate to 53 visible and seven fail-closed under `ExactSelectedFiftyThree`.
The exact material/particle/renderer sources pin BaseV2 queue 3700 with ordered
`_USE_FRESNEL`, `_USE_SOFTBLEND`; a null MainTex therefore follows the shader's
white default without a synthesized texture payload. Its stock mode-4 renderer
keeps the authored HG GPU-instancing preference, local alignment, distribution
zero, Position/Normal/Color/UV streams, and Unity built-in Sphere
(515 vertices/2,304 indices). The dedicated forced-D3D12 probe replays one
fixed-seed particle at five active Timeline-route times and validates its
constant position/rotation/size, color-over-lifetime gradient, disabled Custom
Data module with Unity's all-zero default slot, and deterministic particle and
baked-mesh hashes. The selected raster changes 30,979 pixels unobstructed,
23,251 at a shallow depth intersection, and zero when fully occluded; every
repeat is byte-identical to its first render. Run it directly with:

```bat
render_zhuangfy_glow903_mode4_probe.bat
```

The current conservative source-material gate is 52 visible and eight
fail-closed. The separate `M_fx_ui_zhuangfy_lightning_901` identity was removed
from material-wide admission after the retail producer audit showed that its
visible state was not source-closed. Exact importer validation keeps both
Lightning901 source identities on the ColorMask-0 shader while assigning one
recovered clone only to the three proven `M_fx_ui_lightning_901` renderer
PathIDs. Dian902 source material `6860781171007043348` also remains
ColorMask-0 and outside `SelectedMaterials`; a second clone is isolated to
renderer `-7137180953804559081`. Its generated effect root now carries
`EndfieldRecoveredDian902ManualPlayback`, an explicit, non-auto-playing
runtime. `SimulateExact(float sourceTime)` retains the fixed/manual contract,
and `RestartExact()` plus `AdvanceExact(float callerDelta)` expose the
separately recovered automatic-delta contract without adding an `Update()`
hook.

The API maps the installed-retail fixed/manual source-time intervals to all
nine distinct live states at canonical representatives `.96`, `.98`, `1.00`,
`1.02`, `1.04`, `1.06`, `1.08`, `1.10`, and `1.12`. It verifies that public
Unity reproduced the exact retail seed, position, rotation, and size before
supplying the strict four-field renderer tuple. Pre-birth, post-death,
negative, and non-finite inputs clear the particle and invalidate the tuple.
The installed optimized CustomData evaluator supplies all nine exact
`Custom1.z` values; the Fixed-gradient path makes state 3 transparent and the
other eight states exact linear Draw color `FF006DFF`. Default and all 36
one-bit tuple mutations remain clipped.

The automatic path comes from hash-pinned installed `UnityPlayer.dll`
execution mapped as data, not from public Unity timing. It subdivides each
caller delta with the installed `0.03f` maximum particle timestep, drains a
final remainder down to the native epsilon, applies the strict five/ten-second
hitch floors, crosses the authored delay before the burst, starts the newborn
at age zero, then advances and compacts it with the retail float32 age/death
ordering. Equal nominal time is intentionally partition-sensitive: grouped
`.96`, `48 x .02`, and `.48 + .48` leave emitter-time bits `3C23D55C`,
`3C23D5C0`, and `3C23D520`; grouped `1.10` and `55 x .02` produce age bits
`42AEE179` and `42A4B4B4`.

The scoped BaseV2 clone admits that continuous path only through a coherent
four-field dynamic tuple. Its installed CustomData polynomial and Fixed alpha
were checked at 4,249 finite ages, including every integer percent, randomized
values, and ULP neighborhoods around all branch transitions. Invalid,
pre-birth, post-death, fault-latched, or tuple-poisoned states clear or clip,
and the source material remains ColorMask-0. Public Unity supplies only the
already bit-verified seed and static geometry; it is not retail scheduling
evidence.

Run the fixed/manual, automatic CPU, continuous-leaf, and automatic production
D3D12 checks with:

```bat
run_zhuangfy_dian902_exact_state_d3d12_probe.bat
run_dian902_automatic_delta_contract.bat
run_zhuangfy_dian902_dynamic_render_leaf_d3d12_probe.bat
run_zhuangfy_dian902_automatic_delta_d3d12_probe.bat
```

The generated census is therefore 60 source materials plus two renderer-scoped
clones. Canonical import validation, the fixed/manual Dian902 contract, the
automatic-delta CPU contract, the diagnostic continuous-leaf probe, and both
production Dian902 D3D12 paths pass, as do all 14 maintained D3D12 VFX
regressions. The automatic contract covers six
grouped/split/death sequences, three strict delay boundaries, seven hitch
boundaries, six poison inputs with a sticky fault transition, restart/disable
clearing, and 191 unrelated property-block-preservation checks. Repeated
imports preserve this semantic census and validated payload, although the
existing duplicate-name `baofa` prefab is not byte-idempotent because Unity
reassigns its local fileIDs on each `SaveAsPrefabAsset`.

The BaseV2 disturbance carrier is gated by the serialized
`_UseParticleDisturb` property, not `_DisturbUseWeight`. Nine selected retail
fragment families use `_UseParticleDisturb ? Custom1.w : 1`; the rainbow
polar+screen 1033 signature alone also multiplies `_InParticle`. This split is
source-closed from ten original fragment blobs, and the maintained 1237 port
matches both original MRTs byte-for-byte across baseline, dissolve, and
soft-depth fixtures. Wooden-stake and rainbow D3D12 counterfactuals exercise
the ordinary and exceptional expressions. The fix does not grant
material-wide Dian901/902 admission. Dian901 remains fail-closed; Dian902 now
has only the exact renderer-scoped fixed/manual and automatic-delta paths
described above.

The lizi901/lizi906 main textures, all five rainbow901 slots, Trail901
MainTex, Trail902/903's active carriers, and all five active EntityVFX
textures no longer use decoded PNGs. AnimeStudio's
opt-in native-payload export preserves their original BC7 bytes and mip
manifests, and the importer creates Unity `Texture2D` assets whose
`GetRawTextureData` hashes must match: lizi901 is 512x256 with ten mips and
lizi906 is 128x128 with one mip; the five rainbow slots and Trail901 preserve
their exact BC7 blocks, authored mip counts, and Clamp/Repeat descriptors.
Six native contracts currently contain 28 unique exact textures after shared
payloads are de-duplicated. The newest contract covers the six live 0840/0841
MainTex carriers used by glow center/flash and line/ray 901/902. Their exact
BC7 bytes, authored mip chains, dimensions, color spaces, and sampler settings
come from the installed VFS; dead serialized texture slots remain unbound.

The audited mode-4 mesh particles are no longer blanket-classified as fork
HG-instanced draws. The installed `UnityPlayer.dll` predicate requires
`m_EnableHGGPUInstancing=true`, but all ten audited uses serialize it false and
all eight materials disable instancing variants. The project-local
`EndfieldZhuangfyLightning903904StockMeshProbe` therefore exercises the stock
CPU path. On D3D12 it deterministically reproduces nonzero `BakeMesh` geometry
and exact source-mesh index counts for lightning903/904. Those materials remain
fail-closed. Retail RVA `0x141CCA0` is the shared Local/View/World body
corresponding to the public PDB
`CalculateMeshParticleTransform<0>/<1>/<2>`, not specialization `<3>`.
Velocity alignment uses a separate wrapper at `0x1425650`,
`DrawMeshParticles<4>` at `0x14389C0`, and
`CalculateMeshParticleTransform<4>` at `0x141E370`. Exact snapshot replay
proves that `<4>` consumes both velocity lanes, ignores its transform-matrix
pointer, and expects alive percentage on a `0..100` scale. All five remaining
Lightning901/903/904 renderer uses serialize mode 4 plus alignment 4 and
dispatch to this Velocity specialization; the earlier `<3>` label was wrong.
The Lightning902 bridge now covers four live times. Its first three retail
replays match all 256 baked positions within `1.08e-7`; the `0.40` second
sample retains a constant translation residual of about
`(-1.66e-5,+1.80e-5,-1.93e-6)`, while its affine basis matches within
`9.53e-8` after removing that one offset. All four inverse-transpose normal
comparisons remain within `2.64e-7`, and `0.70` seconds is the zero-particle
death control.

The separate remaining-Lightning bridge can be refreshed with:

```bat
run_zhuangfy_remaining_lightning_velocity_probe.bat
```

It hard-limits capture to the exact five renderer IDs, writes first/repeat
payloads for 25 samples, and retains `visualAdmission=false`. The current run
is byte-deterministic with exact BakeMesh geometry counts. Offline retail
`<4>` replay covers all 36 live public particles / 21,202 source vertices.
After fitting one constant translation per particle, position-basis residuals
stay within `1.71e-7` and inverse-transpose normals within `3.17e-7`. Raw
translation errors remain preserved, reaching `0.012315`; the diagnostic
therefore closes transform shape, not retail state. With the leaf's separate
`alignToDirection` argument false, public `velocity` and `totalVelocity`
candidates produce identical affines and do not resolve native SoA ownership.

The separate Dian shared-transform bridge can be refreshed with:

```bat
run_zhuangfy_dian_shared012_probe.bat
```

It hard-limits capture to the exact Dian901/902/904 renderers and writes 15
first/repeat payload pairs. The current D3D12 run is byte-deterministic, covers
22 live particles / 820 vertices, and preserves exact particle, mesh, vertex,
and index segmentation. Offline replay executes every particle through the
installed retail shared Local/View/World body at `0x141CCA0`. The retail Local
caller selects rotation-LUT block 4; all six initialized blocks were tested,
and block 4 is decisively best. Dian901 and Dian902 close within the configured
`2e-5` position/normal limit. Dian904 does not: its fitted position residual is
`0.00367060879` and inverse-transpose normal error is `0.621998416`.
Caller-matrix construction, ICF specialization, and public SoA ownership
ambiguities remain recorded. The probe therefore retains
`visualAdmission=false`; no shader, material, importer, or admission gate is
changed.

Static stock-version comparison independently rejects public fixed-seed
simulation as a retail-state oracle. The available symbolized player is Unity
`2021.3.34f1`, while Endfield ships `2021.3.34f5`; only
`ParticleSystem::Update0` and `EmissionModule::EmitCommon` are normalized
relocation-equivalent. Critical simulation, initial sampling, burst/rate,
size/color/custom-data, gradient, and curve bodies differ. Public state remains
differential input only.

Static audit further proves `Draw<4>` writes the scaled destination affine
twice and never reads `dstNoScale` afterward; inverse-transpose normal handling
is downstream. The capture wrapper is
dormant and refuses Frida Interceptor attachment without the explicit
code-patch opt-in because Interceptor is not a strict no-target-write oracle.
A strict live Zhuangfy SoA/retail-frame pixel oracle is still missing. A
narrow original-pixel-DXBC oracle now covers the Lightning902 fragment under a
fully declared synthetic surrounding state. It executes the shipped D3D11
pixel blob directly, never treats the recovered Unity shader as an oracle,
uses the two exact native BC7 payloads, and binds sampler state from the native
contract rather than Ruri's friendly register-order names: point-clamp soft
depth, bilinear-clamp MainTex, and bilinear-repeat SampleTex0. Two processes
and six total draws produce deterministic finite two-MRT output.

Run the fail-closed project wrapper only while Unity is stopped:

```bat
verify_zhuangfy_lightning902_original_ps_oracle.bat
```

The wrapper deliberately stays outside an Editor `executeMethod`. Public Unity
cannot create the stripped original pixel program from raw DXBC without
translation, and the oracle refuses to share its D3D11 GPU lane with a Unity
process. Its canonical output is Target0
`BB37A20D9F6B41B8CAB35F6EE737C51DAEC253820FF92C7AFDDDCD3ED47D0823`
and Target1
`265338EAA113D79CEA2A3D3F1BBC984DFFFE7153C4E0960957A171FDD8A897C2`.
The passthrough vertex shader, depth ramp, frame constants, and unreferenced
physical b3 holes remain synthetic and byte-declared; raw retail b0..b3,
runtime depth, original vertex interpolants, exact draw state, and a retail
render-target capture remain required for retail-frame equivalence.
Under those declared synthetic inputs, a same-input differential against a
source HLSL mirror of the current recovered Lightning902-compatible fragment
now closes exactly. Native parameter record 130 contains a compact material
table before its descriptor tail; combined with the common parameter record
and exact Lightning902 material, it source-closes all 53 b3 lanes statically
read by fragment program 0859. The resulting read-set hash is
`0B7806BE0B71FB08984F3EED4E18B72B0F9DD5F6440F385353A59F420B919C7D`.
Twenty-seven unreflected physical lanes remain explicit unknowns, are zeroed
only for deterministic initialization, and are not read by 0859.

Run the exact same-input differential only while Unity is stopped:

```bat
verify_zhuangfy_lightning902_original_ps_differential.bat
```

The semantic recovered port and an independently generated literal
instruction-shaped port both match the original Target0 and Target1
byte-for-byte on all three draws: zero mismatched pixels and zero RMSE on both
MRTs. The earlier mismatch was a differential-port defect: its HLSL input
struct placed `SV_Position` last, so FXC assigned physical PS input registers
in a different order from the original blob. Moving `SV_Position` first closes
the result; literal soft-depth and authored-MV-off sceneMV variants remain
identical, while RGB-selector and no-highlight counterfactuals diverge. No
fragment-stage patch is justified or applied. This exact synthetic
differential supersedes the earlier partial-b3 mismatch report.

The exact Lightning902 companion vertex program is also executable now. Build
the canonical Unity-side input bridge first:

```bat
run_zhuangfy_lightning902_vertex_input_bridge.bat
```

Then, while Unity is stopped, run the original 0858+0859 pair and the
same-input vertex differential:

```bat
verify_zhuangfy_lightning902_original_vs_ps_oracle.bat
```

The original vertex blob is
`6747FE2CBF4E692B924DAD8ABA5547EC19FC590FFEC9446A78E394E2545A494D`.
Its active non-skinned path reads 121 constant-buffer lanes, including 52
exact material lanes and no SRV. Native record 130 supplies both scaled
affines, the disabled-LOD sentinel, motion parameters, and the inverse packed
particle color. The bridge therefore retains source-white COLOR and carries
the live particle color separately; using BakeMesh COLOR as retail COLOR would
apply it twice.

The independent semantic vertex port matches the shipped 0858 output
byte-for-byte across all 5,632 floats for the baseline and six
counterfactuals. The earlier Unity-compatible port differs on 3,584 floats.
Those counterfactuals distinguish five ownership boundaries: the shared shader
was missing camera-facing displacement; public Unity COLOR already represents
the retail c13 color result; selected UV weights already make the current UV
route equivalent; Unity owns its projection jitter; and selected previous-clip
motion is provably neutral. All 52 admitted materials serialize
`_SurfaceType=1` and `_EnableTransparentMV=0`, and all 15 admitted original
fragment signatures therefore emit zero sceneMV X/Y. Generic motion-enabled
passes still require the previous camera/object/deformation lifecycle. The
synthetic original-pair target hashes are
`07854D2FEF297A06BA81685E660C332DE36D5D18D546927D30DAAD6D7FDA1541`
and
`DFAE667BEEBDD592B54956AEF60A98B78FF8E5980A36F9F6405B4BC3D8CFA52E`.
They are component-oracle output, not a retail-frame capture or visual
admission.

Four exact shipped vertex blobs used by ten admitted materials share the
camera-facing formula:

```text
cameraDir * (min(max(distance - 1, 0), _VertCameraOffset) + 0.001)
          * (1 - _DisableAnimateVert)
```

The recovered BaseV2 shader applies it in world space before clip, screen, and
world outputs. `_DisableAnimateVert` is a global per-pass input. The installed
retail producer zero-fills it for the selected Forward, Transparent, and
after-DOF routes; DepthOnly is an explicit non-selected value-1 control.
Unity's zero is therefore the exact selected value, and no redundant global
publisher is needed. Particle COLOR/UV, Unity jitter, generic motion-enabled
history, and the current 52/8 admission gate are unchanged. The static family audit is
`scratch/reverse_engineering/zhuangfy_vfx_vertex_camera_offset/`.
An independent Glow903/0936 semantic differential also matches the shipped
vertex output byte-for-byte. It exposes a missing secondary UV route weighted
by `_MainTexUVWeights.y`, but all 76 censused Zhuangfy materials author that
weight as zero and fragment 0937 does not read the otherwise missing tangent;
neither inactive route justifies a Unity patch.
All 13 maintained VFX probes pass. Glow901's soft-depth fixture follows the
displaced surface and retains strict attenuation:
`21,041,974 -> 6,118,700 -> 0`.

The shared BaseV2 shader also contains the exact shipped Dian901/902 vertex
offset surface behind `_USE_VERTOFFSET` and `_USE_VERTOFFSETMASK`. The path
reproduces blob 1236's secondary-UV selection, direction modes, custom-w
amplitude, offset and mask sampling, bidirectional remap, fused camera offset,
and Sample0/Sample1 UV outputs. The maintained-source differential under
`scratch/reverse_engineering/zhuangfy_dian901_902_original_differential/`
matches all 29 output float lanes for both materials across six cases each.
Neither keyword is active on any of the current 52 selected material tuples;
the importer asserts that boundary, the 52/8 census is unchanged, and
Dian901/902 remain fail-closed until their live particle state is recovered.

Their visible path additionally requires the recovered native sceneMV MRT,
old-scene snapshot, depth-access, selected-rig, time, and exposure gates.
The current installed retail call graph fixes the schedule as GBuffer ->
ForwardOpaque -> main ForwardOnly -> Distortion -> gated post/DOF/motion blur ->
after-DOF ForwardOnly. The lab follows that order. The remaining selected-scene
motion gap is now narrowly the retail 4x4 bone-array construction/coordinate
space, not ForwardOnly/Distortion ordering or history allocation. The native
row ring, `boneCount+1` matrix writer, current/previous generation rollover,
discontinuity reset, draw offsets, and CharacterNPR row consumption are pinned;
the lab stays fail-closed until the input matrix space is equally proven.
SceneMV admission is driven by any of the 53 identity-gated selected materials; an
active blur/refraction Distortion member is not required for main or after-DOF
ForwardOnly effects to render.

The selected BaseV2/Refract ports no longer depend on an unowned stock
`unity_LODFade`. Retail `UnityPlayer.dll` proves the signed 16-bit custom-alpha
packing and `lodFade.xy` reconstruction, plus `(1000,0,0,0)` as the disabled
per-draw/particle sentinel. The selected piaodai EffectSetting enables one
distance tier at distance `0` with `framePercent=1`, disables culling and
auto-fade, and has no stock `LODGroup`; the three materials also serialize
instancing disabled. Their selected Vulkan SPIR-V variants therefore read one
`PerDrawBaseData` block directly: set 2/binding 0 member 1 at byte offset 64,
with no `InstanceIndex` or `BaseInstance` built-in. `SRP_INSTANCING_ON`
variants are a separate ABI that index a 256-entry block array with
`InstanceIndex`. The retail particle helper writes the same disabled
`(1000,0,0,0)` vector at instance-record byte offset 64, independently tying
the sentinel to the shader member.

Generated selected materials bind that exact neutral/default payload through
`_RecoveredLODFade`, and the piaodai compatibility shader now executes the
original position-hash, signed-threshold, coverage, and alpha-tail equations.
The selected runtime route is source-closed as neutral. The ribbon child is
serialized active, its only distance tier also requests active, and current
`GameAssembly.dll` copies that state into both initial/current
`EffectLodCfg` activity; `_RefreshLod` therefore never arms fade state 1 or 2.
Auto-fade is disabled, the selected Effect Timeline contains no
`RecorderEffectAlpha` asset, its alpha curve targets only
`material._TintColorAlpha`, and the shipped Gacha Lua calls no EffectSetting,
EffectInstance, or Renderer custom-LOD API. `UnityPlayer.dll` initializes the
Renderer custom-LOD flag/value to disabled/zero, so this draw retains
`(1000,0,0,0)` exactly rather than merely as a fail-closed assumption. The
hash-pinned verifier/report is under
`scratch/reverse_engineering/piaodai_lodfade_runtime/`.
The selected dissolve/material route is independently source-closed at the
serialized values. All three material identities carry
`_UseDissolve=1`, `_DissolveUseWeight=0`, `_DissolveScheduleOffset=0`,
`_DissolveEdgeSharp=0.5`, `_DissolveEmissiveEdge=0.2`, and
`_DissolveEmissiveColor=(0.88759637,2.1880286,1.889929,1)`. The selected
subtree contains only `EffectSetting` and `EffectAnimation` scripts;
`EffectAnimation.OnEnable` returns for its serialized
`isEnableChangeState=1`, while both authored Timeline clips animate only the
same `_TintColorAlpha` binding. Shipped Gacha Lua, the installed IFix payload,
and the complete current-build `Renderer.SetPropertyBlock` caller census add
no selected dissolve writer. The hash-pinned material-ownership report and
verifier are under
`scratch/reverse_engineering/piaodai_material_override_runtime/`.
Its selected vertex variants use the retail global `_VFXParams0.w =
fmodf(UnityEngine.Time.time, 1024.0f)` for every authored UV-scroll speed
term; they do not use Unity's unwrapped `_Time.y`. The three queue-3700 draws
are narrowly admitted to the owned point-filtered, Repeat-wrapped,
single-sample `A2B10G10R10_UNormPack32` sceneMV attachment. They preserve the
serialized indexed target-1 blend and emit the exact
`float4(0,0,1,activeMask)` result while
`_EnableTransparentMV=0` and `_SurfaceType=1`.
A maintained helper reproduces the exact custom-value encoding for other
source-proven live owners; the selected piaodai route has no manual-alpha
transition.
The particle batch build checks both sides of the retail `0.5` packing
discontinuity. A targeted piaodai rebuild and a separate validation-only editor
load verify the three saved non-instanced materials and their sentinel. Public
Unity `2021.3.34f1` PDBs identify
`SkinnedMeshRendererManager::TryPrepareStandardRenderer`; its unique structural
match in the installed `2021.3.34f5` fork is the distinct function at
`0x180509A70`. A separate custom job at `0x181064100` is proven to transport
raw transition-float bits into D3D12 `startInstance`, but the selected SPIR-V
declares neither shader-visible instance/base-instance input and both selected
D3D12 vertex DXBC signatures omit `SV_InstanceID`. That lane therefore cannot
affect these piaodai programs. Its exact renderer-family
purpose remains open only as a broader fork question, not as a selected-ribbon
pixel-fidelity blocker. The reproducible binary/PDB/DXBC/SPIR-V correlation is
`scratch/reverse_engineering/piaodai_renderer_route/piaodai_renderer_route_report.json`.

The selected GachaRoom exposure owner is now joined as well. The global
environment volume points to `Env_gachaRoom_01`, whose active Manual zero-EV
profile targets exposure `1` with symmetric `0.6/0.6` scaled-`deltaTime`
adaptation. The prefab's `ExternalCamera` contains a serialized-disabled Unity
Camera plus an enabled `CinemachineExternalCamera`: native code samples that
Camera's transform/lens into Cinemachine state, while `CinemachineBrain`
applies the state to `CameraManager`'s separate persistent physical main
Camera. Gacha therefore reuses that Camera's `HGCamera` exposure history rather
than receiving constructor exposure `1`. The exact recurrence is
`E[n+1] = 1 + (E[n]-1) * (1-clamp(0.6*deltaTime[n],0,1))`; the lab implements
it as `AdaptGachaRoom(current, deltaTime)`, but does not invent the missing
carry-in value or frame-delta sequence. The hash-pinned current-build verifier
and report are under
`scratch/reverse_engineering/gacharoom_exposure/` (report SHA-256
`3A74B1BAD97415D240404B6AB90804F7E02AA41A1676B4950DA741F6FF933B7E`).

Regenerate and verify the separate serialized-data contract for the exact
16-track gacha Timeline and its five EntityVFX assets with:

```bat
python tools\build_zhuangfy_gacha_timeline_entity_vfx_contract.py
python tools\verify_zhuangfy_gacha_timeline_entity_vfx_contract.py
```

This contract retains every original track/clip timing, target binding and
particle-control field, the complete four additive-material payloads, and the
complete dissolve payload including its curves. It source-gates the four
animation clips and selected material/texture/shader closure.

Build the exact Zhuang Fangyi-only recovered runtime with the pinned Unity
`2022.3.62f3` editor using:

```bat
build_zhuangfy_gacha_runtime_recovery.bat
```

This regenerates the hash-gated runtime payload, rebuilds the six particle
prefabs, and emits the real 16-track Effect Timeline plus a separate,
source-gated Actor camera Timeline and their bound runtime prefab. The Actor
track replays the exact `A_actor_zhuangfy_gacha_cam` position, normalized
rotation, and vertical-FOV cubic curves on a prefab-local `ExternalCamera`.
That Camera remains disabled and is never connected to the viewer camera or
Cinemachine. The Effect Timeline retains seven particle Control tracks, four
Animation tracks, four additive-material EntityVFX handlers, and one dissolve
handler. A separate fresh-editor validation-only load also passes. The
implementation preserves the native
highest-weight `> 0.001f` gate (equality is inactive), inactive playing-state
cleanup, per-effect material-clone removal, curve-property enum semantics, the
dissolve shadow stop/reset window, and the source initial/delayed Effect
operations. It is deliberately limited to these five serialized Zhuang Fangyi
assets. Three rarity path CRCs stay unbound because an exhaustive original-data
scan classifies them as stale/removed clip bindings in all 18 serialized effect
copies. The selected 25 fields outside the stock importer surface (23
Endfield-only and two shared public-f1 renderer names) are inventoried but their
active fork behavior is not approximated. Renderer-helper eligibility and
material order are closed: Zhuang's `All=-1` mask accepts all four original
default-Normal widget renderers at LOD0-LOD3; the recovery imports their exact
CrossFade `LODGroup`, applies at most four active materials newest-first, keeps
originals last, and restores source materials/visibility on stop. EntityVFX
definitions are joined through the original clip/playable/asset PPtrs. The
four additive definitions now bind admitted BaseV2 materials and five exact
active native BC7 textures. `render_zhuangfy_entity_vfx_probe.bat` exercises
the real runtime lifecycle on the exact source skinned LOD0 renderer and
requires four distinct deterministic D3D12 rasters.
The
installed dissolve path is not a `MaterialPropertyBlock`: native
`EntityVFXDissolveController` reaches
`MeshMaterialController._TryEnsureReplaceMaterial` and writes the resulting
Unity Material instances. The runtime now mirrors that ownership, composes
replacement instances with active additive overlays, writes only supported
properties, and proves clone assignment, reset, restoration, destruction, and
shadow timing.

The four exact `deco-1` LOD targets currently share
`Endfield/Recovered/CharacterCloth`, which supports none of the nine retail
dissolve properties and has no compiled `VFX_CHARACTER_DISSOLVE` branch.
Visible character dissolve therefore remains explicitly fail-closed. The
exact retail CharacterNPR blob `695/33` fragment is recovered, but a faithful
port still requires the custom per-draw schedule carrier at UnityPerDraw
offset 220, Point/Repeat texture sampling/import, and the native pre-final-
lighting energy insertion point; these are not replaced by guessed material
values. This dissolve branch remains the EntityVFX visual boundary; the four
additive HGRP VFX variants now execute through the recovered two-target
ForwardOnly contract.
Camera validation bit-checks the declared previous/current curve samples and
requires exactly the Actor-camera and Effect directors, one disabled
`ExternalCamera`, and no Audio/Light/Others helper objects. The 256-byte
live camera-matrix fixture remains diagnostic-only: physical-camera blending,
cuts, exposure, jitter, previous rendered matrices, and exact rendered-frame
history are not synthesized by this runtime.
The validation report is
`../scratch/character_recovery/zhuangfy_gacha_runtime/unity_validation.json`.

Build the static all-roster feature matrix with
`build_roster_feature_validation_plan.bat`. Its material result deliberately
separates `structural_status=ready` (asset counts and supported-family shader
bindings) from `source_input_status`. A nonblank render is not material-ready
when a selected mesh still uses a fallback shader, a source texture property
has no nonzero/resolvable generated reference, or a source-active
`_Pantyhose`, `_UseCharacterFur`, or `_UseDissolve` input is absent. The same
matrix resolves each actor's deterministic CharInfo presentation profile and
reports source/direct-supported operator-light counts plus the default-off
punctual, character-shadow, and screen-shadow boundaries. Run
`render_roster_feature_validation.bat` when the plan and all PNG stages should
be validated together.

## Default Character Recovery Viewer

Open this scene and press Play:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
```

After the playable UI import, the top-left runtime UI can switch among every
catalog character whose manifest was generated. The catalog and canonical
`Playable/` manifests are required; there is no ordinary legacy-folder fallback.
The full viewer embeds all 31 prefabs in one horizontal, alphabetically ordered
lineup and keeps them resident. The **Model** dropdown moves the recovered
camera framing to the selected actor without loading or destroying a model.
Selection also swaps the exact recovered actor profile:
Overview camera/FOV, character-volume values, operator lights and followers,
portrait texture/mesh/offset, and the shared recovered CharInfo presentation
path. The viewer can search clips, restart playback, and reset the active
character pose. Each character root keeps a
legacy `Animation` component, so scripts can still call
`GetComponent<Animation>().Play("<clip name>")`.

Validate the saved lineup contract after rebuilding the viewer:

```bat
validate_resident_character_lineup.bat
```

The scene records its active/transform/profile prefab-instance overrides, so a
later targeted character-prefab rebuild cannot revert one resident actor to a
legacy inactive prefab root. Generated playable prefab templates also keep an
active root, and the Zhuang gacha builder automatically rebinds and validates
the resident scene after regenerating prefab-local file IDs. The current
validation passes all 31 active instances, preserves every instance while
switching, and performs no runtime model load on selection.

The compact right-edge **Recovered state connections** panel derives a button only
when an imported actor has both an exact `_ui_<from>_to_<to>` transition clip
and an exact destination loop loaded on the active `Animation`. Connections are grouped as labelled arrows,
with outgoing connections highlighted from the current settled state. Clicking
one plays the transition once and then hands off to the destination loop; for
example, Da Pan exposes Overview -> Weapon and Weapon -> Overview alongside
Equip, Skill, and Upgrade connections. The current all-roster catalog exposes
the complete source connections across all 31 playable actors. This is a source-clip
pairing boundary: it does not invent a connection when either clip is missing.

Private item/deco visibility is refreshed from the active body clip, helper,
and recovered controller layers after Play/Sample ownership on every Play,
Restart, transition entry, and destination-loop handoff. Selecting an ordinary
body clip also adopts its matching recovered state composition, so users do not
need to switch to the Recovered dropdown to obtain its proven item layers. An
item hidden by the previous clip lifecycle is therefore shown again whenever
its owning clip is replayed instead of appearing only on the first playback.
Confirm generated Wulfa repeat activation and Da Pan button eligibility with:

```bat
validate_character_viewer_state_items.bat
```

The recovered Chen Qianyu and Da Pan Overview clips already animate both hand
IK targets and both deforming hands. The older lab-authored two-bone solve was
overwriting that motion with guessed weights and no source arm pole. It now
defaults off behind the explicitly labelled **Lab IK** control. The original
game's IK consumer, weights, pole behavior, and layer timing are not yet
recovered, so enabling that control remains a diagnostic choice.

The generated viewer scene keeps a minimal hierarchy:

```text
CharacterRecoveryViewerRoot
  Backdrop/
    ReferenceBackdrop
  Characters/ (has CharacterRecoveryActorCatalog)
    <31 active resident actors, horizontal>
  Lighting/
    KeyLight
  MainCamera
  ViewerUI
```

Generated actor materials use the recovered CharacterNPR suite: cloth/body,
skin, hair, eye, and multiplicative overlay-shadow shaders. A lab-local
`HGCompatRenderPipeline` now drives the camera, publishes the recovered HGRP
character globals, schedules the forward/outline and mixed transparent passes, and applies
the recovered post semantics required by the source portrait insertion point.
The viewer enables the source-backed energy, eye, face-highlight, clustered
NPR light-list and light-binning paths. It also enables only the source-closed
CharInfo floor/wall/far-grid presentation allow-list. `SphereOutside`,
`ShadowPlane`, the retail deferred-lighting integration and the retail paired
world-UI depth output remain unavailable and are deliberately not guessed.
This is therefore still a custom SRP reconstruction, not the game's modified
Unity engine or complete HGRP implementation. VFX materials stay on the
existing lightweight VFX path. The project is intentionally in Linear color
space because the original HGRP material/LUT math is linear-light.

The overlay-shadow passes use the exact shipped keep-only stencil state:
material-driven ref 4/20, read-mask 20, and equal comparison. Current original
eye/eye-white/hair-shadow materials disable `ForwardOnly` and serialize
`_EnablePreDepthPass=0`, so the lab does not submit `PREDEPTH`. Instead the
queue-2900 `OVERLAY_SHADOW` member uses `ForwardCharacterOnly` in the ordinary
transparent list. Hash-pinned GameAssembly/HGRP evidence proves that retail
binds the shared scene depth read-only and makes one mixed ECS+SRP transparent
submission using `CommonTransparent|RendererPriority`; the recovered queues
are overlay 2900, hair 2985, and body/cloth 3000. Wulfa and Zhuang Fangyi
eye/brow/iris value 52 maps through read-mask 20 to ref 20, while face/hair
value 36 maps to ref 4. Run
`python tools\verify_face_eye_overlay_chronology.py` to verify the installed
binary, Shader/material evidence, and lab schedule. Same-queue ordering inside
the custom UnityPlayer command and possible runtime IFix replacement remain
open.
Run `python tools\verify_overlay_runtime_inputs.py` for the separate
hash-pinned OverlayShadow DXBC, Halton jitter, TAA pass-order, and clustered
light-input contract. It does not claim IFix history constants or a settled
retail TAA frame. Run `python tools\audit_taau_history_contract.py` for the
source-backed TAAU history/resource ABI: the history-validity gate, 192-byte
constants, persistent dilated depth/motion-vector textures, and
quality-dependent Dilation→MaskDilation→Resolve scheduling. It also verifies
that `HGRenderPathScene` passes its persistent `historySceneColor` into TAAU
and preserves the current output back under that name (or retains the old
history on a skipped frame). Its report is deliberately marked
`source_closed_live_handles_open`; live TextureHandle identities, settled
weights/internal extent, and IFix replacements remain unclaimed.

The selected overlay local-volume term is also active for the isolated
CharInfo rigs. The recovered type-4 Fog consumer joins all 31 source profiles,
266 serialized lights, 40 supported Fog rows, and the exact clustered
membership plus `LightCharacterOnly`/scene-additional-light gates; missing
producer state returns neutral zero occlusion. Run
`python ..\scratch\reverse_engineering\eye_shadow_cluster_visibility\verify.py`.
Arbitrary gameplay light culling and unsupported OBB/cookie/flicker/culling-
distance states remain outside this bounded presentation path.

The playable UI builder embeds all 31 actors as active resident instances in
one horizontal lineup. Model selection moves the camera and swaps the recovered
profile; it does not load, instantiate, destroy, or reactivate another model.
Use the fast render-style scene for ordinary visual iteration.
Game view starts playback automatically when the active actor has a preview
clip. Wulfa prefers `A_actor_wulfa_ui_overview_loop_01` for the reference render
and the batch preview explicitly samples the selected clip before framing, so
the saved PNG does not stay in the neutral bind pose. If a recovered clip causes
mouth, hat, or arm artifacts, adjust `WulfaPreviewClipPreference` or the
`PreviewAnimationSampleNormalizedTime` constant in
`EndfieldManifestCharacterSetup.cs`.

Zhuangfy now has an evidence-backed overview entry controller on her generated
prefab. Selecting/enabling her starts the recovered 11.25-second overview clip
at its original normalized offset, crossfades for about 0.624 seconds at the
original exit time, then enters the exact 3.333333-second hard-wrapped idle.
The component also publishes the original `WeaponHide`,
`MagicaClothWeight`, and `StaticWeaponHide` values plus four entrance-FX
requests through explicit runtime interfaces. The current lab does not yet have
the matching FX assets or Magica Cloth solver consumer.

Wulfa's imported UI overview clips live under:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Wulfa/Animations/
```

Useful overview entries include:

```text
A_actor_wulfa_ui_overview_loop_01.anim
A_actor_wulfa_ui_overview_start_01.anim
A_item_widget_wulfa_02_ui_overview_loop_01.anim
A_item_widget_wulfa_02_ui_overview_start_01.anim
```

If those files are missing, rebuild the canonical UI subset directly:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_playable_characters_ui.bat --actor wulfa
D:\fluffy-dump\unity_endfield_graph_shader_lab\import_playable_characters_ui.bat --actor zhuangfy
```

The recovered manifests contain multiple mesh LODs from the game. The viewer
imports and keeps only `lod0`, the highest-quality model set, so Game view and
Scene view are inspecting the same renderer set instead of stacked lower-detail
variants. Scene view can still look different when Unity's Scene Lighting toggle
is off because the editor substitutes its own preview lighting; Game view uses
the generated `KeyLight`, ambient color, `MainCamera`, and compatibility render
pipeline.

## Material Preview Workflow

The default viewer now binds the recovered HGRP-inspired shaders and keeps the
original material texture/property contracts where the compatibility renderer
can support them. In particular, packed normals stay raw, flattened character LUTs
use no mipmaps, and hair/skin/eye data is not collapsed into Standard material
slots.

The generated render-pipeline asset is:

```text
Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset
```

It uses the original C28M3 `HGCharacterVolume` values where they were recoverable,
including the `_CharacterParams0..15` packing. The installed CharInfo profile
selects `AutoExposureMode.Manual` at exactly `0 EV`, so neutral multiplier `1`
is its deterministic target and its new-camera/settled value. A reused physical
camera can carry a prior current multiplier for its first entry frames because
HGRP `Reset()` does not reseed exposure. Fixed EV remains an explicit diagnostic
override. The older
compatibility tonemap and character-only bloom remain approximations. An opt-in
branch contains the shipped CharInfo `ACES_modified` curve,
a real 1024x32 linear FP16 grading LUT, grading/vignette remaps, and the complete
eight-level high-quality scene-bloom graph. A separate default-off selector
runs HGRP's recovered Auto-mode histogram/pre-exposure state as a renderer
diagnostic; that branch is not selected by the original CharInfo profile. A
strict capture target reproduces the final OETF/dither contract. Interactive
backbuffer format/transfer and any reused-camera entry history remain unknown. The
character-shadow reconstruction is disabled by default. It uses the original
authored sphere bounds, CameraVirtualLight fit, 1024/D16 tile, bias values,
Poisson rotations, and 16-Gather/64-tap receiver. The installed helper now also
closes the managed caster membership that feeds the dedicated atlas:
`FindRenderers` separates ordinary renderers from shadow modes 3/4,
`characterSelfShadowOffLodQuality=2` admits LOD0/LOD1, and
`UpdateShadowRenderingLayer` assigns a live character index only when the
ordinary renderer's fork-specific `m_RealtimeShadowCaster` bit is set. The
current recovered LOD0 manifests intersect that predicate at 151 exact
renderers across 14 actors. Five imported LOD0 rows are explicitly excluded:
two Wolfgd furcards, Aurora and Ardelia fur, and Bounda's shadowless cloth.
The additional selector
`ENDFIELD_RECOVERED_ORIGINAL_REALTIME_CHARACTER_SHADOW_CASTERS=1` switches the
default-off atlas diagnostic to this fail-closed count/path/hash roster.

The 120 exact installed `Shadow_Proxy/SP_Desktop` LOD1 meshes remain useful
scene-shadow evidence, including their bindposes, hierarchy paths, enabled
states, 126 renderer-material passes, Aurora's two-submesh `_lod1_8` fur proxy,
and Wulfa hair-02 cutout. They are not dedicated character-atlas casters:
the original helper assigns modes 3/4 rendering layer 2 and invalid character
index 15. Older proxy-atlas captures are therefore retained as historical
diagnostics, not as the recovered membership contract. The game's
current helper/list path admits 14 active entries even though the retail shader
constant-buffer ABI retains 15 array elements. Single-actor admission is
filtered-list index 0 / rendering layer 256. The binary also closes
priority-descending / instance-ID-ascending helper ordering and the 14-entry
4-column atlas rectangle formula. A second explicit default-off selector now
executes two-actor 2x1, five-actor 4x2, nine-actor 4x3, and
thirteen-/fourteen-actor 4x4 subsets using the retail rendering-layer carrier.
The fourteen-actor reversal moves the layer-2,097,152/slot-13 owner from
Zhuangfy to Wulfa while changing only 45/8.29M pixels. All 14 assignable
slots are GPU-executed. The current installed binary also closes atlas
lifetime: `ReadShadowResult` registers the handle in Deferred Lighting,
Distortion, Fake Planar Reflection, Forward Opaque, Forward, Transparent After
DOF, Transparent, and both One Pass Deferred phases; the graph compiler
allocates at the first valid write and releases after
`max(latest valid read, latest valid write)`. The lab now ends global
publication before returning its temporary atlas to Unity's pool. A fresh
D3D12 run executes the exact 151-renderer managed roster and excludes all five
fork-flagged rows; its image hashes
`1ECCD771D862D1B3827FE6554697CF786A2D1E1AFE4B1CB4E4FC916E5F04713B`.
Against the retained proxy diagnostic, 25,913/8,294,400 pixels change, bounded
to the character band. The retail UnityPlayer now also closes the adjacent
ECS boundary: the character-index query requires `HGRendererComponent`
(component ID 16), injects a `has-none` filter for
`HGUIParticleComponent` (ID 79), and compares the stored entity character
index in all three renderer-family branches reachable by this query. The one
pinned Zhuangfy particle with character index 1 is non-UI and also stores the
realtime-shadow flag, but its exact original `HGRP/Effect/VFXBaseV2` shader
contains four `ForwardOnly` passes and no `ShadowCaster` pass. It therefore
cannot emit atlas depth, and the lab correctly does not add it to the managed
caster roster. The expanded verifier passes 1,499 checks. This proves
pool eligibility timing, not a particular later physical allocation identity.
The live ECS entity census and complete client frame/VFX consumers remain
unavailable; no additional VFX caster participation is claimed beyond the
source-closed negative result for the pinned Zhuangfy particle set.
Downstream screen-space integration remains
unreconstructed, and matched material results remain mixed.

For matched operator-overview renders, the batch path additionally applies the
recovered CharInfo cameras, per-character volume modifiers, fourteen serialized
studio-light records, and CharInfo bloom/vignette/saturation controls. The final
reference frame's possible carried first-frame exposure and the full-scene HGRP
punctual/rim resource set remain unknown. The source-backed selectors now publish the exact
CharInfo main-directional intensity carrier, evaluate an old-CharacterNPR
Default/Fog/shadowless-Rim subset, resolve all nine overview-light followers,
and sort the isolated overview list by the native priority-descending then
camera-distance-squared-ascending rule. The recovered records and implemented
subset stay exact; the older hand-selected compatibility contribution remains
zero by default.

The complete machine-readable classification is
`render_parameter_provenance.json`. Exact original data may be used in the
reference path; image-fit and unrecovered compatibility values are diagnostic
only. Unknown runtime values stay neutral or default-off.

The Wulfa/Zhuangfy material payloads and final active CharInfo overrides are
also regenerated directly from AnimeStudio exports:

```bat
python -B tools\extract_original_render_parameters.py
python -B tools\extract_original_render_parameters.py --check
```

The output is
`Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/character_render_parameters.json`.
It records source/export/raw-data hashes, keeps inactive VolumeParameter values
separate from active overrides, and marks exposure/history, camera-dependent
light direction, irradiance, and quality state as live-only unknowns. The editor
scene builder reads this payload instead of transcribing actor-specific CharInfo
numbers in C#.

### Original Shader Metadata Recovery

The opt-in AnimeStudio shader sidecar path also writes a Ruri-compatible
`<binary>.metadata.json` beside every exported DXBC, SMOL-V, and decoded SPIR-V
blob. It preserves Unity parameter names and the Endfield Vulkan descriptor
set/binding packing. Each metadata record also identifies its serialized
subshader, pass index/name, and enclosing program stage, so a blob from
`RayTracingReflection` cannot be mislabeled as `ForwardLit`. It preserves the
compiled global/local keyword strings, compiler platform, and hardware tier as
well, allowing the exact material variant to be joined instead of guessed.
Normal Story/asset exports are unchanged because the path still requires
`ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS=1`.

Build the local exporter and the lab-local Ruri wrapper from the repository
root:

```powershell
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
dotnet build .\unity_endfield_graph_shader_lab\tools\RuriEndfieldStandalone.csproj -c Release
```

Generate a narrow filter from the installed-game asset map, then run the
original-data shader export:

```powershell
python -B .\unity_endfield_graph_shader_lab\tools\endfield_asset_map_filter.py `
  --name '^HGRP/CharacterNPR_(Skin|Eye)$' --type Shader `
  --output .\scratch\character_skin_eye_shader_filter.json

$env:ANIMESTUDIO_EXPORT_SHADER_BYTECODE_SIDECARS='1'
& .\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe `
  'D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets' `
  '.\scratch\character_skin_eye_shader_export' `
  --game ArknightsEndfield `
  --types Shader:Both --export_type Convert --group_assets ByType `
  --filter_data '.\scratch\character_skin_eye_shader_filter.json'
```

Some Endfield variants omit the serialized binding record for otherwise named
constant buffers. Join only unique, structurally proven SPIR-V UBO matches
before decompiling:

```powershell
python -B .\unity_endfield_graph_shader_lab\tools\enrich_ruri_shader_metadata.py `
  --spirv '<variant>.spv' `
  --metadata '<variant>.spv.metadata.json' `
  --output '<variant>.enriched.metadata.json' --strict

& .\unity_endfield_graph_shader_lab\tools\bin\Release\net10.0\Ruri.ShaderDecompiler.Endfield.exe `
  '<variant>.spv' '<variant>.glsl' `
  --metadata '<variant>.enriched.metadata.json' --format spv --shader-model 50
```

The enricher propagates only structurally unique UBO assignments and refuses
any ambiguity that remains; it does not guess texture, sampler, SSBO, or
runtime producer names. The selected Endfield Vulkan fragments use
`PhysicalStorageBuffer64`, so Ruri correctly falls back from HLSL to readable
GLSL. Combined Unity program payloads can also label both embedded vertex and
fragment snippets with the enclosing program stage. Treat SPIR-V execution
model/reflection as authoritative for the individual snippet; use
`SourcePassName` for the containing render pass.

The same payload now carries `CharInfo_Env.directIntensity=8.631674` and
`directIntensityDividePi=2.7475471`. The runtime reproduces the active native
`LightExtensions` scalar from `directIntensityDividePi * exposure`, clamps its
base to `[0.75,1.25]`, and applies the original dialog/non-dialog overflow
shaping before publishing the character main-light intensity. CharInfo's source
directional RGB is white, so the generic native HSV correction is an identity
for this environment rather than an omitted fitted color transform.

The Wulfa/Zhuangfy overview-light records are regenerated and checked in the
same data-first manner:

```bat
python -B tools\extract_original_operator_lights.py
python -B tools\extract_original_operator_lights.py --check
```

This produces `operator_lights.json` from the original Light, Transform, and
`HGAdditionalLightData` objects and validates all fourteen native NPR-packed
vectors. The editor imports that payload instead of maintaining hand-copied
arrays, including each serialized priority and the full `rotation_xyzw`. The
runtime derives Spot right/up/forward from that source quaternion instead of
inventing roll from a forward vector. Selection is PPtr-locked to the
direct child named `light_overview`;
this prevents an equal-count page such as Zhuangfy's `light_document` from
silently replacing it. The payload also joins all nine original
`CharInfoLightFollower` components. Wulfa resolves five pose-driven lights and
Zhuangfy four against each sampled/live actor's unique `Bip001` or `Head_Local`
node using the two recovered native transform modes. Missing or duplicate bones
are hard failures, not static-position fallbacks. After follower evaluation,
the runtime rig uses the recovered native priority/distance order rather than
the prefab/controller order. Equal priority and distance remain intentionally
unspecified because the original comparator has no stable tie-break.

A conservative source-backed part of the original punctual/NPR loop is
available only when both base selectors are enabled. Exact isolated-rig
32-pixel XY/2048-slice Z membership has an additional independent selector:

```text
ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1
ENDFIELD_RECOVERED_CLUSTERED_NPR_LIGHT_LOOP=1
ENDFIELD_RECOVERED_LIGHT_BINNING_MEMBERSHIP=1
ENDFIELD_RECOVERED_ISOLATED_PUNCTUAL_SOFT_SHADOWS=1
# optional exact source quality profile: 512 or 1024 (captured RTX 5080 default)
ENDFIELD_RECOVERED_PUNCTUAL_SHADOW_TILE_RESOLUTION=1024
```

For the selected old CharacterNPR variants this evaluates eight Default and two
Fog lights on cloth/hair, plus the two shadowless Rim lights on both materials,
punctual GGX on cloth, and Eye's exact diffuse-only Default/order-sensitive Fog
subset; Eye Rim is exactly zero. Default uses the exact
`saturate(NdotL+0.5)` angular carrier; hair also uses the selected primary
shifted-strand punctual specular/ramp lobe. Double-sided Wulfa hair now applies
the original front/back face sign to its diffuse and geometry normals, aliases
the signed diffuse normal for non-split specular materials, and remains Hair
material mode 1 on both faces. Hair Rim now consumes a dedicated character camera-depth
prepass, the exact screen-depth edge, projected-light side mask, tint, alpha
carrier, and invalid-cache radial self-shadow. The selected
zero-metal/no-bump/no-weather face subset now evaluates its exact Default, Fog,
and both Rim responses: Wulfa 8/8 rows and Zhuangfy 6/6 rows. The Skin Default path reconstructs the complete
SDF/character-shadow/scene-shadow `skinNprDiffuse` selector, its radial/SDF
angular normal, `F0=0.04*_Specular*sdfMask.g`, and original GGX roughness;
the shadowless Rim uses the original projected silhouette/SDF shape, radial
self-shadow, and source diffuse-albedo tint. The atlas-dependent Rim row opens
only through the exact isolated row-4 slot, face-count, source-index, and ready
guards; otherwise it remains fail-closed. When the membership selector is enabled, the runtime
constructs the recovered three-`float4` Point/Spot
descriptors in the same priority/distance order as the shading arrays, runs the
verified `LightBinningXYCS`/`LightBinningZCS` formulas, and intersects word zero
at each supported character fragment. On the D3D lab backend, the shipped cross-compile
wrapper makes raw fragment `SV_POSITION.w` the linear-depth input for both Z
membership and Hair Rim depth-edge evaluation; the apparent reciprocal in the
Vulkan body is canceled by the wrapper's preceding reciprocal. Disabling that selector preserves the earlier
direct eight-light loop. The source-backed path never reads the older hand-authored
compatibility scales. Exact equations, source hashes, and the remaining
resource boundary are recorded in
`scratch/clustered_npr_light_loop_recovery_20260713.md`,
`scratch/operator_light_runtime_attachment_recovery_20260713.md`, and
`scratch/operator_light_follower_integration_20260713.md`, plus
`scratch/hair_depth_rim_punctual_shadow_contract_20260713.md`,
`scratch/hair_secondary_lightlist_recovery_20260713/recovery_note.md`,
`scratch/skin_face_punctual_exact_20260713/recovery_note.md`,
`scratch/skin_shadowless_rim_exact_20260713/recovery_note.md`,
`scratch/punctual_soft_shadow_producer_recovery_20260713.md`,
`scratch/native_lightbinning_formula_evidence_20260713.md`, and
`scratch/light_binning_implementation_plan_20260713.md`. The isolated Unity
D3D11 verifier reported zero XY, Z, and fragment-consumer word mismatches on an
RTX 5080; its result is
`scratch/light_binning_reference_vectors_20260713/gpu_verification.json`.

The resolver-side binding is now closed one step further. Installed
`GameAssembly` evidence fixes `_LightBinningConstants` at 48 bytes: four ints
followed by eight floats, with 32-pixel tiles, 2,048 Z slices, camera near/far,
and a native-cull survivor count capped at 32. The runtime can publish that
exact ABI under the default-off
`ENDFIELD_RECOVERED_LIGHT_BINNING_CONSTANTS=1` selector, but only when the
isolated Overview rig supplies a source-closed count; otherwise it binds 48
zero bytes and clears `_EndfieldRecoveredLightBinningConstantsReady`. Run
`verify_recovered_light_binning_constants.bat --all` to check the 12 words,
field offsets, and failure diagnostics on D3D11 and D3D12. The verified Wulfa
fixture has 8 isolated lights and 120x68 tiles at 3840x2160. It is not the
retail room census: the native whole-scene candidate/survivor list and final
`lightCount` remain open. Installed Gacha Lua now proves that Zhuangfy selects
the six-light `light_overview` character group, initializes its four
`CharInfoLightFollower` components, and activates the 12-light
`SceneLight6Rarity` room group. The exact known serialized candidate union is
therefore 18 lights (3 type 0, 15 type 2), with no authored cookies and one
character-light shadow request. Run
`python tools\audit_gacha_light_population.py --check` to validate the pinned
Lua/layer data, tables, prefabs, Timeline/ACL pose inputs, group membership,
and native follower-method evidence.
The same audit now also pins the native normal candidate core. The shipped
Gacha route has `useFallbackLightCulling=false` and `0 x 0` occlusion
dimensions. Read-only installed-client registry values independently store
`3840x2160` in Unity and game settings. At that selected 16:9 aspect, the
hash-pinned native AABB, authored OBB, point-sphere, and spot-cone paths admit
exactly 11 room rows; only `Spot Light (20)` is rejected. Installed layer data
fixes the recursively assigned Gacha layer at 30. Identity placement, exact
native follower equations, and the original entrance/loop ACL streams admit
all six character rows across all 844 decoded QVV frames; both root-motion
streams are constant and remove to identity, with no mapped muscle lanes. The
exact known authored contribution is therefore 17, including its internal
priority/distance order. Other display aspects, runtime/custom carry-in, the
target-frame pointer/count, whole-list order, and final `lightCount` remain
open, so those 17 rows are not the complete retail survivor array.
Offline IL2CPP/xref recovery now fixes the handoff precisely:
`LightCullResult` is `visibleLightsPtr + visibleLightCount`; its only direct
producer is `HGCullingSystem.CullLights`, both GameAssembly call sites belong
to `HGCamera.DoECSCulling`, and both pass `maxCount=256` before `SetupState`
filters native types 0/2. A targeted AnimeStudio InitBundle extraction now
closes the installed Windows desktop `PunctualLightMaxCount` at 256; native
`SetupState` sorts priority descending and then squared camera distance
ascending before taking `min(survivors, cap)`. The equal upstream/settings
caps prove that the settings layer cannot truncate this result a second time.
The maintained audit now verifies the current GameAssembly call registers and
return copies plus the UnityPlayer candidate gates directly. It also hash-pins
the candidate-pointer vector conversion at `0x180543CE0`: allocation is
`inputCount * 0x94`, and the exact source-to-row projection is recorded for
the 148-byte `VisibleLight` rows. The enclosing `CullLightsInternal` wrapper
is hash-pinned as well, including the `viewHandle == -1` zero-result path,
hidden-sret pointer/count publication, manager retention-vector append, and
local-vector cleanup. It closes the 16-byte `LightCullResult`
layout and the consumer's `VisibleLight` stride, including type `+0x00`,
priority `+0x70`, and world position `+0x74`; future capture can therefore
reject truncated rows deterministically. It now
accepts a detached, build-pinned JSON artifact through
`python tools/decode_light_cull_capture.py capture.json --output decoded.json`;
the decoder validates the pointer/null rule, count cap, exact raw-row length,
the converter-written zero at `VisibleLight+0x84`, and decodes the source-closed
`finalColor`, `specularIntensity`, and `localToWorldMatrix` fields without
attaching to the retail process. Matrix columns 2 and 3 are also emitted for
the source-backed `GetForward`/`GetPosition` b31 inputs. Converter-unwritten
fields such as ScreenRect are intentionally not inferred.
It now
also pins internal call 3304 from the 16-argument `AddCullViewByMatrix` binding
through six-plane extraction and the scheduled view constructor. The physical
camera's `cullingMask` lands at view `+0x4`; the squared
`cullingViewScreenSizeMin` lands at `+0x18` and is zero on the installed desktop
default route. Native candidate evaluation tests synchronous visibility bit 0,
then mask-enabled bit 0, then `view.cullingMask & candidate.layerMask`.
`sceneCullingMask` is forwarded but the complete hash-pinned constructor does
not read its slot. Internal call 3315 now closes the next dispatch boundary:
normal views select the exact six-plane AABB predicate, while
`cameraType == 0x80` selects the exact sphere/distance predicate; neither reads
view `+0x18`. The complete hash-pinned scheduled batch core likewise contains
no direct scalar load from view `+0x18`. Its separate `state +0x180` input is
proven to be squared `parentLODBias` and is only forwarded through the batch
core and child-job thunk, so it is not this view threshold. The installed
CullView-named internal-call surface is now closed end to end:
`AddCullViewByPlanes` shares the same scheduled constructor, dispatch passes
the `manager+0x38` view-pointer array directly into the complete per-view loop,
and that loop, both selected predicates, `GetCullingViewFence`, and
`ResetCullViews` never read `+0x18`. `AddCullChildViewByPlanes` appends a
separate `0xE8`-byte record under `manager+0x58`. The installed
`screenSizeMinimumSquared` word is therefore write-only on this hash-pinned
surface; there is no post-dispatch packet copy or threshold gate. Independent
retail serializer/deserializer code fixes the
formerly generic 28-byte record as `HGTreeRenderer`, nested under
`HGTreeInstance.renderers`: `batchKey`, `renderFlags`, `mesh`, `material`,
`subMeshIndex`, `lodScreenSizeMaxSquared`, and `lodScreenSizeMinSquared`, with
the LOD pair at `+0x14/+0x18`. A dedicated 729-entry HG internal-call table
pairs `HGTreeRender.CreateRendererList` index 564 with `0x1801D9D10` and
`RegisterTreeBatchGroup` index 567 with `0x1801DA040`. The first reaches
`0x18107EE40 -> 0x181080730` and selects runtime jobs
`0x181067A70/0x181064190`; the second reaches registration core `0x181086050`.
Loader `0x1810C5F30` now closes that transform: `count` is followed by a
`0x18`-stride runtime-record array with capacity 1/2/4/8/16/32, then an 8-byte
LOD pair array at `4 + 0x18*capacity`. It passes each serialized record's
`batchKey`, mesh/material PPtrs, and `subMeshIndex` to `0x181086050`, stores the
returned 16-bit handle with `batchKey/renderFlags`, and copies the LOD max/min
floats verbatim to the pair array. Dedicated HG entries 568/569 are
`UnregisterTreeBatchGroup` and `UnregisterTreeBatchGroupWithHandle`; cleanup
`0x1810BCE00` reads record `+0x04` as `batchKey` and `+0x02` as handle before
calling `0x181087E00`, closing the blob lifecycle. The formerly
undifferentiated tail is now split precisely. The serialized `renderFlags` at
record `+0x08` is mutable: particle setup variants
`0x1810416A0/0x181041870/0x181041920/0x1810419D0` advance from blob `+0x0C`
(record `+0x08`), replace the word with bit 20 at the exact `0x18` stride while
selecting modes 2/3/4/5, and scheduled callback `0x181067A70` ORs it into its
render flags. The resource-to-record mapping is now corrected by accounting
for the 4-byte blob header. Hash-pinned `HGMeshRendererData` serialization
binds `m_Materials/m_Meshes/m_ShadowProxyMeshes` to native
`+0x58/+0x78/+0x98`, and independent initializer `0x181088D80` resolves them
through singleton Material/GeometryHandle maps at `+0x90/+0xA0`. Its blob
writes `+0x08/+0x0C/+0x10` are therefore runtime record `+0x04/+0x08/+0x0C`,
exactly matching availability writers `0x181157760/0x181159010` and cleanup.
Thus record `+0x0C` is specifically the `m_ShadowProxyMeshes` GeometryHandle:
owner handle `+0x18` supplies it at `0x181157AD1/0x1811592A0`, cleanup clears
it at `0x18115C110`, and callback read `0x181064B73` consumes it in a combined
masked filter. HG internal-call entries 300/301 name
`HGGeometrySystem.GetGeometryHandle/GetMesh`; builder `0x18108B1C0` closes bits
0..23 as the slot index and bits 24..31 as the 8-bit generation incremented at
slot `+0x06`. Installed `HGTreeRender.CreateRendererList` metadata names the
upstream UInt32 fields `renderFlagsMask/renderFlagsValue/lightModeMask`.
Binding `0x1801D9D10`, core `0x18107EE40`, and scheduler `0x181080730` preserve
them into descriptor `+0x40/+0x44/+0x48`; callback `0x181064190` receives
descriptor `+0x04`, so its `+0x3C/+0x40/+0x44` reads are those exact fields.
GeometryHandle is intentionally folded into the HGTree renderFlags comparison,
not a standalone filter bitfield. The current `GameAssembly.dll` direct-call
census closes all seven managed callers: three punctual-shadow paths, Deferred
PreZ/GBuffer, ASM static shadows, and both directional CSM builders. Deferred
uses mask/value/light-mode `0x500/0x100/0x1`; ASM uses
`0x01080100/0x01080100/0x400`. Punctual paths add Opaque to the hash-pinned
`GetECSRenderFlags` static/dynamic truth table. Both directional builders use
identical mask/value `m_cascadeRenderFlags[i] | 0x02080100`; the metadata-backed
four-entry initializer yields
`0x02180100/0x02280100/0x02480100/0x02880100`. Record `+0x10` is not seeded by a Mesh map;
common Renderer
state synchronizer `0x180432CD0` maintains that separate property-flag word at
blob `+0x14` while preserving mask `0xFC07FBFD`.
Dedicated HG
internal-call entry 204 is
`HGFactoryRenderManager.SetEntityEnabledLightModes_Injected`; wrapper
`0x1801EB940` reaches `0x1810D9110`, which writes the supplied
`enabledLightModes` value to record `+0x14` for the entire `0x18`-stride family.
Installed IL2CPP metadata closes the argument as `UInt32 lightModeMask` and
`HGShaderLightMode` as 31 named pass bits spanning `0..30` plus `None=0`.
Hash-pinned `Beyond.Gameplay.Factory.PerDrawPassConfig` code parses its narrower
gameplay pass enum into that mask and `Apply` calls the managed wrapper at
`0x1869F3904`. Native initialization is closed as well: the Renderer base
constructor defaults field `+0x250` to `0xFFFFFFFF`; builders
`0x18042A130/0x18042AB50` copy it directly to every record `+0x14`, while
generic path `0x180BCCB60 -> 0x180BCB760` carries it through constructor input
`+0x20`. The two HGTree renderer-list callbacks store the requested mask at
job `+0x44` and test it against a separate `0x60`-stride renderer-entry word at
`+0x1C`. Builders `0x18109BE90/0x18109C9D0` now close that word independently:
they clear it, query the renderer material/shader against the exact 31-name
`HGShaderLightMode` pass table, and set every supported bit. It is therefore a
shader-supported-pass mask, not a projection of runtime record `+0x14`.
All 53 direct calls to renderer-blob lookup `0x180424C30` are pinned and
partitioned into 44 exact `0x7F00` calls across 41 entry CFGs plus nine
other-family calls. Width-aware cross-hot/cold CFG taint finds no exact-path
record `+0x14` read, non-stack record-base pointer store, record-base return,
or address-taken stack spill. Its seven exact-result stack stores are local
spills/reloads or reused slots (four `blob+0x00`, three `blob+0x04`); none
becomes a nested job descriptor. The six direct `blob+0x04` call escapes split
into three zero initializers at `0x181CA0040`
and three calls to classifier `0x181131FC0`, which advances by `0x18`, reads
only record `+0x00`, and tests renderer-entry `+0x18/+0x26`. One additional
`blob+0x00` tail path, `0x1810CE280 -> 0x181C9F9A0`, copies the full layout
with byte count `4 + 32*(familyMask>>8)`: count, `24*capacity` runtime records,
and `8*capacity` LOD pairs. It carries `+0x14` verbatim between exact-family
blobs but does not interpret it. HG Factory internal-call entries 198/215 name
the current/obsolete `CreateBatchedEntities` routes; their hash-pinned copy
cores `0x1810CE510/0x1810CEBC0` both call this helper. A third exact
component-K / ray-tracing-K grouping consumer at `0x18112A790` reads only
record `+0x00/+0x04/+0x08/+0x10`. Callback A's apparent `+0x14` read at the
same stride is also excluded: accessors `0x181038D70/0x181038DE0` derive its
base from ECS archetype component columns 127/126, and the value is consumed
as a float. The remaining HGTree renderer-list variants do not expose another
route: internal-call entries 564/565/566 (default, child-view, and PreZ) reach
cores `0x18107EE40/0x18107FCF0/0x181080190`, all converge on scheduler
`0x181080730`, and select the same two already inspected callbacks. The actual
consumer is in the separate GPU-driven renderer path. HG internal-call entries
151/152 and 164/165 identify `GPUDrivenRendererV1/V2` default/PreZ routes;
their four cores build `0xA0`-byte jobs, whose callbacks carry requested light
modes at job `+0x54` and select the `0x7F00` ECS renderer column.
Representative V1/V2 default/PreZ consumers
`0x1810E87E0/0x1810E9AD0/0x1810F58F0/0x1810F6BC0` form record cursors at
base `+0x0C` or `+0x10`, read dword `+0x14`, and advance by `0x18`. They OR
this `enabledLightModes` word with candidate-pass `+0x18` and derived flags
before job `+0x48/+0x4C` mask/value filtering; job `+0x54` is independently
intersected with candidate-pass light modes at `+0x1C`. This closes the native
consumer and separates it from the shader-supported-pass mask for all four
routes. This loader blob is separate
from the LOD jobs' component-bit-67 24-byte state. That record stores LOD count
at `+0x00`, desired/resolved/history indices at `+0x01..+0x03`, pending and
available masks at `+0x04/+0x05`, a reserved/alignment word at `+0x06`, a
64-bit renderer-readiness set at `+0x08`, and eight cumulative renderer-range
endpoints at `+0x10..+0x17`. All 25 direct calls to the archetype/indexed
accessors and their 21 logical caller bodies are pinned; control-flow dataflow
finds no independent `+0x06/+0x07` access or writer on that surface. Writer
`0x1810842E0` closes its request, completion, and unload transitions. Indexed
accessor `0x1811648A0` reaches the same state per entity; writer `0x181159010`
closes the initial LOD0 completion/fallback transition. With only LOD0 pending,
it writes indices `0/0/0`, masks `0/1`, and a readiness mask derived from the
companion renderer/subresource count; otherwise it writes sentinel `8/8/8`
and clears readiness. It does not write the LOD count or cumulative ranges.
Installed scripting registration `0x1807EEEE0 -> 0x1807EC5E0` directly binds
`::Scripting::UnityEngine::HyperGryph::ECS::HGTreeComponentProxy` to native
`HGTreeComponent` in `UnityEngine.HyperGryph.ECS` from
`UnityEngine.HGGraphicsModule.dll`. Dedicated HG internal-call index 712,
`EntityManager.GetOrRegisterEntityTypeImpl_Injected` at `0x1801E0D90`, closes
how numeric component IDs become archetype masks: `mask[id >> 6]` receives bit
`id & 63`, making ID 67 high-qword bit 3 (`0x8`). Current metadata method
478429/token `0x06000279` maps `HGTreeComponent.get_id` to GameAssembly
`0x184DBCEC0`; the exact body is `mov eax, 0x50; ret`. `HGTreeComponent` is
therefore ID 80/high-qword bit 16 (`0x10000`), proving that component 67 is a
separate, still unnamed native LOD-state component. The managed
`RenderObjectLODInfoComponent.get_id` body independently returns 6, excluding
that similarly named type too. The complete installed metadata/codegen surface
contains 30 `UnityEngine.HyperGryph.ECS` `Int32 get_id` declarations, 30 module
pointer slots, and 29 concrete constant-return bodies; none exposes ID 67.
Component 67 therefore has no managed name on the shipped surface and must be
resolved from the remaining pure-native registration data. Raw UInt64 field
defaults in the installed metadata close the separate serialized
`StreamingComponentType` values as
`HLODGroup = 1<<11`, `HGTree = 1<<41`, and `Count = 43`. HG internal-call
entry 677 reaches the native converter registration path: it constructs 43
slots at `0x308` bytes each, selects the slot with `bsf(componentTypeMask)`,
requires a non-empty component list, and requires Transform first. Those are
serialized converter bits rather than ECS component IDs, so component 67
remains a native LOD-state type-identity problem. The native lifecycle
registry is now exact as well: each `ECSEntityType` owns a `0x288`-byte record
containing ten `0x40`-byte `EntityTransition` callbacks from `+0x08`.
Installed metadata names all ten slots. The complete 105-call installer census
partitions between two `StreamingGameplayManager` constructors (52/53 calls),
and both install identical component-67 maps for Render/type 0 and
MergedRenderCollider/type 9. Component 67 is touched only at
`UnloadedToLoading`, `LoadingToLoaded`, `UnloadingToUnloaded`, and
`LoadingToUnloaded`; waiting slots 2/7 are unbound. The managed script replaces
only Water/type 1 and WaterDecal/type 13, leaving those native maps active.
The teardown callbacks now close the adjacent resource-capacity family and
mask semantics. They intersect the archetype high qword with `0x7F0`; the full
serialized corpus makes that selection one-hot with exactly one companion ID
68..73 per component-67 archetype. Each uses an 8-byte header plus 40-byte
rows containing three source pointers and three resource handles, with
capacities 1/2/4/8/16/32; bit 74 is admitted by code but absent from the
corpus. `UnloadingToUnloaded` walks `pending|available`, releases all three
handles, clears the mapped Material/main-Mesh/shadow-proxy runtime words, and
zeros both state-mask bytes; type 9 adds merged-render-collider cleanup.
Shared `LoadingToUnloaded` walks pending ranges only, releases owner handles,
clears pending byte `+0x04`, and preserves available byte `+0x05` and mapped
runtime words. Transition-1 loading is now exact too. Dedicated
`HGLODStreamingSystem` calls 273..291 bind `enableLODStreaming` to state `+0x38`,
keep-last-resource to `+0x39`, `LODCrossFadeConfig` to `+0x3C`, and squared
HLOD unload distances to `+0x474`; the remaining entries name dirty-distance,
reset, status-query, and pending/load/unload-count controls. Installed IL2CPP
field-offset rows close
embedded config `c1` at `+0x18` and
`RenderObjectLODInfoComponent.lodCenter` at `+0x00`. Type 9 requests the
terminal LOD when streaming is enabled and all LODs otherwise. Type 0 requests
its single row directly when streaming is disabled; its enabled branch gates
on squared `lodCenter`-to-`c1` distance and an unnamed component-75 HLOD-level
byte. Both callbacks acquire Material/Mesh/shadow-proxy-Mesh and append exact
24-byte source/AssetType/handle descriptors at transition context `+0x58`.
The acquire core already performs resource-manager bookkeeping. Outer task
`0x181172DD0` combines context `+0x50` deferred entries and `+0x58` direct
descriptors into a request batch; poller `0x181172750` retains state 0,
publishes ready state 1, and removes state 2 without publishing a resolvable
relation. The installed `Streaming load asset %lld failed` resolver path and
component fallback close state 2 semantically as load failure. Once pending is
empty, the task projects batch views through context
`+0x60/+0x68/+0x70` and invokes `LoadingToLoaded`, connecting acquisition to
the pinned Material/Mesh/shadow-proxy runtime writers and LOD availability
updates. Its four direct calls are also closed: one in the grid-load state
driver and three entity-set branches in the Streaming gameplay batch update.
HG internal-call 614 now names the batch driver
`StreamingGameplayManager::Tick_Injected`; its native core directly enters the
batch update. Entry 615 names a separate `TickResource_Injected` core with no
direct call to the component-67 transition task or request poller. Independently,
a registered native callback slot closes the grid path through manager, scene,
grid, grid-load driver, and transition task. Its exact lifecycle phase/thread,
the stripped state-2 enum symbol, and native component names remain open. The
managed host is also closed upward: virtual `GameSceneManager.Tick` calls
`BaseGameScene.Update -> DynamicStreamingScene.Update -> TickSystem`.
`TickSystem` runs `TickResource_Injected` first, then dispatches valid-system
virtual Tick slot 19; `_InitTickStatus` registers `DynamicSceneEcsSystem`, whose
slot-19 body invokes `Tick_Injected` with a `0x100`/`0x800` batch limit. The
virtual caller/thread above `GameSceneManager.Tick` remains open, and the method
name `Update` is not treated as proof of Unity main-thread execution. The
complete hash-pinned `StreamingSceneManagerScript..ctor` binds only bits
12/14/15/19/25/29/32/33/40 through the managed Mono-converter path; HGTree
bit 41 is absent. The complete installed-VFS corpus of 117
`HGMeshRendererData` objects contains 1,449 valid ECS descriptors and no ID
67. The compact source/hash/count inventory is
`Generated/OriginalData/CharInfoPresentation/hgmesh_renderer_data_component_inventory.json`.
These results exclude the managed HGTree delegate and generic serialized
constructor/renderer-data routes without naming the remaining native producer.
The installed UnityPlayer native descriptor table additionally identifies
`HGTree=0x2C9CB981` and `HGTreeData=0x59383C91`. A controlled complete
StreamingAssets map/export scan uses all 117 `HGMeshRendererData` identities
as its positive gate but finds zero top-level objects of either HGTree type.
The compact census is
`Generated/OriginalData/CharInfoPresentation/hgtree_native_serialized_type_census.json`;
the static top-level object surface is excluded. The proprietary `.bytes`
surface is now bounded by the exact managed `StreamingSceneV2.Create` bridge,
dedicated HG icall 621, native loader `0x18117B200`, path builder, request
callback, and custom interleaved-token LZ4 decoder. The 83 serialized
`StreamingMapConfig` roots match 83 `StreamingChunkInfo` files with no gap. A
complete scan of 51,012 main Streaming payloads decodes 3,088,714,060 bytes and
3,084,834 union records; no tag-1 component vector contains HGTree bit 41 or
HLODGroup bit 11. Native tables close tag 1 as MonoEntity, tag 2 as native
ECS, and tag 3 as Proxy. Installed metadata closes all `ECSEntityType` and
`ProxyEntityType` byte values, plus all ten `EntityTransition` byte values.
Native callback-slot registration proves component 67 is shared by type 0
`Render` and type 9 `MergedRenderCollider` across transitions 1/3/6/8. The
full payload census
contains 34,672 Render records in 1,384 files and 2,576,964
MergedRenderCollider records in 4,720 files, closing native entity ownership
without inventing a standalone component name. StreamingSceneV2 root fields
6/7 pair native entity-ID groups with archetype descriptions. Their 8-byte
descriptor rows are `(int16 componentId, int16 elementSize, uint32 auxiliary)`;
component 67 is exactly `(67,24)`, followed by serialized component initial
data. Hash-pinned native copier `0x1801F95E0` copies each
`entityCount*elementSize` slice directly into ECS storage. Across all 83 map
scopes, the 1,230,041 distinct component-67 IDs exactly equal the distinct
type-0/type-9 owner set. All 1,305,818 occurrences initialize LOD count 1..6,
state bytes `8/8/8/0/0`, the `+0x06` reserved word to zero, zero readiness,
and one of 102 cumulative renderer range patterns; repeated map/entity records
are byte-identical. This closes
the LOD-count/range producer to original game-binary data while leaving the
standalone native component name open. All
1,576 DynamicStreaming init/stream payloads contain only tag-2 records and no
component entry. Dynamic `fb_main` is a separate managed gameplay schema: its
457 files contain 2,828 `FBDynamicSceneTreeRootComp` rows, while
`EDynamicSystem.Tree=11` and `EDynamicSceneData.TreeRootComp=64` keep that
destructible-tree normal-model path distinct from both serialized HGTree bit 41
and ECS component 67. The compact evidence is
`Generated/OriginalData/CharInfoPresentation/streaming_scene_v2_payload_census.json`.
Native entity-type
registration core `0x1801FAEC0` consumes 8-byte rows `(int16 id, uint16 size,
uint32 cumulativeOffset)`, places component storage after byte 8, and exposes
per-rank size/offsets at archetype `+0x42/+0x44 + 8*rank`. No installed-code
immediate encodes `(67, 24)`; the recovered StreamingSceneV2 descriptor/blob
path supplies that row and its initial LOD values. Writer `0x181157760`
also closes a second direct-availability initializer: it marks either every LOD/subresource
available or only the terminal LOD and the exact readiness range selected by
the cumulative endpoints. It consumes the serialized LOD count/endpoints
rather than inferring them.
Dispatch segment `0x181079FB1` selects the
LOD variants. The direct path selects
`minSquared < distanceSquared <= maxSquared`; the scaled path tests
`(viewFactor*instanceScale)/max(0.0001,distanceSquared)` against the same
exclusive-lower/inclusive-upper interval after ArtTag scaling. Builder
`0x18106EAD0` creates the exact `0xC30` payload; its 64-byte dispatch packet is
a payload pointer followed by the 56-byte `LODCrossFadeConfig`, so packet
`+0x3C/+0x3E` are `enableDither/lodBias`. Installed
`HGCullingSystem.get/set_parentLODBias` and `Get/SetArtTagLODBias` close the
squared parent bias and both 256-entry ArtTag encodings. Nonzero view
`lodBias` multiplies both copied tables by `(1 + lodBias/255)^2`.
`HGLODStreamingSystem.Get/SetArtTagLODStreamingOffset` owns the separate
256-int table copied to payload `+0x82C`; every LOD job adds that signed ArtTag
offset to the selected index and clamps it to `[0,lodCount-1]`. The
former index-10320 and `0x180175A10 -> 0x180A5E320`
virtual-slot interpretation is retracted because it crossed the HG table
boundary into unrelated Animator code. The complete `0x4E1`-byte UnityPlayer
candidate core is hash-pinned by the maintained audit, including the native
gate/sort/output-cap surface. The component-67 native type name and target-frame
survivor rows remain explicit boundaries. The complete installed CullView
census found no separate `sceneCullingMask` consumer: the field is forwarded by
the constructor but not read by the scheduled loop, either selected predicate,
fence/reset lifecycle, child-view path, or a post-dispatch packet copy.
Run `python tools\audit_light_cull_cap.py --check` to validate the pinned
binary, settings, IFix, route, cap, and ordering evidence. Closing the retail
value still requires an explicitly authorized target-frame capture of that
pointer/count and array; unrelated live native lights are not inferred from
the authored room JSON, and no retail-process attachment or injection was
used.

Binding 37 has a similarly narrow recovered transport. Installed
`HGLightCookieManager` code creates 32 zero atlas records plus 32 zero matrices,
then uploads exactly 512+2,048 bytes. Missing cookies map to index `-1`, and the
selected resolver samples `_LightCookie` only for nonnegative indices. Set
`ENDFIELD_RECOVERED_LIGHT_COOKIE_DATA=1` (or pass
`-endfield-recovered-light-cookie-data`) to publish the exact all-zero
`_LightCookieData` only for the source-closed Wulfa/Zhuangfy isolated Overview
lists; every cookie-bearing or mismatched frame clears
`_EndfieldRecoveredLightCookieDataReady`. Run
`verify_recovered_light_cookie_data.bat --all` for the 640-word D3D11/D3D12
transport check. This does not recover a non-empty retail cookie atlas.

The normal-mapped body Skin branch is separate from that face reduction and is
source-gated to exactly `M_actor_wulfa_body_01` (Material PathID
`7152188194418193687`) and `M_actor_zhuangfy_body_01` (Material PathID
`-6228499253811589790`) on Skin shader PathID `4484747192473637154` with
`_DIFF_RAMP_ON _NORMALMAP _SHADOW_LUT_TEX`. Every other Skin material keeps
`_RecoveredSkinBodyForwardVariant=0` and clears the exact-body texture aliases.
The selected branch ports the packed R*A/G normal, point-family biased Base and
Bump samples, point-clamped flattened ShadowLUT with manual B-slice
interpolation, body grazing tint/F0, the distinct body Default/Fog/Rim material
mode 5, and the source split between unscaled ambient main-light color and the
native-intensity-scaled direct copy. Verify the source identities, generated
materials, texture copies, response values, and 99/61 body bindpose capture
gate with:

```bat
python tools\verify_body_skin_forward_recovery.py
```

After an installed-game refresh, verify the current AnimeStudio source
boundary separately with:

```bat
python tools\verify_current_character_npr_skin_export.py
python tools\verify_current_screen_shadow_binding_boundary.py
python tools\verify_current_screen_shadow_resolve_export.py
```

This current-export audit requires the targeted `CharacterNPR_Skin` shader
export under `scratch/animestudio/body_skin_sidecar_refresh/`. It validates
the current shader/material identities and ForwardLit keyword census without
reusing the older no-screen sidecars or claiming retail frame parity.
The screen-shadow binding audit is independent of that scratch export: it
records that the current binary Skin consumer reads retail `_ScreenSpaceShadowMask`
R/G, while the lab producer remains content-invalid and Skin stays on the
source-shaped retail branch with its keyword disabled until canonical
publication is recovered; the diagnostic branch remains available for
comparison.
The Skin export audit also pins the current binary equations: the directional
R selector honors `DirectionalShadowParams.x` and `CharacterParams1.z`, while
G feeds the character-shadow alpha product and minimum-shadow path.

The resolve export audit is the producer-side complement. It pins the original
`HGRP/ScreenSpaceShadowResolve` AssetMap identity and its
`ScreenSpaceShadowResolve_Character` pass: packed GBuffer0 selects one of 15
character shadow records, the projected point uses the original light-facing
bias, and `_CharacterShadowmapTex` is filtered with 16 `GatherRed` depth
comparisons before the result is written to mask G. This is source-backed
producer semantics only; the lab keeps the runtime publication fail-closed
until the character atlas upload and target-frame state are validated.

The lab resolve now carries that source shape into its default-off attachment:
it binds the same-frame PreGBuffer selector/normal lanes, chooses the scalar or
15-slot character atlas transform, applies light-facing bias, and executes the
 16-tap `GatherRed` depth filter for mask G. The producer checks camera, atlas,
and GBuffer ownership before drawing. Its scene and character passes retain
the original stencil split (`Ref 4`, `ReadMask 7`, `NotEqual`/`Equal`), while
`contentValid=false` still keeps
the retail consumers disabled until complete scene-R and deferred-GBuffer
ownership are recovered.
The directional CSM bridge also publishes the installed CharInfo environment's
serialized `csmIntensity=1.0` gate (the source of
`DirectionalShadowParams.x`) and applies it after CSM composition, matching
the original final blend. Unity `Light.shadowStrength` is a separate field;
this remains diagnostic-only.

In the corrected 3840x2160 controlled A/B, the only change is the exact body
selector. On pixels changing by more than 1/255, reference MAE moves
74.222 -> 74.040 for Wulfa and 60.286 -> 59.078 for Zhuangfy. This is a modest
component result, not whole-frame parity: Wulfa's stronger >4/255 subset is
1.880 MAE farther, while Zhuangfy's is only 0.193 closer. Native retail texture
compression/mip texels, live packed weather state, screen-shadow branch choice,
general nonzero character-rim/subsurface state, the interleaved retail light
list, and Zhuangfy's unsupported shadow caster remain unresolved. Exact metrics
and limitations are in `scratch/body_skin_forward_20260714/` and
`memory/character_render_and_animation_recovery.md`; no screenshot fitting
was used. If cached mesh assets were interrupted during a rebuild, recover only
their original geometry, weights, and bindposes with
`rebuild_character_recovery_scene_original_meshes.bat` before trusting a render.

The punctual-shadow selector is independent of membership but requires the
clustered NPR light loop. It publishes only the isolated source-proven soft Rim
caster: Wulfa Spot slot 40, or Zhuangfy Point faces 40..45. The producer uses
the original B=512/B=1024 `6B x 4B` D16 layout, reversed-Z depth-zero clear,
native projections and point bases, 2-pixel scissor, raster/receiver bias,
CullOff actor `ShadowCaster` passes, and the optimized nine-comparison receiver.
The atlas keeps Point RT metadata; the shader reproduces the original separate
bilinear comparison sampler from four raw D16 reads. If actor/light identity,
D16 reversed-Z support, the atlas, or the recovered actor-caster contract is
unavailable, no slot is published: the two soft rows stay zero while the two
shadowless rows retain their original radial fallback. This is an isolated
actor implementation, not a claim about the full client's visible-light slot
identity or frame-specific caster population.

For quick material checks:

1. Open the project with `open_character_recovery_lab.bat`.
2. Press Play and keep the Game view visible. Use the runtime UI for Wulfa or
   Zhuangfy and camera selection.
3. Select a generated material asset under
   `Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/<Actor>/Materials`.
4. Trace a mismatch back to its exact Material JSON/PathID or runtime producer,
   then refresh the generated payload. Do not promote an image-fit material
   value into the setup script.

Use the shared-viewer render to produce comparison PNGs and validate animation
playback. Active recovered shaders live under
`Assets/EndfieldGraphShaderLab/Shaders/Recovered/`; older experimental shaders
remain useful as comparison/reference assets.

The cloth/hair diffuse recovery has global, environment-selected audit modes;
they do not rewrite generated materials and never change the mode-0 default:

```text
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=0  current full compatibility render
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=1  current diffuse only
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=2  earlier source-shaped diffuse only
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=3  mode 2 plus current downstream lobes
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=4  exact-SPIR-V live-shadow diffuse only
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=5  mode 4 plus current downstream lobes
ENDFIELD_RECOVERED_DIFFUSE_AUDIT_MODE=6  character-shadow receiver scalar
```

Modes 4/5 keep scene directional shadow and the dedicated character shadow as
separate inputs, matching the recovered original branch structure. For branch
diagnostics only, `ENDFIELD_RECOVERED_SHADOW_BLEND_OVERRIDE=0..1` forces the
view-dependent/ramp endpoint or an intermediate blend; unset it (or use `-1`)
for the live value. These modes do not recover the original CSM/ASM resolve or
the full current 14-active-entry character atlas schedule (the shader ABI still
reserves 15 entries), so they are comparison tools rather than new defaults.

The recovered CharInfo post stack is also an isolated, default-off A/B:

```text
ENDFIELD_RECOVERED_POST_SEMANTICS=0  default compatibility post
ENDFIELD_RECOVERED_POST_SEMANTICS=1  shipped ACES_modified/FP16 LUT/vignette/scene bloom
```

Mode 1 is evidence for shader behavior, not a calibrated preset. The original
CharInfo volume independently selects auto-exposure enum value `1`, which is
`Manual`, with zero EV compensation. It does not schedule the histogram kernel.
The default-off real-frame histogram implementation described below is an HGRP
Auto-mode diagnostic only; fixed-EV renders also remain diagnostics. Formulas and
exposure evidence are under
`scratch/charinfo_post_recovery/`; combined bloom/LUT renders are under
`scratch/charinfo_post_recovery_mip_pyramid/` and
`scratch/charinfo_post_exposure_sweep/`. None replace the canonical renders.

For calibration-only fixed-exposure probes, use the Unity menu entries under
`Endfield > Character Recovery Lab > Render Recovered Post Exposure Sweep`.
The default sweep is `0, 0.5, 1, 1.5, 2 EV`; override it with a comma-separated
`ENDFIELD_RECOVERED_POST_EXPOSURE_SWEEP`, or set one render with
`ENDFIELD_RECOVERED_POST_EXPOSURE_EV`. These values are perceptual probes, not
claims about the original frame's adapted exposure. The older sweep found a
coarse shared visual match near `+1.0 EV`, but no sweep value was promoted. Use
the source-backed live path when temporal exposure behavior is under test.

Camera and lighting defaults are near the top of
`EndfieldManifestCharacterSetup.cs`:

```csharp
PreviewFieldOfView
PreviewReferenceVerticalCoverage
PreviewReferenceTopBias
PreviewKeyIntensity
PreviewAmbientColor
PreviewBackgroundColor
PreviewKeyDirectionToLight
```

These fields remain compatibility/viewer controls, not authoritative production
parameters. Change them only for an explicitly labeled diagnostic. A production
correction must come from serialized game data, recovered native behavior,
compiled shader constants, or captured original runtime state.

### Safe Iteration Loop

```text
Open fast scene -> inspect mismatch -> trace original source -> regenerate/check payload -> rebuild fast scene -> render validation preview
```

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\build_fast_render_style_viewer.bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_fast_render_style_preview.bat
```

After changing material import semantics, reapply all recovered serialized
properties and feature toggles in place without rebuilding meshes or animation:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\refresh_recovered_character_materials.bat
```

This re-applies the recovered import profile to every generated texture and
preserves/verifies both texture and material GUIDs. Generated `_p<hash>` names
are classified from the canonical name before the hash: `_N`, `_HN`, `_P`,
`_M`, and `_ST` are linear data; diffuse/ramp maps remain sRGB; RD/RS lookups
remain single-mip. Texture presence is only a fallback when the original
material omitted a feature float; it no longer forces disabled emotion,
emission, SDF, ramp, or packed-map branches on.

Matched 3840x2160 operator-reference renders are available with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_runtime_reference_wulfa.bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_runtime_reference_zhuangfy.bat
```

They write `scratch/runtime_reference_wulfa.png` and
`scratch/runtime_reference_zhuangfy.png`. The supplied front screenshots are
not used by the default original-data render path. The recovered dolly endpoint
positions and FOV remain unchanged. Neutral settled orientation is evaluated
from each original LookAt target through the centered, zero-damping Cinemachine
Composer; the serialized virtual-camera quaternion is only its pre-pipeline
authoring state. Two legacy visual helpers are preserved as explicit
default-off diagnostics:

```text
ENDFIELD_REFERENCE_FITTED_COMPOSITOR_TRANSLATION=1
ENDFIELD_REFERENCE_APPROXIMATE_OPERATOR_LIGHTING=1
```

The first applies screenshot-measured registration offsets. The second enables
the lab's unrecovered punctual/rim light equation with its historical
compatibility scales. Neither is evidence of original game behavior.

Offline Lua and prefab recovery now prove that CharInfo creates the actor at
local zero under an identity `CharContainer`, and parents each operator's
authored overview camera/light roots there at local zero. The serialized
`overviewImgOffset` moves only a decorative background-sprite attachment.
Accordingly, no extra actor compositor translation is part of the recovered
overview path, and the screenshot-measured selector above remains default-off.
With the source Composer correction, the 4K comparison needs only a near-
identity residual registration: Wulfa native scale is `0.9992` with roughly
`(+9,-26)` pixels translation, and Zhuangfy scale is `1.0059` with roughly
`(0,+12)` pixels. Those residual measurements are diagnostics, not parameters
applied by the renderer.

The exact CharInfo exposure profile plus HGRP's 16-bin Auto-mode histogram
kernel, center-metering equation, CPU reduction, and target/adaptation equations
can be regenerated from original exports with:

```bat
python -B tools\recover_charinfo_exposure.py ^
  --profile-json ..\scratch\charinfo_post_recovery\export\MonoBehaviour\HGAutoExposure_p76C3DC144F2EB560.json ^
  --compute-json ..\scratch\charinfo_post_recovery\histogram_shader_export_json\ComputeShader\ComputeShader#0_p9AFAC58F7D1FCEE1.json ^
  --output-json Assets\EndfieldGraphShaderLab\Generated\OriginalData\RenderParameters\charinfo_exposure_state.json
python -m unittest unity_endfield_graph_shader_lab.tools.test_recover_charinfo_exposure
```

Run the unittest from the repository root. The generated state is under
`Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/`.
`_ExposureParams` follows the original `(exposure,0,0,0)` layout. The original
CharInfo branch is active Manual mode: target
`clamp(exp2(0),exp2(-4),exp2(4)) = 1`, with 20/20 clamped adaptation. A newly
constructed HGRP camera starts with current and target both `1`; `HGCamera.Reset`
does not change either value. Therefore neutral is exact for a new or settled
CharInfo camera. Only the initial current value of a reused physical camera and
its delta-time convergence sequence are history-dependent.

For renderer research only, the separate HGRP Auto-mode histogram branch can be
enabled with both:

```text
ENDFIELD_RECOVERED_POST_SEMANTICS=1
ENDFIELD_RECOVERED_LIVE_CHARINFO_AUTO_EXPOSURE=1
```

It uses the recovered 16-bin center-weighted compute histogram, one async
readback at a time, exact tail reduction/clamp, per-camera current/target
history, and 20/20 adaptation before Uber. The compatibility selector name is
retained, but this is a counterfactual Auto-mode diagnostic: do not enable it
when reproducing the original CharInfo profile.

The diagnostic is runtime-validated. With the exact imported overview lights
and live follower bones, 180-frame diagnostic captures converged to `0.448361`
for the Wulfa lab frame and `0.418806` for the Zhuangfy lab frame. Those values
are not CharInfo exposure values: they came from forcing the unselected Auto
branch and must not be used to match the supplied references. See
`scratch/live_charinfo_auto_exposure_recovery_20260713.md` and
`scratch/live_charinfo_auto_exposure_validation_20260713.md` for the historical
diagnostic.

The matching offline final-chain contract is checked from the repository root:

```bat
python -B scratch\test_recover_charinfo_final_chain.py
python -B scratch\recover_charinfo_final_chain.py ^
  --output scratch\charinfo_final_chain_recovery.json --check
```

The shipped CharacterNPR pass divides by the current camera exposure and Uber
multiplies by the same value before grading. `ACES_modified` is baked into the
linear grading LUT; Uber then applies the IEC sRGB OETF and deterministic RGB
dither into a linear `R8G8B8A8_UNorm` target. FinalPass is an alternative raw
copy path, not a pass after Uber. A default-off capture-only path now enables
the exact one-encode output contract only when both selectors are set:

```text
ENDFIELD_RECOVERED_POST_SEMANTICS=1
ENDFIELD_RECOVERED_LINEAR_UNORM_FINAL_TARGET=1
```

It rejects null, sRGB, mismatched, multisampled, layered, or mipmapped targets,
writes one linear `R8G8B8A8_UNorm` temporary, and presents it with a same-format
`CopyTexture`. Interactive screen presentation remains blocked because the
Unity backbuffer contract is not pinned. The original runtime-created camera's
initial state is source-proven as alpha disabled, no custom FrameSettings
override, Postprocess enabled, and Windows TAAU Quality. That is startup/fallback
evidence, not the current settled request: the read-only installed-client save
joined to the original quality tables selects 3840x2160 Very High, DLSS in DLAA
mode, native render scale, and sharpness `0.0`. Its serialized fallback TAAU
rows contain `0.3`, but the selected Quality resolve does not consume that
field. CharInfo's standalone `HGSharpen` component is inactive; Uber's separate
`PERFORM_SHARPEN` branch exists, while the final settled `_PPSharpen` remains
unobserved after possible late mutation. The lab therefore uses no speculative
positive sharpening and does not claim either a converged TAAU or DLAA path.
Temporal parity additionally requires capability/fallback state, history,
jitter, accurate motion vectors, masks, internal extent, and reset/fast-
converge state. Later live camera mutation and `targetTexture` remain unknown.
See
`scratch/charinfo_preexposure_final_chain_20260713.md`,
`scratch/linear_unorm_final_target_recovery_20260713.md`, and
`scratch/charinfo_camera_target_state_recovery_20260713.md`, plus
`scratch/charinfo_taau_sharpen_contract_20260713.md` and
`memory/character_render_and_animation_recovery.md`.

### Default-off PreGBuffer Diagnostic

The recovered PreGBuffer producer boundary has a separately named, default-off
sidecar diagnostic. It allocates the source-backed `D32_SFloat_S8_UInt`
depth/stencil target, exact `A2B10G10R10_UNormPack32` A/B targets, an
`R8G8B8A8_SRGB` material/color C target, and an `R32_SFloat` depth copy; it
then draws the recovered character PreGBuffer
passes after a conservative opaque-scene depth helper. This approximates the
shipped CharInfo `DefaultDeferred` order: generic ECS/ordinary opaque PreZ in
the earlier DepthPrepass, then character ECS/outline/SRP PreG in GBuffer on the
same `sceneDepth`. Only recovered opaque queues through `GeometryLast` produce
PreG; observed queue 2985/3000 layers remain Forward-only consumers. Enable it
only for a capture or GPU audit:

```powershell
$env:ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC = '1'
$env:ENDFIELD_RECOVERED_PREGBUFFER_DIAGNOSTIC_OUTPUT = `
  'D:\fluffy-dump\scratch\pregbuffer_capture'
```

The equivalent standalone switch is
`-endfield-recovered-pregbuffer-diagnostic`, with
`-endfield-recovered-pregbuffer-diagnostic-output PATH`. The explicit editor
check is **Endfield > Character Recovery Lab > Verify Recovered PreGBuffer
Diagnostic**. Its JSON and four PNGs validate the packed character selector,
Y-up oct normal/family tag, raw R32 depth, and low-three stencil bits. This
sidecar does not define, enable, or feed the screen-space shadow mask and is not
a render-style parity claim. Current source evidence, GPU results, and blocked
coverage are recorded in
`memory/character_render_and_animation_recovery.md`.

The current Skin DXBC `PreGBuffer` fragment has also been re-decompiled from
the refreshed AnimeStudio sidecar. The original pass writes five MRT lanes:
zero/unused `Target0`, motion-vector payload `Target1`, packed 10-bit
selector `Target2`, octahedral normal `Target3`, and material/color payload
`Target4`; it uses `DepthCharacterOnly` with stencil `Ref 36 / Always /
Replace`. The maintained diagnostic binds selector/normal A/B and now writes
the source-shaped material/color payload to diagnostic C, with a byte readback
gate. The paired source vertex DXBC is also pinned: `TEXCOORD_3` carries
current clip x/y/w, `TEXCOORD_4_1` carries previous skinned/object clip x/y/w,
and the source binds both non-jittered current/previous camera matrices,
previous camera position, and `unity_MatrixPreviousM`. Because previous skin
deformation is a separate input, motion vectors remain unpublished rather than
being replaced with a camera-only approximation. C is not yet consumed by
retail deferred lighting, so this evidence closes one producer input without
claiming a complete retail GBuffer.

The independent source `HGRP/Lit` `HGBuffer` audit now pins the same history
shape in the deferred character path: current clip x/y/w is carried through
`TEXCOORD_5`, previous clip x/y/w through `TEXCOORD_6`, and `Target1.xy` uses
the signed fourth-root delta blended by the source motion-validity mask in
`Target1.z/w`. The current SphereOutside frame sidecar intentionally keeps a
neutral SceneMV and remains non-presented until previous deformation and
target-frame state are recovered.
The audit also pins the remaining source MRT payload: MRO/porosity and
packed-flag equations in `Target2`, sampled mask and packed flags in `Target3`,
and tint-blended base colour with zero alpha in `Target4`. This closes the
source equations only; the runtime sidecar still does not publish those lanes
through the retail deferred resolver.

The Eye `PreGBuffer` vertex variant confirms the same 6044-byte DXBC and
decompiled vertex program as Skin (Eye uses source pass index 1; Skin uses 3),
so the previous-deformation ABI is shared across these two CharacterNPR
families. Its fragment preserves the same five MRT lanes while setting the
oct-normal alpha lane to `0.7` (Skin uses `0.4`).

The current `CharacterNPR_Hair` export confirms the same 6044-byte vertex
program at source pass index 3. Hair is not a fragment alias: its five-MRT
fragment sets oct-normal alpha to `1.0` and writes sampled hair color scaled by
the serialized per-material tint words. The source identity and these anchors
are included in `verify_current_character_npr_skin_export.py`.

The current generic `HGRP/CharacterNPR` export is pinned separately as well.
Its base `HG_ENABLE_PER_OBJECT_MV` + `SRP_INSTANCING_ON` PreGBuffer vertex is
byte/text-identical to Skin/Eye/Hair, but its fragment keeps the sampled-color
× tint `Target4` lane while writing `Target3.w = 0.0`; it must not be replaced
with Hair's `Target3.w = 1.0` variant. The AssetMap row is PathID
`-7822190029627442914` at offset `185104054` in the current `19F0903A...`
source chunk. These anchors are covered by the same verifier.

The separate canonical-depth owner is also default-off. Unlike the sidecar, it
binds two exact `A2B10G10R10_UNormPack32` PreG colors together with the same
stencil-bearing camera depth attachment consumed by the immediately following
opaque Forward draw. It resets recovered opaque character materials to `LEqual`
before validation and restores their preserved source `_ZTest` only after the
PreG command buffer executes. Any missing pass, unsupported opaque family,
alpha-tested generic depth, attachment capability, or selector-capacity failure
stays at `LEqual`.

```powershell
$env:ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER = '1'
$env:ENDFIELD_RECOVERED_PREGBUFFER_DEPTH_OWNER_OUTPUT = `
  'D:\fluffy-dump\unity_endfield_graph_shader_lab\scratch\character_recovery\preg_depth_owner\gpu_validation'
```

The equivalent command-line switch is
`-endfield-recovered-pregbuffer-depth-owner`. The explicit combined owner and
packed-pixel check is **Endfield > Character Recovery Lab > Verify Canonical
PreGBuffer Depth Owner**; it also requires the diagnostic variables above. The
exact Unity `2022.3.62f3` D3D12 check confirms Last Rite cloth 03 transitions
from compatibility `LEqual` to source `Equal` only after owner submission. This
does not claim retail DrawECS/GPU-driven ordering, live IFix replacement state,
or the complete proprietary GBuffer consumer.

### Default-off CharInfo Screen-shadow Producer/Consumer Diagnostic

The lab now has an exact, focused one-actor path for the active CharInfo
screen-mask state. It borrows the validated PreGBuffer depth/stencil, selector
and oct-normal attachments plus the exact single-actor `CameraVirtualLight`
atlas, clears one full-size `R8G8_UNorm` target to `(1,1)`, and writes raw
character attenuation only to G where `(stencil & 7) == 4`. CharInfo disables
the scene directional term, so R stays neutral; the generic quarter-resolution
scene target and H/V blur are not allocated by this focused diagnostic.

```powershell
$env:ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_DIAGNOSTIC = '1'
$env:ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_DIAGNOSTIC_OUTPUT = `
  'D:\fluffy-dump\scratch\screen_shadow_mask_capture'

# Separate opt-in that feeds the validated mask to Forward consumers.
$env:ENDFIELD_RECOVERED_SCREEN_SHADOW_MASK_CONSUMER_DIAGNOSTIC = '1'
```

The command-line selector is
`-endfield-recovered-screen-shadow-mask-diagnostic`, with
`-endfield-recovered-screen-shadow-mask-diagnostic-output PATH`. Run
`verify_recovered_screen_shadow_mask_diagnostic.bat` for the explicit D3D12
batch audit. The current RTX 5080 capture validates exact RG8/D32S8/A2B10/R32
formats, 246,290 slot-0 character pixels, no writes outside character stencil,
an invariant R byte of 255, zero selector/normal/depth/reprojection mismatches,
and a byte-identical repeated static mask. It writes RG, G-only, and mismatch
PNGs beneath `scratch/screen_shadow_mask_diagnostic_20260713/`.

The producer writes raw character attenuation to G. Original D3D11 and Vulkan
resolves do not apply `Light.shadowStrength` at this boundary; the shared
receiver is therefore invoked with strength one, while the observed lab light
value is recorded only as provenance. The independent consumer selector is
`-endfield-recovered-screen-shadow-mask-consumer-diagnostic`; it selects a
compile-time lab variant that loads R/G once for Skin, Cloth and Hair, loads R
only for Eye as the original selected Eye variant does, and removes the direct
character-atlas solve from those binaries. The diagnostic uses only
`_EndfieldRecovered*` resources and its own keyword; it does not bind
`_ScreenSpaceShadowMask` or publish `HG_ENABLE_SCREEN_SPACE_SHADOW_MASK`.

An authorized standalone Wulfa D3D12 RenderDoc capture proves that fourteen
main Forward draws execute the exact consumer binaries and bind the same
1280x720 `R8G8_UNORM` mask: Cloth 6, Skin 2, Hair 4, Eye 2. Matched Wulfa and
Zhuangfy image checks remain mixed by material, so this path stays default-off.
The current two-RGBA16F D3D12 audit independently reconstructs the screen solve
with zero failures and at most one UNorm8-code difference. It also proves that
sharing PreG depth removes 1,008 family mismatches, while 428 remain to be
classified by stable draw ID and `SV_PrimitiveID`; same family is not same
owner. Generic scene R, native ECS equal-depth order, multi-actor slot ordering,
and production-wide promotion remain unrecovered. Full evidence is in
`memory/character_render_and_animation_recovery.md`.

Use `render_recovered_screen_shadow_scalar_audit.bat <wulfa|zhuangfy> <0|1>`
to isolate the no-screen direct receiver (`0`) or recovered screen G (`1`)
before material lobes. The direct control uses the original VFACE/
`_BackFaceNormalFlip` geometry-normal sign; the two modes are still different
original contracts and are not expected to be pixel-equal.

### Exact Cubemap and Default-off Material Diagnostics

Recover and import the exact CharInfo character-reflection cubemap with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\recover_charinfo_cubemap.bat
```

The same command now imports two exact linear unsigned BC6H assets. Both are
`128x128`, six faces, and eight mips. The character-reflection
`T_hdri_reflection_char_01` payload has SHA-256
`898FF663C8D447456666612E55697F7AECDE13C03B19B74F9DF5B73735E2C9DF`;
the visible CharInfo sky `T_hdri_006` payload has SHA-256
`070FD7C568B9DB9C1CFC936E3FE081465807E761D28090761C92F6F94444214E`.
The importer validates all 48 face/mip slices without decoding, reorientation,
color conversion, or mip regeneration. `scratch/cubemap_dependency_recovery/
recovery_note.md` and `scratch/charinfo_dynamic_lighting_gap_20260713/
recovery_note.md` record the installed-game CAB/PathID evidence and
reproduction details.

On an operator-reference camera, `ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1`
also selects the recovered physical-HDR sky source. The camera clear mode is
Sky; `T_hdri_006` uses the serialized tint `(0.8207547, 0.8207547,
0.8207547, 0.5)`, rotation `294` degrees, and native
`float32(preExposure * skyboxBrightness) = 1.0`. The neutral
`ReferenceBackdrop` remains available as a presentation/UI background but is
disabled before source-camera culling, so it cannot enter the raw HDR target or
the optional `ENDFIELD_RECOVERED_LIVE_CHARINFO_AUTO_EXPOSURE=1` Auto-mode
diagnostic histogram. With the source
selector off, the existing SolidColor/backdrop compatibility behavior is
unchanged.

The sky/background mutation is camera-scoped. The pipeline snapshots the
camera clear state, `RenderSettings.skybox`, and presentation renderer before
culling, submits the selected camera, then restores all three in a `finally`
block. A later SceneView, UI, or other unmarked camera therefore cannot inherit
the physical-HDR sky or a hidden backdrop. The sky vertex writes exact D3D
reversed-Z far depth (`SV_Position.z = 0`) and uses the API-equivalent
`z = w` on non-reversed-Z targets.

Generated shared/fast viewer scenes serialize an inert source-sky marker and
its material/cubemap references. The generic fast capture-player build repairs
that marker and requires `T_hdri_006` before packaging, so launching the player
later with `-endfield-recovered-source-energy-core` cannot find the shader or
cubemap stripped. Running `recover_charinfo_cubemap.bat` also repairs already
generated viewer scenes while importing the exact payload. These references do
not enable the source path by themselves.

This is the exact cubemap/tint/exposure/rotation carrier. A native gate audit
proves that CharInfo disables atmosphere fog, height fog, volumetric fog, flow
noise, and fog-LUT baking. Although a physical-atmosphere configuration is
populated, the active cubemap renderer never binds its `_SkyViewLut`; only the
inactive procedural-sky path consumes that LUT. Keep those fog families reset
or no-op. The visible gray grid/circle is a separate CharInfo presentation
scene, not atmosphere.

Original prefab dependencies identify five enabled layer-13 presentation
renderers: `SphereOutside`, `CharFloorEffect`, `GeoSphere001`, `ShadowPlane`,
and `GridDeco/Far`. They use the recovered CharInfo outside, radial floor,
wall, character-shadow-receiver, and far-grid materials. `CharInfoPanel` is a
later `ScreenSpaceOverlay` Canvas. The lab now imports their exact raw mesh
channels (including required secondary UVs), four native BC7 textures, the
original DXT1 MRO payload, five serialized materials, transforms, renderer
state, and selected shipped DXBC evidence into
`Generated/CharInfoPresentation/RecoveredCharInfoPresentation.prefab`.

The full selector remains default-off and fail-closed. For `SphereOutside`, the
selected `HGRP/Lit` HGBuffer stages, HighEnd attachment formats, 14-pass/640-
variant deferred family, seven native draw entry points, exact pass-0 original
SPIR-V fragment, five named/four debug-anonymous constant buffers whose roles
are now all closed, all 25 sampled texture
roles, and the light/reflection-probe binning buffer are pinned. A default-off
source-specialized five-MRT diagnostic
also validates the exact sphere/material packing on D3D12. It uses a
deterministic packing-audit projection and `ZTest Always`; it is not the
original depth owner or deferred resolve. Exact SPIR-V/DXBC comparison
role-identifies unnamed binding 32 as `_LightBinningConstants`. Its exact
native 48-byte field layout/upload and a default-off, fail-closed isolated-count
Unity publisher are now source-closed; all 12 words read back bit-exactly on
D3D11 and D3D12. The retail whole-scene cull survivors and final `lightCount`
are still not captured. Exact original cross-shader layout identifies b34 as
the 11,440-byte `ShadowData`; the selected resolver reads only PunctualLight
rows `c64..c400`. The native four-section transport, atlas sizing/format,
cache allocation, point/spot matrix construction, PCF_3x3 parameters,
strength fade, normalized rects, and texel size are binary-source-closed. The
default-off lab publisher now consumes the source-backed punctual producer in
the same frame: Wulfa row 4 fills spot slot 40, while Zhuangfy row 4 fills
point slots 40..45, with the matching `6144x4096` D16 atlas. Full
`_ShadowData` and the D3D11 `EndfieldCB5` 401-vector prefix read back
bit-exactly on D3D11/D3D12; all unowned rows remain zero and missing
prerequisites fail closed. Wulfa active/control beauty remains bit-identical.
Because every isolated light is `CharacterOnly`, the selected original
consumer exits before reading b34 or `_PunctualLightShadowTexV2`; this closes
transport and same-frame ownership, not pass 0. Run
`verify_recovered_deferred_shadow_data.bat` to repeat the source audit, GPU
probes, spot/point frames, beauty control, and failure gate. General-scene/
static-cache rows, retail physical-resource identity and atlas pixels, runtime
IFix/setting overrides, non-punctual sections, and a binding-compatible pass-0
implementation remain open.
Binding 37 now has its native
`HGLightCookieManager` initialization,
32-record atlas/matrix layout, exact 2,560-byte upload, and `-1` no-cookie guard
closed. A default-off publisher emits the exact all-zero buffer only for the
source-closed Wulfa/Zhuangfy isolated Overview lists; all 640 words read back
bit-exactly on D3D11 and D3D12. Any cookie-bearing light fails closed because
non-empty retail atlas allocation, pixels, transforms, and settled whole-scene
values remain open. Exact original `ScreenSpaceShadowResolve` metadata identifies b38 as
the 3,568-byte `HDPunctualLightCharacterShadowData` layout. Its installed
`HGHDPLSCharacterShadowManager` owner, static storage, per-frame resets, push-
pass packing, and selected resolver access are now pinned. `FrameSetup` clears
all 56 character-index/channel pairs before candidate processing; the selected
fragment reads only each pair's `.y`, so an inactive frame provably chooses the
punctual-atlas fallback. This is not a byte-exact zero-buffer fixture: matrices
and params are persistent, atlas/global values are frame-derived, and the
callback requests `0xDE0` bytes while writing the reflected final float4 at
`+0xDE0`. Installed `UnityPlayer` recovery now proves that `CBHandle.size`, the
serialized command, and global shader state all retain the logical `0xDE0`
size. The ring keeps that length after 16-byte rounding but aligns allocation
starts to `0x100`, so the next allocation begins at `0xE00` and the final CPU
float4 is isolated in inter-allocation padding. The recorded target forces
Direct3D 11; the installed backend converts `0xDE0` to 222 constants and rounds
the `PSSetConstantBuffers1` range to 224 constants / `0xE00` bytes. The c222
tail is therefore shader-visible on the target path. Publication remains
fail-closed only for settled active values and their matching resources. The
same native path now closes all six `HGSettingParameters` HDPLS offsets and the
current constructor defaults: enabled, atlas height 2048, reduced screen-space
resolution enabled, and zero depth bias/normal bias/softness. With
`S=max(256,hdplsAtlasHeight)`, the atlas is `2S x S`; the default is `4096x2048`
with a `4x2` tile grid through eight requests or `8x4` above eight. Each active
params row is its normalized tile `xyxy`; atlas texel size is
`(1/(2S),1/S,2S,S)`, global params are `(softness,0,0,0)`, screen-space
positions are `float4(HGSharedLightData.worldPosition.xyz,0)`, and both channel
and bit selectors have exact native formulas. The installed unpatched
`GetShadowParamsFromCharacter` path is now closed too: it treats
`Bounds.extents` as a bounding-sphere radius, aims from the light position at
the bounds center (falling back to the light rotation below a `1e-5` direction
epsilon), builds `TRS(lightPosition,rotation,one)`, and derives a `0.1..179.9`
degree cone from `2*asin(radius/distance)`. `FrameSetup` feeds this result and
the light near/far/guard values through the already closed reversed-Z
`ExtractSpotLightMatrix` / `GetShadowTransform` path, stores the matrix by
request index, and forwards the HDPLS depth/normal bias to the caster pass.
Resource recovery now distinguishes the request-gated `2S x S` D16
`_HDPLSTex` caster atlas from the reduced/full-size RGBA8
`_HDPLSScreenSpaceShadowMask` consumed by deferred binding 22. Their
RenderGraph dependencies and global publication are closed; inactive frames
clear all selectors and bind white to both slots, so stale resources cannot
escape. The generated CharInfo IFix report is refreshed with
`tools/refresh_installed_ifix_patch_state.py` from the installed Persistent
`DAFE52C9` overlay. The current overlay decodes to 32 targets (86,926-byte
`Gameplay.Beyond.patch.bytes`) and still replaces neither `0x877` nor `0x890`
owner method, closing the current on-disk branch choice; future/network
patches remain a version boundary. Run
`tools/verify_installed_ifix_patch_state.py` after refresh. Live
bounds/light/settings values, resulting active rows/selectors, unused
persistent rows, atlas texels, and resolved RGBA pixels remain capture-only.
Run `tools/refresh_ifix_deferred_reports.py --check` to verify that the two
deferred-render contracts project the same current IFix summary; its refresh
mode changes only those projection fields and preserves report formatting.
The remaining
16 texture names are now pinned from their original sampling behavior and the
hash/offset-pinned installed IL2CPP shader-property table: low-resolution
directional shadow/ramp, HDPLS, punctual atlas, cookie, multiscattering LUT,
three A/B irradiance clipmap pairs, VisibilitySH RT/log LUT, reflection-probe
oct array, and integrated fog scattering. The exact installed CharInfo prefab,
priority-30001/30000 global VolumeProfiles, and priority-600 environment phase
are also hash-pinned. They prove that wetness and volumetric-fog texture
sampling are disabled in the selected original fragment, that cloud shadow and
ASM are disabled, and that the character ignores directional shadow, while the
environment reflection map, sky cubemap, and character cubemap remain live.
The installed deferred binder closes the disabled wetness resource as Unity's
built-in white `Texture2D` whenever its render-graph handle is invalid. The
installed volumetric binder closes the fog-disabled resource as
`HGVolumetricFogUtils.volumetricBlackTexture3D`; its creator constructs an
exact 1x1x1 black `Texture3D` with numeric `TextureFormat` 48
(`ASTC_4x4` in the lab's pinned Unity 2022.3.62f3 assembly), no mip chain,
then calls `Apply(false, true)`.
The retail capsule-shadow pass also closes the `_VisibilitySHRT` producer
descriptor: camera-sized or signed half-resolution, bilinear/clamp
`R16G16B16A16_SFloat`, no mip chain, and no random write. Its active render
function binds `_LogSHLutTex`, `_ABLutTex`, and the produced handle; the
empty/disabled function publishes `Texture2D.blackTexture` as
`_VisibilitySHRT`. That black texture is branch-specific, not permission to
neutralize a live CharInfo capsule route. The exact shipped LUT payloads are
also recovered through `HGRenderPipelineRuntimeResources`: `VisibilitySHLut`
PathID `8323377478838034894` and `VisibilityABLut` PathID
`2892350180982884757`. Both are 256x1 `RGBA32`, Gamma, one mip,
bilinear/clamp, with their exact 1,024-byte RGBA payloads pinned in
`Generated/OriginalData/CharInfoPresentation/Textures/`. The installed
capsule route is now pinned separately in
`scratch/character_recovery/visibility_capsule_runtime/`. Wulfa and Zhuang
each serialize an enabled `HGCapsuleShadowHelper` with ten enabled
VisibilitySH capsule candidates and `m_interactionOnly=0`; unpatched
`OnEnable` enqueues the helper and binds every candidate. UnityPlayer caps the
render list at 128, culls 52-byte internal records, and copies a 48-byte
`pa/pb/dir` payload. Its native component writer computes
`fullHeight=max(height,2*radius)`,
`halfSegment=0.5*fullHeight-radius`, then writes the two world endpoints with
radius/full-height in `w` and the normalized composed local-`+Y` direction
with clamped `[0.01,2]` intensity in `w`. The active render lambda calls
`HGDrawMeshInstanced` with exact `HGRP/VisibilitySH` pass 2: additive
`One One`, `ZTest Greater`, `ZWrite Off`, `Cull Front`, and stencil
`Ref 4 / ReadMask 7 / NotEqual`. The original D3D11 producer bytecode,
128-entry constant-buffer ABI, fixed SH constants, and LUT sampling algorithm
are pinned. The settled CharInfo `PassInput.enabled` value, current posed
record values, view-cull survivors/order, and publication remain open.
The live irradiance route is the V2 manager, not the legacy
`HGIrradianceVolumeManager.GetActiveIV` selector. `HGRenderPipeline.Render`
calls `HGIrradianceVolumeManagerV2.PipelineUpdateV2`; native V2 update always
receives `m_defaultIV`. V2 `m_gachaIV` only gates update-center selection and
does not replace the rendered object. The complete pinned installed Lua block
independently confirms that CharInfo does not call the old gacha-IV lifecycle:
among 1,290 successfully decoded files from the 1,291-file block, only
`LuaSystem/GachaSystem.lua` calls `CreateGachaIV`/`DestroyGachaIV`, and
`Phase/CharInfo/PhaseCharInfo.lua` contains no irradiance-volume call.
The V2 binary audit also closes the six active A/B clipmap descriptors and
publication order. A textures are 128x64x128
`B10G11R11_UFloatPack32`; default-quality B textures are 128x64x384
`R8G8B8A8_UNorm`. All are random-write point/repeat `Tex3D` resources with one
mip, named `ClipMapA/BLod{0,1,3}`. A missing native object publishes the same
1x1x1 zero `UnityDefault3D` resource to all six globals. The installed
non-IFix V2 path is now closed further: its constructor initializes all three
path fields to `System.String.Empty`; `StreamingInNewMapV2` sets
`m_exportpathV2 = indexRootPath + "/aiTest/index.bytes"`; and that suffix has
zero matches in the complete 224-file primary-plus-fallback IV VFS inventory.
Neither installed IFix, a direct managed call, nor the 1,290 decoded Lua files
replace or invoke that path. `ReloadIndexFileV2` can still pass an arbitrary
path through `SetMap`, so indirect/native invocation remains a runtime boundary.
Four exact shipped indices also close the on-disk record families: marker
`0x03000002` uses 32-byte records, while marker `0x03000003` adds separate
stored/decoded lengths and a counted 20-byte tail after 36-byte records. The
extracted gacha-character index's 24 contiguous records exactly cover its
1,399,240-byte `iv_0_0.bytes`, but that payload belongs to the separately
proven old gacha manager and is not a CharInfo V2 fixture. The native missing-
map path is now exact: `SetMap` clears/releases all six full-size clipmaps,
settles inactive, and publishes one shared Unity default 1x1x1 zero Tex3D plus
parameters `0/0/0/(0,1/3,0,0)`. Generic reflection/external reload invocation,
populated transient-atlas dimensions, live parameters, and texels remain open.
The character cubemap (`T_hdri_reflection_char_01`), sky cubemap
(`T_hdri_006`), and environment reflection-map cubemap
(`T_hdri_env_char_01`, PathID `2404688955498524548`) are exact 128x128 BC6H
six-face/eight-mip payloads. `recover_charinfo_cubemap.bat` re-extracts and
hash-verifies all three. The installed `LightBinningXYCS` and
`LightBinningZCS` assets are now exact too: all eight D3D11/Vulkan programs,
the 28-byte host `BinningData` layout, 32-pixel/2,048-slice light segment,
8x8/64x1 dispatch formulas, and combined light/reflection word offsets are
hash-pinned. A default-off raw bridge now combines the exact isolated light
words with the source-closed zero-local-reflection tail and publishes canonical
`_BinningBuffer` plus all four offsets. At 3840x2160, all 90,848 words / 363,392
bytes read back bit-exactly on both D3D11 and D3D12; retail target-frame light
survivors and pass-0 activation remain open. The installed `ReflectionProbeBinningCS`
`SampleOneTextureMip4AndNotReadSrc` producer is now source-closed: two exact
dispatches populate slice 0, mips 0..7 of a 576x576x32 linear RGBAHalf
`_ReflectionProbeOctTextureArray`, and a Unity GPU diagnostic reproduces every
expected mip byte-for-byte on repeated runs. The installed managed/native
producer for the 4,160-byte `ReflectionProbeGlobalData` buffer is also pinned,
including its four-vector header, reserved global record, 31 local-record
slots, zero-local-probe count, exact CharInfo sky-SH luminance vector, and the
32-pixel camera binning/combined byte-address-buffer layout. The compatibility
pipeline now owns that producer and, only under the existing default-off
canonical selector and exact `T_hdri_env_char_01` asset gate, co-publishes its
oct texture/global buffer in the same camera command stream without replacing
the canonical `_BinningBuffer`. It now binds both the full 260-vector canonical
buffer and the selected original D3D11 `EndfieldCB2` 259-vector prefix.
D3D11/D3D12 probes read both paths bit-exactly, observe both ready flags,
preserve light/reflection sentinels, and see the 576x576x32 texture; missing or
wrong sources clear readiness and fail closed.
The native 128-byte `VisibilitySHConstData` b33 layout is also fully closed.
The producer zero-fills all 128 source bytes, overwrites fixed rows 0..2 and
camera-derived rows 3..4, then copies untouched zero rows 5..7. All 32 words
join that same default-off frame gate and read back bit-exactly on D3D11/D3D12;
the selected deferred consumer itself reads bytes 32..63. The recovered Wulfa
capsule pass now co-publishes its half-resolution result as canonical
`_VisibilitySHRT` only while this full frame gate is ready. D3D11/D3D12 read
the same 320x360 RGBAHalf bytes (20,006 nonzero pixels), and an upstream-off
D3D12 run proves canonical publication fails closed while the diagnostic output
remains available. This is source-backed current-pose output, not a retail
settled-frame capture, and the pass-0 consumer remains disabled.
The next producer boundary is now closed as a non-presented diagnostic: a
default-off SphereOutside sidecar uses the physical CharInfo camera projection,
source transform, exact material depth/stencil state, five logical 640x720 MRT
formats, and D32S8. SceneColor, SceneMV, and GBuffer A/B/C read back bit-exactly
across D3D11/D3D12 without changing the beauty frame; missing canonical
binning/reflection/b33 prerequisites produce no draw or readback. This does not
claim the original render graph's physical identity, lifetime, or presentation.
The original pass-0 consumer remains deliberately disabled.

The next deferred boundary is validated with
`ENDFIELD_RECOVERED_DEFERRED_RESOLVER_INPUT_PROBE=1`. The GBuffer sidecar
stamps camera, frame, extent, and publication serial; the resolver probe
rejects stale or cross-camera A/B/C inputs and records the source order
`t23:_60,t24:_61,t25:_62`. Use the existing D3D12 frame command, then run:

```bat
verify_recovered_deferred_gbuffer_frame.bat --resolver-input-d3d12
python tools\verify_deferred_resolver_input_probe.py --log scratch\character_recovery\deferred_gbuffer_frame\unity_resolver_input_d3d12.log --report scratch\character_recovery\deferred_gbuffer_frame\resolver_input_validation_d3d12.json
```

This is same-frame input-order evidence only: the probe is non-presented and
retail deferred pass 0 remains disabled.

The probe also audits the target resource registers `t0/t1/t5/t6/t7/t11`.
Use the strict resource command when checking the shadow ownership boundary:

```bat
verify_recovered_deferred_gbuffer_frame.bat --resolver-resource-d3d12
verify_recovered_deferred_gbuffer_frame.bat --resolver-resource-d3d11
```

Both backends now report all six resources physical and same-frame. The
PreGBuffer material lane retains `R8G8B8A8_SRGB`; low-resolution shadow is
`160x180 R8_UNorm`, and screen-shadow is `640x720 RG8`. Screen-shadow content
remains explicitly invalid and pass 0 stays disabled.

For an isolated D3D11 exact-consumer attempt, use
`verify_recovered_deferred_gbuffer_frame.bat --exact-consumer-d3d11`. This
submits the selected original DXBC into a private target and never presents it.
The current MainCamera frame proves exact execution (`exactBound=1`) and a
complete `t0..t25` SRV mask (`0x3ffffff`, no resource failures); the readback
contains 7,372,800 bytes with 6,430,845 nonzero bytes. The exact b0–b8 bridge
also reports `constantBufferMask=0x1ff`; the current RGBA-float oracle hash is
`b0130f5a0f67f714181847413757e81fbeebe59af0428abecdc9b33e67d2cb83`. The
output remains private and non-presented, so this command does not enable
retail pass 0 or claim numeric lighting parity.

The selected original pass-0 `_TransformVariables` b30 reads are now closed for
the physical camera's view matrix, inverse view, inverse GPU view-projection,
and world-space position. A default-off same-frame publisher exposes the full
1,312-byte buffer plus the 720-byte D3D11 bridge; all 328 words are identical
on D3D11/D3D12, while the 69 unselected history/jitter/stereo rows stay zero.
This closes only the fields proven used by the selected binary and does not
enable pass 0.

The selected `_LightDataBuffer` b31 reads are also closed for the isolated
Wulfa/Zhuangfy CharInfo fixture. Native construction and `PrepareCPUData`
packing prove a 32,864-byte layout of six header vectors plus 256 eight-vector
punctual records. The exact CharInfo directional header is published; every
selected punctual row has zero OBB flags and `CharacterOnly=1`, so the selected
SphereOutside program exits before unresolved general-light or shadow fields.
All 8,216 words match on D3D11/D3D12 through both `_LightDataBuffer` and the
original DXBC-shell `EndfieldCB4` bridge, with unknown words zero and unchanged
beauty output. This source-closes only that consumer subset; general-scene
punctual records and pass 0 remain open. The installed `PrepareCPUData` body
now closes the native eight-float4 row schema itself for both Spot and
Point/linear-extension branches. For the selected-aspect Gacha room, the exact
authored contribution is one Spot, six ordinary Point, and four
positive-length linear-extension Point rows. All eleven source Lights enable
OBB culling and carry no cookie or shadow. Each row's third GameObject
component resolves to the same serialized `HGAdditionalLightData` script.
Hash-pinned installed `GetLightNPRData` and `GetLightAdditionalData` bodies
close its 32-byte return layout: all rows use type-0 NPR `(1,1,0,0)`, are not
CharacterOnly, use falloff `-1`, and split volumetric intensity 2/5/4 across
0/1/10. This closes b31 record3.yzw, record4, and record6.w for the room rows.
The pinned producer also builds the authored OBB as inverse TRS and writes six
row-major half2 words to record5.xyz/6.xyz. Its installed pack and `f32tof16`
bodies now yield bounded candidates for all 11 rows; decoded corners miss the
unit-box boundary by at most `0.002611`. UnityPlayer icall 2471
(`Matrix4x4::Inverse3DAffine_Injected`) resolves through stub `0x1800A2020`
to the hash-pinned `0x180569BD0` scalar determinant/cofactor body; its exact
float32 order and `-0` sign-mask candidates are now replayed, including the
`Spot Light (12)` one-ULP boundary. Retail packed-word capture and the
runtime Quaternion.Euler order remain open. The adjacent UnityPlayer icall
2470 (`Matrix4x4::TRS_Injected`) is also source-closed: its `0x1800A1BB0`
wrapper, `0x18056CB40` scalar column-scale/position-copy body, and
`0x18056B8A0` quaternion-to-column-major helper are hash-pinned and replayed.
The managed `Quaternion.Euler` wrapper and exact float32 degree-to-radian /
half-angle input are source-closed as well; UnityPlayer icall 2489,
`0x180567590`, and all six native sin/cos call targets are pinned. The
GameAssembly lazy resolver string, `0x180059FC0` call, and slot
`0x18F36FAC8` load/store are hash-pinned as well. The audit maps the installed
UnityPlayer image with `DONT_RESOLVE_DLL_REFERENCES` and
calls the pinned `0x1800A5010` wrapper, producing bit-exact native quaternion
outputs for all eleven authored rows. The wrapper's explicit order-4 immediate
and six-entry native jump table are pinned (selected case offset `0x425`). A
runtime slot/patch state, patched IFix path/output selection, and retail
capture remain open. Pinned
original `globalgamemanagers`
objects set Linear color space and linear light intensity, while all 11 rows
disable color temperature, distance/far-show falloff, animation, multistate,
and flicker. Hash-pinned UnityPlayer `finalColor`, `Color.linear`, animation-
disable, and flicker bodies now close exact b31 record0.xyz bits as linearized
authored RGB times intensity, with falloff/flicker both 1. The two native
`PrepareCPUData` branches close record0.w as
`float(lightKind + 2*shadowOnly)`: the one Spot row is exactly 0 and all ten
Point/linear-extension rows are exactly 1. Record0 is therefore fully closed.
Metadata-backed `VisibleLight.get_range` at `+0x68` and the native divide now
close record1.w for all 11 rows. Hash-pinned half-angle scaling and the original
scalar-cosine body close record2.z plus the Spot row's record2.w; the Point
branch closes record2.z as `HGSharedLightData.length` (`-1` for six ordinary
Points and `18` for four linear extensions). Target-frame record1.xyz/record2.xy,
Point record2.w shadow-face packing, runtime carry-in, final light count, and a
byte-exact room b31 fixture remain open.

`ShaderVariablesGlobal` b35 is now exactly scoped and transported. The
selected body references 33 fields, and installed native reset producers close
atmosphere rows c71..c76, height-fog rows c77..c82, and disabled-volumetric rows
c83..c87. Current constructors, `IsActive`/camera getters, and the selected
CharInfo/global/LookDev VolumeProfiles close c30 as `(0,0,1,1)`; the
`HGSettingParameters` default and every shipped platform/tier override close
c31.x as `reflectionProbeMaxSampleMip=7`. Perspective c4.w, mip bias c26.x,
binning/environment c28/c29, inactive IV parameters c132..c134, and disabled
wetness c156.x are also closed; frame count is read only behind the exact-zero
volumetric gate. Native `HGCamera.UpdateFrustum` builds c3 as
`(-1, near, far, 1/far)`; the original serialized Zhuangfy Overview lens is
near=0.1/far=50, so live c3.y is exactly 0.1. The enabled weight-1 CharInfo
environment volume selects `CharInfo_Env`; installed
`UpdateShaderVariablesIrradianceVolume` and `GetCoefficientsL1` code proves
c135..c137 each equal the serialized ambient-SH reorder
`(SH3,SH1,SH2,SH0) * skyDirectIntensity`, exactly
`(-0.0075507611,0.4722373188,0.0121708093,1.0963056087)`. All selected b35
value producers are source-closed. A default-off publisher binds the full
200-vector canonical buffer and the 157-vector D3D11 `EndfieldCB1` prefix.
D3D11/D3D12 read back 800/800 and 628/628 words exactly; raw c28 integer
offsets are preserved, all unselected rows stay zero, same-frame Wulfa
activation succeeds, and missing canonical prerequisites fail closed without
changing D3D12 beauty. Pass 0 remains disabled.

The remaining streamed
`m_defaultIV` voxel contents/per-frame parameters, light/shadow resources,
settled VisibilitySH `PassInput.enabled`, exact posed record values and
view-cull survivors, render-graph/subpass state, and a binding-compatible
pass-0 resolve are not closed. The current installed `RenderWithAlpha=false`
Gacha route submits no WriteAlpha draw; its recovered passes stay available only
for a future source-closed true route. VisibilitySH's exact LUTs, target,
empty fallback, native output/packing ABI, actor candidates, and producer pass
are source-closed but remain deliberately unpublished with pass 0.
For `ShadowPlane`, the selected
receiver/material, bit-32 character PreG writer contract, original 15-slot
character-atlas shader ABI (14 entries are assignable in the current runtime),
and VisibilitySH capsule topology are pinned; canonical
physical-camera stencil integration and live atlas/posed-capsule publication
are not. Requesting the full branch therefore keeps `ReferenceBackdrop`
enabled instead of substituting a PBR or fake shadow guess. The compatibility
backdrop is still excluded from source-HDR input, and it must not be tuned to
imitate the screenshot. Build/verify this imported asset graph with:

```bat
build_charinfo_presentation_recovery.bat
verify_charinfo_presentation_recovery.bat
python tools\verify_charinfo_outside_lit_recovery.py
verify_recovered_canonical_binning_buffer.bat --all
verify_recovered_canonical_reflection_frame.bat --all
verify_recovered_visibility_sh_constants.bat --all
verify_recovered_visibility_sh_frame.bat --all
verify_recovered_visibility_sh_frame.bat --fail-closed-d3d12
verify_recovered_deferred_gbuffer_frame.bat --all
verify_recovered_deferred_gbuffer_frame.bat --fail-closed-d3d12
verify_recovered_deferred_transform_variables.bat --all
python tools\audit_deferred_shader_variables_global.py --check
verify_recovered_shader_variables_global.bat --all
verify_sphereoutside_hgbuffer_diagnostic.bat
verify_charinfo_shadow_receiver_recovery.bat
```

An explicitly partial, non-original diagnostic can render only the recovered
`CharFloorEffect`, `GeoSphere001`, and `GridDeco/Far` passes at the exact
source-derived opened endpoints. It always excludes unresolved
`SphereOutside` and `ShadowPlane`, remains off by default, and does not make
the five-renderer scene original-equivalent:

```bat
render_charinfo_ready_subset_diagnostic_wulfa.bat
render_charinfo_ready_subset_diagnostic_zhuangfy.bat
```

The clean 3840x2160 ready-subset hashes are Wulfa
`5CF2511042BD0488E0FE5272E0D1443A5305E3D8EF23ADBAAADD598701C5589C`
and Zhuangfy
`D9BD5483D5CE32E0DA32D53BAA633D53DE0B638BFFD8FE2298BE214A598C5932`.
A controlled post-disabled Zhuangfy A/B is exact on every nonzero-alpha actor
pixel, proving these three renderers do not change pre-post character shading.
Their bright gray output does enter bloom/composition, lifting fully opaque
actor luma by about four display codes on average. Against `front_full`, that
shift is mixed for Wulfa and farther for all five measured Zhuangfy groups; it
is source behavior, not evidence that the central response-span gap is closed.

A separately named **PARTIAL/NON-ORIGINAL cumulative diagnostic** adds the
exact actor-specific CharInfo background portrait and the focused one-actor
screen-shadow producer/consumer to that ready subset. Its wrappers explicitly
force the full presentation, standalone PreG, generic screen/direct audit, and
capture-input-dependent gyroscope selectors off, perform a small repeated-mask
validation, then render one 3840x2160 beauty:

```bat
render_charinfo_cumulative_diagnostic_wulfa.bat
render_charinfo_cumulative_diagnostic_zhuangfy.bat
```

The current integrated hashes, regenerated after the exact body-Skin branch
and bounded primary-depth post-Uber portrait compositor landed, are Wulfa
`C5D035DD00730E94B7DE6D4FDA9EFC4E1DEBF832FAAB56077673D3FA998ACBC5`
and Zhuangfy
`FC22179F2268B33FF7A45601A6A93BD42F7249F0D215BCAB7DBFA118C0E0673C`.
Both focused reports have empty `blockedMaterialPasses` and `failures` arrays.
The earlier portrait-free fixed-reference metrics remain useful only as an
isolated screen-shadow comparison; they do not score these portrait-inclusive
PNGs. This cumulative path is still default-off and non-production because it
does not recover `SphereOutside`, `ShadowPlane`, the complete character
response, temporal resolve, or overlay UI.

The large hatched silhouette is no longer an ownership hypothesis. Original
data identifies it as the actor-specific `bg_charinfo_<templateId>` Sprite,
loaded by `PhaseCharInfo.lua` into
`CharInfoCamAttachment/OffsetRoot/CharinfoBGDeco/CharTexture` for Overview. The
lab imports the exact Wulfa/Zhuangfy Texture2D pixels, reconstructs each
GenerateSimpleSprite quad from the original tight `textureRect`, applies the
world-space Canvas hierarchy and settled `90/255` alpha, and ports the selected
`M_ui_world_default_chartex_depthoffset` UI shader variant. Build and render it
independently with:

```bat
build_charinfo_background_portrait_recovery.bat
render_charinfo_background_portrait_wulfa.bat
render_charinfo_background_portrait_zhuangfy.bat
python tools\verify_charinfo_background_portrait_recovery.py --static-only
python tools\verify_charinfo_portrait_post_uber_recovery.py --static-only
```

The current post-Uber 3840x2160 D3D12 hashes are Wulfa
`515AB6742C9775D55C9CD5489C7E5BFFC07B6C750C8D5AF0DA43031EBF85858A`
and Zhuangfy
`EF2A16FDE902645B5D61E8A365F23A05E11125E9948ED788FD520EEBBD09992E`.
Source-feature registration finds Wulfa within `+0.199%` scale but displaced
`(+56.39,-29.77)` pixels from retail, and Zhuangfy within `+2.193%` scale but
displaced `(-51.20,-21.57)` pixels. The opposite horizontal residuals rule out
one evidence-based global nudge. The retail portrait route is now source-closed
far enough to identify the remaining architectural mismatch. The 1022-square
Sprites exceed the retail runtime-atlas limit of 512, so they stay bound to the
original 1024-square BC7 sRGB textures; the reachable canvas mesh is the same
four-vertex `GenerateSimpleSprite` quad used by the lab. Retail draws this
world UI after the Uber fullscreen post and samples the primary general
scene-depth/stencil handle. The default-off lab route now implements that
schedule: it preserves a full-scene `D32_SFloat_S8_UInt` RawDepth attachment
(`D24_UNorm_S8_UInt` fallback), excludes only layer 16 from ordinary
transparents, runs the fullscreen post, then draws the portrait into the post
color while sampling that depth. The distinct retail paired output-depth
attachment is not fabricated because its descriptor is not source-closed and
the selected pass is `ZTest Always`/`ZWrite Off`; absent ECS/HGUI renderer-list
systems are also not claimed. Frame-specific device depth/MSAA selection,
`_ZBufferParams`, non-jittered UI matrix values, the engine-owned
`_TextureSampleAdd` literal (expected zero), later copy/scaler state, and the
final batch ordinal among unrelated equal-sort renderers remain live
observations rather than tunable parameters.

The original `CinemachineGyroscopeEffect` Finalize callback and
`UIGyroscopeEffect` input curves are also recovered. The camera-state diagnostic
supports `off`, `neutral-centered-input`, `serialized-entry`, and
`recorded-input-endpoint` through
`ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE`; ordinary/cumulative renders use
`off` because the reference capture's cursor/controller state was not recorded.
The serialized-entry endpoints can be inspected with:

```bat
render_charinfo_gyroscope_serialized_entry_wulfa.bat
render_charinfo_gyroscope_serialized_entry_zhuangfy.bat
python tools\verify_charinfo_gyroscope_recovery.py
```

Those serialized offsets explain opposite actor-specific camera shifts, but
they are entry state replaced by a two-second OutQuad input transition, not
universal settled values. No portrait or camera offset is fitted from the
screenshots.

Recovered cloth response is selected with
`ENDFIELD_RECOVERED_CLOTH_SPECULAR_MODE` or the standalone argument
`-endfield-recovered-cloth-specular-mode`:

| Mode | Direct response | Character cubemap |
| ---: | --- | --- |
| `0` | canonical lab lobe | off |
| `1` | recovered shipped GGX | off |
| `2` | recovered shipped GGX | exact DFG/cube |
| `3` | canonical lab lobe | exact DFG/cube |

The hair diagnostic is `ENDFIELD_RECOVERED_HAIR_RESPONSE=1`. Both ports are
default-off because matched Wulfa/Zhuangfy A/B results are mixed: cloth mode
`2` improves Wulfa red cloth and both actors' dark hardware but over-lifts
Wulfa white cloth and Zhuangfy green/pale materials; the hair port improves
Wulfa but over-brightens Zhuangfy. See
`scratch/cloth_specular_recovery.md` and
`scratch/hair_response_recovery/recovery_note.md` before enabling either.

`ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1` or
`-endfield-recovered-source-energy-core` selects a single compile-time,
default-off Wulfa/Zhuangfy cloth/hair energy path. It combines the recovered
live-shadow diffuse with the selected original variants' matching carriers:
cloth GGX, spec-ramp, exact character cubemap/DFG, high-luma chroma extrapolation and
serialized emission; hair packed-R strand basis, dual lobes, specular line,
`specAmbientIntensity * fullDiffuse` carrier, and high-luma chroma extrapolation. The
selector also fixes an earlier hair diagnostic mismatch: packed R is not a
diffuse metallic value, and original hair specular is not multiplied by
main-light RGB.

This selector is still incomplete and must not be promoted as the production
path. The exact selected SPIR-V consumes renderer custom-per-draw
rain/wet/wet-global/snow state and wet world-space height, not an authored hair
height-darkening parameter. Those gameplay values, live cluster membership,
shadow resources, and later frame state are
not serialized in the recovered actor payload. They remain neutral or
excluded; the separately gated punctual/Fog subset above is source-backed and
uses no screenshot fitting. Static provenance and validation are recorded in
`scratch/cloth_hair_source_energy_core_recovery.md`.

The shared viewer and ordinary preview builders keep this selector off unless
the inspector toggle, environment variable, or command-line argument explicitly
requests it. Clean Unity 2022.3.62f3 D3D12 off/on captures for Wulfa and
Zhuangfy are under
`scratch/character_recovery/hair_energy_core_ab/`. The selected equations
produce real nontrivial deltas. A material-only diagnostic that holds the
physical CharInfo sky off is byte-identical to the full-selector frame for both
actors, so the delta belongs to the material path in these captures. The
enabled path over-lifts Zhuangfy's crown/face and worsens Wulfa's
hair/white-cloth balance against the supplied retail frames. Keep it diagnostic
until the missing original
lighting/shadow/frame-state context is recovered.

A later installed-binary audit corrected one shared hair/cloth scheduling
error inside this gate: the original character-main descriptor uses unscaled
RGB for the CP12.y ambient `lightBlend` and applies descriptor W only to the
neighboring direct luma/chroma term. Both CharInfo actors resolve CP12.y=1 and
descriptor W=1.624386775, so the prior port duplicated that intensity. Clean
D3D12 rerenders move both actors darker, but do not close the reference
contrast. Combining the correction with the separate character-shadow
diagnostic proves that missing input is material (about 4% of each 4K frame),
while also exposing visibly too-hard current atlas silhouettes. A follow-up
installed-VFS pass temporarily replaced that run's visible-LOD0 caster
enumeration with the exact postmodel `Shadow_Proxy/SP_Desktop` LOD1 hierarchy.
It changes 0.625%
of the Wulfa frame and 0.862% of the Zhuangfy frame relative to the LOD0
result, but does not by itself remove the hard local attenuation. Both paths
therefore remain explicit diagnostics. A later exact helper audit proved these
mode-3/4 renderers receive invalid character index 15 and are not the dedicated
atlas list; the source-correct managed membership is the ordinary LOD0/LOD1
`m_RealtimeShadowCaster` roster described below. Evidence and hashes are in
`scratch/character_recovery/main_light_descriptor_split_20260723/` and
`scratch/character_recovery/character_shadow_proxy_recovery_20260723/`, with
the corrected capture under
`scratch/character_recovery/character_shadow_original_realtime_caster_recovery_20260724/`.

`ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1` and
`-endfield-recovered-separate-character-shadow` are default-off topology
diagnostics. They preserve scene CSM state and render one original-shaped
character-shadow tile independently of `KeyLight.shadows`. Wulfa resolves all
49 authored bone spheres and Zhuangfy all 75; the port uses the recovered
CameraFollow `(32,12)` virtual light, exact orthographic fit, 1024/D16 tile,
hardware bias `(8,0)`, shader bias `(3,6)*texelWorld`, and the selected
original receiver's 16 raw
`GatherRed` operations with its 64-tap nonlinear shaping. Standalone D3D12
captures verify the producer,
two raw/comparison SRV views, point-clamp sampler, and 16 compiled gathers.

The producer construction is now instruction-closed against the current
installed `GameAssembly.dll`, not just source-shaped. Native
`HGShadowManager.GetMatrices` proves the literal-zero virtual-light Euler roll,
extents-length support distance, eight-corner bounds fit, XY recentering,
safe fitted rotation, and final `(width,height,minZ,maxZ)` orthographic call.
`HGShadowUtils.GetShadowBias` proves `2/projection.m00/resolution`, the direct
setting scales, and the 1.5 sample-mode-2 multiplier. The render delegate feeds
hardware bias directly to `CommandBuffer.SetGlobalDepthBias`, draws, then
resets it to zero. The selected original SPIR-V independently matches the
lab's receiver-side offset signs and slope clamp. The lab now supplies the
native literal-zero Euler roll. The same binary audit now closes
`HGCharacters` admission: self-shadow-enabled helpers are sorted and filtered,
their filtered-list index is the shadow ID, and rendering layer is
`1 << (index+8)`. The current binary clamps active IDs at 14, while the retail
shader arrays remain length 15. Focused installed exports prove Wulfa,
Zhuangfy, Lifeng, Mifu, and Pelica each have priority 100, both shadow-enable
flags, and sphere bounds enabled, so any one actor alone is exactly slot 0 /
layer 256.
The equal-priority tie is exact ascending `Object.GetInstanceID`. Frame setup
uses `(count,1)` tiles through four actors and
`(4,ceil(count/4))` thereafter; per index the normalized atlas rectangle is
`(column/columns,row/rows,1/columns,1/rows)`. The 14-entry maximum therefore
uses a 4096x4096 atlas of 1024 tiles with two unused cells in its last row.
The current `RenderCharacterShadows` body closes the surrounding graph
execution too: it loops every active index, assigns the matching 1024-pixel
viewport, creates the `CommonOpaque` Unity character `ShadowCaster` list,
creates the ECS list with character index `i+1`, binds the atlas depth
attachment, and disables pass culling. The original CPU/render-graph schedule
is therefore recovered.

The exact installed helper closes which managed Unity renderers enter that
list. `HGCharacterHelper.FindRenderers` stores ordinary child renderers with an
`inLodGroup`/`castSelfShadow` row and stores shadow modes 3/4 separately.
`HGCharacterQualitySettings..cctor` sets the LOD self-shadow cutoff to 2.
`UpdateShadowRenderingLayer` requires helper self-shadow, the row flag, and
`Renderer.GetIsRealtimeShadowCaster()` before assigning the live index.
Separately stored proxies receive layer 2 and invalid index 15. The current
LOD0 recovery therefore selects 151 ordinary renderers and excludes five exact
`m_RealtimeShadowCaster=0` rows. The adjacent ECS query is exact too:
`CreateRendererListWithCharacterIndex(viewHandle, slot+1, 0x400, 0, 0x400, 0,
context)` excludes `HGRenderFlags.ShadowOnly` and selects `ShadowCaster`.
Its generic backend identity and live runtime entity census remain open.

The lab executes recovered two-, five-, nine-, thirteen-, and fourteen-actor
subsets behind
`ENDFIELD_RECOVERED_SEPARATE_CHARACTER_SHADOW=1` plus
`ENDFIELD_RECOVERED_MULTI_CHARACTER_SHADOW_ATLAS=1`. Adding
`ENDFIELD_RECOVERED_ORIGINAL_REALTIME_CHARACTER_SHADOW_CASTERS=1` uses the
source-closed 151-renderer roster; leaving it unset preserves the older proxy
capture path for historical comparisons. All actors are sorted by the exact
equal-priority instance-ID rule and assigned the shifted
rendering-layer bits. The Wulfa/Zhuangfy probe renders the 2x1 2048x1024
layout; adding Lifeng/Mifu/Pelica reaches the 4x2 4096x2048 layout; adding
Endminm/Endminf/Chen/Wolfgd reaches the 4x3 4096x3072 layout; the later exact
actors reach the 4x4 4096x4096 maximum. Forward
draws decode `asuint(unity_RenderingLayer.x)` into the matching lab-prefixed
15-entry matrix/bias/direction/rectangle arrays; the implementation admits at
most the binary-proven 14 slots and restores every prior renderer mask after
the camera. This remains default-off and does not claim the game's ECS caster
backend/live entity set.

Two D3D12 runs swap the actors' creation/instance-ID order and therefore swap
both atlas slots and rendering-layer bits. The normal image hashes
`5980451E19BF3FD5B0990BE11DB49CF9B04BFDEA5701A7A6DA54B0D443867272`;
the reversed-order image hashes
`A43D8743D60998BDFAF531B170F062020FC8486B07A1408339B9077B93EAD896`.
Only 136 of 8,294,400 RGB pixels differ (0.0016397%, MAE
0.00001346/255, maximum delta 7), GPU-validating the two-actor carrier rather
than only its CPU assignment. Evidence is under
`scratch/character_recovery/multi_character_shadow_atlas_20260723/`.

The five-actor row-transition probe logs exact active proxy counts
`11/5/7/7/7`. Normal scene lifetime order assigns
Mifu/Pelica/Lifeng/Wulfa/Zhuangfy to slots 0..4 and hashes
`9123C9BA620496740D86AC020BBB2B98A65892E882CE7495A8644011CDF6ADCA`.
Forced reverse creation assigns Pelica/Mifu/Lifeng/Zhuangfy/Wulfa and hashes
`02A8E3883675F9D3A74292C374D41E8D5A8FEA2955677452584EEAA82F9FF709`.
The second-row slot-4/layer-4096 owner therefore changes from Zhuangfy to
Wulfa, while only 70 of 8,294,400 pixels differ (151 channels, absolute RGB
delta 281, maximum delta 6). This GPU-closes the first 4x2 row transition;
at that milestone, later slots and row transitions were still open. Evidence is under
`scratch/character_recovery/character_shadow_five_actor_recovery_20260723/`.

The nine-actor third-row probe adds four exact installed postmodels. Endminm,
Endminf, Chen, and Wolfgd preserve priority 100, all three helper admission
flags, 30/31/50/26 authored spheres, and active proxy counts 8/8/7/12 out of
9/9/7/12 exact proxy meshes. Together with the five earlier actors, the
default-off contract contains 78 exact LOD1 meshes. A name-only source-renderer
lookup correctly failed closed on Wolfgd's duplicate
`S_actor_wolfgd_cloth_05_lod0`; every proxy now carries an exact relative
`sourceRendererPath`, so that entry resolves to
`Mesh_all/lod0/S_actor_wolfgd_cloth_05_lod0`.

Both D3D12 runs log `count=9`, `grid=4x3`, `atlas=4096x3072`, 1024 tiles,
and D16. Normal creation assigns
Endminf/Mifu/Endminm/Pelica/Lifeng/Chen/Wulfa/Wolfgd/Zhuangfy to slots 0..8
and hashes
`E06199658F3F784B15A3F89C010184D4DC71170A7D2B14DF3AC6D80720803280`.
Reverse creation assigns
Wolfgd/Chen/Endminf/Endminm/Pelica/Mifu/Lifeng/Zhuangfy/Wulfa and hashes
`109F432F5A02B41FC3D76C7688EA24F0CDA00416603E4791D3A1AC5142653B8E`.
The slot-8/layer-65536 owner changes from Zhuangfy to Wulfa while only 122 of
8,294,400 pixels differ (251 channels, absolute RGB delta 376, maximum delta
8). This GPU-closes the first third-row slot; at that milestone, slots 9..13
and the count-13 fourth-row transition were still open. Evidence is under
`scratch/character_recovery/character_shadow_nine_actor_recovery_20260723/`.

The historical fourth-row and maximum-slot proxy probes add Aglina, Aurora,
Antal, Ardelia, and Bounda. Their exact active proxy counts are 6/6, 9/9, 5/5,
10/10, and 12/12, bringing that diagnostic roster to 120 meshes across 14
actors. Dapan was the initial last-slot proxy candidate, but its focused
playable-postmodel export contains 45 skinned renderers and no desktop shadow
proxies, so it was correctly excluded from that diagnostic rather than assigned
fabricated proxy casters. This does not exclude Dapan from the ordinary
realtime-caster class.

These exports also close exact renderer-material multiplicity. Aurora's fur
proxy points to the two-submesh `S_actor_aurora_fur_01_lod1_8`, not the plain
`_lod1` mesh. Wolfgd furcard, Aglina vfxpart, Ardelia fur, and Bounda eyeshadow
serialize more renderer materials than mesh submeshes. The provider now
preserves all 126 exact material passes, including repeated final-submesh
draws; Aurora's paired fur materials retain cull modes 0 and 2.

Count 13 first executes `grid=4x4`, `atlas=4096x4096`, D16 and slot
12/layer-1,048,576. Its normal/reverse images hash
`02E2939EF8D3C18FD737736E808E12B93BD756C4ED9FDA39B35B253D7D045445`
and
`42B069EDCFA7A896F418B8BC79F3820058D1BA0CE1EC13DBBB8372A60B79F41F`;
only 27 pixels differ. Count 14 then executes the complete binary live range.
Normal creation places Zhuangfy in slot 13/layer 2,097,152 and hashes
`0CD7C5CB965AFE9E0839B8538A81AD883195530650586E6371EDC6404942DF1C`;
reverse creation places Wulfa there and hashes
`0BFC9F3F68F2FAD4CCACF25FAC330246E8BBBEE0552D9815B86D7FFEC33EA5E4`.
Only 45/8,294,400 pixels differ (98 channels, absolute RGB delta 169,
maximum 5). Admission, equal-priority ordering, all row transitions, matrix/
rectangle selection, and rendering-layer transport are therefore GPU-closed
for every assignable slot 0..13. Evidence is under
`scratch/character_recovery/character_shadow_thirteen_actor_recovery_20260723/`
and
`scratch/character_recovery/character_shadow_fourteen_actor_recovery_20260724/`.

The subsequent installed-binary membership audit overturns the proxy-as-atlas
interpretation without invalidating those scheduling captures. Across the same
14 recovered actors, the exact current LOD0 intersection contains 151 ordinary
`m_RealtimeShadowCaster=1` renderers: 14/9/10/11/12/11/11/10/13/9/11/6/13/11
for Wulfa, Zhuangfy, Lifeng, Mifu, Pelica, Endminm, Endminf, Chen, Wolfgd,
Aglina, Aurora, Antal, Ardelia, and Bounda. It excludes five exact false rows.
The fail-closed D3D12 maximum run logs every count and hashes
`1ECCD771D862D1B3827FE6554697CF786A2D1E1AFE4B1CB4E4FC916E5F04713B`.
Relative to the proxy capture, 25,913 pixels (0.312416%) and 60,630 RGB
channels change, with absolute RGB delta 280,846 and maximum channel delta 79;
the bounding box is `[124,871]-[3695,1290]`. Evidence is under
`scratch/reverse_engineering/character_shadow_ecs_caster_20260724/` and
`scratch/character_recovery/character_shadow_original_realtime_caster_recovery_20260724/`.

`SetupCharacterShadowReceiverConstants` also publishes
`Light.shadowStrength` directly; the character volume's
`selfShadowStrength` is not a second multiplier. The generated KeyLight has
Unity shadows disabled but authored strength 0.9. Correcting the exact
diagnostic from 1.0 to 0.9 produces Wulfa
`E3B35784FA90F38DB1D17303061C9C3DE56ECC40919F21D648FC19DFBB02A91F`
and Zhuangfy
`646D39D20DDC6A0301BBA8A795AD63A96CC87FE1E0567BCEEB1027EA146D708F`;
both D3D12 logs retain successful 1024 matrices and exact 11/12 and 5/8 proxy
counts. Evidence and the 1,390-check focused verifier are under
`scratch/character_recovery/character_shadow_producer_matrix_recovery_20260723/`.
The remaining hard attenuation therefore stays assigned to executing live
retail lifetime-driven roster membership, full-client
screen-space attachment and the larger retail frame contract, not a free producer-bias,
receiver-strength, ordering-rule or atlas-rectangle tuning parameter.

This is not yet a promoted whole-pipeline preset, but the recovered receiver is
now behaviorally valid for the one-character lab path. An earlier diagnostic
incorrectly returned full shadow when the reversed-depth gather found zero
blocker taps; original shader/capture evidence proves that endpoint is fully
lit. After correcting only that transcription, mode 6 shows predominantly lit
surfaces with localized hair, layered-cloth, cape, and limb occlusion. Mode 5
then produces non-crushed Wulfa and Zhuangfy cloth/hair validation renders from
the parsed CharInfo payload. The original multi-character list/index contract,
skin/eye and remaining material energy paths, irradiance/visibility inputs,
additional-light equations, a possible reused-camera first-frame exposure
current, and final display/temporal state remain incomplete. Normal settled
CharInfo exposure itself is source-closed as Manual EV0 -> one. Detailed
evidence is in
`scratch/ifix_shadow_recovery/recovery_note.md`,
`scratch/pso_cache_oracle_20260712/recovery_note.md`, and
`scratch/character_shadow_recovery_20260712.md`.

The source-shaped eye response is independently default-off. Enable it for a
Wulfa/Zhuangfy A/B with
`ENDFIELD_RECOVERED_EYE_RESPONSE_SEMANTICS=1`, or use
`-endfield-recovered-eye-response-semantics` in the standalone player. It uses
the exact serialized iris/brow feature sets and material values, the recovered
object-space light projection, two fixed-row ramp samples, CP2/CP5/CP13 energy,
matcap packing, eye subsurface response, `_AlphaPremultiply`, and the exact Eye
camera-cluster Default/Fog subset; Eye Rim is zero. The selected opaque Eye
Target0 now also resolves alpha to the original `1.0`. Original overview data
makes the remaining Eye rim/subsurface/weather/fog/VFX additions dormant, so
the lab does not invent them. The exact selected Zhuang VFX path now owns a
native packed `A2B10G10R10_UNormPack32` sceneMV MRT and one-clear/load/store
lifecycle, but Eye-only frames do not independently request it and the general
packed quarter-power motion path still requires the original previous camera/
object/deformation lifecycle. The current retail total order is source-closed
as GBuffer -> ForwardOpaque -> main ForwardOnly -> Distortion -> gated Phase1 ->
after-DOF ForwardOnly; the lab no longer treats that ordering as inferred. It
does not claim complete global shadow/
irradiance state, character weather, or general second-MRT scheduling.
CharInfo atmosphere fog is source-proven disabled. The exact camera
raster variants are now selected from original Material keywords and the v3
serialized pass metadata: Wulfa/Zhuangfy Skin use pass-0 `ForwardLit`
fragments `0215`/`0179`, and their irises use `0059`/`0065`. The earlier Skin
`2543` module is conclusively pass 4 `RayTracingReflection`; it remains a
shared-contract oracle, not a camera replacement. The raster fragments prove
that emission and punctual lighting precede the final whole-result exposure
division, so the Eye exact branch now follows that ordering. Installed settings
and native keyword publication prove that the unpatched Windows overview selects
`HG_ENABLE_SCREEN_SPACE_SHADOW_MASK`. The producer contract is now exact too:
three quarter-resolution `R8_UNorm` targets perform the bytecode-recovered
4x4-depth/CSM directional evaluation then exact 7x1/1x7 blur; the full-resolution
`R8G8_UNorm` resolve publishes scene attenuation in R plus character attenuation
in G. The original `ContactShadowCS/RayTracingV2` full-resolution R8G8 producer,
64x1x1 dispatch and R attenuation/G displacement contract are now pinned too.
The installed persistent IFix table is signature-disjoint from the searched
screen-shadow/low-res/contact/CSM/ASM/cloud owners, although unobserved transient
replacement remains outside static evidence.

The installed `CharInfo_Env` closes three more frame-input boundaries without
visual fitting. Cloud and cloud-shadow are both disabled; the original sky
constant owner writes `(1,0,0,0)`, zero, and one vectors at the three cloud
parameter rows, while `HGRenderPipeline.UpdateGlobalConstants` binds
`Texture2D.whiteTexture` to `_CloudShadowTex`. ASM is serialized disabled and
its exact skip pass binds the render graph's dedicated 1x1 default depth-shadow
texture to `_ASMShadowmapTex`; the depth comparison value remains unproved.
CSM is enabled. Its five matrices, split spheres, biases, atlas parameters,
texel size, penumbra sizes, directional parameters, and named Rhodes row are
now pinned to the original 11,440-byte `ShadowData` layout and upload owner.
The active atlas texels and live per-camera cascade inputs are not yet reproduced.

The normal lab path deliberately remains no-screen. The default-off CharInfo
diagnostic above now supplies the exact one-actor G topology and a separate
compile-time Forward consumer that removes direct character-atlas sampling.
Skin/Cloth/Hair consume R/G and Eye consumes R only. D3D12 capture proves the
selected programs execute and bind the diagnostic RG8 resource, but HGCompat
still lacks active original CSM atlas content, live contact dispatch data, the
ASM default-depth comparison-content proof, and the exact retail PreG
DrawECS/equal-depth/transparent ownership schedule. The path
therefore keeps a distinct name, never binds a fake production mask, and is not
promoted as a global preset.
Evidence, exact hashes, resource joins,
and remaining equation gaps are in
`scratch/skin_eye_raster_forward_recovery_20260713/recovery_note.md` and
`scratch/skin_eye_raster_forward_recovery_20260713/manifest.json`, plus
`scratch/face_sdf_instance_basis_recovery_20260713.md`,
`scratch/eye_remaining_raster_exact_20260713/recovery_note.md`,
`scratch/screen_shadow_keyword_recovery_20260713.md`, and
`scratch/screen_shadow_producer_recovery_20260713/recovery_note.md`.

### User-authorized original-client GPU capture boundary

The standalone Windows D3D12 lab remains the preferred capture target.
Original-client graphics instrumentation is permitted only for a session
explicitly authorized by the user, on an installation, account, and hardware
they control, where applicable law, service terms, and the instrumentation
tool's terms permit it. A signed mainstream graphics profiler remains
preferred. A narrow read-only user-mode hook is also permitted when the user
explicitly requests it, the exact executable/module hashes and instruction
bytes are pinned before attach, the client is launched through its normal
launcher/protection chain, and the hook only records the predeclared render
fields. Use the graphics API selected by the client; do not force an
alternative API.

This is observation-only permission. It permits the stock profiler hooks or
layers required to inspect event order, PSOs/shaders, constants, descriptors,
textures/buffers, depth/stencil, and render targets. It does not permit
disabling, stopping, patching, unloading, spoofing, hiding from, or otherwise
evading AntiCheatExpert or another protection/access control; manual-map,
stealth, or kernel injection; client/driver modification; signature or handle spoofing;
credential, token, or network interception; or gameplay/network manipulation.
The authorized user-mode hook must use the tool's ordinary documented attach
path, must not persist code or modify game files, and must fail closed on any
binary/config mismatch.

If the client or protection refuses, terminates, or blocks the profiler or
read-only hook, stop immediately and do not retry with an evasion technique. Fall back to
offline game data, external telemetry, or developer-supplied evidence. Vulkan
layers must be process-scoped and tool-managed, never globally registered.
Capture the minimum necessary Character Info frame/resources, redact account or
authentication data, keep proprietary captures local, and record tool/client
hashes plus a no-bypass attestation.

The installed retail build currently includes signed AntiCheatExpert user-mode
and kernel components, and no documented profiler allowlist or official
no-anti-cheat capture mode has been found. Any explicitly authorized read-only
hook is therefore an acknowledged-risk, minimum-duration diagnostic: attach
once through the normal user-mode API, stop on refusal or termination, and do
not attempt bypasses or protection changes. External telemetry, logs,
screenshots, runtime-generated caches, and offline installed data remain the
fallback route.

The shipped `build-system-profiler=1` flag is not a recovered render-state dump
switch. A whole-GameAssembly call audit found the built-in HGRP draw, shadow,
and render-graph diagnostic entry points unrooted in the retail call graph;
HGRP also disables the runtime debug UI. Do not try to invoke those private
methods through a hook. Details are in
`memory/character_render_and_animation_recovery.md`.

The approved narrow runtime hook is configured in
`config/shader_runtime_trace_hooks.json`. It is build-hash-locked to the current
`Endfield.exe`, `UnityPlayer.dll`, `GameAssembly.dll`, and IL2CPP metadata and
also validates the exact 12 bytes at `UnityPlayer.dll+0x541500`. It observes
only the renderer-list source slot and entry `+0x08/+0x0C/+0x4C` fields. The
agent pairs adjacent source slots 0 and 1 with the same renderer-data index;
these are candidates until actor isolation or repeated cross-capture evidence
identifies the eye renderer. It never invokes a render method or changes state.

The combined Mission plus shader listener uses one normal Frida session. Arm it
from the repository root before starting the game, select the matching actor
target, then open and settle that Character Info view:

```bat
tools\frida-runtime\venv\Scripts\python.exe scripts\story_recovery\runtime_trace.py capture --profile mission --shader-target wulfa-settled
tools\frida-runtime\venv\Scripts\python.exe scripts\story_recovery\runtime_trace.py capture --profile mission --shader-target zhuangfy-settled
```

Other configured targets are `lizhiyan-settled` and `lastrite-settled`.
Mission events and shader events are written to separate sibling JSONL files;
agent failures and the 100,000-pair safety cap go to diagnostics. Shader
sampling is initially gated so startup rendering cannot consume that cap. Once
the configured Character Info view is settled, create the unique empty
`.start-shader` trigger file printed by the launcher; Mission observation stays
active before and after the shader window. Use `--shader-start-immediately`
only when attaching to an already settled target. The launcher
waits for both `GameAssembly.dll` and `UnityPlayer.dll` after attaching, and
fails closed on any file, target, or hook-byte mismatch. If normal attachment
is refused or the client/protection terminates, stop and use the external path
below; do not retry through evasion.

The lab-local external telemetry harness implements that active route without
launching, attaching to, injecting into, or patching the client. First validate
the discovered files and tools while the game is stopped:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\capture_original_client_external_telemetry.bat -PreflightOnly -NoWpr -NoPresentMon
```

For a real sample, launch Endfield normally, navigate to the settled Wulfa or
Zhuangfy Character Info view, leave it unobscured, then run this from a second
terminal:

```bat
.\capture_original_client_external_telemetry.bat -DurationSeconds 30 -SampleIntervalMs 500
```

The default run uses three external data sources when available: NVIDIA
FrameViewSDK PresentMon filtered to `Endfield.exe`, `nvidia-smi`, and the
built-in WPR `GPU` ETW profile. PresentMon is time-bounded, disables input
tracking, and never launches the target. WPR runs only from an already elevated
terminal, only when no existing WPR recording is active, and the harness never
requests elevation. Use `-NoWpr` from a normal terminal, or
`-NoPresentMon` to omit process-filtered present telemetry:

```bat
.\capture_original_client_external_telemetry.bat -DurationSeconds 30 -NoWpr
.\capture_original_client_external_telemetry.bat -DurationSeconds 30 -NoPresentMon
```

Every run creates a new
`scratch/original_client_external_telemetry_<timestamp>/` directory. Its
`manifest.json` and `no_bypass_attestation.json` record the exact scope and
tool/client hashes. Other artifacts contain only whitelisted Player-log render
lines, whitelisted raw graphics-registry values with no guessed enum meanings,
read-only client/process/protection metadata, PresentMon CSV, bounded GPU ETW,
and GPU counters. No command lines, loaded modules, process memory,
credentials/tokens, network traffic, or keyboard/mouse input are collected.
If no normally launched client exists at the expected signed executable path,
the harness records the refusal and exits instead of starting the game.

Disposable capture probes can be built from Unity with:

```text
Endfield > Character Recovery Lab > Build Wulfa Baked Capture Probe
Endfield > Character Recovery Lab > Build Wulfa Sanitized Iris Capture Probe
```

The batch builder also accepts `-endfield-capture-probe-mode` with
`environment`, `swatches`, `wulfa`, `wulfa-no-props`, `wulfa-baked`,
`wulfa-sanitized`, `zhuangfy`, or `full`. Renderer-range arguments are available
for binary isolation. The generated probe is a copy of the fast scene, removes
the catalog-bearing `Characters` root that corrupts standalone scene loading,
and never saves over the authoritative scene or actor prefabs. The live-skeleton
`wulfa`, `wulfa-no-props`, and `zhuangfy` modes also reuse the exact imported
operator overview lights, follower-bone formulas, and recovered operator
camera. Skeleton-stripped baked/sanitized modes deliberately do not claim live
followers.

For a deterministic PNG after real player frames, launch a normal (not hidden
or minimized) D3D12 probe window with:

```text
-endfield-png-capture
-endfield-png-capture-output <png-path>
-endfield-png-capture-delay-frames 180
-endfield-png-capture-timeout-frames 600
-endfield-png-capture-quit
```

The capture logs current/target exposure, average EV, measured async-readback
latency, byte count, and SHA-256 before exiting. A hidden Windows player may
advance coroutines without presenting camera frames and is therefore not a
valid visual/exposure test. The original histogram meters raw scene color
before bloom/Uber: backdrop radiance is exposure-scaled in Uber, while
CharacterNPR output divides by the same scalar first and mostly cancels it.

When the player is launched through RenderDoc, its opt-in one-frame trigger is:

```text
-endfield-renderdoc-capture
-endfield-recovered-post-semantics
-endfield-recovered-cloth-specular-mode 2
-endfield-renderdoc-delay-frames 120
-endfield-renderdoc-timeout-frames 600
-endfield-renderdoc-capture-path <capture-template>
-endfield-renderdoc-quit-after-capture
```

The runtime component only binds an already injected `renderdoc.dll`; it never
loads one itself and refuses non-D3D12 devices. A validated full static Wulfa
capture is kept under
`scratch/renderdoc_unity_d3d12/wulfa_full_baked_cleanroot/`. It proves the
reconstructed pass/resource state, not live skinning or original HGRP behavior.
The exact-cubemap cloth capture is under
`scratch/renderdoc_unity_d3d12/wulfa_cloth_mode2_cubemap_20260712/`.
Its strict audit proves that 12 real Wulfa cloth draws bind
`T_hdri_reflection_char_01` as a pixel-visible 128x128, six-face, eight-mip
BC6H TextureCube at the shader's declared cube register. See
`scratch/rdc_audit_cloth_cubemap_20260712/recovery_note.md` for hashes and the
dynamic-branch limitation.

This component is compiled into the standalone lab player only. It must not be
copied into or loaded by the retail client; any original-client capture uses an
external stock-profiler workflow governed by the boundary above.

Rotation is not required for the next useful game capture. For the missing
Zhuangfy entrance, start recording on another operator/list view, select
Zhuangfy once, do not touch the camera or UI, and keep recording for at least
15 seconds after she appears (20 seconds total is safer) at 3840x2160 60 fps.
Save it separately as
`ReferenceCaptures/Zhuangfy/overview_entry_60fps.mkv`; do not replace the
existing settled/tail recording.

After regenerating animation sample JSON/manifests, refresh only the small set
of clips used by the reference viewer with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\rebuild_reference_animations.bat
```

This preserves GUIDs and avoids rewriting the roughly 29 GB complete animation
cache during ordinary render/animation iteration. It imports frame-derived
position, rotation, and scale channels, uses linear key interpolation, applies
loop metadata, and keeps recovered additive layers synchronized to the base
clip clock.

After an interrupted Wulfa animation build, resume only absent Wulfa clips with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\rebuild_missing_wulfa_animations.bat
```

This entry point never clears or rewrites an existing `.anim` and does not
visit the Zhuangfy or Mifu animation caches. Run
`rebuild_character_recovery_scene_cached.bat` after it completes. Do not use
the full shared-viewer build as a cache repair when another actor's sample JSON
directory is unavailable, because the full build intentionally clears each
actor's generated assets first.

After regenerating Wulfa's widget hierarchy/mesh manifest, refresh only its two
private widget skeletons, one-bone meshes, and 11 companion clips with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\rebuild_wulfa_item_widgets.bat
```

Those clips bind all three original widget transforms and preserve the existing
animation/prefab GUIDs. The editor preview samples the matching `ui_prop` layer
beside the body clip and excludes optional props from camera framing.

## Rebuild

Rebuild the generated viewer assets and scene with:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\build_all_character_recovery.bat
```

Or from Unity:

```text
Endfield > Character Recovery Lab > Build All Canonical Characters
```

The rebuild reads generated character manifests under
`Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/<Actor>` and
`NonPlayable/<Actor>`, and writes per-actor Unity assets below the same actor
folder. The all-character viewer scene is
rebuilt from the manifest-driven importer and generated catalog. Lower mesh
LODs are skipped during import; rerunning the preview command also prunes older
generated scenes to `lod0` only. Complete catalog builds instantiate the
existing 31 playable prefabs without rebuilding their assets, then builds the
two nonplayable additions and restores all 33 resident scene instances. The
rebuild also
renders a quick preview to:

```text
D:\fluffy-dump\scratch\character_recovery\all_character_recovery_viewer.png
```

After editing camera, lighting, or material setup code, use the lighter preview
command when you do not need to regenerate character assets:

```text
Endfield > Character Recovery Lab > Render Shared Viewer Preview
```

Or from the command line:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_character_recovery_preview.bat
```

If the scene itself needs to be reset after layout or camera changes, but the
generated meshes/materials/animations are already present, use the cached scene
rebuild instead of the full asset rebuild:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\rebuild_character_recovery_scene_cached.bat
```

For checking distance-related cloth mip/depth issues, render the far-camera
preview:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_character_recovery_far_preview.bat
```

For Wulfa animation recovery, keep transform, root-motion, and float sidecars
current before rebuilding manifests:

```powershell
python D:\fluffy-dump\tools\endfield_acl_sampler\export_actor_samples.py `
  --clip-dir D:\fluffy-dump\scratch\wulfa_animation_clip_json\AnimationClip `
  --output-dir D:\fluffy-dump\scratch\wulfa_acl_samples_all `
  --actor wulfa --all-buffers

python D:\fluffy-dump\tools\endfield_acl_sampler\export_actor_samples.py `
  --clip-dir D:\fluffy-dump\scratch\wulfa_animation_clip_json\AnimationClip `
  --output-dir D:\fluffy-dump\scratch\wulfa_acl_samples_all `
  --actor loli --all-buffers

python D:\fluffy-dump\unity_endfield_graph_shader_lab\tools\unity_muscleclip_sampler.py `
  --clip-dir D:\fluffy-dump\scratch\wulfa_animation_clip_json\AnimationClip `
  --hierarchy-dir D:\fluffy-dump\scratch\wulfa_postmodel_hierarchy_json `
  --root-name chr_0028_wulfa_postmodel `
  --output-dir D:\fluffy-dump\scratch\wulfa_muscleclip_samples `
  --actor-token wulfa `
  --summary-json D:\fluffy-dump\scratch\wulfa_muscleclip_coverage.json

python D:\fluffy-dump\unity_endfield_graph_shader_lab\tools\generate_wulfa_unity_from_original.py
```

The Wulfa manifest combines 390 ACL `TransformBufferData` clips with 25 decoded
stock-Unity/MuscleClip samples. Root-motion and float/muscle scalar curves are
preserved as evidence. Current all-UI clips do not map the six extensions, but
a broader 793-clip original Wulfa/loli scan finds 318 clips animating at least
one and 76 animating all six. The compact fixture
`A_actor_loli_sprint_loop_sp_01` supplies 33 exact 60 Hz input frames for all
six slots with `SK_actor_wulfa_01Avatar`. The pinned retail-f5 replay now also
supplies all 33 final 486-node physical local-TRS frames after TwistSolve and
the later generic overlay. Its Unity transport is explicit opt-in and limited
to this exact Avatar/clip pair.

### RuriRipperImporter cross-check and Endfield humanoid ABI

The optional checkout at `tools/RuriRipperImporter` is useful as an independent
Unity Force-Text/YAML and Blender-side decoder. Its strongest reusable evidence
for this lab is the acceptance of both dictionary and single-key-list material
property shapes, GUID-linked texture aliases, exact rest/bind-pose handling,
interleaved vertex stream validation, cubic-Hermite curve evaluation, and
Avatar muscle-referential math. It does not recover the complete original NPR
shader graph; the lab's AnimeStudio bytecode sidecars and Ruri.ShaderDecompiler
path remain authoritative for compiled shader variants.

Do not apply RuriRipperImporter's stock 95-muscle humanoid solver directly to
Endfield. Recovered Endfield clips use a 206-entry `m_IndexArray` with 42
motion/root/limb-IK attributes and a 101-muscle range. The installed
`UnityPlayer.dll` name table proves that the six game-specific degrees of
freedom are inserted at Endfield slots 28/30/31/39/41/42: Foot Twist Roll,
Toes Left-Right, and Toes Twist Roll for each side. They are not appended at
95-100; later stock arm/finger channels shift accordingly. The standard
MuscleClip sampler and generated manifests preserve the corrected ordering and
binary-backed names.

The closest public engine baseline is installed separately as Unity
2021.3.34f1 changeset `25266724e7bd` with matching Windows IL2CPP support. Its
batch-mode `HumanTrait` probe reports 95 muscles and 55 human bones and none of
the six Endfield names. Exact binary comparison finds the stock 55-entry
direct muscle-to-bone table and 25-by-3 inverse selector table once each. The
retail f5 tables match after inserting the six named slots into the direct map,
shifting every later stock index, and filling the previously absent selector 0
on both feet plus selectors 1/0 on both toe bones. This makes public f1 a strong
native structure and function-matching baseline, but not an authoritative f5
physical-transform output oracle.

An isolated unchanged-source compatibility probe also tested the maintained
Runtime/Shader snapshot in public `2021.3.34f1`. All 11 packages, including
Timeline `1.6.5`, resolve, but managed compilation stops on exactly two public-
f1 shadow-API gaps: no three-argument `ShadowDrawingSettings` constructor and
no `BatchCullingProjectionType`. Shader compilation therefore never starts.
This is a useful public-f1 boundary, not a reproduction of proprietary retail
`2021.3.34f5`; the maintained viewer stays pinned to Unity `2022.3.62f3`.

Re-run the public ABI probe, synthetic numeric pose fixture, exact binary table
comparison, exact-Wulfa stock-95 control, Ruri fixture verifier, and complete
486-node source-derived Wulfa composition with:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\run_unity_2021_baseline_oracle.bat
```

Set `UNITY_2021_EDITOR` or `BLENDER_EXE` first only when those programs are
installed somewhere other than the pinned defaults in the wrapper. The Blender
steps parse Unity's Force-Text synthetic Avatar through RuriRipperImporter,
fail if its 21 compared stock bone rotations diverge by `1e-4` degrees or more,
and regenerate the explicitly mixed-authority Wulfa fixture. In that fixture
the 58 generic ACL tracks are exact original decoded values, while the 24
humanoid local transforms remain source-derived semantic predictions rather
than retail-f5 runtime output. That older mixed-authority public-baseline
fixture remains a differential diagnostic; the separate original-f5 full-pose
fixture below is the authoritative pinned runtime output.

Direct AnimeStudio export from the installed VFS resolves the exact Avatar
referenced by every one of 34 audited postmodel Animators, including Li Zhiyan,
Last Rite, Zhuang Fangyi, both Endministrators, and the full playable sample.
For Foot/Toes human bones 5/6/20/21, zero-muscle
`normalize(preQ * inverse(postQ))` matches the serialized skeleton pose within
`8.01e-6` degrees. The installed `UnityPlayer.dll` resolves
`Internal_GetZYRoll` through thunk RVA `0x14C020` to core RVA `0xA795C0` and
proves:

```text
tx/y/z = tan(selectorAngleX/Y/Z / 2)
Qaxes = normalize(tx, ty + tx*tz, tz - tx*ty, 1)
Qlocal = preQ * Qaxes * inverse(postQ)
```

All 34 exact Avatars agree physically within `3.34e-5` degrees, while still
requiring their serialized `preQ`, `postQ`, sign, and limits. Toe Up-Down is
selector 2; the added Toe Left-Right is selector 1 and Toe Twist Roll is
selector 0. RuriRipperImporter is corrected to the same stock and Endfield
mapping and now preserves over-range muscle values. Its 21-bone solve agrees
with the public 2021.3.34f1 Force-Text Avatar/`HumanPoseHandler` fixture within
`3.43e-5` degrees. This validates the shared public subgraph, not retail-f5
physical output by itself. The retail output is closed separately by the exact
replay/transport below. Instruction-level recovery now
closes GetZYRoll's own scaling: RVA `0xA796AB..0xA79737` selects lower/upper
limits by muscle sign and linearly extrapolates with no internal muscle clamp;
the following block reduces modulo `2*pi`, clamps only the half-angle near
`pi/2`, applies the Avatar sign bit to the tangent lane, and packs the known
quaternion. `tools/unity_muscleclip_sampler.py` now exposes
`muscle_to_selector_angle`, `from_axes_zyroll`, and
`avatar_local_rotation_from_muscles`. The raw `61+20+20` staging path and
`0xB25830/0xB25910 -> 0xB38B10 -> 0xB34260` production chain also contain no
stock `[-1,1]` clamp. A particular curve producer may still constrain its own
values earlier. That retail gather is now instruction-closed: `0xB25830`
iterates body bones `1..24`; `0xB25910` reverses the hash-pinned table's stored
selector order `2/1/0` into converter lanes `0/1/2`, zero-fills absent lanes,
and skips only compact mapping `-1`. Hand helper `0xB25300` converts each
four-value `(phalanx-1 stretched, spread, phalanx-2 stretched, phalanx-3
stretched)` group into three phalanx selector vectors and skips negative
compact mappings. The maintained sampler exposes the exact body and hand
gather helpers. Retail `0xB25B20` is now closed as the split-stage counterpart
of public `0x94D300`. Instruction-level comparison also closes
`0xB34260 <-> 0x95B8B0` for the humanoid ZYRoll path: both build
`normalize(tx, ty + tx*tz, tz - tx*ty, 1)` and then normalize
`preQ * Qaxes * inverse(postQ)`; their differences are compiler inlining and
register allocation, not a recovered equation fork. The remaining runtime
boundary begins after this per-bone local-quaternion conversion:
`HumanPoseHandler.SetInternalHumanPose` stages exactly 61 body plus 20 left-
finger plus 20 right-finger values and calls shared pose-to-skeleton core RVA
`0xB314D0`. That core has three additional native call sites at `0xA5B115`,
`0xAAB7BE`, and `0xB13713`. Icall and unwind evidence identifies them as the
`AnimationClip.SampleAnimation` worker `0xA5AD60`, lazy AnimationStream
materializer `0xAAB6E0`, and subordinate humanoid apply/reset stage `0xB13620`.
Its conditional helper `0xB31D10` is source-closed as the position-only
translation-DoF stage: it iterates the 21 non-Hips core bones and is disabled
in all 33 unique playable Avatars. It is not TwistSolve. Normal
`Animator.Update` is closed from thunk `0x177AB0` through scheduler `0xA64610`,
callback `0xA5AD10`, and `0xB314D0`. `0xB17DB0` is the separate bilateral
foot-goal rebuild. Real TwistSolve is `0xB323F0`: it invokes `0xB27930` for
eight ordered LowerArm/Hand, UpperArm/LowerArm, LowerLeg/Foot, and
UpperLeg/LowerLeg pairs. Each call scales parent selector 0, reconstructs the
parent, and compensates the child. The compact-to-physical mapping is now
closed across all 34 postmodel Animator referentials: every one of the 272
pair observations is an adjacent parent/child pair in both compact and mapped
physical skeletons. `0xB06170 -> 0xB33BD0` copies those exact 48-byte TRS
records to `m_HumanSkeletonIndexArray` destinations. Named Fore/UpArm/Calf/
Thigh twist nodes are direct side branches, so TwistSolve does not overwrite
their local curves; they inherit the corrected parent transform. All 33
exact playable Avatars use `(Arm, ForeArm, UpperLeg, Leg) = (1,0,1,0)`.
`human_fix_twist_human_local` exposes the recovered human-local quaternion
rule. Physical node ownership and propagation are no longer blockers. A
33-frame original fixture exercises all six added muscles and now has matching
retail-f5 physical Transform outputs for every node after ordered solve and
generic-curve precedence. Ordinary clip baking stays off; only the exact
Wulfa/SprintSP fixture is available through the fail-closed opt-in runtime.

That fixture now has an exact controller context. It is the sole node of
`Base Layer.Locomotion.Grounded.Move.SprintSP`, with Write Defaults enabled,
speed 1, looping, no mirror, `m_IKOnFeet=false`, and layer `m_IKPass=false`.
All 188 Wulfa states and all nine layers keep those two IK flags false. Recover
the output as base/rest initialization, all 101 muscles, separate Motion/Root,
and the nine authored generic `IK_*` QVV tracks, followed by compact conversion,
TwistSolve, and compact-to-physical TRS mapping. The exact state and optimized
job path skip the conditional bilateral foot-goal rebuild. Unity 2022 lab
playback remains validation-only, but its payload is the recovered
Unity 2021.3.34f5 numeric output oracle rather than a stock retarget.

Build the exact fixture, attach it to Wulfa, and validate all 33 frames plus
visible body deformation with:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\build_and_validate_wulfa_original_f5_full_pose.bat
```

The fixture applies 485 Transform paths (physical record zero is the virtual
root), preserves all 4,850 generic local-TRS bindings after the humanoid solve,
materializes 48 omitted Avatar support nodes from exact frame-zero TRS, and
fails closed on a missing binding. It defaults off and never moves the resident
lineup root. This closes one Avatar/clip pair, not Motion placement, runtime IK,
blending, constraints, secondary simulation, or general humanoid playback.

Original serialized data and `GameAssembly.dll` also narrow the IK contract.
Exact Grounder exports for all 31 current actors prove that the
`GrounderBipedIK.solver.IKFootBoneL/R` PPtrs equal the authored
`IK_Foot_L/R_001` Transform PPtrs. They are sampled Grounding references, not
BipedIK limb targets. `CharacterAnimationBlackboard._UpdateFootIK` at RVA
`0x3413830` reads `FOOT_IK_WEIGHT`, `FOOT_IK_FOOT_WEIGHT`, and
`FOOT_IK_ADSORB_WEIGHT`; RVA `0x326CF60` transfers the live block to Grounding.
The complete current UI audit covers 779 unique clips and recovers only
`FootIKWeight` (`0x2B797234`): 24 exact 60 Hz ACL arrays, always scalar track
15 and constant one. `FootIKFootWeight` (`0xCF74E25B`) and
`FootIKAdsorbWeight` (`0x7E3D4086`) occur in zero UI clips. Their missing-key
lookup is nevertheless source-closed: `TryGetCurveValue` returns false/raw
zero, and `_UpdateFootIK` ignores the Boolean. The missing foot-weight key
becomes a smoothed grounded target of one; the missing adsorb key becomes
immediate one. The final pelvis recurrence is also recovered from the installed
base path: acceleration subtracts up to `0.8`, special-idle floor disagreement
attenuates the target, ultimate skill snaps, Run/Sprint may rise at rate 8
instead of 3, and air decays with `clamp01(360*dt)`. `_UpdateFootIK` does not
clamp that persistent result; `GrounderBipedIK.Update` separately clamps the
live component weight to `[0,1]`, and static code does not yet prove their
callback order. The exact arrays and source
provenance are generated in `playable_character_foot_ik_scalar_curves.json`.
Retail hand IK instead receives external targets from `CharLimbIKAction` exData
offsets `+0x48/+0x50`. Sampled bend goals are null and no weapon consumer is
recovered. The diagnostic lab solver therefore remains off, and distance-based
hand/knee/foot activation is not treated as original behavior.

The retail quality-3 Grounding base path is source-closed for both coordinate
frames; full prediction and exact capsule no-hit branches remain open.
`Grounding.Update` at RVA `0x326D370` performs root hit,
bilateral leg terrain processing, pelvis correction, then the final leg-length
clamp. Root/foot samples use the Raycast delegate; foot volume uses CapsuleCast;
missing ground produces a height-continuous synthetic plane rather than a zero
hit. `SetLegIK` at RVA `0x326CB90` requests
`lerp(authoredFoot, terrainFoot, clamp(weight*maintianPelvisFootWeight,0,1))`
and assigns `footAdsorbWeight` to the limb position weight. The manifest records
this contract. Twenty-eight actors select this ordinary family; Chen Qianyu,
Li Zhiyan, and Liino set `rotateSolver` at `Grounding+0x9C` and use the recovered
root-aligned frame (`root.up`, root-forward/right, and root-local Y); Camille is
ordinary. `Grounding+0x3D` is `isAccelerating`, not the rotate gate, and the
rotated blocks rejoin the same `FinalSetIKPosition` and `SetLegIK` stages. The
query delegates are installed by the original Grounding constructor, every
cast uses `QueryTriggerInteraction.Ignore`, and root/foot acceptance follows
the recovered ECS/Unity Collider rules. `OnAnimationSetup` overwrites component
masks with `MovementSetting._ikLayers`, so Da Pan/Deepfin's serialized zero
masks are not final runtime masks. Both installed full MovementSettings carry
the exact same mask, `0x00300000` (`Terrain|IK`), and installed movement
modifiers including `MSM_Lizhiyan` have no mask field. The guessed lab solver
remains disabled because the lab still lacks a source-compatible terrain
provider, live controller values and callback order, Unity
runtime profile consumption, the retail pelvis-aware solver surface, and
numeric original-frame fixtures. Exact per-actor serialized profiles are now
embedded in all 31 manifests and in
`playable_character_grounder_profiles.json`; none is runtime-enabled.
Alternate-quality, overstep-disabled, full predictive-step, and exact capsule
no-hit modes remain unrecovered; tilted-root numeric fixtures are also absent.

Root motion is split by ownership: `MotionT/Q` is object trajectory, while
`RootT/Q` is the absolute skeleton body reference and must never be applied to
the GameObject. Character Info's native callback applies only
`worldQ = normalize(worldQ * animator.deltaRotation)` and never translation.
Gameplay routes evaluated Animator deltas through `RootMotionData`, yaw warp,
`VelocityMixer`, movement modes, collision, and the motor. That gameplay object
application remains disabled until controller blending/cycle accumulation and
the downstream movement pipeline are closed. Preserve decoded Motion/Root
sample counts exactly; both looping and non-looping clips can omit a terminal
sample.

Refresh only the recovered ABI and IK evidence inside existing generated
manifests, without invalidating or rebuilding the large source/animation
caches:

```bat
python tools\refresh_animation_runtime_evidence.py
python tools\refresh_animation_runtime_evidence.py --check
python tools\character_import\grounder_profiles.py --check
python tools\character_import\foot_ik_scalar_curves.py --check
validate_playable_ik_recovery.bat
validate_resident_character_lineup.bat
validate_roster_animation_switch_runtime.bat
```

The current validation scope covers all 31 fail-closed IK pose checks, all 24
exact `FootIKWeight` arrays, the 31-instance resident lineup, and the complete
779-body-clip roster switch sweep. Source-backed audits retain fail-closed
canonical-order, skin-tuple, item-owner, and post-reset pose checks.

## Current Fidelity Limits

This is a compatibility reconstruction, not the original HGRP runtime. The lab
now reproduces the character-global control contract, explicit character passes,
correct data-texture color spaces, the recovered live-shadow blend, and an
opt-in shipped `ACES_modified`/CharInfo post branch. It also imports the exact
BC6H character cubemap and exposes shipped cloth GGX/DFG/cubemap and hair-lobe
diagnostics, but their matched two-actor results are not consistent enough to
promote. The installed UnityPlayer fallback scorer now selects serialized
DefaultDeferred pass-0 pair 96 as the unique D3D11 winner for the exact settled
keyword request. Its original VS and PS each execute once in a fail-closed
standalone D3D11 diagnostic with compatible neutral bindings; this closes
program identity and execution, not production-frame resources or numeric
fidelity. The lab now has an exact single-active-character CameraVirtualLight fit and
64-tap receiver, a fail-closed 151-renderer regular LOD0 realtime-caster
diagnostic, retained source-exact desktop LOD1 proxy evidence, and a
slot-swap-validated default-off multi-actor atlas using the retail
rendering-layer carrier, a default-off exact subset of the old cloth/hair punctual NPR
loop, an isolated Wulfa/Zhuangfy soft-Rim punctual atlas producer, a
GPU-validated default-off PreGBuffer producer sidecar, and a GPU-validated
CharInfo RG8 screen-mask G resolve with an executed default-off Forward
consumer. The latter proves the focused one-actor
stencil/selector/depth/normal/CameraVirtualLight topology and actual
Skin/Cloth/Hair/Eye diagnostic binding, but mixed material-reference results
and unrecovered retail surface ownership prevent global promotion. The lab now
executes all 14 active character-shadow slots (the shader ABI retains 15), but
still lacks the generic ECS backend/live caster census, complete client
consumption, and target-frame punctual visible-light/caster membership plus
physical atlas contents,
capsule visibility-SH and generic scene-R screen-space shadow resolve, full pre-depth/stencil
schedule, irradiance-volume sampling, the native arbitrary-scene light
candidate list and full eight-word camera-cluster population (pass-0
Skin/Eye/Cloth/Hair all use 32-pixel XY plus linear Z; world-XZ cells belong to
RayTracingReflection),
motion vectors/TAAU history, exposure history, interactive backbuffer state,
fog/DOF, and source-level Unity renderer changes. The pre-exposure pair,
histogram and adaptation equations, `ACES_modified` LUT placement, final sRGB
OETF/dither, raw FinalPass alternative, initial camera settings, and a strict
capture-only one-encode target are recovered, but they are not yet a complete
live path. The operator subset now evaluates the exact nine `Bip001`/
`Head_Local` light followers from the sampled actor pose and applies HGRP's
priority/distance ordering to the isolated overview list. It still bypasses
the native `HGCullingSystem.CullLights` producer and live interleaved
scene-light list. For the isolated overview list only, an opt-in path now
publishes the exact recovered 32-pixel XY and one-unit Z masks to the supported
Cloth/Hair/Eye subsets and to all 14 selected Skin rows. The two shadowed Skin
Rim rows execute only when the separately verified isolated atlas publishes
their exact row-4 mapping; failure still closes those rows rather than
substituting a tuned fallback.
Hair now decodes the exact CP10/custom-per-draw packed rain/wet/wet-global/snow
carrier, including the original diffuse and dual-strand darkening scales, and
imports `_DisableRainEffectOnMaterial` from the original Materials. The static
overview state is neutral; a live per-renderer publisher is still absent. Skin/face
energy, shell outlines, behind-hair overlay ordering, and visibility-buffer
edge behavior remain incomplete; face-SDF direction now uses the exact raw
renderer object-to-world basis. Runtime exposure history and the proprietary
character-index caster path cannot be recovered from static assets alone.

Animation playback is now intentionally UI-first: two original overview body
clips per playable character, plus 14 overview item-widget clips whose private
rig bindings recover without gaps. Zhuangfy's original overview
start/exit/crossfade timing, interruption enum, and three named FloatBuffer
parameter values are represented. Wulfa's body/widget start and loop pairing is
controller-proven. Zhuangfy widget-03 has 39/39 transform bindings and a
controller-proven entrance activation, but those private Actor-copy clips stay
hidden. The finished ribbon comes from the separately imported 44-transform
Effect clone: the generated 4.5166667-second layer applies the authored
0.4833333-second source clip-in, 39 bound motion tracks and renderer
`material._TintColorAlpha` fade, then holds the invisible endpoint. Its bounded
VFXBaseV2 sample-stack shader is admitted only for the exact original shader
PathID and three material PathIDs. The shipped Lua director-start owner,
rarity-6 gate, `gacha_char_start_6` duration, and black-screen wait are now
source-closed, but this actor-local preview does not replay the full gacha
orchestration. `_ExposureWithMiscParams.y`, `_VFXParams0.xyz/w`, the selected
sceneMV MRT/snapshot chain, and 52 exact gacha particle/EntityVFX materials now
have a source-backed compatibility path. The remaining eight mode-4 material
variants, retail captured-frame attachment/pixel comparison, facial
blendshapes, events,
explicit root-motion application, and secondary hair/cloth/tail dynamics still
need dedicated runtime systems. All three piaodai materials serialize
`_IsSceneEffect=0`, so the selected source program bypasses `_VFXParams1`.

Li Zhiyan's retail video oracle is imported separately from draw ownership:

```bat
python tools\build_lizhiyan_retail_draw_observation_contract.py
python tools\build_lizhiyan_retail_visual_oracle.py
python tools\build_lizhiyan_overview_timing_alignment.py
python tools\build_lizhiyan_overview_start01_contract.py
```

The current fixture pins `videos/2026-08-15_10-32-32.mkv` by byte count and
SHA-256, validates its 3840x2160 H.264/BT.709 stream and integer 1/1000 PTS
time base, and keeps `visibleAdmission=false`. Optional positive and negative
trace inputs are offline imports only; producing them requires separate
explicit authorization. Admission requires the complete HGMesh handle,
64-byte survivor record, stable resource generation, `0x2748`, descriptor
state, `0x2731`, descriptor bind, draw, submit, and exact retail pixel chain,
plus a same-build Li-absent or Wulfa control. Generic API-2 events, pointer
equality, timestamps, or teal pixels alone never admit the effect.

The visual-oracle builder separately decodes exact PTS
`38000/40000/42000/43000/44000/46000`, scales each frame deterministically to
960x540 RGB24, and pins frame hashes plus fixed actor/teal ROI measurements.
It records the broad teal peak at PTS 40000 and the below-one-percent settled
baseline at PTS 46000. This is only a camera/timing/compositing regression
target: it stays `diagnostic_only`, keeps `visibleAdmission=false`, and cannot
unlock the seven fail-closed particle renderers.

The timing-alignment builder joins those frames to source controller data
without upgrading the visual candidate into an original event claim. The
10.7-second start clip enters at normalized `0.0058366423` (clip-local
`0.062452073 s`), exits at `10.68547903 s`, and uses a `0.014519697 s`
transition. The clip has no AnimationEvents. Current lab compatibility policy
publishes the request in the same restart call and would create/destroy the
finger effect at clip-local `0.895782073/3.229112073 s`; the original retail
request producer and epoch remain unknown. Exact frames bound the transition:
the prior actor is last stable at PTS 37667 and starts fading at 37683; blank
frames span PTS 37700..37950, and Li is first recognizable at PTS 37967. The
first teal edge is tentative at PTS 38167 and the first unambiguous teal slab is
PTS 38183. Treating 37967 as a candidate restart aligns PTS 40000 with the compatibility
finger window, but PTS 42000 still contains measured teal after that root would
have been destroyed at candidate PTS 41134. The one recovered finger effect
therefore cannot explain the full retail teal chronology; eleven other
serialized Li entrance requests remain unbound.

The first of those requests is now structurally separated from particle
effects. `P_fxui_lizhiyan_overview_start_01` is a root-mounted, non-looping
2.2-second static-mesh animation: five hierarchy nodes, four
MeshFilter/MeshRenderer pairs, no ParticleSystems, one shared mesh
`S_fx_lzy_tiaodaifenwei_01`, and materials
`M_fxui__lizhiyan_overview_09/_10/_11` at queue 3704. Its EffectSetting,
transforms, renderer state, converted OBJ, and three serialized VFXBaseV2
material payloads are pinned in `lizhiyan_overview_start_01_effect.json`.
Start AnimationClip `A_fxui__lizhiyan_overview_start_01` (PathID
`7360398354216100382`, 30 Hz, 6.366667 seconds, no AnimationEvents) and all
eight referenced Texture2D identities plus converted PNGs are also closed.
All 53 material float curves are now resolved. Unity's own
`Animator.StringToHash` maps four paths to the start_01 renderers and six to
the sibling start_02/start_03 mesh-effect roots, proving the three effects
share this clip. AnimeStudio's CRC28-plus-channel encoding resolves the seven
attributes to `_MainTex_ST.x/y/z/w`, `_TintColorAlpha`,
`_DissolveScheduleOffset`, and `_DisturbUIntensity1`. The builder publishes a
name-complete `.anim`, and Unity `AnimationUtility` imports exactly 53
MeshRenderer curves with all ten paths and seven properties intact.
Native mesh/texture payload parity, selected shader variants, and an admitted static-mesh importer/binding remain open,
so no prefab is materialized and visible admission stays false. Do not route
this effect through the particle marker or invent ParticleSystems.

The runtime now distinguishes `Particle` and `StaticMesh` bindings without
changing the serialized default for existing particle effects. The new
`EndfieldRecoveredStaticMeshEffectSource` carries the exact start_01 root,
EffectSetting, Animator, animation-helper, clip, mesh-filter, renderer, mesh,
and material identities. Its admission gate additionally requires the source
aggregate, an empty blocker list, zero ParticleSystems, applied native
mesh/texture/renderer payloads, and admitted exact shader variants. The current
contract deliberately fails at `sourcePayloadApplied=false` and
`visibleAdmission=false`; no start_01 prefab or controller binding is created.

The pinned IL2CPP build now closes the managed consumer chain:
`AnimatorBehaviourPlayEffect.OnStateEnter` publishes the authored request,
`AnimatorBehaviourPlayEffectHelper.Add` creates/starts the effect instance,
`EffectSetting` initializes and plays `EffectLodCfg`, and `EffectAnimation`
builds a PlayableGraph with AnimationPlayableOutput and
AnimationClipPlayable. For start_01 the serialized LOD rows prove a root
Animator plus four MeshRenderers and null particle pointers. This rules out an
invented AnimatorController and makes an EffectAnimation-compatible playable
driver the intended lab implementation. The renderer pointer has not yet been
joined to a specific renderer-list/API-2 record or final draw.

The exact graph contract is narrower than stock Unity's common mixer path.
Retail `_CreatePlayableGraph` selects `GameTime`, scale one, and a three-input
`UnityEngine.Animations.AdvancedAnimationMixerPlayable` whose slots are
start/loop/end; these Li effects populate only start. That custom retail
AnimationModule type is absent from both the installed stock Unity 2021 editor
and this lab's Unity 2022 editor. The validator therefore rejects standard
`AnimationMixerPlayable`, Timeline mixers, clip stretching, and manual
evaluation as unproven substitutes. The generated
`lizhiyan_effect_animation_playable_topology.json` contract remains
`visibleAdmission=false` and no graph driver starts until the advanced-mixer
semantics, time-control callsites, static renderer payload, and final draw
ownership are closed.

The fixed-build ABI now distinguishes the advanced type from stock more
concretely: stock mixer creation takes `normalizeWeights` and exposes an
implicit Playable conversion; the advanced type exposes neither. Its injected
creation path is UnityPlayer internal-call entry 501 at `0x180158B30`: graph
validation allocates/attaches native node type `0x178` and materializes a
pointer/version handle. Stock creates node type `0x170` with a different
initializer. Input count is applied afterward through `SetInputCount`, so
Advanced and stock use the same count/weight virtual functions. Each 16-byte
slot is cleared on growth or reactivation, producing a null playable and zero
weight with no automatic normalization; negative counts diagnose. Advanced
then differs by its root vtable and the `0x0101` word at node `+0x170`.
Advanced-only slots 3/4/13/18/19 read or mutate `+0x170/+0x171` and gate
animation-runtime behavior, while stock uses no-ops or different methods.
Consequently a stock mixer with explicit weights is only a labeled visual
approximation even for the start-only Li graph, not a retail-equivalent
backend. Null transitions and extreme allocation failure remain open.
The initial state is `1/1`: slot 3 performs a first-valid-evaluation handshake
through `0x180A5A680`, clears `+0x171`, then uses computed evaluation time with
`0x180A634D0` on later passes. Slot 4 sets `+0x170` before stock time/speed
propagation; slot 13 handles state-reset commands; slots 18/19 suppress generic
runtime callbacks only when both bytes are zero. Native scheduler ownership
and those two runtime callback semantics are not yet closed, so a
`ScriptPlayable<PlayableBehaviour>` cannot currently be labeled exact.
The callback bodies are no longer opaque: `0x180A5A680` resets the packed
context state at `+0x9E8..+0xA0C`; `0x180A634D0` selects a 28-byte stage record
and calls `0x180AC4A90`, a four-mode custom timeline state machine that advances
time, changes stages, writes time back at boundaries, and updates node/state
flags. The exact mode names and unique scheduler dispatch remain open. This
cannot be expressed as retail ABI through public Playable APIs; an exact path
requires a native custom node/shim, while a full managed rewrite must remain
labeled behavioral simulation.
The same contract pins `SetManual(bool)`, `ManualEvaluate(float)`,
`SyncProgress(float)`, time-scale/start-duration/start-
scale setters, Stop, OnDisable, and OnRelease. Their decoded fallback bodies
prove graph evaluation, progress-to-time delegation, forced root-speed
refresh, stop, valid-graph destruction, and the corresponding
`EffectInstance` forwarding routes. Each method also has an IFix dispatch
gate, but the currently installed 86,926-byte Persistent patch is parsed to a
unique 32-record target table and contains no `EffectAnimation`,
`EffectInstance`, or `EffectLodCfg` target. The fallback bodies are therefore
effective for this hash-pinned local snapshot; later downloads and live table
mutation remain outside the offline contract. No Li-specific caller
currently opts these three roots into manual evaluation, progress sync, or
duration retiming; speed-one GameTime playback remains the only admitted
timing statement.

The graph's visible state control is exact as well. `_AddClip` connects each
non-null clip output zero to mixer input `animationState-1`; null loop/end clips
return before creation or connection. `_PlayAnimation` writes all three input
weights one-hot, plays the selected valid clip, pauses every other valid clip,
and resets each valid clip to time zero. Thus Li's start-only route connects
only slot zero, writes `[1,0,0]`, then performs `Play` and `SetTime(0)` on the
start playable. It does not cross-fade or synthesize loop/end playables.

The two sibling roots are now source-closed as the remaining halves of that
shared clip. `start_02` is a 5-second, three-renderer effect using one Plane009
mesh and materials 12/13/14; `start_03` is a 7-second, three-renderer effect
using `S_fx_shoutiaodai_01` plus `S_fx_tuoweidisan_01` and materials 15/16/17.
Both have root Animators, null controller/avatar, null particle LOD pointers,
and the same start AnimationClip. Together they add six static renderers, reuse
the same eight texture identities, and remain visibly fail-closed.

The exact managed LOD renderer bindings are now part of the playable-topology
contract: start_01 has four non-null MeshRenderer PathIDs and start_02/start_03
have three each. `EffectLodCfg.Play/Stop` owns their enabled lifecycle. This
does not yet identify a native HGTree survivor: the missing edge is a concrete
managed Renderer pointer/instance id to the native entity/renderer index and
one accepted 64-byte renderer record. ECS component slot 67 is independently
classified LOD/culling state and is not substituted for that identity edge.
Ordinary `Renderer.get_entityID` is now pinned to internal-call entry 1278 and
returns backing native Renderer `+0x268`; `HGMeshRenderer.GetEntity` instead
returns its ECS qword at native `+0x50`. The serialized Li references are
ordinary MeshRenderers, and these two fields are not treated as equivalent.
The managed `Renderer.get_entityID` wrapper has zero direct callers in the
current GameAssembly `.text`; similarly numbered HGTree vtable `+0x268` calls
operate on HGTree contexts rather than Renderer objects. This rules out the
obvious static identity bridge without claiming the runtime-indirect route is
absent.

The candidate retail epoch now produces exact material-key checkpoints rather
than a broad visual guess: start_01 child `(7)` begins changing at PTS 38167,
matching the first tentative teal edge; the other start_01 slabs begin at
38234/38267; start_02 begins at 40834/40867, adjacent to the observed 40900
pillar phase; and `start_03/S_fx_tuoweidisan_01` begins at 42467. These are
candidate time alignments, not proof that a particular screen-space bar belongs
to one renderer. The 2.2/5/7-second EffectSetting lifetimes deliberately expose
different portions of the same 6.366667-second clip at speed one.

One original dialog facial asset is now executable as a bounded source fixture:
Zhuang Fangyi's 2.15-second
`dlgtl_e10m2_5_sub_1_npc_chr_0030_zhuangfy_2`. It evaluates 12 original named
controls and 102 AvatarData bone deltas over the neutral face pose, uses the
retail Maya-Euler conversion, creates no synthetic controller hierarchy, and
fails closed on missing names, counts, mappings, or targets. Playback is
explicit-only (`playOnEnable=false`), matching Timeline ownership rather than
autoplaying a dialog expression in the Overview scene. Verify its source
contract with:

```bat
.\verify_named_facial_animation_recovery.bat
```

The source-closed baseline automatic blink is also executable for Wulfa and Li
Zhiyan only. Both exact NPC and face-avatar records serialize `disableBlink=0`.
The runtime preserves tracker type 10, the original
`normal01 -> data_facialmorph_anim_blink_02` ownership, all six 0.5-second
named Hermite curves, each avatar's own 50/38 mapped bone deltas, the
per-`SkeletalMorphCore` blink/speye random index, immediate first eligible
update, deterministic `[3,4)` cooldowns, and dialog-authored
pause/resume/stop-current behavior. It runs after neutral pose restoration and
before the generic named facial track, creates no controller transforms, and
fails closed on any missing source mapping. Rebuild and validate the two exact
prefabs with:

```bat
.\build_automatic_facial_blink_recovery.bat
```

This does not yet generalize all dialog assets or implement lip-sync, speye/eye
look-at inputs, broader emotions, face material curves, or cross-track event
chronology.

## Layout

```text
Assets/EndfieldGraphShaderLab/
  Editor/CharacterRecovery/                 viewer rebuild tools
  Runtime/                                  runtime viewer/playback/render helpers
  Shaders/Recovered/                        active CharacterNPR recovery suite
  Shaders/                                  older experimental/reference shaders
  Generated/Characters/Catalog/             source-derived playable roster/UI catalog
  Generated/Characters/Playable/<Actor>/    UI-first per-character assets and manifests
  Generated/Characters/NonPlayable/<Actor>/ canonical NPC/cutscene character assets
  Generated/Characters/Scenes/              shared viewer scene
  Generated/Characters/Shared/              shared generated support assets
```

Project-local data-generation helpers live in:

```text
D:\fluffy-dump\unity_endfield_graph_shader_lab\tools
```

The maintained all-roster importer is grouped under
`tools/character_import/`, with user-facing wrappers under
`scripts/character_import/`. Older actor-specific source tools remain only as
historical deep-recovery helpers and may require retired scratch inputs; they
are not viewer inputs and are not the canonical path for adding a playable
character.

Use the maintained importer for a targeted actor:

```bat
import_playable_characters_ui.bat --actor wulfa
```

Only viewer/rebuild files are kept in this Unity project. Older shader-pack
references, shader smoke-test scenes, static OBJ render checks, and extraction
experiments were removed to keep this project focused on the single character
viewer scene.

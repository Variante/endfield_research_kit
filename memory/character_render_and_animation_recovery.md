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

The source-derived character-grade catalog now has 33 identities rather than
only the 30 `CharacterTable` playables. It adds the canonical character
postmodels `chr_0035_liino`, `chr_0036_jsspsi`, and `chr_0037_chenpast` and
keeps their original classification: Liino and JSSPSI are NPCs, while
Chenpast is a historical/cutscene clone. The current installed-data inventory
finds 199 postmodel containers, which collapse to 156 canonical identities
after removing 43 source-proven aliases/variants: 30 playables, two NPC
characters, one cutscene clone, 94 enemies, and 29 ability/prop actors. All
156 canonical postmodel identities now have a generated prefab path, split
between the 33-character lineup and separate non-playable galleries. Six
additional non-postmodel ambient NPC archetypes are also imported as visibly
labelled modular source kits. This closes source-model enumeration and baseline
geometry import, not authored-appearance, shader, or animation parity. Enemy,
ability, and archetype models must not inherit Humanoid, Character Info,
Grounder, or 101-muscle claims unless their own source data proves those
capabilities.

The largest remaining problem is no longer missing texture or camera data. It
is the coupled retail frame contract: exact material response across all
variants, the modified-HGRP light and shadow schedulers, the still-incomplete
shared depth/stencil/GBuffer producers, `SphereOutside` deferred lighting, `ShadowPlane`
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
transform baking remains disabled for ordinary clips. One pinned original-f5
fixture is now integrated as an explicit opt-in path instead: the 33-frame
Wulfa SprintSP oracle applies all 485 physical Transform paths after the
101-muscle solve and later generic overlay without using stock Humanoid
retargeting. Native hierarchy propagation is closed: all 272 TwistSolve pairs
are adjacent mapped parent/child nodes, while named twist nodes are untouched
side branches. The normal `Animator.Update` materialization edge and the
ordered eight-pair TwistSolve are recovered. The fixture retains its virtual
physical root as a non-applied record, fills 48 source Avatar support nodes
from exact frame-zero TRS, remains default-off, and fails closed on any missing
binding. Motion placement, IK, blending, constraints, secondary simulation,
and general clip transport remain separate work.

There is no honest single percentage for the whole effort. If rough
engineering ranges are useful, they should be read as scope estimates rather
than test scores:

| Layer | Current maturity | Meaning |
| --- | --- | --- |
| Static actor/CharInfo assets and serialized parameters | high, roughly 90%+ for the selected Overview scope | Most identities, payloads, transforms, textures, profiles, and selected clips are source-derived and validated. |
| Non-playable static model coverage | broad baseline, not visual parity | All 94 canonical enemies, 29 ability/props, and six ambient NPC archetypes have source-scoped manifests and prefabs. Only admitted baseline renderers are shown; runtime VFX, modular NPC assembly, exact material state, and animation remain incomplete. |
| Selected local CharacterNPR surface equations | medium-high, roughly 60-75% | Important cloth, skin, hair, eye, outline, shadow, and post equations are ported, but variant coverage and live inputs are incomplete. |
| Complete retail CharInfo frame behavior | partial, roughly 35-50% | Several exact diagnostic subgraphs exist, but the complete HGRP scheduling/resource contract is not active as one production path. |
| Final visual parity | not reached | Wulfa and Zhuangfy are recognizable and compositionally close, but still visibly different without close inspection. All 30 characters have not been retail-frame validated. |
| Playable UI animation clips | source recovery complete for the `all-ui` selection | 754 body clips and 321 private item/deco clips are represented across all 30 manifests and generated prefabs. The roster verifier reports all 30 animation providers present. |
| Original animation behavior | partial | All 30 main UI controller graphs are source-backed, but the legacy runtime executes only a bounded subset. The exact NPC -> face/ear avatar ownership and neutral base-pose-first job are active across all 2,680 resident bindings. Wulfa/Li tracker-10 automatic blink, one Zhuang named dialog fixture, and one exact Wulfa original-f5 101-muscle physical-pose transport are active and fail closed. The retail quality-3 world-up and root-aligned Grounding base paths, foot-key semantics, pelvis recurrence, `MovementSetting._ikLayers`, Grounder callback order, and external hand-target path are source-closed but not executed. Live controller values and cross-MonoBehaviour/Animator frame chronology, Grounding, shared prediction/capsule branches, broader emotion/controller execution, events, gameplay root motion, FX, secondary systems, and knee/weapon constraints remain open. |

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

The latest full `build_all_character_recovery.bat` run rebuilt all 30 actors
and the shared viewer under the pinned Unity `2022.3.62f3` editor, exited zero,
and emitted no bounded C# compiler, shader, null-reference, or unhandled
exception diagnostics. Its log reports
`actors=30 active=Lizhiyan`; the actor record is visibly labeled
`Arcane (Li Zhiyan)` and contains 21 skinned meshes, 743 transforms, and 113
clips. This confirms that the earlier missing-Li symptom was an English
catalog/source-actor identity mismatch, not missing installed-game model data.
Zhuang Fangyi likewise builds with 16 skinned meshes, 650 transforms, and 50
clips; Last Rite remains present with 12 skinned meshes, 404 transforms, and 25
clips. The build log SHA-256 is
`8113DA73A0AE99B3D61C1F682B19A481AB315195C821BB6D5A280C47651D3ED5`.

The original `bg_charinfo_*` UIImage portrait is a real optional CharInfo
feature, not a second broken character mesh. It is now disabled in the normal
resident lineup and model-only roster captures because its pale actor
silhouette is misleading there. Dedicated portrait/roster-feature probes keep
the source texture, tight sprite mesh, alpha/depth contract, and explicit
enable path available for CharInfo reconstruction work.

`validate_resident_character_lineup.bat` verifies the saved scene and the
profile-switch path. The accepted run reports 30 active instances at 3.5-unit
spacing across 101.5 units; switching from the first to last alphabetical
profile moved the camera 101.677 units while preserving every instance ID.
The final corrected-texture D3D12 validation repeats those values with
`morphBindings=2680`, `earOwners=6`, and `blinkEligible=30`. After the exact
Wulfa/Li tracker-10 blink integration, the saved resident scene was rebuilt
from cached assets and the validator additionally requires
`exactAutomaticBlinkOwners=2`; its current Unity log SHA-256 is
`C60D2D9F057DA62AF8740FCF08CDC6FD301C29A4132914228B0C9E4B9157176D`.
Resident active/transform/profile overrides are now explicitly recorded on
prefab instances. This prevents a targeted character-prefab rebuild from
silently reverting that actor to its legacy inactive prefab-root value; the
fix was caught when the Zhuang gacha rebuild made only Zhuang inactive in the
saved lineup. Generated playable prefab assets now keep their template root
active independently of the legacy scene-selected state, and the targeted
Zhuang runtime builder rebinds plus validates the resident scene after Unity
regenerates prefab-local file IDs. The exact regression rebuild reports the
16-track gacha runtime valid and then `allActive=true`,
`instancesPreserved=true`, and `runtimeLoadOnSelection=false` for all 30; its
Unity log SHA-256 is
`A5FCE39FEF9D65C4F6D72746CC70EB3F141942FCDFD72A69F29B9D25575701AC`.

The broader character-grade scene is:

```text
unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/AllCharacterRecoveryViewer.unity
```

Run `import_all_character_models.bat --execute --unity` to refresh it and
`validate_all_character_resident_lineup.bat` to validate it. The scene keeps
all 33 roots active in one 3.5-unit horizontal lineup and switches actors by
moving the camera; it does not load or destroy models during selection. The
accepted Unity `2022.3.62f3` build reports Liino as 18 visible LOD0 skinned
meshes/543 transforms/one exact T-pose clip, JSSPSI as 16/561/one, and
Chenpast as 10/420/static. The validator reports `actors=33`, `span=112`,
`allActive=true`, `instancesPreserved=true`, and
`runtimeLoadOnSelection=false`. Current SHA-256 values are scene
`31D26F1B47FC576ABB40F364C269459266D06365231F7B53C3C92888C50106B0`,
catalog `3045B2BDCF20B0FDFFAC25F835F5A338444B6116285B1AB4448FE7AEF059A205`,
build log `A41ADD91F19F17349BE7EA2E259224C6CCC4CEBC1D385CF9282597986A1DFD1C`,
and validation log
`CEF8B88B1713759EB5DF37A4D23CA506ABCF8339C5959564554D482B724A1F71`.

### Non-playable actor galleries

Recover the complete canonical enemy/ability set plus the six source NPC
archetypes, then import their prefabs and build the resident scenes with:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
```

When manifests and prefabs are already current, rebuild or validate only the
scenes with:

```bat
.\build_all_generic_actor_galleries.bat
.\validate_all_generic_actor_galleries.bat
```

The generated scenes live under
`Assets/EndfieldGraphShaderLab/Generated/Actors/Scenes/`: four enemy batches of
at most 24, two ability/prop batches of at most 16, and one six-archetype NPC
batch. Every scene keeps its complete batch active at 3.5-unit horizontal
spacing; the dropdown moves one bounds-framing camera and never loads,
destroys, or replaces actor roots. Stale extra batch scenes are removed when a
catalog partition shrinks.

The accepted Unity `2022.3.62f3` run imports 129/129 prefabs and 428 admitted
renderer/mesh assets: 290 for 94 enemies, 99 for 29 ability/prop actors, and 39
for six ambient NPC archetypes. It also emits 387 collision-safe materials and
1,145 generated PNG assets drawn from 815 unique exact source texture files.
The manifests contain 17,113 transforms, 421 skinned plus seven static
renderers, and zero clips. Generated prefabs contain zero Animator components;
their empty legacy Animation components are compatibility hosts, not recovered
motion. The source planner resolves 1,453 Material texture bindings with zero
unresolved bindings. The strict aggregate validator reports
`scenes=7 roots=129 groups=94/29/6 resident=true
camera_only_selection=true` and no bounded compiler/shader/null-reference/
unhandled failure. The complete `character_import` regression suite passes
89/89 tests. Current SHA-256 values are catalog
`AC9AB42D3597BE9148E4AB4D94A26E655EFC1A8A9AB5299188E27251E0E3E91A`,
extraction plan
`30EA94F03369A43E69C400FA7F203F4571B82EAA07ABCDD2F43FA9D4EE8A7388`,
Unity asset-import log
`CFEE941A958D0F81110464F2DD622ED726941E2843FBD1EDEC74A03FDB5B3917`,
final seven-scene build log
`368E01AA4F824B1C703A341997E407E58D0F6CDFD9D69E975D877C1EF95CB5D3`,
and aggregate validation log
`92CF55FD3B73EA6EACC5650ADDCE545C1274FCF00E52F05A80BE6AE1BFF5613A`.
The asset-import log's earlier nine-scene partition was a catalog batching
mismatch; the final scene-only build changed the default partition to
24/16/16, deleted stale enemy scenes 05/06, and is the current accepted scene
state.

These are static generic/source-model galleries, not animation recovery.
Nefarcore is retained as a labelled external-geometry diagnostic because its
LOD0 renderer serializes a null Mesh PPtr; the importer does not invent a
mesh. The only admitted Unity built-in is exact file ID 2/path ID 10202, which
is a Cube. The mechanic ability actor with no local renderer, the particle-only
bomb actor, and the all-placeholder gentleman archetype remain labelled
zero-visible diagnostics. The six NPC archetypes are modular skeleton/material
slot hosts, not completed named NPC appearances.

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
| `scratch/character_ui_import/renders/*.png` | 30 current accepted 1920x1080 source-profile Overview model renders after exact neutral face/ear base-pose import, corrected original `TextureColorSpace` mapping across all 1,368 copies, exact Linear eye-mask BC7 chains, the complete 193-object/388-owner native face/iris/emotion and priority-surface payload contract, the source-backed LUT correction, and exact priority-character opaque/transparent hair queues. Key SHA-256 values: Li Zhiyan `BF1A8D8469C56D8F7D940455F746F51A7C756F53D08216FD76A9FD7C9137CE60`, Last Rite `7D895D9ABF07DDE1F7BB9482E258D7526509564072E038186F976E94EAA3935F`, Zhuang Fangyi `4D17FCD26A2994CFE8B6455FC04B2CF9AC2698ACDF9F61A4F9128E6DF8FAADE7`, and Wulfa `1D137BBD62954AEF87ACBE42C6C5723CC1CA4C6C4A175FB470DFDA0FE09F35A2`. The final post-queue-correction D3D12 batch exited zero with 30 successes, no pending/failures, passed strict PNG postflight, and emitted no bounded compiler/shader/null-reference/unhandled/crash diagnostic; its Unity log SHA-256 is `507488B1EAAE62107CA98D3AA0A9476132EEAE17370F9C486BF3CCE793A33E0F`, and the checkpoint manifest SHA-256 is `AA81FCF300270EE917B5F04FA1E15803B696DC2A831CB4BF17D46DBE13B71EA2`. The four priority PNGs remained byte-identical after the queue correction in isolated single-character QA, as expected when no overlapping pass changes the final color; the corrected ordering still matters to shared attachment/pass chronology. Direct inspection confirms Li is present, Last Rite has no detached white proxy models, and Zhuang's body-mounted items are visible. Face/hair lighting and eye-shadow parity remain visibly incomplete. The optional `bg_charinfo_*` UIImage portrait is intentionally disabled in this model-only set and remains covered by dedicated feature probes. |
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

The generated source inventory is
`reports/assets/character_recovery/nonplayable_actor_postmodel_inventory.json`.
Its 42 assertions pass with zero unresolved identities. Canonical selection
uses exact postmodel containers; `postmodels/npc` mirrors, Zhuang Fangyi's
`_ult` character variant, enemy variants, and ability-entity models are not
silently folded into the resident character lineup. Renderer dependencies are
resolved by Mesh/Material PPtr across containers because a postmodel container
is not a complete render boundary. JSSPSI is the clearest regression: its
canonical container embeds no Mesh object, while exact PPtr joins recover its
visible body meshes and materials.

Liino and JSSPSI deliberately exclude five and seven LOD0 `vfxpart`
placeholders respectively: the original renderers bind only
`DefaultHGMaterial` and depend on runtime VFX material overrides that have not
been recovered. Making them visible would recreate the detached white-model
failure. Liino's hashed eye-shadow material is resolved by container/path ID
to `m_eyeshadow_common_05.mat`; serialized name alone is not a safe material
identity. Exact `NpcInfoTable -> NpcTemplateGroupTable -> TextTable ->
I18nTextTable_EN -> PrefabInfo` joins supply `Liino` and `Si (Jsspsi)`.
Chenpast's source name is empty, so the source identifier remains the honest
display fallback and its exact PrefabInfo template is `npc_spl_chenpast_01`.

The two NPC character manifests retain the Endfield 206-index/101-muscle
layout metadata, but their playable UI-controller and Grounder contracts are
not claimed. Their canonical postmodel Animators have null controllers and
external Avatar dependencies. The current preview scope imports only exact
token-owned `A_actor_*_t_pose` clips for Liino and JSSPSI; Chenpast has no exact
token-owned preview clip and stays static. Separate original NPC controller
assets prove 11 Liino and five JSSPSI clip mappings, but controller-state
execution and those clip transports remain the next NPC animation phase.

### Non-playable actor source boundary

The maintained non-playable inventory and dependency guidance cover 94
canonical enemy postmodels, 29 ability/prop postmodels, and six supplemental
ambient NPC prefab roots. Exact source scope is the Animator asset root plus
its hierarchy; Mesh and Material dependencies resolve by `(fileID,pathID)`
inside that source chunk or an exact Animator-owned dependency record. Global
path ID or bare-name matching is forbidden. One hash-identical Persistent/
Streaming `fdcentur` Animator mirror collapses to one actor, leaving 129 source
roots and 131 exact Animator records. The dependency audit resolves 3,401
unique type/path-ID identities, with zero unsafe joins and zero missing
serialized Mesh/Material dependencies apart from Nefarcore's explicit null
mesh.

Source renderer totals are 1,173 enemy, 423 ability/prop, and 86 NPC
archetype records. The scene baseline admits only 290, 99, and 39 respectively:
LOD1+, source-marked shadow/VFX/entity placeholders, particle renderers,
`DefaultHGMaterial` NPC slot hosts, and unsupported/null geometry stay in the
manifests as exclusion evidence. This is intentional fail-closed behavior, not
silent loss. The six archetypes are especially incomplete: the gentleman root
has 15/15 placeholder renderers, while the other five expose only a subset of
their modular slots.

All 428 generated mesh paths are path-ID qualified and unique in Unity scope;
all 387 material paths are source-root/path-ID/hash qualified. The built-in
Cube and Nefarcore external-geometry cases have separate explicit contracts.
The generic manifests preserve source shader names, mapped properties, colors,
texture scale/offset, and exact resolved top-level PNGs. They do not yet
reconstruct the complete original material keyword/pass-enable/render-queue
state, renderer probe/sorting flags, native texture import descriptors/mip
chains, runtime material swaps, or VFX systems. Therefore a successful gallery
build proves source-model coverage and dependency integrity, not retail render
parity. The audit finds 12 original shader families mapped to eight current
Unity targets: 17/387 materials still use a built-in fallback. Only 222/1,145
generated texture copies match the existing exact character Texture2D profile
contract; 923 use property/name heuristics. There are 528 same-target secondary
references where first-reference-wins may choose the wrong import settings if
one source texture is reused through semantically different material
properties. Payload binding is complete, but descriptor/mip/color-space parity
is therefore explicitly open.

The generic importer intentionally emits no Humanoid manifest and no animation
clips. Original source evidence finds Animator controllers for 11 enemy roots
and 18 ability/prop roots, and Avatar references for 93 enemies and 22
ability/props, but those references alone do not prove a safe stock-Humanoid or
101-muscle transport. Recover exact controller-to-clip bindings and rig class
per actor before enabling animation. Particle-only and transform-only ability
actors remain valid catalog members even when they have no admitted mesh.
Across all 131 exact Animator entries, 31 controller PPtrs and 123 Avatar PPtrs
are non-null because mirrored/multi-Animator entries can exceed the canonical
root counts; none is currently executed.

### Playable roster and generated assets

- The `CharacterTable`-derived catalog has 30 rows that join to a concrete
  shipped `<charId>_postmodel` Animator, and all 30 are imported.
- `chr_9000_endmin` is an abstract selector row with no concrete post-model and
  is correctly excluded. Male and female Endministrator post-models are both
  included.
- The canonical generated root is
  `Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/<Actor>/`.
- Current generated inventory: 30 actor directories, 30 prefabs, 1,075 `.anim`
  assets, 411 path-ID-safe mesh assets, 448 materials, and 1,403 imported PNG
  texture copies, including 1,368 exact PathID-bearing copies.
- Seven fur meshes use a 32-bit source index buffer despite remaining below the
  usual 65,535-vertex threshold. Index width must therefore be inferred from
  original submesh byte offsets, not vertex count alone. The corrected targeted
  rebuild preserves GUIDs and the strict postflight now matches original vertex
  and submesh index counts for all 372 mesh assets and prefab references.
- Targeted character refreshes now rebuild selected mesh contents in place
  instead of reusing every existing `.asset`. This closed stale Ardelia cloth
  and fur skin streams without changing GUIDs. The source-only audit now checks
  338 selected LOD0 body meshes and reports zero differing skin tuples or
  positive-influence totals. The ACL provenance/order audit likewise resolves
  all 875 clips; large samples read `source_json` from their header while
  skipping the frame payload instead of incorrectly searching only the last
  64 KiB.
- Only LOD0 non-VFX body renderers are active in the character viewer. Lower
  LODs, ordinary actor VFX renderers, and shadow proxies are deliberately not
  stacked into the beauty render.
- Old duplicate generated roots `Characters/Wulfa`, `Characters/Zhuangfy`, and
  `Characters/Mifu` were removed. Their old 563-clip/roughly-29-GiB research
  cache is not the current canonical animation state.

The roster feature plan keeps nonblank structural renderability separate from
material source-input fidelity. The previous catastrophic fallback set has
been narrowed with original-data evidence:

- The filename PathID carried by every generated character texture now joins
  directly back to the installed AnimeStudio asset maps. A streaming parser
  resolved all 853 distinct encoded Texture2D objects used by the 30-character
  roster across 1,368 generated copies, with zero missing or content-hash-
  ambiguous objects. Original type-tree dumps prove formats 4 x56, 10 x3,
  BC7/25 x665 and BC5/27 x129; 757/853 objects have authored mip chains, and
  original color space is split 440 Linear to 413 sRGB. `Texture2D.m_ColorSpace`
  is the `UnityEngine.TextureColorSpace` enum (`Linear=0`, `sRGB=1`), not
  `PlayerSettings.ColorSpace`. Retail
  `Texture.GetTextureColorSpace(bool)` at GameAssembly VA `0x1837E0740`
  consists of `0F B6 C2 83 F0 01 C3` and returns `1-linear`, independently
  pinning that mapping. All 269 roster `_D` diffuse objects serialize sRGB/1;
  representative Wulfa, Zhuang Fangyi, and Li Zhiyan CharacterNPR fragments
  sample BaseMap directly, multiply it by BaseColor, and compute luma/saturation
  without an explicit IEC transfer function. The source therefore requires
  the sRGB resource view/hardware decode rather than a shader gamma patch or a
  global exposure correction. Before applying
  the full contract, the 72 Li/shared profiles covered 399 copies exactly but
  the remaining 969 copies still inherited filename heuristics: 802 had the
  wrong sRGB flag, 736 wrong streaming state, 851 wrong filter, 849 wrong
  anisotropy, 822-823 wrong wrap axes, 85 wrong mip enable, and 272 enabled
  alpha dilation. `character_texture_import_contract.json` now applies exact
  installed sRGB, mip/streaming/priority, filter, anisotropy, mip bias, and
  U/V/W wrap values to all 853 filenames, while forcing non-NPOT rescale and
  PNG alpha dilation off for these shader resources. The post-import census
  reports descriptor drift zero across all 1,368 copies; the maintained
  verifier is `tools/verify_character_texture_import_contract.py`, and source
  evidence stays under
  `unity_endfield_graph_shader_lab/scratch/character_recovery/all_character_native_texture_census/`.
  The corrected census report SHA-256 is
  `859DA4B3A2191BD3CCE5634B19A0565981E7380463EDDC29B82246056CEDCC77`;
  the import contract is
  `ADA322BA49EFEBDECD5B85F155147459D0FAC2272C789E26B61C96DB979D35F0`.
  Pinned Unity 2022.3.62f3 D3D12 reimport exited zero with log SHA-256
  `D77057D122BAD35C1D870EA460F1F6A91A7B34C3AC4E8CFFD4AA9C406EF0406B`.
  Exact native compressed payload preservation is also active for 193 source
  objects across 388 stable PNG GUID owners. This contains the prior 83
  face/iris/emotion objects plus 110 impact-ranked hair/body/cloth/accessory
  objects selected through original material PPtrs for Li Zhiyan, Last Rite,
  Zhuang Fangyi, and Wulfa. The contract covers 380,672,080 logical bytes and
  safely deduplicates them into 191 format/dimension/mip/view-compatible blobs
  totaling 378,924,400 bytes. Together with the two separately owned shared
  eye-shadow masks below, the current exact-payload scope is 195 source
  objects and 437 generated copies. The validator
  checks every mip byte, GUID, material PPtr (`fileID 2800000`), importer/runtime
  descriptor, source-object hash, and generated payload hash. Of the remaining
  660 census objects outside this contract, two are the exact eye masks; 658
  descriptor-only objects keep decoded top-level PNG pixels while Unity still
  regenerates/recompresses their lower mips. The complete raw 853-object
  extraction is retained locally, so this boundary can be expanded without
  re-reading the game VFS.
  The high-impact payload contract SHA-256 is
  `16565BF19AD3A4836712008A1BC1ECA876C9AB2510D676EB2246FF3FE18BFEEA`;
  its pinned-Unity validator report SHA-256 is
  `BCD3C3D0A761E872348FA98AD9FC652FC042D0BA2741C4BE5C11D5E1728DE888`.
- material PathID `7337858377406896398` resolves to canonical
  `M_eyeshadow_common_05` by its stable `_p65D54F510D76590E` suffix, even when
  the hash-derived map name differs. Ardelia, Bounda, Camille, Last Rite,
  Lifeng, and Zhuang Fangyi now retain the original OverlayShadow shader,
  `T_actor_common_eyeshadow_01_M`, blue-gray tint, and authored float values.
  The selected original pixel variant is
  `DISABLE_DRAW_UNDER_HAIR SRP_INSTANCING_ON`, fragment hash
  `e204d0d92c689bcd`; it sets gray-as-alpha to one and dither/predepth/VFX
  adjustments to zero. A targeted AnimeStudio dump pins the two shared masks:
  `T_actor_common_eyeshadow_01_M` PathID
  `1943856218045776426` and `T_actor_common_eyeshadow_02_M` PathID
  `2400241694096528712` are both 32x32 BC7 textures with six mips,
  Bilinear/Clamp/aniso-1 sampling, and serialized `m_ColorSpace=0`, which means
  Linear. An earlier recovery inverted the enum and reclassified these masks
  as sRGB; that was wrong. The exact fragment executes `SampleBias` and uses
  the sampled red channel directly as gray alpha, so an encoded value 173/255
  remains about 0.678 rather than receiving an IEC sRGB decode to about 0.418.
  The exact PathID-bearing import contract now keeps all 49 referenced copies
  Linear without widening filename heuristics to unrelated `_M` textures. The
  strengthened verifier also proves the 237 unrelated generated
  `_M_p<PathID>` copies retain their own source-derived profiles. Two no-suffix shared aliases are
  byte-identical but unreferenced and remain fail-closed rather than widening
  the classifier. The PNG paths now retain their existing GUIDs/material PPtrs
  while `EndfieldEyeShadowBc7PayloadPostprocessor` replaces the imported pixels
  with the exact installed six-mip `RGBA_BC7_UNorm` streams. Each stream is 1,392
  bytes with mip offsets `0/1024/1280/1344/1360/1376` and sizes
  `1024/256/64/16/16/16`; eye-01 hashes to
  `8DCAD11484FB24F20F77A1A3BF4A62D2DFC7E45ED3BC34A09ED7AC63461D86F7`
  and eye-02 to
  `90F826DF7FFBDC640DBB7FD625E2AD49047275B7438B8CE2909193F457A58B99`.
  The original dumps also prove `m_StreamingMipmaps=True`, priority zero. A
  pinned Unity 2022.3.62f3 D3D12 validation reimports all 49 copies (28 eye-01,
  21 eye-02), compares every raw mip byte, and confirms unchanged GUIDs. CPU
  readability remains enabled only for this small lab validation surface; the
  retail Texture2D objects serialize it false. Evidence is under
  `unity_endfield_graph_shader_lab/scratch/character_recovery/eye_shadow_bc7_payload/`.
  The corrected original-data contract SHA-256 is
  `22015E84486E9487047EA79493EF1ECD780CE6A71FC9F037F8E4D10DBBD51F2A`;
  its pinned-Unity validator report SHA-256 is
  `BAF03550BD9C8FF6F0538C89C925B025A9B21EDEF2EF8F1C8B9AC225841353BA`.
  All five common eye-shadow materials plus the shared eye-white
  material retain their exact BaseMap PPtr, tint, 20/4 stencil ref, angle,
  and feature flags. The maintained original-data contract is
  `Generated/OriginalData/RenderParameters/eye_shadow_original_data_contract.json`;
  it pins the installed CHK, texture dumps, six material JSON files, selected
  shader, and a representative Zhuang Fangyi LOD0 source-winding check. The
  cross-actor slot/order/neutral-pose audit and its 111-check verifier are under
  `unity_endfield_graph_shader_lab/scratch/character_recovery/eye_shadow_exact_current_retail/`.
  Because `DisableDrawUnderHair=1`, this exact eye/eye-white
  variant intentionally does not sample the opaque-scene suppression input. The
  no-keyword hair-shadow variant is separate: its exact D3D11 fragment is
  `0025_endfield_dxbc_1.dxbc`, SHA-256
  `0b0a85c057ef0b96966428a2370f98e0ef2b239f40696ddc39a8f94c09f656f5`.
  It integer-loads `_SceneColorTexture` alpha at the current pixel and forces
  overlay alpha to zero when that copied opaque-scene alpha equals exactly one.
  `ForwardPassUtils` binds `sceneColorToSample` to that global before the mixed
  transparent draw. The lab now makes the same opaque-scene copy whenever an
  active no-keyword OverlayShadow material needs it, not only for VFX
  refraction. All 84 generated overlay materials bind the recovered shader,
  with the source refs split 57 at stencil ref 4 and 27 at ref 20. The current
  LOD0 eye-shadow renderers use one submesh with two ordered material slots;
  the custom draw repeats that sole/final submesh and the mutually exclusive
  ref-20/ref-4 stencil tests select iris versus eye-white coverage. Wulfa and
  Li Zhiyan order eye-white before their common eye material, Last Rite orders
  eye-white before common-05, while Zhuang Fangyi intentionally reverses that
  order. Preserve those source slots rather than collapsing them as duplicate
  material references. Zhuang's facial avatar also moves 16 eye-shadow bones
  over `1e-4` from the raw rig (maximum quaternion-component delta about
  `0.014719`), so its native neutral pose and the overlay import are both
  required. The current
  installed raw Shader asset
  is 39,140 bytes with SHA-256
  `2e339e4ab7d96385efea5007e42c8a8137a88eb898d5ebf91876dfd72919c112`.
  Its selected vertex program subtracts the camera origin, subtracts
  `lightDirection.x * _ShadowAngleRange` in camera-relative view space, and
  adds `_TaaJitterStrength.zw * clip.w * (2,-2)`. The fragment multiplies the
  gray mask by local-volume visibility and atmosphere visibility. Output alpha
  contains one `_BaseColor.a` factor, while the multiplicative RGB weight
  contains a second factor. The lab previously removed that second factor after
  misreading the converted register aliases; both current D3D11 keyword variants
  and `UnityPerMaterial` offset `0x10` prove the squared RGB-alpha term. This is
  visually relevant in the current playable set to Ikut's
  `M_clothshadow_common_01`, whose authored alpha is `0.61960787`; the other 83
  generated overlays, including the exact eye/eye-white materials, use alpha
  one.
  Native `UpdateShaderVariablesGraphFeaturesGlobalParam0` writes the selected
  gate's z/w lanes to `1.0`, so the atmosphere branch is bypassed in this render
  path. The lab now publishes the camera-relative carrier, zero clip jitter for
  its non-jittered camera, and exact isolated-CharInfo type-4 clustered
  occlusion with a neutral missing-producer fallback;
- Last Rite's original postmodel has exactly 14 LOD0 renderers: 12 ordinary
  character surfaces and two runtime-effect auxiliaries. The large
  `S_actor_lastrite_skill_01_lod0` shell is the textureless
  `M_fx_lastrite_ztc_060` / `VFXTransparentDepthOnly` depth-only renderer;
  `S_actor_lastrite_vfxpart_01_lod0` uses
  `M_fx_lastrite_toppotential_01` / `CharacterNPR_VFX` and four effect textures.
  Raw retail serialization proves both auxiliary GameObjects are active
  layer-24 children but both SkinnedMeshRenderers serialize `m_Enabled=false`;
  an ordinary body renderer is the enabled control. No direct target name or
  PathID owner exists among the 31 reachable prefab MonoBehaviours, 122 Last
  Rite animation clips, 903 owning-chunk PlayableDirectors, installed Lua/IFix
  strings, GameAssembly strings, or global-metadata strings. The general
  indirect native route is now recovered: `RendererVisibilityEvent` packs
  `(groupIndex<<2)|(visible?2:0)|(persistent?1:0)`, its handler at
  `0x18386E7B0` calls `ComplexAnimatorComponent.SetRendererGroupVisibility` at
  `0x18386E9C0`, and `AnimationConfigExtraData` resolves renderer-name-prefix
  groups for model application plus persistent restoration. Current Last Rite
  data does not join that route: its animation config has no exact or partial
  auxiliary prefix/group, none of its 122 clips emits `RendererVisibility`,
  and the five exported control clips using the event all belong to Deepfin.
  An owner outside the current installed prefix/clip/component/Director/
  Lua/IFix evidence or a future patch remains possible, but no activation
  timing should be invented. The lab therefore excludes both exact
  actor+mesh+material+shader identities from ordinary beauty rendering instead
  of allowing disabled effect shells to become white fallback geometry. The
  remaining 12 source renderers and all 14 of their materials are
  preserved; the original UI-deco inventory is proven zero and this postmodel
  contains no static decoration/weapon renderer. Targeted Unity refresh also
  removes the two exact stale generated mesh/material assets only after saving
  the replacement prefab. `verify_lastrite_white_geometry_recovery.py` pins the
  installed CHKs, source renderer/material records, final prefab census and
  recovered-shader bindings. The wider activation-owner verifier is
  `scratch/reverse_engineering/lastrite_activation_owner/verify.py` (SHA-256
  `5A7E524E0F720E3724F61BB85B780B768A2637E774A037CB5F0A539B89A97441`);
  its JSON report is SHA-256
  `0628C0CC8273139F21FEEF202DE0338526EB0E0223778C32A786FCE8B4D19E66`.
  The compact indirect-route verifier, JSON, and Markdown report under
  `scratch/reverse_engineering/lastrite_activation_timing/` have SHA-256
  `49307038B315401F861CB4B8605B0F3B4659BEBD93A5C97F011DFC9ADA286FB4`,
  `03F1F26905FAF45B5C5802D33642142DA46814D16B798748360664E0F43F8581`,
  and `08E6E11CF2A2B08D9269A19C950553CBB70F0A6D92668C70753E6BEBF0D7F9EA`.
  Its `2021.3.34f5` signature is explicitly the proprietary retail fork, not an
  installable public editor; the lab remains pinned to `2022.3.62f3`;
- a current installed-data variant audit closes three Last Rite material
  selections without screenshot tuning. `M_actor_lastrite_cloth_02` selects
  `_CLEARCOAT`, cloth 05 selects `_PARALLAX_MAP`, and cloth 03 uniquely selects
  `_SILK_STOCKINGS`. The exact cloth-03 D3D11 ForwardLit fragment is 72,012
  bytes with SHA-256
  `d96da10d7a8547ba696c5b5dda4fb073083ca213a38b85fd9a1638dcbfe05355`;
  its non-stockings control is 65,176 bytes with SHA-256
  `f0e6c7ffcface97cd744ca17153e4247211a67389904b1d0052e58596bf166b3`.
  Metadata proves the pair differs by `_SILK_STOCKINGS` only. Both declare the
  same 336-byte material buffer, while the selected member's live b6 span grows
  from 160 to 336 bytes and adds one texture binding and one interpolator.
  Cloth 03 authors `Advance=0` with a null stockings-mask PPtr, so its advanced
  texture path is unreachable. The exact live branch now preserves BaseMap
  alpha as coverage, consumes the raw packed CP10 rain/height/global-wet
  scalar, blends `DryColor` to `WetColor`, and applies
  `lerp(base*tint, EdgeColor, lerp(min,max,min((1.05-NdotV)^(2*coverage),1)))`.
  Its second direct lobe orthogonalizes the tangent, uses anisotropic axes
  `roughness*(1 +/- anisotropy*(1-saturate(coverage*falloff)))`, evaluates at
  `normalize(shippedHalf + view*SpecularValue)`, and adds its clamped
  anisotropic distribution under the same recovered CharacterNPR light/spec-
  ramp energy as the ordinary GGX lobe. Exact authored
  `SpecularMinAtMinWetness=1`, `SpecularFalloff=0`, `SpecularInt=0.1756` and
  `RainWetMaskScale=0` make cloth-03's stockings specular identical in dry and
  wet state; only the tint changes within this branch. The serialized-visible
  LOD0 renderer binds only this material; all 122 Last Rite clips and current
  GameAssembly/global metadata contain no named stockings/material override.
  The lab implementation remains gated by the exact shader/material identity,
  eleven floats, and six texture PPtrs. General advanced-mask stockings and the
  wider CharacterNPR weather-normal/albedo system remain separate open paths.
  The compact verifier/JSON/Markdown under
  `scratch/reverse_engineering/lastrite_silk_stockings/` have SHA-256
  `703E3DA831FD3C74FD4AE1E2E83F81587C63DED2C2C85A4066913E764700467D`,
  `4CB75D5E53EF4DD77BC61CC1BB21753D42A5EB31C991710DFD38A0B2E4923A32`,
  and `28DF8D9D0238BFA7DC0F833847A99F5BAD556CE20E59F30B2276640EDD6021F9`.
  A focused Unity `2022.3.62f3` D3D12 run force-imported the recovered shader,
  found zero shader diagnostics and the exact-keyword `FORWARD` pass, and
  exited successfully; its log SHA-256 is
  `6667946E2DDAFEA5A8C90DDE3C8DE3E0D3B3AA9F757E9160D93FDAE17B469005`.
  The separate all-roster rebuild was stopped after its 20-minute wrapper
  timeout while regenerating Ikut assets, with no shader/C# error in its log,
  and is not claimed as completed;
- the general CharacterNPR `_CLEARCOAT` carrier is now recovered from the exact
  installed shader rather than the former lab approximation. The source asset
  is `HGRP/CharacterNPR`, PathID `-7822190029627442914`, at offset
  `185104054` in
  `0CE8FA57/19F0903A12BA87C0D43E67E64889B525.chk` (211,831,350 bytes,
  SHA-256 `cbc87c7d8f41d90da25af7758cf77ced7321d19c52c067f6f77a75aa5dabc380`).
  A fresh AnimeStudio sidecar export selected the otherwise identical D3D11
  ForwardLit fragment pair blob364/33 (64,996 bytes, SHA-256
  `9f607bbca3e27d20f8c1bd930adb607f2325d983b8167b107818b21af2f61979`)
  and blob392/33 with only `_CLEARCOAT` added (68,572 bytes, SHA-256
  `33fcf3078381560f50cc3766fa8bcda34742ad968d659fbb600c87c6b4ead13a`).
  Ruri.ShaderDecompiler commit
  `de596a8d4f03c1ad2114e18a3bd6b99b5b4de066` decompiled both exact members.
  The active source-energy path now samples raw mask R with the global mip
  bias, gates at `mask > 0.001`, squares `1-smoothness` before the `1/128`
  floor, retains the source's non-renormalized geometry/normal-mode lerp,
  applies `_ClearCoatColor * lerp(0.04,1,metallic)`, the Schlick pow-5 second
  GGX lobe, squared base-spec attenuation, the source's double-mask diffuse
  attenuation, and the separate cubemap/DFG energy-compensation lobe. The
  current 30-character census proves exactly eight selected materials:
  Ardelia cloth 05, Camille cloth 02, Chen weapon misc 0002, Last Rite cloth
  02, Li Zhiyan cloth 03, Mifu cloth 03, Tangtang cloth 03, and Yvonne cloth
  03. Their authored colors, metallic/smoothness/normal-mode values, and five
  non-null mask PPtrs are retained; the other three deliberately use the
  shader's white texture default. None of these eight serializes a scalar
  `_ClearCoatMask`, so the legacy `_ClearCoatMaskValue` alias does not enter
  this exact endpoint. `verify_character_clearcoat_recovery.py` hash-gates the
  installed CHK, 759-MiB source map, exported shader, both DXBC members and
  sidecars, both Ruri outputs, all eight material JSON files, and the two
  recovered HLSL blocks. The ShaderDecompiler metadata still exposes the
  serialized carrier as vertex while decoding the DXBC program as fragment;
  unresolved remapped constant-buffer names and the wider HGRP frame/resource
  schedule remain explicit boundaries. The selected camera's retail
  `_GlobalMipBias` producer/value is closed below. `RuriRipperImporter` commit
  `d006a54b6a9b2ea5773c5d5f8d188431c2b51ff0` corroborates packed material
  channel/color-space handling but is a Blender YAML/model/material importer,
  not a compiled CharacterNPR decoder, so it was not treated as shader truth;
- current type trees also prove that Fluorite/Bounda and Last Rite hair-shell
  materials use queue 2985, `_ZTest=2` (Less), and `_ZWrite=1`. Targeted Unity
  refreshes now retain that source state instead of the generic queue-3000 /
  LEqual transparent fallback. Fluorite's four cloth materials select no
  unique unsupported nonzero cloth toggle, so its remaining mismatch belongs
  to shared CharacterNPR math, texture format/mips, weather/customization, and
  final presentation rather than a missing actor-only keyword;
- the priority-character opaque-hair queue is now source-closed as well.
  Original material JSON and raw Last Rite Material dumps prove that Li
  Zhiyan's opaque `CharacterNPR_Hair` is queue 2000, while Last Rite, Zhuang
  Fangyi, and Wulfa use queue 2015; their transparent `_hairt_` shells remain
  2985. The compatibility importer previously left four opaque materials at
  shader-default queue 2450 or `-1`, which could reorder hair against the
  face/body/overlay passes. `ConfigureMaterialSurface` now applies the exact
  serialized `_characterRenderQueue + _QueueOffset` only to opaque recovered
  hair. The fail-closed verifier covers ten active source/generated material
  rows and reports no regeneration gap after a GUID-preserving 450-material
  refresh. Its report SHA-256 is
  `CB1A0B130CAAE5446DF544B26B5CF49A5BDD22A33EE84DE3FC1E3A9E7CB680C2`;
  the pinned Unity refresh log SHA-256 is
  `7EF590E2B01FB5C5B25CCCF33EF2FD69178F91D1F4113353CF5DE738F7D30858`;
- CharacterNPR serializes `_ClearCoatMask` in both its texture and float
  property sheets. The importer now keeps the TexEnv at `_ClearCoatMask`, maps
  the scalar to the recovered `_ClearCoatMaskValue`, and type-checks numeric
  writes before calling `SetFloat`. This removes a real material-type collision
  while preserving both original values;
- cloth 03's source queue 2000 is represented by the recovered shader's
  Geometry default (`m_CustomRenderQueue=-1`). Its source `_ZTest=3` (Equal)
  is preserved separately as `_RecoveredSourceZTest`; the normal compatibility
  path remains `LEqual`. The material disables generic `DepthOnly` but leaves
  the original `PreGBuffer` / `DepthCharacterOnly` pass enabled. A default-off,
  source-gated canonical owner now submits the recovered PreG pass against the
  same camera depth/stencil attachment as the immediately following opaque
  Forward draw, then restores source `Equal` only after successful execution.
  Every validation failure retains `LEqual`;
- Zhuang Fangyi's full gacha prefab proves that widget 03 has two distinct
  copies of the same mesh. The Actor copy keeps `DefaultHGMaterial` and its
  `chr_0030_zhuangfy_deco_3` ancestor is serialized inactive in the full gacha
  instance even though the standalone widget prefab root is active. The visible
  entrance copy lives under
  `Effect/P_fxui_zhuangfy_ui_overview_start_01_piaodai`, uses three authored
  `M_fx_ui_zhangfy_piaodai_*` materials, and is driven by a separate Timeline;
  no runtime material replacement of the Actor copy was found;
- the maintained playable-manifest path now imports that separate 44-transform
  Effect clone below `RecoveredProps/P_fxui_zhuangfy_ui_overview_start_01_piaodai`.
  Its sole source submesh is submitted through the three ordered material slots
  at queue 3700; shader admission requires the exact VFXBaseV2 PathID plus one
  of the three exact material PathIDs. The 39-transform motion is sampled from
  the original streamed/dense/constant clip at 60 Hz after the authored
  `0.4833333333` clip-in, holds through Timeline time `4.5166666667`, and applies
  the original renderer `material._TintColorAlpha` curve. All former recovered-
  state and clip-visibility joins to the Actor placeholder are removed, so its
  `DefaultHGMaterial` renderer stays fail-closed even when the private diagnostic
  widget clips remain available;
- unknown material records now fail closed through the no-color unavailable
  shader, preventing new missing records from silently becoming white models.

A fresh original-data/current-prefab audit separately pins Zhuang Fangyi's
item 01 mesh `-1924764285534880239` to material
`M_item_widget_zhuangfy_01` PathID `-3984077910243774596`, and item 09 mesh
`6348567289315379369` to `M_item_widget_zhuangfy_09` PathID
`-4308416870317143792`; both use original HGRP/CharacterNPR PathID
`-7822190029627442914`. Their implemented textures and audited feature floats
match source. Both retain source `_ZTest=3` only as `_RecoveredSourceZTest`
while the compatibility path uses LEqual until a canonical same-owner PreG
depth writer is proven; restoring Equal unconditionally would make them
disappear. The same audit reconfirms the two Last Rite auxiliary exclusions,
the inactive Zhuang deco-3 Actor placeholder, 28 clean LOD0 eye-shadow
renderers, and all original shared eye-mask color-space bindings. Its readable
report is `unity_endfield_graph_shader_lab/scratch/character_recovery/
last_rite_zhuang_material_audit/audit_report.md` (SHA-256
`74C721E278046BEC02BE8F10F77B81E7D65519D881C78A5AE8E5EF98E3309145`);
the JSON is SHA-256
`D2DBEC6C9A9D9E4EB1DE24332D94675107B31A504CBB86ADBDA1194659675632`.

The two remaining OverlayShadow runtime inputs are now bounded directly by the
current installed client rather than named heuristically. The selected D3D11
fragment member is 12,852 bytes with SHA-256
`6997620071f0b1082abc4193cb173f410ff64cb8856ab81f2a8d1a9abb7d21d2`;
its exact sidecar places `_TaaJitterStrength` at byte offset `0x130` of
`ShaderVariablesGlobal`. In the hash-pinned `GameAssembly.dll`
(`0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`),
`HGCamera.GetJitteredProjectionMatrix` at VA `0x18326B8B0` computes
base-2/base-3 radical inverses of `(taaFrameIndex & 1023) + 1`, subtracts
`0.5`, divides by actual width/height and rendering scale, and stores
`(rawX, rawY, normalizedX, normalizedY)` at `HGCamera+0x68`.
`HGCamera.UpdateShaderVariablesGlobalCB` at VA `0x1832E0020` then performs the
exact `HGCamera+0x68 -> ShaderVariablesGlobal+0x130` SIMD copy. The overlay
vertex consumes the normalized `.zw` pair. TAA graph construction calls
Dilation, MaskDilation, then Resolve, but its global-history preparation is an
IFix wrapper, so forced phases and complete history constants remain open.

The fragment-side visibility term is now source-closed for the isolated
CharInfo overview rigs rather than described as a generic Unity Volume value.
The exact sidecar binds `_GlobalBinningBuffer`, `_BinningBufferOffsets`,
`_LightBinningConstants`, and the 2,048-entry `_PunctualLightData` array. The
selected fragment traverses its 32-by-32 screen tile/Z-bin masks. Punctual
record lane 3.z is `LightCharacterOnly`, lane 3.w is `HGLightNPRType`, and
`_CharacterParams12.z` is the inverse of
`charIgnoreSceneAdditionalLights`: disabling scene additional lights still
admits character-only rows. Type 16 is excluded. Only type-4 Fog rows add
`saturate(attenuation * nprData.x + previous)`; their range exponent is
`max(2*nprData.y, 0.1)`, their authored directional-falloff flag projects the
distance onto the spot axis, and spot attenuation is squared before the exact
`1e-4` contribution gate.

The exact operator-light export contains 266 lights across all 30 CharInfo
profiles, at most 13 per actor. All profiles contain a type-4 Fog owner: 40
rows total, 35 advanced-carrier and five convenience-packed, including ten
directional-falloff rows. All 40 are enabled, character-only, cookie-free,
OBB-free, non-flickering, non-shadow-only, and do not use culling distance.
`HGAdditionalLightData` owns and uploads their NPR/type/character-only carrier;
`VFXPPCharacterLight -> HGCharacterVolume.SetCharLightVolumeData` owns profile
application; `HGRenderPipeline` publishes the inverse scene-additional-light
gate. The lab now applies the exact recovered 32-pixel XY/2,048 one-unit Z
membership and this bounded type-4 consumer to the 28 audited LOD0 eye-shadow
renderers/all 84 generated overlay materials. Missing rig, compute support,
perspective camera, or membership state returns exact neutral zero occlusion.
The verifier-backed report is
`scratch/reverse_engineering/eye_shadow_cluster_visibility/report.json`; run
`python scratch/reverse_engineering/eye_shadow_cluster_visibility/verify.py`.
The verifier and report SHA-256 values are respectively
`31FDB48EB10A78F07E5DB7AA754BCDA4E6464496C6866E041F72D2AA77DDE6CF`
and `018D321263E41F4489FE1C71B34EB379432570BAB5607E5E970E6DF65AEEB939`.
Unity `2022.3.62f3 (96770f904ca7)` batch import passes. An independent
post-integration batch load also exits zero with no bounded C#, shader,
null-reference, unhandled-exception, or crash diagnostics; its log SHA-256 is
`0D222E26AB9ED45D56BEE72F26B6EE4B4D716B2155672C92F2F6C9E0DBC448B2`.
The current retail `UnityPlayer.dll` now substantially closes the previously
opaque `HGCullingSystem.CullLights` stage. Its 3,962-entry internal-call
registry maps `CullLightsInternal_Injected` to `0x1800FBCE0`, then to result
owner `0x181050FC0` and candidate core `0x181051A40`; manager byte `+0x9D8`
selects the separately bounded fallback core. Each `HGCamera` supplies its own
cull-view handle, camera instance ID, scene/layer masks, squared projected-size
threshold, optional 320x160 occlusion dimensions, and FOV/aspect/near/far
tuple. The native candidate path source-closes the PC device-tier interval,
maximum culling-distance and minimum far-show-distance gates, inclusive Point
sphere/frustum test, Spot helper, authored OBB builder plus separating-plane
test, optional occlusion result gate, and the directional light/camera-owner
identity check. Directionals are appended directly; accepted non-directionals
become 12-byte `(native pointer, camera distanceSquared)` rows sorted ascending
by distance before the 256-result cap. Managed `SetupState` then considers only
that prefix, retains Point/Spot, and applies priority-descending then
distance-ascending order before `punctualLightMaxCount`. Cookie atlas/index and
runtime flicker-color multiplication occur after this shortlist and do not
affect native membership or native order.

The post-shortlist cookie path is now closed against the same current retail
binary. Each `HGCamera` owns one persistent `HGLightCookieManager`; every
`ConstructPass` calls `SetupState`, then `UpdateLightCookieAtlas`, then
`LightCulling.PrepareCPUData`. The manager fields are active cookie rects at
`+0x10`, in-use/remove/add scratch lists at `+0x18/+0x20/+0x28`, the
entity-to-slot dictionary at `+0x30`, atlas allocator at `+0x38`, cached atlas
at `+0x40`, and graphics format at `+0x48`. Its constructor creates a
4,096-by-4,096 allocator and stores format `0x66`, which the exact public
`2022.3.62f3` Unity enum names `R_BC4_UNorm`. Cookies are disabled for the
mobile render-path shader define. The preparation pass considers only the
already selected Point/Spot prefix, retains at most 32 valid cookie textures,
allocates a 2D cookie as width-by-height and a cubemap as six horizontal faces,
and fails invalid or unallocated entries closed. The update pass assigns at
most 32 sequential entity slots in selected-light order, writes atlas rects
with exact scale `1/4096`, uses rotation-only local-to-world for Point cookie
matrices, and uses `ExtractSpotLightMatrix -> GetShadowTransform` for Spot.
`GetLightCookieIndex` returns `-1` for every missing, disabled, unselected, or
unpacked cookie.

The exact clustered payload remains six header `float4` values followed by
eight `float4` values per punctual light. Per-light rows are: final color times
falloff times flicker plus type/shadow mode; position/inverse range; octahedral
forward plus Spot/Point shape data; shadow indices plus volumetric,
character-only and NPR type; NPR data; two packed OBB rows plus falloff
exponent; and finally culling threshold, soft radius, specular intensity and
cookie index. The selected Zhuang Fangyi Hair CharacterNPR fragment consumes
this as `b12`, consumes 32 rects plus 32 matrices as cookie CB `b38`, and samples
the atlas red channel at `t21/s5`. A negative row-7 cookie index preserves
attenuation. Spot cookies use projective UVs; Point cookies rotate the negative
light vector, select one of six horizontal cubemap faces, and inset the face
edge by `(1/4096)/rectHeight`.

Flicker is closed through its consumer and getter, but not yet through its
producer. Light setup copies the resolved flicker-style pointer, speed, time
delay, random-delay flag and enabled flag into the runtime light component at
`+0x28/+0x30/+0x34/+0x38/+0x39`. The current
`HGSharedLightData.get_flickerScale_Injected` resolves that ECS component and
returns its evaluated float at `+0xF0` only when the component exists and
`+0x39` is enabled; all missing, invalid or disabled paths return exact `1.0`.
`PrepareCPUData` multiplies recovered final light color by this value after
culling and ordering. The scheduled updater/curve sampler that writes `+0xF0`
has not been source-closed, so wider flickering lights must retain the unity
fallback instead of receiving a guessed curve evaluator.

A managed-side binary pass now proves this producer gap is structural, not an
unfinished search. Enumerating every `Flicker`-named IL2CPP type/method across
`global-metadata.dat`/`GameAssembly.dll` (CodeRegistration `0x18b9217d0`) yields
only four entries: the getter `UnityEngine.HGSharedLightData.get_flickerScale`
(`0x18b3bdf24`), its injected binding `get_flickerScale_Injected`
(`0x18b3bdef0`), and Unity's `LightFlickerStyle` `.ctor`/`Internal_Create`
authoring pair. There is no managed writer. Disassembly confirms the getter is a
two-instruction tail call into `get_flickerScale_Injected`, which lazily
resolves a native icall pointer and `jmp rax` into it; the passed icall name
string is exactly
`UnityEngine.HGSharedLightData::get_flickerScale_Injected(UnityEngine.HGSharedLightData&)`.
So both the `+0xF0` read and its per-frame writer live inside the custom HGRP
`UnityPlayer.dll`, outside IL2CPP metadata entirely. The GameAssembly/metadata
method that closed the protocol handlers is therefore structurally incapable of
recovering the flicker curve evaluator; source-closing `+0xF0` requires the
`UnityPlayer.dll` internal-call-table lift (the same toolchain that closed
`HGCullingSystem.CullLights` in
`scratch/reverse_engineering/clustered_light_native_culling/`), starting from
the resolved icall target of `get_flickerScale_Injected`. Reproduce the managed
census with
`scratch/reverse_engineering/clustered_light_cookie_flicker/find_flicker_methods.py`.

This closure requires no lab render change for Zhuang Fangyi. All six original
`light_overview` rows from `CAB-096bde421b3c1589c9066fd06523fbfb` are enabled,
character-only, priority zero, cookie-free, flicker-disabled, and OBB-disabled;
the existing cookie index `-1` and flicker scale `1.0` are therefore exact.
The 16 selected fragments covering her 58 `VFXBaseV2` materials plus the one
RadialBlur and one Refract material bind none of the clustered LightData,
cookie-CB, or cookie-atlas resources, so clustered character lighting must not
be added to those effects. The verifier-backed report is
`scratch/reverse_engineering/clustered_light_cookie_flicker/report.json`; run
`python scratch/reverse_engineering/clustered_light_cookie_flicker/verify.py`.
The verifier and report SHA-256 values are respectively
`AD1F2DA0F8016F71FF5951920917A6C5AF092518899B696900F5FB43FE59A8C5`
and `CB29D73FF637C8A6DF74CDA6A0587356ADC57E327D7301A3767C2BB71EEC1B8A`.

This does not promote arbitrary gameplay parity. The scheduled generic
cull-view producer's exact projected-size equation and scene/layer evaluation
order, the 320x160 occlusion helper's geometric/temporal math and cache
history, the fallback core, equal-distance/equal-priority ties, evaluated live
transforms, and unrelated scene-light population remain open. The current 40
isolated CharInfo Fog rows use none of OBB, cookie, flicker, shadow-only or
culling-distance state, so their existing implementation remains inside its
source boundary; wider states must still fail closed when required owner/input
data is absent. The verifier-backed current-binary report is
`scratch/reverse_engineering/clustered_light_native_culling/report.json`; run
`python scratch/reverse_engineering/clustered_light_native_culling/verify.py`.
The verifier and report SHA-256 values are respectively
`9019897C1DC8E04CBB613ECE6285C3FDE597FB2336745B701DD6D44D71944DB5`
and `F7B6E9B6407BB26555491C13F9895B712A9219218C19AC07EFD56D7C947D7D7E`.
The installed public validation editor is exactly `2022.3.62f3`
(`96770f904ca7`) with Windows standalone support. A fresh batch project load
exits zero with no bounded C#/shader/null-reference/unhandled/crash diagnostic;
its project-local log is
`unity_endfield_graph_shader_lab/scratch/character_recovery/native_culling_current_retail/unity_2022_3_62f3_batch.log`
(SHA-256
`6F889D8B5F1AE4833EAFC8B066E4C5416A8A02093D10684475564A5620CEC628`).
The lab also still does not run retail TAA history, so zero jitter remains the
exact compatibility endpoint.

The face/eye/overlay attachment and cross-queue chronology are now
source-closed. The current installed `GameAssembly.dll` calls
`ForwardPassUtils.RenderForwardTransparent` (method index 287276, VA
`0x189BACFCC`) and makes one call at `+0x9C7` to
`HGRendererListUtils.DrawECSMeshRendererListWithSRPRendererList` (method index
288211, VA `0x189C0964C`). The transparent graph binds `input.sceneDepth` with
`DepthAccess.Read`; the array renderer-list descriptor uses sorting value 87,
`CommonTransparent|RendererPriority`. Its retail pass-name order is
`TransparentBackface`, `ForwardOnly`, `Forward`, `ForwardCharacterOnly`, then
optional `CharacterOutline`, and `SRPDefaultUnlit`.

OverlayShadow is queue `Transparent-100` / 2900. Its depth member is
`ForwardOnly`; its multiplicative color member is `ForwardCharacterOnly` and
reads refs 4/20 through read-mask 20 without writing stencil. Every currently
recovered shared eye/eye-white/hair-shadow type tree disables `ForwardOnly`
and serializes `_EnablePreDepthPass=0`, so none contributes the overlay depth
member. Wulfa eyebrow/iris and Zhuang Fangyi brow/iris materials serialize
`_PreZStencilRefOption=52`, while the face side uses 36; therefore
`52 & 20 == 20` selects eye/brow/iris and `36 & 20 == 4` selects the
face/hair side. The same transparent list then orders overlay 2900 before hair
shell 2985 and body/cloth layer 3000 on the shared scene depth/stencil.

The lab now follows that proven route: it no longer explicitly draws
`PREDEPTH` or a late `OVERLAY_SHADOW`; the queue-2900 color member has
`LightMode=ForwardCharacterOnly` and participates in the regular transparent
list with `CommonTransparent|RendererPriority`. The retained `PREDEPTH` pass
is `LightMode=Always` and unsubmitted, a bounded compatibility surface for a
future original material that proves it live. The hash-pinned verifier is
`unity_endfield_graph_shader_lab/tools/verify_face_eye_overlay_chronology.py`.
It pins the current global metadata, GameAssembly, UnityPlayer command
registration, four CharacterNPR raw and converted Shader assets, four native
method slices, decompiled HGRP sources,
material type trees, and the queue inventory. Exact equal-queue ordering
inside the custom UnityPlayer mixed-list command has been narrowed further:
the icall registry/wrapper and append slices prove opcode `0x4F`, while HGRP's
sorting value is exactly 87. The four priority eye renderers each have one
submesh and two authored source slots; lab arrays preserve them byte-for-byte,
including Zhuang Fangyi's authored eye-shadow-first reversal. The opcode
handler is now exact: interpreter `0x1804CE3F0` dispatches table entry `0x4F`
to `0x1804CE461`, decodes the SRP handle plus aligned 16-byte ECS payload, and
reaches the scheduled mixed merge at `0x18053F0B0`. Equal packed cross-list
keys choose ECS before SRP while preserving each already-sorted input range.
The 80-byte renderer-list entry sort at `0x180539910` reaches comparator
`0x180538A90`; value 87 activates deep `OptimizeStateChanges` comparison,
including per-entry `+0x08` state, then unsigned `+0x0C` and `+0x4C` fallbacks.
This proves deterministic state sorting rather than stable source-slot-only
sorting. The actor-specific runtime values were previously uncaptured. The
runtime-key trace now closes two of the three fields: `+0x0C` is the
renderer-data record index and is equal for
the two material slots, while `+0x4C` is the selected-pass ordinal reset per
material and is zero for both one-pass OverlayShadow materials. Only `+0x08`
can permute the pair. Its normal producer hashes the runtime material `+0x20`
buffer with seed `0x8F37154B`, then combines shader runtime dword `+0x08`,
runtime-material byte `+0x114`, and common or indexed property state; the
special descriptor branch uses shader `+0x08`, cached buffer hash `+0x10C`,
and byte `+0x114`. Material slots are enumerated in authored ascending order.
If unsigned `+0x08` ties, the authored order remains; otherwise one live value
capture at `UnityPlayer.dll+0x541500` is still required for final actor-specific
proof. Direct GameAssembly references to the indexed-property-block setter are
only the XLua Renderer wrapper, HGVFX circle-occlusion update, and the public
Renderer tail wrapper; no character-specific direct C# caller or serialized
PropertyBlock payload was found. Indirect/XLua use remains possible because
structured export contains no Lua. Therefore the lab preserves authored arrays
and applies no synthetic reversal or renderer-priority heuristic. The
reproducible audits are
`scratch/reverse_engineering/overlay_same_queue_order/verify_overlay_same_queue_order.py`
and
`scratch/reverse_engineering/overlay_same_queue_order/handler_comparator/verify_handler_comparator.py`,
with the eight-second runtime-key proof under that directory's `runtime_keys/`.
The decoded
installed Persistent IFix table has no face/eye/overlay target; a later patch
refresh remains a version boundary. This does not affect the proven
2900-before-2985-before-3000 order.

The current installed playable Eye/brow ForwardLit selection is now
source-closed at the material/fragment boundary. The 30 canonical manifests
contain 57 unique `HGRP/CharacterNPR_Eye` materials across 28 actors; Antal and
Da Pan are source-proven zero. Targeted serialized dumps recover the keyword,
queue, and disabled-pass data omitted by the normal Material JSON. They select
29 iris (`_DIFF_RAMP_ON _EYE_HIGHLIGHT _MATCAP_ON`), 20 LUT-brow
(`_DIFF_RAMP_ON _SHADOW_LUT_TEX`), and eight plain-brow (`_DIFF_RAMP_ON`)
D3D11 fragments. The exact raster census is queue 2000 x45, 2015 x11, and 2050
x1, with original DepthOnly enabled x10 and disabled x47; all are opaque. The
selected fragments fix `Target0.a=1`, write the packed scene-motion MRT, and
unconditionally consume the screen-space scene-shadow R channel. The recovered
Eye shader and material importer now fail closed to the pinned 57-material
contract and restore the exact queue and mapped `CAMERA_DEPTH_COPY` state. The
strict check is `python tools/verify_eye_brow_forward_recovery.py --require-generated`
from the lab root; it reports zero pending generated materials under the
project-pinned Unity `2022.3.62f3`. The remaining Eye-specific pipeline gaps are
the retail scene-shadow R producer/attachment and independent admission of the
opaque Eye writer. The lab now owns the source-closed
`A2B10G10R10_UNormPack32` scene-motion attachment for selected VFX, but an
Eye-only frame does not request it; those Eye consumers therefore remain
default-off until their own owners are wired.

The refreshed bounded all-roster feature/material plan passes all 30 actors.
Last Rite and Fluorite report complete source inputs, zero selected fallbacks,
and no missing generated texture slots. Their focused material contract is
checked by
`unity_endfield_graph_shader_lab/tools/verify_character_variant_failures.py`;
the final Unity 2022.3.62f3 targeted refreshes compile cleanly and reproduce
the exact hair-shell queue/Z state and selected cloth keyword states. Zhuang
Fangyi's eye overlays are source-complete; her deliberately hidden widget-03
`DefaultHGMaterial` is now source-proven to be the inactive Actor placeholder,
not the finished ribbon material. The separate gacha Effect clone, its three
authored materials, and its activation/animation timing are recovered and now
feed the maintained manifest/import path. A bounded selected-sample-stack
VFXBaseV2 translation is identity-gated to those three materials. Selected
DXBC plus the serialized material constants now close the private dissolve
algebra: the route uses texture red, its schedule remap collapses to `-1.01`,
alpha is `saturate((red + 1.01) * 0.5)`, and the emissive edge is zero for
normalized red. The position-only dither hash and target1 RGBA equations are
also exact. The earlier `_VFXParams0.xy` label for the selected dither operand
was wrong: the selected fragment does not read global buffer `b1/c103` at all;
its dither threshold and alpha tail read per-draw `b2/c4`, mapped by the managed
layout to `PerDrawBaseData.lodFade.xy` / `unity_LODFade.xy`. Global
`_VFXParams0.xyz` is independently source-closed as
`HGVFXManager.m_playerPosition`: `UpdateCurrentPlayerCenter` samples the center
Transform position (or writes `Vector3.zero` for null), and
`UpdateShaderVariablesGlobalVFX` packs it at `ShaderVariablesGlobal+0x670` on
each global-buffer update. Managed zero initialization plus the constructor
gives the same zero default before the bridge first runs. The source-gated
proof is
`scratch/reverse_engineering/vfxparams0_producer/verify_vfxparams0_producer.py`;
its current report SHA-256 is
`5A8298D1F851CC2780FA7FE040905E5D8364E6EF13FEF17DD0F1C07EA330CDB6`.
The previously separate `_VFXParams0.w` channel is now source-closed too.
`HGRPTimeManager.Update` assigns `m_time=UnityEngine.Time.time`;
`HGCamera.UpdateShaderVariablesGlobalCB` writes
`_Time=(time/20,time,2*time,gameplayTime)` at constant-buffer `+0x140`; and
`HGRenderPathBase.UpdateShaderVariablesGlobalVFX` reads `_Time.y` at `+0x144`,
calls the retail float-remainder helper with exact divisor bits `0x44800000`
(`1024.0f`), and packs the result at `_VFXParams0+0xC`. The exact live formula
is therefore `fmodf(UnityEngine.Time.time,1024.0f)`. The selected
`VFXRefract/_USE_DISSOLVE` fragment consumes that precise `c103.w` channel,
and selected non-instanced piaodai vertex program `0063` adds the same value
times each authored speed `.xy` to every scrolling UV pair. The lab now
publishes and consumes this bounded retail time channel instead of substituting
unwrapped Unity `_Time.y`.
The hash-pinned verifier also executes the original helper for seven boundary
and wrap samples with bit-exact float32 results. Its report, verifier, and
findings Markdown SHA-256 values are respectively
`DF8594FA402B03B849CDDEC020BDF84D824F1E56F651E13F18EDB7433D43ACFD`,
`2B65180BBE5161DA86CD3FD431E87E1BEDF0685C769651E247C8AA32D0E679AC`,
and `091526C5BE4B0CC76618C8813903B5B932807B4E988C2014BF9BDDC68A08C91A`
under `scratch/reverse_engineering/vfxparams0_w_producer/`.
UnityPlayer packing is now exact. Retail `CalculateLODFade` produces a
16-bit fade and mode; `SetupLODFade` writes
`x=+/-fade/65535` and `y=+/-(fade&0xF000)/65535`, with mode 3 negating both and
only modes 2/3 enabling cross-fade. The two transition intervals clamp to
`[0.001,0.499]` and `[0.501,0.999]`. The selected ribbon renderer is
`EffectSetting.lodSetting[4]`, with one active distance tier, `lodFadeTime=1`,
cull distance 100, and no serialized Unity `LODGroup`. Original dither execution
now has a source-closed writer. `EffectSetting._SetEffectCfgAlpha` iterates the
complete `lodSetting` array and `EffectLodCfg.UpdateLodFade` reaches the same
sink; `EffectLodCfg.SetEffectAlpha` enables manual dither below effective alpha
`0.95` and writes `1-effectiveAlpha`. UnityPlayer stores that as enable bit 17
and float channel 17 (`+0x44`), the standard flatten path preserves bit 17, and
`CalculateLODFade` carries it through `RenderNode+0x178/+0x17A` to
`unity_LODFade.xy`. Camera dither is the distinct channel 18. The separate
custom-LOD wrappers have only XLua binding-shim direct callers in an exhaustive
GameAssembly executable-section call scan; indirect Lua/reflection use remains
fail-closed. The exact frame's effective alpha, packed uint16/mode/sign, and
final values still require a live capture and must not be inferred from
`lodFadeTime`. The pinned writer report is
`scratch/reverse_engineering/lodfade_live_writer/lodfade_live_writer.json`
(SHA-256 `2E8F12DE68A200103F5585845A837AD70547DF7043D7E01C717A5A5CA6F9FCC7`);
`verify_lodfade_live_writer.py` is
`C5966977148DE7E4B72515D4A8F819ED3C6167B01CB794ACDBE7CD7A3177A406`.
The original `sceneMV` runtime contract is
now source-closed from the current installed `GameAssembly.dll`, global
metadata, forked `UnityPlayer.dll`, and selected VFXBaseV2 vertex bytecode. It
is a full-`HGCamera.sceneRTSize`, point-filtered, Repeat-wrapped, single-sample
`A2B10G10R10_UNormPack32` target (enum value 75). `OnPreRendering` resets its
logical handle to null and creates a transient render-graph handle only when
`HGCamera.enableMV` is true. Deferred first use clears MRT1 to
`(0.5,0.5,0,0)`; the forward/VFX helper conditionally attaches it at the
caller-supplied index with exact `Load`/`Store` and depth slice zero. The black
color passed to that explicit overload is not a clear because the load action
is `Load`. `sceneMV` is current-frame packed motion, not a ping-pong history
texture. `HGCamera.UpdateViewConstants` snapshots current camera constants to
their `prev*` slots, and the selected vertex program consumes paired
current/previous ranges from the fork-owned `_VertexSkinMatrices` buffer.
Zhuang Fangyi's serialized `_EnableTransparentMV=0`, `_SurfaceType=1` makes
that previous-state route irrelevant to her exact Target1 result
`float4(0,0,1,activeMask)`. The lab now owns a narrowly admitted native
`A2B10G10R10_UNormPack32` MRT path for the six exact Zhuang Fangyi particle
material identities plus the three exact piaodai materials; other variants
remain fail-closed.
The reproducible report is
`scratch/reverse_engineering/scenemv_runtime/build_scenemv_runtime_report.py`;
its current report SHA-256 is
`26B2E74DF3F173D9A82DE66DED3F2B513166CFFC95DBBC9695FD710FD6B47FB0`.
The selected VFX MRT producer/order chain is now closed on top of that resource
contract. Target 1 uses indexed `SrcColor/OneMinusSrcColor` RGB and `One/One`
alpha blending. All six selected Zhuang Fangyi VFX outputs are `(0,0,1,A)`, so
the exact result is `(dst.r,dst.g,1,dst.a+A)`: prior sceneMV R/G must survive,
B becomes one, and only the lightning/redwave variants add nonzero responsive
alpha. `baodian` routes through main `ForwardOnly`; lightning, redwave, and wave
route through after-postprocess `ForwardOnly`; blur and niuqu retain
`LightMode=Distortion` in the main transparent queue. Main transparency orders
forward-decal ECS, VFX-decal SRP, VFX-decal ECS, combined transparent SRP/ECS,
HG UI, rain, then snow. Distortion orders opaque SRP/ECS, transparent SRP/ECS,
after-distortion ECS, rain drops, then fullscreen VFX. The current callback does
not draw its otherwise-present `forwardTransparentAfterUIECSList` field.
The runtime resource PathID `5613980184714137857` resolves its copy shader to
`Hidden/HGRP/Blit` PathID `8218498280856943329`; pass zero is ZTest Always,
ZWrite Off, Cull Off and samples the old scene-color handle with
`SampleLevel(..., cb0[2].x)`. Each compositor clones scene color, copies the
incoming handle, binds that old snapshot as `_SceneColorTexture`, draws into
the clone, and publishes the clone. ForwardOnly uses read-only depth;
Distortion uses read-write depth. The higher-level total order is now
source-closed for the current installed build.
`HGRenderPathDefaultDeferred.RenderScene` calls GBuffer, ForwardOpaque, main
ForwardOnly, and Distortion in
that order; `HGRenderPathScene.RenderInternal` then enters Phase1, whose gated
chain is LightShaft, Parafin, DOF, MotionBlur, after-DOF ForwardOnly, LensFlare,
and optional horizontal blur before Phase2. The decisive current-build
callsites are `0x189BF3074`, `0x189BF534E`, `0x189BF5D0F`, `0x189BF5F29`, and
`0x189C00740`. Main ForwardOnly therefore precedes Distortion; this is no
longer a lab ordering choice. Scene color, depth, and sceneMV are published
through `HGRenderPathScene+0x12E0/+0x12F0/+0x1300` between consumers.
ForwardOpaque owns target 1 with Load/Store and the 16 pinned Wulfa/Zhuang
Fangyi CharacterNPR skin/cloth/hair/eye fragments write packed R/G, B=1, and
A=0.4 or 0.4/0.7 there. The retail authored vertex input, draw flags, two
deformation routes, paired history ownership, selected previous-position
selector, renderer-space bone-array construction, `HGMeshSkinning.compute`
producer, and final graphics stream rewrite are closed. The remaining lab
blocker is a dedicated unskinned raw indexed draw that can own those recovered
current/prior/source streams without routing an already-deformed compatibility
`SkinnedMeshRenderer` through skinning again. Until that separate draw exists,
the selected opaque path leaves the one-time neutral clear in target 1 before VFX.
Exhaustive world/terrain/foliage/
vegetation target-1 admission remains outside the isolated CharInfo closure.
The reproducible verifier is `scratch/reverse_engineering/
scenemv_total_order_recovery/verify_scenemv_total_order.py` (SHA-256
`82F1118F92761C381FC9046F5DA34C27074309EAC76AF4CE2689B63A0CCF1389`);
its JSON is SHA-256
`B6BB9C70AE5EF5128AB497E466EADE1E2EA4260DA5F04C555E9F660449680070`.
The consumer semantics are now independently source-closed rather than inferred
from the `sceneMV` field name. Phase1 registers `PassInput.sceneMV` as a
MotionBlur `ReadTexture` at `0x189BBD91C`; Phase2 feeds the same handle into
TAAU dilation and resolve, whose ReadTexture callsites are `0x189BD2246` and
`0x189BD2D86`, and the shipped D3D11 programs load/decode it. The selected
CharacterNPR vertex/fragment pair likewise proves distinct current and previous
skinned positions in TEXCOORD4/5, signed fourth-root packed target-1 R/G, and
B=1. Values 0.4/0.7 quantize in A2 to the interior 1/3 and 2/3 codes, which
TAAU classifies near 0.3/0.6; the high-level semantic name of that material-
derived class remains unknown. The reproducible consumer verifier is
`scratch/reverse_engineering/scenemv_consumer_semantics/
verify_scenemv_consumers.py` (SHA-256
`811A077A1B9A9143A461CA1954564D16A082153FAF53D0466095EDE459AC1986`);
its JSON is SHA-256
`B88FD9BFD31049090767E1DF7F08E90BC9AF1770EC054816465AD76D6447E441`.
The upstream skinned-history producer is now native-pinned as well.
UnityPlayer render-manager `+0xC0060` owns an atomic float4-row ring;
`0x1810BA4E0` allocates three rows per matrix and returns generation, row
offset, and mapped CPU pointer. The skinned renderer path `0x18051C7B0`
allocates `3*(boneCount+1)` rows, rolls current row offset `+0x374` to previous
`+0x370` once per render generation, and collapses previous to newly allocated
current when `oldGeneration+1 != currentGeneration`, setting discontinuity byte
`+0x390`. Writer `0x180517C70` converts one computed renderer matrix followed
by `boneCount` source 4x4 matrices through `0x180517E00`, with 64-byte source
and 48-byte three-float4 destination strides. The prepended matrix is now
pinned as the renderer's local-to-world: `0x180517C94 -> 0x180519B30` resolves
the Transform, `0x1806493D0` copies its TransformAccess handle, and
`0x18012C160` materializes the matrix. The draw record receives the
current/previous row offsets at `+0x50/+0x54`; the selected CharacterNPR shader
reads them from `_32_m0[instance+5].xy`, adds three rows, and fetches each bone
at `offset+3+boneIndex*3`. Current object-transform rows are
`_32_m0[instance+0..3]`; previous rows are `+6..9`. What remains is narrower:
the source 4x4 array is also source-closed. `0x180516F00` and the synchronous
fallback in `0x18051E680` select the mesh's 64-byte bind-pose array at `+0xF0`
(count `+0x100`) and call shared builder `0x180503FA0`. The ordinary root is
renderer world-to-local from `0x180649AD0`; a valid special root at renderer
`+0x438` deliberately substitutes identity. The cached hierarchy path and
direct `0x180501160 -> 0x180508390` fallback implement the same public-Unity
matrix contract:
`renderer.worldToLocalMatrix * bone.localToWorldMatrix * mesh.bindposes[i]`.
Thus each result maps bind-pose mesh vertices into renderer/object space before
the separate object transform. `0x180516E20` independently clamps skin quality
to supported 1/2/4 influences; quality changes vertex weight count only, not
matrix construction or space.

The draw-input/consumer boundary is source-closed. The pinned
4,902-vertex Wulfa LOD0 Mesh stores float3 position/normal, float4 tangent, and
exactly four float weights plus four integer bone indices per vertex; it has no
authored `m_UV4`. The shipped CharacterNPR vertex declares raw `POSITION`,
`BLENDWEIGHTS`, `BLENDINDICES`, and an alternate `TEXCOORD4` previous-position
stream. Per-draw record `+0x4C` carries flags, `+0x50/+0x54` current/previous
skin-row offsets, `+0x00..+0x3F/+0x60..+0x9F` current/previous object matrices,
and `+0xA0.x` the current-versus-previous selector. Native code ORs `0x10` for a
skinned draw; if runtime deformation is unavailable it also ORs `0x20`, and the
shader evaluates the original 1/2/4 weight/index influences from both matrix
ranges. Without `0x20`, current is read from `POSITION` and previous from the
runtime-produced `TEXCOORD4`. `0x180515310` rolls current deformation allocation
`+0x3C0` to previous `+0x3C8`, allocates a new current output through
`0x1810BA580`, and submits both through `0x1810CC5C0`'s paired descriptor ring.

The final producer and graphics binding are no longer unknown. A targeted
AnimeStudio raw export from the installed `unity default resources` recovered
ComputeShader PathID 302 as exact `HGMeshSkinning` bytes: 16,724 bytes,
SHA-256
`991D1CCDC026BEAC1856D6FA4F8FA1B98A80435A06ECEA52E016E608FE0E0D71`.
Its embedded SPIR-V at `0xF4`, size `0x4038`, names `CSMain` and the same four
resources independently initialized by native code:
`_SkinMatrices`, `_OutVertexBuffer`, `_SkinningInfoArray`, and
`_SkinningInfoIndexArray`. Native initializer `0x1810C388E..0x1810C39C8`
loads `HGMeshSkinning.compute`, resolves `CSMain`, queries its real group size,
and caches the kernel runtime. The shipped module is `128x1x1`.

Batch producer `0x1810BD290` builds one 0x38-byte record per mesh containing
source vertex-buffer address/base/stride, weight/index stream address and
offsets/stride, normal/tangent and 1/2/4-influence encoding flags, matrix-row
base, first workgroup, vertex count, and output byte base. It uploads those
records plus a uint workgroup-to-record index array and dispatches
`sum(ceil(vertexCount/resolvedThreadsX)),1,1`. `CSMain` skins current
position/normal/tangent and writes only the new current output in the
source-compatible packed or expanded layout. Previous vertices are not copied:
the old current allocation/offset remains alive as previous. On a render-gap
byte or missing history, native code aliases previous to current before writing
the paired ring entry.

`0x1810C2DD0` selects the active descriptor bank as
`manager+0x50+(generation%3)*0x40000`; command `+0x1128` owns that bank and
`+0x1120` its per-draw index table. Graphics helper `0x181057480` replaces mesh
stream zero with the current descriptor, appends the retained previous
descriptor, appends the preserved original source stream zero, and resolves the
three generated history channels through `0x1810582D0`. For the selected
CharacterNPR member that is the exact route from current output to `POSITION`
and retained prior output to `TEXCOORD4.xyz`; adjacent generated channels carry
prior normal/tangent when requested.

The history selector is no longer ambiguous. Generic draw setup stores virtual
slot `+0x118` at record `+0xA0`; the installed SkinnedMeshRenderer vtable points
that slot to `0x18051A780`, which returns `(1,1,0,0)`. Therefore the selected
shader uses the true previous deformed position. A skipped render generation is
handled separately by setting previous row offset equal to current, not by
converting renderer byte `+0x390` into that float. Renderer `+0x394` is a
separate atomic maximum-displacement float and must not be conflated with the
byte. Pass-level admission is also exact: ForwardOpaque owns sceneMV target 1
with Load/Store, and the selected Zhuang skin member requires
`HG_ENABLE_PER_OBJECT_MV SRP_INSTANCING_ON _DIFF_RAMP_ON _EMISSION
_HIGHLIGHT_MAP _SDFLIGHTMAP`; 16 pinned Wulfa/Zhuang skin/cloth/hair/eye
fragments write the target.

No lab draw was added. The original producer and binding are closed, but stock
Unity does not expose this fork's per-draw current-stream replacement plus
previous/source stream append on the existing imported `SkinnedMeshRenderer`.
Feeding that already-deformed compatibility stream into the row-buffer branch
would double-skin. The next implementation must be a separate unskinned raw
indexed draw owning source weights/indices, current and retained-prior output
buffers, the generated history channels, and CharacterNPR ForwardOpaque MRT
admission. CPU `BakeMesh` history or a fabricated UV would not be that path, so
opaque-character sceneMV remains neutral. The verifier, JSON, and report
Markdown under
`scratch/reverse_engineering/scenemv_history_producer/` have SHA-256
`9AFF0B0846292E08FD97B644195FDD74420DE9128E02C56D0F8B42F7C9EC568B`,
`11BE9BB294AD9660AD2E65DEDD69016847BFFC713C217AD563EFECCD6A4DF524`,
and `F4FA99FD8E886F07E15E58ACAFCB9F324D90FDC20CCB5A6E3DFDC598DC2AFAC8`.
The pinned selected-VFX source chain is
`scratch/reverse_engineering/vfx_mrt_source_chain/` and its JSON
SHA-256 is
`34D75C19D64BFB0B6E12035810E842994780A15B1B0F47CE0DE45594D9887B53`.

The selected compatibility implementation is now active rather than only
designed. `EndfieldRecoveredSceneMVCompositor` allocates the exact packed
current-frame target, performs one neutral opaque clear, uses native MRT
render passes/subpasses, copies each old scene-color handle with a fullscreen
`SampleLevel` pass before drawing into its clone, publishes the old handle as
`_SceneColorTexture`, and carries the new handle through main ForwardOnly,
writable-depth Distortion, post, and after-post presentation. ForwardOnly and
after-post use read-only depth/stencil; Distortion uses writable depth/stencil.
Admission also requires an unambiguous viewer-selected rig (or exactly one
active rig), finite positive exposure, exact `_VFXParams0.xyz`, and
`fmodf(Time.time,1024)`-equivalent positive-time `_VFXParams0.w`; otherwise the
fragment clips. Its main ForwardOnly -> Distortion -> post -> after-DOF
ForwardOnly schedule now matches the current retail call graph; optional stages
retain their original runtime gates. SceneMV admission no longer incorrectly
requires an active blur/refraction Distortion material: any admitted main or
after-DOF ForwardOnly material also activates the resource/handle path, while
the Distortion callback remains conditional on an admitted Distortion member.
A post-fix batch load under exact editor `2022.3.62f3 (96770f904ca7)` exits
cleanly with zero C# compiler, shader, null-reference, unhandled-exception, or
crash diagnostics; the compile-check log SHA-256 is
`2FD075D28A08E8F0FB2C42676739AB3059D75FBF468FEF9AE99A8E3D3CF9F1B1`.

The particle importer admits exactly six materials by the complete tuple of
material PathID, name, original Shader PathID, ordered keywords, and custom
render queue: four VFXBaseV2, one `_USE_MASK` radial blur, and one
`_USE_DISSOLVE` refraction material. It transfers declared textures/ST,
floats, ints, colors, keywords, queue, and instancing state; the other 54
source materials stay on the `ColorMask 0` shader. The selected BaseV2 port
preserves the original reciprocal-exposure multiplication and position-hash
`unity_LODFade.xy` coverage path. The radial port respects `_InParticle`; the
refraction port preserves the selected red/alpha normal decode,
fixed-direction carrier, dissolve remap, and `(1-lodFade.y)` intensity factor.
The final Unity `2022.3.62f3` import report passes with 6 recovered and 54
fail-closed materials, 70 particle systems/renderers, 14 meshes, and 75
textures; there are zero bounded C# errors, shader errors, or exceptions. Its
log and report SHA-256 values are respectively
`4144EE8037AB74620A0AC2EDA349C5BF8C28F7CAFA7CED289B319F46AF29E7CA`
and `8213B196BBB62297F8496C36C1CCABFFA66569DD2715D253CB9C5FD30953A6E3`.
The dependent 16-track gacha runtime then rebuilt against those generated
materials with zero bounded C# errors, shader errors, or exceptions. The
targeted rebuild now also regenerates/rebinds the shared viewer and validates
all 30 resident scene actors in the same batch, preventing prefab file-ID
regeneration from silently leaving a lineup actor inactive. Its Unity log
SHA-256 is
`A5FCE39FEF9D65C4F6D72746CC70EB3F141942FCDFD72A69F29B9D25575701AC`,
and the unchanged strict runtime report remains
`F8AAA54CDE4EF893D8B3ECBAE541A6CC6CA507197A566C311B0CF893F3CA0C9A`.
This is structural/editor validation, not a live RenderDoc proof of native
attachment load/store state, read-only DSV state, or retail-matching pixels.
The current installed-game exposure producer is now source-closed:
`ShaderVariablesGlobal` places
`_ExposureWithMiscParams` at constant-buffer offset `0x1b0`;
`HGCamera.UpdateShaderVariablesGlobalCB` (method 286748, VA `0x1832e0020`)
packs `.x = HGCamera.exposureAdaptation` and
`.y = 1.0 / HGCamera.exposureAdaptation`; the camera constructor initializes
both to `1.0`, and `UberPostPassUtils.AutoExposureUpdateData` (method 286827,
VA `0x189b7e3f8`) copies `m_currentExposure` into the live camera field at
object offset `0x6c8`. The remaining boundary is the exact adapted-exposure
value and temporal history at the selected captured frame, not the producer or
formula. The source-gated verifier/report is
`scratch/reverse_engineering/exposure_misc_params/verify_exposure_misc_params_recovery.py`
and its current report SHA-256 is
`B2F51974EC5D891BF0B2AFC81A737683EA2BB29230AEF9CAC0C5A3F46F8F9B69`.
The installed-game global mip-bias producer is also source-closed for the
selected scene and current recovered camera corpus. `HGCamera.Update` (method
286739, VA `0x183100120`) reads `HGCamera.m_AdditionalCameraData` at object
offset `0xac0`, reads `HGAdditionalCameraData.materialMipBias` at component
offset `0xa0`, and writes `HGCamera.globalMipBias` at `0x960`.
`HGCamera.UpdateShaderVariablesGlobalCB` writes that value to
`ShaderVariablesGlobal+0x1a0` and writes `pow(2.0, bias)` to `+0x1a4`.
The selected original Zhuang Fangyi `ExternalCamera` serializes
`materialMipBias=0` and `allowDynamicResolution=0`; all 17,900 camera
components in the current recovered timeline/AnimeStudio corpus also serialize
zero. The lab now publishes the exact pair `_GlobalMipBias=0` and
`_GlobalMipBiasPow2=1`, not a guessed identity fallback. Future camera assets
with a nonzero authored value must publish that value and its base-2 power.
The generated corpus inventory is
`reports/assets/character_recovery/global_mip_bias/material_mip_bias_inventory.json`
(SHA-256 `A6C5100B9B39088FF46C669AB434331F53E882BC38ECD65F962F377EF80E7FE4`);
the hash-pinned native/data/lab verifier is
`scratch/reverse_engineering/global_mip_bias_producer/verify_global_mip_bias_producer.py`
and its current report SHA-256 is
`6F48AACDAC6773140453ABA3C048271530B0C249EC81C781233445F255652D3B`.
All three materials set
`_IsSceneEffect=0`, so the selected DXBC bypasses `_VFXParams1`; that global is
not an open dependency for this ribbon. The strict mesh audit
covers all 30 prefabs and reports 411 generated mesh assets, zero pending
assets, and zero asset errors.

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

Li Zhiyan's private-item sampler/manifest join now handles both original cases
without shifting curves. Six `A_item_widget_lizhiyan_03_*` MuscleClips declare
94 source transform tracks, while the exact deco-3 prefab contains 78; the
sampler's compact binding table is authoritative, and all six now use indices
`0..77` with the 16 genuinely absent source paths retained as evidence. The 33
`A_wpn_misc_0047` source clips target deco-5/deco-6, producing 58 exact
owner-qualified records. Their shared
`Root/hold_jnt/block_all_jnt/wpn_funnel_potency_vfx_01` node is an original
empty Transform locator, not geometry. It was formerly removed by the generic
VFX-name scene filter; it is now retained only because selected original clips
bind it, while every VFX mesh/renderer remains excluded. The resulting Li
manifest has 24 body plus 89 item records, zero remap gaps, and SHA-256
`E18D2EDD9E89C42D3A4BB7D2AFC742DEE0624836FA210B901CE87FE073C7F813`.
The full-roster streamed audit validates all 321/321 imported item clips and
4,373,166 QVVF track payloads with zero sample failures; its report SHA-256 is
`3CB7A8F8D1CCF67EDDDB098ECAB251AE25575CF00B11DD49D52371AC7439EC14`.
An exact-editor targeted build emits Li with 21 skinned meshes, 743 transforms,
and 113 clips. Controller availability, activation timing, and the separately
fail-closed VFX payload at that locator remain distinct gaps.

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
   AnimeStudio shader bytecode or installed native code. Its humanoid table is
   now corrected from exact public-f1 and retail-f5 evidence: stock toe Up-Down
   uses selector 2, the six Endfield names fill foot selector 0 and toe
   selectors 1/0 on each side, and muscle-to-angle conversion preserves
   over-range inputs. Against the Force-Text public-f1 synthetic Avatar and
   `HumanPoseHandler` fixture, all 21 compared body bones agree within
   `3.43e-5` degrees. It still does not supply the missing f5 physical-output
   oracle or the complete original NPR shader graph.
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

The local Ruri.ShaderDecompiler was updated to upstream `de596a8` and its
shipped Endfield LitPoly fixtures exposed two concrete decoder faults. The CLI
now maps the older exact sidecar field names into the current wire model and
registers their explicit descriptor sets; it no longer silently loads those
fixtures as zero constant buffers. A strict SPIR-V pass coalesces duplicate
uniform aliases only when set, binding, one metadata owner, scalar shape,
array length, and stride all agree. A second exact normalization removes only
the redundant `uint32 -> uint64 -> float` SSA pattern emitted by the DXBC
translator. The vertex and pixel LitPoly fixtures now contain one declaration
per physical constant-buffer binding and both recompile with FXC as SM 5.1;
all nine shipped UnityBinary fixtures decompile without failure. The remaining
vertex warnings are duplicate output semantics, and the instanced UnityPerDraw
buffer remains a named flat cbuffer because its dynamic access-chain shape is
not yet supported by the structured-member rewriter. These are decompiler
boundaries, not evidence that the full live character shader schedule is
recovered.

The retail client observed on this machine is Unity 2021.3.34f5 using Vulkan
and a proprietary source-modified HGRP. The lab is Unity 2022.3.62f3 with a
custom D3D12-capable compatibility SRP. This is an architectural gap, not a
small material preset difference.

The maintained public editor installation is verified at
`D:\Program Files\2022.3.62f3\Editor\Unity.exe`: product revision
`2022.3.62f3_96770f904ca7`, SHA-256
`02E80B2C1D7F983375C97B612655BE9F8ED852121E3A4EEDF1570701C48EA5CD`.
Its Windows standalone support, Roslyn tooling, and package manager are present;
`ProjectVersion.txt` pins the same exact revision and all 55 maintained lab
launchers use it. The only 2021 launcher is the deliberately isolated stock ABI
oracle below.

The closest public engine baseline is now installed and pinned separately at
`D:\Program Files\2021.3.34f1`: Unity 2021.3.34f1 changeset `25266724e7bd`,
including its matching Windows IL2CPP player. `Editor/Unity.exe` has SHA-256
`5788A094ADFD757A918F0E8BA392E4E084FFCBAFCA64A917CBCE3EF0FAC6622C`.
A separate unchanged-source compatibility probe resolves all 11 packages,
including Timeline `1.6.5`, but stops managed compilation on exactly two API
differences in `HGCompatRenderPipeline`: public f1 exposes only the
two-argument `ShadowDrawingSettings(CullingResults,int)` constructor and has no
`BatchCullingProjectionType`. The forced shader pass therefore never loads, so
the absence of emitted shader errors is not a shader-compatibility result. This
is a precise public-f1 boundary, not evidence about the proprietary retail f5
extensions, and the maintained lab remains on `2022.3.62f3`. The isolated
report is
`unity_endfield_graph_shader_lab/scratch/unity_2021_3_34f1_probe/REPORT.md`
(SHA-256
`35AB77FBFF9C002ABC073E1C2B5B185D43B689D6692A9ECD98E20106D8291E0A`);
its verifier confirms an unchanged 162-file Runtime/Shader source snapshot.
A fresh full batch-mode stock-engine oracle reports exactly 95 muscles and
55 human bones and contains none of Endfield's six extension names. Its
nondevelopment IL2CPP `UnityPlayer.dll` has SHA-256
`F64218029F1B56FB67128BBC270C693EDEC402F2359583B8B456DF83172442C9`; the
retail f5 player remains
`B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`.
Exact binary comparison turns this baseline into structural evidence, not an
f5 output oracle. Public f1 has one unique 55-entry direct muscle-to-bone table
at RVA `0x17E70C0` and one unique 25-by-3 inverse body-bone/axis selector table
at `0x17E6D90`. Endfield has the corresponding unique 61-entry and 25-by-3
tables at `0x1DDE340` and `0x1DDE010`. Removing slots
28/30/31/39/41/42 from the former and clearing those six foot/toe selector
holes in the latter reproduces the public tables exactly. The registered
`HumanTrait.get_MuscleCount` implementations likewise return 95 at public RVA
`0x12CFD0` and 101 at retail RVA `0x153340`. This proves a surgical ABI
extension with consistent later-index shifting; it does not prove that the
remaining f5 transform implementation is byte-for-byte stock.

A separate public-f1 numeric fixture now exercises `HumanPoseHandler` on a
synthetic valid 23-bone humanoid. It requests all 95 stock muscles, captures
the resulting local/world Transforms, and verifies the 49 mapped body muscles
through a set/get round trip with maximum error `0.0011557043`; the 46
intentionally omitted eye/jaw/finger channels return exactly zero, and the
maximum captured quaternion-norm error is `4.11e-7`. The fixture SHA-256 is
`AB302D1A63C0B224C62513033EAA660DED467170A806E0D66A448E3E6FE18442`.
This is a reproducible stock-engine numeric test for any supposedly unchanged
subgraph. It still cannot validate Endfield's six new channels or substitute
for the missing original f5 physical Transform fixture.

A read-only bootstrap audit now closes why the untouched retail player cannot
serve as a drop-in oracle. Retail `UnityPlayer.dll` exports only `UnityMain`;
its normalized 38-byte wrapper matches public f1, but the DLL fails initialization
before that export can run under the public Mono/IL2CPP launchers. Retail
`Endfield.exe` instead imports only `EndfieldBase.dll` ordinal 1, whose DllMain
and sole export enter the protected `.tvm0` live-game bootstrap. That path was
not invoked. `GameAssembly.dll` exposes 241 generic `il2cpp_*` APIs but no
Avatar/Human/Animation/Transform evaluator, so IL2CPP initialization alone
cannot create the required native objects or icalls. The original input side is
otherwise complete: 486 physical nodes, 24 compact human nodes, 22 AxesInfo
rows, 206 clip-index entries, 61 body DoF values, 58 generic QVV tracks, 267
generic bindings, and 33 frames of 101 muscles. Inert, allowlisted CPU
emulation of retail `A7B990+B34260` is complete using the original 0x58-byte
Axes payloads in 0x60-stride records. The next pure stage is now covered too:
retail `B27930` executes all 33 Wulfa frames x eight ordered pairs, 264 calls,
using the exact retail Axes outputs as compact-pose input. Every call stays in
the pinned `B27930/B37BF0/A7AD50/B22C70/A7B990/B365D0/B36290/B38110` helper
set, returns normally, and writes only the two private compact poses and stack.
The 8,448-byte parent/child quaternion result hashes to
`3E9F68DFAA91C4DD784D49016C0F9FB7D1C1E7209BB80012FEBC23EE3ADD6EEF`;
the report is
`3B659F7BBF4E759BA75BD7817C8B6FBDE1BBE82E89BEC83DEEE6CBD134C66C2C`.
Maximum semantic-port deltas are `4.1724e-7` parent and `4.0234e-7` child,
with maximum angles `3.803e-5`/`4.320e-5` degrees and combined-orientation
preservation residual `1.449e-5` degrees. This confirms the maintained eight-
pair equations and order without a production formula change. It remains
code-derived evidence rather than an observed final retail Transform oracle;
live CPU-selected `atanf`/physical `RSQRTPS` low bits and the enclosing
`B314D0` scheduler/root object remain outside this inert phase. The pinned
feasibility contract is
`scratch/reverse_engineering/retail_f5_output_oracle/oracle_feasibility.json`
(SHA-256 `F4F2A787FAD95D0EB9BFAB80828EC06EF2FE9A4DADC909B19662A540AD220AE3`).

The recovered CharInfo frame contract is broadly:

1. shared physical camera and settled Cinemachine Composer;
2. depth/pre-depth and character PreG classification on shared depth/stencil;
3. ordinary deferred scene/GBuffer work and character shadow producers;
4. CharacterNPR opaque forward surface and outline, followed by the shared
   mixed transparent list where overlay 2900 precedes hair 2985 and body/cloth
   3000;
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
| Cloth/body `CharacterNPR` | Original Base/normal/packed/ramp contracts; linear data-map imports; packed M/S/shadow/smoothness; source-shaped diffuse/light blend; selected direct/specular carriers; back-face sign; shadow and light-list hooks; `_ParallaxMarchNum` refinement; source-proven Repeat/Bilinear/aniso-1 sampling for `_ParallaxTex`; exact `_CLEARCOAT` direct/environment energy carrier and authored bindings for all eight selected roster materials; exact non-advanced Last Rite cloth-03 stockings alpha/wet-tint/anisotropic direct lobe; selected-camera `_GlobalMipBias=0` and `_GlobalMipBiasPow2=1` producer/value | Complete variant matrix and remaining GGX/DFG/environment integration outside the selected clear-coat/cloth-03 carriers, advanced-mask stockings on other materials, customization/dissolve/wider weather branches, exact additional-light population, and full downstream shadow composition. |
| Skin/face | LUT, face SDF/mask/emotion/highlight inputs; packed normal path; selected Wulfa/Zhuangfy body ForwardLit source branch; selected Default/Fog/Rim punctual rows; face/head basis publication; exact Wulfa/Zhuang non-normal face fragment and Li normal-mapped face fragment carrier split, with unscaled directional RGB in the ambient lightBlend and intensity-scaled RGB only in the adjacent direct luma/chroma term; exact native compressed payloads for 193 face/iris/emotion and priority Li/Last Rite/Zhuang/Wulfa surface/accessory objects across 388 generated owners | Only two body materials and three representative face materials are deeply source-gated. Other skin/face variants and generalized nonzero rim/subsurface/weather state are incomplete. Texture descriptors are exact across the roster, while 658 non-eye objects outside the payload contract still use decoded PNG top levels and Unity-generated lower mips. Live per-draw/light/shadow inputs and final post response remain incomplete. |
| Hair | Split normal, stroke/line maps, packed shadow/smoothness, authored tangent sign, back-face behavior, two-lobe/aniso diagnostics, rain/wet carrier, outline and shadow hooks. The exact dual-strand energy carrier (`darkenedScale` rain/wet decode + `primary 0.04*specMask*ramp*intensity*5`, secondary `sinTheta2^floor(200*(1-range2))*smoothness*color2` suppressed by first-lobe max, and the `specAmbient*fullDiffuse*CP13.w` placement) is closed at equation/data-contract level against the four selected Wulfa/Zhuangfy Hair02/Hairt02 SPIR-V modules and is integrated behind `ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE` in `EndfieldCharacterHairRecovered.shader`. Its verifier `scratch/character_recovery/hair_energy_carrier_exact_20260713/verify_hair_energy_carrier_exact.py` now passes 201 checks, including the four source modules, the default-off viewer/build gate, and clean D3D12 off/on/material-only captures for both actors. | The exact selected equation is still not a valid whole-frame default. At 3840x2160 it changes 1,489,389 Wulfa pixels and 1,447,598 Zhuangfy pixels. Within the registered head/hair crops, mean luma across changed pixels rises by 18.48 and 22.17 sRGB-byte units respectively. Holding the physical CharInfo sky off while retaining the material keyword produces byte-identical output to the full selector for both actors, so this delta belongs to the material path rather than the sky. Visual comparison to the supplied retail frames shows Zhuangfy's hair/face highlight becoming materially too bright and Wulfa's hair/white-cloth balance also moving away even though some dark hardware improves. The source-energy core therefore remains opt-in; the missing source context is the next target, especially complete diffuse/specular/ambient scheduling, live shadow/light membership, and later frame state. Secondary hair motion is not a shader feature and remains absent. |
| Eye/brow | All 57 current playable materials are exact-contract gated across 29 iris, 20 LUT-brow, and eight plain-brow fragments; exact 2000/2015/2050 queues, DepthOnly state, opaque alpha, mandatory integer-pixel `_ScreenSpaceShadowMask.Load(...).x`, and packed scene-motion MRT are pinned. The retail RG8 producer descriptor, pass order, global binding and R semantics are source-closed. The original quarter-resolution directional shader, 7x1/1x7 blur, full-resolution scene composition and `ContactShadowCS/RayTracingV2` are bytecode/native pinned. The contact pass's native four-side/split/compact dispatch builder, inverse-projection ABI, current installed bit-4 stencil variant, source-owned first-contact phase 1, D32/S8 public-Unity bridge, and downstream G displacement are now implemented behind a separate default-off gate and GPU-proven on both reference actors. CharInfo's cloud-disabled constants/white texture owner, ASM skip binding, CSM frame/ShadowData ABI, installed three-cascade D16 defaults, and ordinary-Unity ShadowCaster renderer-list construction/draw dispatch are exact. A default-off lab-prefixed atlas produces stable non-clear Wulfa/Zhuangfy caster texels; the exact raw receiver and blur consume it, and the full-resolution scene-R attachment now performs the installed endpoint trust plus 16-Gather/64-comparison refinement. Same-generation Unity 2021 and independent Unity 2022 D3D12 probes prove the disabled ASM default resource comparison-neutral for valid positive references. The separate sceneMV contract is source-closed as full-resolution transient logical `A2B10G10R10_UNormPack32`, deferred-neutral-cleared and forward-loaded/stored; the selected Zhuang VFX path now implements that native attachment. | Game-only general ECS/grass/tree caster ownership and content, the Endfield-fork zero/default queue-range semantics, canonical CSM/ShadowData/low-resolution/contact publication, complete scene-R ownership, physical pool lifetime, and final scene-R parity remain open. Future patches or gameplay-time mutation could change the current installed terrain fake-shadow value. The compiled Eye-R branch is content-valid gated and unreachable from the default-off scene-R attachment. Eye-only frames do not yet independently request the selected sceneMV owner, and live MRT pixels have not been validated, so this is not whole-pipeline equivalence. |
| Outline | Correct `CHARACTER_OUTLINE` pass is now scheduled; original width/mask/depth inputs are represented where available | Still a compatibility shell. Original average-normal stream use, depth-aware width, exact lit NPR composition, visibility/temporal behavior, and all internal ordering are incomplete. |
| Overlay shadow | Multiplicative material; exact shipped `Ref [_ShadowOverIris]`, read-mask 20, equal comparison, keep-only stencil state; source material refs 4/20; exact selected `DISABLE_DRAW_UNDER_HAIR SRP_INSTANCING_ON` eye fragment plus the no-keyword hair-shadow fragment; both shared eye masks now use their byte-identical installed 1,392-byte BC7 six-mip chains with Linear `RGBA_BC7_UNorm` sampling, streaming mips, Bilinear/Clamp/aniso-1; all five eye-shadow materials and the eye-white material are source-contract pinned; all 84 generated overlay materials are regression-guarded; exact Back cull, LEqual, ZWrite-off, `Zero/SrcColor` RGB and `One/One` alpha blend; exact one-factor output alpha/two-factor multiplicative RGB alpha; exact no-keyword `_SceneColorTexture.Load(...).a == 1` suppression and pre-transparent opaque-scene copy; camera-relative origin and light-angle subtraction; normal Halton jitter producer and exact CB upload; selected-camera `_GlobalMipBias=0`/`_GlobalMipBiasPow2=1`; native-closed atmosphere bypass; exact 32-pixel XY/2,048-slice membership plus `LightCharacterOnly`/inverse-`charIgnoreSceneAdditionalLights` admission and type-4 Fog accumulation for all 30 isolated CharInfo rigs (266 rows, 40 Fog, ten directional); neutral missing-producer fallback; current installed shared scene-depth ownership, one mixed ECS+SRP transparent submission, opcode `0x4F`, pass-name list, sorting value 87 (`CommonTransparent|RendererPriority`), authored two-slot arrays, disabled overlay predepth, and 2900 -> 2985 -> 3000 cross-queue chronology are hash-pinned and active in the lab | The exact eye/eye-white keyword intentionally bypasses opaque-scene suppression; no missing suppression buffer remains on that eye-material branch. Forced jitter/TAA history constants remain IFix-wrapped. Native `CullLights` now closes the per-camera owner, tier, max/min-distance, Point/Spot frustum, authored OBB, occlusion-result, distance-sort and cap gates; cookie/flicker are proven post-shortlist payload inputs. Arbitrary gameplay still lacks the scheduled projected-screen/scene-layer cull equation, occlusion/cache internals, fallback-core lift, exact tie ordering and live unrelated light population. The opcode-`0x4F` execution path, mixed merge, criteria-87 comparator, equal renderer-data `+0x0C`, and zero pass-ordinal `+0x4C` are closed. Only the runtime-generated unsigned `+0x08` state key can permute a pair; a tie preserves authored order, and one live capture at `UnityPlayer.dll+0x541500` remains the exact final proof. No global reversal is justified. Generalized prevention of all double-darkening and the installed IFix target remain open. |
| Li Zhiyan fur | Original `CharacterNPR` material inputs and transforms (`_FurMap` 40x40 with offset 1,1); exact 20-layer `i/19` shell mesh; selected `blob500/33` vertex environment-gravity, unnormalized skinned-world normal-to-down bend, raw-UV direction-alpha length, and current/previous clip-offset reuse; selected fragment cell hash, RG direction/noise-UV warp, B density, shell cutoff/sharpen, root-shell bypass, view-edge coverage, packed rain/wet thinning, alpha clip/output, normal-map-preserving behavior, fur-AO shadow carrier, wet 0.88 shadow floor, active Li ramp coordinate, and auxiliary signed-fourth-root motion MRT are source-pinned. The recovered surface path is active on the source-proven deco-3 lifecycle. | The active Li material has `_FurNoise=0`, `_FurTTIntensity=0`, and `_FurSharpen=0`, so its selected ramp coordinate is exact without resolving the nonzero-noise horizontal transmission reference generally. Complete shared CharacterNPR lighting/additional-light/environment scheduling is still open. The custom SRP has no retail previous-transform/TAA history attachment, so the source-closed auxiliary MRT remains deliberately unbound rather than receiving fabricated history. |
| Li Zhiyan emission/refraction | The selected `CharacterNPR_VFX` emission branch samples `_EmissionTex` with authored ST, multiplies RGB by `_EmissionColor`, and adds it before exposure. The exact material `M_fxui_lizhiyan_relax_sp_01_33` alone uses the selected `VFXRefract` RG decode, authored 1x2 ST/speed/direction/intensity, vertex-alpha modulation, and pre-transparent scene-color sample. Both deco-4 materials are controller-active, not removable shells. | Refraction is deliberately identity-gated to path ID `3646701341811672247`; other materials from that shader family stay on the generic recovery until their own variants are closed. The lab's scene-color attachment timing is source-shaped but not yet a proof of the retail frame-resource lifetime. |

The face carrier correction is independently present in the exact
Wulfa/Zhuang SPIR-V fragment 0263 (SHA-256
`C66724392359EF76C38F61FF712799D0BE20727075FD7C5A6D26F78E9FDD608F`)
and Li's `_NORMALMAP` fragment 0269 (SHA-256
`710D907869F1FEB5F11B4F98CD7844324A40A9C4236D0B64A4978186CAE9BED1`).
The previous lab face path used the intensity-scaled color in both terms,
effectively applying main-light intensity twice when `_CharacterParams12.y=1`
and flattening/overdriving the dark-side organization. The corrected
source-gated path keeps the scaled carrier only in the direct luma/chroma
equation. The strict material/keyword/hash/equation verifier is
`unity_endfield_graph_shader_lab/scratch/character_recovery/skin_face_dark_side_branch/verify_skin_face_dark_side_branch.py`.

The Li fur vertex/fragment evidence is the paired D3D11 program
`0840_endfield_dxbc_0.dxbc` / `0841_endfield_dxbc_1.dxbc`, SHA-256
`304c16d36f301b2742b38e2f0850af3389f243a425e0e5f925e4b95345390c9d` /
`30327371e5bd5c16dc5262a49758b84edba788a4bae6f6d6dc2184d248cfe88e`,
plus its SHA-256
`fb78c1ba7837036f3d754122f6fff374cac9cbf42d19840a1576393d215c7e11`
sidecar. The exact keyword set is `_CHARACTER_FUR`, `_ALPHABLEND_ON`,
`_NORMALMAP`, `_DIFF_RAMP_ON`, `_SPEC_RAMP_ON`, both recovered shadow/motion
keywords, and SRP instancing. The maintained verifier is
`unity_endfield_graph_shader_lab/tools/verify_lizhiyan_fur_fragment_recovery.py`;
its focused CPU regression is
`tools/test_verify_lizhiyan_fur_fragment_recovery.py`. The verifier also pins
Li's original material JSON and the exact source mesh. That mesh has 63,960
vertices: 3,198 base vertices repeated once at each of 20 exact shell
coordinates from 0 through 1. The selected vertex samples direction alpha at
raw UV, evaluates the same CP10/custom-per-draw rain/wet/global-wet carrier as
the fragment, raises `_FurGravityStrength` toward 0.8, and bends toward
world-down by `shell * (0.5 - 0.5 * normalWS.y)` without normalizing. The
same current projected shell offset is added to current and previous
non-jittered clip positions. The fragment encodes half-NDC motion with a signed
fourth root around 0.5, writes Z=1, and writes W=0.4 for Li's neutral selected
surface state (the alternate source threshold writes 0.7). The lab implements
the exact current surface displacement but leaves the auxiliary MRT helper
unbound until the retail history attachment exists. The verifier rejects the
superseded normalized object-space gravity, albedo-AO, direction-as-normal,
base-alpha, and linear edge-width approximations. A
targeted Li rebuild under the project-pinned Unity `2022.3.62f3` compiled the
shader and serialized `_FurNoise`, `_FurSharpen`, `_FurTTIntensity`,
`_SurfaceType`, and `_DisableRainEffectOnMaterial` from original material data.

The active generated shaders are:

```text
Endfield/Recovered/CharacterCloth
Endfield/Recovered/CharacterSkin
Endfield/Recovered/CharacterHair
Endfield/Recovered/CharacterEye
Endfield/Recovered/CharacterOverlayShadow
Endfield/Recovered/VFXRefract
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

The source-energy selector audit found and removed a gate regression before
using the runtime references as evidence. Both shared viewer scenes and two
preview-building paths serialized `enableRecoveredSourceEnergyCore=true`,
despite the selector's default-off contract. They now serialize false.
`CharacterRecoveryPresentationController` also defaults false and admits the
path only through its explicit inspector value,
`ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE=1`, or
`-endfield-recovered-source-energy-core`. The dedicated feature-validation
renderer remains an intentional explicit-on probe. This preserves ordinary
viewer/roster behavior while allowing clean batch A/B ownership.

Fresh Unity `2022.3.62f3` D3D12 pairs are under
`unity_endfield_graph_shader_lab/scratch/character_recovery/hair_energy_core_ab/`.
Wulfa off/on PNG hashes are
`8ACC2A4098FA7DEA9D125EF763D37B6397CD391E275187E764559ABB31F1C4BD`
and
`2B27DC9167A18CB8DD47B93F34745FC5CC80ED543986FE0E96B18A3D742A2595`;
Zhuangfy off/on hashes are
`4161E61712A3E18DB750F06DD96480ED6416419AF93B2B73A3A207495A7EB1FC`
and
`45966C1EBDFA9FEFF3A0C9DC7BF39EEE91F9E0CBFAF3A5C0182CA9DAE49579E0`.
The logs prove keyword zero/one and clean batch exit. The path affects far more
than hair: 17.96% of Wulfa pixels and 17.45% of Zhuangfy pixels change.
Registered head/hair changed-pixel luma rises by 18.48 and 22.17 byte units.
An additional material-only diagnostic holds the physical CharInfo sky off
while leaving the same material keyword enabled. Its PNG is byte-identical to
the full-selector PNG for each actor, so the observed delta belongs to the
material equations/path and not the source-sky carrier in these exact frames.
Against the supplied retail frames, the enabled path materially over-lifts
Zhuangfy's crown highlight and face and also worsens Wulfa's hair/white-cloth
balance, even though some dark hardware gains contrast. This rejects
promotion of the otherwise equation-exact carrier. The next binary-backed
question is which missing original scheduling/input suppresses or redistributes
that energy, not whether to tune the carrier to the screenshots.

The next installed-binary pass found one such concrete scheduling error.
`LightCulling.PrepareCPUData` (method 285282, VA `0x189d0c7bc`) calls the
shared-light and HGLightConfig character descriptor overloads at
`0x189d03a2c` and `0x189d03db8`; both feed the common implementation at
`0x189d03ae8`. In all four selected Hair fragments, descriptor RGB is first
resolved without intensity, a second RGB value is multiplied by descriptor W,
the unscaled value alone enters the CP12.y ambient `lightBlend`, and the scaled
value alone enters the adjacent direct luma/chroma term. The shared hair/cloth
port had incorrectly reused the scaled value in both places. Both overview
actors resolve CP12.y=1 (Zhuangfy inherits the enabled base-volume override),
and the settled CharInfo descriptor W is `1.624386775`, so this was a real
duplicate intensity. The corrected clean D3D12 frames reduce changed-pixel mean
luma by 3.19 Wulfa and 4.49 Zhuangfy byte units relative to the superseded
selector-on frames. The focused verifier passes 91 checks at
`scratch/character_recovery/main_light_descriptor_split_20260723/verify_main_light_descriptor_split.py`.
This improves the direction of travel but does not close retail contrast.

Those corrected captures also proved that the ordinary source-energy A/B had
no character-shadow producer at all: the pipeline asset disables it and the
fragment received neutral white. Combining the corrected path with the already
recovered 1024/D16 CameraVirtualLight diagnostic changes 331,818 Wulfa and
316,664 Zhuangfy pixels (about four percent of each frame), reducing their
changed-pixel luma by 28.26 and 31.29 units. This establishes the shadow input
as materially important, but the current result has visibly too-hard/blocky
silhouettes on Wulfa hair/cape and Zhuangfy dress. It therefore remains
diagnostic.

The next installed-VFS pass closed one receiver false lead and recovered a
separate scene-shadow caster class. Shipped
Vulkan and D3D11 `ScreenSpaceShadowResolve_Character` programs run the same
16-Gather/64-comparison blocker-aware G resolve already in the lab; there is no
missing post-resolve softening stage. More importantly, both playable
postmodels contain an authored `Shadow_Proxy/SP_Desktop` hierarchy that the lab
prefabs had omitted. Exact postmodel renderer PPtrs map all 20 proxy meshes to
the source-model LOD1 payloads, not the visible LOD0 meshes: 12 Wulfa entries
and eight Zhuangfy entries. Retail renderer state enables only 11 and five,
respectively; all four VFX-part proxies are disabled and use ShadowsOnly
casting. The active set is solid except Wulfa hair-02, whose exact LOD material
enables alpha test at 0.4. Body/face/default-Lit proxies cull back faces, while
cloth/hair proxies are two-sided.

The retained default-off diagnostic imports those exact LOD1 meshes, bindposes,
weights, ordered bone paths, root bones, enabled states, cull modes, and the
one alpha-tested BaseMap relationship. It fails closed if any contract member
is unavailable.
Fresh D3D12 logs prove `desktopShadowProxies=11/12` for Wulfa and `5/8` for
Zhuangfy with complete sphere resolution. Against the superseded LOD0-caster
frames, the source proxy changes 0.625% and 0.862% of the full frames; shadow
mask overlap remains 0.943 and 0.947. The change is source-correct but does not
by itself remove the hard local attenuation. A later exact helper audit proved
that using these proxies in the dedicated atlas was a membership false lead:
shadow modes 3/4 are stored separately, assigned rendering layer 2, and given
invalid character index 15. The proxy inventory and GPU results remain valid
scene-shadow evidence and historical scheduling diagnostics, but they are not
the original dedicated character-atlas caster set. Evidence and a 389-check
verifier live under
`scratch/character_recovery/character_shadow_proxy_recovery_20260723/`; the
verifier pins the three installed VFS chunks that supplied the postmodels and
source-model meshes.

The current installed binary now closes the managed atlas-caster predicate.
`HGCharacterHelper.FindRenderers` stores ordinary renderers as
`CharacterRendererInfo(renderer,inLodGroup,castSelfShadow)` while shadow modes
3/4 go to `shadowProxyRenderers`. `HGCharacterQualitySettings..cctor` (method
289105, VA `0x184d7a550`) writes `characterSelfShadowOffLodQuality=2`, so LOD0
and LOD1 retain the row flag and LOD2+ clear it.
`HGCharacterHelper.UpdateShadowRenderingLayer` requires helper self-shadow,
that row flag, and the fork-only `Renderer.GetIsRealtimeShadowCaster()` result
before assigning the live character index. The separately stored proxies
receive layer 2 and invalid index 15. This also corrects the fork enum:
`ShadowCastingMode` 0/1/2 are Off/On/TwoSided and 3/4 are
ShadowsOnly/ShadowsOnlyTwoSided.

The exact current LOD0 manifest intersection contains 151 ordinary
realtime-caster rows across 14 recovered actors: Wulfa 14, Zhuangfy 9, Lifeng
10, Mifu 11, Pelica 12, Endminm 11, Endminf 11, Chen 10, Wolfgd 13, Aglina 9,
Aurora 11, Antal 6, Ardelia 13, and Bounda 11. Five imported LOD0 rows are
excluded by original `m_RealtimeShadowCaster=0`: two Wolfgd furcards, Aurora
and Ardelia fur, and Bounda's shadowless cloth. Every admitted row is enabled,
has ordinary `m_CastShadows=0`, realtime true, and static false in the source.
Per-actor count plus FNV-1a path hashes make the new provider fail closed.

The adjacent ECS query is also exact.
`HGMeshRender.CreateRendererListWithCharacterIndex` receives view handle
`HGCamera+0xa20`, character index `slot+1`, render-flags mask/value
`0x400/0`, light-mode mask `0x400`, zero global keywords, and the context.
Thus it excludes `HGRenderFlags.ShadowOnly` and selects `ShadowCaster`; it does
not require `CastShadow`.

The retail UnityPlayer generated-icall table pins that binding at index 398 /
RVA `0x1f2070`, followed by the query adapter at `0x104f4b0` and exact callback
at `0xff8710`. The adapter injects high-mask `0x8000` into
`componentMaskHasNone`; native assertion identities and callback control flow
close this as `HGUIParticleComponent` ID 79. The job separately requires
low-mask `0x10000`, `HGRendererComponent` ID 16. Its only-ShadowCaster route
dispatches three reachable renderer families at RVAs `0x1023930`,
`0x1024480`, and `0x1025090`; all three compare the stored entity character
index with the requested index. This closes the generic query/filter identity,
but not a live entity census.

The pinned Zhuangfy particle inventory supplies a decisive VFX boundary.
Only `P_fxui_zhuangfy_ui_overview_start_01_jianqiang/all/lizi (1)` stores
`m_CharacterIndex=1`; it is non-UI, enabled, and also stores
`m_RealtimeShadowCaster=1` despite public `m_CastShadows=0`. Its exact material
is `M_fx_ui_lizi_904` (path ID `604984703151022578`), whose original
`HGRP/Effect/VFXBaseV2` artifact has four `ForwardOnly` passes and zero
`ShadowCaster` passes. Even if its live entity satisfies the character-index
query, it cannot write atlas depth. The lab therefore must not add it as an
atlas caster. No additional VFX participation is inferred outside this pinned
set. Reproducible source evidence is under
`scratch/reverse_engineering/character_shadow_ecs_caster_20260724/`.

The current installed binary now closes the producer matrix/depth/bias
boundary as well. `HGShadowManager.GetMatrices` (method 285508, VA
`0x189d20b74`) proves the CameraFollow pitch/yaw construction, literal-zero
Euler roll, extents-length support distance, eight-corner fit, XY recentering,
`LookRotationSafe(-lightDirection,rotatedUp)`, and fitted min/max Z. Its final
call passes `(width,height,minZ,maxZ)` to native VA `0x1833a3cb0`; that target
constructs the exact width/height orthographic matrix, closing the previous
source-level inference around the final projection. `HGShadowUtils.GetShadowBias`
(method 285679, VA `0x189b51728`) computes
`2/projection.m00/resolution`, applies the setting scales, then the exact 1.5
sample-mode-2 multiplier. The character render delegate (method 285534, VA
`0x189d2524c`) passes hardware depth/normal fields directly to
`CommandBuffer.SetGlobalDepthBias`, draws, and resets both to zero; there is no
hidden scalar or sign conversion. The selected original Wulfa hair SPIR-V
independently pins the same receiver equation and slope clamp used by the lab.

The lab's first discrepancy was carrying camera-derived Euler Z instead of the
native literal zero. Correcting it is byte-neutral for both selected cameras,
proving their effective camera roll was already zero.

The same current-binary audit now closes the single-actor helper/index/layer
path. `HGCharacters.RebuildFilteredLists` rebuilds the self-shadow list from
helpers whose serialized `m_EnableCastSelfShadow` is true, calls
`QuerySelfShadowID`, then updates each helper's rendering layer. The ID is the
filtered-list index or `-1`; `GetShadowLayer` is exactly
`index < 0 ? 0 : 1 << ((index + 8) & 31)`. The current executable admits only
IDs `0..13`: `EnableCharacterSelfShadow`, `CharacterShadowFrameSetup`, and
`SetupCharacterShadowReceiverConstants` all clamp or loop at hexadecimal
`0xE`. The selected shaders still declare 15-entry arrays, so distinguish the
15-element constant-buffer ABI from the current 14 assignable helper slots.
Focused installed exports prove Wulfa and Zhuangfy both have priority 100,
`m_EnableCastSelfShadow=1`,
`m_EnableCastHDPunctualLightShadow=1`, and sphere bounds enabled. Either actor
alone is therefore exactly filtered-list index 0 and rendering layer 256.
`HGCharacterHelper.CompareTo` completes the general ordering rule: serialized
priority descending, then `UnityEngine.Object.GetInstanceID()` ascending.
Concrete equal-priority IDs remain lifetime/creation-order state, but the
comparator is no longer unknown.

`CharacterShadowFrameSetup` also closes the atlas grid. Counts 1..4 use
`(columns,rows)=(count,1)`; counts 5..14 use
`(4,ceil(count/4))`. Both dimensions are multiplied by the 1024 tile
resolution. Caster index `i` gets normalized rectangle
`(i%columns/columns, floor(i/columns)/rows, 1/columns, 1/rows)`. The current
14-entry maximum is therefore a 4096x4096 D16 atlas with two unused last-row
cells.

The full current `RenderCharacterShadows` body closes the CPU/render-graph
schedule around those rectangles. It rejects missing/empty helper rosters,
missing directional-light state, disabled feature/pass state, and non-ECS
frames without caster bounds; then creates the atlas and publishes caster and
receiver constants. For every admitted index it uses the corresponding
1024x1024 pixel tile, prepares the Unity `ShadowCaster` renderer list, creates
the ECS renderer list with character index `i+1`, binds the atlas as the depth
attachment, and disables render-graph pass culling. The Unity list sorts with
`SortingCriteria.CommonOpaque`. The original 14-entry scheduling path is
therefore binary-closed.

The lab executes this route behind a separate default-off selector. Its
two-actor probe sorts Wulfa and Zhuangfy with the recovered equal-priority
instance-ID rule, assigns exact layer bits 256/512, builds the 2x1
2048x1024 D16 atlas, and selects each actor's matrix, bias, direction, and
rectangle from the renderer's `asuint(unity_RenderingLayer.x)` carrier. All
prior renderer masks are restored after the camera. Normal creation order
places Wulfa/Zhuangfy in slots 0/1 and hashes
`5980451E19BF3FD5B0990BE11DB49CF9B04BFDEA5701A7A6DA54B0D443867272`.
A forced comparator-order swap places Zhuangfy/Wulfa in slots 0/1 and hashes
`A43D8743D60998BDFAF531B170F062020FC8486B07A1408339B9077B93EAD896`.
The complete slot/matrix/tile swap changes only 136 of 8,294,400 RGB pixels
(0.0016397%, MAE 0.00001346/255, maximum channel delta 7). This GPU-closes the
lab's two-actor transport/scheduling subset.

Focused installed-VFS and exact AssetMap recovery now adds Lifeng, Mifu, and
Pelica. Their priority-100 helpers retain self-shadow, punctual-shadow, and
sphere-bounds eligibility; their exact sphere counts are 22, 41, and 20. Each
postmodel has seven exact source-enabled desktop proxies, so the combined
Wulfa/Zhuangfy/Lifeng/Mifu/Pelica contract contains 41 exact LOD1 meshes with
active counts `11/5/7/7/7`. The source graph was used only to select and
resolve the exact three postmodel identities and Animator assets; installed
AssetMap and focused postmodel/mesh payloads remain the authoritative proxy
and helper evidence.

Fresh D3D12 execution reaches the first retail row transition:
`count=5`, `grid=4x2`, `atlas=4096x2048`, 1024 tiles, D16. Normal scene
lifetime order places Mifu/Pelica/Lifeng/Wulfa/Zhuangfy in slots 0..4 and
hashes
`9123C9BA620496740D86AC020BBB2B98A65892E882CE7495A8644011CDF6ADCA`.
Forced reverse creation order places Pelica/Mifu/Lifeng/Zhuangfy/Wulfa in
slots 0..4 and hashes
`02A8E3883675F9D3A74292C374D41E8D5A8FEA2955677452584EEAA82F9FF709`.
The slot-4/layer-4096 owner therefore changes from Zhuangfy to Wulfa while the
fully framed images differ at only 70/8,294,400 pixels, 151 RGB channels,
absolute delta 281, and maximum channel delta 6. This GPU-closes the first
4x2 row transition and second-row renderer transport for five exact actors.
That milestone alone did not claim later slots, game ECS caster content, or
retail render-graph allocation/lifetime.

Focused installed-VFS/AssetMap recovery now also adds Endminm, Endminf, Chen,
and Wolfgd. The source graph selected their exact postmodel and Animator
identities; installed AssetMap plus focused postmodel/mesh exports remain the
authoritative helper-sphere and proxy scene-shadow evidence. Their priority-100 helpers preserve
self-shadow, punctual-shadow, and sphere-bounds admission, with exact sphere
counts 30, 31, 50, and 26. Their proxy/active counts are 9/8, 9/8, 7/7, and
12/12. The complete nine-profile contract therefore contains 78 exact LOD1
meshes with active counts `11/5/7/7/7/8/8/7/12`.

The first nine-actor run failed closed on two Wolfgd renderers sharing the
visible name `S_actor_wolfgd_cloth_05_lod0`. This proved global name lookup was
not source-exact. The evidence builder now joins renderer GameObjects through
their Transform hierarchy and serializes an exact relative
`sourceRendererPath`; runtime follows that path before validating the renderer
name. Wolfgd cloth-05 resolves to
`Mesh_all/lod0/S_actor_wolfgd_cloth_05_lod0`. The resulting 78-entry contract
hashes
`D47A653D3CBEF0BAF46DAC3A0FB009672848E72680C8F8099694D666CF321498`.

Fresh D3D12 execution reaches the first third-row slot:
`count=9`, `grid=4x3`, `atlas=4096x3072`, 1024 tiles, D16. Normal creation
places Endminf/Mifu/Endminm/Pelica/Lifeng/Chen/Wulfa/Wolfgd/Zhuangfy in slots
0..8 and hashes
`E06199658F3F784B15A3F89C010184D4DC71170A7D2B14DF3AC6D80720803280`.
Forced reverse creation places
Wolfgd/Chen/Endminf/Endminm/Pelica/Mifu/Lifeng/Zhuangfy/Wulfa and hashes
`109F432F5A02B41FC3D76C7688EA24F0CDA00416603E4791D3A1AC5142653B8E`.
The slot-8/layer-65536 owner therefore changes from Zhuangfy to Wulfa, while
the fully framed captures differ at only 122/8,294,400 pixels, 251 RGB
channels, absolute delta 376, and maximum channel delta 8. The exact
4-column third-row transition and renderer transport through slot 8 are
GPU-closed.

The final installed-data extensions add Aglina, Aurora, Antal, Ardelia, and
Bounda. Their helper sphere counts are 30, 21, 17, 39, and 33; proxy/active
counts are 6/6, 9/9, 5/5, 10/10, and 12/12. Dapan was first considered for
the final proxy-diagnostic slot, but its exact playable-postmodel export
contains 45 skinned renderers and zero `Shadow_Proxy/SP_Desktop` entries, so it
remains an explicit exclusion from that diagnostic only. This is not evidence
that Dapan lacks ordinary realtime character-shadow casters. The historical
maximum proxy contract contains 120 exact LOD1 meshes across 14 actors.

This wider evidence invalidated two old one-submesh assumptions. Aurora's fur
proxy points by exact Mesh PathID to `S_actor_aurora_fur_01_lod1_8`, a
two-submesh mesh, rather than the similarly named plain `_lod1` record.
Retail renderer material arrays may also exceed mesh submesh count: Wolfgd
furcard has 2/1, Aglina vfxpart 3/1, Ardelia fur 2/1, and Bounda eyeshadow
2/1. Unity repeats the final submesh for extra material passes. The runtime
provider now preserves all 126 exact material entries instead of silently
keeping only index zero; Aurora's paired fur materials independently retain
cull modes 0 and 2. Maximum contract SHA-256 is
`524ABECA34933BDA382517F338D859E28748538B9EC93A7AFB70AA55C24BE36E`.

Count 13 first executes the 4x4 transition at 4096x4096 D16 and slot
12/layer 1,048,576. Its normal/reverse images hash
`02E2939EF8D3C18FD737736E808E12B93BD756C4ED9FDA39B35B253D7D045445`
and
`42B069EDCFA7A896F418B8BC79F3820058D1BA0CE1EC13DBBB8372A60B79F41F`;
27 pixels, 58 channels, absolute delta 97, maximum 6 differ.

Count 14 then executes the complete binary-proven live range. Normal creation
assigns Endminf/Mifu/Aglina/Endminm/Pelica/Antal/Lifeng/Chen/Wulfa/Aurora/
Bounda/Wolfgd/Ardelia/Zhuangfy to slots 0..13 and hashes
`0CD7C5CB965AFE9E0839B8538A81AD883195530650586E6371EDC6404942DF1C`.
Reverse creation assigns Bounda/Ardelia/Antal/Aurora/Aglina/Wolfgd/Chen/
Endminf/Endminm/Pelica/Mifu/Lifeng/Zhuangfy/Wulfa and hashes
`0BFC9F3F68F2FAD4CCACF25FAC330246E8BBBEE0552D9815B86D7FFEC33EA5E4`.
The slot-13/layer-2,097,152 owner changes from Zhuangfy to Wulfa while only
45/8,294,400 pixels, 98 RGB channels, absolute delta 169, and maximum channel
delta 5 differ. Admission, priority/instance-ID ordering, every row
transition, rectangle/matrix selection, and rendering-layer transport are
therefore GPU-closed across all 14 assignable slots. At this capture milestone
the managed caster membership, generic ECS caster set, same-frame physical
render-graph allocation/reuse, and full-client publication timing remained
open; the later helper audit replaces the proxy membership interpretation with
the exact 151-renderer regular realtime-caster roster above.

The current installed binary now closes that logical-to-physical lifetime
boundary. `ShadowMapPassConstructor.ConstructPass` is the sole direct caller
of `HGShadowManager.RenderCharacterShadows` and carries the character result
as active byte `+0x14` plus `TextureHandle +0x18` in the shared 60-byte
`ShadowResult`. `HGShadowManager.ReadShadowResult` validates that handle and
registers it through `HGRenderGraphBuilder.ReadTexture` in Deferred Lighting,
Distortion, Fake Planar Reflection, Forward Opaque, Forward, Transparent After
DOF, Transparent, and both One Pass Deferred phases. The graph compiler calls
`GetFirstValidWriteIndex`, `GetLatestValidReadIndex`, and
`GetLatestValidWriteIndex`, then attaches physical creation at the first
write and release after `max(latest valid read, latest valid write)`.
Pre-pass execution calls `CreatePooledResource`; post-pass execution calls
`ReleasePooledResource`. `TextureResource` hashes the exact descriptor,
obtains or creates the pooled texture, records its frame allocation, and
returns it to the pool at release.

The default-off lab keeps a conservative camera-wide lifetime, neutralizes
all character-shadow texture/parameter globals, and only then returns the
temporary atlas to Unity's pool. Fresh Unity `2022.3.62f3` D3D12 validation
executes the exact 151-renderer managed roster, excludes all five original
realtime-false rows, and hashes
`1ECCD771D862D1B3827FE6554697CF786A2D1E1AFE4B1CB4E4FC916E5F04713B`.
Against the retained proxy diagnostic it changes 25,913/8,294,400 pixels
(0.312416%), 60,630 RGB channels, absolute RGB delta 280,846, and maximum
channel delta 79, bounded to `[124,871]-[3695,1290]`. The expanded exact-
binary/source/capture verifier passes 1,499 checks. This proves when the texture
becomes pool-eligible; it does not observe or claim a particular later GPU
allocation address alias. Remaining gaps are the live ECS entity census and
complete client frame/VFX consumption, not the native
query identity/filter, managed caster membership, atlas assignment, or release
boundary. The pinned Zhuangfy VFX set adds no atlas caster: its sole
character-index-1 row has no original `ShadowCaster` material pass. No claim is
made for unpinned VFX sets. Reproducible evidence is under
`scratch/reverse_engineering/character_shadow_physical_lifetime_20260724/`,
`scratch/reverse_engineering/character_shadow_ecs_caster_20260724/`, and
`scratch/character_recovery/character_shadow_original_realtime_caster_recovery_20260724/`.

The current binary also closes receiver strength.
`SetupCharacterShadowReceiverConstants` writes
`(Light.shadowStrength, Light.shadows == Soft ? 1 : 0, characterCount, 0)`.
The selected retail hair fragment applies X directly as the dedicated
character-shadow lerp. The character volume's `selfShadowStrength` is not a
second multiplier, and the ordinary Unity `LightShadows.None` enum does not
force this strength to one. The generated KeyLight has that enum plus authored
strength 0.9; correcting the exact diagnostic produces Wulfa
`E3B35784...` and Zhuangfy `646D39D2...`. Against the prior strength-one
captures, 1,481,349 Wulfa RGB pixels (17.8596%, MAE 3.90869/255) and 1,442,122
Zhuangfy pixels (17.3867%, MAE 3.31137/255) change. Both D3D12 logs retain
successful 1024 matrices and exact 11/12 and 5/8 proxy counts. The focused
installed-binary, installed-helper, source, receiver, canonical-default and
capture verifier passed 1,390 checks at that milestone under
`scratch/character_recovery/character_shadow_producer_matrix_recovery_20260723/`.
This eliminates continued producer-bias or receiver-strength tuning as an
evidence-backed route for the hard local attenuation.

### Lighting and shadows

| Area | Recovered | Runtime status and gap |
| --- | --- | --- |
| Main character light | Exact CharacterVolume packing, CharInfo direct-intensity carrier, direction/color/multiplier inputs, and the selected descriptor RGB/W scheduling split (unscaled RGB for CP12.y ambient lightBlend; W-scaled RGB only for direct luma/chroma) | The corrected source path is binary- and GPU-validated but remains default-off with the larger material-energy route; full retail global update and scene coupling remain partial. |
| Overview operator lights | All 266 records, 133 followers, native distance-ascending shortlist followed by managed priority-descending/distance-ascending punctual ordering, 32-pixel XY plus linear-Z membership representation, selected old-CharacterNPR Default/Fog/Rim responses; native tier, maximum/minimum-distance, Point/Spot frustum, authored OBB, occlusion-result and 256-cap gates are binary-pinned | Active bounded roster path for 259 records. It does not execute the scheduled generic projected-screen/scene-layer producer, full interleaved scene/character list, native equal-distance/equal-priority ties, fallback culler, live occlusion/cache history or unrelated scene transforms. Seven positive-linear-length source lights remain unsupported. |
| Punctual soft shadow | Exact Wulfa Spot row and Zhuangfy Point row, D16 atlas layouts at 512/1024, matrices, bias, casters, optimized comparison receiver | Two default-off exact diagnostic rows out of 32 shadowed source rows across 23 actors. Full live cache-slot population and the other 30 rows are not recovered. |
| Dedicated character shadow | Fourteen authored sphere unions; exact CameraVirtualLight matrix/Ortho/depth/bias chain, 1024 D16 tile, 16-gather/64-tap receiver and direct `Light.shadowStrength`; helper admission/order, 14 assignable slots versus the 15-entry ABI, 4-column rectangles, rendering-layer carrier, per-index Unity/ECS schedule, and graph lifetime. `FindRenderers`, the LOD cutoff 2, `UpdateShadowRenderingLayer`, and the fork realtime-caster bit source-close 151 ordinary current LOD0 casters with five exact exclusions. Modes 3/4 are separately assigned layer 2/index 15; the 120 exact `Shadow_Proxy/SP_Desktop` LOD1 meshes and 126 material passes remain scene-shadow evidence and historical scheduling diagnostics, not atlas membership. The Unity list uses `ShadowCaster` plus `CommonOpaque`; the exact ECS query receives `slot+1`, excludes `ShadowOnly` and `HGUIParticleComponent`, requires `HGRendererComponent`, selects `ShadowCaster`, and compares all reachable entity-family character indices. The sole character-index-1 row in the pinned Zhuangfy particle set has no original `ShadowCaster` shader pass and adds no atlas depth. D3D12 executes all 14 slots with the source-closed managed roster; the accepted image hashes `1ECCD771...`, and the 1,499-check verifier passes. | Fourteen recovered sphere/realtime-caster profiles out of 30. The live ECS entity census, remaining actor profiles, complete client frame/VFX consumption, and any later physical GPU allocation alias remain open. No extra VFX caster is inferred outside the pinned negative Zhuangfy result. Dapan's lack of desktop proxies excludes it only from the historical proxy diagnostic, not from the ordinary realtime-caster class. Hard local attenuation remains diagnostic rather than a scalar-fitting target. |
| CharInfo screen shadow | Source-closed retail full-camera `R8G8_UNorm` descriptor, bilinear/clamp sampling, no-clear two-fullscreen-draw ownership, `_ScreenSpaceShadowMask` global binding, frame order, R/G semantics, Eye R-only consumer boundary, exact three-target R8 quarter-resolution directional/blur chain, full scene-resolve composition, and full-resolution R8G8 `RayTracingV2` contact producer. The lab now ports the exact native 64-thread four-side/split/compact contact dispatch, `_InvProjMatrix` reconstruction, current installed bit-4 stencil variant, source-owned first-contact phase 1, CharInfo constants, and G*4 light-direction displacement into both recovered CSM receivers. Installed CharInfo data proves cloud neutral through exact constants plus the white texture owner, selects ASM disabled through the exact ConstructPass predicate/skip/global route, and requests active CSM through the original 11,440-byte `ShadowData` producer/upload ABI. Binary defaults close a three-cascade 2048x2048 D16 atlas with 1024 tiles and active boundaries `0/.15/.375/1`. The retail callback draws Unity, general ECS, grass ECS, then tree ECS lists; the lab now constructs the exact applicable Unity `ShadowCaster` list with `CommonOpaque`, raw per-object bits `0x7800`, and layer mask `-1`, plus a documented stock-Unity all-queue ABI bridge. Its stable lab-prefixed Wulfa/Zhuangfy caster content feeds the binary-exact `ceil(cameraDimension*renderingScale*0.25)` raw R8 receiver, exact 7x1/1x7 blur, and full-resolution attachment with installed endpoint trust, 4x4 phase rotation, and 16 Gather/64 comparisons. At 480x270 Wulfa has 783 zero, 21,189 intermediate, and 107,628 one scene-R texels; Zhuangfy has 740, 23,642, and 105,218. Unity D3D12 proves the public stencil aspect exposes the installed kernel's bit-4 data in `.y`; at 640x720 source-owned phase 1, contact R is 255 throughout while G is nonzero on 2,195 Wulfa and 132,133 Zhuangfy pixels. Unity 2021.3.34f1 and 2022.3.62f3 D3D12 probes independently close comparison behavior for the dedicated default ASM depth resource; retail uses UnityPlayer 2021.3.34f5. | Original data still does not prove every live scene-R contribution. The attachment and contact producer remain separately default-off/content-invalid and leave Eye R disabled. Game-only general ECS/grass/tree caster ownership/content, the fork-only zero/default queue semantics, canonical CSM/ShadowData/low-resolution/contact publication, complete scene-R ownership, multi-actor QueryID, physical pool reuse, and final parity prevent promotion. Future patches or gameplay-time mutation could change the current installed terrain fake-shadow value. Character G remains available only in the older one-actor PreG/atlas diagnostic. |
| `ShadowPlane` | Material, multiplicative blend, bit-32 exclusion, circle fade, 15-slot atlas ABI, VisibilitySH capsule topology, and an isolated live-pose Wulfa/Zhuang VisibilitySH replay are recovered | Not runtime-ready. The default-off canonical PreG owner writes authored stencil Ref 36 to the physical camera target, but full bit-32 readback/consumer validation, the atlas scheduler, retail VisibilitySH target captures, exact cull survivors/order, and canonical consumer integration remain missing. Canonical VisibilitySH therefore stays at its neutral zero-occlusion endpoint. |

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

The current installed binaries now close the missing canonical owner around
that isolated producer. In hash-pinned `GameAssembly.dll`
(`0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce`)
and `global-metadata.dat`
(`90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e`),
`HGRenderPathDeferred.OnPreRendering` prepares the CPU character PreG list when
`preZ.enabledForCPUCommands` is true with opaque mask/value `0x500/0x100` and
LightMode `0x1000` (`DepthCharacterOnly`). `GBufferPassConstructor` separately
builds the opaque SRP list from `HGShaderPassNames.s_DepthCharacterOnlyName`.
`DefaultDeferred.RenderScene` calls DepthPrepass before GBuffer; both pass
inputs use the same `sceneDepth` handle with write access. The GBuffer lambda
draws character ECS, outline ECS, and character SRP PreG lists before ordinary
deferred opaque work. The later opaque character list uses LightMode `0x80`
(`ForwardCharacterOnly`). The three constructor/list-preparation dispatch
points are IFix-covered (`0xc12`, `0xc75`, `0xdf6`), so the mapped native bodies
do not prove a live replacement table or future patch state.

The lab implements that minimum owner as a default-off, fail-closed path. It
binds two exact `A2B10G10R10_UNormPack32` PreG colors with the canonical
stencil-bearing Forward depth target, submits safe generic depth followed by
opaque recovered Cloth/Skin/Eye/Hair PreG draws, restores the camera target,
executes the command, and only then activates each preserved source `_ZTest`.
Unity `2022.3.62f3` D3D12 verification passed on Last Rite cloth 03: queue 2000,
`ZWrite=1`, compatibility `LEqual(4)` before the owner and source `Equal(3)`
after it. The combined packed validation used D32S8, produced 12 character
draws and 244,063 character/stencil pixels, and reported zero selector, normal,
family, stencil, or depth mismatches. The strict evidence/static verifier is
`unity_endfield_graph_shader_lab/tools/verify_character_preg_depth_owner.py`;
the result contract is
`unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/character_preg_depth_owner_contract.json`.
This closes the selected lab attachment/order prerequisite, not retail ECS/
GPU-driven ordering, live preZ/IFix state, all opaque families or full GBuffer
consumer parity.

The current installed screen-shadow owner is now closed at the attachment and
Eye-consumer boundary. `HG.Rendering.Runtime.ScreenSpaceShadowMaskPassConstructor`
(`Construct` VA `0x189b52cac`, normal resolve VA `0x189b53608`) creates a
full-camera `R8G8_UNorm` bilinear/clamp, non-mipped, non-MSAA, non-history
texture, attaches scene depth read-only, performs two full-screen draws without
a clear, and publishes it as `_ScreenSpaceShadowMask`. Pass 0 writes the scene/
directional attenuation to R and neutral G; pass 1 rewrites R and writes
character attenuation to G. Neutral is `1`, and every selected Eye pass-0
D3D11 variant integer-loads `.x`, so Eye consumes R only. In the default
deferred schedule this owner runs after GBuffer, GTAO, contact and capsule
shadow work, and before deferred lighting and ForwardOpaque. RenderGraph creates
and releases the logical texture in-frame; it is neither imported nor preserved
and therefore has no cross-frame history, while exact physical-pool reuse after
the writer remains an open aliasing boundary. The pinned installed hashes,
method VAs/IFix IDs, shader payloads and bindings are recorded in
`unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters/screen_shadow_r_contract.json`
and checked by `unity_endfield_graph_shader_lab/tools/verify_screen_shadow_r_recovery.py`.
The lab attachment bridge deliberately remains default-off and reports content
invalid. Its original RG8-neutral plumbing stage has since been replaced by the
CharInfo-specialized directional scene-R implementation described below, but
that implementation still cannot enable the Eye R keyword until the remaining
retail producer/ownership boundaries are recovered. Exact-editor Unity
`2022.3.62f3` (`96770f904ca7`) D3D12 batch import/
compile exits zero with no compile, shader, or exception failures; the strict
screen-shadow, Eye, and canonical PreG owner checks pass, and the repaired
30-character resident lineup independently remains complete. This is an import/
compile result only, not a claim that the default-off scene-R attachment
reproduces retail shadow content. The same all-character log contains two intermediate
Chen prefab imports with missing `S_wpn_misc_0002/0003` nested-model GUIDs while
cleanup deletes the old `StaticProps` before the old prefab. They are transient:
both exact AnimeStudio OBJ sources are recopied byte-for-byte, their current
GUIDs resolve from the final Chen prefab, its later import succeeds, and the
build exits zero. They do not describe a persistent missing retail dependency.

The current installed bytecode and native route now close substantially more of
that content chain. `HGLowResDirectionalShadowPass.Render` (VA `0x189b4733c`,
installed IFix ID `0x087e`) allocates exactly three quarter-scale `R8_UNorm`
bilinear/clamp, non-mipped targets. It draws `HGRP/LowResDirectionalShadow`
pass 0, then `HGRP/PostProcessing/ShadowBlur` passes 1 and 2, and publishes the
vertical result as `_LowResDirectionalShadow`. The first shader gathers a 4x4
full-resolution depth block, emits an exact `0.5` edge sentinel when an axial
linear-depth difference exceeds `0.1000000014901161`, otherwise chooses/dithers
one of four CSM cascades and performs 16 gathers/64 comparisons. Values outside
the resolve interval `[0.001, 0.99]` are accepted directly at full resolution;
interior values trigger the same expensive CSM refinement. The selected blur is
an exact clamped seven-tap horizontal mean followed by a seven-tap vertical mean
(weight `0.1428571492433548`); its generic 3x3 pass is not used by this route.
The target size is now exact too. The render body multiplies
`cameraDimension * renderingScale` by the float `0.25` stored at VA
`0x18b959510`, then calls helper VA `0x1832dbd50`. That helper converts to
double, calls the installed positive-domain `ceil` implementation at
`0x1801d87b0`, and converts the result to integer. Width and height therefore
use `ceil(cameraDimension * renderingScale * 0.25)` independently; a 480x270
probe allocates 120x68, not 120x67 or 120x68 by an assumed rounding rule.

`ContactShadowCS` is also recovered from the installed VFS rather than fitted.
The active native path selects `RayTracingV2`, dispatches 64x1x1 groups over a
full scaled-camera `R8G8_UNorm` random-write target, binds depth plus stencil,
and publishes `_ContactShadow`; the unsupported path binds `Texture2D.redTexture`.
The compute kernel traces edge-aware 64-ray segments with `groupshared[128]`,
inverse-projection reconstruction and an eight-frame jitter phase. R/B/A carry
contact attenuation. G carries a quantized world-ray displacement divided by
four; the directional shaders use `G * 4` to move the CSM sample position
opposite the directional light only when R is nearly one. The normal terrain
stencil mask is `0x4`; `_DISABLE_TERRAIN_CONTACT_SHADOW` expands it to `0x84`.
Despite its name, the installed `InitWhite` D3D11 kernel writes zero. No matching
screen-shadow, low-resolution, contact, CSM, ASM or cloud owner is present in
the installed persistent IFix table, so the pinned native bodies are the current
static route within that persistent-patch boundary.

The contact pass is now closed through its native dispatch owner rather than
only at bytecode level. `ContactShadowPassConstructor.
PrepareContactShadowPassDataV2` is method 287064 at VA `0x189b90ee4` (file
offset `0x9b8f4e4`). It rounds projected center coordinates with `addss 0.5`
plus `cvttss2si`, forms boundaries `(-roundedX, H-roundedY, W-roundedX,
-roundedY)`, applies the exact four-side base/end formulas, optionally splits
the wedge into a second record, removes records with nonpositive Y/Z counts,
then multiplies the X/Y workgroup offsets by 64. Each record dispatches
`(64,countY,countZ)`. The light vector is the negated directional-light forward
projected by GPU view-projection with `w=0`; clip W is clamped to
`+/-0.000128`. The compute constant buffer is the exact 80-byte
`_DataParams[4]` plus `_WorkgroupOffset` layout. The installed kernel reads
`_InvProjMatrix`, not inverse view-projection; the lab supplies explicit GPU
inverse-projection columns to avoid public-Unity matrix-packing ambiguity.

`EndfieldRecoveredContactShadowProducer` implements that route behind
`ENDFIELD_RECOVERED_CONTACT_SHADOW` /
`-endfield-recovered-contact-shadow`. It consumes the same recovered
`D32_SFloat_S8_UInt` PreG resource through Depth and Stencil aspects, writes a
full-camera bilinear/clamp `R8G8_UNorm` random-write target, and publishes only
lab-prefixed globals. Public Unity initially exposed no stencil SRV for the
combined target; the selector-scoped bridge now requests an `R8_UInt` stencil
view without changing the physical D32/S8 owner. A separately gated D3D12 probe
then proved that view carries no data in X but carries 82,908 nonzero/bit-4
pixels in Y, exactly matching the installed kernel's `.y & 4` load.

The temporal phase is now source-owned rather than an isolated lab convention.
Across all 176 registered `HGCamera` methods, the only direct accesses to
`cameraFrameCount` at `this+0x91c` are `Reset` (method 286643, VA
`0x184b4ed20`) writing zero, `Update` (method 286739, VA `0x183100120`)
incrementing it, `GetCameraFrameCount` (method 286646, VA `0x183df2ff0`)
reading it, and `UpdateShaderVariablesGlobalCB` reading it. A newly allocated
managed camera object is zero-initialized. `HGRenderPipeline.Render` calls
`TryCalculateFrameParameters`, which calls `HGCamera.Update`, before
`ExecuteRenderRequest` reaches default-deferred `RenderScene`,
`ContactShadowPassConstructor.ConstructPass`, and
`_InitContactShadowParams`. The first contact dispatch therefore observes
phase 1; reused cameras continue modulo eight. The lab now increments its
per-camera counter before filling `_DataParams[1].w`.

At 640x720 and source-owned first phase 1, Wulfa builds two dispatch records
with projected light `(296.869141,-1556.08459,-0.00200396776,-1)`. Contact R
is 255 for all pixels and G is nonzero on 2,195 pixels, with RG8 SHA-256
`FE44CBB538628277C1CA09D56FB0BA29B3DED4BE956CF5B112C0F62B76E33E5A`.
Zhuangfy also builds two records at
`(291.4168,-1444.96533,-0.00200396776,-1)` with neutral R, 132,133 nonzero-G
pixels, and RG8 SHA-256
`D69E53FE081E82DE061CFB930BEF2461A6C5E4B75A982D1B3F6088D832592846`.
The large change from the historical phase-zero diagnostics is expected
temporal-phase behavior. Neutral R is expected because the recovered character
PreG owner marks stencil bit 4 and the current installed normal kernel excludes
it; G still feeds the exact `G*4` displacement before both recovered CSM
projections. CPU replay shows complete 460,800-pixel coverage but 202,752
duplicate writes and heavy clamping at boundaries, so this native-shaped
overlapping dispatch is not claimed byte-deterministic. The earlier contact
on/off 3840x2160 presentation remains byte-identical per actor because the
attachment remains content-invalid and Eye R remains disabled. The phase-one
readbacks, source hashes, stencil ABI, and fail-closed A/B are pinned by
`screen_shadow_r_contract.json` and
`tools/verify_screen_shadow_r_recovery.py`.

The terrain variant is also closed for the current installed corpus.
`HGTerrainUtils.ShouldDisableContactShadow` (method 288876, VA
`0x183c94cb0`) reads
`HGTerrainV2.LayerTypeData._fakeShadowData._EnableFakeShadow`.
`TerrainLayerTypeData` is `0x110` bytes, its `TerrainFakeShadowData` member is
at `+0xf8`, and that `0x14`-byte struct stores the enable byte at `+0`.
`TerrainLayerTypeDataConvertFunc.ConvertFrom` zero-initializes the destination,
so an absent property is false. UnityPlayer's serialization path resolves the
exact property key `0x130A0004`: HGTerrain component index 19, property 10,
fake-shadow subproperty 4. The installed VFS scan covered all 25,506
`InitChunkData` files, all 25,506 `StreamingChunkData` files, and all 2,111
`DynamicStreaming` files. Init has no aligned fake-shadow record; static
Streaming has 35 structurally valid exact 20-byte records, all fully zero and
disabled; DynamicStreaming has two aligned key candidates but no structurally
valid 20-byte record. Current installed content therefore always selects the
normal bit-4 kernel, not the terrain-disabled `0x84` variant. Only future
patches or gameplay-time mutation outside the static installed corpus remain
an explicit boundary.

The installed Persistent `CharInfo_Env` now closes the cloud input rather than
leaving it as a generic missing producer. Both `cloudConfig.enable` and
`enableCloudShadow` are zero and the cloud-shadow texture is null.
`HGSkyRenderer.SetupShaderVariablesGlobalCloudShadow` (VA `0x189ce9404`)
writes `_CloudShadowParams0=(1,0,0,0)`, Params1 zero and Params2 one in this
branch. `HGRenderPipeline.UpdateGlobalConstants` (VA `0x189bc91c4`) owns the
texture global and binds `Texture2D.whiteTexture` to `_CloudShadowTex`. Cloud is
therefore exact neutral for this scene, with no screenshot-derived value.

CharInfo requests CSM enabled (`disableCsm=0`, intensity `1`, softness `0.01`)
and ASM disabled (`disableAsm=1`). The original CSM route is now closed at its
frame ABI: `HGShadowManager.ShouldRenderCSMShadowMap` (VA `0x189d24ed4`) gates
on a directional light, graphics CSM setting, manager enable, nonzero light
shadows, intensity at least `0.001`, volume enable, and non-Reflection camera.
`SetDirectionalLightShadowData` (VA `0x189d24344`) writes five matrices, four
split spheres, four bias rows, four atlas rows and texel size. `FrameSetup` (VA
`0x189d1fb50`) fills penumbra sizes and `_DirectionalShadowParams`/`2`, and
writes zero to the named `_CSMRhodesParams` row. These occupy offsets
`0x000..0x240` of the original 11,440-byte `ShadowData`; section 0 is uploaded
by `HGShadowConstantBufferUtils.SetGlobalConstantBuffer` (VA `0x189b4fca8`).
The true pass binds `_CSMShadowmapTex` plus `_CSMShadowRampTex`; CharInfo's null
ramp uses black.

The installed default topology and settings are now closed directly from the
current binary rather than inferred from the four-entry buffer capacity.
`HGSettingParameters..ctor` (VA `0x1836590a0`) sets D16, CSM enabled, 1024-pixel
tiles, 80-unit maximum distance, 60-unit fade-inner distance, three active
cascades, split capacity `.15/.375/.5/1`, no shadow-map cache, 256 occlusion
depth, stop-character cascade 2, near-plane offset 10, and hardware depth/normal
bias `1/1`. `FrameSetup` copies the setting at `+0x250` directly into manager
`+0x98`; its atlas branch therefore selects 2048x2048 for the default count of
three. The active boundaries are `0/.15/.375/1`; `.5` is used only by
four-cascade mode. `HGShadowManager..cctor` (VA `0x184723a70`) supplies scale
capacity `(1,1),(.5,1),(.5,.5),(.5,.5)`, so the default 2x2 atlas uses the first
three 1024 tiles and leaves the fourth unused.

`EndfieldRecoveredDirectionalCSMProducer` implements that topology behind
`ENDFIELD_RECOVERED_DIRECTIONAL_CSM` /
`-endfield-recovered-directional-csm`. It temporarily bridges the source-backed
directional light into Unity culling, restores the light immediately, computes
three cascades, renders a bilinear/clamp 2048x2048 D16 atlas, and publishes only
lab-prefixed globals. A D3D12 R32 inspection copy proves actual caster content:
Wulfa has 8,809 non-clear samples and stable SHA-256
`DBB9C3118B7001215C64F8FB3424F957483F2861FA11BB1A70650676928CB8CF`
across two runs; Zhuangfy has 14,198 and
`D9A035BA7B3262582B1F20CA75933E3B4880842C7BD8A789FA97D4D7AC4453F5`.
Enabled/default-off presented PNGs are byte-identical for each actor, proving
the diagnostic stays offscreen and does not claim `_CSMShadowmapTex`.

The caster draw route is now closed for the renderer class actually used by
the lab. `HGShadowManager+<>c.<.cctor>b__104_3` (method 285536, VA
`0x189d2572c`) draws four prebuilt lists per active cascade in exact order:
Unity, general ECS, grass ECS, then tree ECS. All four receive the same
`HGGraphicsFeatureSwitch.enabled` Boolean; the callback adds no separate
admission predicate. Before those calls it applies the cascade-scaled hardware
depth/normal bias, and afterwards it resets bias and disables scissor.
`RenderShadows` also constructs per-cascade `ShadowDrawingSettings` with the
exact split, `useRenderingLayerMaskTest=(cascade>=stopCharacterCascade)`,
`AllObjects`, and `cullNonRealtimeCasters=true`, but this callback consumes the
prebuilt list arrays rather than that stored settings array.

`CalculateDirectionalShadowParameters` creates the Unity list from current
camera culling results and camera. The pass is proven `ShadowCaster`, not
guessed: `HGShaderPassNames.s_ShadowCasterStr` is string-field index 25 at
static offset `0xc8`, and its class initializer is method 287011 at
`0x1846429f0`. The descriptor overwrites only sorting `0x3b`
(`CommonOpaque`) and retail per-object bits `0x7800`; constructor defaults
leave layer mask `-1` and the remaining queue/state/override/motion fields
zero/default. Stock Unity 2022.3.62f3 accepts the raw `0x7800` bits but treats
the zero queue range as queue-zero-only: an exact-bit probe produced an empty
D16 atlas. The lab therefore uses `RenderQueueRange.all` as the single explicit
ABI bridge. A second probe restored nontrivial content, while Wulfa and
Zhuangfy kept the prior CSM, low-resolution, full-resolution RG8, and presented
PNG hashes byte-identical. Since both actors are ordinary
`SkinnedMeshRenderer`s, this closes their retail Unity-list ownership. The
three HyperGryph ECS/grass/tree systems have no lab equivalent and remain
absent rather than approximated.

`EndfieldRecoveredLowResDirectionalShadowProducer` now consumes that exact
lab CSM plus the recovered PreGBuffer depth behind
`ENDFIELD_RECOVERED_LOW_RES_DIRECTIONAL_SHADOW` /
`-endfield-recovered-low-res-directional-shadow`. The selector automatically
requests those two dependencies and publishes only
`_EndfieldRecoveredLowResDirectionalShadow`. Its shader ports the original
four depth gathers, 0.1 edge sentinel, inverse-VP reconstruction,
split-sphere/dither selection, separate world-to-shadow and atlas vectors,
16 Poisson gathers / 64 reversed-Z comparisons, and signed cubic output
filter. Contact is deliberately black so R stays below the original
`0.9999899864` displacement threshold whenever the independent contact selector
is off. When separately enabled, the recovered full-camera RG8 producer is
bound instead and the exact `G*4` directional displacement branch runs. Thus
the established default-off baseline remains the source no-contact-offset
branch without blocking isolated validation of live contact input.

The first replay exposed and rejected a double GPU-projection conversion:
7,400 valid Wulfa receiver samples were at depth `0.477..0.484` while caster
depth stopped at `0.0462`, yielding only lit/edge output. The directional
culling API projection already matches Unity shadow drawing, so the retail
reversed-Z row flip must operate on that returned projection directly.
After correction, Wulfa receiver depth is
`0.0315325..0.0460869223`, maximum gathered caster depth is `0.04615854`,
and the R8 result contains 29 zero, 436 midpoint, 6,588 one, and 1,107
intermediate texels. Its SHA-256
`DB06D5BD84BDB9169EF1D2445E29223A0469CAEDDB05DE88A6037C751C52484F`
is stable across two runs. Zhuangfy reaches cascades 0 and 2 and produces 30
zero, 564 midpoint, 6,394 one, and 1,172 intermediate texels with SHA-256
`00253BA20B0CE933C8376A5A78C7C1BC974DB1D20DE088F7021A72C1D4D2D9C4`.
The underlying D16 atlas hashes remain unchanged, and enabled/default-off
presented PNGs remain byte-identical. This closes the raw directional receiver
in lab-prefixed resources.

The same owner now allocates the other two retail-shaped 120x68 R8 targets and
runs the installed blur order: seven clamped horizontal `Load` taps followed
by seven clamped vertical taps, each weighted
`0.1428571492433548`. Wulfa's blurred output spans byte 45..255 with 2,788
intermediate texels and stable SHA-256
`A56137FB3ED57426F4E4655748CC3313BE2FDE0AA7AC95E05D765E7F10854B3B`
across two runs. Zhuangfy spans byte 41..255 with 3,034 intermediate texels and
SHA-256
`98189531D6C69412C035F86358035ED6155F5D0370E64AACFDD9140AD7C3CB1D`.
Enabled/default-off presented PNGs remain byte-identical for both actors.
This closes the three-target raw/horizontal/vertical low-resolution chain in
lab-prefixed resources and the applicable retail Unity caster-list dispatch.
Game-only ECS/grass/tree caster content, canonical
`ShadowData`/atlas/low-resolution/contact publication, complete scene-R
ownership, and final scene-R parity remain open.

The ASM skip route is also no longer an unnamed global or callsite gap.
`ShadowMapPassConstructor.ConstructPass` (method 285646, VA `0x189b53bf8`)
calls `HGEnvironmentManager.GetInterpolatedPhase` at method offset `+1125`,
compares phase byte `+0xd7c` with zero, and branches to the skip block when it
is nonzero. `HGEnvironmentPhase.shadowConfig` begins at `+0xd18`;
`HGShadowConfig.disableAsm` is byte `+0x64`; their exact join is `+0xd7c`.
The installed `CharInfo_Env` value is one. A complete installed-image rel32
xref scan finds one `SetCachedData` call at `0x189b54be4` and one
`SkipRenderASM` call at `0x189b54c38`, both owned by this constructor.

`HGASMManager.SkipRenderASM` (VA `0x189d19e98`) schedules its disabled lambda,
which binds `HGRenderGraphDefaultResources.defaultShadowTexture` at handle
offset `+0x100` to `_ASMShadowmapTex`. The default-resources constructor
(method 283538, VA `0x182edc6e0`) creates object `+0x28` as a dedicated 1x1,
one-slice, depth32 comparison RTHandle: numeric color format 4, Point/Repeat,
Tex2D, no mip/random write, MSAA1, and `isShadowMap=true`.
`InitializeForRendering` imports that exact field and stores its handle at
`+0x100`. The native allocation path reaches `RenderTexture.Create` without
an explicit managed-side clear.

Two controlled default-resource probes allocate that exact shape eight times
and bind the depth subresource explicitly. Unity `2021.3.34f1` and
`2022.3.62f3` D3D12 both use reversed Z and produce the same result: every
untouched allocation has stored depth zero, matching Unity's
API clear-to-depth-one control. Comparison sampling returns one for reference
0.5 and 1.0 and zero only at the strict reference-zero endpoint. The recovered
scene fragment rejects projected reference Z at or outside `[0,1]` before
sampling, so every valid positive ASM reference sees neutral attenuation.
The installed retail `UnityPlayer.dll` is `2021.3.34f5`, SHA-256
`B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`;
therefore allocation shape, import, and branch selection are installed-game
binary evidence. The 2021 probe is from the same `2021.3.34` LTS generation
but editor patch `f1` rather than retail player patch `f5`; both initialized
comparison observations remain equivalent-shape lab D3D12 evidence rather
than live retail-process instrumentation. Together they are sufficient to
close ASM for the default-off fail-closed attachment, not to claim a retail
process capture.

The full-resolution scene resolve is now both semantically closed and attached
behind
`ENDFIELD_RECOVERED_SCREEN_SHADOW_R_ATTACHMENT_DIAGNOSTIC`. It reconstructs
world position from the recovered PreG depth, accepts low-resolution endpoints
below `0.0010000000474975` or above `0.9900000095367432`, and refines interior
values with the installed 4x4 screen phase table, 16 Poisson gathers, 64
reversed-Z comparisons, positive-depth accumulator, and signed cubic filter.
It applies the exact 80/60-unit CSM distance fade. The installed CharInfo branch
is specialized without fitted values: contact is black and takes the
no-displacement branch by default, while its independent gate supplies the
recovered RG8 displacement; disabled ASM is comparison-neutral one, cloud is
one, Rhodes and simulated fallback blend are zero, and directional strength is
one.
Both retail-shaped fullscreen passes recompute scene R while keeping G at one;
the RG8 target is still no-clear and published only through the existing
default-off attachment.

The exact-current-source D3D12 replay is stable. At 480x270, Wulfa produces R
counts `783/21189/107628` for zero/intermediate/one and RG8 SHA-256
`6403D764EDBD941E5999DD8440A31F835BCC3375AD7393B2B006C024D02F23ED`
across two runs. Zhuangfy produces `740/23642/105218` and
`7F33E93F1A0E7D8713B0253E58F052FF2B011C6AE9044A247F519569EB1DA5C5`.
Both have zero non-neutral G texels. Enabled and default-off presented PNGs are
byte-identical per actor because `contentValid` remains false and the Eye
consumer keyword remains disabled. This closes the full-resolution scene-R
attachment as a default-off diagnostic. It does not manufacture exact native
game-only ECS/grass/tree caster content, the fork's zero/default queue-range
behavior, canonical `ShadowData`/CSM/low-resolution/contact publication,
multi-character QueryID ownership, physical pool reuse, or final retail
scene-R parity. The updated pinned contract and verifier enforce that
recovered/open boundary.

A proposed shortcut through `IsScreenSpaceShadowMaskEnabled` does not close the
neutrality gap. Current VA `0x183e02240` receives the constructor Boolean read
from instance offset `+0x40`, preserves it unless an external graphics-device
predicate rejects the device, and can only force the request off. It neither
uploads directional constants nor selects a neutral R. The suggested static
address `0x18e25cf98` is read by the normal resolve body as shader-ID/static-class
state and is not read by this predicate. No installed-data evidence obtained in
this pass proves CharInfo values for `_DirectionalShadowParams2.x/.w` or
`_DirectionalShadowParams.x`; neutral R therefore remains rejected for promotion.

The ordinary overlay path is no longer part of that attachment gap. Current
binary and material evidence proves it reads the existing scene depth/stencil
inside the one mixed transparent list; the active source overlays do not run
their `ForwardOnly` predepth member. The remaining shared-attachment work here
is the complete opaque PreG/GBuffer scene-R input production path,
multi-character selector ownership, physical pool reuse, and variant coverage.

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

An independent current-retail audit explicitly rejects a broad corrective
grade: CharInfo serializes post-exposure 0 EV, contrast 0, a white color
filter, hue 0, Manual exposure at EV0/multiplier 1, and inactive HGSharpen.
The non-neutral authored controls must remain: saturation +8, shadow-grade
weight `-0.10526314`, Tonemapping mode 5/`ACES_modified`, HQ bloom
`0.75/0.45/0.8`, vignette `0.3/0.41/0.94`, the recovered environment, and
per-actor light overrides. The source-closed verifier is
`scratch/reverse_engineering/retail_render_pipeline/verify_retail_render_pipeline.py`;
its report SHA-256 is
`11498ACC387DCB0312A0ED93807ADAB38A9951446847EC971F1E1D35676C3588`.

The `ACES_modified` LUT path is now source-closed through the executable
program and its default CharInfo inputs, and the shipped D3D11 program has a
deterministic complete RGBAHalf replay. A live retail render-target comparison
remains open.
AnimeStudio copied the original D3D11 programs directly from the serialized
shader payload without recompilation. The exact vertex program is 496-byte
DXBC, SHA-256
`51C3C79975DAEA42913CBAD2AF387DEEBEDD45A823768EEF8C1FA816F6591C37`;
the exact fragment program is 8,248-byte DXBC, SHA-256
`33EF065D876BE815D5E4121D9C000C10C886536623CE86AD22C5CD2EEB8F448D`.
They are the `TONEMAPPING_ACES_MODIFIED` variant of
`HGRP/PostProcessing/LutBuilder2D`, PathID `0x042EEA518489340B`.
A direct Ruri decompile of that recovered fragment pins `b0` as an 18-float4
constant buffer, `s0` as the LinearClamp sampler, and `t0..t7` as master,
red, green, blue, hue-vs-hue, hue-vs-saturation,
saturation-vs-saturation, and luminance-vs-saturation curve inputs. Every
curve read is red-channel `SampleLevel(..., lod=0)`; the exact master/RGB
`1/256` coordinate offsets and the secondary-curve hue/saturation/luminance
coordinates are verifier-guarded.

The default procedural curve payload is also exact from the current retail
`UnityPlayer.dll` (`2021.3.34f5`, SHA-256
`B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`).
Its internal-call table resolves `AnimationCurve.Evaluate` to VA
`0x1800C6A20`, which reaches the scalar evaluator at `0x1805727C0`; the cached
fast path is the exact float32 Horner chain
`(((c3*dt+c2)*dt+c1)*dt+c0)`. The cubic cache builder at `0x180571240`
reduces the recovered identity keys to exact float32 coefficients
`(0,0,1,0)`. At the native `float32(i)*float32(1/128)` grid, the first four
R16_SFloat textures are therefore exactly `half(i/128)`, SHA-256
`FEDC374D0C803DC2C9B66E280EC4E3C46352EEA632EA3CA9A0FAAA3EE34F54FF`
per 256-byte texture. Empty secondary curves return their stored `0.5`, so
the other four are exact half `0x3800`, SHA-256
`0C29E1AB67689311FF640423CE9FBF86312E17264A1F7DC097B098AA44F18E09`
per texture. Concatenated `t0..t7` payload SHA-256 is
`C8E56A35624B9689C8D7E44B90E0B8603DECD5B546F4ACF72CF5D3153878A429`.

The source/input verifier is
`scratch/reverse_engineering/retail_render_pipeline/verify_aces_modified_lut_recovery.py`;
its contract is
`scratch/reverse_engineering/retail_render_pipeline/aces_modified_lut_contract.json`
with status `source_closed_program_inputs_exact_pixel_output_open` and
SHA-256
`2433D885462725FE78411E376F595A168E666AEF693E82F2CD5075CE38D1B968`.

The raw-DXBC half of that boundary is now closed by the scratch-only hardware
D3D11 harness under
`scratch/reverse_engineering/retail_render_pipeline/d3d11_lut_harness/`.
The original native call chain records the LUT as color attachment 0, invokes
`CoreUtils.DrawFullScreen` with pass 0 and no property block, then records
`CommandBuffer.DrawProcedural(Triangles, vertexCount=3, instanceCount=1)`.
The serialized pass fixes `ZTest Off`, `ZWrite Off`, `Cull Off`, default Blend
Off, and GPU program 1223. The harness executes the exact recovered 496-byte
VS and 8,248-byte PS with the exact `b0` and `t0..t7` payloads into a
1024x32 `R16G16B16A16_FLOAT` target. Two processes with three differently
pre-cleared draws each produced the same 262,144-byte readback: SHA-256
`8B1ED1A0D3E08404D8E2070B78C68BABBB2FA0C464E061818B4F28A933EBC94C`.
All 32,768 alpha values are exact half `1.0`, all channels are finite, and the
payload contains 27,669 unique RGBAHalf texels. The fail-closed verifier is
`run_and_verify.py`; the evidence report is
`aces_modified_lut_d3d11_replay_report.json`, SHA-256
`02FB93672D375AEF59EE120A3774DB770E5931FE4E81CA3271FFFB1016809D5C`.

This result is a deterministic replay of a shipped D3D11 subprogram, not a
retail-captured pixel-equivalence claim. Remaining LUT boundaries are a live
retail 1024x32 target readback, a live command-stream/backend capture, and GPU/
driver equivalence. The static HGRP generic pass types expose
`ConfigureViewportSize` for native mode and `SetupRenderTargets` for regular
mode, so the replay uses the sole attachment's full `0,0,1024,32` extent and
disabled scissor; their inflated runtime bodies have no unique non-generic
pointer in the current static mapper, so those values are source-derived rather
than live-captured. Sample count 1 is likewise the recovered non-MSAA Tex2D LUT
target assumption. The replay covers the exact default CharInfo volume and
curves, not arbitrary runtime volume blending or user overrides. The maintained
Unity LUT shader remains a source-proven subset; a local HLSL recompile is not
evidence of byte-identical intermediate rounding. The remaining broader post
boundary is live HGRP presentation, not a missing global exposure/darkening
control.

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
variants per serialized subshader, and native route topology are known. The
current installed build has four serialized copies of that 14-pass/640-variant
family. Its current metadata/GameAssembly remap closes all seven native draw
targets at method indexes `287098..288237` under CodeRegistration
`0x18b9217d0`; the prior addresses were from an older installed build and are
retired. The exact unpatched initializer reads the nine consecutive
`HGGraphicsFeatureManager` deferred switches into the nine render booleans and,
when `isOnePassDeferred` is false, forces split-stage and tile drawing off.
The current render lambda passes `false`. The current binary's feature defaults
therefore resolve to DefaultLit/Foliage/Subsurface plus Directional/Dynamic/
Indirect enabled, split/per-light/tile disabled, with the general deferred
switch enabled. The resulting installed native route draws resolver
passes 0/1/2 (the three Full Lighting shading models), then WriteAlpha; it does
not draw the split, tiled, or per-light routes. The base `StreamingAssets`
`IFixPatchOut` block is empty, but the active `Persistent` overlay is not: block
version `22764515` contains one encrypted/decrypted 82,021-byte
`Gameplay.Beyond.patch.bytes` file (SHA-256 `73713408...5d27bc21`). Its exact
signature table has 30 targets, none in `HG.Rendering.Runtime`, none matching
`PrepareRenderPipelineSettings`/the setting-parameter accessors, and none
matching `DeferredLightingPass`, `HGRendererListUtils`, or
`HGGraphicsFeatureSwitch`. This closes the current installed IFix replacement
question for this route, but not a later delivered patch: wrapper gates
`0xBE4`, `0x19C`, and `0x19D` still permit a future replacement. Those gate IDs
are not the patch file's on-disk keys; current disjointness is proved by the
parsed type/method/parameter signatures.
The loader route is also pinned in native code. `HotFixPatchManager.PatchInitAssemble`
gets the VFS block and calls `PatchAssemble`; the latter opens the VFS asset
stream, verifies it through `RSACryptoUtils.VerfyStream`, unloads the prior
`IFix.Core.PatchManager`, and calls `PatchManager.Load`. The download-ready
proxy separately enters `_ApplyDownloadPayload`, which directly reaches Lua-
string, ordinary-string, and localized-text injection, while the binaries also
retain remote-config and forced local IFix/Lua entry points. The current patch
does change general presentation-related code—`CharacterPhotoSystem`, four
cinematic-timeline targets, and `DialogManager._DoPlayCinematicNode` are among
the 30—so “no current CharInfo/render/pose replacement” must not be broadened
to “no installed patch.” The hash-pinned source report is
`installed_ifix_patch_state.json`; the maintained
`unity_endfield_graph_shader_lab/tools/verify_installed_ifix_patch_state.py`
re-parses the payload and loader edges after installed-data changes.
The render lambda's handle-to-global routing is also closed: up to four valid
GBuffer handles, copied depth, previous scene color, SSR lighting/fadeness, AO,
fake planar reflection, fog LUT, and wetness are routed through their original
`HGShaderIDs`; an invalid wetness mask binds Unity's white texture. The exact
offline constructor also fixes `changeColorRT=false`: scene color is attachment
0 with explicit Load/Store, scene depth is attached read-only, and GBuffer
handles remain read inputs published as globals. `M_CharInfo_outside` writes
stencil shading-model value 0 with Replace; of the submitted ref-0/1/2 full-
lighting passes, only ref-0 Default Lit (and ref-0 WriteAlpha) affects the
sphere. The exact resource contents/
descriptors/lifetimes, subpass and stencil state, and live lighting/shadow/
indirect/history producers remain unknown. A
Standard/URP/HDRP gray sphere would conceal this real gap and is intentionally
not used. The maintained verifier is
`unity_endfield_graph_shader_lab/tools/verify_charinfo_outside_lit_recovery.py`.

The installed original resolver is now also extracted as raw shader sidecars,
not only read through AnimeStudio's quoted D3D11 disassembly. A one-asset
filter pins `HGRP/DeferredLighting` to PathID `6850169740889141214` in
`assets/beyond/initialassets/settings/renderpipeline/hgrenderpipelineglobalsettings.asset`
and the installed `0CE8FA57/19F0903A12BA87C0D43E67E64889B525.chk`.
For the pass-0 `Default Lit - Full Lighting` candidate with
`HG_ENABLE_SCREEN_SPACE_SHADOW_MASK` and
`HG_USE_SUBPASS_INPUT_UNDER_ONE_PASS_DEFERRED`, the original Vulkan fragment is
`0101_endfield_spirv_1.spv`, SHA-256
`112BCB9FD9152C6530C576E6C9431D37A12CD826E4116D114D360986109F8030`.
The keyword is a compiled-variant fact and must not be equated by itself with
the native `isOnePassDeferred` boolean, which the installed render lambda passes
as false. Metadata enrichment plus decompilation pins five named constant
buffers (`_TransformVariables`, `_LightDataBuffer`, `VisibilitySHConstData`,
`ShaderVariablesGlobal`, and `ReflectionProbeGlobalData`), four still-unnamed
buffers at set 3 bindings 32/34/37/38, 25 sampled textures, one byte-address
buffer, and five samplers. Cross-platform comparison against the exact original
48,984-byte DXBC fragment (SHA-256
`B21A1E35EDA1C5BCB60198C6AF313799DDCC94D0CEE0BE9025938F3BA8C56B6F`)
now role-identifies binding 32 as the 48-byte `_LightBinningConstants`: its
four-int/eight-float layout and used lanes calculate 32x32 screen tiles, z bins,
and offsets into the light-list byte-address buffer. The selected SPIR-V debug
metadata still omits that source name, so the contract preserves the distinction
between role identification and a named descriptor. Bindings 34/37/38 remain
unidentified in the selected debug metadata, but b34 is now independently
source-closed as `ShadowData`: its 11,440-byte layout exactly matches the
original ShadowReceiver metadata, including five `_CSMWorldToShadow` matrices
at byte 0, 15 `_CharacterWorldToShadow` matrices at 7168, ASM matrices at
9216/9280, and 128 `_ASMIndirectParams` vectors at 9392. Only b37 and b38 remain
anonymous in the selected resolver's debug metadata, but b37 is
binary-role-identified as the
2,560-byte `LightCookieData` layout: 32 atlas scale/offset vectors followed by
32 world/direction-to-cookie matrices, used immediately before sampling the
per-light cookie texture. Binding 38 is now independently source-closed by the
exact original `HGRP/ScreenSpaceShadowResolve` sidecar as the 3,568-byte
`HDPunctualLightCharacterShadowData` layout: 32 character world-to-shadow
matrices at byte 0, 32 HDPLS parameter vectors at 2048, 56 `uint4` character
index records at 2560, screen-space shadow indices at 3456, four screen-space
light positions at 3488, and global parameters at 3552. The selected resolver
uses the character-index `.y` lane to select one of four screen-space shadow
channels before falling back to the punctual shadow atlas. All four
debug-anonymous constant-buffer roles are therefore closed. Eight initially
pinned texture bindings are camera depth, GBuffer
A/B/C, screen-space shadow mask, wetness, SSR lighting, and SSR fadeness.
The native `aoEnable` route plus scalar indirect-occlusion math also closes
`_IndirectAmbientOcclusionTexture` at set 3 binding 21. The other 16 names are
now pinned by their selected-binary sampling behavior and exact strings at
hash/offset-verified positions in the installed `global-metadata.dat`:
`_LowResDirectionalShadow`, `_CSMShadowRampTex`, `_HDPLSTex`,
`_PunctualLightShadowTexV2`, `_LightCookie`, `_MultiscatteringLUT`, the
three A/B `_IrradianceVolumeClipmapTexture*` pairs for LOD0/1/3,
`_VisibilitySHRT`, `_LogSHLutTex`, `_ReflectionProbeOctTextureArray`, and
`_IntegratedLightScattering`. All 25 sampled texture roles are therefore
named. A bounded installed-game extraction now also closes the relevant
serialized CharInfo scene controls: `CharInfoCtrl` maps both
`charOverrideVolume` and `overrideVolume` to the enabled priority-30001 global
Volume using `CharOverrideVolumeProfile`; the prefab's enabled priority-30000
global Volume uses `CharInfo_Volume`; and the enabled priority-600 global
environment volume uses `CharInfo_Env` at full manual blend. The exact profile
and environment bytes prove wetness, fog, height fog, volumetric fog,
volumetric-flow noise, cloud shadow, and ASM disabled. The selected original
fragment consequently does not sample `_WaterWetnessMaskTexture` when
`_WaterWetnessMaskParam0.x` is disabled and does not sample
`_IntegratedLightScattering` when `_VolumetricFogParams0.z` is zero. Its
disabled wetness branch uses `(1,1)`, and the native pass binder's invalid
wetness-handle fallback is `Texture2D.whiteTexture`.
The current retail binders now close both selected disabled texture resources
instruction-for-instruction. `DeferredLightingPassConstructor+<>c` tests the
wetness `TextureHandle` and publishes Unity's built-in white `Texture2D` when
it is invalid. When `HGRenderPathScene.ShouldRenderVolumetricFog` is false,
`VolumetricFogPassConstructor+<>c` publishes
`HGVolumetricFogUtils.volumetricBlackTexture3D`. Its unpatched creator at
GameAssembly VA `0x189CEF4E4` constructs a 1x1x1 `Texture3D` with numeric
`TextureFormat` 48 (`ASTC_4x4` in the hash-pinned Unity 2022.3.62f3
`UnityEngine.CoreModule.dll`), no mip chain and no uninitialized creation,
writes `Color.black` to `(0,0,0)`, then calls `Apply(false, true)`. The
hash-pinned audit is
`scratch/character_recovery/charinfo_pass0_resources/deferred_resource_layouts.json`;
these resources are source-closed but remain unpublished because the pass-0
owner is still default-off.

The same pass audit closes the `_VisibilitySHRT` resource descriptor and its
retail empty path. `CapsuleShadowPassConstructor.ConstructPass_VisibilitySH`
creates a camera-sized or signed half-resolution target with numeric
`GraphicsFormat` 48 (`R16G16B16A16_SFloat`), bilinear filtering, clamp wrap,
no mip chain, and no random write. The active lambda binds
`_LogSHLutTex`, `_ABLutTex`, and the produced target. Both the disabled/
maximum-count-zero branch and the post-cull-zero branch store
`Texture2D.blackTexture` into `visibilitySHRTDefault`; the empty lambda then
publishes it as `_VisibilitySHRT`. This closes the descriptor and exact black
fallback. A separate original-resource recovery also closes both producer LUTs.
The exact shipped `HGRenderPipelineRuntimeResources` asset
(PathID `5613980184714137857`) points `VisibilityABLut` to PathID
`2892350180982884757` and `VisibilitySHLut` to PathID
`8323377478838034894`. Targeted AnimeStudio Texture2D export proves both are
256x1 `RGBA32`, Gamma, one mip, bilinear/clamp, and supplies exact 1,024-byte
RGBA payloads. Their payload SHA-256 values are respectively
`ca1a648d1a19434b41a9dbbe9f6ad0191c4c4e7f088341761725895748f33ed0`
and
`3e5d7d50ed14ab927676cb638eebcedfb8e02766b8e0d01164105d519d925bf3`.
The reproducible manifest is
`Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/visibility_luts.json`
and the pinned recovery tool is
`scratch/character_recovery/visibility_luts/recover_visibility_luts.py`.

The capsule input, native packing ABI, and exact producer shader are now
separately source-closed by
`scratch/character_recovery/visibility_capsule_runtime/audit_visibility_capsule_runtime.py`.
Wulfa and Zhuang each serialize one enabled `HGCapsuleShadowHelper` with ten
enabled VisibilitySH candidates, intensity 2, unit radius/height scales, and
`m_interactionOnly=0`. The unpatched helper `OnEnable` at GameAssembly VA
`0x18435D900` enqueues the helper and calls `AddCapsuleListBinding` at
`0x18351FF70`; the latter skips only interaction-only helpers and calls
`AddCapsuleBinding` for every serialized candidate. These ten records are the
VisibilitySH helper topology, not the separate secondary-dynamics collider
counts elsewhere in this document.

The active native route is
`UnityEngine.HyperGryph.HGCapsuleShadowManager`, not the older managed
`HG.Rendering.Runtime.HGCapsuleShadowManager`. Its UnityPlayer count
implementation at `0x180FCB620` subtracts the sentinel and caps the result at
128. The culler at `0x180FCABA0` uses 52-byte internal records, requires the
valid byte plus positive radius/full-height/intensity fields, and copies three
float4 values at internal offsets `+4`, `+0x14`, and `+0x24` into a packed
48-byte `{pa,pb,dir}` output. The shader metadata independently matches this:
a 16-byte header plus 128 records of 48 bytes yields the exact 6,160-byte
`VisibilityCapsuleData` constant buffer.

UnityPlayer's `HGCapsuleBindingComponent` icalls and writer at `0x180FCB950`
close the transform-to-record formula. It composes the current root transform
with the authored local offset and Euler rotation, takes the normalized
composed local `+Y` basis as the world capsule direction, computes
`fullHeight=max(capsuleHeight,2*capsuleRadius)` and
`halfSegment=0.5*fullHeight-capsuleRadius`, then writes
`pa=float4(center-direction*halfSegment,radius)`,
`pb=float4(center+direction*halfSegment,fullHeight)`, and
`dir=float4(direction,clamp(intensityScale,0.01,2))`. Radius, height,
offset, rotation, intensity, and force-render storage offsets and all seven
setter icall table entries are hash/instruction-pinned by the audit.

The active render lambda at GameAssembly VA `0x189D25E7C` calls
`CommandBuffer.HGDrawMeshInstanced` with shader pass index 2. Targeted
AnimeStudio export pins original `HGRP/VisibilitySH` PathID
`-4362943401419010014` and its exact D3D11 pass-2 payload. The pass is
additive `One One`, `ZTest Greater`, `ZWrite Off`, `Cull Front`, with stencil
`Ref 4 / ReadMask 7 / NotEqual`. Its fragment reconstructs world position and
the GBuffer normal, evaluates a bounded sphere chain along the capsule, samples
the exact `_LogSHLutTex`, accumulates L0/L1 SH, and applies distance plus
`dir.w` intensity. `_GStarParams` is exactly
`(17.4207001,9.5547895,-17.4207001,-9.5547895)`; interval scale clamps to
`[0.8,2]` and range scale to `[0.01,5]`.

The direct owner and retail defaults are now closed too.
`HGRenderPathDefaultDeferred.RenderScene` at `0x189BF0890` is the sole direct
caller and constructs the complete 0x90-byte input before calling
`ConstructPass_VisibilitySH` at function offset `+0x4033`.
`HGRenderPipeline.settingParameters` supplies
`visSHEnabled`, `visSHSphereIntervalScale`, `visSHSphereRangeScale`, and
`visSHHalfRez`. The hash-pinned `HGSettingParameters..ctor` at
`0x1836590A0` constructs those defaults as true, `0.8`, `5.0`, and true;
tiled rendering defaults false and tile size defaults 32. The current installed
settings lifecycle is now closed as well: `PrepareRenderPipelineSettings` is
called once by the pipeline constructor, constructs and stores this object at
pipeline offset `+0x160`, the replacement setter has no direct caller, and the
setting hub registers eight other keys but no callback for
`VISIBILITY_SH_FEATURE_NAME` at static-field offset `+0x68`. The base
`StreamingAssets` `IFixPatchOut` block declares zero files, chunks, and bytes.
The active Persistent overlay is nonempty, but its 30 exact
`Gameplay.Beyond` targets are disjoint from `HG.Rendering.Runtime` and the
render-pipeline settings methods. The constructor values are therefore
effective for this snapshot. A future downloaded IFix patch or external
reflection/debug mutation remains a version boundary, not an active unknown
in the current install.

The half-resolution attachment path is exact rather than inferred. The
constructor creates a half-width/half-height depth target using the active
scene depth format, and the static downsample lambda at `0x189D26338` draws
`HGRP/VisibilitySH` pass 0. That fragment gathers the four source-depth
samples in each 2x2 footprint and writes their minimum to `SV_Depth`. The
active pass then writes half-size `R16G16B16A16_SFloat`, attaches this reduced
depth for `ZTest Greater`, and still samples `sceneDepthCopied` and GBuffer
attachment 1 at normalized full-frame UVs. When half resolution is disabled,
it attaches the original scene depth instead.

The exact draw geometry is also closed. The shipped runtime-resources object
points `assets.simpleSphereMesh` to PathID `-497958453517564970`; targeted
installed-VFS export identifies `pSphere1`, 79 vertices and 336 indices, with
approximately half-unit extents. The ten helper root transforms resolve in
both Wulfa and Zhuang to right/left thigh, calf, upper arm, foot, Spine1, and
Head. Their exact hierarchy paths and authored values are preserved in
`Assets/EndfieldGraphShaderLab/Resources/EndfieldRecoveredVisibilitySH/visibility_sh_runtime.json`.

A default-off binding-compatible Unity replay now exists in
`EndfieldRecoveredVisibilitySHProducer`. It loads the exact raw Gamma SH LUT,
the exact `pSphere1` mesh, and the Wulfa/Zhuang authored payloads; derives live
posed `{pa,pb,dir}` records with the native formula; applies the native
conservative view-plane cull; runs the retail min-Gather depth pass and additive
capsule pass; publishes the offscreen result under
`_EndfieldRecoveredVisibilitySH`; and keeps canonical
`_VisibilitySHRT` black. The diagnostic explicitly restores the canonical
color/depth attachment after its command stream. This isolation is necessary:
an early probe that left the offscreen target bound corrupted the subsequent
forward draw even though no canonical consumer was intentionally enabled.
It is enabled only by `ENDFIELD_RECOVERED_VISIBILITY_SH=1` or
`-endfield-recovered-visibility-sh`. The editor compile, exact shader variants,
and full 30-character build pass. Unity's ordinary `DrawMeshInstanced` route
did not execute this raw `SV_InstanceID` shader because it expects Unity's
transform-instancing contract; `DrawMeshInstancedProcedural` is the
binding-compatible adapter for the retail `HGDrawMeshInstanced` call.

Current D3D12 standalone captures validate both actor paths at 960x540
(480x270 producer targets). Wulfa produces 41,820 nonzero pixels with raw
RGBAHalf SHA-256
`f9c268f1d8432dfcce797fc73d9e20f8a88f654dfe5b5c0291af9f4216a240db`;
Zhuang produces 65,667 with
`d663c2a0d17fd19a2b9329fb5363a705538e7e756dbd777cb9137a0bed954357`.
The culling update leaves all ten Wulfa and all ten Zhuang records alive in
registration order `[0,1,2,3,4,5,6,7,8,9]`. Binary evidence pins the culling
cube to the posed world center with extent `0.5 * fullHeight * 5.0` on every
axis; the engine tests that cube against every view plane and copies survivors
without sorting them. Applying that exact gate leaves both raw hashes unchanged.
For each actor, the presented PNG is byte-identical with the producer-on and
producer-off, proving the current replay remains isolated from canonical
presentation. These captures validate the lab producer and binding/attachment
discipline, not parity against a captured retail VisibilitySH target. The
current full technical rebuild also exits zero and regenerates the resident
33-actor viewer/catalog, covering the 30-character roster gate without compile
or shader failures attributable to this producer.

The isolated numeric record transport is now closed separately from retail
pose evidence. The producer logs the exact little-endian packed
`10 * 48`-byte `{pa,pb,dir}` payload and all 20 float4 triplets. Two
independent D3D12 runs per actor are record-for-record identical: Wulfa hashes
to
`0e418fd299cfaa88e8de5ef0388bb5328e326c5afd0b4c69cf2cf47b4a440a08`
and Zhuang to
`1f72039bdd39a1ae073dd2629f0e1245145a852e78dd4114778204ddde654264`.
Each repeated run also preserves the prior nonzero GPU-output hash. The
generated VisibilitySH runtime audit stores every numeric record and validates
the repeated logs. This proves deterministic Unity-side packing and transport;
it does not prove that the lab pose/view equals a settled retail frame.

What remains is the corresponding retail view handle and survivor
count/order, retail settled posed-record values, and a retail VisibilitySH
target capture for quantitative comparison before canonical consumption. The
current installed settings lifecycle/defaults, LUTs, actor candidates and bone
ownership, exact mesh, native packer/output ABI, conservative culling
algorithm, half-resolution depth path, producer algorithm, standalone
Wulfa/Zhuang GPU readback, and technical roster sweep are no longer open
boundaries.

The live irradiance-volume object selector is now closed and corrects the
earlier legacy-path attribution. `HGRenderPipeline.Render` at GameAssembly VA
`0x183455030` calls
`HGIrradianceVolumeManagerV2.PipelineUpdateV2` at `0x183336A30`.
That method stores/uses `m_defaultIV` at field offset `0x10` for the native
V2 pipeline call. Its `m_gachaIV` field at `0x30` only gates update-center
selection; it does not replace the rendered object. The old
`HGIrradianceVolumeManager.GetActiveIV` method still implements
`m_gachaIV ?? m_defaultIV`, but `HGRenderPipeline.Render` does not call that
manager path in this build.

The installed Lua VFS independently closes CharInfo participation in the old
gacha-IV lifecycle. A complete hash-pinned block index contains 1,291 files
and 20,131,202 bytes; AnimeStudio decoded 1,290 scripts, with the sole failure
a non-Lua `ChangePortableDeviceCtrl.md` entry. Across every decoded script,
only `LuaSystem/GachaSystem.lua` owns `CreateGachaIV` and `DestroyGachaIV`.
Its character-IV allow-list contains `GachaPool`, `GachaLauncher`,
`GachaDropBin`, and `GachaChar`, excludes `PhaseId.CharInfo`, and destroys the
override when leaving those phases or on release.
`Phase/CharInfo/PhaseCharInfo.lua` contains no IV lifecycle call. This Lua
evidence is corroborative; the live `m_defaultIV` choice comes from the V2
binary path rather than the old Lua-facing selector.

The V2 native owner now closes the resource contract too. Its default config
uses 128x64x128 clipmap dimensions and LODs 0/1/3. It creates A0/A1/A3 as
128x64x128 `B10G11R11_UFloatPack32` and B0/B1/B3 as default-quality
128x64x384 `R8G8B8A8_UNorm` textures (low-quality B depth is 128). All six
are one-mip random-write point/repeat `Tex3D` resources, named
`HGIrradianceVolume::ClipMapA/BLod%d`, and are published in exact
A0,B0,A1,B1,A3,B3 order. When the native V2 object is missing, the result
packer assigns the same 1x1x1 zero `UnityDefault3D` resource to all six
slots. `HGRenderPathBase.OnPreRendering` forwards the V2 result to
`UpdateShaderVariablesIrradianceVolumeV2`, which publishes the six exact
shader IDs and folds `curFrameIdx % 64` into param3.z. Persistent basis/coeff
atlas names, formats, counts, and dimension formulas are closed; their
transient dimension inputs are not.

The hash-pinned audits are
`scratch/character_recovery/charinfo_pass0_resources/charinfo_v2_irradiance.json`
for the live binary chain and
`scratch/character_recovery/charinfo_pass0_resources/charinfo_irradiance_owner.json`
for the Lua lifecycle boundary. Exact current-scene streamed voxel payloads,
persistent-atlas transient dimensions, and per-frame param0..param3 values
remain open.

The same source prevents an over-broad neutral shortcut. `CharInfo_Volume`
contains active `HGDisableDirectionalShadowComponent=1`,
`charIgnoreMainLightShadow=1`, and character-shadow-resolution override `-1`,
but the exact unshadowed `_LowResDirectionalShadow` producer value and CSM-ramp
binding are still open. More importantly, `CharInfo_Env` has
`reflectionType=1`, reflection-map PathID `2404688955498524548`, sky-cubemap
PathID `-5544960624411894816`, and the priority-30001 character override has
live cubemap PathID `-8084913603968714749`; reflection must remain live.
All three referenced Cubemap payloads are now recovered exactly:
`T_hdri_reflection_char_01`, `T_hdri_006`, and the formerly unresolved
reflection-map `T_hdri_env_char_01` are 128x128 BC6H, six-face/eight-mip
assets with hash-pinned 131,232-byte serialized payloads. The third has PathID
`2404688955498524548`, CAB
`CAB-7e9fb62841465607699a223e58b64af8`, current installed source
`98E51B76A48F5BEF8D07BDFD3E4DA7ED.chk` offset `1026030945`, and payload
SHA-256
`948F8D8DFB77E1B29171C4B04CAAA679202E06624AB7BE2203719E11CA6EE7B7`.
The installed build repacked the older character/sky CABs into
`4A65D5C2457B9C4DBE29646A23A14004.chk`; bounded re-export confirmed their
payload hashes did not change. The installed
`ReflectionProbeBinningCS::SampleOneTextureMip4AndNotReadSrc` producer and its
host contract are now source-closed. Two dispatches (`32x32x1` from source
mip 0, then `2x2x1` from source mip 4) populate destination slice 0, mips
0..7 of the exact 576x576x32 linear RGBAHalf
`_ReflectionProbeOctTextureArray`; the array has ten physical mips. The
source-derived Unity compute port reproduces the expected slice-0 bytes for
all eight populated mips and gives byte-identical results on a repeated GPU
run. The diagnostic remains isolated and does not publish the texture to the
renderer.

The corresponding installed `ReflectionProbeGlobalData` producer is closed
through `ReflectionProbeBinningPassConstructor.PrepareConstantBuffer` at
GameAssembly VA `0x189D10660` and
`HGReflectionProbe.UpdateViewCBHandle_Injected` icall 423/native implementation
VA `0x18108A090`. The constant buffer is exactly 4,160 bytes: four header
`float4` values, one reserved 128-byte global-fallback record, then 31
128-byte local records starting at byte 192. The native producer overwrites
`Param2.x` with the local-probe count; the isolated CharInfo fallback is zero.
Its required live header lanes are `Param1.w=512/576`,
`Param2.w=32/576`, and the exact serialized sky-SH L1 Rec.709 luminance vector
`(-0.0075507620, 0.0121708112, 0.4722373486, 1.0963057280)`. The per-camera
header uses 32-pixel tiles and
`Param2.z=nearHeight*32/ceil(renderHeight/32)`. Camera binning allocates light
and reflection sections in one zero-based byte-address buffer: light uses
2,048 z slices/eight words per bin, reflection uses 1,024 z slices/one word
per bin, and total storage is `9*tileCount+17408` words. With zero local masks,
the selected fragment falls through directly to oct-array slice 0.

`EndfieldRecoveredReflectionProbeFallback.cs` now owns this exact
source-derived no-local resource set and can record both conversion dispatches,
the constant buffer, and the combined zero binning buffer. It is internal,
nothing constructs it in the presentation path, and its only publication
entry point is explicitly diagnostic; `_ReflectionProbeOctTextureArray`,
`ReflectionProbeGlobalData`, and pass 0 therefore remain default-off. The
hash-pinned binary audit is
`scratch/character_recovery/charinfo_reflection_runtime/reflection_global_buffer_audit.json`
(SHA-256
`AD3CE9E92B60E8E47DC55A695FCA668AB477EE2757A0FDC956BBF12FC73B17B3`);
the generated binding contract pins the auditor, GPU report, compute port,
verifier, and runtime producer. The current installed IFix target table has no
HGRP binning or reflection-probe target, so these audited unpatched bodies are
active for this build.

`useCustomIVDefaultSH=0` is not proof of a neutral irradiance route. The live
V2 owner, six A/B descriptors/order, persistent-atlas formulas, zero fallback,
and global-publication bridge are now closed, but exact current-scene streamed
IV voxel contents and per-frame parameters remain open. Exact live
light/shadow resource instances plus retail settled VisibilitySH posed-record
values, cull survivors/order, target contents, and lifetimes remain to be
recovered; the current installed `PassInput` settings lifecycle, both
VisibilitySH LUT payloads, the output
descriptor/empty fallback, native packer/output ABI, actor candidates, exact
pass-2 producer, and selected disabled wetness/fog placeholders are now
closed.
The
byte-address resource at set 3 binding 39 is
`_BinningBuffer`: its masked loads use `_BinningBufferOffsets` for both
light and reflection-probe tile/z-bin lists. The fail-closed machine-readable result is
`Generated/OriginalData/CharInfoPresentation/deferred_resolver_binding_contract.json`;
the reproducible extraction/decompilation inputs remain under the lab's
`scratch/reverse_engineering/sphereoutside_deferred_variant/`.

A source-specialized, default-off five-MRT producer diagnostic now executes the
exact recovered sphere mesh, original 4x4 DXT1 MRO texture, serialized material
floats, and the binary-derived metallic/occlusion/roughness/porosity/normal
packing. It deliberately uses a deterministic diagnostic projection and
`ZTest Always`: it validates material and HGBuffer lanes, not original
visibility/depth ownership. The D3D12 batch run covered 130,488/262,144 pixels
(`0.497772216796875`) with zero mismatches in scene color, scene motion,
GBuffer A/B/C, and a varying oct-normal field. The validation JSON SHA-256 is
`45A79BA5D1BCA9634E121C699F7166FC0CD61154DDA98A9BF0BC701ADBA40FCB`;
the Unity log SHA-256 is
`4E941E7CF79A4C5E23D9C7DA334321F2FC83AD6518D7C06487E69E878D2A079A`.
Run `verify_sphereoutside_hgbuffer_diagnostic.bat` to reproduce it. This pass is
not submitted by the ordinary viewer and does not make `SphereOutside`
runtime-ready.

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
| All 30 shipped main UI AnimatorControllers, including their 40-state graphs, 31 transitions, Overview entrance selectors, start-to-idle timing, body/private-deco state propagation, and curve-driven deco visibility threshold | The legacy viewer stores the recovered selector/interruption/root-blend evidence but does not execute the complete parameter-driven menu graph, retail interruption policy, events, or every state-to-state transition |
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
motion/root/limb-IK attributes, the 101-muscle range, then 63 unused entries.
This tail is no longer inferred padding: a complete census of the 793 decoded
original Wulfa/loli MuscleClips found the same 206 entries in every clip and
zero violations, with every index at 143..205 exactly `-1`. The installed
`UnityPlayer.dll` proves that the six additions are
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

Official-f1 cross-comparison now separates the unchanged native families from
the forked 101-muscle stage. Exhaustive table xrefs prove the exact lookup pairs
`0x949D80 <-> 0xB229A0` and `0x956E60 <-> 0xB2F990`, plus the output-writer
family `0x959E50/0x959F50 <-> 0xB32240/0xB32340`. Normalized call-graph
matching establishes seven more high-confidence public-f1/retail-f5 pairs:
`0x958F40 <-> 0xB314D0`, `0x959FF0 <-> 0xB323F0`,
`0x94F390 <-> 0xB27930`, `0x95B200 <-> 0xB33BD0`,
`0x94D4B0 <-> 0xB25C20`, `0x94D910 <-> 0xB261F0`, and
`0x932600 <-> 0xB06170`. Public f1 wraps scale preparation and mapped-pose
conversion as `0x94DD80 -> 0x94D910 -> 0x94D4B0`, while retail f5 calls the
last two functions directly. Crucially, the f5 input gather at
`0xB25830/0xB25910` is now instruction-closed rather than inferred from public
code. It iterates human bones `1..24`, skips a compact mapping exactly equal to
`-1`, reads the hash-pinned `0x1DDE010` table in stored selector order `2/1/0`,
reverses it into converter lanes `0/1/2`, substitutes zero for absent lanes,
and forwards the raw unclamped muscles to `0xB38B10`. The optional hand helper
`0xB25300` is also closed: each five-finger side consumes four values per
finger `(phalanx-1 stretched, spread, phalanx-2 stretched, phalanx-3 stretched)`
and emits three vectors `(0,spread,phalanx1)`, `(0,0,phalanx2)`, and
`(0,0,phalanx3)`, while
skipping negative compact mappings. This is a retail refactor of public bulk
gather `0x94CF10`, not the public output-writer family; the structural
look-alike match to `0x959E50/0x959F50` remains explicitly rejected by xref
direction. Retail bridge `0xB38B10` and public `0x95F440` are role/dataflow
counterparts. The `0xB25B20` split-stage topology relative to public
`0x94D300` is now closed as
`B32340 -> B25910/B38B10 -> B37BF0 -> B36620 -> tail B38110` versus
`959F50 -> inline gather/95F440 -> 95EF70 -> 95E0A0 -> tail 95F270`.
The deeper `0xB34260 <-> 0x95B8B0` correspondence is now instruction-closed for
the humanoid ZYRoll path rather than inferred from its normalized similarity.
Both functions dispatch on `AxesInfo+0x54` with the same value-1/value-2/value-4/
default topology. Retail f5 calls tangent helper `0xA7B990` for the value-1
path, while public f1 inlines the same range-reduction constants and rational
tangent dataflow there; public calls equivalent helper `0x90D3E0` in the other
shared paths. Retail then inlines the final Avatar sandwich at `0xB347E5`,
where public calls leaf `0x908540`. Exact cross-term instructions in both build
`Qaxes = normalize(tx, ty + tx*tz, tz - tx*ty, 1)` and then
`Qlocal = normalize(preQ * Qaxes * inverse(postQ))`. The differences are
compiler inlining, register allocation, spills, and pdata partitioning; no f5
muscle/limit/sign-to-quaternion equation delta was found. The public Force-Text
Avatar fixture independently validates that maintained equation across 21
body bones with maximum angular error `3.423621675895667e-05` degrees. Public
f1 still is not the missing f5 full-frame physical Transform oracle. Static
recovery has nevertheless closed the downstream implementation: retail
`B13240` performs compact-pose copy `B33B50`, eight-pair `B323F0` TwistSolve,
then `B06170 -> B33BD0` copies complete 48-byte translation/rotation/scale
records to mapped physical nodes. The later generic component overlay
`B06330` is the semantic counterpart of public-f1 `9327D0`: each mapped
translation, rotation, or scale component replaces that component of the
physical/base record independently. Scheduler evidence orders that overlay
after the humanoid job completes. The remaining boundary is numeric validation
against observed retail output, not an unknown hierarchy or write-order stage.

The first allowlisted retail-instruction experiment and its Axes construction
boundary are now closed. An offline Unicorn 2.1.4 harness executes only
`A7B990..A7BB1D` and `B34260..B34908` from the pinned retail player, denies all
imports/syscalls/out-of-range control flow and all writes except its private
stack/output, and covers 22 original Wulfa Axes rows across all 33 frames (726
calls, 250 instructions and one tangent-helper entry each). Stock-symbol PDB
layout plus the retail safe, streamed, BlobWrite, AvatarConstant, Human,
Skeleton, and Axes-array materializers prove `m_PreQ@0x00`, `m_PostQ@0x10`,
sign/min/max/length/type at `0x20/0x30/0x40/0x50/0x54`, and 0x60-byte record
stride. Retail `B38B10` computes `axesId*0x60` and passes the record directly to
`B34260`; there is no adapter or swap. Correcting only the old emulator packing
leaves the production `avatar_local_rotation_from_muscles(pre_q, post_q, ...)`
formula unchanged and reduces the maximum residual to `2.980232e-7` per
component and `2.986988e-5` degrees. The experiment remains deterministic
code-derived inner-stage output, not an observed runtime Transform oracle. The
constructor/bridge report SHA-256 is
`D4D9750E3E2C70FE58131C654CCA03C68DF39663DA6439868156B9A8A3558E5E`;
the corrected emulator report SHA-256 is
`0430773687388CA42BCDD4E6037B0F21D4525D9DFA40567F77EBF1669BCA7C00`
and raw 11,616-byte quaternion SHA-256 is
`DDB083FB9E779F119A2EB77D012EDCEFEDC719D09DA14120A1A34884BF857125`.

The same strict harness method now covers retail `B27930` TwistSolve after the
Axes phase. It executes 264 complete Wulfa calls (33 frames x eight ordered
pairs) and pins the worker ABI, Avatar/Human relative layout, two private
0x30-stride poses, parent/child write ownership, and exact helper-entry topology.
The raw 8,448-byte output SHA-256 is
`3E9F68DFAA91C4DD784D49016C0F9FB7D1C1E7209BB80012FEBC23EE3ADD6EEF`;
the report SHA-256 is
`3B659F7BBF4E759BA75BD7817C8B6FBDE1BBE82E89BEC83DEEE6CBD134C66C2C`.
The maintained semantic port agrees within `4.1724e-7` parent and `4.0234e-7`
child quaternion components, while combined parent/child orientation is
preserved within `1.449e-5` degrees. Public-f1 private symbols independently
identify `mecanim::human::TwistSolve` at `0x959FF0` and `HumanFixTwist` at
`0x94F390`. No production equation changes are required. Live CPU feature-
selected transcendental low bits, the enclosing `B314D0` object/scheduler, and
an observed retail Transform oracle remain open.

The maintained Wulfa fixture now composes all 33 frames into the complete
486-node serialized physical skeleton. Each frame contains 24 humanoid local
transforms from the hash-pinned retail semantic port, 58 exact original ACL
translation/rotation tracks, and 404 untouched serialized-rest nodes. All 58
bindings author only attributes `1/2`, so native `B06330` preserves serialized
base scale rather than applying the decompressor's default scale lane. The
tracks are 30
finger nodes, 16 named twist side branches, nine explicit IK targets, one
look-at node, and two weapon nodes; their destination set has zero overlap with
the compact humanoid destinations. The loop endpoint aliases exact ACL frame
zero, matching the original clip's duplicated humanoid endpoint. Semantic pose
JSON SHA-256 is
`7E958BB1C6C0BEAC07AB9E7C98E605F4250A86E16338876B3511A80B760DF2B4`;
the independently recomposed 486-node world-pose digest is
`A7F405B88CB47FE6949E65CCD5578347C9009AB39E6192232E6E0E5B2793068C`.
Across 264 explicit pair steps, direct parent/child world-orientation
preservation is within `8.01e-6` degrees, and explicit replay agrees with the
maintained TwistSolve port within `2.42e-6` degrees.
This is deliberately a mixed-authority fixture: the generic QVV tracks are
original decoded output, but the 24 humanoid transforms are source-derived
semantic predictions, not observed retail-f5 runtime output. A fresh public
2021.3.34f1 exact-Wulfa stock-95 control validates unchanged non-Hips/non-toe
surrounding math within `3.85e-5` degrees and `1.23e-7` position-component
error. The former toe residual (`6.2526851` degrees maximum) is now
source-closed as a public `AvatarBuilder.BuildHumanAvatar` default-limit
mismatch, not an unknown f5 basis/layout difference. The exact Wulfa
`HumanDescription` marks toe limits unmodified, so public f1 re-bakes its stock
one-channel toe limit of +/-50 degrees; the original serialized f5 Avatar
stores selector limits of +/-40, +/-50, and +/-80 degrees and uses the last for
Toe Up-Down. Persisting that public-f1 Avatar proves its toe `preQ`, `postQ`,
selector-2 direction, and zero pose agree with the original. Across all 33
frames the discrepancy is `abs(Toes Up-Down muscle) * (80-50)` degrees, with
maximum public prediction/output error `1.45e-5` degrees. This validates using
the original serialized f5 `AxesInfo`; it is still not an observed retail-f5
physical Transform oracle.

The Hips/root stage is now substantially source-closed instead of being treated
as a direct serialized-Root substitution. The installed retail build is the
proprietary `2021.3.34f5`; no public f5 editor exists, so the installed official
`2021.3.34f1` editor remains differential-only. Structural matching maps the
public finalizer into editor `Unity.exe` RVA `0x13A0C80`, with the post-helper
site at `0x13A1386` and post-write site at `0x13A15CB`. Re-arming captures cover
all 33 Wulfa frames. Compact root index `1` is the serialized Hips-rest source
record; retail `B314D0` writes
`T=rotate(inverse(helper), sourceT-center)`,
`Q=inverse(helper)*sourceQ`, and unit scale. Same-version captured-intermediate
replay agrees within `2.98e-6` position component and `2.42e-5` degrees.
Retail `B261F0` also proves that the body basis orthogonalizes twice:
`forward=initialRight x up`, then `right=up x forward`; the previous importer
incorrectly kept `initialRight`. Physical Hips uses the center and orientation
converted from serialized Hips-rest space, `RootQ*m_RootX.q`, and
`m_Scale*RootT`. The maintained port now implements that order. Against the
public rebuilt stock-95 Avatar, maximum Hips error drops from
`0.1541316509 m / 6.29149068 degrees` to
`0.00185039267 m / 0.109671613 degrees`. This last residual remains explicitly
cross-version because `AvatarBuilder.BuildHumanAvatar` re-bakes a public-f1
referential; it is not observed retail output. Exact retail numeric closure
still requires a sanctioned f5 harness or trusted physical-pose fixture.
The local `tools/RuriRipperImporter/humanoid_retarget.py` now carries the six
inserted selector mappings, raw over-range muscle behavior, corrected Hips-rest
basis/`m_Scale*RootT` solve, and exact retail eight-pair TwistSolve order. Its
five focused stdlib tests pin the 101-entry table, toe selector ownership,
unclamped conversion, and ordered pair list; these tests validate the recovered
contract but do not turn Blender output into the missing retail Transform
oracle.
Reproducible evidence is
`scratch/character_recovery/humanoid_f5_output/ROOT_TO_PHYSICAL_RECOVERY.md`,
its JSON verifiers/captures, and
`scratch/character_recovery/humanoid_2021_baseline/WULFA_PUBLIC_F1_TOE_RESIDUAL.md`
with its JSON/verifier beside it.

The fixture's nine explicit IK targets are now locked by original Avatar path
CRC and ACL track order, rather than summarized by count: tracks 49..57 are
`IK_Foot_L` (`730228756`), `IK_Foot_R` (`4099293687`), `IK_Root`
(`1552008890`), `IK_Hand_L` (`823765373`), `IK_Hand_R` (`4006183070`),
`IK_Weapon_L` (`3085089603`), `IK_Weapon_R` (`1748144800`), `IK_Knee_L`
(`2573892693`), and `IK_Knee_R` (`1186616758`) in that order. Each target has
exact Transform attributes 1 and 2, position and rotation, and none overlaps a
compact humanoid destination. This proves authored endpoint data, including
both weapon targets; it does not prove that a runtime weapon constraint consumes
them.

Those numeric track indices are fixture-local, not an ABI. A seven-clip
original-data audit spanning 58..407 generic tracks resolves all nine targets
from each clip's binding CRC: `A_actor_wulfa_battle_attack_01`, for example,
places them at 373..381 rather than at the final nine tracks. Six audited clips
keep `IK_Root` at identity, but that battle attack animates it by up to
`0.5489786` position norm and `178.1207` degrees; recovery must never force
`IK_Root` to identity. Six clips also keep each weapon child close to its hand
target within compression-scale residual, while the battle attack deliberately
diverges by up to `1.4997` position and roughly 180 degrees. `IK_Weapon_L/R`
are therefore independent authored targets, not aliases of `IK_Hand_L/R`.

Retail scheduling around these targets is now instruction-closed one stage
further. `A2CBA0` clears the root-delta records; `A2CD74` evaluates and either
publishes normalized rotation/position directly or stores the pending slice;
`A681F0` later applies the component-wise pending scale/subtract operation. In
the normal `A69BC0` path, `A681F0` runs before `A4CE30 -> B06330`, so final
root-delta publication precedes the later generic/IK component overlay.
`ACE2D0` copies already evaluated left/right/interrupted records and weights;
it is not the missing transition blend math. The source-only verifier passes
119 checks; its SHA-256 is
`9B1B6CEC9A0B36C63A849F04DF5B2B455E40220F8011821BAD38FC33E17F41CD`,
and its report SHA-256 is
`ED6552BD0FC8957A0AAEB3678AC43A099E367B6438A3911EF1D46C45E9210914`.

#### Native animation implementation recovery

Expert-supplied reverse-engineering evidence narrowed three open runtime
questions into concrete leads. Static binary/data analysis has now closed part
of each lead while preserving the remaining implementation boundary:

| Lead | Current evidence | What must still be proved before implementation |
| --- | --- | --- |
| Six extra leg muscles | Source-closed for names, order, bone ownership, selector order, limits/sign, per-Avatar referential, GetZYRoll scaling/range reduction, native 101-slot production, the normal `Animator.Update` materialization edge, and TwistSolve pair order/semantics. The current `UnityPlayer.dll` SHA-256 is `B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`. All 34 exact postmodel Animator -> Avatar references resolve. All 272 audited pairs are adjacent in compact and mapped physical skeletons; only mapped parent/child TRS records are copied, while named twist side branches preserve their local curves. Retail `B13240` and `B06170 -> B33BD0` close hierarchy-to-physical ownership and full 48-byte TRS writes; `B06330`, its public-f1 `9327D0` counterpart, and the scheduler call chain close later component-wise generic precedence. Wulfa's 58 generic bindings author only translation/rotation, retain base scale, and do not overlap the 24 humanoid destinations. A broader 793-clip original Wulfa/loli scan found 318 clips animating at least one extension and 76 animating all six; all 793 have the exact 206-entry index layout and an all-`-1` tail at 143..205. `A_actor_loli_sprint_loop_sp_01` is the compact exact input fixture: 33 frames at 60 Hz, all six nonconstant, CHK `62EB15DCD74A3348E244B9B068AB9694.chk`, PathID `-7522027738202102101`, paired with `SK_actor_wulfa_01Avatar`. Its exact controller state is single-node `SprintSP`, Write Defaults on, speed 1, loop on, mirror off, `m_IKOnFeet=false`, and layer `m_IKPass=false`; all 188 Wulfa states and all nine layers keep those IK flags false. The nine authored `IK_*` tracks remain ordinary generic targets. Public 2021.3.34f1 comparison proves that f5 inserted the six direct and inverse-map entries into the otherwise stock ABI. Retail B261/B314 root equations, rest-space conversion, and `m_Scale*RootT` are ported. A strict inert native replay executes the original B314D0 -> B13240 physical materialization and later B06330 generic overlay for all 33 frames and all 486 local physical nodes. Its 769,824-byte fixture hashes to `3276498D97C516E83D1C0F7094754C9D7E2F3A5B448EBD8DBAFE01E1615FA115`; 693/693 isolated humanoid rotations, 1,914/1,914 generic-overlay records, and 13,332/13,332 untouched/rest records are byte-exact, all guards remain zero, two runs are identical, and frame 32 exactly equals frame 0. The opt-in Unity transport now applies the 485 non-virtual physical records plus 4,850 generic TRS bindings, fills 48 exact frame-zero Avatar support nodes, fails closed on a missing path, keeps frame 32 equal to frame 0, and visibly moves Wulfa's 4,902-vertex body by up to 0.5109154 units at frame 16. The contract SHA-256 is `53B4C7E4157ECE6579CCDDA5950C81E31E8BB56FC7F379F4BAF0A5A94F4413B3`; the Unity report SHA-256 is `BE1E6EAF7FB0EE242480E17FB7788EB8B2B973AA1550DCE30BE70F7BBED8A0E5`. | The physical-output oracle and pinned Unity transport are closed for this exact Avatar/clip pair. The closed order is base/rest -> 101 muscles and separate Motion/Root -> GetZYRoll -> compact conversion/root reference -> eight-pair TwistSolve -> compact-to-physical full TRS copy -> later per-component generic overlay. Current all-UI clips map none of the six extensions. Generalize only after another exact Avatar/clip fixture. Hand/TDoF-only branches, Motion object placement, baked/runtime IK, blending, constraints, and secondary simulation remain outside this oracle. |
| Explicit baked IK targets | Exact Grounder exports cover all 30 actors and prove PPtr equality from `IK_Foot_L/R_001` to `GrounderBipedIK.solver.IKFootBoneL/R`. Across 754 UI clips, only `FootIKWeight` is authored: 23 exact 60 Hz ACL arrays, all track 15 and constant one. `TryGetCurveValue` RVA `0x2F963C0` zeroes its out float and returns false on absent keys; `_UpdateFootIK` ignores the Boolean. Missing `FootIKFootWeight` becomes grounded target one through the native two-per-second persistent lerp, while missing `FootIKAdsorbWeight` becomes immediate one. The final pelvis recurrence is now exact: acceleration subtracts up to `0.8`, special-idle floor disagreement attenuates the target, ultimate skill snaps, Run/Sprint may rise at rate 8 otherwise rate 3, and air decays with `clamp01(360*dt)`. `_UpdateFootIK` does not clamp the result; `GrounderBipedIK.Update` separately clamps its live weight to `[0,1]`. Grounder self-init, delegate registration, `Grounding.Update`, bilateral `SetLegIK`, and post-solver order are source-closed; cross-MonoBehaviour/Animator frame chronology is not. Both installed full MovementSettings serialize `_ikLayers=0x00300000` (`Terrain|IK`); no installed modifier can override it. A complete 1,319,989-record original MonoBehaviour scan finds 80 `HGPrepareIKEffector` and 80 `HGTwoBone` constraints, all enabled but confined to 14 enemy and six cutscene/level-sequence containers, with zero playable/CharInfo containers. Native `HGTwoBoneIKConstraintJob.ProcessAnimation` is a real weight-gated `SolveTwoBoneIK` consumer, but it is not a recovered playable baked-marker consumer. The hand action serializes only mask/params/stop state; exData hand targets are external call-time Transform refs. All 16 direct exData creators leave them null, and the only two direct `StartCharLimbIK` calls are the left/right hand branches. No named, literal, serialized-component, or direct-call knee/weapon consumer is present in the current static build. | Do not implement Grounding until source-compatible terrain/ECS query fixtures, live controller values and cross-system frame chronology, C# profile consumption, the pelvis-aware foot-only solver surface, and numeric original-frame fixtures are present. Separately recover other quality/overstep/prediction/capsule branches, an observed indirect external hand-target provider, and any indirect/runtime-created/patch-delivered playable HG, knee, or weapon consumer. |
| Separated Motion/Root semantics | `MotionT/MotionQ` is character-object trajectory in clip space; `RootT/RootQ` is the absolute skeleton body reference in that same space, never a Motion-relative object delta. The original non-looping Wulfa dash directly witnesses the two same-scale absolute trajectories; SprintSP is an identity object cycle with a duplicated Root endpoint. Across all 390 decoded RootMotion streams, 106 clips move Motion and 380 carry Root; every one of the 91 looping clips duplicates its Motion endpoints exactly, so no current source fixture exercises nonidentity loop accumulation. Retail/public delta wrappers are instruction-exact after address normalization. Character Info applies only `worldQ = normalize(worldQ * animator.deltaRotation)` and never translation. Gameplay stores evaluated Animator deltas in `RootMotionData`; its divisor producer and `1e-5` accumulation versus `1e-4` accessor gates are closed. The `RootMotionModifier` manager is also source-closed: effective/default/list fields are at `+0x10/+0x18/+0x20`; default is `{scale=1,disableCliffCheck=false}`; the last surviving add wins; remove scans from zero and deletes the first matching ID; an empty list restores default. `_OnAnimatorMove` applies the effective scale to delta position and linear velocity, never angular velocity. Exactly five direct Add and two direct Remove callsites exist, and all direct Add callers pass `disableCliffCheck=false`. Translation is then yaw-warped through `VelocityMixer` toward the movement motor. | Higher-level divisor meaning, exact controller transition/interruption quaternion blending, non-identity cycle accumulation, indirect modifier callers, movement/collision/cliff gates, and final motor application remain open. The current all-looping corpus provides zero nonidentity accumulation witnesses, so that stage must not be guessed. `disableCliffCheck` is stored but unread in `_OnAnimatorMove`, so its downstream consumer remains unresolved. Gameplay GameObject root motion and generic `Animator.applyRootMotion` remain disabled. |

The new runtime-consumer proof is
`scratch/reverse_engineering/ik101_runtime_consumers/verify_ik101_runtime_consumers.py`.
Its deterministic report SHA-256 is
`1BE47AE4CFBDA89C3357BEF7A0524BBAA2EF2722C698A38155D0C6B9E86FA816`;
the verifier SHA-256 is
`DD5AEE1C0BAB124B004445D2AB442C7B5967C4CDC3C0D4E900F5D0977EF78DC5`.

Reproducible source-only audit artifacts are grouped under
`scratch/character_recovery/humanoid_2021_baseline/`,
`scratch/character_recovery/humanoid_avatar_basis/` (including
`get_zyroll_scaling.md`, `b17db0_twist_and_clamp.md`, and
`animator_update_scheduler_findings.md`),
`scratch/character_recovery/humanoid_runtime_101/`,
`scratch/character_recovery/ik_target_binding/`,
`scratch/character_recovery/ik_target_runtime/`, and
`scratch/character_recovery/root_motion_policy/`. They are investigation
evidence; this topic document remains the durable conclusion and recovery
queue.

A consolidated fail-closed replay of the extension tables, 11-DoF leg ranges,
`m_IndexArray[42+slot] -> customType 8 attribute -> ACL track` transport,
101-slot native stages, nine generic IK targets, and Motion/absolute-Root
semantics is
`scratch/reverse_engineering/humanoid_101_runtime/verify_humanoid_101_runtime.py`.
Its verifier SHA-256 is
`7B6071BBAADBC3FBDFA718BC9123DE601211354D3C2D0F4CA4A9841067A8C971`;
the deterministic `report.json` SHA-256 is
`5A1AA5BB8C32DE9C67CFF943532D64001AC4A117E8AEEC8F4A9DC544C4B0C61B`.
That consolidated transport verifier by itself did not close the final
retail-f5 physical-Transform oracle or invent a knee/weapon/hand consumer.

The stronger final-physical oracle is now
`scratch/reverse_engineering/humanoid_101_full_pose_replay/verify_full_pose_replay.py`.
It executes only allowlisted RVAs from the pinned retail bytes in private
emulator memory and writes
`full_pose_replay_trs.bin` (769,824 bytes, SHA-256
`3276498D97C516E83D1C0F7094754C9D7E2F3A5B448EBD8DBAFE01E1615FA115`).
Its guard counts are all zero. This supersedes the preceding oracle warning
for the exact Wulfa SprintSP fixture; it does not invent the open IK,
constraint, blend, secondary-simulation, or general live-skinning stages.
The pinned Unity transport and visible Wulfa skinning proof are generated by
`tools/build_wulfa_original_f5_full_pose_fixture.py`, verified by
`tools/verify_wulfa_original_f5_full_pose_fixture.py`, and wrapped by
`build_and_validate_wulfa_original_f5_full_pose.bat`. The runtime component is
`EndfieldOriginalF5FullPoseFixture`; both component and generated clip remain
explicit opt-in. The static verifier passes 28 checks and the pinned Unity log
SHA-256 is
`6B275369A68F57F043BE31FC1CDD2F174134BF7F5077D177CEA9F3852E24CDB8`.

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
`FootIKAdsorbWeight` occur in zero of 754 unique UI clips. Native lookup miss
is now closed as raw zero; `_UpdateFootIK` complements those two values to a
smoothed target one and immediate one respectively. Conversely, retail hand IK
accepts explicit
external interaction targets, sampled knee bend goals are null, and no weapon
consumer has been recovered. Authored hand/knee/weapon marker curves therefore
remain preserved but do not activate the lab solver.

The shipped Animation Rigging extension is now separated from that playable
foot path by exhaustive original-data evidence. A bounded-header scan of all
1,319,989 installed AnimeStudio MonoBehaviour JSON records recovered exactly
160 serialized extension constraints: 80
`HGPrepareIKEffectorConstraintJob` and 80
`HGTwoBoneIKConstraintJob`, all with `m_Enabled=1`. Source-scoped
`(CHK, PathID)` resolution against the 759,252,292-byte original asset map
places them in exactly 20 containers with eight records each: 14 enemy
postmodels and six cutscene/level-sequence prefabs, zero playable postmodels or
CharInfo assets. The native job is functional rather than dead schema:
`HGTwoBoneIKConstraintJob.ProcessAnimation` method 40732 at VA
`0x186AFF660` branches on positive job weight at `0x186AFF751`, multiplies the
position, rotation, and hint weights at `0x186AFF930/938/946`, and calls
`AnimationRuntimeUtils.SolveTwoBoneIK` at `0x186AFF9BF -> 0x18B148D48`.
Its zero-weight branch instead calls `PassThrough` three times for root, mid,
and tip. This proves a retail two-bone implementation for the recovered
enemy/cutscene rigs, not a source edge from playable `IK_Hand/Knee/Weapon_*`
markers. Runtime-created IL2CPP/IFix/Lua/network constraints remain outside the
serialized audit and are not ruled out.

Grounder's own activation/callback order is no longer the ambiguous part.
`GrounderBipedIK.Update` method 440594 at VA `0x183E5EA60` clamps the live
weight and is the sole current direct-E8 caller of `Initiate` method 440595 at
`0x183E5EBC0`. `Initiate` installs two `IKSolver.UpdateDelegate` instances in
the solver's pre/post update slots, calls `Grounding.Initiate` at
`0x183E5EEA4`, then sets its initiated byte at `+0x48`. The registered
`OnSolverUpdate` calls `Grounding.Update` before two bilateral `SetLegIK`
writes; `OnPostSolverUpdate` performs the later post-solve adjustments. The
same exhaustive direct-call scan finds no static E8 caller for the MonoBehaviour
`Update`, either delegate callback, or `CharacterLimbIKBrain.Update`, which is
consistent with Unity lifecycle/delegate or other indirect dispatch and keeps
their cross-Animator ordering outside static proof. Consequently gameplay has
a source-closed foot consumer and an externally targeted hand consumer, while
CharInfo-specific activation of those callbacks remains unproved. The lab must
continue to preserve all generic marker tracks and keep guessed non-foot or
CharInfo solver activation fail-closed.

The reproducible contract is
`scratch/character_recovery/ik_target_runtime/constraint_schema_scan.json`
(SHA-256
`C272249888931A7CAF29E444EAA14A969F4EA93126FD532464AF80B13AF5939D`)
plus `ik_target_runtime_contract.json` (SHA-256
`B4467A884CF226B7273CEAD3265A4329F8BC1C247DB0E0FCCF39DCC98251E6AF`).
`verify_ik_target_runtime_contract.py` hash-gates the installed binaries,
anchor CHK, complete asset map, scan report, metadata catalog, native mapping,
method VAs, branch/call bytes, and exact container set. The asset-map SHA-256
is `148415835F911FC94A634925C50C2D8B9A1CD4F5F141412F956CBB143805B6F3`.

The current managed/native boundary now identifies those external hand targets
precisely. `CharPerformExData` is type token `0x020032c8`, has 15 fields, and
ends with `leftHandIKTarget` / `rightHandIKTarget`; its only method is constructor
token `0x060155cf` at RVA `0x3C9D8A0`. `CharLimbIKAction.OnPlay` reads the two
references from `exData+0x48/+0x50` and passes them to
`CharPerformHandleBase.StartCharLimbIK` with limb selectors 2 and 3. The
constructor initializes lists and defaults at `+0x18/+0x28/+0x30/+0x34` but
does not author either target. The static upstream boundary is now closed more
tightly: current metadata has exactly six resolvable typed references to
`CharPerformExData`, no field owner and no `CharPerformExDataForMemoryPack`
type. The serialized `CharLimbIKActionDataForMemoryPack` surface contains only
`handMask`, left/right `HandIKParams`, and `stopOnActionEnd`; `HandIKParams`
contains only `blendTime`, `usePosition`, and `useRotation`. All 16 direct
`CharPerformExData` constructor callers were decoded with preserved object
aliases and none writes `+0x48/+0x50`. The sole direct caller of the external
`CharacterScriptedSystem.PlayPerform(..., exData, ...)` entry is
`ScriptedCharPlayPerform.Execute`; it constructs a default exData and changes
only `fixedTime`. Non-null hand targets are therefore call-time external
Transform references supplied through an indirect Lua/delegate/IFix or other
runtime caller, not fields baked into the perform configuration.

The weapon boundary is negative but equally explicit. Across the current
metadata there is no type, field, or method identifier containing a real
`Weapon...IK`/`IK...Weapon` token, and neither metadata nor `GameAssembly.dll`
contains an `IK_Weapon`, `WeaponIK`, or `IKWeapon` literal. An exhaustive direct
E8 scan finds exactly two calls to `StartCharLimbIK`, both from
`CharLimbIKAction.OnPlay` for hand goals 2 and 3. Combined with the serialized
component audit, no current static weapon-target consumer is present. This
does not exclude an unnamed indirect or patch-delivered consumer, so authored
`IK_Weapon_*` generic curves remain preserved and no weapon solver is enabled.

The `FootIKWeight` persistent recurrence is also closed for the installed
unpatched base path. On ground, acceleration adds
`0.08*min(abs(floorPredictTheta)-10,0)`, so it is a penalty of at most `0.8`,
not a boost. A special-idle branch attenuates the target from disagreement
among `m_floorFeetTheta`, `floorFeetThetaByFoot`, and
`floorFeetThetaByRoot`. Ultimate skill type 7 snaps to the target; otherwise a
rising Run/Sprint target uses rate 8 and all other ground transitions use rate
3. Air uses `clamp01(360*dt)`, normally clearing the persistent pelvis weight
in one frame. The method writes this possibly out-of-range value to both the
blackboard and `Grounder+0x18`; `GrounderBipedIK.Update` is a separate writer
that clamps the live component field to `[0,1]`. Static code proves the
blackboard update order but not the cross-MonoBehaviour callback chronology,
so the two writes are deliberately not collapsed into one final frame
equation. The decoded installed IFix payload is nonempty but none of its 30
target signatures is a Grounder, CharacterAnimationComponent, humanoid, IK, or
physical-pose method. A future network-delivered patch remains outside the
static proof.

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
systems: the current-build `CharUIModelMono`, the 38-field/68-method UI
model/deco owner, has no
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
family. Whiten's serialized overall Grounder weight is `0.348`; Da Pan and
Deepfin serialize zero component masks. Those masks are not runtime-authoritative:
`CharacterAnimationComponent.OnAnimationSetup` overwrites `Grounding.layers`
from `MovementSetting._ikLayers`. Both installed full settings,
`MovementSetting_Default` and `MovementSetting_Aglina`, serialize exactly
`3145728` / `0x00300000`, whose retail TagManager names are `Terrain|IK`.
The five installed modifiers, including `MSM_Lizhiyan`, have no layer-mask
field; installed Lua has no writer and the installed IFix target table contains
no matching writer. Runtime Grounding remains disabled because the lab does not own a
source-compatible terrain/ECS provider, carry the live controller values or a
proven cross-MonoBehaviour/Animator frame chronology,
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

The gacha entrance ribbon is now independently source-closed at the serialized
Timeline boundary. `PlayableDirector` PathID `3160965858571562263` points to
`gacha_char_zhuangfy_Effect` PathID `5154919875066767714` in CHK offset
`90946578`. `Control Track (5)` activates the separate
`Effect/P_fxui_zhuangfy_ui_overview_start_01_piaodai` GameObject from Timeline
time `0` through `4.5166666667` seconds and serializes post-playback state `1`
(`Inactive`). `Animation Track (3)` is bound to that root's Animator PathID
`2970826661772569879` and plays
`A_fx_ui_zhuangfy_ui_overview_start_01_piaodai2` with clip-in
`0.4833333333`. Its only curve is the effect renderer's
`material._TintColorAlpha`: it remains `1` until Timeline time
`2.0166666667`, reaches `0.1620350182` at `2.2666666667`, and reaches `0` at
`2.6833334128`. A companion track plays the full 78-transform ribbon-motion
clip on the child `GameObject` Animator with the same interval and duplicate
alpha curve. The standalone widget prefab root is active, but the full gacha
prefab's Actor `chr_0030_zhuangfy_deco_3` instance is already serialized
inactive before director playback; this is not a timed Timeline disable event.
None of its six directors or 35 extracted Timeline objects references that
root or its DefaultHG renderer. The exact extraction
and raw hashes are preserved in
`scratch/animestudio/zhuangfy_widget03_components/timeline_activation_contract.json`.
The maintained importer now consumes this exact interval, motion, alpha curve,
renderer, mesh, and three-material order; the strict verifier is
`python unity_endfield_graph_shader_lab/tools/verify_zhuangfy_piaodai_effect_recovery.py`.
The external owner is now source-closed in shipped `GachaCharCtrl` /
`GachaCharTLHelper` Lua: it instantiates the prefab, evaluates every child
director at authored time zero, then plays them after the rarity-6
`gacha_char_start_6` gate. That 60 Hz non-looping legacy clip has authored keys
through float32 time `3.0833332538604736`. Native IL2CPP closes
`UIAnimationTween.GetValue()` as the eased normalized value at field `+0x18`;
both `_SetValue` and `GetCurPlayingTime` multiply it by the clip length. The
shipped `DOTweenSettings` selects `OutQuad`, `Normal` update, and
`defaultTimeScaleIndependent=false`, while omitted `Play` arguments resolve to
start `0`, speed `1`, and clear-tween true. The Lua `2.6666669845581055` gate
therefore corresponds to normalized clip progress `0.86486499025667` and an
ideal uninterrupted scaled-tween elapsed time of about `1.9498779332` seconds,
not `2.666667` seconds of wall time. It then schedules the exact float32
`0.25` black-screen timer, giving a nominal time-scale-one sum of about
`2.1998779332` seconds. The follow-up clock and callback phase are now closed
from shipped framework Lua: `GachaCharCtrl` omits `_StartTimer`'s optional
`unscaled` argument, `UICtrl` forwards nil, and `TimerManager` therefore stores
the deadline as `Time.time + 0.25` in its scaled heap. `TimerManager` runs from
`LuaUpdate` `Tick`, processes the scaled heap before the unscaled and frame
heaps, and invokes the callback synchronously on the first Lua Tick whose
`Time.time` reaches the deadline. Native `LuaManager.Tick` reads `actionTick`
at `+0xa0`, and its unpatched frame-group getter returns group `6`. An exact
rendered frame is still not statically recoverable: DOTween's Normal tween runs
from `DOTweenComponent.Update` with `Time.deltaTime`, but the shipped data does
not serialize its cross-system order relative to the Lua frame-tick driver;
variable delta, time scale, stalls, coroutine observation, and first-eligible-
Tick quantization remain runtime inputs. The pinned verifier/report is
`scratch/reverse_engineering/zhuangfy_director_owner/build_gacha_timer_clock_report.py`.

The gacha-room parent and explicit startup call order are now source-closed.
`PhaseGachaChar` creates the shipped `GachaRoom.prefab`; its active, identity
`GachaRoom/TimelineRoot` Transform is the parent supplied unchanged through
`UtilsForLua.CreateObject(GameObject, Transform)` and the native instantiate
wrappers. There is no later root reparent. Zhuang's prefab root and all nine
direct children serialize active. After helper/light/volume/layer/UI-camera
setup, the helper samples the direct-child directors in authored order
Actor, Audio, Effect, Light, Others, each as `Stop -> time=0 -> Evaluate`, then
calls `TailTick(0)`. On the scaled 0.25-second timer callback it rebuilds all
five graphs, then performs `time=0 -> Evaluate -> Play` in the same order.
Effect is third: Actor and Audio are already evaluated/playing, while Light and
Others have not started. The three zero-start additive EntityVFX clips clone,
insert, and sample their materials synchronously inside Effect's explicit
`Evaluate(0)`. Engine Awake/OnEnable sub-order, active IFix replacement,
intra-Effect equal-time track callback order, and the first automatic Director
update relative to Lua group-6 Tick remain runtime boundaries. The pinned
contract is
`scratch/character_recovery/zhuangfy_gacha_start_order/zhuangfy_gacha_start_order_contract.json`
(SHA-256 `A95AE5584BEDD692D5E2B70A3C47913B5427A6E5000D7530844536AD947060BA`).
The exact selected dissolve/dither/MRT proof is pinned by
`scratch/reverse_engineering/vfxbasev2_temporal/build_vfxbasev2_temporal_report.py`.
The runtime target/allocation/attachment and previous-state producer overlay is
pinned separately by
`scratch/reverse_engineering/scenemv_runtime/build_scenemv_runtime_report.py`.

The rest of this gacha Effect is now source-inventoried rather than represented
by a generic "missing particles" label. The same original CHK contains seven
non-looping `EffectSetting` roots and exactly 70 `ParticleSystem` objects with
70 same-GameObject `ParticleSystemRenderer` objects: start `01_01` has 19,
`trail01` 8, `jianqiang` 11, finger lightning 3, `baofa` 19, and the rarity-six
root 10; piaodai is the separate skinned-mesh effect and has no particle
system. No `TrailRenderer` or `LineRenderer` is serialized. The visible trail
is implemented through ParticleSystem trail/stretched-renderer data. All
enabled stock modules, seeds, bursts, render modes, sorting values, custom
vertex streams, material/mesh PPtrs, and raw serialized hashes are indexed per
system.

The six particle-bearing roots now also have a maintained, source-closed Unity
import path rather than only an inventory. The generated contract is
`Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_particle_inventory.json`
(SHA-256 `DA24DA3875B0859E9DD806F7E0FC92566AB3CC0B5956D68CC35DA26B1308AB32`),
and `build_zhuangfy_gacha_particle_recovery.bat` runs the exact pinned
Unity `2022.3.62f3` importer plus strict validation. It emits six standalone
prefabs with all 92 source subtree nodes and 70 one-to-one
`ParticleSystem`/`ParticleSystemRenderer` pairs. Every generated node carries
its original GameObject and Transform PathID; this is required because the
original data contains duplicate sibling names that produce the same textual
hierarchy path. Local position, quaternion, and scale are applied from the
serialized source record, while every enabled stock module payload and stock
renderer field is written through Unity's serialized-property surface.
EffectSetting loop, duration, delay, and random-delay values remain explicit
source metadata on each prefab rather than being turned into an invented
lifetime controller.

The former shorthand "24 retail-only particle/renderer fields" was incorrect.
A public-`2021.3.34f1`/retail-`2021.3.34f5` binary and serialized-data
differential finds 25 selected names absent from the stock importer surface:
23 are Endfield-only, while `m_RayTracingMode` and `m_RayTraceProcedural` also
exist in public f1. The 26-name recovery whitelist has one member not present
on these 70 pairs, `m_TextureClipThresholdUpper`. The meaningful selected
values are now source-inventoried: all 70 enable per-renderer lighting, 66
enable character outline, eight request realtime-shadow casting, one uses
character index 1, and one uses submesh-render mode 1. Distance limiting,
cutout, UI rendering/sorting, and HG GPU instancing remain disabled/default in
this effect. Native disassembly closes the active semantics: per-renderer
lighting transforms the authored offset and publishes the HG lighting index;
character index is a four-bit renderer value with its validity flag; disabling
outline publishes the disable-outline backend bit; realtime shadow publishes
its backend mask; and submesh mode 1 uses signed modulo instead of clamping an
out-of-range submesh to the last slot. The pinned differential and value census
are `scratch/character_recovery/retail_particle_fields/retail_particle_field_contract.json`
(SHA-256 `BA4A7CB37BC3F8186AA105DE6B0043C7A26EFC866C2864347466D36A633AD02D`).

The active compatibility boundary is now source-closed as well. All eight
`m_RealtimeShadowCaster=1` rows serialize stock `m_CastShadows=0`, so mapping
the fork bit to public `shadowCastingMode` would be wrong. Character index is
consumed by HGRP character-shadow renderer-list selection and must not become a
material property. Per-renderer lighting transforms the zero offset/origin,
queries HG lighting, caches its index, and has no public light-probe equivalent.
The four outline-disabled rows should simply remain outside any recovered
outline list, as the current particle path already does. The sole
`m_SubMeshRenderMode=Loop` row has serialized static-batch `subMeshCount=0`, so
the native wrap/clamp gate is not entered and no compatibility behavior is
needed for this effect. Only the two public-f1/shared ray-tracing fields exist
on public Unity 2022, and both are zero here. The reproducible binary/data audit
is `scratch/reverse_engineering/particle_fork_fields/particle_fork_field_report.json`
(SHA-256 `7AF070C55F1D6CAA550B7C0A9AF4DC17AA18B01C4E17035BB96FC6214C2E2210`).
The particle importer now validates this exact census and refuses all public
substitutions.

The dependency side is equally strict: 60 path-ID-qualified materials, 14
decoded meshes, and 75 decoded PNG textures are generated; material and mesh
source JSON is copied byte-for-byte, and validation rechecks every decoded mesh
vertex, normal, UV, tangent, color, submesh, and index. All 651 source-gate
artifacts are size/SHA checked before a build. The saved assets pass both the
build-time round trip and a separate fresh-editor validate-only load. The
current validation report is
`unity_endfield_graph_shader_lab/scratch/character_recovery/zhuangfy_particle_runtime/unity_validation.json`:
Unity version `2022.3.62f3`, dependency aggregate
`59727CFE59D8A4475602D833A9810BE92A0A72E7A05E60FFEBC29841C54D1D5E`,
and generated-prefab aggregate
`FA958E5CF8D51DC911976694F7A958F3D120F215CE2A3511ACAA3A426DA1C347`.
The report records the exact active census (70 per-renderer-lighting rows,
four outline-disabled rows, eight realtime-shadow/cast-off rows, one
character-index-1 row, and one inert submesh-Loop row), passes the no-public-
substitution boundary, and has SHA-256
`BC49E901F3D599F80AFAE8D613DDE48BA82E474232C6B7469AE9E6F6EA6CD187`.

This is deliberately not a claim of final visual/runtime parity. Stock
`2022.3.62f3` does not expose the Endfield execution surface for the 25 selected
names outside the stock importer surface, including the one non-default
`m_SubMeshRenderMode=1` row; those exact values stay in the pinned contract and
are listed by the validation report instead of being approximated. The exact
selected shader variants are decoded, but their retail attachment/compositor
contract is not present in this public project. Every generated material
therefore preserves original name, material PathID, shader name/PathID, queue,
and source JSON but uses
`Hidden/Endfield/Recovered/VFXUnavailableFailClosed` (`ColorMask 0`). This
prevents the former default-white geometry without inventing shader semantics.
The exact parent metadata and Effect Timeline scheduling are now recovered.
EffectSetting runtime cull/LOD/lifetime control, execution of the active fork
renderer fields, and visible shader execution remain open implementation
boundaries.

The full `gacha_char_zhuangfy_Effect` Timeline has 16 tracks and ends at
`14.0333333333` seconds: seven Control tracks, four Animation tracks, and five
Entity-VFX tracks. The five Entity-VFX tracks all bind the same recovered
component on `Actor/chr_0030_zhuangfy_deco_1`; none targets the piaodai ribbon.
`tianshiyi_01/02/03` are three separate additive-material programs with
original materials, `6.3333335`-second duration, and the same authored
late-opacity falloff. `tianshiyi_jianqiang` is a fourth, two-second
additive-material program with its own pulsed opacity curve. The final
`tianshiyi_dissolve` is a distinct looping `0.7`-second dissolve program with
its original texture, edge sharpness `0.72`, emissive edge `0.07`, shadow-stop
delay `0.2`, and ray-tracing/shadow participation controls. Its Timeline clip
runs from `5.6` through `14.0333333333` seconds. This excludes a serialized
Timeline/EntityVFX MaterialPropertyBlock override of piaodai's selected
dissolve constants; native/global per-draw producers remain a separate
boundary.

This serialized Timeline/EntityVFX boundary now has a maintained generated
contract at
`Assets/EndfieldGraphShaderLab/Generated/OriginalData/Effects/zhuangfy_gacha_timeline_entity_vfx_contract.json`
(SHA-256 `38B4611DEB11E27E7D9ACC11B7EC4B9DE065C57A541AFF98C9EF2F705EE5872B`).
The builder reads the exact Timeline, director, prefab binding objects, four
AnimationClips, and five EntityVFX assets from the original decoded CHK
artifacts. It records all 16 one-clip tracks in source order with unrounded
start, clip-in, duration, extrapolation, playable options, PathIDs, and full
target hierarchy. The seven Control tracks retain their original particle
seeds and control flags. The five EntityVFX rows retain their complete
serialized `data` objects rather than a runtime translation, so every
additive opacity key and every dissolve/cutoff/loop/end/shadow/ray-tracing
field remains available for the separately recovered native handlers.

The contract resolves the four additive-material PPtrs, direct dissolve
texture, and the selected materials' transitive texture/shader PPtrs to four
materials, seven textures, and one shader with zero unresolved payload
dependencies. Its 100 decoded source/selection artifacts aggregate to
`9B41B19706006C9942C49B070F9798427089B71ABC33CD0BE0BBD478F914C67F`,
in addition to the separately verified original CHK SHA-256
`DB94219EE4F522A824C32EC979C2DC5BFD7B1013B4E45C18B77FB3AE4809694E`.
`tools/verify_zhuangfy_gacha_timeline_entity_vfx_contract.py` rebuilds the
contract from those sources and fails on timing, binding, payload, identity,
hash, or dependency drift. This remains a data-only contract: it does not
instantiate a Timeline, infer the director start frame, execute any EntityVFX
handler, mutate a material, or schedule the standalone particle roots. The
native-runtime contract below is the separate execution-semantics authority.

The installed unpatched native EntityVFX evaluator and Timeline sampler are
now source-pinned by
`scratch/reverse_engineering/zhuangfy_entity_vfx_runtime/build_native_runtime_contract.py`.
The generated contract SHA-256 is
`1F7AA6596130D65C2DDD6F99CCE7393FEE607E8942B9B4C001E48C9F82471AD5`
against metadata
`90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E`
and `GameAssembly.dll`
`0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`.
`EntityVFXCurveData.propertyType` uses the exact six-value
`UnityEngine.Rendering.ShaderPropertyType` order. Color `0` evaluates the
gradient times color intensity and writes a vector; Vector `1` evaluates four
curves and writes a vector; Float `2` evaluates one curve and writes a float;
Range `3` evaluates one curve, clamps it to its authored range, and writes a
float; Texture `4` evaluates four curves and writes scale XY plus offset ZW;
Int `5` shares the single-curve float-write path. This is backed by the
original compressed enum defaults and the six-entry native jump table at
`0x1850A31F8`, not by a lab enum approximation.

`EntityRenderHelperTimelineSampler.SampleVFX` stores one sample per asset name
and replaces it only when the incoming weight is strictly greater. The later
consumer uses the metadata and native constant `0.0010000000474974513f` and
the native `seta` comparison, so only `weight > 0.001f` is active; equality is
inactive. The downstream `EntityVFX._SampleVFX` path is now closed as well:
an inactive sample force-stops a controller that is still playing through
virtual slot 7, while an active sample starts a stopped controller through
slot 6 after resolving keyword conflicts and then always samples it. A lab
implementation must therefore clean up material/shadow state at or below the
threshold rather than merely skipping that frame's property write. The four
formerly anonymous calls in this path are now resolved as
the `IEntityVFXTimelineHost` `AddTimelineEffect`, `InitAll`, `ResetAll`, and
`SampleVFX` dispatch thunks, including their normal and ECS targets. The
dissolve state machine is also closed for the current unpatched
body. Start samples the start curves at
`Clamp01(passTime/duration)` and consumes `needInit` once. Loop samples the
loop curves only when `useLoopCurve && loopDuration > 0`; otherwise it samples
the start curves at `t=1` only when cutoff-Y is enabled and performs no write
when cutoff-Y is disabled. Stop samples end curves only for positive end
duration. Shadow participation stops once at
`passTime >= stopShadowCastingDelay` only while
`passTime < revertShadowCastingDelay`, passes the authored
`stopRayTracingMeanTime` bit, and restores only after
`passTime > revertShadowCastingDelay`; a direct time jump beyond the revert
boundary never issues the stop call. IFix may replace these bodies at runtime,
and no active patch payload has been captured, so this closes the installed
unpatched implementation rather than every possible patched session.

The same contract now pins the common controller state machine and the
additive-material controller rather than leaving their timing implicit. Play
clears all three clocks, enters start state, refreshes its tick origin, and
samples start immediately. Tick clamps the start clock at duration, enters
loop only when loop is enabled, enters a positive enabled end phase when one
exists, and otherwise final-stops. Timeline sampling uses start while
`time < duration` or loop is disabled; a looping sample uses
`Repeat(time-duration, loopDuration)`. Ending samples execute only when the
end curve is enabled with positive duration. The four Zhuang Fangyi additive
assets are a narrower source-closed case: each enables only its start opacity
curve, writes `_TintColorAlpha`, and has no authored dissolve, scan, cutoff,
custom, loop, end, or additive-property update channel. Their exact durations
are `6.3333335` seconds for `tianshiyi_01/02/03` and `2.0` seconds for
`tianshiyi_jianqiang`. All five Zhuang assets serialize renderer mask `-1`,
which the original `EntityVFXRendererMask` metadata proves is the exact `All`
value; the other flags are one-bit Normal/Body/Cloth/face/hair/weapon/part
categories, followed by `AlphaQuadAvoidAddMaterial`, `All`, and
`AllWithoutAlphaQuad`. A lab implementation may therefore address every
eligible renderer category below the bound
`Actor/chr_0030_zhuangfy_deco_1` host. Because every one of the four additive
assets enables its start curve, the original Play path clones the exact
referenced source material, passes the host/material/mask/customization tuple
to the normal or ECS `AddMaterialToAllRenderer`, retains the returned removal
handle, and gathers all inserted customized instances for later writes. The
lab should animate only `_TintColorAlpha` on those per-effect instances and
remove them by the retained handle on final stop. It must not spill the `All`
value into unrelated character/effect roots or invent extra curve behavior.
The exact renderer-helper selection is now closed. Native initialization walks
the helper-local inactive children, validates renderer/mesh/material state, and
creates one `RendererInfo` per accepted renderer. Type defaults to `Normal`
mask 1 and is replaced by only the first asset-authored contains/regex rule.
Application accepts an added record exactly when
`(rendererTypeMask & effectMask) == rendererTypeMask`. Therefore Zhuang's
`All=-1` includes alpha-quad generally; only
`AllWithoutAlphaQuad=0xFBFFFFFF` excludes type bit 26, with no separate alpha
branch. Zhuang's bound deco-1 helper has null `vfxAssets`, no renderer-type
configs or custom renderer lists, and exactly four accepted original
SkinnedMeshRenderers: widget LOD0, LOD1, LOD2, and LOD3, all default Normal and
all carrying one non-null source material and mesh. The maintained manifest now
imports all four and rebuilds the exact four-entry CrossFade `LODGroup` with
thresholds `0.4/0.1/0.02/0.01`, fade width `0.5`, animated cross-fading, and
source size/reference point. Four additive records overlap from
`3.4833333333333334` through `5.6`, exactly saturating the native cap. Native
rebuild takes matching active records newest-to-oldest, repeats each added
material per source material/submesh slot, and appends the originals last. The
runtime now reproduces that order across all four LOD renderers and restores
each original material/visibility state on stop. The deterministic contract is
`scratch/reverse_engineering/zhuangfy_entity_vfx_runtime/renderer_helper_material_contract.json`
(SHA-256 `AD5471C0C0C50BADA097857747C53616C1641CD58C09A9563D76B457415D8AFA`).

All seven previously unnamed rarity-six renderer-material curve attributes are
now resolved collision-free from the original clip, 12 decoded material
property sheets, the VFXBaseV2 shader metadata, and AnimeStudio's Unity curve
encoding implementation: `0x8FC071C4` is
`material._DisturbVIntensity1`, `0x8A1A9310` is
`material._DissolveScheduleOffset`, `0x8A3281C1` is
`material._TintColorIntensity`, and `0x09836958/0x19836958/0x29836958/
0x39836958` are `material._DisturbTex1_ST.x/y/z/w`. RendererMaterial
`customType=22` stores the property CRC in the low 28 bits, scalar in bit 31,
component in bits 28..29, and RGBA-versus-XYZW in bit 30. The ST tuple starts
at `(1,1,0,0)` and ends at `(1,1,0.4629737138748169,0)`; only offset X varies.
The source proof is under
`scratch/character_recovery/zhuangfy_rarity_curve_bindings/`. Joining every
renderer path to its exact runtime material instance remains a prefab-binding
step and is not inferred from the hash alone.

The three formerly unresolved binding CRCs `103164757`, `955800122`, and
`1182179166` are now source-classified as stale or removed clip bindings, not
missing live nodes. A complete pinned AssetMap scan finds 18 exact copies of
`P_fxui_gacha_char_guangxiao_rarity6effect_01` across nine characters and five
CHK files. Every copy has the identical 22 relative Transform paths and 19
renderer paths; all other unique clip path hashes resolve, while these three
are absent in all 18 copies. Each stale hash authors both Transform position
and `material._TintColorAlpha`, but no current GameObject, MeshFilter, Mesh,
Renderer, or Material dependency exists to bind. Their exact preimages are not
recoverable from CRC32 without guessing. The runtime's existing exclusion is
therefore the source-compatible behavior. The reproducible evidence contract
is `scratch/character_recovery/rarity_binding_crc/rarity_binding_crc_evidence.json`
(SHA-256 `1249D7654EA98F5D0D82CB01E464AA8D724E8B1FEE4D9AF060C9EC243E20DAB3`).

The complete direct dependency identity set for this effect is also closed:
60 selected Materials, 14 selected Mesh assets, 75 selected Texture2D assets
decoded to PNG, and three selected original shaders (`VFXBaseV2`,
`VFXRadialBlur`, and `VFXRefract`). The only identities absent from the game
AssetMap are original PPtrs into `unity default resources`; a clean public
2021.3.34f1 serialization oracle proves the matching stable IDs are Sphere
`10207` and Quad `10210`. This naming proof does not treat public f1 as a
retail-f5 behavioral oracle. The reproducible index, asset filter, exact
selected-output hashes, and honest implementation boundary live under
`scratch/character_recovery/zhuangfy_remaining_vfx/`; rebuild with
`python scratch/character_recovery/zhuangfy_remaining_vfx/build_report.py`.

The shader-side boundary is now exact rather than a generic "missing VFX
shader" label. All 60 material identities are hash-gated. The installed source
contains 58 `VFXBaseV2` materials using 14 signatures among 1,358 compiled
variants, one `_USE_MASK` `VFXRadialBlur` material among ten compiled variants,
and one `_USE_DISSOLVE` `VFXRefract` material among 178 compiled variants.
Sixteen selected non-instanced fragment variants decompile cleanly through
Ruri, and every one writes both `SV_Target0` and `SV_Target1`. Serialized Shader
state closes target-0 RGB/alpha blend factors, target-1 motion-vector blend
factors, ZTest, ZWrite, Cull, and the `ForwardOnly` versus
`Refraction`/Distortion pass split. Six exact material identities now admit
visible compatibility variants; the remaining 54 stay fail-closed.
`VFXBaseV2` uses the retail two-attachment ForwardOnly contract, while radial
blur and refraction use the scene-color snapshot, depth, and Distortion
attachments. That native pass contract is closed:
both pass families clone the incoming scene-color descriptor as target 0 with
DontCare/Store, first copy the old scene-color snapshot into it, keep that same
old resource alive as `_SceneColorTexture`, and attach sceneMV as target 1 with
Load/Store. ForwardOnly uses depth Read; Distortion uses depth ReadWrite. The
selected radial-blur/refraction fragments compose directly through serialized
material blending, so no later distortion-vector compositor is required. The
lab implements this selected attachment/resource lifetime with native render
passes rather than a color-only substitute. The current-build total order is
source-closed as GBuffer -> ForwardOpaque -> main ForwardOnly -> Distortion ->
gated Phase1 -> after-DOF ForwardOnly -> Phase2. Live RenderDoc attachment/pixel
validation and the opaque character's exact previous-frame skinned-position
target-1 producer remain open; exhaustive terrain/foliage/vegetation writers
are a general-world, not isolated-CharInfo, boundary.
The hash-pinned native contract is
`scratch/reverse_engineering/vfx_mrt_compositor/vfx_mrt_compositor_contract.json`
(SHA-256 `5E0466F7F76EF7A0BEBECDAD340BCF2506534E69558C7B4175E6039BEA2C8918`).
Unity `2022.3.62f3` represents the selected declarations through native render
passes, including read-only/read-write depth. The implemented path includes
the selected VFX target1 equations/indexed blend state, explicit depth
ownership, pinned fullscreen copy, and scene-color handle chain through
post-processing.
The older 12-input-pinned assessment that identified those implementation gaps
is retained at
`unity_endfield_graph_shader_lab/scratch/character_recovery/vfx_mrt_lab_gap/vfx_mrt_lab_gap.json`
(SHA-256 `9BB24FFC1C6FAF795B53C11D75904E47F1C45D657FA638D2EB581A1DF6F6977B`)
as pre-implementation evidence rather than current status.
The reproducible variant report is
`scratch/character_recovery/vfx_shader_variants/vfx_shader_variant_report.json`
(SHA-256 `FBCEFB4C44EC3D06CDAB01B01C94712F790479C7FF06E072A62736D462438258`);
its selected decompile aggregate is
`EE3DA63AF1468E124E33E2BB88FE4183F2CCAA0352123BA3FAB316D17132E860`.

The retail standard-renderer LOD-fade ABI is now closed through the installed
`UnityPlayer.dll`, and a prior record-layout ambiguity is corrected. The
manual and camera enable setters at `0x180430880` and `0x180430700` modify bits
17 (`0x20000`) and 18 (`0x40000`) in the first dword of each 24-byte renderer
source record. The record array begins at component `+0x14`; `+0x14` is not a
field within each record. A manual renderer has its enable byte at `+0x236`
and signed custom value at `+0x238`. `0x1804DB750` clamps the magnitude away
from the three ambiguous endpoints using `[0.001,0.499]` or `[0.501,0.999]`,
truncates `magnitude*65535` to a ushort, and emits mode 2 for positive or mode
3 for zero/negative. `FlattenBasicData` at `0x180339740` stores the ushort at
flattened row `+0x178` and mode at `+0x17A`. `SetupLODFade` at `0x1803DA2E0`
reconstructs `lodFade.x = signed(packed)/65535` and
`lodFade.y = signed(packed & 0xF000)/65535`; mode 3 negates both. Thus zero is
the minimum negative custom fade, not disabled. The disabled producer value is
the independently repeated retail `(1000,0,0,0)` sentinel: custom per-draw
jobs use `1000.0` when no transition is active, and the particle instance
helper at `0x181437D40` writes the same vector.

The selected Zhuangfy EffectSetting actually enables distance LOD, correcting
the older “distance LOD disabled” wording. It has only one tier at distance
`0` with `framePercent=1`, disables culling and auto-fade, and has no serialized
stock `LODGroup`. All three piaodai materials serialize instancing disabled.
Their selected Vulkan SPIR-V pairs (`0063/0065` and `0081/0083`) declare no
`InstanceIndex` or `BaseInstance`; each binds one `PerDrawBaseData` block at
set 2/binding 0 and reads member 1 `.xy` at byte offset 64 directly. Across the
2,716 decoded family programs, 679 of 1,358 vertex variants instead declare
`InstanceIndex`; the boundary is the `SRP_INSTANCING_ON` keyword. Reference
pair `4077/4079` indexes a 256-entry `PerDrawBaseData` array in the vertex and
forwards the chosen uint flat at location 5 so the fragment reads the same
member 1 `.xy`.

The particle instance helper at `0x181437D40` independently loads
`(1000,0,0,0)` from `0x181E429C0` and stores it at instance-record `+0x40`
(`0x181438156`), byte-for-byte matching the shader member offset. The lab binds
that exact retail neutral/default payload through `_RecoveredLODFade` and now
executes the selected piaodai position hash, signed threshold, coverage, and
alpha-tail equations. `EndfieldRecoveredLodFadePacking` preserves the signed
custom-alpha path for a future source-proven owner; it does not invent an
uncaptured manual-alpha transition. A targeted Unity `2022.3.62f3` rebuild and
a separate fresh-editor validation both pass for all three saved non-instanced
materials, the serialized sentinel, queue 3700, indexed target-1 blend, and
the exact `ExactSelectedPiaodaiThree` sceneMV admission tag. The maintained
D3D12 MRT probe renders the 2,046-vertex ribbon against a renderer-disabled
control: 7,571 pixels change with absolute RGB difference 1,327,352, while
the compositor reports active and the log contains no shader, compiler, or
render-pass error. The recovered image contains the three expected separated
translucent ribbon layers; the report and captures live under the
self-contained project path
`unity_endfield_graph_shader_lab/scratch/character_recovery/zhuangfy_piaodai_mrt_probe/`.
This closes the lab attachment/draw execution, not pixel parity against a
captured retail frame. Runtime EffectSetting/manual renderer alpha at a
particular retail frame remains capture-dependent.

The separate custom-job boundary is now closed as non-applicable to the
selected non-instanced shader, without claiming the job's broader family name.
Variant `0x181064100` appends a 16-byte
intermediate record `{uint32, signed transition float, component-record+4
pointer}`. Addresses `0x181064D8D..0x181064E1A` prove bytes `8..15` are one
pointer. Downstream `0x18106C6C0` copies the transition float into 96-byte
output record `+0x4C`; `0x18107AE60` submits output `+0x30`. D3D12 callback
`0x180820670` reads command field `+0x1C` and supplies it as
`startInstanceLocation` for both indexed and non-indexed draws, proving that the
raw scalar bits reach API `startInstance`.

The selected source object is a 32-bone serialized `SkinnedMeshRenderer`.
Nearby public `2021.3.34f1` PDBs name
`SkinnedMeshRendererManager::TryPrepareStandardRenderer` at stock RVA
`0x425CD0`; width-4 mnemonic-shingle matching ranks installed-fork
`0x180509A70` first at `0.460348`, versus `0.239224` for the runner-up. The
custom job is separately installed by function pointer at `0x18107E4A6`.
Most importantly, both selected vertex DXBC signatures expose no
`SV_InstanceID`, and all four equivalent piaodai SPIR-V programs expose neither
`InstanceIndex` nor `BaseInstance`. API `startInstance` therefore cannot become
a selected shader input even if a selected draw traversed that job. The exact
custom renderer-family purpose remains open engine-wide, but is no longer a
selected piaodai captured-frame dependency. The hash-pinned verifier/report is
`scratch/reverse_engineering/piaodai_renderer_route/` (report SHA-256
`BF994366BF8EEA078FF4848D804CE3347D6EAC0C6B8A66ED82A80B8B7C7638D9`);
the lower-level record contract remains
`scratch/reverse_engineering/lodfade_component18_reader_20260724/custom_job_lane_contract.json`.

The strict Zhuang-only execution layer is now implemented by
`build_zhuangfy_gacha_runtime_recovery.bat`. It generates a real 16-track
Timeline and bound runtime prefab from the four pinned contracts: seven
particle Control tracks, four Animation tracks, four additive-material
handlers, and one dissolve handler. The runtime preserves the native
highest-weight `> 0.001f` gate (equality is inactive), force-stop cleanup for
an inactive playing controller, four-record/newest-first material rebuilding,
per-effect cloned-material removal, `_TintColorAlpha` writes, dissolve
start/loop sampling, and the exact shadow stop/reset window. It also reproduces
the Effect helper's source operations: initial `Stop -> time=0 -> Evaluate`,
then after the scaled `0.25`-second deadline
`RebuildGraph -> time=0 -> Evaluate -> Play`. Public Unity 2022 does not call
the custom EntityVFX `ProcessFrame`
after the initial stopped evaluation, so the compatibility layer dispatches
only the three exact zero-start definitions; those definitions are resolved by
the original clip-PPtr -> playable-asset -> EntityVFX-PPtr -> source-object
chain, not by mutable Timeline display text. Unity `2022.3.62f3` build and a
separate fresh-editor validation-only load pass. The emitted report at
`scratch/character_recovery/zhuangfy_gacha_runtime/unity_validation.json`
records 16 tracks, four generated clips, four exact eligible renderers, four
additive handlers, one dissolve handler, nine rarity binding renderers, and
three deliberately excluded stale/removed binding CRCs. All strict booleans
pass under `2022.3.62f3`; the report SHA-256 is
`F8AAA54CDE4EF893D8B3ECBAE541A6CC6CA507197A566C311B0CF893F3CA0C9A`.

This does not close final visual parity. The exact captured-frame
`HGCamera.exposureAdaptation` value/history, captured-frame EffectSetting or
manual-alpha override and resulting `PerDrawBaseData.lodFade.xy`, the forked
engine's physical skin-buffer schedule, exact execution of the active
Endfield particle/renderer extension
fields, active IFix payloads, engine Awake/OnEnable and first automatic-update
chronology, native renderer-helper alpha-quad eligibility, and implementation
of the remaining particle/trail/entity variants remain open. The three
stale rarity paths remain deliberately unbound. The fail-closed shader exposes
only the source-animated properties needed to execute curves while keeping
variants without a compatible retail attachment contract invisible.

The shipped main UI AnimatorController JSON is now joined for all 30 actors.
Every controller has one full-body blend layer, 40 states, and 31 serialized
state transitions. The exact `Overview.FromOveview` entrance and
`Overview.OverviewIdle` handoff are published roster-wide, including the
AnyState destination offset, exit time, transition duration, fixed-versus-
normalized duration flag, destination offset, interruption source, and source
JSON path. Both fixed-second and normalized-duration Overview handoffs occur,
so treating every transition duration as normalized is incorrect.

The current installed native UI-model route is now closed for state entry and
private-deco synchronization. The evidence is pinned to `GameAssembly.dll`
SHA-256 `0c557367...d80ffce`, metadata SHA-256
`90c58e26...0adf97e`, and CodeRegistration `0x18b9217d0`; the maintained
verifier checks eight bounded method bodies in
`overview_animator_native_recovery.json`. In the unpatched bodies,
`CharUIModelMono.PlayAnimatorState(string, layer, normalizedTime)` preserves
the canonical name, hashes it with `Animator.StringToHash`, and calls the hash
overload. That overload plays the identical state hash, layer, and normalized
time on the body Animator and every loaded private-deco Animator. Retail
widgets therefore follow matching controller state paths; they are not
independently suffix-timed clips. When `tickStart` is true, `Tick` evaluates
every deco's body-Animator float at its `hideCurveHash` and calls
`SetVisible(0.1f > value)`. This closes the native activation consumer and
visibility threshold. The installed upstream producer is now source-closed as
well. `CharInfoSwitchChar.Execute` is an IFix-gated (`0x85AD`) guide action,
not an Animator owner: its unpatched body resolves `_charId`, reads
`PredefinedEventKeys.GUIDE_CHAR_INFO_CHANGE_CHAR` at the metadata-verified
instance offset `0x428`, and calls `EventManager.SendGlobal<string>`. The Lua
subscriber `CharInfoCtrl.GuideChangeChar` resolves and scrolls to that actor,
then enters the same `_ChangeSelectIndex` path as a normal head-cell click.
That path publishes `CHAR_INFO_SELECT_CHAR_CHANGE`; `PhaseCharInfo` removes the
old `PhaseCharItem`, asynchronously creates one replacement model, and writes
`FromIndex`, `ToIndex`, then `EnableSwitch`. `PhaseCharItem` applies those
integer/trigger values to the body Animator and mirrors them to all private-
deco Animators through `DecoItemSetInteger`/`DecoItemSetTrigger`. This directly
proves that the resident 30-actor lab is a loading optimization rather than
retail lifecycle emulation.

The original Lua group is pinned to VFS chunk SHA-256
`94deb75b...e3cb06df` (version `22097503`, 1,291 declared files); all 1,290
extracted Lua files were audited. None calls `PlayAnimatorState`, and the sole
`PlayAnimByState` occurrence is its unused definition. A direct native xref
scan likewise finds no normal caller of the string overload; the hash overload
has only the string overload's internal call at `0x186C27DD1`. Character Info
Overview is therefore parameter-driven in the installed sources. Any external
`PlayAnimatorState(state, layer, time)` producer remains behind reflection,
XLua/serialized dispatch, or IFix rather than a recoverable direct Lua/native
caller. `verify_charinfo_switch_owner_recovery.py` checks this event field,
encoded method specifications, Lua ownership chain, full-Lua negative result,
and direct-xref boundary against the pinned installed build.
`_ResolveCanonicalStateName` is pass-through in the unpatched body; all mapped
methods retain their IFix dispatch gate. The current Persistent target table
contains neither `CharUIModelMono` nor `CharInfoSwitchChar.Execute`, so these
unpatched bodies are the installed implementation; only a later or separately
delivered table remains an external-state boundary. `ActiveRotationRootMotion` registers the
Animator-move callback, whose body post-multiplies only `deltaRotation` and
never consumes `deltaPosition`.

All 30 Overview AnyState selectors use the same conditions:
`FromIndex == 0`, `ToIndex == 0`, and `EnableSwitch == true`. Every handoff
uses interruption source `2`, ordered interruption, and root-motion blending;
four durations are fixed seconds and 26 are normalized. These flags and the
three entry conditions are now serialized on the lab playback component as
evidence. Legacy `Animation` still cannot reproduce their Animator
interruption behavior. The 30-resident horizontal lineup remains a lab loading
optimization: camera-only selection does not claim the retail client keeps 30
`CharUIModelMono` instances resident.

Private-deco controllers are also joined to body controllers by exact state
path and clip PPtr. The current generated controller audit proves 436 imported
body+item state compositions across Overview, weapon, equip, skill, document,
upgrade, formation/team, and relax families. Remaining suffix-only pairings
stay labelled `source_inferred`. Suffix matching is not enough to establish that two
companion variants may be layered: recovered states reject any combination
whose clips write the same exact transform or active-state channel. The
current item audit contains 938 recovered companion layers and 257 multi-layer
states across seven actors, with zero admitted exact-channel overlaps;
ambiguous conflicting variants remain separately selectable evidence instead
of being played together.

The current installed Character Info secondary-dynamics generation is now
identified and bounded from original data. It is the game's
`BeyondDynamicBone.dll` fork, not the stale `MagicaCloth.BoneCloth` schema
found in an older Wulfa chunk. The current postmodels contain 50
`BeyondBoneCloth` owners and 115 colliders across the four high-priority
actors: Last Rite has 7 cloths/15 capsules, Wulfa 11 cloths/18 capsules/6
spheres, Zhuang Fangyi 13 cloths/25 capsules/1 sphere/3 planes, and Li Zhiyan
19 cloths/44 capsules/3 planes. Every root and collider PPtr resolves to the
current generated hierarchy. All 50 use BoneCloth type 1, AnimatorLinkage
update mode 10, simulate weight 1, blend 1, ability LOD 2, LOD threshold 9,
LOD fade 2, camera-culling mode 30, distance culling disabled, and prebuild
disabled. Per-owner gravity, pose ratio, reset thresholds/flags, wind,
springs, constraints, selection data, roots, and collider membership remain
individually pinned rather than generalized. In particular, Li Zhiyan's 19
cloths use reset threshold `0.03` (16 enable the reset flag), while the other
three actors generally use `0.01`.

The native Character Info bridge is closed at the same installed
`GameAssembly.dll` and metadata hashes as the Overview owner recovery.
`CharUIModelMono.OnAwake` caches both `BeyondBoneCloth[]` and legacy
`MagicaCloth[]`. During `Tick`, `_UpdateMagicaClothWeight` reads the Animator
float `MagicaClothWeight`: a nonzero absolute value targets 1 and zero targets
0; it approaches the target at 8 units/second upward and 6 units/second
downward, and only publishes after a change of at least
`0.001000000047`. Publication calls
`BeyondBoneCloth.SetClothSimulateWeight` for every current cloth and mirrors
the same weight to any legacy cloth. All four current Overview controllers
author the exact idle value `0.01`. A full audit of all 68
`CharUIModelMono` methods finds no other direct secondary-system call and no
cloth-specific release/suspend shortcut.

Component and manager ownership are also source-bounded. Cloth `OnEnable` /
`OnDisable` call `Process.StartUse` / `EndUse`; `Start` initializes, removes
monitoring, and auto-builds; `OnDestroy` disposes. Collider start/enable/
disable/destroy register, toggle, and remove their entries through
`ColliderManager`. `MagicaManager.Initialize` initializes Cloth, PreBuild,
DynamicBoneTransform, Team, VirtualMesh, Render, Collider, Simulation, Time,
and Wind managers in that exact order, then installs seven custom PlayerLoop
delegates spanning early, fixed, update, pre-late, late, delayed, and
rendering stages. `ClothManager.ClothUpdate` invokes
`WindManager.AlwaysWindUpdate`. The current `charinfochar.prefab` environment
exports 241 MonoBehaviours but contains no cloth, collider, or wind-zone
component, so the selected postmodel owns local cloth/colliders and any global
wind input remains external. The installed Persistent IFix table does not
replace `CharUIModelMono` or `BeyondDynamicBone`, so these unpatched bodies are
the current installed implementation.

`secondary_dynamics_owner_recovery.json` pins the raw source hashes, exact
serialized owner/collider records, native bodies/constants, lifecycle and
manager call surfaces, current Character Info environment, and IFix boundary.
Rebuild and verify it without launching Unity with:

```bat
cd unity_endfield_graph_shader_lab
python tools\build_secondary_dynamics_owner_recovery.py
python tools\verify_secondary_dynamics_owner_recovery.py
```

This closes ownership and orchestration, not the numerical solver. The seven
PlayerLoop category/anchor string pairs and before/last placement booleans,
Burst job numerics and writeback, cross-frame scheduling, global wind state,
and original numeric output fixtures remain unrecovered. The lab therefore
keeps secondary-dynamics execution disabled rather than substituting a
look-alike solver.

### Playable skeletal-morph ownership and neutral pose

The installed NPC `PrefabInfo` records now provide exact face/ear avatar
ownership for every playable actor. All 30 playable NPCs name one
`FacialMorph/Avatar/...` asset and serialize `disableBlink=false`; Wulfa and Li
Zhiyan additionally name their exact `EarMorph/Avatar/...` assets. Across the
roster there are 30 face and six ear avatars, and every serialized base-pose
bone resolves uniquely on the primary postmodel skeleton. Spell/proxy NPC
records with empty morph fields remain intentionally separate and are not used
as playable-avatar fallbacks.

The native evaluation order is also source-closed at the skeletal-morph job
level. `EvaluateMorphToBoneJob.Execute` starts from the avatar's serialized
`basePoseConfig`, accumulates each active mapping's position, Maya-Euler
rotation, and scale, and `_ApplyBoneToTrans` writes local Transform values.
`SkeletalMorphUtils.FromMaya` at current `GameAssembly` VA `0x187098dbc` is:

```text
AngleAxis(-z, forward) * AngleAxis(-y, up) * AngleAxis(x, right)
```

Normal evaluation interpolates from the base pose; the additive route adds
position/scale deltas and composes rotation. Blink and animation jobs sample
their own native curves and multiply weights before the same mapped-bone
writeback. `SmoothWeight` uses the native `JobMathf.SmoothDamp` path and snaps
the exact endpoints. This proves that raw postmodel bind transforms are not
the retail neutral facial pose: the roster audit finds 357 base-pose values
over `1e-4` from the imported rig across 26 of 30 characters. Li Zhiyan alone
resolves 91 facial and six ear neutral bones.

The lab now imports those exact NPC -> avatar -> base-pose bindings into
`EndfieldRecoveredSkeletalMorphBasePose` and restores them after body
`Animation` sampling. The saved 30-resident scene was rebuilt from the current
prefabs under pinned Unity `2022.3.62f3 (96770f904ca7)`. Its strict validator
passes with 30 active/resident actors, no runtime model load on selection,
2,680 morph-bone bindings, six ear-avatar owners, and 30 blink-eligible face
owners. A fresh isolated render pass also succeeds for all 30 actors, including
Li Zhiyan, Last Rite, Wulfa, and Zhuang Fangyi. Evidence and the fail-fast
ownership verifier live under
`unity_endfield_graph_shader_lab/scratch/character_recovery/facial_morph_runtime/`.

This is deliberately a neutral-pose executor only. It does not invent live
emotion, speech, look-at, or blink weights. Those layers must reuse the exact
per-avatar control map and native evaluation order; applying an approximate
Unity blendshape or body-clip curve on top would erase the source boundary.

### Current-retail automatic facial blink owner

The baseline automatic-blink chain is now source-closed for Wulfa and Li
Zhiyan in the current installed retail build. `NPCUnionAnimtor.PlayNormalEmotionPose`
reads `DialogUtils.s_defaultEmotionTag`; the retail `DialogUtils..cctor`
constructs that static tag from the encoded original literal
`FacialMorph/Emotion/normal01`. `SkeletalMorphUtils.LoadEmotion` and
`SkeletalMorphDefine.GetEmotionPathByTag` then resolve the original root and
format string to:

```text
Assets/Beyond/DynamicAssets/GameData/SkeletalMorph/SkeletalMorphAnim/
Emotion/data_facialmorph_emotion_normal01.asset
```

That `SkeletalMorphEmotionSO` serializes a 3-second interval, a 1-second
positive random range, blink speed 1, and a PPtr to
`data_facialmorph_anim_blink_02`. The blink asset is a 0.5-second,
non-additive, non-override clip with symmetric brow-down curves and four eye
curves (`eye_thinkcloseeyes_a_{L,R}_ctrl` and
`eye_scale_d_{L,R}_ctrl`); its mouth, other, and ear curve arrays are empty.
Wulfa's and Li Zhiyan's original avatar configs both serialize
`disableBlink=0`. The native `NPCCPUAnimator._InitMorph` branch calls
`SetBlinkTrackEnable(!disableBlink)`, so the `SkeletalMorphCore` blink tracker
type 10 is active for both. The shared clip is evaluated through
`EvaluateBlinkTrackJob._EvaluateBlinkCurve` against each avatar's own
control-to-morph map; it is not a per-character Unity `AnimationClip`.

`_UpdateAutoBlinkRandom` advances only after its core, current-track, and
pause-auto-blink gates pass. On zero/expired cooldown it starts tracker 10,
resets the elapsed counter, increments the shared blink/speye random index,
and stores the next cooldown in `[interval, interval + randomRange)`. The
generator is the recovered custom uint32 hash and mantissa mapping, not
`UnityEngine.Random`; from a new zero index the normal-emotion sequence begins
`3.8589806557`, `3.6475110054`, `3.8080667257`, and `3.4286868572` seconds. A
new core's zero cooldown permits an immediate first eligible update, while an
already-running emotion retains its scheduler state unless the transition
caller requests immediate blink behavior.

Dialog mute-auto-blink tracks are a separate authored override.
`DialogMuteAutoBlinkPlayableBehaviour.OnManualFixBehaviourPlay` forwards
`pause=true` and `_stopCurPlaying` through
`DialogTimelineManager.SetAutoBlinkPause`; its pause callback forwards
`pause=false`. These tracks suppress/resume the scheduler and may stop the
current tracker; they do not own the normal emotion or blink curve. A pinned
original `dlgtl_e6m1_9_sub_1` sample serializes `_stopCurPlaying=1`,
`_muteAutoBlink=1`, and `_muteSpeye=1`.

The current evidence and fail-fast verifier are under
`scratch/reverse_engineering/facial_blink/{report.md,report.json,verify.py}`.
They pin the current retail binary/metadata hashes, exact native method
indices/VAs, encoded literals, serialized asset hashes/PPtrs, both character
enable flags, selected full curve values, interval sequence, and the
independent dialog-mute sample. The lab now executes this exact tracker-10 path
for Wulfa and Li Zhiyan only. `EndfieldRecoveredAutomaticFacialBlink` runs
after the neutral base-pose layer and before the generic named dialog track,
evaluates the six original `blink_02` controls through each actor's own mapping
(50 Wulfa and 38 Li AvatarData bone deltas), permits the immediate first blink,
uses the recovered per-core `[3,4)` random scheduler, returns fully to neutral
at 0.5 seconds, and exposes the original dialog pause/resume/stop API. Both
Streaming evidence assets and the hash-different Persistent mirrors used by
the neutral executor are pinned; their base poses and six selected mapping
payloads must be semantically byte-identical. The other 28 roster actors remain
ineligible, and no synthetic controller nodes are created. The 25-check source
verifier and pinned Unity validator pass. The contract SHA-256 is
`5A774BFCF82E08E9161FE387FA9410A037F89EFA6A91157EAE7EB14990C1178C`;
the Unity log SHA-256 is
`FF3B19871719134CF61EBB19E54ECE9DA4E6567B443E6A85211852BFDA2A5595`.

### Retail facial curve producers and merge order

The original dialog path is a custom named morph-playable chain, not ordinary
Unity float-curve binding and not a requirement to reconstruct a hidden
296-Transform controller hierarchy. `DialogSkeletalMorphTrack.CreateTrackMixer`
(method index 62479, VA `0x186E03E38`) configures the dialog morph assets; its
sample generator (index 61663) reads the backing AnimationClip name/length.
`PrepareFrame` (index 62064) calls
`DialogTimelineManager.SampleNPCMorphAnimAtTime` (index 63860) and
`_DoPlayNPCMorphAnim` (index 63857), which resolves the
`SkeletalMorphAnimSO`, calls `NPCUnionAnimtor.PlayMorphAnim`, and reaches
`SkeletalMorphCore.PlayAnim` (index 80201). That final path converts named
curves to native tracks through `ToNative/_SetWriteableTracks`.
`FMorphCtrlCurve.Create` (index 492223, VA `0x183B04FB0`) explicitly calls
`Animator.StringToHash(ctrlName)`, closing the runtime control key.

The raw optimized companion clips are still real evidence. Li's face clip has
296 unique anonymous Transform path hashes, all with local-position vectors:
888 scalar channels close exactly as 60 streamed plus 828 constant. Li's ear
clip reuses the same 296 hashes and adds local rotations on ten paths: 928
channels close as 90 streamed plus 838 constant. Wulfa's face clip has 272
paths and 816 channels (111 streamed plus 705 constant); those hashes are an
exact subset of Li's, and Li's 24 additional hashes equal the 24 authored
non-neutral ear-control count. These editor-only path strings may serve another
evaluation subsystem, but they are not the recovered dialog binding key.

The avatar topology independently matches those counts. Li has 272 Transform
face controls plus two shader pseudo-controls (`EmotionBlend` and
`EmotionIndex`), and 26 ear controls split into two neutral baselines plus 24
non-neutral controls. Wulfa maps 267 of the standard 272 face slots; the five
absent mappings are the injured left/right brow, injured left/right eye, and
injured mouth controls. All serialized mapping `nameHash` values equal CRC32 /
`Animator.StringToHash`, but Li's 503-entry body Avatar `m_TOS` has zero overlap
with the anonymous controller-path hashes. Li's named semantic namespace is
already complete: 272 face controls plus 24 non-neutral ear controls give 296
unique names. The six top-level asset-map rows named `FacialMorphCtrlGO` are
MonoBehaviour track assets rather than GameObjects, and the selected track
serializes `m_GameObject=null`. Li's renderer-helper prefab contains 514
ordinary transforms, no facial-control nodes, and zero overlap with the 296 raw
clip hashes. Neither source justifies synthesizing a `FacialMorphCtrlGO`
Transform tree.

The fork Animator binding path now narrows that boundary. UnityPlayer's
separate 866-entry icall table maps `CreateMorphBindings_Injected` to
`0x1801697C0`, `CreateMorphBindingsByNameLst_Injected` to `0x180169D30`,
`EnableMorphBindings` to `0x18016A660`, `set_morphAvatar` to `0x180172000`,
and `Internal_GetMorphBoneIds` to `0x180176B10`.
`CreateMorphBindings_Injected` consumes an explicit ordered `Transform[]`,
reads native instance IDs, and builds a 112-byte animation Transform RW handle;
it does not calculate clip path hashes or recover controller names. Retail
`SkeletalMorphComponent._SetupMorph` at `0x1842F61A0` obtains the existing
Animator from `BaseModelComponent.model`, loads the actor's
`SkeletalMorphAvatarDataSO`, creates the core, and calls `_StartMorphCore`.
That method builds the body Transform array from `basePoseConfig`,
`allBoneNames`, `boneNameHash`, and `boneID`; it still does not construct or
serialize the optimized facial-controller hierarchy. Li's SOs contain 274
face mappings (272 Transform plus two shader) and 26 ear mappings; Wulfa's
contain 269 face mappings (267 plus two shader) and 26 ear mappings. Their
referenced Avatars match the actor body conversion path, not the 296/272 clip
controller table. The implementation and current GameAssembly/UnityPlayer
function slices are hash-pinned: UnityPlayer is
`B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2`,
GameAssembly is
`0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE`,
the `CreateMorphBindings_Injected` slice hashes to
`608CBAD50969B84D080C335BC0F6846B6D2B9AB8C8E7FDA9146EA51BBE9BC31D`,
and `_SetupMorph` to
`772345D0AB085B8F9A15D8BBAFECEE9455B322E5C5893C47FB94FB9819F452B6`.
Importantly, this proves why the native morph binding API cannot be used as a
guessed path-hash resolver.

A second source path remains explicit and named: `SkeletalMorphAnimSO` stores
scalar `MorphCtrlCurve` records such as brow sad/offset, eye close, and mouth
tsundere controls with exact Hermite keys. Native `SkeletalMorphCore.PlayAnim`
at `0x183b02580` calls `SkeletalMorphJobUtils.ToNative` and
`_SetWriteableTracks`, proving that these authored curves become native tracks
rather than ordinary Unity float-curve playback.

The lab now executes one exact fixture through that named path:
`dlgtl_e10m2_5_sub_1_npc_chr_0030_zhuangfy_2`. Its original
`SkeletalMorphAnimSO` is 2.15 seconds long and contains 12 explicit controls
(four animated and eight constant); its referenced AvatarData contributes 102
mapped face-bone deltas. `EndfieldRecoveredNamedFacialAnimation` hashes the
original control names, applies the source position/Maya-Euler/scale deltas
over the existing neutral bindings, validates all mappings and exact record
counts before writing, and fails closed on a missing control or target. It
creates no synthetic controller transforms. The generated prefab keeps
`playOnEnable=false` and `loop=false`: retail Timeline owns the explicit
`PlayFromStart`/`SampleAtTime` call, so the unrelated Overview scene cannot
autoplay a dialog clip and retain its final expression. The 49-check source
verifier, 29-check hierarchy proof, 40-check native merge-order proof, and
pinned-Unity sample/failure-path validator all pass. The generated contract
SHA-256 is
`41EF66730116C789006F795E4FFE0FA82D190CD87F3657972C19B09C21349C75`;
the Unity validation log SHA-256 is
`430604D43004CADE0E6A503C0B8F3F0167B37E8B4F0BD62845DC16EA7EC6F365`.

`SkeletalMorphCore.Update` at `0x18344a100` closes the current merge/apply
chronology: reset runtime data; main transition; blink; lip transition; first
job completion; lip-sync evaluation; weight smoothing/snap; eye look-at;
generic single track; morph-to-bone; shader evaluation; apply weight;
bone-Transform application and completion; then renderer shader-property
application. Ear morph owns a separate native job/apply sequence. This places
blink before lip sync, eye look-at before the generic track and bone jobs, and
shader writes after bone evaluation.

The original merge-order 40-check evidence/verifier lives under
`unity_endfield_graph_shader_lab/scratch/character_recovery/facial_morph_runtime/`
as `verify_facial_curve_runtime.py` and
`facial_curve_runtime_audit.{md,json}`. The corrected dialog-chain proof is the
29-check
`scratch/reverse_engineering/facial_controller_hierarchy/verify.py` and its
report. Full relative-path construction for the anonymous 296/272 optimized
clips remains exact CRC32 while the editor-only path strings remain absent,
but that is no longer the hard blocker for dialog playback. The implementation
target is the explicit `SkeletalMorphAnimSO` control names, exact Hermite keys,
face/ear AvatarData mappings, and retail merge/apply order. Live lip-sync,
speye/look-at inputs, shader-property curves, cross-track transitions, and
complete event chronology remain open.

### What is still missing

| Animation area | Current gap |
| --- | --- |
| Animator graph | Serialized main UI graphs are present for all 30 actors. Exact body/private-deco state propagation, normalized-time forwarding, the retail `FromIndex`/`ToIndex`/`EnableSwitch` producer, replacement-model lifecycle, Overview selector conditions, interruption/root-blend flags, `DecoNHide < 0.1` visibility consumption, and the current installed IFix non-replacement result are closed. The missing part is faithful execution of all remaining state transitions/interruption chronology and other parameter/event consumers. |
| Root motion | Motion is clip-space object trajectory and Root is the absolute skeleton body reference, directly witnessed by the Wulfa dash. Character Info's rotation-only post-multiply is source-closed and translation is absent. SprintSP is root-motion-neutral. The gameplay divisor expression, distinct `1e-5` accumulation/`1e-4` accessor gates, and RootMotionModifier manager are recovered: last-added wins, first matching ID is removed, empty restores `{1,false}`, and only delta position/linear velocity receive the scale. Controller blending, non-identity cycle accumulation, indirect modifier callers, higher-level divisor meaning, downstream cliff handling, and final movement/collision/motor behavior remain open, so gameplay GameObject application stays disabled. |
| Humanoid/muscle data | The 206-entry/101-muscle layout, inserted slots 28/30/31/39/41/42, 34/34 exact audited postmodel Avatar referentials, GetZYRoll scaling/range reduction, native ZYRoll construction, raw no-clamp production table, normal `Animator.Update` materialization edge, conditional foot-goal rebuild, inactive translation-DoF stage, eight-pair TwistSolve, exact compact-to-physical writes, and later generic component precedence are recovered. Current UI clips map no extensions, but a 33-frame Wulfa/loli original fixture animates all six. The strict original-f5 native replay yields all 486 physical local records for all 33 frames as a deterministic 769,824-byte oracle. Its opt-in lab path applies 485 Transform records plus 4,850 generic TRS bindings, materializes 48 exact Avatar support nodes, fails closed on missing paths, and visibly deforms the 4,902-vertex Wulfa body by up to 0.5109154 units between frames 0 and 16. General clip transport, hand/TDoF, Motion placement, IK, blending, constraints, and secondary simulation remain open. |
| Facial behavior | Exact NPC -> face/ear avatar ownership, native base-pose-first mapped-bone evaluation, Maya-Euler conversion, all 2,680 resident neutral bindings, baseline automatic blink ownership/schedule/curve, authored dialog pause/resume, fork Animator morph-binding icalls, and native blink/lip/eye/bone/shader merge order are source-closed. The neutral layer is active. Exact tracker-10 automatic blink now runs for the source-eligible Wulfa/Li owners: six named controls each, 50/38 mapped deltas, per-core deterministic `[3,4)` scheduling, 0.5-second neutral return, and dialog pause/resume/stop. Original dialog playback is proven name-based: `DialogSkeletalMorphTrack` resolves `SkeletalMorphAnimSO`, `FMorphCtrlCurve.Create` hashes explicit control names, and Li's 272 face plus 24 non-neutral ear names close its 296-control namespace. The absent editor-only 296/272 optimized clip paths do not block this path and must not be synthesized. One exact Zhuang Fangyi dialog fixture executes 12 named controls and 102 mapped bone deltas with explicit Timeline-owned playback and fail-closed validation. Generalized named-asset ingestion, broader emotion transitions, lip-sync/speye inputs, look-at targets, face material curves, cross-track transitions, and event chronology remain open. |
| Events | Animation events, visibility handlers, audio, material/VFX events, prop toggles, and timeline signals |
| Item widgets | All 204 owner-qualified item/deco runtime clips validate against their decoded source samples, including six exact Wulfa apple clips, two Pelica visibility curves, Mifu's exact deco-2 owner, and four owner-qualified Pograni copies of the shared disappear PPtr. Exact private controllers now drive known Overview start-to-loop/disappear/displayoff handoffs; 14 private controller sources remain unavailable, and external FX/weapon/creature companions still need separate evidence. |
| CharInfo scene animation | Floor/grid one-second opened endpoints are recovered, but complete UIAnimation in/out curves and transition policy are not played |
| FX | Zhuangfy's complete seven-root entrance identity, 16-track Timeline, Effect/EntityVFX scheduling, 92-node/70-particle source prefabs, 60 materials, 14 meshes, 75 textures, and three shader families are recovered. Six exact material tuples now execute identity-scoped BaseV2/RadialBlur/Refract ports through the selected native `A2B10G10R10_UNormPack32` MRT, snapshot-copy, indexed-blend, depth-access, post, and after-post chain; 54 other variants remain `ColorMask 0`. The selected ports preserve the original reciprocal exposure, `_VFXParams0` player/time producer, recovered `_RecoveredLODFade.xy` hash/strength input, target1 equations, radial `_InParticle`, and refraction red/alpha/dissolve behavior. Retail custom-alpha packing/unpacking, the direct non-instanced `PerDrawBaseData` ABI, the separate `SRP_INSTANCING_ON` array ABI, and the neutral `(1000,0,0,0)` disabled sentinel are source-closed. The selected effect has one distance tier, culling and auto-fade disabled, and no stock `LODGroup`; the lab executes the exact dither equations with the neutral payload while synthesizing no uncaptured manual-alpha transition. The final Unity import validates 7 recovered/53 fail-closed assets with zero bounded compiler/shader/runtime errors, and a separate fresh editor validates all three piaodai materials. A compiler-clean D3D12 control probe also executes the three queue-3700 piaodai layers through the owned MRT, changing 7,571 pixels. The current-build total order is source-closed as GBuffer -> ForwardOpaque -> main ForwardOnly -> Distortion -> gated Phase1 -> after-DOF ForwardOnly. Three absent rarity CRCs remain source-proven stale and unbound. The opaque character's raw mesh influence encoding, native row ring, `HGMeshSkinning.compute::CSMain` 128x1x1 producer, 0x38 record ABI, exact batched dispatch, retained current/previous output lifetime, triple descriptor bank, graphics current/previous/source stream rewrite, draw-mode flags, current/previous object and skin records, skipped-generation collapse, selected shader route, and renderer-space bind-pose construction are source-closed. The lab still needs a dedicated unskinned raw indexed CharacterNPR MRT draw; binding the row route to Unity's current `SkinnedMeshRenderer` stream would double-skin. The custom job's raw D3D12 `startInstance` lane is proven absent from the selected shader ABI and is not a piaodai blocker. Also missing are retail RenderDoc attachment/captured-frame pixel comparison, exhaustive world/terrain/foliage/vegetation target-1 admission for general-world parity, the exact captured-frame exposure, any captured-frame manual LOD override, active fork renderer-field execution, IFix payload capture, Awake/OnEnable/first-automatic-frame chronology, and native alpha-quad eligibility. |
| Secondary dynamics | The current BeyondDynamicBone generation, exact four-actor roots/colliders/serialized parameters, CharUI weight bridge, component lifecycle, manager initialization/delegates, wind update ownership, Character Info environment, and local IFix non-replacement are closed. Missing are the seven exact PlayerLoop anchor pairs/placement booleans, Burst job numerics/writeback/cross-frame scheduling, global wind state, numeric original-output fixtures, and an equivalent runtime; execution remains disabled. |
| Procedural motion | Authored targets are preserved roster-wide and guessed lab IK is fail-closed. Exact Grounder/foot bindings and serialized profiles cover all 30 actors; 28 use world-up and Chen/Li use the recovered root-aligned base path. Three-key lookup/miss behavior, final pelvis recurrence, active `Terrain|IK` mask, quality-3 queries, delegate ownership/order, ECS acceptance, missing-ground continuity, pelvis/leg order, final length clamp, and external hand-target path are source-proven. Runtime implementation is blocked on live controller values and cross-MonoBehaviour/Animator frame chronology, a source-compatible terrain provider, C# profile consumption, the retail solver surface, and numeric fixtures; alternate-quality/overstep/prediction/capsule branches and broader pose drivers remain open. |
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
- the corrected sRGB resource views remove the lab-wide washed/pale failure:
  Last Rite's dark cloth/teal panels, Zhuang Fangyi's green/black layers,
  Wulfa's red/black/white outfit, and Li Zhiyan's dark equipment now retain
  materially stronger source contrast;
- Wulfa's face and white dress still remain locally flatter/brighter than the
  retail reference;
- Zhuangfy's face and hair still lack some retail dark-side/highlight
  organization even though the earlier color-space washout is gone;
- hair response and internal occlusion are different, not merely noisier;
- dark hardware and layered cloth have compressed or misplaced response;
- ground/contact shadow and physical background integration are incomplete;
- shell outlines and behind-hair composition still expose compatibility
  behavior;
- the retail overlay UI is absent by design.

The post-neutral-pose and exact-eye-mask 30/30 render passes change former
structural results:
Li Zhiyan now appears in the roster with her exact face and ear neutral avatars,
and Last Rite no longer contains detached auxiliary white models. Zhuang
Fangyi's expected body-mounted items are present rather than fallback-white.
The earlier claim that these two masks required sRGB sampling came from an
inverted `TextureColorSpace` interpretation. Original binary and type-tree
evidence now prove `m_ColorSpace=0` is Linear; all 49 owners use the exact
`RGBA_BC7_UNorm` mip chain and are verifier-guarded. These are
ownership/pose/import fixes, not proof of retail shading parity. The authored
BC7 payloads and all six source mips are now byte-exact in the lab. Remaining
eye-overlay boundaries are live global mip bias/TAA inputs,
live type-4 volume values, and the runtime state IDs consumed by the closed
custom mixed-list comparator for equal-key material slots. The neutral executor
still does not drive expressions or blink during ordinary Overview playback;
the exact Zhuang dialog fixture remains explicit opt-in and automatic blink is
not yet integrated.

Historical registered material-span diagnostics varied from roughly 1.3x to
4.0x reference/candidate range depending on actor/material. Those numbers are
not a current acceptance score: pose, masks, background, and final SDR post are
confounders. They do establish that the gap is broad and material-dependent,
so a global exposure, saturation, bloom, or sharpness adjustment cannot close
it.

The all-roster success count only proves breadth and technical validity. It does
not prove that the generalized shaders are correct for every actor. Last Rite
and Fluorite remain useful visible counterexamples, but their actor-specific
material selection is now substantially narrower: Last Rite's three selected
cloth branches and both actors' hair-shell queue/depth state are source-bound.
Remaining differences should be investigated in generalized advanced-mask
stockings and wider weather behavior outside exact Last Rite cloth-03, the
still-default-off canonical PreG path and unrecovered
retail ECS/live-switch behavior, shared CharacterNPR lighting and material math,
remaining non-face native mip payloads, weather/customization state, and final presentation
rather than another generic fallback.

## Highest-value next work

### Rendering

1. Recover and implement the minimum binding-compatible `SphereOutside`
   deferred resolve path. The exact source-specialized five-MRT producer now
   passes a default-off GPU packing audit, and the installed offline/unpatched
   nine-switch result plus passes 0/1/2 + WriteAlpha draw sequence are closed.
   The exact no-local-probe oct-array conversion, global constant buffer,
   camera binning, zero-mask byte-address path, and serialized CharInfo
   sky-luminance fallback are now source-closed and implemented as an
   unpublished default-off resource owner. Next populate the exact live
   `_LightBinningConstants`, `ShadowData`, `LightCookieData`, and
   `HDPunctualLightCharacterShadowData` contents; recover the exact streamed
   V2 irradiance voxel payloads/per-frame parameters, remaining light/shadow
   resource instances, and retail settled VisibilitySH posed-record values plus the
   corresponding retail view-cull survivors/order;
   recover their CharInfo-frame values/lifetimes; and close the
   exact render-graph/subpass/
   depth contract before executing the original pass-0 resolver and
   WriteAlpha. Live-confirm any later delivered IFix state. Do not substitute
   a generic Lit sphere or promote the diagnostic projection/depth policy into
   the viewer.
2. Extend the now validated default-off canonical PreG owner by directly
   validating authored stencil bit 32. The character-shadow helper admission,
   ordering, ID/layer encoding, 14-active/15-ABI distinction, atlas
   dimensions/rectangles, direct `Light.shadowStrength` scaling, and full
   current binary list schedule are closed. Fourteen exact helper profiles and
   their 151 ordinary LOD0 realtime casters now GPU-execute every assignable
   slot and row transition; five realtime-false rows fail closed, and desktop
   proxies remain invalid index 15. The original graph's first-write
   allocation/latest-read-or-write release boundary is binary-closed. Next
   recover the remaining exact actor profiles, identify the generic ECS
   renderer-list backend/live entity census, and recover complete client
   frame/VFX consumers without substituting lab objects or inferring VFX
   caster participation. Do not treat proven
   pool eligibility as observation of a later physical allocation alias. The default-off
   VisibilitySH replay now owns the exact
   mesh, LUT, half-depth path, actor records, and native posed-record formula;
   its isolated Wulfa/Zhuang GPU captures and roster sweep pass. Capture the
   matching retail target and exact survivor order before activating
   `ShadowPlane`. Keep retail
   DrawECS/query/chunk/PSO ordering and
   live preZ/IFix state explicit rather than treating the SRP lab draw as parity.
3. Keep the source-closed RG8 screen-shadow attachment bridge default-off and
   content-invalid. Low-resolution directional/blur, ContactShadowCS plus its
   native four-side dispatch builder and public D32/S8 stencil bridge, and the
   full-screen scene composition are now exact. CharInfo's cloud-disabled
   constants/white texture, ASM skip predicate/default comparison boundary, and
   CSM frame/ShadowData ABI are also closed. The binary default three-cascade D16 topology/settings and a
   populated default-off Wulfa/Zhuangfy Unity caster atlas are now reproduced.
   The exact ceil-quarter raw receiver and 7x1/1x7 R8 blur are also live and
   content-proven for both actors. The recovered full-resolution scene resolve
   is now attached and GPU-proven for both actors with exact endpoint trust,
   4x4 phase rotation, 16-Gather/64-comparison refinement, and neutral G, while
   deliberately remaining unpublished to Eye. Recover exact native caster
   inclusion/culling and canonical CSM/ShadowData/
   `_LowResDirectionalShadow`/`_ContactShadow` publication. The current
   installed terrain variant and source-owned first-contact HGCamera phase are
   closed; preserve the future-patch/runtime-mutation boundary without
   reintroducing a fitted selector.
   Preserve the explicit retail-player-2021.3.34f5 versus
   lab-editor-2021.3.34f1/2022.3.62f3 ASM probe boundary. The exact
   comparator and maximum fourteen-actor QueryID/layer transport are now
   GPU-proven through every assignable slot 0..13 and every row transition.
   Prove same-frame physical pool reuse before activating the mandatory Eye R
   consumer. The paired
   runtime-deformation producer and `POSITION/TEXCOORD4` graphics binding are
   now closed. Build a dedicated unskinned raw indexed draw that owns original
   weights/indices, current/prior output allocations, and the recovered
   generated history streams, then bind it to the source-closed
   `A2B10G10R10_UNormPack32` scene-motion MRT before enabling motion-dependent
   Eye behavior. The compatibility `SkinnedMeshRenderer` stream cannot be
   reused without double-skinning. Do not add a fabricated history texture
   because `sceneMV` itself is current-frame data.
4. Finish the now-bounded native light-culling gap before claiming full
   interleaving: lift the scheduled projected-screen/scene-layer producer, the
   320x160 occlusion/cache helper, and the `useFallbackLightCulling` core, then
   capture live equal-key ordering and unrelated scene transforms. Preserve the
   recovered per-camera owner, tier, max/min-distance, Point/Spot, OBB,
   distance-sort and cap behavior rather than replacing it with stock Unity
   culling. Cookie atlas ownership, packing, slot assignment, matrices and the
   CharacterNPR consumer are closed; for non-Zhuang flickering lights, recover
   the scheduled ECS curve evaluator that writes the runtime component's
   `+0xF0` scale instead of guessing it. Then finish per-family material
   carriers. The exact selected Wulfa/Zhuang hair energy carrier now has clean
   pose-locked D3D12 off/on/material-only captures and is correctly default-off;
   the sky-held-off frame is byte-identical to the full selector, and the
   remaining large positive-luma material delta worsens the retail comparison,
   especially Zhuang's crown and face.
   Recover the missing source light/shadow/ambient scheduling that should bound
   that energy rather than tuning or promoting the carrier. For Li fur, close
   the nonzero-noise horizontal
   transmission reference and bind the now source-closed auxiliary MRT only
   after the retail previous-transform/TAA history attachment is recovered; do
   not alter the now source-pinned vertex displacement or
   coverage/alpha/root-shadow path. Use Wulfa and Zhuangfy
   pose-locked A/Bs, then audit every actor; prioritize Last Rite and Fluorite
   as variant failures.
5. Extend native mip preservation beyond the exact 193-object/388-owner payload
   contract plus two shared eye-shadow masks. The remaining 658 descriptor-only
   objects still use decoded PNG top levels and Unity-regenerated lower mips.
   Prioritize only evidence-backed visible counterexamples among other actors,
   and recover live per-renderer weather/customization state before judging the
   last material differences. Keep the current 195-object/437-owner exact
   aggregate as the regression fixture.
6. Close the remaining post-Uber paired-depth/copy/scaler and overlay UI state
   only where it affects the selected shader target. DLSS/DLAA remains out of
   scope unless the user explicitly reopens temporal reconstruction.
7. Treat the 129 non-playable prefabs as dependency-closed static baselines,
   not shader-parity results. Recover their exact Material keywords, disabled
   passes, custom queues, renderer probe/sorting/shadow flags, native texture
   descriptors/mips, runtime material overrides, and VFX ownership from the
   original data before widening the beauty-render claim. Keep lower LODs,
   `DefaultHGMaterial` slot hosts, particles, and Nefarcore's external geometry
   fail-closed. Use representative enemy, ability, and modular-NPC captures to
   drive family-level work; do not apply playable CharacterNPR assumptions to
   every actor.

### Animation

1. The retail producer for `FromIndex`, `ToIndex`, and `EnableSwitch` is now
   closed through `CharInfoCtrl -> PhaseCharInfo -> PhaseCharItem`, including
   private-deco mirroring and replacement-model lifecycle. Recover the
   producers and semantics of remaining CharInfo state parameters. The current
   installed IFix table is proven not to replace either the `0x85AD` guide
   action or the closed `CharUIModelMono` entry/deco route; re-run the IFix
   verifier after installed-data updates. Then
   replace the legacy approximation only where full Animator transition/
   interruption execution is source-proven.
2. Keep the integrated 33-frame `A_actor_loli_sprint_loop_sp_01`/Wulfa
   physical-Transform fixture as the strict regression oracle for the recovered
   `base/rest -> 101 muscles + separate
   Motion/Root -> GetZYRoll -> B314D0 -> B323F0 TwistSolve -> physical TRS ->
   B06330 per-component generic overlay` order. The exact
   SprintSP controller and optimized job path both skip the conditional
   `B17DB0` foot-goal rebuild.
   The pinned allowlisted offline `A7B990+B34260` phase now covers all 33
   original frames and every Axes row with exact emulator outputs. The original
   AxesInfo constructor/materializers and `B38B10` caller bridge are closed:
   serialized `m_PreQ` lands at `0x00`, `m_PostQ` at `0x10`, records have
   0x60-byte stride, and no adapter swaps them. The corrected emulator validates
   the maintained production formula. The same strict allowlist now executes
   every `B27930` TwistSolve pair for all 33 frames from those exact Axes outputs,
   with the full output byte stream and helper topology pinned. Extend the inert
   boundary only to the enclosing `B314D0` scheduler/root object if its complete
   allocation, ownership, and call surface can be allowlisted. Do not
   call `EndfieldBase` ordinal 1 or internal UnityPlayer RVAs;
   those enter protected/uninitialized runtime paths and do not constitute a
   read-only animation harness.
   Normal `Animator.Update`, the eight pair order, `(1,0,1,0)` playable
   factors, all 272 adjacent compact/physical pair mappings, and exact mapped
   write ownership are already closed. The B261 two-cross orientation basis,
   B314 inverse-helper compact-root finalizer, Hips-rest-space conversion, and
   `m_Scale*RootT` physical Hips solve are now closed and ported. Public-f1
   same-version intermediate replay is within `2.98e-6` position component and
   `2.42e-5` degrees; the original-f5 referential against the public rebuilt
   Avatar is bounded to `1.85 mm / 0.11 degrees`. Preserve named twist side-branch local
   curves. Do not feed the extensions into a stock
   95-muscle retargeter or clamp authored over-range values; only a specific
   curve producer may constrain values if its own original code proves it.
   Use the maintained direct retail models for the now-closed
   `B25830/B25910` body gather and `B25300` hand gather, and use the public-f1
   numeric fixture only to validate proven unchanged surrounding families,
   the root equations above, and the now instruction-closed
   `B34260 <-> 95B8B0` ZYRoll equation. The
   `94D300 -> B25B20+B25910/B38B10` split-stage topology, retail `B13240`
   post-stage, `B06170 -> B33BD0` 48-byte physical copy, and retail/public
   `B06330 <-> 9327D0` component overlay are closed. Wulfa's generic bindings
   author translation/rotation only, preserve base scale, and have zero
   humanoid destination overlap. Do not
   revive the rejected `B25830/B25910 -> 959E50/959F50` structural look-alike;
   the native retail-f5 numeric/bit-exact output oracle is now recovered for
   all 33 frames/486 physical nodes of the pinned Wulfa SprintSP fixture.
   The exact Avatar/clip transport and visible skinning validation are now
   active as an explicit opt-in path. Before generalizing, recover a second
   original Avatar/clip full-pose oracle and prove its bindings independently.
   Hand/TDoF, Motion placement, IK, blending,
   constraints, secondary simulation, and other Avatar/clip pairs remain
   outside that fixture.
3. Recover controller transition/interruption root-motion blending,
   non-identity loop-cycle accumulation for clips other than the now-closed
   steady SprintSP fixture, multi-modifier aggregation, pipeline time, and
   final movement motor/collision gates before enabling gameplay object motion.
   Character Info remains rotation-only and must never consume Root as object
   motion.
4. Bind the 23 recovered `FootIKWeight` arrays only when a dedicated source-
   compatible runtime exists. The active `Terrain|IK` mask and final
   acceleration/floor/air/idle/ultimate/gait pelvis recurrence are recovered;
   first recover terrain/ECS fixtures, live controller values, cross-
   MonoBehaviour/Animator frame chronology,
   and C# consumption of the already
   recovered per-actor Grounder profiles, the pelvis-aware foot-only consumer
   surface, and numeric original-frame
   fixtures before implementing the quality-3 Grounding path. The ordinary and
   Chen/Li root-aligned base coordinate frames are already closed. Then reverse
   the alternate quality/overstep/prediction/capsule bodies. The static hand
   boundary is now closed as an external call-time exData injection point, not
   serialized perform data; obtain an observed indirect Lua/delegate/IFix
   provider and target fixture before implementing it. Continue looking for
   indirect or patch-delivered knee/weapon consumers, since the current base
   metadata, literals, serialized components, and direct-call graph contain no
   weapon-IK consumer. Keep the lab two-bone solver
   fail-closed and never infer weights from target distance.
5. Keep the integrated current-retail automatic-blink path as a strict
   Wulfa/Li regression: tracker type 10, the `normal01 -> blink_02` PPtr, the
   recovered per-core deterministic `[3,4)` scheduler, full 0.5-second neutral
   return, and dialog-authored pause/resume/stop semantics. Do not widen it to
   other actors without their exact `disableBlink` ownership and mappings, and
   do not replace it with a generic eyelid AnimationClip. Keep the current exact Zhuang
   `SkeletalMorphAnimSO` fixture as the named-path regression: its 12 explicit
   controls, 102 AvatarData deltas, Hermite timing, Maya-Euler conversion,
   fail-closed bindings, and Timeline-owned playback are active. Generalize
   named ingestion through the recovered dialog chain: the source assets'
   explicit names, Hermite curves, `Animator.StringToHash(ctrlName)`, and native
   `ToNative -> writable track` path are source-closed, and Li's 296-name
   namespace is complete. Do not synthesize a `FacialMorphCtrlGO` hierarchy
   from the separate anonymous optimized clip hashes. Then recover live lip-
   sync/speye inputs, look-at targets, remaining material curves, and events.
6. Implement the original UIAnimation policy for floor/grid and exact item
   widget/FX lifecycle rules.
7. Zhuangfy's separate piaodai Effect clone, `0..4.5166666667` motion/alpha
   interval, three authored materials, and Actor-placeholder exclusion are now
   integrated. The shipped Lua owner, `gacha_char_start_6` clip, rarity-6
   pre-roll gate, and black-screen wait are source-closed. The other six
   Effect roots now exist as strict source-root prefabs with all 92 subtree
   nodes and 70 stock particle/module and renderer payloads under exact Unity
   `2022.3.62f3`. Six exact material identities now run their selected
   two-target BaseV2/RadialBlur/Refract ports; the other 54 unrecovered retail
   variants fail closed without color writes. A strict Zhuang-only 16-track
   Timeline now schedules all seven
   particle controls, replays the four Animation tracks, and executes the four
   additive-material plus one dissolve handlers from original serialized data
   and the recovered native state machine. The exact four widget LOD renderers,
   CrossFade `LODGroup`, newest-first/native-four-record cap, original-material
   restoration, parent metadata, and explicit initial/delayed Effect operations
   are integrated. No serialized EntityVFX override targets the piaodai ribbon,
   and the three excluded rarity CRCs are proven stale/removed rather than live
   missing nodes. Before claiming the complete entrance, execute the active
   semantics among the 25 selected fields outside the stock importer surface
   (23 Endfield-only plus two shared public-f1 names), capture active IFix state,
   close Awake/OnEnable, equal-time callback, and first automatic Director versus
   Lua group-6 chronology, recover native alpha-quad renderer eligibility, join
   the rarity material curves that remain on the 54 fail-closed variants,
   validate the new selected MRT/snapshot/handle path in live RenderDoc
   (there is no later distortion-vector compositor), add a dedicated unskinned
   vertex draw path that evaluates the now-closed renderer-world-to-local ×
   current-bone-local-to-world × bind-pose arrays for both current and previous
   ranges without double-skinning, bind it to the opaque target-1 path, and
   capture the exact frame's
   `HGCamera.exposureAdaptation` value/history plus the effective alpha and
   live owner/value feeding the now source-closed `EffectLodCfg` manual-dither
   writer and UnityPlayer custom-value pack/unpack path, enumerate world/
   terrain/foliage/vegetation sceneMV writers only when general-world parity is
   in scope, and recover remaining director/mount behavior. The separate
   custom-job 16-byte lane may still be named for engine-wide archaeology, but
   its proven D3D12 `startInstance` output is absent from the selected SPIR-V
   ABI and must not block this captured-frame piaodai queue.
8. Recover the seven exact BeyondDynamicBone PlayerLoop anchor pairs and
   placement booleans, Burst job numerics/writeback/cross-frame scheduling,
   global wind inputs, and numeric original-output fixtures before enabling
   secondary motion. Reject the stale MagicaCloth schema and video-tuned
   look-alikes.
9. Extend to look-at, grounding, and interaction constraints only with
   equivalent source evidence.
10. Recover non-playable animation per exact rig instead of enabling a blanket
    Humanoid path. Start from the 11 enemy and 18 ability/prop controller-bound
    roots, join each controller state to exact clips and generic bindings, and
    classify its Avatar/101-muscle requirements independently. Keep the current
    seven galleries static until controller execution, root motion, events,
    constraints, and source-owned runtime material/VFX coupling are proven.

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

Recover and validate the non-playable static galleries:

```bat
.\recover_all_nonplayable_actor_models.bat --reuse-audited-hierarchies
.\validate_all_generic_actor_galleries.bat
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

Generated AnimationClips are kept slim: `EndfieldAnimationClipSlimmer` strips
the serialized editor-only duplicates (`m_EditorCurves`, `m_EulerEditorCurves`,
~85% of the YAML on dense-sampled clips) after save, and the three clip
writers (`BuildAnimationClips`, the Original-f5 full-pose builder, and the
Zhuangfy gacha runtime importer) call it automatically. Playback uses the
untouched baked `m_RotationCurves`/`m_PositionCurves`/`m_ScaleCurves`/
`m_FloatCurves`; equivalence was validated fresh-session (identical bindings,
scalar curves exact, rotations identical as quaternions — stored editor curves
predate `EnsureQuaternionContinuity`, so raw component comparison shows q/-q
sign flips that are not real divergence). The 2026-07-18 bulk pass shrank 1037
clips from 59.0 GiB to 15.0 GiB and project open to ~4 s. If fat clips ever
reappear, rerun:

```bat
cd D:\fluffy-dump\unity_endfield_graph_shader_lab
.\slim_generated_animation_clips.bat
```

Python validators that grep clip YAML (`verify_wulfa_apple_animation_recovery`,
`build_roster_feature_validation_plan`) keep working because `path:` lines
survive in the runtime curve sections. Do not re-add editor curves for
Animation-window editing; generated clips are baked outputs, not edit sources.

Play-mode entry uses Enter Play Mode Options with BOTH domain reload and scene
reload disabled (`EditorSettings.asset` `m_EnterPlayModeOptions: 3`). With only
domain reload disabled, every Play re-deserialized the backup scene plus all
referenced assets (~140 s per Play on `AllCharacterRecoveryViewer`, dominated
by re-parsing the ~15 GiB of clip text-YAML the resident lineup references).
With scene reload also disabled, loaded assets survive play/edit transitions:
the first Play per editor session still pays the one-time lineup load (~2-3
min, `CharacterRecoveryViewerUI.Start` -> `EnsureResidentLineupLoaded` loads
every catalog prefab and its clips), but every later Play enters in under a
second (measured 173.3 s then 0.63 s in one batch session via
`EndfieldPlayModeEntryTimer.MeasureAllCharacterViewer`). Do not flip the
generated clips to binary serialization to shrink the first Play: 11 scripts
in `unity_endfield_graph_shader_lab/tools/` parse `.anim` text-YAML.

`AllCharacterRecoveryViewer` uses a uniform pure-white background
(`ApplyNeutralWhiteViewerBackground`, kept on rebuild via
`BuildAllCharacterModelViewer`'s `neutralWhiteBackground: true`; re-apply to
the existing scene with batch method
`EndfieldManifestCharacterSetup.ApplyAllCharacterViewerWhiteBackground`).
Four pieces are all required for exact #FFFFFF: white camera clear, flat-white
`M_ReferenceBackdropWhite` on the ReferenceBackdrop quad with `_HdrBoost` 128
(the lab `ReferenceBackdrop.shader` gained this scene-linear multiplier;
neutral input must stay above the shipped ACES_modified highlight-compression
knee, acescg luma >= 2.0, to tonemap to exact white), the recovered CharInfo
sky released (`operatorPhysicalHdrSource = false` — presentation only;
character shading keeps the source-energy path), and the CharInfo vignette
zeroed on `EndfieldHGOperatorPresentation` (it multiplies after the tonemap,
so no backdrop brightness can defeat it — 32x boost still left corners at
sRGB 218). The dark CharInfo room subset (GeoSphere001/CharFloorEffect/
GridDeco) is disabled via `enableRecoveredReadyPresentationSubset = false`.
Other viewer scenes keep the grey reference backdrop; `_HdrBoost` defaults
to 1 so their look is unchanged.

## Original-client observation boundary

The installed retail client uses Vulkan and includes AntiCheatExpert. The
current approved boundary is observation and offline recovery plus narrowly
scoped runtime observation when the user explicitly authorizes it:

- installed assets, IL2CPP code, shader bytecode, settings, logs, screenshots,
  videos, caches, and external telemetry are usable;
- a signed stock profiler should be used through its documented process-scoped
  workflow and the normal launcher/protection chain when accepted;
- an explicitly requested read-only user-mode hook may record only predeclared
  render fields, must pin the complete client/module hashes and target bytes,
  must use the normal attach path, and must not persist or patch game files;
- if protection blocks or terminates either capture path, stop and do not retry
  through evasion;
- do not patch the client, alter protection services/drivers, register a global
  Vulkan layer, force another graphics API, manual-map or hide a DLL, use
  kernel instrumentation, or evade access controls.

Lab-only RenderDoc capture is already valid and useful for proving the Unity
reconstruction. It must not be confused with original-client evidence. The
retail build's dormant-looking HGRP dump classes have no recovered normal
retail trigger, so invoking private dump methods remains out of scope; a hook
may observe an already-executing pinned instruction but may not manufacture a
retail trigger.

The first approved shader-runtime observation is configured by
`unity_endfield_graph_shader_lab/config/shader_runtime_trace_hooks.json`. It
pins all four current client/build files and the exact 12-byte instruction
sequence at `UnityPlayer.dll+0x541500`. The Frida agent reads only source slot
and renderer-list entry `+0x08/+0x0C/+0x4C`, pairs slots 0 and 1 when their
renderer-data index agrees, caps output, and writes a separate shader JSONL in
the existing combined Mission/runtime session. Each capture is labeled with an
explicit Wulfa, Zhuang Fangyi, Li Zhiyan, or Last Rite settled-view target. A
pair is still a candidate until isolated/repeated target captures identify the
eye renderer; no raw pair is promoted directly to final material order.

The first authorized Wulfa attempt on 2026-07-22 did not load either agent.
Frida process enumeration could not see the protected client; the one explicit
PID attach through Frida's normal API was then refused before script creation
because `WriteProcessMemory` returned access denied (`0x00000005`). This is the
current protection boundary, not missing hook configuration, and must not be
retried through evasion. The hash-pinned external fallback completed against
the settled Wulfa view under
`scratch/character_recovery/original_client_external_telemetry_wulfa-settled_20260722_173920_365/`.
It recorded 55 clean NVIDIA samples: 29-33% GPU utilization (31.42% mean),
11,029-11,375 MiB used (11,199.18 mean), 112.5-123.54 W (115.4 mean),
2,295-2,685 MHz graphics clock (2,404.69 mean), and 54 C. Player log confirms
Unity 2021.3.34f5, Vulkan on RTX 5080, shader viewport/layer support, and PSO
warmup enabled. PresentMon exited without process data because the same
protected-client visibility boundary hid the target. These external values are
environment/performance context only and do not close the actor-specific
renderer-list `+0x08` key or prove a shader/pass execution.

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

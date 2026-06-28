# Unity Character Export Workflow Notes

This note documents the current character recovery path for getting Endfield
character models, textures, materials, animation, shader references, and related
resources into `unity_endfield_graph_shader_lab/`.

The Unity project is a viewer/recovery lab, not the primary extraction tool. The
pipeline is:

1. Use AnimeStudio.CLI and repo wrappers to export game assets into
   `export_full/recovered/AnimeStudio-cli/`.
2. Use character extraction helpers to write actor-specific JSON under
   `scratch/`.
3. Use actor manifest generators to combine hierarchy, mesh, material, texture,
   animation, controller, and optional prop evidence into
   `Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/*_recovery_manifest.json`.
4. Use the Unity editor rebuild script to turn those manifests into Unity
   `.asset`, `.mat`, `.anim`, `.prefab`, texture, static prop, and scene files.

## Maintained Entry Points

Open the Unity lab:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\open_character_recovery_lab.bat
```

Rebuild the generated character assets and shared viewer scene:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\build_all_character_recovery.bat
```

Rebuild only the viewer scene from cached generated assets:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\rebuild_character_recovery_scene_cached.bat
```

Render the current viewer preview:

```bat
D:\fluffy-dump\unity_endfield_graph_shader_lab\render_character_recovery_preview.bat
```

Per-actor manifest generators:

```bat
python unity_endfield_graph_shader_lab\tools\generate_wulfa_unity_from_original.py
python unity_endfield_graph_shader_lab\tools\generate_zhuangfy_unity_from_original.py
python unity_endfield_graph_shader_lab\tools\generate_mifu_unity_from_original.py
```

Generic scratch extraction helper:

```bat
python unity_endfield_graph_shader_lab\tools\extract_character_data.py wulfa
python unity_endfield_graph_shader_lab\tools\extract_character_data.py zhuangfy
python unity_endfield_graph_shader_lab\tools\extract_character_data.py mifu
```

Use `--force` when the scratch extraction should replace an existing scratch
directory, and use `--only hierarchy`, `--only meshes`, or `--only clips` for a
targeted refresh.

## Export Roots

The manifest builders use these AnimeStudio output roots:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/
export_full/recovered/AnimeStudio-cli/Persistent/
```

Important subfolders:

```text
maps/endfield_streamingassets_assets.json
maps/endfield_persistent_assets.json
convert_by_type/Texture2D/
convert_by_type/Mesh/
json_by_type/Material/
json_by_type/AnimatorController/
json_by_type/AnimationClip/
```

The normal asset refresh command is:

```bat
.\export_assets.bat --export-from-game
```

That path exports the WebUI-facing image/model asset set plus `Material` JSON,
and it writes the lightweight VFS/asset maps used by the character manifest
builders. Use a lower worker count if memory pressure is high:

```bat
.\export_assets.bat --export-from-game --animestudio-jobs 4
```

Use debug asset mode only when broad diagnostics or original shader/extra asset
conversion is needed:

```bat
.\export_assets.bat --export-from-game --debug-assets --animestudio-jobs 4
```

Debug asset mode adds broad conversion/JSON coverage such as `Shader`,
`AnimationClip`, `TextAsset`, `Font`, and extra controller/script-like asset
types. The generated Unity viewer does not assign exported game shaders by
default.

## Character Scratch Extraction

`unity_endfield_graph_shader_lab/tools/extract_character_data.py` makes the
scratch data that the manifest generators expect. It uses:

```text
tools/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe
tools/endfield_asset_map_filter.py
export_full/recovered/AnimeStudio-cli/StreamingAssets/maps/endfield_streamingassets_assets.json
```

The built-in actor configs are:

```text
wulfa     actor_path_id 0028, postmodel root chr_0028_wulfa_postmodel
zhuangfy  actor_path_id 0030, postmodel root chr_0030_zhuangfy_postmodel
mifu      actor_path_id 0031, postmodel root chr_0031_mifu_postmodel
```

The helper runs three extraction stages:

```text
hierarchy  GameObject:Both, Transform:Both, SkinnedMeshRenderer:Both, Animator:Both
meshes     Mesh:Both
clips      AnimationClip:Both
```

It filters the asset map before each AnimeStudio call:

```text
hierarchy  Animator named exactly chr_<id>_<actor>_postmodel
meshes     Mesh names matching ^S_<actor_prefix>_.*
clips      AnimationClip entries containing the actor token
```

Typical outputs:

```text
scratch/<actor>_postmodel_hierarchy_json/GameObject/*.json
scratch/<actor>_mesh_json/Mesh/*.json
scratch/<actor>_animation_clip_json/AnimationClip/*.json
scratch/<actor>_postmodel_animator_filter.json
scratch/<actor>_mesh_filter*.json
scratch/<actor>_animation_clip_filter*.json
```

Some current actor generators point at older targeted scratch names, for
example `scratch/mifu_postmodel_hierarchy_json_targeted`,
`scratch/mifu_mesh_json_316c_targeted`, and
`scratch/zhuangfy_mesh_json_316c`. Keep those overrides in the per-actor
generator until the scratch layout is intentionally normalized.

## Model And Skeleton Export

The model source is the original Unity postmodel hierarchy, not a hand-authored
FBX. The hierarchy stage exports GameObject, Transform, SkinnedMeshRenderer, and
Animator JSON for the postmodel root. The mesh stage exports Unity Mesh JSON for
the referenced `S_actor_*` meshes.

`character_manifest_common.py` reads the hierarchy and builds:

```text
transforms      recovered Transform hierarchy
scene_transforms filtered hierarchy used by the viewer
meshes          lod0 non-VFX renderer list
materials       materials referenced by those renderers
renderer_summary
```

The active model filter is intentionally narrow:

```text
include paths under Mesh_all/lod0/
exclude VFX mesh names and VFX paths
exclude lower LOD branches
exclude Shadow_Proxy branches from the scene transform manifest
```

For each SkinnedMeshRenderer entry, the manifest stores:

```text
name
path
mesh_json
mesh_path_id
mesh_container
material_keys
material_names
root_bone_path
bone_paths
aabb_center
aabb_extent
```

The Unity importer then creates the actual Unity mesh asset. In
`EndfieldManifestCharacterSetup.BuildMeshes()` it:

1. Reads the source `mesh_json`.
2. Calls `BuildUnityMesh()` to create a Unity `Mesh`.
3. Writes the mesh to:

   ```text
   Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/Meshes/<mesh>.asset
   ```

4. Adds or updates a `SkinnedMeshRenderer` on the recovered transform object.
5. Binds bone transforms by path CRC and writes `bindposes` and `boneWeights`.
6. Assigns the recovered material list.
7. Applies the recovered local bounds when available.

`BuildUnityMesh()` imports vertices, normals, UV0, UV1, vertex colors, tangents,
indices, submeshes, and bounds from the Mesh JSON. If normals or tangents are
missing or mismatched, Unity recalculates them.

## Texture And Material Export

Textures are exported by AnimeStudio under:

```text
export_full/recovered/AnimeStudio-cli/<StreamingAssets|Persistent>/convert_by_type/Texture2D/
```

Materials are read from:

```text
export_full/recovered/AnimeStudio-cli/<StreamingAssets|Persistent>/json_by_type/Material/
```

The manifest builder resolves texture/material links by path ID through the
asset maps. `material_info()` reads each material JSON and records:

```text
name
path_id
container
asset_root
json
shader_path_id
shader_name
base
normal
textures
floats
colors
alpha
```

Texture links come from `m_SavedProperties.m_TexEnvs`. Colors come from
`m_SavedProperties.m_Colors`. Numeric shader/material parameters come from
`m_SavedProperties.m_Floats`. The manifest keeps all texture property names so
Unity can set matching material slots when they exist.

The Unity importer creates generated materials under:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/Materials/
```

Current generated actor materials use Unity's built-in `Standard` shader by
default. `ResolveShader()` returns `Standard`, with `Diffuse` only as a fallback
if `Standard` cannot be found. This is intentional for fast Play Mode entry and
stable preview behavior.

`ApplyMaterialProperties()` applies:

```text
base color / _Color / _BaseColor
stored material colors
stored floats when the Unity material has the property
textures whose source files exist
alpha blend settings
Standard shader keywords for normal, metallic/gloss, and emission maps
hair, eye, skin, cloth, overlay-shadow preview flags where supported
```

`ImportTexture()` copies source texture files into:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/Textures/
```

Then it configures the Unity `TextureImporter`:

```text
sRGB enabled for color/base textures
linear import for normal, mask, metallic/gloss, MRO/MRA, SDF, line/stroke maps
mipmaps enabled
wrap mode Clamp
filter mode Trilinear
anisotropic level 8 for cloth color textures, 2 otherwise
alphaIsTransparency enabled for color/base textures
cloth color textures imported uncompressed
```

Texture property guessing is name-based for generated profiles. Examples:

```text
*_D.png or *_RD.png   -> _BaseMap
*_N.png or *_HN.png   -> _BumpMap
*_P.png, *_M.png, *_RS.png -> _MetallicGlossMap
*_ST.png              -> _OutlineMask
names containing ramp or lut -> _DiffRampMap
```

## Shader Export And Shader Resources

The Unity project currently carries shader resources in:

```text
Assets/EndfieldGraphShaderLab/Shaders/
Assets/EndfieldGraphShaderLab/Shaders/Preview/
```

These are hand-maintained reference or experimental shaders. They are not
generated by the character rebuild, and generated actor materials do not assign
them by default.

The manifest still records the original material's `shader_path_id` and
`shader_name` when the asset map can resolve the `m_Shader` reference. That
metadata is useful for comparing original material families, but it is not the
same as assigning the original game shader in Unity.

When original shader export or broad shader diagnostics are needed, run:

```bat
.\export_assets.bat --export-from-game --debug-assets
```

or call AnimeStudio.CLI directly for a targeted shader conversion/debug pass.
Keep in mind that a converted/dumped shader is not automatically compatible with
the Unity viewer. To intentionally restore custom shader assignment, update:

```text
Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/EndfieldManifestCharacterSetup.cs
```

The relevant places are:

```text
ResolveShader()
ApplyMaterialProperties()
ConfigureMaterialSurface()
ApplyGeneratedMaterialProfileFlags()
ApplyGeneratedTextureImportProfiles()
```

Do that as an intentional shader-recovery task, because material property names,
render queues, blend modes, and texture color-space assumptions may need to
change together.

## Animation Export

Animation recovery has two layers:

1. AnimeStudio exports original `AnimationClip` JSON for clip metadata and
   binding evidence.
2. The ACL sampler writes frame samples that Unity can turn into transform
   curves.

The generic extraction helper writes source clip JSON to:

```text
scratch/<actor>_animation_clip_json/AnimationClip/
```

The current manifest generators often use actor-specific sample roots:

```text
scratch/wulfa_acl_samples_all/
scratch/zhuangfy_acl_samples_all/
scratch/mifu_acl_samples/
```

For Wulfa locomotion and dodge coverage, keep ACL sidecars current with:

```powershell
python D:\fluffy-dump\tools\endfield_acl_sampler\export_actor_samples.py `
  --clip-dir D:\fluffy-dump\scratch\wulfa_animation_clip_json\AnimationClip `
  --output-dir D:\fluffy-dump\scratch\wulfa_acl_samples_all `
  --actor wulfa --buffer TransformBufferData --buffer RootMotionBufferData

python D:\fluffy-dump\tools\endfield_acl_sampler\export_actor_samples.py `
  --clip-dir D:\fluffy-dump\scratch\wulfa_animation_clip_json\AnimationClip `
  --output-dir D:\fluffy-dump\scratch\wulfa_acl_samples_all `
  --actor loli --buffer TransformBufferData --buffer RootMotionBufferData
```

The manifest builder uses the AnimationClip JSON to recover clip names, binding
metadata, CRC path links, controller evidence, and classification. It uses ACL
sample JSON for sampled `qvvf` transform tracks and frame timing.

For each imported clip, the manifest stores:

```text
name
sample_json
sample_source
frame_count
sample_rate
duration
loop
unity_preview_stride
binding_evidence
clip_class
clip_category
layer_role
standalone_candidate
requires_extra_items
matched_transform_count
missing_transform_count
output_track_count
bones
```

Each `bones` entry maps one sampled track to a recovered Unity transform path:

```text
path_crc
path
name
track_index
pos_animated
rot_animated
```

The Unity importer writes legacy `.anim` clips under:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/Animations/
```

`BuildAnimationClips()` creates a Unity `AnimationClip`, sets `legacy = true`,
sets `frameRate`, and adds local position and local rotation curves for matched
tracks. It samples every frame unless the manifest requests a preview stride for
large clips. Quaternion continuity is applied before the `.anim` asset is
created.

Playback currently uses Unity's legacy `Animation` component, not a recovered
Mecanim controller. `ConfigureAnimation()` adds every generated clip to the
component and chooses a preview clip from the actor preference list. Runtime UI
metadata and recovered state/layer information are stored on
`CharacterRecoveryRig`.

AnimatorController JSON is used as evidence only. The manifest can infer helper
clip combinations, additive layers, recovered state groups, and UI prop
pairings from controller state/blend-tree co-use, but original Endfield runtime
scripts, pose drivers, facial layers, and full state-machine behavior are not
fully reproduced.

## Static Props And Extra Resources

Most character body assets are generated from Mesh JSON. Static props are the
main exception. Wulfa has actor-specific prop recovery in
`generate_wulfa_unity_from_original.py`.

Wulfa static props are looked up from AnimeStudio-converted OBJ files under:

```text
export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Mesh/
```

The generator adds `static_props` entries with:

```text
name
path
mesh_obj
material_keys
material_names
local_pos
local_rot
local_scale
source
note
```

The Unity importer copies those OBJ files into:

```text
Assets/EndfieldGraphShaderLab/Generated/Characters/Wulfa/StaticProps/
```

Then it imports them through Unity's normal model importer, instantiates the
model asset into the recovered prop path, and assigns recovered generated
materials. Wulfa prop clips and recovered states toggle/animate those separate
prop roots where the manifest has evidence.

Other Unity-side resources are split by ownership:

```text
Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/
    maintained editor rebuild/import tools

Assets/EndfieldGraphShaderLab/Runtime/
    maintained runtime viewer, playback, camera, render, and IK helpers

Assets/EndfieldGraphShaderLab/Shaders/
    maintained reference/experimental shader assets

Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/
    rebuildable actor manifests, meshes, textures, materials, animations,
    prefabs, and static props

Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/
    rebuildable shared viewer scene

Assets/EndfieldGraphShaderLab/Generated/Characters/Shared/
    rebuildable shared support assets
```

Do not make durable manual edits under `Generated/Characters/<Actor>` unless the
intent is a temporary experiment. The full build can delete and recreate
generated `.asset`, `.mat`, `.anim`, `.prefab`, copied texture, and static prop
files. Durable behavior changes belong in the manifest generator or
`EndfieldManifestCharacterSetup.cs`.

## Actor-Specific Notes

Wulfa:

- Uses `scratch/wulfa_postmodel_hierarchy_json`, `scratch/wulfa_mesh_json`,
  `scratch/wulfa_animation_clip_json`, and `scratch/wulfa_acl_samples_all`.
- Adds Wulfa-specific static props and UI prop clips.
- Accepts both `wulfa` and shared `loli` ACL sample names for body motion.
- Promotes some UI relax clips when the non-UI clip only recovered secondary
  tracks.

Zhuangfy:

- Uses the defaults in `character_manifest_common.py`.
- Current defaults point at `scratch/zhuangfy_postmodel_hierarchy_json`,
  `scratch/zhuangfy_mesh_json_316c`, optional
  `scratch/zhuangfy_mesh_json_de408`, and
  `scratch/zhuangfy_acl_samples_all`.
- Includes controller recovery, IK metadata, and experimental variant handling.

Mifu:

- Uses targeted scratch roots:
  `scratch/mifu_postmodel_hierarchy_json_targeted`,
  `scratch/mifu_mesh_json_316c_targeted`,
  `scratch/mifu_animation_clip_json_targeted`, and
  `scratch/mifu_acl_samples`.
- Imports LOD0 non-VFX body renderers and selected body/dialog/helper clips.
- Does not currently emit the same IK/controller recovery block as Zhuangfy or
  Wulfa.

## Refresh Checklist For A Character

Use this when adding a new actor or replacing stale character inputs:

1. Refresh the AnimeStudio asset export if the installed game data changed:

   ```bat
   .\export_assets.bat --export-from-game --animestudio-jobs 4
   ```

2. Extract hierarchy, mesh, and clip JSON for the actor:

   ```bat
   python unity_endfield_graph_shader_lab\tools\extract_character_data.py <actor> --force
   ```

3. Generate or refresh ACL transform samples for clips that need playback.
   Use `tools\endfield_acl_sampler\export_actor_samples.py` with the actor's
   `scratch/<actor>_animation_clip_json/AnimationClip` root and the matching
   `scratch/<actor>_acl_samples*` output root.

4. Run the actor manifest generator:

   ```bat
   python unity_endfield_graph_shader_lab\tools\generate_<actor>_unity_from_original.py
   ```

5. Rebuild the Unity viewer:

   ```bat
   D:\fluffy-dump\unity_endfield_graph_shader_lab\build_all_character_recovery.bat
   ```

6. Inspect the generated scene:

   ```text
   Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRecoveryViewer.unity
   ```

7. Press Play and use the runtime UI to switch actor and clips.

8. Render a preview and compare camera/material/animation results:

   ```bat
   D:\fluffy-dump\unity_endfield_graph_shader_lab\render_character_recovery_preview.bat
   ```

Useful logs and outputs:

```text
scratch/character_recovery_build.log
scratch/character_recovery_viewer.png
scratch/<actor>_original_usage_report.json
Assets/EndfieldGraphShaderLab/Generated/Characters/<Actor>/*_recovery_manifest.json
```

## Known Limits

- The Unity viewer imports only the highest-quality `lod0` non-VFX renderer set.
  Lower LODs, VFX renderers, and shadow proxy objects are intentionally filtered
  out.
- Generated actor materials use Unity `Standard` by default. Original Endfield
  shader names are metadata, not active shader assignments.
- Animation playback uses legacy `Animation` clips generated from sampled
  transform curves. Original controller scripts, IK solvers, pose drivers,
  facial morph layers, and full runtime state machines are only partially
  recovered.
- Material reconstruction preserves many original textures, colors, floats, and
  alpha hints, but it is a preview material mapping, not a byte-for-byte
  recreation of the game renderer.
- Static props are actor-specific. Wulfa has the most explicit prop path today;
  other actors need generator support before props are imported.
- The `Generated/Characters` tree is rebuildable output. Fix source manifests or
  importer code instead of manually editing generated assets for durable changes.
